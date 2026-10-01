use crate::{
    config::{ModulationMethod, ProgressionKind, Simulation, Templates},
    modulation,
    theory::{
        chord::Chord,
        key::{Key, Mode},
        tone::Tone,
    },
};
use anyhow::{ensure, Result};
use rand::{seq::SliceRandom, Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, VecDeque};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CyclePosition {
    pub lap: usize,
    pub step: usize, // one-based index in the configured closed sequence
    pub total: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChordEvent {
    pub id: usize,
    pub phrase: usize,
    pub key: Key,
    pub chord: Chord,
    pub degree: Option<u8>,
    pub role: String,
    pub reason: String,
    pub previous_key: Option<Key>,
    #[serde(default)]
    pub cycle: Option<CyclePosition>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ManualModulation {
    Balanced,
    Back,
}

#[derive(Debug, Clone, Copy)]
struct PendingModulation {
    kind: ManualModulation,
    after_id: usize,
    ready: bool,
}

pub struct Progression {
    config: Simulation,
    templates: Templates,
    rng: ChaCha8Rng,
    key: Key,
    queue: VecDeque<ChordEvent>,
    phrase: usize,
    phrases_in_key: usize,
    next_id: usize,
    key_practice: BTreeMap<String, usize>,
    phrase_visits: BTreeMap<String, usize>,
    previous: Option<Chord>,
    previous_key: Option<Key>,
    returned_last: bool,
    cycle_cursor: usize,
    cycle_lap: usize,
    pending_tonic_resolution: bool,
    manual: Option<PendingModulation>,
    manual_notice: String,
}

impl Progression {
    pub fn new(config: Simulation, templates: Templates, seed: u64) -> Result<Self> {
        templates.validate()?;
        config.validate_modulation_methods()?;
        config.validate_approaches()?;
        ensure!(
            config.progression != ProgressionKind::OriginalCycle || !templates.cycle.is_empty(),
            "original_cycle requires cycle in templates file"
        );
        ensure!(
            (1..=8).contains(&config.cycle_chunk_size),
            "cycle_chunk_size must be 1..8"
        );
        ensure!(
            config.minor_dominant_probability.is_finite()
                && (0.0..=1.0).contains(&config.minor_dominant_probability),
            "invalid minor_dominant_probability"
        );
        ensure!(
            !config.keys.is_empty() && !config.modes.is_empty(),
            "empty key scope"
        );
        for mode in &config.modes {
            ensure!(
                templates.templates.iter().any(|t| t.mode == *mode),
                "no template for {}",
                mode.name()
            );
        }
        let mut rng = ChaCha8Rng::seed_from_u64(seed);
        let key = Key {
            tonic: Tone::parse(config.keys.choose(&mut rng).expect("nonempty"))?,
            mode: *config.modes.choose(&mut rng).expect("nonempty"),
        };
        let mut key_practice = BTreeMap::new();
        for name in &config.keys {
            let tonic = Tone::parse(name)?;
            for mode in &config.modes {
                key_practice.insert(
                    Key {
                        tonic: tonic.clone(),
                        mode: *mode,
                    }
                    .label(),
                    0,
                );
            }
        }
        Ok(Self {
            config,
            templates,
            rng,
            key,
            queue: VecDeque::new(),
            phrase: 0,
            phrases_in_key: 0,
            next_id: 0,
            key_practice,
            phrase_visits: BTreeMap::new(),
            previous: None,
            previous_key: None,
            returned_last: false,
            cycle_cursor: 0,
            cycle_lap: 1,
            pending_tonic_resolution: false,
            manual: None,
            manual_notice: String::new(),
        })
    }
    pub fn next_event(&mut self) -> ChordEvent {
        self.execute_manual();
        if self.queue.is_empty() {
            self.build_phrase();
        }
        let event = self.queue.pop_front().expect("phrase always has targets");
        *self.key_practice.entry(event.key.label()).or_default() += 1;
        self.previous = Some(event.chord.clone());
        if self.manual.is_some_and(|p| event.id >= p.after_id) && self.safe_manual_boundary(&event)
        {
            let pending = self.manual.as_mut().expect("pending request");
            pending.ready = true;
            self.manual_notice = format!(
                "Pending {}: after CURRENT chord",
                if pending.kind == ManualModulation::Balanced {
                    "E balanced"
                } else {
                    "Q back"
                }
            );
        }
        event
    }

    pub fn manual_notice(&self) -> &str {
        &self.manual_notice
    }
    pub fn pending_manual_label(&self) -> Option<String> {
        self.manual.map(|p| {
            format!(
                "Pending {}: after {}; finish any chain",
                if p.kind == ManualModulation::Balanced {
                    "E balanced"
                } else {
                    "Q back"
                },
                if p.ready { "CURRENT" } else { "NEXT" }
            )
        })
    }

    /// Schedule after the next presented chord, extending to its resolution.
    /// Replacing a pending request keeps its deadline; repeated keys never stack.
    pub fn request_manual(&mut self, kind: ManualModulation, current_id: usize) {
        if current_id.checked_add(1) != Some(self.key_practice.values().sum()) {
            self.manual_notice = "Manual modulation: return to latest target first".into();
            return;
        }
        if kind == ManualModulation::Back && self.previous_key.is_none() {
            self.manual_notice = "Q unavailable: no previous key yet".into();
            return;
        }
        let candidates = self.reachable_keys();
        if candidates.is_empty()
            || (kind == ManualModulation::Back
                && !candidates.contains(self.previous_key.as_ref().expect("previous key")))
        {
            self.manual_notice = "Manual modulation unavailable: no allowed route".into();
            return;
        }
        let pending = self.manual.get_or_insert(PendingModulation {
            kind,
            after_id: current_id + 1,
            ready: false,
        });
        pending.kind = kind;
        self.manual_notice = format!(
            "Pending {}: after {}; finish any approach/bridge",
            if kind == ManualModulation::Balanced {
                "E balanced"
            } else {
                "Q back"
            },
            if pending.ready { "CURRENT" } else { "NEXT" }
        );
    }

    fn safe_manual_boundary(&self, event: &ChordEvent) -> bool {
        if !matches!(event.role.as_str(), "diatonic" | "arrival" | "mode_change") {
            return false;
        }
        // Preserve explicit V7 -> tonic even if it crosses a preview boundary.
        let resolving_next = event.degree == Some(5)
            && event.chord.quality == "7"
            && (event
                .cycle
                .as_ref()
                .is_some_and(|c| self.templates.cycle.get(c.step) == Some(&1))
                || self.queue.front().is_some_and(|e| {
                    e.key == event.key && e.degree == Some(1) && e.role == "diatonic"
                })
                || (self.queue.is_empty() && self.pending_tonic_resolution));
        !resolving_next
    }

    fn execute_manual(&mut self) {
        let Some(pending) = self.manual.filter(|p| p.ready) else {
            return;
        };
        self.manual = None;
        let destination = match pending.kind {
            ManualModulation::Balanced => self.select_new_key(false),
            ManualModulation::Back => self
                .previous_key
                .clone()
                .filter(|k| self.reachable_keys().contains(k)),
        };
        let Some(destination) = destination else {
            self.manual_notice = "Manual modulation unavailable here: staying in key".into();
            return;
        };
        self.manual_notice = format!(
            "Manual {}: {} -> {}",
            if pending.kind == ManualModulation::Balanced {
                "E"
            } else {
                "Q"
            },
            self.key.label(),
            destination.label()
        );
        // Discard only unpresented music; do not award coverage for previewed targets.
        self.queue.clear();
        self.next_id = self.key_practice.values().sum();
        self.pending_tonic_resolution = false;
        self.modulate_to(destination);
        self.build_phrase();
    }
    /// Targets actually consumed, not queued previews, successes or elapsed time.
    /// A new generator starts at zero; history navigation never calls next_event.
    pub fn key_practice(&self) -> &BTreeMap<String, usize> {
        &self.key_practice
    }
    fn practice_count(&self, key: &Key) -> usize {
        *self.key_practice.get(&key.label()).unwrap_or(&0)
    }
    fn overpracticed(&self) -> bool {
        let minimum = self.key_practice.values().copied().min().unwrap_or(0);
        self.practice_count(&self.key).saturating_sub(minimum) > self.config.key_balance_tolerance
    }
    /// Already planned music only: inspecting a phrase never advances the RNG.
    pub(crate) fn pending_events(&self) -> impl Iterator<Item = &ChordEvent> {
        self.queue.iter()
    }
    fn push(
        &mut self,
        chord: Chord,
        degree: Option<u8>,
        role: &str,
        reason: String,
        previous_key: Option<Key>,
    ) {
        self.queue.push_back(ChordEvent {
            id: self.next_id,
            phrase: self.phrase,
            key: self.key.clone(),
            chord,
            degree,
            role: role.into(),
            reason,
            previous_key,
            cycle: None,
        });
        self.next_id += 1;
    }
    fn reachable_keys(&self) -> Vec<Key> {
        let mut candidates = Vec::new();
        for name in &self.config.keys {
            for mode in &self.config.modes {
                let key = Key {
                    tonic: Tone::parse(name).expect("validated key"),
                    mode: *mode,
                };
                if key.tonic.pc == self.key.tonic.pc && key.mode == self.key.mode {
                    continue;
                }
                // Modal center change: retain at least one sounding chord tone.
                let functional = modulation::functional(&key);
                let reachable = if functional {
                    !modulation::available_methods(&self.key, &key, &self.config.modulation_methods)
                        .is_empty()
                } else {
                    self.previous.as_ref().is_some_and(|c| {
                        c.pcs()
                            .iter()
                            .any(|p| key.chord(1, false).pcs().contains(p))
                    })
                };
                if reachable {
                    candidates.push(key);
                }
            }
        }
        candidates
    }
    fn select_new_key(&mut self, allow_return: bool) -> Option<Key> {
        let mut candidates = self.reachable_keys();
        let minimum = candidates
            .iter()
            .map(|key| self.practice_count(key))
            .min()?;
        if allow_return && !self.returned_last && self.config.modulation_return_probability > 0.0 {
            if let Some(previous) = &self.previous_key {
                if candidates.contains(previous)
                    && self.practice_count(previous).saturating_sub(minimum)
                        <= self.config.key_balance_tolerance
                    && self.rng.gen_bool(self.config.modulation_return_probability)
                {
                    return Some(previous.clone());
                }
            }
        }
        candidates.shuffle(&mut self.rng);
        candidates
            .into_iter()
            .min_by_key(|k| self.practice_count(k))
    }
    fn modulate(&mut self) -> bool {
        let Some(new_key) = self.select_new_key(true) else {
            return false;
        };
        self.modulate_to(new_key);
        true
    }
    fn modulate_to(&mut self, new_key: Key) {
        let old = self.key.clone();
        let returning = self.previous_key.as_ref() == Some(&new_key);
        self.returned_last = returning;
        self.previous_key = Some(old.clone());
        let method = modulation::available_methods(&old, &new_key, &self.config.modulation_methods)
            .choose(&mut self.rng)
            .copied();
        self.key = new_key;
        self.cycle_cursor = 0;
        self.cycle_lap = 1;
        self.phrases_in_key = 0;
        self.push_pivot(&old, method);
        let tonic = self.key.chord(1, false);
        if matches!(
            self.key.mode,
            Mode::Ionian | Mode::Aeolian | Mode::HarmonicMinor | Mode::MelodicMinor
        ) {
            self.push(
                tonic.secondary(),
                None,
                "bridge",
                format!(
                    "{}{} -> {}: prepare V7, resolve to new tonic (minor may raise degree 7)",
                    if returning { "Return: " } else { "" },
                    old.label(),
                    self.key.label()
                ),
                Some(old.clone()),
            );
        }
        let reason = if matches!(
            self.key.mode,
            Mode::Ionian | Mode::Aeolian | Mode::HarmonicMinor | Mode::MelodicMinor
        ) {
            if returning {
                "Return: previous tonic reached; continue in returned key".into()
            } else {
                "arrival: new tonic; continue in new key".into()
            }
        } else {
            format!(
                "{}{} -> {}: common-tone modal center shift; tonic-centered phrase follows (not V-I)",
                if returning { "Return: " } else { "" },
                old.label(),
                self.key.label()
            )
        };
        let same_tonic = old.tonic.pc == self.key.tonic.pc;
        let reason = if same_tonic {
            format!(
                "{}{} -> {}: same-tonic mode change",
                if returning { "Return: " } else { "" },
                old.label(),
                self.key.label()
            )
        } else {
            reason
        };
        self.push(
            tonic,
            Some(1),
            if same_tonic { "mode_change" } else { "arrival" },
            reason,
            Some(old),
        );
        if self.uses_cycle() {
            self.mark_cycle(0);
            self.cycle_cursor = 1; // the arrival already sounded the opening tonic
        }
    }
    fn push_pivot(&mut self, old: &Key, method: Option<ModulationMethod>) {
        match method {
            Some(ModulationMethod::SharedChord) => {
                let pivots = modulation::shared_chords(old, &self.key);
                // Prefer reinterpreting the chord just played, including its seventh.
                let preferred: Vec<_> = pivots
                    .iter()
                    .filter(|p| {
                        self.previous
                            .as_ref()
                            .is_some_and(|c| c.pcs() == p.chord.pcs())
                    })
                    .collect();
                let pivot = if preferred.is_empty() {
                    pivots
                        .choose(&mut self.rng)
                        .expect("validated shared route")
                } else {
                    *preferred
                        .choose(&mut self.rng)
                        .expect("nonempty preference")
                };
                self.push(
                    pivot.chord.clone(),
                    Some(pivot.new_degree),
                    "shared_pivot",
                    format!(
                        "Shared chord: old {} = new {}; then V7 -> tonic",
                        pivot.old_degree, pivot.new_degree
                    ),
                    Some(old.clone()),
                );
            }
            Some(ModulationMethod::Diminished) => {
                let source = modulation::leading_diminished(old);
                let destination = modulation::leading_diminished(&self.key);
                self.push(
                    destination.clone(),
                    Some(7),
                    "diminished_pivot",
                    format!(
                        "Dim7 chromatic: {} = {}; then V7 -> tonic",
                        source.symbol(),
                        destination.symbol()
                    ),
                    Some(old.clone()),
                );
            }
            Some(ModulationMethod::Dominant) | None => {}
        }
    }
    fn uses_cycle(&self) -> bool {
        self.config.progression == ProgressionKind::OriginalCycle
            && matches!(self.key.mode, Mode::Ionian | Mode::Aeolian)
    }
    fn mark_cycle(&mut self, index: usize) {
        self.queue.back_mut().expect("event just pushed").cycle = Some(CyclePosition {
            lap: self.cycle_lap,
            step: index + 1,
            total: self.templates.cycle.len(),
        });
    }
    fn degrees(&mut self) -> Vec<u8> {
        let options: Vec<Vec<u8>> = self
            .templates
            .templates
            .iter()
            .filter(|t| t.mode == self.key.mode)
            .flat_map(|t| t.phrases.clone())
            .collect();
        let minimum = options
            .iter()
            .map(|p| {
                *self
                    .phrase_visits
                    .get(&format!("{}:{p:?}", self.key.label()))
                    .unwrap_or(&0)
            })
            .min()
            .expect("validated templates");
        let candidates: Vec<_> = options
            .into_iter()
            .filter(|p| {
                *self
                    .phrase_visits
                    .get(&format!("{}:{p:?}", self.key.label()))
                    .unwrap_or(&0)
                    == minimum
            })
            .collect();
        let degrees = candidates.choose(&mut self.rng).expect("nonempty").clone();
        *self
            .phrase_visits
            .entry(format!("{}:{degrees:?}", self.key.label()))
            .or_default() += 1;
        degrees
    }
    fn extension(&mut self, target: &Chord, degree: u8) {
        if !self.config.extensions && !self.config.approaches {
            return;
        }
        let roll: f64 = self.rng.gen();
        let s = &self.config;
        let tonicizable = target.tonicizable();
        let single_end = s.secondary_probability + s.substitution_probability;
        let sd25_end = single_end + s.sd25_probability;
        let ssd25_end = sd25_end + s.ssd25_probability;
        if tonicizable && roll < s.secondary_probability {
            self.push(
                target.secondary(),
                None,
                "secondary",
                format!(
                    "V7/{degree} -> {}; tonicization, not modulation",
                    target.symbol()
                ),
                None,
            );
        } else if tonicizable && roll < s.secondary_probability + s.substitution_probability {
            self.push(
                target.substitute(),
                None,
                "substitute",
                format!(
                    "subV7/{degree} -> {}; tritone substitute, root a semitone above target",
                    target.symbol()
                ),
                None,
            );
        } else if tonicizable && roll < ssd25_end {
            let substitute = roll >= sd25_end;
            let [ii, dominant] = target
                .approach_ii_v(substitute)
                .expect("tonicizable target");
            let name = if substitute { "SSD25" } else { "SD25" };
            let reason = format!(
                "{name}: {} -> {} -> {} (degree {degree}); no key change",
                ii.symbol(),
                dominant.symbol(),
                target.symbol()
            );
            self.push(
                ii,
                None,
                if substitute { "ssd25_ii" } else { "sd25_ii" },
                reason.clone(),
                None,
            );
            self.push(
                dominant,
                None,
                if substitute { "ssd25_v" } else { "sd25_v" },
                reason,
                None,
            );
        } else if s.extensions
            && degree == 1
            && self.key.mode == Mode::Ionian
            && roll >= ssd25_end
            && roll < ssd25_end + s.borrow_probability
        {
            let parallel = Key {
                tonic: self.key.tonic.clone(),
                mode: Mode::Aeolian,
            };
            self.push(
                parallel.chord(4, false),
                Some(4),
                "borrowed",
                "minor iv from parallel Aeolian -> I".into(),
                None,
            );
        }
    }
    fn ambient_color(&mut self, chord: Chord) -> Chord {
        if !self.config.ambient || !self.rng.gen_bool(self.config.ambient_probability) {
            return chord;
        }
        let options = vec![
            (vec![(0, 0), (2, 1), (7, 4)], vec![1, 2, 5]),
            (vec![(0, 0), (5, 3), (7, 4)], vec![1, 4, 5]),
            (vec![(0, 0), (4, 2), (7, 4), (2, 1)], vec![1, 3, 5, 9]),
            (vec![(0, 0), (3, 2), (7, 4), (2, 1)], vec![1, 3, 5, 9]),
            (vec![(0, 0), (4, 2), (11, 6), (6, 3)], vec![1, 3, 7, 11]),
        ];
        let scale: Vec<u8> = self.key.scale().iter().map(|t| t.pc).collect();
        let choices: Vec<_> = options
            .into_iter()
            .map(|(ivs, degrees)| {
                Chord::from_tones(
                    ivs.iter()
                        .map(|(n, d)| chord.root.transpose(*n, *d))
                        .collect(),
                    degrees,
                )
            })
            .filter(|c| c.pcs().iter().all(|p| scale.contains(p)))
            .collect();
        choices.choose(&mut self.rng).cloned().unwrap_or(chord)
    }
    fn emit_degree(&mut self, degree: u8, next: Option<u8>, seventh: bool, blocked: bool) {
        let resolving = self.pending_tonic_resolution;
        self.pending_tonic_resolution = false;
        let dominant = self.key.mode == Mode::Aeolian
            && degree == 5
            && next == Some(1)
            && self.config.minor_dominant_probability > 0.0
            && self.rng.gen_bool(self.config.minor_dominant_probability);
        let base = self.key.chord(degree, seventh);
        let chord = if dominant {
            self.key.chord(1, false).secondary()
        } else if resolving {
            base
        } else {
            self.ambient_color(base)
        };
        // Keep explicit V7 -> I/i adjacent, including across preview chunks. The tonic
        // must not be replaced by a color or another inserted approach.
        let starts_resolution = degree == 5 && next == Some(1) && chord.quality == "7";
        if !resolving && !starts_resolution && self.next_id > 0 {
            self.extension(&chord, degree);
        }
        let role = if dominant {
            "minor_dominant"
        } else {
            "diatonic"
        };
        let reason = if dominant {
            "Minor V7 -> i: raised leading tone; key remains minor"
        } else if blocked {
            "No supported modulation path in configured pool; staying in current key"
        } else if self.uses_cycle() {
            "Original degree cycle; preserve ordered backbone transitions"
        } else {
            "Modal phrase / color; keep the tonal center"
        };
        self.push(chord, Some(degree), role, reason.into(), None);
        self.pending_tonic_resolution = starts_resolution;
    }
    fn build_cycle_chunk(&mut self, seventh: bool, blocked: bool) {
        if self.cycle_cursor == self.templates.cycle.len() {
            self.cycle_cursor = 1; // share the closing/opening tonic, not 1 -> 1
            self.cycle_lap += 1;
        }
        let end =
            (self.cycle_cursor + self.config.cycle_chunk_size).min(self.templates.cycle.len());
        for index in self.cycle_cursor..end {
            let degree = self.templates.cycle[index];
            let next = self.templates.cycle.get(index + 1).copied();
            self.emit_degree(degree, next, seventh, blocked);
            self.mark_cycle(index);
        }
        self.cycle_cursor = end;
    }
    fn build_phrase(&mut self) {
        let boundary = !self.uses_cycle() || self.cycle_cursor == self.templates.cycle.len();
        let blocked = self.manual.is_none()
            && boundary
            && self.phrases_in_key >= self.config.minimum_phrases_in_key
            && self.config.modulation_probability > 0.0
            && (self.overpracticed() || self.rng.gen_bool(self.config.modulation_probability))
            && !self.modulate();
        if self.uses_cycle() {
            let seventh = self.rng.gen_bool(self.config.seventh_probability);
            self.build_cycle_chunk(seventh, blocked);
        } else {
            let degrees = self.degrees();
            let seventh = self.rng.gen_bool(self.config.seventh_probability);
            for (index, degree) in degrees.iter().enumerate() {
                self.emit_degree(*degree, degrees.get(index + 1).copied(), seventh, blocked);
            }
        }
        self.phrase += 1;
        self.phrases_in_key += 1;
    }
}

//! Non-realtime planner. The existing UTRP engine remains the only harmony source.
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use serde::Deserialize;
use std::{collections::VecDeque, ffi::c_char};
mod labels;
#[cfg(test)]
mod presentation_tests;
use utrp::{
    config::{Config, Templates},
    progression::{ChordEvent, Progression},
    theory::tone::Tone,
};

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    low: u8,
    high: u8,
    max_span: u8,
    max_step: f64,
    phrase_min: usize,
    phrase_max: usize,
    coverage_weight: f64,
    common_weight: f64,
    jitter: f64,
    hold_weight: u32,
    rise_weight: u32,
    fall_weight: u32,
    modulation_check_interval: usize,
    pub answer_seconds: u32,
    pub demo_seconds: u32,
    pub panel_width: u32,
}
impl Settings {
    fn load() -> Option<Self> {
        let s: Self = toml::from_str(include_str!("game.toml")).ok()?;
        (s.low >= 40
            && s.high <= 81
            && u16::from(s.low) + u16::from(s.max_span) <= u16::from(s.high)
            && s.max_span <= 12
            && s.max_step.is_finite()
            && s.max_step > 0.0
            && s.phrase_min > 0
            && s.phrase_min <= s.phrase_max
            && s.coverage_weight.is_finite()
            && s.coverage_weight >= 0.0
            && s.common_weight.is_finite()
            && s.common_weight >= 0.0
            && s.jitter.is_finite()
            && s.jitter > 0.0
            && u64::from(s.hold_weight) + u64::from(s.rise_weight) + u64::from(s.fall_weight) > 0
            && s.modulation_check_interval > 0
            && (1..=120).contains(&s.answer_seconds)
            && (1..=10).contains(&s.demo_seconds)
            && (280..=480).contains(&s.panel_width))
        .then_some(s)
    }
}

#[repr(C)]
#[derive(Clone, Debug, PartialEq)]
pub struct Target {
    pub id: u32,
    pub count: u32,
    pub notes: [i32; 5],
    pub roles: [i32; 5],
    pub letters: [i32; 5],
    pub scale: [i32; 7],
    pub scale_letters: [i32; 7],
    pub tonic: i32,
    pub signature: i32,
    pub minor: i32,
    pub root: i32,
    pub root_letter: i32,
    pub quality: i32,
    pub degree: i32,
    pub movement: i32,
    pub phrase: u32,
    pub label: [c_char; 96],
    pub key_label: [c_char; 64],
    pub reason: [c_char; 256],
    pub visit: u32,
    pub backbone: u32,
    pub action: [c_char; 48],
    pub route: [c_char; 128],
    pub group: u32,
    pub kind: u32,
    pub palette_role: i32,
    pub capsule: [c_char; 64],
    pub bass: [c_char; 32],
}
fn copy_text<const N: usize>(dest: &mut [c_char; N], text: &str) {
    let mut end = text.len().min(N - 1);
    while !text.is_char_boundary(end) {
        end -= 1;
    }
    for (out, byte) in dest.iter_mut().zip(text.as_bytes()[..end].iter()) {
        *out = *byte as c_char;
    }
}
fn letter(tone: &Tone) -> i32 {
    "CDEFGAB"
        .find(tone.name.chars().next().expect("validated tone"))
        .expect("validated letter") as i32
}
fn mean(notes: &[u8]) -> f64 {
    notes.iter().map(|n| f64::from(*n)).sum::<f64>() / notes.len() as f64
}
fn candidates(event: &ChordEvent, s: &Settings) -> Vec<Vec<u8>> {
    let mut pcs = event.chord.pcs();
    pcs.sort_unstable();
    pcs.dedup();
    (s.low..=s.high)
        .filter(|bass| pcs.contains(&(bass % 12)))
        .filter_map(|bass| {
            let mut notes: Vec<_> = pcs
                .iter()
                .map(|pc| bass + (*pc + 12 - bass % 12) % 12)
                .collect();
            notes.sort_unstable();
            (notes
                .last()
                .is_some_and(|n| *n <= s.high && n - bass <= s.max_span))
            .then_some(notes)
        })
        .collect()
}

// Match the existing capsule's canonical major-key spelling, including its
// relative minor. This changes notation only, never harmony or MIDI pitches.
fn canonical_tonic(key: &utrp::theory::key::Key) -> Tone {
    let minor = key.mode == utrp::theory::key::Mode::Aeolian;
    let signature = (key.tonic.pc + if minor { 3 } else { 0 }) % 12;
    let major = Tone::parse(
        [
            "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
        ][signature as usize],
    )
    .expect("constant key");
    if minor {
        major.transpose(9, 5)
    } else {
        major
    }
}
fn canonical_spelling(event: &mut ChordEvent) {
    let tonic = canonical_tonic(&event.key);
    if let Some(old) = &mut event.previous_key {
        old.tonic = canonical_tonic(old);
    }
    let shift = (letter(&tonic) - letter(&event.key.tonic)).rem_euclid(7);
    let respell = |tone: &Tone| {
        let index = (letter(tone) + shift).rem_euclid(7) as usize;
        let delta = (i32::from(tone.pc) - [0, 2, 4, 5, 7, 9, 11][index] + 6).rem_euclid(12) - 6;
        let accidental = if delta < 0 {
            "b".repeat((-delta) as usize)
        } else {
            "#".repeat(delta as usize)
        };
        Tone {
            pc: tone.pc,
            name: format!("{}{accidental}", ["C", "D", "E", "F", "G", "A", "B"][index]),
        }
    };
    event.chord.tones = event.chord.tones.iter().map(respell).collect();
    event.chord.root = respell(&event.chord.root);
    event.key.tonic = tonic;
}

pub struct Planner {
    engine: Progression,
    rng: ChaCha8Rng,
    settings: Settings,
    previous: Vec<u8>,
    visits: [u32; 128],
    movement: i32,
    remaining: usize,
    direction: i32,
    issued: VecDeque<ChordEvent>,
    last_key: Option<String>,
    visit: u32,
}
impl Planner {
    pub fn new(seed: u64) -> Option<Self> {
        let mut config = Config::load(None).ok()?;
        // Fixed compact sevenths: capsule + bass uniquely defines the answer.
        config.simulation.extensions = false;
        config.simulation.ambient = false;
        let settings = Settings::load()?;
        let mut engine =
            Progression::new(config.simulation, Templates::load(None).ok()?, seed).ok()?;
        engine
            .enable_seventh_practice(settings.modulation_check_interval)
            .ok()?;
        Some(Self {
            engine,
            rng: ChaCha8Rng::seed_from_u64(seed ^ 0x766f6963696e67),
            settings,
            previous: Vec::new(),
            visits: [0; 128],
            movement: 0,
            remaining: 0,
            direction: 2,
            issued: VecDeque::new(),
            last_key: None,
            visit: 0,
        })
    }
    fn choose(&mut self, event: &ChordEvent) -> Option<Vec<u8>> {
        let all = candidates(event, &self.settings);
        if self.remaining == 0 {
            let total = u64::from(self.settings.hold_weight)
                + u64::from(self.settings.rise_weight)
                + u64::from(self.settings.fall_weight);
            let roll = self.rng.gen_range(0..total);
            self.movement = if self.direction != 2 {
                self.direction
            } else if roll < u64::from(self.settings.hold_weight) {
                0
            } else if roll
                < u64::from(self.settings.hold_weight) + u64::from(self.settings.rise_weight)
            {
                1
            } else {
                -1
            };
            self.remaining = self
                .rng
                .gen_range(self.settings.phrase_min..=self.settings.phrase_max);
        }
        self.remaining -= 1;
        let previous = &self.previous;
        let mut nearby: Vec<_> = all
            .iter()
            .filter(|n| {
                previous.is_empty() || (mean(n) - mean(previous)).abs() <= self.settings.max_step
            })
            .collect();
        if nearby.is_empty() {
            return None;
        } // Never jump silently across the range.
        let directional = |notes: &&Vec<u8>, direction: i32| {
            previous.is_empty()
                || direction == 0
                || (mean(notes) - mean(previous)) * f64::from(direction) > 0.0
        };
        if !nearby.iter().any(|n| directional(n, self.movement)) {
            self.movement = -self.movement;
        }
        nearby.retain(|n| directional(n, self.movement));
        let mut best = None;
        for notes in nearby {
            let motion = if previous.is_empty() {
                0.0
            } else {
                notes
                    .iter()
                    .zip(previous)
                    .map(|(n, p)| f64::from(n.abs_diff(*p)))
                    .sum::<f64>()
                    / notes.len() as f64
            };
            let common = notes.iter().filter(|n| previous.contains(n)).count() as f64;
            let coverage = notes
                .iter()
                .map(|n| self.visits[*n as usize] as f64)
                .sum::<f64>()
                / notes.len() as f64;
            let cost = motion - common * self.settings.common_weight
                + coverage * self.settings.coverage_weight
                + self.rng.gen_range(0.0..self.settings.jitter);
            if best.as_ref().is_none_or(|(old, _)| cost < *old) {
                best = Some((cost, notes.clone()));
            }
        }
        let notes = best?.1;
        for n in &notes {
            self.visits[*n as usize] += 1;
        }
        self.previous = notes.clone();
        Some(notes)
    }
    pub fn configure(&mut self, probability: f64, direction: i32, approaches: bool) -> bool {
        if !(-1..=2).contains(&direction) || !self.issued.is_empty() || self.last_key.is_some() {
            return false;
        }
        if self
            .engine
            .configure_practice(probability, approaches)
            .is_err()
        {
            return false;
        }
        self.direction = direction;
        true
    }
    pub fn complete(&mut self, id: u32, success: bool) -> bool {
        if self.issued.front().is_none_or(|e| e.id != id as usize) {
            return false;
        }
        let event = self.issued.pop_front().expect("checked front");
        self.engine.acknowledge_practice(&event, success);
        true
    }
    pub fn next_target(&mut self) -> Option<Target> {
        if self.issued.len() >= 12 {
            return None;
        }
        let mut event = self.engine.next_event();
        let mut resolution = if event.cycle.is_some() {
            event.clone()
        } else {
            self.engine.pending_resolution()?.clone()
        };
        // Keep original engine spelling for acknowledgement and balance identity.
        self.issued.push_back(event.clone());
        let identity = event.key.label();
        if self.last_key.as_ref() != Some(&identity) {
            self.visit += 1;
            self.last_key = Some(identity);
        }
        canonical_spelling(&mut event);
        canonical_spelling(&mut resolution);
        let notes = self.choose(&event)?;
        target_from_event(&event, &resolution, &notes, self.movement, self.visit)
    }
}

fn target_from_event(
    event: &ChordEvent,
    resolution: &ChordEvent,
    notes: &[u8],
    movement: i32,
    visit: u32,
) -> Option<Target> {
    let minor = event.key.mode == utrp::theory::key::Mode::Aeolian;
    let mut out = Target {
        id: u32::try_from(event.id).ok()?,
        count: notes.len() as u32,
        notes: [-1; 5],
        roles: [-1; 5],
        letters: [-1; 5],
        scale: [0; 7],
        scale_letters: [0; 7],
        tonic: event.key.tonic.pc as i32,
        signature: ((event.key.tonic.pc + if minor { 3 } else { 0 }) % 12) as i32,
        minor: i32::from(minor),
        root: event.chord.root.pc as i32,
        root_letter: letter(&event.chord.root),
        quality: [
            "", "m", "dim", "aug", "maj7", "m7", "7", "m7b5", "dim7", "mMaj7", "maj7#5", "7#5",
            "dimMaj7",
        ]
        .iter()
        .position(|q| *q == event.chord.quality)? as i32,
        degree: event.degree.map_or(-1, |d| i32::from(d) - 1),
        movement,
        phrase: event.phrase as u32,
        label: [0; 96],
        key_label: [0; 64],
        reason: [0; 256],
        visit,
        backbone: u32::from(event.cycle.is_some()),
        action: [0; 48],
        route: [0; 128],
        group: u32::try_from(resolution.id).ok()?,
        kind: labels::kind(event),
        palette_role: 0,
        capsule: [0; 64],
        bass: [0; 32],
    };
    for (i, note) in notes.iter().enumerate() {
        let index = event.chord.tones.iter().position(|t| t.pc == note % 12)?;
        out.notes[i] = i32::from(*note);
        out.roles[i] = index as i32;
        out.letters[i] = letter(&event.chord.tones[index]);
    }
    for (i, tone) in event.key.scale().iter().enumerate() {
        out.scale[i] = i32::from(tone.pc);
        out.scale_letters[i] = letter(tone);
    }
    fill_labels(&mut out, event, resolution, notes[0]);
    Some(out)
}

fn fill_labels(out: &mut Target, event: &ChordEvent, resolution: &ChordEvent, bass_note: u8) {
    let bass = &event.chord.tones[out.roles[0] as usize];
    let natural = [0, 2, 4, 5, 7, 9, 11][letter(bass) as usize];
    let accidental = (i32::from(bass.pc) - natural + 6).rem_euclid(12) - 6;
    let octave = (i32::from(bass_note) - natural - accidental) / 12 - 1;
    let (capsule, role) = labels::capsule(event, resolution);
    out.palette_role = role;
    copy_text(&mut out.capsule, &capsule);
    copy_text(
        &mut out.bass,
        &format!(
            "{}{octave}({})",
            bass.name,
            event.chord.degree_label(out.roles[0] as usize)
        ),
    );
    copy_text(
        &mut out.label,
        &format!(
            "{} {}/{}{octave}({})",
            labels::degree(event),
            event.chord.symbol(),
            bass.name,
            event.chord.degree_label(out.roles[0] as usize)
        ),
    );
    copy_text(&mut out.key_label, &event.key.label());
    copy_text(&mut out.reason, &event.reason);
    copy_text(&mut out.action, labels::action(event));
    let route = event.previous_key.as_ref().map_or_else(
        || format!("{} | no key change", event.key.label()),
        |old| format!("{} -> {}", old.label(), event.key.label()),
    );
    copy_text(&mut out.route, &route);
}

// C ABI only. All allocation and harmonic planning stays on the editor thread.
#[no_mangle]
pub extern "C" fn chordlab_game_new(seed: u64) -> *mut Planner {
    std::panic::catch_unwind(|| {
        Planner::new(seed).map_or(std::ptr::null_mut(), |p| Box::into_raw(Box::new(p)))
    })
    .unwrap_or(std::ptr::null_mut())
}
/// # Safety
/// `planner` must be a live pointer returned by chordlab_game_new, freed exactly once.
#[no_mangle]
pub unsafe extern "C" fn chordlab_game_free(planner: *mut Planner) {
    if !planner.is_null() {
        drop(Box::from_raw(planner));
    }
}
/// # Safety
/// Both pointers must be valid and exclusively owned for this call.
#[no_mangle]
pub unsafe extern "C" fn chordlab_game_next(planner: *mut Planner, target: *mut Target) -> bool {
    if planner.is_null() || target.is_null() {
        return false;
    }
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let Some(next) = (*planner).next_target() else {
            return false;
        };
        *target = next;
        true
    }))
    .unwrap_or(false)
}

/// # Safety
/// `planner` must be a live, exclusively owned planner. Call before issuing targets.
#[no_mangle]
pub unsafe extern "C" fn chordlab_game_configure(
    planner: *mut Planner,
    probability: f64,
    direction: i32,
    approaches: bool,
) -> bool {
    if planner.is_null() {
        return false;
    }
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        (*planner).configure(probability, direction, approaches)
    }))
    .unwrap_or(false)
}

/// # Safety
/// `planner` must be live and exclusively owned. Acknowledge presented targets in order.
#[no_mangle]
pub unsafe extern "C" fn chordlab_game_complete(
    planner: *mut Planner,
    id: u32,
    success: bool,
) -> bool {
    if planner.is_null() {
        return false;
    }
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        (*planner).complete(id, success)
    }))
    .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reproducible_bounded_connected_coverage() {
        for seed in 0..8 {
            let mut a = Planner::new(seed).unwrap();
            let mut b = Planner::new(seed).unwrap();
            let mut last = Vec::new();
            let mut seen = [false; 128];
            for _ in 0..1500 {
                let t = a
                    .next_target()
                    .expect("all harmonic events have a playable target");
                assert_eq!(Some(t.clone()), b.next_target());
                assert_eq!(t.count, 4);
                let n: Vec<_> = t.notes[..t.count as usize]
                    .iter()
                    .map(|n| *n as u8)
                    .collect();
                assert!(n.windows(2).all(|w| w[0] < w[1]));
                assert!(n[0] >= 40 && *n.last().unwrap() <= 81 && n.last().unwrap() - n[0] <= 12);
                if !last.is_empty() {
                    assert!((mean(&n) - mean(&last)).abs() <= a.settings.max_step);
                }
                for pitch in &n {
                    seen[*pitch as usize] = true;
                }
                last = n;
                assert!(a.complete(t.id, true));
                assert!(b.complete(t.id, true));
            }
            assert!(
                seen[40..82].iter().all(|v| *v),
                "range coverage seed {seed}"
            );
        }
    }
    #[test]
    fn ffi_invalid_inputs_fail() {
        assert_eq!(std::mem::size_of::<Target>(), 868);
        unsafe {
            assert!(!chordlab_game_next(
                std::ptr::null_mut(),
                std::ptr::null_mut()
            ));
            chordlab_game_free(std::ptr::null_mut());
        }
    }

    #[test]
    fn committed_preview_acknowledges_once_in_order() {
        let mut p = Planner::new(42).unwrap();
        assert!(!p.configure(f64::NAN, 2, true));
        assert!(!p.configure(0.5, 3, true));
        assert!(p.configure(1.0, 2, true));
        let mut queue: VecDeque<_> = (0..3).map(|_| p.next_target().unwrap()).collect();
        assert!(!p.configure(0.0, 0, false));
        for index in 0..600 {
            let t = queue.pop_front().unwrap();
            assert!(!p.complete(queue[0].id, true));
            assert!(p.complete(t.id, index % 5 != 0));
            assert!(!p.complete(t.id, true));
            assert_eq!(p.issued.front().unwrap().id, queue[0].id as usize);
            assert_eq!(t.count, 4);
            queue.push_back(p.next_target().unwrap());
        }
    }

    #[test]
    fn bounded_unacknowledged_queue() {
        let mut p = Planner::new(0).unwrap();
        for _ in 0..12 {
            assert!(p.next_target().is_some());
        }
        assert!(p.next_target().is_none());
    }
}

//! Non-realtime planner. The existing UTRP engine remains the only harmony source.
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use serde::Deserialize;
use std::ffi::c_char;
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
fn canonical_spelling(event: &mut ChordEvent) {
    let minor = event.key.mode == utrp::theory::key::Mode::Aeolian;
    let signature = (event.key.tonic.pc + if minor { 3 } else { 0 }) % 12;
    let major = Tone::parse(
        [
            "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
        ][signature as usize],
    )
    .expect("constant key");
    let tonic = if minor { major.transpose(9, 5) } else { major };
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
}
impl Planner {
    pub fn new(seed: u64) -> Option<Self> {
        let mut config = Config::load(None).ok()?;
        // Fixed compact triads/sevenths: capsule + bass uniquely defines the answer.
        config.simulation.extensions = false;
        config.simulation.ambient = false;
        Some(Self {
            engine: Progression::new(config.simulation, Templates::load(None).ok()?, seed).ok()?,
            rng: ChaCha8Rng::seed_from_u64(seed ^ 0x766f6963696e67),
            settings: Settings::load()?,
            previous: Vec::new(),
            visits: [0; 128],
            movement: 0,
            remaining: 0,
        })
    }
    fn choose(&mut self, event: &ChordEvent) -> Option<Vec<u8>> {
        let all = candidates(event, &self.settings);
        if self.remaining == 0 {
            self.movement = self.rng.gen_range(-1..=1);
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
                    .map(|n| previous.iter().map(|p| n.abs_diff(*p)).min().unwrap_or(0) as f64)
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
    pub fn next_target(&mut self) -> Option<Target> {
        let mut event = self.engine.next_event();
        canonical_spelling(&mut event);
        let notes = self.choose(&event)?;
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
            movement: self.movement,
            phrase: event.phrase as u32,
            label: [0; 96],
            key_label: [0; 64],
            reason: [0; 256],
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
        let bass = &event.chord.tones[out.roles[0] as usize];
        let natural = [0, 2, 4, 5, 7, 9, 11][letter(bass) as usize];
        let accidental = (i32::from(bass.pc) - natural + 6).rem_euclid(12) - 6;
        let octave = (i32::from(notes[0]) - natural - accidental) / 12 - 1;
        copy_text(
            &mut out.label,
            &format!("{}/{}{octave}", event.chord.symbol(), bass.name),
        );
        copy_text(&mut out.key_label, &event.key.label());
        copy_text(&mut out.reason, &event.reason);
        Some(out)
    }
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
            }
            assert!(
                seen[40..82].iter().all(|v| *v),
                "range coverage seed {seed}"
            );
        }
    }
    #[test]
    fn ffi_invalid_inputs_fail() {
        assert_eq!(std::mem::size_of::<Target>(), 576);
        unsafe {
            assert!(!chordlab_game_next(
                std::ptr::null_mut(),
                std::ptr::null_mut()
            ));
            chordlab_game_free(std::ptr::null_mut());
        }
    }
}

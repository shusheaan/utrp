use crate::Pattern;
use std::collections::BTreeMap;
const PPQ: u32 = 960;

pub fn quantized_beat(beat: f64, grid: u32, strength: f64, total: f64) -> f64 {
    if grid == 0 {
        return beat;
    }
    // The last event belongs to this loop, never to the first tick of the next one.
    let target = (beat * grid as f64).round().min(total * grid as f64 - 1.0) / grid as f64;
    beat + (target - beat) * strength
}
fn vlq(mut n: u32, out: &mut Vec<u8>) {
    let mut bytes = [0u8; 4];
    let mut i = 3;
    bytes[i] = (n & 0x7f) as u8;
    while {
        n >>= 7;
        n != 0
    } {
        i -= 1;
        bytes[i] = (n as u8 & 0x7f) | 0x80;
    }
    out.extend_from_slice(&bytes[i..]);
}

pub fn midi_file(pattern: &Pattern) -> Result<Vec<u8>, String> {
    pattern.validate()?;
    let mut track = vec![0, 0xff, 0x51, 3];
    let tempo = (60_000_000.0 / pattern.bpm).round() as u32;
    track.extend_from_slice(&tempo.to_be_bytes()[1..]);
    track.extend_from_slice(&[0, 0xff, 0x58, 4, 4, 2, 24, 8]);
    let end = pattern.bars * 4 * PPQ;
    // Same mapped note on the same tick merges deterministically, maximum velocity wins.
    let mut notes: BTreeMap<(u32, u8), u8> = BTreeMap::new();
    for e in pattern
        .events
        .iter()
        .filter(|e| (e.class as usize) < pattern.notes.len())
    {
        let beat = quantized_beat(
            e.beat,
            pattern.grid,
            pattern.strength,
            pattern.bars as f64 * 4.0,
        );
        let tick = ((beat * PPQ as f64).round() as u32).min(end - 1);
        notes
            .entry((tick, pattern.notes[e.class as usize]))
            .and_modify(|v| *v = (*v).max(e.velocity))
            .or_insert(e.velocity);
    }
    let mut messages = Vec::new();
    let ordered: Vec<_> = notes.into_iter().collect();
    for (index, ((tick, note), velocity)) in ordered.iter().enumerate() {
        let next_same = ordered[index + 1..]
            .iter()
            .find(|((_, n), _)| n == note)
            .map(|((t, _), _)| *t)
            .unwrap_or(end);
        let off = (*tick + PPQ / 8).min(next_same).min(end);
        messages.push((*tick, 1u8, [0x99, *note, *velocity]));
        messages.push((off, 0u8, [0x89, *note, 0]));
    }
    messages.sort_unstable(); // Note-off before note-on on equal ticks.
    let mut time = 0;
    for (tick, _, message) in messages {
        vlq(tick - time, &mut track);
        track.extend_from_slice(&message);
        time = tick;
    }
    vlq(end - time, &mut track);
    track.extend_from_slice(&[0xff, 0x2f, 0]);
    let mut out = b"MThd\0\0\0\x06\0\0\0\x01".to_vec();
    out.extend_from_slice(&(PPQ as u16).to_be_bytes());
    out.extend_from_slice(b"MTrk");
    out.extend_from_slice(&(track.len() as u32).to_be_bytes());
    out.extend(track);
    Ok(out)
}

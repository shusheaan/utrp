//! Generate deterministic synthetic test audio (NOT a real beatbox accuracy benchmark).
use beatlab_engine::{Options, analyze, midi_file};
use std::{fs, path::PathBuf};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let destination = PathBuf::from(
        std::env::args()
            .nth(1)
            .ok_or("Usage: demo OUTPUT_DIRECTORY")?,
    );
    fs::create_dir_all(&destination)?;
    let rate = 48000u32;
    let mut audio = vec![0.0f32; rate as usize * 8];
    let mut seed = 42u32;
    for step in 0..64 {
        let start = step * 6000;
        let mut last = 0.0;
        for i in 0..4000 {
            let t = i as f64 / rate as f64;
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            let n = seed as f64 / u32::MAX as f64 * 2.0 - 1.0;
            let value = match step % 4 {
                0 => (std::f64::consts::TAU * 85.0 * t).sin() * (-t * 60.0).exp(),
                2 => n * (-t * 80.0).exp(),
                _ => (n - last) * (-t * 170.0).exp() * 0.5,
            };
            last = n;
            audio[start + i] = value as f32 * 0.7;
        }
    }
    let pattern = analyze(
        &audio,
        rate,
        &Options {
            bpm: 120.0,
            bars: 4,
            gate_db: -36.0,
        },
    )?;
    fs::write(
        destination.join("demo.json"),
        serde_json::to_string_pretty(&pattern)?,
    )?;
    fs::write(destination.join("demo.mid"), midi_file(&pattern)?)?;
    let size = (audio.len() * 2) as u32;
    let mut wav = Vec::new();
    wav.extend_from_slice(b"RIFF");
    wav.extend_from_slice(&(36 + size).to_le_bytes());
    wav.extend_from_slice(b"WAVEfmt ");
    wav.extend_from_slice(&16u32.to_le_bytes());
    wav.extend_from_slice(&1u16.to_le_bytes());
    wav.extend_from_slice(&1u16.to_le_bytes());
    wav.extend_from_slice(&rate.to_le_bytes());
    wav.extend_from_slice(&(rate * 2).to_le_bytes());
    wav.extend_from_slice(&2u16.to_le_bytes());
    wav.extend_from_slice(&16u16.to_le_bytes());
    wav.extend_from_slice(b"data");
    wav.extend_from_slice(&size.to_le_bytes());
    for sample in audio {
        wav.extend_from_slice(&((sample * 32767.0) as i16).to_le_bytes());
    }
    fs::write(destination.join("demo.wav"), wav)?;
    println!("{} synthetic events exported", pattern.events.len());
    Ok(())
}

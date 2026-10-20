use crate::{Event, Options, Pattern, features};

fn onsets(samples: &[f32], rate: u32, gate: f64) -> Vec<usize> {
    let hop = (rate as usize / 200).max(1); // 5 ms timing resolution before refinement.
    let rms: Vec<f64> = samples
        .chunks(hop)
        .map(|s| (s.iter().map(|x| (*x as f64).powi(2)).sum::<f64>() / s.len() as f64).sqrt())
        .collect();
    // Gate is the user's absolute RMS threshold. A whole-take noise estimate can
    // mistake dense playing for noise and silently defeat the Gate control.
    let threshold = gate;
    let mut result: Vec<usize> = Vec::new();
    let (mut previous, mut envelope) = (0.0_f64, 0.0_f64);
    for (frame, value) in rms.iter().copied().enumerate() {
        let onset = value > threshold
            && value > previous * 1.65
            && (previous < threshold || value > envelope * 1.35);
        let start = frame * hop;
        if onset
            && result
                .last()
                .is_none_or(|last| start.saturating_sub(*last) >= rate as usize * 45 / 1000)
        {
            let offset = samples[start..(start + hop).min(samples.len())]
                .iter()
                .position(|x| (*x as f64).abs() > threshold * 0.5)
                .unwrap_or(0);
            result.push(start + offset);
        }
        previous = value;
        envelope = (envelope * 0.9).max(value);
    }
    result
}

pub fn analyze(samples: &[f32], rate: u32, options: &Options) -> Result<Pattern, String> {
    options.validate()?;
    if !(8_000..=192_000).contains(&rate)
        || samples.is_empty()
        || samples.len() > rate as usize * 60
        || samples.iter().any(|s| !s.is_finite() || s.abs() > 8.0)
    {
        return Err("Expected finite mono audio, 8..192 kHz, up to 60 seconds".into());
    }
    let duration = options.bars as f64 * 4.0 * 60.0 / options.bpm;
    let samples = &samples[..samples.len().min((duration * rate as f64).ceil() as usize)];
    // Remove constant capture bias only in the analysis copy. Preserve source
    // samples and their indices for waveform, audition, state and MIDI timing.
    let mean = samples.iter().map(|s| *s as f64).sum::<f64>() / samples.len() as f64;
    let centered: Vec<f32> = samples.iter().map(|s| (*s as f64 - mean) as f32).collect();
    let samples = centered.as_slice();
    let positions = onsets(samples, rate, 10.0_f64.powf(options.gate_db / 20.0));
    if positions.len() > 2048 {
        return Err("Too many onsets; raise the gate or shorten the take".into());
    }
    let features: Vec<_> = positions
        .iter()
        .map(|i| features::extract(&samples[*i..], rate))
        .collect();
    let groups = features::cluster(&features);
    let events = positions
        .iter()
        .zip(groups)
        .map(|(i, (class, confidence))| {
            let end = (*i + rate as usize / 25).min(samples.len());
            let peak = samples[*i..end]
                .iter()
                .map(|x| x.abs())
                .fold(0.0_f32, f32::max);
            Event {
                beat: *i as f64 / rate as f64 * options.bpm / 60.0,
                source_sample: *i as u64,
                class,
                velocity: (peak.sqrt() * 110.0).round().clamp(1.0, 127.0) as u8,
                confidence,
            }
        })
        .collect();
    let pattern = Pattern {
        version: 2,
        bpm: options.bpm,
        bars: options.bars,
        sample_rate: rate,
        notes: vec![36, 38, 42, 39],
        grid: 0,
        strength: 1.0,
        events,
    };
    pattern.validate()?;
    Ok(pattern)
}

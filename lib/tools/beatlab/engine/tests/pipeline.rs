use beatlab_engine::{Event, Options, Pattern, analyze, midi_file, quantized_beat};

fn synthetic(rate: u32, bpm: f64, bars: u32) -> Vec<f32> {
    let mut audio = vec![0.0; (bars as f64 * 4.0 * 60.0 / bpm * rate as f64) as usize];
    let mut random = 42u32;
    for step in 0..bars * 16 {
        let offset = (step as f64 / 4.0 * 60.0 / bpm * rate as f64) as usize;
        let mut previous = 0.0;
        for i in 0..rate / 12 {
            let t = i as f64 / rate as f64;
            random = random.wrapping_mul(1664525).wrapping_add(1013904223);
            let noise = random as f64 / u32::MAX as f64 * 2.0 - 1.0;
            let value = match step % 4 {
                0 => (std::f64::consts::TAU * 85.0 * t).sin() * (-t * 60.0).exp(),
                2 => noise * (-t * 80.0).exp(),
                _ => (noise - previous) * (-t * 170.0).exp() * 0.5,
            };
            previous = noise;
            if offset + (i as usize) < audio.len() {
                audio[offset + i as usize] += value as f32 * 0.7;
            }
        }
    }
    audio
}
fn options() -> Options {
    Options {
        bpm: 120.0,
        bars: 2,
        gate_db: -36.0,
    }
}
fn pattern() -> Pattern {
    Pattern {
        version: 1,
        bpm: 120.0,
        bars: 2,
        sample_rate: 48000,
        notes: vec![36, 38, 42],
        grid: 4,
        strength: 1.0,
        events: vec![Event {
            beat: 0.1,
            source_sample: 0,
            class: 0,
            velocity: 100,
            confidence: 0.8,
        }],
    }
}

#[test]
fn onset_timing_and_grouping_on_unseen_synthetic_hits() {
    for rate in [8000, 44100, 48000, 96000] {
        for bpm in [60.0, 120.0, 180.0] {
            let input = synthetic(rate, bpm, 2);
            let out = analyze(&input, rate, &Options { bpm, ..options() }).unwrap();
            assert_eq!(
                out.events.len(),
                32,
                "rate={rate}, bpm={bpm}: {:?}",
                out.events
            );
            for (i, event) in out.events.iter().enumerate() {
                let error_seconds = (event.beat - i as f64 / 4.0).abs() * 60.0 / bpm;
                assert!(
                    error_seconds < 0.012,
                    "{rate} {bpm} event {i}: {error_seconds}"
                );
            }
            let first = &out.events;
            assert_ne!(first[0].class, first[2].class);
            assert_ne!(first[0].class, first[1].class);
            // Noise changes per hit: tests are not just identical repeated waveforms.
            assert!(first.iter().filter(|e| e.class == 4).count() < 4);
        }
    }
}
#[test]
fn silence_has_no_events() {
    assert!(
        analyze(&vec![0.0; 48000], 48000, &options())
            .unwrap()
            .events
            .is_empty()
    );
    assert!(
        analyze(&vec![0.0001; 48000], 48000, &options())
            .unwrap()
            .events
            .is_empty()
    );
}

#[test]
fn quiet_hits_remain_detectable_with_microphone_dc_bias() {
    for rate in [8000, 44100, 48000, 96000] {
        let quiet: Vec<f32> = synthetic(rate, 120.0, 2).iter().map(|x| x * 0.05).collect();
        let config = Options {
            gate_db: -48.0,
            ..options()
        };
        let reference = analyze(&quiet, rate, &config).unwrap();
        assert_eq!(reference.events.len(), 32);
        for bias in [-0.03, 0.008, 0.03] {
            let shifted: Vec<f32> = quiet.iter().map(|x| x + bias).collect();
            let actual = analyze(&shifted, rate, &config).unwrap();
            assert_eq!(actual.events.len(), reference.events.len());
            for (a, b) in actual.events.iter().zip(&reference.events) {
                assert!(a.source_sample.abs_diff(b.source_sample) <= 1);
                assert_eq!(a.class, b.class);
            }
        }
        let high_gate = analyze(
            &quiet,
            rate,
            &Options {
                gate_db: -24.0,
                ..options()
            },
        )
        .unwrap();
        assert!(high_gate.events.is_empty());
    }
}

#[test]
fn gate_is_not_overridden_by_continuous_background_energy() {
    let rate = 48000;
    let mut audio: Vec<f32> = (0..rate * 4)
        .map(|i| (std::f64::consts::TAU * 1000.0 * i as f64 / rate as f64).sin() as f32 * 0.01)
        .collect();
    for hit in 1..16 {
        for i in 0..2400 {
            let t = i as f64 / rate as f64;
            audio[hit * 12000 + i] +=
                (0.025 * (std::f64::consts::TAU * 2000.0 * t).sin() * (-t * 80.0).exp()) as f32;
        }
    }
    let detected = analyze(
        &audio,
        rate as u32,
        &Options {
            gate_db: -48.0,
            ..options()
        },
    )
    .unwrap();
    for hit in 1..16 {
        assert!(
            detected
                .events
                .iter()
                .any(|e| (e.beat - hit as f64 / 2.0).abs() < 0.025),
            "missing hit {hit}"
        );
    }
    assert!(detected.events.len() <= 16); // One possible initial tone onset.
}

#[test]
fn biased_constant_or_stationary_noise_is_not_a_rhythm() {
    let rate = 48000;
    let config = Options {
        gate_db: -48.0,
        ..options()
    };
    assert!(
        analyze(&vec![0.03; rate * 4], rate as u32, &config)
            .unwrap()
            .events
            .is_empty()
    );
    let mut seed = 123_u32;
    let noise: Vec<f32> = (0..rate * 4)
        .map(|_| {
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            0.008 + (seed as f64 / u32::MAX as f64 * 2.0 - 1.0) as f32 * 0.01
        })
        .collect();
    assert!(analyze(&noise, rate as u32, &config).unwrap().events.len() <= 1);
}
#[test]
fn rejects_bad_audio_and_config() {
    for sample in [f32::NAN, f32::INFINITY, 9.0] {
        assert!(analyze(&[sample], 48000, &options()).is_err());
    }
    assert!(analyze(&[], 48000, &options()).is_err());
    assert!(analyze(&[0.0], 0, &options()).is_err());
    for bpm in [0.0, f64::NAN, 300.0] {
        assert!(analyze(&[0.0], 48000, &Options { bpm, ..options() }).is_err());
    }
}
#[test]
fn mapping_grid_strength_and_state_roundtrip() {
    let mut p = pattern();
    p.notes = vec![12, 64, 127];
    p.strength = 0.5;
    let restored: Pattern = serde_json::from_str(&serde_json::to_string(&p).unwrap()).unwrap();
    assert_eq!(midi_file(&p).unwrap(), midi_file(&restored).unwrap());
    assert_eq!(quantized_beat(0.1, 4, 0.5, 8.0), 0.05);
    assert_eq!(quantized_beat(0.1, 0, 1.0, 8.0), 0.1);
}
#[test]
fn export_omits_review_and_merges_collisions() {
    let mut p = pattern();
    let one = midi_file(&p).unwrap();
    p.events.push(Event {
        class: 3,
        ..p.events[0].clone()
    });
    assert_eq!(one, midi_file(&p).unwrap());
    p.events.push(p.events[0].clone());
    assert_eq!(one, midi_file(&p).unwrap());
    p.notes[0] = 128;
    assert!(midi_file(&p).is_err());
}
#[test]
fn valid_midi_header_tempo_channel_and_loop_end() {
    let bytes = midi_file(&pattern()).unwrap();
    assert_eq!(&bytes[..14], b"MThd\0\0\0\x06\0\0\0\x01\x03\xc0");
    assert!(
        bytes
            .windows(6)
            .any(|w| w == [0xff, 0x51, 3, 7, 0xa1, 0x20])
    );
    assert!(bytes.windows(3).any(|w| w == [0x99, 36, 100]));
    assert!(bytes.windows(3).any(|w| w == [0x89, 36, 0]));
    assert!(bytes.ends_with(&[0xff, 0x2f, 0]));
}
#[test]
fn quantize_properties_exhaustive_boundaries() {
    for grid in [0, 2, 3, 4, 6, 8, 12, 16] {
        for bars in 1..=8 {
            let end = bars as f64 * 4.0;
            for strength in [0.0, 0.25, 0.5, 1.0] {
                for i in 0..1000 {
                    let beat = end * i as f64 / 1000.0;
                    let q = quantized_beat(beat, grid, strength, end);
                    assert!(q >= 0.0 && q < end);
                    if strength == 0.0 || grid == 0 {
                        assert_eq!(q, beat);
                    }
                }
            }
        }
    }
}
#[test]
fn every_state_field_is_validated() {
    let p = pattern();
    for field in ["version", "sample_rate", "bars", "grid"] {
        let mut json = serde_json::to_value(&p).unwrap();
        json[field] = serde_json::json!(999999);
        let value: Pattern = serde_json::from_value(json).unwrap();
        assert!(value.validate().is_err());
    }
    let mut p = p;
    p.events[0].beat = 8.0;
    assert!(p.validate().is_err());
    p.events[0].beat = 0.0;
    p.events[0].velocity = 0;
    assert!(p.validate().is_err());
}

#[test]
fn fourth_class_exports_but_review_does_not() {
    let mut p = pattern();
    p.version = 2;
    p.notes.push(39);
    p.events[0].class = 3;
    let bytes = midi_file(&p).unwrap();
    assert!(bytes.windows(3).any(|w| w == [0x99, 39, 100]));
    p.events.push(Event {
        class: 4,
        ..p.events[0].clone()
    });
    assert_eq!(bytes, midi_file(&p).unwrap());
    p.events[0].class = 5;
    assert!(p.validate().is_err());
}

#[test]
fn schema_rejects_mismatched_mapping_counts() {
    let mut p = pattern();
    p.version = 2;
    assert!(p.validate().is_err());
    p.notes.push(39);
    assert!(p.validate().is_ok());
    p.version = 1;
    assert!(p.validate().is_err());
}

#[test]
fn four_distinct_recorded_tones_reach_four_midi_notes() {
    let rate = 48000;
    let mut audio = vec![0.0_f32; rate * 4];
    for hit in 0..16 {
        let hz = [100.0, 800.0, 3000.0, 15000.0][hit % 4];
        for i in 0..4000 {
            let t = i as f64 / rate as f64;
            audio[hit * 12000 + i] =
                (0.7 * (std::f64::consts::TAU * hz * t).sin() * (-t * 50.0).exp()) as f32;
        }
    }
    let p = analyze(&audio, rate as u32, &options()).unwrap();
    assert_eq!(p.events.len(), 16);
    assert_eq!(p.version, 2);
    for (hit, event) in p.events.iter().enumerate() {
        assert_eq!(event.class, (hit % 4) as u8);
    }
    let bytes = midi_file(&p).unwrap();
    for note in p.notes {
        assert!(
            bytes
                .windows(3)
                .any(|w| w[0] == 0x99 && w[1] == note && w[2] > 0)
        );
    }
}

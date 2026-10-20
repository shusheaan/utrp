use std::f64::consts::PI;

pub type Feature = [f64; 5];

/// Small radix-2 FFT, used only offline. Inputs are bounded at the API boundary.
fn fft(real: &mut [f64], imag: &mut [f64]) {
    let n = real.len();
    let mut j = 0;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            real.swap(i, j);
            imag.swap(i, j);
        }
    }
    let mut len = 2;
    while len <= n {
        let angle = -2.0 * PI / len as f64;
        let (wi, wr) = angle.sin_cos();
        for base in (0..n).step_by(len) {
            let (mut r, mut im) = (1.0, 0.0);
            for k in 0..len / 2 {
                let a = base + k;
                let b = a + len / 2;
                let tr = r * real[b] - im * imag[b];
                let ti = r * imag[b] + im * real[b];
                real[b] = real[a] - tr;
                imag[b] = imag[a] - ti;
                real[a] += tr;
                imag[a] += ti;
                (r, im) = (r * wr - im * wi, r * wi + im * wr);
            }
        }
        len *= 2;
    }
}

pub fn extract(samples: &[f32], rate: u32) -> Feature {
    let window = ((rate as f64 * 0.045) as usize).clamp(256, 8192);
    let n = window.next_power_of_two();
    let mut real = vec![0.0; n];
    let mut imag = vec![0.0; n];
    let count = window.min(samples.len());
    for i in 0..count {
        real[i] = samples[i] as f64 * (0.5 - 0.5 * (2.0 * PI * i as f64 / window as f64).cos());
    }
    fft(&mut real, &mut imag);
    let mut bands = [0.0; 3];
    let (mut weight, mut centroid) = (0.0, 0.0);
    for i in 1..n / 2 {
        let freq = i as f64 * rate as f64 / n as f64;
        let energy = real[i] * real[i] + imag[i] * imag[i];
        if freq < 40.0 {
            continue;
        }
        bands[if freq < 400.0 {
            0
        } else if freq < 2000.0 {
            1
        } else {
            2
        }] += energy;
        weight += energy;
        centroid += energy * freq;
    }
    let total = weight.max(1e-20);
    let zcr = samples[..count]
        .windows(2)
        .filter(|w| w[0].is_sign_positive() != w[1].is_sign_positive())
        .count();
    [
        bands[0] / total,
        bands[1] / total,
        bands[2] / total,
        centroid / total / (rate as f64 / 2.0),
        zcr as f64 / count.max(1) as f64,
    ]
}

fn distance(a: &Feature, b: &Feature) -> f64 {
    a.iter().zip(b).map(|(x, y)| (x - y).powi(2)).sum()
}

/// Deterministic farthest-first k-means. No semantic classifier is claimed.
pub fn cluster(features: &[Feature]) -> Vec<(u8, f64)> {
    if features.is_empty() {
        return Vec::new();
    }
    let first = features
        .iter()
        .min_by(|a, b| a[3].total_cmp(&b[3]))
        .unwrap();
    let mut centres = vec![*first];
    while centres.len() < 4 {
        let candidate = features
            .iter()
            .max_by(|a, b| {
                let nearest = |f: &Feature| {
                    centres
                        .iter()
                        .map(|c| distance(f, c))
                        .fold(f64::INFINITY, f64::min)
                };
                nearest(a).total_cmp(&nearest(b))
            })
            .unwrap();
        if centres.iter().any(|c| distance(c, candidate) < 0.015) {
            break;
        }
        centres.push(*candidate);
    }
    for _ in 0..24 {
        let mut sums = vec![[0.0; 5]; centres.len()];
        let mut counts = vec![0usize; centres.len()];
        for f in features {
            let nearest = centres
                .iter()
                .enumerate()
                .min_by(|(_, a), (_, b)| distance(f, a).total_cmp(&distance(f, b)))
                .unwrap()
                .0;
            counts[nearest] += 1;
            for (target, value) in sums[nearest].iter_mut().zip(f) {
                *target += value;
            }
        }
        for i in 0..centres.len() {
            if counts[i] > 0 {
                for (c, sum) in centres[i].iter_mut().zip(sums[i]) {
                    *c = sum / counts[i] as f64;
                }
            }
        }
    }
    centres.sort_by(|a, b| a[3].total_cmp(&b[3]));
    features
        .iter()
        .map(|f| {
            let mut scores: Vec<_> = centres
                .iter()
                .enumerate()
                .map(|(i, c)| (i, distance(f, c)))
                .collect();
            scores.sort_by(|a, b| a.1.total_cmp(&b.1));
            let (class, dist) = scores[0];
            let separation = if scores.len() < 2 {
                0.5
            } else {
                (1.0 - dist / scores[1].1.max(1e-12)).clamp(0.0, 1.0)
            };
            (
                if separation < 0.25 || dist > 0.35 {
                    4
                } else {
                    class as u8
                },
                separation,
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn four_distinct_groups_are_available() {
        let features = [
            [1.0, 0.0, 0.0, 0.01, 0.01],
            [0.0, 1.0, 0.0, 0.05, 0.05],
            [0.0, 0.0, 1.0, 0.2, 0.2],
            [0.0, 0.0, 1.0, 0.8, 0.8],
        ];
        let groups = cluster(&features.repeat(4));
        assert_eq!(
            groups.iter().map(|g| g.0).collect::<Vec<_>>(),
            [0, 1, 2, 3].repeat(4)
        );
    }
    #[test]
    fn fft_separates_low_and_high_tones() {
        let tone = |f: f64| {
            (0..2400)
                .map(|i| (2.0 * PI * f * i as f64 / 48000.0).sin() as f32)
                .collect::<Vec<_>>()
        };
        let a = extract(&tone(100.0), 48000);
        let b = extract(&tone(6000.0), 48000);
        assert!(a[0] > 0.99 && b[2] > 0.99);
        assert!(a[3] < b[3]);
    }
    #[test]
    fn identical_samples_do_not_force_four_groups() {
        assert_eq!(
            cluster(&[[0.8, 0.2, 0.0, 0.02, 0.02]; 8]),
            vec![(0, 0.5); 8]
        );
    }
}

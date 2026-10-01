use crate::{config::Guitar, progression::ChordEvent, theory::chord::Chord};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Position {
    pub string: u8,
    pub fret: u8,
    pub midi: u8,
    pub degree: u8,
    pub finger: Option<u8>, // None = sequential path: no simultaneous fingering assigned
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Barre {
    pub fret: u8,
    pub from_string: u8,
    pub to_string: u8,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Shape {
    pub positions: Vec<Position>,
    pub muted: Vec<u8>,
    pub barre: Option<Barre>,
    pub inversion: usize,
    pub family: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GuitarTarget {
    pub region: [u8; 2],
    pub shape: Option<Shape>,
    pub arpeggio: Vec<Position>,
    pub task: String,
    pub note: String,
}

fn assign_fingers(positions: &mut [Position], span: u8) -> Option<Option<Barre>> {
    let stopped: Vec<_> = positions
        .iter()
        .filter(|p| p.fret > 0)
        .map(|p| p.fret)
        .collect();
    let Some(&low) = stopped.iter().min() else {
        for p in positions {
            p.finger = Some(0);
        }
        return Some(None);
    };
    if stopped.iter().max()? - low > span {
        return None;
    }
    let lowest: Vec<u8> = positions
        .iter()
        .filter(|p| p.fret == low)
        .map(|p| p.string)
        .collect();
    let barre = if lowest.len() > 1 {
        let from = *lowest.iter().max()?;
        let to = *lowest.iter().min()?;
        if positions
            .iter()
            .any(|p| p.string >= to && p.string <= from && p.fret < low)
        {
            return None;
        }
        Some(Barre {
            fret: low,
            from_string: from,
            to_string: to,
        })
    } else {
        None
    };
    let mut finger = 2;
    let mut order: Vec<usize> = (0..positions.len()).collect();
    order.sort_by_key(|i| (positions[*i].fret, 6 - positions[*i].string));
    for i in order {
        let p = &mut positions[i];
        p.finger = Some(if p.fret == 0 {
            0
        } else if p.fret == low {
            1
        } else {
            let f = finger;
            finger += 1;
            f
        });
        if p.finger.is_some_and(|f| f > 4) {
            return None;
        }
    }
    Some(barre)
}

fn family(notes: &[u8]) -> String {
    if notes.last().expect("nonempty") - notes[0] < 12 {
        return "close".into();
    }
    if notes.len() == 4 {
        // Color-chord member order (e.g. 1,3,5,9) is not pitch order.
        // Build each genuinely closed arrangement before dropping a voice.
        let mut pcs: Vec<_> = notes.iter().map(|n| n % 12).collect();
        pcs.sort_unstable();
        for inversion in 0..4 {
            let closed: Vec<_> = (inversion..inversion + 4)
                .map(|i| 48 + pcs[i % 4] + (i / 4) as u8 * 12)
                .collect();
            for drop in [2, 3] {
                let mut test = closed.clone();
                test[4 - drop] -= 12;
                test.sort_unstable();
                if test.iter().zip(notes).all(|(a, b)| {
                    i16::from(*a) - i16::from(*b) == i16::from(test[0]) - i16::from(notes[0])
                }) {
                    return format!("drop{drop}");
                }
            }
        }
    }
    "open".into()
}

fn enumerate(
    chord: &Chord,
    cfg: &Guitar,
    strings: &[u8],
    region: [u8; 2],
    chosen: &mut Vec<Position>,
    out: &mut Vec<Shape>,
) {
    if chosen.len() == strings.len() {
        let pcs: Vec<u8> = chosen.iter().map(|p| p.midi % 12).collect();
        if !chord.pcs().iter().all(|pc| pcs.contains(pc)) {
            return;
        }
        let mut positions = chosen.clone();
        let Some(barre) = assign_fingers(&mut positions, cfg.max_span) else {
            return;
        };
        let inversion = chord
            .tones
            .iter()
            .position(|t| t.pc == pcs[0])
            .expect("chord member");
        let notes: Vec<_> = positions.iter().map(|p| p.midi).collect();
        out.push(Shape {
            positions,
            muted: (1..=6).filter(|s| !strings.contains(s)).collect(),
            barre,
            inversion,
            family: family(&notes),
        });
        return;
    }
    let string = strings[chosen.len()];
    for fret in region[0]..=region[1] {
        let midi = cfg.tuning[(6 - string) as usize] + fret;
        let Some(index) = chord.tones.iter().position(|t| t.pc == midi % 12) else {
            continue;
        };
        if chosen.iter().any(|p| p.midi % 12 == midi % 12)
            || chosen.last().is_some_and(|p| p.midi >= midi)
        {
            continue;
        }
        chosen.push(Position {
            string,
            fret,
            midi,
            degree: chord.degrees[index],
            finger: None,
        });
        enumerate(chord, cfg, strings, region, chosen, out);
        chosen.pop();
    }
}

pub fn shapes(chord: &Chord, cfg: &Guitar, region: [u8; 2]) -> Vec<Shape> {
    let sets = if chord.tones.len() == 3 {
        &cfg.triad_strings
    } else {
        &cfg.seventh_strings
    };
    let mut result = Vec::new();
    for strings in sets {
        enumerate(chord, cfg, strings, region, &mut Vec::new(), &mut result);
    }
    result
}

pub struct GuitarPlanner {
    config: Guitar,
    previous: Option<Shape>,
    uses: BTreeMap<String, usize>,
    arpeggio_visits: BTreeMap<String, usize>,
}
impl GuitarPlanner {
    pub fn new(config: Guitar) -> Self {
        Self {
            config,
            previous: None,
            uses: BTreeMap::new(),
            arpeggio_visits: BTreeMap::new(),
        }
    }
    fn tag(event: &ChordEvent, region: [u8; 2], s: &Shape) -> String {
        format!(
            "{}:{}:{region:?}:{:?}:{}",
            event.key.label(),
            event.chord.symbol(),
            s.positions.iter().map(|p| p.string).collect::<Vec<_>>(),
            s.inversion
        )
    }
    fn schedule(&self, phrase: usize) -> (bool, [u8; 2]) {
        let every = self.config.arpeggio_every;
        let (detached, ordinal) = if let Some(previous_arpeggios) = phrase.checked_div(every) {
            let detached = phrase % every == every - 1;
            let ordinal = if detached {
                previous_arpeggios
            } else {
                phrase - previous_arpeggios
            };
            (detached, ordinal)
        } else {
            (false, phrase)
        };
        // Each task rotates its own regions; shared periods cannot lock a
        // task to one region. All events in a phrase keep the same assignment.
        (
            detached,
            self.config.regions
                [(ordinal / self.config.phrases_per_region) % self.config.regions.len()],
        )
    }
    pub fn target(&mut self, event: &ChordEvent) -> GuitarTarget {
        let (detached, region) = self.schedule(event.phrase);
        let candidates = shapes(&event.chord, &self.config, region);
        let chosen = candidates.into_iter().min_by_key(|s| {
            let usage = *self.uses.get(&Self::tag(event, region, s)).unwrap_or(&0);
            let motion = self.previous.as_ref().map_or(0, |previous| {
                s.positions
                    .iter()
                    .map(|p| {
                        previous
                            .positions
                            .iter()
                            .map(|q| {
                                u32::from(p.midi.abs_diff(q.midi))
                                    + u32::from(p.string.abs_diff(q.string))
                            })
                            .min()
                            .unwrap_or(0)
                    })
                    .sum::<u32>()
            });
            let specific = format!(
                "shape:{}:{:?}",
                Self::tag(event, region, s),
                s.positions.iter().map(|p| p.fret).collect::<Vec<_>>()
            );
            let shape_usage = *self.uses.get(&specific).unwrap_or(&0);
            (usage, shape_usage, motion)
        });
        let path_key = format!("{}:{}:{region:?}", event.key.label(), event.chord.symbol());
        let visit = *self.arpeggio_visits.get(&path_key).unwrap_or(&0);
        let arpeggio = crate::arpeggio::path(&event.chord, &self.config, region, visit);
        if detached && arpeggio.len() == event.chord.tones.len() {
            *self.arpeggio_visits.entry(path_key).or_default() += 1;
        }
        let note = if arpeggio.len() != event.chord.tones.len() {
            "No complete arpeggio path in this region; widen configured region"
        } else if chosen.is_none() {
            "No simultaneous solution in this region; detached path available (not a chord grip)"
        } else {
            "Constraint-checked fingering; mute unused strings; adjust if uncomfortable"
        }
        .into();
        if !detached {
            if let Some(s) = &chosen {
                *self.uses.entry(Self::tag(event, region, s)).or_default() += 1;
                let specific = format!(
                    "shape:{}:{:?}",
                    Self::tag(event, region, s),
                    s.positions.iter().map(|p| p.fret).collect::<Vec<_>>()
                );
                *self.uses.entry(specific).or_default() += 1;
                self.previous = Some(s.clone());
            }
        }
        GuitarTarget {
            region,
            shape: chosen,
            arpeggio,
            task: if detached {
                "arpeggio_detached"
            } else {
                "chord"
            }
            .into(),
            note,
        }
    }
}

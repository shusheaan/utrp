use colored::*;
use log::debug;
use rand::Rng;
use std::{
    error::Error,
    fmt,
    io::{stdin, stdout, Write},
    sync::mpsc::{self, Receiver, Sender},
    thread,
    time::{Duration, SystemTime},
};

use crate::{
    chord::{Chord, ChordType, Inversion},
    input::AppSignal,
    key::{Key, KeyType},
    modulation::{DeTour, Modulation},
    print,
};

#[derive(Debug, Clone)]
pub enum Difficulty {
    Easy,
    Hell,
    Guitar,
}

impl fmt::Display for Difficulty {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Difficulty::Easy => {
                write!(f, "{}", "easy".green().bold())
            }
            Difficulty::Hell => {
                write!(f, "{}", "hell".purple().bold())
            }
            Difficulty::Guitar => {
                write!(f, "{}", "guitar".purple().bold())
            }
        }
    }
}

#[derive(Debug)]
pub(super) struct Status {
    ss_idx: usize,
    pub(super) chords: Vec<Chord>,
    pub(super) key: Key,
    key_iteration: i32,
}

#[derive(Debug)]
struct AppEnv {
    total_time: u64,
    sleep_time: u64,
    total_iteration: i32,
    modulation_threshold: i32,
}

impl AppEnv {
    fn new(difficulty: &Difficulty) -> Self {
        match difficulty {
            Difficulty::Easy => AppEnv {
                total_time: 120,
                sleep_time: 15,
                total_iteration: 100,
                modulation_threshold: 10,
            },
            Difficulty::Hell => AppEnv {
                total_time: 120,
                sleep_time: 15,
                total_iteration: 100,
                modulation_threshold: 4,
            },
            Difficulty::Guitar => AppEnv {
                total_time: 120,
                sleep_time: 15,
                total_iteration: 100,
                modulation_threshold: 4,
            },
        }
    }
}

#[derive(Debug)]
pub struct App {
    input_rx: Receiver<AppSignal>,

    difficulty: Difficulty,
    env: AppEnv,
    score: i32,
    ss: Vec<i8>, // std seq

    pub(super) prevous_key: Key,
    pub(super) current: Status,
    pub(super) modulation: Modulation,
    pub(super) next: Status,
}

impl App {
    fn select_difficulty(input_rx: &Receiver<AppSignal>) -> Difficulty {
        let mut difficulty: Difficulty;
        'set_difficulty: loop {
            thread::sleep(Duration::from_millis(500));
            let any_signal = input_rx.try_recv();
            match any_signal {
                Ok(signal) => {
                    match signal {
                        AppSignal::Easy => {
                            difficulty = Difficulty::Easy;
                            print::easy_selected();
                            break 'set_difficulty;
                        }
                        AppSignal::Hell => {
                            difficulty = Difficulty::Hell;
                            print::hell_selected();
                            break 'set_difficulty;
                        }
                        AppSignal::Guitar => {
                            difficulty = Difficulty::Guitar;
                            print::guitar_selected();
                            break 'set_difficulty;
                        }
                        _ => {
                            continue;
                        }
                    };
                }
                Err(e) => {
                    continue;
                }
            }
        }
        difficulty
    }

    pub fn new(input_rx: Receiver<AppSignal>) -> anyhow::Result<App> {
        print::select_difficulty();

        let difficulty = Self::select_difficulty(&input_rx);
        let env = AppEnv::new(&difficulty);

        let ss = vec![
            1, 3, 1, 4, 2, 5, 6, 3, 7, 1, 4, 5, 3, 2, 4, 7, 6, 5, 6, 1, 7, 6, 2, 4, 5, 1, 5, 3, 6,
            7, 3, 4, 2, 1, 6, 2, 7, 3, 5, 1,
        ];

        let current_key = Key::sample(difficulty.clone())?;
        let prevous_key = current_key.clone();
        // current_key.log_all_chords();

        let mut current_ss_idx = rand::thread_rng().gen_range(0..40);
        let current_chord = current_key.gen_chord(ss[current_ss_idx], difficulty.clone())?;
        let current_key_iteration = 1;

        let modulation = Modulation::SameKey;
        let mut next_ss_idx = current_ss_idx + 1;
        if next_ss_idx > (ss.len() - 1) {
            next_ss_idx %= (ss.len() - 1);
        }
        let next_key = current_key.clone();
        let next_key_iteration = current_key_iteration + 1;

        let detour: DeTour = DeTour::sample(difficulty.clone())?;
        let next_chords = detour.build_chords(
            current_key.gen_chord(ss[next_ss_idx], difficulty.clone())?,
            difficulty.clone(),
        )?;

        Ok(App {
            input_rx,
            difficulty,
            env,
            score: 0,
            ss,
            prevous_key,

            current: Status {
                ss_idx: current_ss_idx,
                chords: Vec::from([current_chord]),
                key: current_key,
                key_iteration: current_key_iteration,
            },
            modulation,
            next: Status {
                ss_idx: next_ss_idx,
                chords: next_chords,
                key: next_key,
                key_iteration: next_key_iteration,
            },
        })
    }

    fn key_vec_thread(msg_rx: Receiver<u8>) -> Receiver<Vec<u8>> {
        let (vec_tx, vec_rx) = mpsc::channel();
        let mut sorted_keys: Vec<u8> = Vec::new();
        thread::spawn(move || -> anyhow::Result<()> {
            loop {
                thread::sleep(Duration::from_millis(10));
                let any_kb_idx = msg_rx.try_recv();
                match any_kb_idx {
                    Ok(kb_idx) => {
                        if sorted_keys.contains(&kb_idx) {
                            if let Some(idx) = sorted_keys.iter().position(|x| *x == kb_idx) {
                                sorted_keys.remove(idx);
                            }
                        } else {
                            sorted_keys.push(kb_idx);
                        }
                        sorted_keys.sort();
                        vec_tx.send(sorted_keys.clone())?;
                    }
                    Err(e) => {
                        continue;
                    }
                };
            }
            Ok(())
        });
        vec_rx
    }

    fn game_timeout_thread(start: SystemTime, total_time: u64) -> Receiver<i32> {
        let (game_timeout_tx, game_timeout_rx) = mpsc::channel();
        thread::spawn(move || -> anyhow::Result<()> {
            loop {
                thread::sleep(Duration::from_secs(1));
                let now = SystemTime::now();
                let duration = now.duration_since(start)?;
                if duration > Duration::from_secs(total_time) {
                    game_timeout_tx.send(0);
                }
            }
            Ok(())
        });
        game_timeout_rx
    }

    fn measure_timeout_thread(sleep_time: u64) -> Receiver<i32> {
        let (timeout_tx, timeout_rx) = mpsc::channel();
        let timeout_limit = sleep_time;
        thread::spawn(move || {
            thread::sleep(Duration::from_secs(timeout_limit));
            timeout_tx.send(0);
        });
        timeout_rx
    }

    pub fn run(&mut self, msg_rx: Receiver<u8>) -> anyhow::Result<Duration> {
        print::get_ready();
        thread::sleep(Duration::from_secs(2));
        print::start();

        let start = SystemTime::now();
        let vec_rx = Self::key_vec_thread(msg_rx);
        let game_timeout_rx = Self::game_timeout_thread(start, self.env.total_time);

        'measure: for i in 1..self.env.total_iteration {
            self.next();
            println!("{}", self);

            let mut chords_unmatched: Vec<Chord> =
                self.next.chords.clone().into_iter().rev().collect();
            chords_unmatched.remove(chords_unmatched.len() - 1);
            chords_unmatched.insert(0, self.current.chords[0].clone());

            let timeout_rx = Self::measure_timeout_thread(self.env.sleep_time);
            while chords_unmatched.len() > 0 {
                let target_chord = chords_unmatched.remove(0);
                let target_key_vec: Vec<u8> =
                    target_chord.tones.iter().map(|e| e.idx as u8).collect();
                print::play(&target_chord);

                let chord_match_start = SystemTime::now();
                'match_chord: loop {
                    thread::sleep(Duration::from_millis(10));

                    if let Ok(signal) = timeout_rx.try_recv() {
                        print::measure_timeout();
                        continue 'measure;
                    }

                    if let Ok(signal) = game_timeout_rx.try_recv() {
                        print::game_timeout();
                        break 'measure;
                    }

                    if let Ok(signal) = self.input_rx.try_recv() {
                        if let AppSignal::Quit = signal {
                            break 'measure;
                        }
                    }

                    let any_key_vec = vec_rx.try_recv();
                    match any_key_vec {
                        Ok(key_vec) => {
                            let key_vec: Vec<u8> = key_vec
                                .into_iter()
                                .map(|e| (e - 24 as u8) % 12 + 1)
                                .collect();
                            debug!("{:?}", key_vec); // debug!("{:?}", target_key_vec);
                            if key_vec.len() >= 7 {
                                print::kb_check(key_vec.len());
                            }

                            if key_vec == target_key_vec {
                                let chord_match_end = SystemTime::now();
                                let chord_match_duration =
                                    chord_match_end.duration_since(chord_match_start)?;

                                if chord_match_duration > Duration::from_secs(8) {
                                    self.score += 0
                                } else {
                                    let secs = (8 - chord_match_duration.as_secs());
                                    self.score += secs.pow(4) as i32;
                                }
                                print::matched(&target_chord);
                                print::score(self.score);
                                break 'match_chord;
                            }
                        }
                        Err(e) => {
                            continue;
                        }
                    }
                }
            }
        }

        let end = SystemTime::now();
        let duration = end.duration_since(start)?;
        print::summary(duration.as_secs(), &self.difficulty, self.score);

        Ok(duration)
    }

    fn status_next_to_current(&mut self) {
        // TODO: use ref instead of clone?
        self.prevous_key = self.current.key.clone();
        self.current.key = self.next.key.clone();
        self.current.chords = Vec::from([self.next.chords[0].clone()]);
        self.current.key_iteration = self.next.key_iteration;
        self.next.key_iteration = 1;
    }

    fn modulate(&mut self) -> anyhow::Result<()> {
        match self.modulation {
            Modulation::SameKey => {
                // previous key not updated
                self.current.key = self.next.key.clone();
                self.current.chords = Vec::from([self.next.chords[0].clone()]);

                self.current.key_iteration = self.next.key_iteration;
                self.next.key_iteration = self.current.key_iteration + 1;

                self.current.ss_idx = self.next.ss_idx;
                self.next.ss_idx = self.current.ss_idx + 1;
                if self.next.ss_idx > (self.ss.len() - 1) {
                    self.next.ss_idx %= (self.ss.len() - 1);
                }

                self.next.key = self.current.key.clone();
                let detour: DeTour = DeTour::sample(self.difficulty.clone())?;
                self.next.chords = detour.build_chords(
                    self.next
                        .key
                        .gen_chord(self.ss[self.next.ss_idx], self.difficulty.clone())?,
                    self.difficulty.clone(),
                )?;
            }
            Modulation::ViaTonic => {
                self.status_next_to_current();
                self.current.ss_idx = self.next.ss_idx;
                self.next.ss_idx = rand::thread_rng().gen_range(0..40);

                self.next.key = Key::new(
                    self.current.key.tonic.clone(),
                    KeyType::sample(self.difficulty.clone())?,
                );
                let detour: DeTour = DeTour::sample(self.difficulty.clone())?;
                self.next.chords = detour.build_chords(
                    self.next
                        .key
                        .gen_chord(self.ss[self.next.ss_idx], self.difficulty.clone())?,
                    self.difficulty.clone(),
                )?;
            }
            Modulation::ViaSharedChord => {
                self.status_next_to_current();

                self.current.ss_idx = self.next.ss_idx;
                self.next.ss_idx = rand::thread_rng().gen_range(0..40);

                let next_keys = self.current.chords[0].gen_major_keys();
                let next_key_id = rand::thread_rng().gen_range(0..next_keys.len());
                self.next.key = next_keys[next_key_id]
                    .clone()
                    .change_mode(rand::thread_rng().gen_range(0..7));

                let detour: DeTour = DeTour::sample(self.difficulty.clone())?;
                self.next.chords = detour.build_chords(
                    self.next
                        .key
                        .gen_chord(self.ss[self.next.ss_idx], self.difficulty.clone())?,
                    self.difficulty.clone(),
                )?;
            }
            Modulation::ViaDiminished => {
                self.status_next_to_current();
                self.current.ss_idx = self.next.ss_idx;

                // current chord to a diminished, randomly to another key
                // add new key's dominant for transition
                let proxy_diminished = Chord::new(
                    self.current.chords[0].tonic.clone(),
                    ChordType::Diminished7,
                    Inversion::sample(self.difficulty.clone())?,
                );
                let next_keys = proxy_diminished.gen_major_keys();
                let next_key_id = rand::thread_rng().gen_range(0..next_keys.len());
                self.next.key = next_keys[next_key_id]
                    .clone()
                    .change_mode(rand::thread_rng().gen_range(0..7));

                let dominant_next_key = self.next.key.gen_chord(5, self.difficulty.clone())?;
                let next_chord = self.next.key.gen_chord(1, self.difficulty.clone())?;

                self.next.ss_idx = 1;
                self.next.chords = Vec::from([
                    next_chord,        // 1
                    dominant_next_key, // 5
                    proxy_diminished,  // sub 5
                ]);
            }
            Modulation::Back => {
                let prev_key = self.prevous_key.clone();
                self.status_next_to_current();
                self.next.key = prev_key;

                self.current.ss_idx = self.next.ss_idx;
                self.next.ss_idx = rand::thread_rng().gen_range(0..40);

                let detour: DeTour = DeTour::sample(self.difficulty.clone())?;
                self.next.chords = detour.build_chords(
                    self.next
                        .key
                        .gen_chord(self.ss[self.next.ss_idx], self.difficulty.clone())?,
                    self.difficulty.clone(),
                )?;
            }
        };
        Ok(())
    }
}

impl Iterator for App {
    type Item = Chord;

    fn next(&mut self) -> Option<Chord> {
        let modulation: Modulation;
        if self.current.key_iteration >= self.env.modulation_threshold {
            modulation = Modulation::sample(self.difficulty.clone()).unwrap();
        } else {
            modulation = Modulation::SameKey;
        }
        self.modulation = modulation;
        self.modulate();
        Some(self.current.chords[0].clone())
    }
}

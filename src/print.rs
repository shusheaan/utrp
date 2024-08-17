use crate::{
    app::{App, Difficulty},
    chord::Chord,
};
use colored::*;
use std::fmt;

pub(super) fn intro() {
    println!(
        "
                {}
                {}
                {}
                {} {}
                {} {}
                {}
                {}
                {}

        ",
        "-*-.-`.-**--.".red().bold(),
        "*..-*-.-*-`*-".yellow().bold(),
        "*-**---``-..-".green().bold(),
        "U-TR-P".cyan().bold(),
        "v0.2.1".purple().bold(),
        "by".yellow(),
        "@shusheaan".green().bold(),
        "-*-*-..-`.`-".blue().bold(),
        "-`-.-.--*---`".cyan().bold(),
        "--`-.--`.-.--".purple().bold(),
    );
}

pub(super) fn select_input() {
    println!(
        "
                {}
                {}
                {}
        ",
        "----------------------------".cyan().bold(),
        "select input (enter to skip)".cyan().bold(),
        "----------------------------".cyan().bold(),
    );
}

pub(super) fn select_output() {
    println!(
        "
                {}
                {}
                {}
        ",
        "-------------".cyan().bold(),
        "select output".cyan().bold(),
        "-------------".cyan().bold(),
    );
}

pub(super) fn select_difficulty() {
    println!(
        "
                {}
                {}
                {}

                {} / {} / {}
        ",
        "----------------------".cyan().bold(),
        "select mode/difficulty".cyan().bold(),
        "----------------------".cyan().bold(),
        "[e]asy".green().bold(),
        "[h]ell".purple().bold(),
        "[g]uitar".yellow().bold(),
    );
}

pub(super) fn easy_selected() {
    println!(
        "
                {}
                {}
                {}
        ",
        "-------------------------------".green().bold(),
        "[e]asy mode/difficulty selected".green().bold(),
        "-------------------------------".green().bold(),
    );
}

pub(super) fn hell_selected() {
    println!(
        "
                {}
                {}
                {}
    ",
        "-------------------------------".purple().bold(),
        "[h]ell mode/difficulty selected".purple().bold(),
        "-------------------------------".purple().bold(),
    );
}

pub(super) fn guitar_selected() {
    println!(
        "
                {}
                {}
                {}
    ",
        "---------------------------------".purple().bold(),
        "[g]uitar mode/difficulty selected".purple().bold(),
        "---------------------------------".purple().bold(),
    );
}

pub(super) fn get_ready() {
    println!(
        "
                {}
                {}
                {}
        ",
        "---------".cyan().bold(),
        "get ready".cyan().bold(),
        "---------".cyan().bold(),
    );
}

pub(super) fn start() {
    println!(
        "
                {}
                {}
                {}
        ",
        "-------------".blue().bold(),
        "start playing".blue().bold(),
        "-------------".blue().bold(),
    );
}

pub(super) fn play(chord: &Chord) {
    println!(
        "
                {}
                {} {}
                {}
        ",
        "----".yellow().bold(),
        "play".yellow().bold(),
        chord,
        "----".yellow().bold(),
    );
}

pub(super) fn matched(chord: &Chord) {
    println!(
        "
                {}
                {} {}
                {}
        ",
        "-------".green().bold(),
        "matched".green().bold(),
        chord,
        "-------".green().bold(),
    );
}

pub(super) fn score(score: i32) {
    println!(
        "
                {}
                {} {}
                {}



        ",
        "-----".blue().bold(),
        "score".blue().bold(),
        score,
        "-----".blue().bold(),
    );
}

pub(super) fn measure_timeout() {
    println!(
        "

                {}
                {}
                {}

        ",
        "---------------".red().bold(),
        "measure timeout".red().bold(),
        "---------------".red().bold(),
    );
}

pub(super) fn game_timeout() {
    println!(
        "

                {}
                {}
                {}

        ",
        "------------".red().bold(),
        "game timeout".red().bold(),
        "------------".red().bold(),
    );
}

pub(super) fn kb_check(l: usize) {
    println!(
        "

                {}
                {} {}
                {}
        ",
        "--------".green().bold(),
        "kb check".green(),
        l,
        "--------".green().bold(),
    );
}

pub(super) fn summary(duration: u64, difficulty: &Difficulty, score: i32) {
    println!(
        "

                {}
                {}
                {}

                {} {:?}
                {} {}
                {} {}

        ",
        "-------".cyan().bold(),
        "summary".cyan().bold(),
        "-------".cyan().bold(),
        "time(s)".cyan().bold(),
        duration,
        "mode/difficulty".cyan().bold(),
        difficulty,
        "score".cyan().bold(),
        score,
    );
}

impl fmt::Display for App {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        if self.next.chords.len() == 3 {
            write!(
                f,
                "

                {}

                {}: {}
                {}

                => {}:
                  -> {}
                   --> {}
                    ---> {}

                {}

                ",
                "----------- MEASURE START -----------".cyan().bold(),
                self.current.key,
                self.current.chords[0],
                self.modulation,
                self.next.key,
                self.next.chords[2],
                self.next.chords[1],
                self.next.chords[0],
                "------------ MEASURE END ------------".cyan().bold(),
            )
        } else if self.next.chords.len() == 2 {
            write!(
                f,
                "

                {}

                {}: {}
                {}

                => {}:
                  -> {}
                    --> {}

                {}

                ",
                "----------- MEASURE START -----------".cyan().bold(),
                self.current.key,
                self.current.chords[0],
                self.modulation,
                self.next.key,
                self.next.chords[1],
                self.next.chords[0],
                "------------ MEASURE END ------------".cyan().bold(),
            )
        } else if self.next.chords.len() == 1 {
            write!(
                f,
                "

                {}

                {}: {}
                {}

                => {}: {}

                {}

                ",
                "----------- MEASURE START -----------".cyan().bold(),
                self.current.key,
                self.current.chords[0],
                self.modulation,
                self.next.key,
                self.next.chords[0],
                "------------ MEASURE END ------------".cyan().bold(),
            )
        } else {
            panic!("invalid chord sequence")
        }
    }
}

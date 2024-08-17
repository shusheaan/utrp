use colored::*;
use crossterm::event::{Event, KeyCode};
use midir::{MidiIO, MidiInput, MidiInputPort, MidiOutput, MidiOutputPort};
use std::{
    error::Error,
    fmt,
    io::{stdin, stdout, Write},
    sync::mpsc::{self, Receiver, Sender},
    thread,
    time::{Duration, Instant},
};

use crate::print;

pub(super) fn new_input_thread() -> anyhow::Result<Receiver<AppSignal>> {
    let (input_tx, input_rx): (Sender<AppSignal>, Receiver<AppSignal>) = mpsc::channel();

    thread::spawn(move || -> anyhow::Result<()> {
        let mut last_tick = Instant::now();
        let tick_rate = Duration::from_millis(100);

        'input: loop {
            thread::sleep(tick_rate);
            let timeout = tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| Duration::from_secs(0));

            if crossterm::event::poll(timeout)? {
                if let Event::Key(key) = crossterm::event::read()? {
                    if let KeyCode::Char('q') = key.code {
                        input_tx.send(AppSignal::Quit);
                    }
                    if let KeyCode::Char('e') = key.code {
                        input_tx.send(AppSignal::Easy);
                    }
                    if let KeyCode::Char('h') = key.code {
                        input_tx.send(AppSignal::Hell);
                    }
                    if let KeyCode::Char('g') = key.code {
                        input_tx.send(AppSignal::Guitar);
                    }
                    if let KeyCode::Char('n') = key.code {
                        input_tx.send(AppSignal::Next);
                    }
                }
            };

            if last_tick.elapsed() >= tick_rate {
                last_tick = Instant::now();
            }
        }
    });

    Ok(input_rx)
}

pub(super) struct MIDI {
    device_name: String,
    pub(super) input: MidiInput,
    pub(super) input_port: MidiInputPort,
    pub(super) output: MidiOutput,
    pub(super) output_port: MidiOutputPort,
}

impl fmt::Debug for MIDI {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.device_name)
    }
}

impl MIDI {
    pub(super) fn new() -> Result<Self, Box<dyn Error>> {
        let input = MidiInput::new("input")?;
        let output = MidiOutput::new("output")?;

        print::select_input();
        let input_port = Self::select_port(&input)?;

        print::select_output();
        let output_port = Self::select_port(&output)?;
        let device_name = input.port_name(&input_port)?;

        Ok(MIDI {
            device_name,
            input,
            input_port,
            output,
            output_port,
        })
    }

    fn select_port<T: MidiIO>(midi_io: &T) -> Result<T::Port, Box<dyn Error>> {
        let midi_ports = midi_io.ports();
        for (i, p) in midi_ports.iter().enumerate() {
            println!(
                "
                {}: {}",
                i.to_string().green().bold(),
                midi_io.port_name(p)?.green().bold()
            );
        }
        stdout().flush()?;
        let mut input = String::new();
        stdin().read_line(&mut input)?;
        let port = midi_ports
            .get(input.trim().parse::<usize>()?)
            .ok_or("invalid port number")?;
        Ok(port.clone())
    }
}

pub enum AppSignal {
    Quit,
    Easy,
    Hell,
    Guitar,
    Next,
}

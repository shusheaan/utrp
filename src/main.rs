#![allow(unused)]

use env_logger::Env;
use log::{error, info};
use std::{error::Error, sync::mpsc};

use crate::{
    app::App,
    input::{new_input_thread, MIDI},
};

mod app;
mod chord;
mod input;
mod key;
mod modulation;
mod print;
mod tone;

mod exits {
    pub const SUCCESS: i32 = 0;
    pub const ERROR: i32 = 1;
}

fn main() -> Result<(), Box<dyn Error>> {
    use std::process::exit;
    let env = Env::default().filter_or("RUST_LOG_LEVEL", "error");
    env_logger::init_from_env(env);
    print::intro();

    let input_rx = new_input_thread()?;
    let (msg_tx, msg_rx) = mpsc::channel();

    let midi = MIDI::new()?;
    let mut conn_out = midi.output.connect(&midi.output_port, "")?;
    let _conn_in = midi.input.connect(
        &midi.input_port,
        "",
        move |_, message, _| {
            msg_tx.send(message[1]).unwrap();
        },
        (),
    )?;

    match App::new(input_rx)?.run(msg_rx) {
        Ok(duration) => {
            info!("run successful in {:?}", duration);
            exit(exits::SUCCESS);
        }
        Err(e) => {
            error!("run failed, error: {:?}", e);
            exit(exits::ERROR)
        }
    };
}

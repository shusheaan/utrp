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

    match App::new(input_rx, msg_tx)?.run(msg_rx) {
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

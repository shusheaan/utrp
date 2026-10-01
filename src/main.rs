mod app;
mod input;
mod tui;
mod ui;

use anyhow::{Context, Result};
use utrp::{
    session::Session,
    simulator::{self, Options},
    storage::Log,
};

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|s| s == "--help" || s == "-h") {
        println!("utrp [--instrument guitar|piano] [--config PATH] [--templates PATH] [--seed N]\nutrp simulate [--events N] [--key C] [--mode ionian] [--seed N]\nW faster | S slower | A previous | D next (no credit)\nE balanced random | Q previous key: after NEXT chord (finish any approach/bridge)\nSpace found + next | Enter/Ctrl-C stop + summary | P pause | Tab auto/manual\nStarts untimed; Tab enables 10s/chord by default. No total time limit. --key/--mode restrict scope. --threshold sets minimum phrases per key.");
        return Ok(());
    }
    let options = Options::parse(&args)?;
    if options.headless {
        return simulator::run(&options);
    }
    let (config, templates, seed) = options.load()?;
    let instrument = options
        .instrument
        .clone()
        .unwrap_or_else(|| "guitar".into());
    let midi = if instrument == "piano" {
        Some(input::Midi::connect()?)
    } else {
        None
    };
    let generator = simulator::stream(&config, templates, seed, options.base.unwrap_or(48))?;
    let session = Session::new(generator, config.session.clone(), 0);
    let log = Log::open(&config.storage, &config, seed, &instrument)?;
    let mut app = app::App::new(session, instrument, log, midi);
    let mut terminal = tui::init().context("open terminal")?;
    let result = app.run(&mut terminal);
    let restored = tui::restore();
    result?;
    restored?;
    app.print_summary();
    Ok(())
}

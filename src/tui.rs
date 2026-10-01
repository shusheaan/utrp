use crossterm::{
    event::{KeyboardEnhancementFlags, PopKeyboardEnhancementFlags, PushKeyboardEnhancementFlags},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io::{self, stdout};

pub type Tui = Terminal<CrosstermBackend<io::Stdout>>;

pub fn init() -> anyhow::Result<Tui> {
    enable_raw_mode()?;
    if let Err(error) = execute!(stdout(), EnterAlternateScreen) {
        return initialization_error(error, false, true);
    }
    // Supporting terminals distinguish press/repeat/release. Legacy terminals
    // ignore this command and cannot distinguish repeated ordinary bytes.
    if let Err(error) = execute!(
        stdout(),
        PushKeyboardEnhancementFlags(
            KeyboardEnhancementFlags::DISAMBIGUATE_ESCAPE_CODES
                | KeyboardEnhancementFlags::REPORT_EVENT_TYPES
        )
    ) {
        return initialization_error(error, true, true);
    }
    let original_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        let _ = restore();
        original_hook(panic_info);
    }));
    match Terminal::new(CrosstermBackend::new(stdout())) {
        Ok(terminal) => Ok(terminal),
        Err(error) => initialization_error(error, true, true),
    }
}

fn initialization_error(error: io::Error, keyboard: bool, alternate: bool) -> anyhow::Result<Tui> {
    match restore_steps(keyboard, alternate) {
        Ok(()) => Err(error.into()),
        Err(cleanup) => Err(anyhow::anyhow!(
            "{error}; terminal initialization rollback also failed: {cleanup}"
        )),
    }
}

fn restore_steps(keyboard: bool, alternate: bool) -> anyhow::Result<()> {
    // Evaluate every cleanup independently, even when a previous step fails.
    let raw_result = disable_raw_mode();
    let keyboard_result = if keyboard {
        execute!(stdout(), PopKeyboardEnhancementFlags)
    } else {
        Ok(())
    };
    let screen_result = if alternate {
        execute!(stdout(), LeaveAlternateScreen)
    } else {
        Ok(())
    };
    let errors = [
        ("disable raw mode", raw_result),
        ("restore keyboard protocol", keyboard_result),
        ("leave alternate screen", screen_result),
    ]
    .into_iter()
    .filter_map(|(step, result)| result.err().map(|error| format!("{step}: {error}")))
    .collect::<Vec<_>>();
    anyhow::ensure!(errors.is_empty(), "{}", errors.join("; "));
    Ok(())
}

pub fn restore() -> anyhow::Result<()> {
    restore_steps(true, true)
}

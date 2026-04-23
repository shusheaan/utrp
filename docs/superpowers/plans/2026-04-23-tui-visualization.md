# TUI & Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `println!`-based output with a `ratatui` full-screen TUI, and add piano keyboard, guitar fretboard, and staff notation visualizations for each chord.

**Architecture:** A new `tui` module manages terminal setup/teardown. A new `ui/` module tree contains widget functions that render into ratatui `Frame`. The existing `App` struct gains a `GamePhase` enum and `pub(crate)` field visibility so the UI layer can read game state. All music theory modules (`tone.rs`, `key.rs`, `chord.rs`, `modulation.rs`) remain **100% untouched**. `input.rs` remains untouched. `print.rs` is kept but no longer called.

**Tech Stack:** `ratatui 0.29` + `crossterm 0.28` (backend). All existing deps unchanged except `crossterm` version bump.

---

## File Structure

```
src/
├── main.rs              (MODIFY: terminal init, TUI run loop)
├── app.rs               (MODIFY: add GamePhase, pub(crate) fields, render method)
├── tui.rs               (NEW: terminal setup/teardown helpers)
├── ui/
│   ├── mod.rs           (NEW: main render dispatch + layout)
│   ├── header.rs        (NEW: title bar, score, timer, key, mode)
│   ├── progression.rs   (NEW: chord progression tree widget)
│   ├── target.rs        (NEW: current target chord + status)
│   ├── piano.rs         (NEW: piano keyboard visualization)
│   ├── guitar.rs        (NEW: guitar fretboard visualization)
│   ├── notation.rs      (NEW: simple staff notation)
│   └── footer.rs        (NEW: controls help bar)
├── chord.rs             (NO CHANGE)
├── key.rs               (NO CHANGE)
├── tone.rs              (NO CHANGE)
├── modulation.rs        (NO CHANGE)
├── input.rs             (NO CHANGE)
├── print.rs             (NO CHANGE - dead code, kept for reference)
```

## Target TUI Layout

```
┌──────────────────────────────────────────────────────────────┐
│  U-TR-P v0.2.1        Key: Eb 2/Dorian     Score: 2048      │ <- Header
│  Mode: Piano           (no key change)       Time: 01:23     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Current: Eb 2/Dorian  Fm7-p/1                              │
│   (switch mode with the current key tonic)                   │
│                                                              │
│   => Ab 4/Lydian:                                            │
│     -> Cm7-p/2: [G, Bb, C, Eb]                              │ <- Progression
│       --> Fm7-p/0: [F, Ab, C, Eb]                            │
│         ---> BbM7-p/1: [D, F, Ab, Bb]                       │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  >> PLAY: Fm7-p/0  [F, Ab, C, Eb]                           │ <- Target
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Staff:          │  Piano:                                  │
│   ─── Eb ───      │   ┌─┬───┬┬───┬─┬─┬───┬┬───┬┬───┬─┐     │
│   ─── C  ───      │   │ │   ││   │ │ │   ││▓▓▓││   │ │     │
│   ─── Ab ───      │   │ │   ││   │ │ │   ││▓▓▓││   │ │     │ <- Viz
│   ─── F  ───      │   │ └─┬─┘└─┬─┘ │ └─┬─┘└─┬─┘└─┬─┘ │     │
│                   │   │   │    │   │   │    │    │   │     │
│                   │   │ C │  D │ E │*F │  G │  A │ B │     │
│                   │   └───┴────┴───┴───┴────┴────┴───┘     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Enter] Skip   [Q] Quit                  Measure: 12/100   │ <- Footer
└──────────────────────────────────────────────────────────────┘
```

---

### Task 1: Add dependencies and create module skeleton

**Files:**
- Modify: `Cargo.toml`
- Create: `src/tui.rs`
- Create: `src/ui/mod.rs`
- Create: `src/ui/header.rs`
- Create: `src/ui/progression.rs`
- Create: `src/ui/target.rs`
- Create: `src/ui/piano.rs`
- Create: `src/ui/guitar.rs`
- Create: `src/ui/notation.rs`
- Create: `src/ui/footer.rs`
- Modify: `src/main.rs` (add mod declarations only)

- [ ] **Step 1: Update Cargo.toml**

```toml
[dependencies]
rand = "0.8"
rand_chacha = "0.3.1"
statrs = "0.16.0"
log = "0.4.0"
env_logger = "0.9.0"
colored = "2.0.0"
midir = "0.8.0"
crossterm = "0.28"
anyhow = "1.0"
ratatui = "0.29"
```

Note: `crossterm` bumped from `0.25` to `0.28` (required by ratatui). The crossterm API used in `input.rs` (`Event`, `KeyCode`, `poll`, `read`) is backward-compatible.

- [ ] **Step 2: Create empty module files**

`src/tui.rs`:
```rust
// Terminal setup and teardown for ratatui
```

`src/ui/mod.rs`:
```rust
pub mod header;
pub mod progression;
pub mod target;
pub mod piano;
pub mod guitar;
pub mod notation;
pub mod footer;
```

`src/ui/header.rs`, `src/ui/progression.rs`, `src/ui/target.rs`, `src/ui/piano.rs`, `src/ui/guitar.rs`, `src/ui/notation.rs`, `src/ui/footer.rs`:
```rust
// placeholder
```

- [ ] **Step 3: Add module declarations to main.rs**

Add after existing `mod` lines:
```rust
mod tui;
mod ui;
```

- [ ] **Step 4: Build to verify compilation**

Run: `cargo check`
Expected: compiles with warnings about unused modules

- [ ] **Step 5: Commit**

```bash
git add Cargo.toml src/tui.rs src/ui/ src/main.rs
git commit -m "chore: add ratatui dep and empty TUI module skeleton"
```

---

### Task 2: Terminal setup/teardown (`tui.rs`)

**Files:**
- Modify: `src/tui.rs`

- [ ] **Step 1: Implement terminal helpers**

`src/tui.rs`:
```rust
use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io::{self, stdout};

pub type Tui = Terminal<CrosstermBackend<io::Stdout>>;

pub fn init() -> anyhow::Result<Tui> {
    enable_raw_mode()?;
    execute!(stdout(), EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout());
    let terminal = Terminal::new(backend)?;
    Ok(terminal)
}

pub fn restore() -> anyhow::Result<()> {
    disable_raw_mode()?;
    execute!(stdout(), LeaveAlternateScreen)?;
    Ok(())
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`
Expected: compiles (tui module used in later tasks)

- [ ] **Step 3: Commit**

```bash
git add src/tui.rs
git commit -m "feat: add terminal init/restore helpers for ratatui"
```

---

### Task 3: Add GamePhase and expose App state for rendering

**Files:**
- Modify: `src/app.rs`

This task makes the **minimal** changes to `app.rs` needed for TUI rendering. No game logic changes.

- [ ] **Step 1: Add GamePhase enum**

Add after the `Difficulty` enum and its Display impl (around line 38):

```rust
#[derive(Debug, Clone)]
pub enum GamePhase {
    Intro,
    SelectDifficulty,
    Ready,
    Playing,
    MeasureStart { measure: i32 },
    WaitingForInput { target: Chord },
    Matched { chord: Chord },
    Score,
    MeasureTimeout,
    GameTimeout,
    Summary { duration_secs: u64 },
}
```

- [ ] **Step 2: Change field visibility for TUI access**

Change `Status` fields to `pub(crate)`:
```rust
#[derive(Debug)]
pub(crate) struct Status {
    ss_idx: usize,
    pub(crate) chords: Vec<Chord>,
    pub(crate) key: Key,
    key_iteration: i32,
}
```

Change `App` fields to `pub(crate)`:
```rust
#[derive(Debug)]
pub struct App {
    input_rx: Receiver<AppSignal>,

    pub(crate) difficulty: Difficulty,
    env: AppEnv,
    pub(crate) score: i32,
    ss: Vec<i8>,

    pub(crate) prevous_key: Key,
    pub(crate) current: Status,
    pub(crate) modulation: Modulation,
    pub(crate) next: Status,

    pub(crate) phase: GamePhase,
    pub(crate) measure_num: i32,
    pub(crate) start_time: Option<SystemTime>,
}
```

- [ ] **Step 3: Initialize new fields in App::new()**

In the `Ok(App { ... })` block, add:
```rust
    phase: GamePhase::SelectDifficulty,
    measure_num: 0,
    start_time: None,
```

- [ ] **Step 4: Add a render method to App**

Add this method to the `impl App` block:

```rust
    pub(crate) fn render(&self, terminal: &mut crate::tui::Tui) -> anyhow::Result<()> {
        terminal.draw(|frame| {
            crate::ui::render(frame, self);
        })?;
        Ok(())
    }

    pub(crate) fn elapsed_secs(&self) -> u64 {
        self.start_time
            .and_then(|s| SystemTime::now().duration_since(s).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0)
    }
```

- [ ] **Step 5: Update App::run() to accept terminal and set phases**

Replace the body of `run()` with TUI rendering calls. The game logic (scoring, timing, chord matching, modulation) stays **identical** — only `print::*` calls are replaced with `self.phase = ...` + `self.render(terminal)?`.

Change the signature:
```rust
pub fn run(&mut self, msg_rx: Receiver<u8>, terminal: &mut crate::tui::Tui) -> anyhow::Result<Duration> {
```

Replace `print::get_ready()` with:
```rust
    self.phase = GamePhase::Ready;
    self.render(terminal)?;
```

Replace `print::start()` with:
```rust
    self.start_time = Some(SystemTime::now());
    self.phase = GamePhase::Playing;
    self.render(terminal)?;
```

Inside the `'measure` loop, after `self.next()`:
```rust
    self.measure_num = i;
    self.phase = GamePhase::MeasureStart { measure: i };
    self.render(terminal)?;
```

Replace `print::play(&target_chord)` with:
```rust
    self.phase = GamePhase::WaitingForInput { target: target_chord.clone() };
    self.render(terminal)?;
```

Replace `print::matched(&target_chord)` with:
```rust
    self.phase = GamePhase::Matched { chord: target_chord.clone() };
    self.render(terminal)?;
```

Replace `print::score(self.score)` with:
```rust
    self.phase = GamePhase::Score;
    self.render(terminal)?;
```

Replace `print::measure_timeout()` with:
```rust
    self.phase = GamePhase::MeasureTimeout;
    self.render(terminal)?;
```

Replace `print::game_timeout()` with:
```rust
    self.phase = GamePhase::GameTimeout;
    self.render(terminal)?;
```

Replace `print::summary(...)` with:
```rust
    self.phase = GamePhase::Summary { duration_secs: duration.as_secs() };
    self.render(terminal)?;
    thread::sleep(Duration::from_secs(5)); // keep summary visible
```

All other code (scoring calculations, channel receives, modulation, chord matching) stays **exactly** as-is.

- [ ] **Step 6: Build to verify**

Run: `cargo check`
Expected: compiles (ui::render not yet implemented, will need a stub)

- [ ] **Step 7: Commit**

```bash
git add src/app.rs
git commit -m "feat: add GamePhase enum and TUI render hooks to App"
```

---

### Task 4: Main layout and render dispatch (`ui/mod.rs`)

**Files:**
- Modify: `src/ui/mod.rs`

- [ ] **Step 1: Implement the main render function with layout**

```rust
pub mod header;
pub mod progression;
pub mod target;
pub mod piano;
pub mod guitar;
pub mod notation;
pub mod footer;

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    Frame,
};

use crate::app::{App, Difficulty, GamePhase};

pub fn render(frame: &mut Frame, app: &App) {
    let area = frame.area();

    // Main vertical layout: header | progression | target | visualization | footer
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),   // header
            Constraint::Min(8),     // progression
            Constraint::Length(3),   // target
            Constraint::Length(12), // visualization (piano/guitar + notation)
            Constraint::Length(1),   // footer
        ])
        .split(area);

    header::render(frame, app, chunks[0]);
    progression::render(frame, app, chunks[1]);
    target::render(frame, app, chunks[2]);

    // Split visualization area: notation | instrument
    let viz_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(30), // notation
            Constraint::Percentage(70), // instrument
        ])
        .split(chunks[3]);

    notation::render(frame, app, viz_chunks[0]);

    match app.difficulty {
        Difficulty::Piano => piano::render(frame, app, viz_chunks[1]),
        Difficulty::Guitar => guitar::render(frame, app, viz_chunks[1]),
    }

    footer::render(frame, app, chunks[4]);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`
Expected: compile errors for missing render functions in sub-modules (fixed in next tasks)

- [ ] **Step 3: Commit**

```bash
git add src/ui/mod.rs
git commit -m "feat: main TUI layout with 5-zone vertical split"
```

---

### Task 5: Header widget (`ui/header.rs`)

**Files:**
- Modify: `src/ui/header.rs`

- [ ] **Step 1: Implement header rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let elapsed = app.elapsed_secs();
    let mins = elapsed / 60;
    let secs = elapsed % 60;

    let key_str = format!("{}", app.current.key);
    let score_str = format!("{}", app.score);
    let time_str = format!("{:02}:{:02}", mins, secs);
    let mode_str = format!("{}", app.difficulty);
    let measure_str = format!("{}", app.measure_num);

    let header_line = Line::from(vec![
        Span::styled(" U-TR-P ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::raw("v0.2.1  "),
        Span::styled("Key: ", Style::default().fg(Color::White)),
        Span::styled(&key_str, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::raw("  "),
        Span::styled("Score: ", Style::default().fg(Color::White)),
        Span::styled(&score_str, Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD)),
        Span::raw("  "),
        Span::styled("Time: ", Style::default().fg(Color::White)),
        Span::styled(&time_str, Style::default().fg(Color::Green)),
        Span::raw("  "),
        Span::styled("Mode: ", Style::default().fg(Color::White)),
        Span::styled(&mode_str, Style::default().fg(Color::Magenta)),
    ]);

    let block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(header_line).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/header.rs
git commit -m "feat: TUI header widget with score, time, key, mode"
```

---

### Task 6: Chord progression widget (`ui/progression.rs`)

**Files:**
- Modify: `src/ui/progression.rs`

This widget replaces the `Display` impl for `App` in `print.rs`. It shows the current key, modulation description, next key, and the chord progression chain with indented arrows.

- [ ] **Step 1: Implement progression rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let mut lines: Vec<Line> = Vec::new();

    // Current key and chord
    let current_chord_str = if !app.current.chords.is_empty() {
        format!("{}", app.current.chords[0])
    } else {
        String::new()
    };
    lines.push(Line::from(vec![
        Span::styled("  Current: ", Style::default().fg(Color::White)),
        Span::styled(
            format!("{}", app.current.key),
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ),
        Span::raw("  "),
        Span::styled(
            current_chord_str,
            Style::default().fg(Color::Green),
        ),
    ]));

    // Modulation description
    lines.push(Line::from(vec![
        Span::styled(
            format!("  {}", app.modulation),
            Style::default().fg(Color::Yellow),
        ),
    ]));

    lines.push(Line::from(""));

    // Next key and chord chain
    let next_key_str = format!("{}", app.next.key);
    lines.push(Line::from(vec![
        Span::styled("  => ", Style::default().fg(Color::Cyan)),
        Span::styled(
            format!("{}:", next_key_str),
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ),
    ]));

    // Display chord chain (reversed, deepest first with increasing indent)
    let chords = &app.next.chords;
    let depth = chords.len();
    for i in (0..depth).rev() {
        let indent = "  ".repeat(depth - i);
        let arrow = "->".repeat(depth - i);
        let chord_str = format!("{}", chords[i]);
        lines.push(Line::from(vec![
            Span::raw(format!("  {}", indent)),
            Span::styled(
                format!("{} ", arrow),
                Style::default().fg(Color::DarkGray),
            ),
            Span::styled(
                chord_str,
                Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
            ),
        ]));
    }

    let block = Block::default()
        .title(" Progression ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/progression.rs
git commit -m "feat: chord progression tree widget with modulation display"
```

---

### Task 7: Target chord widget (`ui/target.rs`)

**Files:**
- Modify: `src/ui/target.rs`

- [ ] **Step 1: Implement target rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let (label, label_color, chord_str) = match &app.phase {
        GamePhase::WaitingForInput { target } => {
            (">> PLAY", Color::Yellow, format!("{}", target))
        }
        GamePhase::Matched { chord } => {
            ("** MATCHED", Color::Green, format!("{}", chord))
        }
        GamePhase::MeasureTimeout => {
            ("!! TIMEOUT", Color::Red, String::new())
        }
        GamePhase::GameTimeout => {
            ("!! GAME OVER", Color::Red, String::new())
        }
        GamePhase::Score => {
            ("   SCORE", Color::Blue, format!("{}", app.score))
        }
        GamePhase::Summary { duration_secs } => {
            let mins = duration_secs / 60;
            let secs = duration_secs % 60;
            (
                "== SUMMARY",
                Color::Cyan,
                format!("Time: {:02}:{:02}  Score: {}", mins, secs, app.score),
            )
        }
        GamePhase::Ready => ("-- GET READY", Color::Cyan, String::new()),
        GamePhase::Playing => (">> START PLAYING", Color::Blue, String::new()),
        _ => ("", Color::White, String::new()),
    };

    let line = Line::from(vec![
        Span::styled(
            format!("  {} ", label),
            Style::default().fg(label_color).add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            chord_str,
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
        ),
    ]);

    let block = Block::default()
        .borders(Borders::TOP | Borders::BOTTOM)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(line).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/target.rs
git commit -m "feat: target chord widget with phase-based status display"
```

---

### Task 8: Piano keyboard visualization (`ui/piano.rs`)

**Files:**
- Modify: `src/ui/piano.rs`

Shows a 1-octave piano keyboard (C through B). Chord tones are highlighted. The keyboard uses box-drawing characters.

- [ ] **Step 1: Implement tone-to-key mapping and rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};
use crate::chord::Chord;

/// Returns the set of chromatic indices (1-12) for the current target chord
fn active_keys(app: &App) -> Vec<i8> {
    match &app.phase {
        GamePhase::WaitingForInput { target } => {
            target.tones.iter().map(|t| t.idx).collect()
        }
        GamePhase::Matched { chord } => {
            chord.tones.iter().map(|t| t.idx).collect()
        }
        _ => Vec::new(),
    }
}

/// Map chromatic index to whether it's a black key
fn is_black(idx: i8) -> bool {
    matches!(idx, 2 | 4 | 7 | 9 | 11)
}

/// Piano key labels for white keys: C=1, D=3, E=5, F=6, G=8, A=10, B=12
const WHITE_KEYS: [(i8, &str); 7] = [
    (1, " C"), (3, " D"), (5, " E"), (6, " F"), (8, " G"), (10, " A"), (12, " B"),
];

/// Piano key labels for black keys: C#=2, D#=4, F#=7, G#=9, A#=11
const BLACK_KEYS: [(i8, &str); 5] = [
    (2, "C#"), (4, "D#"), (7, "F#"), (9, "G#"), (11, "A#"),
];

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let active = active_keys(app);
    let active_color = match &app.phase {
        GamePhase::Matched { .. } => Color::Green,
        _ => Color::Yellow,
    };

    let mut lines: Vec<Line> = Vec::new();

    // Row 1-2: Black keys top section
    // Layout: _  C# D#  _  F# G# A#  _
    //         ^skip  ^skip
    let black_row = |label: bool| -> Line {
        let mut spans = Vec::new();
        spans.push(Span::raw("   "));
        // C# area
        for &(idx, name) in &BLACK_KEYS {
            let hit = active.contains(&idx);
            let style = if hit {
                Style::default().fg(Color::Black).bg(active_color).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White).bg(Color::DarkGray)
            };
            if label {
                spans.push(Span::styled(format!(" {} ", name), style));
            } else {
                spans.push(Span::styled("    ", style));
            }
            // Gap between D# and F#, and after A#
            if idx == 4 || idx == 11 {
                spans.push(Span::raw("    "));
            } else {
                spans.push(Span::raw(" "));
            }
        }
        Line::from(spans)
    };

    lines.push(black_row(true));
    lines.push(black_row(false));

    // Row 3: Separator
    lines.push(Line::from(Span::styled(
        "   ┌────┬────┬────┬────┬────┬────┬────┐",
        Style::default().fg(Color::DarkGray),
    )));

    // Row 4-5: White keys
    let white_row = |label: bool| -> Line {
        let mut spans = Vec::new();
        spans.push(Span::styled("   │", Style::default().fg(Color::DarkGray)));
        for &(idx, name) in &WHITE_KEYS {
            let hit = active.contains(&idx);
            let style = if hit {
                Style::default().fg(Color::Black).bg(active_color).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };
            if label {
                spans.push(Span::styled(format!(" {} ", name), style));
            } else {
                spans.push(Span::styled("    ", style));
            }
            spans.push(Span::styled("│", Style::default().fg(Color::DarkGray)));
        }
        Line::from(spans)
    };

    lines.push(white_row(false));
    lines.push(white_row(true));

    // Row 6: Bottom border
    lines.push(Line::from(Span::styled(
        "   └────┴────┴────┴────┴────┴────┴────┘",
        Style::default().fg(Color::DarkGray),
    )));

    // Chord tones label
    let tone_names: String = match &app.phase {
        GamePhase::WaitingForInput { target } => {
            target.tones.iter().map(|t| format!("{}", t)).collect::<Vec<_>>().join(" ")
        }
        GamePhase::Matched { chord } => {
            chord.tones.iter().map(|t| format!("{}", t)).collect::<Vec<_>>().join(" ")
        }
        _ => String::new(),
    };
    lines.push(Line::from(vec![
        Span::styled("   Tones: ", Style::default().fg(Color::DarkGray)),
        Span::styled(tone_names, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
    ]));

    let block = Block::default()
        .title(" Piano ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/piano.rs
git commit -m "feat: piano keyboard widget with active key highlighting"
```

---

### Task 9: Guitar fretboard visualization (`ui/guitar.rs`)

**Files:**
- Modify: `src/ui/guitar.rs`

Shows 6 strings in standard tuning (EADGBE) with 5 frets. Chord tones are shown as dots at their positions.

- [ ] **Step 1: Implement fretboard rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};

/// Standard tuning: string 1 (high E) to string 6 (low E)
/// Chromatic index at open string position
const OPEN_STRINGS: [(i8, &str); 6] = [
    (5, "E"),  // high E (idx 5 = E)
    (12, "B"), // B (idx 12 = B)
    (8, "G"),  // G (idx 8 = G)
    (3, "D"),  // D (idx 3 = D)
    (10, "A"), // A (idx 10 = A)
    (5, "E"),  // low E (idx 5 = E)
];

const NUM_FRETS: i8 = 5;

/// Returns chromatic index (1-12) for a given string at a given fret
fn note_at(string_open: i8, fret: i8) -> i8 {
    let idx = (string_open + fret - 1) % 12 + 1;
    idx
}

/// Returns the set of chromatic indices for the current target chord
fn active_keys(app: &App) -> Vec<i8> {
    match &app.phase {
        GamePhase::WaitingForInput { target } => {
            target.tones.iter().map(|t| t.idx).collect()
        }
        GamePhase::Matched { chord } => {
            chord.tones.iter().map(|t| t.idx).collect()
        }
        _ => Vec::new(),
    }
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let active = active_keys(app);
    let active_color = match &app.phase {
        GamePhase::Matched { .. } => Color::Green,
        _ => Color::Yellow,
    };

    let mut lines: Vec<Line> = Vec::new();

    // Fret number header
    let mut header_spans = vec![Span::raw("      ")];
    for fret in 0..=NUM_FRETS {
        if fret == 0 {
            header_spans.push(Span::styled("  ", Style::default().fg(Color::DarkGray)));
        } else {
            header_spans.push(Span::styled(
                format!("  {}  ", fret),
                Style::default().fg(Color::DarkGray),
            ));
        }
    }
    lines.push(Line::from(header_spans));

    // Each string
    for &(open_idx, name) in &OPEN_STRINGS {
        let mut spans = Vec::new();

        // String name
        spans.push(Span::styled(
            format!("   {} ", name),
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
        ));

        // Nut
        spans.push(Span::styled("║", Style::default().fg(Color::White)));

        // Frets
        for fret in 1..=NUM_FRETS {
            let idx = note_at(open_idx, fret);
            let hit = active.contains(&idx);
            if hit {
                spans.push(Span::styled(
                    "──●──",
                    Style::default().fg(active_color).add_modifier(Modifier::BOLD),
                ));
            } else {
                spans.push(Span::styled(
                    "─────",
                    Style::default().fg(Color::DarkGray),
                ));
            }
            spans.push(Span::styled("┤", Style::default().fg(Color::DarkGray)));
        }
        lines.push(Line::from(spans));
    }

    let block = Block::default()
        .title(" Guitar ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/guitar.rs
git commit -m "feat: guitar fretboard widget with tone position dots"
```

---

### Task 10: Staff notation widget (`ui/notation.rs`)

**Files:**
- Modify: `src/ui/notation.rs`

A simplified staff showing chord tones as note names on/between staff lines. Maps chromatic index to staff position.

- [ ] **Step 1: Implement staff notation rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

use crate::app::{App, GamePhase};
use crate::tone::Tone;

fn get_target_tones(app: &App) -> Vec<Tone> {
    match &app.phase {
        GamePhase::WaitingForInput { target } => target.tones.clone(),
        GamePhase::Matched { chord } => chord.tones.clone(),
        _ => Vec::new(),
    }
}

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let tones = get_target_tones(app);
    let active_color = match &app.phase {
        GamePhase::Matched { .. } => Color::Green,
        _ => Color::Yellow,
    };

    let mut lines: Vec<Line> = Vec::new();

    // Display chord tones vertically (highest to lowest by convention)
    // Simple representation: each tone on its own "staff line"
    if tones.is_empty() {
        for _ in 0..5 {
            lines.push(Line::from(Span::styled(
                "  ─────────────",
                Style::default().fg(Color::DarkGray),
            )));
        }
    } else {
        // Show tones from top (last) to bottom (first) on simplified staff
        let mut display_tones = tones.clone();
        display_tones.reverse();

        for tone in &display_tones {
            let name = format!("{}", tone);
            lines.push(Line::from(vec![
                Span::styled("  ───", Style::default().fg(Color::DarkGray)),
                Span::styled(
                    format!(" {} ", name),
                    Style::default()
                        .fg(active_color)
                        .add_modifier(Modifier::BOLD),
                ),
                Span::styled("───", Style::default().fg(Color::DarkGray)),
            ]));
            // Space between lines
            lines.push(Line::from(Span::styled(
                "  ─────────────",
                Style::default().fg(Color::DarkGray),
            )));
        }
    }

    let block = Block::default()
        .title(" Staff ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));

    let paragraph = Paragraph::new(lines).block(block);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Build to verify**

Run: `cargo check`

- [ ] **Step 3: Commit**

```bash
git add src/ui/notation.rs
git commit -m "feat: simplified staff notation showing chord tones"
```

---

### Task 11: Footer widget (`ui/footer.rs`)

**Files:**
- Modify: `src/ui/footer.rs`

- [ ] **Step 1: Implement footer rendering**

```rust
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::Paragraph,
    Frame,
};

use crate::app::App;

pub fn render(frame: &mut Frame, app: &App, area: Rect) {
    let line = Line::from(vec![
        Span::styled(" [Enter]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::raw(" Skip  "),
        Span::styled("[Q]", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
        Span::raw(" Quit"),
        Span::raw("                  "),
        Span::styled(
            format!("Measure: {}/100", app.measure_num),
            Style::default().fg(Color::DarkGray),
        ),
    ]);

    let paragraph = Paragraph::new(line);
    frame.render_widget(paragraph, area);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/footer.rs
git commit -m "feat: footer widget with controls and measure counter"
```

---

### Task 12: Update main.rs to use TUI

**Files:**
- Modify: `src/main.rs`

- [ ] **Step 1: Replace main function with TUI setup**

```rust
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
mod tui;
mod ui;

mod exits {
    pub const SUCCESS: i32 = 0;
    pub const ERROR: i32 = 1;
}

fn main() -> Result<(), Box<dyn Error>> {
    use std::process::exit;
    let env = Env::default().filter_or("RUST_LOG_LEVEL", "error");
    env_logger::init_from_env(env);

    let input_rx = new_input_thread()?;
    let (msg_tx, msg_rx) = mpsc::channel();

    let mut terminal = tui::init()?;

    let result = App::new(input_rx, msg_tx)?.run(msg_rx, &mut terminal);

    tui::restore()?;

    match result {
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
```

Note: `print::intro()` is no longer called because the TUI handles the intro screen via `GamePhase::Intro`.

- [ ] **Step 2: Build and test**

Run: `cargo build`
Run: `cargo run` (test manually: select difficulty, see TUI render, chords display, quit with Q)

- [ ] **Step 3: Commit**

```bash
git add src/main.rs
git commit -m "feat: wire up ratatui TUI in main entry point"
```

---

### Task 13: Visibility and import fixes

**Files:**
- Modify: `src/tone.rs` (only visibility, if needed)
- Modify: `src/chord.rs` (only visibility, if needed)

The `ui/piano.rs` and `ui/notation.rs` modules need to access `Tone.idx` and `Chord.tones`. These are already `pub(super)` which may not be visible to `ui/` modules. If `cargo check` fails due to visibility:

- [ ] **Step 1: Widen field visibility if needed**

In `src/tone.rs`, change `pub(super)` to `pub(crate)` for `Tone.idx`:
```rust
pub struct Tone {
    pub(crate) idx: i8,
    tone: NeutralTone,
    variant: ToneVariant,
}
```

In `src/chord.rs`, change `pub(super)` to `pub(crate)` for `Chord.tones` and `Chord.tonic`:
```rust
pub struct Chord {
    pub(crate) tonic: Tone,
    chord_type: ChordType,
    inversion: Inversion,
    pub(crate) tones: Vec<Tone>,
}
```

- [ ] **Step 2: Build and verify**

Run: `cargo check`
Expected: clean compilation

- [ ] **Step 3: Commit**

```bash
git add src/tone.rs src/chord.rs
git commit -m "chore: widen field visibility to pub(crate) for TUI access"
```

---

### Task 14: End-to-end manual testing and polish

**Files:**
- Potentially any `src/ui/*.rs` file for layout tweaks

- [ ] **Step 1: Run the app and test all game phases**

Run: `cargo run`

Test checklist:
- [ ] Difficulty selection screen renders (p/g keys work)
- [ ] "Get Ready" / "Start Playing" phases render
- [ ] Measure start shows progression tree correctly
- [ ] "PLAY" target shows correct chord and tones
- [ ] Piano keyboard highlights correct keys for chord
- [ ] Guitar fretboard shows dots at correct positions
- [ ] Staff notation shows all chord tones
- [ ] Enter key skips chord, score updates
- [ ] Measure timeout shows red timeout message
- [ ] Q quits cleanly, terminal restored to normal
- [ ] Summary screen shows final stats
- [ ] With MIDI keyboard: notes are detected and matched

- [ ] **Step 2: Fix any layout or rendering issues found**

Adjust `Constraint` values in `ui/mod.rs` if widgets overflow or are too cramped. Adjust padding/spacing in individual widgets.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete TUI with piano, guitar, and notation visualization"
```

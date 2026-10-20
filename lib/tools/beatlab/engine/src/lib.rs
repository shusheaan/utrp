//! Offline beatbox segmentation, experimental clustering and Standard MIDI export.
//! No host, GUI, audio device, network or filesystem dependency in the core.
mod analysis;
mod features;
mod ffi;
mod midi;
mod model;

pub use analysis::analyze;
pub use midi::{midi_file, quantized_beat};
pub use model::{Event, Options, Pattern};

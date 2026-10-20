//! Only C ABI boundaries use unsafe. No audio-thread calls; caller owns input buffers.
use crate::{Options, Pattern, analyze, midi_file};
use std::ffi::{CStr, CString, c_char};

fn response(result: Result<serde_json::Value, String>) -> *mut c_char {
    let value = match result {
        Ok(value) => serde_json::json!({"ok":true,"value":value}),
        Err(error) => serde_json::json!({"ok":false,"error":error}),
    };
    CString::new(value.to_string())
        .expect("JSON escapes interior NUL")
        .into_raw()
}

/// # Safety
/// `samples` must reference `count` readable f32s; `options` a valid NUL-terminated string.
/// Returned allocation must be released exactly once with beatlab_free.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn beatlab_analyze(
    samples: *const f32,
    count: usize,
    rate: u32,
    options: *const c_char,
) -> *mut c_char {
    let result = std::panic::catch_unwind(|| {
        if samples.is_null() || options.is_null() || count == 0 || count > 192_000 * 60 {
            return Err("Invalid analysis buffers".into());
        }
        // SAFETY: Pointer extent and C string validity are guaranteed by the C caller.
        let text = unsafe { CStr::from_ptr(options) }
            .to_str()
            .map_err(|e| e.to_string())?;
        let config: Options = serde_json::from_str(text).map_err(|e| e.to_string())?;
        let audio = unsafe { std::slice::from_raw_parts(samples, count) };
        serde_json::to_value(analyze(audio, rate, &config)?).map_err(|e| e.to_string())
    })
    .unwrap_or_else(|_| Err("Analysis failed internally".into()));
    response(result)
}

/// # Safety
/// `pattern` is a valid NUL-terminated string. Release result with beatlab_free.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn beatlab_midi(pattern: *const c_char) -> *mut c_char {
    let result = std::panic::catch_unwind(|| {
        if pattern.is_null() {
            return Err("Missing pattern".into());
        }
        // SAFETY: The caller guarantees C string lifetime and termination.
        let text = unsafe { CStr::from_ptr(pattern) }
            .to_str()
            .map_err(|e| e.to_string())?;
        let data: Pattern = serde_json::from_str(text).map_err(|e| e.to_string())?;
        Ok(serde_json::json!(midi_file(&data)?))
    })
    .unwrap_or_else(|_| Err("MIDI export failed internally".into()));
    response(result)
}

/// # Safety
/// `value` must be null or an unreleased pointer returned by this library.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn beatlab_free(value: *mut c_char) {
    if !value.is_null() {
        // SAFETY: Reclaims exactly the allocation returned via CString::into_raw.
        drop(unsafe { CString::from_raw(value) });
    }
}

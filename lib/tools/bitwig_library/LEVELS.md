# Library fader levels

[中文](LEVELS.cn.md)

## Current settings, 2026-10-21

- All audible sound tracks (MIDI, AG guitar, Pad and Beat Lab): **−2 dB**.
- Folder buses, shared MIDI input and Master: **0 dB**.
- `GUITAR - raw detection`: retained at **−∞**, for pitch detection without doubling dry guitar.
- These are fader positions, not perceived-loudness matching. Plugin internal gain, audio routing, Arm, Monitor, Active, Mute and Pan are unchanged. Hot patches or simultaneous piano/guitar can still clip; start with low hardware volume.

## Recipe and scope

`levels.toml` is the current recipe; `levels.js` is an explicit one-shot maintenance helper. Neither production `Library.control.js` nor `Keystation.control.js` loads it. Never add it to startup, which would overwrite later user fader changes. The initial guitar fader in `ambient_guitar.toml` is also −2 dB. The historical migration builder still preserves source-project levels; this recipe is not forced onto ordinary projects.

Call `scheduleLibraryLevels(host, config, apply)` during controller init to create API proxies; derive `config` from TOML. `apply=false` verifies read-only; only `true` writes volumes. Guards check the Library project name, shared-track signature, recording disabled and bank capacity. Folded/inactive tracks are included, raw detection is protected, and other track state is unchanged. Master is deduplicated when already included by ALL_CHANNELS.

On this Bitwig 6.1.4 host raw volume is cube-root amplitude: `dB = 60 × log10(raw)`, not direct amplitude. Verification reads the host's `displayedValue()` to confirm the actual dB value.

## Validation and recovery

- Live read-only verification: **114 tracks including Master, 1 protected, 0 errors**. Audible sounds −2 dB, buses/shared MIDI/Master 0 dB, raw detection retained at −∞.
- 406 related pytest cases pass, covering project scope, recording protection, capacity, Master deduplication, read-only mode, protected raw volume and unchanged non-volume state.
- Saved `~/storage/daw/Library/Library.bwproject`. No full DAW restart, real performance peak measurement or perceived-loudness validation this round.
- `~/storage/daw/Backups/library-levels-20261021T201337Z/Library-live-before.bwproject` is the saved pre-change project; `Library.bwproject` alongside it is an earlier on-disk copy.
- Temporary host scripts removed; production Keystation deployment matches source. Evidence: `target/library-levels/`. No commit/push; finish with a Storage recovery snapshot.

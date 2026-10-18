# Bitwig floating plugin layout

A small Sway window policy, separate from plugin DSP and the Bitwig controller.
It floats external editors and centers Chord Lab with the primary instrument/effect,
keeping the track area available. Extra effects use the right-hand gaps first.

## Behavior and limits

- Requires a `BitwigPluginHost-*` process, a transient parent belonging to the
  Bitwig main window, and a ` / ` editor title. Main windows, dialogs, unrelated
  applications, REAPER and scratchpad are excluded.
- Preserves native dimensions and internal zoom except Surge XT Effects: new editors
  and leftover oversized editors reset to the verified 600×490 (configurable). It can
  remember a tiled 1763×1440 size even after floating. Surge XT instruments are NOT
  resized. Never modifies audio or parameters.
- Chord Lab alone is centered; with Surge XT/sfizz or the first effect it forms a central
  pair, Chord Lab on the left. Extra windows preserve that pair when they fit. If fixed
  centering fragments space, a compact group is centered only if it fits more editors.
- Configuration in `layout.toml`
  reserves 400 logical pixels left, 80 top, 48 bottom, 16 right and 16 between editors.
- Checks every 0.4 seconds; repacks on editor creation/closure, title/size/workspace
  changes. Position and focus changes are ignored, so manual dragging is respected
  until the next layout change. No focus, workspace-switch or editor-close commands.
- If editors cannot fit, notifies instead of shrinking/hiding them. Overflow windows
  remain where they were and may overlap: arbitrary window counts cannot fit a finite display.
- Workspaces are independent; offset coordinates have unit coverage, but live validation
  used the current single 3440×1440 display only.

## Deployment and operation

- Source/config: `layout.py`, `layout.toml` in this directory.
- Enabled service: `~/.config/systemd/user/utrp-plugin-windows.service`.
- Sway include: `~/.config/sway/utrp-plugin-windows.conf`. The existing main config
  is a symlink to `~/work/gral/arch/sway/config`; only an include was appended.
- On Sway startup/reload, the include imports the current `SWAYSOCK` and restarts
  the service. Bitwig does not need restarting.
- After editing spacing: `systemctl --user restart utrp-plugin-windows.service`.
- Temporary stop: `systemctl --user stop utrp-plugin-windows.service` (Sway reload restarts it).
- Permanent removal: remove that include and run
  `systemctl --user disable --now utrp-plugin-windows.service`.
- Move a borderless editor with Sway's existing `Super + left-button drag`.
  Open/close it with the plug-in window button in Bitwig's device panel.
- This is local desktop configuration, not embedded in `.bwproject` or CLAP files.

## Validation — 2026-10-18

- Reproduced tiled Surge XT Effects compressing the main window to 1720 pixels wide;
  floating restored its native 600×490 and the main window's 3440×1440 size.
- Four live editors: Chord Lab 920×703, two Effects instances 600×490 each, Dragonfly
  Hall 920×345. Two rows, no overlaps.
- Surge XT instrument at its existing 1141×711 and sfizz at 775×515 both packed next
  to Chord Lab; internal zoom was not changed.
- Close/reopen, manual drag preservation, focus preservation, service restart and
  Sway configuration validation passed.
- Unit coverage includes right-to-left placement, wrapping, overflow, workspace
  isolation, editor filtering and 300 randomized layout invariants. Strict mypy passed.
- Evidence: `target/plugin-windows/` (ignored). No audio injection or sound-parameter edits.

Reference: [official Sway commands](https://github.com/swaywm/sway/blob/master/sway/sway.5.scd).

## Instrument combination recheck — 2026-10-18

Fixed creation-order fragmentation: small effects opened before a large instrument
could incorrectly report overflow for five-editor combinations that actually fit.
Chord Lab remains anchored; remaining windows now sort by descending height and width.

Added **340 opening-order cases across 11 real-dimension combinations**. Twenty failed
before the fix; all pass now. Together with existing layout/Library tests: **368 passed**,
plus strict mypy. This is not an optimal arbitrary-rectangle packing solver; two large
synth editors, for example, may still exceed the available region.

Live Bitwig coverage: Acoustic Piano, Soft Piano, Suitcase EP, DX EP, Organ, Church Organ,
Warm Veil, Dark Choir, Silver Haze, Glass Air, Soft Prism, Echo Bloom, Cloud Halo.
Checks inspect actual counts, floating state, bounds, pairwise 16 px gaps and the main
window geometry. Guitar FX were opened in different orders, including four-editor wrapping.

Library's exclusive-audition controller deactivates other sound tracks, closing their
editors. That is existing controller behavior, not this tool hiding windows. Cross-track
five-editor mixtures were consequently tested using measured dimensions in pure layout
regressions, **not claimed as simultaneous live windows in the exclusive Library**.
Evidence: `target/plugin-window-combinations/`.

A further live cross-track reopen exposed a remembered 1763×1440 Surge XT Effects
size. Added the narrowly scoped FX reset, with tests for late oversized restoration,
retaining reasonable manual sizes and never resizing Surge XT instruments. Rechecked
three alternating Cloud Halo / Soft Prism opening rounds afterward.

## Center-first update — 2026-10-18

The rules above supersede the earlier right-anchor arrangement. Library controller 0.7
opens the primary device and shared Chord Lab for known sound/guitar tracks. Auxiliary
tracks with a local Chord Lab open that instance without changing the audible sound.
It inspects the first four top-level devices (two on the shared track), not nested chains,
and closes the old track's editor set. Reselecting a sound reopens its editors.

Opening depends on Bitwig selection events; deliberately closed windows are not forced
open by polling. Clicking an already selected track may not produce a selection event:
select another track and return, or use the device editor button.

Coverage adds centered singleton/pairs, instrument priority, stable fitting cores, closing
and local Chord Lab selection. The 340 combination orders now use actual plugin names.
Evidence: `target/plugin-windows-center/`. Window layout does not change audio routing.

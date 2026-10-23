# Standalone playback and Library sound selection

[中文](STANDALONE.cn.md) · [Game mode](GAME.md)

## Current scope: standalone deferred; polish Bitwig first

The latest user decision is to **defer standalone development and polish the plugin inside Bitwig only**. Do not add sound menus or a Library track-selection bridge.

If standalone work resumes, the requested behavior is to reuse the piano and guitar sounds last saved in Bitwig; sound changes remain in Bitwig. Third-party state restoration and native-device compatibility still need separate validation, not a promise to load every Bitwig sound. Catalog work and the earlier plan below are historical; unchecked items are not the active scope.

## Historical actual status — 2026-10-22

The requested application should use the current piano, guitar effects, physical MIDI, computer keys, and game without Bitwig, with the existing Library groups available inside the UI. No new system service.

**Neither the standalone audio host nor the in-plugin sound-selection UI is implemented.** The current JUCE Standalone was launched with Bitwig fully closed. Its editor opens and its output endpoint connects to Spark GO, but it loads no piano or guitar effects and has no usable sound engine chain. An endpoint is not proof of playback. Sway also tiles this ordinary application fullscreen by default; a standalone window policy is still needed. Only a temporary floating check was performed, without new desktop rules. Test settings were isolated in `target/chordlab-live-game/standalone-home/`. The test application was closed and Library reopened afterward.

## Completed catalog preparation

The source is a fresh native Bitwig Export DAWproject, not an older migration artifact:

```sh
python lib/tools/bitwig_library/catalog.py \
  target/chordlab-live-game/library-current.dawproject \
  target/chordlab-live-game/sound-catalog.json
```

- 102 entries: 98 MIDI sounds and 4 guitar effects presets, preserving 8 existing groups.
- Active choices: `Basic Keys / 02 Soft Piano` and `Ambient Guitar / AG - 01 Glass Air`.
- Keeps track and downstream bus/master device order, volume, pan, mute, preset archive paths, and hashes. Does not extract archive paths, load plugins, or modify tracks. Output uses exclusive creation to prevent overwrites.
- Explicit native dependencies: six Basic Keys sounds inherit Bitwig Reverb; `C2-distant` uses Bitwig Tool. A third-party host cannot load these directly; silently omitting them is not identical playback.
- Scope is **sounds managed by the Library controller**, not Bitwig's global browser. `playback_verified=false`: a valid catalog does not establish standalone playback.
- 17 new catalog tests; uncached strict mypy passes.

## Historical implementation and acceptance plan (paused; sound menus cancelled)

- [x] Read current project sounds, groups, active choices, and native dependencies.
- [ ] Add an in-process lightweight audio host, starting with current sfizz Soft Piano, then original-format CLAP instruments and guitar effect chains. Restore preset state, resources, and levels. Report missing plugins/samples and unsupported devices rather than silently substituting sounds.
- [ ] Reuse the normal/game engine: hardware MIDI → Chord Lab → piano; dry guitar input → Guitar Frontend → ch15 judging, parallel guitar input → FX → output. Demo ch16 reaches only the piano and must not feed back into scoring. Computer game input needs single-note/octave controls, not auto-chord shortcuts.
- [ ] A compact Sound entry exposes independent Piano/Guitar selectors grouped as in Library, with current selection and compatibility. G alone controls the game sidebar. Settings select input, output, and MIDI devices manually and restore the last choices. Switching safely releases owned notes without resetting the game or changing the other group.
- [ ] Inside Bitwig, the same UI needs an explicit bridge through the existing Library controller to actually select tracks, not just change a label. Restrict it to Library; keep the shared editor/game alive during sound changes; do not auto-arm or affect other projects. No new background service.
- [ ] Validate both environments: hardware MIDI, computer keys, Spark input, separate scoring, timed demos, preset switching, missing devices, restart restoration, layout transitions, and normal regressions. Disclose and agree native-FX substitutions rather than labeling them identical restoration.

Preset/sample binaries remain in local Storage or ignored `target/`, not Git.

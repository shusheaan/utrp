# UTRP music tools

[中文](README.cn.md) · Wrap-up index, 2026-10-20

Directories are flat and responsibility-based; not every directory is a separate plugin. This wrap-up updates navigation and stale documentation, without moving paths referenced by builds, controllers or systemd.

## Current plugins

| Directory | Responsibility |
|---|---|
| [chordlab/](chordlab/README.md) | Current embedded harmony/drawing engine and resources; required by CLAP, not a second legacy product |
| [chordlab_clap/](chordlab_clap/README.md) | CLAP wrapper, host integration and keyboard handling for that same Chord Lab product |
| [beatlab/](beatlab/README.md) | Independent Beat Lab project: Rust `engine/`, JUCE `plugin/`, integration `tests/`; no Chord Lab runtime dependency |
| [guitar_frontend/](guitar_frontend/README.md) | Independent monophonic guitar detection CLAP, separate from Beat Lab |

Beat Lab 0.3.1 is deployed for recording/analysis/file-export prototyping. Actual recognition still needs human review. Direct MIDI drag-out, host clip creation and standalone cross-take Sound Set templates are unfinished. Structural wrap-up does not mean all product requirements are complete.

## Host integration and infrastructure

- [bitwig_library/](bitwig_library/README.md): Library controller; exclusive audition is Library-only.
- [audio_routing/](audio_routing/README.md): output priorities and dedicated guitar/microphone routing.
- [plugin_windows/](plugin_windows/README.md): floating plugin window layout.
- [daw_backup/](daw_backup/README.md): live Storage directory links, recovery inventory and private snapshots.
- [library/](library/README.md), `reaper/`: original library and REAPER support; historical compatibility tools are retained.

## Other research and tools

- `pipeline/`, `repatch/`: timbre/drum transcription, reverse engineering and batch processing.
- `harmony/`, `simulate/`: harmony exploration and simulation adapters around the shared Rust library.
- `endless/`, `magdalene/`, `sega-universe/`, `tev-woods/`: timbre research/reconstruction recipes.
- [guitar_poly/](guitar_poly/README.md): unaccepted historical dyad/triad research, not the production monophonic signal chain.

## Storage and Git boundaries

| Content | Location |
|---|---|
| Plugin source, configuration recipes, tests and docs | This repository's `lib/tools/` |
| Surge text patches | `lib/surge/` |
| Current Bitwig project and audio assets | `~/storage/daw/Library/Library.bwproject` and corresponding Storage directories |
| User CLAP binaries | `~/storage/daw/UserData/.clap/`; `~/.clap` is a directory symlink |
| Live music preferences and resources | `~/storage/daw/UserData/`; entry points in `daw_backup/live.toml` |
| Beat Lab Standalone | `~/storage/daw/Tools/BeatLab/Beat Lab` |
| Source/configuration recovery snapshots | `~/storage/daw/Recovery/` |
| Bitwig installation | `~/opt/bitwig-studio-6.1.4/`, outside UTRP plugin source |
| Shell launch commands | GRAL `arch/zshrc`, targeted by `~/.zshrc` |

`beatlab/build/`, `beatlab/target/`, `simulate/target/` and root `target/` are Git-ignored local build/test caches, not source size. Root `target/` retains historical evidence/builds; nothing was deleted this round. Cleanup requires separate review of regenerable dependencies and evidence, but does not block wrap-up.

Files on disk or in Storage snapshots are not commits/pushes. Beat Lab source is still uncommitted. Live preference directory links and point-in-time snapshots serve different purposes.

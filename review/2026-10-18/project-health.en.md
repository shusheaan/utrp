# UTRP final wrap-up — 2026-10-18

[中文](project-health.cn.md) · [Index](README.md)

## 1. Executive summary
Automated software checks pass; live preferences physically reside on Storage with home directory symlinks. Overall **Yellow**: Spark GO is currently absent; no fresh physical guitar/pedal or clean-machine recovery acceptance. No blanket 100% claim; no Git commit/push.

## 2. Structure and volume
src/tests contain the Rust trainer/generator; study contains atlas tools; covers contains practice material; lib/surge contains 88 FXPs; lib/tools contains plugins, controllers, rendering research and deployment. Working-tree inventory excluding target/review: 80 Python, 38 Rust, 19 C++, 218 Markdown files. See file-volume.json.

## 3. Architecture
JSFX is Chord Lab's embedded CLAP engine, not a separately deployed legacy product. Guitar Frontend is a separate mono detector; guitar audio FX and display-only MIDI are separate branches. Library controller owns host selection/audition; Sway/PipeWire services own window/output policy, not plugin DSP. Host projects/routing are not interchangeable.

## 4. Robustness and quality
Installed binaries match current builds by SHA-256. Installed CLAP probe covers mixed same-note retrigger, 14 pedal channels, display-only isolation, held H/L, state/lifecycle and 12 rate/block combinations. Guitar Release/UBSan pass; mono only, not zero-error or keyboard-latency recognition.

## 5. Workflow crossings and fixes
Corrected stale scripts references to study in tests/README, default atlas output directories and cover index. Build documentation now builds all CLAP targets instead of missing six CTest executables on a fresh build. Current-state entry points added above retained historical lib/Bitwig notes. Successful snapshots atomically update LATEST; only asset snapshots update LATEST_FULL.

## 6. Tests and simulation
Full Python: 1605 passed using system Python 3.14 plus existing Surge render-environment site-packages. Rust: 119 passed, 3 pre-existing long exhaustive coverage tests ignored; strict Clippy passes. Chord CTest 9/9; Guitar Release 2/2 and UBSan 2/2; installed CLAP probe passes. Seed=42 musical simulation produces 24 identical replay events with valid MIDI pitches. No coverage percentage or fresh physical-performance claim. Financial backtest/RAS/R/single-period golden lanes are inapplicable; musical pixel/voicing regressions ran in CTest.

## 7. Storage integrity
All 10 live links pass; physical data: ~/storage/daw/UserData; project: ~/storage/daw/Library/Library.bwproject. Credentials/runtime caches remain at home. Legacy standalone Surge host settings remain snapshot-only; actual in-DAW Surge preferences migrated. Recovery is rollback, not primary data. Same-disk Storage requires independent-disk backup. See daw_backup/README.md.

## 8. Documentation
Fixed current navigation, atlas paths, build command and Recovery pointers; bilingual CLAP/storage/wrap-up updates included. Historical docs retained; no claim of translating every Markdown file. Current entry-point link check: docs-check.log. No retired research or user assets deleted.

## 9. Confirmed limitations
Spark GO is absent; both Keystation ports present. Output/window services active/enabled; Woo EQ is correctly selected without Spark. No new unplug simulation or physical guitar/pedal test. No clean-machine restore; full Python lane depends on the existing rendering environment documented by pipeline. Working-tree changes are saved and snapshotted, not committed/pushed.

## 10. False alarms and pending items
plugin-states is cleared/recreated by the host and correctly excluded as runtime scratch. Both read-only reviewers' stale-path, missing-build-target and stale-navigation findings were confirmed and fixed. No live-preference fallback to home or installed/build plugin mismatch found.

## 11. Next action
Stop extending this round. When Spark reconnects, perform a short physical check of mono display-only routing, guitar FX, keyboard retrigger and held/released pedal. No migration redo needed. Close DAWs and copy to independent storage before reinstall; user decides when to commit Git.

# Validation commands and results

cwd `/home/shu/work/utrp`, 2026-10-18. No financial backtest pipeline exists.

| Lane | Command / evidence | Result |
|---|---|---|
| Full Python | `PYTHONPATH="$PWD:/home/shu/.cache/timbre-pipeline/venv-render/lib/python3.14/site-packages" PYTHONPYCACHEPREFIX=/tmp/utrp-wrapup-pycache python -m pytest -q tests lib` — python-final.log | 1605 PASS |
| Rust | `cargo test --offline` — rust-test.log | 119 PASS, 3 existing exhaustive tests ignored |
| Clippy | `cargo clippy --offline --all-targets -- -D warnings` — clippy.log | PASS |
| Chord build/CTest | `cmake --build target/chordlab-clap-build/build -j2`; `ctest --test-dir target/chordlab-clap-build/build --output-on-failure` | 9/9 PASS, 3.92s |
| Guitar build/CTest | `cmake --build target/mono-pill-wrapup/guitar-build -j2`; `ctest --test-dir target/mono-pill-wrapup/guitar-build --output-on-failure` | 2/2 PASS, 2.48s |
| Guitar UBSan | same commands with `guitar-ubsan` | 2/2 PASS, 21.25s |
| Installed CLAP | `target/chordlab-clap-build/build/clap_probe "$HOME/.clap/Chord Lab.clap"` with actual DISPLAY | PASS; installed-clap.log |
| Live preferences | `python lib/tools/daw_backup/live.py --check` | 10/10 PASS |
| Musical seeded smoke | build simulate Cargo manifest; `utrp-sim --events 24 --seed 42` twice | 24 identical events; valid MIDI range |
| Backtest / RAS / R | No project-defined lanes | N/A, not falsely counted as pass |
| Single-period golden | No financial-period golden; capsule pixels and voicing tests serve musical regression | musical CTest PASS |
| Monte Carlo | no dedicated MC lane; seeded music simulation and existing Rust sampling tests run | partial analogue, not financial MC |
| Coverage percentage | no instrumented coverage run | not measured |
| Physical guitar/pedal | Spark GO absent | not run this round |
| Clean-machine recovery | no reinstall performed | not run |

Initial Python attempts are retained: python.log (six collection errors: stale scripts imports and missing soundfile), study-python.log (stale generated index), daw-python.log (missing surgepy). Paths/index fixed; existing render dependency environment used rather than hiding/skipping tests or installing packages. Final results supersede those failures. Build/probe tests used current cached dependencies, not a clean compiler/dependency installation.

# Evidence ledger / 证据

- Date: 2026-10-18, US/Eastern. Repository /home/shu/work/utrp, main, HEAD 65e3ffe050adc73ad8b0e5480f8d9f498266f9d4 plus dirty working tree.
- Scope: final DAW storage/deployment verification plus full repository test discovery and small broken-entry fixes; no new music features.
- Test commands, PASS/FAIL/N/A and logs: test-results.md. Wall times are recorded when returned by test runner; missing timings were not invented.
- Two built-in read-only reviewers independently checked storage/architecture and tests/docs; no workmux, no persistent branches/worktrees.
- GUI save/restart and preference-write evidence belongs to the immediately preceding migration round; this follow-up used read-only service/device checks and installed-plugin probes, no audio injection into the live DAW.
- Actual follow-up hardware: Keystation USB MIDI and Transport present; Spark GO absent; Woo Audio present; default eq_woo_in. Both UTRP services active/enabled, audio dry-run proposes no change. Audio links saved in audio-links.txt; window-tree.json describes current workspace windows.
- Installed/build Chord Lab SHA256: 5c02efab99369a046691df44c3d22a84d707da13f6c8976c4d258a9e39ba42d3.
- Installed/build Guitar Frontend SHA256: 1235753fbae32d41cd1a94f181738b4c2e5135cfc7a197af3cc4f95dc2d7c699.
- Snapshot pointer handling now automated in snapshot.py; snapshots exclude credentials. Final snapshot location is discoverable through ~/storage/daw/Recovery/LATEST; full assets through LATEST_FULL.
- No commit/push or broad deletion performed. Existing unrelated working-tree changes preserved. No clean-machine restore or renewed physical guitar acceptance.

# DAW reinstall recovery

[中文](README.cn.md)

## Live data, not a synchronized copy

As of 2026-10-18, the **10 directories** in `live.toml` physically reside in
`~/storage/daw/UserData/`, mirroring their former home-relative paths. Home contains
directory symlinks for Bitwig prefs, view-settings, library and installed-packages;
`Bitwig Studio` user content/controllers; `.clap`; both Surge user directories; SFZTools;
and REAPER configuration. Writes through the original home paths go straight to Storage.
Unsaved application memory still requires saving or normal shutdown. Directory symlinks
survive atomic replacement of files inside them. Recovery snapshots are historical rollback only.

```sh
python lib/tools/daw_backup/live.py          # Preview only
python lib/tools/daw_backup/live.py --check
# Save and close DAWs / standalone instruments first:
python lib/tools/daw_backup/live.py --apply  # Migrate, or relink after reinstall
python -m pytest -q lib/tools/daw_backup/test_live.py lib/tools/daw_backup/test_snapshot.py lib/tools/bitwig_library/tests/test_controller.py
```

The tool only uses same-filesystem rename; it refuses collisions, cross-filesystem moves,
unexpected links and merging. After reinstall, **relink existing UserData before launching**
instead of overwriting live data from old snapshots. Review and preserve freshly generated
home defaults separately if they conflict. Changed usernames/mount points require auditing
absolute paths and internal UTRP/gral links. Application binaries were not relocated.

**Boundaries:** activation, caches and telemetry remain at home; entire `.config` and
`.BitwigStudio` roots were not moved. Legacy `.config/Surge XT.settings` is the standalone
JUCE host's settings file and remains at home with snapshot protection, not a fragile
single-file symlink. Actual in-DAW Surge user preferences, including
`.Surge XT/SurgeXTUserDefaults.xml`, are live on Storage. `plugin-states` was observed to be emptied and recreated at startup and is excluded as
runtime scratch data. Sway/audio/service deployment
rules remain managed by repository source plus snapshots; WirePlumber runtime device
state was not moved. This is not a claim that every system preference has been relocated.

Initial migration compared 13,636 file/link entries (including subsequently excluded
`plugin-states`): directory and file inodes, sizes and modes
were unchanged; non-content-package files also passed SHA-256 comparison, and internal
symlink targets were preserved. No clean-machine reinstall has been performed.


## Ownership

UTRP owns source, recipes and tests for Chord Lab, Guitar Frontend, Bitwig controllers,
audio routing, plugin-window layout and this backup tool. Persistent projects and samples
live under `~/storage/daw/`; preserve the whole directory, not just `Library.bwproject`.
Private recovery snapshots live in `~/storage/daw/Recovery/<UTC timestamp>/`.

Snapshots capture deployed CLAP binaries/controllers, Bitwig preferences, Surge skins and
user patches, sfizz settings, REAPER configuration, Sway/audio rules, user services and
launchers. Symlinks are dereferenced, preserving custom content from external gral paths.
Uncommitted, non-ignored source is included in `utrp-working-tree.tar.gz`. **This operation
does not commit or push Git** and the source archive is not a Git history/remote backup.
Large assets and private preferences stay outside Git. Activation/license credentials,
telemetry and caches are excluded; third-party LICENSE notices are preserved.

## Create and verify

```sh
python lib/tools/daw_backup/snapshot.py
# Also capture Bitwig 6.1.4, installed content and system plugin/factory resources:
python lib/tools/daw_backup/snapshot.py --include-assets
python -m pytest -q lib/tools/daw_backup/test_snapshot.py lib/tools/bitwig_library/tests/test_controller.py
```

Snapshots never overwrite earlier ones. All tar payloads are read back and SHA-256 values
are recorded in `manifest.json`; a remaining `INCOMPLETE` marker means failure.
The Chinese companion includes a checksum verification command. **Close audio applications
normally before the final pre-reinstall snapshot**: running applications may have unsaved
in-memory preferences. Current desired settings are Spark GO USB and manual 128 samples
(revert to 256 if unstable); verify explicitly after restoration. Glass Air is saved at
−9 dB, other AG defaults −12 dB; future user saves take precedence.

## Restore deliberately

1. Preserve Storage and restore the repository, preferably with the original username,
   `~/work/utrp` and `~/storage` paths. Projects, samples and launchers may use absolute paths.
2. Use `packages.txt` as a version inventory, not a blind install list. Restore compatible
   PipeWire/WirePlumber, Sway and realtime permissions. Reinstall distribution plugins or
   rebuild CLAP for a different distribution/architecture.
3. Install Bitwig. Optional runtime archives include the current installation, content,
   CLAP/VST3 and Surge factory resources; do not blindly overwrite another system's `/usr`.
4. Close DAWs. If UserData is intact, run `live.py --apply` to relink the latest live data.
   For snapshot rollback only, extract to staging and review before restoring physical targets,
   not replacing home symlinks. Restore `.clap`, controller scripts, prefs, skins, presets, and persistent samples.
   Legacy REAPER configuration is retained, but CLAP remains the active product line.
5. Restore the two UTRP user services and audio/window rules; check Sway includes and
   `focus_follows_mouse no`. Reload user systemd and enable the services. Old WirePlumber
   device IDs/volumes may not match new hardware.
6. Log in/activate again; Bitwig activation and REAPER licenses are not archived. Private
   prefs can still contain device identifiers and local paths; never publish them.
7. Open Library; check Spark input/output, buffer, both Keystation ports, pedal polarity
   (power on with pedal released), all plugins/AG recipes, and guitar channel 2→15 display routing.
8. Recording projects must not use the reserved Library names. The existing controller
   allows exactly `Library` and historical `Library-migration`, with matching shared-track
   and plugin structure. Other projects do not get exclusive activation/arming/monitoring,
   editor management or key sync. Keystation Transport and global audio priority are separate.
   The Exclusive audition setting is a host preference, not embedded in the project;
   `.bwproject` stores resulting track states and routing. Restore Active/Arm/Monitor manually
   when creating a multitrack recording project.

## Evidence and limits

Regression tests cover unchanged track states in ordinary projects and cancellation of
queued Library actions after switching projects. Archive tests cover materialized symlinks,
uncommitted source and credential exclusion. This is not a clean-machine restore test.
Storage currently shares the home disk: it protects against losing home configuration,
**not disk failure or formatting that partition**. Make an independent-disk backup before reinstalling.

Large runtime assets use uncompressed `.tar` and preserve vendor symlinks, including absolute `/usr/bin`→`/opt` installation links. Home customization archives still materialize deployment links. For the unpacked Bitwig installation, use its `opt/bitwig-studio/bitwig-studio` executable rather than assuming bundled absolute launch links work from home.

### 2026-10-18 verification

- 28 backup, live-migration and Library-controller regression tests passed.
- Bitwig reopened with Chord Lab / sfizz; Audio still showed Spark GO USB and 128 samples.
- A temporary GUI preference edit changed Storage prefs content and write time. The original
  setting was restored, followed by normal Ctrl+S / Ctrl+Q shutdown; all 10 links remained valid.
- Only storage deployment changed; instruments, MIDI routing and audition behavior were not
  modified. No commit/push was performed.

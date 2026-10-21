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
in-memory preferences. Current desired settings are PipeWire / System Out and manual 128 samples
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
5. Restore `utrp-plugin-windows`, `utrp-audio-output` and `utrp-guitar-input` user services and audio/window rules; check Sway includes and
   `focus_follows_mouse no`. Reload user systemd and enable the services. Old WirePlumber
   device IDs/volumes may not match new hardware.
6. Log in/activate again; Bitwig activation and REAPER licenses are not archived. Private
   prefs can still contain device identifiers and local paths; never publish them.
7. Open Library; check the [fixed routing](../audio_routing/README.md) (`Spark-GO-Guitar` input, Spark playback), buffer, both Keystation ports, pedal polarity
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

### 2026-10-19 project and recent-list cleanup

- With user confirmation, removed `Grid Lab`, `utrp-lab`, `Library-migration` and their automatic backups. The canonical `Library`, its resources and automatic backups remain intact.
- With Bitwig closed, reduced the saved recent-project list from 10 entries to only `~/storage/daw/Library/Library.bwproject`. Unrelated preference bytes and the Library project SHA-256 were verified unchanged; no GUI reopen verification was performed for this cleanup.
- Pre-cleanup prefs are at `~/storage/daw/Backups/library-only-recents-20261019T160620.835576Z/6.1.4.prefs.before`. Restoring this preference backup brings back stale recent entries, not deleted projects. The existing `backup.toml` already covers prefs; no additional path is required.

### 2026-10-19 guitar input recovery and reopen verification

- With no input level, Audio's Selected Device(s) was `GB203 High Definition Audio Controller`, providing no input ports. Spark GO was present in the system, but Bitwig only had playback connections. The failure was device selection, not missing guitar effects.
- Selected `Spark GO USB` through the GUI and restarted the audio engine, restoring `capture_MONO → Bitwig in1`. After normal save, exit and reopen, Audio retained Spark GO and manual 128 samples; capture reconnected automatically, and `AG - 02 Soft Prism` and Master showed signal. No effect parameters or controller code were changed; listening confirmation remains with the user.
- Returned to Soft Prism and saved Library. Recent projects still contain only the canonical Library. Before/after project files, prefs and evidence are in `target/guitar-input-20261019/`; existing recovery paths already cover the changes. If `[missing]` recurs, check Audio's selected device rather than assuming the system's Spark GO default output also supplies input. Physical hot-plug behavior and the earlier switch to HDMI were not established.


### 2026-10-19 persistent input (supersedes direct hardware selection above)

- Single deployed configuration: PipeWire / System Out / manual 128 samples. All four Library AG tracks and raw detection use `Spark-GO-Guitar → capture_MONO`. `Spark-GO-Internal-Capture` is the backend of the same loopback, not a duplicate device. No temporary JACK or null-source rule is deployed.
- Required recovery entry added: `~/.config/systemd/user/utrp-guitar-input.service`. Both routing services are enabled at login; source, TOML and unit recipes live under `lib/tools/audio_routing/`. SF-558 remains the default microphone; missing Spark never falls back to a microphone.
- After normal exit, virtual-source recreation and Bitwig reopen, the saved input reconnected by name: Spark → persistent source → Bitwig, at 128 samples. Piano/guitar selection retained exclusive Arm; controller and MIDI bindings are unchanged. Raw detection remains at −∞.
- Temporarily disabling/restoring the Spark profile retained the virtual-source-to-Bitwig connection, left the backend disconnected while absent and automatically reconnected Spark after return. This is not physical USB unplugging, a system reboot or human listening.
- 66 routing, backup and controller regression tests passed; all 10 Storage directory links are valid; policy dry-run is empty. Screenshots/graphs are under `target/input-autoconnect/`. Physical guitar/keyboard listening still needs user confirmation. No commit/push.

### 2026-10-21 Library two-group audition

- Deployed controller 0.8: known MIDI sounds and the four AG guitar tracks are exclusive within separate groups; cross-group Active / Arm / Monitor states are retained. Select one track in each group initially. No track creation, patch changes or production project-file edits; editors still follow the latest selection.
- The existing `Bitwig Studio` recovery entry covers these controllers. Previous files: `~/storage/daw/Backups/library-two-groups-20261021T163556.713740Z/`. All 10 live Storage directory links remain valid; preserve this layout during recovery.
- 40 related tests passed and deployment matches source byte-for-byte. No accessible Bitwig/Sway session was found; host reload, simultaneous live audio and save/reopen acceptance remain pending. After recovery, select one MIDI sound and one AG guitar track in Library and confirm both remain Active / Arm / Monitor ON; ordinary projects must remain unaffected.
- No commit/push. Run `snapshot.py` at closeout to retain deployment and uncommitted source. A snapshot covers on-disk state only and is not live host acceptance.

### 2026-10-21 Spark GO capture runtime recovery

- Recovered a continuously increasing capture-error state; see [routing investigation](../audio_routing/README.md). No new configuration or recovery paths. Original Spark duplex profile, mic links and routing maintenance were restored. Do not turn the temporary clock-isolation experiment into a permanent Beat Lab microphone disconnection.
- Library was not saved; patches, gains and controller were unchanged. Snapshot protects on-disk contents, not unsaved project state. No commit/push; listening and restart stability remain unverified.

### 2026-10-21 Monitor-only guitar audition (controller 0.9)

- Deployed and live-verified: selecting AG does not arm recording; Monitor ON remains, MIDI behavior unchanged. Beat Lab track arm and internal recording were confirmed off in the UI. User reports strong noise resolved; no diagnostic audio captured.
- Existing `Bitwig Studio` recovery entry covers the controller. Previous controller 0.8 and on-disk project: `~/storage/daw/Backups/library-monitor-only-20261021T165825.279088Z/`. 40 related tests passed. Save current Library and run Recovery snapshot at closeout; no commit/push.

## 2026-10-21: Chord Lab twenty-fret deployment

- Installed Chord Lab 0.2.13 into the existing Storage-backed `.clap` directory, preserving its symlink. Both boards show 20 frets; complete hand regions reach anchor 18, sharing upper-octave candidates with navigation and v3 state validation.
- With user approval, saved and gracefully restarted Bitwig. Library's selected sound and key were retained. Chord Lab was restored to 920×703 and reopened at that size; global layout policy is unchanged.
- Old plugin/project backup: `~/storage/daw/Backups/chordlab-twenty-frets-20261021T170800.635371Z/`. Evidence: `target/chordlab-twenty-frets/`; 569 Chord Lab Python tests, 396 related regressions, nine CTests, built and installed CLAP probes all passed. All ten live Storage links are valid.
- Source remains uncommitted/unpushed; the recovery snapshot includes current working source and the installed plugin. The previous maximum-sized window alone does not establish its trigger.

## 2026-10-21: disable auto-arm in both groups

- Library controller 0.10 uses Monitor ON / Arm OFF in both groups. Host Recording Instrument tracks Auto-arm is off; Audio tracks was already off. The global selection preference changes, but the controller still leaves ordinary recording-project states untouched.
- Previous controller/preferences/project: `~/storage/daw/Backups/library-no-auto-arm-20261021T171311.609945Z/`. Forty regressions passed; live MIDI/guitar switching evidence: `target/library-no-auto-arm/`.
- Deployed into the existing Storage-backed controller directory. Source is uncommitted/unpushed; the snapshot captures working source, saved preferences and project.

## 2026-10-21: output fallback responsiveness

Preserved Spark GO → Woo Audio (EQ) → other physical outputs. `audio_routing/policy.toml` now polls every 0.25 seconds; policy service reloaded and enabled/active. All 39 audio-routing tests passed. Live links were identical across service reload and dry-run was a no-op. Removing Spark from an in-memory graph selects Woo EQ; no physical unplug/click-free listening acceptance was performed this round. Evidence: `target/audio-fallback-20261021/`. Source remains uncommitted/unpushed; recovery snapshot preserves the current source/configuration.

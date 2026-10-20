# Portal

[中文](README.cn.md)

Standalone Rust crate inside UTRP, independent of the parent application/workspace. The Rust server embeds plain HTML/CSS/JS; Node is not a runtime dependency. The phone is a remote control; CMUS plays through the computer's existing PipeWire/output chain.

## Current scope

Local supports artist → album → track browsing, search, play/pause, previous/next, ±5 seconds, seek and repeat. Previous restarts the track after three seconds. Volume follows the existing CMUS 100% configuration, without a volume control. Stream supports Liked, Playlists, song Search and Recommended, using the pinned ytmusic-api crate from the owner fork and the existing browser.json authentication. Playback uses a separate headless mpv service with private Unix IPC, not the TUI process. Local playback pauses running YTM via MPRIS, without reading Chromium databases. Stream reads the existing YTM auth file only on the server; it is never sent to the phone.

Library metadata comes from artist/album/file directory layout. No music files/tags are modified. Run `portal restart` after adding files. Previous/next use whole-library path order, not filtered results. Natural advancement/repeat-all still follow CMUS's own queue/cursor and may differ from the web list. Default repeat-one does not depend on queue ordering.

## Deploy / restore

Restore GRAL, UTRP and Storage first; complete GRAL audio setup and Tailscale sign-in:

```sh
cd ~/work/gral
bash arch/scripts/15-install-portal.sh
portal start
tailscale serve --bg --https=8443 http://127.0.0.1:8787
```

Enable the computer's Serve/HTTPS through the prompted Tailscale browser link if necessary. Do not enable public Funnel. Find the private phone URL with `tailscale serve status`; connect the phone using the same Tailscale account.

Private machine configuration lives at `~/storage/home/UserData/.config/portal/config.toml` (0700 directory / 0600 file), generated from Tailscale on first deployment and preserved on reruns. Check `public_origin`, `allowed_login`, `cmus_socket` and `music_root` after hostname, user/UID or path changes. Never commit the real account config.

Source, Cargo.lock and service templates belong here; the installer belongs to GRAL; music and private settings belong to Storage. Installed binaries and home service copies are reproducible. Manual startup is the policy: GRAL installation always disables autostart without stopping the running service or music. After each reboot, run lowercase `portal`; daily commands are `portal` and `portal stop`, not enable/disable. A service can be disabled and manually active at the same time. See GRAL `arch/sheet.md` and `arch/portal.md` for the command reference and reboot routine.

`portal` / `portal start` starts the web service. `portal stop` stops the web backend, managed Stream/CMUS services and reused playback together. It stops HTTP first, then both player services, then sends stop to configured CMUS/Stream IPC and pause to an independent YTM TUI. Managed processes exit; separately opened terminals are not forcibly closed. Every step is attempted on failure, errors return nonzero, and repeated stops are safe. `portal restart` remains web-only and preserves music. Closing a browser tab does not invoke this command. Use `portal status` / `portal logs` for diagnostics. Controls start `portal-cmus.service` in a private PTY when needed, with no tmux; an existing CMUS Unix socket is reused.

## Security boundary

The backend binds loopback only. Tailscale Serve provides HTTPS and the backend checks the account identity. Writes require a matching Origin and custom header. No arbitrary shell/CMUS commands or external paths are accepted. Files must remain inside the library. Audio files, Google credentials and absolute file paths are not sent to the browser.

A malicious local process can spoof loopback identity headers: this is not a security boundary against hostile software already on the computer. Restrict tailnet ACLs/account devices; do not bind the backend to `0.0.0.0`.

## Validation

```sh
cd ~/work/utrp/Portal
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

2026-10-19: 9 Rust tests passed; 918 real tracks indexed; 390×844 mobile screenshot checked without horizontal overflow or JS errors; private Serve HTTPS returned 200. Actual phone interaction and hardware listening require user acceptance. A destructive clean reinstall has not been rehearsed; uncommitted/unpushed files are not remote backups.


## Stream operation and limits

Run `ytm -auth` on the computer if the account session expires, then click Refresh. Portal reloads the existing auth file on each browse. The account is verified on a new list; continued Home/playlist pages must match the same auth file. No browser-based cookie upload or second password store is added. The API dependency is pinned to `shusheaan/ytmusic-tui` commit `09114f3076422756811c62889b605429df704813`.

Liked loads 100 playable, unique songs initially, then 100 more when you scroll to the bottom (or tap Load 100 more). The last batch may be smaller. This uses real upstream continuation requests, not full-list downloading followed by truncation. Upstream shelves may have a different size, so unused rows are retained for the next batch. All playlist detail entry points, including Playlists → Liked Music, use the same incremental path. Search and library-playlist listing are limited to the API's returned page. Clicking a track queues at most 500 entries from the displayed list, around the selection. Recommended song/artist/album/playlist cards can be opened. Playlist editing is not implemented; the player heart supports Like/Unlike.

The footer controls the active playback source, independent of the browsing tab. Portal playback actions pause the other Portal source and terminal YTM. Starting playback directly in a separate terminal application is outside this coordination and may overlap. Existing TUI playback state/queue is not mirrored into Portal.

The Stream service has no login secrets in arguments and receives only fixed YouTube watch URLs. It uses mpv/yt-dlp, just like the TUI engine. Private/auth-restricted tracks may require additional resolver support; failures are not bypassed. Stop it explicitly with `systemctl --user stop portal-stream.service`. Its `mpv.conf` is deployed from `ops/` and regenerated during installation, not unique home data. The runtime queue is transient; it is not a saved playlist. Web-server restart leaves the player running; mpv metadata is used when the in-memory queue is unavailable.

Live isolated verification: correct Sakita Naoto account, 14 playlists, 50 recommended items, 20 song search results and a 2178-track playlist; real network audio decoded with `ao=null`, pause → new track resumed, seek and all repeat modes passed. Phone/hardware Stream playback still requires user acceptance.

Final verification: 15 Portal tests, clippy with warnings denied, and the GRAL 137-test suite passed. Live phone-layout browsing confirmed all 2178 Liked entries and no JavaScript errors or horizontal overflow.


## Compact player UI (2026-10-19)

The header contains only compact Local/Stream pills. Track rows use a single title · artist line without icons or durations; secondary text is capped at 25% width and both fields truncate with ellipses. The player uses one title/artist line, the existing seek bar and one control row: previous, −5 seconds, centered play/pause, +5 seconds, next, and the circular 1/A/off repeat icon. Playback semantics are unchanged; all labels/tooltips remain English.

Isolated browser checks cover 320/390/768px viewports, ellipsis/artist width, centered play, six control actions, repeat cycling, last-row visibility and JS errors. Observed: header 45px, player 110px (excluding device safe area), rows 36px. No live playback is triggered by this test:

```sh
# Optional browser-test dependency only; not part of Portal runtime.
npm install --prefix /tmp/portal-ui-check playwright
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/compact-ui.cjs
```

Requires `/usr/bin/chromium`, or set `CHROMIUM_PATH`. Screenshots are saved to `/tmp/portal-compact-{width}.png`. Deploy embedded web changes through GRAL's installer and restart only `portal.service`; CMUS and the Stream engine keep running.


## Incremental Liked (2026-10-19)

A server-side cursor keeps upstream tokens private. Each batch is committed only on success, so retries return the same songs. Refresh starts a new list; restarting Portal, changing the auth file, or opening/refreshing any playlist in another browser invalidates old cursors (click Refresh). The current-playlist memory cache is limited to 10,000 songs. `stream.list_limit` still applies to other API listings, not the fixed 100-song playlist batch. No fork/API dependency changes or new runtime packages are needed.

The browser appends rows without rebuilding the list or moving the scroll position. Errors keep existing rows and offer manual retry; exhausted lists stop fetching. Playback queues remain bounded to 500 already-loaded tracks and do not automatically expand when another page loads.

Checks: 20 Rust tests, clippy with warnings denied, compact UI regression at 320/390/768px, and the dedicated pagination test (100 → 200 → failed request → retry → 250, no eager fetching, stable scroll/DOM, selected-track playback, exhaustion and Refresh/Search). Real read-only requests returned three disjoint 100-song batches in approximately 1.37s / 0.45s / 0.48s on this run; network timing varies.

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/liked-pagination.cjs
```


## Pill UI refinement (2026-10-19)

Player and list titles are white and left-aligned (at most 75% width); artists are gray, flush right and capped at 25%. Both truncate with ellipses, with at least a 12px gap and no dot separator. List secondary labels use semibold weight. Rows/highlights, search fields, view tabs and outlined buttons use full pill ends; the play button is circular. Both Back controls are bare arrows with accessible English labels and visible keyboard-focus outlines. Playback and 100-song Liked pagination are unchanged.

The compact UI test also checks alignment with short names, width limits, text color/weight, gap, pill radius, absence of separators and borderless Back controls at 320/390/768px.


## Stream landing and pure black surfaces (2026-10-19)

First entering Stream opens Recommended, without prefetching Liked. The four compact pill tabs are Recommended / Liked / Playlists / Search, on one non-wrapping row with 4px gaps. Search still waits for explicit submission; Liked still loads 100 songs at a time on demand. Page, header, footer, search fields and navigation surfaces are pure black (#000000), including the browser theme color; selection/focus and warning states remain distinguishable. Browser regression tests verify initial Recommended routing, no eager Liked fetch, single-row tabs without clipped labels at 320/390/768px, and black surfaces.


## Compact Local navigation (2026-10-19)

Local overview, artist and album headers use one line: a 13px semibold title on the left and the track count on the right. Long names truncate rather than wrapping. Artist/album group names are semibold; their counts remain right-aligned. Only the Local overview has a capsule search field, matching track title, album or artist across the library. Entering an artist or album hides search; returning to the overview restores it. The playback button remains a true 36×36px circle (50% radius). No duration scan or playback changes are introduced.

`tests/local-ui.cjs` checks all three levels, long headers, global search by title/album/artist, Back navigation, and circular playback controls at 320/390/768px without real playback.


## Home sections and categorized search (2026-10-19)

Stream opens directly with Recommended / Liked / Playlists / Search; login text, the account name and the redundant service heading are omitted. Account verification is unchanged. Recommended is the default and preserves the real account Home shelf titles and order. Scrolling to the end fetches the next upstream Home batch (or tap Load more), rather than stopping at the initial shelves or downloading the entire Home feed. Supported music shelves include songs, artists, albums and playlists; podcast episodes and unsupported special modules are omitted. Recommendations are account-dependent and can change; this is not a complete reproduction of the official Home UI.

Search submits one browser request; the Rust backend concurrently queries the four filtered category endpoints, avoiding the pinned API parser’s omission of the default-search best-match card. It offers four compact category pills: Songs / Artists / Albums / Playlists. Switching pills does not refetch. Artist details show the API's top songs, albums and similar artists when available; album and playlist cards open their tracks. Back restores cached results/category/scroll; returning to a paginated playlist reloads its first batch. Only the search root shows the search field and category pills. Refresh reloads the current detail page, not the original search. Search currently uses the API's initial results for each category, not exhaustive category pagination.

Home cursors, like Liked cursors, are private server-side state: retries replay completed pages, and refresh/auth changes/server restart invalidate old cursors. Home has a safety limit of 50 batches / 10,000 items. A song appearing in different Home sections is retained in each section. No new runtime packages or upstream fork changes are required. Code lives in UTRP; private auth/config remains in Storage. Files must still be committed and pushed before they count as a Git backup.

Validation: 24 Rust tests and warning-free clippy; four isolated browser suites covering 320/390/768px, Local, Liked pagination, Home continuation, category switching, request failure/retry, nested Back and detail Refresh. Read-only live requests returned 50 initial Home items plus 30 more, stable continuation retries, songs, artists, albums and playlists for a sample query (including the exact artist match; malformed entries without names are omitted), and successful artist/album/playlist drilldown. Counts are observations, not fixed expectations. No live playback control was sent.

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/stream-catalog.cjs
```


## Centered playback icons (2026-10-20)

The 36×36px circular button uses fixed SVG geometry instead of font-dependent Play/Pause characters. The SVG viewport is centered in both axes; Pause bars are symmetric and the Play triangle's filled-area centroid is at the center. Status updates only switch SVG visibility, preserving accessible labels and playback behavior. `tests/play-icon.cjs` checks both states, stable DOM, controls and subpixel center alignment at 320/390/768px with 2×/3× device pixel ratios, and saves full-page/button screenshots under `/tmp/portal-icon-*` and `/tmp/portal-button-*`.

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/play-icon.cjs
```


## Unified selection gray (2026-10-20)

`--selected: #414141` is the single color for selected navigation pills, current-track rows (including their border), the circular play button, played progress and the seek thumb. Unplayed progress stays darker (`#181818`) for distinction; transport glyphs remain light for readability. The native range input retains its 32px interaction area and keyboard/touch semantics, with explicit 14×14px circular thumbs for WebKit/Blink and Firefox. The fill follows playback and drag previews; no custom pointer-event slider is introduced.

`tests/gray-theme.cjs` checks equal computed colors in Local/Stream, thumb CSS geometry, 0/50/75/100% fill, drag preview, committed seeking and keyboard input at 320/390/768px. High-DPI screenshots are saved under `/tmp/portal-gray-*`. Existing icon centering and other UI regression suites remain applicable.


## Seamless black layout (2026-10-20)

Removed the header bottom border and player top border. The sticky header and fixed player retain opaque black backgrounds, so scrolling content remains occluded at their boundaries without separator lines. Pill outlines and playback controls are unchanged. `tests/gray-theme.cjs` checks zero surface borders, no shadows, black backgrounds and sticky/fixed positioning at three viewport widths.


## Shuffle and compact repeat (2026-10-20)

All seven transport SVGs share a 21×21px size and 24×24 viewBox; the centered circular play button retains its 36px background. Shuffle shows no On/Off text: white means enabled, gray (#808080) means disabled. Accessible labels and aria-pressed report the active player's state, not a browser-only preference. A failed command leaves the state unchanged and shows an error.

Local switches CMUS between shuffle=tracks and shuffle=off; manual previous/next uses CMUS's native shuffled order when enabled. Stream uses mpv playlist-shuffle/playlist-unshuffle and its shuffle property; new queues preserve the mode and selected song. This applies to the currently loaded Stream queue, not unfetched songs. Toggling does not restart the current song. Reloading the page or restarting Portal reads the state from the player; restarting the player follows its startup defaults. Repeat is independent: repeat one still repeats the current song, so use repeat all/off for automatic shuffled progression.

Validation: 27 Rust tests and clippy; tests/shuffle.cjs covers both sources at 320/390/768px, white icon geometry, symmetry, state toggles, failures and reloads. Independent silent mpv with temporary WAV files verified selection/pause preservation and restored order; isolated CMUS verified tracks/off commands. Other UI regression suites remain applicable.


## Compact search toolbar (2026-10-20)

Stream Search uses one full-width capsule: an Enter-submitted input and a circular-arrow refresh button; no magnifying-glass submit button. Redundant Search heading and empty-page instructions are hidden; accessible English labels and Enter-to-search remain. The same refresh button moves back beside the page title on other Stream pages and detail views. Stream catalog browser tests cover mobile geometry, centered borderless icons, blank queries, submit/Enter, refresh and nested Back navigation.


## Soft selection glow and white progress (2026-10-20)

Player top padding grows from 6px to 14px: the opaque black clipping boundary moves up 8px without moving the title or controls, and ResizeObserver keeps list bottom padding in sync. Played progress and the circular thumb use --progress-color: #fff; the unplayed track remains dark. Selected navigation pills, current song rows and the play button share a subtle neutral-gray glow with 3px blur, zero spread and 32% opacity, clipped to each row’s 2px half-gap. No separator, panel shadow, text blur or animated effect is added. Gray-theme regression tests cover the 117px player (without safe-area inset), 14px title clearance, scrolling padding, white progress and consistent selection-only glow.

### Sticky Stream controls and account likes

Stream list controls (Back, title and icon-only Refresh) remain below the source tabs while scrolling, including nested playlists/albums/artists; Search keeps its single compact sticky form. Local list headings also stick below the source tabs.

The player shows a heart only for a Stream track, regardless of the selected browsing tab. Filled means liked; outlined means not liked. Ratings are read from YouTube Music on track changes and periodically while visible, using server-side auth. Clicking sets LIKE / INDIFFERENT and verifies upstream state before painting success. Success is silent; unknown or failed requests show an inline error and require a read before another write. Local tracks never send rating requests. Writes invalidate Liked pagination; the open Liked view refreshes, and navigating back to Liked fetches a fresh first page (100 tracks). Other tabs/devices with stale pagination may need Refresh.

`GET /api/stream/like?id=VIDEO_ID` and `POST /api/stream/like` (`{"id":"VIDEO_ID","liked":true}`) use the same private identity/CSRF gate as other APIs. IDs are validated; write requests are explicit/idempotent, bounded and serialized separately from playback. Credentials and upstream response bodies are never sent to the browser. `tests/stream-rating.cjs` checks mobile sticky controls, confirmed likes, Liked refresh, failures, reload and late-response isolation without changing a real account.

### Compact sticky library headings

Local and Stream list headings stick below the source tabs. Stream places the gray loaded count on the title row, immediately before the rightmost Refresh icon; Back stays left. Both use the same 44px heading height, 13px title and 11px count. Long titles truncate instead of wrapping. Counts no longer occupy a separate row; loading, empty and error messages remain distinct. A continuation shows `100+ tracks` rather than claiming a total. Search keeps its single-row form, placing its filtered result count before Refresh once results exist.

### Search-first Local home and grouped Stream tabs

Local home starts directly with the search field: no Local music title or total-count row, including while filtering. Artist/album detail headers retain Back, title, count and sticky behavior. Recommended / Liked / Playlists / Search share one outer capsule, using the same border, padding, spacing and height as the Local / Stream selector. Inner options have no individual outlines; the selected option retains its gray fill and glow.


## Fade and AB range looping (2026-10-20)

Local and Stream now share nine equally sized transport icons: AB, Fade, Previous, −5 seconds, Play/Pause, +5 seconds, Next, Shuffle and Repeat. Player height is unchanged.

- The second icon from the left toggles Fade: white on, gray off. Manual track changes fade out before loading/fading in the next track; natural transitions and single-track repeats also fade. This is sequential fading, not overlapping crossfade or a guarantee of gapless network playback.
- The leftmost circle always stays white: `A` sets the player's current position as A; `B` sets the second point; `AB` indicates an active loop and clears it when tapped. Both markers appear below the timeline. A may follow B: playback loops between the smaller and larger positions. Points must be at least one second apart. CMUS markers/seeks have whole-second precision; Stream uses mpv fractional positions.
- AB temporarily forces Fade on and disables its toggle. Clearing AB restores that source's previous Fade preference. Each fade is capped at one third of a short range.
- Each source owns independent runtime state. Reloading/closing the page or locking the phone does not interrupt the Rust background loop; pausing preserves the range. Changing tracks clears it. Seeking and ±5-second controls preserve both A/B markers. Seeking outside the range suspends looping until playback re-enters it. `portal restart` preserves music but clears effects state and restores player software volume to 100%; a new session starts with Fade off and no AB marks.
- Top-level `fade_seconds = 0.75` in `config.toml` sets the maximum duration of each fade (0.1–5 seconds). Configs without this field default to 0.75 seconds; an explicit existing value is preserved. Run `portal restart` after editing. Only player software gain changes, never PipeWire/system volume; CMUS software volume is explicitly enabled. Normal gain remains 100%. Startup, clean shutdown and `ExecStopPost` attempt to restore 100%, reporting failures.
- Source, defaults, service templates and tests live in UTRP `Portal/`; the GRAL installer rebuilds them. Machine settings live in Storage. Temporary AB marks are not written to music files or uploaded to YouTube.

Validation: Rust unit/IPC/browser-independent worker tests, clippy, and 320/390/768px UI regressions. Run `cargo test --locked real_mpv_null_audio -- --ignored` for isolated real mpv looping/volume checks using a silent temporary WAV and `--ao=null`. A separate temporary CMUS instance (ALSA null, private HOME/socket) accepted 37%/100% software gain and absolute seek. Tests did not switch the user's real playback; audible transition quality still requires listening.


Source tabs, the four Stream tabs and 44px list headings are fixed from first render. Headings have no capsule border and add 6px of vertical padding on each side. Only the list viewport scrolls: no staged sticky movement or glow behind the black top area. Rows have a 4px gap and clip their subtle glow at 2px vertically (the gap midpoint); the viewport clips all content at the header boundary. Local search and Stream search/categories also stay fixed. Pagination and navigation restore each viewport's scrollTop instead of scrolling the document.

Validation (2026-10-20): 46 Rust tests passed; the isolated real-mpv test passed separately; clippy reported no warnings. Ten frontend suites cover fixed headers, pixel-level clipping, short lists, pagination, search, Like and transport ordering. Installed through GRAL and restarted with user approval, clearing temporary AB without changing CMUS/mpv PIDs. Served assets match source. CMUS software channels and mpv volume are 100%; system sink is 1.00. Portal remains active/disabled; unauthenticated requests return 403. Settings live in Storage; source is not committed/pushed and is not yet a remote backup.

Local overview search and the four-tab Stream strip share the same position, width and 32px outer height, with 11px text. Switching sources does not move or resize this capsule; Local search still matches tracks, albums and artists.

## Playlist pagination and matching search bars (2026-10-20)

All playlist detail views, not just the Liked tab, load at most 100 playable unique tracks per batch. Upstream overflow is cached rather than triggering a full download. Cursors bind the account, playlist and generation; opening/refreshing another playlist invalidates the previous cursor. Returning to a playlist fetches its first batch again. Albums, Home shelves and search retain their own API behavior.

Local and Stream Search use the same 32px capsule and 11px input typography as the Stream navigation capsule. Search and category controls stay outside the scrolling track list. Rust tests cover playlist identity, limited upstream fetching, cached overflow and retry safety; browser pagination tests cover Liked, LM, VLLM and ordinary playlists.

Validation: 49 Rust tests passed (one isolated mpv test intentionally skipped), warning-free clippy and all 10 browser suites passed. Live read-only Playlists → Liked returned 100 + 100 non-overlapping tracks (1.19s / 0.40s); another playlist returned 100 with a continuation (0.84s). These timings vary with the network. Deployed via GRAL; served assets match source, player PIDs stayed unchanged, Portal is active with autostart disabled. Source changes still require commit/push for remote backup.

## Enter-only unified search（2026-10-20）

Both search bars are full-width 32px capsules with 11px text and no magnifying-glass/submit button. Local shows `Search`; Stream shows `Search artists, albums, tracks`. Typing does not submit: press Enter (the phone keyboard Search key) to apply the query. Stream retains its Refresh icon and result count inside the capsule on the right. Both bars stay fixed above their scrollable lists. Browser checks compare Local/Stream geometry and fonts and verify that typing alone does not search.

## Mobile input focus zoom（2026-10-20）

Search input text is now 16px in both Local and Stream, while capsules stay 32px high and navigation labels remain 11px. This replaces the previous 11px input size to address mobile focus zoom. No viewport zoom limits or scaled-text workaround are added. Enter-only search and sticky layout are unchanged. Desktop Chromium mobile-layout tests check input size, matching capsule geometry and unrestricted viewport metadata; they cannot prove real iPhone keyboard/zoom behavior.

Search capsules now show only `...` when empty. Stream Search has no Refresh icon or result count inside the field; pressing Enter repeats the search. Playlist/detail Refresh controls remain available. Input text stays 16px, capsules 32px, and accessible search labels remain descriptive.

Outer black spacing: header top padding is 14px + safe-area inset; player bottom padding is 11px + safe-area inset (8px more at each edge). Header/player heights without insets are 52px/125px. Inner controls, row spacing and list-only scrolling are unchanged; ResizeObserver reserves the updated player height.

Empty search fields now use the same 14px decorative magnifying-glass SVG instead of text or dots. The hint hides while focused or non-empty; it never intercepts taps or submits a search. Actual input text remains 16px. Both fields share capsule dimensions, Enter submission and accessible labels; Search has no refresh button.

## Stream reliability across web restarts (2026-10-20)

Loaded songs no longer depend on the temporary browse catalog. Playback validates a stable YouTube video ID and constructs the watch URL on the server; arbitrary URLs, paths and commands remain rejected. The browser sends bounded display labels with the existing queue IDs (maximum 500 songs), so old lists still work after catalog eviction or a Portal web restart. Older ID-only clients remain compatible; reload the webpage once after this upgrade to receive label preservation and automatic continuation recovery.

Queue labels are stored in mpv `user-data/portal-tracks`, replaced with each queue and read one song at a time. They survive a Portal web restart while that player remains running, but are not a permanent listening-history database. Same-song partial status responses no longer erase the displayed artist; changing songs cannot inherit the previous artist. The heart stays right-aligned even without an artist.

Expired continuation cursors (HTTP 409) are rebuilt automatically by replaying only the prefix needed to reach new items, without removing existing rows or changing scroll position. Initial playlist loads still fetch 100 songs; no background full-library download is added. Recovery is bounded, deduplicates rows and never automatically retries playback/rating POSTs. Real network/auth failures retain the visible list and expose a retry rather than an endless retry loop. Refresh remains optional for deliberately obtaining a new list/order. This supersedes earlier notes requiring manual Refresh after cache expiration.

This is not a promise that YouTube media URLs or login sessions never expire: playback uses the stable watch ID and mpv/yt-dlp resolves the media URL when loading. Removed/restricted videos, expired account authorization and upstream/network failures can still prevent playback. `ytm -auth` is needed only for actual account authentication failure, not Portal catalog eviction.

Source and regression tests live in UTRP `Portal/`; GRAL `arch/scripts/15-install-portal.sh` rebuilds/installs the embedded frontend and Rust backend. Existing configuration stays in Storage. After deployment, restart only `portal.service` to retain player processes (temporary Fade/AB state still resets). No new public listener, Funnel access, cookies in browser, or autostart is introduced. Changes require commit/push in both repositories to become a remote backup.

Validation: 51 Rust tests passed, two isolated real-mpv tests passed separately, clippy passed with warnings denied, all 11 browser suites passed, and the three GRAL policy tests passed. Deployed through the GRAL installer; live embedded assets match source. Only the web service was restarted: CMUS/mpv PIDs and paused state stayed unchanged, and the current Stream artist survived. Autostart remains disabled and anonymous HTTP requests return 403. No long-duration live playback soak test was performed; expiry/restart scenarios were reproduced deterministically with isolated players and mocked browser APIs.

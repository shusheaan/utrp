# Horizontal fretboard matrices: tool research and reproduction

[中文](fretboard-tools.cn.md) · 2026-10-01

## Decision

Use a small deterministic Python renderer for source-grounded Drown phrase maps embedded in Markdown, not a new general music-theory engine. Existing tools remain useful if the scope grows. This comparison is based on official documentation, **not installed-library benchmarks or side-by-side rendering tests**.

| Tool | Documented capabilities | Fit for this project |
|---|---|---|
| [FretBoardGtr](https://fretboardgtr.readthedocs.io/en/stable/get-started/get-started.html) | Python scales, SVG, horizontal/vertical orientation, fret ranges, colors and note/degree configuration | First candidate to evaluate for broader Python scale features |
| [python-fretboard](https://github.com/dmpayton/python-fretboard) | Python SVG fretboards/chord charts with marker labels and colors | Custom positions; phrase paths and explanatory layout need composition |
| [fretboard.js](https://github.com/moonwave99/fretboard.js) | Browser fretboards with scale and CAGED/TNPS tools | Candidate for future interactive practice, unnecessary frontend scope today |
| [SVGuitar](https://github.com/omnibrain/svguitar) | SVG chord charts with orientation, fingering and color options | Good for chord grips; not the first choice for cross-position melodic routes |

## Visual grammar

Separate full scale maps, sparse landmarks with muted context, and phrase-specific routes. One concept per image. High e is on top, low E at the bottom, frets increase rightward. Relative to the explicitly named reference: red = 1, gold = third, blue = fifth, teal = other selected notes, gray = context. Markers also carry pitch names and degrees, so meaning does not rely only on color.

A reference is not necessarily a verified backing root. Arrows encode direction, not duration; parallel double-stop paths move together. Limit each image to 14 fret columns, state the conclusion in its title, and explain evidence limits beneath it.

Five diagrams are embedded in the [Drown analysis](NLND_TABS/drown-mateus-skeleton.md): E minor scale, Em landmarks, measure 106 fourths, measure 117 octaves and measure 119 arpeggio.

## Reproduction

Run from the project root with Python 3.11+. SVG generation uses only the standard library:

```sh
python scripts/render_fretboard.py sheets/NLND_TABS/drown-matrices.toml \
  --output sheets/NLND_TABS --force
```

Omit `--force` for new output; existing output is otherwise protected. See the [configuration](NLND_TABS/drown-matrices.toml) and [script](../scripts/render_fretboard.py).

Markdown embeds PNG for preview compatibility; SVG remains available for scaling. PNG conversion requires `rsvg-convert` from librsvg and CJK fonts, already present on this machine:

```sh
for f in sheets/NLND_TABS/drown-*.svg; do
  rsvg-convert "$f" -o "${f%.svg}.png"
done
```

Regenerate both formats after configuration changes and visually inspect them. The configured font is `Noto Sans CJK SC`; verify font availability on other machines. Fonts are not embedded.

## Configuration boundaries

- `strings` and `tuning` share display order; tuning contains six open-string MIDI pitches.
- `tonic` is a reference pitch class from 0 to 11 (C=0, E=4, A=9).
- `context` defines background pitch classes. `auto_scale=true` enumerates every matching position and is mutually exclusive with explicit `anchors`.
- `anchors=["G12", "B12", "e12"]` selects highlighted positions. Each `paths` entry orders selected anchors into a route.
- `first`/`last` set the range, `slug` names output, and title/subtitle/footer supply explanatory copy.
- `pitch_names` and `degrees` are explicit 12-label tables. Pitch-class calculations do not infer key, harmonic function or theoretically correct enharmonic spelling.
- `theme` controls colors and font. Layout is a fixed six-string horizontal matrix, not TAB, rhythm engraving or automatic harmonic analysis. Long text needs preview checks; automatic wrapping is not implemented.

## Validation

```sh
python -m pytest -q tests/test_render_fretboard.py
```

Development dependencies: `pytest` and `hypothesis`. Tests cover octave invariance, complete scale enumeration, score landmarks, fourths, SVG XML, adjacent-string arrows, invalid configuration and overwrite protection. Manual image review supplements tests; neither replaces score verification nor proves backing harmony.

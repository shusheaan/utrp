"""Render validated TOML phrase maps as dependency-free SVG fretboard matrices."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from math import hypot
from pathlib import Path
import re
import tomllib
from typing import cast


@dataclass(frozen=True)
class Position:
    string: int
    fret: int


@dataclass(frozen=True)
class Diagram:
    slug: str
    title: str
    subtitle: str
    footer: str
    first: int
    last: int
    tonic: int
    context: tuple[int, ...]
    anchors: tuple[Position, ...]
    paths: tuple[tuple[Position, ...], ...]


@dataclass(frozen=True)
class Theme:
    paper: str
    ink: str
    muted: str
    grid: str
    context: str
    anchor: str
    root: str
    third: str
    fifth: str
    route: str
    font: str


@dataclass(frozen=True)
class Settings:
    tuning: tuple[int, ...]
    strings: tuple[str, ...]
    pitch_names: tuple[str, ...]
    degrees: tuple[str, ...]
    theme: Theme
    diagrams: tuple[Diagram, ...]


def table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Expected a TOML table")
    return cast(dict[str, object], value)


def array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("Expected a TOML array")
    return cast(list[object], value)


def string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonempty string")
    return value


def integer(value: object, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"Expected integer in [{lower}, {upper}], got {value!r}")
    return value


def position(value: object, labels: tuple[str, ...]) -> Position:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", string(value))
    if match is None or match[1] not in labels:
        raise ValueError(f"Unknown string/fret: {value!r}")
    return Position(labels.index(match[1]), integer(int(match[2]), 0, 36))


def scale_positions(tuning: tuple[int, ...], pitch_classes: tuple[int, ...],
                    first: int, last: int) -> tuple[Position, ...]:
    return tuple(Position(row, fret) for row in range(len(tuning))
                 for fret in range(first, last + 1)
                 if (tuning[row] + fret) % 12 in pitch_classes)


def parse_diagram(value: object, labels: tuple[str, ...], tuning: tuple[int, ...]) -> Diagram:
    raw = table(value)
    slug = string(raw["slug"])
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("slug must be a safe lowercase hyphenated filename")
    first, last = (integer(raw[key], 0, 36) for key in ("first", "last"))
    if not 2 <= last - first + 1 <= 14:
        raise ValueError("Show 2–14 fret columns per diagram for readable labels")
    context = tuple(integer(p, 0, 11) for p in array(raw["context"]))
    auto_scale = raw.get("auto_scale", False)
    if type(auto_scale) is not bool:
        raise ValueError("auto_scale must be a boolean")
    anchors = (scale_positions(tuning, context, first, last) if auto_scale else
               tuple(position(item, labels) for item in array(raw["anchors"])))
    if auto_scale and "anchors" in raw:
        raise ValueError("Use either auto_scale or explicit anchors, not both")
    paths = tuple(tuple(position(p, labels) for p in array(path))
                  for path in array(raw.get("paths", [])))
    if not anchors or len(set(anchors)) != len(anchors):
        raise ValueError("anchors must be nonempty and unique")
    if any(not first <= p.fret <= last for p in anchors):
        raise ValueError("An anchor is outside the displayed fret range")
    if any(len(path) < 2 or any(p not in anchors for p in path) for path in paths):
        raise ValueError("Each path needs at least two positions, all in anchors")
    if any(a == b for path in paths for a, b in zip(path, path[1:])):
        raise ValueError("A route cannot connect a position to itself")
    return Diagram(slug, string(raw["title"]), string(raw["subtitle"]),
                   string(raw["footer"]), first, last, integer(raw["tonic"], 0, 11),
                   context, anchors, paths)


def parse_settings(raw: dict[str, object]) -> Settings:
    labels = tuple(string(v) for v in array(raw["strings"]))
    tuning = tuple(integer(v, 0, 127) for v in array(raw["tuning"]))
    if len(labels) != 6 or len(set(labels)) != 6 or len(tuning) != 6:
        raise ValueError("Provide six unique string labels and six MIDI open pitches")
    if any(not re.fullmatch(r"[A-Za-z]+", label) for label in labels):
        raise ValueError("String labels must contain letters only")
    names = tuple(string(v) for v in array(raw["pitch_names"]))
    degrees = tuple(string(v) for v in array(raw["degrees"]))
    if len(names) != 12 or len(degrees) != 12:
        raise ValueError("pitch_names and degrees must each contain 12 labels")
    theme_raw = table(raw["theme"])
    colors = tuple(string(theme_raw[key]) for key in
                   ("paper", "ink", "muted", "grid", "context", "anchor", "root", "third", "fifth", "route"))
    if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in colors):
        raise ValueError("Theme colors must use #RRGGBB")
    diagrams = tuple(parse_diagram(v, labels, tuning) for v in array(raw["diagrams"]))
    if not diagrams or len({d.slug for d in diagrams}) != len(diagrams):
        raise ValueError("Provide at least one diagram with unique slugs")
    return Settings(tuning, labels, names, degrees,
                    Theme(*colors, string(theme_raw["font"])), diagrams)


def pitch_class(position: Position, tuning: tuple[int, ...]) -> int:
    return (tuning[position.string] + position.fret) % 12


def coordinates(position: Position, diagram: Diagram) -> tuple[float, float]:
    column = 1220 / (diagram.last - diagram.first + 1)
    return 140 + (position.fret - diagram.first + 0.5) * column, 205 + position.string * 49


def label(x: float, y: float, content: str, size: int, color: str,
          align: str = "start", weight: int = 400) -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" '
            f'text-anchor="{align}" font-weight="{weight}">{escape(content)}</text>')


def grid_svg(diagram: Diagram, settings: Settings) -> list[str]:
    theme = settings.theme
    parts: list[str] = []
    column = 1220 / (diagram.last - diagram.first + 1)
    for fret in range(diagram.first, diagram.last + 1):
        x, _ = coordinates(Position(0, fret), diagram)
        if fret in (0, 12, 24, 36):
            parts.append(f'<rect x="{x-column/2:.2f}" y="180" width="{column:.2f}" '
                         f'height="295" rx="8" fill="{theme.grid}" opacity="0.24"/>')
        parts.append(label(x, 164, str(fret), 17, theme.muted, "middle", 600))
        if fret in (3, 5, 7, 9, 15, 17, 19, 21, 27, 29, 31, 33):
            parts.append(f'<circle cx="{x:.2f}" cy="494" r="3" fill="{theme.muted}"/>')
        elif fret in (12, 24, 36):
            for offset in (-5, 5):
                parts.append(f'<circle cx="{x+offset:.2f}" cy="494" r="3" fill="{theme.muted}"/>')
    for i, name in enumerate(settings.strings):
        y = 205 + i * 49
        parts.append(label(108, y + 6, name, 18, theme.ink, "middle", 600))
        parts.append(f'<path d="M140 {y} H1360" stroke="{theme.grid}" stroke-width="{1+i*.23}"/>')
    for i in range(diagram.last - diagram.first + 2):
        x = 140 + i * column
        parts.append(f'<path d="M{x:.2f} 180 V475" stroke="{theme.grid}" stroke-width="1"/>')
    for row in range(6):
        for fret in range(diagram.first, diagram.last + 1):
            p = Position(row, fret)
            if p not in diagram.anchors and pitch_class(p, settings.tuning) in diagram.context:
                x, y = coordinates(p, diagram)
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{theme.context}"/>')
    return parts


def routes_svg(diagram: Diagram, theme: Theme) -> list[str]:
    parts: list[str] = []
    for path in diagram.paths:
        for start, end in zip(path, path[1:]):
            x1, y1 = coordinates(start, diagram)
            x2, y2 = coordinates(end, diagram)
            distance = hypot(x2-x1, y2-y1)
            if distance < 60:
                parts.append(f'<path d="M{x1+23:.2f} {y1:.2f} '
                             f'Q{x1+65:.2f} {(y1+y2)/2:.2f} {x2+26:.2f} {y2:.2f}" '
                             f'fill="none" stroke="{theme.route}" stroke-width="2.4" '
                             'marker-end="url(#arrow)"/>')
                continue
            dx, dy = (x2-x1)/distance, (y2-y1)/distance
            parts.append(f'<path d="M{x1+26*dx:.2f} {y1+26*dy:.2f} '
                         f'L{x2-29*dx:.2f} {y2-29*dy:.2f}" fill="none" '
                         f'stroke="{theme.route}" stroke-width="2.4" marker-end="url(#arrow)"/>')
    return parts


def render_svg(diagram: Diagram, settings: Settings) -> str:
    theme = settings.theme
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="620" '
             f'viewBox="0 0 1440 620" role="img" aria-labelledby="title desc">',
             f'<title id="title">{escape(diagram.title)}</title>',
             f'<desc id="desc">{escape(diagram.subtitle + ". " + diagram.footer)}</desc>',
             f'<rect width="1440" height="620" rx="22" fill="{theme.paper}"/>',
             f'<g font-family="{escape(theme.font, quote=True)}">',
             '<defs><marker id="arrow" markerWidth="7" markerHeight="7" '
             'refX="6" refY="3.5" orient="auto" markerUnits="userSpaceOnUse">',
             f'<path d="M0 0 L7 3.5 L0 7 Z" fill="{theme.route}"/></marker></defs>',
             label(56, 42, "UTRP  /  PHRASE ATLAS", 12, theme.muted, weight=600),
             label(1384, 42, "音名 / 参照级数 · 箭头只表示走向", 12, theme.muted, "end"),
             label(56, 86, diagram.title, 30, theme.ink, weight=700),
             label(56, 119, diagram.subtitle, 16, theme.muted)]
    parts.extend(grid_svg(diagram, settings))
    parts.extend(routes_svg(diagram, theme))
    for p in diagram.anchors:
        pc = pitch_class(p, settings.tuning)
        x, y = coordinates(p, diagram)
        interval = (pc-diagram.tonic) % 12
        color = (theme.root if interval == 0 else theme.third if interval in (3, 4)
                 else theme.fifth if interval == 7 else theme.anchor)
        degree = settings.degrees[interval]
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="23" fill="{color}" '
                     f'stroke="{theme.paper}" stroke-width="2"/>')
        parts.append(label(x, y-1, settings.pitch_names[pc], 17, theme.paper, "middle", 700))
        parts.append(label(x, y+14, degree, 11, theme.paper, "middle", 500))
    for x, color, text in ((62, theme.root, "1 · 参照主音"),
                            (300, theme.third, "b3 / 3 · 三度"),
                            (540, theme.fifth, "5 · 五度"),
                            (790, theme.anchor, "其他选中音"),
                            (1080, theme.context, "背景位置 · 非指令")):
        parts.append(f'<circle cx="{x}" cy="541" r="6" fill="{color}"/>')
        parts.append(label(x+15, 546, text, 14, theme.muted))
    parts.append(label(56, 586, diagram.footer, 16, theme.ink))
    parts.append('</g></svg>')
    return '\n'.join(parts) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="Replace existing generated SVGs")
    args = parser.parse_args()
    try:
        with args.config.open("rb") as stream:
            settings = parse_settings(tomllib.load(stream))
        destinations = tuple(args.output / f"{d.slug}.svg" for d in settings.diagrams)
        if not args.force and any(p.exists() for p in destinations):
            raise FileExistsError("Output exists; use --force to regenerate")
        args.output.mkdir(parents=True, exist_ok=True)
        for diagram, path in zip(settings.diagrams, destinations):
            path.write_text(render_svg(diagram, settings), encoding="utf-8")
            print(path)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()

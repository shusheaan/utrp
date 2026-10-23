"""Float Bitwig editors around a centered Chord Lab and primary editor."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
import tomllib
from typing import TypeAlias, cast

Json: TypeAlias = 'None | bool | int | float | str | list[Json] | dict[str, Json]'


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def parse(cls, value: Json) -> Rect:
        data = mapping(value)
        fields = tuple(data.get(k) for k in ('x', 'y', 'width', 'height'))
        if not all(type(v) is int for v in fields):
            raise ValueError('Invalid Sway rectangle')
        x, y, width, height = (int(str(v)) for v in fields)
        if width < 0 or height < 0:
            raise ValueError('Negative Sway size')
        return cls(x, y, width, height)


@dataclass(frozen=True)
class Config:
    left_reserved: int
    right_margin: int
    top_margin: int
    bottom_margin: int
    gap: int
    poll_seconds: float
    surge_effects_width: int
    surge_effects_height: int

    @classmethod
    def read(cls, path: Path) -> Config:
        data = tomllib.loads(path.read_text())['layout']
        for key in ('left_reserved', 'right_margin', 'top_margin', 'bottom_margin', 'gap'):
            if type(data[key]) is not int or data[key] < 0:
                raise ValueError(f'Invalid {key}')
        for key in ('surge_effects_width', 'surge_effects_height'):
            if type(data[key]) is not int or data[key] <= 0:
                raise ValueError(f'Invalid {key}')
        if not isinstance(data['poll_seconds'], (int, float)) or not 0.1 <= data['poll_seconds'] <= 10:
            raise ValueError('Invalid polling interval')
        return cls(**data)


@dataclass(frozen=True)
class Window:
    id: int
    title: str
    rect: Rect
    workspace: int
    bounds: Rect
    floating: bool
    fullscreen: bool
    layout_revision: tuple[str, ...] = ()


def mapping(value: Json) -> dict[str, Json]:
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    return value


def children(node: dict[str, Json]) -> tuple[dict[str, Json], ...]:
    result: list[dict[str, Json]] = []
    for key in ('nodes', 'floating_nodes'):
        values = node.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f'Invalid Sway {key}')
        result.extend(mapping(v) for v in values)
    return tuple(result)


def flatten(node: dict[str, Json]) -> tuple[dict[str, Json], ...]:
    return (node,) + tuple(item for child in children(node) for item in flatten(child))


def plugin_windows(tree: dict[str, Json], host_pids: frozenset[int]) -> tuple[Window, ...]:
    all_nodes = flatten(tree)
    parents = {
        n['window'] for n in all_nodes
        if mapping(n.get('window_properties') or {}).get('class') == 'com.bitwig.BitwigStudio'
        and n.get('window') is not None
    }
    result: list[Window] = []
    for workspace in all_nodes:
        if workspace.get('type') != 'workspace' or workspace.get('name') == '__i3_scratch':
            continue
        bounds = Rect.parse(workspace['rect'])
        for node in flatten(workspace):
            props = mapping(node.get('window_properties') or {})
            title = str(node.get('name') or '')
            if (node.get('pid') not in host_pids
                    or props.get('transient_for') not in parents or ' / ' not in title):
                continue
            result.append(Window(int(str(node['id'])), title, Rect.parse(node['rect']),
                                 int(str(workspace['id'])), bounds,
                                 node.get('floating') in ('user_on', 'auto_on'),
                                 bool(node.get('fullscreen_mode')), layout_revision(node)))
    return tuple(result)


def layout_revision(node: dict[str, Json]) -> tuple[str, ...]:
    """Persistent resize notification: even a full G cycle between polls is seen."""
    marks = node.get('marks', [])
    if not isinstance(marks, list):
        raise ValueError('Invalid Sway marks')
    prefix = 'utrp-chordlab-layout-'
    return tuple(sorted(mark for mark in marks if isinstance(mark, str)
                        and mark.startswith(prefix) and mark[len(prefix):].isascii()
                        and mark[len(prefix):].isdigit()))


def available(bounds: Rect, config: Config) -> Rect:
    return Rect(bounds.x + config.left_reserved, bounds.y + config.top_margin,
                max(0, bounds.width - config.left_reserved - config.right_margin),
                max(0, bounds.height - config.top_margin - config.bottom_margin))


def overlaps(a: Rect, b: Rect, gap: int = 0) -> bool:
    return (a.x < b.x + b.width + gap and b.x < a.x + a.width + gap
            and a.y < b.y + b.height + gap and b.y < a.y + a.height + gap)


def find_space(area: Rect, width: int, height: int,
               occupied: tuple[Rect, ...], gap: int) -> Rect | None:
    xs = {area.x + area.width - width} | {r.x - gap - width for r in occupied}
    ys = {area.y} | {r.y + r.height + gap for r in occupied}
    for y in sorted(ys):
        for x in sorted(xs, reverse=True):
            candidate = Rect(x, y, width, height)
            if (x < area.x or y + height > area.y + area.height
                    or x + width > area.x + area.width):
                continue
            if not any(overlaps(candidate, r, gap) for r in occupied):
                return candidate
    return None


def compact_arrangement(windows: tuple[Window, ...], config: Config) -> tuple[tuple[int, Rect | None], ...]:
    occupied: dict[int, tuple[Rect, ...]] = {}
    result: list[tuple[int, Rect | None]] = []
    # Keep Chord Lab anchored; pack tall editors first so small FX do not fragment
    # space needed by a later synth. Creation order only breaks equal-size ties.
    ordered = sorted(windows, key=lambda w: (not w.title.endswith(' / Chord Lab'),
                                             -w.rect.height, -w.rect.width, w.id))
    for window in ordered:
        used = occupied.get(window.workspace, ())
        rect = find_space(available(window.bounds, config), window.rect.width,
                          window.rect.height, used, config.gap)
        result.append((window.id, rect))
        if rect is not None:
            occupied[window.workspace] = used + (rect,)
    return tuple(result)


def centered_origin(bounds: Rect, area: Rect, width: int, height: int) -> tuple[int, int]:
    x = bounds.x + (bounds.width - width) // 2
    y = bounds.y + (bounds.height - height) // 2
    return (max(area.x, min(x, area.x + area.width - width)),
            max(area.y, min(y, area.y + area.height - height)))


def core_windows(windows: tuple[Window, ...]) -> tuple[Window, ...]:
    chords = sorted((w for w in windows if w.title.endswith(' / Chord Lab')),
                    key=lambda w: (not w.title.startswith('CHORD LAB - shared MIDI input / '), w.id))
    others = sorted((w for w in windows if not w.title.endswith(' / Chord Lab')),
                    key=lambda w: (not w.title.endswith((' / Surge XT', ' / sfizz')), w.id))
    if chords:
        return (chords[0],) + tuple(others[:1])
    return tuple(others[:1])


def surrounding_space(area: Rect, core: Rect, width: int, height: int,
                      occupied: tuple[Rect, ...], gap: int) -> Rect | None:
    cx, cy = core.x + core.width // 2, core.y + core.height // 2
    xs = {area.x, area.x + area.width - width, cx - width // 2}
    ys = {area.y, area.y + area.height - height, cy - height // 2}
    for r in occupied:
        xs.update((r.x - gap - width, r.x + r.width + gap, r.x, r.x + r.width - width))
        ys.update((r.y - gap - height, r.y + r.height + gap, r.y, r.y + r.height - height))
    candidates = tuple(Rect(x, y, width, height) for x in xs for y in ys
                       if area.x <= x <= area.x + area.width - width
                       and area.y <= y <= area.y + area.height - height)
    valid = tuple(r for r in candidates if not any(overlaps(r, other, gap) for other in occupied))
    return min(valid, default=None, key=lambda r: (
        0 if r.x >= core.x + core.width + gap else 1,
        abs(r.x + width // 2 - cx) + abs(r.y + height // 2 - cy), -r.x, r.y))


def centered_arrangement(windows: tuple[Window, ...], config: Config) -> tuple[tuple[int, Rect | None], ...]:
    core = core_windows(windows)
    bounds = windows[0].bounds
    area = available(bounds, config)
    width = sum(w.rect.width for w in core) + config.gap * (len(core) - 1)
    height = max(w.rect.height for w in core)
    if width > area.width or height > area.height:
        return tuple((w.id, None) for w in windows)
    x, y = centered_origin(bounds, area, width, height)
    group = Rect(x, y, width, height)
    result: list[tuple[int, Rect | None]] = []
    occupied: tuple[Rect, ...] = ()
    for w in core:
        r = Rect(x, y + (height - w.rect.height) // 2, w.rect.width, w.rect.height)
        result.append((w.id, r))
        occupied += (r,)
        x += r.width + config.gap
    extras = sorted((w for w in windows if w not in core),
                    key=lambda w: (-w.rect.height, -w.rect.width, w.id))
    for w in extras:
        candidate = surrounding_space(area, group, w.rect.width, w.rect.height, occupied, config.gap)
        result.append((w.id, candidate))
        if candidate is not None:
            occupied += (candidate,)
    return tuple(result)


def center_compact(windows: tuple[Window, ...], config: Config) -> tuple[tuple[int, Rect | None], ...]:
    packed = compact_arrangement(windows, config)
    rects = tuple(r for _, r in packed if r is not None)
    if not rects:
        return packed
    left, top = min(r.x for r in rects), min(r.y for r in rects)
    width = max(r.x + r.width for r in rects) - left
    height = max(r.y + r.height for r in rects) - top
    x, y = centered_origin(windows[0].bounds, available(windows[0].bounds, config), width, height)
    return tuple((i, None if r is None else Rect(r.x + x - left, r.y + y - top, r.width, r.height))
                 for i, r in packed)


def arrange(windows: tuple[Window, ...], config: Config) -> tuple[tuple[int, Rect | None], ...]:
    result: list[tuple[int, Rect | None]] = []
    for workspace in sorted({w.workspace for w in windows}):
        group = tuple(w for w in windows if w.workspace == workspace)
        placed = centered_arrangement(group, config)
        if any(r is None for _, r in placed):
            # If an immovable center wastes vertical space, center the whole compact group.
            compact = center_compact(group, config)
            if sum(r is not None for _, r in compact) > sum(r is not None for _, r in placed):
                placed = compact
        result.extend(placed)
    return tuple(result)


def sway(arguments: tuple[str, ...]) -> Json:
    completed = subprocess.run(('swaymsg', '-r', *arguments), check=True,
                               capture_output=True, text=True, timeout=5)
    return cast(Json, json.loads(completed.stdout))


def command(value: str) -> None:
    replies = sway((value,))
    if not isinstance(replies, list) or not replies or any(
            mapping(reply).get('success') is not True for reply in replies):
        raise RuntimeError(f'Sway rejected {value}: {replies}')


def read_windows() -> tuple[Window, ...]:
    tree = mapping(sway(('-t', 'get_tree')))
    pids = {n['pid'] for n in flatten(tree) if type(n.get('pid')) is int}
    hosts: set[int] = set()
    for pid in pids:
        try:
            executable = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[0]
        except (FileNotFoundError, ProcessLookupError):
            continue  # A window/process can close between the tree and /proc snapshots.
        if Path(executable.decode()).name.startswith('BitwigPluginHost-'):
            hosts.add(int(str(pid)))
    return plugin_windows(tree, frozenset(hosts))


def signature(windows: tuple[Window, ...]) -> tuple[tuple[object, ...], ...]:
    # Ignore position/focus: manual dragging and clicking do not trigger a layout fight.
    return tuple((w.id, w.title, w.rect.width, w.rect.height, w.workspace, w.bounds,
                  w.floating, w.fullscreen, w.layout_revision)
                 for w in sorted(windows, key=lambda w: w.id))


def apply_layout(windows: tuple[Window, ...], config: Config) -> None:
    by_id = {w.id: w for w in windows}
    overflow: list[str] = []
    for window_id, rect in arrange(windows, config):
        window = by_id[window_id]
        if rect is None:
            overflow.append(window.title)
            continue  # Never resize, hide or close an editor to pretend it fits.
        if (window.rect.x, window.rect.y) != (rect.x, rect.y):
            command(f'[con_id={window_id}] move absolute position {rect.x} px {rect.y} px')
    if overflow:
        message = 'Not enough room. Close an unused editor: ' + ', '.join(overflow)
        print(message, flush=True)
        subprocess.run(('notify-send', '-a', 'UTRP Plugin Windows', '-r', '9217',
                        'Plugin layout is full', message), check=True, timeout=5)


def needs_effect_size_reset(window: Window, is_new: bool, config: Config) -> bool:
    if not window.title.endswith(' / Surge XT Effects'):
        return False
    wanted = (config.surge_effects_width, config.surge_effects_height)
    actual = (window.rect.width, window.rect.height)
    area = available(window.bounds, config)
    oversized = window.rect.width > area.width or window.rect.height > area.height
    return actual != wanted and (is_new or oversized or not window.floating)


def library_focus_target(tree: dict[str, Json], new_ids: frozenset[int]) -> int | None:
    """One-shot activation of a new Library keyboard, never a global focus lock."""
    nodes = flatten(tree)
    parents = {n.get('window') for n in nodes
               if n.get('window') is not None
               and n.get('name') in ('Bitwig Studio - Library', 'Bitwig Studio - Library-migration')
               and mapping(n.get('window_properties') or {}).get('class') == 'com.bitwig.BitwigStudio'}
    focused = next((n for n in nodes if n.get('focused') is True), None)
    if focused is None:
        return None
    focused_props = mapping(focused.get('window_properties') or {})
    # Do not pull focus away if the user moved to another application/project.
    if focused.get('window') not in parents and focused_props.get('transient_for') not in parents:
        return None
    for node in nodes:
        if (node.get('id') in new_ids and node.get('focused') is not True
                and node.get('name') == 'CHORD LAB - shared MIDI input / Chord Lab'
                and mapping(node.get('window_properties') or {}).get('transient_for') in parents):
            return int(str(node['id']))
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    config = Config.read(Path(__file__).with_name('layout.toml'))
    previous: tuple[tuple[object, ...], ...] | None = None
    seen: frozenset[int] = frozenset()
    while True:
        windows = read_windows()
        converted = False
        for window in windows:
            if not window.floating or window.fullscreen:
                command(f'[con_id={window.id}] fullscreen disable, floating enable')
                converted = True
            if needs_effect_size_reset(window, window.id not in seen, config):
                command(f'[con_id={window.id}] resize set width {config.surge_effects_width} px '
                        f'height {config.surge_effects_height} px')
                converted = True
        current_ids = frozenset(w.id for w in windows)
        new_ids = current_ids - seen
        seen = current_ids
        if converted:
            time.sleep(config.poll_seconds)  # Let the plugin restore its native floating size.
            windows = read_windows()
        current = signature(windows)
        if current != previous:
            apply_layout(windows, config)
            previous = current
        if new_ids:
            target = library_focus_target(mapping(sway(('-t', 'get_tree'))), new_ids)
            if target is not None:
                command(f'[con_id={target}] focus')
        if args.once:
            return
        time.sleep(config.poll_seconds)


if __name__ == '__main__':
    main()

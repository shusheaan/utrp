"""Validate the cover ranking and rebuild its index without deleting song assets."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import tomllib

if __package__:
    from . import render_cover as cover
else:
    import render_cover as cover


@dataclass(frozen=True)
class Entry:
    path: Path
    group: str
    rank: int
    artist: str
    song: str
    key: str
    original: str
    melody_status: str


def load_entry(path: Path) -> Entry:
    with path.open('rb') as stream:
        raw = tomllib.load(stream)
    data = cover.table(raw['library'])
    rank = data['rank']
    if type(rank) is not int or rank < 0:
        raise ValueError(f'{path}: rank must be a nonnegative integer')
    original = data['original']
    if not isinstance(original, str):
        raise ValueError(f'{path}: original must be text (empty for additions)')
    status = cover.string(data['melody_status'])
    if status not in ('pending', 'excerpt', 'verified'):
        raise ValueError(f'{path}: unknown melody status')
    return Entry(path, cover.string(data['group']), rank,
                 cover.string(data['artist']), cover.string(data['song']),
                 cover.string(data['key']), original, status)


def entries(root: Path) -> tuple[Entry, ...]:
    return tuple(load_entry(path) for path in sorted(root.glob('*/*.toml')))


def validate(items: tuple[Entry, ...], slots: int, assets: bool = True) -> None:
    if type(slots) is not int or slots < 1:
        raise ValueError('slots_per_group must be a positive integer')
    groups = {item.group for item in items}
    if len(groups) != 12 or {cover.pitch_class(g) for g in groups} != set(range(12)):
        raise ValueError('Expected exactly twelve distinct key groups')
    identities = [(item.artist, item.song) for item in items]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate song identity')
    for group in groups:
        members = tuple(item for item in items if item.group == group)
        if len({item.path.parent for item in members}) != 1:
            raise ValueError(f'{group}: each group needs a single directory')
        if sorted(item.rank for item in members if item.rank) != list(range(1, slots+1)):
            raise ValueError(f'{group}: active ranks must be exactly 1..{slots}; replace, do not delete assets')
    if len({item.path.parent for item in items}) != 12:
        raise ValueError('Expected one directory per key group')
    if assets:
        for item in items:
            for suffix in ('.md', '.png'):
                if not item.path.with_suffix(suffix).is_file():
                    raise ValueError(f'Missing asset: {item.path.with_suffix(suffix)}')
            if not item.path.with_suffix('.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError(f'Invalid PNG: {item.path}')


def link(item: Entry, root: Path) -> str:
    path = item.path.with_suffix('.md').relative_to(root).as_posix()
    return f'[{item.artist} — {item.song}]({path})'


def index_text(items: tuple[Entry, ...], root: Path, slots: int) -> str:
    groups = sorted({item.group for item in items}, key=cover.pitch_class)
    pending = sum(item.melody_status == 'pending' for item in items if item.rank)
    lines = ['# Covers', '', f'**榜单 12 × {slots}；资料永久保留，下榜不删文件。**', '',
             '每调一个目录；每首仅 `md + toml + png`。沿用 Pink + White / U-N-I-T-Y 版式：'
             '6–8 格长图，钢琴、高低音五线谱、六个七品把位、下方品位点。', '',
             f'**当前是研究初稿，不是已全部核验的谱库。榜内 {pending} 首核心旋律待补；'
             '其自编和弦音练习不冒充原曲旋律。** 调性争议见各曲说明；榜单序号是当前探索优先级，不是客观评分。', '',
             '## 当前榜单', '', '| 调组 | '+ ' | '.join(str(i) for i in range(1,slots+1))+' |',
             '|---|'+'---|'*slots]
    for group in groups:
        members = sorted((item for item in items if item.group == group and item.rank), key=lambda i:i.rank)
        key = cover.atlas.MajorKey.from_name(group)
        minor = key.letters[5] + {-1:'b',0:'',1:'#'}[key.accidentals[5]] + 'm'
        lines.append(f'| {group} / {minor} | '+' | '.join(link(i,root) for i in members)+' |')
    archive = tuple(item for item in items if not item.rank)
    lines += ['', '## 榜外保留', '', '| 歌曲 | 工作调性 |', '|---|---|']
    lines += [f'| {link(item,root)} | {item.key} |' for item in archive]
    lines += ['', '## 原始 36 首追踪', '', '| 歌曲 | 原表标注（未核验） | 当前工作调性 |', '|---|---|---|']
    lines += [f'| {link(i,root)} | {i.original} | {i.key} |' for i in items if i.original]
    lines += ['', '## 维护', '',
              '- 每首 TOML 的 `[library].rank`：`1–5` 在榜，`0` 仅存档。替换时旧曲改 `0`，新曲承接其名次；已有资料直接复用。',
              '- 不自动删除文件，也不拿未核实曲目冒充已完成转录。没有合适替补时检查会报缺额，不静默凑数。', '',
              '```sh', 'python scripts/cover_library.py --check',
              'python scripts/cover_library.py --write-index',
              'python scripts/render_cover.py covers/A-major_F-sharp-minor/A-major--frank-ocean--pink-white.toml --force',
              '```', '', '绘图依赖：`fontTools`、`rsvg-convert`、`FreeSerif`、`Noto Sans CJK SC`。来源及证据限制见各曲 MD。', '']
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('covers'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write-index', action='store_true')
    args = parser.parse_args()
    try:
        with (Path(__file__).resolve().parents[1]/'config/cover-atlas.toml').open('rb') as stream:
            slots = cover.integer(cover.table(tomllib.load(stream)['library'])['slots_per_group'],1,100)
        items = entries(args.root)
        validate(items,slots)
        if args.write_index:
            (args.root/'readme.md').write_text(index_text(items,args.root,slots))
        print(f'{sum(i.rank > 0 for i in items)} active; {sum(i.rank == 0 for i in items)} archived; no song files deleted')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1,f'Error: {error}\n')


if __name__ == '__main__':
    main()

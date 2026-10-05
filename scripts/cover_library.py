"""Validate the cover ranking and rebuild its index without deleting song assets."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import struct
import subprocess
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


def validate_chord_label(card: cover.Card) -> None:
    """Check the displayed symbol, not just whether the pitches form some chord."""
    symbol = card.title.split(' · ', 1)[0]
    match = re.fullmatch(r'([A-G][#b]?)(maj9|maj7|m9|m7|add9|7sus4|sus4|sus2|9|7|6|m)?', symbol)
    if match is None:
        raise ValueError(f'Unsupported chord label: {symbol}')
    intervals = {
        '': (0, 4, 7), 'm': (0, 3, 7), '6': (0, 4, 7, 9),
        'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10), '7': (0, 4, 7, 10),
        'sus2': (0, 2, 7), 'sus4': (0, 5, 7), '7sus4': (0, 5, 7, 10),
        'add9': (0, 4, 7, 2), 'maj9': (0, 4, 7, 11, 2),
        'm9': (0, 3, 7, 10, 2), '9': (0, 4, 7, 10, 2),
    }[match[2] or '']
    root = cover.pitch_class(match[1])
    if tuple(cover.pitch_class(n) for n in card.notes) != tuple((root+i) % 12 for i in intervals):
        raise ValueError(f'Chord label disagrees with notes: {symbol}')


def validate_evidence(raw: dict[str, object], song: cover.Song) -> None:
    library = cover.table(raw['library'])
    sources = cover.strings(library['sources'])
    if not sources or any(not url.startswith('https://') for url in sources):
        raise ValueError('Expected nonempty HTTPS reference sources')
    raw_cards = raw['cards']
    if not isinstance(raw_cards, list):
        raise ValueError('Expected cards array')
    if library['melody_status'] == 'excerpt' and not any(
        cover.table(value).get('evidence') == 'reference_excerpt' for value in raw_cards
    ):
        raise ValueError('Excerpt status requires at least one reference excerpt')
    for value, card in zip(raw_cards, song.cards, strict=True):
        data = cover.table(value)
        evidence = cover.string(data['evidence'])
        if evidence == 'arrangement':
            if card.kind != 'melody' or '自编' not in card.title:
                raise ValueError('Arrangement needs an explicit self-authored melody label')
        elif evidence in ('reference_harmony', 'inferred_harmony', 'reference_excerpt'):
            expected = 'melody' if evidence == 'reference_excerpt' else 'chord'
            if card.kind != expected or cover.string(data['source']) not in sources:
                raise ValueError('Reference card needs matching kind and a listed source')
            if evidence == 'inferred_harmony' and '推断' not in card.title:
                raise ValueError('Inferred harmony needs an explicit inference label')
            if evidence == 'reference_excerpt' and library['melody_status'] == 'pending':
                raise ValueError('Pending melody cannot contain a claimed reference excerpt')
        else:
            raise ValueError(f'Unknown evidence label: {evidence}')
        if card.kind == 'chord':
            validate_chord_label(card)
    chords = tuple(c for c in song.cards if c.kind == 'chord')
    for card in song.cards:
        if card.title == '自编连接 · 逐卡和弦音选点':
            if len(card.notes) != len(chords) or any(
                cover.midi_note(n) % 12 not in {cover.pitch_class(p) for p in chord.notes}
                for n, chord in zip(card.notes, chords)
            ):
                raise ValueError('Per-card exercise must select one tone from each chord')


def validate_content(path: Path, style: cover.Style) -> None:
    raw = tomllib.loads(path.read_text())
    song = cover.parse_song(raw, style)
    validate_evidence(raw, song)
    library = cover.table(raw['library'])
    date.fromisoformat(cover.string(library['audit_date']))
    markdown = path.with_suffix('.md').read_text()
    title = f"{cover.string(library['artist'])} — {cover.string(library['song'])}"
    if song.title != title or not markdown.startswith(f'# {title}\n'):
        raise ValueError(f'{path}: Song identity disagrees across library, chart and Markdown')
    for field in ('audit_note', 'metadata_note'):
        if cover.string(library[field]) not in markdown:
            raise ValueError(f'{path}: Markdown {field} disagrees with TOML')
    if '## 结构与进行' in markdown:
        for field in ('status', 'structure', 'progression'):
            if cover.string(raw[field]) not in markdown:
                raise ValueError(f'{path}: Markdown {field} disagrees with TOML')
        for field in ('key', 'why', 'caveat'):
            if cover.string(library[field]) not in markdown:
                raise ValueError(f'{path}: Markdown {field} disagrees with library metadata')
    if any(url not in markdown for url in cover.strings(library['sources'])):
        raise ValueError(f'{path}: Reference source missing from Markdown')
    png = path.with_suffix('.png').read_bytes()
    if len(png) < 33 or png[:8] != b'\x89PNG\r\n\x1a\n' or png[12:16] != b'IHDR':
        raise ValueError(f'Invalid PNG: {path}')
    if struct.unpack('>II', png[16:24]) != (1600, 420 + 1030 * len(song.cards)):
        raise ValueError(f'{path}: PNG dimensions disagree with card count')


def validate_rendered(items: tuple[Entry, ...], style: cover.Style) -> None:
    """Exact deterministic regeneration catches stale diagrams, not source accuracy."""
    clefs = cover.atlas.load_clefs(style.atlas.music_font)
    for item in items:
        song = cover.parse_song(tomllib.loads(item.path.read_text()), style)
        result = subprocess.run(['rsvg-convert', '--format=png'],
                                input=cover.render_svg(song, style, clefs).encode(),
                                capture_output=True, check=True)
        if result.stdout != item.path.with_suffix('.png').read_bytes():
            raise ValueError(f'{item.path}: PNG differs from current renderer; regenerate it')


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
        style = cover.load_style(Path(__file__).resolve().parents[1]/'config/cover-atlas.toml')
        for item in items:
            for suffix in ('.md', '.png'):
                if not item.path.with_suffix(suffix).is_file():
                    raise ValueError(f'Missing asset: {item.path.with_suffix(suffix)}')
            validate_content(item.path, style)


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
             '## 全量复核边界', '',
             f'{len(items)} 首均有逐曲复核记录（TOML `audit_date` / `audit_note` 与同名 MD）。'
             '联网对照可取得的谱例与作者说明，并检查音高、弦品、和弦名称、证据标签及图文一致性；'
             '未逐段听核全部原录音，未取得的完整商业谱、视频、具体录音版本与所有节奏细节不冒充已验证。', '',
             '主艺人、曲名、专辑归属已逐曲核对并附 `metadata_note` 与发行资料链接；'
             '其中 Endless 的 4 首分曲由发布报道/曲目数据库交叉支持，未直接读取官方片尾 credits。'
             '这不是完整演职员表，也不证明所引编配与某一录音版本完全相同。', '',
             '自编逐卡选音只保证来自相应和弦，不保证最近距离；卡片顺序不是原曲完整进行。'
             '来源相符不等于来源本身正确；机器识别、版本冲突和参考编配的限制见逐曲记录。', '',
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
              'python scripts/cover_library.py --check --check-images',
              'python scripts/cover_library.py --write-index',
              'python scripts/render_cover.py covers/A-major_F-sharp-minor/A-major--frank-ocean--pink-white.toml --force',
              '```', '', '绘图依赖：`fontTools`、`rsvg-convert`、`FreeSerif`、`Noto Sans CJK SC`。来源及证据限制见各曲 MD。', '']
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('covers'))
    parser.add_argument('--check-images', action='store_true',
                        help='Compare every PNG with deterministic regeneration (requires rsvg-convert)')
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
        elif (args.root/'readme.md').read_text() != index_text(items,args.root,slots):
            raise ValueError('Stale cover index; run --write-index')
        if args.check_images:
            style = cover.load_style(Path(__file__).resolve().parents[1]/'config/cover-atlas.toml')
            validate_rendered(items, style)
        print(f'{sum(i.rank > 0 for i in items)} active; {sum(i.rank == 0 for i in items)} archived; no song files deleted')
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1,f'Error: {error}\n')


if __name__ == '__main__':
    main()

"""Extract five unmodified Bravura SMuFL outlines into a pitch-anchored atlas."""
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


def render(font_path: Path, output: Path) -> None:
    with TTFont(font_path) as font:
        if font['name'].getDebugName(1) != 'Bravura' or font['head'].unitsPerEm != 1000:
            raise ValueError('Expected Bravura, 1000 units/em')
        cmap = font.getBestCmap()
        if cmap is None:
            raise ValueError('Missing cmap')
        glyphs = font.getGlyphSet()
        parts = []
        for index, codepoint in enumerate((0xE050, 0xE062, 0xE260, 0xE262, 0xE261)):
            pen = SVGPathPen(glyphs)
            glyphs[cmap[codepoint]].draw(pen)
            # Every glyph origin is the named staff-line/pitch anchor, not its bbox centre.
            parts.append(f'<path data-codepoint="{codepoint:04X}" transform="translate({index * 128 + 16} 160) scale(.12 -.12)" d="{pen.getCommands()}"/>')
    output.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="256" viewBox="0 0 640 256">\n'
                      '<!-- Bravura outlines, Steinberg, SIL OFL 1.1. See notation-license.txt. -->\n'
                      '<g fill="#222222">\n' + '\n'.join(parts) + '\n</g></svg>\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('font', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    render(args.font, args.output)


if __name__ == '__main__':
    main()

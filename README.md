# utrp
![preview](./preview.gif)  
   
master music and your instrument for fearless composition and improvisation!  
interactive progression trainer for **ALL** harmonic dynamics, [midi](https://wiki.archlinux.org/title/USB_MIDI_keyboards)  
*"u-tr-p" is pronounced like [euterpe](https://en.wikipedia.org/wiki/Euterpe)*

## 十二调图谱 / Major-key atlas

- 十二调竖排：[白底](scripts/major-scales-atlas-mobile.png) · [黑底](scripts/major-scales-atlas-mobile-dark.png)
- 4 × 3 总览：[白底](scripts/major-scales-atlas.png) · [黑底](scripts/major-scales-atlas-dark.png)
- 每调两行：五线谱（两列交替，只写音名）、窄键盘、两张指板；下排四张指板。
- 颜色分组不变：1 红、2/3 绿、4/5 鲑鱼色、6/7 蓝；黑底版提亮。配色在 `config/c-major-atlas.toml`。

Regenerate both themes (SVG + PNG; requires `fontTools`, FreeSerif and `rsvg-convert`):

```sh
for theme in light dark; do
  python scripts/render_key_atlas.py --stacked --theme "$theme" --force
  python scripts/render_key_atlas.py --all-keys --theme "$theme" --force
done
for svg in scripts/major-scales-atlas*.svg; do
  rsvg-convert "$svg" -o "${svg%.svg}.png"
done
```

The default is `--theme light`; dark outputs add `-dark` to the filename.
Both themes retain physical black/white piano keys and identical note/degree mappings.

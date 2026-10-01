# 横向指板矩阵：工具研究与生成方法

[English](fretboard-tools.md) · 2026-10-01

## 结论：一张图只解决一个问题

已有开源工具，不必重造完整乐理库。当前需求是把 **Drown 的谱面骨架**变成可重复生成、直接嵌入 Markdown 的图，因此先用小型 Python renderer；以后需要交互时再考虑 JS。以下是官方文档对比，**未安装这些外部库做运行基准或视觉横评**。

| 工具 | 文档确认的能力 | 对本项目的适配判断 |
|---|---|---|
| [FretBoardGtr](https://fretboardgtr.readthedocs.io/en/stable/get-started/get-started.html) | Python；音阶、SVG、横／竖方向、品位范围、颜色及音名／级数配置 | 通用 Python 音阶图的优先候选；若进一步扩展音阶功能，先评估它 |
| [python-fretboard](https://github.com/dmpayton/python-fretboard) | Python SVG 指板／和弦图，marker 标签和颜色 | 适合自定义点位；需再编排乐句路线与解释 |
| [fretboard.js](https://github.com/moonwave99/fretboard.js) | 浏览器指板图，配套音阶与 CAGED／TNPS 工具 | 以后做交互选音、练习界面时的候选，目前无需前端工程 |
| [SVGuitar](https://github.com/omnibrain/svguitar) | SVG 和弦图，方向、指法、颜色配置 | 适合和弦 grip 展示；本次重点是跨把位旋律路线，不优先选它 |

## 视觉语法

1. **地图**：完整音阶，用于说明可用音和调性骨架，不冒充原谱路线。
2. **地标**：只高亮少数结构音，其他可用位置灰化，不要求全弹。
3. **路线**：只保留该句动作；箭头表示方向，不编码时值。双音的两条线同步移动。

高音 e 在上、低音 E 在下、品数向右增加。颜色相对每张图明确写出的参照音：红＝1、金＝♭3／3、蓝＝5、青＝其他选中音、灰＝背景；每点另写音名和 degree。参照音不自动等于已确认的伴奏根音。每图最多 14 个品位列；一图一概念，标题说结论、图下注明证据边界。

已制作并嵌入 [Drown 分析](NLND_TABS/drown-mateus-skeleton.cn.md) 的五图：E minor 音阶、Em 地标、106 四度上行、117 八度下行、119 四音琶音。

## 复现

在项目根目录，Python 3.11+；生成 SVG 只用标准库：

```sh
python scripts/render_fretboard.py sheets/NLND_TABS/drown-matrices.toml \
  --output sheets/NLND_TABS --force
```

初次输出可省略 `--force`；已有文件时默认拒绝覆盖。配置见 [drown-matrices.toml](NLND_TABS/drown-matrices.toml)，脚本见 [render_fretboard.py](../scripts/render_fretboard.py)。

Markdown 使用 PNG 获得更广泛的预览兼容性，同时保留 SVG 供缩放。PNG 转换需 `rsvg-convert`（librsvg）和中文字体；本机已有，无需本次安装：

```sh
for f in sheets/NLND_TABS/drown-*.svg; do
  rsvg-convert "$f" -o "${f%.svg}.png"
done
```

每次改配置后同时重生成 SVG 和 PNG，再打开预览，防止两种格式版本不一致。中文字体用 `Noto Sans CJK SC`，跨机器应确认可用字体；本工具不内嵌字体。

## 配置边界

- `strings` 与 `tuning` 按显示顺序一一对应，后者是六根空弦的 MIDI 音高。
- `tonic` 是 0–11 pitch class（C=0，E=4，A=9），用于当前图的级数参照。
- `context` 是背景音集合；`auto_scale=true` 自动枚举范围内全部位置，不能同时配置 `anchors`。
- `anchors=["G12", "B12", "e12"]` 指定高亮位置；`paths` 是按先后排列的 anchor 路线。
- `first`／`last` 指定显示范围；`slug` 决定输出文件名；标题、副标题、图下注释由配置提供。
- `pitch_names` 和 `degrees` 是显式的 12 项显示表。脚本做半音／pitch-class 运算，**不自动决定调性、和弦功能或正确的等音拼写**。
- `theme` 控制颜色和字体。布局为固定的六弦横向矩阵，不是完整 TAB、节奏排版器或自动和声分析器。长文案需要预览检查，不自动换行。

## 验证

```sh
python -m pytest -q tests/test_render_fretboard.py
```

需要开发依赖 `pytest`、`hypothesis`。覆盖音高八度不变性、完整音阶枚举、谱面地标、四度关系、SVG XML、相邻弦箭头、非法配置与覆盖保护。对本组图另做人工视觉检查；自动测试不替代核谱，也不证明伴奏和声。

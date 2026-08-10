# lib — 音色库(patch 即代码)

utrp 的声音资产层:合成器 patch 全部以文本/小文件形式进 git,宿主通过 symlink
看到它们。目标是让"调音色"像写代码:可 diff、可回滚、git 历史即作者证据链。

在此之上,lib 承载三条核心能力线(详见下文"三大支柱"):

1. **音色复现**:给定几首歌/几个段落,系统性拿到音色信息,最快速度在
   Surge 里做出 4–5 个备选 patch 供耳朵挑;
2. **鼓 transcription**:把参考曲的鼓段(如《MAGDALENE》fallen alien 的
   鼓 solo)自动转成 MIDI + 可视化 step grid,直接套进别的 kit;
3. **和声探索**:选调后在普通电脑键盘上单键触发级数和弦,快速轮换
   十几种 piano/guitar voicing,探索复杂和弦进行并导出。

## 布局与约定

```
lib/
  surge/           # Surge XT patch(.fxp,内容为 XML),按 collection 分子目录
    endless/       # Frank Ocean《Endless》复刻实验(2026-08-09 起)
    sega-universe/ # Sega Bodega《I Created The Universe…》
    tev-woods/     # Tev Woods
    magdalene/     # FKA twigs《MAGDALENE》
  tools/
    pipeline/      # 支柱 1+2:spec TOML -> 分析/browse/渲染/评分/鼓 MIDI/RPP
    harmony/       # 支柱 3:和弦 voicing 键盘探索器(theory/voicings/explore)
    <collection>/  # 各专辑的提取数据(data/)+ 未泛化的特例脚本(存档)
  link.sh          # 布链:Surge 浏览器 User 区出现 utrp/ 目录
```

- 按引擎分顶层目录(以后可加 zyn/、sfz/、drumkv1/),按主题分 collection 子目录
- 命名:`<目标>-<变体>.fxp`;收录时在 Surge 的 patch comment 里写一行配方要点
  (如 `2saw det7 | LP24@1.8k | A550ms | chorus+hall`)
- **只进文本类 patch。任何音频物料(采样、渲染、stem)留 `~/storage`,
  尤其从唱片切的采样绝不进这个公开仓库**

## 三大支柱

### 1. 音色复现:参考段落 -> 4–5 个备选 patch

流程(命令细节见 `tools/pipeline/README.md`):
`separate`(demucs 分轨)→ `scan`(全轨频谱粗扫,人眼选目标段)→
`measure`(深度测量)→ `browse`(**全厂库 ~3000 patch 自动渲染排名,
直接吐出可粘贴的候选行**)→ `render`(渲染打分,fxp 落库)→
`project`(A/B 用 REAPER 工程)。

对 ambient/复杂合成音色,measure 按合成器分区提取可执行特征:
谐波梯子与奇偶比(→ OSC 波形)、attack(→ Amp EG)、centroid
起/中/末/斜率轨迹(→ Filter EG 开合)、0.3–12Hz 幅度与亮度调制
(→ LFO)、分频段 side/mid 宽度(→ unison/chorus)、谱平坦度
(→ 噪声成分)。数字告诉你拧哪里,分数只排序,**最终以耳朵为准**——
browse 给 top-24,人挑 4–5 个进 spec 再精调。

已知边界:复合目标(lead 叠 pad)谱距离虚高;混响是 FX 链的事,参数层
复现不了,选自带对应 FX 的基底。想加的下一步:混响尾 RT60 估计、
按 measurements 自动生成 tweaks 初值(attack/cutoff 直接写进候选)。

### 2. 鼓 transcription:鼓段 -> MIDI / grid / 谱

`analysis.py drums` 打点分类(kick/snare/hat/perc)+ 切 one-shot +
重建对照音频;`drummidi.py` 恒速网格拟合(比 beat_track 的浮动拍点准
3 倍)、逐 hit 直拍/三连音量化,输出:

- `pattern.mid` — 3 轨 SMF:tempo + **quantized(套别的 kit 用)** +
  as-played(保留原始微时值);GM 映射,任何 DAW 直接拖;
- `grid.txt` / `grid.html` — step sequencer 视角的可视化格,力度分级、
  三连音标注、偏差 tooltip;乐谱需求用 MIDI 导入打谱软件即得。

已在四张专辑 8 个鼓段上验证(fallen alien 140bpm 中位偏差 9ms)。
下一步:swing 量估计、按 one-shot 频谱聚类自动分 layered 采样、
grid.html 做成可编辑回写 MIDI。

### 3. 和声探索:键盘即和弦实验台

`tools/harmony/`(用法见其 README):Rust utrp 的 theory 思路 +
素材库音色。选调选调式后 `a–j` 七键 = 七级顺阶七和弦,大写 = 副属,
`v` 轮换 voicing(piano 12 种 + guitar 8 种预设,TOML 可追加自定义),
`m` 换调式、`k` 移调、`p` 换 lib 里任意 patch 出声;`r/x` 录下进行导出
JSON(进 git)+ MIDI(进 storage)。demo 子命令一行渲染整条进行。
Voicing 是音高层面的抽象;指板/键位图与练习打分仍归 Rust utrp TUI。

## 接入宿主

```sh
./link.sh   # ~/.Surge Synth Team/Surge XT/Patches/utrp -> lib/surge
```

系统重装后重跑一次(本仓库不由 gral 的 10-install.sh 管理)。在 Surge 里
save patch 时选 utrp/ 下的目录 = 自动落进本仓库。

## 环境关联(gral)

本目录只管音乐资产;插件与宿主环境由 `~/work/gral` 还原,坏了先去那边查:

- 装了哪些合成器/效果:`gral/arch/audio-packages.txt`(取消注释 = 在用)
- REAPER 安装与配置纳管、硬件陷阱(DISPLAY / 采样率 / 电平):`gral/arch/audio/readme.md`
- 体检:`gral/arch/scripts/61-audio-stack doctor`
- A/B 参考工程与渲染管线:`~/storage/daw/endless-ref/`(scripts/ 内有完整分析代码)

## 管线产物分流

一张专辑 = 一个 `tools/pipeline/specs/<album>.toml`。产物分流:fxp 与
进行 JSON 进本仓库,音频/MIDI/REAPER 工程进 `~/storage/daw/<name>/`。
现有四个 collection(共 47 个候选)的 A/B 工程分别在 `~/storage/daw/` 的
endless-ref、sega-universe、tev-woods、magdalene,目标与配方见各工程 README。

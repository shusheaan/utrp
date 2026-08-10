# utrp/lib — 音色库

patch 即代码。本目录是 utrp 里唯一的音乐资产层,repo 其余部分(Rust TUI)不相干。

## 三层边界(跨仓库,勿混)

- **机器配置** → `~/work/gral`:音频包选型 `arch/audio-packages.txt`、REAPER
  配置纳管 `arch/reaper/`、音频栈文档 `arch/audio/readme.md`、体检
  `./arch/scripts/61-audio-stack doctor`。重装要还原的都在那边。
- **音乐资产/实验** → 本目录:合成器 patch、collection、(将来)SFZ/渲染工具。
  只进文本;**唱片采样与音频物料绝不进**(public repo)。
- **音频物料/工程** → `~/storage/daw/`:REAPER 工程(.rpp)、demucs stem、
  渲染产物、从唱片切的采样 kit。当构建产物,不进任何 git。

音色任务(调 patch / 扒音色 / 写歌实验)在 utrp 开 agent 并主要在本目录工作;
装包/配置/音频栈问题去 gral 开。宿主接入:`./link.sh`(重装后重跑)。

## 工具地图(细节看各自 README,先读再动手)

- **扒音色/扒鼓** → `tools/pipeline/`:spec TOML 驱动,separate/scan/measure/
  browse(全厂库自动选备选)/drums/drummidi(鼓→MIDI+grid)/render/project。
  两个 venv:`~/.cache/timbre-pipeline/venv-analysis`(librosa)与
  `venv-render`(surgepy + pyyaml)。
- **和声探索** → `tools/harmony/`:explore.py(键盘手动)、perform.py +
  session.yaml(simulation 表演,YAML 全参数,双种子可复现,`--replay` 回放)。
- **和声引擎** → `tools/simulate/`:Rust 胶水 crate,`#[path]` 原样编译
  `../../src/theory`;**仓库根的 `src/` 是只读的,永远不改**,一切扩展走
  lib 侧胶水(含种子:LD_PRELOAD 垫片,见其 README)。
  首次构建:`cargo build --release` + `gcc` 编 `shim/seedrandom.c`。

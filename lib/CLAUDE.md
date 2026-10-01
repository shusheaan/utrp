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

## 项目方向(2026-08 定)

主攻**工程化/批量化/音乐逆向/音色发现**。用户极少直接操作 DAW——一切走
工程化自动化(agent 生成工程/渲染/MIDI,人只做试听与决策)。DAW 只用
REAPER(纯文本 .rpp + ReaScript + 命令行渲染是选它的全部理由;Bitwig
评估过,因脚本化弱而不用)。做新功能优先考虑"能否无 GUI 批量跑"。
本仓库只做音乐:3D/视觉管线(Blender 等)在独立 repo,任何相关代码与文档都不进这里。

## 工具地图(细节看各自 README,先读再动手)

- **扒音色/扒鼓** → `tools/pipeline/`:spec TOML 驱动,separate/scan/measure/
  browse(全厂库自动选备选)/drums/drummidi(鼓→MIDI+grid)/render/project。
  两个 venv:`~/.cache/timbre-pipeline/venv-analysis`(librosa)与
  `venv-render`(surgepy + pyyaml)。
- **和声探索** → `tools/harmony/`:explore.py(键盘手动)、perform.py +
  session.yaml(simulation 表演,YAML 全参数,双种子可复现,`--replay` 回放)。
- **音色逆向** → `tools/repatch/`:palette.py(歌→N 个音色色块)+
  soundmatch.py(全库秒级检索,索引在 ~/storage/daw/repatch-index)+
  refine.py(参数搜索精调)+ reabridge.py/`tools/reaper/`(REAPER 一键桥,
  link.sh 布链);市场分析见
  `../docs/2026-08-10-sound-reverse-engineering-market.md`。
- **和声引擎** → 根 `src/lib.rs` 的 theory/progression/guitar/session；
  `tools/simulate/` 是依赖共享 library 的薄适配器，不复制 TUI driver。
  用户已授权实现核心指板训练：原“根 src 永远只读”约定撤销，允许改共享引擎与 TUI。
  随机数使用原生 seed；无需 LD_PRELOAD shim。首次构建 `cargo build --release`。

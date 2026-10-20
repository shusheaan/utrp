# utrp/lib — 音色库

patch 即代码。本目录是 utrp 里唯一的音乐资产层,repo 其余部分(Rust TUI)不相干。

## 三层边界（2026-10-20 更新）

- **系统基础配置** → `~/work/gral`：系统包、shell、机器级维护。`bitwig` / `bw` 启动命令由 `arch/zshrc` 管理。
- **音乐源码与 DAW 定制配方** → 本目录：patch、CLAP 插件源码、controller、音频路由、窗口布局、部署/恢复工具。工具职责见 [tools/README.cn.md](tools/README.cn.md)。
- **工程、音频与运行资源** → `~/storage/daw/`：Library、录音、采样、已安装插件/主题和恢复快照，不进 Git。音乐偏好实体在 `UserData/`，home 为目录 symlink；以 `tools/daw_backup/live.toml` 为清单，不能用时间点备份替代实时主数据。

重装按 `tools/daw_backup/README.cn.md` 恢复；`link.sh` 只是部分旧资源入口，不能替代完整恢复。真实录音、唱片物料和账号凭据不进公共仓库。

## 当前项目方向

Bitwig 是当前交互式音色探索与录音实验宿主，Library 工程在 Storage；REAPER 保留兼容用途，不是唯一宿主。优先复用跨宿主 CLAP 与可测试的计算核心，但不以脚本能力代替真实 GUI/输入输出验收。
Chord Lab 当前只有一个 CLAP 产品：`tools/chordlab/` 是其内嵌引擎，`tools/chordlab_clap/` 是宿主外壳，不能把引擎误当成可删除的旧产品。
Beat Lab 独立放在 `tools/beatlab/`。`guitar_frontend/` 是当前单音产品；`guitar_poly/` 仅是历史隔离研究，未通过双音验收。
本仓库只做音乐；3D/视觉项目留在独立仓库。

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

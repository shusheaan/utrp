# Beat Lab — 录音转四类 MIDI 节奏

[English](README.md) · [验收记录](VALIDATION.cn.md) · [Clip 工作流](WORKFLOW.cn.md)

## 唯一核心流程

**录音 + 明确 BPM → 自动分析 → 最多 A/B/C/D 四类 → 映射鼓音、量化编辑 → MIDI Clip。**

当前主流程改为 **Beat Lab 内录音**：在一条接收麦克风的 Bitwig 轨上挂载插件，开启监听，
不必录 Audio Clip、不用手动导出/保存 WAV。上方是四小节波形，下方是 MIDI 节奏网格。
当前输出仍为 `.mid` 文件，拖回鼓机轨；直接写入宿主 MIDI Clip 尚未实现。

### 录音操作

1. Bitwig 设置 BPM（40–240）、4/4；承载轨输入选麦克风，开启监控，让音频流入插件。
2. 插件跟随宿主 BPM。`Once / 4 bars` 录一次；`Loop / overwrite` 重复覆盖。
3. 点 `Record`，倒数四拍（4、3、2、1，一个小节）后录四小节。无需启动 Bitwig 全局录音。
4. Once 自动结束；Loop 按 `Stop`。保留最后一个完整四小节，舍弃不足四小节的末尾；
   尚无新完整 take 时保留之前的录音与 MIDI，不把半截当四小节。
5. 自动分析，编辑分类、映射、量化，再导出 MIDI。录音/分析期间不允许导入或导出旧结果。
6. 保存 Bitwig 工程：完整源录音与 MIDI 分析一起嵌入插件 state，不需外部 WAV。

录音时钟按宿主 BPM 本地运行，**不启动/定位 DAW transport，也不保证对齐 Arrange 的整小节边界**。
宿主停止时也可录，但必须持续处理麦克风输入。缺少宿主 tempo 时明确显示 Manual BPM。
中途 tempo、采样率或拍号变化会取消当前未完成 take，避免生成错误长度。
建议戴耳机；节拍声不会在代码里混入录音，但扬声器声音仍可能被麦克风重新拾取。
`Click` 控制录音中的节拍声，倒数仍有节拍。暂未做实机输入/输出延迟校准。

**部署状态：0.3.1 已安装 CLAP / Standalone，并重开 Bitwig 验证。用户实际录音已恢复并重新分析；Gate −45 下为 33 个候选（原版 8 个），原始 PCM 不变。候选与类别准确率未完成人工验收，不能将数量增加视为全对。详见 VALIDATION。**

## 本地构建已实现

- Rust：起音检测、频谱特征、最多四类相似声音聚类、量化、力度与 MIDI 编码。
  不足四类不强凑，A/B/C/D 不是可靠的 Kick/Snare/Hat/Clap 语义识别。
- Record/Stop、Once/Loop、四拍倒数、波形与播放头；双缓冲只保留最后完整 take，不累积多轨录音。
- 输入单个 WAV（文件拖入或开发用 Import WAV）后自动分析；BPM 由用户明确填写。
  新录音严格固定四小节（4/4，共 16 拍），保留前导静音；长度与 BPM 不符时拒绝，不截断、不补齐、不拉伸（允许一个采样的舍入误差）。
- 四个独立 MIDI note 映射，默认 36/38/42/39。名字是 GM 提示，实际鼓音取决于下游鼓机。
- Review 是待确认事件，不是第五种音色，不导出；用户可改到 A/B/C/D 或删除。
- 四小节连续网格；1/16、1/32、1/64 与 1/16、1/32 三连音。小节、拍、细分三级刻度。
- View grid 只控制显示与手工添加位置；Quantize 独立控制输出，默认 Off 保留原始时差。
- Zoom 可看四／二／一小节，横向滑条移动视区；四类与 Review 标签固定，不随时间滚走。
- 支持添加事件、改分类、改力度、删除。密集音符使用窄标记，点击命中按像素与缩放计算。
- Hear 只试听某类的原始音频切片，**不是目标鼓机音色试听**。
- 改 BPM/Gate 后用 Reanalyze 重算，避免自动覆盖手工编辑；有录音但分析已失效时禁止导出。
- Export MIDI File 仍是开发验证出口，**不是 MIDI Clip 集成完成标志**。
- Example 为合成测试入口，不是口技准确率证明。

## 状态与限制

- Pattern v2 使用四类 + Review；v1 三类仍可读取。旧 Review 转为新 Review，不误变成 D 类发声。
- State v3 保存原始单声道 PCM、录音 BPM/采样率、pattern、映射与量化；兼容旧 pattern-only state。
  完整录音可恢复；录音中应先 Stop 再保存，以免只保存上一份已接受的 take。
- 新录音固定 4/4、四小节、40–240 BPM、8–192 kHz、mono/stereo WAV。旧的 1–8 小节 pattern 仍可读取导出。WAV sample 0 当第一拍，不自动猜录音起点。
- 一次分析一个声道；Input L/R 选择录音声道或下次导入的 WAV 声道。不要把源 WAV 等同于经过裁剪/拉伸的工程 Clip。
- 非语义分类，不分离重叠口技，不保证识别正确；保留 Review 与手工修正。
- 起音检测目前有 45 ms 最小间隔；更细网格可编辑/导出，并不证明超密集口技能自动全部检出。
- 当前 CLAP 仍是离线分析外壳，**无实时 MIDI 输出、无 MIDI drag-out、无直接宿主 Clip 写入**。
- 麦克风直通始终静音防回授，仅节拍及 Hear 输出；不要插入正常音源、吉他或 Master 效果链。

## 结构与构建

```text
engine/       Rust 计算核心及测试
plugin/       C++/JUCE 外壳与 UI
tests/        CLAP 和 UI 集成测试
theme.toml    独立配色源
dependencies.toml  JUCE / CLAP 依赖版本与 SHA-256
prepare.py    校验和解包依赖，不下载、不修改其他项目
```

需要 Rust（支持 edition 2024）、CMake、Ninja、C++17 编译器、Python 3.11+ 及 JUCE 的 Linux 开发依赖。按 `dependencies.toml` 下载四份归档到同一目录，命名为 `<name>.tar.gz`。本机已有缓存可复用：

```sh
python lib/tools/beatlab/prepare.py \
  --downloads target/chordlab-clap-build/downloads \
  --output lib/tools/beatlab/build/deps
cmake -S lib/tools/beatlab -B lib/tools/beatlab/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBEATLAB_DEPS="$PWD/lib/tools/beatlab/build/deps"
cmake --build lib/tools/beatlab/build -j2
cargo test --offline --manifest-path lib/tools/beatlab/Cargo.toml
cargo clippy --offline --manifest-path lib/tools/beatlab/Cargo.toml --all-targets -- -D warnings
ctest --test-dir lib/tools/beatlab/build --output-on-failure
```

`prepare.py` 拒绝覆盖已有目录；已有 deps 不重复执行。初次机器先 `cargo fetch --locked --manifest-path lib/tools/beatlab/Cargo.toml`，随后离线构建。`Cargo.lock` 固定 Rust 依赖。这里复用的是下载归档，**Beat Lab 有自己的解包目录，不依赖 Chord Lab 的修改版适配器**。

产物：
- `build/BeatLab_artefacts/Release/CLAP/Beat Lab.clap`
- `build/BeatLab_artefacts/Release/Standalone/Beat Lab`

JUCE 8 的使用/分发需遵循其 AGPLv3 或商业许可条款；其他依赖也保留各自许可证。此原型尚未作商业分发许可审查。

## 本机部署与恢复

- 源码：`~/work/utrp/lib/tools/beatlab/`，独立于 Chord Lab。
- CLAP：`~/.clap/Beat Lab.clap`；home 的 `.clap` 是目录链接，实体在 `~/storage/daw/UserData/.clap/`。
- Standalone：`~/storage/daw/Tools/BeatLab/Beat Lab`。
- 示例 WAV/MIDI/JSON：`~/storage/daw/BeatLab/Examples/`。
- 建议自己的录音/导出保存在 `~/storage/daw/BeatLab/`，不进入 Git。
- 重装先按 `lib/tools/daw_backup/live.py` 恢复目录链接。重新构建后关闭 Beat Lab 实例，备份旧二进制再复制新产物；不要用 home 实体目录替换链接。
- 收尾快照用 `python lib/tools/daw_backup/snapshot.py`，包含 `.clap` 和未忽略的源码。**快照不是 Git commit/push。**

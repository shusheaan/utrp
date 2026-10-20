# 原型验收 — 2026-10-20

[English](VALIDATION.md) · [使用说明](README.cn.md)

## 最新：插件内四小节录音（0.3.0）

- 新增 `plugin/recorder.h/.cpp` 与 `plugin/waveform.h`；host 音频 I/O 留在 C++，分析/分类/MIDI 计算仍为 Rust。
- Once/Loop、四拍 count-in、精确四小节、最后完整 take 保留；Stop 舍弃末尾不完整 take。
- Recorder 测试覆盖 count-in 不入录音、内部 click 不入录音、单次/循环、停止边界、tempo/采样率/拍号变化、无效输入和 fractional timing。
- GUI/processor 合成端到端：宿主停止仍处理输入、Input R、宿主小数 BPM、录后自动分析、四小节 MIDI、PCM state 恢复；保存发生在 UI timer 前也保留完整录音。
- Rust 14 项及 Clippy、CTest `clap`/`recorder`、GUI/FFI 测试通过。独立 Recorder UBSan 通过。
- ASan 未完成：运行环境报告 runtime link order 问题；不能算 sanitizer 全部通过。
- 人工检查合成输入截图 `/tmp/beatlab-four-bars/recording-ui.png`：上波形、下网格、四小节及录音控件可见。
- 未做 Bitwig 新实例实机麦克风/count-in 听感/延迟验收；合成信号不代表真实复杂口技准确率。
- 本地时钟跟随 host BPM，不启动 DAW transport、不做 Arrangement 小节相位对齐；节拍扬声器回录与硬件延迟需实机验证。
- MIDI Clip 直写、实时 MIDI 输出、跨录音 Sound Set 模板仍未完成；录音完成后通过 `.mid` 导出。
- 未 commit/push；部署与 Storage 快照结果见本轮收尾记录。

### 0.3.0 部署记录

已原子部署到 `~/storage/daw/UserData/.clap/Beat Lab.clap` 与 `~/storage/daw/Tools/BeatLab/Beat Lab`。
旧二进制保存在 `~/storage/daw/BeatLab/Backups/20261020T192935Z-recording-v030/`。
CLAP SHA-256：`648a5ae262d15a081f946e5f88166ad1defa4d02997fff18eea04bbff9ffeefd`。
未重启 Bitwig，未修改 Library；宿主内现有实例需重新加载，不能据文件部署声称实机已验收。


## Bitwig Clip 拖放探测 — 尚未打通

- Bitwig 6.1.4 / Sway / XWayland，独立临时工程、合成 WAV；不需要用户重新录音，未修改 Library。
- 新增手动诊断 `drop_probe [existing-audio-file]`，使用 JUCE `FileDragAndDropTarget`，接受所有文件类型、不打开音频设备。
- 正向对照：探针产生的 WAV 拖入 Bitwig 成功；WAV 拖回探针得到 `DROP`。
- Arrange Clip 标题、Audio Event 波形及标题向独立探针拖出，没有收到文件；拖放中按 B 也未收到文件。
- 这是独立窗口文件载荷测试，不是 Bitwig 内嵌 CLAP GUI 验收，也不能证明其他宿主传递路径不可行。当前不能承诺“直接拖 Clip 即可用”。
- 需要继续验证宿主内插件拖放或宿主桥接；不能把读取原始 sample 文件冒充带裁剪、拉伸、偏移的 Clip。
- 测试工程已丢弃，诊断窗口已关闭，恢复 Library。新插件仍未部署；没有 commit/push。



## 最新：四小节密集网格（本地构建，未部署）

- Rust 14 项测试和 Clippy 通过；量化边界扩展到每拍 8/12/16 格。
- CLAP/Standalone 构建、CTest CLAP、GUI/FFI 全部通过。
- GUI 新测：四小节 64 事件自动分析，MIDI 结束于 15360 ticks（960 PPQ）。
- 1/16、1/32、1/64、两种三连音 × 四／二／一小节视区的坐标与插入位置往返通过。
- 256 个同轨标记逐一命中通过；View grid/Zoom/Pan 不改 pattern；Off 保留非网格时差。
- 非四小节输入明确报错且不覆盖旧 pattern；恢复有效四小节输入后可继续分析。
- 人工检查 `/tmp/beatlab-four-bars/ui.png`：四小节、每小节四拍均可见，无标签重叠。
- 仍未实测密集口技准确率；45 ms 起音间隔限制未变。Sound Set 模板复用、宿主 Clip 直连未完成。
- 新构建未部署、未 commit/push；旧用户插件二进制保持原样。


## 最新：四分类精简版本（本地构建，未部署）

- `cargo test --offline`：3 unit + 11 integration = 14 项通过。
- `cargo clippy --all-targets -- -D warnings` 通过；CLAP/Standalone Release 构建通过。
- 当前 CTest 仅 `clap`：通过。旧 capture 状态机及测试已随录音功能删除。
- GUI/FFI：验证无 Record/Stop/Save Take、四个 MIDI 映射、WAV 拖入自动分析、拒绝 `.bwclip`、
  v1 Review 迁移不误变 D、状态往返、无默认回授、独立 JUCE MIDI 解码；全部通过。
- 新增四种合成音的音频→四类→四个 MIDI note 回归，以及 D 导出/Review 排除与 schema 边界。
- `/tmp/beatlab-v2/ui.png` 已人工检查：四类加 Review、四组映射，无重叠裁切。
- 不足四类不强制分四类；只表示支持最多四种相似声源，不能保证实录口技分类准确。
- **未部署，未重建 Library 试验轨，未完成 Bitwig 工程 Clip 拖入或 MIDI Clip 拖出/写入。**
  输出 MIDI 文件仍只是开发出口，不是用户要求的最终工作流。未 commit/push。

下方保留早期原型的历史验收；录音相关行为不再属于当前源码。

## 已通过

| 层次 | 验证 |
|---|---|
| 独立构建 | 自己的 SHA-256 校验依赖目录；Rust staticlib + JUCE Standalone + CLAP Release 编译 |
| Rust | `cargo test`：2 个 unit tests、8 个 integration tests，全部通过 |
| 静态检查 | `cargo clippy --all-targets -- -D warnings` 通过 |
| 录音状态机 | CTest `capture`：宿主预备、精确长度、停止、跳位、变速、错误拍号、独立时钟 |
| CLAP ABI | CTest `clap`：动态加载、唯一 ID、创建、输入/输出端口、激活、处理、静音输出、销毁 |
| UI/FFI | 离屏构建窗口、触发 Demo、异步分析产生 32 事件、保存恢复 state、拒绝无效 state |
| 音频边界 | 非零输入无默认回授；零声道 buffer 不越界 |
| MIDI 独立解码 | 用 JUCE MidiFile 解析 Rust 导出的文件：32 个 Note On、channel 10、PPQ 960、两小节结束位置 7680 ticks |
| 视觉 | 离屏 PNG 人工检查；灰底、胶囊控件、英文标签、彩色事件/白环，没有明显重叠裁切 |

起音回归是 **12 组采样率/BPM 组合的合成打击信号**（8/44.1/48/96 kHz × 60/120/180 BPM），每组 32 个事件，检测起音误差小于 12 ms。这个数值不是麦克风到 MIDI 的实时延迟，也不是实录口技误差保证。

Rust 另测：静音、非有限采样、非法配置、JSON roundtrip、所有状态字段验证、Review 不导出、同格同音合并、量化边界与循环长度。

## 尚未验收

- Bitwig 真实麦克风录音及宿主录音时钟；目前完成的是 Demo 分析/导出/导入链路。
- REAPER 实机加载。
- 用户真实口技录音的漏检、误检、类别准确率。
- 实际麦克风、电平、节拍器串音及设备重连。
- 包含真实音频的会话持久化、实时 MIDI 输出、DAW Clip 自动写入、MIDI drag-out：**本版未实现**。

CLAP smoke 不是 Bitwig 兼容认证。当前只可称为“已构建并完成自动化验证的原型”。

## Bitwig Library 实机演示 — 2026-10-20

- Bitwig Studio 6.1.4 内加载 Beat Lab CLAP；在原 Library 新增 `beat lab - input` Audio 轨和 `beat lab - drums` Instrument 轨。
- 插件 Demo 产生 120 BPM、4/4、4 小节、64 个事件；通过真实 Export MIDI 对话框导出，拖入 Clip Launcher，循环长度为 4 小节。
- Drum Machine 使用已安装的 `Legend 808 Normal Kit`。该 Kit 不是 GM 布局：A/B/C 设置为 MIDI **36/37/38**，对应其 Kick/Snare/Hi-Hat。插件下拉中的 Snare 等标签只是 GM 提示，不代表宿主实际 Pad 名称。
- 保存并关闭/重开 Library：Clip、鼓组、Beat Lab pattern 和映射恢复成功；原始录音不随插件 state 保存，Hear 需重新 Demo 或导入 WAV。
- 实测输出双声道非零、未削波。最终 WooAudio monitor 的 4 秒采样峰值双声道约 **−28.50 dBFS**；这是数字输出检测，不是人工听感评价。
- Spark GO 当前不在线；发现 Bitwig 之前选择 HDMI，重开后右声道会回到 HDMI。现已通过 Settings → Audio 选择当前在线的 WooAudio，并复测双声道。**未验证 Spark GO 重连自动切换**；既有路由策略写死 out1/out2，而本次端口重建出现 out5/out6，这项仍需专项修复/验收。
- 演示已停播，输入轨为 No input，未给麦克风录音或口技识别准确率作通过结论。原轨/组保留，钢琴音量恢复 −10 dB。

工程：`~/storage/daw/Library/Library.bwproject`。修改前备份：`~/storage/daw/Backups/library-before-beatlab-20261020T180543Z/Library.bwproject`。
演示 MIDI：`~/storage/daw/BeatLab/Examples/library-808-demo.mid`；未重映射的 GM 版本为 `library-demo.mid`。

试听：点击 `beat lab - drums` 的 `beatlab-808-demo` Clip 左侧三角；顶部 Stop 停止。改 Beat Lab 映射后需要重新 Export MIDI 并替换 Clip，**当前不是实时 MIDI/Clip 同步**。不要把 Beat Lab 插到现有吉他或合成器链中，它默认静音直通信号。

## 复跑

除 README 的测试命令外，离屏测试需要有效图形会话，但不会弹出窗口：

```sh
cargo run --offline --manifest-path lib/tools/beatlab/Cargo.toml --example demo -- /tmp/beatlab-demo
lib/tools/beatlab/build/gui_test /tmp/beatlab-demo/demo.json /tmp/beatlab-ui.png
```

下一次实测建议先录两小节清晰分离的“咚 / 啪 / 嘶”，力度相近、不叠音。逐个核对起音和类别，再增加轻重变化、连击与更长片段。不先追求任意口技自动识别。

## 麦克风接通更新

此前的 No input 状态已修复：`beat lab - input` 使用 `beat lab mic` 命名总线、Arm + Auto Monitor，输入来自 SF-558 USB 麦克风。已看到插件输入电平；专用路由规则已部署、断连恢复已测。输入音频仍被插件静音直通，不是返听。未按 Record，真实口技录音/分析仍待用户试用。

## 2026-10-20 新建 Beat Lab 音轨输入复核

用户新建的 `Beat Lab` 是 Audio Track，但输入为 `No input` 且未 Arm。系统 SF-558 麦克风与 `beat lab mic L/R` 的 PipeWire 连接均已存在，无须重建总线。通过 GUI 选择 `beat lab mic` 并 Arm 后，v0.3 插件 Input 从 silent 变为约 −37 至 −31 dBFS；宿主停止时仍收到音频。没有启动录音，也未验证真实口技识别。Library 已保存；修改前磁盘工程备份在 `~/storage/daw/Backups/library-beatlab-input-20261020T195821Z/`。本次未修改插件代码、系统路由或偏好。

## v0.3.1：真实录音漏检修复（2026-10-20）

- 用户 48 kHz、120 BPM、8 秒录音：旧版仅 8 个起音。录音均值约 +0.00812，20% 分位 RMS 约 −43.22 dBFS；旧版 `max(Gate, floor * 3)` 把实际门槛抬到 −33.68 dBFS，因此从 −36 调到 −48 仍为 8 个。
- 分析副本减去全段 DC 均值；原始 PCM、试听、时间索引不变。移除隐藏的全段噪声门槛覆盖，保留既有上升沿/45 ms 最小间距规则。Gate 明确控制 RMS 门槛，并保存到宿主 state（旧 state 默认 −36；越界/错误类型拒绝）。
- 同一原始录音离线对照：Gate −36 / −42 / −45 / −48 分别为 12 / 23 / 33 / 53 个候选；−45 含 1 个 Review。候选增多不等于正确率通过：没有人工标注，不能报告召回率或类别准确率。−48 有更多噪声风险。
- 新增不同采样率的 DC 偏移不变性、低电平 Gate 控制、连续背景不覆盖 Gate、恒定偏移/平稳噪声不产生节奏测试。Rust 17 tests 与 clippy 已通过。真实录音只在 Storage/临时目录，不进入 Git。

实机部署复核：CTest 2/2、GUI/FFI/state/录音回归通过；Gate 保存与非法值拒绝测试通过。已按用户授权重开 Bitwig，Library 中同一段录音在 −45 dB 得到 33 个候选（含 1 个 Review）；保存后直接核对工程内 plugin state，原始 PCM 与修改前完全相同、gate_db = −45、33 个事件均落盘。10 个 Storage 链接核验通过。旧插件/工程/原 WAV 备份：`~/storage/daw/BeatLab/Backups/sparse-fix-20261020T200424Z/`。真实类别和多余/遗漏候选仍待用户试听。

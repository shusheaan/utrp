# Bitwig / UTRP 收尾与文件地图 — 2026-10-18

## 当前权威状态 — 最终收尾 2026-10-18

此前段落是分阶段记录，版本与布局以此为准：Chord Lab **0.2.12**；
Guitar Frontend **0.2.1 单音**；Library controller **0.7**；浮窗中央优先。
偏好已实际迁入 Storage，不再只是时间点快照。见
[实时存储/恢复](../daw_backup/README.cn.md) 与
[本轮最终验证与剩余边界](../../../review/2026-10-18/project-health.cn.md)。

## 以下为历史阶段记录

## 插件浮窗布局 — 2026-10-18

已启用 Sway 插件浮窗自动布局：Chord Lab 靠右，其余从右向左找空位，必要时换行，保留左侧轨道区。只管理当前 Bitwig 外部插件编辑器，不改变音色、内部缩放或音频路由。真实验证 Surge XT Effects、Dragonfly Hall、Surge XT、sfizz；四窗口同屏、关闭重开、手动拖动和焦点保持通过。27 项布局／Library 自动测试通过，strict mypy 通过。配置和使用见 [`plugin_windows/README.cn.md`](../plugin_windows/README.cn.md)。Library 已保存，当前为 Soft Prism 三窗口布局；Spark GO 实弹不属于本轮窗口验收。

## 最新：Ambient Guitar / controller 0.6

新增 **Ambient Guitar** 分组及四条实时吉他效果轨；音频效果与共享的“仅显示”识别支路分离。见[路由、调节方法、文件与验证说明](AMBIENT_GUITAR.cn.md)。此节覆盖下方历史轨道数量：Library 现为 113 轨（含分组与 Master）。

## 最新收尾：Chord Lab 0.2.10 与共享路由确认

本节优先于下方历史版本／设备状态记录；用户已确认界面并完成保存，本次收尾不再操作宿主或修改工程。

- **外围留白**：窗口由 884×683 扩为 920×703，内容画布仍为 884×683；左右边距由 18 增为 36 px，上方由 10 增为 20 px，下方增加 10 px。字体、胶囊、S/A 圆形和图表不缩放。
- **实现位置**：`lib/tools/chordlab/theme.toml` 的 `[editor]`、`generate_theme.py`；`lib/tools/chordlab_clap/editor.cpp` 同步画布、S/A 与错误提示偏移及窗口限制。新增配置校验与尺寸回归，版本为 0.2.10。
- **共享路由**：Library 顶部 `CHORD LAB - shared MIDI input` 轨包含 `Note Receiver → Chord Lab`。Note Receiver 从吉他轨的 Guitar Frontend 取 MIDI，Source FX 将 channel 2 映射为 display-only channel 15；实体 MIDI 与电脑和弦经过同一个共享 Chord Lab，再供当前试听音色使用。不是每个音色轨都装一套检测器／Chord Lab，也不是所有独立实例自动共享输入。
- **吉他用途**：识别音只用于 Chord Lab 高亮，不透传触发钢琴／合成器。吉他原声仍独立；本轮不修改识别算法或路由。
- **验证**：556 项 Python 测试、8 项 CTest、构建件和安装件 CLAP probe 通过。Bitwig 实际窗口为 920×703；对齐画布后，上方图表和调性条（排除 Active 状态）像素与旧版一致，四周新增留白均为 `#585858`。现场验证 S 点击开关，部署后恢复 S Off / A On；Spark GO 输出和 capture→Bitwig in1 连接保持。
- **保存位置**：工程 `/home/shu/storage/daw/Library/Library.bwproject`；共享安装件 `/home/shu/.clap/Chord Lab.clap`。REAPER 重新加载同一路径也使用新版外观，但宿主工程与实例路由各自独立。
- **证据与快照**：`target/editor-padding/` 包含测试日志、截图、旧插件／工程备份，及用户保存后的 `Library-user-saved-wrapup.bwproject` 和 `wrapup.json`。
- **边界**：本轮未重新做全部音色试听、实体 MIDI／真人吉他准确率测试；未执行 Git commit/push，未删除 REAPER 工程。

## 当前更新：吉他只显示，不触发音源（0.2.5）

- MIDI channel 15 保留为 display-only 输入：Note On/Off 更新钢琴、指板和谱面高亮，不向下游发出音符；该通道的 CC、Sustain、bend 等也不透传。
- 实体键盘使用 channel 1–14，电脑控制继续保留 channel 16。吉他与键盘即使同音也独立释放，吉他不会占用或延长音源的发声。
- 不增加开关或参数；21 个参数、稳定 CLAP ID、v3 工程状态格式不变。旧状态可直接读取。
- Guitar Frontend 本身仍输出 channel 2；Library 的 Note Receiver Source FX 将 2→15，再进入共享 Chord Lab。Mutes Input 保持 OFF。
  该映射只作用于接收的吉他，不改变实体键盘的通道和力度。共享插件升级不会自动修改 REAPER 的旧路由；其他宿主需要同样把检测支路映射到 15。
- Spark GO USB 原始输入已接回，吉他轨 Monitor ON、Detect ON，音频推子仍为 −∞，避免与 Spark GO 的直接声音重复；后续 DAW 效果器必须放在检测器之后。

验证：562 项 pytest、6 项 CTest、真实 CLAP probe 全通过；覆盖 128 个显示音高、控制消息隔离、同音混合输入、两模式电脑键释放、失焦及重复 Note On。
证据及部署前备份：`target/chordlab-guitar-display/`。本次不是识别准确率或真实吉他延迟的验收，不声称 100% 音高识别。

部署后 Bitwig 检查：保存、关闭并重开 Library，Source FX 的 2→15 映射保持；Acoustic Piano 为当前试听轨。
向 Bitwig 吉他输入注入 220 Hz 合成音时，共享 Chord Lab 显示 A3，高亮存在且钢琴/主输出电平表无活动；随后电脑 C 和弦键正常产生音源电平，松键后高亮与电平消退。
临时 PipeWire 测试源已退出；Spark GO capture→Bitwig in1 及 Bitwig out1/out2→Spark GO 输出保持连接。
Library 已再次保存，焦点恢复到 Chord Lab。合成音测试不等同真人吉他或实体 MIDI 键盘验收，仍需用户试弹确认听感。

此节覆盖下方历史记录中的吉他 2→1 发声音源路由及硬件未连接状态。

## 2026-10-18 后续：Chord Lab 0.2.0 双 voicing

最新键位改为 **H/L 移动、J Piano、K Guitar**，旧 G/V 不再使用。
新增吉他指型查表、独立位置记忆、模式圆点和指型外圈；主题不变。
[功能、边界与验证记录](../chordlab_clap/GUITAR_VOICING.cn.md)。
本轮不改变 Library 路由、音色或 Guitar Frontend。


[English](WRAPUP.md)

## 后续本轮收尾：Grid 示例、试用重点与最终配色

本节为 2026-10-18 后续更新；下方保留此前迁移总结与历史验收，不表示这次重新跑过全部测试。

- **最终 Dark 配色**：两组钢琴白键均为背景灰 `#323232`，黑键内外均为纯黑 `#000000`。
  此方案替代此前试过的“纯黑白键、灰色黑键”。保留分隔线、外框、音符高亮；
  不改 Bright、谱面、指板、键位或 MIDI 行为。
- **实现与部署**：主题配置 `lib/tools/chordlab/theme.toml`、生成器 `generate_theme.py`、
  生成资源 `theme.jsfx-inc`、键盘绘制 `ui.jsfx-inc`、回归 `tests/test_theme.py`。
  重建并部署 `~/.clap/Chord Lab.clap`，仍为 0.1.10 的资源更新；Bitwig 已重启加载。
  REAPER 下次重新加载同一插件也使用新版，但各实例仍各自保存 Dark / Bright。
- **本次配色验证**：118 项 pytest、4 项 CTest、真实 CLAP probe 通过；
  在 Bitwig 的两个键盘区域检查显示与像素，确认灰白键、纯黑键均已生效。
  证据、旧插件与工程备份：`target/chordlab-gray-white-black-keys/`。
  最终安装件 SHA-256：`ef47c789ad7bba9945d758ae810fcc07b3480114c82b8f9f4ee71ecc98ef210e`。
- **Grid Lab**：保存到 `~/storage/daw/Grid Lab/Grid Lab/Grid Lab.bwproject`，
  基于官方 Essentials 的 Fractal Machine - Divine Radiance 改编，72 BPM、16 小节 C#m7。
  同目录有 `Preview.wav`；不是从零搭建或 Endless 精确复刻，也不是完整随机编曲器。
  已做保存重开与音频输出检查，使用方法和边界见 [Grid Lab 说明](GRID_LAB.cn.md)。
- **30 天验收重点**：先录音 / 多次 take / 重录与保存恢复，再测音色 Remote Controls、
  automation、Grid 高层结构、AI / 脚本 / 自研插件边界。
  [试用验收清单](TRIAL_ACCEPTANCE.cn.md) 已保存；这些待办不是已经通过的测试。
- **收尾状态**：已保存 Library 和 Grid Lab，保留两个工程标签，回到 Library / Chord Lab；
  没有删除 REAPER 工程，没有执行 Git commit 或 push。
  本次没有重新做 98 音色、实体 MIDI 或 Spark GO 真人演奏全量验收。

## 当前结论

- 主工程：`/home/shu/storage/daw/Library/Library.bwproject`，已保存，当前 C# Minor / Chord Lab C#m/E，Acoustic Piano，Sustain OFF、transport stopped。
- 产品版本：Chord Lab CLAP 0.1.10、Guitar Frontend CLAP 0.1.2、Library controller 0.5。
- 两个 DAW 共用安装在 `~/.clap/` 的两个自研插件，但工程、插件实例状态及宿主控制脚本不共享。
- 软件验收通过不等于硬件验收全部完成：Spark GO 当前缺席，真实吉他/实体 MIDI 混合试弹仍待用户配合。原 REAPER 工程保留。

## 本轮累计改动

### Library 迁移与宿主配置

- 原 95 音色完整迁移，保留三个 Ambient Pad，共 98 音色；108 轨含分组、共享输入、吉他与 Master。工程内使用英文命名。
- 95 个原音源状态已比对；Surge 参数、wavetable、调律保留。sfizz 复存可能多一个默认 CC64=0，已作为明确差异记录。
- Basic Keys 的 ReaVerbate 经批准替换成 Bitwig Reverb，并非相同算法；C2-distant 的超范围轨道增益用后级 Tool 补齐。
- Library controller 实现选轨互斥试听与打开音源/共享 Chord Lab 编辑器。正式多轨编曲前关闭 `Exclusive audition + editors`。
- 实测 Poly Grid 加载、打开编辑器与发声；验收用临时轨已删除，没有留下额外测试音符。

### Chord Lab

- Dark/Bright 外观；深灰背景、深色谱面/指板/键盘，加粗分隔线，提亮音符。透明外圆角无法正确实现，最终恢复干净直角。
- Sustain / Keyboard 改为两个红绿圆点；无 Panic 按钮、无顶栏快捷键说明。
- 电脑键位：ZX=6/7、AS=2/3、C=1、DF=4/5；V/G 移动转位，可与和弦键同时按；Space 切换 Sustain；Tab 在三/七/九和弦间循环并记忆。
- 焦点与按键释放保护；Sway 配置 `focus_follows_mouse no`，鼠标仅经过不再换焦点。
- 相对大小调标签如 Am/C、C#m/E；共用 CLAP 内部仍使用 UTRP 的 EEL/JSFX 引擎源码，不再维护独立旧 JSFX 产品。

### 调性联动与吉他路由

- controller 0.5 双向同步 Major、自然 Minor 和五种其他自然调式；插件改调保留宿主模式，宿主改调映射母大调音集。不等于重写 modal 主音/级数引擎。
- Harmonic Minor 等暂停同步；初始化、恢复同步及同批冲突以宿主为准。播放/持音暂缓保护保留。
- 主共享链为 Note Receiver → Chord Lab；接收 Guitar Frontend 输出，Source FX 的 Channel Map 将 ch 2 转到 ch 1，Mutes Input 关闭，保留实体 MIDI 输入。
- 同音混合输入先在 Chord Lab 合并持音所有权，修复松开一路误截断另一路。
- 吉他识别器在效果器前分析原始输入；不能撤销 Spark 硬件已经施加的效果。当前只接受单音实验能力，不支持可靠双音/三音或扫弦。

## 文件放在哪里

`~` 在本机指 `/home/shu`。

| 类别 | 实际路径 | 用途 |
| --- | --- | --- |
| 自研仓库 | `~/work/utrp/` | 源码、配置、测试、说明、原始 FXP |
| Chord 核心 | `lib/tools/chordlab/` | EEL/JSFX 和声、MIDI、谱面、主题源码；内嵌到 CLAP |
| Chord CLAP | `lib/tools/chordlab_clap/` | C++ 包装、GUI、焦点/键盘、状态、构建和测试 |
| Guitar CLAP | `lib/tools/guitar_frontend/` | 单音 DSP、CLAP audio/MIDI/params/state、测试 |
| 多音研究 | `lib/tools/guitar_poly/` | 实验与基准；不是已交付多音识别插件 |
| Bitwig 集成 | `lib/tools/bitwig_library/` | 迁移、状态校验、controller、双向调性和测试 |
| REAPER 集成 | `lib/tools/library/` | 原 REAPER 音色库/启动/迁移工具，保留 |
| 原有音色 | `lib/surge/` | 88 个纳入 Git 的 FXP；不自动随工程内调参更新 |
| Chord 安装件 | `~/.clap/Chord Lab.clap` | REAPER / Bitwig 共用，当前 0.1.10 |
| Guitar 安装件 | `~/.clap/Guitar Frontend.clap` | REAPER / Bitwig 共用，当前 0.1.2 |
| Controller 安装件 | `~/Bitwig Studio/Controller Scripts/UTRP/` | `Library.control.js`、`Library.key-sync.js`、`Library.config.js` |
| Bitwig 程序 | `~/opt/bitwig-studio-6.1.4/opt/bitwig-studio/bitwig-studio` | 当前 native 6.1.4 Trial，安装树约 651 MiB |
| Bitwig 配置/包 | `~/.BitwigStudio/` | 偏好、缓存、日志等；`installed-packages/` 约 7.5 GiB，包含 Essentials 等 |
| Bitwig 用户库 | `~/Bitwig Studio/Library/` | 用户预设/模板，不是我们命名为 Library 的主工程 |
| 主工程目录 | `~/storage/daw/Library/` | 约 37 MiB，含主工程、迁移快照、预设、自动备份 |
| 主工程文件 | `~/storage/daw/Library/Library.bwproject` | 约 2.3 MiB；打开这个，不是 `Library-migration.bwproject` |
| 新增 Pad FXP | `~/storage/daw/Library/Presets/` | Warm Veil、Dark Choir、Silver Haze |
| 钢琴采样 | `~/storage/daw/samples/SalamanderGrandPianoV3_44.1khz16bit/` | 约 1.2 GiB，SFZ、Soft/Retuned 映射和 WAV；两边共用 |
| 原 REAPER 工程 | `~/storage/daw/synth.rpp`、`~/storage/daw/Guitar Lab.rpp` | 保留，不随 Bitwig 改动自动更新 |
| 备份 | `~/storage/daw/Backups/`、`~/storage/daw/Library/auto-backups/` | 迁移前/变更前和宿主自动备份 |
| 构建/证据 | `~/work/utrp/target/` | 约 3.5 GiB，构建依赖、二进制、录音及验收日志；Git 已忽略 |

系统插件：Surge 位于 `/usr/lib/clap/Surge XT.clap`（另有 Effects 与 VST3）；sfizz 位于
`/usr/lib/vst3/sfizz.vst3` 和 `/usr/lib/lv2/sfizz.lv2`。Bitwig 用 VST3 sfizz，REAPER 原工程用 LV2，
并非同一二进制格式，但可共享采样。当前默认 Scala 仍引用
`/usr/lib/lv2/sfizz.lv2/Contents/Resources/DefaultScale.scl`，迁移/卸载 LV2 时不可漏掉这个依赖。

Surge 主题在 `~/.Surge XT/Skins/`，默认 Modern Dark Blue / 125%，另有 Royal 与 Andromeda 九种配色。
sfizz Dark 偏好在 `~/.config/SFZTools/sfizz/settings.xml`。Sway 焦点设置在 `~/.config/sway/config`。
应用入口在 `~/.local/share/applications/`，`utrp-bitwig-library.desktop` 打开正式 Storage 工程。
残留 Flatpak 数据目录不是当前运行安装；本轮没有删除它。

## 工程是否把一切打包

不是。`.bwproject` 保存轨道/分组、路由、MIDI/Clip、automation、设备链及插件保存的状态；
不包含 Bitwig 程序或 CLAP/VST3 插件二进制，也不保证包含第三方插件引用的所有采样。

- Surge 当前参数随项目保存，原始 `.fxp` 是另外的可复用快照；改工程不会自动重写 FXP。
- sfizz 当前设置/路径随状态保存，钢琴 WAV 仍位于外部 Storage 采样库。
- Controller、主题和系统设备路由是项目外依赖。复制单个 `.bwproject` 不等于搬走整套环境。
- 与 REAPER 的 RPP + 外部音频/插件思路类似，但不是相同文件格式，项目不能互换打开。
- Bitwig 的 `File → Collect and Save` 可收集宿主知道的外部媒体；不要当作第三方采样器所有内部文件或插件程序的自动打包器。

参考：[Bitwig Project Panel](https://www.bitwig.com/userguide/latest/the_project_panel/)。

## REAPER 是否也是新版黑色

是同一个安装插件。已只读提取 `synth.rpp` 的真实 Chord 状态，在当前已安装 CLAP 中加载，
状态恢复和默认 Dark 检查均通过。本轮没有启动 REAPER 或改其工程。
重载插件后使用当前版本；若将来某实例明确保存 Bright，它会保持自己的选择。
共享的是代码/插件安装，不是两个工程的调号、和弦记忆、轨道或音色修改。
Bitwig 调性联动依赖专用 controller，不会自动同步 REAPER 顶栏。

## 验收与剩余边界

收尾重新执行：198 项 Python、Chord 4 项 CTest、Guitar 2 项 CTest 全通过；
已安装 Chord 的独立 X11/CLAP probe、已安装 Guitar 的 host probe、原 RPP 状态兼容 probe 均通过。
最初 `xvfb-run` 不存在，未安装新软件；改用现有 XWayland DISPLAY 验证通过。
两份 CLAP 与对应构建产物逐字节一致；三个 controller 安装文件与源码一致；原 RPP 哈希不变。
两个主 SFZ 各 641 个采样引用与 SoftPiano include 均存在，无缺失。

本轮前序实测：98/98 音色路由发声及重开后的 98/98；8 个合成吉他音高、混合持音释放、
键盘/焦点、Grid、双向调性均有记录。收尾没有重新演奏全部 98 音色。
当前 Keystation 在系统列表，Spark GO 不在；吉他轨仍 No input / Monitor OFF。
当前 HDMI 输出不代表 Spark GO 监听已验收。真实吉他的音高/延迟/噪声与实际键盘混合输入仍待试弹。
此前日志出现过 Surge bus activation 提示与 sfizz/X11 退出问题；发声通过不等于已排除所有宿主边界故障。
测试探针端口 19671 已关闭，没有留后台控制监听。

证据：`target/session-wrapup/`、`target/bitwig-diatonic-sync/`、`target/bitwig-guitar-grid/`、`target/bitwig-migration/`。

## Git 与备份原则

- Storage 在 UTRP 仓库之外：主工程、WAV、自动备份不会被该仓库提交。`target/` 已忽略。
- 自研源码在 UTRP，但当前有大量未提交/未跟踪变更；**放在仓库目录不等于已进入 Git 历史或远端备份**。本轮未提交、未推送。
- 安装目录是运行副本，不是源码维护入口。改 UTRP → 测试/构建 → 部署 → DAW 重载。
- 建议分别备份源码、`storage/daw/`、安装/配置清单；不要仅备份 `.bwproject`。

### 插件跨乐器复验补充

实测 6 种 Basic Keys、3 种 Pad、4 种 Ambient Guitar 共 13 组窗口；检查浮动、边界、两两间距与主窗口尺寸。发现并修复大音源后开时被小 FX 切碎空位而误报溢出的情况；新增 340 种打开顺序回归，修复前 20 个失败，修复后全部通过。当前总测试 368 passed，strict mypy 通过。跨轨混合五窗口是实测尺寸的计算测试，非互斥试听下的真实同时开窗。证据在 `target/plugin-window-combinations/`。

另修复 Surge XT Effects 跨轨重开偶发保留巨型尺寸：只对 FX 在新开窗／超大时恢复 600×490，不调整 Surge XT 音源。


## 2026-10-18：中央浮窗与踏板默认延音（0.2.11）

本节更新前述历史状态：Library 已备份、保存并重新打开，安装的 Chord Lab 为 0.2.11；当前恢复到 Acoustic Piano，Bitwig 左右输出连接 Spark GO。电脑 C 和弦独立录取 Bitwig 输出，peak 0.3421、RMS 0.02354，确认有声。没有重新遍历全部音色，也未把模拟 MIDI 当作真人踏板验证。

- S 表示不踩踏板时的默认延音：红色时踩下延音，绿色时踩下临时取消延音，松开恢复；Space／点击 S 改默认，踏板不改变 S 颜色。仍按住的琴键不被静音。沿用失焦清理默认 S 的规则。标准 CC64 阈值 64；物理极性须正确，重载后先松开再踩。
- `chordlab/midi.jsfx-inc` 与引擎内存新增逐通道踏板状态；CLAP tooltip、二进制 probe、`sustain_tests.cpp`、双语混合输入说明同步更新。安装文件为 `~/.clap/Chord Lab.clap`。
- Library controller 0.7：选音色打开共享 Chord Lab 与主音源／首个吉他 FX；带本地 Chord 的辅助轨打开本地实例。关闭前一组已知编辑器，不改变辅助轨音频路由。管理前四个顶层设备，不承诺任意嵌套设备；关闭当前轨全部窗口后，选另一轨再回来可重新打开。
- 浮窗改为中央优先：单 Chord 居中，Chord 与主插件成组居中，其他 FX 向右及周围空位放置。窗口服务与 controller 已部署。实机检查钢琴、Surge、原始吉他单窗、Soft Prism 三窗及 Cloud Halo 四窗，均浮动、不重叠、不越界。
- 验证：926 项 pytest、9 项 CTest、已安装 CLAP probe 全通过，布局 strict mypy 通过。证据：`target/pedal-baseline/`、`target/plugin-windows-center/`。最终工程仍在 `/home/shu/storage/daw/Library/Library.bwproject`，运行副本与备份不进入 Git；未提交或推送。
- 待用户验证：实体踏板两种默认状态的真实踩放效果。本轮吉他输入仍显示 missing，未声称真实吉他输入已验收；Spark GO 输出正常不等于吉他输入映射正常。

### Keystation Transport 后续配置

已捕获用户真实八键，确认 Mackie/channel 1；新增独立 `Keystation.control.js` + `.config.js` 并安装，Bitwig 显示 ready。原 Generic 演奏输入保留，Volume CC 设 7、Catch 接管；新脚本只接 Transport，不创建音符输入。播放/停止/录音、上下换轨、左右移动一小节、中央回头，录音使能时保护导航。无关自动发现的 Spark GO Generic MIDI controller 已移除，不改其音频输出。927 pytest、9 CTest、已安装 CLAP 新增 CC1/7/11 与 bend 透传 probe 通过；尚待用户实机操作反馈，正式 Library 未创建录音测试 take。详情及证据见 [KEYSTATION.cn.md](KEYSTATION.cn.md) 与 `target/keystation-controls/`。


### Spark GO 吉他输入恢复

Bitwig 错选 GB203 HDMI 导致没有 capture；已改回 Spark GO USB，恢复 mono 输入与立体声输出，检查原始识别轨及共享 Note Receiver，保存 Library 并恢复 Glass Air。共享显示路由与四条 FX 配方未改。关硬件直通后的真实试弹结果仍待用户确认。详情见 [AMBIENT_GUITAR.cn.md](AMBIENT_GUITAR.cn.md) 末节，证据在 `target/guitar-routing-restore/`。


### 踏板保持模式排查（2026-10-18，等待新版重载）

真实 CC64 采样确认踏板极性反向：踩下 0／松开 127。用户脚松开重启 Keystation 后，捕获踩下 127／松开 0；Generic 演奏输入已恢复，当前 Acoustic Piano。另修复 CLAP 失焦清掉 S 默认延音的问题，源码及构建版为 0.2.12，947 pytest、9 CTest、新二进制 probe 通过。**当前已安装／运行仍为 0.2.11**，等待用户确认保存并重开后再部署；真实双模式听感仍需试弹。证据：`target/pedal-hold-check/`。没有硬编码反向踏板映射，不修改吉他／效果器路由。


### 踏板修正版最终部署（0.2.12，已完成保存与重开）

本节替代上节“等待新版重载”的状态：用户已同意，Library 已备份保存，正常退出 Bitwig 后原子安装 `~/.clap/Chord Lab.clap` 0.2.12，再重开工程。安装副本完整 CLAP probe 通过，SHA-256 为 `5c02efab99369a046691df44c3d22a84d707da13f6c8976c4d258a9e39ba42d3`。

- 实机验证：S 设为绿后，点击宿主使 A 变红，S 仍保持绿；回到插件按 Space，S 正常变红。保留现有踏板 momentary XOR 行为，不改 CC64 极性。
- Keystation 演奏与 Transport 两个端口均重新打开；Spark GO 的 mono 输入连至 Bitwig `in1`，`out1/out2` 回放至 Spark GO。重启后端口编号从 out3/out4 回到 out1/out2 属于重新分配。
- 最终恢复 `01 Acoustic Piano`、S 关闭、Chord Lab 已聚焦、宿主停止。工程保存于 `/home/shu/storage/daw/Library/Library.bwproject`。
- 947 pytest、9 CTest、构建及安装副本 probe 通过；新版真实宿主的失焦／Space 操作已复验。实体踏板双模式听感留给用户试弹，没有重验全部音色或宣称全部硬件听感验收。
- 主要修改：`chordlab/midi.jsfx-inc` 分离电脑按键释放与延音重置；`chordlab_clap/sustain_tests.cpp`、`clap_probe.cpp` 增加失焦与长按回归；CMake 版本 0.2.12，双语说明同步。源码未提交或推送；工程与运行备份不进 Git。
- 本轮备份、安装哈希、前后 CC64、截图与最终验收记录：`target/pedal-hold-check/`。旧二进制仅保留作回退备份，不是并行使用的产品版本。

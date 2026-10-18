# Synth Library — 单音色试听工程

> **2026-10-17：已切换为 CLAP 单产品路线。以下 JSFX/VKB 说明属于历史实现，不再是日常操作方式。当前使用见 [CLAP 迁移指南](CLAP_MIGRATION.cn.md)。

当前：95 条音色轨共用一个 Chord Lab 输入，其中 93 条 Surge、2 条 sfizz。
保留原来的 89 条 Surge 音色，新增 6 条基础键盘音色。不是多层叠加演奏器。

## Basic Keys（最前面的音色组）

共享输入轨仍在第一轨，其后是 `Basic Keys - 基础键盘` 文件夹：

| 轨道 | 音源与来源 |
| --- | --- |
| 01 Acoustic Piano | sfizz + Alexander Holm 的 Salamander Grand Piano V3 |
| 02 Soft Piano | 相同采样，加 3800 Hz 二阶低通；不是独立钢琴录音 |
| 03 Suitcase EP | Surge Factory / Keys / Soft Suitcase |
| 04 DX EP | Surge Factory / Keys / DX EP |
| 05 Organ | Surge Factory / Keys / Organ 1 |
| 06 Church Organ | Surge Factory / Keys / Church |

钢琴使用 [FreePats 原始采样包](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html)，
44.1 kHz / 16 bit，作者 Alexander Holm，CC-BY-3.0；安装于
`~/storage/daw/samples/SalamanderGrandPianoV3_44.1khz16bit/`，原 README 和署名保留。
`SoftPiano.sfz` 用 include 引用原映射，不修改原始采样。大采样文件不放进 Git。

`01 Acoustic Piano` 标记 `P_EXT:utrp_library_default=1`。
默认启动入口运行 `Start library.lua` 时，无论上次选了什么，都先激活并选中钢琴。
重复运行 Start 不打断正在进行的试听；没有默认标记的旧工程维持原行为。
直接打开 RPP 而未运行启动脚本时，遵循工程保存的状态。
选 sfizz 轨时显示 sfizz，选 Surge 轨时显示 Surge；都复用同一个 Chord Lab。
音源离线时不能用 `TrackFX_GetInstrument` 判断类型，须读取保存的 FX 名称。

- `Crying in a Loop`：3 个音色（01、02、03）。

## 文件边界

- `../../surge/`：公共 FXP 源；二进制容器，含参数 XML，有些含 wavetable。
- `~/storage/daw/synth.rpp`：日常编辑工程；保存各轨 Surge 状态、路由、Chord Lab 记忆。
- 本目录：只负责一次性迁移和 REAPER 内的试听路由，不实现和弦、键盘或音符绘制。
- `../chordlab/`：独立 JSFX + 输入会话。这里只在固定公共输入轨启动它。
- `library.toml`：迁移配置。生成器拒绝覆盖已有 `synth.rpp`，日常不要重新生成。

## 日常使用

运行 `Start library.lua` 启动；重复运行不会关闭会话。
启动时仅建立 MIDI 监听与试听路由，不主动打开 Chord Lab 或 Surge；工程保存的窗口状态由 REAPER 恢复。
**选中另一条音色轨即可切换试听，并同时打开该轨音源与共享 Chord Lab**，并打开原生 VKB。
切到文件夹／公共输入轨后再选回当前音色，也会重新打开编辑器，但不重新加载音色。
只响应选中轨道的变化：手动关窗后不会被轮询立即打开；重复点击已选中的同一轨不算新的选择。
所有音色轨共用输入，不逐轨复制 Chord Lab。点击专辑文件夹或公共输入轨不切音色。

- **Chord Lab**：选中音色轨时自动显示，也可从 `CHORD LAB - shared MIDI input` 轨的 **Input FX** 打开；同时打开原生 VKB。
- **Surge**：选中音色轨时自动显示，也可从音色轨的普通 **FX** 单独打开／关闭；手动开关 Surge 不带动 Chord Lab 或 VKB。
- **显示与处理独立**：关闭编辑器不是 bypass。隐藏 Chord Lab 后 Input FX、arm／monitor 和实体 MIDI 通路保持运行；隐藏编辑器只到期释放鼠标持音；电脑输入仍由打开的 VKB 提供，关闭 VKB 才停止电脑控制。
- 插件是否处理由各自 FX 的启用／bypass 控制；重新打开 Chord Lab 不会自动取消 bypass。
- 音色切换关闭旧音源浮窗并将旧实例离线，再加载新实例；选轨时打开新音源与共享 Chord Lab。Surge 和 sfizz 使用同一路由，保持单个音色在线，不改其保存参数。
- VKB 随打开 Chord Lab／选中音色轨显示，也可通过 **View → Virtual MIDI Keyboard** 手动开关。手动关闭后稳定轮询不强制重开；隐藏 Chord Lab 不关闭 VKB，关闭 VKB 也不隐藏 Chord Lab。

点击某条音色轨的 **Solo** 也可以切换，管理器自动取消上一个 Solo：只保持当前音源在线、
只把公共 MIDI 发给它，其余音源离线但状态仍保存在 RPP 中。仅改变 Solo、不改变选中轨道时，不自动打开编辑器。
不选任何 Solo 就没有 synth 发声。不要 Solo 专辑文件夹，不要额外 arm synth 轨。

先松开琴键再换轨／音色。离线切换会切断旧音色尾音，不支持跨音色连续长音。
同一音色内调 cutoff 等连续参数不需要离线，和切换整个 preset 是两回事。

电脑 A–J 在 Chord Lab／VKB 获得输入时按住发声。**当前不能把电脑键当作可靠的
跨窗口 MIDI 键盘**：实测按住和弦后拖动 Surge 参数有持续输出，但在 Surge 内松键
会丢失 Note Off，出现挂音；不只是拖动期间不能换和弦。电脑演奏与 Surge 编辑先分开操作，
松键后再进入 Surge；异常挂音用 REAPER 的 All notes off。
普通 MIDI 消息持音并拖动参数已测到持续输出；实体 MIDI 不依赖窗口焦点，
但真实设备需连接后验收，不能拿软件注入代替硬件验收。
MIDI 设备使用 channel 1–15，channel 16 留给电脑控制。

### 本机窗口布局

布局规则独立放在 `~/work/gral/arch/sway/config`，不进入 MIDI／和声代码。
当前 3440×1440 屏幕：左侧 Chord Lab `(560, 282)`，大小 `884×712`；
下接原生 VKB `(560, 994)`、大小 `884×163`，右侧 Surge `(1444, 282)`、大小 `1359×875`。
三窗边缘直接相接，横向与纵向间隙均为 **0 px**。左侧组合和右侧均高 **875 px**，顶底对齐、垂直居中（上下空隙 282／283 px）。
Surge 使用原生约 150% 等比例缩放，当前实际 149% 已保存为默认。
Sway 每次打开 Surge 浮窗时指定 `1359×875`，插件内容随宿主尺寸真实等比例缩放，
避免旧实例保留较小 Zoom；不只扩大空白外框，也不批量改写 89 条轨的音色状态。
Chord Lab 无内部标题行；两套音阶／和弦图同步略压缩，再给 VKB 增加 24 px。
上下谱表各高 270 px，钢琴／吉他各 129 px，仍为 50/50。
VKB 随选轨／打开 Chord Lab 显示，与 Chord Lab 同宽，琴键不再压到极薄。
保留左侧轨道和顶部空间；REAPER `reaper.ini` 的 `dockheight=280` 将混音台留在底部。
规则只决定新窗口初始位置，之后可以自由拖动，不使用常驻布局服务。
更新同名 `for_window` 规则后需 reload Sway；仅运行同名规则不能可靠替换旧缓存。
原生 VKB 图示不是实际和弦输出，以 Chord Lab 为准。
更换屏幕分辨率时需要调整这些桌面坐标；不为此增加常驻布局服务。

- `Ctrl+S` 保存当前 RPP：记录轨道音色与效果设置，不会自动更新原 FXP。
- 要加入公共音色库：在 Surge 另存有描述名称的 FXP 到相应 `lib/surge/<album>/`。
- 停止模式：运行 `Library mode.lua`；它也请求停止所属 Chord Lab 会话。
- 切到别的工程时自动结束会话；回到本工程再运行 Start。
- 工程关闭再打开不自动恢复 Lua，默认 REAPER 启动入口另外运行 Start。

## 验证与保护

```sh
python -m pytest -q lib/tools/library/test_*.py lib/tools/chordlab/tests/test_theme.py
luac -p 'lib/tools/library/Library mode.lua'
lua lib/tools/library/test_mode.lua
lua lib/tools/library/test_start.lua
```

`host_audit.lua` 只允许 `/tmp/` 工程副本，且必须先启动 Library mode。
它顺序选中全部音色轨，分别注入电脑控制通道和普通 MIDI Note On/Off，
测轨道输出峰值，断言只有一个在线 Surge／Solo／armed 输入，且选轨打开目标 Surge、共享 Chord Lab 和 VKB，只保留一个 Surge 浮窗，并导出 CLAP 状态。
测试脚本会显式打开共享 Chord Lab 和 VKB，并关闭副本中的 Surge 浮窗以建立检查基线；结束恢复原 VKB 可见性。
运行前创建 `/tmp/synth-build-stage/` 作为状态导出目录；重新运行前移走旧的
`/tmp/library-audio-done.txt`，避免外部监测器误认完成。
不会主观评价音色，也不能代替实际电脑按键或 USB MIDI 验收。
测试时 master volume 临时归零，完成／退出恢复。报告写 `/tmp/library-*.tsv` 等。

初次全在线压力测试曾在 Surge 音频线程崩溃，不能声称确切原因已定位。
单在线是资源控制及隔离策略，不等于已证明修复 Surge 内部 bug。
不要在生产工程运行一次性 builder 或压力测试。完整检查结果见本目录 `VALIDATION.md`。

### 宿主 tuning 状态保护

`audit_state.py` 分别检查 patch 参数、wavetable 和 populated `dawExtraState` 的 tuning 冲突；
用户主动精调的 patch 与原 FXP 不同是预期现象，需要人工核对，不应自动重置。
Surge 1.3.4 打开 GUI 会用宿主 tuning 模式覆盖 patch 模式，宿主状态不能全部视为纯界面数据。

`align_tuning.py` 只把宿主 tuning 模式对齐到当前 patch 的模式，保留其余参数与二进制数据：

```sh
python -m lib.tools.library.align_tuning /path/to/saved-backup.rpp /path/to/new-copy.rpp
```

它拒绝覆盖目标，不直接修改源工程。应用流程必须先保存当前 RAM 编辑、正常关闭工程、
备份最新 RPP，验证新副本后再替换并重开；不能用早先候选覆盖最新编辑。
本机已按此流程完成 72 处字段修正，详情与回滚副本见 `VALIDATION.md`。

### Basic Keys 共用混响（2026-10-16）

本机工程的 `Basic Keys - 基础键盘` 文件夹普通 FX 已加入一个 ReaVerbate；六条子轨经原有 parent send 共用，不加到 Chord Lab MIDI 输入轨或 Master，也不影响其他组。文件夹轨高 160 px，轨道面板直接显示 `Wet`（混响量）与 `Room size`（空间大小）两个旋钮；更详细的设置点该文件夹的 FX。

初始值：Wet -18 dB、Dry 0 dB、Room size 70、Dampening 50、Delay 20 ms；插件启用。平时主要调 Wet，Dry 保持 0 dB；插件 wrapper 的 Wet 保持 100%，不要与混响本身的 Wet 混淆。音源内原有 FX 未修改，因此若某个 Surge 音色自身已有混响，会与文件夹混响叠加。设置随用户保存 `.rpp` 保留，不修改源 FXP，也没有修改一次性 builder。

### MIDI 键盘断电／重连后无声

本机曾出现 Linux 与 PipeWire 已识别 Keystation，但 `Keystation (USB MIDI) (capture) → REAPER:MIDI Input 2` 连接丢失的情况。REAPER 菜单 `Actions → Show action list` 搜索并执行 `Reset all MIDI devices`，或在 `Preferences → Audio → MIDI Inputs/MIDI Devices` 执行同名重置。此操作关闭再打开 MIDI 设备，不是恢复工程／音色默认设置；应先松键并停止录音。若系统根本看不到设备，则先检查 USB 连接，不能靠 REAPER 重置解决。

2026-10-16 现场：执行 `midi_reinit()` 后 PipeWire 连接恢复，REAPER 收到 device 65 的新 Note On/Off；未注入测试音符、未重启 managers、未改音量或工程路由。检查记录在 `/tmp/utrp-midi-reconnect/`。这次恢复不代表已经实现断电后的自动重连。

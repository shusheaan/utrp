# Bitwig Library：吉他路由与 Grid 验收

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

[English](GUITAR_GRID_ACCEPTANCE.md) · [Library 指南](README.cn.md)

## 范围与状态（2026-10-18）

用户明确要求跳过实际录音，先无人值守完成软件检查。因此，以下自动化结果不等于
真人弹奏验收，也不证明真实吉他的识别准确率或端到端延迟。

- 正式工程：`~/storage/daw/Library/Library.bwproject`。
- 宿主：native Bitwig Studio 6.1.4，当前为 Trial。
- 共享插件：Chord Lab 0.1.10、Guitar Frontend 0.1.2；本轮不改 CLAP binary。
- Library controller 升为 0.4，支持共享 Chord Lab 前置 Note Receiver。
- 本轮前备份与证据：`target/bitwig-guitar-grid/`。
- 原 `~/storage/daw/synth.rpp` 保留，不删除、不修改。

## 实际路由

```text
Keystation / All ins ──────────────────────┐
                                         v
GUITAR - raw detection               Note Receiver → shared Chord Lab
  raw mono audio                       ^                   |
  → Guitar Frontend (MIDI ch 2) ────────┘                   v
  → local Chord Lab (optional display)             selected sound → Master

Note Receiver Source FX: Channel Map, ch 2 → ch 1
Note Receiver Mutes Input: OFF
Computer keyboard → focused shared Chord Lab editor
```

Note Receiver 的 Source 取自 **Guitar Frontend 的输出**，不是 local Chord Lab 后面。
Channel Map 在 Note Receiver 的 **Source FX 内部**，不改实体键盘的输入路径和力度。
主共享设备链只有 `Note Receiver → Chord Lab`。

### 为什么必须有 Channel Map

实际交叉测试发现：吉他 ch 2 与电脑和弦 ch 1 同音时，目标乐器轨的 All→1 转换会在
Chord Lab 之后合并通道，造成其中一路 Note Off 截断另一路。只测试不同音高找不到此问题。

现在先把接收来的吉他 ch 2 转到 ch 1，再进入共享 Chord Lab 的持有者合并逻辑。
同音不重复触发，先释放任一来源都不会截断另一来源，最后一个来源释放才结束。
重叠音沿用最初 Note On 的力度，不是后来的每次输入都重触发包络。

### 原始吉他信号与效果器

Guitar Frontend 必须保持在吉他音频链首位；之后再放 reverb、chorus、amp 等效果。
检测不会经过后面的效果器。Spark GO 内部已经加入的失真/混响不能由软件自动还原为干声，
因此硬件端也应使用尽量干净的预设。

当前 Spark GO 不在系统设备列表中，吉他轨保留 **No input / Monitor OFF / fader −∞**，
没有擅自把电脑麦克风当作吉他输入。检测生成的 MIDI 通过 Note Receiver 单独送出。
接回硬件后仍须选择正确 mono input、开启该轨监听，验证干声电平；不是接上线就已验收。
如需同时监听吉他音频，再单独配置其音量/后级效果，避免未经校准的直通爆音。

## 自动验收方法与证据

1. **音色路由**：98 个音色逐一选择，由 shared track 输入 MIDI 60、velocity 80；检查
   目标音源有音频、仅目标音色启用、录音准备和 Monitor ON。
   `all-sound-routing.json` 为首次完整矩阵；保存重开后的矩阵另存
   `all-sound-routing-reopened.json`，以该文件的最终计数为准。
2. **合成音频端到端**：临时 Test Tone → Guitar Frontend → Note Receiver/Channel Map →
   shared Chord Lab → Acoustic Piano。E2/A2/D3/G3/A3/D4/A4/E5 八项均收到精确 MIDI
   pitch、velocity 90 且音源有音频。`bitwig-synthetic-pitch.json` 是 Channel Map 修复后结果。
3. **检测开关与混合输入**：Detect OFF 停止输出，ON 恢复；电脑和弦与不同吉他音并存；
   同音 E3 的两种先后释放顺序均保持正确，最后完全释放。
   见 `detector-*.json`、`mixed-*.json`、`same-pitch-fixed-*.json`。
4. **电脑键盘**：持 C 时 G 前移、V 返回，松键无残留 Note On；Space 指示灯从红变绿、
   再从绿变红。见 `live-keyboard.json` 与 `sustain-on/off.png`。
5. **调性联动**：插件 Q → A Minor；宿主选择 C# Minor → 插件 C#m/E。最终恢复 C# Minor。
   见 `key-sync-*.png/json`。仅联动主共享实例，不含 local guitar display。
6. **Grid**：临时 `TEST - Grid` 轨实际加载 Poly Grid，MIDI 60 触发音频（VU 9147/16384），
   模块编辑器可打开。见 `grid-loaded.json/png`、`grid-editor.png`。这不是完成了 ambient patch。
7. **软件回归**：134 项 pytest、Chord Lab 4/4 CTest、Guitar 2/2 CTest 与 2/2 UBSan；
   installed CLAP 的 host probes 另覆盖 metadata、state、reset、边界与 MIDI 行为。
8. **保存恢复**：保存、关闭、重开工程；检查共享链、Source FX 的 2→1、Mutes Input OFF
   和共享 MIDI→钢琴发声。与修改前工程比较的 95 个 Surge 状态条目和 2 个 sfizz 状态条目
   字节不变；这是去重后的状态文件数，不是音色轨数。共享 Chord Lab 状态文件可重新编号。

### 测试解释，避免误判

- `playingNotes()` 表示 Note On/Off，不表示 CC64 延续的真实尾音；Sustain 验收不能要求
  松键后 playingNotes 仍非空。
- Bitwig 的 direct-parameter observer 在本轮未实时更新插件只读 meter/Sustain 状态。
  不以这些缓存值判定识别失败；实际收到的音高、音源音频和插件指示灯另行验证。
- 最初含错误断言的测试保留在 `initial-*-harness-*.json` 等文件中；它们不是最终通过记录。
- 使用软件合成纯音不是普通吉他的泛音/杂音/滑音测试；本轮不声称支持双音、三音或扫弦。
- 发声证据是宿主音频电平，不是人工听感评价。开始测试时断开了扬声器连线，但工程重开后
  发现右输出从 `out2` 重建为 `out3` 并自动接回，故不能声称整轮始终静音。
  最终按实际端口恢复 `out1 → FL`、`out3 → FR`；以后无人值守测试应使用独立静音输出，
  不能仅依赖一次性的 PipeWire 断链。
- Surge 切换时宿主日志仍有 `failed to activate audio ... bus`；对应音色的实际输出测试
  通过，不能据此声称日志零错误。保留 `engine-log-tail.txt`，未擅自升级/替换共用 Surge。
  临时 TCP probe 关闭短连接产生的 EOFException 另记在 controller 日志，不当作音源崩溃。

## 日常使用与后续实测

最终收尾：保存重开后 **98/98** 音色再次通过；`Test Tone`、`TEST - Grid` 和临时
`Library Probe` 已移除，测试端口 19671 关闭，无测试 clip、无残留 Note On、播放停止。
恢复 Acoustic Piano、C# Minor、Sustain OFF 及原输出设备，电脑键盘焦点留在 Chord Lab。
机器可读汇总：`target/bitwig-guitar-grid/acceptance.json`。未在无人值守时录入真人声音。

1. 打开 Library，点击一个音色轨；控制器只让该音色启用，并打开音源及共享 Chord Lab。
2. 实体 MIDI 输入不需要 Chord Lab 焦点；电脑和弦需点击插件，右侧 Keyboard 小圆点变绿。
3. G/V 可与和弦键一起用；Space 是 Sustain，分号恢复默认转位。插件有焦点时 Space 不是播放键。
4. 吉他接回后，先验证单音的准确八度、起音/停音和真实延迟，再讨论多音识别。
5. 指板显示相同 MIDI 音高的全部可弹位置，不能推断你实际用了哪根弦、哪个品位。
6. 当前是单音色试听工作流。正式多轨编曲前，在 Controllers 关闭 `Exclusive audition + editors`。

待真人完成：Spark GO 重连/干声输入、实体 Keystation 按键、实际吉他高低把位、重复音、
快速换音、杂音误检与手感延迟。不把这些标为通过。

## The Grid 是否需要下载

Grid 是 Bitwig 原生设备；本机当前 Trial 已实际加载，不需要另装 VST/CLAP。
Poly Grid 做乐器，FX Grid 做音频处理，Note Grid 做音符生成/处理。
这是不同设备用途，不是三个外部插件包。Essentials 内容包也不等于 Essentials 授权版本。
试用结束后需核对授权是否包含 Grid，不把当前 Trial 能力当成旧 16-Track 授权能力。
参考：[Bitwig 官方 Grid 设备说明](https://www.bitwig.com/userguide/latest/the_grid_devices/)。

建议下一次从 Poly Grid 的 oscillator → envelope → output 开始，再加 filter、慢 LFO、
random 与 scale quantization，逐步做 ambient；先不在 Library 中留下未经验收的大型实验 patch。

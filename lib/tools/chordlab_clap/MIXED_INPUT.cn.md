# Chord Lab 混合输入与日常使用

[English](MIXED_INPUT.md) · [主说明](README.cn.md)

## 推荐的 REAPER 路由

练习、即兴并准备录入实际弹奏音符时：

`Keystation USB MIDI → 轨道 Input FX: Chord Lab CLAP → 普通 FX: Surge/钢琴 → Reverb`

电脑键盘的输入由 CLAP 编辑器直接送进同一个引擎，不需要 REAPER VKB。
不要在同一条链再串联旧 Chord Lab JSFX，也不要同时开启旧 Lua/VKB 的键盘捕获。
正式 synth.rpp 已迁移为唯一共享 CLAP 输入轨，详见[音色库指南](../library/CLAP_MIGRATION.cn.md)。

1. Preferences → Audio → MIDI Devices：启用 `Keystation 61 MK3 (USB MIDI)` 演奏输入，
   不要误选 `(Transport)`。单纯弹琴不需要将音符启用为 action/control messages。
2. 轨道 Input 选该设备的 MIDI，All channels；实体琴通常使用 channel 1。
   channels 1–15 为演奏通道，channel 16 是 Chord Lab 内部控制协议，不能用于普通弹奏。
3. 开启轨道录音准备和 Input monitoring。只让目标乐器轨监听，避免多个轨同时发声。
4. 将一个 Chord Lab CLAP 放在 Input FX；乐器及混响留在普通 FX。
5. 点击 Chord Lab 内容，顶部 `Keyboard` 绿色且编辑器有焦点 时弹电脑和弦；同时可以弹实体琴。
6. 要录制时，先用鼠标点 REAPER Record，再点击插件并演奏。启用且有焦点时会消费 Space 等
   无修饰键，不能同时把它当作 DAW 的播放键。停止前先松开电脑和弦键，再点 DAW Stop。
7. 保存工程，轨道上的插件与路由会保留；再次打开仍需轨道录音准备/监听和正确设备输入。

Input FX **不是必须位置，也不是永久开启的系统输入服务**。普通 FX 放在乐器前也能
实时演奏。本轮实录确认：Input FX 的生成和弦与实体式 MIDI 音符进入 MIDI item；普通
Record input 不会自动录下普通 FX 的生成结果。若使用普通 FX，需要另选录制输出路由。

Input FX 主要处理实时录入路径，已有 MIDI item 的回放不经过它，所以不能期待 Input FX
里的图随所有时间线回放同步高亮。若需要练习回放可视化，使用普通 FX 的放置方式；不要
为了显示而不加区分地复制两套控制器串联。录制方式与回放显示是两项需求。

## 焦点：电脑键盘与实体 MIDI 分开理解

| 状态 | 电脑键盘 | 实体 MIDI |
| --- | --- | --- |
| 编辑器启用且有焦点 | 控制和弦/转位/类型/Sustain | 正常接收，无须单独切模式 |
| 编辑器失焦（Keyboard 变红） | 不接管新按键，释放电脑持音 | 只要轨道处理仍运行，就继续接收 |
| 红色 Keyboard | 不接管电脑按键 | 仍是 MIDI 处理器，不是插件 bypass |
| 关闭编辑器 | 清理电脑持音及 Sustain lock | 插件留在链上，仍可接收，界面不可见 |
| 轨道未监听、插件 bypass/offline | 不应期待实时输出 | 不应期待经过插件实时输出 |

所以，**弹实体琴可以去调 Surge，不必保持 Chord Lab 焦点；弹电脑和弦时需要焦点。**
若要一边按住电脑和弦、一边点击其他窗口调音，当前安全策略会释放电脑和弦。
Sustain 锁定可能保留乐器尾音，但不是一个独立的 chord latch 功能。不要把它当全局键盘钩子。
系统或宿主 global 快捷键仍可能优先于插件。

## 灰色点是什么意思

灰色不是“输入来源为硬件”的颜色，而是**该音在当前图的音阶/和弦之外**：

| C 调、下方选择 CM7 时，实体琴按音 | 上方：C 大调音阶 | 下方：CM7 和弦 |
| --- | --- | --- |
| C、E、G、B | 对应音阶彩色高亮 | 对应和弦彩色高亮 |
| D | 音阶彩色高亮 | 灰色 |
| F♯ | 灰色 | 灰色 |

谱表、钢琴和吉他图使用同一规则。松开外部非成员音后灰点消失；成员音回到淡色提示。
界面显示的是 MIDI 按住状态，不是声波检测，也不追踪 Sustain/reverb 的真实尾音。
它不会因为你弹了另一个音就自动改选和弦、重做和弦识别。

显示有音域边界：键盘图为 MIDI 38–86（D2–D6）；谱表与吉他也各有可见范围。
超出图示范围仍可输出 MIDI，不能用“该处没点”判断硬件无输入。

## 同一个音，两边一起按

同一 MIDI channel 1、同一 pitch 采用持有者合并：

- 电脑和弦与实体琴重合时，新的按键会以 Note Off → Note On 重新触发；先松其中一边，不截断另一边仍持有的音。
- 最后一个持有者松开才发送 Note Off。
- 每次实体琴按下都保留这一次的原始力度，不会因为电脑已持有同音而无声。
- 不重合的实体音保持原力度；其他通道的同音独立处理。
- S 显示踏板松开时的默认状态；Space 或点击 S 切换。S 红：松开不延音、踩下延音；S 绿：松开延音、踩下暂时取消延音。踩踏不改变 S。
- 按 MIDI CC64 的标准阈值（64）判定踩下，每个演奏通道独立；这是开关延音，不是半踏连续控制。仍按着的琴键不会被踏板静音。
- 若实体踏板的松开／踩下发值反向，需要先校准踏板／键盘极性；不能仅凭一条 CC64 猜测脚的实际位置。
- 关闭／失焦沿用电脑持音清理规则、默认 S 回红；已收到的实体踏板按下状态仍按对应通道生效。重载插件会清空踏板瞬时状态，请松开再踩。

## 本轮补充验收

以下为历史音乐核心验收，早于 0.1.2 的纯 UI 更新：

- `mixed_ab.lua`：Track FX 42/42，Input FX 42/42；每项同时与原 JSFX 和独立预期 MIDI 比较。
- 覆盖 channels 1/2/15、外部半音/音阶音、双方同音的两种先后释放顺序、原力度、踏板锁定。
- `mixed_record.lua`：两版 Input FX 实录各 6 音；音高、通道、力度、正音长通过，未把控制键录成音符。
- 在实际 REAPER/ysfx 编辑器中人工检查灰点与彩色高亮，两版均符合以上规则。
- 系统识别到 Keystation 61 MK3，隔离 REAPER 已打开其 `/dev/snd/midiC4D0` 输入句柄。
  **用户真实按键仍须以现场事件记录验收，不把模拟 MIDI 测试当作实体演奏通过。**

证据见 `mixed_acceptance.json` 和本机 `target/chordlab-clap-release/evidence/mixed/`。
复现：用 `stage_port.py` 分别创建 `/tmp/chordlab-mixed-track`、`/tmp/chordlab-mixed-input`，
在各自独立 profile 的空工程执行 `mixed_ab.lua`；后者随后执行 `mixed_record.lua`。
REAPER 若弹出保存录音提示，选择 Save All；只对 scratch 测试工程操作。

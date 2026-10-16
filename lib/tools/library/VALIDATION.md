# Synth Library 验证记录

日期：2026-10-15。本记录区分已通过的路由／窗口检查与未通过的交互验收。

## 本轮：单击音色轨显示三个窗口

- `lua lib/tools/library/test_mode.lua`：21 项断言通过。覆盖启动、选轨优先、Solo 兼容、
  单在线／独占路由、无 Solo 静音、文件夹不切音色、窗口不被持续拉回、工程切换退出。
- `luac -p 'lib/tools/library/Library mode.lua'`：通过。
- `python -m pytest -q -p no:cacheprovider lib/tools/library/test_prepare.py lib/tools/chordlab/tests/test_install.py`：18 passed。
- 在 `/tmp/library-final-audit/synth.rpp` 实际鼠标点击 `A3-mks70`、`C4-darkdrone`：
  每次均为 1 个在线 Surge、1 个音色 Solo、1 个 armed 输入轨、1 个 Input FX、1 个 Surge 浮窗；
  Chord Lab 浮窗和原生虚拟键盘均打开。
- 截图确认左上 Chord Lab、左下 VKB 等宽，组合顶底与右侧 Surge 对齐，底部混音台可见。
- 原始记录：`/tmp/library-final-audit/selection-results.txt`、`selection-after.png`。
- 正式 `~/storage/daw/synth.rpp` 在这轮切轨测试中未改写；保留用户 C4 音色调整与 Master −3 dB。

## 既有检查与限制

- 先前顺序加载 86 个音色的普通 MIDI／电脑控制通道路由检查通过；不代表 USB MIDI 硬件已验收。
- 冷启动 monitoring 通过宿主 `SetTrackUIInputMonitor` 重建，已有两次不按 Play 的发声检查通过。
- 先前单在线测量 CPU 中位数约 54.98%（以单核为基准）、峰值约 78.98%，RSS 约 326–381 MiB。
  曾记录至少 4 次 xrun，不能宣称零爆音。这些是先前测量，不是最新选轨版本的全量性能复测。
- 曾在全在线压力测试发生 Surge 音频线程崩溃；单在线减少资源压力，但未证明修复内部崩溃根因。
- 历史原始数据原在 `/tmp/library-final-audit/earlier/`，现已与本轮报告一并持久归档，见下方。

## 最新选轨版本：86 轨全量复测

- `host_audit.lua` 改为逐轨 `SetOnlyTrackSelected`，覆盖新版自动显示 GUI 的实际路径；
  不再仅靠设置 Solo 检查旧路径。18 项 pytest、21 项 Lua 断言与 Lua 语法检查均通过。
- 86/86 电脑控制通道、86/86 普通 MIDI 消息通道有输出；每条均只有 1 个在线 Surge、
  1 个 Solo、1 个 armed 输入、1 个 Surge 浮窗，控制通道 Note Off 后 held=0。
- 顺序测试约 374 秒，无崩溃。CPU 中位 52.98%、峰值 71.98%（单核=100%），
  RSS 328.17–365.68 MiB。正式 REAPER 同时打开但未演奏；这些数值只统计临时测试进程。
- 至少捕获 1 次新的音频 underrun，媒体 underrun 为 0。逐轨时间戳不能给出精确总次数，
  不宣称零爆音，也不能用一次六分钟测试证明长期稳定。
- 状态严格一致性检查**未通过**：临时工程初始已有 A2/A3/C4 三条与 FXP 不同；
  此次加载并显示 GUI 又使 70 条的 `nonparamconfig/tuningApplicationMode` 从 0 变为 1，
  其他经现有 canonicalizer 比较的 patch XML 及全部 86 份 wavetable 二进制一致。
  初始宿主 `dawExtraState` 中此字段为 1，Surge 编辑器打开时用它覆盖 patch 中的 0，
  对应 [Surge 1.3.4 官方恢复代码](https://github.com/surge-synthesizer/surge/blob/release_xt_1.3.4/src/surge-xt/gui/SurgeGUIEditor.cpp#L6208-L6265)。
  当时正式工程只读检查有 72 条同类冲突；后续已按用户批准修正，见下方补充记录。所有轨的 hasTuning/hasMapping 为 0，
  但不应简单忽略该字段后宣称音色完全一致，特别是今后使用自定义调律时。
- 原始数据持久归档：`~/storage/daw/reports/2026-10-15/library-final/`，含测试前工程副本、
  86 条测试后 CLAP 状态、性能采样、音频结果、原生输入测试记录、差异明细及复现脚本。
  它们是验收资料，不是新的日常工程或需要安装的 helper。

## 原生电脑持键与实际鼠标拖动复测

- 隔离工程 `/tmp/surge-input-test/library.rpp`，REAPER 7.78、Surge XT 1.3.4 CLAP、
  A2-fmpad，Master 设为 0 避免测试声响；使用临时 uinput 键盘与鼠标，结束销毁设备。
- 在 Chord Lab 按住 D：`held=1`、轨道峰值 `0.03181520`。
  移到 Surge 并实际拖动 Filter 1 Cutoff：六次采样 `held=1`，峰值 `0.03093–0.04072`；
  拖动后宿主读取 cutoff 从 `0` 变为 `0.08928566`，没有用 API 代替鼠标修改参数。
- **失败边界**：在 Surge 内松开 D 后仍 `held=1`，再次按／松 D 也没有解除。
  所以持音中有输出不等于完整演奏通过；存在 Note Off 丢失／挂音。
- 返回 Chord Lab 后再按／松同一 D 可清理；若先点回 Chord Lab 再松键也能结束持音。
  仅返回焦点并不会自动解除已经挂住的音，这不是跨窗口输入的修复。
- 普通 channel 1 MIDI 消息持音，实际拖动 cutoff 至 `0.17857131`，六次采样峰值
  `0.01273–0.01465`。测试结束显式 Note Off、清理电脑控制音，恢复临时音色参数。
  这是软件 MIDI 消息通路测试，**不是 USB MIDI 键盘验收**。
- 采样不能证明毫秒级完全无断音；这里只确认采样时有持续输出和鼠标参数确实变化。

## Surge 弹出菜单问题：与一般鼠标操作区分

- Scene A/B 按钮、cutoff 拖动都有效；纠正此前“Surge 整体 GUI 鼠标无响应”的判断。
- Menu 原生 X11 弹窗创建后约 5–15 ms 就关闭；保持测试鼠标设备存活也复现。
  没有观察到键盘修饰键卡住。
- 在不含 Chord Lab／VKB 的独立工程、CLAP／VST3、临时 REAPER 7.82 中均复现；
  Surge standalone 同机菜单能正常打开。不是必须依赖本工具才能出现的问题。
- 临时关闭 Sway `focus_follows_mouse` 未解决，已恢复 `yes`；没有安装试验版 REAPER，
  正式版本仍为 7.78。没有新增常驻输入 helper 或试验启动环境。
- 上游有同类 [Linux/Wayland 菜单报告](https://github.com/surge-synthesizer/surge/issues/7663)，
  其评论包含 Sway + REAPER 组合。怀疑宿主嵌入窗口／JUCE／合成器焦点交互，
  **尚未证明确切根因，也未修复**。

## 尚未通过，不能宣称全部收尾

- Surge 内部弹出菜单立即关闭的问题尚未修复。
- 跨 Surge 焦点的电脑按键／松键传递仍不可靠；不能作为完整边弹边调验收通过。
- 没有连接实体 MIDI 键盘，真实 USB MIDI 持音并拖动参数未验收。
- tuning 冲突已修正，最新全音色复测及原始报告已归档；但上述菜单、underrun 和输入边界
  仍未全部通过，不能标记所有验收项通过。修正后没有重新跑完整 86 轨音频压力测试。

## 用户批准后的 tuning 修正与窄键布局

- 用户明确批准“先保存当前编辑，再备份并修正”。正式工程先保存当前 RAM 编辑、
  正常停止 Library／Chord Lab 并退出，然后才从最新文件生成修正；没有使用旧候选覆盖。
- 修正 72 个宿主 `dawExtraState/tuningApplicationMode`，与各自当前 patch 对齐。
  全 86 份 patch 参数、wavetable、其他宿主字段均逐项保持；STATE 外工程内容完全相同。
  用户 C4-darkdrone 精调保留，没有把音色重置回 FXP；Master 仍为 −3 dB。
- 稳定版实际宿主抽查 A1-bellpad：打开 GUI 前后 patch/host 模式均为 0，无冲突，
  patch 参数与 wavetable 一致；进程 maps 确认加载 `/usr/lib/clap/Surge XT.clap`，不是 nightly。
  这项 GUI 往返验证是抽查，全部 86 份检查是文件级语义／二进制比较。
- 新增修正器与审计测试：35 项 pytest、21 项 Lua 断言、Lua 语法检查通过。
- 正式工程重开：86 个音色标记，C4 在线，1 online／1 Solo／1 armed／1 Surge 浮窗，
  Library 与 Chord Lab 会话均运行，原生 VKB 打开。启动验证遇到空工程时断言拒绝保存，
  随后明确打开 synth.rpp 后重验通过。
- VKB 保持宽度 884 px，高度由 202 降至 150 px，位置仍 `(560, 894)`。实测原生
  琴键随高度变窄，同宽约显示五个八度，MIDI 60 / C4 在中间。未修改键盘通道或按键映射。
  Sway 规则与 REAPER 保存位置负责布局，未增加常驻 helper。
- 备份与证据：`~/storage/daw/reports/2026-10-15/library-tuning-fix-20261015-210035/`。
  `synth-before.rpp` 是保存当前编辑后的回滚副本，`synth-aligned.rpp` 是修正副本；
  `repair.json` 记录哈希与改动清单。日常唯一入口仍为 `~/storage/daw/synth.rpp`。

## 官方 nightly 隔离排查：没有安装

- 临时测试官方 `NIGHTLY-2026-10-13-d8b4a7b` plugin-only 包，独立 HOME／REAPER profile；
  进程 maps 确认实际加载临时 nightly CLAP。资源仍使用本机 `/usr/share/surge-xt`，
  因此不是完整新版资源包的兼容性认证。正式插件、REAPER 版本没有升级。
- 弹出 Menu 仍立即销毁；原生 D 持音中鼠标拖动 cutoff 有效果，但在 Surge 松键
  仍丢 Note Off。普通 MIDI 消息持音／松音可用，仍不是实体 USB MIDI 验收。
- 原始菜单事件与持音拖动数据在上述报告目录 `nightly-test/`；临时进程已退出。
- 当前启动没有检测到 Spark，路由回系统默认 `eq_woo_in`；不代表已验证硬件听音输出。

### 布局后续调整

用户要求左右两组重新顶底对齐：Chord Lab 增高至 `884×646`，位置 `(560, 300)`；
原生 VKB 保持窄键 `884×150`，下移到 `(560, 946)`。两窗组合下沿为 1096，
与 Surge `(1480, 300, 1232×796)` 一致。MIDI 60 居中及约五个八度显示不变，
已更新 Sway 初始规则并目视核对；不修改音色、路由或输入映射。

## 本轮 wrapup：已保存，不等于所有交互问题解决

- 按用户要求保存正式 `synth.rpp`，宿主返回 `IsProjectDirty=0`，Master −3 dB；
  Library／Chord Lab 保持运行，REAPER 不关闭。未导出或覆盖公共 FXP。
- 最终文件检查：86 份 Surge state，tuning 冲突 0；35 项 pytest、21 项 Lua 断言及
  Library Lua 语法检查通过。该收尾没有重跑音频压力测试或实体 MIDI 验收。
- 最终窗口位置已写入 Sway 规则；REAPER 自己的 INI 可在退出时刷新坐标，
  初始布局以 Sway 规则为准。两窗组合高度 796 px，与右侧 Surge 一致。
- 更新 Chord Lab README 中旧的尺寸／默认音色说明，保留所有历史验收边界。
- 本轮源码与文档保存到仓库工作区；未执行 Git commit、未安装 nightly、无测试输入 helper 常驻。
- 待处理项仍是 Surge 弹出菜单、电脑键跨焦点 Note Off、Tab 可靠传递、实体 MIDI 验收；
  全量测试曾记录 underrun，不能宣称零爆音或全部性能验收通过。

## 2026-10-16：恢复选轨开窗

- 选中音色轨时先完成独占路由／上线，再显示该轨 Surge 和共享 Chord Lab；VKB 继续由原有 Chord Lab 会话联动。切音色关闭旧 Surge 浮窗，不添加键盘 helper。
- 只响应选中轨道变化；稳定轮询不重开手动关闭的窗口，文件夹／输入轨不触发开窗。离开再选回当前音色可重开，不必重载音色；仅改变 Solo 不主动开窗。
- `python -m pytest -q lib/tools/library/test_*.py lib/tools/chordlab/tests`：56 passed；Library Lua mock：30 assertions；Chord Lab Lua mock：40 assertions。相关 Lua 语法和 `git diff --check` 通过。
- 当前 REAPER 已重载会话，实测选回当前在线音色自动显示 Surge／Chord Lab／VKB；手动关窗后等待不重开，离开再选回可恢复。未运行遍历 89 条轨的完整音频压力验收；`host_audit.lua` 的窗口断言已同步新行为。
- Chord Lab 单独 offline／online 重载后，逐项核对调性、音级、转位、音区、velocity、Enabled、类型及 `JS_SER` 记忆不变。未保存 `synth.rpp`，未主动改写 Surge 参数或 FXP。
- 临时测试实例已退出，只有原 REAPER 进程保留。首轮重载命令因缺少原会话完整环境启动了空实例，工程路径断言阻止执行；仅清理该空实例后，使用原进程环境发送命令成功。
- 临时结果位于 `/tmp/chordlab-feature-20261016/`，含宿主记忆检查和 live reload 结果。首次打开 VKB 的间歇对齐问题本轮未修改；单次位置正确不代表该问题已修复。

## 大调双层图与 VKB 手动开关（2026-10-16）

本节替代上节“选轨打开三个窗口”的当前行为：选轨仅显示 Surge 与共享 Chord Lab；
原生 VKB 通过 View → Virtual MIDI Keyboard 手动打开，不跟随编辑器开关。

- Chord Lab 独占左侧 `884×796`、位置 `(560,300)`，上下两组音阶／和弦图均放入窗口；
  与右侧 Surge `1232×796` 顶底对齐，不再借助原生 VKB 补足高度。
- Sway 只更新 Chord Lab 的初始高度规则，不添加进程、后台服务或全局输入捕获。
- 本轮 pytest **80 passed**；Lua mocks **30 + 42** 项；隔离 REAPER 状态 **101**、生命周期 **32**、音高／调号／音阶颜色 **7041** 项通过。
- `host_audit.lua` 的电脑通道检查改为显式打开 VKB，退出恢复原可见性；本轮未重跑 89 音色完整压力测试。
- 生产实例重载验收通过：保留当前 B2-juno60 音色选择、Chord Lab 参数与 `JS_SER` 记忆；选轨打开两窗、手动关闭后轮询不重开、离开再选回恢复两窗，VKB 全程关闭。没有保存生产工程。
- 实测两窗外框高度均 796、顶部 300、底部 1096。REAPER 重载沿旧窗口中心偏移的位置已一次性纠正；未来首次定位的既有限制没有被当作本轮已修复。

## 恢复 VKB 随选轨打开（2026-10-16，最新行为）

用户最终选择继续包含 VKB：选轨显示 Surge／Chord Lab／VKB，打开 Chord Lab 也带上 VKB。
稳定轮询不重开手动关闭的 VKB；下次选轨或重新打开编辑器才恢复，关窗不双向联动。
当前 REAPER 已重启 Lua 会话并通过三窗恢复、computer mode=1、手动关闭保持、重新选轨恢复检查；
未改音色、voicing 或保存工程。pytest 84 passed，Lua mocks 31 + 43 assertions。
VKB 初始位置更新为 `(560,150)`、尺寸 `884×150`；双层 Chord Lab 仍为 `(560,300)`、`884×796`，
钢琴／吉他 50/50 与统一底色保留。真实电脑按键进入 Surge 的焦点限制未改变。

## 等高居中与加长 VKB 琴键（2026-10-16）

- 保持用户确认的 Surge 实测 `1359×875`；原生 Zoom 菜单选择 150% 后本机实际回报 149%，保存实际值为默认。未批量改写其他实例缩放、音色或保存 `synth.rpp`。
- 移除 Chord Lab 内部标题行及 36 px 留白，内容 `884×731`、外框 `884×760`。上下图尺寸仍相同：谱表 294 px，钢琴／吉他各 141 px。保留 REAPER FX 工具栏。
- VKB 位于正下方，同宽 `884×115`；此前 79 px 方案按用户反馈加高 36 px。左列总高与 Surge 均 875 px，顶部 282、底部 1157，屏幕上下余量 282／283 px。最终坐标与截图在 `/tmp/chordlab-centered-20261016/`。
- 仅注入同名 Sway `for_window` 规则时，重开仍沿用旧定位；刷新 Sway 配置后，新尺寸／坐标重开验证通过。没有添加常驻窗口控制或输入 helper。
- Surge 隐藏／重开后所有暴露的音色参数一致。JSFX 首次重载验收检测到调性从 5（F）变成 8（Ab），因此没有把该次检查记为全通过；`JS_SER` 一致，已向用户确认是否主动切调，未擅自覆盖当前调性。之后重开 Chord Lab／VKB 的当前参数、记忆、computer mode=1 检查通过。
- pytest **84 passed**；Chord Lab Lua mock **43**、Library mock **31** 项通过；`git diff --check` 通过。本轮没有重跑全量音频／实体 MIDI 验收，也没有保存工程。

## 小幅收紧谱表并增加 VKB 高度（2026-10-16）

- Surge 保持用户确认的 `1359×875` 不变。Chord Lab 内容 `884×707`、外框 `884×736`，位置 `(560,282)`；VKB `884×139`、位置 `(560,1018)`。组合仍为 875 px，高度居中不变。
- 上下谱表同步由 294 缩至 282 px；钢琴／吉他由各 141 缩至各 135 px，50/50 和统一底色不变。谱号字形缩放 0.62→0.59。半谱间距 11→10.5 px，音点半径保持 7 px。
- 现场截图逐点检查当前 Ab 大调与 AbM9 的 21 个间内音点（含错列音点），其上下圆点边缘外、谱线内侧共 84 个留白采样点均为背景色；线上音点正常压线。此检查针对当前默认尺寸，不代表任意手动缩至极小窗口仍有同样留白。
- JSFX 重载的参数、`JS_SER` 记忆、VKB 可见性均保持；之后重开检查参数／记忆与 computer mode=1 通过。pytest 84 passed，Lua mocks 43 + 31 assertions，`git diff --check` 通过；未保存工程、未修改 Surge 音色。截图和检查记录：`/tmp/chordlab-spacing-20261016/`。

## 取消左右窗口间隙（2026-10-16）

- Surge 当前及默认位置从 `(1480,282)` 左移至 `(1444,282)`，取消 36 px 间隙；三窗大小不变。
- Sway 配置已刷新，实测 Chord Lab／VKB 右边缘均为 1444，与 Surge 左边缘一致；左列上下相接、左右顶底对齐。未重载插件或保存工程。检查记录：`/tmp/chordlab-spacing-20261016/gap-removal.txt`。

## 最终一档与本轮收尾（2026-10-16）

- Surge 保持 `1359×875`、`(1444,282)`。Chord Lab `884×712`、`(560,282)`；VKB `884×163`、`(560,994)`。三窗无缝相接，整组高度仍 875 px，默认垂直居中。
- 上下图继续等尺寸：谱表各 270 px，钢琴／吉他各 129 px，仍为 50/50；谱号字形 0.56，半谱间距 10 px，音点半径 7 px。
- 当前 E 大调／D#m7b5 截图检查 19 个间内音点，上下间隙共 38 个像素样本均为背景色；线上音点正常压线。仅验证当前默认尺寸，极小手动缩放不在本次验收内。
- 安全重载及重开通过：当前参数、`JS_SER`、VKB 可见性保持，computer mode=1；三窗尺寸／边缘坐标断言通过。pytest 84 passed、`git diff --check` 通过；本轮前段 Lua mocks 43 + 31 assertions 通过。
- 文件主要为 Chord Lab JSFX 布局、UI、theme 与测试／说明，以及本机 Sway 配置；Surge 原生默认缩放沿用前面确认的实际 149%。没有新增常驻服务、没有保存或覆盖 `synth.rpp`、没有 Git commit。原生 VKB 跨 Surge 焦点的 Note Off 限制不变；未重跑实体 MIDI／全音色压力测试。
- 最终截图、参数验证、几何断言及像素检查：`/tmp/chordlab-spacing2-20261016/`。

## 修复旧 Surge 实例切轨后仍偏小（2026-10-16，收尾）

- 根因：修改默认 Zoom 不覆盖已有实例保存的旧缩放；原 Sway Surge 规则只定位，没有统一尺寸。
- Surge 开窗规则增加 `resize set width 1359 px height 875 px`；实际截图确认内容等比例放大，无空白扩框。当前与默认位置仍 `(1444,282)`，三窗无缝、整体居中不变。
- 现场切轨 `A2b-fmpad-dark → A1-bellpad → A2b-fmpad-dark`，两次新浮窗均实测 `1359×875`、`(1444,282)`；返回后原实例所有暴露音色参数一致。未保存工程、未 Git commit，未跑全 89 实例遍历。
- 结果：`/tmp/chordlab-surge-size-20261016/result.txt` 与 `switch-geometry.json`。本次只修改本机 Sway 规则和说明，不改 Lua／MIDI 逻辑。

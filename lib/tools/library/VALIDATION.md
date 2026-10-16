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

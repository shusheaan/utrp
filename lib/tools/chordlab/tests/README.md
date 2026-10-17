# Chord Lab 验证

## 普通测试

```sh
python -m pytest lib/tools/chordlab/tests -q
```

检查配置保留、VKB 映射、主题一致性、安装/卸载、运行时文件隔离和拒绝覆盖用户改动。
另由 `test_lifecycle.py` 调用 Lua host mock，检查选轨开窗、稳定轮询不抢焦点、VKB 手动独立开关、
隐藏不 bypass／disarm、旁路恢复和会话清理；需要 `lua` 可执行文件。
mock 不模拟 JSFX 音频线程，也不能代替原生窗口或实体 MIDI 验收。

## REAPER 宿主测试

只在命名为 `/tmp/chordlab-*.rpp` 的临时工程运行，不能对创作工程运行这些脚本。

轨道 1：Input FX = Chord Lab；normal FX 0 = `midi_probe.jsfx`；normal FX 1 = synth。开启 All MIDI input、arm、monitor；先退出 Chord Lab Lua 模式。测试期间不要按琴键、改变轨道或拖动 FX。

- `host_acceptance.lua`：12 调 × 7 级 × 4 转位，核对实际输出 MIDI，而非仅核对 UI 参数；另测调性锁、停音、双来源同音持有、velocity-zero Note Off、pedal、关闭电脑输入。输出 `/tmp/chordlab-acceptance.txt`。
- `mode_acceptance.lua`：会话启动/关闭、重复运行 Open、输入/arm/monitor/按键捕获恢复（不改变手动 VKB 可见性）、隐藏编辑器保留电脑持音、关闭 VKB 只释放控制音而保留普通 MIDI 持音、JSFX 单独旁路。输出 `/tmp/chordlab-mode.txt`。
- `state_acceptance.lua`：无需分号的持音／松键 K/L 记忆、不同音级隔离、跨调调用、分号重置、三／七／九和弦以及 RPP 保存重载。输出 `/tmp/chordlab-state.txt`。
- `record_acceptance.lua`：空轨录入两组四音和弦，核对 8 个 channel 1 正时长 MIDI 音符。录音后若宿主提示，选 Save All；输出 `/tmp/chordlab-recording.txt`。运行前轨道必须没有 item。

宿主音频线程与 Lua defer 异步，和弦检查等待 150 ms。最初 45 ms 等待在 GUI 更新期间出现一次输出 mask 不匹配，怀疑与异步音频处理时序有关；增加等待后完整复测通过，不自动忽略失败。

GUI 待验收：Surge 浮窗有焦点时按 D/K/L/;/Enter（当前仍有限制）；Tab 全局 action 绑定；调性锁；检查浓色大圆点与 MIDI 音高一致；检查吉他同音重复位置、品号与下方品记；确认鼠标拖动参数时的已知键盘限制。

真实外接 MIDI 键盘未连接时只能模拟独立 MIDI Note/CC，不能把模拟通过称作实体设备验收。输入探针和临时自动化 runner 不安装到用户 profile。

## 本机验证记录（2026-10-15）

REAPER 7.78 / Surge XT CLAP / Arch Linux。安装器 pytest **10 passed**；最终宿主 MIDI 检查 **370/370**；模式生命周期 **24 passed**；录音 **8 notes**（`60,64,67,71,64,67,71,72`）。原生 Enter 返回原位通过；Escape 被 FX 窗口截获关闭窗口，因此不绑定为停音。确认 synth 轨有非零音频电平且 REAPER 输出已连接到现有播放设备；不声称经过人耳音质评审。

此前 GUI 使用白底 D2–D6 键盘/17 品指板、浓色大圆点和浅色小圆点，没有光晕。实体 MIDI 设备验收仍待用户插入键盘后确认。


### 谱表与配色增量验证

- 安装器 pytest：**11 passed**。
- `staff_math_probe.jsfx` 在独立临时 REAPER 工程运行：**4781 checks / 0 failures**，覆盖 12 调 × 128 MIDI 音的拼写/音高回算、C2–C6 边界、秒度错位、12 调的调号与调内音匹配，以及高低谱号调号的字母位置。
- 实际 REAPER 浮窗截图检查：Eb 调在两个谱号后各显示三个降号；调内音旁无重复降号。两个五线谱保持长线，中央 C 与上下加线只在相应音符附近画短线。默认内容区 860 × 457。
- 钢琴／指板和弦外音共用 `external_color=#707070`，白色音名；谱表和弦外音也用灰色圆点，音高由谱位读取。此次未连接实体 MIDI 键盘验收。
- 本次未重新执行旧版 MIDI／录音验收脚本；以上为谱表增量测试，不代表 Surge 焦点和 Tab 限制已解决。

### 加线图层复查

- 实际截图发现：Eb 调 Fm7 的 Ab5 与 C6 共用上方加线，原先逐音绘制让后绘制的 C6 加线穿过已画好的 Ab5 圆点；下方共用加线同样存在风险。
- 改为两遍绘制：先绘制所有短加线，再绘制所有音符／临时记号。两个遍历采用相同的筛选与秒度错位规则。
- 保存并备份工程后在 REAPER 重载，实际截图确认 Ab5 圆点完整、没有横线穿过，中央 C 和外侧加线仍是短线；原键盘模式恢复。安装器测试再次 **11 passed**。未将此前 4781 项音高检查描述为本次重跑。

## 窗口与处理解耦验证（2026-10-16）

- `python -m pytest -q lib/tools/library/test_*.py lib/tools/chordlab/tests`：**56 passed**，其中两个测试调用下列 Lua mock。
- `lua lib/tools/library/test_mode.lua`：**23 assertions passed**；选轨／Solo 只影响路由，不请求开关编辑器。
- `lua lib/tools/chordlab/tests/test_mode.lua`：**40 assertions passed**；覆盖后台启动、保存的已开编辑器、chain／浮窗切换、VKB 双向联动、隐藏不 bypass／disarm、隐藏后重开不取消 bypass、异步旁路清理、冲突解除及退出恢复。
- 全部 Chord Lab／Library Lua 文件通过 `luac -p`；`git diff --check` 通过。
- 本次没有可用图形会话，**未运行更新后的 REAPER 宿主验收**，也未实测 `Ctrl+W`。没有修改快捷键、用户 RPP、Surge 音色或系统配置；运行目录已有 symlink 指向源码，下次启动会话加载新逻辑。
- 待宿主验收：Input FX chain 与浮窗各自开关、关闭 VKB 反向隐藏编辑器、隐藏时普通 MIDI 持音保持、重新启用 bypass、Surge 独立开关及切轨不弹窗。关窗建议使用窗口关闭按钮，不把 `Ctrl+W` 当作已经验证的统一插件关闭键。

## 自动记忆与选轨开窗增量验证（2026-10-16）

- 最新需求恢复选轨自动显示 Surge／共享 Chord Lab／VKB，替代上节历史记录中的“切轨不弹窗”；相关 Lua mock 为 30 + 40 assertions，pytest 56 passed。
- `state_acceptance.lua` 在独立 REAPER 7.78 临时 profile 中执行：**101 checks passed**。不按分号，验证持音 K/L、松键 K/L、切换音级／调性后记忆、其他音级不被修改、Enter 原位重置、类型及实际 MIDI 输出、RPP 保存重载。
- 测试 profile `/tmp/chordlab-feature-20261016/`：仅 Chord Lab + MIDI probe，Master 静音，无 Surge、无测试键盘后台程序；结束后退出测试实例。结果 `runner-result.txt` / `state-result.txt`。
- 正式会话已重载，核对原有序列化记忆和主要参数不变；选轨开窗、关窗后不重开、再次选择重开通过。没有保存正式工程。
- 实际截图 `chordlab-live.png` 确认右上角快捷键说明已删除，保留 CHORD LAB 标题、调性／音级行、谱表、钢琴和指板。
- 没有把此处 MIDI 消息测试等同于物理电脑键／硬件验收；Surge 焦点松键、Tab 和 VKB 首次位置问题仍保留此前边界。

## 大调双层图与手动 VKB（2026-10-16，替代此前窗口联动行为）

- `python -m pytest -q lib/tools/library/test_*.py lib/tools/chordlab/tests`：**80 passed**；包括主题参数边界和 Lua host mocks（Library **30**、Chord Lab **42** 项断言）。
- 独立静音 REAPER profile `/tmp/chordlab-dual-20261016/`：`state_acceptance.lua` **101 passed**，`mode_acceptance.lua` **32 passed**；打开编辑器不打开 VKB，隐藏编辑器保留手动 VKB 的电脑持音，关闭 VKB 释放控制音但不释放普通 MIDI 持音，退出会话保留手动 VKB 可见性。
- `staff_math_probe.jsfx`：**7041 checks / 0 failures**；新增十二大调七个音的四类颜色、上图不受所选和弦影响、下图维持和弦角色、谱表 E2–A5 边界检查。
- 测试注入 C#4、D4、E4、F4：C 大调图中 D/E 绿、F 橙、C# 灰；Cmaj9 图中 D 紫、E 绿、F/C# 灰，同 MIDI 音高的吉他位置同步加深。未按住的同名其他八度维持浅色。
- 临时升降号尺寸为调号的 75%，锚点从基础音点左侧 19 px 移至 34 px；调号尺寸与位置不改。默认内容区 `884×767`，实际 Linux 外框 `884×796`。
- 未连接实体 MIDI 键盘；上述注入与 mock 不代表 USB 硬件验收，也未解决既有 Surge 焦点丢 Note Off 限制。
- 当前生产 REAPER 已重载并验证：原有参数及 `JS_SER` voicing 记忆未变；选轨只打开 Surge／Chord Lab，稳定轮询不重开关掉的编辑器，重新选回可重开且 VKB 仍关闭。未保存生产 `.rpp`。
- 最终截图 `preview-final.png` 核对临时升号缩小及左移；`live-final.png` 核对当前 F 大调双层图与 Surge 同高。重载时 REAPER 按旧窗口中心上移了 75 px，已一次性移回 `(560,300)`；不声称修复既有窗口首次定位问题。测试实例全部正常退出。

## 上下组共用 50/50 高度（2026-10-16）

- 只调整主题中的钢琴／吉他高度比例至 `0.50 / 0.50`；上下两组继续使用同一组布局参数，不改谱表高度、谱号大小、圆点或临时升降号参数。
- pytest **80 passed**。当前 REAPER 重载后参数与 `JS_SER` 记忆一致，VKB 可见性不变，没有保存工程或改动 Surge。
- 实际截图像素检查：上图钢琴 `y=112..252`、吉他 `265..405`；下图钢琴 `472..612`、吉他 `625..765`，四块均 **141 px**。两块谱表均 **294 px**，间隔保持 **12 px**，外框仍 **796 px**。
- 结果及截图位于 `/tmp/chordlab-half-20261016/`。重载产生的旧窗口中心偏移已一次性放回 `(560,300)`，没有增加持续布局控制。

## 统一图面底色与手动电脑输入恢复（2026-10-16）

- 谱表、钢琴白键和吉他指板共用 `diagram_background = "#E9EDF0"`；移除空弦区和白键底部的不同色阴影，不改黑键、谱线、琴弦、音点或 50/50 布局。
- pytest **84 passed**，含共享底色配置生成和非法值拒绝测试。当前 REAPER 截图的上下谱表、白键本体／底部、空弦区／指板共 **10 个背景采样点**均为 RGB `(233,237,240)`。
- 首次重载因仍有生成持音而在离线操作之前退出，未打断演奏；后续音符释放后重载通过，参数和 `JS_SER` 记忆保留，未保存工程。
- 用户报告电脑键盘无声时，只读诊断显示 VKB `40377=0`、捕获 `40637=0`、computer mode `13=0`，当前输入 FX 和 synth 均 enabled、online。经用户明确确认后仅这次手动打开 VKB，验证以上三个状态均为 `1`；没有恢复自动弹出，也没有注入 MIDI 或声称实测物理按键发声。
- 临时诊断、重载和像素检查结果位于 `/tmp/chordlab-background-20261016/`。

## 恢复包含 VKB 的开窗流程（2026-10-16，最新行为）

- 用户确认继续包含原生 VKB：选中音色轨打开 Surge、Chord Lab、VKB；打开 Chord Lab 编辑器（含已打开编辑器的会话启动）也打开 VKB。
- 仅响应编辑器从隐藏到显示／选轨事件；稳定轮询尊重手动关闭 VKB。关闭 Chord Lab 不强制关 VKB，关闭 VKB 也不隐藏 Chord Lab，退出会话保留窗口可见性。
- pytest **84 passed**，Chord Lab Lua mock **43**、Library mock **31** 项通过；增加共享编辑器已打开、手动关闭 VKB 后重新选轨恢复的覆盖。
- 生产 REAPER 会话重启验证通过：三窗恢复、computer mode=1、手动关闭后稳定轮询不重开、离开再选回三窗重开；参数和 `JS_SER` 记忆不变，未保存工程。本轮未重跑隔离 profile 的 MIDI 状态验收。
- VKB 上移至 `(560,150)`，大小仍 `884×150`，不压缩或遮挡 `884×796` 的 Chord Lab；双层图、50/50 比例和统一底色不改。未添加外部输入后台，原生方案的 Surge 焦点限制仍在。
- 记录与 Sway 修改前备份位于 `/tmp/chordlab-vkb-20261016/`。

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

## 最终一档与本轮收尾（2026-10-16）

- Surge 保持 `1359×875`、`(1444,282)`。Chord Lab `884×712`、`(560,282)`；VKB `884×163`、`(560,994)`。三窗无缝相接，整组高度仍 875 px，默认垂直居中。
- 上下图继续等尺寸：谱表各 270 px，钢琴／吉他各 129 px，仍为 50/50；谱号字形 0.56，半谱间距 10 px，音点半径 7 px。
- 当前 E 大调／D#m7b5 截图检查 19 个间内音点，上下间隙共 38 个像素样本均为背景色；线上音点正常压线。仅验证当前默认尺寸，极小手动缩放不在本次验收内。
- 安全重载及重开通过：当前参数、`JS_SER`、VKB 可见性保持，computer mode=1；三窗尺寸／边缘坐标断言通过。pytest 84 passed、`git diff --check` 通过；本轮前段 Lua mocks 43 + 31 assertions 通过。
- 文件主要为 Chord Lab JSFX 布局、UI、theme 与测试／说明，以及本机 Sway 配置；Surge 原生默认缩放沿用前面确认的实际 149%。没有新增常驻服务、没有保存或覆盖 `synth.rpp`、没有 Git commit。原生 VKB 跨 Surge 焦点的 Note Off 限制不变；未重跑实体 MIDI／全音色压力测试。
- 最终截图、参数验证、几何断言及像素检查：`/tmp/chordlab-spacing2-20261016/`。

## Sustain、Tab 即时记忆与音量平衡（2026-10-16）

- 新增 `controls_acceptance.lua`：独立无音源的 REAPER profile 实测 **42 checks passed**，包含 channels 1–15 的延音锁、实体踏板松开不撤销锁、隐藏 UI 保留锁、panic／禁用复位、channel 1/15 的 12 档代表性 Note On 力度原样透传、velocity-zero Note Off、电脑固定力度 64、Tab 切换自动记忆与音级隔离、保存重开后保留类型且 Sustain 默认 OFF。
- 修复重开工程时宿主在 `@init` 后恢复 command serial 导致旧命令被重播的问题：首个音频 block 同步 serial，丢弃存盘命令，显式发送 CC64=0。真实 RPP reload 回归通过。
- 测试探针曾有不支持的 EEL 一元取反语法，已修正；测试曾误用隐藏 UI 的鼠标持音命令，触发预期的超时释放，已改为电脑控制 MIDI。以上失败不记为产品验收通过。最终结果为 `/tmp/chordlab-controls-result.txt` 的 42 checks。
- pytest **85 passed**；Chord Lab lifecycle mock **46 assertions**、Library mock **34 assertions**；所有相关 Lua 通过 `luac -p`，`git diff --check` 通过。
- 正式工程当前 Master 从 `0.70794578438414`（-3 dB）升至 `1`（0 dB），电脑和弦力度从 76 降至 64；实体 MIDI **没有**新增力度曲线、固定力度或压缩。既有各音色轨增益不改。短时输出监测未捕获有效演奏，不据此宣称极重触键／所有音色无削波。
- 正式 Chord Lab 与 Lua managers 已安全重载；当前调性、音级、转位、类型、完整 `JS_SER` 记忆、各轨增益与 Master 全部保持。鼠标实际点击 `Sustain ON / OFF` 截图通过，最后恢复 OFF。没有向正式工程注入音符，也没有保存覆盖 `synth.rpp`。
- 隔离测试实例已退出；当前 RAM 工程备份、参数一致性记录与截图位于 `/tmp/chordlab-controls-20261016/`。自动记忆不等于自动保存工程，长期保留仍需用户保存 `.rpp`。本轮未重新进行实体键盘人耳响度评审。

## 分号恢复默认、Enter 切换 Sustain（2026-10-16）

- `;` 替代旧 Enter：恢复当前和弦 inversion=0、centre=60，保留三／七／九和弦类型并即时记忆。Enter 改为 Sustain 锁切换，Note Off 不撤销锁，重复 Note On 不重复切换。Tab、K/L 自动记忆行为不变。
- 独立无音源 REAPER profile 的 `controls_acceptance.lua` **50 checks passed**，覆盖新增 reset／Enter 行为与原有 42 项回归。pytest 85 passed；Lua 语法和 `git diff --check` 通过。
- 正式工程安全重载通过：参数、完整 `JS_SER`、各轨音量与 Master 均保持，两个 managers 已重启。重载前因演奏仍在继续而被保护检查拒绝两次；用户暂停后通过。测试实例已退出，正式工程未保存覆盖。
- 正式窗口通过 X11 模拟 Enter 验证 OFF→ON、随后单独一次 Enter 验证 ON→OFF；这是软件键盘事件验证，不是用户实体按键验收。首次双键尝试仅一组 Note On/Off 进入 VKB，因此不把该尝试记为两次切换均成功。确认焦点稳定后单键关闭通过，最终 Sustain OFF。
- Master 沿用用户随后要求的 -1.5 dB，电脑和弦力度 64，实体 MIDI 力度未修改。结果与 RAM 工程副本在 `/tmp/chordlab-keys-20261016/`；隔离测试结果 `/tmp/chordlab-controls-result.txt`。

## 音点居中与 Royal 125% 布局（2026-10-17）

- 钢琴黑键宽度改为奇数整像素，地图音点填充直径与黑键一致，钢琴与吉他共用该尺寸；音名字号随音点缩放。白键音点按实际绘制边界居中，黑键圆心与键中心共用坐标；分数像素圆心使用透明图像插值，避免圆点取整而文字未取整的错位。谱表继续使用独立 `note_radius`，不跟随地图放大。
- 在用户加宽的 `1040×780` Chord Lab 截图中，检查上图 16 个黑键音点：黑键宽 19 px，音点左右对称且没有越出黑键。恢复 884 px 宽后音点自动适配较窄黑键，不保留会溢出的 19 px。截图与像素检查位于 `/tmp/chordlab-dots-20261017/`。
- pytest **85 passed**，`git diff --check` 通过。正式 JSFX 安全重载通过，当前参数、完整 `JS_SER`、各轨增益和 Master 不变；最终重载记录位于 `/tmp/chordlab-dots-final-20261017/`。未重新运行实体 MIDI 或全量宿主录音验收。
- 确认 Surge XT 1.3.4 官方 `SurgeGUIEditor::setZoomFactor` 在 Linux 将 150 强制转换成 149；之前只把外框拉至 150% 尺寸并不能固定内部缩放。用户改选 Royal 原生 **125%**。读取当前实例的 `dawExtraState/instanceZoomFactor=125`，关闭／重开仍为 125；默认配置落盘为 125，Sway 仅在开窗时设置匹配的原生 125% 尺寸，不添加持续改尺寸服务。
- 最终布局：Chord Lab `884×631@(684,335)`，VKB `884×139@(684,966)`，Surge `1187×770@(1568,335)`；三窗同在 workspace 2，左列上下相接、左右等高，整组 `2071×770` 在 `3440×1440` 屏幕中央（横向余量 684/685，纵向 335/335）。恢复原宽度，左列高度按更小的 Surge 重新分配，并非恢复旧 875 px 总高。
- Surge 缩放前后原始音源 payload 唯一差异为 `instanceZoomFactor 149→125`；全部 778 个暴露参数、engine XML 和二进制 wavetable 均保持。125% 原像素截图检查标题较 149% 清晰；不声称主题 PNG 小字能变成矢量字。验证与截图位于 `/tmp/surge-zoom-source/`。未覆盖保存 `synth.rpp`。

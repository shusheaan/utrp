> **0.3.3 已于 2026-10-22 安装到真实 Bitwig**：见 [游戏模式及实际测试记录](GAME.cn.md)。[独立运行](STANDALONE.cn.md)已暂停，音色菜单取消；以下保留正常模式和历史安装记录。

# Chord Lab CLAP 0.2.14

## 固定大调配色与游戏和弦胶囊（0.3.3，2026-10-22）

- 只给第二行和弦胶囊上色；顶部 `Am/C` 等选调胶囊保持原样。填充与文字复用现有音符配色，当前目标用饱和填充及白色轮廓突出。
- 颜色固定按选调胶囊对应的大调音级，不随当前和弦或相对小调重新起算。例如 `Am/C` 下 A 始终沿用 C 大调六级的蓝色，不把 A 改成红色。游戏上方调内音图也沿用同一大调配色；下方和弦内部音符角色配色不变。
- 游戏左侧保留七个和弦胶囊；当前目标显示级数、和弦名、精确最低音及八度，借用／变化和弦显示 `bII` 等变化级数。其他项显示当前游戏音阶的三和弦参考，不冒充已排定的后续 voicing。
- 游戏胶囊只读，计分、时限、隐藏未命中答案、弹中后的音符显示、正常模式选择和音型记忆不变。关闭 G 后恢复正常模式。
- 新增真实 JSFX 标签与 LICE 像素回归：12 调 × 大小调 × 7 个根音、转位／变化级数、三种窗口宽度的填充和目标轮廓、游戏禁点与正常模式点击。1348 项 Python、12 项 CTest、CLAP probe、`cargo test` 和 `cargo clippy` 通过。隔离 Sway 截图见 `target/chordlab-colored-choices/`；真实部署记录另见 GAME。


## 延音接收端同步修复（0.3.2，2026-10-22）

- 修复普通模式 S 为绿色、但下游音源没有收到有效 CC64 时，实体 MIDI 与电脑和弦松键即停的问题。启动只发送一次 CC64 不足以覆盖音源晚加载、重新激活或下游控制器状态被清理。
- 每次实体 NoteOn 前按对应通道重发当前有效 CC64；电脑和弦每次发音前重发一次。消息与音符同一采样位置、CC 在前。不延迟或吞掉 NoteOff，也不持续轮询。
- 保留 S 手动关闭、踏板临时反转 baseline、14 个音乐通道及分析/命令通道隔离。G 关闭时原有音型、界面、焦点逻辑不变；不改音色、音频路由、Arm 或服务。
- 新测试模拟错过启动消息或状态被重置的接收端；修复前失败，修复后通过，覆盖两个 baseline、踏板开关、14 个通道与电脑和弦。证据：`target/chordlab-sustain-routing/`。


## 默认 Sustain 与启动 Focus（2026-10-21）

- 新建或重载插件时默认 Sustain On，包括保存过 Off 的旧工程。首次音频块先发 CC64 Off 清理旧延音，再向 14 个音乐通道发 On；不重放旧命令，也不把首次到达的宿主停止状态误认为真正的播放停止。
- 编辑器默认开启电脑键盘接管，等原生父窗口实际可见后获取一次 Focus。关闭后重新打开也获取一次；用户切到其他窗口后不持续抢焦点，手动关闭 A 在当前编辑器中保持关闭。实体 MIDI 不依赖界面焦点。
- Space/S 仍可手动关掉 Sustain；失焦、隐藏或关闭界面不改变当前 Sustain。真正的 transport Stop 和紧急清理仍关闭延音。仅重新打开界面不重置用户手动选择。
- 保留 920×703 默认大小、20 品与高把位白点、21 个参数和 v3 状态格式。没有新增服务，也没有修改音频路由、音量、Arm 或 Library 互斥策略。

验证记录见 `target/chordlab-startup/`。新增真实 CLAP 新建/旧状态恢复及 X11 延迟映射、失焦不抢回、关闭/重建测试；实体键盘和音箱的最终听感由用户确认。


验收：975 项 Python 测试、9 项 CTest、构建与安装 CLAP 探针通过。额外 `clap_probe <plugin> --focus` 在隔离的 rootful Xwayland 中验证原生延迟映射及一次性 Focus；普通 rootless Sway 会重定向测试用 unmanaged 窗口的焦点，不能替代隔离测试。测试服务器未监听网络，结束后关闭；JUCE 所需 WM atom 名称已在测试服务器预先注册。

已保存、备份并重启 Bitwig Library，Workspace 2 实际窗口为 920×703，启动 S/A 均绿色；未点击插件即向当前原生焦点发送和弦键，sfizz 显示 4 voices，松开后清理并恢复 Sustain On。XTest 在此 rootless 会话未产生有效按键，实际证据使用 XSendEvent，不冒充真人实体键盘验收。
安装 SHA-256：`39492f9bdf064aaa50aed63cc9df3bf695e847e23866edeb085f3e0e4c65a7ac`。

## 历史版本

# Chord Lab CLAP 0.2.13

> 2026-10-21 窗口复发修复：已通过[原生开窗规则](../plugin_windows/README.cn.md)消除先平铺后浮动的尺寸竞争，新建共享/吉他实例均为 920×703；下面“未改窗口策略”是较早的临时恢复记录。插件二进制和 20 品功能不变。


## 20 品指板与高把位（2026-10-21）

- 两块指板由 `guitar.toml` 的 `max_fret = 20` 统一控制，保持默认 920×703 窗口和原字体／音符大小，不靠放大窗口容纳更多品。
- 食指候选依原七和弦音型按 12 品重复；锚点上限从 14 扩到 18，保留完整的「食指品位 + 后两品」区域。继续按覆盖音数量去掉相邻候选，因此不是每品都画白点。
- Guitar 模式下，下方和弦指板上沿显示候选空心点／当前实心点。高把位与 H/L 导航、实际 MIDI 发声、v3 保存恢复共用同一目录；Piano 模式不显示这些手位点。
- 当前窗口曾到达允许的最大值 1636×1220，已用窗口管理器恢复默认大小；未改插件缩放、默认尺寸或全局窗口策略。仅凭窗口尺寸不能断定是谁触发了放大。
- 稳定 CLAP ID、21 个参数及 v3 状态格式不变；旧合法手位仍能读取，并按当前候选目录解析最近位置。

验证记录：`target/chordlab-twenty-frets/`；覆盖 20 品渲染界限、12 调八度候选、持音导航，以及 18 品手位／第 20 品音高的保存恢复。

验收完成：569 项 Python、9 项 CTest、构建及安装后 CLAP probe 通过；相关布局／controller／备份回归 396 项通过。Library 已保存、备份并重启，实查 920×703、20 品和高把位白点。

## 历史记录

# Chord Lab CLAP 0.2.12

## 踏板保持与焦点修正（2026-10-18）

- 实体采样确认原先踏板极性颠倒：踩下 CC64=0、松开=127；用户保持踏板松开重新启动 Keystation 后，捕获到踩下=127、松开=0。没有添加写死的反向映射，也不从任意第一条事件猜极性。
- Space／S 设定不踩踏板的默认状态；踩住时临时反转，松开恢复。S 只表示默认状态。重复同值 CC64 不切换；连续四秒没有新事件也保持踩住状态。
- 修正另一个独立问题：窗口失焦、关闭／隐藏编辑器的电脑键释放不再重置默认延音。仍释放电脑按键与和弦 Note On 的所有权，不改变实体 MIDI 按键和踏板状态。自动延音开启时，已释放的音仍遵循延音状态，不等于立刻静音。
- 宿主停止播放、真实演奏通道的紧急清音／重置、插件重新加载仍沿用安全清理规则；本次不承诺跨重启保存延音。
- “不延音”表示松开琴键后正常释放，不是音量静音；按住琴键的音不会因为踩踏板而被强行切断。

证据：`target/pedal-hold-check/`。新增失焦回归在旧引擎失败、新引擎通过；实际 CLAP probe 同样验证失焦后保持模式和踩放行为。实体 CC64 捕获不等于所有音源的听感已验收。

## 历史记录（以下失焦清理说明由 0.2.12 替代）

# Chord Lab CLAP 0.2.11

## 2026-10-18：踏板临时反转默认延音

- S 是踏板松开时的默认状态，不是踩踏指示灯。S 红：松开不延音、踩下延音；S 绿：松开常延音、踩下暂时取消延音；Space／点击 S 改默认。
- 14 个演奏通道各自记录 CC64，输出为默认状态与踩下状态的异或。踩住时改默认立即重算；重复 CC 不切换默认。阈值为 64，不做半踏连续控制。
- 只发 CC64，不用 All Notes Off 或音量静音实现踏板；仍按着的实体琴键和电脑和弦不被释放。Channel 15 的吉他显示和 channel 16 的控制输入不能改变踏板状态。
- 重置控制器会清除对应通道的瞬时踏板状态；保留旧的焦点／关闭时清理电脑默认延音规则。重载后请松开再踩。UI 提示更新，参数数量、名称／ID、旧工程状态格式不变。
- 物理踏板极性需要键盘正确发送“松开 0、踩下 127”；软件不猜测极性，也不从最后一条事件自动学习默认状态。

验证与部署记录：`target/pedal-baseline/`。引擎新增 224 组阈值／通道用例及踩住时切换、持音、显示隔离、清理测试；CLAP probe 独立验证实际二进制的踏板消息。真实踏板听感需部署后由用户确认。

## 之前版本记录

# Chord Lab CLAP 0.2.10

## 2026-10-18：增加外围留白

- 在 `theme.toml` 的 `[editor]` 增加 `padding_x = 18`、`padding_y = 10`。默认窗口从 884×683 扩至 920×703，内部画布仍为 884×683。左右边距变为 36 px，上方变为 20 px，下方额外增加 10 px。
- 最小／最大窗口尺寸同步增加留白，原画布可调整范围不变。S/A 点击区域和错误提示随画布一起平移，保持与调性条对齐。
- 不缩放字体、胶囊、音符或图表；S/A 圆形、MIDI 行为、参数和工程状态格式不变。

验证与部署证据：`target/editor-padding/`，包含备份、Python／CTest 日志、CLAP probe 和前后截图。

## 之前版本记录

# Chord Lab CLAP 0.2.9

## 2026-10-18：S/A 圆形指示内缩

- 按最终方案保留两个独立圆形；半径与选中的小胶囊一致，不再贴满外围底槽：`(29 - 2*3 - 1)/2 = 11 px`。
- 统一读取 TOML 的 `choices.inset`，生成 JUCE 的 `selection_inset`。原 29 px 点击区域不变，圆形几何边界内缩 3.5 px，两圆之间留 7 px 空隙。
- 外围底槽、字体、红绿配色、点击范围和全部 MIDI／快捷键行为不变。

验证：540 项 Python 测试，新增内缩 2/3/4 共用配置及非法值校验；完整 CTest、安装后二进制 CLAP 检查与部署记录见 `target/state-pill-inset/`。修改前插件、工程及前后截图均保留。

## 之前版本记录

# Chord Lab CLAP 0.2.8

## 2026-10-18：实体键盘同音重新触发

- 实体 MIDI channel 1–14 每次 Note On 都触发发声，包括电脑和弦已经按住的同音；保留原始力度、通道和采样时间位置。
- 同通道同音重复／共享时，在同一采样位置发送 Note Off → Note On，不再吞掉新按键，也不堆积没有配对释放的音源声部。反过来，电脑和弦也会重新触发实体键盘按住的同音。
- 两边的按住状态仍分别记录：先松开任何一边，不会误停另一边；最后一边松开才释放。这是共享同音的持有关系，不是两个独立持续声部。
- 吉他 channel 15 仍仅显示；UI、键位、参数和工程状态格式不变。

验收：新增回归在旧引擎复现失败，修改后通过 1,792 组实体音高／通道组合、2,016 组混合输入组合（12 调、7 级、3 种和弦、钢琴／吉他模式及两种按下／释放顺序）；8 项 CTest、532 项 Python 测试和二进制 CLAP probe 均通过。probe 检查精确力度／时间、Sustain、两种释放顺序及吉他隔离。日志与更新前备份：`target/midi-retrigger/`。

## 之前版本记录

# Chord Lab CLAP 0.2.7

## 2026-10-18：胶囊边缘精调

- 修正 LICE 圆形的包含端点像素语义：圆端半径改为 `(height-1)/2`，圆心与矩形像素对齐，右圆心同样减去端点像素。不再使用会向下／向右凸出的 `height/2`。
- 记忆标记改为和弦文字旁的 ` *`，参与整串文字的测量、缩放与居中；删除边缘小点。
- S/A 改为两个独立圆形，保留原红／绿与白字；半像素内缩使半径与底槽一致，相邻圆不重叠。
- 键位、MIDI、音源和吉他单音检测不变。

验收：532 项 Python 测试、7 项 CTest 与安装后 CLAP probe 通过。新增 `capsule_pixels` 直接运行 JSFX/LICE 绘制，覆盖 23/29 px 高度、圆形及多种胶囊宽度，检查矩形边界外无任何亮像素、上下和左右镜像一致。备份与部署截图：`target/pill-polish/`。

## 之前版本记录

# Chord Lab CLAP 0.2.6

## 2026-10-18：连续胶囊选择条

- 调性与和弦两行统一为 29 px 高度，共用字号（基准 10 × font_scale），在窄窗口中一起缩小，选中不再加粗或改变字号。
- 两行各是一条连续圆端底槽；选中项为内嵌胶囊，上下留 3 px。点击区域仍连续，首尾可正常选择。S/A 的外接区域仍为等高方形；最右 A 的外轮廓随整条的右圆端收口。
- 小白点是 `saved[degree*4]` 记忆标记：修改和弦类型、钢琴转位／音区后自动保存置位，Enter 复位也会置位。它不是发声灯，也不表示当前设置一定不同于默认值；单独移动吉他手位使用另一套记忆，不靠这个标记表示。
- MIDI、吉他手位、H/L、J/K、Enter、Space 与焦点逻辑不变，21 个参数及旧工程状态格式不变。
- 同轮 Guitar Frontend 升级为仅单音 0.2.1，详见 [单音收尾](../guitar_frontend/MONO_ONLY.cn.md)。

验收：631 项 pytest、Chord Lab 6 项 CTest、安装后二进制 CLAP probe 通过；Bitwig 已实际查看两行、点击首尾及中间项，并检查电脑键盘按下／释放。备份、截图与日志：`target/mono-pill-wrapup/`。

## 之前版本记录

# Chord Lab CLAP 0.2.5

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

## 当前更新：Enter 复位与更鲜艳的待奏音符

- **Enter**：只恢复当前和弦在当前模式的默认位置。Piano 为原位、中心 MIDI 60；Guitar 为最靠近配置默认第 11 品的可用把位。
  保留调性、级数、三/七/九类型、其他级数位置及另一模式的记忆。持键时立即换回默认声音；空闲时只记忆、不试听。
  自动记住复位结果，跨重启仍需保存 DAW 工程。需插件焦点且 A 开启，无修饰组合键；Space 仍为 Sustain。
- 未发声的音符由 40% 原色改为 80% 原色，减少中性灰混合，并略微提亮；发声时原色保持不变。
  所有字母仍白色，调内按音保留外侧细白环。光晕宽度 2.5→3.5 px，含白边共外扩 4.3 px；圆点本体和字号不变。
  调外实体 MIDI 仍为灰色及灰色光晕，不改变输入解释。

562 项 pytest、6 项 CTest、真实 CLAP probe 通过。新增 12 调 × 7 级 × 3 类型 × 2 模式共 504 组复位覆盖，
核对持键/空闲复位、不影响其他级数/模式、保存恢复；Enter 连按去重与失焦预按阻断纳入键盘测试。
测试 host 显式设为 stopped，避免 YSFX 默认播放状态阻止换调，使 12 调矩阵真正执行。
Bitwig 两模式实测 H 移位后 Enter，复位与默认画面逐像素相同；已安装共享 CLAP，
重开测试前的 Library 并恢复焦点，工程与备份逐字节一致。本轮未重测实体硬件、全音色或 REAPER。
证据：`target/chordlab-enter-reset/`；源改动集中在 `keyboard-map.txt`、`midi.jsfx-inc`、`theme.toml`、生成器及对应测试。

## 当前配色：更浅的灰色面板

整体背景、Dark 图区及白键底色统一从 `#323232` 提亮到 `#585858`，沿用已有 Bitwig 风格工具栏的中浅灰。
黑键保持纯黑；边线同步提亮到 `#B2B8C0`，八度/次要文字为 `#D1D5DA`，避免背景变浅后失去对比。
音符配色、固定白字、外侧细白边及光晕不变。JUCE 外层底色也由 `theme.toml` 生成，避免残留深色边角。
本节覆盖下方历史记录中的旧背景色；Bright 图区仍保留原来的浅色。

561 项 pytest、6 项 CTest、真实 CLAP probe 通过；Bitwig 6.1.4 已重载并检查背景、琴键、边线、按音与松键，
松键画面与测试前逐像素一致。已保存备份 Library，安装共享 CLAP 并恢复焦点；未更改 MIDI/音量/和弦逻辑，
未重测硬件输入、全音色或 REAPER 宿主。证据：`target/chordlab-light-panel/`。

## 当前视觉：固定白字与外侧光晕

本节覆盖下方历史记录中的黑色按音文字、内嵌白环及强烈明暗切换规则。

- 所有音名字母始终白色；按下/松开时字号和圆点本体半径保持一致。
- 未按下的底色低饱和、略浅；按下后同色系更深、更实，不以大幅亮度差区分状态。
- 实际按下的调内音在圆点外沿显示 0.8 px 细白边，再加两层柔和同色光晕；不侵占文字空间。
  光晕最多外扩 3.3 px，圆点本体大小不变。调外实体 MIDI 保持灰色，带灰色光晕、不加调内白边。
- 钢琴、吉他与谱面共用同一渲染；Bright / Dark 都固定白字。半像素圆点的透明度仅合成一次。
- MIDI、发声、音量、H/L 记忆及 S/A 顶栏未改。食指候选/当前点仍只在 Guitar 模式显示。

修改：`lib/tools/chordlab/theme.toml`、`generate_theme.py`、生成的 `theme.jsfx-inc`、
`ui.jsfx-inc` 和 `tests/test_theme.py`。
553 项 pytest、6 项 CTest、真实 CLAP probe 通过。Bitwig 6.1.4 实测 E 和弦、持键 H/L、松键通过；
返回把位与松键恢复的音符画面逐像素一致，抽查白字像素按下前后相同，光晕确在原圆点外。
已安装共享 CLAP，重开 Library 并恢复焦点；工程与测试前保存备份逐字节一致。
本轮未重测实体 MIDI/吉他、全部音色或 REAPER 宿主。证据：`target/chordlab-note-halo/`。

## 当前操作：取消预选指法高亮

不再有单独的预选/预听步骤，也不再把当前区域的未发声音画成比其他背景音更亮。
背景音阶/和弦音仍保留原来的淡色，实际按下才亮起并显示调内白环；实体 MIDI 的高亮照常。
食指上沿的候选空心点/当前实心点只指示 H/L 的把位，不是额外指法选择按钮。

- 按和弦键：按该和弦当前记住的位置发声；新实例尚未移动时，Guitar 默认取最靠近第 11 品的可用把位。
- H/L：Piano 向低/高移动一个转位步骤，不是把全部音整体升降一个半音；Guitar 向低/高移动一个可用食指把位。
- 可以一直按住和弦同时 H/L，声音和高亮即时更新；松键停止按音高亮。空闲 H/L 只更新记忆，不自动试听。
- 每个级数自动记住位置，不需要确认/保存快捷键；两个模式的位置相互独立。跨重启仍需由 DAW 保存工程携带插件状态，
  这里的“自动记住”不表示插件会自动写入整个 Bitwig 工程。
- Guitar 保留三品区域全部不同音高实际发声规则，用户自行精简；S/A 无缝顶栏、25×25 px 正方形不变。


验证：532 项 pytest、6 项 CTest、真实 CLAP probe 通过；新增两模式 × 七级数的无确认键记忆测试。
Bitwig 实测持键 H/L、松开重按、回到原位全部通过；不同把位的空闲音符画面逐像素相同，
不再存在预选亮色。Library 已保存并恢复焦点，证据及备份：`target/chordlab-no-preview/`。


## 0.2.4 顶栏无缝排列

调性条与 S、S 与 A 的间距均设为 0；调性条自动加宽填满空隙，按钮高度、配色和功能不变。
542 项 pytest、6 项 CTest、CLAP probe 通过；Bitwig 重载后逐像素检查两处接缝全部 25 行连续，
S/A 独立点击正常，已恢复 S 关闭、A 开启。保存的 Library 与旧插件备份、日志、截图：
`target/chordlab-seamless-header/`。


## 0.2.4 当前行为：完整区域发声与实际按音白环

本节覆盖下方旧版的“代表指型、四品区域、仅候选显示、指型外圈”规则；旧记录保留用于追踪。

- **K = Guitar**：选定基准品与后两品，共三个品位（例如 6–8 品）。收集标准调弦六弦在该区域内的
  全部当前和弦音，按绝对 MIDI 音高去重，全部同时发声；同名不同八度分别保留。
  不再限制三个剩余手指、每弦一个音、连续发声弦或六音上限。区域是练习音集，**不是保证可同时按住的实体指法**。
- **H/L**：按住和弦时向低/高候选把位移动，先释放旧音再发新音；到边界不重触发。
  **J = Piano**，保持原有紧密排列、独立记忆与转位逻辑。Tab 继续切换三/七/九和弦。
- 七和弦仍使用用户指定的四类位置族并移调；三/九和弦从 1–14 品候选中选择。
  所有类型都剔除相差一品的相邻候选：优先保留区域内和弦音弦/品位置较多者，平手保留低品；间距至少两品。
  因此 C major 的 Bm7♭5 目前保留 **3、6、10、12、14 品**。这是覆盖率筛选，不是已验证的舒适度排序。
  默认仍就近第 11 品；旧项目若保存已被剔除的位置，就近解析，等距取低品。
- 钢琴、吉他、谱面共用高亮规则：普通背景音淡色，当前区域候选较亮，实际按下的调内音最亮且有**白环**。
  白环来自实际电脑和弦或实体 MIDI 的按音状态，不再静态圈出某个代表指型；调外实体 MIDI 音保持灰色。
  所有图中的相同**绝对音高**同步，同音名但其他八度不会无条件亮。
- 白环画在原圆点边界内，不增大到超过黑键宽度。食指上沿空心/实心位置点保留；S/A 柔和配色不变。
- 不做延时扫弦；全部音同一事件位置发出。更多同时音可能更响，先用较低音源/轨道音量试听。
- 21 个 CLAP 参数和 v3 保存格式不变，稳定 ID 不变。`Voice 1..6` 仍只是前六个音的兼容诊断参数，
  不代表 MIDI 总音数；内部容量为 18，当前完整目录最多 9 个不同音高。实体 MIDI 不重新配音。

实现：`guitar.toml` / `generate_guitar.py` / `guitar_table.jsfx-inc` 存区域音高目录；
`guitar.jsfx-inc` 负责查表和导航，`midi.jsfx-inc` 按实际长度发声并释放全部槽位；
`ui.jsfx-inc`、`theme.toml` / `generate_theme.py` 负责共享高亮和白环。
同一安装供 Bitwig / REAPER 加载，宿主需重载插件；本次不另维护 JSFX 产品。


### 0.2.4 验证记录

541 项 pytest、6 项 CTest、真实 CLAP probe 通过；119 项 Rust 测试及严格 Clippy 也通过。目录覆盖 12 调 × 7 级 × 3 类型，
共 1,520 个区域；独立六弦三品枚举核对实际 MIDI 集合、完整和弦、去重、导航及释放。
额外验证超过六音的混合 MIDI 所有权、Sustain/失焦释放、0 品保存恢复与旧状态导入。
Bitwig 6.1.4 实测持键 0→3→0、J 切换与松键；上下两张指板的 864 个位置检查、
上下钢琴白环检查通过，返回原位画面逐像素一致。Library 测试前保存，测试后重开恢复，
工程文件与备份逐字节一致，A 绿色、S 关闭。证据、旧插件和工程备份：`target/chordlab-region-midi/`。
本轮未重测真实硬件 MIDI/踏板/吉他输入、全部音源音量或 REAPER 宿主；自动 MIDI 注入已覆盖混合输入。

## 0.2.3 界面微调与回归复验

S/A 保留 25 px 方形与白字；关闭改为低饱和红 `#94646A`，开启改为低饱和绿
`#567962`。字号 16→14，取消粗体，悬停提亮减弱；普通与悬停状态白字对比度均 ≥4.5。
这是同一版本的样式更新，不改变七和弦把位、MIDI、按键或状态格式。

修改前 531 项 Python、6 项 CTest 和 CLAP probe 通过；修改后 534 项 Python、6 项 CTest、
真实 CLAP probe、119 项 Rust 测试和 `cargo clippy --offline --all-targets -- -D warnings` 通过。
覆盖 252 种和弦 / 1725 个指型、持音换位、混合输入、状态恢复及 GUI 生命周期。
Bitwig 重载后实测 S/A 点击、Space、失焦/恢复及像素配色通过；Library 已保存并恢复焦点。
本轮没有重测实体 MIDI/踏板/吉他输入或全部音源听感，也未重新打开 REAPER 做宿主实测。
日志、截图、安装 hash 和备份：`target/chordlab-soft-controls/`。

## 0.2.3：用户指定的七和弦把位

Guitar 七和弦改用用户提供的 Cmaj7 / Dm7 / G7 / Bm7♭5 食指位置族，
按根音平移、每 12 品重复；H/L 与上沿位置点使用同一目录。三和弦、九和弦不变。
开放位 0 品可保存恢复；旧项目中不再列出的把位就近显示，等距取较低位置。
半减七的位置暂按口述保留 2、3、6、7、9、10、12 品，6/7 不合并，仍待用户实弹校准。
[完整位置表与边界](GUITAR_VOICING.cn.md#用户指定的七和弦把位023)。
531 项 pytest、6 项 CTest、CLAP probe 及 Bitwig 标记/持音 H/L/换调检查通过；
证据与安装前备份在 `target/chordlab-user-anchors/`。未做新的硬件或全音色验收。

## 0.2.2：S / A 方形状态按钮

右上角改为 25 × 25 px 方形按钮，与相邻调性按钮等高：**S = Sustain**，
**A = Active**。白色字母，深红关闭、深绿开启；A 仅在电脑键盘启用且插件获得焦点时为绿。
点击、Space 切换 Sustain、焦点同步与实体 MIDI 行为不变。
428 项 pytest、6 项 CTest、CLAP probe 通过；Bitwig 实测点击、Space 与焦点切换通过。
证据和部署前备份：`target/chordlab-square-controls/`。本轮不是全音色或硬件重测。

## 0.2.2：吉他把位内全部和弦候选音

下组指板突出显示食指起四品内六根弦的所有和弦音，以及全指板上完全相同音高的位置。
候选亮度介于背景音与实际发声音之间；不增加 MIDI 输出，不恢复谱号旁模式点。
[使用与范围](GUITAR_VOICING.cn.md)。

### 0.2.1 后续界面精简

移除谱号旁的两个 Piano/Guitar 模式点、鼠标点击区域、悬停提示和 `Fret n` 文字。
J/K 模式切换与下组指板上沿的空心/实心食指位置点保留；音符与 MIDI 行为不变。

## 0.2.1：食指位置点

Guitar 模式的下组指板上沿新增候选空心点／当前实心点，大小与下方品位点一致。
位置随 H/L、调、级数和和弦类型更新；MIDI 与指型目录不变。
[说明与范围](GUITAR_VOICING.cn.md#食指位置点021)。

## 0.2.0：钢琴 / 吉他双 voicing

**H/L 移动，J 选择 Piano，K 选择 Guitar**；替代旧 G/V。
保留原钢琴转位，新增标准调弦、食指横按加三指的完整和弦指型。
两种模式分别记忆位置，新增实心/空心模式点和实际指型外圈。
[使用方法、实现与验收边界](GUITAR_VOICING.cn.md)。

## 2026-10-18：最终键盘配色——灰白键、纯黑键

按用户后续确认，Dark 白键恢复为与背景一致的 `#323232`，黑键外层与内层均为
纯黑 `#000000`。覆盖下面历史记录中的“黑底白键”方案。分隔线、外框、音符高亮、
Bright 模式和 MIDI 行为不变。118 项 pytest、4 项 CTest、CLAP probe 通过；
证据与部署备份：`target/chordlab-gray-white-black-keys/`。

## 2026-10-18：Dark 白键黑底

两组钢琴的白键底色改为纯黑 `#000000`，保留原有 2 px 分隔线与外框。
新增独立 `key_white` 主题色，不改变黑键、谱面、指板、音符高亮、几何位置或 Bright 模式。
这是 0.1.10 的资源更新；重新加载插件后两宿主共用。已部署并重启 Bitwig，实际检查
两组键盘以及电脑 C 键按住 / 松开时的高亮。118 项 pytest、4 项 CTest 和 CLAP probe 通过。
证据及旧安装件备份：`target/chordlab-black-white-keys/`；不是新一轮全音色或硬件验收。

[当前跨 DAW 状态、安装位置与收尾总结](../bitwig_library/WRAPUP.cn.md)。下文历史版本记录保留；
当前使用 Space Sustain、H/L 转位、J/K 模式与 S/A 方形状态按钮，Dark/Bright 随插件实例保存。

[旧产品清理与复查](RETIREMENT.cn.md)

[0.1.5 左手键位与全量回归](LEFT_HAND.cn.md)

[0.1.4 焦点同步验收](FOCUS_FIX.cn.md)

0.1.4 修复 Keyboard 焦点指示：启用且有焦点时浅绿，失焦或手动关闭时浅红。
失焦不改变启用偏好；点击回到编辑器恢复，手动关闭后须点 Keyboard 开启。
0.1.3 已移除 Panic 入口及其提示；关闭窗口、关闭 Keyboard 等自动释放保护不变。

[0.1.2 双按钮更新验收](controls_acceptance.json)

[0.1.1 字体校准与 Core 试奏工程](UI_CALIBRATION.cn.md)

[English](README.md) · [通用 ysfx 样机历史](PROTOTYPE.cn.md)

[混合输入、灰点与 Input FX 使用指南](MIXED_INPUT.cn.md)

## 当前维护路线：CLAP

- 原生 JSFX + Lua/VKB 产品入口、安装器和旧 binary 已删除，不再维护双版本；历史验收只作迁移基线。
- `../chordlab/` 中的 EEL/JSFX 文件现在仍是 CLAP 内嵌引擎的源码位置；修改后需重建、部署 CLAP，不代表继续维护两个产品。
- 日常音色库已迁移到单个共享 CLAP，见 [迁移与使用](../library/CLAP_MIGRATION.cn.md)。
- 新版：专用 `Chord Lab.clap`，稳定 ID `org.utrp.chordlab`，内含 ysfx 引擎、
  **8 个 EEL/JSFX 引擎文件**（UI 已为 CLAP 双按钮预留空间）、谱号图片和图片许可证。
- 新版自行接收电脑键盘，不需要 Lua 会话或 REAPER VKB。不是另一套和弦算法。
- MIDI-only：放在乐器前面。插件本身不合成声音、不改变总音量、不包含 Surge 音色。

## 快速使用 / 人工验收

正式音色库已切到唯一共享 CLAP Input FX；其他项目先备份，再把插件放在音源前面。

1. REAPER FX 搜索 **Chord Lab (UTRP)**。若尚未扫描，重新扫描 CLAP 或重启 REAPER。
2. 监听链为 `MIDI input → Chord Lab CLAP → Surge / piano instrument → effects`。
   若要录入生成后的和弦 MIDI，在 REAPER 把 CLAP 放在 **Input FX**；正常轨道 FX
   默认录到的输入不等于 FX 生成的输出。
3. 启用轨道录音准备和输入监听，选择实体 MIDI 设备。实体 MIDI 使用 channels 1–15；
   channel 16 保留为 Chord Lab 控制协议。实体键盘力度保持原样，电脑和弦默认力度 64。
4. 旧 JSFX + Lua/VKB 独立产品已弃用，不与 CLAP 串联，也不再双版本同步开发。
5. 右上角为 **S（Sustain）**、**A（Active）** 两个白字方形按钮：柔和绿开启、柔和红关闭。
   A 绿色表示电脑键盘启用且窗口有焦点；失焦变红，点击回到插件自动恢复绿色。
   手动关闭后，单纯恢复焦点不会开启；需再点 A。
   实体 MIDI 不受 A 开关影响。
6. 不提供 Panic 按钮或右键菜单；顶部快捷键说明已移除，
   提示改为悬停显示。加载错误仍保留可见提示，不会隐藏故障。

| 操作 | 验收 |
| --- | --- |
| Q W E R T Y U I O P [ ] | 12 调切换；持音或 transport 播放中按原规则锁定 |
| Z X C A S D F | vi、viiø、I、ii、iii、IV、V（6、7、1、2、3、4、5）；按住发声、松开停止 MIDI 持有 |
| H / L | 钢琴转位 / 吉他把位向低、向高移动；可持键操作，自动记忆 |
| J / K | 直接选择 Piano / Guitar 模式 |
| Tab | 三 → 七 → 九 → 三；当前级数立即记忆 |
| Space / 鼠标 Sustain | 切换 Sustain ON/OFF；Space 按下触发，长按不重复；锁定时踏板释放不能撤销锁定 |
| 两个和弦键重叠 | 后按优先，松开后返回前一个仍按住的和弦 |
| 切去其他级数再回来 | 恢复该级数的和弦类型和位置；无需额外保存键 |
| 保存 RPP、关闭、重开 | 和弦记忆恢复；Sustain 按安全规则恢复 OFF |
| 切到 DAW / 其他窗口 | 释放插件生成音符；重新点击插件后可以继续弹 |
| 点击绿色 Keyboard | 清理生成持音和 Sustain，停止接管按键；点按钮重新开启 |
| 关闭编辑器 | 清理电脑持音和 Sustain；插件 MIDI 处理仍留在轨道上 |

**先松键再切窗口最稳妥。** 在插件失去焦点后继续按住按键，操作系统自动重复可能
触发 DAW 的同名快捷键；插件不跨窗口拦截它们。Ctrl/Shift/Alt/Cmd 组合键不作为插件命令。
Shift 与 Ctrl 均不执行单键命令。Space 可以和和弦键一起按；Ctrl/Shift/Alt 等修饰组合仍不触发。
旧 Esc/Ctrl/H/J/K/L/分号/Enter 功能已取消。
无修饰键在 启用且有焦点时优先由插件消费（包括 Space），前提是宿主把事件送给插件。
宿主明确设为 global 的快捷键、系统快捷键不能由 CLAP 无条件覆盖。

观察上下两组谱表、钢琴和吉他指板：颜色、音高、按住高亮应与原 JSFX 相同。
这是 MIDI 状态显示，不追踪乐器的 release / reverb 尾音。失焦发 Note Off 不等于
关闭 Sustain 或强制截断声音；需要清理电脑输入时关闭 Keyboard。

## 验收证据与“100%”边界

本轮 0.1.6 的结果与 binary 哈希见 `retirement_acceptance.json`、[清理与复查](RETIREMENT.cn.md)
及 `target/chordlab-retirement-0.1.6/`。
历史 0.1.5 的结果与 binary 哈希见 `left_hand_acceptance.json` 及 `target/chordlab-full-0.1.5/`。
原始移植结果、binary 哈希、逐项范围见 `acceptance.json`；对应历史本机证据保存在
`target/chordlab-clap-release/`。历史 `validation.json` 只属于旧通用样机，不能
当作专用版结果。

测试覆盖：
- REAPER 原生 JSFX vs CLAP：12 调 × 7 级数 × 三/七/九和弦及转位、复位、记忆，
  velocities 1–127 / channels 1、15，重叠持音、Sustain/踏板、pitch bend、CC、
  Channel/Poly Pressure、Program Change；逐条比较 MIDI 字节、顺序和 block 内 offset。
- 真实 RPP 保存、关闭、重开；宿主参数写入与原 JSFX 对照。
- 独立 CLAP ABI host：端口、18 参数、默认值、X11 GUI 支持、8 次参数写入、
  44.1/48/96 kHz × 32/64/256/1024 frames，短 MIDI、Clock、SysEx、reset/reactivate、
  跨实例 state 恢复且不含临时 JSFX 路径。
- 键盘状态机与队列单测：重复 key-down 不重复触发、释放/失焦、满队列和发送失败安全清理。
- 独立 headless Sway/XWayland 下的真实鼠标、键盘事件和界面截图。

**通过上述测试不等于所有宿主、硬件、时序的数学等价证明。** 仍需用户实测的部分：
实体 MIDI/Spark GO 音频、真实桌面快捷键设置、长时间演奏、HiDPI/多屏、Bitwig、
macOS/Windows、离线 render、异常卸载/整条 FX chain bypass、录制路由和所有 transport
组合。未实现 CLAP 原生 note expression / MIDI 2.0 / polyphonic modulation；普通
MIDI 控制器透传不等于这些能力。REAPER 多 MIDI bus 不在本轮单端口模型内。

原版 Lua 的音色库/选轨/Surge 窗口配对、VKB 独立窗口、录音 transport 快捷键并没有
变成插件功能。旧 JSFX 的 RPP chunk 也不会自动转换成 CLAP state；先保留原工程。
CLAP 内部的和弦记忆可随新工程保存；不同 DAW 的整个工程不因此互通。

## Bitwig 静态兼容判断

**接口路线可行，未做 Bitwig 实机认证。** Bitwig 官方明确支持 CLAP 插件与原生设备
共同组成设备链；推荐目标链是 `Chord Lab → Surge XT / 其他跨宿主乐器 → effects`。
[官方插件说明](https://www.bitwig.com/userguide/latest/vst_plug-ins/)

当前 binary 为 Linux x86_64；暴露一进一出的 MIDI note port、零 audio port、稳定参数、
state、X11 editor，不依赖 REAPER API、Lua、跨进程 gmem 或原机器 JSFX 目录。
每个实例自行释放资源。Bitwig 支持不同插件隔离模式，首次验证可用 Individually。
[官方隔离模式](https://www.bitwig.com/userguide/latest/vst_plug-in_handling_and_options/)

Bitwig 后续必须验证：扫描分类、MIDI 通道和后级发声、键盘焦点/全局快捷键、保存重开、
录到生成后的 MIDI、transport/suspend 和多实例。不要强制启用 MPE：channel 16 已保留。
本次 Linux binary 不能直接放到 macOS；需要另外构建和验收。

## 实现与修复

依赖固定在 `dependencies.toml`，准备脚本先核对所有 archive SHA-256。
`port_upstream.py` 对固定 ysfx 源做有断言的薄适配，`prepare_build.py` 修 CLAP MIDI 输出：

1. 短消息和 SysEx 不再被仅接受三字节消息的分支丢掉。
2. 构造时加载固定脚本和 18 参数；音频处理先消费 host 参数写入，避免延迟通知到达前
   被旧 slider 值覆盖；按 REAPER 规则量化步进参数，包括半步进边界。
3. 内嵌资源、独立临时目录、去路径化 state；输入有界队列，音频线程注入 MIDI，
   溢出触发清理。0.1.6 在 Linux 使用有序 X11 按键/焦点事件与 detectable auto-repeat；
   持键只认真实释放，避免物理快照早于排队重复事件而重复触发。只在切换焦点/未接管时
   同步物理状态；失焦释放持音并取消修饰键，重新聚焦不触发已按住的键。

`CheckingLevel=Minimal` 保留基础契约检查。固定版本 helpers 的 Maximal flush 检查
会在合法 audio-thread flush 中查询 main-thread-only 参数元数据，产生错误线程日志；
不在音频线程启用这项调试检查。参数值仍校验有限数与范围。

## 构建与复现

依赖：Python 3.11+（archive 解压需要支持 `tarfile` data filter）、CMake 3.22+、C++17、
Ninja、X11/Freetype/ALSA 等 JUCE Linux 开发库。已验证 GCC/Linux，不是跨平台构建保证。
下载 `dependencies.toml` 的六个 URL，分别保存为 `<name>.tar.gz`；准备过程离线运行。

```sh
python lib/tools/chordlab_clap/prepare_build.py \
  --downloads target/chordlab-clap-build/downloads \
  --output target/chordlab-clap-build/deps
cmake -S lib/tools/chordlab_clap -B target/chordlab-clap-build/build -G Ninja \
  -DCHORDLAB_DEPS="$PWD/target/chordlab-clap-build/deps" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
PYTHONPATH=lib/tools/chordlab_clap python -c "from pathlib import Path; from prepare_build import assets; assets(Path('lib/tools/chordlab'), Path('target/chordlab-clap-build/deps/chordlab.zip'), Path('lib/tools/chordlab_clap/prototype.toml'))"
cmake --build target/chordlab-clap-build/build -j 2
ctest --test-dir target/chordlab-clap-build/build --output-on-failure
python -m pytest lib/tools/chordlab_clap lib/tools/chordlab/tests -q
```

`prepare_build.py` 拒绝覆盖已有输出；已准备好时不要再次运行。
产物：`target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap`。
独立 host（需要正常 X11/XWayland DISPLAY）：

```sh
target/chordlab-clap-build/build/clap_probe \
  "$PWD/target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap"
python lib/tools/chordlab_clap/stage_port.py --plugin \
  'target/chordlab-clap-build/build/ChordLab_artefacts/Release/CLAP/Chord Lab.clap' \
  --output /tmp/chordlab-new-test
```

使用生成的独立 HOME、`-cfgfile .../reaper/reaper.ini`、`prototype.rpp` 启动 REAPER；
依次运行 `ab_test.lua`、`state_ab.lua`、`parameter_ab.lua`，查看对应 result 文件。
Dummy Audio、48 kHz/256、无真实硬件输入；不要用会改正式配置的个人 launcher。
脚本带 scratch 路径与空工程保护。阶段输出目录必须不存在。

## 许可证与分发

ysfx source 带 Apache-2.0；JUCE 8 modules 为 AGPLv3 / commercial 双许可；
CLAP/adapter 为 MIT；谱号素材保留自己的许可证。旧 ysfx binary ZIP 的 AGPL
许可与 source library 许可不是同一层。这里只做本地构建和使用，未对外发布。
对外分发时应一并提供适用许可、所需完整对应源码和构建资料；不要只发一个 binary
并宣称它不受 JUCE 的许可约束。实际依赖 LICENSE 保存在构建目录和本机 release 留档。

## 直角状态按钮（2026-10-17）

Sustain / Keyboard 使用与其他控件一致的 25 px 高平面直角矩形，取消圆角和描边，
保留浅红 Off / 浅绿 On。仅替换按钮绘制，不修改点击、焦点、Sustain 或 MIDI 行为。
77 项 Python、3 组 CTest 和真实 CLAP probe 通过；Bitwig 中点击切换两按钮，
截图逐像素核对两种状态的四角均为状态色。工程已保存、重开，窗口恢复并排。
证据：`target/bitwig-flat-buttons/`。

CLAP SHA-256: `2b0379c201f6ca996d04f995c25777b61050c267fbb578ae6ba57cf9b9096b6e`.

## Dark / Bright 外观（0.1.7，2026-10-17）

在图示区域内右键，选择 **Appearance → Dark / Bright**。默认 Dark。
选择随插件实例保存进工程，不是全局偏好。Dark 使用与 Bitwig 匹配的 `#323232` 背景、
浅灰黑键形状、低亮度键盘分隔线、浅色吉他弦/五线谱/谱号；未演奏的音点降低亮度，
正在演奏的和弦角色色保持不变。Bright 恢复浅色图示。Sustain / Keyboard 保留方形红绿按钮。

Appearance 追加为第 19 个参数，原有 1–18 参数 ID 不变；实际旧 Library 状态载入通过，默认 Dark。
打开菜单时释放电脑键盘按住的音并暂停键盘捕获；普通主题参数切换本身不产生 MIDI。

验证：97 项 Python 测试、3 组 CTest、实际 CLAP 生命周期/状态/GUI 探针、12 组采样率与块大小、
混合 MIDI 持续按音期间切换主题均通过。在 Bitwig 实测两种配色和谱号显示，Bright 随 Library
保存并重新打开后仍保留；最后已恢复 Dark 并保存，检查焦点与 Sustain 状态显示。
新 DAWproject 导出的 95 个原音源状态全部匹配，project/metadata XML 中无中文。
本轮**不是**重新完成 98 音色发声或 Spark GO 实机验收；待用户认可外观后再做。

证据：`target/chordlab-dark/`。部署 CLAP SHA-256：
`bbc873f8efd93ae7b3c78d0788dd4ce900ff70d4947825c5cac855ec3db83a36`。

### Dark 配色微调（2026-10-17）

Dark 黑键由浅蓝灰改为中性灰 `#737373` / `#828282`；根音/三音/五音/七音/九音使用更亮的
红/绿/橙/蓝/紫，外部按音灰点也提亮。未按音点采用 45% 角色色与 55% 背景混色
（原为 35% / 65%），按下后仍有明显更高的亮度，并用深色字保证对比。
Bright 配色、键位、MIDI 行为均未改变。这是 0.1.7 的资源配色修订。

104 项 Python 测试、3 组 CTest、CLAP 旧状态/混合 MIDI 探针通过。
已保存、备份并重启 Bitwig，实际检查电脑和弦键按住/松开的亮度变化；截图位于
`target/chordlab-brighter/`。最终工程已保存为 Dark。
CLAP SHA-256：`143c91fcf39d6c42b7e1d474f8b857dd7a83e411d2147b105aec46fff2e598e6`。

### 外框小圆角（2026-10-17）

编辑器外框增加 8 个逻辑像素的小圆角；采用不透明中性深灰衬底，不依赖宿主窗口透明支持。
仅在 EEL 图示绘制后遮罩外框角落，内部方形按钮与图示布局不变。半径和衬底色配置位于
`../chordlab/theme.toml`；编译前运行 `python lib/tools/chordlab/generate_theme.py`
生成 `editor_theme.h`。114 项 Python 测试、3 组 CTest、CLAP 窗口缩放/重建、
旧状态与混合 MIDI 探针通过。已保存、备份并重启 Bitwig，检查四角像素、抗锯齿及电脑
键盘输入。证据：`target/chordlab-rounded/`。
CLAP SHA-256：`ca46e3cf77d8592a9bc8867d19a73ece9566350f379a43875252605d335b675f`。

### Dark 图示分隔线加粗（2026-10-17）

Dark 钢琴白键分隔线与向内绘制的完整外框改为 2 px，吉他品丝分隔线也改为像素对齐的
2 px，琴枕仍为 3 px；灰色统一匹配五线谱线 `#9098A1`。Bright 模式、琴键几何、
音点中心与颜色、MIDI 行为不变。theme.toml 中 `dark_diagram_line_width` 配置线宽
（整数 1–3）。122 项 Python 测试、3 组 CTest、CLAP 状态/GUI/MIDI 探针通过。
已保存备份、重启 Bitwig，检查按住/松开和弦显示，并像素核对实际 2 px 分隔线。
证据：`target/chordlab-thicker-lines/`。CLAP SHA-256：`ec2192cc4e2389e97e2fe3439ba14fcc28bdf2851df71ab120a80b78630e0625`。

> 2026-10-18：上文圆角遮罩方案已撤销，以下更新为准。

### 干净边缘与关系小调标签（2026-10-18）

撤销不透明 8 px 圆角遮罩及生成的 `editor_theme.h`：它在宿主的不透明矩形父窗口中仍留下
黑角，因此恢复干净直角。Dark 图示线宽、音点大小和 Bright Mode 保持不变。
第一行改成小调优先的成对标签（`Am/C`、`Bbm/Db` 等），自动适配现有按钮宽度。
仅调整关系调名称；和弦级数、音色、配音记忆及参数 ID 不变。

换调命令在 `sliderchange(1)` 外增加 `slider_automate(1)`，把参数变化通知宿主。
固定版本 CLAP adapter 的全局参数事件还需将 note_id/port/channel/key 全部设为 -1，
不能保留零；`prepare_build.patch_global_parameters` 在全新构建时应用并检查此补丁。
新增真实 CLAP probe 验证换调输出事件，旧版 note 0 定向事件会被明确拒绝。
Bitwig 工程 Root Key/Scale 联动见 `../bitwig_library/README.cn.md`。
同一批 UI 参数/gesture 事件同时标记 `CLAP_EVENT_IS_LIVE`，probe 也检查这个标志。

## 0.1.8：持键转位与点击焦点

按住 C（或 Z/X/A/S/D/F），点按 G 向右上移动，点按 V 向左下移动；
和弦保持发声，每次真实按下移动一步，长按的系统重复不会重复移动。
Esc 与 Ctrl 不再移动。Shift 仍须单独松开才切换 Sustain；Space 和 Tab 不变。

本机已按用户确认将 Sway 设置为 `focus_follows_mouse no`：鼠标经过其他窗口
不切换焦点，点击或焦点快捷键才切换。该设置作用于整个桌面，不是插件抢焦点。
真正失焦时 Keyboard 仍变红并安全释放电脑持音。
验收记录见 [G/V 与焦点验收](GV_FOCUS.cn.md)。

## 0.1.9：Space 切换 Sustain

Space 每次真实按下切换一次 Sustain，可与和弦键一起操作；长按和松开均不额外切换。
取消 Shift 单键动作，以及原 Space 恢复默认位置的快捷键。G/V、Tab、鼠标 Sustain、
点击切换焦点和实体 MIDI 路由不变。上方 0.1.8 及更早验收段落仅记载历史版本。

0.1.9 验收：118 项 Python、4 项 CTest、199 项键盘检查及 1012 种双键顺序通过。
新增真实 CLAP 检查 Sustain 按下切换、重复/松开不切换、不重置和弦；原 G/V、旧状态、
混合 MIDI 与 GUI 生命周期检查通过。Bitwig 实测 Shift 无动作，Space 按下/长按/松开保持 On，
再次按下 Off，Shift+Space 不触发。已保存并重新加载 Library。
证据：`target/chordlab-space-sustain/`；安装 SHA256：
`3ceeeb44218c56ad1ad67a5a8506c80e130c10fd782a48f760450350848e8971`。

## 0.1.10：圆点状态按钮与提亮音符

右上角左点 Sustain、右点 Keyboard；14 px 圆点、25 px 点击区域，深红 Off / 绿色 On。
不显示按钮文字，名称与说明保留在悬停提示和可访问名称中。两个圆点与调性按钮同一水平线，
12 个调性按钮扩展至剩余宽度；原点击、Space、G/V、焦点处理不变。
Dark Mode 的未按音符混色从 45% 提至 55%，按下颜色也略提亮；保留按下/未按的亮度差。

### 修改如何同步到 DAW

`theme.toml` 是主题和圆点布局的单一配置来源。CMake 会生成 EEL 主题与 C++ 圆点样式，
重新打包当前引擎资源进 CLAP；不再依赖另一次手工打包来同步界面。
本机 Bitwig 和 REAPER 共用 `~/.clap/Chord Lab.clap`。修改源码不会即时改变已加载插件：
需要编译、部署，然后保存工程并重新加载插件（当前采用安全重启 DAW）。
旧项目仍用相同 CLAP ID，加载新 binary 的资源并恢复原参数／和弦记忆，无需逐轨替换。
另一台机器则需另外复制兼容平台的 binary；不是跨机器云同步。Bitwig 项目和 REAPER 项目仍是独立文件。

0.1.10 验收：127 项 Python、4 项 CTest、真实 CLAP 状态／GUI／混合 MIDI／键位探针通过。
已部署并保存、重启 Bitwig Library，实测两圆点点击、悬停提示及持键 G/V；音符亮度截图复核通过。
当前 Library 的 controller 调性联动实测：Bbm/Db → B♭ Minor、G#m/B → G# Minor，
最后恢复 Am/C → A Minor、Sustain Off、Keyboard On 并保存。
该联动依赖 Library controller 和 Project Remotes，不是 CLAP 自动控制任意宿主调号，
也不会自动移调已录制片段。本轮未重新逐个验收全部音色或实体 MIDI 键盘。
REAPER synth.rpp 与 Guitar Frontend binary 的哈希保持不变。
证据：`target/chordlab-dot-ui/`；安装 SHA256：
`ea232a33fe70c9e3bf5719cf899ac90f5c0eb59fb9132cfee28c0a43e28ed044`。

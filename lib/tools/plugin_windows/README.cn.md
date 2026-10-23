# Bitwig 插件浮窗布局

让插件编辑器保持 floating，Chord Lab 与主音源／主效果器成组居中，保留左边轨道区。
这是 Sway 桌面窗口工具，不是插件 DSP 或 Bitwig controller 功能。

## 规则

- 仅处理进程名为 `BitwigPluginHost-*`、父窗口是当前 Bitwig 主窗口、标题含 ` / ` 的插件编辑器。
  不移动 Bitwig 主窗口、普通应用、文件对话框、REAPER，也不操作 scratchpad。
- 仅 Chord Lab 时居中；与 Surge XT／sfizz 或最先打开的主要效果器组成中央组，Chord Lab 在左。其余效果器先找中央组右侧空位，再使用周围空间。
- 新增窗口能放下时中央组不动；若固定居中造成空间碎片，则尝试整组紧凑排布后居中，仅在能容纳更多窗口时采用。左侧轨道保留区优先于严格屏幕对称。
- 默认左侧保留 400 logical px，顶端 80 px、底端 48 px、右边 16 px，窗口间隔 16 px。
- 切换 floating／取消插件 fullscreen，再移动窗口。仅 Surge XT Effects 有例外：新开窗或残留超出可用区的巨大尺寸时，恢复 600×490（配置可调）；它有时会记住 tiling 撑大的尺寸，不能只靠 floating 自动恢复。Chord Lab 由下述原生开窗规则恢复 920×703；其余插件不调用 resize；不修改 Surge XT 音源的内部 zoom、音色或工程路由。
- 每 0.4 秒检查一次。仅新增、关闭、标题／尺寸／工作区变化时重排；鼠标移动、点击焦点、手动拖动不触发重排。
  所以手动拖动可以保留到下次布局变化，**不是永久固定位置**。
- 不改变焦点、不移动到其他 workspace、不自动打开／关闭插件。
- 放不下时通知并保留溢出窗口，不缩小、隐藏或关闭。有限屏幕无法承诺任意数量窗口无重叠。
- 每个工作区独立排布；纯计算测试覆盖不同坐标原点，实际只验收了当前 3440×1440 单屏。

## 文件与使用

- 源码和配置：本目录 `layout.py`、`layout.toml`。
- 服务：`~/.config/systemd/user/utrp-plugin-windows.service`，已 enable。
- 启动入口：`~/.config/sway/utrp-plugin-windows.conf`，由现有 Sway config include。
  config 本身是 `~/work/gral/arch/sway/config` 的软链接；仅追加了 include，没有替换其他规则。
- Sway 启动／reload 时先导入新 `SWAYSOCK` 再启动服务；无须重启 Bitwig。
- 调整留白或间距：编辑 `layout.toml` 后执行 `systemctl --user restart utrp-plugin-windows.service`。
- 临时停用：`systemctl --user stop utrp-plugin-windows.service`（Sway reload 会再次启动）。
- 永久停用：移除 config 中上述 include 并 `systemctl --user disable --now utrp-plugin-windows.service`。
- 没有窗口标题栏时，沿用 Sway 的 `Super + 鼠标左键拖动`；在 Bitwig device 面板用插件窗口按钮开关窗口。
- 此布局是本机设置，不包含在 `.bwproject` 或 CLAP 内。换机器需要单独部署。

## 2026-10-18 验证

- 原因复现：Surge XT Effects 被 tiling，主窗口宽度被挤到 1720；floating 后恢复 600×490，主窗口恢复 3440×1440。
- 真实四窗口：Chord Lab 920×703、两个 Surge XT Effects 各 600×490、Dragonfly Hall 920×345；两排无重叠。
- Surge XT 音源（当前原生 1141×711）、sfizz（775×515）均与 Chord Lab 无重叠。未改变其缩放设置。
- 已测试 FX 关闭／重开、手动拖动保留、焦点不被抢走、服务重启；Sway config validation 通过。
- 单元测试覆盖右向左、换行、越界／空间不足、工作区隔离、识别范围、300 组随机布局不变量；`mypy --strict` 通过。
- 证据在 `target/plugin-windows/`（不进 Git）；没有为本轮窗口测试注入音频或修改任何音色参数。

参考：[Sway 官方命令文档](https://github.com/swaywm/sway/blob/master/sway/sway.5.scd)。

## 乐器组合复验 — 2026-10-18

发现并修复了按创建顺序贪心排布导致的空间碎片问题：某些五窗口组合先开小 FX、后开大音源时，虽然有可行布局仍会误报满屏。现在保持 Chord Lab 靠右，其余按高度、宽度降序排列，再以创建顺序打破平局。

新增 11 类真实尺寸组合的 **340 种打开顺序**回归测试；修复前 20 个用例误报溢出，修复后全部通过。加上现有布局与 Library 测试共 **368 passed**，strict mypy 通过。这不是任意矩形的最优装箱算法；两台大合成器等超出可用区域的情况仍可能放不下。

真实 Bitwig 逐轨复验覆盖：Acoustic Piano、Soft Piano、Suitcase EP、DX EP、Organ、Church Organ、Warm Veil、Dark Choir、Silver Haze，以及 Glass Air、Soft Prism、Echo Bloom、Cloud Halo。每组检查实际窗口数量、floating 状态、可用区边界、两两 16 px 间距与 Bitwig 主窗口尺寸。吉他链改变了效果器打开顺序，包含四窗口换行。

Library 的互斥试听会停用其他音色轨，旧轨插件窗口随之关闭，这是既有控制器逻辑，不是布局工具隐藏窗口。因此跨音色轨同时混合的五窗口组合使用实测窗口尺寸做计算回归，**不声称在当前互斥 Library 内真实同时打开**。证据：`target/plugin-window-combinations/`。

复测跨轨重开时另捕获 Surge XT Effects 记住 1763×1440 的情况；增加仅针对 FX 的开窗尺寸恢复，并覆盖合理手动调整保留、延迟超大尺寸纠正、音源不受影响。之后对 Cloud Halo／Soft Prism 交替三轮重开复验。

## 中央优先更新 — 2026-10-18

以上中央规则替代前两轮右侧锚点方案。Library controller 0.7 在切换到已知音源／吉他音色轨时，打开主设备与共享 Chord Lab；选 raw 等带本地 Chord Lab 的辅助轨时只打开该实例，不改变试听音源。扫描范围为前四台顶层设备（共享轨前两台），不是任意嵌套设备递归。关闭旧轨前四台设备的编辑器，避免前一个效果器遗留。

重新选回同一音色也会重开；controller 依赖 Bitwig 选轨事件，不轮询强制把手动关闭的窗口再弹出。若当前轨已经选中、再次点击没有产生选轨事件，请切到别轨再回来，或点设备的窗口按钮。

新增单窗居中、音源优先、周边容纳时锚点稳定、关窗重排与局部 Chord Lab 测试；340 种组合现在使用真实插件名验证优先级。日志与实机证据：`target/plugin-windows-center/`。窗口布局不改变音频路由。

## 2026-10-21：Bitwig 固定 Workspace 2

`sway.conf` 新增 `assign [class="^com\.bitwig\.BitwigStudio$"] workspace number 2`，部署在现有 `~/.config/sway/utrp-plugin-windows.conf` include 中。所有启动入口创建的 Bitwig 主窗口均适用；不靠启动时所在 workspace，也不改桌面启动器或增加服务。规则仅匹配 Bitwig，不影响其他软件；布局程序仍不负责工作区迁移。

本次将已打开的 Bitwig 主窗口及两个通过 `transient_for` 关联的插件浮窗一起移至 Workspace 2。Sway 配置校验通过并已 reload；未重启音频引擎或修改工程的 Active / Arm / Monitor。规则在新建主窗口时生效，本轮未再次关闭 Bitwig 做启动验收。主配置 symlink 保留。机制见 [Sway assign](https://man.archlinux.org/man/sway.5.en#assign)。

## 2026-10-21：修复 Chord Lab 开窗变大

修复前实机窗口为 1636×1220（插件允许上限）；窗口事件捕获到重新创建时先 `auto_off` 平铺至 1720×1440，再由 0.4 秒轮询切为 `user_on` 浮动。插件源码仍默认 920×703，20 品改动没有增加默认尺寸。仅手动缩小无法消除首次平铺向宿主反馈大尺寸的时序问题；记录不证明每次平铺都会最终停留在最大值。

`sway.conf` 为 Xwayland normal 窗口的精确 ` / Chord Lab` 标题后缀添加原生 `for_window`：**创建时立即 floating，并恢复 920×703**。Bitwig 插件包装窗口没有 WM_CLASS，故不能复用主窗口 class 条件。规则不匹配主窗口或其他插件、不修改音频或插件内容、不增加服务。仅每个新窗口执行一次，后续手动调整大小仍可保留。

配置校验通过；六次真实重开（含共享和 raw detection 两个实例），首次 focus 事件已是 `user_on`、920×703，随后也保持该尺寸与 Workspace 2。证据：`target/chordlab-window-size/`。修复前备份：`~/storage/daw/Backups/chordlab-window-default-20261021T194605Z/`。没有重编译或替换 CLAP；本轮不声称完成整个 DAW 的重启验收。

## 游戏右栏的布局所有权 — 2026-10-22 候选

- Chord Lab 识别 Bitwig transient 父窗口后，只调整自身宽度，不自行移动或恢复坐标；仍由本程序把 Chord Lab 与主音源整组居中。
- G 开合会在该窗口上替换自己的 `utrp-chordlab-layout-<revision>` mark，本程序将版本纳入布局 signature。这样快速关/开即使在 0.4 秒内结束、最终宽度不变，也不会漏掉宿主的自动移位。每个窗口仅保留一个版本 mark；其他用户 marks 不变。
- 手工拖动不会改变版本，因此不会立即被拉回。下一次 G 开合或其他结构变化时重新居中，不回放旧坐标。
- 必须配套部署候选 CLAP 与本程序；本轮仅在临时 Sway 运行源码，没有重启真实用户服务。正式部署与真实 Bitwig 验收仍待进行。游戏本身不要求新增服务。
- 368 项布局测试通过，覆盖三种主音源尺寸、三个输出坐标原点、重复开合，以及同尺寸不同版本的漏检回归。完整游戏说明见 [GAME.cn.md](../chordlab_clap/GAME.cn.md)。

## 2026-10-23：Library 冷启动 Focus / Active 修复

- Library controller 0.11：保存时选中文件夹或无选中轨道，也会一次性打开共享 Chord Lab；设备列表延迟就绪有有界重试。此分支不改音色 Active、Arm、Monitor 或其他编辑器，普通工程不启用。
- Chord Lab 0.3.6：等待宿主打开事务稳定后申请初始键盘焦点；宿主只聚焦外层容器时，将焦点传入自身键盘 peer。手动 A OFF 和离开插件窗口不触发抢焦点。`theme.toml` 的 `interaction.focus_settle_ms=300` 独立于视觉配色。
- 现有 `utrp-plugin-windows` 布局策略仅对新发现的 Library 共享窗口执行一次 compositor focus，且当前焦点必须仍在同一 Library 主窗口/编辑器。不会因 G 展开收起、移动、点击其他应用或定时轮询反复抢焦点；没有新增服务。
- 验证：927 项 Python、12 项 CTest、隔离 Sway 的 CLAP 输入/状态/焦点测试通过；新增“宿主稍后聚焦容器”的断言旧 0.3.5 失败、新版通过。真实 Library 冷启动不点击插件/A 即 S/A 双绿；电脑 A 触发音符及 Bitwig 音量表；离开 3 秒仍保持主窗口焦点，返回插件恢复 A。
- 证据：`target/focus-startup-20261023/`。隔离测试必须使用 compositor-managed 窗口；早期 override-redirect 测试在 rootless Xwayland 得到 PointerRoot，不能作为生产缺陷证明。最终旧/新对比见 `probe-old-host-settle.log` / `probe-final.log`。
- 本轮不声称重新听测实体 MIDI/吉他或所有音色。插件 SHA256：`9f35503a54f4414ee11aa16c6675c4192e2c6d4cc3375be64a57c0ad6c2b9a41`。原件备份：`~/storage/daw/Backups/chordlab-focus-20261023/`。未自动 commit/push。

# Chord Lab

纯 REAPER 的和弦学习与音色探索工具。独立 JSFX MIDI 核心 + 原生 Virtual MIDI Keyboard（VKB）+ 小型 Lua 会话管理，无外部键盘监听、系统服务或扩展依赖。

## 使用

1. 选择已有 Surge XT 或其他 synthesizer 的轨道，Actions 运行 **Open Chord Lab.lua**。
2. 打开 Chord Lab 时会同时打开原生 VKB，供电脑演奏；也可从 **View → Virtual MIDI Keyboard** 手动打开。实体 MIDI 不需要此窗口。选调，**按住**级数键发声，**松开**发送 Note Off。鼠标级数按钮同样按住发声。两个级数键重叠时，后按优先，松开后回到仍按住的前一个。
3. 窗口显示与 FX 启用独立：在公共输入轨的 **Input FX** 打开 Chord Lab 时也打开原生 VKB；选中音色轨时同样带上 VKB。手动关闭 VKB 不会被稳定轮询立即重开，下次打开 Chord Lab 或重新选轨时才恢复。隐藏 Chord Lab 不会 bypass，也不会撤销 arm／monitor 或关闭手动打开的 VKB；实体 MIDI 仍正常处理。
4. Input FX 列表中的启用／bypass 开关才控制插件是否处理输入。Surge 在音色轨的普通 FX 中单独开关界面；不要用 bypass 代替隐藏窗口。
5. 再次运行 **Open Chord Lab.lua** 才是退出会话，恢复此前输入、录音待命、监听及 VKB 按键捕获设置，不改变 VKB 窗口可见性。输入 preset 名称前先关闭 VKB 或退出会话，避免字母被当成演奏键。

| 按键 | 功能 |
|---|---|
| `Q W E R T Y U I O P [ ]` | 大调主音 `C Db D Eb E F Gb G Ab A Bb B` |
| `A S D F G H J` | 顺阶音级 `vi vii I ii iii IV V` |
| `Tab` | 三和弦 → 七和弦 → 九和弦 → 三和弦；可在按住期间切换 |
| `K / L` | voicing 向低／高移动一步，跨原位继续跨八度；每次成功移动自动记住当前音级的类型、voicing 和位置，松开 K/L 不停音 |
| `;` | 保留为手动保存快捷键；K/L 移动后不再需要按它 |
| `Enter` | 保留当前和弦类型，恢复最靠近中央 C 的原位，**同时更新该音级记忆** |

**Tab 接入待完成**：宿主 VKB 未可靠传递 Tab；已提供 `Cycle chord type.lua`，尚未完成全局 Tab 绑定验收。

**默认**每个音级为七和弦原位，平均音高尽量靠近 MIDI 60。三、七、九和弦分别发 3、4、5 个音。九和弦采用紧凑排列（原位按根音、九音、三音、五音、七音排列），并非吉他推荐指法。所有音严格限制在 MIDI 0–127。

记忆按 **音级** 分开，换调沿用类型、转位和音区中心，实际音高和拼写随调变化。换调只允许在没有生成和弦且 transport 停止时。记忆随 JSFX 状态保存在 `.rpp` / FX preset，不写共享全局库；保存工程才能保证下次打开保留。旧 v1 七和弦状态只迁移当时所选调的七个音级。

K/L 无论持音中还是松键后移动，成功移动即更新该音级的记录；切换到其他音级再回来会恢复最后的位置，不必另按 `;`。Enter 保留当前和弦类型并把原位写回记忆。仅 Tab 切换类型仍是当前试听，可通过随后移动、`;` 或 Enter 记住。这里的自动记忆不等于自动保存工程：退出 REAPER 后要保留仍需保存 `.rpp`。Note Off 不强行截断 Surge release / delay / reverb 尾音；sustain 也可能继续延音。

## 界面

- 默认内容区 **884 × 683**，本机浮窗外框 **884 × 712**；下接 **884 × 163** 的 VKB，左列总高 **875 px**，与右侧 Surge 顶底对齐。上下两组均为左侧大谱表、右侧钢琴与吉他指板；可拖动边缘调整大小。
- 顶行只显示大调 `C Db D Eb E F Gb G Ab A Bb B`。其下是完整大调音阶图：**1 红、2／3 绿、4／5 橙、6／7 蓝**，没有九音紫色。例如 C 大调：C 红、D/E 绿、F/G 橙、A/B 蓝。
- 中间保留和弦按钮 `vi vii I ii iii IV V`，例如 `iii Em7/G3`；有保存记录时显示小圆点。下方保留当前和弦图：**根音红、三音绿、五音橙、七音蓝、九音紫**，颜色相对于所选和弦，不跟随上图音阶级数。
- 大七／大九写 `M7` / `M9`，小七写 `m7`；顺阶降九度明确标注，不把 iii 误标为普通 m9。
- 中性灰底 `#B3B3B3`、灰色直角按钮；移除内部 `CHORD LAB` 标题行和快捷键说明，直接从大调选择开始；保留 REAPER 的原生 FX 工具栏，无额外控制面板或色彩图例。
- 谱表、钢琴白键、吉他指板（含空弦区）统一使用 `diagram_background = "#E9EDF0"`；白键底部没有额外灰色阴影。黑键、谱线、琴弦与彩色音点保持原样。
- 每组钢琴 **D2–D6**（49 键）、吉他标准调弦空弦到 **17 品**，高音 E 弦在上。上下两组共用全部尺寸参数；谱表每组默认高 270 px，右侧扣除间隔后钢琴与吉他各占 **50%**（默认各 129 px），两者同宽，左侧谱表与指板底边对齐；指板下方只保留单／双点品记。
- 六个视图共用圆点绘制：默认半径 **7 px**、字号 **12**（升降号自动缩小以适配），黑色加粗音名按调性拼写。非持音为浅色，持音为原色，不变大小、无光晕。
- 上图按完整 MIDI 音高高亮：调内音按其大调级数着色；调外按键仅持有时显示灰色。下图保留和弦规则：和弦内音用角色色，和弦外按键灰色，即使它属于当前调。例如 C 大调 Cmaj9 中 F：上图橙、下图灰；D：上图绿、下图紫。
- 吉他同 MIDI 音高的不同弦位置同时加深；同名的其他八度保持浅色。不追踪 synth release 或 sustain 尾音。
- 两组谱表只显示 **E2–A5**，即低音谱下第一加线至高音谱上第一加线；中央 C 短线常显。谱线、圆点与符号共用音高坐标；先画所有加线再画圆点，避免覆盖。半像素中心保持对齐，谱间距随可用高度缩放；当前默认半间距 10 px、音点半径 7 px，间内音点与上下谱线留白，线上的音点仍正常压线。谱号字形缩放为 0.56。高低谱号均绘制调号，调内音不重复加升降号，调外按键显示必要的临时变化音；临时符号缩至调号符号的 75%，向左靠近谱号并与音点拉开间距，调号大小不变。钢琴／指板超出该谱表范围的音仍可正常显示和演奏。

## MIDI 与边界

```text
电脑键盘 → REAPER VKB / channel 16 ─┐
外接 MIDI / channels 1–15 ─────────┴→ Chord Lab Input FX → synth → 音频
                                           └→ 录制实际和弦 MIDI
```

- 插件放在 **Input FX**，不是 synth 后面。生成音符在 channel 1；同通道同音高合并持有，所有来源释放后才 Note Off。其他 MIDI 通道及 sustain / pitch bend 等控制器透传。
- channel 16 专用于电脑控制，被完整吞掉。原生 VKB 高亮的是控制音，不是额外 synth 音符；不能关闭原生映射又期待纯 REAPER 方案收到电脑按键。Surge 自己的 QWERTY 演奏键盘保持关闭。
- 电脑键盘演奏时 VKB 窗口必须保持打开；只隐藏 Chord Lab 不影响电脑输入；关闭 VKB 才停止电脑键盘输入，但插件及实体 MIDI 通路继续运行；不要改其 channel / centre / layout。不支持其他应用获焦时全局演奏。Surge CLAP 获焦后松开电脑键实测会丢 Note Off、产生挂音；应松键后再进入 Surge 编辑，不能当作可靠的跨窗口演奏。按用户选择不加入外部 helper。
- 只管理固定目标轨，选别的轨不会转移目标。另一条 armed 轨收到 VKB/All MIDI 时会禁用电脑模式并提示，避免控制音误入其他 synth；解除冲突后自动恢复。
- 退出模式和单独旁路 JSFX 会清理生成音符。关闭 VKB 时释放生成音符、关闭电脑键盘捕获，不清理实体 MIDI 的持有状态；只隐藏 Chord Lab 时仅到期清理鼠标持音，不停止电脑键持音。删除/offline 插件、旁路整条 FX chain、关闭工程或音频设备前先松开所有键并退出模式；不能保证强制卸载后仍能发送 MIDI 清理。异常挂音用 REAPER All notes off。
- 打开 `.rpp` 本身不自动运行 Lua 会话；日常 Library 启动器会在后台启动会话，不主动打开隐藏的编辑器；已有打开的 Chord Lab 会带上 VKB。单独使用时运行 Open action。电脑控制需要 Lua 会话运行，不恢复持续发声。音色仍由 synth preset / 工程管理。
- 外接设备需在 REAPER Preferences 中启用；未连接真实键盘时，模拟测试不等同实体设备验收。

## 安装与卸载

先退出使用目标 resource path 的 REAPER：

```sh
python lib/tools/chordlab/install.py --resource "$HOME/.config/REAPER"
```

重开后，Actions → New action → Load ReaScript 加载：
`~/.config/REAPER/Scripts/ChordLab/Open Chord Lab.lua`。也可运行同目录 `Register Chord Lab.lua`。可自行绑定快捷键。

仅链接本工具运行时文件，不安装测试探针；源码目录不要随意移动。安装会全局替换 VKB 键位表（包括 Tab），设置 channel 16 / centre 60 / 禁用箭头移调；第一次安装前的设置保存在 resource path 的 `chordlab-backup/`。不改实体或系统键位。

```sh
# 同样先退出 REAPER
python lib/tools/chordlab/install.py --resource "$HOME/.config/REAPER" --uninstall
```

卸载恢复原 VKB 表和相关设置，保留备份；若用户手动改过映射，拒绝覆盖。Actions 注册条目可手动 Remove。重新建立备份基线前先另存旧备份。

## 模块与验证

- `harmony.jsfx-inc`：纯音高计算、声部排列、和弦性质与音名。
- `midi.jsfx-inc`：命令、MIDI、音符所有权和音级记忆，每个实例私有。
- `ui.jsfx-inc`：响应式布局与地图；只向音频线程提交命令。
- `staff.jsfx-inc` / `notation.svg` / `notation.png`：独立谱表、调号与嵌入的 Bravura 正规音乐字形（SIL OFL，见 `notation-license.txt`）；`render_notation.py` 从 Bravura 字体生成 SVG，再用 `rsvg-convert` 生成运行时 PNG。
- `chordlab.jsfx`：宿主生命周期、参数、状态序列化。
- `Open Chord Lab.lua` / `Chord Lab mode.lua`：入口及纯 REAPER 会话管理。
- `theme.toml` → `theme.jsfx-inc`：配色、字体；通过安装器生成。
- `install.py`：安装、备份与恢复。测试仅在 `tests/`，见 [验证说明](tests/README.md)。

## 本机配置

Sway `~/work/gral/arch/sway/config`：主窗无边框平铺占满 workspace 2，其他 REAPER 窗口浮动；不使用遮挡插件浮窗的真 fullscreen。

Surge 保留当前已确认的原生等比例缩放，实测外框 **1359 × 875**；菜单的 150% 档在本机回报实际 149%，默认 Zoom 已通过原生菜单保存为 **149%**。旧实例可能保留自己的 Zoom，因此 Sway 开窗规则同时指定 `1359×875`，插件内容随尺寸等比例缩放；未批量修改音色工程状态或精调；缩放入口参见 [Surge 官方手册](https://surge-synthesizer.github.io/manual-xt/index.html#zoom)。日常入口为 `~/storage/daw/synth.rpp`；用户 Patches/Endless 链接仓库 `lib/surge/endless`。

原生 VKB 为 **884 × 163**，位于 Chord Lab 正下方；比上一版 139 px 再增加 24 px 琴键高度，中央 C（MIDI 60）居中。它不是输出音高可视化，也不是精确 D2–D6 范围。Chord Lab 移除内部标题，外框缩为 **884 × 712**，上下两组图面同步略缩短，50/50 比例保持不变。左侧组合与右侧 Surge 同为 **875 px** 高，在 1440 px 屏幕上垂直居中，具体坐标见 [Library 布局](../library/README.md)。REAPER 主题在 Options → Themes / Theme Adjuster，未安装第三方主题。

管理边界、今日改动与本机影响见 [MANAGEMENT.md](MANAGEMENT.md)。

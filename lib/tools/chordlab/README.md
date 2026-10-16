# Chord Lab

纯 REAPER 的和弦学习与音色探索工具。独立 JSFX MIDI 核心 + 原生 Virtual MIDI Keyboard（VKB）+ 小型 Lua 会话管理，无外部键盘监听、系统服务或扩展依赖。

## 使用

1. 选择已有 Surge XT 或其他 synthesizer 的轨道，Actions 运行 **Open Chord Lab.lua**。
2. 选调，**按住**级数键发声，**松开**发送 Note Off。鼠标级数按钮同样按住发声。两个级数键重叠时，后按优先，松开后回到仍按住的前一个。
3. 再次运行 **Open Chord Lab.lua** 退出模式，恢复此前输入、录音待命、监听及 VKB 状态。输入 preset 名称前先退出模式，避免字母被当成演奏键。

| 按键 | 功能 |
|---|---|
| `Q W E R T Y U I O P [ ]` | 大调主音 `C Db D Eb E F Gb G Ab A Bb B` |
| `A S D F G H J` | 顺阶音级 `vi vii I ii iii IV V` |
| `Tab` | 三和弦 → 七和弦 → 九和弦 → 三和弦；可在按住期间切换 |
| `K / L` | voicing 向低／高移动一步，跨原位继续跨八度；松开 K/L 不停音 |
| `;` | 保存当前音级的和弦类型、voicing 和位置 |
| `Enter` | 保留当前和弦类型，恢复最靠近中央 C 的原位，**同时更新该音级记忆** |

**Tab 接入待完成**：宿主 VKB 未可靠传递 Tab；已提供 `Cycle chord type.lua`，尚未完成全局 Tab 绑定验收。

**默认**每个音级为七和弦原位，平均音高尽量靠近 MIDI 60。三、七、九和弦分别发 3、4、5 个音。九和弦采用紧凑排列（原位按根音、九音、三音、五音、七音排列），并非吉他推荐指法。所有音严格限制在 MIDI 0–127。

记忆按 **音级** 分开，换调沿用类型、转位和音区中心，实际音高和拼写随调变化。换调只允许在没有生成和弦且 transport 停止时。记忆随 JSFX 状态保存在 `.rpp` / FX preset，不写共享全局库；保存工程才能保证下次打开保留。旧 v1 七和弦状态只迁移当时所选调的七个音级。

按住和弦后，Tab/K/L 是当前试听；按 `;` 或 `Enter` 才更新该音级的记录。切换到其他音级再回来会调用记录。Note Off 不强行截断 Surge release / delay / reverb 尾音；sustain 也可能继续延音。

## 界面

- 默认内容区 **884 × 565**，可拖动浮窗边缘调整宽高。12 个调性按钮及 7 个音级按钮各自铺满可用宽度；左侧谱表与右侧钢琴／指板并排。过窄时文字会缩小。
- 第一行显示关系小调／大调主音，例如 `A/C`、`Bb/Db`，共用原大调顺阶计算；第二行每个按钮一行，例如 `iii Em7/G3`。默认与保存记录都显示，保存记录有小圆点标记。不显示顶部调性／和弦类型状态文字或底部角色色彩图例。
- 大七／大九写 `M7` / `M9`，小七写 `m7`；顺阶九和弦中的降九度会明确标注，不把 iii 误标成普通 m9。
- 与当前 REAPER 插件顶栏匹配的中性灰底（`#B3B3B3`），两行无缝直角按钮用深浅灰表示状态，无蓝灰色调；音符保留角色颜色。无 K/L、Save、Enter、Tab、Keyboard ON、STOP 或 centre 操作按钮；快捷键仍有效。
- 钢琴 **D2–D6**，49 键；吉他标准调弦，空弦到 **17 品**，高音 E 弦在上。两张地图同宽；默认钢琴 **664 × 184**，吉他 **664 × 156**。吉他白底与左侧谱表白底下缘对齐；指板下方只保留单／双点品记，不显示品数数字。
- 根音红、三音绿、五音橙、七音蓝、九音紫；圆内为居中的黑色加粗音名，按调性拼写。所有八度的和弦音均显示；三个视图圆点统一半径 9 px、字号 15；发音音符浓色，其余为浅色，不随发声改变大小，无光晕。
- 吉他按完整 MIDI 音高匹配，不同弦上的重复音都加深。电脑或外接 MIDI 任一来源按住和弦内音，均显示同样大小的浓色圆点，不加外圈。和弦外音仅在实体 MIDI 按住时显示实心圆与音名：钢琴白键、黑键及吉他统一灰圆黑色粗体字。不追踪 synth release 或 sustain 尾音。

- 左侧大谱表覆盖 **C2–C6**；高低音谱各五条长线，中央 C 短线常显，上下加线在相应音符处画短线。谱线、音符与符号使用同一套音高坐标（按实际像素计算 2 px 谱线中心；半像素圆心用透明小图插值，避免实心圆取整偏移），线宽保持 2 px，半个谱间距 11.5 px，即相邻谱线间距 23 px（默认尺寸）；谱号、调号与临时升降号较原版放大约 6%，大小独立于谱线间距，锚点随谱位移动，上下保留留白。谱号后使用当前调的调号，调内音不重复标升降号；外接 MIDI 调外音保留必要的临时升、降、还原号。谱表外音同样使用灰色圆点，按谱面位置读取音高。

## MIDI 与边界

```text
电脑键盘 → REAPER VKB / channel 16 ─┐
外接 MIDI / channels 1–15 ─────────┴→ Chord Lab Input FX → synth → 音频
                                           └→ 录制实际和弦 MIDI
```

- 插件放在 **Input FX**，不是 synth 后面。生成音符在 channel 1；同通道同音高合并持有，所有来源释放后才 Note Off。其他 MIDI 通道及 sustain / pitch bend 等控制器透传。
- channel 16 专用于电脑控制，被完整吞掉。原生 VKB 高亮的是控制音，不是额外 synth 音符；不能关闭原生映射又期待纯 REAPER 方案收到电脑按键。Surge 自己的 QWERTY 演奏键盘保持关闭。
- VKB 窗口必须保持打开；不要改其 channel / centre / layout。不支持其他应用获焦时全局演奏。Surge CLAP 获焦后松开电脑键实测会丢 Note Off、产生挂音；应松键后再进入 Surge 编辑，不能当作可靠的跨窗口演奏。按用户选择不加入外部 helper。
- 只管理固定目标轨，选别的轨不会转移目标。另一条 armed 轨收到 VKB/All MIDI 时会禁用电脑模式并提示，避免控制音误入其他 synth。
- 退出模式和单独旁路 JSFX 会清理生成音符。关闭浮窗时只释放鼠标持有，不影响仍按住的电脑／实体键。删除/offline 插件、旁路整条 FX chain、关闭工程或音频设备前先松开所有键并退出模式；不能保证强制卸载后仍能发送 MIDI 清理。异常挂音用 REAPER All notes off。
- 打开 `.rpp` 不自动运行 Lua 会话，再次运行 Open action 即可，不恢复持续发声。音色仍由 synth preset / 工程管理。
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

Surge 用户默认 **135% Zoom**；各已保存实例可保留自己的缩放及精调。日常入口为 `~/storage/daw/synth.rpp`，当前保留 C4-darkdrone 精调；用户 Patches/Endless 链接仓库 `lib/surge/endless`。原生 VKB 为 **884 × 150**，约五个八度，中央 C（MIDI 60）居中；它不是输出音高可视化，也不是精确 D2–D6 范围。Chord Lab 浮窗 **884 × 646**，与 VKB 上下组合后与右侧 Surge 顶底对齐，具体坐标见 [Library 布局](../library/README.md)。REAPER 主题在 Options → Themes / Theme Adjuster，未安装第三方主题。

管理边界、今日改动与本机影响见 [MANAGEMENT.md](MANAGEMENT.md)。

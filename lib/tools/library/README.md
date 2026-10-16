# Synth Library — 单音色试听工程

当前：88 个仓库 FXP 按五个 collection 分组，保留 Storage 中一个参数不同的版本；
89 条 synth 轨共用一个 Chord Lab 输入。不是多层叠加演奏器。

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
**单击另一条音色轨即可切换试听**，但不再打开或聚焦任何编辑器。
所有音色轨共用输入，不逐轨复制 Chord Lab。点击专辑文件夹或公共输入轨不切音色。

- **Chord Lab**：从 `CHORD LAB - shared MIDI input` 轨的 **Input FX** 打开；原生虚拟键盘同步出现，关闭任一窗口则一起隐藏。
- **Surge**：从音色轨的普通 **FX** 单独打开／关闭，不带动 Chord Lab 或 VKB。
- **显示与处理独立**：关闭编辑器不是 bypass。隐藏 Chord Lab 后 Input FX、arm／monitor 和实体 MIDI 通路保持运行；电脑按键输入随 VKB 关闭，电脑／鼠标持音会安全释放。
- 插件是否处理由各自 FX 的启用／bypass 控制；重新打开 Chord Lab 不会自动取消 bypass。
- 音色切换仍将旧 Surge 离线；REAPER 可能随离线关闭旧实例界面。这是资源策略，不是选轨自动弹窗。需要编辑某个音色时先选中该轨，再打开 FX。
- 会话运行时 VKB 与 Chord Lab 双向同步；稳定轮询不反复开窗或抢焦点。独立打开 VKB 会同时显示 Chord Lab。

点击某条音色轨的 **Solo** 也可以切换，管理器自动取消上一个 Solo：只保持当前 Surge 在线、
只把公共 MIDI 发给它，其余 Surge 离线但状态仍保存在 RPP 中。
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
当前 3440×1440 屏幕：左上 Chord Lab `(560, 300)`，大小 `884×646`；
左下原生虚拟键盘 `(560, 946)`，大小 `884×150`；右侧 Surge `(1480, 300)`，
当前实例大小 `1232×796`。左侧两窗等宽；原生键盘降低高度后琴键同步变窄，约显示五个八度。
中央 C 为 MIDI 60（本机显示 C4），保持居中；左侧组合与 Surge 顶底对齐。
保留左侧轨道和顶部空间。REAPER `reaper.ini` 的 `dockheight=280`
将混音台留在底部。规则只决定新窗口初始位置，之后可以自由拖动。
原生 VKB 图示不是实际和弦输出，以 Chord Lab 为准。
更换屏幕分辨率时需要调整这些桌面坐标；不为此增加常驻布局服务。

- `Ctrl+S` 保存当前 RPP：记录轨道音色与效果设置，不会自动更新原 FXP。
- 要加入公共音色库：在 Surge 另存有描述名称的 FXP 到相应 `lib/surge/<album>/`。
- 停止模式：运行 `Library mode.lua`；它也请求停止所属 Chord Lab 会话。
- 切到别的工程时自动结束会话；回到本工程再运行 Start。
- 工程关闭再打开不自动恢复 Lua，默认 REAPER 启动入口另外运行 Start。

## 验证与保护

```sh
python -m pytest -q lib/tools/library/test_*.py lib/tools/chordlab/tests/test_install.py
luac -p 'lib/tools/library/Library mode.lua'
lua lib/tools/library/test_mode.lua
lua lib/tools/chordlab/tests/test_mode.lua
```

`host_audit.lua` 只允许 `/tmp/` 工程副本，且必须先启动 Library mode。
它顺序选中全部音色轨，分别注入电脑控制通道和普通 MIDI Note On/Off，
测轨道输出峰值，断言只有一个在线 Surge／Solo／armed 输入，且选轨不打开 Surge 浮窗，并导出 CLAP 状态。
测试脚本会显式打开共享 Chord Lab，并关闭副本中的 Surge 浮窗以建立检查基线。
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

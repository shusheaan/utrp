# Chord Race：Bitwig 游戏模式

[English](GAME.md) · [正常模式与历史部署](README.cn.md)

## 0.3.3 胶囊配色与上下文验收（2026-10-22）

用户确认后已保存 Library、正常退出、备份并原子安装 0.3.3，再在 Workspace 2 重开。SHA-256：`b4ee873cb6aa692a1ebc4c3821ef86aaf2ebe02599592f2a8372b958704c092e`。

- 真实 Bitwig 显示七个和弦胶囊，游戏目标含级数、和弦名、最低音及八度，其他和弦保留；未命中答案音仍隐藏。
- 配色固定采用所选调对应的大调音级，两种模式一致，不随相对小调重新起算。顶部选调胶囊不改色。
- 实测 G 展开增加 332 px，不与 sfizz 窗口重叠；收起恢复完全相同的 920×703 窗口位置与尺寸，正常调性及和弦恢复。最终 G 红、S/A 绿。
- 1348 项 Python 测试、12 项 CTest、构建及已安装 CLAP probe、`cargo test`、`cargo clippy` 通过。10 个 Storage 链接核验正常。音色、音频路由、Arm、controller、窗口布局服务未修改。
- 证据及回退副本：`target/chordlab-colored-choices/`。本轮验证 UI 和自动回归，没有重复声称完成实体弹奏或全音色听感验收。源码未 commit/push；源码和部署进入 DAW Recovery 快照。

## 0.3.2 延音同步验收（2026-10-22）

0.3.2 已保存、备份并重载到真实 Bitwig Library，仍位于 Workspace 2。SHA-256：`29cf4c080272ff0462197058f56d3f8ebb5e6147895af52be543a0d72f93ea44`。

- 修复 S 绿色但下游接收端延音状态失同步：实际音符攻击前重发有效 CC64，电脑和弦每次一条，实体 MIDI 按对应通道一条。不改变 NoteOff、踏板 baseline 或游戏规则。
- 启动验收没有手动切 S/A：电脑和弦短按 50 ms 后释放，Bitwig 输出仍有延音。随后手动关闭 S 的同样短按明显较快收音，再恢复 S On。仅采集 Bitwig 输出作对照，没有启动工程录音或采集 Spark 输入。
- 用户确认：不踩踏板，实体 MIDI 和电脑键盘两种输入都有延音。最终普通模式 G 红、S/A 绿；音色、声卡、controller、Arm、窗口布局服务未修改。
- 1340 项 Python 测试、10 项 CTest、构建及已安装 CLAP probe、`cargo test`、`cargo clippy` 均通过；新接收端回归在旧代码失败、修复后通过。`live.py --check` 核验 10 个 Storage 目录链接正常。
- 日志、输出声音对照、截图与旧插件/工程回退副本：`target/chordlab-sustain-routing/`。源码尚未 commit/push；部署与源码保留在 DAW Recovery 快照。

## 状态与边界

**0.3.1 历史部署，2026-10-22。** 仅打磨 Bitwig 内的 Race UI：纯黑底，青色调性、黄色当前和弦、绿色进行／转调解释；后续和弦与调性分色，长说明固定字号换行，最小窗口高度保留底部设置空间。配色集中在 `chordlab/theme.toml` 的 `[game]`，不改变正常模式主题、判定规则、音色或音频路由。独立版暂停，音色菜单取消，见 [范围记录](STANDALONE.cn.md)。

0.3.1 SHA-256：`3eeba212ec1beeaedc5dd00605f6eeac63c240fb33fa91231fe16f972efc656a`。用户同意后保存 Library、正常退出，原子替换 CLAP，再从 Workspace 2 打开 Library。构建产物、隔离及真实宿主截图、测试日志在 `target/chordlab-race-polish/`。

2026-10-22：0.3.0 已备份后安装到真实 CLAP 目录，Library 已保存并重载，Bitwig 在 Workspace 2。声卡配置、controller、系统服务未修改。当时安装的 SHA-256：`cc336dee7fd61f7bd54d83a09175aa3622c33aff7f1a2d9a9f5feb875dbb046f`。没有 commit/push；下方隔离测试和部署阻塞段落为历史记录，以文末真实验收为准。

游戏是显式、临时的模式，不是新宿主参数。默认 G 红色；打开 G 变绿，在现有 920×703 左侧画面右边增加 332 px（含间隔），Start 开始，Pause/Resume 暂停继续，Restart 重新随机开始并清零分数。关闭 G 恢复进入前的正常窗口尺寸、调、和弦、音型记忆与操作。隐藏/关闭编辑器、宿主 reset 或替换引擎会结束游戏；不保存游戏进度。

## 规则

- 钢琴和吉他面对同一个紧凑钢琴 voicing；和弦名加最低音及八度唯一确定它。例如 `Em/G4` 是 G4–B4–E5，不是任意 Em 转位。
- 精确匹配 MIDI 音高，包括八度。可分解或同时弹；每方独立收集，不能拼凑双方命中。先独立弹完的一方获得 1 分并换题。相同采样位置同时完成时，按宿主提供的事件顺序决定先后。
- 重复音不重复计分；下一题不继承上一题的持音。必须先松开再重新弹下。吉他只识别单音音高，不要求弦、品或把位。
- 默认每题 10 秒，可设 1–120 秒；超时不加分，展示答案并演示，默认 2 秒，可设 1–10 秒。修改时长从下一题生效；暂停保留剩余时间。
- 开始前和每题开始时隐藏键盘、指板、五线谱的答案。正确音出现后持续保留正常的和弦/调内颜色、轮廓和光晕；错音不显示为答案。超时显示全部目标音。
- 游戏中禁用自动电脑和弦和正常音型导航，避免一次命令直接完成答案。实体 MIDI、吉他检测和 S 延音控制仍可用。退出后正常电脑键盘控制恢复。

## 和声与 voicing

`../chordlab_game/game.rs` 直接复用 UTRP `Progression` 和原有 `config/simulate.toml` / `config/progressions.toml`，不复制和声算法、不启动服务。三/七和弦、转调、临时经过、恢复调来自原引擎；首版关闭扩展音与 ambient 模式。右侧显示当前调、当前和弦、原引擎原因和随后两个和弦。

独立 voicing 规划在 E2–A5 内选择紧凑排列，每个和弦跨度最多 12 半音；短句在保持/上行/下行之间切换。优先共同实际音、就近移动，平均音高变化最多 5 半音；方向受边界约束时转向。长期访问次数参与随机采样，避免总停在一个音区。具体限制和权重集中在 `../chordlab_game/game.toml`，随构建嵌入，不读取用户 cwd 配置。

## MIDI 路由

| 通道（1-based） | 用途 |
| --- | --- |
| 输入 1–14 | 钢琴计分，原 MIDI 发声/踏板路由保留 |
| 输入 15 | 吉他计分，仅显示/判定，不转成下游钢琴声音 |
| 输入 16 | 原电脑控制私有命令，不能用于答题 |
| 输出 16 | 游戏答案演示，独立 Note On/Off 与 CC64 Off |

Library 原有 Guitar Frontend 检测通道 2 经 Note Receiver 映射到 15 的设置继续使用。**演示输出 16 必须单独送到钢琴音源**，其他演奏通道照旧；不能仅因为有 MIDI 输出就声称已经接好钢琴。本次隔离测试没有音频设备，只验证演示事件与时间，不代表 Spark GO 检测精度、真实听感或 Bitwig 钢琴路由验收完成。

关闭游戏只清理自己的演示通道，不关闭实体键盘的音或踏板。进入游戏释放电脑自动和弦的所有权；退出不自动重弹进入前已释放的电脑和弦。用户在游戏中主动切换 S 属于用户操作，不会在退出时被偷偷撤销。

## 窗口与兼容

- **Bitwig 内只有既有 `../plugin_windows/layout.py` 负责位置**。通过 Bitwig 主窗口与 `transient_for` 关系识别归属后，插件只改变自身尺寸，不再保存、移动或恢复窗口坐标。G 展开/收起触发原程序按实际宽度重算中央组，避免两套逻辑互相抢位置。无需新服务；若原布局程序未运行，则不保证自动成组居中。
- 快速连点可能在两次轮询之间完成整轮开合，尺寸相同却已被宿主移位。因此每次开合结束用一个 `utrp-chordlab-layout-<revision>` Sway mark 请求重新布局；只替换自身的版本标记，不动用户 marks。布局程序将版本纳入 signature。插件和布局源码须配套更新，不能只换 CLAP。
- 原程序每 0.4 秒检查尺寸；这是最终稳定布局，不承诺宿主 resize 的每一帧都无过渡。手动拖动一直有效到下一次结构变化；G 收起后采用当时的正常居中布局，而非强制恢复旧坐标。屏幕不足沿用原程序的显式溢出提示，不承诺任意窗口组合都能放下。
- **非 Bitwig 的隔离/独立宿主**保留插件自身的 Sway 开合布局：只检查当前工作区 floating 窗口；同进程窗口可避让，无关窗口不移动。自动移动的窗口在收起时恢复，用户手动移动的窗口保留；空间不足报告错误。非 Sway 宿主不自动安排旁边窗口。
- Sway IPC 只在 G 切换的 UI 线程访问，不新增全局桌面规则。此次没有修改或重启真实桌面的既有布局服务。
- 稳定 CLAP ID `org.utrp.chordlab`、21 个参数和 v3 保存格式保持不变。游戏不写正常 sliders/音型记忆/序列化状态；音频线程不调用 Rust 规划或 Sway IPC。

## 验证与复现

```sh
cmake --build target/chordlab-clap-build/build -j2
ctest --test-dir target/chordlab-clap-build/build --output-on-failure
python -m pytest -q lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/plugin_windows/test_layout.py
cargo test --offline
cargo clippy --offline --all-targets -- -D warnings
cargo test --offline --manifest-path lib/tools/chordlab_game/Cargo.toml
cargo clippy --offline --manifest-path lib/tools/chordlab_game/Cargo.toml --all-targets -- -D warnings
```

- 569 个 Python 测试、10 项 CTest；新游戏测试直接运行生产 JSFX 与 C++ bridge。
- 检查独立双方计分、错误八度、重复/持音、暂停、采样点截止边界、演示清音、快速开关、宿主 reset、序列化不变、重载游戏关闭、实例隔离。
- `game_tests CURRENT.jsfx ORIGINAL.jsfx` 支持与改动前原始引擎比较 G 关闭后的 MIDI，按字节相等，而非只比较两个新版实例。
- Rust 8 个 seed × 1500 题：确定性、紧凑跨度、相邻移动限制及每个 seed 覆盖 E2–A5 全部 42 个音高。此覆盖是测试结果，不是每轮短局覆盖保证。
- 原 CLAP probe 检查 12 种采样率/块大小、21 参数、持音/踏板、旧状态、Guitar/Piano 切换和双实例生命周期。
- `game_preview plugin.clap midi-in.txt midi-out.txt` 是无声卡、按墙钟运行的原生 CLAP 测试宿主。输入每行 `递增序号 status note velocity`，均为十进制；只用于隔离 Sway，禁止将其当作真实吉他验收。
- 截图、构建/测试日志和布局前后 JSON 归档到 `target/chordlab-game-validation/`（不进 Git）。最终上线前仍须保存 Library、核验 ch16 钢琴演示、Spark 单音判定、现有窗口服务，并按 `../daw_backup/` 更新恢复记录与快照。

- 追加布局验证：368 项布局测试与 569 项插件 Python 测试（合计 937）通过；布局源码 `mypy --strict` 通过。隔离 Sway 中以真实候选 CLAP、模拟 Bitwig 父窗口/sfizz、更新后的布局程序联合测试：20 轮开合、20 次快速切换、拖动后收起、双状态稳定性通过；用户 marks 保留，版本 mark 仅一个。这不是实际 Bitwig 音频验收。

## 多窗口补验与部署阻塞（历史，真实会话已恢复）— 2026-10-22

- 游戏/正常两种宽度覆盖音源和效果器全部既有打开顺序，布局测试增至 708 项；连同插件、Library controller、恢复工具共 1319 项 Python 测试通过。10 项 CTest、原始引擎正常 MIDI 对照、游戏 crate 的 cargo test/clippy 再次通过。
- 隔离 Sway 的五窗口（候选 Chord Lab、模拟 sfizz、两个模拟 FX、模拟混响）连续 10 次开合，均无重叠、在可用区内、保留 16 px 间距；收起后稳定。证据 `target/chordlab-game-validation/multi-game-*.png/json`。
- 用户已同意保存后重载，但当前没有可访问的真实 Bitwig/Sway 桌面会话，当前 PipeWire 会话没有输入/输出端点，也未发现 Spark GO/U Audio；ALSA 仍列出其他板载/USB 设备。未替换正式插件、未修改 Library，不能声称已执行保存/重载或真人听音验收。恢复真实会话后继续 ch16 演示路由与 Spark 检测验收。

## 真实 Bitwig 验收 — 2026-10-22（覆盖此前部署阻塞）

- 真实 Sway 输出 3440×1440，Bitwig Library 在 Workspace 2；Keystation 61 MK3 与 Spark GO 已连接。原 PipeWire 路由核验为 Spark mono → Bitwig in1，Bitwig out1/2 → Spark stereo；本次未改声卡配置。
- 先做 Storage 恢复快照，再原子安装 0.3.0 CLAP。初次启动前 Bitwig 未运行；后续保存 Library、正常退出，再重开完成重载验收。没有启用实际录音或修改 controller。
- 当前钢琴仍为 `Basic Keys / 02 Soft Piano (sfizz)`，当前吉他仍为 `AG - 01 Glass Air`。ch16 超时演示实际触发 sfizz（截图可见 4 voices）；只采集 Bitwig stereo 输出 17 秒作诊断，峰值 -15.82 dBFS，无 NaN/Inf，不录麦克风、不启用 Beat Lab 录音。这段输出包含用户实弹，不将它当作隔离音源测量。
- 真实游戏画面观察到 Guitar 2 分，用户确认当时确实弹了吉他；再次重载后单独的实体 MIDI 试局观察到 Piano 1 分。证据 `demo-real.png`、`score-final.png` 与用户确认。自动测试另行覆盖双方不能合并命中、错误八度、持音、演示清音和状态隔离。
- 20 次实际 Bitwig 开合检查均通过：窗口在屏幕内、不重叠、16 px 间距、整体居中、版本 mark 只有一个。正常 Chord Lab 920×703，游戏 1252×703；sfizz 775×515。退出游戏后用户确认实体 MIDI 和电脑键盘都正常发声。
- 无 Bitwig 的 Standalone 已实际启动检查，但没有音源宿主，所以**独立发声和插件内音色选择未完成**，详见 [独立版和音色目录](STANDALONE.cn.md)。随后关闭测试程序，恢复 Library；重载默认 G 红、S/A 绿，正常尺寸与 Workspace 2 正确。
- 总计 1437 项 Python 测试、Chord Lab 10 项 CTest、Guitar Frontend 2 项 CTest 通过；安装后的真实 CLAP ABI/lifecycle probe、原工程 Rust test/clippy、游戏 crate 的 2 项 test/clippy 均通过。新增目录解析严格类型检查通过。`live.py --check` 核验 10 个 Storage 实时目录链接。
- 实体 MIDI 计分检查临时使用 30 秒，收尾恢复 10 秒／2 秒，G 关闭并保存 Library；录音保持关闭。截图、音频诊断、全量日志、当前 DAWproject 音色导出和目录在 `target/chordlab-live-game/`，不进 Git。
- 恢复清单更新为 0.3.0，增加既有布局服务 drop-in 的可选备份；不创建服务。收尾执行 `lib/tools/daw_backup/snapshot.py`，恢复快照以 `~/storage/daw/Recovery/LATEST` 为准。源码仍未 commit/push。

## 0.3.1 验证补记 — 2026-10-22

- 1,340 项相关 Python 测试、10 项 CTest、CLAP probe（含旧状态、双实例、12 种采样率／块长）、root `cargo test --offline` 和 `cargo clippy --offline --all-targets -- -D warnings` 通过。未声称做了所有领域的全仓验收。
- 隔离 Sway 无音频宿主验证默认及最小高度；真实 Bitwig 上纯黑面板像素验证为 `(0,0,0)`。真实进行面板截图为 `target/chordlab-race-polish/live-game.png`。
- 真实 Bitwig 20 次开合通过：屏幕内、互不重叠、16 px 间距、整体居中、revision mark 数量有界。退出 G 后截图仅 A 焦点指示与进入前不同（最终绿灯），其余正常模式像素一致。默认尺寸 920×703 恢复，G 红、S/A 绿。
- Spark、MIDI 与 Bitwig 的 PipeWire 连接列表和前次验收完全相同。本轮未再次要求用户实弹，声音与计分的人体验收沿用上节历史记录，不把 UI 测试当作新的实弹确认。
- 更新前恢复快照：`20261023T025208.763013Z`。更新后快照见 `target/chordlab-race-polish/recovery.txt` / Storage `Recovery/LATEST`。无 controller、声卡设置或服务变更，无 commit/push。

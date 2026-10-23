# DAW 重装恢复

[English](README.md)

## 实时主数据（不是同步副本）

从 2026-10-18 起，`live.toml` 中的 **10 个目录**实体在
`~/storage/daw/UserData/`，home 原路径是目录 symlink：

| home 入口 | Storage 中实体（相对于 `UserData/`） |
| --- | --- |
| `~/.BitwigStudio/prefs` | `.BitwigStudio/prefs` |
| `~/.BitwigStudio/view-settings`、`library`、`installed-packages` | `.BitwigStudio/` 下对应目录 |
| `~/Bitwig Studio`（controller、用户库等） | `Bitwig Studio` |
| `~/.clap` | `.clap` |
| `~/.Surge XT`、`~/.Surge Synth Team` | 对应同名目录（插件偏好、主题、音色） |
| `~/.config/SFZTools`（sfizz） | `.config/SFZTools` |
| `~/.config/REAPER` | `.config/REAPER` |

软件仍使用熟悉的 home 路径，**每次落盘直接写入同一份 Storage 数据**，无需定时同步。
内存中尚未保存的数据仍须由软件正常保存/退出。目录链接能承受内部文件的临时文件＋rename
原子保存；不要改为只链接某个 prefs 文件。Recovery 快照仅用于历史回退。

```sh
python lib/tools/daw_backup/live.py          # 只预览
python lib/tools/daw_backup/live.py --check  # 检查全部链接
# 先保存并正常退出 Bitwig、REAPER 和独立音源：
python lib/tools/daw_backup/live.py --apply  # 首次迁移；重装后也用于重建入口
python -m pytest -q lib/tools/daw_backup/test_live.py lib/tools/daw_backup/test_snapshot.py lib/tools/bitwig_library/tests/test_controller.py
```

迁移只支持已核对的同文件系统 rename；不自动合并/覆盖冲突目录，也不静默退回复制。
恢复时**优先保留 UserData 主数据并重建 home 链接**，不要用旧快照覆盖新偏好。
若重装后软件已创建同名实体目录，先退出软件，把这些新默认目录另行留存并检查，才重建链接。
若用户名或挂载点改变，先审查绝对路径与内部指向 UTRP/gral 的链接。

**明确边界：**没有迁移整个 `~/.config` 或 `.BitwigStudio`，账号激活、遥测、缓存仍留 home。
旧的 `~/.config/Surge XT.settings` 是 Surge **独立程序**的 JUCE host 设置，不是 DAW 内
Surge 插件的用户偏好；此单文件仍留 home、由 Recovery 快照保存，没有冒充安全实时链接。
插件实际偏好 `.Surge XT/SurgeXTUserDefaults.xml` 已在 Storage。
`plugin-states` 经重启实测会被 Bitwig 清空并重建，属于运行时临时数据，已排除实时迁移。
系统 Sway/音频规则与服务继续由仓库源码/部署文件管理并备份；没有搬迁运行中的 WirePlumber
设备状态或整个系统配置。安装软件本体的路径未变。

初次迁移前后核对了 13,636 个文件/链接条目（含随后排除的 `plugin-states`）：目录及普通文件 inode/大小/权限一致，
非大型内置包文件另做 SHA-256 比较，内部 symlink 目标保持。未执行重装系统演练。


## 保存边界

- **UTRP 源码**：`lib/tools/chordlab*`、`guitar_frontend`、`bitwig_library`、
  `audio_routing`、`plugin_windows`，以及此目录的备份脚本、配置和测试。
- **Storage 工程与采样**：`~/storage/daw/`。Library 为
  `Library/Library.bwproject`，采样为 `samples/`；保留整个目录，不仅一个工程文件。
- **Storage 重装快照**：`~/storage/daw/Recovery/<UTC时间>/`。包括 home 中实际部署的
  CLAP、controller、Bitwig prefs、Surge 主题/用户预设、sfizz 设置、REAPER 配置、
  Sway 配置、音频规则、三个 systemd 用户服务、桌面启动项和音频辅助脚本。
- 大文件、二进制、账号激活数据不进 Git；快照只在私有 Storage。
  **本轮没有自动 commit/push**。当前未提交源码也进入 `utrp-working-tree.tar.gz`，
  因此不会把“位于仓库目录”误认为“已经提交到 Git”。

## 生成及校验

在仓库根目录运行：

```sh
python lib/tools/daw_backup/snapshot.py
# 初次或更新 DAW/系统插件/内置包时，加上可重下载的运行时资源：
python lib/tools/daw_backup/snapshot.py --include-assets
python -m pytest -q lib/tools/daw_backup/test_snapshot.py lib/tools/bitwig_library/tests/test_controller.py
```

脚本先检查必需路径，再创建唯一时间戳目录，不覆盖旧快照。所有归档完成后逐文件读回，
生成 `manifest.json` 的 SHA-256 校验清单，最后移除 `INCOMPLETE`。
保留 `INCOMPLETE` 的目录视为未完成，不能用作恢复基线。
部署路径中的 symlink 解引用保存内容，避免重装后只剩指向旧 home/gral 的断链。
源码快照含 Git 跟踪文件及非 ignored 的未提交文件；不含 `.git` 历史、`target` 构建缓存，
也不是 Git remote 的替代。源码恢复时覆盖到正确版本的仓库工作树，再审查差异。

**应用运行中只能备份已写盘的设置，不包括内存中尚未落盘的设置。** 完整重装前，应保存并
正常退出 Bitwig/REAPER/Surge 后，再执行一次快照。目前期望音频设置为 PipeWire / System Out、
Block size 手动 128（若爆音退回 256）；恢复时请显式核对，不只依赖旧 prefs。
Library 保存的 Glass Air 推子为 −9 dB，其余 AG 初始 −12 dB；以之后用户保存的工程为准。

校验某快照（将 `SNAPSHOT` 换成实际路径）：

```sh
python - SNAPSHOT <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
assert not (root / 'INCOMPLETE').exists()
for name, expected in json.loads((root / 'manifest.json').read_text())['sha256'].items():
    with (root / name).open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == expected, name
print('All archive checksums match')
PY
```

## 恢复顺序（先审查，禁止盲目覆盖）

1. 保留/挂载 Storage，恢复 UTRP 仓库。最好保持原用户名和 `~/work/utrp`、`~/storage` 路径。
   原生工程、sfizz 采样、desktop Exec、prefs 中可能含绝对路径；换用户名须重新定位。
2. 按 `packages.txt` 核对系统环境、PipeWire/WirePlumber、Sway、realtime 权限与插件依赖。
   不要机械安装整张包表；它是版本清单。不同发行版/架构应重新安装系统插件或重编译 CLAP。
3. 安装 Bitwig。启用 `--include-assets` 的快照额外保存本机 Bitwig 6.1.4、内置包和系统
   CLAP/VST3/Surge 工厂资源，供同平台恢复参考，不直接覆盖另一系统的 `/usr`。
4. 关闭音频软件。若 `UserData` 完整，先执行 `live.py --apply` 重建链接，沿用最新主数据。
   只有需要快照回退时，才把 tar 解压到**临时目录**，检查后恢复至对应实体目录；不覆盖 home 链接。
   先恢复自制 `.clap` 和 `Bitwig Studio/Controller Scripts/UTRP`；恢复 prefs、主题、音色和采样。
   REAPER 的旧路径兼容资料也保留，但本项目仍以 CLAP 产品线为准。
5. 只恢复 `utrp-plugin-windows` 用户服务、现有 PipeWire EQ 规则和插件浮窗规则；不要恢复已移除的两个自定义音频服务；核对 Sway 的
   `focus_follows_mouse no` 及 `include` 路径，再 `systemctl --user daemon-reload` 并启用服务。
   不要把旧 WirePlumber 的设备 ID 或音量状态视为新硬件上必然有效。
6. Bitwig 自行重新登录/激活。**不备份 Bitwig `.activation-*`、REAPER license、遥测或登录凭据**。
   私有 prefs 仍可能包含本机路径/设备标识，不发布到 Git。
7. 打开 Storage 中 Library，按[Bitwig 内音频设置](../audio_routing/README.cn.md)检查实体 Spark GO 输入、手动所选输出、128 buffer、两个 Keystation 端口、踏板极性；
   脚松开时开机。检查 Chord Lab/Surge/sfizz、四条 AG 音色及吉他只显示的 channel 2→15 路由。
8. 正式录音工程不要命名为 Library。当前 controller 的历史白名单为 `Library` 与
   `Library-migration`，还要求共享轨及 Chord Lab 结构匹配。其他名字不执行自动停轨、Arm、
   监听/开窗或调号联动；Keystation Transport 与系统音频优先级是另外两套机制。
   `Exclusive audition + editors` 存在 **host preferences**，不是 `.bwproject` 中的开关；
   工程里保存的是已执行后的轨道状态、设备与路由。要多轨录音须手动恢复需要的 Active/Arm/Monitor。

## 验证与限制

本轮新增普通工程全轨状态不变、跨工程待执行动作取消的 controller 模型回归；
备份测试覆盖必需配置、symlink 内容实体化、未提交源码及凭据排除。没有实际重装系统，
所以“归档可校验”不等于在空白系统上已完成端到端恢复。
**Storage 当前与 home 在同一块磁盘上：防重装误删 home，不防硬盘损坏或整盘格式化。**
重装前须另备份到独立磁盘；不要格式化承载 Storage 的分区。

运行时资源归档使用未压缩 `.tar`，避免重复压缩大型音色包；保留厂商安装布局的 symlink（例如 `/usr/bin` 指向 `/opt`）。home 定制快照仍解引用部署链接。恢复本地解包的 Bitwig 时直接使用其 `opt/bitwig-studio/bitwig-studio`，不要假设其中的 `/usr/bin` 绝对链接可直接运行。

### 2026-10-19 工程与最近项目清理

- 按用户确认，删除 `Grid Lab`、`utrp-lab`、`Library-migration` 及各自自动备份；正式 `Library`、其资源与自动备份保留。
- Bitwig 关闭时，将 prefs 中的最近项目从 10 条清理为仅 `~/storage/daw/Library/Library.bwproject`。已逐字节确认其他偏好不变，并核验 Library 工程 SHA-256 不变；未做本次 GUI 重开验证。
- 清理前 prefs 位于 `~/storage/daw/Backups/library-only-recents-20261019T160620.835576Z/6.1.4.prefs.before`。该副本仅供偏好回退；恢复旧 prefs 会带回失效的最近项目记录，不会恢复已删除工程。现有 `backup.toml` 已覆盖 prefs，无需新增路径。

### 2026-10-19 吉他输入恢复与重开验证

- 无输入电平时，Audio 的 Selected Device(s) 实际为 `GB203 High Definition Audio Controller`，没有输入端口；系统虽已识别 Spark GO，Bitwig 只有输出连接。这是设备选择问题，不是吉他效果器缺失。
- 通过 GUI 选择 `Spark GO USB` 并重启音频引擎，恢复 `capture_MONO → Bitwig in1`。正常保存、退出、重开后，Audio 仍为 Spark GO、手动 128 samples；输入连接自动恢复，`AG - 02 Soft Prism` 与 Master 出现电平。未改效果参数或 controller；实际听感仍由用户确认。
- 已回到 Soft Prism 并保存 Library，最近项目仍只有正式 Library。证据与前后工程／prefs 在 `target/guitar-input-20261019/`；恢复清单现有 prefs 与 Library 路径已覆盖本次改动。今后若出现 `[missing]`，先核对 Audio 设备，不能仅凭系统默认输出是 Spark GO 判断输入已接通。没有验证物理热插拔或推断此前为何切到 HDMI。

### 2026-10-18 收尾验证

- 28 项备份、迁移与 Library controller 回归测试通过。
- Bitwig 实际重开加载了 Chord Lab / sfizz；Audio 页面仍为 Spark GO USB、128 samples。
- 使用 GUI 临时改变显示偏好，确认 Storage prefs 的写入时间和内容变化；随后恢复原值，
  用 Ctrl+S、Ctrl+Q 正常保存退出。退出后 10 个目录链接仍全部有效。
- 本轮只调整存储部署，没有改音源、MIDI 路由或 Library 互斥试听行为；没有 commit/push。


### 2026-10-19 固定输入方案（取代上述直接硬件输入）

- 唯一正式配置：PipeWire / System Out / 手动 128 samples；Library 四条 AG 与 raw detection 使用 `Spark-GO-Guitar → capture_MONO`。`Spark-GO-Internal-Capture` 是同一个 loopback 的后端，不是重复设备。没有部署临时 JACK／null-source 规则。
- 新增必需恢复项 `~/.config/systemd/user/utrp-guitar-input.service`；输出策略与该服务均开机自启。源码、TOML 与服务配方在 `lib/tools/audio_routing/`。系统默认麦克风保持 SF-558；Spark 缺席不接麦克风。
- 正常退出、重新创建虚拟源并重开 Bitwig 后，保存的输入按名称恢复；实际 graph 为 Spark → 固定源 → Bitwig，buffer 128。切换钢琴／吉他时 Arm 互斥；controller 和 MIDI 绑定未修改。raw detection 保持 −∞。
- 通过 profile 暂时关闭／恢复 Spark 验证：虚拟源始终接到 Bitwig，缺席时后端无输入，恢复后自动接回 Spark。不是物理拔插／整机重启／真人听音测试。
- 66 项音频路由、备份及 controller 回归测试通过；10 个 Storage 目录链接有效；策略 dry-run 无待修正项。截图和 graph 在 `target/input-autoconnect/`。真实吉他和键盘试听仍待用户确认；未 commit/push。

### 2026-10-21 Library 两组试听

- 已部署 controller 0.8：已知 MIDI 音色与四条 AG 吉他轨分别组内互斥，跨组保留 Active / Arm / Monitor。首次分别选一条；不创建轨道、不改音色参数或正式工程文件。窗口仍跟随最新选择。
- `backup.toml` 的 `Bitwig Studio` 项已覆盖控制器；旧版备份在 `~/storage/daw/Backups/library-two-groups-20261021T163556.713740Z/`。实时主目录和 10 个 home 目录链接保持；恢复时沿用该结构。
- 40 项相关回归通过，部署文件与源码逐字节一致。当前环境未发现可访问的 Bitwig/Sway 会话，宿主重载、实际双组发声和保存重开待用户验证。恢复后在 Library 分别选择一条 MIDI 音色和 AG 吉他轨，再检查二者均 Active / Arm / Monitor ON；普通工程不得受此互斥影响。
- 未 commit/push；收尾运行 `snapshot.py` 保存部署文件与未提交源码。快照只覆盖已写盘状态，不能代替实际宿主验收。

### 2026-10-21 Spark GO 采集状态恢复

- 排查并恢复采集错误持续增加的运行状态，详见 [音频路由记录](../audio_routing/README.cn.md)。未新增配置或改变恢复路径；Spark 原 duplex profile、麦克风连接、自动路由服务均已恢复。不要把临时时钟隔离测试固化为断开 Beat Lab 麦克风的恢复步骤。
- Library 工程未保存，音色、音量及 controller 未修改。快照只保护已写盘内容，不含当前未保存工程状态；未 commit/push。用户听感及重开稳定性待确认。

### 2026-10-21 吉他仅监听（controller 0.9）

- 已部署并实机确认 AG 选轨不自动 Arm，Monitor ON 保持；MIDI 行为不变。Beat Lab 轨 Arm 及插件内部录音经界面确认均未开启；用户确认强杂音已消失，本轮不再采集诊断音频。
- 恢复清单沿用 `Bitwig Studio` 项；修改前 controller 0.8 和磁盘工程备份位于 `~/storage/daw/Backups/library-monitor-only-20261021T165825.279088Z/`。现行源代码 40 项相关测试通过。收尾保存当前 Library 并执行 Recovery 快照；未 commit/push。

## 2026-10-21：Chord Lab 20 品部署

- 安装 Chord Lab 0.2.13 至 `.clap` 的既有 Storage 实体目录；未替换目录 symlink。指板 20 品、最高完整手位 18 品，高八度候选与导航／v3 状态验证同步。
- 用户批准后保存并正常退出／重启 Bitwig；Library 原音色、调性保留。Chord Lab 恢复 920×703，重开后仍为该尺寸；未改全局布局策略。
- 旧插件及工程备份：`~/storage/daw/Backups/chordlab-twenty-frets-20261021T170800.635371Z/`。验证证据在 `target/chordlab-twenty-frets/`：569 项 Chord Lab Python 测试、396 项相关回归、9 项 CTest、构建和安装后二进制 probe 全部通过；10 个实时 Storage 链接有效。
- 本次源码未 commit/push；恢复快照包含当前未提交源码和新插件。大窗口仅确认曾达到最大尺寸，未断言其具体触发原因。

## 2026-10-21：关闭两组自动 Arm

- Library controller 0.10 两组均 Monitor ON／Arm OFF；宿主 Recording 的 Instrument tracks Auto-arm 关闭，Audio tracks 原本已关闭。全局选轨偏好改变，但 controller 不改普通录音工程状态。
- 旧控制器／偏好／工程备份：`~/storage/daw/Backups/library-no-auto-arm-20261021T171311.609945Z/`。40 项回归通过；实际 MIDI／吉他切换及恢复证据：`target/library-no-auto-arm/`。
- 部署在既有 Storage-backed controller 目录，源码未 commit/push；快照保存当前源码、已落盘偏好和工程。

## 2026-10-21：输出自动接替响应（历史，随后已移除）

保留 Spark GO → Woo Audio（EQ）→ 其他实体输出的规则；`audio_routing/policy.toml` 的轮询改为 0.25 秒，服务已重读配置并 enabled/active。39 项音频路由测试通过；重载前后所有实时连接相同、dry-run 无操作。移除 Spark 的内存图模拟选择 Woo EQ；本轮未进行物理拔插或无爆音听感验收。证据：`target/audio-fallback-20261021/`。源码未 commit/push，恢复快照保留当前源码配置。

## 2026-10-21：移除自定义音频服务（当前恢复规则）

用户要求仅在 Bitwig 内选择输入与输出。两个音频服务已停用、删除，恢复清单不再包含它们；旧快照及上方历史中的虚拟输入、自启与自动回退方案均不应恢复。系统音频、Woo EQ、插件窗口服务不变。Bitwig 未运行且 Spark 缺席，未改工程/偏好；四条 AG 与 raw detection 的实体 Spark 输入映射仍待现场完成，Beat Lab 输入总线也需在宿主中核对。详见 [当前路由说明](../audio_routing/README.cn.md)。删除前备份位于 `~/storage/daw/Backups/retire-audio-services-20261021T191202Z/`。

## 2026-10-21：Bitwig 原生 Spark 输入/输出已完成

已在 Bitwig 内保存 `Spark GO USB + WooAudio` Combined Device（Spark clock master，128 samples）、四条 AG 与 raw detection 的实体 Spark mono 输入，以及 Master 的 Spark 立体声输出。Woo 切换只改 Master 输出，不替换整个音频设备组。正常退出重开验证通过；两个自定义服务仍为 not-found/inactive。此条完成上方“实体映射待现场完成”的遗留项；不恢复虚拟输入。`beat lab mic` 未重新映射或 Arm。41 项 Library/备份回归、10 个 Storage 链接检查通过。前置备份 `~/storage/daw/Backups/bitwig-direct-spark-20261021T192545Z/`，证据 `target/bitwig-direct-spark/`；本轮文档未 commit/push，收尾运行恢复快照。

## 2026-10-21：恢复 Bitwig 的 Workspace 2 规则

现有必需项 `.config/sway/utrp-plugin-windows.conf` 现在包含 Bitwig 主窗口的 Workspace 2 assign 规则，源码配方为 `lib/tools/plugin_windows/sway.conf`。恢复该文件并保留主配置中的 include 即可；不需要新的服务或启动脚本。主窗口与两个已打开的插件浮窗已迁至 Workspace 2，配置校验/reload 通过。没有改动音频路由或工程文件；本轮源码和文档尚未 commit/push，收尾保存恢复快照。

## 2026-10-21：Chord Lab 默认小窗口持久规则

恢复现有 `.config/sway/utrp-plugin-windows.conf` 时使用最新 `lib/tools/plugin_windows/sway.conf`：包含 Workspace 2 主窗口分配及 Chord Lab 创建时立即浮动、920×703 的原生规则。该规则修复先平铺后轮询浮动的开窗尺寸竞争，不能只恢复旧的 exec_always 行。无新服务或插件二进制变更；六次编辑器重开验收通过。修复前备份：`~/storage/daw/Backups/chordlab-window-default-20261021T194605Z/`；证据：`target/chordlab-window-size/`。本轮未 commit/push，执行恢复快照保存工作树与部署配置。

## 2026-10-21：Keystation 1.1 手动 Arm / 文件夹

恢复 `Bitwig Studio/Controller Scripts/UTRP/Keystation.control.js` 与 `Keystation.config.js` 的 1.1 配方：上下选可见轨，左右收起/展开文件夹，中央仅切换 Arm，独立 Record 实际录音。原 Library 0.10 自动 Arm 关闭规则与 Spark/Woo 设置不变。405 项相关回归通过，宿主控制台确认 ready；未在正式工程创建测试录音。部署前备份 `~/storage/daw/Backups/keystation-fold-arm-20261021T195527Z/`；详见 [按键说明](../bitwig_library/KEYSTATION.cn.md)。源码未 commit/push。

## 2026-10-21：Library 推子统一

保存后的 Library 工程：可听音色 −2 dB，文件夹/共享 MIDI/Master 0 dB，raw detection 保留 −∞。114 条宿主校验错误 0，406 项回归通过。配方在 `bitwig_library/levels.toml`，一次性维护工具不加入自动启动；正式控制器未改变。修改前工程：`~/storage/daw/Backups/library-levels-20261021T201337Z/Library-live-before.bwproject`。详见 [音量说明](../bitwig_library/LEVELS.cn.md)。未 commit/push，快照保存工作树和当前工程。

## Chord Lab 0.2.14 默认启动（2026-10-21）

- 新建/重载默认 Sustain On；原生窗口映射后获取一次电脑键盘 Focus，不持续抢焦点。实体 MIDI 独立。920×703、20 品、音频路由、Arm 与 Library 两组互斥策略不变。
- 安装目标仍为 `~/.clap/Chord Lab.clap` → Storage UserData，CLAP ID 与旧工程兼容；正常保存退出后原子替换插件，再打开 Library。
- 回退：`~/storage/daw/Backups/chordlab-startup-20261021T203104Z/` 保留旧插件和工程。975 项 Python、9 项 CTest、真实 CLAP 与隔离 Focus 验证通过，Bitwig 重载检查 S/A 绿色及电脑按键事件触发音源。详情见 Chord Lab README。
- 没有新增服务；未 commit/push，收尾 Recovery 快照包含当前未提交源码与部署文件。

## 2026-10-23：Chord Lab 0.3.5 游戏 UI 与真实验收

- 正式 `~/.clap/Chord Lab.clap` 已在现有 Storage 目录原子更新至 0.3.5，SHA-256 `8da1fc121f6f3ea838f6e8bb0794350d3fe0ca3268106a063ad6667d71dc05d8`。包含单列阶梯、灰色临时接近+色点、转调说明，以及仅位于右侧游戏面板顶部的倒计时条。正常模式尺寸和音乐绘制不变。
- 旧 0.3.3、0.3.4 和两次工程备份保存在 `~/storage/daw/Backups/chordlab-live-acceptance-20261023T172629Z/`。沿用清单现有 `.clap`、Library、prefs 与源码项；未新增服务、统计目录或改变音频规则/controller。
- 保存/退出/更新/重开正式 Library 于 Workspace 2；Spark 硬件 mono → Bitwig、Bitwig stereo → Spark，用户确认 MIDI/电脑/吉他三种声音正常。最终 20 次开合验证边界、16 px 间距、组合居中，关闭 G 后正常音乐区像素一致。
- 真实单音输入链成功计分、超时钢琴回放与默认 Sustain 对照通过；最后修订版本另通过 12 项 CTest、隔离 GUI/CLAP probe。709 项相关 Python、123 项根 Rust（3 个超大覆盖测试仍 ignored）、7 项游戏 Rust、Clippy、2 项 Guitar CTest 通过。4,800 题均衡模拟覆盖 24 调，成功数 171–206；不是全球历史存储或真人完成数量。
- 证据 `target/live-acceptance-20261023/`；没有对全部音色逐一重新听音，也没有宣称物理热插拔、长期无爆音或实体双人计分均已覆盖。源码未 commit/push；收尾 Recovery 快照保护当前源码与部署文件。

## 2026-10-23：Library 冷启动 Focus / Active 修复

- Library controller 0.11：保存时选中文件夹或无选中轨道，也会一次性打开共享 Chord Lab；设备列表延迟就绪有有界重试。此分支不改音色 Active、Arm、Monitor 或其他编辑器，普通工程不启用。
- Chord Lab 0.3.6：等待宿主打开事务稳定后申请初始键盘焦点；宿主只聚焦外层容器时，将焦点传入自身键盘 peer。手动 A OFF 和离开插件窗口不触发抢焦点。`theme.toml` 的 `interaction.focus_settle_ms=300` 独立于视觉配色。
- 现有 `utrp-plugin-windows` 布局策略仅对新发现的 Library 共享窗口执行一次 compositor focus，且当前焦点必须仍在同一 Library 主窗口/编辑器。不会因 G 展开收起、移动、点击其他应用或定时轮询反复抢焦点；没有新增服务。
- 验证：927 项 Python、12 项 CTest、隔离 Sway 的 CLAP 输入/状态/焦点测试通过；新增“宿主稍后聚焦容器”的断言旧 0.3.5 失败、新版通过。真实 Library 冷启动不点击插件/A 即 S/A 双绿；电脑 A 触发音符及 Bitwig 音量表；离开 3 秒仍保持主窗口焦点，返回插件恢复 A。
- 证据：`target/focus-startup-20261023/`。隔离测试必须使用 compositor-managed 窗口；早期 override-redirect 测试在 rootless Xwayland 得到 PointerRoot，不能作为生产缺陷证明。最终旧/新对比见 `probe-old-host-settle.log` / `probe-final.log`。
- 本轮不声称重新听测实体 MIDI/吉他或所有音色。插件 SHA256：`9f35503a54f4414ee11aa16c6675c4192e2c6d4cc3375be64a57c0ad6c2b9a41`。原件备份：`~/storage/daw/Backups/chordlab-focus-20261023/`。未自动 commit/push。

## 游戏 UI 更新（2026-10-23）

恢复清单现包含 Chord Lab 0.3.7：灰色圆角游戏面板、同宽倒计时、20 px 外边距、Demo 加分提示、9 和弦密集预览自适应及所有过渡灰胶囊色点。旧插件和保存前工程备份位于 Storage 的 `Backups/chordlab-game-ui-20261023/`。源码尚未 commit/push，需保留本次 Recovery 源码快照；配方见 `chordlab/theme.toml` 和 `chordlab_clap/README.cn.md`。

### 2026-10-23：Chord Lab 0.3.8 固定级数显示

恢复清单升级至 0.3.8：关系大小调统一大调胶囊级数和固定色序，调外和弦不占用左侧槽位；底层循环、覆盖与转调仍区分大小调。详见 `chordlab_clap/README.cn.md`。本次源码未 commit/push，以 Recovery 工作树快照保底。

### 2026-10-23：Chord Lab 0.3.9 游戏设置胶囊

游戏设置改为等高、同字体胶囊，Play/Demo/Mod 并排一行，方向下拉及开关也使用胶囊；普通模式无改动。恢复时需要同时保留 `game_controls.h`、`game_panel.*`、`game_wheel_value.h` 与现有主题生成配方。未 commit/push。

- 2026-10-23：0.3.9 胶囊设置与同色倒计时底轨已部署，备份 `Backups/chordlab-capsule-controls-20261023/`。真实 Library 在 Workspace 2 打开，但 Spark GO USB 未枚举，音频引擎报无输出设备；没有改声卡设置或保存工程。声音验收待设备恢复，安装哈希与测试见 Chord Lab README。

## 2026-10-23：System In + Out 错接麦克风

Spark GO 本次已在 USB/ALSA/PipeWire 正常枚举，但 Bitwig Audio 选成了 `System In + Out`、自动 256 samples，实时图为 SF-558 → Bitwig in1，输出仍到 Spark。此配置跟随系统默认麦克风，不能替代实体 Spark 输入；无法从现有日志确认谁/什么操作改了选择。

已通过 Bitwig GUI 恢复原有 `Spark GO USB + WooAudio` Combined Device（Spark clock master、手动 128 samples）；Woo 缺席显示 Not present，Spark 仍可工作。关闭设置应用后，实时图恢复 Spark capture_MONO → Bitwig in2、out1/out2 → Spark stereo；raw detection 仍为 Mono capture_MONO、Monitor On、−∞，Master 有电平。用户确认“有了”。未改系统默认麦克风、未加服务、未 Arm/录音。

偏好文件已自动落盘（16:33:21）；未重启验证，未确认工程另存成功，不声称做了新的冷启动验收。修改前备份 `~/storage/daw/Backups/spark-routing-20261023/`，证据 `target/spark-no-sound-20261023/`。以后保留该设备组，换扬声器只改 Master 输出；不要为恢复输出切到 System In + Out。

## 2026-10-23 Focus 修复部署

Chord Lab 0.3.10 已通过原 Storage `.clap` 链接部署，修复同一 Bitwig 外框下隐藏 `InputOnly` 焦点代理的交接。回滚插件与未改动的 Library 备份：`~/storage/daw/Backups/chordlab-focus-proxy-20261023T164424/`。真实 Library 连续三次冷启动自动 S/A 双绿，未更改 controller、音频或录音配置；恢复清单已标记 0.3.10。当前源码未 commit/push，需随本轮恢复快照保存。

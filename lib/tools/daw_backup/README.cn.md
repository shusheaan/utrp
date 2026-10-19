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
5. 恢复三个用户服务 `utrp-plugin-windows`、`utrp-audio-output`、`utrp-guitar-input`、PipeWire 规则和插件浮窗规则；核对 Sway 的
   `focus_follows_mouse no` 及 `include` 路径，再 `systemctl --user daemon-reload` 并启用服务。
   不要把旧 WirePlumber 的设备 ID 或音量状态视为新硬件上必然有效。
6. Bitwig 自行重新登录/激活。**不备份 Bitwig `.activation-*`、REAPER license、遥测或登录凭据**。
   私有 prefs 仍可能包含本机路径/设备标识，不发布到 Git。
7. 打开 Storage 中 Library，按[固定音频路由](../audio_routing/README.cn.md)检查 `Spark-GO-Guitar` 输入、Spark 输出、128 buffer、两个 Keystation 端口、踏板极性；
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

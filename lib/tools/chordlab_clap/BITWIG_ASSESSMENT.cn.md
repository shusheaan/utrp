# Bitwig 移植评估（2026-10-17）

[English](BITWIG_ASSESSMENT.md)

> 后续实机进展见 [首次运行验证](BITWIG_RUNTIME.cn.md)。下文保留较早的静态评估，
> 其中“未安装”及旧键位/二进制信息不是当前状态。

## 结论与范围

现有 `Chord Lab.clap` 已是独立插件，不是需要 REAPER 在后台运行的 JSFX 桥接器。
同一台 Linux x86_64 电脑应先让 Bitwig 扫描现有插件，而不是重写算法或制造宿主专版。
这是代码与官方文档的静态评估；本机 PATH、常见 `/opt` / Flatpak 安装位置未发现
Bitwig，本轮没有安装、启动 Bitwig，也没有修改插件、音色或正式工程。
当前二进制 SHA-256：`a17a614adaebb33fb31b346d51afca49610e75203a23d27151be448acec41c44`。

Bitwig 官方明确支持 CLAP 与内建设备共用设备链，提供插件独立进程模式。
这支持接口可行性判断，不替代实际宿主验收。
[插件设备](https://www.bitwig.com/userguide/latest/vst_plug-ins/)；
[隔离模式](https://www.bitwig.com/userguide/latest/vst_plug-in_handling_and_options/)。

## 本地结构与可复用范围

```text
lib/tools/chordlab/                 EEL 音乐核心、记忆、MIDI、谱表/指板绘图
          ↓ 编入资源包
ysfx                               在插件内部执行 EEL
          ↓
lib/tools/chordlab_clap/            JUCE GUI、键盘队列、资源/state 适配
          ↓ clap-juce-extensions
Chord Lab.clap                     同一个插件供 REAPER / Bitwig 加载

lib/tools/library/*.lua            仅 REAPER：切音色、独占路由、窗口显示
```

- `CMakeLists.txt:19–49`：资源编入二进制；MIDI effect；稳定 ID
  `org.utrp.chordlab`；一进一出 MIDI，零音频端口；JUCE/ysfx 链入插件。
- `embedded_source.cpp`：每个实例把内嵌资源展开到独立临时目录，不读取原仓库位置。
  仍依赖可写临时目录、系统库和 Linux X11/XWayland，不是完全无外部依赖。
- `port_upstream.py`：构造时加载内嵌引擎，18 参数；state 不保存原机器 JSFX 路径。
- `editor.cpp` / `control.cpp` / `physical_keys.cpp`：电脑输入由插件自行处理；
  不依赖 REAPER Lua/VKB，但依赖宿主把焦点键盘事件交给编辑器。
- `chordlab.jsfx:@serialize`：v2 保存七音级的和弦记忆；载入重置瞬时持音/Sustain。
- `Library mode.lua:25–68`：Solo、MIDI send、音源 offline/online、窗口配对均是
  REAPER API 行为，不属于可直接带走的插件功能。

因此和弦、转位、三/七/九和弦、七音级记忆、谱表/钢琴/指板、混合输入和按钮
原则上复用现有实现。整个 `synth.rpp`、REAPER Input FX 槽和 Lua 管理器不能照搬。

## 建议的首次验证链

```text
硬件 MIDI + 插件获得焦点的电脑键盘
                 ↓
             Chord Lab
                 ↓
              Surge XT
                 ↓
            Reverb → Master
```

先做一个空工程、一条乐器轨，不先迁移 95 音色库。验证成功后，再建立共享
Chord Lab 控制轨与乐器轨。Bitwig 的 Note Receiver 可以接收项目中的 note 信号，
但它位于设备链中：能听到不等于该轨已经录到处理后的和弦。
生成 MIDI 的录制须验证目标轨选择的输入取样位置，并实际检查生成的 note clip。
[Note Receiver](https://www.bitwig.com/userguide/latest/routing/)；
[轨道输入、监听与录制](https://www.bitwig.com/userguide/latest/recording_clips/)。

## 必须验证或补齐

| 项目 | 当前事实 / 风险 | 下一步 |
|---|---|---|
| 扫描、分类、后级发声 | 已声明 note-effect；还没有 Bitwig 实机证据 | 使用同一 binary 加载，验证纯 MIDI 前置链 |
| 焦点与快捷键 | JUCE + X11；不抢系统/global 快捷键 | A–J、Tab、Enter、分号、鼠标、失焦、关窗、长按逐项测 |
| 静止时电脑发音 | GUI 队列在 process 回调消费；未见显式键盘唤醒请求 | transport 停止、闲置、切轨后测试；必要时处理 host wake-up |
| Suspend | adapter 返回 CONTINUE，但宿主仍有休眠策略 | 初始排障可设 Never；再验证默认策略，不能只测播放中 |
| 输入通道 | MIDI 1.0；ch16 被当作内部控制，不是普通演奏通道 | 保持通道、不要强制 MPE；测同音所有权与真实力度 |
| state | 可移植 state 已存在；UI 没有通用导入/导出按钮 | 先测试各宿主保存重开；要搬现有记忆再加预设交换入口 |
| 自动化 | 18 参数混有音乐参数、内部命令、状态显示 | 检查可自动化参数和量化；不要把所有参数当连续调制目标 |
| 生命周期 | 独立进程、bypass、休眠/恢复会改变调用时序 | 关窗、移除、恢复、两个实例、循环/停止/保存回归 |
| 构建环境 | Linux ELF x86_64，引用 GLIBC_2.43 符号 | 同机原生环境先测；Flatpak/旧发行版另查运行库或重建 |

Bitwig 提供 Never、When silent、Trust plug-in 三种 Suspend 方式。
这是纯 MIDI、GUI 可生成事件插件的重点测试项。
[官方 Inspector/Suspend 说明](https://www.bitwig.com/userguide/latest/the_unified_modulation_system/)。

两个宿主加载同一个文件，不表示两个实例的和弦记忆会实时同步。
REAPER/Bitwig 工程格式和宿主预设格式不能假定互通。
macOS/Windows 需要对应平台构建；不能复制这个 Linux ELF 文件过去直接使用。

## 未来版本：可以继续扩展，但不是自动获得所有 CLAP 能力

1. **播放中转调是实际新需求。** `chordlab.jsfx:68–69` 和 `midi.jsfx-inc:93`
   目前主动锁住持音或播放/录音期间的调性切换。需定义立即转调/下一和弦/下一小节、
   旧音如何释放和 Sustain 行为，再实现双宿主一致的规则。
2. **sequencer 属于引擎功能，不属于 REAPER Lua。** 宿主时间已转入 ysfx，
   但精确节拍调度、跳转/loop、离线 render 是新增实现和测试。不能用 GUI 定时器做节拍器。
3. **CLAP 格式不等于 MPE/polyphonic modulation。** 目前没有原生 CLAP note expression
   路径；ch16 控制协议也与完整 MPE 有冲突。真正需要时再隔离内部命令和外部 MIDI、
   扩展事件模型，不为普通和弦功能提前重写整个核心。
4. **保持一个产品。** 固定 plugin ID、既有参数 ID/含义；新增参数要更新现有固定 18
   参数适配并测试旧工程。扩展 state 时写迁移。公共音乐逻辑不分 REAPER/Bitwig 两份。
5. **不急于废掉 ysfx。** 当前和弦工具继续用 EEL 是可行的；只有真实表达力、性能或
   事件模型需求碰到限制时，才局部迁移到原生代码，保留已有行为测试。

## 整个音色库迁移是另一项工作

实际 `synth.rpp` 有 93 个 Surge CLAP、2 个 sfizz LV2，以及基础组的 ReaVerbate。
Surge 与 Chord Lab 是优先试搬对象。钢琴不能简单假定 LV2 实例可原样加载；Bitwig
官方列出的插件格式为 VST2.4/VST3/CLAP。sfizz 上游提供 VST3，可以重新加载原 SFZ，
但需重建设置并验收音量与声音；ReaVerbate 也不能因为 RPP 标成 VST 就认定独立可用。
[Bitwig 格式](https://www.bitwig.com/modern-foundations/)；
[sfizz 插件源码/格式](https://github.com/sfztools/sfizz-ui)。

## 条件性工作量估算

以下是工程量，不是已运行后台任务的完成时间。前提：Bitwig 已安装可用、同机原生
Linux、可实测硬件，没有重大的宿主/运行库兼容缺陷。

| 目标 | 估算 |
|---|---|
| 现有 binary 扫描、显示、电脑/实体输入接 Surge 首次发声 | 0.5–2 小时 |
| 当前功能的双宿主验收、录制模板、有限适配修复 | 累计约 1–3 工作日 |
| 通用和弦记忆导入/导出（若需要跨项目搬状态） | 另约 0.5–1 工作日 |
| 完整音色库、sfizz 格式替换、效果器与选轨流程 | 插件验收后另约 2–5 工作日；严格复刻窗口自动化另评估 |
| 新转调/编配/sequencer、MPE、跨操作系统 | 独立需求，不能算在这次移植内 |

优先级：真实硬件输入基线 → Bitwig 单轨最小链 → 双宿主功能/录制验收 →
共享模板/音色库 → 新音乐功能。当前实体 MIDI 未进入宿主的问题仍未完成真人复测，
不能用换 DAW 掩盖，也不能把之前模拟 MIDI 的通过记录当作硬件已验收。

## 双宿主发布验收门槛

- 同一源码和 binary 哈希，分别记录宿主版本、隔离设置、采样率和 block size。
- 相同确定性输入：音高、channel、力度、顺序、时序、Note On/Off 配对与同音所有权。
- 真电脑输入、真实 MIDI、两者混合；灰点显示与声音人工核对。
- 停止、播放、录音、循环、闲置后唤醒；失焦、关窗、bypass、多个实例。
- 实录生成的和弦而非仅输入触发；播放录成的 MIDI 不应重复生成。
- 两边各自保存、退出重开；旧版本 state 迁移、Sustain 安全复位。
- 现有 REAPER 基线不回退；Bitwig 未实测前不能标记兼容认证完成。

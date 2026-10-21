# Ambient Guitar — 四条实时吉他音色

> 当前行为更新：controller 0.8 将 MIDI 与吉他分为两组，组内互斥、组间可同时演奏。下文 0.6 的全局互斥及旧验收属于历史记录；见 [当前说明](README.cn.md)。

[English](AMBIENT_GUITAR.md)

## 工程与路由

工程仍为 `~/storage/daw/Library/Library.bwproject`；新建 **Ambient Guitar** 分组，
不是另一个工程，也不是四份 Guitar Frontend。已有合成器音色、识别器和 Chord Lab 引擎不变。

```text
Spark GO USB mono input
├─ GUITAR - raw detection
│  └─ Guitar Frontend → 原有本地 Chord Lab；音频推子 −∞
│       └─ 共享轨 Note Receiver 的 Source FX：channel 2 → 15
│            └─ 共享 Chord Lab：只显示，不触发合成器
└─ 当前选中的 AG 音色轨 → Chorus / Delay / Hall → Ambient Guitar → Master → Spark GO
```

四条音色轨直接使用同一个硬件音频输入；不从已经静音的检测轨后级取声音。
DAW 内新增的效果器不会污染识别输入。这个“原始”只表示 **进入 DAW 后尚未加效果**，
不保证 Spark GO 的 USB 已绕过硬件内部音箱／效果；希望更干净时需在 Spark App 调整。

## 四个起点

| 音色轨 | 效果链 | 主要设定 |
|---|---|---|
| AG - 01 Glass Air | Dragonfly Hall Reverb | 清晰拨弦，22 ms predelay，3.8 s hall |
| AG - 02 Soft Prism | Surge XT Effects Chorus → Hall | 慢速轻 Chorus，5.6 s hall |
| AG - 03 Echo Bloom | Surge XT Effects Delay → Hall | 左 375 / 右 500 ms，4.4 s hall |
| AG - 04 Cloud Halo | Chorus → Delay → Hall | 左 600 / 右 800 ms，8.2 s 长尾 |

全部使用已安装的 CLAP 效果器；没有购买或新增下载插件，也没有使用 Bitwig 专属效果来制作这四条链。
Delay 是固定毫秒值，不是跟随工程 BPM 的同步模式。初始轨道推子 −12 dB，便于安全试听。
完整参数在 [`ambient_guitar.toml`](ambient_guitar.toml)；工程里的实际状态由 Bitwig 保存，
TOML 是可读配方，**不会在启动时自动覆盖你的手动调整**。
初始化用的八个效果器预设另存于 `~/storage/daw/Library/Presets/Ambient Guitar/`。

## 怎么玩

1. 打开 Spark GO、接吉他与 USB，展开 **Ambient Guitar**，点击任意一条 `AG - ...`。
2. Library controller 0.6 自动只启用当前音色轨、打开监听与录音准备，并显示共享 Chord Lab。
   原始检测轨始终保留。点回钢琴／合成器轨时，四条吉他效果轨停用，识别显示仍保留。
3. 点底部效果器：Hall 的 **Late Level** 调空间量，**Decay** 调尾长，**High Cut** 调明亮度；
   Surge 的 **Mix** 调 Chorus／Delay 干湿，Delay 的 **Feedback** 调回声次数。
   总音量调当前轨推子。先少量增加，尤其长尾不要同时把湿度、反馈和音量拉满。
4. 插件浮窗可手动打开，但 Surge XT Effects 通用界面很大；选吉他轨不会自动弹出它，
   默认用 Bitwig 原生底部参数面板。
5. 软件效果与 Spark 直通声音叠在一起时，降低 Spark GO 的 **Guitar Volume**；
   它控制直通监听，不是电脑 USB 回放音量。先保持较低监听音量试弹。
6. 满意后 `Ctrl+S` 保存工程。四轨用于互斥试听，切换会截断上一轨尾音，不是无缝演出切换器。
   需要多轨同时播放／正式编曲时，关闭 Controllers → UTRP Library → **Exclusive audition + editors**，
   再自行设置各轨的启用、监听和录音准备，避免多个实时输入叠加。

吉他显示不需要 Chord Lab 获得焦点；电脑和弦快捷键仍需要点击其窗口让 A 变绿。
选吉他音频轨时，电脑和弦不会凭空产生吉他声音；这些轨处理真实音频，不是 MIDI 吉他音源。

## 保存与验证说明

- 控制器：`lib/tools/bitwig_library/Library.control.js` / `Library.config.js`，
  部署目录 `~/Bitwig Studio/Controller Scripts/UTRP/`。
- 插件：`/usr/lib/clap/Surge XT Effects.clap`、`/usr/lib/clap/DragonflyHallReverb.clap`。
  REAPER 也可加载同一插件，但不会自动获得 Bitwig 工程中的轨道／参数链。
- 本轮证据与工程前后快照：`target/ambient-guitar/`，不进 Git。
- 配置时发现直接脚本调参的状态保存问题：轨道切换通过，但完整重开仍可能恢复初始值。
  最终改为先在独立 CLAP host 中完成参数设定与 DSP 初始化，保存完整预设，再由 Bitwig 加载预设建链；
  不依赖启动脚本每次重新灌入参数。验收包含实际关闭／重开，不把写入请求成功当作保存成功。
- 音频检查使用之前保留的 Spark GO 单音录音，不是新录制或保证无硬件效果的 DI；
  自动检查不能代替用户对四种最终听感、USB 延迟和硬件直通音量的实际试听。

官方硬件说明：[Spark GO USB Audio](https://help.positivegrid.com/hc/en-us/articles/13744445585933-USB-Audio-with-Spark-GO)。

## 本轮验收结果（2026-10-18）

- 14 项 Python／Node 包装测试通过；包含吉他与钢琴互斥切换、检测轨不被停用、FX 浮窗不自动弹出、四个配方名一致。
- 最终原生工程已关闭并重开；四轨八台效果器的数量、类型与全部设定参数通过严格核对，钢琴往返切换正常。
- 最终 DAWproject 导出的八个完整效果器状态，与初始化预设逐字节一致。正式保存以 `.bwproject` 为准。
- 之前保留的单音录音回放：同参数四链都有非零输出与混响尾音；测试时 Master 静音。
  这是最终预设导入前的链条音频检查，最终导入另外完成了状态与重开检查，不冒充真人试听。
- 临时控制脚本／TCP 19477 已移除，正式 controller 0.6 已部署；Master 已取消测试静音，
  工程停留在 Glass Air，共享 Chord Lab 已打开。Chord Lab 和 Guitar Frontend 二进制未修改。
- **收尾时 Spark GO 已离线**，四轨输入显示 `[missing]`，系统及 Bitwig 按原优先级回退到 Woo Audio。
  接回 Spark GO 后先确认输入恢复；若仍显示 `[missing]`，在轨道 Input 选择 Spark GO 的 mono 输入。
  这一步与实际听感／直通监听平衡仍待用户试弹，不能宣称硬件端到端已经最终验收。
- 最终证据：`acceptance.json`、`reopened-switch-parameters.json`、`export-exact-state-check.json`、
  `audio-check.json`、`Library-final.bwproject`、`ready-final.png`，均在 `target/ambient-guitar/`。
  较早的失败导出和配置日志仅是排错过程，不作为最终状态。


## 2026-10-18：恢复 Spark GO 实时输入

本节更新此前“输入 missing”的状态。根因是 Bitwig Audio 的 Selected Device(s) 选中了 GB203 HDMI，没有音频输入；输出策略另把 Bitwig 回放接到 Spark GO，因此“电脑有声音”并不代表吉他输入已接好。已将 Bitwig 音频设备改为 Spark GO USB，48 kHz、256 samples，恢复 `capture_MONO → Bitwig in1`；当前输出为 `out3/out4 → Spark GO playback_FL/FR`。256 samples 是单个处理块，不是已测量的端到端延迟。

- `GUITAR - raw detection`：输入恢复为 `Mono capture_MONO`，Guitar Frontend 显示 `On (mono)`，识别先于所有 Bitwig 吉他效果，原始轨音量保持 −∞，不另发一份干声。
- 共享 Chord Lab 的 Note Receiver 来源仍是 Guitar Frontend；保留既有 Source FX / channel 15 display-only 路由，不在每条效果轨重复识别。
- 当前恢复到 `AG - 01 Glass Air`：输入 `Mono capture_MONO`、监听及 Arm 打开、推子 −12 dB，输出至 Ambient Guitar group，再至 Master。其他三个配方及互斥选轨逻辑未修改；本次没有重新测完四条实际硬件链。
- 只听软件效果时，把 Spark GO 实体 **Guitar Volume** 降至零以关直通；电脑 USB 回放音量由 Bitwig／系统控制。不要把 Spark App 内的音源输出直接静音。USB 输入是否已含 Spark 内部音箱／效果处理须另核对；此处“原始”只保证没有经过 Bitwig 后置效果，不保证真正硬件 DI。
- Library 已保存到 `/home/shu/storage/daw/Library/Library.bwproject`。前后工程、prefs、PipeWire 连接和截图在 `target/guitar-routing-restore/`。插件二进制及控制器源码未因本次输入恢复而改动。
- 待用户确认：关掉硬件直通后，真实单音是否同时产生 Bitwig 混响回放与 Chord Lab 高亮；本次没有把界面配置成功等同于真人听感验收。


## 2026-10-18：降低监听 buffer 与小幅增益

- Library 保持互斥音色探索，不新增 arrangement。Bitwig Block size 从 Automatic（实际 256 samples）改为手动 128 samples，重启音频引擎后 `pw-top` 确认 128 / 48000。约 9 秒观察内错误累计值保持不变；不代表长期稳定或实测端到端延迟。Spark 硬件格式仍为 44100 Hz，未在本轮修改采样率。
- 当前 `AG - 01 Glass Air` 轨推子由初始 −12 dB 提高至 −9 dB；其他 AG 轨保持 −12 dB。Master −1.5 dB、效果器与识别路由不变。工程已于 15:53:50 保存。
- 128 / 48000 的 2.67 ms 仅为单块时长，不是监听往返总延迟。实际手感、最大力度下的削波及音箱失真仍需用户试弹；若持续爆音，回退 256 samples 并重启音频引擎。
- 手动音量优先用所选 AG 轨推子，少量递增并检查轨道、group、Master 峰值；不要提高 raw detection 推子或 Spark Guitar Volume 来放大软件效果。证据：`target/guitar-latency-check/`。


## 2026-10-21：改用 Bitwig 内设置

自定义音频服务已删除，不再使用 `Spark-GO-Guitar` 虚拟输入。请按[当前路由说明](../audio_routing/README.cn.md)在 Bitwig 内选择实体 Spark GO 输入与所需输出；四条 AG 和 raw detection 已映射到实体 Spark mono 输入并保存、重开验证；默认 Master 输出为 Spark，手动 Woo 切换只改 Master 输出。raw detection 保持 −∞，不改 Keystation、共享识别或两组独立试听。

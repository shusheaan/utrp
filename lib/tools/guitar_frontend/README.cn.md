# Guitar Frontend 0.2.1 — 仅单音

2026-10-18：用户真实试弹否决双音实验（含五度、八度问题）。正式插件移除 Mode 和第二音显示，双音运行时代码不再参与构建。离线研究与失败记录保留，不能据此声称双音验收通过。

- 使用原 0.1.2 单音检测器和 64 ms / 8 ms / 24 ms 参数，准确度优先，不采用存在八度误判或收益不足的提速方案。
- 当前 Bitwig 工程：`~/storage/daw/Library/Library.bwproject`。Detect 开关保留；识别 MIDI 只用于 Chord Lab 显示，不重复触发合成器。
- 可读取 v1 与实验版 v2 工程状态；v2 的 Mono / Dyad 均恢复为单音，其他参数保留。新状态保存为 v1。
- 检测器仍不是绝对准确的音高真值工具；不支持同时多音、重叠留弦或扫弦。

## 历史记录（以下版本／部署描述不代表当前状态）

# Guitar Frontend 0.2.0 — 单音 / 双音实验开关

当前新版说明：[Mode 开关与试用](MODE_SWITCH.cn.md)。Mono 原算法保留；Dyad 显式启用，尚非自动单双音融合。下文 0.1.2 部分是历史记录。

# Guitar Frontend 0.1.2 — 单音实验前级

## 双音实验（2026-10-18，不替换本版本）

最新进展：[双音提速与单音保护回归](DYAD_SPEED.cn.md)。DG 开发录音首次确认降到 56–90 ms；
仍是离线候选，未部署，日常单音版本不变。

新增 [保守双音离线实验](DYAD_STUDY.cn.md)：等强度、标准调弦 0–24 品矩阵，
独立泛音证据和因果起止音检查。正式 CLAP 仍为单音 0.1.2；双音尚未部署到 Bitwig，
不支持三音，也不能声称全指板或真人低延迟已经验收。

[English](README.md)

**2026-10-18 状态补充：** [Bitwig / UTRP 收尾](../bitwig_library/WRAPUP.cn.md)。
Bitwig 加载、合成单音与共享 MIDI 路由已验证，替代下文早期“尚未在 Bitwig 验收”的记录；
Spark GO 真实试弹仍未完成，单音实验边界不变。

独立 CLAP：干净吉他音频 → MIDI channel 2 → 现有 Chord Lab。**不修改 Chord Lab 引擎或键位，不依赖 REAPER/JSFX 执行识别。** 当前采用宿主通用参数界面，没有自绘 UI。

## 目前能做什么

- 单音旋律、音阶，以及先止音再弹下一音的不重叠分解和弦。
- 固定音高范围 MIDI 38–88（D2–E6），A4=440 Hz，四舍五入到半音。
- 同一精确 MIDI 音高在 Chord Lab 当前指板可见范围内的多个弦/品位置一起亮；不能知道实际弹的是哪根弦。
- 吉他输入不需要插件窗口焦点；电脑键盘演奏 Chord Lab 仍需要其窗口焦点。
- 原始 stereo audio 逐样本透传；只分析选中的一个声道。固定 MIDI velocity，尚无力度跟踪或 pitch bend/MPE。

**不支持**同时双音、三音、六弦扫弦、留弦叠音的分解和弦。此时可能误认根音、泛音或跳音，不能作为和弦检测器使用。重复拨同一音的能量触发也是启发式，不保证每次拨弦均正确分割。

## 本机试奏

工程：`/home/shu/storage/daw/Guitar Lab.rpp`（与 `synth.rpp` 分开）。

2026-10-17 已部署 0.1.2，保存并重启验证。应用菜单新增 **Guitar Lab**，通过现有 `/home/shu/.local/bin/reaper` 启动器打开这个工程并显式连接 Spark；原 REAPER 默认入口仍保留 `synth.rpp`，未改音色库。先接通 Spark 再打开 Guitar Lab。设备重连后可再次打开该入口刷新路由；没有 Spark 时启动器断开音频输入，不退回电脑麦克风。直接调用 REAPER 原始二进制会绕过路由修正，曾复现麦克风自动占 input 1。

**开关吉他转 MIDI：右侧 Guitar Frontend 第一项 `Detect (mono prototype)`，`On (mono)` 开启、`Off` 关闭。** 关闭会释放识别音，不静音 Spark 自身的吉他声音；已在正式宿主检查并恢复 On 保存。不要用 Chord Lab 的 Keyboard 按钮控制吉他输入，那是电脑键盘焦点状态。

**原始输入约束：** 当前识别轨无 Input FX、无接收、无媒体片段，Guitar Frontend 是唯一的普通 FX，直接收 hardware input 1。以后 REAPER 的 amp、失真、reverb、chorus 放在另一条读取相同硬件输入的声音处理轨，不要放在识别器前面。这样可隔离 REAPER 内效果；Spark 硬件端已进入 USB 信号的效果无法由本插件撤销，仍须在 Spark 端保持干净音色。

```
Spark GO capture_MONO → REAPER input 1
  Track 1: Guitar Frontend（普通 FX、音频输入、arm + monitor）
    └─ MIDI-only send → Track 2: Chord Lab（普通 FX、只显示、无合成器）
```

- 尽量在 Spark App bypass Amp 和所有 FX，避免失真、chorus、delay、reverb 干扰。
- Track 1 的 Master send 关闭，避免软件监听和 Spark 直接监听叠加。此工程不会用钢琴音色播放识别 MIDI；吉他声来自 Spark 直接监听。
- 不要取 Spark 的 `monitor_FL/FR` 回放端口当输入。确认 `pw-link -l` 中 **capture_MONO → REAPER:in1**；本机重启时曾自动接入电脑麦克风，已纠正。
- MIDI send 进入目标轨普通 FX，不经过目标轨 Input FX；不能照搬音色库共享 Input FX 的路由。
- 重新打开时仍应检查硬件连接；工程文件不能保证 PipeWire 每次选择同一设备。

### 参数怎么调

| 参数 | 默认 | 用法 |
|---|---:|---|
| Detect | On | 停止识别并释放已输出的音；不静音干声 |
| Gate | -48 dBFS | 安静也误触发时提高（如 -42）；轻弹丢音时降低（如 -54） |
| Confidence threshold | 0.88 | 提高更严格，可能漏音；降低更容易输出，也可能误判 |
| Stability | 24 ms | 提高减少短暂跳音，但响应更慢 |
| Release | 40 ms | 提高延长识别音的保持，不是 Sustain 踏板 |
| MIDI velocity | 90 | 固定输出力度，不改变吉他干声音量 |
| Analysis input | Left | 选择待分析声道；当前 mono input 1 用 Left |
| Detected MIDI note / Input level / Pitch confidence | 只读 | 音符、电平、周期性置信度；置信度不是“正确概率” |

Input level 是每个 audio block 的峰值 dBFS；Gate 使用滤波后分析帧 RMS，二者不是同一个电平量。没有输入时先查线和路由，不要靠无限降低 Gate 修复。

## 验收和边界

- DSP 合成测试：510 个音高/采样率/波形组合；覆盖 32/44.1/48/96/192 kHz。该测试最慢起音约 **80.25 ms**，释放约 **95.15 ms**，加上实际设备/宿主缓冲后会更慢。这不是实时真琴延迟保证；干声没有额外缓冲延迟。
- 独立 CLAP host：40 个采样率/块大小/float32/float64 组合；检查音频透传、MIDI、事件拒收重试、reset/disable、参数、部分流读写、状态校验、多实例隔离。
- 隔离 REAPER：14 个合成音高、28 个 MIDI on/off，在前级后与 Chord Lab 后逐事件一致，通过 MIDI-only send。
- 真琴：Spark 输入已观察到非静音电平及识别音符；**六根空弦正确率、重复拨弦、噪声条件仍须用户实弹对照，不等于验收通过。**
- Bitwig：使用标准 CLAP audio/note/params/state 接口，无 REAPER 运行依赖；**尚未在 Bitwig 加载/路由/录制验收**，不能保证直接照搬 REAPER 工程。需要验证 audio → MIDI 插件输出的设备链或跨轨 Note Receiver 路由。

识别算法为低通/降采样后的 YIN 类周期检测，固定容量缓冲；实时路径无动态分配、文件 I/O 或互斥锁。它不是多音转录模型，也没有训练数据。

## 0.1.1：修正虚假低音

Spark 录音复现了共同周期误判：E4/B3 留弦叠音可能被原单音检测器认成 E2/A2。新版本增加频谱检查：基音能量不足时检查有证据的高次谐波；不确定的分析帧不输出新音高，已输出音仍遵循 Release。这里依然只选择**一个主音**，不是多音转录。缺失基音或重效果音色仍可能被拒绝或误判。

特定录音 27.9–29.2 秒共有 162 个 `current` 输出状态：E2/A2 错误从 **105 帧降到 0 帧**；新版 E4 为 122 帧，不确定为 40 帧。这里不是原始 `observed`，后者仍有一帧 A2 被稳定逻辑挡住。这只是针对性录音回归，不代表普遍准确率保证。0.1.1 的原 510 组合、新增 45 组留弦干扰、40 组独立宿主、隔离 REAPER 的 14 音高链路均通过；当时相关 Python 回归 116 项通过。

普通 Confidence threshold 控制初始 YIN 候选；频谱补救另有编译配置门槛 `subharmonic_confidence = 0.60`，因此补救结果显示的 confidence 可以低于普通设置 0.88。它表示周期性证据，不是正确概率。`defaults.toml` 还提供 `fundamental_power_ratio`、`spectral_margin`。本次没有增加分析窗口或稳定等待，前述延迟限制依旧，不能当成超低延迟升级。

`replay_clip` 是离线诊断程序：stdin 接收 native float64、mono、48 kHz 原始样本，输出 CSV；不属于插件运行组件。详见 `acceptance.json`，旧验收保留在 `acceptance-0.1.0.json`。

## 构建与测试

### 0.1.2：邻近低频泄漏修正

D4 实录 17.712–17.736 秒出现 G2 误报：约 82 Hz 的真实弱低频，其窗口泄漏被当作约 98 Hz 候选的基音支持。新增局部频谱峰检查，保留高音端估计容差 `spectral_peak_cents=30`；不新增音频缓冲，也未缩短原有延迟。

- D4 13.9–45 秒：错误输出 3 → 0 hop，无音 219 → 219 hop。
- A3 0–38.2 秒：半音跳动输出 7 → 0 hop，无音 975 → 987 hop（增加 96 ms）。瞬态的实际音高变化不能全部视作算法误判。
- 历史留弦片段：输出保持 E4 122、无音 40，未退步。原始候选仍可能错误，不能承诺零误判。
- Release CTest 和 UBSan CTest 各 2/2 通过；包含原 510 音高组合、45 留弦组合、新增 160 邻近低频/相位/采样率组合、40 CLAP host 组合；Python 配置/研究测试 31 通过。
- 正式 REAPER 已加载新版，核对独立原始输入路由、Detect Off/On、保存状态；未把这次检查宣称为重新完成全部音高的 DAW 端到端验收。双音/三音、Bitwig 和 MIDI 键盘级延迟仍未通过验收。

本轮证据：`target/guitar-d4-validation/`，包括原始录音、路由、回放对比、CTest 日志与重启前备份。上一版验收保留为 `acceptance-0.1.1.json`，当前见 `acceptance.json`。

依赖：CMake ≥3.22、C++17、Python ≥3.11、已有固定版本 CLAP headers（来源见 `../chordlab_clap/dependencies.toml`）。运行时不需要 Python。

```sh
cmake -S lib/tools/guitar_frontend -B target/guitar-frontend-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCLAP_INCLUDE_DIR="$PWD/target/chordlab-clap-build/deps/clap-juce/clap-libs/clap/include"
cmake --build target/guitar-frontend-build -j2
ctest --test-dir target/guitar-frontend-build -V
python -m pytest -q lib/tools/guitar_frontend/test_configure.py
```

输出 `target/guitar-frontend-build/Guitar Frontend.clap`；Linux 安装到 `~/.clap/` 后重新扫描/重载。改 `defaults.toml` 需要重编译；已有工程保存的参数优先，不会自动被新默认值覆盖。配置生成器拒绝未知字段、NaN/Inf、非法范围和超容量窗口。

`stage_test.py`、`reaper_test.lua` 和两个测试 JSFX 仅用于隔离宿主验证，不要装入正式音色库。`live_setup.lua` 只接受名为 `Guitar Lab.rpp` 的空工程，不覆盖已有轨道。

额外检查：UBSan 两个 CTest 目标通过。ASan 因本机系统预加载 AppProtection 与运行时初始化冲突未能完成；不计为通过。完整范围见 `acceptance.json`。

## 后续单音优先实验

用户允许放弃不可靠的多音，先提高单音音高/八度正确性并降低延迟。六组离线配置中，加速候选在连续旋律或历史实录中出现回归，因此没有部署。完整数据见 [单音延迟研究](LATENCY_STUDY.cn.md)。

# 固定音频路由：输出优先级与吉他输入

固定策略：**Spark GO → Woo Audio（保留 EQ）→ 其他实体输出**。

这是系统路由工具，不是 Chord Lab/Guitar Frontend 的 DSP 功能。每 250 毫秒检查一次设备及连接，修正旧的默认输出与应用单独记忆的设备；设备发现本身可能另需时间。无需重启 Bitwig 或音频服务器。

## 文件与启动

- 源码：`lib/tools/audio_routing/policy.py`；设备名／检查间隔／JACK 主输出映射：`policy.toml`。
- 已安装服务：`~/.config/systemd/user/utrp-audio-output.service`，登录后自动启动。
- 服务直接运行当前 UTRP 仓库的源码；移动仓库后需更新 `ExecStart`。
- `systemctl --user status utrp-audio-output.service` 查看运行情况。
- `journalctl --user -u utrp-audio-output.service` 查看实际修正命令及异常；设备恰在操作中消失会明确报错，由 systemd 两秒后重启重试。
- `python lib/tools/audio_routing/policy.py --dry-run` 只显示当前待修正项；没有输出表示无需修正。
- 停用：`systemctl --user disable --now utrp-audio-output.service`，再按需要用桌面面板选择设备。

## 范围和保护

- 默认输出供新应用使用；现有普通 PulseAudio／原生 PipeWire 播放流也统一切换，包括原本单独指定 Woo 的流。
- Bitwig 和 REAPER 的 JACK `out1/out2` 主输出单独维护，左右声道一一对应。
- 仅维护专用虚拟吉他输入的后端连接；不接管其他录音输入、默认麦克风、MIDI、DAW 辅助输出或其他处理工具。不改音量、静音、音色或工程文件。
- `eq_woo_out` 和内部虚拟处理流不强制跟随默认输出，避免 EQ 反馈。Woo 实体输出不存在时，即使 `eq_woo_in` 仍在，也绝不选择这个无硬件的 EQ。
- 这是严格的自动设备优先级，会纠正手动切到较低优先级设备的操作。当前 Woo 分支固定使用现有 EQ（EQ 节点不存在才用原始 Woo）。需要临时手选其他设备或 Woo raw 时先停用服务。
- 直接独占 ALSA 硬件的软件绕过 PipeWire，不能受本服务控制；应改为系统音频／PipeWire。额外 JACK 软件需要在 TOML 中声明其立体声主输出端口。

实现采用 WirePlumber 支持的 [默认设备与流重定向机制](https://pipewire.pages.freedesktop.org/wireplumber/policies/linking.html)。单纯提高设备 priority 不足以覆盖已保存的默认选择，参见 [Node priorities](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/priorities.html)。

## 2026-10-18 验收

- `PYTHONPATH="$PWD" python -m pytest -q lib/tools/audio_routing`：20 项通过。
- 实机以静音 Pulse 播放流、原生 PipeWire 播放流及已打开的 Bitwig 同时验证六种场景：两设备在场、Spark 输出消失、两者输出均消失、Woo 先恢复、Spark 恢复抢占、手动默认被纠正。三者每次都只连接预期输出。
- 通过暂时切换设备 profile 模拟输出消失，不是物理 USB 拔插／真人听音测试；原 profile 与 Spark 原始输入 → Bitwig in1 已恢复。
- 服务启用且正在运行；最终系统默认及 Bitwig 主输出均为 Spark GO。
- 原状态、设备 profile、连接图、测试日志：`target/audio-routing/`（不提交运行证据）。

## 固定吉他输入（2026-10-19）

唯一正式方案是 **Bitwig 原生 PipeWire**，不是 JACK。Audio 选择 `System Out`，Block size 手动 **128 samples**。
Library 的四条 AG 音色轨与 `GUITAR - raw detection` 固定选择
`Applications → pw-loopback → Spark-GO-Guitar → capture_MONO`。

链路：`Spark GO capture_MONO → Spark-GO-Internal-Capture → Spark-GO-Guitar → Bitwig`。
`pw-loopback` 是 PipeWire 的音频转接程序；两个名称是同一个进程的输入端和输出端，不是两套重复方案。
使用时只选 `Spark-GO-Guitar`，不要选 `Internal-Capture` 的 monitor 端口。
实现采用官方 [Loopback module](https://docs.pipewire.org/page_module_loopback.html)。

为什么需要固定入口：已复现 Bitwig 启动时 Spark 不在场会选中 HDMI，之后 Spark 返回也没有输入端口。
固定虚拟入口始终存在，后端按设备名称重新接 Spark，不依赖每次变化的节点 ID。
Spark 缺席时保持静音，**不回退到系统麦克风**。默认语音输入 SF-558 不变。
设备发现完成后，策略每 250 毫秒检查；这不是零延迟热插拔保证。

### 安装与恢复

把本目录两个 `.service` 文件安装到 `~/.config/systemd/user/`，保留 `policy.py` 与 `policy.toml` 在仓库路径，然后：

```sh
systemctl --user daemon-reload
systemctl --user enable --now utrp-guitar-input.service utrp-audio-output.service
systemctl --user status utrp-guitar-input.service utrp-audio-output.service
python lib/tools/audio_routing/policy.py --dry-run
```

`utrp-guitar-input.service` 只创建一条 mono 通道；`utrp-audio-output.service` 同时维护已有输出优先级与这一条输入的后端。
首次部署／重新创建虚拟入口后完整重开 Bitwig，让 Applications 列表重新枚举。
不部署临时 null source、JACK 配置或测试路由。停用整套自动路由须停用这两个服务。

日常顺序：**Spark GO 与 Keystation 开机、USB 接好并被系统识别 → 启动 Bitwig → 打开 Library → 选轨弹奏**。
MIDI 仍经原来的 Keystation controller 与共享 Chord Lab；Library 互斥试听 controller 未修改，普通工程不套用该行为。
硬件未识别、断连、服务未启动或音量关闭不能由软件设置保证有声；正常使用无需反复选择 Input。
本次不调整音量、效果参数或 Spark 硬件直通。

### 验证

- 66 项音频路由、备份、Library controller 回归通过。完整退出、重建虚拟源并重开 Bitwig 后自动恢复输入，128 samples 保留。
- profile 模拟 Spark 消失／返回：固定源仍接 Bitwig，后端无麦克风回退，Spark 返回自动连接。不是物理 USB 拔插或整机重启测试。
- 系统 SF-558 麦克风、Keystation controller 与互斥试听保留。真人吉他／键盘听音待用户确认。
- 运行证据在 `target/input-autoconnect/`；恢复清单包含新增服务。

## Beat Lab 麦克风输入（2026-10-20）

`policy.toml` 的 `microphone_inputs` 将固定 SF-558 USB 麦克风的 `capture_MONO` 接入 Bitwig 命名总线 `beat lab mic` 的 L/R 端口。只管理这两个明确命名的端口，不改 `in3` 吉他输入或其他工程的 Arm/Monitor。缺失麦克风时不回退到吉他或其他麦克风；端口重建后按名称重连。Bitwig 的 Audio 设置保留 WooAudio 输出，录音轨输入选 `beat lab mic`，Arm + Auto Monitor 使信号进入 Beat Lab。需要其他设备时修改配置，不自动猜测。

验证：`python -m pytest lib/tools/audio_routing -q` 38 passed；实机断开右输入后自动恢复；插件输入电平非零。没有进行用户口技录音准确率测试。

## 2026-10-21 Spark GO 采集异响排查

- 现场发现 Spark capture 的 `pw-top ERR` 每秒增加约 187，ALSA `hw_ptr=0`、`avail` 异常大；Bitwig BUSY 约 0.1–0.3 ms / 256 samples，不能将此次异常归因于插件 CPU 过载。图中 SF-558 是 driver，Spark 是 follower；48 kHz graph 与 44.1 kHz Spark 硬件共存本身不等于故障。
- suspend/resume Spark source 以及 output-only → 原 duplex profile 重建 source 均未解决。随后短暂停止自动路由服务，仅断开 SF-558 → Bitwig `beat lab mic L/R` 两条连接，使 Spark 独立成为 driver；其采集指针恢复推进，错误停止增长。服务随后恢复，麦克风两条连接重新接回，SF-558 再次成为 driver，Spark 仍稳定。系统默认语音输入未改，也未采录音频。
- 最后约 20 秒、21 个有效观测：Spark capture ERR 固定 4610、输出 1、SF-558 7、Bitwig 2，全部增量为 0。两项路由服务 active，policy dry-run 无修正项，10 个 Storage 链接通过。证据：`target/guitar-noise-20261021/`。
- 这是一次采集运行状态恢复，支持“启动/时钟切换状态异常”的怀疑，但未证明具体驱动根因或重开后不复发。不能将短期计数稳定写成用户听感已确认。未加永久时钟优先级规则、未改 buffer、音色、音量、Library controller 或工程文件；真实异响是否消失等待用户试听。

机制参考：[WirePlumber ALSA 配置](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html)。不要仅看到两设备采样率不同就盲目统一采样率或更改全局 buffer。

## 2026-10-21：确认 Spark 优先、Woo 自动接替

- 当前 Woo 设备名为 `alsa_output.usb-XMOS_WooAudio-00.analog-stereo`。保留 Spark GO → Woo（存在时走 `eq_woo_in`）→ 其他实体输出顺序；Spark 回来后自动优先使用。
- `poll_seconds` 从 1.0 缩短至 0.25，减少设备枚举后策略的额外等待；正确路由仍为空操作，不反复重接。服务重启只重读策略，不重启音频服务器／DAW，不改音量、Arm 或输入。
- 250 毫秒是轮询间隔，不是物理热插拔到有声的保证；USB 枚举、驱动、时钟和 EQ 后端就绪另需时间。不能据此保证零断声或无爆音。

# 系统输出优先级

固定策略：**Spark GO → Woo Audio（保留 EQ）→ 其他实体输出**。

这是系统路由工具，不是 Chord Lab/Guitar Frontend 的 DSP 功能。每秒检查一次设备及连接，修正旧的默认输出与应用单独记忆的设备；设备发现本身可能另需时间。无需重启 Bitwig 或音频服务器。

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
- 不动吉他／麦克风输入、MIDI、录音流、DAW 辅助输出或输出到其他处理工具的连接。不改音量、静音、音色或工程文件。
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

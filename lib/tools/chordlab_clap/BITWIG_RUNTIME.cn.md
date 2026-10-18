# Bitwig 首次实机验证（2026-10-17）

[English](BITWIG_RUNTIME.md)

后续正式工程与扩大后的回归结果见 [Bitwig Library](BITWIG_LIBRARY.cn.md)。下文保留首次验证记录；
设备与工程的当前状态以 Library 文档为准。

## 环境与工程

- Bitwig Studio 6.1.4 Linux 原生版，Trial；REAPER 已关闭。
- 官方 `.deb` 解包到 `~/opt/bitwig-studio-6.1.4`，应用菜单指向原生程序。
- Flatpak 运行库 GLIBC 2.42 无法加载本机需要 GLIBC 2.43 的插件；未修改插件解决该问题。
- 工程：`~/Bitwig Studio/Projects/utrp-lab/utrp-lab.bwproject`，已保存。
- 工作区 2；插件独立进程；Surge 窗口缩放 125%。
- PipeWire / Spark GO USB / 48 kHz / 256 samples；Keystation 61 MK3 USB MIDI 控制器已配置。
- 窗口浮动规则本次通过 Sway IPC 设置，不表示已持久化到桌面配置。

## 两条独立链

1. `keys - chord - surge`：All ins → Chord Lab → Surge XT → Master → Spark GO。
   已武装，轨道音量 −10 dB。电脑键盘要求 Chord Lab 获得焦点且 Keyboard 为绿色。
   实体 MIDI 不需要插件窗口焦点。
2. `guitar - raw detection`：Spark GO mono input → Guitar Frontend → Chord Lab。
   Monitor On，输出 No output，避免与 Spark 直接监听叠加；此轨只用于音高识别与显示。
   检测位于 DAW 效果器之前，但不能消除 Spark 硬件已经加入的效果。

这不是 REAPER 的 95 音色库迁移，也不是共享一份 Chord Lab state 的总线结构。

## 已验证与未验证

- 原生宿主扫描、加载两个自制 CLAP 和 Surge 成功；两个 Chord Lab 实例可同时存在。
- Transport 停止时，聚焦插件并按 C，可见 C/E/G 持音，Surge 发声。
  定向录制 Bitwig out1：峰值 −16.630275 dB，RMS −32.716682 dB。
- 293.6647679 Hz 的已知 D4 测试信号经 Bitwig 输入 → Guitar Frontend → Chord Lab，
  出现灰色 D 音符。测试后已恢复 Spark GO 硬件输入连接。
- 实际 PipeWire 输入与立体声输出均连接到 Spark GO，不是默认电脑麦克风。
- **待用户实弹确认**：实体 MIDI 的声音/显示、真实吉他在此宿主内的识别。
- **尚未全量验收**：所有快捷键、混合输入所有权、持久化重开、长时间休眠唤醒、
  生成 MIDI 的录制、全部音色库。不能宣称 Bitwig 与 REAPER 已 100% 等价。
- 吉他仍为已接受的单音版本，不承诺双音、三音或零延迟。

本地证据：`target/bitwig-validation/` 中的 `chord-focused.wav`、
`chord-focused-held.png`、`d4-sine.wav`、`guitar-d4.png`、`ready.png`。
早先 `chord-audio.wav` 是焦点未激活时的静音排障样本，不是通过证据。

## 插件身份

- Chord Lab 0.1.6：`e4d87665e895c035ef726e2d816d0a5c208107d45cb7244e0252aa96a55c1b1b`
- Guitar Frontend 0.1.2：`4ecc3b85f4fc2428741196bfb647cacc5ac4f051e407b3cda5c051c31d902de6`

本轮没有重编译插件，也没有修改 REAPER 正式工程。

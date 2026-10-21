# Library 推子音量

[English](LEVELS.md)

## 2026-10-21 当前设置

- 所有可听音色（MIDI、AG 吉他、Pad、Beat Lab）推子统一 **−2 dB**。
- 文件夹总线、共享 MIDI 输入和 Master 推子 **0 dB**。
- `GUITAR - raw detection` 保持 **−∞**：仅用于音高检测，不叠加原始干声。
- 这是推子设置，不是感知响度匹配；没有改变插件内部音量、音频路由、Arm、Monitor、Active、Mute 或 Pan。高输出音色或钢琴与吉他叠加仍可能削波；硬件音量请从低处开始。

## 配方与范围

`levels.toml` 是当前配方；`levels.js` 是显式一次性维护工具，正常 `Library.control.js` 和 `Keystation.control.js` 均不加载它。不要把它加入启动项，避免覆盖用户之后的推子调整。`ambient_guitar.toml` 的初始吉他轨推子同步为 −2 dB；旧的迁移构建器仍负责保留源工程原始推子，不在普通工程上强制套用本配方。

维护调用为 `scheduleLibraryLevels(host, config, apply)`，必须在 Controller API 的 init 阶段创建代理；`config` 来自 TOML，`apply=false` 只读校验，`apply=true` 才写音量。它检查 Library 工程名、共享轨签名、录音未启用和 bank 容量；包括已折叠与停用轨道，保护 raw detection，不改其他轨道状态。宿主 ALL_CHANNELS 包含 Master 时不重复计数。

本机 Bitwig 6.1.4 的 raw volume 是线性振幅的立方根，`dB = 60 × log10(raw)`，不是直接线性振幅；以宿主 `displayedValue()` 再次验收，避免把 −2 dB 写成其他数值。

## 验证与恢复

- 宿主只读校验：**114 条（含 Master），保护 1 条，错误 0**。全部可听音色 −2 dB，总线/共享 MIDI/Master 0 dB，raw detection 保持 −∞。
- 406 项相关 pytest 通过；覆盖项目边界、录音保护、容量、已有 Master 去重、只读模式、原始检测轨与其他状态保护。
- 已保存 `~/storage/daw/Library/Library.bwproject`；本轮没有完整退出重开 Bitwig，也没有测量真实演奏峰值或感知响度。
- 部署前：`~/storage/daw/Backups/library-levels-20261021T201337Z/Library-live-before.bwproject` 是保存后的修改前工程；同目录 `Library.bwproject` 是更早的磁盘副本。
- 临时宿主脚本已移除，正式 Keystation 源码/部署一致。证据：`target/library-levels/`。源码未 commit/push；收尾执行 Storage 恢复快照。

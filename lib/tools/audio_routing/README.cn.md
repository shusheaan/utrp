# 音频路由：只使用 Bitwig 设置

[English](README.md)

## 当前状态（2026-10-21）

按用户要求停用并删除 `utrp-audio-output.service` 和 `utrp-guitar-input.service`，包括登录自启链接、仓库服务配方及策略程序。不存在自定义输出优先级或固定虚拟吉他输入，不新增替代服务。

系统 PipeWire / WirePlumber、现有 Woo EQ 和插件窗口服务不变。恢复旧快照时不要重新安装这两个音频服务。旧实现与诊断见 [历史记录](HISTORY.cn.md)，不是当前安装指南。

## Bitwig 内设置（2026-10-21 已部署并重开验证）

- Settings → Audio：原生 `PipeWire`，Bitwig 自带的 Combined Device `Spark GO USB + WooAudio`，只勾选这两个设备；Spark GO 为 clock master。手动 128 samples，Sample rate 保持 Automatic。这不是系统服务或新的虚拟输入程序。
- 四条 AG 轨及 `GUITAR - raw detection`：输入为 `Spark GO USB → Mono capture_MONO`，不再引用旧的 `Spark-GO-Gtrcapture` / `Spark-GO-Guitar`；raw detection 推子保持 −∞。
- 默认 Master 输出：`Spark GO USB → Stereo → Analog Stereo playback_F L/R`。
- 手动换 Woo：选中 **Master**，在左侧 Inspector 的 **输出下拉框**选择 `WooAudio → Stereo → Analog Stereo playback_F L/R`。不要把 Settings → Audio 的整个设备组替换成 WooAudio 单设备，否则 Spark 输入不再可用。Woo 路径是实体设备输出，不经过现有系统 Woo EQ。
- 切回 Spark：在同一个 Master 输出菜单选 Spark GO 的立体声端口。输入无需修改；两组试听和 MIDI 路由不变，不开启自动 Arm。
- `beat lab mic` 命名总线保留但不在本轮重新映射或开启录音；SF-558 不加入这套吉他设备组。
- 保存 Library 后，重开已验证 Spark 输入、Spark Master 输出及 128 samples 保留。以后手动换成 Woo 并保存时会保留该选择，不存在每次启动强制 Spark 的策略。未做缺设备启动或物理热插拔验收，不保证自动回退。

## 本轮验证与备份

四条 AG 输入逐轨检查，raw detection 输入已复验；Woo 输出切换期间 Spark → Bitwig in1 保持，随后恢复 Spark。正常保存、退出并重开，Master / 输入 / 设备组 / buffer 持久化通过。Instrument / Audio Auto-arm 均关闭，Beat Lab 未 Arm，未触发录音。真人听感仍由用户确认。

证据：`target/bitwig-direct-spark/`；修改前工程/偏好备份：`~/storage/daw/Backups/bitwig-direct-spark-20261021T192545Z/`。没有修改 controller 或插件源码。官方机制：[Combined Audio Devices](https://www.bitwig.com/userguide/latest/the_dashboard/)。

## 删除验收

两个 unit 均为 `LoadState=not-found`、`ActiveState=inactive`；系统三个音频服务仍 active，Woo EQ 与当前播放连接不变。删除前备份：`~/storage/daw/Backups/retire-audio-services-20261021T191202Z/`。

# 音频路由：只使用 Bitwig 设置

[English](README.md)

## 当前状态（2026-10-21）

按用户要求停用并删除 `utrp-audio-output.service` 和 `utrp-guitar-input.service`，包括登录自启链接、仓库服务配方及策略程序。不存在自定义输出优先级或固定虚拟吉他输入，不新增替代服务。

系统 PipeWire / WirePlumber、现有 Woo EQ 和插件窗口服务不变。恢复旧快照时不要重新安装这两个音频服务。旧实现与诊断见 [历史记录](HISTORY.cn.md)，不是当前安装指南。

## Bitwig 内设置（待现场完成）

- 先接好 Spark GO 与 Woo Audio，再打开 Bitwig；在 Settings → Audio 中使用原生 PipeWire，选择需要的实体设备。
- 输出选择 Woo Audio；吉他输入选择 Spark GO USB 的 mono capture，而不是已经删除的 `Applications → pw-loopback → Spark-GO-Guitar`。四条 AG 轨和 `GUITAR - raw detection` 都需要重新指定输入，raw detection 推子保持 −∞。
- 如需 Beat Lab 麦克风，在 Bitwig 中将其输入总线明确映射到 SF-558；不再由后台程序维护连接，不开启录音或自动 Arm。
- 输入、输出独立选择；不再强制抢回 Spark，不承诺自动回退或无缝热插拔。设备断开后在 Bitwig 内检查并重新选择。

删除服务时 Bitwig 未运行、Spark GO 不在设备图中，未修改工程或偏好，尚未完成上述实体输入映射及真人听音验证。原工程可能仍引用已删除的虚拟输入，不能将服务删除视为吉他已经恢复有声。

## 删除验收

两个 unit 均为 `LoadState=not-found`、`ActiveState=inactive`；系统三个音频服务仍 active，Woo EQ 与当前播放连接不变。删除前备份：`~/storage/daw/Backups/retire-audio-services-20261021T191202Z/`。

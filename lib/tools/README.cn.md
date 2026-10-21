# UTRP 音乐工具目录

[English](README.md) · 2026-10-20 收尾索引

目录按职责平铺，不代表每个文件夹都是独立插件。本轮只更新地图与过期说明，不移动仍被构建脚本、controller 或 systemd 引用的路径。

## 当前插件

| 目录 | 职责 |
|---|---|
| [chordlab/](chordlab/README.cn.md) | Chord Lab 当前内嵌和声/绘图引擎与资源，仍为 CLAP 所依赖；不是第二套旧产品 |
| [chordlab_clap/](chordlab_clap/README.cn.md) | 同一个 Chord Lab 产品的 CLAP 外壳、宿主集成和键盘处理 |
| [beatlab/](beatlab/README.cn.md) | 独立 Beat Lab 项目；Rust `engine/`、JUCE `plugin/`、集成 `tests/`，不依赖 Chord Lab 运行时 |
| [guitar_frontend/](guitar_frontend/README.cn.md) | 吉他单音识别前级，独立 CLAP；不是 Beat Lab 的一部分 |

Beat Lab 0.3.1 已部署，当前录音/分析/文件导出原型可试用。真实识别仍需人工核对；直接 MIDI drag-out、宿主 Clip 自动写入、独立跨录音 Sound Set 模板尚未完成。不要把“结构收尾”写成“所有产品需求完成”。

## 宿主与基础设施

- [bitwig_library/](bitwig_library/README.cn.md)：Library controller 与宿主集成；互斥试听仅对 Library 有效。
- [audio_routing/](audio_routing/README.cn.md)：已移除的自定义路由；当前 Bitwig 内设置与历史诊断。
- [plugin_windows/](plugin_windows/README.cn.md)：插件浮动窗口布局。
- [daw_backup/](daw_backup/README.cn.md)：实时 Storage 目录链接、恢复清单、私有快照。
- [library/](library/README.md)、`reaper/`：原音色库与 REAPER 配套脚本；本轮不删除历史兼容用途。

## 其他研究与工具

- `pipeline/`、`repatch/`：音色/鼓转写、逆向与批量处理。
- `harmony/`、`simulate/`：和声探索及共享 Rust library 的模拟适配器。
- `endless/`、`magdalene/`、`sega-universe/`、`tev-woods/`：各自的音色研究/重建配方。
- [guitar_poly/](guitar_poly/README.cn.md)：未验收的历史双/三音研究；不属于正式单音运行链。

## 实体存储与 Git 边界

| 内容 | 位置 |
|---|---|
| 插件源码、配置配方、测试、文档 | 本仓库 `lib/tools/` |
| Surge 文本音色 | `lib/surge/` |
| 当前 Bitwig 工程及音频物料 | `~/storage/daw/Library/Library.bwproject` 及 Storage 下对应目录 |
| 用户 CLAP 二进制 | `~/storage/daw/UserData/.clap/`；`~/.clap` 是目录链接 |
| 音乐偏好与资源实体 | `~/storage/daw/UserData/`；具体入口见 `daw_backup/live.toml` |
| Beat Lab Standalone | `~/storage/daw/Tools/BeatLab/Beat Lab` |
| 源码/配置恢复快照 | `~/storage/daw/Recovery/` |
| Bitwig 安装 | `~/opt/bitwig-studio-6.1.4/`，不是 UTRP 插件源码 |
| shell 启动命令 | GRAL `arch/zshrc`；`~/.zshrc` 指向该文件 |

`beatlab/build/`、`beatlab/target/`、`simulate/target/` 和仓库根 `target/` 是被 Git 忽略的本地构建/测试缓存；体积不等于源码体积。根 `target/` 仍有历史测试证据与构建目录，本轮没有删除。清理这些需要单独确认可再生依赖和历史证据，不影响本轮收尾。

源码在磁盘、Storage 快照中，不代表已经 commit/push；当前 Beat Lab 仍有未提交源码。实时偏好目录链接不是快照，二者用途不同。

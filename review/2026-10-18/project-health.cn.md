# UTRP 最终收尾 — 2026-10-18

[English](project-health.en.md) · [验证索引](README.md)

## 1. 执行摘要
软件自动回归通过，偏好已落实为 Storage 实体＋home 目录链接。总体 **Yellow**：软件通过，当前 Spark GO 不在线，未做新一轮吉他/踏板实弹及空白系统恢复。不承诺“所有硬件场景 100%”。没有新建 Git 提交或推送。

## 2. 工程结构与体量
`src/` 与 Rust tests 为终端和声训练/生成；`study/` 为图谱工具；`covers/` 为练习材料；`lib/surge/` 为 88 个 FXP；`lib/tools/` 为 CLAP、宿主控制器、渲染研究和部署工具。按当前工作树去重统计（排除 target/review）：80 Python、38 Rust、19 C++、218 Markdown；详细见 file-volume.json。

## 3. 架构分布与正交性
Chord Lab 的 JSFX 源码是 CLAP 内嵌引擎，不再作为独立旧产品部署。Guitar Frontend 独立单音检测，吉他音频效果与仅显示 MIDI 支路分离。Library controller 负责宿主选轨与互斥；Sway/PipeWire 服务负责窗口与输出，均不属于 CLAP DSP。不同宿主仍有不同路由配置，不等于项目文件通用。

## 4. 稳健性、质量与健康性
真实安装二进制与当前构建 SHA-256 一致。CLAP probe 覆盖混合输入同音重触发、14 通道踏板、display-only 隔离、持键 H/L、状态/生命周期和 12 种 rate/block 组合。吉他 Release 与 UBSan 均通过，但仅支持单音，不能推导零误判或 MIDI 键盘级延迟。

## 5. 工作流交叉与耦合
修复旧 tests/README 的 `scripts/` 引用，统一到真实 `study/`，同步图谱输出默认目录与 cover 索引。CLAP 构建说明改为构建全部目标，避免新 build 缺少六组 CTest executable。上级 lib/README 与 Bitwig WRAPUP 增加当前权威入口，旧阶段记录保留。备份成功后自动原子更新 LATEST；含资源才更新 LATEST_FULL，不再依靠手动改时间戳。

## 6. 测试与仿真覆盖
最终 Python 全量 1605 passed（系统 Python 3.14＋已安装 Surge 渲染环境的 site-packages）。Rust 119 passed、3 个原有长时间 exhaustive coverage 测试 ignored；strict Clippy 通过。Chord Lab CTest 9/9；Guitar Release 2/2、UBSan 2/2；已安装 CLAP probe 通过。24 个 seed=42 音乐事件二次运行完全一致，音高范围通过。测试不等于真人演奏验收；未测覆盖率百分比。不适用金融 backtest/RAS/R/单期 golden；音乐像素/voicing 回归已在 CTest 中执行。

## 7. 数据存储完整度
10 个 live 目录链接全部有效，实体在 `~/storage/daw/UserData/`；工程为 `~/storage/daw/Library/Library.bwproject`。账户激活和临时缓存留 home；旧 Surge standalone host 单文件设置只有快照，DAW 内 Surge 实际偏好已迁移。Recovery 用于回退，不是主数据。Storage 与 home 同盘，必须独立磁盘备份才能防整盘丢失。恢复入口为 `lib/tools/daw_backup/README.cn.md`。

## 8. 文档同步
修复当前入口、图谱路径、CLAP build 命令与 Recovery 指针；中英文 CLAP/存储/收尾说明同步。历史材料保留，不宣称全仓 Markdown 已逐页重译。主入口链接检查见 docs-check.log；未自动删除退役研究或用户资料。

## 9. 已确认风险
- 当前硬件验收缺口：Spark GO 不在线；Keystation MIDI/Transport 在线。输出服务 active/enabled，默认 Woo EQ，符合 Spark 缺席时的策略；未模拟设备拔插或测试新实弹。
- 重装容灾：同盘 Storage 不防硬盘故障；恢复流程未在空白系统演练；Python 完整测试依赖本机 Surge 渲染环境，需按 pipeline README 重建。
- 未提交工作树：本轮改动已文件保存并进入 Storage 源码快照，但不是 Git commit/remote。没有自动提交。

## 10. 错报与待确认
plugin-states 会被宿主启动清空，是运行时数据，排除实时迁移并非偏好漏搬。两位只读 reviewer 的缺路径/漏 build target/旧导航问题均已确认并修正。未发现当前 live 偏好回落 home 或已安装插件与构建不一致。

## 11. 后续
本轮停止扩展。下次 Spark GO 接通后可做短实弹：单音仅显示、吉他 FX 发声、键盘同音重触发、踏板按住/松开；不需要重做本轮迁移。重装前先退出 DAW 并备份独立磁盘。用户决定何时提交 Git。

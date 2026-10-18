# CLAP 0.1.3 全面回归：2026-10-17

[English](FULL_TEST.md)

## 范围与结论

Linux x86_64、REAPER 7.78、Sway/X11。测试实际安装的 `Chord Lab.clap`，
SHA-256：`a17a614adaebb33fb31b346d51afca49610e75203a23d27151be448acec41c44`。
本轮覆盖的回归通过；不是所有宿主、平台或真实硬件使用的百分之百认证。
旧 JSFX 只作为隔离测试中的历史基准，不恢复双产品维护。

| 检查 | 结果 |
|---|---|
| Python / C++ | 113 / 2 项通过 |
| Library 生命周期与启动 | 36 个生命周期断言；默认钢琴、幂等、超时检查通过 |
| MIDI A/B | 2,379/2,379，逐条 MIDI 字节及块内 sample offset 相同 |
| 保存重开 / 宿主参数 | 7/7、22/22 |
| Track FX / Input FX 混合输入 | 各 42/42；对照独立预期事件，不只互相比对 |
| Input FX 实际录制 | 两侧各 6 音，音高/channel/velocity 精确一致，长度为正 |
| 正式音色库 | 95/95 和弦及普通 MIDI 均产生电平；仅一个在线音源、Solo、armed 输入、音源浮窗 |
| ABI / 生命周期 | 18 参数、MIDI ports、GUI 创建/resize/重建、独立实例、state、12 种采样率/块大小组合通过 |
| GUI | 长按不重复、转位、分号恢复、Tab、Enter/鼠标 Sustain、Keyboard 开关、失焦释放/恢复、Space 不启动宿主播放 |
| 真实 REAPER 重启 | 默认 Acoustic Piano、唯一公共 CLAP Input FX、无旧 VKB、电脑按键发声通过 |

重启后识别到 `Keystation 61 MK3`，输入 armed + monitoring 开启。
电脑按键实际钢琴 peak 为 `0.42076608538628`。
102 轨身份与顺序、93 个 Surge 引擎/波表、2 个 sfizz 状态、基础音色组效果器、
所有轨与 Master gain 保持不变；测试前后 CLAP state 精确恢复。
测试夹具已移除，隔离实例已结束，正式 `synth.rpp` 保存并保持打开。

## 测试工具问题与重测

- 初版审计把 Master meter 为零当作静音条件；meter 可能位于 pre-fader。
  改为同时设置并检查 `D_VOL=0`、`B_MUTE=1`，结束恢复两者；全库重测通过。
- 并行隔离实例弹出 GUI，干扰了首次状态测试的焦点。重新加载已保存基准，
  顺序运行状态与参数测试后通过。首次失败证据保留，不计为通过。
- 正式 GUI 测试过早运行，碰到临时 Input FX 数量保护；清理完成后重测。
  排查期间 Keyboard 关闭，确认不发音；重新开启后 GUI 和重启发声均通过。
- `mixed_record.lua` 的 scratch 路径保护允许带版本号的 `*-input` 目录，仍拒绝正式工程。

本轮未改音乐核心或发布插件二进制，只改测试工具及记录。

## 明确未认证

实体手指/踏板与 USB 重连、混合实体输入灰点的像素级视觉检查、Bitwig、
macOS/Windows、长期压力、多显示器/强制平铺缩放、音色主观听感。
当前 Spark GO 未连接，实际输出为 `eq_woo_in → WooAudio`，不代表 Spark 路由测试通过。
REAPER 自带的 `No preset / Param / MIDI / UI` 顶栏本轮未修改。

## 证据与复测

机器记录：`target/chordlab-full-0.1.3/acceptance.json`；完整 TSV、结果、脚本和状态证据
在同目录 `evidence/`，单元测试与 ABI 输出在该目录顶层。

隔离 profile 使用 `stage_port.py` 创建，依次执行 `ab_test.lua`、`state_ab.lua`、
`parameter_ab.lua`；混合测试另用独立 profile 执行 `mixed_ab.lua` / `mixed_record.lua`。
GUI 注入测试不要与会弹窗的其他测试同时执行。
全库审计参见 [迁移说明](../library/CLAP_MIGRATION.cn.md)，运行中不要弹奏、切工程或保存。

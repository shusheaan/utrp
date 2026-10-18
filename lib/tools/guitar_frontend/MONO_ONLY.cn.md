# 单音收尾 — 2026-10-18

[English](MONO_ONLY.md)

## 决策与改动

用户真实试弹否决双音识别。Guitar Frontend 0.2.1 删除 Mode、第二音 meter 和双音运行时构建；仅保留原单音 Detector。旧双音运行时代码与部署备份归档在 `target/mono-pill-wrapup/retired-dyad-runtime/`，不随插件分发；离线实验保留为失败研究记录，不再作为正式功能。

保留 Detect 开关、稳定 CLAP ID、MIDI channel 2 与干声逐样本透传。v1 单音和 v2 双音实验状态都能导入，旧 Mode 无论取 0 或 1 均回到单音；其他参数保留。非法／截断状态事务式拒绝。新工程状态写 v1，兼容旧单音版本。

准确度优先：不修改 `engine.cpp`、`engine.h`、`defaults.toml`；保持 frame/hop/stability = 64/8/24 ms。已有提速研究表明短窗会引入错误八度；较保守的提速收益有限，不能证明真实吉他整体更好，因此未采用。不能承诺 100% 识别，也不能把测试起音延迟当作硬件端到端延迟。

## 验证

- Release 与 UBSan 各 2 项 CTest 通过；覆盖 510 个单音音高／波形／采样率组合、45 个低音误报定向用例、噪声、起止音、连续旋律、40 组 CLAP rate/block/precision、背压、禁用、生命周期及状态兼容。
- 单音、Chord Lab 与包装器共 631 项 pytest 通过；Chord Lab 6 项 CTest 与真实 GUI CLAP probe 通过。
- 三段既有录音共 20,604 个输出帧，与原稳定单音回放逐字节一致。这证明未回归，不等于每个音都是真值正确。
- Bitwig 6.1.4 Library 保存、退出、加载新插件；Mode 不再暴露，Detect On 保留。合成 E4 输入能在共享 Chord Lab 显示，结束后释放。电脑键盘仍能发声和释放。
- 首次输出检查受到前一轮和弦试音的衰减混响尾音污染，保留原始证据并待尾音消退后复测，6 秒 stereo 输出采样峰值为 0；真人吉他听感未重新录制验收。

## 存储与恢复

- 项目：`~/storage/daw/Library/Library.bwproject`，不进入 Git。
- 安装：`~/.clap/Guitar Frontend.clap` 与 `~/.clap/Chord Lab.clap`。两宿主共享文件；已经运行的宿主需要重新加载才能更新。
- 源码：`lib/tools/guitar_frontend/`；胶囊 UI 位于 `lib/tools/chordlab/ui.jsfx-inc`、`theme.toml`、`generate_theme.py`、`chordlab.jsfx` 及 `lib/tools/chordlab_clap/state_button.h`。
- 本轮备份、构建、哈希、录音回归、截图：`target/mono-pill-wrapup/`。旧实验工程／二进制备份只用于回退，不是并行产品。
- 输入恢复为 Spark GO capture_MONO → Bitwig in1；Guitar Frontend 位于效果器之前。既有 2→15 映射让吉他仅显示，不触发键盘音源。Spark 内部效果仍需硬件侧保持干净，插件不能撤销它们。

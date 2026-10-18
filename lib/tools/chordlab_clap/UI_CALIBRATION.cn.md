# 0.1.1 界面校准与 Core 试奏工程

[English](UI_CALIBRATION.md)

## 修复

旧 ysfx 所带的 Linux SWELL 把正字体高度当作 em 高度，导致同一 JSFX 在
CLAP 中的文字比当前 REAPER 原生 JSFX 大。封装层 `font_source()` 回移植
[当前 SWELL 的字体 line-metrics 换算](https://github.com/justinfrankel/WDL/blob/main/WDL/swell/swell-gdi-lice.cpp)。
不修改 JSFX 音乐逻辑、字号配置、调色板或谱号图片。顶部 40 px 键盘控制条是
CLAP 新增功能，原 JSFX 没有；不能把整窗截图当作应完全相同的图片。

真实桌面按相同 gfx 尺寸并排检查顶部调名、和弦按钮、琴键/指板标记；字体大小
现在对齐，原配色保持。Surge Royal 保持 125%，不通过非整数窗口拉伸改缩放。

## 本机试奏工程

`/home/shu/storage/daw/Core.RPP`：仅一条轨道，
`Keystation USB MIDI → Input FX: Chord Lab CLAP → FX: Surge XT instrument → Master`。
没有 Shared MIDI input、旧 JSFX 或旧 Lua/VKB。旧 `synth.rpp` 未改。
录音准备和监听开启，轨道 -6 dB 留余量。当前输出经现有 EQ 到 WooAudio，
不是未连接的 Spark GO。电脑键盘需要点击 CLAP 内容使其显示 Keyboard ACTIVE；
实体 MIDI 不依赖编辑器焦点。电脑键盘按 D 的停止状态发声测试轨道峰值约 0.122。
真实琴键的手动验收仍待用户；连接成功不等于已经验证物理按键。

## 回归证据

`ui_acceptance.json` 对应新版 binary，详细本机证据在
`target/chordlab-clap-0.1.1/evidence/`：82 pytest、2 CTest、CLAP ABI probe、
2379 MIDI A/B、7 保存重开、22 参数对照通过。
旧 `acceptance.json` / `mixed_acceptance.json` 保留为 0.1.0 证据，
不能将旧版全部 GUI/混合输入结果称为新版重测结果。Bitwig 尚未实机验收。

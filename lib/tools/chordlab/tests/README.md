# Chord Lab 验证

## 普通测试

```sh
python -m pytest lib/tools/chordlab/tests -q
```

检查配置保留、VKB 映射、主题一致性、安装/卸载、运行时文件隔离和拒绝覆盖用户改动。

## REAPER 宿主测试

只在命名为 `/tmp/chordlab-*.rpp` 的临时工程运行，不能对创作工程运行这些脚本。

轨道 1：Input FX = Chord Lab；normal FX 0 = `midi_probe.jsfx`；normal FX 1 = synth。开启 All MIDI input、arm、monitor；先退出 Chord Lab Lua 模式。测试期间不要按琴键、改变轨道或拖动 FX。

- `host_acceptance.lua`：12 调 × 7 级 × 4 转位，核对实际输出 MIDI，而非仅核对 UI 参数；另测调性锁、停音、双来源同音持有、velocity-zero Note Off、pedal、关闭电脑输入。输出 `/tmp/chordlab-acceptance.txt`。
- `mode_acceptance.lua`：会话启动/关闭、重复运行 Open、输入/arm/monitor/VKB 恢复、模式关闭后的硬件 MIDI 透传、JSFX 单独旁路。输出 `/tmp/chordlab-mode.txt`。
- `record_acceptance.lua`：空轨录入两组四音和弦，核对 8 个 channel 1 正时长 MIDI 音符。录音后若宿主提示，选 Save All；输出 `/tmp/chordlab-recording.txt`。运行前轨道必须没有 item。

宿主音频线程与 Lua defer 异步，和弦检查等待 150 ms。最初 45 ms 等待在 GUI 更新期间出现一次输出 mask 不匹配，怀疑与异步音频处理时序有关；增加等待后完整复测通过，不自动忽略失败。

GUI 待验收：Surge 浮窗有焦点时按 D/K/L/;/Enter（当前仍有限制）；Tab 全局 action 绑定；调性锁；检查浓色大圆点与 MIDI 音高一致；检查吉他同音重复位置、品号与下方品记；确认鼠标拖动参数时的已知键盘限制。

真实外接 MIDI 键盘未连接时只能模拟独立 MIDI Note/CC，不能把模拟通过称作实体设备验收。输入探针和临时自动化 runner 不安装到用户 profile。

## 本机验证记录（2026-10-15）

REAPER 7.78 / Surge XT CLAP / Arch Linux。安装器 pytest **10 passed**；最终宿主 MIDI 检查 **370/370**；模式生命周期 **24 passed**；录音 **8 notes**（`60,64,67,71,64,67,71,72`）。原生 Enter 返回原位通过；Escape 被 FX 窗口截获关闭窗口，因此不绑定为停音。确认 synth 轨有非零音频电平且 REAPER 输出已连接到现有播放设备；不声称经过人耳音质评审。

此前 GUI 使用白底 D2–D6 键盘/17 品指板、浓色大圆点和浅色小圆点，没有光晕。实体 MIDI 设备验收仍待用户插入键盘后确认。


### 谱表与配色增量验证

- 安装器 pytest：**11 passed**。
- `staff_math_probe.jsfx` 在独立临时 REAPER 工程运行：**4781 checks / 0 failures**，覆盖 12 调 × 128 MIDI 音的拼写/音高回算、C2–C6 边界、秒度错位、12 调的调号与调内音匹配，以及高低谱号调号的字母位置。
- 实际 REAPER 浮窗截图检查：Eb 调在两个谱号后各显示三个降号；调内音旁无重复降号。两个五线谱保持长线，中央 C 与上下加线只在相应音符附近画短线。默认内容区 860 × 457。
- 钢琴／指板和弦外音共用 `external_color=#707070`，白色音名；谱表和弦外音也用灰色圆点，音高由谱位读取。此次未连接实体 MIDI 键盘验收。
- 本次未重新执行旧版 MIDI／录音验收脚本；以上为谱表增量测试，不代表 Surge 焦点和 Tab 限制已解决。

### 加线图层复查

- 实际截图发现：Eb 调 Fm7 的 Ab5 与 C6 共用上方加线，原先逐音绘制让后绘制的 C6 加线穿过已画好的 Ab5 圆点；下方共用加线同样存在风险。
- 改为两遍绘制：先绘制所有短加线，再绘制所有音符／临时记号。两个遍历采用相同的筛选与秒度错位规则。
- 保存并备份工程后在 REAPER 重载，实际截图确认 Ab5 圆点完整、没有横线穿过，中央 C 和外侧加线仍是短线；原键盘模式恢复。安装器测试再次 **11 passed**。未将此前 4781 项音高检查描述为本次重跑。

# Chord Lab 0.1.9：左手操作

[English](LEFT_HAND.md) · [使用说明](README.cn.md)

## 键位

| 键 | 操作 |
| --- | --- |
| Z / X | 6 / 7 级和弦 |
| C | 1 级和弦 |
| A / S | 2 / 3 级和弦 |
| D / F | 4 / 5 级和弦 |
| V / G | 向左下 / 右上移动转位；可以一直按住和弦键 |
| Space | 按下切换 Sustain；长按不重复，松开不再切换 |
| Tab | 三 / 七 / 九和弦，切换即记忆 |

第一行 12 调快捷键不变；鼠标 Sustain 按钮保留。旧 Esc/Ctrl/H/J/K/L/分号/Enter 功能取消。
这里整合的是和弦、移动和延音操作，不是把调性选择也改到左手。

**电脑键盘仅在 Keyboard 绿色、插件有焦点时控制插件。** Space 可在按住和弦时切换 Sustain。
Shift / Ctrl 不再有单键动作；Ctrl/Shift/Alt 等修饰组合不触发插件命令。
真正失焦或关闭 Keyboard 时，仍按安全规则释放生成持音。

Space 在插件里切换 Sustain，不是 REAPER 播放。系统或宿主 global 快捷键仍可能优先；
插件不是系统级键盘钩子。实体 MIDI 的通道、力度、处理链不变，不要求编辑器有焦点。

## 实现

- `keyboard-map.txt` 是 CLAP 自己的键位配置，构建时生成 `keyboard_map.h`。
  旧 JSFX/VKB 配置不参与当前产品的键位生成。
- Space 走普通有序按键流；已移除产品中的修饰键单独松开动作。
  Linux `PhysicalKeys` 只观察自己的 X11 editor peer；不安装全局快捷键。
- 普通按键释放每次核对实际 X11 键状态，避免 JUCE 漏掉 key-up 后卡住和弦。
  这也覆盖编辑器仍有焦点时的偶发缓存滞后。
- 和声算法、MIDI 语义、参数、稳定 CLAP ID、共享输入轨结构不变。
  旧 JSFX 只作为音乐核心 A/B 基线，不恢复双产品维护。

## 历史 0.1.5 验收范围

最终结果见 [本轮验收](left_hand_acceptance.json)，本机完整证据在
`target/chordlab-full-0.1.5/`。真实 GUI 测试使用独立 REAPER、headless Sway/XWayland
与 XTest 注入，`evidence/test_keys.py` 是本轮固定窗口坐标的复现脚本；窗口 ID 和路径
随测试实例改变，不能直接对正式工程盲跑。

自动化测试不是所有硬件/宿主的数学证明：实体手指弹奏、Bitwig、macOS/Windows、
原生 Wayland 插件界面、任意宿主全局快捷键设置不在本轮认证范围内。
左/右修饰键的 native 实现目前只针对 Linux X11/XWayland。

更新前保存工程并备份原插件；重启才加载新 binary。保存重开保留和弦记忆，
Sustain 按既有安全规则重置为 OFF。全库验收临时静音，结束后恢复音量和选择并移除测试 FX。

## 0.1.8：持键转位与点击焦点

按住 C（或 Z/X/A/S/D/F），点按 G 向右上移动，点按 V 向左下移动；
和弦保持发声，每次真实按下移动一步，长按的系统重复不会重复移动。
Esc 与 Ctrl 不再移动。Shift 仍须单独松开才切换 Sustain；Space 和 Tab 不变。

本机已按用户确认将 Sway 设置为 `focus_follows_mouse no`：鼠标经过其他窗口
不切换焦点，点击或焦点快捷键才切换。该设置作用于整个桌面，不是插件抢焦点。
真正失焦时 Keyboard 仍变红并安全释放电脑持音。
验收记录见 [G/V 与焦点验收](GV_FOCUS.cn.md)。

## 0.1.9：Space 切换 Sustain

Space 每次真实按下切换一次 Sustain，可与和弦键一起操作；长按和松开均不额外切换。
取消 Shift 单键动作，以及原 Space 恢复默认位置的快捷键。G/V、Tab、鼠标 Sustain、
点击切换焦点和实体 MIDI 路由不变。上方 0.1.8 及更早验收段落仅记载历史版本。

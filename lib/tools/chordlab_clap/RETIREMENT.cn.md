# 0.1.6：单一 CLAP 产品与全量复查

[English](RETIREMENT.md) · [使用说明](README.cn.md)

## 产品边界

只维护 `Chord Lab.clap`，稳定 ID 为 `org.utrp.chordlab`。旧 JSFX 安装器、Lua/VKB
操作入口、VKB 映射和旧 binary 已退役删除；正式 REAPER 的 Open Chord Lab action
只打开当前共享 CLAP，不会再创建旧 JSFX。

**内嵌 EEL/JSFX 引擎不是旧产品残留。** `../chordlab/` 的六个引擎文件、谱号图片与
许可证继续参与构建，八个资源与构建输入逐字节相同。它们是当前 CLAP 的实现源码，
不能删除。测试中的原生 JSFX 仅是输出回归参考，不是另一个维护/部署的产品。
用户工程备份与历史验收记录保留，旧工程不会因此自动转换。

## 本轮发现与修复

系统自动重复延迟为 200 ms。旧实现以物理键状态快照清除 held，再消费排队中的
重复事件，可能把一次长按误认成新按键，使 Tab/Esc 重复动作。仅跳过部分 JUCE
keydown 回调中的查询不能解决这个竞态。

0.1.6 使用单条有序 X11 按键/焦点事件流和 `XkbSetDetectableAutoRepeat`，真正的
KeyRelease 才结束持键；物理快照仅用于初始/未接管时同步。普通映射与左 Ctrl/Shift
共享该事件流；失焦释放电脑持音并取消待触发动作，重新聚焦不触发已经按住的键。
在其他窗口松开的键会清除失焦保护锁，不会吞掉回到插件后的首次新按键。
原生焦点短暂移出又移回也会释放，不依赖 20 ms timer 恰好观察到失焦。
JUCE 回调即时取事件，timer 仅作补充。X11 不支持所需能力时明确显示错误。

另一个焦点边界：宿主把 native 焦点移回外框后，JUCE 的组件焦点缓存仍可能认为
编辑器已获焦；旧时间戳的 native focus 请求也可能被 X11 忽略。现在点击内容区
在 mouseDown/mouseUp 显式用 `CurrentTime` 恢复可见 peer 的焦点，按钮状态以实际
native 焦点为准；不靠 timer 强行抢回其他窗口焦点。

和声算法、18 个参数、state 格式、实体 MIDI 力度和稳定 plugin ID 不变。

## 验证方法与证据

最终 binary SHA-256 与结果索引：[`retirement_acceptance.json`](retirement_acceptance.json)。
本机原始记录位于 `target/chordlab-retirement-0.1.6/`；失败尝试和 preliminary 结果
单独保留，不冒充最终 binary 的结果。

- 当前 CLAP/引擎/Library 范围 Python：96 项；C++：3 个 CTest，包括 188 键盘检查、924 个有序映射键对/释放序列、
  2040 个 Ctrl/Shift 组合序列及 11 个控制队列检查。
- 独立 REAPER 配置：2379 个 MIDI A/B 用例，逐条核对字节、顺序及 block 内 offset；
  7 项 state、22 项参数写入；Input FX / Track FX 混合输入各 42 项。
- 独立 CLAP host：生命周期、端口、18 参数、8 次待处理参数写入、GUI、跨实例 state、
  44.1/48/96 kHz × 32/64/256/1024 frames；Library 生命周期及启动等待测试。
- 正式桌面：83 项真实 XTest 事件检查，含七级和弦、十二调、旧键失效、左手控制、
  组合键取消、失焦释放/恢复、快速原生焦点切换及 190 ms～1.2 s 的 Tab 长按。
  另有 28 次窗口外松键再聚焦的压力检查，共 56 条断言通过。
  最终测试用无操作的 X11 空窗口承接失焦：早期测试把焦点切到 DAW，系统重复键
  会触发宿主快捷键并打开其他窗口，造成测试干扰。已恢复完整原始工程后重测。
- 正式音色库：95 音色逐个检查电脑和弦控制协议与普通 MIDI 发声、唯一在线音源、
  solo/arm/窗口路由、旧 VKB 关闭；测试期间 master 静音，退出恢复用户设置。
- 对照测试前工程：102 轨身份、93 个 Surge 引擎及 wavetable、2 个 sfizz 状态、
  folder FX、全部轨道和 master 音量保持；最后保存重启并重新检查可弹奏状态。

这是明确范围的回归，不是所有设备/宿主/时序的“100% 数学保证”。本轮未认证
实体 MIDI 键盘的人工手弹、Bitwig、macOS/Windows、native Wayland、所有宿主 global
快捷键设置。真实 MIDI 设备枚举/路由与注入 MIDI 发声通过，不等于替用户手弹硬件。

一次非标准宿主启动出现 stopped CLAP 不处理，播放一次可激活；正式 launcher
冷启动无需播放即通过。本轮不把尚未确定的更底层原因归因于音色或插件 DSP。

## 日常使用

打开 `synth.rpp`，选择音色：`实体 MIDI / 电脑键 → 共享 Chord Lab Input FX → 当前音源 → FX`。
只有共享输入轨 armed；不要再给每个音色额外串一个 Chord Lab。
电脑键需点击 Chord Lab 使 Keyboard 浅绿；实体 MIDI 不要求该窗口获得焦点。
Z/X=6/7，C=1，A/S=2/3，D/F=4/5；Esc 左移、左 Ctrl 单独松开右移、Space 默认位置、
左 Shift 单独松开 Sustain、Tab 三/七/九。Ctrl/Shift 与其他键重叠或失焦均取消单键动作。

## 仓库其它检查

`cargo test --offline` 与 `cargo clippy --offline --all-targets -- -D warnings` 通过。
另尝试仓库根目录不限定范围的 `pytest`，遇到 12 项收集错误：历史 `target/` 测试被
重复收集/要求 GUI、缺少 `soundfile`、旧测试导入不存在的 `scripts` 包。因此不声称
整个仓库的所有 Python 测试通过；本轮插件与音色库范围的 96 项独立通过。

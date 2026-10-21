# Keystation 61 MK3：Bitwig 控制

[English](KEYSTATION.md) · [Library](README.cn.md)

## 两个输入，职责分开

- 原 `Generic / Keystation 61 MK3(USB MIDI)` 保留：琴键、力度、踏板、轮子和滑杆。
- 新 `UTRP / Keystation Transport` 只连接 `Keystation 61 MK3(Transport)`，没有 Note Input，没有 MIDI 输出，也不向合成器重发控制按钮的音符。
- `UTRP / Library` 不变：互斥试听、开窗、调性同步。Transport 不复制这些逻辑。
- 不需要 Chord Lab 焦点即可操作实体控制键；电脑字母和弦仍需要插件焦点。

## 按钮

| 硬件 | 动作 |
| --- | --- |
| Play | 从宿主播放起点开始播放；已在播放时不重复启动 |
| Stop | 停止并关闭 Arranger 录音使能 |
| Record | 开始 Arranger 录音；再次按下取消录音、保留播放 |
| 上 / 下 | 前一条 / 后一条可见轨道；包含文件夹，跳过已收起的子轨 |
| 左 / 右 | 收起 / 展开当前文件夹；选中子轨时操作它的直接父文件夹，收起后选中父文件夹 |
| 中央圆点 | 切换当前乐器 / 音频轨的 Arm 红灯（录音准备），不启动录音；文件夹、Master 不操作 |

为避免中途换轨或取消 Arm 破坏录音，Arranger 录音使能时暂不响应方向和中央 Arm 键。再次按 Record 结束录音（播放继续），或按 Stop 同时停播放后恢复。
只按下触发一次，松开不再触发，按住不自动连发。左右和中央键不再移动播放位置；顶层非文件夹轨的左右键不操作项目根节点。

Record 不是删除上一 take 或自动重录按钮；计数预备拍、循环、Punch 和录入方式仍由 Bitwig 设置决定。
在 Library 先选音色、等加载完成，再按中央键手动 Arm，确认红灯后按 Record 录音。选轨不会自动 Arm；再次选同组音色会清除本组 Arm，另一组保留。无需为本次手动 Arm 关闭 Exclusive audition + editors。正式创作建议另存工程，避免把练习记录混入音色库。

## 滑杆与轮子

- 内置 Generic 的 `Cursor Track → Volume CC = 7`，全局 `Takeover mode = Catch`。目标是当前选中轨的 mixer 音量，不是系统或 Spark GO 硬件音量。
- 切轨后，滑杆先经过软件当前数值才接管，避免音量跳变；因此刚动一点可能暂时没反应。先不要弹琴，慢慢寻找接管点。选中总线或 Master 时控制的也会是那个选择，使用前检查轨名。
- Modulation wheel 保持标准 CC1；音源决定实际效果，可在 Surge 给 Modwheel 指派 vibrato、filter cutoff 等。没有 modulation routing 的音色（尤其采样钢琴）不一定有可听变化，不代表键盘坏了。
- Pitch wheel 保持完整 14-bit pitch bend；弯音范围由音源决定，松手回中。Chord Lab 显示 Note On 的音高，不会把弯音连续变成新的音符格。
- Octave +/- 仍是键盘本身的八度功能；Advanced 暂不改。S/踏板规则仍由 Chord Lab 0.2.11 处理。

## 安装与协议

源码：本目录 `Keystation.control.js`、`Keystation.config.js`；复制到 `~/Bitwig Studio/Controller Scripts/UTRP/`。
Bitwig `Settings → Controllers` 添加 `UTRP → Keystation Transport`，只选择 Transport 输入，无输出。
原 Generic 不应选择 Transport，避免按钮被当作乐器音符或重复绑定。

2026-10-18 实体捕获为 channel 1 Note On/Off：Play 94、Stop 93、Record 95、上 96、下 97、左 98、右 99、中央 100；这套键盘已在 Mackie Control 模式，无需改硬件。
如果以后误改到 HUI/MIDI，按照[官方手册](https://cdn.inmusicbrands.com/m-audio/maudio_documentation/Keystation%2061%20MKIII%20-%20User%20Guide%20-%20v1.6.pdf)选择 Mackie Control：Advanced → DAW，确认 +/- 指示为绿色，再 Enter；不要 Factory Reset。
踏板开机前松开，让键盘检测正确极性。

## 验证边界

Transport 已从真实硬件捕获全部八键；脚本安装后 Bitwig 报告 ready，无初始化错误。
最初 1.0 的 Node 模型覆盖八键、按下去重、两种释放、错误通道/消息、拍号/零边界、录音导航保护；当时 927 项相关 pytest 通过。当前 1.1 的验收见下方。
已安装 CLAP probe 验证 CC1/7/11 所有 128 个值与 14-bit bend 的代表值：演奏通道原样透传，显示/控制通道隔离；原踏板回归同时通过。
这些并不替代真实操作的宿主验收：当前已请求用户验证运输键、方向和滑杆；录音未在正式 Library 中制造测试 take。每个音色的 wheel 效果也不承诺一致。

证据及部署前配置/工程备份：`target/keystation-controls/`。本轮未重建或替换 Chord Lab 插件，仅扩充其 probe；没有改系统音量与 Spark GO 输出策略。


## 踏板反向的实测排查（2026-10-18）

本机曾实测踩下=0、松开=127。保持踏板插入且脚松开，仅重新开关键盘后，复测为踩下=127、松开=0。开机时踏板状态决定极性，参见上面的官方手册；不必修改 CC64 编号或改成锁存模式。识别极性应结合用户实际踩放动作，不能只看一串 0/127 就猜。采集时临时停用 Generic，完成后已恢复；Transport 和 Volume CC=7 未改。

## 2026-10-21：1.1 文件夹与手动 Arm

- `Keystation.control.js` / `Keystation.config.js`：左右收展、中央 Arm；上下使用 GUI 可见轨导航。Play / Stop / Record 的实际录音语义不变。
- `Library.control.js` 未修改；保留 MIDI / 吉他两组互斥、选轨不自动 Arm、加载后 650 ms 清理历史 Arm。故先等音色加载完成再手动 Arm；加载期间过早点亮的 Arm 仍可能被原有清理复位。普通工程不受 Library 试听规则影响。
- 405 项相关 pytest 通过，覆盖分组 / 子轨 / 顶层 / 空选择、音频 / MIDI Arm、按下去重、录音中保护。Bitwig 控制台已确认 `Keystation Transport 1.1 ready: folders + manual arm`，无初始化错误。
- 未在正式 Library 创建录音 take；实体新映射的手感及实际录音仍需用户试按。没有改琴键、滑杆、音频输入输出或插件。
- 部署前备份：`~/storage/daw/Backups/keystation-fold-arm-20261021T195527Z/`；验证：`target/keystation-fold-arm/`。源码未 commit/push，收尾执行 Storage 恢复快照。

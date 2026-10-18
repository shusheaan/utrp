# Chord Lab 0.1.8：G/V 持键转位与焦点

[English](GV_FOCUS.md) · [使用](LEFT_HAND.cn.md)

## 修改

- V → 内部命令 19（左下），G → 内部命令 20（右上）。均按下触发，可与七个和弦键叠按。
- 删除物理 Esc / 左 Ctrl 移动映射；保留左 Shift 单独松开切换 Sustain。
- 不改变和声引擎、参数顺序、CLAP ID、音色与 MIDI 路由。
- Keyboard 失焦问题根因是 Sway 默认鼠标跟随焦点，不是按钮或 mouseExit。
  用真实 Wayland pointer motion 复现；IPC cursor warp 不会等价触发该焦点行为。
- 用户批准后，将 `/home/shu/work/gral/arch/sway/config` 设置为 `focus_follows_mouse no`，
  并即时应用。作用于整个桌面；没有让插件抢焦点，也没有伪造绿色状态。

## 自动化验收

- Python：118 项通过。
- CTest：4/4 通过。
- 键盘：199 项基础检查、1012 种有序双键/释放顺序；另覆盖全部七级和弦持键 G/G/V/V、重复抑制与最终释放。
- ModifierTap 通用状态机：2040 种组合序列通过；其中 Ctrl 是通用状态机测试输入，产品不再注册 Ctrl 动作。
- 真实 CLAP：七级和弦保持按住时上移两次、下移两次，核对最低音方向、音符数量、原位恢复及全部 Note Off。
- 旧 state 导入、19 参数、GUI 创建/缩放/重建、12 种采样率/块大小组合、混合 MIDI 与 Dark/Bright、独立实例状态恢复通过。

本机证据：`target/chordlab-gv-focus/`。旧插件与工程备份仅用于回滚，不恢复双产品开发。
本轮不是全部 98 音色、所有硬件键盘或跨操作系统的重新认证。

## Bitwig 本机验证

已备份、保存 Library，关闭编辑器后正常退出 Bitwig，安装 0.1.8 并重新打开原项目。
实际按住 C 点按 G，界面由 Cmaj7/C4 移至 Cmaj7/E4，后级 sfizz 与轨道输出电平正常。
点按 V 返回；松开和弦后显示释放。Sustain 保持独立：Shift 按下仍红，单独松开变绿，
再次单按关闭；C+Shift 不触发。Esc/Ctrl 单按不再移动。
原生鼠标移到 sfizz 时 Keyboard 仍绿，点击 sfizz 才红，点回恢复绿。
最后恢复 sfizz Controls 页面、Sustain Off、Keyboard On，并保存 Library。

安装文件：`~/.clap/Chord Lab.clap`，SHA256：
`7f3cc182b906794f994a315168e4d8d42d6e78dd6332fa2d89e2ba66c38e8cfe`。
REAPER synth.rpp 与 Guitar Frontend binary 的哈希未变。

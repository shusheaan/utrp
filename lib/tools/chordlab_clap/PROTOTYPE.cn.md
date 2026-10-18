# Chord Lab：JSFX → ysfx CLAP 样机

> 历史验收记录：通用样机已删除，本文命令不再是支持的安装流程。请使用 [当前 CLAP](README.cn.md)。

[English](PROTOTYPE.md)

## 目标与边界

保留 REAPER 原生 JSFX 作为基准，在 CLAP 中运行**同一份未修改的 JSFX**，
先验证引擎兼容性，再决定如何进入 Bitwig。没有重写和弦算法，没有修改用户正式
REAPER 配置、工程、音频设备或安装目录。

本样机使用通用 `ysfx-s FX.clap` 加载 Chord Lab，**不是已经独立打包、具有专属
plugin ID 的 Chord Lab CLAP 产品**。REAPER Lua manager、VKB 和窗口管理不在封装内。

## 2026-10-17 实测

环境：Linux x86_64、REAPER 7.78、ysfx 0.0.47、Dummy Audio、48 kHz / 256 samples，
独立 HOME / REAPER profile / headless Sway。没有连接真实 MIDI 或音频硬件。

| 验证 | 结果 |
| --- | --- |
| 同源 JSFX A/B：有序 MIDI 字节和 block 内 sample offset | 2,377 项中 2,376 一致，1 项失败 |
| 12 个调、7 个级数、三／七／九和弦、转位、复位、切换后记忆 | 通过所列 MIDI 用例 |
| 实体键盘路径模拟：channel 1 / 15、velocity 1…127 | 通过；不是硬件实测 |
| Sustain lock、踏板、重叠和弦、重复音符归属、panic | 通过所列 MIDI 用例 |
| 真实 RPP 保存、关闭、重开 | 7 项检查通过；九和弦／转位记忆一致，Sustain 安全重置 OFF |
| GUI | 双组谱表、钢琴、指板显示；鼠标 Sustain ON → OFF 实测成功 |
| Python 回归 | `70 passed`（样机及已有 Chord Lab 测试） |

### 已定位的失败，不应忽略

用例 2368：输入 pitch bend、CC1、Channel Pressure。原 JSFX 输出三条消息，
CLAP 仅输出前两条，缺少 `65:d0:45:0`。

固定版本依赖的 `clap-juce-extensions` commit
`24e70f7f7cde2842528bb66ff50260b1dc0f4dae` 在输出分支中只处理
`msg.getRawDataSize() == 3`，因而过滤两字节 Channel Pressure。
[对应适配层源码](https://github.com/free-audio/clap-juce-extensions/blob/24e70f7f7cde2842528bb66ff50260b1dc0f4dae/src/wrapper/clap-juce-wrapper.cpp#L1674-L1691)。
Program Change、单字节消息和 SysEx 也应作为后续回归项；本轮未逐项实测它们。
**本轮没有修改／重新编译上游 binary，故此缺陷仍在。**

### 其他未解决的兼容边界

- 动态参数加载后，初次 `TrackFX_SetParamNormalized` 设置 Computer mode 未生效。
  样机通过初始 plugin state 开启 slider14，以便测试 channel 16 控制协议。
  这不是宿主参数自动化已修好的证明。
- QWERTY、Tab、Enter、分号的物理按键／焦点分配没有移植；测试发送的是它们对应的
  channel 16 MIDI 命令。REAPER Lua/VKB 不能直接在 Bitwig 内运行。
- 强制用窗口管理器改变外框大小时，观察到内容裁切；关闭并重开编辑器恢复。
  不等于已通过各种 DPI、缩放和宿主窗口行为测试。
- 初始 state 保存 JSFX 绝对路径；搬目录后不能保证工程可恢复。
- 未验证 Bitwig 路由／录入生成后的 MIDI、transport 全生命周期、多实例、离线 render、
  其他 sample rate/block size、长期负载、macOS，以及实际合成器音频。
- A/B 比较 block 内 offset，不测跨 block 绝对延迟。测试通过不构成全功能等价证明。

## 复现

需要 Python 3.11+、REAPER Linux，以及 `prototype.toml` 固定版本的官方下载 ZIP。
脚本核对 SHA-256、保留发行包 LICENSE、复制未修改源文件并记录哈希；不自动安装。
**仅执行本目录脚本不会下载或启动 REAPER。**

```sh
curl -fL 'https://github.com/JoepVanlier/ysfx/releases/download/v0.0.47/YSFX.Linux.64-bit.CLAP.zip' \
  -o /tmp/ysfx-0.0.47.zip
python lib/tools/chordlab_clap/prototype.py \
  --archive /tmp/ysfx-0.0.47.zip --output /tmp/chordlab-ab-new
```

输出目录必须不存在；为运行 Lua 验收，应使用 `/tmp/chordlab-*` 路径。
在单独的测试桌面终端中运行（不要使用会改正式设备配置的个人 launcher）：

```sh
ROOT=/tmp/chordlab-ab-new
HOME="$ROOT/home" XDG_CONFIG_HOME="$ROOT/home/.config" \
  /home/shu/opt/REAPER/reaper -newinst -nosplash \
  -cfgfile "$ROOT/reaper/reaper.ini" \
  "$ROOT/prototype.rpp" "$ROOT/reaper/ab_test.lua"
```

处理 REAPER 自带的正常提示后等待测试完成，查看 `ab-result.txt`、`ab-events.tsv`。
原版 pinned wrapper 预期存在上面的 1 项失败。第一轮约数分钟。
随后在**同一个隔离实例**通过 Actions 加载并运行 `reaper/state_ab.lua`，查看
`state-result.txt`。状态测试独立于消息兼容性测试，不能抵消第一轮失败。
再次执行完整 A/B 应生成新目录，不在已有两轨工程里重新执行 setup。

```sh
python -m pytest lib/tools/chordlab_clap lib/tools/chordlab/tests -q
luac -p lib/tools/chordlab_clap/ab_test.lua
luac -p lib/tools/chordlab_clap/state_ab.lua
```

本机完整实验留档在 `target/chordlab-clap-prototype/`（Git ignored）：包含发行 ZIP、
样机 binary、源文件快照、逐事件日志和截图。留档 RPP 仍引用原 `/tmp` 路径，
不是可移动安装包；重新运行生成器才能为新目录生成正确 state。

## 推荐到 Bitwig 的路线

1. **短期沿用 JSFX 引擎**：修复／升级封装适配层后重跑 A/B；Bitwig 验证
   `Chord Lab → instrument`、生成 MIDI 的录制、保存／重开和真实键盘。
2. **需要完整工作流时做专用薄封装**：仍复用 JSFX，补齐输入／焦点、参数定义、资源
   打包和稳定 plugin ID。这样同一套和弦逻辑仍可同时用于 REAPER 与 Bitwig。
3. **有证据表明引擎阻碍需求时再原生重写**：例如无法合理解决的 UI／实时性限制，
   或确实需要现有 MIDI 模型之外的原生 note expression；继续用 JSFX 做参考实现。

不建议现在就维护两套独立和弦算法。也不建议把通用 ysfx 样机当作已完成的移植。

## 上游与分发

[ysfx 官方仓库](https://github.com/JoepVanlier/ysfx)提供 JSFX host。
本轮采用的预发布 binary ZIP 内 `LICENSE` 是 AGPLv3，已原样保留；不要把仓库
library 的 Apache 标注当成整个 plugin binary 的许可。对外分发前另行核对全部依赖
和素材条款。本轮仅本地实验，未发布插件或创建 fork/branch。

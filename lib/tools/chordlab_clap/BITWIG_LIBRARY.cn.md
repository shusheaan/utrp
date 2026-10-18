# Bitwig Library：2026-10-17

[English](BITWIG_LIBRARY.md) · [首次宿主验证](BITWIG_RUNTIME.cn.md)

## 工程与依赖

- 正式工程：`~/storage/daw/Library/Library.bwproject`。
- 应用菜单入口：`Bitwig Library`；原生 Bitwig Studio 6.1.4 Trial，workspace 2。
- REAPER 保持关闭；本轮未改 REAPER 工程、插件源码或已安装的二进制。
- 两个宿主共用 `~/.clap/Chord Lab.clap`、`~/.clap/Guitar Frontend.clap` 和
  `/usr/lib/clap/Surge XT.clap`，不维护两份宿主专用构建。
- 不降级系统 GLIBC。原生宿主使用现有系统库；此前 Flatpak 的 GLIBC 2.42
  无法加载要求 2.43 的本机插件。将来若必须支持 2.42，应在旧 sysroot 中重新构建
  相关插件并复测，而不是替换运行中系统的 libc。

## 两条链路

```text
电脑键盘（插件有焦点） ───────────┐
Keystation / All ins ──────────┴→ Chord Lab → Instrument Selector → Master
                                               ├─ Warm Veil / Surge XT
                                               ├─ Dark Choir / Surge XT
                                               └─ Silver Haze / Surge XT

Spark GO USB mono → Guitar Frontend → Chord Lab → No output
```

- `01 - pad library`：armed、Monitor On、轨道音量 −10 dB。
  三个 Pad 共用一个 Chord Lab；Selector 每次选择一个音色，不叠加三个音源。
- `guitar - raw detection`：Monitor On，识别器在 DAW 效果器之前。
  此轨只显示识别到的音，不驱动 Pad；No output 避免叠加 Spark 直接监听。
  Spark 硬件自身已经加入的效果无法由这条路由去除，宜使用干净设置。
- 吉他是已接受的单音版本；不承诺双音、三音或零延迟。
- 两条链各有独立 Chord Lab state。这里不是把吉他和键盘合并到一个全局总线。
- 这是三个音色的新研究库，不是 REAPER 95 个音色的完整迁移。

## 使用

1. 打开工程，选 `01 - pad library`。在底部 Instrument Selector 中点击音色左侧小圆点
   切换发声层；点击名称选择该层，打开其 Surge XT 编辑界面调音色。
2. 电脑键盘要点击 Chord Lab 窗口，确认 Keyboard 绿色。
   `Z/X/C/A/S/D/F` 对应 `6/7/1/2/3/4/5`；`Esc` 左移、单独左 `Ctrl` 松开右移、
   `Space` 恢复当前类型默认位置、`Tab` 切换三/七/九和弦并记忆、单独左 `Shift`
   松开切换 Sustain。Ctrl/Shift 参与组合键时不触发单键动作。
3. 实体 MIDI 不要求插件焦点，但控制器必须在线，轨道输入/监听必须开启。
   真实手弹和混合输入最终验收仍待完成，不能用电脑键盘测试替代。
4. 吉他显示：选择吉他轨，打开该轨的 Chord Lab。识别开关在前面的 Guitar Frontend。
5. 总响度调整 Pad 轨的 volume；单个音色可调该 Selector layer 的 volume 或
   Surge Global Volume。Silver Haze 原始电平明显较低，本轮没有自动响度匹配。
6. 项目保存完整插件状态；另存单个 Surge 音色时使用其 Save Patch。
   三份基础 FXP 已复制进工程的 `Presets/`。Surge 标题可能仍显示载入时旧路径，
   但工程移动并重新打开后的三个音色均已实际发声验证。

### 三个 Pad 来源

沿用本机 `~/storage/daw/patches/pad-lab-20261016/` 的 A/B/C 研究版本，
不是本轮从零制作，也不是 Bitwig 原厂预设：

| 音色 | 基础预设 | 特征 |
| --- | --- | --- |
| Warm Veil | Bluelight / Pads / Juno | 温暖、柔和的模拟 Pad |
| Dark Choir | Giana Brotherz / Pads / Deep Choir | 暗色人声氛围 |
| Silver Haze | Damon Armani / Pads / Freedom Message | 较轻、较空灵的波表氛围 |

原目录 `patches.json` 记录此前的具体参数修改。使用预设内置效果，没有额外插入公共 Reverb。

## 本轮验证

| 项目 | 结果 |
| --- | --- |
| Python 回归 | 102 passed |
| C++ CTest | Chord 3 passed；Guitar 2 passed |
| 已安装 CLAP 的独立 host probes | ports、state、生命周期、多采样率/块大小等通过 |
| Bitwig GUI | 14 条键位/状态检查 + 4 条松键/失焦检查通过 |
| 三音色输出 | 都有非零输出，没有检测到 clipping |
| 正式工程移动、保存重开 | 三个音色重新实际录制，状态与发声可用 |
| 真实吉他、实体 MIDI、混合输入 | 未完成最终实弹验收 |
| 全部 REAPER 音色 / 长期热插拔 / Bitwig MIDI 录制 | 不在本轮通过范围 |

重开后定向录制 Bitwig 输出端口（不是麦克风），峰值 dBFS：
Warm Veil −16.244449；Dark Choir −18.396375；Silver Haze −33.320721。
这是固定测试和弦的结果，不是任何演奏都不会 clipping 的保证。

证据：`target/bitwig-library-validation/`，含测试日志、JSON、截图、WAV 和本次桌面测试脚本。
脚本依赖当时窗口 ID/坐标，不应直接在其他工程盲跑。
`pad-02.wav` 是 Keyboard 未激活时的静音排障样本，成功证据是 `pad-02-retest.wav`
及 `reopened-pad-02.wav`。Surge 加载时有辅助 audio bus 激活警告；主立体声输出已验证，
未验证辅助输出，不宣称日志零警告。

## 尚未解除的硬件阻塞

测试期间 Spark GO 从系统 USB/ALSA 列表消失，而 Keystation 仍在线。
因此不能宣称当前已达到完整的“插上就弹”状态。

为完成软件测试，Bitwig 临时选用了 HDMI 音频设备，输出到 HDMI 扬声器的连线已断开，
避免测试声突然外放。**当前该临时设置不等于 Spark GO 的可听演奏状态。**
工程已保存，默认选择 Warm Veil；Sustain Off，窗口并排。

Spark GO 重新上线后，仍需：

- [ ] 在 Bitwig Audio 设置恢复 PipeWire / Spark GO / 48 kHz / 256 samples，必要时保存重启刷新设备。
- [ ] 核对 Master → Spark GO 的立体声输出，吉他轨使用 Spark GO mono input，而不是电脑麦克风。
- [ ] 用户实弹 MIDI、单音吉他，验证声音、灰色音符和电脑键盘混合输入/松键行为。
- [ ] 再保存重开，确认设备恢复与实际发声。完成前不标记全量验收通过。

## 基础内容库安装（同日后续）

用户要求补齐 Essentials / 基础库。检查发现 Essentials v15 已安装，随后通过官方
Dashboard → Packages → Available → Install All 安装其余 14 个当前授权可用的包。
最终 Installed 页面 15 项均显示 Uninstall，安装清单也有 15 条记录。

- Essentials 核心包：下载 298,377,822 bytes，内容 343,855,497 bytes；包括
  2,663 个 presets、126 个 clips、270 个 impulses、215 个 wavetables 和 74 个 curves。
- 全部当前可用内容：安装内容 7,970,737,978 bytes（约 7.97 GB）；此次新增下载
  4,887,752,917 bytes（约 4.89 GB）。文件系统 `du -sh` 为 7.5G，含分配粒度差异。
- 补齐 Grand Piano、Electric Keys、Acoustic Drums and Percussion、Classic Drum Machines、
  Bass and Guitar、Polymerics、Drums and Indian Percussion，以及 JoMoX、Raw Cutz 和合作方 Loop 包。
  多个合作方包明确为 teaser，不是完整商业素材库。
- 安装目录沿用 `~/.BitwigStudio/installed-packages/5.0/`，由 Bitwig 自动索引；
  没有复制全部样本到 Library 工程，也没有变更现有轨道或音频设备。
- Install All 只覆盖当前账号/版本提供的包，不代表解锁完整商业目录。
  内容包 Essentials 与软件授权版本 Bitwig Studio Essentials 是不同概念。
- 证据：`target/bitwig-content-validation/installed.json` 和 Packages 页面截图。

本次内容安装不解除上述 Spark GO 硬件阻塞。

## 完整音色迁移后续

正式 `~/storage/daw/Library/Library.bwproject` 已升级为 95 个原音色 + 三个保留 Pad。
前面的三 Pad 工程说明属于历史状态；最新替代混响、共享路由、录音、重开测试及硬件缺口，
见 [完整 Library 迁移记录](../bitwig_library/README.cn.md)。尚未完成硬件验收，不删除 REAPER。

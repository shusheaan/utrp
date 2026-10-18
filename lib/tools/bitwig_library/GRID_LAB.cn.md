# Grid Lab：Warm Fractal Veil

[English](GRID_LAB.md) · [Library 指南](README.cn.md)

## 交付与来源（2026-10-18）

- 工程：`~/storage/daw/Grid Lab/Grid Lab/Grid Lab.bwproject`。
- 约 24 秒的内部输出录音：同目录 `Preview.wav`。
- 这是独立的学习示范，没有修改正式 `Library.bwproject` 或 CLAP 插件。
- Bitwig Studio 6.1.4 Trial；使用已安装 Essentials 的官方预设
  `Poly Grid/Fractal Machine - Divine Radiance.bwpreset`，不是本轮从零搭建的原创网络。
- 本轮完成官方网络的选型、宏参数改编、持续和声 clip、项目设置、保存恢复和输出检查。
- 官方源文件：`~/.BitwigStudio/installed-packages/5.0/Bitwig/Essentials/Presets/Poly Grid/Fractal Machine - Divine Radiance.bwpreset`。
- 工程、官方内容、录音都不进 Git；本文件只记录配置、来源与验证。

## 工程与玩法

1. 打开工程；如左上显示 `Activate Audio Engine`，点击激活。
2. 在 Mix / Clip Launcher 中点击 `Warm Fractal Veil` 第一格 `S1` 左边的小三角。
   本例只有 Launcher clip；仅点主播放按钮不等于已经触发这个 clip。
3. 速度 72 BPM，调性标签 C# Minor，16 小节循环；音符 C#3、E3、G#3、B3，
   每个持续 16 小节，velocity 约 100。这是 C#m7 和声，不是自动换和弦。
4. 选择轨道，在下方 device panel 找到 Poly Grid。点击彩色网络缩略图展开接线图。
5. 先玩 `Lowpass → Space → Speed → Steps → Detune`；每次只改变一个。
6. 停止播放会有 release / 空间尾音。不要因为暂时安静就立刻大幅提高总音量。
7. 保存副本再进行大幅改线。想亲手弹奏时停止 Launcher clip，开启该轨录音准备，
   输入保持 `All ins`；本例未接入 Library 的共享 Chord Lab 控制链。

轨道音量 -10 dB，Master -18 dB，最终停止播放，Master 不静音。
示例中保留默认空 Audio 2 和 FX 1；它们不是音色必要组成。

### 已设置的宏

| Macro | 本例设置 | 用途 |
|---|---:|---|
| Lowpass | 35% | 调节明暗；先小幅提高来听清泛音，再降低获得暗色 |
| Detune | 15% | 轻微失谐宽度；过大容易模糊和声 |
| Attack | 85% | 较缓的起音控制 |
| Release | 80% | 较长的松键尾音控制 |
| Speed | 25% | 内部循环速率；由预设映射到离散倍率，不等于 BPM |
| Space | 55% | 官方预设映射的空间混合控制，不是统一的混响秒数 |
| Steps / Output | 保留预设值 | 泛音过程的步数 / 输出；先避免大幅修改 Output |

这些是宏归一化百分比，不是 Hz、秒或实际失谐 cents。

## 这张网络为什么值得用 Grid

实际打开并检查到的主要部分：

- Cycle generator：Transport phase、reset、quantization、倍率选择，组织循环。
- Pitch generator：相位与数学处理形成泛音序列；Steps 与 Step offset 控制结构。
- Pulsar synthesis：Phasor、Window、Formant、Blend、phase sync、sine 等共同塑造波形。
- AR、phase shaping、Lag：控制脉冲形状和动态。
- Voice stacking、detune、pan：扩展声音层次与立体声。
- Average / subtraction：去除 DC offset；Mixer、Audio Out、示波器负责输出和观察。

这份示范是“固定和声输入 + 持续演化的合成结构”，并不保证永不重复；
没有额外实现随机音阶旋律、随机换和弦或完整自动编曲器。
泛音序列也不等同于经过十二平均律音阶量化的独立 MIDI 旋律。
顶上的 C# Minor 标签不是把任意 Grid 音频强制校正到音阶的开关。

## 和 Endless 的关系

参考现有 `lib/tools/pipeline/specs/endless.toml` 的设计方向：
At Your Best outro 的 bell / FM / warm pad，Impietas + Deathwish 的 ghost / distant drone。
这轮没有重新逐段听辨专辑，也不声称原曲用了 Grid 或本例精确复刻原曲。
普通暖 Pad、EP、saw chords 继续用 Surge / 现有音源更直接；
当目标是自定义相位、泛音规则、脉冲形状和内部动态关系时才值得进入 Grid。

## 验证与边界

- 工程保存后关闭并重新打开；宏和 clip 保留，重新触发可见立体声输出。
- 单独检查 piano roll：四个音符、16 小节长度与调性标签一致。
- 捕获约 24 秒 48 kHz stereo float 输出；peak -11.31 dBFS，RMS -36.46 dBFS，
  NaN / Inf 均为 0，没有样本触及 0 dBFS。测量不是主观听感或相似度验收。
- 录音期间临时断开 Bitwig 到扬声器的直连；交付前恢复。
- 本轮未做真实 MIDI 键盘演奏、吉他输入或全 Library 音色复验。
- 证据在 `target/grid-lab/`；不要把这个局部示范验收说成所有功能全量验收。
- Grid 是 Bitwig 原生 device，不是可直接带到 REAPER 的 CLAP；跨宿主可渲染音频。

## 学习顺序与官方资料

先掌握 oscillator → filter → envelope / VCA → output，再学 LFO、random、slew；
随后学 gate、clock、phase、sequence、概率与音阶约束；最后看 polyphony、voice stacking、
feedback、DC 与增益安全。不要一开始背全部模块。

- [The Smallest Generative Patch](https://www.bitwig.com/learnings/1-minute-patch-293/)：最小入门。
- [Modular Concepts & Let's Build an Everything](https://www.bitwig.com/learnings/modular-concepts-lets-build-an-everything-42/)：Phase、Pitch、Polyphony、Ambient Set；部分章节有工程下载。
- [The Grid 手册](https://www.bitwig.com/userguide/latest/welcome_to_the_grid/)：Poly Grid、FX Grid、Note Grid 与编辑基础。

Ambient Set 是整体制作教程，不代表所有声音都必须用 Grid，亦不保证该章节单独提供下载工程。

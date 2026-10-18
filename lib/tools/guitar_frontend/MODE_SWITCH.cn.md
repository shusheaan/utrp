> 已退役：2026-10-18 真人试奏未通过；0.2.1 已移除双音与 Mode。以下仅为历史实验记录。

# Guitar Frontend 0.2.0 — Mono / Dyad 实验开关

[English](MODE_SWITCH.md)

## 怎么试

Bitwig 选中 **GUITAR - raw**，展开 **Guitar Frontend** 的宿主参数：
- **Detect = On**：开启识别；Off 释放所有检测音，不改变干声。
- **Mode = Mono**：日常单音。默认模式，沿用 0.1.2 原算法及 64/8/24 ms 设置。
- **Mode = Dyad (Experimental)**：保守双音实验。先试 D/G 空弦，同时拨、力度接近，其他弦止音。
- 切回 **Mono** 就恢复单音。无需重新加载或另加插件；Mode 跟随工程保存。
- 双音模式不是自动单双音：单音、八度组合、证据不足的音可能不显示，不能代替 Mono。
- 不支持三音或扫弦，也不能保证这类输入一定拒识，误报仍有可能。

使用宿主通用参数面板，没有新增自绘窗口。参数名保持 English。
Mono confidence / stability / release 只作用于 Mono；Gate、输入声道、固定 velocity 两模式共用。
两个只读 MIDI note 参数显示两个输出音。
Pitch evidence 在 Mono 是周期性证据，在 Dyad 是频谱覆盖率，**不是正确概率**。

## 为什么不自动融合

自动融合需要区分“单音+泛音”和两个真实音，不能直接拼接两个检测器输出。
现在每次只运行选中的算法，双音不会给 Mono 加等待时间或 FFT 运算。
Mode、Detect、输入改变以及 reset 清空分析历史并释放此前送出的全部音。
宿主事件队列拒收时保留待释放音并重试，不把未送达的 note-on 算成已送达。

## 路由与状态

干声音频逐样本透传，识别 MIDI 固定 channel 2。
Library 原有 Note Receiver 将 2 映射到 15，Chord Lab 将 15 用作只显示并阻止下发音源。
**本版本不修改该路由，不把吉他识别改成合成器演奏。**
Spark 硬件已加入的效果无法由插件撤销，识别器仍应在 DAW 效果链最前面。

CLAP ID 保持 org.utrp.guitar-frontend。旧 0.1.x 状态可读入，自动使用 Mono。
新状态 v2 保存 Mode；旧插件不保证能读 v2，回滚应同时使用升级前工程备份。
源码在本目录；安装文件 ~/.clap/Guitar Frontend.clap 两 DAW 共用，但需要重新加载才能更新。

## 自动验证（不是现场演奏认证）

- Release / UBSan：各 3/3 CTest，包含原单音回归。
- Python：108 tests passed。
- 独立 CLAP host：原 40 个单音 rate/block/float32/float64 组合；
  双音 5 个采样率 × float32/float64，模式切换、部分事件拒收、
  reset、stop/start、Detect、输入切换、释放音及干声逐样本一致。
- 参数边界、旧状态读取、新状态保存、部分流读写、坏状态事务性拒绝、双实例隔离。
- Native C++ 与 Python 候选逐帧对照：target/guitar-dyad-clap/runtime-parity.json。
- Mono 原/新 replay 三段录音输出逐字节相同：mono-identical.json。
- 固定缓冲 C++，音频回调无 Python、文件 I/O、动态分配或锁。

DG 开发录音 56–90 ms 是之前离线起音测量，不含接口、宿主和 UI；
见 [双音研究](DYAD_SPEED.cn.md)，不能承诺 MIDI 键盘级响应。
本机 48 kHz / 256 samples 是当前试用设置；高采样率或极小 block 实时裕量需另测。
离线运算速度不等于没有实时 xrun。

构建及证据：target/guitar-dyad-clap/。
旧安装文件备份：target/guitar-dyad-clap/Guitar-Frontend-0.1.2.clap。
现场 Bitwig 重载和试弹状态以本轮交付说明为准。

## 本轮部署状态

0.2.0 已安装到共享 CLAP 路径，运行中的 Bitwig 尚未重新加载。已备份磁盘上的 Library 工程；保存内存中工程并重载等待用户确认。234 个 Native/Python 对照用例、52148 帧一致；A3 和 D4 对照录音无双音输出。未标注录音只用于移植一致性，不用于准确率结论。

## Bitwig 重载验证完成

已保存并正常重启 Library，确认新 CLAP 已加载。现场 48 kHz / 256 samples：合成 D3/G3 在 Dyad 同时高亮，合成 E4 在 Mono 正确高亮，停止后均撤回。两次各 6 秒主输出录音 peak=0，没有触发钢琴音源。测试信号已移除，Spark capture_MONO → Bitwig in1 恢复；保存为 Mono。左下角 Guitar Frontend 参数搜索已筛选 mode；拖 Mode 旋钮向上为 Dyad、向下为 Mono。真人准确率和主观速度仍待用户试弹。

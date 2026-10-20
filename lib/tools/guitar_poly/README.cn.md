# 双音／三音低延迟前级：候选筛选

> 历史研究档案，不是当前运行插件。正式产品现为 [Guitar Frontend 0.2.1 单音](../guitar_frontend/README.cn.md)；以下 0.1.0 等描述仅对应当时实验，双音未通过用户验收。

[English](README.md) · [机器可读结果](screening.json)

## 用户目标与本轮结论

- 双音优先，三音作为实验；不做六弦扫弦。
- 分解和弦需要允许上一音继续响。连续弹很多不同音没有数量上限，但第一阶段最多跟踪三个同时在响的独立音高。
- 不确定的音宁可不发 MIDI；不能用当前所选和弦强行猜音、假装识别成功。
- 保留独立 audio→MIDI 前级结构，Chord Lab 只接收 MIDI 和显示，不绑死某个识别引擎。

**本轮仅完成开源候选的隔离筛选，未交付可用的双／三音 CLAP。正式 Guitar Frontend 仍是 0.1.0 单音版，binary hash 未变。**

## 实测候选

[Polyphonic-Pitch-Detector-for-guitars](https://github.com/luciamarock/Polyphonic-Pitch-Detector-for-guitars)，固定 commit `dc4565b3827afd34db47d8ecc770a29b1aed61f0`，上游标注 GPL-3.0。源码只放在 `target/guitar-poly-research/upstream/`，未并入正式插件。

实际代码 `cPdct::doEnergyAnalysis()` 对每个半音 resonator 的能量使用固定 `0.001` 门槛；没有在这段输出逻辑里剔除其他音的泛音，也没有根据新旧音之间的关系推断独立声部。`WINDOW_SIZE=960` 只是分析更新间隔，不等于正确识别整组音所需时间。发布说明中的低延迟数字不能替代对该源码版本的验证。

实验只编译 DSP 文件：定义 `RUN_AT_48KHZ`，用 `LOG_CONFIG_H` 关闭其默认实时日志；没有修改识别算法、没有 GUI/音频设备访问。用上游固定门槛直接测试，没有逐例调门槛。

### 108 组同时起音合成输入

测试电平峰值 0.03/0.1/0.3；正弦及八阶谐波波形、指数衰减；包含八度、五度、三度、相邻半音。定义“曾识别齐”为演奏期间整个音符集合完全正确、连续至少 20 ms，**这只是宽松筛选条件，不是完整通过率**。

| 同时音数 | 用例 | 曾识别齐 | 曾出现额外错误音 |
|---|---:|---:|---:|
| 1 | 36 | 19 | 12 |
| 2 | 48 | 16 | 4 |
| 3 | 24 | 7 | 0 |

三音组“额外音为零”不代表准确：主要问题是漏音或根本未输出。

可复现例子（harmonic、总峰值 0.3）：
- MIDI 40 单音输出过 39、40、41、52，不能通过。
- MIDI 55+59：第一次整组正确约在起音后 61 ms。
- MIDI 48+52+55：约 161 ms 才识别齐。

另测 18 组依次相隔 80 ms 起音、每音持续 400 ms 的重叠分解；平均整个音符集合正确的时间占比约 12.72%，包含起落音转换期。不把该指标和上表“曾正确 20 ms”混用。

这些是简化合成筛选，**不是实际吉他准确率，也不是所有开源算法的结论**。未调整的固定门槛对输入电平敏感；仍不足以作为用户要求的实时多音方案，因此不部署。

## 其他路线（2026-10-17 查证）

- [Jam Origin 商店](https://jam.live/shop/)：桌面许可证标价 USD 149.95。
- [官方试用／平台列表](https://jam.live/downloads/)：完整功能试用带间歇中断，桌面为 Windows/macOS；没有列出 Linux 原生版。MG3 当前 beta，MG2 是 legacy stable。先试，不先买。
- [官方旧版 Linux 使用说明](https://www.jamorigin.com/docs/daw/)提供 Wine/Ardour 路线，不能据此宣称 MG3 在当前 Linux/REAPER/Bitwig 已通过。当前未安装或运行 Jam Origin。
- [Basic Pitch](https://github.com/spotify/basic-pitch) 是值得参考的多音转录项目；[默认模型常量](https://github.com/spotify/basic-pitch/blob/main/basic_pitch/constants.py)使用约 2 秒输入窗，不能把 256-sample hop 当作端到端识别延迟。未将其直接包成实时前级。

## 后续验收必须测什么

1. 第一优先级是二声部的泛音排除、八度/五度干扰、强弱声部差异、重复拨弦和连续重叠衰减；再增加三声部。
2. 有真值标签的真实干声素材：单音、双音、三音、分解、止音、噪声、弱拨弦。不能以“界面亮了”代替准确性验收。
3. 同时报 precision/recall、额外音/漏音、每个音的起音 P50/P95/最大延迟、释放延迟、未检出率、CPU 与掉音情况。漏音不能从统计中悄悄剔除，只报成功音的漂亮延迟。
4. 算法延迟、USB/宿主缓冲、MIDI→Chord Lab UI 刷新分开测；直接监听吉他不等于识别界面零延迟。原单音约 80 ms 的合成起音结果不满足新的跟手要求。
5. Linux Jam Origin 试用若可运行，可用相同输入作参照；不可运行就不建议为 Linux 使用先购买。无需把商业引擎嵌入自家 CLAP：其 MIDI 输出可以作为独立前级接 Chord Lab。

## 复现

获取上述固定 commit 的源码到 `target/guitar-poly-research/upstream/`（保留上游许可证），然后从项目根执行：

```sh
d=$(echo target/guitar-poly-research/upstream/*)
c++ -std=c++17 -O2 -DRUN_AT_48KHZ -DLOG_CONFIG_H \
  -I"$d/pdct_lib/Pdct" -I"$d/pdct_lib/include" -I"$d/pdct_lib/Main" \
  lib/tools/guitar_poly/probe.cpp "$d/pdct_lib/Pdct/cPdct.cpp" \
  "$d/pdct_lib/Pdct/cPdctOutput.cpp" "$d/pdct_lib/Pdct/cComplex.cpp" \
  "$d/pdct_lib/Pdct/cComplexResonator.cpp" -o target/guitar-poly-research/pdct-probe
python lib/tools/guitar_poly/benchmark.py lib/tools/guitar_poly/benchmark.toml \
  target/guitar-poly-research/pdct-probe target/guitar-poly-research/results.json
python -m pytest -q lib/tools/guitar_poly/test_benchmark.py
```

Python 依赖 NumPy，不使用 pandas。完整事件保存在 `target/guitar-poly-research/results.json`。该 probe 依赖本机 native double 的内存表示，仅为当前 Linux x86-64 隔离实验程序，不是可分发插件。

## 保守输出的新实验

后续正式单主音插件已更新为 0.1.1；以上 0.1.0/hash 是当时的筛选历史，不是当前安装状态。最新 1–3 音离线实验、D/G 对照与扫弦拒绝失败见 [保守识别实验](CONSERVATIVE.cn.md)。该实验尚未部署。

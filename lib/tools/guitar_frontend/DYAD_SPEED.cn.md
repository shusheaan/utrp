> 已退役：2026-10-18 真人试奏未通过；0.2.1 已移除双音与 Mode。以下仅为历史实验记录。

# 双音提速：单音主链保持不变

[English](DYAD_SPEED.md) · [首次双音研究](DYAD_STUDY.cn.md)

## 2026-10-18 的交付边界

这是离线实验升级，**没有部署双音 CLAP，没有改 Bitwig 工程或正式单音参数**。
正式 `Guitar Frontend.clap` 和 `Library.bwproject` 的 SHA-256 与实验前一致。
单音 C++ 引擎、plugin.cpp、defaults.toml 未修改；现有单音使用不受本轮影响。
未声称未来单双音自动切换在任何输入上都不会误判。

## 根因与修改

1. DG 实录四次慢起音，主要被基音强弱比例限制挡住：即使两弦拨奏力度接近，
   两个基音的强度和衰减也不相同。把实验最小幅度比从 0.55 调到 0.20，
   不降低 97% 谐波覆盖要求，也不取消每音至少两个独立分音的要求。
2. `dyad_speed.toml` 使用 48 ms 窗、4 ms hop、连续三帧确认。
   两帧确认曾把单音强二次泛音的起止音误报为双音，因此没有采用。
   40/32 ms 更短窗口在真实 DG 上出现高八度错误或大量拒识，也未采用。
3. `dyad_experiment.py` 增加两道泛音歧义检查：
   - 有更低的观测峰解释上方谐波时，不把该谐波晋升成新音的基音。
   - 基音弱到没有单独峰时，如果额外分音支持更低的基音解释，也拒绝高八度猜测。
     这些额外峰可能只占总能量很小一部分，单凭 97% 覆盖率会忽略它们。

没有硬编码 D/G 音高，没有延长保持来掩盖漏检，没有修改正式单音算法。
广泛的“频率分辨率范围内都拒绝”曾大幅降低覆盖率却仍有错误，已弃用。

## DG 实录对照

同一段 Spark GO 录音，前八次 D3/G3 拨奏（5.40–24.77 秒）：

| 指标 | 原实验 64/8/两帧 | 当前候选 48/4/三帧 |
|---|---:|---:|
| 至少一次正确输出的拨奏段 | 8/8 | 8/8 |
| 错误双音输出 | 0 | 0 |
| 首次确认范围 | 72–668 ms | **56–90 ms** |
| 自动稳态窗口正确帧占比 | 810/1126，71.9% | **2180/2252，96.8%** |

当前八次首次确认分别为 64、64、58、74、90、56、60、58 ms。
仍有拒识空白，不能称作连续完美追踪。录音已用于开发，**不是独立验收集**。
时间相对 10 ms RMS 活动门限，不是精确拨弦时间，不含接口/宿主/UI 延迟。
后段非受控演奏不算 D/G 正确率。录音退出码 1 与 WAV 元数据警告仍保留，详见首次研究。

## 扩大回归，不用单次 DG 成功冒充通用成功

每组枚举 1,156 个不同弦的去重音高对，标准调弦 0–24 品。
“正确”表示持音内至少一次正确且全片没有错误；不是持续追踪率。

| 合成信号 | 正确 | 错音 | 全程拒识 | 仅止音后确认 |
|---|---:|---:|---:|---:|
| 等 RMS，衰减谐波 | 803 | 0 | 352 | 1 |
| 纯正弦双音 | 0 | 0 | 1156 | 0 |
| 扰动谐波、±12 cents、噪声，第二音幅度 0.85 | 861 | 0 | 295 | 0 |
| 同类扰动，幅度 0.50 | 791 | 0 | 364 | 1 |
| 同类扰动，幅度 0.30 | 738 | 0 | 417 | 1 |

幅度 0.50 组曾出现 18 个错误用例，促成弱基音/高八度保护；因此这些现已成为开发回归，
不再是未见过的 holdout。八度、同音弦和不确定组合仍保守拒绝。未通过三音/扫弦验收。

单音保护筛查：
- 五组相位种子，合计 **980 个完整单音起止音 + 200 个无重叠单音旋律**，无双音输出。
- A3 实录前 38.2 秒：9539 帧无双音输出。
- D4 历史录音全 45 秒：11239 帧无双音输出；仅 13.9 秒之后用于 D4 音高回归，前段不当作纯 D4 标签。
- Guitar Frontend pytest **101 通过**；正式单音 detector / CLAP host CTest **2/2 通过**。

这些是有限数据上的无误报，不是对任意真琴信号的百分之百保证。

## 单音提速单独评估

用当前 0.1.2 源码重跑，不沿用旧版本的结果：
- 40/32 ms 短窗：即使部分合成测试通过，D4 真琴仍重新出现低八度错误；不采用。
- 64 ms 窗、4 ms hop、8 ms stability：连续旋律测试失败；不采用。
- 64/4/16：通过已有合成测试及 A3/D4/历史留弦片段；合成最坏起音从 80.25 ms 到 76.24 ms，
  仅约 4 ms 收益，合成最坏释放反而从 95.15 ms 到 99.16 ms。
  仍需更多独立真琴验证，不替换正式 64/8/24。

不能说单音已经达到理论极限；本轮只是没有找到值得立即部署且已充分验证的提速方案。

## 复现与文件

```sh
OPENBLAS_NUM_THREADS=1 python -m pytest lib/tools/guitar_frontend -q
OPENBLAS_NUM_THREADS=1 python lib/tools/guitar_frontend/dyad_study.py \
  lib/tools/guitar_frontend/dyad_speed.toml target/dyad-speed-recheck
OPENBLAS_NUM_THREADS=1 python lib/tools/guitar_frontend/dyad_safety_study.py \
  lib/tools/guitar_frontend/dyad_speed.toml target/dyad-safety-recheck
python lib/tools/guitar_frontend/latency_study.py \
  lib/tools/guitar_frontend/latency_study.toml target/mono-timing-recheck
```

证据目录：`target/guitar-dyad-speed/`。当前最终结果：
`matrix-lower-root/48ms.json`、`unequal-0.3.json`、`unequal-0.5.json`、
`dg-current.json`、`dg-current-scored.json`、`a3-current.json`、`d4-current.json`、
`mono-phase-safety.json`、`mono-real.json`、`mono-timing/all-results.json`。
`INVALID-wrong-ringing-source.*` 是研究脚本首次误选录音的无效结果，不用于任何结论；
已以原录音 SHA-256 校验修正，并重跑 `mono-real.json`。
早期 `matrix-final` / `dg-final` 等文件是中间结果，以本节列出的 current/lower-root 为准。

下一步：先用新的真琴双音录音做独立验证，再移植固定缓冲 C++ 并测试单双音仲裁。
单音输出不能为了等待双音而额外延迟；不确定时不凭空加第二音，也不能简单合并两个检测器的输出。
Python 实验不能直接放入 CLAP 音频回调。日常吉他仍保持单音、仅显示、不触发合成器的原链路。

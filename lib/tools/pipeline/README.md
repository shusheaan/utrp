# pipeline — 音色复刻管线(共享框架)

一张专辑 = 一个 `specs/<名>.toml`。流程两侧对应两个 venv(见下),模块 DAG:

```
albumspec.py   冻结数据类 + TOML 加载(唯一的配置入口)
spectral.py    纯 numpy 分析函数(两侧共用,无 I/O):band profile +
               深度音色特征(包络/谐波/centroid 轨迹/调制/立体声)
analysis.py    librosa 侧:separate / scan / measure / drums
synth.py       surgepy 侧:render(渲染+打分+fxp 落 lib)/ project(RPP)/
               browse(全厂库自动扫描选备选)
drummidi.py    鼓 pattern -> MIDI + step grid(纯 stdlib,任意 python)
smf.py         最小 Standard MIDI File 写入(纯函数;harmony 也复用)
rpp.py         REAPER 工程文本生成(纯字符串函数)
```

## 用法(新专辑六步)

```sh
A=~/.cache/timbre-pipeline/venv-analysis/bin/python  # librosa/demucs(Python 3.12)
S=~/.cache/timbre-pipeline/venv-render/bin/python    # surgepy(Python 3.14,须匹配系统 Surge)

$A analysis.py specs/x.toml separate   # demucs -> ~/.cache/demucs-stems(可重建缓存)
$A analysis.py specs/x.toml scan       # 粗扫:每轨频谱图 -> <proj>/scan/,人眼选目标
# ...编辑 specs/x.toml:填 targets(段落/乐句)与 drums...
$A analysis.py specs/x.toml measure    # 深度测量 + 参考截段 -> <proj>/refs/
$S synth.py    specs/x.toml browse M1 "Pads/"   # 自动扫库排名 -> 粘贴候选进 toml
$A analysis.py specs/x.toml drums      # 打点/one-shot/rebuild -> <proj>/drums/
python drummidi.py specs/x.toml        # 量化 -> pattern.mid + grid.txt + grid.html
$S synth.py    specs/x.toml all        # 渲染打分 -> renders/ + scores.json,fxp 进
                                       # lib/surge/<collection>/,并生成 <proj>.rpp
```

`<proj>` = `~/storage/daw/<name>/`(物料与产物,不进 git);fxp 与 scores 进 git。

## browse:备选不再手选

`synth.py <spec> browse <target> [路径过滤 ...]` 用目标乐句的前 4 秒作探针,
把 factory + 3rdparty 全部 ~3000 个 patch 逐个渲染,按
**60 频段谱距离 + centroid 比值 + attack 比值** 的复合距离排名,直接打印
top-24 与五行可粘贴的 candidates。逐 patch 进度缓存在
`<proj>/browse/<target>-scores.json`,中断重跑只补增量;全库约 15–25 分钟,
先用过滤("Pads/"、"Jacky Ligon")做小时级迭代。

## measure 输出的音色特征(对应合成器分区)

| 特征 | 含义 | 拧哪里 |
|---|---|---|
| peaks / f0 / odd_even_db / inharm | 谐波梯子、奇偶比、失谐 | OSC 波形/detune |
| attack_med_ms | 10→90% 起音 | Amp EG |
| centroid_traj(start/mid/end/slope) | 亮度轨迹 | Filter cutoff + EG |
| mod(trem/bright rate+depth) | 0.3–12Hz 幅度/亮度调制 | LFO 速率与深度 |
| stereo(width lo/mid/hi dB)+ lr_corr | 分频段 side/mid 宽度 | unison/chorus/宽度 FX |
| flatness_med | 噪声成分占比 | noise osc / 气声 |

## drummidi:鼓段 -> MIDI/grid

对 `drums/<tag>/pattern.json`(须含 beats;老数据重跑 drums 步骤即可):

- **恒速网格拟合**:beat_track 只做初值,周期 ±3% × 相位全扫、力度加权对齐
  16 分槽,再按 kick 偶拍/snare 奇拍对齐小节线(这批专辑都是恒速编曲,
  拟合后 falien 中位偏差 30ms → 9ms);
- 逐 hit 直/三连音判定(三连音需误差 < 0.6× 直拍才成立);
- `pattern.mid`:3 轨 SMF(tempo / quantized / as-played),GM 鼓映射
  kick36 snare38 hat42 perc39,直接拖进任何 DAW 套鼓机;
- `grid.txt` 文本步进格(velocity 分级 o/O/#)+ `grid.html` 可视化格
  (颜色=类别,透明度=力度,tooltip 有偏差毫秒)。

## 约定与已知边界

- 乐句三种写法:`hold`(和弦长按)、`notes`(逐音 [t, note, vel, dur])、
  `pulses`(节奏泵动),可混用
- 候选基底:`factory:<相对路径>`(自动在 patches_factory / patches_3rdparty 里找)
  或 `lib:<collection>/<名>.fxp`(库自我复用)
- 打分是 60 频段 log 谱距离(render)/复合距离(browse):**复合目标
  (lead 叠 pad)分数仍虚高,以耳朵为准**;自定义 FX 链没法从参数层实例化,
  要 granular/shimmer 就选自带 Nimbus 的基底(fxp 是 XML,可 grep
  `fx._type.*value="22"` 找)
- 鼓分类是 4 类频段启发式(kick/snare/hat/perc),叠打的 layered 采样会
  归到能量占优的一类;grid 上手动改比调分类器快
- venv 搭建与 surgepy 编译坑(CMake4 / GCC16 / 版本匹配)见 gral 侧
  `arch/audio/readme.md` 与本仓库 `tools/endless/README.md`

## 历史

第一轮四个 collection(endless / sega-universe / tev-woods / magdalene,
2026-08-09)由 `tools/<名>/` 下的一次性脚本产出,本框架是它们的第三次重复
后的泛化;specs/ 里的四个 TOML 已把它们全部迁入,一次性脚本仅存档。
2026-08-10:加入深度音色特征、browse 自动选备选、drummidi 鼓 MIDI 化。

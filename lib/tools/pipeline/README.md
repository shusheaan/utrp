# pipeline — 音色复刻管线(共享框架)

一张专辑 = 一个 `specs/<名>.toml`。流程两侧对应两个 venv(见下),模块 DAG:

```
albumspec.py   冻结数据类 + TOML 加载(唯一的配置入口)
spectral.py    纯 numpy 分析函数(两侧共用,无 I/O)
analysis.py    librosa 侧:separate / scan / measure / drums
synth.py       surgepy 侧:render(渲染+打分+fxp 落 lib)/ project(RPP)
rpp.py         REAPER 工程文本生成(纯字符串函数)
```

## 用法(新专辑五步)

```sh
A=~/.cache/timbre-pipeline/venv-analysis/bin/python  # librosa/demucs(Python 3.12)
S=~/.cache/timbre-pipeline/venv-render/bin/python    # surgepy(Python 3.14,须匹配系统 Surge)

$A analysis.py specs/x.toml separate   # demucs -> ~/.cache/demucs-stems(可重建缓存)
$A analysis.py specs/x.toml scan       # 粗扫:每轨频谱图 -> <proj>/scan/,人眼选目标
# ...编辑 specs/x.toml:填 targets(段落/乐句/候选)与 drums...
$A analysis.py specs/x.toml measure    # 测量 + 参考截段 -> <proj>/refs/
$A analysis.py specs/x.toml drums      # 打点/one-shot/rebuild -> <proj>/drums/
$S synth.py    specs/x.toml all        # 渲染打分 -> renders/ + scores.json,fxp 进
                                       # lib/surge/<collection>/,并生成 <proj>/<名>.rpp
```

`<proj>` = `~/storage/daw/<name>/`(物料与产物,不进 git);fxp 与 scores 进 git。

## 约定与已知边界

- 乐句三种写法:`hold`(和弦长按)、`notes`(逐音 [t, note, vel, dur])、
  `pulses`(节奏泵动),可混用
- 候选基底:`factory:<相对路径>`(自动在 patches_factory / patches_3rdparty 里找)
  或 `lib:<collection>/<名>.fxp`(库自我复用)
- 打分是 60 频段 log 谱距离:**复合目标(lead 叠 pad)分数虚高**,以耳朵为准;
  自定义 FX 链没法从参数层实例化,要 granular/shimmer 就选自带 Nimbus 的基底
  (fxp 是 XML,可 grep `fx._type.*value="22"` 找)
- venv 搭建与 surgepy 编译坑(CMake4 / GCC16 / 版本匹配)见 gral 侧
  `arch/audio/readme.md` 与本仓库 `tools/endless/README.md`

## 历史

第一轮四个 collection(endless / sega-universe / tev-woods / magdalene,
2026-08-09)由 `tools/<名>/` 下的一次性脚本产出,本框架是它们的第三次重复
后的泛化;specs/ 里的四个 TOML 已把它们全部迁入,一次性脚本仅存档。

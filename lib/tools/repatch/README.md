# repatch — 听到什么 → 拧出什么(音色逆向原型)

核心需求:一首歌进来,(a)提炼出几个 signature 音色"色块",(b)对每个色块
在**我自己的合成器**上逆向出一个可手调的 patch。市场上没有这个产品
(调研见 `docs/2026-08-10-sound-reverse-engineering-market.md`);
本目录是 neurosymbolic 思路的 v0:**符号半边**(合成器参数空间 = 程序,
在其中做感知距离引导的搜索)先落地,神经半边(学习型嵌入/反演网络)在路线图。

```
palette.py     歌 -> N 个音色色块:分段 -> MFCC+centroid+flatness 特征
               -> k-means -> 每簇 medoid 切片 + 特征卡 + HTML 调色板
               (色相<-亮度重心,饱和<-1-噪声度,明度<-能量,真·声音调色板)
soundmatch.py  本地版 Sonaura Match:全库 patch 预渲染一次建特征索引
               (~/storage/daw/repatch-index/),之后任意目标秒级检索;
               四种加权模式 general/pad/pluck/tone;增量建、断点续
refine.py      目标音频 + 基底 patch -> 参数坐标下降精调 -> 新 .fxp + 试听 wav
reabridge.py   REAPER 桥的 Python 端:item 源文件+时间范围 -> top-K 检索
               -> surgepy 渲染试听 -> TSV 协议给 Lua(见 ../reaper/)
```

REAPER 内一键用法:`lib/link.sh` 布链后,在 REAPER Actions 里加载
`Scripts/utrp/utrp_soundmatch.lua` 并绑键——选中音频 item 一键,候选试听
自动建轨摆好(仅 #1 未静音),听中哪个照轨名去 Surge 浏览器载入。

检索两条路的分工:`soundmatch`(秒级,标准探针,日常首选)与 pipeline
`browse`(慢,按目标乐句渲染,对音高/织体敏感的目标更准)。标准链:
`palette` 选色块 → `soundmatch find` 秒出 top-N → `refine` 精调 → 耳朵定夺。
对照产品 Sonaura Match(sonaura.au,独立开发者的网页版"合成器 Shazam",
~1 万 preset 索引)只做检索层;本目录多出的 refine(参数精调)与
configuration 解释是差异点,详见 docs 市场分析。

## 用法

```sh
A=~/.cache/timbre-pipeline/venv-analysis/bin/python
S=~/.cache/timbre-pipeline/venv-render/bin/python

$A palette.py "<歌>.flac" --k 6              # -> ~/storage/daw/palette/<名>/
$S refine.py target.wav "factory:Pads/X.fxp" out.fxp --notes 38,46,53,60
```

完整逆向链:`palette` 选色块 → 对色块跑 pipeline `browse`(或直接给基底)→
`refine` 精调 → 耳朵定夺 → 手调收尾。首测(MAGDALENE thousand eyes drone,
基底 = 全库 browse 冠军):3 轮扫描距离 11.91 → 7.28(近 39%),主要动作是
Filter Cutoff 合死 + Resonance 79% + Decay 350ms。

## 设计要点与已知边界

- 距离 = 60 频段 log 谱 + centroid 比 + attack 比(与 browse 同源,
  `pipeline/spectral.py` 共享);**分数只用于排序,最终以耳朵为准**;
- refine 白名单默认 8 个高影响参数(`--params` 可换);坐标下降是故意选的
  最笨最稳方案,渲染约 50-100 次、一两分钟出结果;
- palette 对整首混音跑会把人声/鼓混进簇里——先 demucs 分轨再对 stem 跑更准
  (stems 缓存在 `~/.cache/demucs-stems`);
- 输出全进 `~/storage/daw/`(音频物料不进 git),fxp 想收编就手动挪进
  `lib/surge/<collection>/`。

## 路线图(神经半边)

1. 距离升级:CLAP 类对比学习嵌入替代手工谱特征(解决"谱像但律动/质感不像");
2. 搜索升级:CMA-ES / 差分进化替代坐标下降,参数子空间按 patch 拓扑分组;
3. 反演网络:surgepy 免费自监督数据(随机 patch -> 渲染 -> (音频, 参数) 对),
   训练 audio -> 参数初值网络,搜索只做最后一公里——这是商业厂商被 EULA
   卡死、而 Surge 开源生态独有的路;
4. palette 与 refine 缝合成一条命令:歌进,N 个 (色块, 精调 fxp) 对出。

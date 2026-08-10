# 音色逆向工程:市场空白分析

> 2026-08-10。需求定义:听到一首歌 → 快速知道核心音色怎么做的 → 在**自己的**
> 合成器上得到一个接近且可手调的 patch。结论:**这是真实存在但至今没被
> 产品化填上的空白**;原型已落地 `lib/tools/repatch/`。

## 1. 现有产品盘点(2026-08 检索)

| 产品 | 做什么 | 为什么不解决问题 |
|---|---|---|
| **Synplant 2 / Genopatch**(Sonic Charge)| 音频进 → 遗传算法长出 patch,唯一出货的 audio→patch 产品 | 只匹配到**它自家引擎**,不能输出到你的 Surge/Serum;Win/Mac(Linux 需 yabridge)|
| **MicroMusic Replicate** | 音频 → Vital preset 的 AI 小工具 | 实验性,仅 Vital,质量不稳 |
| **FADR SynthGPT** | 文本 prompt → preset/采样,$10/月订阅 | 文本入口不是音频入口,不做逆向 |
| **Tone2 Icarus2** | 内置 resample-to-preset | 同样只进自家引擎 |
| **Sononym / XO / Splice 检索** | 采样相似度搜索 | 找的是**采样**不是可调参数 |
| **Melodyne / RipX / demucs 系** | 音高/和弦/分轨提取 | 解决"弹了什么",不解决"音色怎么拧" |
| **Neutone / RAVE(IRCAM)** | 神经音色迁移 VST | 输出是黑盒神经音频,**不可手调、不可解释** |

学术侧有完整研究线但无产品:InverSynth(CNN 参数反演)、SerumRNN(FX 链
步进编程)、Syntheon(Vital/Dexed 开源反演)、Sound2Synth(DX7)、DiffMoog
(可微分合成器)、Audio Spectrogram Transformer sound matching(2024)、
Neural Proxies for Sound Synthesizers(2025,感知化 preset 表征)。
关键词:automatic synthesizer programming (ASP)。

来源:[MusicRadar/Synplant 2](https://www.musicradar.com/music-tech/is-synplant-2s-new-prompt-based-patch-generator-the-future-of-synthesis) ·
[audiocipher/FADR](https://www.audiocipher.com/post/fadr-synthgpt-synplant) ·
[MicroMusic](https://micromusic.tech/) ·
[KVR Genopatch alternative 讨论](https://www.kvraudio.com/forum/viewtopic.php?t=604148) ·
[0xdevalias 汇总 gist](https://gist.github.com/0xdevalias/5a06349b376d01b2a76ad27a86b08c1b) ·
[AST sound matching (arXiv 2407.16643)](https://arxiv.org/pdf/2407.16643)

## 2. 为什么空白一直没被填(四层原因)

1. **技术**:参数→声音是多对一、强非凸;FX 链/调制/unison 让感知损失函数难做;
   混音里先要分轨,误差级联。一次性"全自动完美复现"做不到,而厂商不敢发布
   "60 分答案"的产品——但 60 分 + 可手调恰恰是制作人要的。
2. **数据与 EULA**:对任意商业合成器(Serum/Diva)做反演,需要海量
   (patch, 渲染) 对——在云端跑别人的 VST 渲染农场违反 EULA。所以只有
   Sonic Charge 给**自家引擎**做了 Genopatch。这是结构性卡点。
3. **市场结构**:买家是愿付 $50–150 买断的制作人,天花板是插件细分
   (~$0.64B)的小生意;合成器厂商自己不做(蚕食 preset 销售与音色设计服务);
   AI 大钱全去了全曲生成(Suno $5.4B),辅助层长期融资不足——见
   `2026-08-10-music-tech-market-map.md` 的杠铃化判断。
4. **工作流**:制作人不信一键结果,要的是**可解释、可继续拧**的起点。这要求
   输出是参数(符号),不是神经音频——比生成音频更难,也正是 Neutone/RAVE
   路线绕开、从而没解决问题的原因。

## 3. 正确的技术形态:neurosymbolic 分析-综合闭环

用户直觉正确。分工:

- **神经半边(感知)**:分轨(demucs)、事件切分、音色嵌入(CLAP 类对比学习
  表征替代手工谱特征)、f0/包络/调制分析 → 把"听感接近"变成可计算距离;
- **符号半边(程序)**:合成器参数空间 = 程序空间。三级火箭:
  ① 全库 preset 检索作先验(我们的 browse);
  ② 参数空间局部搜索精调(坐标下降/CMA-ES,repatch/refine 已落地);
  ③ 反演网络给初值:随机 patch → surgepy 渲染 → (音频, 参数) 自监督对,
    训练 audio→参数网络,搜索只做最后一公里;
- **"调色板"前端**:歌 → 分段聚类 → N 个 signature 色块(repatch/palette
  已落地),每个色块各自走上面的逆向链。

## 4. 我们的独家优势与结论

- **EULA 卡点对我们不存在**:Surge XT 开源 + surgepy 全参数编程访问 =
  免费无限自监督数据 + 闭环渲染评分。商业厂商做不了的路,开源生态可以做,
  而 Surge 方向"任意音频→patch"目前**无人在做**;
- 已有资产直接复用:demucs 缓存、spectral.py 特征、browse 全库粗搜、
  measurements 的"拧哪里"映射;
- 行业需求真实存在的证据:r/synthrecipes 社区、YouTube remake 经济、
  Genopatch 的口碑、preset 市场规模——但都是 prosumer 量级,VC 不进场,
  **适合以个人工具/开源形态做,不适合融资创业**;
- 结论:市面上没有能替代的工具(Genopatch 最接近但引擎封闭),自建成立。
  v0 已在 `lib/tools/repatch/`,首测:browse 冠军基底经 refine 3 轮再拉近
  39%(距离 11.91→7.28)。路线图见其 README。

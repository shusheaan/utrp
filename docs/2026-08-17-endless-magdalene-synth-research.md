# Endless / MAGDALENE 合成器音色推理(第二轮,2026-08-17)

本轮把音色复现覆盖从每张 4 个目标扩到 **Endless 10 个 / MAGDALENE 9 个**:
新增 11 个目标、渲染 33 个候选 + 2 个 refine 精调版,全部 fxp 已进
`lib/surge/endless/` 与 `lib/surge/magdalene/`,A/B 工程已重新生成
(`~/storage/daw/endless-ref/endless-ref.rpp`、`~/storage/daw/magdalene/magdalene.rpp`)。
测量/打分细节表在两个工程的 README「第二轮目标」;本文记录**制作考证、
音色推断与使用方法**。流程说明见 `lib/README.md`(三大支柱)与
`lib/tools/pipeline/README.md`。

## 全专辑级发现

1. **《Endless》整张过了 varispeed 磁带**:新测 6 段的谐波普遍偏 +40 音分
   (bass 段 -50c 同余)。这就是厂库 patch 永远"差一点"的原因。复刻时在
   Surge Scene 级把 pitch 偏 ±40–50c,或渲染后过 tape 插件即可"归位"。
2. **硬件证据链**(详见下文分专辑考证):Endless 键盘音色集中在
   Buddy Ross(Juno-106 / Prophet-6 / ASR-10)、James Blake(Prophet '08)、
   SebastiAn/Vegyn(Logic、EXS24 采样、Korg MS-20、Korg M1);MAGDALENE
   唯一实锤型号是 **twigs 本人的 Dave Smith Tempest**(thousand eyes /
   sad day 有演奏署名),Nicolas Jaar 走 Ableton 重处理,Koreless 走早期
   数字合成器(Roland D-550 / Nord Modular)+ 超长效果链;两处"合唱感"
   是真实采样(保加利亚女声合唱、佛罗里达群众诗班),不是合成。

---

## Frank Ocean《Endless》(2016)

### 制作考证(confirmed,来源见文末)

- 专辑级制作:Frank Ocean + Vegyn + Michael Uzowuru + Troy NōKA;
  mix Tom Elmhirst / Noah Goldstein,master Mike Dean。
  Jon Brion 只在《Blonde》,**不在 Endless**。
- 关键乐手署名:At Your Best = James Blake (synths) + Jonny Greenwood
  弦乐编排 + London Contemporary Orchestra(弦乐是真实乐队,非 string
  machine);Comme des Garçons / In Here Somewhere / Slide on Me /
  Sideways / Florida = Buddy Ross (synths)、Ben Reed (bass);
  Higgs / Rushes To = SebastiAn (programming/synths);
  Mitsubishi Sony = Vegyn (programming);Hublots = 88-Keys(含
  Sherbet "We Ride Tonight" 采样);Unity = Stwo + Frank Dukes 联合制作。
- 型号实锤(经《Blonde》交叉证实的同班底 palette):Buddy Ross —
  Roland Juno-106(White Ferrari pad 出处)、DSI Prophet-6、Ensoniq
  ASR-10;James Blake — DSI Prophet '08(终身主力);Vegyn 自报 —
  Korg MS-20、Korg M1、Logic EXS24、GarageBand/Logic 预置。
- 工作法证词:Buddy Ross 称 Frank 是 "collage artist","我们都是他寄出
  去加工的碎片";大量素材源自巡演 soundcheck 即兴。SebastiAn 的已知手法
  是几乎不用合成器、以 vinyl 采样 + 重压缩/失真/bitcrush 为主。
- Reverb Machine 对 "Sideways" 的逐层拆解(复刻分析级):双层锯齿波 pad
  (相隔八度、每振荡器 5 unison voices)+ 8-bit/7kHz bitcrush + Soundtoys
  Crystallizer 式 +2 octave reverse shimmer;bass 为 Minimoog 类音色。

### 新目标推断与用法(候选按渲染打分排序,粗体 = 最佳)

| 目标 | 原声推断 | 候选 | 用法要点 |
|---|---|---|---|
| E Alabama keys 0:20–1:00 | 无键盘署名,likely Frank 自弹暖 EP/synth;Gm11,1.5Hz 深 tremolo(0.16),质心 808Hz,+40c | **E3-analogmagic (13.2)**、E3b-analogmagic-tuned(refine 版)、E2-dxep、E1-suitcase | D3–Bb4 区弹 Gm11 长按;补 1.5Hz tremolo;全局 +40c |
| F Unity keys stab 0:08–0:48 | house 键 stab(Stwo/Frank Dukes);B/E/F#/A 堆叠(+30~45c),1.2Hz trem | **F3-tekstab (11.1)**、F2-dxep、F1-houseorgan | 八分音符 stab,release 0.35s,B3–B4 区 |
| G CDG bass 0:15–0:55 | Ben Reed 电贝斯 + Ross synth 叠层;A#2 基频 -50c、圆 sub(质心 243Hz)、滑音起音 ~340ms、近 mono | **G3-bassguitar4 (11.7)** 指弹感、G1-electronic (12.1) 纯合成感、G2-bass5 | A#1–C#2 单音线;两种质感二选一或叠层 |
| H In Here Somewhere pad 0:40–1:40 | NōKA + Ross synths;F1 亚低音 + Ab/Cm 宽幅氛围墙,attack 640ms | **H1-lighthouse (7.6,库内最佳)**、H3-journey、H2-distant | F1 低音 + Ab 堆叠长按,attack 0.6s,大混响 |
| J Florida pad 0:10–1:00 | pad 无署名(Ross 仅 bass);F# add9 雾化,L/R 完全去相关 (0.05),attack 740ms | **J1-hauntology (8.3)**、J2-manaquest(+drift 45%)、J3-mks70 | F#2 起 add9 长按;宽度拉满、drift 45% |
| K Higgs riff 0:30–1:30 | SebastiAn programming;organ 声疑似采样/rompler;Cmaj7 系脉冲,1Hz 明暗调制 | **K3-hybridpluck (9.2)**、K2-jupiter8 (9.5,更模拟)、K1-houseorgan | Cmaj7 四分脉冲;K3/K2 几乎并列,全听后定 |

第一轮 4 目标(A At Your Best pad / B Mitsubushi saw chords / C Impietas
drone / D Hublots keys)见 `~/storage/daw/endless-ref/README.md`。

---

## FKA twigs《MAGDALENE》(2019)

### 制作考证(confirmed)

- 逐曲 producers:thousand eyes / fallen alien = twigs + Nicolas Jaar;
  home with you = twigs + Jaar(Ethan P. Flynn 钢琴/单簧管);
  sad day = twigs + benny blanco + Jaar + Skrillex + **Koreless**(synth
  strings 署名)+ Cashmere Cat;mary magdalene = twigs + blanco + Jaar +
  Koreless + Cashmere Cat;holy terrain = twigs + Jack Antonoff +
  Skrillex + Sounwave + Koreless + Kenny Beats(**Arca: vocal
  processing + synth programming**);mirrored heart = twigs + Koreless
  (**Rick Nowels: synths**,少有人注意的实锤);daybed = **Daniel
  Lopatin** 唯一 producer;cellophane = twigs + Jeff Kleinman(钢琴 +
  synths)+ Michael Uzowuru。
- 型号实锤:**Dave Smith Tempest**——twigs 在 thousand eyes 与 sad day
  上有演奏署名,自述 "if it wasn't for the Tempest, I wouldn't have
  started producing my own music";Koreless 佐证她大量用 Tempest 生成
  素材。写作链:TC-Helicon 人声处理器(边唱边变声)。
- 采样实锤:holy terrain 采样保加利亚女声合唱 "Moma Hubava";fallen
  alien 采样 Florida Mass Choir "Storm Clouds Rising"。
- palette 推断:Jaar — Ableton Live 为核心乐器、Absynth 5、modular、
  重 resample/pitch/reverb 处理("thousand eyes" 的 choral drone 最可能
  是 twigs 人声堆叠 + Jaar 重处理);Koreless — Nord Modular、SH-101、
  Model D、Matrix 1000、Roland D-550,"really long crazy effect
  chains",GRM Tools / Soundmagic Spectral;Lopatin — Juno-60、
  Microwave XT、u-he Zebra、iZotope Iris、Omnisphere choir("daybed"
  雾状 pad 的仅有线索)。

### 新目标推断与用法

| 目标 | 原声推断 | 候选 | 用法要点 |
|---|---|---|---|
| M5 sad day 副歌 wash 1:40–2:20 | Koreless synth strings + Tempest 素材;Ab 大调阶梯,attack ~790ms,亮度缓慢爬升 | **M5c-deepnote (8.8,THX 式簇群滑移,意外贴合)**、M5b-stringmachine、M5a-choirpad | Ab 堆叠(G#2–G4)长按,attack 0.7s |
| M6 mary magdalene outro arp 4:05–4:50 | Jaar;金属质感密集琶音,A/C#m 家族,亮度递降 | **M6a-metallicarp (6.1,两轮全场最佳)**、M6c-brainout、M6b-hybridpluck | 16 分琶音 C#3/A3/C#4/E4/G#4;M6a 基本即插即用 |
| M7 cellophane warped 钢琴 0:10–0:50 | Kleinman 真钢琴 + 大幅处理;质心 668Hz 暗,0.9Hz 晃动(tape wow 感,社区"varispeed"说仅为听感) | **M7c-pianobass (8.4)**、M7a-suitcase、M7b-dxep(全带 Osc Drift) | Bm/G 散拍分解和弦;drift 30–40% 是灵魂,加 pitch 慢 LFO 更像 |
| M8 mary magdalene grinding bass 1:40–2:40 | F#1 基频 -35c、失真谐波上探 3kHz、attack 122ms、纯 mono(第一轮 README 标注"想做"的目标,已完成) | **M8c-lowproblems (12.8)**、M8d-lowproblems-tuned(refine 版)、M8a-doomsday、M8b-808er | F#1 半拍脉冲;后级再推一层失真更贴 |
| M9 sad day 玻璃 lead 3:20–4:05 | Koreless 早期数字合成器 + 长效果链;人声-合成器中间态,质心 1836Hz | **M9c-nova (8.4)**、M9b-giallo (9.2)、M9a-cloudhorn (9.2,三者接近,务必全听) | Bb4–F5 旋律区,配 pitch bend;叠在 M5 wash 上还原段落 |

第一轮 4 目标(M1 thousand eyes drone / M2 home with you wash /
M3 daybed haze / M4 fallen alien stab)见 `~/storage/daw/magdalene/README.md`。

---

## 怎么用(三步)

1. `reaper ~/storage/daw/endless-ref/endless-ref.rpp`(或
   `magdalene/magdalene.rpp`):每组先听 `REF mix`,再逐个 unmute 候选轨
   A/B;轨名里 `d=` 是谱距离,`*BEST*` 是自动第一名。
2. 听中的 patch 在 Surge XT 浏览器 `User/utrp/endless|magdalene/` 载入;
   `SURGE LIVE` 轨的 MIDI 乐句就是测出的原曲和弦/音区,可直接弹。
3. 差一点就说形容词(太亮/太闷/太窄/少晃动/少磁带感),agent 翻译成
   tweaks 重渲染或跑 refine;Endless 记得全局 ±40–50c。

## 边界与待办

- refine 精调版(E3b/M8d)在 refine 探针上近了 15–22%,但在 render 打分
  下与 tweaks 原版打平(两种探针度量不同)——两版都保留,耳朵终审。
- MAGDALENE 缺 `04 holy terrain` 与 `07 mirrored heart` 音源;补齐后可
  一小时内覆盖(Arca vocal synth 处理、Rick Nowels synths)。
- M5/M9 的 stem 有人声渗入(twigs 美学本身),候选只逼近器乐部分。
- 尚未做:thousand eyes 3:05 下坠 glissando(pitch env 特效)。
- Reddit/Gearspace 反爬(403),社区共识以 Reverb Machine / KVR / 乐评
  替代,是本次考证的主要证据缺口。

## Sources

Endless: [Wikipedia](https://en.wikipedia.org/wiki/Endless_(Frank_Ocean_album)) ·
[Reverb Machine: Frank Ocean Synth Sounds Pt.2](https://reverbmachine.com/blog/frank-ocean-synth-sounds/) ·
[Reverb Machine: Channel Orange](https://reverbmachine.com/blog/frank-ocean-channel-orange-synth-sounds/) ·
[FADER × Buddy Ross](https://www.thefader.com/2016/08/31/frank-ocean-buddy-ross-blond-endless) ·
[blonded.blog Buddy Ross](https://blonded.blog/news/buddy-ross-talks-about-his-collaborative-history-with-frank) ·
[FADER × Vegyn](https://www.thefader.com/2017/03/03/vegyn-frank-ocean-blonded-interview-plz-make-it-ruins) ·
[Equipboard Vegyn](https://equipboard.com/albums/vegyn-only-diamonds-cut-diamonds) ·
[Billboard credits](https://www.billboard.com/music/music-news/frank-ocean-endless-credits-james-blake-radiohead-jonny-greenwood-7476977/) ·
[MusicRadar James Blake](https://www.musicradar.com/news/james-blake-synths-new-album) ·
[Reverb Machine James Blake](https://reverbmachine.com/blog/james-blake-synth-sounds/) ·
[KVR SebastiAn](https://www.kvraudio.com/forum/viewtopic.php?t=181782)

MAGDALENE: [Wikipedia](https://en.wikipedia.org/wiki/Magdalene_(album)) ·
[SoS Inside Track: Eusexua(Koreless/twigs 手法)](https://www.soundonsound.com/techniques/inside-track-fka-twigs-eusexua) ·
[The Current 访谈](https://www.thecurrent.org/feature/2019/11/23/interview-fka-twigs-magdalene-prince) ·
[KEXP 访谈](https://www.kexp.org/read/2019/11/27/fka-twigs-magdalene-interview/) ·
[i-D 封面故事](https://i-d.co/article/fka-twigs-interview-magdalene-new-album/) ·
[Equipboard FKA twigs(Tempest)](https://equipboard.com/pros/fka-twigs) ·
[MusicRadar OPN](https://www.musicradar.com/news/oneohtrix-point-never-drums-synths) ·
[Ableton × Jaar](https://www.ableton.com/en/blog/nicolas-jaar/) ·
[Wikipedia Sad Day](https://en.wikipedia.org/wiki/Sad_Day_(FKA_Twigs_song)) ·
[Wikipedia Cellophane](https://en.wikipedia.org/wiki/Cellophane_(FKA_Twigs_song))

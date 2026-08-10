# harmony — 电脑键盘上的和弦进行探索器

把 Rust utrp(theory: tone/key/chord + inversions)的思路搬到素材库这边:
选定调与调式后,**七个字母键 = 七个级数的七和弦**,不用弹全部音,单键触发
整个 voicing,用耳朵快速横向对比不同 voicing / 调式 / 借用和弦 / 副属和弦。
声音直接走 surgepy 加载 `lib/surge/` 里的 patch——探索和声时听到的就是
成品音色,不是钢琴 GM 音。

```
theory.py       纯函数:调式表、级数七和弦、voicing 应用(无 I/O;explore 专用)
voicings.toml   voicing 预设库(piano + guitar;可追加 voicings.local.toml)
explore.py      交互键盘 + demo 批量渲染;surgepy 渲染缓存 + paplay 出声
perform.py      simulation 表演层:session.yaml -> utrp-sim -> pad+点缀 -> 声音/MIDI
session.yaml    一次作曲会话的全部参数(复制改名即新会话)
test_theory.py  理论不变量;test_perform.py 点缀引擎 + utrp-sim 输出契约
progressions/   导出的进行(JSON,文本进 git;.mid/.wav 落 ~/storage/daw/harmony)
../simulate/    Rust 胶水 crate:#[path] 原样编译 ../../src/theory(见其 README)
```

## 用法

```sh
P=~/.cache/timbre-pipeline/venv-render/bin/python   # 要 surgepy,同渲染侧 venv

$P explore.py                          # 全库 patch 里探索(p 键切换)
$P explore.py magdalene/M1b-ghostpad.fxp endless/C1-ghostpad.fxp   # 指定 patch

# 无终端/写死进行时:demo 一次渲染整条进行 -> wav + mid + json
$P explore.py demo F ionian magdalene/M1b-ghostpad.fxp \
    2/drop2 5/rootless-b 1maj7/pad-wide b6maj7/close
```

### 键位

| 键 | 作用 |
|---|---|
| `a s d f g h j` | 级数 1–7 的顺阶七和弦(当前调式决定 quality) |
| `A S D F G H J` | 副属:V7/该级 |
| `v` / `V` | 下/上一个 voicing(同一和弦立即重听) |
| `b` | voicing 家族:piano → guitar → all |
| `m` | 换调式(七调式 + 和声/旋律小调) |
| `k` / `K` | 移调 ±1 半音;`[` `]` 八度 |
| `p` / `P` | 换 patch(lib/surge 全库) |
| `space` | 重放上一个和弦 |
| `r` / `c` / `x` | 录进行 / 清空 / 导出(JSON+MID,导出时命名) |

### demo token 语法

`[b|#]<级数>[quality][/voicing]`,如 `2/drop2`、`5maj7/g-barre`、
`b6maj7/close`(降级数 = 借用,quality 缺省 maj7)。

## simulate + perform:原版 Rust simulation 的声音化

意识流作曲的探索链,**Rust 逻辑一行未改未复制**(机制见 `../simulate/README.md`):

```
session.yaml ──sim段──> utrp-sim(原版 theory:40 步 ss 序列 + DeTour 绕行
                         + 转位采样 + via-tonic/共享和弦/dim7/back 转调)
       │                      │ JSON(逐小节:调、和弦、MIDI 音、音阶)
       │ perform/ornament 段  v
       └──────────> perform.py:pad 长音(strum/交叠糊边)
                      + 点缀层(euclidean 时钟 x Turing 机移位寄存器,
                        量化到当前和弦/音阶,modular 生成器思路)
                      ==> 双 Surge 实例连续流(paplay 实时 / --wav 离线)
                      ==> <name>.mid(pad + ornament 两轨,进 DAW 改)
                          + progressions/<name>.json(文字日志)
```

```sh
cargo build --release --manifest-path ../simulate/Cargo.toml   # 一次
$P perform.py session.yaml           # 实时播放,Ctrl-C 停
$P perform.py session.yaml --wav     # 离线渲染整段(2-3 分钟)验听
```

点缀层的随机性三层可调(session.yaml `ornament` 段):euclid 决定"哪里可能
响"(节奏骨架),density 决定"真的响不响"(呼吸),turing.mutate 决定
"旋律变不变"(0 = 死循环,1 = 纯随机,0.1–0.2 = 缓慢演化)。和声层随机性
在原版 Rust 里(thread_rng),每次 simulate 都是新即兴,不可复现是特性。

## voicing 库约定

`pattern = [[度数, 八度偏移], ...]` 从低到高;度数 1/3/5/7 按 quality 查表,
9/11/13 是固定张力(14/17/21 半音)。`qualities` 限定适用和弦(`"*"` 通用)。
每个和弦当前约 12(piano)+ 8(guitar)个预设;试出来喜欢的新写法直接
append——**不改既有条目,名字即 ID**(progressions JSON 里引用的是名字)。

## 设计边界

- 渲染非实时:每个 (patch, 和弦) 首次约 0.2s 渲染后进
  `~/storage/daw/harmony/cache/`,重复触发即时;换 voicing 对比是主要动作,
  全部命中缓存。
- 想要真实时可以后接 MIDI 直通宿主(见 lib/README 路线图),但探索场景下
  缓存方案零依赖、且听到的就是渲染管线同款声音。
- 吉他 voicing 是音高层面的(drop2/drop3/shell 本来就来自吉他把位),
  不建模指板可弹性;要指板图回 Rust utrp。

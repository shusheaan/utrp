# simulate — utrp 原版 Rust theory 的 headless 胶水

**不改不复制原代码**:`src/main.rs` 用 `#[path = "../../../../src/theory/mod.rs"]`
把仓库根部 Rust TUI 的 theory 源码(tone/key/chord/modulation)原样编译进本
crate,唯一的桥接是一个两行的 `app::Difficulty` shim(theory 引用的唯一外部
符号)。本 crate 自己只写 driver:照 `app.rs` 的 `Iterator::next` +
`App::modulate` 调度语义逐小节推进,每个音乐决策(选调、级数和弦、转位采样、
DeTour、四种转调)都调用原函数,输出 JSON 到 stdout。

```sh
cargo build --release            # 一次;依赖是 utrp 本体依赖的子集
./target/release/utrp-sim --measures 20 --key F --mode aeolian \
    --threshold 4 --difficulty piano --base 48
```

输出:每小节 `{measure, key, modulation, degree, scale(pc), chords[{role:
pivot|approach|target, symbol, notes(MIDI 升序堆叠)}]}`。消费者是
`../harmony/perform.py`(YAML 参数 → 本二进制 → pad + 点缀 → 声音/MIDI)。

## 随机性与种子复现

原代码内部全部走 `rand::thread_rng()`(TUI 同款),源码层无法传种子。复现
通过 `shim/seedrandom.c` 实现:`LD_PRELOAD` 拦截 `getrandom()/getentropy()/
syscall(SYS_getrandom)`,设了 `UTRP_SIM_SEED` 就喂 splitmix64 确定字节流,
`thread_rng` 在不知情的情况下变成确定性的——**Rust 仍零改动**。未设环境
变量时垫片直通系统随机,行为与原版一致。

```sh
gcc -shared -fPIC -O2 -o shim/libseedrandom.so shim/seedrandom.c -ldl  # 一次
UTRP_SIM_SEED=42 LD_PRELOAD=$PWD/shim/libseedrandom.so ./target/release/utrp-sim ...
```

perform.py 会在 `sim.seed` 非空时自动挂垫片;同种子逐字节一致(有测试)。
注意跨机器/升级 rand 版本后种子流会变,长期保真靠 `--replay`(每次 sim 的
原始 JSON 自动存 progressions/,回放不再经过随机)。

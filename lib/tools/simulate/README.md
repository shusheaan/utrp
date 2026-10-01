# simulate — shared utrp headless entry

薄适配器，通过 path dependency 调用根 package 的 `utrp::simulator`。
**不再通过 `#[path]` 编译旧 theory，不再复制 TUI driver，不需要 LD_PRELOAD。**

```sh
cargo build --release --manifest-path lib/tools/simulate/Cargo.toml
lib/tools/simulate/target/release/utrp-sim --events 24 --seed 42
lib/tools/simulate/target/release/utrp-sim --measures 24 --key F --mode aeolian --difficulty piano --base 48
```

命令从仓库根运行；在本目录可直接 `cargo build --release`。

- `--events` / `--measures`：实际和弦事件数，bridge 也占一项；不再是旧版一项包含多个经过和弦。
- `--seed` 或 `UTRP_SIM_SEED`：原生 ChaCha8 seed；未给时随机。
- `--key` / `--mode`：限制整局候选池，不只是设置初始调；两者都指定时固定该调/mode。
- `--threshold`：转调前最少完整段数；默认原闭环还必须走完才能转调，不是旧版 iteration。
- 默认为十二主音 × 大 / 小调，原 40 项闭环为底座；开启副属 / 替代 / SD25 / SSD25 接近链，ambient / 借用关闭。每个接近和弦单独占一个事件；指板区域停留由 `guitar.phrases_per_region` 控制。
- `--config` / `--templates`：同 TUI 的 TOML 配置。
- 默认导出 piano notes；`--difficulty guitar` 或 `--instrument guitar` 导出真实指板音高，无解时明确 `notes=[]`。

JSON 向旧 perform 保留 `measure/key/modulation/degree/scale/chords`；一条记录只有一个 `role=target` chord，真实作用见 `kind`。增加 `root_pc` 与完整 `event`，不再从最低音猜根音。旧导出 JSON 仍可 replay，但 `chord+9` 必须有明确 `root_pc`，旧数据缺失则报错要求迁移。

`shim/` 留作历史文件，不再作为构建或测试前提。随机序列与旧版不相同；长期回放保留导出 JSON。同版本、配置与 seed 的 TUI/headless 音乐事件和吉他目标一致。

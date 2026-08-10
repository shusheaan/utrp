# endless 特例脚本 + 提取数据

对应物料层在 `~/storage/daw/endless-ref/`(stem、渲染、REAPER 工程,不进 git)。

通用流程(粗扫/测量/渲染打分/鼓提取/RPP 生成)已泛化进 `../pipeline/`
(spec = `../pipeline/specs/endless.toml`),原一次性脚本经字节级对等验证后删除
(2026-08-09,git 历史可回溯)。留下的是 pipeline 未覆盖的特例:

- `analyze_mitsu.py` 节拍/bass/和弦骨架提取(产出 `data/mitsu-skeleton.json`)
- `remake.py` Mitsubushi Sony remake + sketch 生成(`mitsu-remake.rpp` 唯一来源)
- `compare.py` 候选与参考的频段对比图诊断

运行时环境(venv/surgepy 编译)见 gral 侧 `arch/audio/readme.md`「音色管线运行时」。

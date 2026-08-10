# endless 分析/渲染管线(源码层)

对应物料层在 `~/storage/daw/endless-ref/`(stem、渲染、REAPER 工程,不进 git)。

- `scan.py` 全专辑频谱粗扫 → `measure.py` 目标段测量 → `render.py` surgepy
  批量渲染候选 + 频谱距离打分 → `compare.py` 频段对比图 → `make_rpp.py` A/B 工程
- `drums.py` 鼓 stem 打点/分类/one-shot 切取 → `make_drums_rpp.py` 鼓工程
- `analyze_mitsu.py` 节拍/bass/和弦骨架提取 → `remake.py` remake + sketch

依赖(当前耦合会话环境,泛化待做):Python venv(librosa/demucs 走 3.12,
渲染走 3.14)+ surgepy(需从源码编译且**版本必须匹配系统 Surge XT 插件**;
CMake 4 加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`,GCC 16 加
`-DSURGE_SKIP_WERROR=TRUE`);路径常量指向本机 storage 与 scratchpad。

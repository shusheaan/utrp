# Chord Lab 内嵌引擎

[English](README.md) · [当前 CLAP 产品](../chordlab_clap/README.cn.md)

本目录是**当前 CLAP 的和声与绘图引擎源码**，不是可安装的旧 JSFX 产品。
旧 Lua/VKB 启动器、键位文件、安装器已按用户要求删除，不应再安装到 REAPER Effects。

八个 EEL/JSFX 文件、谱号图片及许可证、主题配置是当前 CLAP 的依赖，必须保留。
`generate_theme.py` 校验 `theme.toml` 并生成 `theme.jsfx-inc`；为了保持内嵌资源逐字节
一致，保留历史生成头注释。修改运行时资源后需重建 CLAP。
当前电脑键位配置位于 `../chordlab_clap/keyboard-map.txt`。

`tests/` 只保留主题验证和音乐核心参考夹具。隔离测试可以暂存原生 JSFX 实例作为
回归基准，但这不代表维护第二个产品，也不是日常使用入口。

```sh
python -m pytest lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/library -q
```

`guitar.toml` / `generate_guitar.py` 编译保守吉他指型表；音频线程只查表。
[双模式和新键位](../chordlab_clap/GUITAR_VOICING.cn.md)。

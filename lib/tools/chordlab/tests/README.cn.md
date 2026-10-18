# 内嵌引擎验证

[English](README.md) · [当前产品](../../chordlab_clap/README.cn.md)

执行 `python -m pytest lib/tools/chordlab/tests lib/tools/chordlab_clap lib/tools/library -q`。
主题测试检查生成资源一致性和无效配置边界；Library 生命周期 mock 检查当前 CLAP 路线。

本目录 Lua/JSFX probe 是隔离临时工程里的音乐核心参考夹具，不安装到用户配置。
宿主验收使用当前 CLAP 的 `stage_port.py`、`ab_test.lua`、`state_ab.lua`、
`parameter_ab.lua` 与混合输入测试。旧安装器、VKB 映射和 Lua 会话测试已随旧产品删除；
历史测试数量不代表当前测试集，最新结果见 CLAP 退役清理报告。

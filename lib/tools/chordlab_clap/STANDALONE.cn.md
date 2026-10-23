# 独立运行和 Library 音色列表

[English](STANDALONE.md) · [游戏模式](GAME.cn.md)

## 当前范围：暂停独立版，先打磨 Bitwig

用户最新决定：**暂不开发独立版，只打磨 Bitwig 内的插件。** 不新增音色菜单或 Library 选轨桥接。

未来若恢复独立版，期望使用 Bitwig 最后保存的钢琴与吉他音色；换音色仍在 Bitwig 内完成。恢复第三方插件状态及 Bitwig 原生设备兼容性仍需单独验证，不能承诺直接加载全部 Bitwig 音色。以下目录准备与早期计划保留为历史记录，未完成项不是当前执行范围。

## 历史实际状态 — 2026-10-22

用户要求不用 Bitwig 也能用当前钢琴、吉他效果、实体 MIDI、电脑键盘和游戏；在插件内按原有分组选择 Library 音色。不新增系统服务。

**尚未完成独立音频宿主或插件内音色选择 UI。** 当前 JUCE Standalone 实际在 Bitwig 关闭时启动过，能打开 Chord Lab，且系统把其输出端点连接到 Spark GO；但它没有加载钢琴或吉他效果器，没有可用音色播放链。端点存在不等于能发声。Sway 默认将普通应用平铺成全屏，还需要独立应用自己的默认窗口策略；本次只临时 floating 检查，没有写新桌面规则。测试配置在 `target/chordlab-live-game/standalone-home/`，没有覆盖用户配置；测试后关闭它，重新打开 Library。

## 已完成的音色目录准备

用 Bitwig 原生 Export DAWproject 导出当前 Library，未用旧迁移文件假冒实时状态：

```sh
python lib/tools/bitwig_library/catalog.py \
  target/chordlab-live-game/library-current.dawproject \
  target/chordlab-live-game/sound-catalog.json
```

- 102 个条目：98 个 MIDI 音色、4 个吉他效果；8 个原有分组不变。
- 当前激活：`Basic Keys / 02 Soft Piano`，`Ambient Guitar / AG - 01 Glass Air`。
- 保留声部及输出 bus/master 的设备顺序、音量、pan、mute、预设 ZIP 路径与 SHA-256。不会提取任意 ZIP 路径、运行插件或改变轨道。输出独占创建，避免覆盖已有文件。
- 明确记录 Bitwig 原生设备依赖：Basic Keys 的 6 个音色共有原生 Reverb，`C2-distant` 使用原生 Tool。它们不能被第三方插件宿主直接加载；不得忽略后声称声音完全一致。
- 清单范围是 **Library controller 管理的音色**，不是扫描 Bitwig 全局浏览器。`playback_verified=false`，目录成功不是独立播放验收。
- `catalog.py` 新增 17 项测试；无缓存 `mypy --strict` 通过。

## 历史实现与验收计划（暂停；音色菜单方案已取消）

- [x] 从当前工程读取音色、分组、当前选择及原生依赖。
- [ ] 独立应用内置轻量音频宿主，先加载当前 sfizz Soft Piano；再加载原格式 CLAP 音源及吉他效果链。保留预设状态、资源路径和电平。缺插件、采样或不支持设备要明确报错，不悄悄换音色。
- [ ] 复用游戏/正常模式引擎。实体 MIDI → Chord Lab → 钢琴；吉他 dry input → Guitar Frontend → ch15 判定，另一支 → 吉他 FX → 输出。演示 ch16 只送钢琴，不能回灌判定。电脑键盘在游戏中需要单音/八度映射，不能恢复自动和弦作弊。
- [ ] 顶部增加收纳式“音色”入口：两个独立选择器“钢琴 / 吉他”，列表按原组展示，显示当前选择和兼容状态；游戏侧栏仍只由 G 控制。设置页手动选择输入、输出及 MIDI 设备，保存上次选择。音色切换安全清音，不重置游戏，不改变另一组。
- [ ] Bitwig 内的同一选择 UI 通过现有 Library controller 的显式桥接操作轨道；不能仅改下拉标签。只允许 Library，共享 Chord Lab 不因换音色被关闭，不修改其他工程或自动 Arm。不新建后台服务。
- [ ] 两种运行模式分别验收 MIDI、电脑键盘、Spark 输入、两方独立计分、超时演示、切音色、缺设备、重启恢复、全部开合及原功能回归。Bitwig 原生 FX 的替代方案要明确告知用户后决定，不能将替代音效标成原样复用。

源状态/采样留在本机 Storage 或忽略的 `target/`，不把用户音色二进制提交到 Git。

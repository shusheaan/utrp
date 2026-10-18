# 音色库：CLAP 单版本迁移

[English](CLAP_MIGRATION.md)

## 日常使用

- 打开 `~/storage/daw/synth.rpp`；启动入口仍为 `Start library.lua`。
- 唯一公共输入轨为 **CHORD LAB CLAP - shared MIDI input**，Input FX 只含
  `org.utrp.chordlab`；实体 MIDI 设备在这条轨设置。选音色不会复制和弦插件。
- 鼠标选音色轨，Library controller 只负责切换 MIDI send、Solo、音源上线/离线
  和编辑器。95 个音色共享调性、力度与七个音级的和弦记忆；一次只试听一个音色。
- 电脑键盘：点击 Chord Lab 内容，看到 **Keyboard** 绿色且编辑器有焦点 后使用。
  Z/X/C/A/S/D/F、Tab、Esc、左 Ctrl、Space、左 Shift 均由 CLAP 接管（详见 [当前键位](../chordlab_clap/README.cn.md)）；不再使用 REAPER 全局 Tab 脚本。
- 实体 MIDI 不需要 CLAP 编辑器焦点；关闭编辑器仍可弹琴。MIDI channels 1–15
  透传原力度，channel 16 仍保留给内部控制协议。
- 不再自动打开旧 VKB，不再启动 `Chord Lab mode.lua`。`Open Chord Lab.lua`
  现在只打开已有 CLAP，不会插入 JSFX。切去音源调参后，回来点一下 CLAP 再用电脑键盘。
- 调整总体音量用 Master，单个音色用对应轨道推子。既有音色、音量与基础键盘组混响
  不属于这次替换范围。音色轨不要额外直接监听同一 MIDI 设备，以免双重发音。
- 这是音色试听库，不是多轨编曲模板。当前录音仍录在唯一 armed 的公共输入轨上；
  正式分轨制作需要另行设置目标轨路由，不能把当前独占试听等同于多轨同时录音。

## 单产品维护

以后只发布和修改 CLAP 行为，不要求原生 JSFX 产品同步。EEL 音乐/绘图源码目前
仍位于 `../chordlab/`，由构建打包到 CLAP 内部；修改源码后须重新构建并部署 `.clap`。
旧 Lua/VKB 流程、旧 A/B 证据与回滚工程保留为历史材料，不会在日常工程启动。
Library Lua 只是 REAPER 选轨/窗口适配，不再负责键盘和和弦算法。

## 迁移与保护

- 替换前备份 `synth.rpp`、REAPER 配置与旧脚本到 `~/storage/daw/Backups/synth-pre-clap-*`。
- `migrate_state.py` 一次性导入原 JSFX v2 七音级记忆，拒绝重复/无效源状态；
  保留调性、音级、类型、转位、音区、力度及 Enabled。清除临时持音、命令和 Sustain。
- 在宿主内核对 normalized 参数和序列化记忆后才删除旧 JSFX。
  CLAP 的 REAPER 参数 API 使用 normalized 范围，不直接照搬 JSFX 的原始整数命令。
- 93 个 Surge 实例的 editor-only 缩放统一为 125%，音色引擎 XML 与波表不变。
- 临时 `Core.RPP` 在迁移验收后删除；正式工程仍为原来的 `synth.rpp`。

## 验收方式

`clap_audit.lua` 使用临时测试 MIDI 输入（不是旧版 Chord Lab），Master 静音，
遍历全部音色：和弦控制协议与普通 MIDI Note 分别触发并测量轨道电平；验证仅一个
在线音源、一个 Solo、一个 armed 输入及一个音源浮窗，且旧 VKB 保持关闭。
退出时移除测试输入，恢复和弦 state、Master 音量及原选轨。运行时不要切工程或保存。
这项测试不等于物理琴键或每一种音色的主观听感验收；电脑键盘还需真实焦点按键测试。

本轮具体统计与证据见 `target/synth-clap-migration/`；旧 `VALIDATION.md` 是历史记录。

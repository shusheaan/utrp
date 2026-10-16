# Chord Lab：改动范围与维护边界

## 三层分离

| 层 | 唯一维护位置 | 保存什么 |
|---|---|---|
| 工具源码 | `~/work/utrp/lib/tools/chordlab/` | 和声／MIDI／绘图／宿主会话／测试 |
| 公共音色 | `~/work/utrp/lib/surge/<album>/*.fxp` | 可复用 Surge 音色，包含 XML 参数及可能的 wavetable |
| 工作工程与媒体 | `~/storage/daw/` | `synth.rpp`、历史工程、录音、MIDI、渲染、采样 |

`../library/` 只负责音色库工程的迁移与单在线试听路由；不复制 Chord Lab 计算代码。
单击音色轨自动显示当前 Surge、共享 Chord Lab、原生虚拟键盘；此行为属于 Library mode，
不在 JSFX 内实现，不给每条音色轨重复添加输入 FX。
历史 `tools/harmony` 与 `pipeline` 不接入这个实时会话，不应为本工具改动它们。

## 本次工具做了什么

- 一个小型 JSFX：十二调、顺阶 3／7／9 和弦、K/L 移动声部、分号保存、Enter 中央 C 附近默认。
- 按住发声、松开发送 Note Off；每个音级的 voicing 状态随 RPP 保存。
- 同一输入合并电脑和实体 MIDI，保留同音持有关系；实体通道 1–15、电脑控制通道 16。
- 一个浮窗统一显示谱表 C2–C6、钢琴 D2–D6、吉他空弦到 17 品。
- 调号／临时变化音、按调性拼写、和弦角色配色；三个视图均为固定大小圆点，不发声浅色，发声深色；调外音灰色。
- 谱线两遍绘制：先线后圆点，防止加线覆盖已画音符。
- 中性灰主题、两行无缝方形按钮、简短英文操作说明；没有额外控制面板。

## 本机影响，必须知道

1. `~/.config/REAPER/Effects/ChordLab/` 是运行文件的 symlink，不是第二份源码。
2. `~/.config/REAPER/Scripts/ChordLab/` 是四个 Lua action 的 symlink。
3. 安装器全局改变 REAPER 的 `reaper-vkbmap.txt` 和 VKB channel / centre / arrow 设置；
   首次备份在 `~/.config/REAPER/chordlab-backup/`。普通 VKB 演奏映射因此不再是默认布局。
4. action 注册在 `reaper-kb.ini`；RPP 本身不携带 action 安装，也不自动启动 Lua。
5. Sway 窗口规则属于 `~/work/gral/arch/sway/config`：主窗在 workspace 2 平铺，其他窗浮动。
   Chord Lab 与 Surge 初始位置左右错开，见 `../library/README.md`；不限制手动拖动。
   REAPER `reaper.ini` 的 `dockheight=280` 留出底部混音台。
6. Surge zoom／默认浏览目录属于用户 Surge 配置，不是 JSFX。当前默认 Zoom 为 135%，
   已保存实例可以保留自己的 Zoom。设置文件为 `~/.Surge XT/SurgeXTUserDefaults.xml`。
   `useKeyboardShortcutsPlugin=0` 关闭 Surge 自身快捷键，但实测不等于解决其输入问题。
   REAPER 的 host 顶栏颜色不是 Chord Lab 可以为所有插件统一控制的。
7. 没有常驻服务、全局键盘捕获 helper 或键盘日志；未依赖 SWS / js_ReaScriptAPI。

## 修改、保存与回滚

- 只改仓库源码，别改 symlink 的“另一份”；不要移动源码目录后留下断链。
- 配色与字体改 `theme.toml`，通过安装器生成 `theme.jsfx-inc`，不要分别维护两份主题。
- 修改音频逻辑前退出模式、松开全部按键，先在 `/tmp/` 工程副本测试。
- 测试探针只用于测试：不放进最终 RPP，不随正常安装部署。
- `Ctrl+S` 保存 RPP 中的 Surge 状态；公共 FXP 要在 Surge 另存。二者不是自动双向同步。
- 新增公共 FXP 不会自动增加现有 RPP 轨；复制音色轨并换 patch 时同步其库标记，
  重启 Library mode 重新扫描。不要重跑 builder 覆盖已有精调。
- 卸载见 `README.md` 的 `install.py --uninstall`，先退出 REAPER；恢复 VKB 设置，保留备份。
- 不把 RPP 备份、音频、参考曲或系统配置混进本目录；不自动提交 Git。

## 尚未掩盖的限制

- 原生 VKB 显示控制键而非实际输出音；以 Chord Lab 图为准。
- 原生 VKB 不能保证在所有 Surge GUI 焦点／鼠标拖动过程中接收到电脑按键。
  2026-10-15 原生输入复测：先在 Chord Lab 按住 D，再拖动 Surge cutoff，声音持续；
  但 Surge 获得焦点后松开 D，Chord Lab 仍显示 held=1，存在丢 Note Off／挂音。
  所以目前应松键后再进入 Surge 编辑，不能宣称电脑键跨窗口持音交互已通过。
- Tab 的原生传递仍未完成可靠验收，`Cycle chord type.lua` 可作为明确 action。
- 当前 Surge 内部 Menu 弹出即关闭，在独立单 Surge 测试工程也复现；不是整个 GUI
  不响应鼠标：Scene 按钮与 cutoff 拖动已确认有效。临时 REAPER 7.82、VST3 对照
  也未修复菜单；正式安装仍为 7.78，没有把试验环境写入启动器。
  未定位确切根因，不能把窗口布局／选轨测试通过当作完整交互验收通过。
- 没接真实 MIDI 键盘时，只能报告 MIDI 消息通路测试，不能宣称 USB 硬件已经验收。
- 离线／删除插件、关闭音频设备等强制操作前先松键；异常挂音用 REAPER All notes off。

完整音色库测试与性能数据见 [`../library/VALIDATION.md`](../library/VALIDATION.md)。

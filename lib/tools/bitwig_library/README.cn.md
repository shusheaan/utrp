# Bitwig Library 完整迁移（进行中）

## 当前：两组都不自动 Arm（2026-10-21，controller 0.10）

- 取代 0.9 的 MIDI 自动 Arm：已选 MIDI／吉他音色都是 Active ON、Monitor ON、Arm OFF；同组其他音色关闭，组间仍独立。激活后的延迟回调也只清除 Arm，不再写入 true。
- 宿主 Settings → Recording → Auto-arm：Instrument tracks 与 Audio tracks 均关闭。检查时前者开启、后者已关闭；仅取消前者。这是全局选轨偏好，不只针对 Library，其他工程需要手动 Arm。
- Arm 只是允许轨道参与录音，并不等于已开始录音。实时演奏使用显式 Monitor ON；若以后要在 Library 录音，先关闭控制器的 Exclusive audition + editors，再手动 Arm，以免再次选轨时被试听规则清除。
- 40 项相关 pytest 通过（含 Node 模型中的启动、激活旧状态、跨组切换及没有瞬间 Arm true 写入）；普通工程的 Active／Arm／Monitor／窗口状态保护不变。实际检查 B2-juno60、Suitcase EP、Glass Air、Soft Prism 均未 Arm，Monitor ON；原 B2-juno60 + Glass Air 已恢复。
- 证据：`target/library-no-auto-arm/`。默认 Chord Lab 窗口及 20 品没有再改。

## 历史记录


## 当前：吉他只监听，不自动 Arm（2026-10-21，controller 0.9）

- 用户只需实时演奏：选中 AG 吉他轨时 Active ON、Monitor ON、Arm OFF；同组其他轨仍关闭，已选 MIDI 音色不变。激活后恢复的旧 Arm 状态也会在延迟回调中清除。
- MIDI 组仍沿用原先选轨/Arm 行为。分组是互斥规则，不新增可见文件夹；原有 MIDI 文件夹与 Ambient Guitar 布局不动。
- 40 项相关 pytest 通过。已部署并在实际 Library 选中 Glass Air，确认 Arm 灰色、输入监听开启、轨道与 Master 有电平。Beat Lab 轨 Arm 已关，插件 Record 可用、Stop 禁用、Input silent，未在录音；未删除已有录音或 MIDI。
- 用户报告 Spark 强杂音已消失；此次未额外录制诊断音频。此前采集异常的具体根因及重开稳定性仍未证明，见 [音频路由记录](../audio_routing/README.cn.md)。

## 当前：MIDI 与吉他独立试听（2026-10-21，controller 0.8）

本节取代下方历史记录中的“钢琴与吉他全局互斥”。已知 MIDI 音色与四条 `AG - ...` 吉他音色分成两组：选轨只改变本组的 Active / Arm / Monitor，另一组保留。因此可同时保留一个钢琴/合成器和一个吉他效果轨。首次使用时分别点一次两组想用的轨；不自动挑选另一组音色，也不创建新轨。

- 组内仍停用未选音色（不是只按 Mute），切换会截断该组旧音色尾音；音量、输入和插件参数不变。
- 插件窗口仍跟随最新选择；关闭另一组窗口不代表停止其声音。共享输入、raw detection、自定义非白名单轨和普通工程不纳入组内互斥。
- 两组激活后的延迟 Arm 修复独立，快速跨组切换不会取消另一组的修复；换工程/关闭控制器设置仍取消两组待执行动作。
- 验证：`python -m pytest -q lib/tools/bitwig_library/tests lib/tools/daw_backup/test_live.py lib/tools/daw_backup/test_snapshot.py`：40 passed；Node 包含组内互斥、跨组保留、快速切换、辅助轨及普通工程状态不变。当前执行环境未发现可访问的 Bitwig/Sway 会话，未做宿主实时选轨或真人吉他＋MIDI 同时发声验收。

## 当前：Keystation 硬件控制

独立 Transport 控制器、播放/录音/方向键、CC7 滑杆与轮子用法及验证边界，见 [Keystation 使用说明](KEYSTATION.cn.md)。保留原 Generic 演奏输入和 Library controller，不修改 Chord Lab 发声代码。

## 最新：Ambient Guitar / controller 0.6

新增 **Ambient Guitar** 分组及四条实时吉他效果轨；音频效果与共享的“仅显示”识别支路分离。见[路由、调节方法、文件与验证说明](AMBIENT_GUITAR.cn.md)。此节覆盖下方历史轨道数量：Library 现为 113 轨（含分组与 Master）。

## 当前更新：吉他只显示，不触发音源（0.2.5）

- MIDI channel 15 保留为 display-only 输入：Note On/Off 更新钢琴、指板和谱面高亮，不向下游发出音符；该通道的 CC、Sustain、bend 等也不透传。
- 实体键盘使用 channel 1–14，电脑控制继续保留 channel 16。吉他与键盘即使同音也独立释放，吉他不会占用或延长音源的发声。
- 不增加开关或参数；21 个参数、稳定 CLAP ID、v3 工程状态格式不变。旧状态可直接读取。
- Guitar Frontend 本身仍输出 channel 2；Library 的 Note Receiver Source FX 将 2→15，再进入共享 Chord Lab。Mutes Input 保持 OFF。
  该映射只作用于接收的吉他，不改变实体键盘的通道和力度。共享插件升级不会自动修改 REAPER 的旧路由；其他宿主需要同样把检测支路映射到 15。
- Spark GO USB 原始输入已接回，吉他轨 Monitor ON、Detect ON，音频推子仍为 −∞，避免与 Spark GO 的直接声音重复；后续 DAW 效果器必须放在检测器之后。

验证：562 项 pytest、6 项 CTest、真实 CLAP probe 全通过；覆盖 128 个显示音高、控制消息隔离、同音混合输入、两模式电脑键释放、失焦及重复 Note On。
证据及部署前备份：`target/chordlab-guitar-display/`。本次不是识别准确率或真实吉他延迟的验收，不声称 100% 音高识别。

部署后 Bitwig 检查：保存、关闭并重开 Library，Source FX 的 2→15 映射保持；Acoustic Piano 为当前试听轨。
向 Bitwig 吉他输入注入 220 Hz 合成音时，共享 Chord Lab 显示 A3，高亮存在且钢琴/主输出电平表无活动；随后电脑 C 和弦键正常产生音源电平，松键后高亮与电平消退。
临时 PipeWire 测试源已退出；Spark GO capture→Bitwig in1 及 Bitwig out1/out2→Spark GO 输出保持连接。
Library 已再次保存，焦点恢复到 Chord Lab。合成音测试不等同真人吉他或实体 MIDI 键盘验收，仍需用户试弹确认听感。

此节覆盖下方历史记录中的吉他 2→1 发声音源路由及硬件未连接状态。

[English](README.md)

**当前状态与完整文件地图：** [2026-10-18 收尾总结](WRAPUP.cn.md)。下文包含历次验收记录，
键位、外观、路由与调式支持以最新收尾及 controller 0.5 为准；硬件实弹仍待完成。

## 原则

- 只读 `~/storage/daw/synth.rpp`，保留最新已保存插件状态、音量、分组。
- 95 个音色：93 个 Surge CLAP、2 个 sfizz 钢琴。覆盖仓库全部 88 个 FXP。
- sfizz LV2 → VST3：沿用实际加载的 SFZ、Scala、CC 和合成参数；Acoustic Piano 使用 Retuned SFZ，而非过期 source marker。
- 迁移通过官方 DAWproject 格式；`write_project` 拒绝覆盖已有文件。
- 原 REAPER 工程和共享 CLAP 二进制不修改；完整验收前不删除。
- Basic Keys 的 ReaVerbate → Bitwig Reverb 已获用户批准；不同算法，必须记录差异，不能宣称完全等价。

## 工具

```sh
python lib/tools/bitwig_library/build.py ~/storage/daw/synth.rpp /tmp/Library-candidate.dawproject
python -m pytest -q lib/tools/bitwig_library/tests
node lib/tools/bitwig_library/tests/controller_test.cjs
```

`--probe` 只导入前四个 Basic Keys 音色。必须另行完成 Bitwig 内的共享输入路由。
生成的 JSON 是源清点报告，不代表宿主发声验收。

`Library.control.js` + `Library.config.js` 是 Library 专用选轨试听控制器，要求 API 25。
只匹配 `Library` / `Library-migration` 工程及共享轨标识；不向其他工程应用互斥试听。
点击音色轨后只启用一个音源，并打开音源编辑器和共享 Chord Lab。
不重新生成/中继 MIDI，不包含网络监听。已部署到 `~/Bitwig Studio/Controller Scripts/UTRP/`，
在 Bitwig Settings → Controllers 中启用 `UTRP Library`。
慢速插件加载时有受限窗口重试，切换工程或再次选轨会取消旧请求。

## 当前验证与缺口

- Python：11 passed；Node 控制器模型测试通过（含慢速窗口和激活后恢复录音准备状态）。
- DAWproject 官方 XSD 验证通过。
- 四音色探针：sfizz 原样本成功加载，实际发声；共享 Chord Lab 电脑键盘 → 钢琴路由通过。
- 正式工程：`~/storage/daw/Library/Library.bwproject`，108 轨：98 音色、7 分组、共享 MIDI、吉他、Master。
- 95 个原音色全部通过共享轨 MIDI → 音源发声/互斥检查；三个保留 Pad 也全部通过。
- 95 个原音源完成 Bitwig 实际导出状态比对；Surge 合成参数、wavetable、调律保持一致。
- sfizz 初次导出 component 字节完全一致；实弹/重开后 Acoustic Piano 多保存一个默认 `CC64=0`。
  验证器明确记录此非字节等同差异，仅允许这一关闭踏板的默认值；不忽略其他 CC 或参数变化。
- 正式项目已保存、关闭、重开；钢琴、EP、高增益音色和三个 Pad 的重开发声/互斥/录音准备抽检通过。
- 通过 GUI 录制电脑键盘三个和弦，共 12 个 MIDI 音符，导出核对；测试片段已删除，最终导出为零测试音符。
- 原 RPP 及两个共享 CLAP 的 SHA-256 未改变。原三 Pad 项目备份在
  `~/storage/daw/Backups/bitwig-library-before-full-migration-20261017/`。
- 临时 `Library Probe` 控制器及脚本已移除，TCP 19671 已确认不再监听。
- Spark GO 当前不在系统设备列表；不能宣称硬件端到端通过。

## 已批准的差异与使用

- Basic Keys 分组后级：Bitwig Reverb，Room、Size 70%、Pre-delay 20 ms、Decay 1.60 s、Mix 12%。
  这是轻混响初始设置，不是与 ReaVerbate 做过盲听匹配的等效算法。音源本身保留。
  手调：点 Basic Keys 分组，在底部 Reverb 调 Mix（干湿量）和 Decay（尾音长度）；
  `Ctrl-click` 参数可输入精确值。其他分组原 Surge 内置 FX 保持不变。
- `C2-distant` 原推子 +12 dB，超过 Bitwig 推子最大 linear 2.0。
  保留最大推子并在 Surge 后加 Tool Gain +5.9794 dB，组合恢复原增益；不修改 Surge 内部音量。
- 点音色轨：仅激活一个音源，打开音源与共享 Chord Lab。电脑键盘使用前点 Chord Lab 内容区域，
  确认 Keyboard 绿灯；实体 MIDI 不应依赖插件窗口焦点。窗口重开的布局仍需视觉复核，
  本轮最终钢琴窗口已与 Chord Lab 手动并排。
- 录音目标是选中的音色轨，而不是共享 MIDI 轨。已停用的轨可能仍保留历史 arm 标记，
  实际只有当前启用音色参与演奏；正式控制器在激活后重新 arm 当前轨。
- 做多轨编曲前在 Controllers 关闭 `Exclusive audition + editors`；此模式专用于 Library 单音色研究，
  不应在需要多轨同时播放时使用。
- Guitar 轨为 `Guitar Frontend → Chord Lab`，现在明确 `No input`、Monitor Off；
  Spark GO 恢复后接原始 mono input，识别器必须处于所有吉他效果之前。
- 当前仍是临时 HDMI 音频设备，测试为安全没有接外放输出；不等同于 Spark GO 可听演奏状态。
  待完成：Spark GO 恢复、实际监听输出、实体 MIDI 与电脑键盘混合演奏、吉他实弹、硬件重开验收。
  完成前不删除 REAPER。

证据目录：`target/bitwig-migration/`；关键文件 `routing-audio.json`、`pad-routing-audio.json`、
`final-state-check.json`、`recording-notes.json`、`reopened-sample-routing.json`、`source-hashes.json`。

## Chord Lab 外观更新（2026-10-17）

- 已部署 Bitwig 灰阶主题：背景 `#323232`、普通按钮 `#494949`；白琴键、浅色谱面/指板和音符角色色保留。
- 中性区域文字改浅色，普通、悬停、选中和禁用标签对比度测试均至少 4.5:1；Sustain/Keyboard 保留浅红/浅绿。
- 只修改绘制颜色，插件 ID、18 个参数、键位、MIDI 与存储格式不变。此次外观构建仍标记 0.1.6，
  用 SHA-256 区分：`c9453048bbdf5925f94d809c588d28f50df4263ed024614c57fc588e0308450d`。
  上文“两个 CLAP 未改变”仅描述迁移验收；本次明确更新共享 `~/.clap/Chord Lab.clap`，REAPER 下次加载也使用新配色。
- 本轮：88 项 Python、3 组 CTest、控制器模型和真实 CLAP probe 全部通过。
  Bitwig 已保存/重开；选轨重新打开音源与 Chord Lab；电脑键盘经共享轨至钢琴录得非零音频（峰值 −9.32 dBFS）。
  Shift Sustain 开关、失焦 Keyboard 红灯完成界面复核；浅色谱面仍清晰。
- 本轮未重复全部 98 音色发声矩阵；这些结果见上轮迁移记录。此次主题不改路由或音源。
- 重启后 Bitwig 自动接回临时 HDMI 输出，测试时临时断开外放，结束后恢复；这不是 Spark GO 监听验收。
  Spark GO 仍缺席，Guitar 轨仍 No input / Monitor Off；真实吉他及实体 MIDI 混合演奏仍需用户配合。
- 备份：`~/storage/daw/Backups/chord-bitwig-theme-20261017-231405/`；
  本轮证据：`target/bitwig-theme/`（截图、录音、测试、部署 hash）。原 `synth.rpp` 和 Guitar Frontend 未修改。

## 来源

- [Bitwig DAWproject](https://github.com/bitwig/dawproject)
- [sfizz VST3 state](https://github.com/sfztools/sfizz-ui/blob/develop/plugins/vst/SfizzVstState.cpp)
- [Steinberg streamer](https://github.com/steinbergmedia/vst3_base/blob/master/source/fstreamer.cpp)
- Controller API 以本机 Bitwig 6.1.4 随附文档为准。

## Bitwig 英文命名约定（2026-10-17）

用户要求 Bitwig 内所有可见名称使用英文，不加中文翻译。当前分组已改为 `Basic Keys` 和
`Pad Lab - Ambient Research`；以后新建轨道、分组、Clip、Scene、设备别名和备注均使用英文。
本仓库中文说明文档不属于 Bitwig UI，可保留。正式 Library 已保存；导出检查 108 轨的
project.xml / metadata.xml 中中文字符为零，95 个迁移音源状态比对通过。
证据：`target/bitwig-english/`。

2026-10-18 补查：之前的 XML 导出检查遗漏了 Basic Keys 和 Pad Lab 分组内的独立输出轨。
已通过 Bitwig 将其分别改成 `Basic Keys`、`Pad Lab - Ambient Research`，与外层名称一致，
并保存 Library。只读扫描保存后的原生工程：UTF-8／UTF-16 均不再出现旧中文名称；
带长度的 UTF-16 字符串候选中未发现其余可打印中文文本。该扫描并非完整原生格式解析器。
全部内嵌插件状态与修改前备份逐字节一致。证据：`target/english-ui-audit/`。
源 REAPER 工程和仓库中文文档未修改；以后 UI 命名继续只用英文。

## 小调优先的工程调性联动（2026-10-18）

`Library.control.js` 加载同目录的 `Library.key-sync.js`。Library 的 Project Remotes
`Perform` 页面前两项分别映射原生 `Root Key` 和 `Scale`。独立 Remote cursor 验证映射名称，
从共享 Chord Lab 的参数变化中仅取 `Key` 参数；`Am/C` 对应 A Minor，`C#m/E` 对应 C# Minor。
通过名称寻找 Minor，不依赖 Scale 列表中的固定下标。映射缺失、改名或调名未知时不写入。

最初为单向同步；以下双向联动更新取代该行为。本功能不转置已录 MIDI，也不自动分析音乐。
原有大调相对级数与和弦记忆保持不变。
需启用现有 Library 专用控制器设置，并保留上述两个 Project Remote 映射；其他工程不受影响。
联动使用 Bitwig 6.1 API 25，不属于通用 CLAP 工程调性接口；REAPER 不会因此自动同步工程调性。

sfizz 已使用原生 `Dark` 主题，设置保存在 `~/.config/SFZTools/sfizz/settings.xml`，
不改变采样音源及调音。Chord Lab 已移除不透明圆角遮罩：Bitwig 的父窗口仍是不透明矩形，
只裁剪插件子窗口不能产生真正的透明外圆角，因此恢复干净直角。


### 本轮验收与已知边界

- 修复 Bitwig 6.1.4 的参数路径差异：初始 `CONTENTS/PID…` 与实时
  `CONTENTS/ROOT_GENERIC_MODULE/PID…` 仅折叠这一明确前缀；其他路径不匹配。
  ID observer 必须先于 value observer 注册。模型测试包含初始/实时路径和无关参数拒绝。
- 真实 Bitwig 逐一点击 12 个调，插件标签与顶栏自然小调全部对应；电脑 W/Q
  换调也通过，最后恢复 `Am/C → A Minor` 并保存。
- 117 项 Python 测试、4 组 CTest、真实 CLAP 参数/GUI/状态/MIDI probe 通过。
  证据：`target/chordlab-minor-sync/`，含十二调矩阵与电脑键盘截图。
- 本轮未重跑 98 音色的发声矩阵，也未重新验收实体 MIDI/吉他；不改变音色或音频路由。
- 诊断中曾遇到带 sfizz 编辑器退出时的 X11 BadWindow / plugin-host 退出 139，
  根因尚未确认；先关 Chord Lab、再关 sfizz 编辑器、保存后退出的后续重启成功。
  sfizz 同时有 invalid parameter ID 544 日志，不能宣称宿主关闭路径完全无故障。

## Surge 主题选择（2026-10-18）

已从校验通过的下载包安装 `Modern Dark Blue` 与 Andromeda 的九套配色到
`~/.Surge XT/Skins/`。通过原生 `Menu → Skins → Modern Dark Blue` 切换并保存默认，
`defaultZoom=125` 不变，其余 Surge 偏好保持不变。手动切换 Andromeda：
`Menu → Skins → Andromeda → Blue / Dub / Green / Orange / Purple / Red / Teal / Wave / Yellow`。
这些是同一主题系列的视觉变体，不是音色或合成引擎模式。证据：`target/surge-modern-dark-blue/`。

## 双向工程调性联动（2026-10-18，controller 0.3）

- 控制器／工程初始化以 Bitwig 已保存调性为准：C# Minor → Chord Lab C#m/E，
  内部 Key 为 E；E Major 也对应这一组音。初始化后，两边均可改调，插件操作保留宿主
  当前 Major／Minor 模式。同一次 flush 同时变化时宿主优先；有序写入确认避免回传循环。
- 只支持 Major 和自然 Minor。其他调式暂停同步并用英文通知，不擅自近似或改掉宿主调式；
  返回 Major／Minor 后重新以宿主为准。插件原有大调相对级数引擎没有重写。
- 播放中或共享插件 Sounding 为真时，宿主到插件的换调暂缓；停止且释放和弦后应用最新调性。
  保留既有引擎安全锁，不属于 sample-accurate 实时调性 automation。仅联动主共享 Chord Lab，
  不含独立吉他显示实例。仍依赖 Library 范围保护和两个 Project Remotes 映射。
- 只更新 controller，CLAP binary、音色、音频路由不变。

验证：13 项 migration／controller pytest 通过；模型覆盖 24 种启动调性、288 次插件换调、
宿主改调、延迟及连续回传、冲突宿主优先、范围／映射保护、不支持调式、播放／持音暂缓、
参数 ID 替换与别名。Bitwig 实测 C# Minor → C#m/E、Db Major → Bbm/Db、插件 C#m/E →
E Major；Dorian 不会被强制改成 Minor，也不近似写入插件；切回 Minor 恢复同步。
播放时宿主改 G Minor 会暂缓，Stop 后插件选中 Gm/Bb。重新加载 controller 保留 C# Minor。
证据和修改前备份：`target/bitwig-key-bidirectional/`。

## 吉他共享输入与 Grid（2026-10-18，controller 0.4）

主共享链改为 `Note Receiver → Chord Lab`；接收 `Guitar Frontend` 输出，Source FX 内
`Channel Map` 把吉他 ch 2 转到 ch 1，`Mutes Input` 关闭，保留实体 MIDI 输入。
修复吉他与电脑和弦同音时先松一路误截断另一路的问题；插件二进制与音源状态不改。
controller 同时兼容原单 Chord Lab 链和这一明确前缀，不接受任意其他前置设备。

已完成 98 音色路由、8 个合成音高、混合输入与 Poly Grid 加载/音频测试；真实 Spark GO
录音按用户要求延期。当前吉他轨仍 No input / Monitor OFF，接回硬件后需要配置并实测。
测试方法、保存恢复记录、使用步骤和边界见[本轮验收说明](GUITAR_GRID_ACCEPTANCE.cn.md)。


## 自然调式双向同步（2026-10-18，controller 0.5）

本节替代 0.3 中“只支持 Major/Minor”的范围说明；原有安全保护保持不变。
支持 Major、Minor（自然小调）、Dorian、Phrygian、Lydian、Mixolydian、Locrian。
宿主改调时，按准确的七音音集映射到 Chord Lab 的母大调；插件改调时保留宿主当前模式，
移动其主音。例：D Dorian → Am/C；随后插件选 Bm/D → E Dorian。

**共享音集不等于共享主音或和弦级数。** Chord Lab 仍使用原有大调相对级数，
不会因为宿主是 Dorian 就自动把 ii 重标成 i；这是音集同步，不是完整 modal 和声引擎。
Harmonic Minor 等其余音阶暂停双向同步，不近似、不强改；回到支持的模式后以宿主为准。
初始化与同批冲突也由宿主优先。播放或持音时宿主换调仍暂缓，不承诺实时调性 automation。

已部署并重载 controller 0.5，CLAP 二进制和音频路由未改。
模型覆盖 84 个启动调性、1008 次插件选择、588 次宿主模式/主音组合转换，
使用独立音程表验证音集，并测试回传、冲突、暂缓及不支持音阶。
本轮相关 Python 回归 198 项通过（包含 controller Node 模型）。
Bitwig 真实界面通过 D Dorian → Am/C、插件 Bm/D → E Dorian、
E Phrygian → Am/C、E Harmonic Minor 双向暂停和返回 Minor 恢复。
最终恢复 C# Minor / C#m/E，Acoustic Piano、Sustain OFF，保存 Library 工程。
证据及修改前备份：`target/bitwig-diatonic-sync/`。未重做实体吉他录音或 98 音色发声测试。

Bitwig 顶部调性是工程级参考：用于钢琴卷帘的音阶提示与 Snap to Key、启用
Use Global Key 的 Note FX，以及 Grid 的音高量化/音阶级数移调。
它不会仅因改菜单就自动转调所有既有 MIDI、录音或改变 Surge 音色。
见 [Bitwig 6 官方说明，第 16–19 页](https://downloads.bitwig.com/6.0/Release-Notes-6.0.pdf)。

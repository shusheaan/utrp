# Portal

[English](README.md)

独立 Rust crate，放在 UTRP 中但不依赖其主程序或 workspace。Rust 后端内嵌原生 HTML/CSS/JS，不需要 Node 运行时。手机仅遥控，音频仍由电脑 CMUS → PipeWire / 现有输出链播放。

## 当前范围

- Local：歌手 → 专辑 → 歌曲、搜索、播放/暂停、上一首/下一首、±5 秒、进度条、循环。
- 上一首在播放超过 3 秒时先回歌头。音量沿用 CMUS 的 100% 配置，无音量滑块。
- Stream 已接入 Liked、Playlists、歌曲 Search、Recommended；复用用户 fork 固定版本的 Rust API 与现有认证文件，独立 headless mpv 负责播放，不遥控 TUI 界面。
- Local 播放前通过 MPRIS 暂停正在运行的 YTM；不会读取 Chromium Cookie。
- 曲库从 `music_root` 的 artist/album/file 目录结构生成，不修改文件或标签；新增文件后运行 `portal restart`。
- 上下首按整库路径排序，不是当前搜索结果队列。自然播完后的接续/列表循环仍由 CMUS 自己的队列与游标决定；不承诺与网页列表顺序相同。默认单曲循环不依赖这个顺序。

## 部署 / 恢复

先恢复 GRAL、UTRP 和 Storage，完成 GRAL 的音频安装及 Tailscale 登录：

```sh
cd ~/work/gral
bash arch/scripts/15-install-portal.sh
portal start
tailscale serve --bg --https=8443 http://127.0.0.1:8787
```

首次使用按 Tailscale 提示在浏览器启用电脑的 Serve / HTTPS；不要启用公网 Funnel。用 `tailscale serve status` 查看手机地址。手机连接同一 Tailscale 账号。

私密机器配置在 `~/storage/home/UserData/.config/portal/config.toml`（0700 目录、0600 文件），首次从 Tailscale 自动生成，重复安装保留原配置。新机器的域名、用户名/UID 或路径改变时需检查 `public_origin`、`allowed_login`、`cmus_socket`、`music_root`。不要把真实账号配置提交 Git。

源码、Cargo.lock、服务模板在本目录；部署脚本在 GRAL；音乐与私密配置在 Storage。二进制与 home 服务副本可重建。固定采用手动启动：GRAL 安装脚本每次将 `portal.service` 保持为 `disabled`，不停止当前网页／音乐。每次电脑重启后输入小写 `portal`；日常只需 `portal` / `portal stop`，不使用 enable/disable。`disabled` 与手动启动后的 `active` 可以同时成立。完整开关用法也收录在 GRAL `arch/sheet.md` 与 `arch/portal.cn.md`。

`portal` / `portal start` 启动网页；`portal stop` 一起关闭网页、托管 Stream / CMUS 并停播：先停 HTTP，再停止两项播放器服务，最后通过配置的 IPC 停止复用的 CMUS / Stream、暂停独立 YTM TUI。托管进程退出，独立终端不强制关闭。任何一步失败仍继续处理其他项并以非零退出；重复 stop 安全。`portal restart` 仍只重启网页、保留音乐，关闭浏览器不等于 stop；`portal status` / `portal logs` 查看状态。播放控制需要时会自动启动独立 PTY 中的 `portal-cmus.service`，不创建 tmux。原有 CMUS 可通过同一 Unix socket 复用。

## 安全边界

只监听 loopback；Tailscale Serve 提供 HTTPS，并由后端校验账号身份。写操作校验 Origin 和自定义请求头，不接受任意 shell/CMUS 指令或外部文件路径。仅允许曲库内文件；不通过浏览器发送音频文件、Google 凭据或绝对路径。

本机恶意进程仍可伪造 loopback 请求身份；这不是隔离同一台电脑上恶意程序的安全边界。限制 Tailscale ACL 与账号设备访问权；不要把后端改为 `0.0.0.0`。

## 验证

```sh
cd ~/work/utrp/Portal
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
```

2026-10-19：9 个 Rust 测试通过；实机曲库 918 首；390×844 手机尺寸浏览截图无横向溢出或 JS 异常；Serve HTTPS 返回 200。实际手机触控与硬件听音仍以用户验收为准。整机清空重装尚未演练；未 commit/push 的代码不等于远端备份。


## Stream 使用与边界

会话失效后在电脑执行 `ytm -auth`，网页 Refresh；每次读取列表重新载入现有认证文件并验证账号。Cookie 不发给手机、不另存密码。Rust API 固定为自己 fork 的 `09114f3076422756811c62889b605429df704813`。

Liked 首次读取 100 首可播放且不重复的歌曲，滚动到底或点 Load 100 more 再追加 100 首，最后一批可能不足 100 首。这是真正的上游分页，不再先读取全表再截断；上游每页数量不固定，剩余歌曲保留到下一批。所有歌单详情入口（含 Playlists → Liked Music）都使用同一增量分页；Search 和歌单库列表受 API 单页返回限制。点歌最多建立当前列表附近的 500 首播放队列。推荐中的专辑/歌单可以打开。本版不提供编辑歌单；播放器爱心支持 Like/Unlike。

底部播放器跟随播放来源，不随浏览 tab 切换。Portal 发起播放会暂停另一来源和终端 YTM；直接在另一个终端主动开始播放不在这个互斥范围，仍可能叠音。TUI 的正在播放与队列不会镜像到 Portal。

mpv 使用相同的 yt-dlp 解析方案，只接收固定 YouTube watch URL，不把凭据放在参数中；受限歌曲可能无法解析，不绕过访问限制。`systemctl --user stop portal-stream.service` 停引擎。`ops/mpv.conf` 是 home 部署副本的权威来源；队列为临时状态，不是保存歌单。网页进程重启不停止引擎，队列元数据丢失时读 mpv 的媒体标题。

隔离实测：正确账号、14 个歌单、50 项推荐、20 个歌曲搜索结果、2178 首歌单；真实网络音频使用 `ao=null` 成功解码，暂停后换歌、seek、三种循环均通过。手机 Stream 实际听音待用户确认。

最终验证：Portal 15 项测试、clippy 禁止 warning、GRAL 137 项测试通过。实机手机尺寸网页确认 2178 首 Liked，无 JavaScript 异常或横向溢出。


## 紧凑播放界面（2026-10-19）

顶部只保留小号 Local / Stream；歌曲列表为单行 title · artist，无音乐图标、无时长，次要信息最多占 25%，超长省略。底部为单行标题作者、原进度条、一排控制按钮：上一首、后退 5 秒、居中播放暂停、前进 5 秒、下一首、圈内 1/A/off 循环图标。播放行为不变，界面和无障碍标签均为 English。

隔离浏览器验收 320 / 390 / 768px：顶部 45px、底部 110px（不含设备安全区）、列表行 36px；作者宽度、省略、居中、按钮动作、循环、最后一行不被遮挡、无 JS 异常均通过。测试使用模拟 API，不触碰真实播放器。

```sh
# 可选浏览器测试依赖，不是 Portal 运行依赖。
npm install --prefix /tmp/portal-ui-check playwright
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/compact-ui.cjs
```

默认 `/usr/bin/chromium`，可用 `CHROMIUM_PATH` 指定；截图保存 `/tmp/portal-compact-{width}.png`。内嵌网页修改通过 GRAL 安装脚本重建，再只重启 `portal.service`，CMUS / Stream 引擎继续播放。


## Liked 增量分页（2026-10-19）

上游 continuation token 只保存在服务端。每批成功才提交缓存，失败/超时可用同一 cursor 安全重试。Refresh 重建列表；Portal 重启、认证文件改变，或另一个浏览器打开/刷新任一歌单后，旧 cursor 需要 Refresh。当前歌单内存缓存上限 10,000 首；`stream.list_limit` 仍控制其他列表，不控制固定 100 首的歌单批次。没有修改 fork/API 依赖，也没有新增运行依赖。

网页只追加新行，保留原列表和滚动位置。失败保留已加载歌曲并提供手动重试，到末尾停止请求。播放队列仍最多取已加载列表附近的 500 首，不会因为继续滚动自动扩展正在播放的队列。

验证：20 项 Rust 测试、clippy 禁止 warning、320/390/768px 紧凑 UI 回归、专门分页浏览器测试（100 → 200 → 请求失败 → 重试 → 250；无提前全量加载、保留滚动/DOM、已加载选歌、末页停止、Refresh/Search）通过。真实只读测试三批各 100 首且不重复，本次约 1.37 / 0.45 / 0.48 秒，实际速度随网络变化。

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/liked-pagination.cjs
```


## 胶囊 UI 微调（2026-10-19）

播放器及列表：白色标题靠左，最多占 75%；灰色作者靠右，最多占 25%；超长均省略，两者至少间隔 12px，移除圆点分隔。列表右侧标签使用半粗体。列表及高亮、搜索框、分组 tab 和描边按钮使用完整胶囊，播放按钮为圆形。两处返回按钮只保留箭头，仍保留英文无障碍标签与键盘焦点提示。播放行为和 Liked 每批 100 首分页不变。

紧凑 UI 测试增加 320/390/768px 下的左右对齐（含短作者名）、宽度上限、颜色/粗细、间距、胶囊半径、无分隔点和无边框返回按钮检查。


## Stream 默认页与纯黑背景（2026-10-19）

首次进入 Stream 显示 Recommended，不预加载 Liked。四个小胶囊顺序为 Recommended / Liked / Playlists / Search，固定单行、间隔 4px。Search 仍需要明确提交，Liked 仍按需每批加载 100 首。页面、顶栏、播放器、搜索框、导航底色及浏览器 theme-color 统一为纯黑 #000000；选中/焦点与警告状态仍有区分。浏览器测试覆盖初始 Recommended 请求、不抢先加载 Liked、320/390/768px 单行 tab 无文字裁切与纯黑底色。


## Local 导航压缩（2026-10-19）

Local 总览、歌手及专辑标题栏统一为单行：左侧 13px 半粗体标题，右侧歌曲数量；长名称省略，不换行。歌手/专辑分组名称加粗，数量继续右对齐。仅总览保留胶囊搜索框，可全库匹配歌曲名、专辑名或歌手名；进入歌手或专辑后隐藏搜索框，返回总览恢复。播放按钮保持真正的 36×36px 正圆（50% 半径）。不新增时长扫描，也不改播放行为。

`tests/local-ui.cjs` 在 320/390/768px 检查三级导航、长标题、全库三种搜索、返回行为与圆形播放按钮，不触发实际播放。


## 主页推荐与分类搜索（2026-10-19）

Stream 顶部不显示登录提示、账户名或重复的服务标题；账号验证逻辑保留；主入口顺序为 Recommended / Liked / Playlists / Search。默认 Recommended 保留真实账号 Home 分组的名称与顺序，滑到底或点击 Load more 再取下一批，而非只显示首页第一批或提前下载全部主页。支持音乐分组中的歌曲、歌手、专辑、歌单；播客单集及尚未支持的特殊模块会跳过。推荐随账号与时间变化，不宣称完整复刻官方主页。

Search 由浏览器发起一次请求，Rust 后端并发请求四个分类接口，避开现有 API 对综合搜索“最佳匹配”卡片的漏解析，再用 Songs / Artists / Albums / Playlists 四个紧凑胶囊切换，不重复请求。歌手详情按接口实际返回展示 Top songs、Albums、Similar artists；专辑与歌单可继续进入歌曲列表。Back 恢复之前缓存的结果、分类与滚动位置；返回分页歌单时重新获取首批，避免使用失效游标。搜索框和分类只出现在搜索根页，详情内 Refresh 刷新当前详情，不跳回搜索。目前是每类首批结果，不是每类无限分页。

Home 与 Liked 一样使用服务端私有游标；已完成页可安全重试，刷新、认证文件变化或网页服务重启后旧游标失效。Home 安全上限为 50 批 / 10,000 项；同一首歌出现在不同主页分组时保留各自位置。没有新增运行包，也未改上游 fork；源码在 UTRP，私有认证与配置在 Storage。源码仍需 commit / push 才算 Git 备份。

验证：24 项 Rust 测试、clippy 禁止 warning；四套隔离浏览器测试覆盖 320/390/768px 布局、Local、Liked 分页、Home 续页、四类切换、失败重试、多层返回及详情刷新。真实只读请求得到主页首批 50 项、续页 30 项且重试稳定；示例搜索返回歌曲、歌手、专辑、歌单（包含精确匹配的歌手，跳过接口中缺少名称的无效条目），歌手、专辑、歌单均成功打开。数量只是本次观察，不是固定期望。没有发送真实播放控制命令。

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/stream-catalog.cjs
```


## 播放图标居中（2026-10-20）

36×36px 正圆按钮改用固定 SVG，消除文字播放/暂停符号受字体基线和留白影响的问题。SVG 视口水平、垂直居中；暂停双竖线对称，播放三角形按填充面积重心居中。状态轮询只切换图形可见性，不替换 DOM，不改变无障碍标签或播放行为。`tests/play-icon.cjs` 在 320/390/768px、2×/3× 像素密度下验证两种状态、控制动作、DOM 保持和亚像素中心误差；全页及按钮截图保存到 `/tmp/portal-icon-*`、`/tmp/portal-button-*`。

```sh
NODE_PATH=/tmp/portal-ui-check/node_modules node tests/play-icon.cjs
```


## 统一选中态灰色（2026-10-20）

统一使用 `--selected: #414141`：顶部和分类胶囊选中态、当前歌曲整行及边框、正圆播放按钮、进度条已播放部分、拖动圆点。未播放部分保留较暗的 `#181818` 以区分进度；控制图标保留浅色保证可读性。仍使用原生 range 输入框及 32px 交互区域，保留触摸和键盘行为；显式设置 WebKit/Blink、Firefox 的 14×14px 正圆滑块。进度填色随播放和拖动预览同步，不引入自定义 pointer-event 拖动组件。

`tests/gray-theme.cjs` 在 320/390/768px 检查 Local/Stream 的颜色一致、滑块 CSS 几何、0/50/75/100% 填色、拖动预览、提交 seek 和键盘输入；高 DPI 截图在 `/tmp/portal-gray-*`。继续运行图标居中与其他 UI 回归测试。


## 一体纯黑布局（2026-10-20）

移除顶部胶囊区域下方、底部播放器上方的分隔线。保留 sticky 顶栏、fixed 播放器及不透明纯黑背景，列表滚动到边界仍被遮挡，不会穿透。胶囊边框和播放控制不变。`tests/gray-theme.cjs` 在三种屏宽验证区域无边框、无阴影、纯黑背景及原有定位。


## 随机播放与紧凑循环图标（2026-10-20）

播放控制整排七个 SVG 统一为 21×21px、24×24 viewBox；居中播放按钮保留 36px 圆形背景。Shuffle 不显示 On/Off 文字，开启为白色，关闭为灰色（#808080）；无障碍标签及 aria-pressed 显示实际播放器状态，不是浏览器独有的开关。失败时不伪造切换成功，保留状态并提示错误。

Local 在 CMUS 的 shuffle=tracks / shuffle=off 间切换；开启时上下首使用 CMUS 原生随机顺序。Stream 使用 mpv playlist-shuffle / playlist-unshuffle 与 shuffle 属性；换队列保留模式及用户选中的歌曲。随机范围仅为当前已加载 Stream 队列，不包括未获取歌曲。切换不重启当前歌曲；刷新网页或重启 Portal 从播放器读取状态，播放器本身重启则遵循其启动默认值。循环模式独立：单曲循环仍优先，要自动随机换歌应选择循环 A/off。

验证：27 项 Rust 测试及 clippy；tests/shuffle.cjs 在 320/390/768px 覆盖两个来源、纯白图标尺寸、对称、状态切换、失败反馈及刷新恢复。临时 WAV + 独立静音 mpv 验证当前歌曲/暂停状态不变和恢复顺序；隔离 CMUS 验证 tracks/off 原生命令。继续执行既有 UI 回归测试。


## 紧凑搜索工具栏（2026-10-20）

Stream Search 使用全宽胶囊：输入后按 Enter 搜索，保留环形刷新按钮，不再显示放大镜搜索按钮。隐藏重复 Search 标题和空页提示，保留英文无障碍标签及 Enter 搜索。其他 Stream 页与详情页仍在标题旁显示同一个刷新图标，返回搜索时移回搜索栏。Stream catalog 浏览器测试覆盖手机布局、无边框居中图标、空查询、点击/回车搜索、刷新及多级返回。


## 淡灰光晕与白色进度（2026-10-20）

播放器顶部留白从 6px 增至 14px：不透明纯黑遮挡边界上移 8px，标题和控制按钮位置不变，ResizeObserver 同步列表底部空间。已播放进度及正圆滑块使用 --progress-color: #fff，未播放轨道保留暗色。导航选中胶囊、当前歌曲行、播放按钮统一加入 3px 模糊、0px 扩散、32% 不透明度（歌曲行仍裁切在上下各 2px 的间距中线内）的轻微中性灰色光晕；不加分隔线、区域阴影、文字模糊或动画。Gray-theme 回归验证不含 safe-area 的 117px 播放器、14px 标题留白、列表避让空间、白色进度及仅选中态的统一光晕。

### Stream 固定工具栏与账号喜欢状态

Stream 的列表操作栏（返回、标题、图标 Refresh）滚动时保持在来源切换栏下方，涵盖歌单、专辑、歌手详情；Search 保留单行紧凑搜索栏并固定。Local 列表标题栏也吸附在来源切换栏下方。

播放器仅在实际来源为 Stream 且有歌曲时显示爱心，与当前浏览哪个 tab 无关。实心表示喜欢，空心表示未喜欢。换歌和页面可见时的定期检查从 YouTube Music 读取真实状态；点击设置 LIKE / INDIFFERENT，并在读回确认后更新。成功无提示；未知或失败显示 inline error，下次点击先重新读取，避免盲目切换。Local 不发送评分请求。写入会使 Liked 分页缓存失效，已打开的 Liked 自动刷新，返回 Liked 时重新获取首批 100 首。其他页面／设备的旧分页可能需要 Refresh。

`GET /api/stream/like?id=VIDEO_ID` 与 `POST /api/stream/like`（`{"id":"VIDEO_ID","liked":true}`）沿用私网身份和 CSRF 校验。验证 ID，显式幂等写入、独立限流与超时，不阻塞播放锁。凭据和上游原始响应不发送给浏览器。`tests/stream-rating.cjs` 在隔离 mock 中验证手机固定栏、确认后点赞、Liked 刷新、失败恢复、重新载入和过期响应隔离，不修改真实账号。

### 紧凑吸顶列表标题

Local 和 Stream 的列表标题栏都吸附在来源切换栏下方。Stream 灰色已加载数量移至标题同行、最右侧 Refresh 之前，返回留在最左侧；两边统一 44px 标题栏、13px 标题和 11px 数量，长标题省略而不换行。正常数量不再占用下一行；加载、空列表和错误信息仍独立显示。尚有分页时显示 `100+ tracks`，不将已加载数量误报为总量。Search 保留单行搜索表单，有结果后将当前分类数量放在 Refresh 前。

### Local 首页精简与 Stream 分段胶囊

Local 首页直接显示搜索框，不再显示 Local music 标题和总数量，搜索过滤时也不显示。进入歌手／专辑后仍保留返回、标题、数量和吸顶行为。Recommended / Liked / Playlists / Search 放在同一个外层长胶囊内，边框、内边距、间距和高度与顶部 Local / Stream 一致；内部选项去掉独立边框，选中项保留灰底及光晕。


## Fade 与 AB 区间循环（2026-10-20）

Local 和 Stream 底部都是九个同尺寸图标：AB、Fade、上一首、−5 秒、播放/暂停、+5 秒、下一首、Shuffle、Repeat。原播放区高度不增加。

- 左侧第二个曲线图标控制 Fade：白色开启、灰色关闭。手动换歌先淡出，再加载新歌淡入；自然换歌和单曲循环也有淡出/淡入。这不是两首同时播放的 crossfade，也不保证网络曲目无缓冲间隙。
- 最左侧圆圈始终白色：`A` 表示未标记，点下取电脑播放器当前位置作为 A；`B` 表示等待第二点，再点取 B；`AB` 表示循环中，再点清除。进度条下面显示两点，A 可以晚于 B，实际循环 `min(A,B)..max(A,B)`。两点至少相距 1 秒；Local 的 CMUS 标记/seek 精度为整数秒，Stream 使用 mpv 小数秒位置。
- AB 启用时临时强制 Fade，Fade 按钮点亮且不能关闭；清除 AB 恢复该来源此前的 Fade 偏好。短片段将每端 Fade 缩短到不超过区间长度的三分之一。
- 两个来源各有独立运行时状态。网页刷新、手机锁屏/关网页不清除状态，Rust 后台继续执行；暂停保留区间。换歌清除旧区间，拖动进度条或按 ±5 秒不会改变 A/B 标记；手动移出区间时暂缓循环、允许自由试听，重新进入区间后继续循环。`portal restart` 不停音乐，但会清除这些临时状态并恢复播放器软件音量 100%；重新启动默认 Fade 关闭、未设置 AB。
- `config.toml` 顶层 `fade_seconds = 0.75` 控制每端最长时长（允许 0.1–5 秒）；缺少该项默认 0.75 秒；已有显式值不会被安装脚本覆盖。改配置后 `portal restart`。这不修改 PipeWire/系统音量；CMUS 明确启用软件音量。常态仍是 100%。服务正常退出、启动及 `ExecStopPost` 都尝试恢复 100%，失败会记录错误而非静默。
- 代码、默认值、服务模板与测试在 UTRP `Portal/`；部署仍由 GRAL 安装脚本重建。只有机器配置存 Storage，短暂 AB 标记不保存到歌曲/音乐文件，也不上传 YouTube。

验证：Rust 单元/IPC/无浏览器后台循环测试、clippy、320/390/768 宽度的手机 UI 回归；另行运行 `cargo test --locked real_mpv_null_audio -- --ignored`，实际 mpv 使用临时静音 WAV 与 `--ao=null` 验证多次 AB 循环和音量恢复。独立临时 CMUS（ALSA null、独立 HOME/socket）已验证软件 37%/100% 音量和绝对 seek。没有为测试切换用户正在播放的音乐；实际音箱上的听感仍需试听。


Local/Stream 来源栏、Stream 四个入口和 44px 列表标题栏从首次显示起就固定在顶部；标题不加胶囊边框，上下各增加 6px 留白。只有下方列表 viewport 滚动，黑色顶部不会经历多级吸顶或露出下方光晕。歌曲行相距 4px，光晕在各行上下 2px（间距中线）以及列表边界处硬裁切，不能侵入标题区。Local 搜索、Stream 搜索/分类也留在固定区域。分页和返回位置使用各自列表的 scrollTop，不再滚动整个页面。

本轮验证（2026-10-20）：46 个 Rust 测试通过，隔离 real-mpv 测试另行通过，clippy 无警告；10 组前端回归覆盖固定顶部、像素级边界遮挡、短列表、分页、搜索、Like 与九键排列。已通过 GRAL 安装并经用户许可重启，仅清空临时 AB，CMUS/mpv PID 不变。线上静态文件与源码一致；CMUS 双声道软件音量、mpv 音量均为 100%，系统 sink 为 1.00；服务 active/disabled，未认证请求返回 403。配置保存在 Storage，源码尚未 commit/push，不等于已在远端备份。

Local 首页搜索胶囊与 Stream 四入口外框共用相同位置、宽度和 32px 高度，文字统一为 11px；切换来源时外框不跳动。搜索仍匹配歌名、专辑和歌手。

## 歌单分页与统一搜索栏（2026-10-20）

所有歌单详情（不只是顶部 Liked）每批最多加载 100 首可播放且不重复的歌曲，上游多返回的歌曲暂存，不提前拉完整列表。游标绑定账号、歌单与代次；打开或刷新另一歌单会让旧游标失效，返回歌单时重新获取首批。专辑、Home 分组及搜索仍按各自 API 行为处理。

Local 与 Stream Search 共享 32px 胶囊和 11px 输入字体，与 Stream 导航胶囊一致。搜索栏和分类控制均固定在列表滚动区域外。Rust 测试覆盖歌单身份、按需上游请求、余量缓存与失败重试；浏览器分页覆盖 Liked、LM、VLLM 和普通歌单四条路径。

验证：49 个 Rust 测试通过（隔离 mpv 测试按默认跳过），clippy 无警告，10 组浏览器回归通过。真实只读 Playlists → Liked 返回 100 + 100 首、不重复（1.19 / 0.40 秒）；另一歌单首批 100 首且可继续分页（0.84 秒）。速度随网络变化。已通过 GRAL 安装上线，线上资源与源码一致，播放器 PID 不变，Portal active 且禁止自启动；源码仍需 commit/push 才构成远端备份。

## 统一 Enter 搜索（2026-10-20）

两处搜索统一为全宽 32px 胶囊、11px 字体，不显示放大镜或单独搜索按钮。Local 提示 `Search`，Stream 提示 `Search artists, albums, tracks`。输入不触发搜索，按 Enter（手机键盘 Search 键）才提交；Stream 刷新图标及结果数量保留在胶囊内右侧。两个搜索栏都固定在滚动列表上方。浏览器回归比较两处尺寸/字体，并验证输入不提前搜索。

## 手机搜索聚焦缩放（2026-10-20）

Local 与 Stream 输入文字改为 16px，替代此前 11px 输入字号，避免手机聚焦小字号输入框时自动放大；胶囊仍为 32px 高，导航标签仍为 11px。不添加 viewport 缩放限制，不用文字缩放技巧。Enter 搜索、固定顶部逻辑不变。桌面 Chromium 手机布局测试检查字号、胶囊尺寸与未禁用页面缩放，但不能代替真实 iPhone 键盘/缩放验收。

两处空搜索框仅提示 `...`。Stream 搜索框移除刷新箭头及结果数量，仅保留输入框；再次按 Enter 即可重新搜索。歌单/详情的刷新按钮不变。输入字号仍为 16px、胶囊仍为 32px，保留完整无障碍搜索标签。

页面外缘黑色留白：顶部为 14px + safe-area，播放器底部为 11px + safe-area（上下各增加 8px）。无 safe-area 时顶栏/播放器高度为 52px/125px。内部按钮、行间距与仅列表滚动不变，ResizeObserver 自动同步播放器避让高度。

两处空搜索框统一使用 14px 装饰性放大镜 SVG，替代文字和三个点；聚焦或有输入时隐藏。图标不拦截点击、不提交搜索，实际输入仍为 16px。两边胶囊尺寸、Enter 搜索与无障碍标签保持一致，搜索页不增加刷新按钮。

## Stream 跨网页后台重启的可靠性（2026-10-20）

已经加载的歌曲不再依赖临时浏览缓存。后端验证固定的 YouTube video ID 并自行构造 watch URL；仍拒绝任意 URL、路径和命令。浏览器随原有队列 ID 发送有长度限制的标题/作者（最多 500 首），所以缓存淘汰或 Portal 网页后台重启后，旧列表仍能选歌。旧版仅发送 ID 的页面继续兼容；升级后刷新网页一次，获得显示信息保留和自动接续分页的新逻辑。

队列信息放在 mpv 的 `user-data/portal-tracks` 中，每次换队列替换整份、读取时只读取当前一首。只要播放器仍运行，Portal 网页后台重启不会丢失这些信息；这不是永久听歌历史数据库。同一首歌的临时不完整状态不再擦除作者，换歌不继承上一首作者。即使没有作者，爱心也固定靠右。

分页游标过期（HTTP 409）时自动重建必要的前缀，直到找到新条目；已有列表和滚动位置保持不变。歌单首次仍只加载 100 首，不增加后台全量下载。恢复有上限、去重，不自动重放播放/点赞 POST。真实网络或授权失败保留列表并允许重试，不无限重试。Refresh 仍可用于主动获取新的列表/顺序，但缓存失效不再要求手动 Refresh；本说明替代此前过期后手动刷新的行为描述。

不能承诺 YouTube 的媒体直链或登录永不过期：播放使用固定 watch ID，由 mpv/yt-dlp 在加载时解析媒体地址。歌曲下架/限制、账号授权过期、上游/网络故障仍可能阻止播放。`ytm -auth` 用于真正的账号授权失败，而非 Portal 缓存淘汰。

源码与回归测试在 UTRP `Portal/`；GRAL `arch/scripts/15-install-portal.sh` 重建并安装内嵌前端和 Rust 后端，现有机器配置继续放在 Storage。部署后仅重启 `portal.service`，保留播放器进程（临时 Fade/AB 状态仍会重置）。不新增公网监听、Funnel、浏览器 Cookie 或开机自启。两个仓库的修改仍须 commit/push 才构成远端备份。

验证：51 项 Rust 测试通过，另行运行的 2 项真实 mpv 隔离测试通过，clippy 零 warning，全部 11 个浏览器测试套件及 3 项 GRAL 策略测试通过。已走 GRAL 安装流程部署，线上内嵌资源与源码一致。只重启网页后台，CMUS/mpv PID 和暂停状态保持不变，当前 Stream 作者跨重启保留。自启动仍禁用，匿名 HTTP 请求返回 403。未进行数小时真实播放耐久测试；过期/重启场景通过隔离播放器和浏览器模拟接口确定性复现。

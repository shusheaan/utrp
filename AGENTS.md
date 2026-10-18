# Project skills

- 当用户要求分析乐谱、TAB、solo 骨架、调性、把位、和弦音位置或结构化练习路线时，先读取 `skills/score-skeleton/SKILL.md`。
- 本项目用 `sheets/` 保存本地谱源与分析；谱源与分析必须明确区分。已有付费 PDF 默认仅供本地使用，不自动提交或发布。
- skill 源码保存在 `skills/`；不要声称已经安装到全局 skill registry。

# DAW 定制持久化

- DAW 定制源码、配置配方、部署与恢复说明保存在 UTRP；工程、采样、主题/插件二进制保存在 `~/storage/daw/`。`lib/tools/daw_backup/live.toml` 所列音乐偏好与用户资源的实体目录必须在 `~/storage/daw/UserData/`，home 只是目录 symlink 入口，不以时间点快照代替实时主数据。账号激活、缓存及清单外文件不自动搬迁。
- 迁移或重建链接使用 `python lib/tools/daw_backup/live.py --apply`（先关闭 DAW）；`--check` 核验。不要将部署入口重新替换成 home 实体目录，不用容易被原子保存覆盖的单文件 symlink 迁移偏好。重装保留 Storage 后重建链接；冲突目录先人工审查，不覆盖。
- 修改 home 中的 controller、插件、音频规则或偏好后，收尾时更新 `lib/tools/daw_backup/` 恢复清单并执行快照。重装前先正常退出 DAW，再补快照以捕获内存中未落盘的设置；许可证/账号凭据不进 Git。
- 未提交源码不等于已在 Git 保存；明确报告 commit/push 状态，必要时用 Storage 中的源码快照保底。不自动创建提交或推送。
- Library 的互斥试听只用于音色库工程，不应用到普通录音/编曲工程。更改 controller 时验证其他工程的 Active、Arm、Monitor 和窗口状态不被改动。

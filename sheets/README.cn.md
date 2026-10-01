# 乐谱与结构分析

[English](README.md)

这里保存用户已有的本地谱源，以及依据具体谱面写出的结构 notes。

## NLND

- 原始库：`/home/shu/storage/documents/media/NLND_TABS/`。
- 项目副本：`NLND_TABS/`，10 份 PDF，原文件名不变；仅复制，未改写原谱。
- [复制清单与 SHA-256](NLND_TABS/manifest.json)。购买凭证未核验，不仅凭文件推定授权来源。
- [Drown — Mateus solo 结构分析](NLND_TABS/drown-mateus-skeleton.cn.md)：PDF 第 14–21 页，105–136 小节，尾音到 137 小节。
- 其余 9 首仅归档，尚未分析。

## 使用原则

PDF 默认被 `.gitignore` 排除，仅供本地使用；没有执行 commit、上传或发布。分析 notes 和 manifest 可独立版本管理。重新 clone 项目不会自动带上这些 PDF。

分析流程见 [score-skeleton skill](../skills/score-skeleton/SKILL.md)。事实、推断和练习版分别标明；不能用缺少伴奏的 solo 谱假装还原了完整和声。

## 指板矩阵

[工具研究与一键生成方法](fretboard-tools.cn.md)：Python + TOML → SVG／PNG；五张矩阵已嵌入 Drown 分析。

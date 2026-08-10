# lib — 音色库(patch 即代码)

utrp 的声音资产层:合成器 patch 全部以文本/小文件形式进 git,宿主通过 symlink
看到它们。目标是让"调音色"像写代码:可 diff、可回滚、git 历史即作者证据链。

## 布局与约定

```
lib/
  surge/           # Surge XT patch(.fxp,内容为 XML)
    endless/       # collection:Frank Ocean《Endless》复刻实验(2026-08-09 起)
  link.sh          # 布链:Surge 浏览器 User 区出现 utrp/ 目录
```

- 按引擎分顶层目录(以后可加 zyn/、sfz/、drumkv1/),按主题分 collection 子目录
- 命名:`<目标>-<变体>.fxp`;收录时在 Surge 的 patch comment 里写一行配方要点
  (如 `2saw det7 | LP24@1.8k | A550ms | chorus+hall`)
- **只进文本类 patch。任何音频物料(采样、渲染、stem)留 `~/storage`,
  尤其从唱片切的采样绝不进这个公开仓库**

## 接入宿主

```sh
./link.sh   # ~/.Surge Synth Team/Surge XT/Patches/utrp -> lib/surge
```

系统重装后重跑一次(本仓库不由 gral 的 10-install.sh 管理)。在 Surge 里
save patch 时选 utrp/ 下的目录 = 自动落进本仓库。

## 环境关联(gral)

本目录只管音色资产;插件与宿主环境由 `~/work/gral` 还原,坏了先去那边查:

- 装了哪些合成器/效果:`gral/arch/audio-packages.txt`(取消注释 = 在用)
- REAPER 安装与配置纳管、硬件陷阱(DISPLAY / 采样率 / 电平):`gral/arch/audio/readme.md`
- 体检:`gral/arch/scripts/61-audio-stack doctor`
- A/B 参考工程与渲染管线:`~/storage/daw/endless-ref/`(scripts/ 内有完整分析代码)

## endless collection

首批 14 个候选,A/B 工程与渲染对比在 `~/storage/daw/endless-ref/`(REAPER
工程 + demucs 参考 + 渲染管线脚本)。目标与配方见该工程的 README。

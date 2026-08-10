# lib — 音色库(patch 即代码)

utrp 的声音资产层:合成器 patch 全部以文本/小文件形式进 git,宿主通过 symlink
看到它们。目标是让"调音色"像写代码:可 diff、可回滚、git 历史即作者证据链。

## 布局与约定

```
lib/
  surge/           # Surge XT patch(.fxp,内容为 XML),按 collection 分子目录
    endless/       # Frank Ocean《Endless》复刻实验(2026-08-09 起)
    sega-universe/ # Sega Bodega《I Created The Universe…》
    tev-woods/     # Tev Woods
    magdalene/     # FKA twigs《MAGDALENE》
  tools/
    pipeline/      # 统一管线框架:spec TOML -> 分析/渲染/评分/RPP(见其 README)
    <collection>/  # 各专辑的提取数据(data/)+ 未泛化的特例脚本(remake 线等)
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

## 管线:从一张专辑到一组候选 patch

统一框架在 `tools/pipeline/`(用法见其 README)。一张专辑 = 一个
`tools/pipeline/specs/<album>.toml`,声明目标片段、试奏乐句、候选 patch 配方、
鼓段;分析侧(demucs/测量/鼓提取)和合成侧(surgepy 渲染/评分/RPP 组装)各一条
命令。产物分流:fxp 进本仓库 `surge/<collection>/`,音频与 REAPER 工程进
`~/storage/daw/<name>/`。

现有四个 collection(共 47 个候选)的 A/B 工程分别在 `~/storage/daw/` 的
endless-ref、sega-universe、tev-woods、magdalene,目标与配方见各工程 README。

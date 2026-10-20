---
slug: viz-diagram-pack
name: 图表与绘图包
displayName: 图表与绘图包
version: 1.0.0
license: MIT
category: visualization
description: |
  把数据可视化 / 智能图表 / 学术出版图 / 科学可视化 / 流程图 / Mermaid / ProcessOn 等可视化 skill 收敛成一个入口。
tags: [组合包, bundle, visualization]
---

# 图表与绘图包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
可视化类 skill 多个且用途交叉。本包按「业务图表 / 学术出版 / 架构流程图」分流。

## 包含的成员（7 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| data-visualization | local | AI智能数据可视化；支持多种图表类型（柱状图、折线图、饼图、散点图、直方图、箱线图、小提琴图、面积图、热力图、平行坐标图、旭日图等），根据数 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 智能图表 | local | 将数据文件（CSV/TSV/TXT/XLSX/XLS/JSON）转化为独立交互式 ECharts HTML 图表——32 类图表、3 套主题 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| academic-figures | local | >- | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 科学可视化 | skillhub | Matplotlib出版级图表/Seaborn统计图/viridis色盲友好配色/多子图编排GridSpec/论文投稿规范/矢量导出PDF- | `skillhub install kunlun-scientific-visualization --namespace kunlungrowth` |
| diagram-drawing | local | 绘制机制图、框架图、流程图、架构图、思维导图等结构化示意图。 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| mermaid-diagram | local | Generate Mermaid diagrams for product managers and developers. Use whe | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| processon-diagram-generator | local | 【强制触发】当用户要求生成、绘制、重绘、渲染或可视化任意结构化图表时，必须调用本技能。适用于流程图、业务流程图、泳道图、时序图、系统架构图、 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
1) 业务交互图表用 smart-charts（ECharts）/ generate-chart；
2) 论文出版级图用 academic-figures / kunlun-scientific-visualization；
3) 架构/流程/思维导图用 diagram-drawing-plus / mermaid-diagram / processon-diagram-generator。

## 一键导入 / 跨账号安装
本目录附带 `install_bundle.py`，在新账号机器上运行即可把成员补齐：

```bash
python install_bundle.py            # 默认装到 ~/.workbuddy/skills
python install_bundle.py --mirror "E:/project/skill/skills-for-cloud"   # 指定本机自研镜像根
```

- **SkillHub 成员**：自动用 `skillhub install` 拉取（匿名即可，无需登录）。
- **本地自研成员**：优先从 `--mirror` 指定的 skills-for-cloud 镜像拷贝；若镜像里没有，脚本会打印提示，
  需要你先把这些自研 skill 推到 GitHub 发布库（workbuddy-skills）或放进 skills-for-cloud 镜像。

## 发布 / 分享
本组合 skill 自带完整 frontmatter（slug / version / displayName），可直接：
- 用 `skillhub publish <本目录>` 发布到社区；或
- 拷进 GitHub 发布库（workbuddy-skills）的子目录，从 GitHub 导入。

## 维护约定
- 新增/剔除成员：编辑本目录的 `manifest.json` 后重跑生成脚本，或手动同步 SKILL.md 成员表。
- 非破坏式：绝不删除被组合的原始 skill。

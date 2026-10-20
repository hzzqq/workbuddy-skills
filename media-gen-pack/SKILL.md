---
slug: media-gen-pack
name: AI媒体生成包
displayName: AI媒体生成包
version: 1.0.0
license: MIT
category: media
description: |
  把图像生成 / 视频生成 / 音乐创作 / 海报 / 白板动画 / 抖音短视频 / 短剧配乐 / 剧本 等 AI 媒体生产 skill 收敛成一个创作入口。
tags: [组合包, bundle, media]
---

# AI媒体生成包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
媒体生成类 skill 非常多且易混淆。本包按「图/视频/音乐/海报/短视频/剧本」分流，按需取用。

## 包含的成员（12 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| ai-photo-restyler | local | 把一张照片转成漫画风、动漫风、卡通、水彩、手绘、黏土或 3D 角色画风，同时保住人物、宠物或商品的辨识度。这个 AI 照片转绘、照片转漫画工 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| first-last-frame-video | local | 用两张审核好的图片——一个首帧和一个尾帧——生成一条从首帧到尾帧的短转场视频。这个 AI 首尾帧视频生成和两张图生成视频工作流可以制作变装转 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| gpt-image-2-5-studio | local | GPT Image 2.5生图用 GPT-Image-2.5 和 ChatGPT Images 2.5 出一张图。GPT Image 2.5 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| multi-style-generation | local | 把「一个小风格清单」扩成「几十种可选、可多选、批量生成」的功能时，必须同步处理的成本闸门、离线塌缩、并行加速三件事。适用于：文案生成器加风格 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| poster-design-studio | local | 将一段活动描述、一张产品照片或品牌参考图，转化为抓人眼球的活动海报、宣传 banner 或社交媒体配图。这款 AI海报设计与制作工具生成图片 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| whiteboard-animation-maker | local | 把一个概念、一份写好的口播稿，或一条要对标的社媒视频，变成 1080×1920 竖屏白板手绘讲解片（白底黑线）。这个白板动画制作工具支持汉字 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| beatra | local | 通过同一个AI创作工具完成AI图片、视频、音乐与语音创作，查找公开社交数据，编辑视觉成果，并集中查看和管理生成资产。Beatra 全能创作支 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| beatra-ai-music-creator | skillhub | 从一个主题、一句歌词、一段画面或参考音频开始，用AI音乐生成和AI作曲制作原创歌曲、歌词成曲、纯音乐、BGM、视频配乐、品牌音乐、广告歌、播 | `skillhub install beatra-ai-music-creator --namespace beatra-ai` |
| short-drama-score-pack | local | 为竖屏短剧一次做出8到15首原创短剧配乐。这个短剧BGM和短剧配乐工作室会按紧张、恋爱、喜感和虐心写出可循环的情绪床，音乐归你所有、可直接商 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| douyin-video-skill | local | 抖音短视频双路径生产体系（单 Skill 版）。Path A[付费·高质量]：策略大脑→（可选：素材混剪/AI高光提取）→脚本优化→AI生图 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| jilaoshi-video-workflow | skillhub | 吉老师中文口播混剪视频完整制作工作流。收到定稿文案和配音后，用于全网搜索相关视频素材、名人采访优先匹配、逐字字幕对齐、素材去重防循环、9:1 | `skillhub install jilaoshi-video-workflow --namespace user_51873b1f` |
| 全师傅的剧本工作站 | skillhub | AI短剧剧本全流程创作技能，专为AI制作管线优化，内容导向强情绪·快节奏·高频反转。启动时通过交互式使用向导精确收集创作需求（市场定位、制作 | `skillhub install xq359 --namespace user_8a0df270` |

## 推荐工作流
1) 图片：gpt-image-2-5-studio / ai-photo-restyler / multi-style-generation；
2) 视频：first-last-frame-video / whiteboard-animation-maker / douyin-pro / jilaoshi-video-workflow；
3) 音乐/配乐：beatra / beatra-ai-music-creator / short-drama-score-pack；
4) 海报：poster-design-studio；
5) 剧本：xq359 剧本工作站。

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

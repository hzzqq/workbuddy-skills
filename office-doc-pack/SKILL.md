---
slug: office-doc-pack
name: 办公文档包
displayName: 办公文档包
version: 1.0.0
license: MIT
category: office
description: |
  把 PPT 生成 / Word 模板 / WPS 全家桶 等办公文档 skill 收敛成一个入口。
tags: [组合包, bundle, office]
---

# 办公文档包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
办公文档类 skill 分散。本包统一入口，按「PPT / Word / WPS 四引擎」分流。

## 包含的成员（3 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| ppt-generator | local | 生成专业PPT演示文稿。当用户要求创建PPT、幻灯片、演示文稿时使用。适用于工作汇报、项目展示、商业计划、培训课件等场景。 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| docx-template-dynamic-paragraphs | local | 用 python-docx 对「固定 docx 模板 + 只换文字/图片、保留原排版」的生成器， 把某个区块的正文段落改成可动态增减（用户想 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| WPS Office 全家桶 | local | WPS Office 全家桶 - 四引擎（WPS/MS Office/LibreOffice/纯Python）智能识别用户已安装软件，纯Py | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
1) 生成 PPT 用 666-v2（ppt-generator）；
2) Word 动态段落模板用 docx-template-dynamic-paragraphs；
3) 需要本地 Office/WPS/LibreOffice 四引擎时用 wps-office-suite。

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

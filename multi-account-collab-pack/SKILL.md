---
slug: multi-account-collab-pack
name: 多账号协作进度同步包
displayName: 多账号协作进度同步包
version: 1.0.0
license: MIT
category: collaboration
description: |
  把多账号协助开发同一项目所需的「文件同步 / 资产迁移 / 备份 / 记忆保留 / 知识库 / 训练数据合规 / 多 Agent 协作」收敛成一个入口，可跨账号一键导入。
tags: [组合包, bundle, collaboration]
---

# 多账号协作进度同步包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
多账号（或多机）协助开发同一项目时，环境不一致、进度不同步、资产/上下文在切换账号时丢失。本包把 8 个免费、无付费回调的协作类 skill 收敛成一个入口。

## 包含的成员（8 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| 文件同步助手 | skillhub | 用于在 Windows、macOS、Linux、NAS 或家庭服务器之间同步工作文件、照片原片、笔记、项目资料和共享目录，也用于排查文件不同 | `skillhub install desktop-file-sync-cn --namespace user_b4da0893` |
| 云盘运维 文件同步 团队协作 | skillhub | 用命令行高效管理 Dropbox 文件、共享链接与团队空间，支持脚本自动化与 CI/CD 集成。 | `skillhub install dbxcli --namespace org-k6bcf2fv` |
| WorkBuddy迁移助手 | skillhub | WorkBuddy 国内版跨机器资产迁移助手（适配客户端 5.7.6）。在更换电脑时，将旧机器的全部个人资产（skills、memory、c | `skillhub install workbuddy-migration-assistant --namespace user_73de2035` |
| backup-yourself | skillhub | Back up the entire agent memory system of the current WorkBuddy accoun | `skillhub install backup-yourself --namespace user_12d85a03` |
| memory-manager-v2 | skillhub | AI 记忆加速器 / Token 节流阀：以「更小、更准、更省」为目标管理 .workbuddy/memory/。 核心能力：治理闭环（go | `skillhub install memory-manager-v2 --namespace indiv-aakook` |
| 知识库 | skillhub | 【知识库】把用户手上的本地文件夹（客户档案、货盘表、朋友圈素材、课程逐字稿、代理政策历史版本、直播复盘…）变成 AI 能稳定查、稳定放、稳定 | `skillhub install xy-vault --namespace user_93c42d4c` |
| 训练数据版权护栏（Data Rights Guard） | skillhub | 当用户说『爬的数据能拿来训练吗』『数据集没写许可证』『微调数据版权合规吗』『怎么确认数据能商用』，或在用数据(爬取/购买/公开集/用户授权) | `skillhub install data-rights-guard --namespace user_8a3569c1` |
| multi-agent-project-builder | skillhub | 多 Agent 项目协作工厂 - 一键实现智能分工完成互联网项目 | `skillhub install multi-agent-project-builder --namespace user_29729038` |

## 推荐工作流
1) 用 dbxcli 或 desktop-file-sync-cn 把项目目录同步到各账号机器，保证源码/数据一致；
2) 换账号前用 backup-yourself + workbuddy-migration-assistant 备份/迁移 skill 与配置；
3) memory-manager-v2 保留跨会话上下文，xy-vault 沉淀项目知识；
4) 每次收尾用 progress-doc 写进度、handoff-doc 出交接包、session-archiver 归档会话，另一账号拉起即可续做；
5) 用 multi-agent-project-builder 在单账号内拆分任务并行；
6) 任何要进训练集的数据先过 data-rights-guard 确认许可与商用权限。

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

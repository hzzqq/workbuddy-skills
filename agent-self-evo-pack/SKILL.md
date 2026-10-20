---
slug: agent-self-evo-pack
name: Agent自我进化包
displayName: Agent自我进化包
version: 1.0.0
license: MIT
category: agent
description: |
  把自我改进 / 自我学习 / 自我调试 / 自驱开发 / 自主研究 / 超级能力约定 等「让 Agent 自己变强」的 skill 收敛成一个入口。
tags: [组合包, bundle, agent]
---

# Agent自我进化包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
这类 skill 都围绕「Agent 自我提升」，概念重叠。本包收敛入口，避免同时加载多个进化循环互相干扰。

## 包含的成员（10 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| active-self-improvement | local | Active self-improvement loop that reads learnings, errors, batch outpu | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| ai-evolution-engine | local | AI自我进化引擎 - 基于SEA循环(Sense-Evolve-Act)的AI成长系统。自我评估、学习引擎、进化机制、协作学习、安全保障。 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| auto-learn-skill | local | 自动学习技能 - 从对话中自动提取知识并创建技能。基于Memento-Skills的Read-Write循环机制。适用于AI Agent自进 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| autoimprove | local | Autonomous optimization loop that improves any measurable thing. Point | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| autoresearch | local | Autonomous experiment loop for AI agents. Use when the user wants to r | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| self-debug | local | 自我排查与变通框架。当 AI 遇到异常结果、工具报错、数据缺失、重复失败时，按 Layer 1-6 逐步自己排查。不要直接问用户，先走完整个 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| self-driving-dev | local | 自主驱动的开发自循环 skill：在本项目里自己找活干、自己定方案、自己实现、自己验收， 反复循环；每一步都自行决策，无需人工批准。 北极星 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| self-evolving-agent | local | Build a goal-driven self-learning loop for OpenClaw and coding agents. | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| using-superpowers | local | Use when starting any conversation - establishes how to find and use s | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| solo-pipeline | local | Launch automated multi-skill pipeline that chains skills into a loop.  | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
按场景只启用一个主循环：日常自我改进用 active-self-improvement；从对话萃取知识用 auto-learn-skill；遇错自查用 self-debug；长任务自驱用 self-driving-dev；做实验循环用 autoresearch；新会话起点用 using-superpowers 定纪律。

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

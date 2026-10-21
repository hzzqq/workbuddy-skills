---
slug: prompt-humanizer-pack
name: 提示词与去痕包
displayName: 提示词与去痕包
version: 1.0.1
license: MIT
category: prompt
description: |
  把提示词工程 / 提示词大师 / 中文 AI 去痕 / 去 AI 味 等 skill 收敛成一个入口。
tags: [组合包, bundle, prompt]
---

# 提示词与去痕包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
去痕类有两个几乎重复的版本（unclecheng 两版），提示词类也有多个。本包收敛，去痕只保留一版即可。

## 包含的成员（5 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| prompt-discipline | local | 结构化 prompt 训练与自查。当用户要写提示词、抱怨 AI 干活慢/跑偏/结果差、想训练"把模糊需求翻译成机器指令"的方法论、需要 pr | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 提示词大神 | local | 一键铸造天花板级提示词。说出需求或目标，即深度挖掘真实意图，产出五层架构完整、自带100分制评分门禁、可直接投喂任意大模型的大神级提示词。当 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 中文 AI 去痕工具 | local | 中文 AI 文本去痕 Skill。诊断并修复 24 种 AI 写作痕迹，按「为什么 AI 会这样」的 6 组病因组织， 附可直接运行的零依赖 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| humanizer | local | 去除文本中的AI写作痕迹，让文字读起来更像人类写作。当用户要求'去AI味'、'降AI味'、'让回复更像人话'、'润色'、'改写得更自然'时使 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| humanizer | local | 去除文本中的AI写作痕迹，让文字读起来更像人类写作。当用户要求'去AI味'、'降AI味'、'让回复更像人话'、'润色'、'改写得更自然'时使 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
1) 写/训提示词用 prompt-discipline + prompt-master；
2) 去 AI 味用 humanizer-zh-pro（或 unclecheng-reduce-ai-perception-v2，二选一，勿同时启用）。

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

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

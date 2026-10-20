---
slug: eng-guardrails-pack
name: 工程护栏纪律包
displayName: 工程护栏纪律包
version: 1.0.0
license: MIT
category: engineering
description: |
  把自研的「AST 护栏 / 双机 git 安全 / 诚实交付 / 静默缺陷狩猎 / 数据源时效 / 长任务判活 / skill 安全审计」等工程纪律 skill 收敛成一个入口。
tags: [组合包, bundle, engineering]
---

# 工程护栏纪律包

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
这类 skill 是老板的工程签名风格（防回退、反静默假死、诚实红线）。散落多处不便记忆，本包统一入口，便于在新项目/新账号复用同一套纪律。

## 包含的成员（16 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| AST防回退护栏 | local | 用 AST 写「源码级防回退护栏」测试，把项目约定/安全基线锁死。适用于：约定靠自觉易回退、错误不崩溃但语义错（如配色反转）、review  | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| AST安全改写 | local | 用 AST 安全改写 Python 源码（批量补参数、插入配置、改调用）时，规避「字节偏移 vs 字符偏移」错位坑与「双逗号」语法坑。适用于 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 双机Git安全 | local | 双机/多 agent 协作同一 git 仓库时的安全红线 + 护栏。适用于：任何在"同账号同仓、双机或同工作树多 agent"仓库上做 gi | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 上下文串味护栏 | local | 多实体内容生成系统里的「串台/串味」缺陷——生成出来的内容对应的是上一个实体（上一部电影/上一只股票/上一个客户），而不是当前输入的那个。适 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 静默缺陷狩猎 | local | 用「可证伪的侦察 + 一轮一缺陷」的 SOP 在既有代码库里找并修真实缺陷（尤其「不崩溃但语义错」的静默失败家族），每轮交付修复+定向回归+ | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| AI交付前自检 | local | 交付前伪阻断 / 缓干闸门（通用行为级纪律）。任何一次向用户交付结果之前（present_files、写最终总结、下结论、状态汇报、向用户提 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 生成文案质量护栏 | local | AI 文案/内容生成器的质量护栏与诚实自评分。当项目里出现「外部数据 → 模板/模型 → 成稿（docx/网页/推送）」且用户抱怨"文案垃圾 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| LLM内容规则落地 | local | 把一个「内容规则」可靠地落进多路径 LLM 文案生成系统（AI 单字段 / AI 整块 / 离线兜底 / 数据驱动自动成稿 / 质量自检 / | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 数据源时效护栏 | local | 数据源时效性与停更（stall）护栏。当项目存在「多个外部数据源 → 落盘 → 驱动决策/报告」的链路，且出现过「数据悄悄停更、系统却照常给 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 长任务判活 | local | 长任务（训练/回测/批量作业）在后台启动后，正确判活、避免「静默假死」误判与「静默真死」漏判。适用于：启动 CPU 训练/回测/构建等耗时任 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| skill-pack-json | local | 将本机已安装的 skill（用户级 ~/.workbuddy/skills/<name>/ 或项目级 .workbuddy/skills/< | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| skill-safe-install | local | 带校验和（sha256）与外部安全审查的 skill 安装/卸载工具。用于"引入外部 skill"时： 先对安装包做 P0/P1/P2 安全 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| Skill安全扫描 | local | Scan Clawdbot and MCP skills for malware, spyware, crypto-miners, | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 衍生资源发布校验 | local | 生成/扫描「衍生资源」（模板文件、默认配置、注册表、清单、构建产物）时的三道护栏：默认项必须写死不能靠排序、校验必须调用真正使用它的那段代码 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 神模块拆分 | local | 当项目里出现 1000+ 行的巨型模块（god module）需要拆分时，用本 skill 的「叶子子模块 + re-export」法。 核 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 批量皮肤迁移 | local | 给「N 个零依赖单文件 HTML 应用」批量统一皮肤/主题，并修复「变量命名分裂 + 换肤静默失效」类真实缺陷。适用于：用户说「把全站/所有 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
1) 接手/拆分代码前用 ast-invariant-guard + ast-safe-edit 锁死约定；
2) 双机/多 agent 同仓用 dual-machine-git-safety；
3) 交付前用 delivery-no-pseudoblock 过伪阻断闸门；
4) 排查「不崩但错」用 silent-failure-defect-hunt；
5) 外部数据链用 data-source-staleness-guard + long-running-task-healthcheck；
6) 装/发包用 skill-safe-install + skill-scanner + derived-artifact-verify-publish。

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

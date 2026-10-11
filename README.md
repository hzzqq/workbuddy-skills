# WorkBuddy 自研 Skill 集合

本仓库用于从 GitHub 导入并发布到 SkillHub 技能广场。
每个子目录即为一个独立 skill，目录名 = slug，内含 `SKILL.md` 及配套脚本/资源。

## 已放入仓库的 Skill（共 10 个）

| slug | 显示名 | version | 一句话价值 |
|---|---|---|---|
| `dev-supervisor` | 自驱进度监控 | 1.0.0 | 监督所有 self-driving-dev 自驱项目的开发进度：只读各项目 .workbuddy/self-driving/state.json， |
| `force-hy3-model` | Hy3 模型强制器 | 1.0.0 | 强制所有"自动生成 / 自主执行"的任务使用 Hy3 模型（近期 Hy3 免费，为老板省成本）。 |
| `game-play-insight` | 游戏数据洞察 | 1.0.0 | 网页小游戏游玩数据收集与反馈闭环 skill。自动采集玩家行为（浏览器埋点 SDK + 本地收集服务），汇总成结构化洞察报告，并生成可直接交给「开发游戏的 AI（Hy3 / WorkBuddy）」的改良指令包。触发词：收集游玩数据、生成玩家反馈报告、把数据发给开发AI、改进游戏、游戏数据洞察。 |
| `handoff-doc` | 交接文档 | 1.0.0 | 将当前对话中最有价值的信息（关键结论、决策、代码、重要规则、待办、进度）提炼成结构化交接文档（.md）， |
| `progress-doc` | 进度文档 | 1.0.0 | 用「进度文档」代替「长会话」。为每个任务/领域维护一份本地磁盘 Markdown 进度文档，新会话只需说「先读进度文档」即可轻量恢复上下文；支持 update 实时增量写回，做到删 WorkBuddy 空间/会话也不丢项目上下文。触发词：进度文档、先读进度文档、读进度文档、开个进度文档、更新进度文档、增量更新进度、实时写回进度、收尾写回、progress doc、恢复上下文、任务文档、续上、接上次、删空间不丢上下文。 |
| `self-driving-dev` | 自驱开发循环 | 1.0.0 | 自主驱动的开发自循环 skill：在本项目里自己找活干、自己定方案、自己实现、自己验收， |
| `session-archiver` | 会话归档管家 | 1.0.0 | 自动化任务的会话归档管家。每当新建一个自动化任务(automation)会话时调用本 skill，登记会话、按"同一时期最多保留 3 个活跃自动化会话"策略定期归档并关闭最旧会话，关之前先调 progress-doc 把上下文增量写回进度文档，做到零丢失释放内存/CPU。核心保证：删 WorkBuddy 空间/会话也不丢项目上下文（进度文档在本地磁盘）。默认每次新建自动化都调用，除非用户明确说"不调用"。触发词：归档会话、关旧会话、会话太多、释放资源、删空间不丢上下文、会话管理。 |
| `skill-pack-json` | Skill 打包器 | 1.0.0 | 将本机已安装的 skill（用户级 ~/.workbuddy/skills/<name>/ 或项目级 .workbuddy/skills/<name>/） |
| `skill-safe-install` | Skill 安全安装 | 1.0.0 | 带校验和（sha256）与外部安全审查的 skill 安装/卸载工具。用于"引入外部 skill"时： |
| `unstick` | 任务解卡器 | 1.0.0 | WorkBuddy 任务解卡器 / 刷新器。当 WorkBuddy 跑任务"卡住不动、不干活、进度停滞、 派活了却没反应"时，一键诊断并清理头号元凶——孤儿锁（agent 已死但 .drive_lock 残留， 且被每小时自动化反复盖新时间戳，导致项目被"假新鲜锁"永久跳过）。按 state.json 停滞 时长精准区分"真卡死"与"真在干活"，只清卡死的、保留活跃的；顺带清 git 锁残留、报端口 占用。触发词：刷新 workbuddy、workbuddy 卡住了、任务卡住、解卡、解决卡住、项目不动了、 派活没反应、清死锁、unstick、refresh。 |

## 尚未放入的 Skill（需清理后再发）

| slug | 原因 |
|---|---|
| `drive-all` | SKILL.md 含 `E:////project` 等个人路径，需泛化/脱敏 |
| `wechat-bridge` | 含 secret 配置说明，需确认发布为模板安全后再入仓 |

## 导入发布步骤

1. 打开 SkillHub → 发布新技能 → 选择 **"从 GitHub 导入"**
2. 选择仓库 `hzzqq/workbuddy-skills`
3. 选择要导入的子目录（skill slug）
4. 确认 frontmatter 信息并发布

## 本地维护

```bash
skillhub publish <skill目录> --dry-run   # 本地预检
```

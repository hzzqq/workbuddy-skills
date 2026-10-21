# SkillHub AI 评测潜力报告（2026-10-21）

> 数据源：`skillhub skill evaluation <slug> --namespace user_f937ad5e --json`（平台 AI 评测，13/29 已生成报告；task-unstuck 平台尚未生成评测 404）。
> 综合分 = 15 个评测子项均分（5 大维：adaptability / convention / effectiveness / reliability / trust）。
> 用途：按平台同一评判口径横向看 29 个自研 skill 的质量与潜力，指导迭代优先级。

## 一、综合排名（已评测 13 个）

| 排名 | skill | 综合分 | 强项（≥4.6） | 主要短板 |
| --- | --- | --- | --- | --- |
| 1 | progress-doc（进度文档） | **4.64** | func 5.0、boundary/trigger 4.5-5.0、errorHandling 4.5 | 缺示例文件、无测试；文档漏写 cmd_read 子命令 |
| 2 | shepherd-sentiment（牧羊人指标） | **4.55** | accuracy 4.8、creativity 4.8、boundary/trigger/domestic 全 5.0 | 缺 README 快速入口；硬编码默认路径；功能面窄（仅 1 条有效规律） |
| 3 | session-archiver（会话归档管家） | **4.46** | usability 4.8、accuracy/completeness/creativity 4.7 | 硬编码 `C:/Users/Administrator/...`；关会话依赖手动；无测试 |
| 4 | handoff-doc（交接文档） | 4.43 | usability 4.8、completeness 4.8 | 只有说明无示例，"像半成品" |
| 4 | macro-data（宏观数据） | 4.43 | structure 4.8、domestic 4.8 | **强耦合 StockSignal 仓库**，独立运行弱（壳 skill） |
| 4 | ladder-resonance（连板龙头共振） | 4.43 | boundary 5.0、accuracy 4.6 | 缺单元/集成测试；参数校验可加强 |
| 7 | self-driving-dev（自驱开发循环） | 4.39 | 文档理念清晰、trust 5.0 | **SKILL.md 后半截断**；纯文档无代码实现 |
| 8 | planning-with-files（文件化规划） | 4.37 | 模板设计合理 | 引用 `references/manus-principles.md` **缺失**；_meta.json 过简；无测试 |
| 9 | skill-safe-install（Skill安全安装） | 4.31 | 分级风险体系完整、trust 5.0 | 纯正则扫描可被混淆绕过；无签名校验 |
| 9 | drive-all（全机派活扫描） | 4.31 | 锁机制/防雪崩设计扎实 | Python 路径+GitHub 用户名**硬编码**；Windows 专属；依赖 gh 未做检查 |
| 11 | futures-combo（期货组合分析） | 4.22 | completeness 4.8、风控红线清晰 | **只有说明书没有代码**，无法独立运行；无示例输出 |
| 12 | skill-scanner（Skill安全扫描） | 4.13（后台显示 4.2） | CLI 参数清晰、exit code 设计好 | **文档提到 streamlit_ui.py 但包里没有**（文档-实现不一致）；未说明检测局限/误报率 |
| — | task-unstuck（任务解卡器） | 暂无评测 | — | 平台未生成报告（404） |

## 二、收敛短板（全员共性 = 迭代杠杆点）

1. **antiPatternFaq（反模式/FAQ）全员最低**（3.3–4.5）：几乎所有 skill 都缺"FAQ + 反模式 + 使用示例"章节。
2. **零测试覆盖**：13 个里 0 个带单元测试。
3. **硬编码路径/用户名**：drive-all、session-archiver、shepherd-sentiment 均被点名 → 改环境变量默认值。
4. **文档-实现不一致**：skill-scanner（streamlit_ui.py 不存在）、progress-doc（cmd_read 未写进文档）、planning-with-files（references 文件缺失）。

## 三、按 ROI 排序的改进清单（升版重发，更新旧版）

| 优先级 | 动作 | 影响分 | 预期提升 |
| --- | --- | --- | --- |
| P0 | skill-scanner：删除 streamlit_ui.py 描述或补文件 + 写明检测局限（正则混淆误报率） | 摘掉垫底 | 4.13 → 4.4+ |
| P0 | self-driving-dev：补全被截断的 SKILL.md 后半段 | 完整性 | 4.39 → 4.6 |
| P0 | planning-with-files：补 references/manus-principles.md | 消失引用 | 4.37 → 4.5 |
| P1 | progress-doc：文档补 cmd_read 说明（已是第 1 名，补齐冲 4.8） | 巩固第一 | 4.64 → 4.8 |
| P1 | 全员补 FAQ/反模式/使用示例章节（antiPatternFaq 从 3.x → 4.5） | 全员 +0.2~0.3 | — |
| P1 | session-archiver / drive-all / shepherd-sentiment：硬编码路径 → 环境变量默认 | adaptability | — |
| P2 | futures-combo：补可运行脚本 + 示例输出（说明书 → 工具） | func | 4.22 → 4.5+ |
| P2 | macro-data：核心取数逻辑内置化（解耦 StockSignal） | reliability | — |
| P2 | ladder-resonance / skill-safe-install：补单元测试 | stability | — |

## 四、关于「Skill安全扫描 19千下载 + AI 评分 4.2」

- **AI 评分 4.2 = 平台评测总分**（本次实测子项均分 4.13，口径差异为四舍五入/权重）。注意：**它是 13 个已评测 skill 里分数最低的**。
- **19 千下载无法从 CLI 确证**（rankings 接口无统计字段）。合理假设：
  1. 「安全扫描」是刚需品类 + 通用名，吃平台搜索/AI 推荐流量；
  2. 平台可能按 publicSlug 聚合计数或计入评测管线自身的包拉取；
  3. 以后台真实数据为准。
- **核心洞察：下载量 ≠ 质量**。下载量由品类需求驱动（安全 > 宏观 > 情绪），质量榜第一的 progress-doc 反而是普通品类。运营上：用 skill-scanner 这类刚需品引流，用 progress-doc / shepherd-sentiment 这类高分品立口碑。

## 五、结论

- 自研底盘质量整体过硬（13 个均分 4.36，trust 维度普遍 4.5–5.0），短板高度收敛在 **FAQ/示例/测试/硬编码** 四件事上，全是低成本低风险的确定性修补。
- 按第三节清单做 2–3 轮「补文档 + 补示例 + 升版重发」，榜单中上游（≥4.4）可再上一档。

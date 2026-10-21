---
name: data-source-staleness-guard
description: 数据源时效性与停更（stall）护栏。当项目存在「多个外部数据源 → 落盘 → 驱动决策/报告」的链路，且出现过「数据悄悄停更、系统却照常给出结论」的静默失败时使用。覆盖 lag-based stale 与 advance-based stall 两种判定的区别、SQLite 观测表、看板/徽标接线、以及必须配套的可证伪测试。
agent_created: true
slug: data-source-staleness-guard
displayName: 数据源时效护栏·时效
version: 1.0.1
license: MIT
---

# 数据源停更 / 时效护栏

## 何时用
- 决策、报告或模型依赖多个外部数据源（行情、因子、快照、事件池…）
- 出现过：数据停在某一天，系统却照常输出结论（**静默失败**，最危险的一类缺陷）
- 需要「在彻底过期之前就提前告警」

## 核心概念：stale ≠ stalled（这是本 skill 的要点）

| 判定 | 计算方式 | 含义 | 阈值示例 |
|---|---|---|---|
| stale（滞后） | `today - as_of` | 数据离今天有多远 | warn 4 天 / stale 8 天 |
| **stalled（停更）** | `today - (as_of 最后一次变大的那天)` | 这个源**停止推进**了吗 | 5 天 |

关键点：一个日更源冻结 5 天时，`lag` 也才 5 天（还没到 stale 阈值 8），
但它**已经在坏掉**。stalled 是 stale 的提前量。
**只做 lag 判断等于半套护栏**——等它变红时损失已经发生了。

## 实现步骤

1. **注册源清单**：`DATA_SOURCES = [{key, name, probe}]`，probe 负责取该源真实的 `as_of`
   （必须是**权威数据日**，不是 `now()`；取不到就返回 None → unknown，不要拿快照日期兜底）。
2. **持久化观测**：SQLite 表 `(source_key, observed_at, as_of, status, lag_days)`，
   每次看板渲染 / 快照落盘时 `record_health_observation()` 插一行。
   **写入失败静默返回 0**——绝不能因为"记录失败"影响主流程渲染。
3. **停更判定** `detect_stall()`：
   - 按 `observed_at` **ASC 回溯**（⚠️ DESC 会退化成"多久没看"，见下方坑）
   - 只在 `as_of` **严格变大**时更新 `last_advance_date`
   - 观测窗口内从未推进 → **退化为从首次观测算起**，否则永不报警
   - `stalled = (frozen >= STALL_DAYS) and (max_as_of < today)`
   - 无历史 / 异常 → `stalled=False`（不误报）
4. **合并输出**：`health_rows_enriched()` = 健康行 + `stalled` / `frozen_days`。
5. **接线到三处**，缺一不可：
   - **刷新计划**：停更源即使 `status != stale` 也要纳入（提前触发刷新）
   - **SLA 看板**：逐源 as_of / 滞后 / 状态 / 停更 卡片
   - **决策面板徽标**：显式写出「某源 as_of=xxxx，滞后 N 天，已降权 X%」

## 坑（真实踩过，勿回退）

- ⚠️ **DESC 遍历是错的**：`ORDER BY observed_at DESC` 后取第一条 `as_of == max_as_of`
  的行，拿到的是**最新一次观测**，于是 `frozen` 变成「距上次观测天数」。
  一个 10 天没推进的源，只要刚被看过一次就判不出停更。
  **必须 ASC 回溯，找 as_of 最后一次"严格变大"发生在哪次观测。**
- ⚠️ **全程未推进的源永不报警**：若观测窗口内 `as_of` 一直是同一个值，
  `last_advance` 会跟着最新观测走 → frozen 永远很小。必须用首次观测日期兜底。
- ⚠️ **决策口径**：陈旧源必须在决策输出里**显式降权并把降权幅度写出来**，
  不能静默按满权重计算（那正是静默失败）。
- ⚠️ **不要用快照 date 兜底 as_of**：调用方可能传历史日期做回补，会造成假陈旧/假新鲜。

## 必须配套的测试（可证伪，不是空转）

- 冻结源 → `stalled=True`
- 正常日更源 → `stalled=False`（**不误报**，这条最容易被漏掉）
- 无观测历史 → `stalled=False`
- `record_health_observation` 重复调用不炸；写失败返回 0 不抛
- 停更源进入 `build_refresh_plan`（即便 status 只是 warn）
- **突变验证**：把 ASC 改回 DESC，测试**必须变红**；不变红说明断言是空转的

## 验收清单

- [ ] 上述测试全绿
- [ ] 页面冒烟通过（新页面通常会被自动发现）
- [ ] 决策面板肉眼可见「as_of / 滞后 N 天 / 已降权」，而不是只有一个笼统的"数据可能过期"

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

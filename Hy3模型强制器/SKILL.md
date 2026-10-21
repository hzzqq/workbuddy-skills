---
name: Hy3 模型强制器
description: |
  强制所有"自动生成 / 自主执行"的任务使用 Hy3 模型（近期 Hy3 免费，为老板省成本）。
  触发场景：我（AI）用工具创建或修改任何定时自动化（automation）时；用户说"检查任务是否都用 hy3""把任务切到 hy3""强制 hy3""所有自动任务用 Hy3"等；
  self-driving-dev 等自主循环派生独立执行的任务时。也作为常驻策略：新建任何 automation 时 model_id 一律设 hy3。
  本 skill 安装于用户级目录，跨项目通用。
agent_created: true
slug: force-hy3-model
version: 1.0.1
displayName: Hy3模型强制器·模型
---

# 强制 Hy3 模型（force-hy3-model）

## 背景 / 为什么
- 近期 **Hy3 模型免费**。老板要求：以后所有"自己生成的任务"——包括**定时自动化 / self-driving 自主循环 / 派生 agent 任务**——一律强制走 Hy3，节省成本。
- Hy3 在自动化配置里的字段取值：
  - `model_id = "hy3"`（数据库 `automations.model_id` 列；`automation_update` 工具参数 `modelId:"hy3"`）
  - `model_is_thinking`：默认 `0`（非推理）；仅当任务确实需要复杂推理时才设 `1`。

## 强制规则（MUST — 每次都遵守）
1. 我用 `automation_update`（mode=create）创建任何新 automation 时，**必须**带 `modelId:"hy3"`。除非用户当场明确指定别的模型。
2. 修改已有 automation（mode=update）时，若发现其 model 不是 hy3，**顺手切成 hy3** 并在回复里告知。
3. self-driving-dev 等自主循环若涉及派生独立执行的任务 / 定时触发，模型选择同样默认 hy3。
4. **唯一例外**：用户明确指定用其它模型；或任务明确需要 hy3 不具备的能力（需说明原因）。

> 这条规则也已写入用户级 `~/.workbuddy/MEMORY.md`，保证每次会话注入、常驻生效。skill 提供的是审计 / 批量切换的可执行流程。

## 触发时的操作

### A. 创建新 automation（最常见）
直接在 `automation_update(mode="create", ...)` 里加 `modelId:"hy3"`（`modelIsThinking` 视需要，默认省略＝非推理）。

### B. 审计 + 批量切换（用户说"检查/切换任务到 hy3"）
1. **只读审计**——列出所有存活自动化及其 model_id（跳过已 deleted 的）：
   ```bash
   "C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe" -c "import sqlite3,os;c=sqlite3.connect(os.path.expanduser('~/.workbuddy/workbuddy.db'));[print(r) for r in c.execute(\"SELECT id,name,status,model_id FROM automations WHERE deleted_at IS NULL\")]"
   ```
2. 找出 `model_id != 'hy3'`（通常是 `'auto'`）的存活自动化。
3. **逐个用工具切换**（不要直接改 db，避免绕过工具校验）：
   `automation_update(mode="update", id="<id>", modelId="hy3")`
4. 汇报改了哪些、跳过哪些（已是 hy3 / 已删除）。

## ⚠️ 跨账号限制（重要，已踩坑）
- `automation_update` 工具**只能操作当前登录账号（`owner_user_id`）名下的自动化**。
- 对**别的账号**创建的自动化调用 update，会报 `Automation not found`（即使 db 里存在且未删除）。
- 审计脚本能看到**所有** owner 的自动化，但工具切换只能覆盖**当前 owner** 的那部分。
- 遇到跨账号的自动化想切 hy3：需在**对应账号的会话**里操作；或经用户明确授权后再考虑直接改 db（默认不越权）。
- 判断归属：审计脚本加查 `owner_user_id`，与当前会话能 `list` 出来的对比即可。

## 护栏（安全）
- 审计查询是**只读**；切换**只改 model_id**，绝不动 prompt / schedule / cwds / status。
- 已 `deleted_at` 非空的自动化不管。
- 内容推送类任务（新闻 / 电影 / 每日一条等）切 hy3 时，`model_is_thinking` 保持原值即可，无需强开 thinking。
- 批量切换用 `automation_update` 工具，**禁止**用 `sqlite3` / `rm` / shell 直接改写数据库（与系统对 automation 的删除/修改规则一致）。

## 备注
- 若哪天 Hy3 不再免费或老板改主意，删掉 MEMORY.md 里对应章节 + 停用本 skill 即可，存量自动化的 model_id 可再批量切回 `auto`。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

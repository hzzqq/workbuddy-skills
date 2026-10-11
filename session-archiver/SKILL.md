---
name: session-archiver
description: 自动化任务的会话归档管家。每当新建一个自动化任务(automation)会话时调用本 skill，登记会话、按"同一时期最多保留 3 个活跃自动化会话"策略定期归档并关闭最旧会话，关之前先调 progress-doc 把上下文增量写回进度文档，做到零丢失释放内存/CPU。核心保证：删 WorkBuddy 空间/会话也不丢项目上下文（进度文档在本地磁盘）。默认每次新建自动化都调用，除非用户明确说"不调用"。触发词：归档会话、关旧会话、会话太多、释放资源、删空间不丢上下文、会话管理。
slug: session-archiver
version: 1.0.0
displayName: 会话归档管家
---

# 会话归档管家（session-archiver）

## 核心问题
WorkBuddy 的会话历史是**云端保存**的——关掉会话**不会丢失记录**，但会释放巨大的内存和 CPU。
现实里：许多自动化任务(automation)不断建立新会话却从不关闭，资源被悄悄吃光。

## 🛡️ 核心保证：删 WorkBuddy 空间 / 会话，也绝不丢项目上下文
本 skill 与 `progress-doc` 协同，给出铁一般的保证：
- **上下文固化在本地磁盘进度文档**（`progress-doc` 的 `.workbuddy/progress/*.md`），**不依赖 WorkBuddy 云端会话/空间**。
- 即使删掉会话、关闭空间、清空云端历史，**进度文档仍在磁盘上**，新会话/新空间说一句「先读进度文档」即可秒恢复。
- 归档 = 先跑 `progress_doc.py update` 把最新进展落盘，再关会话。关的是「内存/CPU 占用」，不是「记忆」。
- 一句话：**会话会死，文档长在；归档即备份，删除零丢失。**

## 归档 = 先存文档，再关会话（零丢失）
关闭会话前**必须**先固化上下文，与 `progress-doc` skill 打通：
1. 若该自动化任务还没有进度文档，先 `progress-doc` 建一份（含上下文恢复要点）。
2. 把当前进度写回进度文档对应段——**用实时增量更新**：
   ```bash
   PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
   SKILL="C:/Users/Administrator/.workbuddy/skills/progress-doc"
   "$PY" "$SKILL/progress_doc.py" update "<任务名>" --note "本次归档进展：..." [--section 已完成|进行中|待办]
   ```
3. 再关闭会话。云端历史仍在，本地资源释放，下次说「先读进度文档」即可秒恢复。

## 核心策略（二选一，默认 rotate）
- **rotate 模式（默认）**：同一时期只保留 **≤3 个活跃自动化会话**；每新增一个，若活跃数 > 3，就归档并关闭**最旧**的那个。
  - 效果天然等价于"每三次自动化任务关闭一次"，且严格保证"只有三个在消耗资源"。
- **onesession 模式**：每个自动化任务独占一个会话，跑完即归档关闭（最干净，但会话切换更频繁）。
  - 切换：`session_registry.py set-mode onesession`

## 触发与调用约定
- **每次新建自动化任务会话时，主动调用本 skill**（这是默认行为，无需用户提醒）。
- 用户说"不调用"/"这次别归档"时，跳过本 skill。
- 调用入口分两步：
  - **登记定义（接线，只做一次）**：创建 automation 后跑 `register ...`，写入 `known_automations`，永不自动关闭。
  - **登记会话（每次运行时）**：自动化真正执行时跑 `run ...`，打开一个会话实例；若活跃会话 > 上限（默认 3），返回 `CLOSE_NOW` 建议关闭最旧会话。

## 使用流程
### 1a. 新建自动化 → 登记定义（接线，只用一次）
```bash
PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SKILL="C:/Users/Administrator/.workbuddy/skills/session-archiver"
"$PY" "$SKILL/session_registry.py" register \
  --id "automation-1784467862596" \
  --name "self-driving-dev 每日自主循环" \
  --workspace "E:/project/hzz/raft-kv" \
  --type automation
```
- 只写入 `known_automations`，不影响 rotate，不会触发关闭。所有"已接线"的自动化都该出现在这里。

### 1b. 自动化运行时 → 登记会话实例（每次触发）
```bash
"$PY" "$SKILL/session_registry.py" run \
  --id "automation-1784467862596" \
  --name "self-driving-dev 每日自主循环" \
  --workspace "E:/project/hzz/raft-kv"
```
- 输出 `CLOSE_NOW: <session_id>`（需关哪个会话实例）或 `NONE`。
- 首次运行时若该自动化不在 known_automations，会自动补登记。

### 2. 若返回 CLOSE_NOW → 先增量写回，再归档关闭
```bash
# a) 确保目标会话有进度文档；把本次最新进展增量写回（实时增量更新 · 零丢失关键）
PROG="C:/Users/Administrator/.workbuddy/skills/progress-doc"
"$PY" "$PROG/progress_doc.py" update "<任务名>" --note "归档前自动写回：本次进展..." [--section 已完成]
# b) 登记为已归档
"$PY" "$SKILL/session_registry.py" archive --id <CLOSE_NOW 的 id> --reason "超过3个活跃会话上限"
# c) 在 WorkBuddy 会话面板关闭该会话（左侧会话列表 → 关闭）
```
> 关闭动作目前走 WorkBuddy 会话面板 UI（无直接 CLI）。skill 负责"判定+增量写回+登记+归档"，UI 关闭一步由 AI 提示用户或在工作流里执行。
> **铁律**：没跑 `progress_doc.py update` 写回就关会话 = 丢上下文，绝对禁止。

### 3. 查看现状
```bash
"$PY" "$SKILL/session_registry.py" list
```

### 4. 切换模式
```bash
"$PY" "$SKILL/session_registry.py" set-mode onesession   # 各跑各的，跑完即关
"$PY" "$SKILL/session_registry.py" set-mode rotate --max 3
```

## registry 存储位置
`C:/Users/Administrator/.workbuddy/session-archiver/registry.json`
（与 skill 目录分离，属运行状态，不随 skill 删除丢失）

## 安全 / 红色警戒
- **绝不**在归档前没写进度文档就关会话——那会丢上下文。
- **绝不**误关用户正在用的主会话（只关 `type=automation` 且登记过的旧会话）。
- 关闭是资源优化动作，不是删除历史；云端记录永恒保留。
- 若 `register` 返回的 `CLOSE_NOW` 会话正是"当前正在执行任务"的会话，不要关它——跳过本轮，等它空闲再关。

## 与其它 skill 的协作
- `progress-doc`：归档前固化上下文（强依赖，零丢失的关键）。
- `using-superpowers`：本 skill 属"工程纪律/资源管理"类，路由层应优先建议调用。

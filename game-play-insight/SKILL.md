---
name: game-play-insight
description: 网页小游戏游玩数据收集与反馈闭环 skill。自动采集玩家行为（浏览器埋点 SDK + 本地收集服务），汇总成结构化洞察报告，并生成可直接交给「开发游戏的 AI（Hy3 / WorkBuddy）」的改良指令包。触发词：收集游玩数据、生成玩家反馈报告、把数据发给开发AI、改进游戏、游戏数据洞察。
agent_created: true
slug: game-play-insight
version: 1.0.0
displayName: game-play-insight
---

# game-play-insight — 网页小游戏游玩数据收集与反馈闭环

## 这是什么
一个给「用 Hy3（WorkBuddy）做的网页小游戏」用的**玩家数据收集 + 反馈闭环** skill。

闭环：
```
游戏内埋点(SDK) → 本地收集服务 → 落盘 .jsonl → 汇总洞察 → 反馈报告 → 交给 Hy3 改良游戏
```

设计目标：**触发极简**（一句话自然语言即可）、**采集零侵入**（游戏只加一行 `<script>` + 少量 `track()` 调用）、**反馈可直接喂给开发 AI（Hy3）**。

## 适用场景
- 你（或 Hy3）做了一个网页小游戏（HTML / JS / Canvas），想看真实玩家怎么玩、卡在哪、哪里有 Bug。
- 想把玩家行为数据整理成报告，交给 Hy3（就是当前这个 AI）去改游戏、做难度 / 体验改良。

## 目录约定
- 采集根目录（可改）：`<你的项目>/.game-telemetry/` 或环境变量 `GAME_TELEMETRY_DIR`。
- 事件落盘结构：`<root>/<gameId>/events/YYYY-MM-DD.jsonl`（每行为一个事件 JSON）。
- 产出文件：
  - `<root>/<gameId>/insight-<date>.json` — 机器可读汇总
  - `<root>/<gameId>/report-<date>.md` — 人读反馈报告
  - `<root>/<gameId>/feedback-<date>.md` — 给 Hy3 的改良指令包

## 工作流

### 第 1 步：接入 SDK（一次性，给游戏加埋点）
把 `scripts/telemetry_client.js` 复制到你的游戏目录，HTML 里加：
```html
<script src="telemetry_client.js"></script>
<script>
  GameTelemetry.init({ gameId: 'my-game', collectorUrl: 'http://localhost:8765' });
  // 关键行为埋点（按需加）
  GameTelemetry.track('level_start',   { level: 1 });
  GameTelemetry.track('level_complete', { level: 1, timeSec: 12 });
  GameTelemetry.track('level_fail',     { level: 3, reason: 'timeout' });
</script>
```
SDK **自动**采集：session 开始 / 结束、页面可见性、运行时报错（`window.onerror` → 直接定位 Bug）。你只需在「想看的点」补 `track()`。

### 第 2 步：启动本地收集服务（一次性后台）
```bash
python <skill>/scripts/game_insight.py start
```
监听 `localhost:8765`，接收浏览器上报并写盘。常驻即可，关掉就停采（数据已落盘的不会丢）。

### 第 3 步：游玩 & 自然语言触发收集
玩家正常玩。之后你对小帮手说：
- **"收集游玩数据"** → 运行 `collect`，汇总成 `insight-<date>.json`
- **"生成玩家反馈报告"** → 运行 `report`，产出可读 Markdown 报告
- **"把数据发给开发AI改进游戏"** → 运行 `feedback`，生成 `feedback-<date>.md`（含具体改良建议 + 验收标准），并提示 Hy3 据此改游戏

### 第 4 步：Hy3 改良
`feedback-<date>.md` 就是给「开发游戏的 AI（Hy3）」的输入。小帮手读取后，直接对游戏代码做改良（调难度、加提示、修报错关卡等），形成闭环。

## 命令参考（也可直接命令行）
```bash
python game_insight.py start                 # 启动本地收集服务（前台；后台请用 run_in_background）
python game_insight.py collect  [--game ID] # 汇总事件 → insight json
python game_insight.py report   [--game ID] # 生成 Markdown 反馈报告
python game_insight.py feedback [--game ID] # 生成给 Hy3 的改良指令包
python game_insight.py demo                  # 造示例数据并跑通 collect→report→feedback（自测）
```
`--game ID` 省略时自动取 `<root>` 下第一个子目录。

## 采集字段
每个事件：`{ ts, session_id, type, gameId, payload, ua, page }`。
- 自动事件：`session_start` / `session_end` / `visibility` / `error`
- 业务事件：游戏自定义。可选通用事件：`level_start` / `level_complete` / `level_fail` / `purchase` / `retry` / `tutorial_skip` 等
- **死亡集中点（无需 level_* 事件也能定位卡点）**：只要发 `death` 事件并在 payload 带 `floor`（地牢类）或 `day`（生存类），分析器会自动统计「玩家死亡最集中的层/天」并据此生成改良建议——适合没有显式关卡概念的游戏。

## 汇总维度（insight json）
- **总览**：session 数、事件数、日期范围、去重玩家（按 session）
- **进度**：各 level 进入 / 完成 / 失败次数、通过率、**卡点（失败率最高环节）**
- **死亡集中点**：`death` 事件的 `floor`/`day` 分布，自动识别「玩家流失最严重的层/天」（领域无关，任何游戏可用）**
- **时长**：平均 / 中位 session 时长、单关耗时分布
- **失败热区**：失败 TOP、error 类型分布（直接定位 Bug）
- **行为序列**：高频路径
- **自动改良建议**：依据阈值（如失败率 > 60% 的关卡 → 建议调难度 / 加提示）

## 安全 & 隐私
- 数据全在**本地**，不上传任何第三方。
- 收集服务只监听 `127.0.0.1`（localhost），不对外暴露。
- 不采集密码等敏感键入；`error` 事件只记 `message` / `stack`，不记敏感输入内容。

## 依赖
- Python 3.8+（仅标准库，无需 pip 安装）
- 浏览器端 SDK 零依赖（纯 JS，无需构建）

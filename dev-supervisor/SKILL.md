---
name: dev-supervisor
description: |
  监督所有 self-driving-dev 自驱项目的开发进度：只读各项目 .workbuddy/self-driving/state.json，
  输出终端 ASCII 进度条 + 本地看板（底部实时进度条），不干扰 AI 干活。
  触发词：监督 AI 开发、看下自驱动进度、起个进度看板、各项目干到第几轮了、迭代进度、开发进度看板。
  与 drive-all（派活）/ unstick（解卡）配套：supervisor 看进度、drive-all 派活、unstick 解卡。
agent_created: true
slug: dev-supervisor
version: 1.0.0
displayName: dev-supervisor
---

# dev-supervisor · AI 开发进度监督

## 这个 skill 解决什么
你让 AI（Hy3 / self-driving-dev）并行啃多个项目，想知道「它们现在干到第几轮了、在做什么、质量如何」。
本 skill 不干扰 AI 干活，只**读**各项目 `.workbuddy/self-driving/state.json`，把进度可视化。

## 进度数据来源
每个被 self-driving-dev 迭代的项目，根目录都有 `.workbuddy/self-driving/state.json`，含：
- `cycle` / `max_cycles` → **进度条主体（百分比）**
- `log[]` → 已完成的任务流（每个有 `task_id` / `new_requirement` / `score` / `ts`）
- `last_task_id` / `last_score` → 当前/最近任务与质量分
- `paused` → 是否暂停；`status` 自动推导：`paused`→已暂停，`cycle>=max`→已完成，否则→运行中

## 两种用法

### 1) 终端快速看（聊天里）
```bash
python scripts/monitor.py bar --root E:\project
```
输出每个项目的 ASCII 进度条 + 最近 3 个任务 + 平均进度。零依赖（仅 Python 标准库）。

### 2) 本地看板（底部实时进度条）
```bash
python scripts/monitor.py serve --root E:\project --host 127.0.0.1 --port 8790
```
启动后浏览器打开 `http://127.0.0.1:8790/`：
- 主区：每个项目一张卡片（进度条 + 最近任务 + 得分 + 任务数）
- **屏幕底部一条固定进度条**：罗列所有项目的迷你进度条，**每 2 秒自动刷新**——AI 干活期间你就能一直看到进度在涨
- 暗色主题，契合 IDE

## 参数
- `--root`：扫描根目录（默认 `E:\project`），会递归找所有含 `.workbuddy/self-driving/state.json` 的项目
- `--host` / `--port`：仅 serve 模式用，看板监听地址（默认 `127.0.0.1:8790`）
- 自动跳过 `.git` / `node_modules` / `.venv` 等重目录，扫描快

## 可选：挂成自动化定期快照
若想脱离浏览器、靠消息推送看进度，可建一个 automation（模型用 hy3）定时跑：
```
python scripts/monitor.py bar --root E:\project
```
让它把输出发给你/写日志。但**实时底部进度条**还是得靠 `serve` 模式开浏览器。

## 护栏
- **只读**：绝不写 state.json、不改任何项目文件，纯监督
- **容错**：state.json 损坏/缺字段的项目单独标红，不影响其他项目
- 扫描根可配，默认 E:\project；机器上换盘符改 `--root` 即可

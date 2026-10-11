---
name: 任务解卡器
description: >-
  WorkBuddy 任务解卡器 / 刷新器。当 WorkBuddy 跑任务"卡住不动、不干活、进度停滞、
  派活了却没反应"时，一键诊断并清理头号元凶——孤儿锁（agent 已死但 .drive_lock 残留，
  且被每小时自动化反复盖新时间戳，导致项目被"假新鲜锁"永久跳过）。按 state.json 停滞
  时长精准区分"真卡死"与"真在干活"，只清卡死的、保留活跃的；顺带清 git 锁残留、报端口
  占用。触发词：刷新 workbuddy、workbuddy 卡住了、任务卡住、解卡、解决卡住、项目不动了、
  派活没反应、清死锁、unstick、refresh。
agent_created: true
slug: unstick
version: 1.0.0
displayName: 任务解卡器
---

# unstick · WorkBuddy 任务解卡器

## 一句话
WorkBuddy 跑任务"卡住不动"时，跑一次这个 skill 就能刷新解卡：清掉卡死项目的
残留锁，让它们下一轮立刻被重新派活；真正在干活的项目原封不动。

## "卡住"的头号元凶：孤儿锁（orphan lock）
drive-all 每小时给派活中的项目写 `.workbuddy/self-driving/.drive_lock`
（含 `ts`/`mode`），干完由 agent 删锁。但当 agent **中途卡死 / 被 cancel /
会话中断**，锁不会被删。更坑的是：**每小时自动化会给这些僵尸项目重新盖一个
新 `ts` 的锁**，于是锁永远"看起来很新鲜"（age 很小），drive-all 的
`--clean-stale`（按 90min 锁**年龄**清）根本清不掉——项目就被当"占用中"一直跳过，
表现就是"WorkBuddy 卡住了、几个项目死活不干活"。

**真正的判定信号 = `state.json` 的停滞时长**（不是锁年龄）：
真在干活的 agent 会持续更新 state.json（每轮写 cycle/log）；
锁还在但 state.json 长时间没更新 = agent 已死 = 孤儿锁，该清。

## 触发方式
老板说以下任意一句，就加载本 skill：
「刷新 workbuddy」「workbuddy 卡住了」「任务卡住了」「解卡」「项目不动了」
「派活没反应」「清死锁」「让卡住的项目重新开工」。

## 用法（脚本）
Python 与脚本绝对路径：
```
PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe
S=C:\Users\Administrator\.workbuddy\skills\unstick\scripts\unstick.py
```

1) **诊断（默认，只读）** —— 先看哪些卡住：
   ```
   %PY% %S% --root E:\project
   ```
   输出每个有锁项目的 `锁age` / `state停滞` / 判定：
   `✅活跃`（保留）、`❌卡死`（孤儿锁，建议清）。

2) **解卡（推荐）** —— 清掉判定为卡死的孤儿锁 + git 锁残留：
   ```
   %PY% %S% --root E:\project --fix
   ```
   只清 `state 停滞 ≥ 30min` 的锁；真在干活的（state 近期更新）一律不动。

3) **强制全刷新** —— 清掉所有锁（不管死活），用于"全部重开"：
   ```
   %PY% %S% --root E:\project --fix --force
   ```

4) **只处理单个项目**：
   ```
   %PY% %S% --path "E:\project\project2" --fix
   ```

5) **调停滞阈值**（默认 30min；一轮开发较久可调大，如 45）：
   ```
   %PY% %S% --root E:\project --fix --stalled-min 45
   ```

## 解卡后：立即重新开工（可选闭环）
清完锁后，卡死项目会在**下一轮每小时自动化**被重新派活。若老板想
**立刻**重开，解卡后紧接着触发 drive-all 派活即可（自然语言「让所有项目继续干活」，
或跑 drive-all 的扫描+派活流程）。unstick 只负责"解卡"，不负责"派活"，职责单一。

## 判定与清理规则
| 判定 | 条件 | `--fix` 行为 |
|---|---|---|
| ✅ active | 有锁 + state 停滞 < 阈值(30min) | 保留，不动 |
| ❌ stalled | 有锁 + state 停滞 ≥ 阈值，或有锁无 state | 清锁 |
| 🔄 force_clear | `--force` 时的所有锁 | 清锁 |
| git 残留 | index.lock / rebase-merge / MERGE_HEAD 悬挂 ≥ 10min | 清理 |
| 端口 8501/5050/26561 | 只读探测 | **只报告，不处理** |

## 安全边界（重要）
- **不杀任何进程**。WorkBuddy 的后台 agent 跑在应用主进程内、不是独立 OS 进程，
  杀进程会误伤 WorkBuddy 本体。解卡只清锁文件 / git 残留。
- 默认只读诊断，`--fix` 才动手；`--force` 才会清活跃锁。
- `paihuo` / `vw_test_*` / `node_modules` 等噪音目录已在扫描中排除。
- 端口占用只提示（可能是老板自己在跑 Streamlit/Flask），绝不主动释放。

## 与 drive-all 的关系
- drive-all 的 `--clean-stale` = 按**锁年龄 ≥90min** 兜底清死锁（防长期无人管）。
- unstick 的 `--fix` = 按 **state 停滞** 精准清孤儿锁（识别"假新鲜锁"），
  这是 `--clean-stale` 覆盖不到的场景，也是老板手动"刷新解卡"的主入口。
- 两者互补：日常靠 drive-all 兜底，卡住时用 unstick 立即刷新。

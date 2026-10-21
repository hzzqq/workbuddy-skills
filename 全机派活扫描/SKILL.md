---
name: drive-all
description: |
  一句话/定时全盘派活给「全部」self-driving 自驱项目：定时监测全部项目进度，
  对「未完成且当前空闲」的项目派活继续做完；对已「完成」的项目仅当能交付系统真实收益时才做 polish
  （遵循 self-driving-dev 北极星，禁止凑迭代水活）；带并发锁防止重复派活/文件冲突，
  单轮最多并发派 2 个项目防雪崩。适用触发语：「完成所有项目的未完成任务」「让所有项目继续干活」
  「派活给全部项目」「一键叫所有项目开工」「全盘派活」。本 skill 安装于用户级目录，任何项目可用。
agent_created: true
slug: drive-all
version: 1.0.0
displayName: 全机派活扫描
license: MIT
---

# drive-all · 全盘自驱派活（每小时监测 + 自动派活）

目标：用户不用来回喊，一句话（或定时触发）就让所有自驱项目各忙各的——
没干完且当前空闲的继续干完；已干完的仅当还能交付**系统真实收益**时才 polish（北极星见 self-driving-dev）。

## 防雪崩硬约束（MUST，2026-07-27 实测教训）
- **单轮最多并发派 2 个项目**。WorkBuddy 后台 agent 全跑在应用主进程内，同一分钟涌入
  多个重型 agent 会互相拖死、产生僵尸 run 阻塞调度器（07-26/27 整点雪崩实锤）。
  空闲项目再多，本轮也只派最该推进的 2 个，其余下一轮再派。
- **定时 automation 必须错峰**：rrule 用 BYMINUTE 避开整点 :00，且频率不高于每 3 小时一次
  （当前生产配置：`FREQ=HOURLY;INTERVAL=3;BYMINUTE=10`）。与其它每小时任务的分钟位不得相同。
- **不给"锁在但 state 停滞"的项目重复盖锁**：派活前若发现项目有锁且 state.json 停滞 ≥30min，
  这是孤儿锁（agent 已死），先按 unstick skill 的逻辑清锁再派活；直接盖新 ts 会让锁"假新鲜"、
  把死项目永久跳过（unstick skill 就是为此而生，两者配合：unstick 解卡、drive-all 派活）。

## 触发
- 用户一句话：「完成所有项目的未完成任务」「让所有项目继续干活」「派活给全部项目」
  「把没干完的活都干完」「一键叫所有项目开工」。
- 定时自动化（每小时）：扫描全盘 → 派活（见文末自动化）。

## 核心规则（每次运行都执行）
1. **扫描并判定**（用配套脚本）：
   ```
   C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe ^
     C:\Users\Administrator\.workbuddy\skills\drive-all\scripts\list_projects.py --root E:\project ^
     > E:\project\paihuo\_dispatch.json
   ```
   脚本对每个项目给出：`status`(running/complete/paused/error)、`cycle/max_cycles`、
   `unfinished`、`locked`、`locked_fresh`、`lock_mode`。
   - 扫描结果（派活清单）落到 `E:\project\paihuo\_dispatch.json`；`paihuo` 与 `vw_test_*` 已被扫描器排除，不会误当项目。
2. **遍历项目，按决策派活**（用 Agent 工具，`subagent_type=general-purpose`，`run_in_background=true`）：
   - `paused=true` → **跳过**（不派）。
   - `locked_fresh=true`（有新鲜锁，正被别的 agent 干）→ **跳过**（防重复派活 / 文件冲突）。
   - `status=complete`（cycle>=max_cycles）或 `max_cycles=0`（视作新项目/已完成待打磨）→ **模式=polish**：再推进 ≥5 次迭代；
    打磨也须遵循 self-driving-dev 的北极星——每轮交付系统真实收益，禁止为凑迭代而水活 / 为覆盖而覆盖（见其反自指铁律）。
   - `status=running` 且 `unfinished`（没干完、当前空闲）→ **模式=continue**：续做干完。
3. 全部派完/跳过后，给一句汇总（派了哪几个、模式、跳了哪几个+原因）。后台 agent 完成时逐个通知。
4. 不做微信推送（Server酱 每天仅 5 条，留给 dev-supervisor 进度报告）。

## 干完自动上传 GitHub
每个项目干完（5 轮或到上限）后，自动把本地改动 commit + push 到其 GitHub 远程仓库。
由配套脚本 `scripts/push_github.py` 负责，不依赖 self-driving-dev 内部 push。

- **有 origin remote 的项目**：子 agent 在删锁前调用
  `push_github.py --path {path}`，脚本会 `git add -A && (有改动则 commit) && git push`
  （无 upstream 自动 `-u`）。commit message 形如 `chore: auto-sync via drive-all (cycle=N)`。
- **无 remote 的项目**：默认跳过并回报"未配远程，跳过上传"；若需自动建私有仓库上传，
  主 agent / 自动化可加 `--create` 模式（`gh repo create` 建 `hzzqq/<repo>` 私有仓再推），
  但该模式会在用户 GitHub 账号下建仓库，属外部动作，需用户明确授权才启用。
- **排除项**：`vw_test_*` 预览/临时项目、`skill`/`skills-for-cloud`/`.workbuddy` 工具镜像根，
  一律不上云。
- 推送失败（push_failed / commit_failed / create_failed）只回报原因，不影响删锁与整体派活。

## 只拉不推白名单（pull_only）
某些项目由**其他账号/机器开发**，本机只做镜像、防止本地覆盖远端进度。这类项目登记在
`E:\project\paihuo\pull_only.txt`（每行一个项目绝对路径，`#` 开头为注释）。名单内项目的行为：

- **不派活开发**：`list_projects.py` 会把它们标成 `status=pull_only`、`unfinished=false`，
  drive-all 派活时自动跳过（永不 continue/polish）。
- **只拉不推**：`push_github.py` 对名单内项目改为 `fetch + reset --hard`——
  强制切到远端默认分支（main/master，不跟随 agent 临时分支）并对齐远端 tip，
  **丢弃**本地未提交改动、本地领先提交、agent 临时分支。绝不 commit、绝不 push。
- **兜底补拉**：`push_github.py --root` 结束后，会把 `pull_only.txt` 里未被 project_list
  覆盖的项目（如嵌套仓 `ks\StockSignal`，无独立 state.json）也补拉一遍。
- 当前名单：`E:\project\ks\StockSignal`、`E:\project\big_game`。增删项目只需编辑该 txt。
- `sync_github.sh`（paihuo 内）也读同一份名单，对名单项目只 `fetch + reset --hard`。

## 派活产物的落盘位置（重要）
- **E:\project 根目录不是派活工作区**。所有派活/预览产生的临时目录（`vw_test_*`）与派活快照
  （如 `_dispatch.json`）统一放在 **E:\project\paihuo\\** 下，不要散落到 E:\project 根。
- 扫描脚本 `list_projects.py` 已把 `paihuo` 加入 `EXCLUDE_ROOTS`，并忽略 `vw_test_*` 前缀的目录，
  因此搬进 paihuo 的临时项目**不会**被当成正式自驱项目重新派活。
- 若需要新建派活测试/预览工作区，请在 `E:\project\paihuo\` 下创建，不要放在 E:\project 根。
- 注：真实自驱项目（big_game / dad / fan / hzz / ks / lianghua / map / personal company /
  project1/2/3 / shuifen / video / FinTech_AI_Dialogue 及子项目 animehub / raft-kv / software-clones）
  仍照常在 E:\project 下被扫描与派活，不受此约定影响。

用法（手动/调试）：
  python scripts/push_github.py --root E:\project          # 全盘推有 remote 的
  python scripts/push_github.py --path E:\project\shuifen  # 单项目推
  python scripts/push_github.py --root E:\project --create  # 无 remote 的也建私有仓推

## 自动 seed 新项目（零配置纳入）
扫描脚本 `list_projects.py` 在扫描时会**自动发现并初始化新项目**，无需手动建 state.json：
- 判定"项目"的边界：目录直接含 `.git` 目录，或直接含强项目 marker
  （`package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml` / `index.html` /
  `main.py` / `manage.py` 等，见脚本 `STRONG_MARKERS`）。
- 排除项：缓存/构建产物目录（`.pytest_cache` / `node_modules` / `dist` / `__pycache__` 等）、
  资源/测试目录（`static` / `templates` / `tests` / `docs` / `assets` 等）、
  工具/镜像根目录（`skill` / `skills-for-cloud` / `.workbuddy`）。
- 子树剪枝：一个项目被纳入后，其整个子树不再重复 seed（避免把 `StockSignal/backend`、
  `lianghua/ui` 等内部子目录误当独立项目）。
- 边界情况：
  - 扫描根 `E:\project` 本身不当项目（即使它是 git 仓库），只遍历其子目录。
  - 空目录（如刚 `mkdir` 还没放文件）不含任何 marker，**不会**被 seed；放入
    `index.html`/`package.json` 等后下一轮自动纳入。
  - 已 seed 的项目写入 `seeded_by:"drive-all"` 标记，方便追溯/清理。
- 关闭自动 seed：扫描时加 `--no-seed` 参数（仅列出，不创建 state.json）。

## 并发锁（必须，防重复派活）
- 锁文件：`<项目根>/.workbuddy/self-driving/.drive_lock`，内容 JSON：
  `{"ts":<float秒>, "mode":"continue|polish"}`。
- 主 agent 派活前读 list_projects 的 `locked_fresh`：为 true 则跳过。
- 被派出的子 agent 在「cd 到项目根之后、开工之前」立即**写锁**；在「无论成功/失败/提前停」的最末尾**删锁**。
  写锁 / 删锁用 python（避免 rm 争议）：
  - 写：`python -c "import json,time,os;p=os.path.join('.workbuddy','self-driving','.drive_lock');json.dump({'ts':time.time(),'mode':'<MODE>'},open(p,'w'))"`
  - 删：`python -c "import os;p=os.path.join('.workbuddy','self-driving','.drive_lock');os.path.exists(p) and os.remove(p)"`
- 锁新鲜阈值默认 90 分钟（>1 个自动化周期），超时视为陈旧可回收（防 agent 崩溃留死锁）。

## 子 agent 派活模板（每个项目一份，填好 {path}/{name}/{mode}）
```
你现在是项目 {name}（根目录 {path}）的自主开发司机，本次模式={mode}
（continue=继续把没做完的干完 / polish=已做完再做至少5次迭代打磨）。

0) ⚠️ **环境约束：本环境子 agent 的 Bash `cwd` 不跨命令持久**。因此【每一条】Bash 命令都必须以
   `cd {path} && ` 开头，确保操作始终落在该项目根；不要依赖单独的 `cd` 命令，也不要假设上一条命令的 cwd 还在。
   验证首条：`cd {path} && pwd && C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe -c "import os;print('cwd=',os.getcwd())"`
   之后所有 git 操作、读取 .workbuddy/self-driving/state.json、修改项目文件都用 `cd {path} && <命令>` 形式；
   路径尽量用相对路径（self-driving-dev 内部就是相对 cwd 工作的）。

1) 立即写并发锁（开工前必须写好）：
   python -c "import json,time,os;p=os.path.join('.workbuddy','self-driving','.drive_lock');json.dump({'ts':time.time(),'mode':'{mode}'},open(p,'w'))"

2) 用 Skill 工具加载 self-driving-dev（command='self-driving-dev'）。

3) 本次最多推进 5 轮：记录 start_cycle = 当前 state.json 的 cycle；
   每完成 1 轮检查，若 (cycle - start_cycle) >= 5 立即停。
   - 若项目已判为 complete（cycle>=max_cycles）：先把 state.json 的 max_cycles 设为 cycle+5，
     给循环留出空间，再跑这 5 轮改进（注入新需求 / 优化 / 补测试文档等）。
   - 若是 continue：正常续做，直到自然收尾或再做满 5 轮。

4) 严格遵守 self-driving-dev 全部规则：不执行不可逆/破坏性命令、验收不过不提交、
   改动小步可回滚、不向用户提问、不等批准。
   （self-driving-dev 内部不要 git push；上传 GitHub 由 drive-all 的 push_github.py
    在本项目干完后统一负责，见子 agent 模板第 5.5 步。）

5) 最末尾（无论成功或任何异常）务必运行删锁（顺序：先第 5.5 步上传，再本步删锁）：

5.5) 上传 GitHub（干完即上传，仅当本项目有 origin remote）：
   `cd {path} && C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe C:/Users/Administrator/.workbuddy/skills/drive-all/scripts/push_github.py --path {path}`
   - 输出 status=pushed → 回报"已上传 GitHub"。
   - 输出 status=no_remote → 回报"未配远程，跳过上传"（不报错）。
   - 输出 status=push_failed / commit_failed → 回报失败原因（不影响删锁与主流程）。
   - 无 remote 的项目无需上传，直接进入删锁。

6) 最末尾（无论成功或任何异常）务必运行删锁：
   python -c "import os;p=os.path.join('.workbuddy','self-driving','.drive_lock');os.path.exists(p) and os.remove(p)"

7) 完成后用 2-3 行回报：做了什么、最终 cycle、有无卡点、是否上传 GitHub。
```

## 注意事项
- root 默认 `E:\project`；若用户指定别的扫描根，把上面 `--root` 换掉即可。
- 手动触发时（用户一句话），可先展示 list_projects 结果再确认；但定时自动化无需确认直接派。
- 这是大盘动作，可能同时起多个后台 agent；靠并发锁保证同一项目不会两 agent 互踩。
- 若本环境 Agent（子 agent）工具不可用，退化为：主 agent 顺序对每个需派项目 `cd` 到其根、
  加载 self-driving-dev 续做/打磨最多 5 轮（同样先写锁、末删锁）。
- **清扫派活/预览杂物**：每次派活收尾，把 `E:\project` 根下因预览/调试生成的 `vw_test_*` 临时目录归位到
  `E:\project\paihuo\`（只移不删）：
  `mv E:/project/vw_test_* E:/project/paihuo/ 2>/dev/null`
  `paihuo` 自身已被排除，不会递归。`E:\project` 根只保留真实项目，派活相关文件全在 `paihuo`。

## 配套自动化（每小时）
- 已建 `automation`：名称「drive-all 每小时全盘派活」，rrule=`FREQ=HOURLY;INTERVAL=1`，
  cwds=`E:/project`，model=hy3，thinking=0，ACT存在即每小时自动跑本 skill 的派活逻辑。
- 该自动化 prompt 复用上方【核心规则】+【子 agent 派活模板】。

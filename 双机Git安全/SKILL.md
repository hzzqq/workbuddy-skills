---
name: dual-machine-git-safety
description: 双机/多 agent 协作同一 git 仓库时的安全红线 + 护栏。适用于：任何在"同账号同仓、双机或同工作树多 agent"仓库上做 git 推送/提交/合并/变基/破坏性操作（已知 StockSignal hzzqq/StockSignal、raft-kv hzz/raft-kv 是这种仓库）；看到 non-fast-forward / 历史分叉；刚做完与另一台机器并行的改动；或用户问"双机协作会不会出错"。把"双机协作"的红线从记忆里抽出来，防止并行编辑导致数据破坏或逻辑静默覆盖。配合 ast-invariant-guard 使用（代码级不变量锁死）。
agent_created: true
slug: dual-machine-git-safety
displayName: 双机Git安全
version: 1.0.0
license: MIT
---

# 双机/多 Agent 安全协作 Git 红线

## 一句话定位
双机处理同一项目**会重复劳动、理论上能 last-writer-wins 覆盖语义**，但靠这套红线把损失压在"白做一轮"级别，**不让人为造成数据破坏或逻辑静默错乱**。本 skill 锁 git 层；代码层不变量用 `ast-invariant-guard` 锁。

## 何时触发
- 在共享仓（双机 / 同工作树多 agent）做 `git push` / `commit` / `merge` / `rebase` / `reset` / `stash` / `checkout` 等任何改动历史的操作。
- 推送前/推送后发现 `non-fast-forward`、远端有你没的提交。
- 刚做完与"另一台机器"看似平行的改动（很可能撞车）。
- 用户问"不同空间处理同一项目会不会出错"。

## 非协商红线（违反即可能造成不可逆损失）
1. **只 fast-forward 推送；非快进绝不 `git push --force`**。远端有新提交（另一台已推）时，本地非快进 → **上报老板定夺**，不静默强推。强推会覆盖另一台未合并的工作。
2. **绝不主动删 git 历史 / `git stash` / `git reset --hard` 对协作者未推送的提交**。破坏性操作前先问老板。
3. **`git merge --abort` 在双机分叉树 + 沙箱下会删除整个 `tests/` 目录（磁盘真没了）** → 立刻 `git checkout -f HEAD -- .` 救回。冲突先 `abort`+救回，再请老板协调，不要反复 merge。
4. **预提交 hook SIGTERM 重提交失败 → 不 `--no-verify` 绕过**。把改动留在 staged/工作树，报告老板（raft-kv 踩过：hook 被杀后 `--no-verify` 会把未校验代码推上去）。
5. **Git Bash 里 `>nul` 会创建删不掉的 `nul` 设备名文件**（本沙箱回收站 API 拒绝设备名）。一律用 POSIX `2>/dev/null`。已误建的 `nul` 加 `.gitignore` 忽略，别反复删。

## 沙箱安全推送流程（每次 push 前必跑）
```bash
BR=$(git rev-parse --abbrev-ref HEAD)
REMOTE=$(git ls-remote --heads origin 2>/dev/null | awk -v b="$BR" '$2==("refs/heads/"b){print $1}')
if [ -z "$REMOTE" ]; then echo "NETWORK_BLOCKED: 留本地提交, 待网络恢复或另一台拉取"; exit 0; fi
if git merge-base --is-ancestor "$REMOTE" "$BR" 2>/dev/null; then
  git push origin "$BR" 2>&1 | tail -4
  R2=$(git ls-remote --heads origin 2>/dev/null | awk -v b="$BR" '$2==("refs/heads/"b){print $1}')
  [ "$R2" = "$(git rev-parse "$BR")" ] && echo "SYNCED ✓" || echo "PUSH_INCOMPLETE"
else
  echo "NON_FF: 远端有新提交, 本地非快进——按红线不强制推送, 上报老板"
  echo "  本地=$(git rev-parse --short "$BR") 远端=$(git rev-parse --short "$REMOTE")"
fi
```
- 推送遇 `502 CONNECT tunnel failed` 等瞬时错误：**重试一次**即可，不要循环狂重试。
- 网络持续取不到远端 SHA：留本地提交，**不强制、不 `--no-verify`**，待网络恢复或另一台拉取。

## 检测与处理 non-fast-forward
- `git ls-remote` 拿远端 SHA，`git merge-base --is-ancestor $REMOTE HEAD` 为 TRUE 才推。
- 非 FF：**把本地 SHA 与远端 SHA 都报给老板**，由老板决定 rebase / merge / 协调，agent 不替老板拍板。

## 多远端仓库：先分清「谁是你能写的」

很多生态里一个本地仓挂了**两个远端**，语义完全不同，推错就是事故：

| 远端 | 典型含义 | 能不能推 |
|---|---|---|
| `origin` = **你自己的 fork**（如 `hzzqq/xxx`） | 你的副本 | ✅ 可推（先验 FF） |
| `upstream` = **官方/他人仓**（如 `pollen-robotics/xxx`） | 别人的 | ❌ 默认不推，走 PR |

每次 push 前先 `git remote -v` 确认，**别默认 `origin` 就是自己的**。
教训（2026-09-15 microduck_rl）：`origin` 直接指向官方仓 `pollen-robotics/microduck_rl`，`git push` 返回 `403 Permission to ... denied to <user>`，且该仓已分叉（共同祖先 5946fd9）→ 既没权限、也不能 FF。

### 无写权限 / 不可 FF 的标准解法（全程不 force）
1. **确认真的没权限 / 真不能 FF**：`git push --dry-run origin <branch>` —— 它会真联系服务端，一次性同时暴露 `403` 和 `non-fast-forward`。
2. **Fork 到自己名下**（`gh` 已登录且带 `repo` scope 时可全自动）：
   ```bash
   gh repo fork <上游/仓名> --clone=false      # 本地已有 clone 时用 --clone=false
   git remote add fork https://github.com/<你>/<仓名>
   ```
3. **推到新话题分支**（新 ref 永远算快进，最安全）：
   ```bash
   git push fork <本地分支>:feature/<有意义的名字>
   ```
4. 再开 PR 合上游。**不要**把别人的 `develop/main` 当推送目标。

> **关键认知**：fork 刚建好时，它的 `develop` 已经等于「上游当前 HEAD」（如 cb70b79），所以本地分叉分支推到自己 fork 的 `develop` **照样 non-fast-forward**。
> **fork 只解决「权限」，不解决「分叉」**——分叉还得靠 merge/rebase，或改名分支。

## 推送三连查（推之前必做，比 ls-remote 更硬）
```bash
git fetch --all                                          # 1. 先看清远端真实位置
git merge-base --is-ancestor origin/<br> <br> && echo "FF ok"   # 2. 明确验快进
git push --dry-run origin <br>                           # 3. 干跑：一次暴露权限+非快进
```
`--dry-run` 会真联系服务端，信息量远大于 `ls-remote`。

## 灾难恢复
- **`merge --abort` 误删 `tests/`**：`git checkout -f HEAD -- .`（或 `git checkout -f HEAD -- tests/`）立即救回，再确认测试绿。
- **未提交改动疑似被覆盖**：先 `git stash list` + `git reflog` 找残留，别急着 `clean`/`reset --hard`。
- **本地分支 unborn / 提交变 dangling**（HEAD 无 commit、reflog 空，文件都在却摸不到）：别急着 `reset --hard` 或盲提交。按顺序——`git cat-file -p <sha>` 看父子链 → `git merge-base --is-ancestor main <tip>` 验是否 FF → `git diff <tip> --stat` 确认工作树与 tip 逐字节一致 → `git branch -f main <tip>` + `git checkout main` 找回，**零历史删除**。2026-09-15 microduck-lab 据此把 4 个 dangling 提交全数救回。

## 降低风险的工程纪律（非 git，靠习惯）
1. **改完即提交即推**，不留长时未提交编辑——若"另一台"是同工作树第二 agent，未提交改动最易被 `pull`/`checkout` 踩掉。
2. **给双机划模块边界**：一台只动 `modules/` 后端 + 校准，另一台只动 `pages/` 渲染，相遇面只过公共 API，减少同文件并行。
3. **公共 API 接触点加 AST 不变量护栏**（调 `ast-invariant-guard`）：凡双机容易各改各的点（如 `CYCLE_ADJ` 六阶段刻度、事件因子 `(df, meta)` 解包、统一响应信封、涨色比较），锁成测试，谁改歪谁红——git 的 FF 拦不住"语义相反的最后提交者胜"，只能靠测试拦。
4. **关键不变量测试要随改动一起提交**，别等"有空再补"。

## 与 ast-invariant-guard 的配合
- 本 skill 管 **git 历史层**（不丢、不覆盖、可恢复）。
- `ast-invariant-guard` 管 **代码语义层**（并行改同一函数时，矛盾改法不被 FF 静默放过）。
- 两者一起，才把"双机协作"的真实残余风险（last-writer-wins 覆盖语义）压住。

## 自检清单（每次双机仓 push 前默念）
- [ ] 远端是本地祖先？（`merge-base --is-ancestor`）否则上报，不强推
- [ ] 没动过 `git reset --hard` / 删 stash / 删历史
- [ ] 没跑过 `git merge --abort` 分叉合并（若跑了，已 `checkout -f HEAD -- .` 救 tests/）
- [ ] 提交信息不含 `--no-verify` 绕过
- [ ] 双机并行改的同一文件，相关不变量测试已绿
- [ ] 推送后 `ls-remote` 复核远端 == 本地

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unstick · WorkBuddy 任务解卡器
================================
解决 WorkBuddy 跑任务"卡住不动"的头号元凶：**孤儿锁（orphan lock）**。

背景（drive-all 派活机制）：
  每小时自动化会给正在派活的项目写 `.workbuddy/self-driving/.drive_lock`
  （JSON，含 ts/mode），干完由子 agent 删锁。但如果 agent 中途卡死 / 被
  cancel / WorkBuddy 会话中断，锁不会被删。更坑的是：**每小时自动化会给
  这些"僵尸项目"重新盖一个新 ts 的锁**，于是锁永远"看起来很新鲜"
  （age 小），drive-all 的 `--clean-stale`（按 90min 锁年龄清）根本清不掉，
  项目就被当"占用中"一直跳过 —— 表现为"WorkBuddy 卡住了、不干活"。

真正的判定信号 = **state.json 的停滞时长**：
  真在干活的 agent 会持续更新 state.json（每轮写 cycle/log）；
  锁还在但 state.json 长时间没更新 = agent 已死 = 孤儿锁，应清理。

本工具做三件事（安全、只读优先）：
  1. 孤儿锁：有锁 + state 停滞 ≥ 阈值(默认30min) → 判卡死，--fix 时清锁。
     （保留真在干活的：state 近期有更新的锁一律不动。）
  2. git 锁残留：index.lock / rebase-merge / MERGE_HEAD 悬挂，--fix 时清理。
  3. 端口占用：8501(Streamlit)/5050(Flask)/26561(代理) 只读探测报告，不动。

⚠️ 本工具**不杀任何进程**。WorkBuddy 的后台 agent 跑在应用主进程内，
   不是独立 OS 进程，杀进程会误伤 WorkBuddy 本体。解卡只清锁/清 git 残留，
   之后项目会在下一轮自动化（或手动跑 drive-all）立即被重新派活。

用法:
  # 诊断（只读，默认）：看哪些卡住了
  python unstick.py --root E:\\project
  # 解卡：清理判定为卡死的孤儿锁 + git 残留
  python unstick.py --root E:\\project --fix
  # 强制全刷新：清掉所有 .drive_lock（不管死活），用于"全部重开"
  python unstick.py --root E:\\project --fix --force
  # 只处理单个项目
  python unstick.py --path "E:\\project\\project2" --fix
  # 自定义停滞阈值（分钟）
  python unstick.py --root E:\\project --fix --stalled-min 45
"""
import argparse
import json
import os
import socket
import sys
import time

STATE_REL = os.path.join(".workbuddy", "self-driving", "state.json")
LOCK_REL = os.path.join(".workbuddy", "self-driving", ".drive_lock")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             ".idea", ".vscode", "dist", "build", ".workbuddy-backup", "paihuo"}
DEFAULT_STALLED_MIN = 30      # state 停滞多少分钟判为孤儿锁
DEFAULT_GITLOCK_MIN = 10      # index.lock 悬挂多少分钟判为残留
PORTS = [(8501, "Streamlit"), (5050, "Flask"), (26561, "代理")]


def age_min(ts):
    return (time.time() - float(ts)) / 60.0


def read_lock(lock_path):
    try:
        info = json.load(open(lock_path, encoding="utf-8"))
        return info, age_min(info.get("ts", 0) or 0)
    except Exception:
        # 锁存在但读不了（损坏）→ 视为很老
        try:
            return {}, age_min(os.path.getmtime(lock_path))
        except Exception:
            return {}, 9999.0


def state_stalled_min(state_path):
    """state.json 距今多少分钟未更新（越大越可能卡死）。"""
    try:
        return age_min(os.path.getmtime(state_path))
    except Exception:
        return 9999.0


def find_locked_projects(root):
    """返回所有存在 .drive_lock 的项目 [(proj_dir, lock_path, state_path), ...]"""
    res = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        if os.path.basename(dp) == "self-driving" and ".drive_lock" in fn:
            proj = os.path.dirname(os.path.dirname(dp))
            res.append((proj,
                        os.path.join(dp, ".drive_lock"),
                        os.path.join(dp, "state.json")))
    return res


def find_git_locks(root):
    """找 index.lock / rebase-merge / rebase-apply / MERGE_HEAD 悬挂残留。"""
    res = []
    for dp, dn, fn in os.walk(root):
        # 只进 .git，不进其它噪音目录
        dn[:] = [d for d in dn if d not in
                 {"node_modules", ".venv", "venv", "__pycache__", "paihuo",
                  ".workbuddy-backup"}]
        if os.path.basename(dp) == ".git":
            for name in ("index.lock", "MERGE_HEAD"):
                p = os.path.join(dp, name)
                if os.path.isfile(p):
                    res.append((p, "file"))
            for name in ("rebase-merge", "rebase-apply"):
                p = os.path.join(dp, name)
                if os.path.isdir(p):
                    res.append((p, "dir"))
            dn[:] = []  # 不递归进 .git 内部
    return res


def probe_ports():
    out = []
    for port, label in PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        busy = (s.connect_ex(("127.0.0.1", port)) == 0)
        s.close()
        out.append({"port": port, "label": label, "busy": busy})
    return out


def classify(lock_path, state_path, stalled_min, force):
    info, lock_age = read_lock(lock_path)
    st_stall = state_stalled_min(state_path)
    has_state = os.path.isfile(state_path)
    if force:
        verdict = "force_clear"
    elif not has_state:
        verdict = "stalled"          # 有锁无 state = 异常，清
    elif st_stall >= stalled_min:
        verdict = "stalled"          # 孤儿锁：agent 已死
    else:
        verdict = "active"           # 真在干活，保留
    return {
        "lock_age_min": round(lock_age, 1),
        "state_stalled_min": round(st_stall, 1) if has_state else None,
        "mode": info.get("mode"),
        "has_state": has_state,
        "verdict": verdict,
    }


def rm_path(p, kind):
    try:
        if kind == "dir":
            import shutil
            shutil.rmtree(p)
        else:
            os.remove(p)
        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    ap = argparse.ArgumentParser(description="WorkBuddy 任务解卡器（清孤儿锁）")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--root", default=None, help="项目根，默认 E:\\project")
    g.add_argument("--path", default=None, help="只处理单个项目目录")
    ap.add_argument("--fix", action="store_true", help="执行清理（默认仅诊断只读）")
    ap.add_argument("--force", action="store_true",
                    help="配合 --fix：清掉所有锁（不管死活），全刷新重开")
    ap.add_argument("--stalled-min", type=float, default=DEFAULT_STALLED_MIN,
                    help=f"state 停滞多少分钟判为孤儿锁，默认 {DEFAULT_STALLED_MIN}")
    ap.add_argument("--gitlock-min", type=float, default=DEFAULT_GITLOCK_MIN,
                    help=f"git index.lock 悬挂多少分钟判为残留，默认 {DEFAULT_GITLOCK_MIN}")
    ap.add_argument("--no-git", action="store_true", help="跳过 git 锁残留检查")
    ap.add_argument("--no-ports", action="store_true", help="跳过端口探测")
    args = ap.parse_args()

    root = args.root or "E:\\project"
    scan_roots = [args.path] if args.path else [root]

    # 1) 锁诊断
    locks = []
    for r in scan_roots:
        for proj, lp, sp in find_locked_projects(r):
            c = classify(lp, sp, args.stalled_min, args.force)
            c.update({"name": os.path.basename(proj.rstrip(os.sep)),
                      "path": proj, "lock_path": lp})
            locks.append(c)
    locks.sort(key=lambda x: -(x["state_stalled_min"] or 0))

    # 2) git 锁残留
    git_locks = []
    if not args.no_git:
        for r in scan_roots:
            for p, kind in find_git_locks(r):
                try:
                    a = age_min(os.path.getmtime(p))
                except Exception:
                    a = 9999.0
                git_locks.append({"path": p, "kind": kind,
                                  "age_min": round(a, 1),
                                  "stale": a >= args.gitlock_min})

    # 3) 端口
    ports = [] if args.no_ports else probe_ports()

    # ---- 执行清理 ----
    cleaned_locks, cleaned_git = [], []
    if args.fix:
        for l in locks:
            if l["verdict"] in ("stalled", "force_clear"):
                ok, err = rm_path(l["lock_path"], "file")
                l["cleaned"] = ok
                if ok:
                    cleaned_locks.append(l["name"])
                else:
                    l["clean_error"] = err
        for g_ in git_locks:
            if g_["stale"]:
                ok, err = rm_path(g_["path"], g_["kind"])
                g_["cleaned"] = ok
                if ok:
                    cleaned_git.append(g_["path"])
                else:
                    g_["clean_error"] = err

    # ---- 输出 ----
    result = {
        "root": root, "mode": "fix" if args.fix else "diagnose",
        "force": args.force, "stalled_min": args.stalled_min,
        "locks": locks, "git_locks": git_locks, "ports": ports,
        "cleaned_locks": cleaned_locks, "cleaned_git": cleaned_git,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # ---- 人类可读摘要（stderr）----
    e = sys.stderr.write
    stalled = [l for l in locks if l["verdict"] in ("stalled", "force_clear")]
    active = [l for l in locks if l["verdict"] == "active"]
    e("\n" + "=" * 56 + "\n")
    e(f"# 锁诊断：共 {len(locks)} 个 .drive_lock | "
      f"卡死/孤儿 {len(stalled)} | 活跃(保留) {len(active)}\n")
    for l in locks:
        tag = {"active": "✅活跃", "stalled": "❌卡死",
               "force_clear": "🔄强清"}.get(l["verdict"], l["verdict"])
        ss = l["state_stalled_min"]
        e(f"  [{tag}] {l['name']:22} 锁age={l['lock_age_min']:.0f}m "
          f"state停滞={'无state' if ss is None else f'{ss:.0f}m'} "
          f"mode={l['mode']}"
          + ("  → 已清" if l.get("cleaned") else "") + "\n")
    if git_locks:
        e(f"# git 残留：{len(git_locks)} 处（stale {sum(1 for g in git_locks if g['stale'])}）\n")
        for g_ in git_locks:
            e(f"  {'❌' if g_['stale'] else '⏳'} {g_['path']} age={g_['age_min']:.0f}m"
              + ("  → 已清" if g_.get("cleaned") else "") + "\n")
    busy = [p for p in ports if p["busy"]]
    if busy:
        e(f"# 端口占用（仅提示，不处理）：" +
          ", ".join(f"{p['port']}({p['label']})" for p in busy) + "\n")
    if args.fix:
        e(f"\n# 已清理：孤儿锁 {len(cleaned_locks)} 个"
          + (f" [{', '.join(cleaned_locks)}]" if cleaned_locks else "")
          + f"，git 残留 {len(cleaned_git)} 处\n")
        if cleaned_locks:
            e("# 下一轮 drive-all（每小时自动化 / 手动）会立即重新派活这些项目。\n")
    else:
        if stalled:
            e(f"\n# 仅诊断。加 --fix 清理上述 {len(stalled)} 个卡死锁并解卡。\n")
        else:
            e("\n# 未发现卡死孤儿锁，一切正常。\n")


if __name__ == "__main__":
    main()

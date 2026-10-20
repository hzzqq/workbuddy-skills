#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive-all 配套扫描器（含自动 seed）：
1) 列出 root 下所有 self-driving 项目 + 状态 + 并发锁
2) 自动 seed：发现 root 下"像业务项目"但没有 state.json 的目录，
   自动初始化 .workbuddy/self-driving/state.json，使其下一轮即被纳入派活。

"项目边界"判定（避免把缓存/子目录误当项目）：
  - 目录直接包含 `.git` 目录，或
  - 目录直接包含强项目 marker（package.json / pyproject.toml / go.mod /
    index.html / main.py 等，见 STRONG_MARKERS）
  - 且 base 名不在 EXCLUDE_SUBDIRS（.pytest_cache / node_modules / dist ...）
  - 且不在已知项目 / 已 seed 项目的子树内（子树剪枝，防重复）

用法:
  python list_projects.py [--root E:\\project] [--lock-ttl 90] [--no-seed]
"""
import argparse
import json
import os
import sys
import time

# 递归 walk 时跳过的噪音目录（不遍历其内部）
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             ".idea", ".vscode", "dist", "build", ".workbuddy-backup"}
# 明确排除的"非业务项目"根目录（工具 / 配置 / 镜像 / 派活暂存）
EXCLUDE_ROOTS = {"skill", "skills-for-cloud", ".workbuddy", ".workbuddy-backup",
                 "software-clones-ignore", "paihuo"}
# 排除的目录名前缀（派活/预览产生的临时文件夹，绝不当作项目）
EXCLUDE_PREFIXES = ("vw_test_",)
# 排除的"像目录但不是项目"的 base 名（缓存 / 构建产物 / 资源）
EXCLUDE_SUBDIRS = {
    ".pytest_cache", "__pycache__", "node_modules", "dist", "build", ".venv",
    "venv", "target", "out", "bin", "obj", ".idea", ".vscode", ".workbuddy",
    ".svn", ".hg", "migrations", "static", "templates", "tests", "test",
    "docs", "assets", "public", "vendor", "coverage", ".tox", ".mypy_cache",
    ".ruff_cache", ".eggs",
}
# 强项目 marker：目录直接含其一即视为"像项目"（不含 README.md 等易误判项）
STRONG_MARKERS = {
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "manage.py",
    "requirements.txt", "pom.xml", "composer.json", "Gemfile", "build.gradle",
    "deno.json", "index.html", "main.py", "app.py", "main.js", "main.go",
    "main.rs", "main.cpp", "setup.py", "CMakeLists.txt", "pubspec.yaml",
}
STATE_REL = os.path.join(".workbuddy", "self-driving", "state.json")
LOCK_NAME = ".drive_lock"
DEFAULT_MAX_CYCLES = 10
DEFAULT_LOCK_TTL = 90


def _norm(p):
    """路径归一化：绝对、正斜杠、小写（Windows 大小写不敏感）。"""
    return os.path.abspath(p).replace("\\", "/").rstrip("/").lower()


def load_pull_only(root):
    """读取 <root>/paihuo/pull_only.txt，返回归一化路径集合。
    名单内项目：只拉不推、不派活开发。"""
    f = os.path.join(root, "paihuo", "pull_only.txt")
    s = set()
    try:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    s.add(_norm(line))
    except Exception:
        pass
    return s


def find_state_files(root):
    res = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS and d != "paihuo"]
        if os.path.basename(dp) == "self-driving" and "state.json" in fn:
            sp = os.path.join(dp, "state.json")
            proj = os.path.dirname(os.path.dirname(dp))
            res.append((proj, sp))
    return res


def find_candidates(root, known_projects):
    """全递归找"项目候选"（无 state.json、像项目、不在已知/已seed子树内）"""
    live = set(known_projects)  # 已知 + 本轮已 seed，用于子树剪枝
    cands = []
    for dp, dn, fn in os.walk(root):
        # 不进入 .git 内部，也不把 .git 当候选 base
        dn[:] = [d for d in dn if d not in SKIP_DIRS and d != ".git"]
        # 根目录本身不当项目（避免把整个仓库当成一个巨型项目）
        if dp == root:
            continue
        base = os.path.basename(dp)
        if base in EXCLUDE_ROOTS:
            dn[:] = []
            continue
        if any(base.startswith(p) for p in EXCLUDE_PREFIXES):
            dn[:] = []
            continue
        if base in EXCLUDE_SUBDIRS:
            dn[:] = []
            continue
        # 已知 / 已 seed 项目子树剪枝
        if dp in live or any(dp == k or dp.startswith(k + os.sep)
                             for k in live):
            dn[:] = []
            continue
        # 已有 state.json（非 known，理论不会发生）→ 当作已知，剪枝子树
        if os.path.exists(os.path.join(dp, STATE_REL)):
            live.add(dp)
            dn[:] = []
            continue
        # 项目边界判定：含 .git 目录 或 含强 marker
        is_git = os.path.isdir(os.path.join(dp, ".git"))
        is_proj = is_git or bool(STRONG_MARKERS & set(fn) | set(dn))
        if not is_proj:
            continue
        cands.append(dp)
        live.add(dp)  # 纳入后立即剪枝其子树，防子目录重复 seed
    return cands


def seed_project(proj):
    """创建初始 state.json。成功返回 True"""
    sd = os.path.join(proj, ".workbuddy", "self-driving")
    os.makedirs(sd, exist_ok=True)
    sp = os.path.join(sd, "state.json")
    state = {
        "cycle": 0,
        "max_cycles": DEFAULT_MAX_CYCLES,
        "paused": False,
        "last_score": None,
        "log": [],
        "seeded_by": "drive-all",
        "seeded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        sys.stderr.write(f"[warn] seed 失败 {proj}: {e}\n")
        return False


def load_state(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def check_lock(state_dir, ttl):
    """返回 (locked, locked_fresh, info)。locked_fresh=True 表示正在被别的 agent 干。"""
    lp = os.path.join(state_dir, LOCK_NAME)
    if not os.path.exists(lp):
        return False, False, None
    try:
        with open(lp, encoding="utf-8") as f:
            info = json.load(f)
        ts = float(info.get("ts", 0) or 0)
        fresh = (time.time() - ts) < ttl * 60
        return True, fresh, info
    except Exception:
        return True, False, None


def clean_stale_locks(root, ttl):
    """删除超过 ttl 分钟的 .drive_lock（视为 agent 卡死/cancel 残留的死锁）。

    返回删除数量。正常单轮派活最多 5 轮、通常 < ttl 分钟结束并自行删锁；
    超过 ttl 仍存在的锁基本是死锁，可安全清理以便下一轮重新派活。
    """
    removed = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        if os.path.basename(dp) == ".workbuddy":
            lp = os.path.join(dp, "self-driving", LOCK_NAME)
            if not os.path.exists(lp):
                continue
            try:
                with open(lp, encoding="utf-8") as f:
                    info = json.load(f)
                age = (time.time() - float(info.get("ts", 0) or 0)) / 60.0
            except Exception:
                age = 9999
            if age >= ttl:
                try:
                    os.remove(lp)
                    removed += 1
                    sys.stderr.write(f"[clean] 删除死锁 {os.path.dirname(os.path.dirname(dp))} "
                                     f"age={age:.0f}min\n")
                except Exception as e:
                    sys.stderr.write(f"[clean] 删除失败 {lp}: {e}\n")
    return removed


def make_entry(proj, sp, lock_ttl, seeded=False, pull_only=None):
    d = load_state(sp)
    name = os.path.basename(proj.rstrip(os.sep))
    state_dir = os.path.dirname(sp)
    locked, locked_fresh, lock_info = check_lock(state_dir, lock_ttl)
    is_pull_only = bool(pull_only) and _norm(proj) in pull_only
    if d is None:
        return {"name": name, "path": proj, "ok": False, "status": "error",
                "unfinished": False, "locked": locked, "locked_fresh": locked_fresh,
                "seeded": seeded, "pull_only": is_pull_only}
    try:
        cyc = int(d.get("cycle", 0) or 0)
        mx = int(d.get("max_cycles", 0) or 0)
    except Exception:
        return {"name": name, "path": proj, "ok": False, "status": "bad_state",
                "unfinished": False, "locked": locked, "locked_fresh": locked_fresh,
                "seeded": seeded, "pull_only": is_pull_only}
    paused = bool(d.get("paused", False))
    status = "pull_only" if is_pull_only else (
        "paused" if paused else ("complete" if (mx and cyc >= mx) else "running"))
    # pull_only 项目：永不派活开发（unfinished 强制 False）
    unfinished = (not is_pull_only) and (status == "running") and (not paused) and (not locked_fresh)
    return {"name": name, "path": proj, "ok": True, "status": status,
            "cycle": cyc, "max_cycles": mx, "last_score": d.get("last_score"),
            "last_task": d.get("last_task_id"), "unfinished": unfinished,
            "locked": locked, "locked_fresh": locked_fresh,
            "lock_mode": (lock_info or {}).get("mode"), "seeded": seeded,
            "pull_only": is_pull_only}


def main():
    ap = argparse.ArgumentParser(description="drive-all · 列出自驱项目 + 自动 seed")
    ap.add_argument("--root", default="E:\\project")
    ap.add_argument("--lock-ttl", type=float, default=DEFAULT_LOCK_TTL,
                    help="锁新鲜阈值（分钟），默认 90；超过视为陈旧可回收")
    ap.add_argument("--no-seed", action="store_true",
                    help="关闭自动 seed（仅列出，不创建 state.json）")
    ap.add_argument("--clean-stale", action="store_true",
                    help="清理超过 lock-ttl 分钟的陈旧锁（自愈死锁），不创建/修改 state.json")
    args = ap.parse_args()

    if args.clean_stale:
        n = clean_stale_locks(args.root, args.lock_ttl)
        print(f"# 已清理陈旧死锁: {n}", file=sys.stderr)

    pull_only = load_pull_only(args.root)
    known = find_state_files(args.root)
    known_paths = {p for p, _ in known}
    entries = [make_entry(p, sp, args.lock_ttl, pull_only=pull_only) for p, sp in known]
    seeded_names = []

    if not args.no_seed:
        for c in find_candidates(args.root, known_paths):
            if seed_project(c):
                sp = os.path.join(c, STATE_REL)
                entries.append(make_entry(c, sp, args.lock_ttl, seeded=True, pull_only=pull_only))
                seeded_names.append(os.path.basename(c.rstrip(os.sep)))

    entries.sort(key=lambda x: x.get("name") or "")
    print(json.dumps({"root": args.root, "projects": entries,
                      "seeded_this_run": seeded_names}, ensure_ascii=False, indent=2))
    n_unfin = sum(1 for p in entries if p.get("unfinished"))
    n_locked = sum(1 for p in entries if p.get("locked_fresh"))
    print(f"\n# 项目总数: {len(entries)} | 将派活(unfinished): {n_unfin} "
          f"| 占用中(locked_fresh): {n_locked} | 本轮新seed: {len(seeded_names)}",
          file=sys.stderr)


if __name__ == "__main__":
    main()

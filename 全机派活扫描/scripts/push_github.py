#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive-all · 干完自动上传 GitHub

对每个 self-driving 项目：
  - 有 origin remote  -> git add -A && (有改动则 commit) && git push (无 upstream 则 -u)
  - 无 remote:
      * 默认跳过并标记 no_remote
      * --create 模式: 用 gh 建私有仓库(hzzqq/<name>)并 push

排除项（不上云）：
  - vw_test_* 预览/临时项目
  - EXCLUDE_ROOTS: skill / skills-for-cloud / .workbuddy 等工具/镜像根

用法:
  python push_github.py --root E:\\project            # 全盘 push 有 remote 的
  python push_github.py --path E:\\project\\shuifen    # 单项目 push
  python push_github.py --root E:\\project --create    # 无 remote 的也自动建私有仓并推
"""
import argparse
import json
import os
import subprocess
import sys

PY = "C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
LIST = "C:/Users/Administrator/.workbuddy/skills/drive-all/scripts/list_projects.py"

EXCLUDE_ROOTS = {"skill", "skills-for-cloud", ".workbuddy", ".workbuddy-backup",
                 "software-clones-ignore", "paihuo"}
PREVIEW_PREFIXES = ("vw_test_",)


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)


def git(cwd, *args):
    return run(["git", "-C", cwd, *args])


def _norm(p):
    return os.path.abspath(p).replace("\\", "/").rstrip("/").lower()


def load_pull_only(root):
    """读取 <root>/paihuo/pull_only.txt：名单内项目只拉不推。"""
    f = os.path.join(root or "E:\\project", "paihuo", "pull_only.txt")
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


def remote_default_branch(path):
    """确定远端默认分支（main/master），不跟随 agent 临时切换的本地分支。"""
    r = git(path, "symbolic-ref", "refs/remotes/origin/HEAD")
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    for b in ("main", "master"):
        rr = git(path, "ls-remote", "--heads", "origin", b)
        if rr.returncode == 0 and rr.stdout.strip():
            return b
    return git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"


def pull_one(path, name):
    """只拉不推：强制切到远端默认分支并 reset --hard 到远端
    （GitHub 为准，丢弃本地改动/领先提交/agent 临时分支）。"""
    res = {"name": name, "path": path, "mode": "pull_only", "status": "unknown"}
    if not os.path.isdir(os.path.join(path, ".git")):
        res["status"] = "not_git"
        return res
    r = git(path, "remote", "get-url", "origin")
    if not (r.returncode == 0 and r.stdout.strip()):
        res["status"] = "no_remote"
        return res
    branch = remote_default_branch(path)
    f = git(path, "fetch", "origin", branch)
    if f.returncode != 0:
        res["status"] = "fetch_failed"
        res["detail"] = (f.stderr or f.stdout).strip()[:300]
        return res
    # 强制切到该分支并对齐到刚 fetch 的远端 tip（-f 丢弃本地改动）
    co = git(path, "checkout", "-f", "-B", branch, "FETCH_HEAD")
    rs = git(path, "reset", "--hard", "FETCH_HEAD")
    if co.returncode == 0 and rs.returncode == 0:
        res["status"] = "pulled_reset"
        res["branch"] = branch
        res["detail"] = rs.stdout.strip()[:200]
    else:
        res["status"] = "pull_failed"
        res["detail"] = ((co.stderr or "") + " | " + (rs.stderr or rs.stdout)).strip()[:300]
    return res


def project_list(root):
    try:
        out = subprocess.check_output([PY, LIST, "--root", root, "--no-seed"],
                                      stderr=subprocess.DEVNULL)
        return json.loads(out).get("projects", [])
    except Exception as e:
        sys.stderr.write(f"[err] 读取项目列表失败: {e}\n")
        return []


def sanitize_repo_name(name):
    """GitHub 仓库名不允许空格/某些字符，转成安全形式。"""
    s = name.strip().replace(" ", "-").replace("_", "-")
    keep = []
    for ch in s:
        if ch.isalnum() or ch in "-.":
            keep.append(ch)
        else:
            keep.append("-")
    s = "".join(keep).strip("-.").lower()
    return s or "repo"


def push_one(path, name, create=False):
    res = {"name": name, "path": path, "status": "unknown"}
    if not os.path.isdir(os.path.join(path, ".git")):
        res["status"] = "not_git"
        return res

    r = git(path, "remote", "get-url", "origin")
    has_remote = (r.returncode == 0 and r.stdout.strip())
    if not has_remote:
        if create:
            repo = sanitize_repo_name(name)
            sys.stderr.write(f"[create] {name} -> gh repo create {repo} (private)...\n")
            cr = run(["gh", "repo", "create", repo, "--private",
                      "--source", ".", "--remote", "origin", "--push"], cwd=path)
            if cr.returncode == 0:
                res["status"] = "created_pushed"
                res["repo"] = f"hzzqq/{repo}"
                res["detail"] = (cr.stdout or cr.stderr).strip()[:200]
            else:
                res["status"] = "create_failed"
                res["detail"] = (cr.stderr or cr.stdout).strip()[:300]
            return res
        res["status"] = "no_remote"
        return res

    # commit（仅当有改动）
    st = git(path, "status", "--porcelain")
    if st.stdout.strip():
        git(path, "add", "-A")
        branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
        msg = "chore: auto-sync via drive-all"
        sj = os.path.join(path, ".workbuddy", "self-driving", "state.json")
        if os.path.exists(sj):
            try:
                cyc = json.load(open(sj, encoding="utf-8")).get("cycle")
                if cyc is not None:
                    msg += f" (cycle={cyc})"
            except Exception:
                pass
        co = git(path, "commit", "-m", msg)
        if co.returncode != 0:
            res["status"] = "commit_failed"
            res["detail"] = (co.stderr or co.stdout).strip()[:300]
            return res

    # push
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    up = git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if up.returncode == 0 and up.stdout.strip():
        p = git(path, "push", "origin", branch)
    else:
        p = git(path, "push", "-u", "origin", branch)
    if p.returncode == 0:
        res["status"] = "pushed"
        res["detail"] = (p.stdout or p.stderr).strip()[:200]
    else:
        res["status"] = "push_failed"
        res["detail"] = (p.stderr or p.stdout).strip()[:300]
    return res


def main():
    ap = argparse.ArgumentParser(description="drive-all · 自动上传 GitHub")
    ap.add_argument("--root", help="全盘模式：扫描根目录")
    ap.add_argument("--path", help="单项目模式：直接指定项目路径")
    ap.add_argument("--create", action="store_true",
                    help="无 remote 的项目自动用 gh 建私有仓库并推送")
    args = ap.parse_args()

    # 只拉不推白名单（root 模式用 --root，path 模式用其上溯的 project 根）
    pull_only = load_pull_only(args.root or "E:\\project")

    results = []
    if args.path:
        if _norm(args.path) in pull_only:
            results.append(pull_one(args.path,
                                    os.path.basename(args.path.rstrip(os.sep))))
        else:
            results.append(push_one(args.path,
                                     os.path.basename(args.path.rstrip(os.sep)),
                                     args.create))
    elif args.root:
        processed = set()
        for p in project_list(args.root):
            name, path = p["name"], p["path"]
            if name in EXCLUDE_ROOTS or name.startswith(PREVIEW_PREFIXES):
                sys.stderr.write(f"[skip] {name} (排除项，不上云)\n")
                continue
            processed.add(_norm(path))
            if _norm(path) in pull_only:
                sys.stderr.write(f"[pull-only] {name} (只拉不推，reset 到远端)\n")
                results.append(pull_one(path, name))
                continue
            results.append(push_one(path, name, args.create))
        # 兜底：pull_only.txt 里未被 project_list 覆盖的（如嵌套仓 StockSignal）也补拉
        for norm_path in pull_only:
            if norm_path in processed:
                continue
            real = norm_path  # 已是正斜杠小写；用它定位实际目录
            if os.path.isdir(os.path.join(real, ".git")):
                nm = os.path.basename(real.rstrip("/"))
                sys.stderr.write(f"[pull-only+] {nm} (名单补拉，reset 到远端)\n")
                results.append(pull_one(real, nm))
    else:
        ap.error("需要 --root 或 --path")

    ok = [r for r in results if r["status"] in ("pushed", "created_pushed")]
    pulled = [r for r in results if r["status"] == "pulled_reset"]
    no_remote = [r for r in results if r["status"] == "no_remote"]
    fails = [r for r in results
             if "failed" in r["status"] or r["status"] in ("not_git",)]
    print(json.dumps({"results": results, "pushed": len(ok),
                      "pulled_only": len(pulled),
                      "no_remote": len(no_remote), "failed": len(fails)},
                     ensure_ascii=False, indent=2))
    sys.stderr.write(f"\n# push 成功: {len(ok)} | 只拉不推: {len(pulled)} "
                     f"| 无remote跳过: {len(no_remote)} | 失败: {len(fails)}\n")


if __name__ == "__main__":
    main()

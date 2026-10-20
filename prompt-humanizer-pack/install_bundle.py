#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合 skill 一键安装脚本：按 manifest.json 补齐成员。"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(HERE, "manifest.json")
TARGET = os.path.expanduser("~/.workbuddy/skills")
MIRROR_DEFAULT = r"E:/project/skill/skills-for-cloud"


def find_skillhub():
    # 优先直接用 Python CLI（skillhub 的 bash 包装只是 exec python3 ~/.skillhub/skills_store_cli.py）
    cli = os.path.join(os.path.expanduser("~"), ".skillhub", "skills_store_cli.py")
    if os.path.isfile(cli):
        return [sys.executable, cli]
    # 退而求其次：PATH 里的 skillhub（Windows 下尽量走 bash 包装）
    p = shutil.which("skillhub")
    if p:
        bash = shutil.which("bash")
        if bash:
            return [bash, p]
        return [p]
    return ["skillhub"]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", default=MIRROR_DEFAULT, help="本机自研 skill 镜像根")
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--dir", default=TARGET, help="同 --target")
    args = ap.parse_args()
    target = args.target or args.dir
    os.makedirs(target, exist_ok=True)
    manifest = json.load(open(META, encoding="utf-8"))
    sk = find_skillhub()
    ok = skip = fail = 0
    for m in manifest["members"]:
        dst = os.path.join(target, m["dir"])
        if os.path.isdir(dst):
            print(f"[skip] 已存在: {m['dir']}")
            skip += 1
            continue
        if m["source"] == "skillhub":
            cmd = sk + ["install", m["slug"], "--namespace", m["namespace"], "--dir", target]
            print(f"[install] {m['dir']} -> {' '.join(cmd)}")
            r = subprocess.run(cmd)
            ok += (r.returncode == 0)
            fail += (r.returncode != 0)
        elif m["source"] == "local":
            src = m.get("mirror_path", "")
            if src and os.path.isdir(src):
                shutil.copytree(src, dst)
                print(f"[copy] 本地自研 {m['dir']} <- {src}")
                ok += 1
            else:
                print(f"[WARN] 本地自研 {m['dir']} 未在镜像中找到 ({src})；请先推 GitHub/skills-for-cloud")
                fail += 1
        else:
            print(f"[WARN] 未找到成员: {m['dir']}")
            fail += 1
    print(f"\n完成：已装 {ok} | 已存在 {skip} | 失败/待处理 {fail}")


if __name__ == "__main__":
    main()

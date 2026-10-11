#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进度文档辅助脚本（纯标准库，无外部依赖）。

用法：
  python progress_doc.py init <任务名> [--title 标题] [--dir 目录]
  python progress_doc.py list [--dir 目录]
  python progress_doc.py read <任务名> [--dir 目录]

默认目录：当前工作区的 .workbuddy/progress/
"""
import argparse
import os
import re
import sys
from datetime import date

DEFAULT_DIR = ".workbuddy/progress"


def _safe_name(name: str) -> str:
    """把任务名转成安全文件名（去非法字符、收尾空格）。"""
    s = re.sub(r'[\\/:*?"<>|]', "_", name).strip().strip(".")
    return s or "untitled"


def _today() -> str:
    return date.today().isoformat()


TEMPLATE = """# 进度文档：{title}
> 创建：{today} ｜ 最后更新：{today}

## 🎯 当前目标
（一句话：这个任务/领域要达成什么）

## ✅ 已完成
-

## 🔄 进行中
-

## 📋 待办（按优先级）
- [ ] 

## 🧠 关键决策 / 约定
- （技术选型、接口约定、老板偏好、踩过的雷）

## 🔗 上下文恢复要点（给新会话看）
- 项目/任务的关键背景、约束、雷区
- 哪些文件是核心、改了会有什么连锁反应

## 📎 相关文件 / 链接
-

## 📝 变更日志
- {today}：初始化进度文档
"""


def _resolve_dir(args_dir: str) -> str:
    d = args_dir or DEFAULT_DIR
    # 绝对路径直接用，相对路径基于当前工作目录
    if not os.path.isabs(d):
        d = os.path.join(os.getcwd(), d)
    os.makedirs(d, exist_ok=True)
    return d


def cmd_init(args):
    base = _resolve_dir(args.dir)
    fname = _safe_name(args.name) + ".md"
    path = os.path.join(base, fname)
    if os.path.exists(path):
        print(f"[progress-doc] 已存在，跳过创建：{path}")
        print(path)
        return
    title = args.title or args.name
    with open(path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(title=title, today=_today()))
    print(f"[progress-doc] 已创建进度文档：{path}")
    print(path)


def cmd_list(args):
    base = _resolve_dir(args.dir)
    files = sorted(
        (f for f in os.listdir(base) if f.endswith(".md")),
        key=lambda f: os.path.getmtime(os.path.join(base, f)),
        reverse=True,
    )
    if not files:
        print(f"[progress-doc] 目录内暂无进度文档：{base}")
        return
    print(f"[progress-doc] 进度文档列表（{base}）：")
    for f in files:
        p = os.path.join(base, f)
        mtime = date.fromtimestamp(os.path.getmtime(p)).isoformat()
        # 取第一行标题
        title = ""
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
        except Exception:
            pass
        print(f"  - {f}  (修改 {mtime})  {title}")


def cmd_read(args):
    base = _resolve_dir(args.dir)
    fname = _safe_name(args.name) + ".md"
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print(f"[progress-doc] 找不到：{path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        sys.stdout.write(f.read())


def cmd_update(args):
    """增量更新进度文档：刷新「最后更新」日期 + 追加变更日志，可选追加到指定段落。

    这是「任务收尾自动写回」的核心命令——每次完成一个任务/阶段，
    跑一次 update 把进展落盘，做到「接上之前的任务始终有料」。
    进度文档是本地磁盘 .md 文件，删 WorkBuddy 空间/会话也不会丢。
    """
    base = _resolve_dir(args.dir)
    fname = _safe_name(args.name) + ".md"
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print("[progress-doc] 找不到：%s，请先用 init 创建" % path, file=sys.stderr)
        sys.exit(1)
    today = _today()
    note = args.note or "(无备注)"

    mapping = {
        "已完成": "## ✅ 已完成",
        "进行中": "## 🔄 进行中",
        "待办": "## 📋 待办（按优先级）",
        "关键决策": "## 🧠 关键决策 / 约定",
        "上下文恢复要点": "## 🔗 上下文恢复要点（给新会话看）",
        "相关文件": "## 📎 相关文件 / 链接",
    }
    target = mapping.get(args.section, args.section) if args.section else None

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    meta_done = False
    changelog_done = False
    section_done = False

    for line in lines:
        # 刷新「最后更新」日期
        if line.startswith("> 创建：") and not meta_done:
            line = re.sub(r"最后更新：\S+", "最后更新：%s" % today, line)
            meta_done = True
        out.append(line)
        # 变更日志：在标题后插入一行（最新在上）
        if not changelog_done and line.strip() == "## 📝 变更日志":
            changelog_done = True
            out.append("- %s：%s\n" % (today, note))
            continue
        # 目标段落：在段标题后插入一行
        if target and not section_done and line.rstrip() == target:
            section_done = True
            bullet = "- [ ] %s\n" % note if args.section == "待办" else "- %s\n" % note
            out.append(bullet)
            continue

    if not changelog_done:
        out.append("\n## 📝 变更日志\n")
        out.append("- %s：%s\n" % (today, note))
    if target and not section_done:
        out.append("\n%s\n" % target)
        bullet = "- [ ] %s\n" % note if args.section == "待办" else "- %s\n" % note
        out.append(bullet)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)
    print("[progress-doc] 已增量更新：%s" % path)
    print(path)


def main():
    ap = argparse.ArgumentParser(description="进度文档辅助（progress-doc）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="创建进度文档模板")
    p_init.add_argument("name", help="任务名（会转成文件名）")
    p_init.add_argument("--title", default=None, help="文档标题，默认等同任务名")
    p_init.add_argument("--dir", default=None, help="目录，默认 .workbuddy/progress/")
    p_init.set_defaults(func=cmd_init)

    p_list = sub.add_parser("list", help="列出全部进度文档")
    p_list.add_argument("--dir", default=None)
    p_list.set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="打印进度文档内容")
    p_read.add_argument("name", help="任务名")
    p_read.add_argument("--dir", default=None)
    p_read.set_defaults(func=cmd_read)

    p_update = sub.add_parser("update", help="增量更新：刷日期+追加变更日志(及可选段落)")
    p_update.add_argument("name", help="任务名")
    p_update.add_argument("--note", default=None, help="本次进展简述（必填，写进变更日志）")
    p_update.add_argument("--section", default=None,
                          choices=["已完成", "进行中", "待办", "关键决策",
                                   "上下文恢复要点", "相关文件"],
                          help="额外把 note 追加到哪个段落（默认只写变更日志）")
    p_update.add_argument("--dir", default=None)
    p_update.set_defaults(func=cmd_update)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

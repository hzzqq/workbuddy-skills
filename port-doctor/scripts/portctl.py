# -*- coding: utf-8 -*-
"""portctl —— 本地演示端口体检与自动分配 CLI。

    python portctl.py scan    [--root DIR] [--depth N] [--json]
    python portctl.py check   PROJECT_DIR [--json]
    python portctl.py alloc   PROJECT_DIR [--prefer N] [--pool LO-HI] [--write]
    python portctl.py release (PROJECT_DIR | --port N)
    python portctl.py list    [--all]
    python portctl.py doctor  [--root DIR] [--json]
    python portctl.py kill    --pid N --yes
    python portctl.py prelaunch PROJECT_DIR        # 打印 PORT=xxxx 供启动脚本使用

设计约定
--------
* 只读命令（scan/check/list/doctor）**绝不修改任何东西**，可以随手跑。
* 写操作（alloc/release/kill）都留痕：alloc 写 .port.env + 登记表，kill 要 --yes。
* 判断"端口被占"用 bind 测试（准），netstat 只用来回答"被谁占"。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import allocator          # noqa: E402
import registry           # noqa: E402
import scanner            # noqa: E402


# --------------------------------------------------------------------------
# 归属判定：这个端口上的进程，是不是这个项目自己的？
# --------------------------------------------------------------------------
def owner_is_project(owner, project_path) -> bool:
    hay = " ".join([owner.proc or "", owner.cmdline or "", owner.local or ""]).lower()
    p = os.path.normcase(str(project_path)).replace("/", "\\").lower()
    # 去掉结尾分隔符再比，避免 C:\a 与 C:\ab 误判
    p = p.rstrip("\\")
    if p and p in hay:
        return True
    tail = os.path.basename(str(project_path)).lower()
    return bool(tail) and tail in hay


def analyze_project(proj, owners_cache=None):
    """给一个项目算出：声明端口 / 实际占用 / 冲突类型

    只对 **占宿主机** 的端口做占用判定；compose 容器侧端口单列为提示，不算冲突。
    """
    owners_cache = owners_cache if owners_cache is not None else {}
    rows = []
    for port in proj.host_ports:
        if port not in owners_cache:
            owners_cache[port] = allocator.port_owners(port)
        owners = owners_cache[port]
        free = allocator.is_port_free(port)
        if not owners and free:
            state, note = "空闲", "未监听"
        elif owners and all(owner_is_project(o, proj.path) for o in owners):
            state, note = "本项目在跑", "; ".join("%s(pid %d)" % (o.proc, o.pid) for o in owners)
        elif owners:
            state = "⚠️ 端口相冲"
            note = "; ".join("%s(pid %d) %s" % (o.proc, o.pid, (o.cmdline or "")[:60]) for o in owners)
        else:
            state, note = "⚠️ 端口相冲", "端口被占但查不到进程（权限不足或瞬时占用）"
        rows.append({
            "port": port,
            "state": state,
            "note": note,
            "declared_in": sorted({d.source for d in proj.decls if d.port == port})[:3],
        })
    for port in proj.container_ports:
        rows.append({
            "port": port,
            "state": "容器内映射",
            "note": "仅容器内端口，不占宿主机",
            "declared_in": sorted({d.source for d in proj.decls if d.port == port})[:3],
        })
    return rows


def find_static_conflicts(projects) -> dict:
    """两个不同项目声明了同一个 **宿主机** 端口 → 静态撞车（还没启动就已经埋雷）"""
    by_port = {}
    for p in projects:
        for port in p.host_ports:
            by_port.setdefault(port, []).append(p)
    return {port: ps for port, ps in by_port.items() if len(ps) > 1}


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------
def _table(headers, rows) -> str:
    if not rows:
        return "（无）"
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    out = [" | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)),
           "-+-".join("-" * w for w in widths)]
    for r in rows:
        out.append(" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
    return "\n".join(out)


def report_scan(projects, root, as_json=False) -> str:
    conflicts = find_static_conflicts(projects)
    if as_json:
        payload = {
            "root": str(root),
            "projects": [p.to_dict() for p in projects],
            "static_conflicts": {str(k): [x.name for x in v] for k, v in conflicts.items()},
            "live": {str(p.name): analyze_project(p) for p in projects},
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    lines = ["扫描根目录: %s" % root,
             "发现项目: %d 个" % len(projects), ""]
    owners_cache = {}
    rows = []
    for p in projects:
        for r in analyze_project(p, owners_cache):
            rows.append([p.name, r["port"], r["state"], ",".join(r["declared_in"])[:38], r["note"][:46]])
    lines.append(_table(["项目", "端口", "状态", "声明位置", "占用者"], rows))
    if conflicts:
        lines += ["", "⚠️ 静态撞车（多个项目声明同一端口，必撞）:"]
        for port, ps in sorted(conflicts.items()):
            lines.append("   端口 %d ← %s" % (port, ", ".join(x.name for x in ps)))
    else:
        lines += ["", "静态撞车: 无"]
    return "\n".join(lines)


def report_doctor(projects, root, as_json=False) -> str:
    owners_cache = {}
    live_conflicts = []
    static_conflicts = find_static_conflicts(projects)
    for p in projects:
        for r in analyze_project(p, owners_cache):
            if r["state"].startswith("⚠️"):
                live_conflicts.append({"project": p.name, "path": p.path, **r})
    stale = registry.gc_stale()
    reg_active = registry.entries(active_only=True)

    if as_json:
        return json.dumps({
            "root": str(root),
            "projects": len(projects),
            "live_conflicts": live_conflicts,
            "static_conflicts": {str(k): [x.name for x in v] for k, v in static_conflicts.items()},
            "registry_active": reg_active,
            "registry_stale": stale,
        }, ensure_ascii=False, indent=2)

    lines = ["=== 端口体检 ===", "根目录: %s" % root, "项目数: %d" % len(projects), ""]
    lines.append("【正在发生的相冲】%d 项" % len(live_conflicts))
    if live_conflicts:
        lines.append(_table(["项目", "端口", "占用者"],
                            [[c["project"], c["port"], c["note"][:60]] for c in live_conflicts]))
        lines.append("")
        lines.append("修复建议（已算好可直接用的空闲端口）:")
        reserved = registry.active_ports()
        suggested = set()   # 已建议出去的端口要互相错开，否则多个项目会被建议成同一个端口
        for c in live_conflicts:
            try:
                proj = next(p for p in projects if p.name == c["project"])
                exclude = set(proj.host_ports) | reserved | suggested
                free = allocator.allocate_port(pool=(5100, 5999), exclude=exclude)
                suggested.add(free)
                lines.append("  · %s 的 %d 被占 → alloc \"%s\" --prefer %d --write"
                             % (c["project"], c["port"], c["path"], free))
            except Exception:
                lines.append("  · %s 的 %d 被占 → 手动选一个空闲端口后 alloc \"%s\" --write"
                             % (c["project"], c["port"], c["path"]))
    else:
        lines.append("  （无）")
    lines += ["", "【静态撞车】%d 项" % len(static_conflicts)]
    if static_conflicts:
        for port, ps in sorted(static_conflicts.items()):
            lines.append("  · 端口 %d ← %s" % (port, ", ".join(x.name for x in ps)))
    else:
        lines.append("  （无）")
    lines += ["", "【登记表】active %d 条，stale %d 条" % (len(reg_active), len(stale))]
    for e in reg_active:
        lines.append("  · %d  %s  pid=%s  %s" % (e.get("port"), e.get("project_name"),
                                                  e.get("pid"), e.get("allocated_at")))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 命令
# --------------------------------------------------------------------------
def cmd_scan(args) -> int:
    projects = scanner.scan_root(args.root, max_depth=args.depth)
    print(report_scan(projects, args.root, as_json=args.json))
    return 0


def cmd_check(args) -> int:
    path = os.path.abspath(args.project)
    if not os.path.isdir(path):
        print("目录不存在: %s" % path, file=sys.stderr)
        return 2
    proj = scanner.scan_project(path)
    rows = analyze_project(proj)
    if args.json:
        print(json.dumps({"project": proj.to_dict(), "live": rows},
                         ensure_ascii=False, indent=2))
        return 0
    print("项目: %s" % proj.name)
    print("声明端口: %s" % (", ".join(str(p) for p in proj.ports) or "无"))
    print("")
    print(_table(["端口", "状态", "声明位置", "占用者"],
                 [[r["port"], r["state"], ",".join(r["declared_in"])[:38], r["note"][:60]] for r in rows]))
    fixed = []
    for r in rows:
        if r["state"].startswith("⚠️"):
            fixed.append(r["port"])
    if fixed:
        print("")
        print("修复: python portctl.py alloc \"%s\" --write" % path)
    return 0


def cmd_alloc(args) -> int:
    path = os.path.abspath(args.project)
    if not os.path.isdir(path):
        print("目录不存在: %s" % path, file=sys.stderr)
        return 2
    lo, hi = (int(x) for x in args.pool.split("-", 1))
    registry.gc_stale()
    exclude = registry.active_ports()
    proj = scanner.scan_project(path)
    exclude |= set(proj.host_ports)  # 别把项目自己声明的宿主机端口发出去（除非显式 prefer）
    try:
        port = allocator.allocate_port(pool=(lo, hi), prefer=args.prefer, exclude=exclude)
    except RuntimeError as e:
        print("分配失败: %s" % e, file=sys.stderr)
        return 1
    env_path = allocator.port_env_path(path)
    if args.write:
        allocator.write_port_env(path, port)
    entry = registry.register(port, path, os.path.basename(path), reason="alloc")
    if args.json:
        print(json.dumps({"port": port, "project": path, "env_file": env_path,
                          "written": bool(args.write), "entry": entry},
                         ensure_ascii=False, indent=2))
    else:
        print("已分配端口: %d" % port)
        print("项目: %s" % path)
        print("登记: %s" % registry.registry_path())
        if args.write:
            print("已写入: %s  (PORT=%d)" % (env_path, port))
        else:
            print("提示: 加 --write 才会写 %s" % env_path)
        print("占用该端口后请记得: python portctl.py release \"%s\"" % path)
    return 0


def cmd_release(args) -> int:
    hit = registry.release(port=args.port, project_path=args.project)
    if not hit:
        print("没有匹配的登记记录", file=sys.stderr)
        return 1
    for e in hit:
        print("已释放: 端口 %d  %s" % (e.get("port"), e.get("project_name")))
    return 0


def cmd_list(args) -> int:
    rows = registry.entries(active_only=not args.all)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(_table(["端口", "项目", "PID", "进程", "分配时间", "状态"],
                 [[e.get("port"), e.get("project_name"), e.get("pid"),
                   e.get("proc"), e.get("allocated_at"), e.get("status")] for e in rows]))
    return 0


def cmd_doctor(args) -> int:
    projects = scanner.scan_root(args.root, max_depth=args.depth)
    print(report_doctor(projects, args.root, as_json=args.json))
    return 0


def cmd_kill(args) -> int:
    if not args.yes:
        print("拒绝执行：需要 --yes 明确确认（会结束 PID %d）" % args.pid, file=sys.stderr)
        return 2
    name = allocator.process_name(args.pid)
    cmdline = allocator.process_cmdline(args.pid)
    print("将结束进程: PID=%d %s %s" % (args.pid, name, cmdline[:80]))
    try:
        os.kill(args.pid, 15)
    except OSError as e:
        print("结束失败: %s" % e, file=sys.stderr)
        return 1
    print("已发送终止信号")
    return 0


def cmd_prelaunch(args) -> int:
    """给启动脚本用：分配端口 -> 写 .port.env -> 打印 PORT=xxxx"""
    path = os.path.abspath(args.project)
    lo, hi = (int(x) for x in args.pool.split("-", 1))
    registry.gc_stale()
    exclude = registry.active_ports()
    proj = scanner.scan_project(path)
    exclude |= set(proj.host_ports)
    port = allocator.allocate_port(pool=(lo, hi), prefer=args.prefer, exclude=exclude)
    allocator.write_port_env(path, port)
    registry.register(port, path, os.path.basename(path), reason="prelaunch")
    if args.shell:
        print("PORT=%d" % port)
    else:
        print("PORT=%d" % port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="portctl", description="本地演示端口体检与自动分配")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_root(sp):
        sp.add_argument("--root", default=".", help="扫描根目录（默认当前目录）")
        sp.add_argument("--depth", type=int, default=2, help="目录扫描深度（默认2）")
        sp.add_argument("--json", action="store_true", help="输出 JSON")

    s = sub.add_parser("scan", help="扫描项目端口声明并与实际占用交叉比对")
    add_root(s)
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("check", help="单个项目体检")
    s.add_argument("project")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("alloc", help="为项目分配空闲端口")
    s.add_argument("project")
    s.add_argument("--prefer", type=int, default=None, help="优先使用该端口（不可用则自动换）")
    s.add_argument("--pool", default="5100-5999", help="端口池，默认 5100-5999")
    s.add_argument("--write", action="store_true", help="写入 <project>/.port.env")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_alloc)

    s = sub.add_parser("release", help="释放登记")
    s.add_argument("project", nargs="?", default=None)
    s.add_argument("--port", type=int, default=None)
    s.set_defaults(func=cmd_release)

    s = sub.add_parser("list", help="列出登记")
    s.add_argument("--all", action="store_true", help="含已释放记录")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("doctor", help="全机端口体检 + 修复建议")
    add_root(s)
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("kill", help="结束占用端口的进程")
    s.add_argument("--pid", type=int, required=True)
    s.add_argument("--yes", action="store_true")
    s.set_defaults(func=cmd_kill)

    s = sub.add_parser("prelaunch", help="启动前预检：分配端口并写 .port.env")
    s.add_argument("project")
    s.add_argument("--prefer", type=int, default=None)
    s.add_argument("--pool", default="5100-5999")
    s.add_argument("--shell", action="store_true", help="输出 shell 可 eval 形式")
    s.set_defaults(func=cmd_prelaunch)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

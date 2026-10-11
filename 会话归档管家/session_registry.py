#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话归档管家 - registry 助手（纯标准库，无第三方依赖）

设计：把「自动化定义」和「运行时会话」彻底分开，避免误关定义。
  - known_automations : 所有已接线到 session-archiver 的自动化定义（基线登记，不自动关闭）
  - sessions          : 自动化运行时实际打开的会话实例（受 rotate 上限约束）
  - archive           : 已归档的会话实例

命令：
  register   登记一个自动化定义（接线用，基线批量为所有现有自动化调用）
  run        自动化运行时登记一个会话实例；超过 max_active 则建议关闭最旧会话
  list       列出已知自动化 / 活跃会话 / 已归档
  next-close 返回当前应关闭的最旧会话 id（无则 NONE）
  archive    把一个会话实例归档（关之前请确保已写进度文档）
  set-mode   切换 rotate(默认,保留max个) / onesession(各跑各的跑完即关)

registry 位置：C:/Users/Administrator/.workbuddy/session-archiver/registry.json
可用环境变量 SESSION_ARCHIVER_HOME 覆盖。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_HOME = "C:/Users/Administrator/.workbuddy/session-archiver"
DEFAULT_MAX = 3
DEFAULT_MODE = "rotate"


def _home():
    return os.environ.get("SESSION_ARCHIVER_HOME", DEFAULT_HOME)


def _path():
    return os.path.join(_home(), "registry.json")


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _blank():
    return {
        "mode": DEFAULT_MODE,
        "max_active": DEFAULT_MAX,
        "known_automations": [],
        "sessions": [],
        "archive": [],
    }


def _load():
    p = _path()
    if not os.path.exists(p):
        return _blank()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.setdefault("mode", DEFAULT_MODE)
    data.setdefault("max_active", DEFAULT_MAX)
    data.setdefault("known_automations", [])
    data.setdefault("sessions", [])
    data.setdefault("archive", [])
    return data


def _save(data):
    os.makedirs(_home(), exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _known_ids(data):
    return {a["id"] for a in data["known_automations"]}


def _active_sessions(data):
    return [s for s in data["sessions"] if s.get("status", "active") == "active"]


def cmd_register(args):
    """登记一个自动化定义（接线用）。不创建运行时会话，不影响 rotate。"""
    data = _load()
    aid = args.id or ("auto-%d" % (len(data["known_automations"]) + 1))
    rec = {
        "id": aid,
        "name": args.name or aid,
        "workspace": args.workspace or "",
        "type": args.type or "automation",
        "registered_at": _now_iso(),
    }
    if aid in _known_ids(data):
        for a in data["known_automations"]:
            if a["id"] == aid:
                a.update({"name": rec["name"], "workspace": rec["workspace"],
                          "type": rec["type"], "registered_at": rec["registered_at"]})
        msg = "KNOWN_REFRESHED"
    else:
        data["known_automations"].append(rec)
        msg = "KNOWN_REGISTERED"
    _save(data)
    print("RESULT=%s" % msg)
    print("AUTOMATION_ID=%s" % aid)
    print("TOTAL_KNOWN=%d" % len(data["known_automations"]))
    return 0


def cmd_run(args):
    """自动化运行时打开一个会话实例，受 rotate 上限约束。"""
    data = _load()
    aid = args.id
    name = args.name or aid or "session"
    ws = args.workspace or ""
    # 确保已知（首次运行自动补登记）
    if aid and aid not in _known_ids(data):
        data["known_automations"].append({
            "id": aid, "name": name, "workspace": ws,
            "type": "automation", "registered_at": _now_iso()})
    sid = args.session_id or ("%s@%d" % (aid or "sess", int(datetime.now().timestamp())))
    sess = {
        "session_id": sid,
        "automation_id": aid,
        "name": name,
        "workspace": ws,
        "created_at": _now_iso(),
        "status": "active",
    }
    data["sessions"].append(sess)

    close_id = "NONE"
    active = _active_sessions(data)
    if data["mode"] == "rotate":
        if len(active) > data["max_active"]:
            oldest = min(active, key=lambda s: s["created_at"])
            close_id = oldest["session_id"]
    elif data["mode"] == "onesession":
        if len(active) > 1:
            oldest = min(active, key=lambda s: s["created_at"])
            close_id = oldest["session_id"]

    _save(data)
    print("RESULT=SESSION_STARTED")
    print("SESSION_ID=%s" % sid)
    print("ACTIVE_SESSIONS=%d" % len(active))
    print("CLOSE_NOW=%s" % close_id)
    if close_id != "NONE":
        tgt = next((s for s in active if s["session_id"] == close_id), None)
        if tgt:
            print("CLOSE_NAME=%s" % tgt["name"])
            print("CLOSE_WORKSPACE=%s" % tgt["workspace"])
    return 0


def cmd_list(args):
    data = _load()
    print("=== KNOWN AUTOMATIONS (%d) ===" % len(data["known_automations"]))
    for a in data["known_automations"]:
        print("[%s] %s | ws=%s | type=%s" % (a["id"], a["name"], a["workspace"], a.get("type")))
    print("=== ACTIVE SESSIONS (%d) ===" % len(_active_sessions(data)))
    for s in sorted(_active_sessions(data), key=lambda x: x["created_at"]):
        print("[%s] auto=%s | name=%s | created=%s" % (
            s["session_id"], s.get("automation_id"), s["name"], s["created_at"]))
    print("=== ARCHIVED SESSIONS (%d) ===" % len(data["archive"]))
    for s in data["archive"]:
        print("[%s] auto=%s | archived_at=%s | reason=%s" % (
            s.get("session_id"), s.get("automation_id"), s.get("archived_at", "?"), s.get("reason", "")))
    print("MODE=%s MAX_ACTIVE=%d" % (data["mode"], data["max_active"]))
    return 0


def cmd_next_close(args):
    data = _load()
    active = _active_sessions(data)
    close_id = "NONE"
    if data["mode"] == "rotate" and len(active) > data["max_active"]:
        oldest = min(active, key=lambda s: s["created_at"])
        close_id = oldest["session_id"]
    elif data["mode"] == "onesession" and len(active) > 1:
        oldest = min(active, key=lambda s: s["created_at"])
        close_id = oldest["session_id"]
    print("NEXT_CLOSE=%s" % close_id)
    return 0


def cmd_archive(args):
    data = _load()
    sid = args.id
    found = None
    for s in data["sessions"]:
        if s.get("session_id") == sid and s.get("status", "active") == "active":
            found = s
            break
    if not found:
        print("ARCHIVE_RESULT=NOT_FOUND_OR_ALREADY_ARCHIVED id=%s" % sid)
        return 1
    found["status"] = "archived"
    found["archived_at"] = _now_iso()
    found["reason"] = args.reason or "超过活跃会话上限"
    data["archive"].append(found)
    data["sessions"] = [s for s in data["sessions"] if s.get("session_id") != sid]
    _save(data)
    print("ARCHIVE_RESULT=OK id=%s name=%s" % (sid, found["name"]))
    return 0


def cmd_set_mode(args):
    data = _load()
    if args.mode:
        data["mode"] = args.mode
    if args.max is not None:
        data["max_active"] = max(1, args.max)
    _save(data)
    print("SET_MODE_OK mode=%s max=%d" % (data["mode"], data["max_active"]))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="session-archiver registry helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("register", help="登记自动化定义（接线用）")
    r.add_argument("--id", default=None)
    r.add_argument("--name", default=None)
    r.add_argument("--workspace", default=None)
    r.add_argument("--type", default="automation")
    r.set_defaults(func=cmd_register)

    run = sub.add_parser("run", help="自动化运行时登记一个会话实例")
    run.add_argument("--id", default=None)
    run.add_argument("--name", default=None)
    run.add_argument("--workspace", default=None)
    run.add_argument("--session-id", default=None)
    run.set_defaults(func=cmd_run)

    l = sub.add_parser("list", help="列出全部")
    l.set_defaults(func=cmd_list)

    n = sub.add_parser("next-close", help="返回应关闭的最旧会话 id")
    n.set_defaults(func=cmd_next_close)

    a = sub.add_parser("archive", help="归档一个会话实例")
    a.add_argument("--id", required=True)
    a.add_argument("--reason", default=None)
    a.set_defaults(func=cmd_archive)

    m = sub.add_parser("set-mode", help="切换模式")
    m.add_argument("--mode", choices=["rotate", "onesession"], default=None)
    m.add_argument("--max", type=int, default=None)
    m.set_defaults(func=cmd_set_mode)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

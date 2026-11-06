# -*- coding: utf-8 -*-
"""端口登记表：谁（哪个项目）占了哪个端口。

为什么要有登记表：
- 「端口空闲」是瞬时状态，两个 Agent 同时起服务会同时看到同一个空端口；
- 登记 + 预留 + 释放，让分配变成**可协调**的动作，而不是各扫各的。
"""
from __future__ import annotations

import datetime
import json
import os
import time

DEFAULT_REGISTRY = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "port_registry.json"
)
FALLBACK_REGISTRY = os.path.join(os.path.expanduser("~"), ".port-doctor", "registry.json")


def registry_path() -> str:
    env = os.environ.get("PORTDOCTOR_REGISTRY")
    if env:
        return env
    home = os.path.expanduser("~")
    if os.path.isdir(os.path.join(home, ".workbuddy")):
        return DEFAULT_REGISTRY
    return FALLBACK_REGISTRY


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load() -> dict:
    p = registry_path()
    if not os.path.exists(p):
        return {"entries": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"entries": []}
    if not isinstance(data, dict):
        return {"entries": []}
    data.setdefault("entries", [])
    return data


def save(data: dict) -> str:
    p = registry_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return p


def register(port: int, project_path: str, project_name: str = "", pid=None,
             proc: str = "", cmdline: str = "", reason: str = "manual") -> dict:
    data = load()
    entry = {
        "port": int(port),
        "project_path": str(project_path),
        "project_name": project_name or os.path.basename(str(project_path)),
        "pid": pid,
        "proc": proc,
        "cmdline": cmdline[:200],
        "reason": reason,
        "status": "active",
        "allocated_at": _now(),
    }
    # 同端口旧记录标记为 released，避免重复登记
    for e in data["entries"]:
        if e.get("port") == int(port) and e.get("status") == "active":
            e["status"] = "superseded"
            e["released_at"] = _now()
    data["entries"].append(entry)
    save(data)
    return entry


def release(port=None, project_path=None) -> list:
    """释放登记。给 port 或 project_path 之一即可。"""
    data = load()
    hit = []
    for e in data["entries"]:
        if e.get("status") != "active":
            continue
        if port is not None and e.get("port") != int(port):
            continue
        if project_path is not None and os.path.normcase(e.get("project_path", "")) != \
                os.path.normcase(str(project_path)):
            continue
        e["status"] = "released"
        e["released_at"] = _now()
        hit.append(e)
    if hit:
        save(data)
    return hit


def entries(active_only: bool = True) -> list:
    data = load()
    rows = data["entries"]
    return [e for e in rows if not active_only or e.get("status") == "active"]


def gc_stale() -> list:
    """把 pid 已死的 active 记录标为 stale（进程崩了但登记还在）"""
    from allocator import pid_alive  # 延迟导入，避免循环依赖
    data = load()
    changed = []
    for e in data["entries"]:
        if e.get("status") != "active":
            continue
        pid = e.get("pid")
        if pid and not pid_alive(int(pid)):
            e["status"] = "stale"
            e["released_at"] = _now()
            changed.append(e)
    if changed:
        save(data)
    return changed


def active_ports() -> set:
    return {int(e["port"]) for e in entries(active_only=True) if e.get("port")}

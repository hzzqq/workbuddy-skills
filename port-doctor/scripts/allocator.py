# -*- coding: utf-8 -*-
"""端口探测 / 分配 / 归属判定。

为什么不用 netstat 作为唯一判据：
- netstat 在 Windows 上要解析 LISTENING 状态、IPv4/IPv6 双行、外文系统语言差异；
- 更可靠的是 **主动 bind 测试**（能不能绑上 = 有没有人占）。
  所以：bind 测试定"是否被占"，netstat 只用来回答"被谁占"。
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass

IS_WINDOWS = os.name == "nt"
DEFAULT_POOL = (5100, 5999)
DEFAULT_ENV_FILE = ".port.env"


# --------------------------------------------------------------------------
# 占用判定
# --------------------------------------------------------------------------
def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """能否绑定该端口。Windows 下用 SO_EXCLUSIVEADDRUSE，避免"看似能绑实则被占"的误判。"""
    if not (1 <= port <= 65535):
        return False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if IS_WINDOWS:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def port_available(port: int, host: str = "127.0.0.1") -> bool:
    """is_port_free 的别名（语义更顺口）"""
    return is_port_free(port, host)


# --------------------------------------------------------------------------
# 谁占了
# --------------------------------------------------------------------------
@dataclass
class Owner:
    pid: int
    proc: str
    cmdline: str = ""
    local: str = ""


def _run(cmd) -> str:
    try:
        # 必须显式指定编码：中文 Windows 下 tasklist/netstat 输出是 GBK，
        # 不指定会在 subprocess 读取线程里抛 UnicodeDecodeError（表现为 pytest 告警）。
        # Windows 用 mbcs（系统 ANSI 代码页=GBK），其它平台用 utf-8。
        enc = "mbcs" if IS_WINDOWS else "utf-8"
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                           encoding=enc, errors="replace")
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def port_owners(port: int) -> list:
    """返回占用该端口的进程列表（尽力而为，失败返回空列表而不是编造）"""
    owners = []
    if IS_WINDOWS:
        out = _run(["netstat", "-ano", "-p", "TCP"])
        for line in out.splitlines():
            if "LISTENING" not in line.upper():
                continue
            m = re.search(r":(\d+)\s+\S+\s+LISTENING\s+(\d+)", line)
            if not m:
                continue
            if int(m.group(1)) != port:
                continue
            pid = int(m.group(2))
            owners.append(Owner(pid=pid, proc=process_name(pid), cmdline=process_cmdline(pid),
                                local=line.strip()))
    else:
        out = _run(["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN"])
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                pid = int(parts[1])
                owners.append(Owner(pid=pid, proc=parts[0], cmdline=" ".join(parts[8:])[:200]))
    return owners


def process_name(pid: int) -> str:
    if IS_WINDOWS:
        out = _run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"])
        for line in out.splitlines():
            # 注意：pid 必须转成字符串再匹配，行是 str
            if str(pid) in line and line.strip() and "INFO" not in line.upper():
                parts = line.split()
                if parts:
                    return parts[0]
        return "?"
    out = _run(["ps", "-p", str(pid), "-o", "comm="])
    return out.strip() or "?"


def process_cmdline(pid: int) -> str:
    """取进程命令行。拿不到就返回空串，绝不臆造。

    注意：刻意**不使用 wmic** —— 新版 Windows 已弃用 wmic，且部分安全策略把它列入黑名单，
    调用会直接被拦。这里只用 PowerShell 的 CIM 接口。
    """
    if IS_WINDOWS:
        out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % pid])
        return out.strip()[:300]
    out = _run(["ps", "-p", str(pid), "-o", "args="])
    return out.strip()[:300]


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        out = _run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"])
        return str(pid) in out and "INFO" not in out.upper()
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# 系统保留端口段
# --------------------------------------------------------------------------
_EXCL_CACHE = None


def excluded_port_ranges() -> list:
    """Windows Hyper-V / WSL 会保留大段动态端口，分配时必须避开。其它平台返回空。"""
    global _EXCL_CACHE
    if _EXCL_CACHE is not None:
        return _EXCL_CACHE
    ranges = []
    if IS_WINDOWS:
        out = _run(["netsh", "int", "ipv4", "show", "excludedportrange", "protocol=tcp"])
        for m in re.finditer(r"(\d+)\s+(\d+)", out):
            ranges.append((int(m.group(1)), int(m.group(2))))
    _EXCL_CACHE = ranges
    return ranges


def in_excluded_range(port: int, ranges=None) -> bool:
    for lo, hi in (ranges if ranges is not None else excluded_port_ranges()):
        if lo <= port <= hi:
            return True
    return False


# --------------------------------------------------------------------------
# 分配
# --------------------------------------------------------------------------
def allocate_port(pool=DEFAULT_POOL, prefer=None, exclude=None, host: str = "127.0.0.1") -> int:
    """从端口池里挑一个真正能绑的端口。找不到就抛 RuntimeError（绝不返回占用的端口）。"""
    exclude = set(exclude or ())
    if prefer:
        if prefer not in exclude and 1 <= prefer <= 65535 and is_port_free(prefer, host) \
                and not in_excluded_range(prefer):
            return prefer
    lo, hi = pool
    for p in range(lo, hi + 1):
        if p in exclude:
            continue
        if in_excluded_range(p):
            continue
        if is_port_free(p, host):
            return p
    raise RuntimeError("端口池 %d-%d 内没有空闲端口，请扩大池或先释放占用" % (lo, hi))


# --------------------------------------------------------------------------
# 项目侧端口环境文件
# --------------------------------------------------------------------------
def port_env_path(project_path) -> str:
    return os.path.join(str(project_path), DEFAULT_ENV_FILE)


def write_port_env(project_path, port: int) -> str:
    """写 <project>/.port.env（PORT=xxxx），供启动脚本 source / dotenv 读取"""
    p = port_env_path(project_path)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 由 port-doctor 自动生成（端口冲突自动分配）\n")
        f.write("PORT=%d\n" % port)
    return p


def read_port_env(project_path) -> int:
    p = port_env_path(project_path)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\s*PORT\s*=\s*(\d+)\s*$", line)
                if m:
                    return int(m.group(1))
    except OSError:
        return None
    return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "free"
    if cmd == "free":
        port = int(argv[1]) if len(argv) > 1 else 5100
        print("free" if is_port_free(port) else "busy")
    elif cmd == "owners":
        for o in port_owners(int(argv[1])):
            print("%d\t%s\t%s" % (o.pid, o.proc, o.cmdline[:120]))
    elif cmd == "alloc":
        print(allocate_port(prefer=int(argv[1]) if len(argv) > 1 else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

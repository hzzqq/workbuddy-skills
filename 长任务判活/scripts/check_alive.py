#!/usr/bin/env python
"""长任务判活：用 CPU 时间增量判断进程是真的在算，还是空闲/僵死。

为什么需要它：阶段式打印的长任务（每 epoch 才输出一行）在日志上会长时间静止，
仅凭日志时间戳或进程是否存在无法区分「正常在跑」与「已卡死」。

判据：采样窗口内 CPU 时间的增量。
  增量 ≈ 线程数 × 窗口秒数  -> 满载运行
  增量 ≈ 0                  -> 空闲/僵死

用法：
    python check_alive.py                      # 自动挑内存最大的 python 进程
    python check_alive.py --pid 12345
    python check_alive.py --name python.exe --sample 20
    python check_alive.py --pid 12345 --json

退出码：
    0 = 正在运行
    1 = 空闲 / 停滞
    2 = 未找到目标进程
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wintypes
import json
import re
import subprocess
import sys
import time

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD)]


def _ft_to_seconds(ft: _FILETIME) -> float:
    return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7


def list_processes(name: str) -> list[tuple[int, int]]:
    """返回 [(pid, mem_kb)]，按内存降序。

    注意：内存字段可能是 "12 K" 这类短串，正则必须容忍，
    否则会漏掉所有小进程（曾导致误报「无进程」）。
    """
    try:
        raw = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception as e:                                       # pragma: no cover
        print(f"tasklist 调用失败: {e}", file=sys.stderr)
        return []

    pat = re.compile(rf'"{re.escape(name)}","(\d+)","[^"]*","[^"]*","([\d,]+) K"')
    out: list[tuple[int, int]] = []
    for line in raw.strip().splitlines():
        m = pat.match(line.strip())
        if m:
            out.append((int(m.group(1)), int(m.group(2).replace(",", ""))))
    out.sort(key=lambda x: -x[1])
    return out


def cpu_seconds(k32, pid: int):
    """返回该进程的累计 CPU 秒数（kernel + user），失败返回 None。"""
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        c, e, k, u = _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
        ok = k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e),
                                 ctypes.byref(k), ctypes.byref(u))
        if not ok:
            return None
        return _ft_to_seconds(k) + _ft_to_seconds(u)
    finally:
        k32.CloseHandle(h)


def main() -> int:
    ap = argparse.ArgumentParser(description="长任务判活（CPU 时间增量）")
    ap.add_argument("--pid", type=int, help="目标 PID（省略则自动挑选）")
    ap.add_argument("--name", default="python.exe", help="进程名，默认 python.exe")
    ap.add_argument("--sample", type=float, default=12.0, help="采样窗口秒数，默认 12")
    ap.add_argument("--busy-ratio", type=float, default=0.66,
                    help="判定为「满载」的 CPU/窗口 比值下限，默认 0.66")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    if sys.platform != "win32":
        print("本脚本面向 Windows。Linux/macOS 请用："
              "两次采样 `cat /proc/<pid>/stat | awk '{print $14+$15}'` 比较增量。",
              file=sys.stderr)
        return 2

    k32 = ctypes.windll.kernel32
    result: dict = {"name": args.name, "sample_seconds": args.sample}

    if args.pid:
        pid = args.pid
        procs = list_processes(args.name)
        mem = next((m for p, m in procs if p == pid), None)
        if mem is None:
            mem = 0
    else:
        procs = list_processes(args.name)
        if not procs:
            print(f"未找到进程 {args.name}（退出码 2）", file=sys.stderr)
            if args.json:
                print(json.dumps({"found": False, "name": args.name}))
            return 2
        pid, mem = procs[0]

    t0 = cpu_seconds(k32, pid)
    if t0 is None:
        print(f"无法读取 PID {pid} 的 CPU 时间（进程可能已退出）", file=sys.stderr)
        if args.json:
            print(json.dumps({"found": False, "pid": pid}))
        return 2

    time.sleep(args.sample)
    t1 = cpu_seconds(k32, pid)
    if t1 is None:
        print(f"PID {pid} 在采样期间退出", file=sys.stderr)
        if args.json:
            print(json.dumps({"found": True, "pid": pid, "alive": False}))
        return 1

    delta = t1 - t0
    busy_ratio = delta / args.sample if args.sample > 0 else 0.0
    running = busy_ratio >= args.busy_ratio

    result.update({
        "found": True, "pid": pid, "mem_mb": round(mem / 1024, 1),
        "cpu_total_s": round(t1, 1), "cpu_delta_s": round(delta, 1),
        "busy_ratio": round(busy_ratio, 2), "running": running,
    })

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PID {pid} | 内存 {mem/1024:.0f} MB | "
              f"CPU 累计 {t1:.0f}s（{args.sample:.0f}s 内 +{delta:.0f}s，"
              f"占用比 {busy_ratio:.2f}）")
        if running:
            print("✅ 正在运行（CPU 时间在增长）")
        else:
            print("⚠️ 空闲或停滞 —— 若预期它在算，请前台重跑 --smoke 看真实报错")
    return 0 if running else 1


if __name__ == "__main__":
    sys.exit(main())

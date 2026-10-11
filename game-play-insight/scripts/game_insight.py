#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
game-play-insight 统一 CLI（纯标准库，零依赖）

子命令：
  start                启动本地收集服务（监听 localhost:8765，接收浏览器上报写盘）
  collect [--game ID] [--dir ROOT]   汇总事件 -> insight-<date>.json
  report  [--game ID] [--dir ROOT]   生成 Markdown 反馈报告
  feedback[--game ID] [--dir ROOT]   生成给 Hy3 的改良指令包
  demo                 造示例数据并跑通 collect -> report -> feedback（自测）

目录约定：
  <ROOT>/<gameId>/events/YYYY-MM-DD.jsonl   事件落盘
  <ROOT>/<gameId>/insight-<date>.json      机器可读汇总
  <ROOT>/<gameId>/report-<date>.md         人读反馈报告
  <ROOT>/<gameId>/feedback-<date>.md       给 Hy3 的改良指令包
ROOT 默认 = 当前目录/.game-telemetry，可用环境变量 GAME_TELEMETRY_DIR 覆盖。
"""
import argparse
import datetime
import glob
import json
import os
import statistics
import tempfile
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_ROOT = os.environ.get("GAME_TELEMETRY_DIR") or os.path.join(os.getcwd(), ".game-telemetry")
PORT = int(os.environ.get("GAME_TELEMETRY_PORT", "8765"))


# ---------------- 工具 ----------------
def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def fmt_ts(ts):
    if isinstance(ts, (int, float)):
        if ts > 1e11:
            ts = ts / 1000
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(ts)
    return str(ts)


def pct(x):
    return f"{int(round(x * 100))}%" if isinstance(x, (int, float)) else "-"


def auto_first_name(root):
    if os.path.isdir(root):
        for n in sorted(os.listdir(root)):
            if os.path.isdir(os.path.join(root, n)):
                return n
    return "unknown"


def events_dir(root, game_id):
    if game_id:
        return os.path.join(root, game_id, "events")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name, "events")
            if os.path.isdir(p):
                return p
    return os.path.join(root, "unknown", "events")


def load_events(root, game_id):
    ed = events_dir(root, game_id)
    evs = []
    if os.path.isdir(ed):
        for fp in sorted(glob.glob(os.path.join(ed, "*.jsonl"))):
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            evs.append(json.loads(line))
                        except Exception:
                            pass
    return evs


def game_out_dir(root, game_id):
    return os.path.join(root, game_id) if game_id else os.path.join(root, auto_first_name(root))


# ---------------- 本地收集服务 ----------------
class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/event":
            self.send_response(404)
            self.end_headers()
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            ev = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return
        if not isinstance(ev, list):
            ev = [ev]
        for item in ev:
            if not isinstance(item, dict):
                continue
            gid = item.get("gameId", "unknown")
            ts = item.get("ts")
            if isinstance(ts, (int, float)):
                try:
                    d = datetime.date.fromtimestamp(ts).isoformat()
                except Exception:
                    d = datetime.date.today().isoformat()
            else:
                d = datetime.date.today().isoformat()
            p = os.path.join(DEFAULT_ROOT, gid, "events", d + ".jsonl")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


def serve():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), _Handler)
    print(f"✓ collector 监听 http://localhost:{PORT}  (Ctrl+C 停止，数据已落盘不丢)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ collector 已停止")


# ---------------- 汇总 ----------------
def collect(root, game_id):
    evs = load_events(root, game_id)
    if not evs:
        print("! 没有采集到任何事件。请先 start 收集服务并游玩，或运行 demo。")
        return None, None
    sessions = {}
    levels = {}
    errors = {}
    death_pts = []
    death_dist = Counter()
    paths = {}
    for e in evs:
        sid = e.get("session_id", "na")
        t = e.get("ts")
        ts = t / 1000 if isinstance(t, (int, float)) and t > 1e11 else t
        s = sessions.setdefault(sid, {"start": ts, "end": ts})
        if isinstance(ts, (int, float)):
            s["start"] = min(s["start"], ts) if isinstance(s["start"], (int, float)) else ts
            s["end"] = max(s["end"], ts) if isinstance(s["end"], (int, float)) else ts
        pl = e.get("payload", {}) or {}
        paths.setdefault(sid, []).append(e.get("type"))
        et = e.get("type")
        if et == "level_start":
            lv = pl.get("level")
            levels.setdefault(lv, {"start": 0, "complete": 0, "fail": 0, "times": []})
            levels[lv]["start"] += 1
        elif et == "level_complete":
            lv = pl.get("level")
            levels.setdefault(lv, {"start": 0, "complete": 0, "fail": 0, "times": []})
            levels[lv]["complete"] += 1
            if pl.get("timeSec") is not None:
                levels[lv]["times"].append(pl["timeSec"])
        elif et == "level_fail":
            lv = pl.get("level")
            levels.setdefault(lv, {"start": 0, "complete": 0, "fail": 0, "times": []})
            levels[lv]["fail"] += 1
        elif et == "error":
            msg = pl.get("message", "?")
            errors[msg] = errors.get(msg, 0) + 1
        elif et == "death":
            lv = pl.get("floor") if pl.get("floor") is not None else pl.get("day")
            if lv is not None:
                death_pts.append(lv)
                death_dist[lv] += 1

    durations = []
    for s in sessions.values():
        if isinstance(s["start"], (int, float)) and isinstance(s["end"], (int, float)) and s["end"] > s["start"]:
            durations.append(s["end"] - s["start"])

    level_ins = []
    for lv, d in sorted(levels.items(), key=lambda x: (x[0] is None, x[0])):
        total = d["complete"] + d["fail"]
        level_ins.append({
            "level": lv,
            "starts": d["start"],
            "completes": d["complete"],
            "fails": d["fail"],
            "pass_rate": round(d["complete"] / total, 3) if total else None,
            "fail_rate": round(d["fail"] / total, 3) if total else None,
            "avg_time_sec": round(statistics.mean(d["times"]), 1) if d["times"] else None,
        })

    stuck = [l for l in level_ins if l["fail_rate"] is not None and (l["completes"] + l["fails"]) >= 3]
    stuck.sort(key=lambda x: x["fail_rate"], reverse=True)

    suggestions = []
    for l in stuck:
        if l["fail_rate"] >= 0.6:
            suggestions.append({
                "level": l["level"],
                "issue": f"关卡 {l['level']} 失败率 {int(l['fail_rate']*100)}%（{l['fails']}/{l['completes']+l['fails']}），疑似过难",
                "action": "降低难度 / 增加提示 / 调整时间或资源",
                "verify": f"改完后该关失败率应降至 <40%",
            })
    for msg, cnt in sorted(errors.items(), key=lambda x: -x[1])[:5]:
        suggestions.append({
            "level": "global",
            "issue": f"运行时报错 ×{cnt}：{msg}",
            "action": "定位并修复该异常（见 error 事件 stack）",
            "verify": "复玩后 error 事件归零",
        })
    # 死亡集中点（领域无关的通用卡点指标：地牢=层 / 生存=天）
    total_deaths = len(death_pts)
    top_death_point = None
    if total_deaths:
        dl, dc = death_dist.most_common(1)[0]
        top_death_point = {"point": dl, "deaths": dc, "share": round(dc / total_deaths, 3)}
        if dc >= 3 and dc / total_deaths >= 0.3:
            suggestions.append({
                "level": dl,
                "issue": f"玩家在 第 {dl} 层/天 死亡最集中（{dc} 次，占全部死亡 {int(dc / total_deaths * 100)}%），疑似该处难度陡增或引导缺失",
                "action": "检查该层/天的敌人强度、资源供给与引导提示；适当下调难度或增加正反馈",
                "verify": "下一轮数据该点死亡占比应明显下降",
            })

    ts_vals = [e["ts"] / 1000 if isinstance(e.get("ts"), (int, float)) and e["ts"] > 1e11 else e["ts"] for e in evs if isinstance(e.get("ts"), (int, float))]
    path_counter = Counter(tuple(p) for p in paths.values())
    top_paths = [list(p) for p, _ in path_counter.most_common(5)]

    insight = {
        "generated_at": now_iso(),
        "game_id": game_id or "(auto)",
        "total_sessions": len(sessions),
        "total_events": len(evs),
        "date_range": [min(ts_vals) if ts_vals else None, max(ts_vals) if ts_vals else None],
        "avg_session_sec": round(statistics.mean(durations), 1) if durations else None,
        "median_session_sec": round(statistics.median(durations), 1) if durations else None,
        "levels": level_ins,
        "stuck_top": stuck[0] if stuck else None,
        "errors": dict(sorted(errors.items(), key=lambda x: -x[1])[:10]),
        "death_distribution": dict(death_dist.most_common(10)),
        "top_death_point": top_death_point,
        "top_paths": top_paths,
        "suggestions": suggestions,
    }
    gd = game_out_dir(root, game_id)
    os.makedirs(gd, exist_ok=True)
    out = os.path.join(gd, f"insight-{datetime.date.today().isoformat()}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insight, f, ensure_ascii=False, indent=2)
    print("✓ 汇总完成 →", out)
    print(f"  sessions={insight['total_sessions']}  events={insight['total_events']}  suggestions={len(suggestions)}")
    return insight, out


def latest_insight(root, game_id):
    gd = game_out_dir(root, game_id)
    files = sorted(glob.glob(os.path.join(gd, "insight-*.json")), reverse=True)
    if not files:
        return None, None
    with open(files[0], encoding="utf-8") as f:
        return json.load(f), files[0]


# ---------------- 报告 ----------------
def report(root, game_id):
    ins, fpath = latest_insight(root, game_id)
    if not ins:
        print("! 没有 insight，请先 collect。")
        return
    L = []
    L.append(f"# 玩家反馈报告 · {ins['game_id']}")
    L.append(f"> 生成时间 {ins['generated_at']}")
    L.append("")
    L.append("## 总览")
    L.append(f"- 会话数（去重玩家）：**{ins['total_sessions']}**")
    L.append(f"- 事件总数：{ins['total_events']}")
    L.append(f"- 平均会话时长：{ins['avg_session_sec']}s（中位 {ins['median_session_sec']}s）")
    L.append(f"- 时间范围：{fmt_ts(ins['date_range'][0])} ~ {fmt_ts(ins['date_range'][1])}")
    L.append("")
    L.append("## 关卡进度与卡点")
    L.append("| 关卡 | 进入 | 完成 | 失败 | 通过率 | 平均耗时 |")
    L.append("|---|---|---|---|---|---|")
    if ins["levels"]:
        for l in ins["levels"]:
            L.append(f"| {l['level']} | {l['starts']} | {l['completes']} | {l['fails']} | {pct(l['pass_rate'])} | {l['avg_time_sec']}s |")
    else:
        L.append("| — | — | — | — | — | — |")
        L.append("\n_（未使用 `level_start/level_complete/level_fail` 事件；难度卡点请见下方「死亡集中点」）_")
    if ins["stuck_top"]:
        s = ins["stuck_top"]
        L.append(f"\n**🔴 最严重卡点：关卡 {s['level']}（失败率 {pct(s['fail_rate'])}）**")
    L.append("")
    L.append("## 运行时报错")
    if ins["errors"]:
        for msg, cnt in ins["errors"].items():
            L.append(f"- ×{cnt} `{msg}`")
    else:
        L.append("- 无")
    L.append("")
    L.append("## 死亡集中点")
    if ins.get("top_death_point"):
        td = ins["top_death_point"]
        L.append(f"- 最集中：**第 {td['point']} 层/天**，{td['deaths']} 次死亡（占 {pct(td['share'])}）")
        if ins.get("death_distribution"):
            L.append("- 分布：" + "、".join(f"第{k}层/天 {v}次" for k, v in ins["death_distribution"].items()))
    else:
        L.append("- 无死亡数据")
    L.append("")
    L.append("## 高频行为路径")
    for p in ins["top_paths"]:
        L.append(f"- {' → '.join(map(str, p))}")
    L.append("")
    L.append("## 改良建议（自动生成）")
    if ins["suggestions"]:
        for i, s in enumerate(ins["suggestions"], 1):
            L.append(f"{i}. **[{s['level']}]** {s['issue']}")
            L.append(f"   - 动作：{s['action']}")
            L.append(f"   - 验收：{s['verify']}")
    else:
        L.append("- 暂无（数据量不足或未达阈值）")
    md = "\n".join(L)
    gd = os.path.dirname(fpath) if fpath else game_out_dir(root, game_id)
    out = os.path.join(gd, f"report-{datetime.date.today().isoformat()}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("✓ 报告已生成 →", out)
    print("--- 预览 ---")
    print(md[:1400])


# ---------------- 反馈指令包 ----------------
def feedback(root, game_id):
    ins, fpath = latest_insight(root, game_id)
    if not ins:
        print("! 没有 insight，请先 collect。")
        return
    L = []
    L.append(f"# 游戏改良指令包 · {ins['game_id']}")
    L.append(f"> 供「开发游戏的 AI（Hy3 / WorkBuddy）」消费 · 生成 {ins['generated_at']}")
    L.append("")
    L.append("## 背景")
    L.append(f"基于 {ins['total_sessions']} 个会话、{ins['total_events']} 条游玩事件自动生成。")
    L.append("")
    L.append("## 必须处理的核心问题")
    items = []
    if ins["stuck_top"]:
        s = ins["stuck_top"]
        items.append(f"- 关卡 {s['level']} 失败率 {pct(s['fail_rate'])}（{s['fails']} 次失败），玩家在此大量流失")
    for msg, cnt in list(ins["errors"].items())[:3]:
        items.append(f"- 运行时报错 `{msg}` ×{cnt}，影响稳定性")
    if ins.get("top_death_point"):
        td = ins["top_death_point"]
        items.append(f"- 死亡最集中：第 {td['point']} 层/天（{td['deaths']} 次，占 {pct(td['share'])}）")
    if not items:
        items.append("- 暂无严重问题")
    L += items
    L.append("")
    L.append("## 具体改良任务（请逐项执行）")
    if ins["suggestions"]:
        for i, s in enumerate(ins["suggestions"], 1):
            L.append(f"{i}. **{s['issue']}**")
            L.append(f"   - 建议动作：{s['action']}")
            L.append(f"   - 验收标准：{s['verify']}")
    else:
        L.append("- 暂无需强制改动")
    L.append("")
    L.append("## 下一步")
    L.append("请 Hy3（WorkBuddy）读取本报告，定位游戏代码中的对应关卡 / 报错，")
    L.append("完成改良后，请玩家再次游玩并用本 skill 的 collect → feedback 验证指标是否改善（失败率下降、报错归零）。")
    md = "\n".join(L)
    gd = os.path.dirname(fpath) if fpath else game_out_dir(root, game_id)
    out = os.path.join(gd, f"feedback-{datetime.date.today().isoformat()}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("✓ 改良指令包已生成 →", out)
    print("⮕ 把这份报告交给 Hy3，即可启动游戏改良闭环。")


# ---------------- 自测 ----------------
def demo():
    root = tempfile.mkdtemp(prefix="gpi-demo-")
    gid = "demo-game"
    ed = os.path.join(root, gid, "events")
    os.makedirs(ed, exist_ok=True)
    base = time.time()

    def ev(off, sid, typ, pl=None):
        return {"ts": base + off, "session_id": sid, "type": typ, "gameId": gid,
                "payload": pl or {}, "ua": "demo", "page": "index.html"}

    rows = []
    # 会话 A：顺利通关
    rows += [ev(0, "A", "session_start"), ev(1, "A", "level_start", {"level": 1}),
             ev(6, "A", "level_complete", {"level": 1, "timeSec": 5}),
             ev(7, "A", "level_start", {"level": 2}), ev(20, "A", "level_complete", {"level": 2, "timeSec": 13}),
             ev(21, "A", "level_start", {"level": 3}), ev(40, "A", "level_complete", {"level": 3, "timeSec": 19}),
             ev(41, "A", "session_end")]
    # 会话 B：卡在关卡 3（超时失败）
    rows += [ev(0, "B", "session_start"), ev(1, "B", "level_start", {"level": 1}),
             ev(4, "B", "level_complete", {"level": 1, "timeSec": 3}),
             ev(5, "B", "level_start", {"level": 2}), ev(15, "B", "level_complete", {"level": 2, "timeSec": 10}),
             ev(16, "B", "level_start", {"level": 3}), ev(40, "B", "level_fail", {"level": 3, "reason": "timeout"}),
             ev(41, "B", "level_start", {"level": 3}), ev(70, "B", "level_fail", {"level": 3, "reason": "timeout"}),
             ev(71, "B", "level_start", {"level": 3}), ev(100, "B", "level_fail", {"level": 3, "reason": "timeout"}),
             ev(101, "B", "session_end")]
    # 会话 C：报错 + 关卡 2 崩溃
    rows += [ev(0, "C", "session_start"), ev(1, "C", "level_start", {"level": 1}),
             ev(3, "C", "level_complete", {"level": 1, "timeSec": 2}),
             ev(4, "C", "error", {"message": "TypeError: cannot read prop of undefined", "stack": "at onClick"}),
             ev(5, "C", "level_start", {"level": 2}), ev(30, "C", "level_fail", {"level": 2, "reason": "crash"}),
             ev(31, "C", "session_end")]
    fp = os.path.join(ed, datetime.date.today().isoformat() + ".jsonl")
    with open(fp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("✓ demo 数据已写入", fp)
    collect(root, gid)
    report(root, gid)
    feedback(root, gid)
    print("\n✓ demo 结束。临时目录（可删）：", root)


# ---------------- 入口 ----------------
def main():
    ap = argparse.ArgumentParser(prog="game_insight.py", description="网页小游戏游玩数据收集与反馈闭环")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("start")
    pc = sub.add_parser("collect")
    pc.add_argument("--game")
    pc.add_argument("--dir")
    pr = sub.add_parser("report")
    pr.add_argument("--game")
    pr.add_argument("--dir")
    pf = sub.add_parser("feedback")
    pf.add_argument("--game")
    pf.add_argument("--dir")
    sub.add_parser("demo")
    args = ap.parse_args()

    if args.cmd == "start":
        serve()
        return
    if args.cmd == "demo":
        demo()
        return
    root = getattr(args, "dir", None) or DEFAULT_ROOT
    gid = getattr(args, "game", None)
    if args.cmd == "collect":
        collect(root, gid)
    elif args.cmd == "report":
        report(root, gid)
    elif args.cmd == "feedback":
        feedback(root, gid)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

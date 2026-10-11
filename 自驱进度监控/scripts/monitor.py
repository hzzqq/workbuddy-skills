#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev-supervisor · 监督 AI 自驱动开发项目的进度看板
读取各项目 .workbuddy/self-driving/state.json，展示 cycle/max_cycles 进度。

用法:
  python monitor.py bar  [--root E:\\project]
        -> 终端 ASCII 进度条（快速查看，零依赖）
  python monitor.py serve [--root E:\\project] [--host 127.0.0.1] [--port 8790]
        -> 启动本地看板，浏览器打开后底部有实时进度条，每 2s 自动刷新
"""
import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE_REL = os.path.join(".workbuddy", "self-driving", "state.json")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
              ".idea", ".vscode", "dist", "build"}

ROOT = "E:\\project"


def find_state_files(root):
    res = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        if os.path.basename(dp) == "self-driving" and "state.json" in fn:
            sp = os.path.join(dp, "state.json")
            proj = os.path.dirname(os.path.dirname(dp))
            res.append((proj, sp))
    return res


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def project_info(proj, sp):
    name = os.path.basename(proj.rstrip(os.sep))
    d = load_state(sp)
    if d is None:
        return {"name": name, "path": proj, "ok": False, "error": "读取/解析失败"}
    try:
        cyc = int(d.get("cycle", 0) or 0)
        mx = int(d.get("max_cycles", 0) or 0)
    except Exception:
        return {"name": name, "path": proj, "ok": False, "error": "cycle/max_cycles 字段异常"}
    log = d.get("log") or []
    paused = bool(d.get("paused", False))
    prog = round(100.0 * cyc / mx, 1) if mx else None
    last = d.get("last_task_id")
    last_score = d.get("last_score")
    status = "paused" if paused else ("complete" if (mx and cyc >= mx) else "running")
    recent = []
    if isinstance(log, list):
        for t in log[-3:]:
            if isinstance(t, dict):
                recent.append({
                    "task_id": t.get("task_id"),
                    "req": t.get("new_requirement") or t.get("implicit") or "",
                    "score": t.get("score"),
                    "ts": t.get("ts"),
                })
    return {
        "name": name, "path": proj, "ok": True,
        "cycle": cyc, "max_cycles": mx, "progress": prog,
        "last_task_id": last, "last_score": last_score,
        "paused": paused, "status": status,
        "tasks_done": len(log) if isinstance(log, list) else 0,
        "recent": recent,
        "coverage": d.get("coverage"),
        "plan_note": d.get("plan_note"),
    }


def collect(root):
    out = []
    for proj, sp in find_state_files(root):
        out.append(project_info(proj, sp))
    out.sort(key=lambda x: (x.get("name") or ""))
    return out


def ascii_bar(pct, width=28):
    if pct is None:
        return "[" + "?" * width + "] N/A"
    pct = max(0.0, min(100.0, pct))
    filled = int(round(pct / 100.0 * width))
    return "[" + "\u2588" * filled + "\u00b7" * (width - filled) + f"] {pct:5.1f}%"


def cmd_bar(root):
    rows = collect(root)
    if not rows:
        print(f"在 {root} 下未找到任何 self-driving 项目（需含 {STATE_REL}）")
        return
    print(f"=== AI 自驱动开发进度看板 · 扫描根: {root} · 项目数: {len(rows)} · {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    for r in rows:
        if not r.get("ok"):
            print(f"  \u2717 {r['name']}: {r.get('error')}")
            continue
        prog = r["progress"]
        bar = ascii_bar(prog)
        flag = {"running": "\u25b6", "paused": "\u23f8", "complete": "\u2714"}.get(r["status"], "?")
        print(f"{flag} {r['name']}  (cycle {r['cycle']}/{r['max_cycles']}, 任务 {r['tasks_done']} 个, 上次得分 {r['last_score']})")
        print(f"   {bar}")
        for t in r["recent"]:
            req = (t.get("req") or "")[:60]
            print(f"   \u00b7 {t.get('task_id')}  [{t.get('score')}] {req}")
        print()
    prog_vals = [r["progress"] for r in rows if r.get("ok") and r.get("progress") is not None]
    if prog_vals:
        avg = sum(prog_vals) / len(prog_vals)
        print(f"--- 平均进度: {ascii_bar(avg)} ---")


PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 开发进度监督</title>
<style>
 :root{--bg:#0f0f23;--card:#1a1a2e;--bd:#2a2a44;--fg:#e6e6f0;--mut:#9aa0b5;--ok:#00d486;--warn:#ffb020;--bad:#ff4d4f;--acc:#667eea;}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:18px 18px 120px;}
 h1{font-size:18px;margin:0 0 4px}
 .sub{color:var(--mut);font-size:12px;margin-bottom:14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
 .card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px}
 .card h2{font-size:15px;margin:0 0 8px;display:flex;align-items:center;gap:8px}
 .badge{font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--bd)}
 .b-run{color:var(--ok);border-color:var(--ok)} .b-pause{color:var(--warn);border-color:var(--warn)} .b-done{color:var(--acc);border-color:var(--acc)}
 .pbar{height:14px;background:#0c0c1c;border-radius:8px;overflow:hidden;border:1px solid var(--bd)}
 .pfill{height:100%;background:linear-gradient(90deg,#667eea,#764ba2);width:0%}
 .pmeta{display:flex;justify-content:space-between;color:var(--mut);font-size:12px;margin:6px 0 10px}
 .tasks{list-style:none;padding:0;margin:0;font-size:12px}
 .tasks li{padding:5px 0;border-top:1px solid var(--bd)}
 .tasks .tid{color:var(--acc)} .tasks .sc{color:var(--mut);float:right}
 .empty{color:var(--bad)}
 #foot{position:fixed;left:0;right:0;bottom:0;background:rgba(16,16,35,.96);border-top:1px solid var(--bd);padding:8px 14px;display:flex;gap:18px;overflow-x:auto}
 #foot .fitem{min-width:200px}
 #foot .fname{font-size:11px;color:var(--mut);margin-bottom:3px;white-space:nowrap}
 #foot .fbar{height:8px;background:#0c0c1c;border-radius:6px;overflow:hidden;border:1px solid var(--bd)}
 #foot .ffill{height:100%;background:linear-gradient(90deg,#667eea,#764ba2);width:0%}
 #foot .fpct{font-size:10px;color:var(--mut);float:right}
 .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
 .d-run{background:var(--ok)} .d-pause{background:var(--warn)} .d-done{background:var(--acc)}
</style></head>
<body>
 <h1>\ud83d\udee0\ufe0f AI 自驱动开发 · 进度监督台</h1>
 <div class="sub" id="sub">加载中…</div>
 <div class="grid" id="grid"></div>
 <div id="foot"></div>
<script>
const STATUS={running:["运行中","d-run"],paused:["已暂停","d-pause"],complete:["已完成","d-done"]};
function esc(s){return (s==null?"":String(s));}
function pbar(pct){if(pct==null)return["0%","?"];pct=Math.max(0,Math.min(100,pct));return[pct.toFixed(1)+"%",pct];}
function render(data){
 document.getElementById("sub").textContent="扫描根: "+data.root+" · 项目数: "+data.projects.length+" · 更新: "+new Date(data.ts*1000).toLocaleString();
 const grid=document.getElementById("grid");grid.innerHTML="";
 const foot=document.getElementById("foot");foot.innerHTML="";
 data.projects.forEach(p=>{
  const card=document.createElement("div");card.className="card";
  if(!p.ok){card.innerHTML='<h2>'+esc(p.name)+'</h2><div class="empty">'+esc(p.error||"状态异常")+'</div>';grid.appendChild(card);return;}
  const [ptxt,pw]=pbar(p.progress);
  const st=STATUS[p.status]||["未知","d-run"];
  let html='<h2>'+esc(p.name)+' <span class="badge '+st[1]+'">'+st[0]+'</span></h2>';
  html+='<div class="pbar"><div class="pfill" style="width:'+pw+'%"></div></div>';
  html+='<div class="pmeta"><span>cycle '+p.cycle+' / '+p.max_cycles+'</span><span>'+ptxt+'</span></div>';
  html+='<div class="pmeta"><span>已完成任务 '+p.tasks_done+'</span><span>上次得分 '+(p.last_score==null?"-":p.last_score)+'</span></div>';
  html+='<ul class="tasks">';
  (p.recent||[]).forEach(t=>{html+='<li><span class="tid">'+esc(t.task_id)+'</span><span class="sc">'+esc(t.score)+'</span><br>'+esc((t.req||"").slice(0,60))+'</li>';});
  html+='</ul>';
  card.innerHTML=html;grid.appendChild(card);
  const f=document.createElement("div");f.className="fitem";
  f.innerHTML='<div class="fname"><span class="dot '+st[1]+'"></span>'+esc(p.name)+'<span class="fpct">'+ptxt+'</span></div><div class="fbar"><div class="ffill" style="width:'+pw+'%"></div></div>';
  foot.appendChild(f);
 });
}
function tick(){fetch("/api/state").then(r=>r.json()).then(render).catch(()=>{});}
tick();setInterval(tick,2000);
</script>
</body></html>"""


def build_html():
    return PAGE


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            data = {"ts": time.time(), "root": ROOT, "projects": collect(ROOT)}
            self._send(200, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")
        elif self.path in ("/", "/index.html"):
            self._send(200, build_html())
        else:
            self._send(404, "not found")

    def log_message(self, *a):
        pass


def cmd_serve(root, host, port):
    global ROOT
    ROOT = root
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"dev-supervisor 看板已启动: http://{host}:{port}/  (root={root})")
    print("按 Ctrl+C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


def main():
    ap = argparse.ArgumentParser(description="dev-supervisor · AI 开发进度监督")
    sub = ap.add_subparsers(dest="cmd")
    rb = sub.add_parser("bar", help="终端 ASCII 进度条")
    rb.add_argument("--root", default="E:\\project")
    rs = sub.add_parser("serve", help="启动本地看板(底部实时进度条)")
    rs.add_argument("--root", default="E:\\project")
    rs.add_argument("--host", default="127.0.0.1")
    rs.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    if args.cmd == "serve":
        cmd_serve(args.root, args.host, args.port)
    else:
        cmd_bar(getattr(args, "root", "E:\\project"))


if __name__ == "__main__":
    main()

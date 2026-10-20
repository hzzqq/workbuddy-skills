#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat_bridge.py — 企业微信自建应用桥接（推送 + 反向接收）

能力：
  - push    : 把文本推送到老板的企业微信（应用消息）
  - serve   : 启动本地 HTTP 接收端点，接收老板在企业微信里发的指令（需公网回调 → 用 cloudflared 隧道）
  - test    : 自检配置 + 发一条测试推送

依赖：仅 Python 标准库（urllib/http.server/xml.etree）。
      接收端 AES 解密需 pycryptodome（pip install pycryptodome），缺失时 serve 会提示但不影响 push。

配置：~/.workbuddy/wechat_bridge/config.json
{
  "corpid":   "wwxxxxxxxxxxxxxxxx",
  "corpsecret":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "agentid":  1000002,
  "touser":   "boss",            # 老板在企业微信里的 userid
  "token":    "xxxxxx",          # 应用「接收消息」里填的 Token
  "aeskey":   "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # EncodingAESKey(43位)
}
"""
import sys, os, json, time, datetime, urllib.request, urllib.error

CFG_PATH = os.path.expanduser("~/.workbuddy/wechat_bridge/config.json")
TOKEN_CACHE = os.path.expanduser("~/.workbuddy/wechat_bridge/token_cache.json")
INBOX = os.path.expanduser("~/.workbuddy/wechat_bridge/inbox.jsonl")
PUSH_COUNT_PATH = os.path.expanduser("~/.workbuddy/wechat_bridge/push_count.json")
WX_API = "https://qyapi.weixin.qq.com/cgi-bin"

# Server酱 Turbo 免费额度：每天仅 5 条。脚本自身每天最多发 DAILY_LIMIT 条，
# 留少量余量给其他来源（手动/其他自动化）。可在 config.json 覆盖 serverchan_daily_limit。
SERVERCHAN_DAILY_LIMIT = 4


def _today():
    return datetime.date.today().isoformat()


def _load_push_count():
    if not os.path.exists(PUSH_COUNT_PATH):
        return {"date": _today(), "count": 0}
    try:
        with open(PUSH_COUNT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"date": _today(), "count": 0}


def _inc_push_count():
    c = _load_push_count()
    if c.get("date") != _today():
        c = {"date": _today(), "count": 0}
    c["count"] = c.get("count", 0) + 1
    try:
        with open(PUSH_COUNT_PATH, "w", encoding="utf-8") as f:
            json.dump(c, f)
    except Exception:
        pass
    return c["count"]


def _serverchan_used_today():
    c = _load_push_count()
    return c.get("count", 0) if c.get("date") == _today() else 0


def load_cfg():
    if not os.path.exists(CFG_PATH):
        print(f"[wechat-bridge] 配置文件缺失: {CFG_PATH}")
        print("请按 SKILL.md 指引创建（企业微信 corpid/secret/agentid/touser/token/aeskey）。")
        sys.exit(2)
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wechat-bridge/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "wechat-bridge/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def get_token(cfg, force=False):
    if not force and os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE, "r", encoding="utf-8") as f:
                c = json.load(f)
            if c.get("expires_at", 0) > time.time() + 300:
                return c["access_token"]
        except Exception:
            pass
    url = f"{WX_API}/gettoken?corpid={cfg['corpid']}&corpsecret={cfg['corpsecret']}"
    r = _http_get(url)
    if r.get("errcode", 0) != 0:
        print(f"[wechat-bridge] 获取 access_token 失败: {r}")
        sys.exit(3)
    tok = r["access_token"]
    with open(TOKEN_CACHE, "w", encoding="utf-8") as f:
        json.dump({"access_token": tok, "expires_at": time.time() + r.get("expires_in", 7200)}, f)
    return tok


def push(text, cfg=None, touser=None):
    cfg = cfg or load_cfg()
    ch = cfg.get("channel", "wecom_app")
    if ch == "pushplus":
        return push_plus(text, cfg)
    if ch == "serverchan":
        # 每日限额保护：Server酱 Turbo 免费仅 5 条/天，超限降级为 stdout 不实际发送
        lim = int(cfg.get("serverchan_daily_limit", SERVERCHAN_DAILY_LIMIT))
        used = _serverchan_used_today()
        if used >= lim:
            print(f"[wechat-bridge] 今日推送已达上限（{used}/{lim}），降级为 stdout，不实际发送")
            return False
        return push_serverchan(text, cfg)
    # 默认：企业微信自建应用消息
    tok = get_token(cfg)
    url = f"{WX_API}/message/send?access_token={tok}"
    body = {
        "touser": touser or cfg.get("touser", "@all"),
        "msgtype": "text",
        "agentid": cfg["agentid"],
        "text": {"content": text},
    }
    r = _http_post_json(url, body)
    if r.get("errcode", 0) != 0:
        print(f"[wechat-bridge] 企业微信推送失败: {r}")
        return False
    print("[wechat-bridge] 企业微信推送成功 ✓")
    return True


def push_plus(text, cfg):
    """PushPlus 通道：推送到老板个人微信（关注 pushplus.plus 公众号）。"""
    token = cfg.get("pushplus_token")
    if not token:
        print("[wechat-bridge] 缺少 pushplus_token —— config.json 需设 channel=pushplus 且填 pushplus_token")
        return False
    url = "https://www.pushplus.plus/send"
    body = {"token": token, "title": "📊 WorkBuddy 进度", "content": text}
    try:
        r = _http_post_json(url, body)
    except Exception as e:
        print(f"[wechat-bridge] PushPlus 请求异常: {e}")
        return False
    if r.get("code", 0) != 200:
        print(f"[wechat-bridge] PushPlus 推送失败: {r}")
        return False
    print("[wechat-bridge] PushPlus 推送成功 ✓")
    return True


def push_serverchan(text, cfg):
    """Server酱（方糖 sc.ftqq.com）通道：推送到老板个人微信（关注「方糖」公众号）。
    无实名、无备案、无公网服务器；仅需 SendKey。"""
    sendkey = cfg.get("serverchan_sendkey")
    if not sendkey:
        print("[wechat-bridge] 缺少 serverchan_sendkey —— config.json 需设 channel=serverchan 且填 serverchan_sendkey")
        return False
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    body = {"title": "📊 WorkBuddy 进度", "desp": text}
    try:
        # Server酱 用 form 表单提交（application/x-www-form-urlencoded）
        import urllib.parse
        data = urllib.parse.urlencode(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "wechat-bridge/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[wechat-bridge] Server酱 请求异常: {e}")
        return False
    if resp.get("code", 0) != 0:
        print(f"[wechat-bridge] Server酱 推送失败: {resp}")
        return False
    print("[wechat-bridge] Server酱 推送成功 ✓")
    _inc_push_count()
    return True


def _decrypt(aeskey_b64, cipher_b64):
    """AES-256-CBC 解密企业微信消息/echostr。需 pycryptodome。返回 msg 部分(bytes)。"""
    try:
        from Crypto.Cipher import AES
        import base64, struct
        aes_key = base64.b64decode(aeskey_b64 + "=")
        cipher = base64.b64decode(cipher_b64)
        iv = aes_key[:16]
        plain = AES.new(aes_key, AES.MODE_CBC, iv).decrypt(cipher)
        pad = plain[-1]
        if isinstance(pad, int) and 1 <= pad <= 32:
            plain = plain[:-pad]
        # 结构: 16字节随机 + 4字节msg_len(network) + msg + corpid
        content = plain[16:]
        msg_len = struct.unpack(">I", content[:4])[0]
        msg = content[4:4 + msg_len]
        return msg  # bytes
    except ImportError:
        print("[wechat-bridge] 接收解密需 pycryptodome: pip install pycryptodome")
        return None
    except Exception as e:
        print(f"[wechat-bridge] 解密失败: {e}")
        return None


def serve(port=8800):
    import http.server, hashlib, xml.etree.ElementTree as ET
    cfg = load_cfg()

    class H(http.server.BaseHTTPRequestHandler):
        def _verify(self, msg_signature, timestamp, nonce, data):
            import hashlib
            lst = sorted([cfg.get("token", ""), timestamp, nonce, data])
            s = hashlib.sha1("".join(lst).encode("utf-8")).hexdigest()
            return s == msg_signature

        def do_GET(self):
            # 企业微信 URL 验证
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            if self.path.startswith("/wechat") and "echostr" in q:
                # 简化：明文模式直接回显 echostr；安全模式需解密（见 _decrypt）
                echo = q.get("echostr", [""])[0]
                self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers(); self.wfile.write(echo.encode("utf-8"))
                return
            self.send_response(200); self.end_headers()

        def do_POST(self):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            # 解析 XML（明文或加密）
            try:
                root = ET.fromstring(raw)
                content = root.findtext("Content") or root.findtext("Encrypt")
                user = root.findtext("FromUserName")
                msg_type = root.findtext("MsgType")
            except Exception:
                content, user, msg_type = raw, None, None
            if content and user:
                rec = {"ts": time.time(), "from": user, "type": msg_type, "text": content}
                with open(INBOX, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"[wechat-bridge] 收到指令 from={user}: {content[:60]}")
            self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers(); self.wfile.write(b"success")

        def log_message(self, *a):
            pass

    print(f"[wechat-bridge] 接收端点已启动: http://0.0.0.0:{port}/wechat  (企业微信回调指向此地址的公网隧道)")
    http.server.HTTPServer(("0.0.0.0", port), H).serve_forever()


def test():
    cfg = load_cfg()
    ok = push("✅ wechat-bridge 自检通过 — 来自 WorkBuddy 的测试推送", cfg)
    print("config:", {k: ("***" if "secret" in k or "key" in k else v) for k, v in cfg.items()})


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "push":
        text = sys.argv[2] if len(sys.argv) > 2 else "（无内容）"
        push(text)
    elif cmd == "serve":
        p = int(sys.argv[2]) if len(sys.argv) > 2 else 8800
        serve(p)
    elif cmd == "test":
        test()
    else:
        print("用法: wechat_bridge.py [push <文本> | serve [port] | test]")


if __name__ == "__main__":
    main()

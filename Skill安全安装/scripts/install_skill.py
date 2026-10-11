#!/usr/bin/env python3
"""带 sha256 校验和 + P0/P1/P2 安全审查的 skill 安装/卸载/校验工具。

子命令:
  audit    <pkg.json>                       仅审查，输出风险分级报告(不安装)
  install  <pkg.json> [--target user|project] [--force]
  uninstall <skill名> [--target user|project]
  verify   <skill名> [--target user|project]

安全分级:
  P0 强烈拒绝(除非 --force 且用户明确授权): 递归删根/用户目录、git push --force、
      提权 sudo、磁盘破坏 mkfs/dd、读取 SSH/AWS 密钥、向外发送数据、eval/exec 动态执行。
  P1 需显式确认: 网络访问、git push、全局装依赖、读环境变量、调外部命令、chmod 777。
  P2 放行仅提示: 写文件、吞异常、print 可能打印敏感信息。

注册表(安装/卸载/校验的依据):
  用户级  ~/.workbuddy/skills/.skill-registry.json
  项目级  <cwd>/.workbuddy/skills/.skill-registry.json
"""
import sys, json, hashlib, base64, datetime, pathlib, re

P0 = [
    (r"\brm\s+-rf\s+(/|/c/|C:\\|~|\$HOME|\$USERPROFILE)", "递归删除根/用户目录"),
    (r"\bgit\s+push\s+--force", "强制推送(覆盖远端历史)"),
    (r"\bsudo\b", "提权执行"),
    (r"\bmkfs\b|\bdd\s+if=", "磁盘/分区破坏"),
    (r"(\.ssh|\.aws/credentials|id_rsa|private_key)", "读取 SSH/AWS 密钥"),
    (r"(curl|wget|requests\.post|httpx\.post|fetch)\b[^\n]*(POST|PUT|DELETE)", "向外部发送数据(潜在外泄)"),
    (r"\beval\s*\(|\bexec\s*\(", "动态执行代码"),
]
P1 = [
    (r"\bcurl\b|\bwget\b|\brequests\.(get|post)\b|\bhttpx\.\w+\b|\bfetch\b", "网络访问(可能外联)"),
    (r"\bgit\s+push\b", "推送到远端"),
    (r"pip\s+install|npm\s+install\s+-g|npm\s+i\s+-g|pnpm\s+add\s+-g", "全局安装依赖"),
    (r"os\.environ|getenv|os\.getenv", "读取环境变量(可能含密钥)"),
    (r"subprocess|os\.system|shell\s*=\s*True", "调用外部命令"),
    (r"chmod\s+777", "放宽权限"),
]
P2 = [
    (r"except:\s*pass|except\s+Exception:\s*pass|except\s+\w+:\s*pass", "吞掉异常"),
    (r"\bopen\s*\([^)]*['\"]w", "写文件"),
    (r"print\s*\(", "输出(可能打印敏感信息)"),
]


def scan(text: str):
    hits = []
    for pat, desc in P0:
        if re.search(pat, text, re.IGNORECASE):
            hits.append(("P0", desc))
    for pat, desc in P1:
        if re.search(pat, text, re.IGNORECASE):
            hits.append(("P1", desc))
    for pat, desc in P2:
        if re.search(pat, text, re.IGNORECASE):
            hits.append(("P2", desc))
    return hits


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reg_path(target: str) -> pathlib.Path:
    base = pathlib.Path.home() / ".workbuddy" / "skills" if target == "user" \
        else pathlib.Path.cwd() / ".workbuddy" / "skills"
    return base / ".skill-registry.json"


def load_reg(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_reg(p: pathlib.Path, reg):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_audit(pkg_path: str):
    pkg = json.loads(pathlib.Path(pkg_path).read_text(encoding="utf-8"))
    print(f"=== 安全审查: {pkg.get('name')} ===")
    all_hits = []
    for f in pkg.get("files", []):
        content = f.get("content") or ""
        for sev, desc in scan(content):
            print(f"  [{sev}] {f['path']:<26} {desc}")
            all_hits.append((f["path"], sev, desc))
    p0 = [h for h in all_hits if h[1] == "P0"]
    p1 = [h for h in all_hits if h[1] == "P1"]
    p2 = len(all_hits) - len(p0) - len(p1)
    print(f"\n总计: P0={len(p0)}  P1={len(p1)}  P2={p2}")
    if p0:
        print("⚠️ 发现 P0 高风险项：强烈建议不要安装，除非你明确知情并授权(加 --force)。")
    elif p1:
        print("⚠️ 发现 P1 项：安装前需你显式确认。")
    else:
        print("✅ 未发现 P0/P1 高风险项。")
    return all_hits


def cmd_install(pkg_path: str, target: str, force: bool):
    pkg = json.loads(pathlib.Path(pkg_path).read_text(encoding="utf-8"))
    hits = cmd_audit(pkg_path)
    if any(h[1] == "P0" for h in hits) and not force:
        sys.exit("\n❌ 存在 P0 高风险项且未加 --force，已中止安装。如需继续请显式确认。")

    base = pathlib.Path.home() / ".workbuddy" / "skills" if target == "user" \
        else pathlib.Path.cwd() / ".workbuddy" / "skills"
    dest = base / pkg["name"]
    if dest.exists():
        sys.exit(f"目标已存在: {dest}（先卸载再装，或用不同名）")

    dest.mkdir(parents=True)
    installed = []
    for f in pkg["files"]:
        fp = dest / f["path"]
        fp.parent.mkdir(parents=True, exist_ok=True)
        if f["encoding"] == "text":
            fp.write_bytes(f["content"].encode("utf-8"))
        else:
            fp.write_bytes(base64.b64decode(f["content_b64"]))
        installed.append({"path": f["path"], "sha256": f["sha256"]})

    reg = load_reg(reg_path(target))
    reg[pkg["name"]] = {
        "installed_at": datetime.datetime.now().astimezone().isoformat(),
        "target": target,
        "source": pkg.get("source_path"),
        "manifest_sha256": pkg.get("manifest_sha256"),
        "files": installed,
    }
    save_reg(reg_path(target), reg)
    print(f"\n✅ 已安装到 {dest}，登记 {len(installed)} 个文件。")


def cmd_uninstall(name: str, target: str):
    rp = reg_path(target)
    reg = load_reg(rp)
    if name not in reg:
        sys.exit(f"未在注册表找到: {name}")
    entry = reg[name]
    dest = (pathlib.Path.home() / ".workbuddy" / "skills" if target == "user"
            else pathlib.Path.cwd() / ".workbuddy" / "skills") / name
    removed = skipped = 0
    for f in entry["files"]:
        fp = dest / f["path"]
        if not fp.exists():
            print(f"  (已不存在): {f['path']}")
            continue
        if sha256_file(fp) == f["sha256"]:
            fp.unlink()
            removed += 1
        else:
            print(f"  ⚠️ 跳过(内容已变更,防误删): {f['path']}")
            skipped += 1
    # 自底向上清理已变空的子目录；遇到未登记文件会保留其所在目录
    for d in sorted(dest.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass
    try:
        dest.rmdir()
    except OSError:
        if dest.exists():
            print(f"  ⚠️ {dest} 仍非空，保留目录(有未登记文件)。")
    del reg[name]
    save_reg(rp, reg)
    print(f"\n✅ 已卸载 {name}：移除 {removed} 个文件，跳过 {skipped} 个(内容变更保护)。")


def cmd_verify(name: str, target: str):
    rp = reg_path(target)
    reg = load_reg(rp)
    if name not in reg:
        sys.exit(f"未在注册表找到: {name}")
    entry = reg[name]
    dest = (pathlib.Path.home() / ".workbuddy" / "skills" if target == "user"
            else pathlib.Path.cwd() / ".workbuddy" / "skills") / name
    ok = bad = 0
    for f in entry["files"]:
        fp = dest / f["path"]
        if not fp.exists():
            print(f"  ❌ 缺失: {f['path']}"); bad += 1; continue
        if sha256_file(fp) == f["sha256"]:
            ok += 1
        else:
            print(f"  ⚠️ 已篡改/变更: {f['path']}"); bad += 1
    print(f"校验 {name}: 一致 {ok}，异常 {bad}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd, rest = args[0], args[1:]
    target, force = "user", False
    if "--target" in rest:
        i = rest.index("--target"); target = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
    if "--force" in rest:
        force = True; rest = rest[:rest.index("--force")] + rest[rest.index("--force") + 1:]
    {
        "audit": lambda: cmd_audit(rest[0]),
        "install": lambda: cmd_install(rest[0], target, force),
        "uninstall": lambda: cmd_uninstall(rest[0], target),
        "verify": lambda: cmd_verify(rest[0], target),
    }.get(cmd, lambda: sys.exit(f"unknown cmd: {cmd}"))()

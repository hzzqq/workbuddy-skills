#!/usr/bin/env python3
"""将本地已安装的 skill 目录无损打包成单个 .skill.json 文件。

输出包含：frontmatter 解析、逐文件内容、每文件 sha256、整包 manifest 校验和、SKILL.md 原文 raw。
文本文件存 content，二进制文件(图片/模型等)自动 base64 存 content_b64。
"""
import sys, json, hashlib, base64, datetime, re, pathlib

TEXT_EXT = {
    ".md", ".py", ".sh", ".ps1", ".bat", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".env",
    ".gitignore", ".gitattributes", ".editorconfig", ".html", ".css",
    ".csv", ".sql", ".rst", ".lock", ".mod", ".sum",
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    data, key, buf = {}, None, []
    for line in fm_raw.splitlines():
        if line and not line[0].isspace():
            if buf and key is not None:
                data[key] = "\n".join(buf).strip()
            if ":" in line:
                k, _, v = line.partition(":")
                key, v = k.strip(), v.strip()
                buf = [] if v == "" else [v]
            else:
                key, buf = None, []
        elif key is not None:
            buf.append(line.strip())
    if buf and key is not None:
        data[key] = "\n".join(buf).strip()
    for k, v in list(data.items()):
        if isinstance(v, str) and v.lower() in ("true", "false"):
            data[k] = v.lower() == "true"
    return data, body


def pack(skill_dir: str, out_path: str):
    skill_dir = pathlib.Path(skill_dir).resolve()
    if not skill_dir.is_dir():
        sys.exit(f"skill 目录不存在: {skill_dir}")
    skill_md = skill_dir / "SKILL.md"

    files = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir).as_posix()
        b = p.read_bytes()
        is_textish = (p.suffix.lower() in TEXT_EXT) or (p.name == "SKILL.md")
        entry = {"path": rel, "size": len(b), "sha256": sha256(b)}
        if is_textish:
            try:
                entry["encoding"] = "text"
                entry["content"] = b.decode("utf-8")
            except UnicodeDecodeError:
                entry["encoding"] = "binary"
                entry["content_b64"] = base64.b64encode(b).decode("ascii")
        else:
            entry["encoding"] = "binary"
            entry["content_b64"] = base64.b64encode(b).decode("ascii")
        files.append(entry)

    fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8")) if skill_md.exists() else ({}, "")
    manifest = sha256("".join(f["sha256"] for f in files).encode())

    pkg = {
        "format": "workbuddy-skill-package/1.0",
        "name": skill_dir.name,
        "source_path": str(skill_dir),
        "packaged_at": datetime.datetime.now().astimezone().isoformat(),
        "file_count": len(files),
        "manifest_sha256": manifest,
        "frontmatter": fm,
        "files": files,
    }

    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pkg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"packed -> {out}")
    print(f"skill     : {pkg['name']}")
    print(f"files     : {len(files)}")
    print(f"manifest  : {manifest}")
    for f in files:
        print(f"  {f['path']:<28} {f['size']:>8}B  {f['sha256'][:12]}  [{f['encoding']}]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: pack_skill.py <skill_dir> [out.json]")
    sd = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else (pathlib.Path(sd).name + ".skill.json")
    pack(sd, out)

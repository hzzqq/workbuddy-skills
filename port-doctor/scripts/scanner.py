# -*- coding: utf-8 -*-
"""端口声明扫描器：从项目文件里提取"这个项目想用哪个端口"。

设计原则
--------
1. 只读、纯静态解析，绝不执行项目代码（项目可能是别人的/半成品/会崩）。
2. 证据可追溯：每条端口声明都带 来源文件 + 行号 + 命中片段，方便人工复核。
3. 不硬编码任何人的项目路径 —— 默认扫当前目录，跨机器通用。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# --------------------------------------------------------------------------
# 框架默认端口表：命中框架名但没写死端口时，用默认端口兜底
# --------------------------------------------------------------------------
FRAMEWORK_DEFAULTS = {
    "next": 3000,
    "nuxt": 3000,
    "vite": 5173,
    "react-scripts": 3000,
    "serve": 3000,
    "http-server": 8080,
    "webpack serve": 8080,
    "webpack-dev-server": 8080,
    "angular": 4200,
    "vue-cli-service": 8080,
    "flask": 5000,
    "django": 8000,
    "fastapi": 8000,
    "uvicorn": 8000,
    "gunicorn": 8000,
    "streamlit": 8501,
    "gradio": 7860,
    "jupyter": 8888,
    "jupyter-notebook": 8888,
    "http.server": 8000,
    "live-server": 35729,
    "remix": 3000,
    "astro": 4321,
    "docusaurus": 3000,
}

# 扫描时跳过的目录（体积大 / 与端口无关 / 生成物）
SKIP_DIRS = {
    "node_modules", ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "venv", ".venv", "env", ".env.d",
    "dist", "build", ".next", ".nuxt", ".output", "out", "coverage",
    "site-packages", ".tox", ".idea", ".vscode", ".gradle", "target",
    ".workbuddy", ".cache", "vendor", "bower_components", ".terraform",
    "AppData", "$Recycle.Bin", "System Volume Information",
}

# 这些扩展名的文件才值得扫
SCAN_EXT = {
    ".json", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".py", ".toml", ".cfg", ".ini", ".env", ".yml", ".yaml", ".sh", ".bash",
    ".bat", ".cmd", ".ps1", ".properties", ".txt", ".md", ".conf",
}
SKIP_EXT = {".min.js", ".map", ".lock", ".log", ".pyc"}

# 单文件最大扫描体积（防止误扫巨型二进制）
MAX_FILE_BYTES = 2 * 1024 * 1024

# port-doctor 生成的机器本地端口文件（运行时真正生效的端口来源）
ENV_FILE_NAME = ".port.env"

# port-doctor 生成的机器本地端口文件（运行时真正生效的端口来源）
ENV_FILE_NAME = ".port.env"


@dataclass
class PortDecl:
    """一条端口声明（谁、哪个端口、凭什么这么说）"""
    port: int
    kind: str                 # framework | explicit | env | compose | script | config
    source: str               # 相对项目根的文件路径
    line: int = 0
    evidence: str = ""        # 命中的原始片段（截断）
    confidence: str = "high"  # high=显式写了端口, medium=框架默认端口推断
    scope: str = "host"       # host=占宿主机端口；container=仅容器内映射，不占宿主机

    def key(self) -> tuple:
        return (self.port, self.source, self.line, self.kind, self.scope)


@dataclass
class ProjectPorts:
    """一个项目的端口画像"""
    name: str
    path: str
    decls: list = field(default_factory=list)
    env_ports: dict = field(default_factory=dict)   # .port.env 里的 键->端口

    @property
    def ports(self) -> list:
        """全部声明端口（含容器侧）"""
        return sorted({d.port for d in self.decls})

    @property
    def host_ports(self) -> list:
        """代码里声明的、真正会占宿主机端口的（容器内映射与 .port.env 排除，避免误报）"""
        return sorted({d.port for d in self.decls
                       if d.scope != "container" and d.kind != "port_env"})

    @property
    def container_ports(self) -> list:
        return sorted({d.port for d in self.decls if d.scope == "container"})

    @property
    def effective_ports(self) -> list:
        """**运行时真正会用的端口**：有 .port.env 就以它为准，否则退回声明端口。

        这是 v1.0.1 的关键改进：项目把端口改成由 .port.env 注入后，
        冲突判定必须看"生效端口"，否则会一直报老端口撞车（不诚实）。
        """
        if self.env_ports:
            return sorted(set(self.env_ports.values()))
        return self.host_ports

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "ports": self.ports,
            "host_ports": self.host_ports,
            "container_ports": self.container_ports,
            "decls": [asdict(d) for d in self.decls],
        }


# --------------------------------------------------------------------------
# 单文件解析
# --------------------------------------------------------------------------
_RE_EXPLICIT = [
    # --port 8080 / --port=8080 / -p 8080
    (re.compile(r"--port[=\s]+(\d{2,5})"), "explicit"),
    (re.compile(r"(?<!\w)-p[=\s]+(\d{2,5})(?!\w)"), "explicit"),
    # PORT=8080 / PORT = 8080 / export PORT=8080
    (re.compile(r"\bPORT\s*[=:]\s*(\d{2,5})\b", re.I), "explicit"),
    # app.run(port=5000)
    (re.compile(r"\bport\s*=\s*(\d{2,5})\b"), "explicit"),
    # http.server 8000 / gunicorn -b 0.0.0.0:8000
    (re.compile(r"\b(?:http\.server|gunicorn|uvicorn)\b[^\n]{0,40}?\b(\d{2,5})\b"), "explicit"),
    # vite.config: server: { port: 5173 }
    (re.compile(r"\bport\s*:\s*(\d{2,5})\b"), "config"),
]
_RE_COMPOSE = re.compile(r"^\s*-\s*[\"']?(\d{2,5}):(\d{2,5})[\"']?\s*$")
_RE_FRAMEWORK_HINT = re.compile(
    r"\b(" + "|".join(sorted((re.escape(k) for k in FRAMEWORK_DEFAULTS), key=len, reverse=True)) + r")\b",
    re.I,
)


def _norm(text: str) -> str:
    return text.replace("\u3000", " ").replace("\t", " ")


def parse_text(text: str, rel_path: str, source_name: str) -> list:
    """从一个文件内容里抽取端口声明"""
    out = []
    lines = text.splitlines()
    fname = os.path.basename(rel_path).lower()

    is_json = fname.endswith(".json")
    is_compose = "compose" in fname and fname.endswith((".yml", ".yaml"))
    is_env = fname.startswith(".env") or fname.endswith((".env", ".env.local"))
    is_vite = "vite.config" in fname
    is_py = fname.endswith(".py")

    for idx, raw in enumerate(lines, 1):
        line = _norm(raw).strip()
        if not line or line.startswith("#") and not is_json:
            continue
        # 二进制/压缩行跳过
        if len(line) > 2000:
            continue

        if is_compose:
            m = _RE_COMPOSE.match(line)
            if m:
                host, cont = int(m.group(1)), int(m.group(2))
                # "8081:80" → 宿主绑 8081，容器内是 80（容器侧不占宿主机）
                out.append(PortDecl(port=host, kind="compose", source=rel_path,
                                    line=idx, evidence=line[:120], scope="host"))
                if cont != host:
                    out.append(PortDecl(port=cont, kind="compose", source=rel_path,
                                        line=idx, evidence=line[:120], scope="container"))
                continue

        if is_env:
            m = re.match(r"^\s*(?:export\s+)?PORT\s*=\s*(\d{2,5})\s*$", line, re.I)
            if m:
                out.append(PortDecl(port=int(m.group(1)), kind="env", source=rel_path,
                                    line=idx, evidence=line[:120]))
                continue

        # 显式端口
        for rx, kind in _RE_EXPLICIT:
            for m in rx.finditer(line):
                port = int(m.group(1))
                if not (1024 <= port <= 65535):
                    continue
                if kind == "explicit" and is_py and "port" not in line.lower():
                    continue
                out.append(PortDecl(port=port, kind=kind, source=rel_path,
                                    line=idx, evidence=line[:120]))
                break

        # 框架默认端口（仅在没有显式端口命中时补）
        if is_json and "package.json" in fname:
            hint = _RE_FRAMEWORK_HINT.search(line)
            if hint:
                fw = hint.group(1).lower()
                default = FRAMEWORK_DEFAULTS.get(fw)
                if default and not any(d.kind in ("explicit", "env") for d in out):
                    out.append(PortDecl(port=default, kind="framework", source=rel_path,
                                        line=idx, evidence=line[:120],
                                        confidence="medium"))
        elif is_vite:
            m = re.search(r"\bport\s*:\s*(\d{2,5})\b", line)
            if m:
                out.append(PortDecl(port=int(m.group(1)), kind="config", source=rel_path,
                                    line=idx, evidence=line[:120]))
    return out


def _read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        raw = path.read_bytes()
    except OSError:
        return ""
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


# --------------------------------------------------------------------------
# 目录遍历
# --------------------------------------------------------------------------
def find_project_roots(root: Path, max_depth: int = 2) -> list:
    """找出 root 下像"项目"的目录（含依赖清单或服务端入口的）。"""
    markers = ("package.json", "requirements.txt", "pyproject.toml", "setup.py",
               "docker-compose.yml", "docker-compose.yaml", "compose.yml",
               "manage.py", "Procfile", "Cargo.toml", "go.mod", "app.py", "main.py")
    roots = []
    root = Path(root)
    if not root.exists():
        return roots
    for cur, dirs, files in _walk_dirs(root, max_depth):
        if cur == root:
            continue
        if any(m in files for m in markers):
            roots.append(Path(cur))
            dirs[:] = []  # 命中后不再深入（子目录通常是被它覆盖的子项目）
    return roots


def _walk_dirs(root: Path, max_depth: int):
    base_depth = len(root.parts)
    stack = [(root, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            entries = list(os.scandir(cur))
        except OSError:
            continue
        dirs = []
        files = set()
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    if e.name in SKIP_DIRS or e.name.startswith("."):
                        if e.name not in (".github",):
                            continue
                    dirs.append(Path(e.path))
                else:
                    files.add(e.name)
            except OSError:
                continue
        yield cur, dirs, files
        if depth < max_depth:
            for d in dirs:
                stack.append((d, depth + 1))


def read_port_env(project_path) -> dict:
    """读取项目根的 .port.env（port-doctor 生成的机器本地端口文件）。

    解析规则与项目内 port_env.py 一致：跳过空行与 # 注释，取 KEY=VALUE，值必须是纯数字。
    """
    path = Path(project_path) / ".port.env"
    out = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if k and v.isdigit():
            out[k] = int(v)
    return out


def scan_project(project_path) -> ProjectPorts:
    """扫描单个项目里所有文件的端口声明"""
    project_path = Path(project_path)
    proj = ProjectPorts(name=project_path.name, path=str(project_path))
    seen = set()
    # .port.env 优先：它代表运行时真正生效的端口
    env_ports = read_port_env(project_path)
    proj.env_ports = env_ports
    for key, port in sorted(env_ports.items()):
        proj.decls.append(PortDecl(port=port, kind="port_env", source=".port.env",
                                   line=0, evidence="%s=%d" % (key, port),
                                   confidence="high"))
    for cur, dirs, files in _walk_dirs(project_path, 2):
        for fname in sorted(files):
            # .port.env 由 read_port_env() 专门处理，不走通用规则（避免双计数）
            if fname == ENV_FILE_NAME:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SCAN_EXT and fname not in (".env", "Procfile", "Dockerfile"):
                continue
            if fname in SKIP_EXT:
                continue
            fpath = Path(cur) / fname
            rel = os.path.relpath(str(fpath), str(project_path)).replace("\\", "/")
            text = _read_text(fpath)
            if not text:
                continue
            for d in parse_text(text, rel, fname):
                if d.key() in seen:
                    continue
                seen.add(d.key())
                proj.decls.append(d)
    proj.decls.sort(key=lambda d: (d.port, d.source, d.line))
    return proj


def scan_root(root, max_depth: int = 2) -> list:
    """扫描一个根目录下所有项目的端口声明"""
    return [scan_project(p) for p in find_project_roots(Path(root), max_depth=max_depth)]


def to_json(projects) -> str:
    return json.dumps([p.to_dict() for p in projects], ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    print(to_json(scan_root(target, depth)))

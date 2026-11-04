#!/usr/bin/env python3
"""
Skill Dependency Auditor v1.0
Supply-chain auditor for Clawdbot / WorkBuddy / MCP skills.

Scans a skill for dependency risks:
  - Unpinned dependencies (version drift / confusion risk)
  - Dependencies installed from arbitrary remote URLs or git repos (RCE-at-install)
  - Local path dependencies
  - Typosquatting candidates (package names close to popular packages)
  - Unverified packages not present in a curated allowlist (review manually)

Pure standard library. Read-only, no network, no installs.

Usage:
    python dependency_auditor.py <path-to-skill-folder>
    python dependency_auditor.py <path-to-skill-folder> --json
    python dependency_auditor.py <path-to-skill-folder> --output report.md

License: MIT
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


class Severity:
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict:
    APPROVED = "approved"
    CAUTION = "caution"
    REJECT = "reject"


@dataclass
class Finding:
    pattern_name: str
    severity: str
    file_path: str
    line_number: int
    line_content: str
    description: str
    recommendation: str


@dataclass
class ScanReport:
    skill_path: str
    scan_timestamp: str
    findings: List[Finding] = field(default_factory=list)
    verdict: str = "approved"
    verdict_reason: str = ""
    deps_found: List[str] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)


# Curated allowlist of widely-used, well-known packages (PyPI + npm).
# Offline heuristic: anything NOT in this list is flagged "unverified" for manual review.
KNOWN_PACKAGES = set("""
numpy pandas scipy scikit-learn matplotlib seaborn requests httpx akshare tushare yfinance
streamlit flask fastapi uvicorn gunicorn django tornado sanic
openai langchain langchain-openai langgraph chromadb faiss-cpu
jieba snownlp transformers torch tensorflow keras
pydantic pydantic-settings typer click argparse yaml toml tomli python-dotenv dotenv
tqdm rich loguru structlog pytest playwright browser-use selenium beautifulsoup4 lxml html5lib
bs4 soupsieve redis celery sqlalchemy pymysql psycopg2-binary pillow pillow
boto3 botocore azure-storage-blob azure-identity google-cloud-storage google-cloud firebase-admin
tencentcloud-sdk-python alibabacloud-sdk oss2 cos-python-sdk-v5
kubernetes docker paramiko pysftp cryptography hashids
pandas-ta ta-lib backtrader vectorbt matplotlib
node-fetch axios request got node-cron
react react-dom vue next nuxt angular express koa fastify
lodash moment dayjs d3 three chart.js tailwindcss webpack vite esbuild
typescript eslint prettier rollup babel
""".split())


def _levenshtein(a: str, b: str, cap: int = 3) -> int:
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
        if min(prev) > cap:
            return cap + 1
    return prev[-1]


def _typosquat_candidate(name: str) -> Optional[str]:
    """Return the closest known package if the name looks like a typo of it."""
    best = None
    best_d = 99
    for known in KNOWN_PACKAGES:
        if abs(len(known) - len(name)) > 2:
            continue
        d = _levenshtein(name.lower(), known)
        if d <= 2 and d < best_d:
            best, best_d = known, d
    return best


# Dependency declaration / install-command scanning rules.
DEP_SPEC_RE = re.compile(r"([A-Za-z0-9_.\-]+)\s*(?:==|>=|<=|~=|!=|@|>|<)")
REMOTE_INSTALL_RE = re.compile(
    r"(?:pip3?|python\s+-m\s+pip|npm\s+i(?:nstall)?|yarn\s+add|pnpm\s+add)\s+[^\n]*?"
    r"(git\+https?://|https?://[^ \n]+\.(?:whl|tar\.gz|zip)|--index-url|--extra-index-url)",
    re.IGNORECASE,
)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_]+)", re.MULTILINE)

DEP_FILES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock", "package.json",
    "package-lock.json", "yarn.lock", "environment.yml", "poetry.lock",
}
INSTALL_SCAN_EXT = {".sh", ".bash", ".md", ".txt", ".yml", ".yaml", ".toml", ".bat"}


class DependencyAuditor:
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path).resolve()
        self.report = ScanReport(
            skill_path=str(self.skill_path),
            scan_timestamp=datetime.now().isoformat(),
        )

    def scan(self) -> ScanReport:
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {self.skill_path}")
        self._scan_files()
        self._determine_verdict()
        return self.report

    def _scan_files(self):
        for root, _dirs, files in os.walk(self.skill_path):
            for fname in files:
                file_path = Path(root) / fname
                rel_path = str(file_path.relative_to(self.skill_path))
                self.report.files_scanned.append(rel_path)
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                # 1) Dependency declarations in manifest files
                if fname in DEP_FILES:
                    self._scan_declarations(file_path, rel_path, content)

                # 2) Imports in python files (typosquat + unverified)
                if file_path.suffix == ".py":
                    self._scan_imports(file_path, rel_path, content)

                # 3) Remote install commands in scripts / docs
                if file_path.suffix in INSTALL_SCAN_EXT:
                    self._scan_install_commands(file_path, rel_path, content)

    def _add(self, name, severity, fpath, line_no, line, desc, rec):
        self.report.findings.append(Finding(name, severity, fpath, line_no, line.strip()[:200], desc, rec))

    def _scan_declarations(self, file_path, rel_path, content):
        for i, line in enumerate(content.split("\n"), 1):
            raw = line.strip()
            if not raw or raw.startswith("#") or raw.startswith(";"):
                continue
            m = DEP_SPEC_RE.search(line)
            if not m:
                continue
            pkg = m.group(1).lower()
            if pkg in ("python", "python-version"):
                continue
            self.report.deps_found.append(pkg)

            # Remote / git source dependency -> RCE at install
            if "@" in line and ("git+http" in line or "https://" in line or "http://" in line or "file://" in line or "git+" in line):
                self._add(
                    "remote_source_dependency", Severity.HIGH, rel_path, i, line,
                    f"依赖 {pkg} 来自远程 URL / git / 本地路径，安装时可能执行任意远程代码",
                    "CAUTION - 仅从可信索引安装；远程源依赖应替换为锁定版本",
                )
                continue
            # Unpinned dependency
            if not re.search(r"(==|>=|<=|~=|!=|>|<)", line):
                self._add(
                    "unpinned_dependency", Severity.MEDIUM, rel_path, i, line,
                    f"依赖 {pkg} 未固定版本，存在版本漂移 / 依赖混淆风险",
                    "固定到精确版本（==x.y.z）或至少下限版本",
                )
            # Typosquat of a known package
            cand = _typosquat_candidate(pkg)
            if cand and cand != pkg:
                self._add(
                    "typosquat_candidate", Severity.HIGH, rel_path, i, line,
                    f"包名 {pkg} 与已知包 {cand} 极相似，疑似 typosquatting（错拼抢注）",
                    f"确认是否应为 {cand}；错拼包常被植入恶意代码",
                )
            elif pkg not in KNOWN_PACKAGES:
                self._add(
                    "unverified_dependency", Severity.LOW, rel_path, i, line,
                    f"依赖 {pkg} 不在策展白名单，无法离线核验来源",
                    "请人工确认其来自官方索引且为预期依赖",
                )

    def _scan_imports(self, file_path, rel_path, content):
        seen = set()
        for m in IMPORT_RE.finditer(content):
            pkg = m.group(1).lower()
            if pkg in seen:
                continue
            seen.add(pkg)
            cand = _typosquat_candidate(pkg)
            if cand and cand != pkg:
                self._add(
                    "typosquat_candidate", Severity.HIGH, rel_path, 0, f"import {pkg}",
                    f"import 的包 {pkg} 与已知包 {cand} 极相似，疑似 typosquatting",
                    f"确认是否应为 {cand}",
                )
            elif pkg not in KNOWN_PACKAGES:
                self._add(
                    "unverified_import", Severity.LOW, rel_path, 0, f"import {pkg}",
                    f"import 的包 {pkg} 不在策展白名单，无法离线核验",
                    "确认来源可信且为预期依赖",
                )

    def _scan_install_commands(self, file_path, rel_path, content):
        for i, line in enumerate(content.split("\n"), 1):
            if REMOTE_INSTALL_RE.search(line):
                self._add(
                    "remote_install_command", Severity.HIGH, rel_path, i, line,
                    "检测到从远程 URL / 非官方索引安装依赖的命令",
                    "CAUTION - 改为从可信索引固定版本安装；禁止在 skill 里执行远程安装",
                )

    def _determine_verdict(self):
        high = [f for f in self.report.findings if f.severity == Severity.HIGH]
        if high:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(high)} high-severity supply-chain issue(s): "
                + ", ".join(sorted(set(f.pattern_name for f in high)))
            )
        elif self.report.findings:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(self.report.findings)} lower-severity dependency issue(s) "
                "(unpinned / unverified) - review recommended"
            )
        else:
            self.report.verdict = Verdict.APPROVED
            self.report.verdict_reason = "No dependency supply-chain issues detected"


def format_markdown(report: ScanReport) -> str:
    lines = [
        f"# Skill Dependency Audit - {report.skill_path}",
        "",
        f"**Scan Date:** {report.scan_timestamp}",
        f"**Skill Path:** `{report.skill_path}`",
        "",
        "## Verdict",
        "",
        f"**{report.verdict.upper()}** - {report.verdict_reason}",
        "",
        f"## Dependencies Found ({len(report.deps_found)})",
        ", ".join(sorted(set(report.deps_found))) or "(none detected)",
        "",
    ]
    if report.findings:
        lines.extend(["## Findings", "", f"Found **{len(report.findings)}** issue(s):", ""])
        for f in report.findings:
            lines.extend([
                f"### {f.pattern_name} ({f.severity})",
                f"- **File:** `{f.file_path}`"
                + (f" line {f.line_number}" if f.line_number else ""),
                f"- **Description:** {f.description}",
                f"- **Recommendation:** {f.recommendation}",
                f"- **Code:** `{f.line_content}`",
                "",
            ])
    else:
        lines.extend(["## Findings", "", "No dependency issues detected.", ""])
    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    data = {
        "skill_path": report.skill_path,
        "scan_timestamp": report.scan_timestamp,
        "verdict": report.verdict,
        "verdict_reason": report.verdict_reason,
        "deps_found": sorted(set(report.deps_found)),
        "findings": [asdict(f) for f in report.findings],
        "files_scanned": report.files_scanned,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Skill Dependency Auditor - supply-chain risk scan"
    )
    parser.add_argument("skill_path", help="Path to skill folder to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Write report to file")
    args = parser.parse_args()

    try:
        auditor = DependencyAuditor(args.skill_path)
        report = auditor.scan()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = format_json(report) if args.json else format_markdown(report)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)

    sys.exit(1 if report.verdict != Verdict.APPROVED else 0)


if __name__ == "__main__":
    main()

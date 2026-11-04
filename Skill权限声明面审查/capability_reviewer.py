#!/usr/bin/env python3
"""
Skill Capability Reviewer v1.0
Declared-vs-actual capability reviewer for Clawdbot / WorkBuddy / MCP skills.

Cross-checks what a skill CLAIMS in its SKILL.md (read-only / no-network /
no-secret) against what its code ACTUALLY does (file writes, network calls,
command execution, env/secret access, destructive FS ops). Surfaces:
  - **mismatch**: claim says safe, but code does the risky thing (trust risk)
  - **undisclosed**: code does the risky thing, but SKILL.md never mentions it
  - **verified**: claim made and code is consistent

Pure standard library. Read-only, no network, no env access.

Usage:
    python capability_reviewer.py <path-to-skill-folder>
    python capability_reviewer.py <path-to-skill-folder> --json
    python capability_reviewer.py <path-to-skill-folder> --output report.md

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
    claims: List[str] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)


# Behavior patterns (regex) -> the capability category they imply.
BEHAVIOR_PATTERNS: Dict[str, str] = {
    "network": r"requests\.(get|post|put|delete|head|patch)|httpx\.|urllib|urlopen|fetch\s*\(|axios|curl\s+|wget\s+|aiohttp",
    "file_write": r"open\s*\([^)]*['\"](?:w|a|x|w\+|a\+|x\+)['\"]|write_text\s*\(|to_csv\s*\(|shutil\.copy|os\.rename|Path\([^)]*\)\.write",
    "command_exec": r"\bsubprocess\b|os\.system|os\.popen|shell=True|popen\s*\(",
    "env_secret": r"environ\s*\[|getenv\s*\(|load_dotenv",
    "fs_destructive": r"shutil\.rmtree|os\.remove|os\.unlink",
}

# Claim keywords in SKILL.md -> capability category the skill says it DOES NOT do.
CLAIM_PATTERNS: Dict[str, Dict[str, str]] = {
    "no_network": {
        "regex": r"零网络|无网络|不联网|离线|纯本地|local[- ]?only|本地运行|不发起网络|不访问网络",
        "contradicts": "network",
        "label": "声明零网络/本地运行",
    },
    "read_only": {
        "regex": r"只读|read[- ]?only|read only|不写文件|不修改文件",
        "contradicts": "file_write",
        "label": "声明只读/不写文件",
    },
    "no_secret": {
        "regex": r"不访问密钥|不读取|无密钥|不读取环境变量|零密钥|不触碰密钥|不访问环境变量",
        "contradicts": "env_secret",
        "label": "声明不访问密钥/环境变量",
    },
}


def _is_definition_line(line: str) -> bool:
    """Skip lines that merely DEFINE our detection regexes (avoid self-matching)."""
    if "re.compile" in line:
        return True
    if "r'" in line or 'r"' in line:
        return True
    if "BEHAVIOR_PATTERNS" in line or "CLAIM_PATTERNS" in line:
        return True
    return False


def _capability_label(cat: str) -> str:
    return {
        "network": "网络访问",
        "file_write": "写文件",
        "command_exec": "执行命令",
        "env_secret": "读取环境变量/密钥",
        "fs_destructive": "删除文件/目录",
    }.get(cat, cat)


class CapabilityReviewer:
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path).resolve()
        self.report = ScanReport(
            skill_path=str(self.skill_path),
            scan_timestamp=datetime.now().isoformat(),
        )
        self._compiled_behavior = {k: re.compile(v, re.IGNORECASE) for k, v in BEHAVIOR_PATTERNS.items()}
        self._compiled_claim = {k: re.compile(v["regex"]) for k, v in CLAIM_PATTERNS.items()}

    def scan(self) -> ScanReport:
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {self.skill_path}")
        skill_md = self.skill_path / "SKILL.md"
        claims = {}
        if skill_md.exists():
            md_text = skill_md.read_text(encoding="utf-8", errors="ignore")
            for ckey, cdef in CLAIM_PATTERNS.items():
                if cdef["regex"] and self._compiled_claim[ckey].search(md_text):
                    claims[ckey] = cdef
                    self.report.claims.append(cdef["label"])
        self._scan_files(claims)
        self._determine_verdict()
        return self.report

    def _scan_files(self, claims: Dict[str, Dict[str, str]]):
        behavior_hits: Dict[str, List[Finding]] = {k: [] for k in BEHAVIOR_PATTERNS}
        for root, _dirs, files in os.walk(self.skill_path):
            for fname in files:
                file_path = Path(root) / fname
                rel_path = str(file_path.relative_to(self.skill_path))
                self.report.files_scanned.append(rel_path)
                suffix = file_path.suffix.lower()
                if suffix not in (".py", ".js", ".ts", ".sh", ".bash", ".md", ".json"):
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for bcat, regex in self._compiled_behavior.items():
                    for i, line in enumerate(content.split("\n"), 1):
                        if _is_definition_line(line):
                            continue
                        if regex.search(line):
                            behavior_hits[bcat].append(
                                Finding(
                                    pattern_name=f"behavior_{bcat}",
                                    severity=Severity.INFO,
                                    file_path=rel_path,
                                    line_number=i,
                                    line_content=line.strip()[:200],
                                    description=f"代码存在{_capability_label(bcat)}行为",
                                    recommendation="",
                                )
                            )
        # Resolve findings against claims.
        self._resolve(claims, behavior_hits)

    def _resolve(self, claims, behavior_hits):
        for ckey, cdef in claims.items():
            contradicts = cdef["contradicts"]
            if behavior_hits.get(contradicts):
                for fh in behavior_hits[contradicts]:
                    self.report.findings.append(
                        Finding(
                            pattern_name=f"claim_mismatch_{ckey}",
                            severity=Severity.HIGH,
                            file_path=fh.file_path,
                            line_number=fh.line_number,
                            line_content=fh.line_content,
                            description=(
                                f"{cdef['label']}，但代码存在{_capability_label(contradicts)}行为"
                                "——声明与实现不一致，存在误导/越权风险"
                            ),
                            recommendation=(
                                "如实更新 SKILL.md 声明，或将代码改为符合声明的实现；"
                                "隐瞒能力会破坏用户信任"
                            ),
                        )
                    )
            else:
                self.report.findings.append(
                    Finding(
                        pattern_name=f"claim_verified_{ckey}",
                        severity=Severity.INFO,
                        file_path="SKILL.md",
                        line_number=0,
                        line_content=cdef["label"],
                        description=f"{cdef['label']}，代码未发现相反行为（声明一致）",
                        recommendation="保持即可",
                    )
                )
        # Undisclosed behaviors: code does risky thing but no claim + SKILL.md silent.
        for bcat, hits in behavior_hits.items():
            if not hits:
                continue
            # If a claim explicitly covers this category, mismatch already handled.
            covered = any(cdef["contradicts"] == bcat for cdef in claims.values())
            if covered:
                continue
            for fh in hits[:5]:  # cap to avoid noise
                self.report.findings.append(
                    Finding(
                        pattern_name=f"undisclosed_{bcat}",
                        severity=Severity.MEDIUM,
                        file_path=fh.file_path,
                        line_number=fh.line_number,
                        line_content=fh.line_content,
                        description=(
                            f"代码存在{_capability_label(bcat)}行为，但 SKILL.md 未声明该能力"
                        ),
                        recommendation="在 SKILL.md 中显式披露此能力，便于用户评估风险",
                    )
                )

    def _determine_verdict(self):
        high = [f for f in self.report.findings if f.severity == Severity.HIGH]
        mismatch = [f for f in self.report.findings if f.pattern_name.startswith("claim_mismatch")]
        if mismatch:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(mismatch)} claim/behavior mismatch(es) (声明与代码不一致)"
            )
        elif self.report.findings:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(self.report.findings)} undisclosed-capability issue(s) - disclose in SKILL.md"
            )
        else:
            self.report.verdict = Verdict.APPROVED
            self.report.verdict_reason = "Claims consistent with code; no undisclosed capabilities"


def format_markdown(report: ScanReport) -> str:
    lines = [
        f"# Skill Capability Review - {report.skill_path}",
        "",
        f"**Scan Date:** {report.scan_timestamp}",
        f"**Skill Path:** `{report.skill_path}`",
        "",
        "## Verdict",
        "",
        f"**{report.verdict.upper()}** - {report.verdict_reason}",
        "",
        "## Declared Claims",
        ", ".join(report.claims) if report.claims else "(none detected in SKILL.md)",
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
        lines.extend(["## Findings", "", "No capability mismatches detected.", ""])
    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    data = {
        "skill_path": report.skill_path,
        "scan_timestamp": report.scan_timestamp,
        "verdict": report.verdict,
        "verdict_reason": report.verdict_reason,
        "claims": report.claims,
        "findings": [asdict(f) for f in report.findings],
        "files_scanned": report.files_scanned,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Skill Capability Reviewer - declared vs actual capability check"
    )
    parser.add_argument("skill_path", help="Path to skill folder to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Write report to file")
    args = parser.parse_args()

    try:
        reviewer = CapabilityReviewer(args.skill_path)
        report = reviewer.scan()
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

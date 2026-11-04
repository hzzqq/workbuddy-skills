#!/usr/bin/env python3
"""
Skill Secret Scanner v1.0
Static secret / credential leak scanner for Clawdbot / WorkBuddy / MCP skills.

Scans a skill folder for hardcoded secrets before you publish or install it:
  - AWS / Azure / GCP access keys & connection strings
  - Private key blocks (RSA / EC / OPENSSH / PGP)
  - GitHub / Slack / Stripe / Google API tokens
  - JWTs and generic api_key / secret / token / password assignments
  - dotenv references and external webhook / callback endpoints

Pure standard library. Read-only, no network, no env access.

Usage:
    python secret_scanner.py <path-to-skill-folder>
    python secret_scanner.py <path-to-skill-folder> --json
    python secret_scanner.py <path-to-skill-folder> --output report.md

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
class SkillMetadata:
    name: str = "unknown"
    version: str = "unknown"
    has_skill_md: bool = False
    file_count: int = 0
    script_count: int = 0
    total_lines: int = 0


@dataclass
class ScanReport:
    skill_path: str
    scan_timestamp: str
    metadata: SkillMetadata
    findings: List[Finding] = field(default_factory=list)
    verdict: str = "approved"
    verdict_reason: str = ""
    files_scanned: List[str] = field(default_factory=list)


# =============================================================================
# SECRET PATTERNS
# =============================================================================

SECRET_PATTERNS: List[Dict] = [
    # --- CLOUD KEYS ---
    {
        "name": "aws_access_key_id",
        "pattern": r"AKIA[0-9A-Z]{16}",
        "severity": Severity.CRITICAL,
        "description": "AWS Access Key ID (hardcoded)",
        "recommendation": "REJECT - move to env var / secret manager; rotate immediately",
        "file_types": [".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml", ".md", ".txt"],
    },
    {
        "name": "aws_secret_assignment",
        "pattern": r"(aws_secret_access_key|aws_secret_key|aws_session_token)\s*[:=]\s*[\"'][A-Za-z0-9/+]{16,}[\"']",
        "severity": Severity.CRITICAL,
        "description": "AWS secret / session token assigned as a literal",
        "recommendation": "REJECT - move to env var / secret manager; rotate immediately",
        "file_types": [".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml"],
    },
    {
        "name": "azure_connection_string",
        "pattern": r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=",
        "severity": Severity.HIGH,
        "description": "Azure Storage connection string with embedded account key",
        "recommendation": "REJECT - use SAS tokens or managed identity; rotate key",
        "file_types": [".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml"],
    },
    {
        "name": "gcp_api_key",
        "pattern": r"AIza[0-9A-Za-z_\-]{35}",
        "severity": Severity.HIGH,
        "description": "Google API key (hardcoded)",
        "recommendation": "REJECT - restrict via API key API and move to secret store",
        "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md"],
    },
    # --- PRIVATE KEYS ---
    {
        "name": "private_key_block",
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
        "severity": Severity.CRITICAL,
        "description": "Private key block embedded in source",
        "recommendation": "REJECT - never ship private keys; use volumes / secret mounts",
        "file_types": [".py", ".js", ".ts", ".sh", ".pem", ".key", ".json", ".yaml", ".yml"],
    },
    # --- SERVICE TOKENS ---
    {
        "name": "github_token",
        "pattern": r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|gho_[A-Za-z0-9]{36}|ghu_[A-Za-z0-9]{36})",
        "severity": Severity.CRITICAL,
        "description": "GitHub personal access / OAuth token",
        "recommendation": "REJECT - revoke and move to env var",
        "file_types": [".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml", ".md"],
    },
    {
        "name": "slack_token",
        "pattern": r"xox[baprs]-[A-Za-z0-9\-]{10,}",
        "severity": Severity.HIGH,
        "description": "Slack token (bot / app / user)",
        "recommendation": "REJECT - revoke and move to env var",
        "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".yml"],
    },
    {
        "name": "stripe_live_key",
        "pattern": r"sk_live_[A-Za-z0-9]{24,}|pk_live_[A-Za-z0-9]{24,}",
        "severity": Severity.CRITICAL,
        "description": "Stripe live secret / publishable key",
        "recommendation": "REJECT - use test keys in skills and move live keys to secret store",
        "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".yml"],
    },
    # --- GENERIC ASSIGNMENTS ---
    {
        "name": "generic_secret_assignment",
        "pattern": r"(api[_-]?key|apikey|secret|token|password|passwd|client_secret|access_token)\s*[:=]\s*[\"'][A-Za-z0-9_\-./+]{16,}[\"']",
        "severity": Severity.HIGH,
        "description": "Generic secret / token assigned as a string literal",
        "recommendation": "REJECT unless clearly a placeholder - move to env var",
        "file_types": [".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml"],
    },
    {
        "name": "jwt_token",
        "pattern": r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
        "severity": Severity.MEDIUM,
        "description": "JSON Web Token (JWT) embedded in source",
        "recommendation": "CAUTION - tokens should be issued at runtime, not hardcoded",
        "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".yml"],
    },
    # --- EXFIL / CALLBACK ENDPOINTS ---
    {
        "name": "external_webhook",
        "pattern": r"https?://(?:hooks\.slack\.com|discord\.com/api/webhooks|api\.telegram\.org|tencentscf\.com)[^\s\"']*",
        "severity": Severity.MEDIUM,
        "description": "External webhook / callback endpoint (data egress risk)",
        "recommendation": "CAUTION - verify the destination is expected and consented",
        "file_types": [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md"],
    },
    # --- ENV FILE LEAK (low severity, common) ---
    {
        "name": "dotenv_reference",
        "pattern": r"load_dotenv\s*\(|dotenv\.load",
        "severity": Severity.INFO,
        "description": "References a dotenv config file (common, but confirm no committed secrets)",
        "recommendation": "OK if the dotenv config is gitignored and contains no committed secrets",
        "file_types": [".py", ".js", ".ts", ".sh", ".md"],
    },
]

# Tokens that look like assignments but are actually placeholders / docs / examples.
_PLACEHOLDER_HINTS = (
    "example", "sample", "placeholder", "xxxx", "xxxxxx", "your-", "your_", "changeme",
    "replace", "todo", "fixme", "dummy", "<", ">", "****", "replacethis", "<your",
    "akiaiosfodnn7example",
)


def _looks_like_placeholder(value: str) -> bool:
    low = value.lower()
    return any(h in low for h in _PLACEHOLDER_HINTS)


# =============================================================================
# SCANNER
# =============================================================================

class SecretScanner:
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path).resolve()
        self.report = ScanReport(
            skill_path=str(self.skill_path),
            scan_timestamp=datetime.now().isoformat(),
            metadata=SkillMetadata(),
        )

    def scan(self) -> ScanReport:
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {self.skill_path}")
        self._extract_metadata()
        self._scan_files()
        self._determine_verdict()
        return self.report

    def _extract_metadata(self):
        skill_md = self.skill_path / "SKILL.md"
        if skill_md.exists():
            self.report.metadata.has_skill_md = True
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            if content.startswith("---"):
                try:
                    end = content.index("---", 3)
                    frontmatter = content[3:end]
                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip().lower()
                            value = value.strip().strip('"').strip("'")
                            if key == "name":
                                self.report.metadata.name = value
                            elif key == "version":
                                self.report.metadata.version = value
                except ValueError:
                    pass

    def _scan_files(self):
        script_extensions = {".py", ".js", ".ts", ".sh", ".bash"}
        for root, _dirs, files in os.walk(self.skill_path):
            for fname in files:
                file_path = Path(root) / fname
                self.report.metadata.file_count += 1
                rel_path = str(file_path.relative_to(self.skill_path))
                self.report.files_scanned.append(rel_path)
                if file_path.suffix in script_extensions:
                    self.report.metadata.script_count += 1
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    self.report.metadata.total_lines += len(lines)
                    self._scan_content(file_path, lines)
                except Exception:
                    pass

    def _scan_content(self, file_path: Path, lines: List[str]):
        rel_path = str(file_path.relative_to(self.skill_path))
        suffix = file_path.suffix.lower()
        for pattern_def in SECRET_PATTERNS:
            if suffix not in pattern_def.get("file_types", []):
                continue
            regex = re.compile(pattern_def["pattern"], re.IGNORECASE)
            for i, line in enumerate(lines, 1):
                m = regex.search(line)
                if not m:
                    continue
                # Reduce false positives for documented example keys.
                matched = m.group(0)
                if _looks_like_placeholder(matched) or _looks_like_placeholder(line):
                    continue
                finding = Finding(
                    pattern_name=pattern_def["name"],
                    severity=pattern_def["severity"],
                    file_path=rel_path,
                    line_number=i,
                    line_content=line.strip()[:200],
                    description=pattern_def["description"],
                    recommendation=pattern_def["recommendation"],
                )
                self.report.findings.append(finding)

    def _determine_verdict(self):
        critical = [f for f in self.report.findings if f.severity == Severity.CRITICAL]
        high = [f for f in self.report.findings if f.severity == Severity.HIGH]
        medium = [f for f in self.report.findings if f.severity == Severity.MEDIUM]
        if critical:
            self.report.verdict = Verdict.REJECT
            self.report.verdict_reason = (
                f"Found {len(critical)} critical credential leak(s): "
                + ", ".join(sorted(set(f.pattern_name for f in critical)))
            )
        elif high:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(high)} high-severity credential issue(s): "
                + ", ".join(sorted(set(f.pattern_name for f in high)))
            )
        elif medium:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(medium)} medium-severity egress/secret issue(s): "
                + ", ".join(sorted(set(f.pattern_name for f in medium)))
            )
        else:
            self.report.verdict = Verdict.APPROVED
            self.report.verdict_reason = "No credential leaks detected"


# =============================================================================
# OUTPUT FORMATTERS
# =============================================================================

def format_markdown(report: ScanReport) -> str:
    lines = [
        f"# Skill Secret Review - {report.metadata.name} {report.metadata.version}",
        "",
        f"**Scan Date:** {report.scan_timestamp}",
        f"**Skill Path:** `{report.skill_path}`",
        "",
        "## Verdict",
        "",
        f"**{report.verdict.upper()}** - {report.verdict_reason}",
        "",
        "## Metadata",
        "",
        f"- **Name:** {report.metadata.name}",
        f"- **Version:** {report.metadata.version}",
        f"- **Has SKILL.md:** {report.metadata.has_skill_md}",
        f"- **Files:** {report.metadata.file_count}",
        f"- **Scripts:** {report.metadata.script_count}",
        f"- **Total Lines:** {report.metadata.total_lines}",
        "",
    ]
    if report.findings:
        lines.extend([
            "## Findings",
            "",
            f"Found **{len(report.findings)}** potential issue(s):",
            "",
        ])
        for f in report.findings:
            lines.extend([
                f"### {f.pattern_name} ({f.severity})",
                "",
                f"- **File:** `{f.file_path}` line {f.line_number}",
                f"- **Description:** {f.description}",
                f"- **Recommendation:** {f.recommendation}",
                f"- **Code:** `{f.line_content}`",
                "",
            ])
    else:
        lines.extend(["## Findings", "", "No credential leaks detected.", ""])
    lines.extend(["## Files Scanned", ""])
    for f in report.files_scanned:
        lines.append(f"- `{f}`")
    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    data = {
        "skill_path": report.skill_path,
        "scan_timestamp": report.scan_timestamp,
        "verdict": report.verdict,
        "verdict_reason": report.verdict_reason,
        "metadata": asdict(report.metadata),
        "findings": [asdict(f) for f in report.findings],
        "files_scanned": report.files_scanned,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Skill Secret Scanner - detect hardcoded secrets in skills"
    )
    parser.add_argument("skill_path", help="Path to skill folder to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Write report to file")
    args = parser.parse_args()

    try:
        scanner = SecretScanner(args.skill_path)
        report = scanner.scan()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = format_json(report) if args.json else format_markdown(report)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)

    if report.verdict == Verdict.REJECT:
        sys.exit(2)
    elif report.verdict == Verdict.CAUTION:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Skill Content Moderator v1.0
Content-compliance scanner for Clawdbot / WorkBuddy / MCP skills.

Scans skill text (SKILL.md / docs / comments) for COMPLIANCE risk signals -
NOT political content. It focuses on:
  - Unauthorized outbound endpoints (webhook / C2-like .php/.asp servers, paid-skill callbacks)
  - Inducement to off-platform contact (add-WeChat / scan-QR / join-group /引流)
  - Undisclosed paid / commercial content (付费/会员/激活码/内部渠道)
  - Undisclosed data collection / exfil phrases (自动上传/回传数据)
  - Phishing-style phrasing (输入银行卡/密码/验证码)

SCOPE BOUNDARY: this tool does NOT encode or detect politically sensitive topics.
It only flags security / marketplace-compliance signals listed above.

Pure standard library. Read-only, no network.

Usage:
    python content_moderator.py <path-to-skill-folder>
    python content_moderator.py <path-to-skill-folder> --json
    python content_moderator.py <path-to-skill-folder> --output report.md

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
from typing import List, Dict


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
    files_scanned: List[str] = field(default_factory=list)


CONTENT_PATTERNS: Dict[str, Dict] = {
    "paid_callback_exfil": {
        "pattern": r"tencentscf\.com|qcloud\.com[^\s\"']*callback|webhook.*(?:付费|收款|激活)",
        "severity": Severity.HIGH,
        "description": "疑似付费 skill 向外部回调/云函数外发数据（数据出境合规风险）",
        "recommendation": "REJECT 或显式披露：付费 skill 不应静默向第三方回调回传用户数据",
    },
    "external_endpoint": {
        "pattern": r"https?://[^\s\"'<>]{4,}\.(?:php|asp|aspx|jsp|cgi)(?:[^\s\"'<>]|$)",
        "severity": Severity.MEDIUM,
        "description": "硬编码非标准服务端端点（.php/.asp 等），可能为外呼/C2/回传",
        "recommendation": "CAUTION - 核实目的并显式告知用户数据去向",
    },
    "webhook_node": {
        "pattern": r"webhook\s*url|回调地址|callback\s*url|推送到.*服务器",
        "severity": Severity.MEDIUM,
        "description": "存在 webhook / 回调推送描述，需确认数据去向已披露",
        "recommendation": "在 SKILL.md 显式说明推送目标与数据内容",
    },
    "inducement_contact": {
        "pattern": r"加微信|加我微信|扫码|扫一扫|关注公众号|私聊我|私我|加QQ|QQ群|加群|电报群|Telegram群|拉你|引流|加好友|加我私",
        "severity": Severity.MEDIUM,
        "description": "存在诱导加微信/扫码/加群等站外引流表述，违反多数市场「禁止站外引流」规则",
        "recommendation": "CAUTION - 移除站外引流话术，或确认市场允许",
    },
    "undisclosed_paid": {
        "pattern": r"付费|收费|会员|打赏|激活码|内部渠道|开通会员|订阅会员",
        "severity": Severity.LOW,
        "description": "包含付费/会员等商业化表述，需确认已明确告知用户",
        "recommendation": "在 SKILL.md 醒目位置披露收费方式与金额",
    },
    "data_collection": {
        "pattern": r"自动上传|上传你的|收集你的|回传数据|读取并上传|悄悄上传|后台上传",
        "severity": Severity.MEDIUM,
        "description": "存在「自动/后台上传你的数据」等未授权数据收集表述",
        "recommendation": "CAUTION - 删除或显式获得用户同意并披露收集内容",
    },
    "phishing_style": {
        "pattern": r"输入银行卡|输入密码|填写验证码|点击不明链接|点击链接领取|扫码领取",
        "severity": Severity.LOW,
        "description": "存在疑似钓鱼/诱导填敏感信息的表述",
        "recommendation": "CAUTION - 移除索取银行卡/密码等敏感信息的话术",
    },
}


def _is_definition_line(line: str) -> bool:
    """Skip lines that merely DEFINE our detection regexes (avoid self-matching)."""
    if "re.compile" in line:
        return True
    if "r'" in line or 'r"' in line:
        return True
    if "CONTENT_PATTERNS" in line:
        return True
    return False


class ContentModerator:
    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path).resolve()
        self.report = ScanReport(
            skill_path=str(self.skill_path),
            scan_timestamp=datetime.now().isoformat(),
        )
        self._compiled = {k: re.compile(v["pattern"]) for k, v in CONTENT_PATTERNS.items()}

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
                in_fence = False
                for i, line in enumerate(content.split("\n"), 1):
                    # Skip fenced code blocks in markdown (examples / docs).
                    if file_path.suffix.lower() == ".md":
                        stripped = line.strip()
                        if stripped.startswith("```"):
                            in_fence = not in_fence
                            continue
                        if in_fence:
                            continue
                    if _is_definition_line(line):
                        continue
                    for pname, pdef in CONTENT_PATTERNS.items():
                        if self._compiled[pname].search(line):
                            self.report.findings.append(
                                Finding(
                                    pattern_name=pname,
                                    severity=pdef["severity"],
                                    file_path=rel_path,
                                    line_number=i,
                                    line_content=line.strip()[:200],
                                    description=pdef["description"],
                                    recommendation=pdef["recommendation"],
                                )
                            )

    def _determine_verdict(self):
        high = [f for f in self.report.findings if f.severity == Severity.HIGH]
        medium = [f for f in self.report.findings if f.severity == Severity.MEDIUM]
        if high:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(high)} high-severity compliance issue(s): "
                + ", ".join(sorted(set(f.pattern_name for f in high)))
            )
        elif medium:
            self.report.verdict = Verdict.CAUTION
            self.report.verdict_reason = (
                f"Found {len(medium)} medium-severity compliance issue(s) - review recommended"
            )
        elif self.report.findings:
            self.report.verdict = Verdict.APPROVED
            self.report.verdict_reason = (
                f"Only low-severity commercial phrasing noted ({len(self.report.findings)}); disclose if paid"
            )
        else:
            self.report.verdict = Verdict.APPROVED
            self.report.verdict_reason = "No compliance risk signals detected"


def format_markdown(report: ScanReport) -> str:
    lines = [
        f"# Skill Content Compliance Review - {report.skill_path}",
        "",
        f"**Scan Date:** {report.scan_timestamp}",
        f"**Skill Path:** `{report.skill_path}`",
        "",
        "## Verdict",
        "",
        f"**{report.verdict.upper()}** - {report.verdict_reason}",
        "",
        "> 范围声明：本工具只检测「安全 / 市场合规」信号（未授权外呼、诱导站外引流、未披露付费、"
        "未授权数据收集、钓鱼话术），**不**进行政治内容审查，也不编码任何敏感话题分类。",
        "",
    ]
    if report.findings:
        lines.extend(["## Findings", "", f"Found **{len(report.findings)}** issue(s):", ""])
        for f in report.findings:
            lines.extend([
                f"### {f.pattern_name} ({f.severity})",
                f"- **File:** `{f.file_path}` line {f.line_number}",
                f"- **Description:** {f.description}",
                f"- **Recommendation:** {f.recommendation}",
                f"- **Text:** `{f.line_content}`",
                "",
            ])
    else:
        lines.extend(["## Findings", "", "No compliance risk signals detected.", ""])
    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    data = {
        "skill_path": report.skill_path,
        "scan_timestamp": report.scan_timestamp,
        "verdict": report.verdict,
        "verdict_reason": report.verdict_reason,
        "findings": [asdict(f) for f in report.findings],
        "files_scanned": report.files_scanned,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Skill Content Moderator - marketplace compliance scan"
    )
    parser.add_argument("skill_path", help="Path to skill folder to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Write report to file")
    args = parser.parse_args()

    try:
        moderator = ContentModerator(args.skill_path)
        report = moderator.scan()
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

---
name: skill-scanner
description: Scan Clawdbot and MCP skills for malware, spyware, crypto-miners,
  and malicious code patterns before you install them. Security audit tool that
  detects data exfiltration, system modification attempts, backdoors, and
  obfuscation techniques.
slug: skill-scanner
displayName: Skill安全扫描
version: 1.0.1
license: MIT
---

# Skill Scanner

Security audit tool for Clawdbot/MCP skills - scans for malware, spyware, crypto-mining, and malicious patterns.

## Capabilities
- Scan skill folders for security threats
- Detect data exfiltration patterns
- Identify system modification attempts
- Catch crypto-mining indicators
- Flag arbitrary code execution risks
- Find backdoors and obfuscation techniques
- Output reports in Markdown or JSON format
- Provide Web UI via Streamlit

## Usage

### Command Line
```bash
python skill_scanner.py /path/to/skill-folder
```

### Within Clawbot
```
"Scan the [skill-name] skill for security issues using skill-scanner"
"Use skill-scanner to check the youtube-watcher skill"
"Run a security audit on the remotion skill"
```

## Requirements
- Python 3.7+
- No additional dependencies (uses Python standard library)

## Entry Point
- **CLI:** `skill_scanner.py`

## Tags
#security #malware #spyware #crypto-mining #scanner #audit #code-analysis #mcp #clawdbot #agent-skills #safety #threat-detection #vulnerability

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

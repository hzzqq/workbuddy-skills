---
name: skill-dependency-auditor
description: |
  skill 的「依赖供应链体检」：静态审计 skill 的依赖声明与 import，找出供应链投毒面——未固定版本、
  从远程 URL/git/本地路径安装依赖（装包即执行任意远程代码）、包名 typosquatting 错拼抢注（如 reqeusts/djanago）、
  白名单外的未核验依赖。覆盖 requirements/pyproject/setup/package.json 与 .py import、.sh/.md 里的远程安装命令。
  P1=远程源依赖/错拼包（需确认），P2=未固定版本/未核验依赖（提示）。与 skill-scanner、skill-safe-install、
  skill-secret-scanner 共同组成「上架前安全体检全家桶」。
  触发词："依赖审计""查 typosquatting""供应链扫描""依赖安全""dependency audit"。
agent_created: true
slug: skill-dependency-auditor
displayName: Skill依赖供应链审计
version: 1.0.0
license: MIT
---

# Skill 依赖供应链审计（skill-dependency-auditor）

依赖是 skill 最大的供应链攻击面：一个错拼的包名（`reqeusts` 而非 `requests`）或一条
`pip install git+https://...` 就能在别人装 skill 时植入恶意代码。本工具把这类风险静态揪出来。

## 何时用
- 发布 skill 前，或拿到别人给的 skill 想先体检。
- CI 里"上架前安全体检"的一环（和密钥泄露扫描、恶意代码扫描并列）。

## 检测项（按严重度）
- **HIGH（需确认）**：依赖来自 `git+http(s)` / 远程 `.whl` / 本地 `file://` 等远程源（装包即可能执行远程代码）；
  包名与白名单知名包编辑距离 ≤2 的疑似 typosquatting（错拼抢注）；`.sh`/`.md` 里从非官方索引远程安装命令。
- **MEDIUM（提示）**：依赖未固定版本（`requests` 而非 `requests==2.31.0`，版本漂移 / 依赖混淆风险）。
- **LOW（放行·人工复核）**：白名单外的未核验依赖——离线无法核验来源，提示人工确认来自官方索引。

## 用法
```bash
python dependency_auditor.py <path-to-skill-folder>
python dependency_auditor.py <path-to-skill-folder> --json
python dependency_auditor.py <path-to-skill-folder> --output report.md
```
退出码：`0`=通过、`1`=caution（存在 P1/P2 风险）。

## 能力边界（诚实声明）
- 白名单是**策展常用包**，离线无法访问 PyPI 实时核验；不在白名单的包一律标记「未核验请人工确认」，
  **不会判定"安全"或"恶意"**——这是启发式，复杂投毒（合法包被接管、依赖混淆）需人工 + 在线核验。
- 只扫描依赖声明与 import，**不执行、不安装、零网络**。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：会不会把我自己的冷门包全标红？→ 会标「未核验(LOW)」，属预期提示，人工确认即可，非拒绝。
- **反模式**：不要把它当"绿了就绝对安全"；它覆盖的是声明层，运行时动态 import 的包可能漏检。
- **快速示例**：见上方命令用法。

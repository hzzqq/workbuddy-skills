---
name: skill-secret-scanner
description: |
  发布 / 安装 skill 前的「密钥泄露体检」：静态扫描 skill 文件夹，找出硬编码的凭据与泄密面，避免把
  API Key / Token / 私钥 / 环境变量文件 秘密随 skill 一起发出去。检测 AWS·Azure·GCP 密钥与连接串、RSA/EC/OPENSSH/PGP
  私钥块、GitHub/Slack/Stripe/Google 令牌、JWT、通用 api_key/secret/token/password 字面量赋值、
  外部 webhook/callback 外呼端点（含 tencentscf.com 等合规相关节点）。
  P0=明文私钥/云密钥/令牌（强烈拒绝），P1=通用密钥赋值/外部 webhook（需确认），P2=环境变量文件引用（放行提示）。
  触发词："扫描密钥""查 skill 有没有泄露密钥""凭据泄露检查""secret scanner""发布前泄密体检"。
agent_created: true
slug: skill-secret-scanner
displayName: Skill密钥泄露扫描
version: 1.0.0
license: MIT
---

# Skill 密钥泄露扫描（skill-secret-scanner）

发布或安装**任何** skill 前的第二道闸门（与 `skill-scanner` 恶意代码扫描、`skill-safe-install`
装包审计互补）：把"悄悄写死在代码里的密钥"揪出来。规则很简单——**密钥只该来自环境变量 /
密钥库，绝不能进仓库**。

## 何时用
- 你写了一个 skill，准备 `publish` 或打包发给别人前。
- 你从网盘 / 聊天 / 仓库拿到别人给的 skill，想先看看它有没有把密钥写死。
- CI 里做"上架前安全体检"的一环。

## 检测项（按严重度）
- **CRITICAL（拒绝）**：`AKIA…` AWS Key、AWS secret/session 字面量、`DefaultEndpointsProtocol=https;AccountName=…;AccountKey=` Azure 连接串、`AIza…` GCP Key、`-----BEGIN PRIVATE KEY-----` 私钥块、`ghp_/github_pat_` GitHub 令牌、`sk_live_/pk_live_` Stripe 密钥。
- **HIGH（需确认）**：`api_key=/secret=/token=/password=` 等通用字面量赋值、`xox[baprs]-` Slack 令牌。
- **MEDIUM（提示）**：`eyJ….` JWT 内嵌、`hooks.slack.com` / `discord.com/api/webhooks` / `api.telegram.org` / `tencentscf.com` 等外部外呼端点（数据出境风险）。
- **INFO（放行）**：环境变量配置文件 / `load_dotenv` 引用——只要配置已被 gitignore 且没提交真实密钥即合规。

## 用法
```bash
# 扫描某个 skill 目录
python secret_scanner.py <path-to-skill-folder>
# JSON 输出（便于 CI 解析）
python secret_scanner.py <path-to-skill-folder> --json
# 写报告文件
python secret_scanner.py <path-to-skill-folder> --output report.md
```
退出码：`0`=通过、`1`=caution（高/中风险）、`2`=reject（致命泄露）。

## 误报抑制
文档里的示例密钥（含 `EXAMPLE`/`example`/`xxxx`/`your-`/`changeme`/`<your-...>` 等占位符）
会被自动跳过，不会误报。真实密钥常是 16+ 位无语义字符串，命中即高优先级复核。

## 安全约定
- 只读扫描目标目录，**零网络外呼、不读取本机环境变量、不访问任何密钥文件**。
- 纯标准库实现，无第三方依赖。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：会不会误报文档里的示例 Key？→ 含 `EXAMPLE`/`xxxx` 等占位符的会被跳过；真实无语义长串才报。
- **反模式**：不要指望它发现"运行时才拼出来的密钥"或混淆过的字符串；它是静态启发式，复杂隐藏需人工复核。
- **快速示例**：见上方命令用法。

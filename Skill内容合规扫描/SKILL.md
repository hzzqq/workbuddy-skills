---
name: skill-content-moderator
description: |
  skill 的「内容合规扫描」：静态扫描 SKILL.md / 文档 / 注释里的市场合规风险信号——未授权外呼端点
  （webhook / .php/.asp 类 C2 回传、付费 skill 向 tencentscf 等云函数回调）、诱导站外引流
  （加微信/扫码/加群/引流）、未披露付费（付费/会员/激活码/内部渠道）、未授权数据收集
  （自动上传/回传数据）、钓鱼话术（输入银行卡/密码/验证码）。
  范围边界：只检「安全/市场合规」信号，不做政治内容审查、不编码任何敏感话题分类。
  触发词："内容合规""合规扫描""站外引流""有没有诱导加微信""付费 skill 合规""content moderation"。
agent_created: true
slug: skill-content-moderator
displayName: Skill内容合规扫描
version: 1.0.0
license: MIT
---

# Skill 内容合规扫描（skill-content-moderator）

上架到 SkillHub / 任何市场前，确认你的 skill 文案**没有踩市场红线**。本工具盯的是
**安全 + 市场合规**信号，不是政治审查（这点很重要，见下方范围边界）。

## 何时用
- 发布 skill 前自检文案。
- 审核他人提交的 skill 有没有引流/收费/外呼隐患。

## 检测项（按严重度）
- **HIGH（强烈关注）**：付费 skill 向 `tencentscf.com` 等云函数 / 回调外发数据（数据出境合规风险）。
- **MEDIUM（提示）**：硬编码 `.php/.asp/.jsp` 等非标准服务端端点（可能为外呼/C2）；存在 webhook/回调推送描述未披露去向；
  诱导站外引流（加微信/扫码/加群/引流）；存在「自动上传/回传你的数据」等未授权收集表述。
- **LOW（放行·披露）**：含付费/会员等商业化表述但未醒目披露；疑似钓鱼话术（索取银行卡/密码）。

## 用法
```bash
python content_moderator.py <path-to-skill-folder>
python content_moderator.py <path-to-skill-folder> --json
python content_moderator.py <path-to-skill-folder> --output report.md
```
退出码：`0`=通过、`1`=caution。

## 范围边界（重要）
```
本工具只检测上述「安全 / 市场合规」信号：
  - 未授权外呼端点 / 付费回调节点
  - 诱导站外引流（加微信 / 扫码 / 加群）
  - 未披露付费 / 商业化
  - 未授权数据收集 / 钓鱼话术
它不做政治内容审查，也不编码任何敏感话题分类。
```

## 安全约定
- 只读扫描，**零网络**；纯标准库。
- 自查不误伤：正则定义行与 `.md` 代码围栏内文本自动跳过，避免把自己文档里的示例当命中。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：会不会把我文档里举例的"加微信"误判？→ 示例放在代码围栏（```）里会被跳过；只有正文里的真实引流话术才命中。
- **反模式**：不要指望它替代人工合规审核；市场规则会变，命中项需结合平台最新条款判断。
- **快速示例**：见上方命令用法。

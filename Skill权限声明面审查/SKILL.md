---
name: skill-capability-reviewer
description: |
  skill 的「声明面审查」：把 SKILL.md 里吹的「只读 / 零网络 / 不访问密钥」等安全声明，
  与代码真实行为（写文件 / 网络请求 / subprocess·os.system 执行命令 / 读 os.environ 密钥 / 删文件）
  做交叉比对，揪出「声称安全但代码干危险事」的声明越权，以及「代码有危险动作但 SKILL.md 只字未提」的未披露能力。
  P1=声明与代码矛盾（高，破坏信任），P2=未披露能力（中，需补声明）。与 skill-scanner / skill-safe-install /
  skill-secret-scanner / skill-dependency-auditor 组成上架前安全体检全家桶。
  触发词："声明审查""能力面审查""只读但写文件""skill 有没有越权""capability review"。
agent_created: true
slug: skill-capability-reviewer
displayName: Skill权限声明面审查
version: 1.0.0
license: MIT
---

# Skill 权限声明面审查（skill-capability-reviewer）

很多 skill 在 SKILL.md 写"只读、零网络、不碰密钥"博取信任，代码里却偷偷 `requests.get` / `open(...,'w')` /
`subprocess`。本工具做**声明 ↔ 实现**的交叉审计，专治这种"说一套做一套"。

## 何时用
- 发布 skill 前自检：我的声明有没有说过头 / 漏说。
- 拿到别人 skill，想快速判断它是否隐瞒了能力（越权风险）。

## 检测逻辑
1. 从 SKILL.md 抓声明关键词：`只读`→不写文件；`零网络/离线/纯本地`→不联网；`不访问密钥/不读取环境变量`→不碰密钥。
2. 扫代码（.py/.js/.sh/.md）真实行为：`requests/httpx/urllib/fetch/axios/curl`(网络)、`open(w)/write_text/to_csv`(写)、`subprocess/os.system/shell=True`(执行)、`os.environ/getenv`(密钥)、`shutil.rmtree/os.remove`(删)。
3. 比对：
   - **声明矛盾（HIGH）**：说了"零网络"却发请求、说了"只读"却写文件 → 信任风险，必须整改。
   - **未披露（MEDIUM）**：代码有危险动作但 SKILL.md 没提 → 要求补声明。
   - **声明一致（INFO）**：说了且代码没相反行为 → 通过。

## 用法
```bash
python capability_reviewer.py <path-to-skill-folder>
python capability_reviewer.py <path-to-skill-folder> --json
python capability_reviewer.py <path-to-skill-folder> --output report.md
```
退出码：`0`=通过、`1`=caution。

## 安全约定
- 只读扫描，**零网络、不读本机环境变量、不执行任何代码**。
- 纯标准库。
- 自查不误伤：声明定义行（含 `re.compile` / `r'...'` 正则字面量）自动跳过，避免把自己的检测规则当命中。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：会不会把我文档里举例的"requests.get"误判成真联网？→ 仅匹配真实代码调用；SKILL.md 正文描述不计入代码行为。
- **反模式**：别拿它当"绿了就无越权"——动态 `importlib.import_module(用户字符串)` 之类运行时行为不在静态覆盖内，需人工复核。
- **快速示例**：见上方命令用法。

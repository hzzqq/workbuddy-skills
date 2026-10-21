---
name: Skill 安全安装
description: |
  带校验和（sha256）与外部安全审查的 skill 安装/卸载工具。用于"引入外部 skill"时：
  先对安装包做 P0/P1/P2 安全审计（destructive 命令、外发数据、密钥读取、提权等），
  P0 强烈拒绝、P1 需显式确认、P2 放行；通过后才按文件清单落地，并在注册表登记每文件校验和；
  卸载只删登记过的文件（且内容未被改动时才删，防误删用户文件）；支持 verify 校验篡改。
  触发词："安装外部 skill""导入 skill""安全审查 skill""卸载 skill""校验 skill 完整性"。
agent_created: true
slug: skill-safe-install
version: 1.0.1
displayName: Skill安全安装·风险扫描
---

# Skill 安全安装/卸载器（skill-safe-install）

引入**外部/他人** skill 时的安全闸门：先审计、再安装、可卸载、可校验。所有操作基于
**每文件 sha256 校验和 + 注册表清单**，绝不模糊删除。

## 何时使用
- 用户从网盘/聊天/仓库拿到一个 `.skill.json` 或 skill 目录，想安装。
- 用户想"安全审查这个 skill 有没有风险""卸载某个 skill""确认我装的 skill 没被改过"。

## 安全审查分级（P0/P1/P2）
- **P0（强烈拒绝，除非用户明确点头）**：递归删根/用户目录(`rm -rf /`、`rm -rf ~`)、
  `git push --force`、提权(`sudo`)、磁盘破坏(`mkfs`/`dd if=`)、读取 SSH/AWS 密钥、
  向外部发送数据(`curl/wget/requests.post` 带 POST/PUT)、`eval(`/`exec(` 动态执行。
- **P1（需显式确认才装）**：任意网络访问(`curl`/`wget`/`requests`/`httpx`)、`git push`、
  全局装依赖(`pip install`/`npm i -g`)、读取环境变量(`os.environ`/`getenv`)、
  调外部命令(`subprocess`/`os.system`/`shell=True`)、`chmod 777`。
- **P2（放行，仅提示）**：写文件、吞异常(`except: pass`)、`print(` 可能打印敏感信息)。

> 与用户既有约定一致：默认**不安装**会把用户代码/数据外发到第三方的 skill（属 P1），
> 除非用户明确授权。外部 skill 若来自 URL，先用**联网隔离**方式（WebFetch）逐文件取回，
> 再跑本工具审计，切勿直接在本机联网环境盲目执行其脚本。

## 用法（脚本在 skill-safe-install/scripts/install_skill.py）

```bash
# 1) 仅审查（不安装）——先跑这个看风险
python ~/.workbuddy/skills/skill-safe-install/scripts/install_skill.py audit <包.json>

# 2) 安装（audit 通过、用户确认后）
python .../install_skill.py install <包.json> --target user      # 用户级
python .../install_skill.py install <包.json> --target project   # 项目级(当前 cwd)

# 3) 卸载（只删登记过的、且未被改动的文件）
python .../install_skill.py uninstall <skill名> --target user

# 4) 校验完整性（检测被篡改/缺失）
python .../install_skill.py verify <skill名> --target user
```

## 安装流程（agent 必须遵循）
1. 运行 `audit`，把 P0/P1/P2 结果清楚告诉用户。
2. **P0 命中且用户未明确授权** → 停止，强烈建议不装。
3. **P1 命中** → 列出具体项，等用户显式确认再继续（必要时 `--force`）。
4. 确认无误后 `install`；成功后打印落地路径与登记文件数。
5. 安装包来源若含二进制 `content_b64`，落地时自动解码。

## 卸载安全机制
- 卸载依据注册表 `.skill-registry.json` 中**登记的原始 sha256**；
- 当前文件 sha256 与登记一致才删除（防止误删用户后来改过的文件或其它文件）；
- 目录空了才 `rmdir`，非空保留并提示。

## 注册表位置
- 用户级：`~/.workbuddy/skills/.skill-registry.json`
- 项目级：`<cwd>/.workbuddy/skills/.skill-registry.json`

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否拦截所有恶意 skill？→ 仅基于正则/文本检测，复杂混淆可能绕过，搭配人工复核。
- **反模式**：不要把它当万能工具；数据/样本不足时按设计诚实返回「无法判断」，请勿强行要求结论。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

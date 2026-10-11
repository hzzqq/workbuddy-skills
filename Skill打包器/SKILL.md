---
name: Skill 打包器
description: |
  将本机已安装的 skill（用户级 ~/.workbuddy/skills/<name>/ 或项目级 .workbuddy/skills/<name>/）
  完整打包成单个 JSON 文件：含解析后的 frontmatter、逐文件内容、每文件 sha256、整包 manifest 校验和，
  以及 SKILL.md 原文 raw。用于备份、迁移、跨机器/跨账号携带、或交付他人审查。
  触发词："把 skill 打包成 json""导出 skill""skill 转 json""备份我的 skill"。
agent_created: true
slug: skill-pack-json
version: 1.0.0
displayName: Skill 打包器
---

# Skill → JSON 打包器（skill-pack-json）

把电脑上某个已安装的 skill 目录，无损打包成单个 `.skill.json` 文件。生成的 JSON 既包含
**结构化字段**（frontmatter、文件清单、校验和），也包含**原文 raw**，可直接反向还原成 `.md`。

## 何时使用
- 用户说"把这个 skill 打包成 json""导出 skill""备份 skill""把 skill 转成 json 给我"。
- 想把本地 skill 带走 / 上传网盘 / 发给别人审查。

## 用法（脚本在 skill-pack-json/scripts/pack_skill.py）

```bash
python <skill-pack-json 目录>/scripts/pack_skill.py <skill目录> [输出.json]
```

例：把 self-driving-dev 打包
```bash
python ~/.workbuddy/skills/skill-pack-json/scripts/pack_skill.py \
       ~/.workbuddy/skills/self-driving-dev \
       ./self-driving-dev.skill.json
```

- 不写输出路径时，默认生成 `<skill名>.skill.json`。
- 自动遍历 skill 目录下**所有文件**（SKILL.md、scripts/、references/、assets/ 等）。
- 文本文件存 `content`；二进制文件（图片/模型等）自动 base64 存 `content_b64`。
- 每个文件计算 `sha256`；整包再聚合出 `manifest_sha256` 作为防篡改指纹。

## 输出 JSON 结构
```json
{
  "format": "workbuddy-skill-package/1.0",
  "name": "self-driving-dev",
  "source_path": "...",
  "packaged_at": "ISO8601",
  "file_count": 1,
  "manifest_sha256": "<聚合校验和>",
  "frontmatter": { "name": "...", "description": "...", "agent_created": true },
  "files": [
    { "path": "SKILL.md", "size": 5724, "sha256": "...", "encoding": "text", "content": "..." }
  ]
}
```

## 还原（如需）
把 `files[].content` 按 `path` 写回目标目录即可；`manifest_sha256` 可用于验证还原后是否一致。

## 与 skill-safe-install 配合
打包出的 `.skill.json` 可直接作为 `skill-safe-install` 的**安装包输入**——
安装工具会先做安全审查（P0/P1/P2），再按文件清单带校验和地落地，并在注册表登记以便卸载。

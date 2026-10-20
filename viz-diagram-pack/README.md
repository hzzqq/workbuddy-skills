# 图表与绘图包（组合 skill）

本目录是一个**非破坏式组合包**：把一组同类 skill 收敛成一个入口，便于调用与跨账号一键导入。
原始 skill 全部保留，本包只做总结、路由与一键安装。

## 文件
- `SKILL.md` — 组合说明、成员表、工作流、导入方式
- `manifest.json` — 机器可读成员清单（含 source / namespace / slug / install_cmd）
- `install_bundle.py` — 新账号一键补齐成员
- `README.md` — 本文件

## 跨账号导入
1. 把本目录整体拷到目标账号的 `~/.workbuddy/skills/<slug>`；或
2. 发布到 SkillHub / GitHub 发布库后从那里导入。
3. 进入目录运行 `python install_bundle.py` 补齐成员（SkillHub 成员自动拉取；本地自研成员需先备好镜像）。

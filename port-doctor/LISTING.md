# 端口医生 · SkillHub 上架物料单（Submission Package）

> 目标平台：**SkillHub**（https://skillhub.cn/）——面向中国用户的 AI Skills 社区，
> 个人开发者真实入口：https://skillhub.cn/dashboard/publish

---

## 1. 基础信息（复制到平台表单）

| 字段 | 内容 | 合规检查 |
|------|------|----------|
| 技能名称 | 端口医生 | ≤20 字 ✓（4 字） |
| 英文名 | 端口医生·本地演示防撞 | 备用 |
| slug | `port-doctor` | 小写字母/数字/连字符 ✓ |
| 版本 | 1.0.0 | 语义化版本 ✓ |
| 作者 | hzzqq（黄子州） | 与你的开发者账号一致 |
| 分类标签 | 开发工具、效率工具、项目管理 | 3–5 个，覆盖搜索场景 |
| 适用平台 | WorkBuddy / 支持 SkillHub 规范的 AI Agent | |

---

## 2. 技能描述（中文，100–300 字）

本地演示最常见的事故是**端口相冲**：A 项目还开着，B 项目也写死 3000，打开 B 的地址看到的却是 A 的页面；
端口被上一个没退干净的进程占着，服务直接起不来报 Address already in use；十几个项目都写死 5000/8000，谁先起谁赢。

端口医生把「端口」变成受管资源：先**体检**——静态扫描项目里的端口声明（package.json 脚本、vite.config、
app.run(port=)、uvicorn、docker-compose、.env、启动 bat/ps1），与操作系统实际监听端口交叉比对，
分清「静态撞车」（两个项目声明同一端口）和「正在发生的相冲」（端口已被别的进程占住），并指明**谁占了谁**；
再**分配**——从托管端口池挑一个真正空闲的端口写进项目 .port.env 并登记在册（项目/端口/PID/时间），
进程死了登记自动作废；最后**回收**——一条命令结束占用者。
纯标准库实现，Windows/macOS/Linux 通用，不改任何项目源码，不自动杀进程。

---

## 3. 英文描述（平台双语备用）

Local demo **port conflicts** solved as a managed resource. Statically scans every project's declared ports
(package.json scripts, vite.config, `app.run(port=)`, uvicorn, docker-compose, .env, launcher scripts),
cross-checks them against the OS's actually-listening sockets, and separates *static collisions* (two projects
claim the same port) from *live conflicts* (someone else already holds it) — telling you **who** holds it.
Then allocates a genuinely free port from a managed pool, writes it to the project's `.port.env`, and keeps a
registry (project / port / PID / time) with automatic stale reclamation. Read-only by default; never edits your
source, never kills a process without explicit `--yes`. Pure Python standard library, cross-platform.

---

## 4. 图标

- **文件**：`assets/icon_512.png`
- **规格**：512 × 512 像素，PNG，圆角透明背景
- **设计说明**：深蓝渐变圆角卡片 + 白色「端」字 + 端口插孔意象 + 右下角绿色心跳点（端口连通）。
- ⚠️ **发布包内不含 png**：SkillHub 拒收含二进制文件的包，图标走后台表单单独上传；
  发布前用 `strip_binary.py` 剥离 png/jpg 等二进制。

---

## 5. 权限声明（基于代码实扫，非声称）

| 权限类别 | 行为 | 声明 |
|----------|------|------|
| 文件系统 | 读 / 写 | **只读**扫描项目文件（package.json / .env / *.py / *.yml / 启动脚本等）用于提取端口声明，**从不修改项目源码**。写入仅两处：`alloc --write` 写 `<项目>/.port.env`，以及登记表 `~/.workbuddy/port_registry.json`。**不删除、不移动任何用户文件**（无 os.remove / rmtree / unlink）。 |
| 网络 | HTTP / socket / 下载 | **无出站网络请求**（实扫：仅 `import socket`，用于**本地端口 bind 探测**，不连接任何远端；无 requests/urllib/http）。 |
| 凭证与隐私 | 读取密钥、Token、通讯录、位置、摄像头 | **无**。仅读取环境变量 `PORTDOCTOR_REGISTRY`（用于指定登记表路径）；不读密钥、Token、通讯录、位置、摄像头。 |
| 进程与代码执行 | subprocess / eval / exec / 动态导入 | **subprocess 有，eval/exec 无**。subprocess 仅用于**只读诊断**：`tasklist` / `netstat`（Windows）、`ps` / `lsof`（POSIX）、`powershell Get-CimInstance`（取占用进程命令行）、`netsh`（读系统保留端口段）。**不执行任何项目代码、不 eval 任何字符串。** |
| 进程终止 | kill | `kill --pid N --yes` 会向目标进程发 SIGTERM（Windows TerminateProcess）。**默认拒绝执行，必须显式 `--yes`**；其余命令一律不杀进程。 |
| 第三方依赖 | 需额外安装的包 | **无**（实扫：只用 Python 标准库 argparse/dataclasses/datetime/json/os/pathlib/re/socket/subprocess/sys/time）。 |
| 环境变量 | 读取 / 设置 | 只读 1 个：`PORTDOCTOR_REGISTRY`。**不修改任何环境变量。** |

**实扫依据**：代码文件 `scripts/{portctl,scanner,allocator,registry}.py`；
扫描项 = 出站网络库 / 写文件 API / 删除类 API / subprocess·eval·exec / 环境变量读取 / 第三方 import。
另：本 skill **刻意不使用 `wmic`**（新版本 Windows 已弃用，且部分安全策略将其列入黑名单），改用 PowerShell CIM 取命令行。

---

## 6. 使用说明（短，用于平台「使用案例」栏）

典型提问：「本地演示端口撞了怎么办」「哪个项目占着 3000 端口」「帮我给这个项目分个不冲突的端口」
「端口被占起不来服务」「多个项目怎么错开端口跑」「演示前帮我体检一遍端口」。

---

## 7. 能力边界（写进产品页，不藏）

- **端口空闲是瞬时事实**：分配到端口与真正 bind 之间存在竞态窗口。登记表能大幅降低多 Agent 并发撞车概率，
  但**不提供分布式锁级保证**；需要严格独占时，让服务启动后回写 PID。
- **只读命令绝不修改**：`scan` / `check` / `doctor` / `list` 全是只读；`alloc` / `release` / `kill` 才写，且 `kill` 需 `--yes`。
- **不改项目源码**：端口以 `.port.env` / 环境变量注入，不去改 `app.py` 里的 `port=5000`。
- **占用者查不到就说查不到**：权限不足或瞬时释放时报「端口被占但查不到进程」，**不编造占用者**。
- **静态解析有盲区**：动态计算出来的端口（运行时才决定）无法静态识别，需靠 `prelaunch` 动态分配兜底。

---

## 8. SkillHub 上架八步清单

1. 打包：剥离 png/jpg 等二进制（SkillHub 拒收含二进制的包），确认 description 为 inline 引号。
2. 打开 https://skillhub.cn/dashboard/publish ，进入发布表单。
3. 填 slug `port-doctor`、版本 `1.0.0`、名称、中英文描述（复制第 1–3 节）。
4. 上传 zip 包（**不含 png**，二进制已剥离）。
5. 单独上传图标 `assets/icon_512.png`（512×512）。
6. 权限声明照抄第 5 节（按真实实扫写，别夸大也别漏报）。
7. 提交后平台会跑安全扫描与人工审核，状态可能为 `pending`——**如实等审核，不谎称已上架**。
8. 回写发布台账：更新本目录 `_meta.json`（slug / version / skillId / versionId / publishedAt / lastPublishStatus）。

---

## 9. 发布包清单

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 技能主文档（含 frontmatter 三件套 slug/version/displayName） |
| `scripts/portctl.py` | CLI 入口：scan / check / alloc / release / list / doctor / kill / prelaunch |
| `scripts/scanner.py` | 端口声明静态提取（带来源文件 + 行号 + 命中片段） |
| `scripts/allocator.py` | bind 探测 / 占用者归属判定 / 端口池分配 |
| `scripts/registry.py` | 全局端口登记表（登记 / 释放 / 僵尸回收） |
| `tests/test_portdoctor.py` | 27 个单测：扫描规则 / 分配 / 登记 / CLI 端到端 |
| `LISTING.md` | 本物料单 |

---

## 10. 发布后 Checklist

- [ ] `python -m pytest tests -q` 全绿（发布前实测 27 passed）
- [ ] 包内无 png/jpg 等二进制
- [ ] `SKILL.md` frontmatter 三件套齐全且 `---` 独立成行
- [ ] 同版本重发返回 409 `VERSION_EXISTS`（权威在架判据），必要时升版重发同一 skillId
- [ ] `_meta.json` 已回写 skillId / versionId / publishedAt / lastPublishStatus
- [ ] 权限声明与第 5 节一致（如代码有改动必须重扫）

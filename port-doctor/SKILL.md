---
name: 端口医生
displayName: 端口医生·本地演示防撞
slug: port-doctor
version: 1.0.0
description: "本地项目演示端口相冲（端口冲突）体检与自动分配：扫描项目目录下所有项目的端口声明（package.json 脚本 / vite.config / app.run(port=) / uvicorn / docker-compose / .env / 启动 bat·ps1），与操作系统实际监听端口交叉比对，定位「谁占了谁」并给出可直接用的空闲端口；从托管端口池自动分配端口、写 .port.env、维护全局登记表（项目/端口/PID/时间）、回收僵尸占用；提供 prelaunch 预检钩子与 kill 占用者。典型场景：演示网址打不开、串到别的项目、端口被上一个进程占着、Flask 5000 与 Next 3000 撞车、多项目同时起服务必须错开端口。触发词：\"端口冲突\"\"端口相冲\"\"端口被占\"\"port conflict\"\"地址打不开\"\"串项目了\"\"分配端口\"\"换端口\"\"本地演示网址\"。"
agent_created: true
license: MIT
---

# 端口医生（本地演示防撞）

## 这个 skill 解决什么

本地演示最常见的一类事故：**端口相冲**。

- A 项目还开着，`B` 项目也写死 3000 → 浏览器打开 B 的地址，看到的是 A 的页面
- 端口被上一个没退干净的进程占着 → 服务起不来，报 `Address already in use`
- 十几个项目各自写死 5000/8000/8080 → 谁先起谁赢，后来者一律失败
- 演示前临时改端口 → 改完忘了改回去，下次又撞

**端口医生**把「端口」变成受管资源：先体检（谁声明了什么、谁真的占着、谁跟谁撞），
再分配（从托管端口池拿一个真正空闲的、写进项目、登记在册），最后回收（进程死了登记自动作废）。

## 快速开始

```bash
# 1) 全机体检：扫项目 → 与实际监听端口交叉比对 → 给出修复建议
python scripts/portctl.py doctor --root E:\project

# 2) 只看某个项目
python scripts/portctl.py check E:\project\project4

# 3) 给项目分配一个空闲端口（写 .port.env + 登记）
python scripts/portctl.py alloc E:\project\project4 --prefer 5100 --write

# 4) 启动前预检（分配 + 写 .port.env + 打印 PORT=xxxx）
python scripts/portctl.py prelaunch E:\project\project4

# 5) 结束占用端口的进程（需 --yes 明确确认）
python scripts/portctl.py kill --pid 12345 --yes

# 6) 查看登记 / 释放登记
python scripts/portctl.py list
python scripts/portctl.py release E:\project\project4
```

所有命令支持 `--json`（`doctor`/`scan`/`check`/`alloc`/`list`），便于接 CI 或其它 Agent。

## 工作原理

### 1. 端口声明怎么提取（纯静态解析，绝不执行项目代码）

| 来源 | 抓什么 | 例子 |
|---|---|---|
| `package.json` | scripts 里的 `--port/-p/PORT=`，以及框架默认端口 | `"dev": "vite --port 5180"` → 5180；`"dev": "next dev"` → 3000 |
| `vite.config.*` | `server.port` | `port: 4173` → 4173 |
| `.env` / `.env.local` | `PORT=xxxx` | `PORT=6100` → 6100 |
| Python 源码 | `app.run(port=)` / `--port` / `http.server` | `app.run(port=5555)` → 5555 |
| `docker-compose*.yml` | `ports:` 的**宿主侧** | `"8081:80"` → 宿主 8081（容器内 80 不占宿主机） |
| 启动脚本 `.bat/.ps1/.sh` | `--port` / `PORT=` | `--port 7777` → 7777 |
| `Procfile` | `$PORT` 动态端口 | 标记为动态，不硬编 |

框架默认端口表：`next/nuxt/serve` 3000、`vite` 5173、`angular` 4200、`flask` 5000、
`django/fastapi/uvicorn/gunicorn` 8000、`streamlit` 8501、`gradio` 7860、`jupyter` 8888 等。

**每条声明都带来源文件 + 行号 + 命中片段**，结论可复核，不搞「黑盒猜测」。

### 2. 「端口被占」怎么判定

- **判定「占没占」用 bind 测试**：能不能绑上 `127.0.0.1:<port>`（Windows 加 `SO_EXCLUSIVEADDRUSE`，
  避免"看着能绑实则被占"的误判）。比 netstat 可靠。
- **回答「被谁占」才用 netstat/lsof**：拿到 PID → 进程名 → 命令行，
  再判断**这个进程是不是该项目自己的**（命令行里含项目路径 = 本项目在跑，属正常）。
- **避坑**：Windows 的 Hyper-V/WSL 会保留大段动态端口（`netsh int ipv4 show excludedportrange`），
  分配时自动跳过这些区间。

### 3. 两类冲突，分开报

| 类型 | 判据 | 含义 |
|---|---|---|
| **静态撞车** | 两个不同项目声明了同一个**宿主机**端口 | 还没启动就埋雷，谁先起谁赢 |
| **正在发生的相冲** | 项目声明的端口已被**别的**进程监听 | 已经撞上了，演示网址会串到别的项目 |

### 4. 分配与登记

- 端口池默认 `5100-5999`（可用 `--pool` 改），优先用 `--prefer` 指定的端口，不可用则自动换
- `alloc --write` → 写 `<项目>/.port.env`（`PORT=xxxx`）供启动脚本读取
- 同时写入全局登记表 `~/.workbuddy/port_registry.json`（项目 / 端口 / PID / 进程 / 时间 / 状态）
- 登记表会做**僵尸回收**：`doctor` / `alloc` 时自动把 PID 已死的 active 记录标为 stale
- 同端口重复分配时，旧记录自动标 `superseded`，避免"登记表里有两个主人"

## 集成到启动脚本（真正一劳永逸的做法）

```bat
@echo off
rem 启动前先要一个不冲突的端口
for /f "tokens=2 delims==" %%P in ('python "%PORTCTL%" prelaunch "%~dp0"') do set PORT=%%P
python -m uvicorn app:app --port %PORT%
```

或 Python 侧：

```python
import subprocess
port = subprocess.check_output(["python", "scripts/portctl.py", "prelaunch", "."],
                                text=True).strip().split("=")[1]
```

登记在 `prelaunch` 时就写好了，进程退出后再 `release` 一下即可。

## 常见疑问

**Q：它会 kill 掉我的进程吗？**
不会自动 kill。`doctor`/`scan`/`check` 全是只读；`kill` 必须显式 `--yes` 才会动手。

**Q：分配到的端口，下次启动还是这个吗？**
`alloc --write` 会把端口固化进 `.port.env`，所以是稳定的；要每次启动动态分配就用 `prelaunch`。

**Q：跨机器能用吗？**
能。纯标准库实现，Windows/macOS/Linux 通用，不依赖任何第三方包，不硬编码任何人的项目路径。

**Q：会不会把别人的项目扫进来？**
只读，扫到就扫到了，不改别人的东西。`alloc`/`release` 只作用于你显式指定的那个项目目录。

**Q：扫一个巨大的目录会不会很慢？**
`--depth` 控制深度（默认 2 层），自动跳过 `node_modules/.git/venv/dist/.next` 等。
实测 21 个项目、约 1.2 万次文件判断，约 12 秒。

## 反模式（别这么用）

- ❌ **别把 `alloc` 的结果硬写回业务代码** —— 用 `.port.env` 或环境变量，别去改 `app.py` 里的 `port=5000`
- ❌ **别靠改 `--port` 手工错开十几个项目** —— 手工改一次漏一个就又撞，用登记表 + 池
- ❌ **别在没看清占用者之前就 kill** —— 先 `doctor` 看清楚是谁（有时占着的正是你要用的另一个服务）
- ❌ **别把容器内端口当宿主机端口** —— compose 的 `"80:80"` 只有宿主侧 80 会占端口（工具已自动区分）
- ❌ **别在 CI 里跑 `alloc`** —— CI 用 `prelaunch` 拿临时端口即可，别把登记表写脏

## 输出示例（真实数据）

```
【正在发生的相冲】3 项
项目              | 端口   | 占用者
-----------------+-------+----------------------------------
方案B-Python轻量MVP | 8000 | python.exe(pid 7964) E:\project\project4\server\.venv\Scripts\python.exe
project4        | 3000 | node.exe(pid 30148) C:\Users\Administrator\.workbuddy\binaries\node.exe

修复建议（已算好可直接用的空闲端口）:
  · 方案B-Python轻量MVP 的 8000 被占 → alloc "...\方案B-Python轻量MVP" --prefer 5100 --write
  · project4 的 3000 被占 → alloc "E:\project\project4" --prefer 5101 --write

【静态撞车】9 项
  · 端口 3000 ← project4, project1
  · 端口 8000 ← 方案B-Python轻量MVP, project4, mirrors
```

## 边界与诚实声明

- **端口"空闲"是瞬时事实**：分配到端口和真正 bind 之间存在竞态窗口。
  登记表能大幅降低多 Agent 并发撞车概率，但**不能提供分布式锁级别的保证**；
  真正要严格独占，请让服务启动后回写 PID（`prelaunch` 已在登记表里留了项目与端口位）。
- 查不到占用进程时（权限不足/瞬时释放），工具会明说「端口被占但查不到进程」，**不会编造占用者**。
- 默认端口池是 5100-5999；如果你自己的项目在这个区间，指定 `--pool` 换一段。
- 不会自动改任何项目源码，也不会自动 kill 任何进程 —— 只给建议和工具，改不改你说了算。

## 目录结构

```
port-doctor/
├── SKILL.md
├── scripts/
│   ├── portctl.py      # CLI 入口（scan/check/alloc/release/list/doctor/kill/prelaunch）
│   ├── scanner.py      # 端口声明静态提取（带来源文件+行号）
│   ├── allocator.py    # bind 探测 / 占用者归属 / 端口池分配
│   └── registry.py     # 全局登记表（登记/释放/僵尸回收）
└── tests/
    └── test_portdoctor.py   # 27 个用例：扫描 / 分配 / 登记 / CLI 端到端
```

自测：`cd port-doctor && python -m pytest tests -q` → 27 passed。

---
name: silent-failure-defect-hunt
description: 用「可证伪的侦察 + 一轮一缺陷」的 SOP 在既有代码库里找并修真实缺陷（尤其「不崩溃但语义错」的静默失败家族），每轮交付修复+定向回归+AST 守卫+提交推送。适用于：用户说「锐评迭代 N 次」「优化项目」「找 bug」「审计代码质量」，或需要把健康检查式的走场迭代升级成真实缺陷修复时。
agent_created: true
slug: silent-failure-defect-hunt
displayName: 静默缺陷狩猎·缺陷
version: 1.0.1
license: MIT
---

# 静默失败缺陷狩猎 SOP（锐评 N 轮迭代）

## 何时用
- 用户说「锐评 N 次」「迭代优化项目 N 轮」「找真缺陷」；
- 已有测试全绿但怀疑「测试只验不崩、没验对不对」；
- 要交付「每轮都有真实收益」的迭代报告（而非走过场）。

## 铁律（每轮验收尺子）
1. **一轮一个缺陷**：能拿证据指认（复现日志 / 实测计数 / 字节对比），不能是"感觉不优雅"。
2. **必须有证伪证据**：修前能证明它错（跑一次打印错误值/异常），修后能证明对了；说不清的就是没做。
3. **定向回归 + 冒烟**：跑与改动相关的测试文件 + 页面/主流程冒烟，全绿才提交。
4. **AST 守卫防回流**：语义类约定（配色、口径、连接必须关、禁止静默 pass）写源码级守卫测试，否则下次一定回退。
5. **提交即推送**（FF-only），提交信息写清「缺陷 + 证据 + 修法 + 测试数」。
6. **守卫必须做负向验证**：新写的守卫测试，要**把历史缺陷注入回去**确认它真的报警，
   再还原并校验文件 hash 一致。没被验证过的守卫 = 没写的守卫（测试全绿可能只是它从不触发）。
   两种注入方式：**注入代码**（还原旧实现，见上文替换脚本）与**注入坏数据**（用退化副本替换
   真实数据文件，见「缺陷侦察清单 · 8」）。后者专治「守卫会不会在告警条件下自我静音」。

## 缺陷侦察清单（按命中率排序，附即用命令）

### 1. 静默吞异常（最高频，且**不崩溃**，最难发现）
```bash
grep -rn "except.*:\s*$" -A1 --include=*.py . | grep -B1 "pass"     # except: pass
# 全量清点（multiline）：
# Grep(pattern="except[^\n]*:\s*\n\s*pass", multiline=True)
```
- 危害分级：**吞掉数据/财务/写盘失败**（严重）> 吞掉可选 UI 增强（可接受）。
- 修法模板：**保留容错 + 留痕 + 分流**——
  ```python
  except sqlite3.OperationalError as e:
      if "no such table" in str(e).lower():
          logger.debug("...表未创建，跳过")        # 预期情形：不吵
      else:
          logger.warning("...失败，缓存未清空: %s", e)  # 真失败：必须可见
  ```
- ⚠️ 插 `logger.xxx` 前先 AST/grep 确认该模块 logger 名（`_feed_io` 的 logger 常被 re-export，名字可能不是 `__name__`）。

### 2. 静默错数据（比吞异常更毒：结果是"看起来正常"的错值）
- **口径把"无信息"当反证**：平盘/停牌/缺失被算成"看错"。→ 改**三态**：方向 ∈ {+1, -1, 0=无信息}，`0` 不计入命中率分母，并单独计数披露。
- **边界兜底造数据**：窗口外/越界时用 `list[0]` 之类硬凑一个值。→ 一律返回 `None`（无法判定）+ 计数上报。
- **二元组漏解包**：`df = f()` 而 `f` 返回 `(df, meta)` → 后续判断永远走兜底分支。→ 注释写明返回结构 + AST 守卫扫调用点。
- **缓存键漏参数**：`cache_key` 未含 `period/adjust/market` 等入参 → 换参数仍读旧数据。→ 补齐键，加"同函数不同参数不得命中同一键"的测试。

### 3. 资源泄漏（跑久了才炸，单测抓不到）
```bash
grep -rn "_get_conn()\|sqlite3\.connect(" --include=*.py . | grep -v tests
```
- 修法：`with contextlib.closing(get_conn()) as conn:`（**`with conn:` 在 sqlite3 里只是事务，不会 close！**）。
- 守卫：AST 扫「函数内赋值了连接但同函数无 `.close()`」，忽略 `_get_conn` 工厂自身。

### 4. 尺寸/线程/超时（"卡死"家族）
- 后台长任务无硬超时 → 网络挂起即永久阻塞（重试也永不触发）。修法：`socket.setdefaulttimeout(N)` + 检查点 + 高频进度日志。
- `requests.*` 无 `timeout=` → UI/进程挂死。先 `grep -rn "requests\.\(get\|post\)(" -A4` 逐个人眼确认。

### 5. 环境耦合与副本漂移
- **硬编码机器专属绝对路径**（`E:/project/...`）→ 双机/部署静默失效。改为 env 可覆盖，默认值不变。
- **同一份默认值被两个模块各抄一份** → 必然漂移，且往往其中一份指向**根本不存在的路径**。
  实例（R1，2026-09-17）：`shepherd_ladder._p1_signals_dir()` 自抄了一份 P1 信号目录默认值，
  与 `p1_signal.discover_source_dirs()` 的口径不一致且该目录本机不存在 →
  「刷新事件池」脚本文档承诺的缺省布局**永远跑不通**，却只返回 `reason=no_p1_signals_dir` 不报警。
  侦察：对同一语义的解析逻辑搜第二处定义（`grep -rn "_signals_dir\|_dir()"`），逐个 `os.path.isdir()` 验真。
  修法：**删掉副本**，让非所有者模块 import 单一真理源；再加 AST 守卫「该绝对路径只许出现在所有者文件里」
  （扫字符串常量、**排除 docstring**，否则会被自己写的说明文字误伤）。
- **候选排序用「文件 mtime」而不是「数据日」** → 静默用了更旧的数据。
  实例（R2）：信号目录按 mtime 取最新，结果 (a) 一个 `latest_date=None` 的旁路产物恰好 mtime 最新，
  它**一个人卡死整条链路**（同目录 8 个有效导出全被无视）；(b) 即便跳过无效文件，mtime 序也会先选到
  `latest_date=2026-07-31` 的旧导出，而同期存在 `2026-08-14` 的更新导出。
  侦察：`ls -lt` 看文件时间 vs `json.load(...)["latest_date"]` 看数据日，两者**刻意错开**才能暴露。
  修法：按 `(data_date, mtime)` 降序取第一个**有效**候选；损坏/字段不全的跳过而不阻断；
  成功时把 `picked` / `skipped_*` 写回 status（留痕）；但**全部无效时仍必须拒绝写入**（保住「不覆盖既有快照」的安全语义）。
- **常量/公式在多处复制**（生产模块 + 分析脚本各一份）→ 漂移后"分析结论校验的不是生产行为"，且无测试报警。→ 统一 import 生产模块，并加"必须是同一对象（`is`）"的测试。
- 数值非有限值：`round(float('nan'))` 抛 ValueError、`inf` 抛 OverflowError（`if x is None` 挡不住）。→ 显式判 `v != v or v in (inf, -inf)`，降级 0 + 留痕。

### 6. 文档/论文数字与实算脱节
- 代码口径一改，正文/摘要仍引用旧数字 → 学术硬伤。→ 加测试：从实算产物 JSON 读数字，断言文档逐字包含（分式、百分比、表格行都要）。改口径必须重跑产物并同步文档。

### 7. 生成物造假 / 契约不匹配（导出图、截图、报告 —— 最容易被公开引用而无人发现）
- **判据**：合成数据本身不是罪，**「不披露 + 被当成真实产出引用」才是**。
  正当兜底长这样：函数名 `_synthetic_df`、docstring 写「仅用于离线演示」、日志/页面明确打印
  「离线合成演示行情」；造假长这样：函数名叫 `shot_backtest_curve`、标题叫「策略回测收益曲线」，
  内部却是 `np.random` 编的"策略跑赢基准"。
- **契约不匹配型（隐蔽度最高）**：喂给可视化/导出函数一个 dict 或 DataFrame，**键名/列名对不上**
  时对方常写成 `.get(key, 0)` 或提前 return 空图 → **不报错**，产出一张"看起来正常"的错图
  （典型：三点全 0 → 雷达图塌缩成一个点；列名不符 → 一张写着"数据缺失"的报错图，而它正被 README 引用）。
  ```bash
  # 先找"被喂数据"的导出/绘图函数，抽出它真正读取的键
  # 再 AST 比对调用方提供的键是否覆盖
  ```
  守卫写法：AST 从被调方抽 `d.get("X"...)` 的键集合，从调用方抽 dict 字面量键集合，断言**后者 ⊇ 前者**。
- **排查命令**：
  ```bash
  grep -rn "np.random\|default_rng\|random.normal\|模拟\|合成\|演示视觉\|fake\|dummy" --include=*.py scripts/ modules/ pages/
  # 再逐个追：它产出的文件被谁引用？（grep 文件名于 README/docs）
  # 被公开引用的造假物优先级最高——那是"已经发出去的假业绩"。
  ```
- **修法**：① 改为调用真实引擎/真实缓存；② 取数不足或异常 → **跳过不产出文件**（绝不落占位图）；
  ③ 加「全 0 / 空值即契约不匹配」的运行期守卫；④ 同步修掉引用该图的文档标题（标题常与真实图不符）。
- **反面清单**：`except` 分支里给"示意数据"（硬编码 72/58/65/48 之类）再照常导出文件 —— 等于用编造的
  数值冒充真实指标，只是日志里小声说了句"用示意数据"。

### 8. 守卫自我静音（测试层的静默失败，最讽刺的一类）
- **判据**：`pytest.skip(...)` 的**理由**属于「告警条件」而非「环境缺失」。
  环境缺失（数据被 gitignore、依赖未装、需 `OFFLINE_TEST=0`）→ skip 正当；
  「数据疑似被错误覆盖」「样本不足，人工核查」「版本对不上」→ **必须 fail**：
  这些恰恰是守卫存在的理由，skip 等于回退**真的发生**时把自己静音。
- **实例（R3，2026-09-17）**：`test_shepherd_analyze_history.py` 里那条 docstring 写着
  「防止被错误重跑覆盖后静默回退」的守卫，在现代段样本 <50 行时 `pytest.skip`。
  实测把 CSV 现代段缩到 20 行 → 输出 `SKIPPED`、整套测试仍 `exit=0`，警报根本不响
  （而该 CSV 在 2026-09-16 就真实退化过一次，靠人工比对 `.bak` 才还原）。
- **侦察命令**：
  ```bash
  grep -rn "pytest.skip\|mark.skipif\|xfail" --include=*.py tests/ backend/tests/ modules/tests/
  # 逐条判：这个 skip 的理由是「环境不具备」还是「结果不对劲」？后者一律改 assert。
  ```
- **兼查 docstring 与事实是否相符**：同一轮里还发现两处守卫声称校准件「**随仓库发布**、必须存在」，
  而 `data/` 已被 `.gitignore` 忽略、根本没随仓分发 —— 声明是假的，缺失时又只能 skip，
  等于这条闸在 clone 出来的环境里从不生效。改法：按事实改写声明，并说清「缺失才可 skip，
  存在就必须经得起检验」。
- **负向验证技法（退化数据注入）**：这类守卫的验证不能靠注入代码，要靠**注入坏数据**——
  备份真实数据文件 → 用退化副本替换 → 跑该条用例 → **断言结果是 failed 而不是 skipped**
  → 还原并用 **sha256 比对**确认原文件分毫未动 → 复绿。
  ```python
  h0 = sha(CSV); shutil.copy2(CSV, BAK)      # ① 备份 + 校验
  csv_degenerate(CSV, modern_rows=20)        # ② 注入退化数据
  c, out = run_one_test()                    # ③ 跑单条用例（限定 node id，避免污染其他用例）
  assert c != 0 and "SKIPPED" not in out     # ④ 必须 fail，skip 即 HIT
  shutil.copy2(BAK, CSV); assert sha(CSV) == h0   # ⑤ 还原 + hash 一致
  ```

## 工具教训（血泪，务必遵守）
- **同一文件的多条 Edit 批量发送会静默丢改**：工具回 `Successfully`，磁盘只落其中一部分（含 U+3000/中文标点时更易触发）。→ 多处精确替换改用**带断言的 Python 替换脚本**：
  ```python
  import pathlib
  P = pathlib.Path(r"...\file.py"); src = P.read_text(encoding="utf-8"); orig = src
  for i,(old,new,expect) in enumerate(REPL,1):
      n = src.count(old); assert n == expect, f"替换{i}命中{n}次（期望{expect}），中止"
      src = src.replace(old, new)
  assert src != orig
  P.write_text(src, encoding="utf-8")
  chk = P.read_text(encoding="utf-8")           # 回读断言
  for must in ["新标记1","新标记2"]: assert must in chk
  ```
  好处：一次调用完成 N 处替换，且**失败即报错**而非静默半成品。
- 任何编辑后**回读磁盘 grep 确认**是硬规矩（`sed -n` 看真实行）。
- 断言别写太宽：例如守卫里 `assert "base = sd[0]" not in src` 会被自己写的注释误伤 → 用 AST 精确匹配赋值节点。
- **断言会被自己的注释/文档串命中**（高频踩坑）：你为了说明"已修缺陷"而引用的那段旧代码或旧标题，
  会出现在新写的 docstring/注释里 → `assert "旧串" not in back` 当场失败（写入其实已成功）。
  对策：断言写成 **AST 语义检查**（如"卡片元组里不含 X"、"赋值语句里不含 X"），而不是裸文本包含。
- **产物必须真的渲染过才算验证**：只校验字节（无残留 token、无外链、图片已内联）不够 —— 要看一眼。
  没有 playwright/agent-browser CLI 时的可行路径（系统装了 Chrome 即可）：
  ```bash
  CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
  # 截图（--force-device-scale-factor=1 必加，否则按系统缩放会量错版面）
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
      --window-size=1440,1300 --virtual-time-budget=6000 --screenshot=out.png "file:///abs/path.html"
  # 测页面真实高度/找最高元素：注入脚本把结果写进 <title>，再用 --dump-dom 抓
  "$CHROME" --headless=new --disable-gpu --window-size=1440,900 --virtual-time-budget=5000 \
      --dump-dom "file:///probe.html" | grep -o "<title>.*</title>"
  ```
  分段看长页面：复制 N 份注入 `html,body{margin-top:-Npx !important}` 逐段截。
  ⚠️ 不给 `--force-device-scale-factor=1` 时，量出的高度可能是真实值的 ~1.5 倍（本机 DPI 缩放），
  会误判"页面底部有大片空白"。
- **验证脚本绝不能丢弃 HTTP 错误响应体 —— 那是唯一装着真相的载荷**（真实踩坑，卡了很久）：
  ```python
  # ✗ 反面：urllib 直接抛 HTTPError，服务端埋在 body 里的错误原文全被扔掉
  with urllib.request.urlopen(req) as r: ...
  # 现象：只看到 "HTTP Error 500: INTERNAL SERVER ERROR"，
  # 而服务端的 catch-all 明明回了 {"error":"AI 生成异常：<真原因>"} —— 有原文却拿不到，
  # 于是只能靠猜（一度怀疑是"段落切分 bug"，全是错的）。
  ```
  正确写法：显式接住异常并把 body 打出来，且**对非 2xx 一律打印响应体**：
  ```python
  try:
      with opener.open(r, timeout=180) as resp: return resp.status, resp.read()
  except urllib.error.HTTPError as e:
      body = e.read().decode("utf-8", "replace")
      print(f"   ⚠ HTTP {e.code}，响应体：{body[:400]}")   # ← 关键，别省
      return e.code, body
  ```
  推论（更普适）：**任何验证/巡检脚本，遇到失败必须打印被验证方的原始回答**。
  只打印"我这边观察到失败"，等于把可诊断故障降级成不可诊断故障——
  这与被排查的产品里"静默失败"是同一类毛病，只是搬到了工具链上。

## 报告模板（每轮给用户的表格）
| 轮 | 真缺陷（有证据） | 修复 | 新增测试 |
|---|---|---|---|
| R1 `sha` | 现象 + 量化证据（如「4093 日中 177 天平盘被当作下跌」） | 一句话修法 | 测试文件 N 例 |

结尾给：验证基线（各套件 passed 数）、远端同步状态、存量富矿（如"仍有 60+ 处 except: pass"）作为下一轮输入。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

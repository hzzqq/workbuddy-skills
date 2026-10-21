---
name: split-god-module
summary: 把 Python「上帝模块」（单文件 1000+ 行、多职责）按最低风险法拆成「编排层 + 叶子子模块 + 全名 re-export」，不破坏任何调用方。
description: >
  当项目里出现 1000+ 行的巨型模块（god module）需要拆分时，用本 skill 的「叶子子模块 + re-export」法。
  核心是：把底层/无依赖的部分抽到 _xxx_io.py / _xxx_nlp.py / _xxx_base.py 等叶子模块，原文件退化为
  编排层并 `from 叶子 import 全部公开名` 保持向后兼容，全站零改动。避开两类必踩坑：
  (1) re-export 是值拷贝，被抽离子模块内部引用原模块的常量/标志必须改为跨模块延迟读取或随函数一起搬走；
  (2) 环依赖——共享 helper 必须放进双方都能 import 的叶子 _xxx_base.py，绝不能让叶子 import 回父模块。
keywords: [refactor, god-module, split, python, re-export, circular-import, value-copy]
slug: split-god-module
displayName: 神模块拆分
version: 1.0.0
license: MIT
---

# 上帝模块最低风险拆分法

适用于：单文件 1000+ 行、含多个 class/多组职责的 Python 模块（如 `fetcher.py` / `news.py` /
`compare.py` / `widgets.py`）。目标：**拆完全站 import 行为不变**，只用 `pytest` 验证、不手动改调用方。

## 三步法

### 1. 找「叶子边界」
用 grep 画出 `^class` / `^def` 与跨组引用：
```bash
wc -l modules/<m>.py
grep -nE "^class |^def " modules/<m>.py
# 看某组是否引用别的组（有则不是叶子）
sed -n '<组起>,<组止>p' modules/<m>.py | grep -nE "其他组函数名"
```
- **叶子**：一组函数只依赖本组 + 标准库 + 已存在的底层模块（如 `fetcher`、`session`）。直接抽。
- **共享 helper**（被多组引用，如 `STAR_AI_LOGO`、`_hex_to_rgba`）：单独抽成 `_<m>_base.py`（真叶子），
  原模块与子模块都从它 import，避免环依赖。
- **跨组调用**：例如 render 组调了 data 组的 `_biz_groups`，则把 `_biz_groups` **连同它引用的常量**
  （如 `_INDUSTRY_GROUPS`）一起搬进叶子，否则 NameError。

### 2. 写拆分脚本（基于缩进，不用 AST 手写）
顶层 `def`/`class` 缩进为 0，用「下一顶层 def 之前」切分块：
```python
import re
src = open("modules/<m>.py", encoding="utf-8").read()
lines = src.split("\n")
tops = [(i, m.group(2)) for i,l in enumerate(lines)
        if (m := re.match(r"^(def|class)\s+(\w+)", l)) and l[:1] not in (" ","\t")]
blocks = {}
for idx,(start,name) in enumerate(tops):
    end = tops[idx+1][0] if idx+1<len(tops) else len(lines)
    blk = lines[start:end]
    while blk and blk[-1].strip()=="": blk.pop()
    blocks[name] = "\n".join(blk)
# 抽取 LEAF_NAMES 到 _<m>_leaf.py；其余保留在 <m>.py；最后追加 re-export
```
⚠️ `find_def` 正则**不要**包含 `# ===`（注释），否则会误匹配分隔注释、把整段数据层丢掉。

### 3. 全名 re-export + 验证
原模块底部：
```python
from modules._<m>_leaf import (  # noqa: E402,F401
    NAME1, NAME2, ...   # 用脚本从叶子模块实际顶层名自动生成，别手列（会漏）
)
```
- 名字列表用正则扫叶子模块顶层 `def`/`class`/`CONST =` 自动生成（排除 `logger` 以免遮蔽父模块自己的）。
- 跑 `pytest tests/`（全量），遇到 NameError 逐个补 import（通常是被抽离子模块缺 `jieba`/`re`/
  `hashlib`/`Counter`/`pd`/`logger` 或引用了原模块的常量 → 改为从 `_<m>_base` 跨模块 import）。
- 提交 + **安全 fast-forward 推送**（多机并发项目：先 `git ls-remote --heads origin` 拿远端 SHA →
  `git merge-base --is-ancestor <SHA> main` 验证 → `git push`，不 `--force`）。

## 必避两个坑
1. **值拷贝**：`from A import FLAG` 是值拷贝。若测试 `monkeypatch.setattr(B,'FLAG',False)` 想影响 A 内代码，
   必须让 A 内改为延迟读 `B.FLAG`（如 `def _is_ok(): return modules.<m>.FLAG`）。
2. **环依赖**：叶子模块**绝不能** `import` 回父模块。共享标志/helper 一律放 `_<m>_base.py` 叶子。

## 不拆的情形
- 单 class 大文件（如 `visualizer.py` 的 `Visualizer`）——拆类风险高、收益低，跳过。
- 纯 CSS 字符串常量模块（如 `ui_theme.py`）——虽大但内聚，跳过。
- 已较内聚的 3-class 文件（如 `backtest.py`）——只抽真正独立的叶子（如结果 dataclass）才划算。

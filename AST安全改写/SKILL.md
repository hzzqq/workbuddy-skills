---
name: ast-safe-edit
description: 用 AST 安全改写 Python 源码（批量补参数、插入配置、改调用）时，规避「字节偏移 vs 字符偏移」错位坑与「双逗号」语法坑。适用于对含中文/多字节字符的 .py 做机械化批量编辑（如给所有 st.dataframe 补 height=、给 st.plotly_chart 补 config=）。
slug: ast-safe-edit
displayName: AST安全改写·代码重构
version: 1.0.1
license: MIT
---

# AST 安全改写 Python 源码

用 `ast` 精确定位 `Call`/节点并改写源码，比正则/字符串匹配安全得多——但有两个隐蔽坑，踩中会让编辑插到错误的 `)`（甚至插进装饰器、下一行），且只在含中文的行暴露。本项目因此翻车两次，以下是已验证的正确做法。

## 何时用
- 批量给某类调用补关键字参数（`st.dataframe` → 补 `height=400`；`st.plotly_chart` → 补 `config=`）。
- 批量改写调用形态（`st.rerun()` → `st.rerun(scope="fragment")`）。
- 源码含中文（列名、caption、注释），且目标调用可能跨多行。

## 坑 1：`ast.end_col_offset` 是**字节**偏移，源码 `str` 是**字符**索引
Python 3.8+ 起，`node.end_col_offset` / `node.col_offset` 是 **UTF-8 字节偏移**。但你在 `src`（Python `str`）里用整数下标是**字符**索引。含 CJK 字符的行（如 `column_config={'净额': ...}`），字节数 > 字符数，直接 `src[offs[lineno-1] + node.end_col_offset]` 会**越界或指错位置**。

**正确做法**：offset 表用字节长度构建，并在真正索引 `src` 前把「绝对字节位置」换算回「字符索引」。

```python
def line_byte_starts(src):
    """每行起始处的 UTF-8 字节偏移。"""
    starts = [0]
    for line in src.split("\n"):
        # +1 为 "\n"（行尾若有 "\r" 算在 line 字节内，CRLF 也正确）
        starts.append(starts[-1] + len(line.encode("utf-8")) + 1)
    return starts

def byte_to_char(src, byte_pos):
    """绝对字节偏移 → 字符索引。"""
    b = 0
    for i, ch in enumerate(src):
        if b >= byte_pos:
            return i
        b += len(ch.encode("utf-8"))
    return len(src)

# 用法：
abs_byte = line_byte_starts(src)[node.end_lineno - 1] + node.end_col_offset
char_idx = byte_to_char(src, abs_byte)   # 这才是能安全用于 src[...] 的索引
```

## 坑 2：多行调用末尾已带逗号时，再补 `, xxx` 会成「双逗号」SyntaxError
若原调用以 `},` 结尾（`},` 已带逗号），在闭合 `)` 前插 `, height=400` → `}, , height=400)` → 语法错误。

**正确做法**：插入前看闭合 `)` 前一个非空白字符；若是 `,`，则**不加前导逗号**。

```python
j = off - 1
while j >= 0 and src[j] in " \t\r\n":
    j -= 1
insert = text if (j >= 0 and src[j] == ",") else ", " + text
new_src = new_src[:off] + insert + new_src[off:]
```

## 必做护栏
1. **写盘前 `ast.parse(new_src)` 校验**：语法坏就跳过该文件，绝不留坏代码。
2. **从后往前应用偏移**（按 offset 降序排序），避免前面插入改变后面偏移。
3. **只匹配确切形态**：如 `st.rerun()` 仅当 `args==[] and keywords==[]`；`st.dataframe` 仅当 func 是 `Attribute` 且 `attr=="dataframe"` 且无 `height` 关键字。
4. **跳过装饰器误伤**：`@safe_fragment(...)` 之类 Name/Attribute 调用不是 `st.dataframe`；字节错位时可能误插——靠坑 1 的根本修复 + 写前 `ast.parse` 兜底。

## 最小可用模板
见本项目 `scripts/_perf_table_height.py` 与 `scripts/_perf_i10_rerun.py`（已验证可用，可复制改造）。核心骨架：
```
parse → 收集 (offset, text) 候选 → 过滤（精确形态 + 字节→字符换算）→ 降序应用（双逗号防护）→ ast.parse 校验 → 写盘
```

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

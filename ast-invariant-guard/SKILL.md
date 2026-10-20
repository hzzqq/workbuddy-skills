---
name: ast-invariant-guard
description: 用 AST 写「源码级防回退护栏」测试，把项目约定/安全基线锁死。适用于：约定靠自觉易回退、错误不崩溃但语义错（如配色反转）、review 肉眼看不出、或运行时难构造的场景（鉴权遗漏、响应未走统一信封、分页下限、凭据外泄、静默吞异常、fragment 内整页 rerun）。当用户说「锁死约定」「防止回退」「加护栏」「审计有没有违规」时使用。
agent_created: true
---

# AST 源码级防回退护栏

## 何时用
满足**任一**条件就该写 AST 护栏，而不只写行为测试：
- 违规**不崩溃**（如红涨绿跌用反了、整页 rerun 拖慢），行为测试测不出来；
- 违规路径**运行时难构造**（如新路由忘了加鉴权、响应绕过统一信封）；
- 约定散落几十个文件，靠 review 必然漏。

## 标准流程
1. **先做审计扫描**（临时脚本，扫完全项目再决定规则）。别凭空定规则——
   先跑一遍看当前违例数：违例 0 → 直接锁死；违例少量 → 修完再锁；违例几百 →
   规则定宽了，收窄（例如「禁止所有硬编码颜色」578 处不切实际，
   收窄为「涨色不得配负向比较」才可执行）。
2. **收窄到可执行**：只断言能**静态确定**的那一类，无法判定的一律跳过避免误报。
   - 三元配色：只判 `>` `>=` `<` `<=`；`== '利好'` / 函数调用跳过。
   - 静默吞异常：只约束宽泛捕获（`except:` / `Exception` / `BaseException`）；
     窄捕获 `except ValueError: pass` 常是刻意的，别一刀切。
3. **写测试文件**，放 `tests/`（前端）或 `backend/tests/`（后端）。
4. **加两个自检**，防止测试自己空转/变成死条目：
   - 断言扫描到的目标数量下限（如「路由数 ≥ 50」「至少扫到 1 处三元表达式」）；
   - 白名单/允许条目做**失效检测**（文件改名后必须报错而不是默默失效）。
5. 跑对应套件确认 0 违例 + 零回归，再提交。

## 可复用骨架
```python
import ast, glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _deco_name(d):                      # 装饰器名（支持 @x 与 @x(...)）
    f = d.func if isinstance(d, ast.Call) else d
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)

def _callee(call):                      # 调用名（支持 a.b() 与 b()）
    fn = call.func
    return fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)

def _subtree_names(node):               # 子树里所有变量名
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}

def test_invariant():
    bad = []
    for path in glob.glob(os.path.join(ROOT, "pages", "**", "*.py"), recursive=True):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            ...                          # 收集违规
    assert not bad, "说明 + 修复指引:\n" + "\n".join(f"  {p}:{ln}" for p, ln in bad)
```

## 已验证有效的高价值护栏（StockSignal 实测）
| 护栏 | 关键 AST 判据 |
|---|---|
| `/api` 路由 100% 鉴权 | 路由函数装饰器集合 ∩ {jwt_required, admin_required} 为空 |
| 响应必走统一信封 | 路由函数 `return` 的值不是 Dict/List、不是 jsonify/make_response/Response |
| fragment 内禁止整页 rerun | `@safe_fragment` 函数里的 `rerun()` 调用无 `scope` 关键字 |
| 凭据零泄漏 | 序列化方法内敏感键名/属性 + 日志 f-string 插值变量命中 password/secret/api_key |
| 分页走有界 helper | 赋值目标含 limit/page/offset 且值里有 `request.args.get` 但没调 parse_* |
| 红涨绿跌语义 | 三元真值分支含 UP_COLOR 却用 `<`/`<=`（DOWN 反之） |
| 静默吞异常 | `ExceptHandler.type ∈ {Exception, BaseException, None}` 且 body 仅 `Pass` |

## 踩过的坑
- **批处理脚本插 import 的铁律**：只插模块顶部 import 区（docstring / `from __future__`
  之后、首个真实代码之前）。必须先跳过**模块 docstring** 与**多行括号 import 块**
  （`from x import (` … `)`），否则会插进缩进块或未闭合括号里，导致几十个文件
  SyntaxError。改完必跑全站 `compileall` + 页面冒烟。
- **同名「全局 import + 函数内局部重赋值」** → UnboundLocalError。批量把函数内惰性
  import 提到模块顶部时最易踩；遇到就恢复函数内惰性导入。
- **别为了「去敏/合规」把功能删没**：护栏测试里反向断言一下正常路径仍可用
  （如 `to_public` 仍返回 username/role）。

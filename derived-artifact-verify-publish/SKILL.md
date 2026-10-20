---
name: derived-artifact-verify-publish
description: 生成/扫描「衍生资源」（模板文件、默认配置、注册表、清单、构建产物）时的三道护栏：默认项必须写死不能靠排序、校验必须调用真正使用它的那段代码、校验通过才准上线。适用于：往目录里新增一种模板/皮肤/主题/规则文件、按 glob/listdir 选默认项、写生成脚本（make_*.py）、出现"加了新文件之后默认行为被悄悄改了"或"校验说坏了但其实好着"。触发词：新增模板、多套皮肤、默认模板、glob 取第一个、生成脚本、资源校验、为什么默认变了。
agent_created: true
---

# 衍生资源的三道护栏：写死默认 · 真函数校验 · 先验后上线

## 何时用
代码里有「一个目录 / 一张清单 / 一套注册表」充当**可扩展资源池**，且存在
"程序自己挑一个当默认"或"脚本生成衍生文件"的环节：

- 模板 / 皮肤 / 主题 / 邮件版式 / 报表格式目录
- 默认配置文件、默认策略、默认渠道（`config.DEFAULT_XXX`）
- `make_templates.py`、`sync_assets.py`、`build_manifest.py` 这类生成脚本

这类地方的 bug 几乎全属于**静默失败**：不报错、不提示、测试也照样过，
只是行为被悄悄换了。三道护栏专治它。

---

## 护栏 1：默认项**写死**，绝不依赖目录扫描/排序顺序

最典型的翻车：

```python
# 之前：目录里只有一份模板，怎么写都对
TEMPLATE = glob.glob(os.path.join(TEMPLATE_DIR, '*.docx'))[0]
```

往里加第二份 `影讯推文模板-蓝.docx` 之后——**默认模板被换掉了，还不报错**。
原因是排序按文件名字符比较：

```
'影讯推文模板-蓝.docx'  vs  '影讯推文模板.docx'
                     '-' = 0x2D  <  '.' = 0x2E      → 带"-蓝"的排在前面
```

同理还有 `-2` / `_v2` / `(备用)` 之类后缀，谁排在前面取决于 ASCII 码，
不是你脑子里的"主文件在前"。**`glob` / `os.listdir` 的顺序本身也是不可依赖的**
（不同文件系统、不同 OS 顺序不同）。

正确写法：

```python
_DEFAULT_KEY = '影讯推文模板'          # ← 显式写死，这是唯一事实来源

def _scan():
    out = []
    for p in glob.glob(os.path.join(DIR, '*.docx')):
        base = os.path.splitext(os.path.basename(p))[0]
        if base.startswith('~$') or base.startswith('.'):   # 跳过 Word/编辑器临时文件
            continue
        out.append({...})
    # 默认项固定排第一，其余按名字稳定排序
    out.sort(key=lambda t: (0 if t['key'] == _DEFAULT_KEY else 1, t['key']))
    return out

TEMPLATES = _scan()
TEMPLATE = TEMPLATES[0]['file'] if TEMPLATES else None
```

取用时的兜底也**不要**用"扫到的第一份"当默认：

```python
def _by_key(key):
    k = (key or '').strip()
    for t in TEMPLATES:
        if t['key'] == k or os.path.basename(t['file']) == k:
            return t
    return TEMPLATES[0] if TEMPLATES else None     # 这里的第一份 = 写死的默认项
```

**判断标准**：把目录里的文件顺序打乱（手工改名 / 用 shutil 反序），程序行为是否完全不变？
是 → 合格。否 → 还有隐藏的"靠顺序"。

> 顺带一条：给资源加显示名/主题色这类映射表时，用 `{key: value}` + `dict.get(k, k)` 兜底，
> 别写成"if 文件名含'蓝' 就…"这类**靠字符串猜**的逻辑，新增一份又要改代码。

---

## 护栏 2：校验要**调用真正使用它的那段代码**，并按其真实返回结构取值

第一次写校验时我犯的错，值得原样记下来：

```python
# ✗ 错法一：朴素的字符串包含，和真正使用它的代码不等价
text = '\n'.join(p.text for p in Document(path).paragraphs)
for h in ('剧情简介', '影片评价', '放映信息'):
    if h not in text:            # 模板里其实是「放映·信息」（中间有间隔点）
        problems.append('缺少 %s' % h)
# → 两份**好**模板都被判成坏的（引擎自己会去掉间隔点再匹配）

# ✗ 错法二：用了引擎的函数，但键名凭印象写
loc = engine.locate_sections(Document(path))
if loc.get('plot') is None:      # 真实结构是 loc['headers']['plot']
    problems.append(...)         # → 又把好模板判成坏的

# ✓ 正确：调真函数 + 按真实返回结构取值
loc = engine.locate_sections(Document(path))
headers = loc.get('headers') or {}
for key, label in (('plot', '剧情简介'), ('review', '影片评价'), ('screening', '放映信息')):
    if headers.get(key) is None:
        problems.append('引擎定位不到槽位标题「%s」' % label)
for key, label in (('plot_img', '剧情简介图'), ('review_img', '影片评价图')):
    if loc.get(key) is None:
        problems.append('引擎定位不到槽位图片「%s」' % label)
```

为什么一定要这样：
- 校验的全部价值在于**回答"这份资源还能用吗"**。而"能用"的定义写在使用方代码里。
  自己另写一套"看起来等价"的判断，只会产出**假告警**（好资源被判坏、白折腾）或
  **假通过**（坏资源放过）。
- 先 `grep` 出真正的定位/解析函数，读它的**返回结构**再写断言；
  别凭函数名猜键名。**读一眼实现比改三遍断言便宜。**

配套做法：校验函数返回**问题列表**（空列表 = 通过），而不是 `bool`——
调用方要能把"哪里不行"直接打给人看。

---

## 护栏 3：**先构建到临时文件 → 校验通过 → 才改名上线**

第一版生成脚本是这样的：`os.replace(tmp, out)` 先上线，再 `verify(out)`。
结果：校验失败的那份文件**留在了目录里**，而下次运行时
"已存在 → skip" 的分支会把它当成正常产物跳过 → **坏资源一路流传，永远不会被重建**。

```python
tmp = out + '.tmp'
try:
    hits = build(source, tmp, color)
    problems = verify(tmp, color)
    if hits == 0 or problems:              # hits==0：没换到任何颜色 = 其实是原封不动的副本
        print('[FAIL] %s：替换 %d 处；%s' % (name, hits, '；'.join(problems) or '没换到任何东西'))
        failed += 1
        continue
    os.replace(tmp, out)                   # ← 只有全部通过才现身
finally:
    if os.path.exists(tmp):                # 失败路径也要清干净
        try: os.remove(tmp)
        except OSError: pass
```

并且——**已存在的产物同样要校验**，别无条件 skip：

```python
if os.path.exists(out) and not args.force:
    problems = verify(out, color)
    if problems:
        print('[WARN] %s 已存在但校验不过：%s（用 --force 重建）' % (name, '；'.join(problems)))
        failed += 1
    else:
        print('[skip] %s 已存在且校验通过' % name)
    continue
```

`hits == 0` 这类**退化信号要当失败**，不能当成功：
"换了 0 处颜色"说明源资源的结构变了，这份衍生文件其实是个毫无差异的副本。

---

## 交付前自检清单
1. 把资源目录的文件顺序反序/改名后，程序默认行为是否完全不变？（护栏 1）
2. 是否存在 `xxx[0]` / `next(...)` / `sorted(...)[0]` 这种"取第一份"当默认的写法？
3. 校验函数调的是**使用方的真函数**吗？返回结构是**读源码确认**的还是猜的？
4. 校验失败时产物会不会留在正式目录里？下次运行会不会被"已存在"跳过？
5. "什么都没改到"（hits==0 / 空 diff / 零命中）是当成功还是当失败？
6. 有没有一条测试专门锁"默认项是谁"？（我这次是靠 `test_generate_with_selected_template`
   里那句"未知 key 要回退默认"才逮到默认被换——**加完新资源后，第一件事就是断言默认没变**。）

---
name: stale-context-binding
description: 多实体内容生成系统里的「串台/串味」缺陷——生成出来的内容对应的是上一个实体（上一部电影/上一只股票/上一个客户），而不是当前输入的那个。适用于：用户说「XX 要结合我输入的 A，而不是上一个 B」「生成的内容跟输入对不上」；或代码里存在「抓来的资料/缓存/上下文」被多处复用的情形。含：三处必查的根因模式、收口式修法、以及零成本拿到「模型实际收到什么 prompt」的字节级验证 + 证伪方法。
agent_created: true
slug: stale-context-binding
displayName: 上下文串味护栏
version: 1.0.0
license: MIT
---

# stale-context-binding：别让上一个实体的资料串进这一篇

## 症状识别

用户描述通常是这几种之一：

- 「邀请语/简介/评价要结合我上面输入的电影，而不是上一个电影」
- 「改了个股代码，分析还是上一只」
- 「换了客户名，方案里还是上一个客户的业务」
- 更隐蔽的：**输出看起来很正常**，只是细节对不上输入（这种最难发现）

关键特征：**当前输入的标识是对的，但随它一起发出去的「参考资料」是旧的**。

---

## 第一步：先定位「资料从哪来、到哪去」

不要上来就改 prompt。先画出这条链：

1. **资料的生产点**：哪个函数/接口把外部数据抓回来？
2. **资料的存放点**：全局变量？模块级缓存？闭包？localStorage？
3. **资料的消费点**：**全部**发出去的地方（用 grep 数清楚，不要凭印象）。
4. **有没有「资料属于哪个实体」这个标记**。

```bash
# 找到所有消费点——这一步不能偷懒，漏一处就漏一个 bug
grep -n "lastMovieInfo\|<你的全局变量名>" static/index.html
```

---

## 三处必查的根因模式（按出现频率排序）

### 模式 1：资料容器「只写不清」，没有实体标识（最常见）

```js
let lastMovieInfo = {};              // 只在页面加载时初始化
async function fetchMovie(){ ... lastMovieInfo = {...}; }   // 唯一写入
// 全文搜不到任何 lastMovieInfo = {} / delete 的清空逻辑
```

片名一改，里面还是上一个实体的资料 → 后续所有生成都串台。

**判断方法**：搜这个变量的**所有写入点**。如果写入点只有「抓取成功」那一处、
且没有伴随「实体标识变更」的失效逻辑，基本就是它。

### 模式 2：prompt 里根本没带当前实体（静默失能）

```python
'invite': f'为校园影院常规放映写一句邀请语'      # ← 连片名都没有
```

这种 prompt **结构上不可能**贴合任何实体，输出必然是「放之四海皆准」的万能句。
用户感知为「没结合我输入的东西」。

**判断方法**：逐个检查 prompt 模板里有没有 `{m}`/`{code}`/`{name}`。
特别注意：**注释里的设计意图可能被实现反了**——原意是「别复述片名」（避免与标题重复），
实现成了「不知道是哪部片」。这两件事完全不同。

### 模式 3：守卫/自检是「休眠」的（最隐蔽，必须专门找）

```python
mv = (ctx.get('movie') or '').strip()          # ctx 从来没人往里写 movie
if mv and mv not in text:
    score -= 8                                  # ← 永远不执行
    reasons.append('未提及本片片名（疑似串台/跑题）')
```

一条**看起来在工作、实际从未触发过**的检查。它会让人误以为「有兜底」，从而不再人工检查。

**判断方法**（必做）：
1. 找出所有「自检/校验/守卫」逻辑；
2. 对每个判据，**回溯它的输入字段是从哪来的**；
3. 如果那个字段在所有写入点都没被赋值过 → 它就是休眠守卫。
4. 顺便审视判据本身是否成立：「没提到片名」≠ 串台（评价类文案的规则往往还**要求**别复述）。

---

## 第二步：修（收口，不要逐处打补丁）

### 前端：把「资料」和「实体标识」绑在一起，并只留一个取用口

```js
let lastMovieInfo = {};   // 必须带 for_movie：这份资料是为哪部片抓的

// ★ 唯一取用口。所有生成接口都必须走这里，
//   禁止再出现 Object.assign({}, lastMovieInfo) 这种裸读。
function ctxFor(movie){
  const m = (movie === undefined || movie === null)
    ? $('movie').value.trim() : String(movie).trim();
  if (!lastMovieInfo || !lastMovieInfo.for_movie || lastMovieInfo.for_movie !== m) return {};
  return Object.assign({}, lastMovieInfo);
}
```

要点：
- **加一个实体标识字段**，在写入点一并写入（`for_movie: 抓取时用的名字`）。
  ⚠ 用**用户输入框里的名字**，不要用后端解析出的正式名——两者可能不一致，
  用了正式名反而会被判成「过期」。
- **收口到一个函数**，然后把所有调用点改过去。这样无论从哪条路径走都不可能再串台。
- **刻意不清空**旧资料：保留才能告诉用户「手里那份属于《X》」。静默清空信息量更低。

### 界面：如实显示资料状态（不静默）

```js
function updateMovieInfoStatus(){
  const cur = $('movie').value.trim(), info = lastMovieInfo || {};
  if (info.for_movie && info.for_movie === cur && info.summary) {  // 就绪
  } else if (info.for_movie && info.for_movie !== cur) {          // 过期：明说属于谁
  } else {                                                        // 还没抓
  }
}
```

挂到：实体输入框的 `input` 事件、`change` 事件、**以及任何程序化改动的函数**（如「填入示例」）。
程序化赋值**不会**触发 `change` 事件——这是常见漏点。

### 后端：纵深防御 + 如实回报

```python
def _norm_movie(s):
    return re.sub(r'[\s《》]', '', str(s or ''))

def _sanitize_ctx(movie, ctx):
    """归属不符则整体丢弃；恒把当前实体名钉进 ctx（让自检有据）。
    返回 (干净的 ctx, 中文提示；无问题时为空串)。"""
    ctx = dict(ctx or {})
    src = str(ctx.pop('for_movie', '') or '').strip()
    if src and _norm_movie(src) != _norm_movie(movie):
        return {}, ('ℹ️ 已忽略参考资料：它属于《%s》，不是当前的《%s》'
                    % (src, movie or '未填'))
    if movie:
        ctx['movie'] = str(movie).strip().strip('《》')
    return ctx, ''
```

- **接入所有分支**（普通/流式/多风格/局部重写/推荐），不要只修主路径。
- **响应里新增独立字段**（如 `ctx_note`）而不是只塞进 note 字符串——
  前端才能精确识别并显示，而不是靠关键词匹配。
- **绝不静默丢弃**：丢弃必须随响应回传、并在界面上显示出来。

### 把休眠守卫改成「真判据」

不要只是把它「激活」（激活一个弱判据会引入误报）。换成直接针对病症的判据：

```python
# 旧：文本必须提到本片片名 → 会误伤合格稿（评价类规则还要求别复述）
# 新：正文里出现**别的**实体名才算串台；系列名不算
mv = _norm_movie(ctx.get('movie') or '')
if mv:
    for _t in re.findall(r'《([^》]{1,40})》', text):
        _nt = _norm_movie(_t)
        if _nt and _nt != mv and _nt not in mv and mv not in _nt:
            score -= 8
            reasons.append('正文出现其他片名《%s》（疑似串台）' % _t.strip())
            break
```

原则：**没有参照物时不敢乱判**（`mv` 为空就不报），宁可漏报也不误伤。

---

## 第三步：验证——零成本拿到「模型实际收到什么」

**不要只看输出像不像**。最快最硬的证据是截获发给模型的 prompt。
起一个本地假 LLM，把 app 的 `base_url` 指向它即可（**不消耗任何真实积分**）。

```python
# fake_llm.py 核心
def _reply_content(user_text):
    """⚠ 夹具文案必须**刻意不含**被测 ctx 的任何词汇。
    因为重写反馈/去重提示会把「上一版稿子」原样回灌给模型，
    夹具自己编的文本若带这些词，会污染「资料有没有泄漏」的判定 → 假阳性。"""
    ...

def do_POST(self):
    body = json.loads(raw)
    user_text = 最后一次 role=='user' 的 content
    open(OUT, 'a', encoding='utf-8').write(json.dumps(
        {'system': ..., 'user': user_text}, ensure_ascii=False) + '\n')
    # 回一段能过字数门槛的文案，让链路跑到最后
```

用**独立配置**起第二个实例，绝不碰用户的真实配置：

```bash
NEWSLETTER_CONFIG_PATH=/tmp/tmp_cfg.json \
no_proxy="127.0.0.1,localhost" http_proxy= https_proxy= \
python -c "from app import app; app.run(port=5099, use_reloader=False)"
```

### 检查设计的三个陷阱（都踩过）

1. **判据别用常见词**。拿 `'动作'` 当泄漏判据 → 命中项目自己的通用措辞
   「画面/**动作**/表演/声音描写」，永远通不过。**判据只用该 ctx 独有的 token**
   （人名、独有短语、`类型：剧情/动作` 这种带上下文的组合）。
2. **区分「首次 prompt」和「回灌 prompt」**。重写反馈会引用上一版稿子
   （`你上一版的稿子如下`）、去重会引用同批其他结果（`其他风格`·`高度雷同`）。
   这些**天然包含**上一版文本，属于正常行为。
3. **必须有对照场景**：实体一致时，资料**应该**被采纳。
   只测「不泄漏」的话，一个「永远丢弃 ctx」的实现也能全绿。

### 必做：证伪

一个「一直通过」的检查没有价值。把**未清洗**的资料直接喂给 prompt 构造函数
（＝修复前的行为），确认判据**能抓到**：

```python
_, u_old = build_block_prompt('plot', '流浪地球3', 3, OLD_CTX, {...})
assert leaks(u_old), '判据抓不到泄漏 → 说明 LIVE 检查是空转的'
clean, note = _sanitize_ctx('流浪地球3', OLD_CTX)
_, u_new = build_block_prompt('plot', '流浪地球3', 3, clean, {...})
assert not leaks(u_new)
```

实测：未清洗 → 7 个泄漏词全部命中；清洗后 → 0 命中。

### 前端护栏（防回退）

用静态检查锁死「禁止裸读全局资料」，但要排除注释和取用口自身的实现：

```python
code = '\n'.join(l for l in html.splitlines() if not l.strip().startswith('//'))
body = re.search(r'function ctxFor\(movie\)\{(.*?)\n\}', code, re.S)
rest = code.replace(body.group(0), '')          # 排除取用口自身
assert not re.findall(r'Object\.assign\(\{\}\s*,\s*lastMovieInfo\s*\)', rest)
```

---

## 环境坑（Windows / 沙箱）

- `http_proxy=http://127.0.0.1:xxxx` 会拦本地回环 →
  客户端 `urllib.request.build_opener(urllib.request.ProxyHandler({}))`；
  服务端 `no_proxy=127.0.0.1,localhost` 且 `http_proxy=` 清空。否则拿到 **502**。
- 后台服务必须用**后台任务方式**启动（`run_in_background: true`）；
  普通 `&` 会随该次工具调用结束被回收，下一次调用就连不上。
- 中文 JSON 用 `--data-binary @file.json` 或 Python 的 `urllib`；
  `curl -d` 会破坏中文。
- 收尾核对：用户真实配置文件 **sha256 未变**、临时配置/端口已清理、正式服务已用新代码重启。

---

## 检查清单

- [ ] 数清「资料容器」的**全部**消费点（grep，不许凭印象）
- [ ] 资料容器有实体标识字段（`for_xxx`）
- [ ] 所有消费点走同一个取用口，零裸读
- [ ] 实体输入的 `input`/`change`/程序化改动 三处都刷新状态显示
- [ ] 界面如实显示「就绪 / 已过期（属于《X》）/ 未抓取」，不静默
- [ ] 后端每个分支都过归属校验，丢弃时随响应回传提示
- [ ] prompt 模板里确实带了当前实体名（别让注释意图与实现相反）
- [ ] 检查所有「自检/守卫」是否休眠（输入字段有无人赋值）
- [ ] 弱判据（没提到名字）升级为真判据，且**没有参照物时不报**
- [ ] 假 LLM 夹具文案不含被测 ctx 词汇
- [ ] 有对照场景（实体一致时资料应被采纳）
- [ ] 做了**证伪**：未清洗必被抓到
- [ ] 前端静态护栏生效，且排除注释与取用口自身
- [ ] 真实配置 sha256 未变

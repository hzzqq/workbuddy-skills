---
name: 事件因子
displayName: 事件因子·A股信号
slug: event-factor
version: 1.0.1
description: "事件因子查询：调用 StockSignal modules.event_factor，从 P1-QuantFactor EV 模型与东方财富新闻情感取真实信号，判断个股看多/看空与百分位。取不到即 available=False，绝不编造或默认 0；支持单标查询与事件驱动看多榜。"
agent_created: true
---

# 事件因子（个股 · 事件/regime 信号）

## 这个 skill 解决什么
老板的 StockSignal 项目需要一个「事件因子适配器」把量化特征对接到**真实信号源**，而不是合成演示数据。
`modules/event_factor.py` 就是这个适配器：

- **主源**：P1-QuantFactor 的 EV 模型信号（在 38 维量价特征上并入「牧羊人市场广度情绪」9 维作为事件 / regime 通道，共 47 维），是一个已落地的真实事件因子。
- **兜底源**：真实东方财富新闻情感（`news_event_signal`），逐标的真实事件面，互不替代、绝不造数。

设计纪律与项目红线一致：**取不到就 `available=False` 并说明原因，绝不返回合成 / 随机值**。

## 何时用
- 用户问"这只票有没有事件因子信号""这标的是看多还是看空""事件驱动看多榜有哪些票"。
- 用户在跑策略 / 写研报，需要把"事件因子"作为一条可解释、有真实来源的特征。

## 用法（让 AI 执行命令，不要自己编数字）
通过命令行调用自带脚本（自带 Python 即可，无需额外依赖）：

```bash
# 1) 查询单标的事件因子（默认模型 ev）
python <skill目录>/scripts/query_event_factor.py symbol 600519
python <skill目录>/scripts/query_event_factor.py symbol 300750 --model ev

# 2) 取事件驱动看多榜（按真实事件因子排序的多头候选池）
python <skill目录>/scripts/query_event_factor.py longlist --top-n 20
```

- 脚本通过 `STOCKSIGNAL_ROOT` 环境变量（默认 `E:/project/ks/StockSignal`）定位 StockSignal 仓库，
  动态导入 `modules.event_factor`（**单一真理源**）；仓库不在则诚实报错而非编造。
- 若 P1 信号未更新（最新有效日停在 2026-08-14 属已知状态），`get_event_factor` 会返回 `available=False`
  并给出原因——这是预期行为，请如实告知用户，不要伪装成有信号。

## 输出与诚实口径（务必照实呈现给用户）
`get_event_factor` 返回结构：
- **有数据**：`{"available": True, "symbol", "score", "signal": "看多"|"看空", "rank", "date", "source"}`
- **无数据**：`{"available": False, "symbol", "reason": "..."}`（如"该标的无 P1 事件因子信号"）

`event_driven_long_list` 返回列表，每项 `{"symbol", "score"(0-100 百分位), "raw_rank", "raw_pred", "signal":"看多", "source"}`；
取不到真实信号优雅返回 `[]`，调用方应展示"无信号"提示而**不应报错或填充假值**。

## 能力边界（写进产品/回答，不藏）
- ✅ 可信：基于 P1 EV 模型（47 维，含牧羊人情绪事件通道）的真实 ranked 信号与新闻情感兜底。
- ❌ 不可信 / 不可用：P1 信号停更期间、标的不在池内、数据源异常——一律 `available=False`，不硬猜。
- ⚠️ 信号来源单日有效日可能滞后（截至 2026-08-14），使用前确认数据新鲜度，陈旧信号须如实标注。

## 红线
- **绝不外推到无依据的结论**，取不到就说取不到，不要为了显得有用而编造方向或分数。
- 不读密钥、不联网外呼、不写用户文件、不删文件。
- 若返回 `available=False`，措辞必须保留"暂无真实信号 / 数据不足"。

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：数据取不到怎么办？→ 严守诚实口径，取不到即返回 available=False / None，绝不编造或默认 0。
- **反模式**：不要期望它在样本不足时给 actionable 信号；超出能力边界时它会诚实降级，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。

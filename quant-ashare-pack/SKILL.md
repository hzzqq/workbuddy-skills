---
slug: quant-ashare-pack
name: A股期货量化全家桶
displayName: A股期货量化全家桶
version: 1.0.0
license: MIT
category: quant
description: |
  把本机散落的 A股/期货/港股数据、选股、回测、监控、事件、情绪类 skill 收敛成一个量化工作台入口。
tags: [组合包, bundle, quant]
---

# A股期货量化全家桶

> 这是一个**组合 skill（bundle）**：把一组同类 skill 收敛成一个入口，便于记忆、调用与**跨账号一键导入**。
> 原 skill 全部保留，本 skill 只做「总结 + 路由 + 一键安装」。

## 这个组合解决什么
本机量化类 skill 多达 25+ 且高度重叠（如 westock-data 两份、quant-backtest-strategy 两份、stock-monitor 两份重复）。本包把它们收敛成一个入口，按需取用，避免重复启用互相打架。

## 包含的成员（23 个）
| 成员 | 类型 | 说明 | 跨账号安装 |
| --- | --- | --- | --- |
| A股每日复盘 | local | >- | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| A股全栈数据 | local | A股全栈数据工具包 — 覆盖行情(mootdx+腾讯+百度K线)、研报(东财+同花顺+iwencai)、信号(同花顺热点+北向+龙虎榜+解禁 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| onequant-backtest | local | OneQuant 4.0 量化交易系统 — A股本地量化平台，Windows/macOS/Linux全平台支持(Docker)。5种调用方式 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| akshare-stock | local | A股量化数据分析工具，基于AkShare库获取A股行情、财务数据、板块信息等。用于回答关于A股股票查询、行情数据、财务分析、选股等问题。 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| A股短线交易 | local | A 股日内与短线决策辅助工具，覆盖盘后诊断、标的初筛、盘中节点评估、单标的因子分析四个环节。 支持从交割单回溯每笔交易的买卖质量并输出结构化 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 中国金融机构数据爬取与分析 | local | 中国金融机构数据爬取与分析综合 Skill v10.0.0。2334家/43大类机构名单、60+财经媒体源舆情、 A股报告/公告/研报、60 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 每日财经新闻 | local | >- | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| hk-quant-advisor | local | 港股专业量化交易决策顾问 v1.0.2。模拟"交易员 + 风控官 + 绩效分析师"三重角色，基于多维度实时数据，运行精确量化策略，为港股账户 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 投资财经日历 | local | 财经事件日历技能。查询CPI/PPI/GDP/PMI/非农/PCE等宏观数据发布时间、FOMC/MLF/LPR等央行决议、财报/IPO/解禁 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| onequant-backtest | local | OneQuant 4.0 量化交易系统 — A股本地量化平台。5种调用方式：①Web界面(浏览器点点点) ②REST API(Python/ | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| onequant-backtest | local | OneQuant 4.0 量化交易系统 — A股本地量化平台。5种调用方式：①Web界面(浏览器点点点) ②REST API(Python/ | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| quant-signal-landing-sop | local | 量化信号重训→落地生产的 SOP 与三大陷阱。当用户要重训/替换/集成 A股多因子预测信号（GRU/LightGBM/集成），或遇到「训练被 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| stock-evaluator-v3 | local | Comprehensive evaluation of potential stock investments combining valu | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| stock-monitor | local | 股票价格实时监控。支持多只股票监控，使用 Yahoo Finance API 获取实时股价，自定义涨跌阈值提醒。当股价波动超过设定阈值时自动 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| stock-monitor | local | 股票实时监测助手，A股盯盘利器，内置股票分析专家。 触发词：监测股票、股票提醒、实时盯盘、盯盘助手、帮我监测、帮我盯盘、 股票异动提醒、涨停 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| stock-selecter | local | 统一选股技能包，整合11种策略（ROE筛选、MACD底背离、高股息、低估值、 费雪成长股、长期低位、近期放量、趋势分析、K线形态、布林带下轨 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| ths-financial-data | local | 该skill用于获取股票市场数据，包括实时行情、中文名称查询、键盘缩写转换、资金流向和日K线数据。使用thsdk库提供同花顺数据接口支持。支 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| stock-catalyst-hunter | local | 当用户想知道一条新闻、传闻、政策变化、地缘事件、行业扰动或截图会对应哪些 A 股题材和股票时，使用这个 skill。它会识别事件、搜索中文财 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| westock-data | local | 金融市场结构化数据查询的权威入口。支持股票（A股/港股/美股）、ETF、指数、板块、期货、外汇、可转债的 K 线、技术指标、筹码、财报、研报 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| westock-data | local | 金融市场结构化数据查询的权威入口。支持股票（A股/港股/美股）、ETF、指数、板块、期货、外汇、可转债的 K 线、技术指标、筹码、财报、研报 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 全球智能投研 | local | 全球智能投研工具 v11.0 — 多源数据强化 + AI 期货/资金流/指数/组合深度分析 + 金融六日 MCP 桥接。 叠加 v10.0  | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| 牧羊人指标 | local | 股票（A股）类型的情绪指标技能：把「牧羊人情绪指标」做成判断次日（第二天）行情方向的工具。 输入当日市场广度（上涨/下跌/平盘家数、跌停/触 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |
| futures-combo | local | 商品期货组合分析专家 —— 专为老板的 6 个实盘品种（玻璃FG / 纸浆SP / 纯碱SA / 鸡蛋JD / 白糖SR / 乙二醇EG）定 | 本地自研：从 skills-for-cloud 镜像拷贝 / 推 GitHub 后复制 |

## 推荐工作流
1) 数据权威入口优先 westock-data（含期货/外汇）；个股深度用 akshare-stock / a-stock-data；
2) 择时/事件用 ticai-lieshou（催化猎手）+ 牧羊人指标（情绪）；
3) 选股/短线用 stock-selecter / ashare-short-term-trading；
4) 回测/信号落地用 quant-backtest-strategy（OneQuant）与 quant-signal-landing-sop；
5) 每日复盘 daily-financial-news + a-share-daily-review + invest-calendar 排程；
6) 港股用 hk-quant-advisor，期货组合用 futures-combo；
7) 自研 event_factor / macro_data 作为事件因子与宏观数据适配器。

## 一键导入 / 跨账号安装
本目录附带 `install_bundle.py`，在新账号机器上运行即可把成员补齐：

```bash
python install_bundle.py            # 默认装到 ~/.workbuddy/skills
python install_bundle.py --mirror "E:/project/skill/skills-for-cloud"   # 指定本机自研镜像根
```

- **SkillHub 成员**：自动用 `skillhub install` 拉取（匿名即可，无需登录）。
- **本地自研成员**：优先从 `--mirror` 指定的 skills-for-cloud 镜像拷贝；若镜像里没有，脚本会打印提示，
  需要你先把这些自研 skill 推到 GitHub 发布库（workbuddy-skills）或放进 skills-for-cloud 镜像。

## 发布 / 分享
本组合 skill 自带完整 frontmatter（slug / version / displayName），可直接：
- 用 `skillhub publish <本目录>` 发布到社区；或
- 拷进 GitHub 发布库（workbuddy-skills）的子目录，从 GitHub 导入。

## 维护约定
- 新增/剔除成员：编辑本目录的 `manifest.json` 后重跑生成脚本，或手动同步 SKILL.md 成员表。
- 非破坏式：绝不删除被组合的原始 skill。

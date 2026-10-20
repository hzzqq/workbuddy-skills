---
name: wechat-bridge
description: 企业微信自建应用桥接 — 让 WorkBuddy 把任务进度/结果推送到老板微信，并支持老板在微信里发指令反向操控（手机远程操作 AI 任务）。适用于「微信推送」「微信远程操控」「手机控制 WorkBuddy」等需求。
slug: wechat-bridge
version: 1.0.0
displayName: wechat-bridge
---

# wechat-bridge — 企业微信桥接（推送 + 反向操控）

把 WorkBuddy 的产出推到老板微信，并让老板在微信里发文字指令（如「启动 big_game 迭代」「查进度」「修那个 bug」）反向触发 AI 执行。

## 0. 通道选择（先看这个）
| 通道 | 推到 | 收（反向指令） | 配置难度 | 本机网络实测 |
|---|---|---|---|---|
| 企业微信自建应用 | 企业微信应用 | ✅（需 cloudflared 隧道） | 高（个人主体受「可信域名」备案 + 「可信IP」前置限制） | ❌ 受限：可信IP前置需可信域名(备案)或接收URL(公网)；cloudflared 二进制常被校园网掐断 |
| PushPlus | 个人微信（关注公众号） | ❌ 仅推送 | 低（扫码拿 token） | ✅ 网络可通，但平台已加**实名/会员**前置门槛 |
| **Server酱（方糖）** | 个人微信（关注「方糖」公众号） | ❌ 仅推送 | **最低（扫码即拿 SendKey）** | ✅ 无实名、无备案、无公网 |

**推荐起步用 Server酱**：微信扫码关注「方糖」→ 官网 `sc.ftqq.com` 拿 SendKey（30 秒），填入配置即可推你个人微信。无实名/备案/公网任何门槛。

切换方式：`config.json` 设 `"channel": "serverchan"` + `"serverchan_sendkey": "<SendKey>"`；PushPlus 设 `"channel": "pushplus"` + `"pushplus_token": "<token>"`；企业微信设 `"channel": "wecom_app"`。

## 为什么选企业微信自建应用
- 免费、学生可用**个人身份**注册企业（填姓名+身份证即可，无需营业执照）。
- 唯一能**同时推+收**的干净方案：应用消息可推给老板；老板在应用里发的消息经回调回到本地。
- 个人微信无官方 API（第三方协议封号风险），公众号需认证付费+公网服务器，均不推荐。

## 架构
```
老板微信 ──发消息──▶ 企业微信服务器 ──回调 POST──▶ cloudflared 隧道 ──▶ 本地 serve(:8800)/wechat ──▶ inbox.jsonl
老板微信 ◀─应用消息── 企业微信服务器 ◀── push() ── WorkBuddy(自动化/AI)
```
- WorkBuddy 沙箱**不暴露公网**，故反向接收必须靠 **cloudflared 免费隧道**把本地 `:8800` 暴露到公网，企业微信「接收消息」回调填隧道 URL。
- 推送方向不需要公网，配置好 corpid/secret 即可。

## 一、老板需完成的 4 步（一次性）
1. **注册企业微信**：work.weixin.qq.com → 用个人身份创建企业（填姓名/身份证）。
2. **建自建应用并拿 4 个推送凭证**（corpid / agentid / corpsecret / touser）：
   - 「应用管理」→「自建」→「创建应用」（名字随意，如「WorkBuddy 遥控」）。
   - 进入应用详情页：
     - **AgentId（=agentid）**：页面直接显示的数字，记下。
     - **Secret（=corpsecret）**：点右侧「查看」→ 企业微信客户端会收到一条含 Secret 的消息 → 复制（新版不在网页明文显示）。
   - **corpid（企业ID）**：左侧「我的企业」→「企业信息」→ 页面最下方「企业ID」→ 显示并复制（格式 `ww` 开头）。
   - **touser（UserId）**：左侧「通讯录」→ 点你自己的名字 → 详情里「账号」字段那串就是 UserId。
3. **装 cloudflared 并拿 2 个反向凭证**（token / aeskey，仅反向需要）：
   - 下载 https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ 安装。
   - 管理员 PowerShell 起隧道：`cloudflared tunnel --url http://localhost:8800` → 记下给的 `https://xxxx.trycloudflare.com` 公网地址。
   - 「应用管理」→「自建」→ 应用 →「接收消息」→「设置API接收」：
     - **URL** 填 `https://xxxx.trycloudflare.com/wechat`
     - **Token**、**EncodingAESKey（=aeskey，43位）** 各点「随机获取」→ 复制。
     - **保存**（保存时企业微信会向 URL 发验证，所以**必须先让 cloudflared 隧道可访问**再保存）。
4. **把 6 个值给 AI**：corpid、corpsecret、agentid、touser、token、aeskey → AI 写入 `~/.workbuddy/wechat_bridge/config.json`（不入 git）。

## 二、配置文件
`~/.workbuddy/wechat_bridge/config.json`：
```json
{
  "corpid": "wwxxxxxxxxxxxxxxxx",
  "corpsecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "agentid": 1000002,
  "touser": "boss",
  "token": "xxxxxx",
  "aeskey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "channel": "serverchan",
  "pushplus_token": "",
  "serverchan_sendkey": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```
- `channel`：`serverchan`（推荐，推个人微信）/`pushplus`（推个人微信）/`wecom_app`（企业微信应用消息）。
- `pushplus_token`：PushPlus 官网（pushplus.plus）登录后「一对多消息」或「一对一」页面复制的 token。⚠️ 平台已加实名/会员前置门槛，不推荐。
- `serverchan_sendkey`：Server酱（sc.ftqq.com）「发送消息」页面复制的 SendKey。推荐，无实名。

### Server酱 SendKey 获取（30 秒）
1. 微信扫码关注公众号「方糖」。
2. 浏览器打开 https://sc.ftqq.com → 用微信登录 → 左侧「发送消息」页面复制 **SendKey**。
3. 把 SendKey 给 AI 写入 config.json 的 `serverchan_sendkey`，并把 `channel` 设为 `serverchan`。

### PushPlus token 获取（2 分钟，已不推荐）
1. 浏览器打开 https://www.pushplus.plus → 微信扫码登录。
2. 左侧「一对多消息」或「一对一消息」→ 复制页面上的 **Token**。
3. 微信关注「PushPlus 推送加」公众号（否则收不到）。
4. 把 token 给 AI 写入 config.json 的 `pushplus_token`。⚠️ 当前平台强制实名/会员前置，建议改用 Server酱。

## 三、用法
```bash
# 推送一条文本到老板微信
python wechat_bridge.py push "dev-supervisor 进度：big_game 40% / raft-kv 32%"

# 自检（发一条测试推送）
python wechat_bridge.py test

# 启动接收端点（需 cloudflared 隧道已起，企业微信回调已配）
python wechat_bridge.py serve 8800
```
- 接收的指令落入 `~/.workbuddy/wechat_bridge/inbox.jsonl`，由 AI 定时轮询解析执行。
- 若仅需推送、暂不反向，跳过步骤 3 和 serve。

## 四、与 dev-supervisor / 其他自动化集成
在自动化 prompt 末尾加一步：运行 bar 模式后，把报告文本通过 `wechat_bridge.py push "<报告>"` 推给老板。配置缺失时自动降级为仅 stdout 并提示。

## 额度与频率（重要）
- **Server酱 Turbo（SCT 开头 key）免费额度：每天仅 5 条**；订阅会员（8 元/月起）1000 条/天、每分钟≤50 条。
- 因此 dev-supervisor 推送频率设为 **每 12 小时 1 次（约 2 条/天）**，并留余量给其他通知/手动推送。
- 脚本内置每日计数保护：`push_count.json` 记录当天已发条数；`serverchan_daily_limit`（默认 4）为脚本每天最多发条数，达上限自动降级为 stdout（不实际发送），避免刷爆 5 条硬上限。
- 提频/提额：升级 Server酱 订阅（改 config 不动代码）；或调高 `serverchan_daily_limit`（仍受 5 条/天硬上限约束）。

## 护栏
- config.json 含 secret，**绝不提交 git / 不外传**。
- 纯桥接，不替老板做任何未授权动作；老板微信指令解析后只执行明确的安全操作（启动已配置的迭代、查进度、读日志），涉及破坏性操作（删文件、force push）一律二次确认。
- 若企业微信 API 域名 `qyapi.weixin.qq.com` 在沙箱被屏蔽，需在 WorkBuddy 沙箱配置域名白名单。

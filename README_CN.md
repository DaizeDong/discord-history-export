# discord-history-export

把整个 Discord 服务器（每个频道、每个 thread）导出到本地 HTML（给你看）和 JSON（给分析用），5 to 10 分钟跑完。

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![基于 DiscordChatExporter](https://img.shields.io/badge/%E5%9F%BA%E4%BA%8E-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![语言](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-EN%20%2F%20CN-blue?style=flat)](#语言)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

---

## ⭐ 先读这个, 设计理念

导出工具（Tyrrrz/DiscordChatExporter）本身已经存在且很优秀。那为什么还要做一个 skill？

因为对一个真实的多频道 Windows 服务器来说，朴素的 CLI 调用有五个非显然的失败方式，而每个失败看起来都像 bug，而不是配置问题。这个 skill 的价值不在于"它调了个工具",而在于**它把那个工具悄悄做错事的每一种方式都固化成了复盘**，再加上两件手动做起来确实很烦的事：

- **不用 DevTools 拿 token。** 正常拿 Discord user token 要打开 DevTools、找一个请求、复制粘贴 `Authorization` header。这个 skill 用 Playwright MCP 开一个有界面的浏览器：你只登录一次、可视化选服务器，它替你抓 token 和 guild ID。
- **真正能读的产物。** DCE 默认输出是一堆 18 位 Discord ID 文件夹。这个 skill 把它重组成 `<分类>/<频道>.html`，双击就能看。

它还**默认对风险诚实**。Discord 服务条款禁止自动化用户账号。skill 会在抓任何 token *之前* 用一句话讲清这点，给管理员提供合规的 Bot 路径，并在结尾提醒你改密码,因为你的 token 出现在了对话记录里。理念是：把又难又繁的部分替用户做掉，但绝不隐藏权衡。

## 定位与边界

**它是** 一个一次性归档工具：指向一个你已加入的服务器，拿回一份完整、可读的 HTML 镜像，外加一份结构平行的 JSON 数据集供分析，按 category / channel 归组，thread 放在子目录里。

**它不是** 持续同步、不是 Discord bot、不是监控工具、也不是读取你本来读不到的服务器的办法。它只导出你自己账号本来就能看到的内容，一次。遇到 Group DM 会直接中止，指给你 Discord 官方的 GDPR "请求我的数据" 导出。

## 安装

```
/plugin install github:DaizeDong/discord-history-export
```

或手动 clone 到 Claude 插件目录：

```bash
git clone https://github.com/DaizeDong/discord-history-export.git \
  ~/.claude/plugins/discord-history-export
```

技能会在以下短语出现时自动触发：`export discord history`、`download my discord server`、`archive discord chat`、`导出 discord 群组`、`拉 discord 频道历史` 等。

## 60 秒概览

你说：

```
帮我导出我加入的那个 Discord 服务器全部历史
```

自动执行的流程：

1. 确认范围（整个服务器 / 单频道 / Group DM）并用一句话提示 Discord ToS 风险
2. 下载最新的 [Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) CLI（self-contained，不需要装 .NET）
3. 用 Playwright MCP 打开有界面的浏览器, **你只登录一次**，切到目标频道，回一句"好了"
4. 自动抓取你的 **user token**（iframe localStorage 绕过 Discord 的清除机制）和 **guild ID**（URL 第二段），不需要打开 DevTools 也不需要你复制粘贴
5. 用 `exportguild` + `--include-threads All` + 防撞名的文件名模板做全量导出
6. 跑 Python 重组脚本：把 DCE 默认输出的"一堆 Discord ID 文件夹"翻译成可读的 `<分类>/<频道>.html` + `<分类>/<频道>_threads/` 树
7. 汇报总消息数、热门频道、被 Discord 拒访的频道、forum 频道的特殊结构
8. 提醒你：**立即改一次 Discord 密码** 作废刚刚出现在对话里的 token

几十个频道、数万条消息规模下，端到端跑完约 5 to 10 分钟；产出约 100 MB 级别的 HTML，外加体量相当的 JSON。

## 如何触发

直接描述意图即可, skill 会在以下触发词出现时自动激活：

- `export discord history`
- `download my discord server`
- `archive discord chat`
- `save my discord messages`
- `导出 discord 群组` / `拉 discord 频道历史` / `discord 历史归档`

你也可以不用 skill，直接调 [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter)：

```bash
# 1. 在 Discord 浏览器 DevTools → Network → 任意 /api 请求 → Authorization header 取 token
# 2. URL 第二段就是 guild ID: discord.com/channels/<GUILD_ID>/<channel_id>

DCE_EXE="path/to/DiscordChatExporter.Cli.exe"

# 列频道（顺便检查权限 + 给重组脚本用）
"$DCE_EXE" channels -t "$TOKEN" -g "$GUILD_ID" > channels.txt

# 全量导出
"$DCE_EXE" exportguild \
  -t "$TOKEN" \
  -g "$GUILD_ID" \
  -f HtmlDark \
  --include-threads All \
  --parallel 4 \
  -o "exports/all/%t/%C [%c].html"

# 重组成可读结构
python skills/discord-history-export/scripts/reorganize.py \
  exports/all exports/organized channels.txt
```

## 示例输出

```
exports/
├── organized/                  ← HTML，双击任意文件即可浏览器查看
│   ├── INDEX.md                ← 目录映射 + 文件/消息计数
│   ├── General/
│   │   ├── general.html
│   │   ├── help-forum_threads/  ← forum 频道：只有 threads
│   │   └── ...
│   ├── Discussion/
│   │   ├── channel-1.html
│   │   ├── channel-1_threads/
│   │   └── ...
│   └── ...
├── organized_json/             ← 同样结构的 JSON 版，给分析用
├── all/, all_json/             ← DCE 的原始输出（按 Discord ID 命名）
└── channels.txt                ← 服务器频道列表（重组脚本会用）
```

### 为什么这事不是直接调 CLI 完事

对一个多频道的 Windows 用户来说，DCE 的朴素调用有五个非显然的坑，每个都会让导出失败或产物不可用。这个 skill 把每个坑的修复都固化在流程里：

| 坑 | 表现 | skill 里的对策 |
|---|---|---|
| `%t` 不是 category 名 | 输出文件夹全是 18 位 Discord ID | `scripts/reorganize.py` 做 ID → 名映射 |
| 同名 thread | 整个导出在中途因 Windows `FileShare` 锁崩溃 | 文件名模板永远带 `[%c]` |
| Git Bash `/c/...` 路径 | 70 MB 静默写到 `C:\c\Users\...` 错误位置 | 一律传 Windows 风格 `C:/...` |
| Forum 频道看起来"空" | `help-forum.html` 之类的找不到 | 在汇报里说明这是 Forum 频道，内容在 threads/ 子目录里 |
| 无权限频道 | 中途报错像是崩了 | 收尾汇报里专门列出来，不当失败 |

完整复盘见 `skills/discord-history-export/SKILL.md` 的 "Gotchas Encountered" 一节。

## 限制

**ToS 风险提示。** Discord 服务条款禁止自动化"用户账号"操作（俗称 self-bot），即使是你手动也能做的动作。这个 skill 走的是"一页消息一个 HTTP 请求"的低速节奏，DCE 内置了 rate-limit 处理；对一个普通账号做一次性导出，被封号的实际风险低但非零。在抓 token 之前 skill 会先把这点告诉用户，并主动给出官方替代路径：

- **你是服务器管理员**？请邀请一个 Bot（完全合规）。skill 会停下、把后续操作交给你。
- **目标是 Group DM**？skill 会直接中止，指给你 Discord 官方的 GDPR 数据导出入口：设置 → 隐私与安全 → **请求我的数据**。

**环境要求：**

- Windows / macOS / Linux（skill 默认 Windows x64，其他系统换一下 DCE 的 release 名即可）
- `git`、`python` (3.8+)、`curl`、`unzip`
- Claude Code 装了 Playwright MCP 插件（提供浏览器控制工具）
- 约 200 MB 空闲磁盘（DCE 二进制 + 每个服务器的导出）

**不需要装 .NET**, DCE 直接发布 self-contained 二进制。

## 语言

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · 更新日志 · License

见 [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [LICENSE](LICENSE)（MIT）。

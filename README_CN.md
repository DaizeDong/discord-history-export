# discord-history-export

一个 Claude Code skill —— 把你加入的任何一个 Discord 服务器的全部历史聊天（每个频道、每个 thread）导出到本地。HTML 给你看，JSON 给 LLM 做分析，按 category / channel 自动归组。

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DCE](https://img.shields.io/badge/Powered%20by-DiscordChatExporter-5865F2?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)

[English](README.md) | [中文版](README_CN.md)

---

## 安装

```
/plugin install github:DaizeDong/discord-history-export
```

或手动 clone 到 Claude 插件目录：

```bash
git clone https://github.com/DaizeDong/discord-history-export.git \
  ~/.claude/plugins/discord-history-export
```

技能会在以下短语出现时自动触发：`export discord history`、`download my discord server`、`archive discord chat`、`导出 discord 群组`、`拉 discord 频道历史`、`discord 历史归档`、`save my discord messages` 等。

---

## 60 秒概览

你说：

```
帮我导出我加入的那个 Discord 服务器全部历史
```

自动执行的流程：

1. 确认范围（整个服务器 / 单频道 / Group DM）并用一句话提示 Discord ToS 风险
2. 下载最新的 [Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) CLI（self-contained，不需要装 .NET）
3. 用 Playwright MCP 打开有界面的浏览器 —— **你只登录一次**，切到目标频道，回一句"好了"
4. 自动抓取你的 **user token**（iframe localStorage 绕过 Discord 的清除机制）和 **guild ID**（URL 第二段），不需要打开 DevTools 也不需要你复制粘贴
5. 用 `exportguild` + `--include-threads All` + 防撞名的文件名模板做全量导出
6. 跑 Python 重组脚本：把 DCE 默认输出的"一堆 Discord ID 文件夹"翻译成可读的 `<分类>/<频道>.html` + `<分类>/<频道>_threads/` 树
7. 汇报总消息数、热门频道、被 Discord 拒访的频道、forum 频道的特殊结构
8. 提醒你：**立即改一次 Discord 密码** 作废刚刚出现在对话里的 token

几十个频道、数万条消息规模下，端到端跑完约 5–10 分钟；产出约 100 MB 级别的 HTML，外加体量相当的 JSON。

---

## 输出结构

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

---

## 这个 skill 的存在意义（为什么不是直接调 CLI 完事）

对一个多频道的 Windows 用户来说，DCE 的朴素调用有五个非显然的坑，每个都会让导出失败或产物不可用。这个 skill 把每个坑的修复都固化在流程里：

| 坑 | 表现 | skill 里的对策 |
|---|---|---|
| `%t` 不是 category 名 | 输出文件夹全是 18 位 Discord ID | `scripts/reorganize.py` 做 ID → 名映射 |
| 同名 thread | 整个导出在中途因 Windows `FileShare` 锁崩溃 | 文件名模板永远带 `[%c]` |
| Git Bash `/c/...` 路径 | 70 MB 静默写到 `C:\c\Users\...` 错误位置 | 一律传 Windows 风格 `C:/...` |
| Forum 频道看起来"空" | `help-forum.html` 之类的找不到 | 在汇报里说明这是 Forum 频道，内容在 threads/ 子目录里 |
| 无权限频道 | 中途报错像是崩了 | 收尾汇报里专门列出来，不当失败 |

完整复盘见 `skills/discord-history-export/SKILL.md` 的 "Gotchas Encountered" 一节。

---

## ToS 风险提示

Discord 服务条款禁止自动化"用户账号"操作（俗称 self-bot），即使是你手动也能做的动作。这个 skill 走的是"一页消息一个 HTTP 请求"的低速节奏，DCE 内置了 rate-limit 处理；对一个普通账号做一次性导出，被封号的实际风险低但非零。在抓 token 之前 skill 会先把这点告诉用户，并主动给出官方替代路径：

- **你是服务器管理员**？请邀请一个 Bot（完全合规）。skill 会停下、把后续操作交给你。
- **目标是 Group DM**？skill 会直接中止，指给你 Discord 官方的 GDPR 数据导出入口：设置 → 隐私与安全 → **请求我的数据**。

---

## 环境要求

- Windows / macOS / Linux（skill 默认 Windows x64，其他系统换一下 DCE 的 release 名即可）
- `git`、`python` (3.8+)、`curl`、`unzip`
- Claude Code 装了 Playwright MCP 插件（提供浏览器控制工具）
- 约 200 MB 空闲磁盘（DCE 二进制 + 每个服务器的导出）

**不需要装 .NET** —— DCE 直接发布 self-contained 二进制。

---

## 不用 skill 手动跑

如果你想自己直接调用 DCE：

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

---

## License

MIT —— 见 `LICENSE`。

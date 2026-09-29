# discord-history-export

把获授权的 Discord 历史导出为经过校验的 HTML 和 JSON，保存在私有 Git 伴生仓里。

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DiscordChatExporter](https://img.shields.io/badge/Engine-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![Languages](https://img.shields.io/badge/Languages-EN%20%2F%20CN-blue?style=flat)](#语言)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

## ⭐ 先读设计理念

一份存档得说得清文件来自哪个频道，也得过段时间还能打开。DiscordChatExporter 负责访问 Discord；这个 skill 负责本地处理：凭据只传入子进程环境，真实产物只写到确认过的私有 Git 仓库，每个文件都记录频道 ID、字节数和校验和。

名称方便人查找，身份由 ID 决定。整理脚本保留导出工具生成的 ID 目录和文件名，同名频道、同名 thread 不会合并，相对媒体链接也能继续使用。索引列出每份 HTML 和 JSON；清单还记录频道显示名称与容器 ID。详见 [PHILOSOPHY.md](PHILOSOPHY.md)。

## 适用范围

使用获授权的 Bot 凭据。服务器应由你管理，或其管理员已允许该 Bot 访问指定频道。可以选一个服务器或一个频道，指定 ISO 日期范围，也可以下载媒体文件。服务器导出包含 threads。脚本依次导出 HTML 和 JSON，只有两种格式的频道 ID 集合一致，才会报告完成。

这是一次性归档工具，不做持续监控，也无法读取 Bot 无权访问的内容。个人账号数据或 Group DM 请使用 Discord 官方的 **请求我的数据** 功能。

## 安装

通过支持的插件管理器安装，或完整克隆仓库：

```bash
git clone --recurse-submodules https://github.com/DaizeDong/discord-history-export.git
```

已有克隆需运行 `git submodule update --init --recursive`。缺少 guards 子模块会直接报错。环境需要 Python 3.10+、Git、已登录的 GitHub CLI (`gh`)，以及支持的 [DiscordChatExporter CLI 版本](https://github.com/Tyrrrz/DiscordChatExporter/releases)。脚本会先检查指定程序的版本和导出命令帮助，再读取凭据；不会自动下载或安装导出工具。

## 私有 DATA 与凭据

新建或使用一个独立的 **PRIVATE GitHub 仓库**，克隆到本机，把 `DISCORD_HISTORY_EXPORT_DATA_DIR` 指向其中的数据目录。子目录可以尚未创建；脚本会先确认所属工作树是私有仓，再在执行时创建。明确设置 DATA 路径后，脚本就以它为准：空值、无效路径或不允许的目标会直接失败，不会改用另一个伴生仓。未设置 DATA 路径时，脚本使用[共享解析器](guards/COMPANION.md)查找目录。写入前还会检查工作树及 origin，并用 `gh repo view` 查询当前可见性。普通仓库和 linked worktree 都支持。公开仓、可见性未知、没有版本管理的目录，以及工具自己的源码目录都会被拒绝。

Bot 凭据放在本机环境变量中，或放在公开源码目录之外的本地文件里。`--credential-ref` 只接收 `env:VARIABLE_NAME` 或 `file:ABSOLUTE_PATH`。凭据文件应只允许所有者读取，并排除在版本管理之外。不要把凭据值发到助手对话或写进命令行。脚本仅在执行时读取值，通过子进程的 `DISCORD_TOKEN` 环境变量传给导出工具。stdout/stderr 由脚本捕获，失败时不会回显或记录原始输出；保存频道列表前会移除其中的凭据值。

目前有源码依据的环境变量传递版本是 **2.47**。帮助文本不必写出该环境变量，绑定关系由对应 tag 的源码证明。未知版本需要在导出命令帮助里明确支持同一环境变量，否则预检失败。详见[凭据传递依据](skills/discord-history-export/reference/credential-transport.md)。

## 预览与执行

把 `$SkillDir` 指向安装位置下的 `skills/discord-history-export`，把 `$Exporter` 指向已有导出程序。参考[生成的合成示例](tests/fixtures/example.md)，在本机换成获授权的范围。`plan` 检查参数和私有输出位置，显示本次范围与命令，不读取凭据，也不写出产物。把 `plan` 改成 `execute` 后执行。

两种操作都接受 `--guild-id` 或 `--channel-id`、`--after`、`--before`、`--media` 和 `--resume`。日期使用 ISO 格式，`--run-id` 必须是单个安全文件名。资源按脚本实际源码位置解析，所以可以从任意当前目录调用。

产物写入 `<private-data-dir>/runs/<run-id>`。`run.json` 固定本次范围、日期、媒体选项、导出程序和凭据引用。每次尝试各自保留原始文件、整理后的存档、索引和清单。运行目录的 `manifest.json` 记录相对文件路径、校验和、大小、从 JSON 实际消息列表算出的数量，以及完整文件目录。

已完成的同参数调用会校验现有文件，确认一致后返回，不再启动导出工具。部分完成或失败时退出码非零，并说明原因。用相同参数加上 `--resume` 可在新的尝试目录重试，之前的文件保留。修改参数或已有产物后，脚本会拒绝复用该 run ID。重试会重新导出两种格式，不会从某一条 Discord 消息接着下载。

## 整理已有导出

原来的位置参数接口仍可使用：

```powershell
python "$SkillDir/scripts/reorganize.py" "$RawDir" "$OrganizedDir" "$ChannelsTxt"
```

`$ChannelsTxt` 是已有的 DCE 频道列表。`$OrganizedDir` 必须位于确认过的私有伴生仓。输入文件名保留 `[%c]`；DCE 的 `%t` 对普通频道表示分类 ID，对 thread 表示父频道 ID。JSON 也可以通过 `channel.id` 提供身份。整理单一格式的已有存档可以算完成；完整导出则必须同时有两种格式。

整理脚本会在复制前检查全部源文件和目标文件；同时提供两种格式时，频道 ID 集合必须一致。脚本保留原始字节与嵌套媒体，检查本地链接。已有内容冲突或源目录改变都会被拒绝。相同输入重复运行不会改变结果，也不会通过覆盖文件解决重名问题。

## 验证与限制

```bash
python tools/make_fixtures.py
python -m pytest tests -q
```

离线测试使用生成的合成 Discord 记录，拦截导出程序、Git 和 GitHub CLI 调用，检查凭据、输出边界、媒体完整性、重试和完整安装目录别名。这只能证明离线行为，不能证明真实 Discord 权限、所有平台上的导出程序兼容性、插件目录激活或无人值守运行。仍为远程 URL 的媒体需要网络访问；需要下载附件时请加 `--media`。导出程序报错不会被当作成功。

## 语言

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · 更新日志 · License

见 [ROADMAP.md](ROADMAP.md)、[CHANGELOG.md](CHANGELOG.md) 和 [LICENSE](LICENSE)（MIT）。

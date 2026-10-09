# discord-history-export

把获授权的 Discord 历史导出为经过校验的 HTML 和 JSON，保存在私有 Git 伴生仓里。

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DiscordChatExporter](https://img.shields.io/badge/Engine-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![Languages](https://img.shields.io/badge/Languages-EN%20%2F%20CN-blue?style=flat)](README.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

## ⭐ 设计哲学

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

已有克隆需运行 `git submodule update --init --recursive`。缺少 guards 子模块会直接报错。环境需要 Python 3.10+、Git、有效的本地 Guards 可见性凭据，以及支持的 [DiscordChatExporter CLI 版本](https://github.com/Tyrrrz/DiscordChatExporter/releases)。脚本会先检查指定程序的版本和导出命令帮助，再读取 Bot 凭据；不会自动下载或安装导出工具。

## 私有 DATA 与凭据

将 `DISCORD_HISTORY_EXPORT_DATA_DIR` 指向独立 PRIVATE Git 伴生仓准确的
`<companion>/data`。显式选择为空或无效时直接失败；缺少的 `data/` 子目录只在执行时、
验证通过后创建。未设置时使用共享伴生仓发现。写入需要已有提交、有效的本地 Guards
可见性记录、声明的产物布局和 Git 可跟踪性。[DATA.md](DATA.md) 规定传输策略、
嵌套工作树检查、产物写入检查和保留规则。脚本不刷新可见性记录，不请求 GitHub，
也不自动暂存、提交或推送存档。

Bot 凭据保存在本地环境变量或仅所有者可读的文件中，文件须位于公开源码目录和版本管理
之外。`--credential-ref` 只接收 `env:VARIABLE_NAME` 或 `file:ABSOLUTE_PATH`；
不要把凭据值写入对话或命令行。执行时通过子进程的 `DISCORD_TOKEN` 环境变量传递，
导出程序输出由脚本捕获，保存频道列表前会移除凭据。原始失败输出不会回显或记录。

[凭据传递依据](skills/discord-history-export/reference/credential-transport.md)
规定有源码证明的 **2.47** 版本，以及未知版本必须在命令帮助中明确提供的环境变量支持。
预览和已完成任务的复验不读取凭据值。

## 预览与执行

把 `$SkillDir` 指向安装位置下的 `skills/discord-history-export`，把 `$Exporter` 指向已有导出程序。参考[生成的合成示例](tests/fixtures/example.md)，在本机换成获授权的范围。`plan` 检查参数和私有输出位置，显示本次范围与命令，不读取凭据，也不写出产物。把 `plan` 改成 `execute` 后执行。

两种操作都接受 `--guild-id` 或 `--channel-id`、`--after`、`--before`、`--media` 和 `--resume`。日期使用 ISO 格式，`--run-id` 必须是单个安全文件名。资源按脚本实际源码位置解析，所以可以从任意当前目录调用。

产物写入 `<private-data-dir>/runs/<run-id>`。`run.json` 固定本次范围、日期、媒体选项、导出程序和凭据引用。每次尝试各自保留原始文件、整理后的存档、索引和清单。运行目录的 `manifest.json` 记录相对文件路径、校验和、大小、从 JSON 实际消息列表算出的数量，以及完整文件目录。

已完成的同参数调用会校验现有文件，确认一致后返回，不再启动导出工具。部分完成或失败时退出码非零，并说明原因。用相同参数加上 `--resume` 可在新的尝试目录重试，之前的文件保留。修改参数或已有产物后，脚本会拒绝复用该 run ID。重试会重新导出两种格式，不会从某一条 Discord 消息接着下载。

扫描目录时遇到权限或 I/O 错误，源文件检查、目标位置检查和已完成任务的复验都会停止。恢复访问后再重试。无法记录完整文件清单时，已有文件和上次保存的清单会保留；如果重试时无法核对这次未完成的尝试，请按报错指引保留原任务，改用新的 run ID。

[归档校验规范](skills/discord-history-export/reference/archive-validation.md)
规定 DCE 2.47 的 HTML 结构、零消息完成记录、JSON 消息数量和本地链接规则。
整理、确认完成和复验都会执行同一套校验。旧的已完成任务若校验失败，须保留原任务，
使用新的 run ID 导出；`--resume` 仅用于未完成的任务。

## 整理已有导出

原来的位置参数接口仍可使用：

```powershell
python "$SkillDir/scripts/reorganize.py" "$RawDir" "$OrganizedDir" "$ChannelsTxt"
```

`$ChannelsTxt` 是已有的 DCE 频道列表。`$OrganizedDir` 必须位于确认过的私有伴生仓的 `<companion>/data/organized/<archive-id>/` 下。输入文件名保留 `[%c]`；DCE 的 `%t` 对普通频道表示分类 ID，对 thread 表示父频道 ID。JSON 也可以通过 `channel.id` 提供身份。整理单一格式的已有存档可以算完成；完整导出则必须同时有两种格式。

整理脚本会在复制前检查全部源文件和目标文件；同时提供两种格式时，频道 ID 集合必须一致。脚本保留原始字节与嵌套媒体，检查本地链接。已有内容冲突或源目录改变都会被拒绝。相同输入重复运行不会改变结果，也不会通过覆盖文件解决重名问题。

完整的文件身份、源字节和媒体依赖规则见[归档校验](skills/discord-history-export/reference/archive-validation.md)。
整理与导出都按 [DATA.md](DATA.md) 检查存储，包括探测导出程序后再次验证目标，
以及拒绝将被 Git 忽略的原始文件报告为完整结果。

## 验证与限制

```bash
python tools/make_fixtures.py
python -m pytest tests -q
```

离线测试使用生成的合成 Discord 记录，并拦截导出程序调用。存储边界测试还会使用真实的临时 Git 仓库和生成的本地可见性凭据，不会请求 Discord 或 GitHub。测试检查凭据、输出边界、媒体完整性、重试和完整安装目录别名。这只能证明离线行为，不能证明真实 Discord 权限、所有平台上的导出程序兼容性、插件目录激活或无人值守运行。仍为远程 URL 的媒体需要网络访问；需要下载附件时请加 `--media`。导出程序报错不会被当作成功。

## 语言

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · 更新日志 · License

见 [ROADMAP.md](ROADMAP.md)、[CHANGELOG.md](CHANGELOG.md) 和 [LICENSE](LICENSE)（MIT）。

# discord-history-export

Export an entire Discord server — every channel, every thread — into local HTML (to read) and JSON (to analyze), in 5–10 minutes.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Powered by DiscordChatExporter](https://img.shields.io/badge/Powered%20by-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![Languages](https://img.shields.io/badge/Languages-EN%20%2F%20CN-blue?style=flat)](#languages)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

---

## ⭐ Read this first — the design philosophy

The exporter (Tyrrrz/DiscordChatExporter) already exists and is excellent. So why a skill?

Because the naive CLI invocation fails in five non-obvious ways for a real multi-channel guild on Windows, and each failure looks like a bug rather than a misconfiguration. The value of this skill is not "it calls a tool" — it is **the encoded debrief of every way that tool quietly does the wrong thing**, plus the two pieces that are genuinely annoying to do by hand:

- **Auth without DevTools.** Getting a Discord user token normally means opening DevTools, finding a request, and copy-pasting an `Authorization` header. This skill drives a headed browser via Playwright MCP: you log in once, pick the server visually, and it captures the token and guild ID for you.
- **Output you can actually read.** DCE's default output is a tree of 18-digit Discord-ID folders. This skill reorganizes it into `<Category>/<channel>.html` so you can double-click and read.

It is also **honest about risk by default**. Discord's ToS forbids automating user accounts. The skill surfaces that in one sentence *before* any token is captured, offers the ToS-compliant Bot route to admins, and at the end tells you to rotate your password because your token appeared in the transcript. The philosophy is: do the hard, fiddly parts for the user, and never hide the trade-off.

## What it is (and isn't)

**It is** a one-shot archival tool: point it at a server you've joined, get back a complete, human-readable HTML mirror plus a parallel JSON dataset for analysis, organized by category and channel with thread sub-folders.

**It isn't** a continuous sync, a Discord bot, a monitoring tool, or a way to read servers you can't already read. It exports only what your own account can already see, once. For Group DMs it aborts and points you at Discord's official GDPR "Request my Data" export instead.

## Install

```
/plugin install github:DaizeDong/discord-history-export
```

Or clone manually into your Claude plugins dir:

```bash
git clone https://github.com/DaizeDong/discord-history-export.git \
  ~/.claude/plugins/discord-history-export
```

Skill auto-activates on phrases like `export discord history`, `download my discord server`, `archive discord chat`, `导出 discord 群组`, `拉 discord 频道历史`, etc.

## 60-second tour

You say:

```
export the full history of the Discord server I'm in
```

What runs automatically:

1. Confirms scope (whole guild vs single channel vs group DM) and surfaces the ToS risk in one sentence
2. Downloads the latest [Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) self-contained CLI release (no .NET install needed)
3. Opens a headed browser via Playwright MCP — **you log in once**, navigate to the target server, and say "OK"
4. Captures your **user token** (iframe localStorage trick) and **guild ID** (URL second segment) — no DevTools, no copy-paste
5. Runs `exportguild` with `--include-threads All` and a collision-proof filename template
6. Runs a Python reorganize step that turns DCE's Discord-ID folders into a human-readable `<Category>/<channel>.html` + `<Category>/<channel>_threads/` tree
7. Reports total messages, top channels by volume, forbidden-channel skips, and forum-channel quirks
8. Tells you to **change your Discord password** to invalidate the token that appeared in the transcript

For a 43-channel guild (~50k messages, ~1900 threads), end-to-end runtime is roughly 5–10 minutes; outputs are ~96 MB HTML + ~70 MB JSON.

## How to invoke

Just describe the intent — the skill auto-activates on triggers like:

- `export discord history`
- `download my discord server`
- `archive discord chat`
- `save my discord messages`
- `导出 discord 群组` / `拉 discord 频道历史` / `discord 历史归档`

You can also drive [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) directly without the skill:

```bash
# 1. Get token from Discord browser DevTools → Network → any /api request → Authorization header
# 2. Get guild ID from the URL: discord.com/channels/<GUILD_ID>/<channel_id>

DCE_EXE="path/to/DiscordChatExporter.Cli.exe"

# list channels (sanity check, also feeds reorganize.py)
"$DCE_EXE" channels -t "$TOKEN" -g "$GUILD_ID" > channels.txt

# export everything
"$DCE_EXE" exportguild \
  -t "$TOKEN" \
  -g "$GUILD_ID" \
  -f HtmlDark \
  --include-threads All \
  --parallel 4 \
  -o "exports/all/%t/%C [%c].html"

# reorganize into readable folders
python skills/discord-history-export/scripts/reorganize.py \
  exports/all exports/organized channels.txt
```

## Example output

```
exports/
├── organized/                  ← HTML, double-click any file to read
│   ├── INDEX.md                ← folder map + file/message counts
│   ├── General/
│   │   ├── general.html
│   │   ├── help-desk_threads/  ← forum channel: threads only
│   │   └── ...
│   ├── Terminal-Bench/
│   │   ├── tb-3.html
│   │   ├── tb-3_threads/
│   │   └── ...
│   └── ...
├── organized_json/             ← parallel tree, JSON for analysis
├── all/, all_json/             ← raw DCE output (Discord-ID folders)
└── channels.txt                ← guild channel list (used by reorganize)
```

### Why this isn't already trivial

The naive DCE CLI invocation fails in five non-obvious ways for a multi-channel guild on Windows. Each one cost a retry during validation; the skill encodes the fix:

| Gotcha | Symptom | Fix encoded in skill |
|---|---|---|
| `%t` is not category name | Output folders are 18-digit Discord IDs | `scripts/reorganize.py` maps IDs → names |
| Duplicate thread titles | Whole export crashes mid-run with `FileShare` lock error | Filename template always includes `[%c]` |
| Git Bash `/c/...` paths | 70 MB silently written to `C:\c\Users\...` | Always pass `C:/...` Windows-style |
| Forum channels look empty | `help-desk.html`, `tb-task-proposals.html` missing | Documented in summary; threads ARE captured |
| Forbidden channels | Errors mid-progress, looks like a crash | Listed in final summary, not treated as failure |

See `skills/discord-history-export/SKILL.md` → "Gotchas Encountered" for the full debrief.

## Limitations

**ToS reality check.** Discord's ToS forbids automating user accounts. This skill makes one HTTP request per page of messages, paced by DCE's rate-limit handler — risk to a normal account doing a one-off export is low but non-zero. Before any token is captured the skill surfaces this risk and offers the official alternative:

- **Server admin?** Invite a Bot (ToS-compliant). Skill hands off, does not run.
- **Group DM?** Skill aborts and points to Settings → Privacy & Safety → **Request my Data** for the GDPR export route.

**Prerequisites:**

- Windows / macOS / Linux (the skill defaults to Windows x64; swap the DCE release asset for other targets)
- `git`, `python` (3.8+), `curl`, `unzip`
- Playwright MCP plugin installed in Claude Code (provides the browser tools)
- ~200 MB free disk for the DCE binary + per-guild exports

No .NET install required — DCE ships a self-contained binary.

## Languages

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · Changelog · License

See [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [LICENSE](LICENSE) (MIT).

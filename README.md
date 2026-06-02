# discord-history-export

A Claude Code skill that exports the full history of any Discord server you've joined — every channel, every thread — into local HTML (for reading) and JSON (for analysis), organized by category and channel.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DCE](https://img.shields.io/badge/Powered%20by-DiscordChatExporter-5865F2?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)

[English](README.md) | [中文版](README_CN.md)

---

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

---

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

---

## Output layout

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

---

## Why this skill exists (i.e. why this isn't already trivial)

The naive DCE CLI invocation fails in five non-obvious ways for a multi-channel guild on Windows. Each one cost a retry during validation; the skill encodes the fix:

| Gotcha | Symptom | Fix encoded in skill |
|---|---|---|
| `%t` is not category name | Output folders are 18-digit Discord IDs | `scripts/reorganize.py` maps IDs → names |
| Duplicate thread titles | Whole export crashes mid-run with `FileShare` lock error | Filename template always includes `[%c]` |
| Git Bash `/c/...` paths | 70 MB silently written to `C:\c\Users\...` | Always pass `C:/...` Windows-style |
| Forum channels look empty | `help-desk.html`, `tb-task-proposals.html` missing | Documented in summary; threads ARE captured |
| Forbidden channels | Errors mid-progress, looks like a crash | Listed in final summary, not treated as failure |

See `skills/discord-history-export/SKILL.md` → "Gotchas Encountered" for the full debrief.

---

## ToS reality check

Discord's ToS forbids automating user accounts. This skill makes one HTTP request per page of messages, paced by DCE's rate-limit handler — risk to a normal account doing a one-off export is low but non-zero. Before any token is captured the skill surfaces this risk to the user and offers the official alternative:

- **Server admin?** Invite a Bot (ToS-compliant). Skill hands off, does not run.
- **Group DM?** Skill aborts and points to Settings → Privacy & Safety → **Request my Data** for the GDPR export route.

---

## Prerequisites

- Windows / macOS / Linux (the skill defaults to Windows x64; swap the DCE release asset for other targets)
- `git`, `python` (3.8+), `curl`, `unzip`
- Playwright MCP plugin installed in Claude Code (provides the browser tools)
- ~200 MB free disk for the DCE binary + per-guild exports

No .NET install required — DCE ships a self-contained binary.

---

## Manual usage (without the skill)

If you want to drive DCE directly:

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

---

## License

MIT — see `LICENSE`.

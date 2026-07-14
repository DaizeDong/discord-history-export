---
name: Discord History Export
description: "Use to export a joined Discord server's history to HTML+JSON via DiscordChatExporter. Triggers: export discord history, archive discord chat, 导出 discord 频道, 拉 discord 群组."
---

# Discord History Export

> **Caveat (ToS)**: Discord's Terms of Service forbid automating user accounts ("self-botting"), even for actions the user could perform by hand. The exporter sends one HTTP request per `before=` page, paced by DCE's built-in rate-limit handler — risk to a normal account doing a one-off export is low but non-zero. The skill must surface this to the user before any token is captured, and must offer the GDPR data-export route as an alternative.
> **Caveat (token)**: The user's token grants full account access (DMs, settings, payments). It appears in the conversation transcript during this skill. After export, instruct the user to change their Discord password — this invalidates the token immediately.

## When To Use

- User has joined a Discord server and wants a local copy of every channel they can read
- User wants ONE specific channel exported (skip the guild-wide walk; use the `export` subcommand instead of `exportguild`)
- User wants a JSON dataset to grep / analyze / feed into another LLM
- User wants an HTML archive that renders identically to Discord (avatars, attachments, replies, emoji)

## When NOT To Use

- Target is a **Group DM** (multi-person private chat) — Discord blocks Bot accounts from joining and self-bot detection is denser here. Use the official GDPR data export instead: Settings → Privacy & Safety → Request my Data.
- User is a **server administrator** and willing to invite a Bot — that path is ToS-compliant. Hand off to the user, do not run this skill.
- User wants **real-time monitoring** — DCE is one-shot. For polling DMs see `~/your-tool-dir/`.
- Only a **single channel snapshot of <200 messages** is needed — call the Discord API directly with `requests`, faster than installing DCE.

## Prerequisites

| Check | Command | Required |
|---|---|---|
| Git available | `git --version` | yes (clone reference repo) |
| Python 3.8+ | `python --version` | yes (reorganize script) |
| Playwright MCP tools loaded | check `mcp__plugin_playwright_playwright__browser_*` | yes (user login flow) |
| Internet | n/a | yes (DCE release + Discord API) |
| `.NET runtime` | NOT required — the CLI release is self-contained |

## Critical Rules (Non-Negotiable)

These come from real failures during the initial run. Apply automatically.

1. **Always include `[%c]` (channel ID) in the output filename template.** Two threads in the same channel with identical titles will trigger a Windows `FileShare` violation and crash the entire export. Correct: `"exports/all/%t/%C [%c].html"`. Incorrect: `"exports/all/%t/%C.html"`.
2. **Pass Windows-style paths to the `.exe`, not Git Bash `/c/...` paths.** Git Bash leaves `/c/Users/...` alone when handing to the Windows binary, which interprets it as `C:\c\Users\...` and silently writes 70 MB to the wrong drive root. Use `C:/Users/...` or `${PWD}` resolved by bash first.
3. **`%t` in DCE is parent-container ID, NOT category name.** For a non-thread channel `%t` = category ID; for a thread `%t` = parent channel ID. The output folders are therefore Discord IDs, never human-readable names. Reorganize after export — see `scripts/reorganize.py`.
4. **`--include-threads All`** — without this flag, forum channels (e.g. `help-forum`, `ideas`, `proposals`) export as empty because their entire content lives in threads.
5. **`--parallel 4`** — 1 is too slow on a 40-channel guild, 8+ trips Discord rate limits faster than DCE's backoff can absorb.
6. **Token rotation reminder before closing the session.** The token appears in plaintext in the conversation. Tell the user to change their Discord password.

## Workflow

### Step 1: Confirm scope with user, surface ToS risk

Ask in one focused message (NOT a barrage):

- Guild type — server (OK), group DM (abort, route to GDPR), single channel (use `export` not `exportguild`)
- Admin of server? — if yes, recommend Bot route instead
- Acknowledge ToS risk in one sentence so the user can opt out

### Step 2: Provision DCE CLI

Default install location: `C:/path/to/DiscordChatExporter/`.

```bash
# Clone the source repo (for reference + version pinning)
git clone https://github.com/Tyrrrz/DiscordChatExporter.git \
  "C:/path/to/DiscordChatExporter"

# Fetch latest CLI release (Windows x64, self-contained — no .NET install needed)
TAG=$(curl -s https://api.github.com/repos/Tyrrrz/DiscordChatExporter/releases/latest \
  | python -c "import json,sys; print(json.load(sys.stdin)['tag_name'])")
mkdir -p "C:/path/to/DiscordChatExporter/bin"
curl -sL -o "C:/path/to/DiscordChatExporter/bin/cli.zip" \
  "https://github.com/Tyrrrz/DiscordChatExporter/releases/download/${TAG}/DiscordChatExporter.Cli.win-x64.zip"
unzip -o "C:/path/to/DiscordChatExporter/bin/cli.zip" \
  -d "C:/path/to/DiscordChatExporter/bin/cli"

# Sanity check
"C:/path/to/DiscordChatExporter/bin/cli/DiscordChatExporter.Cli.exe" --version
```

For other OS/arch, swap the asset name (`linux-x64`, `osx-arm64`, etc.).

### Step 3: Capture token + guild ID via headed browser

Load the Playwright MCP tools first (they are deferred — use `ToolSearch` with `select:mcp__plugin_playwright_playwright__browser_navigate,...`).

```js
// 1. Open login page — user logs in interactively (incl. 2FA)
await page.goto('https://discord.com/login');

// 2. Tell the user: "log in, then navigate to the target server/channel,
//    then scroll or click any message to fire an API request, then say 'OK'"

// 3. Read the URL — guild ID is the second path segment
//    URL pattern: https://discord.com/channels/<guild_id>/<channel_id>
const url = await page.evaluate(() => window.location.href);

// 4. Extract the user token — iframe trick bypasses Discord's
//    localStorage scrub-on-load. The token is JSON-encoded (extra quotes).
const token = await page.evaluate(() => {
  const f = document.createElement('iframe');
  document.body.appendChild(f);
  const t = f.contentWindow.localStorage.getItem('token');
  f.remove();
  return t ? t.replace(/^"|"$/g, '') : null;
});
```

If the iframe trick returns `null`: Discord may have patched it again. Fall back to inspecting a network request — `browser_network_requests` with filter `discord\.com/api` then read the `Authorization` header from any one of them.

### Step 4: Optional — list channels for the user to pick from / sanity-check guild

```bash
"$DCE_EXE" channels -t "$TOKEN" -g "$GUILD_ID"
```

Outputs `<channel_id> | <category> / <channel_name>` lines. Save to `channels.txt` — the reorganize script needs it.

### Step 5: Export

```bash
# HTML (human-readable, on the order of 100 MB for tens of thousands of messages)
"$DCE_EXE" exportguild \
  -t "$TOKEN" \
  -g "$GUILD_ID" \
  -f HtmlDark \
  --include-threads All \
  --parallel 4 \
  --fuck-russia \
  -o "C:/path/to/DiscordChatExporter/exports/all/%t/%C [%c].html"

# JSON (for analysis, a comparable size for the same export)
"$DCE_EXE" exportguild \
  -t "$TOKEN" \
  -g "$GUILD_ID" \
  -f Json \
  --include-threads All \
  --parallel 4 \
  --fuck-russia \
  -o "C:/path/to/DiscordChatExporter/exports/all_json/%t/%C [%c].json"
```

Run sequentially, NOT in parallel processes — same user token making concurrent requests to the same endpoints raises rate-limit pressure faster than DCE can back off.

Expected non-fatal errors: `Request to 'channels/<id>/messages?limit=1' failed: forbidden.` for channels the user cannot read. DCE skips them and continues. Note them for the final summary.

### Step 6: Reorganize raw output

```bash
python skills/discord-history-export/scripts/reorganize.py \
  <raw_export_dir> <organized_output_dir> <channels.txt>
```

The raw layout is keyed by Discord ID (a DCE quirk — see Critical Rule 3). The script:
- Detects whether each folder is a category or a channel-with-threads (by checking whether the folder ID matches a channel ID in `channels.txt`)
- For category folders: copies main channel files up to `<category>/<channel>.html`
- For channel-with-threads folders: copies into `<category>/<channel>_threads/<thread>.html`
- Generates `INDEX.md` with file/message counts

Run it once for HTML, once for JSON, into two parallel `organized/` trees.

### Step 7: Stats + handoff

Aggregate from the JSON export (lightweight one-liner):

```python
import json, glob
total = 0
for fp in glob.glob('organized_json/**/*.json', recursive=True):
    total += len(json.load(open(fp, encoding='utf-8')).get('messages', []))
print(total)
```

Report to the user:
- Total messages, channel count, time range
- Top channels by message volume
- Forbidden channels (skipped by Discord, not by us)
- Forum-channel quirk: those have no `<name>.html`, only `<name>_threads/`

### Step 8: Security cleanup

1. Close the Playwright browser instance.
2. Tell the user: **"Change your Discord password now to invalidate the token that appeared in this conversation."** Plain rotation, no other action required.
3. Do NOT save the token to memory or any persistent file. The `channels.txt` is fine to keep; the token is not.

## Gotchas Encountered (Reference)

These are the failure modes seen during the initial validation run. Each one cost a retry. The Critical Rules above encode the fixes; this section explains why.

### G1 — `%t` is not category name (silent)

Documentation calls `%t` a "thread/category" token. In practice, output folders are 18-digit Discord IDs, not names. There is no human-readable category template variable in DCE 2.47. **Always reorganize.**

### G2 — Identical thread titles → file lock crash (fatal)

DCE writes the channel file first, then opens it again for the message stream. When two threads in the same channel resolve to the same filename (because their titles are identical), the second open hits the first's lock and crashes the whole export, not just that file. **Always include `[%c]` in the filename template.**

### G3 — Git Bash path → wrong drive (silent, 70 MB misplaced)

`-o "/c/Users/foo/bar.json"` — bash leaves it untouched; the Windows .exe sees an absolute path starting with `/c/` and writes to `C:\c\Users\foo\bar.json`. **Pass `C:/...` or resolve with `$(cygpath -w "$path")` before invoking the .exe.**

### G4 — Forum channels look "empty" (informational)

Channels like `help-forum`, `ideas`, `proposals` are Discord Forum channels. Their entire content lives in posts (= threads). With `--include-threads All` the threads ARE captured, but there is no main-channel file. The reorganized output shows `forum-channel_threads/` only. **Tell the user this is expected, not a bug.**

### G5 — Forbidden channels (informational)

Channels with role-gated read perms (often `moderator-only`, `*-reviewers`, `*-area-chairs`, private categories) return `403 forbidden` even to a logged-in user lacking the role. **DCE skips them cleanly; list them in the summary so the user knows.**

### G6 — Bot token ≠ user token (architectural)

If the user already has a Discord Bot configured (e.g. for DM relay), its token is NOT reusable here — Bots can only read channels they have been invited to. This skill needs the user-account token, captured via the browser flow in Step 3.

### G7 — Token in transcript (security)

User tokens captured this way appear in the conversation transcript. They cannot be redacted post-hoc. Password rotation is the only mitigation. Tell the user in Step 8.

## Outputs

After Step 6 completes, the user has:

```
exports/
├── organized/                ← HTML for reading
│   ├── INDEX.md              ← folder map + file/message counts
│   ├── <Category 1>/
│   │   ├── channel-a.html
│   │   ├── channel-b.html
│   │   ├── channel-a_threads/
│   │   │   └── *.html
│   │   └── forum-channel_threads/
│   │       └── *.html
│   └── ...
├── organized_json/           ← parallel tree, same layout, JSON files
├── all/, all_json/           ← raw DCE output (Discord-ID folders)
└── channels.txt              ← guild channel list
```

Total size scales linearly with message count: ~2 KB/message HTML, ~1.4 KB/message JSON.

## Variants

- **Single channel only**: replace `exportguild -g $GUILD_ID` with `export -c $CHANNEL_ID`. Drop `--include-threads All` if the channel is not a forum.
- **Date range**: add `--after 2025-01-01 --before 2025-12-31`.
- **With media (avatars, attachments)**: add `--media --reuse-media`. Disk usage may 3-10× depending on image volume.
- **macOS / Linux**: swap the release asset (`osx-arm64`, `linux-x64`).

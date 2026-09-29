---
name: discord-history-export
description: "Export authorized Discord guild or channel history to verified HTML and JSON in private storage. Use for Discord history export, chat archives, or 导出 Discord 历史."
---

# Discord history export

Use an authorized bot credential for a server the user administers or whose administrator has granted that bot access. For personal account data or Group DMs, use Discord's official Request my Data route. Only export the scope the user has authorized.

## Local setup

The complete source tree requires its guards submodule. Read [reference/credential-transport.md](reference/credential-transport.md) for supported exporter evidence. Python 3.10+, Git, authenticated `gh`, and an existing DiscordChatExporter CLI executable are required. Do not download or install an exporter as part of an export request without the user's authorization.

Resolve the installed skill directory before invoking `scripts/export_history.py`. Paths in commands must be absolute when running from an unrelated current directory. The helper discovers the canonical source tree itself, including through an installed alias.

Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to a directory in a separate private Git companion. An explicit DATA selection is authoritative; invalid or empty values fail without selecting a different companion. A missing child directory is allowed only beneath a verified private worktree and is created during execution, never during plan. Without a DATA override, the helper uses the authoritative shared resolver for discovery. It checks the enclosing worktree, its origin, and fresh PRIVATE visibility before credentials, exporter calls, or output writes. An unversioned directory, PUBLIC/UNKNOWN visibility, or the consumer's own checkout is rejected. Private linked Git worktrees are valid. Real archives and run history stay versioned in that private companion; credentials stay outside version control.

Credentials are local references only: `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH`. Never ask the user to paste a credential into a conversation. The helper reads the reference only for execution and passes the value via the exporter's child `DISCORD_TOKEN` environment. Do not construct a token command-line flag. No browser credential extraction is part of this workflow.

## Export

1. Establish the authorized guild or channel ID, optional ISO date limits, and media preference. A guild export includes all accessible threads.
2. Run `scripts/export_history.py plan` with `--exporter`, `--credential-ref`, `--run-id`, and exactly one of `--guild-id` / `--channel-id`. Optional arguments are `--after`, `--before`, `--media`, and `--resume`. Plan validates the private destination and prints the scope without reading a credential or writing files.
3. Run the same arguments with `execute` when export is authorized. The helper probes exporter version/help, establishes credential transport, then exports HTML and JSON sequentially. DCE filenames always retain `[%c]`; `%t` preserves the category or parent channel ID.
4. Read the run-level `manifest.json`. Only `status: complete` with a zero exit code is success. Quote its HTML/JSON/media counts, actual JSON message count, issues, and private companion. Partial or failed states require a nonzero exit and remain visible.

Output is `<resolved-private-data>/runs/<run-id>`. `run.json` freezes the exporter, credential reference, scope, date limits, and media choice. Completed reruns verify all existing files and return idempotently. An incomplete run needs `--resume` with identical configuration; retry uses a new attempt directory and retains previous files. It re-exports both formats rather than resuming at a message cursor. Never change scope under the same run ID or edit prior artifacts to make a check pass.

## Existing raw archives

Preserve the positional interface: `python scripts/reorganize.py RAW_DIR ORGANIZED_DIR CHANNELS_TXT`. Supply absolute paths from other working directories. The output must pass the same private Git boundary.

The organizer preserves source bytes, ID folders, repeated-title identities, and nested media links. It writes `INDEX.md` plus a manifest with every source/destination path, channel ID, byte count, and SHA-256. JSON contributes counts from its actual `messages` array. A single-format input is complete for that explicitly supplied archive; mixed formats must have matching channel ID sets. Conflicts, unidentified files, broken local links, and changed input are rejected before copying; nothing is overwritten to resolve a collision.

## Evidence boundary

Synthetic tests and an installed-directory alias prove local behavior only. They do not prove live Discord access, exporter behavior on an actual account, plugin catalog activation, or a production run. Report those boundaries explicitly. Remote media URLs still need a network connection unless media was downloaded successfully.

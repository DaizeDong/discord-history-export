---
name: discord-history-export
description: "Export authorized Discord guild or channel history to verified HTML and JSON in private storage. Use for Discord history export, chat archives, or 导出 Discord 历史."
---

# Discord history export

Use an authorized bot credential for a server the user administers or whose administrator has granted that bot access. For personal account data or Group DMs, use Discord's official Request my Data route. Only export the scope the user has authorized.

## Local setup

The complete source tree requires its guards submodule. Read [reference/credential-transport.md](reference/credential-transport.md) for supported exporter evidence. Python 3.10+, Git, a fresh local Guards visibility receipt, and an existing DiscordChatExporter CLI executable are required. Do not download or install an exporter as part of an export request without the user's authorization.

Resolve the installed skill directory before invoking `scripts/export_history.py`. Paths in commands must be absolute when running from an unrelated current directory. The helper discovers the canonical source tree itself, including through an installed alias.

Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to exactly `<companion>/data` in a separate
PRIVATE Git companion. Invalid or empty explicit selections fail; otherwise the
shared resolver discovers storage. A missing child is created during execution,
never during plan. Committed HEAD, current local visibility proof, source-owned
artifact layout and effective Git trackability are required before credentials,
exporter calls or writes. Normal and private linked worktrees are supported.
The standalone organizer uses `data/organized/<archive-id>/`; the runner uses
`data/runs/<run-id>/`. Keep archives and history versioned in the PRIVATE companion.
[DATA.md](../../DATA.md) is authoritative for route and nested-repository policy,
rechecks after exporter probes, concrete-file admission and read-only replay.

Credentials are local references only: `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH`. Never ask the user to paste a credential into a conversation. The helper reads the reference only for execution and passes the value via the exporter's child `DISCORD_TOKEN` environment. Do not construct a token command-line flag. No browser credential extraction is part of this workflow.

Prepare or refresh the local visibility receipt through
[Guards setup](../../guards/COMPANION.md) before export. Proof itself invokes no
SSH, `gh` or network command. Credentials remain outside version control.

## Export

1. Establish the authorized guild or channel ID, optional ISO date limits, and media preference. A guild export includes all accessible threads.
2. Run `scripts/export_history.py plan` with `--exporter`, `--credential-ref`, `--run-id`, and exactly one of `--guild-id` / `--channel-id`. Optional arguments are `--after`, `--before`, `--media`, and `--resume`. Plan validates the private destination and prints the scope without reading a credential or writing files.
3. Run the same arguments with `execute` when export is authorized. The helper probes exporter version/help, establishes credential transport, then exports HTML and JSON sequentially. DCE filenames always retain `[%c]`; `%t` preserves the category or parent channel ID.
4. Read the run-level `manifest.json`. Only `status: complete` with a zero exit code is success. Quote its HTML/JSON/media counts, actual JSON message count, issues, and private companion. Partial or failed states require a nonzero exit and remain visible.

Output is `<resolved-private-data>/runs/<run-id>`. `run.json` freezes the exporter, credential reference, scope, date limits, and media choice. Completed reruns verify all existing files and return idempotently. An incomplete run needs `--resume` with identical configuration; retry uses a new attempt directory and retains previous files. It re-exports both formats rather than resuming at a message cursor. Never change scope under the same run ID or edit prior artifacts to make a check pass.

Every directory inventory must finish successfully. On enumeration errors, restore access before retrying; preserve all files and the last saved manifest. If an interrupted attempt cannot be reconciled on retry, use a new run ID as directed rather than editing its evidence.

## Existing raw archives

Preserve the positional interface: `python scripts/reorganize.py RAW_DIR ORGANIZED_DIR CHANNELS_TXT`. Supply absolute paths from other working directories. `ORGANIZED_DIR` must be under `<companion>/data/organized/<archive-id>/` and pass the same private Git boundary.

The organizer verifies the supplied formats before copying and refuses collisions. Read [channel identity and receipts](reference/archive-validation.md#channel-identity-and-receipts) for source preservation, manifests, format completeness and rejection rules.

Follow [archive validation](reference/archive-validation.md) for the supported
DCE 2.47 HTML structure, empty chatlogs, completion footers, JSON counts and portable
links. Validation runs during organization, export completion and completed replay.
Preserve a historical complete run that fails validation and use a new run ID;
only incomplete runs can retry into a new attempt with `--resume`.

The runner rechecks the destination after exporter probes and before reading
credentials. Ignored raw artifacts remain private and produce partial failure.
The helper does not stage, commit or push archives.

## Evidence boundary

Synthetic tests and an installed-directory alias prove local behavior only. They do not prove live Discord access, exporter behavior on an actual account, plugin catalog activation, or a production run. Report those boundaries explicitly. Remote media URLs still need a network connection unless media was downloaded successfully.

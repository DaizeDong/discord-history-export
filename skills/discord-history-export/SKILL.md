---
name: discord-history-export
description: "Export authorized Discord guild or channel history to verified HTML and JSON in private storage. Use for Discord history export, chat archives, or 导出 Discord 历史."
---

# Discord history export

Use an authorized bot credential for a server the user administers or whose administrator has granted that bot access. For personal account data or Group DMs, use Discord's official Request my Data route. Only export the scope the user has authorized.

## Local setup

The complete source tree requires its guards submodule. Read [reference/credential-transport.md](reference/credential-transport.md) for supported exporter evidence. Python 3.10+, Git, a fresh local Guards visibility receipt, and an existing DiscordChatExporter CLI executable are required. Do not download or install an exporter as part of an export request without the user's authorization.

Resolve the installed skill directory before invoking `scripts/export_history.py`. Paths in commands must be absolute when running from an unrelated current directory. The helper discovers the canonical source tree itself, including through an installed alias.

Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to exactly `<companion>/data` in a separate private Git companion. An explicit DATA selection is authoritative; invalid or empty values fail without selecting a different companion. A missing child directory is allowed only beneath a verified private worktree and is created during execution, never during plan. Without a DATA override, the helper uses the authoritative shared resolver for discovery. The public Guards proof checks the enclosing worktree and all physical and effective publication routes against its local visibility receipt. The helper also requires committed HEAD and an exact output path that Git does not ignore. Missing or stale receipts, PUBLIC/UNKNOWN visibility, unversioned or unborn repositories, ignored paths, and the consumer's own checkout are rejected before credentials, exporter calls, or output writes. Private linked Git worktrees are valid. Real archives and run history stay versioned in that private companion; credentials stay outside version control.

Credentials are local references only: `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH`. Never ask the user to paste a credential into a conversation. The helper reads the reference only for execution and passes the value via the exporter's child `DISCORD_TOKEN` environment. Do not construct a token command-line flag. No browser credential extraction is part of this workflow.

Every effective fetch and push URL of every configured remote must prove PRIVATE visibility on github.com. Git routing overrides, custom transports, and TLS trust overrides are refused. The bundled shared HTTP policy checks every configuration occurrence, including URL scopes and empty resets, while allowing enabled certificate verification and supported performance options. Each proof uses one validated environment snapshot. Use canonical GitHub HTTPS URLs. The shared static policy also accepts SSH, including aliases with a proven GitHub hostname, only when it recognizes the client and preserves default server trust. Unsupported routing or trust settings fail closed. Prepare or refresh the local receipt through the [Guards visibility setup](../../guards/COMPANION.md) before export. Proof itself invokes no SSH, `gh`, or network command. Plan, resume, and completed replay also check the selected run tree and existing nested repositories before exporter probes, credential reads, or output writes.

## Export

1. Establish the authorized guild or channel ID, optional ISO date limits, and media preference. A guild export includes all accessible threads.
2. Run `scripts/export_history.py plan` with `--exporter`, `--credential-ref`, `--run-id`, and exactly one of `--guild-id` / `--channel-id`. Optional arguments are `--after`, `--before`, `--media`, and `--resume`. Plan validates the private destination and prints the scope without reading a credential or writing files.
3. Run the same arguments with `execute` when export is authorized. The helper probes exporter version/help, establishes credential transport, then exports HTML and JSON sequentially. DCE filenames always retain `[%c]`; `%t` preserves the category or parent channel ID.
4. Read the run-level `manifest.json`. Only `status: complete` with a zero exit code is success. Quote its HTML/JSON/media counts, actual JSON message count, issues, and private companion. Partial or failed states require a nonzero exit and remain visible.

Output is `<resolved-private-data>/runs/<run-id>`. `run.json` freezes the exporter, credential reference, scope, date limits, and media choice. Completed reruns verify all existing files and return idempotently. An incomplete run needs `--resume` with identical configuration; retry uses a new attempt directory and retains previous files. It re-exports both formats rather than resuming at a message cursor. Never change scope under the same run ID or edit prior artifacts to make a check pass.

Every directory inventory must finish successfully. On enumeration errors, restore access before retrying; preserve all files and the last saved manifest. If an interrupted attempt cannot be reconciled on retry, use a new run ID as directed rather than editing its evidence.

## Existing raw archives

Preserve the positional interface: `python scripts/reorganize.py RAW_DIR ORGANIZED_DIR CHANNELS_TXT`. Supply absolute paths from other working directories. `ORGANIZED_DIR` must be under `<companion>/data/organized/<archive-id>/` and pass the same private Git boundary.

The organizer preserves source bytes, ID folders, repeated-title identities, and nested media links. It writes `INDEX.md` plus a manifest with every source/destination path, channel ID, byte count, and SHA-256. JSON contributes counts from its actual `messages` array. A single-format input is complete for that explicitly supplied archive; mixed formats must have matching channel ID sets. Conflicts, unidentified files, broken local links, and changed input are rejected before copying; nothing is overwritten to resolve a collision.

Supported HTML needs an HTML5 doctype, closed sibling `preamble`, `chatlog`, and `postamble` sections in order, and an `Exported N message(s)` entry inside the postamble, following the DiscordChatExporter 2.47 template. Empty chatlogs are valid. Localized digit grouping and optional `html`/`body` end tags are accepted. Empty files, plain-text errors, generic error pages, and missing completion footers are rejected during organization, export, and completed replay. Text-only element contents and self-closing non-void elements cannot supply completion; CSS dependency checks recognize escaped identifiers. If a historical complete run fails content validation, preserve it and use a new run ID; only incomplete runs can retry into a new attempt with `--resume`.

Archives must work when opened from local files. Reject scheme-relative URLs (`//host/path`), which inherit `file:` in that context; keep explicit HTTP(S) remote URLs distinct from relative local paths. Active HTML `<base href>` is unsupported and fails before organization or completion, including empty values. Export without a base URL. A base element without `href` or inside inert template content does not alter the document base.

The destination is proved again after exporter version/help probes, before reading credentials. Existing replay files and dynamically named raw artifacts are checked for exact Git ignore status. Ignored raw artifacts remain in the private companion with a partial failure; they cannot produce a complete result. The helper does not stage, commit, or push archives.

## Evidence boundary

Synthetic tests and an installed-directory alias prove local behavior only. They do not prove live Discord access, exporter behavior on an actual account, plugin catalog activation, or a production run. Report those boundaries explicitly. Remote media URLs still need a network connection unless media was downloaded successfully.

The standalone organizer writes only below `<companion>/data/organized/<archive-id>/`. Runner-organized output remains under its declared `data/runs/<run-id>/` tree. Every actual output needs the matching source artifact owner, current PRIVATE proof, a committed HEAD and effective Git trackability before creation.

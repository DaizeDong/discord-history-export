# discord-history-export

Export authorized Discord history to verified HTML and JSON archives in a private Git companion.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DiscordChatExporter](https://img.shields.io/badge/Engine-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![Languages](https://img.shields.io/badge/Languages-EN%20%2F%20CN-blue?style=flat)](README_CN.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

## ⭐ Design Philosophy

An archive is useful when its files can be traced to the requested channels and opened later. DiscordChatExporter handles Discord access. This skill handles the local boundary: credentials stay in the child environment, real output belongs in a verified private Git repository, and each artifact carries its channel ID, byte count, and checksum.

Names help people navigate, but IDs define identity. The organizer preserves the exporter's ID folders and filenames, so repeated channel or thread titles stay separate and relative media links keep working. Its index lists every HTML and JSON artifact; the manifest also records channel display names and container IDs. See [PHILOSOPHY.md](PHILOSOPHY.md).

## Scope

Use an authorized bot credential for a server administered by you, or one whose administrator has granted that bot the required channel access. Select one guild or one channel, optional ISO date limits, and optional downloaded media. Guild exports include threads. The helper exports HTML and JSON sequentially and requires matching channel ID sets before reporting completion.

This is a one-shot archive helper. It does not provide continuous monitoring or access beyond the bot's permissions. For personal account data or group DMs, use Discord's official **Request my Data** feature.

## Installation

Install the plugin through your supported plugin manager, or clone the complete repository:

```bash
git clone --recurse-submodules https://github.com/DaizeDong/discord-history-export.git
```

An existing clone needs `git submodule update --init --recursive`. Missing guard code is a hard error. Install Python 3.10+, Git, and a supported [DiscordChatExporter CLI release](https://github.com/Tyrrrz/DiscordChatExporter/releases). The helper probes the supplied executable's version and export-command help before using a credential. It does not install or download an exporter.

## Private DATA and credentials

Create or use a separate **PRIVATE GitHub repository** and clone it locally. Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to a directory there; a missing child directory is created only during execution after its enclosing worktree is verified. An explicit DATA override is authoritative: empty, invalid, or disallowed selections fail without falling through to another companion. The helper uses the [shared companion interfaces](guards/COMPANION.md) for discovery and proof. Before writing, it verifies every physical and effective publication route against the local Guards visibility receipt, checks committed HEAD, and checks exact output paths and known future directories with Git's ignore rules. Prepare or refresh that receipt through the Guards visibility setup before export; the helper does not refresh it or contact GitHub. Normal and linked Git worktrees are supported. PUBLIC, UNKNOWN, missing or stale receipts, unborn repositories, ignored output paths, and the tool's own checkout are rejected.

Every configured remote's effective fetch and push destinations must identify a PRIVATE GitHub repository, including URL rewrites and selected publication remotes. Custom transports, Git routing overrides, and custom TLS trust settings are refused. The bundled shared HTTP policy checks every configuration occurrence, including URL-scoped entries and values before an empty reset; enabled certificate verification and supported performance options are allowed. Each destination proof uses one validated environment snapshot. Use canonical `https://github.com/OWNER/REPOSITORY.git` URLs. The bundled shared static SSH verifier also supports canonical `git@github.com` destinations when it recognizes the client and proves canonical routing with default trust. A missing verifier, unsupported configuration, or unproven SSH alias fails with HTTPS setup guidance. Verification never invokes SSH.

Plan, execute, resume, and completed replay check the chosen run tree and existing nested repositories before reading credentials, probing the exporter, or writing output. PUBLIC or unproven nested repositories are refused. Private linked worktrees remain valid; Git administration is excluded from archive receipts.

Keep the authorized bot credential in a local environment variable or a local file outside the public checkout. Supply only `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH` as `--credential-ref`. Credential files should have owner-only access and be excluded from version control. No credential value belongs in an assistant conversation or command line. The helper reads the value only during execution and places it in the exporter's `DISCORD_TOKEN` environment variable. Exporter stdout/stderr is captured, and raw failure output is never echoed or logged. The channel listing is saved with the credential value removed.

The current source-proven transport release is **2.47**. Its help need not spell out the environment variable; the tagged source establishes that binding. An unknown release must explicitly establish the same environment capability in its command help or preflight fails. See [credential transport evidence](skills/discord-history-export/reference/credential-transport.md).

## Plan and execute

Set `$SkillDir` to the installed `skills/discord-history-export` directory and `$Exporter` to the existing exporter executable. Run the [generated synthetic example](tests/fixtures/example.md) after substituting your authorized scope locally. `plan` validates arguments and the private destination, prints the frozen scope and commands, and does not read the credential or write output. Change `plan` to `execute` to run that scope.

Both actions accept `--guild-id` or `--channel-id`, `--after`, `--before`, `--media`, and `--resume`. Dates use ISO notation. `--run-id` must be one safe filename component. Commands work from any current directory because resources resolve from the script's canonical source location.

Output goes to `<private-data-dir>/runs/<run-id>`. `run.json` records the immutable scope, dates, media choice, exporter, and credential reference. Each attempt has its own raw files, organized archive, index, and manifest. The run-level `manifest.json` contains relative artifact paths, checksums, sizes, actual JSON message counts, and a complete file inventory.

An identical completed invocation verifies the existing files and returns without calling the exporter. A partial or failed run exits nonzero with actionable issues. Use `--resume` with the same configuration to retry into a new attempt directory while preserving prior artifacts. A changed configuration or modified existing output is rejected. This retry starts both formats again; it does not continue at an individual Discord message.

Directory access and I/O errors stop source inspection, destination checks, and completed replay. Restore access before retrying. Existing files and the last saved manifest remain intact when the full inventory cannot be recorded. If a later retry cannot reconcile that incomplete attempt, preserve the run and choose a new run ID as directed by the error.

HTML validation follows the [DiscordChatExporter 2.47 template](https://github.com/Tyrrrz/DiscordChatExporter/blob/2.47/DiscordChatExporter.Core/Exporting/PreambleTemplate.cshtml): an HTML5 doctype, closed sibling `preamble`, `chatlog`, and `postamble` sections in that order, and an `Exported N message(s)` completion entry inside the postamble. The chatlog may be empty; a completed zero-message channel is valid. Localized digit grouping and optional closing `html`/`body` tags are accepted. Zero-byte files, plain-text errors, generic service pages, and documents missing the completion footer fail validation. Markup inside text-only elements cannot supply the archive sections, and self-closing non-void elements are rejected. CSS links support escaped identifiers as well as escaped values. This checks the supported document structure; message totals still come from the JSON messages array.

The same content check runs before organization, before export completion, and when reusing a completed run. If an older run is marked complete but its HTML fails this check, preserve that run and export under a new run ID. `--resume` preserves earlier attempts for partial or failed runs; it does not rewrite a completed run's evidence.

Portable archives open directly from disk. A scheme-relative URL such as `//example.com/image.png` would inherit `file:`, so it is rejected; use an explicit `https://` or `http://` URL for remote resources. Active HTML `<base href>` elements are unsupported and rejected, including empty values. Export without a base URL so relative links keep their ordinary meaning. A `<base>` without `href`, or one inside inert template content, does not change the document base.

## Organize existing exports

The positional interface remains available:

```powershell
python "$SkillDir/scripts/reorganize.py" "$RawDir" "$OrganizedDir" "$ChannelsTxt"
```

`$ChannelsTxt` is the existing DCE channel listing. `$OrganizedDir` must be inside a verified private companion. Input filenames retain `[%c]`; DCE's `%t` folder is the category ID for a channel and parent channel ID for a thread. JSON can also establish its channel ID through `channel.id`. A supplied one-format archive is valid for the organizer; a full export requires both formats.

The organizer checks the entire source and destination set before copying. When both formats are supplied, their channel ID sets must match. It preserves source bytes and nested media, validates local links, and refuses conflicting output or a different source root. Identical reruns are idempotent. No file is overwritten to resolve a name conflict.

The destination is proved again after exporter version/help probes, before reading credentials. Existing replay files and dynamically named raw artifacts are checked for exact Git ignore status. Ignored raw artifacts remain in the private companion with a partial failure; they cannot produce a complete result. The helper does not stage, commit, or push archives.

## Verification and limits

```bash
python tools/make_fixtures.py
python -m pytest tests -q
```

The offline suite generates synthetic Discord records and intercepts exporter calls. Storage controls also use real temporary Git repositories and generated local visibility receipts; no Discord or GitHub request runs. It exercises local credentials, output boundaries, media integrity, retries, and a complete-tree installed alias. This establishes offline behavior only. It does not prove live Discord permissions, real exporter compatibility on every platform, plugin catalog activation, or unattended production operation. Media retained as remote URLs still needs network access; use `--media` for downloaded assets. An exporter error is never treated as a successful archive.

## Languages

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · Changelog · License

See [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), and [LICENSE](LICENSE) (MIT).

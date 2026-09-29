# discord-history-export

Export authorized Discord history to verified HTML and JSON archives in a private Git companion.

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-orange?style=flat)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DiscordChatExporter](https://img.shields.io/badge/Engine-DiscordChatExporter-green?style=flat)](https://github.com/Tyrrrz/DiscordChatExporter)
[![Languages](https://img.shields.io/badge/Languages-EN%20%2F%20CN-blue?style=flat)](#languages)
[![Roadmap](https://img.shields.io/badge/Roadmap-v0.1.0-purple?style=flat)](ROADMAP.md)

[English](README.md) | [中文版](README_CN.md)

## ⭐ Read this first: philosophy

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

An existing clone needs `git submodule update --init --recursive`. Missing guard code is a hard error. Install Python 3.10+, Git, authenticated GitHub CLI (`gh`), and a supported [DiscordChatExporter CLI release](https://github.com/Tyrrrz/DiscordChatExporter/releases). The helper probes the supplied executable's version and export-command help before using a credential. It does not install or download an exporter.

## Private DATA and credentials

Create or use a separate **PRIVATE GitHub repository** and clone it locally. Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to a directory there; a missing child directory is created only during execution after its enclosing worktree is verified. An explicit DATA override is authoritative: empty, invalid, or disallowed selections fail without falling through to another companion. The helper loads the [shared resolver](guards/COMPANION.md) for discovery when no DATA override is set, verifies the enclosing Git worktree and its origin, and asks `gh repo view` for fresh PRIVATE visibility before writing. Normal and linked Git worktrees are supported. A public repository, unknown visibility, an unversioned folder, or the tool's own checkout is rejected.

SSH companion origins can use an alias declared by ordinary `Host` and `HostName github.com` rules in `~/.ssh/config`. Verification reads that file locally, respects the first matching `HostName`, and never runs SSH or configured commands. Alias configurations using `Include`, `Match`, or hostname canonicalization are refused; use a literal GitHub origin for these configurations. HTTPS origins must name `github.com` directly. The resolved repository must still pass the actual PRIVATE visibility check.

Keep the authorized bot credential in a local environment variable or a local file outside the public checkout. Supply only `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH` as `--credential-ref`. Credential files should have owner-only access and be excluded from version control. No credential value belongs in an assistant conversation or command line. The helper reads the value only during execution and places it in the exporter's `DISCORD_TOKEN` environment variable. Exporter stdout/stderr is captured, and raw failure output is never echoed or logged. The channel listing is saved with the credential value removed.

The current source-proven transport release is **2.47**. Its help need not spell out the environment variable; the tagged source establishes that binding. An unknown release must explicitly establish the same environment capability in its command help or preflight fails. See [credential transport evidence](skills/discord-history-export/reference/credential-transport.md).

## Plan and execute

Set `$SkillDir` to the installed `skills/discord-history-export` directory and `$Exporter` to the existing exporter executable. Run the [generated synthetic example](tests/fixtures/example.md) after substituting your authorized scope locally. `plan` validates arguments and the private destination, prints the frozen scope and commands, and does not read the credential or write output. Change `plan` to `execute` to run that scope.

Both actions accept `--guild-id` or `--channel-id`, `--after`, `--before`, `--media`, and `--resume`. Dates use ISO notation. `--run-id` must be one safe filename component. Commands work from any current directory because resources resolve from the script's canonical source location.

Output goes to `<private-data-dir>/runs/<run-id>`. `run.json` records the immutable scope, dates, media choice, exporter, and credential reference. Each attempt has its own raw files, organized archive, index, and manifest. The run-level `manifest.json` contains relative artifact paths, checksums, sizes, actual JSON message counts, and a complete file inventory.

An identical completed invocation verifies the existing files and returns without calling the exporter. A partial or failed run exits nonzero with actionable issues. Use `--resume` with the same configuration to retry into a new attempt directory while preserving prior artifacts. A changed configuration or modified existing output is rejected. This retry starts both formats again; it does not continue at an individual Discord message.

## Organize existing exports

The positional interface remains available:

```powershell
python "$SkillDir/scripts/reorganize.py" "$RawDir" "$OrganizedDir" "$ChannelsTxt"
```

`$ChannelsTxt` is the existing DCE channel listing. `$OrganizedDir` must be inside a verified private companion. Input filenames retain `[%c]`; DCE's `%t` folder is the category ID for a channel and parent channel ID for a thread. JSON can also establish its channel ID through `channel.id`. A supplied one-format archive is valid for the organizer; a full export requires both formats.

The organizer checks the entire source and destination set before copying. When both formats are supplied, their channel ID sets must match. It preserves source bytes and nested media, validates local links, and refuses conflicting output or a different source root. Identical reruns are idempotent. No file is overwritten to resolve a name conflict.

## Verification and limits

```bash
python tools/make_fixtures.py
python -m pytest tests -q
```

The offline suite generates synthetic Discord records and intercepts exporter, Git, and GitHub CLI calls. It exercises local credentials, output boundaries, media integrity, retries, and a complete-tree installed alias. This establishes offline behavior only. It does not prove live Discord permissions, real exporter compatibility on every platform, plugin catalog activation, or unattended production operation. Media retained as remote URLs still needs network access; use `--media` for downloaded assets. An exporter error is never treated as a successful archive.

## Languages

English (`README.md`) · 中文 (`README_CN.md`)

## Roadmap · Changelog · License

See [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md), and [LICENSE](LICENSE) (MIT).

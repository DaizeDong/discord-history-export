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

Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to exactly `<companion>/data` in a separate
PRIVATE Git companion. An explicit empty or invalid selection fails; a missing
`data/` child is created only during execution after verification. Without an
override, shared companion discovery applies. Writes require committed HEAD,
current local Guards visibility proof, the declared artifact layout and effective
Git trackability. [DATA.md](DATA.md) defines route policy, nested-worktree checks,
source-owned admission and retention. The helper does not refresh the visibility
receipt, contact GitHub, or stage, commit or push archives.

Keep an authorized bot credential in a local environment variable or an owner-only
file outside the public checkout and version control. `--credential-ref` accepts
only `env:VARIABLE_NAME` or `file:ABSOLUTE_PATH`; do not put its value in a
conversation or command line. Execution passes it through the child `DISCORD_TOKEN`
environment, captures exporter output and removes the credential from saved channel
listings. Raw failure output is never echoed or logged.

[Credential transport evidence](skills/discord-history-export/reference/credential-transport.md)
defines source-proven release **2.47** and the explicit help proof required from
unknown releases. Plan and completed replay do not read credential values.

## Plan and execute

Set `$SkillDir` to the installed `skills/discord-history-export` directory and `$Exporter` to the existing exporter executable. Run the [generated synthetic example](tests/fixtures/example.md) after substituting your authorized scope locally. `plan` validates arguments and the private destination, prints the frozen scope and commands, and does not read the credential or write output. Change `plan` to `execute` to run that scope.

Both actions accept `--guild-id` or `--channel-id`, `--after`, `--before`, `--media`, and `--resume`. Dates use ISO notation. `--run-id` must be one safe filename component. Commands work from any current directory because resources resolve from the script's canonical source location.

Output goes to `<companion>/data/runs/<run-id>`. A companion root or an alternate DATA directory is rejected before exporter probes, credential reads, or output creation. `run.json` records the immutable scope, dates, media choice, exporter, and credential reference. Each attempt has its own raw files, organized archive, index, and manifest. The run-level `manifest.json` contains relative artifact paths, checksums, sizes, actual JSON message counts, and a complete file inventory.

An identical completed invocation verifies the existing files and returns without calling the exporter. A partial or failed run exits nonzero with actionable issues. Use `--resume` with the same configuration to retry into a new attempt directory while preserving prior artifacts. A changed configuration or modified existing output is rejected. This retry starts both formats again; it does not continue at an individual Discord message.

Directory access and I/O errors stop source inspection, destination checks, and completed replay. Restore access before retrying. Existing files and the last saved manifest remain intact when the full inventory cannot be recorded. If a later retry cannot reconcile that incomplete attempt, preserve the run and choose a new run ID as directed by the error.

[Archive validation](skills/discord-history-export/reference/archive-validation.md)
defines the supported DCE 2.47 HTML structure, zero-message completion, JSON counts
and portable link rules. The same validation runs during organization, completion
and completed replay. A historical completed run that fails validation must be
preserved and exported with a new run ID; `--resume` applies to incomplete runs.

## Organize existing exports

The positional interface remains available:

```powershell
python "$SkillDir/scripts/reorganize.py" "$RawDir" "$OrganizedDir" "$ChannelsTxt"
```

`$ChannelsTxt` is the existing DCE channel listing. `$OrganizedDir` must be under `<companion>/data/organized/<archive-id>/` in a verified private companion. Input filenames retain `[%c]`; DCE's `%t` folder is the category ID for a channel and parent channel ID for a thread. JSON can also establish its channel ID through `channel.id`. A supplied one-format archive is valid for the organizer; a full export requires both formats.

The organizer checks the entire source and destination set before copying. When both formats are supplied, their channel ID sets must match. It preserves source bytes and nested media, validates local links, and refuses conflicting output or a different source root. Identical reruns are idempotent. No file is overwritten to resolve a name conflict.

Source bytes, channel identities and media dependencies are defined in
[archive validation](skills/discord-history-export/reference/archive-validation.md).
Both organizer and runner use the [storage admission rules](DATA.md), including
rechecking after exporter probes and refusing ignored raw artifacts.

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

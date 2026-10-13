# Private archive data

[storage.contract.json](storage.contract.json) declares storage and retention.
The [export workflow](skills/discord-history-export/SKILL.md) defines authorized
scope and retry behavior. [Archive validation](skills/discord-history-export/reference/archive-validation.md)
defines content, identity, links and completion checks.

## Storage selection and path checks

Create or use a separate **PRIVATE GitHub repository** and clone it locally. Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to exactly `<companion>/data`; a missing child directory is created only during execution after its enclosing worktree is checked. An explicit DATA override is authoritative: empty, invalid, or disallowed selections fail without falling through to another companion. The helper uses the [shared companion resolver](guards/COMPANION.md) for discovery.

Destinations are checked by path only. The output must sit in a Git worktree found by its `.git` marker (normal and linked worktrees are supported), outside the tool's own checkout, with `data/` as the selected root, no symlinks, reparse points or hardlinked files, and no nested repository between the companion and the output. A companion directory named like the tool repository is refused. No Git or `gh` subprocess runs and no repository visibility is queried at runtime; PRIVATE publication is enforced at commit time by the Guards hooks and CI.

Plan, execute, resume, and completed replay check the chosen run tree and existing nested repositories before reading credentials, probing the exporter, or writing output. Nested repositories inside the run tree are refused; Git administration is excluded from archive receipts.

Standalone reorganize output must be one archive beneath `<companion>/data/organized/<archive-id>/` (the `standalone_archive` owner in `storage.contract.json`); the export runner's organized output must lie beneath `data/runs/<run-id>/` (the `runs` owner). Each owner's placement is a pure path check on the resolved destination: the organizer directory and every concrete output file are refused before any input is read or anything is created when they fall outside that layout, including `data/organized` itself, another archive owner's tree, or any other `data/` child. No Git command runs for this check.

New and resumed runs check the prospective organized destination before exporter probes and again before credentials. Completed replay keeps its read-only topology checks. The helper does not stage, commit, or push archives.

## Layout and retention

Contract paths are relative to the PRIVATE companion root. The selected
`data/` directory contains `runs/<run-id>/run.json`, the run manifest and immutable
attempts with raw HTML/JSON, channel mappings, organized archives, indexes and media.

Keep a selected final export or a run whose recovery or verification is still
required. A retained run includes every file required by its manifest, including
earlier attempts. Deleting just an old attempt can invalidate completed replay.
When a run has no remaining deliverable, recovery or downstream reference, review
retirement of the whole run.

The positional organizer may place selected standalone archives under
`data/organized/<archive-id>/` and their required inputs under
`data/raw/<archive-id>/`. Alternate layouts need an explicit contract entry.
Retain raw inputs only for active verification or an explicitly promised rebuild.
Never edit immutable scope or evidence merely to make validation pass.

## Maintenance

An empty installation has no real export bytes. A small existing companion may keep
its README and empty-data marker; installation alone does not justify new archives.
Credential values are outside the archive tree.

Use skill-smith's shared `storage_contract.py` for metadata inventory and reviewed
retirement. It does not replace content validation, prove live Discord access or
authorize an export. Confirm no exporter or organizer is active before removal.
These rules do not schedule deletion or erase Git history.

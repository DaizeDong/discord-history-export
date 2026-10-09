# Private archive data

[storage.contract.json](storage.contract.json) declares storage and retention.
The [export workflow](skills/discord-history-export/SKILL.md) defines authorized
scope and retry behavior. [Archive validation](skills/discord-history-export/reference/archive-validation.md)
defines content, identity, links and completion checks.

## Storage selection and proof

Create or use a separate **PRIVATE GitHub repository** and clone it locally. Set `DISCORD_HISTORY_EXPORT_DATA_DIR` to exactly `<companion>/data`; a missing child directory is created only during execution after its enclosing worktree is verified. An explicit DATA override is authoritative: empty, invalid, or disallowed selections fail without falling through to another companion. The helper uses the [shared companion interfaces](guards/COMPANION.md) for discovery and proof. Before writing, it verifies every physical and effective publication route against the local Guards visibility receipt, checks committed HEAD, and checks exact output paths and known future directories with Git's ignore rules. Prepare or refresh that receipt through the Guards visibility setup before export; the helper does not refresh it or contact GitHub. Normal and linked Git worktrees are supported. PUBLIC, UNKNOWN, missing or stale receipts, unborn repositories, ignored output paths, and the tool's own checkout are rejected.

Every configured remote's effective fetch and push destinations must identify a PRIVATE GitHub repository, including URL rewrites and selected publication remotes. Custom transports, Git routing overrides, and custom TLS trust settings are refused. The bundled shared HTTP policy checks every configuration occurrence, including URL-scoped entries and values before an empty reset; enabled certificate verification and supported performance options are allowed. Each destination proof uses one validated environment snapshot. Use canonical `https://github.com/OWNER/REPOSITORY.git` URLs. The bundled shared static SSH verifier also supports canonical `git@github.com` destinations when it recognizes the client and proves canonical routing with default trust. A missing verifier, unsupported configuration, or unproven SSH alias fails with HTTPS setup guidance. Verification never invokes SSH.

Plan, execute, resume, and completed replay check the chosen run tree and existing nested repositories before reading credentials, probing the exporter, or writing output. PUBLIC or unproven nested repositories are refused. Private linked worktrees remain valid; Git administration is excluded from archive receipts.

Standalone reorganize output must be one archive beneath `<companion>/data/organized/<archive-id>` and binds to `standalone_archive`. The export runner explicitly uses the separate `runs` owner beneath `data/runs/<run-id>/`. Organizer directories and every concrete output file are admitted through the canonical source storage contract before creation; source declarations never authorize arbitrary PRIVATE destinations. Lexical topology, current complete-route PRIVATE proof, committed HEAD, retention and effective ignore rules all remain enforced.

New and resumed runs check the prospective organized destination before exporter probes and again before credentials. A nested PRIVATE worktree must still own the exact declared layout. Completed replay keeps its read-only topology checks and does not request write admission.

The destination is proved again after exporter version/help probes, before reading credentials. Existing replay files and dynamically named raw artifacts are checked for exact Git ignore status. Ignored raw artifacts remain in the private companion with a partial failure; they cannot produce a complete result. The helper does not stage, commit, or push archives.

## Layout and retention

Contract paths are relative to the verified PRIVATE companion root. The selected
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

# Private archive data

[storage.contract.json](storage.contract.json) declares storage and retention.
The [export workflow](skills/discord-history-export/SKILL.md) and its existing
manifest validators remain authoritative for scope, content and completion.

Paths are relative to the verified PRIVATE companion. `DISCORD_HISTORY_EXPORT_DATA_DIR`
must select exactly its `data/` directory; the workflow rejects alternate roots before
exporter probes, credential reads or writes. The data root contains `runs/<run-id>/run.json`, the run manifest, and immutable attempts with
raw HTML/JSON, channel mappings, organized archives, indexes and media.
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

An empty installation has no real export bytes. A small existing companion may keep
its README and empty-data marker; installation alone does not justify new archives.
Credential values are outside the archive tree.

Use skill-smith's shared `storage_contract.py` for metadata inventory and reviewed
retirement. It does not replace content validation, prove live Discord access or
authorize an export. Confirm no exporter or organizer is active before removal.
These rules do not schedule deletion or erase Git history.

Standalone reorganize output must be one archive beneath `<companion>/data/organized/<archive-id>` and binds to `standalone_archive`. The export runner explicitly uses the separate `runs` owner beneath `data/runs/<run-id>/`. Organizer directories and every concrete output file are admitted through the canonical source storage contract before creation; source declarations never authorize arbitrary PRIVATE destinations. Lexical topology, current complete-route PRIVATE proof, committed HEAD, retention and effective ignore rules all remain enforced.

New and resumed runs check the prospective organized destination before exporter probes and again before credentials. A nested PRIVATE worktree must still own the exact declared layout. Completed replay keeps its read-only topology checks and does not request write admission.

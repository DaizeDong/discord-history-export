# Changelog

All notable changes to this project are documented here (Keep a Changelog style).

## [Unreleased]

### Changed
- Raised the companion working-data review threshold from 64 MiB to 256 MiB so a full guild export (raw HTML and JSON under `data/raw/<archive>/`) fits one retained archive.
- Removed the `guards` and `style` submodules and the `pii-guard`, `dash-guard`, `doc-contract`, `load-budget` and `fleet-sync` workflows. The `.githooks` shims run the local fleet-guards and fleet-style checkouts named by `git config fleet.guards` and `fleet.style` and block when either is unset. `export_core` resolves the companion through `fleet_guards.runtime.companion_resolver`.
- Deleted the test suite, its fixture generator and the CI workflow that ran it; the README example is now inline.
- Destination checks are one pass: `private_destination` returns the target and its companion root (the nearest `.git` marker outside this checkout), and drops the always-true containment test, the post-check re-resolve and the refusal of a companion that sits inside another checkout. `private_topology` walks the tree once, checking links per entry and refusing a nested repository below the companion root, instead of re-running the full destination check for every entry. `execute` refuses a run directory that belongs to a different repository than `data/`. The manifest `companion` field remains the companion directory name. The source11 test harness no longer emulates Git.
- Removed the runtime PRIVATE proof. `export_core.py` no longer calls `prove_private_companion`, `read_private_companion_git` (HEAD and `check-ignore`) or `authorize_artifact_write`, and no longer refuses Git, proxy or TLS environment overrides. Destinations are checked by path only: inside a Git worktree found by its `.git` marker, `data/` as the selected root, outside this checkout, no links or nested repositories; no subprocess runs. Manifests record the companion directory name instead of a GitHub slug. PRIVATE publication is enforced at commit time by the Guards hooks and CI. Proof-only tests (`tests/test_ssh_alias.py`, route and visibility cases, the transport-environment conftest) and their fixture generators were removed; the native storage fixture was regenerated.
- Archive placement is enforced again as a pure path check: `authorize_archive` refuses any resolved destination outside its owner's layout (`standalone_archive` under `data/organized/<archive-id>/`, `runs` under `data/runs/<run-id>/`) and unknown owners, before inputs are read and with no subprocess. Restored the wrong-owner negative tests.
- Bind concrete runtime writer destinations and transaction files to canonical source artifact admission before creation. Offline regression controls preserve PRIVATE, retention, topology and versioning refusals.
- Set a 64 MiB companion working-data review threshold. Required observations and
  recovery state stay protected when the threshold is exceeded.
- Credentials use local `env:` or `file:` references and reach the exporter through its child environment. Planning and completed replay do not read credential values. This supersedes the historical browser-driven capture workflow.
- Exports retain immutable scope, separate attempts, ID-preserving HTML/JSON archives, local media links, inventory and checksum receipts in a verified PRIVATE Git companion. Completed replay verifies existing artifacts; partial retries preserve previous attempts and rerun both formats.
- Boundary checks reject unproved publication routes, ignored output, nested public repositories and I/O failures before completion. The helper does not stage, commit or push archives.

### Fixed
- Require the declared companion data/ root before exporter probes, credential reads or output writes. Declare configuration applicability as runtime storage only.
- Companion maintenance points to the pinned `guards/tools/datadir.py` resolver and current run/attempt recovery contract.

## [0.1.0] - 2026-06-24

### Changed
- Deleted the test suite, its fixture generator and the CI workflow that ran it; the README example is now inline.
- docs: unify repo structure (Skill Repo Spec v1)

### Added
- Initial release: guild-wide Discord history export (HTML + JSON), Playwright-driven token/guild-ID capture, Python reorganize into readable category/channel layout, and encoded fixes for known DiscordChatExporter gotchas.

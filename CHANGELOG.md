# Changelog

All notable changes to this project are documented here (Keep a Changelog style).

## [Unreleased]

### Changed
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
- docs: unify repo structure (Skill Repo Spec v1)

### Added
- Initial release: guild-wide Discord history export (HTML + JSON), Playwright-driven token/guild-ID capture, Python reorganize into readable category/channel layout, and encoded fixes for known DiscordChatExporter gotchas.

# Changelog

All notable changes to this project are documented here (Keep a Changelog style).

## [Unreleased]

### Changed
- Honor explicit DATA directory selection before write-side discovery; reject invalid overrides without falling through and support missing children beneath verified private worktrees.
- Add a local plan/execute helper with credential references and verified private Git output.
- Preserve stable channel and container IDs, source bytes, media links, and checksummed manifests.
- Freeze run configuration and retain earlier attempts when retrying incomplete exports.
- Align both README languages and plugin instructions with the authorized bot workflow and offline validation boundary.

### Added
- Generator-backed synthetic regressions for archive integrity, boundary failures, credentials, and retries.

## [0.1.0] - 2026-06-24

### Changed
- docs: unify repo structure (Skill Repo Spec v1)

### Added
- Initial release: guild-wide Discord history export (HTML + JSON), Playwright-driven token/guild-ID capture, Python reorganize into readable category/channel layout, and encoded fixes for known DiscordChatExporter gotchas.

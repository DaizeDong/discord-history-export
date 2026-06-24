# Roadmap

Current: **v0.1.0**

## v0.1.0 (current)

- Guild-wide export via Tyrrrz/DiscordChatExporter, HTML + JSON outputs
- Headed-browser token + guild-ID capture via Playwright MCP (no DevTools)
- Python reorganize step: Discord-ID folders → readable `<Category>/<channel>.html` tree
- Encoded fixes for five known DCE gotchas (template `%t`, duplicate thread titles, Git Bash paths, forum channels, forbidden channels)
- ToS risk surfaced before token capture; Bot hand-off for admins; GDPR route for Group DMs

## Planned

- Single-channel and single-thread export shortcuts
- Cross-platform DCE release auto-selection (macOS / Linux defaults)
- Incremental / resume export to avoid re-downloading unchanged history
- Optional token-redaction pass over the conversation transcript

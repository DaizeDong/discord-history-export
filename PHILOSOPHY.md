# Philosophy

DiscordChatExporter owns the network export. This skill owns the local handoff: keep authorization narrow, keep credentials local, and make archive completeness inspectable.

A name can change or collide. A Discord ID defines which channel, category, or thread a file belongs to. Preserve those IDs and source bytes through organization, and verify relative media links before reporting success.

An exporter exit code is one piece of evidence. Completion also requires the requested formats, matching channel identities, usable local links, and byte-level receipts. Failure keeps its artifacts and an actionable status; retries preserve the prior attempt.

Public code is an uninitialized tool. Generated examples are synthetic. Real archives and run history belong in a separate, verified private Git repository, with credentials excluded from version control.

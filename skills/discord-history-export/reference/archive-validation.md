# Archive validation and completion

The exporter runner requires both HTML and JSON with matching channel ID sets.
The standalone organizer can validate one explicitly supplied format. An exporter
exit code alone does not establish completion. Storage and write admission are
defined in [DATA.md](../../../DATA.md); credential transport is described in
[credential-transport.md](credential-transport.md).

## Channel identity and receipts

The organizer preserves source bytes, ID folders, repeated-title identities, and nested media links. It writes `INDEX.md` plus a manifest with every source/destination path, channel ID, byte count, and SHA-256. JSON contributes counts from its actual `messages` array. A single-format input is complete for that explicitly supplied archive; mixed formats must have matching channel ID sets. Conflicts, unidentified files, broken local links, and changed input are rejected before copying; nothing is overwritten to resolve a collision.

DCE filenames retain `[%c]`; `%t` is the category ID for a channel and parent
channel ID for a thread. JSON may establish identity through `channel.id`.
The index lists every HTML and JSON artifact; the manifest also records channel
display names and container IDs.

## HTML structure and portable links

HTML validation follows the [DiscordChatExporter 2.47 template](https://github.com/Tyrrrz/DiscordChatExporter/blob/2.47/DiscordChatExporter.Core/Exporting/PreambleTemplate.cshtml): an HTML5 doctype, closed sibling `preamble`, `chatlog`, and `postamble` sections in that order, and an `Exported N message(s)` completion entry inside the postamble. The chatlog may be empty; a completed zero-message channel is valid. Localized digit grouping and optional closing `html`/`body` tags are accepted. Zero-byte files, plain-text errors, generic service pages, and documents missing the completion footer fail validation. Markup inside text-only elements cannot supply the archive sections, and self-closing non-void elements are rejected. CSS links support escaped identifiers as well as escaped values. This checks the supported document structure; message totals still come from the JSON messages array.

The same content check runs before organization, before export completion, and when reusing a completed run. If an older run is marked complete but its HTML fails this check, preserve that run and export under a new run ID. `--resume` preserves earlier attempts for partial or failed runs; it does not rewrite a completed run's evidence.

Portable archives open directly from disk. A scheme-relative URL such as `//example.com/image.png` would inherit `file:`, so it is rejected; use an explicit `https://` or `http://` URL for remote resources. Active HTML `<base href>` elements are unsupported and rejected, including empty values. Export without a base URL so relative links keep their ordinary meaning. A `<base>` without `href`, or one inside inert template content, does not change the document base.

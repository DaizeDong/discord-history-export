"""Private output boundaries and byte-preserving Discord archive validation."""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import unquote, urlsplit, quote

SOURCE_ROOT = Path(__file__).resolve().parents[3]
SKILL = "discord-history-export"
NUMERIC_ID = re.compile(r"[0-9]{1,25}\Z")
FILE_ID = re.compile(r"\[([0-9]{1,25})\](?:\.[^.]+)?\Z")


class ExportError(RuntimeError):
    """An actionable diagnostic containing no external command output."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def contains(parent, child):
    return child == parent or parent in child.parents


def load_resolver():
    path = SOURCE_ROOT / "guards" / "tools" / "datadir.py"
    if not path.is_file():
        raise ExportError("Missing guards submodule. Run git submodule update --init --recursive in the source checkout.")
    spec = importlib.util.spec_from_file_location("discord_export_guard_datadir", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The pinned resolver treats every .git file as a submodule. Give it the known consumer
    # anchor so a linked source worktree retains sibling discovery and own-repo rejection.
    module._own_repo_root = lambda: str(SOURCE_ROOT)
    return module


def command_text(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise ExportError("Cannot verify private Git output. Install Git and authenticate gh, then retry.") from None
    if result.returncode:
        raise ExportError("Cannot verify private Git output. Check the companion origin and gh access.")
    return result.stdout.strip()


def _ssh_hostname(alias):
    """Read ordinary user Host/HostName rules without invoking SSH or commands."""
    try:
        lines = (Path.home()/'.ssh/config').read_text(encoding='utf-8').splitlines()
        active, hostname = True, None
        for line in lines:
            tokens = shlex.split(re.sub(r'^(\s*\w+)\s*=\s*', r'\1 ', line), comments=True)
            if not tokens:
                continue
            keyword, values = tokens[0].lower(), tokens[1:]
            if keyword in {'include', 'match'} or keyword.startswith('canonicalize') or keyword == 'canonicaldomains':
                raise ExportError('SSH alias verification supports only ordinary Host/HostName rules')
            if keyword == 'host':
                if not values:
                    raise ExportError('SSH Host rule has no patterns')
                positive, negated = False, False
                for pattern in values:
                    expression = re.escape(pattern.removeprefix('!').lower()).replace(r'\*', '.*').replace(r'\?', '.')
                    if re.fullmatch(expression, alias.lower()):
                        if pattern.startswith('!'):
                            negated = True
                        else:
                            positive = True
                active = positive and not negated
            elif keyword == 'hostname':
                if len(values) != 1:
                    raise ExportError('SSH HostName rule must contain one hostname')
                if active and hostname is None:
                    hostname = values[0].lower()
        return hostname
    except (OSError, ValueError) as exc:
        raise ExportError('cannot resolve SSH alias from ordinary user SSH configuration') from exc


def _github_identity(origin):
    match = re.fullmatch(
        r"(?:https://github\.com/|git@(?P<scp>[^@/:\s]+):|ssh://git@(?P<ssh>[^@/:\s]+)/)"
        r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?", origin)
    if not match:
        raise ExportError("Companion origin is not a verifiable GitHub repository. Set its origin and retry.")
    host = match.group("scp") or match.group("ssh")
    if host and host != "github.com" and _ssh_hostname(host) != "github.com":
        raise ExportError("Companion SSH alias must resolve to github.com for visibility verification.")
    return match.group("slug")


def private_destination(path):
    """Require the actual enclosing worktree, including linked Git worktrees, to be PRIVATE."""
    load_resolver()
    target = Path(path).expanduser().resolve()
    if contains(SOURCE_ROOT, target):
        raise ExportError("Output cannot be inside the tool's own source checkout. Select its private companion.")
    ancestor = target
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ExportError("Output parent must be a directory in a private Git companion.")
    root_text = command_text(["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"])
    if not root_text:
        raise ExportError("Output has no proven enclosing Git worktree.")
    root = Path(root_text).resolve()
    if not contains(root, target) or not (root / ".git").exists():
        raise ExportError("Output has no proven enclosing Git worktree.")
    if contains(SOURCE_ROOT, root) or contains(root, SOURCE_ROOT):
        raise ExportError("The tool's consumer worktree cannot also be the DATA companion.")
    origin = command_text(["git", "-C", str(root), "config", "--get", "remote.origin.url"])
    slug = _github_identity(origin)
    if slug.rsplit("/", 1)[-1].lower() == SKILL:
        raise ExportError("A source repository cannot also be the DATA companion.")
    try:
        proof = json.loads(command_text(["gh", "repo", "view", slug, "--json", "visibility"]))
    except (ValueError, TypeError):
        raise ExportError("Companion visibility could not be verified; no output was written.") from None
    if not isinstance(proof, dict) or proof.get("visibility") != "PRIVATE":
        raise ExportError("Output requires verified PRIVATE repository visibility; PUBLIC and UNKNOWN are denied.")
    return target, slug


def resolve_data_dir():
    resolver = load_resolver()
    selected = os.environ.get("DISCORD_HISTORY_EXPORT_DATA_DIR")
    if selected is not None:
        if not selected.strip():
            raise ExportError("DISCORD_HISTORY_EXPORT_DATA_DIR is empty. Select a directory in a private Git companion.")
        # Read discovery may skip absent paths; a writer must honor the explicit selection.
        return private_destination(selected)
    try:
        path = resolver.resolve_data_dir(SKILL, create=False)
    except RuntimeError:
        raise ExportError("Private DATA is not initialized. Set DISCORD_HISTORY_EXPORT_DATA_DIR to a directory in a private Git companion.") from None
    if path is None:
        raise ExportError("Private DATA is not initialized. Set DISCORD_HISTORY_EXPORT_DATA_DIR to a directory in a private Git companion.")
    return private_destination(path)


def files_under(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ExportError("Archive source is not a readable directory.")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not contains(root, path.resolve()):
            raise ExportError("Archive trees cannot contain symlinks or paths outside their root.")
        if path.is_file():
            files.append(path)
    return files


def parse_channels(path):
    if path is None:
        return {}
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        raise ExportError("Channel listing must be a readable UTF-8 text file.") from None
    result = {}
    for line in text.splitlines():
        if "|" not in line:
            continue
        channel_id, display = (part.strip() for part in line.split("|", 1))
        if not NUMERIC_ID.fullmatch(channel_id):
            continue
        if channel_id in result and result[channel_id] != display:
            raise ExportError("Channel listing contains conflicting names for the same stable ID.")
        result[channel_id] = display
    return result


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.in_stylesheet = False

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            media_type = (dict(attrs).get("type") or "text/css").strip().lower()
            self.in_stylesheet = media_type in ("", "text/css")
        for name, value in attrs:
            if value and name in ("src", "href", "poster"):
                self.links.append(value)
            elif value and name == "srcset":
                self.links.extend(part.strip().split()[0] for part in value.split(",") if part.strip())
            elif value and name == "style":
                self.links.extend(css_links(value))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_stylesheet = False

    def handle_data(self, data):
        if self.in_stylesheet:
            self.links.extend(css_links(data))


def css_links(text):
    """Extract literal url() references outside CSS comments and string values."""
    url = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
    links = []
    index = 0
    while index < len(text):
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if text[index] in "'\"":
            quote = text[index]
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                elif text[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            continue
        boundary = index == 0 or not (text[index - 1].isalnum() or text[index - 1] in "_-\\")
        match = url.match(text, index) if boundary else None
        if match:
            links.append(match.group(2))
            index = match.end()
        else:
            index += 1
    return links


def json_links(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and key.lower().endswith("url"):
                yield item
            else:
                yield from json_links(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_links(item)


def local_target(root, parent, link):
    try:
        parts = urlsplit(link)
    except ValueError:
        raise ExportError("Archive contains a malformed media URL.") from None
    if parts.scheme in ("http", "https", "data", "mailto", "tel", "javascript", "about") or parts.netloc:
        return None
    if not parts.path:
        return None
    decoded = unquote(parts.path).replace("\\", "/")
    if parts.scheme or decoded.startswith("/") or re.match(r"^[A-Za-z]:", decoded):
        raise ExportError("Archive contains an absolute local link; use portable relative media links.")
    target = (parent / decoded).resolve()
    if not contains(root, target) or not target.is_file():
        raise ExportError("Archive contains a missing or escaping local media link. Re-export with --media and retry.")
    return target


def inspect_archive(root, *, allow_empty=False):
    """Validate all identities and links before choosing any destination or writing a byte."""
    root = Path(root).resolve()
    files = files_under(root)
    blobs = {path: path.read_bytes() for path in files}
    identities, links, entries = {}, {}, []
    seen = set()
    for path in files:
        asset_dir = any(part.lower().endswith("_files") or part.lower() in ("media", "attachments")
                        for part in path.relative_to(root).parts[:-1])
        fmt = path.suffix.lower().lstrip(".")
        if asset_dir or fmt not in ("html", "json"):
            continue
        match = FILE_ID.search(path.name)
        channel_id = match.group(1) if match else None
        message_count = 0
        data = None
        try:
            text = blobs[path].decode("utf-8-sig")
            if fmt == "json":
                data = json.loads(text)
                json_id = str(data["channel"]["id"])
                if not NUMERIC_ID.fullmatch(json_id) or not isinstance(data["messages"], list):
                    raise ValueError
                if channel_id and channel_id != json_id:
                    raise ExportError("JSON channel identity disagrees with its filename ID.")
                channel_id = json_id
                message_count = len(data["messages"])
                refs = list(json_links(data))
            else:
                parser = LocalLinks()
                parser.feed(text)
                parser.close()
                refs = parser.links
        except (UnicodeError, ValueError, KeyError, TypeError):
            raise ExportError("Archive HTML/JSON is malformed or lacks channel/messages metadata.") from None
        if not channel_id:
            raise ExportError("Every HTML archive needs a numeric channel ID in its filename; JSON needs channel.id.")
        if (channel_id, fmt) in seen:
            raise ExportError("Archive contains multiple exports for one channel ID and format; use separate runs.")
        seen.add((channel_id, fmt))
        identities[path] = {channel_id}
        links[path] = [target for ref in refs if (target := local_target(root, path.parent, ref)) is not None]
        container = next((part for part in reversed(path.relative_to(root).parts[:-1])
                          if NUMERIC_ID.fullmatch(part)), None)
        entry = {"channel_id": channel_id, "format": fmt,
                 "source": path.relative_to(root).as_posix(), "message_count": message_count}
        if container:
            entry["container_id"] = container
        if data:
            for key in ("categoryId", "parentId"):
                value = data["channel"].get(key)
                if value is not None:
                    if not NUMERIC_ID.fullmatch(str(value)):
                        raise ExportError("JSON contains malformed category or parent IDs.")
                    entry[key] = str(value)
            guild = data.get("guild")
            if isinstance(guild, dict) and guild.get("id") is not None:
                entry["guild_id"] = str(guild["id"])
        entries.append(entry)
    if not entries and not allow_empty:
        raise ExportError("No identified HTML or JSON archives were produced.")
    pending = list(links)
    while pending:
        source = pending.pop()
        for target in links.get(source, []):
            owners = identities.setdefault(target, set())
            additions = identities[source] - owners
            if additions:
                owners.update(additions)
                if target.suffix.lower() == ".css":
                    refs = css_links(blobs[target].decode("utf-8-sig"))
                    links[target] = [p for ref in refs if (p := local_target(root, target.parent, ref))]
                pending.append(target)
    artifact_sources = {entry["source"] for entry in entries}
    known_ids = {entry["channel_id"] for entry in entries}
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel in artifact_sources:
            continue
        owners = identities.get(path, set())
        if not owners:
            for part in path.relative_to(root).parts:
                owners.update(i for i in re.findall(r"\[([0-9]{1,25})\]", part) if i in known_ids)
        if not owners:
            raise ExportError("A media asset has no stable channel identity or referring archive.")
        entries.append({"channel_id": sorted(owners)[0], "channel_ids": sorted(owners), "format": "media", "source": rel})
    by_source = {entry["source"]: entry for entry in entries}
    destination_keys = set()
    for entry in entries:
        source = root / entry["source"]
        destination = Path(entry["source"])
        if entry["format"] != "media" and not FILE_ID.search(destination.name):
            destination = destination.with_name(f"{destination.stem} [{entry['channel_id']}]{destination.suffix}")
        entry["path"] = (Path("archive") / destination).as_posix()
        key = entry["path"].casefold()
        if key in destination_keys:
            raise ExportError("Archive paths conflict on a case-insensitive filesystem.")
        destination_keys.add(key)
        entry.update(size_bytes=len(blobs[source]), sha256=digest(blobs[source]))
    for key in destination_keys:
        parts = key.split("/")
        if any("/".join(parts[:length]) in destination_keys for length in range(1, len(parts))):
            raise ExportError("Archive paths conflict: a planned file would also be a directory.")
    for source, targets in links.items():
        source_entry = by_source[source.relative_to(root).as_posix()]
        for target in targets:
            relative = os.path.relpath(target, source.parent)
            expected = (Path(source_entry["path"]).parent / relative).as_posix()
            actual = by_source[target.relative_to(root).as_posix()]["path"]
            if os.path.normpath(expected) != os.path.normpath(actual):
                raise ExportError("Identity normalization would break a local media link; keep IDs in source filenames.")
    return sorted(entries, key=lambda entry: entry["source"])


def summarize(entries):
    return {"artifact_count": len(entries),
            "html_count": sum(a["format"] == "html" for a in entries),
            "json_count": sum(a["format"] == "json" for a in entries),
            "media_count": sum(a["format"] == "media" for a in entries),
            "message_count": sum(a.get("message_count", 0) for a in entries if a["format"] == "json")}


def validate_channel_sets(entries, *, require_both=False):
    html_ids = {a["channel_id"] for a in entries if a["format"] == "html"}
    json_ids = {a["channel_id"] for a in entries if a["format"] == "json"}
    if (require_both and (not html_ids or not json_ids)) or (html_ids and json_ids and html_ids != json_ids):
        raise ExportError("HTML and JSON channel ID sets are empty or differ. Produce both formats for the same channels.")
    return json_ids


def organize(raw, destination, channels_file):
    raw = Path(raw).resolve()
    destination, companion = private_destination(destination)
    if contains(raw, destination) or contains(destination, raw):
        raise ExportError("Raw and organized archives must be separate, non-overlapping directories.")
    channels = parse_channels(channels_file)
    entries = inspect_archive(raw)
    validate_channel_sets(entries)
    manifest = {"schema_version": 1, "status": "complete", "run_id": destination.name,
                "input": {"root": str(raw), "channels_sha256": digest(Path(channels_file).read_bytes())},
                "companion": companion, "channels": channels, "artifacts": entries,
                "summary": summarize(entries), "issues": []}
    output = {entry["path"]: (raw / entry["source"]).read_bytes() for entry in entries}
    if any(digest(output[entry["path"]]) != entry["sha256"] for entry in entries):
        raise ExportError("Raw source changed during validation. Retry from an immutable source snapshot.")
    output["manifest.json"] = json_bytes(manifest)
    index = "# Discord archive\n\n" + "\n".join(
        f"- [{entry['channel_id']} ({entry['format']})]({quote(entry['path'])})"
        for entry in entries if entry["format"] != "media")
    index += "\n\n" + json.dumps(manifest["summary"], sort_keys=True) + "\n"
    output["INDEX.md"] = index.encode("utf-8")
    if destination.exists():
        existing = {p.relative_to(destination).as_posix(): p.read_bytes() for p in files_under(destination)}
        if existing:
            if existing != output:
                raise ExportError("Existing output differs from this immutable input. Choose a new organized directory.")
            return manifest
        if any(destination.iterdir()):
            raise ExportError("Existing output contains unrelated directories. Choose an empty destination.")
    for relative, content in output.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    return manifest

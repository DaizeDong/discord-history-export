"""Private output boundaries and byte-preserving Discord archive validation."""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from types import MappingProxyType
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


def command_text(argv, environment=None):
    environment = dict(_transport_environment() if environment is None else environment)
    _check_transport_environment(environment)
    controlled = {"GIT_OPTIONAL_LOCKS", "GH_HOST", "GH_PROMPT_DISABLED"}
    environment = {key: value for key, value in environment.items() if key.upper() not in controlled}
    environment.update(GIT_OPTIONAL_LOCKS="0", GH_HOST="github.com", GH_PROMPT_DISABLED="1")
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=30, env=environment)
    except (OSError, subprocess.SubprocessError):
        raise ExportError("Cannot verify private Git output. Install Git and authenticate gh, then retry.") from None
    if result.returncode:
        raise ExportError("Cannot verify private Git output. Check the companion origin and gh access.")
    return result.stdout.strip()


def _check_transport_environment(environment=None):
    environment = os.environ if environment is None else environment
    for key, value in environment.items():
        upper = key.upper()
        if (upper.startswith("GIT_") and upper != "GIT_OPTIONAL_LOCKS") or upper in {
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "SSH_COMMAND",
                "SSL_CERT_FILE", "SSL_CERT_DIR", "CURL_CA_BUNDLE", "CURL_SSL_BACKEND"}:
            raise ExportError("Git, proxy, or TLS trust environment overrides prevent private destination proof. Clear overrides and retry.")
        if upper == "GH_HOST" and value.lower() != "github.com":
            raise ExportError("Private destination verification requires the github.com authority.")


def _transport_environment():
    environment = dict(os.environ)
    _check_transport_environment(environment)
    return MappingProxyType(environment)


def _check_ssh_configuration():
    """Use the shared static verifier; unsupported installed pins fail before SSH activity."""
    path = SOURCE_ROOT / "guards" / "tools" / "data_boundary.py"
    message = "SSH destination proof requires the shared static verifier. Use canonical GitHub HTTPS remotes."
    if not path.is_file():
        raise ExportError(message)
    try:
        spec = importlib.util.spec_from_file_location("discord_export_shared_boundary", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verifier = getattr(module, "_ssh_configuration_problem", None)
        if not callable(verifier) or verifier() is not None:
            raise ExportError(message)
    except Exception:
        raise ExportError(message) from None


def _check_https_configuration(settings, environment):
    """Apply the shared policy to every config occurrence and the proof's snapshot."""
    path = SOURCE_ROOT / "guards" / "tools" / "data_boundary.py"
    message = "Private publication proof requires the shared static HTTPS verifier and supported HTTP configuration."
    if not path.is_file():
        raise ExportError(message)
    try:
        spec = importlib.util.spec_from_file_location("discord_export_shared_boundary", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        verifier = getattr(module, "_https_configuration_problem", None)
        if not callable(verifier) or verifier(settings, environment) is not None:
            raise ExportError(message)
    except Exception:
        raise ExportError(message) from None


def _github_identity(origin):
    match = re.fullmatch(
        r"(?P<transport>https://github\.com/|git@github\.com:|ssh://git@github\.com(?::22)?/)"
        r"(?P<slug>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*?)(?:\.git)?/?", origin)
    if not match:
        raise ExportError("Destination is not canonical GitHub HTTPS or git@github.com SSH. Use canonical HTTPS remotes.")
    if not match.group("transport").startswith("https:"):
        _check_ssh_configuration()
    return match.group("slug")


def _publication_destinations(root, environment):
    prefix = ["git", "-C", str(root)]
    raw = command_text([*prefix, "config", "--null", "--list"], environment)
    settings = []
    for record in raw.split("\0"):
        if not record:
            continue
        key, separator, value = record.partition("\n")
        if not separator:
            raise ExportError("Effective Git configuration could not be read unambiguously.")
        settings.append((key.lower(), value))
    _check_https_configuration(settings, environment)
    remotes = command_text([*prefix, "remote"], environment).splitlines()
    if not remotes or len(set(remotes)) != len(remotes) or any(
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", name) for name in remotes):
        raise ExportError("Companion publication remotes are absent or ambiguous.")
    for key, value in settings:
        custom_transport = key in {"core.sshcommand", "core.gitproxy", "ssh.variant"} or (
            key.startswith("remote.") and key.rsplit(".", 1)[-1] in {"vcs", "proxy", "uploadpack", "receivepack"})
        if custom_transport:
            raise ExportError("Custom Git transport configuration prevents private publication proof.")
        selected_remote = key == "remote.pushdefault" or (
            key.startswith("branch.") and key.rsplit(".", 1)[-1] in {"remote", "pushremote"})
        if selected_remote and value not in remotes:
            raise ExportError("A selected publication remote has no verifiable configured destination.")
    destinations = []
    for remote in remotes:
        for options in ([], ["--push"]):
            urls = command_text([*prefix, "remote", "get-url", *options, "--all", remote], environment).splitlines()
            if not urls or any(not url.strip() for url in urls):
                raise ExportError("A publication remote has no provable effective URL.")
            destinations.extend(_github_identity(url) for url in urls)
    return list(dict.fromkeys(destinations))


def destination_path(path):
    target = Path(path).expanduser().absolute()
    for node in (target, *target.parents):
        try:
            info = node.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ExportError("Output topology cannot contain symlinks or reparse points.")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ExportError("Output topology cannot contain hardlinked files.")
    return target.resolve()


def private_destination(path):
    """Require the actual enclosing worktree, including linked Git worktrees, to be PRIVATE."""
    load_resolver()
    environment = _transport_environment()
    target = destination_path(path)
    if contains(SOURCE_ROOT, target):
        raise ExportError("Output cannot be inside the tool's own source checkout. Select its private companion.")
    ancestor = target.parent if target.is_file() else target
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ExportError("Output parent must be a directory in a private Git companion.")
    root_text = command_text(["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"], environment)
    if not root_text:
        raise ExportError("Output has no proven enclosing Git worktree.")
    root = Path(root_text).resolve()
    if not contains(root, target) or not (root / ".git").exists():
        raise ExportError("Output has no proven enclosing Git worktree.")
    if contains(SOURCE_ROOT, root) or contains(root, SOURCE_ROOT):
        raise ExportError("The tool's consumer worktree cannot also be the DATA companion.")
    destinations = _publication_destinations(root, environment)
    for slug in destinations:
        if slug.rsplit("/", 1)[-1].lower() == SKILL:
            raise ExportError("A source repository cannot also be the DATA companion.")
        try:
            proof = json.loads(command_text(["gh", "repo", "view", "https://github.com/" + slug,
                                             "--json", "visibility,nameWithOwner"], environment))
        except (ValueError, TypeError):
            raise ExportError("Companion visibility could not be verified; no output was written.") from None
        if (not isinstance(proof, dict) or proof.get("visibility") != "PRIVATE"
                or str(proof.get("nameWithOwner", "")).casefold() != slug.casefold()):
            raise ExportError("Every effective publication destination requires verified PRIVATE visibility and identity.")
    return target, destinations[0]


def enumeration_error(error):
    raise ExportError("Directory enumeration failed. Restore directory access and retry.") from error


def private_topology(path):
    """Prove the chosen tree before reading credentials, probing exporters, or writing."""
    target, companion = private_destination(path)
    if target.is_dir():
        for directory, dirs, files in os.walk(target, followlinks=False, onerror=enumeration_error):
            current = Path(directory)
            for name in dirs + files:
                destination_path(current / name)
            if current != target and (current / ".git").exists():
                private_destination(current)
            dirs[:] = [name for name in dirs if name != ".git"]
    return target, companion


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
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=enumeration_error):
        for name in dirs + names:
            path = Path(directory) / name
            destination_path(path)
            if not contains(root, path.resolve()):
                raise ExportError("Archive trees cannot contain paths outside their root.")
            if name in names and name != ".git":
                files.append(path)
        # Git administration belongs to the private repository, never to archive receipts.
        dirs[:] = [name for name in dirs if name != ".git"]
    return sorted(files)


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



def srcset_links(value):
    """Extract URL tokens at srcset whitespace and descriptor boundaries."""
    whitespace = " \t\n\r\f"
    links = []
    index = 0
    while index < len(value):
        while index < len(value) and value[index] in whitespace + ",":
            index += 1
        start = index
        while index < len(value) and value[index] not in whitespace:
            index += 1
        url = value[start:index]
        if not url:
            break
        if url.endswith(","):
            links.append(url.rstrip(","))
            continue
        # Commas inside the URL belong to it. Only a comma after the URL's
        # whitespace-delimited descriptors ends this candidate.
        parenthesized = False
        while index < len(value):
            char = value[index]
            index += 1
            if char == "," and not parenthesized:
                break
            if char == "(":
                parenthesized = True
            elif char == ")":
                parenthesized = False
        links.append(url)
    return links


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.stylesheets = set()
        self.in_stylesheet = False

    def handle_starttag(self, tag, attrs, *, namespace="html"):
        if tag == "style":
            media_type = (dict(attrs).get("type") or "text/css").strip().lower()
            self.in_stylesheet = media_type in ("", "text/css")
        stylesheet = (namespace == "html" and tag == "link"
                      and "stylesheet" in (dict(attrs).get("rel") or "").casefold().split())
        for name, value in attrs:
            if value and (name in ("src", "href", "poster")
                          or (namespace == "svg" and name == "xlink:href")):
                self.links.append(value)
                if stylesheet and name == "href":
                    self.stylesheets.add(value)
            elif value and name == "srcset":
                self.links.extend(srcset_links(value))
            elif value and name == "style":
                self.links.extend(css_links(value, stylesheet_links=self.stylesheets))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_stylesheet = False

    def handle_data(self, data):
        if self.in_stylesheet:
            self.links.extend(css_links(data, stylesheet_links=self.stylesheets))


def css_unescape(value):
    """Decode CSS escapes, including optional hex terminators and continued lines."""
    def replace(match):
        if match.group(1) is not None:
            codepoint = int(match.group(1), 16)
            return chr(codepoint) if 0 < codepoint <= 0x10ffff and not 0xd800 <= codepoint <= 0xdfff else "\ufffd"
        return match.group(2) or ""

    return re.sub(r"\\(?:([0-9a-fA-F]{1,6})(?:\r\n|[ \t\n\r\f])?|\r\n|[\n\r\f]|(.))",
                  replace, value, flags=re.S)


def css_links(text, *, stylesheet_links=None):
    """Return resource URLs and optionally collect the ones selected by @import."""
    string = re.compile(r'''(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)')''', re.S)
    name = re.compile(r"(?:[-\w]|[^\x00-\x7f]|\\(?:[0-9a-fA-F]{1,6}(?:\r\n|[ \t\n\r\f])?|[^\n\r\f]))+")
    spacing = re.compile(r"(?:\s|/\*.*?\*/)*", re.S)
    argument = re.compile(r'''\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|((?:\\.|[^\\'"()])*?))\s*\)''',
                          re.S)
    links = []
    functions = []
    index = 0
    while index < len(text):
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        value = string.match(text, index)
        if value:
            if functions and functions[-1]["image_set"] and functions[-1]["source_start"]:
                links.append(css_unescape(next(part for part in value.groups() if part is not None)))
            if functions:
                functions[-1]["source_start"] = False
            index = value.end()
            continue
        char = text[index]
        if char == ")":
            if functions:
                functions.pop()
            index += 1
            continue
        if char == ",":
            if functions:
                functions[-1]["source_start"] = True
            index += 1
            continue
        if char == "(":
            if functions:
                functions[-1]["source_start"] = False
            functions.append({"image_set": False, "source_start": True})
            index += 1
            continue
        at_keyword = char == "@"
        token = name.match(text, index + 1 if at_keyword else index)
        if not token:
            if functions and not char.isspace():
                functions[-1]["source_start"] = False
            index += 1
            continue
        identifier = css_unescape(token.group()).casefold()
        index = token.end()
        if functions:
            functions[-1]["source_start"] = False
        stylesheet = at_keyword and identifier == "import"
        if stylesheet:
            index = spacing.match(text, index).end()
            value = string.match(text, index)
            if value is None:
                url = name.match(text, index)
                if url and css_unescape(url.group()).casefold() == "url":
                    value = argument.match(text, url.end())
        elif not at_keyword and identifier == "url":
            value = argument.match(text, index)
        else:
            value = None
        if value:
            link = css_unescape(next(part for part in value.groups() if part is not None))
            links.append(link)
            if stylesheet and stylesheet_links is not None:
                stylesheet_links.add(link)
            index = value.end()
        elif index < len(text) and text[index] == "(":
            # Only a direct first string in an image-set alternative is a resource.
            # Nested type() descriptors and unrelated function strings remain text.
            functions.append({"image_set": not at_keyword and identifier in ("image-set", "-webkit-image-set"),
                              "source_start": True})
            index += 1
    return links


class ArchiveHTML(LocalLinks):
    """Check the supported export scaffold while retaining media-link validation."""

    SECTIONS = ("preamble", "chatlog", "postamble")
    TEXT_CONTEXTS = {"script", "style", "textarea", "title", "xmp", "iframe", "noembed", "noframes"}
    INERT = TEXT_CONTEXTS | {"template", "noscript", "plaintext"}
    VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                     "link", "meta", "param", "source", "track", "wbr"}
    SVG_HTML_INTEGRATION = {"foreignobject", "desc", "title"}
    SVG_HTML_BREAKOUT = {"b", "big", "blockquote", "body", "br", "center", "code", "dd", "div", "dl", "dt",
                         "em", "embed", "h1", "h2", "h3", "h4", "h5", "h6", "head", "hr", "i", "img", "li",
                         "listing", "menu", "meta", "nobr", "ol", "p", "pre", "ruby", "s", "small", "span",
                         "strong", "strike", "sub", "sup", "table", "tt", "u", "ul", "var"}

    def __init__(self):
        super().__init__()
        self.doctype = False
        self.divs = []
        self.opened = []
        self.closed = []
        self.section_parent = None
        self.sequence = 0
        self.inert = []
        self.footers = []
        self.malformed = False
        self.foreign = []

    def _start_namespace(self, tag, attrs):
        namespace = "html"
        if self.foreign:
            parent_namespace, parent_tag = self.foreign[-1]
            if parent_namespace == "svg" and parent_tag not in self.SVG_HTML_INTEGRATION:
                namespace = "svg"
                breakout = tag in self.SVG_HTML_BREAKOUT or (
                    tag == "font" and any(name in {"color", "face", "size"} for name, _ in attrs))
                if breakout:
                    # Browser recovery leaves SVG here; this is not the supported
                    # export scaffold and cannot excuse ordinary HTML self-closing tags.
                    self.malformed = True
                    while self.foreign and self.foreign[-1][0] == "svg" and self.foreign[-1][1] not in self.SVG_HTML_INTEGRATION:
                        self.foreign.pop()
                    namespace = "html"
        if tag == "svg":
            namespace = "svg"
        if self.foreign or namespace == "svg":
            if namespace == "svg" or tag not in self.VOID_ELEMENTS:
                self.foreign.append((namespace, tag))
        return namespace

    def _end_namespace(self, tag):
        if not self.foreign:
            return "html"
        for index in range(len(self.foreign) - 1, -1, -1):
            namespace, opened = self.foreign[index]
            if opened == tag:
                if index != len(self.foreign) - 1:
                    self.malformed = True
                del self.foreign[index:]
                return namespace
        self.malformed = True
        return "svg"

    def handle_decl(self, declaration):
        if not self.inert and declaration.strip().casefold() == "doctype html":
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        namespace = self._start_namespace(tag, attrs)
        if tag == "base":
            if namespace == "html" and not self.inert and any(name == "href" for name, _ in attrs):
                raise ExportError("HTML archive uses an unsupported base href; export without a base URL "
                                  "and retain portable relative links or explicit HTTP(S) URLs.")
            # An inert or foreign base element has no document URL effect.
            return namespace
        super().handle_starttag(tag, attrs, namespace=namespace)
        if namespace == "svg":
            return namespace
        if tag == "plaintext":
            self.malformed = True
        if tag in self.INERT:
            self.inert.append(tag)
            if tag in self.TEXT_CONTEXTS:
                self.set_cdata_mode(tag)
            return namespace
        if self.inert or tag != "div":
            return namespace
        classes = set((dict(attrs).get("class") or "").split())
        sections = classes.intersection(self.SECTIONS)
        section = next(iter(sections)) if len(sections) == 1 else None
        if len(sections) > 1:
            self.malformed = True
        if section:
            parent = tuple(frame["id"] for frame in self.divs)
            if self.section_parent is None:
                self.section_parent = parent
            self.opened.append(section)
            if parent != self.section_parent or self.opened != list(self.SECTIONS[:len(self.opened)]):
                self.malformed = True
        # The completion count belongs to a real postamble entry, not text in a
        # message, comment, script, or an inert template.
        footer = ("postamble__entry" in classes and self.divs
                  and self.divs[-1]["section"] == "postamble")
        self.sequence += 1
        self.divs.append({"id": self.sequence, "section": section, "text": [] if footer else None})
        return namespace

    def handle_startendtag(self, tag, attrs):
        namespace = self.handle_starttag(tag, attrs)
        if namespace == "svg":
            self.handle_endtag(tag)
        elif tag not in self.VOID_ELEMENTS:
            self.malformed = True
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if self._end_namespace(tag) == "svg":
            return
        if self.inert:
            if tag == self.inert[-1]:
                self.inert.pop()
            return
        if tag != "div":
            return
        if not self.divs:
            self.malformed = True
            return
        frame = self.divs.pop()
        if frame["text"] is not None:
            self.footers.append(" ".join("".join(frame["text"]).split()))
        if frame["section"]:
            self.closed.append(frame["section"])

    def handle_data(self, data):
        super().handle_data(data)
        if not self.inert:
            for frame in self.divs:
                if frame["text"] is not None:
                    frame["text"].append(data)

    def validate(self):
        # The exporter localizes digit grouping; whitespace can be a grouping
        # separator. This checks its completion declaration, not message counts.
        completed = any(re.fullmatch(r"Exported\s+\d[\d\s,.'\u2019\u066c]*\s+message\(s\)", text)
                        for text in self.footers)
        if (not self.doctype or self.malformed or self.divs or self.inert or self.foreign or not completed
                or self.opened != list(self.SECTIONS) or self.closed != list(self.SECTIONS)):
            raise ExportError("HTML archive is empty, incomplete, or not a supported DiscordChatExporter document. "
                              "Preserve the files, verify the exporter format, and retry an incomplete run with --resume.")


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
    # A network-path reference inherits file: when this portable archive opens from disk.
    if parts.scheme == "file" or (not parts.scheme and parts.netloc):
        raise ExportError("Archive contains an absolute local link; use portable relative media links or explicit HTTP(S) URLs.")
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
    stylesheets, inspected_stylesheets = set(), set()

    def add_links(source, refs, stylesheet_refs):
        targets = links.setdefault(source, [])
        for ref in refs:
            target = local_target(root, source.parent, ref)
            if target is not None:
                targets.append(target)
                if ref in stylesheet_refs:
                    stylesheets.add(target)

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
        stylesheet_refs = set()
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
                parser = ArchiveHTML()
                parser.feed(text)
                parser.close()
                parser.validate()
                refs = parser.links
                stylesheet_refs = parser.stylesheets
        except (UnicodeError, ValueError, KeyError, TypeError):
            raise ExportError("Archive HTML/JSON is malformed or lacks channel/messages metadata.") from None
        if not channel_id:
            raise ExportError("Every HTML archive needs a numeric channel ID in its filename; JSON needs channel.id.")
        if (channel_id, fmt) in seen:
            raise ExportError("Archive contains multiple exports for one channel ID and format; use separate runs.")
        seen.add((channel_id, fmt))
        identities[path] = {channel_id}
        add_links(path, refs, stylesheet_refs)
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
                guild_id = str(guild["id"])
                if not NUMERIC_ID.fullmatch(guild_id):
                    raise ExportError("JSON contains a malformed guild identity.")
                entry["guild_id"] = guild_id
        entries.append(entry)
    if not entries and not allow_empty:
        raise ExportError("No identified HTML or JSON archives were produced.")
    pending = list(links)
    while pending:
        source = pending.pop()
        for target in links.get(source, []):
            owners = identities.setdefault(target, set())
            additions = identities[source] - owners
            owners.update(additions)
            new_stylesheet = (target in stylesheets or target.suffix.lower() == ".css") and target not in inspected_stylesheets
            if new_stylesheet:
                inspected_stylesheets.add(target)
                try:
                    text = blobs[target].decode("utf-8-sig")
                except UnicodeError:
                    raise ExportError("A linked stylesheet is not valid UTF-8. Preserve the files and re-export.") from None
                stylesheet_refs = set()
                refs = css_links(text, stylesheet_links=stylesheet_refs)
                add_links(target, refs, stylesheet_refs)
            # A resource can acquire its stylesheet role after its owners were known.
            # New edges must propagate those existing owners as well as new owners.
            if additions or new_stylesheet:
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
    destination, companion = private_topology(destination)
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
    for relative in output:
        private_destination(destination / relative)
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

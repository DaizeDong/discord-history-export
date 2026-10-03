"""Generated native Git storage controls; recreate with tools/make_fixtures.py."""
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/discord-history-export/scripts"
SLUG = "acmeorg/synthetic-discord-config"


class NativeCompanion:
    def __init__(self, root, monkeypatch):
        self.root, self.monkeypatch = root, monkeypatch
        self.home = root / "home"
        self.home.mkdir()
        self.repository = root / "companion"
        self.environment = {key: value for key, value in os.environ.items()
                            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}}
        self.environment.update(HOME=str(self.home), USERPROFILE=str(self.home),
                                GIT_AUTHOR_NAME="Synthetic User", GIT_AUTHOR_EMAIL="user1@example.com",
                                GIT_COMMITTER_NAME="Synthetic User", GIT_COMMITTER_EMAIL="user1@example.com")
        self.native_run = subprocess.run
        self.git("init", "--template=", str(self.repository), cwd=root)
        self.git("config", "remote.origin.url", "https://github.com/" + SLUG + ".git")
        tree = self.git("hash-object", "-t", "tree", "-w", "--stdin", input="").stdout.strip()
        commit = self.git("commit-tree", tree, "-m", "Synthetic empty companion").stdout.strip()
        self.git("update-ref", "HEAD", commit)
        for key in list(os.environ):
            monkeypatch.delenv(key)
        for key, value in self.environment.items():
            if not key.startswith("GIT_"):
                monkeypatch.setenv(key, value)
        self.receipt = self.home / ".pii-guard/visibility.json"
        self.receipt.parent.mkdir()
        self.visibility()
        self.calls = []
        monkeypatch.setattr(subprocess, "run", self.run)
        spec = importlib.util.spec_from_file_location("native_discord_core", SCRIPTS / "export_core.py")
        self.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.core)

    def git(self, *arguments, cwd=None, input=None):
        result = self.native_run(["git", *arguments], cwd=cwd or self.repository, env=self.environment,
                                 input=input, capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, (arguments, result.returncode, result.stderr)
        return result

    def visibility(self, state="PRIVATE", age=0):
        stamp = datetime.now(timezone.utc) - timedelta(days=age)
        self.receipt.write_text(json.dumps({"_refreshed": stamp.isoformat(), SLUG: state, "acmeorg/synthetic-public": "PUBLIC"}), encoding="utf-8")

    def run(self, arguments, **kwargs):
        self.calls.append((list(map(str, arguments)), dict(kwargs)))
        if arguments[0] == "git":
            return self.native_run(arguments, **kwargs)
        if arguments[0] == "gh":
            # The old consumer queried gh; this synthetic response exposes that dependency.
            return subprocess.CompletedProcess(arguments, 0, json.dumps({
                "visibility": "PRIVATE", "nameWithOwner": SLUG}), "")
        raise AssertionError("Only local Git reads are permitted during storage proof")

    def files(self):
        return {str(path.relative_to(self.repository)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.repository.rglob("*") if path.is_file()}


@pytest.fixture
def native(tmp_path, monkeypatch):
    return NativeCompanion(tmp_path, monkeypatch)


@pytest.mark.parametrize("relative", [".", "data/future", "data/exact.json"])
def test_native_private_receipt_needs_no_network_or_writes(native, relative):
    target = native.repository / relative
    before = native.files()
    assert native.core.private_destination(target) == (target.resolve(), SLUG)
    assert native.files() == before
    assert native.calls and all(args[0] == "git" for args, _ in native.calls)
    queries = [args[1:] for args, _ in native.calls if "check-ignore" in args]
    assert ["check-ignore", "--no-index", "-q", "--", relative] in queries


def test_native_unborn_private_repository_is_rejected(native):
    native.git("update-ref", "-d", "HEAD")
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(native.repository / "data/new.json")


@pytest.mark.parametrize("relative,pattern", [
    ("data/secret.json", "data/secret.json\n"),
    ("data/missing/file.json", "data/missing/\n"),
    ("data/tracked.json", "data/tracked.json\n"),
])
def test_native_exact_ignored_destination_is_rejected(native, relative, pattern):
    if "tracked" in relative:
        target = native.repository / relative
        target.parent.mkdir()
        target.write_text("synthetic record\n", encoding="utf-8")
        blob = native.git("hash-object", "-w", str(target)).stdout.strip()
        native.git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + relative)
    (native.repository / ".gitignore").write_text(pattern, encoding="utf-8")
    before = native.files()
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(native.repository / relative)
    assert native.files() == before


@pytest.mark.parametrize("state,age", [("PUBLIC", 0), ("UNKNOWN", 0), ("PRIVATE", 90)])
def test_native_invalid_local_receipt_is_rejected_without_gh(native, state, age):
    native.visibility(state, age)
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(native.repository / "data/new.json")
    assert all(args[0] == "git" for args, _ in native.calls)


def test_native_linked_private_worktree_is_supported(native):
    linked = native.root / "linked"
    native.git("worktree", "add", "--detach", str(linked))
    assert (linked / ".git").is_file()
    target = linked / "data/future.json"
    assert native.core.private_destination(target) == (target.resolve(), SLUG)
    assert not target.parent.exists()


def test_native_hardlinked_existing_output_is_rejected(native):
    original, alias = native.repository / "original", native.repository / "alias"
    original.write_text("synthetic content", encoding="utf-8")
    os.link(original, alias)
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(alias)
    assert not native.calls


def test_native_public_nested_companion_is_rejected(native):
    nested = native.repository / "data/nested"
    nested.mkdir(parents=True)
    native.git("init", "--template=", str(nested))
    native.git("config", "remote.origin.url", "https://github.com/acmeorg/synthetic-public.git", cwd=nested)
    with pytest.raises(native.core.ExportError):
        native.core.private_topology(native.repository / "data")


def test_native_private_source_repository_name_is_rejected(native):
    slug = "acmeorg/discord-history-export"
    native.git("config", "remote.origin.url", "https://github.com/" + slug + ".git")
    native.receipt.write_text(json.dumps({"_refreshed": datetime.now(timezone.utc).isoformat(), slug: "PRIVATE"}))
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(native.repository / "data")


def test_native_existing_ignored_artifact_is_rechecked(native):
    data = native.repository / "data"
    data.mkdir()
    (data / "existing.json").write_text("synthetic archive\n", encoding="utf-8")
    (native.repository / ".gitignore").write_text("data/existing.json\n", encoding="utf-8")
    before = native.files()
    with pytest.raises(native.core.ExportError):
        native.core.private_topology(data)
    assert native.files() == before


def native_export(native, mutate_after_probe=False, observations=None):
    """Load the complete runner with a generated exporter and real local Git proof."""
    import sys
    spec = importlib.util.spec_from_file_location("native_storage_fixtures", ROOT / "tools/make_fixtures.py")
    generated = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generated)
    exporter = native.root / "synthetic-exporter"
    exporter.write_text("synthetic intercepted executable", encoding="utf-8")
    credential = native.root / "synthetic-credential"
    credential.write_text(generated.SECRET, encoding="utf-8")
    reads = []
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path == credential:
            reads.append(path)
        return original_read(path, *args, **kwargs)

    native.monkeypatch.setattr(Path, "read_text", read)
    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(native.repository / "data"))

    def run(arguments, **kwargs):
        args = list(map(str, arguments))
        if args[0] != str(exporter):
            return native.run(arguments, **kwargs)
        if observations is not None:
            observations.setdefault("exporter_calls", []).append(args[1:])
        if "--version" in args:
            output = "2.47"
        elif "--help" in args:
            output = "Synthetic export command"
            if mutate_after_probe:
                native.git("config", "remote.origin.url", "https://github.com/acmeorg/synthetic-public.git")
        else:
            fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
            target = Path(args[args.index("-o") + 1].partition("%t")[0])
            generated.populate(target, formats=(fmt,), channels=("channel",))
            output = ""
        return subprocess.CompletedProcess(arguments, 0, output, "")

    native.monkeypatch.setattr(subprocess, "run", run)
    native.monkeypatch.setitem(sys.modules, "export_core", native.core)
    spec = importlib.util.spec_from_file_location("native_storage_history", SCRIPTS / "export_history.py")
    history = importlib.util.module_from_spec(spec)
    previous = list(sys.path)
    try:
        spec.loader.exec_module(history)
    finally:
        sys.path[:] = previous
    arguments = ["execute", "--exporter", str(exporter), "--credential-ref", "file:" + str(credential),
                 "--run-id", "synthetic-run", "--channel-id", generated.IDS["channel"]]
    return history, arguments, reads


def test_native_ignored_dynamic_raw_files_cannot_report_complete(native):
    (native.repository / ".gitignore").write_text("**/raw/**/*.html\n", encoding="utf-8")
    history, arguments, reads = native_export(native)
    assert history.main(arguments) == 1
    run = native.repository / "data/runs/synthetic-run"
    result = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "partial"
    assert any((run / "attempts/0001/raw").rglob("*.html"))
    assert not (run / "attempts/0001/organized").exists()


def test_native_route_change_during_exporter_probe_precedes_credentials(native):
    history, arguments, reads = native_export(native, mutate_after_probe=True)
    assert history.main(arguments) == 1
    assert reads == []
    assert not (native.repository / "data").exists()


def test_native_absent_data_directory_ignore_is_rejected_without_creation(native):
    target = native.repository / "data/not-created"
    (native.repository / ".gitignore").write_text("data/not-created/\n", encoding="utf-8")
    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(target))
    before = native.files()
    with pytest.raises(native.core.ExportError):
        native.core.resolve_data_dir()
    assert native.files() == before
    assert not target.exists()


@pytest.mark.parametrize("relative", [".", "data/not-created"])
def test_native_future_directory_and_repository_root_remain_supported(native, relative):
    target = native.repository / relative
    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(target))
    before = native.files()
    assert native.core.resolve_data_dir() == (target.resolve(), SLUG)
    assert native.files() == before


def test_native_directory_only_ignore_does_not_reject_an_exact_file(native):
    target = native.repository / "data/exact.json"
    (native.repository / ".gitignore").write_text("data/exact.json/\n", encoding="utf-8")
    before = native.files()
    assert native.core.private_destination(target) == (target.resolve(), SLUG)
    assert native.files() == before
    assert not target.exists()


def test_native_ignored_empty_directory_in_existing_tree_is_rejected(native):
    target = native.repository / "data"
    (target / "empty").mkdir(parents=True)
    (native.repository / ".gitignore").write_text("data/empty/\n", encoding="utf-8")
    before = native.files()
    with pytest.raises(native.core.ExportError):
        native.core.private_topology(target)
    assert native.files() == before


@pytest.mark.parametrize("relative", ["raw/html", "raw/json", "organized/archive"])
def test_native_known_output_directory_ignore_precedes_probes_credentials_and_writes(native, relative):
    (native.repository / ".gitignore").write_text("**/" + relative + "/\n", encoding="utf-8")
    observations = {}
    history, arguments, reads = native_export(native, observations=observations)
    before = native.files()
    assert history.main(arguments) == 1
    assert reads == []
    assert observations.get("exporter_calls", []) == []
    assert native.files() == before
    assert not (native.repository / "data").exists()


def test_native_exact_file_directory_pattern_allows_complete_export(native):
    (native.repository / ".gitignore").write_text("**/channels.txt/\n", encoding="utf-8")
    history, arguments, reads = native_export(native)
    assert history.main(arguments) == 0
    assert len(reads) == 1
    run = native.repository / "data/runs/synthetic-run"
    result = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "complete"
    assert any((run / "attempts/0001/raw/html").rglob("*.html"))
    assert any((run / "attempts/0001/raw/json").rglob("*.json"))

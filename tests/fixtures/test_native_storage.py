"""Generated native storage path controls; recreate with tools/make_fixtures.py."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import json

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/discord-history-export/scripts"


class NativeCompanion:
    def __init__(self, root, monkeypatch):
        self.root, self.monkeypatch = root, monkeypatch
        self.repository = root / "companion"
        self.native_run = subprocess.run
        self.native_run(["git", "init", "-q", "--template=", str(self.repository)], check=True,
                        capture_output=True, text=True)
        self.calls = []
        monkeypatch.setattr(subprocess, "run", self.run)
        spec = importlib.util.spec_from_file_location("native_discord_core", SCRIPTS / "export_core.py")
        self.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.core)

    def run(self, arguments, **kwargs):
        self.calls.append((list(map(str, arguments)), dict(kwargs)))
        raise AssertionError("The runtime path check starts no subprocess")

    def files(self):
        return {str(path.relative_to(self.repository)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.repository.rglob("*") if path.is_file()}


@pytest.fixture
def native(tmp_path, monkeypatch):
    return NativeCompanion(tmp_path, monkeypatch)


@pytest.mark.parametrize("relative", [".", "data/future", "data/exact.json"])
def test_native_destination_check_is_path_only(native, relative):
    target = native.repository / relative
    before = native.files()
    assert native.core.private_destination(target) == (target.resolve(), native.repository.resolve())
    assert native.files() == before
    assert native.calls == []


def test_native_linked_worktree_marker_is_supported(native):
    linked = native.root / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: ../companion/.git/worktrees/linked\n", encoding="utf-8")
    target = linked / "data/future.json"
    assert native.core.private_destination(target) == (target.resolve(), linked.resolve())
    assert not target.parent.exists()


def test_native_destination_outside_any_worktree_is_rejected(native):
    loose = native.root / "loose"
    loose.mkdir()
    with pytest.raises(native.core.ExportError, match="worktree"):
        native.core.private_destination(loose / "data/new.json")
    assert not (loose / "data").exists()


def test_native_hardlinked_existing_output_is_rejected(native):
    original, alias = native.repository / "original", native.repository / "alias"
    original.write_text("synthetic content", encoding="utf-8")
    os.link(original, alias)
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(alias)
    assert not native.calls


def test_native_nested_repository_is_rejected(native):
    nested = native.repository / "data/nested"
    (nested / ".git").mkdir(parents=True)
    with pytest.raises(native.core.ExportError, match="nested"):
        native.core.private_topology(native.repository / "data")


def test_native_source_repository_name_is_rejected(native):
    clone = native.root / "discord-history-export"
    (clone / ".git").mkdir(parents=True)
    with pytest.raises(native.core.ExportError):
        native.core.private_destination(clone / "data")


@pytest.mark.parametrize("relative", [".", "data/not-created"])
def test_native_undeclared_data_roots_are_rejected(native, relative):
    target = native.repository / relative
    native.monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", str(target))
    before = native.files()
    with pytest.raises(native.core.ExportError, match="data/"):
        native.core.resolve_data_dir()
    assert native.files() == before


def native_export(native, observations=None):
    """Load the complete runner with a generated exporter and real path checks."""
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


def test_native_export_completes_with_path_only_checks(native):
    history, arguments, reads = native_export(native)
    assert history.main(arguments) == 0
    assert len(reads) == 1
    assert native.calls == []
    run = native.repository / "data/runs/synthetic-run"
    result = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "complete"
    assert result["companion"] == "companion"
    assert any((run / "attempts/0001/raw/html").rglob("*.html"))
    assert any((run / "attempts/0001/raw/json").rglob("*.json"))

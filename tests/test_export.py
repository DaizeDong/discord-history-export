"""Business regressions use generated records and intercept every child process."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "discord-history-export" / "scripts"
spec = importlib.util.spec_from_file_location("synthetic_fixtures", ROOT / "tools" / "make_fixtures.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class Harness:
    def __init__(self, root):
        self.root = root
        self.companion = root / "private-companion"
        self.companion.mkdir()
        (self.companion / ".git").mkdir()
        self.data = self.companion / "data"
        self.data.mkdir()
        self.raw = root / "raw"
        fixtures.populate(self.raw)
        self.channels = root / "channels.txt"
        self.channels.write_text(fixtures.records()["channels"], encoding="utf-8")
        self.exporter = root / "synthetic-exporter"
        self.exporter.write_text("synthetic process, intercepted in tests", encoding="utf-8")
        self.calls = []
        self.visibility = "PRIVATE"
        self.version = "2.47"
        self.fail_format = None
        self.empty_format = None
        self.html_case = None
        self.guild_case = None
        self.tree_layout = False
        self.mismatch = False
        self.interrupt_format = None
        self.data_override = None
        self.repositories = {}

    def run(self, argv, **kwargs):
        args = [str(a) for a in argv]
        self.calls.append((args, kwargs.get("env")))
        output, error, code = "", "", 0
        if args[0] == "git":
            requested = Path(args[args.index("-C") + 1]).resolve()
            root = next((path for path in (requested, *requested.parents) if (path / ".git").exists()), None)
            if root is None:
                code = 128
            elif "--show-toplevel" in args:
                output = str(root)
            elif "--list" in args:
                repository = self.repositories.get(root, ("AcmeOrg/discord-history-export-config", self.visibility))[0]
                output = "remote.origin.url\nhttps://github.com/" + repository + ".git\0"
            elif args[-1] == "remote":
                output = "origin"
            elif "remote.origin.url" in args or "get-url" in args:
                repository = self.repositories.get(root, ("AcmeOrg/discord-history-export-config", self.visibility))[0]
                output = "https://github.com/" + repository + ".git"
            else:
                raise AssertionError(f"Unexpected git command: {args}")
        elif args[0] == "gh":
            requested = args[3].removeprefix("https://github.com/")
            visibility = next((visibility for repository, visibility in self.repositories.values()
                               if repository == requested), self.visibility)
            output = json.dumps({"visibility": visibility, "nameWithOwner": requested})
        elif args[0] == str(self.exporter):
            if "--version" in args:
                output = "DiscordChatExporter.Cli " + self.version
            elif "--help" in args:
                output = "Usage: exportguild --guild --format --output --include-threads --after --before --media"
            else:
                assert fixtures.SECRET not in " ".join(args)
                assert kwargs["env"]["DISCORD_TOKEN"] == fixtures.SECRET
                if args[1] == "channels":
                    output = fixtures.records()["channels"]
                else:
                    fmt = "json" if args[args.index("-f") + 1].lower() == "json" else "html"
                    template = args[args.index("-o") + 1]
                    raw = Path(template[:template.index("%t")])
                    if self.empty_format != fmt:
                        channels = ("channel",) if "-c" in args else ("channel", "other_channel")
                        if self.mismatch and fmt == "json":
                            channels = ("thread",)
                        populate = fixtures.source8_populate_tree if self.tree_layout else fixtures.populate
                        populate(raw, formats=(fmt,), channels=channels, media="--media" in args)
                        if self.html_case is not None:
                            fixtures.source7_apply_case(raw, self.html_case)
                        if fmt == "json" and self.guild_case is not None:
                            fixtures.source9_apply_guild(raw, self.guild_case)
                    if self.fail_format == fmt:
                        code = 1
                        output = error = fixtures.SECRET + " Authorization: sensitive child output"
                    if self.interrupt_format == fmt:
                        raise KeyboardInterrupt
        else:
            raise AssertionError(f"Unexpected process: {args}")
        return subprocess.CompletedProcess(args, code, stdout=output, stderr=error)

    def cli(self, monkeypatch, script, args):
        sys.modules.pop("export_core", None)
        monkeypatch.setattr(subprocess, "run", self.run)
        override = str(self.data) if self.data_override is None else self.data_override
        monkeypatch.setenv("DISCORD_HISTORY_EXPORT_DATA_DIR", override)
        monkeypatch.setenv("DISCORD_BOT_TOKEN", fixtures.SECRET)
        monkeypatch.chdir(self.root)
        monkeypatch.setattr(sys, "argv", [str(SCRIPTS / script), *map(str, args)])
        stdout, stderr = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                runpy.run_path(str(SCRIPTS / script), run_name="__main__")
            except SystemExit as exc:
                code = exc.code or 0
            except Exception as exc:
                code = 99
                stderr.write(type(exc).__name__)
        return code, stdout.getvalue() + stderr.getvalue()

    def export(self, monkeypatch, mode="execute", extra=()):
        return self.cli(monkeypatch, "export_history.py", [mode, "--exporter", self.exporter,
            "--credential-ref", "env:DISCORD_BOT_TOKEN", "--run-id", "synthetic-run",
            "--guild-id", fixtures.IDS["guild"], *extra])


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


@pytest.mark.parametrize("case,allowed", fixtures.source9_css_cases())
def test_source9_css_import_dependencies_preserve_archive_integrity(h, monkeypatch, case, allowed):
    raw = h.root / "css-source"
    fixtures.source9_populate_css(raw, case)
    before = hashes(raw)
    target = h.data / "css-archive"
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert hashes(raw) == before
    if allowed:
        assert code == 0, output
        assert hashes(target / "archive") == before
    else:
        assert code == 1, output
        assert "missing or escaping" in output
        assert not target.exists()


@pytest.mark.parametrize("case", fixtures.source9_guild_cases())
def test_source9_guild_export_requires_each_channel_identity(h, monkeypatch, case):
    h.guild_case = case
    code, output = h.export(monkeypatch)
    run = h.data / "runs" / "synthetic-run"
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if case == "matching":
        assert code == 0, output
        assert manifest["status"] == "complete"
        assert h.export(monkeypatch)[0] == 0
    else:
        assert code == 1, output
        assert manifest["status"] == "partial"
        assert "guild" in output.lower()
        assert not (run / "attempts" / "0001" / "organized").exists()
        before = hashes(run / "attempts" / "0001")
        h.guild_case = "matching"
        assert h.export(monkeypatch, extra=["--resume"])[0] == 0
        assert hashes(run / "attempts" / "0001") == before


@pytest.mark.parametrize("case", ["missing", "null", "empty", "null-id", "mixed-null"])
@pytest.mark.parametrize("resume", [False, True])
def test_source9_legacy_guild_replay_refuses_without_mutation(h, monkeypatch, case, resume):
    assert h.export(monkeypatch)[0] == 0
    run = h.data / "runs" / "synthetic-run"
    fixtures.source9_legacy_guild(run, case)
    before = hashes(run)
    calls = len(h.calls)
    code, output = h.export(monkeypatch, extra=["--resume"] if resume else [])
    assert code == 1, output
    assert "guild" in output.lower()
    assert hashes(run) == before
    assert not any(args[0] == str(h.exporter) for args, _ in h.calls[calls:])


@pytest.mark.parametrize("case", ["missing", "null", "empty"])
def test_source9_channel_export_and_standalone_allow_absent_guild(h, monkeypatch, case):
    h.guild_case = case
    args = ["execute", "--exporter", h.exporter, "--credential-ref", "env:DISCORD_BOT_TOKEN",
            "--run-id", "synthetic-channel", "--channel-id", fixtures.IDS["channel"]]
    assert h.cli(monkeypatch, "export_history.py", args)[0] == 0
    assert h.cli(monkeypatch, "export_history.py", args)[0] == 0
    fixtures.source9_apply_guild(h.raw, case)
    assert h.cli(monkeypatch, "reorganize.py", [h.raw, h.data / "standalone", h.channels])[0] == 0


def source8_scan_fault(monkeypatch, directories, error_type):
    original = os.scandir
    selected = {Path(path).absolute() for path in directories}
    attempts = []

    def scan(path):
        if not isinstance(path, int) and Path(path).absolute() in selected:
            attempts.append(str(path))
            raise error_type("Synthetic directory enumeration failure")
        return original(path)

    monkeypatch.setattr(os, "scandir", scan)
    return attempts


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_source_inventory_failure_preserves_then_recovers(h, monkeypatch, error_type):
    raw = h.root / "source8-raw"
    blocked = fixtures.source8_populate_tree(raw)
    before = hashes(raw)
    target = h.data / "source8-organized"
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [blocked], error_type)
        code, output = h.cli(fault, "reorganize.py", [raw, target, h.channels])
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    assert hashes(raw) == before and not target.exists()
    assert h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])[0] == 0
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete" and len(manifest["artifacts"]) == 4


@pytest.mark.parametrize("empty", [False, True])
def test_source8_readable_multidirectory_and_empty_channels(h, monkeypatch, empty):
    raw = h.root / "source8-raw"
    fixtures.source8_populate_tree(raw, empty=empty)
    target = h.data / "source8-organized"
    args = [raw, target, h.channels]
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 0
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete" and len(manifest["artifacts"]) == 4
    assert manifest["summary"]["message_count"] == (0 if empty else 2)
    before = hashes(target)
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 0
    assert hashes(target) == before


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_destination_scan_fails_before_copy(h, monkeypatch, error_type):
    target = h.data / "source8-existing"
    blocked = fixtures.source8_unrecorded_file(target)
    before = hashes(target)
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [blocked], error_type)
        code, output = h.cli(fault, "reorganize.py", [h.raw, target, h.channels])
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    assert hashes(target) == before
    assert h.cli(monkeypatch, "reorganize.py", [h.raw, target, h.channels])[0] == 1
    assert hashes(target) == before


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_file_receipts_require_complete_enumeration(h, monkeypatch, error_type):
    h.tree_layout = True
    assert h.export(monkeypatch)[0] == 0
    run = h.data / "runs" / "synthetic-run"
    sys.modules.pop("export_core", None)
    module = runpy.run_path(str(SCRIPTS / "export_history.py"))
    before = module["file_receipts"](run)
    blocked = run / "attempts" / "0001" / "raw" / "html" / "restricted"
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [blocked], error_type)
        with pytest.raises(module["ExportError"], match="enumerat"):
            module["file_receipts"](run)
    assert attempts and module["file_receipts"](run) == before


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_fresh_export_inventory_failure_preserves_resumable_attempt(h, monkeypatch, error_type):
    h.tree_layout = True
    run = h.data / "runs" / "synthetic-run"
    first = run / "attempts" / "0001"
    blocked = [first / "raw" / fmt / "restricted" for fmt in ("html", "json")]
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, blocked, error_type)
        code, output = h.export(fault)
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "partial" and manifest["in_progress"] is True
    before = hashes(first)
    assert len(list((first / "raw").rglob("*.html"))) == 2
    assert len(list((first / "raw").rglob("*.json"))) == 2
    assert not (first / "organized").exists()
    code, output = h.export(monkeypatch, extra=["--resume"])
    assert code == 0, output
    assert hashes(first) == before
    recovered = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert recovered["status"] == "complete" and recovered["attempt"] == 2


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_completed_replay_rejects_hidden_unreceipted_files(h, monkeypatch, error_type):
    assert h.export(monkeypatch)[0] == 0
    run = h.data / "runs" / "synthetic-run"
    blocked = fixtures.source8_unrecorded_file(run)
    before = hashes(run)
    h.calls.clear()
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [blocked], error_type)
        code, output = h.export(fault)
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    assert hashes(run) == before
    assert not any(args[0] == str(h.exporter) for args, env in h.calls)
    assert h.export(monkeypatch)[0] == 1
    assert hashes(run) == before


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_completed_replay_access_recovery_is_read_only(h, monkeypatch, error_type):
    h.tree_layout = True
    assert h.export(monkeypatch)[0] == 0
    run = h.data / "runs" / "synthetic-run"
    blocked = run / "attempts" / "0001" / "raw" / "html" / "restricted"
    before = hashes(run)
    h.calls.clear()
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [blocked], error_type)
        code, output = h.export(fault)
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    assert hashes(run) == before
    assert h.export(monkeypatch)[0] == 0
    assert hashes(run) == before
    assert not any(args[0] == str(h.exporter) for args, env in h.calls)


@pytest.mark.parametrize("error_type", [PermissionError, OSError, FileNotFoundError])
def test_source8_final_receipt_failure_cannot_publish_complete(h, monkeypatch, error_type):
    run = h.data / "runs" / "synthetic-run"
    with monkeypatch.context() as fault:
        attempts = source8_scan_fault(fault, [run / "attempts"], error_type)
        code, output = h.export(fault)
    assert attempts and code == 1 and "enumerat" in output.lower(), output
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "partial" and manifest["in_progress"] is True
    before = hashes(run)
    code, output = h.export(monkeypatch, extra=["--resume"])
    assert code == 1 and "new run ID" in output, output
    assert hashes(run) == before
    assert h.export(monkeypatch, extra=["--run-id", "synthetic-recovery"])[0] == 0


@pytest.mark.parametrize("error_type", [PermissionError, OSError])
def test_source8_file_read_failure_stays_rejected(h, monkeypatch, error_type):
    target = h.data / "source8-organized"
    original = Path.read_bytes
    unreadable = next(h.raw.rglob("*.html"))
    attempts = []

    def read(path):
        if path == unreadable:
            attempts.append(path)
            raise error_type("Synthetic file read failure")
        return original(path)

    before = hashes(h.raw)
    with monkeypatch.context() as fault:
        fault.setattr(Path, "read_bytes", read)
        code, output = h.cli(fault, "reorganize.py", [h.raw, target, h.channels])
    assert code == 1, output
    assert not target.exists() and hashes(h.raw) == before
    assert attempts, "The injected source read failure was not reached"


@pytest.mark.parametrize('case,allowed', fixtures.source7_html_cases())
def test_source7_html_content_contract_before_organization(h, monkeypatch, case, allowed):
    raw = h.root / 'source7-raw'
    fixtures.populate(raw, media=False)
    fixtures.source7_apply_case(raw, case)
    before = hashes(raw)
    target = h.data / 'source7-organized'
    code, output = h.cli(monkeypatch, 'reorganize.py', [raw, target, h.channels])
    assert hashes(raw) == before
    if allowed:
        assert code == 0, output
        manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        assert manifest['status'] == 'complete'
        if case == 'empty-channel':
            assert manifest['summary']['message_count'] == 0
    else:
        assert code == 1 and 'HTML' in output, output
        assert not target.exists()


@pytest.mark.parametrize('case', [name for name, allowed in fixtures.source7_html_cases() if not allowed])
def test_source7_invalid_export_preserves_attempt_and_can_resume(h, monkeypatch, case):
    h.html_case = case
    code, output = h.export(monkeypatch)
    assert code == 1, output
    run = h.data / 'runs' / 'synthetic-run'
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'partial' and 'HTML' in manifest['issues'][0]
    first = run / 'attempts' / '0001'
    before = hashes(first)
    assert before and not (first / 'organized').exists()
    h.html_case = None
    code, output = h.export(monkeypatch, extra=['--resume'])
    assert code == 0, output
    assert hashes(first) == before
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'complete' and manifest['attempt'] == 2
    completed = hashes(run)
    h.calls.clear()
    assert h.export(monkeypatch)[0] == 0
    assert hashes(run) == completed
    assert not any(args[0] == str(h.exporter) for args, env in h.calls)


@pytest.mark.parametrize('case', ['zero-byte', 'plain-text', 'service-page', 'missing-footer'])
@pytest.mark.parametrize('resume', [False, True])
def test_source7_legacy_complete_invalid_html_requires_new_run(h, monkeypatch, case, resume):
    assert h.export(monkeypatch)[0] == 0
    run = h.data / 'runs' / 'synthetic-run'
    fixtures.source7_legacy_complete(run, case)
    before = hashes(run)
    h.calls.clear()
    code, output = h.export(monkeypatch, extra=['--resume'] if resume else [])
    assert code == 1, output
    assert 'HTML' in output and 'new run ID' in output, output
    assert hashes(run) == before
    assert not any(args[0] == str(h.exporter) for args, env in h.calls)


def test_source7_empty_channel_completes_and_replays(h, monkeypatch):
    h.html_case = 'empty-channel'
    assert h.export(monkeypatch)[0] == 0
    run = h.data / 'runs' / 'synthetic-run'
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'complete'
    assert manifest['summary']['message_count'] == 0
    assert manifest['summary']['html_count'] == 2
    before = hashes(run)
    h.calls.clear()
    assert h.export(monkeypatch)[0] == 0
    assert hashes(run) == before
    assert not any(args[0] == str(h.exporter) for args, env in h.calls)


def test_organizer_integrity_and_idempotence(h, monkeypatch):
    target = h.data / "organized"
    args = [h.raw, target, h.channels]
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 0
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["summary"] == {"artifact_count": 6, "html_count": 2, "json_count": 2,
                                    "media_count": 2, "message_count": 2}
    assert {a["channel_id"] for a in manifest["artifacts"]} == {
        fixtures.IDS["channel"], fixtures.IDS["other_channel"]}
    for item in manifest["artifacts"]:
        destination = target / item["path"]
        assert destination.read_bytes() == (h.raw / item["source"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(destination.read_bytes()).hexdigest()
        assert item["size_bytes"] == destination.stat().st_size
    before = hashes(target)
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 0
    assert hashes(target) == before


@pytest.mark.parametrize("case", fixtures.stylesheet_cases(), ids=lambda case: case[0])
def test_source5_stylesheet_contexts_preserve_archive_bytes(h, monkeypatch, case):
    raw = h.root / "stylesheet-case"
    fixtures.populate_stylesheet_case(raw, case)
    target = h.data / "organized-css"
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert code == 0, output
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["artifacts"]) == len(hashes(raw))
    for entry in manifest["artifacts"]:
        assert (target / entry["path"]).read_bytes() == (raw / entry["source"]).read_bytes()


@pytest.mark.parametrize("case", [case for case in fixtures.stylesheet_cases() if case[2]],
                         ids=lambda case: case[0])
def test_source5_real_stylesheet_assets_remain_required(h, monkeypatch, case):
    raw = h.root / "missing-css-asset"
    fixtures.populate_stylesheet_case(raw, case, include_asset=False)
    target = h.data / "organized-css"
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert code != 0 and "local media link" in output
    assert not target.exists()


@pytest.mark.parametrize("case", ["exact-file-ancestor", "casefold-file-ancestor"])
@pytest.mark.parametrize("existing_empty", [False, True])
def test_source5_normalized_topology_refuses_before_any_copy(h, monkeypatch, case, existing_empty):
    raw = h.root / "topology-case"
    fixtures.populate_destination_topology(raw, case)
    target = h.data / "organized-topology"
    if existing_empty:
        target.mkdir()
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert target.exists() is existing_empty
    if existing_empty:
        assert list(target.iterdir()) == []
    assert code != 0 and "conflict" in output


def test_source5_valid_json_normalization_still_organizes(h, monkeypatch):
    raw = h.root / "valid-topology"
    fixtures.populate_destination_topology(raw, "valid-normalization")
    target = h.data / "organized-topology"
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert code == 0, output
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    normalized = next(item for item in manifest["artifacts"] if item["source"] == "room.json")
    assert normalized["path"] == f"archive/room [{fixtures.IDS['channel']}].json"
    for entry in manifest["artifacts"]:
        assert (target / entry["path"]).read_bytes() == (raw / entry["source"]).read_bytes()


@pytest.mark.parametrize("case", ["changed-source", "unrelated-target", "broken-media", "missing-id", "invalid-json"])
def test_organizer_rejects_without_mutation(h, monkeypatch, case):
    target = h.data / "organized"
    if case == "changed-source":
        assert h.cli(monkeypatch, "reorganize.py", [h.raw, target, h.channels])[0] == 0
        next(h.raw.rglob("*.html")).write_text("changed", encoding="utf-8")
    elif case == "unrelated-target":
        target.mkdir()
        (target / "unrelated.txt").write_text("SYNTHETIC_UNRELATED", encoding="utf-8")
    elif case == "broken-media":
        next(h.raw.rglob("*.bin")).unlink()
    elif case == "missing-id":
        next(h.raw.rglob("*.html")).rename(h.raw / "unknown.html")
    elif case == "invalid-json":
        next(h.raw.rglob("*.json")).write_text("{", encoding="utf-8")
    before = hashes(target) if target.exists() else {}
    code, output = h.cli(monkeypatch, "reorganize.py", [h.raw, target, h.channels])
    assert code != 0
    assert (hashes(target) if target.exists() else {}) == before
    expected = {
        "changed-source": "HTML archive is empty, incomplete",
        "unrelated-target": "Existing output differs from this immutable input",
        "broken-media": "missing or escaping local media link",
        "missing-id": "Every HTML archive needs a numeric channel ID",
        "invalid-json": "Archive HTML/JSON is malformed",
    }
    assert expected[case] in output


@pytest.mark.parametrize("visibility", ["PUBLIC", "UNKNOWN", ""])
def test_organizer_private_boundary(h, monkeypatch, visibility):
    h.visibility = visibility
    target = h.data / "organized"
    code, output = h.cli(monkeypatch, "reorganize.py", [h.raw, target, h.channels])
    assert code != 0
    assert not target.exists()
    assert "verified PRIVATE visibility and identity" in output
    assert any(argv[0] == "gh" for argv, _ in h.calls)


def test_plan_never_reads_credential_or_writes(h, monkeypatch):
    monkeypatch.delenv("MISSING_SYNTHETIC_CREDENTIAL", raising=False)
    args = ["plan", "--exporter", h.exporter, "--credential-ref", "env:MISSING_SYNTHETIC_CREDENTIAL",
            "--run-id", "synthetic-plan", "--channel-id", fixtures.IDS["channel"]]
    code, output = h.cli(monkeypatch, "export_history.py", args)
    assert code == 0, output
    assert not list(h.data.iterdir())
    assert all(call[0][0] in ("git", "gh") for call in h.calls)


def test_export_complete_and_replay(h, monkeypatch):
    code, output = h.export(monkeypatch, extra=["--media", "--after", "2026-01-01", "--before", "2026-02-01"])
    assert code == 0, output
    run = h.data / "runs" / "synthetic-run"
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["summary"]["json_count"] == manifest["summary"]["html_count"] == 2
    assert manifest["summary"]["message_count"] == 2
    assert fixtures.SECRET not in output + (run / "manifest.json").read_text() + (run / "run.json").read_text()
    exports = [argv for argv, env in h.calls if argv[0] == str(h.exporter) and argv[1] == "exportguild" and "--help" not in argv]
    assert len(exports) == 2
    assert all("--include-threads" in argv and "--after" in argv and "--before" in argv for argv in exports)
    before = hashes(run)
    calls_before = len(h.calls)
    assert h.export(monkeypatch, extra=["--media", "--after", "2026-01-01", "--before", "2026-02-01"])[0] == 0
    assert hashes(run) == before
    assert all(argv[0] != str(h.exporter) for argv, _ in h.calls[calls_before:])


@pytest.mark.parametrize("failure", ["child-error", "empty-json", "mismatch"])
def test_failed_export_truthful_and_no_secret(h, monkeypatch, failure):
    h.fail_format = "json" if failure == "child-error" else None
    h.empty_format = "json" if failure == "empty-json" else None
    h.mismatch = failure == "mismatch"
    code, output = h.export(monkeypatch)
    assert code != 0
    run = h.data / "runs" / "synthetic-run"
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["status"] == "partial"
    assert manifest["issues"]
    assert fixtures.SECRET not in output
    assert all(fixtures.SECRET.encode() not in p.read_bytes() for p in run.rglob("*") if p.is_file())


def test_resume_freezes_configuration(h, monkeypatch):
    h.fail_format = "json"
    assert h.export(monkeypatch)[0] != 0
    run = h.data / "runs" / "synthetic-run"
    before = hashes(run)
    call_count = len(h.calls)
    assert h.export(monkeypatch, extra=["--resume", "--media"])[0] != 0
    assert hashes(run) == before
    assert all(argv[0] != str(h.exporter) for argv, _ in h.calls[call_count:])
    h.fail_format = None
    assert h.export(monkeypatch, extra=["--resume"])[0] == 0
    assert all((run / path).read_bytes() and hashlib.sha256((run / path).read_bytes()).hexdigest() == digest
               for path, digest in before.items() if path != "manifest.json")


@pytest.mark.parametrize("extra", [["--run-id", "../escape"], ["--after", "invalid"], ["--after", "2026-03-01", "--before", "2026-01-01"]])
def test_invalid_plan_is_read_only(h, monkeypatch, extra):
    assert h.export(monkeypatch, mode="plan", extra=extra)[0] != 0
    assert not list(h.data.iterdir())


def test_unknown_exporter_version_fails_before_write(h, monkeypatch):
    h.version = "0.0.0-synthetic-unproven"
    code, output = h.export(monkeypatch)
    assert code != 0
    assert not list(h.data.iterdir())
    assert "Exporter credential transport is unproven" in output
    assert [argv[1:] for argv, _ in h.calls if argv[0] == str(h.exporter)] == [
        ["--version"], ["exportguild", "--help"]]


def test_linked_private_worktree(h, monkeypatch):
    (h.companion / ".git").rmdir()
    (h.companion / ".git").write_text("gitdir: ../synthetic-main/.git/worktrees/linked\n", encoding="utf-8")
    code, output = h.export(monkeypatch)
    assert code == 0, output


@pytest.mark.parametrize("case", ["no-git", "own-consumer", "unknown-visibility"])
def test_runner_denies_unproven_destination(h, monkeypatch, case):
    if case == "no-git":
        (h.companion / ".git").rmdir()
    elif case == "own-consumer":
        h.data = ROOT / "synthetic-denied-output"
    else:
        h.visibility = "UNKNOWN"
    code, output = h.export(monkeypatch)
    assert code == 1, output
    assert not list(h.data.iterdir()) if h.data.exists() else True
    assert all(argv[0] != str(h.exporter) for argv, _ in h.calls)
    if case == "no-git":
        assert "Cannot verify private Git output" in output
        assert any("--show-toplevel" in argv for argv, _ in h.calls)
    elif case == "own-consumer":
        assert "Output cannot be inside the tool's own source checkout" in output
        assert not h.calls
    else:
        assert "verified PRIVATE visibility and identity" in output
        assert any(argv[0] == "gh" for argv, _ in h.calls)


def test_complete_tree_installed_alias(h, monkeypatch):
    alias = h.root / "installed-alias"
    if sys.platform == "win32":
        import _winapi
        _winapi.CreateJunction(str(ROOT), str(alias))
    else:
        alias.symlink_to(ROOT, target_is_directory=True)
    try:
        code, output = h.cli(monkeypatch, alias / "skills" / "discord-history-export" / "scripts" / "export_history.py",
            ["execute", "--exporter", h.exporter, "--credential-ref", "env:DISCORD_BOT_TOKEN",
             "--run-id", "synthetic-alias", "--channel-id", fixtures.IDS["channel"]])
        assert code == 0, output
    finally:
        if sys.platform == "win32":
            alias.rmdir()
        else:
            alias.unlink()


def test_missing_guard_hard_failure(h, monkeypatch):
    copied = h.root / "synthetic-install" / "skills" / "discord-history-export" / "scripts"
    shutil.copytree(SCRIPTS, copied, ignore=shutil.ignore_patterns("__pycache__"))
    code, output = h.cli(monkeypatch, copied / "export_history.py", ["plan", "--exporter", h.exporter,
        "--credential-ref", "env:DISCORD_BOT_TOKEN", "--run-id", "synthetic-missing-guard",
        "--channel-id", fixtures.IDS["channel"]])
    assert code == 1
    assert "submodule" in output
    assert not list(h.data.iterdir())


@pytest.mark.parametrize("kind", ["file", "missing-file", "empty-env"])
def test_local_credential_reference(h, monkeypatch, kind):
    path = h.root / "synthetic-credential.txt"
    if kind == "file":
        path.write_text(fixtures.SECRET, encoding="utf-8")
    reference = "env:EMPTY_SYNTHETIC_CREDENTIAL" if kind == "empty-env" else "file:" + str(path)
    monkeypatch.delenv("EMPTY_SYNTHETIC_CREDENTIAL", raising=False)
    code, output = h.export(monkeypatch, extra=["--credential-ref", reference])
    assert code == (0 if kind == "file" else 1), output
    assert fixtures.SECRET not in output
    if kind != "file":
        assert not list(h.data.iterdir())
        expected = "Credential file is unavailable" if kind == "missing-file" else "Credential is empty or malformed"
        assert expected in output
        assert any(argv[0] == "gh" for argv, _ in h.calls)
        assert [argv[1:] for argv, _ in h.calls if argv[0] == str(h.exporter)] == [
            ["--version"], ["exportguild", "--help"]]


def test_repeated_thread_names_keep_ids(h, monkeypatch):
    raw = h.root / "synthetic-threads"
    fixtures.populate(raw, channels=("thread", "other_thread"))
    target = h.data / "threads"
    code, output = h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])
    assert code == 0, output
    manifest = json.loads((target / "manifest.json").read_text())
    assert len({a["path"].casefold() for a in manifest["artifacts"]}) == 6
    assert {a["container_id"] for a in manifest["artifacts"] if a["format"] != "media"} == {fixtures.IDS["channel"]}


def test_rerun_checks_all_destinations_before_copy(h, monkeypatch):
    target = h.data / "organized"
    args = [h.raw, target, h.channels]
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 0
    next(target.rglob("*.html")).write_text("SYNTHETIC_TAMPER", encoding="utf-8")
    before = hashes(target)
    assert h.cli(monkeypatch, "reorganize.py", args)[0] == 1
    assert hashes(target) == before


def test_one_format_organizer_is_complete(h, monkeypatch):
    raw = h.root / "synthetic-html-only"
    fixtures.populate(raw, formats=("html",))
    target = h.data / "html-only"
    assert h.cli(monkeypatch, "reorganize.py", [raw, target, h.channels])[0] == 0
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["summary"]["json_count"] == manifest["summary"]["message_count"] == 0


def test_resume_after_process_interruption(h, monkeypatch):
    h.interrupt_format = "html"
    with pytest.raises(KeyboardInterrupt):
        h.export(monkeypatch)
    run = h.data / "runs" / "synthetic-run"
    before = hashes(run)
    h.interrupt_format = None
    code, output = h.export(monkeypatch, extra=["--resume"])
    assert code == 0, output
    assert all(hashlib.sha256((run / path).read_bytes()).hexdigest() == expected
               for path, expected in before.items() if path != "manifest.json")


def test_completed_manifest_counts_cannot_be_forged(h, monkeypatch):
    assert h.export(monkeypatch)[0] == 0
    path = h.data / "runs" / "synthetic-run" / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["summary"]["message_count"] += 1
    path.write_text(json.dumps(manifest), encoding="utf-8")
    code, output = h.export(monkeypatch)
    assert code == 1, output


def test_shared_resolver_uses_canonical_consumer_root():
    spec = importlib.util.spec_from_file_location("root_probe", SCRIPTS / "export_core.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    assert core.load_resolver()._own_repo_root() == str(ROOT.resolve())


def test_mixed_organizer_formats_must_reconcile(h, monkeypatch):
    next(h.raw.rglob("*.json")).unlink()
    target = h.data / "mismatched-formats"
    code, output = h.cli(monkeypatch, "reorganize.py", [h.raw, target, h.channels])
    assert code == 1, output
    assert not target.exists()
    assert "HTML and JSON channel ID sets are empty or differ" in output


def test_unproven_prerelease_cannot_borrow_release_evidence(h, monkeypatch):
    h.version = "2.47-unproven"
    code, output = h.export(monkeypatch)
    assert code == 1, output
    assert not list(h.data.iterdir())
    assert "Exporter credential transport is unproven" in output
    assert [argv[1:] for argv, _ in h.calls if argv[0] == str(h.exporter)] == [
        ["--version"], ["exportguild", "--help"]]


@pytest.mark.parametrize("mode", ["plan", "execute"])
@pytest.mark.parametrize("case", fixtures.selection_cases(),
                         ids=lambda case: case["kind"] + ("-existing" if case["exists"] else "-missing"))
def test_explicit_data_selection_never_falls_through(h, monkeypatch, case, mode):
    selected, selected_root = fixtures.selected_destination(h.root, ROOT, case)
    if selected_root:
        visibility = "PRIVATE" if case["allowed"] else case["kind"].upper()
        h.repositories[selected_root] = (case["repository"], visibility)
    h.data_override = str(selected)
    # This lower-priority companion is valid and available; its presence must not change intent.
    monkeypatch.setenv("DISCORD_HISTORY_EXPORT_CONFIG", str(h.companion))
    credential = h.root / "synthetic-selection-credential.txt"
    credential.write_text(fixtures.SECRET, encoding="utf-8")
    reads = []
    original_read = Path.read_text

    def observed_read(path, *args, **kwargs):
        if path == credential:
            reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", observed_read)
    fallback_before = hashes(h.companion)
    selected_existed = selected.exists()
    code, output = h.export(monkeypatch, mode=mode, extra=["--credential-ref", "file:" + str(credential)])
    assert hashes(h.companion) == fallback_before, "The unselected fallback companion was mutated"
    assert code == (0 if case["allowed"] else 1), output
    if not case["allowed"]:
        assert "environment overrides" not in output
        if case["kind"] in ("public", "unknown"):
            assert "verified PRIVATE visibility and identity" in output
            assert any(argv[0] == "gh" for argv, _ in h.calls)
        elif case["kind"] == "own-source":
            assert "Output cannot be inside the tool's own source checkout" in output
            assert not h.calls
        elif case["kind"] == "unversioned":
            assert "Cannot verify private Git output" in output
            assert any("--show-toplevel" in argv for argv, _ in h.calls)
    if mode == "plan" or not case["allowed"]:
        assert not reads
        assert all(argv[0] != str(h.exporter) for argv, _ in h.calls)
        assert selected.exists() == selected_existed
    if case["allowed"] and mode == "plan":
        assert json.loads(output)["run_directory"] == str((selected / "runs" / "synthetic-run").resolve())
    if case["allowed"] and mode == "execute":
        assert len(reads) == 1
        manifest = json.loads((selected / "runs" / "synthetic-run" / "manifest.json").read_text())
        assert manifest["status"] == "complete"
        assert manifest["companion"] == case["repository"]


@pytest.mark.parametrize("mode", ["plan", "execute"])
@pytest.mark.parametrize("override", ["", "   "], ids=["empty", "whitespace"])
def test_empty_explicit_data_selection_is_invalid(h, monkeypatch, mode, override):
    h.data_override = override
    monkeypatch.setenv("DISCORD_HISTORY_EXPORT_CONFIG", str(h.companion))
    before = hashes(h.companion)
    code, output = h.export(monkeypatch, mode=mode)
    assert code == 1, output
    assert hashes(h.companion) == before
    assert all(argv[0] != str(h.exporter) for argv, _ in h.calls)
    assert "DISCORD_HISTORY_EXPORT_DATA_DIR is empty" in output
    assert not h.calls



@pytest.mark.parametrize("case", fixtures.probe_environment_cases(),
                         ids=lambda case: case["platform"] + "-" + case["kind"])
def test_preflight_credentials_follow_platform_key_semantics(h, monkeypatch, case):
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location("synthetic_probe", SCRIPTS / "export_history.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "os", SimpleNamespace(name=case["platform"], environ=case["environment"]))
    monkeypatch.setattr(module.subprocess, "run", h.run)
    reference = "env:Discord_Bot_Token" if case["kind"] == "env" else "file:" + str(h.root / "synthetic-secret.txt")
    result = module.probe({"credential_ref": reference, "exporter": str(h.exporter), "guild_id": fixtures.IDS["guild"]})
    assert result["release"] == "2.47"
    expected = {key: value for key, value in case["environment"].items() if key not in case["excluded"]}
    assert len(h.calls) == 2
    assert all(environment == expected for _, environment in h.calls)


@pytest.mark.parametrize("case", fixtures.replay_receipt_cases())
def test_completed_replay_requires_unique_complete_archive_receipts(h, monkeypatch, case):
    code, output = h.export(monkeypatch, extra=["--media"])
    assert code == 0, output
    run = h.data / "runs" / "synthetic-run"
    path = run / "manifest.json"
    manifest = fixtures.altered_replay_receipt(json.loads(path.read_text(encoding="utf-8")), case)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    before = hashes(run)
    calls_before = len(h.calls)
    code, output = h.export(monkeypatch, extra=["--media"])
    assert code == 1, output
    assert hashes(run) == before
    assert all(argv[0] != str(h.exporter) for argv, _ in h.calls[calls_before:])


def source6_track_credential(h, monkeypatch):
    credential = fixtures.source6_credential(h.root)
    reads = []
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if path == credential:
            reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    return credential, reads


def source6_execute(h, monkeypatch, credential, action='execute', resume=False):
    args = [action, '--exporter', h.exporter, '--credential-ref', 'file:' + str(credential),
            '--run-id', 'synthetic-run', '--guild-id', fixtures.IDS['guild']]
    if resume:
        args.append('--resume')
    return h.cli(monkeypatch, 'export_history.py', args)


def source6_bind_ssh_verifier(monkeypatch, configuration):
    """Bind the shared parser to one synthetic config and retain read/result witnesses."""
    original_spec = importlib.util.spec_from_file_location
    original_read = Path.read_bytes
    observations = {"reads": [], "problems": []}

    def read(path):
        data = original_read(path)
        if path == configuration:
            observations["reads"].append(data)
        return data

    def spec_for(name, path, *args, **kwargs):
        spec = original_spec(name, path, *args, **kwargs)
        if name == "discord_export_shared_boundary":
            assert Path(path) == ROOT / "guards" / "tools" / "data_boundary.py"
            original_exec = spec.loader.exec_module

            def load(module):
                original_exec(module)
                monkeypatch.setattr(module, "_ssh_config_paths", lambda: [str(configuration)])
                original_verifier = module._ssh_configuration_problem

                def verify():
                    problem = original_verifier()
                    observations["problems"].append(problem)
                    return problem

                monkeypatch.setattr(module, "_ssh_configuration_problem", verify)

            monkeypatch.setattr(spec.loader, "exec_module", load)
        return spec

    monkeypatch.setattr(Path, "read_bytes", read)
    monkeypatch.setattr(importlib.util, "spec_from_file_location", spec_for)
    return observations


@pytest.mark.parametrize('case', fixtures.source6_publication_cases(), ids=lambda case: case['id'])
def test_source6_effective_publication_route_denies_before_activity(h, monkeypatch, case):
    credential, reads = source6_track_credential(h, monkeypatch)
    base = h.run

    def route(argv, **kwargs):
        args = list(map(str, argv))
        output = None
        if args[0] == 'git':
            tail = args[args.index('-C') + 2:]
            if 'remote.origin.url' in tail:
                output = case['nominal']
            elif tail == ['remote']:
                output = '\n'.join(case['routes'])
            elif tail[:2] == ['remote', 'get-url']:
                output = '\n'.join(case['routes'][tail[-1]]['push' if '--push' in tail else 'fetch'])
            elif '--list' in tail:
                rows = [('remote.' + name + '.url', values['fetch'][0]) for name, values in case['routes'].items()]
                rows.extend(case['config'])
                output = ''.join(key + '\n' + value + '\0' for key, value in rows)
        elif args[0] == 'gh':
            slug = args[3].removeprefix('https://github.com/')
            output = json.dumps({'visibility': case['visibility'].get(slug, 'UNKNOWN'), 'nameWithOwner': slug})
        if output is None:
            return base(argv, **kwargs)
        h.calls.append((args, kwargs.get('env')))
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr='')

    h.run = route
    for key, value in case['environment'].items():
        monkeypatch.setenv(key, value)
    if case.get('ssh_config'):
        home = h.root / 'synthetic-ssh-home'
        (home / '.ssh').mkdir(parents=True)
        configuration = home / '.ssh/config'
        configuration.write_bytes(case['ssh_config'].encode('utf-8'))
        ssh_observations = source6_bind_ssh_verifier(monkeypatch, configuration)
    before = sorted(str(path.relative_to(h.data)) for path in h.data.rglob('*'))
    code, output = source6_execute(h, monkeypatch, credential)
    if case['allowed']:
        assert code == 0, output
        assert reads == [credential]
    else:
        assert code == 1, output
        assert reads == []
        assert all(argv[0] != str(h.exporter) for argv, _ in h.calls)
        assert sorted(str(path.relative_to(h.data)) for path in h.data.rglob('*')) == before
        if case['environment']:
            assert 'environment overrides prevent private destination proof' in output
            assert not h.calls
        else:
            assert any('--list' in argv for argv, _ in h.calls)
            if case['id'] in ('custom-remote-command', 'ssh-command-config'):
                assert 'Custom Git transport configuration' in output
            elif case['id'] == 'unknown-pushremote':
                assert 'selected publication remote has no verifiable configured destination' in output
            elif case['id'] == 'ssh-active-proxy':
                assert 'shared static verifier' in output
                assert ssh_observations['reads'] == [case['ssh_config'].encode('utf-8')]
                assert ssh_observations['problems'] == [
                    'SSH configuration contains an unproven active option']
                configuration.write_bytes(case['safe_ssh_config'].encode('utf-8'))
                ssh_observations['reads'].clear()
                ssh_observations['problems'].clear()
                h.calls.clear()
                safe_code, safe_output = source6_execute(h, monkeypatch, credential, action='plan')
                assert safe_code == 0, safe_output
                assert ssh_observations['reads']
                assert all(data == case['safe_ssh_config'].encode('utf-8')
                           for data in ssh_observations['reads'])
                assert ssh_observations['problems']
                assert all(problem is None for problem in ssh_observations['problems'])
                assert any(argv[0] == 'gh' for argv, _ in h.calls)
                assert reads == [] and all(argv[0] != str(h.exporter) for argv, _ in h.calls)
                assert sorted(str(path.relative_to(h.data)) for path in h.data.rglob('*')) == before
            elif case.get('http_policy'):
                assert 'shared static HTTPS verifier' in output
                assert all(argv[0] != 'gh' for argv, _ in h.calls)
            else:
                assert 'verified PRIVATE visibility and identity' in output
                assert any(argv[0] == 'gh' for argv, _ in h.calls)


@pytest.mark.parametrize('case', fixtures.source6_nested_destination_cases(), ids=lambda case: case['id'])
def test_source6_nested_run_parent_private_proof_precedes_activity(h, monkeypatch, case):
    credential, reads = source6_track_credential(h, monkeypatch)
    nested = fixtures.source6_nested_repository(h.data / 'runs', linked=case['linked'])
    h.repositories[nested] = (case['repository'], case['visibility'])
    before = hashes(h.data)
    tree_before = sorted(str(path.relative_to(h.data)) for path in h.data.rglob('*'))
    code, output = source6_execute(h, monkeypatch, credential, case['action'])
    if case['allowed']:
        assert code == 0, output
        assert reads == ([] if case['action'] == 'plan' else [credential])
    else:
        assert code == 1, output
        assert reads == []
        assert all(argv[0] != str(h.exporter) for argv, _ in h.calls)
        assert hashes(h.data) == before
        assert sorted(str(path.relative_to(h.data)) for path in h.data.rglob('*')) == tree_before
        assert 'verified PRIVATE visibility and identity' in output
        assert any(argv[:4] == ['gh', 'repo', 'view', 'https://github.com/' + case['repository']]
                   for argv, _ in h.calls)


@pytest.mark.parametrize('case', [case for case in fixtures.source6_nested_destination_cases() if not case['allowed']])
def test_source6_completed_replay_rechecks_nested_repository(h, monkeypatch, case):
    credential, reads = source6_track_credential(h, monkeypatch)
    assert source6_execute(h, monkeypatch, credential)[0] == 0
    nested = fixtures.source6_nested_repository(h.data / 'runs' / 'synthetic-run')
    h.repositories[nested] = (case['repository'], case['visibility'])
    before = hashes(nested)
    reads.clear()
    h.calls.clear()
    code, output = source6_execute(h, monkeypatch, credential, case['action'])
    assert code == 1, output
    assert reads == [] and all(argv[0] != str(h.exporter) for argv, _ in h.calls)
    assert hashes(nested) == before


@pytest.mark.parametrize('case', [case for case in fixtures.source6_nested_destination_cases()
                                if not case['allowed'] and case['action'] == 'execute'])
@pytest.mark.parametrize('relative', ['raw/html', 'organized/archive'])
def test_source6_resume_rechecks_future_artifact_destinations(h, monkeypatch, case, relative):
    credential, reads = source6_track_credential(h, monkeypatch)
    h.fail_format = 'json'
    assert source6_execute(h, monkeypatch, credential)[0] == 1
    manifest = json.loads((h.data / 'runs' / 'synthetic-run' / 'manifest.json').read_text())
    assert manifest['status'] == 'partial'
    nested = fixtures.source6_nested_repository(h.data / 'runs' / 'synthetic-run' / 'attempts' / '0002' / relative)
    h.repositories[nested] = (case['repository'], case['visibility'])
    before = hashes(h.data)
    reads.clear()
    h.calls.clear()
    h.fail_format = None
    code, output = source6_execute(h, monkeypatch, credential, resume=True)
    assert code == 1, output
    assert reads == [] and all(argv[0] != str(h.exporter) for argv, _ in h.calls)
    assert hashes(h.data) == before
    assert 'verified PRIVATE visibility and identity' in output
    assert any(argv[:4] == ['gh', 'repo', 'view', 'https://github.com/' + case['repository']]
               for argv, _ in h.calls)


@pytest.mark.parametrize('case', [case for case in fixtures.source6_nested_destination_cases() if case['allowed']])
def test_source6_completed_replay_accepts_proven_private_nesting(h, monkeypatch, case):
    credential, reads = source6_track_credential(h, monkeypatch)
    assert source6_execute(h, monkeypatch, credential)[0] == 0
    nested = fixtures.source6_nested_repository(h.data / 'runs' / 'synthetic-run', linked=case['linked'])
    h.repositories[nested] = (case['repository'], case['visibility'])
    before = hashes(nested)
    reads.clear()
    h.calls.clear()
    code, output = source6_execute(h, monkeypatch, credential, case['action'])
    assert code == 0, output
    assert reads == [] and all(argv[0] != str(h.exporter) for argv, _ in h.calls)
    assert hashes(nested) == before


@pytest.mark.parametrize('case', [case for case in fixtures.source6_nested_destination_cases()
                                if case['action'] == 'execute'])
def test_source6_standalone_organizer_checks_nested_target_before_copy(h, monkeypatch, case):
    target = h.data / 'source6-organized'
    nested = fixtures.source6_nested_repository(target / 'archive', linked=case['linked'])
    h.repositories[nested] = (case['repository'], case['visibility'])
    before = hashes(h.data)
    code, output = h.cli(monkeypatch, 'reorganize.py', [h.raw, target, h.channels])
    assert code == 1, output  # An existing nonempty topology is preserved even when PRIVATE.
    assert hashes(h.data) == before
    if not case['allowed']:
        assert 'PRIVATE' in output
        assert 'verified PRIVATE visibility and identity' in output
    else:
        assert 'Existing output contains unrelated directories' in output
    assert any(argv[:4] == ['gh', 'repo', 'view', 'https://github.com/' + case['repository']]
               for argv, _ in h.calls)

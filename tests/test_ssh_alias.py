"""Generated SSH controls exercise the supported public proof and export CLI."""
import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from test_export import Harness, SCRIPTS, fixtures

SAMPLE = fixtures.ssh_alias_scenarios()


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("No real process or SSH command is permitted")
    monkeypatch.setattr(subprocess, "run", denied)
    spec = importlib.util.spec_from_file_location("alias_export_core", SCRIPTS / "export_core.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    configuration = tmp_path / ".ssh/config"
    configuration.parent.mkdir()
    fixtures.bind_synthetic_ssh_profile(monkeypatch, configuration)
    companion = tmp_path / "companion"
    companion.mkdir()
    (companion / ".git").mkdir()
    return core, configuration, companion


def metadata(core, companion, origin, visibility="PRIVATE"):
    calls = []
    def execute(argv, **kwargs):
        calls.append(argv)
        code = 0
        if argv[0] != "git":
            raise AssertionError("Only intercepted local Git is permitted")
        if "--show-toplevel" in argv:
            output = str(companion)
        elif "--absolute-git-dir" in argv:
            output = str(companion / ".git")
        elif "--verify" in argv:
            output = "1" * 40
        elif "check-ignore" in argv:
            output, code = "", 1
        elif "--list" in argv:
            output = "remote.origin.url\n" + origin + "\0"
        elif argv[-1] == "remote":
            output = "origin"
        elif "get-url" in argv:
            output = origin
        else:
            raise AssertionError("Unexpected local Git query: " + repr(argv))
        return subprocess.CompletedProcess(argv, code, output, "")
    fixtures.bind_public_boundary(core, companion.parent, execute,
                                 lambda: {SAMPLE["identity"]: visibility})
    return calls


@pytest.mark.parametrize("case,origin,config_text,accepted", SAMPLE["cases"])
def test_alias_destination(isolated, monkeypatch, case, origin, config_text, accepted):
    core, configuration, companion = isolated
    if config_text is not None:
        configuration.write_text(config_text, encoding="utf-8")
    calls = metadata(core, companion, origin)
    target = companion / "data/missing-child"
    if accepted:
        assert core.private_destination(target) == (target.resolve(), SAMPLE["identity"])
        assert any("check-ignore" in call for call in calls)
    else:
        with pytest.raises(core.ExportError, match="Cannot verify private Git output"):
            core.private_destination(target)
        assert any("--show-toplevel" in call for call in calls)
        assert any("get-url" in call for call in calls)
    assert all(call[0] == "git" for call in calls)
    assert not target.parent.exists()


@pytest.mark.parametrize("visibility", ["PRIVATE", "PUBLIC", None])
def test_canonical_requires_actual_private_visibility(isolated, monkeypatch, visibility):
    core, configuration, companion = isolated
    configuration.write_text(SAMPLE["ordinary"], encoding="utf-8")
    calls = metadata(core, companion, "https://github.com/" + SAMPLE["identity"] + ".git", visibility)
    target = companion / "data"
    if visibility == "PRIVATE":
        assert core.private_destination(target) == (target.resolve(), SAMPLE["identity"])
    else:
        with pytest.raises(core.ExportError, match="verified PRIVATE visibility and identity"):
            core.private_destination(target)
    assert all(call[0] == "git" for call in calls)
    assert not target.exists()


@pytest.mark.parametrize("mode", ["plan", "execute"])
@pytest.mark.parametrize("visibility", ["PRIVATE", "PUBLIC", None])
def test_alias_export_cli(isolated, tmp_path, monkeypatch, mode, visibility):
    core, configuration, companion = isolated
    configuration.write_text(SAMPLE["ordinary"], encoding="utf-8")
    harness = Harness(tmp_path)
    harness.visibility = visibility
    harness.receipt_override = {SAMPLE["identity"]: visibility}
    ordinary_run = harness.run
    def alias_run(argv, **kwargs):
        if argv[0] == "git" and ("remote.origin.url" in argv or "get-url" in argv):
            harness.calls.append((argv, kwargs.get("env")))
            return subprocess.CompletedProcess(argv, 0, SAMPLE["origin"], "")
        return ordinary_run(argv, **kwargs)
    harness.run = alias_run
    credential = tmp_path / "synthetic-alias-credential.txt"
    credential.write_text(fixtures.SECRET, encoding="utf-8")
    reads = []
    original_read = Path.read_text
    def observed_read(path, *args, **kwargs):
        if path == credential:
            reads.append(path)
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", observed_read)
    code, output = harness.export(monkeypatch, mode=mode, extra=["--credential-ref", "file:" + str(credential)])
    assert code == (0 if visibility == "PRIVATE" else 1), output
    assert reads == ([credential] if mode == "execute" and visibility == "PRIVATE" else [])
    assert all(call[0][0] != "gh" for call in harness.calls)
    assert any("get-url" in call[0] for call in harness.calls)
    if visibility != "PRIVATE" or mode == "plan":
        assert not list(harness.data.iterdir())
        assert all(call[0][0] != str(harness.exporter) for call in harness.calls)


def test_https_never_reads_ssh_config(isolated, monkeypatch):
    core, configuration, companion = isolated
    original_read = Path.read_bytes
    def guarded(path, *args, **kwargs):
        if path == configuration:
            raise AssertionError("HTTPS verification must not consult SSH configuration")
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    target = companion / "data"
    metadata(core, companion, "https://github.com/" + SAMPLE["identity"] + ".git")
    assert core.private_destination(target) == (target.resolve(), SAMPLE["identity"])
    metadata(core, companion, "https://" + SAMPLE["alias"] + "/" + SAMPLE["identity"] + ".git")
    with pytest.raises(core.ExportError):
        core.private_destination(target)


@pytest.mark.parametrize("name,problem,raises,allowed", fixtures.source6_ssh_verifier_cases())
def test_supported_proof_adapter_propagates_failure(isolated, monkeypatch, name, problem, raises, allowed):
    core, configuration, companion = isolated
    calls = []
    def prove(destination):
        calls.append(name)
        if raises:
            raise OSError("synthetic verifier failure")
        if problem:
            raise RuntimeError(problem)
        return SimpleNamespace(root=str(companion), repositories=(SAMPLE["identity"],), signature="synthetic")
    def read(proof, *arguments):
        return subprocess.CompletedProcess(arguments, 1 if arguments[0] == "check-ignore" else 0, "1" * 40, "")
    monkeypatch.setattr(core, "load_boundary", lambda: SimpleNamespace(
        prove_private_companion=prove, read_private_companion_git=read))
    target = companion / "data"
    if allowed:
        assert core.private_destination(target) == (target.resolve(), SAMPLE["identity"])
    else:
        with pytest.raises(core.ExportError, match="Cannot verify private Git output"):
            core.private_destination(target)
    assert calls == [name]

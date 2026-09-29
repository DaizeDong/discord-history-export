"""Generated SSH alias controls exercise the destination proof and export CLI."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from test_export import Harness, ROOT, SCRIPTS, fixtures

SAMPLE = fixtures.ssh_alias_scenarios()


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    def denied(*args, **kwargs):
        raise AssertionError('No real process or SSH command is permitted')
    monkeypatch.setattr(subprocess, 'run', denied)
    spec = importlib.util.spec_from_file_location('alias_export_core', SCRIPTS/'export_core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    config = tmp_path/'.ssh/config'
    config.parent.mkdir()
    companion = tmp_path/'companion'
    companion.mkdir()
    (companion/'.git').mkdir()
    return core, config, companion


def metadata(monkeypatch, companion, origin, visibility='PRIVATE'):
    calls = []
    def execute(argv, **kwargs):
        calls.append(argv)
        if argv[0] == 'git' and '--show-toplevel' in argv:
            output = str(companion)
        elif argv[0] == 'git' and 'remote.origin.url' in argv:
            output = origin
        elif argv[:3] == ['gh', 'repo', 'view']:
            assert argv[3] == SAMPLE['identity']
            output = json.dumps({'visibility': visibility})
        else:
            raise AssertionError('Unexpected process, including SSH: '+repr(argv))
        return subprocess.CompletedProcess(argv, 0, output, '')
    monkeypatch.setattr(subprocess, 'run', execute)
    return calls


@pytest.mark.parametrize('case,origin,config_text,accepted', SAMPLE['cases'])
def test_alias_destination(isolated, monkeypatch, case, origin, config_text, accepted):
    core, config, companion = isolated
    if config_text is not None:
        config.write_text(config_text, encoding='utf8')
    calls = metadata(monkeypatch, companion, origin)
    target = companion/'data/missing-child'
    if accepted:
        assert core.private_destination(target) == (target.resolve(), SAMPLE['identity'])
        assert any(call[0] == 'gh' for call in calls)
    else:
        with pytest.raises(core.ExportError):
            core.private_destination(target)
    assert not target.parent.exists()


@pytest.mark.parametrize('visibility', ['PRIVATE', 'PUBLIC', None])
def test_alias_requires_actual_private_visibility(isolated, monkeypatch, visibility):
    core, config, companion = isolated
    config.write_text(SAMPLE['ordinary'], encoding='utf8')
    calls = metadata(monkeypatch, companion, SAMPLE['origin'], visibility)
    target = companion/'data'
    if visibility == 'PRIVATE':
        assert core.private_destination(target) == (target.resolve(), SAMPLE['identity'])
    else:
        with pytest.raises(core.ExportError):
            core.private_destination(target)
    assert any(call[0] == 'gh' for call in calls)
    assert not target.exists()


@pytest.mark.parametrize('mode', ['plan', 'execute'])
@pytest.mark.parametrize('visibility', ['PRIVATE', 'PUBLIC', None])
def test_alias_export_cli(isolated, tmp_path, monkeypatch, mode, visibility):
    core, config, companion = isolated
    config.write_text(SAMPLE['ordinary'], encoding='utf8')
    harness = Harness(tmp_path)
    harness.visibility = visibility
    ordinary_run = harness.run
    def alias_run(argv, **kwargs):
        if argv[0] == 'git' and 'remote.origin.url' in argv:
            harness.calls.append((argv, None))
            return subprocess.CompletedProcess(argv, 0, SAMPLE['origin'], '')
        if argv[:3] == ['gh', 'repo', 'view']:
            assert argv[3] == SAMPLE['identity']
        return ordinary_run(argv, **kwargs)
    harness.run = alias_run
    credential = tmp_path/'synthetic-alias-credential.txt'
    credential.write_text(fixtures.SECRET, encoding='utf8')
    reads = []
    original_read = Path.read_text
    def observed_read(path, *args, **kwargs):
        if path == credential:
            reads.append(path)
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', observed_read)
    code, output = harness.export(monkeypatch, mode=mode, extra=['--credential-ref', 'file:'+str(credential)])
    assert code == (0 if visibility == 'PRIVATE' else 1), output
    assert any(call[0][0] == 'gh' for call in harness.calls)
    if mode == 'plan' or visibility != 'PRIVATE':
        assert not reads
        assert not list(harness.data.iterdir())
        assert all(call[0][0] != str(harness.exporter) for call in harness.calls)
    else:
        assert len(reads) == 1
        manifest = json.loads((harness.data/'runs/synthetic-run/manifest.json').read_text())
        assert manifest['status'] == 'complete'
        assert manifest['companion'] == SAMPLE['identity']


def test_https_never_reads_ssh_config(isolated, monkeypatch):
    core, config, companion = isolated
    original_read = Path.read_text
    def guarded(path, *args, **kwargs):
        if path == config:
            raise AssertionError('HTTPS verification must not consult SSH configuration')
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', guarded)
    target = companion/'data'
    metadata(monkeypatch, companion, 'https://github.com/'+SAMPLE['identity']+'.git')
    assert core.private_destination(target) == (target.resolve(), SAMPLE['identity'])
    metadata(monkeypatch, companion, 'https://'+SAMPLE['alias']+'/'+SAMPLE['identity']+'.git')
    with pytest.raises(core.ExportError):
        core.private_destination(target)

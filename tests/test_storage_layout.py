"""Exercise layout path checks with generated companions; no subprocess runs."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fixtures'))
from test_native_storage import NativeCompanion, native_export


@pytest.mark.parametrize('relative', ['.', 'exports', 'data/nested'])
def test_undeclared_data_root_rejected_before_exporter_or_credentials(relative, tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    observations = {}
    history, arguments, reads = native_export(native, observations=observations)
    monkeypatch.setenv('DISCORD_HISTORY_EXPORT_DATA_DIR', str(native.repository / relative))
    before = native.files()
    assert history.main(arguments) == 1
    assert reads == []
    assert observations.get('exporter_calls', []) == []
    assert native.files() == before


@pytest.mark.parametrize('relative', ['data/arbitrary/archive', 'data/runs/acme/organized',
                                      'data/organized', 'data', 'data/raw/acme'])
def test_standalone_rejects_wrong_owner_before_reading_inputs(relative, tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    monkeypatch.setattr(native.core, 'parse_channels', lambda path: pytest.fail('read before placement check'))
    before = native.files()
    with pytest.raises(native.core.ExportError, match='standalone_archive artifact must be written beneath'):
        native.core.organize(tmp_path / 'raw', native.repository / relative, tmp_path / 'channels.txt')
    assert native.files() == before
    assert native.calls == []


@pytest.mark.parametrize('relative', ['data/organized/acme', 'data/runs', 'data/arbitrary/acme'])
def test_runner_owner_rejects_paths_outside_runs(relative, tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    monkeypatch.setattr(native.core, 'parse_channels', lambda path: pytest.fail('read before placement check'))
    before = native.files()
    with pytest.raises(native.core.ExportError, match='runs artifact must be written beneath'):
        native.core.organize(tmp_path / 'raw', native.repository / relative, tmp_path / 'channels.txt',
                             artifact_id='runs')
    assert native.files() == before
    assert native.calls == []


def test_unknown_archive_owner_is_refused(tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    with pytest.raises(native.core.ExportError, match='Unknown archive artifact'):
        native.core.authorize_archive(native.repository / 'data/organized/acme', 'readme', directory=True)


@pytest.mark.parametrize('relative,artifact_id', [
    ('data/organized/acme', 'standalone_archive'),
    ('data/runs/acme/organized', 'runs'),
])
def test_organizer_declared_owners_write_complete_archives(relative, artifact_id, tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    import make_fixtures
    raw = tmp_path / 'raw'
    make_fixtures.populate(raw)
    channels = tmp_path / 'channels.txt'
    channels.write_text(make_fixtures.records()['channels'], encoding='utf-8')
    destination = native.repository / relative
    result = native.core.organize(raw, destination, channels, artifact_id=artifact_id)
    assert result['status'] == 'complete'
    assert (destination / 'manifest.json').is_file()


@pytest.mark.parametrize('linked', [False, True])
def test_nested_run_root_refuses_before_exporter_or_credentials(linked, tmp_path, monkeypatch):
    native = NativeCompanion(tmp_path, monkeypatch)
    nested = native.repository / 'data/runs'
    nested.mkdir(parents=True)
    if linked:
        (nested / '.git').write_text('gitdir: ../../.git/worktrees/runs\n', encoding='utf-8')
    else:
        (nested / '.git').mkdir()
    observations = {}
    history, arguments, reads = native_export(native, observations=observations)
    before = native.files()
    assert history.main(arguments) == 1
    assert reads == []
    assert observations.get('exporter_calls', []) == []
    assert native.files() == before

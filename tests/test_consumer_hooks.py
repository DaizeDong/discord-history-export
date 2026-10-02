"""Exercise the shipped forwarding hooks with generated inert delegates."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hook_fixtures", ROOT / "tools/make_fixtures.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


@pytest.mark.parametrize("hook", ["pre-commit", "pre-push"])
@pytest.mark.parametrize("kind", ["missing", "empty", "directory", "valid", "failure"])
def test_consumer_hook_contract(tmp_path, hook, kind):
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX sh is required to exercise Git hooks")
    fixture = fixtures.review10_hook(
        tmp_path, hook, (ROOT / ".githooks" / hook).read_bytes(), kind,
    )
    env = {key: value for key, value in os.environ.items()
           if key.upper() not in {"BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "CDPATH"}
           and not key.upper().startswith("BASH_FUNC_")}
    result = subprocess.run(
        [shell, str(fixture["path"]), *fixture["args"]],
        input=fixture["stdin"], text=True, capture_output=True,
        cwd=tmp_path, env=env, timeout=15, check=False,
    )
    assert result.returncode == fixture["expected_exit"], result.stdout + result.stderr
    if kind in {"valid", "failure"}:
        assert result.stdout == fixture["expected_stdout"]
        assert result.stderr == ""
    else:
        assert "BLOCKED:" in result.stdout
        assert "synthetic-guard-ran" not in result.stdout

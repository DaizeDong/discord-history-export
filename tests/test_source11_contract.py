"""Complete-module regressions use only generator-backed synthetic records."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/discord-history-export/scripts"


def load_complete(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures = load_complete("source11_fixtures", ROOT / "tools/make_fixtures.py")


def hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class Proxy:
    def __init__(self, original, **overrides):
        self.original, self.overrides = original, overrides

    def __getattr__(self, name):
        return self.overrides[name] if name in self.overrides else getattr(self.original, name)


class SyntheticExport:
    def __init__(self, root, kind="html", case="valid"):
        self.root = Path(root)
        self.workspace = fixtures.source11_workspace(self.root)
        self.data = self.workspace["data"]
        self.env = dict(self.workspace["environment"])
        self.calls, self.kind, self.case = [], kind, case
        self.config, self.inject = None, None
        self.core = load_complete("source11_core", SCRIPTS / "export_core.py")
        self.core.os = Proxy(os, environ=self.env)
        self.core.subprocess = Proxy(subprocess, run=self.run)
        self.core.load_resolver = lambda: SimpleNamespace(resolve_data_dir=lambda *a, **k: self.data)
        self.proofs = fixtures.bind_public_boundary(self.core, self.root, self.run,
                                                     lambda: {self.workspace["slug"]: "PRIVATE"}, self.env)
        previous = sys.modules.get("export_core")
        previous_path = list(sys.path)
        sys.modules["export_core"] = self.core
        try:
            self.history = load_complete("source11_history", SCRIPTS / "export_history.py")
        finally:
            sys.path[:] = previous_path
            if previous is None:
                sys.modules.pop("export_core", None)
            else:
                sys.modules["export_core"] = previous
        self.history.os = self.core.os
        self.history.subprocess = self.core.subprocess

    def run(self, argv, **kwargs):
        args = list(map(str, argv))
        self.calls.append((args, dict(kwargs.get("env", {}))))
        slug = self.workspace["slug"]
        if args[0] == "git":
            if "--absolute-git-dir" in args:
                output = str(self.workspace["companion"] / ".git")
            elif "--verify" in args:
                output = "1" * 40
            elif "check-ignore" in args:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
            elif "rev-parse" in args:
                output = str(self.workspace["companion"])
            elif "config" in args:
                output = "remote.origin.url\nhttps://github.com/" + slug + ".git\0"
                if self.config is not None:
                    output += self.config[0] + "\n" + self.config[1] + "\0"
            elif "get-url" in args:
                output = "https://github.com/" + slug + ".git"
            elif args[-1] == "remote":
                output = "origin"
            else:
                raise AssertionError("Unexpected synthetic Git command")
            if self.inject and len(self.calls) == 1:
                self.env.update(self.inject)
        elif args[0] == self.workspace["exporter"]:
            if "--version" in args:
                output = "2.47"
            elif "--help" in args:
                output = "Synthetic export command"
            else:
                assert kwargs["env"]["DISCORD_TOKEN"] == fixtures.SECRET
                assert fixtures.SECRET not in " ".join(args)
                fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
                target = Path(args[args.index("-o") + 1].partition("%t")[0])
                fixtures.source11_archive(target, self.kind, self.case, (fmt,))
                output = ""
        else:
            raise AssertionError("No real process is permitted")
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    def main(self, action="execute", resume=False):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = self.history.main(fixtures.source11_cli(self.workspace["exporter"], action, resume))
        return status, output.getvalue() + errors.getvalue()

    def exporter_calls(self):
        return [call for call in self.calls if call[0][0] == self.workspace["exporter"]]

    @property
    def run_directory(self):
        return self.data / "runs/synthetic-run"


class Source11Contract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="synthetic-source11-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.serial = 0

    def harness(self, kind="html", case="valid"):
        self.serial += 1
        return SyntheticExport(self.root / str(self.serial), kind, case)

    def test_environment_and_plan_boundary(self):
        for label, environment, allowed in fixtures.source11_environment_cases():
            with self.subTest(case=label):
                h = self.harness()
                h.env.update(environment)
                code, output = h.main("plan")
                self.assertEqual(code, 0 if allowed else 1, output)
                self.assertFalse(h.data.exists())
                self.assertFalse(h.exporter_calls())
                if not allowed:
                    self.assertFalse(h.calls)

    def test_git_trust_configuration(self):
        for key, value, allowed in fixtures.source11_transport_configs():
            with self.subTest(case=key):
                h = self.harness()
                h.config = (key, value)
                code, output = h.main("plan")
                self.assertEqual(code, 0 if allowed else 1, output)
                self.assertFalse(h.data.exists())
                self.assertFalse(h.exporter_calls())

    def test_environment_snapshot_is_bound_and_rechecked(self):
        h = self.harness()
        h.inject = h.workspace["mutation"]
        h.core.private_destination(h.data)
        self.assertEqual(len(h.proofs), 1)
        self.assertTrue(h.calls)
        for _, environment in h.calls:
            self.assertTrue(set(h.inject).isdisjoint(environment))
            self.assertEqual(environment["GIT_OPTIONAL_LOCKS"], "0")
        count = len(h.calls)
        with self.assertRaises(h.core.ExportError):
            h.core.private_destination(h.data)
        self.assertEqual(len(h.calls), count)
        with self.assertRaises(AttributeError):
            h.proofs[0].proof.signature = "synthetic-change"

    def check_archive_paths(self, kind, case, allowed):
        h = self.harness(kind, case)
        raw, target = h.root / "raw", h.data / "organized" / "archive"
        fixtures.source11_archive(raw, kind, case)
        before = hashes(raw)
        if allowed:
            result = h.core.organize(raw, target, h.workspace["channels"])
            self.assertEqual(result["status"], "complete")
            self.assertEqual(hashes(target / "archive"), before)
        else:
            with self.assertRaises(h.core.ExportError):
                h.core.organize(raw, target, h.workspace["channels"])
            self.assertFalse(target.exists())
        self.assertEqual(hashes(raw), before)

        h = self.harness(kind, case)
        code, output = h.main()
        self.assertEqual(code, 0 if allowed else 1, output)
        run = h.run_directory
        first = hashes(run / "attempts/0001")
        if allowed:
            calls = len(h.exporter_calls())
            self.assertEqual(h.main()[0], 0)
            self.assertEqual(len(h.exporter_calls()), calls)
        else:
            self.assertFalse((run / "attempts/0001/organized").exists())
            self.assertEqual(h.main()[0], 1)
            h.case = "valid" if kind == "html" else "literal-present"
            self.assertEqual(h.main(resume=True)[0], 0)
        self.assertEqual(hashes(run / "attempts/0001"), first)

        if not allowed:
            valid = "valid" if kind == "html" else "comment-only"
            h = self.harness(kind, valid)
            self.assertEqual(h.main()[0], 0)
            fixtures.source11_legacy_complete(h.run_directory, kind, case)
            before, calls = hashes(h.run_directory), len(h.exporter_calls())
            self.assertEqual(h.main()[0], 1)
            self.assertEqual(hashes(h.run_directory), before)
            self.assertEqual(len(h.exporter_calls()), calls)

    def test_html_business_paths(self):
        for case, allowed in fixtures.source11_html_cases():
            with self.subTest(case=case):
                self.check_archive_paths("html", case, allowed)

    def test_css_business_paths(self):
        for case, _, _, allowed in fixtures.source11_css_cases():
            with self.subTest(case=case):
                self.check_archive_paths("css", case, allowed)

    def test_existing_html_scenarios_remain_applicable(self):
        for case, allowed in fixtures.source7_html_cases():
            with self.subTest(case=case):
                h = self.harness()
                raw = h.root / "legacy-html"
                fixtures.source11_archive(raw, "legacy-html", case)
                if allowed:
                    self.assertTrue(h.core.inspect_archive(raw))
                else:
                    with self.assertRaises(h.core.ExportError):
                        h.core.inspect_archive(raw)

    def test_existing_css_scenarios_remain_applicable(self):
        for case, allowed in fixtures.source9_css_cases():
            with self.subTest(case=case):
                h = self.harness()
                raw = h.root / "legacy-css"
                fixtures.source9_populate_css(raw, case)
                if allowed:
                    self.assertTrue(h.core.inspect_archive(raw))
                else:
                    with self.assertRaises(h.core.ExportError):
                        h.core.inspect_archive(raw)


if __name__ == "__main__":
    unittest.main()

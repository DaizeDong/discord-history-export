"""Generator-owned stylesheet roles through pure inspection and ordinary business paths."""
import ast
from collections import Counter
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys
import tempfile
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]


def production_source():
    return (ROOT / "skills/discord-history-export/scripts/export_core.py").read_bytes()


def fixture_source():
    return (ROOT / "tools/make_fixtures.py").read_bytes()


def fixture_bytes():
    return (ROOT / "tests/fixtures/source14-cases.json").read_bytes()


def generated_cases():
    tree = ast.parse(fixture_source())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {"html_archive", "source14_stylesheet_cases", "source14_css_role_cases"}]
    nodes[:0] = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "IDS" for target in node.targets)]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<source14-generator-functions>", "exec"), namespace)
    return namespace["source14_stylesheet_cases"](), namespace["source14_css_role_cases"]()


class MemoryArchive:
    """Use actual inspection definitions with bounded, read-only in-memory paths."""
    def __init__(self, raw, files):
        self.blobs = {name: bytes.fromhex(value) for name, value in files.items()}
        self.original = dict(self.blobs)
        self.reads = Counter()
        world = self

        class MemoryPath(PurePosixPath):
            def resolve(self):
                return type(self)(posixpath.normpath(str(self)))

            def is_file(self):
                try:
                    relative = self.relative_to("/synthetic-archive").as_posix()
                except ValueError:
                    return False
                return relative in world.blobs

            def read_bytes(self):
                relative = self.relative_to("/synthetic-archive").as_posix()
                world.reads[relative] += 1
                return world.blobs[relative]

        self.root = MemoryPath("/synthetic-archive")
        namespace = {
            "Path": MemoryPath, "HTMLParser": HTMLParser, "re": re, "json": json,
            "hashlib": hashlib, "unquote": unquote, "urlsplit": urlsplit,
            "os": SimpleNamespace(path=posixpath),
            "files_under": lambda root: sorted(root / name for name in self.blobs),
        }
        definitions = {"ExportError", "digest", "contains", "srcset_links", "LocalLinks",
                       "css_unescape", "css_links", "ArchiveHTML", "json_links",
                       "local_target", "inspect_archive"}
        tree = ast.parse(raw)
        nodes = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in definitions]
        nodes[:0] = [node for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id in {"NUMERIC_ID", "FILE_ID"}
                             for target in node.targets)]
        assert {node.name for node in nodes if isinstance(node, (ast.FunctionDef, ast.ClassDef))} == definitions
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<source14-inspection>", "exec"), namespace)
        self.core = SimpleNamespace(**namespace)
        self.steps = 0

    def inspect(self):
        previous = sys.gettrace()

        def bounded(frame, event, argument):
            if event == "line" and frame.f_code.co_filename == "<source14-inspection>":
                self.steps += 1
                if self.steps > 50000:
                    raise AssertionError("Synthetic inspection exceeded its deterministic step budget")
            return bounded

        try:
            sys.settrace(bounded)
            return self.core.inspect_archive(self.root)
        finally:
            sys.settrace(previous)


class Source14PureContract(unittest.TestCase):
    def test_generator_fixture_parity(self):
        cases, roles = generated_cases()
        self.assertEqual(fixture_bytes(), (json.dumps(cases, indent=2) + "\n").encode())
        self.assertEqual(len(cases), 40)
        self.assertEqual(len({case["name"] for case in cases}), 40)
        self.assertEqual(len(roles), 10)

    def test_css_roles_preserve_default_url_list(self):
        _, roles = generated_cases()
        core = MemoryArchive(production_source(), {}).core
        for name, text, links, stylesheet_links in roles:
            with self.subTest(case=name):
                self.assertEqual(core.css_links(text), links)
                found = set()
                self.assertEqual(core.css_links(text, stylesheet_links=found), links)
                self.assertEqual(found, set(stylesheet_links))

    def test_complete_assets_ownership_cycles_and_original_bytes(self):
        for case in json.loads(fixture_bytes()):
            with self.subTest(case=case["name"]):
                archive = MemoryArchive(production_source(), case["files"])
                if case["allowed"]:
                    entries = archive.inspect()
                    self.assertEqual({row["source"] for row in entries}, set(archive.blobs))
                    for row in entries:
                        content = archive.blobs[row["source"]]
                        self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
                        self.assertEqual(row["size_bytes"], len(content))
                        self.assertEqual(row["path"], "archive/" + row["source"])
                        if row["format"] == "media":
                            self.assertEqual(row["channel_ids"], case["owners"][row["source"]])
                            self.assertEqual(row["channel_id"], case["owners"][row["source"]][0])
                else:
                    with self.assertRaises(archive.core.ExportError):
                        archive.inspect()
                self.assertEqual(archive.blobs, archive.original)
                self.assertEqual(archive.reads, Counter({name: 1 for name in archive.blobs}))
                self.assertGreater(archive.steps, 0)
                self.assertLessEqual(archive.steps, 50000)


def load_business_support():
    spec = importlib.util.spec_from_file_location("source14_business_prior", ROOT / "tests/test_source11_contract.py")
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    return prior


class Source14BusinessContract(unittest.TestCase):
    def test_organize_execute_resume_and_complete_replay(self):
        prior = load_business_support()
        cases = json.loads(fixture_bytes())
        by_name = {case["name"]: case for case in cases}

        class SyntheticExport14(prior.SyntheticExport):
            def __init__(self, root, case):
                super().__init__(root)
                self.case14 = case

            def run(self, argv, **kwargs):
                result = super().run(argv, **kwargs)
                args = list(map(str, argv))
                if args[0] == self.workspace["exporter"] and "-o" in args:
                    target = Path(args[args.index("-o") + 1].partition("%t")[0])
                    fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
                    prior.fixtures.source14_archive(target, self.case14, (fmt,))
                return result

        with tempfile.TemporaryDirectory(prefix="synthetic-source14-") as temporary:
            root = Path(temporary)
            for index, case in enumerate(cases):
                repaired = by_name.get(case["name"].removesuffix("-missing") + "-present")
                if not case["business"] or (not case["allowed"] and repaired is None):
                    continue
                with self.subTest(case=case["name"]):
                    harness = SyntheticExport14(root / str(index) / "organize", case)
                    raw, target = harness.root / "raw", harness.data / "organized" / "archive"
                    prior.fixtures.source14_archive(raw, case)
                    before = prior.hashes(raw)
                    if case["allowed"]:
                        result = harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertEqual(result["status"], "complete")
                        self.assertEqual(prior.hashes(target / "archive"), before)
                        self.assertEqual({row["source"] for row in result["artifacts"]}, set(before))
                    else:
                        with self.assertRaises(harness.core.ExportError):
                            harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertFalse(target.exists())
                    self.assertEqual(prior.hashes(raw), before)

                    harness = SyntheticExport14(root / str(index) / "execute", case)
                    status, output = harness.main()
                    self.assertEqual(status, 0 if case["allowed"] else 1, output)
                    first = prior.hashes(harness.run_directory / "attempts/0001")
                    if case["allowed"]:
                        calls = len(harness.exporter_calls())
                        self.assertEqual(harness.main()[0], 0)
                        self.assertEqual(len(harness.exporter_calls()), calls)
                    else:
                        self.assertFalse((harness.run_directory / "attempts/0001/organized").exists())
                        self.assertEqual(harness.main()[0], 1)
                        harness.case14 = repaired
                        self.assertEqual(harness.main(resume=True)[0], 0)
                    self.assertEqual(prior.hashes(harness.run_directory / "attempts/0001"), first)


if __name__ == "__main__":
    unittest.main()

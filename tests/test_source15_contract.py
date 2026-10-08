"""Generator-owned file-URL rejection with original portable/archive behavior."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_source14_contract import MemoryArchive, load_business_support

ROOT = Path(__file__).resolve().parents[1]


def source15_production():
    return (ROOT / "skills/discord-history-export/scripts/export_core.py").read_bytes()


def source15_fixture_bytes():
    return (ROOT / "tests/fixtures/source15-cases.json").read_bytes()


def source15_generator_source():
    return (ROOT / "tools/make_fixtures.py").read_bytes()


def source15_generated():
    tree = ast.parse(source15_generator_source())
    wanted = {"html_archive", "source15_file_link_cases", "source15_archive_cases"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    nodes[:0] = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "IDS" for target in node.targets)]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<source15-generator>", "exec"), namespace)
    return {"links": namespace["source15_file_link_cases"](),
            "archives": namespace["source15_archive_cases"]()}


class Source15PureContract(unittest.TestCase):
    def test_generated_fixture_parity(self):
        cases = source15_generated()
        self.assertEqual(source15_fixture_bytes(), (json.dumps(cases, indent=2) + "\n").encode())
        self.assertEqual(len(cases["links"]), 18)
        self.assertEqual(len(cases["archives"]), 24)

    def test_local_target_classifies_file_before_authority(self):
        fixtures = json.loads(source15_fixture_bytes())
        direct_files = next(case["files"] for case in fixtures["archives"]
                            if case["name"] == "image-portable-present")
        archive = MemoryArchive(source15_production(), direct_files)
        for case in fixtures["links"]:
            with self.subTest(case=case["name"]):
                if case["result"] in ("absolute", "missing"):
                    message = "absolute local link" if case["result"] == "absolute" else "missing or escaping"
                    with self.assertRaisesRegex(archive.core.ExportError, message):
                        archive.core.local_target(archive.root, archive.root, case["link"])
                else:
                    result = archive.core.local_target(archive.root, archive.root, case["link"])
                    self.assertEqual(result, archive.root / "media/asset.bin" if case["result"] == "local" else None)
                self.assertEqual(archive.blobs, archive.original)
                self.assertFalse(archive.reads)

    def test_complete_html_inspection_preserves_bytes(self):
        for case in json.loads(source15_fixture_bytes())["archives"]:
            with self.subTest(case=case["name"]):
                archive = MemoryArchive(source15_production(), case["files"])
                if case["allowed"]:
                    entries = archive.inspect()
                    self.assertEqual({row["source"] for row in entries}, set(archive.blobs))
                    for row in entries:
                        self.assertEqual(row["sha256"], hashlib.sha256(archive.blobs[row["source"]]).hexdigest())
                        self.assertEqual(row["size_bytes"], len(archive.blobs[row["source"]]))
                        if row["format"] == "media":
                            self.assertEqual(row["channel_ids"], case["owners"][row["source"]])
                else:
                    with self.assertRaises(archive.core.ExportError):
                        archive.inspect()
                self.assertEqual(archive.blobs, archive.original)
                self.assertEqual(archive.reads, Counter({name: 1 for name in archive.blobs}))


class Source15BusinessContract(unittest.TestCase):
    def test_organize_execute_resume_and_complete_replay(self):
        prior = load_business_support()
        cases = json.loads(source15_fixture_bytes())["archives"]
        by_name = {case["name"]: case for case in cases}

        class SyntheticExport15(prior.SyntheticExport):
            def __init__(self, root, case):
                super().__init__(root)
                self.case15 = case

            def run(self, argv, **kwargs):
                result = super().run(argv, **kwargs)
                args = list(map(str, argv))
                if args[0] == self.workspace["exporter"] and "-o" in args:
                    target = Path(args[args.index("-o") + 1].partition("%t")[0])
                    fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
                    prior.fixtures.source14_archive(target, self.case15, (fmt,))
                return result

        with tempfile.TemporaryDirectory(prefix="synthetic-source15-") as temporary:
            for index, case in enumerate(cases):
                with self.subTest(case=case["name"]):
                    root = Path(temporary) / str(index)
                    harness = SyntheticExport15(root / "organize", case)
                    raw, target = harness.root / "raw", harness.data / "organized" / "archive"
                    prior.fixtures.source14_archive(raw, case)
                    before = prior.hashes(raw)
                    if case["allowed"]:
                        result = harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertEqual(result["status"], "complete")
                        self.assertEqual(prior.hashes(target / "archive"), before)
                    else:
                        with self.assertRaises(harness.core.ExportError):
                            harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertFalse(target.exists())
                    self.assertEqual(prior.hashes(raw), before)

                    harness = SyntheticExport15(root / "execute", case)
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
                        harness.case15 = by_name[case["repair"]]
                        self.assertEqual(harness.main(resume=True)[0], 0)
                    self.assertEqual(prior.hashes(harness.run_directory / "attempts/0001"), first)


if __name__ == "__main__":
    unittest.main()

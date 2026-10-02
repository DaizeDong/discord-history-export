"""Generated local-file URL and unsupported base semantics through archive paths."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urljoin

from test_source14_contract import MemoryArchive, load_business_support

ROOT = Path(__file__).resolve().parents[1]


def production_source():
    return (ROOT / "skills/discord-history-export/scripts/export_core.py").read_bytes()


def fixture_bytes():
    return (ROOT / "tests/fixtures/source16-cases.json").read_bytes()


def generated_cases():
    tree = ast.parse((ROOT / "tools/make_fixtures.py").read_bytes())
    wanted = {"html_archive", "source16_link_cases", "source16_archive_cases"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    nodes[:0] = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "IDS" for target in node.targets)]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<source16-generator>", "exec"), namespace)
    return {"links": namespace["source16_link_cases"](), "archives": namespace["source16_archive_cases"]()}


class Source16PureContract(unittest.TestCase):
    def test_generated_fixture_parity(self):
        cases = generated_cases()
        self.assertEqual(fixture_bytes(), (json.dumps(cases, indent=2) + "\n").encode())
        self.assertEqual(len(cases["links"]), 10)
        self.assertEqual(len(cases["archives"]), 26)
        self.assertEqual(len({case["name"] for case in cases["archives"]}), 26)

    def test_file_base_uri_semantics_and_preserved_source15_cases(self):
        fixture = json.loads((ROOT / "tests/fixtures/source15-cases.json").read_bytes())
        cases = [case for case in fixture["archives"] if case["name"].endswith("-protocol-relative")]
        self.assertEqual({case["name"] for case in cases}, {
            "image-protocol-relative", "anchor-protocol-relative",
            "inline-css-protocol-relative", "linked-css-protocol-relative",
        })
        self.assertTrue(all(case["allowed"] is False for case in cases))
        base = "file:///synthetic/archive/channel.html"
        self.assertEqual(urljoin(base, "//example.com/synthetic.bin"), "file://example.com/synthetic.bin")
        self.assertEqual(urljoin(base, "https://example.com/synthetic.bin"), "https://example.com/synthetic.bin")
        self.assertEqual(urljoin(urljoin(base, "media/base.bin"), "media/asset.bin"),
                         "file:///synthetic/archive/media/media/asset.bin")

    def test_direct_url_classification(self):
        fixtures = json.loads(fixture_bytes())
        files = next(case["files"] for case in fixtures["archives"] if case["name"] == "portable-image")
        archive = MemoryArchive(production_source(), files)
        for case in fixtures["links"]:
            with self.subTest(case=case["name"]):
                if case["result"] in {"absolute", "missing"}:
                    message = "absolute local link" if case["result"] == "absolute" else "missing or escaping"
                    with self.assertRaisesRegex(archive.core.ExportError, message):
                        archive.core.local_target(archive.root, archive.root, case["link"])
                else:
                    value = archive.core.local_target(archive.root, archive.root, case["link"])
                    self.assertEqual(value, archive.root / "media/asset.bin" if case["result"] == "local" else None)
                self.assertEqual(archive.blobs, archive.original)
                self.assertFalse(archive.reads)

    def test_archive_base_scope_and_media_integrity(self):
        for case in json.loads(fixture_bytes())["archives"]:
            with self.subTest(case=case["name"]):
                archive = MemoryArchive(production_source(), case["files"])
                if case["allowed"]:
                    entries = archive.inspect()
                    self.assertEqual({row["source"] for row in entries}, set(archive.blobs))
                    for row in entries:
                        self.assertEqual(row["sha256"], hashlib.sha256(archive.blobs[row["source"]]).hexdigest())
                        self.assertEqual(row["size_bytes"], len(archive.blobs[row["source"]]))
                        if row["format"] == "media":
                            self.assertEqual(row["channel_ids"], case["owners"][row["source"]])
                else:
                    with self.assertRaisesRegex(archive.core.ExportError, case["issue"]):
                        archive.inspect()
                self.assertEqual(archive.blobs, archive.original)
                self.assertEqual(archive.reads, Counter({name: 1 for name in archive.blobs}))


def business_harness_type(prior):
    class SyntheticExport16(prior.SyntheticExport):
        def __init__(self, root, case):
            super().__init__(root)
            self.case16 = case

        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            args = list(map(str, argv))
            if args[0] == self.workspace["exporter"] and "-o" in args:
                target = Path(args[args.index("-o") + 1].partition("%t")[0])
                fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
                prior.fixtures.source14_archive(target, self.case16, (fmt,))
            return result

    return SyntheticExport16


class Source16BusinessContract(unittest.TestCase):
    def test_organize_execute_resume_and_complete_replay(self):
        prior = load_business_support()
        Harness = business_harness_type(prior)
        cases = json.loads(fixture_bytes())["archives"]
        by_name = {case["name"]: case for case in cases}
        with tempfile.TemporaryDirectory(prefix="synthetic-source16-") as temporary:
            for index, case in enumerate(cases):
                with self.subTest(case=case["name"]):
                    root = Path(temporary) / str(index)
                    harness = Harness(root / "organize", case)
                    raw, target = harness.root / "raw", harness.data / "organized"
                    prior.fixtures.source14_archive(raw, case)
                    before = prior.hashes(raw)
                    if case["allowed"]:
                        result = harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertEqual(result["status"], "complete")
                        self.assertEqual(prior.hashes(target / "archive"), before)
                    else:
                        with self.assertRaisesRegex(harness.core.ExportError, case["issue"]):
                            harness.core.organize(raw, target, harness.workspace["channels"])
                        self.assertFalse(target.exists())
                    self.assertEqual(prior.hashes(raw), before)
                    harness = Harness(root / "execute", case)
                    status, output = harness.main()
                    self.assertEqual(status, 0 if case["allowed"] else 1, output)
                    first = prior.hashes(harness.run_directory / "attempts/0001")
                    if case["allowed"]:
                        calls = len(harness.exporter_calls())
                        self.assertEqual(harness.main()[0], 0)
                        self.assertEqual(len(harness.exporter_calls()), calls)
                    else:
                        self.assertIn(case["issue"], output)
                        self.assertFalse((harness.run_directory / "attempts/0001/organized").exists())
                        self.assertEqual(harness.main()[0], 1)
                        harness.case16 = by_name[case["repair"]]
                        self.assertEqual(harness.main(resume=True)[0], 0)
                    self.assertEqual(prior.hashes(harness.run_directory / "attempts/0001"), first)

    def test_old_complete_replay_rejects_unsupported_url_context(self):
        prior = load_business_support()
        Harness = business_harness_type(prior)
        cases = [case for case in json.loads(fixture_bytes())["archives"] if not case["allowed"]]
        with tempfile.TemporaryDirectory(prefix="synthetic-source16-replay-") as temporary:
            for index, case in enumerate(cases):
                with self.subTest(case=case["name"]):
                    seed = prior.fixtures.source16_replay_seed(case)
                    harness = Harness(Path(temporary) / str(index), seed)
                    self.assertEqual(harness.main()[0], 0)
                    prior.fixtures.source16_legacy_complete(harness.run_directory, case)
                    before, calls = prior.hashes(harness.run_directory), len(harness.exporter_calls())
                    for resume in (False, True):
                        status, output = harness.main(resume=resume)
                        self.assertEqual(status, 1, output)
                        self.assertIn(case["issue"], output)
                        self.assertIn("new run ID", output)
                        self.assertEqual(prior.hashes(harness.run_directory), before)
                        self.assertEqual(len(harness.exporter_calls()), calls)


if __name__ == "__main__":
    unittest.main()

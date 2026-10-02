"""Generated source13 dependency cases through complete local business paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source13_prior", ROOT / "tests/test_source11_contract.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
fixtures = prior.fixtures


class SyntheticExport13(prior.SyntheticExport):
    def __init__(self, root, case):
        super().__init__(root)
        self.case13 = case

    def run(self, argv, **kwargs):
        result = super().run(argv, **kwargs)
        args = list(map(str, argv))
        if args[0] == self.workspace["exporter"] and "-o" in args:
            target = Path(args[args.index("-o") + 1].partition("%t")[0])
            fmt = "json" if args[args.index("-f") + 1] == "Json" else "html"
            fixtures.source13_archive(target, self.case13, (fmt,))
        return result


class Source13Contract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="synthetic-source13-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.serial = 0

    def harness(self, case):
        self.serial += 1
        return SyntheticExport13(self.root / str(self.serial), case)

    def check_business_paths(self, case):
        h = self.harness(case)
        raw, target = h.root / "raw", h.data / "organized"
        fixtures.source13_archive(raw, case)
        before = prior.hashes(raw)
        if case["allowed"]:
            result = h.core.organize(raw, target, h.workspace["channels"])
            self.assertEqual(result["status"], "complete")
            self.assertEqual(prior.hashes(target / "archive"), before)
            self.assertEqual({item["source"] for item in result["artifacts"]}, set(before))
        else:
            with self.assertRaises(h.core.ExportError):
                h.core.organize(raw, target, h.workspace["channels"])
            self.assertFalse(target.exists())
        self.assertEqual(prior.hashes(raw), before)

        h = self.harness(case)
        status, output = h.main()
        self.assertEqual(status, 0 if case["allowed"] else 1, output)
        first = prior.hashes(h.run_directory / "attempts/0001")
        if case["allowed"]:
            calls = len(h.exporter_calls())
            self.assertEqual(h.main()[0], 0)
            self.assertEqual(len(h.exporter_calls()), calls)
        else:
            self.assertFalse((h.run_directory / "attempts/0001/organized").exists())
            self.assertEqual(h.main()[0], 1)
            h.case13 = dict(case, present=True, allowed=True)
            self.assertEqual(h.main(resume=True)[0], 0)
        self.assertEqual(prior.hashes(h.run_directory / "attempts/0001"), first)

    def test_css_token_dependencies(self):
        h = self.harness(fixtures.source13_css_cases()[0])
        for name, css, expected in fixtures.source13_css_forms():
            with self.subTest(case=name):
                self.assertEqual(h.core.css_links(css), expected)

    def test_css_resource_business_paths(self):
        for case in fixtures.source13_css_cases():
            with self.subTest(case=case["name"]):
                self.check_business_paths(case)

    def test_svg_resource_business_paths(self):
        for case in fixtures.source13_svg_cases():
            with self.subTest(case=case["name"]):
                self.check_business_paths(case)

    def test_invalid_complete_replay_preserves_existing_run(self):
        cases = [case for case in fixtures.source13_css_cases() + fixtures.source13_svg_cases()
                 if not case["allowed"]]
        for case in cases:
            with self.subTest(case=case["name"]):
                valid = fixtures.source13_valid_replay_case(case)
                h = self.harness(valid)
                self.assertEqual(h.main()[0], 0)
                fixtures.source13_complete_with_missing_dependency(h.run_directory, case)
                before, calls = prior.hashes(h.run_directory), len(h.exporter_calls())
                self.assertEqual(h.main()[0], 1)
                self.assertEqual(prior.hashes(h.run_directory), before)
                self.assertEqual(len(h.exporter_calls()), calls)


if __name__ == "__main__":
    unittest.main()

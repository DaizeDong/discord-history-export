"""Complete archive paths for generated SVG and srcset regression records."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source12_prior_contract', ROOT / 'tests/test_source11_contract.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
fixtures = prior.fixtures


class SyntheticExport12(prior.SyntheticExport):
    def __init__(self, root, case):
        super().__init__(root)
        self.case12 = case

    def run(self, argv, **kwargs):
        result = super().run(argv, **kwargs)
        args = list(map(str, argv))
        if args[0] == self.workspace['exporter'] and '-o' in args:
            target = Path(args[args.index('-o') + 1].partition('%t')[0])
            fmt = 'json' if args[args.index('-f') + 1] == 'Json' else 'html'
            fixtures.source12_archive(target, self.case12, (fmt,))
        return result


class Source12Contract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='synthetic-source12-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.serial = 0

    def harness(self, case):
        self.serial += 1
        return SyntheticExport12(self.root / str(self.serial), case)

    def check_business_paths(self, case, allowed):
        h = self.harness(case)
        raw, target = h.root / 'raw', h.data / 'organized' / 'archive'
        fixtures.source12_archive(raw, case)
        before = prior.hashes(raw)
        if allowed:
            self.assertEqual(h.core.organize(raw, target, h.workspace['channels'])['status'], 'complete')
            self.assertEqual(prior.hashes(target / 'archive'), before)
        else:
            with self.assertRaises(h.core.ExportError):
                h.core.organize(raw, target, h.workspace['channels'])
            self.assertFalse(target.exists())
        self.assertEqual(prior.hashes(raw), before)

        h = self.harness(case)
        status, output = h.main()
        self.assertEqual(status, 0 if allowed else 1, output)
        first = prior.hashes(h.run_directory / 'attempts/0001')
        if allowed:
            calls = len(h.exporter_calls())
            self.assertEqual(h.main()[0], 0)
            self.assertEqual(len(h.exporter_calls()), calls)
        else:
            self.assertFalse((h.run_directory / 'attempts/0001/organized').exists())
            self.assertEqual(h.main()[0], 1)
            h.case12 = 'svg-use'
            self.assertEqual(h.main(resume=True)[0], 0)
        self.assertEqual(prior.hashes(h.run_directory / 'attempts/0001'), first)

    def test_svg_foreign_content_in_complete_archive_paths(self):
        for case, allowed in fixtures.source12_svg_cases():
            if allowed:
                with self.subTest(case=case):
                    self.check_business_paths(case, True)

    def test_ordinary_html_self_closing_and_unclosed_svg_still_fail(self):
        for case, allowed in fixtures.source12_svg_cases():
            if not allowed:
                with self.subTest(case=case):
                    self.check_business_paths(case, False)

    def test_srcset_url_tokens_preserve_data_and_path_commas(self):
        core = self.harness('svg-use').core
        for case, value, expected in fixtures.source12_srcset_cases():
            with self.subTest(case=case):
                self.assertEqual(core.srcset_links(value), expected)

    def test_srcset_present_assets_in_complete_archive_paths(self):
        for case, _, _ in fixtures.source12_srcset_cases():
            with self.subTest(case=case):
                self.check_business_paths(case, True)

    def test_srcset_missing_local_assets_block_every_archive_path(self):
        for case, _, _ in fixtures.source12_srcset_cases():
            with self.subTest(case=case):
                self.check_business_paths(case + '-missing', False)


if __name__ == '__main__':
    unittest.main()

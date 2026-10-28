"""Fail-closed contracts; run with python3 -m unittest discover -s tests -p 'html_mockup*_test.py'."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'skills/ai-project-kickoff-html-mockup/assets'


def module(name):
    path = ASSETS / (name + '.py')
    if not path.is_file():
        raise AssertionError(f'missing implementation: {path.name}')
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OverflowTests(unittest.TestCase):
    def setUp(self):
        self.tool = module('check-overflow')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.page = Path(self.tmp.name) / 'page.html'
        self.page.write_text('<html><body>test</body></html>')

    def result(self, **updates):
        value = dict(requested=390, innerWidth=390, clientWidth=390, overflow=0, offenders=[])
        value.update(updates)
        return subprocess.CompletedProcess([], 0, json.dumps(value), '')

    def run_main(self, result):
        with patch.object(self.tool.shutil, 'which', return_value='/fake/tool'), \
             patch.object(self.tool.subprocess, 'run', return_value=result), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.tool.main([str(self.page), '--widths=390'])

    def test_success_only_for_measured_requested_width(self):
        self.assertEqual(self.run_main(self.result()), 0)

    def test_actual_width_mismatch_fails(self):
        self.assertNotEqual(self.run_main(self.result(innerWidth=485, clientWidth=485)), 0)

    def test_empty_probe_output_fails(self):
        self.assertNotEqual(self.run_main(subprocess.CompletedProcess([], 0, '', '')), 0)

    def test_crashed_browser_fails_even_with_json(self):
        r = self.result()
        r.returncode = 1
        self.assertNotEqual(self.run_main(r), 0)

    def test_overflow_fails(self):
        self.assertNotEqual(self.run_main(self.result(overflow=19)), 0)

    def test_missing_file_fails(self):
        self.page.unlink()
        self.assertNotEqual(self.run_main(self.result()), 0)

    def test_missing_browser_fails(self):
        with patch.object(self.tool.shutil, 'which', return_value=None), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page)]), 0)

    def test_timeout_fails(self):
        with patch.object(self.tool.shutil, 'which', return_value='/fake/tool'), \
             patch.object(self.tool.subprocess, 'run', side_effect=subprocess.TimeoutExpired('node', 30)), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page), '--widths=390']), 0)

    def test_invalid_width_fails(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page), '--widths=abc']), 0)

    def test_all_widths_run_after_one_failed_probe(self):
        good = self.result(requested=768, innerWidth=768, clientWidth=768)
        with patch.object(self.tool.shutil, 'which', return_value='/fake/tool'), \
             patch.object(self.tool.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 1, '', ''), good]) as run, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page), '--widths=390,768']), 0)
            self.assertEqual(run.call_count, 2)


class MermaidTests(unittest.TestCase):
    def setUp(self):
        self.tool = module('render-mermaid')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.page = Path(self.tmp.name) / 'index.html'
        self.src = '<html><head><style>.mine{color:red}</style></head><body><figure class="mmd" data-mermaid><pre>graph TD\n A--&gt;B</pre></figure></body></html>'
        self.page.write_text(self.src)

    def test_missing_mmdc_nonzero_without_mutation(self):
        with patch.object(self.tool.shutil, 'which', return_value=None), contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page)]), 0)
        self.assertEqual(self.page.read_text(), self.src)

    def test_missing_file_nonzero(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(self.tool.main([str(self.page.parent/'missing.html')]), 0)

    def test_render_atomic_and_three_runs_idempotent(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120"><text x="5" y="20">A</text></svg>'
        with patch.object(self.tool, 'render', return_value=svg):
            self.tool.process(self.page)
            once = self.page.read_bytes()
            self.tool.process(self.page)
            self.tool.process(self.page)
        self.assertEqual(self.page.read_bytes(), once)
        self.assertIn(b'.mine{color:red}', once)
        self.assertIn(b'<svg', once)
        self.assertIn(b'<details>', once)
        self.assertIn(b'mmd wide', once)

    def test_small_graph_keeps_native_readable_width_on_mobile(self):
        with patch.object(self.tool, 'render', return_value='<svg viewBox="0 0 475 127"></svg>'):
            self.tool.process(self.page)
        self.assertIn('max-width:none', self.page.read_text())

    def test_renderer_failure_preserves_whole_file(self):
        self.page.write_text(self.src.replace('</body>', '<figure class="mmd" data-mermaid><pre>graph TD\n C--&gt;D</pre></figure></body>'))
        before = self.page.read_bytes()
        with patch.object(self.tool, 'render', side_effect=['<svg viewBox="0 0 20 20"></svg>', RuntimeError('render failed')]):
            with self.assertRaises(RuntimeError):
                self.tool.process(self.page)
        self.assertEqual(self.page.read_bytes(), before)

    def test_empty_card_not_silently_skipped(self):
        self.page.write_text('<figure class="mmd" data-mermaid></figure>')
        with self.assertRaises(ValueError):
            self.tool.process(self.page)

    def test_unsupported_card_not_silently_skipped(self):
        self.page.write_text('<div class="mmd"><pre>graph TD\nA--&gt;B</pre></div>')
        with self.assertRaises(ValueError):
            self.tool.process(self.page)

    def test_renderer_disables_root_html_labels(self):
        # Installed Mermaid gives root htmlLabels precedence over flowchart.htmlLabels.
        def fake_run(cmd, **kwargs):
            config = json.loads(Path(cmd[cmd.index('-c') + 1]).read_text())
            self.assertIs(config.get('htmlLabels'), False)
            Path(cmd[cmd.index('-o') + 1]).write_text('<svg viewBox="0 0 30 20"></svg>')
            return subprocess.CompletedProcess(cmd, 0, '', '')
        with patch.object(self.tool.shutil, 'which', return_value='/fake/tool'), \
             patch.object(self.tool.subprocess, 'run', side_effect=fake_run):
            self.assertIn('<svg', self.tool.render('flowchart LR\n A-->B'))

    def test_external_svg_resources_rejected(self):
        with self.assertRaises(ValueError):
            self.tool.validate_svg('<svg viewBox="0 0 10 10"><image href="https://example.invalid/a.png"/></svg>')


if __name__ == '__main__':
    unittest.main()

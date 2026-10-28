"""Package invariants only; these checks do not certify project decisions or compliance."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ('project-brief', 'research-record', 'prototype-record', 'architecture-decision',
             'task-packet', 'operations-runbook', 'startup-readiness', 'document-index', 'ai-handoff')


def headings(text):
    result, counts, fence = set(), {}, None
    for line in text.splitlines():
        f = re.match(r'^\s*(`{3,}|~{3,})', line)
        if f:
            if fence is None:
                fence = f.group(1)[0]
            elif f.group(1)[0] == fence:
                fence = None
            continue
        if fence:
            continue
        h = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not h:
            continue
        value = re.sub(r'<[^>]*>', '', h.group(1)).lower()
        value = ''.join(c for c in value if c in '-_' or not unicodedata.category(c).startswith(('P', 'S')))
        value = value.replace(' ', '-')
        n = counts.get(value, 0)
        counts[value] = n + 1
        result.add(value if n == 0 else f'{value}-{n}')
    return result


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.loads, self.ids, self.anchors = [], [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d:
            self.ids.append(d['id'])
        if tag == 'a' and d.get('href', '').startswith('#'):
            self.anchors.append(d['href'][1:])
        if tag in ('script', 'link', 'img', 'iframe', 'source', 'object'):
            for k in ('src', 'href', 'data'):
                if str(d.get(k, '')).startswith(('http:', 'https:', '//')):
                    self.loads.append(d[k])


class PackageIntegrity(unittest.TestCase):
    def test_two_discoverable_skill_entries(self):
        for name in ('ai-project-kickoff', 'html-mockup'):
            with self.subTest(skill=name):
                text = (ROOT / 'skills' / name / 'SKILL.md').read_text()
                self.assertTrue(text.startswith('---\n'))
                front = text.split('---', 2)[1]
                self.assertRegex(front, rf'(?m)^name: {name}$')
                self.assertRegex(front, r'(?m)^description: .+')
                self.assertLess(len(text.splitlines()), 500)

    def test_nine_templates_are_substantial(self):
        for name in TEMPLATES:
            with self.subTest(template=name):
                p = ROOT / 'skills/ai-project-kickoff/assets/templates' / (name + '.md')
                self.assertGreater(len(p.read_text().splitlines()), 15)

    def test_all_relative_markdown_targets_and_anchors_exist(self):
        errors, checked = [], 0
        for p in ROOT.rglob('*.md'):
            for match in re.finditer(r'\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"\n]*")?\)', p.read_text()):
                dest = unquote(match.group(1))
                parts = urlsplit(dest)
                if parts.scheme or dest.startswith('//'):
                    continue
                checked += 1
                target = (p.parent / parts.path).resolve() if parts.path else p.resolve()
                if not target.exists():
                    errors.append(f'{p.relative_to(ROOT)} -> {dest}: missing target')
                elif parts.fragment and target.is_file() and target.suffix == '.md':
                    if parts.fragment not in headings(target.read_text()):
                        errors.append(f'{p.relative_to(ROOT)} -> {dest}: missing anchor')
        self.assertGreater(checked, 20)
        self.assertEqual(errors, [])

    def test_final_report_is_self_contained_with_valid_anchors(self):
        p = Resources()
        p.feed((ROOT / 'docs/delivery-report.html').read_text())
        self.assertEqual(p.loads, [])
        self.assertEqual(len(p.ids), len(set(p.ids)))
        self.assertTrue(set(p.anchors) <= set(p.ids))
        self.assertGreaterEqual(len(p.anchors), 4)

    def test_no_concrete_secret_patterns_in_distributable_text(self):
        patterns = (r'gh[pousr]_[A-Za-z0-9]{25,}', r'github_pat_[A-Za-z0-9_]{30,}',
                    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', r'AKIA[A-Z0-9]{16}')
        for p in ROOT.rglob('*'):
            if not p.is_file() or p.suffix not in ('.md', '.html', '.json', '.yaml', '.yml'):
                continue
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, p.read_text()), str(p.relative_to(ROOT)))

    def test_document_code_fences_are_closed(self):
        for p in ROOT.rglob('*.md'):
            active = None
            for line in p.read_text().splitlines():
                m = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
                if m:
                    marker = m.group(1)
                    if active is None:
                        active = marker
                    elif marker[0] == active[0] and len(marker) >= len(active) and not m.group(2).strip():
                        active = None
            self.assertIsNone(active, str(p.relative_to(ROOT)))


if __name__ == '__main__':
    unittest.main()

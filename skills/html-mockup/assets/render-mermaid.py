#!/usr/bin/env python3
"""Render marked Mermaid figures atomically. Requires existing mmdc; never installs it."""
import argparse
import html
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

CARD = re.compile(r'<figure\b(?=[^>]*\bdata-mermaid\b)[^>]*>.*?</figure>', re.S | re.I)
PRE = re.compile(r'<pre\b[^>]*>(.*?)</pre>', re.S | re.I)
SVG = re.compile(r'<svg\b.*?</svg>', re.S | re.I)


class CardCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if 'mmd' in dict(attrs).get('class', '').split():
            self.count += 1


def validate_svg(svg):
    root = ET.fromstring(svg)
    if root.tag.split('}')[-1] != 'svg' or not root.get('viewBox'):
        raise ValueError('renderer returned no SVG/viewBox')
    for element in root.iter():
        if element.tag.split('}')[-1].lower() in ('script', 'iframe', 'foreignobject'):
            # htmlLabels=false is passed below; no embedded executable HTML is needed.
            raise ValueError('SVG contains executable/embedded HTML')
        for name, value in element.attrib.items():
            local = name.split('}')[-1].lower()
            if local.startswith('on') or (local in ('href', 'src') and not value.startswith('#')):
                raise ValueError('SVG contains event or external reference')
    if re.search(r'url\(\s*[\"\']?(?!#)[^)]+\)|@import', svg, re.I):
        raise ValueError('SVG contains external CSS resource')
    return svg


def render(source):
    mmdc = shutil.which('mmdc')
    if not mmdc:
        raise RuntimeError('mmdc unavailable: graph UNRENDERED; nothing installed')
    with tempfile.TemporaryDirectory(prefix='html-mockup-mermaid-') as directory:
        directory = Path(directory)
        inp, out, config = (directory / name for name in ('input.mmd', 'output.svg', 'config.json'))
        inp.write_text(source, encoding='utf-8')
        config.write_text('{"theme":"dark","htmlLabels":false,"flowchart":{"htmlLabels":false},"themeVariables":{"fontSize":"16px"}}')
        env = os.environ.copy()
        chrome = env.get('CHROME_PATH') or shutil.which('google-chrome') or shutil.which('chromium')
        if chrome:
            env['PUPPETEER_EXECUTABLE_PATH'] = chrome
        cmd = [mmdc, '-i', str(inp), '-o', str(out), '-c', str(config), '-b', 'transparent']
        # Opt-in for trusted isolated containers only; never silently disables sandbox.
        if env.get('HTML_MOCKUP_NO_SANDBOX') == '1':
            puppeteer = directory / 'puppeteer.json'
            puppeteer.write_text('{"args":["--no-sandbox"]}')
            cmd += ['-p', str(puppeteer)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        if result.returncode or not out.is_file():
            raise RuntimeError('Mermaid render failed: ' + (result.stderr or result.stdout)[-800:])
        raw = out.read_text(encoding='utf-8')
        match = SVG.search(raw)
        if not match:
            raise ValueError('renderer output is not SVG')
        return validate_svg(match.group(0))


def process(path, force=False):
    path = Path(path)
    original = path.read_text(encoding='utf-8')
    counter = CardCounter()
    counter.feed(original)
    cards = list(CARD.finditer(original))
    if counter.count != len(cards):
        raise ValueError('unsupported .mmd card: use <figure class="mmd" data-mermaid>')
    output = original
    rendered = 0
    for match in reversed(cards):
        card = match.group(0)
        old_svg = SVG.search(card)
        pre = PRE.search(card)
        if not pre or not html.unescape(pre.group(1)).strip():
            raise ValueError('Mermaid card has no nonempty source <pre>')
        if old_svg and not force:
            validate_svg(old_svg.group(0))
            continue
        source = html.unescape(pre.group(1)).strip()
        svg = validate_svg(render(source))
        viewbox = ET.fromstring(svg).get('viewBox').split()
        width = float(viewbox[2])
        if width <= 0:
            raise ValueError('invalid SVG width')
        kind = 'wide' if width > 900 else 'fit'
        # Keep native text size even for small graphs on phones; only the figure scrolls.
        head_end = svg.index('>')
        head = re.sub(r'\s(?:width|height|style)="[^"]*"', '', svg[:head_end])
        svg = head + f' width="{width:g}" style="max-width:none;height:auto"' + svg[head_end:]
        replacement = (f'<figure class="mmd {kind}" data-mermaid>{svg}\n'
                       f'<details><summary>Mermaid 源码</summary><pre>{html.escape(source)}</pre></details></figure>')
        output = output[:match.start()] + replacement + output[match.end():]
        rendered += 1
    if output != original:
        # No partial writes when a later card fails.
        mode = path.stat().st_mode
        with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(output)
        try:
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return len(cards), rendered


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pages', nargs='+', type=Path)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    failed = False
    for page in args.pages:
        try:
            count, rendered = process(page, args.force)
            print(f'{page}: diagrams={count} rendered={rendered} already-rendered={count-rendered}')
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, ET.ParseError) as exc:
            print(f'UNRENDERED: {page}: {exc}', file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Measure local HTML with Chrome CDP. Fail closed; no dependency installation or server."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pages', nargs='+', type=Path)
    parser.add_argument('--widths', default='390,768,1440')
    parser.add_argument('--chrome', default=os.environ.get('CHROME_PATH'))
    parser.add_argument('--screenshots', type=Path, help='Write browser PNGs to this explicitly requested directory; verify required content coverage')
    parser.add_argument('--no-sandbox', action='store_true', help='Only in a trusted isolated environment where Chrome sandbox cannot run')
    try:
        args = parser.parse_args(argv)
        widths = [int(w) for w in args.widths.split(',')]
        if not widths or any(w < 200 or w > 7680 for w in widths):
            raise ValueError('widths must be 200..7680 CSS pixels')
    except (ValueError, SystemExit) as exc:
        if isinstance(exc, SystemExit):
            return exc.code
        print(f'UNVERIFIED: {exc}', file=sys.stderr)
        return 2
    chrome = args.chrome or next((p for n in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser') if (p := shutil.which(n))), None)
    if not chrome and sys.platform == 'darwin':
        candidate = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        chrome = str(candidate) if candidate.is_file() else None
    node = shutil.which('node')
    if not chrome or not node:
        print('UNVERIFIED: requires existing Chrome/Chromium and Node >=22; nothing installed', file=sys.stderr)
        return 2
    failed = False
    for page in args.pages:
        if not page.is_file():
            print(f'UNVERIFIED: missing file: {page}', file=sys.stderr)
            failed = True
            continue
        for width in widths:
            cmd = [node, str(Path(__file__).with_name('probe-browser.mjs')), chrome, str(page.resolve()), str(width)]
            if args.screenshots:
                # A filename alone is insufficient when separate reports are both named index.html.
                import hashlib
                key = hashlib.sha256(str(page.resolve()).encode()).hexdigest()[:10]
                args.screenshots.mkdir(parents=True, exist_ok=True)
                cmd += ['--screenshot', str((args.screenshots / f'{page.stem}-{key}-{width}.png').resolve())]
            if args.no_sandbox:
                cmd.append('--no-sandbox')
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                if result.returncode:
                    raise RuntimeError((result.stderr or 'browser process failed').strip())
                measured = json.loads(result.stdout)
                if (measured['requested'] != width or measured['innerWidth'] != width
                        or not 0 < measured['clientWidth'] <= width):
                    raise ValueError(f'viewport mismatch: {measured}')
                if not isinstance(measured['overflow'], (int, float)) or not isinstance(measured['offenders'], list):
                    raise ValueError('invalid probe fields')
                print(f'{page} requested={width} measured={measured["innerWidth"]} client={measured["clientWidth"]} overflow={measured["overflow"]} offenders={len(measured["offenders"])}')
                if measured['overflow'] > 1 or measured['offenders']:
                    failed = True
                    print(json.dumps(measured['offenders'][:8], ensure_ascii=False), file=sys.stderr)
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError, RuntimeError) as exc:
                failed = True
                print(f'UNVERIFIED: {page} width={width}: {exc}', file=sys.stderr)
    if failed:
        print('FAIL / UNVERIFIED: at least one requested measurement did not pass', file=sys.stderr)
        return 1
    print('PASS: all requested files and exact viewports measured; no uncaught horizontal overflow')
    return 0


if __name__ == '__main__':
    sys.exit(main())

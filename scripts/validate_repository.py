"""Fast, dependency-free checks for tracked RR3 DevOps source and documentation."""
import ast
import plistlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r'(?<!\!)\[[^\]]+\]\(([^)]+)\)')
SHA_LINE = re.compile(r'^[0-9a-f]{64} \*[^\s]+$')


def fail(message):
    print(f'FAIL: {message}', file=sys.stderr)
    return False


def check_python():
    ok = True
    for path in (ROOT / 'build_4k_v3.py', ROOT / 'scripts' / 'build_debug_v1.py'):
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except SyntaxError as exc:
            ok = fail(f'{path.relative_to(ROOT)} does not parse: {exc}')
    return ok


def check_eds_profile():
    try:
        profile = plistlib.loads((ROOT / 'eds_god.plist').read_bytes())
    except (OSError, plistlib.InvalidFileException) as exc:
        return fail(f'eds_god.plist is invalid: {exc}')
    expected = {
        'PLIST_IDENTIFIER': 'iPad6,8',
        'EXPECTED_SCREEN_WIDTH': 2732,
        'EXPECTED_SCREEN_HEIGHT': 2048,
    }
    for key, value in expected.items():
        if profile.get(key) != value:
            return fail(f'eds_god.plist {key} is not {value!r}')
    return True


def check_checksums():
    lines = (ROOT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
    assets = [line for line in lines if line and not line.startswith('#')]
    if len(assets) != 5 or any(not SHA_LINE.fullmatch(line) for line in assets):
        return fail('SHA256SUMS.txt must contain five standard SHA-256 asset lines')
    return True


def check_all_flags_reference():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'generate_all_flags.py'), '--check'],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return fail(result.stderr.strip() or 'ALL_FLAGS reference validation failed')
    return True


def check_markdown_links():
    ok = True
    for path in ROOT.rglob('*.md'):
        text = path.read_text(encoding='utf-8')
        for target in MARKDOWN_LINK.findall(text):
            target = target.split('#', 1)[0].strip('<>')
            if not target or '://' in target or target.startswith('mailto:'):
                continue
            if not (path.parent / target).resolve().exists():
                ok = fail(f'broken local link in {path.relative_to(ROOT)}: {target}')
    return ok


def main():
    checks = (check_python, check_eds_profile, check_checksums,
              check_all_flags_reference, check_markdown_links)
    if all(check() for check in checks):
        print('Repository validation passed.')
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())

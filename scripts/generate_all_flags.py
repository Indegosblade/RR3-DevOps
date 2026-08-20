"""Generate the public runtime-tweakable reference from the overlay source."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'overlay' / 'rr3_overlay.m'
OUTPUT = ROOT / 'docs' / 'ALL_FLAGS.md'
PAIR = re.compile(r'@"(?P<key>(?:\\.|[^"\\])*)"\s*:\s*@"(?P<value>(?:\\.|[^"\\])*)"')
FLAG = re.compile(r'\{0x[0-9a-f]+,\s*"(?P<label>[^"]+)",\s*"(?P<description>[^"]+)"\}', re.DOTALL)


def block_after(source: str, marker: str) -> str:
    start = source.index(marker) + len(marker)
    end = source.index('\n    };', start)
    return source[start:end]


def unescape(value: str) -> str:
    return value.replace(r'\"', '"').replace(r'\\', '\\')


def pretty_name(value: str) -> str:
    words = []
    for part in value.split('_'):
        if not part:
            continue
        words.append(part if len(part) <= 3 and part.isupper() else part.capitalize())
    return ' '.join(words)


def render() -> str:
    source = SOURCE.read_text(encoding='utf-8')
    labels = dict((unescape(match['key']), unescape(match['value']))
                  for match in PAIR.finditer(block_after(source, 'g_catLabels = @{')))
    entries = [(unescape(match['key']), unescape(match['value']))
               for match in PAIR.finditer(block_after(source, 'g_tweakDescs = @{'))]
    if len(entries) != 887 or len(dict(entries)) != 887:
        raise ValueError(f'expected 887 unique tweakable descriptions, found {len(entries)} / {len(dict(entries))}')

    flag_block = block_after(source, 'static RR3Var g_flags[] = {')
    flags = [(match['label'], match['description']) for match in FLAG.finditer(flag_block)]
    if len(flags) != 8:
        raise ValueError(f'expected 8 BSS flags, found {len(flags)}')

    categories: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, description in entries:
        category = key.split('_', 1)[0] if '_' in key else 'OTHER'
        categories[category].append((key, description))

    lines = [
        '# All Runtime Tweakables and Research Flags',
        '',
        'This reference is generated from the **887 authored description mappings** in `overlay/rr3_overlay.m`. It is the complete description dataset shipped with the RR3 DevOps harness, grouped by the category menu shown in the overlay.',
        '',
        'A listed mapping is not a guarantee that the entry is registered or consumed in every game state. The tested final iOS runtime has exposed roughly 847 entries; some controls are conditional, scene-specific, unused in the final build, or overridden later by higher-priority game logic.',
        '',
        'RR3 DevOps verifies the recovered data path by writing through the live pointer and reading that location back. This confirms registry wiring, not that every entry was individually behavior-tested or will create a visible effect in the current scene.',
        '',
        '## Using descriptions in the overlay',
        '',
        'Press and hold a slider or its list row for about half a second to open the short information panel. It shows the control description, raw runtime name, type, current value, launch snapshot, range, and live-pointer address.',
        '',
        '## Debug Flags menu',
        '',
        'These eight BSS flags are separate research controls in the overlay’s **Debug Flags** menu. They are not part of the 887 tweakable-description mappings. Their descriptions are research interpretations of surviving symbols and behavior, not a guarantee that an individual flag restores a complete original developer panel.',
        '',
        '| Control | What it does |',
        '|---|---|',
    ]
    lines.extend(f'| {label} | {description} |' for label, description in flags)

    for category in sorted(categories):
        title = labels.get(category, pretty_name(category))
        lines.extend([
            '',
            f'## {title} menu (`{category}`)',
            '',
            '| Runtime control | What it does |',
            '|---|---|',
        ])
        lines.extend(f'| `{key}` | {description} |'
                     for key, description in sorted(categories[category]))

    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail when the generated document is stale')
    args = parser.parse_args()
    generated = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != generated:
            print('docs/ALL_FLAGS.md is stale; run scripts/generate_all_flags.py', file=sys.stderr)
            return 1
        print('ALL_FLAGS reference is current.')
        return 0
    OUTPUT.write_text(generated, encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

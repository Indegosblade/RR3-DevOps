"""Rebuild RR3 DevOps's own small importer-repair payload; no game inputs.

Zig 0.14.1 supplies Clang/LLD without an Apple SDK. The interface uses only
scalar AAPCS64 arguments shared with Darwin; x18 is reserved and no variadic,
aggregate, Objective-C ARC, TLS or platform-runtime code is compiled here.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['-target', 'aarch64-freestanding-none', '-Oz', '-ffreestanding', '-ffixed-x18',
         '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
         '-fvisibility=hidden', '-fPIC']


def render(payload, entry, source):
    encoded = base64.b85encode(payload).decode('ascii')
    lines = ['"""Generated from native.c by scripts/build_importer_payload.py; own repair glue only."""',
             'import base64', '', f'ENTRY = {entry:#x}',
             f'SOURCE_SHA256 = {hashlib.sha256(source).hexdigest()!r}',
             f'PAYLOAD_SHA256 = {hashlib.sha256(payload).hexdigest()!r}', 'PAYLOAD = base64.b85decode(']
    lines += ['    ' + repr(encoded[i:i+100]) for i in range(0, len(encoded), 100)]
    return '\n'.join(lines + [')', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Compare with the tracked generated payload')
    args = parser.parse_args()
    zig = str(args.zig.resolve())
    version = subprocess.check_output([zig, 'version'], text=True).strip()
    if version != '0.14.1':
        raise ValueError('Reproducible payload build expects Zig 0.14.1')
    parent = (ROOT / 'investigation').resolve()
    parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='importer-compile-', dir=parent) as temporary:
        work = Path(temporary).resolve()
        if not work.is_relative_to(parent) or work == parent:
            raise ValueError('Temporary build escaped investigation directory')
        env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(work / 'cache'), ZIG_LOCAL_CACHE_DIR=str(work / 'local'))
        obj, elf, binary = work / 'native.o', work / 'native.elf', work / 'native.bin'
        subprocess.run([zig, 'cc', *FLAGS, '-c', str(ROOT / 'importer_fix/native.c'), '-o', str(obj)], env=env, check=True)
        subprocess.run([zig, 'ld.lld', '-T', str(ROOT / 'importer_fix/native.ld'), '-o', str(elf), str(obj)], env=env, check=True)
        subprocess.run([zig, 'objcopy', '-O', 'binary', str(elf), str(binary)], env=env, check=True)
        data = elf.read_bytes()
        if data[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected little-endian ELF64 intermediate')
        entry = struct.unpack_from('<Q', data, 24)[0]
        payload = binary.read_bytes()
        if not 0 <= entry < len(payload) <= 8192:
            raise ValueError('Unexpected payload entry/size')
        source = (ROOT / 'importer_fix/native.c').read_text(encoding='utf-8').encode('utf-8')
        generated = render(payload, entry, source)
        target = ROOT / 'importer_fix/payload.py'
        if args.check:
            if target.read_text(encoding='utf-8') != generated:
                raise ValueError('Generated importer payload differs')
        else:
            target.write_text(generated, encoding='utf-8')
        if not work.is_relative_to(parent) or work == parent:
            raise ValueError('Refusing unverified temporary cleanup')
    print(f'Importer payload {"verified" if args.check else "rebuilt"}: {len(payload)} bytes, {hashlib.sha256(payload).hexdigest()}')


if __name__ == '__main__':
    main()

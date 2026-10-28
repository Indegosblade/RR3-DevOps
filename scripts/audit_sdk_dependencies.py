"""Read-only inventory of packaged Mach-O dependencies and SDK code ownership.

The report is a static dependency map, not proof that a framework is safe to
delete. No IPA entries, executable bytes, signing files or device state change.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import posixpath
import struct
import zipfile

ARM64 = 0x0100000C
LOAD_COMMANDS = {0xC: 'load', 0x80000018: 'weak', 0x8000001F: 'reexport',
                 0x80000023: 'upward', 0x20: 'lazy'}
SDK_CLASSES = ('FIRApp', 'FIRAnalytics', 'FIRRemoteConfig', 'GADMobileAds',
               'ALSdk', 'FBSDKApplicationDelegate')
INITIALIZATION_METHODS = {
    'RealRacingAppDelegate': {'InitialiseFirebase', 'EnableFirebaseCollection:',
                             'application:didFinishLaunchingWithOptions:'},
    'FIRApp': {'configure', 'configureWithOptions:', 'configureCore',
               'defaultApp', 'addAppToAppDictionary:'},
}


def unpack(fmt, data, offset=0):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ValueError('Truncated Mach-O field')
    return struct.unpack_from(fmt, data, offset)


def cstring(data, offset, end=None):
    end = len(data) if end is None else end
    if not 0 <= offset < end <= len(data):
        raise ValueError('String lies outside its table')
    stop = data.find(b'\0', offset, end)
    if stop < 0:
        raise ValueError('Unterminated Mach-O string')
    return data[offset:stop].decode('utf-8', errors='replace')


def select_slice(data, cpu_type=ARM64):
    """Choose a matching fat slice; offsets in the result remain slice-relative."""
    if data[:4] not in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
        return data, 0
    magic, count = unpack('>II', data)
    stride = 32 if magic == 0xCAFEBABF else 20
    if count > 64 or 8 + count * stride > len(data):
        raise ValueError('Invalid universal Mach-O table')
    matches = []
    for index in range(count):
        position = 8 + index * stride
        cpu, subtype = unpack('>II', data, position)
        offset, size = unpack('>QQ' if stride == 32 else '>II', data, position + 8)
        if offset + size > len(data) or offset < 8 + count * stride:
            raise ValueError('Invalid universal Mach-O slice bounds')
        if cpu == cpu_type:
            matches.append((subtype & 0xFFFFFF, offset, size))
    if not matches:
        raise ValueError('No requested CPU slice in universal Mach-O')
    _, offset, size = min(matches)
    return data[offset:offset + size], offset


class MachO:
    def __init__(self, data, cpu_type=ARM64):
        self.data, self.slice_offset = select_slice(data, cpu_type)
        magic, self.cpu_type = unpack('<II', self.data)
        if magic not in (0xFEEDFACE, 0xFEEDFACF):
            raise ValueError('Expected little-endian Mach-O')
        if self.cpu_type != cpu_type:
            raise ValueError('Mach-O CPU does not match the requested architecture')
        self.is64 = magic == 0xFEEDFACF
        self.pointer_size = 8 if self.is64 else 4
        header_size = 32 if self.is64 else 28
        command_count, command_bytes = unpack('<II', self.data, 16)
        end = header_size + command_bytes
        if end > len(self.data) or command_count > command_bytes // 8:
            raise ValueError('Invalid Mach-O load-command extent')
        self.loads, self.rpaths, self.segments, self.sections = [], [], [], []
        self.symtab = None
        self.uuid = None
        self.has_dyld_binding_info = False
        self.has_chained_fixups = False
        position = header_size
        for _ in range(command_count):
            command, size = unpack('<II', self.data, position)
            if size < 8 or position + size > end:
                raise ValueError('Invalid Mach-O load command')
            if command in LOAD_COMMANDS:
                if size < 24:
                    raise ValueError('Truncated dylib command')
                name_offset = unpack('<I', self.data, position + 8)[0]
                if not 24 <= name_offset < size:
                    raise ValueError('Invalid dylib name offset')
                self.loads.append({'ordinal': len(self.loads) + 1,
                                   'kind': LOAD_COMMANDS[command],
                                   'name': cstring(self.data, position + name_offset, position + size)})
            elif command == 0x8000001C:
                if size < 12:
                    raise ValueError('Truncated rpath command')
                name_offset = unpack('<I', self.data, position + 8)[0]
                if not 12 <= name_offset < size:
                    raise ValueError('Invalid rpath offset')
                self.rpaths.append(cstring(self.data, position + name_offset, position + size))
            elif command in (1, 0x19):
                self._segment(position, size, command == 0x19)
            elif command == 2:
                if size < 24:
                    raise ValueError('Truncated symbol-table command')
                self.symtab = unpack('<IIII', self.data, position + 8)
            elif command == 0x1B:
                if size < 24:
                    raise ValueError('Truncated UUID command')
                self.uuid = self.data[position + 8:position + 24].hex()
            elif command in (0x22, 0x80000022):
                self.has_dyld_binding_info = True
            elif command == 0x80000034:
                self.has_chained_fixups = True
            position += size
        if position != end:
            raise ValueError('Load-command count/size mismatch')

    def _segment(self, position, size, is64):
        header, stride = (72, 80) if is64 else (56, 68)
        if size < header:
            raise ValueError('Truncated segment command')
        vm, virtual_size, offset, file_size = unpack('<QQQQ' if is64 else '<IIII', self.data, position + 24)
        count = unpack('<I', self.data, position + (64 if is64 else 48))[0]
        if header + count * stride > size or offset + file_size > len(self.data):
            raise ValueError('Invalid segment/section bounds')
        self.segments.append((vm, virtual_size, offset, file_size))
        for index in range(count):
            at = position + header + index * stride
            name = self.data[at:at + 16].split(b'\0')[0].decode(errors='replace')
            address, length, file_offset = unpack('<QQI' if is64 else '<III', self.data, at + 32)
            flags = unpack('<I', self.data, at + (64 if is64 else 56))[0]
            self.sections.append({'name': name, 'address': address, 'size': length,
                                  'offset': file_offset, 'flags': flags})

    def vm_offset(self, address, size=1):
        for vm, _, offset, file_size in self.segments:
            if vm <= address and address + size <= vm + file_size:
                return offset + address - vm
        raise ValueError('Virtual address is not backed by file bytes')

    def vm_pointer(self, address):
        return unpack('<Q' if self.is64 else '<I', self.data,
                      self.vm_offset(address, self.pointer_size))[0]

    def vm_string(self, address):
        for vm, _, offset, file_size in self.segments:
            if vm <= address < vm + file_size:
                start = offset + address - vm
                return cstring(self.data, start, min(offset + file_size, start + 4096))
        raise ValueError('String address is not backed by file bytes')

    def undefined_symbols(self):
        if self.symtab is None:
            return []
        offset, count, strings, string_size = self.symtab
        stride = 16 if self.is64 else 12
        if offset + count * stride > len(self.data) or strings + string_size > len(self.data):
            raise ValueError('Truncated symbol/string table')
        result = []
        for index in range(count):
            name_index, kind, section, description, value = unpack(
                '<IBBHQ' if self.is64 else '<IBBHI', self.data, offset + index * stride)
            if kind & 0xE0 or kind & 0xE or not kind & 1 or section or value:
                continue
            ordinal = description >> 8
            name = cstring(self.data, strings + name_index, strings + string_size)
            dependency = self.loads[ordinal - 1]['name'] if 1 <= ordinal <= len(self.loads) else None
            result.append({'name': name, 'ordinal': ordinal, 'dependency': dependency,
                           'weak_reference': bool(description & 0x40)})
        return result

    def _methods(self, cls, owner, is_class_method):
        ro = self.vm_pointer(cls + 4 * self.pointer_size) & ~(7 if self.is64 else 3)
        pointer = self.vm_pointer(ro + (32 if self.is64 else 20))
        if not pointer:
            return []
        flags, count = unpack('<II', self.data, self.vm_offset(pointer, 8))
        stride = flags & 0xFFFC
        relative = bool(flags & 0x80000000)
        expected_stride = 12 if relative else self.pointer_size * 3
        if stride != expected_stride or count > 100000:
            raise ValueError('Unsupported Objective-C method-list layout')
        result = []
        for index in range(count):
            entry = pointer + 8 + index * stride
            if relative:
                name_offset, type_offset, implementation_offset = unpack(
                    '<iii', self.data, self.vm_offset(entry, stride))
                name = entry + name_offset
                if not flags & 0x40000000:
                    name = self.vm_pointer(name)
                types = entry + 4 + type_offset
                implementation = entry + 8 + implementation_offset
            else:
                name = self.vm_pointer(entry)
                types = self.vm_pointer(entry + self.pointer_size)
                implementation = self.vm_pointer(entry + self.pointer_size * 2)
            selector = self.vm_string(name)
            if selector in INITIALIZATION_METHODS.get(owner, set()):
                result.append({'class': owner, 'selector': selector,
                               'class_method': is_class_method,
                               'implementation': hex(implementation),
                               'type_encoding': self.vm_string(types)})
        return result

    def objc_metadata(self):
        found, methods, unreadable, unreadable_methods = {}, [], 0, 0
        for section in self.sections:
            if section['name'] not in ('__objc_classlist', '__objc_nlclslist'):
                continue
            if section['size'] % self.pointer_size:
                raise ValueError('Misaligned Objective-C class list')
            for index in range(section['size'] // self.pointer_size):
                try:
                    cls = self.vm_pointer(section['address'] + index * self.pointer_size)
                    data = self.vm_pointer(cls + 4 * self.pointer_size)
                    ro = data & ~(7 if self.is64 else 3)
                    name = self.vm_string(self.vm_pointer(ro + (24 if self.is64 else 16)))
                    if name in SDK_CLASSES:
                        found[name] = hex(cls)
                except ValueError:
                    # Chained/encoded class pointers are not decoded by this inventory.
                    unreadable += 1
                    continue
                if name in INITIALIZATION_METHODS:
                    for is_class_method in (False, True):
                        try:
                            target = self.vm_pointer(cls) if is_class_method else cls
                            methods.extend(self._methods(target, name, is_class_method))
                        except ValueError:
                            unreadable_methods += 1
        unique_methods = {tuple(sorted(method.items())): method for method in methods}
        return found, list(unique_methods.values()), unreadable, unreadable_methods

    def sdk_classes(self):
        found, _, unreadable, _ = self.objc_metadata()
        return found, unreadable

    def report(self):
        symbols = self.undefined_symbols()
        counts = Counter(symbol['ordinal'] for symbol in symbols)
        sdk_classes, methods, unreadable, unreadable_methods = self.objc_metadata()
        text_bytes = sum(section['size'] for section in self.sections if section['name'] == '__text')
        instruction_bytes = sum(section['size'] for section in self.sections
                                if section['flags'] & 0x80000400 or section['name'] in
                                ('__text', '__stubs', '__auth_stubs', '__objc_stubs'))
        return {'cpu_type': self.cpu_type, 'slice_offset': self.slice_offset,
                'uuid': self.uuid, 'text_bytes': text_bytes,
                'instruction_section_bytes': instruction_bytes,
                'rpaths': self.rpaths,
                'loads': [dict(load, undefined_symbol_count=counts[load['ordinal']]) for load in self.loads],
                'undefined_symbols': symbols, 'sdk_class_definitions': sdk_classes,
                'initialization_methods': methods,
                'unreadable_objc_class_entries': unreadable,
                'unreadable_objc_method_lists': unreadable_methods,
                'has_dyld_binding_info': self.has_dyld_binding_info,
                'has_chained_fixups': self.has_chained_fixups}


def expanded_path(name, loader, app):
    for token, base in (('@loader_path', posixpath.dirname(loader)), ('@executable_path', app)):
        if name == token or name.startswith(token + '/'):
            return posixpath.normpath(base + name[len(token):])
    return name


def resolve_load(name, loader, app, images, rpaths):
    candidates = []
    if name.startswith('@rpath/'):
        candidates = [posixpath.normpath(path + '/' + name[len('@rpath/'):]) for path in rpaths]
    else:
        candidates = [expanded_path(name, loader, app)]
    for path in candidates:
        if path in images:
            return path, 'packaged'
    if any(path.startswith(('/System/Library/', '/usr/lib/')) for path in candidates):
        return None, 'system'
    return None, 'unresolved'


def audit_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = {entry.filename: entry for entry in archive.infolist() if not entry.is_dir()}
        if len(entries) != sum(not entry.is_dir() for entry in archive.infolist()):
            raise ValueError('Duplicate file names in IPA')
        apps = [name for name in entries if name.startswith('Payload/') and
                name.endswith('.app/Info.plist') and name.count('/') == 2]
        if len(apps) != 1:
            raise ValueError('Expected one top-level Payload app')
        app = posixpath.dirname(apps[0])
        info = plistlib.loads(archive.read(apps[0]))
        main = app + '/' + info['CFBundleExecutable']
        candidates = {main}
        for name in entries:
            if not name.startswith(app + '/'):
                continue
            if name.endswith('.dylib'):
                candidates.add(name)
            elif name.endswith('/Info.plist'):
                metadata = plistlib.loads(archive.read(name))
                executable = metadata.get('CFBundleExecutable')
                if executable:
                    candidate = posixpath.dirname(name) + '/' + executable
                    if candidate in entries:
                        candidates.add(candidate)
        main_image = MachO(archive.read(main))
        images, skipped = {}, []
        for name in sorted(candidates):
            try:
                image = main_image if name == main else MachO(archive.read(name), main_image.cpu_type)
                images[name] = image.report()
            except ValueError as error:
                if name == main:
                    raise
                skipped.append({'path': name, 'reason': str(error)})
        main_paths = [expanded_path(name, main, app) for name in images[main]['rpaths']]
        edges = []
        for name, image in images.items():
            own_paths = [expanded_path(value, name, app) for value in image['rpaths']]
            paths = list(dict.fromkeys(own_paths + main_paths))
            for load in image['loads']:
                target, resolution = resolve_load(load['name'], name, app, images, paths)
                edges.append({'source': name, 'target': target, 'resolution': resolution,
                              'name': load['name'], 'kind': load['kind'], 'ordinal': load['ordinal']})
        reachable, queue = set(), deque([main])
        adjacency = {}
        for edge in edges:
            if edge['target']:
                adjacency.setdefault(edge['source'], []).append(edge['target'])
        while queue:
            name = queue.popleft()
            if name not in reachable:
                reachable.add(name)
                queue.extend(adjacency.get(name, []))
        frameworks = []
        roots = sorted({name.split('.framework/', 1)[0] + '.framework/' for name in entries
                        if name.startswith(app + '/Frameworks/') and '.framework/' in name})
        for root in roots:
            members = [entry for name, entry in entries.items() if name.startswith(root)]
            executable = root + PurePosixPath(root.rstrip('/')).stem
            image = images.get(executable)
            frameworks.append({'path': root.rstrip('/'), 'files': len(members),
                               'uncompressed_bytes': sum(entry.file_size for entry in members),
                               'zip_compressed_bytes': sum(entry.compress_size for entry in members),
                               'executable': executable,
                               'text_bytes': image['text_bytes'] if image else None,
                               'instruction_section_bytes': image['instruction_section_bytes'] if image else None,
                               'reachable_from_main': executable in reachable})
        owners = {name: [path for path, image in images.items() if name in image['sdk_class_definitions']]
                  for name in SDK_CLASSES}
        empty = [framework for framework in frameworks if framework['text_bytes'] == 0]
        summary = {'frameworks': len(frameworks),
                   'framework_uncompressed_bytes': sum(framework['uncompressed_bytes'] for framework in frameworks),
                   'framework_zip_compressed_bytes': sum(framework['zip_compressed_bytes'] for framework in frameworks),
                   'zero_text_frameworks': len(empty),
                   'zero_text_uncompressed_bytes': sum(framework['uncompressed_bytes'] for framework in empty),
                   'zero_text_zip_compressed_bytes': sum(framework['zip_compressed_bytes'] for framework in empty),
                   'packaged_images': len(images), 'statically_reachable_images': len(reachable)}
    with open(path, 'rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'schema_version': 1, 'input_sha256': checksum, 'main_executable': main,
            'app_runtime_configuration': {'CloudcellEnvironment': info.get('CloudcellEnvironment')},
            'summary': summary, 'sdk_class_owners': owners, 'frameworks': frameworks,
            'images': images, 'edges': edges, 'skipped_images': skipped,
            'limitations': [
                'Static candidates only: code-empty or unreachable does not mean safe to delete.',
                'Imports are LC_SYMTAB undefined-symbol ordinals; bind streams/chained imports are not decoded.',
                'Resolution uses each image and main executable rpaths, not a complete context-sensitive dyld run-path stack.',
                'Dynamic dlopen/NSBundle lookup, +load/constructors, callbacks and device execution are not evaluated.',
                'Class ownership covers selected exact SDK class names; encoded class pointers may be unreadable.',
                'Sizes count current framework ZIP entries, not SDK code embedded in the main executable.',
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', type=Path, help='Optional JSON report; defaults to stdout')
    args = parser.parse_args()
    report = json.dumps(audit_archive(args.ipa), indent=2) + '\n'
    if args.output:
        if args.output.resolve() == args.ipa.resolve():
            parser.error('Report must not overwrite the input IPA')
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(report)
    else:
        print(report, end='')


if __name__ == '__main__':
    main()

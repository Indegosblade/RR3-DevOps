"""Host ports for the actual repair C core; synthetic saves, real temporary files.

Foundation and the inherited minizip/selector APIs are explicit test ports.
No original game bytes, device, profile or signing identity is required.
"""
import ctypes as C
import os
from pathlib import Path
import shutil
import zipfile
import zlib

UP, PTR, INT, BOOL = C.c_size_t, C.c_void_p, C.c_int, C.c_ubyte


class Harness:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.docs, self.tmp = self.root / 'Documents', self.root / 'tmp'
        self.docs.mkdir()
        self.tmp.mkdir()
        self.callbacks, self.objects, self.handles = [], [], {}
        self.events = []
        self.corrupt_extraction = False
        self.fail_backup = False
        self.fail_commit_at = None
        self.fail_rollback = False
        self.missing_symbol = False
        self.commits = 0
        self.api = (UP * 28)()
        self.crt = C.CDLL('ucrtbase' if os.name == 'nt' else None)
        for index, name in ((1, 'malloc'), (2, 'free'), (3, 'fopen'), (4, 'fread'), (5, 'fclose')):
            self.api[index] = C.cast(getattr(self.crt, name), PTR).value
        self.bind(0, PTR, [], lambda: self.string(str(self.tmp)))
        self.bind(6, UP, [UP, PTR, C.c_uint], lambda crc, data, size: zlib.crc32(C.string_at(data, size), crc))
        self.rename = self.callback(INT, [UP, UP], self.rename_file)
        self.exit = self.callback(INT, [UP, UP], lambda status, _: self.events.append(('exit', status)) or 0)
        self.bind(7, PTR, [PTR, C.c_char_p], lambda _, name: 0 if self.missing_symbol else C.cast(self.rename if name == b'rename' else self.exit, PTR).value)
        self.bind(8, PTR, [C.c_char_p], self.zip_open)
        self.bind(9, INT, [PTR], self.zip_first)
        self.bind(10, INT, [PTR, PTR, PTR, UP, PTR, UP, PTR, UP], self.zip_info)
        self.bind(11, INT, [PTR], self.zip_member_open)
        self.bind(12, INT, [PTR, PTR, C.c_uint], self.zip_read)
        self.bind(13, INT, [PTR], self.zip_member_close)
        self.bind(14, INT, [PTR], self.zip_next)
        self.bind(15, INT, [PTR], self.zip_close)
        self.bind(16, PTR, [PTR, PTR], lambda obj, _: obj)
        self.bind(17, PTR, [PTR, PTR, C.c_char_p], lambda cls, sel, text: self.string(text.decode()))
        self.bind(18, PTR, [PTR, PTR, PTR], lambda parent, sel, name: self.string(str(self.path(parent) / self.text(name))))
        self.bind(19, PTR, [PTR, PTR], lambda cls, sel: 0x3333)
        self.bind(20, BOOL, [PTR, PTR, PTR], lambda fm, sel, path: self.path(path).exists())
        self.bind(21, BOOL, [PTR, PTR, PTR, BOOL, PTR, PTR], self.mkdir)
        self.bind(22, BOOL, [PTR, PTR, PTR, PTR, PTR], self.copy)
        self.bind(23, BOOL, [PTR, PTR, PTR, PTR], self.remove)
        self.bind(24, BOOL, [PTR, PTR, PTR, PTR, PTR], self.extract)
        self.classes = [PTR(0x1111), PTR(0x2222)]
        self.api[25], self.api[26] = [C.addressof(x) for x in self.classes]
        self.api[27] = 0

    def callback(self, result, arguments, fn):
        value = C.CFUNCTYPE(result, *arguments)(fn)
        self.callbacks.append(value)
        return value

    def bind(self, index, result, arguments, fn):
        self.api[index] = C.cast(self.callback(result, arguments, fn), PTR).value

    def string(self, text):
        value = C.create_string_buffer(text.encode('utf-8'))
        self.objects.append(value)
        return C.addressof(value)

    def text(self, obj):
        return C.string_at(obj).decode('utf-8')

    def path(self, obj):
        result = Path(self.text(obj)).resolve()
        if not result.is_relative_to(self.root):
            raise AssertionError('Test port escaped its temporary workspace')
        return result

    def mkdir(self, fm, sel, path, intermediates, attributes, error):
        try:
            self.path(path).mkdir(parents=bool(intermediates), exist_ok=True)
            return True
        except OSError:
            return False

    def copy(self, fm, sel, source, target, error):
        if self.fail_backup:
            return False
        try:
            shutil.copy2(self.path(source), self.path(target))
            return True
        except OSError:
            return False

    def remove(self, fm, sel, path, error):
        try:
            p = self.path(path)
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return True
        except OSError:
            return False

    def rename_file(self, source, target):
        source, target = self.path(source), self.path(target)
        rollback = source.parent.name == '.backup'
        if rollback and self.fail_rollback:
            return -1
        if not rollback:
            self.commits += 1
            if self.commits == self.fail_commit_at:
                return -1
        try:
            os.replace(source, target)
            self.events.append(('rollback' if rollback else 'commit', target.name))
            return 0
        except OSError:
            return -1

    def zip_open(self, path):
        try:
            archive = zipfile.ZipFile(path.decode())
        except (OSError, zipfile.BadZipFile):
            return 0
        handle = 0x5000 + len(self.handles)
        self.handles[handle] = {'zip': archive, 'entries': archive.infolist(), 'index': 0, 'error': 0}
        return handle

    def zip_first(self, handle):
        return 0 if self.handles[handle]['entries'] else -100

    def zip_info(self, handle, info, name, size, extra, extra_size, comment, comment_size):
        item = self.handles[handle]
        data = item['entries'][item['index']].filename.encode() + b'\0'
        C.memmove(name, data, min(size, len(data)))
        return 0

    def zip_member_open(self, handle):
        item = self.handles[handle]
        entry = item['entries'][item['index']]
        if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            return -1
        try:
            item['stream'] = item['zip'].open(entry)
            item['error'] = 0
            return 0
        except (RuntimeError, zipfile.BadZipFile):
            return -1

    def zip_read(self, handle, buffer, size):
        item = self.handles[handle]
        try:
            data = item['stream'].read(size)
        except (RuntimeError, zipfile.BadZipFile):
            item['error'] = -1
            return -1
        C.memmove(buffer, data, len(data))
        return len(data)

    def zip_member_close(self, handle):
        item = self.handles[handle]
        item['stream'].close()
        return item['error']

    def zip_next(self, handle):
        item = self.handles[handle]
        item['index'] += 1
        return 0 if item['index'] < len(item['entries']) else -100

    def zip_close(self, handle):
        self.handles[handle]['zip'].close()
        return 0

    def extract(self, plugin, sel, source, destination, progress):
        try:
            with zipfile.ZipFile(self.path(source)) as archive:
                for entry in archive.infolist():
                    if entry.filename.startswith('__MACOSX/') or entry.filename == '.DS_Store':
                        continue
                    target = self.path(destination) / entry.filename
                    data = archive.read(entry)
                    if self.corrupt_extraction and entry.filename == 'character.2.dat':
                        data = data[:-1]
                    target.write_bytes(data)
            return True  # Original extractor can report success despite bad output.
        except (OSError, RuntimeError, zipfile.BadZipFile):
            return False

    def archive(self, entries, *, compression=zipfile.ZIP_DEFLATED):
        source = self.root / 'input.zip'
        with zipfile.ZipFile(source, 'w', compression) as archive:
            for name, data in entries:
                archive.writestr(name, data)
        return source

    def apply(self, library, source, *, cleanup_source=False):
        block = (PTR * 9)()
        block[4], block[5], block[6] = 0x4444, self.string(str(source)), self.string(str(self.docs))
        if cleanup_source:
            C.cast(block, C.POINTER(C.c_ubyte))[0x41] = 1
        call = library.rr3_apply_save
        call.argtypes, call.restype = [PTR, C.POINTER(UP), UP], INT
        return call(block, self.api, 0)

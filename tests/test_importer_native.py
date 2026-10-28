import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
import zipfile

from importer_native_harness import Harness

ROOT = Path(__file__).resolve().parents[1]


def cleanup_temporary(temporary):
    parent = (ROOT / 'investigation').resolve()
    target = Path(temporary.name).resolve()
    if not target.is_relative_to(parent) or target == parent:
        raise ValueError('Temporary test cleanup escaped its workspace')
    temporary.cleanup()


class NativeImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('RR3_NATIVE_TEST_LIBRARY')
        if path:
            cls.library = ctypes.CDLL(str(Path(path).resolve()))
            return
        compiler = shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
        if compiler is None or os.name == 'nt':
            raise unittest.SkipTest('Host C compiler unavailable; set RR3_NATIVE_TEST_LIBRARY to run C integration checks')
        (ROOT / 'investigation').mkdir(exist_ok=True)
        cls.build = tempfile.TemporaryDirectory(prefix='rr3-native-test-', dir=ROOT / 'investigation')
        cls.addClassCleanup(cleanup_temporary, cls.build)
        output = Path(cls.build.name) / 'native.so'
        subprocess.run([compiler, '-std=c11', '-DRR3_TESTING', '-fPIC', '-shared', '-O1',
                        str(ROOT / 'importer_fix/native.c'), '-o', str(output)], check=True)
        cls.library = ctypes.CDLL(str(output))

    def setUp(self):
        (ROOT / 'investigation').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='rr3-import-test-', dir=ROOT / 'investigation')
        self.addCleanup(cleanup_temporary, self.temporary)
        self.h = Harness(self.temporary.name)
        self.original = {'character.2.dat': b'original-current-profile', 'prefs.dat': b'old preferences'}
        for name, data in self.original.items():
            (self.h.docs / name).write_bytes(data)

    def contents(self):
        return {p.name: p.read_bytes() for p in self.h.docs.iterdir() if p.is_file()}

    def unchanged_failure(self, source):
        self.assertEqual(self.h.apply(self.library, source), 0)
        self.assertEqual(self.contents(), self.original)
        self.assertNotIn(('exit', 0), self.h.events)
        self.assertEqual(list(self.h.tmp.iterdir()), [])

    def test_complete_import_terminates_only_after_verified_atomic_commits(self):
        incoming = {'character.2.dat': b'C' * 4569856, 'prefs.dat': b'new preferences', 'extra.dat': b'new file'}
        source = self.h.archive(list(incoming.items()))
        self.assertEqual(self.h.apply(self.library, source), 1)
        self.assertEqual(self.contents(), incoming)
        self.assertEqual(self.h.events[-1], ('exit', 0))
        self.assertEqual(list(self.h.tmp.iterdir()), [])
        self.assertTrue(source.exists())

    def test_owned_cloud_download_cleanup_flag_is_preserved(self):
        source = self.h.archive([('character.2.dat', b'valid synthetic profile')])
        self.assertEqual(self.h.apply(self.library, source, cleanup_source=True), 1)
        self.assertFalse(source.exists())

    def test_bad_archive_and_missing_required_character_leave_live_files_untouched(self):
        source = self.h.root / 'bad.zip'
        source.write_bytes(b'not a ZIP')
        self.unchanged_failure(source)
        self.unchanged_failure(self.h.archive([('prefs.dat', b'new')]))
        self.unchanged_failure(self.h.archive([('Character.2.dat', b'wrong case')]))

    def test_nested_paths_non_save_members_and_case_collisions_are_rejected(self):
        variants = [('../character.2.dat', b'x'), ('Documents/character.2.dat', b'x'),
                    ('assets.bin', b'x'), ('Character.2.dat', b'collision')]
        for entry in variants:
            with self.subTest(entry=entry[0]), warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                self.unchanged_failure(self.h.archive([('character.2.dat', b'profile'), entry]))

    def test_empty_character_and_unsupported_compression_do_not_close_the_game(self):
        self.unchanged_failure(self.h.archive([('character.2.dat', b'')]))
        self.unchanged_failure(self.h.archive([('character.2.dat', b'profile')], compression=zipfile.ZIP_BZIP2))

    def test_false_positive_upstream_extraction_is_detected_before_commit(self):
        self.h.corrupt_extraction = True
        self.unchanged_failure(self.h.archive([('character.2.dat', b'C' * 10000)]))

    def test_backup_failure_prevents_any_live_replacement(self):
        self.h.fail_backup = True
        self.unchanged_failure(self.h.archive([('character.2.dat', b'new profile')]))

    def test_mid_commit_failure_rolls_back_existing_and_new_files(self):
        for entries in ([('character.2.dat', b'new'), ('prefs.dat', b'new')],
                        [('extra.dat', b'new'), ('character.2.dat', b'new')]):
            with self.subTest(entries=entries):
                self.h.commits = 0
                self.h.fail_commit_at = 2
                self.unchanged_failure(self.h.archive(entries))

    def test_rollback_failure_preserves_recovery_copies_and_does_not_exit(self):
        self.h.fail_commit_at = 2
        self.h.fail_rollback = True
        source = self.h.archive([('character.2.dat', b'new'), ('prefs.dat', b'new')])
        self.assertEqual(self.h.apply(self.library, source), 0)
        self.assertNotIn(('exit', 0), self.h.events)
        backup = next(self.h.tmp.glob('rr3-save-stage-*/.backup/character.2.dat'))
        self.assertEqual(backup.read_bytes(), self.original['character.2.dat'])

    def test_missing_required_runtime_symbol_prevents_even_staging(self):
        self.h.missing_symbol = True
        self.unchanged_failure(self.h.archive([('character.2.dat', b'new')]))

    def test_bad_crc_fails_before_any_live_replacement(self):
        source = self.h.archive([('character.2.dat', b'C' * 10000)])
        data = bytearray(source.read_bytes())
        central = data.index(b'PK\x01\x02')
        data[central + 16] ^= 1
        source.write_bytes(data)
        self.unchanged_failure(source)

    def test_archive_entry_limit_is_checked_before_staging(self):
        entries = [('character.2.dat', b'C')]+[(f'item{i}.dat', b'x') for i in range(64)]
        self.unchanged_failure(self.h.archive(entries))

    def test_archive_metadata_is_ignored_without_becoming_live_save_data(self):
        entries = [('character.2.dat', b'new'), ('.DS_Store', b'metadata'), ('__MACOSX/._character.2.dat', b'metadata')]
        self.assertEqual(self.h.apply(self.library, self.h.archive(entries)), 1)
        self.assertEqual(self.contents(), {**self.original, 'character.2.dat': b'new'})

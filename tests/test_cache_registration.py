import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.trace_cache_registration import (CACHE_MAGIC, CACHE_VERSION, GROUP,
    GROUP_PREFIX, LEDGER, audit, classify_catalog, parse_catalog, parse_ledger)


class CacheRegistrationTests(unittest.TestCase):
    def ledger(self, lines=(), token='7469'):
        return (struct.pack('<II', CACHE_MAGIC, CACHE_VERSION)
                + (token + '\n' + ''.join(lines)).encode())

    def test_revision_token_is_independent_of_record_count(self):
        data = self.ledger(['/synthetic/a\t' + '1' * 32 + '\n',
                            '/synthetic/b\t' + '2' * 32 + '\n'])
        result = parse_ledger(data)
        self.assertEqual(result['client_revision_token'], '7469')
        self.assertEqual(result['entry_count'], 2)
        self.assertEqual(result['records']['synthetic/a'], '1' * 32)

    def test_out_of_order_unique_receipts_preserve_the_same_key_hash_map(self):
        a, z = '/synthetic/a\t' + '1' * 32 + '\n', '/synthetic/z\t' + '2' * 32 + '\n'
        self.assertEqual(parse_ledger(self.ledger([z, a]))['records'],
                         parse_ledger(self.ledger([a, z]))['records'])

    def test_header_and_text_corruption_are_rejected(self):
        for data in [b'short', struct.pack('<II', 0, CACHE_VERSION) + b'7469\n',
                     struct.pack('<II', CACHE_MAGIC, 5) + b'7469\n',
                     self.ledger(token='not-numeric'), self.ledger(['/synthetic/a\tbad\n']),
                     self.ledger(['/synthetic/a\t' + '1' * 32 + '\textra\n'])]:
            with self.subTest(data=data[:16]), self.assertRaises(ValueError):
                parse_ledger(data)

    def test_duplicate_and_unsafe_paths_are_not_reinterpreted(self):
        row = '/synthetic/a\t' + '1' * 32 + '\n'
        for rows in [[row, row], ['/../outside\t' + '1' * 32 + '\n'],
                     ['//ambiguous/root\t' + '1' * 32 + '\n'],
                     ['/synthetic\\outside\t' + '1' * 32 + '\n'],
                     ['/synthetic/C:outside\t' + '1' * 32 + '\n']]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_ledger(self.ledger(rows))

    def test_payload_presence_does_not_supply_a_receipt_or_change_catalog(self):
        catalog = parse_catalog(b'/synthetic/atlas.ios.atlas ' + b'1' * 32 + b' 20 40\n')
        result = classify_catalog(catalog, {}, {'synthetic/atlas.ios.atlas'})
        self.assertEqual(result['stored_files_present'], 1)
        self.assertEqual(result['receipt_status_counts'], {'receipt_missing': 1})
        self.assertEqual(catalog['synthetic/atlas.ios.atlas']['transport_bytes'], 20)

    def test_stored_hash_is_not_accepted_as_transport_receipt_identity(self):
        from scripts.trace_asset_transport import atlas_transport
        stored = b'<synthetic>original fixture</synthetic>\n' * 20
        transport = atlas_transport(stored)
        stored_md5, transport_md5 = hashlib.md5(stored).hexdigest(), hashlib.md5(transport).hexdigest()
        self.assertNotEqual(stored_md5, transport_md5)
        path = 'synthetic/atlas.ios.atlas'
        catalog = {path: dict(md5=transport_md5, transport_bytes=len(transport), stored_bytes=len(stored))}
        wrong = classify_catalog(catalog, {path: stored_md5}, {path})
        right = classify_catalog(catalog, {path: transport_md5}, {path})
        self.assertEqual(wrong['receipt_status_counts'], {'receipt_differs_from_catalog': 1})
        self.assertEqual(right['receipt_status_counts'], {'receipt_matches_catalog': 1})

    @patch('scripts.trace_cache_registration.trace_binary', return_value={'synthetic': True})
    def test_payload_only_candidate_audit_retains_the_receipt_gap_without_writing_inputs(self, _trace):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ipa, cache = root / 'original.ipa', root / 'candidate.zip'
            path = GROUP_PREFIX + 'sprites.ios.atlas'
            md5 = '1' * 32
            with zipfile.ZipFile(ipa, 'w') as archive:
                archive.writestr('Payload/RealRacing3.app/RealRacing3', b'synthetic executable')
                archive.writestr('Payload/RealRacing3.app/res/' + GROUP, f'/{path} {md5} 20 40\n')
            with zipfile.ZipFile(cache, 'w') as archive:
                archive.writestr(LEDGER, self.ledger(['/SpeedRush_TV_commercial.mp4\t' + '2' * 32 + '\n']))
                archive.writestr('Caches/' + path, b'synthetic atlas payload')
            before = {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in [ipa, cache]}
            report = audit(ipa, cache)
            self.assertEqual(report['hd_hybrid_highway_subset']['stored_files_present'], 1)
            self.assertEqual(report['hd_hybrid_highway_subset']['receipt_status_counts'], {'receipt_missing': 1})
            self.assertTrue(report['speedrush_comparison']['receipt_present'])
            self.assertFalse(report['speedrush_comparison']['stored_file_present'])
            self.assertEqual(report['ledger']['entry_count'], 1)
            self.assertEqual(report['ledger_archive_members'], [LEDGER])
            self.assertFalse(report['cache_modified'])
            self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in [ipa, cache]})

    def test_conflicting_catalog_records_are_rejected(self):
        row = b'/synthetic/atlas.ios.atlas ' + b'1' * 32 + b' 20 40\n'
        with self.assertRaises(ValueError):
            parse_catalog(row + row.replace(b'1' * 32, b'2' * 32))


if __name__ == '__main__':
    unittest.main()

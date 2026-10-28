"""Synthetic atlas bytes only; no original game XML or media."""
import hashlib
import unittest

from scripts.recover_companion_atlases import descriptor_variants, prove_companion
from scripts.trace_asset_transport import atlas_transport


def expected(stored):
    transport = atlas_transport(stored)
    return {'stored_bytes': len(stored), 'transport_bytes': len(transport),
            'md5': hashlib.md5(transport).hexdigest()}


class CompanionAtlases(unittest.TestCase):
    def setUp(self):
        self.ios = (b'<atlas_images texture_formats=".ptc.pvr" hash="synthetic">\n'
                    b'  <image name="test.png" width="5" height="7"/>\n</atlas_images>\n')

    def test_unchanged_exact_representation(self):
        stored, proof = prove_companion(self.ios, expected(self.ios))
        self.assertEqual(stored, self.ios)
        self.assertFalse(proof['stored_bytes_edited'])
        self.assertEqual(proof['stored_transform'], 'unchanged')

    def test_known_list_and_single_descriptors(self):
        for descriptor in (b'.ptc.pvr .atc.dds .dxt.dds .etc.dds',
                           b'.atc.dds', b'.etc.dds', b'.etc.pvr'):
            with self.subTest(descriptor=descriptor):
                source = self.ios.replace(b'.ptc.pvr', descriptor)
                stored, proof = prove_companion(source, expected(self.ios))
                self.assertEqual(stored, self.ios)
                self.assertTrue(proof['stored_bytes_edited'])
                self.assertEqual(proof['source_stored_sha256'], hashlib.sha256(source).hexdigest())
                self.assertEqual(proof['stored_sha256'], hashlib.sha256(self.ios).hexdigest())

    def test_reject_wrong_content_even_with_known_descriptor(self):
        for wrong in (self.ios.replace(b'width="5"', b'width="6"'),
                      self.ios.replace(b'synthetic', b'otherhash'),
                      self.ios.replace(b'test.png', b'nope.png')):
            with self.subTest(wrong=wrong):
                source = wrong.replace(b'.ptc.pvr', b'.atc.dds')
                with self.assertRaises(ValueError):
                    prove_companion(source, expected(self.ios))

    def test_reject_unknown_or_reordered_descriptors(self):
        for descriptor in (b'.astc.ktx', b'.atc.dds .ptc.pvr',
                           b'.ptc.pvr .etc.dds .dxt.dds .atc.dds'):
            with self.subTest(descriptor=descriptor):
                with self.assertRaises(ValueError):
                    prove_companion(self.ios.replace(b'.ptc.pvr', descriptor), expected(self.ios))

    def test_does_not_replace_an_unrelated_attribute_value(self):
        source = self.ios.replace(b'hash="synthetic"', b'hash=".atc.dds"')
        self.assertEqual(list(descriptor_variants(source)), [('unchanged', source)])

    def test_duplicate_descriptor_fields_are_not_edited(self):
        source = self.ios.replace(b'.ptc.pvr', b'.atc.dds').replace(
            b'hash="synthetic"', b'texture_formats=".atc.dds"')
        self.assertEqual(list(descriptor_variants(source)), [('unchanged', source)])

    def test_each_manifest_measurement_is_required(self):
        for field, value in (('stored_bytes', len(self.ios) + 1),
                             ('transport_bytes', len(atlas_transport(self.ios)) + 1),
                             ('md5', '0' * 32)):
            with self.subTest(field=field):
                record = expected(self.ios)
                record[field] = value
                with self.assertRaises(ValueError):
                    prove_companion(self.ios, record)

    def test_preserves_all_other_bytes_and_line_endings(self):
        ios = self.ios.replace(b'\n', b'\r\n') + b'\r\n'
        source = ios.replace(b'.ptc.pvr', b'.atc.dds')
        stored, _ = prove_companion(source, expected(ios))
        self.assertEqual(stored, ios)
        with self.assertRaises(ValueError):
            prove_companion(source, expected(self.ios))


if __name__ == '__main__':
    unittest.main()

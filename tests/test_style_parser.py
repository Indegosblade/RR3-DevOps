"""Style comparison guards and original-code probes using local user inputs.

No game binary or resource fixtures are redistributed. Engine integration tests
skip if the user's preserved original IPA or optional Unicorn is unavailable.
"""
import unittest
import zipfile

from scripts.trace_style_parser import (EngineProbe, audit, compare_colours,
                                        validate_binary, ROOT)
from build_4k_v3 import BINARY_PATH


class StyleComparisonTests(unittest.TestCase):
    def test_compares_every_local_colour_not_only_final_element(self):
        local = b'<Styles><Colours><Colour name="first" r="1" g="2" b="3"/><Colour name="last" r="9" g="9" b="9"/></Colours></Styles>'
        global_xml = b'<Styles><Colours><Colour name="first" r="7" g="7" b="7"/><Colour name="last" r="9" g="9" b="9"/></Colours></Styles>'
        values = compare_colours(local, global_xml)
        self.assertEqual([item['differs_from_global'] for item in values], [True, False])
        self.assertEqual(values[0]['local_rgba'], [1, 2, 3, 255])

    def test_missing_global_entry_is_explicit(self):
        values = compare_colours(b'<Styles><Colour name="new" r="1" g="2" b="3"/></Styles>', b'<Styles/>')
        self.assertIsNone(values[0]['global_rgba'])
        self.assertTrue(values[0]['differs_from_global'])

    def test_changed_or_truncated_code_is_refused_before_emulation(self):
        for binary in (b'', b'not the original game', b'\xcf\xfa\xed\xfe'):
            with self.assertRaisesRegex(ValueError, 'original executable SHA-256'):
                validate_binary(binary)


ORIGINAL_IPA = ROOT / '959112d6ace07153840144be3201b00f39ec0e91.ipa'


@unittest.skipUnless(ORIGINAL_IPA.is_file(), 'Preserved user-supplied original IPA unavailable')
class LocalEngineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import unicorn
        except ImportError:
            raise unittest.SkipTest('Optional Unicorn unavailable')
        with zipfile.ZipFile(ORIGINAL_IPA) as archive:
            cls.binary = archive.read(BINARY_PATH)

    def test_synthetic_xml_actual_engine_acceptance_and_error_status(self):
        valid = b'<Styles><Colours><Colour name="test" r="221" g="221" b="221"/></Colours></Styles>'
        invalid = valid.replace(b'/></Colours>', b'\r\n</Colours>')
        good = EngineProbe(self.binary).parse(valid)
        bad = EngineProbe(self.binary).parse(invalid)
        self.assertEqual(good['status'], 0)
        self.assertTrue(good['accepted'])
        self.assertEqual(bad['status'], 11)
        self.assertFalse(bad['accepted'])
        self.assertEqual(bad['description'], 'Error parsing start element tag')

    def test_real_encrypted_resource_parser_loader_and_consumer_boundary(self):
        report = audit(ORIGINAL_IPA, emulate=True)
        self.assertEqual(report['colour_count'], 12)
        self.assertEqual(report['colours_different_from_global'], 7)
        old, new = (report['execution'][key] for key in ('original', 'repaired'))
        self.assertEqual((old['parser']['status'], old['parser']['offset']), (11, 1052))
        self.assertEqual(new['parser']['status'], 0)
        self.assertFalse(old['loader_and_consumer']['loader_accepted'])
        self.assertFalse(old['loader_and_consumer']['local_style_ingestion_called'])
        self.assertIn('xml_load_error_logged', old['loader_and_consumer']['events'])
        self.assertTrue(new['loader_and_consumer']['loader_accepted'])
        self.assertTrue(new['loader_and_consumer']['local_style_ingestion_called'])
        self.assertNotIn('xml_load_error_logged', new['loader_and_consumer']['events'])


if __name__ == '__main__':
    unittest.main()

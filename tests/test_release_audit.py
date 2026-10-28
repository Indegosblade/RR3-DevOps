from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.audit_release import PRIVATE_KEY_BLOCK, audit_archive


class PrivacyAuditTests(unittest.TestCase):
    def test_crypto_parser_label_is_not_a_key(self):
        self.assertIsNone(PRIVATE_KEY_BLOCK.search(b'-----BEGIN PRIVATE KEY-----\0PEM parser label\0'))

    def test_complete_armored_key_is_rejected(self):
        fixture = b'-----BEGIN PRIVATE KEY-----\n' + b'A' * 64 + b'\n' + b'B' * 64 + b'\n-----END PRIVATE KEY-----'
        self.assertIsNotNone(PRIVATE_KEY_BLOCK.search(fixture))

    def test_provisioning_and_device_reports_are_rejected(self):
        for name in ('embedded.mobileprovision', 'device.ips', 'signing.p12', 'Nimble.log'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'fixture.ipa'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('Payload/RealRacing3.app/' + name, b'fixture')
                with self.assertRaisesRegex(ValueError, 'Private/runtime file'):
                    audit_archive(path)


if __name__ == '__main__':
    unittest.main()

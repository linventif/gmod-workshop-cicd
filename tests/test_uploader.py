import base64
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from otp import generate_one_time_code
from workshop import published_id, vdf_quote, write_addon, write_manifest


class SteamGuardTests(unittest.TestCase):
    def test_known_hmac_counter(self):
        # RFC 4226 test secret/counter 1 has truncated HMAC value 1094287082.
        # Steam encodes that value in its own alphabet instead of six digits.
        secret = base64.b64encode(b"12345678901234567890").decode()
        value = 1094287082
        alphabet = "23456789BCDFGHJKMNPQRTVWXY"
        expected = ""
        for _ in range(5):
            value, index = divmod(value, len(alphabet))
            expected += alphabet[index]
        self.assertEqual(generate_one_time_code(secret, 59), expected)
        self.assertEqual(generate_one_time_code(secret, 30), expected)
        self.assertNotEqual(generate_one_time_code(secret, 60), expected)

    def test_rejects_invalid_secret(self):
        for secret in ("", "not base64!", "YQ=="):
            with self.subTest(secret=secret), self.assertRaises(ValueError):
                generate_one_time_code(secret, 59)


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "metadata"
        self.manifest = Path(self.temp.name) / "workshop.vdf"
        self.env = patch.dict(os.environ, {
            "TITLE": 'Un "addon" français \\ test',
            "DESCRIPTION": 'Ligne 1\nLigne "2"\tfin\\',
            "PUBLISHED_FILE_ID": "12345",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def manifest_values(self):
        tokens = re.findall(r'"(?:[^"\\]|\\.)*"', self.path.read_text())
        decoded = [json.loads(token) for token in tokens]
        self.assertEqual(decoded.pop(0), "workshopitem")
        return dict(zip(decoded[::2], decoded[1::2]))

    def test_manifest_roundtrips_special_characters(self):
        write_manifest(self.temp.name, self.path)
        values = self.manifest_values()
        self.assertEqual(values["title"], os.environ["TITLE"])
        self.assertEqual(values["description"], os.environ["DESCRIPTION"])
        self.assertEqual(values["contentfolder"], self.temp.name)
        self.assertNotIn("previewfile", values)
        self.assertEqual(values["visibility"], "0")
        self.assertEqual(values["changenote"], "")

    def test_preview_is_only_included_when_supplied(self):
        os.environ["PREVIEW_FILE"] = str(Path(self.temp.name) / 'a "preview".png')
        write_manifest(self.temp.name, self.path)
        self.assertEqual(self.manifest_values()["previewfile"], os.environ["PREVIEW_FILE"])

    def test_addon_is_valid_json_with_special_title(self):
        write_addon(self.path)
        self.assertEqual(json.loads(self.path.read_text())["title"], os.environ["TITLE"])

    def test_rejects_unsupported_control_characters(self):
        with self.assertRaises(ValueError):
            vdf_quote("broken\x01value")

    def test_success_returns_confirmed_id(self):
        self.path.write_text("Uploading content...\nSuccess.\n")
        write_manifest(self.temp.name, self.manifest)
        self.assertEqual(published_id(self.path, self.manifest), "12345")

    def test_missing_confirmation_and_wrong_id_fail(self):
        for output, item_id in (
            ("ERROR! Failed to update workshop item", "12345"),
            ("Success. Created new item, PublishedFileId 12345\nERROR! Failed to update workshop item", "12345"),
            ("Success.\n", "42"),
            ("Success.\n", "0"),
        ):
            with self.subTest(output=output, item_id=item_id):
                self.path.write_text(output)
                self.manifest.write_text(f'"publishedfileid" "{item_id}"\n')
                with self.assertRaises(ValueError):
                    published_id(self.path, self.manifest)

    def test_creation_accepts_new_id(self):
        os.environ["PUBLISHED_FILE_ID"] = "0"
        self.path.write_text("Success.\n")
        self.manifest.write_text('"publishedfileid" "12345"\n')
        self.assertEqual(published_id(self.path, self.manifest), "12345")


if __name__ == "__main__":
    unittest.main()

import base64
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import Mock, patch

from otp import generate_fresh_code, generate_one_time_code, steam_clock
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

    def test_steam_clock_queries_without_credentials(self):
        response = Mock()
        response.read.return_value = b'{"response":{"server_time":"1000"}}'
        opened = Mock()
        opened.__enter__ = Mock(return_value=response)
        opened.__exit__ = Mock(return_value=False)
        with patch("otp.urlopen", return_value=opened) as request, \
                patch("otp.time.monotonic", side_effect=[10, 12]), \
                patch("otp.time.time", return_value=900):
            self.assertEqual(steam_clock(), (1001, 12, 99))
        call = request.call_args
        self.assertEqual(call.kwargs["timeout"], 5)
        self.assertEqual(call.args[0].get_method(), "POST")
        self.assertEqual(call.args[0].data, b"")

    def test_steam_clock_fails_clearly_if_query_is_unavailable(self):
        with patch("otp.urlopen", side_effect=OSError("offline")), \
                self.assertRaisesRegex(ValueError, "Unable to query Steam time"):
            steam_clock()

    def test_fresh_code_uses_server_time_despite_local_clock_drift(self):
        secret = base64.b64encode(b"12345678901234567890").decode()
        diagnostics = io.StringIO()
        with patch("otp.steam_clock", return_value=(120, 10, -3600)), \
                patch("otp.time.monotonic", return_value=10), \
                patch("otp.time.time", side_effect=AssertionError("Local clock must not be used")), \
                redirect_stderr(diagnostics):
            code = generate_fresh_code(secret)
        self.assertEqual(code, generate_one_time_code(secret, 120))
        self.assertIn("offset=-3600.0s", diagnostics.getvalue())
        self.assertNotIn(code, diagnostics.getvalue())
        self.assertNotIn(secret, diagnostics.getvalue())

    def test_fresh_code_waits_for_next_window_when_validity_is_short(self):
        secret = base64.b64encode(b"12345678901234567890").decode()
        with patch("otp.steam_clock", return_value=(148, 10, 0)), \
                patch("otp.time.monotonic", side_effect=[10, 12.1]), \
                patch("otp.time.sleep") as sleep, redirect_stderr(io.StringIO()):
            code = generate_fresh_code(secret)
        sleep.assert_called_once_with(2.1)
        self.assertEqual(code, generate_one_time_code(secret, 150.1))

    def test_invalid_secret_never_queries_steam(self):
        with patch("otp.steam_clock") as clock, self.assertRaises(ValueError):
            generate_fresh_code("invalid")
        clock.assert_not_called()


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

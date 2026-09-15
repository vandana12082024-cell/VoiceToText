import tempfile
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from prepare_android import ANDROID_NS, check_config, configure_android


class AndroidPreparationTests(unittest.TestCase):
    def test_configuration_requires_all_three_values(self):
        with self.assertRaisesRegex(ValueError, "API_BASE_URL"):
            check_config({})

    def test_configuration_rejects_local_http_and_server_keys(self):
        config = {
            "API_BASE_URL": "https://api.example.com",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_example",
        }
        check_config(config)
        with self.assertRaises(ValueError):
            check_config({**config, "API_BASE_URL": "http://localhost:8000"})
        with self.assertRaises(ValueError):
            check_config({**config, "SUPABASE_PUBLISHABLE_KEY": "sb_secret_example"})
        with self.assertRaises(ValueError):
            check_config({**config, "API_BASE_URL": "https://api.example.com/api/v1"})

    def test_permissions_are_idempotent_and_existing_activity_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="voice-android-test-") as directory:
            mobile = Path(directory)
            manifest = mobile / "android/app/src/main/AndroidManifest.xml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                f'<manifest xmlns:android="{ANDROID_NS}"><application android:label="old">'
                '<activity android:name=".MainActivity" /></application></manifest>',
                encoding="utf-8",
            )
            gradle = mobile / "android/app/build.gradle.kts"
            gradle.write_text("defaultConfig { minSdk = flutter.minSdkVersion }", encoding="utf-8")
            configure_android(mobile)
            first_result = manifest.read_bytes()
            configure_android(mobile)
            self.assertEqual(manifest.read_bytes(), first_result)
            tree = ET.parse(manifest)
            names = {node.get(f"{{{ANDROID_NS}}}name") for node in tree.findall("uses-permission")}
            self.assertEqual(names, {"android.permission.INTERNET", "android.permission.RECORD_AUDIO"})
            self.assertIsNotNone(tree.find("application/activity"))
            self.assertIn("maxOf(23, flutter.minSdkVersion)", gradle.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

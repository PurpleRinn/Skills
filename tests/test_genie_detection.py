import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "genie" / "scripts" / "genie.py"
SPEC = importlib.util.spec_from_file_location("genie_script", SCRIPT_PATH)
assert SPEC and SPEC.loader
GENIE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENIE)


class GenieDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> None:
        destination = self.project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def write_package(self, relative: str, dependencies: dict[str, str]) -> None:
        self.write(relative, json.dumps({"dependencies": dependencies}))

    def detect(self) -> dict:
        return GENIE.detect_project_structure(self.project)

    def test_flutter_web_admin_and_backend_enable_all_tracks(self) -> None:
        self.write(
            "pubspec.yaml",
            "name: app\ndependencies:\n  flutter:\n    sdk: flutter\n",
        )
        self.write_package("admin/package.json", {"vue": "latest", "vite": "latest"})
        self.write_package(
            "functions/package.json", {"firebase-functions": "latest"}
        )

        detected = self.detect()

        self.assertEqual(detected["profile"], "flutter-web-backend")
        self.assertEqual(detected["surfaces"], ["backend", "mobile", "web-admin"])
        self.assertEqual(detected["frameworks"]["mobile"], ["flutter"])
        self.assertEqual(detected["frameworks"]["web"], ["vue"])
        self.assertIn("cross-surface", detected["tracks"])

    def test_react_native_is_not_mistaken_for_web(self) -> None:
        self.write_package(
            "package.json", {"react": "latest", "react-native": "latest"}
        )

        detected = self.detect()

        self.assertEqual(detected["surfaces"], ["mobile"])
        self.assertEqual(detected["frameworks"], {"mobile": ["react-native"]})
        self.assertNotIn("web", detected["tracks"])

    def test_expo_web_target_remains_one_mobile_surface(self) -> None:
        self.write_package(
            "package.json",
            {
                "expo": "latest",
                "expo-updates": "latest",
                "react": "latest",
                "react-dom": "latest",
                "react-native": "latest",
                "react-native-web": "latest",
            },
        )

        detected = self.detect()

        self.assertEqual(detected["surfaces"], ["mobile"])
        self.assertEqual(detected["frameworks"], {"mobile": ["expo"]})
        self.assertIn("web", detected["targets"])
        self.assertIn("ota", detected["capabilities"])
        self.assertNotIn("web", detected["tracks"])

    def test_non_react_ssr_web_framework_is_detected(self) -> None:
        self.write_package(
            "package.json",
            {"@sveltejs/kit": "latest", "svelte": "latest", "vite": "latest"},
        )

        detected = self.detect()

        self.assertEqual(detected["surfaces"], ["web"])
        self.assertIn("sveltekit", detected["frameworks"]["web"])
        self.assertIn("ssr", detected["capabilities"])
        self.assertNotIn("mobile", detected["tracks"])

    def test_schema_one_flutter_config_migrates_to_mobile(self) -> None:
        migrated = GENIE.migrate_project_config(
            {
                "schema_version": 1,
                "detected": {
                    "technologies": ["dart", "flutter"],
                    "surfaces": ["flutter"],
                },
                "tracks": ["core", "flutter"],
                "paths": {"flutter": ["app/**"]},
            }
        )

        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["tracks"], ["core", "mobile"])
        self.assertEqual(migrated["detected"]["surfaces"], ["mobile"])
        self.assertEqual(migrated["paths"], {"mobile": ["app/**"]})
        self.assertEqual(migrated["frameworks"], {"mobile": ["flutter"]})

    def test_configure_json_output_contains_no_trailing_text(self) -> None:
        self.write_package(
            "package.json", {"react": "latest", "react-native": "latest"}
        )

        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "configure",
                "--project",
                str(self.project),
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = json.loads(process.stdout)

        self.assertFalse(payload["applied"])
        self.assertEqual(payload["config"]["frameworks"], {"mobile": ["react-native"]})


if __name__ == "__main__":
    unittest.main()

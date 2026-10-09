"""The Cascadeur installer, loaded from the repo root by path. Stdlib only."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "skeldar_cascade_installer",
    os.path.join(ROOT, "SkeldarAnim_Cascadeur_Install.py"))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

INSTALL = r"C:\Users\x\Documents\SkeldarAnim"


class SettingsEdit(unittest.TestCase):

    def base(self):
        return json.dumps({"ScriptsDir": "", "Python": {
            "Path": [], "Commands": ["commands"], "Scripts": ["scripts"]}})

    def test_adds_path_and_package(self):
        text, changed = installer.settings_edit(self.base(), INSTALL, "skeldar_cascadeur")
        data = json.loads(text)
        self.assertTrue(changed)
        self.assertIn(INSTALL, data["Python"]["Path"])
        self.assertIn("skeldar_cascadeur", data["Python"]["Scripts"])
        self.assertIn("scripts", data["Python"]["Scripts"])
        self.assertEqual(data["ScriptsDir"], "")
        self.assertEqual(data["Python"]["Commands"], ["commands"])

    def test_second_run_changes_nothing(self):
        first, _ = installer.settings_edit(self.base(), INSTALL, "skeldar_cascadeur")
        second, changed = installer.settings_edit(first, INSTALL, "skeldar_cascadeur")
        self.assertFalse(changed)
        self.assertEqual(json.loads(first), json.loads(second))

    def test_path_compare_ignores_case_and_trailing_slash(self):
        text = json.dumps({"Python": {"Path": [INSTALL.upper() + "\\"],
                                      "Scripts": ["skeldar_cascadeur"]}})
        _, changed = installer.settings_edit(text, INSTALL, "skeldar_cascadeur")
        self.assertFalse(changed)

    def test_missing_python_section_is_created(self):
        text, changed = installer.settings_edit("{}", INSTALL, "skeldar_cascadeur")
        self.assertTrue(changed)
        self.assertIn("skeldar_cascadeur", json.loads(text)["Python"]["Scripts"])

    def test_not_json_is_refused_and_nothing_changes(self):
        with self.assertRaises(installer.SetupError):
            installer.settings_edit("{broken", INSTALL, "skeldar_cascadeur")


class Archive(unittest.TestCase):

    def test_a_build_needs_the_bridge_module(self):
        self.assertTrue(installer.archive_problems(["SkeldarAnim/install.py"]))

    def test_a_good_build_passes(self):
        names = ["SkeldarAnim/install.py",
                 "SkeldarAnim/skeldar_cascadeur/bridge.py"]
        self.assertEqual(installer.archive_problems(names), [])

    def test_a_path_escape_is_refused(self):
        names = ["SkeldarAnim/skeldar_cascadeur/bridge.py", "../evil.py"]
        self.assertTrue(any("outside" in p for p in installer.archive_problems(names)))


class Install(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cascadeur_install_")
        self.zip = os.path.join(self.root, "SkeldarAnim.zip")
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr("SkeldarAnim/skeldar_cascadeur/bridge.py",
                             "def name():\n    return 'x'\n")
            archive.writestr("SkeldarAnim/install.py", "# build\n")
        self.target = os.path.join(self.root, "Documents", "SkeldarAnim")
        self.settings = os.path.join(self.root, "Cascadeur", "settings.json")
        os.makedirs(os.path.dirname(self.settings))
        with open(self.settings, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"ScriptsDir": "", "Python": {
                "Path": [], "Commands": ["commands"], "Scripts": ["scripts"]}}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_installs_edits_settings_and_backs_up(self):
        status = installer.install(source_zip=self.zip, install_dir=self.target,
                                   settings_path=self.settings)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "skeldar_cascadeur", "bridge.py")))
        self.assertTrue(os.path.isfile(self.settings + ".skeldar-backup"))
        with open(self.settings, encoding="utf-8") as handle:
            self.assertIn("skeldar_cascadeur", json.load(handle)["Python"]["Scripts"])
        self.assertIn("restart", status.lower())

    def test_second_run_updates_and_leaves_settings_alone(self):
        installer.install(source_zip=self.zip, install_dir=self.target,
                          settings_path=self.settings)
        with open(self.settings, encoding="utf-8") as handle:
            after_first = handle.read()
        status = installer.install(source_zip=self.zip, install_dir=self.target,
                                   settings_path=self.settings)
        with open(self.settings, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), after_first)
        self.assertIn("already", status.lower())

    def test_refuses_a_folder_that_is_not_ours(self):
        os.makedirs(self.target)
        with open(os.path.join(self.target, "my_notes.txt"), "w") as handle:
            handle.write("keep me")
        with self.assertRaises(installer.SetupError):
            installer.install(source_zip=self.zip, install_dir=self.target,
                              settings_path=self.settings)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "my_notes.txt")))

    def test_a_read_only_settings_file_is_refused_before_anything_is_copied(self):
        import stat
        os.chmod(self.settings, stat.S_IREAD)
        try:
            with self.assertRaises(installer.SetupError) as caught:
                installer.install(source_zip=self.zip, install_dir=self.target,
                                  settings_path=self.settings)
            self.assertIn("read-only", str(caught.exception))
            self.assertFalse(os.path.exists(self.target))
        finally:
            os.chmod(self.settings, stat.S_IWRITE | stat.S_IREAD)

    def test_refuses_when_the_settings_file_is_missing(self):
        with self.assertRaises(installer.SetupError):
            installer.install(source_zip=self.zip, install_dir=self.target,
                              settings_path=self.settings + ".nope")
        self.assertFalse(os.path.exists(self.target))


if __name__ == "__main__":
    unittest.main()

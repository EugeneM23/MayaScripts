"""Tests for the drag-and-drop installer and its icons.

The icon checks parse the PNG header by hand -- IHDR width/height are
big-endian at bytes 16..24 -- because there is no PIL in the Maya tree
and none is going in.
"""

import os
import subprocess
import sys
import unittest

import install

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON_NAMES = ("picker.png", "uebridge.png", "scenesetup.png",
              "overshoot.png")


class Icons(unittest.TestCase):

    def _header(self, name):
        path = os.path.join(REPO, "icons", name)
        self.assertTrue(os.path.isfile(path), path)
        with open(path, "rb") as handle:
            return handle.read(24)

    def test_all_four_exist_as_png(self):
        for name in ICON_NAMES:
            head = self._header(name)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", name)

    def test_all_four_are_32_by_32(self):
        for name in ICON_NAMES:
            head = self._header(name)
            width = int.from_bytes(head[16:20], "big")
            height = int.from_bytes(head[20:24], "big")
            self.assertEqual((width, height), (32, 32), name)


class MayaFreeBoundary(unittest.TestCase):
    """install.py runs at drop time, before anything of ours is on
    sys.path -- it must import with stdlib alone."""

    def test_importing_install_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "import install\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing install leaked: " + result.stdout.strip())


class Payload(unittest.TestCase):
    """The whitelist is the contract: everything on it exists in the repo,
    and the animator's prefs get nothing else."""

    def test_every_entry_exists_in_the_repo(self):
        for name in install.payload():
            self.assertTrue(
                os.path.exists(os.path.join(REPO, name)), name)

    def test_the_dev_only_folders_stay_out(self):
        for name in ("tests", "docs", "archive", "maya_retarget.py"):
            self.assertNotIn(name, install.payload())

    def test_the_installer_ships_itself(self):
        """A colleague repairs the shelf by re-dragging install.py from
        the installed folder -- so the installed folder must hold it."""
        self.assertIn("install.py", install.payload())
        self.assertIn("README_INSTALL.txt", install.payload())

    def test_source_root_is_this_repo(self):
        self.assertEqual(os.path.normcase(install.source_root()),
                         os.path.normcase(REPO))


class ButtonSpecs(unittest.TestCase):

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_five_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["Rig Picker", "UE Bridge", "Scene Setup",
                                  "Overshoot", "OverRig"])

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "Rig Picker": ("maya_overrig", "show_picker"),
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
        }
        for spec in self._specs()[:4]:
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()[:4]]
        self.assertEqual(icons, [
            self.DEST + "/icons/picker.png",
            self.DEST + "/icons/uebridge.png",
            self.DEST + "/icons/scenesetup.png",
            self.DEST + "/icons/overshoot.png"])

    def test_overrig_button_replays_the_native_installer(self):
        """Verbatim from OverRig's own Drag_and_Drop_to_install.mel: the
        source, both globals, misc/ and the coloring argument."""
        spec = self._specs()[4]
        self.assertEqual(spec["sourceType"], "mel")
        command = spec["command"]
        self.assertIn(
            'source "{0}/overrig/base_OverRig_scripts.mel";'.format(
                self.DEST), command)
        self.assertIn("global int $barnev_OverRig_RotateOrder = 0;", command)
        self.assertIn(
            '$path_to_JGLBN = "{0}/overrig/misc/";'.format(self.DEST),
            command)
        self.assertIn("base_OverRig_scripts(1);", command)
        self.assertEqual(spec["image"],
                         self.DEST + "/overrig/icons/base_OverRig.bmp")

    def test_backslashes_never_reach_a_command(self):
        for spec in install.button_specs(
                "C:\\Users\\Some Body\\Documents\\maya\\scripts\\SkeldarAnim"):
            self.assertNotIn("\\", spec["command"])
            self.assertNotIn("\\", spec["image"])


if __name__ == "__main__":
    unittest.main()

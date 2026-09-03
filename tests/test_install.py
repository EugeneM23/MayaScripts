"""Tests for the drag-and-drop installer and its icons.

The icon checks parse the PNG header by hand -- IHDR width/height are
big-endian at bytes 16..24 -- because there is no PIL in the Maya tree
and none is going in.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import install

# The PLUGIN folder, not the repo root. Payload names have always been
# relative to the folder holding install.py, and since 2026-09-01 that is
# the repo's SkeldarAnim/ -- the workshop keeps the standalone tools.
PLUGIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "SkeldarAnim")
REPO = PLUGIN

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

    def test_the_hotkey_map_ships(self):
        self.assertIn("maya_hotkeys.py", install.payload())

    def test_the_viewport_studio_ships(self):
        self.assertIn("maya_vpstudio.py", install.payload())

    def test_every_icon_a_button_names_exists(self):
        """A missing icon is a shelf button with a blank square on it."""
        for spec in install.button_specs(PLUGIN):
            self.assertTrue(os.path.exists(spec["image"]), spec["image"])

    def test_source_root_is_the_plugin_folder(self):
        self.assertEqual(os.path.normcase(install.source_root()),
                         os.path.normcase(PLUGIN))

    def test_the_workshop_tools_stay_out_of_the_plugin_folder(self):
        """The point of the SkeldarAnim/ split: if it ships it is in
        there, and the standalone tools are not."""
        for name in ("maya_skelfit.py", "maya_meltmorph.py",
                     "make_build.py", "tests"):
            self.assertFalse(
                os.path.exists(os.path.join(PLUGIN, name)), name)


class ButtonSpecs(unittest.TestCase):

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_seven_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["Rig Picker", "UE Bridge", "Scene Setup",
                                  "Overshoot", "Hotkeys", "Studio",
                                  "OverRig"])

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "Rig Picker": ("maya_overrig", "show_picker"),
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
            "Hotkeys": ("maya_hotkeys", "toggle"),
            "Studio": ("maya_vpstudio", "show_window"),
        }
        for spec in self._specs()[:6]:
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()[:6]]
        self.assertEqual(icons, [
            self.DEST + "/icons/picker.png",
            self.DEST + "/icons/uebridge.png",
            self.DEST + "/icons/scenesetup.png",
            self.DEST + "/icons/overshoot.png",
            self.DEST + "/icons/hotkeys.png",
            self.DEST + "/icons/vpstudio.png"])

    def test_overrig_button_replays_the_native_installer(self):
        """Verbatim from OverRig's own Drag_and_Drop_to_install.mel: the
        source, both globals, misc/ and the coloring argument."""
        spec = self._specs()[6]
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


class CopyPayload(unittest.TestCase):
    """copy_payload against a throwaway destination: whitelist in,
    caches out, idempotent, and never eats its own source."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_install_")
        self.dest = os.path.join(self.tmp, "SkeldarAnim")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copies_exactly_the_payload(self):
        install.copy_payload(REPO, self.dest)
        self.assertEqual(sorted(os.listdir(self.dest)),
                         sorted(install.payload()))

    def test_pycache_stays_home(self):
        install.copy_payload(REPO, self.dest)
        for base, dirs, files in os.walk(self.dest):
            self.assertNotIn("__pycache__", dirs, base)
            for name in files:
                self.assertFalse(name.endswith(".pyc"),
                                 os.path.join(base, name))

    def test_overrig_misc_survives_the_trip(self):
        """OverRig's own button points $path_to_JGLBN at misc/."""
        install.copy_payload(REPO, self.dest)
        self.assertTrue(os.path.isdir(
            os.path.join(self.dest, "overrig", "misc")))

    def test_second_run_replaces_rather_than_accumulates(self):
        install.copy_payload(REPO, self.dest)
        stray = os.path.join(self.dest, "stray.txt")
        with open(stray, "w") as handle:
            handle.write("left over")
        install.copy_payload(REPO, self.dest)
        self.assertFalse(os.path.exists(stray))

    def test_same_place_sees_through_slash_styles(self):
        os.makedirs(self.dest)
        self.assertTrue(install.same_place(
            self.dest, self.dest.replace("\\", "/")))

    def test_same_place_is_false_for_a_missing_destination(self):
        self.assertFalse(install.same_place(REPO, self.dest))


class PurgeModules(unittest.TestCase):
    """The update's other half: the import cache, not just the files.

    A fake sys.modules is passed in, so no test can knock the real one
    out from under the suite it is running in.
    """

    def test_the_names_are_what_the_buttons_import(self):
        names = install.module_names()
        self.assertIn("maya_overrig", names)
        self.assertIn("maya_uebridge", names)
        self.assertIn("maya_scenesetup", names)
        self.assertIn("maya_overshoot", names)

    def test_install_itself_is_never_purged(self):
        self.assertNotIn("install", install.module_names())

    def test_data_folders_are_not_modules(self):
        for name in ("icons", "assets", "overrig"):
            self.assertNotIn(name, install.module_names())

    def test_the_package_root_goes_with_its_submodules(self):
        fake = {"maya_overrig": 1, "maya_overrig.builder": 2,
                "maya_overrig.picker_view": 3}
        dropped = install.purge_modules(["maya_overrig"], fake)
        self.assertEqual(fake, {})
        self.assertEqual(dropped, ["maya_overrig", "maya_overrig.builder",
                                   "maya_overrig.picker_view"])

    def test_strangers_are_left_alone(self):
        fake = {"maya_overrig": 1, "maya": 2, "maya.cmds": 3,
                "maya_overrigged": 4}
        install.purge_modules(["maya_overrig"], fake)
        self.assertEqual(sorted(fake), ["maya", "maya.cmds",
                                        "maya_overrigged"])

    def test_nothing_loaded_drops_nothing(self):
        self.assertEqual(install.purge_modules(["maya_overrig"], {}), [])


if __name__ == "__main__":
    unittest.main()

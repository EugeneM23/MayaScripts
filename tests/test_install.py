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
              "retarget.png",
              "overshoot.png", "hotkeys.png", "vpstudio.png",
              "colour.png")


class Icons(unittest.TestCase):

    def _header(self, name):
        path = os.path.join(REPO, "icons", name)
        self.assertTrue(os.path.isfile(path), path)
        with open(path, "rb") as handle:
            return handle.read(24)

    def test_every_icon_exists_as_png(self):
        for name in ICON_NAMES:
            head = self._header(name)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", name)

    def test_every_icon_is_32_by_32(self):
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

    def test_the_colour_palette_ships(self):
        self.assertIn("maya_colour.py", install.payload())

    def test_the_curve_overlay_left_the_plugin(self):
        """2026-09-08: «уберем не только из полки но и из плагина в
        целом» -- it lives in archive/ now, and ships nowhere."""
        self.assertNotIn("maya_curveview", install.payload())
        self.assertNotIn("maya_curveview", install.module_names())
        self.assertFalse(os.path.exists(os.path.join(PLUGIN, "maya_curveview")))
        self.assertTrue(os.path.isfile(os.path.join(
            os.path.dirname(PLUGIN), "archive", "maya_curveview",
            "maya_curveview", "tool.py")))

    def test_overshoot_still_ships_behind_its_flag(self):
        """Off the shelf, not out of the plugin (the picker's precedent)."""
        self.assertIn("maya_overshoot.py", install.payload())
        self.assertFalse(install.features().OVERSHOOT)

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
    """The shelf as data. Since 2026-09-07 the Rig Picker and the OverRig
    panel sit behind `skeldar_features` flags, and since 2026-09-08 so does
    Overshoot: off, the shelf is the six buttons of the AdvancedSkeleton
    pipeline; on, each comes back in its old place. Bake folded into
    Retarget and the Curve Overlay left the plugin the same day."""

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def setUp(self):
        self.features = install.features()
        self.saved = (self.features.OVERRIG, self.features.PICKER,
                      self.features.OVERSHOOT)
        self.features.OVERRIG = False
        self.features.PICKER = False
        self.features.OVERSHOOT = False

    def tearDown(self):
        (self.features.OVERRIG, self.features.PICKER,
         self.features.OVERSHOOT) = self.saved

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_the_flags_ship_off(self):
        """The shipped default: OverRig, the picker and Overshoot are off."""
        self.assertEqual(self.saved, (False, False, False))

    def test_features_loads_the_module_beside_install(self):
        self.assertEqual(
            os.path.normcase(self.features.__file__),
            os.path.normcase(os.path.join(PLUGIN, "skeldar_features.py")))

    def test_six_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["UE Bridge", "Scene Setup", "Retarget",
                                  "Hotkeys", "Studio", "Colour"])

    def test_no_bake_and_no_curves_button(self):
        """Bake folded into Retarget; the Curve Overlay left (2026-09-08)."""
        for flag in ("PICKER", "OVERRIG", "OVERSHOOT"):
            setattr(self.features, flag, True)
        labels = [s["label"] for s in self._specs()]
        self.assertNotIn("Bake", labels)
        self.assertNotIn("Curves", labels)

    def test_the_flags_bring_the_picker_and_overrig_back(self):
        self.features.PICKER = True
        self.features.OVERRIG = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels[0], "Rig Picker")
        self.assertEqual(labels[-1], "OverRig")
        self.assertEqual(len(labels), 8)

    def test_the_overshoot_flag_brings_its_button_back_in_place(self):
        self.features.OVERSHOOT = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["UE Bridge", "Scene Setup", "Retarget",
                                  "Overshoot", "Hotkeys", "Studio",
                                  "Colour"])

    def test_each_flag_acts_alone(self):
        self.features.PICKER = True
        labels = [s["label"] for s in self._specs()]
        self.assertIn("Rig Picker", labels)
        self.assertNotIn("OverRig", labels)
        self.features.PICKER = False
        self.features.OVERRIG = True
        labels = [s["label"] for s in self._specs()]
        self.assertNotIn("Rig Picker", labels)
        self.assertEqual(labels[-1], "OverRig")

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Retarget": ("maya_rig_retarget", "retarget_button"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
            "Hotkeys": ("maya_hotkeys", "toggle"),
            "Studio": ("maya_vpstudio", "show_window"),
            "Colour": ("maya_colour", "show_window"),
        }
        self.features.OVERSHOOT = True
        for spec in self._specs():
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_the_picker_button_still_knows_its_module(self):
        self.features.PICKER = True
        spec = self._specs()[0]
        self.assertIn("import maya_overrig", spec["command"])
        self.assertIn("maya_overrig.show_picker()", spec["command"])
        self.assertEqual(spec["image"], self.DEST + "/icons/picker.png")

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()]
        self.assertEqual(icons, [self.DEST + "/icons/" + name for name in (
            "uebridge.png", "scenesetup.png", "retarget.png",
            "hotkeys.png", "vpstudio.png", "colour.png")])

    def test_the_payload_carries_the_flags_and_the_retarget(self):
        for name in ("skeldar_features.py", "maya_rigs.py", "maya_asretarget.py",
                     "maya_pmretarget.py", "maya_rig_retarget.py"):
            self.assertIn(name, install.payload())
            self.assertTrue(os.path.isfile(os.path.join(PLUGIN, name)), name)
        for name in ("maya_asretarget", "maya_pmretarget", "maya_rigs",
                     "maya_rig_retarget", "skeldar_features"):
            self.assertIn(name, install.module_names())

    def test_overrig_button_replays_the_native_installer(self):
        """Verbatim from OverRig's own Drag_and_Drop_to_install.mel: the
        source, both globals, misc/ and the coloring argument."""
        self.features.OVERRIG = True
        spec = self._specs()[-1]
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

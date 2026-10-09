"""Tests for the drag-and-drop installer and its icons.

The icon checks parse the PNG header by hand -- IHDR width/height are
big-endian at bytes 16..24 -- because there is no PIL in the Maya tree
and none is going in.
"""

import json
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

ICON_NAMES = ("picker.png", "hub.png", "uebridge.png", "characters.png", "weapons.png",
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

    def test_the_graph_overlay_ships(self):
        self.assertIn("maya_graphoverlay", install.payload())
        self.assertIn("maya_com", install.payload())

    def test_the_pose_library_ships(self):
        """2026-10-02: the package and its library folder - a package is purged on an update,
        the library is data."""
        self.assertIn("maya_poselib", install.payload())
        self.assertIn("poses", install.payload())
        self.assertIn("maya_poselib", install.module_names())
        self.assertNotIn("poses", install.module_names())
        self.assertTrue(os.path.isfile(os.path.join(PLUGIN, "poses", ".gitkeep")))

    def test_the_viewport_studio_ships(self):
        self.assertIn("maya_vpstudio.py", install.payload())

    def test_the_edge_panel_ships(self):
        """2026-10-08: the hub's second home, its rules and its windows."""
        self.assertIn("maya_edgerules.py", install.payload())
        self.assertIn("maya_hubedge.py", install.payload())

    def test_the_startup_plugin_ships(self):
        """2026-10-08: the edge panel waiting from Maya's start - the folder
        is data to Python (no __init__), the plug-in Maya's."""
        self.assertIn("plug-ins", install.payload())
        self.assertNotIn("plug-ins", install.module_names())
        self.assertTrue(os.path.isfile(os.path.join(
            PLUGIN, "plug-ins", install.STARTUP_PLUGIN + ".py")))

    def test_the_colour_palette_ships(self):
        self.assertIn("maya_colour.py", install.payload())

    def test_the_window_fit_helper_ships(self):
        """Studio and Colour size their windows through it."""
        self.assertIn("maya_winfit.py", install.payload())

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
    """The shelf as data. Since 2026-09-19 the shipped shelf is TWO buttons,
    the hub and OverRig's native panel («пока пусть будет только наш
    SkeldarAnim ну и овер риг»): the seven section buttons sit behind
    `SECTION_BUTTONS`, the Rig Picker behind `PICKER` (2026-09-07),
    Overshoot behind `OVERSHOOT` (2026-09-08); on, each comes back in its
    old place. `OVERRIG` is the shelf button alone -- the 84 hotkey rows
    ride `OVERRIG_HOTKEYS`, which stays off."""

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    FLAGS = ("OVERRIG", "OVERRIG_HOTKEYS", "PICKER", "OVERSHOOT",
             "SECTION_BUTTONS")

    def setUp(self):
        self.features = install.features()
        self.saved = dict((f, getattr(self.features, f)) for f in self.FLAGS)
        # The "everything off" baseline every test below starts from; the
        # shipped values are pinned by test_the_flags_ship_as_two_buttons.
        for flag in self.FLAGS:
            setattr(self.features, flag, False)

    def tearDown(self):
        for flag, value in self.saved.items():
            setattr(self.features, flag, value)

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_the_flags_ship_as_two_buttons(self):
        """The shipped default (2026-09-19): the OverRig button on, the
        section buttons, the picker, Overshoot and the OverRig hotkeys off."""
        self.assertEqual(self.saved, {
            "OVERRIG": True, "OVERRIG_HOTKEYS": False, "PICKER": False,
            "OVERSHOOT": False, "SECTION_BUTTONS": False})

    def test_the_shipped_shelf_is_the_hub_and_overrig(self):
        for flag, value in self.saved.items():
            setattr(self.features, flag, value)
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim", "OverRig"])

    def test_the_hub_alone_with_everything_off(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim"])

    def test_features_loads_the_module_beside_install(self):
        self.assertEqual(
            os.path.normcase(self.features.__file__),
            os.path.normcase(os.path.join(PLUGIN, "skeldar_features.py")))

    def test_section_buttons_come_back_in_shelf_order(self):
        """The hub first (2026-09-17), then the seven sections it holds."""
        self.features.SECTION_BUTTONS = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim", "UE Bridge", "Characters",
                                  "Weapons", "Retarget", "Hotkeys", "Studio",
                                  "Colour"])

    def test_the_hub_ships(self):
        self.assertIn("maya_hub.py", install.payload())

    def test_the_hub_s_skin_ships(self):
        """2026-09-28: without them the hub falls back to classic, and
        every builder's `import maya_hubstyle` fails outright."""
        for name in ("maya_hubstyle.py", "maya_hubicons.py", "maya_hubqt.py"):
            self.assertIn(name, install.payload())

    def test_every_plugin_module_ships(self):
        """A module beside install.py that the payload forgets reaches a
        colleague as an ImportError days later."""
        for name in os.listdir(REPO):
            if name.endswith(".py") and name.startswith("maya_"):
                self.assertIn(name, install.payload(), name)

    def test_no_bake_and_no_curves_button(self):
        """Bake folded into Retarget; the Curve Overlay left (2026-09-08)."""
        for flag in ("PICKER", "OVERRIG", "OVERSHOOT"):
            setattr(self.features, flag, True)
        labels = [s["label"] for s in self._specs()]
        self.assertNotIn("Bake", labels)
        self.assertNotIn("Curves", labels)

    def test_the_flags_bring_the_picker_and_overrig_back(self):
        self.features.SECTION_BUTTONS = True
        self.features.PICKER = True
        self.features.OVERRIG = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels[1], "Rig Picker")
        self.assertEqual(labels[-1], "OverRig")
        self.assertEqual(len(labels), 10)

    def test_the_overshoot_flag_brings_its_button_back_in_place(self):
        self.features.SECTION_BUTTONS = True
        self.features.OVERSHOOT = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim", "UE Bridge", "Characters",
                                  "Weapons", "Retarget", "Overshoot",
                                  "Hotkeys", "Studio", "Colour"])

    def test_each_flag_acts_alone(self):
        self.features.PICKER = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim", "Rig Picker"])
        self.features.PICKER = False
        self.features.OVERRIG = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim", "OverRig"])
        self.features.OVERRIG = False
        self.features.OVERRIG_HOTKEYS = True
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["SkeldarAnim"],
                         "the hotkey flag must not put a button on the shelf")

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "SkeldarAnim": ("maya_hub", "show"),
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Characters": ("maya_scenesetup", "show_window"),
            "Weapons": ("maya_scenesetup", "show_weapons"),
            "Retarget": ("maya_rig_retarget", "retarget_button"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
            "Hotkeys": ("maya_hotkeys", "toggle"),
            "Studio": ("maya_vpstudio", "show_window"),
            "Colour": ("maya_colour", "show_window"),
        }
        self.features.SECTION_BUTTONS = True
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
        spec = self._specs()[1]
        self.assertIn("import maya_overrig", spec["command"])
        self.assertIn("maya_overrig.show_picker()", spec["command"])
        self.assertEqual(spec["image"], self.DEST + "/icons/picker.png")

    def test_python_buttons_use_our_icons(self):
        self.features.SECTION_BUTTONS = True
        icons = [s["image"] for s in self._specs()]
        self.assertEqual(icons, [self.DEST + "/icons/" + name for name in (
            "hub.png", "uebridge.png", "characters.png", "weapons.png",
            "retarget.png", "hotkeys.png", "vpstudio.png", "colour.png")])

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


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _sha(text):
    import hashlib
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _card_json(name):
    return json.dumps({"format": "skeldar.pose", "version": 1, "kind": "character",
                       "name": name})


def _anim_json(name, note=""):
    return json.dumps({"format": "skeldar.anim", "version": 1, "kind": "character",
                       "name": name, "note": note})


class KeepsLocalPoses(unittest.TestCase):
    """2026-10-02, the Pose Library: «локальные позы переживают каждую установку». The installed
    `poses/` is moved aside before the folder is replaced and put back CARD by CARD (2026-10-03,
    the final review): the previous build's manifest (`poses/.shipped.json`) tells its own cards
    from the colleague's; a local card never merges into a shipped one - it goes back whole, at
    its place, or beside a shipped card of its name as `<Name> (local)`."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_poses_")
        self.src = os.path.join(self.tmp, "build", "SkeldarAnim")
        self.dest = os.path.join(self.tmp, "prefs", "SkeldarAnim")
        _write(os.path.join(self.src, "maya_tool.py"), "new tool")
        _write(os.path.join(self.src, "poses", ".gitkeep"), "")
        _write(os.path.join(self.src, "poses", "Shipped.pose", "pose.json"), "new shipped")
        _write(os.path.join(self.dest, "maya_tool.py"), "old tool")
        _write(os.path.join(self.dest, "stray.txt"), "left over")
        _write(os.path.join(self.dest, "poses", "Shipped.pose", "pose.json"), "old shipped")
        self.manifest(self.poses(), {"Shipped.pose": {"pose.json": _sha("old shipped")}})
        _write(os.path.join(self.dest, "poses", "Mine.pose", "pose.json"), "mine")
        _write(os.path.join(self.dest, "poses", "Mine.pose", "thumbnail.jpg"), "jpg")
        _write(os.path.join(self.dest, "poses", "Fights", "Kick.pose", "pose.json"), "kick")
        os.makedirs(os.path.join(self.dest, "poses", "Empty folder"))
        self.saved = (install.payload, install._say)
        self.said = []
        install.payload = lambda: ("maya_tool.py", "poses")
        install._say = self.said.append

    def tearDown(self):
        install.payload, install._say = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def poses(self, *parts):
        return os.path.join(self.dest, "poses", *parts)

    @staticmethod
    def manifest(poses, cards):
        """A previous install's `.shipped.json`, as that install wrote it."""
        _write(os.path.join(poses, install.SHIPPED),
               install.manifest_text({"format": install.SHIPPED_FORMAT, "version": 1,
                                      "cards": cards}))

    def build(self, cards):
        """A build tree of its own: `cards` {relative card path: {file: text}}."""
        root = tempfile.mkdtemp(prefix="build_", dir=self.tmp)
        _write(os.path.join(root, "maya_tool.py"), "tool")
        _write(os.path.join(root, "poses", ".gitkeep"), "")
        for rel, files in cards.items():
            for name, text in files.items():
                _write(os.path.join(root, "poses", *(rel.split("/") + [name])), text)
        return root

    def listing(self):
        return sorted(install.poses_walk(self.poses())[0])

    # ---- the rules that stood, on the new mechanism

    def test_a_local_card_survives_and_a_shipped_one_is_the_build_s(self):
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Mine.pose", "pose.json")), "mine")
        self.assertEqual(_read(self.poses("Mine.pose", "thumbnail.jpg")), "jpg")
        self.assertEqual(_read(self.poses("Fights", "Kick.pose", "pose.json")), "kick")
        self.assertEqual(_read(self.poses("Shipped.pose", "pose.json")), "new shipped")
        self.assertEqual(sorted(kept), ["Fights/Kick.pose/pose.json", "Mine.pose/pose.json",
                                        "Mine.pose/thumbnail.jpg"])
        self.assertEqual(kept.renamed, {})
        self.assertEqual(self.listing(), ["Fights/Kick.pose", "Mine.pose", "Shipped.pose"])

    def test_the_new_manifest_lists_the_build_s_cards_only(self):
        install.copy_payload(self.src, self.dest)
        self.assertEqual(install.read_shipped(self.poses()),
                         {"Shipped.pose": {"pose.json": _sha("new shipped")}})

    def test_an_empty_local_folder_survives(self):
        install.copy_payload(self.src, self.dest)
        self.assertTrue(os.path.isdir(self.poses("Empty folder")))

    def test_the_rest_is_still_replaced(self):
        install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(os.path.join(self.dest, "maya_tool.py")), "new tool")
        self.assertFalse(os.path.exists(os.path.join(self.dest, "stray.txt")))

    def test_nothing_is_left_beside_the_install(self):
        install.copy_payload(self.src, self.dest)
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), ["SkeldarAnim"])

    def test_a_fresh_install_keeps_nothing_and_records_the_build(self):
        shutil.rmtree(self.dest)
        self.assertEqual(install.copy_payload(self.src, self.dest), [])
        self.assertEqual(sorted(os.listdir(self.poses())),
                         [".gitkeep", install.SHIPPED, "Shipped.pose"])
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), ["SkeldarAnim"])

    # ---- the critical finding: a local card of a shipped card's name

    def test_a_local_card_of_a_shipped_card_s_name_goes_beside_it_whole(self):
        """The default name is «Pose»: the first shipped `Pose` replaced every colleague's own
        `Pose` and glued their thumbnail onto it."""
        _write(self.poses("Pose.pose", "pose.json"), _card_json("Pose"))
        _write(self.poses("Pose.pose", "thumbnail.jpg"), "their picture")
        _write(os.path.join(self.src, "poses", "Pose.pose", "pose.json"), "shipped pose")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(sorted(os.listdir(self.poses("Pose.pose"))), ["pose.json"])
        self.assertEqual(_read(self.poses("Pose.pose", "pose.json")), "shipped pose")
        local = self.poses("Pose (local).pose")
        self.assertEqual(json.loads(_read(os.path.join(local, "pose.json")))["name"],
                         "Pose (local)")
        self.assertEqual(_read(os.path.join(local, "thumbnail.jpg")), "their picture")
        self.assertEqual(kept.renamed, {"Pose.pose": "Pose (local).pose"})
        self.assertTrue(any("Pose (local).pose" in line for line in self.said))
        self.assertIn("(local)", install.poses_note(kept))
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), ["SkeldarAnim"])

    def test_a_case_twin_is_one_card_and_goes_beside_it(self):
        _write(self.poses("fist.pose", "pose.json"), "mine")
        _write(os.path.join(self.src, "poses", "Fist.pose", "pose.json"), "shipped fist")
        if not os.path.exists(os.path.join(self.src, "poses", "FIST.pose")):
            self.skipTest("a case-sensitive disk: two cards")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Fist.pose", "pose.json")), "shipped fist")
        self.assertEqual(_read(self.poses("fist (local).pose", "pose.json")), "mine")
        self.assertEqual(kept.renamed, {"fist.pose": "fist (local).pose"})

    def test_a_second_local_twin_takes_the_next_free_name(self):
        _write(self.poses("Pose.pose", "pose.json"), "mine")
        _write(self.poses("Pose (local).pose", "pose.json"), "an older local one")
        _write(os.path.join(self.src, "poses", "Pose.pose", "pose.json"), "shipped")
        _write(os.path.join(self.src, "poses", "Pose (local).pose", "pose.json"), "shipped too")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Pose (local) 2.pose", "pose.json")), "mine")
        self.assertEqual(_read(self.poses("Pose (local) (local).pose", "pose.json")),
                         "an older local one")
        self.assertEqual(len(kept.renamed), 2)

    def test_a_local_card_the_same_as_the_build_s_is_not_doubled(self):
        """An install from before the manifest: a card byte-identical to the new build's own is
        the build's, not a local one to keep beside it."""
        os.remove(self.poses(install.SHIPPED))
        _write(self.poses("Shipped.pose", "pose.json"), "new shipped")
        kept = install.copy_payload(self.src, self.dest)
        self.assertNotIn("Shipped (local).pose", os.listdir(self.poses()))
        self.assertEqual(kept.renamed, {})

    def test_a_shipped_card_the_colleague_changed_is_theirs(self):
        """Update from selection / Replace thumbnail on a shipped card: no longer the build's -
        kept beside the new build's own."""
        _write(self.poses("Shipped.pose", "pose.json"), "updated from the selection")
        _write(self.poses("Shipped.pose", "thumbnail.jpg"), "a new picture")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(sorted(os.listdir(self.poses("Shipped.pose"))), ["pose.json"])
        self.assertEqual(_read(self.poses("Shipped.pose", "pose.json")), "new shipped")
        local = self.poses("Shipped (local).pose")
        self.assertEqual(_read(os.path.join(local, "pose.json")), "updated from the selection")
        self.assertEqual(_read(os.path.join(local, "thumbnail.jpg")), "a new picture")
        self.assertEqual(kept.renamed, {"Shipped.pose": "Shipped (local).pose"})

    def test_a_file_where_a_local_folder_was_keeps_the_aside_and_says_where(self):
        _write(self.poses("Hands", "Grip.pose", "pose.json"), "grip")
        _write(os.path.join(self.src, "poses", "Hands"), "a file the build ships")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Hands")), "a file the build ships")
        self.assertIn("Hands/Grip.pose", kept.unrestored)
        left = [n for n in os.listdir(os.path.dirname(self.dest)) if n != "SkeldarAnim"]
        self.assertEqual(len(left), 1)
        aside = os.path.join(os.path.dirname(self.dest), left[0], "poses")
        self.assertEqual(_read(os.path.join(aside, "Hands", "Grip.pose", "pose.json")), "grip")
        self.assertEqual(kept.aside, aside.replace("\\", "/"))
        self.assertTrue(any(kept.aside in line for line in self.said))
        self.assertIn(kept.aside, install.poses_note(kept))
        #  everything else went back
        self.assertEqual(_read(self.poses("Mine.pose", "pose.json")), "mine")

    # ---- the important finding: what the build removed stays removed

    def test_renamed_deleted_and_moved_upstream_stay_gone(self):
        first = self.build({"Fist.pose": {"pose.json": "fist"},
                            "Old idle.pose": {"pose.json": "idle"},
                            "Grip.pose": {"pose.json": "grip"}})
        shutil.rmtree(self.dest)
        install.copy_payload(first, self.dest)
        _write(self.poses("Mine.pose", "pose.json"), "mine")
        second = self.build({"Punch.pose": {"pose.json": "fist"},     # Fist renamed
                             "Hands/Grip.pose": {"pose.json": "grip"}})   # Grip moved
        kept = install.copy_payload(second, self.dest)                # Old idle deleted
        self.assertEqual(self.listing(), ["Hands/Grip.pose", "Mine.pose", "Punch.pose"])
        self.assertEqual(sorted(kept.dropped), ["Fist.pose", "Grip.pose", "Old idle.pose"])
        self.assertEqual(list(kept), ["Mine.pose/pose.json"])
        #  and the third install too: nothing comes back
        install.copy_payload(second, self.dest)
        self.assertEqual(self.listing(), ["Hands/Grip.pose", "Mine.pose", "Punch.pose"])

    def test_a_dropped_card_the_colleague_changed_stays_at_its_place(self):
        first = self.build({"Old idle.pose": {"pose.json": "idle"}})
        shutil.rmtree(self.dest)
        install.copy_payload(first, self.dest)
        _write(self.poses("Old idle.pose", "pose.json"), "idle, my version")
        second = self.build({"Other.pose": {"pose.json": "other"}})
        kept = install.copy_payload(second, self.dest)
        self.assertEqual(_read(self.poses("Old idle.pose", "pose.json")), "idle, my version")
        self.assertEqual(kept.dropped, [])
        self.assertEqual(install.read_shipped(self.poses()),
                         {"Other.pose": {"pose.json": _sha("other")}})

    def test_a_card_the_colleague_deleted_comes_back_from_the_build(self):
        """The other side of the same rule: a shipped card is the BUILD's - one deleted here
        comes back while the build ships it (the window's Delete is a move to the trash)."""
        shutil.rmtree(self.poses("Shipped.pose"))
        install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Shipped.pose", "pose.json")), "new shipped")

    # ---- the pieces

    def test_keep_local_alone(self):
        old = os.path.join(self.tmp, "old")
        new = os.path.join(self.tmp, "new")
        _write(os.path.join(old, "A.pose", "pose.json"), "local a")
        _write(os.path.join(old, "B.pose", "pose.json"), "local b")
        _write(os.path.join(new, "B.pose", "pose.json"), "build b")
        kept = install.keep_local(old, new, {"B.pose": {"pose.json": _sha("build b")}})
        self.assertEqual(list(kept), ["A.pose/pose.json", "B (local).pose/pose.json"])
        self.assertEqual(_read(os.path.join(new, "A.pose", "pose.json")), "local a")
        self.assertEqual(_read(os.path.join(new, "B.pose", "pose.json")), "build b")
        self.assertEqual(_read(os.path.join(new, "B (local).pose", "pose.json")), "local b")
        self.assertTrue(os.path.isfile(os.path.join(old, "A.pose", "pose.json")))  # a copy

    def test_the_walk_sees_cards_folders_and_loose_files(self):
        root = os.path.join(self.tmp, "walk")
        _write(os.path.join(root, "A", "B.pose", "pose.json"), "b")
        _write(os.path.join(root, "A", "B.pose", "sub", "x.txt"), "x")
        _write(os.path.join(root, "note.txt"), "n")
        _write(os.path.join(root, install.SHIPPED), "{}")
        _write(os.path.join(root, "C.pose", "pose.json.part"), "half")
        _write(os.path.join(root, "_trash", "D.pose", "pose.json"), "d")
        cards, folders, files = install.poses_walk(root)
        self.assertEqual(cards, ["A/B.pose", "C.pose"])
        self.assertEqual(folders, ["A", "_trash", "_trash/D.pose"])
        self.assertEqual(files, ["_trash/D.pose/pose.json", "note.txt"])
        self.assertEqual(sorted(install.card_files(os.path.join(root, "A", "B.pose"))),
                         ["pose.json", "sub/x.txt"])
        self.assertEqual(install.card_files(os.path.join(root, "C.pose")), {})

    def test_a_broken_manifest_reads_as_none(self):
        root = os.path.join(self.tmp, "broken")
        self.assertIsNone(install.read_shipped(root))
        _write(os.path.join(root, install.SHIPPED), "not json")
        self.assertIsNone(install.read_shipped(root))
        _write(os.path.join(root, install.SHIPPED), json.dumps({"format": "other"}))
        self.assertIsNone(install.read_shipped(root))

    def test_valid_json_that_is_no_object_reads_as_no_manifest(self):
        # the scoped re-review: `[]` or `null` raised AttributeError out of the install
        root = os.path.join(self.tmp, "listy")
        for text in ("[]", "null", "3", '"x"'):
            _write(os.path.join(root, install.SHIPPED), text)
            self.assertIsNone(install.read_shipped(root), text)

    def test_explorer_s_own_files_do_not_make_a_shipped_card_local(self):
        # Thumbs.db / desktop.ini appear in a folder a colleague merely opened in Explorer:
        # the card is still the build's - renamed upstream, it does not come back
        first = self.build({"Fist.pose": {"pose.json": "fist"}})
        shutil.rmtree(self.dest)
        install.copy_payload(first, self.dest)
        _write(self.poses("Fist.pose", "Thumbs.db"), "explorer's")
        _write(self.poses("Fist.pose", "desktop.ini"), "[.ShellClassInfo]")
        second = self.build({"Punch.pose": {"pose.json": "fist"}})
        kept = install.copy_payload(second, self.dest)
        self.assertEqual(self.listing(), ["Punch.pose"])
        self.assertEqual(kept.dropped, ["Fist.pose"])
        self.assertEqual(install.card_files(os.path.join(first, "poses", "Fist.pose")),
                         {"pose.json": _sha("fist")})

    def test_a_failed_restore_keeps_the_old_poses_and_says_where(self):
        def boom(*args):
            raise OSError("disk full")
        saved = install.keep_local
        install.keep_local = boom
        try:
            kept = install.copy_payload(self.src, self.dest)
        finally:
            install.keep_local = saved
        left = [n for n in os.listdir(os.path.dirname(self.dest)) if n != "SkeldarAnim"]
        self.assertEqual(len(left), 1)
        aside = os.path.join(os.path.dirname(self.dest), left[0], "poses")
        self.assertEqual(_read(os.path.join(aside, "Mine.pose", "pose.json")), "mine")
        self.assertEqual(len(self.said), 1)
        self.assertIn("disk full", self.said[0])
        self.assertIn(aside.replace("\\", "/"), self.said[0])
        self.assertEqual(kept.aside, aside.replace("\\", "/"))
        #  the install itself went through
        self.assertEqual(_read(os.path.join(self.dest, "maya_tool.py")), "new tool")

    def test_a_failed_copy_still_puts_the_poses_back_and_drops_nothing(self):
        """Trap 113: a payload row the source does not hold raised after the rmtree. The local
        poses are back in the installed folder before the error goes on - and the old build's
        own card too: with no new build's poses, nothing reads as removed upstream."""
        install.payload = lambda: ("maya_tool.py", "missing.py", "poses")
        with self.assertRaises((IOError, OSError)):
            install.copy_payload(self.src, self.dest)
        self.assertEqual(_read(self.poses("Mine.pose", "pose.json")), "mine")
        self.assertEqual(_read(self.poses("Shipped.pose", "pose.json")), "old shipped")
        self.assertEqual(install.read_shipped(self.poses()),
                         {"Shipped.pose": {"pose.json": _sha("old shipped")}})
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), ["SkeldarAnim"])

    # ---- animation cards (2026-10-03): a `<Name>.anim` folder is one unit as a `.pose` is

    def anim(self, poses, rel, name, text):
        """An animation card `rel` under `poses`: its header (`anim.json`, named `name`), its
        frames and its preview sheet - `text` makes the three differ from another card's."""
        card = os.path.join(poses, *rel.split("/"))
        _write(os.path.join(card, "anim.json"), _anim_json(name, text))
        _write(os.path.join(card, "frames.json.gz"), "frames " + text)
        _write(os.path.join(card, "preview.jpg"), "sheet " + text)
        return card

    def test_a_local_animation_survives_whole(self):
        mine = self.anim(self.poses(), "Loco/Walk.anim", "Walk", "mine")
        before = install.card_files(mine)
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(install.card_files(self.poses("Loco", "Walk.anim")), before)
        self.assertEqual(len(before), 3)
        self.assertIn("Loco/Walk.anim", self.listing())
        self.assertTrue(set(kept) >= set("Loco/Walk.anim/" + name for name in before))
        self.assertEqual(kept.renamed, {})

    def test_an_animation_with_a_shipped_name_goes_beside_it(self):
        self.anim(self.poses(), "Walk.anim", "Walk", "mine")
        shipped = self.anim(os.path.join(self.src, "poses"), "Walk.anim", "Walk", "shipped")
        files = install.card_files(shipped)
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(install.card_files(self.poses("Walk.anim")), files)
        local = self.poses("Walk (local).anim")
        self.assertEqual(json.loads(_read(os.path.join(local, "anim.json")))["name"],
                         "Walk (local)")
        self.assertEqual(_read(os.path.join(local, "frames.json.gz")), "frames mine")
        self.assertEqual(_read(os.path.join(local, "preview.jpg")), "sheet mine")
        self.assertFalse(os.path.exists(os.path.join(local, "pose.json")))
        self.assertEqual(kept.renamed, {"Walk.anim": "Walk (local).anim"})

    def test_a_pose_and_an_animation_of_one_name_are_two_units(self):
        _write(self.poses("Walk.pose", "pose.json"), _card_json("Walk"))
        self.anim(os.path.join(self.src, "poses"), "Walk.anim", "Walk", "shipped")
        kept = install.copy_payload(self.src, self.dest)
        self.assertEqual(json.loads(_read(self.poses("Walk.pose", "pose.json")))["name"], "Walk")
        self.assertEqual(_read(self.poses("Walk.anim", "preview.jpg")), "sheet shipped")
        self.assertEqual(kept.renamed, {})
        self.assertIn("Walk.anim", self.listing())
        self.assertIn("Walk.pose", self.listing())

    def test_the_manifest_lists_animation_cards(self):
        poses = os.path.join(self.tmp, "manifest_poses")
        card = self.anim(poses, "Loco/Walk.anim", "Walk", "shipped")
        _write(os.path.join(poses, "Fist.pose", "pose.json"), "fist")
        cards = install.shipped_manifest(poses)["cards"]
        self.assertEqual(sorted(cards), ["Fist.pose", "Loco/Walk.anim"])
        self.assertEqual(sorted(cards["Loco/Walk.anim"]),
                         ["anim.json", "frames.json.gz", "preview.jpg"])
        self.assertEqual(cards["Loco/Walk.anim"], install.card_files(card))

    def test_a_shipped_animation_renamed_upstream_stays_gone(self):
        first = self.build({"Walk.anim": {"anim.json": "walk", "frames.json.gz": "f"}})
        shutil.rmtree(self.dest)
        install.copy_payload(first, self.dest)
        second = self.build({"Stroll.anim": {"anim.json": "walk", "frames.json.gz": "f"}})
        kept = install.copy_payload(second, self.dest)
        self.assertEqual(self.listing(), ["Stroll.anim"])
        self.assertEqual(kept.dropped, ["Walk.anim"])

    def test_a_local_name_is_free_of_both_types(self):
        folder = os.path.join(self.tmp, "free")
        _write(os.path.join(folder, "Walk (local).pose", "pose.json"), "a pose")
        self.assertEqual(install.free_card(folder, "Walk", card_suffix=".anim"),
                         "Walk (local) 2.anim")
        self.assertEqual(install.free_card(folder, "Run", card_suffix=".anim"),
                         "Run (local).anim")
        self.assertEqual(install.free_card(folder, "Run"), "Run (local).pose")
        self.assertEqual(install.CARD_SUFFIXES, (".pose", ".anim"))
        self.assertEqual(install.CARD_SUFFIX, ".pose")

    def test_the_install_dialog_names_a_renamed_card(self):
        kept = install.Kept(["Pose (local).pose/pose.json"])
        kept.renamed = {"Pose.pose": "Pose (local).pose"}
        self.assertIn("1 local pose card", install.poses_note(kept))
        self.assertEqual(install.poses_note(install.Kept()), "")
        self.assertEqual(install.poses_note(None), "")


class VersionRecord(unittest.TestCase):
    """`version.json`: which build an installed copy is, for Check update
    (2026-09-28). A build carries its own; a copy installed from the
    repository records its git commit and says it came from the source."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_version_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(self.src)
        os.makedirs(self.dest)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_update_section_ships(self):
        self.assertIn("maya_update.py", install.payload())
        self.assertIn("maya_update", install.module_names())

    def test_the_repository_answers_its_last_payload_commit(self):
        """Not HEAD: a CLAUDE.md-only commit is not a new build."""
        head = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--"]
            + list(install.payload()), cwd=PLUGIN,
            capture_output=True, text=True).stdout.strip()
        rec = install.git_record(PLUGIN)
        self.assertEqual(rec["commit"], head)
        self.assertEqual(rec["short"], head[:7])
        self.assertEqual(rec["log"][0][0], head)
        self.assertLessEqual(len(rec["log"]), install.LOG_LENGTH)
        self.assertTrue(rec["subject"])
        self.assertTrue(rec["branch"])
        self.assertIn("dirty", rec)

    def test_no_git_is_an_empty_record(self):
        self.assertEqual(install.git_record(self.src), {})

    def test_a_build_s_own_record_is_copied(self):
        with open(os.path.join(self.src, "version.json"), "w") as handle:
            json.dump({"commit": "c" * 40, "built": "then"}, handle)
        rec = install.write_version(self.src, self.dest)
        self.assertEqual(rec, {"commit": "c" * 40, "built": "then"})
        self.assertEqual(install.read_version(self.dest), rec)

    def test_a_source_without_a_record_says_where_it_came_from(self):
        rec = install.write_version(self.src, self.dest)
        self.assertEqual(rec["source"], self.src.replace("\\", "/"))
        self.assertNotIn("commit", rec)
        self.assertEqual(install.read_version(self.dest), rec)

    def test_the_repository_as_a_source_records_its_commit(self):
        rec = install.write_version(PLUGIN, self.dest)
        self.assertEqual(len(rec["commit"]), 40)
        self.assertEqual(rec["source"], PLUGIN.replace("\\", "/"))

    def test_no_record_reads_as_empty(self):
        self.assertEqual(install.read_version(self.dest), {})

    def test_a_broken_record_reads_as_empty(self):
        with open(os.path.join(self.dest, "version.json"), "w") as handle:
            handle.write("{not json")
        self.assertEqual(install.read_version(self.dest), {})

    def test_the_record_is_not_a_payload_row(self):
        """The source tree holds none; every payload row must exist there."""
        self.assertNotIn("version.json", install.payload())


class InstallOrder(unittest.TestCase):
    """A fresh install must not report «the previous version was loaded»
    (2026-09-28, seen on a Maya with nothing of ours): building the shelf
    loads skeldar_features, and a purge AFTER it dropped that very module
    and counted it. The purge runs first."""

    class FakeCmds(object):
        def __init__(self, app):
            self.app = app
            self.dialogs = []

        def internalVar(self, **kwargs):
            return self.app

        def confirmDialog(self, **kwargs):
            self.dialogs.append(kwargs.get("message", ""))

        hub_open = False
        poses_open = False

        def workspaceControl(self, name, **kwargs):
            return ((self.hub_open and name == install.HUB_CONTROL)
                    or (self.poses_open and name == install.POSELIB_CONTROL))

        def evalDeferred(self, call, **kwargs):
            self.deferred.append(call)
            self.__dict__.setdefault("deferred_flags", []).append(kwargs)

        batch = False

        def about(self, **kwargs):
            return self.batch

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_order_")
        self.order = []
        self.fake = self.FakeCmds(self.tmp + "/")
        self.fake.deferred = []
        self.saved = (install._cmds, install.copy_payload,
                      install.write_version, install._build_shelf,
                      install.purge_modules, install.register_startup)
        install._cmds = lambda: self.fake
        install.copy_payload = lambda src, dest: self.order.append("copy")
        install.write_version = lambda src, dest: self.order.append("version")
        install._build_shelf = lambda dest: self.order.append("shelf")
        self.purged = []
        install.purge_modules = lambda: self.order.append("purge") or \
            list(self.purged)
        #  the startup plug-in (2026-10-08): recorded, answering a note
        self.startup_note = ""
        self.startup_dests = []
        install.register_startup = lambda dest: (
            self.order.append("startup"), self.startup_dests.append(dest),
            self.startup_note)[-1]
        #  no edge panel standing unless a test says so (the real question
        #  asks the test process's QApplication)
        self.saved_edge = getattr(install, "_edge_standing", None)
        install._edge_standing = lambda: False

    def tearDown(self):
        (install._cmds, install.copy_payload, install.write_version,
         install._build_shelf, install.purge_modules,
         install.register_startup) = self.saved
        if self.saved_edge is None:
            install.__dict__.pop("_edge_standing", None)
        else:
            install._edge_standing = self.saved_edge
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_purge_comes_before_the_shelf_loads_the_flags(self):
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(self.order,
                         ["copy", "version", "purge", "shelf", "startup"])

    def test_the_startup_plugin_is_registered_from_the_installed_folder(self):
        """2026-10-08: after the copy and the shelf, AFTER the purge - the
        plug-in's reload must not stop a maya_hub the install is replacing
        (the old module would delete the edge panel under an Update press);
        the fresh start() leaves a standing panel to the install's rebuild."""
        dest = install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(self.startup_dests, [dest.replace("\\", "/")])

    def test_batch_registers_no_startup_plugin(self):
        self.fake.batch = True
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertNotIn("startup", self.order)

    def test_a_registration_that_failed_is_said_in_the_dialog(self):
        self.startup_note = "startup plug-in not registered: no luck"
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertIn("startup plug-in not registered: no luck",
                      self.fake.dialogs[0])

    def test_a_quiet_install_prints_it(self):
        self.startup_note = "startup plug-in not registered: no luck"
        said = []
        saved = install._say
        install._say = said.append
        try:
            install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        finally:
            install._say = saved
        self.assertEqual(self.fake.dialogs, [])
        self.assertTrue(any("not registered: no luck" in line
                            for line in said), said)

    def test_a_registered_plugin_adds_nothing_to_the_dialog(self):
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertNotIn("startup plug-in", self.fake.dialogs[0])

    def test_a_fresh_install_says_nothing_of_a_previous_version(self):
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertEqual(len(self.fake.dialogs), 1)
        self.assertNotIn("previous version", self.fake.dialogs[0])

    def test_the_flags_the_shelf_read_are_not_left_loaded(self):
        """The shelf read them from the SOURCE (for the one-file installer, a
        temp folder deleted a moment later); the next import must find the
        installed copy's."""
        sentinel = object()
        install._build_shelf = lambda dest: sys.modules.__setitem__(
            "skeldar_features", sentinel)
        saved = sys.modules.get("skeldar_features")
        try:
            install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
            self.assertIsNot(sys.modules.get("skeldar_features"), sentinel)
        finally:
            if saved is not None:
                sys.modules["skeldar_features"] = saved

    def test_a_real_update_says_so(self):
        self.purged = ["maya_hub", "maya_update"]
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertIn("previous version", self.fake.dialogs[0])
        self.assertIn("2 modules", self.fake.dialogs[0])


class RebuildsTheOpenHub(unittest.TestCase):
    """An install with the hub open used to leave it showing the OLD build: the modules were
    purged, the widgets stayed, and nothing rebuilt them until somebody pressed the shelf button
    (2026-09-28, the Orc D: «у меня нет возможности выбрать orc d» -- the dropdown was the one built
    before the install). The installer rebuilds it now, deferred like the updater's `_reopen` (an
    install run from a hub button must not delete the layout holding that button under itself)."""

    FakeCmds = InstallOrder.FakeCmds

    def setUp(self):
        InstallOrder.setUp(self)

    def tearDown(self):
        InstallOrder.tearDown(self)

    def test_an_open_hub_is_rebuilt_after_the_install(self):
        self.fake.hub_open = True
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(len(self.fake.deferred), 1)
        self.assertTrue(callable(self.fake.deferred[0]))

    def test_no_hub_no_rebuild(self):
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(self.fake.deferred, [])

    def test_the_dialog_says_the_hub_was_rebuilt(self):
        self.fake.hub_open = True
        self.purged = ["maya_hub", "maya_scenesetup.catalog"]
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertIn("hub is rebuilt", self.fake.dialogs[0])

    def test_an_edge_panel_is_rebuilt_too(self):
        """2026-10-08: the hub's other home - no workspaceControl stands, the
        edge panel's host window does; the fresh maya_hub.rebuild() knows
        which home it is."""
        install._edge_standing = lambda: True
        self.purged = ["maya_hub"]
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertEqual(len(self.fake.deferred), 1)
        self.assertEqual(self.fake.deferred_flags, [{"lowestPriority": True}])
        self.assertIn("hub is rebuilt", self.fake.dialogs[0])


class EdgeStanding(unittest.TestCase):
    """The installer asks Qt, by name, whether the hub's edge panel stands:
    nothing of ours is importable while it runs (it purged our modules)."""

    def setUp(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtWidgets
        self.QtWidgets = QtWidgets
        self.app = (QtWidgets.QApplication.instance()
                    or QtWidgets.QApplication([]))

    def test_the_host_window_by_its_name(self):
        from PySide6 import QtCore
        import shiboken6
        host = self.QtWidgets.QWidget(None, QtCore.Qt.Tool)
        host.setObjectName("skeldarAnimHubEdge")
        try:
            self.assertTrue(install._edge_standing())
        finally:
            shiboken6.delete(host)
        self.assertFalse(install._edge_standing())

    def test_another_window_is_not_it(self):
        import shiboken6
        other = self.QtWidgets.QWidget()
        other.setObjectName("skeldarAnimHubEdgeSensor")
        try:
            self.assertFalse(install._edge_standing())
        finally:
            shiboken6.delete(other)

    def test_the_name_is_maya_hubedge_s(self):
        import maya_hubedge
        self.assertEqual(install.HUB_EDGE, maya_hubedge.HOST)


class RebuildsTheOpenPoseLibrary(unittest.TestCase):
    """The Pose Library's window is a workspaceControl of its own (2026-10-02): an open one is
    rebuilt from the new modules after an install, deferred at the lowest priority as the hub."""

    FakeCmds = InstallOrder.FakeCmds

    def setUp(self):
        InstallOrder.setUp(self)
        self.calls = []
        self.saved_rebuilds = (install.rebuild_open_hub, install.rebuild_open_poselib)
        install.rebuild_open_hub = lambda dest: self.calls.append(("hub", dest))
        install.rebuild_open_poselib = lambda dest: self.calls.append(("poses", dest))

    def tearDown(self):
        install.rebuild_open_hub, install.rebuild_open_poselib = self.saved_rebuilds
        InstallOrder.tearDown(self)

    def run_deferred(self):
        for call in self.fake.deferred:
            call()

    def test_an_open_pose_library_is_rebuilt_after_the_install(self):
        self.fake.poses_open = True
        dest = install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(len(self.fake.deferred), 1)
        self.assertEqual(self.fake.deferred_flags, [{"lowestPriority": True}])
        self.run_deferred()
        self.assertEqual(self.calls, [("poses", dest.replace("\\", "/"))])

    def test_both_open_both_rebuilt(self):
        self.fake.hub_open = self.fake.poses_open = True
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.run_deferred()
        self.assertEqual(sorted(name for name, _dest in self.calls), ["hub", "poses"])

    def test_closed_nothing_scheduled(self):
        install.install(os.path.join(PLUGIN, "install.py"), quiet=True)
        self.assertEqual(self.fake.deferred, [])

    def test_the_dialog_says_the_pose_library_was_rebuilt(self):
        self.fake.poses_open = True
        self.purged = ["maya_poselib", "maya_poselib.window"]
        install.install(os.path.join(PLUGIN, "install.py"))
        self.assertIn("Pose Library is rebuilt", self.fake.dialogs[0])

    def test_the_installer_s_name_is_the_window_s(self):
        from maya_poselib import window
        self.assertEqual(install.POSELIB_CONTROL, window.CONTROL)


class RebuildOpenPoseLibrary(unittest.TestCase):
    """The deferred call: the FRESH maya_poselib.window rebuilds inside its standing control."""

    Window = None

    def setUp(self):
        self.path = list(sys.path)

        class Window(object):
            def __init__(self, open_):
                self.open_, self.rebuilt = open_, 0

            def is_open(self):
                return self.open_

            def rebuild(self):
                self.rebuilt += 1
        self.Window = Window

    def tearDown(self):
        sys.path[:] = self.path

    def test_the_fresh_window_rebuilds(self):
        window = self.Window(True)
        asked = []
        self.assertTrue(install.rebuild_open_poselib(
            "C:/prefs/SkeldarAnim", importer=lambda n: asked.append(n) or window))
        self.assertEqual((asked, window.rebuilt), (["maya_poselib.window"], 1))
        self.assertIn("C:/prefs/SkeldarAnim", sys.path)

    def test_a_window_closed_meanwhile_is_left_alone(self):
        window = self.Window(False)
        self.assertFalse(install.rebuild_open_poselib("C:/x", importer=lambda n: window))
        self.assertEqual(window.rebuilt, 0)

    def test_a_failing_rebuild_is_reported_not_raised(self):
        def boom(name):
            raise ImportError("no maya_poselib")
        self.assertFalse(install.rebuild_open_poselib("C:/x", importer=boom))


class RebuildOpenHub(unittest.TestCase):
    """What the deferred call does: the FRESH maya_hub, from the installed folder, rebuilds the
    accordion inside the standing control -- where it is docked survives."""

    class Hub(object):
        def __init__(self, open_):
            self.open_, self.rebuilt = open_, 0

        def is_open(self):
            return self.open_

        def rebuild(self):
            self.rebuilt += 1

    def setUp(self):
        self.path = list(sys.path)

    def tearDown(self):
        sys.path[:] = self.path

    def test_the_fresh_hub_rebuilds(self):
        hub = self.Hub(True)
        asked = []
        self.assertTrue(install.rebuild_open_hub("C:/prefs/SkeldarAnim",
                                                 importer=lambda n: asked.append(n) or hub))
        self.assertEqual((asked, hub.rebuilt), (["maya_hub"], 1))

    def test_the_installed_folder_is_importable_first(self):
        install.rebuild_open_hub("C:/prefs/SkeldarAnim", importer=lambda n: self.Hub(True))
        self.assertIn("C:/prefs/SkeldarAnim", sys.path)

    def test_a_hub_closed_meanwhile_is_left_alone(self):
        hub = self.Hub(False)
        self.assertFalse(install.rebuild_open_hub("C:/x", importer=lambda n: hub))
        self.assertEqual(hub.rebuilt, 0)

    def test_a_failing_rebuild_is_reported_not_raised(self):
        def boom(name):
            raise ImportError("no maya_hub")
        self.assertFalse(install.rebuild_open_hub("C:/x", importer=boom))


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
        for name in ("icons", "assets", "overrig", "poses"):
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


#  MAYA_PLUG_IN_PATH as a scratch-prefs Maya 2027.2 answered it (2026-10-08),
#  shortened past the two user folders
MEASURED_PATH = ("C:/tmp_sk13/appdir/2027/plug-ins;C:/tmp_sk13/appdir/plug-ins;"
                 "C:/Program Files/Autodesk/Maya2027/bin/plug-ins")


class StartupFolder(unittest.TestCase):
    """Where the startup plug-in goes (2026-10-08): a user folder on
    MAYA_PLUG_IN_PATH - Maya's autoload finds a plug-in there by name at the
    next start, and loads it without its untrusted-location dialog."""

    def test_the_version_folder_maya_put_on_the_path(self):
        self.assertEqual(install.startup_folder(
            MEASURED_PATH, "C:/tmp_sk13/appdir/", "2027"),
            "C:/tmp_sk13/appdir/2027/plug-ins")

    def test_slashes_and_case_do_not_matter(self):
        path = ("C:\\Users\\X\\Documents\\maya\\2027\\plug-ins\\;"
                "C:\\Users\\X\\Documents\\maya\\plug-ins")
        self.assertEqual(install.startup_folder(
            path, "c:/users/x/documents/maya", "2027"),
            "C:/Users/X/Documents/maya/2027/plug-ins")

    def test_another_user_folder_when_the_version_s_is_not_on_it(self):
        self.assertEqual(install.startup_folder(
            "C:/u/maya/plug-ins;C:/Program Files/x", "C:/u/maya/", "2027"),
            "C:/u/maya/plug-ins")

    def test_none_under_the_user_folder_is_none(self):
        self.assertEqual(install.startup_folder(
            "C:/Program Files/Autodesk/Maya2027/bin/plug-ins", "C:/u/maya/",
            "2027"), "")
        self.assertEqual(install.startup_folder("", "C:/u/maya/", "2027"), "")

    def test_a_folder_beside_the_user_folder_is_not_under_it(self):
        self.assertEqual(install.startup_folder(
            "C:/u/maya_old/2027/plug-ins", "C:/u/maya/", "2027"), "")


class MadeThisSession(unittest.TestCase):
    """Task 13b (2026-10-09): Maya trusts the user's plug-ins folder only
    when it stood at Maya's start - a load from it in the session that made
    it raised the modal «Untrusted Plugin Loading». Made this session = the
    installer's mark on `sys`, or a folder born after this process started.
    Pure."""

    def test_the_installer_s_mark_is_this_session(self):
        self.assertTrue(install.made_this_session(
            "C:/u/maya/2027/plug-ins", "C:/u/maya/2027/plug-ins", 10.0, 100.0))

    def test_the_mark_ignores_slashes_and_case(self):
        self.assertTrue(install.made_this_session(
            "C:\\U\\Maya\\2027\\plug-ins\\", "c:/u/maya/2027/plug-ins",
            None, None))

    def test_another_folder_s_mark_is_not_this_one(self):
        self.assertFalse(install.made_this_session(
            "C:/u/maya/2027/plug-ins", "C:/u/maya/plug-ins", 10.0, 100.0))

    def test_born_after_the_process_started_is_this_session(self):
        """Made by somebody else meanwhile (the animator, another tool):
        Maya did not see it at its start either."""
        self.assertTrue(install.made_this_session(
            "C:/u/maya/2027/plug-ins", None, 150.0, 100.0))

    def test_born_before_the_process_started_is_not(self):
        self.assertFalse(install.made_this_session(
            "C:/u/maya/2027/plug-ins", None, 50.0, 100.0))

    def test_without_the_times_only_the_mark_decides(self):
        self.assertFalse(install.made_this_session(
            "C:/u/maya/2027/plug-ins", None, None, 100.0))
        self.assertFalse(install.made_this_session(
            "C:/u/maya/2027/plug-ins", None, 150.0, None))

    def test_this_process_started_before_now(self):
        """The real call (Windows' GetProcessTimes): this test's own process
        started in the past, and not before the year 2026."""
        import time
        started = install.process_start()
        if os.name != "nt":
            self.skipTest("the process start is read on Windows only")
        self.assertIsNotNone(started)
        self.assertLess(started, time.time())
        self.assertGreater(started, 1767225600.0)            # 2026-01-01


class _StartupCmds(object):
    """maya.cmds as `register_startup` / `complete_startup` drive it."""

    def __init__(self, app):
        self.app = app
        self.calls = []
        self.loaded = False
        self.fail = ""
        self.optionvars = {}

    def internalVar(self, **kwargs):
        return self.app

    def about(self, **kwargs):
        return "2027"

    def pluginInfo(self, *args, **kwargs):
        if kwargs.get("query"):
            return self.loaded
        self.calls.append(("pluginInfo", args, kwargs))
        if self.fail == "autoload" and kwargs.get("autoload"):
            raise RuntimeError("autoload refused")

    def loadPlugin(self, path, **kwargs):
        self.calls.append(("loadPlugin", path, kwargs))
        if self.fail == "load":
            raise RuntimeError("load refused")
        if self.fail == "denied":
            return None
        self.loaded = True
        return [install.STARTUP_PLUGIN]

    def unloadPlugin(self, name, **kwargs):
        self.calls.append(("unloadPlugin", name, kwargs))
        self.loaded = False

    def optionVar(self, **kwargs):
        if "exists" in kwargs:
            return kwargs["exists"] in self.optionvars
        if "query" in kwargs:
            return self.optionvars.get(kwargs["query"], 0)
        if "remove" in kwargs:
            self.calls.append(("optionVar", "remove", kwargs["remove"]))
            self.optionvars.pop(kwargs["remove"], None)
            return None
        name, value = kwargs["intValue"]
        self.calls.append(("optionVar", name, value))
        self.optionvars[name] = value
        return None

    def savePrefs(self, **kwargs):
        self.calls.append(("savePrefs", kwargs))

    def loads(self):
        return [c for c in self.calls if c[0] == "loadPlugin"]


class _StartupFolder(unittest.TestCase):
    """A scratch userAppDir with an installed SkeldarAnim holding the plug-in,
    and the installer's `sys` mark kept apart from the real one."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_startup_")
        self.app = self.tmp.replace("\\", "/") + "/appdir/"
        self.dest = os.path.join(self.tmp, "scripts", "SkeldarAnim")
        os.makedirs(os.path.join(self.dest, "plug-ins"))
        with open(os.path.join(self.dest, "plug-ins",
                               install.STARTUP_PLUGIN + ".py"), "w") as h:
            h.write("# the plug-in\n")
        self.path = self.app + "2027/plug-ins;" + self.app + "plug-ins"
        self.folder = self.app + "2027/plug-ins"
        self.target = self.folder + "/" + install.STARTUP_PLUGIN + ".py"
        self.fake = _StartupCmds(self.app)
        self.saved_mark = getattr(sys, install.STARTUP_MADE_MARK, None)
        if hasattr(sys, install.STARTUP_MADE_MARK):
            delattr(sys, install.STARTUP_MADE_MARK)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self.saved_mark is None:
            if hasattr(sys, install.STARTUP_MADE_MARK):
                delattr(sys, install.STARTUP_MADE_MARK)
        else:
            setattr(sys, install.STARTUP_MADE_MARK, self.saved_mark)

    def existed_at_start(self):
        """The user's plug-ins folder stood when this "Maya session" began:
        made here, and the session said to have started an hour later."""
        os.makedirs(self.folder)
        return time_now() + 3600.0

    def made_now(self):
        """This "session" started an hour ago: a folder made now is newer."""
        return time_now() - 3600.0


def time_now():
    import time
    return time.time()


class RegisterStartup(_StartupFolder):
    """`register_startup(dest)` copies the plug-in from the installed folder
    into the user's plug-ins folder, loads it by its full path, sets it to
    autoload and saves Maya's plug-in prefs (2026-10-08) - when that folder
    stood at Maya's start. One made in this session is not trusted by Maya
    yet (its modal security dialog, measured 2026-10-09): copied, not
    loaded, marked pending for the next session's first hub (Task 13b, the
    animator: «Без окна, на сессию позже»). Never raises: a hub without its
    edge panel at startup is no reason to fail an install."""

    def register(self, started):
        return install.register_startup(self.dest, cmds=self.fake,
                                        plug_in_path=self.path,
                                        session_start=started)

    def test_copied_loaded_by_path_autoloaded_and_saved(self):
        self.assertEqual(self.register(self.existed_at_start()), "")
        with open(self.target) as h:
            self.assertEqual(h.read(), "# the plug-in\n")
        self.assertEqual(self.fake.calls, [
            ("loadPlugin", self.target, {"quiet": True}),
            ("pluginInfo", (install.STARTUP_PLUGIN,),
             {"edit": True, "autoload": True}),
            ("pluginInfo", (), {"savePluginPrefs": True})])
        self.assertNotIn(install.STARTUP_PENDING, self.fake.optionvars)

    def test_a_folder_made_now_is_copied_not_loaded_and_pending(self):
        note = self.register(self.made_now())
        self.assertTrue(os.path.isfile(self.target))         # the folder made
        with open(self.target) as h:
            self.assertEqual(h.read(), "# the plug-in\n")
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual([c for c in self.fake.calls if c[0] == "pluginInfo"],
                         [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)
        self.assertIn("next", note)
        self.assertIn("hub", note)
        self.assertNotIn("not registered", note)             # no failure

    def test_the_pending_mark_is_saved_at_once(self):
        """A Maya that crashes (or is killed) before it exits writes no
        prefs: the mark would be lost with them."""
        self.register(self.made_now())
        self.assertIn(("savePrefs", {"general": True}), self.fake.calls)
        self.assertLess(
            self.fake.calls.index(("optionVar", install.STARTUP_PENDING, 1)),
            self.fake.calls.index(("savePrefs", {"general": True})))

    def test_the_folder_made_is_marked_on_sys(self):
        self.register(self.made_now())
        self.assertEqual(getattr(sys, install.STARTUP_MADE_MARK),
                         self.folder)

    def test_a_second_install_this_session_still_does_not_load(self):
        """The mark on `sys` survives the purge and any module name the
        installer is loaded under (the Update card's, the one-file
        installer's) - and the folder exists by now. Even a "session" said
        to have started later than the folder was born."""
        self.register(self.made_now())
        with open(os.path.join(self.dest, "plug-ins",
                               install.STARTUP_PLUGIN + ".py"), "w") as h:
            h.write("# the new one\n")
        note = self.register(time_now() + 3600.0)
        with open(self.target) as h:
            self.assertEqual(h.read(), "# the new one\n")    # replaced
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)
        self.assertIn("next", note)

    def test_a_folder_somebody_made_this_session_is_not_loaded_either(self):
        """No mark of ours - born after this process started."""
        os.makedirs(self.folder)
        self.register(self.made_now())
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_a_registration_clears_a_pending_mark(self):
        """A re-install before the next session's hub opened."""
        self.fake.optionvars[install.STARTUP_PENDING] = 1
        self.assertEqual(self.register(self.existed_at_start()), "")
        self.assertNotIn(install.STARTUP_PENDING, self.fake.optionvars)
        self.assertIn(("savePrefs", {"general": True}), self.fake.calls)

    def test_no_pending_mark_no_prefs_saved(self):
        """An ordinary re-install writes the plug-in prefs, not the rest."""
        self.register(self.existed_at_start())
        self.assertNotIn("savePrefs", [c[0] for c in self.fake.calls])

    def test_a_loaded_plugin_is_unloaded_first(self):
        """Its uninitializePlugin stops a hub still imported (after the
        install's purge there is none); the load runs the new copy."""
        self.fake.loaded = True
        self.register(self.existed_at_start())
        self.assertEqual(self.fake.calls[0],
                         ("unloadPlugin", install.STARTUP_PLUGIN,
                          {"force": True}))
        self.assertEqual(self.fake.calls[1][0], "loadPlugin")

    def test_a_second_install_replaces_the_copy(self):
        started = self.existed_at_start()
        self.register(started)
        with open(os.path.join(self.dest, "plug-ins",
                               install.STARTUP_PLUGIN + ".py"), "w") as h:
            h.write("# the new one\n")
        self.register(started)
        with open(self.target) as h:
            self.assertEqual(h.read(), "# the new one\n")

    def test_a_load_that_fails_is_a_note(self):
        self.fake.fail = "load"
        note = self.register(self.existed_at_start())
        self.assertIn("startup plug-in not registered", note)
        self.assertIn("load refused", note)

    def test_a_load_maya_denied_is_a_note_and_no_autoload(self):
        """A plug-in Maya's untrusted-location dialog was answered Deny for
        came back None, no error (measured 2026-10-08): said, nothing set."""
        self.fake.fail = "denied"
        note = self.register(self.existed_at_start())
        self.assertIn("startup plug-in not registered", note)
        self.assertIn("did not load", note)
        self.assertEqual([c for c in self.fake.calls if c[0] == "pluginInfo"],
                         [])

    def test_an_autoload_that_fails_is_a_note(self):
        self.fake.fail = "autoload"
        note = self.register(self.existed_at_start())
        self.assertIn("autoload refused", note)

    def test_no_user_plugin_folder_on_the_path_loads_nothing(self):
        self.path = "C:/Program Files/Autodesk/Maya2027/bin/plug-ins"
        note = self.register(self.existed_at_start())
        self.assertIn("MAYA_PLUG_IN_PATH", note)
        self.assertEqual(self.fake.calls, [])

    def test_a_missing_plugin_file_is_a_note(self):
        os.remove(os.path.join(self.dest, "plug-ins",
                               install.STARTUP_PLUGIN + ".py"))
        note = self.register(self.existed_at_start())
        self.assertIn("startup plug-in not registered", note)
        self.assertEqual(self.fake.loads(), [])

    def test_the_path_defaults_to_maya_s(self):
        started = self.existed_at_start()
        saved = os.environ.get("MAYA_PLUG_IN_PATH")
        os.environ["MAYA_PLUG_IN_PATH"] = self.path
        try:
            self.assertEqual(install.register_startup(
                self.dest, cmds=self.fake, session_start=started), "")
        finally:
            if saved is None:
                os.environ.pop("MAYA_PLUG_IN_PATH", None)
            else:
                os.environ["MAYA_PLUG_IN_PATH"] = saved
        self.assertTrue(os.path.isfile(self.target))

    def test_the_session_start_defaults_to_this_process_s(self):
        """No `session_start`: the real process start - and the test's
        folder, made just now, is newer than this process."""
        if install.process_start() is None:
            self.skipTest("the process start is read on Windows only")
        os.makedirs(self.folder)
        install.register_startup(self.dest, cmds=self.fake,
                                 plug_in_path=self.path)
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_the_name_is_the_plugin_file_s(self):
        self.assertTrue(os.path.isfile(os.path.join(
            PLUGIN, "plug-ins", install.STARTUP_PLUGIN + ".py")))


class CompleteStartup(_StartupFolder):
    """`complete_startup()` (Task 13b, 2026-10-09): a registration the
    install left pending finished - silently - the first time the hub is
    built or shown in a LATER session, when Maya trusts the folder: loaded by
    its full path, autoload, the plug-in prefs saved, the mark cleared. None
    when there is nothing to do now; "" when registered; a note when it
    failed (the mark stays: the next hub tries again)."""

    def setUp(self):
        _StartupFolder.setUp(self)
        os.makedirs(self.folder)
        shutil.copyfile(os.path.join(self.dest, "plug-ins",
                                     install.STARTUP_PLUGIN + ".py"),
                        self.target)
        self.fake.optionvars[install.STARTUP_PENDING] = 1
        self.later = time_now() + 3600.0     # this session began after the copy

    def complete(self, started=None):
        return install.complete_startup(
            cmds=self.fake, plug_in_path=self.path,
            session_start=self.later if started is None else started)

    def test_loaded_autoloaded_saved_and_the_mark_cleared(self):
        self.assertEqual(self.complete(), "")
        self.assertEqual(self.fake.calls[:3], [
            ("loadPlugin", self.target, {"quiet": True}),
            ("pluginInfo", (install.STARTUP_PLUGIN,),
             {"edit": True, "autoload": True}),
            ("pluginInfo", (), {"savePluginPrefs": True})])
        self.assertNotIn(install.STARTUP_PENDING, self.fake.optionvars)
        self.assertEqual(self.fake.calls[-1], ("savePrefs", {"general": True}))

    def test_nothing_pending_nothing_done(self):
        del self.fake.optionvars[install.STARTUP_PENDING]
        self.assertIsNone(self.complete())
        self.assertEqual(self.fake.calls, [])

    def test_a_pending_mark_of_zero_is_nothing(self):
        self.fake.optionvars[install.STARTUP_PENDING] = 0
        self.assertIsNone(self.complete())
        self.assertEqual(self.fake.calls, [])

    def test_not_in_the_session_that_made_the_folder(self):
        """The install's own session: the second hub open there would raise
        the very dialog the install stepped around."""
        setattr(sys, install.STARTUP_MADE_MARK, self.folder)
        self.assertIsNone(self.complete())
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_not_when_the_folder_is_newer_than_this_session(self):
        self.assertIsNone(self.complete(started=time_now() - 3600.0))
        self.assertEqual(self.fake.loads(), [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_not_when_the_copy_is_gone(self):
        os.remove(self.target)
        self.assertIsNone(self.complete())
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_a_failed_load_keeps_the_mark(self):
        self.fake.fail = "load"
        note = self.complete()
        self.assertIn("startup plug-in not registered", note)
        self.assertIn("load refused", note)
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_a_denied_load_keeps_the_mark_and_sets_no_autoload(self):
        self.fake.fail = "denied"
        note = self.complete()
        self.assertIn("did not load", note)
        self.assertEqual([c for c in self.fake.calls if c[0] == "pluginInfo"],
                         [])
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_a_failed_autoload_keeps_the_mark(self):
        self.fake.fail = "autoload"
        self.assertIn("autoload refused", self.complete())
        self.assertEqual(self.fake.optionvars[install.STARTUP_PENDING], 1)

    def test_already_loaded_is_not_loaded_again(self):
        """Loaded by hand in the Plug-in Manager meanwhile: autoload set."""
        self.fake.loaded = True
        self.assertEqual(self.complete(), "")
        self.assertEqual(self.fake.loads(), [])
        self.assertNotIn(install.STARTUP_PENDING, self.fake.optionvars)
        self.assertIn(("pluginInfo", (install.STARTUP_PLUGIN,),
                       {"edit": True, "autoload": True}), self.fake.calls)

    def test_never_raises(self):
        class Broken(_StartupCmds):
            def internalVar(self, **kwargs):
                raise RuntimeError("no user folder")
        self.fake = Broken(self.app)
        self.fake.optionvars[install.STARTUP_PENDING] = 1
        self.assertIn("no user folder", self.complete())

    def test_the_pending_name(self):
        self.assertEqual(install.STARTUP_PENDING, "skeldarAnimStartupPending")


if __name__ == "__main__":
    unittest.main()

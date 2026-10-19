import os
import shutil
import sys
import tempfile
import types
import unittest
from collections import namedtuple

from maya_skillbar import look, run, sources

Entry = namedtuple("Entry", "key label model kind")
Weapon = namedtuple("Weapon", "key label")
Section = namedtuple("Section", "key label icon")
Card = namedtuple("Card", "path folder name")


class Fakes(object):
    """Every module run.py / sources.py asks for, recording what was done."""

    def __init__(self, root):
        self.done = []
        self.root = root
        fakes = self
        manny = Entry("Manny_Rig", "Manny [rig]", "Manny", "rig")
        self.catalog = types.SimpleNamespace(
            CHARACTERS=[manny, Entry("Manny_Skeleton", "Manny UE5 [skeleton]", "Manny", "skeleton")],
            WEAPONS=[Weapon("Spear_01", "Spear 01")],
            character_for=lambda m, k: manny if (m, k) == ("Manny", "rig") else None,
            by_key=lambda k: Weapon("Spear_01", "Spear 01") if k == "Spear_01" else None,
            portrait_path=lambda m: root + "/%s.png" % m,
            asset_path=lambda name: root + "/" + name)
        self.character = types.SimpleNamespace(
            add_character=lambda e: fakes.done.append(("add", e.key)) or "Manny added")
        self.scene_window = types.SimpleNamespace(
            refresh=lambda: None,
            select_weapon=lambda k: fakes.done.append(("pick", k)),
            add_weapon=lambda: fakes.done.append(("equip",)))
        self.radial = types.SimpleNamespace(
            run_item=lambda item, point: fakes.done.append(("radial", item, point)) or "ran",
            item_label=lambda item: {"cmd:tools.aim": "Aim", "section:tools": "Tools"}.get(item, ""),
            item_icon=lambda item: "tool",
            waiting=lambda key: key == "tools.aim",
            functions=lambda: [("Tools", [("tools.aim", "Aim"), ("tools.knot", "Knot")])])
        self.hotkeys = types.SimpleNamespace(row=lambda key: None if key == "gone" else (key,))
        self.mel = types.SimpleNamespace(eval=lambda code: fakes.done.append(("mel", code)) or "")

        class Scene(object):
            def library(self):
                return root

            def option(self, name, default=None):
                return default

            def apply(self, path, mirror, options=None, only=False):
                fakes.done.append(("apply", path, mirror, options))
                return "posed"

        self.poselib_window = types.SimpleNamespace(Scene=Scene,
                                                   remembered_options=lambda read: {"mode": "x"})
        self.poselib_store = types.SimpleNamespace(
            cards=lambda r: ([Card(root + "/A/Fist.pose", "A", "Fist"),
                              Card(root + "/Walk.anim", "", "Walk")], []))
        self.hub = types.SimpleNamespace(SECTIONS=[Section("tools", "Tools", "tool")])
        self.cmds = types.SimpleNamespace(
            runTimeCommand=lambda query, commandArray: ["SetKey", "GraphEditor", "Zebra"])

    def mod(self, name):
        return {"maya_scenesetup.catalog": self.catalog,
                "maya_scenesetup.character": self.character,
                "maya_scenesetup.window": self.scene_window,
                "maya_radial": self.radial, "maya_hotkeys": self.hotkeys,
                "maya.mel": self.mel, "maya.cmds": self.cmds,
                "maya_poselib.window": self.poselib_window,
                "maya_poselib.store": self.poselib_store, "maya_hub": self.hub}[name]


class OffTheBarFakes(Fakes):
    """Fakes for a drag off the bar: a viewport on the right half, the hub on the left."""

    def __init__(self, root):
        Fakes.__init__(self, root)
        fakes = self

        class Viewport(object):
            @staticmethod
            def at(gx, gy):
                return (object(), (gx, gy)) if gx >= 500 else (None, None)

        class Inventory(object):
            def snapshot(self):
                return ["snap"]

            def target(self, gx, gy, snap):
                if gy < 100:
                    return {"kind": "hand", "root": "|root", "side": "R", "text": "into the right hand"}
                return {"kind": "floor", "root": "|root", "point": (gx, 0, gy), "heading": (1, 0, 0)}

            def to_hand(self, root, side, entry):
                fakes.done.append(("hand", root, side, entry.key))
                return "in hand"

            def to_floor(self, root, entry, point, heading, side=None):
                fakes.done.append(("floor", root, entry.key, point))
                return "on floor"

        self.extra = {"maya_scenesetup.droptarget": types.SimpleNamespace(Viewport=Viewport),
                      "maya_hubqt": types.SimpleNamespace(on_hub=lambda gx, gy: gx < 100),
                      "maya_inventory": types.SimpleNamespace(Scene=Inventory)}

    def mod(self, name):
        if name in self.extra:
            return self.extra[name]
        return Fakes.mod(self, name)


class Base(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp().replace("\\", "/")
        self.fakes = Fakes(self.root)
        self._mods = run._mod, sources._mod
        run._mod = sources._mod = self.fakes.mod

    def tearDown(self):
        run._mod, sources._mod = self._mods
        shutil.rmtree(self.root, ignore_errors=True)


class Running(Base):

    def test_a_section_and_a_tool_go_the_radial_menu_s_road(self):
        self.assertEqual(run.run({"kind": "section", "key": "tools"}, (5, 6)), "ran")
        run.run({"kind": "cmd", "key": "tools.aim"}, (1, 2))
        self.assertEqual(self.fakes.done, [("radial", "section:tools", (5, 6)),
                                           ("radial", "cmd:tools.aim", (1, 2))])

    def test_a_tool_gone_says_so(self):
        self.assertIn("No tool", run.run({"kind": "cmd", "key": "gone"}))
        self.assertEqual(self.fakes.done, [])

    def test_a_character_is_added(self):
        self.assertEqual(run.run({"kind": "character", "model": "Manny", "char": "rig"}), "Manny added")
        self.assertEqual(self.fakes.done, [("add", "Manny_Rig")])
        self.assertIn("No Orc", run.run({"kind": "character", "model": "Orc", "char": "rig"}))

    def test_a_card_is_applied_with_the_remembered_options(self):
        os.makedirs(self.root + "/A/Fist.pose")
        self.assertEqual(run.run({"kind": "card", "path": "A/Fist.pose"}), "posed")
        self.assertEqual(self.fakes.done, [("apply", self.root + "/A/Fist.pose", False, {"mode": "x"})])
        self.assertIn("gone", run.run({"kind": "card", "path": "B/Gone.pose"}))

    def test_a_weapon_is_equipped(self):
        self.assertEqual(run.run({"kind": "weapon", "key": "Spear_01"}), "Equip Spear 01")
        self.assertEqual(self.fakes.done, [("pick", "Spear_01"), ("equip",)])

    def test_maya_and_scripts(self):
        run.run({"kind": "maya", "command": "GraphEditor"})
        run.run({"kind": "script", "lang": "mel", "code": "print 1;"})
        self.assertEqual(self.fakes.done, [("mel", "GraphEditor"), ("mel", "print 1;")])
        run.run({"kind": "shelf", "lang": "python", "code": "import sys; sys._skillbar_test = 7"})
        self.assertEqual(getattr(sys, "_skillbar_test", None), 7)
        del sys._skillbar_test

    def test_an_empty_or_broken_item(self):
        self.assertEqual(run.run(None), "Empty cell")
        self.assertEqual(run.run({"kind": "cmd"}), "Empty cell")


class Texts(Base):

    def test_labels(self):
        self.assertEqual(run.label({"kind": "cmd", "key": "tools.aim"}), "Aim")
        self.assertEqual(run.label({"kind": "cmd", "key": "tools.aim", "label": "Mine"}), "Mine")
        self.assertEqual(run.label({"kind": "character", "model": "Manny", "char": "rig"}),
                         "Manny [rig]")
        self.assertEqual(run.label({"kind": "card", "path": "A/Fist.pose"}), "Fist")
        self.assertEqual(run.label({"kind": "weapon", "key": "Spear_01"}), "Spear 01")
        self.assertEqual(run.label({"kind": "script", "lang": "python", "code": "# hi\nx=1"}), "hi")

    def test_short_names(self):
        self.assertEqual(run.short({"kind": "cmd", "key": "tools.knot_offset"}), "Offset")
        self.assertEqual(run.short({"kind": "cmd", "key": "tools.aim"}), "Aim")
        self.assertEqual(run.short({"kind": "character", "model": "Manny", "char": "rig"}), "")
        self.assertEqual(run.short({"kind": "maya", "command": "FrameSelectedWithoutChildren"}),
                         "FrameSele")
        self.assertEqual(run.short({"kind": "cmd", "key": "x", "label": "Mine"}), "Mine")

    def test_tags(self):
        self.assertEqual(run.tag({"kind": "character", "model": "M", "char": "skeleton"}), "skel")
        self.assertEqual(run.tag({"kind": "card", "path": "Walk.anim"}), "anim")
        self.assertEqual(run.tag({"kind": "script", "lang": "mel", "code": "x"}), "mel")
        self.assertEqual(run.tag({"kind": "cmd", "key": "x"}), "")

    def test_pictures(self):
        self.assertEqual(run.picture({"kind": "cmd", "key": "tools.aim"}), ("icon", "target"))
        self.assertEqual(run.picture({"kind": "cmd", "key": "anim.other"}), ("icon", "tool"))
        self.assertEqual(run.picture({"kind": "character", "model": "Manny", "char": "rig"})[0], "text")
        open(self.root + "/Manny.png", "w").close()
        self.assertEqual(run.picture({"kind": "character", "model": "Manny", "char": "rig"}),
                         ("image", self.root + "/Manny.png"))
        self.assertEqual(run.picture({"kind": "maya", "command": "GraphEditor"}), ("text", "Gr"))
        self.assertEqual(run.picture({"kind": "shelf", "lang": "mel", "code": "x", "image": "a.png"}),
                         ("image", ":/a.png"))

    def test_waiting_and_relative_cards(self):
        self.assertTrue(run.waiting({"kind": "cmd", "key": "tools.aim"}))
        self.assertFalse(run.waiting({"kind": "cmd", "key": "tools.knot"}))
        self.assertEqual(run.relative_card(self.root + "/A/Fist.pose"), "A/Fist.pose")
        self.assertEqual(run.relative_card("D:/x/Y.pose"), "D:/x/Y.pose")


class Sources(Base):

    def test_categories(self):
        found = sources.entries("All")
        cats = set(c for c, _i, _l in found)
        self.assertTrue({"Sections", "Tools", "Characters", "Poses", "Weapons", "Maya"} <= cats)
        for _c, item, _l in found:
            self.assertTrue(look.valid_item(item), item)
        poses = sources.entries("Poses")
        self.assertEqual([i["path"] for _c, i, _l in poses], ["A/Fist.pose", "Walk.anim"])
        self.assertEqual([l for _c, _i, l in poses], ["A / Fist", "Walk"])

    def test_maya_lists_the_animation_ones_and_searches_every_one(self):
        self.assertEqual([l for _c, _i, l in sources.entries("Maya")], ["SetKey", "GraphEditor"])
        self.assertEqual([l for _c, _i, l in sources.entries("Maya", "zeb")], ["Zebra"])

    def test_search_and_a_failing_category(self):
        self.fakes.hub = None          # Sections now raises: the others stand
        found = sources.entries("All", "aim")
        self.assertEqual([l for _c, _i, l in found], ["Aim"])


class OffTheBar(unittest.TestCase):
    """Any skill dragged off the bar into a viewport (2026-10-19)."""

    def setUp(self):
        self.root = tempfile.mkdtemp().replace("\\", "/")
        self.fakes = OffTheBarFakes(self.root)
        self._mod = run._mod
        run._mod = self.fakes.mod

    def tearDown(self):
        run._mod = self._mod
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_tool_dropped_on_a_viewport_runs_there(self):
        drag = run.SceneDrag({"kind": "cmd", "key": "tools.aim"})
        self.assertTrue(drag.active())
        self.assertEqual(drag.caption(800, 300), ("Aim · run here", True))
        said = []
        self.assertIn("running", drag.drop(800, 300, say=said.append))
        self.assertIn(("radial", "cmd:tools.aim", (800, 300)), self.fakes.done)
        self.assertEqual(said, ["ran"])

    def test_off_a_viewport_or_on_the_hub_nothing_runs(self):
        drag = run.SceneDrag({"kind": "section", "key": "tools"})
        self.assertFalse(drag.caption(300, 300)[1])
        self.assertEqual(drag.drop(300, 300), "")
        self.assertFalse(drag.caption(50, 300)[1])
        self.assertEqual(drag.drop(50, 300), "")
        self.assertEqual(self.fakes.done, [])

    def test_a_maya_command_and_a_script_run(self):
        run.SceneDrag({"kind": "maya", "command": "GraphEditor"}).drop(900, 200)
        self.assertIn(("mel", "GraphEditor"), self.fakes.done)

    def test_a_weapon_goes_into_the_hand_or_onto_the_floor(self):
        drag = run.SceneDrag({"kind": "weapon", "key": "Spear_01"})
        self.assertEqual(drag.caption(800, 50), ("into the right hand", True))
        drag.drop(800, 50)
        self.assertIn(("hand", "|root", "R", "Spear_01"), self.fakes.done)
        drag.drop(800, 300)
        self.assertIn(("floor", "|root", "Spear_01", (800, 0, 300)), self.fakes.done)

    def test_an_empty_cell_is_no_drag(self):
        self.assertFalse(run.SceneDrag(None).active())



if __name__ == "__main__":
    unittest.main()

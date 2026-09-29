"""The weapon inventory window, offscreen (2026-09-29): it builds and paints
ink, the grid holds the catalog, the paper doll shows the hands, and a drop
does what the spec's table says - on a fake scene, so no Maya scene is
touched. The viewport half is verify_inventory_live.py's.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import os
import unittest

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_inventory as inv
import maya_invlook as look
from maya_scenesetup import catalog
from maya_scenesetup.equip import Holding

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")
ROOT = "|Manny_Rig:root"


class FakeScene(object):
    """What the window asks the scene and what it tells it, recorded."""

    def __init__(self):
        self.log = []
        self.hold = {"R": Holding("hand", "|w|LongSwordMesh", "LongSword_02",
                                  "Long Sword 02"),
                     "L": Holding(None, None, "", "")}
        self.aim = dict(kind="hand", root=ROOT, side="L",
                        text="Manny_Rig · left hand")
        self.watched = []

    def scale(self):
        return 1.0

    def current(self):
        return ROOT

    def label(self, root):
        return "Manny_Rig"

    def holdings(self, root):
        return dict(self.hold)

    def snapshot(self):
        return ["snap"]

    def target(self, gx, gy, snap, freed=None):
        self.log.append(("target", freed))
        return self.aim

    def to_hand(self, root, side, entry):
        self.log.append(("to_hand", root, side, entry.key))
        return "into"

    def to_floor(self, root, entry, point, heading, side=None):
        self.log.append(("to_floor", root, entry.key, side))
        return "floor"

    def take_off(self, root, side):
        self.log.append(("take_off", root, side))
        return "off"

    def move(self, root, side, target):
        self.log.append(("move", root, side, target[0]))
        return "moved"

    def watch(self, callback):
        self.watched.append(callback)
        return ["job"]

    def unwatch(self, jobs):
        self.log.append(("unwatch", jobs))

    def echo(self, text):
        pass

    def remembered_position(self):
        return None

    def remember_position(self, x, y):
        pass


@unittest.skipIf(QT is None, "no Qt")
class Window(unittest.TestCase):

    def setUp(self):
        self.app = (QT.QtWidgets.QApplication.instance()
                    or QT.QtWidgets.QApplication([]))
        self.scene = FakeScene()
        self.win = inv.make_window(self.scene, parent=None, remember=False)
        self.win.move(3000, 3000)             # well away from 500, 500
        self.addCleanup(self.win.deleteLater)
        self.scene.log = [entry for entry in self.scene.log
                          if entry[0] != "target"]

    def global_of(self, name, dx=5, dy=5):
        x, y = self.win.rects[name][:2]
        point = self.win.mapToGlobal(QT.QtCore.QPoint(int(x) + dx, int(y) + dy))
        return point.x(), point.y()

    def test_it_paints_ink(self):
        image = QT.QtGui.QImage(self.win.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.render(image)
        inked = sum(1 for x in range(0, image.width(), 5)
                    for y in range(0, image.height(), 5)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 100)

    def test_the_grid_holds_every_catalog_row(self):
        self.assertEqual(set(self.win.placements),
                         set(e.key for e in catalog.WEAPONS))

    def test_it_is_the_layouts_size_and_named(self):
        _x, _y, w, h = look.layout()["window"]
        self.assertEqual((self.win.width(), self.win.height()), (w, h))
        self.assertEqual(self.win.objectName(), inv.OBJECT_NAME)

    def test_it_watches_the_scene_and_stops(self):
        self.assertEqual(len(self.scene.watched), 1)
        self.win.close()
        self.assertIn(("unwatch", ["job"]), self.scene.log)

    def test_grid_onto_a_hand_in_the_viewport(self):
        self.win.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.scene.log[-1], ("to_hand", ROOT, "L", "Dagger_01"))

    def test_grid_onto_the_floor(self):
        self.scene.aim = dict(kind="floor", root="|root", side="L",
                              point=(1, 0, 2), heading=(1, 0, 0), text="floor")
        self.win.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual(self.scene.log[-1], ("to_floor", "|root", "Spear_01", "L"))

    def test_grid_onto_a_slot(self):
        self.win.drop_at(*self.global_of("slot_L"), source=("grid", "Dagger_01"))
        self.assertEqual(self.scene.log, [("to_hand", ROOT, "L", "Dagger_01")])

    def test_slot_onto_the_grid_takes_it_off(self):
        self.win.drop_at(*self.global_of("grid"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [("take_off", ROOT, "R")])

    def test_slot_onto_the_other_slot_moves_it(self):
        self.win.drop_at(*self.global_of("slot_L"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [("move", ROOT, "R", "hand")])

    def test_slot_onto_its_own_slot_does_nothing(self):
        self.win.drop_at(*self.global_of("slot_R"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [])

    def test_slot_out_to_the_viewport_moves_it_and_frees_its_side(self):
        self.win.drop_at(500, 500, ("slot", "R"))
        self.assertEqual(self.scene.log, [("target", (ROOT, "R")),
                                          ("move", ROOT, "R", "hand")])

    def test_no_target_does_nothing_and_says_why(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.win.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual([e for e in self.scene.log if e[0] != "target"], [])
        self.assertIn("no floor", self.win.status_text)

    def test_the_status_line_takes_the_answer(self):
        self.win.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.win.status_text, "into")

    def test_an_action_that_raises_says_so_on_the_status_line(self):
        def boom(*a):
            raise RuntimeError("the scene said no")
        self.scene.to_hand = boom
        self.win.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertIn("the scene said no", self.win.status_text)

    def test_an_empty_slot_starts_no_drag(self):
        self.assertIsNone(self.win.source_at(*self.win.rects["slot_L"][:2]))
        x, y = self.win.rects["slot_R"][:2]
        self.assertEqual(self.win.source_at(x + 5, y + 5), ("slot", "R"))
        x, y = look.item_rect(self.win.rects, self.win.placements["Dagger_01"],
                              self.win.cells["Dagger_01"])[:2]
        self.assertEqual(self.win.source_at(x + 3, y + 3), ("grid", "Dagger_01"))


class Wiring(unittest.TestCase):

    def test_the_payload_ships_both_modules(self):
        import install
        for name in ("maya_inventory.py", "maya_invlook.py"):
            self.assertIn(name, install.payload())

    def test_a_hotkey_row_opens_it(self):
        import maya_hotkeys
        self.assertIn("window.inventory", [row[0] for row in maya_hotkeys._OURS])

    def test_the_weapons_section_has_the_button(self):
        import inspect
        from maya_scenesetup import window
        source = inspect.getsource(window.build_weapons_panel)
        self.assertIn('label="Inventory"', source)
        self.assertIn('"backpack"', source)

    def test_the_backpack_icon(self):
        import maya_hubicons
        self.assertIn("backpack", maya_hubicons.ICONS)

    def test_no_maya_ui_is_imported_by_the_look(self):
        with open(os.path.join(PLUGIN, "maya_invlook.py"), encoding="utf-8") as handle:
            self.assertNotIn("import maya", handle.read())

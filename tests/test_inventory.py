"""The weapon inventory, offscreen: since 2026-09-30 the Weapons card itself
(«не в отдельном окне а как часть нашего меню»). It builds and paints ink,
the grid holds the catalog, the hand cards show the hands and their grips as
Channel Box columns, a click picks, a drag drops where the spec's table says
- on a fake scene, so no Maya scene is touched. The viewport half is
verify_weapons_card.py's.

Specs: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md,
docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md
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
WIDTH = 330


class FakeScene(object):
    """What the panel asks the scene and what it tells it, recorded."""

    def __init__(self):
        self.log = []
        self.hold = {"R": Holding("hand", "|w|LongSwordMesh", "LongSword_02",
                                  "Long Sword 02"),
                     "L": Holding(None, None, "", "")}
        self.aim = dict(kind="hand", root=ROOT, side="L",
                        text="Manny_Rig · left hand")
        self.watched = []
        self.said = []
        self.hand_grips = {"R": ((0.0, 90.0, 0.0), (1.5, 0.0, -2.25), True),
                           "L": ((1.38, -1.58, -179.51), (6.62, -0.98, 1.71),
                                 True)}
        self.choice = ["Dagger_01", "R"]

    def scale(self):
        return 1.0

    def current(self):
        return ROOT

    def holdings(self, root):
        return dict(self.hold)

    def grips(self, root):
        return dict(self.hand_grips)

    def picked(self):
        return tuple(self.choice)

    def select_weapon(self, key):
        self.log.append(("select_weapon", key))
        self.choice[0] = key
        return "picked " + key

    def select_hand(self, side):
        self.log.append(("select_hand", side))
        self.choice[1] = side
        return "hand " + side

    def set_grip(self, side, rotate, translate):
        self.log.append(("set_grip", side, tuple(rotate), tuple(translate)))
        return "gripped"

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

    def say(self, text):
        self.said.append(text)

    layout_in = {}
    layout_out = None

    def remembered_layout(self):
        return dict(self.layout_in)

    def remember_layout(self, placements):
        self.layout_out = dict(placements)


class PanelCase(unittest.TestCase):

    def setUp(self):
        self.app = (QT.QtWidgets.QApplication.instance()
                    or QT.QtWidgets.QApplication([]))
        self.scene = FakeScene()
        self.panel = inv.make_panel(self.scene)
        self.panel.resize(WIDTH, self.panel.height_for(WIDTH))
        self.panel.move(3000, 3000)             # well away from 500, 500
        self.panel.show()                       # its resize events delivered
        self.addCleanup(self.panel.deleteLater)
        self.rects = self.panel.rects()
        self.cell = self.rects["cell"]
        self.scene.log = []

    def global_of(self, name, dx=5, dy=5):
        x, y = self.rects[name][:2]
        point = self.panel.mapToGlobal(QT.QtCore.QPoint(int(x) + dx, int(y) + dy))
        return point.x(), point.y()

    def at_cell(self, col, row, dx=5, dy=5):
        gx, gy = self.rects["grid"][:2]
        p = self.panel.mapToGlobal(QT.QtCore.QPoint(
            int(gx + col * self.cell + dx), int(gy + row * self.cell + dy)))
        return p.x(), p.y()

    def image(self):
        image = QT.QtGui.QImage(self.panel.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.panel.render(image)
        return image

    def mouse(self, kind, local, button=None, buttons=None):
        Qt = QT.QtCore.Qt
        button = Qt.LeftButton if button is None else button
        buttons = button if buttons is None else buttons
        point = QT.QtCore.QPointF(local[0], local[1])
        glob = QT.QtCore.QPointF(self.panel.mapToGlobal(
            QT.QtCore.QPoint(int(local[0]), int(local[1]))))
        types = {"press": QT.QtCore.QEvent.MouseButtonPress,
                 "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease}
        event = QT.QtGui.QMouseEvent(types[kind], point, glob, button, buttons,
                                     Qt.NoModifier)
        {"press": self.panel.mousePressEvent,
         "move": self.panel.mouseMoveEvent,
         "release": self.panel.mouseReleaseEvent}[kind](event)

    def item_point(self, key, dx=3, dy=3):
        x, y = look.item_rect(self.rects, self.panel.placements[key],
                              self.panel.cells[key], self.cell)[:2]
        return x + dx, y + dy


@unittest.skipIf(QT is None, "no Qt")
class Panel(PanelCase):

    def test_it_paints_ink(self):
        image = self.image()
        inked = sum(1 for x in range(0, image.width(), 5)
                    for y in range(0, image.height(), 5)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 100)

    def test_the_grid_holds_every_catalog_row(self):
        self.assertEqual(set(self.panel.placements),
                         set(e.key for e in catalog.WEAPONS))

    def test_its_height_follows_the_width_and_it_is_named(self):
        self.assertEqual(self.panel.height(), look.panel(WIDTH)["panel"][3])
        self.assertGreater(self.panel.height_for(500), self.panel.height_for(250))
        self.assertEqual(self.panel.objectName(), inv.OBJECT_NAME)

    def test_it_watches_the_scene_and_stops(self):
        self.assertEqual(len(self.scene.watched), 1)
        scene = FakeScene()
        panel = inv.make_panel(scene)
        self.assertEqual(len(scene.watched), 1)
        panel.deleteLater()
        QT.QtCore.QCoreApplication.sendPostedEvents(
            None, QT.QtCore.QEvent.DeferredDelete)
        self.assertIn(("unwatch", ["job"]), scene.log)

    def test_the_hand_cards_are_hub_cards(self):
        import maya_hubstyle
        image = self.image()
        x, y, w, _h = self.rects["hand_L"]
        got = image.pixelColor(int(x + w - 10), int(y + 10))
        self.assertIn(got.name(), (maya_hubstyle.TOKENS["card"],
                                   maya_hubstyle.TOKENS["card_active"]))


@unittest.skipIf(QT is None, "no Qt")
class Channels(PanelCase):
    """«слева от окошка столбик с параметрами так как в стандартном
    интерфейсе маи в channel box»."""

    def test_twelve_fields_named_by_hand_and_channel(self):
        fields = self.panel.findChildren(QT.QtWidgets.QLineEdit)
        self.assertEqual(len(fields), 12)
        self.assertEqual(sorted(f.property("skChannel") for f in fields),
                         sorted("%s_%s" % (s, c) for s in "RL"
                                for c in look.CHANNELS))
        for field in fields:
            self.assertEqual(field.objectName(), inv.FIELD_NAME)

    def test_each_field_stands_in_its_row_left_of_the_well(self):
        for side in ("R", "L"):
            well_x = self.rects["well_" + side][0]
            for channel in look.CHANNELS:
                geo = self.panel.field(side, channel).geometry()
                row = self.rects["row_%s_%s" % (side, channel)]
                self.assertLessEqual(geo.right(), well_x)
                self.assertGreaterEqual(geo.top(), row[1])
                self.assertLessEqual(geo.bottom(), row[1] + row[3])
                self.assertGreater(geo.width(), 20)

    def test_the_fields_show_the_scenes_grips_in_channel_box_text(self):
        f = self.panel.field
        self.assertEqual([f("R", c).text() for c in look.CHANNELS],
                         ["1.5", "0", "-2.25", "0", "90", "0"])
        self.assertEqual(f("L", "rz").text(), "-179.51")
        self.assertEqual(f("L", "tx").text(), "6.62")

    def test_an_edit_applies_that_hands_six_values(self):
        field = self.panel.field("R", "ry")
        field.setText("45")
        field.editingFinished.emit()
        self.assertEqual(self.scene.log[-1],
                         ("set_grip", "R", (0.0, 45.0, 0.0), (1.5, 0.0, -2.25)))
        self.assertEqual(self.scene.said[-1], "gripped")

    def test_nothing_changed_applies_nothing(self):
        self.panel.field("L", "tx").editingFinished.emit()
        self.assertEqual([e for e in self.scene.log if e[0] == "set_grip"], [])

    def test_a_bad_value_puts_back_what_was_shown(self):
        field = self.panel.field("R", "tx")
        field.setText("abc")
        field.editingFinished.emit()
        self.assertEqual(field.text(), "1.5")
        self.assertEqual([e for e in self.scene.log if e[0] == "set_grip"], [])

    def test_escape_puts_back_what_was_shown(self):
        field = self.panel.field("R", "tz")
        field.setText("99")
        event = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress,
                                   QT.QtCore.Qt.Key_Escape,
                                   QT.QtCore.Qt.NoModifier)
        field.keyPressEvent(event)
        self.assertEqual(field.text(), "-2.25")

    def test_a_hand_that_cannot_take_a_grip_is_read_only(self):
        self.scene.hand_grips["L"] = ((0, 0, 0), (0, 0, 0), False)
        self.panel.refresh()
        self.assertTrue(self.panel.field("L", "tx").isReadOnly())
        self.assertFalse(self.panel.field("R", "tx").isReadOnly())

    def test_a_field_being_typed_in_is_not_rewritten(self):
        self.panel.show()
        self.panel.activateWindow()
        field = self.panel.field("R", "tx")
        field.setFocus()
        self.app.processEvents()
        if not field.hasFocus():
            self.skipTest("no focus offscreen")
        field.setText("7")
        self.panel.refresh()
        self.assertEqual(field.text(), "7")
        self.panel.refresh(force="R")
        self.assertEqual(field.text(), "1.5")

    def test_the_short_names_where_the_nice_ones_do_not_fit(self):
        """Measured with the panel's own font: offscreen Qt has no family
        and draws wide, so the size is set here rather than assumed."""
        small = QT.QtGui.QFont()
        small.setPixelSize(5)
        self.panel.field_font = small
        self.panel._place_fields()
        self.assertEqual(self.panel.short, {"R": False, "L": False})
        big = QT.QtGui.QFont()
        big.setPixelSize(40)
        self.panel.field_font = big
        self.panel._place_fields()
        self.assertEqual(self.panel.short, {"R": True, "L": True})


@unittest.skipIf(QT is None, "no Qt")
class Picking(PanelCase):
    """A click picks (the card's Add / Remove act on it), a drag past the
    start distance carries."""

    def test_a_click_on_an_item_picks_it_and_drops_nothing(self):
        point = self.item_point("Spear_03")
        self.mouse("press", point)
        self.mouse("release", point)
        self.assertEqual(self.scene.log, [("select_weapon", "Spear_03")])
        self.assertEqual(self.panel.picked_key, "Spear_03")
        self.assertIsNone(self.panel._drag)

    def test_a_click_on_a_hand_card_picks_the_hand(self):
        x, y = self.rects["name_L"][:2]
        self.mouse("press", (x + 3, y + 3))
        self.mouse("release", (x + 3, y + 3))
        self.assertEqual(self.scene.log, [("select_hand", "L")])
        self.assertEqual(self.panel.picked_side, "L")

    def test_a_press_moved_past_the_distance_drags(self):
        start = self.item_point("Dagger_01")
        self.mouse("press", start)
        self.assertIsNone(self.panel._drag)
        far = (start[0] + 50, start[1] + 400)
        self.mouse("move", far, button=QT.QtCore.Qt.NoButton,
                   buttons=QT.QtCore.Qt.LeftButton)
        self.assertIsNotNone(self.panel._drag)
        self.mouse("release", (start[0] - 2000, start[1]))
        self.assertIsNone(self.panel._drag)
        self.assertEqual(self.scene.log[-1], ("to_hand", ROOT, "L", "Dagger_01"))

    def test_the_right_button_cancels_a_drag(self):
        start = self.item_point("Dagger_01")
        self.mouse("press", start)
        self.mouse("move", (start[0] + 50, start[1] + 50),
                   button=QT.QtCore.Qt.NoButton, buttons=QT.QtCore.Qt.LeftButton)
        self.mouse("press", start, button=QT.QtCore.Qt.RightButton)
        self.assertIsNone(self.panel._drag)
        self.assertIn("cancelled", self.scene.said)

    def test_an_empty_hand_starts_no_drag(self):
        self.assertIsNone(self.panel.source_at(*self.rects["well_L"][:2]))
        x, y = self.rects["well_R"][:2]
        self.assertEqual(self.panel.source_at(x + 5, y + 5), ("slot", "R"))
        self.assertEqual(self.panel.source_at(*self.item_point("Dagger_01")),
                         ("grid", "Dagger_01"))

    def test_the_picked_item_and_hand_are_lit(self):
        import maya_hubstyle
        image = self.image()
        x, y = self.item_point("Dagger_01", dx=4, dy=self.cell)
        self.assertEqual(image.pixelColor(int(x), int(y)).name(),
                         maya_hubstyle.TOKENS["card_active"])
        hx, hy, hw, _hh = self.rects["hand_R"]
        edge = image.pixelColor(int(hx + hw // 2), int(hy))
        self.assertEqual(edge.name(), maya_hubstyle.TOKENS["accent"])


@unittest.skipIf(QT is None, "no Qt")
class Drops(PanelCase):
    """The window's drop table, unchanged in the card."""

    def test_grid_onto_a_hand_in_the_viewport(self):
        self.panel.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.scene.log[-1], ("to_hand", ROOT, "L", "Dagger_01"))

    def test_grid_onto_the_floor(self):
        self.scene.aim = dict(kind="floor", root="|root", side="L",
                              point=(1, 0, 2), heading=(1, 0, 0), text="floor")
        self.panel.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual(self.scene.log[-1], ("to_floor", "|root", "Spear_01", "L"))

    def test_grid_onto_a_hand_card(self):
        self.panel.drop_at(*self.global_of("well_L"), source=("grid", "Dagger_01"))
        self.assertEqual(self.scene.log, [("to_hand", ROOT, "L", "Dagger_01")])

    def test_slot_onto_the_grid_takes_it_off(self):
        self.panel.drop_at(*self.global_of("grid"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [("take_off", ROOT, "R")])

    def test_slot_onto_the_other_slot_moves_it(self):
        self.panel.drop_at(*self.global_of("hand_L"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [("move", ROOT, "R", "hand")])

    def test_slot_onto_its_own_slot_does_nothing(self):
        self.panel.drop_at(*self.global_of("hand_R"), source=("slot", "R"))
        self.assertEqual(self.scene.log, [])

    def test_slot_out_to_the_viewport_moves_it_and_frees_its_side(self):
        self.panel.drop_at(500, 500, ("slot", "R"))
        self.assertEqual(self.scene.log, [("target", (ROOT, "R")),
                                          ("move", ROOT, "R", "hand")])

    def test_no_target_does_nothing_and_says_why(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.panel.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual([e for e in self.scene.log if e[0] != "target"], [])
        self.assertIn("no floor", self.panel.status_text)

    def test_the_card_line_takes_the_answer(self):
        self.panel.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.panel.status_text, "into")
        self.assertEqual(self.scene.said[-1], "into")

    def test_an_action_that_raises_says_so_on_the_line(self):
        def boom(*a):
            raise RuntimeError("the scene said no")
        self.scene.to_hand = boom
        self.panel.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertIn("the scene said no", self.panel.status_text)


@unittest.skipIf(QT is None, "no Qt")
class Rearranged(PanelCase):
    """2026-09-29, «можно было перетаскивать по инвентарю»: a grid item
    dropped in the grid moves, swaps with the one it lands on when that one
    fits back, or stays; the layout is remembered and a Sort packs it again.
    Nothing in the scene is touched."""

    def scene_actions(self):
        return [e for e in self.scene.log if e[0] != "target"]

    def test_a_grid_drop_moves_the_item_and_remembers(self):
        self.panel.drop_at(*self.at_cell(6, 1), source=("grid", "Dagger_01"), grab=(0, 0))
        self.assertEqual(self.panel.placements["Dagger_01"], (6, 1))
        self.assertEqual(self.scene.layout_out["Dagger_01"], (6, 1))
        self.assertEqual(self.scene_actions(), [])
        self.assertIn("moved", self.panel.status_text)

    def test_the_grab_point_stays_under_the_cursor(self):
        self.panel.drop_at(*self.at_cell(6, 3), source=("grid", "LongSword_02"),
                           grab=(0, 2))
        self.assertEqual(self.panel.placements["LongSword_02"], (6, 1))

    def test_onto_another_item_that_fits_back_they_swap(self):
        self.panel.drop_at(*self.at_cell(1, 0), source=("grid", "LongSword_02"),
                           grab=(0, 0))
        self.assertEqual((self.panel.placements["LongSword_02"],
                          self.panel.placements["Spear_01"]), ((1, 0), (0, 0)))
        self.assertIn("swapped", self.panel.status_text)

    def test_no_room_leaves_the_grid_as_it_was(self):
        before = dict(self.panel.placements)
        self.panel.drop_at(*self.at_cell(0, 0), source=("grid", "Dagger_01"), grab=(0, 0))
        self.assertEqual(self.panel.placements, before)
        self.assertIsNone(self.scene.layout_out)
        self.assertIn("no room", self.panel.status_text)

    def test_sort_packs_the_catalog_again_and_remembers(self):
        self.panel.drop_at(*self.at_cell(6, 1), source=("grid", "Dagger_01"), grab=(0, 0))
        self.panel.sort()
        self.assertEqual(self.panel.placements["Dagger_01"], (3, 0))
        self.assertEqual(self.scene.layout_out["Dagger_01"], (3, 0))

    def test_a_remembered_layout_opens_as_it_was_left(self):
        self.scene.layout_in = {"Dagger_01": [9, 3]}
        panel = inv.make_panel(self.scene)
        self.addCleanup(panel.deleteLater)
        self.assertEqual(panel.placements["Dagger_01"], (9, 3))

    def test_the_preview_paints(self):
        self.panel.preview = (look.footprint((6, 1), (1, 2)), True)
        image = self.image()
        gx, gy = self.rects["grid"][:2]
        lit = image.pixelColor(int(gx + 6 * self.cell + self.cell // 2),
                               int(gy + 1 * self.cell + self.cell // 2))
        self.assertGreater(lit.green(), lit.red())


@unittest.skipIf(QT is None, "no Qt")
class Attached(unittest.TestCase):
    """Laid over a placeholder, the placeholder kept as tall as the panel."""

    def test_the_keeper_sizes_the_host(self):
        app = (QT.QtWidgets.QApplication.instance()
               or QT.QtWidgets.QApplication([]))
        del app
        host = QT.QtWidgets.QWidget()
        self.addCleanup(host.deleteLater)
        classes = inv._classes()
        panel = classes["InventoryPanel"](FakeScene(), host)
        keeper = classes["Keeper"](panel, panel)
        host.installEventFilter(keeper)
        host.resize(360, 40)
        panel.fit(host)
        self.assertEqual(host.height(), panel.height_for(360))
        self.assertEqual(panel.geometry(), host.rect())

    def test_show_opens_the_hub_on_weapons(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(inv.show(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["weapons"])

    def test_the_floating_window_is_gone(self):
        for name in ("make_window", "InventoryWindow", "POSITION_OPTIONVAR"):
            self.assertFalse(hasattr(inv, name), name)
        self.assertNotIn("InventoryWindow", inv._classes())


class Skin(unittest.TestCase):
    """2026-09-30: the hub's look (style B), not Diablo's."""

    def _source(self):
        with open(inv.__file__, encoding="utf-8") as handle:
            return handle.read()

    def test_no_colour_of_its_own(self):
        import re
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b", self._source()), [])

    def test_no_diablo_left(self):
        """The styling, not the history: the docstring still quotes the ask."""
        source = self._source().lower()
        for word in ("bronze", "parchment", "gold", "_diamond", "_bevel",
                     "title_fonts", "smallcaps"):
            self.assertNotIn(word, source)

    def test_every_colour_it_names_is_a_hub_token(self):
        import re
        import maya_hubstyle
        names = set(re.findall(r'colour\("([a-z_]+)"', self._source()))
        self.assertTrue(names)
        self.assertEqual(sorted(names - set(maya_hubstyle.TOKENS)), [])


class Wiring(unittest.TestCase):

    def test_the_payload_ships_both_modules(self):
        import install
        for name in ("maya_inventory.py", "maya_invlook.py"):
            self.assertIn(name, install.payload())

    def test_a_hotkey_row_opens_it(self):
        import maya_hotkeys
        self.assertIn("window.inventory", [row[0] for row in maya_hotkeys._OURS])

    def test_the_weapons_card_lays_it_over_its_placeholder(self):
        from maya_scenesetup import window
        self.assertEqual(window._INVENTORY, inv.PLACEHOLDER)

    def test_the_backpack_icon(self):
        import maya_hubicons
        self.assertIn("backpack", maya_hubicons.ICONS)

    def test_no_maya_ui_is_imported_by_the_look(self):
        import re
        with open(os.path.join(PLUGIN, "maya_invlook.py"), encoding="utf-8") as handle:
            source = handle.read()
        # Maya itself, not maya_hubstyle (stdlib, the palette since 2026-09-30)
        self.assertEqual(re.findall(r"^\s*(?:import|from)\s+maya(?:\.|\s|$)", source,
                                    re.MULTILINE), [])

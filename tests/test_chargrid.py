"""The Characters card's portrait grid, offscreen (2026-09-30): it paints the
portraits, a click selects, the switch dims, a drag outside the widget drops a
character on the floor - on a fake scene, so no Maya scene is touched. The
viewport half is verify_character_grid.py's.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""
import os
import re
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_chargrid as cg
import maya_charlook as look
from maya_scenesetup import catalog


class FakeScene(object):

    def __init__(self):
        self.log = []
        self.aim = dict(kind="floor", point=(120.0, 0.0, -35.0))

    def scale(self):
        return 1.0

    def target(self, gx, gy):
        self.log.append(("target", gx, gy))
        return self.aim

    def over_hub(self, gx, gy):
        return False

    def select(self, model):
        self.log.append(("select", model))

    def place(self, model, kind, point):
        self.log.append(("place", model, kind, point))
        return "placed"

    def open_scene(self, model, kind):
        self.log.append(("open_scene", model, kind))
        return "opened"

    def say(self, text):
        self.log.append(("say", text))


@unittest.skipIf(QT is None, "no Qt")
class Grid(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.scene = FakeScene()
        self.grid = cg.make_grid(self.scene, kind="rig", selected="Manny")
        self.grid.resize(330, self.grid.height_for(330))
        self.grid.move(3000, 3000)
        self.addCleanup(self.grid.deleteLater)

    def centre(self, index):
        x, y, w, h = self.grid.rects()[index]
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)

    def acts(self, name):
        return [e for e in self.scene.log if e[0] == name]

    def test_it_paints_ink(self):
        image = QT.QtGui.QImage(self.grid.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.grid.render(image)
        inked = sum(1 for x in range(0, image.width(), 4)
                    for y in range(0, image.height(), 4)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 200)

    def test_one_tile_per_model(self):
        count = len(catalog.MODELS)
        self.assertEqual(len(self.grid.rects()), count)
        self.assertEqual(self.grid.height_for(330), look.grid(330, count)[3])

    def test_the_auto_card_is_picked_in_both_kinds(self):
        """2026-10-02: the «?» card has no row, and is pickable all the same."""
        for kind in catalog.KINDS:
            self.grid.set_kind(kind)
            self.assertTrue(self.grid.available("Auto"))
        self.assertTrue(self.grid.select("Auto"))
        self.assertEqual(self.acts("select")[-1], ("select", "Auto"))

    def test_the_auto_card_offers_no_scene_and_is_never_placed(self):
        self.assertEqual(self.grid.context_actions("Auto"), [])
        self.assertEqual(self.grid.drop_at(10, 10, "Auto"), look.AUTO_ADD)
        self.assertEqual(self.acts("place"), [])

    def test_a_click_selects_and_calls_back(self):
        self.assertTrue(self.grid.select("Creep"))
        self.assertEqual(self.grid.selected, "Creep")
        self.assertEqual(self.acts("select"), [("select", "Creep")])

    def test_a_dimmed_tile_is_not_selected(self):
        self.assertFalse(self.grid.select("UE4_Mannequin"))
        self.assertEqual(self.grid.selected, "Manny")
        self.assertEqual(self.acts("select"), [])

    def test_the_switch_dims_the_other_model(self):
        self.grid.set_kind("skeleton")
        self.assertTrue(self.grid.available("UE4_Mannequin"))
        self.assertFalse(self.grid.available("Orc_D"))
        self.grid.set_selected("Orc_D")
        self.assertEqual(self.grid.selected, "Orc_D")

    def test_the_model_under_a_point(self):
        p = self.centre(2)
        self.assertEqual(self.grid.model_at(p.x(), p.y()), "Orc_D")
        self.assertIsNone(self.grid.model_at(-5, -5))

    def test_a_drop_on_the_floor_places_the_chosen_kind(self):
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [("place", "Creep", "rig", (120.0, 0.0, -35.0))])
        self.assertEqual(self.grid.status_text, "placed")

    def test_no_floor_places_nothing_and_says_why(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [])
        self.assertIn(("say", "no floor under the cursor"), self.scene.log)

    def test_a_drop_back_on_the_hub_does_nothing(self):
        self.scene.over_hub = lambda gx, gy: True
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [])
        self.assertEqual(self.acts("target"), [])

    def test_a_drop_that_raises_says_so(self):
        def boom(*a):
            raise RuntimeError("the scene said no")
        self.scene.place = boom
        self.grid.drop_at(500, 500, "Creep")
        self.assertIn("the scene said no", self.grid.status_text)

    def _mouse(self, kind, local, button, buttons):
        g = self.grid.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    def test_press_drag_release_outside_drops_the_pressed_portrait(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(1)
        far = start + QT.QtCore.QPoint(-900, 400)
        self._mouse(E.MouseButtonPress, start, L, L)
        self.assertEqual(self.grid.selected, "Creep")
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(30, 0), N, L)
        self.assertIsNotNone(self.grid._drag)
        self._mouse(E.MouseMove, far, N, L)
        self._mouse(E.MouseButtonRelease, far, L, N)
        self.assertIsNone(self.grid._drag)
        self.assertEqual(self.acts("place"), [("place", "Creep", "rig", (120.0, 0.0, -35.0))])

    def test_a_click_without_travel_is_no_drag(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(2)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseButtonRelease, start, L, N)
        self.assertEqual(self.acts("place"), [])
        self.assertEqual(self.grid.selected, "Orc_D")

    def test_a_press_on_a_dimmed_tile_starts_nothing(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(3)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        self.assertIsNone(self.grid._drag)
        self.assertEqual(self.grid.selected, "Manny")

    def test_a_press_and_a_pull_on_the_auto_card_picks_it_and_drags_nothing(self):
        """2026-10-02: the «?» card is picked, never carried into a viewport."""
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        index = [m.key for m in catalog.MODELS].index("Auto")
        start = self.centre(index)
        self._mouse(E.MouseButtonPress, start, L, L)
        self.assertEqual(self.grid.selected, "Auto")
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(-900, 400), N, L)
        self.assertIsNone(self.grid._drag)
        self._mouse(E.MouseButtonRelease, start + QT.QtCore.QPoint(-900, 400), L, N)
        self.assertEqual(self.acts("place"), [])

    def test_escape_cancels_a_drag(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(0)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        key = QT.QtGui.QKeyEvent(E.KeyPress, QT.QtCore.Qt.Key_Escape, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, key)
        self.assertIsNone(self.grid._drag)
        self._mouse(E.MouseButtonRelease, start + QT.QtCore.QPoint(900, 0), L, N)
        self.assertEqual(self.acts("place"), [])

    def test_the_right_button_cancels_a_drag(self):
        E, L, R, N = (QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton,
                      QT.QtCore.Qt.RightButton, QT.QtCore.Qt.NoButton)
        start = self.centre(0)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        self._mouse(E.MouseButtonPress, start + QT.QtCore.QPoint(40, 0), R, L | R)
        self.assertIsNone(self.grid._drag)

    def test_the_right_button_offers_open_scene_for_the_shown_kind(self):
        actions = self.grid.context_actions("Creep")
        self.assertEqual([label for label, _fn in actions], ["Open scene"])
        actions[0][1]()
        self.assertEqual(self.acts("open_scene"), [("open_scene", "Creep", "rig")])
        self.assertEqual(self.grid.status_text, "opened")
        self.grid.set_kind("skeleton")
        self.grid.context_actions("Manny")[0][1]()
        self.assertEqual(self.acts("open_scene")[-1], ("open_scene", "Manny", "skeleton"))

    def test_a_dimmed_portrait_shows_open_scene_disabled(self):
        self.assertEqual(self.grid.context_actions("UE4_Mannequin"),
                         [("Open scene (no rig)", None)])

    def test_off_every_portrait_there_is_no_menu(self):
        self.assertEqual(self.grid.context_actions(None), [])

    def test_a_right_press_runs_the_menu_and_picks_nothing(self):
        shown = []
        saved = maya_hubqt.run_menu
        maya_hubqt.run_menu = lambda parent, point, actions: shown.append(
            (parent, [label for label, _fn in actions]))
        self.addCleanup(setattr, maya_hubqt, "run_menu", saved)
        E, R = QT.QtCore.QEvent, QT.QtCore.Qt.RightButton
        start = self.centre(1)
        self._mouse(E.MouseButtonPress, start, R, R)
        self.assertEqual(shown, [(self.grid, ["Open scene"])])
        self.assertEqual(self.acts("select"), [])
        self.assertIsNone(self.grid._press)

    def test_the_ghost_is_the_shared_one(self):
        self.assertIs(cg._classes()["Ghost"], maya_hubqt.ghost_class())

    def test_a_placeholder_grows_to_the_grids_height(self):
        host = QT.QtWidgets.QWidget()
        self.addCleanup(host.deleteLater)
        host.resize(330, 10)
        grid = cg.make_grid(self.scene, parent=host, kind="rig", selected="Manny")
        grid.fit(host)
        self.assertEqual(host.height(), look.grid(330, len(catalog.MODELS))[3])
        self.assertEqual(grid.geometry(), host.rect())


class Skin(unittest.TestCase):

    def _source(self):
        with open(cg.__file__, encoding="utf-8") as handle:
            return handle.read()

    def test_no_colour_of_its_own(self):
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b", self._source()), [])

    def test_every_colour_it_names_is_a_hub_token(self):
        import maya_hubstyle
        names = set(re.findall(r'colour\("([a-z_0-9]+)"', self._source()))
        self.assertTrue(names)
        self.assertEqual(sorted(names - set(maya_hubstyle.TOKENS)), [])


if __name__ == "__main__":
    unittest.main()

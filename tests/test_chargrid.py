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

    def test_the_card_holds_every_model_in_one_row_at_the_docks_width(self):
        """2026-10-08, the compact hub: five a row, and the grid is as tall as
        its squares - the name lies over them."""
        count = len(catalog.MODELS)
        cols, cell, rects, height = look.grid(330, count)
        self.assertEqual(cols, count)
        self.assertEqual(self.grid.height_for(330), cell)
        self.assertEqual(len({r[1] for r in self.grid.rects()}), 1)

    def render(self):
        image = QT.QtGui.QImage(self.grid.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.grid.render(image)
        return image

    def test_the_name_lies_over_the_portraits_bottom_on_a_shade(self):
        """2026-10-08: no strip under the portrait - the name is drawn over the
        picture's bottom on a shade that fades in from the picture."""
        import maya_hubstyle
        self.grid.pixmaps = {}                 # no picture in the way of the pixels
        image = self.render()
        x, y, w, h = self.grid.rects()[self.keys().index("Creep")]
        nx, ny, nw, nh = look.name_rect((x, y, w, h), self.grid.k)
        self.assertEqual(ny + nh, y + h)

        def luma(px, py):
            c = image.pixelColor(int(px), int(py))
            return c.red() + c.green() + c.blue()
        self.assertEqual(image.pixelColor(x + 4, ny - 3).name(),
                         maya_hubstyle.TOKENS["field"])
        self.assertLess(luma(x + 4, y + h - 4), 0.7 * luma(x + 4, ny - 3))
        self.assertLess(luma(x + 4, y + h - 4), luma(x + 4, ny + 1))

    def test_the_no_rig_tag_sits_above_the_name(self):
        """2026-10-08: the tag on a dimmed portrait moved up by the name's
        height, so the name is never drawn on it."""
        import maya_hubstyle
        self.grid.pixmaps = {}
        image = self.render()
        x, y, w, h = self.grid.rects()[self.keys().index("UE4_Mannequin")]   # no rig
        nx, ny, nw, nh = look.name_rect((x, y, w, h), self.grid.k)
        pad = int(4 * self.grid.k)
        tag_mid = y + h - nh - pad - int(8 * self.grid.k)
        self.assertEqual(image.pixelColor(x + pad + 2, tag_mid).name(),
                         maya_hubstyle.TOKENS["status"])
        # the strip itself holds the shade, not the pill's colour
        self.assertNotEqual(image.pixelColor(x + pad + 2, ny + nh // 2).name(),
                            maya_hubstyle.TOKENS["status"])

    def keys(self):
        return [m.key for m in self.grid.models]

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


@unittest.skipIf(QT is None, "no Qt")
class FireOnHover(unittest.TestCase):
    """2026-10-02: the cursor sets a portrait alight in its own fire
    (docs/superpowers/specs/2026-10-02-character-card-fire-design.md)."""

    def setUp(self):
        import maya_charfire
        self.cf = maya_charfire
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.scene = FakeScene()
        self.grid = cg.make_grid(self.scene, kind="rig", selected="Manny")
        self.grid.resize(330, self.grid.height_for(330))
        self.addCleanup(self.grid.deleteLater)
        animations = cg._animations
        self.addCleanup(lambda: setattr(cg, "_animations", animations))

    def keys(self):
        return [m.key for m in self.grid.models]

    def burn(self, model, seconds=1.0):
        self.grid.hover_model(model)
        for _ in range(int(seconds * 60)):
            self.grid.advance(1.0 / 60)

    def render(self, widget):
        image = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        widget.render(image)
        return image

    def count(self, image, rect, test):
        x0, y0, w, h = [int(v) for v in rect]
        hits = 0
        for x in range(max(0, x0), min(image.width(), x0 + w), 2):
            for y in range(max(0, y0), min(image.height(), y0 + h), 2):
                c = image.pixelColor(x, y)
                if test(c.red(), c.green(), c.blue()):
                    hits += 1
        return hits

    def box(self, model):
        return self.grid.rects()[self.keys().index(model)]

    def test_hovering_an_available_portrait_lights_it(self):
        self.grid.hover_model("Creep")
        self.assertIn("Creep", self.grid.fx)
        self.assertTrue(self.grid.fx["Creep"].hover)
        self.assertTrue(self.grid.fire_timer.isActive())

    def test_a_dimmed_portrait_does_not_burn(self):
        self.grid.hover_model("UE4_Mannequin")          # no rig: dimmed
        self.assertEqual(self.grid.fx, {})

    def test_no_fire_with_the_interface_animations_off(self):
        cg._animations = lambda: False
        self.grid.hover_model("Creep")
        self.assertEqual(self.grid.fx, {})
        self.assertEqual(self.grid._hover, "Creep")     # the old hover stands

    def test_a_model_with_no_fire_keeps_the_old_hover(self):
        fires = dict(self.cf.FIRES)
        self.addCleanup(lambda: self.cf.FIRES.update(fires))
        del self.cf.FIRES["Creep"]
        self.grid.hover_model("Creep")
        self.assertEqual(self.grid.fx, {})
        self.assertEqual(self.grid._hover, "Creep")

    def test_a_burning_card_keeps_its_name_over_its_bottom(self):
        """2026-10-08: the name is over the picture, so the fire's own paint
        (the grown, burning card) lays the same shade under it - the fire
        rising from the bottom would otherwise wash the name out."""
        self.burn("Creep", 0.5)
        x, y, w, h = self.box("Creep")

        def foot(image):
            c = image.pixelColor(x + 6, y + h - 4)         # left of the name's letters
            return c.red() + c.green() + c.blue()
        with_name = foot(self.render(self.grid))
        self.grid._paint_name = lambda *args, **kwargs: None      # the name off
        without = foot(self.render(self.grid))
        self.assertLess(with_name, 0.8 * without, (with_name, without))

    def test_the_unknown_card_burns_as_mannys_does(self):
        """The «?» card burns orange (2026-10-02, «так же как и карточка
        менни»): flame-orange where it was the dark field."""
        from maya_scenesetup import catalog
        self.assertIn(catalog.AUTO, self.keys())
        # the fire's yellow-orange, brighter than the «?» mark's accent
        flame = lambda r, g, b: r > 235 and g > 140 and b < 150      # noqa: E731
        box = self.box(catalog.AUTO)
        cold = self.count(self.render(self.grid), box, flame)
        self.assertLess(cold, 5)
        self.burn(catalog.AUTO)
        self.assertIn(catalog.AUTO, self.grid.fx)
        hot = self.count(self.render(self.grid), box, flame)
        self.assertGreater(hot, 30, (cold, hot))

    def test_the_fire_burns_behind_the_unknown_cards_silhouette(self):
        """«сделай что бы огонь как и на других карточках горел за
        силуэтом»: where the «?» card's faint silhouette stands the card
        looks as it does cold; beside it the fire shows."""
        from maya_scenesetup import catalog
        x, y, w, h = self.box(catalog.AUTO)
        body = (int(x + w * 40 / 256.0), int(y + h * 245 / 256.0))   # alpha 0.30
        empty = (int(x + w * 40 / 256.0), int(y + h * 180 / 256.0))  # alpha 0
        cold = self.render(self.grid)
        self.burn(catalog.AUTO)
        hot = self.render(self.grid)

        def change(point):
            a, b = cold.pixelColor(*point), hot.pixelColor(*point)
            return max(abs(a.red() - b.red()), abs(a.green() - b.green()),
                       abs(a.blue() - b.blue()))
        self.assertLess(change(body), 40)
        self.assertGreater(change(empty), 60)

    def test_moving_on_puts_the_first_out_and_lights_the_second(self):
        self.burn("Creep", 0.3)
        self.grid.hover_model("Orc_D")
        self.assertFalse(self.grid.fx["Creep"].hover)
        self.assertTrue(self.grid.fx["Orc_D"].hover)

    def test_burnt_out_cards_are_dropped_and_the_timer_stops(self):
        self.burn("Creep", 0.5)
        self.grid.hover_model(None)
        still = True
        for _ in range(60 * 6):
            still = self.grid.advance(1.0 / 60)
        self.assertFalse(still)
        self.assertEqual(self.grid.fx, {})
        self.assertFalse(self.grid.fire_timer.isActive())

    def test_a_burning_card_paints_its_own_fire(self):
        blue = lambda r, g, b: b > r + 50 and b > 90                  # noqa: E731
        green = lambda r, g, b: g > r + 50 and g > b + 30 and g > 90  # noqa: E731
        cold = self.render(self.grid)
        self.assertLess(self.count(cold, self.box("Creep"), blue), 5)
        self.assertLess(self.count(cold, self.box("Orc_D"), green), 5)
        self.burn("Creep")
        hot = self.render(self.grid)
        self.assertGreater(self.count(hot, self.box("Creep"), blue), 60)
        self.grid.hover_model("Orc_D")
        for _ in range(60):
            self.grid.advance(1.0 / 60)
        hot = self.render(self.grid)
        # the Orc's shoulders fill the card: less fire shows, and it is green.
        # (The card is a 64 px square now, 0.64 of the old area, and the name's
        # shade darkens the flames' base: 7 samples of green against 0 cold.)
        self.assertGreater(self.count(hot, self.box("Orc_D"), green), 3)

    def test_a_drag_puts_the_fire_out(self):
        self.burn("Creep", 0.3)
        self.grid._start("Creep", QT.QtCore.QPoint(10, 10))
        self.addCleanup(self.grid._end)
        self.assertFalse(any(fx.hover for fx in self.grid.fx.values()))
        self.grid.hover_model("Orc_D")                  # nothing lights mid-drag
        self.assertNotIn("Orc_D", self.grid.fx)

    def test_a_click_bursts_sparks(self):
        self.burn("Creep", 0.1)
        before = len(self.grid.fx["Creep"].sparks.age)
        self.assertTrue(self.grid.select("Creep"))
        self.assertEqual(len(self.grid.fx["Creep"].sparks.age),
                         before + self.cf.CLICK_SPARKS)

    def test_without_a_scroll_area_the_grid_draws_its_fire_itself(self):
        self.grid.show()
        self.burn("Creep", 0.2)
        self.assertIsNone(self.grid.overlay)
        self.assertEqual(self.grid.overlaid, set())

    def _in_a_hub(self, content_h=600):
        area = QT.QtWidgets.QScrollArea()
        self.addCleanup(area.deleteLater)
        area.resize(420, 400)
        content = QT.QtWidgets.QWidget()
        content.resize(400, content_h)
        area.setWidget(content)
        host = QT.QtWidgets.QWidget(content)
        host.setGeometry(30, 150, 330, 10)
        grid = cg.make_grid(self.scene, parent=host, kind="rig", selected="Manny")
        grid.fit(host)
        area.show()
        self.app.processEvents()
        return area, content, host, grid

    def test_in_a_hub_the_overlay_draws_the_burning_card_past_its_edges(self):
        area, content, host, grid = self._in_a_hub()
        grid.hover_model("Creep")
        for _ in range(60):
            grid.advance(1.0 / 60)
        overlay = grid.overlay
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay.objectName(), cg.FIRE_NAME)
        self.assertIs(overlay.parentWidget(), content)
        self.assertTrue(overlay.testAttribute(
            QT.QtCore.Qt.WA_TransparentForMouseEvents))
        spot = QT.QtCore.QRect(grid.mapTo(content, QT.QtCore.QPoint(0, 0)),
                               grid.size())
        self.assertTrue(overlay.geometry().contains(spot))
        self.assertGreater(overlay.geometry().top(), -1)
        self.assertLess(overlay.geometry().top(), spot.top())   # room above
        self.assertEqual(grid.overlaid, {"Creep"})
        blue = lambda r, g, b: b > r + 50 and b > 90                  # noqa: E731
        index = [m.key for m in grid.models].index("Creep")
        x, y, w, h = grid.rects()[index]
        # the overlay has it, the grid skips it
        lifted = self.render(overlay)
        o = overlay.origin
        self.assertGreater(self.count(lifted, (x + o.x(), y + o.y(), w, h),
                                      blue), 60)
        self.assertLess(self.count(self.render(grid), (x, y, w, h), blue), 5)

    def test_a_grid_cut_by_its_parent_draws_its_fire_itself(self):
        area, content, host, grid = self._in_a_hub()
        host.setFixedHeight(20)                          # a card sliding shut
        host.resize(host.width(), 20)
        self.app.processEvents()
        grid.resize(grid.width(), grid.height_for(grid.width()))
        grid.hover_model("Creep")
        grid.advance(1.0 / 60)
        self.assertEqual(grid.overlaid, set())

    def test_the_overlay_goes_with_the_grid(self):
        area, content, host, grid = self._in_a_hub()
        grid.hover_model("Creep")
        grid.advance(1.0 / 60)
        overlay = grid.overlay
        self.assertIsNotNone(overlay)
        grid.deleteLater()
        for _ in range(3):
            self.app.processEvents()
            QT.QtCore.QCoreApplication.sendPostedEvents(
                None, QT.QtCore.QEvent.DeferredDelete)
        self.assertFalse(QT.shiboken.isValid(overlay))


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

"""Walk Builder's wells (maya_walk.posewell), the corners the first tests left: the Scene that hands every press to
the card (maya_walk.panel), the screen's scale, a well's name by its kind and its copy, the thumbnails drawn,
clicks and double clicks and the right button sent as Qt events, the well kept over its placeholder, a press that
fails, and the wells standing (attach, live, every, well_at, light, refresh_all). Offscreen Qt."""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubcopy as hubcopy                  # noqa: E402
import maya_hubqt                              # noqa: E402
from maya_walk import panel                    # noqa: E402
from maya_walk import posewell as pw           # noqa: E402


@contextlib.contextmanager
def hushed():
    """A traceback a press prints on its way, kept off the test's output."""
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        yield


class FakeScene(object):
    """The well's scene: a column of cards held here, every call recorded."""

    def __init__(self, rows=None, scale=1.0):
        self.rows = list(rows or [])
        self.calls = []
        self.k = scale
        self.fail = None

    def scale(self):
        return self.k

    def cards(self):
        self.calls.append(("cards",))
        if self.fail:
            raise RuntimeError(self.fail)
        return list(self.rows)

    def _row(self, path, active):
        name = path.rsplit("/", 1)[-1].split(".")[0]
        return (path, name, "", "", active)

    def take(self, path):
        self.calls.append(("take", path, hubcopy.current()))
        paths = [r[0] for r in self.rows]
        if path not in paths:
            paths.append(path)
        self.rows = [self._row(p, p == path) for p in paths]
        return "took " + path

    def pick(self, path):
        self.calls.append(("pick", path))
        self.rows = [self._row(r[0], r[0] == path) for r in self.rows]
        return "picked " + path

    def remove(self, path):
        self.calls.append(("remove", path))
        self.rows = [r for r in self.rows if r[0] != path]

    def remove_all(self):
        self.calls.append(("remove_all",))
        self.rows = []

    def clear(self):
        self.calls.append(("clear",))
        self.rows = [self._row(r[0], False) for r in self.rows]

    def show(self, path):
        self.calls.append(("show", path))

    def made(self, name):
        return [c for c in self.calls if c[0] == name]


class Qt(unittest.TestCase):

    def setUp(self):
        if maya_hubqt.qt() is None:
            self.skipTest("no Qt")
        self.q = maya_hubqt.qt()
        self.QtCore, self.QtGui, self.QtWidgets = self.q.QtCore, self.q.QtGui, self.q.QtWidgets
        self.app = self.QtWidgets.QApplication.instance() or self.QtWidgets.QApplication([])
        self.saved_wells = dict(pw._WELLS)
        pw._WELLS.clear()
        self.saved = {"find": maya_hubqt.find, "run_menu": maya_hubqt.run_menu, "qt": maya_hubqt.qt}
        self.menus = []
        maya_hubqt.run_menu = lambda parent, point, actions: self.menus.append((parent, point, actions)) or "menu"
        self.widgets = []
        self.temp = tempfile.mkdtemp()

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(maya_hubqt, name, value)
        for widget in reversed(self.widgets):
            try:
                if self.q.shiboken.isValid(widget):
                    widget.hide()
                    self.q.shiboken.delete(widget)
            except RuntimeError:
                pass
        pw._WELLS.clear()
        pw._WELLS.update(self.saved_wells)
        shutil.rmtree(self.temp, ignore_errors=True)

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def well(self, scene, kind="pose", width=300):
        well = self.keep(pw.make_well(scene, kind=kind))
        well.resize(width, well.height_for(width))
        return well

    def send(self, well, kind, x, y, button):
        QtCore = self.QtCore
        event = self.QtGui.QMouseEvent(kind, QtCore.QPointF(x, y), QtCore.QPointF(x + 100.0, y + 200.0),
                                       button, button, QtCore.Qt.NoModifier)
        self.QtWidgets.QApplication.sendEvent(well, event)

    def png(self, name, colour):
        image = self.QtGui.QImage(16, 16, self.QtGui.QImage.Format_RGB32)
        image.fill(self.QtGui.QColor(*colour))
        path = os.path.join(self.temp, name)
        self.assertTrue(image.save(path))
        return path


class SceneRoutes(unittest.TestCase):
    """Scene and WalkScene hand every press to the card (maya_walk.panel), the walk well's to its own presses."""

    NAMES = ("well_rows", "take_card", "pick_card", "remove_card", "remove_all_cards", "clear_card", "show_card",
             "walk_rows", "take_walk_card", "remove_walk_card", "remove_all_walk_cards")

    def setUp(self):
        self.saved = dict((n, getattr(panel, n)) for n in self.NAMES)
        self.calls = []
        for name in self.NAMES:
            setattr(panel, name, (lambda n: lambda *a: self.calls.append((n,) + a) or n)(name))

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(panel, name, value)

    def test_the_pose_well_s_scene_is_the_card_s_pose_presses(self):
        scene = pw.Scene()
        self.assertEqual(scene.cards(), "well_rows")
        self.assertEqual(scene.take("a.pose"), "take_card")
        self.assertEqual(scene.pick("a.pose"), "pick_card")
        self.assertEqual(scene.remove("a.pose"), "remove_card")
        self.assertEqual(scene.remove_all(), "remove_all_cards")
        self.assertEqual(scene.clear(), "clear_card")
        self.assertEqual(scene.show("a.pose"), "show_card")
        self.assertEqual(self.calls, [("well_rows",), ("take_card", "a.pose"), ("pick_card", "a.pose"),
                                      ("remove_card", "a.pose"), ("remove_all_cards",), ("clear_card",),
                                      ("show_card", "a.pose")])

    def test_the_walk_well_s_scene_takes_a_click_as_a_drop_and_has_no_clear(self):
        scene = pw.WalkScene()
        self.assertEqual(scene.cards(), "walk_rows")
        self.assertEqual(scene.take("run.anim"), "take_walk_card")
        self.assertEqual(scene.pick("run.anim"), "take_walk_card")      # a click makes it the cycle: as a drop
        self.assertEqual(scene.remove("run.anim"), "remove_walk_card")
        self.assertEqual(scene.remove_all(), "remove_all_walk_cards")
        self.assertIsNone(scene.clear())                                 # a walk is never "none"
        self.assertEqual(scene.show("run.anim"), "show_card")           # shown in the library as a pose card is
        self.assertNotIn(("clear_card",), self.calls)


class Scale(unittest.TestCase):
    """Scene.scale: Maya's real UI scale, 1 where it cannot say."""

    def setUp(self):
        import maya.cmds
        self.cmds = maya.cmds
        self.had = self.cmds.__dict__.get("mayaDpiSetting")

    def tearDown(self):
        if self.had is None:
            self.cmds.__dict__.pop("mayaDpiSetting", None)
        else:
            self.cmds.mayaDpiSetting = self.had

    def test_the_scale_maya_reports_else_one(self):
        self.cmds.mayaDpiSetting = lambda **kw: 1.5 if kw.get("realScaleValue") else 9.0
        self.assertEqual(pw.Scene().scale(), 1.5)
        self.cmds.mayaDpiSetting = lambda **kw: None
        self.assertEqual(pw.Scene().scale(), 1.0)

        def broken(**kw):
            raise RuntimeError("no UI")
        self.cmds.mayaDpiSetting = broken
        self.assertEqual(pw.Scene().scale(), 1.0)


class Kinds(Qt):

    def test_the_walk_well_says_its_own_texts_and_an_unknown_kind_is_the_pose_well(self):
        walk = self.well(FakeScene(), kind="walk")
        self.assertEqual((walk.kind, walk.objectName()), ("walk", pw.WALK_OBJECT_NAME))
        self.assertIsNone(walk.texts["none"])
        odd = self.well(FakeScene(), kind="armor")
        self.assertEqual((odd.kind, odd.objectName()), ("pose", pw.OBJECT_NAME))

    def test_a_well_made_in_a_popup_copy_wears_the_copy_s_tag(self):
        scope = hubcopy.new_scope("walk")
        try:
            with hubcopy.entered(scope):
                self.assertEqual(pw.scoped_name(pw.OBJECT_NAME), pw.OBJECT_NAME + "_" + scope.tag)
                well = self.well(FakeScene())
            self.assertEqual(well.objectName(), pw.OBJECT_NAME + "_" + scope.tag)
            self.assertEqual(pw.scoped_name(pw.OBJECT_NAME), pw.OBJECT_NAME)
        finally:
            hubcopy.close(scope, cmds=object())

    def test_the_walk_well_s_menu_has_no_none_row_and_a_pose_well_s_none_waits_for_an_active_card(self):
        walk = self.well(FakeScene([("C:/l/run.anim", "run", "", "", True)]), kind="walk")
        self.assertEqual([row[0] for row in walk.context_actions(0) if row],
                         ["Use this cycle", pw.SHOW, pw.REMOVE, pw.REMOVE_ALL])
        pose = self.well(FakeScene([("C:/l/a.pose", "a", "", "", False)]))
        rows = dict(row for row in pose.context_actions() if row)
        self.assertIsNone(rows[pw.NONE])                                    # none active: nothing to clear
        self.assertIsNotNone(rows[pw.REMOVE_ALL])
        beyond = pose.context_actions(7)                                     # a row past the cards: the well's
        self.assertEqual([row[0] for row in beyond], [pw.NONE, pw.REMOVE_ALL])
        self.assertIsNone(beyond[0][1])


class Drawing(Qt):

    def test_a_thumbnail_is_drawn_in_its_square_and_a_missing_one_is_a_figure(self):
        red = self.png("red.png", (255, 0, 0))
        scene = FakeScene([("C:/l/red.pose", "red", red, "", True),
                           ("C:/l/gone.pose", "gone", os.path.join(self.temp, "none.png"),
                            "the card is gone from the library", False)])
        well = self.well(scene)
        self.assertFalse(well.rows[0][2].isNull())
        self.assertIsNone(well.rows[1][2])
        image = well.grab().toImage()
        pixel = image.pixelColor(int(5 + pw.ROW / 2.0), int(pw.ROW / 2.0))     # the square's middle, row 0
        self.assertEqual((pixel.red(), pixel.green(), pixel.blue()), (255, 0, 0))
        middle = image.pixelColor(int(5 + pw.ROW / 2.0), int(pw.ROW + pw.GAP + pw.ROW / 2.0))
        self.assertNotEqual((middle.red(), middle.green(), middle.blue()), (255, 0, 0))   # row 1: no picture
        well.set_hot(True)                                                    # a card dragged over it
        self.assertFalse(well.grab().toImage().isNull())
        well.set_hot(True)                                                    # already lit: nothing to do
        self.assertTrue(well.hot)

    def test_the_well_s_scale_makes_its_rows_and_drop_row_taller(self):
        well = self.well(FakeScene([("C:/l/a.pose", "a", "", "", True)], scale=1.5))
        self.assertEqual(well.height_for(300), int(round(pw.well_height(1) * 1.5)))
        self.assertAlmostEqual(well.row_rect(0).height(), pw.ROW * 1.5 - 1.0)
        self.assertAlmostEqual(well.drop_rect().top(), (pw.ROW + pw.GAP) * 1.5 + 0.5)
        self.assertEqual(well.row_at(self.QtCore.QPoint(10, int(pw.ROW * 1.5) - 2)), 0)
        self.assertIsNone(well.row_at(self.QtCore.QPoint(10, int(pw.ROW * 1.5) + 2)))   # the gap, scaled
        hint = well.sizeHint()
        self.assertEqual((hint.width(), hint.height()), (well.width(), well.height_for(well.width())))

    def test_an_empty_well_is_one_drop_strip(self):
        well = self.well(FakeScene())
        well.resize(200, pw.HEIGHT)
        rect = well.drop_rect()
        self.assertEqual((rect.width(), rect.height()), (199.0, pw.HEIGHT - 1.0))
        self.assertEqual((well.path, well.name), ("", ""))


class Input(Qt):

    def setUp(self):
        Qt.setUp(self)
        self.scene = FakeScene([("C:/l/sword.pose", "sword", "", "", False),
                                ("C:/l/goblin.pose", "goblin", "", "", True)])
        self.w = self.well(self.scene)
        self.w.show()
        self.Qt = self.QtCore.Qt
        self.press, self.double = self.QtCore.QEvent.MouseButtonPress, self.QtCore.QEvent.MouseButtonDblClick

    def test_a_click_on_a_card_picks_it_and_a_click_between_or_below_does_nothing(self):
        self.send(self.w, self.press, 20, 10, self.Qt.LeftButton)
        self.assertEqual(self.scene.made("pick"), [("pick", "C:/l/sword.pose")])
        self.assertEqual(self.w.path, "C:/l/sword.pose")                      # read again after the press
        self.send(self.w, self.press, 20, pw.ROW + 1, self.Qt.LeftButton)       # the gap
        self.send(self.w, self.press, 20, 2 * (pw.ROW + pw.GAP) + 5, self.Qt.LeftButton)   # the drop row
        self.send(self.w, self.press, 20, 10, self.Qt.LeftButton)               # the active card again
        self.assertEqual(len(self.scene.made("pick")), 1)

    def test_the_right_button_opens_the_card_s_menu_where_it_was_pressed(self):
        self.send(self.w, self.press, 20, pw.ROW + pw.GAP + 10, self.Qt.RightButton)
        parent, point, actions = self.menus[-1]
        self.assertIs(parent, self.w)
        self.assertEqual((point.x(), point.y()), (120, 200 + pw.ROW + pw.GAP + 10))
        self.assertEqual([row[0] for row in actions if row], [pw.USE, pw.SHOW, pw.REMOVE, pw.NONE, pw.REMOVE_ALL])
        self.assertIsNone(dict(row for row in actions if row)[pw.USE])          # goblin is the active one
        self.send(self.w, self.press, 20, 2 * (pw.ROW + pw.GAP) + 5, self.Qt.RightButton)   # under the cards
        self.assertEqual([row[0] for row in self.menus[-1][2] if row], [pw.NONE, pw.REMOVE_ALL])
        self.assertEqual(self.scene.made("pick"), [])                          # the right button picks nothing

    def test_a_double_click_shows_the_card_in_the_library(self):
        self.send(self.w, self.double, 20, 10, self.Qt.LeftButton)
        self.assertEqual(self.scene.made("show"), [("show", "C:/l/sword.pose")])
        self.send(self.w, self.double, 20, 2 * (pw.ROW + pw.GAP) + 5, self.Qt.LeftButton)   # the drop row
        self.send(self.w, self.double, 20, 10, self.Qt.RightButton)
        self.assertEqual(len(self.scene.made("show")), 1)

    def test_a_qt5_event_without_position_is_read_by_its_pos(self):
        QtCore = self.QtCore

        class Old(object):
            def __init__(self, button, y):
                self._button, self._y = button, y

            def pos(self):
                return QtCore.QPoint(15, self._y)

            def globalPos(self):                                          # noqa: N802
                return QtCore.QPoint(1, 2)

            def button(self):
                return self._button
        self.w.mousePressEvent(Old(self.Qt.LeftButton, 10))
        self.assertEqual(self.scene.made("pick"), [("pick", "C:/l/sword.pose")])
        self.w.mousePressEvent(Old(self.Qt.RightButton, 10))
        self.assertEqual((self.menus[-1][1].x(), self.menus[-1][1].y()), (1, 2))
        self.w.mouseDoubleClickEvent(Old(self.Qt.LeftButton, pw.ROW + pw.GAP + 3))
        self.assertEqual(self.scene.made("show"), [("show", "C:/l/goblin.pose")])

    def test_the_menu_s_rows_do_what_they_say(self):
        rows = dict(row for row in self.w.context_actions(0) if row)
        self.assertEqual(rows[pw.USE](), "picked C:/l/sword.pose")
        rows[pw.SHOW]()
        rows[pw.REMOVE]()                                                      # the active one, gone
        self.assertEqual([r[0] for r in self.w.rows], ["C:/l/goblin.pose"])
        self.assertIsNone(dict(row for row in self.w.context_actions() if row)[pw.NONE])   # none active now
        self.w.pick(0)
        rows = dict(row for row in self.w.context_actions() if row)
        rows[pw.NONE]()                                                        # none active, the card kept
        self.assertEqual((self.w.path, len(self.w.rows)), ("", 1))
        rows[pw.REMOVE_ALL]()
        self.assertEqual(self.w.rows, [])
        self.assertEqual([c[0] for c in self.scene.calls if c[0] != "cards"],
                         ["pick", "show", "remove", "pick", "clear", "remove_all"])


class Failures(Qt):

    def test_a_scene_that_cannot_list_its_cards_shows_an_empty_well(self):
        scene = FakeScene([("C:/l/a.pose", "a", "", "", True)])
        well = self.well(scene)
        self.assertEqual(len(well.rows), 1)
        scene.fail = "the library is unreachable"
        with hushed():
            well.refresh()
        self.assertEqual(well.rows, [])

    def test_a_press_that_fails_answers_its_error_and_the_well_is_read_again(self):
        scene = FakeScene([("C:/l/a.pose", "a", "", "", False)])
        well = self.well(scene)

        def boom(path):
            raise RuntimeError("boom")
        scene.take = boom
        listed = len(scene.made("cards"))
        with hushed():
            line = well.take("C:/l/b.pose")
        self.assertEqual(line, "RuntimeError: boom")
        self.assertEqual(len(scene.made("cards")), listed + 1)
        self.assertFalse(well.hot)


class KeptOverItsPlaceholder(Qt):

    def test_the_well_fits_its_host_and_keeps_it_as_tall_as_its_column(self):
        host = self.keep(self.QtWidgets.QWidget())
        host.resize(320, 10)
        scene = FakeScene()
        well = self.keep(pw.make_well(scene, host))
        well._host = host
        well.fit(host)
        self.assertEqual((well.width(), host.height()), (320, pw.HEIGHT))
        scene.take("C:/l/a.pose")
        scene.take("C:/l/b.pose")
        well.refresh()                                                        # two cards: the host grows
        self.assertEqual(host.height(), pw.well_height(2))
        self.assertEqual(well.geometry(), host.rect())
        well.fit(host)                                                        # already as tall: unchanged
        self.assertEqual(host.height(), pw.well_height(2))

    def test_a_host_that_cannot_be_fitted_leaves_the_refresh_alone(self):
        well = self.well(FakeScene([("C:/l/a.pose", "a", "", "", True)]))
        well._host = object()                                                 # no rect: fit raises
        well.refresh()
        self.assertEqual(len(well.rows), 1)


class Standing(Qt):
    """attach / live / every / well_at / light / refresh_all: the wells standing over their placeholders."""

    def host(self):
        host = self.keep(self.QtWidgets.QWidget())
        host.resize(300, 20)
        host.show()
        return host

    def test_no_qt_or_no_placeholder_lays_no_well(self):
        maya_hubqt.qt = lambda: None
        self.assertIsNone(pw.attach("skeldarWalkPoseWell", scene=FakeScene()))
        maya_hubqt.qt = self.saved["qt"]
        maya_hubqt.find = lambda name, layout=False: None
        self.assertIsNone(pw.attach("skeldarWalkPoseWell", scene=FakeScene()))
        self.assertEqual(pw.every(), [])
        self.assertIsNone(pw.well_at(0, 0))                                   # no well: no lookup at all

    def test_a_well_laid_over_its_placeholder_stands_and_is_found_under_a_point(self):
        host = self.host()
        found = []
        maya_hubqt.find = lambda name, layout=False: found.append((name, layout)) or host
        scene = FakeScene([("C:/l/a.pose", "a", "", "", True)])
        well = pw.attach("skeldarWalkPoseWell", scene=scene)
        self.keep(well)
        self.assertEqual(found, [("skeldarWalkPoseWell", True)])
        self.assertIs(well.parent(), host)
        self.assertIs(well.scene, scene)                                      # no copy current: as it is
        self.assertEqual((host.height(), well.isVisible()), (pw.well_height(1), True))
        self.assertIs(pw.live("skeldarWalkPoseWell"), well)
        self.assertEqual(pw.every(), [well])
        inside = well.mapToGlobal(self.QtCore.QPoint(10, 10))
        self.assertIs(pw.well_at(inside.x(), inside.y()), well)
        outside = well.mapToGlobal(self.QtCore.QPoint(10, well.height() + 50))
        self.assertIsNone(pw.well_at(outside.x(), outside.y()))
        host.resize(410, 20)                                                  # Maya's layout gives a new width
        self.app.processEvents()
        self.assertEqual((well.width(), host.height()), (410, pw.well_height(1)))

    def test_light_lights_one_well_and_refresh_all_reads_every_one_again(self):
        first, second = self.host(), self.host()
        hosts = {"skeldarWalkPoseWell": first, "skeldarWalkCycleWell": second}
        maya_hubqt.find = lambda name, layout=False: hosts[name]
        pose, cycle = FakeScene(), FakeScene()
        a = self.keep(pw.attach("skeldarWalkPoseWell", scene=pose))
        b = self.keep(pw.attach("skeldarWalkCycleWell", scene=cycle, kind="walk"))
        pw.light(b)
        self.assertEqual((a.hot, b.hot), (False, True))
        pw.light(None)
        self.assertEqual((a.hot, b.hot), (False, False))
        before = (len(pose.made("cards")), len(cycle.made("cards")))
        pw.refresh_all()
        self.assertEqual((len(pose.made("cards")), len(cycle.made("cards"))), (before[0] + 1, before[1] + 1))

    def test_a_well_that_raises_is_passed_by_and_the_others_still_answer(self):
        first, second = self.host(), self.host()
        hosts = {"skeldarWalkPoseWell": first, "skeldarWalkCycleWell": second}
        maya_hubqt.find = lambda name, layout=False: hosts[name]
        a = self.keep(pw.attach("skeldarWalkPoseWell", scene=FakeScene()))
        b = self.keep(pw.attach("skeldarWalkCycleWell", scene=FakeScene(), kind="walk"))

        def broken(*_):
            raise RuntimeError("half deleted")
        a.set_hot = a.refresh = a.isVisible = broken
        pw.light(b)
        self.assertTrue(b.hot)
        pw.refresh_all()
        inside = b.mapToGlobal(self.QtCore.QPoint(5, 5))
        self.assertIs(pw.well_at(inside.x(), inside.y()), b)

    def test_a_deleted_well_is_no_longer_standing(self):
        host = self.host()
        maya_hubqt.find = lambda name, layout=False: host
        well = pw.attach("skeldarWalkPoseWell", scene=FakeScene())
        self.assertIs(pw.live("skeldarWalkPoseWell"), well)
        self.q.shiboken.delete(well)
        self.assertIsNone(pw.live("skeldarWalkPoseWell"))
        self.assertNotIn("skeldarWalkPoseWell", pw._WELLS)
        pw._WELLS["stale"] = well                                             # a dead one left behind
        self.assertEqual(pw.every(), [])
        self.assertNotIn("stale", pw._WELLS)

    def test_where_qt_cannot_be_reached_no_well_is_alive_or_found(self):
        host = self.host()
        maya_hubqt.find = lambda name, layout=False: host
        well = self.keep(pw.attach("skeldarWalkPoseWell", scene=FakeScene()))
        inside = well.mapToGlobal(self.QtCore.QPoint(5, 5))
        saved = pw._classes

        def gone():
            raise RuntimeError("Qt is gone")
        pw._classes = gone
        try:
            self.assertFalse(pw._alive(well))
            self.assertIsNone(pw.well_at(inside.x(), inside.y()))
        finally:
            pw._classes = saved
        self.assertIs(pw.well_at(inside.x(), inside.y()), well)

    def test_a_well_without_a_scene_takes_the_card_s_and_a_walk_well_the_walk_presses(self):
        host = self.host()
        maya_hubqt.find = lambda name, layout=False: host
        saved = panel.walk_rows, panel.well_rows
        panel.walk_rows = lambda: [("C:/l/run.anim", "run", "", "", True)]
        panel.well_rows = lambda: []
        try:
            cycle = self.keep(pw.attach("skeldarWalkCycleWell", kind="walk"))
            pose = self.keep(pw.attach("skeldarWalkPoseWell"))
        finally:
            panel.walk_rows, panel.well_rows = saved
        self.assertIsInstance(cycle.scene, pw.WalkScene)
        self.assertEqual(cycle.path, "C:/l/run.anim")
        self.assertIsInstance(pose.scene, pw.Scene)
        self.assertNotIsInstance(pose.scene, pw.WalkScene)

    def test_a_well_in_a_popup_copy_runs_its_presses_in_that_copy(self):
        """A release comes from the Pose Library, outside the copy's scope: the well's scene is bound to the copy
        that laid it, so the card's controls it reaches are the copy's own."""
        host = self.host()
        maya_hubqt.find = lambda name, layout=False: host
        scene = FakeScene()
        scope = hubcopy.new_scope("walk")
        try:
            with hubcopy.entered(scope):
                well = self.keep(pw.attach("skeldarWalkPoseWell", scene=scene))
            self.assertIsInstance(well.scene, hubcopy.Bound)
            self.assertIsNone(hubcopy.current())
            self.assertEqual(well.take("C:/l/a.pose"), "took C:/l/a.pose")
            self.assertIs(scene.made("take")[-1][2], scope)
        finally:
            hubcopy.close(scope, cmds=object())


if __name__ == "__main__":
    unittest.main()

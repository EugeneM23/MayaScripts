"""The Armor card's tiles, the parts test_armorgrid does not reach (2026-10-27):
the registry (`attach`, `live`, `_prune`) and the portraits' Keeper holding the
placeholder as tall as the tiles, a popup copy's own tiles, the real `Scene`
forwarding to the card's functions (maya_scenesetup.armorpanel) and the drop
target's, the drag's captions and refusals, the hover and the leave, and a
missing icon. Offscreen Qt and fakes only - no Maya scene is touched.

Spec: docs/superpowers/specs/2026-10-01-armor-techlimb-design.md
"""
import contextlib
import io
import os
import sys
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

try:
    import maya.cmds  # noqa: F401
    from maya_scenesetup import armorpanel, droptarget
    MAYA = True
except Exception:                                            # noqa: BLE001
    MAYA = False

import maya_armorgrid as ag
import maya_charlook as look
import maya_hubcopy as hubcopy
import maya_hubstyle
from maya_scenesetup import catalog

_MISSING = object()
_HUBCOPY = "_skeldar_hubcopy"


# ------------------------------------------------------------------ helpers

def rebind(test, obj, name, value):
    """`obj.name` = `value` for the length of the test."""
    saved = getattr(obj, name, _MISSING)
    setattr(obj, name, value)

    def put_back():
        if saved is _MISSING:
            delattr(obj, name)
        else:
            setattr(obj, name, saved)
    test.addCleanup(put_back)


def fresh_copies(test):
    """maya_hubcopy's state on `sys` starts empty, and is put back after."""
    saved = getattr(sys, _HUBCOPY, _MISSING)
    setattr(sys, _HUBCOPY, None)

    def put_back():
        if saved is _MISSING:
            if hasattr(sys, _HUBCOPY):
                delattr(sys, _HUBCOPY)
        else:
            setattr(sys, _HUBCOPY, saved)
    test.addCleanup(put_back)


def keep_grids(test):
    saved = dict(ag._GRIDS)

    def put_back():
        ag._GRIDS.clear()
        ag._GRIDS.update(saved)
    test.addCleanup(put_back)


def close_copy(scope):
    hubcopy.close(scope, cmds=types.SimpleNamespace(scriptJob=lambda **_k: None))


def fake_cmds(test, answer):
    """`maya.cmds` swapped (the sys.modules entry and the package attribute)
    for one whose mayaDpiSetting answers `answer` (raises it when it is an
    exception). Returns the calls' kwargs."""
    import maya
    import maya.cmds as real
    calls = []

    def mayaDpiSetting(**kwargs):                            # noqa: N802
        calls.append(kwargs)
        if isinstance(answer, Exception):
            raise answer
        return answer
    fake = types.ModuleType("maya.cmds")
    fake.mayaDpiSetting = mayaDpiSetting
    saved_entry = sys.modules["maya.cmds"]
    saved_attr = getattr(maya, "cmds", real)
    sys.modules["maya.cmds"] = fake
    maya.cmds = fake

    def put_back():
        sys.modules["maya.cmds"] = saved_entry
        maya.cmds = saved_attr
    test.addCleanup(put_back)
    return calls


class BrokenShiboken(object):
    """shiboken with an isValid that raises (everything else the real one's)."""

    def __init__(self, real):
        self._real = real

    def isValid(self, _obj):                                 # noqa: N802
        raise RuntimeError("shiboken is gone")

    def __getattr__(self, name):
        return getattr(self._real, name)


class FakeScene(object):

    def __init__(self, worn=()):
        self.log = []
        self.worn_keys = set(worn)
        self.aim = dict(kind="character", root="|Manny_Rig:root", label="Manny_Rig",
                        text="onto Manny_Rig")
        self.hub = False
        self.fail = {}                                       # method -> exception

    def _maybe_fail(self, name):
        if name in self.fail:
            raise self.fail[name]

    def scale(self):
        return 1.0

    def select(self, key):
        scope = hubcopy.current()
        self.log.append(("select", key, scope.tag if scope else None))

    def open_scene(self, key):
        self.log.append(("open_scene", key))
        self._maybe_fail("open_scene")
        return "opened " + key

    def worn(self):
        self._maybe_fail("worn")
        return set(self.worn_keys)

    def say(self, text):
        self.log.append(("say", text))

    def snapshot(self):
        self.log.append(("snapshot",))
        self._maybe_fail("snapshot")
        return ["snap"]

    def target(self, gx, gy, snap):
        self.log.append(("target", gx, gy, snap))
        self._maybe_fail("target")
        return self.aim

    def over_hub(self, gx, gy):
        return self.hub

    def equip_on(self, root, key):
        self.log.append(("equip_on", root, key))
        return "%s on %s" % (key, root)


class FakeClock(object):

    def __init__(self, elapsed):
        self.value = elapsed
        self.restarts = 0

    def elapsed(self):
        return self.value

    def restart(self):
        self.restarts += 1
        return self.value


def app():
    return QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])


def render(widget):
    image = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


def near(colour, hexname, tolerance=12):
    want = QT.QtGui.QColor(hexname)
    return (abs(colour.red() - want.red()) <= tolerance
            and abs(colour.green() - want.green()) <= tolerance
            and abs(colour.blue() - want.blue()) <= tolerance)


@contextlib.contextmanager
def quiet():
    """The traceback the tiles print on a failing scene, kept off the run's output."""
    with contextlib.redirect_stderr(io.StringIO()):
        yield


# --------------------------------------------------------------- the seams

class Seams(unittest.TestCase):

    def setUp(self):
        fresh_copies(self)

    def test_last_line_is_the_error_and_failed_for_nothing(self):
        self.assertEqual(ag._last_line("Traceback (most recent call last):\n  x\n"
                                       "RuntimeError: not a character\n"),
                         "RuntimeError: not a character")
        self.assertEqual(ag._last_line(" \n "), "failed")
        self.assertEqual(ag._last_line(None), "failed")

    def test_scoped_name_follows_the_scope_entered(self):
        scope = hubcopy.new_scope("weapons")
        self.assertEqual(ag.scoped_name(ag.OBJECT_NAME), ag.OBJECT_NAME)
        with hubcopy.entered(scope):
            self.assertEqual(ag.scoped_name(ag.OBJECT_NAME), ag.OBJECT_NAME + "_" + scope.tag)

    def test_key_is_the_name_outside_and_the_copys_own_inside(self):
        scope = hubcopy.new_scope("weapons")
        scope.names["mayaSceneSetupArmorTiles"] = scope.prefix + "mayaSceneSetupArmorTiles"
        self.assertEqual(ag._key("mayaSceneSetupArmorTiles"), "mayaSceneSetupArmorTiles")
        with hubcopy.entered(scope):
            self.assertEqual(ag._key("mayaSceneSetupArmorTiles"),
                             scope.prefix + "mayaSceneSetupArmorTiles")


# --------------------------------------------------------------- the scene

@unittest.skipUnless(MAYA, "no maya")
class RealScene(unittest.TestCase):
    """`Scene` is the tiles' one door to Maya: each call goes to the Armor
    card's own function or the drop target's."""

    def setUp(self):
        self.done = []
        self.dpi = fake_cmds(self, 1.5)

    def test_scale_is_mayas_real_ui_scale(self):
        self.assertEqual(ag.Scene().scale(), 1.5)
        self.assertEqual(self.dpi, [dict(query=True, realScaleValue=True)])

    def test_scale_is_one_when_maya_answers_nothing_or_cannot_say(self):
        fake_cmds(self, None)
        self.assertEqual(ag.Scene().scale(), 1.0)
        fake_cmds(self, RuntimeError("batch"))
        self.assertEqual(ag.Scene().scale(), 1.0)

    def test_the_card_presses_go_to_the_armor_card(self):
        rebind(self, armorpanel, "select_armor", lambda key: self.done.append(("select", key)))
        rebind(self, armorpanel, "open_armor_scene",
               lambda key: self.done.append(("open", key)) or "opened")
        rebind(self, armorpanel, "worn_keys", lambda: {"Tech_Limb"})
        rebind(self, armorpanel, "equip_on",
               lambda root, key: self.done.append(("equip", root, key)) or "equipped")
        scene = ag.Scene()
        self.assertIsNone(scene.select("Tech_Limb"))
        self.assertEqual(scene.open_scene("Playerchar_Helmet"), "opened")
        self.assertEqual(scene.worn(), {"Tech_Limb"})
        self.assertEqual(scene.equip_on("|root", "Playerchar_Pants"), "equipped")
        self.assertEqual(self.done, [("select", "Tech_Limb"), ("open", "Playerchar_Helmet"),
                                     ("equip", "|root", "Playerchar_Pants")])

    def test_the_drop_target_is_the_characters_under_the_point(self):
        rebind(self, droptarget, "snapshot", lambda: ["bones"])
        rebind(self, droptarget, "character_target",
               lambda gx, gy, snap, scale: self.done.append((gx, gy, snap, scale))
               or dict(kind="character", root="|root"))
        scene = ag.Scene()
        snap = scene.snapshot()
        self.assertEqual(snap, ["bones"])
        self.assertEqual(scene.target(10, 20, snap), dict(kind="character", root="|root"))
        self.assertEqual(self.done, [(10, 20, ["bones"], 1.5)])

    def test_over_hub_asks_the_hub(self):
        asked = []
        rebind(self, maya_hubqt, "on_hub", lambda *args: asked.append(args) or True)
        self.assertTrue(ag.Scene().over_hub(5, 6))
        self.assertEqual(asked, [(5, 6)])

    def test_say_writes_the_cards_line_and_swallows_a_failure(self):
        said = []
        rebind(self, armorpanel, "say", said.append)
        ag.Scene().say("Tech Limb on Manny_Rig")
        self.assertEqual(said, ["Tech Limb on Manny_Rig"])

        def broken(_text):
            raise RuntimeError("no card")
        armorpanel.say = broken
        ag.Scene().say("Tech Limb on Manny_Rig")             # no raise


# ---------------------------------------------------- the registry, attach

@unittest.skipIf(QT is None, "no Qt")
class Registry(unittest.TestCase):

    def setUp(self):
        app()
        keep_grids(self)
        ag._classes()
        self.scene = FakeScene()

    def tiles(self):
        grid = ag.make_grid(self.scene)
        self.addCleanup(lambda: QT.shiboken.isValid(grid) and grid.deleteLater())
        return grid

    def test_prune_drops_closed_tiles_and_keeps_standing_ones(self):
        standing, gone = self.tiles(), ag.make_grid(self.scene)
        ag._GRIDS.clear()
        ag._GRIDS.update(standing=standing, gone=gone)
        QT.shiboken.delete(gone)
        ag._prune()
        self.assertEqual(sorted(ag._GRIDS), ["standing"])

    def test_prune_drops_tiles_it_cannot_ask_about(self):
        ag._GRIDS.clear()
        ag._GRIDS["odd"] = self.tiles()
        rebind(self, QT, "shiboken", BrokenShiboken(QT.shiboken))
        ag._prune()
        self.assertEqual(ag._GRIDS, {})

    def test_live_answers_the_standing_tiles_and_forgets_closed_ones(self):
        standing = self.tiles()
        ag._GRIDS["mayaSceneSetupArmorTiles"] = standing
        self.assertIs(ag.live("mayaSceneSetupArmorTiles"), standing)
        self.assertIsNone(ag.live("nothingHere"))
        QT.shiboken.delete(standing)
        self.assertIsNone(ag.live("mayaSceneSetupArmorTiles"))
        self.assertNotIn("mayaSceneSetupArmorTiles", ag._GRIDS)

    def test_live_forgets_tiles_it_cannot_ask_about(self):
        ag._GRIDS["mayaSceneSetupArmorTiles"] = self.tiles()

        def broken():
            raise RuntimeError("no Qt")
        rebind(self, ag, "_classes", broken)
        self.assertIsNone(ag.live("mayaSceneSetupArmorTiles"))
        self.assertNotIn("mayaSceneSetupArmorTiles", ag._GRIDS)

    def test_the_keeper_is_the_portraits(self):
        import maya_chargrid
        self.assertIs(ag._classes()["Keeper"], maya_chargrid._classes()["Keeper"])


@unittest.skipIf(QT is None, "no Qt")
class Attach(unittest.TestCase):
    """The portraits' pattern: the tiles laid OVER Maya's placeholder, the
    placeholder kept as tall as the tiles."""

    def setUp(self):
        app()
        keep_grids(self)
        fresh_copies(self)
        self.scene = FakeScene(worn={"Tech_Limb"})
        self.window = QT.QtWidgets.QWidget()
        self.window.resize(500, 400)
        self.addCleanup(self.window.deleteLater)
        self.host = QT.QtWidgets.QWidget(self.window)
        self.host.setGeometry(0, 0, 330, 10)
        self.window.show()
        self.found = []

        def find(name, layout=False):
            self.found.append((name, layout))
            return self.host
        rebind(self, maya_hubqt, "find", find)

    def test_no_qt_no_tiles(self):
        rebind(self, maya_hubqt, "qt", lambda: None)
        self.assertIsNone(ag.attach("mayaSceneSetupArmorTiles", self.scene))
        self.assertEqual(self.found, [])

    def test_no_placeholder_no_tiles(self):
        maya_hubqt.find = lambda name, layout=False: None
        before = dict(ag._GRIDS)
        self.assertIsNone(ag.attach("mayaSceneSetupArmorTiles", self.scene))
        self.assertEqual(ag._GRIDS, before)

    def test_the_tiles_are_laid_over_their_placeholder_and_registered(self):
        grid = ag.attach("mayaSceneSetupArmorTiles", self.scene, selected="Tech_Limb")
        self.assertEqual(self.found, [("mayaSceneSetupArmorTiles", True)])
        self.assertIs(grid.parentWidget(), self.host)
        self.assertEqual(self.host.height(), grid.height_for(330))
        self.assertEqual(grid.geometry(), self.host.rect())
        self.assertTrue(grid.isVisible())
        self.assertEqual(grid.selected, "Tech_Limb")
        self.assertEqual(grid.worn, {"Tech_Limb"})           # read on arrival
        self.assertIs(grid.scene, self.scene)
        self.assertIs(ag.live("mayaSceneSetupArmorTiles"), grid)

    def test_a_resized_placeholder_is_kept_as_tall_as_the_tiles(self):
        grid = ag.attach("mayaSceneSetupArmorTiles", self.scene)
        want = grid.height_for(140)
        self.assertNotEqual(want, grid.height_for(330))      # the resize must matter
        self.host.resize(140, self.host.height())
        QT.QtWidgets.QApplication.processEvents()
        self.assertEqual(self.host.height(), want)
        self.assertEqual(grid.geometry(), self.host.rect())

    @unittest.skipUnless(MAYA, "no maya")
    def test_without_a_scene_the_tiles_get_the_real_one(self):
        fake_cmds(self, 1.25)
        rebind(self, armorpanel, "worn_keys", lambda: {"Playerchar_Pants"})
        grid = ag.attach("mayaSceneSetupArmorTiles")
        self.assertIsInstance(grid.scene, ag.Scene)
        self.assertEqual(grid.k, 1.25)
        self.assertEqual(grid.worn, {"Playerchar_Pants"})

    def test_new_tiles_clear_the_closed_ones_out_of_the_registry(self):
        gone = ag.make_grid(self.scene)
        ag._GRIDS["closedCopyTiles"] = gone
        QT.shiboken.delete(gone)
        ag.attach("mayaSceneSetupArmorTiles", self.scene)
        self.assertNotIn("closedCopyTiles", ag._GRIDS)

    def test_a_popup_copys_tiles_are_its_own(self):
        scope = hubcopy.new_scope("weapons")
        mine = scope.prefix + "mayaSceneSetupArmorTiles"
        scope.names["mayaSceneSetupArmorTiles"] = mine
        with hubcopy.entered(scope):
            grid = ag.attach("mayaSceneSetupArmorTiles", self.scene)
            self.assertIs(ag.live("mayaSceneSetupArmorTiles"), grid)
        self.assertIn(mine, ag._GRIDS)
        self.assertIsNone(ag.live("mayaSceneSetupArmorTiles"))
        self.assertEqual(grid.objectName(), ag.OBJECT_NAME + "_" + scope.tag)
        self.assertTrue(grid.select("Tech_Limb"))            # a click, from Qt
        self.assertIn(("select", "Tech_Limb", scope.tag), self.scene.log)
        close_copy(scope)
        grid.select("Playerchar_Helmet")
        self.assertNotIn("Playerchar_Helmet", [e[1] for e in self.scene.log if e[0] == "select"])


# ------------------------------------------------------------- the tiles

@unittest.skipIf(QT is None, "no Qt")
class TilesMore(unittest.TestCase):

    def setUp(self):
        app()
        self.scene = FakeScene()
        self.grid = ag.make_grid(self.scene, selected=None)
        self.grid.resize(330, self.grid.height_for(330))
        self.grid.move(3000, 3000)
        self.addCleanup(self.grid.deleteLater)
        self.addCleanup(self.grid._end)

    def centre(self, index):
        x, y, w, h = self.grid.rects()[index]
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)

    def acts(self, name):
        return [e for e in self.scene.log if e[0] == name]

    def mouse(self, kind, local, button, buttons):
        g = self.grid.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    def start(self, key="Tech_Limb", point=None):
        point = point or QT.QtCore.QPoint(500, 500)          # off the tiles (at 3000)
        self.grid._start(key, point)
        return point

    # ------------------------------------------------------------ layout
    def test_fit_lays_the_tiles_over_the_host_and_grows_it(self):
        host = QT.QtWidgets.QWidget()
        self.addCleanup(host.deleteLater)
        host.resize(330, 10)
        grid = ag.make_grid(self.scene, parent=host)
        grid.fit(host)
        self.assertEqual(host.height(), grid.height_for(330))
        self.assertEqual(grid.geometry(), host.rect())
        grid.fit(host)                                       # already as tall: as it is
        self.assertEqual(host.height(), grid.height_for(330))

    def test_the_size_hint_at_no_width(self):
        self.grid.resize(0, 0)
        self.assertEqual(self.grid.sizeHint(), QT.QtCore.QSize(1, self.grid.height_for(1)))

    # ------------------------------------------------------------- state
    def test_an_unknown_tile_cannot_be_picked(self):
        self.assertFalse(self.grid.select("NoSuchArmor"))
        self.assertFalse(self.grid.select(None))
        self.assertIsNone(self.grid.selected)
        self.assertEqual(self.acts("select"), [])

    def test_refresh_takes_what_the_caller_read(self):
        self.grid.refresh(worn=("Playerchar_Pants", "Tech_Limb"))
        self.assertEqual(self.grid.worn, {"Playerchar_Pants", "Tech_Limb"})
        self.grid.refresh(worn=())
        self.assertEqual(self.grid.worn, set())

    def test_a_scene_that_cannot_say_what_is_worn_shows_nothing_worn(self):
        self.grid.refresh(worn=("Tech_Limb",))
        self.scene.fail["worn"] = RuntimeError("no character")
        with quiet():
            self.grid.refresh()
        self.assertEqual(self.grid.worn, set())

    def test_a_failing_press_says_its_error(self):
        self.scene.fail["open_scene"] = RuntimeError("the file is gone")
        with quiet():
            text = self.grid.context_actions("Tech_Limb")[0][1]()
        self.assertEqual(text, "RuntimeError: the file is gone")
        self.assertEqual(self.acts("say"), [("say", "RuntimeError: the file is gone")])

    def test_a_drop_with_nothing_dragged_does_nothing(self):
        self.grid.status_text = "Tech Limb - press Equip"
        self.assertEqual(self.grid.drop_at(500, 500), "Tech Limb - press Equip")
        self.assertEqual(self.acts("target"), [])

    def test_a_drop_during_a_drag_reads_its_snapshot_not_a_new_one(self):
        self.start()
        self.assertEqual(len(self.acts("snapshot")), 1)
        self.grid.drop_at(500, 500)                          # the dragged row
        self.assertEqual(len(self.acts("snapshot")), 1)
        self.assertEqual(self.acts("equip_on"), [("equip_on", "|Manny_Rig:root", "Tech_Limb")])

    def test_a_drop_with_no_text_says_no_target(self):
        self.scene.aim = dict(kind="none")
        self.assertEqual(self.grid.drop_at(500, 500, "Tech_Limb"), "no target")
        self.assertIn(("say", "no target"), self.scene.log)

    # -------------------------------------------------------------- drag
    def test_a_drag_with_no_characters_to_read_still_starts(self):
        self.scene.fail["snapshot"] = RuntimeError("no viewport")
        with quiet():
            self.start()
        self.assertIsNotNone(self.grid._drag)
        self.assertEqual(self.grid._drag["snap"], [])
        self.assertIn(("target", 500, 500, []), self.scene.log)

    def test_a_drag_survives_a_keyboard_it_cannot_grab_or_give_back(self):
        def broken():
            raise RuntimeError("no keyboard")
        self.grid.grabKeyboard = broken
        self.grid.releaseKeyboard = broken
        self.start()
        self.assertIsNotNone(self.grid._drag)
        self.grid._end()
        self.assertIsNone(self.grid._drag)

    def test_no_caption_without_a_drag(self):
        self.grid._caption(QT.QtCore.QPoint(500, 500), force=True)
        self.assertEqual(self.acts("target"), [])

    def test_over_a_character_the_caption_names_the_piece_and_him(self):
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), ("Tech Limb %s onto Manny_Rig" % look.DOT, True))

    def test_back_on_the_hub_the_caption_says_release_off_it(self):
        self.scene.hub = True
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), (ag.OFF_HUB, False))
        self.assertEqual(self.acts("target"), [])

    def test_back_on_the_tiles_the_caption_says_release_off_the_hub(self):
        self.start(point=self.grid.mapToGlobal(self.centre(1)))
        self.assertEqual(self.grid._drag["ghost"].text, ag.OFF_HUB)

    def test_off_every_character_the_caption_warns(self):
        self.scene.aim = dict(kind="none", text="drop onto a character")
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), ("drop onto a character", False))

    def test_a_failing_scene_shows_its_error_on_the_caption(self):
        self.scene.fail["target"] = RuntimeError("no camera under the cursor")
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good),
                         ("RuntimeError: no camera under the cursor", False))

    def test_a_move_during_a_drag_carries_the_ghost_and_reads_the_caption_again(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        self.start()
        ghost = self.grid._drag["ghost"]
        where = ghost.pos()
        self.scene.aim = dict(kind="none", text="drop onto a character")
        self.grid._clock = FakeClock(look.THROTTLE_MS - 1)   # too soon: not read again
        self.mouse(E.MouseMove, QT.QtCore.QPoint(-2700, -2700), N, L)
        self.assertNotEqual(ghost.pos(), where)
        self.assertEqual(ghost.text, "Tech Limb %s onto Manny_Rig" % look.DOT)
        self.grid._clock = FakeClock(look.THROTTLE_MS)
        self.mouse(E.MouseMove, QT.QtCore.QPoint(-2600, -2700), N, L)
        self.assertEqual(ghost.text, "drop onto a character")

    def test_a_short_pull_is_no_drag(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(0)
        self.mouse(E.MouseButtonPress, start, L, L)
        self.mouse(E.MouseMove, start + QT.QtCore.QPoint(1, 0), N, L)
        self.assertIsNone(self.grid._drag)
        self.assertIsNotNone(self.grid._press)
        self.mouse(E.MouseButtonRelease, start + QT.QtCore.QPoint(1, 0), L, N)
        self.assertIsNone(self.grid._press)

    # ------------------------------------------------------------- mouse
    def test_the_right_button_runs_the_menu_and_picks_nothing(self):
        shown = []
        rebind(self, maya_hubqt, "run_menu", lambda parent, point, actions: shown.append(
            (parent, [label for label, _fn in actions])))
        E, R = QT.QtCore.QEvent, QT.QtCore.Qt.RightButton
        self.mouse(E.MouseButtonPress, self.centre(0), R, R)
        x, y, w, h = self.grid.rects()[0]
        self.mouse(E.MouseButtonPress, QT.QtCore.QPoint(x + w + 1, y + h // 2), R, R)
        self.assertEqual(shown, [(self.grid, [ag.OPEN_SCENE]), (self.grid, [])])
        self.assertEqual(self.acts("select"), [])
        self.assertIsNone(self.grid._press)

    def test_the_tile_under_the_mouse_is_hovered_until_the_mouse_leaves(self):
        E, N = QT.QtCore.QEvent, QT.QtCore.Qt.NoButton
        self.mouse(E.MouseMove, self.centre(1), N, N)
        self.assertEqual(self.grid._hover, self.grid.keys[1])
        QT.QtWidgets.QApplication.sendEvent(self.grid, QT.QtCore.QEvent(E.Leave))
        self.assertIsNone(self.grid._hover)

    def test_leaving_during_a_drag_leaves_the_hover_alone(self):
        E, N = QT.QtCore.QEvent, QT.QtCore.Qt.NoButton
        self.mouse(E.MouseMove, self.centre(1), N, N)
        self.start()
        QT.QtWidgets.QApplication.sendEvent(self.grid, QT.QtCore.QEvent(E.Leave))
        self.assertEqual(self.grid._hover, self.grid.keys[1])

    def test_another_key_during_a_drag_keeps_it(self):
        self.start()
        event = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, QT.QtCore.Qt.Key_A,
                                   QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)
        self.assertIsNotNone(self.grid._drag)
        self.assertEqual(self.acts("say"), [])

    # ------------------------------------------------------------- paint
    def ring_share(self, image, index, token):
        x, y, w, _h = self.grid.rects()[index]
        inset = int(look.RADIUS * self.grid.k) + 2
        row = [image.pixelColor(px, y) for px in range(x + inset, x + w - inset)]
        return sum(1 for c in row if near(c, maya_hubstyle.TOKENS[token], 40)) / float(len(row))

    def test_the_hovered_tile_takes_the_hover_face_and_ring(self):
        self.grid.pixmaps = {}
        x, y, _w, _h = self.grid.rects()[1]
        plain = render(self.grid)
        self.grid._hover = self.grid.keys[1]
        lit = render(self.grid)
        self.assertEqual(plain.pixelColor(x + 6, y + 6).name(), maya_hubstyle.TOKENS["field"])
        self.assertEqual(lit.pixelColor(x + 6, y + 6).name(), maya_hubstyle.TOKENS["hover"])
        self.assertGreater(self.ring_share(lit, 1, "text2"), 0.9)
        self.assertGreater(self.ring_share(plain, 1, "line"), 0.9)

    def test_with_no_icon_to_draw_a_missing_tile_stays_blank(self):
        self.grid.pixmaps = {}
        x, y, w, h = self.grid.rects()[0]

        def inked(image):
            field = maya_hubstyle.TOKENS["field"]
            return sum(1 for px in range(x + w // 4, x + 3 * w // 4)
                       for py in range(y + h // 4, y + h // 2)
                       if image.pixelColor(px, py).name() != field)
        self.assertGreater(inked(render(self.grid)), 0)      # the shield glyph

        def broken(*_args):
            raise RuntimeError("no icon")
        rebind(self, maya_hubqt, "pixmap", broken)
        self.assertEqual(inked(render(self.grid)), 0)


if __name__ == "__main__":
    unittest.main()

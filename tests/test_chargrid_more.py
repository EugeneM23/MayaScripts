"""The Characters card's portrait grid, the parts test_chargrid does not reach
(2026-10-27): the popup copy's scoping (`_named`, `_key`, `run_in`,
`ScopedScene`), the registry (`attach`, `live`, `_prune`) and the Keeper that
holds the placeholder as tall as the grid, the real `Scene` forwarding to the
card's functions, the skill bar's road, the drag's captions, and the paint's
rarer faces (a portrait under the mouse, a pick the switch lacks, a fire with
no picture). Offscreen Qt and fakes only - no Maya scene is touched.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md,
      docs/superpowers/specs/2026-10-02-character-card-fire-design.md
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
    import maya_hubmotion  # noqa: F401
    from maya_scenesetup import droptarget, swap, window
    MAYA = True
except Exception:                                            # noqa: BLE001
    MAYA = False

try:
    import maya_skillbar  # noqa: F401  (in sys.modules, so its entry can be swapped and put back)
    SKILLBAR = True
except Exception:                                            # noqa: BLE001
    SKILLBAR = False

import maya_chargrid as cg
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
    saved = dict(cg._GRIDS)

    def put_back():
        cg._GRIDS.clear()
        cg._GRIDS.update(saved)
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

    def __init__(self):
        self.log = []
        self.aim = dict(kind="floor", point=(120.0, 0.0, -35.0))
        self.fail_target = None

    def scale(self):
        return 1.0

    def begin(self, label=""):
        self.log.append(("begin", label))

    def end(self):
        self.log.append(("end",))

    def target(self, gx, gy):
        self.log.append(("target", gx, gy))
        if self.fail_target:
            raise self.fail_target
        return self.aim

    def over_hub(self, gx, gy):
        return False

    def select(self, model):
        scope = hubcopy.current()
        self.log.append(("select", model, scope.tag if scope else None))

    def place(self, model, kind, point):
        self.log.append(("place", model, kind, point))
        return "placed"

    def swap(self, model, kind, root):
        self.log.append(("swap", model, kind, root))
        return "swapped"

    def open_scene(self, model, kind):
        self.log.append(("open_scene", model, kind))
        return "opened"

    def say(self, text):
        self.log.append(("say", text))


class FakeBar(object):
    """maya_skillbar as the grid sees it."""

    def __init__(self, target=None, fail=False):
        self.target = target
        self.fail = fail
        self.log = []

    def aim(self, gx, gy):
        self.log.append(("aim", gx, gy))
        if self.fail:
            raise RuntimeError("the bar is gone")
        return self.target

    def light(self, target):
        self.log.append(("light", target))
        if self.fail:
            raise RuntimeError("the bar is gone")

    def drop(self, gx, gy, item):
        self.log.append(("drop", gx, gy, item))
        return "skill F2 cell 3: Creep"

    def caption(self, label, target):
        self.log.append(("caption", label, target))
        return "%s %s skill" % (label, look.DOT)


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


def flush_deletes():
    for _ in range(3):
        QT.QtWidgets.QApplication.processEvents()
        QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.DeferredDelete)


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


# ------------------------------------------------------------ popup copies

class Copies(unittest.TestCase):
    """2026-10-09, H1-H3: a popup copy's grid has names of its own and runs
    the scene in its scope."""

    def setUp(self):
        fresh_copies(self)
        self.scope = hubcopy.new_scope("characters")

    def test_named_is_the_base_outside_a_copy_and_tagged_inside(self):
        self.assertEqual(cg._named("skeldarCharacterGhost", None), "skeldarCharacterGhost")
        self.assertEqual(cg._named("skeldarCharacterGhost", self.scope),
                         "skeldarCharacterGhost_" + self.scope.tag)

    def test_scoped_name_follows_the_scope_entered(self):
        self.assertEqual(cg.scoped_name(cg.OBJECT_NAME), cg.OBJECT_NAME)
        with hubcopy.entered(self.scope):
            self.assertEqual(cg.scoped_name(cg.OBJECT_NAME),
                             cg.OBJECT_NAME + "_" + self.scope.tag)

    def test_key_is_the_name_outside_and_the_copys_own_inside(self):
        self.scope.names["mayaSceneSetupPortraits"] = self.scope.prefix + "mayaSceneSetupPortraits"
        self.assertEqual(cg._key("mayaSceneSetupPortraits"), "mayaSceneSetupPortraits")
        with hubcopy.entered(self.scope):
            self.assertEqual(cg._key("mayaSceneSetupPortraits"),
                             self.scope.prefix + "mayaSceneSetupPortraits")
            self.assertEqual(cg._key("unknownLayout"), "unknownLayout")

    def test_run_in_no_scope_calls_straight_through(self):
        seen = []

        def fn(a, b=0):
            seen.append(hubcopy.current())
            return a + b
        self.assertEqual(cg.run_in(None, fn, 2, b=3), 5)
        self.assertEqual(seen, [None])

    def test_run_in_a_live_copy_runs_inside_it_and_leaves(self):
        seen = []
        self.assertEqual(cg.run_in(self.scope, lambda x: seen.append(hubcopy.current()) or x, 7), 7)
        self.assertEqual(seen, [self.scope])
        self.assertIsNone(hubcopy.current())

    def test_run_in_a_closed_copy_runs_nothing(self):
        close_copy(self.scope)
        called = []
        self.assertIsNone(cg.run_in(self.scope, lambda: called.append(1) or "ran"))
        self.assertEqual(called, [])

    def test_a_scoped_scene_runs_its_calls_in_the_copy(self):
        scene = FakeScene()
        scoped = cg.ScopedScene(scene, self.scope)
        scoped.select("Creep")
        self.assertEqual(scene.log, [("select", "Creep", self.scope.tag)])
        self.assertIsNone(hubcopy.current())

    def test_a_scoped_scene_reads_plain_attributes_and_later_replacements(self):
        scene = FakeScene()
        scoped = cg.ScopedScene(scene, self.scope)
        self.assertEqual(scoped.aim, scene.aim)              # not callable: as it is
        scene.place = lambda model, kind, point: "replaced %s" % model
        self.assertEqual(scoped.place("Creep", "rig", (0, 0, 0)), "replaced Creep")

    def test_a_scoped_scene_of_a_closed_copy_does_nothing(self):
        scene = FakeScene()
        scoped = cg.ScopedScene(scene, self.scope)
        close_copy(self.scope)
        self.assertIsNone(scoped.place("Creep", "rig", (0, 0, 0)))
        self.assertEqual(scene.log, [])


# --------------------------------------------------------------- the seams

class Seams(unittest.TestCase):

    def test_last_line_is_the_error_and_failed_for_nothing(self):
        self.assertEqual(cg._last_line("Traceback (most recent call last):\n  x\n"
                                       "RuntimeError: no floor\n\n"), "RuntimeError: no floor")
        self.assertEqual(cg._last_line(""), "failed")
        self.assertEqual(cg._last_line(None), "failed")

    @unittest.skipUnless(MAYA, "no maya_hubmotion")
    def test_the_fire_follows_the_menus_animations_and_burns_when_it_cannot_ask(self):
        import maya_hubmotion
        rebind(self, maya_hubmotion, "enabled", lambda: False)
        self.assertFalse(cg._animations())

        def broken():
            raise RuntimeError("no optionVar")
        maya_hubmotion.enabled = broken
        self.assertTrue(cg._animations())

    @unittest.skipUnless(SKILLBAR, "no maya_skillbar")
    def test_without_a_skill_bar_there_is_no_skill_road(self):
        saved = sys.modules["maya_skillbar"]
        sys.modules["maya_skillbar"] = None                  # the import fails

        def put_back():
            sys.modules["maya_skillbar"] = saved
        self.addCleanup(put_back)
        self.assertIsNone(cg._skillbar())
        self.assertIsNone(cg.skill_aim(10, 20))
        cg.skill_light(("cell", 2, 0, 1))                    # nothing to light, no raise

    def test_a_failing_bar_aims_at_nothing_and_lights_nothing(self):
        bar = FakeBar(target=("cell", 2, 0, 1), fail=True)
        rebind(self, cg, "_skillbar", lambda: bar)
        self.assertIsNone(cg.skill_aim(10, 20))
        cg.skill_light(("cell", 2, 0, 1))
        self.assertEqual([e[0] for e in bar.log], ["aim", "light"])

    def test_a_working_bar_answers_its_target_and_lights_it(self):
        bar = FakeBar(target=("cell", 2, 0, 1))
        rebind(self, cg, "_skillbar", lambda: bar)
        self.assertEqual(cg.skill_aim(10, 20), ("cell", 2, 0, 1))
        cg.skill_light(("tab", 3))
        self.assertEqual(bar.log, [("aim", 10, 20), ("light", ("tab", 3))])


# --------------------------------------------------------------- the scene

@unittest.skipUnless(MAYA, "no maya")
class RealScene(unittest.TestCase):
    """`Scene` is the grid's one door to Maya: each call goes to the card's
    own function (maya_scenesetup.window), the drop target's or the hub's."""

    def setUp(self):
        self.calls = []
        self.dpi = fake_cmds(self, 1.5)
        self.snap = ["snap"]
        self.hit = dict(kind="character", root="|Manny_Rig:root", label="Manny_Rig")

        def snapshot():
            self.calls.append(("snapshot",))
            if isinstance(self.snap, Exception):
                raise self.snap
            return self.snap

        def character_target(gx, gy, snap, scale):
            self.calls.append(("character_target", gx, gy, snap, scale))
            return self.hit

        def floor_at(gx, gy):
            self.calls.append(("floor_at", gx, gy))
            return dict(kind="floor", point=(1.0, 0.0, 2.0))
        rebind(self, droptarget, "snapshot", snapshot)
        rebind(self, droptarget, "character_target", character_target)
        rebind(self, droptarget, "floor_at", floor_at)

    def asked(self, name):
        return [c for c in self.calls if c[0] == name]

    def test_scale_is_mayas_real_ui_scale(self):
        self.assertEqual(cg.Scene().scale(), 1.5)
        self.assertEqual(self.dpi, [dict(query=True, realScaleValue=True)])

    def test_scale_is_one_when_maya_answers_nothing(self):
        fake_cmds(self, None)
        self.assertEqual(cg.Scene().scale(), 1.0)
        fake_cmds(self, 0)
        self.assertEqual(cg.Scene().scale(), 1.0)

    def test_scale_is_one_when_maya_cannot_say(self):
        fake_cmds(self, RuntimeError("batch"))
        self.assertEqual(cg.Scene().scale(), 1.0)

    def test_a_fresh_scene_holds_no_snapshot(self):
        scene = cg.Scene()
        self.assertIsNone(scene._snap)
        self.assertEqual(scene._label, "")

    def test_a_drag_reads_the_characters_once_and_its_end_forgets_them(self):
        scene = cg.Scene()
        scene.begin("Creep [rig]")
        self.assertEqual(scene._snap, ["snap"])
        self.assertEqual(scene._label, "Creep [rig]")
        scene.target(10, 20)
        scene.target(30, 40)
        self.assertEqual(len(self.asked("snapshot")), 1)
        scene.end()
        self.assertIsNone(scene._snap)
        scene.target(10, 20)
        self.assertEqual(len(self.asked("snapshot")), 2)

    def test_a_drag_survives_a_failing_snapshot(self):
        self.snap = RuntimeError("no viewport")
        scene = cg.Scene()
        scene.begin("Creep [rig]")
        self.assertEqual(scene._snap, [])

    def test_over_a_character_the_target_is_a_swap_named_for_both(self):
        scene = cg.Scene()
        scene.begin("Creep [rig]")
        aim = scene.target(10, 20)
        self.assertEqual(aim, dict(kind="swap", root="|Manny_Rig:root", label="Manny_Rig",
                                   text=swap.swap_caption("Manny_Rig", "Creep [rig]")))
        self.assertEqual(self.asked("character_target"),
                         [("character_target", 10, 20, ["snap"], 1.5)])
        self.assertEqual(self.asked("floor_at"), [])

    def test_a_swap_with_no_drag_label_names_it(self):
        aim = cg.Scene().target(10, 20)
        self.assertEqual(aim["text"], swap.swap_caption("Manny_Rig", "it"))

    def test_off_every_character_the_target_is_the_floor(self):
        self.hit = dict(kind="none", text="drop onto a character")
        aim = cg.Scene().target(10, 20)
        self.assertEqual(aim, dict(kind="floor", point=(1.0, 0.0, 2.0)))
        self.assertEqual(self.asked("floor_at"), [("floor_at", 10, 20)])

    def test_with_no_character_in_the_scene_the_floor_is_asked_straight_away(self):
        self.snap = []
        aim = cg.Scene().target(10, 20)
        self.assertEqual(aim["kind"], "floor")
        self.assertEqual(self.asked("character_target"), [])

    def test_a_failing_snapshot_outside_a_drag_falls_to_the_floor(self):
        self.snap = RuntimeError("no viewport")
        aim = cg.Scene().target(10, 20)
        self.assertEqual(aim["kind"], "floor")
        self.assertEqual(self.asked("character_target"), [])

    def test_over_hub_asks_the_hub_by_its_control(self):
        asked = []
        rebind(self, maya_hubqt, "on_hub",
               lambda gx, gy, control="x": asked.append((gx, gy, control)) or True)
        self.assertTrue(cg.Scene().over_hub(5, 6))
        self.assertEqual(asked, [(5, 6, cg.HUB_CONTROL)])

    def test_every_press_goes_to_the_cards_own_function(self):
        done = []
        rebind(self, window, "select_model", lambda model: done.append(("select", model)))
        rebind(self, window, "place_character",
               lambda model, kind, point: done.append(("place", model, kind, point)) or "placed")
        rebind(self, window, "swap_character",
               lambda model, kind, root: done.append(("swap", model, kind, root)) or "swapped")
        rebind(self, window, "open_character_scene",
               lambda model, kind: done.append(("open", model, kind)) or "opened")
        scene = cg.Scene()
        self.assertIsNone(scene.select("Creep"))
        self.assertEqual(scene.place("Creep", "rig", (1, 0, 2)), "placed")
        self.assertEqual(scene.swap("Creep", "skeleton", "|root"), "swapped")
        self.assertEqual(scene.open_scene("Orc_D", "rig"), "opened")
        self.assertEqual(done, [("select", "Creep"), ("place", "Creep", "rig", (1, 0, 2)),
                                ("swap", "Creep", "skeleton", "|root"),
                                ("open", "Orc_D", "rig")])

    def test_say_writes_the_cards_line_and_swallows_a_failure(self):
        said = []
        rebind(self, window, "say_character", said.append)
        cg.Scene().say("Creep added")
        self.assertEqual(said, ["Creep added"])

        def broken(_text):
            raise RuntimeError("no card")
        window.say_character = broken
        cg.Scene().say("Creep added")                        # no raise


# ---------------------------------------------------- the registry, attach

@unittest.skipIf(QT is None, "no Qt")
class Registry(unittest.TestCase):

    def setUp(self):
        app()
        keep_grids(self)
        cg._classes()
        self.scene = FakeScene()

    def grid(self):
        grid = cg.make_grid(self.scene, kind="rig")
        self.addCleanup(lambda: QT.shiboken.isValid(grid) and grid.deleteLater())
        return grid

    def test_prune_drops_a_closed_grid_and_keeps_a_standing_one(self):
        standing, gone = self.grid(), cg.make_grid(self.scene)
        cg._GRIDS.clear()
        cg._GRIDS.update(standing=standing, gone=gone)
        QT.shiboken.delete(gone)
        cg._prune()
        self.assertEqual(sorted(cg._GRIDS), ["standing"])

    def test_prune_drops_a_grid_it_cannot_ask_about(self):
        cg._GRIDS.clear()
        cg._GRIDS["odd"] = self.grid()
        rebind(self, QT, "shiboken", BrokenShiboken(QT.shiboken))
        cg._prune()
        self.assertEqual(cg._GRIDS, {})

    def test_live_answers_the_standing_grid_and_forgets_a_closed_one(self):
        standing = self.grid()
        cg._GRIDS["mayaSceneSetupPortraits"] = standing
        self.assertIs(cg.live("mayaSceneSetupPortraits"), standing)
        self.assertIsNone(cg.live("nothingHere"))
        QT.shiboken.delete(standing)
        self.assertIsNone(cg.live("mayaSceneSetupPortraits"))
        self.assertNotIn("mayaSceneSetupPortraits", cg._GRIDS)

    def test_live_forgets_a_grid_it_cannot_ask_about(self):
        cg._GRIDS["mayaSceneSetupPortraits"] = self.grid()

        def broken():
            raise RuntimeError("no Qt")
        rebind(self, cg, "_classes", broken)
        self.assertIsNone(cg.live("mayaSceneSetupPortraits"))
        self.assertNotIn("mayaSceneSetupPortraits", cg._GRIDS)


@unittest.skipIf(QT is None, "no Qt")
class Attach(unittest.TestCase):
    """`attach` lays the grid OVER Maya's placeholder (its layouts place
    their own children) and keeps the placeholder as tall as the grid."""

    def setUp(self):
        app()
        keep_grids(self)
        fresh_copies(self)
        self.scene = FakeScene()
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

    def test_no_qt_no_grid(self):
        rebind(self, maya_hubqt, "qt", lambda: None)
        self.assertIsNone(cg.attach("mayaSceneSetupPortraits", self.scene))
        self.assertEqual(self.found, [])

    def test_no_placeholder_no_grid(self):
        maya_hubqt.find = lambda name, layout=False: None
        before = dict(cg._GRIDS)
        self.assertIsNone(cg.attach("mayaSceneSetupPortraits", self.scene))
        self.assertEqual(cg._GRIDS, before)

    def test_the_grid_is_laid_over_its_placeholder_and_registered(self):
        grid = cg.attach("mayaSceneSetupPortraits", self.scene, kind="skeleton",
                         selected="Creep")
        self.assertEqual(self.found, [("mayaSceneSetupPortraits", True)])
        self.assertIs(grid.parentWidget(), self.host)
        self.assertEqual(self.host.height(), grid.height_for(330))
        self.assertEqual(grid.geometry(), self.host.rect())
        self.assertTrue(grid.isVisible())
        self.assertEqual((grid.kind, grid.selected), ("skeleton", "Creep"))
        self.assertIs(grid.scene, self.scene)                # no copy: the scene as it is
        self.assertIs(cg.live("mayaSceneSetupPortraits"), grid)

    def test_a_resized_placeholder_is_kept_as_tall_as_the_grid(self):
        grid = cg.attach("mayaSceneSetupPortraits", self.scene)
        want = grid.height_for(140)
        self.assertNotEqual(want, grid.height_for(330))      # the resize must matter
        self.host.resize(140, self.host.height())
        QT.QtWidgets.QApplication.processEvents()
        self.assertEqual(self.host.height(), want)
        self.assertEqual(grid.geometry(), self.host.rect())

    def test_the_keeper_fits_on_a_resize_only_and_swallows_a_failing_fit(self):
        Keeper = cg._classes()["Keeper"]
        fits = []

        class Grid(object):
            def fit(self, host):
                fits.append(host)
                raise RuntimeError("the grid is gone")
        keeper = Keeper(Grid())
        self.addCleanup(keeper.deleteLater)
        resize = QT.QtGui.QResizeEvent(QT.QtCore.QSize(10, 10), QT.QtCore.QSize(5, 5))
        self.assertFalse(keeper.eventFilter(self.host, resize))
        self.assertEqual(fits, [self.host])
        self.assertFalse(keeper.eventFilter(self.host, QT.QtCore.QEvent(QT.QtCore.QEvent.Enter)))
        self.assertEqual(len(fits), 1)

    @unittest.skipUnless(MAYA, "no maya")
    def test_without_a_scene_the_grid_gets_the_real_one(self):
        fake_cmds(self, 1.25)
        grid = cg.attach("mayaSceneSetupPortraits")
        self.assertIsInstance(grid.scene, cg.Scene)
        self.assertEqual(grid.k, 1.25)

    def test_a_new_grid_clears_the_closed_ones_out_of_the_registry(self):
        gone = cg.make_grid(self.scene)
        cg._GRIDS["closedCopyPortraits"] = gone
        QT.shiboken.delete(gone)
        cg.attach("mayaSceneSetupPortraits", self.scene)
        self.assertNotIn("closedCopyPortraits", cg._GRIDS)

    def test_a_popup_copys_grid_is_its_own(self):
        scope = hubcopy.new_scope("characters")
        mine = scope.prefix + "mayaSceneSetupPortraits"
        scope.names["mayaSceneSetupPortraits"] = mine
        with hubcopy.entered(scope):
            grid = cg.attach("mayaSceneSetupPortraits", self.scene)
            self.assertIs(cg.live("mayaSceneSetupPortraits"), grid)
        self.assertIn(mine, cg._GRIDS)
        self.assertNotIn("mayaSceneSetupPortraits", cg._GRIDS)
        self.assertIsNone(cg.live("mayaSceneSetupPortraits"))     # the hub's: none
        self.assertEqual(grid.objectName(), cg.OBJECT_NAME + "_" + scope.tag)
        self.assertEqual(grid._fire_name, cg.FIRE_NAME + "_" + scope.tag)
        # a click from Qt, outside any scope: the scene is asked inside the copy
        self.assertTrue(grid.select("Creep"))
        self.assertIn(("select", "Creep", scope.tag), self.scene.log)
        # the copy closed: its grid reaches nothing of the scene
        close_copy(scope)
        grid.select("Orc_D")
        self.assertNotIn("Orc_D", [e[1] for e in self.scene.log if e[0] == "select"])


# ------------------------------------------------------------ the grid

@unittest.skipIf(QT is None, "no Qt")
class GridMore(unittest.TestCase):

    def setUp(self):
        app()
        self.scene = FakeScene()
        self.grid = cg.make_grid(self.scene, kind="rig", selected="Manny")
        self.grid.resize(330, self.grid.height_for(330))
        self.grid.move(3000, 3000)
        self.addCleanup(self.grid.deleteLater)
        self.addCleanup(self.grid._end)
        rebind(self, cg, "_skillbar", lambda: None)          # no bar on screen

    def keys(self):
        return [m.key for m in self.grid.models]

    def box(self, model):
        return self.grid.rects()[self.keys().index(model)]

    def centre(self, model):
        x, y, w, h = self.box(model)
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)

    def acts(self, name):
        return [e for e in self.scene.log if e[0] == name]

    def mouse(self, kind, local, button, buttons):
        g = self.grid.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    def key(self, code):
        event = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, code, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    # ------------------------------------------------------------ layout
    def test_the_size_hint_is_the_grids_height_for_its_width(self):
        self.assertEqual(self.grid.sizeHint(),
                         QT.QtCore.QSize(330, self.grid.height_for(330)))
        self.grid.resize(0, 0)
        self.assertEqual(self.grid.sizeHint(), QT.QtCore.QSize(1, self.grid.height_for(1)))

    def test_the_row_names_the_switchs_kind_or_the_bare_model(self):
        self.assertEqual(self.grid._row("Creep"), catalog.character_for("Creep", "rig").label)
        self.assertEqual(self.grid._row("UE4_Mannequin"), "UE4_Mannequin")     # no rig row
        self.grid.set_kind("skeleton")
        self.assertEqual(self.grid._row("Creep"),
                         catalog.character_for("Creep", "skeleton").label)

    def test_an_unknown_model_has_no_place(self):
        self.assertIsNone(self.grid._index("NoSuchModel"))
        self.assertEqual(self.grid._index("Creep"), self.keys().index("Creep"))

    # ------------------------------------------------------------- drops
    def test_a_drop_with_nothing_dragged_does_nothing(self):
        self.grid.status_text = "Creep [rig] - press Import"
        self.assertEqual(self.grid.drop_at(500, 500), "Creep [rig] - press Import")
        self.assertEqual(self.acts("target"), [])
        self.assertEqual(self.acts("say"), [])

    def test_a_drop_of_a_model_the_switch_lacks_says_so(self):
        text = self.grid.drop_at(500, 500, "UE4_Mannequin")
        self.assertEqual(text, look.absent_text(catalog.model_by_key("UE4_Mannequin").label,
                                                "rig"))
        self.assertEqual(self.acts("target"), [])
        self.assertEqual(self.acts("say"), [("say", text)])

    def test_a_drop_on_the_skill_bar_makes_the_portrait_a_skill(self):
        bar = FakeBar(target=("cell", 2, 0, 3))
        cg._skillbar = lambda: bar
        self.assertEqual(self.grid.drop_at(500, 500, "Creep"), "skill F2 cell 3: Creep")
        self.assertIn(("drop", 500, 500, {"kind": "character", "model": "Creep", "char": "rig"}),
                      bar.log)
        self.assertIn(("light", None), bar.log)              # the lit cell put out
        self.assertEqual(self.acts("target"), [])
        self.assertEqual(self.acts("place"), [])

    def test_a_drag_tells_the_scene_it_begins_and_ends_around_the_drop(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre("Creep")
        far = start + QT.QtCore.QPoint(-900, 400)
        self.mouse(E.MouseButtonPress, start, L, L)
        self.mouse(E.MouseMove, far, N, L)
        self.mouse(E.MouseButtonRelease, far, L, N)
        names = [e[0] for e in self.scene.log if e[0] in ("begin", "place", "end")]
        self.assertEqual(names, ["begin", "place", "end"])
        self.assertEqual(self.acts("begin"), [("begin", catalog.character_for("Creep", "rig").label)])

    def test_a_drag_survives_a_keyboard_it_cannot_grab_or_give_back(self):
        def broken():
            raise RuntimeError("no keyboard")
        self.grid.grabKeyboard = broken
        self.grid.releaseKeyboard = broken
        self.grid._start("Creep", QT.QtCore.QPoint(500, 500))
        self.assertIsNotNone(self.grid._drag)
        self.grid._end()
        self.assertIsNone(self.grid._drag)
        self.assertEqual(self.acts("end"), [("end",)])

    # ---------------------------------------------------------- captions
    def start(self, model="Creep", point=None):
        point = point or QT.QtCore.QPoint(500, 500)          # off the grid (it stands at 3000)
        self.grid._start(model, point)
        return point

    def test_no_caption_without_a_drag(self):
        self.grid._caption(QT.QtCore.QPoint(500, 500), force=True)
        self.assertEqual(self.acts("target"), [])

    def test_over_the_floor_the_caption_names_the_point(self):
        point = self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual(ghost.text, look.place_caption(self.grid._row("Creep"),
                                                        (120.0, 0.0, -35.0)))
        self.assertTrue(ghost.good)
        self.assertEqual(self.acts("target"), [("target", point.x(), point.y())])

    def test_over_a_character_the_caption_names_the_swap(self):
        self.scene.aim = dict(kind="swap", root="|root", label="root",
                              text="swap root for Creep [rig]")
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), ("swap root for Creep [rig]", True))

    def test_with_no_target_the_caption_says_why_and_warns(self):
        self.scene.aim = dict(kind="none", text="no target - drop onto a viewport")
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), ("no target - drop onto a viewport", False))

    def test_a_failing_scene_shows_its_error_on_the_caption(self):
        self.scene.fail_target = RuntimeError("no camera under the cursor")
        self.start()
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good),
                         ("RuntimeError: no camera under the cursor", False))

    def test_over_the_skill_bar_the_caption_is_the_bars(self):
        bar = FakeBar(target=("tab", 3))
        cg._skillbar = lambda: bar
        self.start()
        ghost = self.grid._drag["ghost"]
        label = self.grid._row("Creep")
        self.assertEqual((ghost.text, ghost.good), ("%s %s skill" % (label, look.DOT), True))
        self.assertIn(("light", ("tab", 3)), bar.log)
        self.assertIn(("caption", label, ("tab", 3)), bar.log)
        self.assertEqual(self.acts("target"), [])

    def test_back_on_the_grid_the_caption_says_release_off_the_hub(self):
        inside = self.grid.mapToGlobal(self.centre("Orc_D"))
        self.start(point=inside)
        ghost = self.grid._drag["ghost"]
        self.assertEqual((ghost.text, ghost.good), ("release off the hub to place", False))

    def test_the_caption_is_read_at_most_every_few_milliseconds(self):
        self.start()
        asked = len(self.acts("target"))
        self.grid._clock = FakeClock(look.THROTTLE_MS - 1)
        self.grid._caption(QT.QtCore.QPoint(600, 600))
        self.assertEqual(len(self.acts("target")), asked)
        self.grid._clock = FakeClock(look.THROTTLE_MS)
        self.grid._caption(QT.QtCore.QPoint(600, 600))
        self.assertEqual(len(self.acts("target")), asked + 1)
        self.assertEqual(self.grid._clock.restarts, 1)

    # -------------------------------------------------------------- mouse
    def test_a_middle_press_picks_nothing(self):
        E, M = QT.QtCore.QEvent, QT.QtCore.Qt.MiddleButton
        self.mouse(E.MouseButtonPress, self.centre("Creep"), M, M)
        self.assertEqual(self.grid.selected, "Manny")
        self.assertEqual(self.acts("select"), [])
        self.assertIsNone(self.grid._press)

    def test_another_key_during_a_drag_keeps_it(self):
        self.start()
        self.key(QT.QtCore.Qt.Key_A)
        self.assertIsNotNone(self.grid._drag)
        self.assertEqual(self.acts("say"), [])

    def test_leaving_the_grid_puts_the_hover_and_its_fire_out(self):
        rebind(self, cg, "_animations", lambda: True)
        E, N = QT.QtCore.QEvent, QT.QtCore.Qt.NoButton
        self.mouse(E.MouseMove, self.centre("Creep"), N, N)
        self.assertEqual(self.grid._hover, "Creep")
        self.assertTrue(self.grid.fx["Creep"].hover)
        QT.QtWidgets.QApplication.sendEvent(self.grid, QT.QtCore.QEvent(E.Leave))
        self.assertIsNone(self.grid._hover)
        self.assertFalse(self.grid.fx["Creep"].hover)

    def test_leaving_during_a_drag_leaves_the_hover_alone(self):
        rebind(self, cg, "_animations", lambda: False)
        self.grid._set_hover("Creep")
        self.start()
        QT.QtWidgets.QApplication.sendEvent(self.grid, QT.QtCore.QEvent(QT.QtCore.QEvent.Leave))
        self.assertEqual(self.grid._hover, "Creep")

    # --------------------------------------------------------------- fire
    def test_the_fire_dies_on_the_next_frame_once_animations_go_off(self):
        rebind(self, cg, "_animations", lambda: True)
        self.grid.hover_model("Creep")
        self.assertTrue(self.grid.fire_timer.isActive())
        cg._animations = lambda: False
        self.assertFalse(self.grid.advance(1.0 / 60))
        self.assertEqual(self.grid.fx, {})
        self.assertFalse(self.grid.fire_timer.isActive())

    def test_the_timer_steps_the_fire_on(self):
        rebind(self, cg, "_animations", lambda: True)
        self.grid.hover_model("Creep")
        before = self.grid.fx["Creep"].power
        self.grid._fire_clock.restart()
        self.grid._tick()                                    # a dt of ~0 is still a step
        self.grid.advance(0.05)
        self.assertGreater(self.grid.fx["Creep"].power, before)

    # -------------------------------------------------------------- paint
    def ring_share(self, image, model, hexname):
        x, y, w, _h = self.box(model)
        inset = int(look.RADIUS * self.grid.k) + 2
        row = [image.pixelColor(px, y) for px in range(x + inset, x + w - inset)]
        return sum(1 for c in row if near(c, maya_hubstyle.TOKENS[hexname], 40)) / float(len(row))

    def test_a_pick_the_switch_lacks_is_ringed_dashed(self):
        """«selected_absent»: picked, but the switch names a kind it lacks."""
        self.grid.pixmaps = {}
        self.grid.set_kind("skeleton")
        self.grid.set_selected("Manny")
        solid = self.ring_share(render(self.grid), "Manny", "accent")
        self.grid.set_selected("Orc_D")                      # Orc D has no skeleton
        dashed = self.ring_share(render(self.grid), "Orc_D", "accent")
        self.assertGreater(solid, 0.9)
        self.assertGreater(dashed, 0.3)
        self.assertLess(dashed, 0.85)

    def test_the_portrait_under_the_mouse_takes_the_hover_face_and_ring(self):
        rebind(self, cg, "_animations", lambda: False)       # no fire: the cold face
        self.grid.pixmaps = {}
        x, y, _w, _h = self.box("Creep")
        plain = render(self.grid)
        self.grid._set_hover("Creep")
        self.assertEqual(self.grid.fx, {})
        lit = render(self.grid)
        self.assertEqual(plain.pixelColor(x + 6, y + 6).name(), maya_hubstyle.TOKENS["field"])
        self.assertEqual(lit.pixelColor(x + 6, y + 6).name(), maya_hubstyle.TOKENS["hover"])
        self.assertGreater(self.ring_share(lit, "Creep", "text2"), 0.9)
        self.assertGreater(self.ring_share(plain, "Creep", "line"), 0.9)

    def test_with_no_icon_to_draw_a_missing_portrait_stays_blank(self):
        self.grid.pixmaps = {}
        x, y, w, h = self.box("Creep")

        def inked(image):
            field = maya_hubstyle.TOKENS["field"]
            return sum(1 for px in range(x + w // 4, x + 3 * w // 4)
                       for py in range(y + h // 4, y + h // 2)
                       if image.pixelColor(px, py).name() != field)
        self.assertGreater(inked(render(self.grid)), 0)      # the user glyph

        def broken(*_args):
            raise RuntimeError("no icon")
        rebind(self, maya_hubqt, "pixmap", broken)
        self.assertEqual(inked(render(self.grid)), 0)

    def burn(self, model, frames=30):
        rebind(self, cg, "_animations", lambda: True)
        self.grid.hover_model(model)
        for _ in range(frames):
            self.grid.advance(1.0 / 60)

    def test_a_portrait_without_a_picture_still_burns(self):
        """No picture: no silhouette to hide the fire behind, nothing to
        backlight - the glyph stands in the flames. (A cell size no other test
        burns at: the silhouettes are kept per model and size.)"""
        self.grid.resize(277, self.grid.height_for(277))
        self.assertEqual(self.grid.rects()[0][2], 67)
        self.grid.pixmaps = {}
        x, y, w, h = self.box("Creep")
        cold = render(self.grid)
        self.burn("Creep")
        hot = render(self.grid)
        changed = sum(1 for px in range(x, x + w, 2) for py in range(y, y + h, 2)
                      if hot.pixel(px, py) != cold.pixel(px, py))
        self.assertGreater(changed, 50)

    def test_the_picked_portrait_burns_on_its_own_face(self):
        self.burn("Manny")
        picked = render(self.grid)
        self.grid.set_selected("Creep")
        other = render(self.grid)
        x, y, w, h = self.box("Manny")
        changed = sum(1 for px in range(x, x + w, 2) for py in range(y, y + h, 2)
                      if picked.pixel(px, py) != other.pixel(px, py))
        self.assertGreater(changed, 20)

    def test_a_fire_with_no_sparks_draws_no_sparks(self):
        import maya_charfire
        classes = cg._classes()
        fx = maya_charfire.CardFx(7)
        self.assertFalse(fx.sparks.alive())
        image = QT.QtGui.QImage(64, 64, QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        p = QT.QtGui.QPainter(image)
        try:
            self.grid._paint_sparks(p, QT.QtCore.QRectF(0, 0, 64, 64), fx,
                                    classes["fire_look"]("ember"), True)
        finally:
            p.end()
        self.assertTrue(all(image.pixel(px, py) == 0 for px in range(64) for py in range(64)))


# ------------------------------------------------- the overlay, the hub

@unittest.skipIf(QT is None, "no Qt")
class Overlay(unittest.TestCase):

    def setUp(self):
        self.app = app()
        self.scene = FakeScene()
        rebind(self, cg, "_animations", lambda: True)

    def in_a_hub(self):
        area = QT.QtWidgets.QScrollArea()
        self.addCleanup(area.deleteLater)
        area.resize(420, 400)
        content = QT.QtWidgets.QWidget()
        content.resize(400, 600)
        area.setWidget(content)
        host = QT.QtWidgets.QWidget(content)
        host.setGeometry(30, 150, 330, 10)
        grid = cg.make_grid(self.scene, parent=host, kind="rig", selected="Manny")
        grid.fit(host)
        area.show()
        self.app.processEvents()
        return content, grid

    def test_nothing_holds_no_scrolled_content(self):
        self.assertIsNone(cg._classes()["scrolled_content"](None))

    def test_a_grid_never_stands_whole_inside_a_stranger(self):
        grid = cg.make_grid(self.scene)
        self.addCleanup(grid.deleteLater)
        self.assertFalse(grid._whole_in(object()))

    def test_an_overlay_it_cannot_ask_about_is_forgotten(self):
        grid = cg.make_grid(self.scene)
        self.addCleanup(grid.deleteLater)
        grid.overlay = object()
        rebind(self, QT, "shiboken", BrokenShiboken(QT.shiboken))
        self.assertIsNone(grid._live_overlay())
        self.assertIsNone(grid.overlay)

    def test_the_overlay_draws_nothing_for_a_closed_grid(self):
        content, grid = self.in_a_hub()
        FireOverlay = cg._classes()["FireOverlay"]
        gone = cg.make_grid(self.scene)
        overlay = FireOverlay(content, gone)
        overlay.resize(100, 100)
        QT.shiboken.delete(gone)
        image = render(overlay)
        self.assertEqual(overlay.paint_ms, 0.0)
        self.assertTrue(all(image.pixel(px, py) == 0 for px in range(0, 100, 5)
                            for py in range(0, 100, 5)))

    def test_the_overlay_draws_nothing_when_it_cannot_ask_about_its_grid(self):
        content, grid = self.in_a_hub()
        overlay = cg._classes()["FireOverlay"](content, grid)
        overlay.resize(100, 100)
        rebind(self, QT, "shiboken", BrokenShiboken(QT.shiboken))
        render(overlay)
        self.assertEqual(overlay.paint_ms, 0.0)

    def test_the_overlay_draws_a_standing_grid(self):
        content, grid = self.in_a_hub()
        overlay = cg._classes()["FireOverlay"](content, grid)
        overlay.resize(100, 100)
        render(overlay)
        self.assertGreater(overlay.paint_ms, 0.0)

    def test_burnt_out_the_overlay_hides(self):
        content, grid = self.in_a_hub()
        grid.hover_model("Creep")
        grid.advance(1.0 / 60)
        overlay = grid.overlay
        self.assertTrue(overlay.isVisible())
        grid.fx.clear()
        grid._sync_overlay()
        self.assertFalse(overlay.isVisible())
        self.assertEqual(grid.overlaid, set())

    def test_an_overlay_left_in_another_widget_is_replaced(self):
        content, grid = self.in_a_hub()
        other = QT.QtWidgets.QWidget()
        self.addCleanup(other.deleteLater)
        stray = cg._classes()["FireOverlay"](other, grid)
        grid.overlay = stray
        grid.hover_model("Creep")
        self.assertIsNot(grid.overlay, stray)
        self.assertIs(grid.overlay.parentWidget(), content)
        flush_deletes()
        self.assertFalse(QT.shiboken.isValid(stray))


if __name__ == "__main__":
    unittest.main()

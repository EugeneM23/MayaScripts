"""The weapon inventory's remaining paths, offscreen (2026-10-27): the real
`Scene` forwarding to the card's functions, the panel's refresh queue, the
hand cards' Channel Box fields, a drag through every move and drop, the
skill bar and its failures, the paint of every hand state, and laying the
panel over its placeholder (`attach`, `live`, `_prune`, the floating window
an older build left).

Everything Maya-side is faked by rebinding single module attributes, put
back after each test; nothing in sys.modules is replaced but the one entry
a test names, and it is put back.

Specs: docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md,
docs/superpowers/specs/2026-10-01-inventory-card-design.md
"""

import sys
import unittest

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubcopy as hubcopy
import maya_inventory as inv
import maya_invlook as look
from maya_scenesetup import catalog
from maya_scenesetup.equip import Holding

ROOT = "|Manny_Rig:root"
WIDTH = 330


def _app():
    return QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])


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
        self.currents = 0
        self.snapshots = 0

    def scale(self):
        return 1.0

    def current(self):
        self.currents += 1
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
        self.snapshots += 1
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
        self.log.append(("move", root, side, target))
        return "moved"

    def open_scene(self, key):
        self.log.append(("open_scene", key))
        return "opened " + key

    def watch(self, callback):
        self.watched.append(callback)
        return ["job"]

    def unwatch(self, jobs):
        self.log.append(("unwatch", jobs))

    def say(self, text):
        self.said.append(text)


class FakeBar(object):
    """maya_skillbar's drag half: an aim over the bar, what a drop says."""

    def __init__(self, aim=None):
        self.aimed = aim
        self.lit = []
        self.dropped = []

    def aim(self, gx, gy):
        return self.aimed

    def light(self, target):
        self.lit.append(target)

    def drop(self, gx, gy, item):
        self.dropped.append(item)
        return "skill set"

    def caption(self, label, skill):
        return "%s · %s" % (label, skill)


class FakeClock(object):
    def __init__(self, elapsed):
        self.ms = elapsed
        self.restarts = 0

    def elapsed(self):
        return self.ms

    def restart(self):
        self.restarts += 1


_MISSING = object()


class Swaps(object):
    """setattr with the old value put back by the test's cleanup."""

    def swap(self, owner, name, value):
        old = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, old)
        return old

    def swap_module(self, name, value):
        """One sys.modules entry swapped, put back (or taken out) after."""
        old = sys.modules.get(name, _MISSING)
        sys.modules[name] = value
        if old is _MISSING:
            self.addCleanup(sys.modules.pop, name, None)
        else:
            self.addCleanup(sys.modules.__setitem__, name, old)


def _later(widget):
    """deleteLater, unless Qt already deleted it."""
    try:
        if QT.shiboken.isValid(widget):
            widget.deleteLater()
    except RuntimeError:
        pass


@unittest.skipIf(QT is None, "no Qt")
class PanelCase(Swaps, unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.scene = FakeScene()
        self.panel = inv.make_panel(self.scene)
        self.panel.resize(WIDTH, self.panel.height_for(WIDTH))
        self.panel.move(3000, 3000)
        self.panel.show()
        self.addCleanup(self._close)
        self.rects = self.panel.rects()
        self.scene.log = []
        self.bar = FakeBar()
        self.swap(inv, "_skillbar", lambda: self.bar)

    def _close(self):
        try:
            if self.panel._drag:
                self.panel._end()
        except RuntimeError:
            pass
        self.panel.deleteLater()

    def at(self, name, dx=5, dy=5):
        x, y = self.rects[name][:2]
        return int(x) + dx, int(y) + dy

    def glob(self, local):
        p = self.panel.mapToGlobal(QT.QtCore.QPoint(int(local[0]), int(local[1])))
        return p.x(), p.y()

    def tile(self, key, dx=5, dy=5):
        x, y = self.panel.tile_of(key)[:2]
        return x + dx, y + dy

    def mouse(self, kind, local, button=None, buttons=None):
        Qt = QT.QtCore.Qt
        button = Qt.LeftButton if button is None else button
        buttons = button if buttons is None else buttons
        glob = QT.QtCore.QPointF(*self.glob(local))
        event = QT.QtGui.QMouseEvent(
            {"press": QT.QtCore.QEvent.MouseButtonPress,
             "move": QT.QtCore.QEvent.MouseMove,
             "release": QT.QtCore.QEvent.MouseButtonRelease}[kind],
            QT.QtCore.QPointF(local[0], local[1]), glob, button, buttons,
            Qt.NoModifier)
        {"press": self.panel.mousePressEvent,
         "move": self.panel.mouseMoveEvent,
         "release": self.panel.mouseReleaseEvent}[kind](event)

    def move_to(self, local):
        self.mouse("move", local, button=QT.QtCore.Qt.NoButton,
                   buttons=QT.QtCore.Qt.LeftButton)

    def hover(self, local):
        self.mouse("move", local, button=QT.QtCore.Qt.NoButton,
                   buttons=QT.QtCore.Qt.NoButton)

    def key(self, code, target=None):
        event = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, code,
                                   QT.QtCore.Qt.NoModifier, "5")
        (target or self.panel).keyPressEvent(event)

    def image(self):
        image = QT.QtGui.QImage(self.panel.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.panel.render(image)
        return image

    def drag_tile(self, key):
        start = self.tile(key)
        self.mouse("press", start)
        self.move_to((start[0] + 40, start[1] + 40))
        self.assertIsNotNone(self.panel._drag)
        return start


# ------------------------------------------------------------- the real scene

class RealScene(Swaps, unittest.TestCase):
    """`Scene` is the panel's road into Maya: each call reaches the card's own
    function with its arguments, and what it promises to swallow it swallows."""

    def setUp(self):
        from maya_scenesetup import droptarget, equip, window
        self.window, self.equip, self.dt = window, equip, droptarget
        self.calls = []
        rec = self.calls.append
        for name, answer in (("current_character", "|root"),
                             ("hand_grips", {"R": 1}),
                             ("picked", ("Dagger_01", "L")),
                             ("select_weapon", "w"), ("select_hand", "h"),
                             ("set_hand_grip", "g"),
                             ("open_weapon_scene", "o"),
                             ("say_weapon", None)):
            self.swap(window, name, (lambda n, a: lambda *args: rec((n,) + args) or a)(
                name, answer))
        for name, answer in (("holdings", {"R": "held"}), ("to_hand", "in"),
                             ("to_floor", "fl"), ("take_off", "off"),
                             ("move", "mv")):
            self.swap(equip, name, (lambda n, a: lambda *args: rec((n,) + args) or a)(
                name, answer))
        self.swap(droptarget, "snapshot", lambda: rec(("snapshot",)) or ["s"])
        self.swap(droptarget, "target", lambda *args: rec(("target",) + args) or {"kind": "none"})
        self.scene = inv.Scene("myPlaceholder")

    def test_it_remembers_its_placeholder(self):
        self.assertEqual(self.scene.placeholder, "myPlaceholder")
        self.assertEqual(inv.Scene().placeholder, inv.PLACEHOLDER)

    def test_the_reads_go_to_the_card(self):
        self.assertEqual(self.scene.current(), "|root")
        self.assertEqual(self.scene.holdings("|root"), {"R": "held"})
        self.assertEqual(self.scene.grips("|root"), {"R": 1})
        self.assertEqual(self.scene.picked(), ("Dagger_01", "L"))
        self.assertEqual(self.calls, [("current_character",), ("holdings", "|root"),
                                      ("hand_grips", "|root"), ("picked",)])

    def test_the_presses_go_to_the_card_with_their_arguments(self):
        entry = catalog.by_key("Spear_01")
        self.assertEqual(self.scene.select_weapon("Spear_01"), "w")
        self.assertEqual(self.scene.select_hand("L"), "h")
        self.assertEqual(self.scene.set_grip("R", (1, 2, 3), (4, 5, 6)), "g")
        self.assertEqual(self.scene.to_hand("|root", "L", entry), "in")
        self.assertEqual(self.scene.to_floor("|root", entry, (1, 0, 2), (1, 0, 0), "L"), "fl")
        self.assertEqual(self.scene.take_off("|root", "R"), "off")
        self.assertEqual(self.scene.move("|root", "R", ("hand", "|root", "L")), "mv")
        self.assertEqual(self.scene.open_scene("Spear_01"), "o")
        self.assertEqual(self.calls, [
            ("select_weapon", "Spear_01"), ("select_hand", "L"),
            ("set_hand_grip", "R", (1, 2, 3), (4, 5, 6)),
            ("to_hand", "|root", "L", entry),
            ("to_floor", "|root", entry, (1, 0, 2), (1, 0, 0), "L"),
            ("take_off", "|root", "R"),
            ("move", "|root", "R", ("hand", "|root", "L")),
            ("open_weapon_scene", "Spear_01")])

    def test_a_floor_drop_with_no_side_names_none(self):
        self.scene.to_floor("|root", "e", (0, 0, 0), (1, 0, 0))
        self.assertEqual(self.calls[-1], ("to_floor", "|root", "e", (0, 0, 0), (1, 0, 0), None))

    def test_the_drop_target_is_droptargets_at_the_scenes_scale(self):
        self.swap(inv.Scene, "scale", lambda me: 1.5)
        self.assertEqual(self.scene.snapshot(), ["s"])
        self.assertEqual(self.scene.target(10, 20, ["s"], ("|root", "R")), {"kind": "none"})
        self.assertEqual(self.calls, [("snapshot",),
                                      ("target", 10, 20, ["s"], 1.5, ("|root", "R"))])

    def test_say_writes_the_weapons_line_and_swallows_a_failure(self):
        self.scene.say("hello")
        self.assertEqual(self.calls, [("say_weapon", "hello")])

        def boom(text):
            raise RuntimeError("no line")
        self.window.say_weapon = boom
        self.scene.say("again")                      # nothing raised


class FakeCmds(object):
    """The few maya.cmds the real Scene uses."""

    def __init__(self, dpi=1.5, parented=True):
        self.dpi = dpi
        self.parented = parented
        self.jobs = []
        self.killed = []
        self.alive = set()

    def mayaDpiSetting(self, query=False, realScaleValue=False):
        if isinstance(self.dpi, Exception):
            raise self.dpi
        return self.dpi

    def scriptJob(self, event=None, parent=None, exists=None, kill=None, force=False):
        if exists is not None:
            if exists == "broken":
                raise RuntimeError("no such job")
            return exists in self.alive
        if kill is not None:
            self.killed.append((kill, force))
            return None
        if parent is not None and not self.parented:
            raise RuntimeError("no such control: " + parent)
        number = len(self.jobs) + 1
        self.jobs.append((event[0], parent, event[1]))
        self.alive.add(number)
        return number


class RealSceneCmds(Swaps, unittest.TestCase):
    """The Scene's own `maya.cmds` calls: the display scale and the
    scriptJobs that make the hands follow the selection, undo and a scene."""

    def use(self, fake):
        import maya
        self.swap(maya, "cmds", fake)
        self.swap_module("maya.cmds", fake)

    def test_the_scale_is_mayas_real_scale_value(self):
        self.use(FakeCmds(dpi=1.5))
        self.assertEqual(inv.Scene().scale(), 1.5)

    def test_no_answer_or_a_failure_is_one(self):
        self.use(FakeCmds(dpi=0))
        self.assertEqual(inv.Scene().scale(), 1.0)
        self.use(FakeCmds(dpi=RuntimeError("no UI")))
        self.assertEqual(inv.Scene().scale(), 1.0)

    def test_watch_makes_a_job_per_event_parented_to_the_card(self):
        fake = FakeCmds()
        self.use(fake)
        callback = object()
        jobs = inv.Scene("myCard").watch(callback)
        self.assertEqual(jobs, [1, 2, 3, 4, 5])
        self.assertEqual([j[0] for j in fake.jobs], list(inv.EVENTS))
        self.assertTrue(all(j[1] == "myCard" and j[2] is callback for j in fake.jobs))

    def test_a_card_maya_does_not_know_still_gets_its_jobs(self):
        fake = FakeCmds(parented=False)
        self.use(fake)
        jobs = inv.Scene("gone").watch(lambda: None)
        self.assertEqual(len(jobs), len(inv.EVENTS))
        self.assertTrue(all(j[1] is None for j in fake.jobs))

    def test_unwatch_kills_the_live_jobs_and_swallows_a_failure(self):
        fake = FakeCmds()
        self.use(fake)
        fake.alive = {1, 3}
        inv.Scene().unwatch([1, 2, "broken", 3])
        self.assertEqual(fake.killed, [(1, True), (3, True)])
        inv.Scene().unwatch(None)                     # nothing to kill
        self.assertEqual(len(fake.killed), 2)


# --------------------------------------------------------------- skill bar

class SkillBarSeams(Swaps, unittest.TestCase):
    """The skill bar is optional: no module, or one that raises, is no aim."""

    def test_no_skill_bar_module_is_no_aim(self):
        self.swap_module("maya_skillbar", None)      # import raises ImportError
        self.assertIsNone(inv._skillbar())
        self.assertIsNone(inv.skill_aim(1, 2))
        inv.skill_light("anything")                  # nothing raised

    def test_a_bar_that_raises_is_no_aim_and_no_light(self):
        class Broken(object):
            def aim(self, gx, gy):
                raise RuntimeError("aim")

            def light(self, target):
                raise RuntimeError("light")
        self.swap(inv, "_skillbar", lambda: Broken())
        self.assertIsNone(inv.skill_aim(1, 2))
        inv.skill_light("F2")                         # nothing raised

    def test_a_bar_answers_its_aim_and_is_lit(self):
        bar = FakeBar(aim="F3 · cell 4")
        self.swap(inv, "_skillbar", lambda: bar)
        self.assertEqual(inv.skill_aim(1, 2), "F3 · cell 4")
        inv.skill_light("F3 · cell 4")
        self.assertEqual(bar.lit, ["F3 · cell 4"])


class Pure(unittest.TestCase):

    def test_the_last_line_of_an_error(self):
        self.assertEqual(inv._last_line("Traceback\n  x\nRuntimeError: no\n\n"),
                         "RuntimeError: no")
        self.assertEqual(inv._last_line(""), "failed")
        self.assertEqual(inv._last_line(None), "failed")

    def test_hand_values_and_back(self):
        values = inv.hand_values(((1, 2, 3), (4, 5, 6)))
        self.assertEqual(values, {"tx": 4.0, "ty": 5.0, "tz": 6.0,
                                  "rx": 1.0, "ry": 2.0, "rz": 3.0})
        self.assertEqual(inv.grip_of(values), ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_a_scoped_name_carries_the_copys_tag(self):
        self.assertEqual(inv.scoped_name("x"), "x")
        with hubcopy.entered(hubcopy.Scope("hubcopyT")):
            self.assertEqual(inv.scoped_name("x"), "x_hubcopyT")


# ------------------------------------------------------------- refreshing

class RigsReadOnce(Swaps, unittest.TestCase):

    def test_a_reading_that_cannot_start_is_none(self):
        import maya_rigs

        def boom():
            raise RuntimeError("no Maya")
        self.swap(maya_rigs, "reading", boom)
        with inv._rigs_read_once() as reading:
            self.assertIsNone(reading.inner)

    def test_a_reading_is_entered_and_left(self):
        import maya_rigs
        seen = []

        class Reading(object):
            def __enter__(self):
                seen.append("in")

            def __exit__(self, *exc):
                seen.append(("out", exc[0]))
        self.swap(maya_rigs, "reading", lambda: Reading())
        with self.assertRaises(ValueError):
            with inv._rigs_read_once():
                raise ValueError("inside")
        self.assertEqual(seen, ["in", ("out", ValueError)])


class Refresh(PanelCase):

    def test_a_scene_that_raises_empties_the_hands_and_says_why(self):
        def boom():
            raise RuntimeError("the scene broke")
        self.scene.current = boom
        self.panel.refresh()
        self.assertEqual(self.panel.holding, {})
        self.assertIn("the scene broke", self.panel.status_text)
        self.assertIn("the scene broke", self.scene.said[-1])

    def test_a_hand_with_no_grip_keeps_its_fields(self):
        self.panel.field("L", "tx").setText("keep")
        self.scene.hand_grips = {"R": ((0, 0, 0), (9, 9, 9), True)}
        self.panel.refresh()
        self.assertEqual(self.panel.field("R", "tx").text(), "9")
        self.assertEqual(self.panel.field("L", "tx").text(), "keep")

    def test_a_grip_without_an_editable_flag_is_editable(self):
        self.scene.hand_grips = {"R": ((0, 0, 0), (1, 2, 3)), "L": None}
        self.panel.refresh()
        self.assertFalse(self.panel.field("R", "ty").isReadOnly())
        self.assertEqual(self.panel.field("R", "ty").text(), "2")

    def test_a_shown_panel_queues_one_refresh(self):
        before = self.scene.currents
        self.panel._queue_refresh("SelectionChanged")
        self.assertEqual(self.scene.currents, before)          # not at once
        self.app.processEvents()
        self.assertEqual(self.scene.currents, before + 1)

    def test_a_hidden_panel_refreshes_when_it_is_shown(self):
        self.panel.hide()
        before = self.scene.currents
        self.panel._queue_refresh()
        self.app.processEvents()
        self.assertEqual(self.scene.currents, before)
        self.assertTrue(self.panel._stale)
        self.panel.show()
        self.assertFalse(self.panel._stale)
        self.app.processEvents()
        self.assertEqual(self.scene.currents, before + 1)

    def test_a_shown_panel_that_was_not_stale_does_not_refresh(self):
        self.panel.hide()
        before = self.scene.currents
        self.panel.show()
        self.app.processEvents()
        self.assertEqual(self.scene.currents, before)

    def test_a_deleted_or_unknowable_panel_queues_nothing(self):
        classes = inv._classes()
        q = classes["qt"]

        class Dead(object):
            @staticmethod
            def isValid(obj):
                return False
        self.swap(q, "shiboken", Dead())
        before = self.scene.currents
        self.panel._queue_refresh()

        class Broken(object):
            @staticmethod
            def isValid(obj):
                raise RuntimeError("shiboken")
        q.shiboken = Broken()
        self.panel._queue_refresh()                    # swallowed
        self.app.processEvents()
        self.assertEqual(self.scene.currents, before)

    def test_its_size_hint_is_its_height_for_its_width(self):
        hint = self.panel.sizeHint()
        self.assertEqual((hint.width(), hint.height()),
                         (WIDTH, self.panel.height_for(WIDTH)))


# --------------------------------------------------------------- picking

class Picking(PanelCase):

    def test_an_unknown_tile_or_hand_picks_nothing(self):
        self.panel.status_text = "as it was"
        self.assertEqual(self.panel.pick_item("Excalibur"), "as it was")
        self.assertEqual(self.panel.pick_hand("X"), "as it was")
        self.assertEqual(self.scene.log, [])
        self.assertIsNone(self.panel.tile_of("Excalibur"))

    def test_a_press_on_a_held_hand_picks_it_and_can_drag_its_weapon(self):
        well = self.at("well_R")
        self.mouse("press", well)
        self.assertEqual(self.scene.log, [("select_hand", "R")])
        self.assertEqual(self.panel._press[0], ("slot", "R"))
        self.move_to((well[0] + 30, well[1] + 30))
        self.assertEqual(self.panel._drag["source"], ("slot", "R"))

    def test_a_press_on_an_empty_hand_carries_nothing(self):
        well = self.at("well_L")
        self.mouse("press", well)
        self.assertIsNone(self.panel._press)
        self.move_to((well[0] + 30, well[1] + 30))
        self.assertIsNone(self.panel._drag)

    def test_a_press_off_every_target_or_with_the_middle_button_does_nothing(self):
        self.mouse("press", (1, 1))                   # the caption band
        self.mouse("press", self.tile("Spear_01"), button=QT.QtCore.Qt.MiddleButton)
        self.assertEqual(self.scene.log, [])
        self.assertIsNone(self.panel._press)

    def test_a_small_move_is_still_a_click(self):
        start = self.tile("Spear_01")
        self.mouse("press", start)
        self.move_to((start[0] + 1, start[1]))
        self.assertIsNone(self.panel._drag)
        self.mouse("release", start)
        self.assertIsNone(self.panel._press)

    def test_hovering_lights_a_tile_then_a_hand_and_leaving_puts_it_out(self):
        self.hover(self.tile("Spear_01"))
        self.assertEqual(self.panel._hover, ("tile", "Spear_01"))
        self.hover(self.at("hand_L"))
        self.assertEqual(self.panel._hover, ("slot", "L"))
        self.hover((1, 1))
        self.assertIsNone(self.panel._hover)
        self.hover(self.at("hand_L"))
        self.panel.leaveEvent(QT.QtCore.QEvent(QT.QtCore.QEvent.Leave))
        self.assertIsNone(self.panel._hover)

    def test_leaving_during_a_drag_keeps_the_hover(self):
        self.hover(self.tile("Spear_01"))
        self.drag_tile("Dagger_01")
        self.panel._hover = ("tile", "Spear_01")
        self.panel.leaveEvent(QT.QtCore.QEvent(QT.QtCore.QEvent.Leave))
        self.assertEqual(self.panel._hover, ("tile", "Spear_01"))


# --------------------------------------------------------------- channels

class Channels(PanelCase):

    def test_a_typed_digit_reaches_the_field(self):
        field = self.panel.field("R", "tx")
        field.setText("")
        self.key(QT.QtCore.Qt.Key_5, field)
        self.assertEqual(field.text(), "5")

    def test_escape_takes_the_focus_away(self):
        field = self.panel.field("R", "tx")
        field.setText("99")
        self.key(QT.QtCore.Qt.Key_Escape, field)
        self.assertEqual(field.text(), "1.5")
        self.assertFalse(field.hasFocus())

    def test_a_typed_value_applies_on_the_left_hand(self):
        field = self.panel.field("L", "tx")
        field.setText("8")
        field.editingFinished.emit()
        self.assertEqual(self.scene.log[-1][0:2], ("set_grip", "L"))
        self.assertEqual(self.scene.log[-1][3][0], 8.0)

    def test_a_read_only_hand_is_shown_faint_and_its_fields_cannot_be_typed_in(self):
        self.scene.hand_grips["L"] = ((0, 0, 0), (0, 0, 0), False)
        self.panel.refresh()
        self.assertTrue(all(self.panel.field("L", c).isReadOnly() for c in look.CHANNELS))
        self.assertGreater(self.image().width(), 0)    # the faint labels paint


# ------------------------------------------------------------------- drops

class Drops(PanelCase):

    def test_a_tile_over_the_skill_bar_becomes_a_skill(self):
        self.bar.aimed = "F3 · cell 4"
        text = self.panel.drop_at(10, 10, ("tile", "Spear_01"))
        self.assertEqual(text, "skill set")
        self.assertEqual(self.bar.dropped, [{"kind": "weapon", "key": "Spear_01"}])
        self.assertEqual(self.bar.lit[-1], None)
        self.assertEqual([e for e in self.scene.log if e[0] != "target"], [])

    def test_a_hands_weapon_never_goes_to_the_skill_bar(self):
        self.bar.aimed = "F3 · cell 4"
        self.panel.drop_at(10, 10, ("slot", "R"))
        self.assertEqual(self.bar.dropped, [])
        self.assertEqual(self.scene.log[-1][0], "move")

    def test_a_hand_dropped_back_onto_itself_in_the_viewport_says_so(self):
        self.scene.aim = dict(kind="hand", root=ROOT, side="R", text="right")
        self.assertEqual(self.panel.drop_at(10, 10, ("slot", "R")),
                         "already in the right hand")
        self.assertEqual([e for e in self.scene.log if e[0] != "target"], [])

    def test_a_hand_dropped_on_another_characters_hand_moves_there(self):
        self.scene.aim = dict(kind="hand", root="|other:root", side="R", text="t")
        self.panel.drop_at(10, 10, ("slot", "R"))
        self.assertEqual(self.scene.log[-1],
                         ("move", ROOT, "R", ("hand", "|other:root", "R")))

    def test_a_hand_dropped_on_the_floor_lays_it_there(self):
        self.scene.aim = dict(kind="floor", root=ROOT, side="R", point=(1, 0, 2),
                              heading=(1, 0, 0), text="floor")
        self.panel.drop_at(10, 10, ("slot", "R"))
        self.assertEqual(self.scene.log, [("target", (ROOT, "R")),
                                          ("move", ROOT, "R",
                                           ("floor", ROOT, (1, 0, 2), (1, 0, 0)))])

    def test_no_text_for_no_target_says_no_target(self):
        self.scene.aim = dict(kind="none")
        self.assertEqual(self.panel.drop_at(10, 10, ("tile", "Spear_01")), "no target")

    def test_a_drop_outside_a_drag_reads_the_scene_itself(self):
        before = self.scene.snapshots
        self.panel.drop_at(10, 10, ("tile", "Spear_01"))
        self.assertEqual(self.scene.snapshots, before + 1)

    def test_a_drop_during_a_drag_uses_the_drags_reading(self):
        self.drag_tile("Dagger_01")
        before = self.scene.snapshots
        self.panel.drop_at(10, 10, ("tile", "Spear_01"))
        self.assertEqual(self.scene.snapshots, before)


# -------------------------------------------------------------------- drag

class Drag(PanelCase):

    def test_the_drag_reads_the_scene_once_and_moves_the_ghost(self):
        start = self.drag_tile("Dagger_01")
        self.assertEqual(self.scene.snapshots, 1)
        ghost = self.panel._drag["ghost"]
        self.assertEqual(ghost.objectName(), inv.GHOST_NAME)
        self.assertTrue(ghost.isVisible())
        self.panel._clock = FakeClock(1000)
        self.move_to((start[0] + 200, start[1] + 200))
        self.assertEqual(self.scene.snapshots, 1)
        self.assertEqual(ghost.text, "Manny_Rig · left hand")

    def test_a_snapshot_that_raises_still_drags_and_says_why(self):
        def boom():
            raise RuntimeError("no characters")
        self.scene.snapshot = boom
        self.drag_tile("Dagger_01")
        self.assertEqual(self.panel._drag["snap"], [])
        self.assertIn("no characters", self.panel.status_text)

    def test_a_keyboard_that_cannot_be_grabbed_or_let_go_is_no_matter(self):
        def boom(*a):
            raise RuntimeError("keyboard")
        self.panel.grabKeyboard = boom
        self.panel.releaseKeyboard = boom
        self.drag_tile("Dagger_01")
        self.panel._end()
        self.assertIsNone(self.panel._drag)

    def test_escape_cancels_a_drag_other_keys_do_not(self):
        self.drag_tile("Dagger_01")
        self.key(QT.QtCore.Qt.Key_A)
        self.assertIsNotNone(self.panel._drag)
        self.key(QT.QtCore.Qt.Key_Escape)
        self.assertIsNone(self.panel._drag)
        self.assertEqual(self.scene.said[-1], "cancelled")

    def test_escape_without_a_drag_is_the_widgets(self):
        self.key(QT.QtCore.Qt.Key_Escape)
        self.assertEqual(self.scene.said, [])

    def test_a_release_with_the_right_button_drops_nothing(self):
        self.drag_tile("Dagger_01")
        self.mouse("release", (5, 5), button=QT.QtCore.Qt.RightButton)
        self.assertIsNotNone(self.panel._drag)
        self.assertEqual([e for e in self.scene.log if e[0] not in ("target", "select_weapon")], [])

    def test_a_drop_that_raises_still_ends_the_drag(self):
        self.drag_tile("Dagger_01")

        def boom(*a):
            raise RuntimeError("the drop broke")
        self.panel.drop_at = boom
        with self.assertRaises(RuntimeError):
            self.mouse("release", (-5000, 5))
        self.assertIsNone(self.panel._drag)

    def test_the_caption_without_a_drag_is_nothing(self):
        self.panel._caption(QT.QtCore.QPoint(0, 0), force=True)
        self.assertIsNone(self.panel._drag)

    def test_captions_over_the_panel(self):
        self.panel._start(("tile", "Dagger_01"), QT.QtCore.QPoint(*self.glob(self.tile("Dagger_01"))))
        ghost = self.panel._drag["ghost"]
        self.panel._caption(QT.QtCore.QPoint(*self.glob(self.at("hand_R"))), force=True)
        self.assertEqual((ghost.text, ghost.good), ("Right hand", True))
        self.panel._caption(QT.QtCore.QPoint(*self.glob(self.tile("Spear_01"))), force=True)
        self.assertEqual(ghost.text, "")                # a tile among the tiles
        self.panel._end()
        self.panel._start(("slot", "R"), QT.QtCore.QPoint(*self.glob(self.at("well_R"))))
        ghost = self.panel._drag["ghost"]
        self.panel._caption(QT.QtCore.QPoint(*self.glob(self.at("hand_R"))), force=True)
        self.assertEqual((ghost.text, ghost.good), ("Right hand", False))
        self.panel._caption(QT.QtCore.QPoint(*self.glob(self.at("hand_L"))), force=True)
        self.assertEqual((ghost.text, ghost.good), ("Left hand", True))

    def test_over_the_skill_bar_the_caption_is_the_bars(self):
        self.bar.aimed = "F3 · cell 4"
        self.panel._start(("tile", "Spear_01"), QT.QtCore.QPoint(10, 10))
        self.panel._caption(QT.QtCore.QPoint(10, 10), force=True)
        self.assertEqual(self.panel._drag["ghost"].text, "Spear 01 · F3 · cell 4")
        self.assertIn("F3 · cell 4", self.bar.lit)

    def test_the_caption_waits_out_the_throttle(self):
        self.panel._start(("tile", "Spear_01"), QT.QtCore.QPoint(10, 10))
        targets = len([e for e in self.scene.log if e[0] == "target"])
        clock = FakeClock(inv.THROTTLE_MS - 1)
        self.panel._clock = clock
        self.panel._caption(QT.QtCore.QPoint(20, 20))
        self.assertEqual(len([e for e in self.scene.log if e[0] == "target"]), targets)
        clock.ms = inv.THROTTLE_MS + 1
        self.panel._caption(QT.QtCore.QPoint(20, 20))
        self.assertEqual(len([e for e in self.scene.log if e[0] == "target"]), targets + 1)
        self.assertEqual(clock.restarts, 1)

    def test_a_target_that_raises_is_a_bad_caption(self):
        def boom(*a):
            raise RuntimeError("no view")
        self.scene.target = boom
        self.panel._start(("tile", "Spear_01"), QT.QtCore.QPoint(10, 10))
        ghost = self.panel._drag["ghost"]
        self.assertIn("no view", ghost.text)
        self.assertFalse(ghost.good)

    def test_a_hand_dragged_out_frees_its_side(self):
        self.panel._start(("slot", "R"), QT.QtCore.QPoint(10, 10))
        self.assertEqual(self.scene.log[-1], ("target", (ROOT, "R")))


# ------------------------------------------------------------------- paint

class Paint(PanelCase):

    def inked(self, image, box):
        x, y, w, h = [int(v) for v in box]
        return sum(1 for px in range(x + 2, x + w - 2, 3) for py in range(y + 2, y + h - 2, 3)
                   if image.pixelColor(px, py).alpha() > 0)

    def test_a_weapon_on_the_floor_is_dimmed_and_tagged(self):
        import maya_hubstyle
        self.panel.holding = dict(self.scene.hold, L=Holding(
            "floor", "|SpearMesh", "Spear_01", "Spear 01"))
        status = maya_hubstyle.TOKENS["status"]

        def tagged(image):
            x, y, w, _h = [int(v) for v in self.rects["well_L"]]
            return sum(1 for px in range(x + 2, x + w - 2)
                       for py in range(y + 4, y + 22)
                       if image.pixelColor(px, py).name() == status)
        on_floor = tagged(self.image())
        self.panel.holding = dict(self.scene.hold, L=Holding(
            "hand", "|SpearMesh", "Spear_01", "Spear 01"))
        self.assertGreater(on_floor, 50)
        self.assertEqual(tagged(self.image()), 0)        # held: no tag

    def test_a_following_hand_names_the_weapon_it_rides(self):
        self.panel.holding = dict(self.scene.hold, L=Holding(
            "follows", "|LongSwordMesh", "LongSword_02", "Long Sword 02"))
        self.panel.pixmaps = {}
        self.panel.turned = {}
        self.assertGreater(self.inked(self.image(), self.rects["well_L"]), 3)

    def test_a_held_weapon_with_no_icon_names_itself(self):
        self.panel.pixmaps = {}
        self.assertGreater(self.inked(self.image(), self.rects["well_R"]), 3)

    def test_a_held_icon_that_cannot_be_fitted_draws_nothing_wrong(self):
        self.panel.pixmaps["LongSword_02"] = QT.QtGui.QPixmap()
        self.assertGreater(self.image().width(), 0)

    def test_a_dragged_hand_is_refused_lit_and_the_tiles_are_its_target(self):
        import maya_hubstyle
        self.panel._start(("slot", "R"), QT.QtCore.QPoint(10, 10))
        image = self.image()
        hx, hy, hw, _hh = self.rects["hand_R"]
        self.assertEqual(image.pixelColor(int(hx + hw // 2), int(hy)).name(),
                         maya_hubstyle.TOKENS["danger"])
        lx, ly, lw, _lh = self.rects["hand_L"]
        self.assertEqual(image.pixelColor(int(lx + lw // 2), int(ly)).name(),
                         maya_hubstyle.TOKENS["accent"])
        tx, ty, tw, _th = self.rects["tilesarea"]
        self.assertEqual(image.pixelColor(int(tx + tw // 2), int(ty - 1)).name(),
                         maya_hubstyle.TOKENS["accent"])

    def test_a_hovered_hand_is_lit_without_an_outline(self):
        import maya_hubstyle
        self.panel._hover = ("slot", "L")
        image = self.image()
        x, y, w, _h = self.rects["hand_L"]
        self.assertEqual(image.pixelColor(int(x + w - 10), int(y + 10)).name(),
                         maya_hubstyle.TOKENS["card_active"])
        self.assertNotEqual(image.pixelColor(int(x + w // 2), int(y)).name(),
                            maya_hubstyle.TOKENS["accent"])

    def test_a_tile_being_dragged_is_faded_and_lit(self):
        import maya_hubstyle
        self.panel._start(("tile", "Spear_01"), QT.QtCore.QPoint(10, 10))
        image = self.image()
        x, y, _w, h = self.panel.tile_of("Spear_01")
        self.assertEqual(image.pixelColor(int(x + 3), int(y + h // 3)).name(),
                         maya_hubstyle.TOKENS["hover"])


# ----------------------------------------------------------------- keeper

@unittest.skipIf(QT is None, "no Qt")
class Keeper(Swaps, unittest.TestCase):

    def setUp(self):
        _app()
        self.host = QT.QtWidgets.QWidget()
        self.addCleanup(self.host.deleteLater)
        classes = inv._classes()
        self.panel = classes["InventoryPanel"](FakeScene(), self.host)
        self.keeper = classes["Keeper"](self.panel, self.panel)

    def test_a_resize_of_the_host_fits_the_panel(self):
        self.host.resize(400, 10)
        event = QT.QtGui.QResizeEvent(QT.QtCore.QSize(400, 10), QT.QtCore.QSize(1, 1))
        self.assertFalse(self.keeper.eventFilter(self.host, event))
        self.assertEqual(self.host.height(), self.panel.height_for(400))
        self.assertEqual(self.panel.geometry(), self.host.rect())

    def test_other_events_are_let_through_untouched(self):
        self.host.resize(400, 10)
        self.assertFalse(self.keeper.eventFilter(
            self.host, QT.QtCore.QEvent(QT.QtCore.QEvent.Show)))
        self.assertEqual(self.host.height(), 10)

    def test_a_fit_that_raises_is_swallowed(self):
        def boom(host):
            raise RuntimeError("gone")
        self.panel.fit = boom
        event = QT.QtGui.QResizeEvent(QT.QtCore.QSize(400, 10), QT.QtCore.QSize(1, 1))
        self.assertFalse(self.keeper.eventFilter(self.host, event))


# ----------------------------------------------------------- attach, live

@unittest.skipIf(QT is None, "no Qt")
class Attach(Swaps, unittest.TestCase):
    """Laid over the card's placeholder: found by name, sized by the keeper,
    registered under the name the asking scope gives the placeholder."""

    def setUp(self):
        _app()
        saved = dict(inv._PANELS)
        inv._PANELS.clear()
        self.addCleanup(self._restore, saved)
        self.host = QT.QtWidgets.QWidget()
        self.host.resize(360, 20)
        self.addCleanup(self.host.deleteLater)
        self.asked = []
        self.swap(maya_hubqt, "find", lambda name, layout=False: (
            self.asked.append((name, layout)) or self.host))
        self.swap(inv, "close_windows", lambda: self.asked.append("closed"))

    def _restore(self, saved):
        inv._PANELS.clear()
        inv._PANELS.update(saved)

    def test_no_qt_or_no_placeholder_lays_nothing(self):
        self.swap(maya_hubqt, "qt", lambda: None)
        self.assertIsNone(inv.attach(scene=FakeScene()))
        maya_hubqt.qt = lambda: QT
        maya_hubqt.find = lambda name, layout=False: None
        self.assertIsNone(inv.attach(scene=FakeScene()))
        self.assertEqual(inv._PANELS, {})

    def test_the_panel_lies_over_the_placeholder_and_is_live(self):
        scene = FakeScene()
        panel = inv.attach(scene=scene)
        self.addCleanup(panel.deleteLater)
        self.assertEqual(self.asked, [(inv.PLACEHOLDER, True), "closed"])
        self.assertIs(panel.parentWidget(), self.host)
        self.assertIs(panel._host, self.host)
        self.assertEqual(self.host.height(), panel.height_for(360))
        self.assertEqual(panel.geometry(), self.host.rect())
        self.assertIs(panel.scene, scene)                  # no copy: the scene itself
        self.assertIs(inv.live(), panel)
        self.assertIsNone(inv.live("someOtherPlaceholder"))

    def test_the_keeper_follows_the_host(self):
        panel = inv.attach(scene=FakeScene())
        self.addCleanup(panel.deleteLater)
        self.host.show()
        self.host.resize(260, 5)
        QT.QtWidgets.QApplication.instance().processEvents()
        self.assertEqual(self.host.height(), panel.height_for(260))
        self.host.hide()

    def test_in_a_popup_copy_it_is_the_copys_own(self):
        scope = hubcopy.Scope("hubcopyT", "weapons")
        scope.names[inv.PLACEHOLDER] = "copy|" + inv.PLACEHOLDER
        scene = FakeScene()
        with hubcopy.entered(scope):
            panel = inv.attach(scene=scene)
            self.addCleanup(panel.deleteLater)
            self.assertIs(inv.live(), panel)
        self.assertEqual(panel.objectName(), inv.OBJECT_NAME + "_hubcopyT")
        self.assertIsNone(inv.live())                      # the hub has none
        self.assertIsInstance(panel.scene, hubcopy.Bound)
        self.assertIn("copy|" + inv.PLACEHOLDER, inv._PANELS)

    def test_a_deleted_panel_is_no_longer_live(self):
        panel = inv.attach(scene=FakeScene())
        panel.deleteLater()
        QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.DeferredDelete)
        self.assertIsNone(inv.live())
        self.assertNotIn(inv.PLACEHOLDER, inv._PANELS)

    def test_live_with_no_answer_from_qt_forgets_the_panel(self):
        inv._PANELS[inv.PLACEHOLDER] = object()

        def boom():
            raise RuntimeError("no Qt")
        self.swap(inv, "_classes", boom)
        self.assertIsNone(inv.live())
        self.assertEqual(inv._PANELS, {})

    def test_a_new_panel_prunes_the_deleted_ones(self):
        classes = inv._classes()
        q = classes["qt"]
        inv._PANELS["closedCopy"] = "dead"
        inv._PANELS["brokenCopy"] = "broken"
        alive = classes["InventoryPanel"](FakeScene())
        self.addCleanup(alive.deleteLater)
        inv._PANELS["openCopy"] = alive
        real = q.shiboken

        class Shiboken(object):
            @staticmethod
            def isValid(obj):
                if obj == "broken":
                    raise RuntimeError("shiboken")
                return obj != "dead" and real.isValid(obj)
        self.swap(q, "shiboken", Shiboken())
        inv._prune()
        self.assertEqual(sorted(inv._PANELS), ["openCopy"])


@unittest.skipIf(QT is None, "no Qt")
class OldWindows(Swaps, unittest.TestCase):
    """An older build's floating inventory, found by name and closed."""

    def test_the_old_window_and_ghost_are_closed(self):
        app = _app()
        old = QT.QtWidgets.QWidget()
        old.setObjectName(inv.WINDOW_NAME)
        ghost = QT.QtWidgets.QWidget()
        ghost.setObjectName(inv.GHOST_NAME)
        other = QT.QtWidgets.QWidget()
        other.setObjectName("somebodyElse")
        for each in (old, ghost, other):
            each.show()
            self.addCleanup(_later, each)
        found = inv._windows()
        self.assertIn(old, found)
        self.assertIn(ghost, found)
        self.assertNotIn(other, found)
        inv.close_windows()
        self.assertFalse(old.isVisible())
        self.assertFalse(ghost.isVisible())
        self.assertTrue(other.isVisible())
        del app

    def test_a_window_that_cannot_close_is_left(self):
        class Stubborn(object):
            def close(self):
                raise RuntimeError("no")

            def deleteLater(self):
                raise RuntimeError("no")
        self.swap(inv, "_windows", lambda: [Stubborn()])
        inv.close_windows()                               # nothing raised

    def test_no_qt_no_windows(self):
        self.swap(maya_hubqt, "qt", lambda: None)
        self.assertEqual(inv._windows(), [])


if __name__ == "__main__":
    unittest.main()

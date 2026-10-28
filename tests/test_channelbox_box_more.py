"""Our Channel Box, the parts its first tests do not reach (2026-10-27): the head's
layer chip and its menu, the effects layer drawn at every age, the editor's keys, a
section's hover and its closing, the value ink of muted / changed / breakdown
channels, the right-button menu and every row of it, the enum menu, and the guarded
failures. Offscreen Qt, a fake link, events sent to the box's own widgets; the
motion's clock is the test's.

Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""
import contextlib
import io
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_channelbox import box as box_module, look


def chan(attr, value, kind="double", keys=(), on_key=False, **kw):
    plug = "IKLeg_L." + attr
    d = {"key": attr, "node": "IKLeg_L", "attr": attr, "plug": plug, "nice": attr.title(),
         "kind": kind, "value": value, "names": None, "lo": None, "hi": None, "locked": False,
         "muted": False, "source": "curve" if keys else None, "keys": list(keys),
         "breakdowns": [], "on_key": on_key, "breakdown": False, "changed": False,
         "targets": [plug, "IKLeg_R." + attr]}
    d.update(kw)
    return d


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.frame = 12.0
        self.layer_list = [("BaseAnimation", "BaseAnimation", False), ("AnimLayer1", "AnimLayer1", True)]
        self.label = "AnimLayer1"
        self.chans = [chan("translateX", 4.8, "doubleLinear", [0, 12, 24], True),
                      chan("translateY", 9.4, "doubleLinear", [0, 6, 24]),
                      chan("rotateX", -18.5, "doubleAngle"),
                      chan("rotateY", 3.0, "doubleAngle", [0, 24], muted=True),
                      chan("rotateZ", 7.0, "doubleAngle", [0, 24], changed=True),
                      chan("scaleX", 1.0, locked=True),
                      chan("scaleY", 2.0, keys=[12], on_key=True, breakdown=True, breakdowns=[12]),
                      chan("visibility", 1, "bool"),
                      chan("rotateOrder", 0, "enum", names=["xyz", "yzx", "zxy"]),
                      chan("swivel", 0.0, source="driven")]

    def snapshot(self, opened=()):
        self.log.append(("snapshot", opened))
        return {"objects": ["|IKLeg_R", "|IKLeg_L"], "lead": "|IKLeg_L", "frame": self.frame,
                "sections": [{"key": "main", "kind": "main", "label": "IKLeg_L", "title": "",
                              "channels": [dict(c, keys=list(c["keys"])) for c in self.chans]},
                             {"key": "shapes:IKLeg_LShape", "kind": "shapes", "label": "IKLeg_LShape",
                              "title": "SHAPES",
                              "channels": [chan("lineWidth", -1.0)] if "shapes:IKLeg_LShape" in opened else []}]}

    def now(self):
        return self.frame

    def values(self, plugs):
        return [next((c["value"] for c in self.chans if c["plug"] == p), None) for p in plugs]

    def write(self, pairs):
        self.log.append(("write", list(pairs)))
        for plug, value in pairs:
            for c in self.chans:
                if c["plug"] == plug:
                    c["value"] = value
        return len(pairs)

    def key(self, plugs, breakdown=False):
        self.log.append(("key", list(plugs), breakdown))
        for c in self.chans:
            if c["plug"] in plugs and self.frame not in c["keys"]:
                c["keys"].append(self.frame)
                c["on_key"] = True
                c["source"] = "curve"
        return len(plugs)

    def unkey(self, plugs, frame):
        self.log.append(("unkey", list(plugs), frame))
        for c in self.chans:
            if c["plug"] in plugs and frame in c["keys"]:
                c["keys"].remove(frame)
                c["on_key"] = False
        return 1

    def mute(self, plugs, on):
        self.log.append(("mute", list(plugs), on))

    def lock(self, plugs, on):
        self.log.append(("lock", list(plugs), on))

    def select_connection(self, plugs):
        self.log.append(("select_connection", list(plugs)))

    def break_connections(self, plugs):
        self.log.append(("break_connections", list(plugs)))

    def sync_selection(self, plugs):
        self.log.append(("sync", list(plugs)))
        return True

    def speed(self):
        return 1.0

    def set_speed(self, value):
        self.log.append(("speed", value))

    def precision(self):
        return 3

    def chunk_open(self, name):
        self.log.append(("open", name))

    def chunk_close(self):
        self.log.append(("close",))

    def layers(self):
        return list(self.layer_list)

    def layer_label(self):
        return self.label

    def pick_layer(self, name):
        self.log.append(("pick_layer", name))
        self.label = name

    def show_maya_box(self):
        self.log.append(("maya_box",))


def boom(*_a, **_k):
    raise RuntimeError("boom")


def find_action(menu, label):
    for a in menu.actions():
        if a.text() == label:
            return a
    return None


@contextlib.contextmanager
def auto_menu(pick=None):
    """QMenu.exec answered at once with the row labelled `pick` (None: dismissed)."""
    QtWidgets = QT.QtWidgets
    real = QtWidgets.QMenu
    shown = []

    class AutoMenu(real):
        def exec(self, *_args):
            shown.append([a.text() for a in self.actions()])
            return find_action(self, pick) if pick else None

    QtWidgets.QMenu = AutoMenu
    try:
        yield shown
    finally:
        QtWidgets.QMenu = real


@contextlib.contextmanager
def printed():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        yield out


@contextlib.contextmanager
def swapped(obj, name, value):
    own = getattr(obj, "__dict__", {})
    had = name in own
    old = own[name] if had else None
    setattr(obj, name, value)
    try:
        yield
    finally:
        if had:
            setattr(obj, name, old)
        else:
            delattr(obj, name)


@unittest.skipIf(QT is None, "no Qt")
class Base(unittest.TestCase):

    motion = True

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.box = box_module.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=self.motion)
        self.t = [1000.0]
        self.box.clock = lambda: self.t[0]
        self.box.resize(340, 520)
        self.box.show()
        self.app.processEvents()
        self.box.refresh(effects=False)
        self.app.processEvents()

    def tearDown(self):
        self.box.timer.stop()
        self.box.close()
        self.box.deleteLater()
        QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.DeferredDelete)

    # -- helpers ---------------------------------------------------------------
    def row_of(self, key):
        for i, r in enumerate(self.box.rows):
            if r["kind"] == "channel" and r["channel"]["key"] == key:
                return i, self.box.placed[i][2]
        raise KeyError(key)

    def chan_of(self, key):
        return self.box.rows[self.row_of(key)[0]]["channel"]

    @staticmethod
    def point(rect):
        x, y, w, h = rect
        return QT.QtCore.QPointF(x + w / 2.0, y + h / 2.0)

    def mouse(self, kind, pos, widget=None, mods=None, button=None):
        Qt = QT.QtCore.Qt
        widget = widget or self.box.canvas
        button = button or Qt.LeftButton
        mods = mods if mods is not None else Qt.NoModifier
        types = {"press": QT.QtCore.QEvent.MouseButtonPress, "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease,
                 "double": QT.QtCore.QEvent.MouseButtonDblClick}
        buttons = Qt.NoButton if kind in ("release", "move") else button
        ev = QT.QtGui.QMouseEvent(types[kind], pos, widget.mapToGlobal(pos.toPoint()).toPointF(),
                                  Qt.NoButton if kind == "move" else button, buttons, mods)
        QT.QtWidgets.QApplication.sendEvent(widget, ev)

    def plain(self, widget, kind):
        QT.QtWidgets.QApplication.sendEvent(widget, QT.QtCore.QEvent(getattr(QT.QtCore.QEvent, kind)))

    def key(self, widget, key, text=""):
        ev = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, key, QT.QtCore.Qt.NoModifier, text)
        QT.QtWidgets.QApplication.sendEvent(widget, ev)

    def render(self, widget=None):
        widget = widget or self.box
        img = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        widget.render(img)
        return img

    def step_until(self, cond, limit=200):
        for _ in range(limit):
            if cond():
                return True
            self.t[0] += 16.0
            self.box._step()
        return cond()

    def writes(self):
        return [e for e in self.link.log if e[0] == "write"]


class Defaults(unittest.TestCase):

    @unittest.skipIf(QT is None, "no Qt")
    def test_the_hub_s_tokens_and_motion_when_none_are_given(self):
        import maya_hubmotion
        app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        with swapped(maya_hubmotion, "enabled", boom):
            box = box_module.make(FakeLink(), 1.0, None, motion=None)
        self.addCleanup(box.deleteLater)
        self.assertTrue(box.motion, "a failing switch reads as on")
        self.assertEqual(box.tokens, maya_hubstyle.TOKENS)
        self.assertEqual(box_module._tokens(), maya_hubstyle.TOKENS)
        del app


class Head(Base):
    """The lead object's head: the layer chip lifts, flashes and opens the layers."""

    def chip(self):
        return self.box.head.chip_rect()

    def test_the_chip_lifts_under_the_mouse_and_drops_on_leave(self):
        head = self.box.head
        self.mouse("move", self.chip().center(), head)
        self.assertEqual(head.goal, 1.0)
        self.assertTrue(self.step_until(lambda: head.hover > 0.99))
        img = self.render(head)
        self.assertFalse(getattr(head, "_failed", False))
        self.mouse("move", QT.QtCore.QPointF(5, 5), head)
        self.assertEqual(head.goal, 0.0)
        head.goal = 1.0
        self.plain(head, "Leave")
        self.assertEqual(head.goal, 0.0)
        del img

    def test_a_press_on_the_chip_flashes_and_picks_a_layer(self):
        head = self.box.head
        with auto_menu("   BaseAnimation") as shown:
            self.mouse("press", self.chip().center(), head)
        self.assertEqual(shown, [["   BaseAnimation", "• AnimLayer1"]])
        self.assertIn(("pick_layer", "BaseAnimation"), self.link.log)
        self.assertEqual(self.box.layer_text, "BaseAnimation")
        self.t[0] += 30                                     # mid flash
        img = self.render(head)
        self.assertFalse(getattr(head, "_failed", False))
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])
        r = self.chip()
        c = img.pixelColor(int(r.left() + 6), int(r.center().y()))
        self.assertLess(abs(c.red() - accent.red()), 70, "the chip flashes toward the accent")
        self.assertTrue(head.busy(self.t[0]))

    def test_a_press_off_the_chip_opens_nothing(self):
        with auto_menu("   BaseAnimation") as shown:
            self.mouse("press", QT.QtCore.QPointF(5, 5), self.box.head)
        self.assertEqual(shown, [])

    def test_no_layers_no_menu(self):
        self.link.layer_list = []
        with auto_menu("   BaseAnimation") as shown:
            self.box.layer_menu(QT.QtCore.QPoint(0, 0))
        self.assertEqual(shown, [])

    def test_a_failing_label_or_precision_reads_as_none(self):
        self.link.layer_label = boom
        self.link.precision = boom
        self.box.refresh()
        self.assertEqual(self.box.layer_text, "")
        self.assertIsNone(self.box.head.chip_rect())
        self.assertEqual(self.box.precision, 3)


class Effects(Base):
    """The effects layer at every age: a set's flash, a reached key's light, a deleted
    key's pieces and the wait before them."""

    def fx(self):
        return self.box.canvas.fx

    def rect(self, key):
        return look.cell_rect(self.row_of(key)[1]["mark"])

    def test_every_kind_is_drawn_through_its_life_and_then_dropped(self):
        fx = self.fx()
        fx.add("set", rect=self.rect("translateY"), hex="#e07a36")
        fx.add("light", rect=self.rect("rotateX"), hex="#e07a36")
        fx.add("delete", rect=self.rect("rotateZ"), hex="#e07a36", delay=60.0)
        self.assertEqual(len(fx.items), 3)
        lit = self.rect("rotateX")
        for dt in (10, 70, 200, 560):                       # the wait, the flash, the pieces, the fade
            self.t[0] += dt
            img = self.render(fx)
            self.assertFalse(getattr(fx, "_failed", False), "at +%d ms" % dt)
            if dt == 70:
                self.assertGreater(img.pixelColor(int(lit[0] + lit[2] / 2), int(lit[1] + lit[3] / 2)).alpha(), 0,
                                   "the reached key's light")
        self.assertTrue(self.step_until(lambda: not fx.items, limit=400))
        self.assertFalse(self.box.timer.isActive())

    def test_a_waiting_piece_is_drawn_as_its_key(self):
        fx = self.fx()
        r = self.rect("rotateZ")
        fx.add("delete", rect=r, hex="#e07a36", delay=200.0)
        self.t[0] += 10
        img = self.render(fx)
        c = img.pixelColor(int(r[0] + r[2] / 2), int(r[1] + r[3] / 2))
        self.assertEqual(c.name(), "#e07a36")

    def test_a_set_flash_lights_its_cell(self):
        fx = self.fx()
        r = self.rect("translateY")
        fx.add("set", rect=r, hex="#e07a36")
        self.t[0] += 40
        img = self.render(fx)
        self.assertGreater(img.pixelColor(int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)).alpha(), 0)

    def test_an_item_past_its_life_is_not_drawn(self):
        fx = self.fx()
        r = self.rect("translateY")
        fx.add("set", rect=r, hex="#e07a36")
        self.t[0] += 5000                                   # no step pruned it yet
        img = self.render(fx)
        self.assertEqual(img.pixelColor(int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)).alpha(), 0)

    def test_a_flash_at_its_last_breath_draws_nothing(self):
        fx = self.fx()
        r = self.rect("translateY")
        fx.add("set", rect=r, hex="#e07a36")
        self.t[0] += fx.items[0]["life"] - 1.0
        img = self.render(fx)
        self.assertFalse(getattr(fx, "_failed", False))
        self.assertLess(img.pixelColor(int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)).alpha(), 4)

    def test_with_animations_off_nothing_is_added(self):
        self.box.motion = False
        self.fx().add("set", rect=self.rect("translateY"), hex="#e07a36")
        self.assertEqual(self.fx().items, [])

    def test_a_broken_item_prints_once(self):
        fx = self.fx()
        fx.items.append({"kind": "set", "rect": None, "t0": self.t[0], "delay": 0.0, "life": 500, "seed": 1,
                         "hex": "#e07a36"})
        with printed() as out:
            self.render(fx)
            self.render(fx)
        self.assertTrue(fx._failed)
        self.assertEqual(out.getvalue().count("Traceback"), 1)

    def test_keys_of_a_muted_or_breakdown_channel_take_their_colour(self):
        self.mouse("press", self.point(self.rect("rotateY")))         # muted, off its key
        set_items = [i for i in self.fx().items if i["kind"] == "set"]
        self.assertEqual(set_items[-1]["hex"], look.MUTED)
        self.assertEqual(self.box._key_hex(self.chan_of("scaleY")), look.BREAKDOWN)

    def test_effects_for_channels_not_shown_are_dropped(self):
        self.box.key_effects(["nope"], ["nope"])
        self.assertEqual(self.fx().items, [])

    def test_a_box_whose_step_fails_prints_once(self):
        self.box._step = boom
        with printed() as out:
            self.box._animate()
            self.box._animate()
        self.assertEqual(out.getvalue().count("Traceback"), 1)


class Paint(Base):
    """The rows' ink: muted, changed and breakdown cells and values, a section lit and
    open, a key cell flashing, glows under the mouse."""

    def test_the_cells_and_values_of_every_state(self):
        img = self.render()
        self.assertFalse(getattr(self.box.canvas, "_failed", False))
        head = self.box.head.height()

        def cell(key):
            x, y, w, h = look.cell_rect(self.row_of(key)[1]["mark"])
            return img.pixelColor(int(x + w / 2), int(y + h / 2) + head)
        self.assertEqual(cell("scaleY").name(), QT.QtGui.QColor(look.BREAKDOWN).name())

        def beside(key):                                   # just outside the cell's left edge
            x, y, w, h = look.cell_rect(self.row_of(key)[1]["mark"])
            return img.pixelColor(int(x - 1.5), int(y + h / 2) + head).name()
        panel = QT.QtGui.QColor(maya_hubstyle.TOKENS["panel"]).name()
        self.assertEqual(beside("rotateX"), panel, "a plain cell has no ring")
        self.assertNotEqual(beside("rotateZ"), panel, "a changed cell wears the dashed ring")

    def test_a_section_lifts_under_the_mouse_and_turns_open(self):
        i = [n for n, r in enumerate(self.box.rows) if r["kind"] == "section"][0]
        self.mouse("move", self.point(self.box.placed[i][2]["row"]))
        self.assertTrue(self.step_until(lambda: self.box.level(("row", i)) > 0.99))
        self.render()
        self.mouse("press", self.point(self.box.placed[i][2]["row"]))
        self.assertIn("shapes:IKLeg_LShape", self.box.opened)
        self.render()
        self.assertFalse(getattr(self.box.canvas, "_failed", False))
        i = [n for n, r in enumerate(self.box.rows) if r["kind"] == "section"][0]
        self.mouse("press", self.point(self.box.placed[i][2]["row"]))
        self.assertNotIn("shapes:IKLeg_LShape", self.box.opened)

    def test_a_flashing_key_cell_and_a_lit_value_well(self):
        i, parts = self.row_of("rotateX")
        self.mouse("move", self.point(parts["value"]))
        self.assertTrue(self.step_until(lambda: self.box.level(("value", i)) > 0.99))
        self.mouse("press", self.point(look.cell_rect(parts["mark"])))
        self.t[0] += 20
        self.assertGreater(self.box.flashing(("mark", i), self.t[0]), 0.5)
        img = self.render()
        self.assertFalse(getattr(self.box.canvas, "_failed", False))
        del img

    def test_the_hover_falls_back_to_rest_and_the_levels_go(self):
        _, parts = self.row_of("rotateX")
        self.mouse("move", self.point(parts["mark"]))
        self.assertTrue(self.step_until(lambda: self.box.levels))
        self.plain(self.box.canvas, "Leave")
        self.assertTrue(self.step_until(lambda: not self.box.levels and not self.box.timer.isActive()))

    def test_a_toggled_bool_pops_its_well(self):
        i, parts = self.row_of("visibility")
        self.mouse("press", self.point(parts["value"]))
        self.mouse("release", self.point(parts["value"]))
        self.t[0] += 60
        self.assertTrue(0.7 <= self.box.popping(("value", i), self.t[0]) < 1.0)
        self.assertGreater(self.box.flashing(("value", i), self.t[0]), 0.0)
        self.assertTrue(self.box.busy(self.t[0]))
        self.render()
        self.t[0] += 90                                     # the press's flash over, the pop not
        self.assertEqual(self.box.flashing(("value", i), self.t[0]), 0.0)
        self.assertTrue(self.box.busy(self.t[0]))


class Hand(Base):
    """Presses, releases, double clicks and keys on the canvas."""

    def test_buttons_other_than_the_left_and_presses_off_the_rows_do_nothing(self):
        _, parts = self.row_of("rotateX")
        self.mouse("press", self.point(parts["name"]), button=QT.QtCore.Qt.MiddleButton)
        self.assertIsNone(self.box.canvas.press)
        self.mouse("press", QT.QtCore.QPointF(10, self.box.canvas.height() - 2))
        self.assertIsNone(self.box.canvas.press)
        self.mouse("release", QT.QtCore.QPointF(10, 10))           # nothing pressed
        self.assertEqual(self.box.selected, set())

    def test_the_key_cell_of_a_locked_channel_keys_nothing(self):
        _, parts = self.row_of("scaleX")
        self.mouse("press", self.point(look.cell_rect(parts["mark"])))
        self.assertNotIn("key", [e[0] for e in self.link.log])

    def test_an_enum_value_opens_its_names_and_sets_the_pick(self):
        _, parts = self.row_of("rotateOrder")
        self.mouse("press", self.point(parts["value"]))
        with auto_menu("   zxy") as shown:
            self.mouse("release", self.point(parts["value"]))
        self.assertEqual(shown, [["• xyz", "   yzx", "   zxy"]])
        self.assertEqual(self.writes()[-1][1], [("IKLeg_L.rotateOrder", 2), ("IKLeg_R.rotateOrder", 2)])
        self.assertEqual(self.chan_of("rotateOrder")["value"], 2)

    def test_a_double_click_opens_the_editor_only_on_a_typed_value(self):
        for key, part in (("rotateX", "name"), ("visibility", "value"), ("rotateOrder", "value"),
                          ("scaleX", "value")):
            self.mouse("double", self.point(self.row_of(key)[1][part]))
            self.assertIsNone(self.box.canvas.editor, key)
        self.mouse("double", QT.QtCore.QPointF(10, self.box.canvas.height() - 2))
        self.assertIsNone(self.box.canvas.editor)

    def test_a_second_editor_ends_the_first_without_applying_it(self):
        p = self.point(self.row_of("rotateX")[1]["value"])
        self.mouse("double", p)
        first = self.box.canvas.editor
        first.setText("99")
        self.mouse("double", self.point(self.row_of("translateY")[1]["value"]))
        self.assertIsNot(self.box.canvas.editor, first)
        self.assertTrue(first.done)
        self.assertEqual(self.writes(), [])

    def test_escape_leaves_the_value_and_other_keys_type(self):
        self.mouse("double", self.point(self.row_of("rotateX")[1]["value"]))
        editor = self.box.canvas.editor
        editor.clear()
        self.key(editor, QT.QtCore.Qt.Key_5, "5")
        self.assertEqual(editor.text(), "5")
        self.key(editor, QT.QtCore.Qt.Key_Escape)
        self.assertIsNone(self.box.canvas.editor)
        self.app.processEvents()
        self.assertEqual(self.writes(), [])

    def test_a_key_that_starts_no_value_is_the_canvas_s(self):
        self.box.selected = {"rotateX"}
        self.key(self.box.canvas, QT.QtCore.Qt.Key_Left)
        self.assertIsNone(self.box.canvas.editor)
        self.box.selected = set()
        self.key(self.box.canvas, QT.QtCore.Qt.Key_5, "5")       # nothing selected: no editor
        self.assertIsNone(self.box.canvas.editor)

    def test_a_slide_on_an_unselected_channel_selects_it_first(self):
        _, parts = self.row_of("translateY")
        p = self.point(parts["name"])
        self.mouse("press", p)
        self.mouse("move", QT.QtCore.QPointF(p.x() + 10, p.y()))
        self.mouse("release", QT.QtCore.QPointF(p.x() + 10, p.y()))
        self.assertEqual(self.box.selected, {"translateY"})
        self.assertAlmostEqual(dict(self.writes()[-1][1])["IKLeg_L.translateY"], 9.4 + 10 * 0.1)
        press = {"x": 0.0, "moved": False, "channel": self.chan_of("rotateX")}
        self.box.drag(press, 1.0, QT.QtCore.Qt.NoModifier)       # under 3 px: not a drag yet
        self.assertFalse(press["moved"])

    def test_a_failing_sync_still_selects(self):
        self.link.sync_selection = boom
        _, parts = self.row_of("rotateX")
        self.mouse("press", self.point(parts["name"]))
        self.mouse("release", self.point(parts["name"]))
        self.assertEqual(self.box.selected, {"rotateX"})

    def test_values_read_again_from_elsewhere(self):
        next(c for c in self.link.chans if c["key"] == "rotateX")["value"] = 42.0
        self.link.values = lambda plugs: [42.0 if p.endswith("rotateX") else None for p in plugs]
        self.box.on_values()
        self.assertEqual(self.chan_of("rotateX")["value"], 42.0)
        self.assertEqual(self.chan_of("translateX")["value"], 4.8, "a None read keeps the value")


class Menus(Base):
    """The right button: the rows, each press, the guarded failures."""

    def context(self, key, pick):
        pos = self.point(self.row_of(key)[1]["name"]).toPoint()
        ev = QT.QtGui.QContextMenuEvent(QT.QtGui.QContextMenuEvent.Mouse, pos, self.box.canvas.mapToGlobal(pos))
        with auto_menu(pick) as shown:
            QT.QtWidgets.QApplication.sendEvent(self.box.canvas, ev)
        return shown

    def test_the_right_button_selects_the_channel_under_it_and_mutes_it(self):
        shown = self.context("rotateX", "Mute Selected")
        self.assertEqual(self.box.selected, {"rotateX"})
        self.assertEqual(shown[0][0], "Key Selected")
        self.assertIn(("mute", ["IKLeg_L.rotateX", "IKLeg_R.rotateX"], True), self.link.log)
        names = [e[0] for e in self.link.log]
        self.assertLess(names.index("open"), names.index("mute"))
        self.assertLess(names.index("mute"), names.index("close"))

    def test_the_right_button_on_a_selected_channel_keeps_the_selection(self):
        self.box.selected = {"rotateX", "translateY"}
        self.context("rotateX", "Unlock Selected")
        self.assertEqual(self.box.selected, {"rotateX", "translateY"})
        self.assertEqual(self.link.log[-3][0], "lock")
        self.assertFalse(self.link.log[-3][2])

    def test_a_section_s_menu_is_the_box_s(self):
        i = [n for n, r in enumerate(self.box.rows) if r["kind"] == "section"][0]
        pos = self.point(self.box.placed[i][2]["row"]).toPoint()
        ev = QT.QtGui.QContextMenuEvent(QT.QtGui.QContextMenuEvent.Mouse, pos, self.box.canvas.mapToGlobal(pos))
        with auto_menu(None) as shown:
            QT.QtWidgets.QApplication.sendEvent(self.box.canvas, ev)
        self.assertEqual(len(shown), 1)
        self.assertEqual(self.box.selected, set())

    def rows(self):
        return dict((r[0], r[1]) for r in self.box.menu_rows() if r)

    def test_key_and_breakdown_selected_and_every_channel_with_none_selected(self):
        self.box.selected = {"translateX", "rotateX"}
        self.rows()["Key Selected"]()
        keyed = [e for e in self.link.log if e[0] == "key"]
        self.assertEqual(keyed[-1], ("key", ["IKLeg_L.translateX", "IKLeg_R.translateX",
                                             "IKLeg_L.rotateX", "IKLeg_R.rotateX"], False))
        self.assertTrue(any(i["kind"] == "set" for i in self.box.canvas.fx.items), "the standing key flashes")
        self.rows()["Breakdown Selected"]()
        self.assertTrue([e for e in self.link.log if e[0] == "key" and e[2]])
        self.box.selected = set()
        self.rows()["Key Selected"]()
        plugs = [e for e in self.link.log if e[0] == "key"][-1][1]
        self.assertEqual(len(plugs), 2 * len(self.box.channels()))

    def test_delete_keys_at_the_frame(self):
        self.box.selected = {"translateX", "rotateX"}
        self.rows()["Delete Keys at 12"]()
        self.assertIn(("unkey", ["IKLeg_L.translateX", "IKLeg_R.translateX"], 12.0), self.link.log)
        before = len(self.link.log)
        self.box.selected = {"rotateX"}                           # not on a key: nothing
        self.rows()["Delete Keys at 12"]()
        self.assertEqual(len(self.link.log), before)

    def test_every_row_that_needs_a_selection_writes_its_plugs(self):
        self.box.selected = {"rotateX"}
        plugs = ["IKLeg_L.rotateX", "IKLeg_R.rotateX"]
        rows = self.rows()
        for label, entry in (("Unmute Selected", ("mute", plugs, False)), ("Lock Selected", ("lock", plugs, True)),
                             ("Select Connection", ("select_connection", plugs)),
                             ("Break Connections", ("break_connections", plugs))):
            rows[label]()
            self.assertIn(entry, self.link.log, label)
        rows["Maya's Channel Box"]()
        self.assertEqual(self.link.log[-1], ("maya_box",))

    def test_with_nothing_selected_the_rows_are_greyed(self):
        rows = self.rows()
        for label in ("Mute Selected", "Lock Selected", "Select Connection", "Copy Values", "Paste Values"):
            self.assertIsNone(rows[label], label)

    def test_the_channel_speed_rows(self):
        rows = self.rows()
        self.assertIn("• Channel Speed: Medium", rows)
        rows["   Channel Speed: Fast"]()
        self.assertEqual(self.box.speed, 10.0)
        self.assertEqual(self.link.log[-1], ("speed", 10.0))
        self.assertIn("• Channel Speed: Fast", self.rows())

    def test_paste_passes_locked_channels_and_values_it_has_none_for(self):
        self.box.selected = {"translateX", "rotateX"}
        self.box.copy_values()
        self.box.selected = {"translateY", "scaleX"}
        self.box.paste_values()
        self.assertEqual(self.writes(), [])
        self.box.selected = {"translateX"}
        self.box.copy_values()
        self.box.selected = {"scaleX", "rotateZ"}
        self.box.paste_values()
        self.assertEqual(dict(self.writes()[-1][1]), {"IKLeg_L.rotateZ": 4.8, "IKLeg_R.rotateZ": 4.8})
        self.box.clipboard = {}
        before = len(self.link.log)
        self.box.paste_values()
        self.assertEqual(len(self.link.log), before)

    def test_a_dismissed_menu_runs_nothing_and_a_failing_row_is_printed(self):
        with auto_menu(None):
            self.assertFalse(self.box._menu(QT.QtCore.QPoint(0, 0), [("Go", boom)]))
        with auto_menu("Go"), printed() as out:
            self.assertTrue(self.box._menu(QT.QtCore.QPoint(0, 0), [("Go", boom), None, ("Grey", None)]))
        self.assertIn("boom", out.getvalue())
        with auto_menu("Grey"):
            self.assertFalse(self.box._menu(QT.QtCore.QPoint(0, 0), [("Grey", None)]))

    def test_a_row_runs_when_its_wrapper_died_before_exec_answered(self):
        from tests import menurows
        ran = []
        with menurows.dead_rows(QT.QtWidgets, "Go"):
            self.assertTrue(self.box._menu(QT.QtCore.QPoint(0, 0),
                                           [("Other", lambda: ran.append("other")), None,
                                            ("Go", lambda: ran.append("go"))]))
        self.assertEqual(ran, ["go"])


if __name__ == "__main__":
    unittest.main()

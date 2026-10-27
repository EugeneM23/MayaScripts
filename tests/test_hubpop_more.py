"""maya_hubpop - the rest of a section's floating window: its seams to Maya, the
title's and the edges' other buttons, the card it gives the marks, the fades and
the flash driven frame by frame, the burst's own face and parts, a build that
fails, and the manager's restore and clean-up.

Offscreen Qt; `cmds`, the hub, the screens and Maya's main window replaced as in
tests/test_hubpop.py. Animations are driven by setting their current time (no
sleeping). The popup state on `sys` is a fresh one for each test and put back.
"""

import collections
import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

import maya_hubburst as hubburst
import maya_hubcopy as hubcopy
import maya_hubmotion as hubmotion
import maya_hubpop as hubpop
import maya_hubpop_rules as rules
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
from tests.test_hubcopy import FakeCmds

Section = collections.namedtuple("Section",
                                 "key label module builder frame group icon")

SCREEN = (0, 0, 1920, 1040)     # the one screen's available geometry, physical px
_MISSING = object()


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@contextlib.contextmanager
def maya_modules(**fakes):
    """`maya.<name>` stood in for, one entry at a time (sys.modules and the
    package's attribute both, as `import maya.X as y` reads them), and put back."""
    import maya
    saved = []
    for name, fake in fakes.items():
        key = "maya." + name
        saved.append((key, sys.modules.get(key, _MISSING), name,
                      maya.__dict__.get(name, _MISSING)))
        sys.modules[key] = fake
        setattr(maya, name, fake)
    try:
        yield
    finally:
        for key, module, name, attr in reversed(saved):
            if module is _MISSING:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = module
            if attr is _MISSING:
                if name in maya.__dict__:
                    delattr(maya, name)
            else:
                setattr(maya, name, attr)


def fake_omui(main_window):
    """A maya.OpenMayaUI whose MQtUtil.mainWindow() answers `main_window()`."""
    module = types.ModuleType("maya.OpenMayaUI")
    module.MQtUtil = types.SimpleNamespace(mainWindow=main_window)
    return module


def finish(anim):
    """An animation run to its end now (its last value, then `finished`)."""
    anim.setCurrentTime(anim.duration())


class FakeMaya(FakeCmds):
    """FakeCmds with the option variables a window stores and the deferred calls
    it queues (run by the test, as Maya's idle would)."""

    def __init__(self):
        super(FakeMaya, self).__init__()
        self.vars = {}
        self.deferred_calls = []

    def optionVar(self, *args, **kwargs):                # noqa: N802
        if kwargs.get("exists") is not None:
            return kwargs["exists"] in self.vars
        if "query" in kwargs:
            return self.vars.get(kwargs["query"])
        for flag in ("stringValue", "intValue"):
            if flag in kwargs:
                name, value = kwargs[flag]
                self.vars[name] = value
        return None

    def evalDeferred(self, fn, **kwargs):                # noqa: N802
        self.deferred_calls.append(fn)

    def mayaDpiSetting(self, **_kwargs):                 # noqa: N802
        return 1.0


class FakeHub(object):
    """The hub's face a window asks: its sections, their builders, the card
    button and the rail's dot."""

    HEADER_ONLY = ("hotkeys",)

    def __init__(self, builders):
        self.sections = [
            Section("alpha", "Alpha", "fake_alpha", "build", "f", "scene", "user"),
            Section("beta", "Beta", "fake_beta", "build_beta", "f", "animation",
                    "bulb"),
            Section("hotkeys", "Hotkeys", "fake_alpha", "build", "f", "settings",
                    "keyboard"),
        ]
        self.builders = builders
        self.painted = []
        self.floated = []

    def section(self, key):
        for sec in self.sections:
            if sec.key == key:
                return sec
        return None

    def card_sections(self):
        return [s for s in self.sections if s.key not in self.HEADER_ONLY]

    def _import(self, dotted):
        return self

    def build(self):
        return self.builders["build"]()

    def build_beta(self):
        return self.builders.get("build_beta", lambda: None)()

    def paint_popped(self, key, on):
        self.painted.append((key, on))

    def paint_floating(self, key, on):
        self.floated.append((key, on))


class Seams(unittest.TestCase):
    """A fake cmds, one screen and a fake hub for every test; the popup state on
    `sys` fresh and put back; hubcopy's install flag put back."""

    def setUp(self):
        self.app = _app()
        self.cmds = FakeMaya()
        self.builds = []

        def build_alpha():
            self.builds.append(hubcopy.current())
            self.cmds.text("mayaSceneSetupStatus", label="ready")

        self.hub = FakeHub({"build": build_alpha})

        saved = getattr(sys, "_skeldar_hubpop", _MISSING)
        sys._skeldar_hubpop = {"popups": {}, "timer": None, "queued": False,
                               "tries": 0, "restoring": False}
        self.addCleanup(self._put_state_back, saved)
        installed = hubcopy._state()["installed"]
        self.addCleanup(hubcopy._state().__setitem__, "installed", installed)

        for target, attr, value in (
                (hubpop, "cmds", self.cmds),
                (hubpop, "_hub", lambda: self.hub),
                (hubpop, "_scale", lambda: 1.0),
                (hubpop, "_main_window", lambda: None),
                (hubpop, "screens", lambda: [SCREEN]),
                (hubqt, "path_of", lambda obj: "path|" + obj.objectName())):
            patch = mock.patch.object(target, attr, value)
            patch.start()
            self.addCleanup(patch.stop)
        hubcopy.install(self.cmds)
        #  last added, first run: the windows go while the seams still stand
        self.addCleanup(self._close_all)

    def _close_all(self):
        hubpop.destroy_all(forget=False)
        for scope in hubcopy.live():
            hubcopy.close(scope, None)

    @staticmethod
    def _put_state_back(saved):
        if saved is _MISSING:
            if hasattr(sys, "_skeldar_hubpop"):
                del sys._skeldar_hubpop
        else:
            sys._skeldar_hubpop = saved

    def run_deferred(self):
        calls, self.cmds.deferred_calls = self.cmds.deferred_calls, []
        for fn in calls:
            fn()

    def mouse(self, widget, kind, local, global_pt, button, buttons):
        event = QtGui.QMouseEvent(
            kind, QtCore.QPointF(*local), QtCore.QPointF(*global_pt),
            button, buttons, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(widget, event)
        return event

    def corner(self, popup):
        at = popup.root.mapToGlobal(QtCore.QPoint(4, 4))
        return (at.x(), at.y())


# ----------------------------------------------------------- the Maya seams

class Scale(unittest.TestCase):
    """The display scale read from Maya, 1.0 whenever Maya will not say."""

    def scale_with(self, answer):
        stub = types.SimpleNamespace(mayaDpiSetting=answer)
        with mock.patch.object(hubpop, "cmds", stub):
            return hubpop._scale()

    def test_maya_s_real_scale_value(self):
        self.assertEqual(self.scale_with(lambda **kw: 1.5), 1.5)

    def test_no_answer_is_one(self):
        self.assertEqual(self.scale_with(lambda **kw: None), 1.0)
        self.assertEqual(self.scale_with(lambda **kw: 0), 1.0)

    def test_a_failing_query_is_one(self):
        def broken(**_kw):
            raise RuntimeError("no UI")
        self.assertEqual(self.scale_with(broken), 1.0)


class MainWindow(unittest.TestCase):
    """Maya's main window as a QWidget, fetched through OpenMayaUI each time."""

    def setUp(self):
        _app()
        self.window = QtWidgets.QWidget()
        self.addCleanup(self.window.deleteLater)
        self.ptr = shiboken6.getCppPointer(self.window)[0]

    def test_no_maya_ui_no_window(self):
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: False):
            self.assertIsNone(hubpop._main_window())

    def test_no_qt_no_window(self):
        with mock.patch.object(hubqt, "qt", lambda: None):
            self.assertIsNone(hubpop._main_window())

    def test_the_main_window_is_wrapped_from_maya_s_pointer(self):
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                maya_modules(OpenMayaUI=fake_omui(lambda: self.ptr)):
            found = hubpop._main_window()
        self.assertIsNotNone(found)
        self.assertEqual(shiboken6.getCppPointer(found)[0], self.ptr)

    def test_a_null_pointer_or_a_failure_is_no_window(self):
        def broken():
            raise RuntimeError("no main window yet")
        for answer in (lambda: 0, broken):
            with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                    maya_modules(OpenMayaUI=fake_omui(answer)):
                self.assertIsNone(hubpop._main_window())


class Screens(unittest.TestCase):
    """Every screen's available geometry, never an empty list."""

    def setUp(self):
        _app()

    def test_the_screens_qt_knows(self):
        found = hubpop.screens()
        expected = [s.availableGeometry().getRect()
                    for s in QtGui.QGuiApplication.screens()
                    if s.availableGeometry().width() > 0]
        self.assertTrue(found)
        self.assertEqual(found, expected or [hubpop.FALLBACK_SCREEN])

    def test_a_screen_of_no_size_is_left_out(self):
        empty = types.SimpleNamespace(
            availableGeometry=lambda: QtCore.QRect(0, 0, 0, 0))
        gui = types.SimpleNamespace(
            QGuiApplication=types.SimpleNamespace(screens=lambda: [empty]))
        with mock.patch.object(hubqt, "qt",
                               lambda: types.SimpleNamespace(QtGui=gui)):
            self.assertEqual(hubpop.screens(), [hubpop.FALLBACK_SCREEN])

    def test_no_qt_is_the_fallback_screen(self):
        def broken():
            raise ImportError("no PySide")
        with mock.patch.object(hubqt, "qt", broken):
            self.assertEqual(hubpop.screens(), [hubpop.FALLBACK_SCREEN])


class Points(unittest.TestCase):
    """A Qt 5 event's point, and the cursor when Qt will not answer."""

    def test_a_qt5_event_gives_its_global_pos(self):
        class Qt5Event(object):
            def globalPos(self):                          # noqa: N802
                return QtCore.QPoint(31, 47)
        self.assertEqual(hubpop._global(Qt5Event()), (31, 47))

    def test_no_cursor_means_not_under_anything(self):
        def broken():
            raise RuntimeError("no Qt")
        with mock.patch.object(hubqt, "qt", broken):
            self.assertIsNone(hubpop._cursor_point())
            self.assertFalse(hubpop._under(object()))

    def test_a_window_that_cannot_say_its_geometry_is_not_under_the_cursor(self):
        class Gone(object):
            def frameGeometry(self):                     # noqa: N802
                raise RuntimeError("Internal C++ object already deleted")
        with mock.patch.object(hubpop, "_cursor_point", lambda: (10, 10)):
            self.assertFalse(hubpop._under(Gone()))

    def test_the_cursor_on_the_window(self):
        _app()
        window = QtWidgets.QWidget()
        self.addCleanup(window.deleteLater)
        window.setGeometry(100, 100, 200, 150)
        with mock.patch.object(hubpop, "_cursor_point", lambda: (150, 160)):
            self.assertTrue(hubpop._under(window))
        with mock.patch.object(hubpop, "_cursor_point", lambda: (5, 5)):
            self.assertFalse(hubpop._under(window))


# ----------------------------------------------------------- the popup card

class PopupCardDirect(unittest.TestCase):
    """What apply_marks hands a window's card: a subtitle into the title row, the
    notes as the title's tooltip."""

    def setUp(self):
        _app()
        self.slot = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(self.slot)
        self.title = QtWidgets.QWidget()
        self.addCleanup(self.slot.deleteLater)
        self.addCleanup(self.title.deleteLater)
        self.card = hubpop.PopupCard(self.slot, self.title)

    def test_a_subtitle_moves_into_the_slot_right_aligned_and_stretching(self):
        label = QtWidgets.QLabel("Manny_Rig - 3 keys")
        label.setWordWrap(True)
        label.setMinimumHeight(40)
        self.assertIs(self.card.add_subtitle(label), label)
        layout = self.slot.layout()
        self.assertIs(label.parentWidget(), self.slot)
        self.assertEqual(layout.indexOf(label), 0)
        self.assertEqual(layout.stretch(0), 1)
        self.assertFalse(label.wordWrap())
        self.assertEqual(label.property("skRole"), "subtitle")
        self.assertEqual(label.minimumHeight(), 0)
        self.assertEqual(label.sizePolicy().horizontalPolicy(),
                         QtWidgets.QSizePolicy.Ignored)

    def test_a_short_subtitle_is_painted_at_the_right(self):
        label = QtWidgets.QLabel("ab")
        self.card.add_subtitle(label)
        self.slot.layout().setContentsMargins(0, 0, 0, 0)
        self.slot.resize(400, 30)
        self.slot.show()
        QtWidgets.QApplication.processEvents()
        image = label.grab().toImage()
        blank = image.pixelColor(0, 0)
        inked = [x for x in range(image.width()) for y in range(image.height())
                 if image.pixelColor(x, y) != blank]
        self.assertTrue(inked)
        self.assertGreater(min(inked), image.width() // 2)

    def test_bug_the_subtitle_s_alignment_property_is_never_set(self):
        """Fixed 2026-10-27 (written as an int), the bug as it was: maya_hubpop.py PopupCard.add_subtitle (and maya_hubqt.Card.add_subtitle):
        `setProperty("alignment", AlignRight | AlignVCenter)` answers False under
        PySide6 6.8 - the flag combination does not convert to the property's type -
        so the label keeps AlignLeft. Nothing shows it while the elide filter paints
        the label (right-aligned, above); a label painted without the filter would
        stand at the left."""
        label = QtWidgets.QLabel("Manny_Rig - 3 keys")
        self.card.add_subtitle(label)
        self.assertTrue(label.alignment() & QtCore.Qt.AlignRight)

    def test_hints_join_into_the_title_s_tooltip(self):
        self.card.add_hint("Press to retarget")
        self.assertEqual(self.title.toolTip(), "Press to retarget")
        self.card.add_hint("  Shift: keep the take  ")
        self.assertEqual(self.title.toolTip(),
                         "Press to retarget\nShift: keep the take")

    def test_an_empty_hint_adds_nothing(self):
        self.card.add_hint("")
        self.card.add_hint(None)
        self.card.add_hint("   ")
        self.assertEqual(self.title.toolTip(), "")

    def test_the_card_keeps_its_status_lines(self):
        self.assertTrue(hubpop.PopupCard.keeps_text)
        self.assertEqual(self.card.status_controls, set())


class PopupCardThroughTheBuild(Seams):
    """The real road: a section marks a subtitle and a note; the window shows the
    subtitle in its title row and the note as the title's tooltip."""

    def test_a_marked_subtitle_and_note_land_in_the_title_row(self):
        widgets = {"alphaBound": QtWidgets.QLabel("Character: root (rig)"),
                   "alphaTip": QtWidgets.QLabel("Select a rig first")}
        for widget in widgets.values():
            self.addCleanup(widget.deleteLater)

        def build_alpha():
            hubstyle.mark("alphaBound", "subtitle")
            hubstyle.mark("alphaTip", "note")

        self.hub.builders["build"] = build_alpha
        with mock.patch.object(hubqt, "find",
                               lambda name, layout=False: widgets.get(name)):
            popup = hubpop.open_popup("alpha")
        sub = widgets["alphaBound"]
        self.assertIs(sub.parentWidget(), popup.subtitle_slot)
        self.assertEqual(sub.property("skRole"), "subtitle")
        self.assertEqual(popup.title.toolTip(), "Select a rig first")
        self.assertTrue(widgets["alphaTip"].isHidden())


# ------------------------------------------------------------ the build

class Build(Seams):

    def test_a_builder_that_raises_leaves_a_line_in_its_place(self):
        def broken():
            raise ValueError("boom")
        self.hub.builders["build"] = broken
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            popup = hubpop.open_popup("alpha")
        self.assertTrue(popup.alive())
        texts = [c for c in self.cmds.calls if c[0] == "text"]
        self.assertTrue(texts)
        label = texts[-1][2]["label"]
        self.assertEqual(label, "Alpha could not be built: ValueError: boom")
        self.assertTrue(texts[-1][2]["wordWrap"])
        self.assertIn("ValueError: boom", out.getvalue())

    def test_the_commands_are_wrapped_before_a_first_build(self):
        wrapped = []
        with mock.patch.object(hubcopy, "installed", lambda: False), \
                mock.patch.object(hubcopy, "install",
                                  lambda cmds=None: wrapped.append(cmds)):
            hubpop.open_popup("alpha")
        self.assertEqual(wrapped, [self.cmds])

    def test_an_already_wrapped_session_is_not_wrapped_again(self):
        wrapped = []
        with mock.patch.object(hubcopy, "install",
                               lambda cmds=None: wrapped.append(cmds)):
            hubpop.open_popup("alpha")
        self.assertEqual(wrapped, [])

    def test_no_arrow_icon_still_builds_the_window(self):
        def broken(*_a, **_kw):
            raise OSError("no temp folder")
        with mock.patch.object(hubqt, "icon_file", broken):
            self.assertIsNone(hubpop._arrow())
            popup = hubpop.open_popup("alpha")
        self.assertTrue(popup.alive())

    def test_a_window_that_cannot_be_placed_is_destroyed_and_the_error_raised(self):
        def no_place(popup, origin=None):
            raise RuntimeError("no screen")
        err = io.StringIO()
        with mock.patch.object(hubpop.Popup, "place_window", no_place), \
                contextlib.redirect_stderr(err):
            with self.assertRaises(RuntimeError):
                hubpop.open_popup("alpha")
        self.assertFalse(hubpop.is_open("alpha"))
        self.assertEqual(hubpop._state()["popups"], {})
        self.assertNotIn(("alpha", True), self.hub.painted)
        self.assertEqual([s for s in hubcopy.live() if s.section == "alpha"], [])
        standing = [w for w in QtWidgets.QApplication.topLevelWidgets()
                    if w.objectName().startswith(hubstyle.POPUP_ROOT)]
        self.assertEqual(standing, [])
        self.assertIn("no screen", err.getvalue())


class Dead(unittest.TestCase):
    """A window object with no window (not built, or destroyed): every call is
    quiet and changes nothing."""

    def setUp(self):
        _app()
        sec = Section("alpha", "Alpha", "m", "build", "f", "scene", "user")
        self.popup = hubpop.Popup("alpha", sec, 1.0)

    def test_no_window_is_not_alive(self):
        self.assertFalse(self.popup.alive())

    def test_a_window_shiboken_cannot_judge_is_not_alive(self):
        def refuse(_obj):
            raise TypeError("not a Shiboken object")
        q = types.SimpleNamespace(shiboken=types.SimpleNamespace(isValid=refuse))
        self.popup.root = object()
        with mock.patch.object(hubqt, "qt", lambda: q):
            self.assertFalse(self.popup.alive())
        self.popup.root = None

    def test_geometry_without_a_window(self):
        popup = self.popup
        self.assertEqual(popup._card_pad(), 0)
        self.assertEqual(popup._centre(), (0, 0))
        popup._keep_on(SCREEN)
        popup._set_size(300, 200)
        popup._place_grips()
        popup._grip_drag("right", (10, 10), True)
        popup._grip_reset("corner")
        popup._roll_done(True)
        popup._paint_roll()
        popup._settle()
        self.assertIsNone(popup._grip_start)
        self.assertIsNone(popup.user_w)

    def test_light_flash_and_burst_without_a_window(self):
        popup = self.popup
        popup.set_light(True)
        popup.flash()
        popup._opened()
        self.assertFalse(popup._burst(True, (5, 5), lambda: None))
        self.assertIsNone(popup._light_anim)
        self.assertIsNone(popup._flash_anim)

    def test_a_fade_out_with_no_window_is_done_at_once(self):
        done = []
        self.popup.fade_out(lambda: done.append(1))
        self.assertEqual(done, [1])
        self.assertIsNone(self.popup._fade)

    def test_destroy_with_nothing_built_is_quiet(self):
        self.popup.destroy()
        self.popup.destroy()
        self.assertIsNone(self.popup.root)


# --------------------------------------------------- the title and the edges

class TitleButtons(Seams):
    """The title row's other presses: a right press, a nudge inside the drag
    distance, a release with no press."""

    def test_a_right_press_neither_grabs_nor_rolls(self):
        popup = hubpop.open_popup("alpha")
        at = (popup.root.x() + 40, popup.root.y() + 8)
        self.mouse(popup.title, QtCore.QEvent.MouseButtonPress, (40, 8), at,
                   QtCore.Qt.RightButton, QtCore.Qt.RightButton)
        self.assertIsNone(popup.grab)
        self.mouse(popup.title, QtCore.QEvent.MouseButtonRelease, (40, 8), at,
                   QtCore.Qt.RightButton, QtCore.Qt.NoButton)
        self.assertFalse(popup.collapsed)

    def test_a_nudge_inside_the_drag_distance_is_still_a_click(self):
        popup = hubpop.open_popup("alpha")
        place = (popup.root.x(), popup.root.y())
        start = (popup.root.x() + 40, popup.root.y() + 8)
        nudge = (start[0] + 1, start[1])
        self.assertLess(1, QtWidgets.QApplication.startDragDistance())
        self.mouse(popup.title, QtCore.QEvent.MouseButtonPress, (40, 8), start,
                   QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
        self.mouse(popup.title, QtCore.QEvent.MouseMove, (41, 8), nudge,
                   QtCore.Qt.NoButton, QtCore.Qt.LeftButton)
        self.assertEqual((popup.root.x(), popup.root.y()), place)
        self.mouse(popup.title, QtCore.QEvent.MouseButtonRelease, (41, 8), nudge,
                   QtCore.Qt.LeftButton, QtCore.Qt.NoButton)
        self.assertTrue(popup.collapsed)                  # a click: rolled up
        self.assertNotIn(rules.WINDOW_POS_VAR.format("alpha"), self.cmds.vars)

    def test_a_move_with_no_press_moves_nothing(self):
        popup = hubpop.open_popup("alpha")
        place = (popup.root.x(), popup.root.y())
        event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseMove, QtCore.QPointF(5, 5), QtCore.QPointF(900, 900),
            QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        popup.title.mouseMoveEvent(event)             # Qt drops it before the widget
        self.assertEqual((popup.root.x(), popup.root.y()), place)

    def test_a_release_with_no_press_is_no_click(self):
        popup = hubpop.open_popup("alpha")
        at = (popup.root.x() + 40, popup.root.y() + 8)
        self.mouse(popup.title, QtCore.QEvent.MouseButtonRelease, (40, 8), at,
                   QtCore.Qt.LeftButton, QtCore.Qt.NoButton)
        self.assertFalse(popup.collapsed)

    def test_a_drag_with_no_grab_moves_nothing(self):
        popup = hubpop.open_popup("alpha")
        place, remembered = (popup.root.x(), popup.root.y()), popup.place
        popup._drag((700, 500))
        self.assertEqual((popup.root.x(), popup.root.y()), place)
        self.assertEqual(popup.place, remembered)


class GripButtons(Seams):
    """The edge strips' other presses, and the resets of a rolled-up bar and of
    both sides at once."""

    def grip_point(self, grip):
        centre = QtCore.QPoint(grip.width() // 2, grip.height() // 2)
        at = grip.mapToGlobal(centre)
        return (centre.x(), centre.y()), (at.x(), at.y())

    def drag(self, grip, dx, dy):
        local, start = self.grip_point(grip)
        end = (start[0] + dx, start[1] + dy)
        self.mouse(grip, QtCore.QEvent.MouseButtonPress, local, start,
                   QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
        self.mouse(grip, QtCore.QEvent.MouseMove, local, end,
                   QtCore.Qt.NoButton, QtCore.Qt.LeftButton)
        self.mouse(grip, QtCore.QEvent.MouseButtonRelease, local, end,
                   QtCore.Qt.LeftButton, QtCore.Qt.NoButton)

    def open_placed(self):
        popup = hubpop.open_popup("alpha")
        popup._grab((popup.root.x() + 1, popup.root.y() + 1))
        popup._drag((201, 151))
        popup._drop()
        return popup

    def test_a_right_press_and_release_on_an_edge_resize_nothing(self):
        popup = self.open_placed()
        size = (popup.root.width(), popup.root.height())
        grip = popup.grips[0]
        local, at = self.grip_point(grip)
        self.mouse(grip, QtCore.QEvent.MouseButtonPress, local, at,
                   QtCore.Qt.RightButton, QtCore.Qt.RightButton)
        self.assertIsNone(popup._grip_start)
        self.mouse(grip, QtCore.QEvent.MouseMove, local, (at[0] + 80, at[1]),
                   QtCore.Qt.NoButton, QtCore.Qt.RightButton)
        self.mouse(grip, QtCore.QEvent.MouseButtonRelease, local, (at[0] + 80, at[1]),
                   QtCore.Qt.RightButton, QtCore.Qt.NoButton)
        self.assertEqual((popup.root.width(), popup.root.height()), size)
        self.assertNotIn(rules.SIZE_VAR.format("alpha"), self.cmds.vars)

    def test_a_right_double_click_gives_no_side_back(self):
        popup = self.open_placed()
        self.drag(popup.grips[0], 60, 0)
        dragged = popup.user_w
        self.assertIsNotNone(dragged)
        local, at = self.grip_point(popup.grips[0])
        self.mouse(popup.grips[0], QtCore.QEvent.MouseButtonDblClick, local, at,
                   QtCore.Qt.RightButton, QtCore.Qt.RightButton)
        self.assertEqual(popup.user_w, dragged)

    def test_a_move_with_no_resize_started_does_nothing(self):
        popup = self.open_placed()
        size = (popup.root.width(), popup.root.height())
        popup._grip_drag("corner", (1500, 900), False)
        self.assertEqual((popup.root.width(), popup.root.height()), size)
        popup._grip_end()                               # no drag: nothing remembered
        self.assertNotIn(rules.SIZE_VAR.format("alpha"), self.cmds.vars)

    def test_a_double_click_on_a_rolled_bar_fits_its_name_again(self):
        popup = self.open_placed()
        popup.toggle_roll()
        name_w = popup._title_width()
        self.drag(popup.grips[0], 90, 0)
        self.assertEqual(popup.bar_w, name_w + 90)
        local, at = self.grip_point(popup.grips[0])
        self.mouse(popup.grips[0], QtCore.QEvent.MouseButtonDblClick, local, at,
                   QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
        self.assertIsNone(popup.bar_w)
        self.assertEqual(popup.root.width(), name_w)
        self.assertEqual(rules.decode_single(
            self.cmds.vars[rules.BAR_VAR.format("alpha")]), None)

    def test_a_double_click_on_the_corner_gives_both_sides_back(self):
        popup = self.open_placed()
        automatic = (popup.root.width(), popup.root.height())
        self.drag(popup.grips[2], 50, 40)
        self.assertIsNotNone(popup.user_w)
        self.assertIsNotNone(popup.user_h)
        local, at = self.grip_point(popup.grips[2])
        self.mouse(popup.grips[2], QtCore.QEvent.MouseButtonDblClick, local, at,
                   QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
        self.assertEqual((popup.user_w, popup.user_h), (None, None))
        self.assertEqual((popup.root.width(), popup.root.height()), automatic)
        self.assertEqual(rules.decode_pair(
            self.cmds.vars[rules.SIZE_VAR.format("alpha")]), (None, None))

    def test_a_window_off_its_screen_is_brought_back_on(self):
        popup = self.open_placed()
        popup.root.move(5000, -300)
        popup._keep_on(SCREEN)
        x, y = popup.root.x(), popup.root.y()
        self.assertEqual(x + popup.root.width(), SCREEN[2])
        self.assertEqual(y, 0)
        popup._keep_on(SCREEN)                         # on it: not moved again
        self.assertEqual((popup.root.x(), popup.root.y()), (x, y))


# ------------------------------------------------- fades, rolls and the flash

class Fades(Seams):
    """The fades a window falls back on with no burst, driven frame by frame."""

    @contextlib.contextmanager
    def no_burst(self):
        """Animations on, and no burst effect to be had (the fallback fade)."""
        def broken():
            raise RuntimeError("no effect here")
        with mock.patch.object(hubpop.hubwindow, "burst_class", broken), \
                mock.patch.object(hubmotion, "enabled", lambda: True):
            yield

    def test_a_close_with_no_burst_fades_out_then_destroys_the_window(self):
        popup = hubpop.open_popup("alpha")
        with self.no_burst(), contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(hubpop, "_later", lambda fn: fn()):
            hubpop.close_popup("alpha", animate=True)
            fade = popup._fade
            self.assertIsNotNone(fade)
            self.assertTrue(popup.root.testAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents))
            fade.setCurrentTime(fade.duration() // 2)
            self.assertAlmostEqual(popup.root.windowOpacity(),
                                   1.0 - hubmotion.smooth(fade.currentValue()),
                                   places=2)
            self.assertGreater(popup.root.windowOpacity(), 0.0)
            self.assertLess(popup.root.windowOpacity(), 1.0)
            finish(fade)
        self.assertIsNone(popup._fade)
        self.assertFalse(popup.alive())
        self.assertEqual(hubpop._state()["closing"], [])

    def test_the_folded_window_is_destroyed_on_the_loop_s_next_turn(self):
        popup = hubpop.open_popup("alpha")
        with self.no_burst(), contextlib.redirect_stderr(io.StringIO()):
            hubpop.close_popup("alpha", animate=True)
            finish(popup._fade)
        self.assertTrue(popup.alive())                 # not inside the signal
        for _ in range(50):
            if not popup.alive():
                break
            QtWidgets.QApplication.processEvents()
        self.assertFalse(popup.alive())

    def test_a_hidden_window_fades_rather_than_folds(self):
        popup = hubpop.open_popup("alpha")
        popup.root.hide()
        done = []
        popup.fade_out(lambda: done.append(1))
        self.assertIsNone(popup.burst)                 # no burst on a hidden window
        self.assertIsNotNone(popup._fade)
        finish(popup._fade)
        self.assertEqual(done, [1])
        self.assertIsNone(popup._fade)

    def test_a_tick_after_the_window_went_does_nothing(self):
        popup = hubpop.open_popup("alpha")
        popup.root.hide()
        popup.fade_out(lambda: None)
        fade, root = popup._fade, popup.root
        popup.root = None
        fade.setCurrentTime(fade.duration() // 2)       # no window: no opacity to set
        popup.root = root
        self.assertAlmostEqual(root.windowOpacity(), 1.0, places=2)
        finish(fade)

    def test_a_burst_that_raises_opens_with_a_fade(self):
        popup = hubpop.open_popup("alpha")

        def boom(*_a, **_kw):
            raise ValueError("burst broke")
        popup.burster.run = boom
        with contextlib.redirect_stderr(io.StringIO()) as err:
            popup.show_open(animate=True, origin=(300, 200))
        self.assertIn("burst broke", err.getvalue())
        self.assertFalse(popup.bursting())
        self.assertFalse(popup.root.testAttribute(
            QtCore.Qt.WA_TransparentForMouseEvents))
        self.assertIsNotNone(popup._open_anim)
        self.assertLess(popup.root.windowOpacity(), 0.01)
        finish(popup._open_anim)
        self.assertIsNone(popup._open_anim)
        self.assertEqual(popup.root.windowOpacity(), 1.0)


class Roll(Seams):

    def test_a_roll_tick_after_the_window_went_does_nothing(self):
        with mock.patch.object(hubmotion, "enabled", lambda: True):
            popup = hubpop.open_popup("alpha")
            size = (popup.root.width(), popup.root.height())
            popup.set_collapsed(True, animate=True)
        anim, root = popup._roll_anim, popup.root
        self.assertIsNotNone(anim)
        popup.root = None
        anim.setCurrentTime(anim.duration() // 2)
        self.assertEqual((root.width(), root.height()), size)
        popup.root = root
        finish(anim)
        self.assertIsNone(popup._roll_anim)
        self.assertEqual(root.height(), popup._chrome())

    def test_a_roll_to_the_size_it_has_ends_at_once(self):
        with mock.patch.object(hubmotion, "enabled", lambda: True):
            popup = hubpop.open_popup("alpha")
            size = (popup.root.width(), popup.root.height())
            with mock.patch.object(hubpop.Popup, "_target", lambda self, rect: size):
                popup._roll_to(False)
        self.assertIsNone(popup._roll_anim)
        self.assertEqual((popup.root.width(), popup.root.height()), size)


class Flash(Seams):
    """A second ⧉ on a standing window: raised, and its flash driven down to 0."""

    def test_the_flash_rises_and_falls_back_to_nothing(self):
        with mock.patch.object(hubmotion, "enabled", lambda: True):
            popup = hubpop.open_popup("alpha")
            popup.flash()
        anim = popup._flash_anim
        self.assertIsNotNone(anim)
        self.assertAlmostEqual(popup.frame.flash, 1.0)
        anim.setCurrentTime(anim.duration() // 2)
        self.assertAlmostEqual(popup.frame.flash,
                               hubmotion.flash_at(anim.currentValue()))
        self.assertGreater(popup.frame.flash, 0.0)
        self.assertLess(popup.frame.flash, 1.0)
        finish(anim)
        self.assertIsNone(popup._flash_anim)
        self.assertEqual(popup.frame.flash, 0.0)

    def test_with_animations_off_it_is_only_raised(self):
        popup = hubpop.open_popup("alpha")
        raised = []
        popup.root.raise_ = lambda: raised.append(1)
        with mock.patch.object(hubmotion, "enabled", lambda: False):
            popup.flash()
        del popup.root.raise_
        self.assertEqual(raised, [1])
        self.assertIsNone(popup._flash_anim)
        self.assertEqual(popup.frame.flash, 0.0)

    def test_a_window_going_as_it_is_raised_does_not_flash(self):
        popup = hubpop.open_popup("alpha")

        def gone():
            raise RuntimeError("Internal C++ object already deleted")
        popup.root.raise_ = gone
        popup.flash()
        del popup.root.raise_
        self.assertIsNone(popup._flash_anim)
        self.assertEqual(popup.frame.flash, 0.0)


# ------------------------------------------------------------- the burst

class BurstParts(Seams):
    """The 2026-10-17 burst (hubburst.MOTION "burst"): the frame's face under it
    and the parts it pops in - the title row, then the section's rows."""

    def with_row(self):
        popup = hubpop.open_popup("alpha")
        row = QtWidgets.QWidget()
        row.setFixedHeight(60)
        popup.body.addWidget(row)
        row.show()
        popup._fit()
        return popup

    def test_the_face_goes_from_card_to_card_active_with_the_light(self):
        def rgb(token):
            text = hubstyle.TOKENS[token]
            return tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))
        popup = hubpop.open_popup("alpha")
        popup.set_light(False)
        self.assertEqual(popup._burst_face(), rgb("card"))
        popup.set_light(True)
        self.assertEqual(popup._burst_face(), rgb("card_active"))
        popup.frame.level = 0.5
        half = popup._burst_face()
        for channel in range(3):
            low, high = sorted((rgb("card")[channel], rgb("card_active")[channel]))
            self.assertTrue(low <= half[channel] <= high)

    def test_open_the_title_and_the_rows_rolled_up_the_title_alone(self):
        popup = self.with_row()
        title = popup.title
        parts = popup._burst_parts()
        self.assertEqual(parts[0], (title.x(), title.y(), title.width(),
                                    title.height()))
        self.assertGreater(len(parts), 1)
        popup.toggle_roll()
        self.assertEqual(popup._burst_parts(),
                         [(title.x(), title.y(), title.width(), title.height())])

    def test_a_burst_plan_is_made_from_the_window_s_parts_and_face(self):
        with mock.patch.object(hubburst, "MOTION", "burst"), \
                mock.patch.object(hubmotion, "enabled", lambda: True):
            popup = self.with_row()
            popup.show_open(animate=True, origin=self.corner(popup))
            held, popup.burster.anim = popup.burster.anim, None
            held.stop()
            effect = popup.burst
            effect.ms = 60.0
            popup.burster.tick_now()
            plan = effect.plan
            self.assertEqual(plan.kind, "burst")
            self.assertTrue(plan.opening)
            self.assertEqual(plan.parts, popup._burst_parts())
            self.assertEqual(effect.face, popup._burst_face())
            effect.ms = plan.total
            popup.burster.tick_now()
        self.assertFalse(popup.bursting())
        self.assertFalse(popup.root.testAttribute(
            QtCore.Qt.WA_TransparentForMouseEvents))


class BurstFailures(Seams):
    """A burst or a window that goes away under the burst's own calls."""

    def test_a_stop_or_a_window_gone_mid_end_is_quiet(self):
        popup = hubpop.open_popup("alpha")

        def gone(*_a):
            raise RuntimeError("Internal C++ object already deleted")
        popup.burster.stop = gone
        popup.root.setAttribute = gone
        popup._end_burst()                            # neither raises out
        del popup.root.setAttribute
        popup._stop_all()                             # its burster's stop raises too
        self.assertIsNone(popup._light_anim)

    def test_a_fold_ends_even_if_the_window_cannot_hide(self):
        popup = hubpop.open_popup("alpha")
        done = []

        def gone():
            raise RuntimeError("Internal C++ object already deleted")
        popup.root.hide = gone
        popup._folded(lambda: done.append(1))
        del popup.root.hide
        self.assertEqual(done, [1])

    def test_an_animation_already_gone_stops_quietly(self):
        popup = hubpop.open_popup("alpha")

        class Gone(object):
            def stop(self):
                raise RuntimeError("Internal C++ object already deleted")
        popup._light_anim = Gone()
        popup._stop_anim("_light_anim")
        self.assertIsNone(popup._light_anim)

    def test_a_destroy_that_fails_prints_and_forgets_the_window(self):
        popup = hubpop.open_popup("alpha")
        root = popup.root

        def refuse():
            raise ValueError("cannot hide")
        root.hide = refuse
        with contextlib.redirect_stderr(io.StringIO()) as err:
            popup.destroy()
        del root.hide
        self.assertIsNone(popup.root)
        self.assertIn("cannot hide", err.getvalue())
        root.setParent(None)
        shiboken6.delete(root)


# ---------------------------------------------------------- the manager

class Manager(Seams):

    def test_open_at_unrolls_a_window_left_rolled_up(self):
        self.cmds.vars[rules.COLLAPSED_VAR.format("alpha")] = "1"
        popup = hubpop.open_at("alpha", (600, 400), animate=False)
        self.assertFalse(popup.collapsed)
        self.assertEqual(self.cmds.vars[rules.COLLAPSED_VAR.format("alpha")], "0")
        self.assertFalse(popup.scroll.isHidden())

    def test_destroy_all_takes_the_windows_still_folding(self):
        with mock.patch.object(hubmotion, "enabled", lambda: True):
            popup = hubpop.open_popup("alpha")
            hubpop.close_popup("alpha", animate=True, origin=self.corner(popup))
        self.assertIn(popup, hubpop._state()["closing"])
        self.assertGreaterEqual(hubpop.destroy_all(), 1)
        self.assertEqual(hubpop._state()["closing"], [])
        self.assertFalse(popup.alive())

    def test_destroy_all_stops_an_older_follow_timer(self):
        timer = QtCore.QTimer()
        timer.start(100000)
        hubpop._state()["timer"] = timer
        hubpop.destroy_all()
        self.assertFalse(timer.isActive())
        self.assertIsNone(hubpop._state()["timer"])

        class Gone(object):
            def stop(self):
                raise RuntimeError("Internal C++ object already deleted")
        hubpop._state()["timer"] = Gone()
        hubpop.destroy_all()
        self.assertIsNone(hubpop._state()["timer"])

    def test_destroy_all_finds_an_older_module_s_windows_by_name(self):
        orphan = QtWidgets.QWidget()
        orphan.setObjectName(hubstyle.POPUP_ROOT + "_hubcopy9999")
        other = QtWidgets.QWidget()
        other.setObjectName("somebodyElsesWindow")
        self.addCleanup(other.deleteLater)
        self.assertEqual(hubpop.destroy_all(), 1)
        self.assertFalse(shiboken6.isValid(orphan))
        self.assertTrue(shiboken6.isValid(other))

    def test_a_window_dying_during_the_sweep_is_skipped_and_the_rest_go(self):
        class Dying(object):
            def objectName(self):                          # noqa: N802
                raise RuntimeError("Internal C++ object already deleted")
        orphan = QtWidgets.QWidget()
        orphan.setObjectName(hubstyle.POPUP_ROOT + "_hubcopy9998")
        app = types.SimpleNamespace(
            instance=QtWidgets.QApplication.instance,
            topLevelWidgets=lambda: [Dying(), orphan])
        q = types.SimpleNamespace(QtWidgets=types.SimpleNamespace(QApplication=app),
                                  shiboken=shiboken6)
        with mock.patch.object(hubqt, "qt", lambda: q):
            self.assertEqual(hubpop.destroy_all(), 1)
        self.assertFalse(shiboken6.isValid(orphan))

    def test_destroy_all_closes_a_section_copy_no_window_holds(self):
        stray = hubcopy.new_scope(section="alpha")
        loose = hubcopy.new_scope()                      # not a section's: kept
        self.addCleanup(hubcopy.close, loose, self.cmds)
        hubpop.destroy_all()
        self.assertFalse(stray.alive)
        self.assertTrue(loose.alive)

    def test_destroy_all_may_forget_the_open_windows(self):
        hubpop.open_popup("alpha")
        hubpop.destroy_all(forget=True)
        self.assertEqual(self.cmds.vars[rules.POPUPS_VAR], "")

    def test_a_hub_that_cannot_paint_its_button_still_paints_its_dot(self):
        def broken(key, on):
            raise RuntimeError("no card")
        self.hub.paint_popped = broken
        hubpop.open_popup("alpha")
        hubpop.close_popup("alpha")
        self.assertEqual(self.hub.floated, [("alpha", True), ("alpha", False)])


class Restore(Seams):

    def test_nothing_remembered_is_no_key(self):
        self.assertEqual(hubpop.remembered_keys(), [])
        self.assertEqual(hubpop._restore(), [])

    def test_a_queued_restore_is_not_queued_twice(self):
        self.assertTrue(hubpop.restore_later())
        self.assertFalse(hubpop.restore_later())
        self.assertEqual(len(self.cmds.deferred_calls), 1)

    def test_a_hub_that_cannot_list_its_sections_restores_nothing(self):
        self.cmds.vars[rules.POPUPS_VAR] = "alpha"

        def broken():
            raise RuntimeError("hub half built")
        self.hub.card_sections = broken
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(hubpop._restore(), [])
        self.assertIn("hub half built", err.getvalue())
        self.assertFalse(hubpop.is_open("alpha"))

    def test_maya_still_starting_up_retries_then_gives_up(self):
        self.cmds.vars[rules.POPUPS_VAR] = "alpha"
        retries = []
        with mock.patch.object(hubqt, "_maya_ui_ok", lambda: True), \
                mock.patch.object(hubpop, "_retry_later", lambda: retries.append(1)):
            self.assertEqual(hubpop._restore(), [])
            self.assertEqual(hubpop._state()["tries"], 1)
            self.assertEqual(retries, [1])
            hubpop._state()["tries"] = hubpop.RESTORE_TRIES
            self.assertEqual(hubpop._restore(), [])
            self.assertEqual(retries, [1])                 # the last try: no more
        self.assertFalse(hubpop.is_open("alpha"))

    def test_one_window_failing_does_not_stop_the_others(self):
        self.cmds.vars[rules.POPUPS_VAR] = "alpha,beta"
        real = hubpop.Popup.place_window

        def place(popup, origin=None):
            if popup.key == "alpha":
                raise RuntimeError("alpha cannot stand")
            return real(popup, origin)
        with mock.patch.object(hubpop.Popup, "place_window", place), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(hubpop._restore(), ["beta"])
        self.assertEqual(hubpop.open_keys(), ["beta"])
        self.assertEqual(self.cmds.vars[rules.POPUPS_VAR], "beta")
        self.assertFalse(hubpop._state()["restoring"])

    def test_the_retry_asks_qt_for_a_later_restore(self):
        shots = []
        timer = types.SimpleNamespace(singleShot=lambda ms, fn: shots.append((ms, fn)))
        q = types.SimpleNamespace(QtCore=types.SimpleNamespace(QTimer=timer))
        with mock.patch.object(hubqt, "qt", lambda: q):
            hubpop._retry_later()
        self.assertEqual(shots, [(hubpop.RESTORE_MS, hubpop.restore_later)])

    def test_a_retry_with_no_qt_is_quiet(self):
        def broken():
            raise ImportError("no PySide")
        with mock.patch.object(hubqt, "qt", broken):
            hubpop._retry_later()


if __name__ == "__main__":
    unittest.main()

"""maya_graphoverlay.mode - switching on and off, the pipeline, the chrome, the
window's own filter, the follow tick and the scene jobs, on fakes.

The ghost and the glass are fakes standing in the package (their real halves
are proven in test_graphoverlay_ghost / _glass); Maya's commands are a fake;
`QTimer.singleShot` is recorded rather than run, so nothing fires later in the
run; Win32 is not asked for.
"""

import contextlib
import os
import time
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

import maya_graphoverlay
import maya_hubcopy as hubcopy
from maya_graphoverlay import keying, mode, viewport, winstyle


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeSignal(object):

    def __init__(self):
        self.slots = []
        self.disconnected = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        self.disconnected.append(slot)
        self.slots.remove(slot)


class FakeCanvas(object):

    def __init__(self, pointer=111):
        self.frameSwapped = FakeSignal()
        self.pointer = pointer


class FakeGhost(object):
    """ghost.Ghost as the mode drives it."""

    def __init__(self, parent=None, rect=(10, 20, 600, 400), borrow=True):
        self.parent, self.rect, self.borrowed = parent, rect, borrow
        self.panel = "graphEditor1"
        self.host = QtWidgets.QWidget()
        self.host.setGeometry(*rect)
        self.chrome = [QtWidgets.QWidget(self.host),
                       QtWidgets.QWidget(self.host)]
        self.live = FakeCanvas()
        self.is_alive = True
        self.is_showing = True
        self.frame = tuple(rect)
        self.image = None
        self.pieces = [("piece", 0, 0)]
        self.calls = []
        self.grabbing_seen = None

    def showing(self):
        return self.is_showing

    def frame_rect(self):
        return self.frame

    def canvas(self):
        return self.live

    def canvas_pointer(self):
        return self.live.pointer if self.live is not None else None

    def canvas_frame(self):
        if isinstance(self.image, Exception):
            raise self.image
        return self.image

    def canvas_offset(self):
        return (7, 9)

    def chrome_widgets(self):
        return list(self.chrome)

    def chrome_pieces(self):
        self.grabbing_seen = mode._STATE.grabbing
        if isinstance(self.pieces, Exception):
            raise self.pieces
        return self.pieces

    def alive(self):
        return self.is_alive

    def open_channel_list(self):
        self.calls.append("open_channel_list")

    def keep_invisible(self):
        self.calls.append("keep_invisible")

    def destroy(self):
        self.calls.append("destroy")
        self.host.deleteLater()


class FakeGlass(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.placed = []
        self.frames = []
        self.chromes = []
        self.visible = False
        self.calls = []

    def place(self, rect):
        self.placed.append(rect)
        self.visible = True

    def set_frame(self, bgra, offset=(0, 0)):
        self.frames.append((bgra, offset))

    def set_chrome(self, pieces):
        self.chromes.append(pieces)

    def isVisible(self):
        return self.visible

    def hide(self):
        self.visible = False

    def keep_click_through(self):
        self.calls.append("keep_click_through")

    def close_glass(self):
        self.calls.append("close_glass")


class FakeModeCmds(object):

    def __init__(self):
        self.optionvars = {}
        self.calls = []
        self.deferred = []
        self.jobs = 0
        self.job_scopes = []
        self.controls = set()
        self.fail = False

    def optionVar(self, **kw):
        if self.fail:
            raise RuntimeError("no prefs")
        if "exists" in kw:
            return kw["exists"] in self.optionvars
        if "query" in kw:
            return self.optionvars.get(kw["query"])
        name, value = kw["stringValue"]
        self.optionvars[name] = value

    def scriptJob(self, **kw):
        self.calls.append(("scriptJob", kw))
        if self.fail:
            raise RuntimeError("no jobs")
        if "kill" in kw:
            return None
        self.jobs += 1
        self.job_scopes.append(hubcopy.current())
        return self.jobs

    def evalDeferred(self, fn, **kw):
        self.deferred.append(fn)

    def control(self, name, **kw):
        return name in self.controls

    def __getattr__(self, name):
        def call(*args, **kw):
            self.calls.append((name, args, kw))
        return call


class ModeCase(unittest.TestCase):
    """The mode off, its commands faked, its timers recorded, the session's
    state and keying pool put back after."""

    def setUp(self):
        self.app = _app()
        self.real_cmds = mode.cmds
        self.cmds = FakeModeCmds()
        mode.cmds = self.cmds
        self.saved_pool = list(mode._POOL)
        del mode._POOL[:]
        mode.reset_state()
        self.shots = []
        patcher = mock.patch.object(
            QtCore.QTimer, "singleShot",
            side_effect=lambda delay, fn: self.shots.append((delay, fn)))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ghost = None

    def tearDown(self):
        state = mode._STATE
        for timer in state.timers:
            try:
                timer.stop()
            except RuntimeError:
                pass
        for name in ("watch", "frame_watch"):
            watcher = getattr(state, name)
            if watcher is not None:
                try:
                    watcher.deleteLater()
                except RuntimeError:
                    pass
        mode.reset_state()
        del mode._POOL[:]
        mode._POOL.extend(self.saved_pool)
        mode.cmds = self.real_cmds
        if self.ghost is not None:
            try:
                self.ghost.host.deleteLater()
            except RuntimeError:
                pass
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def turn_on(self, **ghost_kw):
        """The state as enable() leaves it, without enable()."""
        self.ghost = FakeGhost(**ghost_kw)
        self.glass = FakeGlass()
        mode._STATE.ghost, mode._STATE.glass = self.ghost, self.glass
        mode._STATE.placed = True
        mode._STATE.table = keying.alpha_table()
        return self.ghost, self.glass


def _fresh_fields(state):
    """The state's fields that differ from a fresh one's."""
    fresh = vars(mode._State())
    return dict((name, value) for name, value in vars(state).items()
                if fresh.get(name, object()) != value)


# ------------------------------------------------------------ on and off

class SwitchOnAndOff(ModeCase):

    def setUp(self):
        super(SwitchOnAndOff, self).setUp()
        self.made = []

        def make_ghost(parent, rect, borrow=True):
            made = FakeGhost(parent, rect, borrow)
            self.made.append(made)
            self.ghost = made
            return made
        self.glass_fails = False

        def make_glass(parent):
            if self.glass_fails:
                raise RuntimeError("no glass")
            self.glass = FakeGlass(parent)
            return self.glass
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(
            maya_graphoverlay, "ghost",
            types.SimpleNamespace(Ghost=make_ghost), create=True))
        stack.enter_context(mock.patch.object(
            maya_graphoverlay, "glass",
            types.SimpleNamespace(Glass=make_glass), create=True))
        stack.enter_context(mock.patch.object(winstyle, "available",
                                              return_value=True))
        stack.enter_context(mock.patch.object(viewport, "maya_main_window",
                                              return_value="mainWindow"))
        stack.enter_context(mock.patch.object(mode, "_start_rect",
                                              return_value=(30, 40, 640, 480)))
        stack.enter_context(mock.patch.object(keying, "make_pool",
                                              return_value="pool"))

    def test_on_builds_the_window_and_its_glass_and_wires_everything(self):
        said = mode.enable()
        self.assertEqual(said, "Graph Overlay ON  -  " + mode.HINT)
        self.assertTrue(mode.is_on())
        ghost = self.made[0]
        self.assertEqual((ghost.parent, ghost.rect, ghost.borrowed),
                         ("mainWindow", (30, 40, 640, 480), mode.BORROW))
        self.assertEqual(self.glass.parent, "mainWindow")
        self.assertEqual(self.glass.placed, [(30, 40, 640, 480)])
        self.assertEqual(mode._STATE.rect, (30, 40, 640, 480))
        self.assertEqual(self.cmds.optionvars[mode.RECT_OPTION],
                         "30,40,640,480")
        self.assertEqual(mode._POOL, ["pool"])
        #  the canvas connected, the first swap queued
        self.assertEqual(ghost.live.frameSwapped.slots, [mode._on_swap])
        self.assertEqual(mode._STATE.canvas_pointer, ghost.live.pointer)
        self.assertTrue(mode._STATE.pending)
        #  the chrome waits for the borrowed panel to settle
        self.assertGreater(mode._STATE.chrome_after, time.perf_counter())
        self.assertEqual(len(mode._STATE.watched), 2)
        #  one follow timer, the two scene jobs
        self.assertEqual(len(mode._STATE.timers), 1)
        self.assertTrue(mode._STATE.timers[0].isActive())
        self.assertEqual(mode._STATE.timers[0].interval(), mode.FOLLOW_MS)
        self.assertEqual([c[1]["event"][0] for c in self.cmds.calls
                          if c[0] == "scriptJob"],
                         ["SceneOpened", "NewSceneOpened"])

    def test_on_twice_says_so(self):
        mode.enable()
        self.assertEqual(mode.enable(), "Graph Overlay is already on")
        self.assertEqual(len(self.made), 1)

    def test_off_takes_everything_down_and_resets_the_state(self):
        mode.enable()
        ghost, glass = self.made[0], self.glass
        timer = mode._STATE.timers[0]
        self.assertEqual(mode.disable(), "Graph Overlay OFF")
        self.assertFalse(mode.is_on())
        self.assertFalse(timer.isActive())
        self.assertEqual(ghost.live.frameSwapped.disconnected,
                         [mode._on_swap])
        self.assertEqual(glass.calls, ["close_glass"])
        self.assertIn("destroy", ghost.calls)
        kills = [c[1]["kill"] for c in self.cmds.calls
                 if c[0] == "scriptJob" and "kill" in c[1]]
        self.assertEqual(kills, [1, 2])
        self.assertEqual(_fresh_fields(mode._STATE), {})

    def test_off_leaves_a_canvas_that_is_no_longer_the_connected_one(self):
        """A deleted sender has let go by itself; asking a wrapper of a
        deleted object anything reads freed memory."""
        mode.enable()
        ghost = self.made[0]
        mode._STATE.canvas_pointer = 999        # another canvas was connected
        mode.disable()
        self.assertEqual(ghost.live.frameSwapped.disconnected, [])

    def test_off_with_no_live_canvas_disconnects_nothing(self):
        mode.enable()
        self.made[0].live = None
        self.assertEqual(mode.disable(), "Graph Overlay OFF")
        self.assertEqual(_fresh_fields(mode._STATE), {})

    def test_off_survives_watchers_already_deleted(self):
        mode.enable()
        shiboken6.delete(mode._STATE.watch)
        shiboken6.delete(mode._STATE.frame_watch)
        self.assertEqual(mode.disable(), "Graph Overlay OFF")
        self.assertIsNone(mode._STATE.watch)

    def test_a_failure_while_switching_on_takes_down_what_was_built(self):
        self.glass_fails = True
        with mock.patch.object(mode.traceback, "print_exc"):
            with self.assertRaises(RuntimeError):
                mode.enable()
        self.assertFalse(mode.is_on())
        self.assertIn("destroy", self.made[0].calls)
        self.assertEqual(_fresh_fields(mode._STATE), {})

    def test_the_keying_pool_is_made_once_a_module(self):
        mode.enable()
        mode.disable()
        mode.enable()
        self.assertEqual(mode._POOL, ["pool"])

    def test_toggle_switches_and_says_it(self):
        with mock.patch.object(mode, "_show", side_effect=lambda t: t) as show:
            self.assertTrue(mode.toggle().startswith("Graph Overlay ON"))
            self.assertEqual(mode.toggle(), "Graph Overlay OFF")
        self.assertEqual(show.call_count, 2)


# ---------------------------------------------------------------- remember

class Remember(ModeCase):

    def test_the_place_round_trips(self):
        mode._remember((10.4, 20, 600, 400))
        self.assertEqual(self.cmds.optionvars[mode.RECT_OPTION],
                         "10,20,600,400")
        self.assertEqual(mode._remembered(), (10, 20, 600, 400))

    def test_nothing_remembered_is_none(self):
        self.assertIsNone(mode._remembered())

    def test_a_broken_memory_is_none(self):
        self.cmds.optionvars[mode.RECT_OPTION] = "10,20,oops"
        self.assertIsNone(mode._remembered())
        self.cmds.optionvars[mode.RECT_OPTION] = "10,20,30"
        self.assertIsNone(mode._remembered())

    def test_prefs_that_fail_are_swallowed(self):
        self.cmds.fail = True
        mode._remember((1, 2, 3, 4))
        self.assertIsNone(mode._remembered())


# ---------------------------------------------------------------- pipeline

def _image(left, right, size=(70, 49)):
    """A frame: the left half one tone, the right half another, a curve."""
    image = QtGui.QImage(size[0], size[1], QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor(*left))
    painter = QtGui.QPainter(image)
    painter.fillRect(size[0] // 2, 0, size[0] - size[0] // 2, size[1],
                     QtGui.QColor(*right))
    painter.setPen(QtGui.QColor(230, 120, 40))
    painter.drawLine(0, size[1] // 2, size[0], size[1] // 2)
    painter.end()
    return image


class Pipeline(ModeCase):

    def setUp(self):
        super(Pipeline, self).setUp()
        patcher = mock.patch.object(winstyle, "gl_kept",
                                    contextlib.nullcontext)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_connecting_the_canvas_queues_the_first_frame(self):
        ghost, _glass = self.turn_on()
        mode._connect_canvas()
        self.assertIs(mode._STATE.canvas, ghost.live)
        self.assertEqual(mode._STATE.canvas_pointer, 111)
        self.assertEqual(self.shots, [(0, mode._update)])

    def test_no_canvas_nothing_to_connect(self):
        ghost, _glass = self.turn_on()
        ghost.live = None
        mode._connect_canvas()
        self.assertIsNone(mode._STATE.canvas)
        self.assertEqual(self.shots, [])

    def test_a_swap_is_coalesced(self):
        self.turn_on()
        mode._on_swap()
        mode._on_swap()
        self.assertEqual(len(self.shots), 1)

    def test_a_swap_waits_out_the_least_interval(self):
        self.turn_on()
        mode._STATE.last = time.perf_counter()
        mode._on_swap()
        delay = self.shots[0][0]
        self.assertGreater(delay, 0)
        self.assertLessEqual(delay, int(round(mode.MIN_UPDATE_S * 1000)))

    def test_a_swap_with_the_mode_off_does_nothing(self):
        mode._on_swap()
        self.assertEqual(self.shots, [])
        self.assertFalse(mode._STATE.pending)

    def test_a_frame_is_keyed_onto_the_glass(self):
        ghost, glass = self.turn_on()
        ghost.image = _image((64, 64, 64), (55, 55, 55))
        mode._STATE.pending = True
        mode._update()
        self.assertFalse(mode._STATE.pending)
        self.assertEqual(len(glass.frames), 1)
        bgra, offset = glass.frames[0]
        self.assertEqual(offset, (7, 9))
        self.assertEqual(bgra.shape, (49, 70, 4))
        self.assertEqual(sorted(mode._STATE.keys),
                         [(55, 55, 55), (64, 64, 64)])
        self.assertEqual(int(bgra[0, 0, 3]), 0)              # background out
        self.assertEqual(int(bgra[24, 3, 3]), 255)           # the curve stays
        self.assertEqual(mode._STATE.frames, 1)
        self.assertIsNotNone(mode._STATE.last)
        self.assertGreaterEqual(mode._STATE.cost, 0.0)

    def test_an_undrawn_frame_teaches_nothing(self):
        ghost, glass = self.turn_on()
        image = QtGui.QImage(40, 30, QtGui.QImage.Format_ARGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        ghost.image = image
        mode._update()
        self.assertEqual(glass.frames, [])
        self.assertEqual(mode._STATE.keys, [])
        self.assertEqual(mode._STATE.frames, 0)

    def test_a_uniform_frame_once_the_tones_are_known_is_shown(self):
        ghost, glass = self.turn_on()
        mode._STATE.keys = [(64, 64, 64)]
        image = QtGui.QImage(40, 30, QtGui.QImage.Format_ARGB32)
        image.fill(QtGui.QColor(64, 64, 64))
        ghost.image = image
        mode._update()
        self.assertEqual(len(glass.frames), 1)

    def test_no_frame_or_an_empty_one_shows_nothing(self):
        ghost, glass = self.turn_on()
        for image in (None, QtGui.QImage()):
            ghost.image = image
            mode._update()
        self.assertEqual(glass.frames, [])

    def test_nothing_is_keyed_while_off_hidden_or_closing(self):
        ghost, glass = self.turn_on()
        ghost.image = _image((64, 64, 64), (55, 55, 55))
        mode._STATE.placed = False
        mode._update()
        mode._STATE.placed, mode._STATE.closing = True, True
        mode._update()
        self.assertEqual(glass.frames, [])

    def test_a_failing_frame_is_printed_not_raised(self):
        ghost, glass = self.turn_on()
        ghost.image = RuntimeError("the canvas went away")
        with mock.patch.object(mode.traceback, "print_exc") as printed:
            mode._update()
        printed.assert_called_once_with()
        self.assertEqual(mode._STATE.frames, 0)
        self.assertIsNone(mode._STATE.last)


# ------------------------------------------------------------------ chrome

class Chrome(ModeCase):

    def test_the_watch_hears_a_paint_and_nothing_else(self):
        self.turn_on()
        watch = mode._make_watch()
        with mock.patch.object(mode, "_on_chrome_paint") as heard:
            self.assertFalse(watch.eventFilter(
                None, QtCore.QEvent(QtCore.QEvent.Paint)))
            watch.eventFilter(None, QtCore.QEvent(QtCore.QEvent.Move))
            mode._STATE.grabbing = True
            watch.eventFilter(None, QtCore.QEvent(QtCore.QEvent.Paint))
        self.assertEqual(heard.call_count, 1)
        watch.deleteLater()

    def test_the_watch_swallows_a_failure(self):
        watch = mode._make_watch()
        with mock.patch.object(mode, "_on_chrome_paint",
                               side_effect=RuntimeError("boom")):
            self.assertFalse(watch.eventFilter(
                None, QtCore.QEvent(QtCore.QEvent.Paint)))
        watch.deleteLater()

    def test_every_chrome_widget_is_watched_once(self):
        ghost, _glass = self.turn_on()
        self.assertEqual(mode._watch_chrome(), 2)
        self.assertEqual(mode._watch_chrome(), 0)
        ghost.chrome.append(QtWidgets.QWidget(ghost.host))
        self.assertEqual(mode._watch_chrome(), 1)

    def test_a_deleted_watch_starts_over(self):
        self.turn_on()
        mode._watch_chrome()
        shiboken6.delete(mode._STATE.watch)
        self.assertEqual(mode._watch_chrome(), 2)
        self.assertTrue(shiboken6.isValid(mode._STATE.watch))

    def test_a_real_repaint_asks_for_a_new_picture(self):
        ghost, _glass = self.turn_on()
        mode._watch_chrome()
        ghost.host.show()
        self.app.processEvents()
        with mock.patch.object(mode, "_on_chrome_paint") as heard:
            ghost.chrome[0].repaint()
        self.assertGreaterEqual(heard.call_count, 1)

    def test_a_chrome_picture_waits_for_the_settle_and_is_coalesced(self):
        self.turn_on()
        mode._STATE.chrome_after = time.perf_counter() + 0.5
        mode._on_chrome_paint()
        mode._on_chrome_paint()
        self.assertEqual(len(self.shots), 1)
        delay, fn = self.shots[0]
        self.assertIs(fn, mode._update_chrome)
        self.assertGreater(delay, 400)
        self.assertLessEqual(delay, 500)

    def test_a_chrome_picture_goes_onto_the_glass(self):
        ghost, glass = self.turn_on()
        mode._STATE.chrome_pending = True
        mode._update_chrome()
        self.assertTrue(ghost.grabbing_seen)        # silent while it grabs
        self.assertFalse(mode._STATE.grabbing)
        self.assertFalse(mode._STATE.chrome_pending)
        self.assertEqual(glass.chromes, [[("piece", 0, 0)]])
        self.assertEqual(mode._STATE.chrome_grabs, 1)
        self.assertIsNotNone(mode._STATE.chrome_last)

    def test_a_failed_chrome_picture_is_printed_and_the_grab_released(self):
        ghost, glass = self.turn_on()
        ghost.pieces = RuntimeError("capture failed")
        with mock.patch.object(mode.traceback, "print_exc") as printed:
            mode._update_chrome()
        printed.assert_called_once_with()
        self.assertFalse(mode._STATE.grabbing)
        self.assertEqual(glass.chromes, [])
        self.assertEqual(mode._STATE.chrome_grabs, 0)

    def test_no_chrome_picture_while_off_or_closing(self):
        mode._update_chrome()
        ghost, glass = self.turn_on()
        mode._STATE.closing = True
        mode._update_chrome()
        self.assertEqual(glass.chromes, [])
        self.assertIsNone(ghost.grabbing_seen)


# ------------------------------------------------------------- the window

class TheWindowsFilter(ModeCase):

    def test_a_move_resize_show_hide_or_state_change_syncs_the_glass(self):
        watch = mode._make_frame_watch()
        kinds = (QtCore.QEvent.Move, QtCore.QEvent.Resize,
                 QtCore.QEvent.Show, QtCore.QEvent.Hide,
                 QtCore.QEvent.WindowStateChange)
        with mock.patch.object(mode, "_sync_glass") as synced:
            for kind in kinds:
                self.assertFalse(watch.eventFilter(None, QtCore.QEvent(kind)))
            watch.eventFilter(None, QtCore.QEvent(QtCore.QEvent.Paint))
        self.assertEqual(synced.call_count, len(kinds))
        watch.deleteLater()

    def test_the_window_s_close_leaves_the_mode_on_the_next_turn(self):
        watch = mode._make_frame_watch()
        watch.eventFilter(None, QtCore.QEvent(QtCore.QEvent.Close))
        self.assertEqual(self.shots, [(0, mode._leave_from_window)])
        watch.deleteLater()

    def test_a_failure_in_the_filter_is_printed(self):
        watch = mode._make_frame_watch()
        with mock.patch.object(mode, "_sync_glass",
                               side_effect=RuntimeError("boom")), \
                mock.patch.object(mode.traceback, "print_exc") as printed:
            self.assertFalse(watch.eventFilter(
                None, QtCore.QEvent(QtCore.QEvent.Move)))
        printed.assert_called_once_with()
        watch.deleteLater()

    def test_the_real_window_s_move_reaches_the_glass(self):
        ghost, _glass = self.turn_on()
        ghost.host.show()
        self.app.processEvents()
        mode._watch_frame()
        first = mode._STATE.frame_watch
        mode._watch_frame()
        self.assertIs(mode._STATE.frame_watch, first)        # one filter
        with mock.patch.object(mode, "_sync_glass") as synced:
            ghost.host.move(ghost.host.x() + 25, ghost.host.y() + 5)
            self.app.processEvents()
        self.assertGreaterEqual(synced.call_count, 1)

    def test_closing_the_window_leaves_the_mode(self):
        self.turn_on()
        with mock.patch.object(mode, "disable",
                               return_value="Graph Overlay OFF"), \
                mock.patch.object(mode, "_show") as show:
            mode._leave_from_window()
        show.assert_called_once_with("Graph Overlay OFF - the window was closed")

    def test_closing_while_already_closing_or_off_does_nothing(self):
        with mock.patch.object(mode, "_show") as show:
            mode._leave_from_window()
            self.turn_on()
            mode._STATE.closing = True
            mode._leave_from_window()
        show.assert_not_called()


# -------------------------------------------------------------- the follow

class Timers(ModeCase):

    def test_one_follow_timer_started_and_stopped(self):
        mode._start_timers()
        timer = mode._STATE.timers[0]
        self.assertEqual(len(mode._STATE.timers), 1)
        self.assertTrue(timer.isActive())
        self.assertEqual(timer.interval(), mode.FOLLOW_MS)
        mode._stop_timers()
        self.assertFalse(timer.isActive())
        self.assertEqual(mode._STATE.timers, [])

    def test_a_timer_already_deleted_is_passed_over(self):
        mode._start_timers()
        shiboken6.delete(mode._STATE.timers[0])
        mode._stop_timers()
        self.assertEqual(mode._STATE.timers, [])


class Follow(ModeCase):

    def setUp(self):
        super(Follow, self).setUp()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.active = True
        stack.enter_context(mock.patch.object(
            viewport, "maya_active", side_effect=lambda: self.active))
        self.synced = stack.enter_context(mock.patch.object(mode,
                                                            "_sync_glass"))
        self.connected = stack.enter_context(mock.patch.object(
            mode, "_connect_canvas"))
        self.rewatched = stack.enter_context(mock.patch.object(
            mode, "_watch_chrome"))
        self.shown = stack.enter_context(mock.patch.object(mode, "_show"))

    def test_a_tick_while_off_does_nothing(self):
        with mock.patch.object(mode, "_follow_once") as once:
            mode._follow()
        once.assert_not_called()

    def test_a_tick_s_failure_is_printed(self):
        self.turn_on()
        with mock.patch.object(mode, "_follow_once",
                               side_effect=RuntimeError("boom")), \
                mock.patch.object(mode.traceback, "print_exc") as printed:
            mode._follow()
        printed.assert_called_once_with()

    def test_a_tick_keeps_the_window_and_the_glass_in_step(self):
        ghost, glass = self.turn_on()
        mode._STATE.canvas_pointer = ghost.live.pointer
        mode._follow()
        self.assertTrue(mode._STATE.active)
        self.synced.assert_called_once_with()
        self.assertEqual(ghost.calls, ["open_channel_list", "keep_invisible"])
        self.assertEqual(glass.calls, ["keep_click_through"])
        self.connected.assert_not_called()
        self.assertEqual(mode._STATE.ticks, 1)

    def test_maya_behind_another_program_keeps_the_list_alone(self):
        ghost, glass = self.turn_on()
        mode._STATE.canvas_pointer = ghost.live.pointer
        self.active = False
        mode._follow()
        self.assertFalse(mode._STATE.active)
        self.assertEqual(ghost.calls, ["keep_invisible"])
        self.assertEqual(glass.calls, [])

    def test_a_new_canvas_is_connected(self):
        ghost, _glass = self.turn_on()
        mode._STATE.canvas_pointer = 5
        mode._follow()
        self.connected.assert_called_once_with()

    def test_a_new_canvas_at_the_old_address_is_connected(self):
        """2026-10-27: Maya made the canvas again where the old one was freed - the address
        the same, the mark `_connect_canvas` left on the old one missing."""
        ghost, _glass = self.turn_on()
        marks = {}
        ghost.live.property = marks.get
        ghost.live.setProperty = marks.__setitem__
        mode._STATE.canvas_pointer = ghost.live.pointer
        mode._follow()
        self.connected.assert_called_once_with()
        marks[mode.CONNECTED] = True
        mode._follow()
        self.connected.assert_called_once_with()

    def test_the_chrome_is_looked_at_again_every_few_ticks(self):
        ghost, _glass = self.turn_on()
        mode._STATE.canvas_pointer = ghost.live.pointer
        for _ in range(mode.REWATCH_TICKS):
            mode._follow()
        self.assertEqual(self.rewatched.call_count, 1)

    def test_maya_taking_the_graph_editor_back_ends_the_mode(self):
        ghost, _glass = self.turn_on()
        ghost.is_alive = False
        with mock.patch.object(mode, "disable",
                               return_value="Graph Overlay OFF"):
            mode._follow()
        self.shown.assert_called_once_with(
            "Graph Overlay OFF - the Graph Editor was opened in its own window")
        self.synced.assert_not_called()

    def test_a_deleted_panel_of_ours_ends_the_mode(self):
        ghost, _glass = self.turn_on(borrow=False)
        ghost.is_alive = False
        with mock.patch.object(mode, "disable",
                               return_value="Graph Overlay OFF"):
            mode._follow()
        self.shown.assert_called_once_with(
            "Graph Overlay OFF - its Graph Editor panel was deleted")


# ---------------------------------------------------------------- the jobs

class Jobs(ModeCase):

    def test_the_scene_jobs_are_made_in_the_root_scope(self):
        """2026-10-09: the overlay is the scene's, not a card's - a popup
        copy's close must not take its jobs."""
        with hubcopy.entered("aCopysScope"):
            mode._install_jobs()
        made = [c[1] for c in self.cmds.calls if c[0] == "scriptJob"]
        self.assertEqual([m["event"][0] for m in made],
                         ["SceneOpened", "NewSceneOpened"])
        self.assertTrue(all(m["event"][1] is mode._on_scene for m in made))
        self.assertTrue(all(m["killWithScene"] is False for m in made))
        self.assertEqual(self.cmds.job_scopes, [None, None])
        self.assertEqual(mode._STATE.jobs, [1, 2])

    def test_a_job_that_cannot_be_made_is_skipped(self):
        self.cmds.fail = True
        mode._install_jobs()
        self.assertEqual(mode._STATE.jobs, [])

    def test_the_jobs_are_killed_and_forgotten(self):
        mode._STATE.jobs = [4, 9]
        mode._kill_jobs()
        kills = [c[1] for c in self.cmds.calls if c[0] == "scriptJob"]
        self.assertEqual(kills, [{"kill": 4, "force": True},
                                 {"kill": 9, "force": True}])
        self.assertEqual(mode._STATE.jobs, [])

    def test_a_job_that_cannot_be_killed_is_forgotten_all_the_same(self):
        mode._STATE.jobs = [4]
        self.cmds.fail = True
        mode._kill_jobs()
        self.assertEqual(mode._STATE.jobs, [])

    def test_a_scene_opened_leaves_the_mode_deferred(self):
        self.turn_on()
        mode._on_scene()
        self.assertEqual(self.cmds.deferred, [mode._leave_for_scene])

    def test_a_scene_opened_while_off_or_closing_does_nothing(self):
        mode._on_scene()
        self.turn_on()
        mode._STATE.closing = True
        mode._on_scene()
        self.assertEqual(self.cmds.deferred, [])

    def test_leaving_for_a_scene_says_why(self):
        self.turn_on()
        with mock.patch.object(mode, "disable",
                               return_value="Graph Overlay OFF"), \
                mock.patch.object(mode, "_show") as show:
            mode._leave_for_scene()
        show.assert_called_once_with("Graph Overlay OFF - a scene was opened")

    def test_leaving_for_a_scene_while_off_does_nothing(self):
        with mock.patch.object(mode, "_show") as show:
            mode._leave_for_scene()
        show.assert_not_called()


# ------------------------------------------------------------- the section

class Section(ModeCase):

    def test_the_button_toggles(self):
        with mock.patch.object(mode, "toggle", return_value="ok") as toggle:
            self.assertEqual(mode._press(), "ok")
        toggle.assert_called_once_with()

    def test_a_failing_toggle_is_said_and_raised(self):
        with mock.patch.object(mode, "toggle",
                               side_effect=RuntimeError("boom")), \
                mock.patch.object(mode, "_show") as show:
            with self.assertRaises(RuntimeError):
                mode._press()
        show.assert_called_once_with("RuntimeError: boom")

    def test_open_while_its_status_line_stands(self):
        self.assertFalse(mode.is_open())
        self.cmds.controls.add(mode.STATUS)
        self.assertTrue(mode.is_open())

    def test_show_window_opens_the_hub_on_this_section(self):
        import maya_hub
        with mock.patch.object(maya_hub, "show", return_value="hub") as show:
            self.assertEqual(mode.show_window(), "hub")
        show.assert_called_once_with(mode.HUB_SECTION)


if __name__ == "__main__":
    unittest.main()

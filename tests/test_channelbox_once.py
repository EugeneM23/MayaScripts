"""Our Channel Box reads the scene once a change (2026-10-27): a selection used to read
it twice - its own SelectionChanged callback and the side panel's refresh, 6-9 ms each
with a rig control selected. A read the box missed while hidden (a selection, the
time) is made up the next time the side panel shows it."""
import sys
import unittest

import maya_channelbox as cb


class FakeBox(object):
    def __init__(self):
        self.calls = []
        self.objects = []

    def refresh(self):
        self.calls.append("full")

    def on_values(self):
        self.calls.append("values")

    def on_time(self):
        self.calls.append("time")


class ReadOnce(unittest.TestCase):

    def setUp(self):
        self.saved_state = getattr(sys, "_skeldar_channelbox", None)
        if hasattr(sys, "_skeldar_channelbox"):
            del sys._skeldar_channelbox
        self.box = FakeBox()
        self.shown = True
        self.saved = (cb.current, cb._shown, cb._watch_nodes, cb._run_pending)
        cb.current = lambda: self.box
        cb._shown = lambda: self.shown
        cb._watch_nodes = lambda nodes: None
        self.timers = []
        timers = self.timers

        class Timer(object):
            @staticmethod
            def singleShot(ms, fn):
                timers.append(fn)                            # fired by hand: `fire()`

        class Qt(object):
            QtCore = type("QtCore", (), {"QTimer": Timer})

        self.saved_hubqt = sys.modules.get("maya_hubqt")
        sys.modules["maya_hubqt"] = type(sys)("maya_hubqt")
        sys.modules["maya_hubqt"].qt = lambda: Qt

    def tearDown(self):
        cb.current, cb._shown, cb._watch_nodes, cb._run_pending = self.saved
        if self.saved_hubqt is None:
            sys.modules.pop("maya_hubqt", None)
        else:
            sys.modules["maya_hubqt"] = self.saved_hubqt
        if self.saved_state is None:
            if hasattr(sys, "_skeldar_channelbox"):
                del sys._skeldar_channelbox
        else:
            sys._skeldar_channelbox = self.saved_state

    def fire(self):
        """The event loop turns: the scheduled read runs."""
        while self.timers:
            self.timers.pop(0)()

    def test_the_callback_then_the_side_panel_read_once(self):
        cb._schedule("full")
        self.fire()
        cb.refresh()
        self.assertEqual(self.box.calls, ["full"])

    def test_the_side_panel_first_then_the_callback_read_once(self):
        cb._schedule("full")
        cb.refresh()
        self.fire()
        self.assertEqual(self.box.calls, ["full"])

    def test_every_new_change_reads_again(self):
        cb._schedule("full")
        self.fire()
        cb._schedule("full")
        self.fire()
        cb.refresh()
        self.assertEqual(self.box.calls, ["full", "full"])

    def test_a_read_missed_while_hidden_is_made_up_when_shown(self):
        cb._schedule("full")
        cb.refresh()
        self.shown = False
        cb._schedule("full")
        self.fire()
        self.assertEqual(self.box.calls, ["full"])
        self.shown = True
        cb.refresh()
        self.assertEqual(self.box.calls, ["full", "full"])

    def test_the_time_moving_while_hidden_is_made_up_when_shown(self):
        cb.refresh()
        self.shown = False
        cb._time_changed()
        self.assertEqual(self.box.calls, ["full"])
        self.shown = True
        cb.refresh()
        self.assertEqual(self.box.calls, ["full", "full"])

    def test_a_refresh_with_nothing_changed_reads_nothing(self):
        cb.refresh()
        cb.refresh()
        self.assertEqual(self.box.calls, ["full"])

    def test_a_new_box_is_read(self):
        cb.refresh()
        self.box = FakeBox()
        cb.refresh()
        self.assertEqual(self.box.calls, ["full"])

    def test_values_only_still_read_the_values(self):
        cb.refresh()
        cb._schedule("values")
        self.fire()
        self.assertEqual(self.box.calls, ["full", "values"])


if __name__ == "__main__":
    unittest.main()

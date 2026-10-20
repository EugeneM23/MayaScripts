"""Our Channel Box during a Time Bar key drag (2026-10-20, «ключи сильно задерживаются
за курсором»): a full read on every step of the drag cost 17-121 ms; the values only
while the drag stands, one full read once it is let go."""
import sys
import types
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


class DragKeys(unittest.TestCase):

    def setUp(self):
        self.saved_state = getattr(sys, "_skeldar_channelbox", None)
        if hasattr(sys, "_skeldar_channelbox"):
            del sys._skeldar_channelbox
        self.saved_scene = sys.modules.get("maya_timebar.scene")
        self.scene = types.ModuleType("maya_timebar.scene")
        self.scene._LIVE = {}
        sys.modules["maya_timebar.scene"] = self.scene
        self.box = FakeBox()
        self.saved = (cb.current, cb._shown, cb._watch_nodes, cb._schedule)
        cb.current = lambda: self.box
        cb._shown = lambda: True
        cb._watch_nodes = lambda nodes: None
        self.scheduled = []

        def schedule(kind):
            self.scheduled.append(kind)
            state = cb._state()
            if state.get("pending") != "full":
                state["pending"] = "full" if kind == "full" else (state.get("pending") or "values")
        cb._schedule = schedule

    def tearDown(self):
        cb.current, cb._shown, cb._watch_nodes, cb._schedule = self.saved
        if self.saved_scene is None:
            sys.modules.pop("maya_timebar.scene", None)
        else:
            sys.modules["maya_timebar.scene"] = self.saved_scene
        if self.saved_state is None:
            if hasattr(sys, "_skeldar_channelbox"):
                del sys._skeldar_channelbox
        else:
            sys._skeldar_channelbox = self.saved_state

    def test_a_key_edit_with_no_drag_reads_everything(self):
        cb._key_edited()
        cb._run_pending()
        self.assertEqual(self.box.calls, ["full"])

    def test_in_a_drag_a_key_edit_reads_the_values_only(self):
        self.scene._LIVE = {"curves": {}}
        for _step in range(3):
            cb._key_edited()
            cb._run_pending()
        self.assertEqual(self.box.calls, ["values", "values", "values"])

    def test_the_drag_let_go_reads_everything_once(self):
        self.scene._LIVE = {"curves": {}}
        cb._key_edited()
        cb._run_pending()
        cb._key_edited()                  # the release's edit, delivered while the drag stood
        self.scene._LIVE = {}             # live_end cleared it
        cb._run_pending()
        cb._schedule("values")            # a value set later: values again
        cb._run_pending()
        self.assertEqual(self.box.calls, ["values", "full", "values"])


if __name__ == "__main__":
    unittest.main()

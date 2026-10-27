"""maya_timebar.meter - the scrub meter (2026-10-16): Maya's time-change callback clocks
every frame change for a few seconds, the Time Bar's own steps are recorded beside
it, and the report comes when it stops. On a fake OpenMaya and a fake timer."""
import sys
import types
import unittest
from unittest import mock

from maya_timebar import meter


class FakeOpenMaya(object):
    def __init__(self):
        self.callbacks = {}
        self.removed = []

    def module(self):
        om = types.ModuleType("maya.api.OpenMaya")
        fake = self

        class MDGMessage(object):
            @staticmethod
            def addTimeChangeCallback(fn):
                cid = len(fake.callbacks) + 1
                fake.callbacks[cid] = fn
                return cid

        class MMessage(object):
            @staticmethod
            def removeCallback(cid):
                fake.removed.append(cid)
                fake.callbacks.pop(cid, None)

        om.MDGMessage, om.MMessage = MDGMessage, MMessage
        return om


class Meter(unittest.TestCase):

    def setUp(self):
        meter._state().pop("meter", None)
        self.om = FakeOpenMaya()
        self.timers = []
        timers = self.timers

        class Timer(object):
            @staticmethod
            def singleShot(ms, fn):
                timers.append((ms, fn))

        class Qt(object):
            QtCore = types.SimpleNamespace(QTimer=Timer)

        hubqt = types.ModuleType("maya_hubqt")
        hubqt.qt = lambda: Qt
        om = self.om.module()
        api = types.ModuleType("maya.api")
        api.OpenMaya = om
        import maya
        self.patches = [
            mock.patch.dict(sys.modules, {"maya.api": api, "maya.api.OpenMaya": om, "maya_hubqt": hubqt}),
            mock.patch.object(maya, "api", api, create=True),
            mock.patch.object(meter, "say", side_effect=lambda text, stay_ms=3000: text),
        ]
        for p in self.patches:
            p.start()
        self.clock = [0.0]
        self.patches.append(mock.patch.object(meter, "clock", side_effect=lambda: self.clock[0]))
        self.patches[-1].start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        meter._state().pop("meter", None)

    def tick(self, ms):
        self.clock[0] += ms
        for fn in list(self.om.callbacks.values()):
            fn()

    def test_start_hangs_a_callback_and_a_timer_for_the_seconds(self):
        text = meter.start(4)
        self.assertTrue(meter.running())
        self.assertIn("4 s", text)
        self.assertEqual(len(self.om.callbacks), 1)
        self.assertEqual(self.timers[0][0], 4000)

    def test_a_second_start_while_measuring_changes_nothing(self):
        meter.start(4)
        text = meter.start(4)
        self.assertIn("already measuring", text)
        self.assertEqual(len(self.om.callbacks), 1)

    def test_maya_s_slider_scrubbing_is_reported_by_its_frame_changes(self):
        meter.start(2)
        for _ in range(11):
            self.tick(20.0)
        text = self.timers[0][1]()                    # the timer ends it
        self.assertFalse(meter.running())
        self.assertEqual(self.om.callbacks, {})
        self.assertIn("11 frame changes", text)
        self.assertIn("50 a second", text)
        self.assertIn("Maya's own slider drove it", text)

    def test_the_time_bar_s_own_steps_are_reported_beside(self):
        meter.start(2)
        for i in range(5):
            self.tick(25.0)
            meter.record(1.5, 8.0 + i)
        text = meter.stop()
        self.assertIn("the Time Bar's own work 1.50 ms", text)
        self.assertIn("Maya's frame change 10.0 ms", text)

    def test_nothing_dragged_says_so(self):
        meter.start(2)
        self.assertIn("no scrubbing", meter.stop())

    def test_a_record_with_no_meter_standing_is_dropped(self):
        meter.record(1.0, 2.0)
        self.assertFalse(meter.running())

    def test_stop_with_nothing_running_is_empty(self):
        self.assertEqual(meter.stop(), "")


if __name__ == "__main__":
    unittest.main()

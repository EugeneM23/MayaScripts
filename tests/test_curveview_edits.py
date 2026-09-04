"""The undo chunk and the throttle."""

import unittest

from maya_curveview import edits


class FakeCmds(object):

    def __init__(self, fail=False):
        self.calls = []
        self.chunks = []
        self.tangents = []
        self.fail = fail
        self.time = None
        self.selected = []
        self.cut = False

    def undoInfo(self, **kwargs):
        if kwargs.get("openChunk"):
            self.chunks.append("open")
        if kwargs.get("closeChunk"):
            self.chunks.append("close")

    def keyframe(self, *args, **kwargs):
        if kwargs.get("query") and kwargs.get("selected"):
            return list(self.selected)
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("no keys selected")

    def keyTangent(self, target, **kwargs):
        self.tangents.append((target, kwargs))

    def setKeyframe(self, target, **kwargs):
        self.calls.append(kwargs)

    def cutKey(self, **kwargs):
        self.cut = True
        return 0

    def currentTime(self, *args, **kwargs):
        if kwargs.get("query"):
            return self.time or 0.0
        if args:
            self.time = args[0]
        return self.time


class Fixture(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        edits.cmds = self.fake
        edits._depth = 0

    def tearDown(self):
        edits.cmds = edits._real_cmds
        edits._depth = 0


class TestChunk(Fixture):

    def test_one_chunk_per_drag(self):
        edits.begin()
        edits.end()
        self.assertEqual(self.fake.chunks, ["open", "close"])

    def test_nesting_opens_once(self):
        edits.begin()
        edits.begin()
        edits.end()
        self.assertEqual(self.fake.chunks, ["open"])
        edits.end()
        self.assertEqual(self.fake.chunks, ["open", "close"])

    def test_an_extra_end_cannot_close_a_chunk_nobody_opened(self):
        edits.end()
        self.assertEqual(self.fake.chunks, [])
        self.assertFalse(edits.in_chunk())

    def test_the_chunk_closes_even_when_the_edit_raises(self):
        self.fake.fail = True
        edits.begin()
        try:
            edits.apply_delta(1.0, 0.0)
        except RuntimeError:
            pass
        edits.end()
        self.assertEqual(self.fake.chunks, ["open", "close"])


class TestDelta(Fixture):

    def test_apply_delta_moves_the_selected_keys_relatively(self):
        edits.apply_delta(2.0, 0.5)
        self.assertEqual(len(self.fake.calls), 1)
        call = self.fake.calls[0]
        self.assertTrue(call["relative"])
        self.assertTrue(call["edit"])
        self.assertEqual(call["timeChange"], 2.0)
        self.assertEqual(call["valueChange"], 0.5)
        self.assertEqual(call["animation"], "keys")

    def test_a_zero_delta_writes_nothing(self):
        edits.apply_delta(0.0, 0.0)
        self.assertEqual(self.fake.calls, [])

    def test_a_value_only_delta_still_writes(self):
        edits.apply_delta(0.0, 0.25)
        self.assertEqual(len(self.fake.calls), 1)


class TestTime(Fixture):

    def test_follow_time_respects_the_throttle(self):
        stamp = edits.follow_time(10.0, now=1.0, last=None, interval=0.05)
        self.assertEqual(self.fake.time, 10.0)
        self.assertEqual(stamp, 1.0)
        held = edits.follow_time(11.0, now=1.01, last=1.0, interval=0.05)
        self.assertEqual(self.fake.time, 10.0)
        self.assertEqual(held, 1.0)

    def test_past_the_interval_it_moves_again(self):
        edits.follow_time(10.0, now=1.0, last=None)
        stamp = edits.follow_time(11.0, now=1.2, last=1.0)
        self.assertEqual(self.fake.time, 11.0)
        self.assertEqual(stamp, 1.2)

    def test_settle_is_never_gated(self):
        edits.settle(42.0)
        self.assertEqual(self.fake.time, 42.0)


class TestKeys(Fixture):

    def test_insert_keeps_the_shape(self):
        edits.insert_key("curveA", 12.0)
        self.assertTrue(self.fake.calls[0]["insert"])
        self.assertEqual(self.fake.calls[0]["time"], (12.0, 12.0))

    def test_set_tangent_writes_the_side_it_was_given(self):
        edits.set_tangent("curveA", 2, "out", 33.0)
        target, kwargs = self.fake.tangents[0]
        self.assertEqual(target, "curveA")
        self.assertEqual(kwargs["index"], (2, 2))
        self.assertEqual(kwargs["outAngle"], 33.0)

    def test_set_tangent_in_side(self):
        edits.set_tangent("curveA", 0, "in", -12.0)
        self.assertEqual(self.fake.tangents[0][1]["inAngle"], -12.0)

    def test_delete_selected_counts_before_the_cut(self):
        # cutKey(clear=True) answers 0 even when it worked, measured live,
        # so the count comes from the key selection instead.
        self.fake.selected = [1.0, 2.0, 5.0]
        self.assertEqual(edits.delete_selected(), 3)
        self.assertTrue(self.fake.cut)

    def test_deleting_nothing_cuts_nothing(self):
        self.fake.selected = []
        self.assertEqual(edits.delete_selected(), 0)
        self.assertFalse(self.fake.cut)


if __name__ == "__main__":
    unittest.main()

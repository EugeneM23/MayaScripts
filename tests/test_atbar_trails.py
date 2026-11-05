"""The AT bar's motion trail engine (2026-11-05), on a fake scene (no Maya).

«дуже тормозить сцена ... це все через моушен трейл з АТ»: Maya's snapshot trail cost 1.3 s a key edit on a
rig. Ours computes only the frames that changed, through the EM, in idle slices.
"""

import sys
import unittest
from unittest import mock

import maya.api.OpenMaya as om

from maya_atbar import trails

SET = om.MNodeMessage.kAttributeSet


class FakeScene(object):

    def __init__(self, current=10):
        self.now = current
        self.mouse = False
        self.play = False
        self.alive = set()
        self.hidden = set()
        self.curve_data = {}
        self.walked, self.writes, self.held_plugs, self.put = [], [], [], []

    def current(self):
        return self.now

    def playing(self):
        return self.play

    def mouse_down(self):
        return self.mouse

    def exists(self, uuid):
        return uuid in self.alive

    def visible(self, uuid):
        return uuid not in self.hidden

    def position(self, target, frame):
        return (float(frame), float(len(target)), 0.0)

    def reader(self, target):
        return lambda: self.position(target, self.now)

    def walk(self, frame_list, readers):
        self.walked.append(list(frame_list))
        out, here = {}, self.now
        for f in frame_list:
            self.now = f
            out[f] = {k: r() for k, r in readers.items()}
        self.now = here
        return out

    def curves(self, span):
        return {c: {f: v for f, v in d.items() if span[0] <= f <= span[1]} for c, d in self.curve_data.items()}

    def held(self, plugs):
        self.held_plugs.append(list(plugs))
        return [("plug", 1.0)]

    def put_back(self, held):
        self.put.append(held)

    def write(self, uuid, span, points):
        self.writes.append((uuid, span, dict(points)))


def fresh():
    sys._skeldar_attrail = {}
    st = trails.state()
    st["per_frame_ms"] = 5.0
    return st


def add(st, sc, handle="h", target="obj", span=(0, 20)):
    sc.alive.update((handle, target))
    tr = trails.Track(handle, target, span)
    st["tracks"][handle] = tr
    return tr


class Pure(unittest.TestCase):

    def test_the_span_round_trips_and_nonsense_reads_as_none(self):
        self.assertEqual(trails.parse_span(trails.span_text((0, 62))), (0, 62))
        self.assertEqual(trails.parse_span("40 10.0"), (10, 40))
        for bad in (None, "", "a b", "1 2 3"):
            self.assertIsNone(trails.parse_span(bad))

    def test_the_point_is_the_world_rotate_pivot(self):
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 10, 20, 30, 1]
        self.assertEqual(trails.pivot_point((0, 0, 0), m), (10, 20, 30))
        turned = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 10, 20, 30, 1]      # 90 degrees about Z
        self.assertEqual(trails.pivot_point((1, 0, 0), turned), (10, 21, 30))

    def test_any_hidden_parent_or_a_tab_s_lod_hides_the_trail(self):
        self.assertTrue(trails.shown([(1, 1, 0, 0), (1, 1, 1, 1)]))
        self.assertFalse(trails.shown([(1, 1, 0, 0), (1, 0, 0, 0)]))      # a hidden scene tab
        self.assertFalse(trails.shown([(0, 1, 0, 0)]))
        self.assertFalse(trails.shown([(1, 1, 1, 0)]))

    def test_only_the_frames_a_curve_changed_and_every_frame_of_a_new_or_gone_one(self):
        before = {"a": {1: 0.0, 2: 0.0, 3: 0.0}, "gone": {7: 1.0}}
        after = {"a": {1: 0.0, 2: 5.0, 3: 0.0}, "new": {9: 1.0, 10: 2.0}}
        self.assertEqual(trails.curve_changes(before, after), {2, 7, 9, 10})

    def test_the_spans_union(self):
        self.assertEqual(trails.union_span([(5, 9), None, (0, 3)]), (0, 9))
        self.assertIsNone(trails.union_span([]))


class Tick(unittest.TestCase):

    def setUp(self):
        self.st = fresh()
        self.sc = FakeScene()
        self.arm = mock.patch.object(trails, "arm").start()
        self.addCleanup(mock.patch.stopall)

    def test_dirty_frames_are_walked_nearest_the_current_one_first(self):
        tr = add(self.st, self.sc, span=(0, 20))
        trails.tick(self.sc)
        first = self.sc.walked[0]
        self.assertEqual(first[:3], [10, 9, 11])
        self.assertEqual(self.sc.writes[-1][0], "h")
        trails.run_until_clean(self.sc)
        self.assertEqual(tr.dirty, set())
        self.assertEqual(tr.points[3], (3.0, 3.0, 0.0))

    def test_one_walk_serves_every_trail(self):
        add(self.st, self.sc, "h1", "a", (0, 5))
        add(self.st, self.sc, "h2", "bb", (0, 5))
        trails.run_until_clean(self.sc)
        self.assertEqual(sorted(f for batch in self.sc.walked for f in batch), list(range(6)))

    def test_a_tweak_is_put_back_after_the_walk(self):
        add(self.st, self.sc)
        trails.tick(self.sc)
        self.assertEqual(self.sc.put, [[("plug", 1.0)]])

    def test_nothing_is_walked_while_the_mouse_is_down_or_playing(self):
        add(self.st, self.sc)
        self.sc.mouse = True
        trails.tick(self.sc)
        self.sc.mouse, self.sc.play = False, True
        trails.tick(self.sc)
        self.assertEqual(self.sc.walked, [])
        self.arm.assert_called_with(trails.WAIT_MS)

    def test_a_hidden_trail_waits_until_it_shows(self):
        tr = add(self.st, self.sc, span=(0, 4))
        self.sc.hidden.add("h")
        self.assertEqual(trails.run_until_clean(self.sc), 0)
        self.assertEqual(len(tr.dirty), 5)
        self.sc.hidden.clear()
        trails.run_until_clean(self.sc)
        self.assertEqual(tr.dirty, set())

    def test_a_curve_edit_dirties_only_the_frames_it_changed(self):
        tr = add(self.st, self.sc, span=(0, 20))
        self.sc.curve_data = {"c": {f: 0.0 for f in range(21)}}
        trails.run_until_clean(self.sc)
        walked_before = len(self.sc.walked)
        self.sc.curve_data["c"][14] = 3.0
        self.sc.curve_data["c"][15] = 3.0
        trails._on_curves()
        trails.run_until_clean(self.sc)
        self.assertEqual(sorted(f for batch in self.sc.walked[walked_before:] for f in batch), [14, 15])
        self.assertEqual(tr.dirty, set())

    def test_a_static_set_dirties_every_frame(self):
        tr = add(self.st, self.sc, span=(0, 3))
        trails.run_until_clean(self.sc)
        plug = mock.Mock(isDestination=False)
        trails._on_attribute(SET, plug, None, "h")
        self.assertEqual(tr.dirty, {0, 1, 2, 3})

    def test_a_tweak_moves_only_the_current_point_and_it_survives_the_walk(self):
        tr = add(self.st, self.sc, span=(0, 20))
        trails.run_until_clean(self.sc)
        plug = mock.Mock(isDestination=True)
        trails._on_attribute(SET, plug, None, "h")
        self.assertEqual(tr.dirty, set())
        self.sc.position = lambda target, frame: (99.0, 0.0, 0.0) if frame == 10 else (float(frame), 3.0, 0.0)
        walked = len(self.sc.walked)
        trails.tick(self.sc)
        self.assertEqual(tr.points[10], (99.0, 0.0, 0.0))
        self.assertEqual(len(self.sc.walked), walked)
        tr.dirty.add(10)
        self.sc.position = lambda target, frame: (float(frame), 3.0, 0.0)
        trails.tick(self.sc)
        self.assertEqual(tr.points[10], (99.0, 0.0, 0.0))
        self.assertNotIn(10, tr.dirty)

    def test_the_time_moving_away_brings_the_keyed_pose_back(self):
        tr = add(self.st, self.sc, span=(0, 20))
        self.st["live_frames"] = {10}
        with mock.patch.object(trails, "scene", return_value=self.sc):
            self.sc.now = 12
            trails._on_time()
        self.assertIn(10, tr.dirty)
        self.assertEqual(self.st["live_frames"], set())

    def test_a_deleted_trail_or_object_is_dropped(self):
        add(self.st, self.sc, "h1", "a")
        add(self.st, self.sc, "h2", "b")
        self.sc.alive.discard("h1")
        self.sc.alive.discard("b")
        with mock.patch.object(trails, "_unwatch"):
            trails.tick(self.sc)
        self.assertEqual(self.st["tracks"], {})


class Tracking(unittest.TestCase):

    def setUp(self):
        self.st = fresh()
        mock.patch.object(trails, "arm").start()
        self.watch = mock.patch.object(trails, "_watch").start()
        self.addCleanup(mock.patch.stopall)

    def test_tracking_the_same_trail_again_keeps_its_points(self):
        tr = trails.track("h", "obj", (0, 9))
        tr.points[3] = (1, 2, 3)
        self.assertIs(trails.track("h", "obj", (0, 9)), tr)
        self.assertEqual(self.watch.call_count, 1)
        self.assertIsNot(trails.track("h", "obj", (0, 12)), tr)


if __name__ == "__main__":
    unittest.main()

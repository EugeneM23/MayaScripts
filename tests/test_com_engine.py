"""The trail engine's decisions, on a fake scene (no Maya)."""

import importlib
import sys
import unittest

from maya_com import engine


class FakeScene(object):

    def __init__(self, groups, span=(0, 20), current=10):
        self.groups = dict(groups)            # uuid -> path
        self.span = span
        self.now = current
        self.mouse = False
        self.play = False
        self.walked = []
        self.writes = []
        self.put = []
        self.tweak_list = []
        self.fail_walk = False
        self.settings_by = {u: {"trail": 1, "range": 0, "around": 5}
                            for u in groups}

    def current(self):
        return self.now

    def playback(self):
        return self.span

    def animation(self):
        return (self.span[0] - 10, self.span[1] + 10)

    def playing(self):
        return self.play

    def mouse_down(self):
        return self.mouse

    def group(self, uuid):
        return self.groups.get(uuid)

    def settings(self, group):
        uuid = [u for u, g in self.groups.items() if g == group][0]
        return self.settings_by[uuid]

    def value(self, uuid, frame):
        return (float(frame), float(len(uuid)), 0.0, 0.0)

    def reader(self, group):
        uuid = [u for u, g in self.groups.items() if g == group][0]
        return lambda: self.value(uuid, self.now)

    def walk(self, frame_list, readers):
        if self.fail_walk:
            raise RuntimeError("boom")
        self.walked.append(list(frame_list))
        out = {}
        here = self.now
        for f in frame_list:
            self.now = f
            out[f] = {u: r() for u, r in readers.items()}
        self.now = here
        return out

    def tweaks(self, plugs):
        return list(self.tweak_list)

    def put_back(self, tweaks):
        self.put.append(list(tweaks))

    def write(self, group, span, points):
        self.writes.append((group, span, dict(points)))


def fresh():
    sys._skeldar_com = {}
    st = engine.state()
    st["per_frame_ms"] = 5.0
    return st


def add(st, sc, uuid):
    tr = engine.Track(uuid, engine.span_for(sc.settings(sc.groups[uuid]), sc))
    st["tracks"][uuid] = tr
    return tr


class Tick(unittest.TestCase):

    def setUp(self):
        self.st = fresh()
        self.sc = FakeScene({"aaaa": "|a:CenterOfMass"})
        self.tr = add(self.st, self.sc, "aaaa")

    def test_the_nearest_frames_first_within_the_budget(self):
        n = engine.tick(self.sc)
        self.assertEqual(n, 4)                  # (25 - 5) // 5
        self.assertEqual(self.sc.walked, [[10, 9, 11, 8]])
        self.assertEqual(len(self.sc.writes), 1)
        self.assertEqual(self.tr.points[9], (9.0, 4.0, 0.0, 0.0))

    def test_no_walk_while_a_mouse_button_is_down(self):
        self.sc.mouse = True
        self.assertEqual(engine.tick(self.sc), 0)
        self.assertEqual(self.sc.walked, [])

    def test_no_walk_during_playback(self):
        self.sc.play = True
        self.assertEqual(engine.tick(self.sc), 0)

    def test_the_live_point_moves_even_with_the_mouse_down(self):
        self.sc.mouse = True
        self.st["live"] = True
        engine.tick(self.sc)
        self.assertEqual(self.tr.points[10], (10.0, 4.0, 0.0, 0.0))
        self.assertNotIn(10, self.tr.dirty)
        self.assertEqual(len(self.sc.writes), 1)

    def test_run_until_clean_computes_every_frame(self):
        engine.run_until_clean(self.sc)
        self.assertEqual(sorted(self.tr.points), list(range(0, 21)))
        self.assertEqual(engine.pending(), 0)

    def test_tweaks_are_put_back_even_when_the_walk_fails(self):
        self.sc.tweak_list = [("plug", 1.0)]
        self.sc.fail_walk = True
        with self.assertRaises(RuntimeError):
            engine.tick(self.sc)
        self.assertEqual(self.sc.put, [[("plug", 1.0)]])
        self.assertFalse(self.st.get("busy"))

    def test_a_vanished_group_is_dropped(self):
        self.sc.groups = {}
        self.assertEqual(engine.tick(self.sc), 0)
        self.assertEqual(self.st["tracks"], {})

    def test_two_characters_share_one_walk(self):
        self.sc.groups["bbbbbb"] = "|b:CenterOfMass"
        self.sc.settings_by["bbbbbb"] = {"trail": 1, "range": 0, "around": 5}
        other = add(self.st, self.sc, "bbbbbb")
        engine.tick(self.sc)
        self.assertEqual(len(self.sc.walked), 1)
        self.assertEqual(other.points[11], (11.0, 6.0, 0.0, 0.0))

    def test_around_follows_the_time(self):
        self.sc.settings_by["aaaa"]["range"] = 1
        engine.tick(self.sc)
        self.assertEqual(self.tr.span, (5, 15))
        self.sc.now = 18
        engine.tick(self.sc)
        self.assertEqual(self.tr.span, (13, 23))
        self.assertIn(23, self.tr.dirty | set(self.tr.points))


class Tracks(unittest.TestCase):

    def test_rerange_keeps_the_points_inside(self):
        tr = engine.Track("u", (0, 4))
        tr.points = {f: (f, 0, 0, 0) for f in range(5)}
        tr.dirty = set()
        tr.rerange((2, 7))
        self.assertEqual(sorted(tr.points), [2, 3, 4])
        self.assertEqual(tr.dirty, {5, 6, 7})

    def test_the_state_lives_on_sys_across_a_reload(self):
        st = fresh()
        st["tracks"]["keep"] = engine.Track("keep", (0, 1))
        importlib.reload(engine)
        self.assertIn("keep", engine.state()["tracks"])


if __name__ == "__main__":
    unittest.main()

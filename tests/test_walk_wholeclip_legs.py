"""maya_walk.wholeclip's legs and pelvis on a whole clip (2026-11-19, the animator's TwoHand batch review: feet
spread past the norm and knees turned in, knee kinks, the legs wrong at the clip's end, the pelvis sinking): the
contacts at the clip's ends, a contact's motion along the floor, the feet's width held to what the walk asks, the
leg's soft reach and the sink it asks, the knee kept out and the bones' roll kept about the knee's hinge."""
import math
import unittest

import numpy as np

from maya_startstop import model as ss
from maya_walk import wholeclip as wcl
from tests.test_walk_wholeclip import loop_clip, tiled


def frame(pos, rot=None):
    m = np.eye(4)
    if rot is not None:
        m[:3, :3] = rot
    m[3, :3] = pos
    return m


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])


class EdgeContacts(unittest.TestCase):
    def test_a_foot_down_from_the_first_frame_joins_the_contact_it_runs_into(self):
        down = np.array([1, 1, 1, 1, 1, 1, 0, 0, 0, 0], bool)
        self.assertEqual(wcl.edge_contacts([(3, 5)], down, 10), [(0, 5)])

    def test_a_landing_at_the_last_frame_is_a_contact_of_its_own(self):
        down = np.array([0, 1, 1, 1, 0, 0, 0, 1, 1, 1], bool)
        self.assertEqual(wcl.edge_contacts([(1, 3)], down, 10), [(1, 3), (7, 9)])

    def test_a_foot_in_the_air_at_the_ends_adds_nothing(self):
        down = np.array([0, 0, 1, 1, 1, 0, 0, 0, 0, 0], bool)
        self.assertEqual(wcl.edge_contacts([(2, 4)], down, 10), [(2, 4)])

    def test_a_contact_already_at_an_end_is_left(self):
        down = np.ones(10, bool)
        self.assertEqual(wcl.edge_contacts([(0, 9)], down, 10), [(0, 9)])


class ContactMotion(unittest.TestCase):
    def test_the_foot_keeps_its_height_and_tilt_and_takes_the_floor_place_and_heading(self):
        clip = frame([10.0, 8.0, 5.0], rot_x(20.0))
        turn = ss.yaw(math.radians(30.0))
        blended = frame([14.0, 13.0, 2.0], rot_x(35.0) @ turn)
        motion = wcl.contact_motion(clip, blended)
        moved = clip @ motion
        self.assertAlmostEqual(moved[3, 1], 8.0, places=9)                  # the height the clip has
        np.testing.assert_allclose(moved[3, [0, 2]], [14.0, 2.0], atol=1e-9)  # the place along the floor the walk's
        np.testing.assert_allclose(motion[:3, 1], [0.0, 1.0, 0.0], atol=1e-12)   # a turn about up only
        # a foot the walk does not move is not moved
        np.testing.assert_allclose(wcl.contact_motion(clip, clip), np.eye(4), atol=1e-12)


class Reach(unittest.TestCase):
    def test_soft_reach_is_the_leg_up_to_the_soft_zone_then_eases_under_the_limit(self):
        self.assertEqual(wcl.soft_reach(70.0, 85.0, 4.0), 70.0)
        self.assertEqual(wcl.soft_reach(81.0, 85.0, 4.0), 81.0)
        values = [wcl.soft_reach(d, 85.0, 4.0) for d in np.linspace(80.0, 100.0, 81)]
        self.assertTrue(all(v < 85.0 for v in values))
        self.assertTrue(all(b >= a for a, b in zip(values, values[1:])))
        slope = (wcl.soft_reach(81.0 + 1e-5, 85.0, 4.0) - wcl.soft_reach(81.0, 85.0, 4.0)) / 1e-5
        self.assertAlmostEqual(slope, 1.0, places=3)                        # no corner where it begins

    def test_the_sink_is_what_puts_the_leg_at_its_length(self):
        hip, goal = np.array([0.0, 90.0, 0.0]), np.array([30.0, 0.0, 0.0])
        drop = wcl.sink_for(hip, goal, 85.0)
        self.assertAlmostEqual(np.linalg.norm(goal - (hip - [0.0, drop, 0.0])), 85.0, places=9)
        self.assertEqual(wcl.sink_for(hip, goal, 200.0), 0.0)


class KneePlane(unittest.TestCase):
    def test_a_knee_turned_in_comes_out_to_the_floor_and_one_out_is_left(self):
        e = np.array([0.0, -1.0, 0.0])
        outward = np.array([1.0, 0.0, 0.0])
        inward = ss._unit(np.array([-0.6, 0.0, 0.8]))
        got = wcl.knee_plane(inward, e, outward, -0.1)
        self.assertAlmostEqual(float(np.dot(got, outward)), -0.1, places=9)
        self.assertAlmostEqual(float(np.dot(got, e)), 0.0, places=9)
        self.assertGreater(got[2], 0.0)                                     # turned the least way: still forward
        out = ss._unit(np.array([0.3, 0.0, 0.9]))
        np.testing.assert_allclose(wcl.knee_plane(out, e, outward, 0.0), out)

    def test_knee_share_reads_the_bend_against_the_body(self):
        hip, ankle = np.array([0.0, 90.0, 0.0]), np.array([0.0, 10.0, 0.0])
        self.assertAlmostEqual(wcl.knee_share(hip, [5.0, 50.0, 0.0], ankle, [1.0, 0.0, 0.0]), 1.0)
        self.assertAlmostEqual(wcl.knee_share(hip, [-5.0, 50.0, 0.0], ankle, [1.0, 0.0, 0.0]), -1.0)


class Width(unittest.TestCase):
    def test_the_bounds_follow_the_ask_and_never_cross_feet_the_clip_keeps_apart(self):
        lo, hi = wcl.width_bounds([20.0, 4.0, -10.0], [-16.0, -16.0, 0.0], least=5.0, slack=3.0)
        np.testing.assert_allclose(lo, [5.0, 4.0, -10.0])
        np.testing.assert_allclose(hi, [23.0, 7.0, -7.0])
        lo, hi = wcl.width_bounds([10.0], [6.0], least=5.0, slack=3.0)
        np.testing.assert_allclose([lo[0], hi[0]], [7.0, 19.0])

    def test_a_contact_outside_the_bounds_moves_half_the_way_back(self):
        widths = np.array([0.0, 0.0, 10.0, 10.0])
        lo, hi = np.full(4, 4.0), np.full(4, 20.0)
        self.assertEqual(wcl.width_shifts(widths, lo, hi, [(0, 1), (2, 3)]), {0: 2.0})

    def test_the_feet_width_is_measured_across_the_hips(self):
        clip = loop_clip()
        w = wcl.feet_width(clip.worlds, clip.index)
        self.assertEqual(w.shape, (clip.F,))


class Hinge(unittest.TestCase):
    def test_a_leg_bent_past_square_keeps_its_bones_roll_about_the_knee(self):
        # hip, knee forward, ankle under and behind the knee: the calf bent past square to the hip-ankle line - the
        # pose the old least turn flipped half a turn
        raw = tiled(strides=1, before=0)
        w = raw.worlds[:, 0].copy()
        ix = raw.index
        th, ca, fo = ix["thigh_l"], ix["calf_l"], ix["foot_l"]

        def hinge_in(bone, ws):
            h, k, a = ws[th, 3, :3], ws[ca, 3, :3], ws[fo, 3, :3]
            n = ss._unit(np.cross(h - k, a - k))
            return n @ ss.orthonormal(ws[bone]).T
        before = [hinge_in(b, w) for b in (th, ca)]
        hip = w[th, 3, :3]
        l1 = np.linalg.norm(w[ca, 3, :3] - hip)
        target = np.array(w[fo])
        target[3, :3] = hip + np.array([0.0, -0.45 * l1, -0.2 * l1])        # a deep bend: calf past square
        short = wcl._leg_fix(raw, w, target, "l", 0.999)
        self.assertLess(short, 1e-9)
        for b, was in zip((th, ca), before):
            now = hinge_in(b, w)
            self.assertGreater(float(np.dot(now, was)), math.cos(math.radians(1.0)))

    def test_the_thighs_hinge_gives_back_the_side_the_knee_bends_to(self):
        clip = loop_clip()
        n = wcl.thigh_hinge(clip, clip.worlds, "l", least=1.0)
        self.assertIsNotNone(n)
        ix = clip.index
        for f in range(0, clip.F, 5):
            h, k, a = (clip.worlds[ix["%s_l" % b], f, 3, :3] for b in ("thigh", "calf", "foot"))
            e = ss._unit(a - h)
            if np.linalg.norm(np.cross(k - h, e)) < 1.0:
                continue
            bend = ss.bend_side(k - h, e)
            pref = ss.bend_side(np.cross(n @ ss.orthonormal(clip.worlds[ix["thigh_l"], f]), e), e)
            self.assertGreater(float(np.dot(bend, pref)), 0.9)


class Build(unittest.TestCase):
    def test_the_walks_own_values_give_the_clip_back_with_its_contacts(self):
        raw = tiled(before=8, after=8)
        loop = loop_clip()
        out, info = wcl.build(raw, loop, loop)
        np.testing.assert_allclose(out[:, :, 3, :3], raw.worlds[:, :, 3, :3], atol=1e-6)
        self.assertEqual(info["drop"], 0.0)

    def test_a_narrowed_walk_keeps_the_contacts_on_their_frames_and_the_feet_on_the_floor(self):
        raw = tiled(before=8, after=8)
        loop = loop_clip()
        narrowed = loop.worlds.copy()
        ix = loop.index
        for s, sign in (("l", -1.0), ("r", 1.0)):        # each foot 6 cm toward the middle, its leg by IK
            for f in range(loop.F):
                t = np.array(narrowed[ix["foot_" + s], f])
                t[3, 0] += sign * 6.0
                wcl._leg_fix(loop, narrowed[:, f], t, s, 1.0)
        out, info = wcl.build(raw, loop, ss.Clip(loop.names, loop.parents, narrowed, 30.0, "narrow"))
        a0 = ss.Analysis(raw)
        a1 = ss.Analysis(ss.Clip(raw.names, raw.parents, out, raw.fps, "out"))
        for s in ss.SIDES:
            self.assertEqual([tuple(c) for c in a1.feet[s]["contacts"]], [tuple(c) for c in a0.feet[s]["contacts"]])
            fo = raw.index["foot_" + s]
            for c0, c1 in a0.feet[s]["contacts"]:
                np.testing.assert_allclose(out[fo, c0:c1 + 1, 3, 1], raw.worlds[fo, c0:c1 + 1, 3, 1], atol=1e-6)
        width = wcl.feet_width(out, raw.index)
        self.assertGreaterEqual(width.min(), min(wcl.feet_width(raw.worlds, raw.index).min(), wcl.WIDTH_LEAST) - 0.5)


if __name__ == "__main__":
    unittest.main()

"""Where the leg bends when it goes dead STRAIGHT. The clean's smoothing straightens the clip's leg wherever the
smoothed hip cannot reach the ankle it keeps - its knee exactly on its hip-ankle line, which a captured cycle's
own never is (the animator's read 1.95 cm at its least raw and 0.0000 cm cleaned) - and the model's result is
straight there too. Reading the leg's plane per instant then reads rounding:

  * the model's own `_leg` read it from the source clip and flipped ~180 deg a frame, rolling the thigh and the
    calf (fixed 1432379f, model._knee_planes);
  * `target._leg` read it from the model's RESULT, which the transfer rebuilds with the target's own rest
    lengths - 0.0001 to 0.07 cm is left of the offset and its direction is float cancellation. Measured
    2026-10-30 on the animator's cycle (port 7006): it turned 160-170 deg a frame on their left leg and their
    left thigh's turn accelerated 11.8 deg a frame against the clip's own 5.4, its calf twisting 21.8 against
    15.4; the right leg's noise reached 51 deg and stayed under the clip's, which is the asymmetry they saw.

mayapy: target.py needs OpenMaya."""

import math
import unittest

import numpy as np
import maya.api.OpenMaya as om

from tests.test_walkmodel import clip, wm
from tests.test_walktarget import statics_of, target_of

wt = __import__("maya_walk.target", fromlist=["target"])

STRAIGHT = (6, 7, 8)        # the frames the fixture straightens (mid-cycle: the seam is left alone)
SIDE = "l"
BONES = ("thigh", "calf", "foot")


def _unit(v):
    return np.asarray(v, float) / max(float(np.linalg.norm(v)), 1e-12)


def _least_turn(u0, u1):
    """The least rotation taking direction u0 onto u1 (row-vector)."""
    u0, u1 = _unit(u0), _unit(u1)
    axis = np.cross(u0, u1)
    s, c = float(np.linalg.norm(axis)), float(np.dot(u0, u1))
    if s < 1e-12:
        return np.eye(3) if c > 0.0 else -np.eye(3)
    return wm.exp_rot(_unit(axis) * math.atan2(s, c))


def _between(a, b):
    """The angle between two rotations (deg)."""
    return math.degrees(float(np.linalg.norm(wm.log_rot(wm.orthonormal(np.linalg.inv(a[:3, :3]) @ b[:3, :3])))))


def straightened(c, side=SIDE, frames=STRAIGHT):
    """`c` with its leg dead straight on `frames`: the knee moved onto the hip-ankle line at the thigh's own
    length, the hip and the ankle kept, the bones turned the least - what the clean's _keep_feet leaves where
    the smoothed hip cannot reach the ankle it keeps."""
    worlds = c.worlds.copy()
    index = dict((n, j) for j, n in enumerate(c.names))
    th, ca, fo = (index["%s_%s" % (b, side)] for b in BONES)
    for f in frames:
        hip, knee, ankle = (worlds[j, f, 3, :3].copy() for j in (th, ca, fo))
        e = _unit(ankle - hip)
        new_knee = hip + float(np.linalg.norm(knee - hip)) * e
        worlds[th, f, :3, :3] = worlds[th, f, :3, :3] @ _least_turn(knee - hip, new_knee - hip)
        worlds[ca, f, :3, :3] = worlds[ca, f, :3, :3] @ _least_turn(ankle - knee, ankle - new_knee)
        worlds[ca, f, 3, :3] = new_knee
    return wm.Clip(c.names, c.parents, worlds, c.fps, c.up, c.name)


def knee_offsets(positions):
    """How far the knee stands off its hip-ankle line, a frame (cm)."""
    out = []
    for hip, knee, ankle in zip(*positions):
        e = _unit(ankle - hip)
        out.append(float(np.linalg.norm((knee - hip) - np.dot(knee - hip, e) * e)))
    return out


def twists(mats, child):
    """Each frame-to-frame turn's twist about the bone's own direction (deg), over a periodic series."""
    n = len(mats) - 1
    out = []
    for i in range(n):
        inv = np.linalg.inv(mats[i])
        axis = (np.append(child[i][3, :3], 1.0) @ inv)[:3]
        w = wm.log_rot(wm.orthonormal((inv @ mats[(i + 1) % n])[:3, :3]))
        angle = float(np.linalg.norm(w))
        if np.linalg.norm(axis) < 1e-9 or angle < 1e-12:
            out.append(0.0)
            continue
        out.append(math.degrees(2.0 * math.atan2(math.sin(angle / 2.0) * float(np.dot(_unit(w), _unit(axis))),
                                                 math.cos(angle / 2.0))))
    return out


def jumps(mats):
    """How far the bone's pivot moves a frame (cm), over a periodic series."""
    n = len(mats) - 1
    return [float(np.linalg.norm(mats[(i + 1) % n][3, :3] - mats[i][3, :3])) for i in range(n)]


def clip_series(c, side=SIDE):
    index = dict((n, j) for j, n in enumerate(c.names))
    return dict((b, [np.array(c.worlds[index["%s_%s" % (b, side)], f]) for f in range(c.worlds.shape[1])])
                for b in BONES)


def model_series(walk, result, side=SIDE):
    return dict((b, [np.array(result.worlds[walk.index["%s_%s" % (b, side)], f]) for f in range(result.frames + 1)])
                for b in BONES)


def target_series(rt, frames, side=SIDE):
    return dict((b, [wt._np(fr[leaf]) for fr in frames]) for b, leaf in zip(BONES, rt.legs[side]))


def positions(series):
    return [[m[3, :3] for m in series[b]] for b in BONES]


class Fixture(unittest.TestCase):
    """A base that straightens the walker's leg and transfers it, as Retarget.frames does."""

    def setUp(self):
        self.c = straightened(clip())
        self.walk = wm.analyse(self.c)
        self.rt = wt.Retarget(self.walk, statics_of(self.c), target_of(self.c))
        self.result = self.walk.evaluate(self.walk.own_knobs())

    def outs(self):
        """The transferred frames, as Retarget.frames builds them."""
        rt, result = self.rt, self.result
        first = rt._bones(result.worlds[:, 0])
        out = []
        for f in range(result.frames + 1):
            src = rt._bones(result.worlds[:, f])
            out.append(rt.transfer.frame(source=src, target=rt.target,
                                         root_world=rt.transfer.travel(src, first) * rt.place))
        return out


class FixtureTests(Fixture):
    """The fixture must really take the plane away, or every test below passes for nothing."""

    def test_the_raw_clip_always_has_a_plane_and_the_straightened_one_does_not(self):
        self.assertGreater(min(knee_offsets(positions(clip_series(clip())))), wm.KNEE_PLANE_MIN)
        offs = knee_offsets(positions(clip_series(self.c)))
        for f in STRAIGHT:
            self.assertAlmostEqual(offs[f], 0.0, places=9)
        self.assertGreater(min(o for f, o in enumerate(offs) if f not in STRAIGHT), wm.KNEE_PLANE_MIN)

    def test_straightening_keeps_the_hip_the_ankle_and_the_thigh(self):
        raw, bent = clip_series(clip()), clip_series(self.c)
        for f in STRAIGHT:
            self.assertLess(float(np.abs(bent["thigh"][f] - raw["thigh"][f])[3, :3].max()), 1e-9)
            self.assertLess(float(np.abs(bent["foot"][f] - raw["foot"][f]).max()), 1e-9)
            self.assertAlmostEqual(float(np.linalg.norm(bent["calf"][f][3, :3] - bent["thigh"][f][3, :3])),
                                   float(np.linalg.norm(raw["calf"][f][3, :3] - raw["thigh"][f][3, :3])), places=9)

    def test_the_model_s_result_leg_is_straight_there_too(self):
        """Why the target needs the plane at all: its own bend input has none either."""
        offs = knee_offsets(positions(model_series(self.walk, self.result)))
        for f in STRAIGHT:
            self.assertLess(offs[f], wm.KNEE_PLANE_MIN)


class ModelTests(Fixture):
    """model._knee_planes (1432379f) - the same reading one layer up, which had no test of its own."""

    def test_the_model_turns_the_leg_no_harder_than_the_straightened_clip(self):
        src, mdl = clip_series(self.c), model_series(self.walk, self.result)
        for bone, child in (("thigh", "calf"), ("calf", "foot")):
            own = max(np.abs(twists(src[bone], src[child])))
            got = max(np.abs(twists(mdl[bone], mdl[child])))
            self.assertLessEqual(got, own + 1.0, "%s: %.1f deg a frame against the clip's %.1f" % (bone, got, own))


class PlaneTests(Fixture):
    """Retarget._knee_planes: the cycle's own plane, filled across the frames that have none."""

    def test_the_plane_turns_little_from_one_frame_to_the_next(self):
        dirs = self.rt._knee_planes(self.outs())[SIDE]
        self.assertIsNotNone(dirs)
        turns = [math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(dirs[f], dirs[(f + 1) % len(dirs)]))))))
                 for f in range(len(dirs))]
        self.assertLess(max(turns), 30.0, "the plane turns %.1f deg a frame" % max(turns))

    def test_a_leg_that_is_never_bent_has_no_plane(self):
        self.assertIsNone(self.rt._knee_planes(self.outs(), least=1e6)[SIDE])

    def test_the_frames_that_have_one_keep_their_own(self):
        outs = self.outs()
        dirs = self.rt._knee_planes(outs)[SIDE]
        th, ca, fo = self.rt.legs[SIDE]
        for f in (0, 3, 12, 20):
            hip, knee, ankle = (wt._np(outs[f][leaf])[3, :3] for leaf in (th, ca, fo))
            e = _unit(ankle - hip)
            own = _unit((knee - hip) - np.dot(knee - hip, e) * e)
            self.assertGreater(float(np.dot(own, _unit(dirs[f] @ wt._rot(outs[f][th])))), 0.999, f)

    def test_frames_reads_the_cycle_s_planes_once(self):
        self.assertIsNone(self.rt.planes)
        self.rt.frames(self.result)
        self.assertEqual(sorted(self.rt.planes), ["l", "r"])
        self.assertEqual(self.rt.planes[SIDE].shape, (self.result.frames, 3))


class BendInputTests(Fixture):
    """The measured condition: at a straight frame the transferred knee is a HAIR off its line (0.0001 to
    0.07 cm) and points anywhere. What it costs, measured on the animator's cycle: the solved knee stood on the
    other side of the leg - 10.24 cm away at their frame 88 - and the thigh turned 13.56 deg with it."""

    def _solve_leg(self, out, f, reach=0.97):
        """(thigh, calf) as _leg solves them at frame `f`, the thigh's parent unmoved and the foot's goal
        `reach` of the way to it - the mapped foot a drop puts within reach, so the leg really bends (the
        animator's solved knee stood 3.7 to 8.2 cm off its line)."""
        th, ca, fo = self.rt.legs[SIDE]
        parent = self.rt.target[th].get("parent")
        final = {parent: om.MMatrix(out[parent])}
        hip, ankle = (wt._np(out[leaf])[3, :3] for leaf in (th, fo))
        self.rt._leg(SIDE, out, final, hip + (ankle - hip) * reach, f)
        return wt._np(final[th]), wt._np(final[ca])

    def _moved_knee(self, out, along, off):
        """`out` with its knee `off` cm off its hip-ankle line along `along`."""
        ca = self.rt.legs[SIDE][1]
        m = wt._np(out[ca]).copy()
        m[3, :3] = m[3, :3] + _unit(along) * off
        return dict(out, **{ca: wt._om(m)})

    def _plane_at(self, outs, f):
        """The cycle's own plane at frame `f`, in the world."""
        th, ca, fo = self.rt.legs[SIDE]
        hip, ankle = (wt._np(outs[f][leaf])[3, :3] for leaf in (th, fo))
        return self.rt._plane(SIDE, f, outs[f], _unit(ankle - hip))

    def _knee_side(self, solved, out):
        """The solved knee's offset from the hip-ankle line (a vector)."""
        th, ca, fo = self.rt.legs[SIDE]
        hip, ankle = (wt._np(out[leaf])[3, :3] for leaf in (th, fo))
        e = _unit(ankle - hip)
        knee = solved[1][3, :3]
        return (knee - hip) - np.dot(knee - hip, e) * e

    def test_the_solved_knee_stands_in_the_cycle_s_plane_not_in_a_hair_of_noise(self):
        outs = self.outs()
        self.rt.planes = self.rt._knee_planes(outs)
        f = STRAIGHT[1]
        plane = self._plane_at(outs, f)
        self.assertIsNotNone(plane)
        against = self._moved_knee(outs[f], -plane, 0.02)       # a hair the other way, as the noise does
        offset = self._knee_side(self._solve_leg(against, f), against)
        self.assertGreater(float(np.linalg.norm(offset)), 1.0)  # the leg really bends
        self.assertGreater(float(np.dot(_unit(offset), plane)), 0.99,
                           "the knee bent %.0f deg away from the cycle's plane"
                           % math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(_unit(offset), plane)))))))

    def test_a_hair_either_way_moves_nothing(self):
        outs = self.outs()
        self.rt.planes = self.rt._knee_planes(outs)
        f = STRAIGHT[1]
        plane = self._plane_at(outs, f)
        one = self._solve_leg(self._moved_knee(outs[f], plane, 0.02), f)
        other = self._solve_leg(self._moved_knee(outs[f], -plane, 0.02), f)
        moved = float(np.linalg.norm(one[1][3, :3] - other[1][3, :3]))
        self.assertLess(moved, 1e-6, "the knee moves %.3f cm on a hair" % moved)
        # not zero: `align` carries the transferred leg's own frame, and the hair is in it (0.02 cm on a 48 cm
        # thigh is 0.024 deg); what must not follow the hair is where the leg BENDS
        self.assertLess(_between(one[0], other[0]), 0.5)

    def test_without_the_cycle_s_plane_a_hair_swings_the_knee_across_the_leg(self):
        """The control - what the reading costs, and the path a leg that is never bent enough still takes."""
        outs = self.outs()
        f = STRAIGHT[1]
        self.rt.planes = self.rt._knee_planes(outs)
        plane = self._plane_at(outs, f)             # only to aim the hair; the solve gets no planes
        self.rt.planes = None
        one = self._solve_leg(self._moved_knee(outs[f], plane, 0.02), f)
        other = self._solve_leg(self._moved_knee(outs[f], -plane, 0.02), f)
        moved = float(np.linalg.norm(one[1][3, :3] - other[1][3, :3]))
        self.assertGreater(moved, 5.0, "the knee moves %.3f cm on a hair" % moved)

    def test_the_frames_that_have_a_plane_follow_their_own_knee(self):
        """The reading is not simply ignored: a cycle bent the other way bends the other way."""
        outs = self.outs()
        f = 12                                      # a frame whose leg really is bent
        self.rt.planes = self.rt._knee_planes(outs)
        plane = self._plane_at(outs, f)
        mirrored = []
        for out in outs:
            th, ca, fo = self.rt.legs[SIDE]
            hip, knee, ankle = (wt._np(out[leaf])[3, :3] for leaf in (th, ca, fo))
            e = _unit(ankle - hip)
            b = (knee - hip) - np.dot(knee - hip, e) * e
            m = wt._np(out[ca]).copy()
            m[3, :3] = knee - 2.0 * b               # the knee across the leg, the whole cycle
            mirrored.append(dict(out, **{ca: wt._om(m)}))
        self.rt.planes = self.rt._knee_planes(mirrored)
        offset = self._knee_side(self._solve_leg(mirrored[f], f), mirrored[f])
        self.assertLess(float(np.dot(_unit(offset), plane)), -0.99)


class TargetTests(Fixture):
    """End to end, onto the walker itself."""

    def setUp(self):
        Fixture.setUp(self)
        self.frames, self.info = self.rt.frames(self.result)

    def test_the_target_turns_the_leg_no_harder_than_the_clip(self):
        src, tgt = clip_series(self.c), target_series(self.rt, self.frames)
        for bone, child in (("thigh", "calf"), ("calf", "foot")):
            own = max(np.abs(twists(src[bone], src[child])))
            got = max(np.abs(twists(tgt[bone], tgt[child])))
            self.assertLessEqual(got, own + 1.0, "%s: %.1f deg a frame against the clip's %.1f" % (bone, got, own))

    def test_the_target_s_knee_does_not_swing_round_the_leg(self):
        src, tgt = clip_series(self.c), target_series(self.rt, self.frames)
        own, got = max(jumps(src["calf"])), max(jumps(tgt["calf"]))
        self.assertLessEqual(got, own + 0.5, "the knee moves %.2f cm a frame against the clip's %.2f" % (got, own))

    def test_the_feet_stay_where_the_clip_steps(self):
        src, tgt = clip_series(self.c), target_series(self.rt, self.frames)
        for f in range(len(tgt["foot"])):
            self.assertLess(float(np.abs(tgt["foot"][f] - src["foot"][f]).max()), 1e-6, f)


if __name__ == "__main__":
    unittest.main()

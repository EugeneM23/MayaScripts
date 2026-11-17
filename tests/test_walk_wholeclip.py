"""maya_walk.wholeclip: Walk Builder on a whole clip - a standing start, three strides of a loop, a stop. The
synthetic walker of test_walkmodel, tiled; the walk's "result" a changed copy of the loop. Runs under mayapy."""
import unittest

import numpy as np

from maya_startstop import model as ss
from maya_walk import wholeclip as wcl
from tests.test_walkmodel import synthetic, rot_y

P = 24
TRAVEL = 120.0


def loop_clip(worlds=None):
    names, parents, w = synthetic(P=P, travel=TRAVEL)
    return ss.Clip(names, parents, w if worlds is None else worlds, 30.0, "loop")


def tiled(strides=3, before=12, after=0):
    """A clip: `before` frames standing on the loop's first frame, `strides` strides of the loop, `after` frames
    standing on its last."""
    names, parents, w = synthetic(P=P, travel=TRAVEL)
    frames = []
    for f in range(before):
        frames.append(w[:, 0])
    for k in range(strides):
        for f in range(P):
            m = w[:, f].copy()
            m[:, 3, 2] += k * TRAVEL
            frames.append(m)
    end = w[:, P].copy()
    end[:, 3, 2] += (strides - 1) * TRAVEL
    frames.append(end)
    for f in range(after):
        frames.append(end)
    return ss.Clip(names, parents, np.stack(frames, axis=1), 30.0, "raw")


def turned(clip, name, deg):
    """The clip with `name` turned `deg` about up in its own frame, its children carried."""
    w = clip.worlds.copy()
    j = clip.index[name]
    for f in range(clip.F):
        before = w[:, f].copy()
        new = before[j].copy()
        new[:3, :3] = rot_y(deg) @ before[j][:3, :3]
        changed = {j: new}
        for i in clip.order:
            q = clip.parents[i]
            if i != j and q in changed:
                changed[i] = before[i] @ np.linalg.inv(before[q]) @ changed[q]
        for i, m in changed.items():
            w[i, f] = m
    return ss.Clip(clip.names, clip.parents, w, clip.fps, clip.name)


def local_rot(clip_worlds, clip, name, f):
    j = clip.index[name]
    q = clip.parents[j]
    r = ss.orthonormal(clip_worlds[j, f])
    return r @ ss.orthonormal(clip_worlds[q, f]).T


class Phases(unittest.TestCase):
    def test_the_walking_strides_and_the_parts(self):
        raw = tiled()
        loop = loop_clip()
        out, info = wcl.build(raw, loop, loop)
        self.assertGreaterEqual(len(info["walking"]), 1)
        self.assertIsNotNone(info["start"])
        self.assertIn("start 0-", wcl.line(info))

    def test_a_clip_with_no_stride_is_refused(self):
        names, parents, w = synthetic(P=P, travel=TRAVEL)
        still = ss.Clip(names, parents, np.repeat(w[:, :1], 40, axis=1), 30.0, "still")
        with self.assertRaises(wcl.Refusal):
            wcl.build(still, loop_clip(), loop_clip())


class Difference(unittest.TestCase):
    def test_the_walks_own_values_give_the_clip_back(self):
        raw = tiled()
        loop = loop_clip()
        out, _info = wcl.build(raw, loop, loop)
        np.testing.assert_allclose(out[:, :, 3, :3], raw.worlds[:, :, 3, :3], atol=1e-6)
        np.testing.assert_allclose(out[:, :, :3, :3], raw.worlds[:, :, :3, :3], atol=1e-6)

    def test_a_change_to_the_loop_reaches_every_walking_frame(self):
        raw = tiled()
        loop = loop_clip()
        result = turned(loop, "upperarm_l", 20.0)
        out, info = wcl.build(raw, loop, result)
        cycle = ss.Cycle(result)
        for t0, t1 in info["walking"]:
            for f in range(t0, t1):
                want = local_rot(cycle.sample(info["phases"][f])[:, None], result, "upperarm_l", 0)
                got = local_rot(out, raw, "upperarm_l", f)
                np.testing.assert_allclose(got, want, atol=1e-6)

    def test_the_change_is_laid_over_the_clips_own_frame(self):
        raw = tiled()
        loop = loop_clip()
        out, info = wcl.build(raw, loop, turned(loop, "upperarm_l", 20.0))
        f = info["walking"][0][0] + 3
        before = local_rot(raw.worlds, raw, "upperarm_l", f)
        after = local_rot(out, raw, "upperarm_l", f)
        angle = np.degrees(np.arccos(np.clip((np.trace(after @ before.T) - 1) / 2, -1, 1)))
        self.assertAlmostEqual(angle, 20.0, places=4)


class Legs(unittest.TestCase):
    def test_a_lower_pelvis_keeps_the_planted_feet_and_the_bone_lengths(self):
        raw = tiled()
        loop = loop_clip()
        lowered = loop.worlds.copy()
        pelvis = loop.index["pelvis"]
        under = wcl._under(loop, pelvis)
        lowered[under, :, 3, 1] -= 4.0
        out, info = wcl.build(raw, loop, ss.Clip(loop.names, loop.parents, lowered, 30.0, "low"))
        a = ss.Analysis(raw)
        for s in ss.SIDES:
            fo = raw.index["foot_" + s]
            for c0, c1 in a.feet[s]["contacts"]:
                for f in range(c0 + 1, c1 + 1):
                    moved = np.linalg.norm(out[fo, f, 3, :3] - out[fo, f - 1, 3, :3])
                    own = np.linalg.norm(raw.worlds[fo, f, 3, :3] - raw.worlds[fo, f - 1, 3, :3])
                    self.assertLess(moved - own, 1e-6)
        for j in range(raw.J):
            q = raw.parents[j]
            if q < 0 or raw.names[j].startswith(("ik_", "pelvis")):
                continue
            np.testing.assert_allclose(np.linalg.norm(out[j, :, 3, :3] - out[q, :, 3, :3], axis=1),
                                       np.linalg.norm(raw.worlds[j, :, 3, :3] - raw.worlds[q, :, 3, :3], axis=1),
                                       atol=1e-6, err_msg=raw.names[j])
        f = info["walking"][0][0] + 5
        self.assertLess(out[pelvis, f, 3, 1], raw.worlds[pelvis, f, 3, 1] - 3.0)


def gripped(loop):
    """The loop with its left hand held where it stands against the right one at frame 0, on every frame (a pose's
    two-handed grip in the walk's result)."""
    w = loop.worlds.copy()
    r, l = loop.index["hand_r"], loop.index["hand_l"]
    hold = w[l, 0] @ np.linalg.inv(w[r, 0])
    # a third of the way from the right hand to the left shoulder: 20 cm apart, and in the left arm's reach
    shoulder = loop.index["upperarm_l"]
    hold[3, :3] = 0.3 * np.mean([(w[shoulder, f] @ np.linalg.inv(w[r, f]))[3, :3] for f in range(w.shape[1])], axis=0)
    for f in range(w.shape[1]):
        short = wcl._limb_fix(loop, w[:, f], hold @ w[r, f], ["upperarm_l", "lowerarm_l", "hand_l"], 1.0)
        assert short < 1e-9, short
    return ss.Clip(loop.names, loop.parents, w, loop.fps, "gripped"), hold


class Grip(unittest.TestCase):
    def test_the_walks_grip_is_found_and_a_free_walk_has_none(self):
        loop = loop_clip()
        res, hold = gripped(loop)
        np.testing.assert_allclose(wcl.grip_hold(res, loop.index), wcl._rigid(hold), atol=1e-9)
        self.assertIsNone(wcl.grip_hold(loop, loop.index))

    def test_both_hands_hold_the_weapon_on_every_frame_of_the_clip(self):
        raw = tiled(before=12, after=8)
        loop = loop_clip()
        res, hold = gripped(loop)
        out, info = wcl.build(raw, loop, res)
        self.assertTrue(info["grip"])
        r, l = raw.index["hand_r"], raw.index["hand_l"]
        for f in range(raw.F):
            rel = wcl._rigid(out[l, f]) @ np.linalg.inv(wcl._rigid(out[r, f]))
            np.testing.assert_allclose(rel[3, :3], hold[3, :3], atol=1e-6 + info["grip_short"])
        for name in ("lowerarm_l", "hand_l", "lowerarm_r", "hand_r"):
            j = raw.index[name]
            q = raw.parents[j]
            np.testing.assert_allclose(np.linalg.norm(out[j, :, 3, :3] - out[q, :, 3, :3], axis=1),
                                       np.linalg.norm(raw.worlds[j, :, 3, :3] - raw.worlds[q, :, 3, :3], axis=1),
                                       atol=1e-6, err_msg=name)

    def test_the_weapon_rides_the_chest_as_the_walk_carries_it(self):
        raw = tiled(before=0, after=0)
        loop = loop_clip()
        res, _hold = gripped(loop)
        out, info = wcl.build(raw, loop, res)
        r, c = raw.index["hand_r"], raw.index["clavicle_r"]
        chest = raw.parents[c]
        rc = ss.Cycle(res)
        for f in range(info["walking"][0][0], info["walking"][-1][1]):
            R = rc.sample(info["phases"][f])
            want = (wcl._rigid(R[r]) @ np.linalg.inv(wcl._rigid(R[chest])))[3, :3]
            got = (wcl._rigid(out[r, f]) @ np.linalg.inv(wcl._rigid(out[chest, f])))[3, :3]
            np.testing.assert_allclose(got, want, atol=1e-4 + info["grip_short"])

    def test_a_clip_that_holds_its_own_grip_is_left_to_the_difference(self):
        loop, _hold = gripped(loop_clip())
        frames = []
        for k in range(3):                         # three strides of the held loop, standing first
            for f in range(P):
                m = loop.worlds[:, f].copy()
                m[:, 3, 2] += k * TRAVEL
                frames.append(m)
        frames = [loop.worlds[:, 0]] * 12 + frames
        raw = ss.Clip(loop.names, loop.parents, np.stack(frames, axis=1), 30.0, "raw")
        out, info = wcl.build(raw, loop, loop)
        self.assertFalse(info["grip"])
        np.testing.assert_allclose(out[:, :, 3, :3], raw.worlds[:, :, 3, :3], atol=1e-4)

    def test_a_walk_with_no_grip_leaves_the_arms_alone(self):
        raw = tiled()
        loop = loop_clip()
        out, info = wcl.build(raw, loop, loop)
        self.assertFalse(info["grip"])
        np.testing.assert_allclose(out[raw.index["hand_l"]], raw.worlds[raw.index["hand_l"]], atol=1e-6)


if __name__ == "__main__":
    unittest.main()

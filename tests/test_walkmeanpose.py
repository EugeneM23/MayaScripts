"""The walk's mean pose and its correction (maya_walk.meanpose) on the synthetic walker: numpy only, no Maya."""

import math
import os
import shutil
import tempfile
import unittest

import numpy as np

from tests import test_walkmodel as base

wm = base.wm
mp = base.load("meanpose")


def turned_local(worlds, walk, name, turn):
    """A copy of the pose `worlds` ({name: 4x4}) with `name`'s local rotation turned by `turn` (row-vector, left:
    local' = turn . local) and everything under it carried along."""
    out = dict((n, np.array(m, float)) for n, m in worlds.items())
    j = walk.index[name]
    parent = walk.names[walk.parents[j]]
    local = out[name] @ np.linalg.inv(out[parent])
    new_local = wm.matrix(turn @ local[:3, :3], local[3, :3])
    moved = new_local @ out[parent]
    carry = np.linalg.inv(out[name]) @ moved
    under = [walk.names[k] for k in mp._below(j, mp._children(walk.parents))]
    for n in under:
        out[n] = out[n] @ carry
    return out


def angle_deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


class FileTests(unittest.TestCase):

    def test_save_load_and_an_empty_correction_removes_the_file(self):
        folder = tempfile.mkdtemp()
        try:
            path = mp.path_for(os.path.join(folder, "asd.walk.gz"))
            self.assertTrue(path.endswith("asd.walkfix.json"))
            fix = mp.empty()
            fix["rot"]["spine_02"] = base.rot_x(10)
            fix["height"], fix["width"] = -3.0, 2.5
            fix["knee"]["l"], fix["toe"]["r"] = 0.2, -0.1
            mp.save(path, fix)
            back = mp.load(path)
            self.assertLess(float(np.abs(back["rot"]["spine_02"] - fix["rot"]["spine_02"]).max()), 1e-9)
            self.assertEqual((back["height"], back["width"], back["knee"]["l"], back["toe"]["r"]), (-3.0, 2.5, 0.2, -0.1))
            mp.save(path, mp.empty())
            self.assertFalse(os.path.exists(path))
            self.assertTrue(mp.is_empty(mp.load(path)))
        finally:
            shutil.rmtree(folder)


class MeanPoseTests(unittest.TestCase):

    def test_the_mean_pose_holds_every_bone_and_reads_no_change_against_itself(self):
        w = base.walk()
        pose = mp.mean_pose(w)
        self.assertEqual(sorted(pose), sorted(w.names))
        m = mp.measure(pose, w)
        fix, moved = mp.combine(mp.empty(), m, m)
        self.assertTrue(mp.is_empty(fix))
        self.assertEqual(moved, [])

    def test_the_mean_pose_stands_each_bone_on_its_local_means(self):
        w = base.walk()
        pose = mp.mean_pose(w)
        for name in ("spine_02", "upperarm_l", "head"):
            j = w.index[name]
            local = pose[name][:3, :3] @ pose[w.names[w.parents[j]]][:3, :3].T
            self.assertLess(angle_deg(local @ w.lmean[j].T), 1e-9)

    def test_the_legs_corrections_read_back_as_themselves(self):
        """What the rig shows for a correction (mean_pose) reads back, against the plain mean pose, as that very
        correction - the sign of every part, and the size."""
        w = base.walk()
        plain = mp.measure(mp.mean_pose(w), w)
        fix = mp.empty()
        fix["height"], fix["width"] = -4.0, 6.0
        fix["knee"] = {"l": math.radians(20.0), "r": math.radians(-12.0)}
        fix["toe"] = {"l": math.radians(15.0), "r": math.radians(-25.0)}
        shown = mp.measure(mp.mean_pose(w, fix), w)
        back, _ = mp.combine(mp.empty(), plain, shown)
        self.assertAlmostEqual(back["height"], -4.0, places=6)
        self.assertAlmostEqual(back["width"], 6.0, places=6)
        for key in ("knee", "toe"):
            for side in "lr":
                self.assertAlmostEqual(back[key][side], fix[key][side], places=5, msg=(key, side))
        self.assertEqual(back["rot"], {})


class CombineTests(unittest.TestCase):

    def test_a_bone_turned_on_the_rig_becomes_its_correction_and_turns_again_on_top(self):
        w = base.walk()
        pose = mp.mean_pose(w)
        m0 = mp.measure(pose, w)
        edited = turned_local(pose, w, "spine_02", base.rot_x(10))
        fix, moved = mp.combine(mp.empty(), m0, mp.measure(edited, w))
        self.assertEqual(sorted(fix["rot"]), ["spine_02"])
        self.assertLess(angle_deg(fix["rot"]["spine_02"] @ base.rot_x(10).T), 1e-6)
        self.assertEqual([(n, round(v, 3)) for n, v, _ in moved], [("spine_02", 10.0)])
        again = turned_local(edited, w, "spine_02", base.rot_y(5))
        fix2, _ = mp.combine(fix, mp.measure(edited, w), mp.measure(again, w))
        self.assertLess(angle_deg(fix2["rot"]["spine_02"] @ (base.rot_y(5) @ base.rot_x(10)).T), 1e-6)
        self.assertIn("spine_02 10.0 deg", mp.describe(moved))


class CorrectTests(unittest.TestCase):

    def test_no_turn_gives_the_clip_back(self):
        c = base.clip()
        self.assertIs(mp.correct(c, mp.empty()), c)

    def test_a_spine_turn_turns_the_walks_mean_and_keeps_its_motion(self):
        c, w = base.clip(), base.walk()
        fix = mp.empty()
        fix["rot"]["spine_02"] = base.rot_x(12)
        w2 = wm.analyse(mp.correct(c, fix))
        j = w.index["spine_02"]
        self.assertLess(angle_deg(w2.lmean[j] @ (base.rot_x(12) @ w.lmean[j]).T), 0.01)
        # the motion about the mean is the walk's: each frame's local against its mean
        self.assertLess(float(np.abs(w2.llog[j] - w.llog[j]).max()), 1e-3)
        # bones it does not hold keep their locals
        k = w.index["spine_01"]
        self.assertLess(angle_deg(w2.lmean[k] @ w.lmean[k].T), 1e-9)

    def test_a_pelvis_turn_keeps_the_feet_where_the_cycle_plants_them(self):
        c = base.clip()
        fix = mp.empty()
        fix["rot"]["pelvis"] = base.rot_x(10) @ base.rot_y(8)
        out = mp.correct(c, fix)
        idx = dict((n, j) for j, n in enumerate(c.names))
        for name in ("foot_l", "ball_l", "foot_r", "ball_r"):
            self.assertLess(float(np.abs(out.worlds[idx[name]] - c.worlds[idx[name]]).max()), 1e-6, name)
        # the legs keep their lengths, and the knee bends in the leg's plane
        for side in "lr":
            th, ca, fo = (idx["%s_%s" % (b, side)] for b in mp.LEGS)
            for j, k in ((th, ca), (ca, fo)):
                before = np.linalg.norm(c.worlds[k, :, 3, :3] - c.worlds[j, :, 3, :3], axis=1)
                after = np.linalg.norm(out.worlds[k, :, 3, :3] - out.worlds[j, :, 3, :3], axis=1)
                self.assertLess(float(np.abs(after - before).max()), 1e-6)
            # the thigh's frame still points down the bone the way it did (its X at the knee)
            u = out.worlds[ca, :, 3, :3] - out.worlds[th, :, 3, :3]
            x = out.worlds[th, :, 0, :3]
            cos = np.sum(u * x, axis=1) / np.linalg.norm(u, axis=1)
            self.assertGreater(float(cos.min()), 0.999)
        # a helper that followed the foot follows it still
        self.assertLess(float(np.abs(out.worlds[idx["ik_foot_l"]] - out.worlds[idx["foot_l"]]).max()), 1e-6)
        # and the corrected cycle is a walk the model reads
        w2 = wm.analyse(out)
        self.assertEqual(w2.P, 24)
        self.assertLess(float(np.abs(w2.evaluate(w2.own_knobs()).worlds - out.worlds).max()), 1e-4)

    def test_the_loop_stays_closed(self):
        c = base.clip()
        fix = mp.empty()
        fix["rot"]["upperarm_l"] = base.rot_z(20)
        fix["rot"]["pelvis"] = base.rot_z(6)
        out = mp.correct(c, fix)
        w2 = wm.analyse(out)              # refuses a cycle that does not close
        self.assertEqual(w2.P, 24)


class ModelFixTests(unittest.TestCase):

    def test_an_empty_fix_is_the_walk(self):
        w = base.walk()
        r = w.evaluate(w.own_knobs())
        self.assertLess(float(np.abs(r.worlds - base.clip().worlds).max()), 1e-6)

    def test_the_legs_fix_turns_the_knees_and_feet_and_moves_the_pelvis_and_the_width(self):
        w = base.walk()
        knobs = dict(w.own_knobs(), balance=0.0)
        plain = w.evaluate(knobs)
        w.fix = mp.model_fix({"height": -5.0, "width": 6.0, "knee": {"l": math.radians(20.0), "r": 0.0},
                              "toe": {"l": 0.0, "r": math.radians(-15.0)}})
        try:
            r = w.evaluate(knobs)
        finally:
            w.fix = mp.model_fix(mp.empty())
        pel = lambda res: base.positions(res, "pelvis", w) @ w.up
        self.assertAlmostEqual(float((pel(r) - pel(plain)).mean()), -5.0, delta=0.05)
        spread = lambda res: (base.positions(res, "foot_l", w) - base.positions(res, "foot_r", w)) @ w.side
        self.assertAlmostEqual(float((spread(r) - spread(plain)).mean()), 6.0, delta=0.3)
        f = 6
        d = base.knee_heading(r, w, "l", f) - base.knee_heading(plain, w, "l", f)
        self.assertAlmostEqual(d, 20.0, delta=1.0)
        g = 15                          # the right foot's stance (a swinging foot hangs in its shin)
        toe = lambda res: mp.heading(base.positions(res, "ball_r", w)[g] - base.positions(res, "foot_r", w)[g], w)
        self.assertAlmostEqual(math.degrees(toe(r) - toe(plain)), -15.0, delta=1.0)

    def test_a_pose_takes_the_knees_over_from_the_correction_at_its_share(self):
        w = base.walk()
        pose = base.a_pose(w)
        knobs = {"pose": 1.0}
        posed = w.evaluate(knobs, pose)
        w.fix = mp.model_fix({"height": 0.0, "width": 0.0, "knee": {"l": math.radians(25.0), "r": 0.0},
                              "toe": {"l": 0.0, "r": 0.0}})
        try:
            fixed = w.evaluate(knobs, pose)
        finally:
            w.fix = mp.model_fix(mp.empty())
        self.assertLess(float(np.abs(fixed.worlds - posed.worlds).max()), 1e-9)


class _Plug(object):
    def __init__(self, keyable, children=()):
        self.isKeyable = keyable
        self.isCompound = bool(children)
        self._children = list(children)

    def numChildren(self):
        return len(self._children)

    def child(self, i):
        return self._children[i]


class WatchTests(unittest.TestCase):

    def test_a_manipulators_compound_set_is_an_edit_a_marker_is_not(self):
        """The viewport's manipulators set `rotate` / `translate` whole, a compound that is never keyable itself
        (2026-10-15: a drag changed nothing while the Channel Box did)."""
        mr = base.load("meanrig")
        rotate = _Plug(False, [_Plug(True), _Plug(True), _Plug(True)])
        self.assertTrue(mr.watched(rotate))
        self.assertTrue(mr.watched(_Plug(True)))                       # rotateZ from the Channel Box
        self.assertFalse(mr.watched(_Plug(False)))                     # the marker string
        self.assertFalse(mr.watched(_Plug(False, [_Plug(False)])))     # parentMatrix and its like


if __name__ == "__main__":
    unittest.main()

"""The rig pose as a top layer (2026-11-02): the mean pose correction is the key poses' `cycle` entry, applied at
every frame of the evaluated animation, and the rig stands in the mean pose of what the walker shows.

The spec: docs/superpowers/specs/2026-11-02-walk-rig-pose-top-layer-design.md. The synthetic walker and the fake
scene are the existing harnesses (tests.test_walkmodel, tests.test_walk_meanrig).
"""

import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walk_keyposes import local_at, worlds_at
from tests.test_walk_meanrig import FakedTest, keyrig, meanrig

wm = T.wm
kp = T.load("keyposes")
mp = T.load("meanpose")


def moved_subtree(walk, worlds, name, delta):
    """`worlds` with the bone `name` and everything under it moved by `delta` (world)."""
    out = dict((n, np.array(m)) for n, m in worlds.items())
    kids = mp._children(walk.parents)
    for k in mp._below(walk.index[name], kids):
        out[walk.names[k]][3, :3] = out[walk.names[k]][3, :3] + np.asarray(delta, float)
    return out


def turned_subtree(walk, worlds, name, rot):
    """`worlds` with the bone `name` and everything under it turned by `rot` (world axes) about the bone."""
    out = dict((n, np.array(m)) for n, m in worlds.items())
    kids = mp._children(walk.parents)
    pivot = out[name][3, :3].copy()
    for k in mp._below(walk.index[name], kids):
        n = walk.names[k]
        out[n][:3, :3] = out[n][:3, :3] @ rot
        out[n][3, :3] = pivot + (out[n][3, :3] - pivot) @ rot
    return out


class CycleEntryTests(unittest.TestCase):
    """The whole-cycle entry in keyposes: constant, unmirrored, needing no steps."""

    def setUp(self):
        self.w = T.walk()
        self.steps = kp.find(self.w)

    @staticmethod
    def entry(rot=None, pelvis=None, knee=None, print_=None):
        out = kp.empty_key()
        out["rot"] = dict(rot or {})
        if pelvis is not None:
            out["pelvis"] = np.array(pelvis, float)
        for side, value in (knee or {}).items():
            out["knee"][side] = value
        for side, (t, yaw) in (print_ or {}).items():
            out["print"][side] = {"t": np.array(t, float), "yaw": yaw}
        return out

    def test_a_cycle_edit_is_the_same_turn_on_every_frame(self):
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(rot={"spine_02": Y})}, self.steps, self.w)
        for f in range(self.w.P):
            want = local_at(self.w.clip, self.w, "spine_02", f) @ Y
            self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", f), want, atol=1e-9), f)

    def test_a_cycle_edit_is_never_mirrored(self):
        """A mean-pose edit of the left arm holds the left arm the whole cycle: it does not swap sides on the
        other foot's step, the way a key pose's edit does."""
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(rot={"upperarm_l": Y})}, self.steps, self.w)
        for f in range(self.w.P):
            self.assertTrue(np.allclose(local_at(out, self.w, "upperarm_l", f),
                                        local_at(self.w.clip, self.w, "upperarm_l", f) @ Y, atol=1e-9), f)
            self.assertTrue(np.allclose(local_at(out, self.w, "upperarm_r", f),
                                        local_at(self.w.clip, self.w, "upperarm_r", f), atol=1e-9), f)

    def test_a_cycle_edit_needs_no_steps(self):
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(rot={"spine_02": Y})}, None, self.w)
        for f in (0, 7, 13):
            want = local_at(self.w.clip, self.w, "spine_02", f) @ Y
            self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", f), want, atol=1e-9), f)

    def test_no_cycle_edit_and_no_steps_gives_the_clip_back(self):
        clip = self.w.clip
        self.assertIs(kp.correct(clip, {"down": self.entry(pelvis=[0.0, 0.0, 3.0])}, None, self.w), clip)
        self.assertIs(kp.correct(clip, {kp.CYCLE: kp.empty_key()}, self.steps, self.w), clip)

    def test_a_cycle_pelvis_move_lifts_the_hips_on_every_frame_and_keeps_the_feet(self):
        up = np.asarray(self.w.up, float)
        out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(pelvis=[0.0, 0.0, 3.0])}, self.steps, self.w)
        before, after = self.w.clip.worlds, out.worlds
        pelvis, foot = self.w.index["pelvis"], self.w.index["foot_l"]
        for f in range(self.w.P):
            rose = float(np.dot(after[pelvis, f, 3, :3] - before[pelvis, f, 3, :3], up))
            self.assertAlmostEqual(rose, 3.0, places=6, msg=f)
            if max(kp.ground(self.w, "l", f)) > 0.5:
                self.assertLess(float(np.linalg.norm(after[foot, f, 3, :3] - before[foot, f, 3, :3])), 0.5, f)

    def test_a_cycle_edit_and_a_key_edit_stand_together(self):
        """A key pose's edit lands on top of a standing mean correction: exact at its key."""
        A = wm.exp_rot(np.array([0.0, 0.0, math.radians(10.0)]))
        B = wm.exp_rot(np.array([0.0, 0.0, math.radians(15.0)]))
        keys = {kp.CYCLE: self.entry(rot={"spine_02": A}), "passing": self.entry(rot={"spine_02": B})}
        out = kp.correct(self.w.clip, keys, self.steps, self.w)
        f = kp.frames_of(self.steps, self.w.P)["passing"]
        want = local_at(self.w.clip, self.w, "spine_02", f) @ wm.exp_rot(wm.log_rot(A) + wm.log_rot(B))
        self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", f), want, atol=1e-9))

    def test_the_file_carries_a_cycle_entry(self):
        keys = {kp.CYCLE: self.entry(pelvis=[0.0, 0.0, 3.0], knee={"l": 0.2})}
        back = kp.loads(kp.dumps(keys))
        self.assertIn(kp.CYCLE, back)
        self.assertTrue(np.allclose(back[kp.CYCLE]["pelvis"], [0.0, 0.0, 3.0]))
        self.assertAlmostEqual(back[kp.CYCLE]["knee"]["l"], 0.2)
        self.assertFalse(kp.is_empty(keys))

    def test_summary_names_the_keys_apart_from_the_mean_pose(self):
        keys = {kp.CYCLE: self.entry(pelvis=[0.0, 0.0, 3.0])}
        self.assertEqual(kp.summary(keys, only=kp.KEYS), "no key pose edited")
        self.assertIn("Mean pose", kp.summary(keys))

    def test_a_cycle_print_moves_the_foot_s_stances(self):
        out = kp.correct(self.w.clip, {kp.CYCLE: self.entry(print_={"l": ((4.0, 0.0, 0.0), 0.0)})},
                         self.steps, self.w)
        j = self.w.index["foot_l"]
        before, after = self.w.clip.worlds, out.worlds
        planted = [f for f in range(self.w.P) if max(kp.ground(self.w, "l", f)) > 0.9]
        for f in planted:
            self.assertGreater(float(np.linalg.norm(after[j, f, 3, :3] - before[j, f, 3, :3])), 1.0, f)
        k = self.w.index["foot_r"]
        for f in range(self.w.P):
            self.assertLess(float(np.linalg.norm(after[k, f, 3, :3] - before[k, f, 3, :3])), 0.5, f)

    def test_planted_reads_a_foot_s_move_as_its_print(self):
        """A mean pose has no foot in the air: its move along the ground is its print, whatever frame it is read
        at (frame 18 of the synthetic walker has foot_l in flight)."""
        base = kp.measure(worlds_at(self.w, 18), self.w)
        now = kp.measure(moved_subtree(self.w, worlds_at(self.w, 18), "foot_l", (4.0, 0.0, 0.0)), self.w)
        free = kp.increment(kp.CYCLE, base, now, self.w, 18)[0]
        planted = kp.increment(kp.CYCLE, base, now, self.w, 18, planted=True)[0]
        self.assertGreater(float(np.abs(free["foot"]["l"]["t"]).max()), 1.0)
        self.assertTrue(np.allclose(free["print"]["l"]["t"], 0.0))
        self.assertTrue(np.allclose(planted["foot"]["l"]["t"], 0.0))
        self.assertGreater(float(np.abs(planted["print"]["l"]["t"]).max()), 1.0)

    def test_one_foot_on_the_ground_does_not_make_the_other_read_planted(self):
        """Frame 5 of the synthetic walker has foot_l standing and foot_r in flight: the lift of the flying one is
        its own move, not a print refused as «a planted foot stays on the ground»."""
        base = kp.measure(worlds_at(self.w, 5), self.w)
        now = kp.measure(moved_subtree(self.w, worlds_at(self.w, 5), "foot_r", (0.0, 3.0, 0.0)), self.w)
        inc, moved, ignored = kp.increment("passing", base, now, self.w, 5)
        self.assertGreater(float(np.abs(inc["foot"]["r"]["t"]).max()), 1.0)
        self.assertEqual(ignored, [])

    def test_planted_reads_a_foot_s_turn_about_up_as_its_toe_out(self):
        up = np.asarray(self.w.up, float)
        rot = wm.exp_rot(up * math.radians(12.0))
        base = kp.measure(worlds_at(self.w, 18), self.w)
        now = kp.measure(turned_subtree(self.w, worlds_at(self.w, 18), "foot_l", rot), self.w)
        planted = kp.increment(kp.CYCLE, base, now, self.w, 18, planted=True)[0]
        self.assertAlmostEqual(math.degrees(planted["print"]["l"]["yaw"]), 12.0, places=3)
        self.assertTrue(np.allclose(planted["foot"]["l"]["r"], np.eye(3), atol=1e-6))

    def test_a_cycle_reading_lands_what_it_asked_on_every_frame(self):
        """The rig's own round trip: a 20 deg turn read off a pose and put in the cycle entry reaches the bone's
        local on every frame (the mean of locals right-multiplied by a constant is the mean times it)."""
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        before = mp.mean_pose(self.w)
        after = dict((n, np.array(m)) for n, m in before.items())
        kids = mp._children(self.w.parents)
        pivot = after["spine_02"][3, :3].copy()
        for k in mp._below(self.w.index["spine_02"], kids):
            n = self.w.names[k]
            after[n][:3, :3] = after[n][:3, :3] @ Y
            after[n][3, :3] = pivot + (after[n][3, :3] - pivot) @ Y
        inc = kp.increment(kp.CYCLE, kp.measure(before, self.w), kp.measure(after, self.w), self.w, 0,
                           planted=True)[0]
        out = kp.correct(self.w.clip, {kp.CYCLE: inc}, self.steps, self.w)
        mean = mp.mean_pose(wm.analyse(out))
        want = wm.orthonormal(after["spine_02"][:3, :3]) @ wm.orthonormal(after["spine_01"][:3, :3]).T
        got = wm.orthonormal(mean["spine_02"][:3, :3]) @ wm.orthonormal(mean["spine_01"][:3, :3]).T
        self.assertLess(math.degrees(float(np.linalg.norm(wm.log_rot(got.T @ want)))), 0.05)

    def test_on_result_gives_the_result_back_as_a_walk_when_its_steps_cannot_be_read(self):
        """A result whose key poses cannot be found still takes the cycle edit, and `rw` comes back for the rig
        pose to stand in."""
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        keys = {kp.CYCLE: self.entry(rot={"spine_02": Y})}
        saved = kp.find
        kp.find = lambda walk: (_ for _ in ()).throw(kp.Refusal("no steps here"))
        try:
            worlds, rw, steps, note = kp.on_result(self.w, self.w.clip.worlds, keys)
        finally:
            kp.find = saved
        self.assertIsNotNone(rw)
        self.assertIsNone(steps)
        self.assertIn("no steps here", note)
        out = wm.Clip(self.w.clip.names, self.w.clip.parents, worlds, self.w.clip.fps, self.w.clip.up, "out")
        want = local_at(self.w.clip, self.w, "spine_02", 0) @ Y
        self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", 0), want, atol=1e-9))


class ResetTests(FakedTest):
    """The two Resets stop sweeping each other's correction."""

    def entry(self, pelvis):
        out = kp.empty_key()
        out["pelvis"] = np.array(pelvis, float)
        return out

    def edits_with(self, root, **keys):
        edits = self.scene.walker_edits(root, "asd")[0]
        edits["keys"] = dict(keys)
        self.scene.set_edits(root, edits)

    def test_reset_key_poses_keeps_the_mean_pose_correction(self):
        root = self.walker(working=True)
        self.edits_with(root, **{kp.CYCLE: self.entry([0.0, 0.0, 3.0]), "down": self.entry([0.0, 0.0, 1.0])})
        line = keyrig.reset(root)
        keys = self.scene.edits[root]["keys"]
        self.assertIn(kp.CYCLE, keys)
        self.assertTrue(np.allclose(keys[kp.CYCLE]["pelvis"], [0.0, 0.0, 3.0]))
        self.assertNotIn("down", keys)
        self.assertIn("dropped", line)

    def test_reset_key_poses_with_only_a_mean_correction_says_nothing_was_edited(self):
        root = self.walker(working=True)
        self.edits_with(root, **{kp.CYCLE: self.entry([0.0, 0.0, 3.0])})
        line = keyrig.reset(root)
        self.assertIn("no key pose edited", line)
        self.assertIn(kp.CYCLE, self.scene.edits[root]["keys"])

    def test_reset_rig_pose_drops_the_mean_correction_and_keeps_the_keys(self):
        root = self.walker(working=True)
        self.edits_with(root, **{kp.CYCLE: self.entry([0.0, 0.0, 3.0]), "down": self.entry([0.0, 0.0, 1.0])})
        line = meanrig.reset(root)
        keys = self.scene.edits[root]["keys"]
        self.assertNotIn(kp.CYCLE, keys)
        self.assertIn("down", keys)
        self.assertIn("dropped", line)

    def test_reset_rig_pose_drops_an_old_correction_too(self):
        root = self.walker(working=True)
        edits = self.scene.walker_edits(root, "asd")[0]
        fix = mp.empty()
        fix["height"] = 3.0
        edits["fix"] = fix
        self.scene.set_edits(root, edits)
        meanrig.reset(root)
        self.assertTrue(mp.is_empty(self.scene.edits[root]["fix"]))


class RigPoseTests(FakedTest):
    """The rig stands in the mean pose of the result, and Update writes the cycle entry."""

    def setUp(self):
        FakedTest.setUp(self)
        self.root = self.walker(working=True)

    def local_of(self, ns, name):
        R = lambda n: wm.orthonormal(self.w.world_of(ns, n)[:3, :3])
        parent = self.w.statics[name]["parent"]
        return R(name) @ R(parent).T

    def correction(self, degrees=20.0, bone="spine_02"):
        """A standing cycle correction of `degrees` on `bone`, on the walker's edits."""
        entry = kp.empty_key()
        entry["rot"] = {bone: T.rot_x(degrees)}
        edits = self.scene.walker_edits(self.root, "asd")[0]
        edits["keys"] = {kp.CYCLE: entry}
        self.scene.set_edits(self.root, edits)

    def test_press_asks_for_the_animation_with_its_steps(self):
        meanrig.press(self.root)
        self.assertTrue(all(with_steps for _, with_steps in self.scene.anim_calls), self.scene.anim_calls)

    def test_the_rig_stands_in_the_mean_pose_of_the_result(self):
        """Not of the cycle: with a standing correction the two differ, and the rig shows the result's."""
        self.correction()
        meanrig.press(self.root)
        anim = self.scene.walker_animation(self.root)
        ns = meanrig.find(self.root).namespace
        want = mp.mean_pose(anim.rw)
        plain = mp.mean_pose(anim.walk)
        wanted = wm.orthonormal(want["spine_02"][:3, :3]) @ wm.orthonormal(want["spine_01"][:3, :3]).T
        plained = wm.orthonormal(plain["spine_02"][:3, :3]) @ wm.orthonormal(plain["spine_01"][:3, :3]).T
        got = self.local_of(ns, "spine_02")
        self.assertLess(math.degrees(float(np.linalg.norm(wm.log_rot(got.T @ wanted)))), 0.01)
        self.assertGreater(math.degrees(float(np.linalg.norm(wm.log_rot(got.T @ plained)))), 10.0)

    def test_update_writes_the_cycle_entry_and_not_the_old_correction(self):
        meanrig.press(self.root)
        rig = meanrig.find(self.root)
        self.w.turn(rig.namespace, "spine_02", T.rot_x(20))
        line = meanrig.update()
        keys = self.scene.edits[self.root]["keys"]
        self.assertIn(kp.CYCLE, keys)
        self.assertIn("spine_02", keys[kp.CYCLE]["rot"])
        turn = math.degrees(float(np.linalg.norm(wm.log_rot(keys[kp.CYCLE]["rot"]["spine_02"]))))
        self.assertAlmostEqual(turn, 20.0, places=2)
        self.assertTrue(mp.is_empty(self.scene.edits[self.root]["fix"]))
        self.assertIn("spine_02", line)

    def test_update_with_nothing_moved_writes_nothing(self):
        meanrig.press(self.root)
        self.scene.edit_calls = []
        line = meanrig.update()
        self.assertEqual(self.scene.edit_calls, [])
        self.assertEqual(line, meanrig.NOTHING_MOVED)

    def test_update_re_keys_the_walker_unrecorded(self):
        meanrig.press(self.root)
        rig = meanrig.find(self.root)
        self.w.turn(rig.namespace, "spine_02", T.rot_x(20))
        meanrig.update()
        self.assertTrue(self.scene.applied)
        self.assertFalse(self.scene.applied[-1]["record"])

    def test_a_second_update_adds_to_the_first(self):
        meanrig.press(self.root)
        rig = meanrig.find(self.root)
        self.w.turn(rig.namespace, "spine_02", T.rot_x(10))
        meanrig.update()
        self.w.turn(rig.namespace, "spine_02", T.rot_x(10))
        meanrig.update()
        entry = self.scene.edits[self.root]["keys"][kp.CYCLE]
        turn = math.degrees(float(np.linalg.norm(wm.log_rot(entry["rot"]["spine_02"]))))
        self.assertAlmostEqual(turn, 20.0, places=2)

    def test_a_lowered_pelvis_is_the_cycle_entry_s_own_move(self):
        meanrig.press(self.root)
        rig = meanrig.find(self.root)
        self.w.lower(rig.namespace, -3.0)
        line = meanrig.update()
        entry = self.scene.edits[self.root]["keys"][kp.CYCLE]
        up = np.asarray(self.scene.walker_animation(self.root).rw.up, float)
        basis = np.asarray(self.scene.walker_animation(self.root).rw.basis, float)
        self.assertAlmostEqual(float(np.asarray(entry["pelvis"], float) @ basis @ up), -3.0, places=4)
        self.assertIn("pelvis", line)

    def test_a_walker_whose_steps_cannot_be_read_still_takes_a_correction(self):
        self.scene.no_steps = "the key poses: no steps here"
        meanrig.press(self.root)
        rig = meanrig.find(self.root)
        self.w.turn(rig.namespace, "spine_02", T.rot_x(20))
        meanrig.update()
        self.assertIn(kp.CYCLE, self.scene.edits[self.root]["keys"])


if __name__ == "__main__":
    unittest.main()

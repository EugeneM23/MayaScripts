"""Walk Builder's key poses (maya_walk.keyposes) on the synthetic walker: numpy only, no Maya."""

import math
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
kp = T.load("keyposes")
mp = T.load("meanpose")


def worlds_at(walk, f):
    """{name: 4x4} - the walker's frame f."""
    return dict((n, np.array(walk.clip.worlds[j, f])) for j, n in enumerate(walk.names))


def turned_subtree(walk, worlds, name, rot):
    """`worlds` with the bone `name` and everything under it turned by `rot` (world axes) about the bone."""
    out = dict((n, np.array(m)) for n, m in worlds.items())
    kids = mp._children(walk.parents)
    j = walk.index[name]
    pivot = out[name][3, :3].copy()
    for k in mp._below(j, kids):
        n = walk.names[k]
        out[n][:3, :3] = out[n][:3, :3] @ rot
        out[n][3, :3] = pivot + (out[n][3, :3] - pivot) @ rot
    return out


def local_at(clip, walk, name, f):
    j = walk.index[name]
    p = walk.parents[j]
    R = clip.worlds[:, f, :3, :3]
    return wm.orthonormal(R[j]) @ wm.orthonormal(R[p]).T


def world_rot(clip, walk, name, f):
    return wm.orthonormal(clip.worlds[walk.index[name], f, :3, :3])


class PurityTests(unittest.TestCase):

    def test_imports_nothing_of_maya(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_walk.keyposes; "
                "print(sorted(k for k in sys.modules if k.startswith('maya') and not k.startswith('maya_')))"
                % T.PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


class FindTests(unittest.TestCase):

    def test_every_step_has_four_key_poses_in_order(self):
        w = T.walk()
        steps = kp.find(w)
        self.assertEqual([s["side"] for s in steps], ["r", "l"])
        for s in steps:
            frames = [s[k] for k in kp.KEYS] + [s["next"]]
            self.assertEqual(frames, sorted(set(frames)), s)
        self.assertEqual(kp.reference(steps)["side"], "l")
        ref = kp.frames_of(steps, w.P)
        self.assertEqual(ref["contact"], 23)
        self.assertTrue(all(0 <= ref[k] < w.P for k in kp.KEYS))

    def test_down_and_up_stand_inside_the_step(self):
        """Down and Up are poses of their own: never a frame beside the contact or the passing."""
        w = T.walk()
        for s in kp.find(w):
            self.assertGreaterEqual(s["down"] - s["contact"], 1)
            self.assertGreaterEqual(s["passing"] - s["down"], 1)
            self.assertGreaterEqual(s["up"] - s["passing"], 1)
            self.assertGreaterEqual(s["next"] - s["up"], 1)

    def test_a_walk_with_no_steps_is_refused(self):
        w = T.walk()
        w.placement_note = "the left foot never lifts"
        with self.assertRaises(kp.Refusal):
            kp.find(w)


class CorrectTests(unittest.TestCase):

    def setUp(self):
        self.w = T.walk()
        self.steps = kp.find(self.w)
        self.ref = kp.frames_of(self.steps, self.w.P)
        self.other = dict((k, [s for s in self.steps if s["side"] != kp.REF_SIDE][0][k] % self.w.P) for k in kp.KEYS)

    def edited(self, key, **parts):
        entry = kp.empty_key()
        for name, value in parts.items():
            if name == "rot":
                entry["rot"] = value
            elif name == "pelvis":
                entry["pelvis"] = np.array(value, float)
            elif name == "knee":
                entry["knee"].update(value)
            elif name == "foot":
                for side, (t, r) in value.items():
                    entry["foot"][side] = {"t": np.array(t, float), "r": r}
        return {key: entry}

    def test_no_edit_gives_the_clip_back(self):
        clip = self.w.clip
        self.assertIs(kp.correct(clip, {}, self.steps, self.w), clip)
        self.assertIs(kp.correct(clip, {"down": kp.empty_key()}, self.steps, self.w), clip)

    def test_an_edit_is_exact_at_its_key_and_none_at_the_others(self):
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(20.0)]))
        out = kp.correct(self.w.clip, self.edited("passing", rot={"spine_02": Y}), self.steps, self.w)
        f = self.ref["passing"]
        want = local_at(self.w.clip, self.w, "spine_02", f) @ Y
        self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", f), want, atol=1e-9))
        for key in ("contact", "down", "up"):
            for frame in (self.ref[key], self.other[key]):
                self.assertTrue(np.allclose(local_at(out, self.w, "spine_02", frame),
                                            local_at(self.w.clip, self.w, "spine_02", frame), atol=1e-9), (key, frame))

    def test_the_other_foot_s_step_takes_the_edit_mirrored(self):
        """The left arm turned at the left contact: the right arm turns as its mirror at the right contact."""
        Y = wm.exp_rot(np.array([math.radians(15.0), math.radians(10.0), 0.0]))
        out = kp.correct(self.w.clip, self.edited("contact", rot={"upperarm_l": Y}), self.steps, self.w)
        a, b = self.ref["contact"], self.other["contact"]
        Dl = world_rot(self.w.clip, self.w, "upperarm_l", a).T @ world_rot(out, self.w, "upperarm_l", a)
        Dr = world_rot(self.w.clip, self.w, "upperarm_r", b).T @ world_rot(out, self.w, "upperarm_r", b)
        M = kp.reflection(self.w)
        self.assertGreater(T.angle(Dl), 10.0)
        self.assertTrue(np.allclose(Dr, M @ Dl @ M, atol=1e-9))
        self.assertTrue(np.allclose(world_rot(out, self.w, "upperarm_r", a),
                                    world_rot(self.w.clip, self.w, "upperarm_r", a), atol=1e-9))

    def test_a_lowered_pelvis_keeps_the_feet_and_the_legs(self):
        out = kp.correct(self.w.clip, self.edited("down", pelvis=[0.0, 0.0, -3.0]), self.steps, self.w)
        idx = self.w.index
        f = self.ref["down"]
        rise = (out.worlds[idx["pelvis"], f, 3, :3] - self.w.clip.worlds[idx["pelvis"], f, 3, :3]) @ self.w.up
        self.assertAlmostEqual(float(rise), -3.0, places=6)
        for name in ("foot_l", "ball_l", "foot_r", "ball_r"):
            self.assertTrue(np.allclose(out.worlds[idx[name], :, 3, :3], self.w.clip.worlds[idx[name], :, 3, :3],
                                        atol=1e-9), name)
        for side in "lr":
            for a, b in (("thigh", "calf"), ("calf", "foot")):
                d0 = np.linalg.norm(self.w.clip.worlds[idx["%s_%s" % (a, side)], :, 3, :3]
                                    - self.w.clip.worlds[idx["%s_%s" % (b, side)], :, 3, :3], axis=1)
                d1 = np.linalg.norm(out.worlds[idx["%s_%s" % (a, side)], :, 3, :3]
                                    - out.worlds[idx["%s_%s" % (b, side)], :, 3, :3], axis=1)
                self.assertLess(float(np.abs(d1 - d0).max()), 1e-6, (side, a, b))
        self.assertTrue(np.allclose(out.worlds[:, -1, 3, :3] - out.worlds[:, 0, 3, :3],
                                    self.w.clip.worlds[:, -1, 3, :3] - self.w.clip.worlds[:, 0, 3, :3], atol=1e-9))

    def test_a_foot_in_the_air_moves_a_flat_one_does_not(self):
        idx = self.w.index
        f = self.ref["passing"]
        self.assertGreater(min(kp.ground(self.w, "l", f)), 0.5)            # the left foot stands flat
        self.assertLess(max(kp.ground(self.w, "r", f)), 0.5)               # the right one swings
        lift = {"r": ([0.0, 0.0, 4.0], np.eye(3)), "l": ([0.0, 0.0, 4.0], np.eye(3))}
        out = kp.correct(self.w.clip, self.edited("passing", foot=lift), self.steps, self.w)
        up = lambda clip, name, frame: float(clip.worlds[idx[name], frame, 3, :3] @ self.w.up)
        self.assertAlmostEqual(up(out, "foot_r", f) - up(self.w.clip, "foot_r", f), 4.0, places=6)
        self.assertAlmostEqual(up(out, "foot_l", f) - up(self.w.clip, "foot_l", f), 0.0, places=9)
        g = self.other["passing"]             # mirrored: the left foot swings at the right passing
        self.assertAlmostEqual(up(out, "foot_l", g) - up(self.w.clip, "foot_l", g), 4.0, places=6)

    def test_a_knee_turn_turns_the_knee_about_the_leg(self):
        idx = self.w.index
        f = self.ref["passing"]
        out = kp.correct(self.w.clip, self.edited("passing", knee={"r": math.radians(25.0)}), self.steps, self.w)
        old = tuple(self.w.clip.worlds[idx["%s_r" % b], f, 3, :3] for b in mp.LEGS)
        new = tuple(out.worlds[idx["%s_r" % b], f, 3, :3] for b in mp.LEGS)
        turn = mp.knee_turn((old[0], old[1] - old[0], old[2]), (new[0], new[1] - new[0], new[2]))
        self.assertAlmostEqual(math.degrees(turn), 25.0, places=4)


class CombineTests(unittest.TestCase):

    def test_a_rig_s_edit_read_back_lands_exactly_at_its_key(self):
        """The rig reads base, the animator turns the left arm 20 deg and lowers the pelvis 2 cm: the edit put in
        the cycle gives the rig's pose back at the key."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["down"]
        base = worlds_at(w, f)
        now = turned_subtree(w, base, "upperarm_l", wm.exp_rot(np.array([0.0, math.radians(20.0), 0.0])))
        keys, moved, ignored = kp.combine({}, "down", kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertEqual([m[0] for m in moved], ["upperarm_l"])
        self.assertAlmostEqual(moved[0][1], 20.0, places=6)
        self.assertEqual(ignored, [])
        out = kp.correct(w.clip, keys, steps, w)
        got = kp.measure(dict((n, np.array(out.worlds[j, f])) for j, n in enumerate(w.names)), w)
        want = kp.measure(now, w)
        for name in mp.upper_bones(w):
            self.assertTrue(np.allclose(got["local"][name], want["local"][name], atol=1e-9), name)

    def test_a_second_edit_adds_to_the_first(self):
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["up"]
        base = worlds_at(w, f)
        turn = wm.exp_rot(np.array([0.0, 0.0, math.radians(10.0)]))
        one = turned_subtree(w, base, "spine_02", turn)
        keys = kp.combine({}, "up", kp.measure(base, w), kp.measure(one, w), w, f)[0]
        two = turned_subtree(w, one, "spine_02", turn)
        keys = kp.combine(keys, "up", kp.measure(one, w), kp.measure(two, w), w, f)[0]
        self.assertAlmostEqual(T.angle(keys["up"]["rot"]["spine_02"]), 20.0, places=6)

    def test_a_flat_foot_s_move_is_not_taken_and_said(self):
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        for name in ("foot_l", "ball_l"):
            now[name][3, :3] = now[name][3, :3] + np.array([3.0, 0.0, 0.0])
        keys, moved, ignored = kp.combine({}, "passing", kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertTrue(kp.is_empty(keys))
        self.assertEqual(len(ignored), 1)
        self.assertIn("flat", ignored[0])

    def test_a_flat_foot_s_knee_stays_with_it_and_a_lowered_pelvis_reads_minus(self):
        """A foot planted flat moved on the rig, its knee following it: neither is taken (the knee only followed
        the foot). The pelvis lowered reads «pelvis -2.0 cm»."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        for name in ("foot_l", "ball_l"):
            now[name][3, :3] = now[name][3, :3] + np.array([4.0, 0.0, 0.0])
        now["calf_l"][3, :3] = now["calf_l"][3, :3] + np.array([6.0, 0.0, 0.0])
        kids = mp._children(w.parents)
        for k in mp._below(w.index["pelvis"], kids):
            if w.names[k] not in ("foot_l", "ball_l", "calf_l"):
                now[w.names[k]][3, :3] = now[w.names[k]][3, :3] - 2.0 * w.up
        keys, moved, ignored = kp.combine({}, "passing", kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertEqual(keys["passing"]["knee"]["l"], 0.0)
        self.assertTrue(any("foot_l stands flat" in text for text in ignored), ignored)
        pelvis = [m for m in moved if m[0] == "pelvis"]
        self.assertEqual(len(pelvis), 1)
        self.assertAlmostEqual(pelvis[0][1], -2.0, places=6)
        self.assertIn("pelvis -2.0 cm", kp.describe(moved))

    def test_the_pelvis_move_is_read_in_travel_coordinates(self):
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["up"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        kids = mp._children(w.parents)
        for k in mp._below(w.index["pelvis"], kids):
            now[w.names[k]][3, :3] = now[w.names[k]][3, :3] + 2.5 * w.up
        keys = kp.combine({}, "up", kp.measure(base, w), kp.measure(now, w), w, f)[0]
        self.assertTrue(np.allclose(keys["up"]["pelvis"], [0.0, 0.0, 2.5], atol=1e-9))


class FileTests(unittest.TestCase):

    def test_round_trip_and_an_empty_file_goes(self):
        folder = tempfile.mkdtemp()
        path = kp.path_for(os.path.join(folder, "asd.walk.gz"))
        self.assertTrue(path.endswith("asd" + kp.SUFFIX))
        keys = {"down": kp.empty_key()}
        keys["down"]["rot"]["spine_02"] = wm.exp_rot(np.array([0.1, 0.2, 0.3]))
        keys["down"]["pelvis"] = np.array([0.0, 1.0, -2.0])
        keys["down"]["knee"]["l"] = 0.25
        keys["down"]["foot"]["r"] = {"t": np.array([0.0, 0.0, 3.0]), "r": wm.exp_rot(np.array([0.2, 0.0, 0.0]))}
        kp.save(path, keys)
        back = kp.load(path)
        self.assertTrue(np.allclose(back["down"]["rot"]["spine_02"], keys["down"]["rot"]["spine_02"]))
        self.assertTrue(np.allclose(back["down"]["pelvis"], keys["down"]["pelvis"]))
        self.assertAlmostEqual(back["down"]["knee"]["l"], 0.25)
        self.assertTrue(np.allclose(back["down"]["foot"]["r"]["r"], keys["down"]["foot"]["r"]["r"]))
        self.assertEqual(kp.summary(back), "Down edited")
        kp.save(path, {"down": kp.empty_key()})
        self.assertFalse(os.path.exists(path))
        self.assertEqual(kp.load(path), {})


class MirrorTests(unittest.TestCase):

    def test_names(self):
        self.assertEqual(kp.mirror_name("upperarm_l"), "upperarm_r")
        self.assertEqual(kp.mirror_name("index_01_r"), "index_01_l")
        self.assertEqual(kp.mirror_name("spine_02"), "spine_02")

    def test_knots_are_four_a_step_in_order(self):
        w = T.walk()
        steps = kp.find(w)
        points = kp.knots({}, steps, w)
        self.assertEqual(len(points), 4 * len(steps))
        times = [t for t, _ in points]
        self.assertEqual(times, sorted(times))
        self.assertLess(times[-1] - times[0], w.P)


if __name__ == "__main__":
    unittest.main()

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

    def test_each_key_stands_in_its_own_quarter_of_the_step(self):
        """Four distinct poses, as the guide lays them out: Down near a quarter of the step, Passing near its
        middle, Up near three quarters - on a walk and on a run alike. A sprint read the raw events: its swinging
        foot passes the standing one right after the strike, so Contact, Down and Passing fell on three frames
        in a row and Up beside the next contact (2026-10-27, «по 2 одинаковые»)."""
        for kw in ({}, {"P": 28, "stance": 0.25, "lift": 30.0}, {"P": 16, "stance": 0.3, "lift": 30.0}):
            w = T.walk(**kw)
            for s in kp.find(w):
                span = s["next"] - s["contact"]
                band = span / 16.0 + 1.0
                for share, key in ((0.25, "down"), (0.5, "passing"), (0.75, "up")):
                    self.assertLessEqual(abs(s[key] - (s["contact"] + share * span)), band, (kw, key, s))

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

    def planted(self, w, side="l"):
        """A key frame of the reference step where `side`'s foot stands flat."""
        steps = kp.find(w)
        ref = kp.frames_of(steps, w.P)
        for key in kp.KEYS:
            heel, ball = kp.ground(w, side, ref[key])
            if heel > 0.5 and ball > 0.5:
                return steps, key, ref[key]
        self.fail("no key with the %s foot flat" % side)

    def test_a_planted_foot_s_move_is_its_print_for_the_whole_stance(self):
        """2026-10-27 («реагирует на изменения всех контроллеров»): a planted foot moved along the ground is where
        it stands for its whole stance - held still there (no slide), the other foot's stances mirrored; a lift
        is not taken, said."""
        w = T.walk()
        steps, key, f = self.planted(w)
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        move = 3.0 * np.asarray(w.fwd) + 2.0 * np.asarray(w.side) + 1.5 * np.asarray(w.up)
        for name in ("foot_l", "ball_l"):
            now[name][3, :3] = now[name][3, :3] + move
        keys, moved, ignored = kp.combine({}, key, kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertTrue(np.allclose(keys[key]["print"]["l"]["t"], [3.0, 2.0, 0.0], atol=1e-9))
        self.assertTrue(any("lifted 1.5 cm" in text for text in ignored), ignored)
        out = kp.correct(w.clip, keys, steps, w)
        weights = kp.stance_weights(w, "l", w.clip.worlds.shape[1])
        j = w.index["foot_l"]
        shift = 3.0 * np.asarray(w.fwd) + 2.0 * np.asarray(w.side)
        held = [g for g in range(w.P) if weights[g] >= 1.0]
        self.assertTrue(held)
        for g in held:
            self.assertTrue(np.allclose(out.worlds[j, g, 3, :3] - w.clip.worlds[j, g, 3, :3], shift, atol=1e-6), g)
        r = w.index["foot_r"]
        mirror = 3.0 * np.asarray(w.fwd) - 2.0 * np.asarray(w.side)
        for g in [g for g in range(w.P) if kp.stance_weights(w, "r", w.clip.worlds.shape[1])[g] >= 1.0]:
            self.assertTrue(np.allclose(out.worlds[r, g, 3, :3] - w.clip.worlds[r, g, 3, :3], mirror, atol=1e-6))
        for leg in ("thigh_l", "calf_l"):
            child = {"thigh_l": "calf_l", "calf_l": "foot_l"}[leg]
            lengths = np.linalg.norm(out.worlds[w.index[child], :, 3, :3] - out.worlds[w.index[leg], :, 3, :3], axis=1)
            self.assertLess(float(np.ptp(lengths)), 1e-6)

    def test_a_flat_foot_turned_about_up_is_its_toe_out_a_tilt_is_not(self):
        w = T.walk()
        steps, key, f = self.planted(w)
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        pivot = now["foot_l"][3, :3].copy()
        turn = wm.exp_rot(math.radians(12.0) * np.asarray(w.up)) @ wm.exp_rot(math.radians(5.0) * np.asarray(w.fwd))
        for name in ("foot_l", "ball_l"):
            now[name][:3, :3] = now[name][:3, :3] @ turn
            now[name][3, :3] = pivot + (now[name][3, :3] - pivot) @ turn
        keys, moved, ignored = kp.combine({}, key, kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertAlmostEqual(math.degrees(keys[key]["print"]["l"]["yaw"]), 12.0, delta=0.6)
        self.assertTrue(any("tilted" in text for text in ignored), ignored)

    def test_a_knee_of_a_straight_leg_or_a_flipped_one_is_not_read(self):
        """The IK solver flips a nearly straight knee; the live rigs read 78-161 deg there (2026-10-27)."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        base = kp.measure(worlds_at(w, f), w)
        hip, thigh, ankle = base["knee"]["l"]
        straight = (hip, mp._unit(ankle - hip) * np.linalg.norm(thigh), ankle)
        now = dict(base, knee=dict(base["knee"], l=straight))
        flat_base = dict(base, knee=dict(base["knee"], l=straight))
        flipped = (hip, -thigh + 2.0 * np.dot(thigh, mp._unit(ankle - hip)) * mp._unit(ankle - hip), ankle)
        for b, n, word in ((base, now, "nearly straight"), (flat_base, now, "nearly straight")):
            inc, moved, ignored = kp.increment("passing", b, n, w, f)
            self.assertEqual(inc["knee"]["l"], 0.0)
        bent = kp.bend(base["knee"]["l"])
        if bent > kp.KNEE_BENT:
            inc, moved, ignored = kp.increment("passing", base, dict(base, knee=dict(base["knee"], l=flipped)), w, f)
            self.assertEqual(inc["knee"]["l"], 0.0)
            self.assertTrue(ignored, "the flip is said")

    def test_a_leg_the_pelvis_pulled_straight_gives_no_foot_and_no_toes(self):
        """2026-10-27: the pelvis +5 cm on a rig pulls an IK leg straight and drags its foot with the hip (1.4 cm
        lifts, 0.8 cm prints, 7 deg toes read live) - the solver's, not the animator's: the pelvis is taken, that
        leg's foot and toes are not, said."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["up"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        up = np.asarray(w.up, float)
        kids = mp._children(w.parents)
        for k in mp._below(w.index["pelvis"], kids):
            now[w.names[k]][3, :3] = now[w.names[k]][3, :3] + 5.0 * up
        hip = now["thigh_l"][3, :3]
        thigh = np.linalg.norm(base["calf_l"][3, :3] - base["thigh_l"][3, :3])
        calf = np.linalg.norm(base["foot_l"][3, :3] - base["calf_l"][3, :3])
        line = mp._unit(base["foot_l"][3, :3] - hip)
        knee, ankle = hip + line * thigh, hip + line * (thigh + calf)
        drag = ankle - now["foot_l"][3, :3]
        now["calf_l"][3, :3] = knee
        for name in ("foot_l", "ball_l"):
            now[name][3, :3] = now[name][3, :3] + drag
        now["ball_l"][:3, :3] = wm.exp_rot(np.array([math.radians(7.0), 0.0, 0.0])) @ now["ball_l"][:3, :3]
        self.assertLess(kp.bend(kp.measure(now, w)["knee"]["l"]), kp.KNEE_BENT)
        inc, moved, ignored = kp.increment("up", kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertAlmostEqual(float(inc["pelvis"][2]), 5.0, places=6)
        self.assertNotIn("ball_l", inc["rot"])
        self.assertLess(float(np.linalg.norm(inc["foot"]["l"]["t"])), 1e-9)
        self.assertLess(float(np.linalg.norm(inc["print"]["l"]["t"])), 1e-9)
        self.assertTrue(any("leg_l" in text and "pulled straight" in text for text in ignored), ignored)

    def test_a_straight_leg_with_the_pelvis_still_keeps_its_foot_move(self):
        """A foot moved on a nearly straight leg with the pelvis where it was is the animator's."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["up"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        for name in ("foot_l", "ball_l"):
            now[name][3, :3] = now[name][3, :3] + 4.0 * np.asarray(w.fwd, float)
        inc, moved, ignored = kp.increment("up", kp.measure(base, w), kp.measure(now, w), w, f)
        self.assertFalse(any("pulled straight" in text for text in ignored), ignored)
        self.assertGreater(float(np.linalg.norm(inc["foot"]["l"]["t"])
                                 + np.linalg.norm(inc["print"]["l"]["t"])), 3.0)

    def test_a_knee_is_read_only_on_the_sides_given(self):
        """keyrig.knees_taken: an IK leg whose pole control stayed turns by itself when the pelvis or the foot
        moves (1.6-2.3 deg on the live rigs) - that knee is not read."""
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        base = worlds_at(w, f)
        hip = base["thigh_l"][3, :3].copy()
        line = mp._unit(base["foot_l"][3, :3] - hip)
        now = turned_subtree(w, base, "thigh_l", wm.exp_rot(math.radians(12.0) * line))
        b, n = kp.measure(base, w), kp.measure(now, w)
        if kp.bend(b["knee"]["l"]) <= kp.KNEE_BENT:
            self.skipTest("the synthetic leg is straight at the passing")
        taken = kp.increment("passing", b, n, w, f)[0]
        self.assertAlmostEqual(math.degrees(abs(taken["knee"]["l"])), 12.0, delta=0.5)
        skipped = kp.increment("passing", b, n, w, f, knees={"l": False, "r": True})[0]
        self.assertEqual(skipped["knee"]["l"], 0.0)

    def test_knees_taken_by_the_poles(self):
        kr = T.load("keyrig")
        still = {"l": {"ik": True, "t": [1.0, 2.0, 3.0]}, "r": {"ik": True, "t": [4.0, 5.0, 6.0]}}
        moved = {"l": {"ik": True, "t": [1.0, 2.0, 9.0]}, "r": {"ik": True, "t": [4.0, 5.0, 6.0]}}
        fk = {"l": {"ik": False, "t": [1.0, 2.0, 3.0]}, "r": {"ik": True, "t": [4.0, 5.0, 6.0]}}
        self.assertEqual(kr.knees_taken(still, still), {"l": False, "r": False})
        self.assertEqual(kr.knees_taken(still, moved), {"l": True, "r": False})
        self.assertEqual(kr.knees_taken(still, fk), {"l": True, "r": False})
        self.assertIsNone(kr.knees_taken(None, still))

    def test_the_toes_turn_in_the_foot_s_frame(self):
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["up"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        now["ball_l"][:3, :3] = wm.exp_rot(np.array([math.radians(20.0), 0.0, 0.0])) @ now["ball_l"][:3, :3]
        keys = kp.combine({}, "up", kp.measure(base, w), kp.measure(now, w), w, f)[0]
        self.assertIn("ball_l", keys["up"]["rot"])
        out = kp.correct(w.clip, keys, steps, w)
        rot = lambda c, n, g: wm.orthonormal(c[w.index[n], g, :3, :3])
        local = lambda c, g: rot(c, "ball_l", g) @ rot(c, "foot_l", g).T
        got = local(out.worlds, f) @ local(w.clip.worlds, f).T
        self.assertAlmostEqual(math.degrees(float(np.linalg.norm(wm.log_rot(got)))), 20.0, delta=0.01)
        foot = w.index["foot_l"]
        self.assertTrue(np.allclose(out.worlds[foot, f], w.clip.worlds[foot, f], atol=1e-6))

    def test_a_lowered_pelvis_reads_minus(self):
        w = T.walk()
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        base = worlds_at(w, f)
        now = dict((n, np.array(m)) for n, m in base.items())
        kids = mp._children(w.parents)
        for k in mp._below(w.index["pelvis"], kids):
            if w.names[k] not in ("foot_l", "ball_l", "foot_r", "ball_r"):
                now[w.names[k]][3, :3] = now[w.names[k]][3, :3] - 2.0 * w.up
        keys, moved, ignored = kp.combine({}, "passing", kp.measure(base, w), kp.measure(now, w), w, f)
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


class LineTests(unittest.TestCase):

    def test_the_rigs_stand_one_behind_another_along_the_travel(self):
        """Contact first beside the walker, then each key further along where the walk goes (2026-10-27)."""
        kr = T.load("keyrig")
        points = [kr.line_point((10.0, 0.0, 5.0), (0.0, 0.0, 300.0), i) for i in range(4)]
        self.assertEqual(points[0], (10.0 - kr.OFFSET, 0.0, 5.0))
        for i, p in enumerate(points):
            self.assertAlmostEqual(p[0], 10.0 - kr.OFFSET)
            self.assertAlmostEqual(p[2], 5.0 + kr.GAP * i)
        back = [kr.line_point((0.0, 0.0, 0.0), (-50.0, 0.0, 0.0), i) for i in range(2)]   # walking along -X
        self.assertAlmostEqual(back[1][0] - back[0][0], -kr.GAP)
        self.assertAlmostEqual(back[0][2], -kr.OFFSET)     # its right is -Z
        still = kr.line_point((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1)
        self.assertAlmostEqual(still[2], kr.GAP)            # in place: along +Z


class SplitTests(unittest.TestCase):

    def incs(self, ups, forwards=(0.0, 0.0, 0.0, 0.0)):
        out = {}
        for key, up, fwd in zip(kp.KEYS, ups, forwards):
            e = kp.empty_key()
            e["pelvis"] = np.array([fwd, 0.0, up])
            out[key] = e
        return out

    def test_the_pelvis_raised_alike_on_all_four_is_the_height(self):
        """2026-10-27 («цикл должен измениться по умному»): all four alike is a setting of the whole walk."""
        common, rest = kp.split_common(self.incs((5.0, 5.0, 6.0, 5.5), (-3.0, -3.0, -3.0, -2.5)))
        self.assertAlmostEqual(common["height"], 5.0)
        self.assertAlmostEqual(common["forward"], -2.5)
        self.assertAlmostEqual(rest["passing"]["pelvis"][2], 1.0)
        self.assertAlmostEqual(rest["contact"]["pelvis"][0], -0.5)

    def test_one_key_or_mixed_signs_stay_the_keys(self):
        for ups in ((0.0, -4.0, 0.0, 0.0), (3.0, -3.0, 3.0, 3.0), (5.0, 1.0, 5.0, 5.0)):
            common, rest = kp.split_common(self.incs(ups))
            self.assertEqual(common["height"], 0.0, ups)
            self.assertTrue(np.allclose([rest[k]["pelvis"][2] for k in kp.KEYS], ups))

    def test_a_foot_moved_alike_on_two_rigs_is_one_print(self):
        incs = self.incs((0.0, 0.0, 0.0, 0.0))
        incs["down"]["print"]["l"]["t"] = np.array([4.0, 0.0, 0.0])
        incs["passing"]["print"]["l"]["t"] = np.array([4.2, 0.0, 0.0])
        one = kp.one_print(incs)
        self.assertTrue(np.allclose(kp.stance_prints(one)["l"]["t"], [4.2, 0.0, 0.0]))


class ResultTests(unittest.TestCase):

    def test_an_edit_on_the_result_is_exact_at_the_result_s_key(self):
        """The key edits go on the walker's evaluated animation (after the parameters, the pose and the physics):
        exact at the key found on the result, nothing at the other keys."""
        w = T.walk()
        r = w.evaluate({"tempo": 18, "balance": 0.0})
        keys = {"contact": kp.empty_key()}
        Y = wm.exp_rot(np.array([0.0, 0.0, math.radians(15.0)]))
        keys["contact"]["rot"]["upperarm_l"] = Y
        worlds, rw, steps, note = kp.on_result(w, r.worlds, keys)
        self.assertEqual(note, "")
        ref = kp.frames_of(steps, rw.P)
        local = lambda W, g: (wm.orthonormal(W[w.index["upperarm_l"], g, :3, :3]) @
                              wm.orthonormal(W[w.index["clavicle_l"], g, :3, :3]).T)
        got = local(r.worlds, ref["contact"]).T @ local(worlds, ref["contact"])
        self.assertLess(float(np.abs(got - Y).max()), 1e-9)
        self.assertLess(float(np.abs(local(worlds, ref["down"]) - local(r.worlds, ref["down"])).max()), 1e-9)

    def test_in_place_is_the_model_s(self):
        w = T.walk()
        moving = w.evaluate({"balance": 0.0})
        still = w.evaluate({"balance": 0.0, "in_place": 1.0})
        self.assertLess(float(np.abs(kp.in_place(moving.worlds, w, 1.0) - still.worlds).max()), 1e-6)

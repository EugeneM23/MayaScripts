"""maya_walk.clean on the synthetic walker of test_walkmodel: each breakage made, found and undone; a clean
cycle left exactly as it is. numpy only, no Maya."""

import math
import os
import subprocess
import sys
import unittest

import numpy as np

from tests import test_walkmodel as tw

wm = tw.wm
wc = tw.load("clean")
P = 24
NAMES = [b[0] for b in tw.BONES]
PARENTS = [NAMES.index(b[1]) if b[1] else -1 for b in tw.BONES]
IDX = dict((n, i) for i, n in enumerate(NAMES))


def standing():
    """The synthetic's skeleton standing still and symmetric (its rest and its reference): the upper body as at
    phase 0, the legs bent alike over flat feet at ankle height 8."""
    local = dict((b[0], b[2]) for b in tw.BONES)
    W = {"root": tw.mat(np.eye(3), [0.0, 0.0, 0.0]), "pelvis": tw.mat(np.eye(3), [0.0, 90.0, 0.0])}
    for name in tw.UPPER:
        parent = tw.BONES[NAMES.index(name)][1]
        W[name] = tw.mat(tw.upper_rot(name, 0.0), local[name]) @ W[parent]
    for side, x in (("l", 10.0), ("r", -10.0)):
        hip = np.array(local["thigh_" + side], float) @ W["pelvis"][:3, :3] + W["pelvis"][3, :3]
        ankle = np.array([x, 8.0, 0.0])
        knee, thigh_rot, calf_rot = tw.leg(hip, ankle)
        W["thigh_" + side] = tw.mat(thigh_rot, hip)
        W["calf_" + side] = tw.mat(calf_rot, knee)
        W["foot_" + side] = tw.mat(np.eye(3), ankle)
        W["ball_" + side] = tw.mat(np.eye(3), local["ball_" + side]) @ W["foot_" + side]
        W["thigh_twist_01_" + side] = tw.mat(np.eye(3), local["thigh_twist_01_" + side]) @ W["thigh_" + side]
        W["ik_foot_" + side] = W["foot_" + side].copy()
    W["ik_foot_root"] = W["root"].copy()
    W["camera_root"] = tw.mat(np.eye(3), local["camera_root"]) @ W["root"]
    return W


REST = standing()
STATICS = dict((n, {"parent": tw.BONES[i][1], "canonical": n, "rest": [float(v) for v in REST[n].reshape(16)]})
               for i, n in enumerate(NAMES))


def walker_worlds():
    return tw.synthetic(P=P)[2].copy()


def clip_of(worlds):
    return wm.Clip(NAMES, PARENTS, worlds, fps=30.0, up=(0, 1, 0), name="synthetic")


def run(worlds, posture_fix=False, **knobs):
    return wc.clean(clip_of(worlds), STATICS, dict(REST), knobs, posture_fix=posture_fix)


def rig_of(worlds):
    return wc.Rig(NAMES, PARENTS, worlds)


def deg(r):
    return np.degrees(np.linalg.norm(wm.log_rot(r), axis=-1))


def steps(report):
    return [step for step, _, _ in report.lines]


class PurityTests(unittest.TestCase):

    def test_imports_nothing_of_maya(self):
        here = os.path.dirname(os.path.abspath(__file__))
        plugin = os.path.join(os.path.dirname(here), "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); import maya_walk.clean; "
                "print(sorted(k for k in sys.modules if k.startswith('maya') and not k.startswith('maya_')))" % plugin)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


class KnobTests(unittest.TestCase):

    def test_the_knobs_and_their_defaults(self):
        self.assertEqual([k[0] for k in wc.KNOBS], ["smooth", "seam"])
        self.assertEqual(wc.knobs(), wc.DEFAULTS)
        k = wc.knobs({"smooth": 99.0, "stride": 2.0, "seam": -1.0})
        self.assertEqual((k["smooth"], k["seam"]), (4.0, 0.0))
        self.assertNotIn("stride", k)


class IdentityTests(unittest.TestCase):

    def test_a_clean_cycle_comes_back_as_it_went_in(self):
        clip = clip_of(walker_worlds())
        out, report = wc.clean(clip, STATICS, dict(REST), {})
        self.assertIs(out, clip)
        self.assertFalse(report.changed, report.text())
        self.assertEqual(report.short(), "")

    def test_without_statics_or_a_reference_too(self):
        clip = clip_of(walker_worlds())
        out, report = wc.clean(clip)
        self.assertIs(out, clip)
        self.assertFalse(report.changed, report.text())

    def test_the_rig_composes_its_worlds_back(self):
        worlds = walker_worlds()
        self.assertLess(float(np.abs(rig_of(worlds).worlds() - worlds).max()), 1e-9)


class LoopTests(unittest.TestCase):

    def test_a_cycle_written_without_its_closing_frame_gets_it(self):
        worlds = walker_worlds()
        out, report = run(worlds[:, :P])
        self.assertIn("loop", steps(report))
        self.assertEqual(out.worlds.shape[1], P + 1)
        self.assertLess(float(np.abs(out.worlds - worlds).max()), 1e-6)

    def test_the_best_loop_is_cut_out_of_a_longer_clip(self):
        worlds = walker_worlds()
        travel = worlds[IDX["root"], P, 3, :3] - worlds[IDX["root"], 0, 3, :3]
        second = worlds[:, 1:16].copy()
        second[:, :, 3, :3] += travel
        long = np.concatenate([worlds, second], axis=1)          # 1.6 cycles
        out, report = run(long)
        self.assertEqual(out.worlds.shape[1], P + 1, report.text())
        self.assertTrue(wc.is_closed(out.worlds, wc._Clip(out)))
        walk = wm.analyse(out)
        self.assertAlmostEqual(float(np.linalg.norm(walk.travel)), 120.0, delta=0.5)

    def test_a_take_of_many_cycles_gives_one(self):
        worlds = walker_worlds()
        travel = worlds[IDX["root"], P, 3, :3] - worlds[IDX["root"], 0, 3, :3]
        parts = [worlds]
        for k in (1, 2, 3, 4):
            more = worlds[:, 1:(16 if k == 4 else None)].copy()
            more[:, :, 3, :3] += k * travel
            parts.append(more)
        out, report = run(np.concatenate(parts, axis=1))        # four cycles and a half: the loop is one
        self.assertEqual(out.worlds.shape[1], P + 1, report.text())

    def test_a_cut_seam_is_closed_in_value_and_slope(self):
        worlds = walker_worlds()
        travel = worlds[IDX["root"], P, 3, :3] - worlds[IDX["root"], 0, 3, :3]
        second = worlds[:, 1:16].copy()
        second[:, :, 3, :3] += travel
        long = np.concatenate([worlds, second], axis=1)
        rig = rig_of(long[:, 3:3 + P + 1])
        j = IDX["spine_01"]
        rig.rot[j, -6:] = rig.rot[j, -6:] @ wm.exp_rot([0.0, 0.0, math.radians(8.0)])      # the seam off 8 deg
        before = rig.rot[j].copy()
        wc.close_seam(rig, IDX["root"], 6, True, STATICS, wc.Report())
        x, _ = wc._rot_series(rig, j)
        d, dv = wc._seam_steps(x)
        self.assertLess(float(np.degrees(np.linalg.norm(d))), 1e-6)
        self.assertLess(float(np.degrees(np.linalg.norm(dv))), 0.05)
        middle = slice(8, P - 8)
        self.assertLess(float(np.abs(rig.rot[j, middle] - before[middle]).max()), 1e-9)

    def test_holden_offsets_take_the_step_off_and_end_flat(self):
        off = wc._holden(25, 6, np.array([2.0]), np.array([0.5]))
        self.assertAlmostEqual(float(off[0, 0] - off[-1, 0]), 2.0, places=12)
        self.assertEqual(float(off[6, 0]), 0.0)
        self.assertEqual(float(off[18, 0]), 0.0)
        self.assertTrue(np.all(off[7:18] == 0.0))


class SmoothTests(unittest.TestCase):

    def test_smooth_quiets_a_jitter(self):
        worlds = walker_worlds()
        rig = rig_of(worlds)
        j = IDX["head"]
        noise = np.array([math.radians(3.0) * (1 if f % 2 else -1) for f in range(P + 1)])
        noise[-1] = noise[0]
        rig.rot[j] = rig.rot[j] @ wm.exp_rot(np.outer(noise, [1.0, 0.0, 0.0]))
        noisy = rig.worlds()
        original = rig_of(worlds).rot[j]
        out, report = run(noisy, smooth=2.0)
        self.assertIn("smooth", steps(report))
        after = rig_of(out.worlds).rot[j]
        self.assertLess(float(deg(after @ np.swapaxes(original, -1, -2)).max()), 1.0)
        out0, _ = run(noisy, smooth=0.0)
        self.assertGreater(float(deg(rig_of(out0.worlds).rot[j] @ np.swapaxes(original, -1, -2)).max()), 2.9)

    def test_smooth_keeps_the_feet_where_they_step(self):
        # 2026-10-16: Smooth 0.9 blurred a clip's foot heights until the walk read the left foot stepping 4 times
        # and the right 3, and Pick refused it; the feet stay the source's, the legs reach them
        worlds = walker_worlds()
        rig = rig_of(worlds)
        j = IDX["pelvis"]
        noise = np.array([1.5 * (1 if f % 2 else -1) for f in range(P + 1)])
        noise[-1] = noise[0]
        rig.trans[j, :, 1] += noise                              # the hips jitter 1.5 cm up and down
        noisy = rig.worlds()
        out, report = run(noisy, smooth=3.0)
        self.assertIn("smooth", steps(report))
        for side in ("l", "r"):
            for name in ("foot_" + side, "ball_" + side):
                k = IDX[name]
                self.assertLess(float(np.abs(out.worlds[k] - noisy[k]).max()), 1e-6, name)
            th, ca, fo = IDX["thigh_" + side], IDX["calf_" + side], IDX["foot_" + side]
            for f in range(P + 1):                               # the leg whole: its bones' lengths kept
                for a, b in ((th, ca), (ca, fo)):
                    was = np.linalg.norm(noisy[b, f, 3, :3] - noisy[a, f, 3, :3])
                    now = np.linalg.norm(out.worlds[b, f, 3, :3] - out.worlds[a, f, 3, :3])
                    self.assertAlmostEqual(float(now), float(was), places=5)
        hips = out.worlds[j, :P, 3, 1]
        self.assertLess(float(np.abs(np.diff(hips)).max()), 1.0)      # the jitter is gone from the hips
        a, b = wm.analyse(clip_of(noisy)), wm.analyse(out)
        for side in ("l", "r"):
            self.assertEqual([f.on for f in a.steps[side]], [f.on for f in b.steps[side]])


def turned(worlds, name, axis_world_like, degrees):
    """A copy with `name`'s local turned `degrees` about an axis given in its parent's frame."""
    rig = rig_of(worlds)
    j = IDX[name]
    rig.rot[j] = rig.rot[j] @ wm.exp_rot(np.radians(degrees) * np.asarray(axis_world_like, float))
    return rig.worlds()


class PostureTests(unittest.TestCase):

    def test_a_foot_turned_out_takes_its_opposite_mirrored(self):
        worlds = walker_worlds()
        shin = wm._unit(rig_of(worlds).trans[IDX["foot_l"]].mean(axis=0))
        broken = turned(worlds, "foot_l", shin, 70.0)
        out, report = run(broken, posture_fix=True)
        self.assertIn("posture", steps(report))
        self.assertIn("foot_l", report.text())
        self.assertIn("mirrored", report.text())
        a, b = rig_of(out.worlds), rig_of(worlds)
        j = IDX["foot_l"]
        self.assertLess(float(deg(wm.mean_rot(a.rot[j, :P]) @ wm.mean_rot(b.rot[j, :P]).T)), 2.0)
        self.assertLess(float(np.median(deg(a.rot[j] @ np.swapaxes(b.rot[j], -1, -2)))), 2.0)

    def test_dropped_shoulders_go_back_on_the_reference_and_the_arms_keep_hanging(self):
        worlds = walker_worlds()
        broken = turned(turned(worlds, "clavicle_l", [0, 0, 1], -25.0), "clavicle_r", [0, 0, 1], 25.0)
        out, report = run(broken, posture_fix=True)
        text = report.text()
        self.assertIn("clavicle_l", text)
        self.assertIn("clavicle_r", text)
        self.assertIn("reference", text)
        a, b = rig_of(out.worlds), rig_of(worlds)
        for name in ("clavicle_l", "clavicle_r"):
            j = IDX[name]
            self.assertLess(float(deg(wm.mean_rot(a.rot[j, :P]) @ wm.mean_rot(b.rot[j, :P]).T)), 2.0, name)
        broken_arm = wm._batch_rot(broken[IDX["upperarm_l"]])
        self.assertLess(float(np.abs(wm._batch_rot(out.worlds[IDX["upperarm_l"]]) - broken_arm).max()), 1e-9)

    def test_a_bone_moved_off_its_joint_goes_back(self):
        worlds = walker_worlds()
        rig = rig_of(worlds)
        j = IDX["clavicle_l"]
        t = rig.trans[j]
        rig.trans[j] = t + 6.0 * t / np.linalg.norm(t, axis=1, keepdims=True)
        out, report = run(rig.worlds(), posture_fix=True)
        self.assertIn("clavicle_l", report.text())
        self.assertLess(float(np.abs(rig_of(out.worlds).trans[j] - rig_of(worlds).trans[j]).max()), 1e-6)

    def test_only_when_asked(self):
        worlds = walker_worlds()
        broken = turned(turned(worlds, "clavicle_l", [0, 0, 1], -25.0), "clavicle_r", [0, 0, 1], 25.0)
        out, report = run(broken)
        self.assertNotIn("posture", steps(report))

    def test_a_walk_within_its_limits_is_left(self):
        worlds = turned(walker_worlds(), "foot_l", [0, 1, 0], 15.0)
        out, report = run(worlds, posture_fix=True)
        self.assertNotIn("posture", steps(report))


class DerivedTests(unittest.TestCase):

    def test_a_helper_that_does_not_loop_goes_back_on_its_bone(self):
        worlds = walker_worlds()
        broken = worlds.copy()
        h = IDX["ik_foot_l"]
        for f in range(P + 1):
            broken[h, f, :3, :3] = wm.exp_rot([0.0, math.radians(3.0 * f), 0.0])
        out, report = run(broken)
        self.assertIn("helpers", steps(report))
        self.assertLess(float(np.abs(out.worlds[h] - out.worlds[IDX["foot_l"]]).max()), 1e-9)

    def test_a_twist_that_does_not_loop_is_rebuilt_and_a_good_one_kept(self):
        worlds = walker_worlds()
        rig = rig_of(worlds)
        j = IDX["thigh_twist_01_l"]
        rig.rot[j] = rig.rot[j] @ wm.exp_rot(np.outer(np.radians(np.linspace(0.0, 30.0, P + 1)), [1.0, 0.0, 0.0]))
        out, report = run(rig.worlds())
        self.assertIn("twists", steps(report))
        self.assertIn("thigh_twist_01_l", report.text())
        self.assertNotIn("thigh_twist_01_r", report.text())
        a = rig_of(out.worlds)
        rule = wc._twist_rule(a, wc._Clip(out), STATICS, "thigh_twist_01_l")
        self.assertLess(float(deg(a.rot[j] @ np.swapaxes(rule, -1, -2)).max()), 1e-6)
        self.assertLess(float(deg(a.rot[j, -1] @ a.rot[j, 0].T)), 1e-6)


class SceneTests(unittest.TestCase):
    """The walks folder read through maya_walk.scene with no Maya: a raw clip saved, read under clean knobs."""

    def setUp(self):
        import tempfile
        self.scene = tw.load("scene")
        self.files = tw.load("walkfile")
        self.folder = tempfile.mkdtemp()
        self.old = self.scene.WALKS
        self.scene.WALKS = self.folder
        self.scene._state()["loaded"] = {}

    def tearDown(self):
        import shutil
        self.scene.WALKS = self.old
        shutil.rmtree(self.folder, ignore_errors=True)

    def save(self, worlds, name="raw"):
        clip = clip_of(worlds)
        clip.name = name
        self.files.save(self.files.path_for(self.folder, name), clip, STATICS, 0)
        return name

    def save_standing_pose(self, name="standing"):
        bones = dict((n, dict(STATICS[n], world=STATICS[n]["rest"])) for n in NAMES)
        self.files.save_pose(self.files.pose_path_for(self.folder, name), name, bones)
        return name

    def test_a_raw_clip_is_read_cleaned(self):
        name = self.save(walker_worlds()[:, :P])            # no closing frame: Save walk refused this before
        walk, statics, start, report = self.scene.load_walk(name, {})
        self.assertEqual(walk.P, P)
        self.assertIn("loop", steps(report))

    def test_the_reading_is_cached_per_knobs(self):
        name = self.save(walker_worlds())
        a = self.scene.load_walk(name, {})[0]
        self.assertIs(self.scene.load_walk(name, {"stride": 1.3})[0], a)
        self.assertIsNot(self.scene.load_walk(name, {"smooth": 1.0})[0], a)

    def test_fix_posture_is_a_walker_s_edit_the_walk_s_file_is_never_written(self):
        """2026-10-27: «Текущая походка загруженная из библиотеки не должна пострадать» - Fix posture says what
        it sets right and the walker takes it (its edits' "posture"); the file stays as it is."""
        self.assertTrue(os.path.exists(self.scene.REFERENCE_FILE))
        worlds = walker_worlds()
        shin = wm._unit(rig_of(worlds).trans[IDX["foot_l"]].mean(axis=0))
        name = self.save(turned(worlds, "foot_l", shin, 70.0))
        path = self.files.path_for(self.folder, name)
        stamp = os.path.getmtime(path)
        report, line, fixed = self.scene.fix_posture(name, {})
        self.assertTrue(fixed)
        self.assertIn("posture", steps(report))
        self.assertIn("foot_l", line)
        self.assertEqual(os.path.getmtime(path), stamp)
        self.assertFalse(os.path.exists(path + self.scene.BACKUP))
        self.assertNotIn("posture", steps(self.scene.load_walk(name, {})[3]))    # the walk as the library has it
        walk = self.scene.load_walk(name, {}, {"posture": True})[0]           # a walker's: set right
        j = IDX["foot_l"]
        rot = wm.orthonormal(walk.clip.worlds[j, 0, :3, :3])
        self.assertIn("posture", steps(self.scene.load_walk(name, {}, {"posture": True})[3]))
        self.assertIsNotNone(rot)

    def test_fix_posture_leaves_a_good_walk_untouched(self):
        name = self.save(walker_worlds())
        path = self.files.path_for(self.folder, name)
        stamp = os.path.getmtime(path)
        report, line, fixed = self.scene.fix_posture(name, {})
        self.assertFalse(fixed)
        self.assertIn("nothing out of place", line)
        self.assertEqual(os.path.getmtime(path), stamp)
        self.assertFalse(os.path.exists(path + self.scene.BACKUP))

    def test_model_knobs_leave_the_clean_ones_out(self):
        got = self.scene.model_knobs({"stride": 1.2, "smooth": 2.0, "lift_l": 1.5})
        self.assertEqual(got, {"stride": 1.2, "lift_l": 1.5})
        self.assertIn("smooth", self.scene.ALL_DEFAULTS)
        self.assertIn("stride", self.scene.ALL_DEFAULTS)


if __name__ == "__main__":
    unittest.main()

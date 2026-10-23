"""Our CAT's model (docs/superpowers/plans/catwalk/catmodel.py) on Manny's template: the walk it
synthesises keeps the skeleton whole, closes, plants its feet and moves the way CATMotion says."""
import importlib.util
import json
import math
import os
import subprocess
import sys
import unittest

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL = os.path.join(REPO, "docs", "superpowers", "plans", "catwalk", "catmodel.py")
TEMPLATE = os.path.join(REPO, "SkeldarAnim", "assets", "manny_skeleton_template.json")


def _load():
    spec = importlib.util.spec_from_file_location("catmodel_under_test", MODEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cm = _load()


def manny():
    with open(TEMPLATE) as handle:
        joints = json.load(handle)["joints"]
    return cm.Skeleton.from_template(dict((j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]})
                                          for j in joints))


SKEL = manny()


def gen(**given):
    knobs = cm.preset(given.pop("preset", "Walk"), 30)
    knobs.update(given)
    return cm.generate(SKEL, knobs, 30), knobs


def pos(cycle, f, leaf):
    return cycle.frames[f][leaf][3, :3]


def bob_harmonics(cycle):
    """The amplitudes (cm) of the pelvis height's harmonics over the cycle (index k = k times a cycle)."""
    T = cycle.info["frames"]
    y = np.array([cycle.frames[f]["pelvis"][3, 1] for f in range(T)])
    return np.abs(np.fft.rfft(y - y.mean())) * 2.0 / T


class Pure(unittest.TestCase):
    def test_imports_nothing_but_numpy(self):
        code = "import sys; sys.path.insert(0, %r); import catmodel; print(sorted(m for m in sys.modules if m.startswith(('maya', 'PySide'))))" % os.path.dirname(MODEL)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]")


class Cycle(unittest.TestCase):
    def test_every_preset_keeps_the_bones_and_closes_on_its_travel(self):
        for name in cm.PRESET_ORDER:
            c, _ = gen(preset=name)
            T = c.info["frames"]
            for leaf, parent in SKEL.parent.items():
                if parent is None or leaf == SKEL.pelvis:
                    continue
                rest = np.linalg.norm(SKEL.pos[leaf] - SKEL.pos[parent])
                for f in (0, T // 3, T // 2):
                    self.assertAlmostEqual(np.linalg.norm(pos(c, f, leaf) - pos(c, f, parent)), rest, 4, (name, leaf))
            for leaf in SKEL.order:
                np.testing.assert_allclose(pos(c, T, leaf) - pos(c, 0, leaf), c.travel, atol=1e-6)
                np.testing.assert_allclose(c.frames[T][leaf][:3, :3], c.frames[0][leaf][:3, :3], atol=1e-9)

    def test_on_the_spot_the_cycle_stands_still(self):
        c, _ = gen(on_spot=1.0)
        self.assertEqual(float(np.linalg.norm(c.travel)), 0.0)
        np.testing.assert_allclose(pos(c, c.info["frames"], "pelvis"), pos(c, 0, "pelvis"), atol=1e-9)

    def test_a_cycle_travels_two_steps(self):
        c, k = gen()
        self.assertAlmostEqual(float(np.linalg.norm(c.travel)), 2 * k["stride"] * SKEL.leg, 6)

    def test_the_planted_ankle_stands_still_mid_stance(self):
        c, k = gen()
        T, d = c.info["frames"], k["duty"]
        frames = [f for f in range(T) if 0.22 * d < f / float(T) < 0.5 * d]
        for a, b in zip(frames, frames[1:]):
            self.assertLess(np.linalg.norm(pos(c, a, "foot_l") - pos(c, b, "foot_l")), 1e-9)

    def test_the_ball_stays_down_while_the_heel_rises(self):
        c, k = gen()
        T, d = c.info["frames"], k["duty"]
        frames = [f for f in range(T) if 0.6 * d < f / float(T) < 0.98 * d]
        for a, b in zip(frames, frames[1:]):
            self.assertLess(np.linalg.norm(pos(c, a, "ball_l") - pos(c, b, "ball_l")), 1e-6)
        self.assertGreater(pos(c, frames[-1], "foot_l")[1], pos(c, frames[0], "foot_l")[1] + 1.0)

    def test_a_walk_has_both_feet_down_and_a_run_has_flight(self):
        walk, _ = gen()
        run, _ = gen(preset="Run")
        self.assertGreater(walk.info["double"], 0)
        self.assertEqual(walk.info["flight"], 0)
        self.assertGreater(run.info["flight"], 0)
        self.assertEqual(run.info["double"], 0)

    def test_the_knees_bend_forward(self):
        for name in ("Walk", "Run", "Sneak"):
            c, _ = gen(preset=name)
            for w in c.frames:
                hip, knee, ankle = w["thigh_l"][3, :3], w["calf_l"][3, :3], w["foot_l"][3, :3]
                axis = cm.unit(ankle - hip)
                off = (knee - hip) - axis * np.dot(knee - hip, axis)
                self.assertGreater(float(np.dot(off, SKEL.fwd)), 0.0, name)

    def test_the_pelvis_bobs_smoothly_even_driven_by_hard_knees(self):
        # the planting knee asks for a deep bend at the contact and its leg takes over within a frame: the
        # body's height still changes smoothly, nothing past the 4th harmonic of the cycle
        c, _ = gen(knee_drive=1.0, knee_plant=46.0, knee_load=30.0, knee_mid=11.0, knee_lift=29.0, bob=0.0,
                   crouch=0.0)
        amps = bob_harmonics(c)
        self.assertLess(amps[5:].sum(), 0.1 * amps[2], amps[:9].round(2))

    def test_the_default_walk_bobs_once_a_step(self):
        for fps in (24, 30, 60):
            c = cm.generate(SKEL, cm.preset("Walk", fps), fps)
            amps = bob_harmonics(c)
            self.assertGreater(amps[2], 2.5, (fps, amps[:9].round(2)))           # cm
            self.assertLess(amps[3:].sum(), 0.15 * amps[2], (fps, amps[:9].round(2)))


class Signs(unittest.TestCase):
    def test_at_the_left_contact_the_left_foot_and_hip_lead_and_the_left_hand_trails(self):
        c, _ = gen()
        w = c.frames[0]
        fwd = SKEL.fwd
        self.assertGreater(np.dot(w["foot_l"][3, :3] - w["foot_r"][3, :3], fwd), 30.0)
        self.assertGreater(np.dot(w["thigh_l"][3, :3] - w["thigh_r"][3, :3], fwd), 0.5)
        self.assertLess(np.dot(w["hand_l"][3, :3] - w["hand_r"][3, :3], fwd), -10.0)

    def test_mid_left_stance_the_swing_hip_drops_and_the_weight_goes_left(self):
        c, k = gen()
        f = int(round(k["duty"] / 2.0 * c.info["frames"]))
        w = c.frames[f]
        self.assertGreater(w["thigh_l"][3, 1], w["thigh_r"][3, 1])
        still, _ = gen(weight_shift=0.0)
        self.assertGreater(np.dot(w["pelvis"][3, :3] - still.frames[f]["pelvis"][3, :3], SKEL.left), 1.0)

    def test_direction_moves_sideways_and_keeps_the_facing(self):
        c, _ = gen(preset="Strafe L")
        self.assertGreater(float(np.dot(c.travel, SKEL.left)), 50.0)
        self.assertLess(abs(float(np.dot(c.travel, SKEL.fwd))), 1e-6)
        np.testing.assert_allclose(c.frames[0]["root"][:3, :3], SKEL.rest["root"][:3, :3], atol=1e-12)

    def test_backward_moves_back(self):
        c, _ = gen(preset="Backward")
        self.assertLess(float(np.dot(c.travel, SKEL.fwd)), -50.0)

    def test_a_gradient_climbs(self):
        c, _ = gen(gradient=10.0)
        self.assertGreater(c.travel[1], 0.15 * float(np.dot(c.travel, SKEL.fwd)))
        self.assertGreater(pos(c, c.info["frames"], "foot_l")[1], pos(c, 0, "foot_l")[1] + 10.0)

    def test_a_limp_moves_one_leg_s_phase(self):
        even, _ = gen()
        limp, _ = gen(phase_r=0.1)
        np.testing.assert_allclose(pos(limp, 0, "foot_l"), pos(even, 0, "foot_l"), atol=1e-6)
        self.assertGreater(np.linalg.norm(pos(limp, 0, "foot_r") - pos(even, 0, "foot_r")), 1.0)

    def test_a_knob_outside_its_range_is_held_and_an_unknown_one_refused(self):
        self.assertEqual(cm.knobs({"stride": 99.0})["stride"], cm.RANGES["stride"][1])
        with self.assertRaises(KeyError):
            cm.knobs({"wobble": 1.0})

    def test_a_cycle_offset_plays_a_later_frame_and_still_closes(self):
        plain, k = gen()
        T = plain.info["frames"]
        shifted = cm.generate(SKEL, dict(k, cycle_offset=-10.0), 30)
        # frame 10 of the shifted cycle is the plain cycle's frame 0, moved by the same amount for every bone
        move = pos(shifted, 10, "pelvis") - pos(plain, 0, "pelvis")
        for leaf in ("foot_l", "hand_r", "head"):
            np.testing.assert_allclose(pos(shifted, 10, leaf) - pos(plain, 0, leaf), move, atol=1e-9)
        for leaf in SKEL.order:
            np.testing.assert_allclose(pos(shifted, T, leaf) - pos(shifted, 0, leaf), shifted.travel, atol=1e-6)
        self.assertLess(np.linalg.norm(cm.flat(pos(shifted, 0, "root") - pos(plain, 0, "root"))), 1e-6)

    def test_a_place_carries_the_whole_cycle(self):
        place = np.eye(4)
        place[:3, :3] = cm.rot(cm.UP, 90.0).T
        place[3, :3] = (100.0, 0.0, 50.0)
        plain, k = gen()
        moved = cm.generate(SKEL, k, 30, place=place)
        np.testing.assert_allclose(moved.frames[5]["pelvis"], plain.frames[5]["pelvis"] @ place, atol=1e-9)


def turn_about(a, b, axis):
    """Degrees two 4x4 worlds' rotations differ about `axis` (the rotation vector's part along it)."""
    q = b[:3, :3].T @ a[:3, :3]
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(q) - 1.0) / 2.0))))
    v = np.array([q[2, 1] - q[1, 2], q[0, 2] - q[2, 0], q[1, 0] - q[0, 1]])
    if np.linalg.norm(v) < 1e-9:
        return 0.0 if angle < 1.0 else angle
    return abs(float(np.dot(v / np.linalg.norm(v), cm.unit(axis)))) * angle


class Chest(unittest.TestCase):
    """The chest has its own motion in degrees (2026-10-23): the old knobs were shares of the pelvis's motion
    and moved it by a degree or less over their whole range."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(MODEL))
        import catmatch
        cls.mt = catmatch

    def test_each_chest_knob_turns_the_chest_by_its_degrees(self):
        base = cm.preset("Jog", 30)          # upright: under a lean the read-back is an euler of a tilted chest
        m0 = self.mt.measure(SKEL, cm.generate(SKEL, base, 30).frames)
        for knob in ("chest_twist", "chest_roll", "chest_pitch"):
            m = self.mt.measure(SKEL, cm.generate(SKEL, dict(base, **{knob: base[knob] + 15.0}), 30).frames)
            self.assertAlmostEqual(m[knob] - m0[knob], 15.0, delta=2.5, msg=knob)       # was <= 1.3 over a whole range

    def test_the_pelvis_no_longer_takes_the_chest_with_it(self):
        base = cm.preset("Walk", 30)
        m0 = self.mt.measure(SKEL, cm.generate(SKEL, base, 30).frames)
        m = self.mt.measure(SKEL, cm.generate(SKEL, dict(base, twist=20.0, roll=10.0), 30).frames)
        self.assertAlmostEqual(m["chest_twist"], m0["chest_twist"], delta=0.3)
        self.assertAlmostEqual(m["chest_roll"], m0["chest_roll"], delta=0.3)

    def test_knobs_saved_before_play_the_same_chest(self):
        k = cm.knobs({"counter": 1.3, "roll_cancel": 0.4, "twist": 9.0, "roll": 6.0})
        self.assertAlmostEqual(k["chest_twist"], 11.7)
        self.assertAlmostEqual(k["chest_roll"], 3.6)
        self.assertNotIn("counter", k)


class Sprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(MODEL))
        import catmatch
        cls.mt = catmatch

    def test_the_run_flies_and_its_shins_never_flip(self):
        c, k = gen(preset="Run")
        self.assertGreater(c.info["flight"], 0)
        self.assertEqual(c.info["double"], 0)
        T = c.info["frames"]
        for side in "lr":
            calf, foot = "calf_" + side, "foot_" + side
            for f in range(T):
                a, b = c.frames[f], c.frames[f + 1]
                axis = b[foot][3, :3] - b[calf][3, :3]
                self.assertLess(turn_about(a[calf], b[calf], axis), 30.0, (side, f))

    def test_a_swinging_foot_hangs_off_its_shin_pointed(self):
        for point in (0.0, 20.0, -15.0):
            c, k = gen(preset="Run", foot_follow=1.0, swing_point=point)
            m = self.mt.measure(SKEL, c.frames)
            self.assertAlmostEqual(m["swing_point"], point, delta=1.0)
            self.assertLess(m["swing_foot"], 4.0)
        c, k = gen(preset="Run", foot_follow=0.0)
        self.assertLess(self.mt.measure(SKEL, c.frames)["swing_point"], -30.0)    # level: far from the shin

    def test_a_take_of_several_cycles_is_averaged_into_one(self):
        c, k = gen(preset="Run")
        T = c.info["frames"]
        travel = c.frames[T]["root"][3, :3] - c.frames[0]["root"][3, :3]
        take = []
        for r in range(3):
            for f in range(T + (1 if r == 2 else 0)):
                world = {}
                for leaf, m in c.frames[f].items():
                    m = m.copy()
                    m[3, :3] += travel * r
                    world[leaf] = m
                take.append(world)
        self.assertEqual(self.mt.cycles_in(SKEL, take), 3)
        one, cycles = self.mt.mean_cycle(SKEL, take)
        self.assertEqual((cycles, len(one)), (3, T + 1))
        worst = max(float(np.abs(one[f][leaf] - c.frames[f][leaf]).max()) for f in range(T + 1) for leaf in one[f])
        self.assertLess(worst, 1e-6)
        same, cycles = self.mt.mean_cycle(SKEL, c.frames)
        self.assertEqual(cycles, 1)
        self.assertIs(same, c.frames)


class Match(unittest.TestCase):
    """catmatch: a cycle our CAT made is read back and matched."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(MODEL))
        import catmatch
        import catmodel
        cls.mt, cls.cm = catmatch, catmodel
        with open(TEMPLATE) as handle:
            joints = json.load(handle)["joints"]
        cls.skel = catmodel.Skeleton.from_template(dict(
            (j["name"], {"parent": j.get("parent"), "world_matrix": j["world_matrix"]}) for j in joints))

    def test_measure_reads_back_what_made_the_cycle(self):
        k = self.cm.preset("Walk", 30)
        k.update(stride=0.9, twist=9.0, swing=30.0)
        c = self.cm.generate(self.skel, k, 30)
        m = self.mt.measure(self.skel, c.frames)
        self.assertEqual(m["frames"], c.info["frames"])
        self.assertAlmostEqual(m["stride"], 0.9, 3)
        self.assertAlmostEqual(m["twist"], 9.0, 0)
        self.assertAlmostEqual(m["arm_swing"], 30.0, delta=3.0)
        self.assertAlmostEqual(m["duty"], k["duty"], delta=1.5 / c.info["frames"])

    def test_a_cycle_walked_on_the_spot_is_read_off_its_treadmill(self):
        k = self.cm.preset("Walk", 30)
        line = self.mt.measure(self.skel, self.cm.generate(self.skel, k, 30).frames)
        spot = self.mt.measure(self.skel, self.cm.generate(self.skel, dict(k, on_spot=1.0), 30).frames)
        self.assertFalse(line["spot"])
        self.assertTrue(spot["spot"])
        for key in ("stride", "duty", "stance_center", "lift"):
            self.assertAlmostEqual(spot[key], line[key], delta=0.02, msg=key)
        self.assertEqual(spot["left_contact"], line["left_contact"])

    def test_the_default_walk_keeps_a_foot_down_at_every_rate(self):
        for fps in (24, 30, 60):
            c = self.cm.generate(self.skel, self.cm.preset("Walk", fps), fps)
            self.assertEqual(c.info["flight"], 0, fps)
            self.assertGreater(c.info["double"], 0, fps)

    def test_a_cycle_of_ours_is_matched_closely(self):
        k = self.cm.preset("Jog", 30)
        k.update(twist=12.0, lean=6.0, arm_out=20.0, elbow=60.0, bend_spine_03=10.0, shoulders=-6.0)
        ref = self.cm.generate(self.skel, k, 30).frames
        fitted, r, o, _ = self.mt.fit(self.skel, ref, 30, rounds=20)
        ours = self.cm.generate(self.skel, fitted, 30).frames
        errors = self.mt.compare(self.skel, ref, ours, r, self.mt.measure(self.skel, ours))
        for group, value in errors.items():
            self.assertLess(value, 4.0, (group, errors))

    def test_a_matched_cycle_bobs_like_its_reference_and_its_knobs_say_so(self):
        k = self.cm.preset("Walk", 30)
        k.update(knee_drive=0.0, crouch=0.05, bob=0.03, bob_phase=0.85)
        ref = self.cm.generate(self.skel, k, 30).frames
        fitted, r, o, _ = self.mt.fit(self.skel, ref, 30, rounds=12)
        self.assertLess(self.mt.pelvis_track(r, o), 0.3)                  # percent of the leg
        self.assertAlmostEqual(o["bob"], fitted["bob"], delta=0.003)
        self.assertAlmostEqual(-o["height"], fitted["crouch"], delta=0.003)


if __name__ == "__main__":
    unittest.main()

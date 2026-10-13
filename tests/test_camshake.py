"""Camera Shake (maya_camshake): the model, the rotation algebra and the hub card, without a scene."""

import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

import maya_camshake as cs  # noqa: E402

FPS = 30.0


def rms2(values):
    """Two RMS: what an amplitude means here."""
    return 2.0 * float(np.sqrt(np.mean(np.square(values))))


class SettingsTests(unittest.TestCase):

    def test_defaults_fill_every_control(self):
        for mode in cs.MODES:
            s = cs.settings(mode)
            for name, _, default, _, _ in cs.CONTROLS[mode]:
                self.assertEqual(s[name], default)
            self.assertEqual(s["seed"], 1)
        self.assertEqual(cs.settings("impact")["direction"], "Random")

    def test_values_are_clamped_and_bad_ones_fall_back(self):
        s = cs.settings("handheld", {"sway": 100.0, "speed": -3, "jitter": "x", "seed": -4})
        self.assertEqual(s["sway"], 6.0)
        self.assertEqual(s["speed"], 0.25)
        self.assertEqual(s["jitter"], 0.12)
        self.assertEqual(s["seed"], 0)
        self.assertEqual(cs.settings("impact", {"direction": "Sideways"})["direction"], "Random")

    def test_a_preset_keeps_the_seed_ease_and_length(self):
        s = cs.preset("handheld", "Nervous", {"seed": 9, "ease": 12.0})
        self.assertEqual((s["sway"], s["speed"], s["seed"], s["ease"]), (1.8, 1.8, 9, 12.0))
        s = cs.preset("impact", "Light", {"seed": 4, "length": 40.0, "direction": "Left"})
        self.assertEqual((s["strength"], s["seed"], s["length"], s["direction"]), (2.0, 4, 40.0, "Left"))

    def test_axes_and_decay(self):
        for mode in cs.MODES:
            s = cs.settings(mode)
            self.assertEqual((s["tilt_on"], s["pan_on"], s["roll_on"]), (True, True, True))
            self.assertFalse(cs.settings(mode, {"pan_on": False})["pan_on"])
            kept = cs.preset(mode, cs.DEFAULT_PRESET[mode], {"roll_on": False})
            self.assertFalse(kept["roll_on"])
        self.assertEqual(cs.settings("impact")["decay"], "Exponential")
        self.assertEqual(cs.settings("impact", {"decay": "Smooth"})["decay"], "Smooth")
        self.assertEqual(cs.settings("impact", {"decay": "Wobbly"})["decay"], "Exponential")
        old = cs.settings("impact", {"swing": 4.0, "bounce": 0.5})        # a record from before
        self.assertNotIn("swing", old)
        self.assertEqual(old["wave"], 8.0)

    def test_an_impact_preset_may_set_the_direction(self):
        self.assertEqual(cs.preset("impact", "Explosion", {"direction": "Left"})["direction"], "Below")
        self.assertEqual(cs.preset("impact", "Recoil")["direction"], "Front")

    def test_every_default_preset_exists(self):
        for mode in cs.MODES:
            self.assertIn(cs.DEFAULT_PRESET[mode], [label for label, _ in cs.PRESETS[mode]])
            self.assertRaises(ValueError, cs.preset, mode, "Nope")


class NoiseTests(unittest.TestCase):

    def seconds(self, n=6000):
        return np.arange(n) / FPS

    def test_deterministic(self):
        a = cs.noise(self.seconds(300), 7, 3, 2.0)
        b = cs.noise(self.seconds(300), 7, 3, 2.0)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.allclose(a, cs.noise(self.seconds(300), 8, 3, 2.0)))
        self.assertFalse(np.allclose(a, cs.noise(self.seconds(300), 7, 4, 2.0)))

    def test_unit_rms_over_a_long_span(self):
        values = cs.noise(self.seconds(), 1, 1, 2.0)
        self.assertAlmostEqual(float(np.sqrt(np.mean(values ** 2))), 1.0, delta=0.1)

    def test_smooth(self):
        """White noise reads ~1.4 here, a 1 Hz sine at 30 fps 0.21: the spline is the sine's kind."""
        values = cs.noise(self.seconds(), 1, 1, 1.0)
        first = np.abs(np.diff(values)).mean()
        second = np.abs(np.diff(values, 2)).mean()
        self.assertLess(second, 0.5 * first)
        white = np.random.default_rng(0).standard_normal(6000)
        self.assertGreater(np.abs(np.diff(white, 2)).mean(), 1.2 * np.abs(np.diff(white)).mean())

    def test_a_longer_span_keeps_the_start(self):
        short = cs.noise(self.seconds(100), 5, 2, 3.0)
        long = cs.noise(self.seconds(1000), 5, 2, 3.0)
        self.assertTrue(np.allclose(short, long[:100]))

    def test_swings_about_hz_times_a_second(self):
        for hz in (0.5, 2.0):
            values = cs.noise(self.seconds(30000), 3, 1, hz)
            crossings = np.count_nonzero(np.diff(np.sign(values)) != 0) / (30000 / FPS)
            self.assertGreater(crossings, 1.6 * hz)    # a sine at hz crosses zero 2 hz times
            self.assertLess(crossings, 2.4 * hz)

    def test_zero_hz_is_still(self):
        self.assertTrue(np.all(cs.noise(self.seconds(10), 1, 1, 0.0) == 0.0))

    def test_fractal_unit_rms(self):
        values = cs.fractal(self.seconds(), 2, 1, 0.5, 3, fps=FPS)
        self.assertAlmostEqual(float(np.sqrt(np.mean(values ** 2))), 1.0, delta=0.12)

    def test_tremor_is_unit_rms_and_deterministic(self):
        values = cs.tremor(self.seconds(), 4, 2, 7.0)
        self.assertAlmostEqual(float(np.sqrt(np.mean(values ** 2))), 1.0, delta=0.1)
        self.assertTrue(np.array_equal(values, cs.tremor(self.seconds(), 4, 2, 7.0)))
        self.assertFalse(np.allclose(values, cs.tremor(self.seconds(), 5, 2, 7.0)))

    def test_tremor_shows_its_rate_in_frames_up_to_the_limit(self):
        """A broad-band noise sampled at 30 fps tops out at 7.5 swings a second; the tremor does not."""
        for hz in (3.0, 7.0, 10.0, 12.0):
            values = cs.tremor(self.seconds(18000), 2, 1, hz)
            swings = np.count_nonzero(np.diff(np.sign(values)) != 0) / (2.0 * 18000 / FPS)
            self.assertAlmostEqual(swings, hz, delta=0.1 * hz)
        broad = cs.noise(self.seconds(18000), 2, 1, 10.0)
        self.assertLess(np.count_nonzero(np.diff(np.sign(broad)) != 0) / (2.0 * 18000 / FPS), 8.0)

    def test_capped_below_nyquist(self):
        self.assertEqual(cs.capped(7.0, 30.0), 7.0)
        self.assertAlmostEqual(cs.capped(20.0, 24.0), 0.42 * 24.0)


class EnvelopeTests(unittest.TestCase):

    def test_smootherstep(self):
        self.assertEqual(float(cs.smootherstep(-1.0)), 0.0)
        self.assertEqual(float(cs.smootherstep(2.0)), 1.0)
        self.assertAlmostEqual(float(cs.smootherstep(0.5)), 0.5)

    def test_eased(self):
        frames = np.arange(10, 41)
        env = cs.eased(frames, 10, 40, 6)
        self.assertEqual(env[0], 0.0)
        self.assertEqual(env[-1], 0.0)
        self.assertTrue(np.all(env[6:25] == 1.0))
        self.assertTrue(np.all(np.diff(env[:7]) >= 0))
        self.assertTrue(np.all(cs.eased(frames, 10, 40, 0) == 1.0))

    def test_an_ease_longer_than_half_the_range_meets_in_the_middle(self):
        env = cs.eased(np.arange(0, 11), 0, 10, 30)
        self.assertEqual(env[5], 1.0)
        self.assertEqual(env[0], 0.0)


class HandheldTests(unittest.TestCase):

    def run_it(self, a=0, b=4000, **given):
        s = cs.settings("handheld", dict({"ease": 0.0}, **given))
        frames = np.arange(a, b + 1)
        return cs.handheld(frames, a, b, FPS, s)

    def test_sway_is_two_rms_of_pan(self):
        rot, _ = self.run_it(sway=2.0, jitter=0.0)
        self.assertAlmostEqual(rms2(rot[:, 1]), 2.0, delta=0.3)

    def test_tilt_is_three_quarters_and_roll_follows_roll(self):
        rot, _ = self.run_it(sway=2.0, jitter=0.0, roll=0.5)
        self.assertAlmostEqual(rms2(rot[:, 0]) / 2.0, 0.75, delta=0.15)
        self.assertAlmostEqual(rms2(rot[:, 2]) / 2.0, 0.5, delta=0.1)
        rot, _ = self.run_it(sway=2.0, jitter=0.5, roll=0.0)
        self.assertTrue(np.all(rot[:, 2] == 0.0))

    def test_jitter_alone_is_fast(self):
        rot, _ = self.run_it(sway=0.0, jitter=0.4)
        self.assertAlmostEqual(rms2(rot[:, 1]), 0.4, delta=0.06)
        crossings = np.count_nonzero(np.diff(np.sign(rot[:, 1])) != 0) / (4000 / FPS)
        self.assertGreater(crossings, 1.6 * cs.settings("handheld")["jitter_hz"])

    def rate(self, rot):
        """Swings a second of the pan: half its zero crossings."""
        return np.count_nonzero(np.diff(np.sign(rot[:, 1])) != 0) / (2.0 * len(rot) / FPS)

    def test_jitter_hz_sets_the_tremors_rate(self):
        for hz in (3.0, 9.0):
            rot, _ = self.run_it(sway=0.0, jitter=0.4, jitter_hz=hz)
            self.assertAlmostEqual(self.rate(rot), hz, delta=0.2 * hz)

    def test_speed_leaves_the_jitter_alone(self):
        slow, _ = self.run_it(sway=0.0, jitter=0.4, speed=0.5)
        fast, _ = self.run_it(sway=0.0, jitter=0.4, speed=3.0)
        self.assertTrue(np.allclose(slow, fast))

    def test_the_jitter_never_aliases(self):
        rot, _ = self.run_it(sway=0.0, jitter=0.4, jitter_hz=15.0)
        self.assertLess(self.rate(rot), 1.2 * cs.NYQUIST_SHARE * FPS)

    def test_drift_moves_the_camera_mostly_up_and_down(self):
        _, off = self.run_it(drift=4.0)
        self.assertAlmostEqual(rms2(off[:, 1]), 4.0, delta=0.7)
        self.assertLess(rms2(off[:, 2]), rms2(off[:, 0]))
        _, off = self.run_it(drift=0.0)
        self.assertTrue(np.all(off == 0.0))

    def test_scaling_sway_keeps_the_shape(self):
        one, _ = self.run_it(b=300, sway=1.0, jitter=0.0)
        two, _ = self.run_it(b=300, sway=2.0, jitter=0.0)
        self.assertTrue(np.allclose(two, 2.0 * one))

    def test_speed_raises_the_rate(self):
        slow, _ = self.run_it(sway=1.0, jitter=0.0, speed=0.5)
        fast, _ = self.run_it(sway=1.0, jitter=0.0, speed=3.0)
        rate = lambda v: np.count_nonzero(np.diff(np.sign(v[:, 1])) != 0)
        self.assertGreater(rate(fast), 2.0 * rate(slow))

    def test_seed_and_camera_index_change_the_shape(self):
        s = cs.settings("handheld")
        frames = np.arange(0, 200)
        one, _ = cs.handheld(frames, 0, 199, FPS, s)
        other, _ = cs.handheld(frames, 0, 199, FPS, dict(s, seed=2))
        second, _ = cs.handheld(frames, 0, 199, FPS, s, index=1)
        self.assertFalse(np.allclose(one, other))
        self.assertFalse(np.allclose(one, second))

    def test_axes_switch_off_whole(self):
        rot, off = self.run_it(b=300, sway=2.0, jitter=0.5, pan_on=False)
        self.assertTrue(np.all(rot[:, 1] == 0.0))
        self.assertGreater(np.abs(rot[:, 0]).max(), 0.1)
        self.assertGreater(np.abs(off).max(), 0.1)
        rot, _ = self.run_it(b=300, sway=2.0, jitter=0.5, tilt_on=False, roll_on=False)
        self.assertTrue(np.all(rot[:, 0] == 0.0) and np.all(rot[:, 2] == 0.0))

    def test_eased_in_and_out(self):
        s = cs.settings("handheld", {"ease": 8.0})
        rot, off = cs.handheld(np.arange(20, 121), 20, 120, FPS, s)
        self.assertTrue(np.all(rot[0] == 0.0) and np.all(rot[-1] == 0.0))
        self.assertTrue(np.all(off[0] == 0.0) and np.all(off[-1] == 0.0))
        self.assertGreater(np.abs(rot[50]).max(), 0.0)


class ImpactTests(unittest.TestCase):

    def run_it(self, a=40, b=70, **given):
        s = cs.settings("impact", dict({"rattle": 0.0}, **given))
        frames = np.arange(a, b + 1)
        return frames, cs.impact(frames, a, b, FPS, s)

    def fine(self, wave=8.0, span=40.0, decay="Exponential", rate=1.0):
        tau = np.linspace(0.0, span, 8001)
        return tau, cs.waves(tau, wave, span, decay, rate)

    def test_waves_are_zero_at_the_hit_and_one_at_their_first_crest(self):
        for decay in cs.DECAYS:
            tau, x = self.fine(decay=decay)
            self.assertEqual(x[0], 0.0)
            self.assertAlmostEqual(float(x.max()), 1.0, places=5)   # samples 0.005 fr apart straddle the top
            self.assertLess(tau[int(np.argmax(x))], 2.0 + 1e-9)     # by a quarter of the wave
            self.assertEqual(x[-1], 0.0)                              # gone at the end of the range

    def test_wave_is_the_period_crest_to_crest(self):
        for wave in (6.0, 12.0):
            tau, x = self.fine(wave=wave, span=60.0, decay="Linear")
            crossings = tau[1:][np.diff(np.sign(x)) != 0]
            spacing = float(np.median(np.diff(crossings)))
            self.assertAlmostEqual(spacing, wave / 2.0, delta=0.02)

    def test_decay_types(self):
        u = np.linspace(0.0, 1.0, 1001)
        for decay in cs.DECAYS:
            env = cs.envelope(u, decay)
            self.assertAlmostEqual(float(env[0]), 1.0)
            self.assertAlmostEqual(float(env[-1]), 0.0)
            self.assertTrue(np.all(np.diff(env) <= 1e-12), decay)
        at = lambda decay, x: float(cs.envelope(x, decay))
        self.assertAlmostEqual(at("Linear", 0.5), 0.5)
        self.assertGreater(at("Smooth", 0.2), 0.85)                  # holds the strength first
        self.assertLess(at("Sharp", 0.5), 0.05)                      # gone within the first waves
        self.assertGreater(at("Exponential", 0.8), 0.005)            # a long thin tail
        self.assertLess(at("Exponential", 0.3), at("Linear", 0.3))   # falls fast at first
        self.assertAlmostEqual(at("Unknown", 0.5), at("Exponential", 0.5))

    def test_waves_never_alias(self):
        tau, x = self.fine(wave=0.5, span=30.0, decay="Linear")
        crossings = tau[1:][np.diff(np.sign(x)) != 0]
        self.assertGreaterEqual(float(np.median(np.diff(crossings))), cs.MIN_WAVE / 2.0 - 0.01)

    def test_the_wave_and_the_decay_change_the_ringing(self):
        frames = np.arange(0, 61)
        def pan(**given):
            s = cs.settings("impact", dict({"rattle": 0.0, "direction": "Left", "roll": 0.0}, **given))
            return cs.impact(frames, 0, 60, FPS, s)[0][:, 1]
        short = pan(wave=6.0)
        long = pan(wave=16.0)
        swings = lambda v: np.count_nonzero(np.diff(np.sign(v[1:])) != 0)
        self.assertGreater(swings(short), swings(long) + 3)
        late = lambda v: np.abs(v[30:]).max()
        self.assertGreater(late(pan(decay="Smooth")), 3.0 * late(pan(decay="Sharp")))

    def test_still_at_the_hit_and_at_the_end(self):
        for decay in cs.DECAYS:
            _, (rot, off) = self.run_it(rattle=2.0, direction="Left", decay=decay)
            self.assertTrue(np.all(rot[0] == 0.0) and np.all(off[0] == 0.0))
            self.assertTrue(np.all(rot[-1] == 0.0) and np.all(off[-1] == 0.0))
            self.assertLess(np.abs(rot[-2]).max(), 0.5, decay)

    def test_from_below_turns_the_view_up_by_the_strength(self):
        _, (rot, off) = self.run_it(strength=5.0, direction="Below", roll=0.0, push=3.0)
        i = int(np.argmax(rot[:, 0]))
        self.assertGreater(rot[i, 0], 4.0)                    # about +X: the view tilts up
        self.assertLessEqual(i, 3)
        self.assertAlmostEqual(rot[i, 1], 0.0, delta=1.3)     # the wobble only
        self.assertGreater(off[i, 1], 2.0)                    # knocked up
        self.assertAlmostEqual(off[i, 0], 0.0)

    def test_from_the_left_pans_right_and_rolls_the_top_right(self):
        _, (rot, off) = self.run_it(strength=5.0, direction="Left", roll=0.5, push=2.0)
        i = 2
        self.assertLess(rot[i, 1], -3.0)      # about -Y: the view turns to +X
        self.assertLess(rot[i, 2], -1.0)      # about -Z: the top to +X
        self.assertGreater(off[i, 0], 1.0)    # knocked right
        _, (mirror, _) = self.run_it(strength=5.0, direction="Right", roll=0.5, push=2.0)
        self.assertGreater(mirror[i, 1], 3.0)
        self.assertGreater(mirror[i, 2], 1.0)

    def test_from_the_front_pushes_back_and_kicks_up(self):
        _, (rot, off) = self.run_it(strength=3.0, direction="Front", push=2.0)
        self.assertGreater(off[2, 2], 1.0)
        self.assertGreater(rot[2, 0], 2.0)

    def test_rattle_hz_sets_the_rattles_rate(self):
        frames = np.arange(0, 3001)
        def rate(hz):
            s = cs.settings("impact", {"strength": 0.0, "push": 0.0, "rattle": 3.0, "rattle_hz": hz,
                                       "decay": "Linear"})
            rot = cs.impact(frames, 0, 3000, FPS, s)[0][1:300, 1]
            return np.count_nonzero(np.diff(np.sign(rot)) != 0) / (2.0 * len(rot) / FPS)
        self.assertGreater(rate(10.0), 2.0 * rate(3.0))

    def test_axes_switch_off_whole(self):
        _, (rot, off) = self.run_it(rattle=2.0, direction="Left", roll=0.5, pan_on=False, roll_on=False)
        self.assertTrue(np.all(rot[:, 1] == 0.0) and np.all(rot[:, 2] == 0.0))
        self.assertGreater(np.abs(rot[:, 0]).max(), 0.1)          # the wobble and the rattle still tilt
        self.assertGreater(np.abs(off[:, 0]).max(), 1.0)          # the push is a move, not a turn
        _, (rot, _) = self.run_it(rattle=2.0, direction="Below", tilt_on=False)
        self.assertTrue(np.all(rot[:, 0] == 0.0))

    def test_random_is_seeded(self):
        a = cs.hit_vector("Random", 3)
        self.assertTrue(np.allclose(a, cs.hit_vector("Random", 3)))
        self.assertFalse(np.allclose(a, cs.hit_vector("Random", 4)))
        self.assertAlmostEqual(float(np.linalg.norm(a)), 1.0)
        self.assertEqual(a[2], 0.0)

    def test_picture_direction(self):
        self.assertTrue(np.allclose(cs.picture_direction((0.0, 0.0, 1.0)), (0.0, 1.0)))
        self.assertTrue(np.allclose(cs.picture_direction((3.0, 4.0, 0.0)), (0.6, 0.8)))

    def test_rattle_is_loud_early_and_gone_late(self):
        a, b = 0, 120
        s = cs.settings("impact", {"strength": 0.0, "push": 0.0, "rattle": 3.0})
        frames = np.arange(a, b + 1)
        rot, _ = cs.impact(frames, a, b, FPS, s)
        early = np.abs(rot[1:20]).max()
        late = np.abs(rot[100:]).max()
        self.assertGreater(early, 0.5)
        self.assertLess(late, 0.1 * early)
        self.assertTrue(np.all(rot[0] == 0.0))


try:
    import maya.api.OpenMaya as om
except ImportError:
    om = None

VIEW = np.array([0.0, 0.0, -1.0])    # a camera looks down its own -Z


def maya_matrix(degrees, order):
    rotation = om.MEulerRotation([math.radians(v) for v in degrees], cs.ORDERS.index(order))
    m = rotation.asMatrix()
    return np.array([[m.getElement(r, c) for c in range(3)] for r in range(3)])


class AlgebraTests(unittest.TestCase):

    def angles(self, n=40, seed=0):
        return np.random.default_rng(seed).uniform(-200.0, 200.0, size=(n, 3))

    @unittest.skipIf(om is None, "OpenMaya is needed to compare")
    def test_euler_matrix_is_mayas_on_every_order(self):
        for order in cs.ORDERS:
            for degrees in self.angles():
                ours = cs.euler_matrix(np.radians(degrees), order)
                self.assertTrue(np.allclose(ours, maya_matrix(degrees, order), atol=1e-12), order)

    def test_both_solutions_give_the_matrix(self):
        for order in cs.ORDERS:
            for degrees in self.angles(seed=1):
                m = cs.euler_matrix(np.radians(degrees), order)
                for solution in cs.matrix_eulers(m, order):
                    self.assertTrue(np.allclose(cs.euler_matrix(solution, order), m, atol=1e-10), order)

    def test_gimbal_lock_still_gives_the_matrix(self):
        for order in cs.ORDERS:
            degrees = [0.0, 0.0, 0.0]
            degrees["xyz".index(order[1])] = 90.0
            degrees["xyz".index(order[0])] = 30.0
            m = cs.euler_matrix(np.radians(degrees), order)
            for solution in cs.matrix_eulers(m, order):
                self.assertTrue(np.allclose(cs.euler_matrix(solution, order), m, atol=1e-9), order)

    def test_closest_follows_the_base_across_the_seam(self):
        base = np.radians([179.0, -10.0, 720.0 + 30.0])
        m = cs.euler_matrix(base + np.radians([2.0, 0.5, -1.0]), "xyz")
        got = np.degrees(cs.closest(cs.matrix_eulers(m, "xyz"), base))
        self.assertTrue(np.allclose(got, [181.0, -9.5, 749.0], atol=1e-9))

    def test_a_zero_shake_is_the_base(self):
        for order in cs.ORDERS:
            for degrees in self.angles(5, seed=2):
                got = cs.shaken(degrees, order, (0.0, 0.0, 0.0), (10.0, -20.0, 5.0))
                self.assertTrue(np.allclose(got, degrees, atol=1e-9))

    def test_a_tilt_turns_the_view_up_in_the_cameras_own_axes(self):
        rng = np.random.default_rng(3)
        for order in cs.ORDERS:
            base = rng.uniform(-90, 90, 3)
            axis = (12.0, -7.0, 3.0)
            got = cs.shaken(base, order, (5.0, 0.0, 0.0), axis)
            frame = cs.euler_matrix(np.radians(axis), "xyz")
            before = frame @ cs.euler_matrix(np.radians(base), order)
            after = frame @ cs.euler_matrix(np.radians(got), order)
            # In the camera's own frame before the shake, the new view points up by 5 degrees.
            seen = VIEW @ after @ before.T
            self.assertAlmostEqual(math.degrees(math.asin(seen[1])), 5.0, places=9)
            self.assertAlmostEqual(seen[0], 0.0, places=9)

    def test_a_turn_about_each_axis(self):
        frame = np.eye(3)
        pan = cs.euler_matrix(np.radians(cs.shaken((0, 0, 0), "xyz", (0.0, -10.0, 0.0))), "xyz")
        self.assertGreater((VIEW @ pan)[0], 0.17)                  # about -Y: the view to +X
        roll = cs.euler_matrix(np.radians(cs.shaken((0, 0, 0), "xyz", (0.0, 0.0, -10.0))), "xyz")
        self.assertGreater((np.array([0.0, 1.0, 0.0]) @ roll)[0], 0.17)   # about -Z: the top to +X

    def test_rotation_from_vector(self):
        self.assertTrue(np.allclose(cs.rotation_from_vector(np.radians([30.0, 0, 0])),
                                    cs.euler_matrix(np.radians([30.0, 0, 0]), "xyz")))
        self.assertTrue(np.allclose(cs.rotation_from_vector((0, 0, 0)), np.eye(3)))

    def test_along_axes(self):
        moved = cs.along_axes((1.0, 0.0, 0.0), (0.0, 90.0, 0.0), "xyz")
        self.assertTrue(np.allclose(moved, (0.0, 0.0, -1.0)))
        with_orient = cs.along_axes((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), "xyz", joint_orient_deg=(0.0, 90.0, 0.0))
        self.assertTrue(np.allclose(with_orient, (0.0, 0.0, -1.0)))

    def test_a_joint_orient_does_not_change_the_turn(self):
        rot = np.array([[2.0, -3.0, 1.0]])
        off = np.zeros((1, 3))
        base = np.array([[10.0, 20.0, 30.0]])
        plain, _ = cs.deltas(rot, off, base, "yzx")
        oriented, _ = cs.deltas(rot, off, base, "yzx", joint_orient=(40.0, 0.0, -15.0))
        self.assertTrue(np.allclose(plain, oriented))

    def test_deltas_put_the_shake_on_top_of_the_base(self):
        rng = np.random.default_rng(4)
        base = rng.uniform(-170, 170, (20, 3))
        rot = rng.uniform(-6, 6, (20, 3))
        off = rng.uniform(-3, 3, (20, 3))
        dr, dt = cs.deltas(rot, off, base, "zxy", (5.0, 0.0, -8.0))
        for i in range(20):
            expect = cs.shaken(base[i], "zxy", rot[i], (5.0, 0.0, -8.0))
            self.assertTrue(np.allclose(base[i] + dr[i], expect))
            self.assertLess(np.abs(dr[i]).max(), 30.0)
            self.assertTrue(np.allclose(dt[i], cs.along_axes(off[i], base[i], "zxy", (5.0, 0.0, -8.0))))


class RecordTests(unittest.TestCase):

    def test_layer_name(self):
        self.assertEqual(cs.layer_name("impact", 45, 70), "CamShake_Impact_45_70")
        self.assertEqual(cs.layer_name("handheld", -5, 20), "CamShake_Handheld_m5_20")

    def test_record_round_trip(self):
        s = cs.settings("impact", {"direction": "Left"})
        text = cs.record_text("impact", s, 3, 30, ["AAA", "BBB"])
        rec = cs.parse_record(text)
        self.assertEqual(rec["mode"], "impact")
        self.assertEqual(rec["frames"], [3, 30])
        self.assertEqual(rec["targets"], ["AAA", "BBB"])
        self.assertEqual(rec["settings"]["direction"], "Left")

    def test_bad_records_are_none(self):
        for text in ("", "{", '{"version": 2}', '{"version": 1, "mode": "x"}', None):
            self.assertIsNone(cs.parse_record(text))


class FakeCmds(object):
    """Just enough of maya.cmds for the card: controls remember what they were made and edited with,
    queries answer it, menus hold their items, a radio button lights alone in its collection."""

    def __init__(self):
        self.controls = {}
        self.options = {}
        self.jobs = {}
        self.killed = []
        self.count = 0

    def _name(self, kind, args):
        if args and isinstance(args[0], str):
            return args[0]
        self.count += 1
        return "%s%d" % (kind, self.count)

    def _control(self, kind, args, kw):
        name = self._name(kind, args)
        if kw.get("exists"):
            return name in self.controls
        if kw.get("query") or kw.get("q"):
            props = self.controls[name]
            for key, flag in kw.items():
                if key not in ("query", "q") and flag is True:
                    if key == "itemListLong":
                        return list(props.get("items", []))
                    return props.get(key)
            return None
        if kw.get("edit") or kw.get("e"):
            self.controls[name].update({k: v for k, v in kw.items() if k not in ("edit", "e")})
            return name
        self.controls[name] = dict(kw, kind=kind, items=[])
        return name

    def __getattr__(self, kind):
        if kind in ("rowLayout", "flowLayout", "columnLayout", "text", "button", "intField", "floatSliderGrp",
                    "checkBox", "iconTextRadioCollection"):
            return lambda *args, **kw: self._control(kind, args, kw)
        raise AttributeError(kind)

    def setParent(self, *args, **kw):
        return None

    def iconTextRadioButton(self, *args, **kw):
        name = self._control("iconTextRadioButton", args, kw)
        if (kw.get("edit") or kw.get("select")) and kw.get("select") and isinstance(name, str):
            group = self.controls[name].get("collection")
            for other, props in self.controls.items():
                if other != name and props.get("kind") == "iconTextRadioButton" and \
                        props.get("collection") == group:
                    props["select"] = False
        return name

    def optionMenu(self, *args, **kw):
        name = self._name("optionMenu", args)
        if (kw.get("edit") or kw.get("e")) and "value" in kw:
            labels = [self.controls[item]["label"] for item in self.controls[name]["items"]]
            assert kw["value"] in labels, (kw["value"], labels)
        if (kw.get("query") or kw.get("q")) and kw.get("value"):
            props = self.controls[name]
            if props.get("value") is None and props["items"]:
                return self.controls[props["items"][0]]["label"]
            return props.get("value")
        return self._control("optionMenu", args, kw)

    def menuItem(self, *args, **kw):
        parent = kw.pop("parent")
        name = self._control("menuItem", args, kw)
        self.controls[parent]["items"].append(name)
        return name

    def deleteUI(self, *names, **kw):
        for name in names:
            for props in self.controls.values():
                if name in props.get("items", []):
                    props["items"].remove(name)
            self.controls.pop(name, None)

    def scriptJob(self, *args, **kw):
        if "exists" in kw:
            return kw["exists"] in self.jobs
        if "kill" in kw:
            self.killed.append(kw["kill"])
            self.jobs.pop(kw["kill"], None)
            return None
        number = len(self.jobs) + len(self.killed) + 1
        self.jobs[number] = kw
        return number

    def optionVar(self, *args, **kw):
        if "exists" in kw:
            return kw["exists"] in self.options
        if "query" in kw:
            return self.options.get(kw["query"])
        if "stringValue" in kw:
            key, value = kw["stringValue"]
            self.options[key] = value
        return None


LAYER = "CamShake_Impact_40_60"


class CardTests(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.saved = {name: getattr(cs, name) for name in
                      ("cmds", "apply", "retune", "delete", "picked", "pick", "record", "shakes", "targets",
                       "frames_for", "editor_pick", "_node_names")}
        cs.cmds = self.fake
        self.calls = []
        self.current = None
        cs.picked = lambda: self.current
        cs.pick = lambda layer: setattr(self, "current", layer)
        cs.record = lambda layer: {"mode": "impact", "frames": [40, 60], "targets": ["U"],
                                   "settings": cs.settings("impact", {"strength": 7.0, "direction": "Left",
                                                                      "decay": "Smooth", "pan_on": False})} \
            if layer else None
        cs.shakes = lambda: [LAYER]
        cs.targets = lambda selection=None: ["|cam"]
        cs.frames_for = lambda mode, s, given=None: (0, 50, "the playback range")
        cs.editor_pick = lambda: None
        cs.apply = lambda mode, given=None, selection=None, frames=None: (
            self.calls.append(("apply", mode, given)) or (LAYER, "applied"))
        cs.retune = lambda layer, given: self.calls.append(("retune", layer, given)) or "re-tuned"
        cs.delete = lambda layer: self.calls.append(("delete", layer)) or "deleted"
        cs._node_names = lambda found: "cam"
        cs.build_panel()

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(cs, name, value)
        cs._QUIET[0] = False
        cs.JOB.clear()
        cs._state().pop("editor", None)

    def control(self, name):
        return self.fake.controls[name]

    def slider(self, mode, name):
        return self.control(cs._slider(mode, name))

    def test_builds_every_control(self):
        for mode in cs.MODES:
            self.assertIn(cs._mode_tab(mode), self.fake.controls)
            self.assertIn(cs._mode_column(mode), self.fake.controls)
            for name, _, _, _, _ in cs.CONTROLS[mode]:
                self.assertIn(cs._slider(mode, name), self.fake.controls)
        for key, _ in cs.AXES:
            self.assertEqual(self.control(cs._axis_chip(key))["kind"], "checkBox")
        for name in (cs.SUBTITLE, cs.SHAKE_MENU, cs.DELETE_BTN, cs.PRESET_MENU, cs.DIRECTION_MENU,
                     cs.DECAY_MENU, cs.SEED_FIELD, cs.SEED_BTN, cs.APPLY_BTN, cs.STATUS):
            self.assertIn(name, self.fake.controls)
        events = sorted(job["event"][0] for job in self.fake.jobs.values())
        self.assertEqual(events, ["Redo", "SelectionChanged", "Undo", "animLayerRefresh"])
        self.assertTrue(all(job["parent"] == cs.STATUS for job in self.fake.jobs.values()))

    def test_every_control_a_popup_copy_can_scope(self):
        """A popup copy renames only the commands maya_hubcopy knows (checkBoxGrp / radioButtonGrp are not
        among them): the card makes nothing else under a name."""
        import maya_hubcopy
        named = {props["kind"] for name, props in self.fake.controls.items()
                 if not name.startswith(props["kind"])}
        self.assertTrue(named <= maya_hubcopy.CREATORS, named - maya_hubcopy.CREATORS)

    def test_the_mode_shown_is_the_one_remembered(self):
        self.assertEqual(cs.current_mode(), "handheld")
        self.assertTrue(self.control(cs._mode_column("handheld"))["manage"])
        self.assertFalse(self.control(cs._mode_column("impact"))["manage"])

    def test_a_preset_fills_the_sliders_and_sets_up_the_next_apply(self):
        self.control(cs.PRESET_MENU)["value"] = "Nervous"
        cs.preset_changed()
        self.assertEqual(self.slider("handheld", "sway")["value"], 1.8)
        self.assertEqual(self.slider("handheld", "jitter_hz")["value"], 9.5)
        self.assertEqual(self.control(cs.PRESET_MENU)["value"], cs.PRESET_PROMPT)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.control(cs.STATUS)["label"], "Set for the next Apply.")

    def test_picking_a_shake_loads_it_and_a_slider_re_keys_it(self):
        self.control(cs.SHAKE_MENU)["value"] = "%s - cam" % LAYER
        cs.shake_changed()
        self.assertEqual(self.current, LAYER)
        self.assertEqual(cs.current_mode(), "impact")
        self.assertTrue(self.control(cs._mode_column("impact"))["manage"])
        self.assertEqual(self.slider("impact", "strength")["value"], 7.0)
        self.assertFalse(self.control(cs._axis_chip("pan_on"))["value"])
        self.assertEqual(self.control(cs.DECAY_MENU)["value"], "Smooth")
        self.slider("impact", "strength")["value"] = 9.0
        cs.slider_changed("impact")()
        verb, layer, given = self.calls[-1]
        self.assertEqual((verb, layer), ("retune", LAYER))
        self.assertEqual((given["strength"], given["direction"], given["decay"], given["pan_on"]),
                         (9.0, "Left", "Smooth", False))
        self.assertEqual(self.control(cs.STATUS)["label"], "re-tuned")
        self.assertIn("Editing %s" % LAYER, self.control(cs.SUBTITLE)["label"])

    def test_apply_applies_what_the_card_reads(self):
        self.slider("handheld", "sway")["value"] = 2.5
        self.control(cs._axis_chip("roll_on"))["value"] = False
        cs.press_apply()
        verb, mode, given = self.calls[-1]
        self.assertEqual((verb, mode, given["sway"], given["roll_on"]), ("apply", "handheld", 2.5, False))
        self.assertEqual(self.control(cs.STATUS)["label"], "applied")

    def test_switching_mode_unpicks(self):
        self.current = LAYER
        cs.mode_changed("impact")()
        self.assertIsNone(self.current)
        self.assertEqual(cs.current_mode(), "impact")
        self.assertTrue(self.control(cs._mode_column("impact"))["manage"])
        self.assertFalse(self.control(cs._mode_column("handheld"))["manage"])
        labels = [self.fake.controls[item]["label"] for item in self.control(cs.PRESET_MENU)["items"]]
        self.assertEqual(labels, [cs.PRESET_PROMPT] + [label for label, _ in cs.PRESETS["impact"]])

    def test_settings_are_remembered_per_mode(self):
        self.slider("handheld", "jitter")["value"] = 0.9
        cs.slider_changed("handheld")()
        self.assertEqual(cs.remembered("handheld")["jitter"], 0.9)
        self.assertNotIn("jitter", cs.remembered("impact"))

    def test_delete_needs_a_picked_shake(self):
        cs.press_delete()
        self.assertEqual(self.calls, [])
        self.current = LAYER
        cs.press_delete()
        self.assertEqual(self.calls[-1], ("delete", LAYER))

    def test_a_layer_selected_in_the_editor_is_picked_once(self):
        cs.editor_pick = lambda: LAYER
        cs.from_editor()
        self.assertEqual(self.current, LAYER)
        self.assertEqual(self.slider("impact", "strength")["value"], 7.0)
        self.current = None                    # the animator picks + New in the card
        cs.from_editor()                       # the same layer still selected in the editor
        self.assertIsNone(self.current)

    def test_a_new_seed_re_keys_the_picked_shake(self):
        self.current = LAYER
        cs._load(LAYER)
        before = self.control(cs.SEED_FIELD)["value"]
        cs.press_new_seed()
        self.assertEqual(self.calls[-1][0], "retune")
        self.assertNotEqual(self.calls[-1][2]["seed"], before)

    def test_with_the_card_closed_a_press_uses_the_remembered_settings(self):
        self.slider("handheld", "drift")["value"] = 4.0
        cs.slider_changed("handheld")()
        self.fake.controls.clear()
        self.assertFalse(cs.is_open())
        message = cs.press_apply()
        self.assertEqual(message, "applied")
        self.assertEqual(self.calls[-1][2]["drift"], 4.0)

    def test_a_refusal_is_the_status(self):
        def refuse(*args, **kwargs):
            raise cs.Refused("select a camera to shake")
        cs.apply = refuse
        self.assertEqual(cs.press_apply(), "select a camera to shake")

    def test_the_hub_opens_on_the_card(self):
        import maya_hub
        self.assertEqual(maya_hub.section(cs.HUB_SECTION).module, "maya_camshake")
        self.assertEqual(maya_hub.section(cs.HUB_SECTION).group, "animation")


if __name__ == "__main__":
    unittest.main()

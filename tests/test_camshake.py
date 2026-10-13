"""Camera Shake: the model, the rotation algebra and the window, without a scene."""

import importlib.util
import math
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "camshake")
SCRIPT = os.path.join(FOLDER, "skeldar_camshake.py")


def load():
    spec = importlib.util.spec_from_file_location("skeldar_camshake_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cs = load()

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
        self.assertGreater(crossings, 1.6 * cs.JITTER_HZ)

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

    def crest(self, swing, bounce):
        tau = np.linspace(0, 3 * swing, 3001)
        x = cs.kick(tau, swing, bounce)
        return tau[int(np.argmax(x))], float(np.max(x))

    def test_kick_is_zero_at_the_hit_and_one_at_its_crest(self):
        self.assertEqual(float(cs.kick(0.0, 4.0, 0.5)), 0.0)
        when, top = self.crest(4.0, 0.5)
        self.assertAlmostEqual(top, 1.0, places=4)
        self.assertLess(when, 4.0)

    def test_bounce_overshoots_more(self):
        tau = np.linspace(0, 12, 4001)
        dead = cs.kick(tau, 4.0, 0.0)
        ring = cs.kick(tau, 4.0, 1.0)
        self.assertLess(dead.min(), 0.0)          # still underdamped
        self.assertLess(ring.min(), 3.0 * dead.min())

    def test_still_at_the_hit_and_at_the_end(self):
        _, (rot, off) = self.run_it(rattle=2.0, direction="Left")
        self.assertTrue(np.all(rot[0] == 0.0) and np.all(off[0] == 0.0))
        self.assertTrue(np.all(rot[-1] == 0.0) and np.all(off[-1] == 0.0))
        self.assertLess(np.abs(rot[-2]).max(), 0.05)

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


if __name__ == "__main__":
    unittest.main()

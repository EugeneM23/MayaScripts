"""Camera Shake's Bobbing (2026-10-28): the gait formula, the step shapes, the model, the heading frame and the
card's tab, without a scene."""

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
from tests.test_camshake import FakeCmds  # noqa: E402

FPS = 30.0


def plain(**given):
    """Bobbing settings with nothing on but what is given."""
    base = {"bob": 0.0, "side": 0.0, "nod": 0.0, "turn": 0.0, "lean": 0.0, "footfall": 0.0, "variation": 0.0,
            "ease": 0.0, "contact": 0.0, "tempo": 120.0, "softness": 50.0}
    base.update(given)
    return cs.settings("bobbing", base)


def pp(values):
    return float(np.max(values) - np.min(values))


class FormulaTests(unittest.TestCase):

    def test_walk_reads_the_guides_table(self):
        s = cs.from_speed(1.32)
        self.assertEqual(s["gait"], "Walk")
        self.assertAlmostEqual(s["tempo"], 116.0, places=1)
        self.assertAlmostEqual(cs.from_speed(1.6)["bob"], 4.83, places=2)
        self.assertAlmostEqual(cs.from_speed(1.6)["side"], 3.85, places=2)
        self.assertAlmostEqual(cs.from_speed(1.6)["nod"], 4.83 * 3.58 / 5.43, places=2)
        self.assertEqual(s["turn"], 2.85)

    def test_run_past_the_transition(self):
        self.assertEqual(cs.from_speed(2.0)["gait"], "Walk")
        s = cs.from_speed(2.5)
        self.assertEqual((s["gait"], s["tempo"], s["bob"], s["softness"], s["turn"]), ("Run", 162.0, 8.9, 78.3, 6.1))
        self.assertGreater(cs.from_speed(7.0)["tempo"], cs.from_speed(4.5)["tempo"])
        self.assertLess(cs.from_speed(7.0)["softness"], cs.from_speed(2.5)["softness"])

    def test_the_speed_is_remembered(self):
        self.assertEqual(cs.from_speed(3.456)["pace"], 3.46)

    def test_every_preset_and_the_default(self):
        labels = [label for label, _ in cs.PRESETS["bobbing"]]
        self.assertEqual(labels, ["Slow walk", "Walk", "Fast walk", "Jog", "Run", "Sprint", "Sneak", "Heavy", "Tired"])
        default = cs.settings("bobbing")
        walk = cs.preset("bobbing", "Walk", default)
        for key in ("pace", "tempo", "bob", "side", "nod", "turn", "softness", "gait"):
            self.assertEqual(default[key], walk[key], key)

    def test_style_presets_scale_the_formula(self):
        sneak = cs.preset("bobbing", "Sneak")
        base = cs.from_speed(0.8)
        self.assertAlmostEqual(sneak["bob"], round(base["bob"] * 0.4, 2))
        self.assertEqual(sneak["footfall"], 0.0)
        self.assertGreater(cs.preset("bobbing", "Heavy")["footfall"], cs.preset("bobbing", "Walk")["footfall"])
        self.assertGreater(cs.preset("bobbing", "Tired")["variation"], cs.preset("bobbing", "Walk")["variation"])
        self.assertEqual(cs.preset("bobbing", "Sprint")["gait"], "Run")

    def test_a_preset_keeps_the_foot_the_contact_and_ease(self):
        s = cs.preset("bobbing", "Run", {"foot": "Right", "contact": 7.0, "ease": 12.0, "seed": 5})
        self.assertEqual((s["foot"], s["contact"], s["ease"], s["seed"]), ("Right", 7.0, 12.0, 5))

    def test_settings_fall_back(self):
        s = cs.settings("bobbing", {"gait": "Hop", "foot": "Middle", "tempo": 999})
        self.assertEqual((s["gait"], s["foot"], s["tempo"]), ("Walk", "Left", 300.0))


class ShapeTests(unittest.TestCase):

    def test_both_are_one_peak_to_peak_about_zero(self):
        for gait in cs.GAITS:
            for softness in (0.0, 0.5, 1.0):
                y = cs.step_curve(gait, softness)
                self.assertAlmostEqual(pp(y), 1.0, places=9)
                self.assertAlmostEqual(float(np.mean(y)), 0.0, places=9)

    def test_walk_is_low_after_the_contact_and_high_at_passing(self):
        y = cs.step_curve("Walk", 0.5)
        u = np.arange(cs.SAMPLES) / float(cs.SAMPLES)
        self.assertAlmostEqual(u[int(np.argmin(y))], cs.WALK_LOW, delta=0.02)
        self.assertAlmostEqual(u[int(np.argmax(y))], cs.WALK_LOW + 0.5, delta=0.02)

    def test_walk_is_fast_into_the_down_slow_over_the_up(self):
        """A pendulum's arc: the curve spends most of the step above its mean, its low a short dip."""
        y = cs.step_curve("Walk", 0.2)
        self.assertGreater(float(np.mean(y > 0.0)), 0.55)

    def test_softness_rounds_the_walks_low(self):
        def sharpness(softness):
            y = cs.step_curve("Walk", softness)
            i = int(np.argmin(y))
            return y[(i - 1) % len(y)] + y[(i + 1) % len(y)] - 2.0 * y[i]
        self.assertGreater(sharpness(0.0), 3.0 * sharpness(1.0))

    def test_run_is_low_mid_stance_and_high_mid_flight(self):
        for softness in (0.2, 0.5, 0.8):
            c = cs.stance_share(softness)
            y = cs.step_curve("Run", softness)
            u = np.arange(cs.SAMPLES) / float(cs.SAMPLES)
            self.assertAlmostEqual(u[int(np.argmin(y))], c / 2.0, delta=0.01)
            self.assertAlmostEqual(u[int(np.argmax(y))], c + (1.0 - c) / 2.0, delta=0.01)

    def test_run_has_no_corner_at_take_off_or_landing(self):
        y = cs.step_curve("Run", 0.5)
        d = np.diff(np.append(y, y[0]))
        c = int(round(cs.stance_share(0.5) * cs.SAMPLES))
        for i in (c, 0):
            self.assertAlmostEqual(d[i - 2], d[i + 1], delta=0.05 * abs(d[i - 2]) + 1e-4)

    def test_the_shape_is_periodic(self):
        self.assertAlmostEqual(float(cs.step_shape("Run", 0.5, 0.3)), float(cs.step_shape("Run", 0.5, 2.3)))


class BobbingTests(unittest.TestCase):
    STEP = 15                     # frames a step at 120 steps/min, 30 fps
    frames = np.arange(0, 241)

    def run_model(self, frames=None, **given):
        return cs.bobbing(self.frames if frames is None else frames, 0, 240, FPS, plain(**given))

    def test_bob_side_and_nod_are_their_sizes(self):
        """Read between the frames too: on whole frames a 15-frame step misses its low (1.5 fr after)."""
        rot, off = self.run_model(np.arange(0.0, 240.0, 0.125), bob=4.0, side=5.0, nod=3.0)
        self.assertAlmostEqual(pp(off[:, 1]), 4.0, delta=0.05)
        self.assertAlmostEqual(pp(off[:, 0]), 5.0, delta=0.05)
        self.assertAlmostEqual(pp(rot[:, 0]), 3.0, delta=0.05)

    def test_the_low_is_just_after_each_contact_and_the_nod_down_at_the_top(self):
        rot, off = self.run_model(bob=4.0, nod=3.0, contact=5.0)
        for contact in (5, 20, 35):
            window = slice(contact, contact + self.STEP)
            low = contact + int(np.argmin(off[window, 1]))
            self.assertLessEqual(low - contact, 3)
            top = contact + int(np.argmax(off[window, 1]))
            self.assertAlmostEqual(rot[top, 0], float(np.min(rot[:, 0])), places=6)

    def test_a_stride_repeats(self):
        rot, off = self.run_model(bob=4.0, side=5.0, nod=2.0, turn=3.0, lean=1.5, footfall=1.0)
        stride = 2 * self.STEP
        self.assertTrue(np.allclose(off[stride:stride + 60], off[2 * stride:2 * stride + 60]))
        self.assertTrue(np.allclose(rot[stride:stride + 60], rot[2 * stride:2 * stride + 60]))

    def test_the_first_foot_takes_the_sway_the_roll_and_the_turn(self):
        rot, off = self.run_model(np.arange(0.0, 240.0, 0.5), side=5.0, lean=2.0, turn=3.0)
        mid = int(2 * cs.WALK_SIDE_PEAK * self.STEP)          # half frames: 7.5 fr is index 15
        self.assertAlmostEqual(off[mid, 0], -2.5, places=6)       # over the left foot: to the left
        self.assertAlmostEqual(rot[mid, 2], 1.0, places=6)        # the top toward it
        self.assertAlmostEqual(rot[0, 1], 1.5, places=6)          # looking toward the striking left foot
        self.assertAlmostEqual(off[mid + 2 * self.STEP, 0], 2.5, places=6)   # then over the right
        right_rot, right_off = self.run_model(np.arange(0.0, 240.0, 0.5), side=5.0, lean=2.0, turn=3.0,
                                              foot="Right")
        self.assertAlmostEqual(right_off[mid, 0], 2.5, places=6)
        self.assertAlmostEqual(right_rot[0, 1], -1.5, places=6)

    def test_a_runs_sway_peaks_mid_stance(self):
        _, off = self.run_model(side=5.0, gait="Run", softness=50.0)
        peak = 0.5 * cs.stance_share(0.5) * self.STEP
        self.assertAlmostEqual(int(np.argmin(off[:self.STEP, 0])), peak, delta=1.0)

    def test_the_footfall_jolts_down_after_each_contact(self):
        rot, off = self.run_model(footfall=2.0, contact=10.0)
        window = slice(10, 10 + self.STEP)
        self.assertAlmostEqual(float(np.min(rot[window, 0])), -2.0, delta=0.15)
        self.assertAlmostEqual(float(np.min(off[window, 1])), -1.0, delta=0.08)
        self.assertLess(int(np.argmin(rot[window, 0])), 4)

    def test_variation_changes_the_steps_by_the_seed(self):
        _, even = self.run_model(bob=4.0)
        _, varied = self.run_model(bob=4.0, variation=30.0)
        _, again = self.run_model(bob=4.0, variation=30.0)
        _, other = self.run_model(bob=4.0, variation=30.0, seed=7)
        sizes = [pp(varied[i:i + self.STEP, 1]) for i in range(0, 240, self.STEP)]
        self.assertGreater(max(sizes) - min(sizes), 0.3)
        self.assertTrue(np.array_equal(varied, again))
        self.assertFalse(np.allclose(varied, other))
        self.assertTrue(np.allclose(even[:self.STEP, 1], even[self.STEP:2 * self.STEP, 1]))

    def test_axes_and_ease(self):
        rot, _ = self.run_model(nod=3.0, footfall=1.0, tilt_on=False)
        self.assertTrue(np.all(rot[:, 0] == 0.0))
        rot, off = self.run_model(bob=4.0, nod=3.0, ease=10.0)
        self.assertEqual(float(off[0, 1]), 0.0)
        self.assertEqual(float(rot[-1, 0]), 0.0)

    def test_shake_dispatches(self):
        rot, off = cs.shake("bobbing", np.arange(0.0, 240.0, 0.125), 0, 240, FPS, plain(bob=4.0))
        self.assertAlmostEqual(pp(off[:, 1]), 4.0, delta=0.05)


class HeadingTests(unittest.TestCase):

    def test_a_camera_looking_down_bobs_straight_up(self):
        base = (-40.0, 0.0, 0.0)
        self.assertTrue(np.allclose(cs.along_heading((0.0, 1.0, 0.0), base, "xyz"), (0.0, 1.0, 0.0)))
        tilted = cs.along_axes((0.0, 1.0, 0.0), base, "xyz")
        self.assertAlmostEqual(float(tilted[1]), math.cos(math.radians(40.0)), places=6)

    def test_side_and_back_follow_the_heading(self):
        base = (-25.0, 90.0, 0.0)
        side = cs.along_heading((1.0, 0.0, 0.0), base, "xyz")
        own_x = cs.euler_matrix(np.radians(base), "xyz")[0]
        flat = np.array([own_x[0], 0.0, own_x[2]])
        self.assertTrue(np.allclose(side, flat / np.linalg.norm(flat)))
        back = cs.along_heading((0.0, 0.0, 1.0), base, "xyz")
        self.assertAlmostEqual(float(back[1]), 0.0, places=9)
        self.assertAlmostEqual(float(np.dot(back, side)), 0.0, places=9)

    def test_rolled_on_its_side_it_keeps_its_own_axes(self):
        base = (0.0, 0.0, 90.0)
        self.assertTrue(np.allclose(cs.along_heading((0.0, 1.0, 0.0), base, "xyz"),
                                    cs.along_axes((0.0, 1.0, 0.0), base, "xyz")))

    def test_deltas_heading(self):
        base = np.array([[-40.0, 0.0, 0.0]])
        _, moved = cs.deltas(np.zeros((1, 3)), np.array([[0.0, 2.0, 0.0]]), base, "xyz", heading=True)
        self.assertTrue(np.allclose(moved[0], (0.0, 2.0, 0.0)))


class RecordTests(unittest.TestCase):

    def test_layer_name_and_record(self):
        self.assertEqual(cs.layer_name("bobbing", 0, 60), "CamShake_Bobbing_0_60")
        s = cs.settings("bobbing", {"gait": "Run", "foot": "Right"})
        found = cs.parse_record(cs.record_text("bobbing", s, 0, 60, ["U"]))
        self.assertEqual((found["mode"], found["settings"]["gait"], found["settings"]["foot"]),
                         ("bobbing", "Run", "Right"))

    def test_describe(self):
        text = cs.describe("bobbing", cs.settings("bobbing"), 0, 60, ["|cam"], "CamShake_Bobbing_0_60")
        self.assertIn("Bobbing: walk at", text)
        self.assertIn("left foot first", text)


class CardTests(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.saved = {name: getattr(cs, name) for name in
                      ("cmds", "apply", "picked", "pick", "record", "shakes", "apply_targets", "replaced",
                       "_uuid", "frames_for", "editor_pick")}
        cs.cmds = self.fake
        self.calls = []
        cs.picked = lambda: None
        cs.pick = lambda layer: None
        cs.record = lambda layer: None
        cs.shakes = lambda: []
        cs.apply_targets = lambda mode, selection=None: ["|cam"]
        cs.replaced = lambda mode, uuids: []
        cs._uuid = lambda node: "U"
        cs.frames_for = lambda mode, s, given=None: (0, 50, "the playback range")
        cs.editor_pick = lambda: None
        cs.apply = lambda mode, given=None, selection=None, frames=None: (
            self.calls.append((mode, given)) or ("L", "applied"))
        cs.build_panel()
        cs.mode_changed("bobbing")()

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(cs, name, value)
        cs._QUIET[0] = False
        cs.JOB.clear()
        cs._state().pop("editor", None)

    def control(self, name):
        return self.fake.controls[name]

    def slider(self, name):
        return self.control(cs._slider("bobbing", name))

    def labels(self, menu):
        return [self.control(item)["label"] for item in self.control(menu)["items"]]

    def test_the_tab_and_its_menus(self):
        self.assertEqual(cs.current_mode(), "bobbing")
        self.assertTrue(self.control(cs._mode_column("bobbing"))["manage"])
        self.assertFalse(self.control(cs._mode_column("handheld"))["manage"])
        self.assertEqual(self.labels(cs.GAIT_MENU), ["Walk", "Run"])
        self.assertEqual(self.labels(cs.FOOT_MENU), ["Left", "Right"])
        self.assertIn("Sprint", self.labels(cs.PRESET_MENU))

    def test_a_preset_fills_the_knobs_and_the_gait(self):
        self.control(cs.PRESET_MENU)["value"] = "Run"
        cs.preset_changed()
        run = cs.preset("bobbing", "Run")
        self.assertEqual(self.slider("tempo")["value"], run["tempo"])
        self.assertEqual(self.control(cs.GAIT_MENU)["value"], "Run")

    def test_speed_fills_the_gaits_knobs_and_keeps_the_style(self):
        self.slider("lean")["value"] = 4.0
        self.slider("pace")["value"] = 3.5
        cs.pace_changed()
        expected = cs.from_speed(3.5)
        self.assertEqual(self.slider("tempo")["value"], expected["tempo"])
        self.assertEqual(self.slider("bob")["value"], expected["bob"])
        self.assertEqual(self.control(cs.GAIT_MENU)["value"], "Run")
        self.assertEqual(self.slider("lean")["value"], 4.0)
        self.assertEqual(self.control(cs.STATUS)["label"], "Set for the next Apply.")

    def test_apply_reads_the_tab(self):
        self.control(cs.FOOT_MENU)["value"] = "Right"
        cs.press_apply()
        mode, given = self.calls[-1]
        self.assertEqual((mode, given["foot"], given["gait"]), ("bobbing", "Right", "Walk"))


if __name__ == "__main__":
    unittest.main()

"""Camera Shake's Loop (2026-10-29) for Handheld and Bobbing: the range is one cycle - its last frame shows what
its first does - the noise, the tremor and the steps repeat over it, nothing fades in or out, the layer's curves
cycle past it; the card's Loop chip. The model without a scene, the keys on test_camshake_more's fake scene,
the card on test_camshake's fake cmds."""

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
from tests.test_camshake_more import HAVE_API, Scene, SceneTest  # noqa: E402

FPS = 30.0


def extended(mode, s, a, b, cycles=2):
    """The shake over `cycles` cycles from a (its frames a..a + cycles x (b - a)), the cycle being a..b."""
    frames = np.arange(a, a + cycles * (b - a) + 1)
    work = {"handheld": cs.handheld, "bobbing": cs.bobbing}[mode]
    rot, off = work(frames, a, b, FPS, s)
    return frames, rot, off


class Settings(unittest.TestCase):

    def test_loop_is_handhelds_and_bobbings_off_by_default(self):
        self.assertFalse(cs.settings("handheld")["loop"])
        self.assertFalse(cs.settings("bobbing")["loop"])
        self.assertNotIn("loop", cs.settings("impact"))
        self.assertTrue(cs.settings("handheld", {"loop": 1})["loop"])

    def test_a_preset_keeps_the_loop(self):
        self.assertTrue(cs.preset("handheld", "Nervous", {"loop": True})["loop"])
        self.assertTrue(cs.preset("bobbing", "Run", {"loop": True})["loop"])

    def test_a_record_keeps_it(self):
        s = cs.settings("bobbing", {"loop": True})
        data = cs.parse_record(cs.record_text("bobbing", s, 0, 60, ["U"]))
        self.assertTrue(data["settings"]["loop"])


class Noise(unittest.TestCase):

    def test_a_looped_noise_repeats_every_period(self):
        period = 2.0
        s = np.linspace(0.0, period, 301)
        one = cs.noise(s, 4, 9, 1.3, period)
        two = cs.noise(s + period, 4, 9, 1.3, period)
        np.testing.assert_allclose(one, two, atol=1e-12)
        self.assertAlmostEqual(float(one[0]), float(one[-1]), places=12)

    def test_it_is_smooth_across_the_seam(self):
        period = 1.5
        dt = 1e-3
        s = np.arange(-0.05, 0.05 + dt / 2, dt)
        v = cs.noise(s, 2, 3, 2.0, period)
        second = np.abs(np.diff(v, 2)) / dt ** 2
        self.assertLess(float(second.max()), 4.0 * float(np.median(second)) + 50.0)

    def test_its_knots_are_whole_and_never_too_few(self):
        self.assertEqual(cs.loop_knots(2.0, 1.0), int(round(2.0 * cs.KNOTS_PER_CYCLE)))
        self.assertEqual(cs.loop_knots(1.0, 0.05), cs.LOOP_KNOTS)

    def test_a_slow_noise_in_a_short_loop_still_moves(self):
        s = np.linspace(0.0, 1.0, 61)
        v = cs.noise(s, 1, 1, 0.05, 1.0)
        self.assertGreater(float(np.ptp(v)), 0.1)

    def test_a_looped_noise_is_about_unit_rms_and_its_rate(self):
        period = 400.0
        s = np.linspace(0.0, period, 40001)
        v = cs.noise(s, 6, 2, 1.0, period)
        self.assertAlmostEqual(float(np.sqrt(np.mean(v * v))), 1.0, delta=0.1)
        crossings = np.count_nonzero(np.diff(np.sign(v)) != 0) / (2.0 * period)
        self.assertAlmostEqual(crossings, 1.0, delta=0.15)

    def test_no_period_is_the_old_noise(self):
        s = np.linspace(0.0, 3.0, 91)
        np.testing.assert_array_equal(cs.noise(s, 5, 7, 1.1), cs.noise(s, 5, 7, 1.1, None))

    def test_a_fractal_repeats_too(self):
        s = np.linspace(0.0, 3.0, 91)
        one = cs.fractal(s, 3, 2, 0.4, 3, fps=FPS, period=3.0)
        np.testing.assert_allclose(one, cs.fractal(s + 3.0, 3, 2, 0.4, 3, fps=FPS, period=3.0), atol=1e-12)


class Tremor(unittest.TestCase):

    def test_whole_cycles(self):
        self.assertAlmostEqual(cs.whole_cycles(7.0, 2.0), 7.0)
        self.assertAlmostEqual(cs.whole_cycles(7.2, 2.0), 7.0)
        self.assertAlmostEqual(cs.whole_cycles(7.3, 2.0), 7.5)
        self.assertAlmostEqual(cs.whole_cycles(0.1, 2.0), 0.5)    # at least once a cycle

    def test_whole_cycles_stay_under_the_frame_rates_cap(self):
        cap = cs.NYQUIST_SHARE * FPS
        hz = cs.whole_cycles(cap, 0.3, FPS)
        self.assertLessEqual(hz, cap + 1e-9)
        self.assertAlmostEqual(hz * 0.3, round(hz * 0.3), places=9)

    def test_a_looped_tremor_repeats(self):
        s = np.linspace(0.0, 2.0, 121)
        one = cs.tremor(s, 3, 4, 7.3, 2.0)
        np.testing.assert_allclose(one, cs.tremor(s + 2.0, 3, 4, 7.3, 2.0), atol=1e-12)

    def test_it_swings_its_whole_cycles(self):
        s = np.linspace(0.0, 4.0, 4001)
        v = cs.tremor(s, 1, 1, 6.0, 4.0)
        crossings = np.count_nonzero(np.diff(np.sign(v)) != 0) / 8.0
        self.assertAlmostEqual(crossings, 6.0, delta=0.6)


class Handheld(unittest.TestCase):

    def given(self, **more):
        values = {"sway": 2.0, "speed": 1.4, "jitter": 0.4, "jitter_hz": 8.3, "roll": 0.6, "drift": 4.0,
                  "ease": 12.0, "loop": True, "seed": 7}
        values.update(more)
        return cs.settings("handheld", values)

    def test_the_last_frame_shows_the_first_and_the_cycle_repeats(self):
        a, b = 10, 70
        frames, rot, off = extended("handheld", self.given(), a, b, cycles=3)
        n = b - a
        np.testing.assert_allclose(rot[:-n], rot[n:], atol=1e-9)
        np.testing.assert_allclose(off[:-n], off[n:], atol=1e-9)
        np.testing.assert_allclose(rot[0], rot[n], atol=1e-9)
        self.assertGreater(float(np.abs(rot).max()), 0.3)

    def test_no_ease_in_a_loop(self):
        frames, rot, off = extended("handheld", self.given(), 0, 60, cycles=1)
        self.assertGreater(float(np.abs(rot[0]).max()), 0.0)
        self.assertGreater(float(np.abs(off[-1]).max()), 0.0)

    def test_sizes_hold_in_a_long_loop(self):
        s = self.given(jitter=0.0, drift=0.0, sway=2.0)
        frames = np.arange(0, 4001)
        rot, _ = cs.handheld(frames, 0, 4000, FPS, s)
        pan = rot[:, 1]
        self.assertAlmostEqual(2.0 * float(np.sqrt(np.mean(pan * pan))), 2.0, delta=0.35)

    def test_off_it_is_the_shake_it_was(self):
        frames = np.arange(0, 61)
        on = dict(self.given(), loop=False)
        rot, off = cs.handheld(frames, 0, 60, FPS, on)
        plain = {key: value for key, value in on.items() if key != "loop"}
        old_rot, old_off = cs.handheld(frames, 0, 60, FPS, plain)
        np.testing.assert_array_equal(rot, old_rot)
        np.testing.assert_array_equal(off, old_off)
        self.assertEqual(float(np.abs(rot[0]).max()), 0.0)          # eased in, as before


class Bobbing(unittest.TestCase):

    def given(self, **more):
        values = dict(cs.preset("bobbing", "Walk"), footfall=0.8, variation=25.0, ease=10.0, contact=4.0,
                      loop=True, seed=3)
        values.update(more)
        return cs.settings("bobbing", values)

    def test_the_tempo_fits_whole_strides(self):
        tempo, strides = cs.loop_tempo(116.0, 60, FPS)
        self.assertEqual(strides, 2)
        self.assertAlmostEqual(tempo, 120.0)
        tempo, strides = cs.loop_tempo(170.0, 45, FPS)
        self.assertEqual(strides, 2)
        self.assertAlmostEqual(tempo, 120.0 * 2 * FPS / 45.0)
        self.assertEqual(cs.loop_tempo(60.0, 10, FPS)[1], 1)           # never fewer than one

    def test_the_last_frame_shows_the_first_and_the_cycle_repeats(self):
        a, b = 0, 75
        frames, rot, off = extended("bobbing", self.given(), a, b, cycles=3)
        n = b - a
        np.testing.assert_allclose(rot[:-n], rot[n:], atol=1e-9)
        np.testing.assert_allclose(off[:-n], off[n:], atol=1e-9)
        self.assertGreater(float(np.ptp(off[:, 1])), 1.0)

    def test_a_run_loops_too(self):
        s = self.given(**dict(cs.preset("bobbing", "Run"), loop=True, footfall=1.0, variation=30.0))
        frames, rot, off = extended("bobbing", s, 5, 48, cycles=2)
        np.testing.assert_allclose(rot[:-43], rot[43:], atol=1e-9)
        np.testing.assert_allclose(off[:-43], off[43:], atol=1e-9)

    def test_the_steps_are_the_fitted_tempos(self):
        s = self.given(variation=0.0, footfall=0.0, contact=0.0, tempo=116.0)
        frames = np.arange(0, 61)
        rot, off = cs.bobbing(frames, 0, 60, FPS, s)
        lows = [int(f) for f in frames[1:-1] if off[f, 1] < off[f - 1, 1] and off[f, 1] <= off[f + 1, 1]]
        self.assertEqual(len(lows), 4)                                  # 2 strides, 4 steps
        self.assertAlmostEqual(cs.tempo_of(0, 60, FPS, s), 120.0)
        self.assertEqual(cs.tempo_of(0, 60, FPS, dict(s, loop=False)), 116.0)

    def test_no_ease_in_a_loop(self):
        frames, rot, off = extended("bobbing", self.given(), 0, 60, cycles=1)
        self.assertGreater(float(np.abs(off[0]).max()), 0.0)

    def test_off_it_is_the_shake_it_was(self):
        frames = np.arange(0, 61)
        on = dict(self.given(), loop=False)
        plain = {key: value for key, value in on.items() if key != "loop"}
        for got, old in zip(cs.bobbing(frames, 0, 60, FPS, on), cs.bobbing(frames, 0, 60, FPS, plain)):
            np.testing.assert_array_equal(got, old)


class Describe(unittest.TestCase):

    def test_a_loop_says_so(self):
        s = cs.settings("handheld", {"loop": True})
        text = cs.describe("handheld", s, 0, 60, ["|cam"], "L", "", (), FPS)
        self.assertIn("looped: frame 60 shows frame 0, the layer cycles past them", text)
        self.assertNotIn("looped", cs.describe("handheld", cs.settings("handheld"), 0, 60, ["|cam"], "L"))

    def test_a_bobbing_loop_names_its_strides_and_its_tempo(self):
        s = cs.settings("bobbing", {"loop": True, "tempo": 116.0})
        text = cs.describe("bobbing", s, 0, 60, ["|cam"], "L", "", (), FPS)
        self.assertIn("2 strides in the loop at 120 steps/min (Tempo 116)", text)
        s = cs.settings("bobbing", {"loop": True, "tempo": 120.0})
        self.assertNotIn("Tempo 120", cs.describe("bobbing", s, 0, 60, ["|cam"], "L", "", (), FPS))


class LoopScene(Scene):
    """The fake scene, its curves cut and their infinity remembered."""

    def __init__(self):
        super(LoopScene, self).__init__()
        self.infinity = {}

    def cutKey(self, curve, time=None, clear=False, **_kw):  # noqa: N802
        self.curves[curve].pop(float(time[0]), None)
        return 1

    def setAttr(self, plug, *values, **kw):  # noqa: N802
        node, attr = plug.rsplit(".", 1)
        if attr in ("preInfinity", "postInfinity"):
            self.infinity.setdefault(node, {})[attr] = values[0]
        return super(LoopScene, self).setAttr(plug, *values, **kw)


class LoopSceneTest(SceneTest):

    def setUp(self):
        super(LoopSceneTest, self).setUp()
        self.scene = LoopScene()
        cs.cmds = self.scene


class Keys(LoopSceneTest):

    def test_a_loop_keys_only_its_frames_and_cycles(self):
        self.scene.curves["c"] = {9.0: 0.0, 14.0: 0.0}                # an earlier press's zeros
        cs._key("c", np.arange(10, 14), [1.0, 2.0, 3.0, 1.0], loop=True)
        self.assertEqual(self.scene.curves["c"], {10.0: 1.0, 11.0: 2.0, 12.0: 3.0, 13.0: 1.0})
        self.assertEqual(self.scene.infinity["c"], {"preInfinity": cs.CYCLE, "postInfinity": cs.CYCLE})

    def test_both_end_keys_are_fixed_on_the_chord_across_the_seam(self):
        self.scene.curves["c"] = {}
        cs._key("c", np.arange(10, 14), [1.0, 2.0, 3.0, 1.0], loop=True)
        angle = np.degrees(np.arctan((2.0 - 3.0) / 2.0))
        fixed = [(time, kw) for _c, time, kw in self.scene.tangents if "lock" not in kw]
        self.assertEqual([time for time, _ in fixed], [(10, 10), (13, 13)])
        for _time, kw in fixed:
            self.assertEqual((kw["inTangentType"], kw["outTangentType"]), ("fixed", "fixed"))
            self.assertAlmostEqual(kw["inAngle"], angle)
            self.assertAlmostEqual(kw["outAngle"], angle)

    def test_the_seam_slope(self):
        self.assertAlmostEqual(cs.seam_slope([0.0, 2.0, 5.0, -4.0, 0.0]), (2.0 - -4.0) / 2.0)
        self.assertEqual(cs.seam_slope([1.0, 1.0]), 0.0)

    def test_off_it_holds_zero_outside_and_stops_cycling(self):
        self.scene.curves["c"] = {}
        cs._key("c", np.arange(10, 14), [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(self.scene.infinity["c"], {"preInfinity": cs.CONSTANT, "postInfinity": cs.CONSTANT})
        self.assertEqual(self.scene.curves["c"][9.0], 0.0)
        self.assertEqual(self.scene.curves["c"][14.0], 0.0)


class Seam(unittest.TestCase):

    def test_a_closed_loop_has_no_gap(self):
        values = {"rotateX": np.array([1.0, 2.0, 1.0]), "translateY": np.array([0.5, 0.0, 0.5])}
        self.assertEqual(cs.seam_gap(values, ["rotateX", "translateY"]), (0.0, 0.0))

    def test_a_gap_in_degrees_and_cm(self):
        values = {"rotateY": np.array([1.0, 2.0, 1.3]), "translateX": np.array([0.0, 1.0, -0.2])}
        deg, cm = cs.seam_gap(values, ["rotateY", "translateX"], unit_deg=1.0, unit_cm=1.0)
        self.assertAlmostEqual(deg, 0.3)
        self.assertAlmostEqual(cm, 0.2)

    def test_the_line_names_the_node_and_the_jump(self):
        self.assertEqual(cs.seam_text({}, 0, 60), "")
        text = cs.seam_text({"|rig|cam": (0.321, 0.0)}, 0, 75)
        self.assertIn("cam's own animation differs at frames 0 and 75: the loop's seam jumps 0.32 deg", text)
        self.assertNotIn("cm", text)
        self.assertIn("0.32 deg, 1.50 cm", cs.seam_text({"|cam": (0.321, 1.5)}, 0, 75))


class Gone(LoopSceneTest):
    """A layer deleted: an unkeyed channel stands where it stood without it, not where the DG left it."""

    def setUp(self):
        super(Gone, self).setUp()
        self.scene.camera("|cam")
        self.scene.nodes["|cam"]["rotate"] = [-15.0, 0.0, 0.0]
        self.scene.layers["L"] = {"plugs": {"|cam.rotateX"}, "curves": {"|cam.rotateX": "Lc"}, "lock": False,
                                  "mute": False, "weight": 0.5, "selected": False, "marker": "{}",
                                  "uuid": "LAYER9"}
        self.scene.curves["Lc"] = {0.0: 4.0, 20.0: 4.0}
        self.order = []
        scene = self.scene

        def animLayer(name, query=False, edit=False, attribute=None, mute=False, **kw):   # noqa: N802
            if query and attribute is True:
                return sorted(scene.layers[name]["plugs"])
            if edit and mute:
                self.order.append("mute")
                scene.layers[name]["mute"] = True
                return None
            return Scene.animLayer(scene, name, query=query, edit=edit, attribute=attribute, mute=mute, **kw)

        def delete(name):
            # Maya: the channel keeps what its blend last evaluated - base + this layer's share, unless muted
            self.order.append("delete")
            scene.nodes["|cam"]["rotate"][0] = scene.shown("|cam", "rotateX", scene.time)
            Scene.delete(scene, name)

        self.scene.animLayer, self.scene.delete = animLayer, delete

    def test_a_deleted_layer_leaves_an_unkeyed_channel_where_it_stood_without_it(self):
        self.assertEqual(self.scene.shown("|cam", "rotateX", 10.0), -13.0)
        cs._delete_layer("L")
        self.assertNotIn("L", self.scene.layers)
        self.assertEqual(self.order, ["mute", "delete"])
        self.assertEqual(self.scene.nodes["|cam"]["rotate"][0], -15.0)

    def test_the_card_s_delete_goes_that_way(self):
        self.scene.layers["L"]["marker"] = cs.record_text("handheld", cs.settings("handheld"), 0, 20,
                                                          [self.scene.nodes["|cam"]["uuid"]])
        cs.delete("L")
        self.assertEqual(self.order, ["mute", "delete"])
        self.assertEqual(self.scene.nodes["|cam"]["rotate"][0], -15.0)


@unittest.skipUnless(HAVE_API, "needs maya.api.OpenMaya")
class Press(LoopSceneTest):

    def setUp(self):
        super(Press, self).setUp()
        self.scene.camera("|cam")
        self.scene.nodes["|cam"]["rotate"] = [-10.0, 25.0, 0.0]
        self.scene.selection = ["|cam"]

    def curve(self, layer, attr):
        return self.scene.layers[layer]["curves"]["|cam." + attr]

    def test_a_looped_apply_and_a_retune_out_of_it_and_back(self):
        layer, text = cs.apply("handheld", {"loop": True, "drift": 0.0}, frames=(0, 30))
        self.assertIn("looped: frame 30 shows frame 0", text)
        self.assertTrue(cs.record(layer)["settings"]["loop"])
        curve = self.curve(layer, "rotateY")
        self.assertEqual(sorted(self.scene.curves[curve]), [float(f) for f in range(0, 31)])
        keys = self.scene.curves[curve]
        self.assertAlmostEqual(keys[0.0], keys[30.0], places=9)
        self.assertEqual(self.scene.infinity[curve]["postInfinity"], cs.CYCLE)

        cs.retune(layer, {"loop": False, "drift": 0.0})
        self.assertEqual(self.scene.curves[curve][-1.0], 0.0)
        self.assertEqual(self.scene.curves[curve][31.0], 0.0)
        self.assertEqual(self.scene.infinity[curve]["postInfinity"], cs.CONSTANT)
        self.assertFalse(cs.record(layer)["settings"]["loop"])

        cs.retune(layer, {"loop": True, "drift": 0.0})
        self.assertNotIn(-1.0, self.scene.curves[curve])
        self.assertNotIn(31.0, self.scene.curves[curve])
        self.assertEqual(self.scene.infinity[curve]["preInfinity"], cs.CYCLE)


LAYER = "CamShake_Handheld_0_50"


class Card(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        names = ("cmds", "apply", "retune", "picked", "pick", "record", "shakes", "apply_targets", "replaced",
                 "_uuid", "frames_for", "editor_pick", "_node_names")
        saved = {name: getattr(cs, name) for name in names}
        self.addCleanup(lambda: [setattr(cs, name, value) for name, value in saved.items()])
        self.addCleanup(cs.JOB.clear)
        self.addCleanup(lambda: cs._state().pop("editor", None))
        self.addCleanup(lambda: cs._QUIET.__setitem__(0, False))
        import maya_hubstyle
        self.addCleanup(maya_hubstyle.take_marks)
        cs.cmds = self.fake
        self.calls = []
        self.current = None
        self.looped = True
        cs.picked = lambda: self.current
        cs.pick = lambda layer: setattr(self, "current", layer)
        cs.record = lambda layer: {"mode": "handheld", "frames": [0, 50], "targets": ["U"],
                                   "settings": cs.settings("handheld", {"loop": self.looped})} if layer else None
        cs.shakes = lambda: [LAYER]
        cs.apply_targets = lambda mode, selection=None: ["|cam"]
        cs.replaced = lambda mode, uuids: []
        cs._uuid = lambda node: "U"
        cs.frames_for = lambda mode, s, given=None: (0, 50, "the playback range")
        cs.editor_pick = lambda: None
        cs.apply = lambda mode, given=None, selection=None, frames=None: (
            self.calls.append(("apply", mode, given)) or (LAYER, "applied"))
        cs.retune = lambda layer, given: self.calls.append(("retune", layer, given)) or "re-tuned"
        cs._node_names = lambda found: "cam"
        cs.build_panel()

    def control(self, name):
        return self.fake.controls[name]

    def test_a_loop_chip_in_handheld_and_bobbing_only(self):
        for mode in cs.LOOP_MODES:
            chip = self.control(cs._loop_chip(mode))
            self.assertEqual((chip["kind"], chip["label"], chip["value"]), ("checkBox", "Loop", False))
        self.assertNotIn(cs._loop_chip("impact"), self.fake.controls)
        self.assertNotEqual(self.control(cs._slider("handheld", "ease")).get("enable"), False)

    def test_the_chip_dims_ease_and_sets_up_the_next_apply(self):
        chip = self.control(cs._loop_chip("handheld"))
        chip["value"] = True
        chip["changeCommand"]()
        self.assertFalse(self.control(cs._slider("handheld", "ease"))["enable"])
        self.assertEqual(self.control(cs.STATUS)["label"], "Set for the next Apply.")
        self.assertTrue(cs.remembered("handheld")["loop"])
        self.assertIn("New looped handheld shake on cam", self.control(cs.SUBTITLE)["label"])
        cs.press_apply()
        self.assertTrue(self.calls[-1][2]["loop"])
        chip["value"] = False
        chip["changeCommand"]()
        self.assertTrue(self.control(cs._slider("handheld", "ease"))["enable"])

    def test_the_chip_re_keys_the_picked_shake(self):
        self.current = LAYER
        cs._load(LAYER)
        self.assertTrue(self.control(cs._loop_chip("handheld"))["value"])
        self.assertFalse(self.control(cs._slider("handheld", "ease"))["enable"])
        self.assertTrue(cs.selection_line().endswith("frames 0-50, looped"), cs.selection_line())
        self.control(cs._loop_chip("handheld"))["value"] = False
        self.control(cs._loop_chip("handheld"))["changeCommand"]()
        verb, layer, given = self.calls[-1]
        self.assertEqual((verb, layer, given["loop"]), ("retune", LAYER, False))

    def test_filled_from_code_it_runs_nothing(self):
        cs._QUIET[0] = True
        cs.loop_changed("handheld")()
        self.assertEqual(self.calls, [])

    def test_a_bobbing_loop_is_read_and_remembered_apart(self):
        cs.mode_changed("bobbing")()
        self.control(cs._loop_chip("bobbing"))["value"] = True
        self.control(cs._loop_chip("bobbing"))["changeCommand"]()
        self.assertTrue(cs.remembered("bobbing")["loop"])
        self.assertFalse(cs.remembered("handheld")["loop"])
        cs.press_apply()
        self.assertEqual((self.calls[-1][1], self.calls[-1][2]["loop"]), ("bobbing", True))


if __name__ == "__main__":
    unittest.main()

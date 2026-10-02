"""The fire on the Characters cards, as numbers (2026-10-02): the palettes, the
heat field, the sparks, a card's life and the light masks - maya_charfire is
numpy and stdlib, so all of it is tested with no Qt and no Maya. The painting
is test_chargrid's, the hub verify_character_fire.py's.

Spec: docs/superpowers/specs/2026-10-02-character-card-fire-design.md
"""
import os
import subprocess
import sys
import unittest

import numpy as np

import maya_charfire as cf
from maya_scenesetup import catalog

PLUGIN = os.path.dirname(os.path.abspath(cf.__file__))


class Palettes(unittest.TestCase):

    def test_every_character_model_has_a_fire_of_its_own(self):
        """A model with a character row burns; the fires are all different
        and every one is a palette."""
        burning = [m.key for m in catalog.MODELS
                   if any(catalog.character_for(m.key, kind)
                          for kind in catalog.KINDS)]
        self.assertTrue(burning)
        for key in burning:
            self.assertIn(cf.fire_of(key), cf.PALETTES, key)
        fires = [cf.fire_of(key) for key in burning]
        self.assertEqual(len(set(fires)), len(fires))

    def test_the_four_characters_burn_in_four_colours(self):
        self.assertEqual(cf.fire_of("Manny"), "ember")
        self.assertEqual(cf.fire_of("Creep"), "spectral")
        self.assertEqual(cf.fire_of("Orc_D"), "toxic")
        self.assertEqual(cf.fire_of("UE4_Mannequin"), "arcane")

    def test_a_model_not_named_has_no_fire(self):
        self.assertEqual(cf.fire_of("Auto"), "")
        self.assertEqual(cf.fire_of("nobody"), "")

    def test_the_lut_is_premultiplied_and_runs_dark_to_white_hot(self):
        for name in cf.PALETTES:
            lut = cf.palette_lut(name)
            self.assertEqual(lut.shape, (256, 4))
            self.assertEqual(lut.dtype, np.uint8)
            self.assertTrue((lut[:, :3] <= lut[:, 3:4]).all(), name)
            self.assertEqual(int(lut[0, 3]), 0)
            self.assertEqual(int(lut[255, 3]), 255)
            self.assertGreater(int(lut[255, :3].min()), 200, name)

    def test_hotter_is_never_more_transparent(self):
        for name in cf.PALETTES:
            alpha = [cf.palette_rgba(name, i / 50.0)[3] for i in range(51)]
            self.assertEqual(alpha, sorted(alpha), name)

    def test_heat_outside_the_range_is_clamped(self):
        self.assertEqual(cf.palette_rgba("ember", -1.0),
                         cf.palette_rgba("ember", 0.0))
        self.assertEqual(cf.palette_rgba("ember", 3.0),
                         cf.palette_rgba("ember", 1.0))


class FireField(unittest.TestCase):

    def steps(self, fire, power, seconds):
        for _ in range(int(seconds * cf.SIM_HZ)):
            fire.step(power)

    def test_unpowered_it_stays_cold(self):
        fire = cf.Fire(3)
        self.steps(fire, 0.0, 2.0)
        self.assertTrue(fire.cold())

    def test_powered_it_rises_past_two_fifths_of_the_card(self):
        fire = cf.Fire(3)
        self.steps(fire, 1.0, 1.5)
        hot_rows = np.where(fire.heat.max(axis=1) > 0.3)[0]
        self.assertTrue(len(hot_rows))
        reach = (cf.Fire.ROWS - hot_rows.min()) / float(cf.Fire.ROWS)
        self.assertGreater(reach, 0.4)
        self.assertGreater(fire.warmth(), 0.3)

    def test_put_out_it_goes_cold(self):
        fire = cf.Fire(3)
        self.steps(fire, 1.0, 1.0)
        self.assertFalse(fire.cold())
        self.steps(fire, 0.0, 3.0)
        self.assertTrue(fire.cold())

    def test_the_same_seed_burns_the_same(self):
        a, b = cf.Fire(11), cf.Fire(11)
        self.steps(a, 1.0, 0.5)
        self.steps(b, 1.0, 0.5)
        self.assertTrue(np.array_equal(a.heat, b.heat))

    def test_the_field_is_the_heat_at_any_size_through_the_palette(self):
        fire = cf.Fire(3)
        self.steps(fire, 1.0, 1.0)
        lut = cf.palette_lut("spectral")
        field = fire.field(lut, 50, 40)
        self.assertEqual(field.shape, (40, 50, 4))
        self.assertEqual(field.dtype, np.uint8)
        self.assertTrue(field.flags["C_CONTIGUOUS"])
        # the bottom is hot and blue (B G R A: blue over red)
        bottom = field[-3:].reshape(-1, 4).astype(int).mean(axis=0)
        self.assertGreater(bottom[3], 150)
        self.assertGreater(bottom[0], bottom[2])
        # and a second size is answered too (the grid is cached per size)
        self.assertEqual(fire.field(lut, 7, 9).shape, (9, 7, 4))


class SparksLife(unittest.TestCase):

    def test_a_burst_rises_and_dies(self):
        sparks = cf.Sparks(5)
        sparks.spawn(24, burst=True)
        self.assertEqual(len(sparks.age), 24)
        y0 = sparks.pos[:, 1].copy()
        sparks.step(0.1, 0.0)
        self.assertTrue((sparks.pos[:, 1] < y0).all())
        for _ in range(40):
            sparks.step(0.05, 0.0)
        self.assertFalse(sparks.alive())

    def test_a_rate_spawns_about_that_many_a_second(self):
        sparks = cf.Sparks(5)
        born = 0
        for _ in range(60):
            before = len(sparks.age)
            sparks.step(1.0 / 60, 30.0)
            born += max(0, len(sparks.age) - before)
        self.assertGreaterEqual(born, 20)
        self.assertLessEqual(born, 31)

    def test_a_quarter_or_so_fly_in_front(self):
        sparks = cf.Sparks(5)
        sparks.spawn(400)
        share = sparks.front.mean()
        self.assertGreater(share, 0.15)
        self.assertLess(share, 0.35)


class CardLife(unittest.TestCase):

    def run_for(self, fx, seconds, dt=1.0 / 60):
        for _ in range(int(seconds / dt)):
            fx.step(dt)

    def test_a_card_never_hovered_is_idle(self):
        self.assertFalse(cf.CardFx(1).active())

    def test_it_catches_grows_and_settles_back(self):
        fx = cf.CardFx(1)
        fx.set_hover(True)
        self.assertEqual(len(fx.sparks.age), cf.CATCH_SPARKS)
        self.assertEqual(fx.flash, 1.0)
        self.assertTrue(fx.active())
        self.run_for(fx, 1.0)
        self.assertGreater(fx.power, 0.95)
        self.assertAlmostEqual(fx.grow, 1.0, delta=0.05)
        self.assertGreater(fx.warm, 0.2)
        fx.set_hover(False)
        self.run_for(fx, 4.0)
        self.assertFalse(fx.active())
        self.assertEqual(fx.power, 0.0)

    def test_the_grow_overshoots_a_little_and_never_shows_below_rest(self):
        fx = cf.CardFx(1)
        fx.set_hover(True)
        peak = 0.0
        for _ in range(60):
            fx.step(1.0 / 60)
            peak = max(peak, fx.grow)
        self.assertGreater(peak, 1.0)
        self.assertLess(peak, 1.25)
        fx.set_hover(False)
        lowest = 1.0
        for _ in range(120):
            fx.step(1.0 / 60)
            lowest = min(lowest, fx.shown_grow())
        self.assertGreaterEqual(lowest, 0.0)

    def test_hovering_again_does_not_burst_again(self):
        fx = cf.CardFx(1)
        fx.set_hover(True)
        fx.set_hover(True)
        self.assertEqual(len(fx.sparks.age), cf.CATCH_SPARKS)

    def test_a_click_bursts(self):
        fx = cf.CardFx(1)
        fx.burst()
        self.assertEqual(len(fx.sparks.age), cf.CLICK_SPARKS)
        self.assertTrue(fx.active())


class LitMasks(unittest.TestCase):

    def disc(self, side=64):
        yy, xx = np.mgrid[0:side, 0:side]
        r = np.hypot(xx - side / 2.0, yy - side / 2.0)
        return (r < side * 0.35).astype(np.float32)

    def test_a_body_filling_the_picture_has_no_rim_at_its_frame(self):
        shade, rim, light = cf.lit_masks(np.ones((48, 48), np.float32))
        self.assertLess(float(rim.max()), 1e-6)
        self.assertTrue(np.allclose(shade, 1.0))

    def test_the_rim_is_the_inside_of_the_edge(self):
        alpha = self.disc()
        _shade, rim, _light = cf.lit_masks(alpha)
        self.assertEqual(float(rim[32, 32]), 0.0)          # the middle
        self.assertGreater(float(rim[32, 32 - 21]), 0.1)   # just inside
        self.assertEqual(float(rim[2, 2]), 0.0)            # outside

    def test_the_firelight_comes_from_below(self):
        alpha = np.ones((40, 40), np.float32)
        _shade, _rim, light = cf.lit_masks(alpha)
        self.assertEqual(float(light[0].max()), 0.0)
        self.assertGreater(float(light[-1].min()), 0.5)
        column = light[:, 20]
        self.assertTrue((np.diff(column) >= -1e-6).all())


class Purity(unittest.TestCase):

    def test_it_imports_no_qt_and_no_maya(self):
        code = ("import sys, maya_charfire; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('PySide6', 'PySide2', 'maya', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()

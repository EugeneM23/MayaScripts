"""The glow of the hub's controls under the mouse, as numbers (2026-10-02):
the ink, the bloom and the primary button's rim - maya_hubglow is numpy and
stdlib, so all of it is tested with no Qt and no Maya. The painting is
test_hubqt's HoverGlow, the live hub verify_hub_glow.py's.

Spec: docs/superpowers/specs/2026-10-02-hub-hover-glow-design.md
"""
import os
import subprocess
import sys
import unittest

import numpy as np

import maya_hubglow as hg
import maya_hubmotion as motion
import maya_hubstyle as style

PLUGIN = os.path.dirname(os.path.abspath(hg.__file__))
P = style.HOVER_GLOW


def rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def canvas(h, w, face=None):
    """Premultiplied BGRA, `face` "#rrggbb" opaque or transparent."""
    out = np.zeros((h, w, 4), np.uint8)
    if face:
        paint(out, slice(None), slice(None), face)
    return out


def paint(arr, ys, xs, colour):
    r, g, b = rgb(colour)
    arr[ys, xs] = (b, g, r, 255)


def button(face="#34363b", text="#e4e4e6", border="#45474d"):
    """A hovered button: its face, a 1 px border, a bar of letters."""
    arr = canvas(40, 120, face)
    paint(arr, 0, slice(None), border)
    paint(arr, -1, slice(None), border)
    paint(arr, slice(None), 0, border)
    paint(arr, slice(None), -1, border)
    paint(arr, slice(17, 23), slice(40, 80), text)
    return arr


class Ink(unittest.TestCase):

    def test_the_letters_are_ink_the_face_and_border_are_not(self):
        mask, _colour = hg.ink(button())
        self.assertGreater(mask[20, 60], 0.99)
        self.assertEqual(mask[5, 10], 0.0)          # the hover fill
        self.assertEqual(mask[0, 60], 0.0)          # the border
        self.assertEqual(mask[20, 0], 0.0)

    def test_text_on_a_transparent_face_is_ink(self):
        """A segment: no background of its own, its muted text."""
        arr = canvas(30, 80)
        paint(arr, slice(12, 17), slice(20, 60), style.TOKENS["muted"])
        mask, _ = hg.ink(arr)
        self.assertGreater(mask[14, 40], 0.99)
        self.assertEqual(mask[2, 2], 0.0)

    def test_dark_letters_on_a_lit_face_are_no_ink(self):
        """The orange primary: nothing brighter than its face."""
        arr = button(face=style.TOKENS["accent_hover"],
                     text=style.TOKENS["on_accent"],
                     border=style.TOKENS["accent_hover"])
        mask, _ = hg.ink(arr)
        self.assertEqual(float(mask.max()), 0.0)
        self.assertIsNone(hg.bloom(arr))

    def test_the_face_is_read_inside_the_control_not_its_padding(self):
        """The bloom pads the source; a ring of transparent padding must not
        become the face of a small, lighter control."""
        pad = 8
        arr = canvas(30 + 2 * pad, 30 + 2 * pad)
        paint(arr, slice(pad, -pad), slice(pad, -pad), "#707070")
        inner = (pad, pad, arr.shape[0] - pad, arr.shape[1] - pad)
        mask, _ = hg.ink(arr, inner)
        self.assertEqual(float(mask.max()), 0.0)
        padded, _ = hg.ink(arr)                     # the ring as the face
        self.assertGreater(float(padded.max()), 0.5)

    def test_the_colour_is_the_pixel_over_the_card(self):
        arr = canvas(10, 10)
        paint(arr, 5, 5, "#e39a93")
        _mask, colour = hg.ink(arr)
        b, g, r = colour[5, 5]
        self.assertEqual((round(r), round(g), round(b)), rgb("#e39a93"))
        b, g, r = colour[0, 0]                       # transparent = the card
        self.assertEqual((round(r), round(g), round(b)),
                         rgb(style.TOKENS["card"]))


class Bloom(unittest.TestCase):

    def setUp(self):
        self.arr = button()
        self.out = hg.bloom(self.arr)

    def test_it_lights_around_the_letters(self):
        self.assertEqual(self.out.dtype, np.uint8)
        self.assertEqual(self.out.shape, self.arr.shape)
        self.assertGreater(self.out[25, 60, 3], 20)      # 2 px under them
        self.assertGreater(self.out[20, 36, 3], 20)      # 4 px left of them

    def test_it_leaves_the_letters_themselves_and_the_far_face(self):
        self.assertEqual(self.out[20, 60, 3], 0)         # a letter's core
        self.assertEqual(self.out[20, 112, 3], 0)        # far right
        self.assertEqual(self.out[2, 5, 3], 0)

    def test_at_most_its_strength(self):
        self.assertLessEqual(int(self.out[..., 3].max()),
                             int(round(255 * P["strength"])) + 1)

    def test_premultiplied(self):
        self.assertTrue((self.out[..., :3] <= self.out[..., 3:4]).all())

    def test_in_the_letters_own_colour(self):
        white = self.out[25, 60].astype(float)
        self.assertLess(abs(white[0] - white[2]), 4)     # B ~ R: white
        pink = hg.bloom(button(text="#e39a93"))[25, 60].astype(float)
        self.assertGreater(pink[2], pink[1] + 5)          # R over G
        self.assertGreater(pink[2], pink[0] + 5)          # R over B

    def test_it_reaches_as_far_as_the_radius(self):
        """Nothing more than ~3 radii from the letters (the box passes)."""
        far = int(np.ceil(3 * P["radius"])) + 1
        self.assertEqual(self.out[20, 40 - far - 1, 3], 0)

    def test_a_larger_display_blooms_wider(self):
        small = hg.bloom(self.arr, scale=1.0)
        large = hg.bloom(self.arr, scale=1.5)
        self.assertGreater(int((large[..., 3] > 0).sum()),
                           int((small[..., 3] > 0).sum()))

    def test_the_padding_is_the_radius(self):
        self.assertEqual(hg.pad(1.5), style.px(P["radius"], 1.5))


class Rim(unittest.TestCase):

    def setUp(self):
        self.arr = canvas(40, 120)
        paint(self.arr, slice(2, 38), slice(2, 118), style.TOKENS["accent"])
        self.out = hg.rim(self.arr, scale=1.0)

    def test_inside_the_edge_only(self):
        self.assertGreater(self.out[3, 60, 3], 30)        # just inside
        self.assertEqual(self.out[1, 60, 3], 0)           # outside
        self.assertEqual(self.out[20, 60, 3], 0)          # deep inside

    def test_its_colour_and_strength(self):
        self.assertLessEqual(int(self.out[..., 3].max()),
                             int(round(255 * P["rim_strength"])) + 1)
        px = self.out[3, 60].astype(float)
        r, g, b = rgb(P["rim"])
        self.assertAlmostEqual(px[2] / px[3], r / 255.0, delta=0.03)
        self.assertAlmostEqual(px[0] / px[3], b / 255.0, delta=0.03)

    def test_nothing_on_nothing(self):
        self.assertIsNone(hg.rim(canvas(10, 10)))


class Blur(unittest.TestCase):

    def test_flat_stays_flat_inside(self):
        a = np.ones((60, 60))
        out = hg.blur(a, 4)
        self.assertAlmostEqual(float(out[30, 30]), 1.0, places=6)

    def test_mass_is_kept_and_spread_evenly(self):
        a = np.zeros((61, 61))
        a[30, 30] = 1.0
        out = hg.blur(a, 4)
        self.assertAlmostEqual(float(out.sum()), 1.0, places=6)
        self.assertAlmostEqual(float(out[30, 25]), float(out[30, 35]))
        self.assertAlmostEqual(float(out[25, 30]), float(out[30, 25]))
        self.assertLess(float(out[30, 30]), 0.1)


class Numbers(unittest.TestCase):

    def test_the_chosen_look(self):
        """Prototype A, chosen 2026-10-02."""
        self.assertEqual((P["lo"], P["span"], P["radius"], P["gain"],
                          P["strength"]), (25.0, 70.0, 5.0, 2.2, 0.42))
        self.assertEqual((P["rim"], P["rim_strength"], P["rim_depth"]),
                         ("#fff1e2", 0.38, 6.0))

    def test_the_fade(self):
        self.assertEqual((motion.GLOW_IN_MS, motion.GLOW_OUT_MS), (110, 220))
        self.assertEqual(motion.glow_ms(True, 0.0, 1.0), 110)
        self.assertEqual(motion.glow_ms(False, 1.0, 0.0), 220)
        self.assertEqual(motion.glow_ms(False, 0.5, 0.0), 110)
        self.assertEqual(motion.glow_ms(True, 0.99, 1.0),
                         motion.LIGHT_MIN_MS)


class Purity(unittest.TestCase):

    def test_it_imports_no_qt_and_no_maya(self):
        code = ("import sys, maya_hubglow; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('PySide6', 'PySide2', 'maya', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()

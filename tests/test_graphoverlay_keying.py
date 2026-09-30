"""The Graph Editor's picture with its flat background taken out."""

import os
import subprocess
import sys
import unittest

import numpy as np

from maya_graphoverlay import keying

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


def frame(height=6, width=8, rgb=(64, 64, 64)):
    """A flat picture in QImage's ARGB32 byte order: B G R A."""
    bgra = np.zeros((height, width, 4), np.uint8)
    bgra[..., 0], bgra[..., 1], bgra[..., 2] = rgb[2], rgb[1], rgb[0]
    bgra[..., 3] = 255
    return bgra


class AlphaTable(unittest.TestCase):

    def test_it_rises_over_soft_levels(self):
        table = keying.alpha_table(28)
        self.assertEqual(table.dtype, np.uint8)
        self.assertEqual(len(table), 256)
        self.assertEqual(table[0], 0)
        self.assertEqual(table[14], 127)
        self.assertEqual(table[28], 255)
        self.assertEqual(table[255], 255)
        self.assertTrue(np.all(np.diff(table.astype(int)) >= 0))


class Background(unittest.TestCase):

    def test_the_commonest_colour_wins(self):
        bgra = frame(40, 40)
        bgra[5:8, :, :3] = (0, 170, 255)          # a curve across it
        self.assertEqual(keying.background(bgra, step=1), (64, 64, 64))

    def test_it_answers_r_g_b_from_b_g_r_bytes(self):
        self.assertEqual(keying.background(frame(rgb=(30, 20, 10)), step=1),
                         (30, 20, 10))


class KeyOut(unittest.TestCase):

    def setUp(self):
        self.table = keying.alpha_table(28)

    def test_the_background_goes_and_its_colour_stays(self):
        out = keying.key_out(frame(), (64, 64, 64), self.table)
        self.assertTrue(np.all(out[..., 3] == 0))
        self.assertTrue(np.all(out[..., :3] == 64))

    def test_a_curve_is_opaque_in_its_own_colour(self):
        bgra = frame()
        bgra[2, 3, :3] = (35, 35, 255)             # red, as B G R
        out = keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertEqual(out[2, 3, 3], 255)
        self.assertEqual(tuple(out[2, 3, :3]), (35, 35, 255))

    def test_the_farthest_channel_decides(self):
        bgra = frame()
        bgra[1, 1, :3] = (64, 78, 64)              # 14 levels over, green only
        bgra[1, 2, :3] = (50, 64, 64)              # 14 levels under, blue only
        out = keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertEqual(out[1, 1, 3], 127)
        self.assertEqual(out[1, 2, 3], 127)

    def test_bands_on_threads_give_the_same_picture(self):
        rng = np.random.default_rng(3)
        bgra = rng.integers(0, 256, (37, 23, 4), dtype=np.uint8)
        alone = keying.key_out(bgra, (64, 70, 80), self.table)
        pool = keying.make_pool(4)
        try:
            banded = keying.key_out(bgra, (64, 70, 80), self.table, pool,
                                    bands=4)
        finally:
            pool.shutdown()
        self.assertTrue(np.array_equal(alone, banded))

    def test_fewer_rows_than_bands(self):
        pool = keying.make_pool(4)
        try:
            out = keying.key_out(frame(2, 5), (64, 64, 64), self.table, pool,
                                 bands=4)
        finally:
            pool.shutdown()
        self.assertEqual(out.shape, (2, 5, 4))
        self.assertTrue(np.all(out[..., 3] == 0))

    def test_the_input_is_left_alone(self):
        bgra = frame()
        bgra[0, 0, :3] = (200, 10, 10)
        before = bgra.copy()
        keying.key_out(bgra, (64, 64, 64), self.table)
        self.assertTrue(np.array_equal(bgra, before))


class Purity(unittest.TestCase):

    def test_keying_and_geometry_import_neither_maya_nor_qt(self):
        code = ("import sys; import maya_graphoverlay.keying, "
                "maya_graphoverlay.geometry; "
                "print([m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'shiboken6')])")
        result = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), "[]", result.stderr)


if __name__ == "__main__":
    unittest.main()

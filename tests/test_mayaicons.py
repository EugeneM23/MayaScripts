"""maya_mayaicons / maya_mayaicons_art: Maya's icons in the hub's style
(2026-10-17) - the recolour, our drawings, writing into a folder and taking
only ours back out.

Spec: docs/superpowers/specs/2026-10-17-maya-icons-design.md
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np                                           # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets                  # noqa: E402

import maya_hubstyle as hubstyle                              # noqa: E402
import maya_mayaicons as icons                                # noqa: E402
import maya_mayaicons_art as art                              # noqa: E402

APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


def pixel(rgb, alpha=1.0):
    return np.array([[list(rgb) + [alpha]]], dtype=np.float32)


def hexrgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


class Recolour(unittest.TestCase):

    def test_a_light_grey_becomes_the_hub_s_text(self):
        out = icons.recolour(pixel([0.8, 0.8, 0.8]))[0, 0]
        np.testing.assert_allclose(out[:3], hexrgb(hubstyle.TOKENS["text"]),
                                   atol=0.01)

    def test_black_becomes_the_hub_s_darkest(self):
        out = icons.recolour(pixel([0, 0, 0]))[0, 0]
        np.testing.assert_allclose(out[:3], hexrgb(hubstyle.TOKENS["track"]),
                                   atol=0.01)

    def test_maya_s_blue_becomes_orange(self):
        out = icons.recolour(pixel([0.32, 0.52, 0.65]))[0, 0]
        self.assertGreater(out[0], out[1])
        self.assertGreater(out[1], out[2])

    def test_alpha_is_kept(self):
        out = icons.recolour(pixel([0.2, 0.6, 0.9], 0.37))[0, 0]
        self.assertAlmostEqual(float(out[3]), 0.37, places=5)

    def test_axis_icons_keep_red_green_blue_and_lose_cyan(self):
        for rgb in ([0.9, 0.1, 0.1], [0.2, 0.8, 0.2], [0.2, 0.3, 0.95]):
            kept = icons.recolour(pixel(rgb), keep_axes=True)[0, 0]
            np.testing.assert_allclose(kept[:3], rgb, atol=1e-6)
        cyan = icons.recolour(pixel([0.1, 0.8, 0.9]), keep_axes=True)[0, 0]
        self.assertGreater(cyan[0], cyan[2])
        self.assertIn("move_M", icons.AXES)

    def test_a_qimage_round_trip(self):
        img = QtGui.QImage(4, 3, QtGui.QImage.Format_ARGB32)
        img.fill(QtGui.QColor(10, 200, 30, 128))
        back = icons.from_array(icons.to_array(img))
        self.assertEqual((back.width(), back.height()), (4, 3))
        c = back.pixelColor(1, 1)
        self.assertEqual((c.red(), c.green(), c.blue(), c.alpha()),
                         (10, 200, 30, 128))


class Drawings(unittest.TestCase):

    def test_the_art_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_mayaicons_art; "
                "import maya_mayaicons; print([m for m in sys.modules if "
                "m.split('.')[0] in ('maya', 'PySide6', 'PySide2', 'numpy')])"
                ) % _PLUGIN
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=_PLUGIN).decode().strip()
        self.assertEqual(out, "[]")

    def test_about_a_hundred_and_fifty_drawn_and_the_rest_generated(self):
        self.assertGreaterEqual(len(art.ART), 140)
        self.assertEqual(len(art.LAYOUTS), 16)
        for partial, base in art.PARTIAL.items():
            self.assertIn(base, art.ART)
            self.assertTrue(partial.endswith("Partial"))

    def test_every_drawing_renders_with_ink_at_every_size(self):
        for name in art.NAMES:
            for size in (16, 20, 32):
                img = icons.render(name, size, size)
                a = icons.to_array(img)[..., 3]
                self.assertGreater(float((a > 0.3).mean()), 0.02,
                                   "%s at %d px is empty" % (name, size))

    def test_dashed_lines_draw(self):
        """QtSvg dropped the stroke of a dashed element whose dash was an
        attribute or a style (pickTemplate came out empty)."""
        img = icons.render("pickTemplate", 32, 32)
        self.assertGreater(float((icons.to_array(img)[..., 3] > 0.3).mean()),
                           0.03)

    def test_the_four_auto_tangents_differ(self):
        pics = [icons.to_array(icons.render(n, 20, 20)).tobytes() for n in
                ("autoTangent", "autocustomTangent", "autoeaseTangent",
                 "automixTangent")]
        self.assertEqual(len(set(pics)), 4)

    def test_a_layout_s_panels_fill_its_frame(self):
        self.assertEqual(len(art.layout_panels("defaultSingleLayout")), 1)
        self.assertEqual(len(art.layout_panels("defaultFourQuadLayout")), 4)
        big, *rest = art.layout_panels("defaultThreeSplitLeftLayout")
        self.assertEqual(len(rest), 2)
        self.assertGreater(big[2] * big[3], rest[0][2] * rest[0][3])
        for x, y, w, h in art.layout_panels("defaultFourSplitBottomLayout"):
            self.assertGreaterEqual(x, 3.4)
            self.assertLessEqual(x + w, 20.6)
            self.assertLessEqual(y + h, 19.6)

    def test_a_partial_is_its_mask_on_a_tint(self):
        self.assertIn("tint", art.body("pickJointObjPartial"))
        self.assertIn(art.ART["pickJointObj"], art.body("pickJointObjPartial"))


def maya_icon(colour, size=20):
    img = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
    img.fill(QtGui.QColor(colour))
    return img


class Folder(unittest.TestCase):

    def setUp(self):
        self.dest = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dest, ignore_errors=True)

    def sources(self):
        return [("move_M.png", maya_icon("#5285a6", 32)),
                ("somethingElse.png", maya_icon("#c0c0c0")),
                ("theirs.png", maya_icon("#c0c0c0"))]

    def test_written_drawn_or_recoloured_and_the_animator_s_kept(self):
        with open(os.path.join(self.dest, "theirs.png"), "wb") as handle:
            handle.write(b"their own icon")
        written, kept, stopped = icons.write_icons(self.dest, self.sources())
        self.assertEqual((written, kept, stopped), (2, ["theirs.png"], False))
        with open(os.path.join(self.dest, "theirs.png"), "rb") as handle:
            self.assertEqual(handle.read(), b"their own icon")
        drawn = QtGui.QImage(os.path.join(self.dest, "move_M.png"))
        self.assertEqual(drawn.width(), 32)            # Maya's own size
        other = QtGui.QImage(os.path.join(self.dest, "somethingElse.png"))
        self.assertEqual(other.pixelColor(5, 5).name(),
                         QtGui.QColor(*[int(round(v * 255)) for v in
                                        icons.recolour(pixel(hexrgb("#c0c0c0")))[0, 0][:3]]).name())
        manifest = json.load(open(os.path.join(self.dest, icons.MANIFEST)))
        self.assertEqual(sorted(manifest["files"]),
                         ["move_M.png", "somethingElse.png"])

    def test_a_second_on_rewrites_ours_only(self):
        icons.write_icons(self.dest, self.sources())
        written, kept, _ = icons.write_icons(self.dest, self.sources())
        self.assertEqual(written, 3)       # theirs.png was free the first time
        self.assertEqual(kept, [])

    def test_off_takes_out_ours_and_leaves_an_edited_one(self):
        with open(os.path.join(self.dest, "theirs.png"), "wb") as handle:
            handle.write(b"their own icon")
        icons.write_icons(self.dest, self.sources())
        with open(os.path.join(self.dest, "somethingElse.png"), "wb") as handle:
            handle.write(b"edited by hand")
        removed, changed = icons.remove_icons(self.dest)
        self.assertEqual((removed, changed), (1, ["somethingElse.png"]))
        self.assertEqual(sorted(os.listdir(self.dest)),
                         ["somethingElse.png", "theirs.png"])

    def test_a_stop_answers_stopped(self):
        _, _, stopped = icons.write_icons(self.dest, self.sources(),
                                          progress=lambda i, n: i < 1)
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()

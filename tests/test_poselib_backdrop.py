"""The backdrop a Pose Library card's picture is shot on (2026-10-15).

The animator: «Мы должны делать превью с разным фоном для поз оранжевый для анимаций голубой а не
закрашивать всю карточку каким-то оверлеем». `capture.backdrop(kind)` sets the viewport's
background colours for a blast and puts them back; tested on a fake `cmds` (the real playblast
needs a GUI Maya: the animator's check).
"""

import unittest

from maya_poselib import capture


class FakeCmds(object):

    def __init__(self, gradient=True):
        self.colours = {"background": [0.36, 0.36, 0.36], "backgroundTop": [0.5, 0.5, 0.5],
                        "backgroundBottom": [0.1, 0.1, 0.1]}
        self.gradient = gradient
        self.log = []

    def displayRGBColor(self, name, *rgb, **flags):
        if flags.get("query"):
            return list(self.colours[name])
        self.colours[name] = list(rgb)
        self.log.append((name, tuple(rgb)))

    def displayPref(self, query=False, displayGradient=None):
        if query:
            return self.gradient
        self.gradient = displayGradient
        self.log.append(("gradient", displayGradient))


class Backdrop(unittest.TestCase):

    def setUp(self):
        self.saved = capture.cmds
        self.fake = capture.cmds = FakeCmds()

    def tearDown(self):
        capture.cmds = self.saved

    def test_a_pose_is_shot_on_orange_and_everything_is_put_back(self):
        before = dict((k, list(v)) for k, v in self.fake.colours.items())
        with capture.backdrop("pose"):
            for name in capture.BACKDROP_COLOURS:
                self.assertEqual(self.fake.colours[name], list(capture.BACKDROPS["pose"]))
            self.assertFalse(self.fake.gradient)
            r, g, b = self.fake.colours["background"]
            self.assertGreater(r, b)                       # orange
        self.assertEqual(self.fake.colours, before)
        self.assertTrue(self.fake.gradient)

    def test_an_animation_is_shot_on_blue(self):
        with capture.backdrop("anim"):
            r, g, b = self.fake.colours["background"]
            self.assertGreater(b, r)

    def test_put_back_when_the_blast_raises(self):
        before = dict((k, list(v)) for k, v in self.fake.colours.items())
        with self.assertRaises(RuntimeError):
            with capture.backdrop("anim"):
                raise RuntimeError("playblast failed")
        self.assertEqual(self.fake.colours, before)
        self.assertTrue(self.fake.gradient)

    def test_a_flat_background_stays_flat(self):
        self.fake.gradient = False
        with capture.backdrop("pose"):
            pass
        self.assertNotIn(("gradient", True), self.fake.log)

    def test_an_unknown_kind_is_the_pose_colour(self):
        with capture.backdrop("objects"):
            self.assertEqual(self.fake.colours["background"], list(capture.BACKDROPS["pose"]))


try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


class StudioStops(unittest.TestCase):

    def test_light_in_the_middle_dark_at_the_corners(self):
        for kind in ("pose", "anim"):
            (_a, light), (_b, mid), (_c, dark) = capture.studio_stops(kind)
            self.assertGreater(sum(light), sum(mid))
            self.assertGreater(sum(mid), sum(dark))
        self.assertGreater(capture.studio_stops("pose")[1][1][0],
                           capture.studio_stops("pose")[1][1][2])      # orange
        self.assertGreater(capture.studio_stops("anim")[1][1][2],
                           capture.studio_stops("anim")[1][1][0])      # blue


@unittest.skipIf(QT is None, "no Qt")
class Studio(unittest.TestCase):

    def image(self, alpha):
        gui = QT.QtGui
        image = gui.QImage(100, 100, gui.QImage.Format_ARGB32)
        image.fill(gui.QColor(0, 0, 0, 0) if alpha else gui.QColor(40, 40, 40))
        painter = gui.QPainter(image)
        painter.fillRect(45, 30, 10, 50, gui.QColor(240, 240, 240))     # the character
        painter.end()
        return image

    def test_a_transparent_background_becomes_the_studio_light(self):
        out = capture.studio(QT, self.image(True), "pose")
        centre, corner = out.pixelColor(30, 40), out.pixelColor(1, 1)
        self.assertGreater(centre.lightness(), corner.lightness())
        self.assertGreater(centre.red(), centre.blue())
        self.assertEqual(out.pixelColor(50, 50).name(), "#f0f0f0")     # the character as shot
        blue = capture.studio(QT, self.image(True), "anim").pixelColor(30, 40)
        self.assertGreater(blue.blue(), blue.red())

    def test_an_opaque_blast_is_drawn_as_it_is(self):
        out = capture.studio(QT, self.image(False), "pose")
        self.assertEqual(out.pixelColor(1, 1).name(), "#282828")


if __name__ == "__main__":
    unittest.main()

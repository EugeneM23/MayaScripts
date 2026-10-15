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


if __name__ == "__main__":
    unittest.main()

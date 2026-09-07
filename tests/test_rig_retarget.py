import os
import unittest

import maya_asretarget as ar
import maya_pmretarget as pm
import maya_rig_retarget as rr


class TestInThePlugin(unittest.TestCase):
    """Since 2026-09-07 the three modules ship: the shelf buttons for them
    are the installer's, not the animator's hand-made ones a re-drag wipes."""

    def test_the_modules_live_in_the_plugin(self):
        for mod in (ar, pm, rr):
            self.assertEqual(
                os.path.basename(os.path.dirname(os.path.abspath(mod.__file__))),
                "SkeldarAnim", mod.__name__)


class TestButtons(unittest.TestCase):
    """The two shelf buttons forward and report; the report is a print plus
    an in-view message, and the text comes back for whoever called."""

    def setUp(self):
        self.saved = (rr.connect, rr.bake, rr._show)
        self.calls = []
        rr.connect = lambda *a, **k: self.calls.append("connect") or "connected 74"
        rr.bake = lambda *a, **k: self.calls.append("bake") or "baked 20"
        rr._show = lambda text: self.calls.append(text) or text

    def tearDown(self):
        rr.connect, rr.bake, rr._show = self.saved

    def test_retarget_button_connects_and_shows(self):
        self.assertEqual(rr.retarget_button(), "connected 74")
        self.assertEqual(self.calls, ["connect", "connected 74"])

    def test_bake_button_bakes_and_shows(self):
        self.assertEqual(rr.bake_button(), "baked 20")
        self.assertEqual(self.calls, ["bake", "baked 20"])

    def test_show_survives_a_viewport_less_session(self):
        rr._show = self.saved[2]
        self.assertEqual(rr._show("two\nlines"), "two\nlines")

OWN = ["Root", "Hip", "Spine1", "Spine2", "Spine3", "Spine4", "Neck", "Head", "Right_Arm", "Left_Hand", "Right_Toes"]
UE5 = ["root", "pelvis", "spine_01", "spine_05", "upperarm_l", "hand_r", "ball_l", "neck_01", "head"]
UE4 = ["root", "pelvis", "spine_01", "spine_03", "upperarm_l", "hand_r", "ball_l", "neck_01", "head"]


class TestPick(unittest.TestCase):

    def test_the_lugal_rig_goes_to_the_playermale_module(self):
        self.assertEqual(rr.pick(OWN), (pm, ""))

    def test_the_manny_rig_goes_to_the_manny_module_whether_ue5_or_ue4(self):
        self.assertEqual(rr.pick(UE5), (ar, ""))
        self.assertEqual(rr.pick(UE4), (ar, ""))

    def test_an_unknown_skeleton_is_refused_by_name(self):
        mod, why = rr.pick(["hips", "chest", "l_arm"], "|hips")
        self.assertIsNone(mod)
        self.assertIn("|hips", why)
        self.assertIn("Manny", why)
        self.assertIn("Lugal", why)

    def test_every_forwarder_exists_on_both_modules(self):
        for name in ("report", "connect", "bake", "disconnect"):
            self.assertTrue(callable(getattr(rr, name)))
            self.assertTrue(callable(getattr(ar, name)), name)
            self.assertTrue(callable(getattr(pm, name)), name)


class TestNativeBake(unittest.TestCase):
    """Since 2026-09-07 both modules bake through their own `vendor_bake` --
    the vendor's proc in cmds -- and neither reaches for MEL at all, so a
    session that never sourced AdvancedSkeleton can still press Bake."""

    def _source(self, mod):
        with open(mod.__file__.replace(".pyc", ".py"), encoding="utf-8") as fh:
            return fh.read()

    def test_both_modules_carry_the_native_bake_and_no_mel(self):
        for mod in (ar, pm):
            src = self._source(mod)
            self.assertIn("def vendor_bake(start, end):", src, mod.__name__)
            self.assertIn("def connected_source():", src, mod.__name__)
            self.assertNotIn("mel.eval(", src, mod.__name__)
            self.assertNotIn("import maya.mel", src, mod.__name__)
        self.assertIn("NOTHING", ar.disconnect.__doc__)

    def test_the_playermale_module_still_imports_nothing_from_its_sibling(self):
        src = self._source(pm)
        self.assertFalse("import maya_asretarget" in src
                         or "from maya_asretarget" in src)


if __name__ == "__main__":
    unittest.main()

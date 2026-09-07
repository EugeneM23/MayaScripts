import os
import types
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



class TestHelperPlan(unittest.TestCase):
    """The four bones the rig leaves riding their parents (2026-09-07): moved
    when both skeletons have them, named when not."""

    SRC = {"weapon_r": "|a:root|a:hand_r|a:weapon_r",
           "camera_root": "|a:root|a:camera_root"}
    DST = {"weapon_r": "|root|hand_r|weapon_r", "weapon_l": "|root|hand_l|weapon_l",
           "camera_root": "|root|camera_root",
           "camera_bone": "|root|camera_root|camera_bone"}

    def test_moves_what_both_have_and_names_the_rest(self):
        moves, skipped = rr.helper_plan(self.SRC, self.DST)
        self.assertEqual(moves, [("weapon_r", self.SRC["weapon_r"], self.DST["weapon_r"]),
                                 ("camera_root", self.SRC["camera_root"], self.DST["camera_root"])])
        self.assertEqual(dict(skipped), {"weapon_l": "not in the source",
                                         "camera_bone": "not in the source"})

    def test_a_foreign_constraint_is_skipped_by_name(self):
        moves, skipped = rr.helper_plan(self.SRC, self.DST, foreign={"camera_root"})
        self.assertEqual([m[0] for m in moves], ["weapon_r"])
        self.assertEqual(dict(skipped)["camera_root"], "driven by somebody else's constraint")

    def test_a_rig_without_the_bone_says_nothing(self):
        """The PlayerMale skeleton has none of the four."""
        moves, skipped = rr.helper_plan(self.SRC, {"Hip": "|Root|Hip"})
        self.assertEqual((moves, skipped), ([], []))

    def test_the_order_is_the_tables(self):
        both = dict(self.DST)
        moves, _ = rr.helper_plan(both, both)
        self.assertEqual([m[0] for m in moves], list(rr.HELPER_BONES))


class TestHelperNote(unittest.TestCase):

    def test_names_what_moved_what_was_skipped_and_the_camera(self):
        text = rr.helper_note(["weapon_r", "camera_bone"],
                              [("weapon_l", "not in the source")],
                              "camera SceneSetup_camera on camera_bone (46 frames)")
        self.assertIn("weapon_r, camera_bone carried from the source", text)
        self.assertIn("skipped weapon_l (not in the source)", text)
        self.assertIn("SceneSetup_camera", text)

    def test_nothing_is_an_empty_tail(self):
        self.assertEqual(rr.helper_note([], [], ""), "")


class FakeBakeScene(object):
    """cmds for the dispatcher's bake(): undo chunks and a playback range."""

    def __init__(self):
        self.chunks = []

    def undoInfo(self, **kwargs):
        self.chunks.append(kwargs)

    def playbackOptions(self, **kwargs):
        return 0.0 if kwargs.get("min") else 100.0


class TestBakeOrchestration(unittest.TestCase):
    """bake() runs the six steps in order and words the result."""

    def setUp(self):
        self.saved = (rr.rig_module, rr.carry_helpers, rr.cmds)
        self.calls = []
        mod = types.SimpleNamespace(
            __name__="maya_asretarget",
            connected_source=lambda: "|clip:root",
            source_key_range=lambda: (3.0, 41.0),
            rig_paths=lambda: ["|root"],
            rig_skeleton_root=lambda paths: "|root",
            bake=lambda disconnect=True: self.calls.append(("bake", disconnect))
            or "baked 20 controls over 3..41; still connected - disconnect() when done",
            disconnect=lambda: self.calls.append(("disconnect",)) or "retarget disconnected (82 constraints)")
        self.mod = mod
        rr.rig_module = lambda: (mod, "")
        rr.carry_helpers = lambda source, rig, start, end: (
            self.calls.append(("carry", source, rig, start, end))
            or (["weapon_r", "camera_bone"], [], "camera SceneSetup_camera on camera_bone (39 frames)"))
        rr.cmds = FakeBakeScene()

    def tearDown(self):
        rr.rig_module, rr.carry_helpers, rr.cmds = self.saved

    def test_the_steps_run_in_order_over_the_clips_range(self):
        text = rr.bake()
        self.assertEqual(self.calls, [("bake", False), ("carry", "|clip:root", "|root", 3.0, 41.0),
                                      ("disconnect",)])
        self.assertIn("baked 20 controls over 3..41", text)
        self.assertNotIn("still connected", text)
        self.assertIn("retarget disconnected", text)
        self.assertIn("weapon_r, camera_bone carried", text)
        self.assertIn("SceneSetup_camera", text)
        self.assertTrue(text.startswith("maya_asretarget: "))

    def test_one_undo_chunk_closed_even_when_a_step_raises(self):
        def explode(*a, **k):
            raise RuntimeError("boom")
        rr.carry_helpers = explode
        with self.assertRaises(RuntimeError):
            rr.bake()
        self.assertEqual([c.get("openChunk") for c in rr.cmds.chunks][:1], [True])
        self.assertTrue(rr.cmds.chunks[-1].get("closeChunk"))

    def test_nothing_connected_defers_to_the_module(self):
        self.mod.connected_source = lambda: None
        self.mod.bake = lambda *a, **k: "nothing connected (MoCapConstraints not found) - connect() first"
        self.assertIn("nothing connected", rr.bake())
        self.assertEqual(self.calls, [])

    def test_a_missing_rig_is_the_dispatchers_refusal(self):
        rr.rig_module = lambda: (None, "no AdvancedSkeleton rig in this scene")
        self.assertEqual(rr.bake(), "no AdvancedSkeleton rig in this scene")


if __name__ == "__main__":
    unittest.main()

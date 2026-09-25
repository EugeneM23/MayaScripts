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
    """ONE shelf button since 2026-09-08: it runs the whole retarget and
    reports; the report is a print plus an in-view message, and the text
    comes back for whoever called."""

    def setUp(self):
        self.saved = (rr.retarget, rr._show)
        self.calls = []
        rr.retarget = lambda *a, **k: self.calls.append("retarget") or "Group: connected 74  |  baked"
        rr._show = lambda text: self.calls.append(text) or text

    def tearDown(self):
        rr.retarget, rr._show = self.saved

    def test_retarget_button_runs_the_whole_retarget_and_shows(self):
        self.assertEqual(rr.retarget_button(), "Group: connected 74  |  baked")
        self.assertEqual(self.calls, ["retarget", "Group: connected 74  |  baked"])

    def test_there_is_no_bake_button_any_more(self):
        self.assertFalse(hasattr(rr, "bake_button"))
        self.assertTrue(callable(rr.bake))      # the API stays for the bridge

    def test_show_survives_a_viewport_less_session(self):
        rr._show = self.saved[1]
        self.assertEqual(rr._show("two\nlines"), "two\nlines")


LEGACY = rr.maya_rigs.Rig("", "ControlSet", "|Group|MotionSystem|MainSystem|Main",
                          "|Group", "|root")


class FakeRunScene(object):
    """cmds for run_retarget: undo chunks recorded, the holder's existence
    scripted per call."""

    def __init__(self, holder_exists):
        self.chunks = []
        self.holder_exists = list(holder_exists)

    def undoInfo(self, **kwargs):
        self.chunks.append(kwargs)

    def objExists(self, name):
        return self.holder_exists.pop(0) if self.holder_exists else False

    def playbackOptions(self, **kwargs):
        return 0.0 if kwargs.get("min") else 100.0


class FakeModule(object):
    def __init__(self, calls, posed=()):
        self.__name__ = "maya_asretarget"
        self.calls = calls
        self.posed = list(posed)

    def holder_of(self, rig):
        return "MoCapConstraints"

    def reset_build_pose(self, rig=None):
        self.calls.append(("reset", rig.namespace))
        return 12, 3

    def posed_controls(self, tol=1e-3, rig=None):
        return self.posed

    def connect(self, source_root=None, rig=None):
        self.calls.append(("connect", source_root, rig.namespace))
        return "retarget connected: 74 controls of Group driven from clip\nmore lines"


class TestRunRetarget(unittest.TestCase):
    """The one button: reset, connect, bake -- or bake alone over a standing
    holder -- under one undo chunk, with the refusals by name."""

    def setUp(self):
        self.saved = (rr.resolve, rr.bake, rr.cmds, rr.hands_connected)
        #  the Connections guard (2026-09-18) reads the real scene; these
        #  tests fake rr.cmds, so it answers "not connected" here
        rr.hands_connected = lambda rig: ""
        self.calls = []
        self.mod = FakeModule(self.calls)
        rr.resolve = lambda rig=None: (LEGACY, self.mod, "")
        rr.bake = lambda rig=None: self.calls.append(("bake", rig.namespace)) or "maya_asretarget: baked 20"

    def tearDown(self):
        rr.resolve, rr.bake, rr.cmds, rr.hands_connected = self.saved

    def test_a_fresh_rig_is_reset_connected_and_baked(self):
        # holder: absent at the start, present after connect
        rr.cmds = FakeRunScene([False, True])
        ok, text = rr.run_retarget("|clip:root")
        self.assertTrue(ok)
        self.assertEqual(self.calls, [("reset", ""), ("connect", "|clip:root", ""), ("bake", "")])
        self.assertIn("previous take cleared (12 curves)", text)
        self.assertIn("retarget connected: 74 controls", text)
        self.assertNotIn("more lines", text)
        self.assertIn("baked 20", text)
        self.assertTrue(text.startswith("Group: "))
        self.assertEqual([c.get("openChunk") for c in rr.cmds.chunks][:1], [True])
        self.assertTrue(rr.cmds.chunks[-1].get("closeChunk"))

    def test_a_standing_holder_is_baked_not_refused(self):
        rr.cmds = FakeRunScene([True])
        ok, text = rr.run_retarget()
        self.assertTrue(ok)
        self.assertEqual(self.calls, [("bake", "")])
        self.assertIn("already connected", text)

    def test_a_rig_still_posed_after_the_reset_is_refused_by_name(self):
        rr.cmds = FakeRunScene([False])
        self.mod.posed = ["FKElbow_R", "FKWrist_R"]
        ok, text = rr.run_retarget()
        self.assertFalse(ok)
        self.assertIn(rr.POSED, text)
        self.assertIn("FKElbow_R, FKWrist_R", text)
        self.assertEqual(self.calls, [("reset", "")])
        self.assertTrue(rr.cmds.chunks[-1].get("closeChunk"))

    def test_a_connect_refusal_is_reported_and_nothing_is_baked(self):
        rr.cmds = FakeRunScene([False, False])
        self.mod.connect = lambda source_root=None, rig=None: "nothing selected - select any joint"
        ok, text = rr.run_retarget()
        self.assertFalse(ok)
        self.assertIn("retarget refused: nothing selected", text)
        self.assertEqual([c for c in self.calls if c[0] == "bake"], [])

    def test_no_rig_is_the_resolvers_refusal(self):
        rr.resolve = lambda rig=None: (None, None, "2 rigs in the scene (a, b) - select")
        self.assertEqual(rr.run_retarget(), (False, "2 rigs in the scene (a, b) - select"))
        self.assertEqual(rr.retarget(), "2 rigs in the scene (a, b) - select")

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
            self.assertIn("def vendor_bake(start, end, rig=None):", src, mod.__name__)
            self.assertIn("def connected_source(rig=None):", src, mod.__name__)
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
        self.saved = (rr.resolve, rr.carry_helpers, rr.cmds, rr.hands_connected)
        rr.hands_connected = lambda rig: ""
        self.calls = []
        mod = types.SimpleNamespace(
            __name__="maya_asretarget",
            connected_source=lambda rig=None: "|clip:root",
            source_key_range=lambda rig=None: (3.0, 41.0),
            bake=lambda disconnect=True, rig=None: self.calls.append(("bake", disconnect, rig.namespace))
            or "baked 20 controls over 3..41; still connected - disconnect() when done",
            disconnect=lambda rig=None: self.calls.append(("disconnect",)) or "retarget disconnected (82 constraints)")
        self.mod = mod
        rr.resolve = lambda rig=None: (LEGACY, mod, "")
        rr.carry_helpers = lambda source, rig, start, end, relative=False: (
            self.calls.append(("carry", source, rig, start, end) + (("relative",) if relative else ()))
            or (["weapon_r", "camera_bone"], [], "camera SceneSetup_camera on camera_bone (39 frames)"))
        rr.cmds = FakeBakeScene()

    def tearDown(self):
        rr.resolve, rr.carry_helpers, rr.cmds, rr.hands_connected = self.saved

    def test_the_steps_run_in_order_over_the_clips_range(self):
        text = rr.bake()
        self.assertEqual(self.calls, [("bake", False, ""), ("carry", "|clip:root", "|root", 3.0, 41.0),
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
        self.mod.connected_source = lambda rig=None: None
        self.mod.bake = lambda *a, **k: "nothing connected (MoCapConstraints not found) - connect() first"
        self.assertIn("nothing connected", rr.bake())
        self.assertEqual(self.calls, [])

    def test_a_rotation_only_rig_carries_the_helper_bones_in_their_parents_space(self):
        """2026-09-24, the Creep: his arms are 26% longer than the source's, so a
        weapon_r carried in WORLD space would float off his hand. A rig marked
        rotation-only takes each helper bone relative to its parent (hand_r)."""
        self.mod.rotation_mode = lambda rig: True
        rr.bake()
        self.assertEqual(self.calls[1], ("carry", "|clip:root", "|root", 3.0, 41.0, "relative"))

    def test_the_space_is_world_unless_the_module_says_rotation_only(self):
        self.assertEqual(rr.helper_space(self.mod, LEGACY), "world")
        self.mod.rotation_mode = lambda rig: False
        self.assertEqual(rr.helper_space(self.mod, LEGACY), "world")
        self.mod.rotation_mode = lambda rig: True
        self.assertEqual(rr.helper_space(self.mod, LEGACY), "parent")
    def test_a_missing_rig_is_the_dispatchers_refusal(self):
        rr.resolve = lambda rig=None: (None, None, "no AdvancedSkeleton rig in this scene")
        self.assertEqual(rr.bake(), "no AdvancedSkeleton rig in this scene")


if __name__ == "__main__":
    unittest.main()

"""The two retarget versions wired into the presses (2026-10-02): the drive plans,
the Retarget button, the bridge's rig / skeleton / batch imports - which version
runs, when the press asks, and that a Cancel changes nothing."""
import sys
import types
import unittest

import maya_asretarget as ar
import maya_pmretarget as pm
import maya_retargetmode as rm
import maya_rig_retarget as rr
from maya_uebridge import lineimport, rigimport, skeletonimport as si

from tests.uifakes import FakeUiCmds

CONTROLS = ar.candidates(ar.UE5)
BONES = [b for _, b in ar.ROWS] + ["root", "pelvis"]
BONES = [b + s for b in BONES for s in ("", "_l", "_r")]


def creep_measure(source="Clip", target="Creep_Rig"):
    return rm.measure([("upperarm_l", 28.0, 34.8), ("lowerarm_l", 27.0, 36.0),
                       ("thigh_l", 45.0, 45.0), ("calf_l", 43.0, 43.0),
                       ("neck_01", 12.0, 16.0)], None, source, target)


def twin_measure(source="Clip", target="Manny_Rig"):
    return rm.measure([("upperarm_l", 28.0, 28.0), ("thigh_l", 45.0, 45.0),
                       ("calf_l", 43.0, 43.0)], None, source, target)


class Answers(object):
    def __init__(self, button):
        self.button, self.asked = button, []

    def __call__(self, text):
        self.asked.append(text)
        return self.button


class AsDrivePlan(unittest.TestCase):
    """maya_asretarget: the stretch onto another body is the rotation plan whose FK
    controls take position too; the twin's stretch is the old twin plan."""

    def test_scaled_fk_controls_take_position_and_ik_follows_our_fk(self):
        drives, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, scaled=True)
        fk = [d for d in drives if d.control.startswith("FK")]
        self.assertTrue(fk and all(d.translate and d.rotate and not d.own for d in fk))
        own = [d for d in drives if d.own]
        self.assertTrue(own and all(d.bone.startswith("FKX") for d in own))
        main = [d for d in drives if d.control in ("Main", "RootX_M")]
        self.assertEqual(sorted(d.control for d in main), ["Main", "RootX_M"])

    def test_rotations_take_no_position(self):
        drives, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, rotation=True)
        self.assertTrue(all(not d.translate for d in drives if d.control.startswith("FK")))

    def test_the_twin_stretch_is_the_legacy_plan(self):
        self.assertEqual(ar.drive_plan(CONTROLS, BONES, ar.UE5),
                         ar.drive_plan(CONTROLS, BONES, ar.UE5, rotation=False, scaled=False))

    def test_pairs_read_our_bone_against_the_clips(self):
        drives, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, rotation=True)
        rig_bones = dict((b, "|" + b) for b in BONES)
        pairs = ar.pairs_of(drives, rig_bones)
        self.assertEqual(pairs["upperarm_l"], "upperarm_l")
        self.assertEqual(pairs["root"], "root")
        self.assertNotIn("FKXWrist_L", pairs.values())     # our own FK, not the clip's

    def test_mixamo_pairs_through_the_map(self):
        mixamo = ["Hips", "Spine", "Spine1", "Spine2", "LeftArm", "LeftForeArm", "LeftHand"]
        drives, _ = ar.drive_plan(CONTROLS, mixamo, ar.MIXAMO, rotation=True)
        pairs = ar.pairs_of(drives, dict((b, "|" + b) for b in BONES))
        self.assertEqual(pairs["upperarm_l"], "LeftArm")
        self.assertEqual(pairs["spine_05"], "Spine2")

    def test_the_status_says_squash_and_stretch(self):
        self.assertIn("squash & stretch", ar.stretch_note(1.0))

    def test_only_orientation_driven_bones_get_a_position_follow(self):
        rows = [("upperarm_l", {"orientConstraint": ["|G|Shoulder_L"]}, False),
                ("pelvis", {"orientConstraint": ["|G|Root_M"], "pointConstraint": ["|G|Root_M"]}, False),
                ("ik_hand_r", {"parentConstraint": ["|hand_r"]}, False),
                ("upperarm_twist_01_l", {"orientConstraint": ["|G|ShoulderPart1_L"]}, True),
                ("weapon_r", {}, False),
                ("odd", {"orientConstraint": ["|a", "|b"]}, False)]
        self.assertEqual(ar.follow_plan(rows), [("upperarm_l", "|G|Shoulder_L")])


class PmPairs(unittest.TestCase):

    def test_fk_and_the_pelvis_against_the_clip(self):
        drives = [pm.Drive("FKShoulder_R", "upperarm_r", "fk"), pm.Drive("RootX_M", "pelvis", "pelvis"),
                  pm.Drive("IKArm_R", "FKXWrist_R", "ik")]
        pairs = pm.pairs_of(drives)
        self.assertEqual(pairs[pm.our_bone("FKShoulder_R")], "upperarm_r")
        self.assertEqual(pairs[pm.OUR_PELVIS], "pelvis")
        self.assertEqual(len(pairs), 2)


class TheButton(unittest.TestCase):
    """maya_rig_retarget: asked BEFORE the reset; Cancel touches nothing."""

    def setUp(self):
        self.saved = (rr.resolve, rr.bake, rr.cmds, rr.hands_connected)
        rr.hands_connected = lambda rig: ""
        self.calls = []
        rig = types.SimpleNamespace(namespace="Creep_Rig", label="Creep_Rig")
        calls = self.calls

        class Mod(object):
            __name__ = "maya_asretarget"

            def holder_of(self, rig):
                return "Creep_Rig:MoCapConstraints"

            def measure(self, source_root=None, rig=None):
                calls.append(("measure", source_root))
                return creep_measure(), ""

            def reset_build_pose(self, rig=None):
                calls.append(("reset",))
                return 0, 0

            def posed_controls(self, tol=1e-3, rig=None):
                return []

            def connect(self, source_root=None, rig=None, bones=None):
                calls.append(("connect", bones))
                held.append(True)
                return "retarget connected"

        held = []
        rr.resolve = lambda rig=None: (rig_, Mod(), "")
        rig_ = rig
        rr.bake = lambda rig=None: calls.append(("bake",)) or "baked"
        rr.cmds = types.SimpleNamespace(
            objExists=lambda name: bool(held),
            undoInfo=lambda **k: None)
        rr.maya_rigs = types.SimpleNamespace(label=lambda r: r.namespace,
                                             current_rig=lambda: (rig_, ""))

    def tearDown(self):
        rr.resolve, rr.bake, rr.cmds, rr.hands_connected = self.saved
        import maya_rigs
        rr.maya_rigs = maya_rigs
        rm.set_asker(None)

    def test_keep_runs_the_rotations_and_says_why(self):
        answers = Answers(rm.KEEP)
        rm.set_asker(answers)
        ok, text = rr.run_retarget("|clip:root")
        self.assertTrue(ok)
        self.assertEqual(len(answers.asked), 1)
        self.assertEqual([c for c in self.calls if c[0] != "measure"],
                         [("reset",), ("connect", rm.ROTATION), ("bake",)])
        self.assertIn("rotations - Creep_Rig keeps its proportions", text)

    def test_squash_runs_the_stretch(self):
        rm.set_asker(Answers(rm.SQUASH))
        ok, text = rr.run_retarget("|clip:root")
        self.assertIn(("connect", rm.STRETCH), self.calls)
        self.assertIn("stretch - Creep_Rig squashed & stretched", text)

    def test_cancel_changes_nothing(self):
        rm.set_asker(Answers(rm.CANCEL))
        ok, text = rr.run_retarget("|clip:root")
        self.assertFalse(ok)
        self.assertIn(rr.CANCELLED, text)
        self.assertEqual([c[0] for c in self.calls], ["measure"])

    def test_a_forced_version_is_never_asked(self):
        answers = Answers(rm.CANCEL)
        rm.set_asker(answers)
        rr.run_retarget("|clip:root", bones=rm.STRETCH)
        self.assertEqual(answers.asked, [])
        self.assertIn(("connect", rm.STRETCH), self.calls)
        self.assertNotIn(("measure", "|clip:root"), self.calls)


class Decide(unittest.TestCase):

    def test_a_module_that_cannot_measure_is_the_legacy_call(self):
        self.assertEqual(rr.decide_for(types.SimpleNamespace(), None).mode, None)
        self.assertEqual(rr.connect_kwargs(rr.decide_for(types.SimpleNamespace(), None)), {})

    def test_a_refused_measure_is_the_legacy_call(self):
        mod = types.SimpleNamespace(measure=lambda source_root=None, rig=None: (None, "nothing selected"))
        self.assertEqual(rr.decide_for(mod, None).mode, None)

    def test_the_kwargs(self):
        self.assertEqual(rr.connect_kwargs(rm.Decision(rm.STRETCH, False, "")), {"bones": rm.STRETCH})


class HelperSpace(unittest.TestCase):
    """The helper bones (weapon/camera) carried in world space only for the twin's
    exact stretch; the rotations and the scaled stretch relative to their parent."""

    def test_by_the_standing_version(self):
        for mode, space in (("twin", "world"), ("rotation", "parent"), ("stretch", "parent")):
            mod = types.SimpleNamespace(connected_mode=lambda rig, m=mode: m,
                                        rotation_mode=lambda rig: False)
            self.assertEqual(rr.helper_space(mod, None), space, mode)

    def test_a_legacy_connect_reads_the_mark(self):
        mod = types.SimpleNamespace(connected_mode=lambda rig: None, rotation_mode=lambda rig: True)
        self.assertEqual(rr.helper_space(mod, None), "parent")


class Card(unittest.TestCase):
    """[Auto | Rotations | Stretch] in the Retarget card."""

    def test_three_segments_auto_lit(self):
        fake = FakeUiCmds()
        saved = rr.cmds
        rr.cmds = fake
        try:
            rr.build_panel()
        finally:
            rr.cmds = saved
        made = [(c[1][0] if c[1] else None, c[2]) for c in fake.calls if c[0] == "iconTextRadioButton"]
        self.assertEqual([m[0] for m in made], [rr.bones_button(v) for v in rm.SETTINGS])
        self.assertEqual([m[1]["label"] for m in made], ["Auto", "Rotations", "Stretch"])
        self.assertEqual([bool(m[1].get("select")) for m in made], [True, False, False])
        self.assertIn(("iconTextRadioCollection", (rr.BONES,), {}),
                      [(c[0], c[1], c[2]) for c in fake.calls])


class SkeletonDrives(unittest.TestCase):

    def test_the_versions(self):
        self.assertEqual(si.drive_for("upperarm_l", False, True, "stretch"), "parent")
        self.assertEqual(si.drive_for("upperarm_l", False, True, "rotation"), "orient")
        self.assertEqual(si.drive_for("root", True, True, "rotation"), "orient+point")
        self.assertEqual(si.drive_for("upperarm_l", False, False, "stretch"), "orient+scaled")
        self.assertEqual(si.drive_for("root", True, False, "stretch"), "orient+scaled")
        self.assertIsNone(si.drive_for("ik_hand_gun", False, False, "stretch"))
        self.assertEqual(si.drive_for("upperarm_l", False, False, None), "orient")

    def test_the_line_says_which(self):
        r = dict(twin=False, moved=89, skipped=[], missing=[], mode="stretch")
        self.assertIn("89 bones squashed & stretched to the clip",
                      si.result_line("A", "Creep [skeleton]", "root", r, {}))
        r = dict(twin=True, moved=89, skipped=[], missing=[], mode="rotation")
        self.assertIn("by rotation", si.result_line("A", "Manny", "root", r, {}))


class SkeletonCancel(unittest.TestCase):
    """onto_skeleton: Cancel deletes the skeleton it added and the clip's namespace."""

    def setUp(self):
        self.calls = []
        saved = dict(cmds=si.cmds, new=si.new_skeleton, transfer=si.transfer, discard=si.discard_new)

        def restore():
            si.cmds, si.new_skeleton = saved["cmds"], saved["new"]
            si.transfer, si.discard_new = saved["transfer"], saved["discard"]
        self.addCleanup(restore)
        si.new_skeleton = lambda entry: (self.calls.append(("add",)) or ("|root1", "added"))
        si.discard_new = lambda root: self.calls.append(("discard", root))
        self.twins = []
        si.transfer = lambda source, root, start, end, mode=None, twin=None: (
            self.calls.append(("transfer", mode)) or self.twins.append(twin) or
            dict(twin=bool(twin), moved=89, skipped=[], missing=[], mode=mode))
        si.cmds = types.SimpleNamespace(
            ls=lambda node, uuid=False, long=False: ["UUID"] if uuid else ["|root1"],
            namespace=lambda **k: self.calls.append(("delete_ns", k.get("removeNamespace"))))
        self.entry = types.SimpleNamespace(label="Creep [skeleton]", key="Creep_Skeleton")

    def test_cancel(self):
        def decide(source, root, label, start):
            raise rm.Cancelled("A")
        with self.assertRaises(rm.Cancelled):
            si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0}, "|A:root", "A",
                             None, decide=decide)
        self.assertEqual(self.calls, [("add",), ("discard", "|root1"), ("delete_ns", "A")])

    def test_the_decided_version_reaches_the_transfer_and_the_line(self):
        decide = lambda source, root, label, start: rm.Decision(rm.STRETCH, False, "stretch - why")
        line, failure, _top = si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0},
                                               "|A:root", "A", None, decide=decide)
        self.assertIn(("transfer", rm.STRETCH), self.calls)
        self.assertTrue(line.endswith("stretch - why"))

    def test_the_transfer_runs_on_the_verdict_the_line_reports(self):
        # the fix pass: the press decided "twin" on retargetmode's measure; the transfer
        # must not judge again by its own rule and run the other version
        for twin in (True, False):
            del self.twins[:]
            decide = lambda source, root, label, start, t=twin: rm.Decision(
                rm.STRETCH, False, "stretch - why", t)
            si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0}, "|A:root", "A", None,
                             decide=decide)
            self.assertEqual(self.twins, [twin])


class RigImportCancel(unittest.TestCase):
    """import_and_retarget: the clip in, the question, Cancel - the clip's namespace
    gone, an added rig deleted, the standing rig never reset."""

    def setUp(self):
        self.calls = []
        names = ("plan_press", "ready_rig", "import_source", "decide_bones", "discard_added",
                 "retarget_imported", "rig_place", "cmds")
        self.saved = dict((n, getattr(rigimport, n)) for n in names)
        self.addCleanup(lambda: [setattr(rigimport, n, v) for n, v in self.saved.items()])
        self.rig = types.SimpleNamespace(namespace="Creep_Rig", main="Creep_Rig:Main")
        rigimport.rig_place = lambda rig: {"point": (0, 0, 0), "yaw": 0.0, "kept": True}
        rigimport.ready_rig = lambda plan: (self.calls.append(("ready", plan["add"])) or
                                            (self.rig, "mod", [], ""))
        rigimport.import_source = lambda *a, **k: (self.calls.append(("import",)) or
                                                   ("A", {"start": 0.0, "end": 9.0}, "|A:root"))
        rigimport.discard_added = lambda rig: self.calls.append(("discard", rig.namespace))
        rigimport.retarget_imported = lambda *a, **k: (self.calls.append(("retarget", k.get("bones")))
                                                       or ("line", ""))
        rigimport.cmds = types.SimpleNamespace(
            undoInfo=lambda **k: None,
            namespace=lambda **k: self.calls.append(("delete_ns", k.get("removeNamespace"))))

        def cancel(rig, mod, source):
            self.calls.append(("decide",))
            raise rm.Cancelled("A")
        rigimport.decide_bones = cancel

    def test_onto_a_standing_rig(self):
        rigimport.plan_press = lambda target, rig=None: (dict(rig=self.rig, mod="mod", add=False, entry=None), "")
        self.assertEqual(rigimport.import_and_retarget("C:/A.fbx", "A"), rigimport.CANCELLED)
        self.assertEqual(self.calls, [("import",), ("decide",), ("delete_ns", "A")])

    def test_onto_a_new_rig(self):
        rigimport.plan_press = lambda target, rig=None: (dict(rig=None, mod=None, add=True, entry="e"), "")
        self.assertEqual(rigimport.import_and_retarget("C:/A.fbx", "A", target="new_rig"),
                         rigimport.CANCELLED)
        self.assertEqual(self.calls, [("ready", True), ("import",), ("decide",), ("delete_ns", "A"),
                                      ("discard", "Creep_Rig")])

    def test_an_answer_reaches_the_retarget(self):
        rigimport.plan_press = lambda target, rig=None: (dict(rig=self.rig, mod="mod", add=False, entry=None), "")
        rigimport.decide_bones = lambda rig, mod, source: rm.Decision(rm.STRETCH, False, "stretch - why")
        text = rigimport.import_and_retarget("C:/A.fbx", "A")
        self.assertEqual(self.calls, [("import",), ("ready", False), ("retarget", rm.STRETCH)])
        self.assertIn("stretch - why", text)


class BatchOnce(unittest.TestCase):
    """lineimport's _Versions: every clip measured against the first target, asked once."""

    def tearDown(self):
        rm.set_asker(None)

    def test_one_question_for_the_batch(self):
        answers = Answers(rm.KEEP)
        rm.set_asker(answers)
        clips = [dict(source="|A:root", info={"start": 0}), dict(source="|B:root", info={"start": 0}),
                 dict(source="|C:root", info={"start": 0})]
        measures = {"|A:root": twin_measure("A"), "|B:root": creep_measure("B"),
                    "|C:root": creep_measure("C")}
        mod = types.SimpleNamespace(measure=lambda source_root=None, rig=None: (measures[source_root], ""))
        versions = lineimport._Versions(clips)
        modes = [versions.for_rig(i, "rig", mod).mode for i in range(3)]
        self.assertEqual(modes, [rm.STRETCH, rm.ROTATION, rm.ROTATION])
        self.assertEqual(len(answers.asked), 1)
        self.assertIn("all 2 animations", answers.asked[0])
        # B and C share one reason (the same rig, the same difference): said once
        self.assertEqual(len(versions.reasons()), 2)

    def test_a_module_that_cannot_measure(self):
        versions = lineimport._Versions([dict(source="|A:root", info={})])
        self.assertIsNone(versions.for_rig(0, "rig", types.SimpleNamespace()))


if __name__ == "__main__":
    unittest.main()

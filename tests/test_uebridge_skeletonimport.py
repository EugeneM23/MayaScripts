"""The Skeleton mode's skeleton (2026-10-01): the Characters card's, with its
geometry, the clip transferred onto it by bone name.

The pure halves - which skeleton, which bone takes which, twin or not, how
each bone is driven, the wording - and the press's order with every scene
call faked. The scene half is verify_uebridge_many.py's.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
(addendum 3)
"""
import collections
import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import catalog  # noqa: E402
from maya_uebridge import skeletonimport as si  # noqa: E402


class WhichSkeleton(unittest.TestCase):
    """«используем скелет который активен в вкладке character»; a rig there
    means that model's skeleton; a model without one, Manny's."""

    def test_an_active_skeleton_row_is_itself(self):
        creep = catalog.character_for("Creep", "skeleton")
        self.assertIs(si.skeleton_entry_for(creep), creep)

    def test_a_rig_means_its_models_skeleton(self):
        self.assertEqual(si.skeleton_entry_for(catalog.character_for("Creep", "rig")).key, "Creep")
        self.assertEqual(si.skeleton_entry_for(catalog.character_for("Manny", "rig")).key, "Manny")

    def test_a_model_with_no_skeleton_means_manny(self):
        self.assertEqual(si.skeleton_entry_for(catalog.character_for("Orc_D", "rig")).key, "Manny")

    def test_nothing_chosen_asks_the_remembered_model(self):
        self.assertEqual(si.skeleton_entry_for(None, "Creep").key, "Creep")
        self.assertEqual(si.skeleton_entry_for(None, "Orc_D").key, "Manny")
        self.assertEqual(si.skeleton_entry_for(None, None).key, "Manny")


class PairBones(unittest.TestCase):

    def test_by_leaf_name(self):
        self.assertEqual(si.leaf("|A_Jump:skeldarDropShift|A_Jump:root|A_Jump:pelvis"), "pelvis")
        self.assertEqual(si.pair_bones(["pelvis", "hand_r", "weapon_r"], ["pelvis", "hand_r", "head"]),
                         {"pelvis": "pelvis", "hand_r": "hand_r"})

    def test_a_ue4_target_under_a_ue5_clip_maps_the_spine(self):
        """maya_retarget's map: the same bone, a different count."""
        ue5 = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05"]
        ue4 = ["pelvis", "spine_01", "spine_02", "spine_03"]
        self.assertEqual(si.pair_bones(ue5, ue4), {"pelvis": "pelvis", "spine_01": "spine_02",
                                                   "spine_02": "spine_04", "spine_03": "spine_05"})

    def test_a_ue5_target_keeps_its_names(self):
        ue5 = ["spine_01", "spine_02", "spine_03", "spine_04", "spine_05"]
        self.assertEqual(si.pair_bones(ue5, ue5), dict((n, n) for n in ue5))


class Twin(unittest.TestCase):
    """Measured on six UE clips: the median relative bone-length difference
    is 0.0000 against Manny UE5 [skeleton] on every one, 0.2424 against the
    Creep, 0.2403 against the UE4 Mannequin. The share within 1 % was not
    enough: a 3P clip animates bone translations and scale, and the thrust
    read 0.90 against Manny - on the line."""

    def test_a_twin(self):
        lengths = [(10.0, 10.0)] * 82 + [(10.27, 6.9)]          # Manny: weapon_r moved
        self.assertTrue(si.is_twin(lengths))

    def test_a_3p_clip_that_stretches_some_bones_is_still_a_twin(self):
        self.assertTrue(si.is_twin([(10.0, 10.0)] * 73 + [(10.5, 10.0)] * 8))

    def test_another_body(self):
        self.assertFalse(si.is_twin([(10.0, 10.0)] * 29 + [(10.0, 14.0)] * 54))

    def test_short_bones_do_not_vote(self):
        self.assertTrue(si.is_twin([(0.2, 0.9)] * 50 + [(30.0, 30.1)] * 10))
        self.assertFalse(si.is_twin([(0.2, 0.2)] * 5))


class Drive(unittest.TestCase):

    def test_a_twin_takes_every_bone_whole(self):
        for name in ("pelvis", "hand_r", "ik_hand_gun"):
            self.assertEqual(si.drive_for(name, False, True), "parent")
        self.assertEqual(si.drive_for("Manny_Skeleton_root", True, True), "parent")

    def test_another_body_turns_its_bones_and_moves_root_and_pelvis(self):
        self.assertEqual(si.drive_for("hand_r", False, False), "orient")
        self.assertEqual(si.drive_for("pelvis", False, False), "orient+point")
        self.assertEqual(si.drive_for("root", True, False), "orient+point")

    def test_another_body_leaves_its_ik_helpers_at_rest(self):
        self.assertIsNone(si.drive_for("ik_hand_gun", False, False))
        self.assertIsNone(si.drive_for("ik_foot_l", False, False))


class Words(unittest.TestCase):

    def test_the_line(self):
        result = dict(twin=True, moved=89, skipped=[], missing=["head", "neck_01", "neck_02"])
        self.assertEqual(si.result_line("A_Jump", "Manny UE5 [skeleton]", "root1", result,
                                        {"start": 0.0, "end": 61.0}),
                         "A_Jump onto Manny UE5 [skeleton] root1: 89 bones exact, frames 0-61  |  "
                         "not in the clip: head, neck_01, neck_02")

    def test_by_rotation_and_the_helpers(self):
        result = dict(twin=False, moved=80, skipped=["ik_foot_l", "ik_hand_gun"], missing=[])
        self.assertEqual(si.result_line("A", "Creep [skeleton]", "Armature", result, {}),
                         "A onto Creep [skeleton] Armature: 80 bones by rotation (its own "
                         "proportions)  |  at rest: ik_foot_l, ik_hand_gun")


Rec = collections.namedtuple("Rec", "name package")


class Onto(unittest.TestCase):
    """The order: the skeleton added, the clip moved onto the point, the
    transfer, the clip's skeleton deleted."""

    def setUp(self):
        self.calls = []
        saved = dict(cmds=si.cmds, root_at=si.rigimport.root_at, wrap=si.rigimport._wrap,
                     new=si.new_skeleton, transfer=si.transfer)

        def restore():
            si.cmds = saved["cmds"]
            si.rigimport.root_at = saved["root_at"]
            si.rigimport._wrap = saved["wrap"]
            si.new_skeleton = saved["new"]
            si.transfer = saved["transfer"]
        self.addCleanup(restore)
        si.new_skeleton = lambda entry: (self.calls.append(("add", entry.key)) or
                                         ("|root1", "Manny UE5 [skeleton] added"))
        si.rigimport.root_at = lambda source, frame=None: (4.0, 90.0, -12.0)
        si.rigimport._wrap = lambda source, ns: (
            self.calls.append(("wrap", source)) or ("%s:skeldarDropShift" % ns,
                                                    "|%s:skeldarDropShift|%s:root" % (ns, ns)))
        si.transfer = lambda source, root, start, end: (
            self.calls.append(("transfer", source, root, start, end)) or
            dict(twin=True, moved=89, skipped=[], missing=[]))
        si.cmds = types.SimpleNamespace(
            ls=lambda node, uuid=False, long=False: ["UUID"] if uuid else ["|root1"],
            move=lambda x, y, z, node, relative=False, worldSpace=False: self.calls.append(
                ("move", (x, y, z), node)),
            namespace=lambda **k: self.calls.append(("delete_ns", k.get("removeNamespace"))))
        self.entry = catalog.character_for("Manny", "skeleton")

    def test_onto_the_point(self):
        line, failure, top = si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0},
                                              "|A:root", "A", (100.0, 0.0, -50.0))
        self.assertEqual((failure, top), ("", "root1"))
        self.assertEqual([c[0] for c in self.calls], ["add", "wrap", "move", "transfer",
                                                      "delete_ns"])
        self.assertEqual([c for c in self.calls if c[0] == "move"],
                         [("move", (96.0, 0.0, -38.0), "A:skeldarDropShift")])
        self.assertEqual([c for c in self.calls if c[0] == "transfer"],
                         [("transfer", "|A:skeldarDropShift|A:root", "|root1", 0.0, 30.0)])
        self.assertIn("A onto Manny UE5 [skeleton] root1: 89 bones exact", line)
        self.assertIn("standing at floor (100, -50)", line)

    def test_where_the_clip_is(self):
        line, failure, _top = si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0},
                                               "|A:root", "A", None)
        self.assertEqual([c[0] for c in self.calls], ["add", "transfer", "delete_ns"])
        self.assertNotIn("standing", line)

    def test_no_bone_in_common_is_a_failure_and_keeps_the_clip(self):
        si.transfer = lambda *a: dict(twin=False, moved=0, skipped=[], missing=["pelvis"])
        line, failure, _top = si.onto_skeleton(self.entry, "A", {"start": 0.0, "end": 30.0},
                                               "|A:root", "A", None)
        self.assertIn("no bone of A matches Manny UE5 [skeleton]", failure)
        self.assertNotIn("delete_ns", [c[0] for c in self.calls])


class ChooseSkeleton(unittest.TestCase):
    """2026-10-01, the merge: Skeleton x Onto selected - which skeleton."""

    BARE = ["|root", "|Armature|root"]
    LABELS = {"|root": "Manny UE5 [skeleton] (root)",
              "|Armature|root": "Creep [skeleton] (root)"}

    def choose(self, named, rigs=(), bare=None):
        return si.choose_skeleton(
            named, list(rigs), self.BARE if bare is None else bare, self.LABELS)

    def test_the_one_the_selection_names(self):
        self.assertEqual(self.choose(["|Armature|root", "|Armature|root"]),
                         ("|Armature|root", ""))

    def test_two_named_is_no_answer(self):
        root, refusal = self.choose(["|root", "|Armature|root"])
        self.assertIsNone(root)
        self.assertEqual(refusal, "2 skeletons selected (Manny UE5 [skeleton] (root), "
                                  "Creep [skeleton] (root)) - select one")

    def test_a_rig_named_says_pick_rig(self):
        root, refusal = self.choose([], ["Manny_Rig"])
        self.assertIsNone(root)
        self.assertEqual(refusal, "Manny_Rig is a rig - pick Rig in Animation Setup, or "
                                  "select a skeleton")

    def test_a_skeleton_named_beside_a_rig_wins(self):
        self.assertEqual(self.choose(["|root"], ["Manny_Rig"]), ("|root", ""))

    def test_nothing_named_the_only_one(self):
        self.assertEqual(self.choose([], bare=["|root"]), ("|root", ""))

    def test_nothing_named_none_standing_adds_one(self):
        self.assertEqual(self.choose([], bare=[]), (None, ""))

    def test_nothing_named_several_standing_names_them(self):
        root, refusal = self.choose([])
        self.assertIsNone(root)
        self.assertIn("2 skeletons in the scene (Manny UE5 [skeleton] (root), "
                      "Creep [skeleton] (root))", refusal)

    def test_the_first_only_note(self):
        self.assertEqual(si.first_only(["A"]), "")
        self.assertEqual(si.first_only(["A", "B", "C"]),
                         "only A: a skeleton takes one animation (2 more picked)")


class Facing(unittest.TestCase):
    """The yaw a skeleton's root faces: its -Y under the -90 X turn."""

    @staticmethod
    def matrix(yaw, ue_root):
        import math
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        if ue_root:      # Rx(-90) then Ry(yaw), row vectors
            x, y, z = (c, 0.0, -s), (-s, 0.0, -c), (0.0, 1.0, 0.0)
        else:            # Ry(yaw)
            x, y, z = (c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c)
        return list(x) + [0.0] + list(y) + [0.0] + list(z) + [0.0, 1.0, 2.0, 3.0, 1.0]

    def test_a_ue_root_and_main_read_alike(self):
        from maya_uebridge import rigimport
        for yaw in (0.0, 30.0, 90.0, -120.0, 179.0):
            self.assertAlmostEqual(rigimport.facing(self.matrix(yaw, True)), yaw, 6)
            self.assertAlmostEqual(rigimport.facing(self.matrix(yaw, False)), yaw, 6)
            self.assertAlmostEqual(rigimport.heading(self.matrix(yaw, False)), yaw, 6)

    def test_place_moves_turns_by_the_facing_it_is_given(self):
        from maya_uebridge import rigimport
        pivot, turn, move = rigimport.place_moves(
            (100.0, 0.0, -50.0), 90.0, self.matrix(30.0, True), rigimport.facing)
        self.assertEqual(pivot, (1.0, 2.0, 3.0))
        self.assertAlmostEqual(turn, 60.0, 6)
        self.assertEqual(move, (99.0, 0.0, -53.0))


if __name__ == "__main__":
    unittest.main()

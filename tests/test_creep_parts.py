"""The second Creep's parts (2026-10-27): the right arm and the head as rigs and skeletons of their own.

The pure halves: the catalog rows, the part anchor in the AS retarget's tables, the decision for a
part (never squashed), the Auto card leaving parts out.  The scene halves are
docs/superpowers/plans/verify_creep_parts.py.
"""
import os
import types
import unittest

import maya_asretarget as ar
import maya_retargetmode as rm
import maya_rig_retarget as rr
from maya_scenesetup import catalog


class Rows(unittest.TestCase):

    def test_four_rows_two_models_each_a_part_on_the_chest(self):
        for model in ("Creep2_ArmR", "Creep2_Head"):
            rig, skel = catalog.character_for(model, "rig"), catalog.character_for(model, "skeleton")
            self.assertTrue(rig and skel, model)
            for row in (rig, skel):
                self.assertEqual(row.part, "spine_05")
                self.assertFalse(row.textured)
                self.assertTrue(os.path.isfile(catalog.character_file(row)), row.file)
            self.assertTrue(os.path.isfile(catalog.portrait_path(model)))

    def test_a_whole_character_is_no_part(self):
        for row in catalog.CHARACTERS:
            if not row.model.startswith("Creep2_"):
                self.assertEqual(row.part, "", row.key)

    def test_the_parts_follow_the_second_creep_in_the_grid(self):
        keys = [m.key for m in catalog.MODELS]
        self.assertEqual(keys.index("Creep2_ArmR"), keys.index("Creep2_Body") + 1)
        self.assertEqual(keys.index("Creep2_Head"), keys.index("Creep2_Body") + 2)

    def test_the_rig_assets_are_part_rigs_built_manny_s_way(self):
        for key in ("Creep2_ArmR_Rig", "Creep2_Head_Rig"):
            with open(catalog.character_file(catalog.character_by_key(key)), encoding="utf-8",
                      errors="replace") as fh:
                text = fh.read()
            self.assertIn('".skeldarPartAnchor" -type "string" "spine_05"', text, key)
            self.assertIn("createNode transform -n \"PartAnchor\"", text, key)
            self.assertIn("createNode pointConstraint", text, key)       # point + orient + scale
            self.assertNotIn('"skeldarRetarget"', text, key)             # not rotation-only
            self.assertNotIn("createNode script", text, key)

    def test_every_part_asset_carries_manny_s_whole_skeleton(self):
        """2026-10-27, «скелеты должны быть от менни»: 93 joints, each under Manny's parent."""
        import re
        def joints(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                found = dict(re.findall(r'createNode joint -n "([^"]+)" -p "([^"]+)"', fh.read()))
            found.pop("root", None)                     # under Armature in the parts, at world in Manny's
            return found
        manny = joints(catalog.character_file(catalog.character_by_key("Manny")))
        for key in ("Creep2_ArmR_Rig", "Creep2_Head_Rig", "Creep2_ArmR", "Creep2_Head"):
            part = joints(catalog.character_file(catalog.character_by_key(key)))
            self.assertEqual(len(manny), 92, "Manny's 93 bones less the root")
            for name, parent in manny.items():                # AS's own joints beside them
                self.assertEqual(part[name], parent, (key, name))

    def test_the_arm_rig_has_no_left_arm(self):
        with open(catalog.character_file(catalog.character_by_key("Creep2_ArmR_Rig")), encoding="utf-8",
                  errors="replace") as fh:
            text = fh.read()
        self.assertNotIn('-n "Shoulder_L"', text)
        self.assertIn('-n "Shoulder_R"', text)


class Anchor(unittest.TestCase):

    def test_root_x_stands_for_the_anchor_bone(self):
        self.assertEqual(ar.our_bone_map()["RootX_M"], "pelvis")
        self.assertEqual(ar.our_bone_map("spine_05")["RootX_M"], "spine_05")

    def test_the_source_name_of_the_chest(self):
        self.assertEqual(ar.source_name("spine_05", ar.UE5), "spine_05")
        self.assertEqual(ar.source_name("spine_05", ar.MIXAMO), "Spine2")
        self.assertIsNone(ar.source_name("nothing", ar.UE5))

    def test_root_x_follows_the_given_bone(self):
        drives, _ = ar.drive_plan(["Main", "RootX_M", "FKScapula_R"], ["root", "spine_05", "clavicle_r"],
                                  pelvis="spine_05")
        root_x = [d for d in drives if d.control == "RootX_M"]
        self.assertEqual([d.bone for d in root_x], ["spine_05"])
        self.assertIn("clavicle_r", [d.bone for d in drives if d.control == "FKScapula_R"])

    def test_without_an_anchor_root_x_follows_the_pelvis(self):
        drives, _ = ar.drive_plan(["RootX_M"], ["pelvis"])
        self.assertEqual([d.bone for d in drives], ["pelvis"])

    def test_pairs_name_the_anchor(self):
        drives = [ar.Drive("RootX_M", "spine_05", True, True), ar.Drive("Main", "root", True, True)]
        rig_bones = {"spine_05": "|Group|PartAnchor", "root": "|Armature|root"}
        self.assertEqual(ar.pairs_of(drives, rig_bones, "spine_05"), {"spine_05": "spine_05", "root": "root"})

    def test_part_anchor_none_without_a_rig(self):
        self.assertEqual(ar.part_anchor(None), (None, None))


class PartModule(object):
    """A module that measures and knows part anchors."""

    def __init__(self, twin, anchor):
        self._twin, self._anchor = twin, anchor

    def measure(self, source_root=None, rig=None):
        return rm.Measure(twin=self._twin), ""

    def part_anchor(self, rig):
        return (self._anchor, "|Group|PartAnchor") if self._anchor else (None, None)


class Decide(unittest.TestCase):

    def setUp(self):
        self._label = rr.maya_rigs.label
        rr.maya_rigs.label = lambda rig: "Creep2_ArmR_Rig"

    def tearDown(self):
        rr.maya_rigs.label = self._label

    def test_a_part_and_its_own_clip_go_whole(self):
        d = rr.decide_for(PartModule(True, "spine_05"), types.SimpleNamespace())
        self.assertEqual((d.mode, d.ask, d.twin), (rm.STRETCH, False, True))

    def test_a_part_and_any_other_clip_go_by_rotation_never_asked(self):
        d = rr.decide_for(PartModule(False, "spine_05"), types.SimpleNamespace())
        self.assertEqual((d.mode, d.ask), (rm.ROTATION, False))
        self.assertIn("part", d.reason)


class Auto(unittest.TestCase):

    def test_the_auto_card_never_matches_a_part(self):
        from maya_uebridge import autoimport
        with open(autoimport.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('if not getattr(entry, "part", "")', src)


class FitsTheGrid(unittest.TestCase):

    def test_every_model_with_a_row_has_a_fire(self):
        import maya_charfire
        for model in ("Creep2_ArmR", "Creep2_Head"):
            self.assertIn(model, maya_charfire.FIRES)


if __name__ == "__main__":
    unittest.main()

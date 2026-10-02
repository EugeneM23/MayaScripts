"""The pure halves of wiring maya_skeletonmap into the retargets (2026-10-02)."""

import os
import sys
import unittest

import maya_skeletonmap as sm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skeleton_conventions as fixtures  # noqa: E402

try:                                   # the real maya when this runs inside mayapy
    import maya.cmds  # noqa: F401
    HAVE_MAYA = True
except ImportError:
    HAVE_MAYA = False


def result_of(convention, **kwargs):
    rows, _expected = fixtures.build(convention)
    paths = fixtures.paths(rows)
    positions = dict((paths[n], pos) for n, _p, pos in rows)
    return sm.recognize(list(paths.values()), positions, **kwargs)


class TestDirectionChildren(unittest.TestCase):

    def test_hand_points_at_the_middle_finger_not_the_thumb(self):
        result = result_of("ue5")
        parents = sm.canonical_parents(result.mapping, sm.parent_map(list(result.mapping.values())))
        children = sm.direction_children(parents)
        self.assertEqual(children["hand_l"], "middle_metacarpal_l")
        self.assertEqual(children["pelvis"], "spine_01")
        self.assertEqual(children["spine_05"], "neck_01")
        self.assertEqual(children["upperarm_r"], "lowerarm_r")

    def test_without_metacarpals_the_middle_finger(self):
        parents = {"hand_l": None, "thumb_01_l": "hand_l", "middle_01_l": "hand_l",
                   "index_01_l": "hand_l"}
        self.assertEqual(sm.direction_children(parents)["hand_l"], "middle_01_l")


@unittest.skipUnless(HAVE_MAYA, "needs maya.api for the uebridge module's imports")
class TestSkeletonImportPairs(unittest.TestCase):

    def setUp(self):
        from maya_uebridge import skeletonimport
        self.si = skeletonimport

    def test_a_biped_pairs_onto_manny_chain_onto_chain(self):
        source, target = result_of("biped"), result_of("ue5")
        pairs = self.si.foreign_pairs(source, target)
        by_leaf = dict((sm.leaf(t), sm.leaf(s)) for t, s in pairs.items())
        self.assertEqual(by_leaf["upperarm_l"], "Bip001_L_UpperArm")
        self.assertEqual(by_leaf["spine_01"], "Bip001_Spine")
        self.assertEqual(by_leaf["spine_05"], "Bip001_Spine2")
        self.assertEqual(by_leaf["neck_01"], "Bip001_Neck")
        self.assertNotIn("neck_02", by_leaf)
        self.assertNotIn("root", by_leaf)

    def test_a_five_spine_source_onto_the_ue4_mannequin_takes_the_ends(self):
        source, target = result_of("daz"), result_of("ue4")
        by_leaf = dict((sm.leaf(t), sm.leaf(s)) for t, s in
                       self.si.foreign_pairs(source, target).items())
        self.assertEqual(by_leaf["spine_01"], "abdomenLower")
        self.assertEqual(by_leaf["spine_03"], "chestUpper")

    def test_ue_covered(self):
        self.assertTrue(self.si.ue_covered(dict((n, n) for n in self.si.UE_CORE)))
        self.assertFalse(self.si.ue_covered({"pelvis": "Hips"}))

    def test_ground_axis(self):
        self.assertEqual(self.si.ground_axis(None), "y")
        # a -90 X Null: its local Z is world up (the Creep's Armature)
        null = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]
        self.assertEqual(self.si.ground_axis(null), "z")


@unittest.skipUnless(HAVE_MAYA, "needs maya.api")
class TestRetargetModules(unittest.TestCase):

    def test_scaled_matrix(self):
        import maya_asretarget as ar
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1.0, 0.95, 0.0, 1]
        out = ar.scaled_matrix(m, 100.0, (1.0, 0.0, 0.0))
        self.assertEqual(out[12:15], [1.0, 95.0, 0.0])
        self.assertEqual(out[:12], m[:12])

    def test_mixamo_stays_mixamo_cmu_does_not(self):
        import maya_asretarget as ar
        mixamo = list(fixtures.paths(fixtures.build("mixamo")[0]).values())
        cmu = list(fixtures.paths(fixtures.build("cmu")[0]).values())
        unity = list(fixtures.paths(fixtures.build("unity")[0]).values())
        self.assertTrue(ar.mixamo_like(mixamo))
        self.assertFalse(ar.mixamo_like(cmu))
        self.assertFalse(ar.mixamo_like(unity))
        names = [sm.leaf(p) for p in cmu]
        schema, _score = ar.detect_schema(names)
        self.assertIs(schema, ar.MIXAMO)        # CMU scores as Mixamo by its names ...
        self.assertFalse(ar.mixamo_like(cmu))   # ... and is taken out of it

    def test_ue5_and_mixamo_detection_unchanged(self):
        import maya_asretarget as ar
        for convention, schema in (("ue5", ar.UE5), ("mixamo", ar.MIXAMO)):
            names = [sm.leaf(p) for p in fixtures.paths(fixtures.build(convention)[0]).values()]
            self.assertIs(ar.detect_schema(names)[0], schema)

    def test_playermale_ue_names(self):
        import maya_pmretarget as pm
        names = pm.ue_names_of_ours()
        self.assertEqual(names["Left_Arm"], "upperarm_l")
        self.assertEqual(names["Right_Knee"], "calf_r")
        self.assertEqual(names["Spine4"], "spine_05")
        self.assertEqual(names["Hip"], "pelvis")

    def test_generic_detection_is_not_offered_to_the_rig_dispatcher(self):
        import maya_pmretarget as pm
        import maya_rig_retarget as rr
        biped = [sm.leaf(p) for p in fixtures.paths(fixtures.build("biped")[0]).values()]
        self.assertIsNone(pm.detect_schema(biped))
        self.assertIsNone(rr.pick(biped)[0])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAVE_MAYA, "needs maya.api for the uebridge module's imports")
class TestTravelScaleRoad(unittest.TestCase):
    """The fix pass, 2026-10-02: which clips the square must read at another size."""

    def setUp(self):
        from maya_uebridge import skeletonimport
        self.si = skeletonimport

    def leaves(self, convention):
        rows, _e = fixtures.build(convention)
        return [sm.leaf(n) for n, _p, _pos in rows]

    def test_a_ue_clip_is_never_scaled(self):
        for target in ("new_rig", "skeleton"):
            self.assertFalse(self.si.scales_travel(self.leaves("ue5"), "ue5", target))
            self.assertFalse(self.si.scales_travel(self.leaves("ue4"), "ue4", target))

    def test_mixamo_onto_a_rig_takes_the_rigs_own_mixamo_road(self):
        self.assertFalse(self.si.scales_travel(self.leaves("mixamo"), "mixamo", "new_rig"))
        self.assertTrue(self.si.scales_travel(self.leaves("mixamo"), "mixamo", "skeleton"))

    def test_any_other_convention_is(self):
        for convention in ("cmu", "biped", "vrm", "rigify"):
            self.assertTrue(self.si.scales_travel(self.leaves(convention), convention, "new_rig"))

    def test_the_reference_is_mannys_bind(self):
        ref = self.si.reference_positions()
        self.assertAlmostEqual(sm.standing_height(ref), 87.5537, places=3)
        self.assertAlmostEqual(sm.leg_length(ref), 85.5625, places=3)

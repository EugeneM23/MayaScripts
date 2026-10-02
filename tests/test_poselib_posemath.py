"""posemath: pairing, rest alignment, the parent-relative transfer, mirror, blend - on synthetic
skeletons built here (no Maya scene).

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""
import math
import os
import subprocess
import sys
import unittest

import maya.api.OpenMaya as om

from maya_poselib import posemath as pm


def trs(t=(0, 0, 0), r=(0, 0, 0)):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*[math.radians(v) for v in r]))
    tm.setTranslation(om.MVector(*t), om.MSpace.kTransform)
    return tm.asMatrix()


CHAIN = [("root", None, (0, 0, 0)), ("pelvis", "root", (0, 95, 0)),
         ("spine_01", "pelvis", (0, 10, 0)), ("upperarm_l", "spine_01", (15, 30, 0)),
         ("lowerarm_l", "upperarm_l", (28, 0, 0)), ("hand_l", "lowerarm_l", (26, 0, 0)),
         ("middle_01_l", "hand_l", (8, 0, 0)), ("upperarm_r", "spine_01", (-15, 30, 0)),
         ("lowerarm_r", "upperarm_r", (-28, 0, 0)), ("hand_r", "lowerarm_r", (-26, 0, 0)),
         ("middle_01_r", "hand_r", (-8, 0, 0)), ("thigh_l", "pelvis", (10, -5, 0)),
         ("calf_l", "thigh_l", (0, -45, 0)), ("foot_l", "calf_l", (0, -42, 0)),
         ("thigh_r", "pelvis", (-10, -5, 0)), ("calf_r", "thigh_r", (0, -45, 0)),
         ("foot_r", "calf_r", (0, -42, 0)), ("head", "spine_01", (0, 50, 0))]


def skeleton(locals_=None, scale=1.0, rest_locals=None, place=om.MMatrix()):
    """{leaf: bone} with world matrices from local (translate, rotate) per bone."""
    locals_ = locals_ or {}
    worlds, rests, out = {}, {}, {}
    for name, parent, t in CHAIN:
        t = tuple(v * scale for v in t)
        rest_local = trs(t, (rest_locals or {}).get(name, (0, 0, 0)))
        local = trs(t, locals_.get(name, (rest_locals or {}).get(name, (0, 0, 0))))
        rests[name] = rest_local * (rests[parent] if parent else om.MMatrix())
        worlds[name] = local * (worlds[parent] if parent else place)
        out[name] = {"parent": parent, "canonical": name, "rest": pm.flat(rests[name]),
                     "world": pm.flat(worlds[name])}
    return out


class Pairing(unittest.TestCase):

    def test_ue_by_leaf_and_roots(self):
        s, t = skeleton(), skeleton()
        pairs = pm.pairs(s, t)
        self.assertEqual(pairs["hand_l"], "hand_l")
        self.assertEqual(pairs["root"], "root")

    def test_canonical_road(self):
        s = skeleton()
        renamed = {}
        for leaf, bone in s.items():
            new = "mx_" + leaf
            renamed[new] = dict(bone, parent=("mx_" + bone["parent"]) if bone["parent"] else None)
        pairs = pm.pairs(renamed, skeleton())
        self.assertEqual(pairs["hand_l"], "mx_hand_l")
        self.assertEqual(pairs["root"], "mx_root")


class Opposite(unittest.TestCase):

    def test_spellings(self):
        for a, b in (("hand_l", "hand_r"), ("LeftHand", "RightHand"), ("Left_Arm", "Right_Arm"),
                     ("hand.L", "hand.R"), ("Bip001 L Hand", "Bip001 R Hand"),
                     ("upperarm_L_", "upperarm_R_")):
            self.assertEqual(pm.opposite(a), b)
            self.assertEqual(pm.opposite(b), a)
        self.assertIsNone(pm.opposite("spine_01"))


class Transfer(unittest.TestCase):

    def test_twin_full_pose_is_exact(self):
        pose = {"upperarm_l": (0, 30, 40), "lowerarm_l": (0, 0, 50), "hand_l": (10, 20, 30),
                "spine_01": (5, 0, 10)}
        s = skeleton(pose)
        t = skeleton()
        out = pm.targets(s, t, pm.pairs(s, t), [b for b in s if b != "root"])
        for leaf in ("upperarm_l", "lowerarm_l", "hand_l", "spine_01"):
            self.assertLess(pm.angle(out[leaf], pm.matrix(s[leaf]["world"])), 1e-6, leaf)

    def test_the_root_stays_and_the_pose_is_relative(self):
        pose = {"pelvis": (0, 0, 20), "upperarm_l": (0, 30, 40)}
        s = skeleton(pose)
        turned = trs((300, 0, -50), (0, 90, 0))
        t = skeleton(place=turned)
        out = pm.targets(s, t, pm.pairs(s, t), ["pelvis", "upperarm_l"])
        self.assertLess(pm.angle(out["root"], turned), 1e-9)
        want = pm.matrix(s["upperarm_l"]["world"]) * turned
        self.assertLess(pm.angle(out["upperarm_l"], want), 1e-6)

    def test_a_hand_pose_lands_on_the_arm_as_it_stands(self):
        s = skeleton({"hand_l": (0, 0, 45), "upperarm_l": (0, 0, 80)})
        t = skeleton({"upperarm_l": (0, 60, 0)})
        out = pm.targets(s, t, pm.pairs(s, t), ["hand_l"])
        self.assertLess(pm.angle(out["upperarm_l"], pm.matrix(t["upperarm_l"]["world"])), 1e-9)
        local_s = pm.rotation(pm.matrix(s["hand_l"]["world"])) * \
            pm.rotation(pm.matrix(s["lowerarm_l"]["world"])).inverse()
        local_t = pm.rotation(out["hand_l"]) * pm.rotation(out["lowerarm_l"]).inverse()
        self.assertLess(pm.angle(local_s, local_t), 1e-6)

    def test_other_proportions_keep_lengths_and_scale_the_pelvis(self):
        s = skeleton({"pelvis": (0, 0, 0)}, scale=1.0)
        t = skeleton(scale=2.0)
        pairs = pm.pairs(s, t)
        scale = pm.scale_between(s, t, pairs)
        self.assertAlmostEqual(scale, 2.0, 6)
        out = pm.targets(s, t, pairs, ["pelvis", "upperarm_l"], scale=scale)
        self.assertAlmostEqual(pm.position(out["pelvis"]).y, 190.0, 6)
        arm = (pm.position(out["lowerarm_l"]) - pm.position(out["upperarm_l"])).length()
        self.assertAlmostEqual(arm, 56.0, 6)

    def test_rest_alignment_points_bones_like_the_source(self):
        # the source's arm rests 40 deg down (an A-pose), the target's level (a T-pose)
        s = skeleton({"upperarm_l": (0, 0, -40)}, rest_locals={"upperarm_l": (0, 0, -40)})
        t = skeleton()
        out = pm.targets(s, t, pm.pairs(s, t), ["upperarm_l"])
        s_dir = pm.position(pm.matrix(s["lowerarm_l"]["world"])) - \
            pm.position(pm.matrix(s["upperarm_l"]["world"]))
        t_dir = pm.position(out["lowerarm_l"]) - pm.position(out["upperarm_l"])
        self.assertLess(pm.direction_angle(s_dir, t_dir), 1e-5)


class Mirror(unittest.TestCase):

    def test_left_takes_the_right_mirrored(self):
        s = skeleton({"upperarm_r": (0, 30, -40)})
        m, members = pm.mirror(s, ["upperarm_r"])
        self.assertEqual(members, ["upperarm_l"])
        expect = skeleton({"upperarm_l": (0, -30, 40)})
        self.assertLess(pm.angle(pm.matrix(m["upperarm_l"]["world"]),
                                 pm.matrix(expect["upperarm_l"]["world"])), 1e-6)

    def test_twice_is_identity(self):
        s = skeleton({"upperarm_r": (10, 30, -40), "spine_01": (0, 20, 5)})
        once, mem = pm.mirror(s, ["upperarm_r", "spine_01"])
        twice, mem2 = pm.mirror(once, mem)
        self.assertEqual(sorted(mem2), ["spine_01", "upperarm_r"])
        for leaf in ("upperarm_r", "spine_01"):
            self.assertLess(pm.angle(pm.matrix(twice[leaf]["world"]),
                                     pm.matrix(s[leaf]["world"])), 1e-6)


class Blend(unittest.TestCase):

    def test_half(self):
        a, b = trs((0, 0, 0), (0, 0, 0)), trs((10, 0, 0), (0, 0, 90))
        half = pm.blend(a, b, 0.5)
        self.assertAlmostEqual(pm.position(half).x, 5.0, 9)
        self.assertAlmostEqual(pm.angle(half, a), 45.0, 6)


class Regions(unittest.TestCase):

    def test_names(self):
        # REGIONS order: Head, Spine, Pelvis, Arm L, Hand L, Arm R, Hand R, Leg L, Leg R
        self.assertEqual(pm.regions(["hand_l", "index_01_l", "upperarm_r", "head"]),
                         ["Head", "Hand L", "Arm R"])


# ---------------------------------------------------------------- beyond the brief's tests:
# the rest of the rules pinned (the UE4 spine map, the canonical spine chain, the drive, the
# pelvis mirror, the 2 % size rule) and a source with no root of its own (Mixamo's Hips)

UE_LIMBS = ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
            "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r")


def names_only(names, prefix=""):
    """A bones dict holding only what pairing reads: every bone under the root."""
    out = {prefix + "root": {"parent": None, "canonical": "root"}}
    for name in names:
        out[prefix + name] = {"parent": prefix + "root", "canonical": name}
    return out


def rootless(bones):
    """A copy with the root gone and its children at the top, every leaf `mx_`-prefixed (the
    canonical names kept): Mixamo's shape, whose Hips is its root."""
    out = {}
    for leaf, bone in bones.items():
        if leaf == "root":
            continue
        parent = bone["parent"]
        out["mx_" + leaf] = dict(bone, parent=None if parent in (None, "root") else "mx_" + parent)
    return out


class PairingRules(unittest.TestCase):

    def test_a_ue4_target_takes_the_spine_map(self):
        source = names_only(UE_LIMBS + ("spine_01", "spine_02", "spine_03", "spine_04",
                                        "spine_05", "neck_01"))
        target = names_only(UE_LIMBS + ("spine_01", "spine_02", "spine_03", "neck_01"))
        pairs = pm.pairs(source, target)
        self.assertEqual([pairs[n] for n in ("spine_01", "spine_02", "spine_03")],
                         ["spine_02", "spine_04", "spine_05"])
        self.assertEqual(pairs["neck_01"], "neck_01")

    def test_a_short_spine_is_distributed_chain_onto_chain(self):
        source = names_only(UE_LIMBS[:6] + ("spine_01", "spine_03", "spine_05"), prefix="mx_")
        target = names_only(UE_LIMBS + ("spine_01", "spine_02", "spine_03", "spine_04",
                                        "spine_05"))
        pairs = pm.pairs(source, target)
        self.assertEqual(pairs["spine_01"], "mx_spine_01")
        self.assertEqual(pairs["spine_03"], "mx_spine_03")
        self.assertEqual(pairs["spine_05"], "mx_spine_05")
        self.assertNotIn("spine_02", pairs)

    def test_helpers_pair_by_leaf_only(self):
        source = names_only(UE_LIMBS + ("ik_hand_gun",))
        target = names_only(UE_LIMBS + ("ik_hand_gun",))
        self.assertEqual(pm.pairs(source, target)["ik_hand_gun"], "ik_hand_gun")
        renamed = names_only(UE_LIMBS[:6] + ("ik_hand_gun",), prefix="mx_")
        self.assertNotIn("ik_hand_gun", pm.pairs(renamed, target))


class TransferRules(unittest.TestCase):

    def test_the_drive_is_used_only_when_asked(self):
        s = skeleton({"upperarm_l": (0, 30, 40)})
        drive = trs((15, 135, 0), (25, 30, 40))
        s["upperarm_l"]["drive"] = pm.flat(drive)
        t = skeleton()
        pairs = pm.pairs(s, t)
        driven = pm.targets(s, t, pairs, ["upperarm_l"], use_drive=True)
        shown = pm.targets(s, t, pairs, ["upperarm_l"])
        self.assertLess(pm.angle(driven["upperarm_l"], drive), 1e-6)
        self.assertLess(pm.angle(shown["upperarm_l"], pm.matrix(s["upperarm_l"]["world"])), 1e-6)

    def test_a_size_within_two_percent_is_one(self):
        s, t = skeleton(), skeleton(scale=1.015)
        self.assertEqual(pm.scale_between(s, t, pm.pairs(s, t)), 1.0)

    def test_a_source_with_no_root_has_its_frame_at_the_world_origin(self):
        s = rootless(skeleton({"pelvis": (0, 0, 20), "upperarm_l": (0, 30, 40)}))
        t = skeleton()
        pairs = pm.pairs(s, t)
        self.assertEqual(pairs["root"], "mx_pelvis")        # the roots are always paired
        self.assertEqual(pairs["pelvis"], "mx_pelvis")
        out = pm.targets(s, t, pairs, ["mx_pelvis", "mx_upperarm_l"])
        self.assertLess(pm.angle(out["pelvis"], pm.matrix(s["mx_pelvis"]["world"])), 1e-6)
        self.assertAlmostEqual(pm.position(out["pelvis"]).y, 95.0, 6)
        self.assertLess(pm.angle(out["upperarm_l"], pm.matrix(s["mx_upperarm_l"]["world"])), 1e-6)
        self.assertAlmostEqual(pm.scale_between(s, skeleton(scale=2.0), pairs), 2.0, 6)


class MirrorRules(unittest.TestCase):

    def test_the_pelvis_position_reflects(self):
        s = skeleton()
        s["pelvis"]["world"] = pm.flat(trs((7, 95, 3)))
        m, members = pm.mirror(s, ["pelvis"])
        self.assertEqual(members, ["pelvis"])
        self.assertAlmostEqual(pm.position(m["pelvis"]["world"]).x, -7.0, 9)
        self.assertAlmostEqual(pm.position(m["pelvis"]["world"]).z, 3.0, 9)
        self.assertLess(pm.angle(m["pelvis"]["world"], om.MMatrix()), 1e-9)

    def test_a_source_whose_root_is_its_pelvis_mirrors_in_the_world(self):
        s = rootless(skeleton())
        s["mx_pelvis"]["world"] = pm.flat(trs((7, 95, 3), (0, 30, 0)))
        m, members = pm.mirror(s, ["mx_pelvis"])
        self.assertEqual(members, ["mx_pelvis"])
        want = trs((-7, 95, 3), (0, -30, 0))
        self.assertLess(pm.angle(m["mx_pelvis"]["world"], want), 1e-9)
        self.assertLess((pm.position(m["mx_pelvis"]["world"]) - pm.position(want)).length(), 1e-9)

    def test_the_drive_mirrors_too(self):
        s = skeleton({"upperarm_r": (0, 30, -40)})
        s["upperarm_r"]["drive"] = s["upperarm_r"]["world"]
        s["upperarm_l"]["drive"] = s["upperarm_l"]["world"]
        m, _ = pm.mirror(s, ["upperarm_r"])
        self.assertLess(pm.angle(m["upperarm_l"]["drive"], m["upperarm_l"]["world"]), 1e-9)


class Names(unittest.TestCase):

    def test_more_spellings_and_centre_bones(self):
        for a, b in (("mixamorig:LeftHand", "mixamorig:RightHand"), ("lShldrBend", "rShldrBend"),
                     ("CC_Base_L_Upperarm", "CC_Base_R_Upperarm"), ("DEF-hand.L", "DEF-hand.R"),
                     ("Shoulder_L", "Shoulder_R"), ("LHipJoint", "RHipJoint")):
            self.assertEqual(pm.opposite(a), b)
        for centre in ("pelvis", "head", "root", "Hips", "Bip001 Spine", "L5", "neck_01",
                       "J_Bip_C_Hips", "RootX_M"):
            self.assertIsNone(pm.opposite(centre), centre)

    def test_regions_of_twists_fingers_and_helpers(self):
        self.assertEqual(pm.regions(["upperarm_twist_01_l", "ik_hand_gun", "root", "neck_01",
                                     "calf_twist_01_r", "spine_03", "pelvis", "thumb_01_r",
                                     "index_metacarpal_l"]),
                         ["Head", "Spine", "Pelvis", "Arm L", "Hand L", "Hand R", "Leg R"])

    def test_helpers_and_twists(self):
        self.assertTrue(all(pm.is_helper(n) for n in ("ik_hand_gun", "weapon_r", "camera_root",
                                                      "interaction", "center_of_mass")))
        self.assertFalse(pm.is_helper("hand_l"))
        self.assertTrue(pm.is_twist("upperarm_twist_01_l"))
        self.assertFalse(pm.is_twist("upperarm_l"))


class Purity(unittest.TestCase):

    def test_imports(self):
        plugin = os.path.dirname(os.path.dirname(os.path.abspath(pm.__file__)))
        code = ("import sys; sys.path.insert(0, %r); import maya_poselib.posemath; "
                "bad = [m for m in sys.modules if m.startswith(('maya.cmds', 'PySide'))]; "
                "sys.exit(1 if bad else 0)") % plugin
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)

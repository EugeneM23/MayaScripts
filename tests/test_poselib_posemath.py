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

    def test_a_source_with_no_root_poses_the_pelvis(self):
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


# a rootless source moved, and moved and turned, off the origin (a Mixamo native dropped on a
# point, a clip whose hips walk and turn) - its pelvis tilted to the side only, a pure swing,
# so its heading IS the place's turn and a rooted twin standing there is the same pose
PLACES = (trs((120, 0, -36)), trs((120, 0, -36), (0, 90, 0)), trs((-40, 0, 75), (0, -135, 0)))
TILTED = {"pelvis": (0, 0, 20), "spine_01": (5, 0, 10), "upperarm_l": (0, 30, 40),
          "upperarm_r": (10, 30, -40), "lowerarm_r": (0, 0, 35), "thigh_l": (-25, 0, 5)}


def forward(m):
    """A bone's +Z in world."""
    return om.MVector(0, 0, 1) * pm.rotation(m)


class Rootless(unittest.TestCase):

    def assertSameMatrix(self, a, b, what):
        self.assertLess(pm.angle(a, b), 1e-6, what)
        self.assertLess((pm.position(a) - pm.position(b)).length(), 1e-6, what)

    def test_moved_and_turned_it_transfers_as_its_rooted_twin(self):
        for place in PLACES:
            rooted = skeleton(TILTED, place=place)
            mixamo = rootless(rooted)
            for t in (skeleton(), skeleton(place=trs((300, 0, -50), (0, 90, 0)))):
                want = pm.targets(rooted, t, pm.pairs(rooted, t), list(TILTED))
                got = pm.targets(mixamo, t, pm.pairs(mixamo, t), ["mx_" + b for b in TILTED])
                for leaf in t:
                    self.assertSameMatrix(got[leaf], want[leaf], leaf)

    def test_the_hips_off_the_origin_stay_over_the_target_root(self):
        # the reviewer's measure: the hips at (120, 95, -36) once put the pelvis there, 125 cm
        # off a root at the origin, and a 90 deg turn turned it 90 deg off the root's facing
        for place in PLACES[:2]:
            s = rootless(skeleton(TILTED, place=place))
            t = skeleton()
            out = pm.targets(s, t, pm.pairs(s, t), ["mx_pelvis"])
            self.assertLess((pm.position(out["pelvis"]) - om.MVector(0, 95, 0)).length(), 1e-9)
            self.assertLess(pm.direction_angle(forward(out["pelvis"]), om.MVector(0, 0, 1)), 1e-6)

    def test_its_size_is_measured_on_its_rest_floor(self):
        for place in PLACES:
            s = rootless(skeleton(TILTED, place=place))
            big = skeleton(scale=2.0)
            self.assertAlmostEqual(pm.scale_between(s, big, pm.pairs(s, big)), 2.0, 9)

    def test_its_heading_is_the_yaw_of_the_turn(self):
        swing = om.MQuaternion(math.radians(40), om.MVector(1, 0, 1)).asMatrix()
        yaw = trs(r=(0, 70, 0))
        self.assertLess(pm.angle(pm._heading(swing * yaw), yaw), 1e-9)
        self.assertLess(pm.angle(pm._heading(trs(r=(0, -110, 0))), trs(r=(0, -110, 0))), 1e-9)
        self.assertLess(pm.angle(pm._heading(trs(r=(180, 0, 0))), om.MMatrix()), 1e-9)
        pose, rest = pm._ground(trs((1, 95, 2)), trs(r=(0, 0, 20)) * trs((7, 95, 3), (0, 30, 0)))
        self.assertLess((pm.position(pose) - om.MVector(7, pm.FLOOR, 3)).length(), 1e-9)
        self.assertLess((pm.position(rest) - om.MVector(1, pm.FLOOR, 2)).length(), 1e-9)
        self.assertLess(pm.angle(pose, trs(r=(0, 30, 0))), 1e-9)
        self.assertLess(pm.angle(rest, om.MMatrix()), 1e-9)


class MirrorRules(unittest.TestCase):

    def test_the_pelvis_position_reflects(self):
        s = skeleton()
        s["pelvis"]["world"] = pm.flat(trs((7, 95, 3)))
        m, members = pm.mirror(s, ["pelvis"])
        self.assertEqual(members, ["pelvis"])
        self.assertAlmostEqual(pm.position(m["pelvis"]["world"]).x, -7.0, 9)
        self.assertAlmostEqual(pm.position(m["pelvis"]["world"]).z, 3.0, 9)
        self.assertLess(pm.angle(m["pelvis"]["world"], om.MMatrix()), 1e-9)

    def test_a_source_whose_root_is_its_pelvis_mirrors_on_its_ground(self):
        # the hips stand at (7, 95, 3) facing 30 deg round, rolled 20 deg to the side: the mirror
        # keeps the place and the facing and rolls them the other way (in the world's frame they
        # came back at (-7, 95, 3) facing -30 deg: the body turned, not mirrored)
        s = rootless(skeleton())
        s["mx_pelvis"]["world"] = pm.flat(trs(r=(0, 0, 20)) * trs((7, 95, 3), (0, 30, 0)))
        m, members = pm.mirror(s, ["mx_pelvis"])
        self.assertEqual(members, ["mx_pelvis"])
        want = trs(r=(0, 0, -20)) * trs((7, 95, 3), (0, 30, 0))
        self.assertLess(pm.angle(m["mx_pelvis"]["world"], want), 1e-9)
        self.assertLess((pm.position(m["mx_pelvis"]["world"]) - pm.position(want)).length(), 1e-9)

    def test_a_rootless_source_moved_and_turned_mirrors_as_its_rooted_twin(self):
        for place in PLACES:
            rooted = skeleton(TILTED, place=place)
            mixamo = rootless(rooted)
            members = ["upperarm_r", "lowerarm_r", "pelvis", "spine_01", "thigh_l"]
            want, want_members = pm.mirror(rooted, members)
            got, got_members = pm.mirror(mixamo, ["mx_" + b for b in members])
            self.assertEqual(got_members, ["mx_" + b for b in want_members])
            for leaf in rooted:
                if leaf == "root":
                    continue
                a, b = pm.matrix(got["mx_" + leaf]["world"]), pm.matrix(want[leaf]["world"])
                self.assertLess(pm.angle(a, b), 1e-6, leaf)
                self.assertLess((pm.position(a) - pm.position(b)).length(), 1e-6, leaf)
            # the reviewer's measure: turned 90 deg the hips faced (1, 0, 0), and came back
            # facing (-1, 0, 0)
            hips = forward(got["mx_pelvis"]["world"])
            self.assertLess(pm.direction_angle(hips, forward(mixamo["mx_pelvis"]["world"])), 1e-6)

    def test_a_rootless_mirror_twice_is_identity(self):
        s = rootless(skeleton(TILTED, place=PLACES[2]))
        once, mem = pm.mirror(s, ["mx_upperarm_r", "mx_pelvis", "mx_thigh_l"])
        twice, mem2 = pm.mirror(once, mem)
        self.assertEqual(sorted(mem2), ["mx_pelvis", "mx_thigh_l", "mx_upperarm_r"])
        for leaf in s:
            a, b = pm.matrix(twice[leaf]["world"]), pm.matrix(s[leaf]["world"])
            self.assertLess(pm.angle(a, b), 1e-6, leaf)
            self.assertLess((pm.position(a) - pm.position(b)).length(), 1e-6, leaf)

    def test_the_drive_mirrors_too(self):
        s = skeleton({"upperarm_r": (0, 30, -40)})
        s["upperarm_r"]["drive"] = s["upperarm_r"]["world"]
        s["upperarm_l"]["drive"] = s["upperarm_l"]["world"]
        m, _ = pm.mirror(s, ["upperarm_r"])
        self.assertLess(pm.angle(m["upperarm_l"]["drive"], m["upperarm_l"]["world"]), 1e-9)


def standing(locals_=None, scale=1.0, off=None, rest_locals=None):
    """`skeleton`, with each bone in `off` ({leaf: (x, y, z)}) standing that far off its bind in
    its parent's frame - its world (and its subtree's) moved, its rest left where the bind put it.
    Manny's skeleton stands 0.07 cm off its own bind at the left calf (trap 171), and a rig's game
    bones, point-constrained to AdvancedSkeleton's, wander from pose to pose."""
    locals_, off = locals_ or {}, off or {}
    worlds, rests, out = {}, {}, {}
    for name, parent, t in CHAIN:
        t = tuple(v * scale for v in t)
        moved = tuple(a + b for a, b in zip(t, off.get(name, (0.0, 0.0, 0.0))))
        rest_turn = (rest_locals or {}).get(name, (0, 0, 0))
        rests[name] = trs(t, rest_turn) * (rests[parent] if parent else om.MMatrix())
        worlds[name] = trs(moved, locals_.get(name, rest_turn)) * \
            (worlds[parent] if parent else om.MMatrix())
        out[name] = {"parent": parent, "canonical": name, "rest": pm.flat(rests[name]),
                     "world": pm.flat(worlds[name])}
    return out


POSE = {"pelvis": (0, 10, 5), "spine_01": (5, 0, 10), "upperarm_l": (0, 30, 40),
        "lowerarm_l": (0, 0, 50), "hand_l": (10, 20, 30), "thigh_l": (-30, 0, 10),
        "calf_l": (40, 0, 0), "foot_l": (5, 10, 0)}


class Twins(unittest.TestCase):
    """The spec: a twin gives A = I, so a pose saved and applied on the same model is exact - a
    twin being the median paired length within 1 % (maya_retargetmode's rule) with every rest
    direction within `TWIN_DEG` (an A-posed and a T-posed copy of one skeleton are no twins)."""

    def assertExact(self, source, out, members):
        for leaf in members:
            self.assertLess(pm.angle(out[leaf], pm.matrix(source[leaf]["world"])), 1e-6, leaf)

    def test_what_is_a_twin(self):
        same = skeleton()
        self.assertTrue(pm.twin(pm.pairs(same, skeleton()), same, skeleton()))
        bigger = skeleton(scale=1.2)
        self.assertFalse(pm.twin(pm.pairs(same, bigger), same, bigger))
        a_pose = skeleton(rest_locals={"upperarm_l": (0, 0, -40)})
        self.assertFalse(pm.twin(pm.pairs(a_pose, same), a_pose, same))
        off = standing(off={"calf_l": (0.0, 0.0, 0.07)})
        self.assertTrue(pm.twin(pm.pairs(off, off), off, off))

    def test_a_twin_standing_off_its_bind_is_exact(self):
        # Manny's skeleton onto Manny's skeleton: the calf 0.07 cm off its bind on both read the
        # thigh's direction 0.089 deg off its rest one - an alignment a twin must not have
        s = standing(POSE, off={"calf_l": (0.0, 0.0, 0.07)})
        t = standing(off={"calf_l": (0.0, 0.0, 0.07)})
        members = [b for b in s if b != "root"]
        self.assertExact(s, pm.targets(s, t, pm.pairs(s, t), members), members)

    def test_a_twin_whose_bones_wander_from_pose_to_pose_is_exact(self):
        # Manny_Rig onto Manny_Rig: the game calf, point-constrained to AdvancedSkeleton's knee,
        # stands 0.06 cm one way in the card's pose and the other way in the target's
        s = standing(POSE, off={"calf_l": (0.0, 0.0, 0.06)})
        t = standing(off={"calf_l": (0.0, 0.0, -0.06)})
        members = [b for b in s if b != "root"]
        out = pm.targets(s, t, pm.pairs(s, t), members)
        self.assertExact(s, out, members)

    def test_an_a_posed_copy_is_still_aligned(self):
        s = skeleton({"upperarm_l": (0, 0, -40)}, rest_locals={"upperarm_l": (0, 0, -40)})
        t = skeleton()
        align = pm.alignments(pm.pairs(s, t), s, t)
        self.assertAlmostEqual(pm.angle(align["upperarm_l"], om.MMatrix()), 40.0, 6)


class AsItStands(unittest.TestCase):
    """Where a bone points is read from where its child STANDS, on both skeletons (trap 171): a
    source standing off its bind points where its child is, not where the bind put it."""

    def test_a_target_bone_points_where_the_source_bone_does(self):
        s = standing(POSE, off={"calf_l": (0.0, 0.0, 0.5)})      # 0.64 deg off its bind
        t = skeleton(scale=1.3)                                  # no twin: 30 % longer
        out = pm.targets(s, t, pm.pairs(s, t), ["pelvis", "thigh_l", "calf_l"])
        want = pm.position(pm.matrix(s["calf_l"]["world"])) - \
            pm.position(pm.matrix(s["thigh_l"]["world"]))
        got = pm.position(out["calf_l"]) - pm.position(out["thigh_l"])
        self.assertLess(pm.direction_angle(got, want), 1e-6)

    def test_a_chord_past_an_unpaired_bone_is_read_at_rest(self):
        # a UE4 spine under a UE5 one: the target's spine_01 points at its spine_02, partnered
        # by the source's spine_02 and spine_04 - spine_04 is no child of spine_02, so the chord
        # between them is the rest one (a posed spine_03 would swing the pelvis with it). Here the
        # thigh's partner child is the foot, past an unpaired calf bent 40 deg and standing 0.5
        # cm off its bind: the alignment is the unposed skeleton's
        s = standing(POSE, off={"calf_l": (0.0, 0.0, 0.5)})
        t = skeleton(scale=1.3)
        pairs = pm.pairs(s, t)
        pairs_skip = dict(pairs)
        del pairs_skip["calf_l"]                       # the thigh's direction child is now the foot
        align = pm.alignments(pairs_skip, s, t)
        rest = pm.alignments(pairs_skip, skeleton(), t)
        self.assertLess(pm.angle(align["thigh_l"], rest["thigh_l"]), 1e-9)


class TargetDrive(unittest.TestCase):
    """Onto a rig the four unrolled limb bones are in DRIVE form on both sides: a target bone
    that carries a `drive` stands in it, so what follows it follows the drive chain the rig
    holds it by - a hand under a posed forearm keeps its place on the forearm's drive, not on the
    unrolled bone (the forearm's roll lives in the twist joints, trap 126)."""

    def test_a_bone_follows_the_drive_of_a_posed_parent(self):
        s = skeleton({"lowerarm_l": (0, 0, 50)})
        s["lowerarm_l"]["drive"] = pm.flat(trs((0, 0, 0), (35, 0, 0)) *
                                           pm.matrix(s["lowerarm_l"]["world"]))
        t = skeleton({"hand_l": (0, 20, 10)})
        roll = trs((0, 0, 0), (-60, 0, 0)) * pm.matrix(t["lowerarm_l"]["world"])
        t["lowerarm_l"]["drive"] = pm.flat(roll)
        out = pm.targets(s, t, pm.pairs(s, t), ["lowerarm_l"], use_drive=True)
        self.assertLess(pm.angle(out["lowerarm_l"], pm.matrix(s["lowerarm_l"]["drive"])), 1e-6)
        want = pm.rotation(pm.matrix(t["hand_l"]["world"])) * pm.rotation(roll).inverse()
        got = pm.rotation(out["hand_l"]) * pm.rotation(out["lowerarm_l"]).inverse()
        self.assertLess(pm.angle(got, want), 1e-6)

    def test_without_use_drive_the_target_stands_in_its_world(self):
        s = skeleton({"lowerarm_l": (0, 0, 50)})
        t = skeleton({"hand_l": (0, 20, 10)})
        t["lowerarm_l"]["drive"] = pm.flat(trs((0, 0, 0), (-60, 0, 0)) *
                                           pm.matrix(t["lowerarm_l"]["world"]))
        out = pm.targets(s, t, pm.pairs(s, t), ["lowerarm_l"])
        want = pm.rotation(pm.matrix(t["hand_l"]["world"])) * \
            pm.rotation(pm.matrix(t["lowerarm_l"]["world"])).inverse()
        got = pm.rotation(out["hand_l"]) * pm.rotation(out["lowerarm_l"]).inverse()
        self.assertLess(pm.angle(got, want), 1e-6)


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

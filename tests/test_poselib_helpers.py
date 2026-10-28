"""maya_poselib.helpers (2026-10-20): the camera and the weapon bones on a card - which of them an
Apply writes, and how each is written (its own channels, or the weapon / camera driving it).

Spec: docs/superpowers/specs/2026-10-20-camera-and-weapon-bones-design.md
"""
import math
import unittest

import maya.api.OpenMaya as om

from maya_poselib import helpers
from maya_poselib import posemath as pm


def trs(t=(0, 0, 0), r=(0, 0, 0), order=0):
    tm = om.MTransformationMatrix()
    tm.setRotation(om.MEulerRotation(*([math.radians(v) for v in r] + [order])))
    tm.setTranslation(om.MVector(*t), om.MSpace.kTransform)
    return tm.asMatrix()


def close(test, a, b, tol=1e-9, what=""):
    worst = max(abs(x - y) for x, y in zip(list(a), list(b)))
    test.assertLessEqual(worst, tol, "%s: %g" % (what, worst))


BONES = dict((leaf, {"parent": parent}) for leaf, parent in (
    ("root", None), ("pelvis", "root"), ("spine_01", "pelvis"), ("hand_r", "spine_01"),
    ("hand_l", "spine_01"), ("weapon_r", "hand_r"), ("weapon_l", "hand_l"),
    ("camera_root", "root"), ("camera_bone", "camera_root"), ("ik_hand_gun", "root")))
WHOLE = ["pelvis", "spine_01", "hand_r", "hand_l"]


class Members(unittest.TestCase):

    def test_weapon_bones_go_with_their_hands(self):
        self.assertEqual(helpers.members_with(["hand_r"], BONES, WHOLE), ["hand_r", "weapon_r"])
        self.assertEqual(helpers.members_with(["hand_l", "spine_01"], BONES, WHOLE),
                         ["hand_l", "spine_01", "weapon_l"])

    def test_the_camera_only_with_the_whole_body(self):
        out = helpers.members_with(WHOLE, BONES, WHOLE)
        self.assertEqual(out, WHOLE + ["weapon_r", "weapon_l", "camera_root", "camera_bone"])
        self.assertNotIn("camera_root", helpers.members_with(WHOLE[:3], BONES, WHOLE))

    def test_only_bones_the_card_holds_and_never_twice(self):
        bones = dict((k, v) for k, v in BONES.items() if k not in ("weapon_r", "camera_bone"))
        out = helpers.members_with(WHOLE + ["weapon_l"], bones, WHOLE)
        self.assertEqual(out, WHOLE + ["weapon_l", "camera_root"])

    def test_ik_helpers_are_never_ours(self):
        self.assertFalse(helpers.is_helper("ik_hand_gun"))
        self.assertTrue(helpers.is_helper("Manny_Rig:weapon_r"))
        self.assertEqual(helpers.split(["hand_r", "weapon_r", "ik_hand_gun"]),
                         (["hand_r", "ik_hand_gun"], ["weapon_r"]))


class Pure(unittest.TestCase):

    def test_the_driver_stands_where_its_bone_lands(self):
        K = trs((1, 2, 3), (10, 20, 30))
        want = trs((40, 100, 5), (0, 60, 0))
        close(self, K * helpers.driver_target(K, want), want, 1e-9)

    def test_a_weapon_space_is_carried_by_its_hand(self):
        hand_now, hand_wanted = trs((1, 2, 3), (0, 30, 0)), trs((5, 1, 0), (20, 0, 0))
        space_now = trs((0.5, 0, 0)) * hand_now
        close(self, helpers.carried_parent(space_now, hand_now, hand_wanted),
              trs((0.5, 0, 0)) * hand_wanted)
        close(self, helpers.carried_parent(space_now, None, None), space_now)

    def test_driver_channels_keep_pivots_scale_and_rotate_axis(self):
        attrs = {"rotateOrder": 3, "rotateAxis": (10, 0, 5), "scale": (0.4, 0.4, 0.4),
                 "shear": (0, 0, 0), "rotatePivot": (1, 2, 0), "rotatePivotTranslate": (0.5, 0, 0),
                 "scalePivot": (0, 1, 0), "scalePivotTranslate": (0, 0, 0.25)}
        tm = om.MTransformationMatrix()
        tm.setScale([0.4, 0.4, 0.4], om.MSpace.kTransform)
        tm.setScalePivot(om.MPoint(0, 1, 0), om.MSpace.kTransform, False)
        tm.setScalePivotTranslation(om.MVector(0, 0, 0.25), om.MSpace.kTransform)
        tm.setRotatePivot(om.MPoint(1, 2, 0), om.MSpace.kTransform, False)
        tm.setRotatePivotTranslation(om.MVector(0.5, 0, 0), om.MSpace.kTransform)
        tm.setRotationOrientation(om.MEulerRotation(math.radians(10), 0, math.radians(5))
                                  .asQuaternion())
        tm.setRotation(om.MEulerRotation(math.radians(20), math.radians(-35), math.radians(70), 3))
        tm.setTranslation(om.MVector(7, -3, 12), om.MSpace.kTransform)
        rotate, translate = helpers.driver_channels(tm.asMatrix(), attrs, (20, -35, 70))
        for got, want in zip(rotate, (20, -35, 70)):
            self.assertAlmostEqual(got, want, 6)
        for got, want in zip(translate, (7, -3, 12)):
            self.assertAlmostEqual(got, want, 6)


class FakeScene(object):
    """The Writer's seams on a dict scene: worlds, parents' worlds, plug values, who drives."""

    def __init__(self):
        self.worlds, self.parents, self.plugs = {}, {}, {}
        self.weapons, self.cameras, self.followers, self.carriers = {}, {}, {}, {}
        self.unwritable = {}
        self.attrs = {}

    def install(self, test):
        saved = {}
        seams = {"_world": lambda n: om.MMatrix(self.worlds[n]),
                 "_parent_world": lambda n: om.MMatrix(self.parents[n]),
                 "_get": lambda p: self.plugs.get(p, 0.0),
                 "_attrs": lambda n: self.attrs.get(n, {}),
                 "_weapon_of": lambda p: self.weapons.get(p),
                 "_camera_of": lambda p: self.cameras.get(p),
                 "_followers": lambda w: self.followers.get(w, []),
                 "_carrier_of": lambda d: self.carriers.get(d),
                 "_camera_carrier": lambda d: self.carriers.get(d)}
        for name, fn in seams.items():
            saved[name] = getattr(helpers, name)
            setattr(helpers, name, fn)
        saved_writable = helpers.keys.writable
        helpers.keys.writable = lambda plug: (False, self.unwritable[plug.rsplit(".", 1)[0]]) \
            if plug.rsplit(".", 1)[0] in self.unwritable else (True, "")

        def undo():
            for name, fn in saved.items():
                setattr(helpers, name, fn)
            helpers.keys.writable = saved_writable
        test.addCleanup(undo)


def bones_of(paths):
    out = {}
    for leaf, path in paths.items():
        out[leaf] = {"path": path, "parent": BONES[leaf]["parent"], "jointOrient": (0, 0, 0),
                     "rotateAxis": (0, 0, 0), "rotateOrder": 0}
    return out


class WriterTests(unittest.TestCase):

    HAND, WEAPON = "|root|hand_r", "|root|hand_r|weapon_r"
    SWORD, SPACE = "|grp|space|Sword", "|grp|space"

    def setUp(self):
        self.scene = FakeScene()
        self.scene.install(self)
        self.bones = bones_of({"hand_r": self.HAND, "weapon_r": self.WEAPON})
        self.hand_now = trs((-40, 100, 5), (0, 30, 0))
        self.scene.worlds[self.HAND] = self.hand_now

    def wanted(self):
        hand = trs((-30, 110, 0), (0, 0, 40))
        return {"hand_r": hand, "weapon_r": trs((-6, -2, 1), (0, 0, 15)) * hand}

    def test_a_free_weapon_bone_takes_its_local_against_its_parent_s_target(self):
        self.scene.worlds[self.WEAPON] = trs((-6, -2, 1)) * self.hand_now
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        out = writer.solve(self.wanted())
        self.assertAlmostEqual(out.values[self.WEAPON + ".rotateZ"], 15.0, 6)
        self.assertAlmostEqual(out.values[self.WEAPON + ".translateX"], -6.0, 6)
        self.assertEqual(writer.notes, [])

    def test_a_weapon_in_the_hand_is_keyed_so_its_bone_lands(self):
        # the sword rides a weapon space following the hand, the bone follows the sword with the
        # grip's inverse as offset
        space_now = trs((0.2, 0, 0)) * self.hand_now
        sword_now = trs((-3, -1, 0), (0, 0, 5)) * space_now
        K = trs((-2, -1, 1), (0, 0, 7))
        self.scene.worlds.update({self.SWORD: sword_now, self.WEAPON: K * sword_now})
        self.scene.parents[self.SWORD] = space_now
        self.scene.weapons[self.WEAPON] = self.SWORD
        self.scene.carriers[self.SWORD] = self.HAND
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        self.assertEqual(writer.notes, ["weapon_r keyed through Sword"])
        wanted = self.wanted()
        out = writer.solve(wanted)
        self.assertNotIn(self.WEAPON + ".rotateZ", out.values)
        local = trs([out.values[self.SWORD + ".translate" + a] for a in "XYZ"],
                    [out.values[self.SWORD + ".rotate" + a] for a in "XYZ"])
        space_new = trs((0.2, 0, 0)) * wanted["hand_r"]
        close(self, K * local * space_new, wanted["weapon_r"], 1e-6, "the bone lands")

    def test_a_floor_weapon_stands_where_it_is_carried_by_nothing(self):
        floor = trs((100, 0, 30), (0, 45, 0))
        K = trs((1, 0, 0))
        self.scene.worlds.update({self.SWORD: floor, self.WEAPON: K * floor})
        self.scene.parents[self.SWORD] = om.MMatrix()
        self.scene.weapons[self.WEAPON] = self.SWORD
        out = helpers.Writer(None, self.bones, ["weapon_r"]).solve(self.wanted())
        local = trs([out.values[self.SWORD + ".translate" + a] for a in "XYZ"],
                    [out.values[self.SWORD + ".rotate" + a] for a in "XYZ"])
        close(self, K * local, self.wanted()["weapon_r"], 1e-6)

    def test_the_hands_riding_the_weapon_skip_it(self):
        self.scene.worlds.update({self.SWORD: om.MMatrix(), self.WEAPON: om.MMatrix()})
        self.scene.weapons[self.WEAPON] = self.SWORD
        self.scene.followers[self.SWORD] = ["L"]
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        self.assertEqual(writer.leaves(), [])
        self.assertIn("the hands ride Sword", writer.skipped["weapon_r"])
        self.assertEqual(writer.solve(self.wanted()).values, {})

    def test_a_bone_somebody_else_drives_is_skipped(self):
        self.scene.worlds[self.WEAPON] = om.MMatrix()
        self.scene.unwritable[self.WEAPON] = "driven by someConstraint"
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        self.assertIn("driven by someConstraint", writer.skipped["weapon_r"])

    def test_the_camera_control_under_main_rides_the_root_s_travel(self):
        """2026-10-21: the camera's CONTROL is keyed, its parent (Main) carried by the root - an
        animation card moves Main by the travel, and the camera must land on camera_root
        anyway."""
        bones = bones_of({"root": "|r", "camera_root": "|r|camera_root"})
        ctrl, main = "|Main|Camera_ctrl", "|Main"
        root_now = trs((0, 0, 0))
        main_now = trs((0, 0, 0))
        K = trs((0, 0, 0), (0, 0, 0))          # the camera_root stands on the control
        bone_now = trs((5, 164, 2), (-90, 0, 0))
        self.scene.worlds.update({"|r": root_now, "|r|camera_root": bone_now,
                                  ctrl: K.inverse() * bone_now})
        self.scene.parents[ctrl] = main_now
        self.scene.cameras["|r|camera_root"] = ctrl
        self.scene.carriers[ctrl] = "root"
        writer = helpers.Writer(None, bones, ["camera_root"])
        self.assertEqual(writer.notes, ["camera_root keyed through Camera_ctrl"])
        root_wanted = trs((50, 0, -20), (0, 30, 0))
        wanted_bone = trs((60, 150, -10), (-80, 20, 0))
        out = writer.solve({"root": root_wanted, "camera_root": wanted_bone})
        local = trs([out.values[ctrl + ".translate" + a] for a in "XYZ"],
                    [out.values[ctrl + ".rotate" + a] for a in "XYZ"])
        main_new = main_now * root_now.inverse() * root_wanted       # Main moved with the root
        close(self, K * local * main_new, wanted_bone, 1e-6, "camera_root lands")

    def test_the_camera_to_set_up_is_a_free_camera_root(self):
        bones = bones_of({"camera_root": "|root|camera_root"})
        self.scene.worlds["|root|camera_root"] = om.MMatrix()
        writer = helpers.Writer(None, bones, ["camera_root"])
        self.assertEqual(writer.camera_to_set_up(), "|root|camera_root")
        self.scene.cameras["|root|camera_root"] = "|grp|SceneSetup_camera"
        self.scene.worlds["|grp|SceneSetup_camera"] = om.MMatrix()
        writer = helpers.Writer(None, bones, ["camera_root"])
        self.assertIsNone(writer.camera_to_set_up())
        self.assertEqual(writer.notes, ["camera_root keyed through SceneSetup_camera"])


class CameraCarriers(unittest.TestCase):

    def test_head_and_follow_carriers(self):
        from maya_poselib import helpers
        self.assertEqual(helpers.HEAD_BONE, "head")
        self.assertEqual(helpers._carrier_for_parent("|r|Main|FKHead_M", head=True,
                                                      follow=False), "head")

    def test_an_entry_is_not_a_camera_unless_said(self):
        from maya_poselib import helpers
        self.assertFalse(helpers.Entry("weapon_r", "|w", "driver", "|s", None, None).camera)
        self.assertIsNone(helpers._carrier_for_parent("|r|Main|Camera_follow", head=False,
                                                       follow=True))


if __name__ == "__main__":
    unittest.main()

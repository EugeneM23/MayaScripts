"""maya_walk.scene.keys_changed: new animation on a walked skeleton told from a bone whose curves
something else took.

Measured in the animator's scene on 2026-10-29: the walk keyed `weapon_r`, then the Long Sword went
into the hand - bonedrive.link cut that bone's curves and constrained it to the sword - and from then
on every knob of the card refused with «new keys on it since the walk», although not one key of the
walk's own output had changed. The digest the memo keeps must not read a bone a driver took as a new
take; a bone that really was re-keyed still must.
"""

import unittest

from tests.test_walk_scene_more import Base, scene


BONES = (("root", ""), ("pelvis", "root"), ("spine_01", "pelvis"), ("hand_r", "spine_01"),
         ("weapon_r", "hand_r"), ("camera_root", "root"))


class KeysChanged(Base):
    """A small walked skeleton: every bone keyed on its rotateY, the root keyed on translateZ."""

    def setUp(self):
        Base.setUp(self)
        self.paths = {}
        parent = {}
        for leaf, above in BONES:
            path = (parent[above] + "|" + leaf) if above else "|" + leaf
            parent[leaf] = path
            self.paths[leaf] = path
            self.fake.joint(path)
            self.fake.key(path + ".rotateY", [[0, 0.0], [5, 10.0]], kind="animCurveTA")
        self.fake.key(self.paths["root"] + ".translateZ", [[0, 0.0], [10, 50.0]])
        self.walked()

    def walked(self):
        """The memo as apply() writes it: the walk's name and the digest of the keys as they stand."""
        self.memo("|root", walk="asd", version=4, keys=scene.keys_print("|root"))

    def driven(self, leaf, channels=scene.CHANNELS):
        """`leaf`'s own curves cut and the channels driven from a node - what Add Weapon does to
        weapon_r (bonedrive.link) and Camera Setup to camera_root."""
        node = self.fake.add(leaf + "_parentConstraint1", "parentConstraint")
        for ch in channels:
            plug = self.paths[leaf] + "." + ch
            source = self.fake.conn.pop(plug, None)
            if source:
                self.fake.delete(source.split(".")[0])
            self.fake.conn[plug] = node + ".constraint" + ch[0].upper() + ch[1:]

    # ---- a driver took a bone: not new animation

    def test_a_weapon_in_the_hand_is_not_new_animation(self):
        self.assertFalse(scene.keys_changed("|root"))
        self.driven("weapon_r")
        self.assertFalse(scene.keys_changed("|root"),
                         "Add Weapon cut weapon_r's curves - the walk's own keys did not change")

    def test_a_camera_on_the_skeleton_is_not_new_animation(self):
        self.driven("camera_root")
        self.assertFalse(scene.keys_changed("|root"))

    def test_a_weapon_and_a_camera_together(self):
        self.driven("weapon_r")
        self.driven("camera_root")
        self.assertFalse(scene.keys_changed("|root"))

    def test_the_knobs_keep_working_once_the_driver_is_gone_again(self):
        self.driven("weapon_r")
        self.assertFalse(scene.keys_changed("|root"))
        for ch in scene.CHANNELS:                                  # Remove Weapon hands the bone back
            self.fake.conn.pop(self.paths["weapon_r"] + "." + ch, None)
        self.assertFalse(scene.keys_changed("|root"))

    # ---- what is still new animation

    def test_a_clip_keyed_over_the_walk_is_new_animation(self):
        self.fake.curves["pelvis_rotateY"].append([9, 20.0])
        self.assertTrue(scene.keys_changed("|root"))

    def test_one_value_moved_on_one_bone_is_new_animation(self):
        self.fake.curves["spine_01_rotateY"][1][1] = 11.0
        self.assertTrue(scene.keys_changed("|root"))

    def test_a_clip_over_a_skeleton_that_also_holds_a_weapon(self):
        self.driven("weapon_r")
        self.fake.curves["pelvis_rotateY"].append([9, 20.0])
        self.assertTrue(scene.keys_changed("|root"),
                        "a weapon in the hand must not hide a clip loaded onto the skeleton")

    # ---- the rules this leaves

    def test_a_bone_whose_keys_were_deleted_by_hand_is_not_new_animation(self):
        self.fake.delete("spine_01_rotateY")
        self.fake.conn.pop(self.paths["spine_01"] + ".rotateY", None)
        self.assertFalse(scene.keys_changed("|root"),
                         "nothing is there to keep - the next press keys that bone again")

    def test_a_bone_the_walk_never_keyed_gaining_keys_is_not_new_animation(self):
        self.fake.joint(self.paths["root"] + "|ik_hand_l")
        self.fake.key(self.paths["root"] + "|ik_hand_l.rotateY", [[0, 0.0], [4, 7.0]], kind="animCurveTA")
        self.assertFalse(scene.keys_changed("|root"))

    def test_a_marker_from_before_the_per_bone_digest_cannot_tell(self):
        self.memo("|root", walk="asd", version=4, keys="0123456789abcdef")
        self.assertFalse(scene.keys_changed("|root"))

    def test_a_marker_with_no_walk_never_answers_changed(self):
        self.memo("|root", version=4, keys=scene.keys_print("|root"))
        self.fake.curves["pelvis_rotateY"].append([9, 20.0])
        self.assertFalse(scene.keys_changed("|root"))

    # ---- the digest itself

    def test_the_digest_is_a_bone_a_row_and_stable(self):
        first = scene.keys_print("|root")
        self.assertEqual(scene.keys_print("|root"), first)
        self.assertEqual(sorted(first), sorted(leaf for leaf, _ in BONES))
        self.assertTrue(all(isinstance(v, str) and v for v in first.values()))

    def test_a_driven_bone_is_left_out_of_the_digest(self):
        self.driven("weapon_r")
        self.assertNotIn("weapon_r", scene.keys_print("|root"))

    def test_a_layer_the_animator_keys_on_top_is_not_new_animation(self):
        f = self.fake
        f.add("blend1", "animBlendNodeAdditiveRotation")
        f.curve("layer_rotateY", [[0, 0.0], [3, 99.0]], kind="animCurveTA")
        f.conn["blend1.inputAY"] = f.conn.pop(self.paths["pelvis"] + ".rotateY")
        f.conn["blend1.inputBY"] = "layer_rotateY.output"
        f.conn[self.paths["pelvis"] + ".rotateY"] = "blend1.outputY"
        self.assertFalse(scene.keys_changed("|root"))
        f.curves["layer_rotateY"][1][1] = 3.0
        self.assertFalse(scene.keys_changed("|root"))


if __name__ == "__main__":
    unittest.main()

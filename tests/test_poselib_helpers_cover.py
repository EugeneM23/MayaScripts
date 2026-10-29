"""The camera and weapon bones on a card, the parts `test_poselib_helpers` leaves out: the scene reads
(`_world`, `_parent_world`, `_get`, `_attrs`), the 1P chest (`under_chest`, `first_person`), who
carries a camera control (`_camera_carrier`, `_camera_follow`), Aim Mode (`_aim_of`, `_point`, a
Writer keying a weapon or a camera through its two controllers), `merged`, the seeded rotate read
and `set_up_camera`.

Every scene seam is rebound for the test (the module's `cmds`, the `maya_scenesetup` functions it
asks) and restored by cleanup; no Maya node is touched.
"""

import sys
import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya.api.OpenMaya as om
from maya_scenesetup import bonedrive, camera, cameraaim, connections, rootcontrol, weaponaim, weaponspace

from maya_poselib import helpers, skelsolve
from tests.test_poselib_helpers import FakeScene, bones_of, close, trs


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


class ReadCmds(object):
    """`getAttr`, `listRelatives(parent)`, `attributeQuery`, `ls` of a dict scene."""

    def __init__(self, values=None, parents=None, marked=(), found=None, broken=False):
        self.values = values or {}
        self.parents = parents or {}
        self.marked = set(marked)
        self.found = found or {}
        self.broken = broken
        self.queried = []

    def getAttr(self, plug):
        if self.broken:
            raise RuntimeError("cannot read")
        return self.values[plug]

    def listRelatives(self, node, **kwargs):
        if self.broken:
            raise RuntimeError("no dag")
        return self.parents.get(node)

    def attributeQuery(self, attr, node=None, exists=False):
        self.queried.append((node, attr))
        return (node, attr) in self.marked

    def ls(self, pattern, **kwargs):
        if self.broken:
            raise RuntimeError("cannot list")
        return self.found.get(pattern)


class SceneReads(Patched):

    def test_the_world_and_the_parent_world_are_the_matrices_of_their_plugs(self):
        world = [float(v) for v in trs((1, 2, 3))]
        parent = [float(v) for v in trs((4, 5, 6))]
        self.patch(helpers, "cmds", ReadCmds({"|n.worldMatrix[0]": world,
                                              "|n.parentMatrix[0]": parent}))
        close(self, helpers._world("|n"), world)
        close(self, helpers._parent_world("|n"), parent)

    def test_a_plug_is_read_as_a_float(self):
        self.patch(helpers, "cmds", ReadCmds({"|n.rotateZ": 3}))
        value = helpers._get("|n.rotateZ")
        self.assertEqual(value, 3.0)
        self.assertIsInstance(value, float)

    def test_a_transform_s_attrs_are_its_order_and_its_pivots_scale_and_shear(self):
        values = {"|n.rotateOrder": 2, "|n.rotateAxis": [(10, 0, 5)], "|n.scale": [(1, 2, 3)],
                  "|n.shear": [(0, 0, 0)], "|n.rotatePivot": [(1, 1, 1)],
                  "|n.rotatePivotTranslate": [(2, 2, 2)], "|n.scalePivot": [(3, 3, 3)],
                  "|n.scalePivotTranslate": [(4, 4, 4)]}
        self.patch(helpers, "cmds", ReadCmds(values))
        self.assertEqual(helpers._attrs("|n"), {
            "rotateOrder": 2, "rotateAxis": [10.0, 0.0, 5.0], "scale": [1.0, 2.0, 3.0],
            "shear": [0.0, 0.0, 0.0], "rotatePivot": [1.0, 1.0, 1.0],
            "rotatePivotTranslate": [2.0, 2.0, 2.0], "scalePivot": [3.0, 3.0, 3.0],
            "scalePivotTranslate": [4.0, 4.0, 4.0]})

    def test_a_point_is_the_direction_times_the_distance_in_the_matrix(self):
        matrix = [float(v) for v in trs((10, 20, 30))]
        self.assertEqual(helpers._point(matrix, (0, 0, 1), 5), (10.0, 20.0, 35.0))
        self.assertEqual(helpers._point(list(om.MMatrix()), (1, 2, 0), 2), (2.0, 4.0, 0.0))


class Delegates(Patched):

    def test_the_weapon_driving_a_bone_is_bonedrive_s_answer(self):
        self.patch(bonedrive, "driving_weapon", lambda bone: "|Sword" if bone == "|b" else None)
        self.assertEqual(helpers._weapon_of("|b"), "|Sword")
        self.assertIsNone(helpers._weapon_of("|other"))

    def test_the_node_keyed_for_a_camera_bone_is_the_cameras_answer(self):
        self.patch(camera, "keyed_node", lambda bone: "|Camera_ctrl" if bone == "|b" else None)
        self.assertEqual(helpers._camera_of("|b"), "|Camera_ctrl")
        self.assertIsNone(helpers._camera_of("|other"))

    def test_the_hands_riding_a_weapon_are_connections_answer(self):
        self.patch(connections, "followers_of", lambda weapon: ["hand_l"])
        self.assertEqual(helpers._followers("|Sword"), ["hand_l"])

    def test_the_joint_carrying_a_driver_is_the_weapon_spaces_answer(self):
        self.patch(weaponspace, "holding_hand", lambda node: "|hand_r" if node == "|Sword" else None)
        self.assertEqual(helpers._carrier_of("|Sword"), "|hand_r")
        self.assertIsNone(helpers._carrier_of("|floor"))


class NoSceneSetup(Patched):
    """Where Scene Setup is not installed, every ask of it answers 'nobody': a helper is then
    written as a free joint, never an error."""

    def setUp(self):
        saved = sys.modules.get("maya_scenesetup", False)
        sys.modules["maya_scenesetup"] = None

        def undo():
            if saved is False:
                del sys.modules["maya_scenesetup"]
            else:
                sys.modules["maya_scenesetup"] = saved

        self.addCleanup(undo)

    def test_no_weapon_drives_a_bone(self):
        self.assertIsNone(helpers._weapon_of("|b"))

    def test_no_camera_holds_a_bone_s_motion(self):
        self.assertIsNone(helpers._camera_of("|b"))

    def test_no_control_carries_a_camera_control(self):
        self.assertIsNone(helpers._camera_carrier("|ctrl"))
        self.assertIsNone(helpers._camera_follow("|ctrl"))

    def test_no_driver_is_in_aim_mode(self):
        self.assertIsNone(helpers._aim_of("|ctrl"))

    def test_no_hands_ride_a_weapon_and_no_joint_carries_a_driver(self):
        self.assertEqual(helpers._followers("|Sword"), [])
        self.assertIsNone(helpers._carrier_of("|Sword"))

    def test_no_range_is_known_for_a_bone(self):
        self.assertIsNone(helpers._span("|b"))


class CarrierForParent(unittest.TestCase):

    def test_a_parent_that_is_neither_the_head_nor_a_follow_group_carries_nothing(self):
        self.assertIsNone(helpers._carrier_for_parent("|r|Main", head=False, follow=False))

    def test_a_follow_group_carries_nothing_even_under_the_head(self):
        self.assertIsNone(helpers._carrier_for_parent("|r|FKHead_M", head=True, follow=True))


class UnderChest(Patched):

    def test_a_marked_ancestor_at_any_height_is_a_chest(self):
        parents = {"|a|b|c|n": ["|a|b|c"], "|a|b|c": ["|a|b"], "|a|b": ["|a"], "|a": None}
        self.patch(helpers, "cmds", ReadCmds(parents=parents,
                                             marked=[("|a|b", helpers.CHEST_MARKER)]))
        self.assertTrue(helpers.under_chest("|a|b|c|n"))

    def test_the_node_itself_does_not_count(self):
        self.patch(helpers, "cmds", ReadCmds(parents={"|n": None},
                                             marked=[("|n", helpers.CHEST_MARKER)]))
        self.assertFalse(helpers.under_chest("|n"))

    def test_no_marked_ancestor_is_no_chest(self):
        self.patch(helpers, "cmds", ReadCmds(parents={"|a|n": ["|a"], "|a": None}))
        self.assertFalse(helpers.under_chest("|a|n"))

    def test_a_scene_that_cannot_be_asked_is_no_chest(self):
        self.patch(helpers, "cmds", ReadCmds(broken=True))
        self.assertFalse(helpers.under_chest("|n"))


class FirstPerson(Patched):

    def rig_ref(self, namespace="Manny_Rig1"):
        rig = type("Rig", (), {"namespace": namespace})()
        return type("Ref", (), {"kind": "rig", "rig": rig})()

    def marked_scene(self, **namespaces):
        found = {"*." + helpers.CHEST_MARKER: list(namespaces)}
        values = dict((node + "." + helpers.CHEST_MARKER, ns) for node, ns in namespaces.items())
        return ReadCmds(values=values, found=found)

    def test_a_rig_whose_namespace_marks_a_chest_knot_is_first_person(self):
        self.patch(helpers, "cmds", self.marked_scene(**{"|knot1": "Other1", "|knot2": "Manny_Rig1"}))
        self.assertTrue(helpers.first_person(self.rig_ref()))

    def test_a_chest_knot_of_another_rig_is_not_this_rig_s(self):
        self.patch(helpers, "cmds", self.marked_scene(**{"|knot1": "Other1"}))
        self.assertFalse(helpers.first_person(self.rig_ref()))

    def test_no_chest_knot_in_the_scene_is_third_person(self):
        self.patch(helpers, "cmds", ReadCmds())
        self.assertFalse(helpers.first_person(self.rig_ref()))

    def test_a_skeleton_or_nothing_is_never_first_person(self):
        self.patch(helpers, "cmds", self.marked_scene(**{"|knot1": "Manny_Rig1"}))
        skeleton = type("Ref", (), {"kind": "skeleton", "rig": None})()
        self.assertFalse(helpers.first_person(skeleton))
        self.assertFalse(helpers.first_person(None))
        no_rig = type("Ref", (), {"kind": "rig", "rig": None})()
        self.assertFalse(helpers.first_person(no_rig))

    def test_a_scene_that_cannot_be_listed_is_third_person(self):
        self.patch(helpers, "cmds", ReadCmds(broken=True))
        self.assertFalse(helpers.first_person(self.rig_ref()))


class CameraCarrier(Patched):
    """Who carries a camera control's parent rigidly. The scene is the control's chain of parents
    and the markers on them; `camera.is_control` and `camera.is_main` are rebound."""

    DRIVER = "|Main|Parent|Camera_ctrl"

    def setUp(self):
        self.control = True
        self.mains = set()
        self.patch(camera, "is_control", lambda node: self.control)
        self.patch(camera, "is_main", lambda node: node in self.mains)

    def scene(self, parent, marked=(), chest_parents=None):
        parents = {self.DRIVER: [parent] if parent else None}
        parents.update(chest_parents or {})
        self.patch(helpers, "cmds", ReadCmds(parents=parents, marked=marked))

    def test_something_that_is_not_a_camera_control_has_no_carrier(self):
        self.control = False
        self.scene("|Main")
        self.assertIsNone(helpers._camera_carrier(self.DRIVER))

    def test_a_control_under_main_is_carried_by_the_root(self):
        self.mains.add("|Main")
        self.scene("|Main")
        self.assertEqual(helpers._camera_carrier(self.DRIVER), "root")

    def test_a_control_under_the_root_control_is_carried_by_the_root(self):
        self.scene("|Root_ctrl", marked=[("|Root_ctrl", rootcontrol.MARKER)])
        self.assertEqual(helpers._camera_carrier(self.DRIVER), "root")

    def test_a_control_in_a_follow_group_has_no_single_carrier(self):
        self.scene("|Camera_follow", marked=[("|Camera_follow", camera.FOLLOW_MARKER)])
        self.assertIsNone(helpers._camera_carrier(self.DRIVER))

    def test_a_control_under_the_head_control_is_carried_by_the_head(self):
        self.scene("|Main|ns:" + camera.HEAD)
        self.assertEqual(helpers._camera_carrier(self.DRIVER), "head")

    def test_a_control_under_the_1p_chest_is_carried_by_spine_03(self):
        self.scene("|Elsewhere", chest_parents={"|Elsewhere": ["|Chest"]},
                   marked=[("|Chest", helpers.CHEST_MARKER)])
        self.assertEqual(helpers._camera_carrier(self.DRIVER), helpers.CHEST_BONE)

    def test_a_control_under_none_of_these_is_carried_by_the_world(self):
        self.scene("|Elsewhere", chest_parents={"|Elsewhere": None})
        self.assertIsNone(helpers._camera_carrier(self.DRIVER))

    def test_a_control_with_no_parent_is_carried_by_the_world(self):
        self.scene(None)
        self.assertIsNone(helpers._camera_carrier(self.DRIVER))


class CameraFollow(Patched):

    DRIVER = "|Main|Camera_follow|Camera_ctrl"
    GROUP = "|Main|Camera_follow"

    def setUp(self):
        self.control = True
        self.group = self.GROUP
        self.patch(camera, "is_control", lambda node: self.control)
        self.patch(camera, "follow_of", lambda node: self.group)

    def scene(self, followed, marked=()):
        plug = self.GROUP + "." + camera.FOLLOW_MARKER
        found = {followed: [followed]} if followed else {}
        self.patch(helpers, "cmds", ReadCmds(values={plug: followed}, found=found, marked=marked))

    def test_something_that_is_not_a_camera_control_follows_nothing(self):
        self.control = False
        self.scene("|r|FKHead_M")
        self.assertIsNone(helpers._camera_follow(self.DRIVER))

    def test_a_control_outside_a_follow_group_follows_nothing(self):
        self.group = None
        self.scene("|r|FKHead_M")
        self.assertIsNone(helpers._camera_follow(self.DRIVER))

    def test_a_group_following_the_head_control_turns_with_the_root_and_rides_the_head(self):
        self.scene("|r|ns:" + camera.HEAD)
        self.assertEqual(helpers._camera_follow(self.DRIVER), ("root", "head"))

    def test_a_group_following_the_root_control_rides_the_root(self):
        self.scene("|r|Root_ctrl", marked=[("|r|Root_ctrl", rootcontrol.MARKER)])
        self.assertEqual(helpers._camera_follow(self.DRIVER), ("root", "root"))

    def test_a_group_following_the_1p_chest_rides_spine_03(self):
        self.scene("|r|Chest", marked=[("|r|Chest", helpers.CHEST_MARKER)])
        self.assertEqual(helpers._camera_follow(self.DRIVER), ("root", helpers.CHEST_BONE))

    def test_a_group_following_any_other_node_has_no_place_carrier(self):
        self.scene("|r|prop")
        self.assertEqual(helpers._camera_follow(self.DRIVER), ("root", None))

    def test_a_group_whose_followed_node_is_gone_has_no_place_carrier(self):
        self.scene("")
        self.assertEqual(helpers._camera_follow(self.DRIVER), ("root", None))


class AimOf(Patched):

    def setUp(self):
        self.groups = {"weapon": {}, "camera": {}}
        self.controllers = {}
        for key, module in (("weapon", weaponaim), ("camera", cameraaim)):
            self.patch(module, "group_of", self.group_of(key))
            self.patch(module, "controllers", lambda group: self.controllers[group])
            self.patch(module, "stored_vectors", lambda group: ((0, 0, 1), (0, 1, 0), 10.0, 20.0))

    def group_of(self, key):
        return lambda driver: self.groups[key].get(driver)

    def test_a_driver_in_no_aim_mode_has_no_aim(self):
        self.assertIsNone(helpers._aim_of("|Sword"))

    def test_a_weapon_in_aim_mode_is_its_controllers_and_stored_vectors(self):
        self.groups["weapon"]["|Sword"] = "G1"
        self.controllers["G1"] = {"target": "|T", "up": "|U"}
        self.assertEqual(helpers._aim_of("|Sword"),
                         helpers.Aim("|T", "|U", (0, 0, 1), (0, 1, 0), 10.0, 20.0))

    def test_a_camera_control_in_aim_mode_is_found_when_no_weapon_group_holds_it(self):
        self.groups["camera"]["|Camera_ctrl"] = "G2"
        self.controllers["G2"] = {"target": "|CT", "up": "|CU"}
        aim = helpers._aim_of("|Camera_ctrl")
        self.assertEqual((aim.target, aim.up), ("|CT", "|CU"))

    def test_an_aim_group_missing_a_controller_is_no_aim(self):
        self.groups["weapon"]["|Sword"] = "G1"
        self.controllers["G1"] = {"target": "|T"}
        self.assertIsNone(helpers._aim_of("|Sword"))
        self.controllers["G1"] = {"up": "|U"}
        self.assertIsNone(helpers._aim_of("|Sword"))

    def test_the_weapon_group_is_taken_before_the_camera_group(self):
        self.groups["weapon"]["|X"] = "GW"
        self.groups["camera"]["|X"] = "GC"
        self.controllers["GW"] = {"target": "|WT", "up": "|WU"}
        self.controllers["GC"] = {"target": "|CT", "up": "|CU"}
        self.assertEqual(helpers._aim_of("|X").target, "|WT")


class Merged(unittest.TestCase):

    def test_the_body_values_come_first_and_a_helper_overrides_a_shared_plug(self):
        body = skelsolve.Solution({"a.rx": 1.0, "b.rx": 2.0}, ["n1", "n2"], {"hand": "driven"})
        helper = skelsolve.Solution({"b.rx": 9.0, "w.tx": 3.0}, ["n2", "n3"], {"hand": "locked",
                                                                               "weapon_r": "x"})
        out = helpers.merged(body, helper)
        self.assertEqual(list(out.values.items()), [("a.rx", 1.0), ("b.rx", 9.0), ("w.tx", 3.0)])
        self.assertEqual(out.notes, ["n1", "n2", "n3"])
        self.assertEqual(out.skipped, {"hand": "locked", "weapon_r": "x"})

    def test_the_inputs_are_left_as_they_were(self):
        body = skelsolve.Solution({"a.rx": 1.0}, ["n1"], {})
        helper = skelsolve.Solution({"w.tx": 3.0}, ["n3"], {"w": "why"})
        helpers.merged(body, helper)
        self.assertEqual((dict(body.values), body.notes, body.skipped), ({"a.rx": 1.0}, ["n1"], {}))


class WriterSeeds(Patched):

    PATH = "|root|weapon_r"

    def setUp(self):
        self.scene = FakeScene()
        self.scene.install(self)
        self.bones = bones_of({"root": "|root", "weapon_r": self.PATH})
        self.bones["weapon_r"]["parent"] = "root"
        self.scene.worlds["|root"] = om.MMatrix()
        self.scene.worlds[self.PATH] = om.MMatrix()
        self.wanted = {"root": om.MMatrix(), "weapon_r": trs((1, 2, 3), (0, 0, 15))}

    def values(self, seed=None):
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        return writer.solve(self.wanted, seed).values

    def test_a_seed_holding_every_rotate_plug_is_the_euler_to_stay_nearest(self):
        seed = dict((self.PATH + "." + c, v) for c, v in
                    (("rotateX", 0.0), ("rotateY", 0.0), ("rotateZ", 375.0)))
        self.assertAlmostEqual(self.values(seed)[self.PATH + ".rotateZ"], 375.0, 6)

    def test_a_seed_missing_a_plug_is_read_from_the_scene(self):
        self.scene.plugs[self.PATH + ".rotateZ"] = 375.0
        seed = {self.PATH + ".rotateX": 0.0}
        self.assertAlmostEqual(self.values(seed)[self.PATH + ".rotateZ"], 375.0, 6)

    def test_no_seed_reads_the_scene_and_the_plain_euler_comes_back(self):
        self.assertAlmostEqual(self.values()[self.PATH + ".rotateZ"], 15.0, 6)

    def test_a_joint_helper_takes_its_parent_world_from_the_scene_when_the_parent_is_not_wanted(self):
        self.scene.parents[self.PATH] = trs((1, 0, 0))
        out = helpers.Writer(None, self.bones, ["weapon_r"]).solve({"weapon_r": trs((1, 2, 3))})
        self.assertAlmostEqual(out.values[self.PATH + ".translateX"], 0.0, 6)
        self.assertAlmostEqual(out.values[self.PATH + ".translateY"], 2.0, 6)

    def test_a_helper_the_card_does_not_name_is_left_alone(self):
        writer = helpers.Writer(None, self.bones, ["weapon_r"])
        self.assertEqual(writer.solve({"root": om.MMatrix()}).values, {})

    def test_a_leaf_the_target_does_not_hold_is_not_prepared(self):
        writer = helpers.Writer(None, self.bones, ["weapon_l", "weapon_r", "camera_root"])
        self.assertEqual(writer.leaves(), ["weapon_r"])


def bone(path, parent):
    return {"path": path, "parent": parent, "jointOrient": (0, 0, 0), "rotateAxis": (0, 0, 0),
            "rotateOrder": 0}


class AimedWriter(Patched):
    """A weapon (or a camera control) in Aim Mode keys its translate and its two controllers'
    translates, never its rotate: the rotate is whatever the controllers aim."""

    SWORD, SPACE = "|grp|Sword", "|grp"
    TARGET, UP = "|aim|target", "|aim|up"
    WEAPON = "|root|hand_r|weapon_r"
    HAND = "|root|hand_r"

    def setUp(self):
        self.scene = FakeScene()
        self.scene.install(self)
        self.aim = helpers.Aim(self.TARGET, self.UP, (0, 0, 1), (0, 1, 0), 10.0, 20.0)
        self.patch(helpers, "_aim_of", lambda driver: self.aim)
        self.patch(helpers, "under_chest", lambda node: False)
        self.bones = bones_of({"hand_r": self.HAND, "weapon_r": self.WEAPON})
        self.scene.worlds.update({self.HAND: om.MMatrix(), self.WEAPON: om.MMatrix(),
                                  self.SWORD: om.MMatrix()})
        self.scene.parents.update({self.SWORD: om.MMatrix(), self.TARGET: om.MMatrix(),
                                   self.UP: om.MMatrix()})
        self.scene.weapons[self.WEAPON] = self.SWORD
        self.wanted = {"hand_r": om.MMatrix(), "weapon_r": trs((1, 2, 3))}

    def writer(self):
        return helpers.Writer(None, self.bones, ["weapon_r"])

    def test_the_note_says_the_controllers_are_what_is_keyed(self):
        self.assertEqual(self.writer().notes,
                         ["weapon_r keyed through Sword (Aim Mode: its controllers)"])

    def test_the_weapon_and_both_controllers_get_a_translate_and_nothing_gets_a_rotate(self):
        out = self.writer().solve(self.wanted).values
        self.assertEqual(sorted(out), sorted(
            "%s.translate%s" % (node, axis) for node in (self.SWORD, self.TARGET, self.UP)
            for axis in "XYZ"))

    def test_the_controllers_stand_their_distance_along_their_vectors_from_the_weapon(self):
        out = self.writer().solve(self.wanted).values
        for axis, want in zip("XYZ", (1.0, 2.0, 3.0)):
            self.assertAlmostEqual(out[self.SWORD + ".translate" + axis], want, 6)
        for axis, want in zip("XYZ", (1.0, 2.0, 13.0)):
            self.assertAlmostEqual(out[self.TARGET + ".translate" + axis], want, 6)
        for axis, want in zip("XYZ", (1.0, 22.0, 3.0)):
            self.assertAlmostEqual(out[self.UP + ".translate" + axis], want, 6)

    def test_a_controller_parent_is_undone_so_its_translate_is_local(self):
        self.scene.parents[self.TARGET] = trs((0, 0, 100))
        out = self.writer().solve(self.wanted).values
        self.assertAlmostEqual(out[self.TARGET + ".translateZ"], 13.0 - 100.0, 6)

    def test_a_controller_under_the_1p_chest_is_carried_as_the_chest_will_stand(self):
        chest = "|root|spine_03"
        self.bones["spine_03"] = bone(chest, "root")
        self.scene.worlds[chest] = om.MMatrix()
        self.wanted["spine_03"] = trs((0, 0, 50))
        self.patch(helpers, "under_chest", lambda node: node == self.TARGET)
        out = self.writer().solve(self.wanted).values
        self.assertAlmostEqual(out[self.TARGET + ".translateZ"], 13.0 - 50.0, 6)
        self.assertAlmostEqual(out[self.UP + ".translateZ"], 3.0, 6)

    def test_a_locked_controller_translate_skips_the_weapon_and_names_the_controller(self):
        self.scene.unwritable[self.UP] = "driven by something"
        writer = self.writer()
        self.assertEqual(writer.leaves(), [])
        self.assertIn("translateX driven by something", writer.skipped["weapon_r"])
        self.assertTrue(writer.skipped["weapon_r"].startswith("Sword "))

    def test_a_camera_aimed_through_a_follow_group_carries_its_controllers_with_the_group(self):
        camera_path = "|root|camera_root"
        bones = bones_of({"root": "|root", "camera_root": camera_path})
        bones["head"] = bone("|root|head", "root")
        ctrl, group = "|Main|Camera_follow|Camera_ctrl", trs((0, 160, 0))
        self.scene.weapons.clear()
        self.scene.cameras[camera_path] = ctrl
        self.scene.follows[ctrl] = ("root", "head")
        self.scene.worlds.update({"|root": om.MMatrix(), "|root|head": trs((0, 160, 0)),
                                  camera_path: om.MMatrix(), ctrl: om.MMatrix()})
        self.scene.parents.update({ctrl: group, self.TARGET: group, self.UP: group})
        writer = helpers.Writer(None, bones, ["camera_root"])
        self.assertEqual(writer.entries[0].mode, "aimed")
        self.assertTrue(writer.entries[0].camera)
        wanted = {"root": om.MMatrix(), "head": trs((0, 180, 0)), "camera_root": om.MMatrix()}
        out = writer.solve(wanted).values
        self.assertAlmostEqual(out[self.TARGET + ".translateY"], -180.0, 6)
        self.assertAlmostEqual(out[self.TARGET + ".translateZ"], 10.0, 6)

    def test_a_camera_aimed_under_a_carrier_carries_its_controllers_with_that_bone(self):
        camera_path = "|root|camera_root"
        bones = bones_of({"root": "|root", "camera_root": camera_path})
        ctrl = "|Main|Camera_ctrl"
        self.scene.weapons.clear()
        self.scene.cameras[camera_path] = ctrl
        self.scene.carriers[ctrl] = "root"
        self.scene.worlds.update({"|root": om.MMatrix(), camera_path: om.MMatrix(),
                                  ctrl: om.MMatrix()})
        self.scene.parents.update({ctrl: om.MMatrix(), self.TARGET: om.MMatrix(),
                                   self.UP: om.MMatrix()})
        writer = helpers.Writer(None, bones, ["camera_root"])
        out = writer.solve({"root": trs((0, 0, 30)), "camera_root": om.MMatrix()}).values
        self.assertAlmostEqual(out[self.TARGET + ".translateZ"], 10.0 - 30.0, 6)


class CameraSpan(Patched):

    def test_the_range_is_the_playback_range_widened_to_the_bone_s_keys(self):
        class Cmds(object):
            def keyframe(self, bone, **kwargs):
                return [-5.0, 60.0, 140.0]

            def playbackOptions(self, query=False, min=False, max=False):
                return 1 if min else 100

        self.patch(helpers, "cmds", Cmds())
        self.assertEqual(helpers._span("|camera_root"), (-5.0, 140.0))

    def test_a_bone_with_no_keys_gets_the_playback_range(self):
        class Cmds(object):
            def keyframe(self, bone, **kwargs):
                return None

            def playbackOptions(self, query=False, min=False, max=False):
                return 1 if min else 100

        self.patch(helpers, "cmds", Cmds())
        self.assertEqual(helpers._span("|camera_root"), (1, 100))


class SetUpCamera(Patched):

    BONE = "|root|ns:camera_root"

    class Cmds(object):
        def __init__(self, existing, selection):
            self.existing = set(existing)
            self.selection = list(selection)
            self.selected = []

        def objExists(self, node):
            return node in self.existing

        def ls(self, selection=False, long=False):
            return self.selection

        def select(self, *nodes, **kwargs):
            self.selected.append((nodes, kwargs))

    def setUp(self):
        self.setups = []
        self.patch(helpers, "_camera_of", lambda bone: None)
        self.patch(helpers, "_span", lambda bone: (1, 120))
        self.patch(camera, "setup", lambda bone, start, end: self.setups.append((bone, start, end)))

    def scene(self, existing=(), selection=()):
        fake = self.Cmds(existing, selection)
        self.patch(helpers, "cmds", fake)
        return fake

    def test_a_free_bone_gets_a_camera_over_the_span_and_the_line_to_say(self):
        self.scene(existing=[self.BONE])
        self.assertEqual(helpers.set_up_camera(self.BONE), "camera set up on camera_root")
        self.assertEqual(self.setups, [(self.BONE, 1, 120)])

    def test_no_bone_a_gone_bone_or_a_bone_already_set_up_says_nothing(self):
        self.scene(existing=[self.BONE])
        self.assertEqual(helpers.set_up_camera(None), "")
        self.assertEqual(helpers.set_up_camera("|gone"), "")
        self.patch(helpers, "_camera_of", lambda bone: "|Camera_ctrl")
        self.assertEqual(helpers.set_up_camera(self.BONE), "")
        self.assertEqual(self.setups, [])

    def test_the_animator_s_selection_that_still_exists_is_selected_again(self):
        fake = self.scene(existing=[self.BONE, "|a"], selection=["|a", "|gone"])
        helpers.set_up_camera(self.BONE)
        self.assertEqual(fake.selected, [((["|a"],), {"replace": True})])

    def test_an_empty_selection_is_cleared_again(self):
        fake = self.scene(existing=[self.BONE], selection=[])
        helpers.set_up_camera(self.BONE)
        self.assertEqual(fake.selected, [((), {"clear": True})])

    def test_a_setup_that_fails_says_why_and_leaves_the_selection_as_it_was(self):
        def setup(bone, start, end):
            raise RuntimeError("no camera rig\nsecond line")

        self.patch(camera, "setup", setup)
        fake = self.scene(existing=[self.BONE, "|a"], selection=["|a"])
        self.assertEqual(helpers.set_up_camera(self.BONE),
                         "camera not set up on camera_root: no camera rig")
        self.assertEqual(fake.selected, [((["|a"],), {"replace": True})])

    def test_a_failure_with_no_message_names_its_type(self):
        def setup(bone, start, end):
            raise KeyError()

        self.patch(camera, "setup", setup)
        self.scene(existing=[self.BONE])
        self.assertEqual(helpers.set_up_camera(self.BONE),
                         "camera not set up on camera_root: KeyError")


if __name__ == "__main__":
    unittest.main()

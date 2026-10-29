"""The Pose Library's Apply, the seams and refusals `test_poselib_apply` leaves out: a rig's rotate
nodes (`rotations_of`), the selection reads (`_selected`, `_targets`, `_loose`), the measure on a
skeleton, a card dropped on a character (`apply_onto`), the character just added (`_add`,
`_reselect`), a stored object found again (`_find_object`), the parts of a character left out of an
objects pose (`_not_characters`), a character card's own objects (`card_objects`), what Select objects
selects and every refusal of a Blend that does not start.

Each seam is rebound for the test and restored by cleanup; no Maya node is touched.
"""
import contextlib
import io
import unittest
from collections import OrderedDict

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya_rigs
from maya_poselib import apply as ap
from maya_poselib import keys, objects, rigsolve, scene
from tests.test_poselib_helpers import trs


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)

    def unrecorded(self):
        @contextlib.contextmanager
        def block():
            yield

        self.patch(ap, "_unrecorded", block)
        self.patch(ap, "_press", block)


def rig_ref(label="Manny [rig]", root="|A|Manny_Rig1:root", namespace="Manny_Rig1"):
    return scene.CharacterRef("rig", root, "the rig", label, "Manny_Rig", "Manny", namespace)


def skeleton_ref(label="Manny UE5 [skeleton]", root="|S|root"):
    return scene.CharacterRef("skeleton", root, None, label, "Manny", "Manny", "")


class AttrCmds(object):
    """`getAttr` of a dict of plugs (an attribute in `broken` raises), `ls` of selection and names,
    `objExists`, `select`."""

    def __init__(self, values=None, broken=(), selected=(), longs=None, existing=()):
        self.values = values or {}
        self.broken = set(broken)
        self.selected = list(selected)
        self.longs = longs or {}
        self.existing = set(existing)
        self.selects = []
        self.ls_calls = []

    def getAttr(self, plug):
        if plug in self.broken:
            raise RuntimeError("no such attribute")
        return self.values[plug]

    def ls(self, *names, **kwargs):
        self.ls_calls.append((names, kwargs))
        if kwargs.get("selection"):
            return list(self.selected)
        return self.longs.get(names[0]) if names else None

    def objExists(self, node):
        if node == "raises":
            raise RuntimeError("bad name")
        return node in self.existing

    def select(self, *nodes, **kwargs):
        self.selects.append((nodes, kwargs))


class RotationNodes(Patched):

    def test_a_node_holding_all_three_rotate_plugs_gives_them_and_its_rotate_order(self):
        values = OrderedDict((plug, 0.0) for plug in (
            "|a.rotateX", "|a.rotateY", "|a.rotateZ", "|a.translateX"))
        self.patch(ap, "cmds", AttrCmds({"|a.rotateOrder": 2}))
        self.assertEqual(ap.rotations_of(values),
                         {"|a": ("|a.rotateX", "|a.rotateY", "|a.rotateZ", 2)})

    def test_a_node_with_two_rotate_plugs_is_not_a_turn(self):
        values = {"|b.rotateX": 0.0, "|b.rotateY": 0.0}
        self.patch(ap, "cmds", AttrCmds({"|b.rotateOrder": 0}))
        self.assertEqual(ap.rotations_of(values), {})

    def test_a_node_whose_rotate_order_cannot_be_read_is_left_out(self):
        values = dict(("|c.rotate" + axis, 0.0) for axis in "XYZ")
        self.patch(ap, "cmds", AttrCmds(broken=["|c.rotateOrder"]))
        self.assertEqual(ap.rotations_of(values), {})

    def test_plugs_are_spelled_as_the_values_spell_them(self):
        values = dict(("|ns:d.rotate" + axis, 0.0) for axis in "XYZ")
        self.patch(ap, "cmds", AttrCmds({"|ns:d.rotateOrder": 5}))
        self.assertEqual(ap.rotations_of(values)["|ns:d"][3], 5)
        self.assertTrue(ap._has_rotate(values))
        self.assertFalse(ap._has_rotate({"|ns:d.translateX": 0.0}))
        self.assertFalse(ap._has_rotate({}))


class SelectionReads(Patched):

    def setUp(self):
        self.patch(scene, "dag_object", lambda item: None if item == "bad" else "|" + item.split(".")[0])

    def test_the_selected_transforms_are_long_paths_once_in_order(self):
        self.assertEqual(ap._selected(["b.vtx[1]", "a", "bad", "b"]), ["|b", "|a"])

    def test_mayas_own_selection_is_read_when_none_is_given(self):
        self.patch(ap, "cmds", AttrCmds(selected=["x", "y"]))
        self.assertEqual(ap._selected(None), ["|x", "|y"])
        self.assertEqual(ap.cmds.ls_calls, [((), {"selection": True, "long": True})])

    def test_the_bodies_and_the_objects_of_a_selection_are_scene_split_s(self):
        a = rig_ref()
        self.patch(scene, "split", lambda selection=None: ([a], ["|body"], [("|obj", None), ("|cam", a)]))
        self.assertEqual(ap._body_refs(["x"]), [a])
        self.assertEqual(ap._loose(["x"]), ["|obj", "|cam"])

    def test_the_loose_objects_of_mayas_selection_when_none_is_given(self):
        self.patch(ap, "cmds", AttrCmds(selected=["|obj"]))
        seen = []
        self.patch(scene, "split", lambda selection=None: seen.append(selection) or ([], [], []))
        self.assertEqual(ap._loose(None), [])
        self.assertEqual(seen, [["|obj"]])

    def test_a_node_name_is_its_long_path_or_itself(self):
        self.patch(ap, "cmds", AttrCmds(longs={"cube": ["|grp|cube"], "gone": []}))
        self.assertEqual(ap._long_node("cube"), "|grp|cube")
        self.assertEqual(ap._long_node("gone"), "gone")


class Targets(Patched):

    def setUp(self):
        self.a, self.b = rig_ref("A"), skeleton_ref("B")
        self.split = ([], [], [])
        self.every = []
        self.patch(scene, "split", lambda selection=None: self.split)
        self.patch(scene, "all_characters", lambda: self.every)

    def test_the_characters_the_selection_touches_are_the_targets(self):
        self.split = ([self.a], [], [])
        self.assertEqual(ap._targets(["|A|Main"]), ([self.a], ""))

    def test_a_selection_of_nothing_a_character_is_refused_not_redirected(self):
        self.every = [self.a]
        self.assertEqual(ap._targets(["|prop"]), ([], ap.NOT_A_CHARACTER))

    def test_nothing_selected_is_the_only_character_in_the_scene(self):
        self.every = [self.a]
        self.assertEqual(ap._targets([]), ([self.a], ""))

    def test_nothing_selected_and_no_character_in_the_scene_is_a_refusal(self):
        self.assertEqual(ap._targets([]), ([], ap.NO_CHARACTER))

    def test_nothing_selected_among_several_is_a_refusal_naming_them_or_the_cards_own(self):
        self.every = [self.a, self.b]
        targets, refusal = ap._targets([])
        self.assertEqual(targets, [])
        self.assertTrue(refusal.startswith("2 characters in the scene (Manny_Rig1, "))
        self.assertEqual(ap._targets([], prefer="Manny_Rig1"), ([self.a], ""))

    def test_mayas_own_selection_is_read_when_none_is_given(self):
        self.patch(ap, "cmds", AttrCmds(selected=[]))
        self.every = [self.a]
        self.assertEqual(ap._targets(None), ([self.a], ""))


class Measure(Patched):

    def bones(self, extra_root=True):
        out = {"root": {"path": "|root", "parent": None, "canonical": "root" if extra_root else None},
               "pelvis": {"path": "|root|pelvis", "parent": "root", "canonical": "pelvis"},
               "hand_l": {"path": "|root|pelvis|hand_l", "parent": "pelvis", "canonical": "hand_l"},
               "hand_r": {"path": "|root|pelvis|hand_r", "parent": "pelvis", "canonical": "hand_r"}}
        return out

    def extra(self, bones, wanted, members):
        return ap.Extra(wanted, members, bones, None)

    def scene_of(self, worlds):
        class Cmds(object):
            def objExists(self, path):
                return path in worlds

            def getAttr(self, plug):
                return list(worlds[plug.rsplit(".", 1)[0]])

        self.patch(ap, "cmds", Cmds())

    def test_nothing_to_measure_without_a_character_or_members(self):
        bones = self.bones()
        plan = ap.Plan(skeleton_ref(), {}, {}, [], {})
        self.assertIsNone(ap._measure(ap.Plan(None, {}, {}, [], {}), self.extra(bones, {}, ["pelvis"])))
        self.assertIsNone(ap._measure(plan, None))
        self.assertIsNone(ap._measure(plan, self.extra(bones, {}, [])))

    def test_a_rig_is_measured_by_the_rig_solver(self):
        seen = []
        self.patch(rigsolve, "measure", lambda rig, wanted, members, placed: seen.append(
            (rig, wanted, members, placed)) or (1.5, 2.5, "hand_l"))
        plan = ap.Plan(rig_ref(), {}, {}, [], {})
        extra = ap.Extra({"hand_l": "m"}, ["hand_l"], self.bones(), None, ("pelvis",))
        self.assertEqual(ap._measure(plan, extra), (1.5, 2.5, "hand_l"))
        self.assertEqual(seen, [("the rig", {"hand_l": "m"}, ["hand_l"], ("pelvis",))])

    def test_a_skeleton_is_measured_by_the_worst_member_s_angle_and_place(self):
        bones = self.bones()
        wanted = {"pelvis": trs((0, 96, 0)), "hand_l": trs((10, 100, 0), (0, 0, 20)),
                  "hand_r": trs((-30, 100, 0), (0, 0, 5))}
        self.scene_of({"|root|pelvis": trs((0, 96, 0)),
                       "|root|pelvis|hand_l": trs((10, 100, 0), (0, 0, 0)),
                       "|root|pelvis|hand_r": trs((-30, 100, 4), (0, 0, 5))})
        plan = ap.Plan(skeleton_ref(), {}, {}, [], {})
        deg, cm, leaf = ap._measure(plan, self.extra(bones, wanted, ["pelvis", "hand_l", "hand_r"]))
        self.assertAlmostEqual(deg, 20.0, 6)
        self.assertAlmostEqual(cm, 4.0, 6)
        self.assertEqual(leaf, "hand_l")

    def test_the_root_the_skipped_and_the_unwanted_are_not_measured(self):
        bones = self.bones()
        wanted = {"root": trs((100, 0, 0)), "pelvis": trs((0, 96, 0)), "hand_l": trs((100, 0, 0)),
                  "hand_r": trs((-30, 100, 0))}
        self.scene_of({"|root": trs(), "|root|pelvis": trs((0, 96, 0)),
                       "|root|pelvis|hand_l": trs(), "|root|pelvis|hand_r": trs((-30, 100, 0))})
        plan = ap.Plan(skeleton_ref(), {}, {}, [], {"hand_l": "driven"})
        members = ["root", "pelvis", "hand_l", "hand_r", "not_wanted"]
        deg, cm, leaf = ap._measure(plan, self.extra(bones, wanted, members))
        self.assertLess(deg, 1e-6)
        self.assertLess(cm, 1e-6)
        self.assertNotIn(leaf, ("root", "hand_l", "not_wanted"))

    def test_a_member_whose_joint_is_gone_is_not_measured(self):
        bones = self.bones()
        self.scene_of({})
        plan = ap.Plan(skeleton_ref(), {}, {}, [], {})
        extra = self.extra(bones, {"hand_l": trs((5, 5, 5))}, ["hand_l"])
        self.assertEqual(ap._measure(plan, extra), (0.0, 0.0, None))

    def test_the_seams_of_the_measure_are_the_rig_solver_s(self):
        self.patch(rigsolve, "switches", lambda: "switches")
        self.patch(rigsolve, "_fresh", lambda tweaks, skip: ("fresh", tweaks, skip))
        self.assertEqual(ap._switches(), "switches")
        self.assertEqual(ap._evaluated("T", ["s"]), ("fresh", "T", ["s"]))


class DroppedOnACharacter(Patched):

    DATA = {"name": "Fist", "bones": {"hand_l": {}}, "members": ["hand_l"]}

    def setUp(self):
        self.pressed = []
        self.patch(ap, "_apply_refs", lambda data, refs, mirror=False: self.pressed.append(
            (data, refs, mirror)) or (True, "pressed"))

    def test_an_objects_card_goes_onto_objects_not_onto_a_character(self):
        self.assertEqual(ap.apply_onto({"kind": "objects"}, "|root"), (False, ap.OBJECTS_ONTO))

    def test_no_card_or_a_card_without_bones_is_refused(self):
        self.assertEqual(ap.apply_onto(None, "|root"), (False, ap.NO_CARD))
        self.assertEqual(ap.apply_onto({"bones": {}}, "|root"), (False, ap.NO_BONES))

    def test_a_node_of_no_character_is_not_found(self):
        self.patch(scene, "character_of", lambda root: None)
        self.assertEqual(ap.apply_onto(self.DATA, "|prop"), (False, "no character at |prop"))
        self.assertEqual(ap.apply_onto(self.DATA, None), (False, "no character at nothing"))

    def test_the_card_is_pressed_onto_the_character_the_node_belongs_to(self):
        ref = rig_ref()
        self.patch(scene, "character_of", lambda root: ref if root == "|Manny|root" else None)
        self.assertEqual(ap.apply_onto(self.DATA, "|Manny|root", mirror=True), (True, "pressed"))
        self.assertEqual(self.pressed, [(self.DATA, [ref], True)])


class ObjectsAlone(Patched):

    DATA = {"name": "Fist", "objects": [{"name": "cam"}, {"name": "prop"}]}

    def setUp(self):
        self.unrecorded()
        self.layer = ("layer", "")
        self.entry = (ap.Plan(None, OrderedDict([("|cam.tx", 1.0)]), {}, [], {}), "extra")
        self.keyed = []
        self.patch(keys, "active_layer", lambda: self.layer)
        self.patch(keys, "quaternion_note", lambda layer: self.note)
        self.note = ""
        self.patch(ap, "card_objects", lambda data, loose, refs, only: (self.entry, []))
        self.patch(ap, "_frame", lambda: 12.0)

        def key_entries(entries, name, frame, layer, alpha=1.0, mirror=False):
            self.keyed.append((entries, name, frame, layer, alpha))
            return [ap.Result(name, "the objects", 1, "objects", None, frame, None, [], alpha, False)]

        self.patch(ap, "_key_entries", key_entries)

    def test_a_locked_layer_is_refused_before_anything_is_read(self):
        self.layer = (None, "the animation layer A is locked - unlock it or pick another")
        self.assertEqual(ap._objects_alone(self.DATA, ["|cam"]),
                         (False, "the animation layer A is locked - unlock it or pick another"))
        self.assertEqual(self.keyed, [])

    def test_a_selection_matching_none_of_the_card_s_objects_is_refused_by_count(self):
        self.entry = None
        self.assertEqual(ap._objects_alone(self.DATA, ["|other"]),
                         (False, ap.SELECTION_UNMATCHED % (2, "s", 2)))
        self.assertEqual(ap._objects_alone({"objects": [{"name": "cam"}]}, ["|other"])[1],
                         ap.SELECTION_UNMATCHED % (1, "", 1))

    def test_a_quaternion_layer_refuses_objects_that_turn(self):
        self.note = "the layer accumulates quaternions"
        self.entry[0].values["|cam.rotateY"] = 3.0
        self.assertEqual(ap._objects_alone(self.DATA, ["|cam"]), (False, self.note))
        self.assertEqual(self.keyed, [])

    def test_a_quaternion_layer_does_not_refuse_objects_that_only_move(self):
        self.note = "the layer accumulates quaternions"
        ok, _text = ap._objects_alone(self.DATA, ["|cam"])
        self.assertTrue(ok)

    def test_the_objects_are_keyed_alone_and_the_line_says_no_character_was_selected(self):
        ok, text = ap._objects_alone(self.DATA, ["|cam"], alpha=0.5)
        self.assertTrue(ok)
        self.assertEqual(self.keyed[0][1:], ("Fist", 12.0, "layer", 0.5))
        self.assertEqual(self.entry[0].notes[0], ap.OBJECTS_ALONE)
        self.assertIn("Fist at 50 % onto the objects: 1 object keyed", text)


class AddedCharacter(Patched):

    def test_the_animator_s_selection_that_still_exists_is_selected_again(self):
        self.unrecorded()
        fake = AttrCmds(existing=["|a", "|b"])
        self.patch(ap, "cmds", fake)
        ap._reselect(["|a", "|gone", "raises", "|b"])
        self.assertEqual(fake.selects, [((["|a", "|b"],), {"replace": True, "noExpand": True})])

    def test_an_empty_selection_is_cleared(self):
        self.unrecorded()
        fake = AttrCmds()
        self.patch(ap, "cmds", fake)
        ap._reselect(["|gone"])
        ap._reselect(None)
        self.assertEqual(fake.selects, [((), {"clear": True})] * 2)

    def test_a_uuid_is_its_long_path_or_none(self):
        self.patch(ap, "cmds", AttrCmds(longs={"U1": ["|grp|node"], "U2": []}))
        self.assertEqual(ap._long("U1"), "|grp|node")
        self.assertIsNone(ap._long("U2"))
        self.assertIsNone(ap._long(""))
        self.assertIsNone(ap._long(None))

    def test_every_nodes_uuid_is_asked_with_the_names_first(self):
        calls = []

        class Cmds(object):
            def ls(self, *names, **kwargs):
                calls.append((names, kwargs))
                return ["U1", "U2", "U1"] if kwargs.get("uuid") else ["a", "b"]

        self.patch(ap, "cmds", Cmds())
        self.assertEqual(ap._scene_uuids(), {"U1", "U2"})
        self.assertEqual(calls[1], ((["a", "b"],), {"uuid": True}))

    def test_a_rig_is_added_and_its_game_skeleton_root_is_the_new_character(self):
        from maya_overrig import builder  # noqa: F401
        from maya_scenesetup import catalog, character
        from maya_uebridge import rigimport
        entry = catalog.character_by_key("Manny_Rig")
        rig = maya_rigs.Rig("Manny_Rig3", None, None, "|G", "|G|Manny_Rig3:root", None)
        added = []
        self.patch(maya_rigs, "rigs", lambda: [])
        self.patch(character, "add_character", lambda e, at=None: added.append((e, at)) or "added")
        self.patch(rigimport, "fresh_rig", lambda before, after: rig)
        self.assertEqual(ap._add(entry, (10.4, 0.0, 20.6)),
                         ("|G|Manny_Rig3:root", "a new Manny [rig] Manny_Rig3 at floor (10, 21)"))
        self.assertEqual(added, [(entry, (10.4, 0.0, 20.6))])

    def test_a_rig_that_did_not_arrive_is_said(self):
        from maya_scenesetup import catalog, character
        from maya_uebridge import rigimport
        entry = catalog.character_by_key("Manny_Rig")
        self.patch(maya_rigs, "rigs", lambda: [])
        self.patch(character, "add_character", lambda e, at=None: "the file is missing")
        self.patch(rigimport, "fresh_rig", lambda before, after: None)
        self.assertEqual(ap._add(entry, (0, 0, 0)),
                         (None, "Manny [rig] was not added: the file is missing"))

    def test_a_skeleton_is_added_and_the_new_root_found_by_a_diff(self):
        from maya_overrig import builder
        from maya_scenesetup import catalog, character
        entry = catalog.character_by_key("Manny")
        roots = iter([["|old"], ["|old", "|new|root"]])
        self.patch(builder, "character_roots", lambda: next(roots))
        self.patch(character, "add_character", lambda e, at=None: "added")
        self.patch(character, "new_root", lambda before, after: after[-1])
        self.assertEqual(ap._add(entry, (3.0, 0.0, -4.0)),
                         ("|new|root", "a new Manny UE5 [skeleton] root at floor (3, -4)"))

    def test_a_skeleton_that_did_not_arrive_is_said(self):
        from maya_overrig import builder
        from maya_scenesetup import catalog, character
        entry = catalog.character_by_key("Manny")
        self.patch(builder, "character_roots", lambda: [])
        self.patch(character, "add_character", lambda e, at=None: "no scene")
        self.patch(character, "new_root", lambda before, after: None)
        self.assertEqual(ap._add(entry, (0, 0, 0)), (None, "Manny UE5 [skeleton] was not added: no scene"))


class RebuildCmds(object):
    """The scene a rebuilt skeleton is made in: joints named `built`, a cube, a skin, the root's
    place and every call logged."""

    def __init__(self, built, root_at=(40.0, 0.0, -25.0)):
        self.built = built
        self.root_at = root_at
        self.log = []
        self.uuid_of = {}

    def ls(self, *names, **kwargs):
        if kwargs.get("uuid"):
            return ["U-%s" % names[0]]
        if kwargs.get("type") == "joint":
            return list(self.built)
        return []

    def polyCube(self, name=None, constructionHistory=False):
        self.log.append(("cube", name, constructionHistory))
        return ["|" + name.strip(":")]

    def skinCluster(self, nodes, toSelectedBones=False, name=None):
        self.log.append(("skin", list(nodes), name))

    def addAttr(self, node, **kwargs):
        self.log.append(("addAttr", node, kwargs["longName"]))

    def setAttr(self, plug, value):
        self.log.append(("setAttr", plug, value))

    def xform(self, node, query=False, worldSpace=False, translation=False):
        return list(self.root_at)

    def move(self, dx, dy, dz, node, relative=False, worldSpace=False):
        self.log.append(("move", dx, dy, dz, node))


class RebuildSkeleton(Patched):
    """A native card's skeleton rebuilt at its rest as a character (the module docstring)."""

    JOINTS = [{"name": "root"}, {"name": "pelvis"}]
    PATHS = ["|pose_Sweep:root", "|pose_Sweep:root|pose_Sweep:pelvis"]

    def setUp(self):
        from maya_scenesetup import chargroup, character, deletion
        from maya_scenetabs import scope
        from maya_uebridge import formats
        self.unrecorded()
        self.fake = RebuildCmds(self.PATHS)
        self.patch(ap, "cmds", self.fake)
        self.patch(ap, "rebuild_joints", lambda bones: self.JOINTS)
        self.patch(ap, "_scene_uuids",
                   lambda: set(["old"]) if not self.fake.log else set(["old", "n1", "n2"]))
        self.patch(ap, "_long", lambda uuid: "|pose_Sweep:" + uuid)
        self.taken = []
        self.patch(character, "existing_namespaces", lambda: self.taken)
        self.built = []
        self.patch(formats, "build", lambda namespace, joints, parents, extras, set_timeline=True:
                   self.built.append((namespace, [j["name"] for j in joints], set_timeline)))
        self.grouped = []
        self.patch(chargroup, "make", lambda namespace, label, root, tops: self.grouped.append(
            (namespace, label, root, tops)))
        self.recorded = []
        self.patch(deletion, "record_import", lambda root, nodes, label: self.recorded.append(
            (root, sorted(nodes), label)))
        self.patch(scope, "home_namespace", lambda namespace, cmds_=None: "tab_a:" + namespace)
        self.patch(scope, "relative", lambda name, cmds_=None: name.split(":", 1)[1])
        self.group_error = None
        self.patch(ap.traceback, "print_exc", lambda: None)

    def rebuild(self, point=(100.0, 0.0, 50.0), name="Sweep"):
        return ap._rebuild({"name": name, "bones": {"root": {}}}, point)

    def test_a_card_with_no_joint_built_is_not_added(self):
        self.fake.built = []
        self.assertEqual(self.rebuild(), (None, "Sweep was not added: no joint built"))

    def test_a_card_with_no_name_is_called_the_pose_s_skeleton_in_the_refusal(self):
        self.fake.built = []
        self.assertEqual(ap._rebuild({"bones": {}}, (0, 0, 0))[1],
                         "the pose's skeleton was not added: no joint built")

    def test_the_skeleton_is_built_in_a_free_namespace_named_for_the_card(self):
        self.rebuild()
        self.assertEqual(self.built, [("pose_Sweep", ["root", "pelvis"], False)])
        self.assertEqual(self.fake.log[0], ("cube", ":pose_Sweep:restBind", False))

    def test_a_namespace_already_taken_is_numbered(self):
        self.taken = ["pose_Sweep"]
        self.rebuild()
        self.assertEqual(self.built[0][0], "pose_Sweep1")

    def test_a_card_name_maya_would_refuse_is_made_legal_first(self):
        self.rebuild(name="Sweep: left")
        self.assertTrue(self.built[0][0].startswith("pose_Sweep_"))
        self.assertNotIn(" ", self.built[0][0])

    def test_a_cube_is_skinned_to_the_joints_marked_and_hidden_so_the_rest_stays_the_bind(self):
        self.rebuild()
        skin = ("skin", self.PATHS + ["|pose_Sweep:restBind"], ":pose_Sweep:restSkin")
        self.assertIn(skin, self.fake.log)
        self.assertIn(("addAttr", "|pose_Sweep:restBind", ap.REST_MARK), self.fake.log)
        self.assertIn(("setAttr", "|pose_Sweep:restBind.visibility", False), self.fake.log)

    def test_the_root_is_moved_to_stand_on_the_point_whatever_the_card_s_rest(self):
        self.rebuild(point=(100.0, 7.0, 50.0))
        moves = [entry for entry in self.fake.log if entry[0] == "move"]
        self.assertEqual(moves, [("move", 60.0, 0.0, 75.0, "|pose_Sweep:U-" + self.PATHS[0])])

    def test_it_is_made_a_character_grouped_and_recorded_for_delete(self):
        root, _line = self.rebuild()
        self.assertEqual(root, "|pose_Sweep:U-" + self.PATHS[0])
        self.assertEqual(len(self.grouped), 1)
        namespace, label, group_root, tops = self.grouped[0]
        self.assertEqual((namespace, label), ("pose_Sweep", "Sweep [own skeleton]"))
        self.assertEqual(tops, [group_root, "|pose_Sweep:U-|pose_Sweep:restBind"])
        self.assertEqual(self.recorded, [(root, ["n1", "n2"], "Sweep [own skeleton]")])

    def test_the_line_names_the_namespace_as_the_active_tab_shows_it_and_the_floor_point(self):
        _root, line = self.rebuild(point=(100.4, 0.0, 49.6))
        self.assertEqual(line, "pose_Sweep rebuilt (bones only) at floor (100, 50)")

    def test_a_group_that_cannot_be_made_is_said_and_the_rebuild_stands(self):
        from maya_scenesetup import chargroup

        def broken(namespace, label, root, tops):
            raise RuntimeError("no layer\nsecond line")

        self.patch(chargroup, "make", broken)
        root, line = self.rebuild()
        self.assertIsNotNone(root)
        self.assertEqual(line, "pose_Sweep rebuilt (bones only) at floor (100, 50)"
                               " - no character group (no layer) - its parts stand at world level")

    def test_a_record_that_cannot_be_made_does_not_break_the_rebuild(self):
        from maya_scenesetup import deletion

        def broken(root, nodes, label):
            raise RuntimeError("no record")

        self.patch(deletion, "record_import", broken)
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            root, line = self.rebuild()
        self.assertIsNotNone(root)
        self.assertTrue(line.startswith("pose_Sweep rebuilt"))
        self.assertIn("no record for Delete (no record)", printed.getvalue())

    def test_a_tab_that_cannot_take_the_namespace_leaves_it_where_it_is(self):
        from maya_scenetabs import scope

        def broken(namespace, cmds_=None):
            raise RuntimeError("no tab")

        self.patch(scope, "home_namespace", broken)
        root, line = self.rebuild()
        self.assertIsNotNone(root)
        self.assertTrue(line.startswith("pose_Sweep rebuilt"))


class StoredObjects(Patched):

    def test_a_stored_object_is_found_by_its_exact_path_when_that_names_one_node(self):
        self.patch(ap, "cmds", AttrCmds(longs={"|cam": ["|cam"]}))
        self.assertEqual(ap._find_object({"path": "|cam", "name": "cam"}), "|cam")

    def test_else_by_the_one_transform_carrying_its_leaf_name(self):
        fake = AttrCmds(longs={"|gone": [], "cam": ["|shot:cam"]})
        self.patch(ap, "cmds", fake)
        self.assertEqual(ap._find_object({"path": "|gone", "name": "cam"}), "|shot:cam")
        self.assertEqual(fake.ls_calls[-1], (("cam",), {"recursive": True, "long": True,
                                                        "type": "transform"}))

    def test_a_path_naming_two_nodes_falls_to_the_name(self):
        self.patch(ap, "cmds", AttrCmds(longs={"|cam": ["|a|cam", "|b|cam"], "cam": ["|c|cam"]}))
        self.assertEqual(ap._find_object({"path": "|cam", "name": "cam"}), "|c|cam")

    def test_several_or_none_of_that_name_is_none(self):
        self.patch(ap, "cmds", AttrCmds(longs={"cam": ["|a|cam", "|b|cam"]}))
        self.assertIsNone(ap._find_object({"name": "cam"}))
        self.assertIsNone(ap._find_object({"name": "other"}))
        self.assertIsNone(ap._find_object({}))


class CharacterPartsLeftOut(Patched):

    def setUp(self):
        self.a = rig_ref()
        self.b = skeleton_ref()
        self.resolved = []
        self.body = set()
        self.patch(scene, "resolve", lambda paths: self.resolved)
        self.patch(scene, "is_body", lambda path, ref: path in self.body)

    def test_nothing_selected_leaves_nothing_out(self):
        self.assertEqual(ap._not_characters([]), ([], ""))

    def test_objects_are_kept_and_nothing_is_said(self):
        self.resolved = [("|prop", None), ("|cam", self.a)]
        self.assertEqual(ap._not_characters(["|prop", "|cam"]), (["|prop", "|cam"], ""))

    def test_one_part_of_a_character_is_left_out_and_named(self):
        self.resolved = [("|prop", None), ("|A|Manny_Rig1:Main", self.a)]
        self.body.add("|A|Manny_Rig1:Main")
        self.assertEqual(ap._not_characters(["x"]), (["|prop"], "Main is part of Manny_Rig1"))

    def test_several_parts_are_counted_by_character(self):
        self.resolved = [("|A|Manny_Rig1:Main", self.a), ("|A|Manny_Rig1:FKWrist_L", self.a),
                         ("|S|root|hand", self.b)]
        self.body.update(["|A|Manny_Rig1:Main", "|A|Manny_Rig1:FKWrist_L", "|S|root|hand"])
        loose, note = ap._not_characters(["x"])
        self.assertEqual(loose, [])
        self.assertTrue(note.startswith("3 selected are parts of Manny_Rig1, Manny UE5 [skeleton]"))


class CardObjects(Patched):

    STORED = [{"name": "camera1", "path": "|camera1"}, {"name": "SceneSetup_camera", "own": True},
              {"name": "prop", "path": "|prop"}]

    def setUp(self):
        self.found = {}
        self.free_all = True
        self.matched_entries = []
        self.patch(objects, "found_for", lambda stored, refs, only: self.found)
        self.patch(ap, "_not_characters",
                   lambda paths: (list(paths) if self.free_all else [], ""))

        def values_entry(matched, label_nodes=None):
            self.matched_entries.append(matched)
            return ap.Plan(None, {}, {}, ["entry note"], {}), "extra"

        self.patch(ap, "_values_entry", values_entry)

    def test_a_card_with_no_objects_has_no_entry(self):
        self.assertEqual(ap.card_objects({"objects": []}, ["|x"], []), (None, []))
        self.assertEqual(ap.card_objects(None, [], []), (None, []))

    def test_nothing_matched_gives_no_entry_and_the_objects_not_found_are_named(self):
        entry, notes = ap.card_objects({"objects": self.STORED}, [], [])
        self.assertIsNone(entry)
        self.assertEqual(notes, ["not in the scene: camera1, SceneSetup_camera, prop"])

    def test_with_selected_only_the_unfound_are_not_said(self):
        entry, notes = ap.card_objects({"objects": self.STORED}, [], [], only=True)
        self.assertEqual((entry, notes), (None, []))

    def test_the_selected_are_paired_first_and_the_scene_answers_the_rest(self):
        self.found = {2: ["|prop"]}
        entry, notes = ap.card_objects({"objects": self.STORED}, ["|shot:camera1"], [])
        plan, _extra = entry
        self.assertEqual([(r["name"], p) for r, p in self.matched_entries[0]],
                         [("camera1", "|shot:camera1"), ("prop", "|prop")])
        self.assertEqual(plan.notes, ["entry note", "not in the scene: SceneSetup_camera"])
        self.assertEqual(notes, [])

    def test_a_found_object_that_is_part_of_a_character_is_not_taken(self):
        self.found = {2: ["|prop"]}
        self.free_all = False
        entry, _notes = ap.card_objects({"objects": self.STORED}, [], [])
        self.assertIsNone(entry)

    def test_objects_paired_by_order_say_so_first(self):
        stored = [{"name": "a"}, {"name": "b"}]
        entry, _notes = ap.card_objects({"objects": stored}, ["|x:one", "|x:two"], [], only=True)
        self.assertEqual(entry[0].notes[0], ap.BY_ORDER)


class SelectObjects(Patched):

    DATA = {"name": "Fist", "bones": {"hand_l": {}}, "members": ["hand_l"], "keep": None}

    def setUp(self):
        self.fake = AttrCmds()
        self.patch(ap, "cmds", self.fake)
        self.refs = [rig_ref()]
        self.patch(ap, "_targets", lambda selection, prefer=None: (self.refs, ""))
        self.bones = {"root": {"path": "|root", "parent": None, "canonical": "root"},
                      "hand_l": {"path": "|root|hand_l", "parent": "root", "canonical": "hand_l"}}
        self.patch(scene, "skeleton", lambda ref: (self.bones, "ue"))
        self.patch(ap, "_transform_of", lambda node: node)
        self.patch(ap.pm, "pairs", lambda source, bones: {"hand_l": "hand_l"})
        self.patch(ap.pm, "with_torso", lambda source, members: members)
        self.patch(ap.lower, "target_keep", lambda keep, pairs, bones: [])
        self.patch(rigsolve, "controls_for", lambda rig, members: ["|ctrl_%s" % m for m in members])
        self.patch(ap, "card_objects", lambda data, loose, refs: (None, []))

    def test_no_card_is_refused(self):
        self.assertEqual(ap.select_objects(None), (False, ap.NO_CARD))
        self.assertEqual(ap.select_objects({"bones": {}}), (False, ap.NO_BONES))

    def test_the_targets_refusal_is_the_answer(self):
        self.patch(ap, "_targets", lambda selection, prefer=None: ([], "no character"))
        self.assertEqual(ap.select_objects(self.DATA), (False, "no character"))

    def test_a_rig_selects_the_controls_that_key_the_members(self):
        self.assertEqual(ap.select_objects(self.DATA), (True, "Selected 1 control on Manny_Rig1"))
        self.assertEqual(self.fake.selects, [((["|ctrl_hand_l"],), {"replace": True})])

    def test_a_skeleton_selects_its_member_joints_the_root_aside(self):
        self.refs = [skeleton_ref()]
        self.patch(ap.pm, "pairs", lambda source, bones: {"hand_l": "hand_l", "root": "root"})
        data = dict(self.DATA, members=["hand_l", "root"])
        ok, text = ap.select_objects(data)
        self.assertTrue(ok)
        self.assertEqual(self.fake.selects, [((["|root|hand_l"],), {"replace": True})])
        self.assertEqual(text, "Selected 1 joint on Manny UE5 [skeleton] (root)")

    def test_a_skeleton_with_no_root_of_its_own_selects_its_top_joint_too(self):
        self.refs = [skeleton_ref()]
        self.bones["root"]["canonical"] = "pelvis"
        self.patch(ap.pm, "pairs", lambda source, bones: {"hand_l": "hand_l", "root": "root"})
        _ok, text = ap.select_objects(dict(self.DATA, members=["hand_l", "root"]))
        self.assertEqual(self.fake.selects, [((["|root", "|root|hand_l"],), {"replace": True})])
        self.assertEqual(text, "Selected 2 joints on Manny UE5 [skeleton] (root)")

    def test_the_card_s_namespace_is_the_character_to_prefer(self):
        asked = []
        self.patch(ap, "_targets", lambda selection, prefer=None: asked.append(prefer) or (self.refs, ""))
        ap.select_objects(dict(self.DATA, character={"namespace": "Manny_Rig7"}))
        self.assertEqual(asked, ["Manny_Rig7"])

    def test_the_objects_the_card_keys_are_selected_beside_the_controls(self):
        entry = (ap.Plan(None, OrderedDict([("|cam|camShape.focalLength", 35.0)]), {}, [], {}), "extra")
        self.patch(ap, "card_objects", lambda data, loose, refs: (entry, []))
        self.patch(ap, "_transform_of", lambda node: "|cam" if node.endswith("camShape") else node)
        _ok, text = ap.select_objects(self.DATA)
        self.assertEqual(self.fake.selects[0][0], (["|ctrl_hand_l", "|cam"],))
        self.assertEqual(text, "Selected 2 controls on Manny_Rig1")

    def test_nothing_of_the_pose_on_the_character_is_said(self):
        self.patch(rigsolve, "controls_for", lambda rig, members: [])
        self.assertEqual(ap.select_objects(self.DATA), (False, "nothing of the pose on Manny_Rig1"))
        self.assertEqual(self.fake.selects, [])

    def test_a_rig_and_a_skeleton_together_are_nodes(self):
        self.refs = [rig_ref(), skeleton_ref()]
        _ok, text = ap.select_objects(self.DATA)
        self.assertTrue(text.startswith("Selected 2 nodes on Manny_Rig1, "))

    def test_an_objects_card_selects_the_objects_it_would_key(self):
        entry = (ap.Plan(None, OrderedDict([("|cam.tx", 1.0), ("|cam.ty", 2.0), ("|prop.tx", 3.0)]),
                         {}, [], {}),
                 ap.Extra(None, None, None, "2 objects"))
        self.patch(ap, "_objects_entry", lambda data, selection: (entry, ""))
        self.patch(ap, "_transform_of", lambda node: node)
        ok, text = ap.select_objects({"kind": "objects", "objects": [{}]})
        self.assertTrue(ok)
        self.assertEqual(self.fake.selects, [((["|cam", "|prop"],), {"replace": True})])
        self.assertEqual(text, "Selected 2 objects on 2 objects")

    def test_an_objects_card_with_one_object_says_object(self):
        entry = (ap.Plan(None, OrderedDict([("|cam.tx", 1.0)]), {}, [], {}),
                 ap.Extra(None, None, None, "1 object"))
        self.patch(ap, "_objects_entry", lambda data, selection: (entry, ""))
        self.patch(ap, "_transform_of", lambda node: node)
        self.assertEqual(ap.select_objects({"kind": "objects"}), (True, "Selected 1 object on 1 object"))

    def test_an_objects_card_that_finds_nothing_is_refused_as_the_press_would(self):
        refusal = "none of the pose's 1 object is in the scene"
        self.patch(ap, "_objects_entry", lambda data, selection: (None, refusal))
        self.assertEqual(ap.select_objects({"kind": "objects"}),
                         (False, "none of the pose's 1 object is in the scene"))

    def test_an_objects_card_with_no_plugs_has_nothing_to_select(self):
        entry = (ap.Plan(None, OrderedDict(), {}, [], {}), ap.Extra(None, None, None, "0 objects"))
        self.patch(ap, "_objects_entry", lambda data, selection: (entry, ""))
        self.assertEqual(ap.select_objects({"kind": "objects"}),
                         (False, "nothing of the pose on 0 objects"))


class ShapeTransform(Patched):

    def test_a_shape_counts_as_its_transform_and_a_failing_count_as_the_node(self):
        class Cmds(object):
            def objectType(self, node, isAType=None):
                if node == "boom":
                    raise RuntimeError("gone")
                return node.endswith("Shape")

            def listRelatives(self, node, parent=False, fullPath=False):
                return ["|cam"] if node == "|cam|camShape" else None

        self.patch(ap, "cmds", Cmds())
        self.assertEqual(ap._transform_of("|cam|camShape"), "|cam")
        self.assertEqual(ap._transform_of("|lonelyShape"), "|lonelyShape")
        self.assertEqual(ap._transform_of("|cam"), "|cam")
        self.assertEqual(ap._owner("|cam|camShape"), "|cam")
        self.assertEqual(ap._owner("boom"), "boom")


class BlendRefusals(Patched):
    """A session that cannot start says why and has changed nothing."""

    DATA = {"name": "Fist", "bones": {"hand_l": {}}, "members": ["hand_l"],
            "objects": [{"name": "cam"}]}

    def setUp(self):
        self.unrecorded()
        self.layer = (("layer",), "")
        self.note = ""
        self.patch(keys, "active_layer", lambda: self.layer)
        self.patch(keys, "quaternion_note", lambda layer: self.note)
        self.patch(ap, "_frame", lambda: 1.0)
        self.patch(ap, "cmds", AttrCmds())
        self.blend = ap.Blend()

    def test_a_session_already_running_is_cancelled_first(self):
        cancelled = []
        self.blend.entries = [("plan", "extra")]
        self.blend.cancel = lambda: cancelled.append(True) or self.blend._clear()
        self.assertEqual(self.blend.start(None), ap.NO_CARD)
        self.assertEqual(cancelled, [True])
        self.assertFalse(self.blend.active())

    def test_a_locked_layer_is_the_refusal(self):
        self.layer = (None, "the animation layer A is locked - unlock it or pick another")
        self.assertEqual(self.blend.start(self.DATA), self.layer[1])

    def test_an_objects_card_that_finds_nothing_says_so(self):
        self.patch(ap, "_objects_entry", lambda data, selection: (None, "no objects here"))
        self.assertEqual(self.blend.start({"kind": "objects", "objects": [{}]}), "no objects here")

    def test_an_objects_card_that_turns_is_refused_on_a_quaternion_layer(self):
        entry = (ap.Plan(None, {"|cam.rotateY": 1.0}, {}, [], {}), "extra")
        self.patch(ap, "_objects_entry", lambda data, selection: (entry, ""))
        self.note = "the layer accumulates quaternions"
        self.assertEqual(self.blend.start({"kind": "objects", "objects": [{}]}), self.note)
        self.assertFalse(self.blend.active())

    def test_a_card_without_bones_or_on_a_quaternion_layer_is_refused(self):
        self.assertEqual(self.blend.start({"bones": {}}), ap.NO_BONES)
        self.note = "the layer accumulates quaternions"
        self.assertEqual(self.blend.start(self.DATA), self.note)

    def test_objects_alone_that_match_nothing_are_refused(self):
        self.patch(ap, "_loose", lambda selection: ["|other"])
        self.patch(ap, "_body_refs", lambda selection: [])
        self.patch(ap, "card_objects", lambda data, loose, refs, only: (None, []))
        self.assertEqual(self.blend.start(self.DATA, selection=["|other"]),
                         ap.NOTHING % "the selection matches none of the card's objects")

    def test_targets_that_are_refused_are_the_refusal(self):
        self.patch(ap, "_loose", lambda selection: [])
        self.patch(ap, "_targets", lambda selection: ([], ap.NO_CHARACTER))
        self.assertEqual(self.blend.start(self.DATA, selection=[]), ap.NO_CHARACTER)

    def test_a_plan_with_no_channel_to_key_names_why(self):
        self.patch(ap, "_loose", lambda selection: [])
        self.patch(ap, "_targets", lambda selection: ([rig_ref()], ""))
        plan = ap.Plan(rig_ref(), OrderedDict(), {}, ["no hand_l on Manny_Rig1"], {})
        self.patch(ap, "_plan", lambda data, ref, mirror=False, **kw: (plan, "extra"))
        self.patch(ap, "_with_objects", lambda entries, data, loose, refs, only, mirror: entries)
        self.assertEqual(self.blend.start(self.DATA, selection=["|A|Main"]),
                         ap.NOTHING % "no hand_l on Manny_Rig1")
        self.assertFalse(self.blend.active())

    def test_a_plan_with_no_channel_and_no_note_says_so_plainly(self):
        self.patch(ap, "_loose", lambda selection: [])
        self.patch(ap, "_targets", lambda selection: ([rig_ref()], ""))
        plan = ap.Plan(rig_ref(), OrderedDict(), {}, [], {})
        self.patch(ap, "_plan", lambda data, ref, mirror=False, **kw: (plan, "extra"))
        self.patch(ap, "_with_objects", lambda entries, data, loose, refs, only, mirror: entries)
        self.assertEqual(self.blend.start(self.DATA, selection=["|A|Main"]),
                         ap.NOTHING % "no channel the pose can turn")

    def test_selected_only_asks_for_the_selected_nodes(self):
        asked = []
        self.patch(ap, "_loose", lambda selection: [])
        self.patch(ap, "_targets", lambda selection: ([rig_ref()], ""))
        self.patch(ap, "selected_nodes", lambda selection: asked.append(selection) or frozenset(["|n"]))
        plan = ap.Plan(rig_ref(), OrderedDict(), {}, [], {})
        kwargs = []
        self.patch(ap, "_plan", lambda data, ref, mirror=False, **kw: kwargs.append(kw) or (plan, "extra"))
        self.patch(ap, "_with_objects", lambda entries, data, loose, refs, only, mirror: entries)
        self.blend.start(self.DATA, selection=["|A|Main"], only=True)
        self.assertEqual(asked, [["|A|Main"]])
        self.assertEqual(kwargs, [{"only": frozenset(["|n"])}])

    def test_mayas_selection_is_read_when_none_is_given(self):
        self.patch(ap, "cmds", AttrCmds(selected=["|A|Main"]))
        seen = []
        self.patch(ap, "_loose", lambda selection: seen.append(selection) or [])
        self.patch(ap, "_targets", lambda selection: ([], ap.NO_CHARACTER))
        self.blend.start(self.DATA)
        self.assertEqual(seen, [["|A|Main"]])

    def test_a_blend_that_is_not_running_previews_nothing_and_keys_nothing(self):
        self.assertFalse(self.blend.active())
        self.assertIsNone(self.blend.set(0.5))
        self.assertEqual(self.blend.alpha, 0.0)
        self.assertEqual(self.blend.finish(), ap.NO_BLEND)


class FloorDrop(Patched):
    """A card dropped on an empty floor: its source added (a catalog row) or rebuilt (a native
    skeleton), the selection put back, the pose pressed onto it."""

    BONES = {"root": {}}

    def setUp(self):
        self.layer = (("layer",), "")
        self.note = ""
        self.calls = []
        self.patch(keys, "active_layer", lambda: self.layer)
        self.patch(keys, "quaternion_note", lambda layer: self.note)
        self.patch(ap, "cmds", AttrCmds(selected=["|sel"]))
        self.patch(ap, "_add",
                   lambda entry, point: self.calls.append(("add", entry.key, point)) or self.added)
        self.patch(ap, "_rebuild", lambda data, point: self.calls.append(("rebuild", point)) or self.added)
        self.patch(ap, "_reselect", lambda selection: self.calls.append(("reselect", selection)))
        self.patch(ap, "apply_onto", lambda data, root, mirror=False: self.calls.append(
            ("onto", root, mirror)) or (True, "posed"))
        self.added = ("|new|root", "a new Manny [rig] Manny_Rig2 at floor (1, 2)")

    def card(self, key="Manny_Rig", **kwargs):
        data = {"name": "Fist", "character": {"key": key} if key else {}, "bones": self.BONES}
        data.update(kwargs)
        return data

    def test_an_objects_card_or_no_card_is_not_dropped_on_a_floor(self):
        self.assertEqual(ap.drop_floor({"kind": "objects"}, (0, 0, 0)), (False, ap.OBJECTS_ONTO))
        self.assertEqual(ap.drop_floor(None, (0, 0, 0)), (False, ap.NO_CARD))

    def test_a_card_with_neither_a_row_of_ours_nor_bones_has_no_source(self):
        self.assertEqual(ap.drop_floor(self.card(key=None, bones={}), (0, 0, 0)), (False, ap.NO_SOURCE))
        self.assertEqual(ap.drop_floor(self.card(key="Not_A_Row", bones={}), (0, 0, 0)),
                         (False, ap.NO_SOURCE))

    def test_a_card_with_a_row_and_no_bones_holds_no_bones(self):
        self.assertEqual(ap.drop_floor(self.card(bones={}), (0, 0, 0)), (False, ap.NO_BONES))
        self.assertEqual(self.calls, [])

    def test_a_locked_layer_or_a_quaternion_layer_is_refused_before_anything_is_added(self):
        self.layer = (None, "the animation layer A is locked - unlock it or pick another")
        self.assertEqual(ap.drop_floor(self.card(), (0, 0, 0)), (False, self.layer[1]))
        self.layer = (("layer",), "")
        self.note = "the layer accumulates quaternions"
        self.assertEqual(ap.drop_floor(self.card(), (0, 0, 0)), (False, self.note))
        self.assertEqual(self.calls, [])

    def test_a_catalog_card_adds_its_character_then_presses_the_pose_onto_it(self):
        ok, text = ap.drop_floor(self.card(), (1.0, 0.0, 2.0), mirror=True)
        self.assertTrue(ok)
        self.assertEqual(text, "a new Manny [rig] Manny_Rig2 at floor (1, 2) | posed")
        self.assertEqual(self.calls, [("add", "Manny_Rig", (1.0, 0.0, 2.0)), ("reselect", ["|sel"]),
                                      ("onto", "|new|root", True)])

    def test_a_native_card_is_rebuilt_from_its_bones(self):
        ok, _text = ap.drop_floor(self.card(key=None), (1.0, 0.0, 2.0))
        self.assertTrue(ok)
        self.assertEqual(self.calls[0], ("rebuild", (1.0, 0.0, 2.0)))

    def test_a_character_that_could_not_be_added_is_the_answer_and_nothing_is_pressed(self):
        self.added = (None, "Manny [rig] was not added: no file")
        self.assertEqual(ap.drop_floor(self.card(), (0, 0, 0)),
                         (False, "Manny [rig] was not added: no file"))
        self.assertEqual([call[0] for call in self.calls], ["add"])

    def test_an_animation_s_own_press_replaces_the_pose_press(self):
        pressed = []
        _ok, text = ap.drop_floor(self.card(), (0, 0, 0),
                                 onto=lambda root: pressed.append(root) or (True, "pasted"))
        self.assertEqual(text, "a new Manny [rig] Manny_Rig2 at floor (1, 2) | pasted")
        self.assertEqual(pressed, ["|new|root"])
        self.assertNotIn("onto", [call[0] for call in self.calls])


class WithObjects(Patched):
    """The card's objects' entry after the characters' entries."""

    def setUp(self):
        self.asked = []
        self.entry = (ap.Plan(None, {"|cam.tx": 1.0}, {}, [], {}), "extra")
        self.notes = []

        def card_objects(data, loose, refs, only):
            self.asked.append((loose, only))
            return self.entry, self.notes

        self.patch(ap, "card_objects", card_objects)
        self.first = (ap.Plan(rig_ref(), {"|A.rx": 1.0}, {}, [], {}), "extra")

    def test_the_objects_entry_comes_last(self):
        out = ap._with_objects([self.first], {}, ["|cam"], [rig_ref()], None, False)
        self.assertEqual(out, [self.first, self.entry])
        self.assertEqual(self.asked, [(["|cam"], False)])

    def test_selected_only_is_passed_on_as_a_flag(self):
        ap._with_objects([self.first], {}, [], [], frozenset(["|n"]), False)
        self.assertEqual(self.asked[0][1], True)

    def test_a_mirrored_press_says_the_objects_were_not_mirrored_first(self):
        self.entry[0].notes.append("an own note")
        out = ap._with_objects([self.first], {}, [], [], None, True)
        self.assertEqual(out[1][0].notes, [ap.OBJECTS_UNMIRRORED, "an own note"])

    def test_objects_that_were_neither_selected_nor_found_are_said_on_the_first_entry(self):
        self.entry, self.notes = None, ["not in the scene: cam"]
        out = ap._with_objects([self.first], {}, [], [], None, True)
        self.assertEqual(out, [self.first])
        self.assertEqual(self.first[0].notes, ["not in the scene: cam"])

    def test_notes_with_no_entry_to_carry_them_are_dropped(self):
        self.entry, self.notes = None, ["not in the scene: cam"]
        self.assertEqual(ap._with_objects([], {}, [], [], None, False), [])


class SmallRefusals(Patched):

    def test_a_card_press_with_no_card_or_no_bones_is_refused(self):
        self.assertEqual(ap.apply(None), (False, ap.NO_CARD))
        self.assertEqual(ap.apply({"bones": {}}), (False, ap.NO_BONES))

    def test_a_press_whose_targets_are_refused_says_why(self):
        self.patch(ap, "cmds", AttrCmds(selected=["|prop"]))
        self.patch(ap, "_targets", lambda selection: ([], ap.NOT_A_CHARACTER))
        self.assertEqual(ap.apply({"bones": {"root": {}}}), (False, ap.NOT_A_CHARACTER))

    def test_objects_selected_beside_no_character_press_the_objects_alone(self):
        self.patch(ap, "cmds", AttrCmds(selected=["|cam"]))
        self.patch(ap, "_loose", lambda selection: ["|cam"])
        self.patch(ap, "_body_refs", lambda selection: [])
        self.patch(ap, "_objects_alone", lambda data, loose, alpha: (True, "alone %s %s" % (loose, alpha)))
        data = {"bones": {"root": {}}, "objects": [{"name": "cam"}]}
        self.assertEqual(ap.apply(data, alpha=0.5), (True, "alone ['|cam'] 0.5"))

    def test_a_press_onto_objects_card_goes_to_the_objects_press(self):
        self.patch(ap, "apply_objects", lambda data, selection, alpha: (True, "objects %s" % alpha))
        self.assertEqual(ap.apply({"kind": "objects"}, alpha=0.25), (True, "objects 0.25"))

    def test_the_skipped_plugs_are_noted_once_a_reason_with_their_leaves(self):
        notes = ap._skipped_note({"|a|b.tx": "locked", "|c.ty": "locked", "hand_l": "driven"})
        self.assertEqual(notes, ["2 not posed (locked): b.tx, c.ty", "1 not posed (driven): hand_l"])
        self.assertEqual(ap._skipped_note(None), [])

    def test_a_view_that_cannot_refresh_is_left_as_it_is(self):
        class Cmds(object):
            def refresh(self, currentView=False):
                raise RuntimeError("no view")

        self.patch(ap, "cmds", Cmds())
        self.assertIsNone(ap._refresh())

    def test_the_selected_nodes_of_mayas_selection_when_none_is_given(self):
        self.patch(ap, "cmds", AttrCmds(selected=["a", "b"]))
        self.patch(scene, "dag_object", lambda item: "|" + item)
        self.patch(scene, "stand_ins", lambda paths: dict((p, p) for p in paths))
        self.patch(rigsolve, "knot_driver", lambda path: "|knot" if path == "|b" else None)
        self.assertEqual(ap.selected_nodes(), frozenset(["|a", "|b", "|knot"]))

    def test_a_card_that_selected_only_keeps_in_full_says_nothing(self):
        values = OrderedDict([("|a.tx", 1.0), ("|b.tx", 2.0)])
        self.patch(ap, "_long_node", lambda node: node)
        self.assertEqual(ap.only_selected(values, frozenset(["|a", "|b"]), "controls"), (values, ""))

    def test_a_card_that_selected_only_keeps_in_part_says_how_many(self):
        values = OrderedDict([("|a.tx", 1.0), ("|b.tx", 2.0)])
        self.patch(ap, "_long_node", lambda node: node)
        kept, note = ap.only_selected(values, frozenset(["|a"]), "controls")
        self.assertEqual((list(kept), note), (["|a.tx"], "Selected only: 1 of 2 controls keyed"))

    def test_the_failure_to_find_a_stored_attribute_is_named_with_its_object(self):
        self.patch(ap, "cmds", AttrCmds())
        self.patch(objects, "plugs_of",
                   lambda record, path, cmds_: (OrderedDict(), ["cam.gone", "cam.gone2"]))
        self.patch(keys, "current", lambda values: {})
        plan, extra = ap._values_entry([({"name": "cam"}, "|cam")])
        self.assertEqual(plan.notes, ["2 not posed (no such attribute): cam.gone, cam.gone2"])
        self.assertEqual(extra.label, "1 object")

    def test_an_objects_card_with_no_objects_and_no_layer_to_key_is_refused(self):
        self.assertEqual(ap._objects_entry({"objects": []}, None), (None, ap.NO_OBJECTS))
        self.assertEqual(ap._objects_entry(None, None), (None, ap.NO_OBJECTS))
        self.patch(keys, "active_layer", lambda: (None, "the animation layer A is locked"))
        self.assertEqual(ap.apply_objects({"objects": [{}]}), (False, "the animation layer A is locked"))
        self.patch(keys, "active_layer", lambda: (("layer",), ""))
        self.assertEqual(ap.apply_objects({"objects": []}), (False, ap.NO_OBJECTS))


if __name__ == "__main__":
    unittest.main()

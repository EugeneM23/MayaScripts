"""The Pose Library's reading of the scene, the parts `test_poselib_scene` leaves out: which node is a
DAG object, which character a node belongs to (`character_of`, `rig_ref`, `skeleton_ref`,
`characters`, `split`, `resolve`), body or object (`_skinned`, `_is_body`), the part rig's driven
bones, the skeleton read as data (`skeleton`, `bind_pose`, `_unlisted_helpers`, `_bind`, `bone_path`,
`identity`) and the member bones a scene selection names (`members_of`).

Everything runs on small fakes: the module's `cmds` and `maya_rigs` functions, the `maya_scenesetup` /
`maya_uebridge` seams it asks, and - for `skeleton` - the shipped Manny template laid out as a scene.
Each seam is rebound for the test and restored by cleanup.
"""

import copy
import json
import os
import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya_asretarget
import maya_retargetmode
import maya_rigs
import maya_skeletonmap as skelmap
from maya_scenesetup import armor, bonedrive, camera, cameraaim, deletion, weaponaim, weaponspace
from maya_uebridge import skeletonimport

from maya_poselib import posemath, rigsolve, scene
from tests.test_poselib_helpers import close, trs

_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "SkeldarAnim", "assets", "manny_skeleton_template.json")


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


def make_rig(group="|Manny_Rig1_Character|Manny_Rig1:Group", namespace="Manny_Rig1",
             skeleton_root="|Manny_Rig1_Character|Manny_Rig1:root", character=None):
    return maya_rigs.Rig(namespace, None, None, group, skeleton_root, character)


def character(kind="rig", root="|Manny_Rig1_Character|Manny_Rig1:root", rig="make",
              label="Manny [rig]", namespace="Manny_Rig1"):
    if rig == "make":
        rig = make_rig(skeleton_root=root)
    return scene.CharacterRef(kind, root, rig, label, "Manny_Rig", "Manny", namespace)


# ------------------------------------------------------------------ pure leftovers

class CanonicalNamesPaths(unittest.TestCase):

    def test_a_mapped_path_the_skeleton_does_not_hold_is_ignored(self):
        out = scene.canonical_names(["|root", "|root|hips"], {"pelvis": "|root|hips", "head": "|gone"},
                                    False)
        self.assertEqual(out, {"|root": None, "|root|hips": "pelvis"})


class KnotWalk(Patched):
    """`stand_in` follows a knot on a knot a few steps and then stops - a knot cycle or a very deep
    stack ends the walk instead of looping."""

    def chain(self, count, loop=False):
        nodes = dict(("|k%d" % i, {"skeldarKnot": "knot", "skeldarKnotSource": "U%d" % (i + 1)})
                     for i in range(count))
        uuids = dict(("U%d" % i, "|k%d" % i) for i in range(count + 1))
        if loop:
            uuids["U%d" % count] = "|k0"
        else:
            nodes["|k%d" % count] = {}

        class Cmds(object):
            def attributeQuery(self, attr, node=None, exists=False):
                return attr in nodes.get(node, {})

            def getAttr(self, plug):
                node, attr = plug.rsplit(".", 1)
                return nodes[node][attr]

            def ls(self, items, objectsOnly=False, long=False, **kwargs):
                if isinstance(items, str):
                    return [uuids[items]] if items in uuids else []
                return [n for n in set(i.rsplit(".", 1)[0] for i in items) if n in nodes
                        and any(i.rsplit(".", 1)[1] in nodes[n] for i in items
                                if i.rsplit(".", 1)[0] == n)]

        self.patch(scene, "cmds", Cmds())

    def test_a_cycle_of_knots_stops_where_it_began(self):
        self.chain(3, loop=True)
        self.assertEqual(scene.stand_in("|k0"), "|k0")

    def test_a_stack_deeper_than_the_depth_stops_at_the_depth(self):
        self.chain(12)
        self.assertEqual(scene.stand_in("|k0"), "|k%d" % scene.KNOT_DEPTH)

    def test_a_stack_inside_the_depth_reaches_its_object(self):
        self.chain(3)
        self.assertEqual(scene.stand_in("|k0"), "|k3")


# ------------------------------------------------------------------ the part rig's bones

class PartCmds(object):

    def __init__(self, anchored=(), joints=(), constrained=()):
        self.anchored = set(anchored)
        self.joints = list(joints)
        self.constrained = set(constrained)
        self.asked = []

    def attributeQuery(self, attr, node=None, exists=False):
        return attr == scene.PART_ANCHOR_ATTR and node in self.anchored

    def ls(self, root, dag=False, type=None, long=False):
        self.asked.append((root, type))
        return self.joints

    def listRelatives(self, joint, children=False, type=None):
        return ["constraint1"] if joint in self.constrained else []


class DrivenBones(Patched):

    ROOT = "|G|ns:root"
    JOINTS = ["|G|ns:root", "|G|ns:root|ns:spine", "|G|ns:root|ns:hand_r"]

    def part_rig(self, **kwargs):
        self.patch(scene, "cmds", PartCmds(**kwargs))
        return character(root=self.ROOT, rig=make_rig(group="|G", skeleton_root=self.ROOT))

    def test_only_a_rig_has_driven_bones(self):
        self.patch(scene, "cmds", PartCmds(anchored=["|G"]))
        skeleton = character(kind="skeleton", rig=None)
        self.assertIsNone(scene.driven_bones(skeleton, {"root": {}}))
        self.assertIsNone(scene.driven_bones(character(rig=None), {"root": {}}))

    def test_a_rig_with_no_group_or_no_part_anchor_poses_the_whole_skeleton(self):
        self.patch(scene, "cmds", PartCmds())
        self.assertIsNone(scene.driven_bones(character(rig=make_rig(group=None)), {"root": {}}))
        self.assertIsNone(scene.driven_bones(character(rig=make_rig(group="|G")), {"root": {}}))

    def test_a_part_rig_drives_the_joints_with_a_constraint_under_them_in_skeleton_order(self):
        ref = self.part_rig(anchored=["|G"], joints=self.JOINTS,
                            constrained=["|G|ns:root|ns:hand_r", "|G|ns:root|ns:spine"])
        bones = {"root": {}, "hand_r": {}, "spine": {}, "pelvis": {}}
        self.assertEqual(scene.driven_bones(ref, bones), ["hand_r", "spine"])

    def test_a_part_rig_driving_nothing_has_an_empty_list_not_none(self):
        ref = self.part_rig(anchored=["|G"], joints=self.JOINTS)
        self.assertEqual(scene.driven_bones(ref, {"root": {}}), [])

    def test_the_joints_are_asked_under_the_skeleton_root(self):
        ref = self.part_rig(anchored=["|G"], joints=self.JOINTS)
        scene.driven_bones(ref, {"root": {}})
        self.assertEqual(scene.cmds.asked, [(self.ROOT, "joint")])


# ------------------------------------------------------------------ which node, which character

class DagCmds(object):

    def __init__(self, longs=None, dag=(), shapes=None, selected=()):
        self.longs = longs or {}
        self.dag = set(dag)
        self.shapes = shapes or {}
        self.selected = list(selected)

    def ls(self, *names, **kwargs):
        if kwargs.get("selection"):
            return list(self.selected)
        found = self.longs.get(names[0])
        return [found] if found else []

    def objectType(self, path, isAType=None):
        if isAType == "dagNode":
            return path in self.dag
        return path in self.shapes

    def listRelatives(self, path, parent=False, fullPath=False):
        parent_path = self.shapes.get(path)
        return [parent_path] if parent_path else None


class DagObject(Patched):

    def setUp(self):
        self.patch(scene, "cmds", DagCmds(
            longs={"cube": "|cube", "cubeShape": "|cube|cubeShape", "orphanShape": "|orphanShape",
                   "time1": "time1"},
            dag=["|cube", "|cube|cubeShape", "|orphanShape"],
            shapes={"|cube|cubeShape": "|cube", "|orphanShape": None}))

    def test_a_name_is_the_long_path_or_none(self):
        self.assertEqual(scene._long("cube"), "|cube")
        self.assertIsNone(scene._long("nothing"))
        self.assertIsNone(scene._long(""))
        self.assertIsNone(scene._long(None))

    def test_a_transform_is_itself(self):
        self.assertEqual(scene.dag_object("cube"), "|cube")

    def test_a_component_is_its_object(self):
        self.assertEqual(scene.dag_object("cube.vtx[0:3]"), "|cube")

    def test_a_shape_is_its_transform(self):
        self.assertEqual(scene.dag_object("cubeShape"), "|cube")

    def test_a_shape_with_no_parent_is_none(self):
        self.assertIsNone(scene.dag_object("orphanShape"))

    def test_a_node_outside_the_dag_is_none(self):
        self.assertIsNone(scene.dag_object("time1"))
        self.assertIsNone(scene.dag_object("nothing"))
        self.assertIsNone(scene.dag_object(None))
        self.assertIsNone(scene.dag_object(""))


class LabelCmds(object):

    def __init__(self, marked=None):
        self.marked = marked or {}

    def attributeQuery(self, attr, node=None, exists=False):
        return attr == maya_rigs.CHARACTER_MARKER and node in self.marked

    def getAttr(self, plug):
        return self.marked[plug.rsplit(".", 1)[0]]


class Refs(Patched):

    def setUp(self):
        self.patch(maya_rigs, "label", lambda rig: "label of " + rig.namespace)
        self.recorded = ("", "")
        self.patch(deletion, "recorded", lambda root: (set(), self.recorded[0]))
        self.patch(maya_rigs, "group_of", lambda path: "|Char_Character")

    def test_a_group_with_no_marker_has_no_label(self):
        self.patch(scene, "cmds", LabelCmds())
        self.assertEqual(scene._group_label("|G"), "")
        self.assertEqual(scene._group_label(None), "")

    def test_a_group_s_label_is_its_marker_s_value(self):
        self.patch(scene, "cmds", LabelCmds({"|G": "Manny [rig]", "|H": None}))
        self.assertEqual(scene._group_label("|G"), "Manny [rig]")
        self.assertEqual(scene._group_label("|H"), "")

    def test_a_rig_that_drives_no_game_skeleton_is_no_character(self):
        self.patch(scene, "cmds", LabelCmds())
        self.assertIsNone(scene.rig_ref(make_rig(skeleton_root=None)))

    def test_a_rig_takes_its_catalog_row_from_its_group_marker(self):
        rig = make_rig(character="|Creep_Group", namespace="Anything7")
        self.patch(scene, "cmds", LabelCmds({"|Creep_Group": "Creep [rig]"}))
        ref = scene.rig_ref(rig)
        self.assertEqual((ref.kind, ref.label, ref.key, ref.model, ref.namespace),
                         ("rig", "Creep [rig]", "Creep_Rig", "Creep", "Anything7"))
        self.assertIs(ref.rig, rig)
        self.assertEqual(ref.root, rig.skeleton_root)

    def test_a_rig_with_no_marker_takes_its_row_from_its_namespace_key(self):
        self.patch(scene, "cmds", LabelCmds())
        ref = scene.rig_ref(make_rig(namespace="Orc_D_Rig3"))
        self.assertEqual((ref.label, ref.key, ref.model), ("Orc D [rig]", "Orc_D_Rig", "Orc_D"))

    def test_a_marker_the_catalog_does_not_know_falls_back_to_the_namespace_key(self):
        rig = make_rig(character="|G", namespace="Manny_Rig2")
        self.patch(scene, "cmds", LabelCmds({"|G": "Unheard Of"}))
        self.assertEqual(scene.rig_ref(rig).label, "Manny [rig]")

    def test_a_rig_the_catalog_does_not_know_is_named_as_a_message_names_it(self):
        self.patch(scene, "cmds", LabelCmds())
        ref = scene.rig_ref(make_rig(namespace="Stranger1"))
        self.assertEqual((ref.label, ref.key, ref.model), ("label of Stranger1", None, None))

    def test_a_skeleton_takes_its_row_from_the_label_its_add_recorded(self):
        self.recorded = ("Manny UE5 [skeleton]", "")
        self.patch(scene, "cmds", LabelCmds())
        ref = scene.skeleton_ref("|Manny_Character|root")
        self.assertEqual((ref.kind, ref.root, ref.label, ref.key, ref.model, ref.namespace),
                         ("skeleton", "|Manny_Character|root", "Manny UE5 [skeleton]", "Manny",
                          "Manny", ""))
        self.assertIsNone(ref.rig)

    def test_a_skeleton_with_no_record_takes_its_label_from_its_character_group(self):
        self.patch(scene, "cmds", LabelCmds({"|Char_Character": "Creep [skeleton]"}))
        ref = scene.skeleton_ref("|Char_Character|root")
        self.assertEqual((ref.label, ref.key), ("Creep [skeleton]", "Creep"))

    def test_a_native_skeleton_keeps_its_recorded_label_and_has_no_row(self):
        self.recorded = ("Auto Rig skeleton", "")
        self.patch(scene, "cmds", LabelCmds())
        ref = scene.skeleton_ref("|Auto:root")
        self.assertEqual((ref.label, ref.key, ref.model, ref.namespace),
                         ("Auto Rig skeleton", None, None, "Auto"))

    def test_a_skeleton_with_no_label_at_all_is_named_by_its_root(self):
        self.patch(scene, "cmds", LabelCmds())
        self.assertEqual(scene.skeleton_ref("|Stranger|hips").label, "hips")


class CharacterOf(Patched):
    """`character_of`: the rig's own answer comes before the weapon and armour walks; a joint of a
    bare skeleton names it at once; a mesh, a group or any transform goes through the skin, the
    skeletons below it or its character group."""

    RIG = make_rig()
    ROOT = "|Creep_Character|root"

    def setUp(self):
        self.log = []
        self.longs = {}
        self.types = {}
        self.owner = {}
        self.hands = {}
        self.bones = {}
        self.skins = {}
        self.groups = {}
        self.group_roots = {}
        self.cmds = DagCmds()
        self.cmds.ls = lambda *names, **kw: [self.longs[names[0]]] if names[0] in self.longs else []
        self.cmds.objectType = lambda path, isAType=None: self.types.get(path, "transform")
        self.patch(scene, "cmds", self.cmds)
        self.patch(maya_rigs, "rigs", lambda: [self.RIG])
        self.patch(maya_rigs, "rig_of", lambda path, rigs: self.owner.get(path))
        self.patch(maya_rigs, "group_of", lambda path: self.groups.get(path))
        self.patch(maya_rigs, "group_root", lambda group: self.group_roots.get(group))
        self.patch(scene, "rig_ref", lambda rig: self.log.append("rig_ref") or "RIG REF")
        self.patch(scene, "skeleton_ref", lambda root: self.log.append("skel " + root) or "SKEL " + root)
        self.patch(skeletonimport, "_top_joint", lambda path: self.ROOT)
        self.patch(skeletonimport, "_skin_root", lambda path: self.skins.get(path))
        self.patch(weaponspace, "hand_for",
                   lambda path: self.log.append("hand_for") or self.hands.get(path))
        self.patch(armor, "bone_for", lambda path: self.log.append("bone_for") or self.bones.get(path))
        for path in ("|Manny_Rig1_Character|Manny_Rig1:Group|Manny_Rig1:Main", "|sword", "|mesh", "|prop",
                     self.ROOT, "|Creep_Character|root|hand"):
            self.longs[path] = path

    def of(self, path, bare=(), refs=None):
        return scene.character_of(path, rigs=[self.RIG], bare=list(bare), refs=refs)

    def test_nothing_or_a_node_that_is_gone_is_no_character(self):
        self.assertIsNone(self.of(None))
        self.assertIsNone(self.of(""))
        self.assertIsNone(self.of("|gone"))

    def test_a_rig_s_node_is_that_rig_and_no_weapon_or_armour_walk_is_made(self):
        path = "|Manny_Rig1_Character|Manny_Rig1:Group|Manny_Rig1:Main"
        self.owner[path] = self.RIG
        self.assertEqual(self.of(path), "RIG REF")
        self.assertEqual(self.log, ["rig_ref"])

    def test_one_rig_ref_is_made_for_a_selection_that_shares_a_refs_dict(self):
        path = "|Manny_Rig1_Character|Manny_Rig1:Group|Manny_Rig1:Main"
        self.owner[path] = self.RIG
        refs = {}
        self.of(path, refs=refs)
        self.of(path, refs=refs)
        self.assertEqual(self.log, ["rig_ref"])
        self.assertEqual(list(refs), [("rig", self.RIG.namespace, self.RIG.group)])

    def test_the_rigs_are_read_from_the_scene_when_not_given(self):
        path = "|sword"
        self.owner[path] = self.RIG
        self.patch(scene, "_bare", lambda: [])
        self.assertEqual(scene.character_of(path), "RIG REF")

    def test_a_joint_of_a_bare_skeleton_names_it_at_once(self):
        path = "|Creep_Character|root|hand"
        self.types[path] = "joint"
        self.assertEqual(self.of(path, bare=[self.ROOT]), "SKEL " + self.ROOT)
        self.assertEqual(self.log, ["skel " + self.ROOT])

    def test_a_weapon_names_the_character_whose_hand_holds_it(self):
        self.hands["|sword"] = "|Manny_Rig1_Character|Manny_Rig1:Group|Manny_Rig1:Main"
        self.owner[self.hands["|sword"]] = self.RIG
        self.assertEqual(self.of("|sword"), "RIG REF")
        self.assertEqual(self.log, ["hand_for", "rig_ref"])

    def test_an_armour_piece_names_the_bone_its_space_follows(self):
        self.bones["|sword"] = "|Manny_Rig1_Character|Manny_Rig1:Group|Manny_Rig1:Main"
        self.owner[self.bones["|sword"]] = self.RIG
        self.assertEqual(self.of("|sword"), "RIG REF")
        self.assertEqual(self.log, ["hand_for", "bone_for", "rig_ref"])

    def test_a_mesh_names_the_skeleton_it_is_skinned_to(self):
        self.skins["|mesh"] = self.ROOT
        self.assertEqual(self.of("|mesh", bare=[self.ROOT]), "SKEL " + self.ROOT)

    def test_a_group_names_the_bare_skeleton_under_it(self):
        self.assertEqual(self.of("|prop", bare=["|prop|root"]), "SKEL |prop|root")

    def test_a_transform_beside_a_skeleton_names_its_character_group_s_root(self):
        self.groups["|prop"] = "|Creep_Character"
        self.group_roots["|Creep_Character"] = self.ROOT
        self.assertEqual(self.of("|prop", bare=[self.ROOT]), "SKEL " + self.ROOT)

    def test_a_node_of_no_character_is_none(self):
        self.assertIsNone(self.of("|prop", bare=[self.ROOT]))
        self.groups["|prop"] = "|Creep_Character"
        self.group_roots["|Creep_Character"] = "|Other|root"
        self.assertIsNone(self.of("|prop", bare=[self.ROOT]))

    def test_a_joint_of_no_bare_skeleton_is_none(self):
        path = "|Creep_Character|root|hand"
        self.types[path] = "joint"
        self.assertIsNone(self.of(path, bare=[]))

    def test_the_cache_keeps_one_ref_per_key(self):
        refs = {}
        made = []
        first = scene._cached(refs, ("rig", "a", "g"), lambda: made.append(1) or "one")
        second = scene._cached(refs, ("rig", "a", "g"), lambda: made.append(1) or "two")
        self.assertEqual((first, second, len(made)), ("one", "one", 1))


class Selection(Patched):

    def refs(self):
        a = character(root="|A|root", rig=None, kind="skeleton")
        b = character(root="|B|root", rig=None, kind="skeleton")
        return a, b

    def test_the_selected_nodes_default_to_mayas_and_none_selected_asks_no_one(self):
        self.patch(scene, "cmds", DagCmds(selected=[]))
        self.patch(maya_rigs, "rigs", lambda: self.fail("no rigs asked for an empty selection"))
        self.assertEqual(scene.resolve(), [])

    def test_a_selection_is_resolved_in_order_without_repeats_and_through_stand_ins(self):
        self.patch(scene, "cmds", DagCmds(selected=["a.vtx[0]", "b", "a", "bad"]))
        self.patch(scene, "dag_object", lambda item: None if item == "bad" else "|" + item.split(".")[0])
        self.patch(scene, "stand_ins", lambda paths: {"|b": "|c"})
        self.patch(scene, "_bare", lambda: [])
        self.patch(maya_rigs, "rigs", lambda: [])
        self.patch(scene, "character_of", lambda path, rigs, bare, refs: "ref of " + path)
        self.assertEqual(scene.resolve(), [("|a", "ref of |a"), ("|c", "ref of |c")])

    def test_characters_are_each_once_in_order_and_the_rest_are_loose(self):
        a, b = self.refs()
        a_again = a._replace(label="same root")
        self.patch(scene, "resolve", lambda selection=None: [
            ("|A|root|hand", a), ("|prop", None), ("|B|root|hand", b), ("|A|root|foot", a_again)])
        refs, loose = scene.characters()
        self.assertEqual(refs, [a, b])
        self.assertEqual(loose, ["|prop"])

    def test_the_label_the_save_panel_says_is_the_description_of_the_selection(self):
        a, _b = self.refs()
        self.patch(scene, "resolve", lambda selection=None: [("|A|root|hand", a)])
        self.assertEqual(scene.selection_label(), "Manny [rig] (Manny_Rig1)")
        self.patch(scene, "resolve", lambda selection=None: [("|p1", None), ("|p2", None)])
        self.assertEqual(scene.selection_label(), "2 objects")
        self.patch(scene, "resolve", lambda selection=None: [])
        self.assertEqual(scene.selection_label(), "nothing selected")

    def test_every_rig_that_drives_a_skeleton_then_every_bare_skeleton(self):
        driving, idle = make_rig(namespace="A1"), make_rig(namespace="B1", skeleton_root=None)
        self.patch(maya_rigs, "rigs", lambda: [driving, idle])
        self.patch(scene, "rig_ref", lambda rig: None if rig is idle else "rig " + rig.namespace)
        self.patch(scene, "skeleton_ref", lambda root: "skeleton " + root)
        self.patch(scene, "_bare", lambda: ["|S1|root", "|S2|root"])
        self.assertEqual(scene.all_characters(), ["rig A1", "skeleton |S1|root", "skeleton |S2|root"])

    def test_the_bare_skeletons_are_the_ue_bridges(self):
        self.patch(skeletonimport, "bare_roots", lambda: ["|S|root"])
        self.assertEqual(scene._bare(), ["|S|root"])


class SplitSelection(Patched):

    def test_the_body_nodes_the_characters_they_touch_and_the_objects_with_their_owners(self):
        a = character(root="|A|root", rig=None, kind="skeleton")
        b = character(root="|B|root", rig=None, kind="skeleton")
        self.patch(scene, "resolve", lambda selection=None: [
            ("|A|root|hand", a), ("|A|cam", a), ("|prop", None), ("|B|root", b),
            ("|A|root|foot", a)])
        self.patch(scene, "_is_body", lambda path, ref: path.startswith(ref.root))
        refs, body, loose = scene.split()
        self.assertEqual(refs, [a, b])
        self.assertEqual(body, ["|A|root|hand", "|B|root", "|A|root|foot"])
        self.assertEqual(loose, [("|A|cam", a), ("|prop", None)])

    def test_an_object_is_owned_by_the_character_it_belongs_to_only(self):
        a = character(root="|A|root", rig=None, kind="skeleton")
        b = character(root="|B|root", rig=None, kind="skeleton")
        self.assertTrue(scene.owned(a, a._replace(label="the same root")))
        self.assertFalse(scene.owned(a, b))
        self.assertFalse(scene.owned(a, None))
        self.assertFalse(scene.owned(None, a))


class BodyCmds(object):

    def __init__(self, types=None, meshes=None, skinned=()):
        self.types = types or {}
        self.meshes = meshes or {}
        self.skinned = set(skinned)

    def nodeType(self, path):
        return self.types.get(path, "transform")

    def listRelatives(self, path, shapes=False, type=None, fullPath=False):
        return self.meshes.get(path)

    def listHistory(self, shape, pruneDagObjects=False):
        return ["history of " + shape]

    def ls(self, history, type=None):
        return ["skinCluster1"] if history[0].endswith(tuple(self.skinned)) else []


class IsBody(Patched):

    GROUP = "|Manny_Rig1_Character|Manny_Rig1:Group"
    ROOT = "|Manny_Rig1_Character|Manny_Rig1:root"

    def setUp(self):
        self.kinds = {}
        self.patch(scene, "_kind", lambda path, ref=None: self.kinds.get(path, "transform"))
        self.ref = character(root=self.ROOT, rig=make_rig(group=self.GROUP, skeleton_root=self.ROOT))
        self.skeleton = character(kind="skeleton", root="|Manny_Character|root", rig=None)

    def scene(self, **kwargs):
        self.patch(scene, "cmds", BodyCmds(**kwargs))

    def test_a_node_of_no_character_is_an_object(self):
        self.scene()
        self.assertFalse(scene._is_body("|prop", None))

    def test_a_joint_is_body(self):
        self.scene(types={"|j": "joint"})
        self.assertTrue(scene._is_body("|j", self.skeleton))

    def test_anything_under_a_rig_s_group_is_body(self):
        self.scene()
        self.assertTrue(scene._is_body(self.GROUP + "|Manny_Rig1:Main", self.ref))
        self.assertTrue(scene._is_body(self.GROUP, self.ref))

    def test_a_group_holding_the_skeleton_or_the_rig_is_body(self):
        self.scene()
        self.assertTrue(scene._is_body("|Manny_Rig1_Character", self.ref))
        self.assertTrue(scene._is_body("|Manny_Character", self.skeleton))

    def test_a_skinned_mesh_is_body_and_a_plain_one_is_an_object(self):
        self.scene(meshes={"|skin": ["|skin|skinShape"], "|prop": ["|prop|propShape"]},
                   skinned=["skinShape"])
        self.assertTrue(scene._is_body("|skin", self.skeleton))
        self.assertFalse(scene._is_body("|prop", self.skeleton))

    def test_an_accessory_and_the_camera_are_body_and_any_other_transform_is_an_object(self):
        self.scene()
        self.kinds.update({"|sword": scene.ACCESSORY, "|cam": scene.CAMERA})
        self.assertTrue(scene._is_body("|sword", self.skeleton))
        self.assertTrue(scene._is_body("|cam", self.skeleton))
        self.assertFalse(scene._is_body("|prop", self.skeleton))

    def test_a_node_with_no_shape_history_is_not_skinned(self):
        self.scene()
        self.assertFalse(scene._skinned("|prop"))

    def test_is_body_asks_the_node_a_knot_stands_for(self):
        self.scene()
        self.patch(scene, "stand_in", lambda path: "|object" if path == "|knot" else path)
        self.patch(scene, "_is_body", lambda path, ref: path == "|object")
        self.assertTrue(scene.is_body("|knot", self.skeleton))
        self.assertFalse(scene.is_body("|other", self.skeleton))


# ------------------------------------------------------------------ the skeleton as data

class JointCmds(object):
    """A dict scene of joints: {path: {"world": [16], "rotateOrder", "jointOrient", "rotateAxis"}}."""

    def __init__(self, joints, root, skinned=()):
        self.joints = joints
        self.root = root
        self.skinned = set(skinned)

    def objExists(self, node):
        return node in self.joints

    def ls(self, path, long=False):
        return [path] if path in self.joints else []

    def listRelatives(self, root, allDescendents=False, type=None, fullPath=False):
        return [p for p in self.joints if p != root]

    def getAttr(self, plug):
        path, attr = plug.rsplit(".", 1)
        joint = self.joints[path]
        if attr == "worldMatrix[0]":
            return list(joint["world"])
        if attr == "rotateOrder":
            return joint.get("rotateOrder", 0)
        return [tuple(joint.get(attr, (0.0, 0.0, 0.0)))]

    def listConnections(self, plug, **kwargs):
        return ["skinCluster1"] if plug.rsplit(".", 1)[0] in self.skinned else None


def manny_scene():
    """The shipped Manny skeleton as {path: joint} and {leaf: its template record}."""
    with open(_TEMPLATE) as handle:
        records = json.load(handle)["joints"]
    paths, joints, by_leaf = {}, {}, {}
    for record in records:
        parent = paths.get(record["parent"], "")
        paths[record["name"]] = path = parent + "|" + record["name"]
        joints[path] = {"world": [float(v) for v in record["world_matrix"]],
                        "rotateOrder": record["rotateOrder"], "jointOrient": record["jointOrient"],
                        "rotateAxis": record["rotateAxis"]}
        by_leaf[record["name"]] = record
    return joints, paths, by_leaf


class SkeletonRead(Patched):

    def setUp(self):
        self.joints, self.paths, self.records = manny_scene()
        self.ref = scene.CharacterRef("skeleton", self.paths["root"], None, "Manny UE5 [skeleton]",
                                      "Manny", "Manny", "")
        self.patch(scene, "cmds", JointCmds(self.joints, self.paths["root"]))

    def test_every_joint_is_a_bone_keyed_by_its_leaf_with_its_parent_leaf(self):
        bones, convention = scene.skeleton(self.ref)
        self.assertEqual(sorted(bones), sorted(self.records))
        self.assertIsNone(bones["root"]["parent"])
        self.assertEqual(bones["pelvis"]["parent"], "root")
        self.assertEqual(bones["hand_l"]["path"], self.paths["hand_l"])
        self.assertEqual(convention, skelmap.convention_of(list(self.joints)))

    def test_an_unskinned_skeleton_rests_as_it_stands_and_reads_its_channels(self):
        bones, _convention = scene.skeleton(self.ref)
        hand = bones["hand_l"]
        self.assertEqual(hand["world"], [float(v) for v in self.records["hand_l"]["world_matrix"]])
        self.assertEqual(hand["rest"], hand["world"])
        self.assertEqual(bones["root"]["jointOrient"], [-90.0, 0.0, 0.0])
        self.assertEqual(hand["rotateAxis"], [0.0, 0.0, 0.0])
        self.assertIsInstance(hand["rotateOrder"], int)
        self.assertNotIn("drive", hand)

    def test_a_ue_named_skeleton_gets_its_ue_names_and_its_twists_stay_unnamed(self):
        bones, _convention = scene.skeleton(self.ref)
        self.assertEqual(bones["hand_l"]["canonical"], "hand_l")
        self.assertEqual(bones["pelvis"]["canonical"], "pelvis")
        self.assertIsNone(bones["lowerarm_twist_01_l"]["canonical"])

    def test_a_second_bone_of_a_leaf_is_dropped_and_said_in_the_notes(self):
        extra = "|root|pelvis|ball_l"
        self.joints[extra] = dict(self.joints[self.paths["ball_l"]])
        notes = []
        bones, _convention = scene.skeleton(self.ref, notes)
        self.assertEqual(bones["ball_l"]["path"], extra)
        self.assertEqual(notes, ["Manny UE5 [skeleton] carries 2 bones named ball_l - the first is kept"])
        self.assertEqual(len(bones), len(self.records))

    def test_the_notes_are_optional(self):
        extra = "|root|pelvis|ball_l"
        self.joints[extra] = dict(self.joints[self.paths["ball_l"]])
        bones, _convention = scene.skeleton(self.ref)
        self.assertIn("ball_l", bones)

    def test_a_rig_s_unrolled_bones_carry_their_drive(self):
        ref = self.ref._replace(kind="rig", rig=make_rig())
        drive = trs((1, 2, 3), (0, 0, 30))
        self.patch(rigsolve, "drive_matrices", lambda rig: {"upperarm_l": drive, "not_a_bone": drive})
        bones, _convention = scene.skeleton(ref)
        self.assertEqual(bones["upperarm_l"]["drive"], posemath.flat(drive))
        self.assertNotIn("drive", bones["upperarm_r"])
        self.assertNotIn("not_a_bone", bones)

    def test_the_joints_are_the_root_and_every_joint_under_it_parents_first(self):
        paths = scene._joints(self.paths["root"])
        self.assertEqual(paths, sorted(paths, key=lambda p: p.split("|")))
        self.assertEqual(paths[0], self.paths["root"])
        self.assertEqual(len(paths), len(self.records))

    def test_a_missing_or_empty_root_has_no_joints(self):
        self.assertEqual(scene._joints("|gone"), [])
        self.assertEqual(scene._joints(""), [])
        self.assertEqual(scene._joints(None), [])

    def test_a_bone_s_path_is_the_first_joint_with_its_leaf_or_none(self):
        self.assertEqual(scene.bone_path(self.ref, "hand_l"), self.paths["hand_l"])
        self.assertIsNone(scene.bone_path(self.ref, "no_such_bone"))


class SkinnedSkeleton(Patched):
    """A skinned skeleton rests at its bind; the bind pose is asked about the unskinned top first."""

    ROOT, PELVIS = "|root", "|root|pelvis"
    HAND, WEAPON = "|root|pelvis|hand_r", "|root|pelvis|hand_r|weapon_r"

    def setUp(self):
        world = trs((0, 0, 0))
        self.joints = {
            self.ROOT: {"world": list(world)},
            self.PELVIS: {"world": list(trs((0, 96, 0)))},
            self.HAND: {"world": list(trs((-40, 100, 5)))},
            self.WEAPON: {"world": list(trs((-45, 90, 5)))},
        }
        self.binds = {self.PELVIS: list(trs((0, 90, 0))), self.HAND: list(trs((-40, 94, 5)))}
        self.asked = []
        self.posed = {}
        self.seen = {}
        self.ref = scene.CharacterRef("skeleton", self.ROOT, None, "S", None, None, "")
        self.patch(scene, "cmds", JointCmds(self.joints, self.ROOT))
        self.patch(scene, "_bind", lambda path: self.binds.get(path))

        def bind_pose(top, paths):
            self.asked.append(top)
            return self.posed if top == self.posed_for else {}

        self.posed_for = self.ROOT
        self.patch(scene, "bind_pose", bind_pose)

        def recognize(paths, positions):
            self.seen.update(positions)
            return type("Result", (), {"mapping": {}, "refusal": "no", "convention": "x"})()

        self.patch(skelmap, "recognize", recognize)

    def test_a_skinned_joint_rests_at_its_bind_and_recognize_is_handed_the_rests(self):
        bones, convention = scene.skeleton(self.ref)
        self.assertEqual(bones["pelvis"]["rest"], self.binds[self.PELVIS])
        self.assertEqual(bones["pelvis"]["world"], self.joints[self.PELVIS]["world"])
        self.assertEqual(self.seen[self.PELVIS], (0.0, 90.0, 0.0))
        self.assertEqual(self.seen[self.HAND], (-40.0, 94.0, 5.0))
        self.assertEqual(convention, "x")

    def test_an_unskinned_helper_rides_its_parent_s_bind_and_a_refused_name_stays_none(self):
        bones, _convention = scene.skeleton(self.ref)
        self.assertAlmostEqual(bones["weapon_r"]["rest"][13], 84.0, 6)
        self.assertTrue(all(bone["canonical"] is None for bone in bones.values()))

    def test_the_first_bind_pose_that_lists_the_joints_stops_the_asking(self):
        self.posed = {self.ROOT: list(trs((0, 0, 0))), self.PELVIS: list(trs((0, 90, 0)))}
        scene.skeleton(self.ref)
        self.assertEqual(self.asked, [self.ROOT])

    def test_a_skeleton_no_pose_lists_is_asked_for_its_top_then_a_helper(self):
        self.posed_for = None
        scene.skeleton(self.ref)
        self.assertEqual(self.asked[0], self.ROOT)
        self.assertEqual(self.asked[-1], self.WEAPON)


class BindPoseCmds(object):

    def __init__(self, poses, links, worlds):
        self.poses = poses
        self.links = links
        self.worlds = worlds

    def dagPose(self, top, query=False, bindPose=False):
        return self.poses

    def listConnections(self, plug, **kwargs):
        return self.links.get(plug.rsplit(".", 1)[0])

    def getAttr(self, plug):
        return self.worlds[plug]


class BindPose(Patched):

    A, B, C = "|r", "|r|a", "|r|a|b"

    def flat(self, x):
        return [float(v) for v in trs((x, 0, 0))]

    def test_no_pose_listing_the_joint_is_an_empty_answer(self):
        self.patch(scene, "cmds", BindPoseCmds(None, {}, {}))
        self.assertEqual(scene.bind_pose(self.A, [self.A]), {})

    def test_the_worlds_the_pose_holds_for_the_listed_joints(self):
        self.patch(scene, "cmds", BindPoseCmds(
            ["dagPose1"], {self.A: ["dagPose1.members[0]"], self.B: ["dagPose1.members[3]"]},
            {"dagPose1.worldMatrix[0]": self.flat(1), "dagPose1.worldMatrix[3]": self.flat(2)}))
        self.assertEqual(scene.bind_pose(self.A, [self.A, self.B, self.C]),
                         {self.A: self.flat(1), self.B: self.flat(2)})

    def test_of_several_poses_the_one_listing_the_most_joints_wins(self):
        self.patch(scene, "cmds", BindPoseCmds(
            ["dagPose1", "dagPose2"],
            {self.A: ["dagPose1.members[0]", "dagPose2.members[0]"],
             self.B: ["dagPose2.members[1]"]},
            {"dagPose1.worldMatrix[0]": self.flat(1), "dagPose2.worldMatrix[0]": self.flat(5),
             "dagPose2.worldMatrix[1]": self.flat(6)}))
        self.assertEqual(scene.bind_pose(self.A, [self.A, self.B]),
                         {self.A: self.flat(5), self.B: self.flat(6)})

    def test_a_tie_goes_to_the_first_pose_by_name(self):
        self.patch(scene, "cmds", BindPoseCmds(
            ["dagPose2", "dagPose1"],
            {self.A: ["dagPose2.members[0]", "dagPose1.members[0]"]},
            {"dagPose1.worldMatrix[0]": self.flat(1), "dagPose2.worldMatrix[0]": self.flat(2)}))
        self.assertEqual(scene.bind_pose(self.A, [self.A]), {self.A: self.flat(1)})

    def test_a_plug_that_is_not_a_member_slot_or_not_of_a_known_pose_is_ignored(self):
        self.patch(scene, "cmds", BindPoseCmds(
            ["dagPose1"],
            {self.A: ["dagPose1.parents[0]", "dagPose9.members[0]", "dagPose1.members[2]"]},
            {"dagPose1.worldMatrix[2]": self.flat(3)}))
        self.assertEqual(scene.bind_pose(self.A, [self.A]), {self.A: self.flat(3)})

    def test_a_world_that_is_not_sixteen_numbers_is_left_out(self):
        self.patch(scene, "cmds", BindPoseCmds(
            ["dagPose1"], {self.A: ["dagPose1.members[0]"], self.B: ["dagPose1.members[1]"]},
            {"dagPose1.worldMatrix[0]": [1.0, 2.0], "dagPose1.worldMatrix[1]": None}))
        self.assertEqual(scene.bind_pose(self.A, [self.A, self.B]), {})


class HelperCmds(object):

    def __init__(self, translate, rotate_axis=(0.0, 0.0, 0.0), joint_orient=None):
        self.values = {"translate": [translate], "rotateAxis": [rotate_axis]}
        if joint_orient is not None:
            self.values["jointOrient"] = [joint_orient]

    def getAttr(self, plug):
        return self.values[plug.rsplit(".", 1)[1]]

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.values


class UnlistedHelpers(Patched):

    PARENT, HELPER, FINGER = "|r|hand_r", "|r|hand_r|weapon_r", "|r|hand_r|finger"

    def test_a_helper_the_pose_does_not_list_rests_on_its_parent_with_no_rotation(self):
        self.patch(scene, "cmds", HelperCmds((0.0, 5.0, 0.0), rotate_axis=(0.0, 0.0, 90.0)))
        parent = [float(v) for v in trs((10, 0, 0))]
        parents = {self.PARENT: None, self.HELPER: self.PARENT}
        out = scene._unlisted_helpers([self.PARENT, self.HELPER], parents, {self.PARENT: parent})
        close(self, out[self.HELPER], trs((0, 5, 0), (0, 0, 90)) * trs((10, 0, 0)), 1e-9)
        self.assertEqual(out[self.PARENT], parent)

    def test_the_joint_orient_turns_the_helper_too_when_it_has_one(self):
        self.patch(scene, "cmds", HelperCmds((0.0, 0.0, 0.0), joint_orient=(0.0, 90.0, 0.0)))
        parents = {self.PARENT: None, self.HELPER: self.PARENT}
        parent = [float(v) for v in trs((0, 0, 0))]
        out = scene._unlisted_helpers([self.PARENT, self.HELPER], parents, {self.PARENT: parent})
        close(self, out[self.HELPER], trs((0, 0, 0), (0, 90, 0)), 1e-9)

    def test_what_is_not_a_helper_or_is_listed_or_has_no_listed_parent_is_left_alone(self):
        self.patch(scene, "cmds", HelperCmds((1.0, 1.0, 1.0)))
        listed = [float(v) for v in trs((7, 7, 7))]
        parent = [float(v) for v in trs((10, 0, 0))]
        parents = {self.PARENT: None, self.HELPER: self.PARENT, self.FINGER: self.PARENT,
                   "|r|camera_root": "|r|missing"}
        posed = {self.PARENT: parent, self.HELPER: listed}
        out = scene._unlisted_helpers(
            [self.PARENT, self.HELPER, self.FINGER, "|r|camera_root"], parents, posed)
        self.assertEqual(out, posed)

    def test_the_posed_input_is_not_changed(self):
        self.patch(scene, "cmds", HelperCmds((0.0, 5.0, 0.0)))
        posed = {self.PARENT: [float(v) for v in trs((10, 0, 0))]}
        before = copy.deepcopy(posed)
        scene._unlisted_helpers([self.PARENT, self.HELPER], {self.HELPER: self.PARENT}, posed)
        self.assertEqual(posed, before)


class RestOfAnUnskinnedTop(unittest.TestCase):

    def test_an_unskinned_top_with_no_skinned_joint_below_it_in_the_pose_rests_where_it_stands(self):
        top, child = "|r", "|r|a"
        binds = {child: [float(v) for v in trs((0, 90, 0))]}
        now = {top: [float(v) for v in trs((50, 0, 0))], child: [float(v) for v in trs((50, 90, 0))]}
        posed = {top: [float(v) for v in trs((3, 0, 0))]}
        out = scene.rests([top, child], binds, now, posed)
        self.assertEqual(out[top], posed[top])
        self.assertEqual(out[child], binds[child])


class OwnNodes(Patched):
    """A character's own nodes need no walk up their ancestors for a weapon or armour space."""

    def test_no_character_owns_nothing(self):
        self.assertFalse(scene._own(None, "|a:b"))

    def test_a_rig_owns_what_is_in_its_namespace(self):
        ref = character(namespace="Manny_Rig1")
        self.assertTrue(scene._own(ref, "|G|Manny_Rig1:Main"))
        self.assertFalse(scene._own(ref, "|G|Other1:Main"))
        self.assertFalse(scene._own(ref, "|G|Main"))

    def test_a_skeleton_with_no_namespace_owns_its_joints_and_only_its_joints(self):
        ref = character(kind="skeleton", root="|Manny_Character|root", rig=None, namespace="")
        self.patch(scene, "cmds", BodyCmds(types={"|Manny_Character|root|hand": "joint"}))
        self.assertTrue(scene._own(ref, "|Manny_Character|root|hand"))
        self.assertFalse(scene._own(ref, "|Manny_Character|root|prop"))
        self.assertFalse(scene._own(ref, "|Elsewhere|root|hand"))

    def test_a_skeleton_with_a_namespace_owns_the_nodes_in_it(self):
        ref = character(kind="skeleton", root="|clip:root", rig=None, namespace="clip")
        self.assertTrue(scene._own(ref, "|clip:root|clip:hand"))
        self.assertFalse(scene._own(ref, "|other:hand"))


class SelectionKind(Patched):
    """The kind of one selected transform: a camera, an accessory (a weapon in a hand or on the
    floor, an armour piece), a mesh, or the node type."""

    def setUp(self):
        self.camera_markers = set()
        self.accessory_markers = set()
        self.types = {}
        self.meshes = {}
        self.hand = {}
        self.piece = {}
        self.weapon_controllers = set()
        self.patch(camera, "MARKER", "camMark")
        self.patch(camera, "CONTROL_MARKER", "camCtrl")
        self.patch(camera, "FOLLOW_MARKER", "camFollow")
        self.patch(bonedrive, "MARKER", "boneMark")
        self.patch(armor, "MARKER", "armorMark")
        self.patch(cameraaim, "is_controller", lambda path: False)
        self.patch(weaponaim, "is_controller", lambda path: path in self.weapon_controllers)
        self.patch(weaponspace, "hand_for", lambda path: self.log("hand_for") or self.hand.get(path))
        self.patch(armor, "bone_for", lambda path: self.log("bone_for") or self.piece.get(path))
        self.walks = []
        owner = self

        class Cmds(object):
            def attributeQuery(self, attr, node=None, exists=False):
                return attr in owner.camera_markers | owner.accessory_markers

            def nodeType(self, path):
                return owner.types.get(path, "transform")

            def listRelatives(self, path, shapes=False, type=None, fullPath=False):
                return owner.meshes.get(path)

        self.patch(scene, "cmds", Cmds())

    def log(self, what):
        self.walks.append(what)

    def test_a_node_with_a_camera_marker_is_the_camera(self):
        self.camera_markers.add("camCtrl")
        self.assertEqual(scene._kind("|ctrl"), scene.CAMERA)

    def test_a_camera_aim_controller_is_the_camera(self):
        self.patch(cameraaim, "is_controller", lambda path: True)
        self.assertEqual(scene._kind("|aim"), scene.CAMERA)

    def test_a_weapon_in_a_hand_space_or_an_armour_piece_is_an_accessory(self):
        self.hand["|sword"] = "|hand_r"
        self.piece["|helmet"] = "|head"
        self.assertEqual(scene._kind("|sword"), scene.ACCESSORY)
        self.assertEqual(scene._kind("|helmet"), scene.ACCESSORY)

    def test_a_marked_weapon_or_armour_piece_or_a_weapon_aim_controller_is_an_accessory(self):
        self.accessory_markers.add("boneMark")
        self.assertEqual(scene._kind("|floor_spear"), scene.ACCESSORY)
        self.accessory_markers.clear()
        self.accessory_markers.add("armorMark")
        self.assertEqual(scene._kind("|piece"), scene.ACCESSORY)
        self.accessory_markers.clear()
        self.weapon_controllers.add("|aim")
        self.assertEqual(scene._kind("|aim"), scene.ACCESSORY)

    def test_a_node_with_a_mesh_shape_is_a_mesh_and_a_joint_never_is(self):
        self.meshes["|body"] = ["|body|bodyShape"]
        self.meshes["|joint"] = ["|joint|jointShape"]
        self.types["|joint"] = "joint"
        self.assertEqual(scene._kind("|body"), "mesh")
        self.assertEqual(scene._kind("|joint"), "joint")

    def test_any_other_node_is_its_type(self):
        self.types["|loc"] = "locator"
        self.assertEqual(scene._kind("|loc"), "locator")
        self.assertEqual(scene._kind("|grp"), "transform")

    def test_the_character_s_own_nodes_are_not_walked_for_a_weapon_or_an_armour_space(self):
        ref = character(namespace="Manny_Rig1")
        self.assertEqual(scene._kind("|G|Manny_Rig1:FKWrist_L", ref), "transform")
        self.assertEqual(self.walks, [])
        scene._kind("|G|elsewhere", ref)
        self.assertEqual(self.walks, ["hand_for", "bone_for"])


class BindOf(Patched):

    def test_a_joint_no_skin_holds_has_no_bind(self):
        class Cmds(object):
            def listConnections(self, plug, **kwargs):
                return None

        self.patch(scene, "cmds", Cmds())
        self.assertIsNone(scene._bind("|j"))

    def test_a_skinned_joint_s_bind_is_its_rest_world_as_floats(self):
        class Cmds(object):
            def listConnections(self, plug, source=False, destination=False, type=None):
                return ["skinCluster1"] if (plug, type) == ("|j.worldMatrix[0]", "skinCluster") else None

        self.patch(scene, "cmds", Cmds())
        self.patch(maya_retargetmode, "rest_world", lambda joint: list(trs((1, 2, 3))))
        self.assertEqual(scene._bind("|j"), [float(v) for v in trs((1, 2, 3))])


class Identity(Patched):

    def setUp(self):
        self.patch(scene, "_joints", lambda root: ["|r", "|r|a"])
        self.convention_of = []

        def convention_of(paths):
            self.convention_of.append(paths)
            return "ue"

        self.patch(skelmap, "convention_of", convention_of)

    def test_the_card_s_character_block_names_who_the_pose_was_made_on(self):
        ref = character(kind="skeleton", root="|Manny_Character|root", rig=None,
                        label="Manny UE5 [skeleton]", namespace="")
        self.assertEqual(scene.identity(ref), {
            "key": "Manny_Rig", "model": "Manny", "kind": "skeleton", "label": "Manny UE5 [skeleton]",
            "namespace": "", "root": "root", "convention": "ue", "rotation_only": False})
        self.assertEqual(self.convention_of, [["|r", "|r|a"]])

    def test_a_convention_already_read_is_not_read_again(self):
        ref = character(kind="skeleton", rig=None)
        self.assertEqual(scene.identity(ref, "mixamo")["convention"], "mixamo")
        self.assertEqual(self.convention_of, [])

    def test_a_rig_that_takes_rotations_only_says_so(self):
        for mode, expected in ((True, True), (0, False), ("rotation", True)):
            self.patch(maya_asretarget, "rotation_mode", lambda rig, mode=mode: mode)
            self.assertIs(scene.identity(character())["rotation_only"], expected)


class MembersOf(Patched):

    def setUp(self):
        self.ref = character(kind="skeleton", root="|Manny_Character|root", rig=None)
        self.calls = []
        self.patch(scene, "dag_object", lambda node: None if node == "bad" else "|" + node)
        self.patch(scene, "_kind", lambda path, ref=None: "joint" if path.startswith("|hand") else "mesh")
        self.patch(scene, "driven_bones", lambda ref, bones: self.driven)
        self.driven = None

        def members_from_selection(ref, selection, bones, limit=None):
            self.calls.append((selection, bones, limit))
            return ["picked"]

        self.patch(scene, "members_from_selection", members_from_selection)

    def test_the_kinds_are_read_from_the_scene_and_nodes_outside_the_dag_are_skipped(self):
        bones = {"root": {}}
        self.assertEqual(scene.members_of(self.ref, ["hand_l", "bad", "body"], bones), ["picked"])
        self.assertEqual(self.calls, [([("|hand_l", "joint"), ("|body", "mesh")], bones, None)])

    def test_a_part_rig_s_driven_bones_limit_the_members(self):
        self.driven = ["hand_l"]
        scene.members_of(self.ref, ["hand_l"], {"root": {}})
        self.assertEqual(self.calls[0][2], ["hand_l"])

    def test_the_skeleton_is_read_when_the_bones_are_not_given(self):
        read = []
        self.patch(scene, "skeleton", lambda ref: read.append(ref) or ({"read": {}}, "ue"))
        scene.members_of(self.ref, None)
        self.assertEqual(read, [self.ref])
        self.assertEqual(self.calls, [([], {"read": {}}, None)])


if __name__ == "__main__":
    unittest.main()

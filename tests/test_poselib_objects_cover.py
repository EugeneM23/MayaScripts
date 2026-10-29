"""The Pose Library's objects, the parts `test_poselib_objects` leaves out: reading an object's channels
(`shape_of`, `channel_names`, `values_of`, `pose_record`), setting them on a scene object (`plugs_of`),
finding a card's object again (`find_exact`, `find_owned`, `found_for`) and naming records (`names`).

The channel readers take their `cmds` as an argument and run on a small fake; the finders use the
module's own `cmds`, `maya_rigs` and `scene.is_body`, rebound for the test and restored by cleanup.
"""

import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

from maya_poselib import objects
from maya_poselib import scene


def ref(namespace="", root="|Char|root", kind="skeleton"):
    return scene.CharacterRef(kind, root, None, "Char", "Char", "Char", namespace)


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


class ShapeCmds(object):
    """`listRelatives(shapes=True)` and `getAttr(<shape>.intermediateObject)` of a few shapes."""

    def __init__(self, shapes=None, intermediate=(), broken=()):
        self.shapes = shapes
        self.intermediate = set(intermediate)
        self.broken = set(broken)

    def listRelatives(self, path, **kwargs):
        assert kwargs.get("shapes") and kwargs.get("fullPath")
        return self.shapes

    def getAttr(self, plug):
        node = plug.rsplit(".", 1)[0]
        if node in self.broken:
            raise RuntimeError("no such attribute")
        return node in self.intermediate


class ShapeOf(unittest.TestCase):

    def test_the_first_shape_that_is_not_intermediate_is_the_shape(self):
        fake = ShapeCmds(["|c|orig", "|c|shape", "|c|other"], intermediate=["|c|orig"])
        self.assertEqual(objects.shape_of("|c", fake), "|c|shape")

    def test_a_shape_that_cannot_be_read_is_skipped(self):
        fake = ShapeCmds(["|c|gone", "|c|shape"], broken=["|c|gone"])
        self.assertEqual(objects.shape_of("|c", fake), "|c|shape")

    def test_no_shapes_is_none(self):
        self.assertIsNone(objects.shape_of("|c", ShapeCmds(None)))
        self.assertIsNone(objects.shape_of("|c", ShapeCmds([])))

    def test_only_intermediate_shapes_is_none(self):
        fake = ShapeCmds(["|c|orig"], intermediate=["|c|orig"])
        self.assertIsNone(objects.shape_of("|c", fake))


class ChannelCmds(object):
    """`listAttr` and `getAttr` of one node: channels is the keyable scalar unlocked list,
    `values` {attr: what getAttr answers}; an attr in `broken` raises, `channels` None raises."""

    def __init__(self, channels, values=None, broken=(), shape=None):
        self.channels = channels
        self.values = values or {}
        self.broken = set(broken)
        self.shape = shape
        self.asked = []

    def listAttr(self, node, **kwargs):
        self.asked.append(kwargs)
        if self.channels is None:
            raise RuntimeError("no such node")
        return self.channels

    def getAttr(self, plug):
        attr = plug.split(".", 1)[1]
        if attr in self.broken:
            raise RuntimeError("cannot read")
        return self.values[attr]

    def listRelatives(self, path, **kwargs):
        return [self.shape] if self.shape else None


class ChannelNames(unittest.TestCase):

    def test_the_keyable_scalar_unlocked_attributes_are_asked_for(self):
        fake = ChannelCmds(["translateX", "visibility"])
        self.assertEqual(objects.channel_names("|n", fake), ["translateX", "visibility"])
        self.assertEqual(fake.asked, [{"keyable": True, "scalar": True, "unlocked": True}])

    def test_a_node_with_none_gives_an_empty_list(self):
        self.assertEqual(objects.channel_names("|n", ChannelCmds([])), [])

    def test_a_node_that_is_gone_gives_an_empty_list(self):
        self.assertEqual(objects.channel_names("|n", ChannelCmds(None)), [])


class ValuesOf(unittest.TestCase):

    def test_a_number_a_bool_and_an_int_become_floats(self):
        fake = ChannelCmds(["tx", "visibility", "rotateOrder"],
                           {"tx": 2.5, "visibility": True, "rotateOrder": 3})
        out = objects.values_of("|n", fake)
        self.assertEqual(out, {"tx": 2.5, "visibility": 1.0, "rotateOrder": 3.0})
        self.assertTrue(all(isinstance(v, float) for v in out.values()))

    def test_a_channel_that_answers_no_number_is_left_out(self):
        fake = ChannelCmds(["tx", "label", "compound"],
                           {"tx": 1.0, "label": "hello", "compound": [(1.0, 2.0, 3.0)]})
        self.assertEqual(objects.values_of("|n", fake), {"tx": 1.0})

    def test_a_channel_that_cannot_be_read_is_left_out(self):
        fake = ChannelCmds(["tx", "ty"], {"tx": 1.0, "ty": 2.0}, broken=["tx"])
        self.assertEqual(objects.values_of("|n", fake), {"ty": 2.0})

    def test_a_node_with_no_channels_has_no_values(self):
        self.assertEqual(objects.values_of("|n", ChannelCmds(None)), {})


class PoseRecord(unittest.TestCase):

    def test_the_record_holds_the_name_the_path_the_transform_and_the_shape(self):
        fake = ChannelCmds(["tx"], {"tx": 4.0, "intermediateObject": False})
        fake.shape = "|ns:cam|ns:camShape"
        record = objects.pose_record("|grp|ns:cam", own=1, cmds=fake)
        self.assertEqual(record["name"], "cam")
        self.assertEqual(record["path"], "|grp|ns:cam")
        self.assertEqual(record["attrs"], {"tx": 4.0})
        self.assertEqual(record["shape"], {"tx": 4.0})
        self.assertIs(record["own"], True)

    def test_an_object_without_a_shape_has_an_empty_shape_record(self):
        fake = ChannelCmds(["tx"], {"tx": 4.0, "intermediateObject": False})
        record = objects.pose_record("|prop", cmds=fake)
        self.assertEqual(record["shape"], {})
        self.assertIs(record["own"], False)


class PlugCmds(object):
    """`attributeQuery(exists)` of a few nodes and the shape of a transform."""

    def __init__(self, attrs, shape=None):
        self.attrs = attrs
        self.shape = shape

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.attrs.get(node, ())

    def listRelatives(self, path, **kwargs):
        return [self.shape] if self.shape else None

    def getAttr(self, plug):
        return False


class PlugsOf(unittest.TestCase):

    def test_the_transform_s_channels_go_on_the_object_and_the_shape_s_on_its_shape(self):
        record = {"attrs": {"tx": 1.0, "ty": 2.0}, "shape": {"focalLength": 35.0}}
        fake = PlugCmds({"|cam": ["tx", "ty"], "|cam|camShape": ["focalLength"]}, "|cam|camShape")
        plugs, missing = objects.plugs_of(record, "|cam", fake)
        self.assertEqual(list(plugs.items()), [("|cam.tx", 1.0), ("|cam.ty", 2.0),
                                              ("|cam|camShape.focalLength", 35.0)])
        self.assertEqual(missing, [])

    def test_a_channel_the_object_lacks_is_named_by_leaf_and_attribute(self):
        record = {"attrs": {"tx": 1.0, "gone": 2.0}}
        plugs, missing = objects.plugs_of(record, "|shot:cam", PlugCmds({"|shot:cam": ["tx"]}))
        self.assertEqual(list(plugs), ["|shot:cam.tx"])
        self.assertEqual(missing, ["cam.gone"])

    def test_a_shape_channel_the_shape_lacks_is_missing(self):
        record = {"shape": {"focalLength": 35.0, "gone": 1.0}}
        fake = PlugCmds({"|cam|camShape": ["focalLength"]}, "|cam|camShape")
        plugs, missing = objects.plugs_of(record, "|cam", fake)
        self.assertEqual(list(plugs), ["|cam|camShape.focalLength"])
        self.assertEqual(missing, ["cam.gone"])

    def test_every_shape_channel_is_missing_when_the_object_has_no_shape(self):
        record = {"shape": {"focalLength": 35.0}}
        plugs, missing = objects.plugs_of(record, "|prop", PlugCmds({}))
        self.assertEqual(len(plugs), 0)
        self.assertEqual(missing, ["prop.focalLength"])

    def test_a_record_with_no_channels_sets_nothing(self):
        plugs, missing = objects.plugs_of({"attrs": None}, "|prop", PlugCmds({}))
        self.assertEqual((len(plugs), missing), (0, []))


class SceneCmds(object):
    """`ls` and `listRelatives` of a scene: `ls_answers` {(name, type): [paths]}."""

    def __init__(self, ls_answers=None, descendants=None):
        self.ls_answers = ls_answers or {}
        self.descendants = descendants
        self.ls_calls = []

    def ls(self, name, long=False, type=None):
        self.ls_calls.append((name, type))
        return self.ls_answers.get((name, type))

    def listRelatives(self, group, **kwargs):
        return self.descendants


class FindExact(Patched):

    def test_a_record_with_no_path_finds_nothing(self):
        self.patch(objects, "cmds", SceneCmds())
        self.assertIsNone(objects.find_exact({"name": "cam"}))
        self.assertIsNone(objects.find_exact({"path": ""}))

    def test_one_object_at_the_path_is_found(self):
        self.patch(objects, "cmds", SceneCmds({("|camera1", None): ["|camera1"]}))
        self.assertEqual(objects.find_exact({"path": "|camera1"}), "|camera1")

    def test_no_object_or_two_is_none(self):
        self.patch(objects, "cmds", SceneCmds({("|a", None): ["|a", "|b|a"]}))
        self.assertIsNone(objects.find_exact({"path": "|a"}))
        self.assertIsNone(objects.find_exact({"path": "|nope"}))


class Rigs(object):
    def __init__(self, group):
        self.group = group
        self.asked = []

    def group_of(self, root):
        self.asked.append(root)
        return self.group


class FindOwned(Patched):

    def setUp(self):
        self.body = set()
        self.patch(scene, "is_body", lambda path, character: path in self.body)

    def test_a_record_without_a_name_or_a_character_finds_nothing(self):
        self.patch(objects, "cmds", SceneCmds())
        self.assertIsNone(objects.find_owned({"name": ""}, ref("rig1")))
        self.assertIsNone(objects.find_owned({"name": "cam"}, None))

    def test_a_rig_is_searched_by_namespace_and_name_among_transforms(self):
        fake = SceneCmds({("Rig2:SceneSetup_camera", "transform"): ["|G|Rig2:SceneSetup_camera"]})
        self.patch(objects, "cmds", fake)
        found = objects.find_owned({"name": "SceneSetup_camera"}, ref("Rig2"))
        self.assertEqual(found, "|G|Rig2:SceneSetup_camera")
        self.assertEqual(fake.ls_calls, [("Rig2:SceneSetup_camera", "transform")])

    def test_two_matches_are_none(self):
        fake = SceneCmds({("Rig2:cam", "transform"): ["|A|Rig2:cam", "|B|Rig2:cam"]})
        self.patch(objects, "cmds", fake)
        self.assertIsNone(objects.find_owned({"name": "cam"}, ref("Rig2")))

    def test_the_body_is_not_an_object(self):
        fake = SceneCmds({("Rig2:cam", "transform"): ["|A|Rig2:cam"]})
        self.patch(objects, "cmds", fake)
        self.body.add("|A|Rig2:cam")
        self.assertIsNone(objects.find_owned({"name": "cam"}, ref("Rig2")))

    def test_a_skeleton_with_no_namespace_is_searched_under_its_character_group(self):
        rigs = Rigs("|Creep_Character")
        self.patch(objects, "maya_rigs", rigs)
        self.patch(objects, "cmds", SceneCmds(descendants=["|Creep_Character|Armature",
                                                           "|Creep_Character|sub|prop"]))
        found = objects.find_owned({"name": "prop"}, ref("", root="|Creep_Character|root"))
        self.assertEqual(found, "|Creep_Character|sub|prop")
        self.assertEqual(rigs.asked, ["|Creep_Character|root"])

    def test_two_transforms_of_that_name_under_the_group_are_none(self):
        self.patch(objects, "maya_rigs", Rigs("|Creep_Character"))
        self.patch(objects, "cmds", SceneCmds(descendants=["|Creep_Character|a|prop",
                                                           "|Creep_Character|b|prop"]))
        self.assertIsNone(objects.find_owned({"name": "prop"}, ref("")))

    def test_a_skeleton_with_no_character_group_finds_nothing(self):
        self.patch(objects, "maya_rigs", Rigs(None))
        self.patch(objects, "cmds", SceneCmds(descendants=["|prop"]))
        self.assertIsNone(objects.find_owned({"name": "prop"}, ref("")))


class FoundFor(Patched):

    def setUp(self):
        self.owned_calls = []
        self.exact_calls = []

        def find_owned(record, target):
            self.owned_calls.append((record["name"], target.namespace))
            return {"Rig1": "|A|Rig1:cam", "Rig2": "|A|Rig1:cam", "Rig3": None}[target.namespace]

        def find_exact(record):
            self.exact_calls.append(record["name"])
            return record.get("path") if record["name"] != "gone" else None

        self.patch(objects, "find_owned", find_owned)
        self.patch(objects, "find_exact", find_exact)

    def test_selected_only_asks_the_scene_for_nothing(self):
        found = objects.found_for([{"name": "cam", "own": True}], [ref("Rig1")], only=True)
        self.assertEqual(found, {})
        self.assertEqual(self.owned_calls + self.exact_calls, [])

    def test_an_own_record_is_found_in_each_target_once(self):
        records = [{"name": "cam", "own": True}]
        found = objects.found_for(records, [ref("Rig1"), ref("Rig2"), ref("Rig3")])
        self.assertEqual(found, {0: ["|A|Rig1:cam"]})
        self.assertEqual([ns for _n, ns in self.owned_calls], ["Rig1", "Rig2", "Rig3"])
        self.assertEqual(self.exact_calls, [])

    def test_any_other_record_is_found_by_its_exact_path_and_never_by_target(self):
        records = [{"name": "prop", "path": "|prop"}, {"name": "gone", "path": "|gone"}]
        found = objects.found_for(records, [ref("Rig1")])
        self.assertEqual(found, {0: ["|prop"]})
        self.assertEqual(self.owned_calls, [])

    def test_the_index_is_the_record_s_place_among_all_records(self):
        records = [{"name": "gone", "path": "|gone"}, {"name": "cam", "own": True}]
        self.assertEqual(objects.found_for(records, [ref("Rig1")]), {1: ["|A|Rig1:cam"]})

    def test_no_records_and_no_targets_find_nothing(self):
        self.assertEqual(objects.found_for(None, None), {})
        self.assertEqual(objects.found_for([{"name": "cam", "own": True}], None), {})


class Names(unittest.TestCase):

    def test_a_record_is_named_by_its_name_else_by_the_leaf_of_its_path(self):
        records = [{"name": "camera1", "path": "|x"}, {"path": "|grp|ns:prop"}, {}]
        self.assertEqual(objects.names(records), ["camera1", "prop", "?"])


if __name__ == "__main__":
    unittest.main()

"""maya_uebridge.nativeimport - the scene half of keeping a clip in its own skeleton (the Auto card,
2026-10-02): the meshes it brought, whether something above the root moves, standing the root on a
floor point (its keys, else its values, in its parent's space), merging the clip's namespaces into
the root (or the active tab), and `keep` as a whole - its group, colour, record, label and line.
On a fake scene; the pure halves are in tests/test_uebridge_autoimport.py and the live road is
docs/superpowers/plans/verify_auto_character.py."""

import contextlib
import io
import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import nativeimport as ni  # noqa: E402

IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
#  the world-inverse of a parent turned +90 deg about Y: world +X is its local +Z
TURNED_Y = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def _flat(args):
    out = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            out.extend(arg)
        elif arg is not None:
            out.append(arg)
    return out


class Scene(object):
    """What nativeimport asks of Maya, kept as data."""

    def __init__(self):
        self.uuid = {}               # path: uuid
        self.meshes = {}             # shape: (parent or None, vertex count or an exception)
        self.joints = set()
        self.assemblies = []
        self.curves = {}             # plug: curve
        self.types = {}              # curve: node type
        self.counts = {}             # curve: key count
        self.attrs = {}              # plug: value
        self.unsettable = set()
        self.matrices = {}           # parent: world-inverse (flat)
        self.parents = {}            # path: parent path
        self.namespaces = set()
        self.nested = {}             # ":ns": [nested namespaces]
        self.contents = {}           # ns: [nodes]
        self.calls = []
        self.refuse_removal = set()

    def ls(self, *args, **kw):
        items = _flat(args)
        if kw.get("assemblies"):
            return list(self.assemblies)
        if kw.get("uuid"):
            return [self.uuid[i] for i in items if i in self.uuid]
        if kw.get("type") == "mesh":
            return [i for i in items if i in self.meshes]
        if kw.get("type") == "joint":
            return [i for i in items if i in self.joints]
        if kw.get("long"):
            by_uuid = dict((v, k) for k, v in self.uuid.items())
            return [by_uuid.get(i, i) for i in items if i in by_uuid or i in self.uuid]
        return items

    def listRelatives(self, node, parent=False, fullPath=False):  # noqa: N802
        if node in self.meshes:
            owner = self.meshes[node][0]
            return [owner] if owner else []
        found = self.parents.get(node)
        return [found] if found else None

    def polyEvaluate(self, shape, vertex=False):                # noqa: N802
        count = self.meshes[shape][1]
        if isinstance(count, Exception):
            raise count
        return count

    def listConnections(self, plug, source=False, destination=False, type=None):  # noqa: N802,A002
        curve = self.curves.get(plug)
        return [curve] if curve else []

    def nodeType(self, node):                                   # noqa: N802
        return self.types[node]

    def getAttr(self, plug, time=None, settable=False):         # noqa: N802
        if settable:
            return plug not in self.unsettable
        if plug.endswith(".worldInverseMatrix[0]"):
            self.calls.append(("matrix at", plug, time))
            return list(self.matrices.get(plug.rsplit(".", 1)[0], IDENTITY))
        return self.attrs.get(plug, 0.0)

    def setAttr(self, plug, value):                             # noqa: N802
        self.attrs[plug] = value
        self.calls.append(("setAttr", plug, value))

    def keyframe(self, curve, query=False, keyframeCount=False, edit=False, relative=False,
                 valueChange=None, index=None):
        if query:
            return self.counts.get(curve, 0)
        self.calls.append(("keys moved", curve, valueChange, index))

    def namespaceInfo(self, name, listOnlyNamespaces=False, listOnlyDependencyNodes=False,  # noqa: N802
                      recurse=False, dagPath=False):
        if listOnlyNamespaces:
            return list(self.nested.get(name, []))
        return list(self.contents.get(name, []))

    def namespace(self, exists=None, removeNamespace=None, **kw):
        if exists is not None:
            return exists.lstrip(":") in self.namespaces
        name = removeNamespace.lstrip(":")
        if name in self.refuse_removal:
            raise RuntimeError("namespace is locked")
        self.namespaces.discard(name)
        self.calls.append(("merged", name, sorted(k for k in kw if kw[k])))


class Base(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()
        self.patch(ni, "cmds", self.scene)

    def patch(self, owner, name, value):
        saved = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, saved)

    def curve(self, plug, kind="animCurveTL", keys=3):
        name = plug.replace("|", "_").replace(".", "_")
        self.scene.curves[plug] = name
        self.scene.types[name] = kind
        self.scene.counts[name] = keys
        return name


class Names(Base):

    def test_a_leaf_is_the_last_part_without_namespaces(self):
        self.assertEqual(ni.leaf("|clip:Armature|clip:mixamorig:Hips"), "Hips")
        self.assertEqual(ni.leaf("root"), "root")

    def test_a_path_s_namespace_is_its_leaf_s(self):
        self.assertEqual(ni._namespace_of("|grp|clip:mixamorig:Hips"), "clip:mixamorig")
        self.assertEqual(ni._namespace_of("|root"), "")
        self.assertEqual(ni._namespace_of(":clip:root"), "clip")

    def test_in_a_namespace_is_in_it_or_nested_in_it_never_beside_it(self):
        self.assertTrue(ni._in("clip", "|clip:root"))
        self.assertTrue(ni._in("clip", "|clip:mixamorig:Hips"))
        self.assertFalse(ni._in("clip", "|clip2:root"))
        self.assertFalse(ni._in("clip", "|root"))

    def test_uuid_and_back(self):
        self.scene.uuid["|clip:root"] = "U-ROOT"
        self.assertEqual(ni._uuid("|clip:root"), "U-ROOT")
        self.assertIsNone(ni._uuid("|gone"))
        self.assertEqual(ni._long("U-ROOT"), "|clip:root")
        self.assertIsNone(ni._long(None))
        self.assertIsNone(ni._long("U-GONE"))


class Meshes(Base):

    def test_the_meshes_with_their_owner_and_vertex_count(self):
        self.scene.meshes.update({
            "|clip:Body|clip:BodyShape": ("|clip:Body", 40000),
            "|clip:Hat|clip:HatShape": ("|clip:Hat", RuntimeError("not a poly")),
            "|clip:orphanShape": (None, 10)})
        found = ni._meshes(["|clip:Body|clip:BodyShape", "|clip:Hat|clip:HatShape",
                            "|clip:orphanShape", "|clip:root"])
        self.assertEqual(found, [("Body", 40000), ("Hat", 0)])

    def test_the_group_is_named_for_the_largest(self):
        self.scene.meshes.update({"|a:HatShape": ("|a:Hat", 120), "|a:BodyShape": ("|a:Body", 9)})
        self.assertEqual(ni.native_base(ni._meshes(["|a:HatShape", "|a:BodyShape"]), "a",
                                        "root"), "Hat")


class Moving(Base):

    def test_a_time_curve_on_a_transform_channel_moves_it(self):
        self.curve("|Armature.rotateY", "animCurveTA")
        self.assertTrue(ni._moves("|Armature"))

    def test_a_driven_key_does_not(self):
        self.curve("|Armature.translateX", "animCurveUL")
        self.assertFalse(ni._moves("|Armature"))
        self.assertFalse(ni._moves("|other"))

    def test_the_first_moving_ancestor_from_the_top(self):
        self.curve("|grp|Armature.scaleX", "animCurveTU")
        self.assertEqual(ni.moving_ancestor("|grp|Armature|root"), "|grp|Armature")
        self.assertIsNone(ni.moving_ancestor("|root"))
        self.curve("|grp.translateZ")
        self.assertEqual(ni.moving_ancestor("|grp|Armature|root"), "|grp")

    def test_the_curve_on_a_plug(self):
        name = self.curve("|root.translateX")
        self.assertEqual(ni._curve_on("|root.translateX"), name)
        self.assertIsNone(ni._curve_on("|root.translateY"))


class MoveRoot(Base):

    def test_keyed_channels_move_their_keys_unkeyed_their_values(self):
        tx = self.curve("|clip:root.translateX", keys=40)
        self.scene.attrs["|clip:root.translateZ"] = 7.0
        self.assertEqual(ni.move_root("|clip:root", (120.0, 0.0, -36.0)), "")
        self.assertIn(("keys moved", tx, 120.0, (0, 39)), self.scene.calls)
        self.assertEqual(self.scene.attrs["|clip:root.translateZ"], -29.0)
        self.assertFalse([c for c in self.scene.calls if c[1] == "|clip:root.translateY"])

    def test_a_curve_with_no_keys_moves_the_value(self):
        self.curve("|clip:root.translateX", keys=0)
        self.scene.attrs["|clip:root.translateX"] = 2.0
        ni.move_root("|clip:root", (3.0, 0.0, 0.0))
        self.assertEqual(self.scene.attrs["|clip:root.translateX"], 5.0)

    def test_the_move_is_read_in_the_parent_s_space_at_the_first_frame(self):
        self.scene.parents["|clip:Armature|clip:root"] = "|clip:Armature"
        self.scene.matrices["|clip:Armature"] = TURNED_Y
        tz = self.curve("|clip:Armature|clip:root.translateZ")
        ni.move_root("|clip:Armature|clip:root", (10.0, 0.0, 0.0), frame=4.0)
        self.assertIn(("matrix at", "|clip:Armature.worldInverseMatrix[0]", 4.0),
                      self.scene.calls)
        self.assertIn(("keys moved", tz, 10.0, (0, 2)), self.scene.calls)

    def test_a_channel_that_cannot_move_is_named(self):
        self.scene.unsettable.add("|clip:root.translateZ")
        note = ni.move_root("|clip:root", (1.0, 0.0, 2.0))
        self.assertEqual(note, "the root's translateZ could not move - it stands where the clip "
                               "has it")
        self.assertEqual(self.scene.attrs["|clip:root.translateX"], 1.0)

    def test_a_root_under_a_moving_ancestor_stays_and_says_why(self):
        self.curve("|clip:Armature.rotateX", "animCurveTA")
        note = ni.move_root("|clip:Armature|clip:root", (50.0, 0.0, 0.0))
        self.assertEqual(note, "its root rides Armature, which the clip animates - it stands "
                               "where the clip has it")
        self.assertEqual([c for c in self.scene.calls if c[0] in ("setAttr", "keys moved")], [])


class Merge(Base):

    def setUp(self):
        Base.setUp(self)
        from maya_scenetabs import scope
        self.scope = scope
        self.homed = []
        self.patch(scope, "home_namespace",
                   lambda name, cmds=None: self.homed.append(name) or name.lstrip(":"))

    def test_a_chain_of_namespaces_merges_into_the_root_deepest_first(self):
        self.scene.namespaces.update({"clip", "clip:mixamorig"})
        self.scene.nested[":clip"] = [":clip:mixamorig"]
        self.assertEqual(ni.merge_into_root("clip"), "")
        merged = [c for c in self.scene.calls if c[0] == "merged"]
        self.assertEqual(merged, [("merged", "clip:mixamorig", ["mergeNamespaceWithRoot"]),
                                  ("merged", "clip", ["mergeNamespaceWithRoot"])])
        self.assertEqual(self.homed, ["clip"])

    def test_sibling_characters_keep_their_own_namespaces(self):
        self.scene.namespaces.update({"clip", "clip:Hero", "clip:Enemy"})
        self.scene.nested[":clip"] = ["clip:Hero", "clip:Enemy"]
        ni.merge_into_root("clip")
        merged = [c[1] for c in self.scene.calls if c[0] == "merged"]
        self.assertEqual(merged, ["clip"])

    def test_with_scene_tabs_on_it_merges_into_the_tab(self):
        self.patch(self.scope, "home_namespace", lambda name, cmds=None: "tab_a:clip")
        self.scene.namespaces.update({"tab_a:clip"})
        ni.merge_into_root("clip")
        merged = [c for c in self.scene.calls if c[0] == "merged"]
        self.assertEqual(merged, [("merged", "tab_a:clip", ["mergeNamespaceWithParent"])])

    def test_a_namespace_that_will_not_go_is_named(self):
        self.scene.namespaces.update({"clip", "clip:mixamorig"})
        self.scene.nested[":clip"] = ["clip:mixamorig"]
        self.scene.refuse_removal.add("clip:mixamorig")
        with contextlib.redirect_stderr(io.StringIO()):
            note = ni.merge_into_root("clip")
        self.assertEqual(note, "names kept in clip:mixamorig")

    def test_a_tab_move_that_fails_is_said_and_merged_into_the_root(self):
        def broken(name, cmds=None):
            raise RuntimeError("no tab")
        self.patch(self.scope, "home_namespace", broken)
        self.scene.namespaces.update({"clip"})
        self.scene.refuse_removal.add("clip")
        with contextlib.redirect_stderr(io.StringIO()):
            note = ni.merge_into_root(":clip")
        self.assertEqual(note, "clip not moved into the scene tab; names kept in clip")

    def test_a_namespace_already_gone_is_skipped(self):
        ni.merge_into_root("clip")
        self.assertEqual([c for c in self.scene.calls if c[0] == "merged"], [])


class Keep(Base):
    """`keep` as a whole, every module it reaches stubbed."""

    def setUp(self):
        Base.setUp(self)
        from maya_scenesetup import character, chargroup, cliplabel, colour, deletion
        from maya_uebridge import rigimport
        self.did = []
        s = self.scene
        s.uuid.update({"|clip:root": "U1", "|clip:root|clip:pelvis": "U2",
                       "|clip:Body": "U3", "|clip:Body|clip:BodyShape": "U4"})
        s.joints.update({"|clip:root", "|clip:root|clip:pelvis"})
        s.meshes["|clip:Body|clip:BodyShape"] = ("|clip:Body", 20000)
        s.assemblies[:] = ["|clip:root", "|clip:Body", "|persp", "|clip2:root"]
        s.contents["clip"] = list(s.uuid)
        s.namespaces.add("clip")

        @contextlib.contextmanager
        def unrecorded():
            self.did.append("unrecorded")
            yield
        self.patch(character, "_unrecorded", unrecorded)
        self.patch(chargroup, "make", lambda base, label, root, tops: self.did.append(
            ("group", base, label, root, list(tops))))
        self.patch(cliplabel, "label_skeleton", lambda root, name: self.did.append(
            ("label", root, name)))
        self.patch(colour, "free_colour",
                   lambda: types.SimpleNamespace(rgb=(0.1, 0.2, 0.3)))
        self.patch(colour, "paint_nodes", lambda nodes, rgb, key: self.did.append(
            ("paint", sorted(nodes), rgb, key)))
        self.patch(deletion, "record_import", lambda root, uuids, label: self.did.append(
            ("record", root, sorted(uuids), label)))
        self.patch(rigimport, "root_at", lambda source, frame=None: (10.0, 0.0, 5.0))
        self.patch(ni, "merge_into_root", lambda namespace: self.did.append(
            ("merge", namespace)) or "")
        self.moved = []
        self.patch(ni, "move_root", lambda root, delta, frame=None: (
            self.moved.append((root, delta, frame)) or ""))
        self.modules = (character, chargroup, colour, deletion)

    def keep(self, point=None, why=""):
        return ni.keep("clip", {"start": 0.0, "end": 48.0}, "|clip:root", "Ability_Q", point,
                       why)

    def test_kept_grouped_painted_recorded_and_labelled(self):
        line, failure, base = self.keep(why="no skeleton of ours")
        self.assertEqual((failure, base), ("", "Body"))
        self.assertEqual(line, "Ability_Q: no skeleton of ours - in its own skeleton Body: "
                               "2 joints, 1 mesh, frames 0-48")
        self.assertEqual(self.did[0], "unrecorded")
        self.assertIn(("group", "Body", "Body [own skeleton]", "|clip:root",
                       ["|clip:root", "|clip:Body"]), self.did)
        self.assertIn(("merge", "clip"), self.did)
        paint = [d for d in self.did if d[0] == "paint"][0]
        self.assertEqual((paint[2], paint[3]), ((0.1, 0.2, 0.3), "Body"))
        self.assertEqual(paint[1], sorted(self.scene.uuid))
        self.assertIn(("record", "|clip:root", ["U1", "U2", "U3", "U4"], "Body [own skeleton]"),
                      self.did)
        self.assertEqual(self.did[-1], ("label", "|clip:root", "Ability_Q"))
        self.assertEqual(self.moved, [])                  # no point: where the clip has it

    def test_a_drop_stands_the_root_on_the_point(self):
        line, _failure, _base = self.keep(point=(120.5, 0.0, -36.25))
        self.assertEqual(self.moved, [("|clip:root", (110.5, 0.0, -41.25), 0.0)])
        self.assertTrue(line.endswith("  |  standing at floor (120, -36)"), line)

    def test_a_root_that_could_not_move_says_so_and_is_not_placed(self):
        self.patch(ni, "move_root", lambda root, delta, frame=None: "the root's translateX "
                                                                     "could not move")
        line, _f, _b = self.keep(point=(0.0, 0.0, 0.0))
        self.assertNotIn("standing at floor", line)
        self.assertTrue(line.endswith("  |  the root's translateX could not move"), line)

    def test_no_mesh_names_the_group_for_the_namespace(self):
        self.scene.meshes.clear()
        line, _f, base = self.keep()
        self.assertEqual(base, "clip")
        self.assertIn("in its own skeleton clip: 2 joints, 0 meshes", line)

    def test_a_group_that_fails_paint_that_fails_and_a_merge_note(self):
        character, chargroup, colour, deletion = self.modules

        def broken(*args, **kw):
            raise RuntimeError("Armature is locked")
        self.patch(chargroup, "make", broken)
        self.patch(colour, "paint_nodes", broken)
        self.patch(deletion, "record_import", broken)
        self.patch(ni, "merge_into_root", lambda namespace: "names kept in clip")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            line, failure, _base = self.keep()
        self.assertEqual(failure, "")
        self.assertIn("no character group (Armature is locked)", line)
        self.assertIn("names kept in clip", line)
        self.assertIn("not painted", line)

    def test_a_root_gone_keeps_nothing(self):
        self.scene.uuid.pop("|clip:root")
        line, failure, base = self.keep(point=(1.0, 0.0, 1.0))
        self.assertEqual((line, base), ("", ""))
        self.assertEqual(failure, "Ability_Q: the clip's root is gone")
        self.assertEqual(self.did, [])


if __name__ == "__main__":
    unittest.main()

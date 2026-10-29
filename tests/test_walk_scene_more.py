"""maya_walk.scene with no Maya: the walks folder, saving and reading walks (files, cards, a skeleton's own cycle),
load_walk's cache, the walker marker and its edits, the keys written in place or recorded, the source keys kept and
given back, poses, animate / apply's wiring and line - on a fake cmds holding a small scene (a DAG, attributes,
connections, curves) and a fake OpenMaya for the curves' keys. The synthetic walker of tests/test_walkmodel.py is
the cycle wherever a real walk is needed."""

import gzip
import json
import math
import os
import shutil
import sys
import tempfile
import types
import unittest

import numpy as np

from tests import test_walkmodel as tw
from tests import test_walkclean as tc

wm = tw.wm
scene = tw.load("scene")
wf = tw.load("walkfile")
wt = tw.load("walktarget")
wp = tw.load("walkpose")
wc = tw.load("clean")

from maya_walk import cards as wcards       # noqa: E402
from maya_walk import meanpose as mp        # noqa: E402
from maya_walk import keyposes as kp        # noqa: E402
from maya_poselib import store              # noqa: E402
import maya.api.OpenMaya as real_om         # noqa: E402

_MISSING = object()


# ---------------------------------------------------------------------------------------------- the fake scene

class FakeCmds(object):
    """Just enough of maya.cmds for maya_walk.scene: nodes by long path (DAG) or name (DG), their attributes,
    connections dest -> source, animation curves' keys, world matrices by time, the selection and the undo state."""

    def __init__(self):
        self.nodes = {}                   # name -> {"type", "attrs", "uuid"}
        self.conn = {}                    # dest plug -> source plug
        self.curves = {}                  # curve node -> [[time, value], ...]
        self.worlds = {}                  # path -> {time: 16 floats}
        self.locks = set()
        self.referenced = set()
        self.selection = []
        self.unit = "ntsc"
        self.linear = "cm"
        self.up = "y"
        self.scene_file = ""
        self.undo = True
        self.undo_calls = []
        self.vars = {}
        self.app_dir = "C:/fake/maya/"
        self.time = 0.0
        self.set_values = {}
        self.deleted = []
        self._uuid = 0

    # ---- building
    def add(self, name, kind, **attrs):
        self._uuid += 1
        self.nodes[name] = {"type": kind, "attrs": dict(attrs), "uuid": "UUID-%03d" % self._uuid}
        return name

    def joint(self, path, rotate=(0.0, 0.0, 0.0), **attrs):
        return self.add(path, "joint", rotate=tuple(rotate), jointOrient=(0.0, 0.0, 0.0),
                        rotateAxis=(0.0, 0.0, 0.0), rotateOrder=0, **attrs)

    def curve(self, name, keys, kind="animCurveTL"):
        self.add(name, kind)
        self.curves[name] = [list(k) for k in keys]
        return name

    def key(self, plug, keys, kind="animCurveTL"):
        name = self.curve(plug.split("|")[-1].replace(".", "_"), keys, kind)
        self.conn[plug] = name + ".output"
        return name

    # ---- lookups
    def resolve(self, name):
        if name is None:
            return None
        if name in self.nodes:
            return name
        for path, node in self.nodes.items():
            if node["uuid"] == name:
                return path
        found = [p for p in self.nodes if p.rsplit("|", 1)[-1] == name]
        return found[0] if len(found) == 1 else None

    def _split(self, plug):
        node, attr = plug.split(".", 1)
        return self.resolve(node) or node, attr

    def ls(self, *args, **kw):
        if kw.get("selection"):
            return list(self.selection)
        names = []
        for arg in args:
            names.extend(arg if isinstance(arg, (list, tuple)) else [arg])
        kind = kw.get("type")
        if names and isinstance(names[0], str) and names[0].startswith("*."):
            attr = names[0][2:]
            return [p for p, n in self.nodes.items() if attr in n["attrs"] and (not kind or n["type"] == kind)]
        if not names:
            return [p for p, n in self.nodes.items() if not kind or n["type"] == kind]
        out = []
        for name in names:
            path = self.resolve(name)
            if path is None:
                continue
            out.append(self.nodes[path]["uuid"] if kw.get("uuid") else path)
        return out

    def objExists(self, name):
        return self.resolve(name) is not None

    def nodeType(self, name):
        return self.nodes[self.resolve(name)]["type"]

    def listRelatives(self, path, parent=False, allDescendents=False, type=None, fullPath=False, shapes=False,
                      noIntermediate=False):
        path = self.resolve(path) or path
        if parent:
            above = path.rsplit("|", 1)[0]
            return [above] if above in self.nodes else None
        if allDescendents:
            found = [p for p, n in self.nodes.items() if p.startswith(path + "|") and (not type or n["type"] == type)]
            return found or None
        if shapes:
            found = [p for p, n in self.nodes.items() if p.rsplit("|", 1)[0] == path and n["type"] == "mesh"]
            return found or None
        return None

    def listHistory(self, shape, pruneDagObjects=False):
        return list(self.nodes[shape]["attrs"].get("history", []))

    def skinCluster(self, skin, query=False, influence=False):
        return list(self.nodes[skin]["attrs"].get("influences", []))

    def attributeQuery(self, attr, node=None, exists=False):
        path = self.resolve(node)
        return path is not None and attr in self.nodes[path]["attrs"]

    def getAttr(self, plug, time=None, lock=False, **kw):
        if lock:
            return plug in self.locks
        node, attr = self._split(plug)
        if attr == "worldMatrix[0]":
            table = self.worlds.get(node)
            if table is None:                                    # a group standing at the origin
                return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
            return list(table[self.time if time is None else time])
        value = self.nodes[node]["attrs"][attr]
        if attr in ("rotate", "jointOrient", "rotateAxis"):
            return [tuple(value)]
        return value

    def setAttr(self, plug, *values, **kw):
        if "lock" in kw:
            (self.locks.add if kw["lock"] else self.locks.discard)(plug)
            return
        node, attr = self._split(plug)
        self.set_values[plug] = values[0]
        if node in self.nodes:
            self.nodes[node]["attrs"][attr] = values[0]

    def addAttr(self, node, longName=None, dataType=None, **kw):
        self.nodes[self.resolve(node)]["attrs"][longName] = ""

    def deleteAttr(self, plug):
        node, attr = self._split(plug)
        del self.nodes[node]["attrs"][attr]

    def keyframe(self, target, attribute=None, query=False, timeChange=False, valueChange=False,
                 keyframeCount=False):
        if target in self.curves:
            keys = self.curves[target]
        else:
            attrs = attribute if isinstance(attribute, (list, tuple)) else [attribute]
            keys = []
            for attr in attrs:
                source = self.conn.get(target + "." + attr)
                if source and source.split(".")[0] in self.curves:
                    keys.extend(self.curves[source.split(".")[0]])
        if keyframeCount:
            return len(keys)
        if timeChange:
            return [k[0] for k in keys] or None
        if valueChange:
            return [k[1] for k in keys] or None
        return None

    def listConnections(self, plug, source=True, destination=True, plugs=False, skipConversionNodes=False,
                        type=None):
        out = []
        if source and plug in self.conn:
            src = self.conn[plug]
            out.append(src if plugs else src.split(".")[0])
        if destination:
            for dest, src in self.conn.items():
                if src == plug:
                    node = dest.split(".")[0]
                    if type and self.nodes.get(node, {}).get("type") != type:
                        continue
                    out.append(dest if plugs else node)
        return out or None

    def currentUnit(self, query=False, linear=False, time=False):
        return self.linear if linear else self.unit

    def upAxis(self, query=False, axis=False):
        return self.up

    def file(self, query=False, sceneName=False):
        return self.scene_file

    def undoInfo(self, **kw):
        self.undo_calls.append(kw)
        if kw.get("query"):
            return self.undo
        if "stateWithoutFlush" in kw:
            self.undo = kw["stateWithoutFlush"]
        return None

    def currentTime(self, query=False):
        return self.time

    def optionVar(self, exists=None, query=None):
        if exists is not None:
            return exists in self.vars
        return self.vars.get(query)

    def internalVar(self, userAppDir=False):
        return self.app_dir

    def createNode(self, kind, name=None, skipSelect=False):
        base, number = name or kind, 1
        while name in self.nodes:
            name = "%s%d" % (base, number)
            number += 1
        self.add(name, kind)
        if kind.startswith("animCurve"):
            self.curves[name] = []
        return name

    def connectAttr(self, src, dest):
        self.conn[dest] = src

    def delete(self, node):
        self.deleted.append(node)
        self.nodes.pop(node, None)
        self.curves.pop(node, None)
        for dest, src in list(self.conn.items()):
            if src.split(".")[0] == node or dest.split(".")[0] == node:
                del self.conn[dest]

    def referenceQuery(self, node, isNodeReferenced=False):
        return node in self.referenced

    # ---- reading back
    def curve_on(self, plug):
        """The curve feeding `plug` and its keys (follows nothing)."""
        src = self.conn.get(plug)
        if not src:
            return None, None
        node = src.split(".")[0]
        return node, self.curves.get(node)


class _MTime(object):
    def __init__(self, value, unit=None):
        self.value = float(value)

    @staticmethod
    def uiUnit():
        return "ui"


class _SelectionList(object):
    def __init__(self):
        self.items = []

    def add(self, name):
        self.items.append(name)

    def getDependNode(self, i):
        return self.items[i]


def fake_om():
    """OpenMaya for the curves' keys: a time, its array, a selection by name; the real MMatrix for the maths."""
    return types.SimpleNamespace(MMatrix=real_om.MMatrix, MTime=_MTime, MTimeArray=list, MDoubleArray=list,
                                 MSelectionList=_SelectionList)


def fake_oma(cmds):
    """OpenMayaAnim's MFnAnimCurve on the fake's curves (a node is its name)."""
    class MFnAnimCurve(object):
        kTangentAuto = 18

        def __init__(self, node):
            self.node = node

        @property
        def numKeys(self):
            return len(cmds.curves[self.node])

        def remove(self, i):
            del cmds.curves[self.node][i]

        def addKeys(self, times, values, tin, tout):
            cmds.curves[self.node].extend([t.value, float(v)] for t, v in zip(times, values))
    return types.SimpleNamespace(MFnAnimCurve=MFnAnimCurve)


# ---------------------------------------------------------------------------------------------- fixtures

def turn(degrees, x=0.0, y=0.0, z=0.0):
    """A row-vector world matrix: a turn about Y and a place."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[c, 0, -s, 0], [0, 1, 0, 0], [s, 0, c, 0], [x, y, z, 1]], float)


SMALL = ["root", "pelvis", "thigh_l"]


def small_worlds(frames=5):
    """root > pelvis > thigh_l, moving and turning frame by frame (test_walk_cycle_cards' small walk)."""
    return np.array([[turn(0, 0, 0, 10.0 * f) for f in range(frames)],
                     [turn(5.0 * f, 0, 95, 10.0 * f) for f in range(frames)],
                     [turn(-7.0 * f, 10, 90, 10.0 * f + 1) for f in range(frames)]])


def flat(m):
    return [float(v) for v in np.asarray(m, float).reshape(16)]


class Base(unittest.TestCase):
    """A temporary walks folder, the walk session cache on sys put aside, a fake cmds and OpenMaya; every module
    attribute swapped is put back."""

    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix="walkscene_")
        self.walks = os.path.join(self.temp, "walks")
        self.library = os.path.join(self.temp, "library").replace("\\", "/")
        os.makedirs(self.walks)
        os.makedirs(self.library)
        self.saved_state = getattr(sys, "_skeldar_walk", _MISSING)
        sys._skeldar_walk = {"loaded": {}, "target": None, "model": wm, "clean": wc}
        self.fake = FakeCmds()
        self.swap(scene, "WALKS", self.walks)
        self.swap(scene, "_cmds", lambda: self.fake)
        self.swap(scene, "_om", fake_om)
        self.swap(scene, "_oma", lambda: fake_oma(self.fake))
        self.swap(wcards, "library_root", lambda cmds=None: self.library)

    def tearDown(self):
        if self.saved_state is _MISSING:
            if hasattr(sys, "_skeldar_walk"):
                del sys._skeldar_walk
        else:
            sys._skeldar_walk = self.saved_state
        shutil.rmtree(self.temp, ignore_errors=True)

    def swap(self, obj, name, value):
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    # ---- a skeleton in the fake scene
    def skeleton(self, names, parents, worlds, top="", start=0, keyed=True, skinned=False):
        """Joints for `names` under `top` (a group path, or none), each world by frame; root.translateZ keyed on
        every frame (the clip's range) when `keyed`. Returns {leaf: path}."""
        if top:
            self.fake.add(top, "transform")
        paths = {}
        for i, name in enumerate(names):
            parent = parents[i]
            paths[name] = (paths[names[parent]] if parent >= 0 else top) + "|" + name
            self.fake.joint(paths[name])
            self.fake.worlds[paths[name]] = dict((start + f, flat(worlds[i, f])) for f in range(worlds.shape[1]))
        if keyed:
            root = paths[names[0]]
            self.fake.key(root + ".translateZ", [[start + f, float(worlds[0, f, 3, 2])]
                                                  for f in range(worlds.shape[1])])
        if skinned:
            self.fake.add("skinCluster1", "skinCluster")
            self.fake.conn["skinCluster1.matrix[0]"] = paths[names[1]] + ".worldMatrix[0]"
        self.paths = paths
        return paths

    def stub_bones(self, statics):
        """maya_poselib.scene.skeleton answering the fake skeleton's joints with these statics as their rest."""
        from maya_poselib import scene as pscene
        paths = self.paths

        def skeleton(ref, notes=None):
            bones = {}
            for leaf, path in paths.items():
                bone = statics[leaf]
                bones[leaf] = {"path": path, "parent": bone["parent"], "canonical": bone["canonical"],
                               "rest": list(bone["rest"]), "world": list(self.fake.worlds[path][min(
                                   self.fake.worlds[path])]),
                               "rotateOrder": 0, "jointOrient": [0.0, 0.0, 0.0], "rotateAxis": [0.0, 0.0, 0.0]}
            return bones, "ue"
        self.swap(pscene, "skeleton_ref", lambda root: root)
        self.swap(pscene, "skeleton", skeleton)

    def small(self, top="|Hero_Character", start=3, skinned=False):
        worlds = small_worlds()
        paths = self.skeleton(SMALL, [-1, 0, 1], worlds, top=top, start=start, skinned=skinned)
        statics = dict((leaf, {"parent": (SMALL[i - 1] if i else None), "canonical": leaf,
                               "rest": flat(worlds[i, 0])}) for i, leaf in enumerate(SMALL))
        self.stub_bones(statics)
        return paths

    def synthetic(self, top="", skinned=True):
        """The synthetic walker (test_walkmodel's, 24 frames and the closing one) as a keyed skeleton."""
        worlds = tc.walker_worlds()
        paths = self.skeleton(tc.NAMES, tc.PARENTS, worlds, top=top, start=0, skinned=skinned)
        self.stub_bones(tc.STATICS)
        return paths

    def save_synthetic(self, name="raw"):
        clip = tc.clip_of(tc.walker_worlds())
        clip.name = name
        wf.save(wf.path_for(self.walks, name), clip, tc.STATICS, 0)
        return name

    def memo(self, root, **memo):
        if not self.fake.objExists(root):
            self.fake.joint(root)
        self.fake.nodes[root]["attrs"][scene.MARKER] = json.dumps(memo)


class Report(object):
    def __init__(self, changed=False, short=""):
        self.changed, self._short = changed, short

    def short(self):
        return self._short


# ---------------------------------------------------------------------------------------------- the folder, basics

class Folder(Base):

    def test_the_override_wins(self):
        self.assertEqual(scene.folder(), self.walks)

    def test_the_option_var_then_the_user_app_dir(self):
        self.swap(scene, "WALKS", None)
        self.assertEqual(scene.folder(), os.path.join("C:/fake/maya/", scene.FOLDER_NAME))
        self.fake.vars[scene.FOLDER_OPTIONVAR] = ""                   # set but empty: still the default
        self.assertEqual(scene.folder(), os.path.join("C:/fake/maya/", scene.FOLDER_NAME))
        self.fake.vars[scene.FOLDER_OPTIONVAR] = "D:/elsewhere"
        self.assertEqual(scene.folder(), "D:/elsewhere")

    def test_walk_and_pose_names_list_the_folder(self):
        self.save_synthetic("b")
        self.save_synthetic("a")
        wf.save_pose(wf.pose_path_for(self.walks, "hunch"), "hunch",
                     dict((n, dict(tc.STATICS[n], world=tc.STATICS[n]["rest"])) for n in tc.NAMES))
        self.assertEqual(scene.walk_names(), ["a", "b"])
        self.assertEqual(scene.pose_names(), ["hunch"])


class Basics(Base):

    def test_the_frame_rate_of_the_scene(self):
        for unit, fps in (("film", 24.0), ("ntsc", 30.0), ("ntscf", 60.0), ("23.976fps", 23.976), ("90fps", 90.0)):
            self.fake.unit = unit
            self.assertAlmostEqual(scene._fps(), fps)
        self.fake.unit = "millisec"
        with self.assertRaises(scene.Refusal):
            scene._fps()

    def test_a_node_gone_is_refused_by_name(self):
        self.fake.joint("|root")
        self.assertEqual(scene._long("root"), "|root")
        with self.assertRaises(scene.Refusal) as raised:
            scene._long("|nobody")
        self.assertIn("nobody is gone from the scene", str(raised.exception))
        self.assertEqual(scene._short("|a|b:c"), "b:c")

    def test_a_chunk_opens_and_closes_one_undo_step(self):
        with scene._Chunk("skeldarTest"):
            pass
        self.assertEqual(self.fake.undo_calls, [{"openChunk": True, "chunkName": "skeldarTest"},
                                                {"closeChunk": True}])

    def test_a_chunk_closes_when_the_press_raises(self):
        with self.assertRaises(ValueError):
            with scene._Chunk("skeldarTest"):
                raise ValueError("boom")
        self.assertEqual(self.fake.undo_calls[-1], {"closeChunk": True})

    def test_unrecorded_turns_recording_off_without_a_flush_and_back(self):
        with scene.Unrecorded():
            self.assertFalse(self.fake.undo)
        self.assertTrue(self.fake.undo)
        self.assertIn({"stateWithoutFlush": False}, self.fake.undo_calls)
        self.assertNotIn({"state": False}, self.fake.undo_calls)                # never the flushing switch

    def test_unrecorded_with_recording_already_off_touches_nothing(self):
        self.fake.undo = False
        with scene.Unrecorded():
            pass
        self.assertEqual(self.fake.undo_calls, [{"query": True, "state": True}])
        self.assertFalse(self.fake.undo)

    def test_the_session_state_starts_afresh_for_another_model(self):
        sys._skeldar_walk = {"loaded": {"x": 1}, "target": "T", "model": object(), "clean": wc}
        state = scene._state()
        self.assertEqual(state["loaded"], {})            # the old model's readings dropped
        self.assertEqual(state["target"], "T")           # the target kept
        self.assertIs(state["model"], wm)
        del sys._skeldar_walk
        self.assertEqual(scene._state()["loaded"], {})   # made when missing


class Seams(unittest.TestCase):

    def test_the_maya_seams_hand_out_the_real_modules(self):
        import maya.api.OpenMaya
        import maya.api.OpenMayaAnim
        import maya.cmds
        self.assertIs(scene._om(), maya.api.OpenMaya)
        self.assertIs(scene._oma(), maya.api.OpenMayaAnim)
        self.assertIs(scene._cmds(), maya.cmds)


# ---------------------------------------------------------------------------------------------- which skeleton

class WhichSkeleton(Base):

    def setUp(self):
        Base.setUp(self)
        import maya_rigs
        self.rigs = maya_rigs
        self.swap(maya_rigs, "rigs", lambda: [])
        self.swap(maya_rigs, "rig_of", lambda path, rigs: "Manny_Rig" if "Rig:" in path else None)
        f = self.fake
        f.joint("|root")
        f.joint("|root|pelvis")
        f.joint("|root|pelvis|thigh_l")
        f.add("|body", "transform")
        f.add("|body|bodyShape", "mesh", history=["skinCluster1", "tweak1"])
        f.add("skinCluster1", "skinCluster", influences=["pelvis", "root"])
        f.add("tweak1", "tweak")
        f.add("|prop", "transform")
        f.add("|prop|propShape", "mesh", history=[])
        f.add("|grp", "transform")
        f.joint("|grp|hips")
        f.joint("|grp|hips|spine")
        f.add("|empty", "transform")
        f.joint("|Manny_Rig:root")

    def test_a_joint_climbs_to_its_top_joint(self):
        self.assertEqual(scene.skeleton_root_of("|root|pelvis|thigh_l"), "|root")
        self.assertEqual(scene.skeleton_root_of("thigh_l"), "|root")

    def test_a_skinned_mesh_names_its_skeleton(self):
        self.assertEqual(scene.skeleton_root_of("|body"), "|root")

    def test_a_group_names_the_skeleton_under_it(self):
        self.assertEqual(scene.skeleton_root_of("|grp"), "|grp|hips")

    def test_a_group_with_no_joints_and_a_rig_are_refused(self):
        with self.assertRaises(scene.Refusal) as raised:
            scene.skeleton_root_of("|empty")
        self.assertIn("holds no skeleton", str(raised.exception))
        with self.assertRaises(scene.Refusal) as raised:
            scene.skeleton_root_of("|prop")
        self.assertIn("holds no skeleton", str(raised.exception))
        with self.assertRaises(scene.Refusal) as raised:
            scene.skeleton_root_of("|Manny_Rig:root")
        self.assertIn("belongs to a rig", str(raised.exception))

    def test_the_selection_names_its_skeletons_once_each_in_order(self):
        with self.assertRaises(scene.Refusal):
            scene.selected_root()
        with self.assertRaises(scene.Refusal):
            scene.selected_roots()
        self.fake.selection = ["|grp|hips|spine", "|root|pelvis", "|body", "|grp"]
        self.assertEqual(scene.selected_root(), "|grp|hips")
        self.assertEqual(scene.selected_roots(), ["|grp|hips", "|root"])

    def test_selected_top_is_cheap_and_answers_none_rather_than_refusing(self):
        self.assertIsNone(scene.selected_top())
        self.fake.selection = ["|root|pelvis|thigh_l"]
        self.assertEqual(scene.selected_top(), "|root")
        self.fake.selection = ["|body"]
        self.assertEqual(scene.selected_top(), "|root")
        self.fake.selection = ["|prop"]
        self.assertIsNone(scene.selected_top())
        self.fake.selection = ["|Manny_Rig:root"]                  # no rig check: Apply makes it
        self.assertEqual(scene.selected_top(), "|Manny_Rig:root")
        self.fake.nodes["skinCluster1"]["attrs"]["influences"] = ["gone"]
        self.fake.selection = ["|body"]
        self.assertIsNone(scene.selected_top())


# ---------------------------------------------------------------------------------------------- the walker marker

class Walkers(Base):

    def build(self):
        self.memo("|A_Character|root", walk="x", version=4)
        self.memo("|ns:root", walk="y", version=2)
        self.memo("|C|root", walk="z", version=3, listed=False)
        self.memo("|D|root", version=4)                                   # walks nothing
        self.memo("|E|root", walk="w", version=1)                         # a version not read
        self.fake.joint("|F|root")
        self.memo("|F|root|pelvis", walk="v", version=4)                  # not a top joint
        self.fake.joint("|G|root")                                        # never walked

    def test_walkers_are_the_listed_walked_top_joints_by_label(self):
        self.build()
        self.assertEqual(scene.walkers(), ["|A_Character|root", "|ns:root"])

    def test_set_listed_takes_a_walker_out_and_back(self):
        self.build()
        scene.set_listed("|A_Character|root", False)
        self.assertEqual(scene.walkers(), ["|ns:root"])
        self.assertFalse(scene.memo_of("|A_Character|root")["listed"])
        scene.set_listed("|C|root", True)
        self.assertEqual(scene.walkers(), ["|C|root", "|ns:root"])
        scene.set_listed("|G|root", True)                                 # no memo: nothing written
        self.assertNotIn(scene.MARKER, self.fake.nodes["|G|root"]["attrs"])

    def test_labels(self):
        self.assertEqual(scene.walker_label("|Manny_Skeleton_Character|root"), "Manny_Skeleton")
        self.assertEqual(scene.walker_label("|ns:root"), "ns")
        self.assertEqual(scene.walker_label("|grp|root"), "grp")
        self.assertEqual(scene.walker_label("|root"), "root")
        self.assertEqual(scene.walker_label("|_Character"), "_Character")       # a top that IS the joint

    def tabs(self, active="tab_a"):
        from maya_scenetabs import records
        state = records.empty_state()
        state["tabs"] = [records.new_tab("tab_a", "", "", {}), records.new_tab("tab_b", "", "", {})]
        state["active"] = active
        self.fake.add(records.SESSION_NODE, "network", **{records.SESSION_ATTR: records.dumps(state)})

    def test_with_scene_tabs_only_the_active_tab_s_walkers_named_as_the_tab_shows_them(self):
        self.memo("|tab_a:Hero_Character|tab_a:root", walk="x", version=4)
        self.memo("|tab_b:root", walk="y", version=4)
        self.tabs()
        self.assertEqual(scene.walkers(), ["|tab_a:Hero_Character|tab_a:root"])
        self.assertEqual(scene.walker_label("|tab_a:Hero_Character|tab_a:root"), "Hero")
        self.assertEqual(scene.walker_label("|tab_a:root"), "root")

    def test_working_walkers_are_the_ones_pick_chose(self):
        self.build()
        scene.set_working(["|ns:root", "|nobody"])                         # a node gone is passed over
        self.assertEqual(scene.working(), ["|ns:root"])
        self.assertIn({"stateWithoutFlush": False}, self.fake.undo_calls)  # unrecorded
        scene.set_working(["|A_Character|root"])
        self.assertEqual(scene.working(), ["|A_Character|root"])
        self.assertFalse(scene.memo_of("|ns:root")["working"])
        scene.set_working(None)
        self.assertEqual(scene.working(), [])


class Memo(Base):

    def test_a_memo_that_is_not_json_reads_as_none(self):
        self.fake.joint("|root", **{scene.MARKER: "{broken"})
        self.assertEqual(scene.memo_of("|root"), {})
        self.fake.nodes["|root"]["attrs"][scene.MARKER] = ""
        self.assertEqual(scene.memo_of("|root"), {})
        self.fake.joint("|bare")
        self.assertEqual(scene.memo_of("|bare"), {})

    def test_a_memo_that_is_json_but_no_object_reads_as_none(self):
        """BUG (scene.py memo_of, lines 804-808): a marker that is not JSON reads as no memo, but one that is JSON
        and not an object ("1", "[]", a string) raises AttributeError on .get - walkers() then fails for the whole
        card's list over one broken attribute."""
        self.fake.joint("|root", **{scene.MARKER: "[1, 2]"})
        self.assertEqual(scene.memo_of("|root"), {})

    def test_set_memo_adds_the_attribute_once_and_writes_json(self):
        self.fake.joint("|root")
        scene._set_memo("|root", {"walk": "asd", "version": 4})
        self.assertEqual(scene.memo_of("|root"), {"walk": "asd", "version": 4})
        scene._set_memo("|root", {"walk": "dw", "version": 4})
        self.assertEqual(scene.memo_of("|root")["walk"], "dw")

    def test_pick_reads_what_a_walked_skeleton_carries_and_makes_it_the_target(self):
        self.memo("|root", walk="asd", version=2, pose="goblin", parts=["torso"],
                  knobs={"stride": 1.2, "lift_l": 1.5, "seam": 6.0, "nonsense": 9.0})
        walk, knobs, pose, parts = scene.pick("root")
        self.assertEqual((walk, pose, parts), ("asd", "goblin", ("torso",)))
        self.assertEqual(knobs["stride"], 1.2)
        self.assertEqual(knobs["lift_l"], 1.5)
        self.assertEqual(knobs["seam"], wc.knobs({"seam": 6.0})["seam"])
        self.assertNotIn("nonsense", knobs)
        self.assertEqual(knobs["bob"], wm.DEFAULTS["bob"])                  # the rest at their defaults
        self.assertEqual(scene.target_root(), "|root")

    def test_pick_of_a_skeleton_walking_nothing_is_refused(self):
        self.fake.joint("|root")
        with self.assertRaises(scene.Refusal):
            scene.pick("|root")
        self.memo("|root", walk="asd", version=4)
        self.assertEqual(scene.pick("|root")[2:], (None, scene.ALL_PARTS))

    def test_the_target_set_and_gone(self):
        with self.assertRaises(scene.Refusal):
            scene.target_root()
        self.fake.joint("|root")
        scene.set_target("|root")
        self.assertEqual(scene.target_root(), "|root")
        self.fake.delete("|root")
        with self.assertRaises(scene.Refusal):
            scene.target_root()
        scene.set_target(None)
        self.assertIsNone(scene._state()["target"])


# ---------------------------------------------------------------------------------------------- a walker's edits

def a_fix(height=3.0):
    fix = mp.empty()
    fix["height"] = height
    fix["rot"] = {"spine_01": np.eye(3)}
    return fix


def some_keys():
    entry = kp.empty_key()
    entry["pelvis"] = np.array([0.0, -2.0, 0.0])
    return {"contact": entry}


class Edits(Base):

    def setUp(self):
        Base.setUp(self)
        self.fake.joint("|root")

    def test_set_and_read_back(self):
        self.assertIsNone(scene.edits_of("|root"))
        self.assertIsNone(scene.edits_of("|nobody"))
        self.assertIsNone(scene.edits_of(None))
        scene.set_edits("|root", {"walk": "asd", "fix": a_fix(), "keys": some_keys(), "posture": True})
        back = scene.edits_of("|root")
        self.assertEqual(back["walk"], "asd")
        self.assertEqual(back["fix"]["height"], 3.0)
        self.assertEqual(sorted(back["fix"]["rot"]), ["spine_01"])
        self.assertAlmostEqual(float(back["keys"]["contact"]["pelvis"][1]), -2.0)
        self.assertTrue(back["posture"])
        self.assertIn({"stateWithoutFlush": False}, self.fake.undo_calls)     # unrecorded
        scene.set_edits("|root", None)                                        # none: an empty record
        self.assertTrue(scene.edits_empty(scene.edits_of("|root")))

    def test_an_edits_attribute_that_is_not_json_reads_as_none(self):
        self.fake.nodes["|root"]["attrs"][scene.EDITS_ATTR] = "{nope"
        self.assertIsNone(scene.edits_of("|root"))

    def test_edits_that_are_json_but_no_object_read_as_none(self):
        """BUG (scene.py edits_of, lines 858-862): the same as memo_of - "[]" or "3" in the edits attribute raises
        AttributeError (raw.get) where text that is not JSON reads as none."""
        self.fake.nodes["|root"]["attrs"][scene.EDITS_ATTR] = "[]"
        self.assertIsNone(scene.edits_of("|root"))

    def test_a_fix_of_a_format_this_tool_does_not_read_is_dropped(self):
        self.fake.nodes["|root"]["attrs"][scene.EDITS_ATTR] = json.dumps(
            {"walk": "asd", "fix": {"format": "other", "height": 2.0}, "posture": True})
        back = scene.edits_of("|root")
        self.assertTrue(mp.is_empty(back["fix"]))
        self.assertTrue(back["posture"])

    def test_a_fix_it_cannot_read_does_not_take_the_key_edits_with_it(self):
        """BUG (scene.py edits_of, lines 863-867): fix and keys are read in one try - a fix this build cannot read
        (another format, a newer version) raises before the key poses are read, so valid key pose edits are
        dropped with it. Each should be read on its own."""
        self.fake.nodes["|root"]["attrs"][scene.EDITS_ATTR] = json.dumps(
            {"walk": "asd", "fix": {"format": mp.FORMAT, "version": mp.VERSION + 1, "height": 2.0},
             "keys": kp.dumps(some_keys())})
        back = scene.edits_of("|root")
        self.assertFalse(kp.is_empty(back["keys"]))

    def test_edits_empty_and_the_line(self):
        self.assertTrue(scene.edits_empty(None))
        self.assertTrue(scene.edits_empty(scene.empty_edits("asd")))
        self.assertFalse(scene.edits_empty(dict(scene.empty_edits(), posture=True)))
        self.assertEqual(scene.edits_line(None), "")
        self.assertEqual(scene.edits_line(scene.empty_edits()), "")
        line = scene.edits_line({"fix": a_fix(), "keys": some_keys(), "posture": True})
        self.assertIn("mean pose corrected (1 bone turned, pelvis +3.0 cm)", line)
        self.assertIn("key poses: Contact edited", line)
        self.assertTrue(line.endswith("posture fixed"))

    def test_a_walker_s_own_edits_of_this_walk(self):
        scene.set_edits("|root", {"walk": "asd", "fix": a_fix()})
        edits, note = scene.walker_edits("|root", "asd")
        self.assertEqual((edits["walk"], edits["fix"]["height"], note), ("asd", 3.0, ""))
        scene.set_edits("|root", {"walk": "", "posture": True})
        edits, note = scene.walker_edits("|root", "asd")                     # no walk named: this one's
        self.assertEqual((edits["walk"], edits["posture"], note), ("asd", True, ""))

    def test_another_walk_s_edits_are_dropped_and_said(self):
        scene.set_edits("|root", {"walk": "dw", "fix": a_fix()})
        edits, note = scene.walker_edits("|root", "asd")
        self.assertTrue(scene.edits_empty(edits))
        self.assertEqual(edits["walk"], "asd")
        self.assertEqual(note, "root's edits of dw dropped (another walk)")
        scene.set_edits("|root", {"walk": "dw"})                             # nothing to drop: nothing said
        self.assertEqual(scene.walker_edits("|root", "asd")[1], "")

    def legacy(self, version, fix=None, walk="asd"):
        self.save_synthetic("asd")
        mp.save(mp.path_for(wf.path_for(self.walks, "asd")), fix if fix is not None else a_fix(-4.0))
        self.memo("|root", walk=walk, version=version)

    def test_an_older_walker_carries_its_cycle_s_old_mean_pose_file_once(self):
        self.legacy(3)
        edits, note = scene.walker_edits("|root", "asd")
        self.assertEqual(edits["fix"]["height"], -4.0)
        self.assertEqual(note, "the cycle's old mean pose correction carried onto root")

    def test_no_carry_for_a_new_walker_another_walk_or_an_empty_file(self):
        for version, walk, fix in ((4, "asd", None), (3, "dw", None), (3, "asd", mp.empty())):
            self.legacy(version, fix, walk)
            edits, note = scene.walker_edits("|root", "asd")
            self.assertTrue(mp.is_empty(edits["fix"]), (version, walk))
            self.assertEqual(note, "")

    def test_an_unreadable_old_mean_pose_file_carries_nothing(self):
        self.legacy(3)
        with open(mp.path_for(wf.path_for(self.walks, "asd")), "w") as handle:
            handle.write("not json")
        edits, note = scene.walker_edits("|root", "asd")
        self.assertTrue(mp.is_empty(edits["fix"]))
        self.assertEqual(note, "")

    def test_the_walk_s_correction_and_key_files(self):
        self.save_synthetic("asd")
        fix, path = scene.walk_fix("asd")
        self.assertTrue(mp.is_empty(fix))
        self.assertTrue(path.endswith("asd" + mp.SUFFIX))
        mp.save(path, a_fix(1.5))
        self.assertEqual(scene.walk_fix("asd")[0]["height"], 1.5)
        keys, path = scene.walk_keys("asd")
        self.assertEqual(keys, {})
        self.assertTrue(path.endswith("asd" + kp.SUFFIX))


# ---------------------------------------------------------------------------------------------- keys

class Keys(Base):

    def setUp(self):
        Base.setUp(self)
        f = self.fake
        f.joint("|root")
        f.joint("|root|pelvis")
        f.joint("|root|pelvis|thigh_l")
        f.key("|root.translateZ", [[0, 0.0], [10, 50.0]])
        f.key("|root|pelvis.rotateY", [[0, 0.0], [5, 10.0]], kind="animCurveTA")

    def test_has_keys(self):
        self.assertTrue(scene.has_keys("|root"))
        self.fake.delete("root_translateZ")
        self.fake.delete("pelvis_rotateY")
        self.assertFalse(scene.has_keys("|root"))

    def test_the_print_follows_the_base_keys(self):
        first = scene.keys_print("|root")
        self.assertEqual(sorted(first), ["pelvis", "root"])     # a row a keyed bone, thigh_l carries none
        self.assertEqual(scene.keys_print("|root"), first)
        self.fake.curves["root_translateZ"][1][1] = 51.0
        self.assertNotEqual(scene.keys_print("|root"), first)

    def test_a_layer_on_top_and_a_constraint_do_not_count(self):
        first = scene.keys_print("|root")
        f = self.fake
        f.add("blend1", "animBlendNodeAdditiveRotation")
        f.curve("layer_rotateY", [[0, 0.0], [3, 99.0]], kind="animCurveTA")
        f.conn["blend1.inputAY"] = f.conn.pop("|root|pelvis.rotateY")
        f.conn["blend1.inputBY"] = "layer_rotateY.output"
        f.conn["|root|pelvis.rotateY"] = "blend1.outputY"
        f.add("thigh_parentConstraint1", "parentConstraint")
        f.conn["|root|pelvis|thigh_l.translateX"] = "thigh_parentConstraint1.constraintTranslateX"
        self.assertEqual(scene.keys_print("|root"), first)
        f.curves["layer_rotateY"][1][1] = 3.0                           # the animator's layer: still the same
        self.assertEqual(scene.keys_print("|root"), first)

    def test_keys_changed_against_the_marker(self):
        self.memo("|root", walk="asd", version=4, keys=scene.keys_print("|root"))
        self.assertFalse(scene.keys_changed("|root"))
        self.fake.curves["pelvis_rotateY"].append([9, 20.0])           # a clip put on it
        self.assertTrue(scene.keys_changed("|root"))
        self.memo("|root", walk="asd", version=4)                        # a marker from before the digest
        self.assertFalse(scene.keys_changed("|root"))
        self.memo("|root", version=4, keys="0" * 16)                     # walks nothing
        self.assertFalse(scene.keys_changed("|root"))

    def test_base_input_follows_layers_to_the_base(self):
        f = self.fake
        self.assertEqual(scene.base_input("|root.translateZ"), ("|root.translateZ", "root_translateZ"))
        self.assertEqual(scene.base_input("|root|pelvis.rotateX"), ("|root|pelvis.rotateX", None))
        f.add("blendT", "animBlendNodeAdditiveDL")
        f.conn["blendT.inputA"] = f.conn.pop("|root.translateZ")
        f.conn["|root.translateZ"] = "blendT.output"
        self.assertEqual(scene.base_input("|root.translateZ"), ("blendT.inputA", "root_translateZ"))
        f.add("blendX", "animBlendNodeAdditiveRotation")
        f.conn["|root.rotateX"] = "blendX.outputX"                       # a layer with no base curve yet
        self.assertEqual(scene.base_input("|root.rotateX"), ("blendX.inputAX", None))

    def test_base_input_refuses_any_other_driver_by_name(self):
        f = self.fake
        f.add("expr1", "expression")
        f.conn["|root.rotateZ"] = "expr1.output[0]"
        with self.assertRaises(scene.Refusal) as raised:
            scene.base_input("|root.rotateZ")
        self.assertIn("driven by expr1 (expression)", str(raised.exception))
        f.add("blendW", "animBlendNodeAdditiveRotation")                  # a blend's weight is no channel
        f.conn["|root.rotateY"] = "blendW.weightA"
        with self.assertRaises(scene.Refusal):
            scene.base_input("|root.rotateY")

    def test_base_input_gives_up_on_a_layer_chain_it_cannot_follow(self):
        f = self.fake
        f.add("loop1", "animBlendNodeAdditiveDL")
        f.conn["|root.translateX"] = "loop1.output"
        f.conn["loop1.inputA"] = "loop1.output"
        with self.assertRaises(scene.Refusal) as raised:
            scene.base_input("|root.translateX")
        self.assertIn("cannot follow", str(raised.exception))


# ---------------------------------------------------------------------------------------------- writing curves

class WriteCurves(Base):

    def setUp(self):
        Base.setUp(self)
        f = self.fake
        f.joint("|root")
        f.joint("|root|pelvis")

    def test_new_curves_keyed_from_start_auto_tangents(self):
        written, held = scene.write_curves({"|root": {"rotateY": [0.1, 0.2, 0.3], "translateZ": [0.0, 5.0, 10.0]}},
                                           {}, 7)
        self.assertEqual((written, held), (2, {}))
        node, keys = self.fake.curve_on("|root.rotateY")
        self.assertEqual(self.fake.nodeType(node), "animCurveTA")
        self.assertEqual(keys, [[7.0, 0.1], [8.0, 0.2], [9.0, 0.3]])
        node, keys = self.fake.curve_on("|root.translateZ")
        self.assertEqual(self.fake.nodeType(node), "animCurveTL")
        self.assertEqual(keys[-1], [9.0, 10.0])

    def test_a_recorded_re_key_replaces_the_curve_node(self):
        old = self.fake.key("|root.rotateY", [[0, 1.0]], kind="animCurveTA")
        scene.write_curves({"|root": {"rotateY": [0.5]}}, {}, 0)
        node, keys = self.fake.curve_on("|root.rotateY")
        self.assertIn(old, self.fake.deleted)
        self.assertEqual(keys, [[0.0, 0.5]])

    def test_an_unrecorded_re_key_keeps_the_node_and_writes_its_keys_again(self):
        old = self.fake.key("|root.rotateY", [[0, 1.0], [1, 2.0], [2, 3.0]], kind="animCurveTA")
        scene.write_curves({"|root": {"rotateY": [0.5, 0.6]}}, {}, 10, in_place=True)
        node, keys = self.fake.curve_on("|root.rotateY")
        self.assertEqual(node, old)
        self.assertEqual(keys, [[10.0, 0.5], [11.0, 0.6]])
        self.assertEqual(self.fake.deleted, [])

    def test_in_place_still_replaces_a_referenced_curve_or_one_of_another_kind(self):
        ref = self.fake.key("|root.rotateY", [[0, 1.0], [1, 2.0]], kind="animCurveTA")
        self.fake.referenced.add(ref)
        wrong = self.fake.key("|root.rotateX", [[0, 1.0]], kind="animCurveTU")
        scene.write_curves({"|root": {"rotateY": [0.5], "rotateX": [0.25]}}, {}, 0, in_place=True)
        self.assertEqual(sorted(self.fake.deleted), sorted([ref, wrong]))       # deleted, not emptied
        node, keys = self.fake.curve_on("|root.rotateY")
        self.assertEqual((self.fake.nodeType(node), keys), ("animCurveTA", [[0.0, 0.5]]))
        node, keys = self.fake.curve_on("|root.rotateX")
        self.assertEqual((self.fake.nodeType(node), keys), ("animCurveTA", [[0.0, 0.25]]))

    def test_under_a_layer_the_base_is_re_keyed_and_the_layer_stays(self):
        f = self.fake
        base = f.curve("base_rotateY", [[0, 0.0]], kind="animCurveTA")
        layer = f.curve("layer_rotateY", [[0, 9.0]], kind="animCurveTA")
        f.add("blend1", "animBlendNodeAdditiveRotation")
        f.conn["|root.rotateY"] = "blend1.outputY"
        f.conn["blend1.inputAY"] = base + ".output"
        f.conn["blend1.inputBY"] = layer + ".output"
        scene.write_curves({"|root": {"rotateY": [0.7]}}, {}, 0)
        self.assertEqual(f.conn["|root.rotateY"], "blend1.outputY")
        node, keys = f.curve_on("blend1.inputAY")
        self.assertEqual(keys, [[0.0, 0.7]])
        self.assertEqual(f.conn["blend1.inputBY"], layer + ".output")
        self.assertEqual(f.curves[layer], [[0, 9.0]])

    def test_a_channel_something_else_drives_is_left_to_it_and_named(self):
        f = self.fake
        f.add("weapon_parentConstraint1", "parentConstraint")
        f.conn["|root|pelvis.rotateY"] = "weapon_parentConstraint1.constraintRotateY"
        f.conn["|root|pelvis.translateX"] = "weapon_parentConstraint1.constraintTranslateX"
        written, held = scene.write_curves({"|root|pelvis": {"rotateY": [0.1], "rotateX": [0.2]}},
                                           {"|root|pelvis": (1.0, 2.0, 3.0)}, 0)
        self.assertEqual(written, 1)
        self.assertEqual(held, {"pelvis": "weapon_parentConstraint1"})
        self.assertEqual(f.conn["|root|pelvis.rotateY"], "weapon_parentConstraint1.constraintRotateY")
        self.assertNotIn("|root|pelvis.translateX", f.set_values)
        self.assertEqual(f.set_values["|root|pelvis.translateY"], 2.0)

    def test_a_static_translate_deletes_the_curves_and_sets_the_values_unlocked(self):
        f = self.fake
        old = f.key("|root.translateX", [[0, 4.0], [3, 8.0]])
        f.locks.add("|root.translateY")
        scene.write_curves({}, {"|root": (1.0, 2.0, 3.0)}, 0)
        self.assertIn(old, f.deleted)
        self.assertEqual([f.set_values["|root." + ch] for ch in scene.TRANSLATE], [1.0, 2.0, 3.0])
        self.assertNotIn("|root.translateY", f.locks)

    def test_a_locked_channel_is_unlocked_before_its_new_curve(self):
        self.fake.locks.add("|root.rotateZ")
        scene.write_curves({"|root": {"rotateZ": [0.1]}}, {}, 0)
        self.assertNotIn("|root.rotateZ", self.fake.locks)
        self.assertEqual(self.fake.curve_on("|root.rotateZ")[1], [[0.0, 0.1]])


class ChannelValues(Base):

    def setUp(self):
        Base.setUp(self)
        f = self.fake
        f.add("|grp", "transform")
        f.joint("|grp|root")
        f.joint("|grp|root|pelvis")
        f.worlds["|grp"] = {0.0: flat(turn(90.0, 5.0, 0.0, 0.0))}
        self.bones = {"root": {"path": "|grp|root", "parent": None, "jointOrient": [0, 0, 0], "rotateAxis": [0, 0, 0],
                               "rotateOrder": 0},
                      "pelvis": {"path": "|grp|root|pelvis", "parent": "root", "jointOrient": [0, 0, 0],
                                 "rotateAxis": [0, 0, 0], "rotateOrder": 0}}

    def frames(self, degrees):
        return [{"root": real_om.MMatrix(flat(turn(90.0 + d, 5.0, 0.0, 10.0 * i))),
                 "pelvis": real_om.MMatrix(flat(turn(90.0 + 2 * d, 5.0, 90.0, 10.0 * i)))}
                for i, d in enumerate(degrees)]

    def test_locals_against_the_parent_and_the_node_above_the_top(self):
        values, static = scene.channel_values(self.bones, self.frames([0.0, 10.0, 20.0]), ["root", "pelvis"],
                                              {"root"})
        root, pelvis = values["|grp|root"], values["|grp|root|pelvis"]
        self.assertEqual(sorted(root), sorted(scene.CHANNELS))                     # translated: all six
        self.assertEqual(sorted(pelvis), sorted(scene.ROTATE))                     # rotations only
        self.assertEqual([round(math.degrees(v), 6) for v in root["rotateY"]], [0.0, 10.0, 20.0])
        self.assertEqual([round(math.degrees(v), 6) for v in pelvis["rotateY"]], [0.0, 10.0, 20.0])
        self.assertEqual(sorted(static), ["|grp|root|pelvis"])                     # its first frame's local
        local = turn(90.0, 5.0, 90.0, 0.0) @ np.linalg.inv(turn(90.0, 5.0, 0.0, 0.0))
        self.assertTrue(np.allclose(static["|grp|root|pelvis"], local[3, :3]))

    def test_each_frame_s_euler_is_the_one_nearest_the_frame_before(self):
        values, _ = scene.channel_values(self.bones, self.frames([170.0, 190.0, 210.0]), ["root"], set())
        degrees = [math.degrees(v) for v in values["|grp|root"]["rotateY"]]
        self.assertTrue(all(abs(b - a) < 25.0 for a, b in zip(degrees, degrees[1:])), degrees)

    def test_a_top_joint_at_world_level_reads_against_the_identity(self):
        f = self.fake
        f.joint("|top")
        bones = {"top": {"path": "|top", "parent": None, "jointOrient": [0, 0, 0], "rotateAxis": [0, 0, 0],
                         "rotateOrder": 0}}
        frames = [{"top": real_om.MMatrix(flat(turn(30.0, 1.0, 2.0, 3.0)))}]
        values, static = scene.channel_values(bones, frames, ["top"], {"top"})
        self.assertAlmostEqual(math.degrees(values["|top"]["rotateY"][0]), 30.0)
        self.assertEqual(values["|top"]["translateZ"], [3.0])


# ---------------------------------------------------------------------------------------------- reading a clip, saving

class ReadClip(Base):

    def test_every_joint_s_world_on_every_whole_frame(self):
        self.fake.scene_file = "C:/anim/stroll_v02.ma"
        paths = self.small(start=3)
        clip, start = scene.read_clip(paths["root"])
        self.assertEqual(start, 3)
        self.assertEqual(clip.names, SMALL)
        self.assertEqual(clip.parents, [-1, 0, 1])
        self.assertEqual(clip.worlds.shape, (3, 5, 4, 4))
        self.assertTrue(np.allclose(clip.worlds, small_worlds()))
        self.assertEqual((clip.fps, clip.name, tuple(clip.up)), (30.0, "stroll_v02", (0.0, 1.0, 0.0)))

    def test_an_untitled_scene_names_the_clip_after_its_group_or_root(self):
        paths = self.small()
        self.assertEqual(scene.read_clip(paths["root"])[0].name, "Hero_Character")
        self.fake.up = "z"
        self.assertEqual(tuple(scene.read_clip(paths["root"])[0].up), (0.0, 0.0, 1.0))

    def test_refusals(self):
        paths = self.small()
        self.fake.linear = "m"
        with self.assertRaises(scene.Refusal):
            scene.read_clip(paths["root"])
        self.fake.linear = "cm"
        self.fake.curves["root_translateZ"][0][0] = 3.5
        with self.assertRaises(scene.Refusal) as raised:
            scene.read_clip(paths["root"])
        self.assertIn("whole frames", str(raised.exception))
        self.fake.curves["root_translateZ"] = []
        with self.assertRaises(scene.Refusal) as raised:
            scene.read_clip(paths["root"])
        self.assertIn("carries no keys", str(raised.exception))


class ReadBones(Base):

    def test_a_skinned_skeleton_keeps_its_own_rest(self):
        paths = self.small(skinned=True)
        bones, note = scene.read_bones(paths["root"])
        self.assertEqual(note, "")
        self.assertEqual(bones["pelvis"]["rest"], flat(small_worlds()[1, 0]))

    def test_an_unskinned_skeleton_that_is_not_manny_s_rests_as_it_stands(self):
        paths = self.small()
        bones, note = scene.read_bones(paths["root"])
        self.assertEqual(note, "root has no skin: its rest is read as it stands")
        self.assertEqual(bones["pelvis"]["rest"], flat(small_worlds()[1, 0]))

    def test_an_unskinned_manny_rests_at_manny_s_bind(self):
        template = wf.read_template(scene.TEMPLATE)
        names = [n for n in template]
        parents = [names.index(template[n]["parent"]) if template[n]["parent"] in names else -1 for n in names]
        shift = np.eye(4)
        shift[3, :3] = (40.0, 0.0, -25.0)                    # standing elsewhere: lengths the same
        worlds = np.array([[np.array(template[n]["world_matrix"]).reshape(4, 4) @ shift] for n in names])
        paths = self.skeleton(names, parents, worlds, keyed=False)
        statics = dict((n, {"parent": template[n]["parent"], "canonical": n, "rest": flat(worlds[i, 0])})
                       for i, n in enumerate(names))
        self.stub_bones(statics)
        bones, note = scene.read_bones(paths[names[0]])
        self.assertEqual(note, "")
        self.assertEqual(bones["pelvis"]["rest"], template["pelvis"]["world_matrix"])


class SaveWalk(Base):

    def off(self, data):
        """How far a saved walk's worlds are from the synthetic walker's, joint by joint by name."""
        source = tc.walker_worlds()
        return max(float(np.abs(data["worlds"][i] - source[tc.IDX[name]]).max())
                   for i, name in enumerate(data["names"]))

    def test_the_cycle_saved_as_it_stands_and_read_back(self):
        self.fake.scene_file = "C:/anim/My stroll.ma"
        paths = self.synthetic()
        name, line = scene.save_walk(paths["root"])
        self.assertEqual(name, "My_stroll")
        self.assertTrue(line.startswith("saved My_stroll" + wf.SUFFIX + " | "))
        self.assertIn("cycle 24 frames", line)
        data = wf.load(wf.path_for(self.walks, name))
        self.assertEqual(sorted(data["names"]), sorted(tc.NAMES))
        self.assertEqual(data["names"][0], "root")                            # by depth: the top first
        self.assertLess(self.off(data), 1e-9)
        self.assertEqual(data["statics"]["thigh_l"]["parent"], "pelvis")
        self.assertEqual(scene.walk_names(), ["My_stroll"])

    def test_a_given_name_and_a_fresh_save_drops_the_old_reading(self):
        paths = self.synthetic()
        name = scene.save_walk(paths["root"], "stroll")[0]
        before = scene.load_walk(name)[0]
        scene.save_walk(paths["root"], "stroll")
        self.assertIsNot(scene.load_walk(name)[0], before)

    def test_a_cycle_the_clean_has_to_close_says_what_it_did(self):
        paths = self.skeleton(tc.NAMES, tc.PARENTS, tc.walker_worlds()[:, :tc.P], start=0, skinned=True)
        self.stub_bones(tc.STATICS)
        line = scene.save_walk(paths["root"], "open")[1]
        self.assertIn(" | cleaned: loop closed", line)
        self.assertEqual(wf.load(wf.path_for(self.walks, "open"))["worlds"].shape[1], tc.P)   # saved as it stands
        from maya_poselib import capture
        self.swap(capture, "thumbnail", lambda path, kind=None, **kw: (False, "no viewport"))
        line = scene.save_walk_card(paths["root"], "open")[1]
        self.assertIn(" | cleaned: loop closed", line)

    def test_an_unskinned_cycle_says_so(self):
        paths = self.synthetic(skinned=False)
        line = scene.save_walk(paths["root"], "x")[1]
        self.assertTrue(line.endswith("root has no skin: its rest is read as it stands"))

    def test_bones_the_skeleton_reader_does_not_know_are_refused(self):
        paths = self.synthetic()
        from maya_poselib import scene as pscene
        real = pscene.skeleton

        def short(ref, notes=None):
            bones, convention = real(ref, notes)
            bones.pop("ball_l")
            return bones, convention
        self.swap(pscene, "skeleton", short)
        for save in (scene.save_walk, scene.save_walk_card, scene.capture_source):
            with self.assertRaises(scene.Refusal) as raised:
                save(paths["root"])
            self.assertIn("ball_l", str(raised.exception))

    def test_saved_as_a_walk_card_of_the_library(self):
        from maya_poselib import capture
        self.swap(capture, "thumbnail", lambda path, kind=None, **kw: (_ for _ in ()).throw(RuntimeError("no view")))
        paths = self.synthetic()
        name, line = scene.save_walk_card(paths["root"], "stroll")
        self.assertEqual(name, scene.card_walk(wcards.WALK_FOLDER + "/stroll.anim"))
        self.assertIn("saved the walk card %s/stroll" % wcards.WALK_FOLDER, line)
        card = os.path.join(self.library, wcards.WALK_FOLDER, "stroll.anim")
        self.assertFalse(os.path.exists(os.path.join(card, store.THUMB_FILE)))   # no viewport: no still
        self.assertFalse(os.path.exists(os.path.join(self.walks, scene.CARD_CACHE, "still.part.jpg")))
        back = wf.load(scene.walk_path(name))
        self.assertLess(self.off(back), 1e-5)
        second = scene.save_walk_card(paths["root"], "stroll")[0]                # a name taken: the next free
        self.assertEqual(second, scene.card_walk(wcards.WALK_FOLDER + "/stroll 2.anim"))

    def test_a_walk_card_keeps_the_still_a_viewport_gave(self):
        from maya_poselib import capture
        source = os.path.join(self.temp, "still.jpg")
        from PySide6 import QtGui
        image = QtGui.QImage(8, 8, QtGui.QImage.Format_RGB32)
        image.fill(0x335577)
        image.save(source, "JPG")

        def thumbnail(path, kind=None, **kw):
            shutil.copy(source, path)
            return True, ""
        self.swap(capture, "thumbnail", thumbnail)
        paths = self.synthetic()
        scene.save_walk_card(paths["root"], "stroll")
        card = os.path.join(self.library, wcards.WALK_FOLDER, "stroll.anim")
        self.assertTrue(os.path.exists(os.path.join(card, store.THUMB_FILE)))
        self.assertFalse(os.path.exists(os.path.join(self.walks, scene.CARD_CACHE, "still.part.jpg")))


# ---------------------------------------------------------------------------------------------- a skeleton's own cycle

class OwnCycle(Base):

    def test_the_keys_kept_on_the_skeleton_once_and_read_into_a_walk_file(self):
        paths = self.small()
        root = paths["root"]
        self.assertFalse(scene.has_source(root))
        name = scene.capture_source(root)
        self.assertTrue(scene.is_own(name))
        self.assertTrue(scene.has_source(root))
        self.assertEqual(scene.walk_label(name), "Hero's cycle")
        path = scene.walk_path(name)
        self.assertTrue(path.startswith(os.path.join(self.walks, scene.OWN_CACHE)))
        data = wf.load(path)
        self.assertEqual((data["names"], data["start"], data["name"]), (SMALL, 3, "Hero"))
        self.assertTrue(np.allclose(data["worlds"], small_worlds()))
        self.assertFalse(os.path.exists(os.path.join(self.walks, scene.OWN_CACHE, "capture.part" + wf.SUFFIX)))
        stamp = os.path.getmtime(path)
        self.assertEqual(scene.capture_source(root), name)                     # a second call: the one kept
        self.assertEqual(os.path.getmtime(path), stamp)
        self.assertTrue(scene.walk_exists(name))

    def test_an_own_cycle_s_file_is_written_again_from_the_scene(self):
        paths = self.small()
        name = scene.capture_source(paths["root"])
        shutil.rmtree(os.path.join(self.walks, scene.OWN_CACHE))
        sys._skeldar_walk["own_labels"] = {}
        self.assertEqual(scene.walk_label(name), "own cycle")                  # no skeleton read yet
        path = scene.walk_path(name)                                           # _sync_own finds the skeleton
        self.assertTrue(os.path.exists(path))
        self.assertEqual(scene.walk_label(name), "Hero's cycle")

    def test_an_own_cycle_no_skeleton_keeps_is_refused(self):
        name = scene.OWN + "0123456789abcdef"
        self.fake.joint("|other", **{scene.SOURCE_ATTR: ""})                   # keeps an empty one
        with self.assertRaises(scene.Refusal) as raised:
            scene.walk_path(name)
        self.assertIn("no skeleton in the scene keeps own cycle", str(raised.exception))
        self.assertFalse(scene.walk_exists(name))
        with self.assertRaises(scene.Refusal):
            scene.own_name("|other")

    def test_drop_source(self):
        paths = self.small()
        scene.capture_source(paths["root"])
        scene.drop_source(paths["root"])
        self.assertFalse(scene.has_source(paths["root"]))
        scene.drop_source(paths["root"])                                       # nothing kept: nothing done

    def test_restore_keys_the_cycle_back_and_takes_the_walk_off(self):
        paths = self.small()
        root = paths["root"]
        scene.capture_source(root)
        self.memo(root, walk="asd", version=4)
        self.fake.nodes[root]["attrs"][scene.POSE_COPY] = "packed"
        line = scene.restore_source(root)
        self.assertEqual(line, "Hero: its original keys back (5 frames), out of the list")
        for attr in (scene.MARKER, scene.SOURCE_ATTR, scene.POSE_COPY):
            self.assertNotIn(attr, self.fake.nodes[root]["attrs"])
        f = self.fake
        times = [k[0] for k in f.curve_on(root + ".translateZ")[1]]
        self.assertEqual(times, [3.0, 4.0, 5.0, 6.0, 7.0])
        self.assertEqual([round(k[1], 6) for k in f.curve_on(root + ".translateZ")[1]], [0, 10, 20, 30, 40])
        pelvis = [round(math.degrees(k[1]), 6) for k in f.curve_on(paths["pelvis"] + ".rotateY")[1]]
        self.assertEqual(pelvis, [0, 5, 10, 15, 20])
        thigh = [round(math.degrees(k[1]), 6) for k in f.curve_on(paths["thigh_l"] + ".rotateY")[1]]
        self.assertEqual(thigh, [0, -12, -24, -36, -48])
        self.assertEqual(f.undo_calls[0], {"openChunk": True, "chunkName": "skeldarWalkRestore"})
        self.assertEqual(f.undo_calls[-1], {"closeChunk": True})

    @unittest.expectedFailure
    def test_restore_takes_the_walker_s_own_edits_off_too(self):
        """OPEN QUESTION, left pinned until the animator decides (scene.py restore_source): "the walk taken off: the marker and the kept cycle go" - but the
        walker's own edits (EDITS_ATTR: Fix posture, the mean pose's correction, the key poses') stay on the top
        joint, so a later Pick of the same walk brings them back on a skeleton whose walk was taken off."""
        paths = self.small()
        root = paths["root"]
        scene.capture_source(root)
        self.memo(root, walk="asd", version=4)
        scene.set_edits(root, {"walk": "asd", "posture": True})
        scene.restore_source(root)
        self.assertIsNone(scene.edits_of(root))

    def test_restore_without_a_kept_cycle_is_refused(self):
        paths = self.small()
        with self.assertRaises(scene.Refusal) as raised:
            scene.restore_source(paths["root"])
        self.assertIn("Hero keeps no original cycle", str(raised.exception))


# ---------------------------------------------------------------------------------------------- walk names, existence

class WalkNames(Base):

    def test_labels_and_kinds(self):
        self.assertEqual(scene.walk_label(None), "")
        self.assertEqual(scene.walk_label("asd"), "asd")
        self.assertEqual(scene.walk_label(scene.card_walk("Walk cycles/run.anim")), "run")
        self.assertFalse(scene.is_card(""))
        self.assertFalse(scene.is_own(None))

    def test_existence(self):
        self.assertFalse(scene.walk_exists(""))
        self.assertFalse(scene.walk_exists("asd"))
        self.save_synthetic("asd")
        self.assertTrue(scene.walk_exists("asd"))
        self.assertFalse(scene.walk_exists(scene.card_walk("Walk cycles/never.anim")))

    def test_a_card_whose_source_record_is_broken_is_read_again(self):
        header, frames = wcards.card_of_walk({"names": SMALL, "parents": [-1, 0, 1], "worlds": small_worlds(),
                                              "fps": 30.0, "up": [0, 1, 0], "name": "stroll", "start": 0,
                                              "statics": dict((leaf, {"parent": (SMALL[i - 1] if i else None),
                                                                      "canonical": leaf,
                                                                      "rest": flat(small_worlds()[i, 0])})
                                                              for i, leaf in enumerate(SMALL))})
        path = store.write(self.library, wcards.WALK_FOLDER, "stroll", header, frames=frames)
        name = scene.card_walk(wcards.relative(path, self.library))
        cache = scene.walk_path(name)
        with open(cache + scene.CARD_SOURCE, "w") as handle:
            handle.write("[not a dict]")
        os.remove(cache)
        self.assertEqual(scene.walk_path(name), cache)
        self.assertTrue(os.path.exists(cache))


# ---------------------------------------------------------------------------------------------- load_walk's cache

class LoadWalk(Base):

    def test_a_walk_not_saved_is_refused(self):
        with self.assertRaises(scene.Refusal) as raised:
            scene.load_walk("nope")
        self.assertIn("no saved walk named nope", str(raised.exception))
        with self.assertRaises(scene.Refusal):
            scene.fix_posture("nope")

    def test_fix_posture_judged_against_the_rest_when_the_idle_cannot_stand_on_the_walk(self):
        name = self.save_synthetic()

        def refuse(*a):
            raise wt.Refusal("the pose's skeleton has nothing for the walk's pelvis")
        self.swap(wp, "carried", refuse)
        report, line, fixed = scene.fix_posture(name)
        self.assertFalse(fixed)
        self.assertIn("nothing out of place; the UE5 idle was not used (the pose's skeleton has nothing for the "
                      "walk's pelvis) - judged against the rest", line)

    def test_fix_posture_with_no_idle_shipped(self):
        name = self.save_synthetic()
        self.swap(scene, "REFERENCE_FILE", os.path.join(self.temp, "none.wpose.gz"))
        self.assertIsNone(scene._reference())
        report, line, fixed = scene.fix_posture(name)
        self.assertFalse(fixed)
        self.assertEqual(line, "Fix posture: raw - nothing out of place")

    def test_the_reading_is_kept_per_clean_knobs_edits_and_file_time(self):
        name = self.save_synthetic()
        walk, statics, start, report = scene.load_walk(name)
        self.assertEqual((start, sorted(statics) == sorted(tc.NAMES)), (0, True))
        self.assertIs(scene.load_walk(name, {"stride": 1.5})[0], walk)                 # a model knob: same reading
        self.assertIs(scene.load_walk(name, {}, scene.empty_edits(name))[0], walk)     # empty edits: the same
        self.assertIs(scene.load_walk(name, {}, {"keys": some_keys()})[0], walk)        # key poses: on the result
        self.assertIsNot(scene.load_walk(name, {}, {"posture": True})[0], walk)
        fixed = scene.load_walk(name, {}, {"fix": a_fix(2.0)})[0]
        self.assertIsNot(fixed, walk)
        self.assertEqual(fixed.fix["height"], 2.0)
        self.assertEqual(walk.fix["height"], 0.0)
        self.assertIs(scene.load_walk(name, {}, {"fix": a_fix(2.0)})[0], fixed)
        self.assertIsNot(scene.load_walk(name, {}, {"fix": a_fix(2.5)})[0], fixed)
        path = wf.path_for(self.walks, name)
        os.utime(path, (os.path.getmtime(path) + 10, os.path.getmtime(path) + 10))
        self.assertIsNot(scene.load_walk(name)[0], walk)                              # the file changed

    def test_the_walk_carries_its_key_steps_or_why_not(self):
        name = self.save_synthetic()
        walk = scene.load_walk(name)[0]
        self.assertTrue(walk.key_steps)
        self.assertEqual(walk.key_note, "")

        def refuse(walk):
            raise kp.Refusal("the feet do not take turns")
        self.swap(kp, "find", refuse)
        refused = scene.load_walk(name, {"smooth": 1.0})[0]
        self.assertIsNone(refused.key_steps)
        self.assertEqual(refused.key_note, "the feet do not take turns")

    def test_at_most_six_readings_of_a_kind_and_file_are_kept(self):
        state = scene._state()
        for i in range(scene.CACHED_READINGS + 3):
            scene._cache(("walk", "a.walk.gz", i), i)
        scene._cache(("walk", "b.walk.gz", 0), "b")
        scene._cache(("pose", "a.walk.gz", 0), "p")
        kept = sorted(k[2] for k in state["loaded"] if k[:2] == ("walk", "a.walk.gz"))
        self.assertEqual(kept, list(range(3, scene.CACHED_READINGS + 3)))
        self.assertIn(("walk", "b.walk.gz", 0), state["loaded"])
        self.assertIn(("pose", "a.walk.gz", 0), state["loaded"])

    def test_forget_drops_every_reading_of_a_file(self):
        state = scene._state()
        state["loaded"].update({"a": 1, ("walk", "a", 1): 2, ("clean", "a", 1): 3, ("walk", "b", 1): 4})
        scene._forget("a")
        self.assertEqual(list(state["loaded"]), [("walk", "b", 1)])


# ---------------------------------------------------------------------------------------------- poses

def standing_pose():
    return dict((n, dict(tc.STATICS[n], world=tc.STATICS[n]["rest"])) for n in tc.NAMES)


class Poses(Base):

    def test_save_pose_writes_the_skeleton_as_it_stands(self):
        paths = self.small()
        self.fake.time = 12.0
        name, line = scene.save_pose(paths["root"])
        self.assertEqual(name, "root_pose")
        self.assertEqual(line, "saved root_pose%s: 3 bones of root at frame 12 | root has no skin: its rest is read "
                               "as it stands" % wf.POSE_SUFFIX)
        self.assertEqual(scene.pose_names(), ["root_pose"])
        back = wf.load_pose(wf.pose_path_for(self.walks, "root_pose"))[1]
        self.assertEqual(back["pelvis"]["world"], flat(small_worlds()[1, 0]))
        self.assertEqual(scene.save_pose(paths["root"], "hunch: 2")[0], "hunch_2")

    def test_a_saved_pose_carried_onto_the_walk_once(self):
        walk = self.save_synthetic()
        wf.save_pose(wf.pose_path_for(self.walks, "standing"), "standing", standing_pose())
        pose = scene.prepared_pose(walk, "standing")
        self.assertEqual(pose["scale"], 1.0)
        self.assertIs(scene.prepared_pose(walk, "standing"), pose)
        path = wf.pose_path_for(self.walks, "standing")
        os.utime(path, (os.path.getmtime(path) + 10, os.path.getmtime(path) + 10))
        self.assertIsNot(scene.prepared_pose(walk, "standing"), pose)                  # the pose changed
        with self.assertRaises(scene.Refusal):
            scene.prepared_pose(walk, "nope")

    def test_given_bones_are_cached_by_their_ident(self):
        walk = self.save_synthetic()
        bones = standing_pose()
        first = scene.prepared_pose(walk, "card", bones=bones, ident=("card:x", 1))
        self.assertIs(scene.prepared_pose(walk, "card", bones=bones, ident=("card:x", 1)), first)
        self.assertIsNot(scene.prepared_pose(walk, "card", bones=bones, ident=("card:x", 2)), first)

    def test_the_pose_copy_on_a_skeleton(self):
        self.fake.joint("|root")
        self.assertEqual(scene.pose_copy(None), "")
        self.assertEqual(scene.pose_copy("|root"), "")
        self.fake.nodes["|root"]["attrs"][scene.POSE_COPY] = "abc"
        self.assertEqual(scene.pose_copy("|root"), "abc")

    def card(self, folder, name):
        eye = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        bones = {"root": {"parent": None, "canonical": "root", "rest": eye, "world": eye},
                 "pelvis": {"parent": "root", "canonical": "pelvis", "rest": eye, "world": eye}}
        data = {"format": store.FORMAT, "kind": "character", "bones": bones, "character": {"label": name},
                "members": sorted(bones), "objects": []}
        return store.write(self.library, folder, name, data), bones

    def test_card_pose_the_card_the_copy_the_old_pose_and_none(self):
        self.fake.joint("|root")
        path, bones = self.card("", "goblin")
        rel = wcards.relative(path, self.library)
        name, got, note, ident = scene.card_pose(rel, root="|root")
        self.assertEqual((name, sorted(got), note), ("goblin", ["pelvis", "root"], ""))
        self.assertEqual(ident, (wcards.absolute(rel, self.library), wcards.stamp(path)))
        self.fake.nodes["|root"]["attrs"][scene.POSE_COPY] = wcards.pack(bones)
        shutil.rmtree(path)
        name, got, note, ident = scene.card_pose(rel, root="|root")
        self.assertEqual(name, "goblin")
        self.assertIn("gone", note)
        self.assertEqual(ident[0], "copy:" + rel)
        self.assertEqual(scene.card_pose(None, None, "|root"), (None, None, "", None))

    def test_card_pose_of_an_old_pose_name(self):
        wf.save_pose(wf.pose_path_for(self.walks, "hunch"), "hunch", standing_pose())
        name, got, note, ident = scene.card_pose(None, "hunch")
        self.assertEqual((name, note), ("hunch", ""))
        self.assertEqual(ident[0], wf.pose_path_for(self.walks, "hunch"))
        path, _ = self.card(wcards.MIGRATED_FOLDER, "hunch")                    # moved into the library
        name, got, note, ident = scene.card_pose(None, "hunch")
        self.assertEqual(sorted(got), ["pelvis", "root"])
        self.assertEqual(ident, (wcards.absolute(wcards.legacy_card("hunch"), self.library), wcards.stamp(path)))


# ---------------------------------------------------------------------------------------------- animate

class Animate(Base):

    def setUp(self):
        Base.setUp(self)
        self.walk_name = self.save_synthetic("asd")
        self.fake.joint("|root")

    def test_a_pose_named_by_its_old_name_walks_through_its_migrated_card(self):
        path = store.write(self.library, wcards.MIGRATED_FOLDER, "standing",
                           {"format": store.FORMAT, "kind": "character", "bones": standing_pose(),
                            "character": {"label": "standing"}, "members": sorted(tc.NAMES), "objects": []})
        anim = scene.animate("|root", self.walk_name, {"pose": 1.0}, pose_name="standing")
        self.assertEqual(anim.pose_card, wcards.legacy_card("standing"))
        self.assertEqual(anim.pose_label, "standing")
        self.assertIsNotNone(anim.pose)
        self.assertEqual(wcards.unpack(anim.packed), json.loads(json.dumps(standing_pose())))
        self.assertTrue(os.path.isdir(path))
        self.assertEqual(anim.result.info["knobs"]["pose"], 1.0)

    def test_a_pose_at_no_share_is_not_read(self):
        anim = scene.animate("|root", self.walk_name, {"pose": 0.0}, pose_card="gone/card.pose")
        self.assertIsNone(anim.pose)
        self.assertEqual(anim.pose_label, "card")
        self.assertIsNone(anim.packed)

    def test_a_pose_card_gone_with_no_copy_is_refused(self):
        with self.assertRaises(scene.Refusal) as raised:
            scene.animate("|root", self.walk_name, {"pose": 1.0}, pose_card="gone/card.pose")
        self.assertIn("pose card card is gone", str(raised.exception))

    def test_with_steps_the_result_is_read_as_a_walk_and_in_place_moves_it_back(self):
        moving = scene.animate("|root", self.walk_name, {}, with_steps=True)
        self.assertIsNotNone(moving.rw)
        self.assertTrue(moving.steps)
        placed = scene.animate("|root", self.walk_name, {"in_place": 1.0}, with_steps=True)
        self.assertEqual(placed.result.info["in_place"], 1.0)
        root = placed.walk.index["root"]
        travel = placed.result.worlds[root, :, 3, :3] - placed.result.worlds[root, 0, 3, :3]
        self.assertLess(float(np.abs(travel @ placed.walk.fwd).max()), 1e-6)
        self.assertGreater(float(np.abs(moving.result.worlds[root, -1, 3, :3] -
                                        moving.result.worlds[root, 0, 3, :3]).max()), 10.0)

    def test_the_parameters_carry_the_clean_knobs_of_given(self):
        anim = scene.animate("|root", self.walk_name, {"seam": 5.0}, params={"pins": []})
        self.assertEqual(anim.params["clean"]["seam"], wc.knobs({"seam": 5.0})["seam"])
        self.assertEqual(anim.given["seam"], wc.knobs({"seam": 5.0})["seam"])
        self.assertIsNotNone(anim.values_asked)

    def test_walker_animation_reads_the_walker_s_own_memo(self):
        with self.assertRaises(scene.Refusal):
            scene.walker_animation("|root")
        calls = []
        self.swap(scene, "animate", lambda *a, **kw: calls.append((a, kw)) or "anim")
        self.memo("|root", walk="asd", version=2, knobs={"stride": 1.1}, pose="hunch", parts=["torso"],
                  pose_card="Walk poses/hunch.pose")
        self.assertEqual(scene.walker_animation("|root"), "anim")
        args, kw = calls[-1]
        self.assertEqual(args, ("|root", "asd", {"stride": 1.1}, "hunch", ("torso",)))
        self.assertEqual(kw, {"pose_card": "Walk poses/hunch.pose", "params": None, "with_steps": True})
        self.memo("|root", walk="asd", version=4, params={"changes": {"step": ["ratio", 1.1]}})
        scene.walker_animation("|root", with_steps=False)
        self.assertEqual(calls[-1][1]["params"]["changes"], {"step": ("ratio", 1.1)})
        self.assertEqual(calls[-1][0][3:], (None, scene.ALL_PARTS))


class Evaluated(unittest.TestCase):

    def test_kept_on_the_walk_at_most_four(self):
        calls = []

        class Walk(object):
            def evaluate(self, knobs, pose):
                calls.append(dict(knobs))
                return object()
        walk = Walk()
        first = scene.evaluated(walk, {"stride": 1.0}, None)
        self.assertIs(scene.evaluated(walk, {"stride": 1.0}, None), first)
        for i in range(scene.EVALS_KEPT):
            scene.evaluated(walk, {"stride": 1.1 + i}, None)
        self.assertIsNot(scene.evaluated(walk, {"stride": 1.0}, None), first)          # pushed out
        self.assertEqual(len(walk._skeldar_evals), scene.EVALS_KEPT)
        prepared = object()
        a = scene.evaluated(walk, {"stride": 1.0}, {"p": 1}, prepared, ("torso",))
        self.assertIsNot(a, scene.evaluated(walk, {"stride": 1.0}, {"p": 1}, object(), ("torso",)))


class Params(unittest.TestCase):

    def test_broken_changes_are_passed_over(self):
        p = scene.normal_params({"changes": {"step": 1.2, "bounce": ["ratio", "much"], "lean": None,
                                             "height": ["offset", 2]},
                                 "macros": {"weight": "", "speed": None}, "strength": None, "pose": None,
                                 "in_place": 0.4})
        self.assertEqual(p["changes"], {"height": ("offset", 2.0)})
        self.assertEqual(p["macros"], {})
        self.assertEqual((p["strength"], p["pose"], p["in_place"]), (0.0, 0.0, 0.0))


# ---------------------------------------------------------------------------------------------- apply's line

class FakeRetarget(object):
    info = {}

    def __init__(self, walk, statics, bones, place):
        self.place = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
        self.given_place = place

    def frames(self, result, knee_pops=True):
        FakeRetarget.knee_pops = knee_pops
        return {}, dict({"scale": 0.5, "drop": [0.0], "short": 0.0}, **FakeRetarget.info)

    def written(self):
        return ["pelvis"]

    def translated(self):
        return []


class Apply(Base):

    def setUp(self):
        Base.setUp(self)
        self.fake.joint("|root")
        self.swap(scene, "read_bones", lambda root: ({}, ""))
        self.swap(wt, "Retarget", FakeRetarget)
        FakeRetarget.info = {}
        self.writes = []
        self.swap(scene, "channel_values", lambda bones, frames, written, translated: ({}, {}))
        self.swap(scene, "write_curves",
                  lambda values, static, start, in_place=False: self.writes.append(in_place) or (1, {}))
        self.info = {"knobs": {"pose": 0.0, "in_place": 0.0}, "stride_cm": 60.0, "speed": 1.5, "lowered": 0.0}
        self.anim_kw = {}
        self.swap(scene, "animate", lambda *a, **kw: self.anim())

    def anim(self):
        result = wm.Result(None, 24, self.info)
        kw = dict(walk="WALK", statics={}, start=0, report=Report(), given={"seam": 4.0}, params=None,
                  result=result, packed=None, pose_label="", pose_card=None, edits_note="", edits=scene.empty_edits(),
                  pose=None, layer_note="", pose_note="", values_asked=None)
        kw.update(self.anim_kw)
        return scene.Animation(**kw)

    def test_the_line_names_the_walk_the_target_and_its_size(self):
        result, info, line = scene.apply("|root", "asd")
        self.assertTrue(line.startswith("asd on root, 1 bones x0.50 | 24 fr (0-24), stride 30 cm, 0.75 m/s"), line)
        self.assertEqual(self.writes, [False])
        memo = scene.memo_of("|root")
        self.assertEqual((memo["walk"], memo["version"], memo["listed"], memo["working"]), ("asd", 4, True, False))
        self.assertEqual(memo["knobs"]["seam"], wc.knobs({"seam": 4.0})["seam"])
        self.assertEqual(memo["keys"], scene.keys_print("|root"))
        self.assertEqual(scene._state()["target"], self.fake.ls("|root", uuid=True)[0])
        self.assertTrue(FakeRetarget.knee_pops)
        self.assertEqual(self.fake.undo_calls[0], {"openChunk": True, "chunkName": "skeldarWalkApply"})
        self.assertIsNotNone(scene.edits_of("|root"))                     # no edits kept before: kept now

    def test_unrecorded_re_key_writes_in_place_and_opens_no_chunk(self):
        scene.apply("|root", "asd", record=False)
        self.assertEqual(self.writes, [True])
        self.assertNotIn("openChunk", [k for call in self.fake.undo_calls for k in call])

    def test_the_pose_copy_is_kept_once(self):
        self.anim_kw.update(packed="PACKED", pose=object(), pose_label="goblin")
        self.info["knobs"]["pose"] = 0.75
        line = scene.apply("|root", "asd", parts=("torso",))[2]
        self.assertEqual(scene.pose_copy("|root"), "PACKED")
        self.assertIn(" | pose goblin x0.75 (torso)", line)
        line = scene.apply("|root", "asd", parts=())[2]
        self.assertIn(" | pose goblin x0.75 (no part)", line)
        line = scene.apply("|root", "asd")[2]
        self.assertIn(" | pose goblin x0.75 |", line + " |")

    def test_every_part_of_the_line(self):
        self.anim_kw.update(pose=object(), pose_label="sword", pose_note="pose card sword is gone",
                            edits_note="edits dropped", layer_note="the key poses: no steps",
                            report=Report(True, "looped"),
                            edits=dict(scene.empty_edits("asd"), posture=True))
        self.info.update({"knobs": {"pose": 1.0, "in_place": 1.0}, "lowered": 2.0,
                          "leg_match": {"on": True, "keep": 0.15, "hips_deg": 36.4},
                          "ground": {"l": [(0.6, 0.55)], "r": [(0.6, 0.6)]},
                          "balance": {"carry": 3.2}})
        FakeRetarget.info = {"drop": [0.0, 1.5], "short": 0.4, "pops": {"fixed": 2, "found": {"l": [9, 24]}}}
        self.swap(scene, "read_bones", lambda root: ({}, "root has no skin"))
        held = {"weapon_r": "weapon_parentConstraint1"}
        self.swap(scene, "write_curves", lambda values, static, start, in_place=False: (1, held))
        line = scene.apply("|root", "asd")[2]
        for part in ("pose sword x1.00", "legs matched x0.15, hips 36 deg to the spine",
                     "pelvis down 1.5 cm where the legs fall short", "knee pops smoothed: 2 (L 9, 24)",
                     "the walk sinks 2.0 cm at the contacts", "a foot falls 0.4 cm short",
                     "feet down x0.55-0.60 of x0.60 asked", "balance carries the pelvis 3.2 cm", "in place",
                     "posture fixed", "edits dropped", "the key poses: no steps", "looped", "pose card sword is gone",
                     "left to their drivers: weapon_r (weapon_parentConstraint1)", "root has no skin"):
            self.assertIn(" | " + part, line)
        self.assertRegex(line, r" \| [0-9.]+ s$")

    def test_quiet_parts_say_nothing(self):
        self.anim_kw.update(pose=object(), pose_label="p")
        self.info.update({"leg_match": {"on": True, "keep": 0.8, "hips_deg": 0.4},
                          "ground": {"l": [(0.6, 0.61)]}, "balance": {"note": "no masses"}})
        line = scene.apply("|root", "asd")[2]
        self.assertIn("legs matched x0.80 |", line)
        self.assertNotIn("hips", line)
        self.assertNotIn("feet down", line)
        self.assertIn(" | no balance: no masses", line)
        self.assertNotIn("in place", line)

    def test_with_parameters_ground_time_in_shares_and_a_failed_measure_never_fails_the_keys(self):
        self.anim_kw.update(params=scene.normal_params({"knee_pops": False}), values_asked={"step": 60.0})
        self.info["ground"] = {"l": [(0.6, 0.5)]}

        def broken(walk, result):
            raise RuntimeError("no measure")
        self.swap(scene, "diagnosis", broken)
        result, info, line = scene.apply("|root", "asd")
        self.assertIn(" | feet down 50-50 % of 60 % asked", line)
        self.assertEqual((info["values"], info["measured"], info["diagnosis"]), ({"step": 60.0}, {}, []))
        self.assertFalse(FakeRetarget.knee_pops)
        self.assertIn("params", scene.memo_of("|root"))

    def test_edits_carried_are_written_back(self):
        written = []
        self.swap(scene, "set_edits", lambda root, edits: written.append(edits))
        self.fake.nodes["|root"]["attrs"][scene.EDITS_ATTR] = json.dumps({"walk": "asd"})
        scene.apply("|root", "asd")
        self.assertEqual(written, [])                                   # kept edits, nothing new: untouched
        self.anim_kw.update(edits_note="dropped")
        scene.apply("|root", "asd")
        self.assertEqual(len(written), 1)

    def test_the_place_kept_from_the_first_walk(self):
        self.memo("|root", walk="asd", version=4, place=[1.0] * 16, working=True)
        places = []
        real = FakeRetarget.__init__

        def init(self_, walk, statics, bones, place):
            places.append(place)
            real(self_, walk, statics, bones, place)
        self.swap(FakeRetarget, "__init__", init)
        scene.apply("|root", "asd")
        self.assertEqual(places, [[1.0] * 16])
        self.assertTrue(scene.memo_of("|root")["working"])               # Pick's choice survives a re-key


# ---------------------------------------------------------------------------------------------- the package, files, pose, target

class Package(unittest.TestCase):

    def test_show_window_opens_the_card(self):
        import maya_walk
        from maya_walk import panel
        old = panel.show_window
        panel.show_window = lambda: "shown"
        try:
            self.assertEqual(maya_walk.show_window(), "shown")
        finally:
            panel.show_window = old


class Files(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="walkfiles_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_a_file_that_is_not_gzip_json_is_refused_by_name(self):
        for opener, text in ((lambda p: open(p, "w"), "plain"), (lambda p: gzip.open(p, "wt"), "{nope")):
            path = os.path.join(self.folder, "x" + wf.SUFFIX)
            with opener(path) as handle:
                handle.write(text)
            with self.assertRaises(wf.Refusal) as raised:
                wf.load(path)
            self.assertIn("x%s is not a saved walk" % wf.SUFFIX, str(raised.exception))
        with self.assertRaises(wf.Refusal):
            wf.load(os.path.join(self.folder, "missing" + wf.SUFFIX))

    def test_a_newer_version_is_refused(self):
        path = os.path.join(self.folder, "x" + wf.SUFFIX)
        with gzip.open(path, "wt") as handle:
            json.dump({"format": wf.FORMAT, "version": wf.VERSION + 1, "names": []}, handle)
        with self.assertRaises(wf.Refusal) as raised:
            wf.load(path)
        self.assertIn("version %d" % (wf.VERSION + 1), str(raised.exception))

    def test_poses_written_into_a_new_folder_overwritten_and_refused(self):
        path = wf.pose_path_for(os.path.join(self.folder, "new", "deeper"), "p")
        bones = {"root": {"parent": None, "canonical": "root", "rest": [0.0] * 16, "world": [1.0] * 16}}
        wf.save_pose(path, "p", bones)
        bones["root"]["world"] = [2.0] * 16
        wf.save_pose(path, "p", bones)
        self.assertEqual(wf.load_pose(path)[1]["root"]["world"], [2.0] * 16)
        self.assertFalse(os.path.exists(path + ".part"))
        self.assertEqual(wf.pose_names_in(os.path.join(self.folder, "none")), [])
        self.assertEqual(wf.names_in(os.path.join(self.folder, "none")), [])
        with open(path, "wb") as handle:
            handle.write(b"broken")
        with self.assertRaises(wf.Refusal):
            wf.load_pose(path)
        with gzip.open(path, "wt") as handle:
            json.dump({"format": wf.FORMAT, "name": "p", "bones": {}}, handle)
        with self.assertRaises(wf.Refusal) as raised:
            wf.load_pose(path)
        self.assertIn("not a pose this tool reads", str(raised.exception))

    def test_safe_names(self):
        self.assertEqual(wf.safe_name("My walk: 01"), "My_walk_01")
        self.assertEqual(wf.safe_name("..x.."), "x")
        self.assertEqual(wf.safe_name(""), "walk")
        self.assertEqual(wf.safe_name(None), "walk")

    def template(self):
        return wf.read_template(os.path.join(tw.PLUGIN, "assets", "manny_skeleton_template.json"))

    def test_template_rests_skips_parents_it_disagrees_on_and_tiny_bones(self):
        template = self.template()
        positions = dict((n, tuple(t["world_matrix"][12:15])) for n, t in template.items())
        parents = dict((n, t["parent"]) for n, t in template.items())
        rests = wf.template_rests(positions, parents, template)
        self.assertIsNotNone(rests)
        self.assertEqual(rests["pelvis"], template["pelvis"]["world_matrix"])
        reparented = dict(parents, hand_l="spine_01")                 # a different hierarchy for one bone: skipped
        self.assertIsNotNone(wf.template_rests(positions, reparented, template))
        tiny = dict(template, tiny={"parent": "pelvis", "world_matrix": template["pelvis"]["world_matrix"][:12] +
                                    [v + 0.3 for v in template["pelvis"]["world_matrix"][12:15]] + [1.0]})
        rests = wf.template_rests(dict(positions, tiny=tuple(tiny["tiny"]["world_matrix"][12:15])),
                                  dict(parents, tiny="pelvis"), tiny)          # a bone under a centimetre: no vote
        self.assertEqual(rests["tiny"], tiny["tiny"]["world_matrix"])
        legless = dict((n, p) for n, p in parents.items() if n != "calf_r")
        self.assertIsNone(wf.template_rests(positions, legless, template))
        grown = dict((n, tuple(2.0 * v for v in p)) for n, p in positions.items())
        self.assertIsNone(wf.template_rests(grown, parents, template))


class PoseGaps(unittest.TestCase):

    def test_lean_room_without_a_neck_is_whole(self):
        w = tw.walk()
        rest = {"root": {"world": flat(np.eye(4))}}
        self.assertEqual(wp.lean_room({"pelvis": np.eye(4)}, w, rest, wm), 1.0)

    def test_lean_room_is_whole_when_the_rest_already_leans_past_the_limit(self):
        w = tw.walk()
        rest = {"root": {"world": flat(np.eye(4))}, "pelvis": {"world": flat(tw.mat(np.eye(3), [0, 90, 0]))},
                "neck_01": {"world": flat(tw.mat(np.eye(3), [0, 90, 200]))}}
        out = {"pelvis": tw.mat(np.eye(3), [0, 90, 0]), "neck_01": tw.mat(np.eye(3), [0, 150, 10])}
        self.assertEqual(wp.lean_room(out, w, rest, wm), 1.0)

    def test_a_weapon_the_pose_holds_is_read_in_its_hand(self):
        from tests.test_walktarget import statics_of
        names, parents, worlds = tw.synthetic(P=24)
        h = names.index("hand_r")
        carry = tw.mat(tw.rot_x(30.0), [5.0, -3.0, 12.0])
        weapon = np.array([carry @ worlds[h, f] for f in range(worlds.shape[1])])
        c = wm.Clip(names + ["weapon_r"], parents + [h], np.concatenate([worlds, weapon[None]]), fps=30.0,
                    up=(0, 1, 0), name="armed")
        w = wm.analyse(c)
        self.assertEqual(w.follows[w.index["weapon_r"]][0], h)
        bones = statics_of(c)
        for j, name in enumerate(c.names):
            bones[name]["world"] = [float(v) for v in c.worlds[j, 5].reshape(16)]
        grip = tw.mat(tw.rot_z(20.0), [0.0, 10.0, 0.0])
        bones["weapon_r"]["world"] = flat(grip @ c.worlds[h, 5])
        pose = wp.prepare(w, statics_of(c), bones, wm, wt)
        self.assertTrue(np.allclose(pose["weapons"][w.index["weapon_r"]], grip, atol=1e-6))

    def test_a_pose_missing_the_walk_s_head_or_legs_is_refused(self):
        from tests.test_walktarget import statics_of
        c = tw.clip()
        w = wm.analyse(c)
        bones = statics_of(c)
        for j, name in enumerate(c.names):
            bones[name]["world"] = [float(v) for v in c.worlds[j, 0].reshape(16)]
        del bones["head"]
        with self.assertRaises(wt.Refusal) as raised:
            wp.prepare(w, statics_of(c), bones, wm, wt)
        self.assertIn("head", str(raised.exception))


class TargetGaps(unittest.TestCase):

    def test_small_pure_helpers(self):
        self.assertEqual(wt._angle([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]), 0.0)
        self.assertAlmostEqual(wt._angle([1.0, 0.0, 0.0], [0.0, 2.0, 0.0]), math.pi / 2.0)
        self.assertEqual(wt._drop_for([0, 100, 0], [0, 20, 0], 90.0), 0.0)            # within reach
        self.assertAlmostEqual(wt._drop_for([0, 100, 0], [0, 0, 0], 90.0), 10.0)
        self.assertEqual(wt._drop_for([0, 0, 0], [500, 0, 0], 90.0), 0.0)            # no drop reaches it
        stance = wt._stance(wm.Result(None, 4, {}), "l", 4)
        self.assertTrue(stance.all())
        stance = wt._stance(wm.Result(None, 6, {"contacts": {"l": [(4, 1)]}}), "l", 6)
        self.assertEqual(stance.tolist(), [True, True, False, False, True, True])

    def test_the_pops_line(self):
        self.assertEqual(wt.pops_line({"fixed": 3, "found": {"r": [33], "l": [9, 24]}, "drop": 0.8, "left": 1}),
                         "knee pops smoothed: 3 (L 9, 24; R 33), pelvis down up to 0.8 cm, 1 left")
        self.assertEqual(wt.pops_line({}), "knee pops smoothed: 0 ()")


if __name__ == "__main__":
    unittest.main()

"""Walk Builder's mean pose rig (maya_walk.meanrig) on fakes: no Maya scene.

The scene the rig tools see is a FakeCmds over a World - Main nodes with their markers, rigs (maya_rigs.Rig) whose
game skeleton is the synthetic walker's (test_walkmodel), controls with time curves, the walkers' top joints with
their UUIDs. The Pose Library's solve stands a fake rig in the card it is given (re-rooted on the rig's own root, as
the solve leaves Main and the root where they stand), Add Character adds a rig at the point asked, Delete removes
it. The walk maths - meanpose, keyposes, pose._onto - are the real ones: what a rig shows is read back through them.

test_walk_keyrig imports the fakes from here."""

import contextlib
import io
import json
import math
import sys
import types
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walktarget import statics_of

wm = T.wm
mp = T.load("meanpose")
kp = T.load("keyposes")
wscene = T.load("scene")
meanrig = T.load("meanrig")
keyrig = T.load("keyrig")

import maya_rigs                                                 # noqa: E402
from maya_poselib import apply as papply                         # noqa: E402
from maya_poselib import scene as pscene                         # noqa: E402
from maya_scenesetup import catalog, character, cliplabel, deletion   # noqa: E402

UP = np.array([0.0, 1.0, 0.0])


def translate(x, y, z):
    m = np.eye(4)
    m[3, :3] = (x, y, z)
    return m


def flat(m):
    return [float(v) for v in np.asarray(m, float).reshape(16)]


def mat(values):
    return np.array(values, float).reshape(4, 4)


def angle_deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


# ---- the fake scene ----

class World(object):
    """What the fakes share: nodes and their attributes, the rigs and their game skeletons, the selection."""

    def __init__(self):
        self.attrs = {}                 # node -> {attr: value}
        self.uuids = {}                 # node -> uuid
        self.mats = {}                  # node -> 4x4 world
        self.timed = {}                 # node -> f(time) -> 16 floats (a walker's root over time)
        self.rigs = []
        self.bones = {}                 # namespace -> {leaf: bone}
        self.members = {}               # control set -> [members]
        self.transforms = set()
        self.curves = {}                # control -> [curve]
        self.curve_types = {}
        self.deleted = []
        self.selection = []
        self.auto = True
        self.locked = set()
        self.depth = 0                  # inside an Unrecorded block
        self.writes = []                # (plug, value, unrecorded)
        self.jobs = set()
        self.killed = []
        self.playback = (0.0, 24.0)
        self.skeleton_reads = 0
        self.posed = []                 # (namespace, card name)
        self.added = []                 # (catalog key, at)
        self.labels = []
        self.label_error = None
        self.delete_calls = []
        self.statics = statics_of(T.clip())

    # -- nodes --
    def node(self, name, uuid=None, matrix=None, **attrs):
        self.attrs.setdefault(name, {}).update(attrs)
        if uuid:
            self.uuids[name] = uuid
        if matrix is not None:
            self.mats[name] = np.array(matrix, float)
        return name

    def exists(self, name):
        if "." in name:
            node, attr = name.split(".", 1)
            return node in self.attrs and attr.split("[")[0] in self.attrs[node]
        return name in self.attrs

    # -- rigs --
    def add_rig(self, at=(0.0, 0.0, 0.0), ns=None, skeleton=True):
        """A Manny rig standing at `at` (its Main there, its game skeleton at rest on it)."""
        if ns is None:
            taken = set(r.namespace for r in self.rigs)
            ns, i = "Manny_Rig", 0
            while ns in taken:
                i += 1
                ns = "Manny_Rig%d" % i
        rig = maya_rigs.Rig(ns, ns + ":ControlSet", ns + ":Main", ns + ":Group",
                            ("|%s:root" % ns) if skeleton else "")
        self.node(rig.main, matrix=translate(*at))
        bones = {}
        for leaf, b in self.statics.items():
            bone = dict(b)
            bone["world"] = flat(mat(b["rest"]) @ translate(*at))
            bone["path"] = "%s:%s" % (ns, leaf)
            bones[leaf] = bone
        self.bones[ns] = bones
        ctrl, locked, shape = ns + ":FKSpine1_M", ns + ":FKLocked_M", ns + ":FKSpine1_MShape"
        for c in (ctrl, locked):
            self.node(c, rotateX=0.0)
            self.transforms.add(c)
        self.node(shape)
        self.members[rig.control_set] = [ctrl, locked, shape]
        self.locked.add(locked + ".rotateX")
        self.curves[ctrl] = [ns + ":FKSpine1_M_rotateX", ns + ":FKSpine1_M_sdk"]
        self.curve_types[ns + ":FKSpine1_M_rotateX"] = "animCurveTA"
        self.curve_types[ns + ":FKSpine1_M_sdk"] = "animCurveUA"
        for side in ("L", "R"):
            self.node("%s:FKIKLeg_%s" % (ns, side), FKIKBlend=0.0)
            self.node("%s:PoleLeg_%s" % (ns, side), translate=[(1.0, 2.0, 3.0)])
        self.rigs.append(rig)
        return rig

    def rig(self, ns):
        return [r for r in self.rigs if r.namespace == ns][0]

    def world_of(self, ns, leaf):
        return mat(self.bones[ns][leaf]["world"])

    def below(self, leaf):
        """`leaf` and every bone under it (the synthetic skeleton)."""
        kids = {}
        for name, b in self.statics.items():
            kids.setdefault(b.get("parent"), []).append(name)
        out, stack = [], [leaf]
        while stack:
            n = stack.pop()
            out.append(n)
            stack.extend(kids.get(n, []))
        return out

    def turn(self, ns, leaf, rot):
        """The bone `leaf` of a rig and everything under it turned by `rot` (world axes) about the bone - a control
        turned by the animator."""
        pivot = self.world_of(ns, leaf)[3, :3].copy()
        for n in self.below(leaf):
            w = self.world_of(ns, n)
            w[:3, :3] = w[:3, :3] @ rot
            w[3, :3] = pivot + (w[3, :3] - pivot) @ rot
            self.bones[ns][n]["world"] = flat(w)

    def lower(self, ns, d):
        """The rig's pelvis (and the body over it) moved `d` cm along up, each leg solved again onto its ankle - an
        IK rig's RootX_M moved: the feet stay where they stand."""
        legs = set()
        for side in ("l", "r"):
            legs.update(self.below("thigh_" + side))
        old = dict((n, self.world_of(ns, n)) for n in self.statics)
        for n in self.below("pelvis"):
            if n in legs:
                continue
            w = old[n].copy()
            w[3, :3] += d * UP
            self.bones[ns][n]["world"] = flat(w)
        for side in ("l", "r"):
            self._solve_leg(ns, side, old, d * UP, np.zeros(3))

    def move_foot(self, ns, side, delta):
        """A foot moved `delta` (world), its leg solved again from the hip that stays - an IK foot control moved."""
        old = dict((n, self.world_of(ns, n)) for n in self.statics)
        self._solve_leg(ns, side, old, np.zeros(3), np.asarray(delta, float))

    def turn_knee(self, ns, side, degrees):
        """A knee turned `degrees` about its leg's line, hip and ankle where they stand - an IK pole moved."""
        old = dict((n, self.world_of(ns, n)) for n in self.statics)
        th, ca, fo = ("%s_%s" % (b, side) for b in mp.LEGS)
        h0, a0 = old[th][3, :3], old[fo][3, :3]
        e = (a0 - h0) / np.linalg.norm(a0 - h0)
        rot = wm.exp_rot(-e * math.radians(degrees))
        for n in self.below(th):
            if n in self.below(fo):
                continue
            w = old[n].copy()
            w[:3, :3] = w[:3, :3] @ rot
            w[3, :3] = h0 + (w[3, :3] - h0) @ rot
            self.bones[ns][n]["world"] = flat(w)

    def _solve_leg(self, ns, side, old, hip_move, foot_move):
        th, ca, fo = ("%s_%s" % (b, side) for b in mp.LEGS)
        h0, k0, a0 = old[th][3, :3], old[ca][3, :3], old[fo][3, :3]
        h1, a1 = h0 + hip_move, a0 + foot_move
        l1, l2 = float(np.linalg.norm(k0 - h0)), float(np.linalg.norm(a0 - k0))
        knee, _, _ = wm.two_bone(h1, a1, l1, l2, k0 - h0, 1.0)
        rt, rc = mp._leg_turns(h0, k0, a0, h1, knee, a1)
        self.bones[ns][th]["world"] = flat(wm.matrix(old[th][:3, :3] @ rt, h1))
        self.bones[ns][ca]["world"] = flat(wm.matrix(old[ca][:3, :3] @ rc, knee))
        for n in self.below(fo):
            w = old[n].copy()
            w[3, :3] += foot_move
            self.bones[ns][n]["world"] = flat(w)
        for n in self.below(th):
            if n in (th, ca) or n in self.below(fo):
                continue
            parent = self.statics[n]["parent"]
            local = old[n] @ np.linalg.inv(old[parent])
            self.bones[ns][n]["world"] = flat(local @ self.world_of(ns, parent))

    def move_main(self, ns, matrix):
        """The rig's Main moved by hand: the whole rig carried with it."""
        rig = self.rig(ns)
        carry = np.linalg.inv(self.mats[rig.main]) @ np.asarray(matrix, float)
        self.mats[rig.main] = np.asarray(matrix, float)
        for b in self.bones[ns].values():
            b["world"] = flat(mat(b["world"]) @ carry)

    def stand(self, ns, data):
        """The Pose Library's solve, faked: the rig's bones on the card's worlds, re-rooted on the rig's own root."""
        bones = self.bones[ns]
        rel = np.linalg.inv(mat(data["bones"]["root"]["world"])) @ mat(bones["root"]["world"])
        for leaf, b in data["bones"].items():
            if leaf in bones:
                bones[leaf]["world"] = flat(mat(b["world"]) @ rel)
                bones[leaf].pop("drive", None)
        self.posed.append((ns, data["name"]))


class FakeCmds(object):
    """The maya.cmds calls of meanrig and keyrig, on a World."""

    def __init__(self, world):
        self.w = world

    def objExists(self, name):
        return self.w.exists(name)

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.w.attrs.get(node, {})

    def addAttr(self, node, longName=None, dataType=None):
        self.w.attrs.setdefault(node, {})[longName] = ""

    def setAttr(self, plug, *value, **kw):
        if plug in self.w.locked:
            raise RuntimeError("locked: %s" % plug)
        node, attr = plug.split(".", 1)
        if node not in self.w.attrs:
            raise RuntimeError("No object matches name: %s" % plug)
        self.w.attrs[node][attr] = value[0] if len(value) == 1 else list(value)
        self.w.writes.append((plug, self.w.attrs[node][attr], self.w.depth > 0))

    def getAttr(self, plug, settable=False, time=None):
        node, attr = plug.split(".", 1)
        if time is not None and attr == "worldMatrix[0]":
            if node not in self.w.timed:
                raise RuntimeError("No object matches name: %s" % plug)
            return self.w.timed[node](time)
        if node not in self.w.attrs or attr not in self.w.attrs[node]:
            raise RuntimeError("No object matches name: %s" % plug)
        if settable:
            return plug not in self.w.locked
        return self.w.attrs[node][attr]

    def ls(self, *args, **kw):
        if kw.get("selection"):
            return list(self.w.selection)
        arg = args[0] if args else None
        if kw.get("uuid"):
            return [self.w.uuids[arg]] if arg in self.w.uuids else []
        if isinstance(arg, (list, tuple)):
            return [a for a in arg if self.w.exists(a)]
        found = [n for n, u in self.w.uuids.items() if u == arg]
        if found:
            return found
        return [arg] if arg and self.w.exists(arg) else []

    def xform(self, node, query=False, worldSpace=False, matrix=False, translation=False):
        m = self.w.mats.get(node)
        if m is None:
            raise RuntimeError("No object matches name: %s" % node)
        return flat(m) if matrix else [float(v) for v in m[3, :3]]

    def sets(self, name, query=False):
        return list(self.w.members.get(name, []))

    def objectType(self, node, isAType=None):
        return node in self.w.transforms

    def listConnections(self, node, source=True, destination=True, type=None):
        return [c for c in self.w.curves.get(node, []) if c in self.w.curve_types]

    def nodeType(self, node):
        return self.w.curve_types[node]

    def delete(self, nodes):
        for n in nodes:
            self.w.curve_types.pop(n, None)
            self.w.deleted.append(n)

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.w.auto
        self.w.auto = state

    def select(self, nodes, replace=False):
        self.w.selection = list(nodes)

    def scriptJob(self, exists=None, kill=None, force=False):
        if exists is not None:
            return exists in self.w.jobs
        self.w.jobs.discard(kill)
        self.w.killed.append(kill)

    def playbackOptions(self, query=False, minTime=False, maxTime=False):
        return self.w.playback[0] if minTime else self.w.playback[1]


class Recorded(object):
    """scene.Unrecorded, faked: the World knows its writes are unrecorded."""

    def __init__(self, world):
        self.w = world

    def __enter__(self):
        self.w.depth += 1

    def __exit__(self, *exc):
        self.w.depth -= 1
        return False


class FakeScene(object):
    """maya_walk.scene as the rig tools use it: the walkers' memos and edits held here, the walker's animation the
    synthetic walker's (its mean pose correction and key edits put on it with the real maths); every pure function
    the real module's."""

    Refusal = wscene.Refusal

    def __init__(self, world):
        self.world = world
        self.memos = {}
        self.edits = {}
        self.edit_calls = []
        self.applied = []
        self.no_steps = None            # a layer note: the walker's steps were not read
        self.anim_calls = []
        self._walks = {}

    def __getattr__(self, name):
        return getattr(wscene, name)

    def Unrecorded(self):
        return Recorded(self.world)

    def walker(self, root, uuid, walk="asd", at=(0.0, 0.0, 0.0), **memo):
        self.world.node(root, uuid=uuid, matrix=translate(*at))
        self.memos[root] = dict({"walk": walk, "version": 4}, **memo)
        return root

    def memo_of(self, root):
        return dict(self.memos.get(root) or {})

    def _set_memo(self, root, memo):
        self.memos[root] = dict(memo)

    def walkers(self):
        return sorted(r for r, m in self.memos.items() if m.get("walk") and m.get("listed", True))

    def working(self):
        return [r for r in self.walkers() if self.memos[r].get("working")]

    def walker_label(self, root):
        return root.rsplit("|", 1)[-1]

    def walker_edits(self, root, walk_name):
        edits = self.edits.get(root)
        if edits is None:
            return wscene.empty_edits(walk_name), ""
        return self._copy(edits), ""

    def set_edits(self, root, edits):
        self.edit_calls.append(root)
        self.edits[root] = self._copy(edits)

    @staticmethod
    def _copy(edits):
        """Through their files' plain data, as the walker's attribute holds them."""
        return {"walk": edits.get("walk") or "", "fix": mp.loads(mp.dumps(edits.get("fix") or mp.empty())),
                "keys": kp.loads(kp.dumps(edits.get("keys") or {})), "posture": bool(edits.get("posture"))}

    def apply(self, root, walk, knobs=None, pose=None, parts=(), record=True, pose_card=None, params=None):
        self.applied.append({"root": root, "walk": walk, "knobs": knobs, "pose": pose, "parts": parts,
                             "record": record, "pose_card": pose_card, "params": params})

    def _walk(self, fix):
        """The synthetic walk read under the mean pose correction `fix` (its upper body's turns in the frames)."""
        key = json.dumps(mp.dumps(fix), sort_keys=True)
        if key not in self._walks:
            clip = T.clip()
            self._walks[key] = wm.analyse(mp.correct(clip, fix)) if fix.get("rot") else wm.analyse(clip)
        return self._walks[key]

    def walker_animation(self, root, with_steps=True):
        memo = self.memo_of(root)
        self.anim_calls.append((root, with_steps))
        if not memo.get("walk"):
            raise wscene.Refusal("%s walks nothing of this tool - Pick puts a walk on it" % self.walker_label(root))
        edits = self.walker_edits(root, memo["walk"])[0]
        walk = self._walk(edits["fix"])
        keys = edits.get("keys") or {}
        moving = rw = steps = None
        note = ""
        if with_steps or not kp.is_empty(keys):
            moving, rw, steps, note = kp.on_result(walk, walk.clip.worlds, keys)
        if self.no_steps is not None:
            rw = steps = None
            note = self.no_steps
        return wscene.Animation(root=root, walk_name=memo["walk"], walk=walk, statics=self.world.statics,
                                edits=edits, moving=moving, rw=rw, steps=steps, layer_note=note)


class Fakes(object):
    """Every fake bound in, and put back: maya.cmds (the modules' own _cmds), maya_walk.scene, maya_rigs.rigs, the
    Pose Library's reading and solve, Add Character, the clip label, Delete; meanrig's state on sys."""

    def __init__(self):
        self.world = World()
        self.cmds = FakeCmds(self.world)
        self.scene = FakeScene(self.world)
        self.saved = []
        self.had_state = hasattr(sys, "_skeldar_walk_mean")
        self.state = getattr(sys, "_skeldar_walk_mean", None)
        w = self.world
        cmds = self.cmds

        def skeleton(ref, notes=None):
            w.skeleton_reads += 1
            return dict((leaf, dict(b)) for leaf, b in w.bones[ref].items()), "ue"

        def refresh_world(ref, bones):
            out = {}
            for leaf, b in bones.items():
                fresh = dict(b)
                fresh["world"] = list(w.bones[ref][leaf]["world"])
                if "drive" in w.bones[ref][leaf]:
                    fresh["drive"] = list(w.bones[ref][leaf]["drive"])
                out[leaf] = fresh
            return out

        def plan_for(data, ref, mirror=False):
            w.stand(ref, data)
            return types.SimpleNamespace(values={ref + ":FKSpine1_M.rotateX": 12.5, ref + ":FKLocked_M.rotateX": 3.0},
                                         notes=["", "1 not posed (driven by pairBlend1)"])

        def add_character(entry=None, rgb=None, at=None):
            rig = w.add_rig(at=at or (0.0, 0.0, 0.0))
            w.added.append((entry.key, tuple(at)))
            w.selection = [rig.main]                 # Add Character leaves the new rig's Main selected
            return "Manny [rig] added as %s" % rig.namespace

        def label_rig(rig, name):
            if w.label_error:
                raise RuntimeError(w.label_error)
            w.labels.append((rig.namespace, name))

        def delete_selected(selection=None, confirm=None):
            asked = confirm("delete?")
            w.delete_calls.append((list(selection), asked))
            gone = [r for r in w.rigs if r.main in selection]
            for r in gone:
                w.rigs.remove(r)
                w.attrs.pop(r.main, None)
            return "Deleted %s - %d nodes" % (", ".join(r.namespace for r in gone), 100 * len(gone))

        for obj, name, value in (
                (meanrig, "_cmds", lambda: cmds), (keyrig, "_cmds", lambda: cmds),
                (meanrig, "scene", self.scene), (keyrig, "scene", self.scene),
                (maya_rigs, "rigs", lambda: list(w.rigs)),
                (pscene, "rig_ref", lambda rig: rig.namespace if rig.skeleton_root else None),
                (pscene, "skeleton", skeleton), (pscene, "refresh_world", refresh_world),
                (papply, "plan_for", plan_for), (character, "add_character", add_character),
                (cliplabel, "label_rig", label_rig), (deletion, "delete_selected", delete_selected)):
            self.saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        sys._skeldar_walk_mean = {"callbacks": [], "jobs": [], "timer": None, "bones": None, "busy": False}

    def restore(self):
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)
        if self.had_state:
            sys._skeldar_walk_mean = self.state
        elif hasattr(sys, "_skeldar_walk_mean"):
            del sys._skeldar_walk_mean


class FakedTest(unittest.TestCase):

    def setUp(self):
        self.f = Fakes()
        self.addCleanup(self.f.restore)
        self.w, self.scene = self.f.world, self.f.scene

    def walker(self, root="|walkerA", uuid="UUID-A", **memo):
        return self.scene.walker(root, uuid, **memo)


def reading(rig, walk, memo=None):
    """What the rig shows, read onto the walk's skeleton and measured (meanpose)."""
    return mp.measure(meanrig._read(rig, walk, statics_of(T.clip()), memo), walk)


# ---- the tests ----

class WhichRigTests(FakedTest):

    def test_rigs_are_the_ones_whose_main_carries_the_marker(self):
        a, b = self.w.add_rig(), self.w.add_rig(at=(300, 0, 0))
        self.assertEqual(meanrig.rigs(), [])
        meanrig._set_memo(a, {"walker": "UUID-A", "walk": "asd"})
        self.assertEqual(meanrig.rigs(), [a])
        self.assertEqual(meanrig.memo_of(a), {"walker": "UUID-A", "walk": "asd"})
        self.assertEqual(meanrig.memo_of(b), {})                     # no marker: no memo

    def test_a_memo_that_is_not_json_reads_empty(self):
        rig = self.w.add_rig()
        self.w.attrs[rig.main][meanrig.MARKER] = "{not json"
        self.assertEqual(meanrig.memo_of(rig), {})

    def test_a_rig_belongs_to_the_walker_its_memo_names(self):
        self.walker("|walkerA", "UUID-A")
        self.walker("|walkerB", "UUID-B")
        a, b = self.w.add_rig(), self.w.add_rig(at=(300, 0, 0))
        meanrig._set_memo(a, {"walker": "UUID-A", "walk": "asd"})
        meanrig._set_memo(b, {"walker": "UUID-B", "walk": "asd"})
        self.assertEqual(meanrig.rigs("|walkerA"), [a])
        self.assertEqual(meanrig.rigs("|walkerB"), [b])
        self.assertIs(meanrig.find("|walkerB"), b)
        self.assertIs(meanrig.find(), a)
        self.assertIsNone(meanrig.find("|walkerC"))
        self.assertEqual(meanrig.walker_of("UUID-B"), "|walkerB")
        self.assertIsNone(meanrig.walker_of(""))
        self.assertIsNone(meanrig.walker_of("UUID-GONE"))
        self.assertEqual(meanrig.uuid_of("|walkerA"), "UUID-A")
        self.assertEqual(meanrig.uuid_of(None), "")

    def test_an_older_rig_is_adopted_by_the_working_walker_on_its_walk_once(self):
        self.walker("|walkerA", "UUID-A", walk="asd")
        self.walker("|walkerB", "UUID-B", walk="asd", working=True)
        self.walker("|walkerC", "UUID-C", walk="dw", working=True)
        rig = self.w.add_rig()
        meanrig._set_memo(rig, {"walk": "asd"})
        self.assertEqual(meanrig.rigs("|walkerB"), [rig])
        self.assertEqual(meanrig.memo_of(rig)["walker"], "UUID-B")
        self.assertTrue(self.w.writes[-1][2], "the adoption is written unrecorded")
        self.assertEqual(meanrig.rigs("|walkerA"), [])

    def test_with_no_working_walker_the_first_walker_on_the_walk_takes_it(self):
        self.walker("|walkerB", "UUID-B", walk="asd")
        self.walker("|walkerA", "UUID-A", walk="asd")
        rig = self.w.add_rig()
        meanrig._set_memo(rig, {"walk": "asd"})
        self.assertEqual(meanrig.walker_uuid(rig, meanrig.memo_of, meanrig._set_memo), "UUID-A")

    def test_a_rig_whose_walk_nobody_walks_belongs_to_none(self):
        self.walker("|walkerA", "UUID-A", walk="dw")
        rig = self.w.add_rig()
        meanrig._set_memo(rig, {"walk": "asd"})
        self.assertEqual(meanrig.walker_uuid(rig, meanrig.memo_of, meanrig._set_memo), "")
        self.assertNotIn("walker", meanrig.memo_of(rig))
        self.assertEqual(meanrig.rigs("|walkerA"), [])


class ReadingTests(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.walk = T.walk()
        self.rig = self.w.add_rig(at=(150, 0, 0))
        self.w.stand(self.rig.namespace, meanrig.card_data(self.walk, self.w.statics, mp.mean_pose(self.walk), "asd"))

    def test_card_data_holds_the_walk_s_bones_and_leaves_the_helpers_out_of_the_members(self):
        data = meanrig.card_data(self.walk, self.w.statics, mp.mean_pose(self.walk), "asd")
        self.assertEqual(data["name"], "asd - mean pose")
        self.assertEqual(sorted(data["bones"]), sorted(self.walk.names))
        self.assertIn("camera_root", data["bones"])
        self.assertNotIn("camera_root", data["members"])
        self.assertNotIn("ik_foot_l", data["members"])
        self.assertIn("spine_02", data["members"])
        bone = data["bones"]["spine_02"]
        self.assertEqual((bone["parent"], bone["canonical"]), ("spine_01", "spine_02"))
        self.assertEqual(len(bone["world"]), 16)

    def test_card_data_skips_a_bone_with_no_rest_or_no_world(self):
        statics = dict(self.w.statics)
        del statics["head"]
        worlds = mp.mean_pose(self.walk)
        del worlds["hand_l"]
        data = meanrig.card_data(self.walk, statics, worlds, "x")
        self.assertNotIn("head", data["bones"])
        self.assertNotIn("hand_l", data["bones"])

    def test_the_rig_reads_back_as_the_pose_it_stands_in(self):
        base = mp.measure(mp.mean_pose(self.walk), self.walk)
        fix, moved = mp.combine(mp.empty(), base, reading(self.rig, self.walk))
        self.assertEqual(moved, [])
        self.assertTrue(mp.is_empty(fix))

    def test_a_turned_control_reads_as_that_bone_s_turn(self):
        before = reading(self.rig, self.walk)
        self.w.turn(self.rig.namespace, "spine_02", T.rot_x(10))
        fix, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        self.assertEqual([m[0] for m in moved], ["spine_02"])
        self.assertAlmostEqual(moved[0][1], 10.0, places=6)
        self.assertAlmostEqual(angle_deg(fix["rot"]["spine_02"]), 10.0, places=6)

    def test_a_lowered_pelvis_reads_as_its_height(self):
        before = reading(self.rig, self.walk)
        self.w.lower(self.rig.namespace, -3.0)
        fix, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        self.assertAlmostEqual(fix["height"], -3.0, places=5)
        self.assertIn(("pelvis", -3.0), [(n, round(v, 5)) for n, v, _ in moved])

    def test_main_moved_by_hand_is_no_pose_change(self):
        main0, root0 = meanrig.placement(self.rig)
        memo = {"main0": main0, "root0": root0}
        stood = dict((leaf, mat(b["world"])) for leaf, b in self.w.bones[self.rig.namespace].items())
        before = reading(self.rig, self.walk, memo)
        self.w.move_main(self.rig.namespace, wm.matrix(T.rot_y(40), [80.0, 0.0, -35.0]))
        held = meanrig._held(self.rig, meanrig._bones(self.rig, self.rig.namespace), memo)
        for leaf in ("root", "pelvis", "hand_l", "foot_r"):          # back where they stood
            self.assertLess(float(np.abs(mat(held[leaf]["world"]) - stood[leaf]).max()), 1e-9, leaf)
        _, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk, memo))
        self.assertEqual(moved, [])
        _, unheld = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        self.assertEqual(unheld, [], "a twin carried onto the walk's root reads a rigid move as nothing either")

    def test_the_game_root_moved_alone_is_no_pose_change(self):
        main0, root0 = meanrig.placement(self.rig)
        memo = {"main0": main0, "root0": root0}
        before = reading(self.rig, self.walk, memo)
        root = self.w.world_of(self.rig.namespace, "root")
        root[3, :3] += (0.0, -7.0, 23.5)                       # Root_ctrl moved: the root alone
        self.w.bones[self.rig.namespace]["root"]["world"] = flat(root)
        _, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk, memo))
        self.assertEqual(moved, [])
        _, unheld = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        self.assertIn("pelvis", [m[0] for m in unheld], "without the memo the root's move reads as the pelvis's")

    def test_the_game_root_s_drive_is_held_where_it_stood_too(self):
        main0, root0 = meanrig.placement(self.rig)
        bones = meanrig._bones(self.rig, self.rig.namespace)
        bones["root"]["drive"] = flat(translate(1, 2, 3))
        held = meanrig._held(self.rig, bones, {"main0": main0, "root0": root0})
        self.assertEqual((held["root"]["world"], held["root"]["drive"]), (root0, root0))

    def test_held_with_no_memo_gives_the_bones_back(self):
        bones = meanrig._bones(self.rig, self.rig.namespace)
        self.assertIs(meanrig._held(self.rig, bones, None), bones)
        self.assertIs(meanrig._held(self.rig, bones, {"root0": [1.0] * 16}), bones)

    def test_a_bone_s_drive_is_read_in_place_of_its_world(self):
        """AdvancedSkeleton's shoulder never rolls - the roll lives in its drive: the reading takes the drive."""
        before = reading(self.rig, self.walk)
        arm = self.w.world_of(self.rig.namespace, "upperarm_l")
        rolled = arm.copy()
        rolled[:3, :3] = T.rot_x(25) @ arm[:3, :3]                  # about the bone's own X, in place
        self.w.bones[self.rig.namespace]["upperarm_l"]["drive"] = flat(rolled)
        _, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        turns = dict((n, v) for n, v, _ in moved)
        self.assertAlmostEqual(turns["upperarm_l"], 25.0, places=5)
        del self.w.bones[self.rig.namespace]["upperarm_l"]["drive"]
        meanrig._state()["bones"] = None
        _, moved = mp.combine(mp.empty(), before, reading(self.rig, self.walk))
        self.assertEqual(moved, [], "the bare world, unrolled, reads nothing")

    def test_the_skeleton_is_read_once_a_rig_then_refreshed(self):
        meanrig._state()["bones"] = None
        first = reading(self.rig, self.walk)
        reading(self.rig, self.walk)
        self.assertEqual(self.w.skeleton_reads, 1)
        self.w.turn(self.rig.namespace, "head", T.rot_y(30))
        _, moved = mp.combine(mp.empty(), first, reading(self.rig, self.walk))
        self.assertEqual(self.w.skeleton_reads, 1, "the same rig: its worlds refreshed, not read whole")
        self.assertEqual([m[0] for m in moved], ["head"])
        other = self.w.add_rig(at=(-150, 0, 0))
        meanrig._read(other, self.walk, self.w.statics)
        self.assertEqual(self.w.skeleton_reads, 2)
        meanrig._read(self.rig, self.walk, self.w.statics)     # another rig was read between: read whole again
        self.assertEqual(self.w.skeleton_reads, 3)

    def test_a_rig_that_drives_no_game_skeleton_is_refused(self):
        bare = self.w.add_rig(skeleton=False)
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig._read(bare, self.walk, self.w.statics)
        self.assertIn("drives no game skeleton", str(caught.exception))

    def test_placement_is_main_and_the_game_root_as_they_stand(self):
        main, root = meanrig.placement(self.rig)
        self.assertEqual(main, flat(translate(150, 0, 0)))
        self.assertEqual(root, self.w.bones[self.rig.namespace]["root"]["world"])

    def test_flat_and_unflat_are_inverse(self):
        worlds = mp.mean_pose(self.walk)
        back = meanrig._unflat(meanrig._flat(worlds))
        self.assertEqual(sorted(back), sorted(worlds))
        self.assertLess(max(float(np.abs(back[n] - worlds[n]).max()) for n in worlds), 1e-12)
        json.dumps(meanrig._flat(worlds))                          # plain data


class PoseTests(FakedTest):

    def test_the_controls_keep_no_time_curve_and_take_the_solve_s_values(self):
        walk = T.walk()
        rig = self.w.add_rig()
        data = meanrig.card_data(walk, self.w.statics, mp.mean_pose(walk), "asd")
        plan = meanrig._pose(rig, data)
        ns = rig.namespace
        self.assertEqual(self.w.deleted, [ns + ":FKSpine1_M_rotateX"])           # the driven key stays
        self.assertIn(ns + ":FKSpine1_M_sdk", self.w.curve_types)
        self.assertEqual(self.w.attrs[ns + ":FKSpine1_M"]["rotateX"], 12.5)
        self.assertEqual(self.w.attrs[ns + ":FKLocked_M"]["rotateX"], 0.0)        # a locked channel skipped
        self.assertTrue(all(unrecorded for plug, _, unrecorded in self.w.writes))
        self.assertTrue(self.w.auto, "autoKey back as it was")
        self.assertEqual(self.w.posed, [(ns, "asd - mean pose")])
        self.assertIn("1 not posed (driven by pairBlend1)", plan.notes)

    def test_auto_key_off_stays_off(self):
        walk = T.walk()
        rig = self.w.add_rig()
        self.w.auto = False
        meanrig._pose(rig, meanrig.card_data(walk, self.w.statics, mp.mean_pose(walk), "asd"))
        self.assertFalse(self.w.auto)

    def test_auto_key_comes_back_on_when_the_solve_fails(self):
        rig = self.w.add_rig()

        def broken(data, ref, mirror=False):
            raise RuntimeError("solve")
        papply.plan_for = broken
        with self.assertRaises(RuntimeError):
            meanrig._pose(rig, {"bones": {}, "name": "x", "members": []})
        self.assertTrue(self.w.auto)

    def test_controls_are_the_set_s_transforms(self):
        rig = self.w.add_rig()
        self.assertEqual(meanrig._controls(rig), [rig.namespace + ":FKSpine1_M", rig.namespace + ":FKLocked_M"])


class CreateTests(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.walker("|walkerA", "UUID-A", at=(40.0, 0.0, -10.0))
        self.w.selection = ["|walkerA", "|gone"]

    def test_create_adds_a_rig_beside_the_walker_in_its_mean_pose(self):
        line = meanrig.press("|walkerA")
        self.assertEqual(len(self.w.rigs), 1)
        rig = self.w.rigs[0]
        self.assertEqual(self.w.added, [("Manny_Rig", (190.0, 0.0, -10.0))])
        self.assertEqual(self.w.selection, ["|walkerA"], "the animator's selection kept (what still exists)")
        memo = meanrig.memo_of(rig)
        self.assertEqual((memo["walker"], memo["walk"]), ("UUID-A", "asd"))
        self.assertEqual(memo["clean"], dict(wscene.wc.knobs(None)))
        self.assertEqual(memo["main0"], flat(translate(190.0, 0.0, -10.0)))
        self.assertEqual(len(memo["root0"]), 16)
        walk = T.walk()
        # its base is what it shows: the walk's mean pose
        _, moved = mp.combine(mp.empty(), mp.measure(meanrig._unflat(memo["base"]), walk),
                              mp.measure(mp.mean_pose(walk), walk))
        self.assertEqual(moved, [])
        self.assertEqual(self.w.labels, [("Manny_Rig", "walkerA - mean pose")])
        self.assertTrue(line.startswith("added Manny_Rig in the mean pose of walkerA (no correction)"), line)
        self.assertIn("pose its controls, then Update", line)
        self.assertIn("| 1 not posed (driven by pairBlend1)", line)
        self.assertEqual(self.scene.anim_calls, [("|walkerA", False)])
        self.assertTrue(all(unrecorded for plug, _, unrecorded in self.w.writes if plug.endswith(meanrig.MARKER)))

    def test_a_second_press_poses_the_walker_s_own_rig_again(self):
        meanrig.press("|walkerA")
        rig = self.w.rigs[0]
        self.w.turn(rig.namespace, "head", T.rot_x(30))
        line = meanrig.press("|walkerA", clean={"smooth": 2.0})
        self.assertEqual(len(self.w.rigs), 1)
        self.assertTrue(line.startswith("posed Manny_Rig in the mean pose of walkerA"), line)
        self.assertEqual(meanrig.memo_of(rig)["clean"], dict(wscene.wc.knobs({"smooth": 2.0})))
        walk = T.walk()
        _, moved = mp.combine(mp.empty(), mp.measure(mp.mean_pose(walk), walk), reading(rig, walk))
        self.assertEqual(moved, [], "the turned head stood back in the mean pose")

    def test_each_walker_has_a_rig_of_its_own(self):
        self.walker("|walkerB", "UUID-B", at=(-200.0, 0.0, 0.0))
        meanrig.press("|walkerA")
        meanrig.press("|walkerB")
        self.assertEqual(len(self.w.rigs), 2)
        self.assertEqual([meanrig.memo_of(r)["walker"] for r in self.w.rigs], ["UUID-A", "UUID-B"])
        self.assertEqual(self.w.added[1][1], (-50.0, 0.0, 0.0))

    def test_the_rig_stands_in_the_walker_s_corrected_mean_pose(self):
        fix = mp.empty()
        fix["rot"]["spine_02"] = T.rot_x(12)
        fix["height"] = -2.0
        self.scene.edits["|walkerA"] = {"walk": "asd", "fix": fix, "keys": {}, "posture": False}
        line = meanrig.press("|walkerA")
        self.assertIn("(1 bone turned, pelvis -2.0 cm)", line)
        rig = self.w.rigs[0]
        walk = self.scene._walk(fix)
        _, moved = mp.combine(mp.empty(), mp.measure(mp.mean_pose(walk, fix), walk), reading(rig, walk))
        self.assertEqual(moved, [])
        plain = T.walk()
        back, _ = mp.combine(mp.empty(), mp.measure(mp.mean_pose(plain), plain), reading(rig, walk))
        self.assertAlmostEqual(angle_deg(back["rot"]["spine_02"]), 12.0, delta=0.05)
        self.assertAlmostEqual(back["height"], -2.0, delta=0.05)

    def test_no_walker_or_a_walker_of_no_walk_is_refused(self):
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.press(None)
        self.assertEqual(str(caught.exception), meanrig.NO_WALKER)
        self.scene.memos["|walkerA"]["walk"] = ""
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.press("|walkerA")
        self.assertIn("walkerA walks nothing of this tool", str(caught.exception))
        self.assertEqual(self.w.rigs, [])

    def test_add_character_adding_no_rig_is_refused(self):
        character.add_character = lambda entry=None, rgb=None, at=None: "nothing came out of Manny_Rig.ma"
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.press("|walkerA")
        self.assertIn("no Manny rig was added: nothing came out", str(caught.exception))

    def test_a_label_that_fails_does_not_fail_the_press(self):
        self.w.label_error = "no annotation"
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            line = meanrig.press("|walkerA")
        self.assertTrue(line.startswith("added"))
        self.assertIn("no annotation", stderr.getvalue())

    def test_the_point_beside_a_walker_that_is_gone_is_the_origin(self):
        self.assertEqual(meanrig._point("|gone"), (0.0, 0.0, 0.0))
        self.assertEqual(meanrig._point(None), (0.0, 0.0, 0.0))
        self.assertEqual(meanrig._point("|walkerA"), (190.0, 0.0, -10.0))


class UpdateTests(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.walker("|walkerA", "UUID-A")
        meanrig.press("|walkerA")
        self.rig = self.w.rigs[0]
        self.rekeyed = []

    def rekey(self, root):
        self.rekeyed.append(root)
        return " -> %s keyed again" % root

    def test_no_rig_is_refused(self):
        self.w.rigs = []
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.update(self.rekey)
        self.assertEqual(str(caught.exception), meanrig.NO_RIG)

    def test_nothing_moved_writes_nothing(self):
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)
        self.assertEqual(self.scene.edit_calls, [])
        self.assertEqual(self.rekeyed, [])

    def test_a_turned_control_goes_into_its_walker_s_correction_and_keys_it_again(self):
        self.w.turn(self.rig.namespace, "spine_02", T.rot_x(10))
        line = meanrig.update(self.rekey)
        self.assertEqual(line, "mean pose of walkerA: spine_02 10.0 deg -> |walkerA keyed again")
        self.assertEqual(self.rekeyed, ["|walkerA"])
        fix = self.scene.edits["|walkerA"]["fix"]
        self.assertEqual(sorted(fix["rot"]), ["spine_02"])
        self.assertAlmostEqual(angle_deg(fix["rot"]["spine_02"]), 10.0, places=5)
        # the base became what the rig shows: a second Update finds nothing
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)
        self.assertEqual(self.rekeyed, ["|walkerA"])

    def test_a_second_edit_adds_to_the_first(self):
        self.w.turn(self.rig.namespace, "spine_02", T.rot_x(10))
        meanrig.update(self.rekey)
        self.w.lower(self.rig.namespace, -4.0)
        line = meanrig.update(self.rekey)
        self.assertIn("pelvis -4.0 cm", line)
        fix = self.scene.edits["|walkerA"]["fix"]
        self.assertAlmostEqual(angle_deg(fix["rot"]["spine_02"]), 10.0, places=5)
        self.assertAlmostEqual(fix["height"], -4.0, places=4)

    def test_main_moved_by_hand_is_nothing_moved(self):
        self.w.move_main(self.rig.namespace, wm.matrix(T.rot_y(-70), [0.0, 0.0, 300.0]))
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)

    def test_the_default_rekey_keys_the_walker_as_it_was_keyed_last(self):
        self.scene.memos["|walkerA"].update(knobs={"stride": 1.2}, pose="goblin", parts=["torso"],
                                            pose_card="Walk poses/goblin.pose",
                                            params={"changes": {"height": ["offset", 3.0]}, "pins": ["height"]})
        self.w.turn(self.rig.namespace, "head", T.rot_y(15))
        line = meanrig.update()
        self.assertTrue(line.endswith(" -> walkerA keyed again"), line)
        call = self.scene.applied[-1]
        self.assertEqual((call["root"], call["walk"], call["knobs"], call["pose"], call["parts"], call["record"],
                          call["pose_card"]),
                         ("|walkerA", "asd", {"stride": 1.2}, "goblin", ("torso",), False, "Walk poses/goblin.pose"))
        self.assertEqual(call["params"]["changes"]["height"], ("offset", 3.0))

    def test_a_rig_stood_by_an_older_build_is_stood_again_and_read_nothing(self):
        memo = meanrig.memo_of(self.rig)
        meanrig._set_memo(self.rig, {"walker": memo["walker"], "walk": "asd", "base": memo["base"]})
        self.w.turn(self.rig.namespace, "spine_02", T.rot_x(10))
        line = meanrig.update(self.rekey)
        self.assertIn("Manny_Rig stood by an older build", line)
        self.assertEqual(self.scene.edit_calls, [])
        self.assertIn("main0", meanrig.memo_of(self.rig))
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)

    def test_a_rig_with_no_base_takes_what_it_shows_as_its_base(self):
        memo = meanrig.memo_of(self.rig)
        meanrig._set_memo(self.rig, dict(memo, base={}))
        self.w.turn(self.rig.namespace, "spine_02", T.rot_x(10))
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)
        self.assertTrue(meanrig.memo_of(self.rig)["base"])
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)

    def test_a_rig_whose_walker_is_gone_says_so(self):
        meanrig._set_memo(self.rig, dict(meanrig.memo_of(self.rig), walker="UUID-GONE"))
        self.assertEqual(meanrig.update(self.rekey),
                         "Manny_Rig stands for no walker in the scene - Delete it and Create again")
        self.scene.memos["|walkerA"]["walk"] = ""
        meanrig._set_memo(self.rig, dict(meanrig.memo_of(self.rig), walker="UUID-A"))
        self.assertIn("stands for no walker", meanrig.update(self.rekey))

    def test_each_rig_moves_its_own_walker(self):
        self.walker("|walkerB", "UUID-B", at=(-300.0, 0.0, 0.0))
        meanrig.press("|walkerB")
        b = [r for r in self.w.rigs if meanrig.memo_of(r)["walker"] == "UUID-B"][0]
        self.w.turn(b.namespace, "upperarm_l", T.rot_z(20))
        line = meanrig.update(self.rekey)
        self.assertEqual(self.rekeyed, ["|walkerB"])
        self.assertTrue(line.startswith("mean pose of walkerB: upperarm_l 20.0 deg"), line)
        self.assertNotIn("|walkerA", self.scene.edits)
        self.w.turn(self.rig.namespace, "head", T.rot_x(-8))
        self.w.turn(b.namespace, "head", T.rot_x(6))
        line = meanrig.update(self.rekey)
        self.assertEqual(line.count("mean pose of"), 2)
        self.assertEqual(self.rekeyed, ["|walkerB", "|walkerA", "|walkerB"])

    def test_update_takes_down_an_older_build_s_watch(self):
        state = meanrig._state()
        self.w.jobs.update([7, 8])
        state["jobs"] = [7, 8, 9]
        stopped = []
        state["timer"] = types.SimpleNamespace(stop=lambda: stopped.append(True))
        meanrig.update(self.rekey)
        self.assertEqual(self.w.killed, [7, 8])
        self.assertEqual((state["jobs"], state["timer"], stopped), ([], None, [True]))


class StopTests(FakedTest):

    def test_stop_removes_the_callbacks_kills_the_jobs_and_stops_the_timer(self):
        import maya.api.OpenMaya as om
        removed = []

        class Message(object):
            @staticmethod
            def removeCallback(cid):
                removed.append(cid)
                if cid == 2:
                    raise RuntimeError("gone")
        real = om.MMessage
        om.MMessage = Message
        try:
            state = meanrig._state()
            state["callbacks"] = [1, 2, 3]
            self.w.jobs.add(5)
            state["jobs"] = [5]

            class Timer(object):
                def stop(self):
                    raise RuntimeError("Internal C++ object already deleted")
            state["timer"] = Timer()
            meanrig.stop()
        finally:
            om.MMessage = real
        self.assertEqual(removed, [1, 2, 3])
        self.assertEqual(self.w.killed, [5])
        self.assertEqual((state["callbacks"], state["jobs"], state["timer"]), ([], [], None))

    def test_a_job_that_cannot_be_asked_is_dropped(self):
        def broken(**kw):
            raise RuntimeError("scriptJob")
        self.f.cmds.scriptJob = broken
        state = meanrig._state()
        state["jobs"] = [3]
        meanrig.stop()
        self.assertEqual(state["jobs"], [])

    def test_the_state_is_made_once_on_sys(self):
        del sys._skeldar_walk_mean
        state = meanrig._state()
        self.assertIs(meanrig._state(), state)
        self.assertEqual(sorted(state), ["bones", "busy", "callbacks", "jobs", "timer"])


class ResetDeleteTests(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.walker("|walkerA", "UUID-A")
        self.rekeyed = []

    def rekey(self, root):
        self.rekeyed.append(root)
        return " -> keyed"

    def test_reset_drops_the_correction_and_stands_the_rig_in_the_plain_mean_pose(self):
        meanrig.press("|walkerA")
        rig = self.w.rigs[0]
        self.w.turn(rig.namespace, "spine_02", T.rot_x(10))
        meanrig.update(self.rekey)
        line = meanrig.reset("|walkerA", rekey=self.rekey)
        self.assertEqual(line, "walkerA: the mean pose correction dropped, the rig pose back in the mean pose -> keyed")
        self.assertTrue(mp.is_empty(self.scene.edits["|walkerA"]["fix"]))
        walk = T.walk()
        _, moved = mp.combine(mp.empty(), mp.measure(mp.mean_pose(walk), walk), reading(rig, walk))
        self.assertEqual(moved, [])
        self.assertEqual(meanrig.update(self.rekey), meanrig.NOTHING_MOVED)

    def test_reset_with_no_correction_and_no_rig(self):
        line = meanrig.reset("|walkerA", rekey=self.rekey)
        self.assertEqual(line, "walkerA has no correction -> keyed")
        self.assertEqual(self.w.rigs, [])
        self.assertEqual(self.rekeyed, ["|walkerA"])

    def test_reset_refuses_no_walker(self):
        with self.assertRaises(meanrig.Refusal):
            meanrig.reset(None)

    def test_delete_takes_the_walker_s_rig_and_keeps_its_correction(self):
        meanrig.press("|walkerA")
        fix = mp.empty()
        fix["height"] = -3.0
        self.scene.edits["|walkerA"] = {"walk": "asd", "fix": fix, "keys": {}, "posture": False}
        line = meanrig.delete("|walkerA")
        self.assertEqual(line, "rig pose of walkerA deleted (Deleted Manny_Rig - 100 nodes) - the walker keeps its "
                               "correction")
        self.assertEqual(self.w.rigs, [])
        self.assertEqual(self.w.delete_calls, [(["Manny_Rig:Main"], True)])
        self.assertEqual(self.scene.edits["|walkerA"]["fix"]["height"], -3.0)
        self.assertIsNone(meanrig._state()["bones"])

    def test_delete_with_no_walker_takes_the_only_rig(self):
        meanrig.press("|walkerA")
        self.assertIn("rig pose of walkerA deleted", meanrig.delete())

    def test_delete_of_a_walker_with_none_when_others_stand_is_refused(self):
        self.walker("|walkerB", "UUID-B")
        self.walker("|walkerC", "UUID-C")
        meanrig.press("|walkerA")
        meanrig.press("|walkerB")
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.delete("|walkerC")
        self.assertIn("walkerC has no rig pose - 2 others stand", str(caught.exception))
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.delete()
        self.assertIn("the working walker has no rig pose", str(caught.exception))

    def test_delete_with_no_rig_at_all(self):
        with self.assertRaises(meanrig.Refusal) as caught:
            meanrig.delete("|walkerA")
        self.assertEqual(str(caught.exception), "no rig pose in the scene")

    def test_delete_of_a_rig_whose_walker_is_gone_names_nobody(self):
        meanrig.press("|walkerA")
        meanrig._set_memo(self.w.rigs[0], dict(meanrig.memo_of(self.w.rigs[0]), walker="UUID-GONE"))
        self.assertTrue(meanrig.delete().startswith("rig pose of - deleted"))

    def test_rekey_root_says_the_walker(self):
        self.scene.memos["|walkerA"]["knobs"] = {"tempo": 28}
        self.assertEqual(meanrig.rekey_root("|walkerA"), " -> walkerA keyed again")
        self.assertEqual(self.scene.applied[-1]["parts"], tuple(wscene.ALL_PARTS))
        self.assertIsNone(self.scene.applied[-1]["pose"])
        self.assertIsNone(self.scene.applied[-1]["params"])


if __name__ == "__main__":
    unittest.main()

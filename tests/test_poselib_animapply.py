"""The Pose Library's animation Apply (2026-10-03): the press of an animation card against a fake
scene - the order (refusals, the walk, the dry solve, the chunk, the paste mode's ops, a solve
and a key per frame), the seeds, Connect, the travel, Mirror, Blend, a cancel, the status line;
objects; drops; Select objects; the Blend session.

The animator: «Все правила которые работают для поз должны работать и для анимаций. Так же мы
должны уметь выбирать способ вставки анимации как в studio library». Every module the press talks
to is a fake rebound as a module attribute of `animapply` (CLAUDE.md's rule) and put back in
`tearDown`: `cmds`, `keys`, `scene`, `pm`, `rigsolve`, `skelsolve`, `timewalk`, and the seams
that reach the scene through `apply` (`_targets`, `_main_of`, `_rotations`,
`_measure_skeleton`, `_objects_pairs`). `animdata`, `look` and the pure halves of `apply` are the
real ones. The scene half is docs/superpowers/plans/verify_poselib_anim.py (mayapy standalone).
"""

import unittest
from collections import OrderedDict

import maya.api.OpenMaya as om

from maya_poselib import animapply as aa
from maya_poselib import animdata
from maya_poselib import apply as ap
from maya_poselib import keys as real_keys
from maya_poselib import look
from maya_poselib import posemath as real_pm
from maya_poselib import rigsolve as real_rigsolve
from maya_poselib import scene as real_scene
from maya_poselib.skelsolve import Solution

WRIST = "Manny_Rig1:FKWrist_L.rotateX"
MAIN = "|Manny_Rig_Character|Manny_Rig1:Group|Manny_Rig1:Main"
MAIN_SHORT = "Manny_Rig1:Main"
MAIN_PLUGS = [MAIN_SHORT + "." + ch for ch in ("rotateX", "rotateY", "rotateZ", "translateX",
                                               "translateY", "translateZ")]
SKEL_ROOT = "|Manny_Skeleton_Character|root"
HAND = "|Manny_Skeleton_Character|root|pelvis|hand_l"
LAYER = real_keys.Layer("AnimLayer1", False, True, False, False)

SEAMS = ("cmds", "keys", "scene", "pm", "rigsolve", "skelsolve", "timewalk", "_targets",
         "_character_of", "_main_of", "_rotations", "_measure_skeleton", "_objects_pairs",
         "apply", "apply_onto")
AP_SEAMS = ("drop_floor", "select_objects", "Blend")


def q7(tx=0.0, ty=0.0, tz=0.0):
    return [0.0, 0.0, 0.0, 1.0, float(tx), float(ty), float(tz)]


def ident(tx=0.0, ty=0.0, tz=0.0):
    return [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, tx, ty, tz, 1.0]


def card(count=6, start=0.0, members=("pelvis", "hand_l"), key_times=None, fps="ntsc"):
    """(header, frames) of a character card: four bones over `count` frames from `start`; frame
    i's ROOT stands at x = i, so a fake can tell which frame it was handed (`index`)."""
    names = ("root", "pelvis", "hand_l", "hand_r")
    parents = (None, "root", "pelvis", "pelvis")
    bones = OrderedDict()
    for name, parent in zip(names, parents):
        bones[name] = {"parent": parent, "canonical": name, "rest": ident(), "rotateOrder": 0}
    header = {"format": "skeldar.anim", "version": 1, "kind": "character", "name": "Walk",
              "fps": fps, "start": float(start), "end": float(start + count - 1),
              "frames": count, "key_times": list(key_times or [start, start + count - 1]),
              "bones": bones, "members": list(members), "regions": [],
              "character": {"key": "Manny_Rig", "namespace": "Manny_Rig", "kind": "rig"}}
    world = []
    for i in range(count):
        world.append(q7(i) + q7(i, 95) + q7(i, 140, 20) + q7(i, 140, -20))
    return header, {"bones": list(names), "world": world, "drive": {}}


def index(bones):
    """Which frame of `card` a bone dict was decoded from: its root's x."""
    return int(round(bones["root"]["world"][12]))


def mirrored(bones):
    return bool(bones["root"].get("mirrored"))


def flat(matrix):
    return None if matrix is None else [round(float(v), 9) for v in om.MMatrix(matrix)]


def moved(x, y=0.0, z=0.0):
    return om.MMatrix(ident(x, y, z))


class World(object):
    """The fake scene every fake shares: one log, the time the walk stands on, what reads
    answer."""

    def __init__(self):
        self.log = []
        self.frame = 12.0
        self.recording = True
        self.auto = True
        self.unit = "ntsc"
        self.short = {MAIN: MAIN_SHORT}
        self.values = {}                 # plug -> a value, or a function of the frame
        self.attrs = None                # (node, attr) that exist; None: every one
        self.selected = []
        self.calls = 0                   # solves so far: what a solve answers carries it
        self.measured = {}               # wanted index -> (deg, cm, leaf)
        self.walks = []
        self.place = moved(100.0, 0.0, 50.0)
        self.blocked = {}                # plug -> why keys.writable refuses it
        self.characters = {}             # path -> CharacterRef (character_of)
        self.ground_of = None            # frame -> the target's ground as it stands there
        self.top_member = False          # a skeleton solve writes its top joint (rootless)
        self.fail_at = None              # a solve number that raises
        self.refuse_breakdown = None     # keyframe -edit -breakdown raising
        self.auto_query_fails = False    # autoKeyframe -q raising (the chunk's first question)
        self.cut_count = 0               # the keys keys.cut answers it removed (a call)
        self.shift_count = 0             # the keys keys.shift answers it moved (a call)

    def value(self, plug, frame):
        found = self.values.get(plug, 0.0)
        return float(found(frame) if callable(found) else found)

    def names(self):
        return [entry[0] for entry in self.log]

    def entries(self, name):
        return [entry for entry in self.log if entry[0] == name]


class FakeCmds(object):

    def __init__(self, world):
        self.world = world

    def undoInfo(self, query=False, state=None, openChunk=False, closeChunk=False,
                 chunkName=None, stateWithoutFlush=None, **kwargs):
        if query:
            return self.world.recording
        if stateWithoutFlush is not None:
            self.world.recording = bool(stateWithoutFlush)
            self.world.log.append(("record", self.world.recording))
        if openChunk:
            self.world.log.append(("open", chunkName))
        if closeChunk:
            self.world.log.append(("close",))

    def autoKeyframe(self, query=False, state=None):
        if query:
            if self.world.auto_query_fails:
                raise RuntimeError("autoKeyframe: no answer")
            return self.world.auto
        self.world.auto = state
        self.world.log.append(("autoKey", state))

    def currentTime(self, value=None, query=False, **kwargs):
        if query:
            return self.world.frame
        raise AssertionError("a press never sets the time through currentTime")

    def currentUnit(self, query=False, time=False, **kwargs):
        return self.world.unit

    def undo(self):
        self.world.log.append(("undo",))

    def dgdirty(self, nodes):
        self.world.log.append(("dirty", list(nodes)))

    def getAttr(self, plug, time=None, **kwargs):
        return self.world.value(plug, self.world.frame if time is None else time)

    def attributeQuery(self, attr, node=None, exists=False, **kwargs):
        return self.world.attrs is None or (node, attr) in self.world.attrs

    def ls(self, *args, **kwargs):
        if kwargs.get("selection"):
            return list(self.world.selected)
        if not args:
            return []
        path = args[0]
        if kwargs.get("long"):
            return [path]
        return [self.world.short.get(path, path)]

    def select(self, nodes, add=False, replace=False, **kwargs):
        self.world.log.append(("select", list(nodes), add))

    def keyframe(self, curve, edit=False, time=None, breakdown=None, **kwargs):
        assert edit and breakdown is not None, kwargs
        if self.world.refuse_breakdown is not None:
            self.world.refuse_breakdown(curve, time=time)
        self.world.log.append(("keyframe", curve, tuple(time), breakdown))


class FakeKeys(object):
    """`keys` as an animation press sees it: the layer, the quaternion note, what plugs show,
    the keys, the curves' ops and their state - logged."""

    Written = real_keys.Written

    def __init__(self, world, layer=None, refusal="", quaternion=""):
        self.world = world
        self.layer = layer
        self.refusal = refusal
        self.quaternion = quaternion

    def active_layer(self):
        self.world.log.append(("layer",))
        return self.layer, self.refusal

    def quaternion_note(self, layer):
        self.world.log.append(("quaternion",))
        return self.quaternion

    def layer_note(self, layer):
        return real_keys.layer_note(layer)

    def current(self, plugs):
        self.world.log.append(("current", self.world.frame, sorted(plugs)))
        return dict((p, self.world.value(p, self.world.frame)) for p in plugs)

    def write(self, values, frame, layer):
        self.world.log.append(("write", OrderedDict(values), frame))
        return real_keys.Written(len(values), [], list(values))

    def cut(self, plugs, layer, start=None, end=None):
        self.world.log.append(("cut", sorted(plugs), start, end))
        return self.world.cut_count

    def shift(self, plugs, layer, at, by):
        self.world.log.append(("shift", sorted(plugs), at, by))
        return self.world.shift_count

    def curve_state(self, plugs, layer):
        self.world.log.append(("state", sorted(plugs)))
        return OrderedDict((plug, {"preInfinity": "cycle", "postInfinity": "constant",
                                   "weighted": False}) for plug in plugs)

    def put_curve_state(self, state, layer):
        self.world.log.append(("restate", state))
        return 0

    def feed_of(self, plug):
        return "curve", "curve:" + plug

    def writable(self, plug):
        why = self.world.blocked.get(plug)
        return (False, why) if why else (True, "")

    def write_keys(self, plug, keys_list, layer, weighted=False, tangents=True):
        self.world.log.append(("write_keys", plug, [list(k) for k in keys_list], weighted,
                               tangents))
        return real_keys.Written(len(keys_list), [], [plug])

    NO_CURVE = real_keys.NO_CURVE

    def curve_for(self, plug, layer):
        return "curve:" + plug

    def shown_at_start(self, tweaks, plugs):
        """What the plugs showed when the walk was entered (its `tweaks`' reading)."""
        self.world.log.append(("shown", sorted(plugs)))
        return OrderedDict((p, tweaks.values[p] if p in tweaks.values else
                            self.world.value(p, self.world.frame)) for p in plugs)

    def undo_marks(self, values):
        self.world.log.append(("mark", OrderedDict(values)))
        return list(values)


class FakeTweaks(object):
    """keys.Tweaks: every plug the world knows, read where the walk is entered."""

    def __init__(self, world):
        self.values = dict((plug, world.value(plug, world.frame)) for plug in world.values)


class FakeWalk(object):

    world = None

    def __init__(self, fresh=True):
        self.fresh = fresh
        self.keyed = []
        self.moved = False

    def __enter__(self):
        self.world.log.append(("walk", self.fresh))
        self.world.walks.append(self)
        self.here = self.world.frame            # the real walk puts the time back on exit
        self.tweaks = FakeTweaks(self.world)
        return self

    def go(self, frame):
        self.world.frame = frame
        self.moved = True
        self.world.log.append(("go", frame))

    def arrive(self, frame):
        """`timewalk.Walk.arrive`: no time set on the frame the walk entered on until it moved."""
        if not self.moved and abs(float(frame) - float(self.here)) <= 1e-9:
            self.world.log.append(("arrive", frame))
            return False
        self.go(frame)
        return True

    def restore_all(self):
        self.world.log.append(("restore_all",))
        del self.keyed[:]
        return []

    def __exit__(self, *exc):
        self.world.frame = self.here
        self.world.log.append(("walked",))
        return False


class FakeTimewalk(object):

    def __init__(self, world):
        self.Walk = type("Walk", (FakeWalk,), {"world": world})


class FakeScene(object):

    def __init__(self, world, bones):
        self.world = world
        self.bones = bones                   # root path -> {leaf: bone}

    def skeleton(self, ref, notes=None):
        self.world.log.append(("skeleton", ref.root, self.world.frame))
        return OrderedDict((k, dict(v)) for k, v in self.bones[ref.root].items()), "unreal_ue5"

    def refresh_world(self, ref, bones):
        self.world.log.append(("refresh", ref.root, self.world.frame))
        out = OrderedDict((k, dict(v)) for k, v in bones.items())
        if self.world.ground_of is not None and "root" in out:
            out["root"]["ground"] = list(self.world.ground_of(self.world.frame))
        return out

    def character_of(self, path):
        return self.world.characters.get(path)

    leaf = staticmethod(real_scene.leaf)
    describe = staticmethod(real_scene.describe)


class FakeTransfer(object):

    world = None

    def __init__(self, source, target, pairs, members, use_drive=False, scale=1.0):
        self.world.log.append(("transfer", index(source), mirrored(source), sorted(members),
                               use_drive))

    def place(self, target=None):
        if target is not None and "ground" in target.get("root", {}):
            return om.MMatrix(target["root"]["ground"])
        return om.MMatrix(self.world.place)

    def frame(self, source=None, target=None, root_world=None, source_root=None):
        self.world.log.append(("frame", index(source), mirrored(source), flat(root_world)))
        if source_root is not None:
            self.world.log.append(("source_root", index(source), flat(source_root)))
        return {"index": index(source), "mirrored": mirrored(source)}

    def travel(self, source_now, source_first, flip=False, roots=None):
        self.world.log.append(("travel", index(source_now), index(source_first), flip,
                               mirrored(source_now) or mirrored(source_first)))
        if roots is not None:
            self.world.log.append(("travel_roots", flat(roots[0]), flat(roots[1])))
        return moved(10.0 * (index(source_now) - index(source_first)))


class FakePm(object):

    def __init__(self, world, rooted=True):
        self.world = world
        self.rooted = rooted
        self.Transfer = type("Transfer", (FakeTransfer,), {"world": world})

    def pairs(self, source, target):
        return dict((leaf, leaf) for leaf in target if leaf in source)

    def scale_between(self, source, target, pairs):
        return 1.0

    def mirror(self, source, members, root_frame=None):
        self.world.log.append(("mirror", index(source), flat(root_frame)))
        out = OrderedDict((leaf, dict(bone, mirrored=True)) for leaf, bone in source.items())
        swap = {"hand_l": "hand_r", "hand_r": "hand_l"}
        return out, [swap.get(m, m) for m in members or ()]

    def has_root(self, bones):
        return self.rooted

    def root_of(self, bones):
        return "root"

    def clip_roots(self, first, worlds):
        """posemath.clip_roots: one marker a frame - the root frame at z = 1000 + the world's x
        (the card's frame i stands at x = i)."""
        self.world.log.append(("clip_roots", len(worlds)))
        return [moved(0.0, 0.0, 1000.0 + om.MMatrix(world)[12]) for world in worlds]

    _find = staticmethod(real_pm._find)
    is_twist = staticmethod(real_pm.is_twist)
    ue_named = staticmethod(real_pm.ue_named)


class FakeRigsolve(object):
    """`rigsolve` as an animation press sees it: a Solver whose every solve answers the wrist and
    - built with `main` - Main's six channels, each carrying the number of the solve."""

    MAIN_KEPT = real_rigsolve.MAIN_KEPT
    NO_MAIN = real_rigsolve.NO_MAIN

    def __init__(self, world):
        self.world = world
        outer = self

        class Solver(object):
            def __init__(self, rig, members, main=False):
                outer.world.log.append(("solver", list(members), main))
                self.main = MAIN if main else None

            def solve(self, wanted, seed=None):
                outer.world.calls += 1
                if outer.world.fail_at == outer.world.calls:
                    raise RuntimeError("solve failed")
                n = float(outer.world.calls)
                outer.world.log.append(("solve", wanted["index"],
                                        None if seed is None else dict(seed)))
                values = OrderedDict([(WRIST, n)])
                if self.main:
                    for k, plug in enumerate(MAIN_PLUGS):
                        values[plug] = 100.0 * n + k
                return Solution(values, ["the FK forearm twist is lost on arm_l (an IK elbow is "
                                         "a hinge): %d deg" % n], {})

            def measure(self, wanted):
                outer.world.log.append(("measure", wanted["index"]))
                return outer.world.measured.get(wanted["index"], (0.0001, 0.0, None))
        self.Solver = Solver


class FakeSkelsolve(object):

    def __init__(self, world):
        self.world = world

    def solve(self, ref, bones, wanted, members, seed=None, root=False):
        self.world.calls += 1
        if self.world.fail_at == self.world.calls:
            raise RuntimeError("solve failed")
        n = float(self.world.calls)
        self.world.log.append(("skel", wanted["index"], None if seed is None else dict(seed),
                               root, list(members)))
        values = OrderedDict([(HAND + ".rotateX", n)])
        if root or self.world.top_member:
            values[SKEL_ROOT + ".translateX"] = 10.0 * n
        return Solution(values, [], {})

    def root_leaf(self, ref, bones):
        return "root"


def rig_ref(namespace="Manny_Rig1"):
    root = "|Manny_Rig_Character|%s:root" % namespace
    return real_scene.CharacterRef("rig", root, object(), "Manny [rig]", "Manny_Rig", "Manny",
                                   namespace)


def skel_ref():
    return real_scene.CharacterRef("skeleton", SKEL_ROOT, None, "Manny UE5 [skeleton]",
                                   "Manny_Skeleton", "Manny", "")


def target_bones(root):
    bones = OrderedDict()
    for name, parent in (("root", None), ("pelvis", "root"), ("hand_l", "pelvis"),
                         ("hand_r", "pelvis")):
        bones[name] = {"path": root if name == "root" else root + "|" + name, "parent": parent,
                       "canonical": name, "rest": ident(), "world": ident(), "rotateOrder": 0,
                       "jointOrient": [0.0, 0.0, 0.0], "rotateAxis": [0.0, 0.0, 0.0]}
    return bones


class Progress(object):
    """A progress window answering False (Esc pressed) on its `cancel_at`-th step."""

    def __init__(self, cancel_at=None):
        self.cancel_at = cancel_at
        self.steps = []

    def step(self, text=""):
        self.steps.append(text)
        return self.cancel_at is None or len(self.steps) < self.cancel_at


class Base(unittest.TestCase):

    def setUp(self):
        self.saved = dict((name, getattr(aa, name)) for name in SEAMS)
        self.saved_ap = dict((name, getattr(ap, name)) for name in AP_SEAMS)
        self.world = World()
        self.ref = rig_ref()
        self.skel = skel_ref()
        aa.cmds = FakeCmds(self.world)
        aa.keys = FakeKeys(self.world)
        aa.scene = FakeScene(self.world, {self.ref.root: target_bones(self.ref.root),
                                          SKEL_ROOT: target_bones(SKEL_ROOT)})
        aa.pm = FakePm(self.world)
        aa.rigsolve = FakeRigsolve(self.world)
        aa.skelsolve = FakeSkelsolve(self.world)
        aa.timewalk = FakeTimewalk(self.world)
        aa._targets = lambda selection, prefer=None: ([self.ref], "")
        aa._main_of = lambda ref: MAIN
        aa._rotations = lambda values: {}
        aa._measure_skeleton = self.measure_skeleton
        self.header, self.frames = card()

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(aa, name, value)
        for name, value in self.saved_ap.items():
            setattr(ap, name, value)

    def measure_skeleton(self, ref, values, skipped, wanted, members, bones):
        self.world.log.append(("measure", wanted["index"]))
        return self.world.measured.get(wanted["index"], (0.0001, 0.0, None))

    def press(self, **kw):
        return aa.apply(self.header, self.frames, **kw)

    def writes(self):
        return self.world.entries("write")

    def solves(self):
        return [entry for entry in self.world.log if entry[0] in ("solve", "skel")]


# ------------------------------------------------------------------ pure

class Pure(unittest.TestCase):

    def test_options_of_what_a_caller_passes(self):
        self.assertEqual(aa._options(None), animdata.Options())
        given = animdata.Options(mode="insert")
        self.assertIs(aa._options(given), given)
        self.assertEqual(aa._options({"mode": "merge", "connect": "1", "in_place": 0}),
                         animdata.Options(mode="merge", connect=True))
        self.assertEqual(aa._options({"mode": "nonsense"}).mode, "replace")

    def test_a_stored_curve_clipped_to_the_range(self):
        stored = [[0.0, 0.0], [10.0, 5.0], [20.0, 1.0]]
        # on keys: the keys inside, nothing to insert
        self.assertEqual(aa._clip(stored, 0, 10), ([[0.0, 0.0], [10.0, 5.0]], []))
        # between keys: both ends wanted
        self.assertEqual(aa._clip(stored, 4, 15), ([[10.0, 5.0]], [4, 15]))
        # past the last key, before the first: nothing to insert there (the curve is held)
        self.assertEqual(aa._clip(stored, 15, 30), ([[20.0, 1.0]], [15]))
        self.assertEqual(aa._clip(stored, -5, 0), ([[0.0, 0.0]], []))
        # one frame between keys: one insert
        self.assertEqual(aa._clip(stored, 4, 4), ([], [4]))

    def test_the_value_a_curve_holds_outside_its_keys(self):
        stored = [[0.0, 3.0], [10.0, 5.0]]
        self.assertEqual(aa._held(stored, -4), 3.0)
        self.assertEqual(aa._held(stored, 14), 5.0)

    def test_a_note_repeated_every_frame_with_another_number_is_one_note(self):
        self.assertEqual(aa._note_key("the FK forearm twist is lost on arm_l: 31 deg"),
                         aa._note_key("the FK forearm twist is lost on arm_l: 7.5 deg"))
        self.assertEqual(aa._note_key("the IK toes do not reach the ball's turn on leg_l: 9 deg"),
                         aa._note_key("the IK toes do not reach the ball's turn on leg_l: 10 deg"))
        self.assertNotEqual(aa._note_key("no hand_l on Creep_Rig"),
                            aa._note_key("no hand_r on Creep_Rig"))
        # a number INSIDE a name is the name's: two bones, two rigs, two notes
        self.assertNotEqual(aa._note_key("1 not posed (locked): spine_01"),
                            aa._note_key("1 not posed (locked): spine_02"))
        self.assertNotEqual(aa._note_key("no hand_l on Manny_Rig1"),
                            aa._note_key("no hand_l on Manny_Rig2"))

    def test_the_frame_a_blend_previews(self):
        plan = animdata.paste_plan(0, 5, None, animdata.Options(at_current=False), 0)
        self.assertEqual(aa._shown(plan, 3.0), (3, 3))
        self.assertEqual(aa._shown(plan, 3.4), (3, 3))
        self.assertEqual(aa._shown(plan, 9.0), (0, 0))          # outside: the first
        self.assertEqual(aa._shown(plan, -2.0), (0, 0))
        plan = animdata.paste_plan(0, 5, None, animdata.Options(), 12)
        self.assertEqual(aa._shown(plan, 12.0), (0, 0))         # at the current frame: the first


# ------------------------------------------------------------------ the character press

class Order(Base):

    def test_the_order_of_a_press(self):
        ok, text = self.press()
        self.assertTrue(ok, text)
        names = self.world.names()
        wanted = ["layer", "quaternion", "walk", "arrive", "skeleton", "solve", "current",
                  "shown", "open", "mark", "state", "cut", "arrive", "solve", "write"] + \
            ["go", "solve", "write"] * 5 + ["restate", "close", "walked"]
        got = [n for n in names if n in set(wanted)]
        self.assertEqual(got, wanted)
        self.assertEqual(self.world.entries("walk"), [("walk", True)])
        self.assertEqual(self.world.entries("open"), [("open", aa.UNDO_CHUNK)])
        self.assertEqual(aa.UNDO_CHUNK, "skeldarAnimApply")
        # the paste starts on the current frame: the walk sets no time there (M2: a time set
        # on the frame the scene stands on throws the animator's tweaks away), then goes to
        # every planned frame in order, each key on the frame the walk stands on
        self.assertEqual([e[1] for e in self.world.entries("arrive")], [12, 12])
        self.assertEqual([e[1] for e in self.world.entries("go")], [13, 14, 15, 16, 17])
        self.assertEqual([e[2] for e in self.writes()], [12, 13, 14, 15, 16, 17])
        # a solve per frame, of that frame's source, after a fresh read of the target there
        self.assertEqual([e[1] for e in self.solves()], [0, 0, 1, 2, 3, 4, 5])
        self.assertEqual([e[2] for e in self.world.entries("refresh")],
                         [12, 13, 14, 15, 16, 17])
        # autoKey off inside the chunk and back before it closes
        opened = names.index("open")
        closed = names.index("close")
        self.assertEqual(self.world.log[opened + 1], ("autoKey", False))
        self.assertEqual(self.world.log[closed - 1], ("autoKey", True))
        self.assertTrue(self.world.auto)

    def test_the_dry_solve_leaves_no_undo_step(self):
        self.press()
        names = self.world.names()
        dry = names.index("solve")
        self.assertEqual(self.world.log[names.index("record")], ("record", False))
        self.assertLess(names.index("record"), dry)
        back = names.index("record", dry)
        self.assertEqual(self.world.log[back], ("record", True))
        self.assertLess(back, names.index("open"))
        self.assertTrue(self.world.recording)

    def test_the_paste_modes_ops_on_the_planned_plugs(self):
        plugs = sorted([WRIST] + MAIN_PLUGS)
        for mode, op in (("replace", ("cut", plugs, 12, 17)),
                         ("replace_all", ("cut", plugs, None, None)),
                         ("insert", ("shift", plugs, 12, 6)),
                         ("merge", None)):
            del self.world.log[:]
            self.world.calls = 0
            ok, text = self.press(options={"mode": mode})
            self.assertTrue(ok, text)
            ops = [e for e in self.world.log if e[0] in ("cut", "shift")]
            self.assertEqual(ops, [op] if op else [], mode)
            names = self.world.names()
            if op:
                self.assertLess(names.index("open"), names.index(op[0]), mode)
                self.assertLess(names.index(op[0]), names.index("write"), mode)
            # the curves' infinity and weighting read before the ops, given back after the keys
            self.assertLess(names.index("state"), names.index("write"), mode)
            self.assertLess(max(i for i, n in enumerate(names) if n == "write"),
                            names.index("restate"), mode)

    def test_every_frame_is_seeded_with_the_one_before(self):
        self.press()
        solves = self.solves()
        values = [OrderedDict([(WRIST, float(n))] + [(p, 100.0 * n + k)
                                                     for k, p in enumerate(MAIN_PLUGS)])
                  for n in range(1, 8)]
        self.assertIsNone(solves[0][2])                     # the dry solve: the scene's values
        self.assertEqual(solves[1][2], dict(values[0]))     # frame 0: the dry solve's
        for i in range(2, 7):
            self.assertEqual(solves[i][2], dict(values[i - 1]), i)

    def test_the_keyed_plugs_are_the_walks_so_it_never_sets_them_back(self):
        self.press()
        walk = self.world.walks[0]
        written = [p for e in self.writes() for p in e[1]]
        # every plug keyed handed over ONCE: the walk's exit resolves each to its node's UUID
        self.assertEqual(walk.keyed, list(OrderedDict.fromkeys(written)))
        self.assertEqual(len(written), 6 * len(walk.keyed))

    def test_the_keyed_curves_are_dirtied_before_the_measure(self):
        self.press()
        names = self.world.names()
        first_write = names.index("write")
        self.assertEqual(self.world.log[first_write + 1],
                         ("dirty", ["curve:" + p for p in self.writes()[0][1]]))
        self.assertLess(first_write + 1, names.index("measure"))


class Travel(Base):

    def test_the_travel_is_carried_from_where_the_character_stands(self):
        self.press()
        self.assertEqual(self.world.entries("solver"),
                         [("solver", ["pelvis", "hand_l"], True)])
        frames = self.world.entries("frame")
        # the dry solve at the paste frame: the root frame where the character stands
        self.assertEqual(frames[0][3], flat(self.world.place))
        # each frame: travel(source i, the first) . place
        for i, entry in enumerate(frames[1:]):
            self.assertEqual(entry[1], i)
            self.assertEqual(entry[3], flat(moved(10.0 * i) * self.world.place), i)
        travels = self.world.entries("travel")
        self.assertEqual([(e[1], e[2], e[3]) for e in travels],
                         [(i, 0, False) for i in range(6)])

    def test_in_place_carries_nothing(self):
        self.press(options={"in_place": True})
        self.assertEqual(self.world.entries("solver"), [("solver", ["pelvis", "hand_l"], False)])
        self.assertTrue(all(e[3] is None for e in self.world.entries("frame")))
        self.assertEqual(self.world.entries("travel"), [])
        self.assertTrue(all(MAIN_SHORT not in "".join(e[1]) for e in self.writes()))

    def test_a_hand_card_carries_nothing(self):
        self.header, self.frames = card(members=("hand_l",))
        self.press()
        self.assertEqual(self.world.entries("solver"), [("solver", ["hand_l"], False)])
        self.assertTrue(all(e[3] is None for e in self.world.entries("frame")))
        self.assertEqual(self.world.entries("travel"), [])

    def test_a_main_that_cannot_be_written_is_not_carried_and_said(self):
        self.world.blocked[MAIN + ".translateY"] = "locked"
        ok, text = self.press()
        self.assertTrue(ok, text)
        self.assertEqual(self.world.entries("solver"), [("solver", ["pelvis", "hand_l"], False)])
        self.assertTrue(all(e[3] is None for e in self.world.entries("frame")))
        self.assertIn(real_rigsolve.MAIN_KEPT % "translateY locked", text)

    def test_a_skeleton_writes_its_root_for_the_travel(self):
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        ok, text = self.press()
        self.assertTrue(ok, text)
        skels = self.world.entries("skel")
        self.assertEqual(len(skels), 7)
        self.assertTrue(all(e[3] is True for e in skels))           # root=True: the travel
        self.assertEqual(skels[0][4], ["pelvis", "hand_l"])
        self.assertIsNone(skels[0][2])
        self.assertEqual(skels[1][2], {HAND + ".rotateX": 1.0, SKEL_ROOT + ".translateX": 10.0})
        self.assertTrue(text.startswith("Walk onto Manny UE5 [skeleton] (root): 2 joints keyed"),
                        text)

    def test_a_skeleton_root_that_cannot_be_written_is_not_carried_and_said(self):
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        self.world.blocked[SKEL_ROOT + ".rotateZ"] = "driven by root_parentConstraint1"
        ok, text = self.press()
        self.assertTrue(all(e[3] is False for e in self.world.entries("skel")))
        self.assertIn(aa.ROOT_KEPT % ("root", "rotateZ driven by root_parentConstraint1"), text)

    def test_a_rootless_skeleton_keeps_the_moving_ground(self):
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        aa.pm = FakePm(self.world, rooted=False)
        self.press()
        frames = self.world.entries("frame")
        self.assertEqual(frames[-1][3], flat(moved(50.0) * self.world.place))
        self.assertTrue(all(e[3] is True for e in self.world.entries("skel")))

    def test_a_rootless_skeleton_whose_top_joint_cannot_be_written_carries_nothing(self):
        """The final review (S6): a rootless target carries the travel on its top joint, a
        member written anyway - and it was never asked whether all six of its channels can be:
        a locked hips translate turned the body on a ground that stayed. All six or none, as
        for Main and a root - and the line says so."""
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        aa.pm = FakePm(self.world, rooted=False)
        self.world.blocked[SKEL_ROOT + ".translateZ"] = "locked"
        ok, text = self.press()
        self.assertTrue(all(e[3] is False for e in self.world.entries("skel")))
        self.assertTrue(all(e[3] is None for e in self.world.entries("frame")))
        self.assertEqual(self.world.entries("travel"), [])
        self.assertIn(aa.ROOT_KEPT % ("root", "translateZ locked"), text)


class Rootless(Base):
    """A card with no root of its own (Mixamo's Hips): its root frame on every frame from
    `posemath.clip_roots`, its heading steadied across the clip (the final review, M3) - the
    travel, the transfer's pelvis offset and the mirror all read that one."""

    def setUp(self):
        Base.setUp(self)
        aa.pm = FakePm(self.world, rooted=False)

    def test_the_travel_and_the_frame_read_the_steadied_roots(self):
        ok, text = self.press()
        self.assertTrue(ok, text)
        self.assertEqual(self.world.entries("clip_roots"), [("clip_roots", 6)])
        root = lambda i: flat(moved(0.0, 0.0, 1000.0 + i))         # noqa: E731
        self.assertEqual([e[1:] for e in self.world.entries("travel_roots")],
                         [(root(i), root(0)) for i in range(6)])
        # the dry solve and every frame: the source's root frame is the steadied one
        self.assertEqual([e[1:] for e in self.world.entries("source_root")],
                         [(0, root(0))] + [(i, root(i)) for i in range(6)])

    def test_mirrored_the_mirror_plane_is_the_steadied_root_s(self):
        self.press(mirror=True)
        root = lambda i: flat(moved(0.0, 0.0, 1000.0 + i))         # noqa: E731
        self.assertEqual([e[1:] for e in self.world.entries("mirror")],
                         [(0, root(0))] + [(i, root(i)) for i in range(6)])

    def test_a_part_of_the_clip_steadies_over_that_part(self):
        self.press(options={"at_current": False, "start": 2, "end": 4})
        self.assertEqual(self.world.entries("clip_roots"), [("clip_roots", 3)])
        self.assertEqual(self.world.entries("source_root")[0][1:],
                         (2, flat(moved(0.0, 0.0, 1002.0))))

    def test_a_rooted_card_steadies_nothing(self):
        aa.pm = FakePm(self.world, rooted=True)
        self.press(mirror=True)
        self.assertEqual(self.world.entries("clip_roots"), [])
        self.assertEqual(self.world.entries("source_root"), [])
        self.assertEqual(self.world.entries("travel_roots"), [])
        self.assertTrue(all(e[2] is None for e in self.world.entries("mirror")))


class InPlaceGround(Base):
    """The final review (M4): a ROOTLESS target pasted In place stands on the ground its top
    joint makes - and that joint is a planned member, cut by Replace and keyed every frame, so
    frame i read its ground off the curve the press was rewriting. It is read at every pasted
    frame BEFORE the ops and handed to the transfer."""

    def setUp(self):
        Base.setUp(self)
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        aa.pm = FakePm(self.world, rooted=False)
        self.world.top_member = True
        self.world.ground_of = lambda frame: ident(7.0 * frame, 0.0, 3.0)

    def test_the_ground_of_every_pasted_frame_is_read_before_the_ops(self):
        ok, text = self.press(options={"in_place": True})
        self.assertTrue(ok, text)
        names = self.world.names()
        cut = names.index("cut")
        before = [e for e in self.world.log[:cut] if e[0] == "refresh"]
        self.assertEqual([e[2] for e in before], [12, 13, 14, 15, 16, 17])
        # every frame's transfer stands on the ground read there BEFORE anything was cut
        frames = self.world.entries("frame")[1:]
        self.assertEqual([e[3] for e in frames],
                         [flat(ident(7.0 * t, 0.0, 3.0)) for t in range(12, 18)])

    def test_under_insert_every_pasted_frame_stands_on_the_ground_at_a(self):
        """The re-review of the fix wave (M4 regressed under Insert): Insert moves the take's
        frames from `a` on to after the clip, while the grounds were read off the take BEFORE the
        ops - the paste rode the take's own a..b ground, then the shifted take resumed after it
        from its frame-a ground: a target walking 200 cm over the range snapped back 200 cm.
        Under Insert every pasted frame stands on the take's ground at `a`, where the shifted
        take resumes - read once, the walk going nowhere else for it."""
        ok, text = self.press(options={"in_place": True, "mode": "insert"})
        self.assertTrue(ok, text)
        names = self.world.names()
        shift = names.index("shift")
        before = [e for e in self.world.log[:shift] if e[0] == "refresh"]
        self.assertEqual([e[2] for e in before], [12])
        self.assertEqual([e for e in self.world.log[:shift] if e[0] == "go"], [])
        frames = self.world.entries("frame")[1:]
        self.assertEqual([e[3] for e in frames], [flat(ident(84.0, 0.0, 3.0))] * 6)

    def test_under_insert_a_blend_still_reads_the_take_on_every_frame(self):
        self.world.values = {SKEL_ROOT + ".translateX": lambda frame: 2.0 * frame}
        ok, text = self.press(options={"in_place": True, "mode": "insert"}, alpha=0.5)
        self.assertTrue(ok, text)
        shift = self.world.names().index("shift")
        reads = [e[1] for e in self.world.log[:shift] if e[0] == "current"]
        self.assertEqual(reads, [12, 12, 13, 14, 15, 16, 17])
        grounds = [e[2] for e in self.world.log[:shift] if e[0] == "refresh"]
        self.assertEqual(grounds, [12])
        frames = self.world.entries("frame")[1:]
        self.assertEqual([e[3] for e in frames], [flat(ident(84.0, 0.0, 3.0))] * 6)

    def test_merge_reads_the_ground_of_every_frame(self):
        ok, text = self.press(options={"in_place": True, "mode": "merge"})
        self.assertTrue(ok, text)
        opened = self.world.names().index("open")
        before = [e for e in self.world.log[:opened] if e[0] == "refresh"]
        self.assertEqual([e[2] for e in before], [12, 13, 14, 15, 16, 17])
        frames = self.world.entries("frame")[1:]
        self.assertEqual([e[3] for e in frames],
                         [flat(ident(7.0 * t, 0.0, 3.0)) for t in range(12, 18)])

    def test_the_take_s_frame_a_ground_stands_for(self):
        plan = animdata.paste_plan(0, 5, None, animdata.Options(mode="insert"), 12)
        self.assertEqual([aa._ground_time(plan, t) for _s, _i, t in plan.frames], [12] * 6)
        for mode in ("replace", "replace_all", "merge"):
            plan = animdata.paste_plan(0, 5, None, animdata.Options(mode=mode), 12)
            self.assertEqual([aa._ground_time(plan, t) for _s, _i, t in plan.frames],
                             list(range(12, 18)), mode)

    def test_a_target_carrying_the_travel_reads_no_ground(self):
        self.press()
        cut = self.world.names().index("cut")
        self.assertEqual([e for e in self.world.log[:cut] if e[0] == "refresh"], [])

    def test_a_rooted_target_in_place_reads_no_ground(self):
        aa.pm = FakePm(self.world, rooted=True)
        self.press(options={"in_place": True})
        cut = self.world.names().index("cut")
        self.assertEqual([e for e in self.world.log[:cut] if e[0] == "refresh"], [])
        self.assertTrue(all(e[3] is None for e in self.world.entries("frame")))


class UndoMark(Base):
    """The final review (M1): every frame's solve records its temporary sets and their restores
    in the press's chunk, at frames that are not the current one, and one Ctrl+Z replayed them
    backwards - every planned channel ended showing the FIRST pasted frame's value. The chunk's
    first step now sets each planned channel to what it showed when the press began."""

    def test_the_first_step_of_the_chunk_marks_what_the_planned_plugs_showed(self):
        self.world.values = {WRIST: lambda frame: 2.0 * frame,
                             MAIN_SHORT + ".translateX": lambda frame: 100.0 + frame}
        ok, text = self.press(options={"at_current": False})       # pasted at 0..5, now 12
        self.assertTrue(ok, text)
        names = self.world.names()
        opened = names.index("open")
        marks = self.world.entries("mark")
        self.assertEqual(len(marks), 1)
        # right after autoKey goes off, before any curve is read, cut or keyed
        self.assertEqual(self.world.log[opened + 1], ("autoKey", False))
        self.assertEqual(names[opened + 2], "mark")
        values = marks[0][1]
        self.assertEqual(sorted(values), sorted([WRIST] + MAIN_PLUGS))
        # what they showed on frame 12, where the press began - never frame 0's
        self.assertEqual(values[WRIST], 24.0)
        self.assertEqual(values[MAIN_SHORT + ".translateX"], 112.0)

    def test_no_planned_plug_no_mark(self):
        aa.rigsolve = FakeRigsolve(self.world)
        empty = type("Solver", (object,), {
            "__init__": lambda s, rig, members, main=False: None,
            "solve": lambda s, wanted, seed=None: Solution(OrderedDict(), [], {}),
            "measure": lambda s, wanted: (0.0, 0.0, None)})
        aa.rigsolve.Solver = empty
        self.press()
        self.assertEqual(self.world.entries("mark"), [])
        self.assertNotIn("open", self.world.names())


class Mirror(Base):

    def test_aligned_off_the_unmirrored_first_frame_and_given_mirrored_frames(self):
        ok, text = self.press(mirror=True)
        self.assertTrue(ok, text)
        # the transfer: the first frame UNMIRRORED (its alignment), the members mirrored
        self.assertEqual(self.world.entries("transfer"),
                         [("transfer", 0, False, ["hand_r", "pelvis"], True)])
        self.assertEqual(self.world.entries("solver"), [("solver", ["pelvis", "hand_r"], True)])
        # every frame handed over mirrored, the travel read off the unmirrored frames, flipped
        self.assertTrue(all(e[2] is True for e in self.world.entries("frame")))
        travels = self.world.entries("travel")
        self.assertTrue(all(e[3] is True and e[4] is False for e in travels))
        self.assertIn("Walk mirrored onto Manny_Rig1", text)


class Connect(Base):

    def test_every_channel_takes_what_it_showed_but_main(self):
        self.world.values = {WRIST: 5.0, MAIN_SHORT + ".translateX": 7.0}
        ok, text = self.press(options={"connect": True})
        self.assertTrue(ok, text)
        writes = self.writes()
        # the dry solve answered 1.0 (the first solve): every frame moved by 5 - 1
        for k, entry in enumerate(writes):
            n = k + 2                                         # the walk's solves: 2..7
            self.assertAlmostEqual(entry[1][WRIST], n + 4.0, places=12)
            for j, plug in enumerate(MAIN_PLUGS):            # Main: placed, never offset
                self.assertEqual(entry[1][plug], 100.0 * n + j)
        self.assertAlmostEqual(writes[0][1][WRIST], 5.0 + 1.0, places=12)

    def test_a_connected_paste_is_not_measured_and_says_no_worst(self):
        # Connect moves every channel off the transfer ON PURPOSE (to start where it stood): the
        # wrist 20 deg off the clip's first frame, measured against the transfer, would read
        # «worst 20 deg / 3.5 cm at frame 14» on a correct paste - the review's case
        self.world.values = {WRIST: 21.0}                     # the dry solve answers 1.0
        self.world.measured = {2: (20.0, 3.5, "hand_l")}     # what the measure would read
        ok, text = self.press(options={"connect": True})
        self.assertTrue(ok, text)
        self.assertNotIn("measure", self.world.names())
        self.assertNotIn("worst", text)
        self.assertEqual(text.split(" | ")[0],
                         "Walk onto Manny_Rig1: 2 controls keyed over frames 12-17 (6 frames, "
                         "replace)")
        # the keys are still the solve moved by Connect's offset (20 = 21 - 1)
        self.assertEqual([e[1][WRIST] for e in self.writes()],
                         [float(n) + 20.0 for n in range(2, 8)])

    def test_a_connected_paste_onto_a_skeleton_is_not_measured(self):
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        self.world.values = {HAND + ".rotateX": 21.0}
        self.world.measured = {2: (20.0, 0.0, "hand_l")}
        ok, text = self.press(options={"connect": True})
        self.assertTrue(ok, text)
        self.assertNotIn("measure", self.world.names())
        self.assertNotIn("worst", text)
        # the root carries the travel: placed, never offset - so it alone is no reason to skip
        self.assertEqual([e[1][SKEL_ROOT + ".translateX"] for e in self.writes()],
                         [10.0 * n for n in range(2, 8)])

    def test_a_connect_that_moves_no_channel_is_measured(self):
        # the take already stands where the clip's first frame puts it: every offset 0, the keys
        # ARE the transfer's solve, and the line says how close it came (Main's own difference
        # is no offset - the travel is placed)
        self.world.values = {WRIST: 1.0}                      # the dry solve answers 1.0
        self.world.measured = {2: (0.25, 0.0, "hand_l")}
        ok, text = self.press(options={"connect": True})
        self.assertTrue(ok, text)
        self.assertEqual([e[1] for e in self.world.entries("measure")], [0, 1, 2, 3, 4, 5])
        self.assertIn(" - worst 0.25 deg at frame 14", text)


class BlendPress(Base):

    def test_at_half_the_take_as_it_stood_is_the_partner_of_the_mix(self):
        self.world.values = {WRIST: lambda frame: 2.0 * frame}
        ok, text = self.press(alpha=0.5)
        self.assertTrue(ok, text)
        names = self.world.names()
        opened = names.index("open")
        # one walk over the paste range reading the planned plugs, before anything changes
        reads = [e for e in self.world.log[:opened] if e[0] == "current"]
        self.assertEqual([e[1] for e in reads], [12, 12, 13, 14, 15, 16, 17])
        for k, entry in enumerate(self.writes()):
            t = 12 + k
            solved = float(k + 2)
            self.assertAlmostEqual(entry[1][WRIST], 2.0 * t + (solved - 2.0 * t) * 0.5,
                                   places=12)
        self.assertIn("Walk at 50 % onto Manny_Rig1", text)
        self.assertNotIn("measure", names)                   # a blend lands between: unmeasured

    def test_nothing_at_zero(self):
        ok, text = self.press(alpha=0.0)
        self.assertEqual((ok, text), (False, ap.BLEND_ZERO))
        self.assertEqual(self.world.names(), ["layer", "quaternion"])


class Cancel(Base):

    def test_esc_on_the_third_frame_undoes_the_press(self):
        progress = Progress(cancel_at=3)
        ok, text = self.press(progress=progress)
        self.assertEqual((ok, text), (False, aa.CANCELLED))
        self.assertEqual(aa.CANCELLED, "cancelled - nothing changed")
        self.assertEqual(len(self.writes()), 3)
        names = self.world.names()
        last_write = max(i for i, n in enumerate(names) if n == "write")
        tail = [n for n in names[last_write + 1:] if n in ("close", "undo", "restore_all",
                                                             "walked", "restate", "go")]
        self.assertEqual(tail, ["close", "undo", "restore_all", "walked"])
        self.assertEqual(names.count("undo"), 1)
        self.assertEqual(len(progress.steps), 3)

    def test_with_undo_off_a_cancel_says_what_stays(self):
        """The final review (S3): with undo off nothing can be undone - so what was keyed
        stays, its curves get their infinity and weighting back like any paste's, the walk
        never sets the keyed plugs back as tweaks (they show their new keys), and the line
        names what stays: the frames keyed and what the mode did to the keys."""
        self.world.recording = False
        self.world.cut_count = 14
        ok, text = self.press(progress=Progress(cancel_at=2))
        self.assertEqual((ok, text), (False, aa.CANCELLED_KEPT % (
            "frames 12-13 keyed, 14 keys of the pasted channels in 12-17 cut")))
        names = self.world.names()
        self.assertNotIn("undo", names)
        self.assertNotIn("restore_all", names)
        self.assertIn("restate", names)
        self.assertLess(max(i for i, n in enumerate(names) if n == "write"),
                        names.index("restate"))
        self.assertTrue(self.world.walks[0].keyed)               # handed over, never set back

    def test_with_undo_off_the_line_says_what_each_mode_did(self):
        self.world.recording = False
        self.world.cut_count, self.world.shift_count = 40, 9
        for mode, done in (("replace_all", "40 keys of the pasted channels cut"),
                           ("insert", "9 keys of the pasted channels from 12 on moved 6 later"),
                           ("merge", None)):
            self.world.calls = 0
            ok, text = self.press(options={"mode": mode}, progress=Progress(cancel_at=1))
            want = "frame 12 keyed" + (", " + done if done else "")
            self.assertEqual(text, aa.CANCELLED_KEPT % want, mode)

    def test_with_undo_off_a_cut_or_move_that_did_not_happen_is_not_claimed(self):
        """The re-review of the fix wave: the line said «keys in a-b cut» (or moved) from the
        plan's ops, even when the curves lost nothing - a REFERENCED curve only warns and keeps
        its keys, and `keys.cut` / `shift` answer the keys that really went (0 here). It says
        what the curves lost."""
        self.world.recording = False
        for mode in ("replace", "replace_all", "insert"):
            self.world.calls = 0
            ok, text = self.press(options={"mode": mode}, progress=Progress(cancel_at=1))
            self.assertEqual(text, aa.CANCELLED_KEPT % "frame 12 keyed", mode)

    def test_an_error_mid_press_undoes_the_half_paste_and_raises(self):
        """The final review (S2): a solve that raised on the third frame left two frames keyed
        and the cut done - the chunk closed with half a paste in it. Now it is undone (one
        `cmds.undo`, after the chunk closed), every tweak set back, and the error goes on."""
        self.world.fail_at = 4                    # the dry solve, then frames 12, 13 - then 14
        with self.assertRaises(RuntimeError):
            self.press()
        names = self.world.names()
        self.assertEqual(len(self.writes()), 2)
        tail = [n for n in names[names.index("close"):] if n in
                ("close", "undo", "restore_all", "walked", "restate")]
        self.assertEqual(tail, ["close", "undo", "restore_all", "walked"])
        self.assertTrue(self.world.auto)          # autoKey back

    def test_an_error_with_undo_off_undoes_nothing(self):
        self.world.recording = False
        self.world.fail_at = 4
        with self.assertRaises(RuntimeError):
            self.press()
        self.assertNotIn("undo", self.world.names())
        self.assertNotIn("restore_all", self.world.names())

    def test_a_chunk_that_recorded_nothing_undoes_nothing(self):
        """The re-review of the fix wave: when the chunk's first question - autoKey's state -
        raised, the chunk closed holding no step of the press, and `_undo_failed`'s Ctrl+Z
        undid the ANIMATOR's step before it. Only what the press recorded is undone: nothing
        here, the error goes on."""
        self.world.auto_query_fails = True
        with self.assertRaises(RuntimeError):
            self.press()
        names = self.world.names()
        self.assertEqual(names[names.index("open"):], ["open", "close", "walked"])
        self.assertNotIn("undo", names)
        self.assertNotIn("write", names)


class Refusals(Base):

    def test_a_locked_layer_refuses_before_the_walk(self):
        aa.keys = FakeKeys(self.world, refusal=real_keys.LOCKED % "L")
        self.assertEqual(self.press(), (False, real_keys.LOCKED % "L"))
        self.assertEqual(self.world.log, [("layer",)])

    def test_a_quaternion_layer_refuses_a_character_card(self):
        note = real_keys.QUATERNION % "Q"
        aa.keys = FakeKeys(self.world, layer=LAYER, quaternion=note)
        self.assertEqual(self.press(), (False, note))
        self.assertEqual(self.world.log, [("layer",), ("quaternion",)])

    def test_an_empty_range_is_refused(self):
        ok, text = self.press(options={"start": 10, "end": 20})
        self.assertEqual((ok, text), (False, animdata.EMPTY_RANGE))
        self.assertNotIn("walk", self.world.names())

    def test_a_card_without_frames(self):
        for frames in (None, {}, {"bones": ["root"], "world": []}):
            self.assertEqual(aa.apply(self.header, frames), (False, aa.NO_FRAMES))
        # frames that do not cover the clip the header says
        short = dict(self.frames, world=self.frames["world"][:3])
        self.assertEqual(aa.apply(self.header, short), (False, aa.NO_FRAMES))
        self.assertNotIn("walk", self.world.names())

    def test_no_card_and_no_bones(self):
        self.assertEqual(aa.apply(None, self.frames), (False, ap.NO_CARD))
        self.assertEqual(aa.apply(dict(self.header, bones={}), self.frames), (False, ap.NO_BONES))

    def test_the_selection_s_refusal(self):
        aa._targets = lambda selection, prefer=None: ([], ap.NOT_A_CHARACTER)
        self.assertEqual(self.press(selection=["|pCube1"]), (False, ap.NOT_A_CHARACTER))
        self.assertEqual(self.world.log, [])


class Status(Base):

    def test_the_line(self):
        aa.keys = FakeKeys(self.world, layer=LAYER)
        self.world.measured = {2: (0.25, 0.0, "hand_l"), 4: (0.003, 0.002, "pelvis")}
        ok, text = self.press()
        self.assertTrue(ok)
        self.assertEqual(text.split(" | ")[0],
                         "Walk onto Manny_Rig1: 2 controls keyed over frames 12-17 (6 frames, "
                         "replace) on AnimLayer1 - worst 0.25 deg at frame 14")
        self.assertEqual(text, look.anim_status({
            "name": "Walk", "target": "Manny_Rig1", "count": 2, "noun": "controls",
            "layer": "AnimLayer1", "a": 12, "b": 17, "frames": 6, "mode": "replace",
            "worst": (0.25, 0.0), "worst_frame": 14, "alpha": 1.0, "mirror": False,
            "notes": ["the FK forearm twist is lost on arm_l (an IK elbow is a hinge): 1 deg"]}))

    def test_a_note_every_frame_repeats_is_said_once(self):
        ok, text = self.press()
        self.assertEqual(text.count("the FK forearm twist is lost"), 1)

    def test_a_card_at_another_rate_is_pasted_frame_for_frame_and_said(self):
        self.world.unit = "film"
        ok, text = self.press()
        self.assertIn(aa.FPS_NOTE % ("ntsc", "film"), text)
        self.assertEqual(aa.FPS_NOTE % ("ntsc", "film"),
                         "the card is ntsc, the scene film - pasted frame for frame")

    def test_a_muted_layer_is_said(self):
        aa.keys = FakeKeys(self.world, layer=real_keys.Layer("M", False, True, False, False,
                                                             True, 1.0))
        ok, text = self.press()
        self.assertIn(real_keys.MUTED % "M", text)

    def test_the_source_keys_paste_only_at_the_source_s_key_times(self):
        self.header, self.frames = card(count=6, key_times=[0, 2, 5])
        ok, text = self.press(options={"keys": "source"})
        self.assertEqual([e[2] for e in self.writes()], [12, 14, 17])
        self.assertIn("over frames 12-17 (6 frames, replace)", text)

    def test_at_its_own_frames_and_a_part_of_the_clip(self):
        self.press(options={"at_current": False, "start": 2, "end": 4})
        self.assertEqual([e[2] for e in self.writes()], [2, 3, 4])
        self.assertEqual([e[1] for e in self.solves()], [2, 2, 3, 4])


# ------------------------------------------------------------------ objects

def loc_card():
    tx = {"keys": [[0.0, 0.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
                   [10.0, 5.0, "linear", "linear", 26.6, 1.0, 26.6, 1.0]],
          "weighted": False, "breakdown": []}
    return {"format": "skeldar.anim", "version": 1, "kind": "objects", "name": "Loc",
            "fps": "ntsc", "start": 0.0, "end": 10.0, "frames": 11,
            "objects": [{"name": "loc", "path": "|loc",
                         "attrs": {"translateX": tx, "visibility": {"static": 1.0}}}]}


class Objects(Base):

    def setUp(self):
        Base.setUp(self)
        self.world.frame = 30.0
        self.objects = loc_card()
        record = self.objects["objects"][0]
        aa._objects_pairs = lambda header, selection: ([(record, "|locB")], [], "")

    def keyed(self):
        return dict((e[1], e) for e in self.world.entries("write_keys"))

    def test_keys_shifted_to_the_paste_frame_a_static_attribute_keyed_once(self):
        ok, text = aa.apply(self.objects, None)
        self.assertTrue(ok, text)
        keyed = self.keyed()
        self.assertEqual(keyed["|locB.translateX"][2],
                         [[30.0, 0.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
                          [40.0, 5.0, "linear", "linear", 26.6, 1.0, 26.6, 1.0]])
        self.assertEqual(keyed["|locB.visibility"][2], [[30.0, 1.0]])
        # no layers: the stored curve is the plug's whole motion - tangents and all
        self.assertTrue(all(e[4] is True for e in keyed.values()))
        names = self.world.names()
        self.assertEqual([n for n in names if n in ("layer", "open", "state", "cut",
                                                     "write_keys", "restate", "close")],
                         ["layer", "open", "state", "cut", "write_keys", "write_keys",
                          "restate", "close"])
        self.assertEqual(self.world.entries("cut"),
                         [("cut", ["|locB.translateX", "|locB.visibility"], 30, 40)])
        self.assertNotIn("walk", names)
        self.assertEqual(text, "Loc onto 1 object: 1 object keyed over frames 30-40 (11 "
                               "frames, replace)")

    def test_on_a_layer_only_the_tangent_types_travel(self):
        aa.keys = FakeKeys(self.world, layer=LAYER)
        aa.apply(self.objects, None)
        self.assertTrue(all(e[4] is False for e in self.keyed().values()))

    def weighted_card(self):
        self.objects["objects"][0]["attrs"]["translateX"]["weighted"] = True
        return self.world.entries("restate")

    def test_a_weighted_curve_keyed_with_its_tangents_stays_weighted(self):
        # put_curve_state gives back the TARGET curve's infinity and weighting (a cut that
        # empties a curve deletes it); where the card's keys carry their tangents the card's
        # weighting wins - given back unweighted, the curve would drop the weights just keyed
        self.weighted_card()
        aa.apply(self.objects, None)
        state = self.world.entries("restate")[0][1]
        self.assertEqual(state["|locB.translateX"],
                         {"preInfinity": "cycle", "postInfinity": "constant", "weighted": True})
        self.assertEqual(state["|locB.visibility"]["weighted"], False)
        self.assertEqual(self.keyed()["|locB.translateX"][3], True)

    def test_on_a_layer_the_target_curve_s_weighting_is_given_back(self):
        self.weighted_card()
        aa.keys = FakeKeys(self.world, layer=LAYER)
        aa.apply(self.objects, None)
        state = self.world.entries("restate")[0][1]
        self.assertEqual(state["|locB.translateX"]["weighted"], False)

    def test_insert_and_merge(self):
        aa.apply(self.objects, None, options={"mode": "insert"})
        self.assertEqual(self.world.entries("shift"),
                         [("shift", ["|locB.translateX", "|locB.visibility"], 30, 11)])
        del self.world.log[:]
        aa.apply(self.objects, None, options={"mode": "merge"})
        self.assertEqual([e for e in self.world.log if e[0] in ("cut", "shift")], [])

    def test_connect_starts_every_channel_where_it_stood(self):
        self.world.values = {"|locB.translateX": 2.0, "|locB.visibility": 0.0}
        aa.apply(self.objects, None, options={"connect": True})
        keyed = self.keyed()
        self.assertEqual([k[1] for k in keyed["|locB.translateX"][2]], [2.0, 7.0])
        self.assertEqual([k[1] for k in keyed["|locB.visibility"][2]], [0.0])

    def test_blend_mixes_every_key_with_the_take_where_it_lands(self):
        self.world.values = {"|locB.translateX": lambda frame: frame / 10.0}
        ok, text = aa.apply(self.objects, None, alpha=0.5)
        keyed = self.keyed()
        self.assertEqual([k[1] for k in keyed["|locB.translateX"][2]],
                         [3.0 + (0.0 - 3.0) * 0.5, 4.0 + (5.0 - 4.0) * 0.5])
        self.assertIn("Loc at 50 % onto 1 object", text)

    def test_a_missing_attribute_is_named(self):
        self.world.attrs = {("|locB", "translateX")}
        ok, text = aa.apply(self.objects, None)
        self.assertEqual(list(self.keyed()), ["|locB.translateX"])
        self.assertIn("1 not posed (no such attribute): locB.visibility", text)

    def test_a_quaternion_layer_refuses_only_what_turns(self):
        note = real_keys.QUATERNION % "Q"
        aa.keys = FakeKeys(self.world, layer=LAYER, quaternion=note)
        ok, text = aa.apply(self.objects, None)
        self.assertTrue(ok, text)
        turning = loc_card()
        turning["objects"][0]["attrs"]["rotateY"] = {"static": 30.0}
        record = turning["objects"][0]
        aa._objects_pairs = lambda header, selection: ([(record, "|locB")], [], "")
        self.assertEqual(aa.apply(turning, None), (False, note))

    def test_a_cancel_undoes_the_objects_press(self):
        ok, text = aa.apply(self.objects, None, progress=Progress(cancel_at=1))
        self.assertEqual((ok, text), (False, aa.CANCELLED))
        names = self.world.names()
        self.assertEqual(names[-2:], ["close", "undo"])
        self.assertNotIn("restate", names)

    def test_the_breakdown_keys_land_as_breakdowns(self):
        """The final review (S4): the card keeps which of its keys were breakdowns, and the
        paste keyed them as plain keys. A stored breakdown inside the range is made one again
        on its landed key; one outside the range, or at an inserted end, is no key of the
        paste."""
        tx = self.objects["objects"][0]["attrs"]["translateX"]
        tx["keys"].append([20.0, 2.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0])
        tx["breakdown"] = [10.0, 20.0]
        self.objects.update(end=20.0, frames=21)
        aa.apply(self.objects, None, options={"end": 10})          # 0..10 at 30
        self.assertEqual(self.world.entries("keyframe"),
                         [("keyframe", "curve:|locB.translateX", (40.0, 40.0), True)])
        del self.world.log[:]
        aa.apply(self.objects, None)                                # 0..20 at 30
        self.assertEqual([e[2] for e in self.world.entries("keyframe")],
                         [(40.0, 40.0), (50.0, 50.0)])
        # a key the edit refuses: the line says so, the paste stands
        def refuse(curve, **kw):
            raise RuntimeError("keyframe: referenced\nmore")
        self.world.refuse_breakdown = refuse
        ok, text = aa.apply(self.objects, None)
        self.assertTrue(ok, text)
        self.assertIn(aa.BREAKDOWN_LOST % ("|locB.translateX", "keyframe: referenced"), text)

    def test_with_undo_off_a_cancel_keeps_the_channels_keyed_and_says_so(self):
        self.world.recording = False
        self.world.cut_count = 3
        ok, text = aa.apply(self.objects, None, progress=Progress(cancel_at=1))
        self.assertEqual((ok, text), (False, aa.CANCELLED_KEPT % (
            "1 channel keyed, 3 keys of the channels in 30-40 cut")))
        names = self.world.names()
        self.assertNotIn("undo", names)
        self.assertIn("restate", names)

    def test_an_error_mid_objects_press_undoes_the_half_paste(self):
        def boom(plug, keys_list, layer, weighted=False, tangents=True):
            if plug.endswith("visibility"):
                raise RuntimeError("setKeyframe failed")
            self.world.log.append(("write_keys", plug))
            return real_keys.Written(len(keys_list), [], [plug])
        aa.keys.write_keys = boom
        with self.assertRaises(RuntimeError):
            aa.apply(self.objects, None)
        names = self.world.names()
        self.assertEqual(names[-2:], ["close", "undo"])

    def test_an_objects_chunk_that_recorded_nothing_undoes_nothing(self):
        """The re-review of the fix wave: the objects press undid the animator's step too when
        the chunk's autoKey question raised before the press recorded anything."""
        self.world.auto_query_fails = True
        with self.assertRaises(RuntimeError):
            aa.apply(self.objects, None)
        names = self.world.names()
        self.assertEqual(names[-2:], ["open", "close"])
        self.assertNotIn("undo", names)

    def test_an_objects_card_does_not_go_onto_a_character(self):
        self.assertEqual(aa.apply_onto(self.objects, None, "|root"), (False, ap.OBJECTS_ONTO))
        self.assertEqual(aa.drop_floor(self.objects, None, (0, 0, 0)), (False, ap.OBJECTS_ONTO))


# ------------------------------------------------------------------ drops, select, Blend

class Drops(Base):

    def test_drop_floor_hands_the_animation_press_to_the_pose_s_road(self):
        calls = []

        def drop(data, point, mirror=False, onto=None):
            calls.append((data, point, mirror))
            ok, text = onto("|Manny_Rig_Character|Manny_Rig2:root")
            return ok, "added | " + text
        ap.drop_floor = drop
        pressed = []

        def apply_onto(header, frames, root, mirror=False, alpha=1.0, options=None,
                       progress=None):
            pressed.append((root, mirror, alpha, options, progress))
            return True, "pasted"
        aa.apply_onto = apply_onto
        progress = Progress()
        options = {"mode": "insert"}
        ok, text = aa.drop_floor(self.header, self.frames, (150.0, 0.0, 80.0), True, options,
                                 progress)
        self.assertEqual((ok, text), (True, "added | pasted"))
        self.assertEqual(calls, [(self.header, (150.0, 0.0, 80.0), True)])
        self.assertEqual(pressed, [("|Manny_Rig_Character|Manny_Rig2:root", True, 1.0,
                                    aa._options(options), progress)])

    def test_drop_floor_refuses_what_the_press_would_before_a_character_is_added(self):
        ap.drop_floor = lambda *args, **kwargs: self.fail("a character was added")
        self.assertEqual(aa.drop_floor(self.header, None, (0, 0, 0)), (False, aa.NO_FRAMES))
        self.assertEqual(aa.drop_floor(self.header, self.frames, (0, 0, 0),
                                       options={"start": 40, "end": 50}),
                         (False, animdata.EMPTY_RANGE))

    def test_apply_onto_the_character_dropped_on(self):
        self.world.characters["|Manny_Rig_Character|Manny_Rig1:root"] = self.ref
        aa._targets = lambda selection, prefer=None: self.fail("the selection was asked")
        aa._character_of = self.world.characters.get
        ok, text = aa.apply_onto(self.header, self.frames, "|Manny_Rig_Character|Manny_Rig1:root")
        self.assertTrue(ok, text)
        self.assertTrue(text.startswith("Walk onto Manny_Rig1"), text)
        self.assertEqual(aa.apply_onto(self.header, self.frames, "|nobody"),
                         (False, ap.NOT_FOUND % "|nobody"))


class SelectObjects(Base):

    def setUp(self):
        Base.setUp(self)
        self.selected = []
        ap.select_objects = lambda data, selection=None: (
            self.selected.append(selection) or (True, "Selected 23 controls on Manny_Rig1"))

    def test_main_is_selected_too_when_the_travel_would_be_carried(self):
        ok, text = aa.select_objects(self.header, ["|x"])
        self.assertTrue(ok)
        self.assertEqual(self.world.entries("select"), [("select", [MAIN], True)])
        self.assertEqual(text, "Selected 23 controls on Manny_Rig1" + aa.CARRIED % "Main")

    def test_in_place_or_a_hand_card_selects_no_main(self):
        aa.select_objects(self.header, ["|x"], options={"in_place": True})
        self.header, self.frames = card(members=("hand_l",))
        aa.select_objects(self.header, ["|x"])
        self.assertEqual(self.world.entries("select"), [])

    def test_a_skeleton_s_root(self):
        aa._targets = lambda selection, prefer=None: ([self.skel], "")
        ok, text = aa.select_objects(self.header, [])
        self.assertEqual(self.world.entries("select"), [("select", [SKEL_ROOT], True)])
        self.assertTrue(text.endswith(aa.CARRIED % "root"), text)

    def test_an_objects_card_selects_its_objects(self):
        objects = loc_card()
        aa.select_objects(objects, ["|locB"])
        self.assertEqual(self.selected, [["|locB"]])


class FakePoseBlend(object):
    """`apply.Blend` as the animation Blend drives it."""

    log = None

    def __init__(self):
        self.alpha = 0.0
        self.on = False
        self.frame = None

    def start(self, data, mirror=False, selection=None):
        self.log.append(("start", data, mirror, selection))
        self.on = True
        return ""

    def set(self, alpha):
        self.alpha = alpha
        self.log.append(("set", alpha))

    def cancel(self):
        self.log.append(("cancel",))
        self.on = False

    def active(self):
        return self.on


class AnimBlend(Base):

    def setUp(self):
        Base.setUp(self)
        self.blend_log = []
        ap.Blend = type("Blend", (FakePoseBlend,), {"log": self.blend_log})
        self.pressed = []

        def press(header, frames, selection=None, mirror=False, alpha=1.0, options=None,
                  progress=None):
            self.pressed.append((selection, mirror, alpha, options, progress))
            return True, "pasted at %s" % alpha
        aa.apply = press

    def started(self):
        return [e for e in self.blend_log if e[0] == "start"]

    def test_the_preview_is_the_frame_that_falls_on_the_current_frame(self):
        blend = aa.Blend()
        self.assertEqual(blend.start(self.header, self.frames, selection=["|a"]), "")
        data = self.started()[0][1]
        self.assertEqual(index(data["bones"]), 0)           # at the current frame: the first
        self.assertEqual(data["members"], self.header["members"])
        self.assertTrue(blend.active())
        blend.cancel()
        self.world.frame = 3.0
        blend.start(self.header, self.frames, options={"at_current": False}, selection=[])
        self.assertEqual(index(self.started()[1][1]["bones"]), 3)
        blend.cancel()
        self.world.frame = 9.0                               # past the clip: the first
        blend.start(self.header, self.frames, options={"at_current": False}, selection=[])
        self.assertEqual(index(self.started()[2][1]["bones"]), 0)

    def test_finish_puts_the_preview_back_then_pastes_the_whole_range_at_its_weight(self):
        blend = aa.Blend()
        progress = Progress()
        blend.start(self.header, self.frames, mirror=True, options={"mode": "merge"},
                    selection=["|a"])
        blend.set(0.4)
        text = blend.finish(progress)
        self.assertEqual(text, "pasted at 0.4")
        self.assertEqual([e[0] for e in self.blend_log], ["start", "set", "cancel"])
        self.assertEqual(self.pressed, [(["|a"], True, 0.4,
                                         aa._options({"mode": "merge"}), progress)])
        self.assertFalse(blend.active())

    def test_finish_at_zero_and_after_the_time_moved_keys_nothing(self):
        blend = aa.Blend()
        blend.start(self.header, self.frames, selection=[])
        self.assertEqual(blend.finish(), ap.BLEND_ZERO)
        blend.start(self.header, self.frames, selection=[])
        blend.set(0.5)
        self.world.frame = 20.0
        self.assertEqual(blend.finish(), ap.TIME_MOVED)
        self.assertEqual(self.pressed, [])
        self.assertEqual(blend.finish(), ap.NO_BLEND)

    def test_the_selection_at_the_start_is_the_one_pasted_onto(self):
        self.world.selected = ["|Manny_Rig_Character|Manny_Rig1:FKWrist_L"]
        blend = aa.Blend()
        blend.start(self.header, self.frames)
        self.world.selected = []
        blend.set(1.0)
        blend.finish()
        self.assertEqual(self.pressed[0][0], ["|Manny_Rig_Character|Manny_Rig1:FKWrist_L"])

    def test_a_card_with_no_frames_starts_nothing(self):
        blend = aa.Blend()
        self.assertEqual(blend.start(self.header, None), aa.NO_FRAMES)
        self.assertFalse(blend.active())
        self.assertEqual(self.blend_log, [])

    def test_an_objects_card_previews_its_values_at_that_frame(self):
        blend = aa.Blend()
        self.world.frame = 10.0
        blend.start(loc_card(), None, options={"at_current": False}, selection=["|locB"])
        data = self.started()[0][1]
        self.assertEqual(data["kind"], "objects")
        self.assertEqual(data["objects"][0]["attrs"], {"translateX": 5.0, "visibility": 1.0})


if __name__ == "__main__":
    unittest.main()

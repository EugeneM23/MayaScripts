"""The Pose Library's Save of an ANIMATION (2026-10-03): the range a save takes, the source's key
times, a character's frames read in ONE time walk, objects' curves copied through a duplicate, and
the preview sheet.

The animator: «теперь давай добавим возможность сохранять анимации. Все правила которые работают
для поз должны работать и для анимаций». A character card is a pose card per frame: its bones'
STATIC half (parent, canonical, rest, rotate order) read once at the current frame, their worlds
(and a rig's drives) at every frame of the range in one `timewalk.Walk(fresh=False)`. An objects
card holds each selected transform's keyable channels as curves.

The scene runs on fakes rebound as module attributes (CLAUDE.md's rule) and restored after: one
fake `cmds` for `animcapture`, `capture` and `keys` (the save reuses `capture._common` and
`keys.feed_of`), and fake `scene`, `timewalk`, `_drive_matrices`, `_highlight`. The playblast half
of `preview` needs a viewport and is proven in the GUI verify; its refusals, the order of its steps
against a fake playblast, and the sheet's paint (Qt offscreen) are proven here.

Fix round 1: a Save is no step of the animator's undo queue (the walk and the blast run with the
queue off - `SaveIsNoUndoStep`, the undo half of `PreviewSteps`), and the blast's pieces are
`capture`'s, written once and called by the thumbnail and the preview alike (`SharedBlastPieces`,
`ThumbnailThroughThePieces`, `OneCopy`).

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("Save")
"""

import ast
import copy
import inspect
import math
import os
import shutil
import sys
import tempfile
import types
import unittest
from collections import OrderedDict

from maya_poselib import animcapture as ac
from maya_poselib import animdata
from maya_poselib import capture
from maya_poselib import keys
from maya_poselib import look
from maya_poselib import scene
from maya_poselib import store


def turned(degrees, x=0.0, y=0.0, z=0.0):
    """A flat world matrix turned `degrees` about Y, standing at (x, y, z)."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [c, 0.0, -s, 0.0, 0.0, 1.0, 0.0, 0.0, s, 0.0, c, 0.0, x, y, z, 1.0]


# ------------------------------------------------------------------ the fake scene

class FakeCurve(object):
    """A time curve: keys [t, v, in type, out type, in angle, in weight, out angle, out weight],
    linear between its keys and constant past them - enough for `setKeyframe -insert`."""

    def __init__(self, points, kind="animCurveTL", weighted=False, breakdown=(), tangents=None):
        self.kind = kind
        self.keys = []
        for index, (time, value) in enumerate(points):
            tangent = (tangents or {}).get(index, ("auto", "auto", 0.0, 1.0, 0.0, 1.0))
            self.keys.append([float(time), float(value)] + list(tangent))
        self.weighted = weighted
        self.breakdown = set(float(t) for t in breakdown)

    def value(self, time):
        if time <= self.keys[0][0]:
            return self.keys[0][1]
        if time >= self.keys[-1][0]:
            return self.keys[-1][1]
        for (t0, v0), (t1, v1) in zip(((k[0], k[1]) for k in self.keys),
                                      ((k[0], k[1]) for k in self.keys[1:])):
            if t0 <= time <= t1:
                return v0 + (v1 - v0) * (time - t0) / (t1 - t0)
        raise AssertionError(time)

    def insert(self, time):
        time = float(time)
        if any(abs(k[0] - time) < 1e-9 for k in self.keys):
            return 0                                        # measured: no key made there
        self.keys.append([time, self.value(time), "fixed", "fixed", 12.5, 1.0, 12.5, 1.0])
        self.keys.sort(key=lambda k: k[0])
        return 1

    def inside(self, span):
        if span is None:
            return list(self.keys)
        return [k for k in self.keys if span[0] <= k[0] <= span[1]]


class FakeCmds(object):
    """The `cmds` a save meets: plugs and their inputs, time curves, worlds that follow the
    current frame, a set's members, the undo state, autoKey, a model panel and its playblast.
    `touched` keeps (what, the undo state it ran under) of every call that changes the scene or
    the view - what a Save must do with the undo queue off."""

    _TANGENT = {"inTangentType": 2, "outTangentType": 3, "inAngle": 4, "inWeight": 5,
                "outAngle": 6, "outWeight": 7}

    def __init__(self):
        self.log = []
        self.frame = 12.0
        self.batch = True
        self.types = {}             # node -> its type
        self.keyable = {}           # node -> [its keyable attributes]
        self.inputs = {}            # node -> [(attribute on the node, source node)]
        self.curves = {}            # curve node -> FakeCurve
        self.values = {}            # plug -> a value, or f(time)
        self.worlds = {}            # joint path -> f(frame) -> 16 floats
        self.members = {}           # set -> [members]
        self.long = {}              # short name -> long path (`ls -long`)
        self.playback = (0.0, 47.0)
        self.undo = True
        self.copies = 0
        self.editor = {}            # model editor flag -> shown
        self.unknown = set()        # model editor flags this editor does not know (it raises)
        self.blasted = []           # every playblast's keywords
        self.skip_frames = set()    # frames the sequence playblast does not write
        self.colours = {}           # frame -> (r, g, b) the playblast paints
        self.auto = True            # autoKeyframe -state
        self.touched = []           # (what, the undo state it ran under)

    # ---- capture._common
    def file(self, query=False, sceneName=False):
        return "C:/shots/shot_010.ma"

    def currentTime(self, query=False):
        return self.frame

    def currentUnit(self, query=False, time=False):
        return "ntsc"

    def optionVar(self, exists=None, query=None):
        return False if exists else ""

    def about(self, batch=False):
        return self.batch

    def playbackOptions(self, query=False, minTime=False, maxTime=False):
        return self.playback[0] if minTime else self.playback[1]

    # ---- plugs
    def getAttr(self, plug, time=None):
        if plug.endswith(".worldMatrix[0]"):
            self.log.append(("world", plug[:-len(".worldMatrix[0]")], self.frame))
            return list(self.worlds[plug[:-len(".worldMatrix[0]")]](self.frame))
        value = self.values[plug]
        if callable(value):
            return value(self.frame if time is None else time)
        return value

    def nodeType(self, node):
        if node not in self.types:
            raise RuntimeError("No object matches name: " + node)
        return self.types[node]

    def objectType(self, node):
        return self.nodeType(node)

    def listAttr(self, node, keyable=False, scalar=False, unlocked=False):
        if node not in self.keyable:
            raise ValueError("No object matches name: " + node)
        return list(self.keyable[node])

    def listConnections(self, target, source=True, destination=True, connections=False,
                        plugs=False, skipConversionNodes=False):
        assert source and not destination, "a save reads inputs only"
        if "." in target:
            node, attr = target.split(".", 1)
            return [src for a, src in self.inputs.get(node, []) if a == attr] or None
        entries = self.inputs.get(target, [])
        if connections and plugs:
            out = []
            for attr, src in entries:
                out += [target + "." + attr, src + ".output"]
            return out or None
        out = []
        for _attr, src in entries:
            if src not in out:
                out.append(src)
        return out or None

    def connectionInfo(self, plug, isDestination=False, sourceFromDestination=False):
        return False                        # no compound parent is fed in these scenes

    # ---- curves
    def _span(self, time):
        return None if time is None else (float(time[0]), float(time[1]))

    def keyframe(self, curve, query=False, time=None, timeChange=False, valueChange=False,
                 breakdown=False):
        assert query, "a save never edits a curve"
        data = self.curves[curve]
        span = self._span(time)
        inside = data.inside(span)
        if breakdown:
            return sorted(t for t in data.breakdown
                          if span is None or span[0] <= t <= span[1]) or None
        if timeChange and valueChange:
            out = []
            for k in inside:
                out += [k[0], k[1]]
            return out or None
        if timeChange:
            return [k[0] for k in inside] or None
        raise AssertionError("keyframe asked for nothing")

    def keyTangent(self, curve, query=False, time=None, weightedTangents=False, **flags):
        assert query, "a save never edits a tangent"
        data = self.curves[curve]
        if weightedTangents:
            return [data.weighted]
        (flag,) = [name for name, on in flags.items() if on]
        return [k[self._TANGENT[flag]] for k in data.inside(self._span(time))] or None

    def duplicate(self, node):
        self.copies += 1
        name = "%s_copy%d" % (node, self.copies)
        self.curves[name] = copy.deepcopy(self.curves[node])
        self.types[name] = self.types[node]
        self.log.append(("duplicate", node, self.undo))
        return [name]

    def setKeyframe(self, target, insert=False, time=None, **kw):
        self.log.append(("setKeyframe", target, time, insert, self.undo))
        assert insert, "a save keys nothing"
        return self.curves[target].insert(time)

    def delete(self, nodes):
        for node in nodes if isinstance(nodes, (list, tuple)) else [nodes]:
            self.log.append(("delete", node, self.undo))
            self.curves.pop(node, None)
            self.types.pop(node, None)

    def undoInfo(self, query=False, state=False, stateWithoutFlush=None, **kw):
        if query:
            return self.undo
        if stateWithoutFlush is not None:
            self.undo = bool(stateWithoutFlush)
            self.log.append(("undo", self.undo))
            return None
        raise AssertionError("a save opens no undo chunk: %r" % kw)

    def autoKeyframe(self, query=False, state=None):
        """`autoKeyframe -q -state` / `-state v`: a toggle is a step of the undo queue in Maya
        (trap 145), so each one notes the undo state it ran under."""
        if query:
            return self.auto
        self.auto = bool(state)
        self.log.append(("autoKeyframe", self.auto))
        self.touched.append(("autoKeyframe", self.undo))
        return None

    # ---- sets
    def sets(self, name, query=False):
        return list(self.members.get(name, []))

    def ls(self, items, long=False):
        return [self.long.get(item, item) for item in items]

    # ---- the preview's viewport
    def modelEditor(self, panel, query=False, edit=False, **flags):
        (flag, value), = flags.items()
        if flag in self.unknown:
            raise RuntimeError("Invalid flag '%s'" % flag)
        if query:
            return self.editor.get(flag, True)
        self.editor[flag] = value
        self.log.append(("editor", flag, value))
        self.touched.append(("editor", self.undo))
        return None

    def refresh(self, force=False, **kw):
        self.log.append(("refresh",))
        self.touched.append(("refresh", self.undo))

    def playblast(self, **kw):
        self.blasted.append(kw)
        self.log.append(("playblast", tuple(kw["frame"]), "completeFilename" in kw))
        self.touched.append(("playblast", self.undo))
        import maya_hubqt
        qt = maya_hubqt.qt()
        width, height = kw["widthHeight"]
        if "completeFilename" in kw:
            targets = [(kw["frame"][0], kw["completeFilename"])]
        else:
            targets = [(f, "%s.%04d.jpg" % (kw["filename"], f)) for f in kw["frame"]
                       if f not in self.skip_frames]
        for frame, path in targets:
            image = qt.QtGui.QImage(width, height, qt.QtGui.QImage.Format_RGB32)
            image.fill(qt.QtGui.QColor(*self.colours.get(frame, (90, 90, 90))))
            assert image.save(path, "JPG", 95), path
        return kw.get("completeFilename") or kw["filename"] + ".####.jpg"


class FakeWalk(object):
    """timewalk.Walk: `go` moves the fake scene's frame; entering and leaving are logged, and
    leaving puts the frame back. `thrown`: the walk threw an unkeyed tweak away, so leaving sets
    it back as `keys.Tweaks.restore` does - autoKey turned off and back, two steps on the undo
    queue unless it is off. Each step notes the undo state it ran under (`cmds.touched`)."""

    def __init__(self, cmds, fresh, thrown=False):
        self.cmds, self.fresh, self.thrown = cmds, fresh, thrown
        self.keyed = []

    def __enter__(self):
        self.here = self.cmds.frame
        self.cmds.log.append(("walk enter", self.fresh))
        self.cmds.touched.append(("walk enter", self.cmds.undo))
        return self

    def go(self, frame):
        self.cmds.log.append(("go", frame))
        self.cmds.touched.append(("go", self.cmds.undo))
        self.cmds.frame = frame

    def __exit__(self, kind, error, trace):
        self.cmds.frame = self.here
        if self.thrown:
            auto = self.cmds.autoKeyframe(query=True, state=True)
            self.cmds.autoKeyframe(state=False)
            self.cmds.autoKeyframe(state=auto)
        self.cmds.touched.append(("walk exit", self.cmds.undo))
        self.cmds.log.append(("walk exit",))
        return False


class FakeTimewalk(object):
    def __init__(self, cmds):
        self.walks = []
        self.thrown = False             # the walks made from now on throw a tweak away

        def walk(fresh=True):
            made = FakeWalk(cmds, fresh, self.thrown)
            self.walks.append(made)
            return made
        self.Walk = walk


class FakeScene(object):
    """The parts of `scene` a save asks: which characters a selection names, the skeleton
    (logged with the frame it was read at), the members; `describe`, `leaf` and `regions_of` are
    the real, pure ones."""

    describe = staticmethod(scene.describe)
    leaf = staticmethod(scene.leaf)
    regions_of = staticmethod(scene.regions_of)
    NOTHING = scene.NOTHING

    def __init__(self, cmds, resolved, bones=None, members=None):
        self.cmds, self.resolved, self.bones, self.members = cmds, resolved, bones, members

    def resolve(self, selection=None):
        self.cmds.log.append(("resolve", selection))
        return list(self.resolved)

    def skeleton(self, ref, notes=None):
        self.cmds.log.append(("skeleton", ref.root, self.cmds.frame))
        return copy.deepcopy(self.bones), "unreal_ue5"

    def members_of(self, ref, nodes, bones=None):
        if self.members is not None:
            return list(self.members)
        return [name for name in bones if name != "root"]

    def identity(self, ref, convention=None):
        return {"key": ref.key, "model": ref.model, "kind": ref.kind, "label": ref.label,
                "namespace": ref.namespace, "root": scene.leaf(ref.root),
                "convention": convention, "rotation_only": False}

    def dag_object(self, item):
        return item


class FakeProgress(object):
    """timewalk.Progress: each step's text kept; answers True, or what `answers` says."""

    def __init__(self, answers=()):
        self.answers = list(answers)
        self.texts = []

    def step(self, text=""):
        self.texts.append(text)
        return self.answers.pop(0) if self.answers else True


BONES = ["root", "pelvis", "spine_01"]
TOP = "|Manny_Skeleton_Character|root"
PATHS = {"root": TOP, "pelvis": TOP + "|pelvis", "spine_01": TOP + "|pelvis|spine_01"}
SKELETON = scene.CharacterRef("skeleton", TOP, None, "Manny UE5 [skeleton]", "Manny", "Manny",
                              "")


def skeleton_bones():
    """`scene.skeleton`'s answer for a three-bone UE skeleton, its world the frame's own."""
    out, parent = {}, None
    for index, name in enumerate(BONES):
        out[name] = {"path": PATHS[name], "parent": parent, "canonical": name,
                     "rest": turned(0.0, 0.0, 10.0 * index), "world": turned(99.0),
                     "rotateOrder": index, "jointOrient": [0.0, 0.0, 0.0],
                     "rotateAxis": [0.0, 0.0, 0.0]}
        parent = name
    return out


def world_of(index):
    """The fake world of bone `index` at a frame: turned with it and moving."""
    return lambda frame: turned(10.0 * frame + 7.0 * index, float(index), 2.0 * frame,
                                -3.0 * index * frame)


class Rebound(unittest.TestCase):
    """One FakeCmds as `cmds` in animcapture, capture and keys; `scene`, `timewalk` and the seams
    replaced per test; every one put back after."""

    def setUp(self):
        self.cmds = FakeCmds()
        self.log = self.cmds.log
        saved = [(ac, name, getattr(ac, name)) for name in
                 ("cmds", "scene", "timewalk", "keys", "oma", "_drive_matrices",
                  "_highlight", "_panel", "_qt")]
        saved += [(capture, "cmds", capture.cmds), (keys, "cmds", keys.cmds),
                  (capture, "_port", capture._port)]
        self.addCleanup(lambda: [setattr(module, name, value) for module, name, value in saved])
        ac.cmds = capture.cmds = keys.cmds = self.cmds
        self.timewalk = FakeTimewalk(self.cmds)
        ac.timewalk = self.timewalk
        ac._highlight = lambda: None

    def rebind(self, owner, name, value):
        """`owner.name` = `value` for this test, put back after - deleted when it was not
        there (a module function the code under test may not have yet)."""
        missing = object()
        old = getattr(owner, name, missing)

        def back():
            if old is missing:
                if hasattr(owner, name):
                    delattr(owner, name)
            else:
                setattr(owner, name, old)
        self.addCleanup(back)
        setattr(owner, name, value)

    def rebind_module(self, name, module):
        """`sys.modules[name]` = `module` for this test (an `import name` inside the code then
        finds it), put back after."""
        missing = object()
        old = sys.modules.get(name, missing)

        def back():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        self.addCleanup(back)
        sys.modules[name] = module

    def character(self, ref=SKELETON, members=None, selection=None):
        """The scene holds one three-bone character `ref`, the selection one of its bones."""
        for index, name in enumerate(BONES):
            self.cmds.worlds[PATHS[name]] = world_of(index)
            self.cmds.keyable[PATHS[name]] = ["translateX", "rotateX"]
        selection = selection or [PATHS["pelvis"]]
        ac.scene = FakeScene(self.cmds, [(path, ref) for path in selection], skeleton_bones(),
                             members)

    def curve(self, name, points, kind="animCurveTL", **kw):
        self.cmds.curves[name] = FakeCurve(points, kind, **kw)
        self.cmds.types[name] = kind
        return name

    def feed(self, node, attr, source):
        self.cmds.inputs.setdefault(node, []).append((attr, source))


# ------------------------------------------------------------------ the range

class WholeFrames(unittest.TestCase):

    def test_the_same_half_up_rule_as_animdata(self):
        # a save's frames and a paste's must round alike: `_whole` is animdata's `_frame` rule
        for value in (12.5, 13.5, -0.5, -1.5, 2.4999999, 0.4, 47.0, -3.6, 1e4 + 0.5):
            self.assertEqual(ac._whole(value), animdata._frame(value), value)
            self.assertIsInstance(ac._whole(value), int)


class DefaultRange(Rebound):

    # the module's own `_highlight`, kept here: `Rebound.setUp` replaces it with a quiet slider
    real_highlight = staticmethod(ac._highlight)

    def test_a_highlight_wins_its_frames_whole(self):
        # the slider answers [start, end + 1): a highlight over frames 10..20
        ac._highlight = lambda: (10.0, 21.0)
        self.assertEqual(ac.default_range(), (10, 20))

    def test_a_single_frame_highlight_is_the_playback_range(self):
        self.cmds.playback = (0.0, 47.0)
        ac._highlight = lambda: (12.0, 13.0)
        self.assertEqual(ac.default_range(), (0, 47))

    def test_no_highlight_is_the_playback_range_in_whole_frames(self):
        self.cmds.playback = (1.0, 120.0)
        self.assertEqual(ac.default_range(), (1, 120))
        self.cmds.playback = (0.5, 47.4)                    # half up, as animdata rounds
        self.assertEqual(ac.default_range(), (1, 47))
        for value in ac.default_range():
            self.assertIsInstance(value, int)

    def test_the_slider_read_through_overrig(self):
        # the real `overrig.slider_selection` on a fake slider: a one-frame highlight (the slider
        # answers [12, 13)) is no highlight, a dragged one is, a hidden one is not
        from maya_overrig import overrig
        saved = (overrig.cmds, overrig.mel)
        self.addCleanup(lambda: (setattr(overrig, "cmds", saved[0]),
                                 setattr(overrig, "mel", saved[1])))
        slider = {"visible": True, "range": [12.0, 13.0]}

        class Slider(object):
            @staticmethod
            def timeControl(name, query=False, rangeVisible=False, rangeArray=False):
                assert name == "timeControl1"
                return slider["visible"] if rangeVisible else list(slider["range"])
        overrig.cmds = Slider()
        overrig.mel = types.SimpleNamespace(eval=lambda text: "timeControl1")
        ac._highlight = self.real_highlight
        self.cmds.playback = (0.0, 30.0)
        self.assertEqual(ac.default_range(), (0, 30))
        slider["range"] = [10.0, 21.0]
        self.assertEqual(ac.default_range(), (10, 20))
        slider["visible"] = False
        self.assertEqual(ac.default_range(), (0, 30))

    def test_a_slider_that_cannot_be_read_is_the_playback_range(self):
        def broken():
            raise RuntimeError("no slider in batch")
        from maya_overrig import overrig
        saved = overrig.slider_selection
        self.addCleanup(setattr, overrig, "slider_selection", saved)
        overrig.slider_selection = broken
        ac._highlight = self.real_highlight
        self.assertEqual(ac.default_range(), (0, 47))


# ------------------------------------------------------------------ the key times

class KeyTimes(Rebound):

    def test_two_curves_inside_the_range_rounded_and_the_ends_in(self):
        self.cmds.keyable["|a"] = ["translateX", "translateY"]
        self.feed("|a", "translateX", self.curve("a_tx", [(0, 0), (4.4, 1), (30, 2)]))
        self.feed("|a", "translateY", self.curve("a_ty", [(12, 5)]))
        self.assertEqual(ac.key_times(["|a"], 0, 20), [0, 4, 12, 20])

    def test_whole_frames_as_floats_for_the_header(self):
        self.cmds.keyable["|a"] = ["translateX"]
        self.feed("|a", "translateX", self.curve("a_tx", [(3, 0)]))
        times = ac.key_times(["|a"], 0, 10)
        self.assertEqual(times, [0.0, 3.0, 10.0])
        for time in times:
            self.assertIsInstance(time, float)

    def test_a_layered_channel_reaches_both_its_curves(self):
        # a layer's blend node holds the base curve as inputA and the layer's as inputB; its
        # weights come from the animLayer, which is no curve
        self.cmds.keyable["|b"] = ["translateY"]
        self.cmds.types["blend1"] = "animBlendNodeAdditiveDL"
        self.cmds.types["AnimLayer1"] = "animLayer"
        self.feed("|b", "translateY", "blend1")
        self.feed("blend1", "inputA", self.curve("b_ty", [(3, 0)]))
        self.feed("blend1", "inputB", self.curve("b_ty_L1", [(7.6, 1)]))
        self.feed("blend1", "weightA", "AnimLayer1")
        self.feed("blend1", "weightB", "AnimLayer1")
        self.assertEqual(ac.key_times(["|b"], 0, 20), [0, 3, 8, 20])

    def test_stacked_layers_are_walked_through_every_blend(self):
        self.cmds.keyable["|b"] = ["rotateX"]
        self.cmds.types["blend1"] = "animBlendNodeAdditiveDA"
        self.cmds.types["blend2"] = "animBlendNodeAdditiveDA"
        self.feed("|b", "rotateX", "blend2")
        self.feed("blend2", "inputA", "blend1")
        self.feed("blend2", "inputB", self.curve("b_rx_L2", [(15, 0)], "animCurveTA"))
        self.feed("blend1", "inputA", self.curve("b_rx", [(2, 0)], "animCurveTA"))
        self.feed("blend1", "inputB", self.curve("b_rx_L1", [(9, 0)], "animCurveTA"))
        self.assertEqual(ac.key_times(["|b"], 0, 20), [0, 2, 9, 15, 20])

    def test_a_quaternion_layer_blend_reads_its_curves_not_the_node_it_turns(self):
        # measured: animBlendNodeAdditiveRotation takes the node's own rotateOrder as an input
        self.cmds.keyable["|c"] = ["rotateX"]
        self.cmds.types["|c"] = "transform"
        self.cmds.types["rot1"] = "animBlendNodeAdditiveRotation"
        self.feed("|c", "rotateX", "rot1")
        self.feed("rot1", "inputAX", self.curve("c_rx", [(4, 0)], "animCurveTA"))
        self.feed("rot1", "rotateOrder", "|c")
        self.assertEqual(ac.key_times(["|c"], 0, 10), [0, 4, 10])

    def test_driven_keys_and_unkeyable_channels_are_no_key_times(self):
        self.cmds.keyable["|d"] = ["translateZ"]
        self.feed("|d", "translateZ", self.curve("d_tz_driven", [(6, 0)], "animCurveUL"))
        self.feed("|d", "lockedThing", self.curve("d_locked", [(7, 0)]))
        self.assertEqual(ac.key_times(["|d"], 0, 10), [0, 10])

    def test_keys_outside_the_range_stay_out_and_a_half_rounds_up(self):
        self.cmds.keyable["|e"] = ["translateX"]
        self.feed("|e", "translateX", self.curve("e_tx", [(-0.6, 0), (12.5, 1), (19.6, 2),
                                                         (20.6, 3)]))
        self.assertEqual(ac.key_times(["|e"], 0, 20), [0, 13, 20])

    def test_a_curve_feeding_two_nodes_counts_once_and_missing_nodes_add_nothing(self):
        self.cmds.keyable["|f"] = ["translateX"]
        self.cmds.keyable["|g"] = ["translateX"]
        shared = self.curve("shared", [(5, 0)])
        self.feed("|f", "translateX", shared)
        self.feed("|g", "translateX", shared)
        self.assertEqual(ac.key_times(["|f", "|g", "|gone"], 0, 9), [0, 5, 9])

    def test_the_ends_alone_with_no_curve_and_one_frame(self):
        self.cmds.keyable["|h"] = ["translateX"]
        self.assertEqual(ac.key_times(["|h"], 5, 9), [5, 9])
        self.assertEqual(ac.key_times(["|h"], 5, 5), [5])
        self.assertEqual(ac.key_times([], 3.4, 6.5), [3, 7])


# ------------------------------------------------------------------ a character card

class CharacterCard(Rebound):

    def test_three_frames_of_three_bones_in_one_walk(self):
        self.character()
        header, frames, note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(header["frames"], 3)
        self.assertEqual(frames["bones"], BONES)
        self.assertEqual(len(frames["world"]), 3)
        for frame in range(3):
            row = frames["world"][frame]
            self.assertEqual(len(row), 7 * len(BONES))
            for index in range(len(BONES)):
                got = animdata.decode(row[7 * index:7 * index + 7])
                for a, b in zip(got, world_of(index)(frame)):
                    self.assertAlmostEqual(a, b, places=6)
        self.assertEqual(frames["drive"], {})
        self.assertIs(header["rig_source"], False)
        self.assertEqual([walk.fresh for walk in self.timewalk.walks], [False])
        self.assertEqual([entry for entry in self.log if entry[0] == "go"],
                         [("go", 0), ("go", 1), ("go", 2)])
        self.assertEqual(self.cmds.frame, 12.0)                   # the walk put the time back

    def test_every_frame_reads_every_bone_at_that_frame(self):
        self.character()
        ac.build_animation([PATHS["pelvis"]], start=4, end=5)
        reads = [entry for entry in self.log if entry[0] == "world"]
        self.assertEqual(reads, [("world", PATHS[name], frame) for frame in (4, 5)
                                 for name in BONES])

    def test_the_static_half_is_read_at_the_current_frame_before_the_walk(self):
        self.character()
        ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        read = self.log.index(("skeleton", TOP, 12.0))
        self.assertLess(read, self.log.index(("walk enter", False)))

    def test_the_header_holds_the_static_half_only(self):
        self.character()
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(list(header["bones"]), BONES)
        bones = skeleton_bones()
        for name, bone in header["bones"].items():
            self.assertEqual(sorted(bone), ["canonical", "parent", "rest", "rotateOrder"])
            for field in ("parent", "canonical", "rest", "rotateOrder"):
                self.assertEqual(bone[field], bones[name][field])

    def test_the_header_fields(self):
        self.character()
        self.feed(PATHS["pelvis"], "translateX", self.curve("pelvis_tx", [(1, 0), (30, 1)]))
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(header["format"], store.ANIM_FORMAT)
        self.assertEqual(header["version"], store.VERSION)
        self.assertEqual(header["kind"], "character")
        self.assertEqual(header["name"], "Anim")
        self.assertNotIn("frame", header)
        self.assertEqual(header["scene"], "shot_010.ma")
        self.assertEqual(header["fps"], "ntsc")
        self.assertTrue(header["author"])
        self.assertTrue(header["created"])
        self.assertEqual((header["start"], header["end"], header["frames"]), (0.0, 2.0, 3))
        self.assertIsInstance(header["start"], float)
        self.assertEqual(header["key_times"], [0.0, 1.0, 2.0])     # the joints' own keys
        self.assertEqual(header["members"], ["pelvis", "spine_01"])
        self.assertEqual(header["regions"], ["Spine", "Pelvis"])
        self.assertEqual(header["character"]["label"], "Manny UE5 [skeleton]")
        self.assertEqual(header["character"]["convention"], "unreal_ue5")
        self.assertEqual(header["objects"], [])

    def test_the_note(self):
        self.character()
        _header, _frames, note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(note, "Manny UE5 [skeleton] (root): 3 frames (0-2), 2 of 3 bones - "
                               "Spine, Pelvis")
        _header, _frames, note = ac.build_animation([PATHS["pelvis"]], start=5, end=5)
        self.assertTrue(note.startswith("Manny UE5 [skeleton] (root): 1 frame (5), "), note)

    def test_the_regions_narrow_the_members_as_for_a_pose(self):
        self.character()
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], regions=["Pelvis"],
                                                    start=0, end=1)
        self.assertEqual(header["members"], ["pelvis"])
        self.assertEqual(header["regions"], ["Pelvis"])

    def test_no_member_left_is_refused_before_the_walk(self):
        self.character()
        header, frames, note = ac.build_animation([PATHS["pelvis"]], regions=["Hand L"],
                                                  start=0, end=2)
        self.assertEqual((header, frames), (None, None))
        self.assertEqual(note, "no bone of Hand L in the animation of Manny UE5 [skeleton]")
        self.assertEqual(self.timewalk.walks, [])

    def test_the_range_defaults_to_default_range_and_is_made_whole_once(self):
        self.character()
        ac._highlight = lambda: (10.0, 13.0)
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]])
        self.assertEqual((header["start"], header["end"], header["frames"]), (10.0, 12.0, 3))
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=0.4, end=2.5)
        self.assertEqual((header["start"], header["end"], header["frames"]), (0.0, 3.0, 4))
        gos = [entry[1] for entry in self.log if entry[0] == "go"]
        self.assertEqual(gos[-4:], [0, 1, 2, 3])
        for frame in gos:
            self.assertIsInstance(frame, int)
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=5)
        self.assertEqual((header["start"], header["end"]), (5.0, 12.0))     # the end defaulted

    def test_an_empty_range_is_refused_before_anything_is_read(self):
        self.character()
        self.assertEqual(ac.build_animation([PATHS["pelvis"]], start=5, end=2),
                         (None, None, "the range 5-2 holds no frame"))
        self.assertEqual(self.timewalk.walks, [])
        self.assertNotIn("resolve", [entry[0] for entry in self.log])

    def test_a_step_per_frame_and_a_cancel_saves_nothing(self):
        self.character()
        progress = FakeProgress()
        ac.build_animation([PATHS["pelvis"]], start=0, end=2, progress=progress)
        self.assertEqual(len(progress.texts), 3)
        self.log[:] = []
        progress = FakeProgress([True, False])
        self.assertEqual(ac.build_animation([PATHS["pelvis"]], start=0, end=5,
                                            progress=progress),
                         (None, None, "cancelled - nothing saved"))
        self.assertEqual(len(progress.texts), 2)
        self.assertEqual([entry for entry in self.log if entry[0] == "go"],
                         [("go", 0), ("go", 1)])
        self.assertEqual(self.log[-2:], [("walk exit",), ("undo", True)])   # left, queue back
        self.assertEqual(self.cmds.frame, 12.0)

    def test_a_rig_keeps_its_drives_every_frame_and_its_controls_key_times(self):
        rig = types.SimpleNamespace(namespace="Manny_Rig", control_set="Manny_Rig:ControlSet")
        ref = scene.CharacterRef("rig", TOP, rig, "Manny [rig]", "Manny_Rig", "Manny",
                                 "Manny_Rig")
        self.character(ref)
        asked = []

        def drives(given):
            self.assertIs(given, rig)
            asked.append(self.cmds.frame)
            return {"pelvis": turned(30.0 * self.cmds.frame, 0.0, 1.0, 2.0),
                    "not_a_bone": turned(5.0)}
        ac._drive_matrices = drives
        self.cmds.members["Manny_Rig:ControlSet"] = ["Manny_Rig:Main", "Manny_Rig:FKSpine1_M"]
        self.cmds.long = {"Manny_Rig:Main": "|Manny_Rig:Group|Manny_Rig:Main",
                          "Manny_Rig:FKSpine1_M": "|Manny_Rig:Group|Manny_Rig:FKSpine1_M"}
        self.cmds.keyable["|Manny_Rig:Group|Manny_Rig:Main"] = ["translateZ"]
        self.cmds.keyable["|Manny_Rig:Group|Manny_Rig:FKSpine1_M"] = ["rotateX"]
        self.feed("|Manny_Rig:Group|Manny_Rig:FKSpine1_M", "rotateX",
                  self.curve("spine_rx", [(1, 0)], "animCurveTA"))
        # a game bone's keys (a helper's bake) are no key times of a rig: its controls' are
        self.feed(PATHS["spine_01"], "translateX", self.curve("bone_tx", [(2, 0)]))
        header, frames, note = ac.build_animation([PATHS["pelvis"]], start=0, end=3)
        self.assertIs(header["rig_source"], True)
        self.assertEqual(sorted(frames["drive"]), ["pelvis"])
        self.assertEqual(asked, [0, 1, 2, 3])
        self.assertEqual(len(frames["drive"]["pelvis"]), 4)
        for frame, q7 in enumerate(frames["drive"]["pelvis"]):
            for a, b in zip(animdata.decode(q7), turned(30.0 * frame, 0.0, 1.0, 2.0)):
                self.assertAlmostEqual(a, b, places=6)
        self.assertEqual(header["key_times"], [0.0, 1.0, 3.0])
        self.assertTrue(note.startswith("Manny [rig] (Manny_Rig): 4 frames (0-3)"), note)

    def test_a_rig_with_no_control_keys_has_the_ends_only(self):
        rig = types.SimpleNamespace(namespace="Manny_Rig", control_set="Manny_Rig:ControlSet")
        ref = scene.CharacterRef("rig", TOP, rig, "Manny [rig]", "Manny_Rig", "Manny",
                                 "Manny_Rig")
        self.character(ref)
        ac._drive_matrices = lambda given: {}
        self.feed(PATHS["pelvis"], "translateX", self.curve("bone_tx", [(1, 0)]))
        header, frames, _note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(header["key_times"], [0.0, 2.0])
        self.assertEqual(frames["drive"], {})
        self.assertIs(header["rig_source"], False)

    def test_two_characters_or_nothing_are_refused(self):
        other = SKELETON._replace(root="|Other_Character|root")
        self.character()
        ac.scene.resolved = [(PATHS["pelvis"], SKELETON), ("|Other_Character|root", other)]
        self.assertEqual(ac.build_animation(start=0, end=2),
                         (None, None, "pick one character for an animation"))
        ac.scene.resolved = []
        self.assertEqual(ac.build_animation(start=0, end=2),
                         (None, None, "select a character or objects"))
        self.assertEqual(self.timewalk.walks, [])

    def test_objects_beside_the_character_are_left_out_and_said(self):
        self.character()
        ac.scene.resolved = [(PATHS["pelvis"], SKELETON), ("|grp|pCube1", None)]
        header, _frames, note = ac.build_animation(start=0, end=2)
        self.assertEqual(header["kind"], "character")
        self.assertEqual(header["objects"], [])
        self.assertTrue(note.endswith(" | 1 object outside Manny UE5 [skeleton] left out"),
                        note)


class SaveIsNoUndoStep(Rebound):
    """A Save runs outside any undo chunk (`_unrecorded`'s docstring), so whatever it toggles
    on the way is a step of the animator's undo queue unless the queue is off. The walk's exit
    sets the tweaks back (`keys.Tweaks.restore`), turning autoKey off and back - measured in
    mayapy 2027 (fix round 1): a locator's tx keyed 0/10, set to 99 by hand at frame 0, then
    autoKey turned on; after the Save's walk the animator's first Ctrl+Z switched autoKey OFF,
    the second back ON, and their setAttr was never reached. The walk runs with the queue off
    and puts it back as it was, whatever ends it."""

    def test_the_walk_runs_with_the_undo_queue_off(self):
        self.character()
        self.timewalk.thrown = True
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertIsNotNone(header)
        self.assertEqual([kind for kind, _undo in self.cmds.touched],
                         ["walk enter", "go", "go", "go", "autoKeyframe", "autoKeyframe",
                          "walk exit"])
        self.assertEqual(set(undo for _kind, undo in self.cmds.touched), set([False]))
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"],
                         [("undo", False), ("undo", True)])
        self.assertLess(self.log.index(("undo", False)), self.log.index(("walk enter", False)))
        self.assertGreater(self.log.index(("undo", True)), self.log.index(("walk exit",)))
        self.assertIs(self.cmds.undo, True)
        self.assertIs(self.cmds.auto, True)                 # the toggles end where they began

    def test_a_cancelled_walk_puts_the_queue_back_on(self):
        self.character()
        self.timewalk.thrown = True
        progress = FakeProgress([True, False])
        self.assertEqual(ac.build_animation([PATHS["pelvis"]], start=0, end=5,
                                            progress=progress),
                         (None, None, "cancelled - nothing saved"))
        self.assertEqual(set(undo for _kind, undo in self.cmds.touched), set([False]))
        self.assertEqual(self.log[-2:], [("walk exit",), ("undo", True)])
        self.assertIs(self.cmds.undo, True)

    def test_a_walk_that_fails_puts_the_queue_back_on(self):
        self.character()
        self.timewalk.thrown = True

        def broken(frame):
            raise RuntimeError("no world at %s" % frame)
        self.cmds.worlds[PATHS["spine_01"]] = broken
        with self.assertRaises(RuntimeError):
            ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertEqual(set(undo for _kind, undo in self.cmds.touched), set([False]))
        self.assertEqual(self.log[-2:], [("walk exit",), ("undo", True)])
        self.assertIs(self.cmds.undo, True)

    def test_a_queue_already_off_is_left_off_by_the_walk(self):
        self.character()
        self.cmds.undo = False
        header, _frames, _note = ac.build_animation([PATHS["pelvis"]], start=0, end=2)
        self.assertIsNotNone(header)
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"], [])
        self.assertIs(self.cmds.undo, False)


# ------------------------------------------------------------------ objects

class ObjectCurves(Rebound):

    def cube(self):
        """|grp|pCube1: tx keyed 0/0 and 10/5, a static visibility, ty in an animation layer."""
        node = "|grp|pCube1"
        self.cmds.keyable[node] = ["translateX", "visibility", "translateY"]
        self.cmds.types["blend1"] = "animBlendNodeAdditiveDL"
        self.feed(node, "translateX", self.curve("pCube1_translateX", [(0, 0), (10, 5)]))
        self.feed(node, "translateY", "blend1")
        self.cmds.values[node + ".visibility"] = True
        self.cmds.values[node + ".translateY"] = lambda time: 2.0 * time + 1.0
        ac.scene = FakeScene(self.cmds, [(node, None)])
        return node

    def test_the_curve_shapes(self):
        node = self.cube()
        (record,) = ac.object_curves([node], 0, 10)
        self.assertEqual((record["name"], record["path"]), ("pCube1", node))
        self.assertEqual(record["attrs"]["translateX"],
                         {"keys": [[0.0, 0.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
                                   [10.0, 5.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0]],
                          "weighted": False, "breakdown": []})
        self.assertEqual(record["attrs"]["visibility"], {"static": 1.0})
        sampled = record["attrs"]["translateY"]
        self.assertEqual([k[0] for k in sampled["keys"]], [float(t) for t in range(11)])
        self.assertEqual([k[1] for k in sampled["keys"]], [2.0 * t + 1.0 for t in range(11)])
        self.assertEqual(set((k[2], k[3]) for k in sampled["keys"]), set([("spline", "spline")]))
        for key in sampled["keys"]:
            self.assertEqual(len(key), 8)
        self.assertEqual((sampled["weighted"], sampled["breakdown"]), (False, []))
        self.assertEqual(list(record["attrs"]), ["translateX", "visibility", "translateY"])

    def test_a_shape_keeping_key_at_each_end_and_nothing_outside(self):
        node = self.cube()
        (record,) = ac.object_curves([node], 2, 8)
        keys_ = record["attrs"]["translateX"]["keys"]
        self.assertEqual([k[:4] for k in keys_], [[2.0, 1.0, "fixed", "fixed"],
                                                  [8.0, 4.0, "fixed", "fixed"]])
        (record,) = ac.object_curves([node], 0, 20)                 # past the last key
        self.assertEqual([k[:2] for k in record["attrs"]["translateX"]["keys"]],
                         [[0.0, 0.0], [10.0, 5.0], [20.0, 5.0]])

    def test_tangents_weights_and_breakdowns_travel(self):
        node = "|grp|loc"
        self.cmds.keyable[node] = ["rotateX"]
        self.feed(node, "rotateX", self.curve(
            "loc_rx", [(0, 0), (5, 3), (10, 9)], "animCurveTA", weighted=True, breakdown=[5],
            tangents={1: ("fixed", "linear", 30.0, 2.5, -20.0, 7.0)}))
        ac.scene = FakeScene(self.cmds, [])
        (record,) = ac.object_curves([node], 0, 10)
        curve = record["attrs"]["rotateX"]
        self.assertEqual(curve["keys"][1], [5.0, 3.0, "fixed", "linear", 30.0, 2.5, -20.0, 7.0])
        self.assertIs(curve["weighted"], True)
        self.assertEqual(curve["breakdown"], [5.0])

    def test_read_off_a_duplicate_unrecorded_the_scenes_curve_untouched(self):
        node = self.cube()
        before = copy.deepcopy(self.cmds.curves["pCube1_translateX"].keys)
        ac.object_curves([node], 2, 8)
        self.assertEqual(self.cmds.curves["pCube1_translateX"].keys, before)
        edits = [entry for entry in self.log if entry[0] in ("duplicate", "setKeyframe",
                                                               "delete")]
        self.assertEqual([entry[0] for entry in edits],
                         ["duplicate", "setKeyframe", "setKeyframe", "delete"])
        copy_name = edits[-1][1]
        self.assertNotEqual(copy_name, "pCube1_translateX")
        self.assertEqual([entry[1] for entry in edits[1:3]], [copy_name, copy_name])
        self.assertEqual([entry[2] for entry in edits[1:3]], [2, 8])
        self.assertEqual(set(entry[-1] for entry in edits), set([False]))    # undo off
        self.assertNotIn(copy_name, self.cmds.curves)
        self.assertIs(self.cmds.undo, True)                                  # and back on
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"],
                         [("undo", False), ("undo", True)])

    def test_the_duplicate_goes_even_when_a_read_fails(self):
        node = self.cube()

        def broken(*args, **kw):
            raise RuntimeError("keyTangent failed")
        self.cmds.keyTangent = broken
        (record,) = ac.object_curves([node], 0, 10)
        self.assertNotIn("translateX", record["attrs"])         # that channel left out ...
        self.assertEqual(record["attrs"]["visibility"], {"static": 1.0})   # ... the rest kept
        self.assertEqual(sorted(self.cmds.curves), ["pCube1_translateX"])
        self.assertIs(self.cmds.undo, True)

    def test_an_undo_queue_already_off_is_left_off(self):
        node = self.cube()
        self.cmds.undo = False
        ac.object_curves([node], 0, 10)
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"], [])

    def test_one_record_per_object_and_odd_values_left_out(self):
        node = self.cube()
        self.cmds.keyable[node].append("label")
        self.cmds.values[node + ".label"] = "text"
        records = ac.object_curves([node, node, "|nothing"], 0, 10)
        self.assertEqual([r["path"] for r in records], [node, "|nothing"])
        self.assertNotIn("label", records[0]["attrs"])

    def test_an_objects_card(self):
        node = self.cube()
        header, frames, note = ac.build_animation(start=0, end=10)
        self.assertIsNone(frames)
        self.assertEqual(header["kind"], "objects")
        self.assertEqual(header["format"], store.ANIM_FORMAT)
        self.assertEqual(header["name"], "Anim")
        self.assertNotIn("frame", header)
        self.assertEqual((header["start"], header["end"], header["frames"]), (0.0, 10.0, 11))
        self.assertEqual([o["path"] for o in header["objects"]], [node])
        self.assertEqual(note, "1 object: 11 frames (0-10)")
        # its layered ty is sampled: one read-only walk (no evaluation switch)
        self.assertEqual([walk.fresh for walk in self.timewalk.walks], [False])

    # task 10's verify (2026-10-08, mayapy 2027): a fed channel read frame after frame with
    # `getAttr(time=)` - a locator parent-constrained to Manny_Rig's IK hand - answered 1.25e-4
    # cm off the scene at frame 10, and trap 69 saw such a read not pull a constraint riding an
    # IK chain at all in a GUI Maya. Every fed channel is read in ONE walk, after a real time
    # change.

    def test_a_fed_channel_is_read_after_a_real_time_change_never_in_a_time_context(self):
        node = self.cube()
        real = self.cmds.getAttr

        def stale(plug, time=None):
            # trap 69: a context read that does not pull the chain answers the frame shown
            return real(plug)
        self.cmds.getAttr = stale
        self.cmds.frame = 4
        (record,) = ac.object_curves([node], 0, 10)
        self.assertEqual([k[1] for k in record["attrs"]["translateY"]["keys"]],
                         [2.0 * t + 1.0 for t in range(11)])
        self.assertEqual(self.cmds.frame, 4)                      # the walk put the time back

    def test_every_fed_channel_in_one_walk_with_the_queue_off(self):
        node = self.cube()
        other = "|grp|pSphere1"
        self.cmds.keyable[other] = ["rotateZ"]
        self.cmds.types["blend2"] = "animBlendNodeAdditiveDA"
        self.feed(other, "rotateZ", "blend2")
        self.cmds.values[other + ".rotateZ"] = lambda time: -3.0 * time
        ac.scene = FakeScene(self.cmds, [(node, None), (other, None)])
        records = ac.object_curves([node, other], 2, 6)
        self.assertEqual(len(self.timewalk.walks), 1)
        self.assertEqual([entry[1] for entry in self.log if entry[0] == "go"], [2, 3, 4, 5, 6])
        self.assertEqual([k[1] for k in records[1]["attrs"]["rotateZ"]["keys"]],
                         [-3.0 * t for t in range(2, 7)])
        self.assertEqual([k[1] for k in records[0]["attrs"]["translateY"]["keys"]],
                         [2.0 * t + 1.0 for t in range(2, 7)])
        gone = [undo for what, undo in self.cmds.touched if what in ("walk enter", "go")]
        self.assertEqual(set(gone), set([False]))                # unrecorded, as a Save is
        self.assertIs(self.cmds.undo, True)

    def test_no_fed_channel_no_walk(self):
        node = "|grp|loc"
        self.cmds.keyable[node] = ["translateX", "visibility"]
        self.feed(node, "translateX", self.curve("loc_tx", [(0, 0), (10, 5)]))
        self.cmds.values[node + ".visibility"] = True
        ac.scene = FakeScene(self.cmds, [(node, None)])
        (record,) = ac.object_curves([node], 0, 10)
        self.assertEqual(sorted(record["attrs"]), ["translateX", "visibility"])
        self.assertEqual(self.timewalk.walks, [])

    def test_a_fed_channel_that_answers_no_number_is_left_out_in_its_place(self):
        node = self.cube()
        self.cmds.values[node + ".translateY"] = lambda time: "text" if time == 3 else 1.0
        (record,) = ac.object_curves([node], 0, 10)
        self.assertEqual(list(record["attrs"]), ["translateX", "visibility"])


# ------------------------------------------------------------------ the preview

class FakeTime(object):
    def __init__(self, value, unit=None):
        self.value, self.unit = value, unit

    @staticmethod
    def uiUnit():
        return "ntsc"


class FakeAnimControl(object):
    def __init__(self, log, cmds=None):
        self.log, self.cmds, self.now = log, cmds, FakeTime(12.0)

    def currentTime(self):
        return self.now

    def setCurrentTime(self, time):
        self.log.append(("time", time.value))
        if self.cmds is not None:
            self.cmds.touched.append(("time", self.cmds.undo))
        self.now = time


class FakeTweaks(object):
    """keys.Tweaks: read and set back, both logged. With `cmds`, the set-back finds a tweak the
    blasts threw away and puts it back as `keys.Tweaks.restore` does: autoKey turned off and
    back - two steps on the undo queue unless it is off."""

    def __init__(self, log, cmds=None):
        self.log, self.cmds = log, cmds
        log.append(("tweaks",))

    def restore(self, skip=()):
        if self.cmds is not None:
            auto = self.cmds.autoKeyframe(query=True, state=True)
            self.cmds.autoKeyframe(state=False)
            self.cmds.autoKeyframe(state=auto)
        self.log.append(("restore",))
        return []


class PreviewRefusals(Rebound):

    def setUp(self):
        Rebound.setUp(self)
        self.cmds.batch = False
        ac._panel = lambda: "modelPanel4"
        capture._port = lambda panel: (640, 360)

    def test_batch(self):
        self.cmds.batch = True
        self.assertEqual(ac.preview("x.jpg", 0, 10), (False, "no viewport for a preview", None))

    def test_no_panel(self):
        ac._panel = lambda: None
        self.assertEqual(ac.preview("x.jpg", 0, 10), (False, "no viewport for a preview", None))

    def test_a_hidden_port(self):
        capture._port = lambda panel: (8, 8)
        self.assertEqual(ac.preview("x.jpg", 0, 10),
                         (False, "the viewport is 8x8 - too small for a preview", None))

    def test_no_qt(self):
        ac._qt = lambda: None
        self.assertEqual(ac.preview("x.jpg", 0, 10), (False, "no Qt for a preview", None))

    def test_an_empty_range(self):
        self.assertEqual(ac.preview("x.jpg", 5, 2), (False, "the range 5-2 holds no frame", None))
        self.assertEqual(self.cmds.blasted, [])


class QtCase(Rebound):

    def setUp(self):
        Rebound.setUp(self)
        import maya_hubqt
        self.qt = maya_hubqt.qt()
        if self.qt is None:
            self.skipTest("no Qt")
        self.dir = tempfile.mkdtemp(prefix="poselib_anim_preview_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def colour_at(self, path, x, y):
        colour = self.qt.QtGui.QImage(path).pixelColor(x, y)
        return colour.red(), colour.green(), colour.blue()

    def near(self, got, want, tolerance=14):
        self.assertTrue(all(abs(a - b) <= tolerance for a, b in zip(got, want)), (got, want))


COLOURS = [(220, 40, 40), (40, 200, 60), (40, 60, 220), (230, 200, 40), (180, 60, 200)]


class Sheet(QtCase):

    def picture(self, name, width, height, centre, margin=(0, 0, 0)):
        """A `width` x `height` picture: `margin` outside its centred square, `centre` inside."""
        gui = self.qt.QtGui
        image = gui.QImage(width, height, gui.QImage.Format_RGB32)
        image.fill(gui.QColor(*margin))
        x, y, side = capture.square(width, height)
        painter = gui.QPainter(image)
        painter.fillRect(x, y, side, side, gui.QColor(*centre))
        painter.end()
        path = os.path.join(self.dir, name)
        self.assertTrue(image.save(path, "PNG"))
        return path

    def test_each_picture_square_and_scaled_into_its_cell(self):
        pictures = [self.picture("p%d.png" % i, 400, 225, colour, (0, 0, 0))
                    for i, colour in enumerate(COLOURS)]
        target = os.path.join(self.dir, "preview.jpg")
        self.assertEqual(ac.paint_sheet(self.qt, pictures, target, 64), (True, ""))
        image = self.qt.QtGui.QImage(target)
        columns = look.sheet_columns(len(COLOURS))
        self.assertEqual(columns, 3)
        self.assertEqual((image.width(), image.height()), (3 * 64, 2 * 64))
        for index, colour in enumerate(COLOURS):
            x, y, size, _ = look.sheet_cell(index, columns, 64)
            for dx, dy in ((4, 4), (59, 4), (4, 59), (59, 59), (32, 32)):
                self.near(self.colour_at(target, x + dx, y + dy), colour)    # no margin shows
        self.assertEqual(sorted(os.listdir(self.dir)),
                         sorted(["p%d.png" % i for i in range(5)] + ["preview.jpg"]))   # no .part

    def test_a_step_per_cell_and_a_cancel_writes_nothing(self):
        pictures = [self.picture("p%d.png" % i, 64, 64, colour)
                    for i, colour in enumerate(COLOURS)]
        target = os.path.join(self.dir, "preview.jpg")
        progress = FakeProgress()
        ac.paint_sheet(self.qt, pictures, target, 32, progress)
        self.assertEqual(len(progress.texts), 5)
        os.remove(target)
        progress = FakeProgress([True, True, False])
        self.assertEqual(ac.paint_sheet(self.qt, pictures, target, 32, progress),
                         (False, "cancelled - nothing saved"))
        self.assertEqual(len(progress.texts), 3)
        self.assertFalse(os.path.exists(target))
        self.assertFalse(os.path.exists(target + ".part"))

    def test_a_picture_that_cannot_be_read_writes_nothing(self):
        pictures = [self.picture("p0.png", 64, 64, COLOURS[0]),
                    os.path.join(self.dir, "missing.jpg")]
        target = os.path.join(self.dir, "preview.jpg")
        ok, note = ac.paint_sheet(self.qt, pictures, target, 32)
        self.assertFalse(ok)
        self.assertIn("nothing readable", note)
        self.assertFalse(os.path.exists(target))

    def test_each_cell_cut_and_the_sheet_written_by_captures_pieces(self):
        # fix round 1: the crop + scale and the atomic JPG write are the thumbnail's own
        # (`capture.square_scaled`, `capture.save_jpg`), not a copy of them
        calls = []
        real_scaled, real_save = capture.square_scaled, capture.save_jpg
        self.rebind(capture, "square_scaled", lambda qt, image, size: calls.append(
            ("cell", image.width(), image.height(), size)) or real_scaled(qt, image, size))
        self.rebind(capture, "save_jpg", lambda image, path, quality: calls.append(
            ("write", image.width(), image.height(), path, quality))
            or real_save(image, path, quality))
        pictures = [self.picture("p%d.png" % i, 80, 45, colour)
                    for i, colour in enumerate(COLOURS[:3])]
        target = os.path.join(self.dir, "preview.jpg")
        self.assertEqual(ac.paint_sheet(self.qt, pictures, target, 32), (True, ""))
        self.assertEqual(calls, [("cell", 80, 45, 32)] * 3
                         + [("write", 2 * 32, 2 * 32, target, ac.SHEET_QUALITY)])
        for index, colour in enumerate(COLOURS[:3]):
            x, y, _size, _ = look.sheet_cell(index, 2, 32)
            self.near(self.colour_at(target, x + 16, y + 16), colour)

    def test_the_blasted_frames_read_back_in_frame_order(self):
        for name in ("frame.0002.jpg", "frame.-001.jpg", "frame.0000.jpg", "first.jpg",
                     "frame.0001.png", "other.0003.jpg"):
            with open(os.path.join(self.dir, name), "wb") as handle:
                handle.write(b"x")
        found = ac.blasted(self.dir)
        self.assertEqual([frame for frame, _path in found], [-1, 0, 2])
        self.assertEqual([os.path.basename(path) for _frame, path in found],
                         ["frame.-001.jpg", "frame.0000.jpg", "frame.0002.jpg"])
        self.assertEqual(ac.blasted(os.path.join(self.dir, "nowhere")), [])


class PreviewSteps(QtCase):
    """`preview` against a fake playblast that paints each frame its own colour: the order of the
    press and the sheet it leaves."""

    def setUp(self):
        QtCase.setUp(self)
        self.cmds.batch = False
        ac._panel = lambda: "modelPanel4"
        capture._port = lambda panel: (96, 54)
        ac._qt = lambda: self.qt
        self.rebind(capture, "pump", lambda qt: self.log.append(("pump",)))
        self.control = FakeAnimControl(self.log, self.cmds)
        ac.oma = types.SimpleNamespace(MAnimControl=self.control)
        self.thrown = False             # the blasts threw a tweak away (its set-back toggles)
        ac.keys = types.SimpleNamespace(
            Tweaks=lambda: FakeTweaks(self.log, self.cmds if self.thrown else None),
            TIME_CURVES=keys.TIME_CURVES, feed_of=keys.feed_of)
        self.cmds.editor = {"joints": True, "grid": False, "nurbsCurves": True}
        self.cmds.colours = dict((frame, COLOURS[frame % len(COLOURS)]) for frame in range(-5, 80))
        self.target = os.path.join(self.dir, "preview.jpg").replace("\\", "/")

    def assert_flags_back(self):
        """Every flag the blast hid shows what it showed before (unset flags read shown)."""
        before = {"joints": True, "grid": False, "nurbsCurves": True}
        for flag in capture.HIDDEN:
            self.assertEqual(self.cmds.editor.get(flag, True), before.get(flag, True), flag)

    def test_the_sheet_holds_the_frames_in_order(self):
        ok, note, info = ac.preview(self.target, 0, 4)
        self.assertTrue(ok, note)
        self.assertEqual(info, {"frames": 5, "columns": 3, "size": look.PREVIEW_SIZE, "step": 1})
        image = self.qt.QtGui.QImage(self.target)
        self.assertEqual((image.width(), image.height()), (3 * 320, 2 * 320))
        for index in range(5):
            x, y, size, _ = look.sheet_cell(index, 3, 320)
            self.near(self.colour_at(self.target, x + 160, y + 160), COLOURS[index])
        self.assertIn("modelPanel4", note)
        self.assertIn("5 cells", note)

    def test_the_order_of_the_press(self):
        ac.preview(self.target, 0, 4)
        kinds = [entry[0] for entry in self.log]
        self.assertEqual(kinds[:2], ["undo", "tweaks"])     # the queue off, the tweaks read first
        blasts = [entry for entry in self.log if entry[0] == "playblast"]
        self.assertGreaterEqual(len(blasts), 3)                         # trap 120: settled
        for entry in blasts[:-1]:
            self.assertEqual(entry[1:], ((0,), True))                   # the first frame alone
        self.assertEqual(blasts[-1][1:], ((0, 1, 2, 3, 4), False))      # then ONE sequence
        first_blast = kinds.index("playblast")
        hidden = [entry for entry in self.log[:first_blast] if entry[0] == "editor"]
        self.assertEqual(set(entry[1] for entry in hidden), set(capture.HIDDEN))
        self.assertEqual(set(entry[2] for entry in hidden), set([False]))   # all off to blast
        self.assert_flags_back()
        last_blast = len(self.log) - 1 - kinds[::-1].index("playblast")
        tail = [entry for entry in self.log[last_blast + 1:] if entry[0] != "editor"]
        # the time back, then the tweaks set back, then the undo queue back on
        self.assertEqual(tail, [("time", 12.0), ("restore",), ("undo", True)])
        self.assertTrue(all(kw["offScreen"] and kw["editorPanelName"] == "modelPanel4"
                            and kw["widthHeight"] == (96, 54) and kw["format"] == "image"
                            for kw in self.cmds.blasted))

    def test_the_temporary_frames_are_removed(self):
        ac.preview(self.target, 0, 4)
        folder = os.path.dirname(self.cmds.blasted[-1]["filename"])
        self.assertTrue(folder)
        self.assertFalse(os.path.exists(folder))

    def test_a_long_clip_holds_every_step_th_frame(self):
        ok, note, info = ac.preview(self.target, 0, 69)
        self.assertTrue(ok, note)
        frames, step = look.preview_frames(0, 69)
        self.assertEqual(step, 2)
        self.assertEqual(info, {"frames": len(frames), "columns": look.sheet_columns(len(frames)),
                                "size": look.PREVIEW_SIZE, "step": 2})
        self.assertEqual(tuple(self.cmds.blasted[-1]["frame"]), tuple(frames))
        self.assertIn("every 2 frames", note)

    def test_a_frame_the_playblast_did_not_write(self):
        self.cmds.skip_frames = set([3])
        self.assertEqual(ac.preview(self.target, 0, 4),
                         (False, "the playblast wrote 4 of 5 frames", None))
        self.assertFalse(os.path.exists(self.target))

    def test_a_cancel_writes_no_sheet_and_still_puts_everything_back(self):
        self.assertEqual(ac.preview(self.target, 0, 4, FakeProgress([True, False])),
                         (False, "cancelled - nothing saved", None))
        self.assertFalse(os.path.exists(self.target))
        self.assertIn(("time", 12.0), self.log)
        self.assertEqual(self.log[-2:], [("restore",), ("undo", True)])

    def test_esc_during_the_playblast_cancels_and_writes_nothing(self):
        """The final review (S1): Esc during the playblast stopped it short - read as «the
        playblast wrote 3 of 5 frames», a preview that could not be made, and the card was saved
        without one. The progress is asked for a cancel right after the blast (`asked`, no step)
        and the answer is CANCELLED - nothing written, everything put back."""
        class Asked(FakeProgress):
            def asked(self):
                return True
        self.cmds.skip_frames = set([3, 4])                   # Esc stopped the playblast short
        self.assertEqual(ac.preview(self.target, 0, 4, Asked()),
                         (False, "cancelled - nothing saved", None))
        self.assertFalse(os.path.exists(self.target))
        self.assert_flags_back()
        self.assertEqual(self.log[-3:], [("time", 12.0), ("restore",), ("undo", True)])
        # a playblast Esc made RAISE: the same answer
        def stopped(**kw):
            raise RuntimeError("playblast: interrupted")
        self.cmds.playblast = stopped
        self.assertEqual(ac.preview(self.target, 0, 4, Asked()),
                         (False, "cancelled - nothing saved", None))

    def test_a_progress_without_esc_pressed_previews_as_before(self):
        class Calm(FakeProgress):
            def asked(self):
                return False
        ok, note, _info = ac.preview(self.target, 0, 4, Calm())
        self.assertTrue(ok, note)

    def test_a_failing_playblast_is_no_preview_and_puts_everything_back(self):
        def broken(**kw):
            raise RuntimeError("playblast: the panel is gone\nmore")
        self.cmds.playblast = broken
        self.assertEqual(ac.preview(self.target, 0, 4),
                         (False, "no preview - playblast: the panel is gone", None))
        self.assert_flags_back()
        self.assertEqual(self.log[-3:], [("time", 12.0), ("restore",), ("undo", True)])
        self.assertIs(self.cmds.undo, True)

    # ---- fix round 1: a preview is no step of the animator's undo queue

    def test_the_blast_runs_with_the_undo_queue_off(self):
        # a playblast steps the time and throws an unkeyed tweak away; setting it back
        # (`keys.Tweaks.restore`) toggles autoKey - two loose steps on the queue, measured, until
        # the blast ran unrecorded
        self.thrown = True
        ok, note, _info = ac.preview(self.target, 0, 4)
        self.assertTrue(ok, note)
        kinds = [kind for kind, _undo in self.cmds.touched]
        self.assertIn("playblast", kinds)
        self.assertEqual(kinds[-3:], ["time", "autoKeyframe", "autoKeyframe"])   # set back last
        self.assertEqual(set(undo for _kind, undo in self.cmds.touched), set([False]))
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"],
                         [("undo", False), ("undo", True)])
        self.assertEqual((self.log[0], self.log[-1]), (("undo", False), ("undo", True)))
        self.assertIs(self.cmds.undo, True)
        self.assertIs(self.cmds.auto, True)

    def test_a_failing_blast_still_sets_back_with_the_queue_off(self):
        self.thrown = True

        def broken(**kw):
            raise RuntimeError("playblast: the panel is gone")
        self.cmds.playblast = broken
        self.assertFalse(ac.preview(self.target, 0, 4)[0])
        self.assertEqual([kind for kind, _undo in self.cmds.touched][-3:],
                         ["time", "autoKeyframe", "autoKeyframe"])
        self.assertEqual(set(undo for _kind, undo in self.cmds.touched), set([False]))
        self.assertIs(self.cmds.undo, True)

    def test_a_queue_already_off_is_left_off_by_the_preview(self):
        self.cmds.undo = False
        ok, note, _info = ac.preview(self.target, 0, 4)
        self.assertTrue(ok, note)
        self.assertEqual([entry for entry in self.log if entry[0] == "undo"], [])
        self.assertIs(self.cmds.undo, False)

    # ---- fix round 1: the blast is capture's, not a copy of it

    def test_the_preview_blasts_with_captures_options_flags_and_pump(self):
        real_options, real_shown, real_set = (capture.blast_options, capture.shown_flags,
                                              capture.set_flags)
        asked = []
        self.rebind(capture, "blast_options", lambda panel, width, height: dict(
            real_options(panel, width, height), sentinel=(panel, width, height)))
        self.rebind(capture, "shown_flags",
                    lambda panel: asked.append(("shown", panel)) or real_shown(panel))
        self.rebind(capture, "set_flags", lambda panel, values: asked.append(
            ("set", panel, dict(values))) or real_set(panel, values))
        ok, note, _info = ac.preview(self.target, 0, 4)
        self.assertTrue(ok, note)
        self.assertGreaterEqual(len(self.cmds.blasted), 4)          # settled, then the sequence
        self.assertEqual([kw.get("sentinel") for kw in self.cmds.blasted],
                         [("modelPanel4", 96, 54)] * len(self.cmds.blasted))
        self.assertEqual([entry[:2] for entry in asked],
                         [("shown", "modelPanel4"), ("set", "modelPanel4"),
                          ("set", "modelPanel4")])
        shown = real_shown("modelPanel4")
        self.assertEqual(asked[1][2], dict((flag, False) for flag in shown))   # all off ...
        self.assertEqual(asked[2][2], shown)                                   # ... and back
        # idle pumped BETWEEN the first-frame blasts (the last blast is the sequence)
        self.assertEqual(self.log.count(("pump",)), len(self.cmds.blasted) - 2)


# ------------------------------------------------------------------ capture's pieces, shared

BLAST_OPTIONS = dict(format="image", compression="jpg", quality=95, widthHeight=(96, 54),
                     percent=100, viewer=False, showOrnaments=False, offScreen=True,
                     forceOverwrite=True, clearCache=True, editorPanelName="modelPanel4")


class SharedBlastPieces(QtCase):
    """The blast's pieces in `capture` (fix round 1: about 25 lines had been copied into
    `animcapture` - the next fix to the thumbnail's blast would have landed in one copy only):
    the editor flags read and set, the playblast's options, one frame blasted, the idle pump,
    the centre square scaled, the JPG written whole."""

    def test_the_shown_flags_each_read_and_one_the_editor_refuses_left_out(self):
        self.cmds.editor = {"joints": True, "grid": False}
        self.cmds.unknown = set(["follicles"])
        shown = capture.shown_flags("modelPanel4")
        self.assertEqual(list(shown), [flag for flag in capture.HIDDEN if flag != "follicles"])
        self.assertIs(shown["joints"], True)
        self.assertIs(shown["grid"], False)
        self.assertEqual([entry for entry in self.log if entry[0] == "editor"], [])   # a query

    def test_the_flags_set_each_on_its_own_one_refused_stops_none(self):
        self.cmds.unknown = set(["grid"])
        capture.set_flags("modelPanel4", OrderedDict([("joints", False), ("grid", False),
                                                      ("nurbsCurves", True)]))
        self.assertEqual([entry for entry in self.log if entry[0] == "editor"],
                         [("editor", "joints", False), ("editor", "nurbsCurves", True)])

    def test_the_blast_options(self):
        self.assertEqual(capture.blast_options("modelPanel4", 96, 54), BLAST_OPTIONS)
        self.assertEqual(capture.BLAST_QUALITY, 95)

    def test_one_frame_blasted_after_a_refresh_its_bytes_answered(self):
        path = os.path.join(self.dir, "one.jpg").replace("\\", "/")
        options = capture.blast_options("modelPanel4", 32, 18)
        data = capture.blast_file(options, 7, path)
        with open(path, "rb") as handle:
            self.assertEqual(data, handle.read())
        self.assertTrue(data)
        self.assertEqual([entry[0] for entry in self.log], ["refresh", "playblast"])
        self.assertEqual(self.cmds.blasted, [dict(options, frame=[7], completeFilename=path)])

    def test_the_pump_turns_mayas_idle_queue_then_qts_events(self):
        import maya.utils
        turned = []
        self.rebind(maya.utils, "processIdleEvents", lambda: turned.append("maya idle"))
        qt = types.SimpleNamespace(QtWidgets=types.SimpleNamespace(
            QApplication=types.SimpleNamespace(processEvents=lambda: turned.append("qt"))))
        capture.pump(qt)
        self.assertEqual(turned, ["maya idle", "qt"])

    def picture(self, width, height):
        """A `width` x `height` QImage: blue outside its centred square, red inside."""
        gui = self.qt.QtGui
        image = gui.QImage(width, height, gui.QImage.Format_RGB32)
        image.fill(gui.QColor(0, 0, 255))
        x, y, side = capture.square(width, height)
        painter = gui.QPainter(image)
        painter.fillRect(x, y, side, side, gui.QColor(255, 0, 0))
        painter.end()
        return image

    def test_the_centre_square_scaled_smooth(self):
        for width, height in ((400, 225), (90, 160)):
            small = capture.square_scaled(self.qt, self.picture(width, height), 50)
            self.assertEqual((small.width(), small.height()), (50, 50))
            for x, y in ((1, 1), (48, 1), (1, 48), (48, 48), (25, 25)):
                colour = small.pixelColor(x, y)
                self.assertGreater(colour.red(), 200, (width, height, x, y))   # no blue margin
                self.assertLess(colour.blue(), 60, (width, height, x, y))

    def test_a_jpg_written_whole_or_not_at_all(self):
        image = self.picture(64, 64)
        path = os.path.join(self.dir, "out.jpg")
        self.assertEqual(capture.save_jpg(image, path, 80), (True, ""))
        self.assertFalse(self.qt.QtGui.QImage(path).isNull())
        self.assertFalse(os.path.exists(path + ".part"))
        nowhere = os.path.join(self.dir, "no_such_folder", "out.jpg")
        self.assertEqual(capture.save_jpg(image, nowhere, 80),
                         (False, "could not write " + nowhere))
        self.assertFalse(os.path.exists(nowhere))
        self.assertFalse(os.path.exists(nowhere + ".part"))


class ThumbnailThroughThePieces(QtCase):
    """`capture.thumbnail` against the fake playblast: what the pose card's still did before
    its pieces were lifted out for the preview (fix round 1) and does after - the HIDDEN flags
    off for the blasts and put back, the tweaks read first and set back last, idle pumped
    between the blasts, the same playblast options, a `size` px square JPG, the raw blast
    removed. Written against the code before the lift and green on both."""

    def setUp(self):
        QtCase.setUp(self)
        self.cmds.batch = False
        self.cmds.editor = {"joints": True, "grid": False, "nurbsCurves": True}
        capture._port = lambda panel: (96, 54)
        self.rebind(capture, "keys", types.SimpleNamespace(Tweaks=lambda: FakeTweaks(self.log)))
        self.rebind_module("maya_vpstudio",
                           types.SimpleNamespace(active_panel=lambda: "modelPanel4"))
        import maya.utils
        self.rebind(maya.utils, "processIdleEvents", lambda: self.log.append(("idle",)))
        self.raw = os.path.join(tempfile.gettempdir(),
                                "skeldar_pose_thumbnail_%d.jpg" % os.getpid()).replace("\\", "/")

    def test_the_still(self):
        target = os.path.join(self.dir, "thumbnail.jpg")
        self.assertEqual(capture.thumbnail(target, 64),
                         (True, "thumbnail from modelPanel4 (96x54, 3 blasts)"))
        image = self.qt.QtGui.QImage(target)
        self.assertEqual((image.width(), image.height()), (64, 64))
        self.assertFalse(os.path.exists(self.raw))
        self.assertFalse(os.path.exists(target + ".part"))
        self.assertEqual(self.cmds.blasted,
                         [dict(BLAST_OPTIONS, frame=[12.0], completeFilename=self.raw)] * 3)

    def test_the_order(self):
        capture.thumbnail(os.path.join(self.dir, "thumbnail.jpg"), 64)
        kinds = [entry[0] for entry in self.log]
        self.assertEqual(kinds[0], "tweaks")
        blasts = [index for index, kind in enumerate(kinds) if kind == "playblast"]
        hidden = [entry for entry in self.log[:blasts[0]] if entry[0] == "editor"]
        self.assertEqual(set(entry[1] for entry in hidden), set(capture.HIDDEN))
        self.assertEqual(set(entry[2] for entry in hidden), set([False]))
        between = [entry[0] for entry in self.log[blasts[0]:blasts[-1]]
                   if entry[0] in ("idle", "playblast")]
        self.assertEqual(between, ["playblast", "idle", "playblast", "idle"])
        tail = [entry for entry in self.log[blasts[-1] + 1:] if entry[0] != "editor"]
        self.assertEqual(tail, [("restore",)])
        before = {"joints": True, "grid": False, "nurbsCurves": True}
        for flag in capture.HIDDEN:
            self.assertEqual(self.cmds.editor.get(flag, True), before.get(flag, True), flag)


def calls_in(module):
    """[(name, owner, keywords)] of every call in `module`'s source: `name` the function or
    method called, `owner` the plain name it was called on ("" for none), `keywords` the
    keyword names passed."""
    out = []
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if not isinstance(node, ast.Call):
            continue
        func, words = node.func, [word.arg for word in node.keywords if word.arg]
        if isinstance(func, ast.Attribute):
            owner = func.value.id if isinstance(func.value, ast.Name) else ""
            out.append((func.attr, owner, words))
        elif isinstance(func, ast.Name):
            out.append((func.id, "", words))
    return out


class OneCopy(unittest.TestCase):
    """Each piece of the blast is written ONCE, in `capture`, and `animcapture` calls it (fix
    round 1). Read off the two modules' code: a piece copied back would show here before it
    drifts from the thumbnail's."""

    PIECES = {          # one frame blasted (blast_file): the single playblast, pinned below
        "modelEditor": "the editor flags (shown_flags, set_flags)",
        "processIdleEvents": "the idle pump (pump)",
        "processEvents": "the idle pump (pump)",
        "scaled": "the centre square scaled (square_scaled)",
        "save": "the JPG written (save_jpg)",
    }

    def test_animcapture_holds_no_piece_of_the_blast(self):
        calls = calls_in(ac)
        for name, piece in self.PIECES.items():
            self.assertNotIn(name, [call[0] for call in calls], piece)
        self.assertNotIn(("replace", "os"), [call[:2] for call in calls],
                         "the JPG written whole (save_jpg)")
        for word in ("offScreen", "editorPanelName", "widthHeight", "quality", "percent"):
            self.assertNotIn(word, [w for call in calls for w in call[2]],
                             "the playblast's options (blast_options)")

    def test_capture_holds_each_piece_once(self):
        calls = calls_in(capture)
        names = [call[0] for call in calls]
        self.assertEqual(names.count("modelEditor"), 2)           # shown_flags, set_flags
        self.assertEqual(names.count("processIdleEvents"), 1)     # pump
        self.assertEqual(names.count("scaled"), 1)                # square_scaled
        self.assertEqual(names.count("playblast"), 1)             # blast_file
        self.assertEqual([call[:2] for call in calls].count(("replace", "os")), 1)   # save_jpg
        keywords = [word for call in calls for word in call[2]]
        self.assertEqual(keywords.count("offScreen"), 1)          # blast_options

    def test_animcapture_blasts_its_sequence_with_captures_options(self):
        # the one playblast animcapture makes itself - the preview's frames, in one go - takes
        # its options from capture (`**options`), adding only where the frames go
        (blast,) = [node for node in ast.walk(ast.parse(inspect.getsource(ac)))
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "playblast"]
        self.assertEqual(sorted(word.arg for word in blast.keywords if word.arg),
                         ["filename", "frame", "framePadding"])
        self.assertEqual([type(word.value).__name__ for word in blast.keywords
                          if word.arg is None], ["Name"])          # ** the options


if __name__ == "__main__":
    unittest.main()

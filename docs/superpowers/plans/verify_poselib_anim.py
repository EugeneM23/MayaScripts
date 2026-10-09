"""The Pose Library's ANIMATION cards, end to end, in mayapy STANDALONE (2026-10-03).

Never in the animator's open Maya: this adds characters, keys them, makes animation layers,
undoes and finally starts a new scene. Run with a scratch MAYA_APP_DIR (the animator's prefs
never touched):

    $env:MAYA_APP_DIR = "<a scratch folder>"
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
        docs/superpowers/plans/verify_poselib_anim.py [out.txt]

Every gate prints `PASS/FAIL <name> <value>`, the run ends `SUMMARY x/y` (an optional file
argument gets the same lines). The plugin is the one beside this script (`<repo>/SkeldarAnim`;
`$env:POSELIB_PLUGIN` names another), its path the first line; `POSELIB_PHASES` narrows a run
(the characters a phase needs are added the first time one asks for them). The real road every
time: a card is `animcapture.build_animation` of a selection, written by `store.write` and read
back by `store.read` / `store.read_frames` (the window's road), pasted by `animapply.apply` /
`apply_onto` / `drop_floor` / `Blend`; the scene is then re-evaluated by a REAL time change at
every frame measured, and the game BONES are measured against the card's own frames - never
against the press's own measure.

  capture   Manny_Rig A keyed over 0..23 (every FK control and RootX_M at five frames, another
            pose at each - the hinges bent forward -, Main travelling (0, 0, 0) -> (60, 0, 120)
            and turning 30 deg, one control keyed at 9.4): `build_animation` of Main -> 24
            frames, every bone's decoded world at 0 / 11 / 23 equal to the scene's (1e-5), the
            eight drives too, `key_times` the keyed frames rounded (9.4 -> 9) with the ends in,
            the header static only; a left-hand card (the chip); the Manny UE5 skeleton keyed
            and carded the same; the cards through the disk (`store.write`, `read`,
            `read_frames`, `cards`) unchanged.
  twin      the full card onto a second Manny_Rig B standing at (200, 0, -100) turned 90 deg,
            pasted at 50: every member bone of B at 50+i on A's at i RELATIVE TO each one's root
            (0.01 deg / 0.01 cm; the unrolled limb bones by where they point), B's root at 50+i
            on A's travel carried onto where B stood (0.01 cm / 0.01 deg); Select objects
            exactly the controls the press keyed, Main with them; In place (through
            `apply_onto`, B's root naming it): Main's keys key for key, the root unmoved, the
            members on the card; the hand card: Main and the arm's controls key for key, the
            arm's bones where they stood on every frame, the hand on its forearm's drive and the
            fingers on the hand as the card's, Select objects what it keyed and no Main; Main
            dragged by hand off its keys (autoKey off), then a default Apply: the travel from the
            TWEAKED place (the final review's M2) - the control, the walk going to the frame the
            scene stands on as before the fix, travels from the keyed place 170 cm away; RootX_M
            dragged off its keys, then A's left-leg card at Blend 50 % with Connect (a pre-pass
            walks the range before the chunk): every channel's first key what it showed, the IK
            foot included (the re-review of the fix wave) - the control, back on the entry frame
            a plain time set as before the fix, keys the IK foot 10.8 cm off.
  modes     B carrying a take of its own (keys at 40, 60, 70.5, 80, 100 on EVERY control
            channel), pasted at 60 (24 frames) in each of Replace / Replace all / Insert / Merge,
            once on the base and once with an additive layer carrying a take of its own (the
            base then never touched): the written plugs' curves on the active layer exactly the
            mode's (the old keys outside [60, 83] kept, moved by 24 or gone, 70.5 kept by
            Merge only), the plugs the press did not write key for key, the pose on the card at
            60 / 71 / 83.
  options   At current time off: keys on 0..23; a sub-range 5..9 at 50: keys on 50..54, B on
            A's 5..9 and its root travelling from frame 5; Connect: the first keyed value of
            every channel is what it showed (Main aside: the travel is placed), every later key
            the plain paste's plus that constant - to twice the solve's own dependence on the
            pose it starts from (a floor of 1e-4): a frame's solve samples the rig as it stands
            there, and the plain paste itself from two starting poses differs by 0.0012 deg
            (measured here every run, degrees and centimetres apart) -, and the line carries no
            «worst» while the pose stands 5+ deg off the card (a measure would have read it) and
            the plain paste's does; Source keys: keys only on the card's key times moved to 50,
            the pose on the card there.
  cross     the full card onto Creep_Rig, Orc_D_Rig, the Manny skeleton and the Creep skeleton,
            each moved and turned: every paired member pointing where the source's bone does on
            every frame (0.1 deg) - its direction at the first pasted frame, which the transfer
            aligns a non-twin's rests on once (spec, "Per frame"), carried by its turn; the
            card's own children wandering in their parents' frames are read off the card and
            said (Manny_Rig's neck_02 -> head 0.32 deg: its in-between rolls with half the
            head's twist); the twin Manny skeleton every member TURNED as the source's, 0.01
            deg -, lengths unchanged, the root on the travel carried through the two root rests
            and scaled by the bodies' size (computed here, and equal to
            `posemath.scale_between`).
  mirror    the card mirrored onto B: every member on its parent the mirror of the card's
            opposite on every frame (0.01 deg), the pelvis's offset from the root mirrored, the
            root on the travel reflected across the root's sagittal plane (F . L . F) - the
            sideways step negated, the forward step kept.
  blend     B carrying a take, a Blend session at 50 %: every keyed control's rotation on every
            frame HALFWAY between the take and the card (the quaternion angle from the take
            half the whole turn, and so is the rest of the way, 0.01 deg), every translation
            halfway (0.01 cm: the card is the plain paste's solve from the take, the blend's
            solves start from the blended pose - an IK pole's place 0.0002 cm apart).
  objects   a locator's tx (a spline, the curve weighted, one fixed out-tangent) and its free
            channels saved over 0..20 and pasted at 30 onto another locator: the keys on 30 /
            40 / 50 with the source's values, tangent types, the fixed angle and weight; the
            curve equal to the source's at every quarter frame; the free channels one key each
            at 30; Replace and Insert over a take of the target's own; a sub-range with keys
            inserted at its ends; Connect; a prop parent-constrained to A's IK hand and a
            channel on an additive layer - sampled every frame, the card's keys the scene's at
            every frame, pasted at 30 onto two free locators and read back there.
  undo      B carrying a take, autoKey ON, a tweak on A and on a prop, the animator's last step
            a marker: after a Replace paste the tweaks stand; ONE Ctrl+Z - every curve in the
            scene key for key, B's channels back, the tweaks still standing - and the next
            Ctrl+Z takes the marker back; Esc on the third frame (a progress that cancels):
            «cancelled», every curve key for key, the tweaks standing, and the next Ctrl+Z the
            animator's step; a Save with autoKey on: no curve touched, the tweaks standing, the
            next Ctrl+Z the animator's step; pasted OFF the current frame (At current time off
            standing at 90 - Merge, and Replace onto channels with no key in 0..23 -, and Merge
            at 89.5): ONE Ctrl+Z, every channel read at the current frame what it showed before
            the press (the final review's M1) - the control, the press with no undo mark as before
            the fix, leaves them on the first pasted frame's values.
  mixamo    the skeleton_conventions Mixamo fixture built at 0.85 of its size (so the bodies
            differ), its Hips travelling and turning: onto Manny_Rig - the root on the Hips'
            ground travel (the floor under them, turned by their heading) carried and SCALED by
            the bodies' size (computed, and != 1), the members pointing where the card's do; a
            second Mixamo fixture as the TARGET, walking along a take of its own, A's full card
            pasted on it In place with Replace: its ground frame on the take's own at every
            pasted frame (the final review's M4) - the control, the ground read off the curve the
            press rewrites as before the fix, falls off it; the same In place with Insert at 60:
            every pasted frame on the take's ground at 60, where the shifted take resumes at 84
            (the re-review of the fix wave) - the control, each frame on the take's own ground
            there as before the fix, rides the walk and snaps back; a Mixamo fixture ROLLING over its
            Hips (a full turn about X, a 2 deg side tilt, its own heading jumping 165 deg near
            upside down) carded and pasted onto a rootless twin standing elsewhere, with the
            travel and In place: every member on the card relative to the target's ground on
            every frame (the re-review of the fix wave) - the control, the top joint's OWN
            heading taken off as before the fix, turns the body 180 deg at the inverted frames.
  speed     the seconds a frame of a paste onto a rig and onto a skeleton (< 1.0 on the rig).
  floor     a new scene: `drop_floor` of the full card at (150, 0, 80) - a Manny_Rig added, Main
            on the point at the paste frame, the root travelling from there as the card's, the
            members on the card, the selection kept; the hand card (ntsc) pasted into the scene
            switched to film - frame for frame, the line saying so; the Mixamo card dropped at
            (-100, 0, 50) -
            rebuilt bones only, its ground frame on the point at the paste frame and travelling
            from there, every member on the card carried from its ground frame.

Two harness facts (measured for the pose verify, holding here): `currentTime` IS on Maya's undo
queue, and so is `autoKeyframe -state` - a time change or an autoKey switch between a press and
its `cmds.undo()` takes the Ctrl+Z. The undo gates read right after the press.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md
"""

import contextlib
import io
import math
import os
import shutil
import sys
import tempfile
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402

# the plugin beside THIS script (<repo>/SkeldarAnim) - CLAUDE.md note 9; POSELIB_PLUGIN overrides
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
TESTS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "tests"))
if not os.path.isfile(os.path.join(PLUGIN, "maya_poselib", "animapply.py")):
    raise ImportError("no plugin with maya_poselib.animapply at %s" % PLUGIN)
sys.path.insert(0, PLUGIN)
sys.path.insert(0, TESTS)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_asretarget  # noqa: E402
import maya_rigs  # noqa: E402
import maya_skeletonmap as skelmap  # noqa: E402
import skeleton_conventions as fixtures  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

from maya_poselib import animapply, animcapture, animdata, keys, rigsolve, scene, store  # noqa
from maya_poselib import timewalk  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

PHASES = [p.strip() for p in os.environ.get(
    "POSELIB_PHASES",
    "capture,twin,modes,options,cross,mirror,blend,objects,undo,mixamo,speed,floor"
).split(",") if p.strip()]
OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []

ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")
UNROLLED_LIMB = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
HINGE = {"Elbow": ("Shoulder", "Wrist"), "Knee": ("Hip", "Ankle")}

START, END = 0, 23                  # the source take
KEY_FRAMES = (0, 6, 12, 18, 23)     # ... keyed here
ODD_KEY = 9.4                       # ... and one control here: `key_times` rounds it to 9
TRAVEL = (60.0, 0.0, 120.0)         # A's Main over the take
TURN = 30.0
SKEL_FRAMES = (0, 8, 16, 23)        # the Manny skeleton's take
AT = 50                             # where most pastes land
TAKE = (40.0, 60.0, 70.5, 80.0, 100.0)   # the modes phase's take on the target
MODES_AT = 60
#  where each target stands, (x, y, z) and the turn about world Y
PLACES = {"B": ((200.0, 0.0, -100.0), 90.0), "C": ((-150.0, 0.0, 80.0), -40.0),
          "O": ((300.0, 0.0, 220.0), 135.0), "S": ((-250.0, 0.0, -150.0), 60.0),
          "CS": ((120.0, 0.0, 300.0), -110.0)}
KEYS_OF = {"A": "Manny_Rig", "B": "Manny_Rig", "S": "Manny", "C": "Creep_Rig",
           "O": "Orc_D_Rig", "CS": "Creep"}
MIX_FACTOR = 0.85                   # the Mixamo fixture built at this size: the bodies differ
MIX_FRAMES = (0, 8, 16, 23)
MIX_TRAVEL = (40.0, 0.0, 150.0)
MIX_TURN = 25.0
FLOOR_AT = (150.0, 0.0, 80.0)
NATIVE_AT = (-100.0, 0.0, 50.0)
FLOOR_FRAME = 12
FPS_AT = 60                         # the film-rate paste of the floor phase


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))
    return bool(ok)


def W(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def rel(a, b):
    """a in b's frame, rigid."""
    return pm.rigid(a) * pm.rigid(b).inverse()


def frame():
    return float(cmds.currentTime(query=True))


def go(t):
    """A REAL time change: every keyed channel and the rig downstream read fresh after it."""
    cmds.currentTime(t, update=True)


def evaluate():
    t = frame()
    go(t + 1)
    go(t)


def matrix_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def placed(turn, point):
    """A rotation standing at `point` (x, y, z or an MVector)."""
    values = [float(v) for v in om.MMatrix(turn)]
    values[12:15] = [float(point[0]), float(point[1]), float(point[2])]
    values[15] = 1.0
    return om.MMatrix(values)


def cm_deg(a, b):
    """(cm, deg) between two matrices' places and turns."""
    return (pm.position(a) - pm.position(b)).length(), pm.angle(a, b)


def scene_uuids():
    return set(cmds.ls(cmds.ls() or [], uuid=True) or [])


# ------------------------------------------------------------------ the characters

def add(key):
    """The new Rig or skeleton root after Add Character of the catalog row `key`."""
    before_rigs = set(r.namespace for r in maya_rigs.rigs())
    before_bare = set(skeletonimport.bare_roots())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    new_rigs = [r for r in maya_rigs.rigs() if r.namespace not in before_rigs]
    if new_rigs:
        return new_rigs[0]
    new = [r for r in skeletonimport.bare_roots() if r not in before_bare]
    return new[0] if new else None


def control_plugs(rig):
    """Every keyable, unlocked, settable scalar channel of the rig's ControlSet members."""
    out = []
    for member in cmds.sets(rig.control_set, query=True) or []:
        node = (cmds.ls(member, long=True) or [None])[0]
        if node is None or not cmds.objectType(node, isAType="transform"):
            continue
        for attr in cmds.listAttr(node, keyable=True, unlocked=True, scalar=True) or []:
            plug = node + "." + attr
            try:
                if cmds.getAttr(plug, settable=True):
                    out.append(plug)
            except (RuntimeError, ValueError):
                continue
    return out


def joint_plugs(root):
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or [])
    return [j + "." + ch for j in joints for ch in ROT + TR
            if not cmds.getAttr(j + "." + ch, lock=True)]


def long_plug(plug):
    node, attr = plug.rsplit(".", 1)
    return (cmds.ls(node, long=True) or [node])[0] + "." + attr


def values_of(plugs):
    return dict((p, float(cmds.getAttr(p))) for p in plugs)


def set_values(values):
    for plug, value in values.items():
        cmds.setAttr(plug, value)


def drop_layers():
    """Every animation layer gone, BaseAnimation last."""
    layers = cmds.ls(type="animLayer") or []
    root = cmds.animLayer(query=True, root=True)
    for layer in [n for n in layers if n != root] + ([root] if root else []):
        if cmds.objExists(layer):
            cmds.delete(layer)


class Char(object):
    """One character of the run: its ref, its channels and their values after Add, a wipe."""

    def __init__(self, label, handle):
        self.label = label
        if isinstance(handle, maya_rigs.Rig):
            self.rig, self.root = handle, handle.skeleton_root
            self.ref = scene.rig_ref(handle)
            self.plugs = control_plugs(handle)
        else:
            self.rig, self.root = None, handle
            self.ref = scene.skeleton_ref(handle)
            self.plugs = joint_plugs(handle)
        self.defaults = values_of(self.plugs)
        self._bones = None

    def wipe(self):
        """Every layer gone, every curve on the character's channels deleted, every channel
        back at its value after Add."""
        drop_layers()
        curves = cmds.listConnections(self.plugs, source=True, destination=False,
                                      type="animCurve") or []
        if curves:
            cmds.delete(list(set(curves)))
        for plug, value in self.defaults.items():
            try:
                cmds.setAttr(plug, value)
            except RuntimeError:
                pass
        evaluate()

    def node(self, leaf):
        return maya_rigs.node(self.rig, leaf)

    def long(self, leaf):
        return (cmds.ls(self.node(leaf), long=True) or [None])[0]

    def bones(self):
        """`scene.skeleton`'s bones, read ONCE: the run reads only their STATIC fields (path,
        parent, canonical, rest) - every world is read live (`W`) at the frame measured."""
        if self._bones is None:
            self._bones = scene.skeleton(self.ref)[0]
        return self._bones

    def game(self):
        return dict((leaf, b["path"]) for leaf, b in self.bones().items())

    def selection(self):
        """What a press is made through: a rig's wrist control, a skeleton's root."""
        return [self.node("FKWrist_L")] if self.rig is not None else [self.root]

    def place(self, keyed=()):
        """Moved to and turned as PLACES says: a rig's Main (keyed there at `keyed` when given),
        a skeleton's root joint."""
        (x, y, z), yaw = PLACES[self.label]
        if self.rig is not None:
            main = self.rig.main
            for attr, value in zip(TR + ("rotateY",), (x, y, z, yaw)):
                if keyed:
                    for t in keyed:
                        cmds.setKeyframe(main + "." + attr, time=t, value=value)
                else:
                    cmds.setAttr(main + "." + attr, value)
        else:
            cmds.move(x, y, z, self.root, relative=True, worldSpace=True)
            cmds.rotate(0, yaw, 0, self.root, relative=True, worldSpace=True)
        evaluate()


CH = {}
CARDS = {}
SPEED = {}
LIBRARY = []


def need(label):
    """The character `label`, added the first time a phase asks for it."""
    if label not in CH:
        t0 = time.time()
        handle = add(KEYS_OF[label])
        if handle is None:
            raise RuntimeError("Add Character of %s added nothing" % KEYS_OF[label])
        CH[label] = Char(label, handle)
        say("   added %s = %s in %.1f s" % (label, scene.describe([CH[label].ref], []),
                                            time.time() - t0))
    return CH[label]


# ------------------------------------------------------------------ a deterministic FK pose
# (task 6a's proof: knees and elbows bent on their anatomical hinge, signed by the body's front -
# a hyperextended knee flips an IK hinge 170 deg, which says nothing of the press)

_BENDS = {}


def _perp(a, b, c):
    s, e, w = (pm.position(W(n)) for n in (a, b, c))
    line = (w - s).normal()
    return e - (s + line * ((e - s) * line))


def bend_channels(ch, joint, side):
    key = (ch.label, joint, side)
    if key in _BENDS:
        return _BENDS[key]
    up, down = HINGE[joint]
    ref = om.MVector(0, 0, 1) if joint == "Knee" else om.MVector(0, 0, -1)
    ctrl = ch.node("FK" + joint + side)
    effect = {}
    for channel in ROT:
        old = cmds.getAttr(ctrl + "." + channel)
        cmds.setAttr(ctrl + "." + channel, old + 30)
        effect[channel] = _perp(ch.node("FKX" + up + side), ch.node("FKX" + joint + side),
                                ch.node("FKX" + down + side))
        cmds.setAttr(ctrl + "." + channel, old)
    bend = max(ROT, key=lambda c: abs(effect[c] * ref))
    sign = 1.0 if effect[bend] * ref > 0 else -1.0
    roll = min([c for c in ROT if c != bend], key=lambda c: effect[c].length())
    other = [c for c in ROT if c not in (bend, roll)][0]
    _BENDS[key] = (bend, sign, roll, other)
    return _BENDS[key]


def toes_swing(ch, side):
    key = (ch.label, "Toes", side)
    if key in _BENDS:
        return _BENDS[key]
    ctrl, joint, ikx = ch.node("FKToes" + side), ch.node("FKXToes" + side), \
        ch.node("IKXToes" + side)
    here = pm.rigid(W(ikx))
    v = max(((pm.position(W(t)) - pm.position(here)) * pm.rotation(here).inverse()
             for t in cmds.listRelatives(ikx, children=True, type="joint", fullPath=True)),
            key=lambda o: o.length())
    moved = {}
    for channel in ROT:
        before = v * pm.rotation(W(joint))
        old = cmds.getAttr(ctrl + "." + channel)
        cmds.setAttr(ctrl + "." + channel, old + 30)
        moved[channel] = pm.direction_angle(before, v * pm.rotation(W(joint)))
        cmds.setAttr(ctrl + "." + channel, old)
    _BENDS[key] = max(ROT, key=lambda c: moved[c])
    return _BENDS[key]


def pose_values(ch, seed=0.0):
    """{long plug: value}: every FK control of `maya_asretarget.ROWS` turned (a forearm roll,
    the hinges bent forward, the toes swung, fingers smaller), RootX_M moved and turned."""
    out = {}
    k = 0
    for base, _ue in maya_asretarget.ROWS:
        for side in ("_M", "_L", "_R"):
            node = ch.node("FK" + base + side)
            if not cmds.objExists(node):
                continue
            k += 1
            amp = 12.0 if "Finger" in base else 18.0
            vals = (amp * math.sin(1.3 * k + seed), amp * math.cos(0.7 * k + 2 * seed),
                    amp * math.sin(0.4 * k + 1 + seed))
            if base in HINGE:
                bend, sign, roll, other = bend_channels(ch, base, side)
                amount = {"Elbow": (42.0, 20.0, 4.0), "Knee": (35.0, 9.0, 3.0)}[base]
                by = {bend: sign * (amount[0] + 6 * seed), roll: amount[1], other: amount[2]}
                vals = tuple(by[c] for c in ROT)
            if base == "Toes":
                swing = toes_swing(ch, side)
                vals = tuple(16.0 + 4 * seed if c == swing else 0.0 for c in ROT)
            for channel, value in zip(ROT, vals):
                plug = node + "." + channel
                if not cmds.getAttr(plug, lock=True):
                    out[long_plug(plug)] = value
    rootx = ch.node("RootX_M")
    for channel, value in zip(TR + ROT, (3.0, -4.0, 5.0, 8.0, 15.0, -6.0)):
        out[long_plug(rootx + "." + channel)] = value * (1.0 - 0.6 * seed)
    return out


# ------------------------------------------------------------------ the cards

def card_bones(card, i):
    """The card's frame `i` (an index from its first frame) as a pose card's bones."""
    header, frames = card
    return animdata.bones_at(header, frames, i)


def target_members(header, ch, source=None, mirror=False):
    """(target members, pairs, target bones) of the card's members on `ch` - as the press
    pairs them (`posemath.pairs` of the card's frame bones and the target)."""
    members = header["members"]
    if mirror:
        source, members = pm.mirror(source, members)
    bones = ch.bones()
    pairs = pm.pairs(source, bones)
    wanted = set(members)
    return [leaf for leaf in bones if pairs.get(leaf) in wanted], pairs, bones


def scene_worlds(ch, game=None):
    game = game or ch.game()
    return dict((leaf, pm.rigid(W(path))) for leaf, path in game.items())


def rel_rows(source, ch, members, game=None):
    """[(leaf, deg, cm)]: each non-twist member bone RELATIVE TO ITS ROOT against the card's
    frame `source`, relative to the card's root - the four unrolled limb bones by where they
    point (toward the next limb bone)."""
    worlds = scene_worlds(ch, game)
    root = pm.root_of(ch.bones())
    s_root = pm.root_of(source)
    g_root, c_root = worlds[root], pm.rigid(source[s_root]["world"])
    rows = []
    for leaf in members:
        if leaf not in worlds or leaf not in source or pm.is_twist(leaf) or leaf == root:
            continue
        got, want = rel(worlds[leaf], g_root), rel(source[leaf]["world"], c_root)
        cm = (pm.position(got) - pm.position(want)).length()
        base = leaf[:-2] if leaf.endswith(("_l", "_r")) else leaf
        child = UNROLLED_LIMB.get(base)
        if child is not None and child + leaf[-2:] in worlds:
            child = child + leaf[-2:]
            a = (pm.position(worlds[child]) - pm.position(worlds[leaf])) * \
                pm.rotation(g_root).inverse()
            b = (pm.position(source[child]["world"]) - pm.position(source[leaf]["world"])) * \
                pm.rotation(c_root).inverse()
            rows.append((leaf, pm.direction_angle(a, b), cm))
        else:
            rows.append((leaf, pm.angle(got, want), cm))
    return rows


def worst_of(rows):
    """(deg, cm, leaf of the worst deg, leaf of the worst cm) over (leaf, deg, cm) rows."""
    deg = max(rows, key=lambda r: r[1]) if rows else (None, 0.0, 0.0)
    cm = max(rows, key=lambda r: r[2]) if rows else (None, 0.0, 0.0)
    return deg[1], cm[2], deg[0], cm[0]


class Worst(object):
    """The worst (value, where) seen."""

    def __init__(self):
        self.value, self.at = 0.0, None

    def see(self, value, at):
        if self.at is None or value > self.value:
            self.value, self.at = value, at

    def __str__(self):
        return "%.6f (%s)" % (self.value, self.at)


def heading(turn):
    """The yaw about world +Y of a world-space turn (the swing-twist split's twist)."""
    q = om.MTransformationMatrix(om.MMatrix(turn)).rotation(asQuaternion=True)
    size = math.hypot(q.y, q.w)
    if size < 1e-12:
        return om.MMatrix()
    return om.MQuaternion(0.0, q.y / size, 0.0, q.w / size).asMatrix()


def root_frames(bones, world=None):
    """(pose frame, rest frame) of a skeleton's ROOT FRAME, computed here: its root bone's own
    when it stands at the floor (a root of its own), else its GROUND frame - the floor under its
    top joint, turned by the top joint's heading since its rest (the rest frame unturned)."""
    top = pm.root_of(bones)
    rest = pm.matrix(bones[top]["rest"])
    pose = pm.matrix(world if world is not None else bones[top]["world"])
    if pm.has_root(bones):
        return pm.rigid(pose), pm.rigid(rest)
    turn = pm.rotation(rest).inverse() * pm.rotation(pose)
    at_pose, at_rest = pm.position(pose), pm.position(rest)
    return (placed(heading(turn), (at_pose.x, 0.0, at_pose.z)),
            placed(om.MMatrix(), (at_rest.x, 0.0, at_rest.z)))


def body_height(bones):
    """The pelvis's rest height over the root's rest frame (the floor for a rootless top)."""
    pelvis = next((leaf for leaf, b in sorted(bones.items()) if b.get("canonical") == "pelvis"),
                  "pelvis" if "pelvis" in bones else None)
    top = pm.root_of(bones)
    floor = pm.position(bones[top]["rest"]).y if pm.has_root(bones) else 0.0
    return pm.position(bones[pelvis]["rest"]).y - floor


def body_scale(source, target):
    """Target over source pelvis height, 1.0 within 2 % - computed here."""
    ratio = body_height(target) / body_height(source)
    return 1.0 if abs(ratio - 1.0) <= 0.02 else ratio


def reflection(bones):
    """F: the reflection across the card's sagittal plane, in its root's rest frame."""
    root = pm.root_of(bones)
    # the rest frame alone: a header's bones are static, they carry no world
    rest_root = pm.rotation(root_frames(bones, bones[root]["rest"])[1])
    across = (pm.position(bones["upperarm_l"]["rest"]) - pm.position(
        bones["upperarm_r"]["rest"])) * rest_root.inverse()
    axis = across.normal()
    values = [1.0 if i == j else 0.0 for i in range(4) for j in range(4)]
    for i in range(3):
        for j in range(3):
            values[i * 4 + j] -= 2.0 * axis[i] * axis[j]
    return om.MMatrix(values), axis


def expected_root(first, now, target_bones, place, scale, flip=None):
    """Where the target's root frame stands for the card's frame `now` (the first pasted frame
    `first`): the source root frame's motion L = R_now . R_first^-1 (reflected F . L . F when
    `flip`), carried into the target's root axes through the two root rests (Q . L . Q^-1, Q =
    rot(T_rest) . rot(S_rest)^-1), its translation scaled, from where the target stood
    (`place`)."""
    s_now, s_rest = root_frames(now)
    s_first, _r = root_frames(first)
    motion = pm.rigid(s_now) * pm.rigid(s_first).inverse()
    if flip is not None:
        motion = flip * motion * flip
    t_rest = root_frames(target_bones)[1]
    q = pm.rotation(pm.rigid(t_rest) * pm.rigid(s_rest).inverse())
    carried = q * motion * q.inverse()
    return placed(pm.rotation(carried), pm.position(carried) * scale) * place


def target_place(ch):
    """The target's root frame as it stands now (its root, or its ground frame)."""
    bones = ch.bones()
    top = pm.root_of(bones)
    return root_frames(bones, W(bones[top]["path"]))[0]


def direction_children(pairs, source, target):
    """{target leaf: its direction child}, read the way `posemath.alignments` reads it."""
    ue = pm.ue_named(source) and pm.ue_named(target)
    root = pm.root_of(target) if pm.has_root(target) else None
    usable = [t for t in pm._ordered(target) if t in pairs and t != root and pairs[t] in source
              and not pm.is_helper(t) and not pm.is_twist(t)]
    mapping, names = {}, {}
    for leaf in usable:
        name = leaf if ue else (target[leaf].get("canonical") or leaf)
        if name not in mapping:
            mapping[name], names[leaf] = leaf, name
    parents = dict((leaf, b.get("parent")) for leaf, b in target.items())
    children = skelmap.direction_children(skelmap.canonical_parents(mapping, parents))
    out = {}
    for leaf, name in names.items():
        child = mapping.get(children.get(name))
        if child is not None:
            out[leaf] = child
    return out


def _poses(source, ch, bones, pairs):
    """{source leaf: P} as the transfer reads the source onto `ch`: a bone's drive where
    `posemath.drive_bones` names it (onto a rig every drive; onto a skeleton the bones whose roll
    its own twist bones cannot take), else its world."""
    drives = pm.drive_bones(source, bones, pairs, use_drive=ch.rig is not None)
    return dict((leaf, pm.matrix(b["drive"] if leaf in drives else b["world"]))
                for leaf, b in source.items())


def _source_direction(source, p, s, sc, first=None, p_first=None):
    """Where the source bone `s` points at its partner child `sc`, in world: its own child's
    place as it stands - or, with `first` (the frame the transfer aligned its rests on), the
    direction the child stood in, in `s`'s P frame, at `first`, turned by `s`'s P now: what a
    rotation transfer aligned ONCE carries; a partner further down read off the two rests."""
    if source[sc]["parent"] == s:
        if first is None:
            return pm.position(source[sc]["world"]) - pm.position(source[s]["world"])
        local = (pm.position(first[sc]["world"]) - pm.position(first[s]["world"])) * \
            pm.rotation(p_first[s]).inverse()
        return local * pm.rotation(p[s])
    rest_dir = pm.position(source[sc]["rest"]) - pm.position(source[s]["rest"])
    return rest_dir * pm.rotation(source[s]["rest"]).inverse() * pm.rotation(p[s])


def pointing(source, ch, members, pairs, bones, children, first=None):
    """[(leaf, deg, 0)]: every paired member with a direction child pointing where the source's
    bone does, each in its root frame's rest axes (verify_poselib_apply's `pointing`).

    With `first` - the clip's first pasted frame, the one the transfer reads a non-twin's rest
    alignment off, ONCE (the spec's "Per frame": per frame it would make a clip jitter) - "where
    the source's bone points" is the direction its child stood in at `first`, carried by the
    bone's turn since (`_source_direction`). A source whose child moves in its parent's frame
    (Manny_Rig's game neck_02 rolls with half the head's twist while the head keeps its place:
    0.3195 deg over this take, measured off the card alone) cannot be followed by a rotation
    transfer; `drift` reads how far the card's own children wander so."""
    p = _poses(source, ch, bones, pairs)
    p_first = _poses(first, ch, bones, pairs) if first is not None else None
    now = dict((leaf, W(b["path"])) for leaf, b in bones.items())
    t_pose, t_rest = root_frames(bones, now[pm.root_of(bones)])
    t_frame = pm.rotation(t_pose).inverse() * pm.rotation(t_rest)
    s_pose, s_rest = root_frames(source, source[pm.root_of(source)]["world"])
    s_frame = pm.rotation(s_pose).inverse() * pm.rotation(s_rest)
    rows = []
    for leaf in members:
        child = children.get(leaf)
        if child is None or child not in now or leaf not in now:
            continue
        s, sc = pairs[leaf], pairs[child]
        want = _source_direction(source, p, s, sc, first, p_first)
        got = (pm.position(now[child]) - pm.position(now[leaf])) * t_frame
        rows.append((leaf, pm.direction_angle(got, want * s_frame), 0.0))
    return rows


def drift(source, first, ch, members, pairs, bones, children):
    """[(leaf, deg, 0)]: how far each paired member's partner child has wandered in the source
    bone's own frame since `first` - the card's own data, no scene read: the angle between where
    the source bone points now and where the first frame's direction, carried by its turn, does."""
    p, p_first = _poses(source, ch, bones, pairs), _poses(first, ch, bones, pairs)
    rows = []
    for leaf in members:
        child = children.get(leaf)
        if child is None or leaf not in pairs or child not in pairs:
            continue
        s, sc = pairs[leaf], pairs[child]
        rows.append((leaf, pm.direction_angle(_source_direction(source, p, s, sc),
                                              _source_direction(source, p, s, sc, first,
                                                                p_first)), 0.0))
    return rows


def twin_turns(source, ch, members, pairs, bones):
    """[(leaf, deg, 0)]: a twin's every member TURNED as the source's, relative to the root,
    through the two rests (verify_poselib_solve's cross gate for a twin)."""
    t_root, s_root = pm.root_of(bones), pm.root_of(source)
    now = dict((leaf, W(b["path"])) for leaf, b in bones.items())
    p = dict((leaf, pm.matrix(b["world"])) for leaf, b in source.items())
    s_rest_root = pm.rotation(source[s_root]["rest"])
    rows = []
    for leaf in members:
        s = pairs[leaf]
        got = pm.rotation(now[leaf]) * pm.rotation(now[t_root]).inverse()
        want = pm.rotation(bones[leaf]["rest"]) * pm.rotation(source[s]["rest"]).inverse() \
            * pm.rotation(p[s]) * pm.rotation(p[s_root]).inverse() * s_rest_root \
            * pm.rotation(bones[t_root]["rest"]).inverse()
        rows.append((leaf, pm.angle(got, want), 0.0))
    return rows


def lengths(bones):
    """{leaf: its distance from its parent} as the skeleton stands now."""
    out = {}
    for leaf, b in bones.items():
        parent = b.get("parent")
        if parent in bones:
            out[leaf] = (pm.position(W(b["path"])) - pm.position(W(bones[parent]["path"]))
                         ).length()
    return out


# ------------------------------------------------------------------ curves

def curve_of(plug, layer=None):
    """The time curve holding `plug`'s keys on `layer` (a layer's name; None: no layers)."""
    return keys.curve_for(plug, layer)


def curve_keys(plug, layer=None):
    """((times), (values)) of the plug's curve on `layer`, or ((), ()) when it has none."""
    curve = curve_of(plug, layer)
    if curve is None:
        return (), ()
    return (tuple(cmds.keyframe(curve, query=True, timeChange=True) or ()),
            tuple(cmds.keyframe(curve, query=True, valueChange=True) or ()))


def key_at(plug, t, layer=None):
    curve = curve_of(plug, layer)
    if curve is None:
        return None
    found = cmds.keyframe(curve, query=True, time=(t, t), valueChange=True)
    return found[0] if found else None


def curve_state():
    """{curve: (times, values)} of every animCurve in the scene."""
    out = {}
    for curve in cmds.ls(type="animCurve") or []:
        times = tuple(cmds.keyframe(curve, query=True, timeChange=True) or ())
        values = tuple(cmds.keyframe(curve, query=True, valueChange=True) or ())
        out[curve] = (times, values)
    return out


def curves_same(before, after):
    """(changed curves, curves gone, new curves)."""
    changed = [c for c in before if c in after and (
        len(before[c][0]) != len(after[c][0]) or
        any(abs(a - b) > 1e-9 for a, b in zip(before[c][0] + before[c][1],
                                               after[c][0] + after[c][1])))]
    gone = [c for c in before if c not in after]
    new = [c for c in after if c not in before]
    return changed, gone, new


def keyed_plugs(ch, t, layer=None):
    """The character's plugs with a key at `t` on `layer`'s curve - what a paste wrote."""
    return [p for p in ch.plugs if key_at(p, t, layer) is not None]


def same_times(got, want):
    return len(got) == len(want) and all(abs(a - b) < 1e-6 for a, b in zip(got, want))


# ------------------------------------------------------------------ setup: the takes and cards

def key_source(a):
    """A's take: every FK control and RootX_M at KEY_FRAMES, another pose at each; Main
    travelling and turning; one control keyed off the whole frames (ODD_KEY)."""
    a.wipe()
    for n, f in enumerate(KEY_FRAMES):
        for plug, value in pose_values(a, seed=0.35 * n).items():
            cmds.setKeyframe(plug, time=f, value=value)
        u = float(f - START) / (END - START)
        for attr, value in zip(TR + ("rotateY",),
                               (TRAVEL[0] * u, TRAVEL[1] * u, TRAVEL[2] * u, TURN * u)):
            cmds.setKeyframe(a.rig.main + "." + attr, time=f, value=value)
    spine = long_plug(a.node("FKSpine1_M") + ".rotateZ")
    go(ODD_KEY)
    cmds.setKeyframe(spine, time=ODD_KEY, value=float(cmds.getAttr(spine)) + 6.0)
    evaluate()


def key_skeleton(s):
    """The Manny skeleton's take: every joint (the root's and the helpers' aside) turned at
    SKEL_FRAMES, the root travelling."""
    s.wipe()
    bones = s.bones()
    root = pm.root_of(bones)
    rest = values_of([b["path"] + "." + c for b in bones.values() for c in ROT])
    for n, f in enumerate(SKEL_FRAMES):
        for i, leaf in enumerate(sorted(bones)):
            if leaf == root or pm.is_helper(leaf):
                continue
            path = bones[leaf]["path"]
            for j, channel in enumerate(ROT):
                plug = path + "." + channel
                cmds.setKeyframe(plug, time=f,
                                 value=rest[plug] + 7.0 * math.sin(i + 2.0 * j + 0.9 * n))
        u = float(f - START) / (END - START)
        for attr, value in zip(("translateX", "translateZ"), (-30.0 * u, 90.0 * u)):
            plug = s.root + "." + attr
            cmds.setKeyframe(plug, time=f, value=s.defaults[plug] + value)
    evaluate()


def through_disk(name, header, frames):
    """The card written to the scratch library and read back as the window reads it: (header,
    frames, path)."""
    if not LIBRARY:
        LIBRARY.append(tempfile.mkdtemp(prefix="skeldar_anim_verify_").replace("\\", "/"))
    path = store.write(LIBRARY[0], "", name, header, frames=frames)
    return store.read(path), (store.read_frames(path) if frames is not None else None), path


def cards():
    """The cards every phase uses (built once): A's full card, its left-hand card, the Manny
    skeleton's card - each through the disk."""
    if "full" in CARDS:
        return
    a = need("A")
    key_source(a)
    t0 = time.time()
    header, frames, note = animcapture.build_animation([a.rig.main], start=START, end=END)
    SPEED["capture"] = (time.time() - t0) / (END - START + 1)
    say("   full card: %s (%.3f s a frame)" % (note, SPEED["capture"]))
    CARDS["full_raw"] = (header, frames)
    read, read_frames, path = through_disk("Walk", header, frames)
    CARDS["full"] = (read, read_frames)
    CARDS["full_path"] = path
    hand, hand_frames, note = animcapture.build_animation([a.rig.main], regions=["Hand L"],
                                                          start=START, end=END)
    say("   hand card: %s" % note)
    read, read_frames, _p = through_disk("Wave", hand, hand_frames)
    CARDS["hand"] = (read, read_frames)
    go(0)


def leg_card():
    """A's LEFT-LEG card (the chip «Leg L»), through the disk: its IK foot is a world-space
    control - it follows the pelvis as it stands."""
    cards()
    if "leg" not in CARDS:
        a = need("A")
        header, frames, note = animcapture.build_animation([a.rig.main], regions=["Leg L"],
                                                           start=START, end=END)
        say("   leg card: %s" % note)
        read, read_frames, _p = through_disk("Step", header, frames)
        CARDS["leg"] = (read, read_frames)
        go(0)
    return CARDS["leg"]


def skeleton_card():
    if "skeleton" in CARDS:
        return
    s = need("S")
    key_skeleton(s)
    header, frames, note = animcapture.build_animation([s.root], start=START, end=END)
    say("   skeleton card: %s" % note)
    CARDS["skeleton_raw"] = (header, frames)
    read, read_frames, _p = through_disk("SkelWalk", header, frames)
    CARDS["skeleton"] = (read, read_frames)


# ------------------------------------------------------------------ capture

def capture_gates(label, ch, card, expected_times, raw):
    header, frames = card
    count = END - START + 1
    bones = ch.bones()
    gate("capture %s: %d frames, every bone a row, the range whole" % (label, count),
         header["frames"] == count and len(frames["world"]) == count and
         header["start"] == float(START) and header["end"] == float(END) and
         sorted(frames["bones"]) == sorted(bones) and
         all(len(row) == 7 * len(frames["bones"]) for row in frames["world"]),
         "%d frames, %d rows of %d bones (the skeleton %d), %s-%s" % (
             header["frames"], len(frames["world"]), len(frames["bones"]), len(bones),
             header["start"], header["end"]))
    static = [leaf for leaf, b in header["bones"].items()
              if set(b) != set(("parent", "canonical", "rest", "rotateOrder"))]
    gate("capture %s: the header's bones static only" % label, not static,
         "%d bones, %d carry more %s" % (len(header["bones"]), len(static), static[:3]))
    worst, control = Worst(), Worst()
    drive_worst, scaled = Worst(), Worst()
    for i in (0, 11, 23):
        go(START + i)
        row = frames["world"][i]
        for n, leaf in enumerate(frames["bones"]):
            decoded = animdata.decode(row[7 * n:7 * n + 7])
            world = W(bones[leaf]["path"])
            # against the RIGID world: the codec keeps a bone's turn and place and drops its
            # scale by design (animdata), and the rig's scale chain leaves up to 4e-5 of scale
            # on Manny_Rig's left finger bones at frame 11 - against the whole matrix that read
            # 3.3e-5 while the turn and place agree to 5e-7 (measured, 2026-10-03)
            worst.see(matrix_diff(decoded, pm.rigid(world)), "%s @%d" % (leaf, i))
            scaled.see(matrix_diff(world, pm.rigid(world)), "%s @%d" % (leaf, i))
        if ch.rig is not None:
            drives = rigsolve.drive_matrices(ch.rig)
            for leaf, series in frames["drive"].items():
                drive_worst.see(matrix_diff(animdata.decode(series[i]), drives[leaf]),
                                "%s @%d" % (leaf, i))
    go(START)
    row = frames["world"][11]
    for n, leaf in enumerate(frames["bones"]):
        control.see(matrix_diff(animdata.decode(row[7 * n:7 * n + 7]),
                                W(bones[leaf]["path"])), leaf)
    gate("capture %s: every bone's decoded world at 0 / 11 / 23 is the scene's (its turn and "
         "place)" % label, worst.value <= 1e-5 and control.value > 0.1,
         "worst element %s (the scale the codec drops: %s); frame 11's against the scene at 0 "
         "(the clip moves): %s" % (worst, scaled, control))
    if ch.rig is not None:
        gate("capture %s: the eight drives, every frame, decoded = the rig's" % label,
             sorted(frames["drive"]) == sorted(
                 ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "thigh_r",
                  "calf_l", "calf_r"]) and
             all(len(s) == count for s in frames["drive"].values()) and
             drive_worst.value <= 1e-5 and header["rig_source"],
             "%s, worst %s" % (sorted(frames["drive"]), drive_worst))
    else:
        gate("capture %s: no drive, no rig source" % label,
             frames["drive"] == {} and not header["rig_source"], "%s" % frames["drive"])
    gate("capture %s: key_times the keyed frames rounded, the ends in" % label,
         header["key_times"] == [float(t) for t in expected_times],
         "%s (expected %s)" % (header["key_times"], [float(t) for t in expected_times]))
    raw_header, raw_frames = raw
    same_header = dict((k, v) for k, v in raw_header.items() if k != "name") == \
        dict((k, v) for k, v in header.items() if k != "name")
    gate("capture %s: through the disk (store.write -> read / read_frames) unchanged" % label,
         same_header and raw_frames == frames and header["format"] == store.ANIM_FORMAT,
         "header %s, frames %s" % (same_header, raw_frames == frames))


def phase_capture():
    cards()
    a = need("A")
    expected = sorted(set([START, END] + list(KEY_FRAMES) + [int(math.floor(ODD_KEY + 0.5))]))
    capture_gates("Manny_Rig", a, CARDS["full"], expected, CARDS["full_raw"])
    header = CARDS["full"][0]
    say("   speed: capture %.4f s a frame (93 bones and 8 drives)" % SPEED["capture"])
    listed, broken = store.cards(LIBRARY[0])
    walk = [c for c in listed if c.name == "Walk"]
    gate("capture the library lists the card as an animation",
         len(walk) == 1 and walk[0].type == "anim" and walk[0].frames == 24 and
         walk[0].start == 0.0 and walk[0].end == 23.0 and walk[0].fps == "ntsc" and
         walk[0].kind == "character" and not broken,
         "%s; broken %s" % (walk[0][10:] if walk else None, broken))
    hand = CARDS["hand"][0]
    hand_bones = sorted(leaf for leaf in header["bones"] if leaf.endswith("_l") and (
        leaf == "hand_l" or leaf.split("_")[0] in skelmap.FINGERS))
    gate("capture the hand card holds the left hand and its fingers",
         sorted(hand["members"]) == hand_bones and hand["regions"] == ["Hand L"],
         "%d members %s" % (len(hand["members"]), hand["regions"]))
    skeleton_card()
    s = need("S")
    capture_gates("Manny skeleton", s, CARDS["skeleton"], SKEL_FRAMES, CARDS["skeleton_raw"])


# ------------------------------------------------------------------ twin

def paste_rows(ch, card, pairs_at, members_t):
    """Worst (deg, cm) over the frames `pairs_at` [(target time, card index)] of the members
    on the card relative to the root."""
    deg, cm = Worst(), Worst()
    for t, i in pairs_at:
        go(t)
        rows = rel_rows(card_bones(card, i), ch, members_t)
        d, c, at_d, at_c = worst_of(rows)
        deg.see(d, "%s @%g" % (at_d, t))
        cm.see(c, "%s @%g" % (at_c, t))
    return deg, cm


def root_rows(ch, card, pairs_at, first_index, place, scale, flip=None):
    """Worst (cm, deg) of the target's root frame against the card's travel carried from
    `place`."""
    bones = ch.bones()
    top = pm.root_of(bones)
    first = card_bones(card, first_index)
    cm, deg = Worst(), Worst()
    for t, i in pairs_at:
        go(t)
        want = expected_root(first, card_bones(card, i), bones, place, scale, flip)
        got = root_frames(bones, W(bones[top]["path"]))[0]
        c, d = cm_deg(got, want)
        cm.see(c, "@%g" % t)
        deg.see(d, "@%g" % t)
    return cm, deg


def phase_twin():
    cards()
    b = need("B")
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    # ---- the full card, Main keyed at B's place at 40 and 100
    b.wipe()
    b.place(keyed=(40, 100))
    go(AT)
    place = target_place(b)
    members_t, _pairs, _b = target_members(header, b, card_bones(card, 0))
    t0 = time.time()
    ok, text = animapply.apply(header, frames, selection=b.selection())
    SPEED["rig"] = (time.time() - t0) / count
    say("   twin: %s" % text)
    wrist = long_plug(b.node("FKWrist_L") + ".rotateX")
    main_tx = b.rig.main + ".translateX"
    gate("twin the press keyed every frame 50..73 (Main also keeps its keys at 40 and 100)",
         ok and same_times(curve_keys(wrist)[0], [AT + i for i in range(count)]) and
         same_times(curve_keys(main_tx)[0], [40.0] + [AT + i for i in range(count)] + [100.0]),
         "wrist %d keys, Main %d keys | %s" % (len(curve_keys(wrist)[0]),
                                               len(curve_keys(main_tx)[0]), text))
    keyed_nodes = set(p.rsplit(".", 1)[0] for p in keyed_plugs(b, AT))
    ok_sel, sel_text = animapply.select_objects(header, selection=b.selection())
    selected = set(cmds.ls(selection=True, long=True) or [])
    main_long = cmds.ls(b.rig.main, long=True)[0]
    gate("twin Select objects: exactly the controls the press keyed, Main with them (it carries "
         "the travel)", ok_sel and selected == keyed_nodes and main_long in selected,
         "%d selected, %d keyed; selected not keyed %s, keyed not selected %s | %s" % (
             len(selected), len(keyed_nodes),
             sorted(n.split("|")[-1] for n in selected - keyed_nodes)[:4],
             sorted(n.split("|")[-1] for n in keyed_nodes - selected)[:4], sel_text))
    cmds.select(clear=True)
    deg, cm = paste_rows(b, card, span, members_t)
    shifted, _c = paste_rows(b, card, [(AT + i, i + 1) for i in range(0, count - 1, 4)],
                             members_t)
    gate("twin every member on A's frame relative to the root, every frame",
         deg.value <= 0.01 and cm.value <= 0.01 and shifted.value > 1.0,
         "%s deg, %s cm; against the NEXT frame (the gate can fail): %s deg" % (
             deg, cm, shifted))
    scale = body_scale(header["bones"], b.bones())
    rcm, rdeg = root_rows(b, card, span, 0, place, scale)
    go(AT + count - 1)
    moved = (pm.position(target_place(b)) - pm.position(place)).length()
    gate("twin the root on A's travel carried from where B stood, every frame",
         rcm.value <= 0.01 and rdeg.value <= 0.01 and moved > 100.0 and scale == 1.0,
         "%s cm, %s deg; it travelled %.2f cm (scale %.4f)" % (rcm, rdeg, moved, scale))
    # ---- In place: Main keyed at its place, untouched, the root unmoved
    b.wipe()
    b.place(keyed=(40, 100))
    main_plugs = [p for p in b.plugs if p.rsplit(".", 1)[0] == cmds.ls(b.rig.main,
                                                                        long=True)[0]]
    main_keys = dict((p, curve_keys(p)) for p in main_plugs)
    go(AT)
    place = target_place(b)
    # through `apply_onto` (a drop on the character in a viewport): the root names it
    ok, text = animapply.apply_onto(header, frames, b.root,
                                    options=animdata.Options(in_place=True))
    say("   in place (apply_onto): %s" % text)
    kept = [p for p in main_plugs if curve_keys(p) != main_keys[p]]
    gate("twin In place: Main's keys key for key", ok and not kept and any(
        main_keys[p][0] for p in main_plugs), "%d Main channels, %d changed %s" % (
            len(main_plugs), len(kept), kept[:3]))
    unmoved = Worst()
    for t, _i in span[::3]:
        go(t)
        c, d = cm_deg(target_place(b), place)
        unmoved.see(max(c, d), "@%g" % t)
    deg, cm = paste_rows(b, card, span[::3], members_t)
    gate("twin In place: the root where it stood, the members on the card",
         unmoved.value <= 1e-6 and deg.value <= 0.01,
         "root off by %s; members %s deg, %s cm" % (unmoved, deg, cm))
    # ---- the hand card: Main and the arm untouched, the hand on the card
    hand = CARDS["hand"]
    b.wipe()
    b.place(keyed=(40, 100))
    arm = [rigsolve.bases(b.rig)[leaf].fk for leaf in ("clavicle_l", "upperarm_l",
                                                       "lowerarm_l")]
    for node in arm:
        for channel, swing in zip(ROT, (15.0, -10.0, 20.0)):
            plug = node + "." + channel
            cmds.setKeyframe(plug, time=40, value=float(cmds.getAttr(plug)))
            cmds.setKeyframe(plug, time=100, value=float(cmds.getAttr(plug)) + swing)
    evaluate()
    watched = main_plugs + [n + "." + c for n in arm for c in ROT + TR]
    watched_keys = dict((p, curve_keys(p)) for p in watched)
    game = b.game()
    arm_bones = ("clavicle_l", "upperarm_l", "lowerarm_l")
    before = {}
    for t, _i in span:
        go(t)
        before[t] = dict((leaf, W(game[leaf])) for leaf in arm_bones + ("hand_l",))
        before[t]["Main"] = W(b.rig.main)
    go(AT)
    ok, text = animapply.apply(hand[0], hand[1], selection=b.selection())
    say("   hand: %s" % text)
    hand_keyed = set(p.rsplit(".", 1)[0] for p in keyed_plugs(b, AT))
    ok_sel, sel_text = animapply.select_objects(hand[0], selection=b.selection())
    selected = set(cmds.ls(selection=True, long=True) or [])
    gate("twin Select objects of the hand card: exactly what it keyed, no Main",
         ok_sel and selected == hand_keyed and main_long not in selected and hand_keyed,
         "%d selected, %d keyed | %s" % (len(selected), len(hand_keyed), sel_text))
    cmds.select(clear=True)
    changed = [p for p in watched if curve_keys(p) != watched_keys[p]]
    hand_members, _p, _bb = target_members(hand[0], b, card_bones(hand, 0))
    stood, moved, on_card = Worst(), Worst(), Worst()
    for t, i in span:
        go(t)
        for leaf in arm_bones:
            stood.see(max(cm_deg(W(game[leaf]), before[t][leaf])), "%s @%g" % (leaf, t))
        stood.see(max(cm_deg(W(b.rig.main), before[t]["Main"])), "Main @%g" % t)
        moved.see(pm.angle(W(game["hand_l"]), before[t]["hand_l"]), "@%g" % t)
        src = card_bones(hand, i)
        drive = pm.matrix(rigsolve.drive_matrices(b.rig)["lowerarm_l"])
        on_card.see(pm.angle(rel(W(game["hand_l"]), drive),
                             rel(src["hand_l"]["world"], src["lowerarm_l"]["drive"])),
                    "hand_l @%g" % t)
        for leaf in hand_members:
            if leaf == "hand_l":
                continue
            on_card.see(pm.angle(rel(W(game[leaf]), W(game["hand_l"])),
                                 rel(src[leaf]["world"], src["hand_l"]["world"])),
                        "%s @%g" % (leaf, t))
    gate("twin the hand card: Main's and the arm's controls key for key, the arm's bones and "
         "Main where they stood on every frame", ok and not changed and stood.value <= 1e-6,
         "%d channels watched, %d changed %s; bones off by %s" % (
             len(watched), len(changed), changed[:3], stood))
    gate("twin the hand card: the hand on its forearm's drive and the fingers on the hand as "
         "the card's, every frame", on_card.value <= 0.01 and moved.value > 1.0,
         "%s deg (the hand moved up to %s deg)" % (on_card, moved))
    b.wipe()
    tweaked_gates(b, card, span)
    prepass_tweak_gates(b)


@contextlib.contextmanager
def patched(owner, name, value):
    """`owner.name` replaced by `value` for the block and put back - a positive control runs the
    code as it was before a fix (the final review's M1 / M2 / M4)."""
    saved = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, saved)


def _walk_always_goes(walk, frame, restore=True):
    """`timewalk.Walk.arrive` before the final review's M2: a `go` even onto the frame the scene
    already stands on (which throws the animator's unkeyed tweaks away)."""
    walk.go(frame)
    return True


def tweaked_gates(b, card, span):
    """The final review's M2: Main dragged by hand off its keys (autoKey off - an unkeyed tweak)
    to place the walk, then a DEFAULT Apply (At current time on: the paste on the frame the scene
    stands on) - the travel starts from the TWEAKED place, Main keyed from there. The control:
    the same press with the walk going to the paste frame although the scene stands there (the
    code before the fix) - its travel starts where Main's keys stand, 170 cm away."""
    header, frames = card
    scale = body_scale(header["bones"], b.bones())
    tweak = (("translateX", 150.0), ("translateZ", 80.0), ("rotateY", 25.0))

    def stage():
        b.wipe()
        b.place(keyed=(40, 100))
        go(AT)
        keyed = target_place(b)
        for attr, d in tweak:
            plug = b.rig.main + "." + attr
            cmds.setAttr(plug, float(cmds.getAttr(plug)) + d)
        return keyed, target_place(b)

    keyed, tweaked = stage()
    apart = (pm.position(tweaked) - pm.position(keyed)).length()
    ok, text = animapply.apply(header, frames, selection=b.selection())
    say("   twin, Main tweaked off its keys: %s" % text)
    rcm, rdeg = root_rows(b, card, span, 0, tweaked, scale)
    gate("twin Main dragged off its keys by hand, a default Apply: the travel starts from the "
         "TWEAKED place, every frame", ok and rcm.value <= 0.01 and rdeg.value <= 0.01 and
         apart > 100.0,
         "%s cm, %s deg off the travel from the tweaked place (%.2f cm from the keyed one) | %s"
         % (rcm, rdeg, apart, text))
    _k, tweaked = stage()
    with patched(timewalk.Walk, "arrive", _walk_always_goes):
        ok_c, text_c = animapply.apply(header, frames, selection=b.selection())
    ccm, cdeg = root_rows(b, card, span, 0, tweaked, scale)
    kcm, kdeg = root_rows(b, card, span, 0, keyed, scale)
    gate("twin the control - the walk going to the frame it stands on (before the fix): the "
         "travel from the KEYED place, the gate above would fail",
         ok_c and ccm.value > 100.0 and kcm.value <= 0.01 and kdeg.value <= 0.01,
         "%s cm off the tweaked place's travel, %s cm / %s deg off the keyed place's" % (
             ccm, kcm, kdeg))
    b.wipe()


def _arrive_as_before(walk, frame, restore=True):
    """`timewalk.Walk.arrive` before the re-review of the fix wave: back on the entry frame after
    a move, a plain time set - the tweaks it threw away stay away."""
    here = walk._here is not None and abs(float(frame) - float(walk._here.value)) <= 1e-9
    if not walk.moved and here:
        walk.frame = frame
        return False
    walk.go(frame)
    return True


def prepass_tweak_gates(b):
    """The re-review of the fix wave (M2 only partly fixed): a press that walks the paste range
    BEFORE its chunk - Blend under 100 % reads the take on every frame (a rootless target its
    ground) - came back to its first frame `a`, the frame it entered on, through a real time
    set, which threw the animator's unkeyed tweaks away: frame a was solved against the KEYED
    scene while the partner and Connect's reference had read the tweaks. B carrying a take on
    RootX_M (keys at 40 and 100), RootX_M dragged by hand off its keys at 50 (autoKey off), then
    A's LEFT-LEG card at Blend 50 % with Connect, at 50: every channel's first key is what it
    showed - the IK foot (world-space: it follows the pelvis as it stands) included. The
    control: the same press with the walk's arrival back at the entry frame a plain time set
    (the code before the fix) - the IK foot's first key moves off with the pelvis."""
    header, frames = leg_card()
    rootx = b.node("RootX_M")
    tweak = (("translateX", 20.0), ("translateZ", -12.0))

    def stage():
        b.wipe()
        b.place()
        for t, extra in ((40, 0.0), (100, 15.0)):
            for attr in TR:
                plug = rootx + "." + attr
                cmds.setKeyframe(plug, time=t, value=float(cmds.getAttr(plug)) + extra)
        evaluate()
        go(AT)
        for attr, d in tweak:
            plug = rootx + "." + attr
            cmds.setAttr(plug, float(cmds.getAttr(plug)) + d)
        return values_of(b.plugs)

    def press(control):
        shown = stage()
        options = animdata.Options(connect=True)
        if control:
            with patched(timewalk.Walk, "arrive", _arrive_as_before):
                ok, text = animapply.apply(header, frames, selection=b.selection(), alpha=0.5,
                                           options=options)
        else:
            ok, text = animapply.apply(header, frames, selection=b.selection(), alpha=0.5,
                                       options=options)
        written = keyed_plugs(b, AT)
        first, ik = Worst(), Worst()
        for plug in written:
            off = abs(key_at(plug, AT) - shown[plug])
            if plug.endswith(ROT):
                off = abs((off + 180.0) % 360.0 - 180.0)
            name = plug.split("|")[-1]
            first.see(off, name)
            if "IKLeg_L" in name and plug.endswith(TR):
                ik.see(off, name)
        return ok, text, written, first, ik

    ok, text, written, first, ik = press(False)
    say("   twin, Blend 50 %% + Connect with RootX_M tweaked: %s" % text)
    gate("twin RootX_M dragged off its keys by hand, the leg card at Blend 50 % with Connect (a "
         "pre-pass walks the range first): every channel's first key is what it showed, the IK "
         "foot included", ok and len(written) > 5 and first.value <= 1e-3,
         "%d written, worst %s (the IK foot %s) | %s" % (len(written), first, ik, text))
    ok_c, text_c, written_c, first_c, ik_c = press(True)
    gate("twin the control - back on the entry frame a plain time set (before the fix): frame a "
         "solved against the keyed pelvis, the IK foot's first key off, the gate above would "
         "fail", ok_c and ik_c.value > 1.0,
         "%d written, worst %s, the IK foot %s cm" % (len(written_c), first_c, ik_c))
    b.wipe()


# ------------------------------------------------------------------ modes

def key_take(ch, times, layer=None, seed=2.0):
    """The modes phase's take: every control channel keyed at `times` (on `layer`, final
    values, when given) - the FK controls and RootX_M in another pose at every time, Main at
    its place, every other channel at the value it shows."""
    shown = values_of(ch.plugs)
    if layer:
        cmds.animLayer(layer, edit=True, attribute=ch.plugs)
    for n, t in enumerate(times):
        pose = pose_values(ch, seed + 0.4 * n)
        for plug in ch.plugs:
            value = pose.get(plug, shown[plug])
            if layer:
                cmds.setKeyframe(plug, time=t, value=value, animLayer=layer)
            else:
                cmds.setKeyframe(plug, time=t, value=value)
    evaluate()


def expected_times(mode, before, a, b):
    """The times a written plug's active curve holds after a paste over [a, b] in `mode`, its
    keys `before`."""
    paste = [float(t) for t in range(int(a), int(b) + 1)]
    n = b - a + 1
    if mode == "replace":
        kept = [t for t in before if t < a - 1e-6 or t > b + 1e-6]
    elif mode == "replace_all":
        kept = []
    elif mode == "insert":
        kept = [t for t in before if t < a - 1e-6] + [t + n for t in before if t >= a - 1e-6]
    else:
        kept = [t for t in before if not any(abs(t - p) < 1e-6 for p in paste)]
    return sorted(kept + paste)


def moved_values(mode, before, a, b):
    """{time after: value} the old keys must keep in `mode` (the paste's own frames aside)."""
    times, values = before
    n = b - a + 1
    out = {}
    for t, v in zip(times, values):
        if mode == "replace" and (t < a - 1e-6 or t > b + 1e-6):
            out[t] = v
        elif mode == "insert":
            out[t + n if t >= a - 1e-6 else t] = v
        elif mode == "merge" and not (a - 1e-6 <= t <= b + 1e-6 and abs(t - round(t)) < 1e-6):
            out[t] = v
    return out


def phase_modes():
    cards()
    b = need("B")
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    a_, b_ = MODES_AT, MODES_AT + count - 1
    members_t, _p, _bb = target_members(header, b, card_bones(card, 0))
    for layered in (False, True):
        for mode in animdata.MODES:
            label = "%s%s" % (mode, " on an additive layer" if layered else "")
            b.wipe()
            b.place()
            key_take(b, TAKE)
            layer = None
            if layered:
                layer = cmds.animLayer("AnimTake")
                key_take(b, TAKE, layer=layer, seed=3.1)
                cmds.animLayer(layer, edit=True, selected=True, preferred=True)
            base = "BaseAnimation" if layered else None
            before_active = dict((p, curve_keys(p, layer)) for p in b.plugs)
            before_base = dict((p, curve_keys(p, base)) for p in b.plugs) if layered else {}
            take_ok = all(len(k[0]) == len(TAKE) for k in before_active.values())
            go(MODES_AT)
            ok, text = animapply.apply(header, frames, selection=b.selection(),
                                       options=animdata.Options(mode=mode))
            say("   %s: %s" % (label, text))
            written = keyed_plugs(b, a_ + 1, layer)
            bad, unwritten = [], []
            for plug in b.plugs:
                after = curve_keys(plug, layer)
                if plug in written:
                    want = expected_times(mode, before_active[plug][0], a_, b_)
                    keep = moved_values(mode, before_active[plug], a_, b_)
                    got = dict(zip(after[0], after[1]))
                    if not same_times(after[0], want) or any(
                            abs(got.get(t, 1e9) - v) > 1e-9 for t, v in keep.items()):
                        bad.append(plug)
                elif after != before_active[plug]:
                    unwritten.append(plug)
            base_moved = [p for p in before_base if curve_keys(p, base) != before_base[p]]
            gate("modes %s: every written curve exactly the mode's, the plugs not written key "
                 "for key%s" % (label, ", the base key for key" if layered else ""),
                 ok and take_ok and len(written) > 50 and not bad and not unwritten and
                 not base_moved,
                 "%d written (%d off the mode), %d not written changed %s, base %d moved; "
                 "the take %s | %s" % (len(written), len(bad), len(unwritten),
                                       [p.split("|")[-1] for p in (bad + unwritten)[:3]],
                                       len(base_moved), take_ok, text))
            deg, cm = paste_rows(b, card, [(a_, 0), (a_ + 11, 11), (b_, count - 1)],
                                 members_t)
            gate("modes %s: the pose on the card at 60 / 71 / 83" % label,
                 deg.value <= 0.01 and cm.value <= 0.01, "%s deg, %s cm" % (deg, cm))
            if layered:
                cmds.delete(layer)
            b.wipe()
    left = [p for p in b.plugs if keys.feed_of(p)[0] != "free"]
    gate("modes cleaned up: no layer, no curve on B", not cmds.ls(type="animLayer") and not left,
         "%d plugs still fed" % len(left))


# ------------------------------------------------------------------ options

def phase_options():
    cards()
    b = need("B")
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    members_t, _p, _bb = target_members(header, b, card_bones(card, 0))
    scale = body_scale(header["bones"], b.bones())
    # ---- At current time off: the clip on its own frames
    b.wipe()
    b.place()
    go(AT)
    ok, text = animapply.apply(header, frames, selection=b.selection(),
                               options=animdata.Options(at_current=False))
    say("   at current off: %s" % text)
    written = keyed_plugs(b, START + 1)
    wrong = [p for p in written if not same_times(curve_keys(p)[0],
                                                  [float(t) for t in range(START, END + 1)])]
    deg, cm = paste_rows(b, card, [(START + i, i) for i in (0, 11, 23)], members_t)
    gate("options At current time off: keys on the clip's own frames 0..23, the pose on them",
         ok and len(written) > 50 and not wrong and deg.value <= 0.01 and
         not keyed_plugs(b, AT),
         "%d written, %d off 0..23; %s deg | %s" % (len(written), len(wrong), deg, text))
    # ---- a sub-range 5..9 at 50
    b.wipe()
    b.place()
    go(AT)
    place = target_place(b)
    ok, text = animapply.apply(header, frames, selection=b.selection(),
                               options=animdata.Options(start=5, end=9))
    say("   sub-range: %s" % text)
    written = keyed_plugs(b, AT + 1)
    wrong = [p for p in written if not same_times(curve_keys(p)[0],
                                                  [float(AT + k) for k in range(5)])]
    span = [(AT + k, 5 + k) for k in range(5)]
    deg, cm = paste_rows(b, card, span, members_t)
    other, _c = paste_rows(b, card, [(AT, 0)], members_t)
    rcm, rdeg = root_rows(b, card, span, 5, place, scale)
    gate("options a sub-range 5..9 at 50: keys on 50..54, B on A's 5..9, its root travelling "
         "from frame 5", ok and len(written) > 50 and not wrong and deg.value <= 0.01 and
         other.value > 1.0 and rcm.value <= 0.01 and rdeg.value <= 0.01,
         "%d written, %d off; %s deg (against A's 0: %s); root %s cm %s deg | %s" % (
             len(written), len(wrong), deg, other, rcm, rdeg, text))
    # ---- Connect: B standing in another pose (static), the plain paste first, undone
    # the solve's own dependence on the pose the rig stands in when each frame is solved: the
    # same plain paste from B's build pose (a frame's solve samples the rig's constants there -
    # L, O_g - and the rig's scale chain makes them wander with the pose; measured 0.0012 deg
    # at FKMiddleFinger3_R.rotateX, every frame of the solve within its 0.01-deg tolerance)
    b.wipe()
    b.place()
    go(AT)
    ok, _t = animapply.apply(header, frames, selection=b.selection())
    from_build = dict((p, curve_keys(p)) for p in keyed_plugs(b, AT))
    b.wipe()
    b.place()
    set_values(pose_values(b, seed=1.3))
    evaluate()
    go(AT)
    stood = values_of(b.plugs)
    go(AT)
    ok, plain_text = animapply.apply(header, frames, selection=b.selection())
    plain_written = keyed_plugs(b, AT)
    plain = dict((p, curve_keys(p)) for p in plain_written)
    dependence, dependence_cm = Worst(), Worst()
    for plug, (times, values) in plain.items():
        if plug in from_build:
            for v, w in zip(values, from_build[plug][1]):
                # a rotation's euler may come back a whole turn away from another start
                if plug.endswith(ROT):
                    dependence.see(abs((v - w + 180.0) % 360.0 - 180.0), plug.split("|")[-1])
                else:
                    dependence_cm.see(abs(v - w), plug.split("|")[-1])
    cmds.undo()
    left = keyed_plugs(b, AT)
    go(AT)
    ok, text = animapply.apply(header, frames, selection=b.selection(),
                               options=animdata.Options(connect=True))
    say("   connect: %s" % text)
    # the positive control of «no worst»: the connected paste does stand off the card at its
    # first frame (it keeps what B showed) - a measure against the transfer would read this
    off, _c = paste_rows(b, card, [(AT, 0)], members_t)
    main = cmds.ls(b.rig.main, long=True)[0]
    written = keyed_plugs(b, AT)
    first, steady, steady_cm = Worst(), Worst(), Worst()
    for plug in written:
        if plug.rsplit(".", 1)[0] == main:
            continue
        times, values = curve_keys(plug)
        first.see(abs(values[0] - stood[plug]), plug.split("|")[-1])
        if plug in plain:
            constant = values[0] - plain[plug][1][0]
            into = steady if plug.endswith(ROT) else steady_cm
            for v, w in zip(values, plain[plug][1]):
                into.see(abs(v - w - constant), plug.split("|")[-1])
    gate("options Connect: the first keyed value of every channel is what it showed",
         ok and len(written) > 50 and first.value <= 1e-3 and not left,
         "%d written, worst %s (the plain paste undone: %d keys left at 50)" % (
             len(written), first, len(left)))
    # each frame's solve samples the rig as it stands there, and the connected take stands off
    # the plain one by the offsets: the keys agree to the solve's own dependence on the pose it
    # starts from (`dependence`, the plain paste from two poses, measured this run) - tied to
    # it, twice it with a floor of 1e-4 (the final review, S16: the solver's whole tolerance,
    # 0.01, would let a Connect off by 25x the measured dependence pass)
    bound, bound_cm = max(2.0 * dependence.value, 1e-4), max(2.0 * dependence_cm.value, 1e-4)
    gate("options Connect: every later key the plain paste's plus one constant per channel "
         "(within twice the solve's own dependence on its start)",
         steady.value <= bound and steady_cm.value <= bound_cm and
         dependence.value <= rigsolve.TOL_DEG and dependence_cm.value <= rigsolve.TOL_CM,
         "worst %s deg (bound %.6f), %s cm (bound %.6f) over %d channels; the plain paste "
         "itself from the build pose vs from this pose: %s deg, %s cm" % (
             steady, bound, steady_cm, bound_cm, len(plain), dependence, dependence_cm))
    gate("options Connect: no «worst» said, while the pasted pose stands off the card's first "
         "frame (a measure against the transfer would read that) and the plain paste is measured",
         "worst" not in text and off.value > 5.0 and "worst" in plain_text,
         "B stands %s deg off the card at 50 | the plain paste said: %s" % (off, plain_text))
    # ---- Source keys: only on the card's key times
    b.wipe()
    b.place()
    go(AT)
    ok, text = animapply.apply(header, frames, selection=b.selection(),
                               options=animdata.Options(keys="source"))
    say("   source keys: %s" % text)
    want = [AT + t - START for t in header["key_times"]]
    written = keyed_plugs(b, AT)
    wrong = [p for p in written if not same_times(curve_keys(p)[0], want)]
    deg, cm = paste_rows(b, card, [(AT + t - START, int(t) - START) for t in
                                   header["key_times"]], members_t)
    gate("options Source keys: keys only on the card's key times moved to 50, the pose there",
         ok and len(written) > 50 and not wrong and deg.value <= 0.01 and len(want) < count,
         "%d written on %s, %d off; %s deg | %s" % (len(written), want, len(wrong), deg, text))
    b.wipe()


# ------------------------------------------------------------------ cross

def phase_cross():
    cards()
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    for label in ("C", "O", "S", "CS"):
        ch = need(label)
        ch.wipe()
        ch.place()
        bones = ch.bones()
        go(AT)
        place = target_place(ch)
        source0 = card_bones(card, 0)
        members_t, pairs, _t = target_members(header, ch, source0)
        twin = pm.twin(pairs, source0, bones)
        children = direction_children(pairs, source0, bones)
        before = pointing(source0, ch, members_t, pairs, bones, children)
        lengths_before = lengths(bones)
        scale = body_scale(header["bones"], bones)
        t0 = time.time()
        ok, text = animapply.apply(header, frames, selection=ch.selection())
        took = (time.time() - t0) / count
        if label == "S":
            SPEED["skeleton"] = took
        say("   cross %s (%.3f s a frame): %s" % (label, took, text))
        rows, lens, actual, wander = Worst(), Worst(), Worst(), Worst()
        pelvis = skelsolve_pelvis(bones)
        top = pm.root_of(bones)
        for t, i in span:
            go(t)
            src = card_bones(card, i)
            found = twin_turns(src, ch, members_t, pairs, bones) if twin else \
                pointing(src, ch, members_t, pairs, bones, children, first=source0)
            d, _c, at, _a = worst_of(found)
            rows.see(d, "%s @%g" % (at, t))
            if not twin:
                d, _c, at, _a = worst_of(pointing(src, ch, members_t, pairs, bones, children))
                actual.see(d, "%s @%g" % (at, t))
                d, _c, at, _a = worst_of(drift(src, source0, ch, members_t, pairs, bones,
                                               children))
                wander.see(d, "%s @%g" % (at, t))
            now_len = lengths(bones)
            for leaf, length in lengths_before.items():
                if leaf in (pelvis, top) or pm.is_helper(leaf):
                    continue
                lens.see(abs(now_len[leaf] - length), "%s @%g" % (leaf, t))
        d0, _c, at0, _a = worst_of(before)
        name = ch.ref.label
        if twin:
            gate("cross %s (a twin): every member turned as the source's, every frame" % name,
                 ok and rows.value <= 0.01 and d0 > 5.0,
                 "%s deg (before the paste: %.3f)" % (rows, d0))
        else:
            # where the source's bone points: its first frame's direction carried by its turn -
            # the rest alignment is read ONCE, off the first pasted frame (spec, "Per frame");
            # against its child as it stands the gate reads the card's own wander as well
            # (`drift`, the card's data alone: Manny_Rig's neck_02 -> head 0.3195 deg, measured)
            gate("cross %s: every paired member points where the source's does, every frame"
                 % name, ok and rows.value <= 0.1 and d0 > 5.0,
                 "%s deg over %d members (before the paste %.3f at %s); against the source's "
                 "children as they stand %s deg - the card's own children wander up to %s deg "
                 "in their parents' frames" % (rows, len(members_t), d0, at0, actual, wander))
        gate("cross %s: lengths unchanged (pelvis, root and helpers aside)" % name,
             lens.value <= 1e-4, "%s cm" % lens)
        rcm, rdeg = root_rows(ch, card, span, 0, place, scale)
        go(AT + count - 1)
        moved = (pm.position(target_place(ch)) - pm.position(place)).length()
        library_scale = pm.scale_between(source0, bones, pairs)
        gate("cross %s: the root on the travel carried through the root rests, scaled" % name,
             rcm.value <= 0.01 and rdeg.value <= 0.01 and moved > 50.0 and
             abs(library_scale - scale) < 1e-9,
             "%s cm, %s deg; travelled %.2f cm; scale %.4f (posemath %.4f)" % (
                 rcm, rdeg, moved, scale, library_scale))
        ch.wipe()


def skelsolve_pelvis(bones):
    for leaf in sorted(bones):
        if (bones[leaf] or {}).get("canonical") == "pelvis":
            return leaf
    return "pelvis" if "pelvis" in bones else None


# ------------------------------------------------------------------ mirror

def opposite(leaf):
    if leaf.endswith("_l"):
        return leaf[:-1] + "r"
    if leaf.endswith("_r"):
        return leaf[:-1] + "l"
    return leaf


def phase_mirror():
    cards()
    b = need("B")
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    b.wipe()
    b.place()
    go(AT)
    place = target_place(b)
    ok, text = animapply.apply(header, frames, selection=b.selection(), mirror=True)
    say("   mirror: %s" % text)
    rests = header["bones"]
    root = pm.root_of(rests)
    flip, axis = reflection(rests)
    members = [m for m in header["members"] if not pm.is_twist(m) and m != root]
    game = b.game()
    on_parent, pelvis_off, pelvis_ctl = Worst(), Worst(), Worst()
    control = Worst()
    for t, i in span:
        go(t)
        src = card_bones(card, i)
        drives = rigsolve.drive_matrices(b.rig)
        p_root = pm.matrix(src[root]["world"])
        r_root = pm.rotation(rests[root]["rest"])

        def key_of(leaf):
            return "drive" if src[leaf].get("drive") else "world"

        def mirrored(leaf):
            """The card's bone mirrored, in its root's space: r_x . F . (r_o^-1 . p_o) . F."""
            if leaf == root:
                return om.MMatrix()
            other = opposite(leaf) if opposite(leaf) in src else leaf
            r_x = pm.rotation(rests[leaf]["rest"]) * r_root.inverse()
            r_o = pm.rotation(rests[other]["rest"]) * r_root.inverse()
            p_o = pm.rotation(src[other][key_of(other)]) * pm.rotation(p_root).inverse()
            return r_x * flip * (r_o.inverse() * p_o) * flip

        def shown(leaf):
            if key_of(leaf) == "drive":
                return pm.rotation(drives[leaf])
            return pm.rotation(W(game[leaf]))

        def own(leaf):
            return pm.rotation(src[leaf][key_of(leaf)]) * pm.rotation(p_root).inverse()

        for leaf in members:
            parent = rests[leaf]["parent"]
            want = mirrored(leaf) * mirrored(parent).inverse()
            got = shown(leaf) * shown(parent).inverse()
            on_parent.see(pm.angle(got, want), "%s @%g" % (leaf, t))
            unmirrored = own(leaf) * (own(parent) if parent != root else om.MMatrix()).inverse()
            control.see(pm.angle(got, unmirrored), "%s @%g" % (leaf, t))
        d = (pm.position(src["pelvis"]["world"]) - pm.position(p_root)) * \
            pm.rotation(p_root).inverse()
        g_root = W(game[root])
        got = (pm.position(W(game["pelvis"])) - pm.position(g_root)) * \
            pm.rotation(g_root).inverse()
        pelvis_off.see((got - d * flip).length(), "@%g" % t)
        pelvis_ctl.see((got - d).length(), "@%g" % t)          # unmirrored: the control
    gate("mirror every member on its parent the mirror of the card's opposite, every frame",
         ok and on_parent.value <= 0.01 and control.value > 1.0,
         "%s deg; unmirrored it would read %s deg" % (on_parent, control))
    gate("mirror the pelvis's offset from the root mirrored", pelvis_off.value <= 0.01 and
         pelvis_ctl.value > 1.0, "%s cm; unmirrored it would read %s cm" % (pelvis_off,
                                                                            pelvis_ctl))
    rcm, rdeg = root_rows(b, card, span, 0, place, 1.0, flip)
    first = card_bones(card, 0)
    s0 = root_frames(first)[0]
    sideways, forward = Worst(), Worst()
    largest = 0.0
    for t, i in span:
        go(t)
        d_a = (pm.position(root_frames(card_bones(card, i))[0]) - pm.position(s0)) * \
            pm.rotation(s0).inverse()
        d_b = (pm.position(target_place(b)) - pm.position(place)) * \
            pm.rotation(place).inverse()
        across_a, across_b = d_a * axis, d_b * axis
        largest = max(largest, abs(across_a))
        sideways.see(abs(across_b + across_a), "@%g" % t)
        forward.see(((d_b - axis * across_b) - (d_a - axis * across_a)).length(), "@%g" % t)
    gate("mirror the root on the travel reflected (F . L . F): the sideways step negated, the "
         "rest kept", rcm.value <= 0.01 and rdeg.value <= 0.01 and sideways.value <= 0.01 and
         forward.value <= 0.01 and largest > 10.0,
         "%s cm %s deg; sideways %s cm off its negation (A's up to %.2f cm), the rest %s cm" % (
             rcm, rdeg, sideways, largest, forward))
    b.wipe()
    mirror_cross(card, span)


def target_directions(ch, bones, children, members):
    """{leaf: unit direction} of each member toward its direction child as the target stands
    now, in its root frame's REST axes."""
    now = dict((leaf, W(b["path"])) for leaf, b in bones.items())
    t_pose, t_rest = root_frames(bones, now[pm.root_of(bones)])
    t_frame = pm.rotation(t_pose).inverse() * pm.rotation(t_rest)
    out = {}
    for leaf in members:
        child = children.get(leaf)
        if child is None or child not in now or leaf not in now:
            continue
        out[leaf] = ((pm.position(now[child]) - pm.position(now[leaf])) * t_frame).normal()
    return out


def asymmetry(first, header, ch, members, pairs, children, bones):
    """{target leaf: deg}: the card's own left/right asymmetry at its first frame, the card's
    data alone - the direction toward its partner child of each member's partner (read in its
    own P frame, turned to its rest orientation, in the root's rest axes) against the sagittal
    reflection of its opposite's. Manny_Rig's neck_02 -> head: 0.287 deg (the in-between rolls
    with half the head's twist), the thighs 0.096 (its 0.07-cm calf), measured."""
    p = _poses(first, ch, bones, pairs)
    root = pm.root_of(first)
    root_rest = pm.rotation(first[root]["rest"])
    flip, _axis = reflection(header["bones"])

    def rest_dir(s, sc):
        local = (pm.position(first[sc]["world"]) - pm.position(first[s]["world"])) * \
            pm.rotation(p[s]).inverse()
        return local * pm.rotation(first[s]["rest"]) * root_rest.inverse()
    out = {}
    for leaf in members:
        child = children.get(leaf)
        if child is None or leaf not in pairs or child not in pairs:
            continue
        s, sc = pairs[leaf], pairs[child]
        o, oc = opposite(s), opposite(sc)
        if o in first and oc in first:
            out[leaf] = pm.direction_angle(rest_dir(s, sc), rest_dir(o, oc) * flip)
    return out


def mirror_cross(card, span):
    """The card mirrored onto a NON-twin (Creep_Rig): the spec reads its rest alignment off the
    clip's first frame UNMIRRORED - «it fixes the mirrored non-twin case, mirrored rotations
    against unmirrored positions». So the mirrored paste stands as the plain paste's reflection:
    each member's direction (its root frame's rest axes) the target's sagittal reflection of its
    opposite's in the plain paste, every frame - but for the card's own left/right asymmetry
    where the alignment reads it (`asymmetry`): the mirrored left bone takes its OWN side's
    alignment under the reflected right's turn, so the two differ by exactly that angle, the
    same on every frame (a turn carries both directions alike)."""
    header, frames = card
    c = need("C")
    bones = c.bones()
    source0 = card_bones(card, 0)
    members_t, pairs, _t = target_members(header, c, source0)
    children = direction_children(pairs, source0, bones)
    flip, _axis = reflection(bones)
    expected = asymmetry(source0, header, c, members_t, pairs, children, bones)
    shown, lines = {}, []
    for mirrored in (False, True):
        c.wipe()
        c.place()
        go(AT)
        ok, text = animapply.apply(header, frames, selection=c.selection(), mirror=mirrored)
        lines.append(ok)
        say("   %s onto %s: %s" % ("mirrored" if mirrored else "plain", c.ref.label, text))
        shown[mirrored] = {}
        for t, _i in span:
            go(t)
            shown[mirrored][t] = target_directions(c, bones, children, members_t)
    worst, residue, control, own = Worst(), Worst(), Worst(), Worst()
    for t, _i in span:
        plain, mirrored = shown[False][t], shown[True][t]
        for leaf, direction in mirrored.items():
            other = opposite(leaf)
            if other not in plain or leaf not in expected:
                continue
            angle = pm.direction_angle(direction, plain[other] * flip)
            worst.see(angle, "%s @%g" % (leaf, t))
            residue.see(abs(angle - expected[leaf]), "%s @%g" % (leaf, t))
            own.see(expected[leaf], leaf)
            if other != leaf:
                control.see(pm.direction_angle(direction, plain[leaf]), "%s @%g" % (leaf, t))
    gate("mirror onto a non-twin (Creep_Rig): every member the reflection of its opposite in the "
         "plain paste, every frame, but for the card's own asymmetry",
         all(lines) and residue.value <= 0.01 and worst.value <= own.value + 0.01 and
         control.value > 5.0,
         "off the card's own asymmetry by %s deg over %d members (the reflection itself %s deg, "
         "the card's asymmetry up to %s deg); against its own side unreflected %s deg" % (
             residue, len(expected), worst, own, control))
    c.wipe()


# ------------------------------------------------------------------ blend

def _q(values, order):
    return om.MEulerRotation(*([math.radians(v) for v in values] + [order])).asQuaternion()


def _qangle(a, b):
    d = a.inverse() * b
    v = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return math.degrees(2.0 * math.atan2(v, abs(d.w)))


def phase_blend():
    cards()
    b = need("B")
    header, frames = CARDS["full"]
    count = END - START + 1
    span = [AT + i for i in range(count)]
    b.wipe()
    b.place()
    for t, seed in ((40, 2.2), (100, 2.9)):
        for plug, value in pose_values(b, seed).items():
            cmds.setKeyframe(plug, time=t, value=value)
    evaluate()
    before = {}
    for t in span:
        go(t)
        before[t] = values_of(b.plugs)
    go(AT)
    ok, text = animapply.apply(header, frames, selection=b.selection())
    written = keyed_plugs(b, AT)
    card = dict((p, dict(zip(*curve_keys(p)))) for p in written)
    cmds.undo()
    undone = keyed_plugs(b, AT + 1)
    go(AT)
    blend = animapply.Blend()
    refusal = blend.start(header, frames, selection=b.selection())
    blend.set(0.8)
    blend.set(0.5)
    text = blend.finish()
    say("   blend: %s" % text)
    now = dict((p, dict(zip(*curve_keys(p)))) for p in written)
    nodes = {}
    for plug in written:
        node, attr = plug.rsplit(".", 1)
        if attr in ROT:
            nodes.setdefault(node, set()).add(attr)
    turns, whole, moves = Worst(), Worst(), Worst()
    for node, attrs in nodes.items():
        if len(attrs) != 3:
            continue
        order = int(cmds.getAttr(node + ".rotateOrder"))
        plugs = [node + "." + a for a in ROT]
        for t in span:
            q0 = _q([before[t][p] for p in plugs], order)
            q1 = _q([card[p][t] for p in plugs], order)
            qn = _q([now[p][t] for p in plugs], order)
            all_way = _qangle(q0, q1)
            turns.see(max(abs(_qangle(q0, qn) - 0.5 * all_way),
                          abs(_qangle(qn, q1) - 0.5 * all_way)),
                      "%s @%g" % (node.split("|")[-1], t))
            whole.see(all_way, node.split("|")[-1])
    whole_move = Worst()
    for plug in written:
        if plug.rsplit(".", 1)[1] in ROT:
            continue
        for t in span:
            moves.see(abs(now[plug][t] - (before[t][plug] + 0.5 * (card[plug][t] -
                                                                    before[t][plug]))),
                      "%s @%g" % (plug.split("|")[-1], t))
            whole_move.see(abs(card[plug][t] - before[t][plug]), plug.split("|")[-1])
    # `card` is the plain paste's solve from the take; the blended paste solves each frame from
    # the blended pose standing there, and a solve's values depend on the pose it starts from
    # to well within its tolerance (the options phase's `dependence`; here the IK pole's place,
    # read on the plane of the chain as it stands: 0.0002 cm, measured) - so the halves agree to
    # the solver's tolerance (rigsolve.TOL_DEG / TOL_CM)
    gate("blend at 50 %: every keyed rotation halfway between the take and the card, every "
         "frame", ok and refusal == "" and not undone and turns.value <= rigsolve.TOL_DEG and
         whole.value > 5.0 and "at 50 %" in text,
         "%s deg off half over %d controls (the largest whole turn %s) | %s" % (
             turns, len(nodes), whole, text))
    gate("blend at 50 %: every translation and other channel halfway",
         moves.value <= rigsolve.TOL_CM and whole_move.value > 1.0,
         "%s off half (the largest whole move %s)" % (moves, whole_move))
    b.wipe()


# ------------------------------------------------------------------ objects

def locator(name, values=None):
    node = cmds.ls(cmds.spaceLocator(name=name)[0], long=True)[0]
    for attr, value in (values or {}).items():
        cmds.setAttr(node + "." + attr, value)
    return node


def full_keys(curve):
    """[[t, v, in type, out type, in angle, in weight, out angle, out weight]] of a curve."""
    columns = [cmds.keyframe(curve, query=True, timeChange=True) or [],
               cmds.keyframe(curve, query=True, valueChange=True) or []]
    for flag in ("inTangentType", "outTangentType", "inAngle", "inWeight", "outAngle",
                 "outWeight"):
        columns.append(cmds.keyTangent(curve, query=True, **{flag: True}) or [])
    return [list(key) for key in zip(*columns)]


def own_curve(plug):
    return keys.curve_for(plug, None)


def evaluated(curve, t):
    return cmds.keyframe(curve, query=True, eval=True, time=(t, t))[0]


def phase_objects():
    src = locator("animSrc")
    tx = src + ".translateX"
    for t, v in ((0, 0.0), (10, 10.0), (20, 5.0)):
        cmds.setKeyframe(tx, time=t, value=v)
    curve = own_curve(tx)
    cmds.keyTangent(curve, edit=True, weightedTangents=True)
    cmds.keyTangent(curve, edit=True, time=(10, 10), lock=False, outAngle=30.0, outWeight=5.0)
    for attr, value in (("translateY", 2.0), ("rotateY", 25.0), ("visibility", 1.0)):
        cmds.setAttr(src + "." + attr, value)
    source_keys = full_keys(curve)
    raw, raw_frames, note = animcapture.build_animation([src], start=0, end=20)
    say("   objects card: %s" % note)
    header, _f, _p = through_disk("Slide", raw, None)
    attrs = header["objects"][0]["attrs"]
    gate("objects the card: tx a curve of 3 keys, weighted, the free channels static",
         header["kind"] == "objects" and raw_frames is None and
         len(attrs["translateX"]["keys"]) == 3 and attrs["translateX"]["weighted"] and
         attrs["visibility"] == {"static": 1.0} and attrs["translateY"] == {"static": 2.0},
         "tx %s, visibility %s" % (attrs["translateX"].get("keys"), attrs.get("visibility")))
    # ---- plain: onto another locator at 30
    dst = locator("animDst")
    go(30)
    ok, text = animapply.apply(header, None, selection=[dst])
    say("   objects onto another locator: %s" % text)
    got = full_keys(own_curve(dst + ".translateX"))
    want = [[k[0] + 30] + k[1:] for k in source_keys]
    off = max(abs(a - b) if isinstance(a, float) else (0.0 if a == b else 1e9)
              for g, w in zip(got, want) for a, b in zip(g, w)) if len(got) == len(want) \
        else 1e9
    weighted = cmds.keyTangent(own_curve(dst + ".translateX"), query=True,
                               weightedTangents=True)[0]
    gate("objects keys on 30 / 40 / 50: the source's values, tangent types, the fixed angle and "
         "weight, the curve weighted", ok and off <= 1e-6 and weighted and
         abs(got[1][6] - 30.0) < 1e-6 and abs(got[1][7] - 5.0) < 1e-6,
         "worst %.3g; out tangent at 40: %s / %s | %s" % (off, got[1][6] if len(got) > 1 else
                                                         None, got[1][7] if len(got) > 1 else
                                                         None, text))
    shape, control = 0.0, 0.0
    dst_curve = own_curve(dst + ".translateX")
    for k in range(81):
        x = k * 0.25
        shape = max(shape, abs(evaluated(dst_curve, 30 + x) - evaluated(curve, x)))
        control = max(control, abs(evaluated(dst_curve, x + 30) - evaluated(curve, x + 0.75)))
    gate("objects the pasted curve is the source's at every quarter frame, shifted to 30",
         shape <= 1e-6 and control > 0.1, "%.3g (a 0.75-frame slip would read %.3f)" % (
             shape, control))
    statics = []
    for attr, value in (("translateY", 2.0), ("rotateY", 25.0), ("visibility", 1.0)):
        times, values = curve_keys(dst + "." + attr)
        statics.append(times == (30.0,) and abs(values[0] - value) < 1e-9)
    gate("objects every free channel one key at 30 with the source's value", all(statics),
         "%s" % statics)
    # ---- Replace / Insert over a take of the target's own
    take = ((25, 1.0), (35, 2.0), (45, 3.0), (60, 4.0))
    for mode, want in (("replace", [(25, 1.0), (30, 0.0), (40, 10.0), (50, 5.0), (60, 4.0)]),
                       ("insert", [(25, 1.0), (30, 0.0), (40, 10.0), (50, 5.0), (56, 2.0),
                                   (66, 3.0), (81, 4.0)])):
        node = locator("animTake_" + mode)
        for t, v in take:
            cmds.setKeyframe(node + ".translateX", time=t, value=v)
        go(30)
        ok, text = animapply.apply(header, None, selection=[node],
                                   options=animdata.Options(mode=mode))
        times, values = curve_keys(node + ".translateX")
        gate("objects %s over a take of its own: %s" % (mode, want),
             ok and same_times(times, [t for t, _v in want]) and
             all(abs(a - b[1]) < 1e-9 for a, b in zip(values, want)),
             "%s | %s" % (list(zip(times, values)), text))
        cmds.delete(node)
    # ---- a sub-range 3..14: a key inserted at each end, the shape kept
    node = locator("animPart")
    go(30)
    ok, text = animapply.apply(header, None, selection=[node],
                               options=animdata.Options(start=3, end=14))
    part = own_curve(node + ".translateX")
    times = curve_keys(node + ".translateX")[0]
    shape = max(abs(evaluated(part, 30 + k * 0.25) - evaluated(curve, 3 + k * 0.25))
                for k in range(45))
    gate("objects a sub-range 3..14 at 30: keys 30 / 37 / 41 (two inserted), the source's "
         "shape at every quarter frame", ok and same_times(times, [30.0, 37.0, 41.0]) and
         shape <= 1e-6, "%s, %.3g | %s" % (times, shape, text))
    cmds.delete(node)
    # ---- Connect: the first value is what the channel showed
    node = locator("animConnect", {"translateX": 7.0, "translateY": 3.0})
    go(30)
    ok, text = animapply.apply(header, None, selection=[node],
                               options=animdata.Options(connect=True))
    times, values = curve_keys(node + ".translateX")
    ty = curve_keys(node + ".translateY")
    gate("objects Connect: tx 7 / 17 / 12 at 30 / 40 / 50, ty its own 3",
         ok and same_times(times, [30.0, 40.0, 50.0]) and
         all(abs(a - b) < 1e-9 for a, b in zip(values, (7.0, 17.0, 12.0))) and
         ty == ((30.0,), (3.0,)), "%s, ty %s | %s" % (list(zip(times, values)), ty, text))
    for made in (src, dst, node):
        if cmds.objExists(made):
            cmds.delete(made)
    held_gates()


def held_gates():
    """Channels no plain curve holds, saved by sampling every frame (`animcapture._sampled`): a
    prop held by A's IK hand - a parent constraint riding the IK chain, the case trap 69 saw
    `getAttr(time=)` not pull in a GUI Maya - and a channel on an additive layer; the card's keys
    against the scene at every frame (a real time change), then pasted at 30 onto two free
    locators (by selection order) and read back there."""
    cards()
    a = need("A")
    held = locator("animHeld")
    cmds.parentConstraint(a.game()["hand_l"], held, maintainOffset=False)
    blend = a.node("FKIKArm_L") + ".FKIKBlend"
    blend_was = float(cmds.getAttr(blend))         # given back as it was, never a literal 0
    ik = a.node("IKArm_L")
    base = cmds.getAttr(ik + ".translate")[0]
    for f, d in ((0, 0.0), (12, 25.0), (23, -15.0)):
        for attr, value in zip(TR, base):
            cmds.setKeyframe(ik + "." + attr, time=f, value=value + d)
    cmds.setAttr(blend, 10)
    layered = locator("animLayered")
    for f, v in ((0, 0.0), (20, 10.0)):
        cmds.setKeyframe(layered + ".translateY", time=f, value=v)
    layer = cmds.animLayer("ObjLayer")
    cmds.animLayer(layer, edit=True, attribute=layered + ".translateY")
    for f, v in ((0, 5.0), (20, 25.0)):              # final values: the layer holds +5, +15
        cmds.setKeyframe(layered + ".translateY", time=f, value=v, animLayer=layer)
    evaluate()
    watched = [(held, a_) for a_ in TR] + [(layered, "translateY")]
    shown = {}
    for f in range(START, END + 1):
        go(f)
        shown[f] = [float(cmds.getAttr(n + "." + a_)) for n, a_ in watched]
    header, _f, note = animcapture.build_animation([held, layered], start=START, end=END)
    say("   held / layered card: %s" % note)
    stored = []
    for n, a_ in watched:
        record = [o for o in header["objects"] if o["path"] == n][0]
        stored.append(record["attrs"].get(a_, {}))
    off, moved = Worst(), 0.0
    for k, ((n, a_), curve) in enumerate(zip(watched, stored)):
        got = dict((key[0], key[1]) for key in curve.get("keys") or ())
        for f in range(START, END + 1):
            off.see(abs(got.get(float(f), 1e9) - shown[f][k]), "%s.%s @%d" % (
                n.split("|")[-1], a_, f))
            moved = max(moved, abs(shown[f][k] - shown[START][k]))
    gate("objects a prop held by an IK hand and a layered channel: sampled every frame, the "
         "card's keys the scene's", off.value <= 1e-6 and moved > 5.0,
         "worst %s (the channels move up to %.2f) | %s" % (off, moved, note))
    copies = [locator("animHeldCopy"), locator("animLayeredCopy")]
    cmds.animLayer(layer, edit=True, selected=False)
    drop_layers()
    go(30)
    ok, text = animapply.apply(header, None, selection=copies)
    pasted = Worst()
    for f in range(START, END + 1):
        go(30 + f - START)
        values = [float(cmds.getAttr(copies[0] + "." + a_)) for a_ in TR] + \
            [float(cmds.getAttr(copies[1] + ".translateY"))]
        for k, value in enumerate(values):
            pasted.see(abs(value - shown[f][k]), "@%d" % (30 + f - START))
    gate("objects the held prop's and the layered channel's card pasted at 30 onto two free "
         "locators: their values on every frame", ok and pasted.value <= 1e-6,
         "worst %s | %s" % (pasted, text))
    cmds.setAttr(blend, blend_was)
    cmds.cutKey(ik, attribute=list(TR), clear=True)
    for attr, value in zip(TR, base):
        cmds.setAttr(ik + "." + attr, value)
    for made in [held, layered] + copies:
        if cmds.objExists(made):
            cmds.delete(made)
    evaluate()


# ------------------------------------------------------------------ undo

def phase_undo():
    cards()
    a, b = need("A"), need("B")
    header, frames = CARDS["full"]
    b.wipe()
    b.place()
    for t, seed in ((40, 1.7), (100, 2.4)):
        for plug, value in pose_values(b, seed).items():
            cmds.setKeyframe(plug, time=t, value=value)
    prop = locator("undoProp")
    for t in (0, 100):
        cmds.setKeyframe(prop + ".translateX", time=t, value=0.0)
    marker = locator("undoMarker")
    go(AT)
    spine = long_plug(a.node("FKSpine1_M") + ".rotateX")
    tweaks = {spine: float(cmds.getAttr(spine)) + 25.0, prop + ".translateX": 40.0}
    set_values(tweaks)                           # autoKey off: unkeyed tweaks
    cmds.autoKeyframe(state=True)
    cmds.setAttr(marker + ".translateX", 1.0)    # the animator's last step
    before_values = values_of(b.plugs)
    before = curve_state()
    ok, text = animapply.apply(header, frames, selection=b.selection())
    say("   undo: %s" % text)
    pressed = values_of(list(tweaks))
    changed, gone, new = curves_same(before, curve_state())
    auto = cmds.autoKeyframe(query=True, state=True)
    gate("undo the press keyed B, the tweaks on A and on a prop stand, autoKey still on",
         ok and (changed or new) and auto and
         all(abs(pressed[p] - v) <= 1e-6 for p, v in tweaks.items()),
         "%d curves changed, %d new; tweaks %s" % (len(changed), len(new), [
             "%.4f" % pressed[p] for p in tweaks]))
    # no time change and no autoKey switch from here to the second Ctrl+Z: each is a step of
    # Maya's undo queue and would take a Ctrl+Z (the module docstring)
    cmds.undo()
    changed, gone, new = curves_same(before, curve_state())
    standing = values_of(list(tweaks))
    gate("undo one Ctrl+Z: every curve in the scene key for key, the tweaks still standing",
         not changed and not gone and not new and
         all(abs(standing[p] - v) <= 1e-6 for p, v in tweaks.items()),
         "curves %d changed %d gone %d new of %d; tweaks %s" % (
             len(changed), len(gone), len(new), len(before),
             ["%.4f" % standing[p] for p in tweaks]))
    cmds.undo()
    gate("undo the next Ctrl+Z takes the animator's step before the press back",
         abs(cmds.getAttr(marker + ".translateX")) < 1e-12,
         "marker tx %s" % cmds.getAttr(marker + ".translateX"))
    cmds.autoKeyframe(state=False)
    evaluate()
    after_values = values_of(b.plugs)
    worst = max(abs(after_values[p] - v) for p, v in before_values.items())
    at = max(before_values, key=lambda p: abs(after_values[p] - before_values[p]))
    gate("undo B's channels back exactly (read after a real time change)", worst <= 1e-9,
         "max %.3g (%s) over %d channels" % (worst, at.split("|")[-1], len(before_values)))
    # ---- Esc in the progress window on the third pasted frame (the spec: «Cancel undoes the
    # press's own chunk (everything back) and says so»), autoKey on, a tweak standing
    go(AT)
    set_values(tweaks)
    cmds.autoKeyframe(state=True)
    cmds.setAttr(marker + ".translateY", 2.0)    # the animator's last step
    before = curve_state()
    esc = Esc(3)
    ok, text = animapply.apply(header, frames, selection=b.selection(), progress=esc)
    say("   cancelled: %s" % text)
    changed, gone, new = curves_same(before, curve_state())
    standing = values_of(list(tweaks))
    auto = cmds.autoKeyframe(query=True, state=True)
    gate("undo Esc on the third frame: «cancelled», every curve key for key, the tweaks standing, "
         "autoKey on", not ok and text == animapply.CANCELLED and esc.steps == 3 and
         not changed and not gone and not new and auto and
         all(abs(standing[p] - v) <= 1e-6 for p, v in tweaks.items()),
         "%d steps; curves %d changed %d gone %d new; tweaks %s | %s" % (
             esc.steps, len(changed), len(gone), len(new),
             ["%.4f" % standing[p] for p in tweaks], text))
    cmds.undo()
    gate("undo after a cancel the next Ctrl+Z takes the animator's step back (the cancel left "
         "no step of its own)", abs(cmds.getAttr(marker + ".translateY")) < 1e-12,
         "marker ty %s" % cmds.getAttr(marker + ".translateY"))
    # ---- a Save walks the same way (animcapture): autoKey on, the tweaks standing
    go(AT)
    cmds.autoKeyframe(state=False)
    set_values(tweaks)
    cmds.autoKeyframe(state=True)
    cmds.setAttr(marker + ".translateZ", 3.0)    # the animator's last step
    before = curve_state()
    saved, saved_frames, note = animcapture.build_animation([a.rig.main], start=START, end=END)
    changed, gone, new = curves_same(before, curve_state())
    standing = values_of(list(tweaks))
    gate("undo a Save with autoKey on: no curve touched, the tweaks standing, autoKey on",
         saved_frames is not None and len(saved_frames["world"]) == END - START + 1 and
         not changed and not gone and not new and
         cmds.autoKeyframe(query=True, state=True) and
         all(abs(standing[p] - v) <= 1e-6 for p, v in tweaks.items()),
         "%s; curves %d changed %d gone %d new; tweaks %s" % (
             note, len(changed), len(gone), len(new), ["%.4f" % standing[p] for p in tweaks]))
    cmds.undo()
    gate("undo after a Save the next Ctrl+Z takes the animator's step back (the Save left no "
         "step of its own)", abs(cmds.getAttr(marker + ".translateZ")) < 1e-12 and
         all(abs(values_of(list(tweaks))[p] - v) <= 1e-6 for p, v in tweaks.items()),
         "marker tz %s" % cmds.getAttr(marker + ".translateZ"))
    cmds.autoKeyframe(state=False)
    for made in (prop, marker):
        cmds.delete(made)
    evaluate()
    b.wipe()
    undo_mark_gates(b, (header, frames))


def _no_marks(values):
    """`keys.undo_marks` before the final review's M1: the press's chunk opened with no mark."""
    return []


def undo_mark_gates(b, card):
    """The final review's M1: a paste OFF the current frame - At current time off (the clip on
    its own frames 0..23 while the scene stands at 90), Merge, and Replace onto channels with no
    key in 0..23 (B's take keys 40 / 60 / 70.5 / 80 / 100), and Merge at a fractional current
    time (89.5: the paste at 90) - then ONE Ctrl+Z right after the press (no time change between:
    it would take the undo): every one of B's channels, read at the current frame with no time
    change, shows what it showed before the press, and every curve is back key for key. Each
    frame's solve records its temporary sets at frames that are not the current one; undone
    backwards they used to leave every planned channel on the first pasted frame's value. The
    control: the same Merge with the chunk opened by no mark (the code before the fix)."""
    header, frames = card

    def press(options, now, marks=True):
        b.wipe()
        b.place()
        key_take(b, TAKE)
        go(now)
        before = values_of(b.plugs)
        curves = curve_state()
        if marks:
            ok, text = animapply.apply(header, frames, selection=b.selection(), options=options)
        else:
            with patched(keys, "undo_marks", _no_marks):
                ok, text = animapply.apply(header, frames, selection=b.selection(),
                                           options=options)
        written = len(keyed_plugs(b, animdata._frame(now) if options.at_current else START + 1))
        cmds.undo()
        shown = values_of(b.plugs)                    # the current frame, no time change
        changed, gone, new = curves_same(curves, curve_state())
        off, count = Worst(), 0
        for plug, value in before.items():
            d = abs(shown[plug] - value)
            off.see(d, plug.split("|")[-1])
            count += d > 1e-6
        return ok, text, written, off, count, (len(changed), len(gone), len(new))

    for label, options, now in (
            ("Merge, At current time off", animdata.Options(mode="merge", at_current=False), 90.0),
            ("Replace onto channels with no key in 0..23, At current time off",
             animdata.Options(mode="replace", at_current=False), 90.0),
            ("Merge at a fractional current time (the paste at 90)",
             animdata.Options(mode="merge"), 89.5)):
        ok, text, written, off, count, curves = press(options, now)
        say("   undo mark, %s: %s" % (label, text))
        gate("undo %s at %g, ONE Ctrl+Z: every channel shows what it showed before the press, "
             "every curve key for key" % (label, now),
             ok and written > 50 and off.value <= 1e-6 and curves == (0, 0, 0),
             "%d keyed; worst %s over %d channels, %d off; curves changed / gone / new %s" % (
                 written, off, len(b.plugs), count, curves))
    ok, text, written, off, count, curves = press(
        animdata.Options(mode="merge", at_current=False), 90.0, marks=False)
    gate("undo the control - Merge off the current frame with no undo mark (before the fix): "
         "the channels left on the first pasted frame's values, the gate above would fail",
         ok and written > 50 and off.value > 1.0 and count > 50,
         "worst %s, %d channels off | %s" % (off, count, text))
    b.wipe()


class Esc(object):
    """A progress window whose animator presses Esc at the `after`-th step (`timewalk.Progress`'s
    interface: `step(text)` answers False once cancelled)."""

    def __init__(self, after):
        self.after, self.steps = after, 0

    def step(self, text=""):
        self.steps += 1
        return self.steps < self.after


# ------------------------------------------------------------------ mixamo

MIXAMO_POSE = {   # our bone: delta on the local rotate channels, degrees
    "upperarm_l": (10, 25, -40), "upperarm_r": (-15, 20, 35), "lowerarm_l": (0, 40, 10),
    "lowerarm_r": (10, -35, 0), "clavicle_l": (0, 10, 12), "hand_r": (20, 0, 25),
    "thigh_l": (35, 5, 0), "thigh_r": (-30, 0, 8), "calf_l": (0, 0, 50), "calf_r": (40, 0, 0),
    "foot_l": (10, 0, 15), "spine_01": (5, 20, 0), "spine_05": (0, -10, 8),
    "neck_01": (10, 0, 0), "head": (15, 10, 0), "index_01_l": (0, 0, 30),
    "thumb_01_l": (20, 0, 0),
}


def build_mixamo(ns, factor=1.0):
    """The Mixamo fixture as joints in `ns` (`mixamorig:` names inside it) at `factor` of its
    size, oriented as Mixamo orients (Y down the bone, `yzx`), its T-pose rest in jointOrient,
    bound to a cube at that rest. (top, {ours: path})."""
    rows, expected = fixtures.build("mixamo")
    for full in sorted(set(":".join([ns] + n.split(":")[:-1]) for n, _p, _pos in rows)):
        parts = full.split(":")
        for i in range(1, len(parts) + 1):
            here = ":".join(parts[:i])
            if not cmds.namespace(exists=":" + here):
                cmds.namespace(add=parts[i - 1], parent=":" + ":".join(parts[:i - 1]))
    made = {}
    for name, parent, pos in rows:
        under = made.get(parent)
        kwargs = {"name": "%s:%s" % (ns, name), "skipSelect": True}
        if under:
            kwargs["parent"] = cmds.ls(under, long=True)[0]
        joint = cmds.createNode("joint", **kwargs)
        joint = cmds.ls(joint, long=True)[0]
        cmds.xform(joint, worldSpace=True, translation=[c * factor for c in pos])
        made[name] = cmds.ls(joint, uuid=True)[0]

    def path(name):
        return cmds.ls(made[name], long=True)[0]
    top = path(rows[0][0])
    cmds.joint(top, edit=True, orientJoint="yzx", secondaryAxisOrient="yup", children=True,
               zeroScaleOrient=True)
    joints = [path(n) for n in made]
    cube = cmds.polyCube(name=ns + ":body", constructionHistory=False)[0]
    cmds.skinCluster(joints + [cube], toSelectedBones=True)
    evaluate()
    return path(rows[0][0]), dict((o, path(n)) for o, n in expected.items())


def mixamo_card():
    """The Mixamo fixture at MIX_FACTOR, animated over 0..23 (its Hips travelling and turning,
    the limbs swinging), carded and hidden."""
    if "mixamo" in CARDS:
        return
    top, by_ours = build_mixamo("mxa", MIX_FACTOR)
    rest_rot = dict((p, cmds.getAttr(p + ".rotate")[0]) for p in by_ours.values())
    rest_t = cmds.getAttr(top + ".translate")[0]
    for n, f in enumerate(MIX_FRAMES):
        u = float(f - START) / (END - START)
        for ours, delta in MIXAMO_POSE.items():
            joint = by_ours.get(ours)
            if joint is None:
                continue
            weight = 0.3 + 0.7 * u + 0.15 * math.sin(2.0 * n)
            for channel, rest, d in zip(ROT, rest_rot[joint], delta):
                cmds.setKeyframe(joint + "." + channel, time=f, value=rest + d * weight)
        for channel, rest, d in zip(TR, rest_t, (MIX_TRAVEL[0] * u, 2.0 * math.sin(3.0 * n),
                                                 MIX_TRAVEL[2] * u)):
            cmds.setKeyframe(top + "." + channel, time=f, value=rest + d)
        for channel, rest, d in zip(ROT, rest_rot[top], (4.0 * math.sin(n), MIX_TURN * u, 0.0)):
            cmds.setKeyframe(top + "." + channel, time=f, value=rest + d)
    evaluate()
    header, frames, note = animcapture.build_animation([top], start=START, end=END)
    say("   mixamo card: %s; convention %s" % (note, header["character"]["convention"]))
    read, read_frames, _p = through_disk("Sweep", header, frames)
    CARDS["mixamo"] = (read, read_frames)
    cmds.setAttr(top + ".visibility", False)
    go(START)


def phase_mixamo():
    mixamo_card()
    b = need("B")
    card = CARDS["mixamo"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    b.wipe()
    b.place()
    go(AT)
    place = target_place(b)
    bones = b.bones()
    source0 = card_bones(card, 0)
    members_t, pairs, _t = target_members(header, b, source0)
    children = direction_children(pairs, source0, bones)
    scale = body_scale(header["bones"], bones)
    ok, text = animapply.apply(header, frames, selection=[b.rig.main])
    say("   mixamo onto Manny_Rig: %s" % text)
    gate("mixamo the card is rootless, its Hips the pelvis, keyed on 0 / 8 / 16 / 23",
         not pm.has_root(header["bones"]) and header["key_times"] == [float(t) for t in
                                                                      MIX_FRAMES],
         "has_root %s, key_times %s" % (pm.has_root(header["bones"]), header["key_times"]))
    rcm, rdeg = root_rows(b, card, span, 0, place, scale)
    library_scale = pm.scale_between(source0, bones, pairs)
    go(AT + count - 1)
    moved = (pm.position(target_place(b)) - pm.position(place)).length()
    gate("mixamo Main travels the Hips' ground travel, carried and scaled, every frame",
         ok and rcm.value <= 0.01 and rdeg.value <= 0.01 and abs(scale - 1.0) > 0.05 and
         abs(library_scale - scale) < 1e-9 and moved > 100.0,
         "%s cm, %s deg; scale %.4f (posemath %.4f); travelled %.2f cm" % (
             rcm, rdeg, scale, library_scale, moved))
    rows, wander = Worst(), Worst()
    for t, i in span[::4] + [span[-1]]:
        go(t)
        src = card_bones(card, i)
        found = pointing(src, b, members_t, pairs, bones, children, first=source0)
        d, _c, at, _a = worst_of(found)
        rows.see(d, "%s @%g" % (at, t))
        d, _c, at, _a = worst_of(drift(src, source0, b, members_t, pairs, bones, children))
        wander.see(d, "%s @%g" % (at, t))
    gate("mixamo every paired member points where the card's does", rows.value <= 0.1,
         "%s deg over %d members (the card's children wander %s deg)" % (
             rows, len(members_t), wander))
    b.wipe()
    rootless_target_gates()
    rolling_target_gates()


#  the rootless target's own take (the final review's M4): its Hips keyed walking and turning -
#  (frame, x, z, yaw about world Y) from its rest
WALK = ((40, 0.0, 0.0, 0.0), (60, 35.0, 50.0, 15.0), (80, 60.0, 110.0, 35.0),
        (100, 95.0, 160.0, 50.0))


def _ground_unread(target, time):
    """`animapply._Target.read_ground` before the final review's M4: nothing read before the
    ops, so each frame reads the ground off the top joint as the rewritten curve stands."""
    return None


def rootless_target_gates():
    """The final review's M4: a ROOTLESS target (the Mixamo fixture at its own size, a second
    one) walking along a take of its own - its Hips keyed walking and turning (WALK) - and A's
    full card pasted on it In place with Replace at 50: its ground frame (the floor under the
    Hips, turned by their heading - computed here, `root_frames`) on the take's own at every
    pasted frame, the take's read frame by frame before the press. Its Hips are a planned
    member: Replace cut their keys in 50..73 and every frame keyed them, so a ground read off
    them as they stand reads the curve the press is rewriting. The control: the same press with
    nothing read before the ops (the code before the fix)."""
    cards()
    card = CARDS["full"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    top, _ours = build_mixamo("mxw", 1.0)
    ch = Char("mxw", top)
    own = [top + "." + attr for attr in ROT + TR]

    def walk_take():
        ch.wipe()
        for f, x, z, yaw in WALK:
            for plug in own:
                cmds.setAttr(plug, ch.defaults[plug])
            cmds.rotate(0, yaw, 0, top, relative=True, worldSpace=True)
            cmds.move(x, 2.0 * math.sin(0.1 * f), z, top, relative=True, worldSpace=True)
            cmds.setKeyframe(own, time=f)
        evaluate()
        grounds = {}
        for t, _i in span:
            go(t)
            grounds[t] = target_place(ch)
        go(AT)
        return grounds

    grounds = walk_take()
    travelled = (pm.position(grounds[AT + count - 1]) - pm.position(grounds[AT])).length()
    turned = pm.angle(grounds[AT + count - 1], grounds[AT])
    options = animdata.Options(mode="replace", in_place=True)
    ok, text = animapply.apply(header, frames, selection=[top], options=options)
    say("   in place onto a walking rootless target: %s" % text)
    cut = same_times(curve_keys(top + ".translateX")[0],
                     [40.0] + [float(AT + i) for i in range(count)] + [80.0, 100.0])
    on, on_deg = Worst(), Worst()
    for t, _i in span:
        go(t)
        c, d = cm_deg(target_place(ch), grounds[t])
        on.see(c, "@%g" % t)
        on_deg.see(d, "@%g" % t)
    gate("mixamo In place, Replace onto a ROOTLESS target walking along its own take: its ground "
         "on the take's own at every pasted frame (its Hips keyed 50..73, the take's 60 cut)",
         ok and cut and on.value <= 0.01 and on_deg.value <= 0.01 and travelled > 50.0 and
         turned > 10.0,
         "%s cm, %s deg; the take's ground travels %.2f cm and turns %.2f deg over the paste | %s"
         % (on, on_deg, travelled, turned, text))
    grounds = walk_take()
    with patched(animapply._Target, "read_ground", _ground_unread):
        ok_c, text_c = animapply.apply(header, frames, selection=[top], options=options)
    off, off_deg = Worst(), Worst()
    for t, _i in span:
        go(t)
        c, d = cm_deg(target_place(ch), grounds[t])
        off.see(c, "@%g" % t)
        off_deg.see(d, "@%g" % t)
    gate("mixamo the control - the ground read off the curve the press rewrites (before the "
         "fix): off the take's own ground, the gate above would fail",
         ok_c and max(off.value, off_deg.value) > 1.0,
         "%s cm, %s deg | %s" % (off, off_deg, text_c))
    # ---- Insert (the re-review of the fix wave): the take's frames from INSERT_AT on move to
    # after the clip - every pasted frame stands on the take's ground at INSERT_AT, and the
    # shifted take resumes there (its key at INSERT_AT lands right after the clip). The control:
    # each pasted frame on the take's own ground there (before the fix) - the paste rides the
    # walk and the shifted take snaps it back
    insert_span = [(INSERT_AT + i, i) for i in range(count)]
    resume = INSERT_AT + count
    options = animdata.Options(mode="insert", in_place=True)

    def insert_press(control):
        grounds = walk_take()
        ground = grounds[INSERT_AT]
        go(INSERT_AT)
        if control:
            with patched(animapply, "_ground_time", _ground_time_as_before):
                ok, text = animapply.apply(header, frames, selection=[top], options=options)
        else:
            ok, text = animapply.apply(header, frames, selection=[top], options=options)
        shifted = same_times(curve_keys(top + ".translateX")[0],
                             [40.0] + [float(t) for t, _i in insert_span] +
                             [float(f + count) for f, _x, _z, _y in WALK if f >= INSERT_AT])
        on, on_deg = Worst(), Worst()
        for t in [t for t, _i in insert_span] + [resume]:
            go(t)
            c, d = cm_deg(target_place(ch), ground)
            on.see(c, "@%g" % t)
            on_deg.see(d, "@%g" % t)
        walked = (pm.position(grounds[AT + count - 1]) - pm.position(ground)).length()
        return ok, text, shifted, on, on_deg, walked

    ok, text, shifted, on, on_deg, walked = insert_press(False)
    say("   insert onto a walking rootless target: %s" % text)
    gate("mixamo In place, Insert at %d onto a ROOTLESS target walking along its own take: every "
         "pasted frame on the take's ground at %d, and so is the shifted take resuming at %d (its "
         "keys from %d on moved %d later)" % (INSERT_AT, INSERT_AT, resume, INSERT_AT, count),
         ok and shifted and on.value <= 0.01 and on_deg.value <= 0.01,
         "%s cm, %s deg; the take walks %.2f cm on from %d | %s" % (on, on_deg, walked,
                                                                    INSERT_AT, text))
    ok_c, text_c, shifted_c, off, off_deg, walked = insert_press(True)
    gate("mixamo the control - under Insert each pasted frame on the take's own ground there "
         "(before the fix): the paste rides the walk, the shifted take snaps it back at %d, the "
         "gate above would fail" % resume,
         ok_c and shifted_c and max(off.value, off_deg.value) > 10.0,
         "%s cm, %s deg | %s" % (off, off_deg, text_c))
    ch.wipe()
    cmds.setAttr(top + ".visibility", False)


INSERT_AT = 60                      # an Insert lands on the walk's key at 60 (rootless_target_gates)


def _ground_time_as_before(plan, time):
    """`animapply._ground_time` before the re-review of the fix wave: every pasted frame on the
    take's own ground there, Insert or not."""
    return time


#  the rolling card (the re-review of the fix wave): its Hips forward a frame, their side tilt
ROLL_STEP = 4.0
ROLL_TILT = 2.0
SWING_LIMIT = 120.0                 # deg off upright past which a heading is noise (computed here)
ROLL_AT = ((-60.0, 0.0, 90.0), 70.0)   # where the rolling card's target stands, and its turn


def rolling_card():
    """A Mixamo fixture at its own size rolling forward over its Hips: a full turn about world X
    over the take (0..23), a +-ROLL_TILT deg side tilt about world Z every other frame, no turn
    about Y, ROLL_STEP cm forward a frame - carded and hidden."""
    if "roll" in CARDS:
        return
    top, _ours = build_mixamo("mxr", 1.0)
    ch = Char("mxr", top)
    own = [top + "." + attr for attr in ROT + TR]
    count = END - START + 1
    for i in range(count):
        for plug in own:
            cmds.setAttr(plug, ch.defaults[plug])
        tilt = ROLL_TILT if i % 2 else -ROLL_TILT
        cmds.rotate(360.0 * i / count, 0.0, tilt, top, relative=True, worldSpace=True)
        cmds.move(0.0, 0.0, ROLL_STEP * i, top, relative=True, worldSpace=True)
        cmds.setKeyframe(own, time=START + i)
    evaluate()
    header, frames, note = animcapture.build_animation([top], start=START, end=END)
    say("   rolling card: %s" % note)
    read, read_frames, _p = through_disk("Roll", header, frames)
    CARDS["roll"] = (read, read_frames)
    cmds.setAttr(top + ".visibility", False)
    go(START)


def _yaw(turn):
    """The yaw (radians) of `heading(turn)`."""
    q = om.MTransformationMatrix(heading(turn)).rotation(asQuaternion=True)
    return 2.0 * math.atan2(q.y, q.w)


def _swing(turn):
    """How far `turn` tips world +Y off upright (deg): the swing of its swing-twist split."""
    up = om.MVector(0.0, 1.0, 0.0)
    return pm.direction_angle(up * pm.rotation(turn), up)


def _wrap(a):
    return a - 2.0 * math.pi * math.floor((a + math.pi) / (2.0 * math.pi))


def steadied_grounds(card):
    """[MMatrix]: the card's GROUND frame on every frame - the floor under its top joint, turned
    by the joint's heading since its rest (`root_frames`) - the heading held CONTINUOUS across
    the frames whose joint stands more than SWING_LIMIT deg off upright (there a 2 deg tilt reads
    as a half turn): such a frame takes the yaw interpolated, the short way, between the nearest
    frames within the limit on either side (by frame), the nearest one's at an end. Computed here,
    the spec's rule ("Root motion"), no posemath."""
    header, frames = card
    top = pm.root_of(header["bones"])
    rest = pm.matrix(header["bones"][top]["rest"])
    worlds = [card_bones(card, i)[top]["world"] for i in range(len(frames["world"]))]
    turns = [pm.rotation(rest).inverse() * pm.rotation(w) for w in worlds]
    good = [i for i, turn in enumerate(turns) if _swing(turn) <= SWING_LIMIT]
    yaw = dict((i, _yaw(turns[i])) for i in good)
    for before, after in zip(good, good[1:]):
        yaw[after] = yaw[before] + _wrap(yaw[after] - yaw[before])
    out = []
    for i, world in enumerate(worlds):
        if i not in yaw:
            lower = [g for g in good if g < i]
            upper = [g for g in good if g > i]
            if not lower:
                y = yaw[upper[0]]
            elif not upper:
                y = yaw[lower[-1]]
            else:
                a, b = lower[-1], upper[0]
                y = yaw[a] + (yaw[b] - yaw[a]) * float(i - a) / float(b - a)
        else:
            y = yaw[i]
        at = pm.position(pm.matrix(world))
        out.append(placed(om.MQuaternion(y, om.MVector(0.0, 1.0, 0.0)).asMatrix(),
                          (at.x, 0.0, at.z)))
    return out


_ON_GROUND = pm._on_ground


def _on_ground_own(turn, point, rest, ground, steadied=None):
    """`posemath._on_ground` before the re-review of the fix wave: the top joint's OWN heading
    taken off, whatever the source's root frame was steadied to."""
    return _ON_GROUND(turn, point, rest, ground)


def _body_on(card, ch, members_t, pairs, span, carry_of):
    """(worst deg, worst cm): every member bone of `ch` at each (t, i) of `span` against the
    card's partner at frame i carried by `carry_of(i)`, read after a real time change."""
    deg, cm = Worst(), Worst()
    bones = ch.bones()
    for t, i in span:
        go(t)
        src = card_bones(card, i)
        carry = carry_of(i)
        for leaf in members_t:
            want = pm.rigid(pm.matrix(src[pairs[leaf]]["world"]) * carry)
            got = pm.rigid(W(bones[leaf]["path"]))
            deg.see(pm.angle(got, want), "%s @%g" % (leaf, t))
            cm.see((pm.position(got) - pm.position(want)).length(), "%s @%g" % (leaf, t))
    return deg, cm


def rolling_target_gates():
    """The re-review of the fix wave: the final review's M3 steadied a rootless card's root
    heading across a roll's inverted frames - and a ROOTLESS target's top joint still took off
    its OWN heading, near upside down a 2 deg tilt read as a half turn, so the body stood turned
    about world Y by up to ~180 deg there. The rolling card (a Mixamo fixture rolling over its
    Hips) onto a second fixture at its own size - a twin, rootless - standing at ROLL_AT, pasted
    at 50: with the travel, every member on the card carried from its ground at its first frame
    onto the target's ground where it stood (the body travels as the card's); In place, every
    member on the card's STEADIED ground frame (computed here, `steadied_grounds`) placed on the
    target's - every frame. The control: the same presses with `_on_ground` taking off the
    joint's own heading (the code before the fix)."""
    rolling_card()
    card = CARDS["roll"]
    header, frames = card
    count = END - START + 1
    span = [(AT + i, i) for i in range(count)]
    source0 = card_bones(card, 0)
    top_leaf = pm.root_of(header["bones"])
    rest = pm.matrix(header["bones"][top_leaf]["rest"])
    turns = [pm.rotation(rest).inverse() * pm.rotation(card_bones(card, i)[top_leaf]["world"])
             for i in range(count)]
    swings = [_swing(turn) for turn in turns]
    own = [_yaw(turn) for turn in turns]
    jump = max(abs(_wrap(b - a)) for a, b in zip(own, own[1:]))
    gate("mixamo the rolling card: rootless, its Hips past %g deg off upright on some frames and "
         "within it on others, their own heading jumping between two neighbours" % SWING_LIMIT,
         not pm.has_root(header["bones"]) and max(swings) > 150.0 and min(swings) < 10.0 and
         math.degrees(jump) > 90.0,
         "swing %.2f..%.2f deg, %d frames past it; the own heading's worst jump %.2f deg" % (
             min(swings), max(swings), sum(1 for s in swings if s > SWING_LIMIT),
             math.degrees(jump)))
    top, _ours = build_mixamo("mxs", 1.0)
    (x, y, z), yaw = ROLL_AT
    cmds.move(x, y, z, top, relative=True, worldSpace=True)
    cmds.rotate(0.0, yaw, 0.0, top, relative=True, worldSpace=True)
    evaluate()
    ch = Char("mxs", top)
    members_t, pairs, bones = target_members(header, ch, source0)
    twin = pm.twin(pairs, source0, bones)
    first_ground = root_frames(source0)[0]
    steady = steadied_grounds(card)

    def press(options, control):
        ch.wipe()
        go(AT)
        stand = target_place(ch)
        if control:
            with patched(pm, "_on_ground", _on_ground_own):
                ok, text = animapply.apply(header, frames, selection=[top], options=options)
        else:
            ok, text = animapply.apply(header, frames, selection=[top], options=options)
        return ok, text, stand

    for label, options, carry_of in (
            ("with the travel", animdata.Options(),
             lambda i, stand: first_ground.inverse() * stand),
            ("In place", animdata.Options(in_place=True),
             lambda i, stand: steady[i].inverse() * stand)):
        ok, text, stand = press(options, False)
        say("   rolling card %s onto a rootless twin: %s" % (label, text))
        deg, cm = _body_on(card, ch, members_t, pairs, span,
                           lambda i, stand=stand, carry_of=carry_of: carry_of(i, stand))
        gate("mixamo the rolling card %s onto a ROOTLESS twin: every member on the card relative "
             "to the target's ground, every frame (its Hips upside down included)" % label,
             ok and twin and len(members_t) > 20 and deg.value <= 0.01 and cm.value <= 0.01,
             "%s deg, %s cm over %d members, %d frames | %s" % (deg, cm, len(members_t), count,
                                                                text))
        ok_c, text_c, stand = press(options, True)
        deg_c, cm_c = _body_on(card, ch, members_t, pairs, span,
                               lambda i, stand=stand, carry_of=carry_of: carry_of(i, stand))
        gate("mixamo the control - %s, the top joint's OWN heading taken off (before the fix): "
             "the body turned at the inverted frames, the gate above would fail" % label,
             ok_c and deg_c.value > 90.0,
             "%s deg, %s cm | %s" % (deg_c, cm_c, text_c))
    ch.wipe()
    cmds.setAttr(top + ".visibility", False)


# ------------------------------------------------------------------ speed

def phase_speed():
    cards()
    count = END - START + 1
    header, frames = CARDS["full"]
    for label, kind in (("B", "rig"), ("S", "skeleton")):
        if kind in SPEED:
            continue
        ch = need(label)
        ch.wipe()
        go(AT)
        t0 = time.time()
        animapply.apply(header, frames, selection=ch.selection())
        SPEED[kind] = (time.time() - t0) / count
        ch.wipe()
    say("   speed: capture %s s a frame, a paste onto a rig %.3f s a frame, onto a skeleton "
        "%.3f s a frame" % ("%.4f" % SPEED["capture"] if "capture" in SPEED else "-",
                            SPEED["rig"], SPEED["skeleton"]))
    gate("speed a paste onto a rig under a second a frame (standalone)", SPEED["rig"] < 1.0,
         "%.3f s a frame (%.1f s for %d frames); a skeleton %.3f" % (
             SPEED["rig"], SPEED["rig"] * count, count, SPEED["skeleton"]))


# ------------------------------------------------------------------ floor

def carried_rows(card, i, bones, ground_t):
    """[(leaf, deg, cm)]: each card bone's world at frame `i`, carried from the card's ground
    frame there onto the target's (`ground_t`), against the target's bone of that leaf."""
    src = card_bones(card, i)
    carry = root_frames(src)[0].inverse() * ground_t
    rows = []
    for leaf, b in bones.items():
        if leaf not in src:
            continue
        want = pm.rigid(pm.matrix(src[leaf]["world"]) * carry)
        got = pm.rigid(W(b["path"]))
        rows.append((leaf, pm.angle(got, want), (pm.position(got) - pm.position(want)).length()))
    return rows


def phase_floor():
    cards()
    full = CARDS["full"]
    mix = CARDS.get("mixamo")
    if mix is None and "mixamo" in PHASES:
        mixamo_card()
        mix = CARDS["mixamo"]
    count = END - START + 1
    cmds.file(new=True, force=True)
    CH.clear()
    cmds.currentUnit(time="ntsc")
    cmds.undoInfo(state=True, infinity=True)
    go(FLOOR_FRAME)
    keep = locator("keepSelected")
    cmds.select(keep, replace=True)
    t0 = time.time()
    ok, text = animapply.drop_floor(full[0], full[1], FLOOR_AT)
    say("   floor (%.1f s): %s" % (time.time() - t0, text))
    rigs = maya_rigs.rigs()
    rig = rigs[0] if len(rigs) == 1 else None
    gate("floor a Manny_Rig added", ok and rig is not None and rig.namespace.startswith(
        "Manny_Rig"), "%s" % [r.namespace for r in rigs])
    if rig is None:
        return
    ch = Char("floor", rig)
    go(FLOOR_FRAME)
    main = pm.position(W(rig.main))
    off = (main - om.MVector(*FLOOR_AT)).length()
    gate("floor Main on the point at the paste frame", off <= 0.01,
         "%.6f cm (%.3f, %.3f, %.3f)" % (off, main.x, main.y, main.z))
    place = target_place(ch)
    span = [(FLOOR_FRAME + i, i) for i in range(count)]
    rcm, rdeg = root_rows(ch, full, span, 0, place, 1.0)
    go(FLOOR_FRAME + count - 1)
    moved = (pm.position(target_place(ch)) - pm.position(place)).length()
    gate("floor the root travelling as the card's from there", rcm.value <= 0.01 and
         rdeg.value <= 0.01 and moved > 100.0,
         "%s cm, %s deg; travelled %.2f cm" % (rcm, rdeg, moved))
    members_t, _p, _b = target_members(full[0], ch, card_bones(full, 0))
    deg, cm = paste_rows(ch, full, [(FLOOR_FRAME + i, i) for i in (0, 11, 23)], members_t)
    gate("floor the members on the card", deg.value <= 0.01, "%s deg, %s cm" % (deg, cm))
    gate("floor the selection as before", cmds.ls(selection=True, long=True) == [keep],
         "%s" % cmds.ls(selection=True, long=True))
    # ---- a card saved at another rate: pasted frame for frame, and the line says so
    cmds.currentUnit(time="film")
    go(FPS_AT)
    hand = CARDS["hand"]
    ok, text = animapply.apply(hand[0], hand[1], selection=[ch.node("FKWrist_L")])
    say("   at film: %s" % text)
    written = keyed_plugs(ch, FPS_AT + 1)
    wrong = [p for p in written if not same_times(
        [t for t in curve_keys(p)[0] if t >= FPS_AT - 1e-6],
        [float(FPS_AT + i) for i in range(count)])]
    gate("floor a ntsc card pasted into a film scene: frame for frame, said",
         ok and written and not wrong and
         animapply.FPS_NOTE % (hand[0]["fps"], "film") in text,
         "%d written, %d off %d..%d | %s" % (len(written), len(wrong), FPS_AT,
                                            FPS_AT + count - 1, text))
    cmds.currentUnit(time="ntsc")
    go(FLOOR_FRAME)
    if mix is None:
        say("   floor: no Mixamo card (the mixamo phase did not run) - the native drop skipped")
        return
    go(FLOOR_FRAME)
    ok, text = animapply.drop_floor(mix[0], mix[1], NATIVE_AT)
    say("   floor native: %s" % text)
    bare = [r for r in skeletonimport.bare_roots() if maya_rigs.namespace_of(r).startswith(
        "pose_")]
    root = bare[0] if len(bare) == 1 else None
    gate("floor native: rebuilt bones only in pose_<name>", ok and root is not None,
         "%s" % bare)
    if root is None:
        return
    native = Char("native", root)
    bones = native.bones()
    go(FLOOR_FRAME)
    ground = target_place(native)
    on = math.hypot(pm.position(ground).x - NATIVE_AT[0], pm.position(ground).z - NATIVE_AT[2])
    gate("floor native: its ground frame on the point at the paste frame", on <= 0.01,
         "%.6f cm" % on)
    rcm, rdeg = root_rows(native, mix, span, 0, ground, 1.0)
    go(FLOOR_FRAME + count - 1)
    moved = (pm.position(target_place(native)) - pm.position(ground)).length()
    gate("floor native: its ground frame travelling as the card's from there",
         rcm.value <= 0.01 and rdeg.value <= 0.01 and moved > 100.0,
         "%s cm, %s deg; travelled %.2f cm" % (rcm, rdeg, moved))
    rows = Worst()
    for t, i in span[::4] + [span[-1]]:
        go(t)
        found = carried_rows(mix, i, bones, target_place(native))
        d, c, at, at_c = worst_of(found)
        rows.see(max(d, c), "%s/%s @%g" % (at, at_c, t))
    gate("floor native: every bone on the card carried from its ground frame", rows.value <= 0.01,
         "%s (deg or cm)" % rows)


# ------------------------------------------------------------------ the run

def run():
    t0 = time.time()
    say("plugin %s (animapply from %s); evaluation %s" % (
        PLUGIN, os.path.dirname(animapply.__file__),
        cmds.evaluationManager(query=True, mode=True)))
    for name, fn in (("capture", phase_capture), ("twin", phase_twin), ("modes", phase_modes),
                     ("options", phase_options), ("cross", phase_cross),
                     ("mirror", phase_mirror), ("blend", phase_blend),
                     ("objects", phase_objects), ("undo", phase_undo),
                     ("mixamo", phase_mixamo), ("speed", phase_speed),
                     ("floor", phase_floor)):
        if name not in PHASES:
            continue
        say("== %s" % name)
        t1 = time.time()
        try:
            fn()
        except Exception:                                    # noqa: BLE001
            say(traceback.format_exc())
            gate("%s ran" % name, False, "raised")
        say("   (%s %.1f s)" % (name, time.time() - t1))
    say("total %.1f s" % (time.time() - t0))


try:
    run()
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    gate("run", False, "raised")
finally:
    for folder in LIBRARY:
        shutil.rmtree(folder, ignore_errors=True)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
if OUT is not None:
    OUT.close()

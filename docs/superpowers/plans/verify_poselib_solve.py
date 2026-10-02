"""The Pose Library's solve, end to end, in mayapy STANDALONE (2026-10-02).

Never in the animator's open Maya: this adds six characters, poses them, keys them and switches
their FK/IK blends. Run with a scratch MAYA_APP_DIR (the animator's prefs never touched):

    $env:MAYA_APP_DIR = "<a scratch folder>"
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
        docs/superpowers/plans/verify_poselib_solve.py [out.txt]

Every gate prints `PASS/FAIL <name> <value>`, the run ends `SUMMARY x/y` (an optional file
argument gets the same lines). The plugin is the one beside this script (`<repo>/SkeldarAnim`;
`$env:POSELIB_PLUGIN` names another), and its path is the first line. The real road every
time: a card is `capture.build_pose` of a selection, a target is `scene.skeleton`, the
transfer `posemath.pairs / scale_between / targets`, the solve `rigsolve.solve` /
`skelsolve.solve`, the keys `keys.write` on the layer `keys.active_layer` answers (none:
plain keys) - then a real time change evaluates the rig and the BONES are measured against the
card, independently of the solver's own `measure`.

  save      Manny_Rig, Creep_Rig, Orc_D_Rig, the Manny UE5 skeleton (twice), the Creep skeleton
            and the UE4 Mannequin added; each rig posed by its FK controls (arms with a forearm
            roll, knees and elbows bent on their anatomical hinge, toes swung, spine, neck,
            head, fingers) and RootX_M moved and turned - with every limb shown in FK for the
            capture (the Creep's and the Orc D's legs ship in IK; their FK pose would not
            show) - and a full pose (Main selected) and a left-hand pose (the `Hand L` chip)
            captured: bones = the skeleton's, every member with its rest / world, the drive on
            the eight unrolled limb bones (upperarm, lowerarm, thigh, calf a side) and on
            nothing else - the neck lands its BONES (rigsolve), so it carries none - canonical
            names = the leaves (all three rigs are UE5).
  rig-twin  each rig's full pose solved back onto the SAME rig standing elsewhere (every pose
            channel at -0.5 v + 3), as shipped (the Creep's and the Orc D's legs in IK): every
            member game bone on its captured world to 0.01 deg / 0.01 cm (the four unrolled
            limb bones by where they point), the twist bones of the limbs SHOWN IN FK on their
            captured ones to 0.05 deg, Main unmoved, the FK controls on the values that made the
            pose to 0.001 deg, RootX_M too (0.001 deg / cm); the solve left the scene as found.
  ik        the Creep's and the Orc D's legs in IK (shipped), Manny's left arm AND left leg
            switched to IK before the solve (that calf, point-constrained to AdvancedSkeleton's
            knee, wanders 0.06 cm from pose to pose: the IK foot must stand on the FK foot):
            the IK limb's bones on the pose to 0.05 cm / 0.05 deg (the unrolled ones by where
            they point; a hinge note is allowed), then the blend set to FK and the FK chain
            shows the same pose to 0.01 deg, its twist bones to 0.05 deg. And an `Arm L` card
            (no hand) onto Manny's left arm in another pose, shown in IK and in FK: the arm
            points as the card's on its clavicle, the IK hand keeps its turn on the forearm's
            drive, and the FK-shown arm's keys switched to IK show the hand where FK showed it.
  neck      a neck pose made on the Manny SKELETON (neck_01, neck_02 and head turned by their
            joints, the head turned about its own neck axis too - NeckPart1_M takes half of
            that turn) onto Manny_Rig standing in another pose, at FKNeck_M.bias 0 and at 10:
            neck_01, neck_02 and head TURNED as the targets to 0.05 deg (their places printed:
            the rig's own lengths), and the targets on the skeleton's own pose relative to the
            chest (a twin); bias and the in-between's twist share unchanged.
  cross     Manny_Rig's full pose onto Creep_Rig, Orc_D_Rig, the Manny skeleton, the Creep
            skeleton and the UE4 Mannequin: every paired member bone with a direction child
            POINTS where the source's does to 0.1 deg (in each root's rest frame; a TWIN target,
            the Manny skeleton, every member TURNED as the source's to 0.01 deg instead - below),
            every length unchanged to 0.0001 cm (the pelvis excepted: it is placed; the export
            helpers follow their own constraints), the root / Main unmoved, the pelvis at the
            source's root offset carried through the two root rests and scaled by the bodies'
            size.
  skeleton  a Manny skeleton posed by every joint (the pelvis moved too) onto a second Manny
            skeleton standing elsewhere (moved and turned): every member, twist bones included,
            on the source's pose relative to the root to 0.001 deg / 0.001 cm. Then a card
            whose bones carry TRANSLATIONS (neck_01 and the clavicles 3.7 cm off their bind, as
            a UE 3P clip has them, the left calf 3 cm): still a twin (decided on the rests),
            every member TURNED as the card's to 0.001 deg (its places the target's lengths).
  partial   the Creep_Rig's left-hand pose onto the Creep_Rig standing in another pose: only
            the left hand's controls change - its FK wrist, its finger controls and the IK arm's
            end (the spec's «both modes keyed»: the IK wrist is the hand's own) - every other
            control channel to 1e-6, the hand on the pose relative to the forearm's DRIVE (the
            forearm with its roll: the unrolled bone never rolls) and every finger relative to
            the hand to 0.01 deg.

What is NOT gated as the brief first had it, and why (each the spec's own promise, stated
rather than weakened):

- the twist bones of a limb shown in IK: an IK elbow or knee is a hinge, the FK calf / forearm
  roll a pose carries cannot be held by it (spec "Onto a rig": «measured and said, as the FK/IK
  switch does») - they are printed, and gated once the blend is back at FK;
- the PLACE of a bone on a rig, the pelvis's apart: a solve turns controls, and where a bone
  then stands is the rig's own lengths - Manny_Rig's game bones are point-constrained to
  AdvancedSkeleton's joints and wander from pose to pose (the left calf 0.06 cm, the head on
  neck_02 0.05 cm with the twist share). The twin gates measure places against the card (the
  same rig, the same lengths: exact); the neck gate measures turns;
- where a twin's bones POINT (the cross phase's Manny skeleton): the spec gives a twin A = I, so
  its bones turn exactly as the source's and point along their own rigid lengths, while the
  source rig's game neck_02 stands where its point constraint puts it (0.13 cm off
  NeckPart1_M) - 0.34 deg of pointing at neck_02, printed;
- a bone whose direction child skips one of its partner's bones (the UE4 Mannequin's three
  spine bones under five, its one neck under two; a hand whose middle finger hangs past a
  metacarpal the target lacks): the transfer copies the partner's ROTATION, so such a bone
  points where the partner's rest chord is carried by the partner's turn - gated so, apart
  (`a chord past a bone it lacks`); for a direct child that is the partner's actual direction.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Apply - where, and how").
"""

import io
import math
import os
import sys
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.api.OpenMaya as om  # noqa: E402
import maya.cmds as cmds  # noqa: E402

# the plugin beside THIS script (<repo>/SkeldarAnim), never a path written in: run from another
# checkout, a fixed path would import that checkout's plugin and prove its code (CLAUDE.md note
# 9). POSELIB_PLUGIN overrides it.
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
if not os.path.isfile(os.path.join(PLUGIN, "maya_poselib", "posemath.py")):
    raise ImportError("no plugin with maya_poselib at %s" % PLUGIN)
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")

import maya_asretarget  # noqa: E402
import maya_rigs  # noqa: E402
import maya_skeletonmap as skelmap  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

from maya_poselib import capture, keys, rigsolve, scene, skelsolve  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

PHASES = [p.strip() for p in os.environ.get(
    "POSELIB_PHASES", "save,rig-twin,ik,neck,cross,skeleton,partial").split(",") if p.strip()]
OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []

ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")
UNROLLED_LIMB = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
EIGHT = sorted(["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "thigh_l", "thigh_r",
                "calf_l", "calf_r"])
FINGER_WORDS = skelmap.FINGERS
HINGE = {"Elbow": ("Shoulder", "Wrist"), "Knee": ("Hip", "Ankle")}


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


def evaluate():
    """A real time change, so every keyed channel and the rig downstream are read fresh."""
    t = frame()
    cmds.currentTime(t + 1, update=True)
    cmds.currentTime(t, update=True)


# ------------------------------------------------------------------ the characters

def add(key):
    """(the new Rig or skeleton root) after Add Character of the catalog row `key`."""
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


def values_of(plugs):
    return dict((p, float(cmds.getAttr(p))) for p in plugs)


def long_plug(plug):
    node, attr = plug.rsplit(".", 1)
    return (cmds.ls(node, long=True) or [node])[0] + "." + attr


class Char(object):
    """One character of the run: its ref, its default channel values, the plugs it was keyed on."""

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
        self.keyed = set()

    def reset(self):
        """Every key the run made cut, every channel back at its value after Add."""
        if self.keyed:
            cmds.cutKey(sorted(self.keyed), clear=True)
            self.keyed = set()
        for plug, value in self.defaults.items():
            try:
                cmds.setAttr(plug, value)
            except RuntimeError:
                pass
        evaluate()

    def node(self, leaf):
        return maya_rigs.node(self.rig, leaf)

    def bones(self):
        return scene.skeleton(self.ref)[0]

    def game(self):
        """{leaf: long path} of the game skeleton."""
        return dict((leaf, b["path"]) for leaf, b in self.bones().items())


def set_values(values):
    for plug, value in values.items():
        cmds.setAttr(plug, value)


# ------------------------------------------------------------------ a deterministic FK pose
# (task 6a's proof: knees and elbows bent on their anatomical hinge, signed by the body's front -
# a hyperextended knee flips an IK hinge 170 deg, which says nothing of the solver)

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
    """{plug: value}: every FK control of `maya_asretarget.ROWS` turned (a forearm roll, the
    hinges bent forward, the toes swung, fingers smaller), RootX_M moved and turned."""
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
                    out[plug] = value
    rootx = ch.node("RootX_M")
    for channel, value in zip(TR + ROT, (3.0, -4.0, 5.0, 8.0, 15.0, -6.0)):
        out[rootx + "." + channel] = value * (1.0 - 0.6 * seed)
    return out


def blends(ch):
    """{plug: value} of every limb's FK/IK switch."""
    out = {}
    for limb in ("Arm", "Leg"):
        for side in ("L", "R"):
            plug = ch.node("FKIK%s_%s" % (limb, side)) + ".FKIKBlend"
            if cmds.objExists(plug):
                out[plug] = float(cmds.getAttr(plug))
    return out


def shown_in_ik(ch):
    """{(kind, side)} of the limbs shown (partly) in IK."""
    out = set()
    for plug, value in blends(ch).items():
        name = plug.split(":")[-1].split(".")[0]           # FKIKArm_L
        if value > 1e-9:
            out.add(("arm" if "Arm" in name else "leg", name[-1].lower()))
    return out


# ------------------------------------------------------------------ the road

def transfer(data, target, members=None):
    """(wanted, target members, target bones, pairs, scale): posemath's road, as Apply takes it."""
    source = data["bones"]
    members = data["members"] if members is None else members
    bones = target.bones()
    pairs = pm.pairs(source, bones)
    scale = pm.scale_between(source, bones, pairs)
    wanted = pm.targets(source, bones, pairs, members, use_drive=target.rig is not None,
                        scale=scale)
    members_t = [t for t, s in pairs.items() if s in set(members)]
    return wanted, members_t, bones, pairs, scale


def solve_and_key(target, wanted, members_t, bones=None):
    """(solution, keys made, key notes): the solver's values keyed on the active layer at the
    current frame, the frame then re-evaluated."""
    if target.rig is not None:
        solution = rigsolve.solve(target.rig, wanted, members_t)
    else:
        solution = skelsolve.solve(target.ref, bones or target.bones(), wanted, members_t)
    layer, refusal = keys.active_layer()
    if refusal:
        return solution, 0, [refusal]
    count, notes = keys.write(solution.values, frame(), layer)
    target.keyed.update(solution.values)
    evaluate()
    return solution, count, notes


def limb_kind(leaf):
    base, side = (leaf[:-2], leaf[-1]) if leaf.endswith(("_l", "_r")) else (leaf, None)
    word = base.split("_")[0]
    if side is None:
        return None
    if word in ("upperarm", "lowerarm", "hand"):
        return ("arm", side)
    if word in ("thigh", "calf", "foot", "ball"):
        return ("leg", side)
    return None


def bone_error(leaf, now, captured, game_now, captured_bones):
    """(deg, cm) of a game bone against its captured world: the four unrolled limb bones by
    where they point (toward the next limb bone), the rest by their whole rotation."""
    base = leaf[:-2] if leaf.endswith(("_l", "_r")) else leaf
    cm = (pm.position(now) - pm.position(captured)).length()
    child = UNROLLED_LIMB.get(base)
    if child is not None:
        child = child + leaf[-2:]
        if child in game_now and child in captured_bones:
            a = pm.position(game_now[child]) - pm.position(now)
            b = pm.position(captured_bones[child]) - pm.position(captured)
            return pm.direction_angle(a, b), cm
    return pm.angle(now, captured), cm


def worst_of(rows):
    """(deg, cm, leaf of the worst deg, leaf of the worst cm) over (leaf, deg, cm) rows."""
    deg = max(rows, key=lambda r: r[1]) if rows else (None, 0.0, 0.0)
    cm = max(rows, key=lambda r: r[2]) if rows else (None, 0.0, 0.0)
    return deg[1], cm[2], deg[0], cm[0]


def captured_worlds(data):
    return dict((leaf, pm.rigid(b["world"])) for leaf, b in data["bones"].items())


def scene_worlds(target):
    return dict((leaf, pm.rigid(W(path))) for leaf, path in target.game().items())


def main_world(target):
    return W(target.rig.main) if target.rig is not None else W(target.root)


def matrix_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


# ------------------------------------------------------------------ phases

CH = {}
POSES = {}          # rig label -> {"full", "hand", "values"}


def phase_save():
    t0 = time.time()
    for label, key in (("Manny_Rig", "Manny_Rig"), ("Creep_Rig", "Creep_Rig"),
                       ("Orc_D_Rig", "Orc_D_Rig"), ("Manny", "Manny"), ("Manny2", "Manny"),
                       ("Creep", "Creep"), ("UE4", "UE4_Mannequin")):
        handle = add(key)
        if handle is None:
            gate("save add %s" % label, False, "nothing added")
            continue
        CH[label] = Char(label, handle)
    say("added %d characters in %.1f s; EM %s; frame %g" % (
        len(CH), time.time() - t0, cmds.evaluationManager(query=True, mode=True), frame()))
    for label in ("Manny_Rig", "Creep_Rig", "Orc_D_Rig"):
        ch = CH[label]
        ch.reset()
        for plug in blends(ch):
            cmds.setAttr(plug, 0.0)                 # every limb shown in FK for the capture
        values = pose_values(ch)
        set_values(values)
        evaluate()
        full, note = capture.build_pose([ch.rig.main])
        hand, hand_note = capture.build_pose([ch.rig.main], regions=["Hand L"])
        POSES[label] = {"full": full, "hand": hand, "values": values}
        say("   %s: %s | %s" % (label, note, hand_note))
        joints = 1 + len(cmds.listRelatives(ch.root, allDescendents=True, type="joint") or [])
        gate("save %s bones = the skeleton's" % label, full and len(full["bones"]) == joints,
             "%d of %d" % (len(full["bones"]) if full else -1, joints))
        missing = [m for m in full["members"] if len(full["bones"][m].get("rest") or []) != 16
                   or len(full["bones"][m].get("world") or []) != 16]
        gate("save %s every member has rest / world" % label,
             full["members"] and not missing, "%d members, %d without" % (
                 len(full["members"]), len(missing)))
        drives = sorted(leaf for leaf, b in full["bones"].items() if b.get("drive"))
        gate("save %s drive on the eight unrolled limb bones, nothing else" % label,
             drives == EIGHT, "%s" % drives)
        named = [(leaf, b["canonical"]) for leaf, b in full["bones"].items() if b["canonical"]]
        wrong = [(leaf, c) for leaf, c in named if c != leaf]
        gate("save %s canonical = leaf (UE5)" % label, named and not wrong,
             "%d named, %d differ %s" % (len(named), len(wrong), wrong[:4]))
        hand_bones = sorted(leaf for leaf in full["bones"] if leaf.endswith("_l") and (
            leaf == "hand_l" or leaf.split("_")[0] in FINGER_WORDS))
        gate("save %s left-hand pose = the hand and its fingers" % label,
             hand and sorted(hand["members"]) == hand_bones and hand["regions"] == ["Hand L"],
             "%d members %s" % (len(hand["members"]) if hand else -1,
                                hand["regions"] if hand else None))
        ch.reset()


def twin_gates(label, ch, data, solution, count, key_notes, wanted, members_t, main_before,
               tol_deg=0.01, tol_cm=0.01, ik_ok=False):
    """The rig-twin / ik gates of one solve onto the rig the card was made on."""
    captured = captured_worlds(data)
    game_now = scene_worlds(ch)
    ik = shown_in_ik(ch)
    rows, twists, twist_ik = [], [], []
    for leaf in members_t:
        if leaf not in game_now:
            continue
        if pm.is_twist(leaf):
            base = leaf.split("_twist_")[0]
            kind = ("arm" if base in ("upperarm", "lowerarm") else "leg", leaf[-1])
            deg = pm.angle(game_now[leaf], captured[leaf])
            (twist_ik if kind in ik else twists).append((leaf, deg, 0.0))
            continue
        deg, cm = bone_error(leaf, game_now[leaf], captured[leaf], game_now, captured)
        rows.append((leaf, deg, cm))
    deg, cm, at_deg, at_cm = worst_of(rows)
    gate("%s members on the captured world" % label, deg <= tol_deg and cm <= tol_cm,
         "%.6f deg (%s) %.6f cm (%s), %d bones" % (deg, at_deg, cm, at_cm, len(rows)))
    m_deg, m_cm, m_leaf = rigsolve.measure(ch.rig, wanted, members_t)
    gate("%s rigsolve.measure" % label, m_deg <= tol_deg and m_cm <= tol_cm,
         "%.6f deg %.6f cm (%s)" % (m_deg, m_cm, m_leaf))
    t_deg, _t, t_at, _a = worst_of(twists)
    gate("%s twist bones (limbs shown in FK)" % label, twists and t_deg <= 0.05,
         "%.6f deg (%s), %d bones" % (t_deg, t_at, len(twists)))
    if twist_ik:
        i_deg, _i, i_at, _b = worst_of(twist_ik)
        say("   %s twist bones of limbs shown in IK (the hinge, not gated): %.3f deg (%s), "
            "%d bones" % (label, i_deg, i_at, len(twist_ik)))
    gate("%s Main unmoved" % label, matrix_diff(main_before, W(ch.rig.main)) < 1e-9,
         "%.3g" % matrix_diff(main_before, W(ch.rig.main)))
    gate("%s every value keyed" % label, count == len(solution.values) and not key_notes
         and not solution.skipped,
         "%d keys of %d values, notes %s, skipped %s" % (count, len(solution.values),
                                                        key_notes, dict(solution.skipped)))
    say("   %s notes: %s" % (label, solution.notes))
    stray = unexpected_notes(solution.notes, ik_ok)
    gate("%s no note but the driven twist bones%s" % (label, " and the hinge" if ik_ok else ""),
         not stray, "%s" % stray)


# the Orc D's shoulder pads are game joints riding their clavicles by constraint, no control
PADS = "2 member(s) have no control on Orc_D_Rig: AB_Armor_Shoulder_L, AB_Armor_Shoulder_R"


def unexpected_notes(notes, ik_ok=False):
    """The notes a solve should not have said: anything but the twist bones driven on a rig, the
    Orc D's shoulder pads, and - on a limb shown in IK - the hinge."""
    return [n for n in notes if "are driven on a rig" not in n and n != PADS
            and not (ik_ok and "hinge" in n)]


def control_values_gate(label, ch, values):
    """The FK controls (and RootX_M) on the values that made the pose."""
    fk_worst, fk_at, root_worst, root_at = 0.0, None, 0.0, None
    for plug, value in values.items():
        got = float(cmds.getAttr(plug))
        d = abs(got - value)
        if plug.split(".")[0].endswith("RootX_M"):
            if d > root_worst:
                root_worst, root_at = d, plug
        elif d > fk_worst:
            fk_worst, fk_at = d, plug
    gate("%s FK control values = the pose's" % label, fk_worst <= 0.001,
         "%.6f (%s)" % (fk_worst, fk_at))
    gate("%s RootX_M values = the pose's" % label, root_worst <= 0.001,
         "%.6f (%s)" % (root_worst, root_at))


def elsewhere(values):
    return dict((p, -0.5 * v + 3.0) for p, v in values.items())


def phase_rig_twin():
    for label in ("Manny_Rig", "Creep_Rig", "Orc_D_Rig"):
        ch, pose = CH[label], POSES[label]
        ch.reset()
        moved = elsewhere(pose["values"])
        set_values(moved)
        evaluate()
        main_before = W(ch.rig.main)
        wanted, members_t, _bones, pairs, scale = transfer(pose["full"], ch)
        before = values_of(ch.plugs)
        solved = rigsolve.solve(ch.rig, wanted, members_t)
        after = values_of(ch.plugs)
        moved_by = max(abs(before[p] - after[p]) for p in before)
        gate("twin %s the solve leaves the scene as found" % label, moved_by < 1e-9,
             "max %.3g over %d channels" % (moved_by, len(before)))
        solution, count, key_notes = solve_and_key(ch, wanted, members_t)
        say("   %s: %d target members, scale %.4f, %d values (%d the same as the dry run)" % (
            label, len(members_t), scale, len(solution.values),
            sum(1 for p, v in solution.values.items()
                if abs(solved.values.get(p, 1e9) - v) < 1e-9)))
        twin_gates("twin %s" % label, ch, pose["full"], solution, count, key_notes, wanted,
                   members_t, main_before, ik_ok=bool(shown_in_ik(ch)))
        control_values_gate("twin %s" % label, ch, pose["values"])
        keyed = set(long_plug(p) for p in solution.values)
        unkeyed = [p for p in ch.plugs if p not in keyed and
                   abs(before[p] - float(cmds.getAttr(p))) > 1e-9]
        gate("twin %s no channel but the solved ones changed" % label, not unkeyed,
             "%d keyed, %s" % (len(keyed), [p.split("|")[-1] for p in unkeyed[:4]]))
        ch.reset()


def phase_ik():
    # Manny's left leg too: its game calf is point-constrained to AdvancedSkeleton's knee and
    # wanders 0.06 cm from pose to pose - the IK foot must stand on the FK foot, not on a model
    for label, set_ik in (("Creep_Rig", None), ("Orc_D_Rig", None),
                          ("Manny_Rig", ["FKIKArm_L", "FKIKLeg_L"])):
        ch, pose = CH[label], POSES[label]
        ch.reset()
        set_values(elsewhere(pose["values"]))
        for name in set_ik or ():
            cmds.setAttr(ch.node(name) + ".FKIKBlend", 10.0)
        evaluate()
        ik = shown_in_ik(ch)
        gate("ik %s limbs shown in IK" % label, ik, "%s" % sorted(ik))
        main_before = W(ch.rig.main)
        wanted, members_t, _b, _p, _s = transfer(pose["full"], ch)
        solution, count, key_notes = solve_and_key(ch, wanted, members_t)
        say("   ik %s notes: %s" % (label, solution.notes))
        captured = captured_worlds(pose["full"])
        game_now = scene_worlds(ch)
        rows = [(leaf,) + bone_error(leaf, game_now[leaf], captured[leaf], game_now, captured)
                for leaf in members_t if limb_kind(leaf) in ik and not pm.is_twist(leaf)]
        deg, cm, at_deg, at_cm = worst_of(rows)
        gate("ik %s the IK limbs' bones on the pose" % label, rows and deg <= 0.05 and cm <= 0.05,
             "%.6f deg (%s) %.6f cm (%s), %d bones" % (deg, at_deg, cm, at_cm, len(rows)))
        gate("ik %s every value keyed" % label, count == len(solution.values) and not key_notes,
             "%d of %d %s" % (count, len(solution.values), key_notes))
        gate("ik %s Main unmoved" % label, matrix_diff(main_before, W(ch.rig.main)) < 1e-9)
        # the blend back at FK: the FK chain shows the same pose
        for plug in blends(ch):
            cmds.setAttr(plug, 0.0)
        evaluate()
        game_now = scene_worlds(ch)
        rows = [(leaf, pm.angle(game_now[leaf], captured[leaf]),
                 (pm.position(game_now[leaf]) - pm.position(captured[leaf])).length())
                for leaf in members_t if limb_kind(leaf) in ik and not pm.is_twist(leaf)]
        deg, cm, at_deg, at_cm = worst_of(rows)
        gate("ik %s switched to FK: the same pose" % label, deg <= 0.01 and cm <= 0.01,
             "%.6f deg (%s) %.6f cm (%s)" % (deg, at_deg, cm, at_cm))
        twist = [(leaf, pm.angle(game_now[leaf], captured[leaf]), 0.0) for leaf in members_t
                 if pm.is_twist(leaf) and (("arm" if leaf.startswith(("upperarm", "lowerarm"))
                                            else "leg"), leaf[-1]) in ik]
        t_deg, _c, t_at, _a = worst_of(twist)
        gate("ik %s switched to FK: its twist bones" % label, twist and t_deg <= 0.05,
             "%.6f deg (%s), %d bones" % (t_deg, t_at, len(twist)))
        ch.reset()
    ik_arm_card()


def ik_arm_card():
    """An `Arm L` card (the clavicle, the upper arm and the forearm, no hand) onto Manny's left
    arm standing in another pose, shown in IK and shown in FK:

    - the arm points where the card's does on the clavicle it hangs from;
    - shown in IK (its hand rolled 50 deg about the forearm first): the IK hand - no member -
      keeps its turn on the forearm's DRIVE as the card holds it; on the forearm the IK elbow
      shows, the turn differs by the twist a hinge cannot hold (the hinge note) - in IK that
      twist shows through the hand;
    - shown in FK (its FK forearm rolled about its bone): the keys switched to IK show the hand
      where the FK hand stood - both modes keyed. The IK end is the target's hand, which no
      member moves but which follows the FK forearm the card turned: on the forearm's drive it
      lands there; on the unrolled bone it was off by the forearm's roll."""
    ch, pose = CH["Manny_Rig"], POSES["Manny_Rig"]
    full = pose["full"]
    card = dict(full)
    card["members"] = capture.region_members(full["bones"], full["members"], ["Arm L"])
    source = full["bones"]
    blend = ch.node("FKIKArm_L") + ".FKIKBlend"
    for shown in ("IK", "FK"):
        ch.reset()
        set_values(pose_values(ch, seed=1.0))
        if shown == "IK":
            cmds.setAttr(blend, 10.0)
            cmds.setAttr(ch.node("IKArm_L") + ".rotateX", 50.0)
        evaluate()
        drive_before = pm.matrix(rigsolve.drive_matrices(ch.rig)["lowerarm_l"])
        hand_before = rel(scene_worlds(ch)["hand_l"], drive_before)
        wanted, members_t, _b, _p, _s = transfer(card, ch)
        solution, count, key_notes = solve_and_key(ch, wanted, members_t)
        say("   ik Arm L card, arm in %s: members %s, notes %s" % (
            shown, sorted(members_t), solution.notes))
        game = scene_worlds(ch)
        clav_t = pm.rotation(game["clavicle_l"])
        clav_s = pm.rotation(pm.matrix(source["clavicle_l"]["world"]))
        rows = []
        for bone, child in (("upperarm_l", "lowerarm_l"), ("lowerarm_l", "hand_l")):
            got = (pm.position(game[child]) - pm.position(game[bone])) * clav_t.inverse()
            want = (pm.position(source[child]["world"]) - pm.position(source[bone]["world"])) \
                * clav_s.inverse()
            rows.append((bone, pm.direction_angle(got, want), 0.0))
        deg, _c, at, _a = worst_of(rows)
        gate("ik an Arm L card, arm in %s: the arm points as the card's on its clavicle" % shown,
             deg <= 0.05, "%.6f deg (%s)" % (deg, at))
        if shown == "IK":
            hand_after = rel(game["hand_l"], wanted["lowerarm_l"])
            own = rel(game["hand_l"], pm.matrix(rigsolve.drive_matrices(ch.rig)["lowerarm_l"]))
            gate("ik an Arm L card, arm in IK: the hand keeps its turn on the forearm's drive",
                 pm.angle(hand_before, hand_after) <= 0.01,
                 "%.6f deg (on the IK forearm's own drive %.3f deg: the hinge)" % (
                     pm.angle(hand_before, hand_after), pm.angle(hand_before, own)))
        else:
            fk_hand = game["hand_l"]
            cmds.setAttr(blend, 10.0)
            evaluate()
            ik_hand = scene_worlds(ch)["hand_l"]
            moved = (pm.position(ik_hand) - pm.position(fk_hand)).length()
            gate("ik an Arm L card, arm in FK: switched to IK the hand stands where FK showed it",
                 pm.angle(ik_hand, fk_hand) <= 0.01 and moved <= 0.05,
                 "%.6f deg %.6f cm" % (pm.angle(ik_hand, fk_hand), moved))
    ch.reset()


def _joint(ch, leaf):
    return scene.bone_path(ch.ref, leaf)


def phase_neck():
    skel, rig = CH["Manny"], CH["Manny_Rig"]
    skel.reset()
    turns = {"neck_01": (-4.0, 6.0, 10.0), "neck_02": (5.0, -7.0, 9.0), "head": (25.0, 8.0, -6.0)}
    paths = dict((leaf, _joint(skel, leaf)) for leaf in turns)
    for leaf, delta in turns.items():
        now = cmds.getAttr(paths[leaf] + ".rotate")[0]
        cmds.setAttr(paths[leaf] + ".rotate", *[a + b for a, b in zip(now, delta)])
    evaluate()
    data, note = capture.build_pose([paths[leaf] for leaf in ("neck_01", "neck_02", "head")])
    say("   neck card: %s" % note)
    gate("neck card holds neck_01, neck_02, head", data and sorted(data["members"]) == sorted(
        turns), "%s" % (data["members"] if data else None))
    source = data["bones"]
    bias_plug = rig.node("FKNeck_M") + ".bias"
    share_plug = rig.node("twistAmountDivideNeckPart1_M") + ".input2"
    for bias in (0.0, 10.0):
        rig.reset()
        set_values(POSES["Manny_Rig"]["values"])       # the rig stands in another pose
        cmds.setAttr(bias_plug, bias)
        evaluate()
        share = float(cmds.getAttr(share_plug))
        wanted, members_t, bones, pairs, _scale = transfer(data, rig)
        solution, count, key_notes = solve_and_key(rig, wanted, members_t)
        game_now = scene_worlds(rig)
        rows = [(leaf, pm.angle(game_now[leaf], wanted[leaf]),
                 (pm.position(game_now[leaf]) - pm.position(wanted[leaf])).length())
                for leaf in ("neck_01", "neck_02", "head")]
        deg, cm, at_deg, at_cm = worst_of(rows)
        # turns: where a neck bone STANDS is the rig's own lengths, never the solve's - Manny_Rig's
        # game neck_02 is point-constrained 0.13 cm off NeckPart1_M and the head's place on it
        # turns with the in-between's twist share (0.05 cm here); printed, not gated
        gate("neck bias %g: neck_01, neck_02, head turned as the targets" % bias,
             deg <= 0.05, "%.6f deg (%s) [places %.4f cm (%s)] | %s" % (
                 deg, at_deg, cm, at_cm, ", ".join("%s %.4f" % (r[0], r[1]) for r in rows)))
        # the targets themselves: the skeleton's neck relative to its chest, carried (a twin)
        chain = (("neck_01", "spine_05"), ("neck_02", "neck_01"), ("head", "neck_02"))
        drift = 0.0
        for leaf, parent in chain:
            src = rel(pm.matrix(source[leaf]["world"]), pm.matrix(source[parent]["world"]))
            got = rel(game_now[leaf], game_now[parent])
            o = rel(pm.matrix(bones[leaf]["rest"]), pm.matrix(source[leaf]["rest"]))
            op = rel(pm.matrix(bones[parent]["rest"]), pm.matrix(source[parent]["rest"]))
            expected = pm.rotation(o) * pm.rotation(src) * pm.rotation(op).inverse()
            drift = max(drift, pm.angle(got, expected))
        gate("neck bias %g: the neck on the skeleton's pose relative to the chest" % bias,
             drift <= 0.05, "%.6f deg" % drift)
        gate("neck bias %g: bias and share unchanged" % bias,
             float(cmds.getAttr(bias_plug)) == bias and float(cmds.getAttr(share_plug)) == share,
             "bias %s share %s (was %s)" % (cmds.getAttr(bias_plug), cmds.getAttr(share_plug),
                                            share))
        gate("neck bias %g: every value keyed" % bias,
             count == len(solution.values) and not key_notes, "%d of %d, notes %s" % (
                 count, len(solution.values), solution.notes))
    rig.reset()
    skel.reset()


def direction_children(pairs, source, target):
    """{target leaf: its direction child}, read the way `posemath.alignments` reads it."""
    ue = pm.ue_named(source) and pm.ue_named(target)
    root = pm.root_of(target)
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


def lengths(bones_paths, bones):
    out = {}
    for leaf, path in bones_paths.items():
        parent = bones[leaf].get("parent")
        if parent in bones_paths:
            out[leaf] = (pm.position(W(path)) - pm.position(W(bones_paths[parent]))).length()
    return out


def phase_cross():
    data = POSES["Manny_Rig"]["full"]
    source = data["bones"]
    s_root = pm.root_of(source)
    for label in ("Creep_Rig", "Orc_D_Rig", "Manny", "Creep", "UE4"):
        target = CH[label]
        target.reset()
        before_paths = target.game()
        bones = target.bones()
        before_len = lengths(before_paths, bones)
        root_before = main_world(target)
        t_root_path = target.root
        root_world_before = W(t_root_path)
        wanted, members_t, bones, pairs, scale = transfer(data, target)
        solution, count, key_notes = solve_and_key(target, wanted, members_t, bones)
        say("   cross %s: %d paired members, scale %.4f, notes %s, skipped %s" % (
            label, len(members_t), scale, solution.notes, dict(solution.skipped)))
        use_drive = target.rig is not None
        p = dict((leaf, pm.matrix(b["drive"] if use_drive and b.get("drive") else b["world"]))
                 for leaf, b in source.items())
        t_root = pm.root_of(bones)
        now = dict((leaf, W(path)) for leaf, path in before_paths.items())
        t_frame = pm.rotation(now[t_root]).inverse() * pm.rotation(bones[t_root]["rest"])
        s_frame = pm.rotation(p[s_root]).inverse() * pm.rotation(source[s_root]["rest"])
        children = direction_children(pairs, source, bones)
        rows, chords, skipped = [], [], 0
        for leaf in members_t:
            child = children.get(leaf)
            if child is None or child not in now:
                skipped += 1
                continue
            s, sc = pairs[leaf], pairs[child]
            if source[sc]["parent"] == s:
                # a direct child: where the source's bone really points in the card
                want = pm.position(source[sc]["world"]) - pm.position(source[s]["world"])
                into = rows
            else:
                # past a bone the target lacks: the partner's rest chord, turned as it turns
                rest_dir = pm.position(source[sc]["rest"]) - pm.position(source[s]["rest"])
                want = rest_dir * pm.rotation(source[s]["rest"]).inverse() * pm.rotation(p[s])
                into = chords
            got = (pm.position(now[child]) - pm.position(now[leaf])) * t_frame
            into.append((leaf, pm.direction_angle(got, want * s_frame), 0.0))
        deg, _cm, at, _a = worst_of(rows)
        if pm.twin(pairs, source, bones):
            # the same body (posemath.twin: lengths within 1 %, rests within a degree): the spec
            # takes A = I, so every member TURNS as the source's, through the two rests - and
            # where a bone points follows the turn and the target's own (rigid) lengths, while
            # Manny_Rig's game neck_02 stands where its point constraint puts it (0.13 cm off
            # NeckPart1_M, the head's place on it turning with the twist share)
            s_rest_root = pm.rotation(source[s_root]["rest"])
            turns = []
            for leaf in members_t:
                s = pairs[leaf]
                got = pm.rotation(now[leaf]) * pm.rotation(now[t_root]).inverse()
                want = pm.rotation(bones[leaf]["rest"]) * pm.rotation(source[s]["rest"]).inverse() \
                    * pm.rotation(p[s]) * pm.rotation(p[s_root]).inverse() * s_rest_root \
                    * pm.rotation(bones[t_root]["rest"]).inverse()
                turns.append((leaf, pm.angle(got, want), 0.0))
            t_deg, _t, t_at, _ta = worst_of(turns)
            gate("cross %s a twin: every paired member turns as the source's" % label,
                 t_deg <= 0.01, "%.6f deg (%s), %d bones; pointing %.4f deg (%s), not gated" % (
                     t_deg, t_at, len(turns), deg, at))
        else:
            gate("cross %s every paired member points where the source's does" % label,
                 rows and deg <= 0.1, "%.6f deg (%s), %d bones, %d with no direction child" % (
                     deg, at, len(rows), skipped))
        if chords:
            c_deg, _c, c_at, _ca = worst_of(chords)
            gate("cross %s a chord past a bone it lacks turns as its partner" % label,
                 c_deg <= 0.1, "%.6f deg (%s), %d bones %s" % (
                     c_deg, c_at, len(chords), [r[0] for r in chords]))
        after_len = lengths(before_paths, bones)
        pelvis = skelsolve.pelvis_of(bones)
        changes = [(leaf, abs(after_len[leaf] - before_len[leaf])) for leaf in before_len
                   if leaf != pelvis and not pm.is_helper(leaf)]
        worst_len = max(changes, key=lambda r: r[1]) if changes else (None, 0.0)
        gate("cross %s lengths unchanged (the helpers follow their own constraints)" % label,
             worst_len[1] <= 0.0001,
             "%.7f cm (%s), %d bones" % (worst_len[1], worst_len[0], len(changes)))
        gate("cross %s root / Main unmoved" % label,
             matrix_diff(root_before, main_world(target)) < 1e-9 and
             matrix_diff(root_world_before, W(t_root_path)) < 1e-6,
             "%.3g / %.3g" % (matrix_diff(root_before, main_world(target)),
                              matrix_diff(root_world_before, W(t_root_path))))
        # the pelvis: the source's offset from its root, through the two root rests, scaled
        s_pelvis = skelsolve.pelvis_of(source)
        d_local = (pm.position(p[s_pelvis]) - pm.position(p[s_root])) * \
            pm.rotation(p[s_root]).inverse()
        o_root = pm.rotation(source[s_root]["rest"]) * \
            pm.rotation(bones[t_root]["rest"]).inverse()
        heights = [(pm.position(b[pv]["rest"]).y - pm.position(b[rt]["rest"]).y)
                   for b, pv, rt in ((bones, pelvis, t_root), (source, s_pelvis, s_root))]
        size = heights[0] / heights[1]
        size = 1.0 if abs(size - 1.0) <= 0.02 else size
        expected = d_local * o_root * size
        got = (pm.position(now[pelvis]) - pm.position(now[t_root])) * \
            pm.rotation(now[t_root]).inverse()
        gate("cross %s the pelvis at the scaled offset" % label,
             (got - expected).length() <= 0.01 and abs(size - scale) < 1e-9,
             "%.6f cm (size %.4f, posemath %.4f)" % ((got - expected).length(), size, scale))
        gate("cross %s every value keyed" % label,
             count == len(solution.values) and not key_notes and not solution.skipped,
             "%d of %d %s" % (count, len(solution.values), key_notes))
        target.reset()


def phase_skeleton():
    source_ch, target = CH["Manny"], CH["Manny2"]
    source_ch.reset()
    target.reset()
    bones = source_ch.bones()
    root = pm.root_of(bones)
    for i, leaf in enumerate(sorted(bones)):
        if leaf == root or pm.is_helper(leaf):
            continue
        path = bones[leaf]["path"]
        r = cmds.getAttr(path + ".rotate")[0]
        cmds.setAttr(path + ".rotate", r[0] + 9 * math.sin(i), r[1] + 7 * math.cos(1.7 * i),
                     r[2] + 11 * math.sin(0.3 * i + 1))
    pelvis = bones["pelvis"]["path"]
    t = cmds.getAttr(pelvis + ".translate")[0]
    cmds.setAttr(pelvis + ".translate", t[0] + 2.0, t[1] - 3.0, t[2] + 4.0)
    evaluate()
    data, note = capture.build_pose([source_ch.root])
    say("   skeleton card: %s" % note)
    # the target elsewhere: moved and turned (the solve never writes its root)
    cmds.setAttr(target.root + ".translate", 150.0, 0.0, -60.0)
    cmds.setAttr(target.root + ".rotateY", 40.0)
    evaluate()
    wanted, members_t, t_bones, _pairs, _scale = transfer(data, target)
    solution, count, key_notes = solve_and_key(target, wanted, members_t, t_bones)
    say("   skeleton: %d members, %d values, notes %s, skipped %s" % (
        len(members_t), len(solution.values), solution.notes, dict(solution.skipped)))
    source = data["bones"]
    s_root = pm.matrix(source[root]["world"])
    t_root = W(target.root)
    rows = []
    for leaf in members_t:
        got = rel(W(t_bones[leaf]["path"]), t_root)
        want = rel(pm.matrix(source[leaf]["world"]), s_root)
        rows.append((leaf, pm.angle(got, want), (pm.position(got) - pm.position(want)).length()))
    deg, cm, at_deg, at_cm = worst_of(rows)
    twists = sum(1 for leaf in members_t if pm.is_twist(leaf))
    gate("skeleton Manny -> Manny exact, twist bones included",
         deg <= 0.001 and cm <= 0.001 and twists > 0,
         "%.7f deg (%s) %.7f cm (%s), %d members, %d twist" % (
             deg, at_deg, cm, at_cm, len(rows), twists))
    gate("skeleton every value keyed", count == len(solution.values) and not key_notes
         and not solution.skipped, "%d of %d %s" % (count, len(solution.values), key_notes))
    source_ch.reset()
    target.reset()
    translated_card(source_ch, target, bones)


# where a UE 3P clip moves its bones off the bind (trap 152: neck_01 and the clavicles ~3.7 cm),
# plus a calf 3 cm out (a squash & stretch take moves every bone) - in each joint's parent frame
TRANSLATED = {"neck_01": (0.0, 3.7, 0.0), "clavicle_l": (0.0, 3.7, 1.0),
              "clavicle_r": (0.0, -3.7, 1.0), "calf_l": (0.0, 0.0, 3.0)}


def translated_card(source_ch, target, bones):
    """A card whose bones carry TRANSLATIONS is still its own model's twin (posemath.twin decides
    on the two rests): onto the second Manny skeleton standing elsewhere every member TURNS as
    the card's, relative to the root, to 0.001 deg - its places are the target's own lengths
    (only the pelvis takes the card's). Read as the bones stood, a calf 1 cm off its bind made
    the card no twin and turned thigh_l 1.273 deg off it (3 cm: 3.814 deg)."""
    root = pm.root_of(bones)
    for i, leaf in enumerate(sorted(bones)):
        if leaf == root or pm.is_helper(leaf):
            continue
        path = bones[leaf]["path"]
        r = cmds.getAttr(path + ".rotate")[0]
        cmds.setAttr(path + ".rotate", r[0] + 8 * math.cos(i), r[1] + 6 * math.sin(1.3 * i),
                     r[2] + 10 * math.cos(0.7 * i + 2))
    for leaf, (dx, dy, dz) in sorted(TRANSLATED.items()):
        path = bones[leaf]["path"]
        t = cmds.getAttr(path + ".translate")[0]
        cmds.setAttr(path + ".translate", t[0] + dx, t[1] + dy, t[2] + dz)
    evaluate()
    data, note = capture.build_pose([source_ch.root])
    say("   translated card: %s" % note)
    cmds.setAttr(target.root + ".translate", -120.0, 0.0, 80.0)
    cmds.setAttr(target.root + ".rotateY", -65.0)
    evaluate()
    wanted, members_t, t_bones, pairs, _scale = transfer(data, target)
    source = data["bones"]
    is_twin = pm.twin(pairs, source, t_bones)
    # how far each moved bone stands off its bind in its parent's frame, read off the card
    off = max((pm.position(rel(source[leaf]["world"], source[source[leaf]["parent"]]["world"]))
               - pm.position(rel(source[leaf]["rest"], source[source[leaf]["parent"]]["rest"]))
               ).length() for leaf in TRANSLATED)
    solution, count, key_notes = solve_and_key(target, wanted, members_t, t_bones)
    s_root = pm.matrix(source[root]["world"])
    t_root = W(target.root)
    rows = []
    for leaf in members_t:
        got = rel(W(t_bones[leaf]["path"]), t_root)
        want = rel(pm.matrix(source[leaf]["world"]), s_root)
        rows.append((leaf, pm.angle(got, want), 0.0))
    deg, _cm, at_deg, _at = worst_of(rows)
    gate("skeleton a card with translated bones is a twin, every member turned as it",
         is_twin and deg <= 0.001 and off >= 3.0,
         "twin %s, %.7f deg (%s), %d members, the card's bones up to %.3f cm off their bind" % (
             is_twin, deg, at_deg, len(rows), off))
    gate("skeleton the translated card keyed", count == len(solution.values) and not key_notes
         and not solution.skipped, "%d of %d %s" % (count, len(solution.values), key_notes))
    source_ch.reset()
    target.reset()


def phase_partial():
    ch = CH["Creep_Rig"]
    ch.reset()
    set_values(pose_values(ch, seed=1.0))           # another pose than the card's
    evaluate()
    data = POSES["Creep_Rig"]["hand"]
    before = values_of(ch.plugs)
    wanted, members_t, bones, _p, _s = transfer(data, ch)
    solution, count, key_notes = solve_and_key(ch, wanted, members_t)
    say("   partial: %d members, %d values, notes %s" % (len(members_t), len(solution.values),
                                                        solution.notes))
    allowed = set()
    for leaf in members_t:
        base = rigsolve.bases(ch.rig).get(leaf)
        if base and base.fk:
            allowed.add(base.fk)
    allowed.add((cmds.ls(ch.node("IKArm_L"), long=True) or [""])[0])
    changed = sorted(set(p.rsplit(".", 1)[0] for p in ch.plugs
                         if abs(before[p] - float(cmds.getAttr(p))) > 1e-6))
    stray = [c for c in changed if c not in allowed]
    gate("partial only the left hand's controls change", changed and not stray,
         "%d changed, stray %s" % (len(changed), [c.split("|")[-1] for c in stray]))
    source = data["bones"]
    game_now = scene_worlds(ch)
    # the forearm as the rig's drive chain holds it, its roll included: the bone itself never
    # rolls (AdvancedSkeleton moves the roll into the twist joints), and the hand's turn on the
    # unrolled bone carries whatever roll the forearm has in each pose
    forearm_now = pm.matrix(rigsolve.drive_matrices(ch.rig)["lowerarm_l"])
    forearm_card = pm.matrix(source["lowerarm_l"]["drive"])
    rows = []
    for leaf in members_t:
        if leaf == "hand_l":
            got = rel(game_now[leaf], forearm_now)
            want = rel(pm.matrix(source[leaf]["world"]), forearm_card)
        else:
            got = rel(game_now[leaf], game_now["hand_l"])
            want = rel(pm.matrix(source[leaf]["world"]), pm.matrix(source["hand_l"]["world"]))
        rows.append((leaf, pm.angle(got, want), 0.0))
    deg, _cm, at, _a = worst_of(rows)
    gate("partial the hand on the pose relative to the forearm's drive, the fingers to the hand",
         rows and deg <= 0.01, "%.6f deg (%s), %d bones" % (deg, at, len(rows)))
    gate("partial every value keyed", count == len(solution.values) and not key_notes,
         "%d of %d %s" % (count, len(solution.values), key_notes))
    ch.reset()


def run():
    t0 = time.time()
    say("plugin %s (posemath from %s)" % (PLUGIN, os.path.dirname(pm.__file__)))
    phase_save()
    for name, fn in (("rig-twin", phase_rig_twin), ("ik", phase_ik), ("neck", phase_neck),
                     ("cross", phase_cross), ("skeleton", phase_skeleton),
                     ("partial", phase_partial)):
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
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
if OUT is not None:
    OUT.close()

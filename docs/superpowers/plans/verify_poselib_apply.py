"""The Pose Library's Apply, end to end, in mayapy STANDALONE (2026-10-02).

Never in the animator's open Maya: this adds characters, keys them, makes animation layers,
undoes and finally starts a new scene. Run with a scratch MAYA_APP_DIR (the animator's prefs
never touched):

    $env:MAYA_APP_DIR = "<a scratch folder>"
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
        docs/superpowers/plans/verify_poselib_apply.py [out.txt]

Every gate prints `PASS/FAIL <name> <value>`, the run ends `SUMMARY x/y` (an optional file
argument gets the same lines). The plugin is the one beside this script (`<repo>/SkeldarAnim`;
`$env:POSELIB_PLUGIN` names another), its path the first line; `POSELIB_PHASES` narrows a run.
Every press goes through `maya_poselib.apply` exactly as the window calls it - `apply`,
`apply_onto`, `drop_floor`, `select_objects`, `Blend` - the cards made by `capture.build_pose`
of a selection; the scene is then re-evaluated by a real time change and the BONES measured
against the card, independently of the press's own measure.

  undo      Manny_Rig in another pose, half its channels keyed and half static, autoKey ON: a
            full card applied, then ONE `cmds.undo()` - every control channel back exactly,
            every curve key for key, no curve left over, autoKey still on; the same on the Manny
            skeleton.
  root      the second Manny_Rig moved (Main translate (300, 0, -120), rotate Y 70) and posed
            otherwise: the full card applied through a selected wrist control - Main unchanged,
            every member bone on the card's pose RELATIVE TO THE ROOT to 0.01 deg (the unrolled
            limb bones by where they point).
  mirror    a right-arm-and-hand card applied mirrored onto Manny_Rig in another pose: every
            left member ON ITS PARENT = the mirrored card's, each bone's root-space rotation
            mirrored as r_x . F . (r_o^-1 . p_o) . F (`o` its opposite, F the reflection across
            the card's sagittal plane, both computed here from the card's rests; the unrolled
            limb bones in their drive form, as the card holds them) to 0.05 deg; the right arm's
            controls unchanged. On its parent, not in root space: the transfer carries a bone
            relative to its nearest paired ancestor, and the target's chest stands in its own
            pose - in root space the arm reads off by the two chests' difference (115 deg at a
            finger in the first run, with the code right).
  blend     a Blend session at 0.5: every control's rotation HALFWAY (the quaternion angle from
            the current one is half the angle to the final one, and so is the rest of the way,
            0.01 deg), translations halfway; `cancel` - every value back exactly, and one Ctrl+Z
            then takes back the animator's last step before the session (a cancel leaves no undo
            step); a session at 0.3 finished - keys at the frame on the mixed values, «at 30 %»,
            one Ctrl+Z puts every channel and curve back; a session ended after the time moved
            (and previewed on at the new frame) - nothing keyed, the free channels at their
            start values, the keyed ones on their curves at the frame shown; the same cancelled
            with every other control's static channels in an animation layer, in DG evaluation
            and in parallel - the layered ones on their own values, also after the next time
            change (a static channel in a layer is not time-dependent: the settle dirties its
            feeding node).
  partial   the left-hand card onto the Manny skeleton (through its root) and onto Creep_Rig
            (through a control): only the hand's channels change - the skeleton's hand and finger
            joints, the Creep's FK wrist and finger controls and its IK arm's end (both modes
            keyed); the skeleton's hand on the card relative to its forearm, the fingers to the
            hand, through the two rests (0.01 deg).
  mixamo    a synthetic Mixamo skeleton (`mixamorig:` names, a T-pose rest in jointOrient,
            `tests/skeleton_conventions.py`'s rows, bound to a cube at its rest) posed, carded and
            applied onto Manny_Rig: every paired member POINTS where the source's bone does to
            0.1 deg, each in its root's rest frame (the card's root frame its ground frame: the
            Hips are its root and its pelvis); the target bones no source bone plays (spine_02,
            spine_04, neck_02 - Mixamo has three spine bones and one neck) on the transfer's
            rigid follow to 0.01 deg - neck_02 below a posed neck_01 stood 28.9 deg off it, the
            rig's neck in-between turning it, until rigsolve held it (`held_bones`).
  objects   two cubes posed, an objects card, applied to renamed copies in a namespace (by name,
            the namespace ignored): their attributes equal the card's, the originals untouched;
            the SELECTION decides - by order onto two differently named boxes WITH the originals
            in the scene (they do not move); by name and the rest by order (a copy and a box);
            nothing selected: the stored originals by their paths, the copies beside unmoved;
            two props of one leaf in two namespaces (`propA:ctrl`, `propB:ctrl`) each taking
            their own values, selected together and the second alone (the first unmoved).
  select    Select objects: the hand card's controls on Manny_Rig (`rigsolve.controls_for`),
            the hand's joints on the Manny skeleton, with nothing selected the character in the
            card's own namespace; an objects card's objects.
  layers    Manny_Rig keyed on the base: `plan_for` leaves no undo step; no layers -> plain keys
            on the base curves; an additive layer `PoseL` selected -> keys only on PoseL (every
            base curve key for key unchanged), the final pose on the card to 0.01 deg; an
            override layer the same; the override layer locked -> refused, nothing changed; an
            additive layer in quaternion accumulation -> refused, nothing changed.
  floor     a new scene, a locator selected: `drop_floor` of the Creep_Rig card at
            (150, 0, -60) - a Creep_Rig added with Main on the point (0.01 cm), its bones on the
            pose relative to the root (0.01 deg), the locator still the selection, one Ctrl+Z
            takes the pose keys and nothing else (the rig and its channels at Add's values);
            `drop_floor` of a Mixamo card (no catalog row) whose rest root stands OFF the origin
            (40, -25) - rebuilt bones only in `pose_<name>`, its root ON the point, every member
            on the card relative to the root (0.01 deg), its rest still the card's once posed
            (the hidden bind cube); one outliner group and layer over it, Delete's record
            («<card name> [own skeleton]»), and Delete taking it whole and nothing else.

Two harness facts this run paid for (mayapy 2027, measured): `currentTime` IS on Maya's undo
queue (one undo after `currentTime 6` put the time back to 5) and so is `autoKeyframe -state`
(trap 145) - a time change or an autoKey switch between a press and its `cmds.undo()` takes the
Ctrl+Z. The press re-evaluates its own frame; the gates read right after it.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Apply - where, and how",
"Keys - the active layer", "Blend", "The window").
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

# the plugin beside THIS script (<repo>/SkeldarAnim) - CLAUDE.md note 9; POSELIB_PLUGIN overrides
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
TESTS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "tests"))
if not os.path.isfile(os.path.join(PLUGIN, "maya_poselib", "apply.py")):
    raise ImportError("no plugin with maya_poselib.apply at %s" % PLUGIN)
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
from maya_scenesetup import catalog, character, chargroup, deletion  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

from maya_poselib import apply as ap  # noqa: E402
from maya_poselib import capture, keys, rigsolve, scene  # noqa: E402
from maya_poselib import posemath as pm  # noqa: E402

PHASES = [p.strip() for p in os.environ.get(
    "POSELIB_PHASES", "undo,root,mirror,blend,partial,mixamo,objects,select,layers,floor"
).split(",") if p.strip()]
OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []

ROT = ("rotateX", "rotateY", "rotateZ")
TR = ("translateX", "translateY", "translateZ")
NATIVE_REST = (40.0, 0.0, -25.0)     # the floor's native card: its rest moved off the origin
NATIVE_AT = (-100.0, 0.0, 50.0)      # ... and dropped here
UNROLLED_LIMB = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}
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


def matrix_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def scene_uuids():
    """Every node's UUID - `ls(uuid=True)` with no objects answers NAMES (trap 8)."""
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


def values_of(plugs):
    return dict((p, float(cmds.getAttr(p))) for p in plugs)


def set_values(values):
    for plug, value in values.items():
        cmds.setAttr(plug, value)


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


class Char(object):
    """One character of the run: its ref, its default channel values, a reset."""

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

    def reset(self):
        """Every key on its channels cut, every channel back at its value after Add."""
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

    def bones(self):
        return scene.skeleton(self.ref)[0]

    def game(self):
        return dict((leaf, b["path"]) for leaf, b in self.bones().items())


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
    out = {}
    for limb in ("Arm", "Leg"):
        for side in ("L", "R"):
            plug = ch.node("FKIK%s_%s" % (limb, side)) + ".FKIKBlend"
            if cmds.objExists(plug):
                out[plug] = float(cmds.getAttr(plug))
    return out


# ------------------------------------------------------------------ measures

def scene_worlds(ch):
    return dict((leaf, pm.rigid(W(path))) for leaf, path in ch.game().items())


def rel_rows(data, ch, members):
    """[(leaf, deg, cm)]: each non-twist member bone RELATIVE TO ITS ROOT against the card's,
    relative to the card's root - the four unrolled limb bones by where they point (toward the
    next limb bone)."""
    source = data["bones"]
    game = scene_worlds(ch)
    root = pm.root_of(ch.bones())
    s_root = pm.root_of(source)
    g_root, c_root = game[root], pm.rigid(source[s_root]["world"])
    rows = []
    for leaf in members:
        if leaf not in game or leaf not in source or pm.is_twist(leaf) or leaf == root:
            continue
        got, want = rel(game[leaf], g_root), rel(source[leaf]["world"], c_root)
        cm = (pm.position(got) - pm.position(want)).length()
        base = leaf[:-2] if leaf.endswith(("_l", "_r")) else leaf
        child = UNROLLED_LIMB.get(base)
        if child is not None and child + leaf[-2:] in game:
            child = child + leaf[-2:]
            a = (pm.position(game[child]) - pm.position(game[leaf])) * \
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


def target_members(data, ch, mirror=False):
    source, members = data["bones"], data["members"]
    if mirror:
        source, members = pm.mirror(source, members)
    bones = ch.bones()
    pairs = pm.pairs(source, bones)
    return ap.target_members(bones, pairs, members), pairs, bones


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


# ------------------------------------------------------------------ phases

CH = {}
CARDS = {}


def setup():
    t0 = time.time()
    for label, key in (("A", "Manny_Rig"), ("B", "Manny_Rig"), ("S", "Manny"),
                       ("C", "Creep_Rig")):
        handle = add(key)
        if handle is None:
            gate("setup add %s" % label, False, "nothing added")
            continue
        CH[label] = Char(label, handle)
    say("added %d characters in %.1f s: %s" % (len(CH), time.time() - t0, ", ".join(
        "%s=%s" % (k, ap.target_label(c.ref)) for k, c in sorted(CH.items()))))
    a = CH["A"]
    a.reset()
    set_values(pose_values(a))
    evaluate()
    CARDS["full"], note = capture.build_pose([a.rig.main])
    CARDS["hand"], hand_note = capture.build_pose([a.rig.main], regions=["Hand L"])
    CARDS["arm_r"], arm_note = capture.build_pose([a.rig.main], regions=["Arm R", "Hand R"])
    for card, name in ((CARDS["full"], "Full"), (CARDS["hand"], "Hand"),
                       (CARDS["arm_r"], "ArmR")):
        card["name"] = name
    say("   cards: %s | %s | %s" % (note, hand_note, arm_note))
    a.reset()
    c = CH["C"]
    c.reset()
    shipped = blends(c)
    for plug in shipped:
        cmds.setAttr(plug, 0.0)                    # every limb shown in FK for the capture
    set_values(pose_values(c, seed=0.5))
    evaluate()
    CARDS["creep"], creep_note = capture.build_pose([c.rig.main])
    CARDS["creep"]["name"] = "Creep"
    say("   creep card: %s" % creep_note)
    c.reset()
    set_values(shipped)
    evaluate()
    mixamo_card()
    # the floor's native card: a rest whose root stands OFF the origin, so «on the point» and
    # «at rest + point» are 47 cm apart (the first build landed the second)
    mixamo_card("mxo", NATIVE_REST, "mixamo_off", "SweepOff")
    off_root = pm.position(CARDS["mixamo_off"]["bones"][pm.root_of(
        CARDS["mixamo_off"]["bones"])]["rest"])
    gate("setup the off-origin native card's rest root", abs(off_root.x - NATIVE_REST[0]) < 1e-6
         and abs(off_root.z - NATIVE_REST[2]) < 1e-6,
         "(%.3f, %.3f, %.3f)" % (off_root.x, off_root.y, off_root.z))
    gate("setup cards", all(CARDS.get(k) for k in ("full", "hand", "arm_r", "creep", "mixamo",
                                                   "mixamo_off"))
         and
         CARDS["full"]["character"]["key"] == "Manny_Rig" and
         CARDS["creep"]["character"]["key"] == "Creep_Rig",
         "full %d members, hand %d, arm_r %d, creep %d" % tuple(
             len(CARDS[k]["members"]) for k in ("full", "hand", "arm_r", "creep")))


def keyed_half(ch, values):
    """Half the pose channels keyed (frames 0 and 10, the same value), the other half static."""
    keyed = sorted(values)[::2]
    for plug in keyed:
        cmds.setKeyframe(plug, time=0, value=values[plug])
        cmds.setKeyframe(plug, time=10, value=values[plug])
    for plug in sorted(values)[1::2]:
        cmds.setAttr(plug, values[plug])
    evaluate()
    return keyed


def undo_gate(label, ch, select):
    before_values = values_of(ch.plugs)
    before_curves = curve_state()
    cmds.autoKeyframe(state=True)
    ok, text = ap.apply(CARDS["full"], selection=[select])
    auto = cmds.autoKeyframe(query=True, state=True)
    say("   undo %s: %s" % (label, text))
    # no time change between the press and the Ctrl+Z: `currentTime` is on Maya's undo queue
    # (measured: one undo after `currentTime 6` put the time back to 5), so it would take the
    # Ctrl+Z; the press re-evaluated its frame itself
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in before_values.items())
    gate("undo %s the press keyed and moved the channels" % label, ok and moved > 1.0,
         "ok %s, max %.3f" % (ok, moved))
    gate("undo %s autoKey on before and after the press" % label, auto is True, "%s" % auto)
    cmds.undo()
    # autoKey off only now: `autoKeyframe -state` is on the undo queue too (trap 145) - switched
    # before the Ctrl+Z, it would take it
    cmds.autoKeyframe(state=False)
    evaluate()
    after_values = values_of(ch.plugs)
    worst = max(abs(after_values[p] - v) for p, v in before_values.items())
    at = max(before_values, key=lambda p: abs(after_values[p] - before_values[p]))
    gate("undo %s one Ctrl+Z: every channel back exactly" % label, worst <= 1e-9,
         "max %.3g (%s) over %d channels" % (worst, at.split("|")[-1], len(before_values)))
    changed, gone, new = curves_same(before_curves, curve_state())
    gate("undo %s one Ctrl+Z: every curve key for key, none left over" % label,
         not changed and not gone and not new,
         "%d changed, %d gone, %d new of %d" % (len(changed), len(gone), len(new),
                                                len(before_curves)))


def phase_undo():
    a, s = CH["A"], CH["S"]
    a.reset()
    cmds.currentTime(5)
    keyed = keyed_half(a, pose_values(a, seed=1.5))
    say("   undo Manny_Rig: %d channels keyed, %d static" % (len(keyed), len(a.plugs) - len(
        keyed)))
    undo_gate("Manny_Rig", a, a.node("FKWrist_L"))
    a.reset()
    s.reset()
    bones = s.bones()
    values = {}
    for i, leaf in enumerate(sorted(bones)):
        if pm.is_helper(leaf) or leaf == pm.root_of(bones):
            continue
        path = bones[leaf]["path"]
        for j, channel in enumerate(ROT):
            values[path + "." + channel] = float(cmds.getAttr(path + "." + channel)) + \
                7.0 * math.sin(i + 2.0 * j)
    keyed_half(s, values)
    undo_gate("Manny skeleton", s, s.root)
    s.reset()


def phase_root():
    b = CH["B"]
    b.reset()
    set_values(pose_values(b, seed=1.0))
    cmds.setAttr(b.rig.main + ".translate", 300.0, 0.0, -120.0)
    cmds.setAttr(b.rig.main + ".rotateY", 70.0)
    evaluate()
    main_before = W(b.rig.main)
    cmds.currentTime(8)
    ok, text = ap.apply(CARDS["full"], selection=[b.node("FKWrist_L")])
    say("   root: %s" % text)
    evaluate()
    gate("root Main unchanged", ok and matrix_diff(main_before, W(b.rig.main)) < 1e-9,
         "%.3g" % matrix_diff(main_before, W(b.rig.main)))
    members, _p, _b = target_members(CARDS["full"], b)
    rows = rel_rows(CARDS["full"], b, members)
    deg, cm, at_deg, at_cm = worst_of(rows)
    gate("root every member on the card relative to the root", rows and deg <= 0.01,
         "%.6f deg (%s), places %.6f cm (%s), %d bones" % (deg, at_deg, cm, at_cm, len(rows)))
    cmds.setAttr(b.rig.main + ".translate", 0.0, 0.0, 0.0)
    cmds.setAttr(b.rig.main + ".rotateY", 0.0)
    b.reset()


def _root_space(m, root):
    return pm.rotation(m) * pm.rotation(root).inverse()


def phase_mirror():
    a = CH["A"]
    a.reset()
    set_values(pose_values(a, seed=2.0))
    evaluate()
    card = CARDS["arm_r"]
    source = card["bones"]
    right = [m for m in card["members"] if not pm.is_twist(m)]
    right_controls = [p for p in a.plugs if "_R." in p.split("|")[-1] and
                      p.split("|")[-1].split(":")[-1].startswith(("FK", "IK", "Pole"))]
    before_right = values_of(right_controls)
    cmds.currentTime(6)
    ok, text = ap.apply(card, selection=[a.rig.main], mirror=True)
    say("   mirror: %s" % text)
    evaluate()
    # F: the reflection across the card's sagittal plane, in its root's rest frame
    root = pm.root_of(source)
    rest_root = pm.rotation(source[root]["rest"])
    across = (pm.position(source["upperarm_l"]["rest"]) -
              pm.position(source["upperarm_r"]["rest"])) * rest_root.inverse()
    axis = across.normal()
    flip = [1.0 if i == j else 0.0 for i in range(4) for j in range(4)]
    for i in range(3):
        for j in range(3):
            flip[i * 4 + j] -= 2.0 * axis[i] * axis[j]
    flip = om.MMatrix(flip)
    drives = rigsolve.drive_matrices(a.rig)
    game = scene_worlds(a)
    p_root = pm.matrix(source[root]["world"])

    def key_of(leaf):
        return "drive" if source[leaf].get("drive") else "world"

    def opposite(leaf):
        if leaf.endswith("_l"):
            return leaf[:-1] + "r"
        if leaf.endswith("_r"):
            return leaf[:-1] + "l"
        return leaf

    def mirrored(leaf):
        """The card's bone mirrored, in its root's space: r_x . F . (r_o^-1 . p_o) . F, `o` its
        opposite (a centre bone its own)."""
        other = opposite(leaf)
        r_x = _root_space(source[leaf]["rest"], source[root]["rest"])
        r_o = _root_space(source[other]["rest"], source[root]["rest"])
        p_o = _root_space(source[other][key_of(other)], p_root)
        return r_x * flip * (r_o.inverse() * p_o) * flip

    def shown(leaf):
        return pm.rotation(drives[leaf]) if key_of(leaf) == "drive" else \
            pm.rotation(game[leaf])

    # each left member on its parent (the transfer carries a bone relative to its nearest paired
    # ancestor - the target's chest stands in its own pose, not the card's: in root space the
    # arm would be off by the two chests' difference)
    rows = []
    for leaf_r in right:
        leaf_l = opposite(leaf_r)
        parent = source[leaf_l]["parent"]
        expected = mirrored(leaf_l) * mirrored(parent).inverse()
        got = shown(leaf_l) * shown(parent).inverse()
        rows.append((leaf_l, pm.angle(got, expected), 0.0))
    deg, _cm, at, _a = worst_of(rows)
    gate("mirror the left members take the mirror of the right's (each on its parent)",
         ok and rows and deg <= 0.05,
         "%.6f deg (%s), %d bones (%d in drive form)" % (
             deg, at, len(rows), sum(1 for r in right if source[r].get("drive"))))
    after_right = values_of(right_controls)
    moved = max(abs(after_right[p] - v) for p, v in before_right.items())
    gate("mirror the right arm's controls unchanged", moved <= 1e-9,
         "max %.3g over %d channels" % (moved, len(before_right)))
    a.reset()


def _q(values, order):
    return om.MEulerRotation(*([math.radians(v) for v in values] + [order])).asQuaternion()


def _qangle(a, b):
    d = a.inverse() * b
    v = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return math.degrees(2.0 * math.atan2(v, abs(d.w)))


def phase_blend():
    a = CH["A"]
    a.reset()
    cmds.currentTime(4)
    keyed_half(a, pose_values(a, seed=1.0))
    marker = cmds.spaceLocator(name="blendMarker")[0]
    cmds.setAttr(marker + ".translateX", 1.0)               # the animator's last step
    blend = ap.Blend()
    refusal = blend.start(CARDS["full"], selection=[a.rig.main])
    gate("blend a session starts", refusal == "" and blend.active(), refusal)
    current, final = {}, {}
    for plan, _extra in blend.entries:
        current.update(plan.current)
        final.update(plan.values)
    t0 = time.time()
    blend.set(0.5)
    took = time.time() - t0
    now = values_of(final)
    rows, moves = [], []
    for node, spec in ap.rotations_of(final).items():
        plugs, order = spec[:3], spec[3]
        q0, q1 = _q([current[p] for p in plugs], order), _q([final[p] for p in plugs], order)
        qn = _q([now[p] for p in plugs], order)
        whole = _qangle(q0, q1)
        rows.append((node, max(abs(_qangle(q0, qn) - 0.5 * whole),
                               abs(_qangle(qn, q1) - 0.5 * whole)), whole))
    for plug in final:
        if plug.rsplit(".", 1)[1] in TR:
            moves.append(abs(now[plug] - 0.5 * (current[plug] + final[plug])))
    worst = max(rows, key=lambda r: r[1])
    gate("blend at 0.5 every control's rotation halfway",
         rows and worst[1] <= 0.01 and max(r[2] for r in rows) > 5.0,
         "%.6f deg off half (%s), %d controls, the largest turn %.1f deg; set() %.3f s" % (
             worst[1], worst[0].split(":")[-1], len(rows), max(r[2] for r in rows), took))
    gate("blend at 0.5 translations halfway", moves and max(moves) <= 1e-6,
         "%.3g over %d channels" % (max(moves) if moves else -1, len(moves)))
    blend.cancel()
    back = values_of(final)
    off = max(abs(back[p] - current[p]) for p in final)
    gate("blend cancel: every value back exactly", off <= 1e-9 and not blend.active(),
         "max %.3g over %d channels" % (off, len(final)))
    cmds.undo()
    gate("blend cancel left no undo step (one Ctrl+Z takes the step before the session)",
         abs(cmds.getAttr(marker + ".translateX")) < 1e-12 and
         max(abs(float(cmds.getAttr(p)) - current[p]) for p in final) <= 1e-9,
         "marker tx %s" % cmds.getAttr(marker + ".translateX"))
    cmds.delete(marker)
    before_values = values_of(a.plugs)
    before_curves = curve_state()
    blend = ap.Blend()
    blend.start(CARDS["full"], selection=[a.rig.main])
    current, final = {}, {}
    for plan, _extra in blend.entries:
        current.update(plan.current)
        final.update(plan.values)
    blend.set(0.8)
    blend.set(0.3)
    text = blend.finish()
    say("   blend finish: %s" % text)
    mixed = ap.mix(current, final, 0.3, ap.rotations_of(final))
    # the press re-evaluated its frame; a time change here would take the Ctrl+Z below
    off = max(abs(float(cmds.getAttr(p)) - v) for p, v in mixed.items())
    keyed = [p for p in mixed if cmds.keyframe(p, query=True, time=(4, 4), keyframeCount=True)]
    gate("blend finish keys the mix at the frame", off <= 1e-6 and len(keyed) == len(mixed)
         and "at 30 %" in text, "max %.3g, %d of %d keyed at 4" % (off, len(keyed), len(mixed)))
    cmds.undo()
    evaluate()
    after = values_of(a.plugs)
    worst_v = max(abs(after[p] - v) for p, v in before_values.items())
    changed, gone, new = curves_same(before_curves, curve_state())
    gate("blend finish undone in one Ctrl+Z: every channel and curve back",
         worst_v <= 1e-9 and not changed and not gone and not new,
         "max %.3g, curves %d changed %d gone %d new" % (worst_v, len(changed), len(gone),
                                                         len(new)))
    # a session ended after the TIME moved: the free channels back at their start values, the
    # keyed ones on their curves at the frame now shown (the first build set their start values
    # - the OLD frame's - back, a stale value holding until the next time change)
    a.reset()
    cmds.currentTime(4)
    values = pose_values(a, seed=1.0)
    for plug in keyed_half(a, values):
        cmds.setKeyframe(plug, time=8, value=values[plug] + 15.0)     # the curves MOVE at 4..6
    evaluate()
    blend = ap.Blend()
    blend.start(CARDS["full"], selection=[a.rig.main])
    current, final = {}, {}
    for plan, _extra in blend.entries:
        current.update(plan.current)
        final.update(plan.values)
    blend.set(0.5)
    cmds.currentTime(6, update=True)                # the animator scrubbed
    blend.set(0.7)                                  # ... and dragged on at the new frame
    text = blend.finish()
    free = [p for p in final if keys.input_of(p) == "free"]
    keyed = [p for p in final if keys.input_of(p) == "curve"]

    def on_curve(plug):
        curve = cmds.listConnections(plug, source=True, destination=False, type="animCurve")[0]
        return cmds.keyframe(curve, query=True, eval=True, time=(6, 6))[0]
    free_off = max([abs(float(cmds.getAttr(p)) - current[p]) for p in free] or [0.0])
    keyed_off = max([abs(float(cmds.getAttr(p)) - on_curve(p)) for p in keyed] or [-1.0])
    moved = max([abs(on_curve(p) - current[p]) for p in keyed] or [0.0])
    gate("blend ended after a time change: free channels back, keyed ones on the frame shown",
         text == ap.TIME_MOVED and free and keyed and free_off <= 1e-9 and
         0.0 <= keyed_off <= 1e-6 and moved > 1.0 and not blend.active(),
         "free %d off %.3g, keyed %d off their curves at 6 %.3g (the curves moved %.1f since "
         "the start); %s" % (len(free), free_off, len(keyed), keyed_off, moved, text))
    # STATIC channels in an animation layer (Create Layer From Selected puts every static channel
    # of a control there), the time moved mid-blend, then cancel, in DG evaluation and in
    # parallel: every layered channel shows its own value again and keeps it through the next
    # time change. The 7m settle (a same-time `currentTime` alone) left them on the preview's -
    # an `animBlendNode` over no curve is not time-dependent - a value that then stood through
    # every time change for an S key or autoKey to bake (fix round 1)
    a.reset()
    cmds.currentTime(4)
    set_values(pose_values(a, seed=1.0))
    evaluate()
    planned = list(ap.plan_for(CARDS["full"], a.ref).values)
    nodes = []
    for plug in planned:
        if plug.rsplit(".", 1)[0] not in nodes:
            nodes.append(plug.rsplit(".", 1)[0])
    in_layer = set(nodes[::2])                     # every other control: layered and free mixed
    cmds.animLayer("BlendL")
    cmds.animLayer("BlendL", edit=True,
                   attribute=[p for p in planned if p.rsplit(".", 1)[0] in in_layer])
    mode = cmds.evaluationManager(query=True, mode=True)[0]
    try:
        for em in ("off", "parallel"):
            cmds.evaluationManager(mode=em)
            evaluate()
            blend = ap.Blend()
            refusal = blend.start(CARDS["full"], selection=[a.rig.main])
            current, final = {}, {}
            for plan, _extra in blend.entries:
                current.update(plan.current)
                final.update(plan.values)
            blend.set(0.5)
            cmds.currentTime(6, update=True)                # the animator scrubbed
            blend.set(0.7)                                  # ... and dragged on at the new frame
            shown = ap.mix(current, final, 0.7, ap.rotations_of(final))
            blend.cancel()
            layered = [p for p in final if keys.input_of(p) == "layer"]
            free = [p for p in final if keys.input_of(p) == "free"]

            def off(plugs):
                return max([abs(float(cmds.getAttr(p)) - current[p]) for p in plugs] or [-1.0])
            layered_off, free_off = off(layered), off(free)
            previewed = max([abs(shown[p] - current[p]) for p in layered] or [0.0])
            evaluate()                                      # the next time change
            later = off(layered)
            gate("blend cancelled after a time change, static channels in a layer (%s): back on "
                 "their own values" % em,
                 refusal == "" and layered and free and 0.0 <= layered_off <= 1e-6 and
                 0.0 <= later <= 1e-6 and 0.0 <= free_off <= 1e-9 and previewed > 1.0 and
                 not blend.active(),
                 "evaluation %s; layered %d off %.3g, after the next time change %.3g (the "
                 "preview had them up to %.1f off); free %d off %.3g" % (
                     cmds.evaluationManager(query=True, mode=True)[0], len(layered), layered_off,
                     later, previewed, len(free), free_off))
    finally:
        cmds.evaluationManager(mode=mode)
        if cmds.objExists("BlendL"):
            cmds.delete("BlendL")
        root = cmds.animLayer(query=True, root=True)
        if root and not cmds.animLayer(root, query=True, children=True):
            cmds.delete(root)
    a.reset()
    gate("blend layer cleaned up", keys.active_layer() == (None, ""), "%s, evaluation %s" % (
        keys.active_layer(), cmds.evaluationManager(query=True, mode=True)[0]))


def phase_partial():
    s, c = CH["S"], CH["C"]
    s.reset()
    card = CARDS["hand"]
    before = values_of(s.plugs)
    cmds.currentTime(9)
    ok, text = ap.apply(card, selection=[s.root])
    say("   partial skeleton: %s" % text)
    evaluate()
    members, _pairs, bones = target_members(card, s)
    allowed = set(bones[leaf]["path"] for leaf in members)
    changed = sorted(set(p.rsplit(".", 1)[0] for p in s.plugs
                         if abs(before[p] - float(cmds.getAttr(p))) > 1e-9))
    stray = [n for n in changed if n not in allowed]
    gate("partial Manny skeleton: only the hand's joints change", ok and changed and not stray,
         "%d changed, stray %s" % (len(changed), [n.split("|")[-1] for n in stray]))
    source = card["bones"]
    game = scene_worlds(s)
    rows = []
    for leaf in members:
        parent = "lowerarm_l" if leaf == "hand_l" else "hand_l"
        if leaf == parent or parent not in game:
            continue
        o = rel(bones[leaf]["rest"], source[leaf]["rest"])
        op = rel(bones[parent]["rest"], source[parent]["rest"])
        want = pm.rotation(o) * pm.rotation(rel(source[leaf]["world"], source[parent]["world"])) \
            * pm.rotation(op).inverse()
        rows.append((leaf, pm.angle(rel(game[leaf], game[parent]), want), 0.0))
    deg, _cm, at, _a = worst_of(rows)
    gate("partial Manny skeleton: the hand on the card on its forearm, the fingers on the hand",
         rows and deg <= 0.01, "%.6f deg (%s), %d bones" % (deg, at, len(rows)))
    s.reset()
    c.reset()
    set_values(pose_values(c, seed=1.0))
    evaluate()
    before = values_of(c.plugs)
    ok, text = ap.apply(card, selection=[c.node("FKShoulder_R")])
    say("   partial Creep_Rig: %s" % text)
    evaluate()
    members, _pairs, _bones = target_members(card, c)
    allowed = set()
    for leaf in members:
        base = rigsolve.bases(c.rig).get(leaf)
        if base and base.fk:
            allowed.add(base.fk)
    allowed.add((cmds.ls(c.node("IKArm_L"), long=True) or [""])[0])
    changed = sorted(set(p.rsplit(".", 1)[0] for p in c.plugs
                         if abs(before[p] - float(cmds.getAttr(p))) > 1e-6))
    stray = [n for n in changed if n not in allowed]
    gate("partial Creep_Rig: only the hand's controls change (its FK and the IK arm's end)",
         ok and changed and not stray,
         "%d changed, stray %s" % (len(changed), [n.split("|")[-1] for n in stray]))
    c.reset()


MIXAMO_POSE = {   # our bone: delta on the local rotate channels, degrees
    "upperarm_l": (10, 25, -40), "upperarm_r": (-15, 20, 35), "lowerarm_l": (0, 40, 10),
    "lowerarm_r": (10, -35, 0), "clavicle_l": (0, 10, 12), "hand_r": (20, 0, 25),
    "thigh_l": (35, 5, 0), "thigh_r": (-30, 0, 8), "calf_l": (0, 0, 50), "calf_r": (40, 0, 0),
    "foot_l": (10, 0, 15), "spine_01": (5, 20, 0), "spine_05": (0, -10, 8),
    "neck_01": (10, 0, 0), "head": (15, 10, 0), "index_01_l": (0, 0, 30),
    "thumb_01_l": (20, 0, 0), "pelvis": (5, 15, 0),
}


def build_mixamo(ns="mx", offset=None):
    """The Mixamo fixture as joints in `ns` (`mixamorig:` names inside it), oriented as Mixamo
    orients (Y down the bone, `yzx`), the T-pose rest in jointOrient - moved by `offset` (x, y,
    z) when given, so the rest's root stands off the origin - bound to a cube at that rest (a
    Mixamo character's bind is its skin's), then posed by MIXAMO_POSE. (top, {ours: path})."""
    rows, expected = fixtures.build("mixamo")
    for full in (ns, ns + ":mixamorig"):
        if not cmds.namespace(exists=":" + full):
            cmds.namespace(add=full.split(":")[-1], parent=":" + ":".join(full.split(":")[:-1]))
    made = {}
    for name, parent, pos in rows:
        under = made.get(parent)
        kwargs = {"name": "%s:%s" % (ns, name), "skipSelect": True}
        if under:
            kwargs["parent"] = cmds.ls(under, long=True)[0]
        joint = cmds.createNode("joint", **kwargs)
        joint = cmds.ls(joint, long=True)[0]
        cmds.xform(joint, worldSpace=True, translation=pos)
        made[name] = cmds.ls(joint, uuid=True)[0]

    def path(name):
        return cmds.ls(made[name], long=True)[0]
    top = path(rows[0][0])
    cmds.joint(top, edit=True, orientJoint="yzx", secondaryAxisOrient="yup", children=True,
               zeroScaleOrient=True)
    if offset:
        cmds.move(offset[0], offset[1], offset[2], top, relative=True, worldSpace=True)
    joints = [path(n) for n in made]
    cube = cmds.polyCube(name=ns + ":body", constructionHistory=False)[0]
    cmds.skinCluster(joints + [cube], toSelectedBones=True)
    for ours, delta in MIXAMO_POSE.items():
        if ours in expected:
            joint = path(expected[ours])
            rest = cmds.getAttr(joint + ".rotate")[0]
            cmds.setAttr(joint + ".rotate", *[r + d for r, d in zip(rest, delta)])
    evaluate()
    return path(rows[0][0]), dict((o, path(n)) for o, n in expected.items())


def pointing(data, ch):
    """[(leaf, deg, 0)]: every paired member with a direction child pointing where the source's
    bone does, each in its root's rest frame (the source's ground frame when it has no root of
    its own) - verify_poselib_solve's cross gate."""
    source = data["bones"]
    members, pairs, bones = target_members(data, ch)
    use_drive = ch.rig is not None
    p = dict((leaf, pm.matrix(b["drive"] if use_drive and b.get("drive") else b["world"]))
             for leaf, b in source.items())
    t_root, s_root = pm.root_of(bones), pm.root_of(source)
    rootless = not pm._own_root(pairs, source, t_root)
    now = dict((leaf, W(b["path"])) for leaf, b in bones.items())
    t_frame = pm.rotation(now[t_root]).inverse() * pm.rotation(bones[t_root]["rest"])
    pose_frame, rest_frame = pm._root_frames(source, s_root, p[s_root], rootless)
    s_frame = pm.rotation(pose_frame).inverse() * pm.rotation(rest_frame)
    children = direction_children(pairs, source, bones)
    rows = []
    for leaf in members:
        child = children.get(leaf)
        if child is None or child not in now:
            continue
        s, sc = pairs[leaf], pairs[child]
        if source[sc]["parent"] == s:
            want = pm.position(source[sc]["world"]) - pm.position(source[s]["world"])
        else:
            rest_dir = pm.position(source[sc]["rest"]) - pm.position(source[s]["rest"])
            want = rest_dir * pm.rotation(source[s]["rest"]).inverse() * pm.rotation(p[s])
        got = (pm.position(now[child]) - pm.position(now[leaf])) * t_frame
        rows.append((leaf, pm.direction_angle(got, want * s_frame), 0.0))
    return rows, rootless


def mixamo_card(ns="mx", offset=None, key="mixamo", name="Sweep"):
    """A Mixamo skeleton built (its rest moved by `offset`), carded as CARDS[key] and hidden
    (setup: the floor phase rebuilds the off-origin card)."""
    top, _by_ours = build_mixamo(ns, offset)
    data, note = capture.build_pose([top])
    data["name"] = name
    CARDS[key] = data
    cmds.setAttr(top + ".visibility", False)
    say("   %s card: %s; convention %s" % (key, note, data["character"]["convention"]))


def phase_mixamo():
    a = CH["A"]
    a.reset()
    data = CARDS["mixamo"]
    gate("mixamo the card is a character card with no catalog row",
         data["kind"] == "character" and data["character"]["key"] is None and
         len(data["members"]) > 40, "%d members, key %s" % (len(data["members"]),
                                                            data["character"]["key"]))
    cmds.currentTime(11)
    _plan, extra = ap._plan(data, a.ref)                  # where the transfer puts every bone
    unpaired_t = [leaf for leaf in ("spine_02", "spine_04", "neck_02") if leaf in extra.wanted
                  and leaf not in extra.members]
    ok, text = ap.apply(data, selection=[a.rig.main])
    say("   mixamo onto Manny_Rig: %s" % text)
    evaluate()
    game = a.game()
    held = [(leaf, pm.angle(W(game[leaf]), extra.wanted[leaf]),
             (pm.position(W(game[leaf])) - pm.position(extra.wanted[leaf])).length())
            for leaf in unpaired_t]
    deg, cm, at, _a = worst_of(held)
    # neck_02 below a posed neck_01 through the rig's neck in-between: 28.9 deg off before
    # rigsolve held it (task 7)
    gate("mixamo the bones no source bone plays stand on the transfer's rigid follow",
         held and deg <= 0.01 and cm <= 0.01, "%.6f deg (%s) %.6f cm | %s" % (
             deg, at, cm, ", ".join("%s %.4f" % (r[0], r[1]) for r in held)))
    rows, rootless = pointing(data, a)
    deg, _cm, at, _a = worst_of(rows)
    say("   mixamo worst rows: %s" % ", ".join(
        "%s %.4f" % (r[0], r[1]) for r in sorted(rows, key=lambda r: -r[1])[:6]))
    gate("mixamo onto Manny_Rig every paired member points where the source's does",
         ok and rows and deg <= 0.1 and rootless,
         "%.6f deg (%s), %d bones, rootless %s" % (deg, at, len(rows), rootless))
    a.reset()


def _cube(name, values):
    cube = cmds.polyCube(name=name, constructionHistory=False)[0]
    for attr, value in values.items():
        cmds.setAttr(cube + "." + attr, value)
    return cmds.ls(cube, long=True)[0]


def phase_objects():
    one = _cube("poseCubeA", {"translateX": 5.0, "translateY": 2.0, "rotateY": 33.0,
                              "scaleZ": 1.5})
    two = _cube("poseCubeB", {"translateZ": -4.0, "rotateX": -20.0, "rotateZ": 75.0,
                              "visibility": 1.0})
    data, note = capture.build_pose([one, two])
    data["name"] = "Cubes"
    CARDS["objects"] = data
    say("   objects card: %s" % note)
    if not cmds.namespace(exists=":copy"):
        cmds.namespace(add="copy")
    copies = []
    for cube in (one, two):
        dup = cmds.duplicate(cube)[0]
        dup = cmds.rename(dup, "copy:" + cube.split("|")[-1])
        dup = cmds.ls(dup, long=True)[0]
        for attr in ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ"):
            cmds.setAttr(dup + "." + attr, 9.0)
        copies.append(dup)
    originals = values_of([o + "." + a for o in (one, two)
                           for a in data["objects"][0]["attrs"]])
    cmds.currentTime(2)
    ok, text = ap.apply(data, selection=list(reversed(copies)))
    say("   objects onto the copies: %s" % text)
    evaluate()
    off = []
    for record in data["objects"]:
        copy = [c for c in copies if scene.leaf(c) == record["name"]][0]
        for attr, value in record["attrs"].items():
            off.append(abs(float(cmds.getAttr(copy + "." + attr)) - value))
    gate("objects onto renamed copies in a namespace: their attributes equal the card's",
         ok and off and max(off) <= 1e-6, "max %.3g over %d attributes" % (max(off), len(off)))
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in originals.items())
    gate("objects the originals untouched", moved <= 1e-9, "%.3g" % moved)
    # the SELECTION decides: two differently named boxes selected while the card's originals and
    # the copies are all in the scene - the pose goes onto the boxes by order, nothing else moves
    # (the first build sent it to the originals, found by path, and left the boxes alone)
    boxes = [_cube("boxOne", {}), _cube("boxTwo", {})]
    others = values_of([n + "." + a for n in [one, two] + copies
                        for a in data["objects"][0]["attrs"]])
    ok, text = ap.apply(data, selection=boxes)
    say("   objects by order: %s" % text)
    evaluate()
    off = [abs(float(cmds.getAttr(box + "." + attr)) - value)
           for box, record in zip(boxes, data["objects"])
           for attr, value in record["attrs"].items()]
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in others.items())
    gate("objects by selection order onto the selection, the originals in the scene",
         ok and max(off) <= 1e-6 and "selection order" in text and moved <= 1e-9,
         "max %.3g, the originals and copies moved %.3g" % (max(off), moved))
    # by name and the rest by order: copy:poseCubeA and a third box selected
    third = _cube("boxThree", {})
    copy_a = [c for c in copies if scene.leaf(c) == "poseCubeA"][0]
    for attr in ("translateX", "rotateY"):
        cmds.setAttr(copy_a + "." + attr, 9.0)
    others = values_of([n + "." + a for n in [one, two] + boxes
                        for a in data["objects"][0]["attrs"]])
    ok, text = ap.apply(data, selection=[third, copy_a])
    say("   objects by name, then by order: %s" % text)
    evaluate()
    by = dict((record["name"], record) for record in data["objects"])
    off = [abs(float(cmds.getAttr(node + "." + attr)) - value)
           for node, name in ((copy_a, "poseCubeA"), (third, "poseCubeB"))
           for attr, value in by[name]["attrs"].items()]
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in others.items())
    gate("objects by name, the selection left over by order",
         ok and max(off) <= 1e-6 and moved <= 1e-9 and "selection order" in text,
         "max %.3g, the unselected moved %.3g" % (max(off), moved))
    # nothing selected: the stored originals found in the scene (their exact paths), whatever
    # copies of them stand beside
    for node in (one, two):
        for attr in ("translateX", "rotateX"):
            cmds.setAttr(node + "." + attr, 9.0)
    others = values_of([n + "." + a for n in copies + boxes + [third]
                        for a in data["objects"][0]["attrs"]])
    ok, text = ap.apply(data, selection=[])
    say("   objects, nothing selected: %s" % text)
    evaluate()
    off = [abs(float(cmds.getAttr(node + "." + attr)) - value)
           for node, record in zip((one, two), data["objects"])
           for attr, value in record["attrs"].items()]
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in others.items())
    gate("objects nothing selected: the stored originals, by their paths",
         ok and max(off) <= 1e-6 and moved <= 1e-9,
         "max %.3g, the copies and boxes moved %.3g" % (max(off), moved))
    cmds.delete(copies + boxes + [third])
    if cmds.namespace(exists=":copy"):
        cmds.namespace(removeNamespace=":copy", mergeNamespaceWithRoot=True)
    # two referenced copies of one prop share a leaf (`|propA:ctrl`, `|propB:ctrl`): each takes
    # its OWN values, selected together or alone - the first rewrite gave every selected path the
    # first stored object of its leaf, so propB took propA's values (fix round 1)
    props = []
    for ns, values in (("propA", {"translateX": 1.0, "rotateY": 10.0}),
                       ("propB", {"translateX": 2.0, "rotateY": 20.0})):
        if not cmds.namespace(exists=":" + ns):
            cmds.namespace(add=ns)
        node = cmds.rename(_cube("ctrl_" + ns, values), ns + ":ctrl")
        props.append(cmds.ls(node, long=True)[0])
    prop_card, _note = capture.build_pose(props)
    prop_card["name"] = "Props"
    stored = dict((record["path"], record["attrs"]) for record in prop_card["objects"])

    def scramble():
        for node in props:
            for attr in ("translateX", "rotateY"):
                cmds.setAttr(node + "." + attr, 9.0)

    def own_off(nodes):
        return max(abs(float(cmds.getAttr(node + "." + attr)) - value)
                   for node in nodes for attr, value in stored[node].items())
    scramble()
    ok, text = ap.apply(prop_card, selection=list(reversed(props)))
    say("   objects, two same-named props: %s" % text)
    evaluate()
    both = own_off(props)
    gate("objects two same-named props selected: each takes its own values",
         ok and sorted(stored) == sorted(props) and both <= 1e-6,
         "max %.3g over %s" % (both, ", ".join(props)))
    cmds.cutKey(props, clear=True)                  # static again, so "unmoved" means unmoved
    scramble()
    first = values_of([props[0] + "." + attr for attr in stored[props[0]]])
    ok, text = ap.apply(prop_card, selection=[props[1]])
    say("   objects, the second prop alone: %s" % text)
    evaluate()
    alone = own_off([props[1]])
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in first.items())
    gate("objects the second same-named prop alone takes its own values, the first unmoved",
         ok and alone <= 1e-6 and moved <= 1e-9, "max %.3g, %s moved %.3g" % (
             alone, props[0], moved))
    cmds.delete(props)
    for ns in ("propA", "propB"):
        if cmds.namespace(exists=":" + ns):
            cmds.namespace(removeNamespace=":" + ns, mergeNamespaceWithRoot=True)


def phase_select():
    a, s = CH["A"], CH["S"]
    card = CARDS["hand"]
    members, _p, _b = target_members(card, a)
    want = set(rigsolve.controls_for(a.rig, members))
    ok, text = ap.select_objects(card, selection=[a.node("FKHead_M")])
    got = set(cmds.ls(selection=True, long=True) or [])
    gate("select the hand card's controls on Manny_Rig", ok and got == want and want,
         "%s; %d selected" % (text, len(got)))
    members, _p, bones = target_members(card, s)
    want = set(bones[leaf]["path"] for leaf in members)
    ok, text = ap.select_objects(card, selection=[s.root])
    got = set(cmds.ls(selection=True, long=True) or [])
    gate("select the hand card's joints on the Manny skeleton", ok and got == want,
         "%s; %d selected" % (text, len(got)))
    ok, text = ap.select_objects(card, selection=[])
    got = set(cmds.ls(selection=True, long=True) or [])
    members, _p, _b = target_members(card, a)
    gate("select with nothing selected: the card's own namespace among %d characters" % len(
        scene.all_characters()), ok and got == set(rigsolve.controls_for(a.rig, members)),
         text)
    if "objects" in CARDS:
        ok, text = ap.select_objects(CARDS["objects"], selection=[])
        got = sorted(scene.leaf(n) for n in cmds.ls(selection=True, long=True) or [])
        gate("select an objects card's objects", ok and got == ["poseCubeA", "poseCubeB"],
             "%s %s" % (text, got))
    else:
        say("   select: no objects card (the objects phase did not run)")
    cmds.select(clear=True)


def layer_curves(name):
    return set(cmds.animLayer(name, query=True, animCurves=True) or [])


def landed(ch, data, frame_):
    """(deg, cm, at) of the card's members on the card (the rig the card was made on, Main
    where it was): the unrolled limb bones by where they point."""
    cmds.currentTime(frame_, update=True)
    evaluate()
    members, _p, _b = target_members(data, ch)
    rows = rel_rows(data, ch, members)
    deg, cm, at, _a = worst_of(rows)
    return deg, cm, at


def phase_layers():
    a = CH["A"]
    a.reset()
    pose_b = pose_values(a, seed=1.0)
    for plug, value in sorted(pose_b.items()):
        cmds.setKeyframe(plug, time=0, value=value)
        cmds.setKeyframe(plug, time=10, value=value)
    card = CARDS["full"]
    # no layers at all: plain keys on the base curves
    gate("layers none in the scene", keys.active_layer() == (None, ""), "%s" % (
        keys.active_layer(),))
    cmds.currentTime(3)
    # plan_for leaves no undo step: the animator's last step is the next Ctrl+Z (the first build
    # left the rig solve's net-nothing chunk there)
    marker = cmds.spaceLocator(name="planMarker")[0]
    cmds.setAttr(marker + ".translateX", 1.0)
    plan = ap.plan_for(card, a.ref)
    cmds.undo()
    gate("layers plan_for leaves no undo step (one Ctrl+Z takes the step before it)",
         plan.values and abs(cmds.getAttr(marker + ".translateX")) < 1e-12,
         "%d values, marker tx %s" % (len(plan.values), cmds.getAttr(marker + ".translateX")))
    cmds.delete(marker)
    ok, text = ap.apply(card, selection=[a.rig.main])
    say("   no layers: %s" % text)
    on_base = []
    for plug, value in plan.values.items():
        curves = cmds.listConnections(plug, source=True, destination=False,
                                      type="animCurve") or []
        got = cmds.keyframe(curves[0], query=True, time=(3, 3), valueChange=True) if curves \
            else None
        on_base.append(bool(got) and abs(got[0] - value) <= 1e-6)
    deg, cm, at = landed(a, card, 3)
    gate("layers none: keys on the base curves, the pose on the card",
         ok and all(on_base) and deg <= 0.01 and "controls keyed at frame 3" in text,
         "%d of %d plugs keyed on their base curve at 3; %.6f deg (%s) %.6f cm" % (
             sum(on_base), len(on_base), deg, at, cm))
    # an additive layer selected
    cmds.animLayer("PoseL")
    cmds.animLayer("PoseL", edit=True, selected=True, preferred=True)
    before = curve_state()
    cmds.currentTime(5)
    ok, text = ap.apply(card, selection=[a.rig.main])
    say("   additive: %s" % text)
    changed, gone, new = curves_same(before, curve_state())
    in_layer = layer_curves("PoseL")
    gate("layers additive PoseL: keys only on PoseL, every base curve key for key",
         ok and new and set(new) <= in_layer and not changed and not gone and "on PoseL" in text,
         "%d new curves (%d in PoseL), %d base curves changed, %d gone of %d" % (
             len(new), len(set(new) & in_layer), len(changed), len(gone), len(before)))
    deg, cm, at = landed(a, card, 5)
    gate("layers additive PoseL: the final pose on the card", deg <= 0.01,
         "%.6f deg (%s) %.6f cm" % (deg, at, cm))
    # an override layer selected, the additive one not
    cmds.animLayer("PoseO", override=True)
    cmds.animLayer("PoseL", edit=True, selected=False, preferred=False)
    cmds.animLayer("PoseO", edit=True, selected=True, preferred=True)
    picked = keys.active_layer()[0]
    before = curve_state()
    cmds.currentTime(7)
    ok, text = ap.apply(card, selection=[a.rig.main])
    say("   override: %s" % text)
    changed, gone, new = curves_same(before, curve_state())
    in_layer = layer_curves("PoseO")
    gate("layers override PoseO: keys only on PoseO, every other curve key for key",
         ok and picked and picked.name == "PoseO" and new and set(new) <= in_layer and
         not changed and not gone,
         "%d new curves (%d in PoseO), %d others changed, %d gone" % (
             len(new), len(set(new) & in_layer), len(changed), len(gone)))
    deg, cm, at = landed(a, card, 7)
    gate("layers override PoseO: the final pose on the card", deg <= 0.01,
         "%.6f deg (%s) %.6f cm" % (deg, at, cm))
    # the override layer locked: refused, nothing changed
    cmds.animLayer("PoseO", edit=True, lock=True)
    cmds.currentTime(8)
    before = curve_state()
    before_values = values_of(a.plugs)
    ok, text = ap.apply(card, selection=[a.rig.main])
    changed, gone, new = curves_same(before, curve_state())
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in before_values.items())
    gate("layers locked: refused, nothing changed",
         not ok and "locked" in text and not changed and not gone and not new and moved <= 1e-9,
         "%s | curves %d/%d/%d, channels %.3g" % (text, len(changed), len(gone), len(new),
                                                  moved))
    cmds.animLayer("PoseO", edit=True, lock=False)
    # an additive layer accumulating rotation as QUATERNIONS (`rotationAccumulationMode` 1 - no
    # animLayer flag for it in Maya 2027, trap 41): refused, nothing changed
    cmds.animLayer("PoseQ")
    cmds.setAttr("PoseQ.rotationAccumulationMode", 1)
    cmds.animLayer("PoseO", edit=True, selected=False, preferred=False)
    cmds.animLayer("PoseQ", edit=True, selected=True, preferred=True)
    picked = keys.active_layer()[0]
    before = curve_state()
    before_values = values_of(a.plugs)
    ok, text = ap.apply(card, selection=[a.rig.main])
    changed, gone, new = curves_same(before, curve_state())
    moved = max(abs(float(cmds.getAttr(p)) - v) for p, v in before_values.items())
    gate("layers quaternion additive PoseQ: refused, nothing changed",
         picked is not None and picked.name == "PoseQ" and picked.quaternion and not ok and
         "quaternions" in text and not changed and not gone and not new and moved <= 1e-9,
         "%s | curves %d/%d/%d, channels %.3g" % (text, len(changed), len(gone), len(new),
                                                  moved))
    for name in ("PoseQ", "PoseO", "PoseL"):
        if cmds.objExists(name):
            cmds.delete(name)
    root = cmds.animLayer(query=True, root=True)
    if root and not cmds.animLayer(root, query=True, children=True):
        cmds.delete(root)
    a.reset()
    gate("layers cleaned up", keys.active_layer() == (None, ""), "%s" % (keys.active_layer(),))


def phase_floor():
    creep_defaults = dict((p.split("|")[-1].split(":")[-1], v)
                          for p, v in CH["C"].defaults.items())
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    cmds.undoInfo(state=True, infinity=True)
    cmds.currentTime(12)
    keep = cmds.ls(cmds.spaceLocator(name="keepSelected")[0], long=True)[0]
    cmds.select(keep, replace=True)
    t0 = time.time()
    ok, text = ap.drop_floor(CARDS["creep"], (150.0, 0.0, -60.0))
    took = time.time() - t0
    say("   floor Creep_Rig (%.1f s): %s" % (took, text))
    rigs = maya_rigs.rigs()
    rig = rigs[0] if len(rigs) == 1 else None
    gate("floor a Creep_Rig added", ok and rig is not None and rig.namespace.startswith(
        "Creep_Rig"), "%s" % [r.namespace for r in rigs])
    if rig is None:
        return
    main = pm.position(W(rig.main))
    off = (main - om.MVector(150.0, 0.0, -60.0)).length()
    gate("floor Main on the point", off <= 0.01, "%.6f cm (%.3f, %.3f, %.3f)" % (
        off, main.x, main.y, main.z))
    ch = Char("floor", rig)
    members, _p, _b = target_members(CARDS["creep"], ch)
    rows = rel_rows(CARDS["creep"], ch, members)
    deg, cm, at, at_cm = worst_of(rows)
    gate("floor its bones on the pose relative to the root", rows and deg <= 0.01,
         "%.6f deg (%s), places %.6f cm (%s), %d bones" % (deg, at, cm, at_cm, len(rows)))
    gate("floor the selection as before", cmds.ls(selection=True, long=True) == [keep],
         "%s" % cmds.ls(selection=True, long=True))
    timed = [c for c in cmds.listConnections(ch.plugs, source=True, destination=False,
                                             type="animCurve") or []]
    cmds.undo()
    evaluate()
    rigs = maya_rigs.rigs()
    left = cmds.listConnections(ch.plugs, source=True, destination=False,
                                type="animCurve") or []
    values = values_of(ch.plugs)
    off = [abs(v - creep_defaults[p.split("|")[-1].split(":")[-1]]) for p, v in values.items()
           if not p.split("|")[-1].split(":")[-1].startswith("Main.") and
           p.split("|")[-1].split(":")[-1] in creep_defaults]
    gate("floor one Ctrl+Z takes the pose keys and nothing else",
         timed and not left and len(rigs) == 1 and off and max(off) <= 1e-6 and
         cmds.objExists(keep) and cmds.ls(selection=True, long=True) == [keep],
         "%d curves before, %d after; rigs %d; channels at Add's values to %.3g" % (
             len(timed), len(left), len(rigs), max(off) if off else -1))
    # a card with no catalog row: rebuilt bones only - the off-origin card (its rest root at
    # NATIVE_REST), so «on the point» cannot pass as «at rest + point»
    card = CARDS.get("mixamo_off")
    if card is None:
        gate("floor native card", False, "no off-origin mixamo card (setup)")
        return
    before_drop = scene_uuids()
    ok, text = ap.drop_floor(card, NATIVE_AT)
    say("   floor native: %s" % text)
    bare = [r for r in skeletonimport.bare_roots() if maya_rigs.namespace_of(r).startswith(
        ap.NATIVE_PREFIX)]
    root = bare[0] if len(bare) == 1 else None
    gate("floor native rebuilt bones only in pose_<name>", ok and root is not None,
         "%s" % bare)
    if root is None:
        return
    ns = maya_rigs.namespace_of(root)
    joints = cmds.ls(ns + ":*", type="joint", long=True) or []
    meshes = cmds.ls(ns + ":*", type="mesh", long=True, noIntermediate=True) or []
    proxy = (cmds.ls(ns + ":" + ap.REST_PROXY, long=True) or [None])[0]
    gate("floor native: every bone of the card, one hidden bind cube",
         len(joints) == len(card["bones"]) and len(meshes) == 1 and proxy is not None and
         not cmds.getAttr(proxy + ".visibility"),
         "%d joints of %d, %d meshes" % (len(joints), len(card["bones"]), len(meshes)))
    rest_root = pm.position(card["bones"][pm.root_of(card["bones"])]["rest"])
    at_root = pm.position(W(root))
    off = math.hypot(at_root.x - NATIVE_AT[0], at_root.z - NATIVE_AT[2])
    # the first build stood it at rest + point: 47.17 cm away with this card
    gate("floor native: its root ON the point, whatever the card's rest", off <= 0.01,
         "%.6f cm (root at %.3f, %.3f, %.3f; the card's rest root at %.1f, %.1f)" % (
             off, at_root.x, at_root.y, at_root.z, rest_root.x, rest_root.z))
    ch = Char("native", root)
    members, _p, _b = target_members(card, ch)
    rows = rel_rows(card, ch, members)
    deg, cm, at, _a = worst_of(rows)
    gate("floor native: every member on the card relative to the root", rows and deg <= 0.01,
         "%.6f deg (%s) %.6f cm, %d bones" % (deg, at, cm, len(rows)))
    bones = ch.bones()
    drift = max(matrix_diff(bones[leaf]["rest"], card["bones"][leaf]["rest"])
                for leaf in card["bones"] if leaf in bones)
    gate("floor native: posed, its rest is still the card's (the bind cube)", drift <= 1e-6,
         "%.3g" % drift)
    # a character like every other: one group + layer, Delete's record, Delete takes it whole
    group = chargroup.group_of(root)
    layer = chargroup.layer_of(group)
    tops = [t for t in cmds.ls(assemblies=True, long=True) or []
            if maya_rigs.namespace_of(t) == ns]
    under = group is not None and maya_rigs.under(root, group) and proxy is not None and \
        maya_rigs.under((cmds.ls(ns + ":" + ap.REST_PROXY, long=True) or [""])[0], group)
    marker = cmds.getAttr(group + "." + chargroup.MARKER) if group else None
    gate("floor native: one outliner group and layer over its root and its bind cube",
         group is not None and group.count("|") == 1 and under and layer is not None and
         not tops and marker == card["name"] + " [own skeleton]",
         "group %s (%s), layer %s, world-level parts %s" % (group, marker, layer, tops))
    uuids, label = deletion.recorded(root)
    made = scene_uuids() - before_drop
    gate("floor native: Delete's record holds what the rebuild made, labelled as a native import",
         label == card["name"] + " [own skeleton]" and uuids and
         scene.skeleton_ref(root).label == label and
         cmds.ls(root, uuid=True)[0] in uuids and cmds.ls(proxy, uuid=True)[0] in uuids,
         "%d recorded of %d new nodes, label %r, ref label %r" % (
             len(uuids), len(made), label, scene.skeleton_ref(root).label))
    line = deletion.delete_selected([root], confirm=lambda question: True)
    after = scene_uuids()
    left = after - before_drop
    lost = before_drop - after
    gate("floor native: Delete takes it whole, nothing else",
         not left and not lost and not cmds.namespace(exists=":" + ns),
         "%s | %d left (%s), %d lost" % (line, len(left), ", ".join(sorted(
             (cmds.ls(u) or [u])[0] for u in left)[:6]), len(lost)))


def run():
    t0 = time.time()
    say("plugin %s (apply from %s)" % (PLUGIN, os.path.dirname(ap.__file__)))
    setup()
    for name, fn in (("undo", phase_undo), ("root", phase_root), ("mirror", phase_mirror),
                     ("blend", phase_blend), ("partial", phase_partial),
                     ("mixamo", phase_mixamo), ("objects", phase_objects),
                     ("select", phase_select), ("layers", phase_layers),
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
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
if OUT is not None:
    OUT.close()

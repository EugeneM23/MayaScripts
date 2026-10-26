"""Standalone gates for Dynamics (2026-10-26).

    mayapy verify_dynamics.py

mayapy STANDALONE, a fresh scene per case (spec docs/superpowers/specs/2026-10-26-bone-dynamics-design.md).
The prop: a transform keyed swinging along X (0 at frame 0, 30 at 12, 0 at 24, cycling) holding a chain
of five joints 6 cm apart hanging down its -Y. Frames 0..48.

A  + Chain and Simulate:
   - the chain node in a Dynamics group, five members, its carrier;
   - the layer Dynamics_hair_01, marked with the chain's UUID;
   - the scene plays what the solver answered: every member's world rotation to 0.001 deg, every frame;
   - the lengths kept; the chain swings (it lags the prop);
   - muted, the layer gives the animation back exactly.
B  A knob changed, re-solved from the reading: the same layer, its weight kept, the motion changed.
C  A capsule beside the swing and a floor: no joint inside either on any frame (the joint's radius).
D  The wind arrow blows the chain along its +Z.
E  Loop over 0..24: settled, the curves cycle, frame f and f + 24 the same, the seam no bigger than a
   step inside the cycle.
F  One undo takes the press back; Remove takes the layer and the setup (the colliders stay).
G  On Manny_Rig: an FK finger chain through the FKX joints, Auto body's capsules on the body and a
   floor, Simulate moving the game finger, Delete character taking the Dynamics group, the chain, its
   layer and the colliders.
"""
import math
import os
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
for _plugin in ("matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except Exception:
        pass

from maya_dynamics import model, run, setup  # noqa: E402

FAILS = []
COUNT = [0]
CASE = ["-"]
FRAMES = list(range(0, 49))


def case(name):
    CASE[0] = name
    print("--- %s" % name)


def gate(ok, msg):
    COUNT[0] += 1
    print("%s gate %02d [%s]: %s" % ("PASS" if ok else "FAIL", COUNT[0], CASE[0], msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append((CASE[0], COUNT[0], msg))


# ------------------------------------------------------------------ measure

def wm(node):
    return np.reshape(cmds.getAttr(node + ".worldMatrix[0]"), (4, 4))


def rows(m):
    u, _s, vt = np.linalg.svd(np.asarray(m, float)[:3, :3])
    return u @ vt


def angle(a, b):
    r = rows(a).T @ rows(b) if np.asarray(a).shape == (4, 4) else np.asarray(a).T @ np.asarray(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1.0) / 2.0))))


def pivot(node):
    return np.array(cmds.xform(node, query=True, worldSpace=True, rotatePivot=True))


def track(nodes, frames=FRAMES):
    """{frame: [(world matrix, pivot) per node]} by a real time walk (trap 69)."""
    out = {}
    now = cmds.currentTime(query=True)
    for f in frames:
        cmds.currentTime(f, update=True)
        out[f] = [(wm(n), pivot(n)) for n in nodes]
    cmds.currentTime(now, update=True)
    return out


class Spy(object):
    """model.simulate's answers during a press."""

    def __init__(self):
        self.answers = []
        self.original = run.model.simulate

    def __enter__(self):
        def spy(*args, **kwargs):
            answer = self.original(*args, **kwargs)
            self.answers.append(answer)
            return answer
        run.model.simulate = spy
        return self

    def __exit__(self, *exc):
        run.model.simulate = self.original
        return False


def prop_scene(frames=48, cycle=True):
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=frames, animationStartTime=0, animationEndTime=frames)
    prop = cmds.createNode("transform", name="prop")
    for t, x in ((0, 0.0), (12, 30.0), (24, 0.0)):
        cmds.setKeyframe(prop, attribute="translateX", time=t, value=x)
    if cycle:
        cmds.setInfinity(prop + ".translateX", preInfinite="cycle", postInfinite="cycle")
    cmds.setAttr(prop + ".translateY", 100.0)
    joints = []
    for i in range(5):
        cmds.select(joints[-1] if joints else prop, replace=True)
        joints.append(cmds.joint(position=(0.0, 100.0 - 6.0 * i, 0.0), name="hair_%02d" % (i + 1)))
    cmds.select(clear=True)
    joints = [cmds.ls(j, long=True)[0] for j in joints]
    cmds.currentTime(0)
    return cmds.ls(prop, long=True)[0], joints


def chain_for(joints, **given):
    made, notes, refusal = setup.add_chains([joints[0]], given)
    if refusal:
        raise RuntimeError(refusal)
    return made[0]


# --------------------------------------------------------------------- cases

def case_a():
    case("A chain")
    prop, joints = prop_scene()
    before = track(joints)
    chain = chain_for(joints, stiffness=0.15, damping=0.15, preroll=10)
    group = cmds.listRelatives(chain, parent=True, fullPath=True)[0]
    gate(setup._has(group, setup.GROUP_MARKER) and group == "|Dynamics",
         "the chain node in the Dynamics group: %s" % chain)
    gate(setup.members(chain) == joints, "five members, root first")
    gate(setup.carrier(chain) == prop, "the carrier is the prop: %s" % setup.carrier(chain))
    with Spy() as spy:
        line = run.simulate([chain], highlight=None)
    gate(line.startswith("hair_01: 5 joints, frames 0-48"), line)
    layer = setup.layer_of(chain)
    gate(layer == "Dynamics_hair_01" and cmds.getAttr(layer + "." + setup.LAYER_MARKER)
         == setup._uuid(chain), "the layer, marked with the chain: %s" % layer)
    after = track(joints)
    outs = spy.answers[-1][0][0]
    worst = max(angle(after[f][i][0][:3, :3], outs[i, f, :3, :3])
                for f in FRAMES for i in range(5))
    gate(worst < 1e-3, "the scene plays the solver: %.6f deg" % worst)
    lengths = [np.linalg.norm(after[f][i + 1][1] - after[f][i][1]) for f in FRAMES for i in range(4)]
    gate(max(abs(v - 6.0) for v in lengths) < 1e-4, "lengths kept: %.6f" % max(
        abs(v - 6.0) for v in lengths))
    swing = max(angle(after[f][0][0], before[f][0][0]) for f in FRAMES)
    gate(swing > 5.0, "the chain swings off its animation: up to %.2f deg" % swing)
    cmds.setAttr(layer + ".mute", True)
    muted = track(joints)
    cmds.setAttr(layer + ".mute", False)
    worst = max(angle(muted[f][i][0], before[f][i][0]) for f in FRAMES for i in range(5))
    gate(worst < 1e-6, "muted, the animation as it was: %.8f deg" % worst)
    return prop, joints, chain


def case_b():
    case("B re-solve")
    prop, joints = prop_scene()
    chain = chain_for(joints, stiffness=0.15, damping=0.15)
    run.simulate([chain], highlight=None)
    layer = setup.layer_of(chain)
    cmds.setAttr(layer + ".weight", 0.5)
    first = track(joints)
    s = setup.read_settings(chain)
    s["stiffness"] = 0.8
    setup.write_settings(chain, s)
    line = run.simulate([chain], highlight=None, reuse=True)
    second = track(joints)
    gate(setup.layer_of(chain) == layer and len(setup.layers()) == 1, "the same layer: " + line)
    gate(abs(cmds.getAttr(layer + ".weight") - 0.5) < 1e-9, "its weight kept 0.5")
    moved = max(angle(first[f][2][0], second[f][2][0]) for f in FRAMES)
    gate(moved > 1.0, "the motion changed: %.2f deg" % moved)


def case_c():
    case("C colliders")
    prop, joints = prop_scene()
    for t, y in ((0, 100.0), (12, 80.0), (24, 100.0)):    # the prop dips: the tip below the floor
        cmds.setKeyframe(prop, attribute="translateY", time=t, value=y)
    cmds.select(clear=True)
    post = cmds.joint(position=(-12.0, 60.0, -15.0), name="post")
    cmds.joint(position=(-12.0, 60.0, 15.0), name="post_end")
    post = cmds.ls(post, long=True)[0]
    capsule = setup.add_collider("capsule", post)
    cmds.setAttr(capsule + ".radius", 4.0)
    setup.redraw(capsule)
    floor = setup.add_floor(joints[0], height=62.0)
    chain = chain_for(joints, stiffness=0.0, damping=0.1, radius=1.0, radius_tip=1.0, preroll=0)
    with Spy() as spy:
        line = run.simulate([chain], highlight=None)
    gate("2 colliders" in line, line)
    outs, info = spy.answers[-1]
    gate(info["ignored"] == 0, "no joint started inside: %d" % info["ignored"])
    tails = outs[0][1:, :, 3, :3]
    a, b = np.array([-12.0, 60.0, -15.0]), np.array([-12.0, 60.0, 15.0])
    t = np.clip(((tails - a) @ (b - a)) / np.dot(b - a, b - a), 0.0, 1.0)
    near = a + t[..., None] * (b - a)
    clear = np.linalg.norm(tails - near, axis=-1) - 4.0 - 1.0
    gate(clear.min() > -1e-3, "no joint inside the capsule: least clearance %.4f cm" % clear.min())
    above = tails[..., 1] - 62.0 - 1.0
    gate(above.min() > -1e-3, "none under the floor: least %.4f cm" % above.min())
    reached = (np.abs(clear) < 0.5).any() or (np.abs(above) < 0.5).any()
    gate(reached, "the chain touched them (a contact within 0.5 cm)")
    gate(cmds.objExists(floor) and setup.kind_of(floor) == "plane", "the floor is a plane collider")


def case_d():
    case("D wind")
    prop, joints = prop_scene()
    chain = chain_for(joints, stiffness=0.3, damping=0.3)
    calm = None
    with Spy() as spy:
        run.simulate([chain], highlight=None)
    calm = spy.answers[-1][0][0]
    wind = setup.add_wind()
    cmds.setAttr(wind + ".rotateY", 0.0)                 # +Z
    cmds.setAttr(wind + ".strength", 0.5)
    cmds.setAttr(wind + ".turbulence", 0.0)
    cmds.setAttr(wind + ".gust", 0.0)
    with Spy() as spy:
        line = run.simulate([chain], highlight=None)
    windy = spy.answers[-1][0][0]
    gate(", wind -" in line, line)
    push = float(np.mean(windy[-1, :, 3, 2] - calm[-1, :, 3, 2]))
    gate(push > 1.0, "the tip blown along +Z: %.2f cm on average" % push)


def case_e():
    case("E loop")
    prop, joints = prop_scene(frames=24)
    chain = chain_for(joints, stiffness=0.2, damping=0.2, loop=True)
    line = run.simulate([chain], highlight=None)
    gate("Loop settled" in line, line)
    layer = setup.layer_of(chain)
    curves = [c for c in cmds.ls(type="animCurve") or []
              if cmds.listConnections(c + ".output", type="animBlendNodeBase")]
    cycled = all(cmds.getAttr(c + ".postInfinity") == 3 for c in curves)
    gate(curves and cycled, "the layer's %d curves cycle" % len(curves))
    cmds.playbackOptions(min=0, max=48)
    long_track = track(joints, list(range(0, 49)))
    period = max(angle(long_track[f][i][0], long_track[f + 24][i][0])
                 for f in range(0, 24) for i in range(5))
    gate(period < 0.01, "frame f and f + 24 the same: %.5f deg" % period)
    steps = [max(angle(long_track[f][i][0], long_track[f + 1][i][0]) for i in range(5))
             for f in range(0, 30)]
    inside = max(steps[0:23])
    seam = steps[23]
    gate(seam <= 1.5 * inside + 1e-6, "the seam %.4f deg against %.4f inside" % (seam, inside))
    gate(layer is not None, "the layer: %s" % layer)


def case_f():
    case("F undo, Remove")
    prop, joints = prop_scene()
    chain = chain_for(joints)
    capsule = setup.add_collider("sphere", joints[2])
    before = track(joints)
    run.simulate([chain], highlight=None)
    gate(setup.layer_of(chain) is not None, "simulated")
    cmds.undo()
    gate(setup.layer_of(chain) is None and not setup.layers(), "one undo takes the layer back")
    after = track(joints)
    worst = max(angle(after[f][i][0], before[f][i][0]) for f in FRAMES for i in range(5))
    gate(worst < 1e-6, "the animation as before: %.8f deg" % worst)
    run.simulate([chain], highlight=None)
    line = run.remove([chain])
    gate(not setup.chains() and not setup.layers() and not cmds.ls(type="animLayer"),
         "Remove: no chain, no layer, no BaseAnimation - " + line)
    gate(cmds.objExists(capsule), "the collider stays")


def case_g():
    case("G Manny_Rig")
    from maya_scenesetup import catalog, character, deletion
    import maya_rigs
    cmds.file(new=True, force=True)
    cmds.playbackOptions(min=0, max=40, animationStartTime=0, animationEndTime=40)
    character.add_character(catalog.default_rig())
    rig = maya_rigs.rigs()[0]
    elbow = cmds.ls(maya_rigs.node(rig, "FKElbow_R"), long=True)[0]
    for t, value in ((0, 0.0), (10, -70.0), (20, 0.0), (40, 0.0)):
        cmds.setKeyframe(elbow, attribute="rz", time=t, value=value)
    finger = cmds.ls(maya_rigs.node(rig, "FKIndexFinger1_R"), long=True)[0]
    made, notes, refusal = setup.add_chains([finger], {"stiffness": 0.1, "damping": 0.1})
    gate(not refusal and len(made) == 1, "+ Chain on FKIndexFinger1_R: %s %s" % (made, refusal))
    chain = made[0]
    names = [setup.leaf(m) for m in setup.members(chain)]
    gate(names[:3] == ["FKIndexFinger1_R", "FKIndexFinger2_R", "FKIndexFinger3_R"],
         "the FK controls through the FKX joints: %s" % names)
    gate(setup.carrier(chain) == cmds.ls(maya_rigs.node(rig, "Main"), long=True)[0],
         "the carrier is Main")
    colliders, refusal = setup.auto_body([finger])
    kinds = [setup.kind_of(c) for c in colliders]
    gate(not refusal and kinds.count("capsule") >= 10 and kinds.count("plane") == 1,
         "Auto body: %d capsules and a floor %s" % (kinds.count("capsule"), refusal))
    head = [c for c in colliders if setup._get(c, setup.AUTO_MARKER) == "head"]
    bone = [j for j in cmds.ls(type="joint", long=True)
            if setup.leaf(j) == "head" and maya_rigs.under(j, rig.skeleton_root)][0]
    centre = wm(head[0])[3, :3] if head else np.zeros(3)
    gate(head and np.linalg.norm(centre - pivot(bone)) < 20.0,
         "the head's capsule by the head: %.1f cm" % np.linalg.norm(centre - pivot(bone)))
    again, _r = setup.auto_body([finger])
    gate(len([c for c in setup.colliders() if setup._has(c, setup.AUTO_MARKER)])
         == len([c for c in again if setup._has(c, setup.AUTO_MARKER)]),
         "a second Auto body replaces the first")
    game = [j for j in cmds.ls(type="joint", long=True)
            if setup.leaf(j) == "index_02_r" and maya_rigs.under(j, rig.skeleton_root)][0]
    before = track([game], list(range(0, 41)))
    line = run.simulate([chain], highlight=None)
    gate(line.startswith("FKIndexFinger1_R: "), line)
    after = track([game], list(range(0, 41)))
    moved = max(angle(after[f][0][0], before[f][0][0]) for f in range(0, 41))
    gate(moved > 1.0, "the game finger index_02_r moved: up to %.2f deg" % moved)
    layer = setup.layer_of(chain)
    deletion.delete_selected([elbow], confirm=lambda text: True)
    gate(not setup.chains() and not setup.colliders() and not cmds.objExists(layer or "x")
         and not cmds.ls("*." + setup.GROUP_MARKER, recursive=True, objectsOnly=True),
         "Delete character takes the group, the chain, its layer and the colliders")


def main():
    for case_run in (case_a, case_b, case_c, case_d, case_e, case_f, case_g):
        try:
            case_run()
        except Exception:
            import traceback
            traceback.print_exc()
            gate(False, "%s raised" % case_run.__name__)
    print("verify_dynamics: %d gates, %d failed%s" % (
        COUNT[0], len(FAILS), "".join("\n  %s gate %02d: %s" % f for f in FAILS)))


main()

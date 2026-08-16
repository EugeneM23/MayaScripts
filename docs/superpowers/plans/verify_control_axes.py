"""Live proof that FK controllers stand in their bones' axes.

Sent through the command port against a scene holding the skeleton. The script
builds the rig itself, in two halves, so the turning step can be measured on
its own:

  phase 1 -- build the hybrid rig with `orient_controllers` suppressed, which
             is exactly the rig this project shipped before this change;
  phase 2 -- run `orient_controllers` for real and measure what moved.

Gates, in order of what matters:

1. Bones do not move. The knots turn and the driver locators are counter-
   rotated; if that is wrong the whole character shifts. Measured over every
   bone at every frame.
2. Every controller stands in its bone's frame -- the thing the animator grabs.
3. The rotate channels are still in the bone's axes and still read zero at the
   build pose: this change must not spend what the previous one bought.
4. What the animator grabs and what the finger does are the same axis. Measured
   before and after the turn, on a finger, which is where it was reported.
5. Equal values on a left/right pair still mirror the pose, and the rest frames
   now mirror the way the skeleton does.

Nothing is undone with `cmds.undo()` -- the whole bridge script is one command
and undoing inside it reverts a prior chunk. Poked values are read first and
written back.
"""

import math
import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)
for _name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[_name]

import maya.cmds as cmds
import maya.api.OpenMaya as om

from maya_overrig import axes, bodymap, builder, fkcontrols, naming

failures = []


def check(label, condition, detail=""):
    print("%-56s %s %s" % (label, "PASS" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def world(node):
    return om.MMatrix(cmds.xform(node, query=True, worldSpace=True,
                                 matrix=True))


def world_rot(node):
    return axes._rotation_only(world(node))


def parent_rot(node):
    parents = cmds.listRelatives(node, parent=True, fullPath=True)
    return world_rot(parents[0]) if parents else om.MMatrix()


def rows_of(matrix):
    return ((matrix[0], matrix[1], matrix[2]),
            (matrix[4], matrix[5], matrix[6]),
            (matrix[8], matrix[9], matrix[10]))


# --- the bound skeleton, resolved the way the panel does --------------------
root = builder.character_roots()[0]
mapping = naming.hierarchy_map(root)
prefix = naming.detect_prefix(list(mapping), {b.joint for b in bodymap.BUTTONS})
SCENE = naming.strip_prefix(mapping, prefix)
print("skeleton root: %s, %d joints mapped" % (root, len(SCENE)))

frame = cmds.currentTime(query=True)
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
print("timeline %d..%d, current frame %s" % (start, end, frame))

BONES = [SCENE[j] for _, chain in fkcontrols.CHAINS for j in chain
         if j in SCENE and cmds.objExists(SCENE[j])]

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
selection = cmds.ls(selection=True, long=True)

# The scene must not already carry the animator's work: this script keys bones
# to give the drift gate something to measure, and resets them afterwards.
# The test is whether a curve MOVES, not whether one exists -- every build
# leaves the bones carrying constant baked curves, so "has animCurves" reads
# true on a perfectly idle skeleton and would skip the reset for ever after.
moving = []
for _bone in BONES:
    for _curve in cmds.listConnections(_bone, type="animCurve") or []:
        if not fkcontrols.is_constant(
                cmds.keyframe(_curve, query=True, valueChange=True) or [],
                1e-4):
            moving.append(_bone)
            break
virgin = not moving
print("bones carrying real animation: %d%s" % (
    len(moving), "" if virgin else " - reset and cleanup will be skipped"))

# --- phase 1: the rig as it was --------------------------------------------
print()
print("=== phase 1: build with the turn suppressed ===")
if fkcontrols.has_fk():
    fkcontrols.bake_fk(SCENE)
if builder.has_build():
    builder.bake_limbs(SCENE, builder.built_limbs())
REST = {}
if virgin:
    cmds.cutKey(BONES, clear=True)
    # Back onto the pose the file holds. `cutKey` leaves a bone wherever it
    # last evaluated, and a build bakes the pose the skeleton stands in --
    # so a run that started from a bent skeleton would bake the bend in.
    for pose in cmds.ls(type="dagPose") or []:
        if cmds.getAttr(pose + ".bindPose"):
            cmds.select(cmds.ls(root, long=True)[0], hierarchy=True,
                        replace=True)
            cmds.dagPose(pose, restore=True, g=True)
    cmds.select(clear=True)
    cmds.currentTime(frame, edit=True)

    REST = {bone: cmds.xform(bone, query=True, worldSpace=True, matrix=True)
            for bone in BONES}

    # Keys relative to what each bone already holds: the bind orientation of
    # this skeleton lives in its ROTATE channels, so keying a literal 0 would
    # bend the skeleton rather than leave it alone.
    for bone, attr, delta in (("spine_03", "rotateZ", 18.0),
                              ("index_02_l", "rotateZ", -40.0),
                              ("thumb_02_r", "rotateZ", 25.0)):
        base = cmds.getAttr(SCENE[bone] + "." + attr)
        cmds.setKeyframe(SCENE[bone], attribute=attr, time=start, value=base)
        cmds.setKeyframe(SCENE[bone], attribute=attr, time=end,
                         value=base + delta)
    print("keyed spine_03, index_02_l, thumb_02_r off their rest values")

real_orient = fkcontrols.orient_controllers
fkcontrols.orient_controllers = lambda *a, **k: 0
try:
    print("build:", fkcontrols.rebuild(SCENE, fk_limbs=False))
finally:
    fkcontrols.orient_controllers = real_orient

CTRLS = [(fkcontrols.controller_name(j), SCENE[j])
         for _, chain in fkcontrols.CHAINS for j in chain
         if j in SCENE and cmds.objExists(fkcontrols.controller_name(j))]
TURNABLE = [(c, b) for c, b in CTRLS
            if cmds.attributeQuery("jointOrient", node=c, exists=True)]
print("%d controllers built, %d of them joints" % (len(CTRLS), len(TURNABLE)))


def frame_gap(ctrl, bone):
    """Angle between the controller's own frame and the bone's."""
    return axes.angle_of(axes.frame_offset(world_rot(bone), world_rot(ctrl)))


def channel_gap(ctrl, bone):
    """Angle between the frame the rotate channels act in and the bone's."""
    orient = fkcontrols._euler_matrix(cmds.getAttr(ctrl + ".jointOrient")[0])
    return axes.angle_of(axes.frame_offset(world_rot(bone),
                                           orient * parent_rot(ctrl)))


before_gap = max(frame_gap(c, b) for c, b in TURNABLE)
print("worst controller-to-bone frame gap before: %.3f deg" % before_gap)


def sample_bones():
    table = {}
    for f in range(start, end + 1):
        cmds.currentTime(f, edit=True)
        table[f] = [cmds.xform(b, query=True, worldSpace=True, matrix=True)
                    for b in BONES]
    cmds.currentTime(frame, edit=True)
    return table


def deviation(before, after):
    worst = 0.0
    for f, rows in before.items():
        for a, b in zip(rows, after[f]):
            worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
    return worst


class poked(object):
    """Set a controller's rotate for a measurement, then put it back exactly.

    A scripted poke at a keyed channel must not create or destroy keys: the
    existing key's value is edited and restored, never re-keyed.
    """

    def __init__(self, ctrl, values, time):
        self.ctrl, self.values, self.time = ctrl, values, time

    def set(self, values):
        self._write(values)
        self._settle()

    def _write(self, values):
        for attr, value in zip(fkcontrols._ROTATE_CHANNELS, values):
            if cmds.keyframe(self.ctrl, attribute=attr, query=True,
                             time=(self.time, self.time), valueChange=True):
                cmds.keyframe(self.ctrl, attribute=attr,
                              time=(self.time, self.time), valueChange=value,
                              absolute=True)
            else:
                cmds.setAttr(self.ctrl + "." + attr, value)

    def _settle(self):
        """A read straight after a write returns a stale mixture across nodes.
        Wiggling time is what makes the scene answer honestly."""
        cmds.currentTime(self.time + 1, edit=True)
        cmds.currentTime(self.time, edit=True)

    def __enter__(self):
        cmds.currentTime(self.time, edit=True)
        self.original = list(cmds.getAttr(self.ctrl + ".rotate")[0])
        self._write(self.values)
        self._settle()
        return self

    def __exit__(self, *exc):
        self._write(self.original)
        self._settle()
        return False


def turn_axis(ctrl, bone, channel=2, amount=30.0):
    """(the axis you grab, the axis the bone turns about, how far) for one
    channel, measured from the zeroed controller.

    Zeroing first is what makes the question well posed. Away from zero the
    euler channels interleave -- rotateZ turns about the REST frame's Z, not
    about where the controller points now -- which is ordinary euler
    behaviour on any rig and not what this gate is asking about.
    """
    cmds.currentTime(frame, edit=True)
    values = [0.0, 0.0, 0.0]
    values[channel] = amount
    with poked(ctrl, [0.0, 0.0, 0.0], frame) as pose:
        rest = world_rot(bone)
        grab = rows_of(world_rot(ctrl))[channel]
        pose.set(values)
        moved = world_rot(bone)
    quat = om.MTransformationMatrix(rest.inverse()
                                    * moved).rotation(asQuaternion=True)
    vector, angle = quat.asAxisAngle()
    if angle < 0:
        vector, angle = -vector, -angle
    return grab, vector.normal(), math.degrees(angle)


def angle_between(a, b):
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    return math.degrees(math.acos(abs(dot)))


FINGER = ("index_02_l_FK_ctrl", SCENE["index_02_l"])
grab_before = None
if cmds.objExists(FINGER[0]):
    grab, motion, swing = turn_axis(*FINGER)
    grab_before = angle_between(motion, grab)
    print("finger before: rotateZ turns the bone %.2f deg about an axis "
          "%.2f deg from the controller's own Z" % (swing, grab_before))

before = sample_bones()

# --- phase 2: turn the knots onto their bones -------------------------------
print()
print("=== phase 2: orient_controllers ===")
cmds.undoInfo(openChunk=True, chunkName="verify_control_axes")
try:
    turned = fkcontrols.orient_controllers(SCENE)
finally:
    cmds.undoInfo(closeChunk=True)
print("turned %d controller(s)" % turned)

after = sample_bones()

# --- gate 1: nothing moved --------------------------------------------------
print()
drift = deviation(before, after)
check("gate 1: bones unmoved (%d frames, %d bones)" % (len(before),
                                                       len(BONES)),
      drift < 1e-4, "worst %.3e" % drift)

# --- gate 2: the controller stands in the bone's frame ----------------------
worst_gap, worst_ctrl = 0.0, None
for ctrl, bone in TURNABLE:
    gap = frame_gap(ctrl, bone)
    if gap > worst_gap:
        worst_gap, worst_ctrl = gap, ctrl
check("gate 2: controller frames on the bones", worst_gap < 0.01,
      "worst %.5f (%s), was %.3f" % (worst_gap, worst_ctrl, before_gap))

worst_axis, axis_ctrl = 0.0, None
for ctrl, _ in TURNABLE:
    largest = max(abs(v) for v in cmds.getAttr(ctrl + ".rotateAxis")[0])
    if largest > worst_axis:
        worst_axis, axis_ctrl = largest, ctrl
check("gate 2b: rotateAxis is gone", worst_axis < 0.001,
      "worst %.6f (%s)" % (worst_axis, axis_ctrl))

# --- gate 3: the channels are untouched -------------------------------------
worst_chan, chan_ctrl = 0.0, None
for ctrl, bone in TURNABLE:
    gap = channel_gap(ctrl, bone)
    if gap > worst_chan:
        worst_chan, chan_ctrl = gap, ctrl
check("gate 3: channels still in the bone axes", worst_chan < 0.01,
      "worst %.5f (%s)" % (worst_chan, chan_ctrl))

worst_zero, zero_ctrl = 0.0, None
for ctrl, _ in TURNABLE:
    largest = max(abs(v) for v in cmds.getAttr(ctrl + ".rotate")[0])
    if largest > worst_zero:
        worst_zero, zero_ctrl = largest, ctrl
check("gate 3b: controllers read zero at the build pose", worst_zero < 0.01,
      "worst %.5f (%s)" % (worst_zero, zero_ctrl))

# --- gate 4: grab and motion are the same axis ------------------------------
if grab_before is not None:
    grab, motion, swing = turn_axis(*FINGER)
    grab_after = angle_between(motion, grab)
    check("gate 4: the finger turns about the axis you grab",
          grab_after < 0.5 and abs(swing - 30.0) < 0.01,
          "%.3f deg apart (was %.2f), swing %.2f" % (grab_after, grab_before,
                                                     swing))

# --- gate 5: mirroring ------------------------------------------------------
pairs = [(c, b, c.replace("_l_", "_r_")) for c, b in TURNABLE
         if "_l_" in c and cmds.objExists(c.replace("_l_", "_r_"))]
bad = []
behaviour = 0
for left, left_bone, right in pairs:
    right_bone = SCENE[naming.leaf(left_bone).replace("_l", "_r")]
    ctrl_signs = axes.mirror_signs(rows_of(world_rot(left)),
                                   rows_of(world_rot(right)))
    bone_signs = axes.mirror_signs(rows_of(world_rot(left_bone)),
                                   rows_of(world_rot(right_bone)))
    if ctrl_signs != bone_signs:
        bad.append("%s ctrl%s bone%s" % (left, ctrl_signs, bone_signs))
    if ctrl_signs == (-1, -1, -1):
        behaviour += 1
    else:
        print("  not a behaviour mirror in the skeleton either: %s %s"
              % (left, ctrl_signs))
check("gate 5: rest frames mirror as the bones do (%d pairs)" % len(pairs),
      not bad, "; ".join(bad[:3]) if bad else
      "%d/%d also read the behaviour mirror (-1,-1,-1)"
      % (behaviour, len(pairs)))

WATCH = [("index_02_l", "index_02_r"), ("index_03_l", "index_03_r"),
         ("thumb_02_l", "thumb_02_r")]
root_inverse = world(SCENE["root"]).inverse()


def in_root(node):
    point = cmds.xform(node, query=True, worldSpace=True, translation=True)
    moved = om.MPoint(point[0], point[1], point[2]) * root_inverse
    return (moved.x, moved.y, moved.z)


with poked("index_02_l_FK_ctrl", (12.0, -8.0, -35.0), frame):
    with poked("index_02_r_FK_ctrl", (12.0, -8.0, -35.0), frame):
        worst_mirror = 0.0
        for left, right in WATCH:
            want = list(in_root(SCENE[left]))
            want[0] *= -1.0
            got = in_root(SCENE[right])
            worst_mirror = max(worst_mirror,
                               max(abs(a - b) for a, b in zip(want, got)))
check("gate 5b: equal values give a mirrored pose", worst_mirror < 0.5,
      "worst %.4f cm" % worst_mirror)

# --- leave the scene as a clean, correct rig --------------------------------
print()
if virgin:
    fkcontrols.bake_fk(SCENE)
    builder.bake_limbs(SCENE, builder.built_limbs())
    # A bake walks the timeline. Come back to the rest frame BEFORE cutting
    # the keys, or every bone freezes at whatever pose the last baked frame
    # left it in -- and the rebuild below then bakes that as the build pose.
    cmds.currentTime(frame, edit=True)
    cmds.cutKey(BONES, clear=True)
    cmds.currentTime(frame, edit=True)
    # World matrices, not channel values: a bone can come back off a bake
    # reading 23 where it read -337, which is the same rotation written the
    # other way round and not a skeleton that moved.
    back = max(max(abs(a - b) for a, b in
                   zip(want, cmds.xform(bone, query=True, worldSpace=True,
                                        matrix=True)))
               for bone, want in REST.items())
    check("cleanup: skeleton back on its rest pose", back < 1e-4,
          "worst %.3e" % back)
    print("test animation removed;", fkcontrols.rebuild(SCENE, fk_limbs=False))
cmds.currentTime(frame, edit=True)
cmds.autoKeyframe(state=auto_key)
if selection:
    cmds.select(selection, replace=True)
else:
    cmds.select(clear=True)

print()
print("VERIFY DONE - %s" % ("ALL GREEN" if not failures
                            else "FAILED: " + ", ".join(failures)))

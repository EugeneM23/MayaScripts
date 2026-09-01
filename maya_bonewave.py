"""Sine-wave animation over a group of joints.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose): select joints - or one root joint, then the joints
under it are taken - set amplitude, period and wavelength, press Apply
Wave. Every joint gets per-frame keys on one translate channel across the
playback range: a sine wave travelling through the group, each joint's
phase taken from its position along the travel axis, so the wave rolls
across the bone cloud instead of rocking it in unison. The channel's rest
value is stored on the joint (geoWaveRest<axis>) the first time the wave
touches it, so re-applying with new settings never drifts, and Remove Wave
puts the exact rest back and drops the marker. A channel animated by
something that is not our wave is skipped and named in the status line.

Symmetry modes, the centre being the bounding-box centre of the joints
being waved (the object's central axis, wherever the object stands):
Off is the plain one-way wave; Mirror (2 waves) sends two waves apart
from the central plane, phase from the unsigned distance along the travel
axis; Radial (4 waves) sends a ring wave out from the central axis in the
plane perpendicular to the move axis - along +X, -X, +Z, -Z and every
direction between, like a drop on water (the travel axis is unused there).

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_bonewave; maya_bonewave.show()
"""

import math

import maya.cmds as cmds

WINDOW = "boneWaveWindow"
REST_ATTR = "geoWaveRest"
AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}
SYMMETRY_MODES = {"Off": "off",
                  "Mirror (2 waves)": "mirror",
                  "Radial (4 waves)": "radial"}

_amp = None
_period = None
_length = None
_move_axis = None
_travel_axis = None
_symmetry = None
_status = None


# ---------------------------------------------------------------- pure logic

def wave_value(frame, start, period, dist, wavelength, amplitude):
    """The wave at one frame for a joint sitting dist along the travel
    axis: one full cycle every period frames, the crest travelling one
    wavelength per cycle; wavelength 0 keeps the whole group in phase."""
    phase = (frame - start) / float(period)
    if wavelength > 0.0:
        phase -= dist / float(wavelength)
    return amplitude * math.sin(2.0 * math.pi * phase)


def bbox_center(positions):
    """Centre of the bounding box of the given (x, y, z) positions."""
    lo = [min(p[i] for p in positions) for i in range(3)]
    hi = [max(p[i] for p in positions) for i in range(3)]
    return [(lo[i] + hi[i]) * 0.5 for i in range(3)]


def phase_distance(position, mode, travel_index, move_index, center):
    """The distance that decides a joint's phase. Off: signed position
    along the travel axis (the plain travelling wave). Mirror: unsigned
    distance from the central plane, so two waves spread apart. Radial:
    distance from the central axis in the plane perpendicular to the move
    axis, so a ring spreads out in every direction."""
    if mode == "mirror":
        return abs(position[travel_index] - center[travel_index])
    if mode == "radial":
        a, b = [i for i in (0, 1, 2) if i != move_index]
        da = position[a] - center[a]
        db = position[b] - center[b]
        return math.sqrt(da * da + db * db)
    return position[travel_index]


# ---------------------------------------------------------------- scene side

def target_joints():
    """Selected joints; a single selected joint with joint children means
    the group under it (the geobones root gesture)."""
    sel = cmds.ls(selection=True, type="joint", long=True) or []
    if len(sel) == 1:
        kids = cmds.listRelatives(sel[0], allDescendents=True,
                                  type="joint", fullPath=True) or []
        if kids:
            return kids
    return sel


def _rest_attr(joint, axis):
    return joint + "." + REST_ATTR + axis


def apply_wave(joints, move_axis, travel_axis, amplitude, period,
               wavelength, start, end, mode="off"):
    """Per-frame keys on translate<move_axis> for every joint; returns
    (keyed joints, skipped joint names)."""
    channel = "translate" + move_axis
    todo = []
    skipped = []
    for joint in joints:
        plug = joint + "." + channel
        has_curve = bool(cmds.listConnections(plug, source=True,
                                              destination=False,
                                              type="animCurve"))
        if has_curve and not cmds.objExists(_rest_attr(joint, move_axis)):
            skipped.append(joint.split("|")[-1])
            continue
        todo.append(joint)

    # First pass: everything back to rest, so the second pass reads clean
    # positions even when a waved parent carries waved children.
    for joint in todo:
        plug = joint + "." + channel
        rest_attr = _rest_attr(joint, move_axis)
        if cmds.objExists(rest_attr):
            rest = cmds.getAttr(rest_attr)
        else:
            rest = cmds.getAttr(plug)
            cmds.addAttr(joint, longName=REST_ATTR + move_axis,
                         attributeType="double")
            cmds.setAttr(rest_attr, rest)
        cmds.cutKey(joint, attribute=channel, clear=True)
        cmds.setAttr(plug, rest)

    travel_index = AXIS_INDEX[travel_axis]
    move_index = AXIS_INDEX[move_axis]
    positions = {}
    for joint in todo:
        positions[joint] = cmds.xform(joint, query=True, worldSpace=True,
                                      translation=True)
    center = (bbox_center(list(positions.values())) if todo
              else [0.0, 0.0, 0.0])
    for joint in todo:
        rest = cmds.getAttr(_rest_attr(joint, move_axis))
        dist = phase_distance(positions[joint], mode, travel_index,
                              move_index, center)
        for frame in range(start, end + 1):
            cmds.setKeyframe(joint, attribute=channel, time=frame,
                             value=rest + wave_value(frame, start, period,
                                                     dist, wavelength,
                                                     amplitude))
    return todo, skipped


def remove_wave(joints):
    """Cut our keys, put the stored rest back, drop the markers; returns
    how many joints were cleaned."""
    cleaned = 0
    for joint in joints:
        touched = False
        for axis in ("X", "Y", "Z"):
            rest_attr = _rest_attr(joint, axis)
            if not cmds.objExists(rest_attr):
                continue
            channel = "translate" + axis
            cmds.cutKey(joint, attribute=channel, clear=True)
            cmds.setAttr(joint + "." + channel, cmds.getAttr(rest_attr))
            cmds.deleteAttr(joint, attribute=REST_ATTR + axis)
            touched = True
        if touched:
            cleaned += 1
    return cleaned


# ------------------------------------------------------------------- window

def _say(message):
    if _status and cmds.text(_status, exists=True):
        cmds.text(_status, edit=True, label=message)
    print("bonewave: " + message)


def _frame_range():
    start = int(math.floor(cmds.playbackOptions(query=True, min=True)))
    end = int(math.ceil(cmds.playbackOptions(query=True, max=True)))
    return start, end


def _apply_pressed(*_):
    try:
        amplitude = cmds.floatFieldGrp(_amp, query=True, value1=True)
        period = cmds.floatFieldGrp(_period, query=True, value1=True)
        wavelength = cmds.floatFieldGrp(_length, query=True, value1=True)
        move_axis = cmds.optionMenu(_move_axis, query=True, value=True)
        travel_axis = cmds.optionMenu(_travel_axis, query=True, value=True)
        mode = SYMMETRY_MODES.get(cmds.optionMenu(_symmetry, query=True,
                                                  value=True), "off")
        joints = target_joints()
        if not joints:
            _say("Select joints first.")
            return
        if period <= 0:
            _say("Period must be positive.")
            return
        if amplitude == 0:
            _say("Amplitude is zero - nothing to animate.")
            return
        start, end = _frame_range()
        cmds.undoInfo(openChunk=True)
        try:
            keyed, skipped = apply_wave(joints, move_axis, travel_axis,
                                        amplitude, period, wavelength,
                                        start, end, mode)
        finally:
            cmds.undoInfo(closeChunk=True)
        message = ("Wave on %d joint(s)%s, frames %d..%d."
                   % (len(keyed),
                      "" if mode == "off" else " (%s)" % mode,
                      start, end))
        if skipped:
            names = ", ".join(skipped[:4])
            if len(skipped) > 4:
                names += " +%d more" % (len(skipped) - 4)
            message += " Skipped (own animation): %s." % names
        _say(message)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def _remove_pressed(*_):
    try:
        joints = target_joints()
        if not joints:
            _say("Select joints first.")
            return
        cmds.undoInfo(openChunk=True)
        try:
            cleaned = remove_wave(joints)
        finally:
            cmds.undoInfo(closeChunk=True)
        if cleaned:
            _say("Wave removed from %d joint(s)." % cleaned)
        else:
            _say("No wave on the selection.")
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _amp, _period, _length, _move_axis, _travel_axis, _symmetry, \
        _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Bone Wave", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select joints (or their root), press Apply Wave.",
              align="left")
    _amp = cmds.floatFieldGrp(
        label="Amplitude", value1=10.0, precision=3,
        annotation="How far each joint travels from its rest position.")
    _period = cmds.floatFieldGrp(
        label="Period (frames)", value1=30.0, precision=1,
        annotation="Frames per full cycle - the rhythm of the wave.")
    _length = cmds.floatFieldGrp(
        label="Wavelength", value1=50.0, precision=1,
        annotation="Distance between two crests along the travel axis; "
                   "0 moves the whole group in phase.")
    _move_axis = cmds.optionMenu(label="Move axis")
    for axis in ("Y", "X", "Z"):
        cmds.menuItem(label=axis)
    _travel_axis = cmds.optionMenu(label="Travel axis")
    for axis in ("X", "Y", "Z"):
        cmds.menuItem(label=axis)
    _symmetry = cmds.optionMenu(
        label="Symmetry",
        annotation="Mirror: two waves apart from the object's central "
                   "plane. Radial: a ring wave out from its central axis "
                   "(travel axis unused).")
    for label in ("Off", "Mirror (2 waves)", "Radial (4 waves)"):
        cmds.menuItem(label=label)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 0)])
    cmds.button(label="Apply Wave", height=34, command=_apply_pressed)
    cmds.button(label="Remove Wave", height=34, width=110,
                command=_remove_pressed)
    cmds.setParent("..")
    cmds.text(label="Keys land on every frame of the playback range.",
              align="left", enable=False)
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)

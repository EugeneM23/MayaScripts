"""Override mode (2026-11-02): the chest carries the weapon, late.

The animator: «Override mode. Галочка в той же вкладке. В этом режиме оружие
привязывается к груди (spine_03; в 1P-режиме рига грудь - это контрол-кнот
Chest_1P_ctrl) и даются три настройки: сила наследования вращения, сила
наследования смещения по позиции и отставание в миллисекундах - так получается
захлёст оружия». Asked how the result is written: «Ключи, настройки помним» - the
Aim Mode road, with the three numbers kept on the weapon so a knob turned
re-writes, as a Walk Builder parameter does.

## The formula

For every frame `f`, with `C` the chest's world matrix, `W_own` the weapon's world
track BEFORE the mode (its base) and `ref` the span's first frame:

    W(f) = W_own(f) · C(f)⁻¹ · C(ref) · G(f)

`G(f)` is the chest's motion from `ref` to `f − lag`, its turn slerped from identity
by `rotation` and its travel scaled by `position`, both about the chest's own pivot.
So the weapon keeps its own pose RELATIVE TO THE CHEST and the chest's own motion is
put back scaled and late:

- `1 / 1 / 0` is the identity - the mode changes nothing (the repository's rule: the
  defaults are the source);
- a lag at full strength is `W_own(f) · C(f)⁻¹ · C(f − lag)`: the weapon takes the
  chest's pose from earlier, which is the overlap that was asked for;
- `rotation 0` and the weapon does not inherit the body's turn at all; `position 0`
  and it does not inherit its travel.

The chest's time is clamped to the first frame, so that frame is bit-exact and the
lag eases in over the first `lag` frames.

## What it writes, and what it keeps

Keys on the weapon's own translate / rotate, on its keys ∪ the chest's keys, plus the
frames between them where the result stands off (`aimcore`'s fill loop). Its ORIGINAL
curves are parked on the weapon the way a floor drop parks a bone's track
(`bonedrive.park`): a re-write reads them and Default puts them back, exactly.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_timewarp
from maya_scenesetup import aimcore
from maya_scenesetup import fkik

MARKER = "skeldarWeaponOverride"      # on the weapon: "rotation position lag"
BASE_PREFIX = "skeldarOverrideBase"   # + Channel: the weapon's own curve, parked
CHANNELS = fkik.TRANSLATE + fkik.ROTATE
CHEST = "spine_03"

Settings = namedtuple("Settings", "rotation position lag")
DEFAULTS = Settings(1.0, 1.0, 80.0)
IDENTITY = Settings(1.0, 1.0, 0.0)
QUIET = 1e-9

NO_WEAPON = "no weapon in the scene - Inventory > Equip first"
NO_CHEST = "%s: the rig has no %s bone - Override needs the chest"
AIMED = "%s is in Aim Mode - it writes the rotation too: Default first"
NOT_OVERRIDDEN = "%s is not in Override mode"
IDENTITY_NOTE = "the identity, nothing changed - dial the Lag or drop a strength"
HELD_NOTE = ("in the %s hand: it slides in the grip by the lag - Weapon -> World "
             "with 2H keeps the hands on it")


# ------------------------------------------------------------------- pure

def parse(text):
    """`Settings` from the string kept on the weapon, or None (nothing there, or no
    three numbers). Pure."""
    parts = str(text or "").split()
    if len(parts) != 3:
        return None
    try:
        return Settings(*[float(v) for v in parts])
    except ValueError:
        return None


def unparse(settings):
    """The three numbers as one string, `weaponaim.VECTORS`' way (JSON-free). Pure."""
    return " ".join("%.12g" % float(v) for v in settings)


def is_identity(settings):
    """Full strength and no lag: the mode changes nothing. Pure."""
    return (abs(settings.rotation - 1.0) < QUIET and abs(settings.position - 1.0) < QUIET
            and abs(settings.lag) < QUIET)


def lag_frames(ms, fps):
    """Milliseconds as frames of the scene's own rate. Pure."""
    return float(ms) * float(fps) / 1000.0


def _translate(v):
    return om.MMatrix([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, v[0], v[1], v[2], 1])


def rigid(matrix):
    """`matrix` without its scale or shear - its turn and its place. The chest's scale
    is never inherited: a rig's scale chain leaves 4e-7 on a bone, and a partial scale
    means nothing. Pure (OpenMaya)."""
    m = om.MMatrix(matrix)
    turn = om.MTransformationMatrix(m).rotation(asQuaternion=True)
    return om.MMatrix(list(om.MMatrix(turn.asMatrix()))[0:12] +
                      [m[12], m[13], m[14], 1.0])


def scaled(ref, late, rotation, position):
    """`G`: the chest's motion from `ref` to `late` (world matrices), its turn slerped
    from identity by `rotation` and its travel scaled by `position`, both about the
    CHEST's own pivot - the translation of a bare `ref⁻¹ · late` carries the lever to
    the world origin, and scaling that would throw the weapon off the body.

    Row vectors: a world point p maps to p · G. At full strength it IS `ref⁻¹ · late`,
    exactly (measured: 0.0), so the identity costs nothing. Pure (OpenMaya)."""
    ref, late = om.MMatrix(ref), om.MMatrix(late)
    if rotation == 1.0 and position == 1.0:
        return ref.inverse() * late
    turn = om.MQuaternion.slerp(
        om.MQuaternion(),
        om.MTransformationMatrix(ref).rotation(asQuaternion=True).inverse() *
        om.MTransformationMatrix(late).rotation(asQuaternion=True), float(rotation))
    pivot = [ref[12], ref[13], ref[14]]
    travel = [(late[12 + i] - pivot[i]) * float(position) for i in range(3)]
    return (_translate([-v for v in pivot]) * om.MMatrix(turn.asMatrix()) *
            _translate([pivot[i] + travel[i] for i in range(3)]))


def result(own, chest_now, chest_ref, g):
    """The weapon's world under the mode: `W = W_own · C(f)⁻¹ · C(ref) · G` - its own
    pose relative to the chest kept, the chest's own motion put back scaled and late.
    Pure (OpenMaya)."""
    return (om.MMatrix(own) * om.MMatrix(chest_now).inverse() *
            om.MMatrix(chest_ref) * om.MMatrix(g))


def sampled(mats, t):
    """The world matrix at the fractional frame `t` from `mats` ({frame: matrix}): its
    turn slerped and its place lerped between the two whole frames around it, clamped
    to the frames it holds. Pure (OpenMaya)."""
    frames = sorted(mats)
    if not frames:
        return om.MMatrix()
    if t <= frames[0]:
        return om.MMatrix(mats[frames[0]])
    if t >= frames[-1]:
        return om.MMatrix(mats[frames[-1]])
    low = max(f for f in frames if f <= t)
    high = min(f for f in frames if f >= t)
    if high == low:
        return om.MMatrix(mats[low])
    share = (t - low) / float(high - low)
    a, b = om.MMatrix(mats[low]), om.MMatrix(mats[high])
    turn = om.MQuaternion.slerp(om.MTransformationMatrix(a).rotation(asQuaternion=True),
                                om.MTransformationMatrix(b).rotation(asQuaternion=True),
                                share)
    place = [a[12 + i] + (b[12 + i] - a[12 + i]) * share for i in range(3)]
    return om.MMatrix(list(om.MMatrix(turn.asMatrix()))[0:12] + place + [1.0])


def pick_value(on, settings):
    """A pick's value: what the press would make stand. Pure."""
    return (bool(on),) + tuple(float(v) for v in settings)


def state_value(standing, card):
    """What the scene shows: the settings standing, else off with the CARD's own
    numbers - so a knob turned with the mode off is no pick, and one turned with it on
    is. Pure."""
    return pick_value(True, standing) if standing else pick_value(False, card)


def entered_message(label, keys, settings, carrier, held):
    """What the status says after a press. Pure."""
    head = "%s on %s: %g / %g / %g ms" % (label, carrier, settings.rotation,
                                          settings.position, settings.lag)
    notes = ["%d key%s" % (len(keys), "" if len(keys) == 1 else "s") if keys else
             "no keys of its own: set at the current frame"]
    if is_identity(settings):
        notes.append(IDENTITY_NOTE)
    elif held:
        #  only where the numbers actually move the weapon: at the identity nothing
        #  slides, and the note would be a lie about the press just made
        notes.append(HELD_NOTE % ("right" if held == "R" else "left"))
    return "%s (%s)" % (head, ", ".join(notes))


def left_message(label):
    """Pure."""
    return "%s back to Default - its own animation restored" % label


# ------------------------------------------------------------------ the base

def base_attr(channel):
    """The weapon's attribute holding `channel`'s own curve. Pure."""
    return BASE_PREFIX + channel[0].upper() + channel[1:]


def state(weapon):
    """The settings standing on `weapon`, or None."""
    if not weapon or not cmds.objExists(weapon) or not cmds.attributeQuery(
            MARKER, node=weapon, exists=True):
        return None
    return parse(cmds.getAttr(weapon + "." + MARKER))


def is_overridden(weapon):
    return state(weapon) is not None


def park(weapon):
    """The weapon's own curves off it and onto our attributes - the base a re-write
    reads and Default puts back; a channel with no curve keeps its value. What was
    parked before goes first, its curves deleted with it (a re-write parks the base it
    has just reconnected, never the override's own result)."""
    drop(weapon)
    for channel in CHANNELS:
        attr = base_attr(channel)
        kind = "doubleLinear" if channel.startswith("translate") else "doubleAngle"
        cmds.addAttr(weapon, longName=attr, attributeType=kind, keyable=False)
        plug = weapon + "." + channel
        curves = cmds.listConnections(plug, source=True, destination=False,
                                      type="animCurve", plugs=True) or []
        if curves:
            cmds.connectAttr(curves[0], weapon + "." + attr)
            cmds.disconnectAttr(curves[0], plug)
        else:
            cmds.setAttr(weapon + "." + attr, cmds.getAttr(plug))


def unpark(weapon):
    """The base back on the weapon, exactly: the override's own curve cut first (an
    emptied curve node goes with it - trap 210), then the parked curve reconnected or
    the plain value written. False when nothing was parked."""
    if not cmds.attributeQuery(base_attr(CHANNELS[0]), node=weapon, exists=True):
        return False
    for channel in CHANNELS:
        attr = weapon + "." + base_attr(channel)
        if not cmds.objExists(attr):
            continue
        plug = weapon + "." + channel
        cmds.cutKey(plug, clear=True)
        curves = cmds.listConnections(attr, source=True, destination=False,
                                      plugs=True) or []
        if curves:
            cmds.connectAttr(curves[0], plug, force=True)
            cmds.disconnectAttr(curves[0], attr)
        else:
            try:
                cmds.setAttr(plug, cmds.getAttr(attr))
            except RuntimeError:
                pass
    drop(weapon)
    return True


def drop(weapon):
    """Our attributes off `weapon`, the curves still parked on them deleted."""
    for channel in CHANNELS:
        attr = weapon + "." + base_attr(channel)
        if cmds.objExists(attr):
            for curve in cmds.listConnections(attr, source=True,
                                              destination=False) or []:
                if cmds.objExists(curve):
                    cmds.delete(curve)
            cmds.deleteAttr(attr)
    if cmds.attributeQuery(MARKER, node=weapon, exists=True):
        cmds.deleteAttr(weapon + "." + MARKER)


# ----------------------------------------------------------------- the chest

def chest_of(rig):
    """The rig's chest bone (`spine_03`), long path, or None.

    In 1P the chest control (`Chest_1P_ctrl`) drives that bone through Tools' knot, so
    reading the bone reads the control's motion - one road for both modes, and it works
    beside a bare skeleton too. With the upper animation layer muted (1P Setup's own
    state) the bone IS the stabilized chest, which is what a weapon should inherit."""
    from maya_scenesetup import skeleton
    root = getattr(rig, "skeleton_root", None) if rig is not None else None
    return skeleton.resolve_bone(root, CHEST) if root else None


def refusal(weapon, chest):
    """'' or why `weapon` cannot go into Override mode. Nothing here changes anything."""
    from maya_scenesetup import weaponaim
    if not weapon or not cmds.objExists(weapon):
        return NO_WEAPON
    label = aimcore.leaf(weapon)
    if weaponaim.is_aimed(weapon):
        return AIMED % label
    if not chest:
        return NO_CHEST % (label, CHEST)
    #  the aim's own rule (`aimcore.rotate_refusal`) over both channel sets: this mode
    #  writes the translate too
    for channel in CHANNELS:
        plug = weapon + "." + channel
        if cmds.getAttr(plug, lock=True):
            return "%s.%s is locked" % (label, channel)
        if fkik._layered(plug):
            return "%s.%s is on animation layers - bake its layers first" % (label, channel)
        driver = fkik._foreign(plug)
        if driver:
            return "%s.%s is driven by %s" % (label, channel, driver)
    return ""


def _held(weapon):
    """The side of the hand holding `weapon`, or None."""
    try:
        from maya_scenesetup import weaponspace
        hand = weaponspace.holding_hand(weapon)
    except Exception:                                        # noqa: BLE001 - no rig
        return None
    if not hand:
        return None
    leaf = aimcore.leaf(hand)
    return "R" if leaf.endswith("_r") else ("L" if leaf.endswith("_l") else None)


# ---------------------------------------------------------------- the engine

def _fps():
    from maya_poselib import look
    return look.fps_of(cmds.currentUnit(query=True, time=True))


def _curves(weapon, chest):
    """Every time curve that can move the weapon or the chest. A rig's chest bone is
    driven by constraints and holds no curve of its own, so the weapon's own keys alone
    would key nothing at all on a weapon seated in a hand - `driving_curves` is what
    reads the body's keys through the rig."""
    return set(fkik.own_curves([weapon], [])) | set(fkik.driving_curves([chest]))


def span_for(weapon, chest, curves=None):
    """(start, end, False): the playback range and every key that moves the weapon or
    the chest, whole frames."""
    start = cmds.playbackOptions(query=True, min=True)
    end = cmds.playbackOptions(query=True, max=True)
    times = []
    for curve in (_curves(weapon, chest) if curves is None else curves):
        times.extend(cmds.keyframe(curve, query=True, timeChange=True) or [])
    if times:
        start, end = min(start, min(times)), max(end, max(times))
    return (int(math.floor(start)), int(math.ceil(end)), False)


def frames_for(window, curves):
    """(frames to key, the keys, their tangents) - `fkik.own_keys`' own two halves over
    a wider curve set, so the keys are the weapon's and those of whatever moves the
    chest, with the tangents of the source keys. No key at all: one plain value at the
    current frame."""
    mine = [fkik._keys_of(c) for c in curves]
    keys = fkik.key_frames([t for curve in mine for t, _i, _o in curve], window)
    tangents = dict((f, fkik.tangents_at(mine, mine, f)) for f in keys)
    return (keys or [cmds.currentTime(query=True)]), keys, tangents


def _read(weapon, chest, frames):
    """{frame: (the weapon's world, the chest's rigid world, the weapon's parent
    inverse)} over `frames` - ONE walk, the time put back. Read with the base still
    connected: this is the weapon's own track."""
    out = {}
    with maya_timewarp.unwarped():
        fkik._suspend(True)
        now = cmds.currentTime(query=True)
        try:
            for frame in frames:
                fkik._goto(frame)
                out[frame] = (aimcore.world(weapon), rigid(aimcore.world(chest)),
                              om.MMatrix(cmds.getAttr(weapon + ".parentInverseMatrix[0]")))
        finally:
            fkik._goto(now)
            fkik._suspend(False)
    return out


def wanted(read, settings, fps):
    """{frame: the weapon's world under the mode} over every frame `read` holds.

    The chest's time is clamped to the first frame, so that frame is bit-exact and the
    lag eases in over the first `lag` frames: a body moving before the span is not read
    there, and the weapon starts where it started."""
    frames = sorted(read)
    chests = dict((f, read[f][1]) for f in frames)
    ref = chests[frames[0]]
    lag = lag_frames(settings.lag, fps)
    out = {}
    for frame in frames:
        late = sampled(chests, max(frames[0], frame - lag))
        out[frame] = result(read[frame][0], chests[frame], ref,
                            scaled(ref, late, settings.rotation, settings.position))
    return out


def channels_of(weapon, read, want, frames):
    """{frame: (tx, ty, tz, rx, ry, rz)} for the wanted worlds: each frame's local
    matrix turned into the weapon's own channels by the Pose Library's own writer
    (`helpers.driver_channels` keeps the rotate order, the rotate axis, the pivots, the
    shear and the scale), one Euler path through the frames in time order so no
    neighbour is a turn apart."""
    from maya_poselib import helpers
    attrs = helpers._attrs(weapon)
    previous = [cmds.getAttr(weapon + "." + ch) for ch in fkik.ROTATE]
    out = {}
    for frame in frames:
        rotate, translate = helpers.driver_channels(
            om.MMatrix(want[frame]) * read[frame][2], attrs, previous)
        out[frame] = tuple(translate) + tuple(rotate)
        previous = list(rotate)
    return out


def _fill(weapon, want, values, keyed, frames):
    """Keys added on the frames between the keys where the weapon stands off `want`
    (`aimcore.track_off`: 0.1 deg or 0.01 cm), until none does - Default's own loop.
    The values are the first walk's, never read again with `getAttr(time=)`, which does
    not pull a constraint chain (trap 69). How many."""
    def missed(todo):
        return aimcore.track_off(want, aimcore.walk(todo, lambda: aimcore.world(weapon)))

    def key(frame):
        for value, channel in zip(values[frame], CHANNELS):
            cmds.setKeyframe(weapon, attribute=channel, time=frame, value=value)

    with maya_timewarp.unwarped():
        fkik._suspend(True)
        try:
            return aimcore.fill_passes([f for f in frames if f not in keyed], missed, key)
        finally:
            fkik._suspend(False)


def enter(weapon, chest, settings):
    """Override mode on `weapon` (the caller holds the undo chunk and autoKey): its own
    track read, parked, and its channels keyed to what the chest carries. Pressed with
    the mode standing, the base is reconnected FIRST, so a knob turned re-reads the
    weapon's original animation and never its own result. The status line."""
    weapon = aimcore.long_(weapon)
    label = aimcore.leaf(weapon)
    key = aimcore.uuid(weapon)
    unpark(weapon)                       # a re-write: the base back before it is read
    curves = _curves(weapon, chest)
    window = span_for(weapon, chest, curves)
    frames = list(range(window[0], window[1] + 1))
    read = _read(weapon, chest, frames)
    want = wanted(read, settings, _fps())
    values = channels_of(weapon, read, want, frames)
    sample, keys, tangents = frames_for(window, curves)
    sample = [f for f in sample if f in values] or [frames[0]]
    weapon = aimcore.long_(key)
    park(weapon)
    cmds.addAttr(weapon, longName=MARKER, dataType="string")
    cmds.setAttr(weapon + "." + MARKER, unparse(settings), type="string")
    for index, channel in enumerate(CHANNELS):
        fkik._write(weapon + "." + channel, sample,
                    [values[f][index] for f in sample], window, False, tangents)
    added = _fill(weapon, want, values, set(sample), frames) if keys else 0
    line = entered_message(label, keys, settings, aimcore.leaf(chest), _held(weapon))
    return line + (" + %d frame(s) between the keys" % added if added else "")


def leave(weapon):
    """Default on `weapon` (the caller holds the chunk): its own animation back,
    exactly. The status line."""
    weapon = aimcore.long_(weapon)
    if not weapon:
        return NO_WEAPON
    label = aimcore.leaf(weapon)
    if state(weapon) is None:
        return NOT_OVERRIDDEN % label
    if not unpark(weapon):
        drop(weapon)
    return left_message(label)

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
    if held:
        notes.append(HELD_NOTE % ("right" if held == "R" else "left"))
    return "%s (%s)" % (head, ", ".join(notes))


def left_message(label):
    """Pure."""
    return "%s back to Default - its own animation restored" % label

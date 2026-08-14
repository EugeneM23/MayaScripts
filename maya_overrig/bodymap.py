"""Static body map for the OverRig picker.

Pure data. Imports nothing outside the stdlib -- no Qt, no maya.cmds -- so the
layout can be tested in plain Python.

Coordinates live in a fixed body-space of CANVAS_W x CANVAS_H units which the
view scales to fit, so nothing here depends on window size.

Orientation is a FRONT view of the character in a T-pose: the character's left
side (the `_l` joints) is drawn on the viewer's RIGHT, and the arms run
horizontally outward from the shoulders. Vertical arms were tried first and
read badly -- they leave the figure narrow, strand the hands, and push the
finger blocks far from the arm they belong to.
"""

from collections import namedtuple

Button = namedtuple("Button", "id joint x y w h region")

CANVAS_W = 560
CANVAS_H = 410

REGIONS = ("root", "spine", "head",
           "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r")

GROUPS = ("all", "main") + REGIONS

# Fingers carrying a metacarpal joint, ordered top to bottom below the thumb.
_FINGERS = ("index", "middle", "ring", "pinky")

# One row per finger, one column per joint, running outward from the hand.
_FINGER_W = 22
_FINGER_H = 16
_FINGER_STEP_X = 24
_FINGER_STEP_Y = 19
_FINGER_X0 = 462
_FINGER_Y0 = 86
_THUMB_Y = 66


def _centre_buttons():
    """Root, pelvis, spine stack, neck and head -- all on the midline."""
    rows = [
        ("head", 260, 18, 40, 34, "head"),
        ("neck_02", 269, 56, 22, 12, "head"),
        ("neck_01", 269, 72, 22, 12, "head"),
        ("spine_05", 252, 88, 56, 15, "spine"),
        ("spine_04", 252, 107, 56, 15, "spine"),
        ("spine_03", 252, 126, 56, 15, "spine"),
        ("spine_02", 252, 145, 56, 15, "spine"),
        ("spine_01", 252, 164, 56, 15, "spine"),
        ("pelvis", 247, 183, 66, 20, "root"),
        # Wider than the pelvis on purpose: root is the world control, and a
        # plinth shape keeps it from reading as one more spine segment.
        ("root", 238, 207, 84, 14, "root"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_limb_buttons():
    """Character-left arm and leg, drawn on the viewer's right.

    The arm is a horizontal chain running outward from the shoulder; the leg
    hangs vertically from the pelvis.
    """
    rows = [
        ("clavicle_l", 312, 86, 26, 18, "arm_l"),
        ("upperarm_l", 342, 86, 42, 18, "arm_l"),
        ("lowerarm_l", 388, 86, 40, 18, "arm_l"),
        ("hand_l", 432, 86, 26, 18, "arm_l"),
        ("thigh_l", 286, 226, 26, 56, "leg_l"),
        ("calf_l", 286, 286, 24, 54, "leg_l"),
        ("foot_l", 286, 344, 22, 22, "leg_l"),
        ("ball_l", 286, 370, 22, 14, "leg_l"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_finger_buttons():
    """Character-left hand: a row per finger, a column per joint.

    The thumb sits on its own row above the others and has no metacarpal.
    """
    out = []
    for row, finger in enumerate(_FINGERS):
        y = _FINGER_Y0 + row * _FINGER_STEP_Y
        joints = ["{0}_metacarpal_l".format(finger)]
        joints += ["{0}_{1:02d}_l".format(finger, i) for i in (1, 2, 3)]
        for col, joint in enumerate(joints):
            x = _FINGER_X0 + col * _FINGER_STEP_X
            out.append(Button(joint, joint, x, y, _FINGER_W, _FINGER_H, "hand_l"))

    for col, i in enumerate((1, 2, 3)):
        joint = "thumb_{0:02d}_l".format(i)
        x = _FINGER_X0 + col * _FINGER_STEP_X
        out.append(Button(joint, joint, x, _THUMB_Y, _FINGER_W, _FINGER_H, "hand_l"))

    return out


def _mirrored(buttons):
    """Mirror character-left buttons into their character-right twins.

    Every input button's id, joint and region must end in `_l`.
    """
    out = []
    for b in buttons:
        out.append(Button(
            b.id[:-2] + "_r",
            b.joint[:-2] + "_r",
            CANVAS_W - b.x - b.w,
            b.y, b.w, b.h,
            b.region[:-2] + "_r",
        ))
    return out


def _build():
    left = _left_limb_buttons() + _left_finger_buttons()
    return tuple(_centre_buttons() + left + _mirrored(left))


BUTTONS = _build()

_BY_ID = {b.id: b for b in BUTTONS}


def button_by_id(bid):
    """Return the Button with this id. Raises KeyError if unknown."""
    return _BY_ID[bid]


def group_members(group):
    """Return the button ids belonging to a group.

    `all` is every button; `main` is everything except fingers; any other name
    must be a region. Raises KeyError for unknown groups.
    """
    if group not in GROUPS:
        raise KeyError(group)
    if group == "all":
        return tuple(b.id for b in BUTTONS)
    if group == "main":
        return tuple(b.id for b in BUTTONS
                     if b.region not in ("hand_l", "hand_r"))
    return tuple(b.id for b in BUTTONS if b.region == group)

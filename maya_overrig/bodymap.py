"""Static body map for the OverRig picker.

Pure data. Imports nothing outside the stdlib -- no Qt, no maya.cmds -- so the
layout can be tested in plain Python.

Coordinates live in a fixed body-space of CANVAS_W x CANVAS_H units which the
view scales to fit, so nothing here depends on window size.

Orientation is a FRONT view of the character: the character's left side (the
`_l` joints) is drawn on the viewer's RIGHT.
"""

from collections import namedtuple

Button = namedtuple("Button", "id joint x y w h region")

CANVAS_W = 400
CANVAS_H = 620

REGIONS = ("root", "spine", "head",
           "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r")

GROUPS = ("all", "main") + REGIONS

# Fingers carrying a metacarpal joint, ordered inboard to outboard on the hand.
_FINGERS = ("index", "middle", "ring", "pinky")

_FINGER_W = 20
_FINGER_H = 17
_FINGER_STEP_X = 23
_FINGER_STEP_Y = 20
_FINGER_X0 = 296
_FINGER_Y0 = 286
_THUMB_X = 270


def _centre_buttons():
    """Root, pelvis, spine stack, neck and head -- all on the midline."""
    rows = [
        ("head", 178, 28, 44, 40, "head"),
        ("neck_02", 188, 72, 24, 14, "head"),
        ("neck_01", 188, 90, 24, 14, "head"),
        ("spine_05", 168, 110, 64, 17, "spine"),
        ("spine_04", 168, 131, 64, 17, "spine"),
        ("spine_03", 168, 152, 64, 17, "spine"),
        ("spine_02", 168, 173, 64, 17, "spine"),
        ("spine_01", 168, 194, 64, 17, "spine"),
        ("pelvis", 162, 215, 76, 24, "root"),
        ("root", 178, 560, 44, 20, "root"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_limb_buttons():
    """Character-left arm and leg, drawn on the viewer's right."""
    rows = [
        ("clavicle_l", 236, 110, 34, 16, "arm_l"),
        ("upperarm_l", 252, 130, 28, 58, "arm_l"),
        ("lowerarm_l", 256, 192, 26, 54, "arm_l"),
        ("hand_l", 258, 250, 24, 26, "arm_l"),
        ("thigh_l", 208, 250, 30, 72, "leg_l"),
        ("calf_l", 210, 326, 28, 70, "leg_l"),
        ("foot_l", 212, 400, 26, 28, "leg_l"),
        ("ball_l", 212, 432, 26, 16, "leg_l"),
    ]
    return [Button(n, n, x, y, w, h, r) for n, x, y, w, h, r in rows]


def _left_finger_buttons():
    """Character-left hand: four metacarpal fingers in columns, plus the thumb."""
    out = []
    for col, finger in enumerate(_FINGERS):
        x = _FINGER_X0 + col * _FINGER_STEP_X
        joints = ["{0}_metacarpal_l".format(finger)]
        joints += ["{0}_{1:02d}_l".format(finger, i) for i in (1, 2, 3)]
        for row, joint in enumerate(joints):
            y = _FINGER_Y0 + row * _FINGER_STEP_Y
            out.append(Button(joint, joint, x, y, _FINGER_W, _FINGER_H, "hand_l"))

    for row, i in enumerate((1, 2, 3)):
        joint = "thumb_{0:02d}_l".format(i)
        y = _FINGER_Y0 + (row + 1) * _FINGER_STEP_Y
        out.append(Button(joint, joint, _THUMB_X, y, _FINGER_W, _FINGER_H, "hand_l"))

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

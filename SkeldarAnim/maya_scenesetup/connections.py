"""Connections -- the hands on the weapon, and off it again.

The animator's ask (2026-09-18): «вкладка connections, в которой мы сможем
привязывать и отвязывать руки к оружию. Привязку и отвязку реализовать при
помощи OverRig, будем перепекать анимацию (важно, чтобы мы не ломали
иерархию нашего рига)».

The rig is the AdvancedSkeleton one (a namespace, `maya_rigs`), and its IK
hand controls `IKArm_R` / `IKArm_L` may NOT leave their place in the DAG:
`CustomOrientIKArm_R|IKExtraArm_R|IKArm_R` is what the arm's IK solver,
its follow switches and its FK/IK align read. So the two halves of a
connection are done two different ways, and the split is the whole design:

- **The WEAPON is re-baked by OverRig.** It hangs under the hand bone
  (Weapons > Add), and a node cannot both ride a hand and drive it, so
  Connect lifts it to world through `apply_Parent_out` -- its world track
  baked onto its own channels, drift measured 0.000000 -- and Disconnect
  hangs it back under the hand through `apply_Parent_in`, which re-bakes
  whatever the animator did with it out in the world into the hand's
  space rather than throwing it away. The weapon is geometry under a bone,
  not part of the rig, so re-parenting it breaks nothing.
- **The HANDS are constrained, never re-parented.** Each chosen IK control
  gets a `parentConstraint` to the weapon's geometry with `maintainOffset`
  captured on the CURRENT frame (the grip the animator is looking at), its
  own keys cut first (trap 37: keying a constrained channel splices a
  pairBlend) and its current values written back before the constraint is
  made (trap 58: `cutKey` leaves the channel wherever the DG last
  evaluated). Disconnect bakes the controls over the range through
  `cmds.bakeResults`, then deletes only OUR constraints -- found by the
  `skeldarHandLink` attribute they carry, never by name.

`FKIKArm_*.FKIKBlend` is put at 10 (IK) for a connected arm; a blend that
is KEYED at anything else is a refusal by name rather than a silent
override. The four poles are left alone (the elbow keeps answering to the
body, the ordinary prop workflow, and the earlier OverRig-rig Connect made
the same call).

What keeps the retarget honest: `maya_rig_retarget` refuses to retarget or
bake a rig whose hands are connected -- its `connect` would skip the
constrained IK controls as somebody else's and the take would arrive with
the hands standing still.

Spec: docs/superpowers/specs/2026-09-18-connections-design.md
"""

import traceback

import maya.cmds as cmds

import maya_rigs
from maya_overrig import overrig
from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import skeleton

HUB_SECTION = "connections"
STATUS = "skeldarConnectionsStatus"
HEADER = "skeldarConnectionsHeader"
_RIGHT = "skeldarConnectionsRight"
_LEFT = "skeldarConnectionsLeft"
_OPTIONVAR = "skeldarConnections_{0}"

MARKER = "skeldarHandLink"          # on our constraints: the weapon's UUID
WEAPON_BONE = "weapon_r"
SIDES = ("R", "L")
SIDE_LABEL = {"R": "right hand", "L": "left hand"}
IK_CONTROL = "IKArm_{0}"
BLEND_NODE = "FKIKArm_{0}"
BLEND_ATTR = "FKIKBlend"
IK_BLEND = 10.0
CHANNELS = ("translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ")

NO_WEAPON = "no weapon in the hand - Weapons > Add first"
NO_HANDS = "choose at least one hand"
NOTHING_CONNECTED = "nothing is connected"
RETARGETING = ("a retarget is standing on this rig (MoCapConstraints) - "
               "finish it first")


# ------------------------------------------------------------------- pure

def hands_to_connect(right, left):
    """The sides the two checkboxes name, in rig order. Pure."""
    return [side for side, on in (("R", right), ("L", left)) if on]


def blend_refusal(side, value, keyed):
    """Why a connect may not put this arm in IK, or None.

    A blend that is keyed at anything but IK is the animator's own
    switching; overriding it silently would change their take. Pure.
    """
    if keyed and abs(value - IK_BLEND) > 1e-6:
        return ("%s: %s.%s is keyed at %g - set it to %g (IK) or unkey it "
                "first" % (SIDE_LABEL[side], BLEND_NODE.format(side),
                           BLEND_ATTR, value, IK_BLEND))
    return None


def union_range(playback, keys):
    """(start, end) covering the playback range and the weapon's keys,
    snapped outward to whole frames. Pure."""
    start, end = float(playback[0]), float(playback[1])
    if keys:
        start = min(start, min(keys))
        end = max(end, max(keys))
    import math
    return float(math.floor(start)), float(math.ceil(end))


def connected_message(sides, frame, lifted):
    hands = ", ".join(SIDE_LABEL[s] for s in sides)
    text = "Connected: %s on the weapon (grip as at frame %g)" % (hands, frame)
    if lifted:
        text += "; weapon out to world, animation re-baked"
    return text


def disconnected_message(sides, span, returned):
    hands = ", ".join(SIDE_LABEL[s] for s in sides)
    text = "Disconnected: %s baked over %g..%g" % (hands, span[0], span[1])
    if returned:
        text += "; weapon back in the hand, animation re-baked"
    return text


def already_message(sides):
    return "already connected: %s - press Disconnect first" % ", ".join(
        SIDE_LABEL[s] for s in sides)


# ------------------------------------------------------------------ scene

def _rig(rig):
    if rig is not None:
        return rig, ""
    return maya_rigs.current_rig()


def _control(rig, side):
    paths = cmds.ls(maya_rigs.node(rig, IK_CONTROL.format(side)), long=True) or []
    return paths[0] if paths else None


def _blend_plug(rig, side):
    paths = cmds.ls(maya_rigs.node(rig, BLEND_NODE.format(side)), long=True) or []
    return (paths[0] + "." + BLEND_ATTR) if paths else None


def weapon_of(rig):
    """(hand bone, drive bone, weapon) for the rig, weapon None when bare.

    The weapon is what drives `weapon_r` (in the hand or, once connected,
    out in world), else what hangs under the hand.
    """
    root = rig.skeleton_root
    bone = skeleton.resolve_bone(root, WEAPON_BONE) if root else None
    if not bone:
        return None, None, None
    hand = attach.parent_bone(bone)
    weapon = bonedrive.driving_weapon(bone)
    if not weapon and hand:
        weapon = attach.find_attached(hand)
    return hand, bone, weapon


def our_constraints(control):
    """The constraints under `control` that we made (by attribute)."""
    out = []
    for node in cmds.listRelatives(control, children=True, type="constraint",
                                   fullPath=True) or []:
        if cmds.attributeQuery(MARKER, node=node, exists=True):
            out.append(node)
    return out


def connected_sides(rig):
    """The sides whose IK control rides a weapon through our constraint."""
    sides = []
    for side in SIDES:
        control = _control(rig, side)
        if control and our_constraints(control):
            sides.append(side)
    return sides


def is_connected(rig):
    return bool(connected_sides(rig))


def _in_hand(weapon, hand):
    parent = cmds.listRelatives(weapon, parent=True, fullPath=True) or []
    return bool(parent) and parent[0] == hand


def _values_now(control, now):
    """The control's channel values at `now`, read off the CURVES for keyed
    channels (trap 58: the DG may not have evaluated them)."""
    values = {}
    for channel in CHANNELS:
        plug = control + "." + channel
        curves = cmds.listConnections(plug, source=True, destination=False,
                                      type="animCurve") or []
        if curves:
            values[channel] = cmds.keyframe(curves[0], query=True, eval=True,
                                            time=(now, now))[0]
        else:
            values[channel] = cmds.getAttr(plug)
    return values


def _hang_hand(control, target, now, weapon_uuid):
    """Keys cut, current pose written back, the constraint made with the
    offset the animator is looking at, our mark on it."""
    values = _values_now(control, now)
    cmds.cutKey(control, attribute=list(CHANNELS), clear=True)
    for channel, value in values.items():
        cmds.setAttr(control + "." + channel, value)
    con = cmds.parentConstraint(target, control, maintainOffset=True)[0]
    con = cmds.ls(con, long=True)[0]
    cmds.addAttr(con, longName=MARKER, dataType="string")
    cmds.setAttr(con + "." + MARKER, weapon_uuid, type="string")
    return con


def connect(rig=None, sides=SIDES):
    """The chosen hands onto the weapon. Returns the status text."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    sides = [s for s in SIDES if s in sides]
    if not sides:
        return NO_HANDS
    hand, bone, weapon = weapon_of(rig)
    if not weapon:
        return NO_WEAPON
    already = connected_sides(rig)
    if already:
        return already_message(already)
    if cmds.objExists(maya_rigs.node(rig, "MoCapConstraints")):
        return RETARGETING
    for side in sides:
        if not _control(rig, side):
            return "%s: %s not found in %s" % (SIDE_LABEL[side],
                                               IK_CONTROL.format(side),
                                               maya_rigs.label(rig))
        plug = _blend_plug(rig, side)
        if plug:
            keyed = bool(cmds.listConnections(plug, source=True,
                                              destination=False))
            text = blend_refusal(side, cmds.getAttr(plug), keyed)
            if text:
                return text
    gate = overrig.mel_gate()
    if gate:
        return gate

    cmds.undoInfo(openChunk=True, chunkName="Connect hands to weapon")
    try:
        for side in sides:
            plug = _blend_plug(rig, side)
            if plug and not cmds.listConnections(plug, source=True,
                                                 destination=False):
                cmds.setAttr(plug, IK_BLEND)
        weapon = cmds.ls(weapon, long=True)[0]
        lifted = False
        if cmds.listRelatives(weapon, parent=True, fullPath=True):
            # parent_out re-parents, so the path goes stale (trap 16); the
            # UUID survives the move.
            uuid = cmds.ls(weapon, uuid=True)[0]
            overrig.parent_out(weapon)
            weapon = cmds.ls(uuid, long=True)[0]
            lifted = True
        target = attach.model_root(weapon)
        weapon_uuid = cmds.ls(weapon, uuid=True)[0]
        now = cmds.currentTime(query=True)
        for side in sides:
            _hang_hand(_control(rig, side), target, now, weapon_uuid)
        return connected_message(sides, now, lifted)
    finally:
        cmds.undoInfo(closeChunk=True)


def disconnect(rig=None):
    """Bake the hands where the weapon carried them, drop our constraints,
    put the weapon back in the hand. Returns the status text."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    sides = connected_sides(rig)
    if not sides:
        return NOTHING_CONNECTED
    hand, bone, weapon = weapon_of(rig)
    weapon = cmds.ls(weapon, long=True)[0] if weapon else None
    returning = bool(weapon and hand and not _in_hand(weapon, hand))
    if returning:
        gate = overrig.mel_gate()
        if gate:
            return gate

    cmds.undoInfo(openChunk=True, chunkName="Disconnect hands from weapon")
    try:
        keys = cmds.keyframe(weapon, query=True, timeChange=True) if weapon else []
        span = union_range((cmds.playbackOptions(query=True, min=True),
                            cmds.playbackOptions(query=True, max=True)),
                           keys or [])
        controls = [_control(rig, side) for side in sides]
        cmds.bakeResults(controls, attribute=list(CHANNELS),
                         time=(span[0], span[1]), simulation=True, sampleBy=1,
                         preserveOutsideKeys=True)
        for control in controls:
            for con in our_constraints(control):
                if cmds.objExists(con):
                    cmds.delete(con)
        if returning:
            uuid = cmds.ls(weapon, uuid=True)[0]
            overrig.parent_in(weapon, hand)
            weapon = cmds.ls(uuid, long=True)[0]
        return disconnected_message(sides, span, returning)
    finally:
        cmds.undoInfo(closeChunk=True)


# ------------------------------------------------------------------ panel

def _remembered(side_key, default=True):
    var = _OPTIONVAR.format(side_key)
    if cmds.optionVar(exists=var):
        return bool(cmds.optionVar(query=var))
    return default


def _remember(side_key, value):
    cmds.optionVar(intValue=(_OPTIONVAR.format(side_key), int(bool(value))))


def chosen_sides():
    """What the two checkboxes say; both when the panel is not built."""
    if not cmds.control(_RIGHT, exists=True):
        return list(SIDES)
    return hands_to_connect(cmds.checkBox(_RIGHT, query=True, value=True),
                            cmds.checkBox(_LEFT, query=True, value=True))


def _status(text):
    if cmds.control(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
    return text


def _run(action):
    """Failures belong on the status line, not in the Script Editor."""
    try:
        return _status(action())
    except Exception:                                        # noqa: BLE001
        _status(traceback.format_exc().strip().splitlines()[-1])
        raise
    finally:
        refresh()


def header_text(rig, weapon, sides):
    """The header line. Pure."""
    if rig is None:
        return "no rig in the scene"
    if not weapon:
        return "%s: no weapon in the hand" % maya_rigs.label(rig)
    leaf = weapon.split("|")[-1]
    if sides:
        return "%s: %s connected to %s" % (
            maya_rigs.label(rig), ", ".join(SIDE_LABEL[s] for s in sides), leaf)
    return "%s: %s in the hand, hands free" % (maya_rigs.label(rig), leaf)


def refresh(*_args):
    """Re-read the scene into the header. Never writes a checkbox."""
    if not cmds.control(HEADER, exists=True):
        return ""
    rig, _refusal = maya_rigs.current_rig()
    weapon = weapon_of(rig)[2] if rig else None
    sides = connected_sides(rig) if rig else []
    text = header_text(rig, weapon, sides)
    cmds.text(HEADER, edit=True, label=text)
    return text


def is_open():
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Connections section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def _press_connect(*_args):
    return _run(lambda: connect(sides=chosen_sides()))


def _press_disconnect(*_args):
    return _run(lambda: disconnect())


def _side_changed(side_key):
    def go(value):
        _remember(side_key, value)
    return go


def build_panel():
    """Two checkboxes, two buttons, a header and a status line."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", 8))
    cmds.text(HEADER, label="", align="left", wordWrap=True, height=36)
    cmds.text(label="The chosen hands (IK controls) follow the weapon; the "
                    "weapon leaves the hand for world space with its "
                    "animation re-baked by OverRig. The grip is taken from "
                    "the current frame. Disconnect bakes the hands and puts "
                    "the weapon back.",
              align="left", wordWrap=True, height=70)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 120),
                   columnAlign2=("left", "left"))
    cmds.checkBox(_RIGHT, label="Right hand", value=_remembered("right"),
                  changeCommand=_side_changed("right"))
    cmds.checkBox(_LEFT, label="Left hand", value=_remembered("left"),
                  changeCommand=_side_changed("left"))
    cmds.setParent("..")
    cmds.button(label="Connect", height=32, backgroundColor=(0.45, 0.60, 0.70),
                annotation="Hands onto the weapon; the arms go to IK",
                command=_press_connect)
    cmds.button(label="Disconnect", height=26,
                annotation="Bake the hands where the weapon carried them, "
                           "weapon back in the hand",
                command=_press_disconnect)
    cmds.text(STATUS, label="", align="left", wordWrap=True, height=36)
    cmds.setParent("..")
    try:
        refresh()
    except Exception:                                        # noqa: BLE001
        _status(traceback.format_exc().strip().splitlines()[-1])
    return column

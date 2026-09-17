"""Connections -- who drives whom: the two hands and the weapon.

The animator's ask (2026-09-18): «вкладка connections, в которой мы сможем
привязывать и отвязывать руки к оружию … при помощи OverRig, будем
перепекать анимацию (важно, чтобы мы не ломали иерархию нашего рига)»,
then the same day: «нужна какая-то гибкая система переключений: обе руки к
мечу, руки по отдельности, меч к левой или правой руке, меч к правой а
левую руку к мечу».

## The model: three nodes, two links

Left hand -- weapon -- right hand. Each link has three states:

- ``holds``   the weapon hangs in this hand (Weapons > Add puts it there);
              at most ONE hand holds;
- ``follows`` the hand's IK control rides the weapon;
- ``None``    no link.

A *scheme* is ``{"L": state, "R": state}``. Every combination the animator
named is one: both hands follow a weapon standing in world; one hand
follows; the weapon in a hand with the other hand free or following.

## The panel: three rows, a parent for each, Apply per row and Apply all

    Hand_R   [ Free | Weapon         ]  [Apply]
    Hand_L   [ Free | Weapon         ]  [Apply]
    Weapon   [ World | Hand_R | Hand_L ] [Apply]
                                        [ Apply all ]

(the animator's shape, the same day: «заголовок Hand_R, Hand_L, Weapon,
напротив каждого выпадающий список с родителем, напротив каждого кнопка
apply, внизу общая Apply all» - the arrow row that came before it read
unclear). A hand's parent is Free or Weapon (it follows); the weapon's is
World or the hand it hangs in. A choice that would make a cycle - the
weapon in Hand_R while Hand_R follows the weapon - fixes the other menu
and says so (`resolve_menus`, pure). A row's Apply changes that link only
(`wanted_for_row`, pure); Apply all brings the scene to all three menus
(`scheme_from_menus`, pure). The menus are re-read from the scene after
every Apply, so they always show what IS.

## How a transition is done, and why in two different ways

The rig is the AdvancedSkeleton one, and its IK hand controls `IKArm_R` /
`IKArm_L` may NOT leave their place in the DAG - the solver, the follow
switches and the FK/IK align read it. So:

- **The WEAPON is re-baked by OverRig.** Leaving a hand: `apply_Parent_out`
  to world, its track baked onto its own channels (drift 0.000000).
  Entering a hand: `apply_Parent_in` under that hand's bone, whatever the
  animator did with it in world re-baked into the hand's space. The weapon
  is geometry under a bone, not rig, so re-parenting it breaks nothing.
- **The HANDS are constrained, never re-parented.** A following hand's IK
  control gets a `parentConstraint` to the weapon's geometry with
  `maintainOffset` from the CURRENT frame (keys cut first - trap 37; the
  current values written back after the cut - trap 58). Releasing bakes
  the control (`cmds.bakeResults`) and deletes only OUR constraint, found
  by its `skeldarHandLink` attribute.
- **The drive bone follows the holding hand** (the animator's ruling): in
  the right hand the weapon drives `weapon_r`, in the left `weapon_l`, and
  in world it keeps driving the bone it drove last. A bone change unlinks
  the old bone (`bonedrive.unlink`, baked back) and constrains the new one
  onto the weapon with no offset, so the export socket sits ON the weapon.

`FKIKArm_*.FKIKBlend` goes to 10 for a following arm; keyed elsewhere it
is a refusal by name. Poles untouched. The retarget refuses a rig with
following hands (`maya_rig_retarget.hands_connected`).

Spec: docs/superpowers/specs/2026-09-18-connections-design.md (addendum)
"""

import math
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
MENU = {"R": "skeldarConnectionsParentR", "L": "skeldarConnectionsParentL",
        "W": "skeldarConnectionsParentW"}
ROW_LABEL = {"R": "Hand_R", "L": "Hand_L", "W": "Weapon"}
FREE, WORLD, WEAPON = "Free", "World", "Weapon"
HAND_CHOICES = (FREE, WEAPON)
WEAPON_CHOICES = (WORLD, "Hand_R", "Hand_L")
HAND_OF = {"Hand_R": "R", "Hand_L": "L"}

MARKER = "skeldarHandLink"          # on our hand constraints: the weapon's UUID
SIDES = ("L", "R")
SIDE_LABEL = {"R": "right hand", "L": "left hand"}
WEAPON_BONE = {"R": "weapon_r", "L": "weapon_l"}
IK_CONTROL = "IKArm_{0}"
BLEND_NODE = "FKIKArm_{0}"
BLEND_ATTR = "FKIKBlend"
IK_BLEND = 10.0
CHANNELS = ("translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ")

HOLDS = "holds"
FOLLOWS = "follows"

NO_WEAPON = "no weapon in the scene - Weapons > Add first"
NOTHING_TO_DO = "nothing to change"
RETARGETING = ("a retarget is standing on this rig (MoCapConstraints) - "
               "finish it first")


# ------------------------------------------------------------------- pure

def master(scheme):
    """The side holding the weapon, or None (the weapon stands in world)."""
    for side in SIDES:
        if scheme.get(side) == HOLDS:
            return side
    return None


def followers(scheme):
    return [side for side in SIDES if scheme.get(side) == FOLLOWS]


def other(side):
    return "R" if side == "L" else "L"


def menus_from_scheme(scheme):
    """What the three dropdowns show for `scheme`. Pure."""
    held = master(scheme)
    return {"R": WEAPON if scheme.get("R") == FOLLOWS else FREE,
            "L": WEAPON if scheme.get("L") == FOLLOWS else FREE,
            "W": ROW_LABEL[held] if held else WORLD}


def scheme_from_menus(menus):
    """The scheme the three dropdowns describe. The weapon's parent wins a
    conflict: a hand the weapon hangs in holds it whatever its own menu
    says. Pure."""
    held = HAND_OF.get(menus.get("W"))
    scheme = {}
    for side in SIDES:
        if side == held:
            scheme[side] = HOLDS
        else:
            scheme[side] = FOLLOWS if menus.get(side) == WEAPON else None
    return scheme


def resolve_menus(menus, changed):
    """The menus after `changed` was picked, with the cycle fixed: the
    weapon put into a hand frees that hand; a hand set to follow the weapon
    it hangs in puts the weapon into the world. Returns (menus, note). Pure."""
    out = dict(menus)
    note = ""
    if changed == "W":
        held = HAND_OF.get(out["W"])
        if held and out.get(held) == WEAPON:
            out[held] = FREE
            note = "%s set to Free - it holds the weapon" % ROW_LABEL[held]
    elif out.get(changed) == WEAPON and HAND_OF.get(out.get("W")) == changed:
        out["W"] = WORLD
        note = "Weapon set to World - %s follows it" % ROW_LABEL[changed]
    return out, note


def wanted_for_row(current, row, choice):
    """The scheme after ONE row's Apply: that link changed, the rest as it
    stands, a cycle resolved the same way the menus resolve it. Pure."""
    wanted = dict(current)
    if row == "W":
        held = HAND_OF.get(choice)
        for side in SIDES:
            if wanted.get(side) == HOLDS:
                wanted[side] = None
        if held:
            wanted[held] = HOLDS
    else:
        if choice == WEAPON:
            wanted[row] = FOLLOWS
        elif wanted.get(row) in (FOLLOWS, HOLDS):
            wanted[row] = None
    return wanted


def describe(scheme):
    """One line for the header. Pure."""
    held = master(scheme)
    parts = []
    if held:
        parts.append("weapon in the %s" % SIDE_LABEL[held])
    else:
        parts.append("weapon in world")
    fol = followers(scheme)
    if fol:
        parts.append(", ".join(SIDE_LABEL[s] for s in fol)
                     + (" follows" if len(fol) == 1 else " follow"))
    elif held:
        parts.append("%s free" % SIDE_LABEL[other(held)])
    else:
        parts.append("hands free")
    return "; ".join(parts)


def plan(current, wanted):
    """The steps from `current` to `wanted`, in the order they must run.

    Release the hands that stop following (baked where they were), move
    the weapon (lift to world, then hang in the new hand), then hang the
    hands that start following - a hand cannot follow a weapon that is
    about to move under it with a stale offset. Pure.
    """
    steps = []
    for side in SIDES:
        if current.get(side) == FOLLOWS and wanted.get(side) != FOLLOWS:
            steps.append(("release", side))
    was, will = master(current), master(wanted)
    if was != will:
        if was:
            steps.append(("lift", was))
        if will:
            steps.append(("hang", will))
    for side in SIDES:
        if wanted.get(side) == FOLLOWS and current.get(side) != FOLLOWS:
            steps.append(("follow", side))
    return steps


def blend_refusal(side, value, keyed):
    """Why a following arm may not be put in IK, or None. Pure."""
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
    return float(math.floor(start)), float(math.ceil(end))


def applied_message(steps, frame, scheme):
    """What Apply did, then what stands. Pure."""
    words = {"release": "%s released (baked)",
             "lift": "weapon out of the %s to world (re-baked)",
             "hang": "weapon into the %s (re-baked)",
             "follow": "%s follows (grip as at frame " + "%g" % frame + ")"}
    done = [words[step] % SIDE_LABEL[side] for step, side in steps]
    return "Applied: " + "; ".join(done) + " -> " + describe(scheme)


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


def bones_of(rig):
    """{side: (hand bone, drive bone)} for the rig's weapon bones."""
    out = {}
    root = rig.skeleton_root
    for side in SIDES:
        bone = skeleton.resolve_bone(root, WEAPON_BONE[side]) if root else None
        hand = attach.parent_bone(bone) if bone else None
        out[side] = (hand, bone)
    return out


def weapon_of(rig, bones=None):
    """The rig's weapon: what drives a weapon bone, else what hangs under a
    hand. None when there is none."""
    bones = bones or bones_of(rig)
    for side in ("R", "L"):
        hand, bone = bones[side]
        if bone:
            found = bonedrive.driving_weapon(bone)
            if found:
                return cmds.ls(found, long=True)[0]
    for side in ("R", "L"):
        hand, bone = bones[side]
        if hand:
            found = attach.find_attached(hand)
            if found:
                return cmds.ls(found, long=True)[0]
    return None


def driven_side(rig, bones=None):
    """Which weapon bone the weapon drives now, or None."""
    bones = bones or bones_of(rig)
    for side in SIDES:
        bone = bones[side][1]
        if bone and bonedrive.driving_weapon(bone):
            return side
    return None


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
    return [side for side in SIDES
            if _control(rig, side) and our_constraints(_control(rig, side))]


def is_connected(rig):
    return bool(connected_sides(rig))


def read_scheme(rig, bones=None, weapon=None):
    """The scheme the scene stands in: who holds, who follows."""
    bones = bones or bones_of(rig)
    weapon = weapon or weapon_of(rig, bones)
    scheme = {"L": None, "R": None}
    if weapon:
        parent = (cmds.listRelatives(weapon, parent=True, fullPath=True) or [None])[0]
        for side in SIDES:
            if parent and bones[side][0] == parent:
                scheme[side] = HOLDS
    for side in connected_sides(rig):
        scheme[side] = FOLLOWS
    return scheme


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


def _follow(rig, side, target, now, weapon_uuid):
    """Keys cut, the current pose written back, the constraint made with the
    offset the animator is looking at, our mark on it; the arm in IK."""
    plug = _blend_plug(rig, side)
    if plug and not cmds.listConnections(plug, source=True, destination=False):
        cmds.setAttr(plug, IK_BLEND)
    control = _control(rig, side)
    values = _values_now(control, now)
    cmds.cutKey(control, attribute=list(CHANNELS), clear=True)
    for channel, value in values.items():
        cmds.setAttr(control + "." + channel, value)
    con = cmds.parentConstraint(target, control, maintainOffset=True)[0]
    con = cmds.ls(con, long=True)[0]
    cmds.addAttr(con, longName=MARKER, dataType="string")
    cmds.setAttr(con + "." + MARKER, weapon_uuid, type="string")
    return con


def _release(rig, side, span):
    """Bake the control where the weapon carried it, drop our constraint."""
    control = _control(rig, side)
    cmds.bakeResults([control], attribute=list(CHANNELS),
                     time=(span[0], span[1]), simulation=True, sampleBy=1,
                     preserveOutsideKeys=True)
    for con in our_constraints(control):
        if cmds.objExists(con):
            cmds.delete(con)


def _drive_bone(weapon, bone):
    """The drive bone onto the weapon, no offset: the export socket sits ON
    the weapon wherever the animator put it. Keys cut first (trap 37)."""
    values = _values_now(bone, cmds.currentTime(query=True))
    cmds.cutKey(bone, attribute=list(CHANNELS), clear=True)
    for channel, value in values.items():
        try:
            cmds.setAttr(bone + "." + channel, value)
        except RuntimeError:
            pass
    cmds.parentConstraint(weapon, bone, maintainOffset=False)


def _span(weapon):
    keys = cmds.keyframe(weapon, query=True, timeChange=True) if weapon else []
    return union_range((cmds.playbackOptions(query=True, min=True),
                        cmds.playbackOptions(query=True, max=True)), keys or [])


def apply(wanted, rig=None):
    """Bring the scene from the scheme it stands in to `wanted`.

    Returns the status text; refusals happen before anything moves.
    """
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    bones = bones_of(rig)
    weapon = weapon_of(rig, bones)
    if not weapon:
        return NO_WEAPON
    if cmds.objExists(maya_rigs.node(rig, "MoCapConstraints")):
        return RETARGETING
    current = read_scheme(rig, bones, weapon)
    steps = plan(current, wanted)
    if not steps:
        return NOTHING_TO_DO
    for step, side in steps:
        if step == "hang" and not (bones[side][0] and bones[side][1]):
            return "%s: no %s bone (or its hand) on this rig" % (
                SIDE_LABEL[side], WEAPON_BONE[side])
        if step == "follow":
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
    if any(step in ("lift", "hang") for step, _ in steps):
        gate = overrig.mel_gate()
        if gate:
            return gate

    now = cmds.currentTime(query=True)
    uuid = cmds.ls(weapon, uuid=True)[0]
    cmds.undoInfo(openChunk=True, chunkName="Connections: apply")
    try:
        span = _span(weapon)
        for step, side in steps:
            weapon = cmds.ls(uuid, long=True)[0]
            if step == "release":
                _release(rig, side, span)
            elif step == "lift":
                overrig.parent_out(weapon)
            elif step == "hang":
                hand, bone = bones[side]
                overrig.parent_in(weapon, hand)
                weapon = cmds.ls(uuid, long=True)[0]
                if driven_side(rig, bones) != side:
                    was = driven_side(rig, bones)
                    if was:
                        bonedrive.unlink(bones[was][1])
                    _drive_bone(weapon, bone)
            elif step == "follow":
                _follow(rig, side, attach.model_root(weapon), now, uuid)
        return applied_message(steps, now, read_scheme(rig, bones))
    finally:
        cmds.undoInfo(closeChunk=True)


def connect(rig=None, sides=SIDES):
    """Both (or the given) hands follow the weapon standing in world - the
    hotkey's meaning; the panel goes through `apply`."""
    wanted = {"L": None, "R": None}
    for side in sides:
        wanted[side] = FOLLOWS
    return apply(wanted, rig=rig)


def disconnect(rig=None):
    """No hand follows; the weapon back in the hand whose bone it drives."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    held = driven_side(rig) or "R"
    wanted = {"L": None, "R": None, held: HOLDS}
    return apply(wanted, rig=rig)


# ------------------------------------------------------------------ panel

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


def header_text(rig, weapon, scheme):
    """The header line. Pure."""
    if rig is None:
        return "no rig in the scene"
    if not weapon:
        return "%s: no weapon - Weapons > Add first" % maya_rigs.label(rig)
    return "%s: %s - %s" % (maya_rigs.label(rig), weapon.split("|")[-1],
                            describe(scheme))


def menus():
    """What the three dropdowns say now."""
    return {row: cmds.optionMenu(MENU[row], query=True, value=True)
            for row in ("R", "L", "W")}


def _set_menus(values):
    for row, value in values.items():
        if cmds.optionMenu(MENU[row], exists=True):
            cmds.optionMenu(MENU[row], edit=True, value=value)


def refresh(*_args):
    """Re-read the scene into the header and the menus: after a press what
    IS is what the dropdowns show."""
    if not cmds.control(HEADER, exists=True):
        return ""
    rig, _refusal = maya_rigs.current_rig()
    weapon = weapon_of(rig) if rig else None
    scheme = read_scheme(rig) if rig else {"L": None, "R": None}
    _set_menus(menus_from_scheme(scheme))
    text = header_text(rig, weapon, scheme)
    cmds.text(HEADER, edit=True, label=text)
    return text


def is_open():
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Connections section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def _menu_changed(row):
    """A pick fixes a cycle in the other menus and asks for Apply."""
    def go(*_args):
        fixed, note = resolve_menus(menus(), row)
        _set_menus(fixed)
        text = "press Apply for: " + describe(scheme_from_menus(fixed))
        _status((note + "; " + text) if note else text)
    return go


def _press_row(row):
    def go(*_args):
        def act():
            rig, refusal = maya_rigs.current_rig()
            if rig is None:
                return refusal
            wanted = wanted_for_row(read_scheme(rig), row, menus()[row])
            return apply(wanted, rig=rig)
        return _run(act)
    return go


def _press_apply_all(*_args):
    return _run(lambda: apply(scheme_from_menus(menus())))


def _press_connect(*_args):
    return _run(lambda: connect())


def _press_disconnect(*_args):
    return _run(lambda: disconnect())


def build_panel():
    """A header, three parent rows each with its Apply, Apply all, status."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", 8))
    cmds.text(HEADER, label="", align="left", wordWrap=True, height=36)
    cmds.text(label="Pick each node's parent. A hand's parent Weapon means "
                    "the hand follows the weapon (IK); the weapon's parent "
                    "is the hand it hangs in. Apply on a row changes that "
                    "link only; Apply all brings the scene to all three. "
                    "Released hands are baked, the weapon moves through "
                    "OverRig with its animation re-baked, followers take "
                    "the grip of the current frame.",
              align="left", wordWrap=True, height=88)
    for row, choices in (("R", HAND_CHOICES), ("L", HAND_CHOICES),
                         ("W", WEAPON_CHOICES)):
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                       columnWidth3=(70, 150, 70),
                       columnAlign3=("left", "left", "center"),
                       columnAttach=[(1, "left", 0), (2, "both", 4),
                                     (3, "right", 0)])
        cmds.text(label=ROW_LABEL[row], font="boldLabelFont")
        cmds.optionMenu(MENU[row], changeCommand=_menu_changed(row),
                        annotation="the parent of " + ROW_LABEL[row])
        for choice in choices:
            cmds.menuItem(label=choice)
        cmds.button(label="Apply", width=66, height=24,
                    annotation="apply this row's parent only",
                    command=_press_row(row))
        cmds.setParent("..")
    cmds.button(label="Apply all", height=32,
                backgroundColor=(0.45, 0.70, 0.50),
                annotation="bring the scene to all three parents",
                command=_press_apply_all)
    cmds.text(STATUS, label="", align="left", wordWrap=True, height=36)
    cmds.setParent("..")
    try:
        refresh()
    except Exception:                                        # noqa: BLE001
        _status(traceback.format_exc().strip().splitlines()[-1])
    return column

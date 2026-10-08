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
  Entering a hand: `apply_Parent_in` under that hand's WEAPON SPACE
  (`weaponspace`, since 2026-09-24: a transform outside the skeleton that
  follows the hand with no offset - the skeleton holds bones only),
  whatever the animator did with it in world re-baked into the hand's
  space. A space left empty by the move is pruned. The weapon is geometry,
  not rig, so re-parenting it breaks nothing.
- **The HANDS are constrained to a PROXY, never re-parented.** A
  following hand gets a locator `handProxy_<side>` INSIDE the weapon's
  geometry; the hand's own world track is baked onto that proxy over the
  range (so, in the weapon's space, the hand keeps exactly the motion it
  had - nothing is flattened to one frame's grip), channels that came out
  constant are un-keyed (the vendor's `delete -staticChannels` idea), and
  the IK control is parent-constrained to the proxy with no offset (keys
  cut first - trap 37; the current values written back after the cut -
  trap 58). **The proxy is what the animator animates from then on**: a
  key on it moves the hand against the weapon, while the weapon still
  carries the hand (the animator, 2026-09-18: «сейчас мы теряем
  возможность анимировать объект, который был приконстрейнен … через
  прокси-локатор внутри родителя, перепечь на него анимацию и уже потом
  констрейнить»). Releasing bakes the control (`cmds.bakeResults`),
  deletes only OUR constraint (its `skeldarHandLink` attribute) and the
  proxy (its `skeldarHandProxy` attribute).
- **The drive bone follows the holding hand** (the animator's ruling): in
  the right hand the weapon drives `weapon_r`, in the left `weapon_l`, and
  in world it keeps driving the bone it drove last. A bone change unlinks
  the old bone (`bonedrive.unlink`, baked back) and constrains the new one
  onto the weapon with no offset, so the export socket sits ON the weapon.

A following arm is brought to IK over the whole take first, by the FK/IK
switch (`fkik`, 2026-09-30): the IK is keyed to what the arm SHOWS, so an FK
arm edited after the retarget no longer jumps when its hand goes onto the
weapon, and a keyed blend is no longer a refusal. The retarget refuses a rig
with following hands (`maya_rig_retarget.hands_connected`).

## FK / IK (2026-09-30)

Two rows at the top, `Arm_R [FK | IK]`, `Arm_L [FK | IK]`: a press switches
that arm at once, over the highlighted range on the time slider or else the
whole take, keeping what the arm shows (`fkik`); the lit segment is the mode
read from the rig, none when the blend is mixed. FK on a hand that rides the
weapon releases it first (baked where its proxy carried it).

Spec: docs/superpowers/specs/2026-09-18-connections-design.md (addendum)
"""

import math
import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle
import maya_rigs
from maya_overrig import overrig
from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import fkik
from maya_scenesetup import skeleton
from maya_scenesetup import weaponspace

HUB_SECTION = "connections"
STATUS = "skeldarConnectionsStatus"
HEADER = "skeldarConnectionsHeader"
MENU = {"R": "skeldarConnectionsParentR", "L": "skeldarConnectionsParentL",
        "W": "skeldarConnectionsParentW"}
ROW_LABEL = {"R": "Hand_R", "L": "Hand_L", "W": "Weapon"}
# Which of two weapons the rows act on (2026-09-29): a segment row above them,
# its pick kept by UUID (a rename or a re-parent keeps it).
CHOOSER = "skeldarConnectionsWeapon"
# the row holding the chooser: shown only while two weapons stand (2026-10-08,
# the compact hub - with one weapon the chooser had nothing to choose)
CHOOSER_ROW = "skeldarConnectionsChooserRow"
_PICKED = {"uuid": None, "selection": None}
NO_SLOT = "-"
FREE, WORLD, WEAPON = "Free", "World", "Weapon"
HAND_CHOICES = (FREE, WEAPON)
WEAPON_CHOICES = (WORLD, "Hand_R", "Hand_L")
HAND_OF = {"Hand_R": "R", "Hand_L": "L"}
_ROWS = (("R", HAND_CHOICES), ("L", HAND_CHOICES), ("W", WEAPON_CHOICES))
#  what a segment reads (2026-09-28); the values stay the choices above
SEGMENT_LABEL = {"Hand_R": "Hand R", "Hand_L": "Hand L"}

MARKER = "skeldarHandLink"          # on our hand constraints: the proxy's UUID
PROXY_MARKER = "skeldarHandProxy"   # on the proxy locator: the side it carries
PROXY_NAME = "handProxy_{0}"
PROXY_SCALE = 8.4                    # the locator's local scale, cm (+40 %)
HIDDEN_VIS = "skeldarHiddenVis"      # on our constraint: the object's visibility before
STATIC_TOLERANCE = 1e-6
SIDES = ("L", "R")
SIDE_LABEL = {"R": "right hand", "L": "left hand"}
WEAPON_BONE = {"R": "weapon_r", "L": "weapon_l"}
IK_CONTROL = "IKArm_{0}"
# the FK / IK rows (2026-09-30): two check boxes a row, either press switches
FKIK_BOX = "skeldarConnectionsFKIK_{0}_{1}"
ARM_ROW = "Arm_{0}"
CHANNELS =("translateX", "translateY", "translateZ",
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


def choose_weapon(weapons, selection, picked, picked_selection=None):
    """The weapon the section acts on, of the rig's `weapons` (long paths).
    Pure. The one picked in the chooser while the selection is what it was
    at the pick (`picked_selection`) - the pick is the newer word; else the
    selection's (the weapon itself or anything under it, one of its proxies
    too); else the picked one while it is still the rig's; else the first."""
    if picked in weapons and picked_selection is not None \
            and list(selection or []) == list(picked_selection):
        return picked
    for path in selection or []:
        for weapon in weapons:
            if path == weapon or path.startswith(weapon + "|"):
                return weapon
    if picked in weapons:
        return picked
    return weapons[0] if weapons else None


def labels_for(pairs):
    """[(label, side)] -> the chooser's labels, the hand named where two
    weapons share a label. Pure."""
    labels = [label for label, _side in pairs]
    return [("%s (%s)" % (label, side)
             if labels.count(label) > 1 and side else label)
            for label, side in pairs]


def blocked(current, wanted, other, other_label, bone_taken=None):
    """Why `wanted` (this weapon's scheme, from `current`) may not stand
    beside the other weapon's scheme `other`, or "". Pure.

    A hand holds XOR follows, across both weapons (2026-09-29): a holding
    hand rides nothing, so no chain of rides can close into a loop. A hand
    whose bone the other weapon drives from world (`bone_taken`) takes no
    weapon - one bone, one weapon. Only the links that change are checked:
    what already stands is never refused.
    """
    for side in SIDES:
        mine = wanted.get(side)
        if not mine or mine == current.get(side):
            continue
        theirs = (other or {}).get(side)
        if theirs == HOLDS:
            return "%s holds the %s - move it first" % (ROW_LABEL[side],
                                                        other_label)
        if theirs == FOLLOWS:
            return "%s follows the %s - release it first" % (ROW_LABEL[side],
                                                            other_label)
        if mine == HOLDS and side == bone_taken:
            return ("%s is driven by the %s (in world) - remove it or put it "
                    "in a hand first" % (WEAPON_BONE[side], other_label))
    return ""


def is_constant(values, tolerance=STATIC_TOLERANCE):
    """True when a sampled channel never moves: its keys collapse to a plain
    value so the animator's own keys on the proxy start from nothing. Pure."""
    values = list(values)
    return not values or (max(values) - min(values)) <= tolerance


def union_range(playback, keys):
    """(start, end) covering the playback range and the weapon's keys,
    snapped outward to whole frames. Pure."""
    start, end = float(playback[0]), float(playback[1])
    if keys:
        start = min(start, min(keys))
        end = max(end, max(keys))
    return float(math.floor(start)), float(math.ceil(end))


def applied_message(steps, scheme):
    """What Apply did, then what stands. Pure."""
    words = {"release": "%s released (baked)",
             "lift": "weapon out of the %s to world (re-baked)",
             "hang": "weapon into the %s (re-baked)",
             "follow": "%s follows (its track kept on the proxy)"}
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
    paths = cmds.ls(maya_rigs.node(rig, fkik.FKIK_NODE.format(fkik.LIMB, side)),
                    long=True) or []
    return (paths[0] + "." + fkik.BLEND_ATTR) if paths else None


def _not_ik(rig, side):
    """The arm, when it is not IK over the whole take (else None)."""
    arm, _refusal = fkik.limb(rig, side)
    if arm and fkik.mode_of(fkik.blend_values(arm)) != fkik.IK:
        return arm
    return None


def _whole(arm):
    return fkik.span_for(None, fkik.whole_take(arm))


def bones_of(rig):
    """{side: (hand bone, drive bone)} for the rig's weapon bones."""
    out = {}
    root = rig.skeleton_root
    for side in SIDES:
        bone = skeleton.resolve_bone(root, WEAPON_BONE[side]) if root else None
        hand = attach.parent_bone(bone) if bone else None
        out[side] = (hand, bone)
    return out


def _same(a, b):
    return bool(a and b) and cmds.ls(a, long=True) == cmds.ls(b, long=True)


def weapons_of(rig, bones=None):
    """Every weapon of the rig, right-hand related first (2026-09-29, up to
    two): what drives a weapon bone, what hangs in a hand's space, what a
    hand's proxy rides - out in world with no bone link left (somebody
    deleted it) it is still whatever this rig's hands ride."""
    bones = bones or bones_of(rig)
    found = []

    def add(node):
        paths = cmds.ls(node, long=True) if node else []
        if paths and paths[0] not in found:
            found.append(paths[0])

    for side in ("R", "L"):
        hand, bone = bones[side]
        if bone:
            add(bonedrive.driving_weapon(bone))
        if hand:
            add(attach.find_attached(hand))
    for side in ("R", "L"):
        add(following(rig, side))
    return found


def chosen_weapon(rig, bones=None, weapons=None):
    """The weapon the section acts on (`choose_weapon` over the scene)."""
    weapons = weapons if weapons is not None else weapons_of(rig, bones)
    picked = cmds.ls(_PICKED["uuid"], long=True) if _PICKED["uuid"] else []
    return choose_weapon(weapons, cmds.ls(selection=True, long=True) or [],
                         picked[0] if picked else None,
                         _PICKED.get("selection"))


def weapon_of(rig, bones=None):
    """The rig's weapon the section acts on, or None (kept for its callers:
    with one weapon, that weapon)."""
    return chosen_weapon(rig, bones)


def driven_side(rig, bones=None, weapon=None):
    """Which weapon bone `weapon` drives now (any weapon, without one), or None."""
    bones = bones or bones_of(rig)
    for side in SIDES:
        bone = bones[side][1]
        driver = bonedrive.driving_weapon(bone) if bone else None
        if driver and (weapon is None or _same(driver, weapon)):
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


def followers_of(weapon):
    """The sides whose hands ride `weapon`: the proxies inside it, found by
    attribute (a following hand's proxy is a locator in the weapon's
    geometry). What makes a weapon out in world "linked" (2026-09-29): one
    nothing rides is its hand's to replace or take off."""
    out = []
    if not weapon or not cmds.objExists(weapon):
        return out
    for node in cmds.listRelatives(weapon, allDescendents=True,
                                   type="transform", fullPath=True) or []:
        if cmds.attributeQuery(PROXY_MARKER, node=node, exists=True):
            side = (cmds.getAttr(node + "." + PROXY_MARKER) or "").split(":")[-1]
            if side in SIDES and side not in out:
                out.append(side)
    return out


def _marked_above(node):
    """The nearest marked weapon at or above `node`, or None."""
    while node:
        if cmds.attributeQuery(attach.MARKER, node=node, exists=True):
            return cmds.ls(node, long=True)[0]
        node = (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0]
    return None


def following(rig, side):
    """The weapon `side`'s IK hand rides (through our proxy), or None."""
    control = _control(rig, side)
    for con in our_constraints(control) if control else []:
        proxy = proxy_for(con)
        if proxy:
            found = _marked_above(proxy)
            if found:
                return found
    return None


def weapon_label(weapon):
    """A weapon node's catalog label (its marker key), else its leaf name."""
    if not weapon:
        return ""
    key = ""
    if cmds.objExists(weapon) and cmds.attributeQuery(attach.MARKER, node=weapon, exists=True):
        key = cmds.getAttr(weapon + "." + attach.MARKER) or ""
    entry = catalog.by_key(key) if key else None
    return entry.label if entry else weapon.split("|")[-1]


def connected_sides(rig):
    """The sides whose IK control rides a weapon through our constraint."""
    return [side for side in SIDES
            if _control(rig, side) and our_constraints(_control(rig, side))]


def is_connected(rig):
    return bool(connected_sides(rig))


def read_scheme(rig, bones=None, weapon=None):
    """The scheme `weapon` (the chosen one without it) stands in: which hand
    holds it, which hands ride it. The other weapon's hands are not in it."""
    bones = bones or bones_of(rig)
    weapon = weapon or weapon_of(rig, bones)
    scheme = {"L": None, "R": None}
    if weapon:
        # the hand's SPACE holds the weapon since 2026-09-24 (outside the
        # skeleton); a file from before holds it under the hand bone itself
        holder = weaponspace.holding_hand(weapon)
        for side in SIDES:
            if holder and bones[side][0] and cmds.ls(bones[side][0], long=True) == cmds.ls(holder, long=True):
                scheme[side] = HOLDS
        for side in connected_sides(rig):
            if _same(following(rig, side), weapon):
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


def proxies():
    """Every proxy locator of ours in the scene, by attribute (a name
    pattern would miss the ones in a namespace - `*.attr` does not cross
    a colon, which is how proxies once survived a bake)."""
    out = []
    for shape in cmds.ls(type="locator", long=True) or []:
        node = (cmds.listRelatives(shape, parent=True, fullPath=True) or [None])[0]
        if node and cmds.attributeQuery(PROXY_MARKER, node=node, exists=True):
            out.append(node)
    return out


def proxy_of(rig, side):
    """The side's proxy locator, or None."""
    tag = "%s:%s" % (rig.namespace, side)
    for node in proxies():
        if cmds.getAttr(node + "." + PROXY_MARKER) == tag:
            return node
    return None


def orphan_proxies():
    """Proxies no constraint of ours points at any more - debris a bake
    left behind (the first build lost them behind a namespace colon)."""
    pointed = set()
    for con in cmds.ls(type="parentConstraint", long=True) or []:
        if cmds.attributeQuery(MARKER, node=con, exists=True):
            pointed.add(cmds.getAttr(con + "." + MARKER))
    return [node for node in proxies()
            if cmds.ls(node, uuid=True)[0] not in pointed]


def sweep_orphans():
    """Delete the orphan proxies. Returns how many. Called at the front of
    every Apply and BakeAcross, never from a refresh."""
    orphans = orphan_proxies()
    for node in orphans:
        if cmds.objExists(node):
            cmds.delete(node)
    return len(orphans)


def proxy_for(constraint):
    """The proxy our constraint points at (its UUID is the mark), or None."""
    uuid = cmds.getAttr(constraint + "." + MARKER)
    found = cmds.ls(uuid, long=True) if uuid else []
    return found[0] if found else None


def _make_proxy(name, parent, tag):
    """A locator INSIDE `parent`, marked with `tag`. The one place this
    module re-parents anything - and it is our own locator."""
    proxy = cmds.spaceLocator(name=name)[0]
    cmds.setAttr(proxy + ".localScale", PROXY_SCALE, PROXY_SCALE, PROXY_SCALE,
                 type="double3")
    proxy = cmds.parent(proxy, parent, relative=True)[0]
    proxy = cmds.ls(proxy, long=True)[0]
    cmds.addAttr(proxy, longName=PROXY_MARKER, dataType="string")
    cmds.setAttr(proxy + "." + PROXY_MARKER, tag, type="string")
    return proxy


def _bake_onto(source, proxy, span):
    """The source's world track onto the proxy's channels (in its parent's
    space), then the still channels un-keyed."""
    temporary = cmds.parentConstraint(source, proxy, maintainOffset=False)[0]
    cmds.bakeResults([proxy], attribute=list(CHANNELS),
                     time=(span[0], span[1]), simulation=True, sampleBy=1)
    cmds.delete(temporary)
    for channel in CHANNELS:
        plug = proxy + "." + channel
        values = cmds.keyframe(plug, query=True, valueChange=True) or []
        if values and is_constant(values):
            value = values[0]
            cmds.cutKey(plug, clear=True)
            cmds.setAttr(plug, value)


def _set_visible(node, visible):
    """Best effort: a visibility channel may be locked or driven."""
    try:
        cmds.setAttr(node + ".visibility", bool(visible))
        return True
    except RuntimeError:
        return False


def attach_to_proxy(obj, parent, span, name, tag):
    """`obj` rides a proxy inside `parent`: the proxy created and baked from
    the object's own world track, the object's keys cut and its pose written
    back, the object constrained to the proxy with no offset, hidden (the
    animator's ask - the constrained control only gets in the way of the
    proxy), our mark and its old visibility on the constraint."""
    now = cmds.currentTime(query=True)
    proxy = _make_proxy(name, parent, tag)
    _bake_onto(obj, proxy, span)
    values = _values_now(obj, now)
    cmds.cutKey(obj, attribute=list(CHANNELS), clear=True)
    for channel, value in values.items():
        cmds.setAttr(obj + "." + channel, value)
    con = cmds.parentConstraint(proxy, obj, maintainOffset=False)[0]
    con = cmds.ls(con, long=True)[0]
    cmds.addAttr(con, longName=MARKER, dataType="string")
    cmds.setAttr(con + "." + MARKER, cmds.ls(proxy, uuid=True)[0], type="string")
    cmds.addAttr(con, longName=HIDDEN_VIS, attributeType="short")
    cmds.setAttr(con + "." + HIDDEN_VIS, int(bool(cmds.getAttr(obj + ".visibility"))))
    _set_visible(obj, False)
    return proxy, con


def detach_from_proxy(obj, span):
    """Bake `obj` where its proxy carried it, drop our constraint, delete the
    proxy, show the object again. Returns the number of proxies removed."""
    cons = our_constraints(obj)
    if not cons:
        return 0
    cmds.bakeResults([obj], attribute=list(CHANNELS),
                     time=(span[0], span[1]), simulation=True, sampleBy=1,
                     preserveOutsideKeys=True)
    removed = 0
    visible = True
    for con in cons:
        proxy = proxy_for(con)
        if cmds.attributeQuery(HIDDEN_VIS, node=con, exists=True):
            visible = bool(cmds.getAttr(con + "." + HIDDEN_VIS))
        if cmds.objExists(con):
            cmds.delete(con)
        if proxy and cmds.objExists(proxy):
            cmds.delete(proxy)
            removed += 1
    _set_visible(obj, visible)
    return removed


def _follow(rig, side, target, span):
    """The hand's IK control onto a proxy inside the weapon. An arm not in
    IK over the whole take is switched first, keeping what it shows (before
    2026-09-30 the blend was only set to 10 over whatever the IK held, and
    an FK arm edited after the retarget jumped). On every frame, not only
    the keys (2026-10-08): the proxy is baked on every frame anyway, and
    between keys an IK hand would take its own path. Returns the switch's
    note, or ''."""
    arm = _not_ik(rig, side)
    note = fkik.switch(arm, fkik.IK, _whole(arm), every_frame=True) if arm else ""
    attach_to_proxy(_control(rig, side), target, span,
                    maya_rigs.node(rig, PROXY_NAME.format(side)),
                    "%s:%s" % (rig.namespace, side))
    return note


def _release(rig, side, span):
    """The hand baked where its proxy carried it, constraint and proxy gone."""
    return detach_from_proxy(_control(rig, side), span)


def _drive_bone(weapon, bone):
    """The drive bone onto the weapon, no offset: the export socket sits ON
    the weapon wherever the animator put it. Keys cut first (trap 37).

    ON the weapon's socket, that is: a model standing in a frame of its own
    (`bonedrive.FRAME_ROTATE`, the Creep Sword's 45) is turned against the
    bone by exactly that frame at zero grip, so the constraint's target
    offset undoes it -- the bone takes the weapon's world as the weapon's
    old bone did. The identity for every other weapon. `bonedrive.drive_socket`
    since 2026-09-29 - the floor drives its bone the same way."""
    return bonedrive.drive_socket(weapon, bone)


def _span(weapon, controls=()):
    """Playback range, the weapon's keys and the controls' keys, whole frames."""
    keys = list(cmds.keyframe(weapon, query=True, timeChange=True) or []) if weapon else []
    for control in controls:
        if control:
            keys.extend(cmds.keyframe(control, query=True, timeChange=True) or [])
    return union_range((cmds.playbackOptions(query=True, min=True),
                        cmds.playbackOptions(query=True, max=True)), keys)


def apply(wanted, rig=None, weapon=None):
    """Bring `weapon` (the chosen one without it) from the scheme it stands
    in to `wanted`.

    Returns the status text; refusals happen before anything moves - the
    other weapon's included (`blocked`).
    """
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    bones = bones_of(rig)
    weapons = weapons_of(rig, bones)
    weapon = weapon or chosen_weapon(rig, bones, weapons)
    if not weapon:
        return NO_WEAPON
    if cmds.objExists(maya_rigs.node(rig, "MoCapConstraints")):
        return RETARGETING
    current = read_scheme(rig, bones, weapon)
    steps = plan(current, wanted)
    if not steps:
        return NOTHING_TO_DO
    for other in [w for w in weapons if not _same(w, weapon)]:
        taken = (None if weaponspace.holding_hand(other)
                 else driven_side(rig, bones, other))
        text = blocked(current, wanted, read_scheme(rig, bones, other),
                       weapon_label(other), taken)
        if text:
            return text
    for step, side in steps:
        if step == "hang" and not (bones[side][0] and bones[side][1]):
            return "%s: no %s bone (or its hand) on this rig" % (
                SIDE_LABEL[side], WEAPON_BONE[side])
        if step == "follow":
            if not _control(rig, side):
                return "%s: %s not found in %s" % (SIDE_LABEL[side],
                                                   IK_CONTROL.format(side),
                                                   maya_rigs.label(rig))
            arm = _not_ik(rig, side)
            text = fkik.refusal(arm, fkik.IK, _whole(arm)) if arm else ""
            if text:
                return text
    if any(step in ("lift", "hang") for step, _ in steps):
        gate = overrig.mel_gate()
        if gate:
            return gate

    uuid = cmds.ls(weapon, uuid=True)[0]
    notes = []
    cmds.undoInfo(openChunk=True, chunkName="Connections: apply")
    try:
        sweep_orphans()
        span = _span(weapon, [_control(rig, side) for side in SIDES])
        for step, side in steps:
            weapon = cmds.ls(uuid, long=True)[0]
            if step == "release":
                _release(rig, side, span)
            elif step == "lift":
                was = (cmds.listRelatives(weapon, parent=True, fullPath=True) or [None])[0]
                overrig.parent_out(weapon)
                weaponspace.prune(was)
                # out of the hand, still the character's: into its group (2026-10-02), an
                # identity parent, so the track parent_out baked in world is unchanged
                from maya_scenesetup import chargroup
                chargroup.park(cmds.ls(uuid, long=True)[0], rig)
            elif step == "hang":
                hand, bone = bones[side]
                # into the space that follows the hand -- the skeleton holds
                # bones only; parent_in re-bakes the track into its space,
                # which stands exactly where the hand does
                was = (cmds.listRelatives(weapon, parent=True, fullPath=True) or [None])[0]
                overrig.parent_in(weapon, weaponspace.ensure_space(hand))
                weaponspace.prune(was)
                weapon = cmds.ls(uuid, long=True)[0]
                if driven_side(rig, bones, weapon) != side:
                    was = driven_side(rig, bones, weapon)
                    if was:
                        bonedrive.unlink(bones[was][1])
                    _drive_bone(weapon, bone)
                # In a hand the bone's truth is the weapon's motion: a track
                # a floor drop parked on it no longer belongs to anybody.
                bonedrive.drop_park(weapon)
            elif step == "follow":
                note = _follow(rig, side, attach.model_root(weapon), span)
                if note:
                    notes.append(note)
        weapon = cmds.ls(uuid, long=True)[0]
        return applied_message(steps, read_scheme(rig, bones, weapon)) + \
            "".join(" | " + note for note in notes)
    finally:
        cmds.undoInfo(closeChunk=True)


def across_plan(paths):
    """(parent, children) for BakeAcross from the selection in order, or
    (None, refusal). The LAST selected is the parent, everything before it
    rides. Pure."""
    paths = list(paths)
    if len(paths) < 2:
        return None, "select the objects to attach, then the parent LAST (two or more)"
    parent, children = paths[-1], paths[:-1]
    for child in children:
        if child == parent or parent.startswith(child + "|"):
            return None, "%s is above the parent %s - a cycle" % (
                child.split("|")[-1], parent.split("|")[-1])
        if child.startswith(parent + "|"):
            return None, "%s is already inside %s" % (
                child.split("|")[-1], parent.split("|")[-1])
    return parent, children


def across_message(children, parent):
    return "BakeAcross: %d object(s) ride proxies inside %s (hidden; key the proxies)" % (
        len(children), parent.split("|")[-1])


def release_message(count, proxies):
    return "Released %d object(s), %d proxy(ies) removed, objects shown" % (count, proxies)


def _transforms(paths):
    """The selection as transform LONG paths, shapes resolved to their
    transforms, duplicates dropped. Long, or `across_plan`'s cycle check -
    a prefix test on paths - reads a short name as outside everything."""
    out = []
    for path in paths:
        found = cmds.ls(path, long=True) or []
        if not found:
            continue
        path = found[0]
        if cmds.objectType(path, isAType="transform"):
            out.append(path)
        else:
            parent = cmds.listRelatives(path, parent=True, fullPath=True) or []
            if parent and cmds.objectType(parent[0], isAType="transform"):
                out.append(parent[0])
    seen = []
    for path in out:
        if path not in seen:
            seen.append(path)
    return seen


def bake_across(selection=None):
    """The animator's ask: every selected object rides the LAST selected
    one through a proxy locator of its own - its track kept, keyable on
    the proxy - the way a following hand rides the weapon."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    parent, children = across_plan(_transforms(selection))
    if parent is None:
        return children
    for child in children:
        if our_constraints(child):
            return "%s already rides a proxy - Release it first" % child.split("|")[-1]
    keys = []
    for node in [parent] + children:
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
    span = union_range((cmds.playbackOptions(query=True, min=True),
                        cmds.playbackOptions(query=True, max=True)), keys)
    cmds.undoInfo(openChunk=True, chunkName="BakeAcross")
    try:
        sweep_orphans()
        for child in children:
            attach_to_proxy(child, parent, span,
                            child.split("|")[-1].split(":")[-1] + "_proxy",
                            cmds.ls(child, uuid=True)[0])
        cmds.select(parent, replace=True)
        return across_message(children, parent)
    finally:
        cmds.undoInfo(closeChunk=True)


def release_across(selection=None):
    """Every selected object that rides one of our proxies is baked where
    the proxy carried it and freed; a selected PROXY frees its rider."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    riders = []
    for node in _transforms(selection):
        if our_constraints(node):
            riders.append(node)
        elif cmds.attributeQuery(PROXY_MARKER, node=node, exists=True):
            uuid = cmds.ls(node, uuid=True)[0]
            for con in cmds.ls(type="parentConstraint", long=True) or []:
                if cmds.attributeQuery(MARKER, node=con, exists=True) \
                        and cmds.getAttr(con + "." + MARKER) == uuid:
                    rider = (cmds.listRelatives(con, parent=True, fullPath=True) or [None])[0]
                    if rider and rider not in riders:
                        riders.append(rider)
    if not riders:
        return "nothing selected rides a proxy of ours"
    keys = []
    for node in riders:
        keys.extend(cmds.keyframe(node, query=True, timeChange=True) or [])
        for con in our_constraints(node):
            proxy = proxy_for(con)
            if proxy:
                keys.extend(cmds.keyframe(proxy, query=True, timeChange=True) or [])
    span = union_range((cmds.playbackOptions(query=True, min=True),
                        cmds.playbackOptions(query=True, max=True)), keys)
    cmds.undoInfo(openChunk=True, chunkName="Release across")
    try:
        removed = 0
        for node in riders:
            removed += detach_from_proxy(node, span)
        cmds.select(riders, replace=True)
        return release_message(len(riders), removed)
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
    """No hand follows the chosen weapon; it goes back into the hand whose
    bone it drives."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    weapon = weapon_of(rig)
    held = driven_side(rig, None, weapon) or "R"
    wanted = {"L": None, "R": None, held: HOLDS}
    return apply(wanted, rig=rig)


def _highlight():
    """The range highlighted on the time slider, or None (none in batch)."""
    try:
        return overrig.slider_selection()
    except Exception:                                        # noqa: BLE001
        return None


def switch_arm(side, mode, rig=None, highlight=None):
    """The arm on `side` to FK or IK over the highlighted range, else the
    whole take, keeping what it shows (`fkik.switch`). FK on a hand that
    rides a weapon releases it first (over the whole take - the link is the
    take's). `highlight` overrides the slider (a verify has none). One undo
    chunk; refusals before anything moves."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    if cmds.objExists(maya_rigs.node(rig, "MoCapConstraints")):
        return RETARGETING
    arm, text = fkik.limb(rig, side)
    if arm is None:
        return text
    span = fkik.span_for(_highlight() if highlight is None else highlight or None,
                         fkik.whole_take(arm))
    rides = following(rig, side)
    if rides and mode == fkik.IK:
        if fkik.mode_of(fkik.blend_values(arm)) == fkik.IK:
            return fkik.ALREADY % (fkik.ARM_LABEL.format(side), "IK (it follows %s)"
                                   % weapon_label(rides))
        return "%s follows %s - set it Free first" % (ROW_LABEL[side],
                                                      weapon_label(rides))
    text = fkik.refusal(arm, mode, span)
    if text:
        return text
    notes = []
    cmds.undoInfo(openChunk=True, chunkName="Connections: %s to %s"
                  % (fkik.ARM_LABEL.format(side), mode))
    try:
        if rides:
            sweep_orphans()
            _release(rig, side, _span(rides, [_control(rig, s) for s in SIDES]))
            notes.append("%s released from %s" % (ROW_LABEL[side], weapon_label(rides)))
        notes.append(fkik.switch(arm, mode, span))
        return "; ".join(notes)
    finally:
        cmds.undoInfo(closeChunk=True)


# ------------------------------------------------------------------ panel

def _status(text):
    """The card's status line - and the hub's message line too (2026-10-08):
    the skin hides the card's own line and shows what `hubstyle.tell` carries;
    the classic hub listens to nothing and keeps the line in the card."""
    if cmds.control(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
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


def header_text(rig, weapon, scheme, others="", arms=""):
    """The header line; `others` says where the other weapon is, `arms`
    which arm is mixed FK/IK. Pure."""
    if rig is None:
        return "no rig in the scene"
    tail = "; " + arms if arms else ""
    if not weapon:
        return "%s: no weapon - Weapons > Add first%s" % (maya_rigs.label(rig), tail)
    text = "%s: %s - %s" % (maya_rigs.label(rig), weapon.split("|")[-1],
                            describe(scheme))
    return text + ("; also " + others if others else "") + tail


def arms_text(modes):
    """«Arm_R mixed FK/IK» for each arm whose blend is keyed between the two
    ({side: mode or None}, an arm the rig lacks left out). Pure."""
    mixed = [ARM_ROW.format(side) for side in ("R", "L")
             if side in modes and modes[side] is None]
    return ", ".join(mixed) + " mixed FK/IK (keyed)" if mixed else ""


def fkik_box(side, mode):
    return FKIK_BOX.format(side, mode)


def where_text(label, scheme):
    """«Dagger 01 in the left hand» - the other weapon, for the header. Pure."""
    held = master(scheme)
    return "%s in the %s" % (label, SIDE_LABEL[held]) if held else \
        "%s in world" % label


def chooser_segment(index):
    """The chooser's segment `index` (0, 1)."""
    return "{0}_{1}".format(CHOOSER, index)


def _side_of(rig, bones, weapon):
    """The hand `weapon` hangs in, else the side whose bone it drives."""
    holder = weaponspace.holding_hand(weapon)
    for side in SIDES:
        if holder and _same(holder, bones[side][0]):
            return side
    return driven_side(rig, bones, weapon)


def _set_chooser(weapons, chosen, sides=()):
    """The chooser's two segments: the weapons' labels (`sides` names each
    one's hand, for two of one kind), an empty slot "-" and disabled, the
    chosen one selected. Its row is shown only while two weapons stand
    (2026-10-08, the compact hub: one weapon has nothing to choose)."""
    sides = list(sides) + [None] * (len(weapons) - len(sides))
    labels = labels_for([(weapon_label(weapon), side)
                         for weapon, side in zip(weapons[:2], sides)])
    for index in (0, 1):
        name = chooser_segment(index)
        if not cmds.iconTextRadioButton(name, exists=True):
            continue
        present = index < len(labels)
        cmds.iconTextRadioButton(name, edit=True,
                                 label=labels[index] if present else NO_SLOT,
                                 enable=present)
        if present and _same(weapons[index], chosen):
            cmds.iconTextRadioButton(name, edit=True, select=True)
    try:
        cmds.rowLayout(CHOOSER_ROW, edit=True, manage=len(labels) > 1)
    except (RuntimeError, TypeError, ValueError):
        pass


def _chooser_picked(index):
    """A chooser segment's onCommand: that weapon, by UUID, then re-read."""
    def go(*_args):
        rig, _refusal = maya_rigs.current_rig()
        weapons = weapons_of(rig) if rig else []
        if index < len(weapons):
            _PICKED["uuid"] = cmds.ls(weapons[index], uuid=True)[0]
            #  the pick holds while the selection stays as it is now
            _PICKED["selection"] = cmds.ls(selection=True, long=True) or []
        refresh()
    return go


def segment_name(row, choice):
    """The segment button of `choice` in `row`'s collection. Pure."""
    return "{0}_{1}".format(MENU[row], choice)


def menus():
    """What the three rows say now: each row's selected segment, the row's
    first choice when none is (a collection answers nothing before a pick).

    The three parents were dropdowns until 2026-09-28; since the skin they
    are segments (`iconTextRadioCollection` named MENU[row]) - the values
    and every pure function over them unchanged."""
    out = {}
    for row, choices in _ROWS:
        chosen = cmds.iconTextRadioCollection(MENU[row], query=True,
                                              select=True) or ""
        chosen = chosen.split("|")[-1]
        out[row] = next((c for c in choices if segment_name(row, c) == chosen),
                        choices[0])
    return out


def _set_menus(values):
    for row, value in values.items():
        name = segment_name(row, value)
        if cmds.iconTextRadioButton(name, exists=True):
            cmds.iconTextRadioButton(name, edit=True, select=True)


def refresh(*_args):
    """Re-read the scene into the header and the menus: after a press what
    IS is what the dropdowns show."""
    if not cmds.control(HEADER, exists=True):
        return ""
    rig, _refusal = maya_rigs.current_rig()
    bones = bones_of(rig) if rig else None
    weapons = weapons_of(rig, bones) if rig else []
    weapon = chosen_weapon(rig, bones, weapons) if rig else None
    scheme = read_scheme(rig, bones, weapon) if weapon else {"L": None, "R": None}
    _set_chooser(weapons, weapon, [_side_of(rig, bones, w) for w in weapons])
    _set_menus(menus_from_scheme(scheme))
    modes = _arm_modes(rig)
    _set_fkik(modes)
    others = "; ".join(where_text(weapon_label(w), read_scheme(rig, bones, w))
                       for w in weapons if not _same(w, weapon))
    text = header_text(rig, weapon, scheme, others, arms_text(modes))
    cmds.text(HEADER, edit=True, label=text)
    return text


def _arm_modes(rig):
    """{side: FK / IK / None (mixed)} for each arm the rig has."""
    modes = {}
    for side in SIDES:
        arm = fkik.limb(rig, side)[0] if rig else None
        if arm:
            modes[side] = fkik.mode_of(fkik.blend_values(arm))
    return modes


_FKIK_QUIET = {"on": False}


def _set_fkik(modes):
    """Light each arm's mode, neither when mixed or missing. Quiet: a box's
    own command must not fire from here (trap 116 - an edit ran a radio's
    onCommand in one hub build)."""
    _FKIK_QUIET["on"] = True
    try:
        for side in SIDES:
            for mode in fkik.MODES:
                name = fkik_box(side, mode)
                if cmds.iconTextCheckBox(name, exists=True):
                    cmds.iconTextCheckBox(name, edit=True,
                                          value=modes.get(side) == mode)
    finally:
        _FKIK_QUIET["on"] = False


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


def _press_bake_across(*_args):
    return _run(lambda: bake_across())


def _press_release_across(*_args):
    return _run(lambda: release_across())


def _press_fkik(side, mode):
    """Either press of a box - lighting it or not - switches the arm; the
    refresh after it lights what IS."""
    def go(*_args):
        if _FKIK_QUIET["on"]:
            return None
        return _run(lambda: switch_arm(side, mode))
    return go


def _press_connect(*_args):
    return _run(lambda: connect())


def _press_disconnect(*_args):
    return _run(lambda: disconnect())


def build_panel():
    """The scene's state line (the card's subtitle in the skin), Arm R / Arm L
    FK|IK on one row, the "Acts on" chooser (a row shown only while two
    weapons stand), three parent rows - label, segments, Apply - then Apply
    all with BakeAcross and Release on one row, the status. 2026-09-28 (the
    skin): segments in place of the dropdowns, Apply all the section's one
    primary action. 2026-10-08 (the compact hub): the arrangement above, the
    heights and gaps from `hubstyle`, the status told to the hub's one
    message line."""
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    #  the scene's state line is the card's subtitle in the skin (one line,
    #  elided); the classic hub keeps its two wrapped lines in the body
    hubstyle.mark(cmds.text(HEADER, label="", align="left",
                            wordWrap=hubstyle.pick(False, True),
                            height=hubstyle.pick(18, 36)), "subtitle")
    #  FK / IK per arm (2026-09-30): check boxes, not radios - a radio does
    #  not fire on the lit segment (a range inside a take of that mode), and
    #  a mixed take lights neither. A press switches at once. Both arms on
    #  one row, Arm R [FK|IK]  Arm L [FK|IK] (2026-10-08).
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3),
                                 (3, "left", 6), (4, "both", 3)])
    for side in SIDES[::-1]:
        cmds.text(label=ARM_ROW.format(side).replace("_", " "),
                  font="boldLabelFont")
        segments = cmds.rowLayout(numberOfColumns=2,
                                  columnAttach=[(1, "both", 1), (2, "both", 1)])
        hubstyle.mark(segments, "segments", layout=True)
        for mode in fkik.MODES:
            hubstyle.mark(cmds.iconTextCheckBox(
                fkik_box(side, mode), style="textOnly", label=mode,
                height=hubstyle.height("segment", 22),
                value=False,
                annotation="{0} to {1} - over the highlighted range, else the "
                           "whole take; the arm keeps what it shows".format(
                               ARM_ROW.format(side), mode),
                onCommand=_press_fkik(side, mode),
                offCommand=_press_fkik(side, mode)), "segment")
        cmds.setParent("..")
    cmds.setParent("..")
    #  Which of two weapons the rows act on (2026-09-29): the selection names
    #  one too. Two fixed segments - labels written by refresh, an empty slot
    #  disabled - rather than rows that come and go, which the skin's
    #  segment tracks would not follow. 2026-10-08: the whole row is managed
    #  off until two weapons stand (`_set_chooser`).
    cmds.rowLayout(CHOOSER_ROW, numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(hubstyle.pick(48, 64), 110),
                   columnAttach=[(1, "left", 0), (2, "both", 3)],
                   manage=False)
    cmds.text(label="Acts on", font="boldLabelFont")
    chooser = cmds.rowLayout(numberOfColumns=2,
                             columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(chooser, "segments", layout=True)
    cmds.iconTextRadioCollection(CHOOSER)
    for index in (0, 1):
        hubstyle.mark(cmds.iconTextRadioButton(
            chooser_segment(index), style="textOnly", label=NO_SLOT,
            height=hubstyle.height("segment", 22),
            select=index == 0, enable=index == 0,
            annotation="the weapon the rows below act on - or select it",
            onCommand=_chooser_picked(index)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")
    for row, choices in _ROWS:
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                       columnWidth3=(hubstyle.pick(48, 64), 110,
                                     hubstyle.tool_width(66)),
                       columnAlign3=("left", "left", "center"),
                       columnAttach=[(1, "left", 0), (2, "both", 4),
                                     (3, "right", 0)])
        cmds.text(label=ROW_LABEL[row], font="boldLabelFont")
        segments = cmds.rowLayout(numberOfColumns=len(choices),
                                  columnAttach=[(i + 1, "both", 1)
                                                for i in range(len(choices))])
        hubstyle.mark(segments, "segments", layout=True)
        cmds.iconTextRadioCollection(MENU[row])
        for index, choice in enumerate(choices):
            hubstyle.mark(cmds.iconTextRadioButton(
                segment_name(row, choice), style="textOnly",
                label=SEGMENT_LABEL.get(choice, choice),
                height=hubstyle.height("segment", 22),
                select=index == 0,
                annotation="the parent of {0}: {1}".format(ROW_LABEL[row],
                                                           choice),
                onCommand=_menu_changed(row)), "segment")
        cmds.setParent("..")
        hubstyle.mark(cmds.button(
            label=hubstyle.tool_label("Apply"),
            width=hubstyle.tool_width(66),
            height=hubstyle.height("small", 24),
            annotation="apply this row's parent only",
            command=_press_row(row)), "tool", "check")
        cmds.setParent("..")
    #  Apply all, BakeAcross and Release on one row (2026-10-08)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3),
                                 (3, "both", 3)])
    hubstyle.mark(cmds.button(
        label="Apply all", height=hubstyle.height("button", 32),
        backgroundColor=(0.45, 0.70, 0.50),
        annotation="bring the scene to all three parents",
        command=_press_apply_all), "primary", "check")
    hubstyle.mark(cmds.button(
        label="BakeAcross", height=hubstyle.height("button", 28),
        annotation="Select the objects, then the parent LAST: each object "
                   "rides a proxy locator inside the parent with its own "
                   "track baked onto it, and is hidden. Key the proxies.",
        command=_press_bake_across), "secondary", "link")
    hubstyle.mark(cmds.button(
        label="Release", height=hubstyle.height("button", 28),
        width=hubstyle.pick(78, 90),
        annotation="Selected objects (or their proxies) baked where the "
                   "proxies carried them, proxies removed, objects shown "
                   "again",
        command=_press_release_across), "secondary", "unlink")
    cmds.setParent("..")
    #  three lines (2026-09-30): an Apply plus the FK/IK switch it made first
    #  is longer than two - a wordWrap text keeps the height it is given
    #  (trap 67)
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=54), "status")
    cmds.setParent("..")
    try:
        refresh()
    except Exception:                                        # noqa: BLE001
        _status(traceback.format_exc().strip().splitlines()[-1])
    return column

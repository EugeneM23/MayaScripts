"""1P upper body (2026-10-21): a card's upper body only, carried relative to the chest.

The animator, two tabs open - an old take, and a new rig after Tools > 1P Setup: «Нужно
перенести анимацию с первой сцены во вторую ... через нашу библиотеку поз. Во второй сцене анимация
нижней части тела не должна пострадать ... настройку которая будет переносить позы и анимацию только
для верхней части тела в режиме засетапленого 1P»; then «копирование поз и анимаций верхней части
тела должно учитывать камеру и оружие».

What went wrong without it (measured on a rebuild of their tab): the card held the legs too, so a
Replace all keyed the lower body over the 1P Setup's lower layer (the feet 34-48 cm off), and it
held `spine_03`, which 1P Setup's chest knot drives - «1 not posed», the measure 92 deg off.

`restrict(data)` (pure) cuts a card down before any press reads it:

- the members are the card's chest (`CHEST`, the bone whose canonical or leaf name is
  `spine_03`) and EVERY bone of the card below it, selected at its save or not: spine_04/05,
  neck, head, clavicles, arms, hands, fingers, arm twists (a card holds every bone's world - one
  saved without spine_04/05 hung its arms on the target's own spine, 53 deg off the chest). The
  spine under the chest, the pelvis, the legs and the root are not members: the target keeps
  them - after 1P Setup the lower body. The chest takes the card's turn against the ROOT
  (`posemath`'s torso rule, below), standing on the target's own spine; in 1P it is written
  through `Chest_1P_ctrl` (`rigsolve`'s knot redirect - the first build left the chest out and
  the torso kept the take's turn: «разворот корпуса не верный»);
- every member above it takes its turn against the chest as posed - what the hands do in front
  of the 1P camera is what the card's hands did in front of its chest;
- the weapon bones come with the hands (`helpers.members_with`), keyed through the weapon that
  drives them, a weapon in the hand or one 1P Setup moved into the chest;
- the camera bones are members, `camera_root` ANCHORED on the chest (`anchors_for`, the
  Transfer's `anchors`): its turn and place relative to the chest, as 1P Setup hangs the camera
  control under `Chest_1P_ctrl`. Keyed through the Camera Setup control when there is one
  (`helpers.Writer`).
- no pelvis member, so no travel and no Main.

The chest's TURN is the card's against the character's root - `posemath`'s torso rule, 2026-10-21
(«... даже на риге с анимацией в которой есть провороты она должна остаться стабилизированой»):
measured on a 1P card whose chest stood still against its root onto a combo whose torso twists,
the chest had come 78 deg off the card's and turned 112.7 deg on the target's spine_02. The rule is
the card's members', so a card saved with only its upper body selected lands the same with the
option off; the option cuts a FULL card down to that.

The window's check box «1P upper body» (`window.UPPER_VAR`) applies it to every press of a
character card: Apply, Blend, a drop, the skill bar. An objects card is left alone.
"""

CHEST = "spine_03"
CAMERA = ("camera_root", "camera_bone")
# a card's other helpers never become members on their own (the weapon bones come with the hands,
# `helpers.members_with`; ik_* and the rest are export helpers)
HELPER_PREFIXES = ("weapon_", "ik_", "interaction", "center_of_mass")
# the bones that ride the chest in an upper-body card (`anchors_for`)
ON_CHEST = ("camera_root",)
# the torso, as `posemath.is_torso` reads it (restated: this module is pure)
TORSO = ("pelvis",)
TORSO_PREFIX = "spine_"
NOTE = "1P upper body: %d bones from %s up (the spine below, the legs and the pelvis kept)"
NO_CHEST = "1P upper body: the card has no %s - nothing to carry the upper body on" % CHEST
NO_UPPER = "1P upper body: the card holds nothing above %s" % CHEST


def _bare(name):
    return (name or "").split(":")[-1].split("|")[-1]


def chest_of(bones):
    """The card's chest leaf: the bone whose canonical name is `CHEST`, else whose leaf is."""
    for leaf, bone in (bones or {}).items():
        if (bone or {}).get("canonical") == CHEST:
            return leaf
    for leaf in bones or {}:
        if _bare(leaf) == CHEST:
            return leaf
    return None


def below(bones, top):
    """The leaves strictly below `top` in the card's hierarchy (pure)."""
    out = set()
    for leaf in bones or {}:
        seen = set()
        parent = (bones[leaf] or {}).get("parent")
        while parent and parent in bones and parent not in seen:
            if parent == top:
                out.add(leaf)
                break
            seen.add(parent)
            parent = (bones[parent] or {}).get("parent")
    return out


def restrict(data):
    """(card, note) - a copy of the character card `data` cut to its upper body (the module's
    rule), its `anchors` set; (None, why) when it cannot be. An objects card, or none, comes back
    as it is with no note."""
    if not data or data.get("kind") == "objects":
        return data, ""
    bones = data.get("bones") or {}
    chest = chest_of(bones)
    if chest is None:
        return None, NO_CHEST
    upper = below(bones, chest)
    members = list(data.get("members") or ())
    # the chest and EVERY bone of the card above it (2026-10-21: «разворот корпуса не верный»):
    # a card saved with spine_04/05 unselected hung the clavicles on the target's own spine, and
    # the hands stood 31 cm / 53 deg off the chest - so off the 1P camera. A card holds every
    # bone's world, its members only say what was selected. In 1P the solve writes the chest
    # through Chest_1P_ctrl
    if not any(m in upper or m == chest for m in members):
        return None, NO_UPPER
    kept = [m for m in members if (m in upper or m == chest) and _bare(m) not in CAMERA]
    kept += [leaf for leaf in bones if (leaf in upper or leaf == chest) and leaf not in kept
             and _bare(leaf) not in CAMERA and not _bare(leaf).startswith(HELPER_PREFIXES)]
    for leaf in bones:
        if _bare(leaf) in CAMERA and leaf not in kept:
            kept.append(leaf)
    out = dict(data)
    out.pop("anchors", None)               # derived at every press (`anchors_for`)
    out["members"] = kept
    out["upper_1p"] = True
    return out, NOTE % (len([m for m in kept if _bare(m) not in CAMERA]), chest)


def _torso(bones, leaf):
    name = _bare((bones.get(leaf) or {}).get("canonical") or leaf)
    return name in TORSO or name.startswith(TORSO_PREFIX)


def anchors_for(bones, members):
    """{camera_root leaf: the chest leaf} (pure): the camera rides the chest - its turn and place
    against it, `posemath.Transfer`'s `anchors` - whenever the members POSE the chest but not the
    whole torso under it (an upper-body card, cut by the option or saved so in 1P; a card with a
    gap in its spine): the chest then stands on the target's own spine (`posemath`'s torso rule),
    as 1P Setup hangs the camera control under `Chest_1P_ctrl`. {} else - a whole torso keeps its
    camera on the root, as it was."""
    bones = bones or {}
    have = set(members or ())
    chest = chest_of(bones)
    if chest is None or chest not in have:
        return {}
    node, seen, gap = (bones[chest] or {}).get("parent"), set(), False
    while node in bones and node not in seen:
        seen.add(node)
        if _torso(bones, node) and node not in have:
            gap = True
            break
        node = (bones[node] or {}).get("parent")
    if not gap:
        return {}
    return dict((leaf, chest) for leaf in bones if _bare(leaf) in ON_CHEST)


def target_anchors(anchors, pairs):
    """{target leaf: target anchor leaf} of a card's `anchors` (source leaves) through `pairs`
    ({target leaf: source leaf}) - for `posemath.Transfer`."""
    if not anchors:
        return {}
    back = dict((s, t) for t, s in (pairs or {}).items())
    out = {}
    for leaf, onto in anchors.items():
        if leaf in back and onto in back:
            out[back[leaf]] = back[onto]
    return out

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

- the members are the card's bones strictly BELOW its chest (`CHEST`, the bone whose canonical or
  leaf name is `spine_03`): spine_04/05, neck, head, clavicles, arms, hands, fingers, arm twists.
  The chest itself, the spine under it, the pelvis, the legs and the root are not members: the
  target keeps them - in 1P the chest is the stabilized `Chest_1P_ctrl` the camera rides;
- so every member's turn is taken against the target's chest as it stands (`posemath.Transfer`:
  a member relative to its nearest paired ancestor, the chest a non-member that stays) - what the
  hands do in front of the 1P camera is what the card's hands did in front of its chest;
- the weapon bones come with the hands (`helpers.members_with`), keyed through the weapon that
  drives them, a weapon in the hand or one 1P Setup moved into the chest;
- the camera bones are members, `camera_root` ANCHORED on the chest (`ANCHORS`, the Transfer's
  `anchors`): its turn and place relative to the chest, as 1P Setup hangs the camera control under
  `Chest_1P_ctrl`. Keyed through the Camera Setup control when there is one (`helpers.Writer`).
- no pelvis member, so no travel and no Main.

The window's check box «1P upper body» (`window.UPPER_VAR`) applies it to every press of a
character card: Apply, Blend, a drop, the skill bar. An objects card is left alone.
"""

CHEST = "spine_03"
CAMERA = ("camera_root", "camera_bone")
ANCHORS = {"camera_root": CHEST}
NOTE = "1P upper body: %d of %d bones above %s (the chest, the legs and the pelvis kept)"
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
    kept = [m for m in members if m in upper and _bare(m) not in CAMERA]
    if not kept:
        return None, NO_UPPER
    anchors = {}
    for leaf in bones:
        bare = _bare(leaf)
        if bare in CAMERA and leaf not in kept:
            kept.append(leaf)
        if bare in ANCHORS:
            anchors[leaf] = chest
    out = dict(data)
    out["members"] = kept
    out["anchors"] = anchors
    out["upper_1p"] = True
    return out, NOTE % (len([m for m in kept if _bare(m) not in CAMERA]), len(members), chest)


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

"""1P lower body (2026-10-22): a card's lower body only, the target's chest kept stable.

The animator: «Так как мы обрабатываем анимацию upper body в нашей библеотеке поз давай точно так
же сделаем обработку и lower body и галочку для загрузки анимации только на нижнюю часть». Asked
what the target's upper body does meanwhile, they chose KEPT STABLE (over riding the new hips).

`restrict(data)` (pure) cuts a character card down before any press reads it - the mirror of
`upper.restrict`:

- the members are every bone of the card that is NOT its chest (`upper.chest_of`: canonical
  `spine_03`) or below it in the card's hierarchy, selected at its save or not: the root, the
  pelvis, spine_01/02, the legs and their twists. Never a helper (`weapon_*`, `ik_*`, ...) and
  never the camera bones: no hand comes, and no whole body;
- `keep`: [the chest leaf] - the TARGET's chest is kept stable (`posemath.Transfer`'s `kept`):
  its turn against the character's root as it stood, its place riding the end of the new spine.
  Everything above it follows it as it did - the neck, the head, the clavicles and FK arms; in
  1P the IK arms (their Extra groups on `Chest_1P_ctrl`), the camera control and a weapon in the
  chest. In 3P the press keys `FKSpine3_M`; in 1P `Chest_1P_ctrl` (rigsolve's knot redirect):
  its place follows the spine, its turn stays what it was, turning only as far as Main does -
  1P Setup's own split, the knot's turn on Upper and its place on Lower;
- the pelvis is a member, so an animation card carries its travel onto Main as a whole card does
  (In place keeps the character where it stands).

The window's check box «1P lower» (`window.LOWER_VAR`) applies it to every press of a character
card: Apply, Blend, a drop onto a character, Select objects, the skill bar. It and «1P upper»
exclude each other. An objects card is left alone.

Spec: docs/superpowers/specs/2026-10-22-pose-library-lower-body-design.md
"""

from maya_poselib import upper

NOTE = "1P lower body: %d bones under %s (%s kept stable, the arms and the head ride it)"
NO_CHEST = "1P lower body: the card has no %s - nothing marks where its lower body ends" % \
    upper.CHEST
NO_LOWER = "1P lower body: the card holds nothing under %s" % upper.CHEST


def _bare(name):
    return upper._bare(name)


def _lower(leaf):
    """Can the bone be a lower-body member at all - no helper, no camera bone?"""
    name = _bare(leaf)
    return name not in upper.CAMERA and not name.startswith(upper.HELPER_PREFIXES)


def restrict(data):
    """(card, note) - a copy of the character card `data` cut to its lower body (the module's
    rule), its `keep` set; (None, why) when it cannot be. An objects card, or none, comes back as
    it is with no note."""
    if not data or data.get("kind") == "objects":
        return data, ""
    bones = data.get("bones") or {}
    chest = upper.chest_of(bones)
    if chest is None:
        return None, NO_CHEST
    above = upper.below(bones, chest) | {chest}
    members = list(data.get("members") or ())
    taken = [m for m in members if m in bones and m not in above and _lower(m)]
    if not taken:
        return None, NO_LOWER
    taken += [leaf for leaf in bones if leaf not in above and leaf not in taken and _lower(leaf)]
    out = dict(data)
    out.pop("anchors", None)
    out["members"] = taken
    out["keep"] = [chest]
    out["lower_1p"] = True
    return out, NOTE % (len(taken), _bare(chest), _bare(chest))


def target_keep(keep, pairs, target):
    """The TARGET leaves a card's `keep` (its leaves) names, through `pairs` ({target leaf:
    source leaf}); a kept card bone the target does not pair is the target's own chest
    (`upper.chest_of`). [] for no `keep`. Pure."""
    if not keep:
        return []
    wanted = set(keep)
    out = [leaf for leaf, source in (pairs or {}).items() if source in wanted]
    if not out:
        own = upper.chest_of(target or {})
        if own is not None:
            out = [own]
    return out

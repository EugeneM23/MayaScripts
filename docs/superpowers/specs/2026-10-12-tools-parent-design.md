# Tools: OverRig's "parent" tab, native (2026-10-12)

The animator: «Теперь давай реализуем весь функционал из вкладки parent». Asked, and answered (all
three the recommendation):

- inside / world / swap **refuse an AdvancedSkeleton rig's controls and every skeleton bone** (moving
  them in the DAG breaks the rig or the export) and point to Across; a bone or a control may be the
  PARENT (a prop into a hand);
- **Across is a knot inside the parent** - attach, a range, Bake / Remove like every knot, the
  object not hidden; Connections' BakeAcross / Release stay as they are;
- **multiple across is a block in the card**, not a window.

## What OverRig does (read off `overrig/base_OverRig_scripts.mel`, v10.2)

| Button | proc | what it does |
|---|---|---|
| inside | `apply_Parent_in` → `…32e5cf02…` | children then the parent last: a temp locator per child follows it (`parentConstraint -mo`), baked; the child re-parented under the last selected (`parent`); the child constrained to its locator and baked; locators deleted; `filterCurve` |
| world | `apply_Parent_out` → `…3be196f3…` | the same with `parent -w` |
| swap | `apply_Swap_parent` → `…d6efb621…` | every selected baked onto a locator; all to world; the others under the LAST selected; the last under the former parent of the one before it; all baked back |
| across | `apply_parent_anim_across` → `…d4a5d701…` | per child a locator `par_in_<child>` parented under the last selected, baked from the child (its keys in the parent's space), the child constrained to it, `attach` keyed for a highlight - a knot inside the parent |
| multiple across | window `…b5eac6c5…` → `…9f70c994…` | remembered Targets and Objects lists (same length), swap, checkboxes rotation / translation; pairs object i → target i |
| 0 / 1 | `setKey_on_attach_attr(v)` | keys `attach` = v on the selected (unlocking it): at the highlight's two ends, else the selected keys' range, else the current frame; flat |

inside / world / swap also cut the children's SCALE keys and hide scale and visibility from the
channel box (`…25dd166f…`, `…c89bf830…`) and bake only a highlight when there is one - leaving the
object's curves outside it in the old space. Neither is copied.

## The card (Tools)

A third subsection and a fourth, between Double knot and the common rows:

```
Parent ────────────────────────────────────
[ Inside ] [ World ] [ Swap ] [ Across ]
Multiple across ───────────────────────────
[ Objects 3 ] [ Targets 3 ] [ ⇄ ]
[ Rotate ] [ Translate ] [ Across ]

Rotate order [ Object | XYZ | XZY ]
Attach       [ 0 ] [ 1 ]
[ Bake ] [ Remove ]
```

Every button orange (the card's rule since this morning), every row of buttons `fill` (stretched
over the card). Rotate / Translate are chips (remembered, `skeldarAcrossRotate` /
`skeldarAcrossTranslate`, both on). Objects / Targets remember the selection (by UUID, for the Maya
session: they live on `sys`, trap 111) and show their counts; ⇄ swaps the two lists. Attach is a
plain label and a `fill` row of 0 and 1. Hotkey rows: `tools.inside`, `tools.world`, `tools.swap`,
`tools.across`, `tools.attach_0`, `tools.attach_1` (no keys bound).

## Inside, World, Swap - re-parenting that keeps the motion

`maya_tools/reparent.py`. For every node that moves:

1. **Refusals first, nothing changes** (by name): fewer than two selected (Inside, Swap) or none
   (World); a skeleton bone; a control of an AdvancedSkeleton rig (a node in the rig's namespace, or
   a member of its ControlSet / under its group for a rig in the root namespace); the plugin's own
   nodes (any attribute with our prefixes: knots, pivots, weapons, armor, spaces, CoM, labels); an
   object riding a knot; a locked translate or rotate channel; a channel driven by anything but a
   time curve; a destination parent scaled unevenly, sheared or mirrored; scale keyed while the old
   and the new parent's world scale differ; a cycle (the parent inside a child); already there
   (Inside: the parent already is its parent; World: already at world level).
2. **The span is the whole take** - playback ∪ animation range ∪ the keys of the moving nodes, their
   ancestors before and after the move - never a highlight: a re-parent changes the object's space
   on every frame, so curves left outside a range would play in the wrong space.
3. A temporary locator per node takes its world track (`parentConstraint` with no offset - its
   origin on the node's rotate pivot, its axes the node's), baked on every frame.
4. The DAG move: Inside - the children under the last selected; World - to world level; Swap - all
   to world, the others under the last selected, the last under the former parent of the one before
   it (world when it had none).
5. Each node constrained to its locator with no offset (offsets captured after a move would read
   the old curves in the new space), its translate and rotate baked on every frame (into its own
   curves, through Maya's pairBlend when keyed), the constraint deleted, only the baked rotate keys
   made continuous (`continuous_eulers`), the locators deleted.

Scale is left alone: `cmds.parent` keeps the current frame's world scale in the unkeyed channels;
a keyed scale is refused when the parents' scales differ (above). One undo chunk; the moved nodes
selected after. On every integer frame the world track is unchanged; between frames the dense keys
interpolate their own way (the same as OverRig's).

## Across - a knot inside the parent

A knot kind `across` (`<leaf>_across`, teal): the locator is created as a DAG child of the target
(the last selected), baked from the object's world track (`parentConstraint` with no offset - its
keys land in the target's space), and the object follows it exactly as a knot's object does:
pairBlend, `attach` (keyed 0/1/1/0 for a highlight), one constraint `-mo` skipping locked channels,
`skeldarKnotOf`. Bake, Remove, the rotate order, the subtitle's count treat it as any knot. Because
it does not live in a Knots group, every across knot is also a member of an objectSet marked
`skeldarKnotRegistry` (`SkeldarAcrossKnots`; Maya deletes the set with its last member, trap 18) -
how `knots()` finds them without walking the scene.

Refusals as a knot's, plus: the object is the target, or the target lies inside the object (a
cycle); the target scaled unevenly, sheared or mirrored. A target may be anything - a rig control,
a bone, a prop (that is the point: a prop riding a hand).

**Multiple across** pairs Objects[i] with Targets[i]: refused when the lists are empty or of
different lengths, or when both Rotate and Translate are off. Rotate off: the rotate channels are
skipped by the follow constraint (and not keyed) - the object keeps its own rotation; Translate off
likewise.

## Attach 0 / 1

`knots.set_attach(value, selection)`: the selected knots (any node of one, or an object riding one
- every knot it rides) get `attach` keyed `value` with flat tangents: at the highlight's two ends
(`a` and `b - 1`), else at the selected graph keys' first and last time, else at the current
frame. One undo; refused with nothing of ours selected.

## Modules and proof

- `knotplan.py` (pure): the `across` kind, `swap_plan`, `cycle`, the refusal and message lines, the
  list labels, `attach_times`.
- `knots.py`: `create_across(pairs, ...)`, the registry, `set_attach`; `knots()` adds the registry.
- `reparent.py` (new, `cmds`): inside / to_world / swap and their refusals.
- `panel.py`: the two subsections, the chips, the lists, the Attach row.
- `verify_parent.py` (mayapy standalone): Inside / World / Swap keep every frame's world track
  (props under animated parents, a rotate pivot off the origin, zxy), the hierarchy as asked, one
  undo; every refusal changes nothing (a Manny control, a bone, a locked channel, a knot rider, a
  cycle, an uneven parent); Across: nothing moves, the knot under the target, the object follows the
  target, a knot edit moves it in the target's space, Bake / Remove, a range; Multiple across with
  Rotate off keeps the object's own rotation; Attach 0 / 1 at a frame, a highlight, selected keys;
  an across knot under a Manny control goes with Delete character.

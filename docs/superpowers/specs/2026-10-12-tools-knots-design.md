# Tools: OverRig's Knots and Double knot, native (2026-10-12)

The animator: «В скрипте over rig (который есть в моей мае) есть несколько фичей которые я бы хотел
реализовать в нашем плагине. 1 то что находится во вкладке knots 2 что что во вкладке double knots.
Давай заведем раздел тул и реализуем такие же инструменты». Asked, and answered:

- Knot Offset finishes with a **two-step button** (Knot Offset, then Finish offset), not OverRig's
  deselect-to-finish scriptJob;
- knots come off through **two buttons, Bake and Remove**;
- «делай все до конца» - the build goes all the way, the design as proposed.

## What OverRig does (read off `overrig/base_OverRig_scripts.mel`, v10.2)

The procs are obfuscated (`BOVER_10_2_<md5>`); each was followed to its helpers.

| Button | proc | what it builds |
|---|---|---|
| Knot | `apply_parentConstrAnim` → `…43aae6ab…` | a locator `Parent_<obj>` on the object; `parentConstraint -mo obj→loc`, bake, delete; `parentConstraint -mo loc→obj`; an `attach` attribute driving the constraint weight and the pairBlend |
| Knot Offset | `apply_PivotParentAnimation` → `…e2f38e4d…` | a locator `Pivot_for_<obj>`, Move tool, a run-once `scriptJob -cf SomethingSelected`: on DESELECT the locator follows the object (`-mo`), is baked, and drives it |
| Knot Orient | `apply_Knot_Orient_Point` → `…85101271…` | a locator `<obj>_or`: `pointConstraint obj→loc` kept (it rides the object), the orientation baked, then an orient-only `parentConstraint -mo -st x y z loc→obj` |
| Double knot local | `apply_DoubleUzelLocal` → `…cf7d60c1…` | a group `b_DUL_<obj>` baked with the object's whole world track, a locator `rot_<obj>` under it at zero driving the object |
| Double knot world | `apply_DoubleUzelGlobal` → `…5ef36e91…` | a locator `move_<obj>` with no rotation carrying the position, `rotate_<obj>` under it carrying the rotation, driving the object |

Shared by all: the source's unconnected t/r channels are KEYED first (`…bb580589…`) so Maya splices a
pairBlend whose input 1 keeps the object's own animation; locked channels are skipped (`-st`/`-sr`);
a time-slider highlight of more than one frame bakes `[start-1, end]` and keys `attach` 0/1/1/0 at
`start-1, start, end-1, end` (Knot, Offset, Orient - not the double knots); otherwise the bake runs
over `playbackOptions -ast/-aet`; knots go into `OverRig_knots`, sources into
`OverRig_rig_objects`; the knot's rotate order is xyz / xzy / the object's (a radio in its
"change Rotation Order" frame). Taking knots off is a separate bake of the sources plus deleting
the knots by hand (or the scene-wide `barn_fast_bake_source_obj_and_delete_knots`, the procedure
`maya_hotkeys` refuses to bind).

## Measured before designing (mayapy, a keyed cube under a parent constraint)

- Constraining a keyed object makes Maya splice `pairBlend1` (input 1 the object's curves) and add
  `blendParent1` on the object driving `pairBlend.weight`.
- **Deleting that constraint deletes the pairBlend and `blendParent1` and reconnects the original
  curves** - the object plays its own animation again, exactly. So Remove is a delete.
- **`bakeResults(..., preserveOutsideKeys=True)` on a pairBlended channel bakes INTO input 1's
  curve** (dense keys over the range, the keys outside kept, the blend interpolating into them)
  and leaves the pairBlend and the constraint standing. So Bake is a bake, then the constraint's
  delete (which reconnects the now-baked curve).

## Native, not a wrapper

The five tools are rewritten in `cmds` (no `mel.eval`, nothing of OverRig loaded) - the plugin's
direction since 2026-09-07. Ours are found by our own attributes, so Bake and Remove never touch a
knot the animator made with OverRig itself; each press is one undo; a colleague's Maya needs no
OverRig; every behaviour is proven in mayapy standalone. OverRig's MEL is not changed or called.

## The card

A new hub section **Tools** (key `tools`), last in the **Animation** group (after Pose Library),
Tabler's `tool` icon (the wrench). Hotkey rows: `window.tools` and `tools.knot`,
`tools.knot_offset`, `tools.knot_orient`, `tools.double_local`, `tools.double_world`,
`tools.bake`, `tools.remove` - no default keys. Top down:

- the subtitle `skeldarToolsSubtitle`: «3 knots in the scene · 1 pivot waiting» / «no knots»;
- heading **Knots** (`skeldarToolsKnotsHeading`); one row: **Knot** (primary, the card's one
  orange), **Knot Offset** (reads **Finish offset** while a pivot is waiting), **Knot Orient**;
- heading **Double knot** (`skeldarToolsDoubleHeading`); one row: **Local**, **World**;
- **Rotate order** `[Object | XYZ | XZY]` (`skeldarToolsOrder_object/_xyz/_xzy`, remembered in
  `skeldarKnotRotateOrder`, default **Object**: the knot takes its object's rotate order, so its
  curves behave like the object's);
- one row: **Bake** (secondary), **Remove** (danger);
- the status line `skeldarToolsStatus`.

Tooltips carry OverRig's own explanations. A SelectionChanged job owned by the status line
refreshes the subtitle and the offset button's label; the job is per card (the hub and each popup
copy, `maya_hubcopy`). The presses are module functions reading the optionVar, so the hotkey rows
work with the card closed (`maya_hotkeys._report` shows their line).

## The five tools - one set of rules

Every selected transform gets its own knot (Knot Offset: one object). For each:

1. **Refusals first, for every selected object, before anything changes** (by name):
   nothing selected; an object that already rides a knot of ours («select its knot to knot it
   again - or Bake / Remove first»; a knot itself CAN be knotted); a waiting pivot or its space;
   no free channel (every translate and rotate locked - for Knot Orient every rotate); a free
   channel driven by anything but a time animCurve - a constraint, a pairBlend, an expression, a
   driven key, an animation layer's blend node (layers: stated as not supported yet).
2. **The span**: a highlight of more than one frame (`overrig.slider_selection`, `[a, b)`) gives
   `[a-1, b]` and `attach` keyed 0/1/1/0 at `a-1, a, b-1, b` (flat), else the whole take -
   playback ∪ the object's own keys - and `attach` 1, unkeyed. **All five** take a range (OverRig's
   double knots did not); `attach` stays keyable, so the animator can blend any knot in and out.
3. **The object's free unconnected t/r channels are keyed** at their current values (the
   channel=value list kept on the knot, `skeldarKnotKeyed`) - Maya's pairBlend then holds the
   object's own animation as input 1.
4. **The knot is built and baked** (every frame of the span, `bakeResults -simulation`, the
   rotate curves euler-filtered (trap 108), a still channel collapsed to a plain value), its
   temporary constraints deleted.
5. **The object follows the knot** through one constraint `-mo` skipping its locked channels,
   marked `skeldarKnotOf` = the knot's UUID; `attach` drives the constraint weight and the
   pairBlend weight (`blendParentN` / `blendOrientN`); the pairBlend interpolates rotations as
   quaternions.
6. **Nothing moves**: the object plays exactly what it played before the press (gated 0.0).

Where the knot stands: on the object's world rotate pivot, in the object's world orientation at the
current frame (a temporary no-offset `parentConstraint` snap), with the chosen rotate order.

- **Knot** `<leaf>_knot`: a world locator carrying the object's world track; the object follows
  it (`parentConstraint`).
- **Knot Offset**, two presses:
  - **Knot Offset**: a space `<leaf>_pivotSpace` (marked `skeldarKnotPendingSpace`) rides the
    object (`parentConstraint`, no offset); in it a locator `<leaf>_pivot` (marked
    `skeldarKnotPending` = the object's UUID, red) at zero, selected, the Move tool on. **It rides
    the object while you place it**, so scrubbing keeps it where you put it on the object (OverRig's
    stood still in world). The span (the highlight at THIS press) and the rotate order are kept on
    it. The button reads **Finish offset**.
  - **Finish offset**: the pivot of the selection (the pivot, its space or its object selected),
    else the only waiting pivot, else a refusal naming them. A knot `<leaf>_knotOffset` baked from
    the pivot's world track (its place and axes on the object), the space and pivot deleted, the
    object following the knot. Rotating the knot turns the object about that point.
  - **Remove** on a waiting pivot deletes it; a second Knot Offset on an object with a pivot
    waiting refuses.
- **Knot Orient** `<leaf>_knotOrient`: rides the object's position (a `pointConstraint` kept,
  translate locked), carries the object's world rotation; the object follows it by orientation
  only (`orientConstraint`) and keeps its own translation animation.
- **Double knot Local**: `<leaf>_dknotBase` (outer, the top) carries the object's whole world
  track; `<leaf>_dknot` (inner) under it at zero drives the object (`parentConstraint`). A key on
  the inner is an offset in the animated object's own axes. The inner is selected after the press.
- **Double knot World**: `<leaf>_dknotMove` (outer, the top) has no rotation (world axes) and
  carries the object's world position; `<leaf>_dknotRotate` (inner) under it at zero translate
  carries the world rotation and drives the object (`parentConstraint`). Rotating the outer turns
  the whole animation about the object's pivot in WORLD axes; moving it shifts it along world axes.
  The outer is selected after the press.

**Identity**: the knot's top node carries `skeldarKnot` (the kind: `knot`, `offset`, `orient`,
`double_local`, `double_world`), `skeldarKnotSource` (the object's UUID), `skeldarKnotSpan`
(`"start end ranged"`), `skeldarKnotKeyed` and `attach`; the object's constraint `skeldarKnotOf`.
Lookups walk locators (`ls(type="locator")`) and ask `attributeQuery` - never `ls("*.attr")`
(trap 70). Names are for the outliner only; Maya uniquifies them.

**Look**: locators sized from the object (a third of its world bounding-box diagonal, at least
3 cm; a joint without a shape from its radius), the double knots' outer 1.6 times the inner;
coloured by kind through the shape's RGB override - Knot green, Offset orange, Orient blue, double
Local violet, double World yellow, a waiting pivot red.

**Where knots live**: a group `Knots` (marked `skeldarKnotGroup`, its transform locked at
identity) inside the object's **character group** (`chargroup.group_of`), else a world-level
`SkeldarKnots` for a prop or a legacy character. Removed when its last knot goes. **Delete
character takes its knots** (they lie inside its group; `deletion` reads our markers as ours), and
its objects with them.

## Bake and Remove

Both take the selection: a knot (any node of it), a waiting pivot (Remove only), or an object
riding a knot (all its knots). Nothing of ours selected: a refusal, never "every knot in the scene"
(OverRig's scene-wide bake is exactly what `maya_hotkeys` will not bind). One undo per press.

- **Bake**: the object's constrained channels baked over the knot's span ∪ the knot's own key range
  (the animator may have keyed past it), `preserveOutsideKeys`, every frame, then the constraint
  deleted (Maya reconnects the now-baked curve), the knot deleted, the rotate curves
  euler-filtered. Outside a ranged knot the object keeps its own keys; a blend frame bakes what it
  showed. A knot driving another selected knot's object is baked first (a knot on a knot collapses
  inward). The objects are selected after.
- **Remove**: the constraint deleted (the object plays its own curves again), the curves of the
  channels we keyed at creation cut and their values written back (trap 58), the knot deleted: the
  object's animation is exactly what it was before the knot (keys, values, tangents).

## Modules

- `SkeldarAnim/maya_tools/__init__.py` - the package (Tools may grow).
- `maya_tools/knotplan.py` - stdlib, pure: the kinds table (suffixes, colours), `span_for`,
  `attach_keys`, `channel_plan` (free / skipped / refusal from locks and inputs), `knot_size`,
  `rotate_order_index`, `bake_order`, the messages, the subtitle.
- `maya_tools/knots.py` - `cmds` + OpenMaya: create, offset begin/finish, bake, remove, find.
- `maya_tools/panel.py` - the card, the presses, the refresh job.
- `maya_hub.SECTIONS`, `maya_hubicons` (+ `tool`, `rotate`, `focus-2`, `stack-2`),
  `maya_hotkeys` rows, `install.payload()` row, `deletion` (knot groups as parts).

## Proof

- Unit tests: `knotplan` whole (pure), the panel on fake `cmds`, the hub row, the hotkey rows, the
  payload row, the icons.
- `docs/superpowers/plans/verify_knots.py`, mayapy standalone: a keyed prop under an animated
  parent (with a rotate pivot off its origin and a locked channel) and a Manny rig control;
  per tool: nothing moves at creation (0.0 over every frame); the knot stands on the pivot; a knot
  edit moves the object as the tool promises (Knot +10 cm moves it 10; Offset turned 90° keeps the
  chosen point fixed; Orient turned leaves the translation track alone; double Local's inner turned
  about its X turns the object about its own animated X; double World's outer turned 90° about Y
  turns the path about the pivot in world axes); `attach` 0 gives the original; a ranged knot
  leaves everything outside the range at 0.0; Bake keeps the edited motion with no constraint,
  pairBlend or knot left and the outside keys kept; Remove restores every curve exactly; one undo
  per press; refusals change nothing; a knot on a knot bakes inward; Delete character takes the
  knots.
- The card in a live Maya is the animator's check (the GUI verify written, not run - their rule).

# UE Bridge: several animations at once, a line of rigs

2026-10-01. The animator: «Давай добавим возможность выделить массив анимаций и выполнить действие над
массивом анимаций как по кнопке так и перетягивание в сцену рукой. Если мы выбрали массив анимаций и нажали
import to rig или перетянули в уже созданный риг на сцене то пускай загружается только первая анимация это
логично потому что в этом случае мы работаем с конкретным ригом. Если мы нажали add new rig или перетянули в
пустое место на сцене то давай мы создадим все наши анимации в линию с некоторым шагом что бы они не
пересекались. В случае с кнопкой пусть анимации будут выставляться симметрично относительно нуля сцены а в
случае с перетягиванием пускай относительно точки в которую мы указали.»

Asked, and answered (all three the recommended option):

- **the step**: 2.5 m, **widened** where a clip's root travels sideways — the gap to a neighbour grows by
  exactly how far each of the two wanders toward the other, so no two root paths cross, and standing clips
  stand evenly;
- **a drag's line runs across the screen**: along the camera's right on the floor, through the point, in
  list order left to right; the button's along world X about the origin;
- **Skeleton mode with several**: all of them, each its own namespaced skeleton, in the same line about the
  origin (moved by a wrapper group, the keys untouched).

## What the animator does

The list takes a multiple selection (`allowMultiSelection`): click, Ctrl+click, Shift+click as anywhere.
"The first" is the topmost picked row in list order.

| how | Rig | New rig | Skeleton |
|---|---|---|---|
| Import button, 1 picked | as before | as before | as before |
| Import button, N picked | the first only, onto the rig (as before); the status says the rest were left | N new rigs in a line along world X, centred on the origin | N skeletons in that line |
| drag, 1 carried | onto the rig under the cursor (as before) | a new rig on the floor point (as before) | — |
| drag, N carried | onto the rig under the cursor: the first only | N new rigs in a line across the screen, centred on the floor point | — |

- **What a drag carries**: the pressed row with every other picked row when the pressed row was picked
  before the press and no Ctrl/Shift was held (Explorer's rule); otherwise the selection the press left,
  when it holds the pressed row; otherwise the pressed row alone. The list's selection is put back to what
  is carried after the drag starts: Qt's ExtendedSelection collapses a selection to the clicked row on the
  RELEASE of a press on a picked row, and the drag ends the click for the list with a synthetic release.
- **The ghost** names it: «A_Jump · retarget onto Manny_Rig1 · first of 3», «3 animations · 3 new Manny
  [rig] in a line · floor (120, -36)». One animation reads as before.
- **One animation behaves exactly as before**, both roads: the Import button with New rig leaves the rig
  where the clip stands, a floor drop stands it on the point. The line rule is for two or more.
- A floor drop that saw no floor (looking above the horizon) centres its line on the origin, still across
  the screen.
- **Export to uasset** with several picked refuses: «pick one animation to overwrite - 3 are picked».
- A double click acts on its own row (its first click has made it the selection).

## The line

`maya_uebridge/lineup.py`, stdlib only, pure:

- `side_extent(track, axis)` — a clip's root positions over its frames, relative to its first, along the
  line's axis: `(lo, hi)`, `lo ≤ 0 ≤ hi`.
- `offsets(extents, step)` — slot `i + 1` stands `step + hi_i − lo_{i+1}` past slot `i`; the whole line is
  then shifted so the first and last slots are equidistant from the centre.
- `floor_axis(direction)` — a horizontal unit vector from a 3-vector (the camera's right), world X when it
  has no horizontal part.
- `slots(centre, axis, offsets)` — the world points.
- `widened(names, extents)` — the clips whose root leaves its start sideways by more than 1 cm (named in
  the status).

A rig's slot is where its **Main** stands at its clip's first frame (the floor drop's own rule,
`rigimport._place`, horizontal only, the clip's facing kept). A skeleton's slot is where its root stands at
the first frame.

## Several animations, one press

`maya_uebridge/lineimport.py` — `run(records, export, target, centre, axis, set_timeline, step)`, with
`target` "new_rig" or "skeleton" and `export(record) -> (fbx, fps)` the window's editor round trip:

1. Refusals first, nothing touched: for New rig the rig file of `rigimport.new_rig_entry()`.
2. **Every clip out of the editor** before anything enters the scene (a dead editor refuses with the scene
   untouched). One clip the editor cannot export is named and left out.
3. **Every clip imported** as its own namespaced skeleton (`rigimport.import_source`), the timeline not
   set per clip.
4. **Measured**: each clip's root track over its own range, through `getAttr(worldMatrix, time=)` — a bare
   skeleton driven by its curves, no constraint (trap 69 is about constraint chains); at most 240 samples
   a clip. A frame walk would evaluate every rig in the scene per frame.
5. **Laid out** (`lineup`), and the timeline set to the union of the clips' ranges when the checkbox is on —
   before the bakes, so every bake and the camera set-up sees a range covering its clip.
6. **Each clip in turn**: New rig — a rig added (`rigimport.ready_rig`, the Characters card's active rig,
   else Manny), the clip retargeted onto it standing on its slot (`rigimport.retarget_imported`, the floor
   drop's wrapper), its skeleton deleted; Skeleton — the root wrapped in a group of its namespace
   (`skeldarDropShift`) and the group moved onto the slot.
7. A **cancellable progress window** over the whole press. A cancel keeps what is done and deletes the clip
   skeletons imported for the clips not yet done; a clip whose import or retarget fails is named and the
   rest go on.

The status line: «3 animations onto 3 new rigs in a line about (0, 0): Manny_Rig1 A_Jump, Manny_Rig2
A_Walk, Manny_Rig3 A_Run | step 2.5 m, widened beside A_Strafe», with any failures after it; the full
per-clip lines go to the Script Editor.

`rigimport.import_and_retarget` is split into those pieces — `plan_press`, `ready_rig`, `import_source`,
`retarget_imported` — and composes them in the same order as before, so the one-animation press is
unchanged.

## Pieces

- `maya_uebridge/window.py` — `allowMultiSelection=True`; `_selected_records()` (list order);
  `import_selected` routes N picked with New rig / Skeleton to `lineimport.run` (centre the origin, axis
  world X), Rig to the first with a note; `import_dropped(records, aim)` takes one record or a list —
  onto a rig the first, a floor drop of several to `lineimport.run` centred on the point along the aim's
  axis; `export_uasset_selected` refuses several.
- `maya_uebridge/listdrag.py` — the carried rows (`carried_rows`, pure), the selection put back, a list of
  records in the drag, `caption(names, aim)`; `drop_at(gx, gy, records)` takes a record or a list;
  `Scene.drop(records, aim)`.
- `maya_scenesetup/droptarget.clip_target` — a "new_rig" aim carries `label` and `axis` (the camera's
  right on the floor).

## Proof

Unit tests for every pure half (`lineup`, `carried_rows`, the captions, the routing in `window`), an
offscreen QListWidget in ExtendedSelection for the carried rows and the selection put back, and
`docs/superpowers/plans/verify_uebridge_many.py` in a disposable Maya (no Unreal: the editor's export
replaced by UE clips on disk): three clips by the button with New rig standing about the origin along X on
their slots, Main to 1e-3; a strafe-like sideways clip widening its gap; Skeleton mode the same; Rig mode
taking the first only; a real press–drag–release of a multiple selection onto empty floor laying three
rigs across the screen about the point, and onto a rig taking the first only; the list's selection kept.

## Addendum, the same day: a square, on the world's axes

The animator, after the push: «Давай будем всегда располагать наши анимации в квадратной формации в не
зависимости от угла камеры». The line is gone, and so is the drag's camera axis:

- **A square formation on world X and Z, whatever the camera**: `cols = ceil(√N)`, `rows = ceil(N / cols)`
  (2 → 2 × 1, 3 and 4 → 2 × 2, 5 and 6 → 3 × 2, 7–9 → 3 × 3). Clip i stands in column `i % cols`, row
  `i // cols`: **row 0 in front** (+Z, toward the front camera), each row **left to right along +X**, the last
  row partly filled from the left - the columns stay aligned.
- **Centred** on the origin (the button) or the floor point (a drop; the origin when no floor was seen):
  first and last column, first and last row, equidistant from the centre.
- **The step is per band**: a column's band is the union of its clips' sideways reach along X, a row's along
  the row axis (−Z, front to back); neighbouring bands keep `STEP` between them (`lineup.offsets` on the bands).
  So every two clips in different columns stay a whole step apart in X and every two in one column a whole step
  apart in Z - no two root paths ever come within a step, and still clips stand on an even grid.
- `lineup`: `grid_shape(count)`, `band(extents)`, `square_offsets(x_extents, z_extents, step)`,
  `square_slots(centre, x_extents, z_extents, step)`, `COLUMNS = (1, 0, 0)`, `ROWS = (0, 0, −1)`;
  `floor_axis`/`slots` and `droptarget`'s `axis`/`on_floor` go (nothing reads a camera axis any more).
- Wording: «3 animations onto 3 new rigs in a 2 x 2 square about (0, 0): …», the ghost «3 animations · 3 new
  Manny [rig] in a square · floor (120, -36)».

## Addendum 2: a drag in the Skeleton mode places skeletons

The animator: «Сейчас групповое перетягивание работает только с ригом даже если выбран skeleton давай исправим.
если у нас выбран скелет то будем располагать в сцене скелеты». Until then a drag ignored the mode segments.

- **The Skeleton mode reaches the drag** (read when the drag starts): over a viewport the clip(s) arrive as
  skeletons standing on the floor point under the cursor - **rigs under the cursor are ignored**, nothing is
  retargeted - one with its root at its first frame on the point, several in the square about it
  (`lineimport.run(..., "skeleton", centre=point)`). No floor under the cursor: one stands where the clip
  is, several about the origin. Off every viewport, or back on the hub: nothing, as before.
- `droptarget.skeleton_target(gx, gy)` → `dict(kind="skeleton", point, text)` / `dict(kind="none", text)`;
  `listdrag.Scene` reads `window.import_mode()` at the snapshot and asks it in that mode; the ghost:
  «A_Jump · a skeleton · floor (120, -36)», «3 animations · 3 skeletons in a square · floor (120, -36)».
- `window.import_dropped` takes kind "skeleton": one is `rigimport.import_source` + `stand_skeleton` (the
  timeline checkbox applies), several `lineimport.run`.
- Rig and New rig drags are unchanged: a rig under the cursor takes the first, the floor a square of new rigs.

## Addendum 3: Skeleton means the Characters card's skeleton, with its geometry

The animator: «Давай сделаем что бы скелет вставлялся с геометрией» - then, before anything was built, «давай
будем использовать скелет который активен в вкладке character». Asked: the clip goes **by bone names, respecting
proportions**; a rig active in Characters means **that model's skeleton**.

- **Which skeleton** (`skeletonimport.skeleton_entry_for`, pure): the Characters card's active row when it is a
  skeleton; else that model's skeleton (Manny [rig] → Manny UE5 [skeleton], Creep [rig] → Creep [skeleton]);
  else (Orc D has none) Manny UE5 [skeleton]. The Skeleton mode - button or drag, one or several - adds that
  skeleton (`character.add_character`, its geometry and textures or palette colour as Add Character gives them)
  and the clip's own skeleton is deleted after the transfer, as the rig modes do.
- **The transfer** (`skeletonimport.transfer`): target bones paired with the clip's by leaf name (the roots
  paired whatever their names - a second Manny's root is `Manny_Skeleton_root`); for a UE4-schema target under
  a UE5 clip the spine follows `maya_retarget`'s map (spine_01 ← spine_02, spine_02 ← spine_04, spine_03 ←
  spine_05). **A twin** - measured: ≥ 90 % of the shared bones longer than 1 cm within 1 % of the clip's
  length (Manny UE5 99 %, Creep 35 %, UE4 Mannequin 2 %) - takes every bone's world matrix
  (`parentConstraint`, no offset): exact. **Otherwise** every bone takes the clip bone's world orientation
  (`orientConstraint`, no offset; the bone keeps its own length, the mesh does not stretch), root and pelvis
  their position too, and the `ik_*` helpers stay at rest (their layout is the skeleton's own: the Creep's
  `ik_hand_gun` stands at zero with `ik_hand_r` 110 cm under it). Baked over the clip's range
  (`bakeResults -simulation`), the constraints deleted. Bones with no partner are named.
- **Placement** is the clip's: its root wrapped (`skeldarDropShift`) and moved onto the slot / the floor point
  before the transfer, so the bake carries the move into the skeleton's root; a single clip with no point stands
  where the clip is. The new skeleton itself is never moved (the Creep's `Armature` stays Cascadeur's layout).
- The ghost: «A_Jump · a new Manny UE5 [skeleton] · floor (100, -50)», «3 animations · 3 new Manny UE5 [skeleton]
  in a square · floor (…)». The status: «A_Jump onto Manny UE5 [skeleton] root1: 89 bones exact, frames 0-61 |
  standing at floor (100, -50) | not in the clip: head, neck_01, neck_02».

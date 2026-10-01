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

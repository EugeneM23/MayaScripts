# UE Bridge: an animation dragged out of the list into the viewport

2026-10-01. The animator: «Двай реализуем возможность перетаскивания анимаций из окна UEbridge. Суть
такая - я зажимаю клавишу мышки и ташу анимацию из списка во вьюпорт и подобно с нашим оружием если я
попадаю в какой-то риг то анимация должна перекинутся на него какбуд-то мы нажали import с опцией rig
если мы не нашли ничего то тогда нам нужно сделать new rig.»

Asked, and answered:

- **a new rig stands where the clip is** («Где клип»), as Import with New rig does. The retarget puts
  `Main` on the clip's root, so the drop point could be honoured only by shifting the clip, and that
  shift would ride into the root bone and the export. The drop decides WHICH rig, nothing else;
- **the new rig is Manny** («Manny, как New rig»): `catalog.default_rig()`, the New rig segment's rig.

## What the animator does

1. Press on a row of the UE Bridge list and move past Qt's start distance. The row is the one pressed,
   whatever the list's selection does on the way.
2. A ghost rides the cursor (the hub's shared one: an icon on a backdrop, a caption pill under it):
   - over a rig in a viewport: «A_Jump · retarget onto Manny_Rig1», in the accent;
   - over a viewport with no rig under the cursor: «A_Jump · a new Manny [rig]», in the accent;
   - over the hub, the list included: «release off the hub to import», muted;
   - anywhere else: «no target - drop onto a viewport», muted.
3. Release:
   - on a rig → the clip is exported from the editor and imported as Import with the Rig mode would,
     onto THAT rig (its previous take cleared, retarget, bake, the clip's skeleton deleted);
   - on a viewport, no rig → as Import with New rig: a Manny rig is added and takes the clip;
   - anywhere else → nothing, and the status line says why.
4. Esc or the right button cancels.

The import-mode segments and the scene selection do not change a drop: where it lands is the choice.
The «set timeline to clip range» checkbox applies, as for Import. A click and a double click on the
list behave as before (a double click still imports through the mode).

## Which rig is under the cursor

The Weapons drag's rule (`droptarget`), on rigs: every rig's game skeleton (`Rig.skeleton_root` and its
joints; a rig driving none falls back to the joints under its group) is read once when the drag
starts, in world space, as parent→child segments. Per move they are projected through the model panel
under the cursor; a rig whose nearest bone on screen is within max(16 px, 8 % of its projected height)
is under the cursor, the nearest wins, a tie goes to the rig nearer the camera. Bare skeletons do not
count: they are not rigs, and a drop beside one makes a new rig.

The rig is carried as its namespace and found again (`maya_rigs.find`) after the editor's round trip:
the export takes seconds and the animator may have deleted it meanwhile — that is said, nothing is
imported.

## Pieces

- `maya_scenesetup/droptarget.py` — `figure_under(point, figures, radius_min)` (pure; `choose` now
  uses it for the figures that have hands), `rig_snapshot()`, `clip_target(gx, gy, snap, scale,
  new_label)` → `dict(kind="rig", rig=<namespace>, label, text)` / `dict(kind="new_rig", text)` /
  `dict(kind="none", text)`; captions `rig_text`, `new_rig_text` (pure).
- `maya_uebridge/rigimport.py` — `import_and_retarget(..., rig=None)`: an explicit rig is the one
  that takes the clip with `target="rig"`; the selection is not asked. `target="new_rig"` ignores it.
- `maya_uebridge/window.py` — `import_dropped(record, aim)`: the rig re-found, the editor's export,
  `rigimport.import_and_retarget` with that rig or `"new_rig"`; `build_panel` attaches the drag to the
  list (`listdrag.attach`) where Qt stands. The window module stays `cmds`.
- `maya_uebridge/listdrag.py` (new; Qt lazily through `maya_hubqt.qt()`) — an event filter on the
  list's `QListWidget` (Maya's `textScrollList` is one) and its viewport:
  - the press passes through (Maya selects the row as before) and records the row (`indexAt`) and
    the record (`records_of()[row]`, the window's filtered list, one row per record);
  - while the left button is held after such a press, MOVES are eaten — the list neither drags its
    selection nor autoscrolls — and past the start distance the drag starts: a synthetic release at
    the press point completes the click for the list (its selection stays on the pressed row, its
    state returns to none), the ghost shows, the rigs are read (`scene.snapshot()`), the keyboard is
    grabbed for Esc;
  - during the drag every mouse event is ours; the caption is re-read at most every 33 ms;
  - the release ends the drag (the ghost gone) and calls `drop_at`, public so a verify drives it
    without a mouse;
  - `Scene` is the seam the tests replace: `scale`, `snapshot`, `target`, `over_hub`, `drop`, `say`.
    The real `drop` defers the import one idle (`maya.utils.executeDeferred`) so the ghost is gone and
    the mouse released before the editor's round trip blocks Maya, and runs it through `window._run`
    (the status line takes a failure).
- `maya_hubqt.on_hub(gx, gy)` — whether a global point lies on the hub: moved out of the Characters
  grid's `Scene.over_hub`, which now asks it.
- `maya_hubicons` — Tabler's `run` icon (MIT, as the rest), the ghost's.

## Refusals and messages

Everything `rigimport` refuses it still refuses, after the round trip as for Import: a connected rig
(MoCapConstraints standing), a rig still posed after the reset, no rig file for a new rig. The drop's
own: the rig gone while the editor exported; no record under the press (an empty list) starts
nothing.

## Proof

- Unit tests: `figure_under`, `clip_target` on a fake viewport; `rigimport` with an explicit rig (the
  selection never asked, that rig reset and connected) and with `new_rig` ignoring it; `listdrag`
  offscreen on a real `QListWidget` with a fake scene — press/drag/release outside drops the pressed
  row's record, a click is no drag, moves are eaten while held, Esc and the right button cancel, a
  release on the hub does nothing, the caption names the target, a drop that raises says so.
- `docs/superpowers/plans/verify_uebridge_drag.py` in a disposable GUI Maya (scratch `MAYA_APP_DIR`,
  `MAYA_NO_HOME=1`): the hub on UE Bridge with a cached list, two rigs added; `clip_target` at the
  projected pelvis of each rig names that rig, at an empty floor point "new_rig", off the viewport
  "none"; a press-drag-release sent through Qt to the real list starts and ends a drag; `drop_at`
  with an FBX standing in for the editor's export (`window._export_from_editor` replaced for the
  run — no editor is needed) retargets onto the rig under the point and leaves the other unmoved, and
  a drop on the empty floor adds a third rig.

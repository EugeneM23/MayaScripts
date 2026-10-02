# The animation's name under each character (2026-10-02)

## The ask

The animator, task 4 of four, away for two hours («сделать самостоятельно от начала и до конца ...
пушить и делать сборку не нужно пока я не проверю»):

> при групповом импорте в сцену в том числе и при переноси мышкой драгом давай внизу под каждым
> скелетом или ригом персонажем будем писать имя анимации а то сейчас не понятно

After a batch import (`lineimport.run`, the 2 x 2 square of 2026-10-01) the scene holds four identical
Mannys and nothing says which clip plays on which. Every decision below was taken alone; each is
recorded with its reason.

## Measured first (a disposable GUI Maya 2027, port 7065, scratch prefs, `MAYA_NO_HOME=1`)

What can write text in the viewport under a character:

| option | what it does | verdict |
|---|---|---|
| `annotationShape` (`displayArrow` off) | text at a FIXED SCREEN SIZE, centred on its point, facing the camera, drawn OVER every mesh (an annotation 40 cm behind a 40 cm-wide body read whole), in a playblast; hidden by Show > Dimensions | **chosen** |
| `textCurves` | 115 nodes for one 28-letter name; illegible at 16 m lying on the floor, barely standing; occluded by bodies | rejected |
| a HUD per character | screen-space, would need its own projection each frame | not pursued |

How the annotation behaves (each measured on six side-by-side variants, a marquee
`MGlobal.selectFromScreen` box over the whole view, and two backgrounds):

- default colour: Maya's dark green; an RGB override on the transform or the shape recolours it;
- **reference display draws it BLACK whatever its colour** (on the transform, the shape, or through a
  display layer with its own colour) - unreadable on a dark backdrop; template draws a dim grey;
- **the transform in reference display + the shape's OWN override back to normal (display type 0) with
  RGB on**: the marquee does not take it (the pick reads the parent's display type) and it is drawn in
  the shape's colour (the draw reads the shape's override). The only variant that is both;
- `cmds.annotate` refuses a bare transform («Annotation command only works on shapes»);
  `createNode("annotationShape")` needs no target at all.

The colour, measured behind the labels of a 2 x 2 square of textured Mannys (WCAG contrast ratio of the
worst tenth of each token's ink against what is behind it, per camera; the second number a dark
backdrop):

| token | low camera (back labels over front bodies) | three-quarter working camera (labels over the floor) |
|---|---|---|
| muted `#9a9ca3` | 2.10 / 2.10 | 2.28 / 3.94 |
| text `#e4e4e6` | 1.35 / 1.35 | 4.91 / 8.52 |
| accent `#e07a36` | 2.14 / 2.27 | 2.15 / 3.61 |
| accent_text `#f0a26b` | 1.62 / 1.62 | 3.00 / 5.19 |
| ok `#8fd19a` | 1.40 / 1.40 | 3.49 / 6.05 |

No luminance beats ~2.3 against a grey background and white bodies at once (the bodies sit near 0.8,
the grey at 0.11); near-white wins over the floor and collapses to 1.35 over a body. The accent orange
has the best worst case across both cameras, and its HUE stands apart from every neutral behind it -
looking at the pictures, orange over a white leg still reads where grey does not. The dispatcher's
suggestion was the muted text colour; measured, it ties the accent on luminance and loses on hue.

Where it stands: `FRONT` = 50 cm ahead of the root on world +Z, past Main's ring (radius 40.52 cm); at
30 cm the text sat on the ring and the feet. Every rig faces +Z; a turned character keeps the label
50 cm on world +Z - simple and exact, and the label draws over meshes anyway.

Following: four DG nodes (since the fix pass - see its section; the first build used a
`pointConstraint`, whose offset turned and rose with the group above the label). For a rig the root is
its game skeleton's root (`root <- Main`, root motion); for a skeleton its root joint.

## The design

`SkeldarAnim/maya_scenesetup/cliplabel.py` (cmds; a leaf, imports nothing of ours):

- pure: `label_text` (the file's name without a known animation extension, whitespace collapsed, a
  long name kept by its head and tail around "..."), `node_name` (`<rig ns>:clipLabel`, or
  `<root>_clipLabel` at world level so the outliner pairs them), **`home_for(kind, group)` - the ONE
  function that decides where a label hangs** (the rig's top group; None = world for a skeleton),
  `plan(existing, clip)` (create / keep / update, extras to delete), `colour_of`;
- scene: `labels_of(root)` (by the message link, then the marker), `all_labels()` (by type then
  marker - trap 70), `ensure(root, clip, namespace, home)`, and the two entry points
  **`label_rig(rig, clip)` / `label_skeleton(root, clip)`, which never raise** (a label must not fail
  an import; the traceback goes to the Script Editor).
- identity: `skeldarClipLabel` (the clip's name, locked) on the transform, `skeldarClipLabelRoot` fed
  by the root's `.message`. Never found by name.
- rotate and scale locked; the translate is driven by the follow network (below), visibility free.
- **following in WORLD space** (`_follow`): `root.worldMatrix[0]` -> decomposeMatrix (its world X, Z)
  -> composeMatrix (Y = `FLOOR`) -> multMatrix (a constant translate of `FRONT` on world +Z - two pure
  translations add in either order - then the label's own `parentInverseMatrix[0]`) -> decomposeMatrix
  -> `label.translate`. Each node carries `skeldarClipLabelOf`, fed by the label's `.message`
  (`parts_of`). `follows(label, root)` / `follows_plan` (pure) ask whether the translate comes from one
  of ours and one of ours reads this root; `ensure` rebuilds a label that no longer follows
  (`_unfollow` takes our nodes, a first-build pointConstraint and any input off the translate).
- **a label names the take, so whatever clears the take clears the label**: `clear(root)` /
  `clear_rig(rig)` (never raising) from the rig reset in front of every bridge import
  (`rigimport.ready_rig`) and the Retarget button's (`maya_rig_retarget.run_retarget`); the Retarget
  button then relabels the rig (`relabel_rig`) with `clip_name_from(source, top_is_joint, scene)`
  (pure): the source's outermost namespace (the bridge's «as a new skeleton» names it for the clip),
  else its top node when that is not a joint and not a generic wrapper (`GENERIC`: `Armature`, `root`,
  `Group`, `Bip001`...), else the scene's file when it was OPENED from a clip file (`CLIP_FILES`; never a
  .ma / .mb) - else no name, and no label.

The hooks - one seam each, `_label`, importing `cliplabel` lazily and answering None without it:

- `rigimport.retarget_imported` after the bake and the clip's namespace removal - the Import Animation
  button (Rig, New rig), a drop on a rig or the floor, and `lineimport._onto_new_rig` (the batch
  square) all go through it;
- `skeletonimport.onto_skeleton` (Skeleton x New, the Skeleton square, a drop on the floor in the
  Skeleton kind) and `onto_existing` (Skeleton x Onto selected, a drop on a skeleton).

`lineimport` and `window` needed no change: one rule, at the bottom of every road.

`deletion`: `LABEL_MARKER` (pinned equal to `cliplabel.MARKER`), `_clip_labels(root)` (the CoM rule:
linked to the root by message, carrying the marker) added to both a rig's and a skeleton's parts. A
rig's label is under its group already; a skeleton's stands at world level and would otherwise survive
its character.

Never in an export: the label is not under the skeleton, and the exporter exports the joints with
`FBXExportIncludeChildren false` (trap 76). The existing "is this joint constrained" checks
(`animimport.constrained_joints`: constraint CHILDREN; `fbxlayout._kind`: incoming connections) do not
see a constraint where the root is only a TARGET, so a labelled skeleton is not refused on its next
import and its layout is not misread.

**For the merge (agent D's per-character group)**: point `home_for` at D's group - one line - and the
labels move into it; `deletion._clip_labels` keeps finding them by the link either way.

## Decisions taken alone

1. The annotation over text geometry (measured above).
2. Unselectable by the parent-reference / shape-normal split (measured above).
3. The accent colour over the muted one (measured above).
4. 50 cm in front on world +Z, not the character's own facing (simple, exact, faces +Z on arrival).
5. A label per CHARACTER. A skeleton's is replaced in place (the same node, its text and marker
   rewritten; the same clip again changes nothing). A rig's is deleted by the reset in front of the
   import and made again after the bake (fix pass): the reset is the one place every rig road passes
   BEFORE anything can be refused, so no refusal can leave a stale name.
6. The Retarget button (`maya_rig_retarget.run_retarget`) relabels the rig with its source's name, or
   unlabels it when the source gives none (fix pass; the first build left the old clip's name standing).
   Two small seams there, `_unlabel` / `_relabel`, nothing else in the module touched.
7. No hotkey, no toggle: Show > Dimensions hides every label (measured: it hides annotations), and
   Delete takes them with their characters.
8. A label is not a "part" Onto selected names a skeleton by (it cannot be picked in the viewport).

## Fix pass (2026-10-02, after an independent review)

Five findings, each read against the code:

1. **A wrong name is worse than none: the Retarget button left the bridge's label standing.**
   Confirmed: `run_retarget` resets and re-takes the rig with no word to the label. Fixed - the reset
   clears it, a successful bake relabels from the source (`clip_name_from`), a source with no name
   leaves the rig unlabelled.
2. **A refusal after the reset left the old label on a cleared rig.** Confirmed for the rig road
   (`ready_rig`'s still-posed refusal, a clip with no joint, a connect refusal - all after
   `reset_build_pose`). Fixed by clearing AT the reset, which covers every refusal after it. Rejected
   for the skeleton road: `skeletonimport.transfer` returns before cutting a single key when no bone
   pairs (`if not pairs: ... touch nothing`), so a «no bone matches» failure leaves the take - and its
   label - true.
3. **The pointConstraint's offset is in the constrained node's PARENT space**, and a rig's label hangs
   under the rig's group. Confirmed by measuring: with the group moved (37, 22, -15) and turned 40 deg
   the first build's scheme reads **32.139 cm** off. Fixed with the world-space follow network: the
   label **0.000000 cm** off under the same move.
4. **`ensure` never mended a label that had stopped following.** Confirmed. Fixed (`follows` /
   `_unfollow` / `_follow`), on the same node - also for a label still carrying the first build's
   pointConstraint.
5. **Viewport Studio's Clean view hides `dimensions`, and with it every label.** Confirmed (CLUTTER
   holds `dimensions`); NOT changed: Clean view is the beauty picture - grid, joints, cameras and
   locators already go - and a working label is clutter there; unticking Clean view (or Restore) brings
   the labels back with the animator's own flags. Stated in the CLAUDE.md draft.

## Proof

`docs/superpowers/plans/verify_clip_labels.py` - **17/17 in mayapy standalone** (the editor's export
replaced by UE clips on disk, the worktree's plugin first on `sys.path`):

1. a batch onto New rig, three clips: one label per rig, its clip, under its group, in its namespace,
   dressed, outside the skeleton;
2. following over the take (first / middle / last frame, a real time change each): worst **0.000000 cm**
   while the thrust's root travels **248.058 cm** (the positive control);
3. 3a the reset in front of an import onto rig 1 takes its label (0 left); 3 the import: one label,
   the new clip; 3b the same clip again keeps it; 3c still following, 0.000000;
4. the Skeleton square (Manny UE5 [skeleton]): one label per skeleton at world level, following,
   0.000000;
5. Skeleton x Onto selected replaces the skeleton's label's text;
6. a rig's and a skeleton's export read back (93 joints each) hold no label, no marker, no annotation -
   while the label exported on purpose reads back by name (the control);
7. Delete through a rig's Main and a skeleton's mesh takes both labels (3729 nodes), the others keep
   theirs; 7b Ctrl+Z brings them back linked;
8. every label belongs to a character standing, one each;
9. a Creep rig, root under its Armature: labelled, 0.000000 cm over 248.1 cm of travel;
10. the rig's top group moved (37, 22, -15) and turned 40 deg: the label **0.000000 cm** from the root's
    floor point + FRONT on world +Z; the first build's pointConstraint under the same group, the
    control, **32.139 cm** off;
11. a label whose follow nodes were deleted, and one carrying a first-build pointConstraint: both follow
    again after the next import, on the same node (0.000000 / 0.000000 cm, no constraint left);
12. the Retarget button with a hand-imported source in the namespace `Walk_byHand`: the rig's label
    goes from ShortSword_Attack_Thrust_3P to `Walk_byHand`;
13. the Retarget button with a source that names no clip (its namespace merged away, a bare `|root`,
    an untitled scene): the rig is left with no label.

`docs/superpowers/plans/verify_clip_labels_gui.py` - **all gates green in a disposable GUI Maya**
(port 7065, killed by its PID after; re-run whole in the fix pass with the window restored -
minimized, gates 3, 4 and 9 failed on the measurement, trap 163?):

- square: four rigs from the batch each labelled (gate 1); with one label or one body hidden at a time
  and diffed against the full playblast, each label's ink drawn (2986 / 2601 / 1796 / 962 px, gate 2),
  its centre inside its own body's width and at its feet (-0.022..+0.064 body heights), no two labels
  overlapping (gate 3); a marquee over the whole view takes 8 nodes and no label (gate 4); the contrast
  table above (gate 9: the accent's worst tenth 2.15 / 3.61 >= 2);
- drag: `listdrag.drop_at` of the thrust onto empty floor - a new rig, Main on the cursor's floor point
  (139.34, 2.12 for an aim at 140, 0 - about a pixel), labelled (gate 5); two clips dropped in turn
  onto a standing rig - labelled, then relabelled with the second, one label throughout (gate 6).
- the fix pass's square run: ink 2987 / 2600 / 1796 / 962 px, centres -0.022..+0.064 body heights,
  no overlap, the marquee 8 nodes and no label, accent 2.15 / 3.61 - the first run's numbers.
- pictures: `clip_labels_square.png` (the working camera), `clip_labels_square_dark.png`,
  `clip_labels_drag.png` (re-taken on the fixed build; the square is the first build's picture to the
  eye - the follow network draws where the constraint did).

3558 unit tests, all green (`tests/test_scenesetup_cliplabel.py`: text, names, home, plan, colour,
the dressing, the never-raise rule, `ensure`'s answers and its repair, `clip_name_from`,
`follows_plan`, `clear` / `clear_rig` / `relabel_rig`, every road asking for a label;
`test_uebridge_rigimport`: the reset unlabels, a connect refusal leaves no label;
`test_rig_retarget`: unlabel after the reset, relabel after the bake with the source, none on a
refusal or a holder still standing).

## Not done

- A label that turns with the character (it stays 50 cm on world +Z).
- A per-label toggle or a hub switch (Show > Dimensions does all of them; Viewport Studio's Clean view
  hides them too, by design - finding 5).
- Labels for clips imported before this (they appear on the next import onto that character).
- The Retarget button names its source by namespace / top group / opened file only; a plain import
  of `Walk.fbx` into a working .ma, its root at world level, gives no name, and the rig is left
  unlabelled rather than guessed.

## CLAUDE.md section (draft)

## The animation's name under each character (2026-10-02)

The animator: «при групповом импорте в сцену в том числе и при переноси мышкой драгом давай внизу под
каждым скелетом или ригом персонажем будем писать имя анимации а то сейчас не понятно» - away for two
hours, every choice taken alone. Spec `docs/superpowers/specs/2026-10-02-clip-labels-design.md`.

- **One rule at the bottom of every road**: `rigimport.retarget_imported` (the Rig and New rig presses,
  a drop on a rig or the floor, the batch square) and `skeletonimport.onto_skeleton` / `onto_existing`
  (the Skeleton presses and drops) end in `_label`, a lazy seam onto
  **`maya_scenesetup/cliplabel.py`** (`label_rig` / `label_skeleton`, never raising). `lineimport` and
  `window` needed nothing. One label per character: a later clip REPLACES its text on the same node
  (`plan`: create / keep / update) - and **a label names the take, so whatever clears the take clears
  the label**: the rig reset in front of every bridge import (`rigimport.ready_rig`) deletes it, so no
  refusal after the reset (still posed, no joint, a connect refused) leaves a stale name, and the press
  writes a fresh one after its bake. **The Retarget button** (`maya_rig_retarget.run_retarget`) clears
  at its reset too and relabels after the bake from its source (`clip_name_from`, pure: the outermost
  namespace, else a top group that is not a joint or a generic wrapper, else the clip file the scene was
  OPENED from) - or leaves the rig unlabelled when the source names nothing: never the old clip's name.
- **What it is, measured against text curves (115 nodes, illegible at 16 m)**: an `annotationShape`,
  `displayArrow` off - fixed screen size, centred on its point, facing the camera, drawn over every mesh,
  in a playblast, hidden by Show > Dimensions. **Unselectable AND coloured** (trap 159?): the transform in
  reference display, the shape's own override back to normal with RGB. In the hub's **accent** - measured
  behind the labels of a textured 2 x 2 square, no luminance beats ~2.3 against a grey background and
  white bodies at once (muted 2.10, accent 2.14 the best worst case; near-white 4.91 over the floor,
  1.35 over a body), and the orange's hue stands apart from every neutral.
- **Where**: 50 cm ahead of the root on world +Z (`FRONT`, past Main's ring, 40.52) on the floor,
  following the root in WORLD space through four DG nodes (`_follow`: the root's world X/Z, Y on the
  floor, FRONT on world +Z, then the label's own `parentInverseMatrix`): exact (0.000000 cm over the
  thrust's 248 cm) and still exact with the rig's group moved and turned (trap 160?). Each node is linked
  to the label by message (`skeldarClipLabelOf`); a label whose network is gone is mended on the next
  import (`follows`).
  A rig's label hangs under its group in its namespace (`<ns>:clipLabel`), a skeleton's at world level
  (`<root>_clipLabel`), linked by message (`skeldarClipLabelRoot`) and marked `skeldarClipLabel` (the
  clip's name). **`home_for` is the one place that decides where** - the per-character group points it
  there in one line. `deletion._clip_labels` takes it as a part; never under the skeleton, never in an
  export (trap 76; gated by reading the FBX back, with the label exported on purpose as the control).
  The root only FEEDS the label's network (its `worldMatrix` out), so the existing checks - a joint's
  constraint CHILDREN, a root's incoming connections - see nothing new on it.
- Viewport Studio's **Clean view hides the labels** with `dimensions` (by design: it is the beauty
  picture); unticking it gives them back.

Proof: `verify_clip_labels.py` **17/17 standalone** (batch onto rigs and skeletons, the reset taking
the label, a single import relabelling, following to 0.000000 cm, the exports free of labels, Delete +
Ctrl+Z, a Creep, the group moved and turned - the label 0.000000 against the old constraint's 32.139 cm
-, a broken label mended, the Retarget button relabelling from its source's namespace and unlabelling
for a nameless source); `verify_clip_labels_gui.py` all gates in a disposable Maya (each label's ink at
its own character's feet by hiding one at a time, no overlap, a marquee takes no label, the colour
table, drops onto the floor and onto a rig); pictures `clip_labels_square.png`, `_dark`,
`clip_labels_drag.png`; 3558 unit tests.

159?. **An annotation in reference display draws BLACK whatever its colour** - an override on the
      transform, on the shape, or a display layer's own colour - so "unselectable" read as "invisible on
      a dark backdrop". The pick reads the PARENT's display type and the draw the SHAPE's override: the
      transform in reference, the shape's override enabled at display type 0 with RGB on, is both
      unselectable by a marquee and drawn in its colour. Template draws a dim grey.
160?. **A `pointConstraint`'s offset - and the constrained node's own skipped channel - live in its
      PARENT space** (the memory note "pointConstraint offset is parent-space", met again). The first
      build's label hung under the rig's group with `offset=(0, 0, 50)` and `skip="y"`: with the group
      moved (37, 22, -15) and turned 40 deg it stood **32.139 cm** off its floor point, turned with the
      group and lifted 22. A WORLD point for a node under a group that may move is computed in world and
      brought in through the node's own `parentInverseMatrix` (decompose -> compose -> mult ->
      decompose -> translate): 0.000000.
161?. **`cmds.annotate` refuses a bare transform** («Annotation command only works on shapes»), and when
      given a shape it draws an arrow to it; `createNode("annotationShape", parent=t)` needs no target.
162?. **Work queued with `maya.utils.executeDeferred` does not run inside the same command-port send**,
      not even through `maya.utils.processIdleEvents()`: a drop's import (`listdrag` defers it one idle)
      happens after the send ends, and a gate in the same send reads the scene before it. Drop in one
      send, measure in the next.
163?. **A disposable GUI Maya left MINIMIZED playblasts fine and measures wrong**: the same square read
      label boxes overlapping each other, the contrast at 1.93 for 2.15 and a whole-view marquee picking
      **0** nodes - the pick runs through the viewport's draw (trap 56) and a minimized window draws
      nothing - while the picture itself was the same to the eye. `MayaWindow.showNormal()` (port 802 x
      650) and every gate passed with the first run's numbers. Restore the window before a gate that
      picks or diffs, and probe `M3dView.portWidth()` (trap 105's family).
164?. **A playblast diff's bounding box is stretched across the picture by a few stray changed pixels**
      (a texture filtered a hair differently between two blasts, at JPG quality 100): one label's box
      read as overlapping all three others. Trim the box to the 2nd..98th percentile of the changed
      pixels. And hide one thing at a time rather than projecting points: no film-fit arithmetic to get
      wrong.

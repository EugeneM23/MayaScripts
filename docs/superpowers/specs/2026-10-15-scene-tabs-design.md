# Scene tabs, stage 1: several scenes in one Maya, switched like browser tabs

2026-10-15. The animator asked whether Maya can hold several scenes as browser tabs
instead of several Maya processes; after three answers («Возможно ли в maya сделать
вкладки как в браузере», a desktop shell offered, then «давай подумаем про вариант с
референсами ... мы нажимаем на вкладку и все объекты которые она референсит скрываются и
деактивируются, изменяется настройки вьюпорта, открываются старые окна и показываются
новые ... имитируем разные вкладки») they chose, from three approaches:

- **what tabs are for: all three** - several own scenes worked on and saved each to its
  own file, carrying poses / animation / characters between scenes, keeping a reference
  scene beside the work;
- **approach A**: every tab is a scene file IMPORTED into a namespace of its own in one
  Maya scene (references, approach B, cannot save new objects into the tab's file; one
  scene at a time, approach C, cannot carry anything between tabs);
- **undo: one shared history** - a Ctrl+Z that reaches a step made in another tab
  switches to that tab first;
- **the tab bar above the viewport**, always there, not in the hub;
- **each tab keeps its whole Maya layout** (a workspace of its own), slower switching
  accepted;
- built in **two stages**: this spec is the tabs themselves; stage 2
  (`2026-10-15-scene-tabs-plugin-scope-design.md`) makes the plugin's tools see only the
  active tab.

Maya holds one scene per process (one DG, one timeline, one undo queue); nothing here
changes that. Tabs are an imitation built on namespaces, visibility and per-tab state.

## Measured before designing (mayapy standalone, 2026-10-15)

Scripts in the session scratchpad (`reftabs/probe_*.py`), on a work scene holding a Manny
rig added through Add Character (66 MB `.ma`) and a film-rate scene with a nested
reference, an animation layer, a display layer and a camera.

| | |
|---|---|
| open the rig scene `.ma` / `.mb` | 1.90 s / 1.03 s |
| save it `.ma` / `.mb` | 0.88 s / 0.32 s |
| import it into a namespace | 1.19-1.42 s |
| reference it / unload / reload | 1.55 / 0.54 / 1.60 s |
| a frame with the rig shown / hidden (EM parallel, no viewport) | 3.19 / 0.07 ms |

- **New nodes go into the current namespace**: with `:tabA` current, a locator came out
  `tabA:madeInTab`, and Add Character made `tabA:Manny_Rig1`.
- **Import with `preserveReferences=True` keeps a nested reference a reference**
  (`tabC:refRN` -> `tabB.ma`, `tabD:refRN` -> `tabB.ma{1}`); without the flag the
  referenced content is flattened into plain nodes and an empty reference node is left.
  A reference's namespace moves with `file -edit -namespace`, its reference node renamed
  with it.
- **Animation layers**: the first imported file's `BaseAnimation` became the scene's root
  layer; the second file's root became a CHILD layer of it (`tabD:AnimLayerRoot`, parent
  `tabC:BaseAnimation`); both tabs' layers evaluate right (45.0 each), muting one tab's
  layer leaves the other alone. A layer made while `:tabD` is current is named
  `tabD:NewLayer` and parented under the SCENE root.
- **One undo chunk restores a switch**: namespace, time unit, playback range and
  visibility all came back with one `cmds.undo()`.
- **A time-unit switch keeps keys on their seconds** (`currentUnit -updateAnimation
  true`): a film tab's keys at 10/30 read 12.5/37.5 in ntsc and 10/30 back in film; an
  ntsc tab's keys round-trip exactly.
- **Maya's own Save can be refused**: an `MSceneMessage.addCheckCallback(kBeforeSaveCheck)`
  returning False cancelled `file -save` (nothing written; Maya raises «File operation
  cancelled by user supplied callback»).
- **A tab saves back to a plain file** by renaming its nodes into the root namespace,
  `exportSelected -preserveReferences`, and renaming them back: the rig scene came back
  with its keys, the rig added in the tab, a locator made in the tab, unit ntsc, range
  0-50. Moving the whole namespace (`namespace -moveNamespace`) failed on the second tab
  («would result in a name clash»): the import brings the file's furniture
  (`sceneConfigurationScriptNode`, `uiConfigurationScriptNode`, `shapeEditorManager`,
  `poseInterpolatorManager`, `UsdDefaultRenderSettings`) into the namespace. And
  `exportSelected -relativeNamespace` is refused together with `-preserveReferences`.
- **Referencing does not bring the file's playback range** (the session kept its own);
  the range lives in the file's `sceneConfigurationScriptNode`, which
  `maya_sharerecords.playback_from_script` already parses without evaluating.
- **A reference unload flushes undo whole** - one reason tabs are imports.

## What a tab is

- **The session.** In tab mode the Maya scene is a session: its name is
  `<userAppDir>/SkeldarTabs/session_<date_time>.ma` (Maya's autosave and recovery file get
  a name; the session itself is never written by a Save). A `network` node
  `skeldarSceneTabs` in the root namespace holds the session as JSON (`skeldarSceneTabs`
  attribute): version, the active tab, and per tab its namespace, file path, file mtime
  at open, fps, playback and animation ranges, current frame, modified flag, workspace
  name, persp camera matrix and focal length, panel display flags, selection (UUIDs). The
  autosave / recovery file therefore holds every tab and the bar can be rebuilt from it.
- **A tab** is one `.ma` / `.mb` file imported with `preserveReferences=True` into its
  namespace: the file's stem made a legal Maya name (`t_` before a leading digit), free
  among the scene's namespaces (`attack_01`, `attack_011`, ...). Its own animation layers
  hang under a tab layer root (the file's `BaseAnimation`, whatever Maya renamed it to on
  import, found as the namespace's top layer) under the session's root layer.
- **One tab is ordinary Maya.** While one scene is open it stays in the root namespace and
  nothing is intercepted; the bar shows its name. Opening a second scene CONVERTS the
  current one into tab 1: its own nodes renamed into the namespace of its file's stem
  (by UUID, furniture and default nodes left out), its top-level references moved with
  `file -edit -namespace`, its root-level child namespaces (`Manny_Rig`) moved under it
  (`namespace -rename x x -parent :tab`), its layers under a tab layer root. The session
  takes its session name. Closing tabs down to one converts the last back (the reverse)
  and gives the scene its file's name again.

## Opening, saving, closing

- **Open** (the bar's «+» > Open file..., a recent file, or Maya's File › Open / Ctrl+O /
  a script's `file -open` while two or more tabs exist): import as above (this flushes
  Maya's undo, as opening a file does), read the tab's fps and ranges from the file
  (ranges from its imported `sceneConfigurationScriptNode`, numbers only; the unit from the
  `.ma` header line `currentUnit ... -t <unit>`, from the `.mb` header - the plan measures
  how), delete the imported furniture (its script nodes are never run; the plugin's vaccine
  sweep runs over what came in), give the tab a copy of the current workspace, switch to
  it.
- **New** (the bar's «+» > Empty tab, or File › New while tabs exist): an empty tab named
  `untitled`, `untitled1`, ...; its first Save asks for a path.
- **A file holding a `skeldarSceneTabs` node** (a recovered session) opens as a session:
  its tabs are rebuilt from the node instead of being nested in a tab.
- **Save** (Ctrl+S, File › Save, the tab's menu; a non-active tab is switched to first):
  1. the session's unit is the tab's (it is, while active);
  2. the tab's own nodes renamed into the root namespace by UUID, its top-level
     references moved by `file -edit -namespace`, its child namespaces moved to the root,
     its layer root disconnected from the session root - a name clash with the root
     namespace refuses by name and puts everything back;
  3. a `sceneConfigurationScriptNode` written with the tab's `playbackOptions` (min, max,
     ast, aet) and exported with it;
  4. `exportSelected -preserveReferences` to `<file>.skeldartmp`, then `os.replace` onto
     the file - a failed save leaves the file as it was;
  5. in a `finally`: every name, namespace, reference and layer parent back by UUID; the
     whole save runs unrecorded (it nets to nothing; trap 145: not inside a chunk).
  If the file's mtime changed since the tab opened or last saved, ask first («changed on
  disk since you opened it - overwrite?»).
- **Save As** (File › Save As, the tab's menu): the same to the chosen path; the tab takes
  the new path and name. The `kBeforeSaveCheck` callback tells Save from Save As by the
  scene name Maya is about to write (the session's own name -> Save; another -> Save As,
  the session renamed back after) and lets an AUTOSAVE through (its path is in the
  autosave folder; the plan measures how the callback sees it).
- **Close** (×, middle click, the tab's menu): a modified tab asks Save / Don't Save /
  Cancel; then its references are removed, its namespace deleted with its content
  (unlocking what is locked, trap 158), its layer root and workspace deleted; an active tab
  hands over to its right-hand neighbour first.
- **Quit**: an event filter on Maya's main window close asks about modified tabs (Save all
  / Discard / Cancel) before Maya does, then marks the session unmodified so Maya does not
  ask to save the session.
- **Tabs off** (the bar's ⋮): asks about the other tabs, closes them, converts the active
  one back to an ordinary scene.

## Switching

One undo chunk `skeldarTabSwitch` (measured: one Ctrl+Z restores it), in this order:

1. **record the tab being left**: its modified flag (`file -q -modified` or'ed in, then
   the flag cleared), current frame, persp camera matrix and focal length, the model
   panel's display flags (a whitelist: displayAppearance, displayTextures, displayLights,
   shadows, joints, nurbsCurves, polymeshes, locators, cameras, grid, isolateSelect), its
   selection by UUID, its workspace (`workspaceLayoutManager -saveAs`);
2. **hide it**: `lodVisibility` 0 on its top DAG nodes (never `visibility`, which the
   animator keys) and `hiddenInOutliner` 1; whether the evaluation manager then skips it
   in a GUI Maya is measured in the plan (a standalone frame went 3.19 -> 0.07 ms with the
   rig hidden); if it does not, the `frozen` evaluator is used, its settings put back when
   tabs end;
3. **show the new one** and make its namespace current;
4. **its time**: `currentUnit -time <fps> -updateAnimation true` (keys keep their
   seconds), playback and animation ranges, current frame;
5. **its view**: persp matrix and focal length, the panel's display flags, its selection;
6. **its layout**: `workspaceLayoutManager -setCurrent` (GUI only); the bar and the hub are
   put back into it if the layout lacks them.

The bar follows Undo / Redo (scriptJobs) by reading the session node, so a Ctrl+Z past a
switch shows the tab it brought back. A failure inside a switch restores the recorded
state explicitly (never by `cmds.undo()`).

**New animation layers** made while a tab is active are parented under that tab's layer
root (an `MDGMessage` node-added callback on `animLayer`, the re-parent deferred one idle),
so a tab's file always gets its own layers back.

## The bar

A `workspaceControl` `skeldarSceneTabs`, docked above the viewport, one row high, Qt,
styled from `maya_hubstyle.TOKENS`:

- a tab: the file's stem, `*` when modified, `×`; the active one lit with the hub's
  accent; the tooltip the full path, fps and range;
- «+»: Open file..., the recent files (Maya's own list), Empty tab;
- click switches, middle click closes; the right button: Save, Save As..., Reload from
  disk (drops the tab's changes, asks), Show in Explorer, Close others;
- ⋮: Tabs off;
- the active tab's `*` follows `file -q -modified` on a 500 ms Qt timer;
- hotkey rows `tabs.next` / `tabs.previous` in the plugin's map (Ctrl+Tab / Ctrl+Shift+Tab
  if Maya leaves them free - the plan checks), `window.tabs` to show the bar.

## Modules

`SkeldarAnim/maya_scenetabs/` (a payload row):

| module | does | imports |
|---|---|---|
| `records.py` | the session JSON, namespace naming, the unit from a `.ma` header, a tab's ranges, the save plan | stdlib only (a subprocess test) |
| `session.py` | the session node, read / write, active tab, tab-mode on / off, convert to / from a tab | `cmds` |
| `opening.py` | open, new, close, reload, recovered sessions | `cmds`, `session` |
| `switching.py` | the switch chunk, hide / show, time, view, layout | `cmds`, `session` |
| `saving.py` | save / save as | `cmds`, `session` |
| `hooks.py` | the save / open / new check callbacks, the layer callback, undo / redo jobs, the quit filter | `cmds`, OpenMaya, Qt (lazy) |
| `bar.py` | the bar | Qt, `cmds` |

## Error handling

- Every refusal names what refused (a name clash, a file changed on disk, a locked node).
- A save never leaves a half-written file (temp then replace) and never leaves the scene
  renamed (`finally` by UUID).
- A switch that fails half way puts the recorded state back and says so.
- Batch mode (`cmds.about(batch=True)`) installs no callbacks and no bar.

## Not built

FBX files as tabs (Maya's import into the active tab stays), reference tabs (approach B),
undo isolated per tab, dragging tabs to reorder, render setup / render layers per tab,
the plugin seeing only the active tab (stage 2).

## Proof

- Unit tests on `records` (naming, the header unit, the session JSON round trip, the save
  plan) and on the bar's layout offscreen.
- `docs/superpowers/plans/verify_scene_tabs.py`, mayapy standalone, three tab files built
  by the script (the rig scene; a film scene with a nested reference, two animation layers,
  a display layer and a camera; a scene with no layers), each also saved as `.mb`:
  - open all three: names, references kept, layers evaluating, ranges and units read;
  - edits in each: keys on a control, a rig added with Add Character, a weapon, a new
    animation layer, a locator;
  - switches: visibility, outliner, unit, ranges, frame, camera, selection per tab;
  - undo across a switch restores the previous tab, then its step;
  - save each, open each file in a fresh Maya and compare with the original file plus the
    edits: every node name (no prefix), every key, layer tree and keys, references and
    their namespaces, display layers, unit, ranges;
  - a save refused by a name clash leaves the scene and the file untouched;
  - the check callbacks: Save, Save As, Open and New redirected, an autosave let through;
  - a recovered session (the session saved by the verify's own hand) rebuilds its tabs;
  - closing tabs down to one converts the last back to an ordinary scene.
- Live only (the animator's): the bar docked above the viewport, per-tab workspaces and how
  long a switch takes with them, the hidden tabs' cost in the viewport, the quit dialog.

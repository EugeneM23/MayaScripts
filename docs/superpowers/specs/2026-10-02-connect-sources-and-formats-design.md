# Connect: Unreal, Unity, a folder - and every format we can read (2026-10-02)

The animator, away for two hours («делай все самостоятельно ... пушить и делать сборку не нужно пока я не
проверю»): «Во вкладке Animation setup раздел с подключением к unreal engine нужно визуально как-то
отделить. Далее я бы хотел что бы у нас была возможность подключаться не только к анриал енжину а и к
Unity, и просто к папке с FBX файлами.......хорошо бы было сделать максимальный обхват форматов которые
мы можем прочитать и вытащить из них анимацию.» Every choice below was taken alone; each says why.

Built on `3606438` (the worktree branch had been cut from `main`, `496f719`; it was reset to the base
before any work).

## What was measured first

- **Unity Hub keeps its recent projects in `%APPDATA%/UnityHub/projects-v1.json`**: `{"schema_version":
  "v1", "data": {path: {"title", "path", "version", "lastModified", ...}}}`. Five projects on this
  machine, one listed twice (`c:\!!!Work\Missile...` and `C:\!!!Work\Missile...`).
- **The Lugal project (`C:/!!!Work/work`)**: 1606 FBX, 1599 `.fbx.meta` (949 with a `clipAnimations`
  list - `name`, `takeName`, `firstFrame`, `lastFrame`), 145 `.anim` (88 Humanoid muscle clips with
  `attribute: RootT.x`; the generic ones mostly props - and one real skeletal clip,
  `Recon Troop/Model/TwoHandGunFireStanding.anim`, 620 KB, `m_RotationCurves` by path `Bip01/Bip01_Pelvis`,
  old-style numbers `.407678992`, with `mReconTroop.fbx` beside it).
- **FBX takes** (mayapy 2027): `FBXRead -f` + `FBXGetTakeCount` + `FBXGetTakeName i` +
  `FBXGetTakeLocalTimeSpan i` - the index is POSITIONAL (`-n i` answers «Use syntax»), spans are in the
  scene's frames, and the read is lazy: 1-3 ms a file (2 MB), the whole Lugal project's 1854 model
  rows in 4-5 s. An FBX written with two `FBXExportSplitAnimationIntoTakes` takes reads as THREE
  (`Take 001` whole, then the two). `FBXImport -f ... -t i` imports one take - **looked up in the file
  READ LAST** (trap 159?).
- **Collada**: the FBX plugin's `DAE_FBX` reads and writes it; `FBXImport` of a `.dae` brings keyed
  joints into the current namespace; `FBXGetTakeCount` answers 0 for it. **Maya's DAE writer resamples
  onto 24 fps** whatever the scene's rate (keys 1.25 frames apart at 30 fps) - a DAE from Maya is lossy
  between its keys (trap 160?).
- **USD**: mayaUsd's `mayaUSDImport(file, readAnimData=True, primPath="/")` brings a UsdSkel skeleton
  in as keyed joints honouring the current namespace (93 joints, 837 curves, 0.09 s). Exporting one
  needs a group above the root (`mayaUSDExport` refuses a root prim as SkelRoot) and takes no
  `animation` flag (`frameRange` is it).
- **Maya .ma/.mb**: `file -i -namespace ... -executeScriptNodes false` brings the clip in; a script
  node in the file arrives (and is deleted by us) without having run.

## The design

### The block (task 1)

The connection rows in Animation Setup are ONE block set into the card (`window.build_rows`):
`ueAnimBridgeInset`, a `columnLayout` marked with the new hub role **`inset`**
(`maya_hubstyle.ROLES`, tokens `inset` #232529 / `inset_line` #3a3c42: a step darker than the card, a
1 px hairline, radius 8). A plain QWidget paints no stylesheet background, so `maya_hubqt._apply_mark`
sets `WA_StyledBackground` on it and pads its layout 8 logical px. The classic hub gives the column a
background of its own (`INSET_CLASSIC_BG`, `hubstyle.pick`). Inside, top down: the heading **Connect**
(was «UE Connect» - it is no longer Unreal only), the source switch, the source's line, the dropdown +
Refresh, search, the list, `Import [Onto selected | New]`, the timeline box, Import Animation, the two
exports. The card's one status line stays OUTSIDE the block.

### Sources (task 2)

`[Unreal | Unity | Folder]` segments (`ueAnimBridgeSource_<source>`), remembered in the optionVar
`ueAnimBridgeSourceKind`; each file source remembers its last place (`ueAnimBridgeLocation_<source>`)
and its recent places (`ueAnimBridgeRecent_<source>`, JSON).

- **Unreal**: exactly as before (editors, cache in userPrefDir, the editor's export, Export to uasset).
- **Unity**: the dropdown lists Unity Hub's projects (`unityfiles.hub_projects`, one per folder, newest
  first; «open» when `Library/EditorInstance.json`'s pid is alive - no other process's command line is
  read), then projects browsed to, then **Browse...**. Refresh scans `<project>/Assets`: a model file
  (`.fbx`, `.dae`) gives one row per clip its `.meta` defines (`take_name`, `first`, `last` - cut out of
  the take on import), else one per take; a meta with `importAnimation: 0` is skipped; a `.anim` gives
  one row (Humanoid / compressed rows are listed, marked, and refuse on import by name).
- **Folder**: the dropdown lists the folders browsed to (name + the path's tail - a whole path widened
  the block to 682 px) and **Browse...** (`fileDialog2 -fileMode 3`). Refresh scans it recursively
  (`Library`, `Temp`, `.git`... skipped).

A scan runs under a cancellable `progressWindow` and is cached as JSON in the temp folder
(`sources.cache_name`: one file per source and place), so opening the card costs nothing; a cancelled
scan is shown but not cached. Rows say which file/clip they are: a whole file is its NAME with the
extension (`thrust.bvh`, `thrust.dae` - six formats of one clip must read apart), a take
`pack.fbx · jump`, a Unity clip its own name; after the length the format and any reason it will not
import (`31 fr  anim  humanoid`).

**One funnel, no road of its own.** `records.AnimRecord` gained `source`, `path`, `clip`, `fmt`
(defaults = an Unreal asset, so every positional constructor and every old cache still reads). Every
road calls `window._export_from_editor(record)`: an Unreal record is exported by the editor as before
(`_export_unreal`), a file record answers its **clip reference** (`sources.record_ref`: `C:/a/x.bvh`,
`C:/a/p.fbx|take=2`, `C:/a/x.glb|anim=0`, `C:/u/Bow.fbx|first=0&last=5&take_name=Take+001` - `|` cannot
be in a Windows path). `rigimport.import_source` - the funnel the button, the double click, the drag,
`skeletonimport` and `lineimport` all use - sends a plain FBX to `animimport.import_clip` exactly as
before and anything else to `formats.import_clip`, which leaves the scene in the same shape (a namespace
holding a keyed joint skeleton; info with `namespace`, `joints`, `start`/`end`, `fps`, `warning`). So the
retarget onto a rig, the transfer onto a skeleton and the square of several needed no edit at all.
`file_refusal` refuses a Humanoid / compressed / unreadable / vanished file's row BEFORE anything is
imported or added. **Export FBX...** works whatever the source; **Export to uasset** is disabled for
Unity and Folder and refuses by name if reached.

### Formats (task 3)

| format | listed by | imported by |
|---|---|---|
| FBX | `formats.fbx_takes` (FBXRead): one row a take | `animimport.import_clip(take=)`; a Unity clip trimmed to its frames (keys inserted on both edges, the rest cut) |
| Collada .dae | one row a file | the FBX plugin (`animimport.import_clip`) |
| Maya .ma/.mb | one row a file | `file -i -namespace -executeScriptNodes false`; every script node that arrived deleted |
| USD .usd/.usda/.usdc/.usdz | one row a file | `mayaUSDImport(readAnimData=True)` in the namespace |
| BVH | `bvh.parse` (joints, frames, fps) | our parser + `formats.build`: channels' own rotation order (listed `Z X Y` = Maya `yxz`), position channels over the offset, end sites skipped |
| glTF .gltf/.glb | `gltf.clips`: one row an animation | our parser: skins' joints + ancestors, rest TRS as jointOrient, LINEAR (slerp) / STEP / CUBICSPLINE at the union of the keys, metres x100, data URIs, normalized accessors |
| Unity .anim | `unityfiles.anim_summary` | generic clips: Hermite curves sampled at `m_SampleRate`; onto the model beside it (same folder up to 3 parents, never above `Assets`, and only its own folder outside a project) whose bytes name 90 % of the clip's bones - `rotate = RA⁻¹·Q·JO⁻¹`, translate by the measured units; with no model, bones stood on the clip's own positions (all must have one) |

`formats.build` makes the joints and writes keys through `MFnAnimCurve.addKeys` (linear tangents),
times in SECONDS so a clip plays at its own speed whatever the scene's rate; a clip whose rate differs
from the scene's says so («a 30 fps clip on the 24 fps timeline: keys at its own times») - the bridge
never writes the scene's rate. Unity is left-handed: `to_maya_position (-x, y, z)`, `to_maya_rotation
(x, -y, -z, w)`, Unity eulers applied Z, X, Y.

**Considered and dropped**: Acclaim ASF/AMC (CMU ships BVH conversions; a second mocap text format for
nobody here), OBJ / 3DS / Alembic point caches (no skeleton), `.blend` (needs Blender), `.max` (needs
3ds Max), Unity Humanoid muscle clips (only Unity's avatar can turn muscles into bones - refused with the
way out: export FBX from Unity), compressed `.anim` (Unity's private encoding - refused).

## Decisions taken alone

1. The heading is «Connect» (it reaches Unity and a folder now).
2. The Unity source reads projects OFF THE DISK - no editor plugin, nothing written into a project. An
   «open» project is the one whose `EditorInstance.json` pid lives.
3. A Unity model's clips come from its `.meta`; with none, its takes; the clip's `firstFrame..lastFrame`
   are taken as the scene's frames after the FBX import (trap 80: the importer switches the scene to the
   file's rate).
4. A file's clip reference rides the existing `(path, fps)` of every road; `_export_from_editor` stays
   the one front door (its name kept: tests and every road patch or call it).
5. Times in seconds for our own builders; the scene's rate untouched.
6. glTF rest = the nodes' TRS (not the inverse bind matrices); BVH rest = zero rotations; jointOrient
   carries the rest so rotate reads 0 there (a Mixamo-style "rotates at 0" rest).
7. BVH end sites are not joints (they animate nothing).
8. Whole-file rows are named with the extension.
9. A row that cannot import is still LISTED, marked, and refuses on press.
10. Scans are cached per source and place in the temp folder; Unreal's cache stays where it was.

## Proof

- `docs/superpowers/plans/verify_import_sources.py` - **27/27 in mayapy standalone** since the fix
  review (19/19 before it; scratch
  `MAYA_APP_DIR`): `ShortSword_Attack_Thrust_3P.FBX` (92 joints, 0..36 at 30 fps; its 270 scale curves
  removed from the reference - BVH cannot carry scale) written out as a two-take FBX, DAE, USD, `.ma`
  (with a script node), BVH, GLB and two Unity `.anim` (one beside a model, one alone), each read back
  through the REAL funnel and every joint's world matrix compared over the frames, with a frame-off
  positive control that must fail (34-175 cm):
  - FBX take 2 / take 3: **0.000000 cm, 0.000004°** (19 frames each, on the original frames);
  - USD **0.000018 cm**; `.ma` **0.000000 cm** (its script node deleted, never ran); BVH **0.000090 cm,
    0.000147°**; glTF **0.000033 cm**; Unity on its model **0.000000 cm**; Unity alone **0.000000 cm**;
  - DAE **0.000527 cm at the file's own key times** (Maya's writer resamples onto 24 fps, trap 160?);
  - a Humanoid clip refused by name; the REAL Unity clip - since the fix review against Unity's OWN
    data (below): `TwoHandGunFireStanding.anim` is Unity's copy of `mReconTroop.fbx`'s clip
    `TwoHandGunIFirestanding`, and the two roads agree on **36 of 37 bones within 0.6° and 0.05 cm on
    every one of 40 frames** (worst 0.500°, 0.030 cm - Unity's keyframe reduction's own 0.5°), the 37th
    (`Bip01_Spine2`) a constant **20.000° at every key**, an edit made on the copy; only the X mirror
    lands the first frame (36/37; the Y mirror 0 of the 22 bones where it differs, Z and none 0 of 37);
  - the folder lists 11 rows of 7 formats in 0.06 s; the Lugal project **1975 rows in 4-5 s** (1854
    model clips, 81 generic + 40 humanoid `.anim`), e.g. «Aim Bow» `first=17.8&last=40&take_name=Take 001`;
  - the roads end to end: the BVH onto a NEW Manny rig (`hand_r` travels 251.1 cm, the clip's namespace
    gone); the GLB onto a new Manny UE5 skeleton («91 bones exact», no namespace left); an FBX take, the
    DAE and the USD at once through `lineimport.run` - **3 new rigs in a 2 x 2 square**, each animated,
    no clip namespace left.
- A disposable GUI Maya (port 7061, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, minimized, killed by its
  PID after): the hub floated at the animator's dock (viewport **510**), the content's minimum **504**
  with Unreal / Unity, **431** with the folder (after the dropdown's labels were cut to a tail - 682 px
  before); the switch clicked through Qt; Unity Hub's projects in the dropdown, the Lugal project
  scanned in **3.9 s** (1975 rows), «bow aim» 39 of them; the verify's folder scanned and a BVH row
  imported with **Import Animation** onto a new Manny rig in **4.8 s** («thrust retargeted onto
  Manny_Rig ... source skeleton thrust deleted»). Pictures: `docs/superpowers/plans/
  connect_block_unreal.png`, `connect_block_unity.png` (the whole card), `connect_block_folder.png`.
- Unit tests: **3564, OK** (3507 before: 57 new - `tests/test_uebridge_sources.py`, the window's
  file-source tests, the press's failed-import test; `test_hub_sections`,
  `test_uebridge_window` updated: the heading, the one inset column, the source segments).

## Fix review (2026-10-02, the same day)

An independent review found nine things; each was read in the code and, where cheap, run.

1. **Refusals came after the press had added a rig** - fixed. For Unreal every clip-level failure
   happened in the editor's export, before the scene was touched; for a file the real refusals
   (a Unity clip with no model and no positions, a glTF with no skeleton, a take not in the file) were
   raised inside `formats.import_clip`, after `ready_rig` had added a 9.5 s Manny. Now
   `formats.check(ref)` reads the file again for every one of them and `window._export_from_editor`
   refuses with it (`window._clip_check`), so the button, the double click, the drag, the square of
   several and the skeleton roads all refuse before anything is added; the pure rules live in
   `sources` (`take_refusal`, `anim_refusal`, `gltf_refusal`, `find_take`), and the import raises the
   SAME sentence (`_import_unity_anim` goes through `anim_refusal`). And whatever still fails inside the
   import (a USD stage, a reader) is taken back: `rigimport.import_and_retarget` removes every namespace
   the import left and DELETES the rig the press added (`_undo_failed_import`, through
   `maya_scenesetup.deletion`), and the line says «A could not be imported: ... - the rig it added and
   the clip were removed». A rig already standing keeps its place (its take was cleared by the reset,
   as any import's is). Gates 13, 14, 54, 55.
2. **A whole-saved `.ma` left its scene behind** - fixed, and measured first: a scene saved with
   mayaUsd loaded carries `createNode UsdDefaultSettings -n "UsdDefaultRenderSettings"`, it imports
   LOCKED into the clip namespace, and `namespace -rm -deleteNamespaceContent` raised «is locked, can not
   remove it». `formats.tidy_scene_import` unlocks what the import locked and deletes that settings
   node (`SCENE_FURNITURE`); `formats.remove_namespace` (unlock, delete, the trap-158 managers merged to
   the root) is what the failed-import path uses. Gate 53: a .ma saved WHOLE onto a new rig, retargeted,
   no namespace left.
3. **A Unity clip whose `takeName` is not in the FBX imported the default take in silence** - fixed:
   refused by name («Bow.fbx: take 'mixamo.com' is not in the file - it holds Take 001, first,
   second»), by the check and by the import. Gate 13.
4. **A file with one moving take among several was a plain-path row**, which imports the file's DEFAULT
   take (a still `Take 001` beside the real one would bake a still pose) - fixed: such a row names its
   take (`take=2`); only a file of ONE take stays a plain path. Unit-tested (a file with a still default
   take could not be written with Maya's split-take export, whose `Take 001` is always the whole clip).
5. **The model under a Unity clip came in with its own take** - fixed, and it was real on the very model
   the verify used: `mReconTroop.fbx` carries 333 curves, a pose up to 260° off its rest, and every bone
   the `.anim` does not key played that take. `formats.import_model_rest` imports the model with the
   plugin's `FBXProperty "Import|IncludeGrp|Animation" -v false` (0 curves, measured), set AFTER
   `_apply_import_options` (whose `FBXResetImport` turns it back on) and put back in a finally. Gate 18:
   37 keyed, the 7 bones the clip does not hold unkeyed.
6. **The Unity handedness was not proven** - fixed, the gate replaced: the old one wrote its `.anim` with
   the inverse of the same conversion (any error cancels) and passed the real clip on a MEDIAN. The real
   `.anim` is now compared with Maya's own import of the model clip it duplicates, every bone, every
   frame (gate 16, numbers above), and a positive control proves the gate can fail (gate 17: the other
   three mirrorings land 0 of the bones where they differ from ours; a bone turning about its own Z alone
   reads alike in the X and Y mirrors, which is why the old "share of all bones" read 41 % for Y).
   Positions: 0.030 cm worst over the 36 bones.
7. **Duplicate leaf names in `build`** - fixed: `_make_joint` finds the joint it made as the child that
   was not there before (`listRelatives` / `ls -assemblies` diff), never by `ls(<short name>)[0]`.
8. **The FBX plugin writes `<file>.fbm` beside the file it imports** - fixed, measured: importing a copy
   of the Creep's Cascadeur FBX made `creep_T-pose_draft.fbm` beside it. Every file of the animator's
   (a Folder FBX, a Unity model, a take) is now read from a copy in the bridge's temp folder
   (`sources.staged`: `%TEMP%/maya_uebridge/staged/<md5 of path, size, mtime>/<ascii name>`, reused
   while the original is unchanged); an Unreal export, already in that folder, is read as it is. Gate 15:
   our import leaves the source folder as it was, the plugin's own read of the original makes the
   `.fbm`. `FBXRead` (the scan) does not extract: the Lugal project, scanned four times today, holds only
   three `.fbm` folders, all from 2026-09-05.
9. **Switching back to Unreal dropped the live editor list, and `current_source()` answered "unreal"
   before the card was built** - fixed: the last Refresh's labels are kept (`_STATE["unreal_labels"]`)
   and restored with the choice; `_STATE["source"]` starts None and `current_source` falls back to the
   remembered switch (`ueAnimBridgeSourceKind`).

## Not done

- The drag from a Unity/Folder row was not driven with a real mouse (the drag code is the Unreal one,
  unchanged; it reads the same records and calls the same `import_dropped`).
- Takes are listed only with Maya's FBX plugin; a few Lugal files answered «FBXRead: Use syntax» (paths
  the MEL string could not carry) and list as one row without frames. Their IMPORT reads an ASCII-named
  copy since the fix review (`sources.staged`), so a take of such a file imports; the scan itself still
  reads the original (copying 1854 files to list them is not worth it).
- A failed import onto a rig already standing leaves that rig with its take cleared (the reset ran);
  only a rig the press ADDED is removed.
- Unity: `m_EditorCurves`-only and `m_CompressedRotationCurves` clips; a Unity clip's own root motion
  (path "") is ignored; `.blend`/`.max` models are not candidates.
- The Unreal road's own verify (`verify_uebridge_*`) was not re-run (no editor); its unit tests are green.

## CLAUDE.md section (draft)

## Connect: Unreal, Unity, a folder - and every format we can read (2026-10-02)

The animator, away for two hours: «Во вкладке Animation setup раздел с подключением к unreal engine
нужно визуально как-то отделить. Далее я бы хотел что бы у нас была возможность подключаться не только к
анриал енжину а и к Unity, и просто к папке с FBX файлами.......хорошо бы было сделать максимальный
обхват форматов которые мы можем прочитать и вытащить из них анимацию.» Every choice was taken alone;
spec `docs/superpowers/specs/2026-10-02-connect-sources-and-formats-design.md`.

**The block**: the connection rows are one column set into the Animation Setup card, `ueAnimBridgeInset`,
hub role **`inset`** (tokens `inset` / `inset_line`; `maya_hubqt` sets `WA_StyledBackground` - a plain
QWidget paints no stylesheet background - and pads it 8 px; the classic hub a `backgroundColor`). Top
down: the heading **Connect** (was «UE Connect»), **[Unreal | Unity | Folder]** (`ueAnimBridgeSource_*`,
remembered in `ueAnimBridgeSourceKind`), the source's line, the dropdown + Refresh, search, the list, the
Import target, the timeline box, Import Animation, the two exports. The card's status line stays outside.

- **Unreal** as before. **Unity**: Unity Hub's projects (`%APPDATA%/UnityHub/projects-v1.json`, one per
  folder - it lists one twice by drive-letter case; «open» = `Library/EditorInstance.json`'s pid alive),
  then browsed ones, then **Browse...**; Refresh scans `Assets`: a model's `.meta` `clipAnimations`
  (name, takeName, firstFrame, lastFrame) one row each, else one per take; `.anim` one row, Humanoid /
  compressed listed and marked. **Folder**: remembered folders (`ueAnimBridgeRecent_folder`) and
  Browse...; Refresh scans recursively, skipping `Library`/`Temp`/`.git`. Scans run under a cancellable
  progress window and are cached in the temp folder per source and place (`sources.cache_name`).
- **One funnel**: `records.AnimRecord` gained `source, path, clip, fmt` (defaults = Unreal). Every road
  calls `window._export_from_editor`; a file record answers a **clip reference** (`C:/a/p.fbx|take=2`,
  `x.glb|anim=0`, `Bow.fbx|first=0&last=5&take_name=Take+001`), and `rigimport.import_source` sends a
  plain FBX to `animimport.import_clip` as always, anything else to `formats.import_clip`, which leaves the
  same shape (a namespaced keyed skeleton + info). Retarget, skeleton transfer, the square of several and
  the drag needed nothing. Export to uasset is Unreal's only; a row that cannot import refuses on press.
- **Formats** (`maya_uebridge/formats.py`, readers `bvh.py`, `gltf.py`, `unityfiles.py`, scan rules
  `sources.py` - the last four stdlib): FBX takes (`FBXRead` + `FBXGetTakeName i`, positional; `FBXImport
  -t i`), Collada and FBX through the FBX plugin, `.ma/.mb` imported with script nodes not run and
  deleted, USD by `mayaUSDImport(readAnimData=True)`, BVH / glTF / Unity `.anim` by our parsers and one
  builder (`formats.build`: `MFnAnimCurve.addKeys`, times in SECONDS, the scene's rate untouched and a
  difference said). BVH's listed `Z X Y` is Maya's `yxz`; glTF rest TRS is the jointOrient, metres x100;
  Unity is left-handed (`(-x, y, z)`, quaternion `(x, -y, -z, w)`) and a generic clip lands on the model
  beside it (never above `Assets`) found by its bones' names in the file's bytes.

- **Refused before the press** (the fix review): `formats.check(ref)` reads the file again for what
  its import would refuse - a take not in it (or the default take would come in silently), a Unity clip
  with no model and no positions, a glTF with no skeleton - and `window._export_from_editor` raises it,
  so no road adds a rig first; what still fails inside an import is taken back
  (`rigimport._undo_failed_import`: the clip's namespaces, the rig the press added). A file with one
  moving take among several names its take. A whole-saved `.ma`'s locked `UsdDefaultSettings` is
  unlocked and deleted (`formats.tidy_scene_import`). A Unity model comes in with NO take of its own
  (`formats.import_model_rest`). Every file of the animator's is read from a COPY in the bridge's temp
  folder (`sources.staged`): the plugin writes `<file>.fbm` beside what it reads.

Proof: `docs/superpowers/plans/verify_import_sources.py` **27/27 standalone** - a UE 3P clip written as
a two-take FBX, DAE, USD, `.ma`, BVH, GLB and two `.anim`, read back through the real funnel against
every joint's world matrix with a frame-off control (34-175 cm): FBX takes 0.000000 cm, USD 0.000018,
`.ma` 0.000000 (its script node never ran), BVH 0.000090, glTF 0.000033, Unity 0.000000, DAE 0.000527 at
its own key times; the real `TwoHandGunFireStanding.anim` against Maya's own import of the model clip
it is Unity's copy of - 36 of 37 bones within 0.6° / 0.05 cm on all 40 frames, the 37th a constant
20.000° at every key (an edit on the copy), and only the X mirror landing (the others 0 of the bones where
they differ); refusals before the press (no rig added) and after it (the added rig removed, 3.8 s); a
whole-saved `.ma` retargeted with its namespace gone; no `.fbm` beside a source file; the Lugal project listed (1975 rows, 4-5 s); a BVH onto a new Manny rig,
a GLB onto a new Manny UE5 skeleton, an FBX take + DAE + USD at once in a 2 x 2 square, every clip
namespace gone. A disposable GUI Maya (port 7061): the card at the dock's 510 px viewport, content 504 /
431, the Lugal project scanned in 3.9 s, a BVH imported from the folder onto a new rig in 4.8 s; pictures
`connect_block_unreal.png`, `connect_block_unity.png`, `connect_block_folder.png`. 3564 unit tests.

159?. **`FBXImport -f file -t i` looks the take index up in the file the plugin READ LAST**, not in
     `file`. After a scan had `FBXRead` other files, `-t 2` answered «FBXImport error: take not found»
     on a file that has three takes. Read the file again (`FBXRead -f`) right before a take import. And
     `FBXGetTakeName` takes the index positionally: `FBXGetTakeName -n 1` is «Use syntax».
160?. **Maya's Collada writer resamples onto 24 fps whatever the scene's rate**: a 30 fps clip came
     back with keys 1.25 frames apart, exact at its own key times (0.0005 cm) and up to 165 cm off
     between them (an euler flip a resample put between two keys). A DAE from Maya is lossy; judge a
     reader of it at the file's own key times.
161?. **A verify's `write_glb` returned its loop variable**: `for key, path, kind in ...` inside a
     function whose argument is `path` wrote the file as `./rotation` and returned "rotation" - the
     verify then found no GLB. Never reuse an argument's name as a loop variable.
162?. **A model search that climbs folders left the sandbox**: a clip "alone" in `%TEMP%/.../alone`
     climbed into `%TEMP%` and took another tool's `skeldar_inventory_export.fbx` as its model (it named
     the bones). A search for a sibling file stops at the project's `Assets`, and outside a project looks
     in its own folder only.
163?. **The scratchpad is shared between parallel agents**: another agent's `probe1.py` replaced this
     one's between two runs. Each agent works in a folder of its own inside it.
164?. **A whole-saved `.ma` carries mayaUsd's `UsdDefaultSettings`, and it imports LOCKED into the
     clip's namespace**: `namespace -rm -deleteNamespaceContent` then raises «is locked, can not remove
     it» and the clip's whole scene stays behind (measured 2026-10-02, trap 158's family from the import
     side). Unlock what an import of a scene brought, and delete its furniture, before the namespace goes.
165?. **`FBXResetImport` turns every `FBXProperty` back to its default**, so an option set before a
     helper that resets (`animimport.import_clip` does) is lost silently: the model under a Unity clip
     kept importing its 333-curve take with `Import|IncludeGrp|Animation` set false just before. Set it
     AFTER the reset, and put it back in a finally - it is session-wide.
166?. **`FBXImport` extracts a file's embedded media into `<file>.fbm` beside the file** (a folder in a
     Unity project's Assets, which Unity then imports); `FBXRead` does not. Read a file you do not own from
     a copy.
167?. **A gate that writes its own input with the inverse of the conversion it tests cannot fail**, and
     a mirror control that counts every bone cannot either: a bone turning about its local Z alone reads
     the same under Unity's X and Y mirrors (41 % "landed" for the wrong one). Prove a conversion against
     the other program's own output (Unity's copy of a model clip against Maya's import of that take),
     and count a control only where the candidates differ.

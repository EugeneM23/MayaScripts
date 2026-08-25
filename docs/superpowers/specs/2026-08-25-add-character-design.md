# Add Character — the working skeleton and geometry on one button

**Date:** 2026-08-25
**Status:** approved by the user in advance («сделаем точно такую же кнопочку
как и для меча, только Add Character... просто будет в сцену вставляться
персонаж»); designed and implemented autonomously on their instruction to
carry the task to the end.

## The problem

Every working session starts the same way: the animator opens
`C:/!!!Work/Animations/Rigs/Characters/Manny_Sckeleton.ma` (the typo is in
the real filename) to get the working character — the UE5 Manny skeleton,
its geometry, and the camera bone. The user asked for a button in Scene
Setup that does it: press Add Character, the character is in the scene.

Their explicit calls, all honoured here:

- a button exactly like the weapon's Add, labelled **Add Character**;
- the character is **inserted into the current scene** — not opened over it;
- the file ships **the same way as the sword**: a copy in the repo's
  `assets/`, resolved shipped-copy-first («разместим таким же образом как и
  оружие в исходниках плагина»);
- distribution concerns (52 MB in git, whose copy is canonical) are
  deferred — «в будущем подумаем что с этим делать».

## What is in the file — measured, not assumed

`Manny_Sckeleton.ma`, Maya ASCII, 52 MB, 1,196,699 lines:

- `SKM_Manny_Simple` — the geometry group, 6 mesh transforms, lamberts,
  dead texture paths (`D:/dev/temp/...`) that nothing here needs;
- `root` — the skeleton, **93 joints**, including `camera_root` →
  `camera_bone` (inside the skeleton subtree in this scene);
- `bindPose2` — the dagPose the rig tooling depends on;
- `camera1`, `materialXStack1`, 8 animCurves, the usual ui/scene
  configuration script nodes;
- **the "vaccine" malware**: script nodes `vaccine_gene` and `breed_gene`
  (lines 1165025–1165038, 14 lines, zero connections to anything). On scene
  open they write a `userSetup.py` into the user's prefs and hook
  `SceneSaved` so every save re-infects the file. This is the malware
  already on record for this studio's Manny scenes.

## Decisions

### The shipped copy is the file with the malware cut, and nothing else

`assets/Manny_Skeleton.ma` (typo fixed in our copy — the user flagged it) is
the source file with exactly the 14 malware lines removed, byte-identical
otherwise. Verified safe: the two script nodes have no `connectAttr` lines
anywhere in the file.

**Textual cut, never a Maya round-trip.** A `mayapy` open-and-resave would
have to load `mtoa`, `mayaUsdPlugin`, `stereoCamera` and `materialxStack`
(all in the file's `requires` list) or risk mangling their nodes on save —
and opening executes script nodes unless the flag is remembered. Deleting
fourteen unconnected lines is lossless by construction.

Everything else stays: `camera1`, the materialX stack, the ui-config nodes.
The user curates the source scene; the tool does not editorialize. Malware
is the one cut because it is malware.

### Import, not open — and no namespace

`cmds.file(path, i=True, type="mayaAscii", returnNewNodes=True,
ignoreVersion=True)`. Import never executes script nodes and never touches
the open scene's content. Not FBX, so traps 22/33 do not apply — but
`returnNewNodes` is still the point: it feeds the status count and the
malware sweep. No namespace, deliberately: the UE bridge merges clips onto
this skeleton by **plain bone names**, and a namespace is exactly what stops
the names matching (the same rule as the bridge's own import).

### Refuse when a skeleton is already in the scene

Guard: `builder.character_roots()` non-empty → refuse, naming the root
found. Importing over an existing `root` makes Maya rename the incoming
skeleton (`root1`, `pelvis1`, ...) — a second character that the picker and
the UE bridge then refuse to guess between, in a scene that looks fine.
Nothing happening is the safe direction of failure, and the status line
says why. This also makes a second press idempotent-by-refusal.

### The malware sweep at import time

After the import, any **imported** script node whose leaf name contains
`vaccine` or `breed` is deleted and named on the status line. The shipped
file is clean, so in the normal case this matches nothing. It exists for
two real paths: the legacy fallback imports the user's **original infected
file** on a machine that predates `assets/`, and some day someone re-exports
the character from an infected working scene and swaps it into `assets/`
without reading this spec. The sweep only looks at nodes this import
created — it never deletes anything that was already in the scene.

### Path resolution mirrors the sword

`catalog.character_path()`: `<container>/assets/Manny_Skeleton.ma` first
(true in the repo and an installed copy alike), the user's legacy absolute
path — original spelling, `Manny_Sckeleton.ma` — as fallback. Forward
slashes, like every path in `catalog`. `assets` is already a whole-directory
entry in the installer's `_PAYLOAD`, so the character rides the SkeldarAnim
install with no installer change.

### Module boundaries

| Piece | Home | Why |
|---|---|---|
| `character_path()` | `catalog.py` | stdlib-only path policy, same as `_sword_path` |
| `scene_type`, `refusal`, `malware_nodes`, `added_message` | `character.py`, pure | testable without Maya |
| `add_character()` | `character.py` | the one `cmds`-touching action |
| the button + callback | `window.py` | through `_run` (trap 20), `refresh()` after so the bound header catches up, status written last so the outcome stays visible |

The button sits at the top of the window, above the weapon row — the
workflow is character first, weapon second, camera third. After a
successful add the scene holds exactly one skeleton, so the header binds to
it on the same refresh (`skeleton.current_root()` → lone-skeleton rule).

## Not built, deliberately

- No character dropdown/table — one character exists. The catalog grows a
  table the day a second one does (YAGNI; the sword's `Weapon` tuple shows
  the shape it would take).
- No teardown/Remove Character — deleting a character is a normal Maya
  delete; nothing of ours hangs on it.
- No timeline or frame-rate handling — the file is a bind-pose scene
  (8 animCurves, none that matter); import does not execute its
  sceneConfiguration node either way.
- No re-pointing of the dead texture paths — the lamberts render grey
  regardless, which is what the user works with today.

## Verification

- Unit: path resolution (shipped/legacy/slashes), the pure helpers, and a
  scan pinning that the **shipped asset contains no vaccine strings** — so
  the sanitize cannot silently regress if the file is ever replaced.
- Live (`docs/superpowers/plans/verify_add_character.py`): in the user's
  Maya through the bridge. If the scene is empty of skeletons: real
  `add_character()`, gate root/93 joints/meshes present, no malware nodes
  scene-wide, exactly one `character_roots()`, second press refuses, then
  delete the imported nodes so the scene is left as found. If the scene
  already holds a skeleton: gate the refusal live (scene untouched) and
  skip the import gates, reporting so.

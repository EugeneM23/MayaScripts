# The AdvancedSkeleton pipeline: rig in, clip in, retarget, bake, done

**Date:** 2026-09-07
**Status:** approved by the animator in conversation («Делай все до конца»);
decisions below that they did not rule on explicitly are marked *(our call)*.

## The ask, in the animator's words

> Давай пока отключим все что связано с over rig и полностью перейдем на наш
> риг и ретаргет адванцед скелетон. Отключаем пикер пока он не нужен (но
> оставь его где-то, удалять не нужно из проекта). Bridge — import onto the
> skeleton давай поменяем на автоматический импорт нашего рига + импорт
> выбранной анимации потом ретаргет, бейк анимаций на ретаргет и удаление
> скелета с которого взяли анимацию. Опция as new skeleton делает импорт
> только скелета так же как и сейчас. Уберем весь функционал по работе с
> перфорсом. Сделаем одно окно для всех действий. Scene setup — рисуем
> шестеренку вместо меча. Add character теперь должен добавлять наш
> адванцед скелетон риг; чистые скелеты UE5 и UE4 оставим, но пометим их
> как скелеты, а риг как риг. Add weapon должна добавлять оружие к
> персонажу — какой персонаж рабочий понимаем по выделению: достаточно
> выделить любой контрол. Если у персонажа уже есть оружие — перекинуть
> анимацию на weapon bone, удалить старое и добавить новое. Connect arms /
> disconnect arms / add aim — убираем. Camera setup кнопку убираем, сам
> сетап должен происходить в момент ретаргета. Retarget — кроме ретаргета
> на риг переносим анимацию weapon bone (левой и правой) и camera root /
> camera bone, и выполняем camera setup. Бейк — через нашу кнопку Bake.

Answered on the way: the rig file is **final** (`Manny_rig_02.ma`, saved
2026-09-05 17:44) and goes into `assets/` as a shipped copy (variant A);
everything else «я потом проверю» — build to the end, no checkpoints.

## What the animator gets

A SkeldarAnim shelf of nine buttons — **UE Bridge, Scene Setup, Retarget,
Bake, Overshoot, Hotkeys, Studio, Colour, Curves** — and no OverRig anywhere
on it. One UE Bridge window. Scene Setup with a gear icon whose Add
Character puts the AdvancedSkeleton rig into the scene, whose Add Weapon
finds the character from whatever control is selected, and without the
four OverRig-era buttons. And one press in the bridge that goes from an
AnimSequence in the running editor to a baked take on the rig, sword and
camera included, source skeleton gone.

## Decisions

### One rig per scene *(our call, recommended and not contested)*

Both retarget modules address the rig by NAME — `Main`, `ControlSet`,
`|Group`, `FKWrist_R` — and Maya uniquifies every one of those on a second
import (`Manny_Rig_Group`, `FKWrist_R1`). Supporting several rigs means
rewriting both modules onto paths from a selected control and a live proof
on two rigs; the animator's working loop is one rig plus clips. So: Add
Character with the rig entry **refuses while a rig stands** (`ControlSet`
and `Main` both exist) and says so; the bridge adds a rig only when the
scene has none; plain skeletons (UE5, UE4) stay unlimited as before.

### OverRig and the picker are switched off, not removed

`SkeldarAnim/skeldar_features.py`, stdlib-only, two booleans:

```python
OVERRIG = False   # the OverRig shelf button and its 84 hotkey rows
PICKER = False    # the Rig Picker button, its 6 hotkey rows, and connecting
                  # a freshly added character to it
```

Read by `install.button_specs`, `maya_hotkeys.COMMANDS`,
`character.connect`, and the two `picker_root()` fallbacks
(`maya_scenesetup.skeleton`, `maya_uebridge.animimport`). Every module,
test and verify script of `maya_overrig` stays in the repo and in the
payload; flipping a flag brings the buttons back. The animator's own words
were «оставь его где-то, удалять не нужно».

### The retarget lives in the plugin

`maya_asretarget.py`, `maya_pmretarget.py` and `maya_rig_retarget.py` move
from the repo root into `SkeldarAnim/` (payload rows). Reasons: the shelf
buttons for them have to be the installer's, not the animator's hand-made
`shelfButton9`/`shelfButton32` that every re-drag wipes (CLAUDE.md already
records that cost); the bridge automation imports them; and a colleague
receiving the zip gets the retarget at all. `maya_pmretarget.ASSETS` is
corrected from `<dir>/SkeldarAnim/assets` to `<dir>/assets` — it assumed
the repo root. The three verify scripts' `sys.path` lines follow. Tests
import the modules by name and need no change.

### The bake is ours, on the vendor's contract *(our call)*

`bake()` in both modules ran `mel.eval("asMoCapMatcherBake;")`. That needs
AdvancedSkeleton sourced in the session — installed under the animator's
`Downloads/`, pressed from their Custom shelf, and absent on a colleague's
machine — so the bridge's IMPORT would die with `Cannot find procedure`
in a fresh Maya (trap 20's shape). The vendor's proc is eleven lines and
was read whole:

```
constraints = listConnections(MoCapConstraints.disableConstraints, s=0, d=1)
controls    = [listConnections(c + ".constraintParentInverseMatrix")[0] for c in constraints]
bakeResults -simulation true -t min:max -sampleBy 1 -disableImplicitControl true
            -preserveOutsideKeys false -sparseAnimCurveBake false
            -removeBakedAttributeFromLayer false -bakeOnOverrideLayer false
            -controlPoints false -shape false
delete -staticChannels -unitlessAnimationCurves false -hierarchy none -controlPoints 0 -shape 1
```

`vendor_bake()` in each module does exactly that in `cmds`, flag for flag,
and `disconnect()` was already native. Nothing of AdvancedSkeleton is
called at runtime any more; the rig itself is stock nodes (`matrixNodes`,
`quatNodes`, which interactive Maya auto-loads). The two modules stay
independent copies — `maya_pmretarget` imports nothing from its sibling
and a test pins it — so the helper is duplicated, deliberately.

### The Bake button does more than the bake

`maya_rig_retarget.bake()` — the dispatcher, which IS the shelf button —
becomes the whole "after the retarget" step:

1. the module's `bake(disconnect=False)` — controls keyed over the clip's
   key range, static channels dropped;
2. the **helper bones**: `weapon_r`, `weapon_l`, `camera_root`,
   `camera_bone` — for every one present in BOTH the source skeleton and
   the rig's game skeleton, the rig's bone is `parentConstraint`ed to the
   source's (no offset: same schema, same bind frames, and the rig's
   `hand_r` reproduces the source's to 0.0016 cm), baked over the same
   range with the camera module's flags, the constraint deleted, static
   channels dropped. A Mixamo source has none of them and the step says
   so; a target bone under somebody else's constraint is skipped by name;
3. a **weapon link** on `weapon_r`/`weapon_l` (`bonedrive.driving_weapon`)
   is unlinked before the transfer and relinked after it, exactly as the
   bridge's merge does — the sword snaps onto the new bone track and takes
   its stored grip back;
4. a **standing camera setup** is torn down before the transfer
   (`camera.teardown`, which bakes the bone back first) so the old
   camera's constraint does not fight the transfer's;
5. the module's `disconnect()`;
6. **Camera Setup** on the rig's `camera_bone` over the clip range
   (`camera.setup`), whenever the rig's skeleton has one. The Scene Setup
   button for it is gone; this is where it happens now.

The source root comes from the holder (`asrtSourceRoot` /
`pmrtSourceRoot`), read before the disconnect deletes it; both modules
expose it as `connected_source()`. The pure half — which bones to move,
how to word what was moved and what was skipped — lives in
`maya_rig_retarget` with the scene as data.

### The bridge automation

New module `maya_uebridge/rigimport.py`. `import_and_retarget(fbx, name,
clip_fps, set_timeline)`:

```
precheck ─ no rig?            → character.add_character(rig entry)   (refuse if the file is missing)
         ─ MoCapConstraints?  → refuse: "bake or disconnect first"
         ─ rig posed?         → refuse, naming Go To BuildPose
import   ─ animimport.import_clip(fbx, namespace, merge=False)  (the "as new skeleton" path, unchanged)
         ─ source root = topmost joint of the namespace's DAG nodes (namespaceInfo, recurse=True:
           a Mixamo clip nests `ns:mixamorig:Hips`, and ls("ns:*") does not reach it)
connect  ─ maya_rig_retarget.connect(source_root=...)    (refusal → the source stays, status says why)
bake     ─ maya_rig_retarget.bake()                       (the six steps above)
delete   ─ namespace(removeNamespace, deleteNamespaceContent=True)
range    ─ playback range = the clip's key range when the checkbox says so
```

One undo chunk. Every refusal happens BEFORE anything is imported, except
connect's own, after which the imported skeleton is left in the scene with
the status line naming it — the animator can fix the pose and press
Retarget by hand.

### One bridge window, no Perforce

The Export tab, the Checkout button, the VCS checkbox/root row and every
p4 dialog leave the window. `vcs.py` and `checkouts.py` stay as modules
with their tests (pure functions, verified against a real depot) and are
not imported by `window.py`. What remains:

```
Project: [editor ▾]  connected                          [Refresh]
Search: [______________________________________________]
[ animation list                                        ]
Import: (•) retarget onto the rig   ( ) as a new skeleton
[x] set timeline to clip range
[Export FBX...] [Export to uasset]                     [IMPORT]
status
```

`Export FBX...` is the old Export tab's p4-less path — a `fileDialog2` and
`animexport.export_hierarchy` on the resolved skeleton. `Export to uasset`
is unchanged (it never touched Perforce). The list loses its `✓`/green
marks with the poll that fed them.

### Which character — the selection, the rig, the sole skeleton

The picker's Connect used to name the active character for Scene Setup
and for the bridge's target. Its replacement, `maya_scenesetup.skeleton
.current_root()`, in order:

1. **selection** — a node under the rig's top group (the top ancestor of
   `Main`) or in `ControlSet` means the rig's game skeleton; a joint means
   its topmost joint; anything else is ignored. Several distinct answers
   → refuse;
2. **the rig's skeleton**, when a rig stands;
3. **the only skeleton** (`character_roots()` minus the rig's own
   deformation joints);
4. refuse.

`animimport.choose_target_root`'s "connected character" slot is fed from
the same function (lazy import, guarded — the bridge stays plain `cmds`),
so Import, Export and Add Weapon can never disagree. The pure decision
(`choose_root`) takes the scene as data, as before.

### Scene Setup

- `catalog.Character` gains `kind` (`"rig"` / `"skeleton"`). Rows, in
  dropdown order: `Manny_Rig` — «Manny [rig]», `Manny_Rig.ma`, legacy
  `C:/!!!Work/Animations/Rigs/Characters/Manny_rig_02.ma`; `Manny` —
  «Manny UE5 [skeleton]»; `UE4_Mannequin` — «UE4 Mannequin [skeleton]».
  The dropdown defaults to the rig; `default_character()` keeps answering
  the **skeleton** so `character_path()` with no argument still means
  `Manny_Skeleton.ma` — `maya_skelfit` and three test modules ask that.
- **The shipped rig copy is `Manny_rig_02.ma` with one block cut**: the
  leftover `camera1` (transform + shape, 15 lines, self-contained — grep
  found no connection to it). Textual, like the vaccine cut; never an
  open-and-resave. The `materialXStack1` node stays (two of the animator's
  shading nodes reference it). The `skeldarColour_red` blinn stays in the
  file too; instead `character.add_character` paints the import's meshes
  with the CHOSEN colour through a new `colour.paint_fresh` — a fresh
  material regardless of what the asset carries — so a rig does not
  arrive red every time. The asset's red material is then unassigned and
  stops counting (`is_assigned`).
- `add_character` for a `rig` entry: refuse while a rig stands; import
  (`.ma` path, `cmds.file(i=True)`), paint, sweep, report. The picker
  connect is skipped while `PICKER` is off.
- Buttons removed: Connect Arms To Weapon, Disconnect Arms, Add Aim,
  Camera Setup — callbacks deleted from `window.py`; `connect.py`,
  `aim.py`, `camera.py` stay (the bake uses `camera`, old files may carry
  a link or an aim, and the guards in Add/Remove Weapon that refuse over a
  standing link or aim keep protecting those files).
- Header line reads the resolver: «Character: root (rig)».
- Add Weapon / Remove Weapon / grip fields / colour: unchanged mechanics;
  only "which character" changed.

### Shelf, icons, hotkeys

- `install._PYTHON_BUTTONS`: Rig Picker out (behind `PICKER`), Retarget
  and Bake in after Scene Setup (`maya_rig_retarget.retarget_button` /
  `bake_button` — call, print, `inViewMessage`); the OverRig MEL button
  behind `OVERRIG`. Payload gains `skeldar_features.py` and the three
  retarget modules.
- `icons/make_icons.py`: `draw_scenesetup` becomes a **gear**;
  `retarget.png` (two figures, an arrow) and `bake.png` (a key diamond
  over a bar) added.
- `maya_hotkeys.COMMANDS`: `picker.*` rows behind `PICKER`, `_OVERRIG`
  behind `OVERRIG`; two new rows `retarget.connect` / `retarget.bake`.
  Existing runTimeCommands in the animator's prefs keep resolving through
  `run()`, which reports an unknown key rather than raising.

## Error handling

Every refusal is a string on a status line, before the scene is touched:
no rig file, a second rig, a connected holder, a posed rig, no animation
selected, an ambiguous character. A connect refusal inside the bridge flow
leaves the imported skeleton and says so. A bone under a foreign constraint
is skipped by name. `camera.setup` and `bonedrive` keep their own
autoKey/undo hygiene.

## Testing

- Unit (mayapy, fake `cmds`): the feature flags gating buttons and rows;
  `button_specs` labels and commands; the catalog rows and defaults; the
  resolver's `choose_root` over selection/rig/sole cases; `rigimport`'s
  pure halves (source root pick, wording, refusals); `maya_rig_retarget`'s
  helper-bone plan and wording; the native `vendor_bake` issuing the
  vendor's flags; `paint_fresh`; the window's remaining pure helpers.
- **Standalone proof** `verify_rig_pipeline.py` in mayapy (never the
  animator's scene — it adds a rig and deletes a skeleton): load
  `matrixNodes`/`quatNodes`/`fbxmaya`, run `import_and_retarget` on a real
  UE clip from `Animations/Export`, and gate: rig added once (second add
  refused), controls keyed over the clip range, the rig's `weapon_r` /
  `camera_bone` world matrices against the SOURCE's sampled before its
  deletion (per frame, the expectation computed, not typed), the camera
  present with its marker and following `camera_bone`, the namespace gone,
  a second run on the same rig working (teardown + relink paths), and a
  sword attached before the run still linked after it.
- **Live smoke** through the bridge in the animator's Maya: installed copy
  refreshed, shelf holds the nine buttons, the three windows open, no
  OverRig procedure sourced.

## Not built

Several rigs in one scene (see above); the PlayerMale rig's Add Character
row (the Lugal project has its own file); a Retarget row for Mixamo's
weapon (it has none); any change to the retarget mathematics; removal of
`vcs.py`/`checkouts.py`/`maya_overrig` from the repository.

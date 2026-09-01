# Export to uasset — the short road, with no Perforce on it

2026-09-01. The bridge can already put the scene back into a uasset, but only
through the Perforce path on the Export tab: resolve the working fbx, `p4
edit`, place, reimport. The animator wants the direct version — press a
button on the **Import** tab, confirm the overwrite, and the selected
AnimSequence takes the scene's animation. In their words: «кнопочка экспорта
в uasset… при нажатии будем выводить защитное предупреждение о перезаписи…
если uasset readonly то будем снимать эту настройку и делать экспорт… пока
что наша кнопочка ни как не будет связываться с нашим функционалом для
перфорса… fbx который идет в uasset мы можем экспортировать локально
куда-то в темп фолдер».

## Where it lives

A third button on the Import tab's bottom row:

```
Checkout | Export to uasset | IMPORT
```

There, because it acts on the same list selection as IMPORT and Checkout —
the animator's own framing ("кнопочка из раздела меню import"). It is
**not** called `EXPORT`: the Export tab already has a button by that name
which does go through Perforce, and two identically-labelled buttons with
different blast radii is how somebody submits by accident.

The "Connect to version control" checkbox does not change this button's
behaviour in any way. That is the requirement, not an accident.

## What one press does

1. **The selected record.** Nothing selected → a status line, nothing else.
2. **The uasset's disk path**, from the package and the project's Content
   dir (`records.uasset_path_of`). No Content dir known — the window has
   never been refreshed — → refuse, naming Refresh. The file not on disk →
   refuse, naming the path.
3. **The scene skeleton**, through `animexport.resolve_root()`: selection,
   then the picker's connected character, then the only skeleton, then the
   one called `root`. The same rule as every other direction of the bridge,
   which is the point of it being one function. Undecidable → refuse
   **before** any dialog: a refusal must cost the animator nothing.
4. **The warning.** Names the asset and the skeleton it is about to take,
   and says the three things that are actually at stake:
   - a replace-import rebuilds the asset from the FBX, so uasset curves the
     FBX does not carry — `Pose_0..9`, `MoveData_Speed`, `DisableLegIK`,
     `RootMotionAdditiveInput` and the pose drivers (trap 40: 135 such
     curves measured on one real clip against 9 transform channels) — do
     **not** survive;
   - Perforce is not touched, so the uasset is modified on disk with no
     changelist behind it;
   - when the file is read-only, that the flag will be cleared.

   Buttons `Overwrite` / `Cancel`, default and dismiss both Cancel.
5. **Export the FBX** to `%TEMP%/maya_uebridge/<Name>.uasset.fbx`
   (`animexport.export_hierarchy`): bake-on-export so the rig is never
   touched, range = animation ∪ playback (trap 38 — a narrowed range
   narrows the clip), keys outside the range warned about. This happens
   **before** the read-only flag is touched: a failed export must leave the
   uasset exactly as it was.
6. **Clear the read-only flag** if it is set, remember that we did, and say
   so in the status. It stays cleared — the file genuinely is modified now,
   and putting the flag back would hide that.
7. **Reimport in the editor** — `uescripts.reimport_script`, unchanged,
   pinned to the same project the listing came from (a second open editor
   would be asked for an asset path it does not have).
8. **The status line**: the export line, the read-only note, the reimport
   result, and the fps mismatch warning. The scene's frame rate is never
   written; a mismatch is reported and UE resamples.

## Making the "no Perforce" boundary real

New module `maya_uebridge/uassetexport.py`, one job. `window.py` is already
650 lines and holds the Perforce dialogs; `checkouts.py` *is* the Perforce
tab. A separate module keeps the boundary visible and lets the policy be
tested with neither application running.

The only thing the new code needs from `vcs.py` is the pure package↔path
conversion, so **`package_of` and `uasset_path_of` move to `records.py`** —
string and path work with no p4 anywhere in them, in a module that is
already stdlib-only and holds "everything pure that operates on" bridge
data. `vcs.py` re-imports them, so nothing else changes. `reimport_line`
moves there too: both export directions read that payload, and duplicating
the wording is how two status lines drift apart.

A subprocess test then asserts the real thing — `uassetexport` imports
without `maya_uebridge.vcs` in `sys.modules`.

| Piece | Kind |
|---|---|
| `overwrite_message(name, package, root, read_only)` | pure |
| `refusal(record, content_dir, uasset)` | pure |
| `readonly_note(cleared)` | pure |
| `result_line(name, info, payload, notes)` | pure |
| `is_read_only` / `clear_read_only` | os only |
| `export_to_uasset(record, content_dir, project, asks=None)` | orchestration |

`asks` is injectable for the same reason it is in `vcs.prepare_target` and
`checkouts.export_to`: a modal dialog raised over the command port blocks
Maya's idle queue, and every live proof in this project runs over that port
(bridge note 6).

## Refusals, each with its own wording

| Situation | Result |
|---|---|
| nothing selected | "select an animation first" |
| no Content dir yet | "press Refresh first — the project's Content folder is not known" |
| uasset not on disk | "no uasset at `<path>`" |
| skeleton undecidable | `animexport`'s own message (select the hierarchy, or connect one) |
| Cancel | "cancelled — `<asset>` untouched" |
| read-only flag will not clear | "cannot clear read-only on `<path>`: `<reason>`" — before the editor is asked for anything |
| the editor reports a failure | its `error` verbatim |

Nothing between steps 5 and 7 is undoable in Maya, and none of it needs to
be: the export writes a temp file and the reimport happens inside Unreal.
The scene is read, never modified — `export_hierarchy` restores the
selection it borrowed.

## Testing

`tests/test_uebridge_uasset.py`, no application running: the dialog wording
(names the asset, names the skeleton, mentions the lost curve families,
mentions Perforce, mentions read-only only when read-only), the refusal
table, the read-only note, the status line, `uasset_path_of`/`package_of`
round-tripping after the move, and the import-purity subprocess check.

Live: `docs/superpowers/plans/verify_uebridge_uasset.py` — duplicate a real
AnimSequence into a sandbox asset, set the sandbox read-only, export the
scene onto it, assert the frame count changed and the flag came off, then
delete the sandbox asset and leave the depot and the animator's assets
exactly as found. The same shape as `verify_uebridge_export.py`'s sandbox
gate, which measured 2 → 60 frames.

## Not done, deliberately

- **No `p4 edit`, no `p4 add`, no fstat.** That is the request. The
  consequence is stated in the dialog rather than worked around.
- **No restoring the read-only flag.** Chosen: the file is modified, and
  hiding that would be worse than the flag being off.
- **No "export every checked-out row" batch.** One selected asset per
  press; the Export tab is where the multi-row workflow lives.
- **No refusal when the asset carries `Pose_*`/`MoveData_*` curves.**
  Offered and declined in favour of saying it in the warning: refusing
  would block the ordinary case, since almost every UE clip carries them.

---

## Addendum, the same day: what live verification changed

The design above survived contact with the editor unchanged in shape, and
gained two things it did not have. Both came from the button appearing to
work while writing nothing.

### The silent no-op is reported (`records.unchanged_warning`)

The first live run's status read:

```
AS_VerifyUassetExport: 93 bones, frames 0-71  |  reimported and saved (196 frames)  |  read-only cleared
```

Every word of that was true except the impression it gave: the asset had
not changed at all. The editor's reply was `ok: True, saved: True,
notes: [], error: ""`, and `frames` was simply the asset's own count read
back afterwards — the same number it had before.

So `reimport_script` now reads the asset BEFORE the import too
(`before_frames`, `before_length`, `skeleton`), and
`records.unchanged_warning` fires when frame count and length both come
out identical. The wording is "the asset did NOT change (N frames) —
check the exported bones match `<skeleton>`" rather than an error,
because re-exporting an unchanged clip looks exactly the same from here.

**Both export directions use it.** The Perforce road had the same blind
spot.

### The cause: a fractional playback range (CLAUDE.md trap 50)

Two theories died before the editor log settled it. The scene held three
characters by then, so the export was taking `Manny_Skeleton_root` — the
second character, whose root Maya had renamed — and "UE clips need a bone
called `root`" was a good story. It was wrong: exporting `|root`
explicitly changed nothing. The sandbox's skeleton being
`UE4_Mannequin_Skeleton` against a UE5 Manny was the second story, and it
was wrong too — a `SKEL_Manny` source failed identically.

`<project>/Saved/Logs/<name>.log`, which trap 46 already names as the tool
for this, had the answer in one line:

```
FBXImport: Error: Animation length 2.96 is not compatible with import
frame-rate 31 fps (sub frame 0.752), animation has to be frame-border
aligned. Either re-export animation or enable snap...
```

The animator's time slider ended at **88.792**. `union_range` passed that
straight to `FBXExportBakeComplexEnd`, and UE refuses a clip whose length
is not a whole number of frames — while the import task reports success
and saves the package.

`union_range` now snaps OUTWARD: `floor(start)`, `ceil(end)`. Outward
matters — inward rounding would clip the clip, which is trap 38 again.
With the snap in place the same sandbox went 195 → 100 frames, and a
second one 90 → 100.

This was a live bug in the **Perforce** export direction since
2026-08-21, silent every time the animator's range happened to end on a
fraction.

### The verify proves both directions of the warning

`verify_uebridge_uasset.py` deliberately runs its first round trip against
the project's most common skeleton — almost never the character in the
scene — so the no-op path is exercised for real, and asserts
`changed XOR warned`. A second round trip picks a Manny-shaped skeleton
and asserts changed AND unwarned. **Green live 2026-09-01, 0 of 25 gates
failed.**

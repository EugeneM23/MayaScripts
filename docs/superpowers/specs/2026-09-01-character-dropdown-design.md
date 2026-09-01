# A dropdown of skeletons for Add Character, and UE4_Mannequin in it

2026-09-01. The animator's open project carries `LongswordAnimsetPro` and
`SwordAnimsetPro`, whose ~1200 animations all run on **UE4_Mannequin**. Add
Character only knows the newer Epic Manny. Their ask: «я бы хотел иметь
возможность добавлять скелет UE4_Mannequin… в add character сделаем
выпадающий список где у нас будет возможность добавить разные скелеты…
на этом этапе не делать поддержку риганга и пикера для UE4_Mannequin
просто сделаем так чтобы можно было добавить его в сцену импортировать
на него анимацию».

So: one dropdown, one more entry, and nothing about rigging.

## The asset: exported once from the editor, then shipped

`SkeldarAnim/assets/UE4_Mannequin.fbx` — **1.0 MB, 68 joints, 2 meshes**,
exported from `/Game/SwordAnimsetPro/UE4_Mannequin/Mesh/SK_Mannequin` in the
open project through the bridge's own `uelink` (an `AssetExportTask` with
`automated=True`/`prompt=False`, and `load_asset` guarded because a null
`Object` does not raise, it ASSERTS and takes the editor down — trap 24).

Verified in a standalone Maya before shipping: root at `|SK_Mannequin|root`,
**no script nodes at all**, and exactly the UE4 bone set —

```
root pelvis spine_01..03 clavicle_* upperarm_* lowerarm_* hand_*
<finger>_01..03_* (5 fingers, NO metacarpals)
one twist per segment: upperarm/lowerarm/thigh/calf_twist_01_*
neck_01 head thigh_* calf_* foot_* ball_*
ik_foot_root ik_foot_* ik_hand_root ik_hand_gun ik_hand_*
```

...and confirmed ABSENT: `spine_04`, `spine_05`, `neck_02`,
`index_metacarpal_l`, **`weapon_r`**, **`camera_bone`**. The last two
matter — see Limitations.

Three alternatives were weighed and dropped. Extracting from the animator's
own `UE4_To_Many.ma` means separating one skeleton out of 299 joints across
three skeletons plus an AdvancedSkeleton rig, and sanitizing 2 vaccine/breed
script nodes; the editor's export is authentic and arrives clean. Exporting
on every press would make the button need a running editor, which the
shipped-asset design of Add Character deliberately avoids. Reading the
`.uasset` directly is not buildable at all.

**Provenance:** this is Epic's UE4 mannequin, redistributed inside a studio
tool. The same call the user already made for OverRig, and the same
reasoning — private repo, intra-studio hand-off, studio's decision.

## The catalog gets a character table

`maya_scenesetup/catalog.py` already holds `WEAPONS` as a table of
namedtuples with a shipped-copy-first path. Characters get the same shape:

```python
Character = namedtuple("Character", "key label file legacy")
CHARACTERS = (
    Character("Manny",         "Manny (UE5)",   "Manny_Skeleton.ma", <legacy>),
    Character("UE4_Mannequin", "UE4 Mannequin", "UE4_Mannequin.fbx", ""),
)
```

plus `character_labels()`, `character_by_label()`, `character_by_key()` and
`character_file(entry)`.

**`character_path()` with no argument keeps meaning Manny.** That is
deliberate: `maya_skelfit`, `verify_add_character.py` and three test modules
call it, and none of them is about the dropdown.

`legacy` stays a per-entry field rather than a special case, because Manny's
fallback IS the user's original infected file and that resolution rule has
to survive.

## Import handles both formats, and trap 33 decides how

`.ma` keeps today's path. `.fbx` goes through the FBX plugin — and the
plugin's import MODE is one global setting for the whole session that DOES
reach `cmds.file`, while `maya_uebridge` leaves it on `exmerge`, where the
importer matches names against the scene and **creates nothing**. Without
forcing it, Add Character would silently stop working after any animation
import from Unreal.

That guard already exists inside `attach.import_model`. It **moves to one
shared helper** (`catalog`-adjacent, imported by both) so the fix for trap
33 exists once rather than twice. `FBXImportSetMayaFrameRate -v false` goes
in beside it: `cmds.file` ignores the curve settings anyway, but the scene's
frame rate is never ours to write and saying so explicitly costs nothing.

`returnNewNodes` is why this stays on `cmds.file` rather than `FBXImport` —
trap 22's warning is about losing animation curves, and a reference skeleton
has none, while `FBXImport` cannot report what it created at all. This is
the same trade `attach.py` documents.

## The dropdown

An `optionMenu` directly above the Add Character button, filled from
`catalog.character_labels()`, the choice remembered in
`mayaSceneSetup_character`, defaulting to Manny — so anyone who never opens
the list sees exactly today's behaviour.

## Unchanged

Press it as many times as you like; the rename note; the new character
connected on arrival; the malware sweep on every import (an FBX cannot carry
script nodes, and the `.ma` path needs it, so the sweep stays
format-blind); and nothing at all about the rig.

`character.LABEL` becomes the entry's label, so the status line says which
skeleton arrived.

## Limitations, stated rather than worked around

- **No `weapon_r`** on the UE4 mannequin, so Add Weapon refuses on it
  through its existing "bone not found" path. Its `ik_hand_gun` is not a
  weapon socket in our sense and is not substituted.
- **No `camera_bone`**, so Camera Setup refuses likewise.
- **The rig is neither blocked nor promised.** The UE4 schema is exactly the
  case `verify_missing_bones.py` already proves (no metacarpals, spine to
  `_03`), so Connect and Build are likely to work — but nothing on this
  skeleton has been live-verified, and the docs say so instead of implying
  support.
- The FBX carries a 30 fps stamp and Maya warns about the mismatch on
  import. Informational: `cmds.file` does not write the scene's rate, and
  the reference skeleton has no keys for it to resample.

## Testing

Unit (`tests/test_scenesetup_catalog.py`, `test_scenesetup_character.py`,
`test_scenesetup_window.py`): the table's shape and unique labels, every
entry's file present in `assets/` and inside `install.payload()`, the
`.ma`/`.fbx` type derived from the extension, `character_path()` still
answering Manny, the import-mode guard set-and-restored against a fake
`cmds`, and the remembered dropdown choice.

Live: `verify_add_character.py` gains a UE4_Mannequin pass — import it,
assert 68 joints resolving by plain name with `spine_03` present and
`spine_04`/`index_metacarpal_l` absent, the first character untouched, the
new one active, then delete it and leave the frame, range, autoKey and
selection as found.

## Not done, deliberately

- Rig, picker or twist support for UE4_Mannequin.
- A weapon socket substitute for the missing `weapon_r`.
- Retargeting between the two skeletons — `maya_retarget.py` already exists
  for the suit and is a separate piece of work.
- Any third skeleton. The table makes adding one a two-line change; adding
  one nobody asked for is not.

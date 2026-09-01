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

---

## Addendum: making the two imports the same shape — and the bug under it

The animator's first note after using it: «сейчас ue5 скелет вставляется в
сцену кости отдельно меш отдельно, UE4 скелет вставляется в сцену в одной
группе с мешем, нужно сделать однородно!»

Measured, the difference was bigger than that. **One Manny press brings four
world-level nodes** — the 93 joints, a transform holding the 6 meshes, a
camera and a materialXStack. **One UE4 press brought one** — a group holding
both the joints and the meshes. With six characters in the scene that is 24
nodes against 6.

Asked which shape should win, the animator chose **flat, like Manny's**. So
the FBX importer's wrapper is flattened away and Manny is untouched.

### The wrapper was not just untidy

The wrapper carries the FBX axis conversion — `rotateX -90`, Z-up to Y-up —
while `root` beneath it has clean channels. No import option changes that:
`FBXImportUpAxis y`, `FBXImportAxisConversionEnable` and
`FBXImportForcedFileAxis z` were all tried in a standalone Maya and all
three produced the same wrapper.

And a **UE clip carries that same -90**, on `root`'s jointOrient. So merging
one onto a WRAPPED skeleton applies the rotation twice. Measured standalone
from one clip:

| | head at rest | head at frame 0 of the clip |
|---|---|---|
| wrapped | `0, 165.5, -4.0` | `4.7, 2.96, -147.8` — **lying down** |
| flattened | `0, 165.5, -4.0` | `4.7, 147.8, 3.0` — upright |

So flattening is what makes an animation import land the right way up. The
earlier live run that reported "68 of 68 bones animated" was telling the
truth and the character was on its face; nothing had measured which way up
it stood.

### A plain unparent moves the skeleton

`cmds.parent(children, world=True)` changed the world matrix by a full
90 degrees (measured: worst matrix element 1.0). Maya distributes a joint's
new parentage into `jointOrient`, and the arithmetic it picks is not the one
that preserves the pose. So `flatten_wrappers` records every child's world
matrix by UUID first, unparents, and re-asserts the world matrix by hand.
The rest pose then comes out identical to the wrapped import — head Y
165.516 both ways.

### What flat costs, stated rather than wished away

At world level Maya will not allow a second `root`, so in a scene that
already holds one the UE4 mannequin arrives as `root2` — exactly as a
second Manny arrives as `Manny_Skeleton_root`. An exmerge matches bone
NAMES, so the clip's `root` then matches nothing and that one bone comes in
unanimated: **67 of 68**, measured. That is the pre-existing behaviour of a
second Manny, now shared; the first character in a scene keeps `root` and
gets all 68. The verify gate computes the expectation from the root's actual
name instead of asserting the happy case.

Flattening is FBX-only. Running it over Manny's `.ma` would flatten the
transform that legitimately holds its six meshes.

Proof: `verify_add_character.py`, **green live 2026-09-01, 0 of 26 gates
failed** — including the shape (skeleton and mesh at world level, no
wrapper), the rest pose surviving to 0.01, and the animated character
standing up.

### Addendum 2: the flatten left the geometry behind

The animator, one press later: «скелет стоит на правильном месте а геометрия
нет». Measured, and they were exactly right:

| | head (joint) | mesh bbox Y | mesh bbox Z |
|---|---|---|---|
| wrapped (reference) | `0, 165.5, -4.0` | `-0.04 .. 182.53` | `-21.97 .. 14.75` |
| flattened, first try | `0, 165.5, -4.0` | `-14.75 .. 21.97` | `-0.04 .. 182.53` |

Y and Z swapped: the skeleton stood up and the mesh lay on its side.
Sampled vertices confirmed it exactly — `(x, y, z)` came out as `(x, -z, y)`.

**Cause: the FBX importer LOCKS a skinned mesh's transform** — all nine of
t/r/s, measured — to stop anyone double-transforming the deformation. And a
locked plug makes `cmds.xform` a **silent no-op**. So the joints took their
world matrix back and the mesh could not: it kept identity, while the
skinCluster's stored `geomMatrix` (which holds the wrapper's -90; measured,
not connected to anything) meant the deformation still needed that -90 from
the DAG above the mesh.

Two strategies were measured and BOTH failed identically before the cause
was found — preserving the mesh's world matrix, and preserving its local
matrix. That they agreed was the clue: nothing written to that transform
was landing at all.

The fix is three lines: record which plugs are locked, unlock them around
the write, lock exactly those back. Drift from the wrapped reference is then
**0.000000 on the bounding box and 0.000000 on the head**.

**The lesson for the gates.** Every gate in the previous run passed while
the animator was looking at a character lying down, because they all
measured JOINTS. Bones are the easy half to measure and the wrong half to
trust — `verify_add_character.py` now measures the mesh's world bounding box
and that the importer's locks are back on.

Green live 2026-09-02: **0 of 28 gates failed.**

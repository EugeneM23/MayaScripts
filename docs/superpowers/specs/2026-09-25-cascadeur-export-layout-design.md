# Export in Cascadeur's layout — a wrapper named for the character, `root` at zero (2026-09-25)

## The ask

The animator moves animation Maya ⇄ Cascadeur and asked whether Maya and our rigs could work
"with the same axes as Unreal and Cascadeur". Asked what goes wrong in practice, they named
**moving animation**: Cascadeur → Maya and Maya → Cascadeur.

Of three approaches, they chose **one layout for every export**, Cascadeur's:
- a wrapper node over `root`;
- `root` at zero beneath it;
- the same for the files that go to Unreal.

The wrapper is named **for the character**: `Creep` for the Creep, `Manny` for Manny.

## What was measured first

- **Inside the skeleton, every file already agrees.** Unreal's own clip, Cascadeur's clip and
  our export carry the same root-space bones: Manny's pelvis `(0, −2.281, 95.9)` in both
  Unreal's file and ours, the Creep's `(−0.0, −2.281, 95.749)` in Cascadeur's.
- **The files differ in where the −90° X Z-up→Y-up turn lives:**

  | File | Header | Where the −90° X turn lives |
  |---|---|---|
  | Unreal | Z-up | nowhere: `root` at identity |
  | Cascadeur | Y-up | on a Null `SKM_Manny_Simple` rotated −90° X; `root` at identity beneath, its translation in the Null's Z-up space |
  | Ours | Y-up | on `root` itself as jointOrient/PreRotation −90° X; no parent |

- **The risk in Maya → Cascadeur.** A tool matching bones by name onto Cascadeur's wrapped
  character could add our −90 to its wrapper and lay the character down. That is the Maya
  wrapper bug of 2026-09-01 in reverse. Cascadeur is not on this machine, so this cannot be
  tried here.
- **Cascadeur → Maya works**, measured on `creep_attack_forward.fbx` imported, retargeted onto
  a fresh Creep_Rig and exported:
  - root world 8e-10, pelvis 0.0000 cm;
  - every bone but the twists 0.0006°, the limb bones' pointing 0.025°, the helper bones exact;
  - the twist bones up to 58°, because AdvancedSkeleton spreads the arm roll its own way. That
    is not an axis matter and is not in this spec.
- **`FBXExportUpAxis z` does not give Unreal's layout.** The header says Z-up, `root` keeps a
  +90 PreRotation, and a Y-up Maya reads it back 169 units off.
- **Z-up Maya was rejected.** AdvancedSkeleton's author advises against it in its code, the
  toggle is commented out in 6.797 and its MoCap Library errors under Z-up. And Unreal is
  left-handed, so one axis would still differ in sign.

## The design

### The layout

Every export through `animexport.export_hierarchy` writes:
- a transform (FBX Null) at world level, named for the character, rotated **−90° X**;
- `root` as its child. Its jointOrient becomes `JO · W⁻¹` (W = the wrapper's rotation), which is
  zero for our usual `root` with a −90° X jointOrient. Its translation is re-expressed in the
  wrapper's space: `t' = t · W⁻¹ = (x, −z, y)`.

Every joint's world matrix is unchanged, so the pose is the same. Every bone below `root` is
untouched. Those roads are Export FBX…, Export to uasset and the checkouts' EXPORT.
`export_hierarchy` gains `layout="cascadeur"` (the default) and `layout="plain"` (the old file),
so one caller can be switched back without touching the others.

### How: for the length of the export, in the live scene, put back in a `finally`

A new leaf module, `maya_uebridge/fbxlayout.py` (`cmds` + OpenMaya), with pure halves:

1. **Plan** (`layout_plan`, pure) — read what drives `root`'s translate/rotate:
   - **constrained** (the rig's `root ← Main`): the constraint reads `parentInverseMatrix` and
     `jointOrient`, so it re-solves under the wrapper by itself;
   - **keyed** (animCurves straight into the channels): the translate inputs are routed
     through a temporary swizzle — X→X, Z→−Y (a multDoubleLinear −1), Y→Z. The rotate curves
     stay: the jointOrient change absorbs the wrapper exactly. No key is touched;
   - **static**: the translate values are rewritten to `(x, −z, y)` and written back after;
   - **anything else** (a pairBlend of keys and constraint, an expression, a root already
     under a parent): the plain layout, and the export's notes say why.
2. **The wrapper's name** (`wrapper_name`, pure), the first answer of:
   - the root's `skeldarCharacter` attribute, which Add Character now writes (the catalog key);
   - the root's rig namespace without its digits (`Creep_Rig1` → `Creep_Rig`), when it is a
     catalog key;
   - the one catalog key the root's skinned meshes' `skeldarColour` materials carry (Add
     Character paints with the key);
   - else `Character`, named in the notes.

   A key becomes a name by dropping a trailing `_Rig` (`catalog.export_name`): `Creep_Rig` and
   `Creep` → `Creep`, `Manny_Rig` and `Manny` → `Manny`, `UE4_Mannequin` stays.
3. **The name is FREED first.** The Creep skeleton's meshes stand under a world-level group
   `|Creep`, and Maya would make the wrapper `Creep1`. Any node answering to the name is renamed
   aside (`rpHold_`, the bridge's own prefix) for the length of the export. The name Maya
   actually gave is checked (trap 48's lesson), and everything is restored by UUID.
4. **The surgery**: the wrapper created in the root namespace → `root` parented under it with
   `relative=True` (no compensation; Maya's own is not pose-preserving for a joint, trap from
   2026-09-01) → jointOrient `JO · W⁻¹` (unlocked and relocked if locked) → the plan's
   translate step. The wrapper is selected with the bones.
5. **Restore**, in a `finally`, by UUID: translate back (the swizzle deleted, the original
   inputs reconnected, or the static values written back) → jointOrient back → `root` back to
   world (`relative=True`) → wrapper deleted → held names back.

### The Creep skeletal mesh FBX

`export_creep_skeleton_fbx.py` writes the same layout in its throwaway scene:
- the wrapper `Creep` over `root`;
- the meshes at world level beside it, as in Cascadeur's file; the `|Creep` group is emptied
  and deleted there.

The file is re-exported with `--overwrite`.

### Unreal — verified before the switch is kept

A verify in mayapy standalone drives the animator's running editor through `uelink`, as
`verify_uebridge_uasset.py` does:
1. a Manny AnimSequence duplicated into `/Game/__bridge_verify`;
2. a UE clip retargeted onto a Manny_Rig in Maya;
3. exported in the Cascadeur layout and reimported into the sandbox asset;
4. the sandbox asset exported back out of Unreal and compared, bone by bone and frame by frame,
   with what we wrote;
5. the editor log read for skeleton warnings;
6. the sandbox deleted.

If Unreal reads the wrapper wrongly (an extra bone, a turned root), `uassetexport` and
`checkouts` go back to `layout="plain"` and only Export FBX… keeps Cascadeur's layout. The
result is reported either way.

## Tests

**Unit, pure:**
- `export_name`;
- `wrapper_name` over every source and its order;
- `jo_after` (JO · W⁻¹ in the joint's rotate order);
- the swizzle map;
- `layout_plan` over constrained / keyed / static / pairBlend / parented roots.

**Unit, fake cmds:**
- the surgery's order and its complete restore;
- a held name restored;
- a refusal touching nothing;
- `add_character` writing `skeldarCharacter`.

**`verify_cascadeur_layout.py`, standalone:**

| Case | Checked |
|---|---|
| Creep_Rig on the Cascadeur clip | the file's wrapper `Creep` −90° X, `root` without orientation; read back beside Cascadeur's own file, every bone's LOCAL values including `root`'s (translation and rotation) equal Cascadeur's; world equal |
| Bare Creep skeleton, root keyed in translate and rotate | the `|Creep` group's name freed and back |
| Static skeleton | the file's layout, the scene restored |
| Manny_Rig | wrapper `Manny` |
| A pairBlend root | the plain layout with a note |

In every case the scene comes back exactly: root world at sampled frames, its connections,
jointOrient, names, no wrapper left.

**`verify_cascadeur_layout_unreal.py`** — the Unreal sandbox round trip above.

## Not in this spec

- The twist distribution (58°) — the retarget, separately.
- 30 fps.
- Cascadeur itself: the animator imports one file into Cascadeur to confirm.

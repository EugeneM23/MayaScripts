# Manny in Unreal's own textures — the rig and the skeleton (2026-09-30)

## The ask

«Давай для нашего мени рига и скелета найдем текстуры и добавим их в проект точно так же как и
для орка». The same road as the Orc D (spec `2026-09-28-orc-d-textured-design.md`): the textures
out of the open Unreal project through `maya_uebridge.uelink`, Unreal's material maths baked into
2048 JPG maps in `assets/Manny/`, the materials inside the shipped `.ma` naming their images
relatively, `catalog.Character.textured` on both Manny rows, Add Character relinking them.

## What was measured first

- **Where the textures are.** The editor answering is `MyProject2` (Remote Execution on). It holds
  two Mannys: the Third Person template's `/Game/Characters/Mannequins/` (`SKM_Manny_Simple` in
  `MI_Manny_01_New` / `MI_Manny_02_New`, textures `T_Manny_0X_D/_MRA/_BN` — **1024²**, the 02_BN
  4096²) and the Orc Marauder pack's demo copy `/Game/Orc_Marauder/Demo/Characters/Mannequins/`
  (`SKM_Manny_Simple` in `MI_Manny_01` / `MI_Manny_02`, textures `T_Manny_0X_D/_N/_BN/_Tan/
  _ASAOPMASK_MSK/_CCRCCPlastic_MSK/_MSR_MSK` — all **4096²**, RGBA, alpha 255 everywhere).
- **Our meshes are the demo copy's.** `Skin_3p` (48705 vertices, 92178 triangles, UV set
  `DiffuseUV`) is its `SKM_Manny_Simple` index for index: every UV equal to **0.000000**, points to
  0.073 cm. The template's mesh has the same counts but UVs **0.017** off. `Hands_1P` (21570
  vertices, 40258 triangles; arms, shoulders and hands, 72–162 cm) is a cut of the same mesh:
  21560 of its vertices sit on the demo mesh's to 0.0001 cm with the same UV. Both shipped assets
  have lost the per-face split: every face wears one material (the animator's red blinn in the rig,
  a MaterialX `Maya_Blinn1` in the skeleton), and the old `MI_Manny_*` networks left in the files
  point at `D:/dev/temp/...` and `/Users/Shared/Epic Games/...`.
- **Two material slots**: `M_HeadLegs` (`MI_Manny_01`, 38166 faces of the demo mesh) and
  `M_Torso` (`MI_Manny_02`, 54012), one texture set each.
- **The master `M_Mannequin` (demo), read off its graph as T3D** (the Python API will not follow a
  NamedReroute): Masked with no opacity mask connected (opaque), shading model ClearCoat.
  - Base colour = `lerp(lerp(D, desat(ML_BaseColorFallOff(D), Metal_Desaturation) ·
    Metal_Brightness · Tint, MetalPaintMask), desat(that · Tint, Plastic_Desaturation) ·
    Plastic_Brightness, PlasticMask)`, where `ML_BaseColorFallOff` is
    `lerp(D · EnergeConservation, D, saturate(|N·V| ^ BaseColorFallOff))`. The two instances set
    Tint 1, both desaturations 0, both brightnesses 1, EnergeConservation 1, BaseColorFallOff 0 —
    **every lerp collapses and the base colour is `D` itself** on both slots.
  - Normal = `T_Manny_0X_N`, the clear coat's (top) normal — nearly flat; the bevels and panel
    lines are in `T_Manny_0X_BN`, which feeds `ClearCoatNormalCustomOutput`: the base layer's.
  - Emissive, `MI_Manny_02` only (`UseLogo` on): `MF_logo3layers` — the `T_UE_Logo_M` mask placed
    by `ScaleUVsByCenter(uv + (LogoPosOffset_X, _Y), LogoSize)` = (−0.241, 0.259), 0.076, in
    three layers (parallax offsets, mip blurs, a sphere mask radius 0.65 hardness 0.75), layer 0
    `(0, 1, 1) × 16`: the cyan UE logo on the chest.

## Decisions

1. **Both Manny rows textured** — «Manny [rig]» (`Manny_Rig`, `assets/Manny_Rig.ma`) and
   «Manny UE5 [skeleton]» (`Manny`, `assets/Manny_Skeleton.ma`), `textured=True`. Both meshes,
   `Skin_3p` and `Hands_1P`, wear the maps. Nothing else in either file changes: the rig, the
   skeleton, the skins, the UV set name (`DiffuseUV`, the only set — renaming it on a skinned mesh
   with three `Orig` shapes buys nothing), `camera1` in the skeleton file.
2. **The demo texture set** (4096², our UVs exactly), not the template's (1024², other UVs).
3. **Colour = `D`**, downsampled to 2048² in linear light, sRGB last; the bake script re-derives
   the collapse from the exported parameters and refuses if any of them is not the value above.
4. **The chest logo baked into the torso colour** (the animator's pick, «Запечь лого в цвет»):
   layer 0 only — `lerp(D, (0, 1, 1), saturate(16 · logo · sphereMask))` at the logo's UV — no
   glow, no parallax, no blur layers (an emissive cannot be a colour map; saturated it is cyan).
5. **Normal = `BN`** (the visible bevels), renormalised as vectors, green flipped into Maya's
   convention (Unreal's are DirectX), through a `bump2d` in tangent-space mode — the Orc D's wiring.
6. **Two materials, one per slot** — `skeldarTexture_Manny_HeadLegs`, `skeldarTexture_Manny_Torso`,
   the one shader wearing `colour.LOOK`, `colour.TEXTURE_MARKER`, every file node marked
   `colour.ASSET_IMAGE` ("Manny/<file>"), colour spaces fixed (sRGB colour, Raw normal). **Per face
   by Unreal's slot**: `Skin_3p` face by face through its vertex ids (the same mesh); `Hands_1P`
   through its vertices matched to Unreal's by position and UV, the few it cut new taking the slot
   of the Unreal face closest to their centre. The meshes' old materials and every shading node
   left unused are deleted (the dead `MI_Manny_*` networks, `EnvSamplerTex`, the MaterialX
   `Maya_Blinn1/3`, the red blinn, AdvancedSkeleton's unused lamberts in the skeleton file).
7. **Built in mayapy, in place, re-runnable** (`make_manny_textured_assets.py`): open the shipped
   `.ma` (script nodes not executed), dress, save, cut Maya's two script-node blocks from the text
   (trap 74), refuse banned text (`D:/`, `C:/`, `/Users/Shared`, `MI_Manny`, `T_Manny_0`,
   `skeldarColour`, …). The build checks that nothing but shading changed: every node of the file
   before, bar the shading ones deleted, is there after with its type and parent, and the file's
   text outside the shading blocks is the same.
8. **Add, Recolour, the palette** — the Orc D's rules unchanged: a textured Add paints nothing and
   leaves the swatch, turns Textures on in the model panels, says «textured»; Recolour (the Colour
   section) replaces the textures with a colour; the next Add is textured again.
9. **The Manny portrait is rendered again textured** (`make_character_portraits.py` keeps a
   textured row's own materials).

## The files

- `docs/superpowers/plans/export_manny_from_unreal.py` → `sources/manny/`:
  `SKM_Manny_Simple.fbx` (the demo mesh, LOD0 — which face is which slot),
  `textures/T_Manny_01_D.png`, `T_Manny_01_BN.png`, `T_Manny_02_D.png`, `T_Manny_02_BN.png`,
  `T_UE_Logo_M.png`, and `manny_materials.json` (the slots, both instances' parameters, the master's
  blend mode and shading model, the textures' sizes and sRGB flags).
- `docs/superpowers/plans/make_manny_textures.py` → `SkeldarAnim/assets/Manny/`:
  `Manny_HeadLegs_Color.jpg`, `Manny_HeadLegs_Normal.jpg`, `Manny_Torso_Color.jpg`,
  `Manny_Torso_Normal.jpg` (2048², q95).
- `docs/superpowers/plans/make_manny_textured_assets.py` → `assets/Manny_Rig.ma`,
  `assets/Manny_Skeleton.ma`, in place.
- `docs/superpowers/plans/verify_manny_textured.py` — standalone gates (below).

## Proof

`verify_manny_textured.py`, mayapy standalone, a scratch scene:
- both rows textured, the four images on disk, nothing absolute in either asset's text;
- each asset: the two materials, every face of both meshes in one of them, the face counts per slot
  as Unreal's (`Skin_3p` 38166 / 54012), the file nodes relative and colour-managed as decided;
- **the slot is right face by face**: at sampled faces of each slot Maya's own sampler at the face's
  UV centre gives what Unreal's `D` gives there for THAT slot, and not what the other slot's gives;
- the logo: cyan at its centre on the torso map, where Unreal's `D` is not;
- the normal maps: Unreal's `BN` with the green flipped, to JPG noise;
- Add Character of both rows: relinked to the installed copy's images, «textured» in the message,
  the palette's next free colour unmoved, Recolour replacing the textures, a second Add textured;
- the rig still works: `verify_rig_pipeline.py` and `verify_many_rigs.py` re-run on the new asset,
  `verify_add_character.py` on the new skeleton, `verify_one_shader.py`.

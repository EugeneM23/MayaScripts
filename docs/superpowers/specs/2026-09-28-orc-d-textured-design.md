# Orc D — SK_Orc_Marauder_D as a textured rig row (2026-09-28)

## The ask

«У нас в плагине есть риг орка. Давай добавим еще один вариант орка но на этот раз
SK_Orc_Marauder_D вот эту версию и для этой версии сделаем материал с текстурами.»
The project is open in Unreal (`MyProject2`, `/Game/Orc_Marauder/Meshes/`); Remote Execution was
switched on by the animator for this, so the mesh and every texture came out of the editor through
`maya_uebridge.uelink` — `AssetExportTask` of the skeletal mesh (LOD0, morph targets) and of each
`Texture2D` to PNG from its SOURCE data (the image as imported, not the platform compression).

## What was measured first

- **The skeleton IS the F orc's.** 91 joints, the same names; every joint's rest world matrix and
  every skin bindPreMatrix equal to F's to **0.0** (the same `SKEL_Orc_Marauder`, the same
  reference pose). So D needs no rig of its own: it is bound onto the shipped `Orc_Rig`'s game
  skeleton, whose joints stand at that bind at build pose.
- **The mesh**: 28035 vertices, 48259 faces, 56 morph targets (the F orc's 56), UV sets
  `DiffuseUV` + `LightMapUV`. Five sections in Unreal: 0 Cloth, 1 Body, 2 Eye, 3 Skirt_Sim (the one
  that uses cloth simulation), 4 **Skirt_Proxy** — 885 faces, 489 vertices, one shell hovering a
  median 1.65 cm (p90 4.5, max 10.6) off the rest of the mesh: the cage the clothing asset was made
  from. No fur section (F has one; D does not).
- **The materials** (read off the instances and their master materials' expression graphs):
  - Body (`MI_Orc_Marauder_Body_A_Inst` → `M_Orc_Marauder_MasterMaterial_SP`), linear:
    `lerp(pow(base · 1.70377, 1.095925), TattooColorA · atlas(u), tattooMask.R · 1.0)` —
    saturation 1.17 is clamped to 1 (no effect), the body colour mask is off, Skin_Color white;
    `TattooColorA` (0.010414, 0.034492, 0.046875), `atlas` the CurveLinearColorAtlas `CA_Mannequin`
    (one curve, 64 samples, sampled along U), so the tattoos come out nearly black.
  - Cloth (`MI_Orc_Marauder_Cloth_Inst` → `M_Orc_Marauder_MasterMaterial`): `base · 1.5`
    (contrast 1, saturation 1.1 clamped, the eight ID colours white), **opacity mask = the base
    colour's alpha, clip 0.3333**, two-sided. The alpha cuts the chain-mail netting and the fringes.
  - Eye (`M_Orc_Marauder_Eye_MasterMaterial`): a refraction eye (ML_EyeRefraction):
    `shadow(uv) · lerp(sclera · 2.3009, iris(uv') · 4.1602 · limbus, irisMask)`, iris UV radius
    0.166, limbus width 0.043 / power 8, shadow = SphereMask(radius 0.186, hardness 0.0724) toward
    (0.23, 0.083, 0.032).
  - Normal maps are DirectX (green down); Maya's tangent-space normals are OpenGL (green up).
- **Sizes**: the colour and normal maps are 4096²; at 2048² JPG q95 the four main ones are ≈7 MB.

## Decisions

1. **A fourth rig row «Orc D [rig]»**, key `Orc_D_Rig`, asset `assets/Orc_D_Rig.ma`, namespace
   `Orc_D_Rig`, `Orc_D_Rig1`, … — the shipped `Orc_Rig.ma` with its F mesh replaced by D's. The
   AdvancedSkeleton rig, the helper bones, the pads, the rotation-only mark are the F orc's, byte
   for byte in behaviour; nothing is rebuilt live.
2. **D's skin on the rig's game joints by name**, weights copied as Unreal has them, the blendShape
   rebuilt with its 56 targets (weights 0), the mesh in world space with one UV set `map1` (Unreal's
   `DiffuseUV`), the normals and smoothing as the FBX has them.
3. **The Skirt_Proxy section is dropped** (measured above: the clothing asset's cage, not what Unreal
   draws). The Skirt_Sim section stays as plain skin — no cloth simulation in Maya.
4. **Textures at 2048², JPG** (the animator's choice over 4096 JPG and 4096 PNG: «2048, JPG»),
   except the cloth's cut-out, a lossless PNG holding the alpha already clipped at 0.3333 (0 or 255
   — a hard cut, no blending to sort in the viewport).
5. **Unreal's material maths is baked into the colour maps**, not rebuilt in nodes: body =
   the SP formula above (intensity, contrast, tattoos), cloth = ×1.5, eye = the sclera/iris/shadow
   composite at 1024². Every result stays below 1.0 in linear, so an 8-bit sRGB image holds it
   without clipping. The formula is the graph's; the eye is an approximation (no refraction).
6. **Maya materials** — three, one per Unreal material, each the one shader (`colour.SHADER`,
   phong wearing `colour.LOOK`): colour from its map; body and cloth get their normal map through a
   `bump2d` in tangent-space-normals mode (the green channel flipped into Maya's convention in the
   shipped JPG); the cloth's `transparency` from the cut-out PNG. So a textured character wears
   several materials — one per texture set, one shader type.
7. **The shipped images live in `assets/Orc_D/`** and the `.ma` names them RELATIVELY: each file
   node carries `skeldarAssetImage` = the path under `assets/`, and Add Character points
   `fileTextureName` at the installed copy (`colour.relink_images`). No path of this machine is in
   the asset. Each material carries `colour.TEXTURE_MARKER` (the colour image's path), never
   `colour.MARKER`, so the palette does not count it.
8. **Add Character on a textured row**: the asset's own materials stay (no palette colour, the
   swatch is not advanced), the images are relinked, Textures are turned on in every model panel
   where they are off, and the message says «textured» (+ «(viewport textures on)»). A missing
   image is named in the message; the character still arrives.
9. **Recolour replaces the textures with a colour** — Spear 03's ruling («заменяет текстуру
   цветом»), one meaning per control; a whole-shape assignment replaces the per-face ones. The next
   Add brings the textures back.
10. **Sources** (`sources/orc/`): `SK_Orc_Marauder_D.fbx`, the seven Unreal textures the maps are
    made from, at their original size, and `orc_d_materials.json` holding every parameter read off
    Unreal (the atlas curve included), so the maps rebuild without the editor.

## Pipeline (re-runnable)

1. `export_orc_d_from_unreal.py` (mayapy, the editor open with Remote Execution on): the FBX, the
   textures, the parameters → `sources/orc/`.
2. `make_orc_d_textures.py` (mayapy): the maps → `SkeldarAnim/assets/Orc_D/`.
3. `make_orc_d_rig_asset.py` (mayapy): `Orc_Rig.ma` + the FBX → `SkeldarAnim/assets/Orc_D_Rig.ma`.

## Proof

`verify_orc_d_rig_asset.py` (mayapy standalone, the real Add Character): the asset's text holds no
absolute path and no script node; the images exist; two Orc D and an F orc added, each in its
namespace, rotation-marked, at their bind, textured (every file node on an existing image, the
palette untouched); D's skin under a pose equal to the FBX's own skin driven the same way; the 56
targets equal to the FBX's; the face sets per material equal to Unreal's sections, the proxy gone;
UVs and normals equal to the source's; the file node sampled at texel centres equal to the image's
pixels; the retarget through the button onto the first D (orientations, lengths), the others
unmoved; Recolour replacing the textures, a second Add textured again; the export bones only.
A playblast in a disposable Maya shows it.

## Not built

The F orc textured (the same maps fit it but for its fur); the fur material; Unreal's cloth
simulation; the eye's refraction and the body's subsurface scattering.

## Addendum — the cut-out only where there is a cut (same day)

The animator, after the first Add: «при стандартных настройках рендера определенные части орка
просвечиваются». Viewport 2.0's default transparency (Object Sorting) draws a material with any
transparency input in the transparent pass whole and does not depth-sort inside one render item,
so with the cut on the whole cloth the vest's leather drew over the shoulder plates, the belt over
its buckle, the wraps over the knee pads. Decision 6 changes: the cloth is **two** materials — the
opaque cloth, and `ClothCut` (the same colour and normal file nodes, plus the cut) worn only by the
faces whose uvs touch a cut texel, 106 of 20122. Four materials in all. Measured: the diff against
the same scene with no transparency fell from 12k–57k pixels a view to 44–1515, all on the vest's
torn edge; gate 19 of the verify samples every opaque cloth face on the mask and finds no cut.

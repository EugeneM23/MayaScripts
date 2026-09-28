# Spear 03: the first weapon that arrives with its texture (2026-09-28)

The animator, handing over `Downloads/Spear_03.fbx` and `Downloads/Halberd_A.tga`:
«Давай добавим новое оружие к нам в инструменты, это должно выдаваться сразу
с текстурой».

## Measured before anything was decided

- A Blender 2.83 FBX out of a Unity project: two meshes, `Spear_03_LOD0`
  (230 vertices, 185 faces) and `Spear_03_LOD1` (116), identity transforms,
  pivots at the origin. 199.6 cm along +Y with the head at +Y (7.7 cm wide in
  **Z**, 2.9 cm thin in X), the butt ON the origin.
- One phong `Halberd`, its colour a file node on
  `D:\Unity_Project\...\Halberd_A.tga` — a path on no machine of ours.
- The UV set is `UVКарта`, which reaches Maya as `UV?????`.
- The texture: 2048 × 2048 TGA, 24-bit, uncompressed, no alpha, 12.6 MB.

## Decisions

- **The grip: Spear 01's fraction** of the length from the butt (the
  animator's pick over "the middle" and "the butt"): 0.2233, measured on the
  shipped `Spear_01.fbx` in the asset script's own run — 44.6 cm above the
  butt of a 199.6 cm spear.
- **Recolour replaces the texture with the colour** (the animator's pick over
  tinting it or refusing): one meaning per control, the same as on every
  weapon; the next Add brings the texture back.
- The LOD0 ships (the Orc's precedent); label «Spear 03», key `Spear_03`,
  `weapon_r`, scale 1.0 (a 2 m spear), identity frame.
- The texture ships as **`assets/Spear_03.png`**: lossless, 6.7 MB, both files
  read back through `MImage` and compared pixel for pixel.

## Shape

`docs/superpowers/plans/make_spear03_asset.py` (mayapy standalone, the dagger's
script's shape): LOD0 kept, a quarter turn about +Y (width Z → X, thickness
X → −Z, det +1), the shaft's bottom centred on the axis (it was 0.002 off), the
origin moved up to the grip, frozen, the UV set renamed `map1`, a plain lambert
in place of the file's material, exported alone; the TGA to PNG.

**`catalog.Weapon` gains `texture`** (default `""`): the shipped image a weapon
arrives in. Every other row, and a pasted FBX, keeps the palette. `missing()`
names a missing texture as it names a missing model.

**`colour.paint_texture(shapes, image, key)`**: a phong wearing `LOOK` — the one
shader — with a `file` node (sRGB, a `place2dTexture` wired the way
Hypershade wires one) on its colour, marked **`skeldarTexture`** = the image
path, NOT `skeldarColour`. So the palette scan never reads a textured material
as a worn colour, and `paint` — which reuses a `skeldarColour` material with a
`setAttr` on `.color` — never finds it: Recolour and the Colour tool build a
fresh colour material over it, which is the decision above. A textured
material already in the scene for the same image is reused, so re-adding the
spear does not pile up file nodes.

**`attach.attach`** paints a textured entry with it instead of the swatch's
colour. **Weapons > Add** says «textured» where it names a colour, leaves the
swatch where it is (no colour was used), and turns **Textures** on in the
visible model panels where it is off, saying so — Maya's viewport shows a
textured material flat grey without it, and "arrives with its texture" means
seeing it. Nothing else about the viewport is touched.

## Not built

A texture for a pasted FBX (it keeps the palette), per-LOD choice, normal or
roughness maps (none were given), a relative texture path in saved scenes (the
file node holds the installed copy's absolute path, as every asset path does).

# The Creep in its own textures — the rig and the skeleton (2026-09-30)

## The ask

«Вот текстуры для крипа давай сделаем тоже самое что и для мени» — three images: the body's colour and
normal, the head's colour (`Downloads/creep_body_diff.png`, `creep_body_norm.png`, `creep_face_diff.jpg`).
Asked, the animator chose **the whole Creep** («Весь Крип») over those three alone: the head's normal and
the set the back and both arms share come from the Creep's own Cascadeur FBX.

## What was measured first

- **The textures.** `creep_body_diff.png` / `creep_body_norm.png` are byte for byte `8.png` / `9.png`, which
  Cascadeur embedded in `sources/creep/creep_T-pose_draft.fbx`; `creep_face_diff.jpg` is its `0.jpg`
  re-encoded (mean difference 0.0006). All 2048², no alpha. The FBX's meshes wear: `body` 8/9, `face` 0/1,
  `back`, `arm_l`, `arm_r` one shared set 2/3 (4/5 and 6/7 are the same bytes). Cascadeur's materials are
  phongs at full colour (the texture on `.color`, diffuse 1) — no material maths to bake.
- **The UVs.** Our five meshes (`Creep_Body`, `Creep_Face`, `Creep_Back`, `Creep_Arm_L`, `Creep_Arm_R`, the
  rig's and the skeleton's alike) carry Cascadeur's UVs index for index: counts equal, values to 7.5e-9,
  per-face UV ids equal. The images go on as they are.
- **The normal maps' green**, by the curl of the field (a height field's normals are curl-free, so in image
  coordinates `d(nx)/dy` and `d(ny)/dx` correlate positively for DirectX, negatively for OpenGL), with
  Unreal's own maps as controls (Manny BN +0.39, Orc body +0.47 — DirectX; our flipped Manny −0.39):
  **the body −0.22 and the back/arms −0.29 are already OpenGL (Maya's), the head +0.70 is DirectX.** The
  head's normal is nearly flat (a fine grain).

## Decisions

1. **Both Creep rows textured** — «Creep [rig]» (`Creep_Rig.ma`) and «Creep [skeleton]» (`Creep_Skeleton.ma`),
   `textured=True`. So every rig row is textured now; the UE4 Mannequin is the one character that still
   arrives in a palette colour.
2. **Three texture sets, one material each**: `Creep_Body` (body), `Creep_Face` (the head), `Creep_Limbs`
   (the back and both arms — Cascadeur's shared set). Materials `skeldarTexture_Creep_Body/_Face/_Limbs`,
   the one shader wearing `colour.LOOK`, `TEXTURE_MARKER`; each file node `ASSET_IMAGE` "Creep/…",
   colour sRGB, normal Raw through a bump2d in tangent space — the Orc D's and Manny's wiring. A whole
   mesh wears one material: no per-face split.
3. **Maps at 2048 JPG q95** in `assets/Creep/`: `Creep_{Body,Face,Limbs}_{Color,Normal}.jpg`. Colour as the
   image is; normals renormalised, the green flipped where the curl test says DirectX (the head) and left
   where it says OpenGL — the script measures and refuses a map it cannot decide (|corr| < 0.1).
4. **Sources** copied into `sources/creep/textures/` (the animator's three under their names; the FBX's
   head normal and shared set as `creep_face_norm.jpg`, `creep_limbs_diff.png`, `creep_limbs_norm.png` —
   the `.fbm` folder is not in git).
5. **The assets dressed in place** by `make_creep_textured_assets.py`, one mayapy process each, with
   Manny's checks (the header unchanged, `git diff` showing nothing but shading, the resave noise and the
   singletons; banned text refused; relative paths asserted). The shared machinery moves out of
   `make_manny_textured_assets.py` into `asset_dress.py`, which both use; Manny's script, re-run through it
   into a scratch folder, must give its committed assets again.
6. **The Creep pipeline gains a last step**: after `make_creep_weapon_sockets.py`, the textures. It is
   re-runnable, so a rebuilt asset is dressed again by the same command.
7. **Add, Recolour, the portrait** — as the Orc D and Manny: textured Add, the Colour section repaints, the
   next Add is textured; the Creep portrait rendered again textured.

## Proof

`verify_creep_textured.py`, standalone: both rows textured and on the installed images; each mesh wears its
set's material alone; at sampled faces of every mesh Maya's sampler gives the SOURCE colour of that mesh's
set at the face's UV centre, and not the other sets'; the normals the sources' (the head's green flipped,
the others not); skins as they were; Recolour and a second Add. The Creep's asset verifies
(`verify_creep_rig_asset.py`, `verify_creep_skeleton_asset.py`), `verify_one_shader.py` and
`verify_orc_d_rig_asset.py` re-run; the unit tests.

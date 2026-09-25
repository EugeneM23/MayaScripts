# `Armature` over the skeleton, and one shader on every model — design (2026-09-25, evening)

## The ask

> Появилось требование чтобы верхняя группа называлась Armature. Еще нужно на все наши модели и
> риги настроить единый шейдер. Такой чтобы он смотрелся хорошо в мае и в каскадере. Сейчас при
> экспорте в каскадер модель выглядит темной и на модели много материалов.

The animator then left for an hour («сделай все самостоятельно»): every decision below was taken
without them and is stated so it can be reversed.

## 1. The wrapper is `Armature`

The morning's export (`maya_uebridge.fbxlayout`, Cascadeur's layout) named its −90 X Null for the
character (`Creep`, `Manny`, `Orc`) — the animator's choice then («по персонажу»). The requirement
now is one name for every character: `fbxlayout.WRAPPER_NAME = "Armature"`, used by
`animexport.export_hierarchy` and `export_creep_skeleton_fbx.py`.

Everything that existed only to find the character's name goes: `fbxlayout.wrapper_name`,
`character_name`, `_colour_keys`, `FALLBACK_NAME`, `COLOUR_MARKER`; `catalog.export_name`; and
Add Character's `skeldarCharacter` tag on the skeleton root (`character.tag_root`,
`CHARACTER_TAG`). `fbxlayout.tag_held` stays: roots tagged by today's build are in the animator's
scenes, and the tag must not ride into a file as a root property (trap 40). The name is still freed
before the wrapper takes it (`rpHold_`), so a node of the animator's called `Armature` is held
aside and put back.

## 2. One shader

**Measured first** (standalone, every shipped asset and both Cascadeur files of the creature):

- the assets are a patchwork: the Creep's arms and face a grey `blinn1` (0.5 × diffuse 0.8), its
  back a red blinn, its body NO material; the Orc five materials by face (a phong, lamberts, FBX's
  default); Manny's skeleton a MaterialX shader; the UE4 mannequin black phongs; the weapons a
  lambert each; 8–15 unworn materials per file, some with textures on `E:\work\...`;
- the skeletal-mesh FBX sent to Cascadeur carried three materials — `blinn1` on the arms and
  face, the red blinn on the back, FBX's `Default_Material` on the body — every one with
  `DiffuseFactor 0.8`, `SpecularColor 0.5`, `ReflectionFactor 0.5`;
- the FBX Cascadeur 2024.1 itself wrote of this creature (`creep_T-pose_draft (1).fbx`) carries
  phongs with the colour at full, `Specular 0.2`, `Shininess 20`, `Reflectivity 0`, no
  `ReflectionFactor`. Cascadeur's viewport is PBR (baseColor/metallic/roughness/reflectance);
  its FBX import maps a phong into it in C++, not in any of its Python.

**The shader** is that one: `colour.SHADER = "phong"` wearing `colour.LOOK = {diffuse 1,
specularColor 0.2, cosinePower 20, reflectivity 0}` — the numbers Cascadeur writes itself, so it
reads ours as it reads its own. A phong's `cosinePower` is FBX's `ShininessExponent`, so the
values land in the file unconverted. Still a shiny shader, not a lambert (the animator's 2026-09-03
ruling). `colour.dress(material)` applies LOOK; `make_material` calls it, so every material we
create — Add Character, Add Weapon, Recolour of a material that is not ours yet — is the one shader.

**One material per character, in its colour.** Add Character already paints every mesh the import
brought with ONE fresh material (`paint_fresh`), and a whole-shape `forceElement` replaces a
per-face assignment (measured: the Orc's five sets become one). The per-character colours stay —
they are what tells two characters apart in the viewport (2026-09-03) — so «единый шейдер» is one
shader TYPE and LOOK, not one colour for everything. Rejected: one material shared by every
character (loses the colours), and rewriting the six asset files (a resave of Manny's `.ma` needs
mtoa/USD/MaterialX loaded or mangles their nodes; nothing in the scene would change, since Add
repaints anyway).

**The skeletal mesh for Cascadeur** (`export_creep_skeleton_fbx.py`) paints its five meshes with
one material of the shader, `Creep_Mat`, in a neutral 0.8 grey (Cascadeur's own default base
colour), its marker attribute removed before the export.

Scenes made before this keep their blinns (`paint` reuses a marked material rather than swapping it
under an assignment); a re-Add brings the shader.

## Proof

- `verify_one_shader.py` (standalone): every catalog character through Add wears one material of
  the shader in its colour — the Orc's per-face five included — every catalog weapon the same, an
  artist's own FBX of the Orc's meshes carries one phong with Cascadeur's numbers, and the
  animation export's top node is `Armature`.
- `verify_creep_skeleton_fbx_cascadeur.py`: gate 6 — ONE material in the exported file on all five
  meshes, phong, specular/shininess/reflectivity equal to Cascadeur's own body material.
- `verify_cascadeur_layout.py` 9/9 with `Armature` (a node of the animator's named `Armature` held
  and restored; a legacy tagged root still keeps its tag out of the file).

## Not verified

Cascadeur's viewport itself. It is installed and running, but its script runner starts from its own
menu (`MCP.Start script server`) and listens on 127.0.0.1:8765, which another session's server holds
right now. The FBX-level equality with Cascadeur's own file is the proof available; the animator's
eye on the imported file is the proof that matters.

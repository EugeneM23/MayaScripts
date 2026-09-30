# Manny Textured Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** «Manny [rig]» and «Manny UE5 [skeleton]» arrive in Unreal's own textures, the Orc D's way.

**Architecture:** Three re-runnable mayapy scripts in `docs/superpowers/plans/` — export from the editor
(uelink) → bake the maps (numpy + QImage) → dress the two shipped `.ma` in place — plus two catalog flags.
The plugin's textured-character path (`colour.relink_images`, `character.appearance`) already exists and
is not changed.

**Tech Stack:** mayapy 2027 (maya.standalone, OpenMaya 2), PySide6 QImage, numpy, Unreal 5.8 Python over
`maya_uebridge.uelink`.

## Global Constraints

- Source set: `/Game/Orc_Marauder/Demo/Characters/Mannequins/` (4096², our UVs exactly), editor `MyProject2`.
- Maps: 2048², JPG q95, in `SkeldarAnim/assets/Manny/`, named `Manny_{HeadLegs,Torso}_{Color,Normal}.jpg`.
- Colour = `D`; torso colour gets the logo layer 0: `lerp(D, (0,1,1), saturate(16 · logo · sphereMask))`.
- Normal = `BN`, renormalised, green flipped.
- Materials `skeldarTexture_Manny_HeadLegs`, `skeldarTexture_Manny_Torso`; file nodes carry
  `colour.ASSET_IMAGE` = "Manny/<file>"; no absolute path in either asset.
- `Skin_3p` slot counts must equal Unreal's: HeadLegs 38166, Torso 54012.
- Nothing in either `.ma` changes but shading; script-node blocks cut from the text after the save.
- Commit only this work's files and hunks — peers have uncommitted edits in the tree (CLAUDE.md,
  window.py, inventory); never push without asking.

---

### Task 1: Export from Unreal

**Files:**
- Create: `docs/superpowers/plans/export_manny_from_unreal.py`
- Create (output): `sources/manny/SKM_Manny_Simple.fbx`, `sources/manny/textures/*.png`,
  `sources/manny/manny_materials.json`

**Interfaces:**
- Produces: `manny_materials.json` = `{"slots": [[slot, mi_path], ...], "materials": {mi_path: {"parent",
  "scalars", "vectors", "textures", "switches"}}, "master": {"blend_mode", "shading_model"},
  "textures": {name: {"size", "srgb"}}}`; PNGs `T_Manny_01_D`, `T_Manny_01_BN`, `T_Manny_02_D`,
  `T_Manny_02_BN`, `T_UE_Logo_M`.

- [ ] Step 1: write the script (the shape of `export_orc_d_from_unreal.py`: one UE script, reply JSON,
  `AssetExportTask` automated/prompt False, the mesh LOD0 FBX); refuse unless the slots are
  `M_HeadLegs → MI_Manny_01`, `M_Torso → MI_Manny_02` and every file landed.
- [ ] Step 2: run it; expect five PNGs 4096²/1024² and a 2.9 MB FBX.

### Task 2: Bake the maps

**Files:**
- Create: `docs/superpowers/plans/make_manny_textures.py`
- Create (output): `SkeldarAnim/assets/Manny/Manny_HeadLegs_Color.jpg`, `..._HeadLegs_Normal.jpg`,
  `..._Torso_Color.jpg`, `..._Torso_Normal.jpg`

**Interfaces:**
- Consumes: Task 1's files.
- Produces: the four JPGs; stdout reports the logo's UV box and the BN/N flatness.

- [ ] Step 1: write it — refuse unless the instance parameters are the collapse's (Tint 1, both
  desaturations 0, both brightnesses 1, EnergeConservation 1, BaseColorFallOff 0, `UseLogo` on 02
  only); colour in linear, shrink, sRGB; logo from `ScaleUVsByCenter(uv + offset, LogoSize)` in
  Unreal's uv (row 0 = v 0), sphere mask `saturate((1 - d/0.65) / (1 - 0.75))`; normals as the Orc D's
  `normal_map`.
- [ ] Step 2: run; look at the torso colour's logo region.

### Task 3: Dress the assets

**Files:**
- Create: `docs/superpowers/plans/make_manny_textured_assets.py`
- Modify (output): `SkeldarAnim/assets/Manny_Rig.ma`, `SkeldarAnim/assets/Manny_Skeleton.ma`

**Interfaces:**
- Consumes: `sources/manny/SKM_Manny_Simple.fbx`, `assets/Manny/*.jpg`,
  `colour.make_textured_material(image, key)`, `colour.ASSET_IMAGE`, `colour.TEXTURE_MARKER`,
  `colour._PLACE2D`.
- Produces: in each asset two materials assigned per face on `Skin_3p` and `Hands_1P`.

- [ ] Step 1: write it — per asset: open (no script nodes), import the FBX in a namespace, slot per
  Unreal face, `Skin_3p` by vertex-id triples (all must match), `Hands_1P` by position+uv vertex match
  then closest face for the rest, strip old shading, build the two materials (the Orc D's `material()`),
  assign, drop unused shading, remove the namespace, save, cut script nodes, banned words, and the
  before/after checks (nodes by UUID bar shading; text outside shading blocks identical).
- [ ] Step 2: run on both; expect `Skin_3p` 38166/54012.

### Task 4: Catalog flags + tests

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py` (the two Manny rows)
- Modify: `tests/test_scenesetup_catalog.py` (the Orc D class's "only the Orc D is textured", a Manny class)

- [ ] Step 1: failing tests:

```python
class MannyTextured(unittest.TestCase):
    MAPS = ("Manny_HeadLegs_Color.jpg", "Manny_HeadLegs_Normal.jpg",
            "Manny_Torso_Color.jpg", "Manny_Torso_Normal.jpg")

    def test_both_manny_rows_are_textured(self):
        for key in ("Manny_Rig", "Manny"):
            self.assertTrue(catalog.character_by_key(key).textured, key)

    def test_the_maps_ship(self):
        for name in self.MAPS:
            self.assertTrue(os.path.isfile(catalog.asset_path("Manny/" + name)), name)

    def test_the_assets_name_their_images_relatively(self):
        for key in ("Manny_Rig", "Manny"):
            images = []
            with open(catalog.character_file(catalog.character_by_key(key)),
                      encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '.ftn" -type "string"' in line:
                        images.append(line.split('"')[-2])
                    for bad in ("D:/", "C:/", "/Users/Shared", "MI_Manny", "T_Manny_0"):
                        self.assertNotIn(bad, line, key)
            self.assertEqual(sorted(set(images)), sorted("Manny/" + m for m in self.MAPS), key)
```

and `test_only_the_orc_d_is_textured` becomes the three textured keys.
- [ ] Step 2: run → FAIL (textured False); Step 3: set `textured=True`; Step 4: run the whole suite green.

### Task 5: Verify, portraits, install, docs

**Files:**
- Create: `docs/superpowers/plans/verify_manny_textured.py`
- Modify: `docs/superpowers/plans/verify_orc_d_rig_asset.py` (its palette control rig: a Creep, the Manny
  is textured now)
- Modify: `SkeldarAnim/assets/character_portraits/Manny.png` (re-rendered)
- Modify: `sources/README.md`, `CLAUDE.md` (own hunk only)

- [ ] Step 1: write the verify (the spec's Proof list) and run it standalone.
- [ ] Step 2: re-run `verify_rig_pipeline.py`, `verify_many_rigs.py`, `verify_add_character.py`,
  `verify_one_shader.py`, `verify_orc_d_rig_asset.py` standalone.
- [ ] Step 3: portrait in a disposable GUI Maya (free port, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`).
- [ ] Step 4: commit own files; install into the animator's Maya from a `git archive` snapshot; docs.

# Orc D (textured) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** «Orc D [rig]» — SK_Orc_Marauder_D on the shipped Orc rig, arriving in Unreal's textures.

**Architecture:** Three mayapy scripts build the data (sources from Unreal, 2048 JPG maps with
Unreal's material maths baked in, the `.ma` = `Orc_Rig.ma` with D's mesh re-skinned onto the game
joints and three textured phongs whose file nodes name their images relative to `assets/`). The
plugin gains one catalog column (`Character.textured`), one colour function (`relink_images`), and
the textured branch of Add Character.

**Tech Stack:** Maya 2027 mayapy, maya.cmds, OpenMaya 2, numpy 2.3 + PySide6 QImage (images),
Epic's remote_execution via `maya_uebridge.uelink`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-28-orc-d-textured-design.md`.
- Textures 2048² JPG (eye 1024²), the cloth cut-out a PNG with alpha clipped at 0.3333 (0/255).
- `maya_scenesetup.catalog` stays stdlib-only; `colour` stays a leaf (cmds only).
- No absolute path of this machine inside `Orc_D_Rig.ma`; no `createNode script`.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`

---

### Task 1: Sources from Unreal

**Files:** Create `docs/superpowers/plans/export_orc_d_from_unreal.py`; `sources/orc/SK_Orc_Marauder_D.fbx`,
`sources/orc/textures/*.png` (7), `sources/orc/orc_d_materials.json`; Modify `sources/README.md`.

- [ ] Script: `uelink.run_script` exporting the FBX (LOD0, morph targets), the seven textures
  (Body_BaseColor, Body_Normal, Body_Tatoo_Mask, Cloth_BaseColor, Cloth_Normal,
  Eyes_ScleraBaseColor, Eyes_BaseColor) and the parameters (instance scalars/vectors, the atlas
  curve's 64 samples, the cloth clip) into the JSON.
- [ ] Run it; check the files; README rows.

### Task 2: The maps

**Files:** Create `docs/superpowers/plans/make_orc_d_textures.py` → `SkeldarAnim/assets/Orc_D/`
(`Orc_D_Body_Color.jpg`, `Orc_D_Body_Normal.jpg`, `Orc_D_Cloth_Color.jpg`, `Orc_D_Cloth_Normal.jpg`,
`Orc_D_Cloth_Mask.png`, `Orc_D_Eye_Color.jpg`).

- [ ] numpy, in linear: body `lerp(pow(b·I, C), T·atlas(u), m.R·P)`, cloth `b·1.5`, eye composite;
  back to sRGB; 2048 by area average (the eye 1024); normals G → 255−G; the cut-out `a ≥ 0.3333`.
- [ ] Self-checks printed: max linear value < 1 before encoding; the maps' sizes.

### Task 3: catalog + colour + character (TDD)

**Files:** Modify `SkeldarAnim/maya_scenesetup/catalog.py`, `colour.py`, `character.py`, `window.py`;
Test `tests/test_scenesetup_catalog.py`, `tests/test_scenesetup_colour.py`,
`tests/test_scenesetup_character.py`, `tests/test_scenesetup_window.py`.

**Interfaces (produced):**
- `catalog.Character(key, label, file, kind, textured=False)`; row
  `Character("Orc_D_Rig", "Orc D [rig]", "Orc_D_Rig.ma", "rig", textured=True)` at index 3.
- `catalog.asset_path(relative) -> str` (forward slashes, under `assets/`).
- `colour.ASSET_IMAGE = "skeldarAssetImage"`;
  `colour.relink_plan(images, resolve, exists) -> (links, missing)` pure:
  `images` = `[(file_node, relative)]`, `links` = `[(file_node, absolute)]`, `missing` = absolutes
  not on disk; `colour.relink_images(nodes, resolve) -> (relinked_count, missing)`.
- `character.appearance(textured, rgb, switched, missing) -> str` pure.
- `character.add_character(entry, rgb)`: a textured entry is not painted; its images relinked;
  `colour.show_textures()`; the message's appearance from `appearance`.
- `window.add_character()`: the swatch advanced only for an untextured entry.

- [ ] Failing tests for each; implement; green; commit.

### Task 4: The asset

**Files:** Create `docs/superpowers/plans/make_orc_d_rig_asset.py` → `SkeldarAnim/assets/Orc_D_Rig.ma`.

- [ ] Open `Orc_Rig.ma` (no script nodes executed); delete `Orc_Body`, its deformers and the five
  materials; import the D FBX into namespace `srcD`; build `Orc_D_Body` in world space from its
  Orig at bind with the proxy faces removed (vertex map old→new by order, checked by position);
  one UV set `map1`; blendShape `Orc_D_Body_blendShapes` from the 56 targets sampled off the
  source (weight 1 each, at bind); skinCluster on the rig's game joints with the source's weights
  by joint name; the per-face materials (body, cloth incl. Skirt_Sim, eye) as three textured
  phongs; the source removed; the bind pose saved whole; the Orc_Rig clean-up; saved `.ma`, script
  nodes cut, banned words refused (`C:/`, `scratchpad`, `Unreal Projects`, `srcD:`, `Skirt_Proxy`).

### Task 5: Proof

**Files:** Create `docs/superpowers/plans/verify_orc_d_rig_asset.py`.

- [ ] Standalone gates listed in the spec; run; fix until green.
- [ ] A disposable Maya playblast of the textured orc; look at it.

### Task 6: Ship

- [ ] Full unit run; `make_build.py`; the installed copy refreshed in the animator's Maya
  (`install.install(quiet=True)` over port 7001); CLAUDE.md section; commits (only this work's
  hunks).

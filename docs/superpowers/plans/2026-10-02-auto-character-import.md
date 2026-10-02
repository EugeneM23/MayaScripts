# The «?» (Auto) character card - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With the Auto portrait picked, every import road puts a clip on OUR rig/skeleton whose skeleton the clip's
is, and otherwise keeps the clip's own skeleton (with Unreal's mesh) as a character.

**Architecture:** a stdlib matcher over shipped per-row bone templates (`skeletonmatch`), a scene reader + the
one-clip press (`autoimport`), the native keeper (`nativeimport`), and the existing roads (`window`, `lineimport`,
`listdrag`) branching on `scene_window.auto_kind()`. The catalog gains a pseudo-model `Auto` with no row.

**Tech Stack:** Maya 2027 `maya.cmds`, mayapy `unittest` (`-m unittest discover -s tests -t .`), PySide6 for the
grid, Unreal Python Remote Execution for the export.

Spec: `docs/superpowers/specs/2026-10-02-auto-character-import-design.md`.

## Global Constraints

- `skeletonmatch.py` imports the stdlib only (a subprocess test, like `records.py`).
- Thresholds: TOLERANCE 0.01, SHORTEST 1.0 cm, MIN_SHARE 0.75, MIN_BONES 10, 9 sampled frames.
- Helpers never vote: `ik_`, `weapon_`, `camera_` prefixes; `root`, `pelvis`, `center_of_mass`, `interaction`.
- An explicit target (selection naming a character of the kind, a drop on a character) wins over Auto.
- The kind is kept: Rig matches rig rows only, Skeleton skeleton rows only.
- A native is painted in the next free palette colour; no textures.
- No `mel.eval` of AdvancedSkeleton; every Maya-side step of the native runs unrecorded (trap 115).
- Never `cmds.undo()` over the port; verify scripts in mayapy standalone or a disposable Maya.

## File structure

| file | responsibility |
|---|---|
| `SkeldarAnim/maya_uebridge/skeletonmatch.py` (new) | templates loading, `score`, `match`, wording - pure |
| `SkeldarAnim/assets/character_skeletons.json` (new) | per catalog row: file, sha1, bones `{leaf: [parent, x, y, z]}` |
| `docs/superpowers/plans/make_character_skeletons.py` (new) | writes the JSON (mayapy) |
| `SkeldarAnim/maya_uebridge/autoimport.py` (new) | `clip_bones`, `match_clip`, `import_auto`, `explicit_rig`, `explicit_skeleton` |
| `SkeldarAnim/maya_uebridge/nativeimport.py` (new) | `keep` - the clip's skeleton as a character; pure helpers `native_base`, `local_delta` |
| `SkeldarAnim/maya_uebridge/uescripts.py` | `export_script(..., preview_mesh=False)` |
| `SkeldarAnim/maya_uebridge/window.py` | Auto branches in `import_selected` / `import_dropped`; `_export_from_editor(record, mesh=False)` |
| `SkeldarAnim/maya_uebridge/lineimport.py` | `run(..., auto=None)`; per-clip targets; `auto_summary` |
| `SkeldarAnim/maya_uebridge/listdrag.py` | Auto captions; `aim["auto"]` |
| `SkeldarAnim/maya_scenesetup/catalog.py` | `AUTO`, `is_auto`, `kinds_of(AUTO)`, Auto in `MODELS` |
| `SkeldarAnim/maya_scenesetup/window.py` | `current_choice`, `auto_kind`, Auto line, + Import refusal, dropdown rows |
| `SkeldarAnim/maya_charlook.py` | `auto_text`, `AUTO_ADD`, `AUTO_CAPTION` |
| `SkeldarAnim/maya_chargrid.py` | Auto: no drag, no menu |
| `SkeldarAnim/assets/character_portraits/Auto.png` + `docs/superpowers/plans/make_auto_portrait.py` | the «?» |
| `docs/superpowers/plans/verify_auto_character.py` | standalone proof on Unreal exports on disk |

### Task 1: the matcher and the templates

**Files:** create `skeletonmatch.py`, `make_character_skeletons.py`, `assets/character_skeletons.json`,
`tests/test_uebridge_skeletonmatch.py`.

**Interfaces - produces:**
- `skeletonmatch.Score(key, share, count, median)`; `Match(key, scores, kind)`.
- `score(clip, template) -> Score` - `clip` `{leaf: (parent leaf or None, [(x,y,z), ...])}`, `template`
  `{leaf: (parent leaf or None, (x,y,z))}`.
- `match(clip, templates, keys) -> Match` - `templates` `{row key: template}`, `keys` the rows asked (catalog order).
- `load_templates(path=None) -> {row key: template}` (cached); `TEMPLATES_PATH`.
- `match_text(m, label_of) -> str`.

- [ ] Test: synthetic chain clip equal to its template → share 1.0; scaled 1.1 → 0.0; helpers ignored; anchor
  mismatch skipped; `match` picks the best ≥ MIN_SHARE, None under it, None under MIN_BONES; ties by key order.
- [ ] Test on the shipped JSON: every catalog row has an entry with the asset's sha1; each rig template as a clip
  matches itself among rig rows; Manny's skeleton template among skeleton rows matches Manny; Orc D's template
  among skeleton rows matches nothing (best Manny < 0.75).
- [ ] Implement, run mayapy `make_character_skeletons.py`, run tests, commit.

### Task 2: Unreal exports the mesh on request

**Files:** `uescripts.py`, `window.py` (`_export_unreal`, `_export_from_editor`), tests in
`tests/test_uebridge_uescripts.py` / `test_uebridge_window.py`.

- [ ] Test: `export_script(out, pkg, fbx)` carries `("export_preview_mesh", False)`; `preview_mesh=True` carries
  `True`; `_export_from_editor(record, mesh=True)` passes it for an Unreal record, ignores it for a file record.
- [ ] Implement, test, commit.

### Task 3: the Auto card

**Files:** `catalog.py`, `maya_charlook.py`, `maya_chargrid.py`, `maya_scenesetup/window.py`,
`make_auto_portrait.py`, `assets/character_portraits/Auto.png`; tests `test_scenesetup_catalog.py`,
`test_chargrid.py`, `test_charlook.py`, `test_scenesetup_window.py`.

**Produces:** `catalog.AUTO`, `catalog.is_auto(model)`; `window.current_choice() -> (model, kind)`,
`window.auto_kind() -> "rig"|"skeleton"|None`; `charlook.auto_text(kind)`, `charlook.AUTO_ADD`.

- [ ] Tests: MODELS ends with Auto; `kinds_of(AUTO) == KINDS`; `character_for(AUTO, k)` None; the portrait PNG
  256x256 RGBA; grid: Auto available in both kinds, `context_actions(AUTO) == []`, a press on Auto never starts a
  drag, `drop_at(model=AUTO)` refuses; window: `auto_kind()` from the optionVars and from the dropdown labels,
  `add_character` refuses Auto with `AUTO_ADD`, `_say_choice` writes `auto_text(kind)`.
- [ ] Implement, draw the PNG (mayapy offscreen), test, commit.

### Task 4: the native character

**Files:** create `nativeimport.py`, `tests/test_uebridge_nativeimport.py`.

**Produces:** `nativeimport.keep(namespace, info, source, name, point=None, why="") -> (line, failure, top)`;
pure `native_base(meshes, namespace, root_leaf)`, `local_delta(delta, parent_inverse)`, `line_for(...)`.

- [ ] Tests on the pure helpers (largest mesh names the base; a turned parent maps the move; the wording).
- [ ] Implement `keep` (UUIDs, place by keys, group, merge namespaces deepest first, paint, record, label).
- [ ] Commit; proven in Task 7.

### Task 5: the one-clip press and the roads

**Files:** create `autoimport.py`; modify `uebridge/window.py`; tests `tests/test_uebridge_autoimport.py`,
`test_uebridge_window.py`.

**Produces:** `autoimport.import_auto(ref, name, kind, clip_fps=None, set_timeline=True, at=None) -> str`;
`autoimport.explicit_rig(selected_rigs) -> (rig, refusal)` (pure); `autoimport.explicit_target(kind)`.

- [ ] Tests (fakes): a matched rig row goes through `ready_rig`/`retarget_imported` with that entry; a matched
  skeleton row through `onto_skeleton(entry...)`; no match through `nativeimport.keep`; an import failure removes
  the namespaces; window: Auto + New → `import_auto`; Auto + Onto + a selected rig → today's road onto it; Auto +
  Onto + nothing → `import_auto`; several → `lineimport.run(..., auto=kind)`; the export asks for the mesh.
- [ ] Implement, test, commit.

### Task 6: several clips and the drag

**Files:** `lineimport.py`, `listdrag.py`, `uebridge/window.py` (`import_dropped`); tests
`test_uebridge_lineimport.py`, `test_uebridge_listdrag.py`.

- [ ] Tests: `auto_summary` wording; `run(..., auto="rig")` sends matched clips to `_onto_new_rig` with their own
  plan and natives to `nativeimport.keep`, one `_Versions` per row; `caption` for an auto aim (one, several);
  `Scene.target` marks `auto`; `import_dropped` with an auto aim goes to `import_auto` / `run(auto=)`.
- [ ] Implement, test, commit.

### Task 7: proof and docs

**Files:** `docs/superpowers/plans/verify_auto_character.py`, `CLAUDE.md`.

- [ ] Standalone verify on the Unreal exports on disk: the match table; Manny/Orc rig roads exact; UE4 skeleton
  exact; Kwang native (group, layer, plain names, colour, record, label, the clip played exactly, a drop point,
  Delete + undo); a batch of three; explicit target; export of a native.
- [ ] Live: the card in a GUI Maya (the «?» portrait, the line), a real Unreal export + Import Animation with
  Auto, a picture.
- [ ] CLAUDE.md section, installed copy refreshed from a `git archive`, commit.

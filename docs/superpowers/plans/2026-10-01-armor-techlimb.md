# Armor Card + Tech Limb Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Atone's Tech Limb plate (`SM_Shield_Test`) shipped as the first row of a new ARMOR table, and a hub card **Armor** whose Equip puts it on the current character's `lowerarm_l` exactly where the game does.

**Architecture:**
- Two dev scripts measure Unreal's placement and bake it into the asset's points, in `lowerarm_l`'s local axes.
- In the scene, `armor.py` hangs the piece in an armor space outside the skeleton; it reuses `weaponspace`, its internals parameterised by marker.
- The card `armorpanel.py` lays a Qt tile grid `maya_armorgrid.py` over a `cmds` placeholder, the Characters grid's pattern.

**Tech Stack:** Maya 2027 `maya.cmds` / OpenMaya 2.0 / PySide6 6.8.3, mayapy unittest, Unreal 5.8 Python Remote Execution through `maya_uebridge.uelink`.

Spec: `docs/superpowers/specs/2026-10-01-armor-techlimb-design.md`.

## Global Constraints

- Tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo root, with `$env:QT_QPA_PLATFORM='offscreen'`.
- The plugin reads nothing outside `SkeldarAnim/`; `tests/test_sources.py` pins that no plugin string names `Animations/` or `Downloads`.
- No `cmds.ls("*.attr")` lookups (trap 70). Identity is by attribute and connection, never by name.
- A file import flushes undo (trap 115). What follows it runs unrecorded.
- Never touch the animator's live Maya on 7001 without asking peers (trap 148). Live checks go in a disposable Maya with a scratch `MAYA_APP_DIR` and `MAYA_NO_HOME=1`.
- Stage only this work's hunks: CLAUDE.md holds a peer's uncommitted Orc D 1P paragraph.

---

### Task 1: Unreal's placement out of the editor

**Files:**
- Create: `docs/superpowers/plans/export_techlimb_from_unreal.py`
- Output: `sources/armor/SM_Shield_Test.fbx`, `sources/armor/techlimb_ue.json`

**Interfaces:** Produces `techlimb_ue.json` = {`socket`, `placement` {`location`, `rotation`, `scale`}, `colour`, `verts_mesh` [[x,y,z]…1526], `verts_bone` (each vertex in `lowerarm_l` space after the BP's offset), `verts_cs` (component space at the reference pose), `bones` {name: {`t`, `x`, `y`, `z`} axes in component space}}.

- [ ] Write the script. It uses `uelink.run_script(UE, REPLY, project="Atone")` with a UE body that:
  - loads `DA_Techlimb` and refuses unless `equip_socket == "lowerarm_l"`;
  - reads the `SM_Shield_Test_GEN_VARIABLE` template through `SubobjectDataSubsystem` and refuses unless its static mesh is `SM_Shield_Test`;
  - builds `rel = unreal.Transform(location, rotation, scale)` from that component's `relative_location` / `relative_rotation` / `relative_scale3d`;
  - takes the bone's ref-pose world transform: `AnimPoseExtensions.get_ref_bone_pose(get_reference_pose(skeleton), "lowerarm_l", AnimPoseSpaces.WORLD)`;
  - for each vertex of `ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, 0)[0]`, records `b = MathLibrary.transform_location(rel, v)` and `cs = MathLibrary.transform_location(bone, b)`;
  - records each bone's `t` and axes (`transform_direction` of the unit X/Y/Z, scale stripped);
  - exports the static mesh with `AssetExportTask` (`automated=True`, `prompt=False`, trap 24).
- [ ] Run it with mayapy and confirm the FBX lands, 1526 vertices.
- [ ] Commit the script and `sources/armor/` (the FBX is 1526 vertices, small).

### Task 2: The asset — points in `lowerarm_l`'s axes

**Files:**
- Create: `docs/superpowers/plans/ue_maya_axes.py` (numpy helpers shared with the verify)
- Create: `docs/superpowers/plans/make_techlimb_asset.py`
- Output: `SkeldarAnim/assets/Armor/Tech_Limb.fbx`

`ue_maya_axes.py`:

```python
import numpy as np

def signed_permutations():
    """The 48 signed 3x3 permutation matrices."""

def nearest(a, b):
    """For each row of a, (index into b, distance) - brute force, fine for 1-2k points."""

def best_map(a, b):
    """The signed permutation P with max over a of |P a - nearest b| smallest; (P, that max)."""

def round_to_permutation(m):
    """The signed permutation nearest the 3x3 `m` (argmax per row), and the max deviation."""

def ue_to_maya(ue_bones, maya_bones):
    """M (3x3, column vectors) with maya = M @ ue over the shared bones' positions, as a signed
    permutation: the least-squares fit rounded. Returns (M, worst residual cm)."""

def row_world(matrix16):
    """Maya's row-major worldMatrix -> (A 3x3 with axes as COLUMNS, t)."""
```

`make_techlimb_asset.py` (mayapy standalone):
1. `M, res_bones = ue_to_maya(json bones, template world positions)`, using `assets/manny_skeleton_template.json`. Refuse if `res_bones > 0.05`.
2. `A, t = row_world(template lowerarm_l)`. `R_b` = the UE bone axes as columns. `N = A.T @ M @ R_b`, rounded to a signed permutation; refuse if the deviation is over 1e-4. (The joint and bone frames agree up to the axis convention.)
3. Target joint-local points `q = N @ verts_bone`. Check `A @ q + t` against `M @ verts_cs`, worst under 0.01 cm: Unreal's reference pose is Manny's bind.
4. Import the FBX (add mode), then `makeIdentity(apply=True)` and one mesh. Read the points. `P, d = best_map(points, verts_mesh)`, `d < 1e-3`. Match each Maya point to its UE vertex.
5. Fit the similarity X (rotation, uniform scale, translation; Umeyama) taking the Maya points onto the matched `q`. Refuse unless the residual is under 1e-3 and det > 0. Set the node's matrix to X, then `makeIdentity(apply=True)`, so the normals turn with the points.
6. Rename it `TechLimbMesh`, give it a plain lambert, delete everything else, export with `FBXExport -s` to `SkeldarAnim/assets/Armor/Tech_Limb.fbx`.
7. Read it back in a new scene: one mesh, identity transform, points on `q` to 1e-3.

- [ ] Write both files; run; record the numbers printed (M, N, residuals, scale ≈ 1.17647).
- [ ] Commit.

### Task 3: The catalog's ARMOR table

**Files:** Modify `SkeldarAnim/maya_scenesetup/catalog.py`; Test `tests/test_scenesetup_catalog.py`.

```python
Armor = collections.namedtuple("Armor", "key label path bone slot texture", defaults=("",))
ARMOR = [Armor("Tech_Limb", "Tech Limb", _asset_path("Armor/Tech_Limb.fbx"), "lowerarm_l",
               "left_forearm")]
def armor_labels(): return [e.label for e in ARMOR]
def armor_by_key(key): ...          # None when unknown
def armor_by_label(label): ...
def armor_icon_path(key): return asset_path("armor_icons/{0}.png".format(key))
```

- [ ] Tests:
  - the row's file exists;
  - its icon exists (after Task 6, so this test lands in Task 6);
  - the keys are legal node names (`node_key(k) == k`) and unique;
  - `missing(row) == ""`;
  - lookups;
  - the slot is non-empty.
- [ ] Run, fail, implement, pass, commit.

### Task 4: Armor spaces — `weaponspace` parameterised, `skeleton` resolving them

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/weaponspace.py`, `skeleton.py`
- Test: `tests/test_scenesetup_armor.py` (new; fake cmds)

New public generic functions in `weaponspace`:
- `marked_space_of(bone, marker)`
- `bone_of(space)` (= `hand_of`)
- `owner_for(path, marker)`
- `ensure_marked_space(bone, marker, group_marker, group_name, suffix)`
- `prune_marked(space, marker, group_marker)`

The weapon API (`is_space`, `space_of`, `hand_of`, `hand_for`, `ensure_space`, `prune`, `group_for`) wraps them with the weapon markers. `skeleton.current_root` maps a selected path through `weaponspace.hand_for(path) or armor.bone_for(path) or path`.

- [ ] Tests (fake cmds):
  - an armor space is not a weapon space and vice versa;
  - `ensure_marked_space` names `<bone>_armorSpace`, marks it, constrains with no offset, lives in the marked group;
  - `prune_marked` deletes the space and the empty group.
- [ ] Implement; the existing weapon tests stay green; commit.

### Task 5: `armor.py` — equip, unequip, worn

**Files:** Create `SkeldarAnim/maya_scenesetup/armor.py`; Test `tests/test_scenesetup_armor.py`.

Pure:
- `slot_plan(worn, entry)`: the sorted keys of `worn` ({key: slot}) in `entry.slot`, plus `entry.key` if worn;
- `equipped_message(label, bone, character, replaced, colour_name)`;
- `unequipped_message(label, character)`;
- `not_worn_message(label, character)`;
- `no_bone_message(label, bone, character)`;
- `missing_message(label, path)`.

Scene:
- `bone_for(path)`;
- `pieces()`: every marked piece in the scene, as (node, key, slot, bone), found through the ArmorSpaces groups among assemblies and their children;
- `worn(root)`: {key: (node, slot)} for the pieces whose bone is `root` or under it;
- `equip(root, entry, rgb=None)` (import, then unrecorded dressing);
- `unequip(root, key)` (one undo chunk).

- [ ] Tests: the pure functions, plus `equip` / `unequip` against a scripted fake (the parent call, the markers, the seat, the prune, the slot replace), then implement and commit.

### Task 6: The icon and the `shield` hub icon

**Files:**
- Create: `docs/superpowers/plans/make_armor_icons.py`
- Output: `SkeldarAnim/assets/armor_icons/Tech_Limb.png`
- Modify: `SkeldarAnim/maya_hubicons.py` (`"shield"`, Tabler outline: `"M12 3a12 12 0 0 0 8.5 3a12 12 0 0 1 -8.5 15a12 12 0 0 1 -8.5 -15a12 12 0 0 0 8.5 -3"`)

- [ ] The renderer:
  - imports each ARMOR row's FBX;
  - projects its triangles along the mesh's thinnest bbox axis, back to front;
  - flat-shades them steel with the weapon icons' light;
  - pads them into a 256 px transparent square.
- [ ] Add the catalog test "every ARMOR row has its icon" and the hubicons test entry; commit.

### Task 7: `maya_armorgrid.py` — the tiles

**Files:** Create `SkeldarAnim/maya_armorgrid.py`; Test `tests/test_armorgrid.py`.

- `Scene`: `scale`, `select(key)`, `open_scene(key)`, `worn()` (a set of keys), `say(text)`, calling `armorpanel`.
- `ArmorGrid(QWidget)`:
  - `rows` = `catalog.ARMOR`; `selected`; `worn`;
  - `height_for`, `rects`, `fit` (the `maya_charlook.grid` layout);
  - `key_at`, `select`, `refresh()` (re-reads `worn`), `context_actions(key)` ([("Open scene", fn)]);
  - paints like the portraits, with an «equipped» pill on a worn row;
  - `mousePressEvent`: left picks, right opens the menu (`maya_hubqt.run_menu`).
- `make_grid(scene, parent, selected)`, `attach(placeholder, scene, selected)` (the Keeper from `maya_chargrid._classes()`), `live(placeholder)`.

- [ ] Offscreen tests:
  - it paints ink;
  - a click selects and tells the scene;
  - a worn row draws the pill (pixels differ from an unworn render);
  - the context menu offers Open scene and calls the scene;
  - an empty spot offers nothing;
  - `height_for` grows with rows.
- [ ] Implement; commit.

### Task 8: The card, the hub section, the hotkey row, the payload

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/armorpanel.py`
- Modify: `SkeldarAnim/maya_hub.py` (Section after weapons), `SkeldarAnim/maya_hotkeys.py` (`window.armor`), `SkeldarAnim/install.py` (`maya_armorgrid.py`)
- Tests: `tests/test_hub_sections.py` (an `Armor` class), `tests/test_hub.py` (order and labels), `tests/test_hotkeys.py` (count 36), `tests/test_install.py` (if it lists rows)

`armorpanel`:
- constants: `HUB_SECTION = "armor"`, `_STATUS`, `_BOUND`, `_TILES`, `_MENU`, `_OPTIONVAR = "mayaSceneSetup_armor"`;
- `chosen_armor()`, `select_armor(key)`, `worn_keys()`, `refresh()`;
- `equip_armor()`, `unequip_armor()`, `open_armor_scene(key)`;
- `is_open()`, `show_window()`;
- `build_panel()`: subtitle, placeholder (the grid laid over it, else a dropdown), an Equip (primary, "shield") / Unequip (danger, "trash") row, the status line, a `SelectionChanged` scriptJob parented to the status line that calls `refresh`.

- [ ] Tests:
  - the named controls, one primary, no window;
  - `show_window` asks the hub for "armor";
  - Equip and Unequip report on the line;
  - the dropdown only without the grid;
  - the hub order puts armor after weapons in the scene group;
  - the hotkey row exists.
- [ ] Full test suite green; commit.

### Task 9: `verify_armor.py` (mayapy standalone) + live card check

**Files:** Create `docs/superpowers/plans/verify_armor.py`.

- [ ] Gates:
  1. Equip on Manny_Rig: every plate vertex, in world, on `M @ verts_cs` to 1e-3 cm; channels 0.
  2. The space is outside the skeleton, under the rig group.
  3. The same on the Creep and the Orc D, on their own `lowerarm_l`.
  4. A UE clip (`Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX`) through `maya_rig_retarget.run_retarget` onto Manny: the plate's world = its local · bone world at sampled frames to 1e-6.
  5. `animexport.export_hierarchy` read back: joints only.
  6. A second Equip: still one piece.
  7. Unequip on each: no armor node or group left.
  8. The other characters unmoved.
- [ ] Run until green; then in a disposable GUI Maya: build the hub, click the tile, press Equip / Unequip through Qt, playblast. Update CLAUDE.md (a new section), commit; ask before push.

# The weapon is the geometry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add parents the weapon's mesh transform straight into the bone — no group — and a text field can point Add at any FBX on disk.

**Architecture:** `attach.attach` gains one decision (which of the imported transforms hold a mesh) and loses the unconditional carrier. The marked-node concept survives untouched, so every consumer keeps working. `catalog` gains a pure constructor for an off-catalog entry; `window` gains one field and one pure resolver.

**Tech Stack:** Python 3 for Maya 2027, `maya.cmds` window, stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-20-weapon-is-the-geometry-design.md`.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` — 679 green before this change. Never pipe `mayapy` through `2>&1` in PowerShell; commit messages go through a file and `git commit -F`.
- `catalog.py` must stay **stdlib-only** — a subprocess test in `tests/test_scenesetup_catalog.py` enforces it. `os.path` is fine, `maya.cmds` is not.
- The marker attribute stays `mayaWeapon` (it is written into the animator's files) and the offset optionVar keeps reading the legacy `mayaWeapons_offset_*` name.
- Every window callback goes through `_run`, so a failure lands on the status line and not in the Script Editor.

---

### Task 1: An entry for any FBX on disk

**Files:**
- Modify: `maya_scenesetup/catalog.py`
- Test: `tests/test_scenesetup_catalog.py`

**Interfaces:**
- Produces: `catalog.node_key(text) -> str`, `catalog.entry_for_path(path, bone) -> Weapon`

- [ ] **Step 1: Write the failing tests**

```python
class NodeKey(unittest.TestCase):

    def test_a_plain_name_is_untouched(self):
        self.assertEqual(catalog.node_key("LongSword_02"), "LongSword_02")

    def test_spaces_and_dots_become_underscores(self):
        """The key names an objectSet through the aim manifest, so a space or
        a dot in it is a future cmds.sets traceback."""
        self.assertEqual(catalog.node_key("My Sword v1.2"), "My_Sword_v1_2")

    def test_a_leading_digit_gets_a_prefix(self):
        self.assertEqual(catalog.node_key("2handed"), "_2handed")

    def test_non_ascii_is_replaced(self):
        self.assertEqual(catalog.node_key("мечи"), "____")

    def test_empty_becomes_a_usable_name(self):
        self.assertEqual(catalog.node_key(""), "weapon")


class EntryForPath(unittest.TestCase):

    def test_key_and_label_come_from_the_file_stem(self):
        entry = catalog.entry_for_path("D:/props/Axe_01.FBX", "weapon_r")
        self.assertEqual(entry.key, "Axe_01")
        self.assertEqual(entry.label, "Axe_01")

    def test_the_path_is_kept_verbatim(self):
        entry = catalog.entry_for_path("D:/props/Axe_01.FBX", "weapon_r")
        self.assertEqual(entry.path, "D:/props/Axe_01.FBX")

    def test_the_bone_is_the_callers(self):
        self.assertEqual(
            catalog.entry_for_path("D:/a.fbx", "weapon_l").bone, "weapon_l")

    def test_scale_is_one_never_the_catalogs(self):
        """A scale correction is a fact about one known model; applying the
        sword's to somebody else's file is a surprise."""
        self.assertEqual(catalog.entry_for_path("D:/a.fbx", "weapon_r").scale,
                         1.0)

    def test_a_windows_path_works_too(self):
        entry = catalog.entry_for_path(r"D:\props\Big Axe.fbx", "weapon_r")
        self.assertEqual(entry.key, "Big_Axe")
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

```python
def node_key(text):
    """`text` reduced to a legal Maya node name.

    The key is not only a marker value: it names the aim manifest, which
    reaches `cmds.sets`, and an optionVar. A space, a dot or a leading digit
    there is a traceback later, on a press that has nothing to do with this.
    """
    safe = "".join(c if c in _LEGAL else "_" for c in text)
    if not safe:
        return "weapon"
    return "_" + safe if safe[0].isdigit() else safe


def entry_for_path(path, bone):
    """An entry for a file the catalog knows nothing about.

    Scale is 1.0 rather than the dropdown's: see node_key's neighbours in the
    spec -- a size correction belongs to a model we know, not to any file.
    """
    stem = os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
    key = node_key(stem)
    return Weapon(key, key, path, bone, 1.0)
```

with `_LEGAL = set(string.ascii_letters + string.digits + "_")` and
`import string` beside `import os`.

- [ ] **Step 4: Run the tests, then the whole suite**

- [ ] **Step 5: Commit**

---

### Task 2: Attach the mesh, not a group

**Files:**
- Modify: `maya_scenesetup/attach.py`
- Test: `tests/test_scenesetup_attach.py`

**Interfaces:**
- Consumes: `catalog.Weapon` (unchanged fields).
- Produces:
  - `attach.group_name(key)` (was `carrier_name`)
  - `attach.mesh_transforms(paths) -> [str]`
  - `attach.model_root(node)` — now answers `node` itself when it holds a mesh
  - `attach.attach(entry, bone, rotate, translate) -> (path, note)`

  **The return type changes**: a tuple of the attached node and a note
  (`""` when the mesh went in alone, a sentence when the group fallback ran).
  `window.add_weapon` is the only caller and Task 3 updates it.

- [ ] **Step 1: Write the failing tests**

```python
class MeshTransforms(unittest.TestCase):

    def test_finds_the_one_transform_holding_a_mesh(self):
        attach.cmds = FakeModel({}, with_mesh=["|Sword"])
        self.assertEqual(attach.mesh_transforms(["|Sword", "|null1"]),
                         ["|Sword"])

    def test_looks_below_a_wrapper_null(self):
        """An exporter that wraps the mesh in a null is the group the animator
        is trying to be rid of, so the mesh under it still counts."""
        attach.cmds = FakeModel({"|null1": ["|null1|Sword"]},
                                with_mesh=["|null1|Sword"])
        self.assertEqual(attach.mesh_transforms(["|null1"]), ["|null1|Sword"])

    def test_two_meshes_are_both_reported(self):
        attach.cmds = FakeModel({}, with_mesh=["|blade", "|guard"])
        self.assertEqual(attach.mesh_transforms(["|blade", "|guard"]),
                         ["|blade", "|guard"])

    def test_nothing_when_no_mesh_arrived(self):
        attach.cmds = FakeModel({}, with_mesh=[])
        self.assertEqual(attach.mesh_transforms(["|locator1"]), [])


class ModelRootIsTheNodeItself(unittest.TestCase):

    def test_a_marked_mesh_transform_answers_itself(self):
        """With no carrier the marked node IS the geometry, and a mesh the
        animator parented under it must not outrank it."""
        attach.cmds = FakeModel({"|Sword": ["|Sword|somebodyElse"]},
                                with_mesh=["|Sword", "|Sword|somebodyElse"],
                                direct_mesh=["|Sword"])
        self.assertEqual(attach.model_root("|Sword"), "|Sword")

    def test_a_group_still_answers_the_model_inside(self):
        attach.cmds = FakeModel({"|weapon": ["|weapon|Sword"]},
                                with_mesh=["|weapon|Sword"], direct_mesh=[])
        self.assertEqual(attach.model_root("|weapon"), "|weapon|Sword")
```

`FakeModel` gains a `direct_mesh` list and answers
`listRelatives(node, children=True, type="mesh")` from it, alongside the
existing `allDescendents` answer. Existing `ModelRoot` tests pass
`direct_mesh=[]`.

Rename the existing name test:

```python
    def test_names_the_fallback_group_after_the_weapon(self):
        self.assertEqual(attach.group_name("LongSword_02"),
                         "LongSword_02_weapon")
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

`mesh_transforms`:

```python
def mesh_transforms(paths):
    """The transforms at or below `paths` that hold a mesh shape.

    Deduplicated and in order. This is what decides whether Add needs a group
    at all: exactly one mesh transform is the weapon, and anything else the
    file brought is scaffolding.
    """
    found = []
    for path in paths:
        candidates = [path] + (cmds.listRelatives(
            path, allDescendents=True, type="transform", fullPath=True) or [])
        for candidate in candidates:
            if (cmds.listRelatives(candidate, children=True, type="mesh")
                    and candidate not in found):
                found.append(candidate)
    return found
```

`model_root` gains one question in front:

```python
def model_root(node):
    # With no group the marked node IS the geometry. Ask that first: a mesh
    # the animator parented under the sword by hand would otherwise outrank
    # the sword itself.
    if cmds.listRelatives(node, children=True, type="mesh"):
        return node
    for child in ...unchanged...
```

`attach` becomes:

```python
def attach(entry, bone, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0)):
    """Put `entry`'s model into `bone`. Returns (attached path, note).

    One mesh in the file and the mesh itself is the weapon -- parented into
    the bone, marked, seated, holding the offsets on its own channels, and
    the scaffolding the file came wrapped in deleted. Zero or two meshes keep
    the old group: two of them cannot both be the node the offsets live on,
    and one click cannot select both.

    Whatever was attached before is removed first: one weapon per bone, so
    the offset fields always have exactly one thing to move. All of it is one
    undo chunk -- a half-undone import leaves geometry with no home.
    """
    cmds.undoInfo(openChunk=True)
    try:
        remove_attached(bone)
        roots = import_model(entry.path)
        if not roots:
            raise RuntimeError("nothing came out of " + entry.path)

        meshes = mesh_transforms(roots)
        note = ""
        if len(meshes) == 1:
            weapon = cmds.ls(cmds.parent(meshes[0], bone)[0], long=True)[0]
            leftovers = [r for r in cmds.ls(roots, long=True) or []
                         if cmds.objExists(r) and r != weapon]
            if leftovers:
                cmds.delete(leftovers)
        else:
            # Built empty and filled rather than grouping the model: a group
            # made around geometry takes that geometry's pivot with it, and
            # the pivot then has to be undone on the other side (trap 32).
            group = cmds.group(empty=True, world=True,
                               name=group_name(entry.key))
            cmds.parent(roots, group)
            weapon = cmds.ls(cmds.parent(group, bone)[0], long=True)[0]
            note = "{0} mesh(es) in the file - kept in a group".format(
                len(meshes))

        cmds.addAttr(weapon, longName=MARKER, dataType="string")
        cmds.setAttr(weapon + "." + MARKER, entry.key, type="string")
        seat(weapon, entry.scale)
        write_offsets(weapon, rotate, translate)
        return weapon, note
    finally:
        cmds.undoInfo(closeChunk=True)
```

Note the ORDER: `cmds.parent` first, marker second, `seat` third. Parenting is
what leaves the pivot compensation in `rotatePivotTranslate` that `seat` has to
clear, so seating before the parent would prove nothing.

Update the module docstring: the offsets live on the weapon itself now, and the
marker is still the only way anything is found.

- [ ] **Step 4: Run the suite**

- [ ] **Step 5: Commit**

---

### Task 3: The rename, and the callers

**Files:**
- Modify: `maya_scenesetup/connect.py`, `maya_scenesetup/aim.py`, `maya_scenesetup/window.py`
- Modify: `docs/superpowers/plans/verify_connect_arms.py`, `docs/superpowers/plans/verify_weapon_aim.py`
- Test: `tests/test_scenesetup_connect.py`

**Interfaces:**
- Produces: `connect.linked_weapon()` (was `linked_carrier`), `connect._is_marked` (was `_is_carrier`).

- [ ] **Step 1: Write the failing test**

```python
    def test_the_linked_weapon_is_found_under_its_new_name(self):
        self.assertTrue(callable(linking.linked_weapon))
        self.assertFalse(hasattr(linking, "linked_carrier"))
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Rename**

`connect.py`: `linked_carrier` → `linked_weapon`, `_is_carrier` → `_is_marked`,
locals `carrier` → `weapon`, and the docstrings that describe the carrier as
"our offset group" now describe the marked weapon node. `connect`'s comment
about hanging on the geometry rather than the carrier keeps its measurement but
gains the reason it is now moot in the single-mesh case.

`aim.py`: parameter `carrier` → `weapon`; the aim handles become
`[model]` when `model == weapon`, otherwise `[model, weapon]` — deduplicated,
since a handle list with the same UUID twice is bookkeeping nobody can read.

`window.py`: `_carrier` → `_attached`, locals renamed, `linking.linked_weapon`.

The two verify scripts: `linked_carrier` → `linked_weapon`, local names left
alone where they are only labels.

- [ ] **Step 4: Run the suite; compile-check both verify scripts**

```bash
mayapy -c "import py_compile;py_compile.compile(r'...verify_connect_arms.py',doraise=True)"
```

- [ ] **Step 5: Commit**

---

### Task 4: The FBX field

**Files:**
- Modify: `maya_scenesetup/window.py`
- Test: `tests/test_scenesetup_window.py`

**Interfaces:**
- Produces: `window.chosen_entry(field_text, entry) -> Weapon`, `window._CUSTOM` field name, `window._CUSTOM_OPTIONVAR`.

- [ ] **Step 1: Write the failing tests**

```python
class ChosenEntry(unittest.TestCase):

    ENTRY = catalog.WEAPONS[0]

    def test_an_empty_field_leaves_the_dropdown_alone(self):
        self.assertIs(window.chosen_entry("", self.ENTRY), self.ENTRY)

    def test_whitespace_is_empty(self):
        """A stray space must not redirect Add at a file called " "."""
        self.assertIs(window.chosen_entry("   ", self.ENTRY), self.ENTRY)

    def test_a_path_wins_over_the_dropdown(self):
        got = window.chosen_entry("D:/props/Axe_01.fbx", self.ENTRY)
        self.assertEqual(got.path, "D:/props/Axe_01.fbx")
        self.assertEqual(got.key, "Axe_01")

    def test_the_bone_comes_from_the_dropdown(self):
        got = window.chosen_entry("D:/props/Axe_01.fbx", self.ENTRY)
        self.assertEqual(got.bone, self.ENTRY.bone)

    def test_the_path_is_stripped(self):
        got = window.chosen_entry("  D:/props/Axe_01.fbx  ", self.ENTRY)
        self.assertEqual(got.path, "D:/props/Axe_01.fbx")
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

```python
def chosen_entry(field_text, entry):
    """The entry a press uses: the FBX field wins when it holds a path."""
    text = (field_text or "").strip()
    if not text:
        return entry
    return catalog.entry_for_path(text, entry.bone)
```

`_entry()` becomes `chosen_entry(cmds.textFieldGrp(_CUSTOM, query=True,
text=True), catalog.by_label(...))`, so every callback — Add, the offset
fields, Connect, Add Aim, refresh — follows the field with no further edits.
The field is created after the dropdown:

```python
    cmds.textFieldGrp(_CUSTOM, label="FBX", text=_remembered_path(),
                      annotation="Paste a path to any .fbx to attach it "
                                 "instead of the dropdown's weapon. The bone "
                                 "comes from the dropdown; scale is 1.",
                      changeCommand=lambda *_args: _run(custom_changed))
```

`custom_changed` remembers the text in `mayaSceneSetup_custom_fbx` and calls
`refresh()`, so the offset fields reload for the new key.

`add_weapon` takes the note from `attach.attach` and appends it to the status
line when it is not empty.

- [ ] **Step 4: Run the suite**

- [ ] **Step 5: Commit**

---

### Task 5: Live gates and the working notes

**Files:**
- Modify: `docs/superpowers/plans/verify_weapons.py`, `CLAUDE.md`

- [ ] **Step 1: Add the gates**

In `verify_weapons.py`, after the first Add:

1. the marked node holds a mesh directly, and its parent is the weapon bone —
   no node of ours in between;
2. exactly one transform under the bone came from us;
3. the weapon's local matrix is identity but for the offsets — worst element 0
   (trap 32, now on the geometry);
4. writing the offset fields moves the MESH the animator selects;
5. the trap-34 gate unchanged: drag the sword after Connect, both hands travel;
6. a custom path through `chosen_entry` attaches and reports its derived key.

- [ ] **Step 2: Send it through the command port, read the output file**

- [ ] **Step 3: Fix what it finds, re-run until green**

- [ ] **Step 4: Update `CLAUDE.md`** — the weapon-attach section (no carrier;
what the marker sits on now; the seat consequence), the FBX field, and the
`catalog` row gaining `entry_for_path`.

- [ ] **Step 5: Commit**

---

## Self-review

**Spec coverage:** mesh-or-group decision → Task 2; leftovers deleted → Task 2;
`model_root` fix → Task 2; renames → Tasks 2 and 3; the field and its key,
bone, scale and memory → Tasks 1 and 4; live gates → Task 5.

**Placeholders:** none.

**Type consistency:** `attach.attach` returns `(str, str)` and Task 4's
`add_weapon` unpacks two values; `chosen_entry` and `entry_for_path` both
return a `catalog.Weapon`; `mesh_transforms` takes and returns long paths.

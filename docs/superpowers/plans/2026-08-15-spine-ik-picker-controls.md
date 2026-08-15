# Spine IK + controller-only picker + single Build — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spine joins the IK/Switch machinery; the picker selects controllers
(FK and IK) instead of bones, dimming what does not exist; Build and Build FK
merge into one Build with an `FK Limbs` toggle.

**Architecture:** `builder.LIMBS` gains a spine entry so every generic
mechanism (manifest, bake, resolve, nesting) covers it; IK controls are found
by role through the limb manifest (`builder.ik_control`); the picker gets a
parallel `IK_BUTTONS` table and a pure resolution module; orchestration of the
hybrid build lives in `fkcontrols.rebuild`.

**Tech Stack:** Maya 2027 mayapy + stdlib unittest, PySide6 offscreen for view
tests, OverRig MEL through `overrig.py`.

## Global Constraints

- `bodymap.py` and the new `pickerstate.py` import stdlib only; `picker_view.py` imports Qt only (subprocess test enforces bodymap).
- Never identify OverRig nodes by bare scene name — manifest membership first.
- Spec: `docs/superpowers/specs/2026-08-15-spine-ik-picker-controls-design.md`.
- Test command: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` (Qt tests need `$env:QT_QPA_PLATFORM='offscreen'`).
- Commit after each green task; messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` via `git commit -F`.

---

### Task 1: Spine in `builder.LIMBS`, `DEFAULT_IK`, `ik_control`

**Files:**
- Modify: `maya_overrig/builder.py` (LIMBS, new constants + function)
- Modify: `maya_overrig/fkcontrols.py:874-886` (`_ik_hand_control` delegates)
- Test: `tests/test_builder.py`

**Interfaces:**
- Produces: `builder.LIMBS` (5 entries, spine = `("pelvis", "spine_03", "spine_05")`); `builder.DEFAULT_IK = ("arm_l", "arm_r", "leg_l", "leg_r")`; `builder.IK_ROLES = {"end": "_IK_feet", "pole": "_IK_knee", "base": "_IK_strech_gr"}`; `builder.ik_control(limb, role) -> long path or None`.

- [ ] Update `TestLimbTable` in `tests/test_builder.py`: five limbs, names `["arm_l", "arm_r", "leg_l", "leg_r", "spine"]`, fifteen distinct joints, `table["spine"] == ("pelvis", "spine_03", "spine_05")`; add:

```python
class TestDefaultIk(unittest.TestCase):

    def test_arms_and_legs_only(self):
        self.assertEqual(builder.DEFAULT_IK,
                         ("arm_l", "arm_r", "leg_l", "leg_r"))

    def test_subset_of_the_limb_table(self):
        names = {name for name, _ in builder.LIMBS}
        self.assertTrue(set(builder.DEFAULT_IK) < names)


class TestIkRoles(unittest.TestCase):

    def test_three_roles(self):
        self.assertEqual(set(builder.IK_ROLES), {"end", "pole", "base"})

    def test_marks_are_distinct_overrig_suffixes(self):
        marks = list(builder.IK_ROLES.values())
        self.assertEqual(len(marks), len(set(marks)))
        for mark in marks:
            self.assertTrue(mark.startswith("_IK_"))
```

- [ ] Run; expect the table tests to fail against the 4-limb table.
- [ ] Implement: extend `LIMBS`, add `DEFAULT_IK`, `IK_ROLES`, and

```python
def ik_control(limb, role):
    """The IK control of a built limb for a role, through its manifest.

    Never by bare scene name -- OverRig suffixes renames on collision, so the
    search space is the limb's own recorded nodes.
    """
    mark = IK_ROLES[role]
    for member in overrig.set_members(limb_set(limb)):
        if not cmds.objExists(member):
            continue
        if mark in member.split("|")[-1] and cmds.objectType(member) in (
                "transform", "joint"):
            return member
    return None
```

- [ ] `fkcontrols._ik_hand_control(limb)` becomes `return builder.ik_control(limb, "end")` (docstring kept).
- [ ] Full suite green; commit `feat(spine): spine enters the IK limb table with role-addressed controls`.

### Task 2: Switch FK/IK covers the spine, dependents re-hung

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`SWITCHABLE`, `dependent_chains`, spine branch in `switch_limbs`)
- Modify: `maya_overrig/picker_window.py:325-351` (`switch_selected_limbs` uses `SWITCHABLE`)
- Test: `tests/test_fkcontrols.py`

**Interfaces:**
- Consumes: `builder.ik_control`, `builder._is_inside`, `builder.build`, `builder.bake_limbs`.
- Produces: `fkcontrols.SWITCHABLE = LIMB_CHAINS + ("spine",)`; `fkcontrols.dependent_chains(root_ctrls, containers) -> [chain names]` (pure); `fkcontrols.SPINE_REHANG = {"spine_05": "end", "pelvis": "base"}`.

- [ ] Tests first:

```python
class TestSwitchable(unittest.TestCase):

    def test_limbs_plus_spine(self):
        self.assertEqual(fkcontrols.SWITCHABLE,
                         ("arm_l", "arm_r", "leg_l", "leg_r", "spine"))


class TestDependentChains(unittest.TestCase):

    def test_finds_chains_rooted_inside_the_containers(self):
        ctrls = {"neck": "|spine_05_FK_ctrl|neck_01_FK_ctrl",
                 "arm_l": "|spine_05_FK_ctrl|clavicle_l_FK_ctrl",
                 "leg_l": "|pelvis_FK_ctrl|thigh_l_FK_ctrl",
                 "arm_r": "|clavicle_r_FK_ctrl"}
        found = fkcontrols.dependent_chains(
            ctrls, ["|spine_05_FK_ctrl", "|pelvis_FK_ctrl"])
        self.assertEqual(found, ["neck", "arm_l", "leg_l"])

    def test_separator_matters(self):
        ctrls = {"neck": "|spine_05_FK_ctrl_extra|neck_01_FK_ctrl"}
        self.assertEqual(
            fkcontrols.dependent_chains(ctrls, ["|spine_05_FK_ctrl"]), [])

    def test_missing_controllers_are_skipped(self):
        self.assertEqual(fkcontrols.dependent_chains({}, ["|x"]), [])


class TestSpineRehang(unittest.TestCase):

    def test_targets_cover_both_attach_bones(self):
        self.assertEqual(fkcontrols.SPINE_REHANG,
                         {"spine_05": "end", "pelvis": "base"})
```

- [ ] Implement `dependent_chains` (pure, CHAINS order, `builder._is_inside`), `SWITCHABLE`, `SPINE_REHANG`; spine branch in `switch_limbs`:
  - detection: containers = spine FK members + spine IK members; root_ctrls = `{chain: cmds.ls(controller_name(first))[0] if exists}` for every chain but spine;
  - `_parent_out` each dependent's root controller (recorded to its own chain set);
  - convert exactly like a limb (same is_ik/is_fk logic — spine skips the finger bracket);
  - re-hang: attach bone via `attach_parent`; target = `controller_name(bone)` when spine went FK, else `builder.ik_control("spine", SPINE_REHANG[bone])`; missing target → note, chain stays in world.
- [ ] `switch_selected_limbs` in the window: `SWITCHABLE` instead of `LIMB_CHAINS` for the fk-members map and the final filter.
- [ ] Suite green; commit `feat(spine): Switch FK/IK converts the spine, dependents survive on the new controls`.

### Task 3: `fkcontrols.rebuild` — one entry point for Build

**Files:**
- Modify: `maya_overrig/fkcontrols.py`
- Test: `tests/test_fkcontrols.py`

**Interfaces:**
- Produces: `fkcontrols.HYBRID_FK_CHAINS` (every chain not in `LIMB_CHAINS`); `fkcontrols.rebuild(scene_map, fk_limbs=False) -> message str`.

- [ ] Tests first:

```python
class TestHybridFkChains(unittest.TestCase):

    def test_everything_but_the_switchable_limbs(self):
        names = [name for name, _ in fkcontrols.CHAINS]
        expected = tuple(n for n in names
                         if n not in fkcontrols.LIMB_CHAINS)
        self.assertEqual(fkcontrols.HYBRID_FK_CHAINS, expected)

    def test_torso_and_fingers_stay_fk(self):
        self.assertIn("root", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("spine", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("neck", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("index_l", fkcontrols.HYBRID_FK_CHAINS)
        self.assertNotIn("arm_l", fkcontrols.HYBRID_FK_CHAINS)
        self.assertEqual(len(fkcontrols.HYBRID_FK_CHAINS), 13)
```

- [ ] Implement `rebuild`: one undo chunk; teardown FK first (`_bake_fk_chains(scene_map)` when `has_fk()`), then IK (`builder.bake_limbs(scene_map, builder.built_limbs())` when `builder.has_build()`); then `build_fk(scene_map)` when `fk_limbs` else `build_fk(scene_map, only=HYBRID_FK_CHAINS)` + `builder.build(scene_map, only=list(builder.DEFAULT_IK))` + hang each arm's built finger chains on `builder.ik_control(limb, "end")` via `_parent_in`. Returns a combined status message.
- [ ] Suite green; commit `feat(build): one rebuild path — hybrid by default, full FK on demand`.

### Task 4: `bodymap.IK_BUTTONS` + groups

**Files:**
- Modify: `maya_overrig/bodymap.py`
- Test: `tests/test_bodymap.py`

**Interfaces:**
- Produces: `bodymap.IkButton(id, limb, role, x, y, w, h, region)`; `bodymap.IK_BUTTONS` (11: end+pole per limb, top/mid/bot spine column at x=226); `group_members` returns FK + IK ids; `ik_button_by_id(bid)`.

- [ ] Tests first (added to `tests/test_bodymap.py`):

```python
class TestIkButtons(unittest.TestCase):

    def test_eleven_buttons(self):
        self.assertEqual(len(bodymap.IK_BUTTONS), 11)

    def test_ids_unique_and_disjoint_from_fk(self):
        ids = [b.id for b in bodymap.IK_BUTTONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & {b.id for b in bodymap.BUTTONS})

    def test_roles_are_known(self):
        for b in bodymap.IK_BUTTONS:
            self.assertIn(b.role, ("end", "pole", "base"), b.id)

    def test_limbs_cover_the_ik_table(self):
        self.assertEqual(
            {(b.limb, b.role) for b in bodymap.IK_BUTTONS},
            {("arm_l", "end"), ("arm_l", "pole"),
             ("arm_r", "end"), ("arm_r", "pole"),
             ("leg_l", "end"), ("leg_l", "pole"),
             ("leg_r", "end"), ("leg_r", "pole"),
             ("spine", "end"), ("spine", "pole"), ("spine", "base")})

    def test_right_side_mirrors_the_left(self):
        by_id = {b.id: b for b in bodymap.IK_BUTTONS}
        for b in bodymap.IK_BUTTONS:
            if not b.limb.endswith("_l"):
                continue
            twin = by_id[b.id.replace("_l_", "_r_")]
            self.assertEqual(twin.x, bodymap.CANVAS_W - b.x - b.w, b.id)
            self.assertEqual((twin.y, twin.w, twin.h), (b.y, b.w, b.h), b.id)

    def test_stay_on_the_canvas(self):
        for b in bodymap.IK_BUTTONS:
            self.assertTrue(0 <= b.x and b.x + b.w <= bodymap.CANVAS_W, b.id)
            self.assertTrue(0 <= b.y and b.y + b.h <= bodymap.CANVAS_H, b.id)

    def test_never_overlap_fk_buttons(self):
        for ik in bodymap.IK_BUTTONS:
            for fk in bodymap.BUTTONS:
                clear = (ik.x + ik.w <= fk.x or fk.x + fk.w <= ik.x
                         or ik.y + ik.h <= fk.y or fk.y + fk.h <= ik.y)
                self.assertTrue(clear, "{0} vs {1}".format(ik.id, fk.id))

    def test_groups_include_ik_ids(self):
        spine = bodymap.group_members("spine")
        self.assertIn("spine_ik_top", spine)
        self.assertIn("leg_l_ik_end", bodymap.group_members("leg_l"))
        self.assertIn("arm_r_ik_pole", bodymap.group_members("all"))
        self.assertIn("spine_ik_bot", bodymap.group_members("main"))
```

- [ ] Implement: left-side rows `arm_l end (436,112) pole (392,112); leg_l end (314,346) pole (314,294)`, size 18×18, mirrored `_l_`→`_r_`; spine column `top (226,106) end / mid (226,144) pole / bot (226,184) base`, region `spine`. Nudge coordinates until the overlap test passes. `group_members` appends IK ids (`all`, `main`, per-region).
- [ ] Suite green (existing bodymap tests untouched); commit `feat(picker): IK control buttons join the body map`.

### Task 5: `pickerstate.py` — pure resolution

**Files:**
- Create: `maya_overrig/pickerstate.py`
- Test: `tests/test_pickerstate.py`

**Interfaces:**
- Produces: `pickerstate.resolve(fk_nodes, ik_nodes) -> {button_id: path}` (fk_nodes: `{joint: path|None}`, ik_nodes: `{(limb, role): path|None}`); `pickerstate.selected_ids(resolution, selected_paths) -> [ids]`.

- [ ] Tests first:

```python
import unittest

from maya_overrig import bodymap, pickerstate


class TestResolve(unittest.TestCase):

    def test_fk_button_maps_to_its_controller(self):
        found = pickerstate.resolve({"pelvis": "|pelvis_FK_ctrl"}, {})
        self.assertEqual(found["pelvis"], "|pelvis_FK_ctrl")

    def test_missing_controller_leaves_the_button_out(self):
        found = pickerstate.resolve({"pelvis": None}, {})
        self.assertNotIn("pelvis", found)

    def test_ik_button_maps_through_limb_and_role(self):
        found = pickerstate.resolve({}, {("leg_l", "end"): "|foot_l_IK_feet"})
        self.assertEqual(found["leg_l_ik_end"], "|foot_l_IK_feet")

    def test_unknown_joints_are_ignored(self):
        self.assertEqual(pickerstate.resolve({"martian": "|x"}, {}), {})

    def test_empty_scene_resolves_nothing(self):
        self.assertEqual(pickerstate.resolve({}, {}), {})


class TestSelectedIds(unittest.TestCase):

    def test_matches_on_full_paths(self):
        resolution = {"pelvis": "|a|pelvis_FK_ctrl", "head": "|a|head_FK_ctrl"}
        self.assertEqual(
            pickerstate.selected_ids(resolution, {"|a|pelvis_FK_ctrl"}),
            ["pelvis"])

    def test_bare_names_do_not_match(self):
        resolution = {"pelvis": "|a|pelvis_FK_ctrl"}
        self.assertEqual(
            pickerstate.selected_ids(resolution, {"pelvis_FK_ctrl"}), [])
```

- [ ] Implement (stdlib only, imports `bodymap`); `selected_ids` keeps `bodymap` id order (BUTTONS then IK_BUTTONS).
- [ ] Add `pickerstate` to the stdlib-only subprocess guard in `tests/test_bodymap.py` if one lists modules; otherwise mirror the bodymap subprocess test for it.
- [ ] Suite green; commit `feat(picker): pure controller resolution for the picker`.

### Task 6: view draws IK buttons as circles

**Files:**
- Modify: `maya_overrig/picker_view.py`
- Test: `tests/test_picker_view.py`

**Interfaces:**
- Consumes: `bodymap.IK_BUTTONS`.
- Produces: `ButtonItem(button, shape="rect"|"ellipse")`; view builds items for both tables; `items_by_id` covers all 139 ids.

- [ ] Tests first (offscreen, following the existing file's app fixture):

```python
class TestIkItems(unittest.TestCase):

    def test_view_holds_an_item_per_ik_button(self):
        view = picker_view.PickerView()
        for button in bodymap.IK_BUTTONS:
            self.assertIn(button.id, view.items_by_id)

    def test_ik_items_are_ellipses(self):
        view = picker_view.PickerView()
        self.assertEqual(view.items_by_id["spine_ik_top"].shape, "ellipse")
        self.assertEqual(view.items_by_id["pelvis"].shape, "rect")
```

- [ ] Implement: `ButtonItem.__init__(button, shape="rect")`; IK items get `joint=None`-safe tooltip `"{limb} IK {role}"`, region colour from the same table; `paint` draws `drawEllipse(self.rect())` for `"ellipse"`; `PickerView.__init__` also instantiates IK buttons.
- [ ] Suite green; commit `feat(picker): IK buttons render as circles in the view`.

### Task 7: window — controllers only, availability, toolbar

**Files:**
- Modify: `maya_overrig/picker_window.py`

**Interfaces:**
- Consumes: `pickerstate.resolve/selected_ids`, `builder.ik_control`, `fkcontrols.rebuild`, `fkcontrols.controller_name`, `bodymap.IK_BUTTONS`.

- [ ] `_resolution(self)`: fk_nodes from `cmds.ls(controller_name(joint), long=True)` for joints present in `self._scene_map`; ik_nodes from `builder.ik_control(b.limb, b.role)` per IK button; returns `pickerstate.resolve(...)`.
- [ ] `sync_from_scene` recomputes the resolution, calls `view.set_available(list(resolution))` then `view.set_selected(pickerstate.selected_ids(resolution, selected))` — availability now tracks the scene on every sync.
- [ ] `apply_selection` maps ids through the resolution (no more `scene_map` joint paths); unbound → same message.
- [ ] Toolbar: drop `fk_button`; `Build` calls `fkcontrols.rebuild(self._scene_map, self.fk_limbs.isChecked())`; add checkable `FK Limbs` button (`setCheckable(True)`, checked style `background: #5a4a7a`), tooltips describing hybrid vs full FK; Switch tooltip mentions the spine.
- [ ] `_refresh_view` keeps the bound label; initial availability comes from the same `_resolution`.
- [ ] Manual import smoke check only (Qt+Maya module; no unit test): `mayapy -c "import ast; ast.parse(open('maya_overrig/picker_window.py').read())"` plus the full suite.
- [ ] Commit `feat(picker): picker drives controllers only; one Build with an FK Limbs toggle`.

### Task 8: verification scripts, docs, push

**Files:**
- Create: `docs/superpowers/plans/verify_spine_ik.py`, `docs/superpowers/plans/verify_hybrid_build.py`, `docs/superpowers/plans/verify_spine_switch.py`
- Modify: `CLAUDE.md` (What the tool does today; OverRig facts if the 3-joint spine IK teaches one)

**Interfaces:**
- Consumes: the bridge pattern from `docs/superpowers/plans/verify_*.py` (runner writes stdout/stderr to an output file).

- [ ] Write the three bridge scripts per the spec's Testing section (they bind explicitly, never rely on auto-connect, and print PASS/FAIL per assertion).
- [ ] Update CLAUDE.md: single Build + FK Limbs toggle, spine in Switch, controller-only picker, spine IK = rebike-3 on (pelvis, spine_03, spine_05).
- [ ] Full suite green under mayapy; `git push origin feature/overrig-picker`.

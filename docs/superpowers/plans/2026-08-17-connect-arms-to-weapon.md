# Connect arms to weapon — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two buttons in the weapon window that take the weapon out of the
skeleton, put both arms in IK, and hang the IK hand controls on the weapon — and
put it all back.

**Architecture:** Rig knowledge stays in `maya_overrig.fkcontrols` (two new
functions beside `hang_ik_on_root`); `maya_scenesetup.connect` orchestrates the
three steps and owns the "is there a link" question; `window.py` grows two
buttons and two guards.

**Tech Stack:** `maya.cmds` + OverRig MEL through the existing wrappers,
stdlib `unittest` under `mayapy`.

Spec: `docs/superpowers/specs/2026-08-17-connect-arms-to-weapon-design.md`.

## Global Constraints

- **Limb IK state is `limb in builder.built_limbs()`** — the same source
  `switch_limbs` uses. Never "does a node with this name exist".
- **Never re-parent an OverRig knot that already has a parent.** Lift to world
  with `apply_Parent_out`, then hang with `apply_Parent_in`. Selection order for
  `_in` is child first, parent last.
- **Re-read manifests after any re-parenting** — `overrig.set_members` resolves
  long paths at call time (trap 16).
- Every MEL entry point calls `overrig.ensure_loaded()` first and returns
  `overrig.NOT_LOADED_MESSAGE` when the toolset is missing (trap 20).
- One `undoInfo` chunk per button press.
- Tests: fake `maya.cmds` injected into `sys.modules`, module attribute
  rebound. Never delete from `sys.modules`.
- Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`

---

### Task 1: Hang an IK hand on an arbitrary node

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (beside `hang_ik_on_root`)

**Interfaces:**
- Produces: `hang_ik_end_on(limb, target) -> bool`, `lift_ik_end(limb) -> bool`.

- [ ] **Step 1: Write the functions**

```python
def hang_ik_end_on(limb, target):
    """Hang a limb's IK end group on `target`, animation re-baked.

    The end group is where the animator's hand control lives, and the only
    one that rides a prop: the pole keeps answering to the body, and hanging
    the chain base on a prop pins the shoulder to it.

    A knot that already has a parent is lifted to world first. Re-parenting
    one in place is not a path this repo has measured, and the lift-then-hang
    pair is what `switch_limbs` already does with its riders.
    """
    node = builder.ik_control(limb, "end")
    if not node or not cmds.objExists(node):
        return False
    target_path = cmds.ls(target, long=True)[0]
    if builder._is_inside(cmds.ls(node, long=True)[0], target_path):
        return False  # already there; the operation is idempotent
    set_name = builder._ensure_limb_set(limb)
    if cmds.listRelatives(node, parent=True):
        _parent_out(node, set_name)
        node = builder.ik_control(limb, "end")  # the path moved; trap 16
    _parent_in(node, target, set_name)
    return True


def lift_ik_end(limb):
    """Lift a limb's IK end group back to world, animation re-baked."""
    node = builder.ik_control(limb, "end")
    if not node or not cmds.objExists(node):
        return False
    if not cmds.listRelatives(node, parent=True):
        return False
    _parent_out(node, builder._ensure_limb_set(limb))
    return True
```

- [ ] **Step 2: Run the suite — nothing may break**

Run: `mayapy -m unittest discover -s tests -t .`
Expected: 514 tests, OK.

- [ ] **Step 3: Commit** — `feat(overrig): hang an IK hand on any node, not just the root`

---

### Task 2: The connect module

**Files:**
- Create: `maya_scenesetup/connect.py`
- Test: `tests/test_weapons_connect.py`

**Interfaces:**
- Produces: `ARMS`, `limbs_to_switch(state)`, `marked_ancestor(path, marked)`,
  `linked_carrier(limbs)`, `connect(carrier, scene_map)`,
  `disconnect(carrier, bone)`. The two orchestrators return a status string.

- [ ] **Step 1: Write the failing tests**

```python
class LimbsToSwitch(unittest.TestCase):

    def test_nothing_to_do_when_both_arms_are_ik(self):
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": True, "arm_r": True}), [])

    def test_both_when_neither_is(self):
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": False, "arm_r": False}),
            ["arm_l", "arm_r"])

    def test_only_the_fk_arm_in_a_mixed_rig(self):
        """Switching an arm that is already IK converts it to FK -- the exact
        opposite of what the button promises."""
        self.assertEqual(
            connect.limbs_to_switch({"arm_l": True, "arm_r": False}),
            ["arm_r"])


class MarkedAncestor(unittest.TestCase):

    def test_finds_the_carrier_above_the_control(self):
        marked = {"|LongSword_02_weapon"}
        self.assertEqual(
            connect.marked_ancestor(
                "|LongSword_02_weapon|arm_r_IK_feet|ctrl", marked.__contains__),
            "|LongSword_02_weapon")

    def test_is_none_when_nothing_above_is_marked(self):
        self.assertIsNone(
            connect.marked_ancestor("|root_FK_ctrl|arm_r_IK_feet",
                                    set().__contains__))

    def test_takes_the_nearest_one(self):
        marked = {"|a", "|a|b"}
        self.assertEqual(
            connect.marked_ancestor("|a|b|c", marked.__contains__), "|a|b")

    def test_a_shared_prefix_is_not_an_ancestor(self):
        marked = {"|sword"}
        self.assertIsNone(
            connect.marked_ancestor("|swordExtra|ctrl", marked.__contains__))
```

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: Write `maya_scenesetup/connect.py`**

Pure parts as tested above; the orchestrators:

```python
def connect(carrier, scene_map):
    """Weapon out to world, both arms to IK, hands onto the weapon."""
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE

    cmds.undoInfo(openChunk=True, chunkName="Connect arms to weapon")
    try:
        state = {limb: limb in builder.built_limbs() for limb in ARMS}
        switching = limbs_to_switch(state)
        if switching:
            fkcontrols.switch_limbs(scene_map, switching)

        carrier = cmds.ls(carrier, long=True)[0]
        if cmds.listRelatives(carrier, parent=True):
            overrig.parent_out(carrier)
            carrier = cmds.ls(carrier.split("|")[-1], long=True)[0]

        hung = [limb for limb in ARMS
                if fkcontrols.hang_ik_end_on(limb, carrier)]
        return message(switching, hung)
    finally:
        cmds.undoInfo(closeChunk=True)
```

`overrig.parent_out` / `parent_in` are added to `overrig.py` as the thin MEL
binding (no manifest recording — the carrier belongs to no rig):

```python
def parent_out(node):
    """Lift a node to world through OverRig, animation re-baked."""
    ensure_loaded()
    cmds.select(node, replace=True)
    mel.eval("apply_Parent_out()")


def parent_in(child, parent):
    """Hang a node inside another; selection is child first, parent last."""
    ensure_loaded()
    cmds.select([child, parent], replace=True)
    mel.eval("apply_Parent_in()")
```

`disconnect(carrier, bone)` is the mirror: `fkcontrols.lift_ik_end(limb)` then
`fkcontrols.hang_ik_on_root(limb)` for each arm, then
`overrig.parent_in(carrier, bone)`.

- [ ] **Step 4: Run the tests, then the suite**

- [ ] **Step 5: Commit** — `feat(weapons): connect and disconnect the arms`

---

### Task 3: The buttons and the two guards

**Files:**
- Modify: `maya_scenesetup/window.py`, `maya_scenesetup/attach.py`
- Test: `tests/test_weapons_window.py`, `tests/test_weapons_attach.py`

**Interfaces:**
- Produces: `attach.is_animated(node) -> bool`; window constants
  `LINKED_NO_ADD`, `LINKED_NO_OFFSETS`, `NOT_CONNECTED`, `ALREADY_CONNECTED`;
  callbacks `connect_arms()`, `disconnect_arms()`.

- [ ] **Step 1: Write the failing tests**

```python
class IsAnimated(unittest.TestCase):

    def test_true_when_a_channel_carries_a_curve(self):
        fake = FakeCurves({"|c.rotateY": ["curve1"]})
        attach.cmds = fake
        self.assertTrue(attach.is_animated("|c"))

    def test_false_on_a_clean_node(self):
        attach.cmds = FakeCurves({})
        self.assertFalse(attach.is_animated("|c"))
```

plus window message tests in the existing style.

- [ ] **Step 2: Implement**

`add_weapon` refuses when `connect.linked_carrier(connect.ARMS)` is not None;
`offsets_changed` refuses when `attach.is_animated(carrier)`; `refresh` finds
the carrier in the bone **or** through the link and says which.

- [ ] **Step 3: Run the suite**

- [ ] **Step 4: Commit** — `feat(weapons): the Connect/Disconnect buttons`

---

### Task 4: Live proof and notes

**Files:**
- Create: `docs/superpowers/plans/verify_connect_arms.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write the verification script**

Sample both hand bones' world matrices across the timeline before Connect;
Connect; assert both arms are IK, each end control is a DAG descendant of the
carrier, the carrier has no parent, and **the hands did not move**. Then
Connect again (idempotent), then Disconnect and assert the carrier is back in
`weapon_r`, the end controls are back under `root_FK_ctrl`, and the hands
still have not moved.

- [ ] **Step 2: Run it through the command port and fix what it reports**

- [ ] **Step 3: Record it in `CLAUDE.md`** — the feature, the ordering rules,
  and any trap the live run turns up.

- [ ] **Step 4: Commit**

## Self-review

Spec coverage: three ordered steps → Tasks 1-2; end-only rule → Task 1;
link detection → Task 2; Add and offset guards → Task 3; failure messages →
Tasks 2-3; live proof → Task 4. No placeholders. `limbs_to_switch`,
`marked_ancestor`, `linked_carrier`, `hang_ik_end_on`, `lift_ik_end`,
`is_animated` keep the same names and signatures across tasks.

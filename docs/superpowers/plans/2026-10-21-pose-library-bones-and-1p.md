# Pose Library: bones first, 3P = 1P, the upper body stabilized - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a card's torso keeps its own relations (an upper-body card's chest stabilized against the
character's root on any target, 3P or 1P), and our Tools knots / the camera control count as the
rig's body when a card is saved or applied.

**Architecture:** `posemath.Transfer` replaces a torso member's paired ancestor by its nearest
torso MEMBER ancestor, else the root frame; `upper.anchors_for` derives the camera's chest anchor
from any card's members; `scene.stand_in` maps a selected knot to the object it drives and the
camera control names the camera bones; `apply.selected_nodes` adds the knot a selected control is
driven by.

**Tech Stack:** Maya 2027 mayapy, maya.api.OpenMaya, stdlib unittest
(`mayapy -m unittest discover -s tests -t .`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-21-pose-library-bones-and-1p-design.md`.
- Torso = the target bone whose canonical name (else its bare leaf) is `pelvis` or starts `spine_`.
- A full card's results do not change (every existing verify stays green).
- `maya_poselib` imports no `maya_tools` module: the knot markers are spelled and pinned by a test.
- Tests run headless: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest ...`.

---

### Task 1: the torso rule in `posemath.Transfer`

**Files:**
- Modify: `SkeldarAnim/maya_poselib/posemath.py` (`Transfer.__init__`, new `is_torso`, `_torso_anchor`)
- Test: `tests/test_poselib_posemath.py` (new class `Torso`)

**Interfaces:**
- Produces: `posemath.is_torso(bones, leaf) -> bool`; `Transfer.above[leaf]` for torso members.

- [ ] **Step 1: failing tests** - a spine chain fixture (root, pelvis, spine_01..04, head, arm),
  a target whose spine_01/02 twist 30/25 deg about Y:
  - an upper card (spine_03 and above): `rot(out[spine_03]) . rot(out[root])^-1` equals the card's
    to 1e-6 deg, and is NOT the card's against spine_02; `out[spine_02]` the target's own; the
    hand on spine_03 as the card's;
  - a full card unchanged (every bone the card's on a twin);
  - pelvis + spine_03 card: spine_03 against the card's pelvis;
  - spine_02 + spine_04 card: spine_04 against spine_02 as the card's;
  - a rootless target (`rootless()` fixture): spine_03 member alone turns against the ground;
  - a hand card unchanged.
- [ ] **Step 2:** run `mayapy -m unittest tests.test_poselib_posemath -v` - the new tests FAIL.
- [ ] **Step 3: implement**

```python
TORSO = ("pelvis",)
TORSO_PREFIX = "spine_"


def is_torso(bones, leaf):
    name = (bones[leaf].get("canonical") or leaf).split(":")[-1]
    return name in TORSO or name.startswith(TORSO_PREFIX)
```

  in `Transfer.__init__`, after `self.above` is filled and before the anchors:

```python
for leaf in self.order:
    if is_torso(target, leaf) and self._posed(leaf):
        self.above[leaf] = self._torso_anchor(leaf, anchor)
```

  with `_posed(leaf)`: `pairs.get(leaf) in self.members and pairs.get(leaf) in source`, and
  `_torso_anchor` walking the target's parents: the rooted target's root -> the root; a torso bone
  that is posed -> it; past the top -> `anchor` (None for a rootless target: its ground).
- [ ] **Step 4:** the module's tests pass (old and new).

### Task 2: the camera's chest anchor for any upper-body card (`upper`)

**Files:**
- Modify: `SkeldarAnim/maya_poselib/upper.py`, `apply.py` (`_plan`), `animapply.py` (`_Target`, `_press_refs`)
- Test: `tests/test_poselib_upper.py`

**Interfaces:**
- Produces: `upper.is_upper_body(data) -> bool`, `upper.anchors_for(data) -> {leaf: chest}`.

- [ ] **Step 1: failing tests** - `anchors_for` of a card whose members are the chest and above:
  `{"camera_root": "spine_03"}`; of a full card `{}`; of the pelvis + chest card `{}` (a torso
  member below the chest); `restrict`'s cut card answers the anchor.
- [ ] **Step 2:** they fail.
- [ ] **Step 3:** implement; `apply._plan` and `animapply._Target` take
  `upper.target_anchors(upper.anchors_for(data), pairs)`; `restrict` stops writing `anchors`.
- [ ] **Step 4:** tests pass.

### Task 3: our nodes are the rig (`scene`)

**Files:**
- Modify: `SkeldarAnim/maya_poselib/scene.py` (`stand_in`, `resolve`, `_kind`, `_item_bones`, `is_body`)
- Test: `tests/test_poselib_scene.py`

**Interfaces:**
- Produces: `scene.stand_in(path) -> path`, `scene.CAMERA` (a selection kind),
  `scene.CAMERA_BONES`, the spelled knot markers.

- [ ] **Step 1: failing tests** - a fake cmds: a knot top marked `skeldarKnot`="knot" with
  `skeldarKnotSource` -> FKSpine3_M stands for FKSpine3_M; an inner node -> its top -> the object;
  a knot on a knot followed down; a snapshot stands for itself; a waiting pivot -> its object;
  `members_from_selection(("Manny_Rig1:Camera_ctrl", "camera"))` -> `["camera_root",
  "camera_bone"]`; `_kind` of the camera control -> `CAMERA`; the markers equal `knotplan`'s.
- [ ] **Step 2:** they fail.
- [ ] **Step 3:** implement (the batch plug `ls` first: nothing marked costs one call).
- [ ] **Step 4:** tests pass, `test_poselib_scene` whole.

### Task 4: Selected only reaches the knot (`apply.selected_nodes`)

**Files:** Modify `SkeldarAnim/maya_poselib/apply.py`; Test `tests/test_poselib_apply.py`.

- [ ] **Step 1:** failing test - with `scene.dag_object`, `scene.stand_in` and
  `rigsolve.knot_driver` faked, `selected_nodes(["|...|FKSpine3_M"])` holds the knot too, and a
  selected knot holds the control it stands for.
- [ ] **Step 2-4:** implement, pass.

### Task 5: proof

**Files:**
- Create: `docs/superpowers/plans/verify_poselib_1p_transfer.py`
- Modify: `docs/superpowers/plans/verify_poselib_upper_1p.py` (the chest against the root)

- [ ] **Step 1:** the verify (standalone and, unchanged, in a GUI Maya): A (HoleCombo + 1P Setup)
  card off Main, an upper card off Chest_1P_ctrl + shoulders + head + Camera_ctrl, B (L_Lt_2_3P);
  gates: the save classification, the chest stabilized in 3P and 1P (ON and the upper card OFF),
  upper on the chest, lower kept, 3P = 1P, the full card OFF exact, Selected only on FKSpine3_M,
  a pose card, one undo.
- [ ] **Step 2:** run it; run `verify_poselib_apply`, `_solve`, `_anim`, `_upper_1p`,
  `verify_camera_weapon_bones`, `verify_poselib_objects`, `verify_poselib_selected_only`; the unit
  suite whole.
- [ ] **Step 3:** the scenario in the Maya on port 7003 (the repo's code loaded, modules purged).
- [ ] **Step 4:** CLAUDE.md section; commit only our files.

# Clavicle Chains + Weapon Drives Bone — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hybrid Build grows always-FK clavicle controls, and Add inverts the
weapon drive — the sword parents under the hand, `weapon_r`'s animation moves
onto the sword, and `weapon_r` is parent-constrained (mo=False) to it; the UE
bridge unlinks/relinks across a merge.

**Architecture:** Clavicles split out of the arm chains in `fkchains.CHAINS`
(the pelvis/spine precedent) — everything downstream is existing machinery. A
new leaf module `maya_scenesetup/bonedrive.py` (cmds + OpenMaya only) owns
"a bone that follows a marked node": link/unlink/relink, the grip-space
composition, and the range policy. `attach` depends on bonedrive, the bridge
imports it lazily.

**Tech Stack:** Python 2/3-compatible style as the repo uses, `maya.cmds`,
`maya.api.OpenMaya`, stdlib unittest under mayapy.

## Global Constraints

- Specs: `docs/superpowers/specs/2026-08-21-clavicle-chains-design.md`,
  `docs/superpowers/specs/2026-08-21-weapon-drives-bone-design.md`.
- The clavicle control drives ONLY the bone — the IK hang is untouched
  (the user's explicit call; do not couple the IK base to it).
- The weapon→bone constraint is `maintainOffset=False` — the bone lives in
  the sword's frame. No offset capture anywhere.
- Test runner: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <target> -v`
  (no system Python, no pytest). Qt tests need `$env:QT_QPA_PLATFORM = 'offscreen'`.
- Fake-Maya pattern: inject `types.ModuleType` fakes into `sys.modules`
  BEFORE importing the module under test, then rebind the module attribute
  (`module.cmds = fake`). Never delete from sys.modules to force re-import.
- autoKey is guarded off around every scripted write (trap 14).
- Commit messages via `git commit -F <file>` (PowerShell 5.1 quoting).

---

### Task 1: fkchains — the clavicle split

**Files:**
- Modify: `maya_overrig/fkchains.py` (CHAINS at :41, new CLAVICLE_OF near
  SWITCHABLE at :22, `switchable_bones` at :159)
- Test: `tests/test_fkcontrols.py`

**Interfaces:**
- Produces: `CHAINS` with `("clavicle_l", ("clavicle_l",))` and
  `("clavicle_r", ("clavicle_r",))` before `arm_l`; `arm_l/arm_r` chains of
  three bones; `CLAVICLE_OF = {"clavicle_l": "arm_l", "clavicle_r": "arm_r"}`;
  `switchable_bones(scene_map)` also maps clavicle bone paths to their arms.
  All re-exported by `fkcontrols` as today.

- [ ] **Step 1: Update the pinning tests to the new truth**

In `tests/test_fkcontrols.py`:

`test_eighteen_chains` becomes:

```python
    def test_twenty_chains(self):
        self.assertEqual(len(fkcontrols.CHAINS), 20)
```

Add to `TestChains`:

```python
    def test_clavicles_are_their_own_single_knot_chains(self):
        """Always-FK: the control must survive the arm's switches, so it
        cannot share a chain (and a manifest) with the arm."""
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["clavicle_l"], ("clavicle_l",))
        self.assertEqual(table["clavicle_r"], ("clavicle_r",))

    def test_arm_chains_start_at_the_upperarm(self):
        table = dict(fkcontrols.CHAINS)
        self.assertEqual(table["arm_l"],
                         ("upperarm_l", "lowerarm_l", "hand_l"))
        self.assertEqual(table["arm_r"],
                         ("upperarm_r", "lowerarm_r", "hand_r"))

    def test_clavicles_precede_the_arms(self):
        """Parents precede children in CHAINS: a full build must find the
        clavicle controller standing when it couples the arm."""
        names = [name for name, _ in fkcontrols.CHAINS]
        self.assertLess(names.index("clavicle_l"), names.index("arm_l"))
        self.assertLess(names.index("clavicle_r"), names.index("arm_r"))
```

In the HYBRID class, `test_hybrid_is_four_chains` (line ~511) becomes:

```python
    def test_hybrid_is_six_chains(self):
        self.assertEqual(len(fkcontrols.HYBRID_FK_CHAINS), 6)

    def test_hybrid_includes_the_clavicles(self):
        self.assertIn("clavicle_l", fkcontrols.HYBRID_FK_CHAINS)
        self.assertIn("clavicle_r", fkcontrols.HYBRID_FK_CHAINS)
```

Add to the switchable-bones class (there is already a clavicle→arm test at
~:520 — keep it; it now proves the explicit mapping):

```python
    def test_clavicle_controllers_do_not_switch(self):
        """The clavicle chain itself is not switchable - it is always FK."""
        self.assertNotIn("clavicle_l", fkcontrols.SWITCHABLE)
        self.assertNotIn("clavicle_r", fkcontrols.SWITCHABLE)
```

Fix the tests the split invalidates:
- `test_missing_clavicle_moves_the_arm_root_to_the_upperarm` (~:141): the
  arm chain root IS the upperarm now; repoint the test at the clavicle
  chain — a rig without clavicles has `chain_root(("clavicle_l",)) is None`.
- Nesting-path expectations at ~:295-297 describe the arm root controller as
  `clavicle_l_FK_ctrl`; the arm root controller is `upperarm_l_FK_ctrl`
  (inside the clavicle's) — update paths and any counts they pin.
- `attach_parent` class (~:587): keep `"clavicle_l": "spine_05"`; add
  `upperarm_l → clavicle_l` if not already covered.

- [ ] **Step 2: Run, verify the new tests fail**

`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_fkcontrols -v`
Expected: the new/updated tests FAIL (CHAINS still 18, arm still 4 bones).

- [ ] **Step 3: Implement in fkchains.py**

CHAINS (replace the arm entries, insert clavicles before them):

```python
    ("neck", ("neck_01", "neck_02", "head")),
    # The clavicles are deliberately their own single-knot chains (the
    # pelvis/spine precedent, 2026-08-21): always FK, so the control
    # survives the arm's switches in both directions. Before the arms,
    # because parents precede children -- coupling must find its target.
    # The control drives ONLY the bone: the IK arm keeps riding the root
    # controller (the user's explicit call; see the spec before "fixing").
    ("clavicle_l", ("clavicle_l",)),
    ("clavicle_r", ("clavicle_r",)),
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
```

Near SWITCHABLE:

```python
# Clicking a clavicle still switches its arm: the bone is no longer part of
# the switchable chain, but the animator's habit is older than the split.
CLAVICLE_OF = {"clavicle_l": "arm_l", "clavicle_r": "arm_r"}
```

At the end of `switchable_bones`, before `return out`:

```python
    for joint, limb in CLAVICLE_OF.items():
        path = scene_map.get(joint)
        if path:
            out[path] = limb
```

- [ ] **Step 4: Run the whole suite, fix remaining fallout**

`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
(with `$env:QT_QPA_PLATFORM = 'offscreen'`). Any other test still describing
the four-bone arm gets updated to the new truth — expectations only, never
the machinery.

- [ ] **Step 5: Commit**

`feat(fkchains): clavicles split into their own always-FK chains`

### Task 2: verify scripts for the clavicle build

**Files:**
- Modify: `docs/superpowers/plans/verify_hybrid_build.py`
- Modify: `docs/superpowers/plans/verify_control_axes.py` (only if its pair
  list or counts include the clavicles)

**Interfaces:**
- Consumes: Task 1's tables.

- [ ] **Step 1: verify_hybrid_build.py** — controller-count gates go 10→12
  and the FK-chain list gains the clavicles; add two gates:
  clavicle_l_FK_ctrl exists and is a DAG descendant of the spine-tip
  controller; rotating it 15° moves the clavicle BONE's world matrix and
  leaves `upperarm_l`'s unmoved (the user's chosen behaviour), both restored
  via the script's `pushed` pattern.
- [ ] **Step 2: verify_control_axes.py** — the mirror gates iterate built
  pairs; clavicle knots are now plain transforms skipped by align (like the
  pelvis), so exclude `clavicle_*` from the pair list the way root/pelvis
  are excluded, with a comment saying why.
- [ ] **Step 3: Commit** — `test(verify): hybrid build gates cover the clavicles`

### Task 3: bonedrive — the pure math

**Files:**
- Create: `maya_scenesetup/bonedrive.py`
- Test: `tests/test_scenesetup_bonedrive.py`

**Interfaces:**
- Produces: `MARKER = "mayaWeapon"`;
  `union_range(start, end, times) -> (start, end)`;
  `matrix_of(rotate, translate) -> tuple16` (XYZ degrees, no scale);
  `composed_grip(rotate, translate, bone_local16) -> (rotate3, translate3)`.
- Consumes: nothing (leaf module).

- [ ] **Step 1: Write the failing tests** (om imports directly, as
  `tests/test_axes.py` does):

```python
import math
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive


def _matrix(rx, ry, rz, tx, ty, tz):
    m = om.MTransformationMatrix()
    m.setRotation(om.MEulerRotation(math.radians(rx), math.radians(ry),
                                    math.radians(rz)))
    m.setTranslation(om.MVector(tx, ty, tz), om.MSpace.kTransform)
    return tuple(m.asMatrix())


class UnionRange(unittest.TestCase):

    def test_keys_widen_the_playback_range(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, [-20.0, 10.0, 45.0]),
                         (-20.0, 45.0))

    def test_no_keys_keep_the_playback_range(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, []), (0.0, 30.0))

    def test_keys_inside_change_nothing(self):
        self.assertEqual(bonedrive.union_range(0.0, 30.0, [5.0, 12.0]),
                         (0.0, 30.0))


class ComposedGrip(unittest.TestCase):
    """Old-scheme grip (channels under weapon_r) -> channels under the hand.

    The sword's world matrix must be identical in both schemes:
    grip_under_hand · L_bone == grip (as it stood under weapon_r composed on
    the bone's local matrix).
    """

    def test_identity_bone_local_returns_the_grip(self):
        rotate, translate = bonedrive.composed_grip(
            (10.0, 20.0, 30.0), (1.0, 2.0, 3.0), _matrix(0, 0, 0, 0, 0, 0))
        for got, want in zip(rotate + translate,
                             (10.0, 20.0, 30.0, 1.0, 2.0, 3.0)):
            self.assertAlmostEqual(got, want, places=9)

    def test_zero_grip_returns_the_bone_local(self):
        rotate, translate = bonedrive.composed_grip(
            (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _matrix(90.0, 0, 0, 5.0, 0, 0))
        self.assertAlmostEqual(rotate[0], 90.0, places=9)
        self.assertAlmostEqual(translate[0], 5.0, places=9)

    def test_composition_matches_the_matrix_product(self):
        grip = ((10.0, -35.0, 4.0), (0.5, -2.0, 12.0))
        bone_local = _matrix(25.0, 80.0, -5.0, 3.0, 4.0, -1.0)
        rotate, translate = bonedrive.composed_grip(grip[0], grip[1],
                                                    bone_local)
        want = om.MMatrix(bonedrive.matrix_of(*grip)) * om.MMatrix(bone_local)
        got = om.MMatrix(bonedrive.matrix_of(rotate, translate))
        worst = max(abs(got[i] - want[i]) for i in range(16))
        self.assertLess(worst, 1e-9)
```

- [ ] **Step 2: Run, expect ImportError/AttributeError**

`mayapy -m unittest tests.test_scenesetup_bonedrive -v`

- [ ] **Step 3: Implement the pure half of bonedrive.py**

```python
"""A bone that follows a marked node.

The Camera Setup pattern generalised: the animator's thing (the weapon)
carries the animation and the export bone is parent-constrained to it,
`maintainOffset=False` -- the bone lives in the node's frame, so wherever the
sword is, the bone is, and the export is honest. `attach` builds the link at
Add, the picker never sees it, and the UE bridge unlinks/relinks around a
merge (the constraint would otherwise trip the trap-37 refusal).

A leaf module on purpose: maya.cmds and OpenMaya only, so `attach` can depend
on it and the bridge can import it lazily without dragging a window in.
"""

import math
from contextlib import contextmanager

import maya.api.OpenMaya as om
import maya.cmds as cmds

# The weapon marker. Defined here (the leaf) and re-exported by `attach`, so
# every existing `attach.MARKER` reader keeps working.
MARKER = "mayaWeapon"

CHANNELS = tuple(channel + axis
                 for channel in ("translate", "rotate") for axis in "XYZ")


def union_range(start, end, times):
    """The playback range widened to cover `times`. Pure.

    Trap 38 from the export side: a bake narrower than the keys silently
    truncates them, so every bake here covers both ranges.
    """
    if times:
        start = min(start, min(times))
        end = max(end, max(times))
    return start, end


def matrix_of(rotate, translate):
    """Grip channels (XYZ degrees, no scale) as a local matrix, 16 floats."""
    matrix = om.MTransformationMatrix()
    matrix.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    matrix.setTranslation(om.MVector(*translate), om.MSpace.kTransform)
    return tuple(matrix.asMatrix())


def composed_grip(rotate, translate, bone_local):
    """An old-scheme grip (channels under weapon_r) as under-hand channels.

    The sword's world position is identical in both schemes by construction:
    the old channels rode `weapon_r`, so composing them onto the bone's local
    matrix relative to the hand is the same world placement, expressed where
    the channels now live.
    """
    product = om.MMatrix(matrix_of(rotate, translate)) * om.MMatrix(bone_local)
    frame = om.MTransformationMatrix(product)
    euler = frame.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    shift = frame.translation(om.MSpace.kTransform)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (shift.x, shift.y, shift.z))
```

- [ ] **Step 4: Run to green, commit**

`feat(bonedrive): the pure half - range union and grip-space composition`

### Task 4: bonedrive — the scene half

**Files:**
- Modify: `maya_scenesetup/bonedrive.py`
- Test: `tests/test_scenesetup_bonedrive.py`

**Interfaces:**
- Produces: `bake_range(node)`, `local_matrix(node, parent) -> tuple16`,
  `driving_weapon(bone) -> long path | None`, `find_links(joints) ->
  [(bone, weapon)]`, `moves(node) -> bool`, `snap(node, target)`,
  `link(weapon, bone) -> frames_baked`, `unlink(bone) -> weapon | None`,
  `relink(weapon, bone) -> frames_baked`.
- Consumes: Task 3's pure half.

- [ ] **Step 1: Write the failing tests.** A FakeCmds in the test module
  records call order; the assertions that matter are ORDER assertions —
  the camera paid for these:

```python
class FakeCmds(object):
    """Records the calls whose ORDER is the design."""

    def __init__(self, bone_keys=(), bone_curves=False, weapon="|hand|sword",
                 marked=("|hand|sword",)):
        self.log = []
        self.autokey = True
        self._bone_keys = list(bone_keys)
        self._bone_curves = bone_curves
        self._weapon = weapon
        self._marked = set(marked)
        self._constraints = {}   # bone -> constraint node

    def playbackOptions(self, query=False, minTime=False, maxTime=False):
        return 0.0 if minTime else 30.0

    def keyframe(self, node, query=False, timeChange=False,
                 valueChange=False, **kwargs):
        if valueChange:
            return list(self._bone_keys)
        return [0.0, 30.0] if self._bone_keys else []

    def listRelatives(self, node, children=False, type=None, fullPath=False,
                      **kwargs):
        if type == "parentConstraint" and node in self._constraints:
            return [self._constraints[node]]
        return None

    def parentConstraint(self, *nodes, **kwargs):
        if kwargs.get("query"):
            return [self._weapon]
        self.log.append(("constrain", nodes,
                         kwargs.get("maintainOffset", True)))
        name = nodes[-1] + "_parentConstraint1"
        self._constraints[nodes[-1]] = name
        return [name]

    def ls(self, *args, **kwargs):
        return [args[0]] if args and args[0] else []

    def attributeQuery(self, name, node=None, exists=False, **kwargs):
        return node in self._marked

    def listConnections(self, plug, **kwargs):
        return ["curve"] if self._bone_curves else None

    def bakeResults(self, node, **kwargs):
        self.log.append(("bake", node, kwargs.get("time")))

    def cutKey(self, node, **kwargs):
        self.log.append(("cut", node, kwargs.get("attribute")))

    def delete(self, node):
        self.log.append(("delete", node))

    def xform(self, node, **kwargs):
        if kwargs.get("query"):
            return (0.0, 0.0, 0.0)
        self.log.append(("xform", node))

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.autokey
        self.autokey = state

    def objExists(self, node):
        return True
```

Tests: `link` on a moving bone logs `constrain(bone→weapon, mo=False)`,
`bake(weapon)`, `delete(temp)`, `cut(bone…)`, `constrain(weapon→bone,
mo=False)` in that order; `link` on a still bone logs no bake and returns 0;
`unlink` bakes the BONE before `delete(constraint)` and returns the weapon;
`unlink` with no constraint returns None and logs nothing; `relink` cuts the
WEAPON's curves and snaps before linking; `find_links` pairs only marked
drivers; autoKey is False during every logged write and restored after.

- [ ] **Step 2: Run, expect failures**
- [ ] **Step 3: Implement the scene half** (key bodies):

```python
@contextmanager
def _autokey_off():
    """Trap 14: the user works with autoKey ON; scripted pokes must not key."""
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        yield
    finally:
        cmds.autoKeyframe(state=state)


def bake_range(node):
    """The playback range widened to `node`'s own keys."""
    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)
    return union_range(start, end,
                       cmds.keyframe(node, query=True, timeChange=True) or [])


def local_matrix(node, parent):
    """`node`'s matrix relative to `parent`, from world matrices.

    World matrices rather than the local channels: a joint's local matrix
    hides jointOrient and rotateAxis, and this module must not care.
    """
    child = om.MMatrix(cmds.xform(node, query=True, matrix=True,
                                  worldSpace=True))
    above = om.MMatrix(cmds.xform(parent, query=True, matrix=True,
                                  worldSpace=True))
    return tuple(child * above.inverse())


def _constraints_on(bone):
    return cmds.listRelatives(bone, children=True, type="parentConstraint",
                              fullPath=True) or []


def driving_weapon(bone):
    """The marked node whose parentConstraint drives `bone`, or None."""
    for constraint in _constraints_on(bone):
        for target in cmds.parentConstraint(constraint, query=True,
                                            targetList=True) or []:
            paths = cmds.ls(target, long=True) or []
            if paths and cmds.attributeQuery(MARKER, node=paths[0],
                                             exists=True):
                return paths[0]
    return None


def find_links(joints):
    """[(bone, weapon)] for the joints our marked nodes drive. Read-only."""
    found = []
    for joint in joints:
        weapon = driving_weapon(joint)
        if weapon:
            found.append((joint, weapon))
    return found


def moves(node):
    """Whether any transform channel carries keys that actually change.

    "Has animCurves" is not "has animation" (trap 30): builds leave constant
    baked curves behind, and transferring a constant is worse than nothing --
    the weapon's channels end up keyed and the grip fields go quiet.
    """
    for channel in CHANNELS:
        values = cmds.keyframe("{0}.{1}".format(node, channel), query=True,
                               valueChange=True) or []
        if values and (max(values) - min(values)) > 1e-9:
            return True
    return False


def _cut(node):
    """Drop any animCurves on the transform channels.

    Before constraining, always: a constraint over a still-connected channel
    splices a pairBlend in (the camera's trap), and a pairBlend is a rig
    nobody recorded.
    """
    for channel in CHANNELS:
        plug = "{0}.{1}".format(node, channel)
        if cmds.listConnections(plug, source=True, destination=False,
                                type="animCurve"):
            cmds.cutKey(node, attribute=channel, clear=True)


def _bake(node, start, end):
    cmds.bakeResults(node, time=(start, end), attribute=list(CHANNELS),
                     simulation=False, sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False)


def snap(node, target):
    """Put `node`'s world translate/rotate on `target`'s. Scale untouched --
    the weapon's scale is the catalog's business, not the bone's."""
    cmds.xform(node, worldSpace=True, translation=cmds.xform(
        target, query=True, worldSpace=True, translation=True))
    cmds.xform(node, worldSpace=True, rotation=cmds.xform(
        target, query=True, worldSpace=True, rotation=True))


def link(weapon, bone):
    """Move the bone's animation onto the weapon, then drive the bone from it.

    Returns the number of frames baked across (0: the bone had nothing that
    moves, so the weapon's channels stay clean and the grip fields stay live).
    The caller has already put the weapon where the bone is, so mo=False jumps
    nothing -- and mo=False is the design in one flag: the bone lives in the
    weapon's frame, wherever the animator takes it.
    """
    start, end = bake_range(bone)
    frames = 0
    with _autokey_off():
        if moves(bone):
            temporary = cmds.parentConstraint(bone, weapon,
                                              maintainOffset=False)[0]
            _bake(weapon, start, end)
            cmds.delete(temporary)
            frames = int(round(end - start)) + 1
        _cut(bone)
        cmds.parentConstraint(weapon, bone, maintainOffset=False)
    return frames


def unlink(bone):
    """Bake the bone back from the weapon driving it, drop the constraint.

    Returns the weapon it was riding, or None when nothing of ours drives the
    bone. Bake first, delete second -- the animation lives on the weapon, and
    the camera already paid for the other order.
    """
    weapon = driving_weapon(bone)
    if not weapon:
        return None
    start, end = bake_range(weapon)
    with _autokey_off():
        _bake(bone, start, end)
        cmds.delete(_constraints_on(bone))
    return weapon


def relink(weapon, bone):
    """After a merge rewrote the bone: the fresh animation back onto the weapon.

    The weapon's own curves are stale by definition here -- the merge's
    contract is "the scene plays this clip" -- so they are cut, the weapon is
    snapped onto the bone (a clip with no weapon_r keys leaves the bone at its
    cleared pose, and the weapon must stand there too), and the link rebuilt.
    """
    with _autokey_off():
        _cut(weapon)
        snap(weapon, bone)
        return link(weapon, bone)
```

- [ ] **Step 4: Run to green** (rebind `bonedrive.cmds = fake` per test)
- [ ] **Step 5: Commit** — `feat(bonedrive): link, unlink, relink - the bone lives in the weapon's frame`

### Task 5: attach — two bones, snap+link, detach

**Files:**
- Modify: `maya_scenesetup/attach.py`
- Test: `tests/test_scenesetup_attach.py`

**Interfaces:**
- Consumes: `bonedrive.snap/link/unlink/MARKER`.
- Produces: `attach.MARKER` (re-export), `parent_bone(bone) -> path | None`,
  `attach(entry, parent_bone, drive_bone, rotate, translate) -> (path, note)`,
  `detach(parent_bone, drive_bone) -> removed | None`. `remove_attached` is
  gone (it deleted without giving the bone its animation back).

- [ ] **Step 1: Update/extend the tests.** `test_scenesetup_attach.py`'s fake
  gains `parentConstraint/bakeResults/cutKey/xform/playbackOptions/keyframe/
  objExists/undoInfo/addAttr` no-ops where needed, or — simpler — the new
  tests rebind BOTH `attach.cmds` and `attach.bonedrive` (a
  `types.SimpleNamespace` fake with `snap/link/unlink` recording calls).
  Tests: `detach` calls `bonedrive.unlink(drive_bone)` BEFORE
  `cmds.delete(weapon)`; `detach` looks under the parent bone first and the
  drive bone second (legacy home); `detach` with nothing attached returns
  None and unlinks nothing; `attach.MARKER == bonedrive.MARKER`;
  `parent_bone` returns the DAG parent or None. The import-flow test (order:
  parent → marker → seat → snap → link → offsets-only-when-frames-0) goes in
  as a call-log test with the fakes.

- [ ] **Step 2: Run, expect failures**

- [ ] **Step 3: Implement.** In `attach.py`:

```python
from maya_scenesetup import bonedrive

# The marker moved into bonedrive (the leaf) so the bridge can read it
# without importing this module; every existing reader of attach.MARKER
# keeps working through this re-export.
MARKER = bonedrive.MARKER
```

New helpers and the reworked entry points:

```python
def parent_bone(bone):
    """The bone the weapon parents under: the drive bone's own DAG parent.

    On Manny that is hand_r -- and resolving it as "weapon_r's parent" rather
    than by name keeps a UE4-schema rig, a prefix or a weapon_l entry working
    with no new table.
    """
    parents = cmds.listRelatives(bone, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def detach(parent_bone_path, drive_bone):
    """Remove our weapon and give the bone its animation back.

    Unlink FIRST: the bone's motion lives on the weapon while the link
    stands, and deleting the weapon first would take it away (the camera's
    second press, same order). The legacy home -- a sword parented under
    weapon_r by the old version -- is searched second.
    """
    weapon = find_attached(parent_bone_path) or find_attached(drive_bone)
    if not weapon:
        return None
    bonedrive.unlink(drive_bone)
    cmds.delete(weapon)
    return weapon
```

`attach(entry, parent_bone_path, drive_bone, rotate=(0,0,0), translate=(0,0,0))`
keeps its body shape but: `detach(parent_bone_path, drive_bone)` replaces
`remove_attached(bone)`; the mesh/group parents into `parent_bone_path`;
after `seat(weapon, entry.scale)`:

```python
        # Onto the drive bone exactly, then invert the drive. The weapon
        # standing on the bone is what makes mo=False jump nothing.
        bonedrive.snap(weapon, drive_bone)
        frames = bonedrive.link(weapon, drive_bone)
        if frames:
            note = (note + " - " if note else "") + \
                "{0} frame(s) moved from the bone onto the weapon".format(
                    frames)
        else:
            # A clean bone: the remembered grip applies, and the bone
            # follows it -- the constraint is already standing.
            write_offsets(weapon, rotate, translate)
        return weapon, note
```

The whole body runs under autoKey-off (wrap with the same query/set/finally
pattern `write_offsets` uses) — `bonedrive` guards its own calls, this guards
`seat` and the snap.

Delete `remove_attached` and update its two unit tests to `detach`.

- [ ] **Step 4: Run to green**
- [ ] **Step 5: Commit** — `feat(attach): the weapon parents under the hand and drives its bone`

### Task 6: window — bones, Remove button, grip migration

**Files:**
- Modify: `maya_scenesetup/window.py`
- Test: `tests/test_scenesetup_window.py`

**Interfaces:**
- Consumes: `attach.parent_bone/attach/detach`, `bonedrive.local_matrix/
  composed_grip`, `linking.disconnect(weapon, hand_bone)`.
- Produces: `_GRIP_OPTIONVAR = "mayaSceneSetup_grip_{0}"`;
  `grip_optionvar_name(key)`; `_attached(entry)` returns
  `(root, hand, bone, weapon, linked)`; `remove_weapon()` callback;
  message constants `NO_PARENT_BONE`, `LINKED_NO_REMOVE`.

- [ ] **Step 1: Tests first** (pure parts): `grip_optionvar_name` formats;
  `_remembered`-policy extracted pure as

```python
def grip_values(new_era, old_era, bone_local, compose):
    """Which grip the fields show: new-era raw, old-era composed, else zeros.

    Old-space numbers are never displayed as if they were new-space: with no
    bone to compose against the fields show zeros instead.
    """
    if new_era is not None:
        return unpack_offsets(new_era)
    if old_era is not None and bone_local is not None:
        rotate, translate = unpack_offsets(old_era)
        return compose(rotate, translate, bone_local)
    return unpack_offsets(None)
```

with tests for all three branches (compose passed as a lambda recording its
arguments). Message tests: `missing_parent_message("weapon_r")` mentions the
bone, `removed_message(entry)` mentions the label.

- [ ] **Step 2: Run, expect failures**
- [ ] **Step 3: Implement in window.py:**

- `_GRIP_OPTIONVAR = "mayaSceneSetup_grip_{0}"`, `grip_optionvar_name(key)`.
- `_remember` writes the new name only; `_remembered(entry, bone_local)`
  reads new name → `grip_values(...)` with the two legacy names as old_era
  and `bonedrive.composed_grip` as compose.
- `_attached(entry)` resolves `bone = skeleton.resolve_bone(root, entry.bone)`
  then `hand = attach.parent_bone(bone)`; searches
  `attach.find_attached(hand)` then `attach.find_attached(bone)` (legacy);
  returns the 5-tuple; `_locate` refuses with `NO_PARENT_BONE` ("weapon_r
  has no parent bone - nothing to hang the weapon on") when hand is None.
- `add_weapon`: unchanged guards; calls
  `attach.attach(entry, hand, bone, rotate, translate)`.
- `remove_weapon` (new callback + button between Add and the offsets):

```python
def remove_weapon():
    """Take the weapon off: the bone gets its animation back, the sword goes."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, hand, bone, weapon, linked = located
    if linked:
        _status(LINKED_NO_REMOVE)
        return
    if not weapon:
        _status(NOT_ATTACHED)
        return
    if aimrig.aim_for(attach.model_root(weapon)):
        _status(AIMED_NO_ADD)
        return
    removed = attach.detach(hand, bone)
    _status(removed_message(entry) if removed else NOT_ATTACHED)
```

- `disconnect_arms` passes the HAND: `linking.disconnect(weapon, hand)`.
- `refresh` computes `bone_local = bonedrive.local_matrix(bone, hand)` when
  both resolve and nothing is attached, and feeds `_remembered`.
- `add_weapon`'s aim guard keeps using `attach.model_root`.

- [ ] **Step 4: Run to green (offscreen), full suite**
- [ ] **Step 5: Commit** — `feat(window): remove button, hand-bone routing, grip migration`

### Task 7: the bridge unlinks and relinks

**Files:**
- Modify: `maya_uebridge/animimport.py` (merge block at :319-334, results
  at :387)
- Test: `tests/test_uebridge_import.py`

**Interfaces:**
- Consumes: `bonedrive.find_links/unlink/relink` (lazy import).
- Produces: `foreign_constrained(constrained, linked_bones)` (pure),
  `relink_note(bones)` (pure), result dict key `"relinked": [short names]`.

- [ ] **Step 1: Tests first** (pure): `foreign_constrained` filters ours
  out and keeps strangers; empty lists both ways; `relink_note([])` is ""
  and `relink_note(["weapon_r"])` names the bone. Plus one behavioural test
  with fakes if the module's existing tests fake cmds — follow the file's
  own pattern.

- [ ] **Step 2: Run, expect failures**
- [ ] **Step 3: Implement:**

```python
def foreign_constrained(constrained, linked_bones):
    """The constrained joints that are NOT ours to unlink. Pure."""
    ours = set(linked_bones)
    return [joint for joint in constrained if joint not in ours]


def relink_note(bones):
    """Status text for the weapon links rebuilt after the merge."""
    if not bones:
        return ""
    return "weapon re-linked on " + ", ".join(bones)


def _weapon_links(joints):
    """[(bone, weapon)] our weapon tool drives; [] when scenesetup is absent.

    Lazy and guarded on purpose: the bridge must work in a Maya that never
    installed the weapon tool, and a bare import here would be a hard
    dependency for every user of the window.
    """
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return []
    return bonedrive.find_links(joints)
```

In `import_clip`'s merge block, replacing the refusal pair:

```python
        target_joints = joints_under(target)
        links = _weapon_links(target_joints)
        rigged = foreign_constrained(constrained_joints(target_joints),
                                     [bone for bone, _ in links])
        if rigged:
            # Nothing has been touched yet -- the weapon links are read, not
            # released, so a refusal leaves the scene exactly as it was.
            raise RuntimeError(rigged_target_message(
                [_short(j) for j in rigged]))
        if links:
            from maya_scenesetup import bonedrive
            for bone, _weapon in links:
                bonedrive.unlink(bone)
```

After the timeline is set (so `bake_range` unions against the clip's range),
before the warnings are built:

```python
    relinked = []
    if merge and links:
        from maya_scenesetup import bonedrive
        for bone, weapon in links:
            if cmds.objExists(weapon) and cmds.objExists(bone):
                bonedrive.relink(weapon, bone)
                relinked.append(_short(bone))
```

`warnings.append(relink_note(relinked))` in the merge branch, and
`"relinked": relinked` in the result dict (initialise `links = []` beside
`target = None` so the non-merge path reads clean).

- [ ] **Step 4: Run to green, full suite**
- [ ] **Step 5: Commit** — `feat(uebridge): unlink and relink the weapon bone across a merge`

### Task 8: verify scripts for the weapon flow

**Files:**
- Modify: `docs/superpowers/plans/verify_weapons.py`
- Modify: `docs/superpowers/plans/verify_connect_arms.py`
- Modify: `docs/superpowers/plans/verify_weapon_aim.py`

- [ ] **Step 1: verify_weapons.py** — every `attach.attach(entry, bone, ...)`
  becomes `attach.attach(entry, hand, bone, ...)` with
  `hand = attach.parent_bone(bone)`; the seat gate measures the weapon
  against the DRIVE bone (world matrices — it stands ON weapon_r, under the
  hand); new gates: the marked node's DAG parent is the hand; `weapon_r`
  carries a parentConstraint whose driver is the marked node; move the sword
  10 units (pushed), the bone's world matrix follows to <1e-6; key two
  poses on `weapon_r` first in a sandboxed pre-step, Add, and the sword's
  channels now carry the motion while the bone's world matrices match the
  original at both frames; `attach.detach` puts the animation back on the
  bone (world matrices match, constraint gone) — replaces the old
  `remove_attached` cleanup.
- [ ] **Step 2: verify_connect_arms.py** — resolve `hand` beside `bone`,
  pass it to `linking.disconnect(weapon, hand)`; the round-trip gate's
  "back in the bone" check asks for the marked node under the HAND; add one
  gate: after Connect, dragging the sword still moves `weapon_r` (the
  constraint survived `parent_out`).
- [ ] **Step 3: verify_weapon_aim.py** — the attach call gains the hand
  argument; no gate changes (the aim sits on the geometry either way).
- [ ] **Step 4: Commit** — `test(verify): weapon gates for the inverted drive`

### Task 9: documentation

**Files:**
- Modify: `CLAUDE.md` (the picker "what the tool does" section for the
  clavicles; the `maya_scenesetup` section for the weapon; the uebridge
  section for the relink)

- [ ] **Step 1:** CLAUDE.md — clavicle paragraph (split, always-FK, the
  user's "only the bone" call, Switch/Bake semantics, old files degrade);
  weapon paragraphs (hand parent, mo=False, detach order, grip optionVar
  migration, Remove button, bridge relink, legacy home fallback); update the
  bullet under "what the tool does today" that says hybrid = ten controllers.
- [ ] **Step 2:** Full suite one more time; commit —
  `docs: clavicle chains and the weapon-driven bone in the working notes`

### Task 10: live verification attempt

- [ ] **Step 1:** `Get-NetTCPConnection -State Listen -LocalPort 7001` — the
  port died to trap 8 on 2026-08-20 and only a Maya restart revives it.
- [ ] **Step 2:** If listening: send a two-line print probe first (bridge
  note 7's tell), then run `verify_hybrid_build.py` and `verify_weapons.py`
  through the runner pattern (marker file guarded with `if`, never
  SystemExit — bridge note 8). If not listening or the probe is silent:
  report the scripts as ready-to-run and stop — the user restarts Maya.

## Self-review notes

- Spec coverage: clavicle spec → Tasks 1-2; weapon spec → Tasks 3-8; both
  docs → Task 9; live proof → Tasks 2/8/10.
- `linking.connect` needs no change (checked: it re-resolves the weapon by
  UUID around `parent_out`; the constraint targets the node).
- `bake_targets` needs no change: clavicle bones resolve to the clavicle
  chain through CHAINS, controllers through the chain manifest.
- Type consistency: `attach.attach(entry, parent_bone_path, drive_bone,
  rotate, translate)` everywhere; `detach(parent_bone_path, drive_bone)`;
  bonedrive returns paths long. `_attached` 5-tuple `(root, hand, bone,
  weapon, linked)` — every window callback unpacks five.

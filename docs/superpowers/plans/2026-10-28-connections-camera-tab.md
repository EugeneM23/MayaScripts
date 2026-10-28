# Connections Camera Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Camera tab in the hub's Connections card: the camera control's parent switched among Main / Root / Chest / Head / World (optionally position only, like a point constraint), and the weapon's Aim Mode / Default applied to the camera.

**Architecture:** The weapon aim's engine moves out of `weaponaim.py` into `aimcore.py`, parametrised by an `AimKind` (markers, names, undo chunk names); `weaponaim` keeps its whole public API as thin wrappers, and a new `cameraaim.py` drives `Camera_ctrl` through the same engine. `camera.set_parent` grows Head and a Position only mode (a `Camera_follow` group under Main, point-constrained to the chosen node). `camera.move_control` leaves and re-enters Aim Mode around every move, so 1P Setup, the chest bake and the tab all keep the aim.

**Tech Stack:** Maya 2027 Python (`maya.cmds`, `maya.api.OpenMaya`), the hub's `maya_hubstyle` UI, `unittest` under `mayapy`, mayapy-standalone verify scripts.

Spec: `docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md`.

## Global Constraints

- Repo `C:\!!!Work\MayaScripts`, branch `main`. The working tree carries the animator's unrelated uncommitted edits (`maya_scenetabs/*`, `maya_timebar/bar.py`, a few tests and plans): **never stage them**; commit with explicit paths only (`git commit -F <msgfile> -- <paths>`).
- Commit messages: `feat(connections): ...` / `refactor(aim): ...` / `test(...)`, written to a file and committed with `-F` (no here-strings with quotes in PowerShell), ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- No system Python. Unit tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root with `$env:QT_QPA_PLATFORM = 'offscreen'`; never `python`. Avoid `2>&1` on mayapy in PowerShell.
- Parents list, exactly: `PARENTS = ("Main", "Root", "Chest", "Head", "World")`. Head = the rig's `FKHead_M`.
- Position only: rotation relative to the rig's Main. Main and World ignore the option (said in the line).
- Camera aim distances: target `AIM_DISTANCE = 300.0` cm along the view, up `UP_DISTANCE = 50.0` cm along the camera's up.
- Default's fill tolerance stays `TOLERANCE = 0.1` degrees, `FILL_PASSES = 4`.
- Every press: one undo chunk, autoKey off, the time warp off, the current frame put back.
- Code style: match the module around it (its docstring voice, `# noqa: BLE001` on broad excepts, long paths, UUID re-finding after any reparent).

---

### Task 1: Lift the aim engine into `aimcore.py`

Pure refactor: every existing test and `verify_weapon_aim_mode.py` must stay green with no behaviour change.

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/aimcore.py`
- Modify: `SkeldarAnim/maya_scenesetup/weaponaim.py` (whole module body below the constants)
- Test: `tests/test_scenesetup_aimcore.py` (new), `tests/test_scenesetup_weaponaim.py` (unchanged, must pass)

**Interfaces:**
- Produces (used by Tasks 2-6):
  - `aimcore.AimKind(marker, ctrl_marker, con_marker, vectors_attr, group_name, target_name, up_name, enter_chunk, leave_chunk)` (namedtuple)
  - `aimcore.WORLD = "world"`, `TOLERANCE`, `FILL_PASSES`
  - pure: `diamond(r)`, `point_of(matrix, direction, distance)`, `up_axis(aim_v, up_v)`, `turn_between(a, b, order=0)`, `frames_off(aimed, baked, tolerance=TOLERANCE, order=0)`, `broken(made, constraint)`
  - scene: `long_(node)`, `uuid(node)`, `leaf(path)`, `groups(kind)`, `group_of(node, kind)`, `controllers(group, kind)`, `is_controller(node, kind)`, `constraint(node, kind)`, `stored_vectors(group, kind)`, `owner_of_group(group, kind)`, `rotate_refusal(node)`, `put(group, home)`, `clear_broken(node, kind, group, cleanup=None)`
  - engine: `aim_on(node, kind, vec, home_of, place, size=None) -> (keys, node_long_path)`; `aim_off(node, kind, group, made, cleanup=None) -> (keys, added)`

- [ ] **Step 1: Write the failing test**

`tests/test_scenesetup_aimcore.py`:

```python
"""The aim engine shared by the weapon's and the camera's Aim Mode (2026-10-28): the weapon module
re-exports the pure halves from it, so one fix serves both."""

import unittest

from maya_scenesetup import aimcore
from maya_scenesetup import weaponaim as wa


class Shared(unittest.TestCase):

    def test_the_weapon_s_pure_halves_are_the_core_s(self):
        for name in ("diamond", "point_of", "up_axis", "turn_between", "frames_off", "broken"):
            self.assertIs(getattr(wa, name), getattr(aimcore, name), name)

    def test_the_weapon_kind_keeps_its_scene_names(self):
        kind = wa.KIND
        self.assertEqual((kind.marker, kind.ctrl_marker, kind.con_marker, kind.vectors_attr),
                         ("skeldarWeaponAim", "skeldarWeaponAimCtrl", "skeldarWeaponAimOf",
                          "skeldarWeaponAimVectors"))
        self.assertEqual(kind.group_name.format("Sword"), "Sword_aim")
        self.assertEqual(kind.enter_chunk, "Connections: Aim Mode")
        self.assertEqual(kind.leave_chunk, "Connections: Default")

    def test_the_world_level_is_one_word_for_both(self):
        self.assertEqual(wa.WORLD, aimcore.WORLD)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_aimcore -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'maya_scenesetup.aimcore'`

- [ ] **Step 3: Write `aimcore.py`**

Lift, do not rewrite: each function below is the current `weaponaim` body with `weapon` renamed `node` and the module constants replaced by `kind.<field>`.

```python
"""The aim engine (2026-10-28): a node's rotation aims at two controllers keyed on its own keys
(Aim Mode), and back (Default). Lifted out of `weaponaim` when the camera got the same Aim Mode
(the animator: «такой же aim как для оружия») - an `AimKind` names a user's markers and words.

Spec: docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md
"""

import math
from collections import namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_timewarp
from maya_scenesetup import fkik

AimKind = namedtuple("AimKind", "marker ctrl_marker con_marker vectors_attr group_name "
                                "target_name up_name enter_chunk leave_chunk")

WORLD = "world"
ROTATE = fkik.ROTATE
TRANSLATE = fkik.TRANSLATE
LOCKED = ("rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ")
TARGET_COLOUR = (1.0, 0.45, 0.12)
UP_COLOUR = (0.25, 0.75, 1.0)
# Default keys the rotation on the keys, then on every frame between them that still turns more than
# this off the aim (2026-10-26: a fast swing between two keys came out 27 degrees off)
TOLERANCE = 0.1         # degrees
FILL_PASSES = 4         # a key added re-shapes its neighbours' auto tangents: checked again
```

Then move from `weaponaim.py`, verbatim apart from the renames:
- pure: `up_axis`, `point_of`, `diamond`, `turn_between`, `frames_off`, `broken` (keep their docstrings);
- `_long` → `long_`, `_uuid` → `uuid`, `_leaf` → `leaf`, `_span` → `span`, `_walk` → `walk`, `_world` → `world`, `_control` → `control`, `_local` → `local`, `_write_series` → `write_series`, `_put` → `put`;
- `_fill_between(weapon, ...)` → `fill_between(node, aimed, keyed, order)`.

Add the kind-parametrised scene readers (bodies as `weaponaim`'s with the constant swapped):

```python
def groups(kind):
    """Every aim group of `kind` in the scene (long paths); none where the scene cannot be asked."""
    try:
        found = cmds.ls("*." + kind.marker, recursive=True, objectsOnly=True, long=True,
                        type="transform") or []
    except (AttributeError, RuntimeError, TypeError):
        return []
    return list(dict.fromkeys(found))


def group_of(node, kind):
    found = groups(kind)
    key = uuid(node) if found else None
    for group in found if key else ():
        try:
            if cmds.getAttr(group + "." + kind.marker) == key:
                return group
        except (RuntimeError, ValueError):
            continue
    return None


def controllers(group, kind):
    """{"target": path, "up": path} under an aim group."""
    out = {}
    for child in cmds.listRelatives(group, children=True, fullPath=True, type="transform") or []:
        if cmds.attributeQuery(kind.ctrl_marker, node=child, exists=True):
            out[cmds.getAttr(child + "." + kind.ctrl_marker)] = child
    return out


def is_controller(node, kind):
    try:
        return bool(cmds.attributeQuery(kind.ctrl_marker, node=node, exists=True))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def owner_of_group(group, kind):
    return long_(cmds.getAttr(group + "." + kind.marker))


def stored_vectors(group, kind):
    values = [float(v) for v in cmds.getAttr(group + "." + kind.vectors_attr).split()]
    return tuple(values[0:3]), tuple(values[3:6]), values[6], values[7]


def constraint(node, kind):
    for con in cmds.listRelatives(node, children=True, fullPath=True,
                                  type="aimConstraint") or []:
        if cmds.attributeQuery(kind.con_marker, node=con, exists=True):
            return con
    return None


def is_aimed(node, kind):
    group = group_of(node, kind)
    return group is not None and not broken(controllers(group, kind), constraint(node, kind))


def rotate_refusal(node):
    """'' or why the rotate of `node` cannot be aimed: locked, layered or driven."""
    label = leaf(node)
    for ch in ROTATE:
        plug = node + "." + ch
        if cmds.getAttr(plug, lock=True):
            return "%s.%s is locked" % (label, ch)
        if fkik._layered(plug):
            return "%s.%s is on animation layers - bake its layers first" % (label, ch)
        driver = fkik._foreign(plug)
        if driver:
            return "%s.%s is driven by %s" % (label, ch, driver)
    return ""


def clear_broken(node, kind, group, cleanup=None):
    """What is left of a broken Aim Mode on `node` deleted: our constraint, the group."""
    con = constraint(node, kind)
    if con:
        cmds.delete(con)
    if cleanup:
        cleanup(group)
    if cmds.objExists(group):
        cmds.delete(group)


def make_controls(node, kind, size_target, size_up):
    """`weaponaim._make_controls` with `kind`'s names and markers; (group, {role: path})."""
```

`make_controls` body: `weaponaim._make_controls` with `GROUP_NAME/TARGET_NAME/UP_NAME/MARKER/CTRL_MARKER/VECTORS` → `kind.group_name/target_name/up_name/marker/ctrl_marker/vectors_attr`, `_control` → `control`.

The engine (the bodies of `weaponaim.enter` / `leave` between the chunk open and close):

```python
def aim_on(node, kind, vec, home_of, place, size=None):
    """Aim Mode's work on `node` (the caller holds the undo chunk and autoKey): controllers keyed on
    the node's own keys in `home_of(node)`'s space, `place(group, node)` putting the group there,
    the rotate keys cut and an aimConstraint (no offset) on. (keys, the node's long path)."""
    aim_v, up_v, d_aim, d_up = vec
    window = span()
    key = uuid(node)
    stale = group_of(node, kind)
    if stale:
        clear_broken(node, kind, stale)
    with maya_timewarp.unwarped():
        sample, keys, tangents = fkik.own_keys([long_(key)], [], window)
        fkik._suspend(True)
        try:
            home = home_of(long_(key))
            worlds = walk(sample, lambda: world(long_(key)))
            spaces = walk(sample, lambda: world(home)) if home and home != WORLD else None
        finally:
            fkik._suspend(False)
        size = size or max(d_aim, d_up) * 0.06
        group, made = make_controls(long_(key), kind, size, size * 0.8)
        cmds.setAttr(group + "." + kind.vectors_attr, " ".join(
            "%.12g" % v for v in tuple(aim_v) + tuple(up_v) + (d_aim, d_up)), type="string")
        group = place(group, long_(key))
        made = controllers(group, kind)
        frames = list(sample)
        if keys:
            targets = [local(point_of(worlds[f], aim_v, d_aim), spaces, f) for f in frames]
            ups = [local(point_of(worlds[f], up_v, d_up), spaces, f) for f in frames]
            write_series(made["target"], frames, targets, window, tangents)
            write_series(made["up"], frames, ups, window, tangents)
        else:
            now = frames[0]
            for role, direction, distance in (("target", aim_v, d_aim), ("up", up_v, d_up)):
                cmds.xform(made[role], worldSpace=True,
                           translation=point_of(worlds[now], direction, distance))
        node = long_(key)
        for ch in ROTATE:
            cmds.cutKey(node + "." + ch, clear=True)
        con = cmds.aimConstraint(made["target"], node, maintainOffset=False,
                                 aimVector=aim_v, upVector=up_axis(aim_v, up_v),
                                 worldUpType="object", worldUpObject=made["up"])[0]
        cmds.addAttr(con, longName=kind.con_marker, dataType="string")
        cmds.setAttr(con + "." + kind.con_marker, key, type="string")
    return keys, long_(key)


def aim_off(node, kind, group, made, cleanup=None):
    """Default's work on `node` (the caller holds the chunk): the rotation keyed back on the keys of
    the controllers and of its translate, then between them (`fill_between`), the constraint and the
    group deleted. (keys, how many keys were added between them)."""
```

`aim_off` body: `weaponaim.leave` from `from maya_poselib import helpers` through `added = _fill_between(...)`, with `weapon` → `node`, `_constraint(weapon)` → `constraint(node, kind)`, `_drop_lines(group)` → `if cleanup: cleanup(group)`, returning `keys, added`.

- [ ] **Step 4: Make `weaponaim` delegate**

In `weaponaim.py` keep the module docstring, the constants (`MARKER` ... `NO_GEOMETRY`, `UP_SHARE`, `UP_ALONG`, `LINE_MARKER`, `WORLD`), `vectors`, `entered_message`, `left_message`, `home_of`, `_park`, `rehome`, `_drop_lines`, `_into_1p`. Replace the rest with:

```python
from maya_scenesetup import aimcore
from maya_scenesetup.aimcore import (broken, diamond, frames_off, point_of, turn_between,  # noqa: F401
                                     up_axis, TOLERANCE, FILL_PASSES, ROTATE, TRANSLATE, LOCKED,
                                     TARGET_COLOUR, UP_COLOUR)

KIND = aimcore.AimKind(MARKER, CTRL_MARKER, CON_MARKER, VECTORS, GROUP_NAME, TARGET_NAME, UP_NAME,
                       "Connections: Aim Mode", "Connections: Default")
WORLD = aimcore.WORLD
_long, _uuid, _leaf, _put = aimcore.long_, aimcore.uuid, aimcore.leaf, aimcore.put


def groups():
    return aimcore.groups(KIND)


def group_of(weapon):
    return aimcore.group_of(weapon, KIND)


def is_aimed(weapon):
    return aimcore.is_aimed(weapon, KIND)


def controllers(group):
    return aimcore.controllers(group, KIND)


def is_controller(node):
    return aimcore.is_controller(node, KIND)


def weapon_of_group(group):
    return aimcore.owner_of_group(group, KIND)


def stored_vectors(group):
    return aimcore.stored_vectors(group, KIND)


def _constraint(weapon):
    return aimcore.constraint(weapon, KIND)


def refusal(weapon):
    """'' or why `weapon` cannot go into Aim Mode."""
    if not weapon or not cmds.objExists(weapon):
        return NO_WEAPON
    if is_aimed(weapon):
        return ALREADY % _leaf(weapon)
    return aimcore.rotate_refusal(weapon)


def enter(weapon):
    """Aim Mode on `weapon` (refusals first; nothing changed on one). The status line."""
    why = refusal(weapon)
    if why:
        return why
    weapon = _long(weapon)
    label = _leaf(weapon)
    extents = aimplace.local_extents(weapon)
    vec = vectors(*extents) if extents else None
    if vec is None:
        return NO_GEOMETRY % label
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.enter_chunk)
    try:
        cmds.autoKeyframe(state=False)
        keys, weapon = aimcore.aim_on(weapon, KIND, vec, home_of, _park)
        #  a rig in 1P (Tools > 1P Setup, 2026-10-21): the controllers ride its chest
        in_1p = _into_1p(weapon)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = entered_message(label, keys)
    return line + (" | " + in_1p if in_1p else "")


def leave(weapon):
    """Default on `weapon` (`aimcore.aim_off`). The status line."""
    weapon = _long(weapon)
    if not weapon:
        return NO_WEAPON
    label = _leaf(weapon)
    group = group_of(weapon)
    if group is None:
        return NOT_AIMED % label
    made = controllers(group)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.leave_chunk)
    try:
        cmds.autoKeyframe(state=False)
        if broken(made, _constraint(weapon)):
            aimcore.clear_broken(weapon, KIND, group, _drop_lines)
            return CLEARED % label
        keys, added = aimcore.aim_off(weapon, KIND, group, made, _drop_lines)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = left_message(label, keys)
    return line + (" + %d between them where the aim turned faster" % added if added else "")
```

`home_of`, `_park` and `rehome` keep their bodies; they already call `_long` / `_uuid` / `_put` / `controllers`, now the aliases. Delete `_clear_broken`, `_make_controls`, `_control`, `_walk`, `_world`, `_local`, `_write_series`, `_span`, `_fill_between` from `weaponaim`.

- [ ] **Step 5: Run the unit tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_aimcore tests.test_scenesetup_weaponaim tests.test_scenesetup_connections -v`
Expected: all PASS.

Then the whole suite: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: same pass count as before the task (record it first with a run on the untouched tree), 0 failures.

- [ ] **Step 6: Run the weapon aim's scene proof**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_weapon_aim_mode.py $env:TEMP\aim_t1.txt`
Expected: `21/21` (unchanged behaviour).

- [ ] **Step 7: Commit**

```bash
git commit -F msg.txt -- SkeldarAnim/maya_scenesetup/aimcore.py SkeldarAnim/maya_scenesetup/weaponaim.py tests/test_scenesetup_aimcore.py
```
Message: `refactor(aim): the weapon's Aim Mode engine lifted into aimcore for the camera's`.
(`git add` the new files by path first.)

---

### Task 2: `cameraaim.py` - Aim Mode and Default on `Camera_ctrl`

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/cameraaim.py`
- Test: `tests/test_scenesetup_cameraaim.py`

**Interfaces:**
- Consumes: `aimcore.*` (Task 1); `camera.AXIS_OFFSET`, `camera.is_control(node)`.
- Produces: `cameraaim.KIND`, `AIM_DISTANCE`, `UP_DISTANCE`, `CONTROL_SIZE`, `camera_vectors(offset=camera.AXIS_OFFSET) -> (aim_v, up_v, d_aim, d_up)`, `home_of(control) -> path | aimcore.WORLD`, `group_of(control)`, `controllers(group)`, `is_controller(node)`, `stored_vectors(group)`, `is_aimed(control) -> bool`, `refusal(control) -> str`, `enter(control) -> str`, `leave(control) -> str`, `discard(control)` (delete the aim without baking), `NO_CAMERA`, `ALREADY`, `NOT_AIMED`, `CLEARED`.

- [ ] **Step 1: Write the failing test**

```python
"""The camera's Aim Mode (2026-10-28): the pure halves. The scene half is
docs/superpowers/plans/verify_camera_tab.py."""

import unittest

from maya_scenesetup import aimcore
from maya_scenesetup import cameraaim as ca


class Pure(unittest.TestCase):

    def test_the_view_is_the_camera_s_minus_z_in_the_control_s_frame(self):
        aim_v, up_v, d_aim, d_up = ca.camera_vectors()
        # AXIS_OFFSET's rows: (-1,0,0), (0,0,1), (0,1,0): -Z goes to -Y, +Y to +Z
        self.assertEqual(aim_v, (0.0, -1.0, 0.0))
        self.assertEqual(up_v, (0.0, 0.0, 1.0))
        self.assertEqual((d_aim, d_up), (ca.AIM_DISTANCE, ca.UP_DISTANCE))

    def test_an_identity_offset_aims_down_minus_z(self):
        identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
        aim_v, up_v, _d, _du = ca.camera_vectors(identity)
        self.assertEqual(aim_v, (0.0, 0.0, -1.0))
        self.assertEqual(up_v, (0.0, 1.0, 0.0))

    def test_the_up_is_across_the_view(self):
        aim_v, up_v, _d, _du = ca.camera_vectors()
        self.assertEqual(aimcore.up_axis(aim_v, up_v), up_v)

    def test_the_kind_has_names_of_its_own(self):
        self.assertEqual(ca.KIND.marker, "skeldarCameraAim")
        self.assertEqual(ca.KIND.group_name.format("Camera_ctrl"), "Camera_ctrl_aim")
        self.assertNotEqual(ca.KIND.ctrl_marker, "skeldarWeaponAimCtrl")


class Refusals(unittest.TestCase):

    def test_no_camera(self):
        saved = ca.cmds
        try:
            class Fake(object):
                @staticmethod
                def objExists(_n):
                    return False
            ca.cmds = Fake
            self.assertEqual(ca.refusal("|nothing"), ca.NO_CAMERA)
            self.assertEqual(ca.refusal(None), ca.NO_CAMERA)
        finally:
            ca.cmds = saved


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_cameraaim -v`
Expected: FAIL with `No module named 'maya_scenesetup.cameraaim'`

- [ ] **Step 3: Write `cameraaim.py`**

```python
"""Aim Mode for the camera (2026-10-28): `Camera_ctrl`'s rotation aims at two controllers, as the
weapon's (the animator: «В разделе для камеры нужно реализовать такой же aim как для оружия»).

The camera under the control stays locked; the control carries the motion, so the control is what
aims. The vectors are the camera's own: its view (-Z) and its up (+Y) through `AXIS_OFFSET`, the
target `AIM_DISTANCE` ahead and the up `UP_DISTANCE` above. The group repeats the control's
parent (Main, Root_ctrl, the chest, FKHead_M, Camera_follow, ...).

Spec: docs/superpowers/specs/2026-10-28-connections-camera-tab-design.md
"""

import maya.cmds as cmds

from maya_scenesetup import aimcore
from maya_scenesetup import camera

KIND = aimcore.AimKind("skeldarCameraAim", "skeldarCameraAimCtrl", "skeldarCameraAimOf",
                       "skeldarCameraAimVectors", "{0}_aim", "{0}_aimTarget", "{0}_aimUp",
                       "Connections: Camera Aim Mode", "Connections: Camera Default")
AIM_DISTANCE = 300.0     # cm ahead of the lens
UP_DISTANCE = 50.0       # cm above it
CONTROL_SIZE = 8.0       # the target diamond's radius, cm

NO_CAMERA = "no camera with a control - Characters > Camera Setup first"
ALREADY = "%s is in Aim Mode already - Default first"
NOT_AIMED = "%s is not in Aim Mode"
CLEARED = ("%s: its Aim Mode was broken (the controllers or the constraint deleted) - cleared, "
           "the rotation left as it is")


def camera_vectors(offset=camera.AXIS_OFFSET):
    """(aim vector, up vector, aim distance, up distance) in the control's frame: the camera's -Z
    and +Y carried through the row-vector `offset` (camera local = offset · control). Pure."""
    rows = [offset[0:3], offset[4:7], offset[8:11]]

    def through(v):
        return tuple(float(sum(v[i] * rows[i][j] for i in range(3))) + 0.0 for j in range(3))

    return through((0, 0, -1)), through((0, 1, 0)), AIM_DISTANCE, UP_DISTANCE


def home_of(control):
    """The control's own parent, or the world level."""
    parents = cmds.listRelatives(control, parent=True, fullPath=True) or []
    return parents[0] if parents else aimcore.WORLD


def _place(group, control):
    return aimcore.put(group, home_of(control))


def group_of(control):
    return aimcore.group_of(control, KIND)


def controllers(group):
    return aimcore.controllers(group, KIND)


def is_controller(node):
    return aimcore.is_controller(node, KIND)


def stored_vectors(group):
    return aimcore.stored_vectors(group, KIND)


def is_aimed(control):
    return bool(control) and aimcore.is_aimed(control, KIND)


def refusal(control):
    """'' or why the camera's control cannot go into Aim Mode."""
    if not control or not cmds.objExists(control) or not camera.is_control(control):
        return NO_CAMERA
    if is_aimed(control):
        return ALREADY % aimcore.leaf(control)
    return aimcore.rotate_refusal(control)


def enter(control):
    """Aim Mode on the camera's control. The status line."""
    why = refusal(control)
    if why:
        return why
    control = aimcore.long_(control)
    label = aimcore.leaf(control)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.enter_chunk)
    try:
        cmds.autoKeyframe(state=False)
        keys, _control = aimcore.aim_on(control, KIND, camera_vectors(), home_of, _place,
                                        size=CONTROL_SIZE)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    if not keys:
        return "%s in Aim Mode - no keys of its own: the controllers set at the current frame" % label
    return "%s in Aim Mode on %d key%s (%g..%g) - animate %s_aimTarget / _aimUp" % (
        label, len(keys), "" if len(keys) == 1 else "s", keys[0], keys[-1], label)


def leave(control):
    """Default on the camera's control. The status line."""
    control = aimcore.long_(control)
    if not control:
        return NO_CAMERA
    label = aimcore.leaf(control)
    group = group_of(control)
    if group is None:
        return NOT_AIMED % label
    made = controllers(group)
    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(openChunk=True, chunkName=KIND.leave_chunk)
    try:
        cmds.autoKeyframe(state=False)
        if aimcore.broken(made, aimcore.constraint(control, KIND)):
            aimcore.clear_broken(control, KIND, group)
            return CLEARED % label
        keys, added = aimcore.aim_off(control, KIND, group, made)
    finally:
        cmds.autoKeyframe(state=auto)
        cmds.undoInfo(closeChunk=True)
    line = ("%s back to Default on %d key%s" % (label, len(keys), "" if len(keys) == 1 else "s")
            if keys else "%s back to Default - no keys: its rotation set at the current frame" % label)
    return line + (" + %d between them where the aim turned faster" % added if added else "")


def discard(control):
    """The aim on `control` deleted without baking (the control itself is going)."""
    group = group_of(control) if control else None
    if group:
        aimcore.clear_broken(control, KIND, group)
```

- [ ] **Step 4: Run tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_cameraaim -v`
Expected: PASS (5 tests). If `camera_vectors` returns `-0.0` components, the `+ 0.0` normalises them; `assertEqual` treats `-0.0 == 0.0` anyway.

- [ ] **Step 5: Commit**

Paths: `SkeldarAnim/maya_scenesetup/cameraaim.py tests/test_scenesetup_cameraaim.py`. Message: `feat(connections): the camera's Aim Mode and Default on Camera_ctrl`.

---

### Task 3: Head and Position only in `camera.set_parent`

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/camera.py` (constants near `PARENTS`, `parent_target`, `parent_choice`, `_mark_parent`, `move_control`, `set_parent`, `go_home`, `teardown`)
- Test: `tests/test_scenesetup_camera.py` (append a class)

**Interfaces:**
- Consumes: `cameraaim.is_aimed / leave / enter / discard` (Task 2).
- Produces: `camera.PARENTS` (five), `HEAD = "FKHead_M"`, `FOLLOW_MARKER = "skeldarCameraFollow"`, `FOLLOW_NAME = "Camera_follow"`, `POSITION_MARKER = "skeldarCameraPosition"`, `NO_CONTROL`, `position_applies(choice) -> bool` (pure), `follow_name_for(bone) -> str` (pure), `follow_of(control) -> path | None`, `is_position_only(control) -> bool`, `set_parent(bone, choice, position_only=False) -> str`, `release_followers(node) -> list[str]` (lines).

- [ ] **Step 1: Write the failing test** (append to `tests/test_scenesetup_camera.py`, above `if __name__`)

```python
class Parents(unittest.TestCase):

    def test_five_parents_head_before_world(self):
        from maya_scenesetup import camera
        self.assertEqual(camera.PARENTS, ("Main", "Root", "Chest", "Head", "World"))

    def test_position_only_means_nothing_for_main_and_world(self):
        from maya_scenesetup import camera
        self.assertFalse(camera.position_applies("Main"))
        self.assertFalse(camera.position_applies("World"))
        for choice in ("Root", "Chest", "Head"):
            self.assertTrue(camera.position_applies(choice), choice)

    def test_the_follow_group_is_named_in_the_bone_s_namespace(self):
        from maya_scenesetup import camera
        self.assertEqual(camera.follow_name_for("|g|Manny:root|Manny:camera_root"),
                         "Manny:Camera_follow")
        self.assertEqual(camera.follow_name_for("camera_root"), "Camera_follow")
```

- [ ] **Step 2: Run to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_camera.Parents -v`
Expected: FAIL (`PARENTS` has four; `position_applies` missing).

- [ ] **Step 3: Implement**

Constants (replace the `PARENTS` line):

```python
PARENTS = ("Main", "Root", "Chest", "Head", "World")
HEAD = "FKHead_M"
# Position only (2026-10-28, «опцией которая может привязать только позицию как поинт констрейн»):
# the control in a group under Main, point-constrained to the chosen node - its rotation stays Main's
FOLLOW_MARKER = "skeldarCameraFollow"       # on the group: the followed node's UUID
FOLLOW_NAME = "Camera_follow"
POSITION_MARKER = "skeldarCameraPosition"   # on the control: 1 while it follows a position only
NO_CONTROL = "no camera with a control on %s - press Camera Setup first"
```

Pure helpers beside `control_name_for`:

```python
def position_applies(choice):
    """Does Position only change anything for `choice`? Main is the rotation space already; World
    has no position to follow. Pure."""
    return choice not in ("Main", "World")


def follow_name_for(bone):
    """The follow group's name, in the bone's own namespace. Pure."""
    short = (bone or "").split("|")[-1]
    namespace = short.rsplit(":", 1)[0] if ":" in short else ""
    return namespace + ":" + FOLLOW_NAME if namespace else FOLLOW_NAME
```

`parent_target`: add before the final `return`:

```python
    if choice == "Head":
        import maya_rigs
        head = maya_rigs.node(rig, HEAD)
        if not cmds.objExists(head):
            return None, "Head: no %s on %s" % (HEAD, maya_rigs.label(rig))
        return (cmds.ls(head, long=True) or [head])[0], ""
```

Follow group readers and makers:

```python
def follow_of(control):
    """The Camera_follow group the control stands in, or None."""
    parents = (cmds.listRelatives(control, parent=True, fullPath=True) or []) if control else []
    if parents and cmds.attributeQuery(FOLLOW_MARKER, node=parents[0], exists=True):
        return parents[0]
    return None


def is_position_only(control):
    return bool(control) and cmds.attributeQuery(POSITION_MARKER, node=control, exists=True) \
        and bool(cmds.getAttr(control + "." + POSITION_MARKER))


def _make_follow(bone, target):
    """A group under the rig's Main at identity, point-constrained (no offset) to `target`."""
    rig = _rig_of(bone)
    main = (cmds.ls(rig.main, long=True) or [rig.main])[0]
    group = cmds.createNode("transform", name=scope.as_created(follow_name_for(bone)),
                            parent=main, skipSelect=True)
    group = cmds.ls(group, long=True)[0]
    cmds.addAttr(group, longName=FOLLOW_MARKER, dataType="string")
    cmds.setAttr(group + "." + FOLLOW_MARKER, cmds.ls(target, uuid=True)[0], type="string")
    cmds.pointConstraint(target, group, maintainOffset=False)
    return group


def _drop_follow(group):
    """An emptied follow group deleted (its point constraint with it)."""
    if not group or not cmds.objExists(group):
        return
    kids = [c for c in cmds.listRelatives(group, children=True, fullPath=True) or []
            if not cmds.objectType(c, isAType="constraint")]
    if not kids:
        cmds.delete(group)


def _mark_position(control, on):
    if not cmds.attributeQuery(POSITION_MARKER, node=control, exists=True):
        cmds.addAttr(control, longName=POSITION_MARKER, attributeType="bool")
    cmds.setAttr(control + "." + POSITION_MARKER, lock=False)
    cmds.setAttr(control + "." + POSITION_MARKER, bool(on))
    cmds.setAttr(control + "." + POSITION_MARKER, lock=True)
```

`move_control`: keep the `current == parent` shortcut first; then wrap the rebake in the aim (any caller - set_parent, go_home, 1P Setup - keeps Aim Mode):

```python
def move_control(control, parent, choice):
    """The control under `parent` (None: world level) with its motion kept ... Its long path. A
    control in Aim Mode leaves it first and enters it again in its new parent (2026-10-28)."""
    from maya_tools import knots, reparent
    current = cmds.listRelatives(control, parent=True, fullPath=True)
    current = current[0] if current else None
    if current == parent:
        _mark_parent(control, choice)
        return control
    from maya_scenesetup import cameraaim
    aimed = cameraaim.is_aimed(control)
    if aimed:
        cameraaim.leave(control)
    # ... the existing body from `span = reparent._take(...)` through `_mark_parent(control, choice)` ...
    if aimed:
        cameraaim.enter(control)
    return control
```

`set_parent`:

```python
def set_parent(bone, choice, position_only=False):
    """The camera's control for `bone` under the parent `choice` names, its motion kept; with
    `position_only` (Root / Chest / Head) in a follow group under Main point-constrained to it. The
    line."""
    control = control_for(bone)
    if not control:
        return NO_CONTROL % leaf(bone)
    target, refusal = parent_target(bone, choice)
    if refusal:
        return refusal
    follow = bool(position_only) and position_applies(choice)
    from maya_tools import knots
    with knots._press("skeldarCameraParent"):       # one undo step, autoKey off
        old = follow_of(control)
        if follow:
            target = _make_follow(bone, target)
        control = move_control(control, target, choice)
        _mark_position(control, follow)
        if old and old != target:
            _drop_follow(old)
    line = PARENT_LINE % (leaf(control), choice + (" (position)" if follow else ""))
    if position_only and not follow:
        line += " - Position only changes nothing for %s" % choice
    return line
```

Note: `move_control`'s shortcut never fires for a fresh follow group (a new node), so the rebake always runs when switching into Position only.

`go_home(control)`: remember `old = follow_of(control)` first, run the existing body, then `_mark_position(control, False)` and `_drop_follow(old)` before returning.

`release_followers(node)` (for Task 4):

```python
def release_followers(node):
    """Every control following `node`'s position only (a follow group pointing at it) back home -
    `node` is going (1P Setup's chest baked off). The lines."""
    key = (cmds.ls(node, uuid=True) or [None])[0]
    lines = []
    for group in cmds.ls("*." + FOLLOW_MARKER, recursive=True, objectsOnly=True, long=True) or []:
        if cmds.getAttr(group + "." + FOLLOW_MARKER) != key:
            continue
        for child in cmds.listRelatives(group, children=True, fullPath=True) or []:
            if is_control(child):
                go_home(child)
                lines.append("%s back under Main" % leaf(child))
    return lines
```

`teardown`: before `cmds.delete(control)` add

```python
    if control:
        from maya_scenesetup import cameraaim
        cameraaim.discard(control)
        old = follow_of(control)
```
and after the delete `_drop_follow(old)` (guard `old` defined: initialise `old = None` at the top).

- [ ] **Step 4: Run tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_camera tests.test_tools_firstperson tests.test_tools_panel -v`
Expected: all PASS (the 1P buttons call `set_parent(bone, choice)` positionally - unchanged).

- [ ] **Step 5: Commit**

Paths: `SkeldarAnim/maya_scenesetup/camera.py tests/test_scenesetup_camera.py`. Message: `feat(connections): the camera follows Head, and Position only through a follow group`.

---

### Task 4: The chest's bake-off lets camera followers and camera aims go safely

**Files:**
- Modify: `SkeldarAnim/maya_tools/knots.py` (`_release_children`, ~line 1090)
- Test: covered by `verify_camera_tab.py` (Task 7) and the re-run of `verify_camera_control.py`; no unit seam here.

**Interfaces:**
- Consumes: `camera.release_followers(node)` (Task 3).

- [ ] **Step 1: Edit `_release_children`**

Inside the inner loop, first line: a child the camera's aim already took away is gone -

```python
        for child in _children(node):
            if not cmds.objExists(child):     # a camera's Aim Mode group went with its control
                continue
```

After the outer `for node in ...` loop:

```python
    try:
        from maya_scenesetup import camera
        camera.release_followers(top)       # a camera following the chest's position only
    except Exception:                       # noqa: BLE001 - never stop a Bake / Remove over it
        pass
```

- [ ] **Step 2: Run the knots and 1P unit tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_tools_knots tests.test_tools_firstperson -v`
Expected: PASS.

- [ ] **Step 3: Commit**

Paths: `SkeldarAnim/maya_tools/knots.py`. Message: `fix(knots): the chest's bake-off sends a camera following it home`.

---

### Task 5: The Camera tab in the Connections card, its hotkeys

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` (constants ~line 125-140, new functions beside `aim_mode` ~1513, `show_tab`, `refresh` ~1320, `build_panel` ~1660-1790)
- Modify: `SkeldarAnim/maya_hotkeys.py` (after `connections.default`, ~line 1285)
- Test: `tests/test_scenesetup_weaponaim.py` (`Tabs.test_two_tab_segments_body_first` updated), new `tests/test_scenesetup_connections_camera.py`

**Interfaces:**
- Consumes: `camera.PARENTS`, `camera.set_parent`, `camera.control_for`, `camera.parent_choice`, `camera.is_position_only`, `camera.NO_CONTROL`, `cameraaim.enter/leave/is_aimed`, `firstperson._selected_bone(selection=None) -> (bone, refusal)`.
- Produces: `connections.camera_parent(choice, position_only=False) -> str`, `connections.camera_aim(on=True) -> str`, `connections.camera_text(choice, position, aimed) -> str` (pure), `CAMERA_MENU`, `CAMERA_POSITION`, `CAMERA_AIM_BUTTON`, `CAMERA_DEFAULT_BUTTON`, `camera_segment(choice)`, `_press_camera_parent`, `_press_camera_aim_mode`, `_press_camera_default`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scenesetup_weaponaim.py`, `Tabs.test_two_tab_segments_body_first` becomes:

```python
    def test_three_tab_segments_body_first(self):
        self.assertEqual([label for _n, label in self.fake.segments[cx.TAB_COLLECTION]],
                         ["Body", "Weapon", "Camera"])
        self.assertEqual(self.marks[cx.tab_segment("body")].role, "segment")
```

New `tests/test_scenesetup_connections_camera.py`:

```python
"""Connections' Camera tab (2026-10-28): the card's rows and the presses. The scene half is
docs/superpowers/plans/verify_camera_tab.py."""

import unittest

from maya_scenesetup import camera
from maya_scenesetup import connections as cx

from tests.test_scenesetup_connections import FakeMenuCmds


class Text(unittest.TestCase):

    def test_the_state_line(self):
        self.assertEqual(cx.camera_text("Head", True, True), "Camera: Head (position) - Aim Mode")
        self.assertEqual(cx.camera_text("Main", False, False), "Camera: Main")
        self.assertEqual(cx.camera_text(None, False, False), cx.NO_CAMERA_TEXT)


class Card(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        cx.cmds, cx.refresh = self.real

    def test_the_parents_are_the_camera_s_five(self):
        self.assertEqual([label for _n, label in self.fake.segments[cx.CAMERA_MENU]],
                         list(camera.PARENTS))

    def test_the_camera_tab_holds_parent_position_and_aim(self):
        order = [c[1][0] if c[1] else c[2].get("label") for c in self.fake.calls
                 if c[0] in ("columnLayout", "checkBox", "button", "iconTextRadioCollection")
                 and not c[2].get("edit")]
        column = order.index(cx.TAB_COLUMN["camera"])
        for item in (cx.CAMERA_MENU, cx.CAMERA_POSITION, cx.CAMERA_AIM_BUTTON,
                     cx.CAMERA_DEFAULT_BUTTON):
            self.assertLess(column, order.index(item), item)

    def test_aim_mode_is_the_camera_tab_s_primary(self):
        self.assertEqual(self.marks[cx.CAMERA_AIM_BUTTON].role, "primary")
        self.assertEqual(self.marks[cx.CAMERA_DEFAULT_BUTTON].role, "secondary")


class Presses(unittest.TestCase):

    def test_the_aim_presses_go_through_camera_aim(self):
        asked = []
        saved = cx.camera_aim
        cx.camera_aim = lambda on=True: asked.append(on) or "done"
        try:
            cx._press_camera_aim_mode()
            cx._press_camera_default()
        finally:
            cx.camera_aim = saved
        self.assertEqual(asked, [True, False])

    def test_no_camera_refuses_the_parent(self):
        saved = cx._camera_bone
        cx._camera_bone = lambda: (None, "select any part of a character")
        try:
            self.assertEqual(cx.camera_parent("Head"), "select any part of a character")
            self.assertEqual(cx.camera_aim(True), "select any part of a character")
        finally:
            cx._camera_bone = saved


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_camera tests.test_scenesetup_weaponaim -v`
Expected: FAIL (`camera_text` / `CAMERA_MENU` missing; two tab segments).

- [ ] **Step 3: Implement in `connections.py`**

Imports: add `from maya_scenesetup import camera` and `from maya_scenesetup import cameraaim` beside the others.

Constants:

```python
CAPTION = {..., "camparent": "skeldarConnectionsCapCamParent",
           "camaim": "skeldarConnectionsCapCamAim"}
# [Body | Weapon | Camera] (2026-10-28, «Во вкладке конекшен нужно добавить раздел для камер»)
TABS = (("body", "Body"), ("weapon", "Weapon"), ("camera", "Camera"))
TAB_COLUMN = {"body": "skeldarConnectionsBodyTab", "weapon": "skeldarConnectionsWeaponTab",
              "camera": "skeldarConnectionsCameraTab"}
CAMERA_MENU = "skeldarConnectionsCameraParent"
CAMERA_POSITION = "skeldarConnectionsCameraPosition"
CAMERA_AIM_BUTTON = "skeldarConnectionsCameraAimMode"
CAMERA_DEFAULT_BUTTON = "skeldarConnectionsCameraDefault"
NO_CAMERA_TEXT = "no camera - Characters > Camera Setup first"
```

Functions (beside `aim_mode`):

```python
def camera_segment(choice):
    return "skeldarConnectionsCamera_" + choice


def camera_text(choice, position, aimed):
    """The Camera tab's state line. Pure."""
    if choice is None:
        return NO_CAMERA_TEXT
    return "Camera: %s%s%s" % (choice or "?", " (position)" if position else "",
                               " - Aim Mode" if aimed else "")


def _camera_bone():
    from maya_tools import firstperson
    return firstperson._selected_bone()


def _camera_control():
    """(the active character's camera control, refusal)."""
    bone, refusal = _camera_bone()
    if refusal:
        return None, refusal
    control = camera.control_for(bone)
    return (control, "") if control else (None, camera.NO_CONTROL % camera.leaf(bone))


def camera_parent(choice, position_only=False):
    """The camera's control under `choice` (2026-10-28), position only if asked. The line."""
    bone, refusal = _camera_bone()
    if refusal:
        return refusal
    return camera.set_parent(bone, choice, position_only)


def camera_aim(on=True):
    """Aim Mode (`on`) or Default on the active character's camera. The line."""
    control, refusal = _camera_control()
    if refusal:
        return refusal
    return cameraaim.enter(control) if on else cameraaim.leave(control)


def _camera_state():
    """(choice or None, position only, aimed) of the active character's camera."""
    try:
        control, refusal = _camera_control()
    except Exception:                                        # noqa: BLE001 - no scene to ask
        return None, False, False
    if refusal:
        return None, False, False
    return (camera.parent_choice(control) or "", camera.is_position_only(control),
            cameraaim.is_aimed(control))


def _set_camera(choice, position):
    if choice and cmds.iconTextRadioButton(camera_segment(choice), exists=True):
        cmds.iconTextRadioButton(camera_segment(choice), edit=True, select=True)
    if cmds.checkBox(CAMERA_POSITION, exists=True):
        cmds.checkBox(CAMERA_POSITION, edit=True, value=bool(position))


def _chosen_camera_parent():
    picked = cmds.iconTextRadioCollection(CAMERA_MENU, query=True, select=True) or ""
    for choice in camera.PARENTS:
        if picked.endswith(camera_segment(choice)):
            return choice
    return camera.PARENTS[0]


def _press_camera_parent(*_args):
    position = bool(cmds.checkBox(CAMERA_POSITION, query=True, value=True))
    return _run(lambda: camera_parent(_chosen_camera_parent(), position))


def _press_camera_aim_mode(*_args):
    return _run(lambda: camera_aim(True))


def _press_camera_default(*_args):
    return _run(lambda: camera_aim(False))
```

`refresh`: after the weapon's `text` is built, replace the final `cmds.text(HEADER, ...)` with:

```python
    if current_tab() == "camera":
        choice, position, aimed = _camera_state()
        _set_camera(choice, position)
        text = camera_text(choice, position, aimed)
    cmds.text(HEADER, edit=True, label=text)
    return text
```

`show_tab`: after the loop that manages the columns, inside the `try`, add `refresh()` wrapped in `try/except Exception: pass` (`# noqa: BLE001`), so the subtitle follows the tab.

`build_panel`: after the weapon column's closing `cmds.setParent("..")` (the one before the STATUS text), add:

```python
    cmds.columnLayout(TAB_COLUMN["camera"], adjustableColumn=True,
                      rowSpacing=hubstyle.row_spacing(6), manage=tab == "camera")
    _caption("camparent", "Camera parent")
    segments = cmds.rowLayout(numberOfColumns=len(camera.PARENTS),
                              columnAttach=[(i + 1, "both", 1) for i in range(len(camera.PARENTS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(CAMERA_MENU)
    for index, choice in enumerate(camera.PARENTS):
        hubstyle.mark(cmds.iconTextRadioButton(
            camera_segment(choice), style="textOnly", label=choice,
            height=hubstyle.height("segment", 22), select=index == 0,
            annotation="the camera control's parent: %s" % choice), "segment")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "right", 0)])
    hubstyle.mark(cmds.checkBox(
        CAMERA_POSITION, label="Position only", value=False,
        annotation="Follow the parent's position only (a point constraint); the camera turns "
                   "with Main"), "chip")
    hubstyle.mark(cmds.button(
        label=hubstyle.tool_label("Apply"), width=hubstyle.tool_width(66),
        height=hubstyle.height("small", 24),
        annotation="the camera under the chosen parent, its motion kept",
        command=_press_camera_parent), "tool", "check")
    cmds.setParent("..")
    _caption("camaim", "Camera aim")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3)])
    hubstyle.mark(cmds.button(
        CAMERA_AIM_BUTTON, label="Aim Mode", height=hubstyle.height("button", 32),
        annotation="The camera's turn aims at two controllers (a target ahead, an up above), "
                   "keyed on the camera's own keys - it looks where it looked on every key",
        command=_press_camera_aim_mode), "primary", "target")
    hubstyle.mark(cmds.button(
        CAMERA_DEFAULT_BUTTON, label="Default", height=hubstyle.height("button", 32),
        width=hubstyle.pick(90, 96),
        annotation="The aim baked back onto the camera's rotation, the controllers removed",
        command=_press_camera_default), "secondary", "rotate")
    cmds.setParent("..")
    cmds.setParent("..")
```

Check `columnAttach` keyword for the TAB row: `build_panel`'s tab row already uses `len(TABS)` - three segments follow automatically.

- [ ] **Step 4: Hotkeys** (`maya_hotkeys.py`, after the `connections.default` row)

```python
    ("connections.camera_aim", "Connections", "Camera Aim Mode",
     "The camera's turn aims at two controllers, keyed on its own keys",
     partial(_connections, "_press_camera_aim_mode")),
    ("connections.camera_default", "Connections", "Camera Default",
     "The camera's aim baked back onto its rotation, the controllers removed",
     partial(_connections, "_press_camera_default")),
```

- [ ] **Step 5: Run tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_connections_camera tests.test_scenesetup_weaponaim tests.test_scenesetup_connections tests.test_hotkeys -v`
Expected: PASS. If `test_hotkeys` pins a row count, raise it by 2 in that test.

- [ ] **Step 6: Commit**

Paths: `SkeldarAnim/maya_scenesetup/connections.py SkeldarAnim/maya_hotkeys.py tests/test_scenesetup_connections_camera.py tests/test_scenesetup_weaponaim.py` (+ `tests/test_hotkeys.py` if touched). Message: `feat(connections): a Camera tab - five parents, Position only, Aim Mode / Default`.

---

### Task 6: The Pose Library writes a camera on Head, following, or aimed

**Files:**
- Modify: `SkeldarAnim/maya_poselib/helpers.py` (`_camera_carrier` ~214, `_aim_of` ~232, `Writer._prepare` ~288, the `aimed` write ~384)
- Modify: `SkeldarAnim/maya_poselib/scene.py` (`_kind` ~953)
- Test: `tests/test_poselib_helpers.py` (append)

**Interfaces:**
- Consumes: `camera.HEAD`, `camera.FOLLOW_MARKER`, `cameraaim.group_of / controllers / stored_vectors / is_controller`.
- Produces: `helpers._aim_of(driver)` now answers for a weapon OR a camera control; `HEAD_BONE = "head"`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_poselib_helpers.py`; it already fakes `cmds` per test class - follow the nearest `CameraIsBody` class's setup)

```python
class CameraCarriers(unittest.TestCase):

    def test_head_and_follow_carriers(self):
        from maya_poselib import helpers
        self.assertEqual(helpers.HEAD_BONE, "head")
        self.assertEqual(helpers._carrier_for_parent("|r|Main|FKHead_M", head=True,
                                                      follow=False), "head")

    def test_an_entry_is_not_a_camera_unless_said(self):
        from maya_poselib import helpers
        self.assertFalse(helpers.Entry("weapon_r", "|w", "driver", "|s", None, None).camera)
        self.assertIsNone(helpers._carrier_for_parent("|r|Main|Camera_follow", head=False,
                                                       follow=True))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_helpers.CameraCarriers -v`
Expected: FAIL (`HEAD_BONE` missing).

- [ ] **Step 3: Implement**

```python
HEAD_BONE = "head"


def _carrier_for_parent(parent, head, follow):
    """The game bone carrying a camera control's parent rigidly, from what the parent is (pure
    half of `_camera_carrier`): FKHead_M carries `head`; a Camera_follow group none (it turns with
    Main but rides another node's position - read in the world)."""
    if follow:
        return None
    if head:
        return HEAD_BONE
    return None
```

In `_camera_carrier`, after the Main/Root branch and before `under_chest`:

```python
    if parents and cmds.attributeQuery(camera.FOLLOW_MARKER, node=parents[0], exists=True):
        return _carrier_for_parent(parents[0], head=False, follow=True)
    if parents and parents[0].split("|")[-1].split(":")[-1] == camera.HEAD:
        return _carrier_for_parent(parents[0], head=True, follow=False)
```

`_aim_of(driver)`: try the weapon's group first, then the camera's:

```python
def _aim_of(driver):
    """An `Aim` when `driver` (a weapon or the camera's control) stands in Aim Mode, else None."""
    try:
        from maya_scenesetup import cameraaim, weaponaim
    except ImportError:
        return None
    for module in (weaponaim, cameraaim):
        group = module.group_of(driver)
        if group is None:
            continue
        made = module.controllers(group)
        if "target" not in made or "up" not in made:
            return None
        aim_v, up_v, d_aim, d_up = module.stored_vectors(group)
        return Aim(made["target"], made["up"], aim_v, up_v, d_aim, d_up)
    return None
```

`Writer._prepare`: `aimed = _aim_of(weapon) if weapon else None` → `aimed = _aim_of(driver)`.

`Entry` (line 60) gets a trailing field: `Entry = namedtuple("Entry", "leaf path mode driver K carrier aim camera")` with `Entry.__new__.__defaults__ = (None, False)`; `_prepare` passes `camera=not weapon` in its `Entry(...)` at line ~315.

The `aimed` write: a camera's controllers repeat the control's parent, so carry them as the control's carrier does; a weapon's controllers stand under Main / the chest, not its hand, so they keep the old branch. Replace the 1P-only branch with:

```python
                    ctrl_parent = _parent_world(ctrl)
                    if entry.camera and entry.carrier is not None and entry.carrier in wanted:
                        ctrl_parent = carried_parent(ctrl_parent,
                                                     _world(self.bones[entry.carrier]["path"]),
                                                     wanted[entry.carrier])
                    elif CHEST_BONE in self.bones and CHEST_BONE in wanted and under_chest(ctrl):
                        ctrl_parent = carried_parent(ctrl_parent,
                                                     _world(self.bones[CHEST_BONE]["path"]),
                                                     wanted[CHEST_BONE])
```

`scene._kind`: extend the CAMERA test:

```python
    from maya_scenesetup import armor, bonedrive, camera, cameraaim, weaponaim, weaponspace
    if cameraaim.is_controller(path) or any(
            cmds.attributeQuery(marker, node=path, exists=True)
            for marker in (camera.MARKER, camera.CONTROL_MARKER, camera.FOLLOW_MARKER)):
        return CAMERA
```

- [ ] **Step 4: Run tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_helpers tests.test_poselib_scene -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Paths: `SkeldarAnim/maya_poselib/helpers.py SkeldarAnim/maya_poselib/scene.py tests/test_poselib_helpers.py`. Message: `feat(poselib): a camera on Head, following a position, or in Aim Mode`.

---

### Task 7: Scene proof, regressions, install, notes

**Files:**
- Create: `docs/superpowers/plans/verify_camera_tab.py`
- Modify: `CLAUDE.md` (a new section after "Aim Mode: a broken aim is cleared, not refused")

- [ ] **Step 1: Write `verify_camera_tab.py`**

Start from `verify_camera_control.py`'s scaffold (the mayapy standalone init, `PLUGIN` insertion, `say` / gate helpers, Manny_Rig load and a camera keyed on 0/10/20 by moving and turning `camera_root`'s source before Camera Setup). Gates, each `gate(name, ok, detail)`:

1. `parents` - for each of `Main, Head, Head+position, Root+position, Chest(needs 1P: run firstperson setup first)+position, World, Main`: `camera.set_parent(bone, choice, position)`; the camera's world matrix on every frame 0..20 equals the recorded one to 1e-4 (translation cm, rotation deg via `aimcore.turn_between`).
2. `follow` - with Head (position): `Camera_follow` exists under Main with one `pointConstraint`; on every frame the control's world rotation equals Main's world rotation times the control's local (1e-4); after switching to World the follow group is gone.
3. `aim enter` - `cameraaim.enter(control)`: on keys 0/10/20 the camera's world matrix equals the recorded one to 1e-6; the two controllers' translate keys are exactly {0, 10, 20}; `cmds.undo()` once restores the control's rotate curves.
4. `aim leave` - `cameraaim.leave(control)`: every frame 0..20 within 1e-4 of what Aim Mode showed; no `skeldarCameraAim` group left.
5. `aim + parent` - Aim Mode, then `set_parent(bone, "Head", True)`: still aimed, the aim group under `Camera_follow`, the camera on every key where it was.
6. `chest gone` - 1P Setup, `set_parent(bone, "Chest", True)`, bake the chest off (`knots` Bake on `Chest_1P_ctrl` as `verify_1p_setup.py` does): the control back under Main, no follow group, motion kept to 1e-4.
7. `pose card` - camera on Head, a whole-body card captured at frame 10 and applied at frame 15 (`capture` / `apply` as in `verify_camera_weapon_bones.py`): `camera_root` on the card's place to 1e-4.
8. `undo` - each press of 1 and 3 undone by one `cmds.undo()`.

End with `say("%d/%d" % (passed, total))`.

- [ ] **Step 2: Run it**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_camera_tab.py $env:TEMP\camtab.txt`
Expected: `N/N` with every gate PASS. A failing gate is a bug in Tasks 1-6: fix it there (with a unit test when the cause is pure), not in the script.

- [ ] **Step 3: Re-run the regressions**

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_weapon_aim_mode.py $env:TEMP\r1.txt
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_camera_control.py $env:TEMP\r2.txt
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_1p_setup.py $env:TEMP\r3.txt
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_camera_weapon_bones.py $env:TEMP\r4.txt
```
(pass the same `<clip> [rig]` arguments their docstrings name). Expected: 21/21, 29/29, 30/30, 24/24. Then the whole unit suite: 0 failures.

- [ ] **Step 4: CLAUDE.md section**

`## Connections: a Camera tab - parents, Position only, Aim Mode (2026-10-28)`: the animator's words, what was asked (fixed list + Head; rotation relative to Main), the modules (`aimcore`, `cameraaim`, `camera.set_parent` follow group, `knots` release), the Pose Library carriers, the proof numbers from Steps 2-3, and "not seen in a GUI Maya" unless the animator checked it over port 7001.

- [ ] **Step 5: Commit**

Paths: `docs/superpowers/plans/verify_camera_tab.py CLAUDE.md`. Message: `test(connections): the Camera tab proved in mayapy; the notes`.

- [ ] **Step 6: Install into the animator's Maya copy (only on the animator's OK)**

The shelf runs `Documents/maya/scripts/SkeldarAnim`, not the repo. Ask before `install.install(quiet=True)` or pushing (a push to `main` touching the plugin cuts a release for colleagues).

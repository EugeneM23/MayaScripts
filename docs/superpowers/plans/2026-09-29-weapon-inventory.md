# Weapon Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two weapons per character (one per hand), a weapon lying on the floor that its hand's bone follows, and a Diablo-style inventory window whose weapons are dragged onto a hand or the floor in the viewport.

**Architecture:** Three layers, each proven before the next. Layer 1 generalises the one-weapon code (Weapons panel, Connections, `attach.detach`) to a chosen hand / a chosen weapon, with the left grip mirrored from the right through the rig's own sockets. Layer 2 adds `floor.py` (a weapon placed flat, the bone's track parked on it, the bone driven by it) and teaches `bonedrive.relink` to leave a world weapon where it is. Layer 3 adds pure layout/targeting modules and a Qt window that calls `equip.py`, the scene actions of the first two layers.

**Tech Stack:** Maya 2027 `maya.cmds` + `maya.api.OpenMaya`/`OpenMayaUI`, PySide6 6.8.3 (through `maya_hubqt.qt()`), stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-29-weapon-inventory-design.md`.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` from the repo root; Qt tests with `$env:QT_QPA_PLATFORM = 'offscreen'`. Never `python`, never pytest.
- Every new `SkeldarAnim/maya_*.py` is a payload row in `install._PAYLOAD` (a test pins it).
- A new tool is a hub section or lives inside one — no shelf button, no drawn shelf icon.
- Every cmds callback goes through the module's `_run` (failures on the status line).
- Identity by attribute/UUID, never by name; long paths; autoKey off around scripted writes (trap 14); one undo chunk per press.
- Python source is written with Write/Edit, never a PowerShell here-string (trap 101).
- Stylesheet/QPainter pixels are physical: every logical px × `mayaDpiSetting -q -realScaleValue` (trap 98).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; commit via `git commit -F` from a file or a Bash heredoc.

## File Structure

| File | Responsibility |
|---|---|
| `SkeldarAnim/maya_scenesetup/catalog.py` (modify) | `side_bone(bone, side)` |
| `SkeldarAnim/maya_scenesetup/bonedrive.py` (modify) | `mirror_grip`; `drive_socket` (from connections); park / unpark / drop_park; `relink` world branch |
| `SkeldarAnim/maya_scenesetup/grips.py` (create) | grip memory per weapon and hand (optionVars), the left default mirrored |
| `SkeldarAnim/maya_scenesetup/attach.py` (modify) | `import_weapon` split out; `mayaWeaponSource`; `detach` takes a world weapon, unparks |
| `SkeldarAnim/maya_scenesetup/window.py` (modify) | `Hand [Right|Left]`; per-hand grip; `linked` = followers; Inventory button |
| `SkeldarAnim/maya_scenesetup/connections.py` (modify) | `weapons_of`, chosen weapon, `blocked`, per-weapon scheme/driven side, chooser row |
| `SkeldarAnim/maya_scenesetup/floor.py` (create) | `lying_pose` (pure), `drop` |
| `SkeldarAnim/maya_scenesetup/equip.py` (create) | inventory actions: holdings, to_hand, to_floor, take_off, moves; `floor_side` (pure) |
| `SkeldarAnim/maya_scenesetup/droptarget.py` (create) | `choose` (pure) and the viewport snapshot/projection |
| `SkeldarAnim/maya_invlook.py` (create) | stdlib: palette, cells, packing, layout rects, hit tests |
| `SkeldarAnim/maya_inventory.py` (create) | the Qt window, the drag, the ghost, the scriptJob |
| `SkeldarAnim/maya_hubicons.py` (modify) | `backpack` icon |
| `SkeldarAnim/maya_hotkeys.py` (modify) | `window.inventory` row |
| `SkeldarAnim/install.py` (modify) | payload rows |
| `SkeldarAnim/assets/weapon_icons/` (create) | `<key>.png` + `weapon_icons.json` |
| `docs/superpowers/plans/make_weapon_icons.py` (create) | renders the icons in mayapy |
| `docs/superpowers/plans/verify_inventory.py` (create) | standalone proof |
| `docs/superpowers/plans/verify_inventory_live.py` (create) | disposable-Maya proof: Connections with two weapons, drop_at |
| tests: `test_scenesetup_hands.py`, `test_scenesetup_floor.py`, `test_scenesetup_equip.py`, `test_scenesetup_droptarget.py`, `test_invlook.py`, `test_inventory.py` (create); `test_scenesetup_connections.py`, `test_scenesetup_attach.py`, `test_scenesetup_bonedrive.py` (modify) | |

---

### Task 1: `side_bone` and `mirror_grip` (pure)

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py` (after `by_key`)
- Modify: `SkeldarAnim/maya_scenesetup/bonedrive.py` (pure section)
- Test: `tests/test_scenesetup_hands.py` (create)

**Interfaces:**
- Produces: `catalog.side_bone(bone: str, side: "R"|"L") -> str`; `catalog.SIDES = ("R", "L")`;
  `bonedrive.mirror_grip(rotate, translate, frame_rotate, socket_r16, socket_l16) -> (rotate3, translate3)`;
  `bonedrive.MODEL_MIRROR`, `bonedrive.BEHAVIOUR_MIRROR` (16-tuples).

- [ ] **Step 1: Write the failing tests**

```python
"""Two hands (2026-09-29): which bone a hand drives, and the left grip as the
mirror of the right through the rig's own sockets.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import math
import random
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive
from maya_scenesetup import catalog

MX = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
MZ = om.MMatrix(bonedrive.MODEL_MIRROR)
F = om.MMatrix(bonedrive.BEHAVIOUR_MIRROR)


def m(rotate, translate):
    return om.MMatrix(bonedrive.matrix_of(rotate, translate))


def close(a, b, tol=1e-9):
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


class SideBone(unittest.TestCase):

    def test_the_right_hand_keeps_the_rows_bone(self):
        self.assertEqual(catalog.side_bone("weapon_r", "R"), "weapon_r")

    def test_the_left_hand_takes_the_twin(self):
        self.assertEqual(catalog.side_bone("weapon_r", "L"), "weapon_l")

    def test_a_left_row_answers_its_right_twin(self):
        self.assertEqual(catalog.side_bone("weapon_l", "R"), "weapon_r")

    def test_a_bone_without_a_side_is_its_own_twin(self):
        self.assertEqual(catalog.side_bone("prop", "L"), "prop")

    def test_the_sides(self):
        self.assertEqual(catalog.SIDES, ("R", "L"))


class MirrorGrip(unittest.TestCase):
    """G_l . Fr . B_l == Mz . G_r . Fr . B_r . Mx for behaviour-mirrored
    hands, whatever the sockets are."""

    def _world(self, grip, frame, socket, hand):
        return grip * frame * socket * hand

    def _check(self, rotate, translate, frame_rotate, s_r, s_l):
        hand_r = m((-67.77, 1.47, 1.85), (-47.77, 104.47, 15.70))
        hand_l = F * hand_r * MX
        left = bonedrive.mirror_grip(rotate, translate, frame_rotate,
                                     tuple(s_r), tuple(s_l))
        fr = m(frame_rotate, (0, 0, 0))
        w_r = self._world(m(rotate, translate), fr, s_r, hand_r)
        w_l = self._world(m(*left), fr, s_l, hand_l)
        self.assertTrue(close(w_l, MZ * w_r * MX, 1e-7),
                        (list(w_l), list(MZ * w_r * MX)))
        return left

    def test_mannys_sockets(self):
        """weapon_r at (-6.62, -1.69, 0.98) turned 1.6 deg, weapon_l at
        (0, 3.4, 0) - measured on Manny_Rig.ma 2026-09-29."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        self._check((0, 0, 0), (0, 0, 0), (0, 0, 0), s_r, s_l)
        self._check((10, -20, 35), (1.5, -2.0, 4.0), (0, 45, 0), s_r, s_l)

    def test_the_zero_right_grip_turns_the_left_blade_round_on_manny(self):
        """At zero grip the left blade points backwards (-0.9993 measured):
        the mirror grip is not the identity there."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        rotate, _ = bonedrive.mirror_grip((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                          tuple(s_r), tuple(s_l))
        turned = om.MEulerRotation(*[math.radians(v) for v in rotate])
        self.assertGreater(math.degrees(turned.asQuaternion().asAxisAngle()[1]),
                           170.0)

    def test_a_geometric_mirror_pair_needs_no_correction(self):
        """The Creep's weapon_l is the geometric mirror of weapon_r (+1.0000
        measured): zero right grip -> zero left grip."""
        s_r = m((92.87, -14.60, -21.18), (-9.80, -4.61, 1.01))
        s_l = MZ * s_r * F
        rotate, translate = self._check((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                        s_r, s_l)
        self.assertTrue(close(rotate, (0, 0, 0), 1e-6), rotate)
        self.assertTrue(close(translate, (0, 0, 0), 1e-6), translate)

    def test_random_grips_frames_and_sockets(self):
        rng = random.Random(7)
        for _ in range(20):
            r = lambda: tuple(rng.uniform(-180, 180) for _ in range(3))
            t = lambda: tuple(rng.uniform(-20, 20) for _ in range(3))
            self._check(r(), t(), r(), m(r(), t()), m(r(), t()))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_hands -v`
Expected: FAIL — `AttributeError: module 'maya_scenesetup.catalog' has no attribute 'side_bone'`.

- [ ] **Step 3: Implement**

`catalog.py`, after `by_key`:

```python
SIDES = ("R", "L")


def side_bone(bone, side):
    """The drive bone `side`'s hand uses for a row whose bone is `bone`. Pure.

    The rows name the right hand's bone (`weapon_r`); the left hand takes its
    twin (2026-09-29, two weapons per character): a trailing `_r` becomes `_l`
    and back. A bone with no side suffix is its own twin.
    """
    if side == "L" and bone.endswith("_r"):
        return bone[:-2] + "_l"
    if side == "R" and bone.endswith("_l"):
        return bone[:-2] + "_r"
    return bone
```

`bonedrive.py`, after `grip_between`:

```python
# The model's thickness mirror (every catalog weapon lies with its thickness
# on Z) and the hands' behaviour mirror (UE's left hand: the three axes of
# the mirrored right hand negated - 0.0003 cm on Manny, 0.045 on the Creep).
MODEL_MIRROR = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0)
BEHAVIOUR_MIRROR = (-1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0,
                    0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _as_grip(product):
    frame = om.MTransformationMatrix(product)
    euler = frame.rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    shift = frame.translation(om.MSpace.kTransform)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (shift.x, shift.y, shift.z))


def mirror_grip(rotate, translate, frame_rotate, socket_r16, socket_l16):
    """The left hand's grip standing a weapon as the world mirror of where the
    right grip (`rotate`, `translate`) stands it. Pure.

    Wanted: G_l . Fr . B_l = Mz . G_r . Fr . B_r . Mx, with B = S . H (the
    weapon bone's LOCAL matrix in its hand, the hand) and H_l = F . H_r . Mx.
    So G_l = Mz . G_r . Fr . S_r . F . S_l^-1 . Fr^-1 - the sockets decide it,
    which is why Manny (weapon_l 6.9 cm off the mirror of weapon_r, the blade
    backwards at zero grip) and the Creep (a geometric pair, zero is right)
    come out differently from the same numbers. Row vectors, as everywhere.
    """
    frame = om.MMatrix(matrix_of(frame_rotate, (0.0, 0.0, 0.0)))
    product = (om.MMatrix(MODEL_MIRROR) * om.MMatrix(matrix_of(rotate, translate))
               * frame * om.MMatrix(socket_r16) * om.MMatrix(BEHAVIOUR_MIRROR)
               * om.MMatrix(socket_l16).inverse() * frame.inverse())
    return _as_grip(product)
```

- [ ] **Step 4: Run to verify it passes**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_hands -v`
Expected: all PASS.

- [ ] **Step 5: Commit** — `feat(weapons): the left hand's bone and its mirrored grip, from the rig's own sockets`

---

### Task 2: grip memory per hand (`grips.py`) and `attach` for two hands

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/grips.py`
- Modify: `SkeldarAnim/maya_scenesetup/attach.py` (`import_weapon`, `SOURCE`, `detach`)
- Modify: `SkeldarAnim/maya_scenesetup/window.py` (policy helpers delegate to grips)
- Modify: `tests/test_scenesetup_attach.py` (FakeBonedrive gains `driving_weapon`, `is_parked`, `unpark`)
- Test: `tests/test_scenesetup_hands.py` (append)

**Interfaces:**
- Consumes: `catalog.side_bone`, `bonedrive.mirror_grip`.
- Produces:
  - `grips.optionvar_name(key, side="R")`, `grips.pack(rotate, translate)`, `grips.unpack(values)`,
    `grips.stored(key, side="R") -> (r, t) | None`, `grips.remember(key, side, r, t)`,
    `grips.sockets(root, bone="weapon_r") -> (s_r16, s_l16) | None`,
    `grips.for_hand(entry, side, root) -> (r, t)`, `grips.ZERO`.
  - `attach.SOURCE = "mayaWeaponSource"`; `attach.import_weapon(entry, parent=None, rgb=None) -> (weapon, note)`;
    `attach.detach(hand, bone)` also takes off a weapon out in world driving `bone` (unparking it when parked).
  - `bonedrive.is_parked(weapon)`, `bonedrive.unpark(weapon, bone)` are STUBS here returning False (Task 5 fills them) so attach can call them now.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_scenesetup_hands.py`)

```python
from maya_scenesetup import grips


class FakeVars(object):
    """optionVar as Maya answers it."""

    def __init__(self, stored=None):
        self.vars = dict(stored or {})

    def optionVar(self, **kwargs):
        if "exists" in kwargs:
            return kwargs["exists"] in self.vars
        if "query" in kwargs:
            return self.vars.get(kwargs["query"])
        if "clearArray" in kwargs:
            self.vars[kwargs["clearArray"]] = []
        if "floatValueAppend" in kwargs:
            name, value = kwargs["floatValueAppend"]
            self.vars.setdefault(name, []).append(value)


class Entry(object):
    key = "LongSword_02"
    bone = "weapon_r"
    frame = (0.0, 0.0, 0.0)


class GripMemory(unittest.TestCase):

    def setUp(self):
        self.real = grips.cmds
        self.addCleanup(setattr, grips, "cmds", self.real)

    def test_the_right_hand_keeps_its_old_name(self):
        self.assertEqual(grips.optionvar_name("LongSword_02"),
                         "mayaSceneSetup_offset_LongSword_02")
        self.assertEqual(grips.optionvar_name("LongSword_02", "R"),
                         "mayaSceneSetup_offset_LongSword_02")

    def test_the_left_hand_has_its_own(self):
        self.assertEqual(grips.optionvar_name("LongSword_02", "L"),
                         "mayaSceneSetup_offset_LongSword_02_L")

    def test_nothing_stored_is_none_not_zeros(self):
        grips.cmds = FakeVars()
        self.assertIsNone(grips.stored("LongSword_02", "L"))

    def test_the_legacy_name_serves_the_right_hand_only(self):
        grips.cmds = FakeVars({"mayaWeapons_offset_LongSword_02":
                               [0, 90, 0, 1, 2, 3]})
        self.assertEqual(grips.stored("LongSword_02", "R"),
                         ((0.0, 90.0, 0.0), (1.0, 2.0, 3.0)))
        self.assertIsNone(grips.stored("LongSword_02", "L"))

    def test_remember_then_stored(self):
        grips.cmds = FakeVars()
        grips.remember("LongSword_02", "L", (1, 2, 3), (4, 5, 6))
        self.assertEqual(grips.stored("LongSword_02", "L"),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_a_dialled_left_grip_wins(self):
        grips.cmds = FakeVars({"mayaSceneSetup_offset_LongSword_02_L":
                               [1, 2, 3, 4, 5, 6]})
        grips.sockets = lambda root, bone="weapon_r": self.fail("no mirror")
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_an_undialled_left_grip_is_the_right_ones_mirror(self):
        grips.cmds = FakeVars({"mayaSceneSetup_offset_LongSword_02":
                               [0, 0, 0, 1, 0, 0]})
        seen = []
        real_sockets, real_mirror = grips.sockets, grips.bonedrive.mirror_grip
        self.addCleanup(setattr, grips, "sockets", real_sockets)
        self.addCleanup(setattr, grips.bonedrive, "mirror_grip", real_mirror)
        grips.sockets = lambda root, bone="weapon_r": ("SR", "SL")
        grips.bonedrive.mirror_grip = lambda *a: seen.append(a) or ((0, 0, 180), (-1, 0, 0))
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"),
                         ((0, 0, 180), (-1, 0, 0)))
        self.assertEqual(seen, [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                                 (0.0, 0.0, 0.0), "SR", "SL")])

    def test_no_sockets_means_zeros(self):
        grips.cmds = FakeVars()
        real = grips.sockets
        self.addCleanup(setattr, grips, "sockets", real)
        grips.sockets = lambda root, bone="weapon_r": None
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"), grips.ZERO)

    def test_the_window_delegates(self):
        from maya_scenesetup import window
        self.assertEqual(window.optionvar_name("X"), grips.optionvar_name("X"))
        self.assertIs(window.pack_offsets, grips.pack)
        self.assertIs(window.unpack_offsets, grips.unpack)
```

And in `tests/test_scenesetup_attach.py`, `FakeBonedrive` gains:

```python
    def driving_weapon(self, bone):
        return getattr(self, "world", None)

    def is_parked(self, weapon):
        return getattr(self, "parked", False)

    def unpark(self, weapon, bone):
        self.log.append(("unpark", weapon, bone))
        return True
```

and `Detach` gains:

```python
    def test_a_weapon_out_in_world_comes_off_too(self):
        """2026-09-29: a weapon on the floor (or lifted in Connections) drives
        the bone from world; Remove and a replacing Add take it off."""
        fake = FakeCmds()
        log = self._wire(fake)
        attach.bonedrive.world = "|SpearMesh"
        removed = attach.detach(HAND, BONE)
        self.assertEqual(removed, "|SpearMesh")
        self.assertEqual(log, [("unlink", BONE), ("delete", "|SpearMesh")])

    def test_a_parked_weapon_gives_the_bone_its_track_back(self):
        fake = FakeCmds()
        log = self._wire(fake)
        attach.bonedrive.world = "|SpearMesh"
        attach.bonedrive.parked = True
        attach.detach(HAND, BONE)
        self.assertEqual(log, [("unpark", "|SpearMesh", BONE),
                               ("delete", "|SpearMesh")])
```

and `AttachFlow` gains:

```python
    def test_the_source_file_is_recorded(self):
        """So the inventory can put the same weapon into the other hand."""
        fake = self._wire(frames=0)
        attach.attach(self.Entry(), HAND, BONE)
        self.assertIn(SPACE + "|sword." + attach.SOURCE, fake.attrs)
        self.assertEqual(fake.attrs[SPACE + "|sword." + attach.SOURCE],
                         "C:/x/sword.fbx")
```

- [ ] **Step 2: Run to verify they fail** (`tests.test_scenesetup_hands`, `tests.test_scenesetup_attach`): no module `grips`, no `SOURCE`.

- [ ] **Step 3: Implement**

`grips.py`:

```python
"""The grip a hand gives a weapon, remembered per weapon AND per hand.

Bone-relative, as since 2026-08-25: zeros mean exactly on the drive bone. The
right hand keeps the names it always had (`mayaSceneSetup_offset_<key>`, the
pre-rename `mayaWeapons_offset_<key>` read second); the left hand (2026-09-29,
two weapons per character) has `..._L`. A left grip nobody has dialled is the
MIRROR of the right one through the rig's own sockets (`bonedrive.mirror_grip`
- on Manny zero grip turns the left blade backwards, on the Creep it is
already right), recomputed each time so it follows the right grip until the
left is dialled.

Window policy the Weapons panel and the inventory share, so both put the same
weapon into the same hand the same way.
"""

import maya.cmds as cmds

from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import skeleton

_OPTIONVAR = "mayaSceneSetup_offset_{0}"
_LEGACY_OPTIONVAR = "mayaWeapons_offset_{0}"
ZERO = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def optionvar_name(key, side="R"):
    name = _OPTIONVAR.format(key)
    return name if side == "R" else name + "_L"


def pack(rotate, translate):
    return [float(value) for value in tuple(rotate) + tuple(translate)]


def unpack(values):
    """Six stored numbers -> (rotate, translate). Anything else -> zeros.

    Maya answers a missing optionVar with 0 or an empty list, and a stored
    value of the wrong length can only come from an older version of this
    tool; half a grip is worse than none.
    """
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return ZERO
    if len(numbers) != 6:
        return ZERO
    return tuple(numbers[:3]), tuple(numbers[3:])


def stored(key, side="R"):
    """The remembered grip, or None when nothing is (zeros are a real grip)."""
    names = [optionvar_name(key, side)]
    if side == "R":
        names.append(_LEGACY_OPTIONVAR.format(key))
    for name in names:
        if cmds.optionVar(exists=name):
            return unpack(cmds.optionVar(query=name))
    return None


def remember(key, side, rotate, translate):
    name = optionvar_name(key, side)
    cmds.optionVar(clearArray=name)
    for value in pack(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def sockets(root, bone="weapon_r"):
    """The two drive bones' LOCAL matrices in their hands, or None."""
    paths = [skeleton.resolve_bone(root, catalog.side_bone(bone, side))
             for side in catalog.SIDES]
    if not all(paths):
        return None
    return tuple(tuple(cmds.xform(path, query=True, matrix=True,
                                  objectSpace=True)) for path in paths)


def for_hand(entry, side, root):
    """The grip `side`'s hand gives `entry`: dialled, else (left) mirrored."""
    got = stored(entry.key, side)
    if got is not None:
        return got
    right = stored(entry.key, "R") or ZERO
    if side == "R":
        return right
    pair = sockets(root, entry.bone) if root else None
    if not pair:
        return ZERO
    return bonedrive.mirror_grip(right[0], right[1],
                                 getattr(entry, "frame", (0.0, 0.0, 0.0)),
                                 pair[0], pair[1])
```

`window.py`: replace `optionvar_name`, `pack_offsets`, `unpack_offsets`, `_OPTIONVAR`, `_LEGACY_OPTIONVAR` bodies with delegation:

```python
from maya_scenesetup import grips

optionvar_name = grips.optionvar_name
pack_offsets = grips.pack
unpack_offsets = grips.unpack
```

`attach.py`: add `SOURCE = "mayaWeaponSource"`; split `attach` into `import_weapon` + the hang:

```python
def import_weapon(entry, parent=None, rgb=None):
    """`entry`'s model in the scene as OUR weapon: imported, one mesh made the
    weapon (else a group of ours), under `parent` (a weapon space) or at world
    level, marked with its key and its source file, seated, dressed (colour or
    texture) and its frame stored. Returns (weapon, note). The caller holds
    the undo chunk and autoKey."""
    roots = import_model(entry.path)
    if not roots:
        raise RuntimeError("nothing came out of " + entry.path)
    meshes = mesh_transforms(roots)
    note = ""
    if len(meshes) == 1:
        weapon = _home(meshes[0], parent)
        leftovers = [path for path in cmds.ls(roots, long=True) or []
                     if cmds.objExists(path) and path != weapon]
        if leftovers:
            cmds.delete(leftovers)
    else:
        group = cmds.group(empty=True, world=True, name=group_name(entry.key))
        cmds.parent(roots, group)
        weapon = _home(group, parent)
        note = "{0} mesh(es) in the file - kept in a group".format(len(meshes))
    cmds.addAttr(weapon, longName=MARKER, dataType="string")
    cmds.setAttr(weapon + "." + MARKER, entry.key, type="string")
    cmds.addAttr(weapon, longName=SOURCE, dataType="string")
    cmds.setAttr(weapon + "." + SOURCE, entry.path, type="string")
    seat(weapon, entry.scale)
    texture = getattr(entry, "texture", "")
    if texture:
        colouring.paint_texture_nodes([weapon], texture, entry.key)
    else:
        if rgb is None:
            rgb = colouring.free_colour().rgb
        colouring.paint_nodes([weapon], rgb, entry.key)
    bonedrive.store_frame(weapon, getattr(entry, "frame", (0.0, 0.0, 0.0)))
    return weapon, note


def _home(node, parent):
    """`node` under `parent`, or at world level; its long path."""
    if parent:
        return cmds.ls(cmds.parent(node, parent)[0], long=True)[0]
    if cmds.listRelatives(node, parent=True):
        node = cmds.parent(node, world=True)[0]
    return cmds.ls(node, long=True)[0]
```

and `attach()` keeps its docstring and becomes:

```python
    cmds.undoInfo(openChunk=True)
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        detach(parent_bone_path, drive_bone)
        home = weaponspace.ensure_space(parent_bone_path)
        weapon, note = import_weapon(entry, home, rgb)
        if rotate is not None and translate is not None:
            bonedrive.apply_grip(weapon, drive_bone, rotate, translate)
        else:
            bonedrive.place_at_grip(weapon, drive_bone, (0.0, 0.0, 0.0),
                                    (0.0, 0.0, 0.0))
        frames = bonedrive.link(weapon, drive_bone)
        if frames:
            moved = ("{0} frame(s) moved from the bone onto the weapon"
                     .format(frames))
            note = note + " - " + moved if note else moved
        return weapon, note
    finally:
        cmds.autoKeyframe(state=autokey)
        cmds.undoInfo(closeChunk=True)
```

(The ensure_space call moves BEFORE the import — the test that pins "space before parent" still holds.)

`detach`:

```python
def detach(parent_bone_path, drive_bone):
    """Take off the weapon this hand holds or this bone follows, giving the
    bone its animation back.

    Unlink FIRST (the bone's motion lives on the weapon while the link stands).
    Looked for in the hand's space, under the bone (a file from before
    2026-09-24), and - since 2026-09-29 - as the node driving the bone from
    world (a weapon on the floor, or lifted in Connections): a weapon that
    PARKED the bone's own track (a floor drop) hands it back verbatim instead
    of a bake. The caller refuses a weapon hands ride before calling this.
    """
    weapon = find_attached(parent_bone_path) or find_attached(drive_bone)
    held = bool(weapon)
    if not weapon:
        weapon = bonedrive.driving_weapon(drive_bone)
        if not weapon:
            return None
    space = weaponspace.space_of(parent_bone_path) if held else None
    if not held and bonedrive.is_parked(weapon):
        bonedrive.unpark(weapon, drive_bone)
    else:
        bonedrive.unlink(drive_bone)
    cmds.delete(weapon)
    if space:
        weaponspace.prune(space)
    return weapon
```

`bonedrive.py` stubs (Task 5 replaces them):

```python
def is_parked(weapon):
    return False


def unpark(weapon, bone):
    return False
```

- [ ] **Step 4: Run** `tests.test_scenesetup_hands tests.test_scenesetup_attach tests.test_scenesetup_window` — PASS.
- [ ] **Step 5: Commit** — `feat(weapons): the grip remembered per hand, the left one mirrored; detach takes a weapon out in world`

---

### Task 3: the Weapons section's `Hand [Right | Left]`

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/window.py`
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` (`followers_of`, `following`)
- Test: `tests/test_scenesetup_hands.py` (append)

**Interfaces:**
- Consumes: `grips.for_hand/remember`, `catalog.side_bone`.
- Produces: `window._HAND = "mayaSceneSetupHand"`, segment names `window.hand_segment(side)`, `window.side()` (the chosen side), `window.hand_follows_message(side, label)`;
  `connections.followers_of(weapon) -> [side]` (by the proxies inside it), `connections.following(rig, side) -> weapon | None`.

- [ ] **Step 1: Failing tests**

```python
from tests.uifakes import FakeUiCmds


class HandCmds(FakeUiCmds):
    """The UI fake plus radio collections (as in the Connections tests)."""

    def __init__(self):
        FakeUiCmds.__init__(self)
        self.selected, self.owner, self.on, self._current = {}, {}, {}, None

    def iconTextRadioCollection(self, name=None, **kwargs):
        if kwargs.get("query"):
            return self.selected.get(name)
        self.selected[name] = None
        self._current = name
        return name

    def iconTextRadioButton(self, name=None, **kwargs):
        if kwargs.get("exists"):
            return name in self.owner
        if kwargs.get("edit"):
            if kwargs.get("select"):
                self.selected[self.owner[name]] = name
            return name
        self.owner[name] = self._current
        self.on[name] = kwargs.get("onCommand")
        if kwargs.get("select"):
            self.selected[self._current] = name
        self.children.append(name)
        self.calls.append(("iconTextRadioButton", (name,), kwargs))
        return name


class HandRow(unittest.TestCase):

    def setUp(self):
        from maya_scenesetup import window
        self.window = window
        self.real = window.cmds
        self.fake = HandCmds()
        window.cmds = self.fake
        self.addCleanup(setattr, window, "cmds", self.real)

    def test_the_segments_are_right_and_left(self):
        self.window._hand_row()
        labels = [c[2]["label"] for c in self.fake.calls
                  if c[0] == "iconTextRadioButton"]
        self.assertEqual(labels, ["Right", "Left"])

    def test_the_right_hand_is_the_default(self):
        self.window._hand_row()
        self.assertEqual(self.window.side(), "R")

    def test_a_remembered_left_hand_opens_on_left(self):
        self.fake.optionvars[self.window._HAND_OPTIONVAR] = "L"
        self.window._hand_row()
        self.assertEqual(self.window.side(), "L")

    def test_picking_a_hand_remembers_it(self):
        self.window._hand_row()
        self.fake.selected[self.window._HAND] = self.window.hand_segment("L")
        refreshed = []
        real = self.window.refresh
        self.window.refresh = lambda: refreshed.append(1)
        self.addCleanup(setattr, self.window, "refresh", real)
        self.fake.on[self.window.hand_segment("L")]()
        self.assertEqual(self.fake.optionvars[self.window._HAND_OPTIONVAR], "L")
        self.assertEqual(refreshed, [1])

    def test_the_left_hand_asks_for_weapon_l(self):
        asked = []
        self.fake.selected[self.window._HAND] = self.window.hand_segment("L")
        real_resolve, real_root = (self.window.skeleton.resolve_bone,
                                   self.window._bound_root)
        self.window.skeleton.resolve_bone = lambda root, name: asked.append(name)
        self.window._bound_root = lambda: "|root"
        self.addCleanup(setattr, self.window.skeleton, "resolve_bone", real_resolve)
        self.addCleanup(setattr, self.window, "_bound_root", real_root)
        self.window._attached(catalog.by_key("LongSword_02"))
        self.assertEqual(asked, ["weapon_l"])

    def test_the_follow_refusal_names_the_hand_and_the_weapon(self):
        text = self.window.hand_follows_message("L", "Long Sword 02")
        self.assertIn("left hand follows the Long Sword 02", text)
        self.assertIn("Connections", text)
```

- [ ] **Step 2: Run — FAIL** (`_hand_row` missing).

- [ ] **Step 3: Implement** in `window.py`:

```python
_HAND = "mayaSceneSetupHand"              # the hand the presses act on (2026-09-29)
_HAND_OPTIONVAR = "mayaSceneSetup_hand"
HAND_LABEL = {"R": "Right", "L": "Left"}
SIDE_LABEL = {"R": "right hand", "L": "left hand"}


def hand_segment(side):
    return "{0}_{1}".format(_HAND, side)


def hand_follows_message(side, label):
    return ("the {0} follows the {1} - release it in Connections first"
            .format(SIDE_LABEL[side], label))


def side():
    """The hand the Weapons presses act on: the segment picked, else "R"."""
    chosen = (cmds.iconTextRadioCollection(_HAND, query=True, select=True)
              or "").split("|")[-1]
    for key in catalog.SIDES:
        if chosen == hand_segment(key):
            return key
    return "R"


def _remembered_side():
    if cmds.optionVar(exists=_HAND_OPTIONVAR):
        value = cmds.optionVar(query=_HAND_OPTIONVAR)
        if value in catalog.SIDES:
            return value
    return "R"


def hand_changed(key):
    def go(*_args):
        cmds.optionVar(stringValue=(_HAND_OPTIONVAR, key))
        _run(refresh)
    return go


def _hand_row():
    """`Hand [Right | Left]`: which hand Add, Remove, the grip and Recolour
    act on (2026-09-29, two weapons per character)."""
    start = _remembered_side()
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(64, 120),
                   columnAttach=[(1, "left", 0), (2, "both", 4)])
    cmds.text(label="Hand", align="left")
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_HAND)
    for key in catalog.SIDES:
        hubstyle.mark(cmds.iconTextRadioButton(
            hand_segment(key), style="textOnly", label=HAND_LABEL[key],
            height=22, select=key == start,
            annotation="Add, Remove, the grip and Recolour act on the {0}"
                       .format(SIDE_LABEL[key]),
            onCommand=hand_changed(key)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")
```

`_attached(entry)`: `bone = skeleton.resolve_bone(root, catalog.side_bone(entry.bone, side()))`, and after the hand/bone lookups:

```python
    legacy = linking.linked_weapon()
    if legacy:
        return root, hand, bone, legacy, True
    world = bonedrive.driving_weapon(bone)
    if world:
        from maya_scenesetup import connections
        return root, hand, bone, world, bool(connections.followers_of(world))
    return root, hand, bone, None, False
```

`_locate` / `refresh` name the side's bone in their messages (`catalog.side_bone(entry.bone, side())`). `refresh` and `add_weapon` read the grip through `grips.for_hand(entry, side(), root)`; `offsets_changed` and `add_weapon` remember through `grips.remember(entry.key, side(), rotate, translate)`; `_remembered`/`_remember` are deleted. `add_weapon` refuses a following hand before anything:

```python
    rig = maya_rigs.rig_of(bone, maya_rigs.rigs())
    if rig is not None:
        from maya_scenesetup import connections
        rides = connections.following(rig, side())
        if rides:
            _status(hand_follows_message(side(), connections.weapon_label(rides)))
            return
```

`build_weapons_panel`: `_hand_row()` right after the dropdown row.

`connections.py`:

```python
def followers_of(weapon):
    """The sides whose hands ride `weapon`: its proxies (inside it, by attribute)."""
    out = []
    for node in cmds.listRelatives(weapon, allDescendents=True, type="transform",
                                   fullPath=True) or []:
        if cmds.attributeQuery(PROXY_MARKER, node=node, exists=True):
            side = cmds.getAttr(node + "." + PROXY_MARKER).split(":")[-1]
            if side in SIDES and side not in out:
                out.append(side)
    return out


def following(rig, side):
    """The weapon `side`'s IK hand rides, or None."""
    control = _control(rig, side)
    for con in our_constraints(control) if control else []:
        proxy = proxy_for(con)
        parent = (cmds.listRelatives(proxy, parent=True, fullPath=True) or [None])[0] if proxy else None
        while parent and not cmds.attributeQuery(attach.MARKER, node=parent, exists=True):
            parent = (cmds.listRelatives(parent, parent=True, fullPath=True) or [None])[0]
        if parent:
            return parent
    return None


def weapon_label(weapon):
    """The catalog label of a weapon node (its marker key), else its leaf."""
    key = cmds.getAttr(weapon + "." + attach.MARKER) if cmds.attributeQuery(
        attach.MARKER, node=weapon, exists=True) else ""
    entry = catalog.by_key(key) if key else None
    return entry.label if entry else weapon.split("|")[-1]
```

(`connections` gains `from maya_scenesetup import catalog`.)

- [ ] **Step 4: Run** `tests.test_scenesetup_hands tests.test_scenesetup_window tests.test_scenesetup_connections` — PASS.
- [ ] **Step 5: Commit** — `feat(weapons): Hand Right/Left in the Weapons section; a world weapon nothing rides is the hand's to replace`

---

### Task 4: Connections acts on a chosen weapon of two

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py`
- Modify: `tests/test_scenesetup_connections.py`

**Interfaces:**
- Consumes: `followers_of`, `following`, `weapon_label` (Task 3).
- Produces: `weapons_of(rig, bones=None) -> [path]`; `choose_weapon(weapons, selection, picked) -> path|None` (pure);
  `labels_for(pairs) -> [str]` (pure; pairs = [(label, side|None)]); `blocked(current, wanted, other, other_label, bone_taken=None) -> str` (pure);
  `read_scheme(rig, bones=None, weapon=None)` per weapon; `driven_side(rig, bones=None, weapon=None)`;
  `chosen_weapon(rig, bones=None)`; `apply(wanted, rig=None, weapon=None)`; `CHOOSER = "skeldarConnectionsWeapon"`, `chooser_segment(i)`.

- [ ] **Step 1: Failing tests** (append to `test_scenesetup_connections.py`)

```python
class TwoWeapons(unittest.TestCase):
    """2026-09-29: a sword in one hand, a dagger in the other. The section acts
    on one of them; a hand holds XOR follows across both."""

    A, B = "|g|WeaponSpaces|hand_r_weaponSpace|LongSwordMesh", "|g|WeaponSpaces|hand_l_weaponSpace|DaggerMesh"

    def test_the_selection_names_the_weapon(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], [self.B + "|handProxy_R"], None), self.B)

    def test_else_the_picked_one(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], [], self.B), self.B)

    def test_a_picked_weapon_that_went_is_forgotten(self):
        self.assertEqual(cx.choose_weapon([self.A], [], self.B), self.A)

    def test_else_the_first(self):
        self.assertEqual(cx.choose_weapon([self.A, self.B], ["|elsewhere"], None), self.A)
        self.assertIsNone(cx.choose_weapon([], [], None))

    def test_labels_of_one_key_carry_their_hand(self):
        self.assertEqual(cx.labels_for([("Long Sword 02", "R"), ("Long Sword 02", "L")]),
                         ["Long Sword 02 (R)", "Long Sword 02 (L)"])
        self.assertEqual(cx.labels_for([("Long Sword 02", "R"), ("Dagger 01", "L")]),
                         ["Long Sword 02", "Dagger 01"])

    def test_a_hand_the_other_weapon_hangs_in_takes_nothing(self):
        text = cx.blocked(scheme(right=H), scheme(left=H, right=H), scheme(left=H), "Dagger 01")
        self.assertEqual(text, "Hand_L holds the Dagger 01 - move it first")
        text = cx.blocked(scheme(right=H), scheme(left=F, right=H), scheme(left=H), "Dagger 01")
        self.assertEqual(text, "Hand_L holds the Dagger 01 - move it first")

    def test_a_hand_riding_the_other_weapon_takes_nothing(self):
        text = cx.blocked(scheme(right=H), scheme(left=F, right=H), scheme(left=F), "Dagger 01")
        self.assertEqual(text, "Hand_L follows the Dagger 01 - release it first")

    def test_a_bone_the_other_weapon_drives_from_world(self):
        text = cx.blocked(scheme(right=H), scheme(left=H), scheme(), "Dagger 01", bone_taken="L")
        self.assertEqual(text, "weapon_l is driven by the Dagger 01 (in world) - remove it or put it in a hand first")

    def test_what_already_stands_is_never_blocked(self):
        self.assertEqual(cx.blocked(scheme(right=H), scheme(right=H), scheme(left=H), "Dagger 01"), "")

    def test_the_free_hand_is_free(self):
        self.assertEqual(cx.blocked(scheme(right=H), scheme(right=F), scheme(left=H), "Dagger 01"), "")
```

Panel test updates: the chooser row is first — `labels_of("C")` would not exist as a `_ROWS` row; assert instead:

```python
    def test_the_chooser_row_has_two_segments(self):
        names = [n for n, _l in self.fake.segments[cx.CHOOSER]]
        self.assertEqual(names, [cx.chooser_segment(0), cx.chooser_segment(1)])
```

and `test_three_rows...` expects six texts (the chooser's label) and `test_the_segments_are_marked_for_the_skin` four segment rows.

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement** (connections.py):

```python
CHOOSER = "skeldarConnectionsWeapon"   # which of two weapons (2026-09-29)
_PICKED = {"uuid": None}               # the chooser's pick, by UUID


def chooser_segment(index):
    return "{0}_{1}".format(CHOOSER, index)


def choose_weapon(weapons, selection, picked):
    """The weapon the section acts on. Pure: the selection's (the weapon or
    anything under it - one of its proxies too), else the picked one while it
    is still a weapon of this rig, else the first."""
    for path in selection or []:
        for weapon in weapons:
            if path == weapon or path.startswith(weapon + "|"):
                return weapon
    if picked in weapons:
        return picked
    return weapons[0] if weapons else None


def labels_for(pairs):
    """[(label, side)] -> segment labels, a hand named where two share one. Pure."""
    labels = [label for label, _side in pairs]
    return [("%s (%s)" % (label, side) if labels.count(label) > 1 and side else label)
            for label, side in pairs]


def blocked(current, wanted, other, other_label, bone_taken=None):
    """Why `wanted` may not stand beside the other weapon's scheme, or "". Pure.

    A hand holds XOR follows across both weapons - a holding hand rides
    nothing, so no chain can loop - and a hand whose bone the other weapon,
    out in world, drives takes no weapon. Only what changes is checked."""
    for side in SIDES:
        mine = wanted.get(side)
        if not mine or mine == current.get(side):
            continue
        theirs = (other or {}).get(side)
        if theirs == HOLDS:
            return "%s holds the %s - move it first" % (ROW_LABEL[side], other_label)
        if theirs == FOLLOWS:
            return "%s follows the %s - release it first" % (ROW_LABEL[side], other_label)
        if mine == HOLDS and side == bone_taken:
            return ("%s is driven by the %s (in world) - remove it or put it in "
                    "a hand first" % (WEAPON_BONE[side], other_label))
    return ""


def _same(a, b):
    return bool(a and b) and cmds.ls(a, long=True) == cmds.ls(b, long=True)


def weapons_of(rig, bones=None):
    """Every weapon of the rig, right-hand related first: what drives a weapon
    bone, what hangs in a hand's space, what holds one of its proxies."""
    bones = bones or bones_of(rig)
    found = []

    def add(node):
        paths = cmds.ls(node, long=True) if node else []
        if paths and paths[0] not in found:
            found.append(paths[0])

    for side in ("R", "L"):
        hand, bone = bones[side]
        if bone:
            add(bonedrive.driving_weapon(bone))
        if hand:
            add(attach.find_attached(hand))
    for side in ("R", "L"):
        add(following(rig, side))
    return found


def chosen_weapon(rig, bones=None, weapons=None):
    weapons = weapons if weapons is not None else weapons_of(rig, bones)
    picked = cmds.ls(_PICKED["uuid"], long=True) if _PICKED["uuid"] else []
    return choose_weapon(weapons, cmds.ls(selection=True, long=True) or [],
                         picked[0] if picked else None)


def weapon_of(rig, bones=None):
    """The weapon the section acts on (kept for its callers)."""
    return chosen_weapon(rig, bones)
```

`driven_side(rig, bones=None, weapon=None)` compares `bonedrive.driving_weapon(bone)` with `weapon` via `_same` when a weapon is given. `read_scheme(rig, bones=None, weapon=None)` keeps its holder logic and marks followers only where `_same(following(rig, side), weapon)`. `apply(wanted, rig=None, weapon=None)`:

```python
    bones = bones_of(rig)
    weapons = weapons_of(rig, bones)
    weapon = weapon or chosen_weapon(rig, bones, weapons)
    if not weapon:
        return NO_WEAPON
    ...
    current = read_scheme(rig, bones, weapon)
    others = [w for w in weapons if not _same(w, weapon)]
    if others:
        other = others[0]
        taken = driven_side(rig, bones, other) if not weaponspace.holding_hand(other) else None
        text = blocked(current, wanted, read_scheme(rig, bones, other), weapon_label(other), taken)
        if text:
            return text
```

and the hang step uses `driven_side(rig, bones, weapon)` for this weapon only. `connect(rig=None, sides=SIDES)` and `disconnect(rig=None)` resolve `chosen_weapon` and pass it (`disconnect`: `held = driven_side(rig, None, weapon) or "R"`). `header_text(rig, weapon, scheme, others="")` appends `"; also " + others` when given. `refresh()` fills the chooser (`_set_chooser(weapons, chosen)`: labels via `labels_for`, `enable=False` and label "—" on an empty slot, `select=True` on the chosen one). `_chooser_picked(index)` stores the UUID of `weapons_of(...)[index]` into `_PICKED` and refreshes. `build_panel()` builds the chooser row first:

```python
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(64, 110),
                   columnAttach=[(1, "left", 0), (2, "both", 4)])
    cmds.text(label="Acts on", font="boldLabelFont")
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(CHOOSER)
    for index in (0, 1):
        hubstyle.mark(cmds.iconTextRadioButton(
            chooser_segment(index), style="textOnly", label="-", height=22,
            select=index == 0, enable=index == 0,
            annotation="the weapon the rows below act on (or select it)",
            onCommand=_chooser_picked(index)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")
```

- [ ] **Step 4: Run** `tests.test_scenesetup_connections tests.test_hotkeys tests.test_hub_sections` — PASS.
- [ ] **Step 5: Commit** — `feat(connections): two weapons - the section acts on the chosen one, a hand holds or follows, never both`

---

### Task 5: the floor (`floor.py`, park/unpark, `drive_socket`, world relink)

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/floor.py`
- Modify: `SkeldarAnim/maya_scenesetup/bonedrive.py` (replace the Task 2 stubs; `drive_socket`; `relink`)
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` (`_drive_bone` → `bonedrive.drive_socket`; hang drops the park)
- Test: `tests/test_scenesetup_floor.py` (create), `tests/test_scenesetup_bonedrive.py` (append)

**Interfaces:**
- Produces: `floor.lying_pose(bbox, scale, point, heading) -> (rotate3, translate3)` (pure); `floor.drop(entry, bone, point, heading, rgb=None) -> (weapon, note)`;
  `bonedrive.PARK_BONE`, `bonedrive.park_attr(channel)`, `bonedrive.park(weapon, bone)`, `bonedrive.unpark(weapon, bone) -> bool`, `bonedrive.is_parked(weapon)`, `bonedrive.drop_park(weapon)`, `bonedrive.drive_socket(weapon, bone)`, `bonedrive.is_held(weapon)`.

- [ ] **Step 1: Failing tests** — `tests/test_scenesetup_floor.py`:

```python
"""A weapon on the floor (2026-09-29): lying flat, lowest point on Y=0, the
blade along the given heading, the bone's track parked on it.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import math
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive
from maya_scenesetup import floor

SWORD_BOX = (-15.576, -31.119, -1.57, 15.576, 115.925, 1.57)


def world_points(rotate, translate, scale, box):
    m = om.MTransformationMatrix()
    m.setScale((scale, scale, scale), om.MSpace.kTransform)
    m.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    m.setTranslation(om.MVector(*translate), om.MSpace.kTransform)
    matrix = m.asMatrix()
    corners = [om.MPoint(x, y, z) for x in (box[0], box[3])
               for y in (box[1], box[4]) for z in (box[2], box[5])]
    return [p * matrix for p in corners], matrix


class LyingPose(unittest.TestCase):

    def test_the_lowest_point_is_on_the_floor(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (30.0, 0.0, -12.0), (1.0, 0.0, 0.0))
        points, _ = world_points(rotate, translate, 1.0, SWORD_BOX)
        self.assertAlmostEqual(min(p.y for p in points), 0.0, places=9)

    def test_the_thickness_stands_up_and_the_blade_along_the_heading(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (0.0, 0.0, 0.0), (0.0, 0.3, 2.0))
        _, matrix = world_points(rotate, translate, 1.0, SWORD_BOX)
        blade = om.MVector(matrix[4], matrix[5], matrix[6]).normal()
        thick = om.MVector(matrix[8], matrix[9], matrix[10]).normal()
        self.assertAlmostEqual(thick.y, 1.0, places=9)
        self.assertAlmostEqual(blade * om.MVector(0, 0, 1), 1.0, places=9)

    def test_the_middle_of_the_weapon_is_over_the_point(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 0.4, (30.0, 5.0, -12.0), (0.0, 0.0, -1.0))
        points, _ = world_points(rotate, translate, 0.4, SWORD_BOX)
        cx = (min(p.x for p in points) + max(p.x for p in points)) / 2
        cz = (min(p.z for p in points) + max(p.z for p in points)) / 2
        self.assertAlmostEqual(cx, 30.0, places=9)
        self.assertAlmostEqual(cz, -12.0, places=9)
        self.assertAlmostEqual(min(p.y for p in points), 5.0, places=9)

    def test_a_vertical_heading_falls_back_to_x(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (0, 0, 0), (0.0, 1.0, 0.0))
        _, matrix = world_points(rotate, translate, 1.0, SWORD_BOX)
        self.assertAlmostEqual(matrix[4], 1.0, places=9)


class ParkNames(unittest.TestCase):

    def test_one_attribute_per_channel(self):
        self.assertEqual(bonedrive.park_attr("translateX"), "skeldarParkTranslateX")
        self.assertEqual(bonedrive.park_attr("rotateZ"), "skeldarParkRotateZ")

    def test_the_space_marker_is_weaponspaces(self):
        from maya_scenesetup import weaponspace
        self.assertEqual(bonedrive.SPACE_MARKER, weaponspace.SPACE_MARKER)
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement**

`floor.py`:

```python
"""A weapon on the floor: the character's, its hand's bone following it.

2026-09-29, the animator's inventory: a weapon dropped on the floor lies there
and its hand's weapon bone follows it - the Connections "World" state - so a
pickup is animated from there and the export carries it through the bone. The
bone's own track is PARKED on the weapon (`bonedrive.park`) and handed back if
the weapon is taken off while it still lies there.
"""

import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_scenesetup import attach
from maya_scenesetup import bonedrive


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def lying_pose(bbox, scale, point, heading):
    """(rotate XYZ degrees, translate) laying a model flat. Pure.

    `bbox` is the unscaled model's (xmin, ymin, zmin, xmax, ymax, zmax) in its
    own axes: blade +Y, guard X, thickness Z, like every catalog weapon. The
    thickness stands straight up, the blade runs along `heading` projected on
    the floor (world X when the heading is vertical), the box's middle is over
    `point` and its lowest point on `point`'s height.
    """
    hx, hz = float(heading[0]), float(heading[2])
    length = math.hypot(hx, hz)
    if length < 1e-9:
        hx, hz, length = 1.0, 0.0, 1.0
    y_axis = (hx / length, 0.0, hz / length)
    z_axis = (0.0, 1.0, 0.0)
    x_axis = _cross(y_axis, z_axis)
    centre = [(bbox[i] + bbox[i + 3]) * 0.5 * scale for i in range(3)]
    tx = point[0] - (centre[0] * x_axis[0] + centre[1] * y_axis[0])
    tz = point[2] - (centre[0] * x_axis[2] + centre[1] * y_axis[2])
    ty = point[1] - bbox[2] * scale
    rotation = om.MMatrix([x_axis[0], x_axis[1], x_axis[2], 0.0,
                           y_axis[0], y_axis[1], y_axis[2], 0.0,
                           z_axis[0], z_axis[1], z_axis[2], 0.0,
                           0.0, 0.0, 0.0, 1.0])
    euler = om.MTransformationMatrix(rotation).rotation(asQuaternion=False)
    euler = euler.reorder(om.MEulerRotation.kXYZ)
    return (tuple(math.degrees(v) for v in (euler.x, euler.y, euler.z)),
            (tx, ty, tz))


def model_box(weapon, scale):
    """The unscaled model's box: the weapon stands seated (identity rotate and
    translate, the catalog scale) at world level right after the import."""
    box = cmds.exactWorldBoundingBox(weapon)
    return tuple(value / scale for value in box)


def drop(entry, bone, point, heading, rgb=None):
    """`entry`'s weapon lying at `point`, `bone` following it with its own
    track parked on the weapon. One undo chunk; the bone must be free (the
    caller takes off whatever it followed). Returns (weapon, note)."""
    if bonedrive.driving_weapon(bone):
        raise RuntimeError("%s already follows a weapon" % bone.split("|")[-1])
    cmds.undoInfo(openChunk=True, chunkName="Weapon onto the floor")
    autokey = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        weapon, note = attach.import_weapon(entry, None, rgb)
        scale = float(getattr(entry, "scale", 1.0)) or 1.0
        rotate, translate = lying_pose(model_box(weapon, scale), scale, point, heading)
        cmds.xform(weapon, worldSpace=True, translation=translate)
        cmds.xform(weapon, worldSpace=True, rotation=rotate)
        bonedrive.park(weapon, bone)
        bonedrive.drive_socket(weapon, bone)
        return weapon, note
    finally:
        cmds.autoKeyframe(state=autokey)
        cmds.undoInfo(closeChunk=True)
```

`bonedrive.py` (the stubs replaced):

```python
PARK_BONE = "skeldarParkBone"
SPACE_MARKER = "mayaWeaponSpace"   # weaponspace.SPACE_MARKER; this module stays a leaf


def park_attr(channel):
    return "skeldarPark" + channel[0].upper() + channel[1:]


def is_parked(weapon):
    return bool(weapon) and cmds.objExists(weapon) and cmds.attributeQuery(
        PARK_BONE, node=weapon, exists=True)


def is_held(weapon):
    """True when a hand holds `weapon`: its parent is a weapon space, or a
    joint (a file from before 2026-09-24)."""
    parent = (cmds.listRelatives(weapon, parent=True, fullPath=True) or [None])[0]
    if parent is None:
        return False
    return (cmds.attributeQuery(SPACE_MARKER, node=parent, exists=True)
            or cmds.objectType(parent) == "joint")


def drop_park(weapon):
    """The parked data off `weapon`, its curves deleted."""
    if not weapon or not cmds.objExists(weapon):
        return
    for channel in CHANNELS:
        attr = weapon + "." + park_attr(channel)
        if cmds.objExists(attr):
            for curve in cmds.listConnections(attr, source=True, destination=False) or []:
                if cmds.objExists(curve):
                    cmds.delete(curve)
            cmds.deleteAttr(attr)
    if cmds.attributeQuery(PARK_BONE, node=weapon, exists=True):
        cmds.deleteAttr(weapon + "." + PARK_BONE)


def park(weapon, bone):
    """The bone's own track onto `weapon`, before the weapon drives it.

    Each transform channel's animCurve is reconnected to a matching attribute
    on the weapon (doubleLinear / doubleAngle, so no unitConversion creeps in),
    a plain channel's value copied; the bone's UUID recorded. What was parked
    before goes first - a retarget parks the fresh clip over a stale one.
    """
    drop_park(weapon)
    cmds.addAttr(weapon, longName=PARK_BONE, dataType="string")
    cmds.setAttr(weapon + "." + PARK_BONE, cmds.ls(bone, uuid=True)[0], type="string")
    for channel in CHANNELS:
        attr = park_attr(channel)
        kind = "doubleLinear" if channel.startswith("translate") else "doubleAngle"
        cmds.addAttr(weapon, longName=attr, attributeType=kind, keyable=False)
        plug = bone + "." + channel
        curves = cmds.listConnections(plug, source=True, destination=False,
                                      type="animCurve", plugs=True) or []
        if curves:
            cmds.connectAttr(curves[0], weapon + "." + attr)
            cmds.disconnectAttr(curves[0], plug)
        else:
            cmds.setAttr(weapon + "." + attr, cmds.getAttr(plug))


def _our_constraints(bone, weapon):
    out = []
    for constraint in _constraints_on(bone):
        targets = cmds.parentConstraint(constraint, query=True, targetList=True) or []
        if any(cmds.ls(t, long=True) == cmds.ls(weapon, long=True) for t in targets):
            out.append(constraint)
    return out


def unpark(weapon, bone):
    """The parked track back onto the bone, our constraint off it: the bone
    exactly as it was before the drop. False when nothing was parked."""
    if not is_parked(weapon):
        return False
    with _autokey_off():
        for constraint in _our_constraints(bone, weapon):
            cmds.delete(constraint)
        for channel in CHANNELS:
            attr = weapon + "." + park_attr(channel)
            if not cmds.objExists(attr):
                continue
            plug = bone + "." + channel
            curves = cmds.listConnections(attr, source=True, destination=False, plugs=True) or []
            if curves:
                cmds.connectAttr(curves[0], plug, force=True)
                cmds.disconnectAttr(curves[0], attr)
            else:
                try:
                    cmds.setAttr(plug, cmds.getAttr(attr))
                except RuntimeError:
                    pass
        drop_park(weapon)
    return True


def drive_socket(weapon, bone):
    """The bone onto the weapon's SOCKET, no offset (Connections' bone rule,
    moved here 2026-09-29 for the floor): keys cut first (trap 37), the current
    values written back (trap 58), a framed weapon's frame undone."""
    with _autokey_off():
        now = cmds.currentTime(query=True)
        settled = _keyed_values_at(bone, now)
        _cut(bone)
        for plug, value in settled:
            try:
                cmds.setAttr(plug, value)
            except RuntimeError:
                pass
        constraint = cmds.parentConstraint(weapon, bone, maintainOffset=False)[0]
        frame = frame_of(weapon)
        if any(frame):
            cmds.setAttr(constraint + ".target[0].targetOffsetRotate",
                         *unframing(frame, cmds.getAttr(bone + ".rotateOrder")))
    return constraint
```

`relink` gains, first thing:

```python
    if not is_held(weapon):
        # Out in world (on the floor, or lifted in Connections): it stays where
        # it is - the fresh track is parked on it and the bone follows it again.
        with _autokey_off():
            park(weapon, bone)
            drive_socket(weapon, bone)
        return 0
```

`connections._drive_bone(weapon, bone)` becomes `return bonedrive.drive_socket(weapon, bone)`; the hang step calls `bonedrive.drop_park(weapon)` after `_drive_bone`.

- [ ] **Step 4: Run** `tests.test_scenesetup_floor tests.test_scenesetup_bonedrive tests.test_scenesetup_connections tests.test_scenesetup_attach` — PASS (the Connections boundary tests that grep `_drive_bone` for `maintainOffset=False` / `targetOffsetRotate` read `bonedrive.drive_socket` now — update them to parse `bonedrive.py`).
- [ ] **Step 5: Commit** — `feat(weapons): a weapon on the floor - lying flat, the bone's track parked on it, a retarget leaves it there`

---

### Task 6: `equip.py` — the inventory's scene actions

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/equip.py`
- Test: `tests/test_scenesetup_equip.py`

**Interfaces:**
- Consumes: `attach.attach/detach/find_attached/parent_bone/SOURCE/MARKER`, `floor.drop`, `grips.for_hand`, `catalog.side_bone/by_key/entry_for_path`, `connections.followers_of/following/weapon_label`, `colour.show_textures`, `skeleton.resolve_bone`.
- Produces:
  - `Holding = namedtuple("Holding", "where weapon key label")`, where ∈ `"hand"|"floor"|"follows"|None`
  - `holdings(root) -> {"R": Holding, "L": Holding}`
  - `floor_side(taken) -> "R"|"L"` (pure; `taken = {"R": bool, "L": bool}`)
  - `to_hand(root, side, entry) -> str`, `to_floor(root, entry, point, heading, side=None) -> str`, `take_off(root, side) -> str`, `move(root, side, target) -> str` where target is `("hand", root2, side2)` or `("floor", root2, point, heading)`
  - `entry_of(weapon) -> Weapon | None`
  - `refusal` strings raise nothing: every action returns its status text.

- [ ] **Step 1: Failing tests** — pure parts:

```python
import unittest

from maya_scenesetup import equip


class FloorSide(unittest.TestCase):

    def test_the_free_right_first(self):
        self.assertEqual(equip.floor_side({"R": False, "L": False}), "R")

    def test_the_free_left_when_the_right_is_taken(self):
        self.assertEqual(equip.floor_side({"R": True, "L": False}), "L")

    def test_both_taken_replaces_the_right(self):
        self.assertEqual(equip.floor_side({"R": True, "L": True}), "R")


class Messages(unittest.TestCase):

    def test_into_a_hand(self):
        self.assertEqual(equip.into_message("Long Sword 02", "|Manny_Rig:root", "L"),
                         "Long Sword 02 into Manny_Rig's left hand")

    def test_onto_the_floor(self):
        self.assertEqual(equip.floor_message("Spear 01", "|Manny_Rig:root", "L"),
                         "Spear 01 onto the floor - Manny_Rig's weapon_l follows it")

    def test_off(self):
        self.assertEqual(equip.off_message("Dagger 01", "|root", "R"),
                         "Dagger 01 off root's right hand - the bone has its animation back")

    def test_a_character_name_is_its_rig_namespace_or_its_root(self):
        self.assertEqual(equip.character_name("|Creep_Rig:Armature|Creep_Rig:root"), "Creep_Rig")
        self.assertEqual(equip.character_name("|root"), "root")
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement**:

```python
"""The inventory's scene actions: a weapon into a hand, onto the floor, off.

Every path is the Weapons section's own machinery - `attach` for a hand (the
grip remembered per hand, `grips`), `floor` for the floor, `attach.detach` to
take off - so the inventory and the panel can never disagree about what
"a weapon in the left hand" is. Each action is ONE undo chunk and answers its
status line; refusals change nothing.
"""

from collections import namedtuple

import maya.cmds as cmds

import maya_rigs
from maya_scenesetup import attach
from maya_scenesetup import bonedrive
from maya_scenesetup import catalog
from maya_scenesetup import colour as colouring
from maya_scenesetup import connections
from maya_scenesetup import floor
from maya_scenesetup import grips
from maya_scenesetup import skeleton

Holding = namedtuple("Holding", "where weapon key label")
EMPTY = Holding(None, None, "", "")
SIDE_LABEL = {"R": "right hand", "L": "left hand"}
BONE = "weapon_r"


# ------------------------------------------------------------------- pure

def floor_side(taken):
    """Which bone a weapon dropped on the floor takes: the free one, right
    first; both taken -> the right one's weapon is replaced. Pure."""
    if not taken.get("R"):
        return "R"
    if not taken.get("L"):
        return "L"
    return "R"


def character_name(root):
    """A rig's namespace, else the root's leaf. Pure."""
    leaf = (root or "").split("|")[-1]
    return leaf.split(":")[0] if ":" in leaf else leaf


def into_message(label, root, side):
    return "%s into %s's %s" % (label, character_name(root), SIDE_LABEL[side])


def floor_message(label, root, side):
    return "%s onto the floor - %s's %s follows it" % (
        label, character_name(root), catalog.side_bone(BONE, side))


def off_message(label, root, side):
    return "%s off %s's %s - the bone has its animation back" % (
        label, character_name(root), SIDE_LABEL[side])


# ------------------------------------------------------------------ scene

def _bones(root, side):
    bone = skeleton.resolve_bone(root, catalog.side_bone(BONE, side)) if root else None
    return (attach.parent_bone(bone) if bone else None), bone


def occupant(root, side):
    """(weapon, where) of `side`: held in the hand, or on the floor driving its
    bone; (None, None) when free."""
    hand, bone = _bones(root, side)
    if not bone:
        return None, None
    held = (attach.find_attached(hand) if hand else None) or attach.find_attached(bone)
    if held:
        return held, "hand"
    world = bonedrive.driving_weapon(bone)
    if world:
        return world, ("hand" if bonedrive.is_held(world) else "floor")
    return None, None


def _rig(root):
    return maya_rigs.rig_of(root, maya_rigs.rigs()) if root else None


def holdings(root):
    out = {}
    rig = _rig(root)
    for side in catalog.SIDES:
        weapon, where = occupant(root, side)
        if weapon:
            out[side] = Holding(where, weapon, _key(weapon), connections.weapon_label(weapon))
            continue
        rides = connections.following(rig, side) if rig else None
        out[side] = (Holding("follows", rides, _key(rides), connections.weapon_label(rides))
                     if rides else EMPTY)
    return out


def _key(weapon):
    if weapon and cmds.attributeQuery(attach.MARKER, node=weapon, exists=True):
        return cmds.getAttr(weapon + "." + attach.MARKER) or ""
    return ""


def entry_of(weapon):
    """The catalog row a weapon node came from, else its source file's entry."""
    entry = catalog.by_key(_key(weapon))
    if entry:
        return entry
    if cmds.attributeQuery(attach.SOURCE, node=weapon, exists=True):
        path = cmds.getAttr(weapon + "." + attach.SOURCE)
        if path:
            return catalog.entry_for_path(path, BONE)
    return None


def _refusal(root, side):
    """Why `side` of `root` cannot take a weapon, or ""."""
    hand, bone = _bones(root, side)
    if not root:
        return "no character there"
    if not bone:
        return "%s has no bone '%s'" % (character_name(root), catalog.side_bone(BONE, side))
    rig = _rig(root)
    rides = connections.following(rig, side) if rig else None
    if rides:
        return "the %s follows the %s - release it in Connections first" % (
            SIDE_LABEL[side], connections.weapon_label(rides))
    weapon, _where = occupant(root, side)
    if weapon and connections.followers_of(weapon):
        return "the hands ride the %s - release them in Connections first" % (
            connections.weapon_label(weapon))
    return ""


def to_hand(root, side, entry):
    refusal = _refusal(root, side)
    if refusal:
        return refusal
    absent = catalog.missing(entry)
    if absent:
        return "file not found: " + absent
    hand, bone = _bones(root, side)
    rotate, translate = grips.for_hand(entry, side, root)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: into a hand")
    try:
        attach.detach(hand, bone)
        _weapon, note = attach.attach(entry, hand, bone, rotate, translate)
    finally:
        cmds.undoInfo(closeChunk=True)
    text = into_message(entry.label, root, side)
    if getattr(entry, "texture", ""):
        colouring.show_textures()
    return text + (" - " + note if note else "")


def to_floor(root, entry, point, heading, side=None):
    if side is None:
        taken = dict((s, bool(occupant(root, s)[0])) for s in catalog.SIDES)
        side = floor_side(taken)
    refusal = _refusal(root, side)
    if refusal:
        return refusal
    absent = catalog.missing(entry)
    if absent:
        return "file not found: " + absent
    hand, bone = _bones(root, side)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: onto the floor")
    try:
        attach.detach(hand, bone)
        _weapon, note = floor.drop(entry, bone, point, heading)
    finally:
        cmds.undoInfo(closeChunk=True)
    if getattr(entry, "texture", ""):
        colouring.show_textures()
    return floor_message(entry.label, root, side) + (" - " + note if note else "")


def take_off(root, side):
    weapon, _where = occupant(root, side)
    if not weapon:
        return "nothing in the %s" % SIDE_LABEL[side]
    if connections.followers_of(weapon):
        return "the hands ride the %s - release them in Connections first" % (
            connections.weapon_label(weapon))
    label = connections.weapon_label(weapon)
    hand, bone = _bones(root, side)
    cmds.undoInfo(openChunk=True, chunkName="Inventory: take off")
    try:
        attach.detach(hand, bone)
    finally:
        cmds.undoInfo(closeChunk=True)
    return off_message(label, root, side)


def move(root, side, target):
    """The weapon of `side` taken off and the same weapon put at `target`:
    ("hand", root2, side2) or ("floor", root2, point, heading)."""
    weapon, _where = occupant(root, side)
    if not weapon:
        return "nothing in the %s" % SIDE_LABEL[side]
    entry = entry_of(weapon)
    if entry is None:
        return "cannot tell which file %s came from - Weapons > Add it again" % weapon.split("|")[-1]
    cmds.undoInfo(openChunk=True, chunkName="Inventory: move")
    try:
        ok, off = _take_off(root, side)       # take_off's body, answering (ok, text)
        if not ok:
            return off
        if target[0] == "hand":
            return to_hand(target[1], target[2], entry)
        return to_floor(target[1], entry, target[2], target[3])
    finally:
        cmds.undoInfo(closeChunk=True)
```

- [ ] **Step 4: Run** `tests.test_scenesetup_equip` — PASS.
- [ ] **Step 5: Commit** — `feat(inventory): the scene actions - into a hand, onto the floor, off, moved`

---

### Task 7: `droptarget.py` — which hand, or the floor

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/droptarget.py`
- Test: `tests/test_scenesetup_droptarget.py`

**Interfaces:**
- Produces: `Figure = namedtuple("Figure", "key segments hands depth")` (screen space); `seg_distance(p, a, b)`; `choose(point, figures, radius_min) -> ("hand", key, side) | None` (pure);
  `floor_hit(near, far) -> (x, y, z) | None` (pure, the ray against Y=0 in front of the camera);
  `owner(point3, roots) -> key | None` (pure; roots = {key: (x, y, z)});
  `snapshot() -> [dict(key, label, points, segments, hands, root)]`; `Viewport` — `.at(gx, gy)`, `.project(world)`, `.ray(x, y)`, `.heading()`; `target(gx, gy, snap) -> dict(kind, root, side, point, heading, text)`.

- [ ] **Step 1: Failing tests**

```python
import unittest

from maya_scenesetup import droptarget as dt


def figure(key, x0, hands):
    """A stick figure standing at x0, 100 px tall."""
    segments = [((x0, 0.0), (x0, 100.0)), ((x0 - 30, 70.0), (x0 + 30, 70.0))]
    return dt.Figure(key, segments, hands, depth=10.0)


class Choose(unittest.TestCase):

    def test_on_the_figure_the_nearer_hand(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((125.0, 60.0), [f], 16), ("hand", "A", "L"))
        self.assertEqual(dt.choose((95.0, 30.0), [f], 16), ("hand", "A", "R"))

    def test_off_the_figure_nothing(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertIsNone(dt.choose((300.0, 60.0), [f], 16))

    def test_the_radius_grows_with_the_figure(self):
        big = dt.Figure("A", [((0.0, 0.0), (0.0, 1000.0))], {"R": (0.0, 700.0)}, 1.0)
        self.assertEqual(dt.choose((70.0, 500.0), [big], 16), ("hand", "A", "R"))

    def test_the_nearest_figure_wins(self):
        a = figure("A", 100.0, {"R": (70.0, 70.0)})
        b = figure("B", 140.0, {"R": (110.0, 70.0)})
        self.assertEqual(dt.choose((136.0, 40.0), [a, b], 16)[1], "B")

    def test_a_missing_hand_is_skipped(self):
        f = figure("A", 100.0, {"R": None, "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((75.0, 70.0), [f], 16), ("hand", "A", "L"))

    def test_a_figure_without_hands_is_no_target(self):
        f = figure("A", 100.0, {"R": None, "L": None})
        self.assertIsNone(dt.choose((100.0, 50.0), [f], 16))


class Floor(unittest.TestCase):

    def test_a_ray_down_meets_the_floor(self):
        self.assertEqual(dt.floor_hit((0.0, 100.0, 50.0), (0.0, -100.0, -50.0)), (0.0, 0.0, 0.0))

    def test_a_ray_up_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (0.0, 20.0, 5.0)))

    def test_a_level_ray_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (5.0, 10.0, 5.0)))

    def test_the_owner_is_the_nearest_on_the_floor(self):
        roots = {"A": (0.0, 0.0, 0.0), "B": (300.0, 90.0, 0.0)}
        self.assertEqual(dt.owner((250.0, 0.0, 10.0), roots), "B")
        self.assertIsNone(dt.owner((0.0, 0.0, 0.0), {}))
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement** — pure half:

```python
"""Where a weapon dragged out of the inventory lands: a hand, or the floor.

Read once when a drag starts (the camera and the time cannot move while the
mouse is ours): every character's joints in world space, its bones as
parent->child segments, its two hands (the drive bones' parents) and its
root. Per move they are projected through the model panel under the cursor.
A character whose nearest bone on screen is within R = max(radius_min, 0.08 x
its projected height) is under the cursor and the hand nearer the cursor is
the target; otherwise the camera ray meets the floor (Y = 0) in front of the
camera and the character nearest to that point owns the weapon. Bones, not
meshes: every character has them, a bare skeleton included.
"""

import math
from collections import namedtuple

Figure = namedtuple("Figure", "key segments hands depth")
HEIGHT_SHARE = 0.08


def seg_distance(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 < 1e-12 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _height(segments):
    ys = [y for seg in segments for _x, y in seg]
    return (max(ys) - min(ys)) if ys else 0.0


def choose(point, figures, radius_min):
    """("hand", key, side) for the figure under `point`, else None. Pure."""
    best = None
    for fig in figures:
        if not fig.segments or not any(fig.hands.values()):
            continue
        radius = max(radius_min, HEIGHT_SHARE * _height(fig.segments))
        near = min(seg_distance(point, a, b) for a, b in fig.segments)
        if near > radius:
            continue
        score = (near / radius, fig.depth)
        if best is None or score < best[0]:
            best = (score, fig)
    if best is None:
        return None
    fig = best[1]
    side = min((s for s in ("R", "L") if fig.hands.get(s)),
               key=lambda s: math.hypot(point[0] - fig.hands[s][0], point[1] - fig.hands[s][1]))
    return ("hand", fig.key, side)


def floor_hit(near, far, height=0.0):
    """Where the ray near -> far meets Y = height in front of `near`, or None."""
    dy = far[1] - near[1]
    if abs(dy) < 1e-12:
        return None
    t = (height - near[1]) / dy
    if t <= 0.0:
        return None
    return tuple(near[i] + t * (far[i] - near[i]) for i in range(3))


def owner(point, roots):
    """The key whose root stands nearest to `point` on the floor, or None."""
    if not roots:
        return None
    return min(roots, key=lambda k: math.hypot(point[0] - roots[k][0], point[2] - roots[k][2]))
```

Scene half (same module, imports inside the functions so the pure tests need no Maya UI):

```python
def characters():
    """(root, label) of every character: the rigs' game skeletons, then bare
    skeletons (the Weapons section's own reading, `skeleton.current_root`)."""
    import maya_rigs
    from maya_overrig import builder
    from maya_scenesetup import equip
    rigs = maya_rigs.rigs()
    roots = [rig.skeleton_root for rig in rigs if rig.skeleton_root]
    for root in builder.character_roots():
        if root not in roots and not any(maya_rigs.under(root, rig.group) for rig in rigs if rig.group):
            roots.append(root)
    return [(root, equip.character_name(root)) for root in roots]


def snapshot():
    import maya.cmds as cmds
    from maya_scenesetup import equip
    out = []
    for root, label in characters():
        joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
        points = dict((j, tuple(cmds.xform(j, query=True, worldSpace=True, translation=True))) for j in joints)
        segments = []
        for j in joints:
            parent = (cmds.listRelatives(j, parent=True, fullPath=True) or [None])[0]
            if parent in points:
                segments.append((parent, j))
        hands = {}
        for side in ("R", "L"):
            hand, _bone = equip._bones(root, side)
            hands[side] = hand if hand in points else None
        out.append(dict(key=root, label=label, points=points, segments=segments,
                        hands=hands, root=points[root]))
    return out


class Viewport(object):
    """The model panel under a global cursor position, and its camera."""

    def __init__(self, panel, view, widget):
        self.panel, self.view, self.widget = panel, view, widget
        self.sx = view.portWidth() / float(max(1, widget.width()))
        self.sy = view.portHeight() / float(max(1, widget.height()))

    @classmethod
    def at(cls, gx, gy):
        import maya.cmds as cmds
        import maya.OpenMayaUI as omui1   # noqa - M3dView lives in both APIs
        import maya.api.OpenMayaUI as omui
        from maya_hubqt import qt
        q = qt()
        panels = []
        under = cmds.getPanel(underPointer=True)
        if under and cmds.getPanel(typeOf=under) == "modelPanel":
            panels.append(under)
        panels += [p for p in (cmds.getPanel(type="modelPanel") or []) if p not in panels]
        for panel in panels:
            try:
                view = omui.M3dView.getM3dViewFromModelPanel(panel)
            except RuntimeError:
                continue
            widget = q.shiboken.wrapInstance(int(view.widget()), q.QtWidgets.QWidget)
            if not widget.isVisible():
                continue
            local = widget.mapFromGlobal(q.QtCore.QPoint(int(gx), int(gy)))
            if widget.rect().contains(local):
                return cls(panel, view, widget), (local.x(), local.y())
        return None, None

    def to_port(self, local):
        return local[0] * self.sx, (self.widget.height() - local[1]) * self.sy

    def project(self, world):
        import maya.api.OpenMaya as om
        x, y, _clipped = self.view.worldToView(om.MPoint(*world))
        return float(x), float(y)

    def ray(self, port):
        import maya.api.OpenMaya as om
        near, far = om.MPoint(), om.MPoint()
        self.view.viewToWorld(int(port[0]), int(port[1]), near, far)
        return (near.x, near.y, near.z), (far.x, far.y, far.z)

    def heading(self):
        import maya.api.OpenMaya as om
        camera = self.view.getCamera()
        right = om.MFnCamera(camera).rightDirection(om.MSpace.kWorld)
        return (right.x, right.y, right.z)

    def depth(self, world):
        import maya.api.OpenMaya as om
        eye = om.MFnCamera(self.view.getCamera()).eyePoint(om.MSpace.kWorld)
        return (om.MPoint(*world) - eye).length()


def target(gx, gy, snap, scale=1.0):
    """What a release at the global point would do:
    {"kind": "hand"|"floor"|"none", "root", "side", "point", "heading", "text"}."""
    view, local = Viewport.at(gx, gy)
    if view is None:
        return dict(kind="none", text="no target - drop onto a viewport")
    port = view.to_port(local)
    figures = []
    for ch in snap:
        pts = dict((j, view.project(p)) for j, p in ch["points"].items())
        figures.append(Figure(ch["key"], [(pts[a], pts[b]) for a, b in ch["segments"]],
                              dict((s, pts[h] if h else None) for s, h in ch["hands"].items()),
                              view.depth(ch["root"])))
    picked = choose(port, figures, 16.0 * scale * view.sx)
    if picked:
        ch = next(c for c in snap if c["key"] == picked[1])
        from maya_scenesetup import equip
        return dict(kind="hand", root=ch["key"], side=picked[2],
                    text="%s \u00b7 %s" % (ch["label"], equip.SIDE_LABEL[picked[2]]))
    near, far = view.ray(port)
    hit = floor_hit(near, far)
    if hit is None:
        return dict(kind="none", text="no floor under the cursor")
    key = owner(hit, dict((c["key"], c["root"]) for c in snap))
    if key is None:
        return dict(kind="none", text="no character in the scene")
    ch = next(c for c in snap if c["key"] == key)
    return dict(kind="floor", root=key, point=hit, heading=view.heading(),
                text="floor \u00b7 %s" % ch["label"])
```

(The floor text names the bone once the equip rule decides it; the window adds `· weapon_l` through `equip.floor_side` when it composes the caption.)

- [ ] **Step 4: Run** `tests.test_scenesetup_droptarget` — PASS.
- [ ] **Step 5: Commit** — `feat(inventory): the drop target - the hand under the cursor, else the floor`

---

### Task 8: weapon icons

**Files:**
- Create: `docs/superpowers/plans/make_weapon_icons.py`
- Create: `SkeldarAnim/assets/weapon_icons/*.png`, `weapon_icons.json`
- Test: `tests/test_invlook.py` (the catalog-has-icons gate lives with the look)

**Interfaces:**
- Produces: `assets/weapon_icons/<key>.png` (w×80 by h×80 px, transparent) and `weapon_icons.json` = `{key: {"cells": [w, h], "length": cm}}`.

- [ ] **Step 1:** Write the script (mayapy standalone; `QT_QPA_PLATFORM=offscreen`; `QGuiApplication`):
  - For each `catalog.WEAPONS` row: `cmds.file(new=True, force=True)`; `cmds.file(entry.path, i=True, type="FBX")` with `FBXImportMode -v add` (trap 33); the meshes' world triangles (`MFnMesh.getTriangles`, `getPoints(kWorld)`), × `entry.scale`.
  - Length `L = ymax - ymin`, width `W = xmax - xmin`; cells `h = clamp(round(2 + (L - 45) / 55), 2, 5)`, `w = 1`.
  - Canvas `w*80 × h*80`, padding 6 %, uniform fit, y up.
  - Per triangle: normal `n` (cross of edges, normalised); `shade = 0.30 + 0.70 * max(0, n·L)` with `L = normalize(-0.45, 0.55, 0.70)`; colour by region — polearm (`L / W > 10`): steel above `ymax - 0.22 L`, wood below; blade: leather `y < 0`, bronze where `|y| < 0.06 L and |x| > 0.45 * max|x|`, steel elsewhere; a textured row samples its PNG at the triangle's mean UV (`QImage.pixelColor(u*w, (1-v)*h)`).
  - Painter's order: sort by centroid z ascending (the viewer at +Z); fill + a same-colour pen of 0.6 px (no hairline seams); a 1.5 px dark rim pass first (the whole silhouette in `#0d0a07` drawn with a 2 px pen), so the icon reads on the dark grid.
  - Save PNGs and the JSON with `sort_keys=True`.
- [ ] **Step 2:** Run it: `& mayapy docs/superpowers/plans/make_weapon_icons.py`; open each PNG with the Read tool and tune colours by eye.
- [ ] **Step 3:** The gate (in `tests/test_invlook.py`, Task 9): every catalog row has a PNG and a JSON entry.
- [ ] **Step 4: Commit** — `feat(inventory): weapon icons rendered from the models`

---

### Task 9: `maya_invlook.py` — the look as data (pure)

**Files:**
- Create: `SkeldarAnim/maya_invlook.py`
- Test: `tests/test_invlook.py`

**Interfaces:**
- Produces: `CELL = 40`, `COLS = 10`, `ROWS = 5`, `SLOT = (2, 4)`, `PALETTE` (dict of hex), `TITLE_FONTS`;
  `item_cells(length) -> (1, h)`; `pack(items, cols=COLS, rows=ROWS) -> {key: (col, row)}` (items = [(key, (w, h))], column-major first fit, overflow skipped);
  `layout() -> {name: (x, y, w, h)}` in logical px — `window, title, close, name, slot_R, slot_L, grid, status`;
  `hit(rects, placements, cells, x, y) -> ("close",)|("title",)|("slot", side)|("item", key)|("grid",)|None`;
  `icons_dir()`, `icon_path(key)`, `load_cells() -> {key: (w, h)}`.

- [ ] **Step 1: Failing tests**

```python
import json
import os
import unittest

import maya_invlook as look
from maya_scenesetup import catalog


class Cells(unittest.TestCase):

    def test_heights_follow_the_length(self):
        self.assertEqual(look.item_cells(45.7), (1, 2))
        self.assertEqual(look.item_cells(124.0), (1, 3))
        self.assertEqual(look.item_cells(147.0), (1, 4))
        self.assertEqual(look.item_cells(199.6), (1, 5))
        self.assertEqual(look.item_cells(266.2), (1, 5))


class Pack(unittest.TestCase):

    def test_column_major_first_fit(self):
        placed = look.pack([("a", (1, 4)), ("b", (1, 2)), ("c", (1, 2)), ("d", (1, 5))], cols=3, rows=5)
        self.assertEqual(placed, {"a": (0, 0), "b": (1, 0), "c": (1, 2), "d": (2, 0)})

    def test_what_does_not_fit_is_left_out(self):
        self.assertEqual(look.pack([("a", (1, 6))], cols=2, rows=5), {})


class Layout(unittest.TestCase):

    def setUp(self):
        self.rects = look.layout()

    def test_everything_inside_the_window(self):
        wx, wy, ww, wh = self.rects["window"]
        for name, (x, y, w, h) in self.rects.items():
            self.assertTrue(x >= wx and y >= wy and x + w <= wx + ww and y + h <= wy + wh, name)

    def test_the_grid_is_ten_by_five_cells(self):
        _x, _y, w, h = self.rects["grid"]
        self.assertEqual((w, h), (look.COLS * look.CELL, look.ROWS * look.CELL))

    def test_the_right_hand_slot_is_on_the_viewers_left(self):
        self.assertLess(self.rects["slot_R"][0], self.rects["slot_L"][0])

    def test_hits(self):
        placements = {"LongSword_02": (0, 0)}
        cells = {"LongSword_02": (1, 4)}
        gx, gy = self.rects["grid"][:2]
        self.assertEqual(look.hit(self.rects, placements, cells, gx + 5, gy + 5), ("item", "LongSword_02"))
        self.assertEqual(look.hit(self.rects, placements, cells, gx + 45, gy + 5), ("grid",))
        sx, sy = self.rects["slot_L"][:2]
        self.assertEqual(look.hit(self.rects, placements, cells, sx + 3, sy + 3), ("slot", "L"))
        cx, cy = self.rects["close"][:2]
        self.assertEqual(look.hit(self.rects, placements, cells, cx + 2, cy + 2), ("close",))


class Icons(unittest.TestCase):

    def test_every_catalog_row_has_an_icon_and_cells(self):
        cells = look.load_cells()
        for entry in catalog.WEAPONS:
            self.assertTrue(os.path.isfile(look.icon_path(entry.key)), entry.key)
            self.assertIn(entry.key, cells)
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement**:

```python
"""The inventory's look as data (2026-09-29): Diablo's bronze and parchment,
the cells, where each weapon sits, what a point in the window is.

Stdlib only, like maya_hubstyle: the window paints what this module says, and
every decision here is tested without Qt.
"""

import json
import os

CELL = 40
COLS, ROWS = 10, 5
SLOT = (2, 4)
MARGIN = 14
TITLE_H = 34
NAME_H = 18
STATUS_H = 34
GAP = 12

PALETTE = {
    "ground": "#16110c", "frame": "#7a5a2e", "frame_hi": "#b08a3c", "frame_lo": "#3a2a14",
    "cell": "#0d0a07", "cell_line": "#3a2c18", "gold": "#d8b36a", "parchment": "#a08a64",
    "dim": "#7d6a4a", "valid": "#3f7a3a", "invalid": "#8a2f24", "hover": "#1f2a3a",
    "ghost_text": "#e8d6a8",
}
TITLE_FONTS = ("Palatino Linotype", "Book Antiqua", "Georgia", "serif")

_HERE = os.path.dirname(os.path.abspath(__file__))


def icons_dir():
    return os.path.join(_HERE, "assets", "weapon_icons")


def icon_path(key):
    return os.path.join(icons_dir(), key + ".png")


def load_cells():
    path = os.path.join(icons_dir(), "weapon_icons.json")
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        return {}
    return dict((key, tuple(value["cells"])) for key, value in data.items())


def item_cells(length):
    height = int(round(2 + (float(length) - 45.0) / 55.0))
    return (1, max(2, min(5, height)))


def pack(items, cols=COLS, rows=ROWS):
    taken = set()
    placed = {}
    for key, (w, h) in items:
        spot = None
        for col in range(cols - w + 1):
            for row in range(rows - h + 1):
                cells = set((col + i, row + j) for i in range(w) for j in range(h))
                if not cells & taken:
                    spot = (col, row, cells)
                    break
            if spot:
                break
        if spot:
            placed[key] = (spot[0], spot[1])
            taken |= spot[2]
    return placed


def layout():
    grid_w, grid_h = COLS * CELL, ROWS * CELL
    width = grid_w + 2 * MARGIN
    slot_w, slot_h = SLOT[0] * CELL, SLOT[1] * CELL
    y = MARGIN
    rects = {"title": (MARGIN, y, grid_w, TITLE_H)}
    rects["close"] = (MARGIN + grid_w - 22, y + 6, 22, 22)
    y += TITLE_H
    rects["name"] = (MARGIN, y, grid_w, NAME_H)
    y += NAME_H + GAP // 2
    middle = MARGIN + grid_w // 2
    rects["slot_R"] = (middle - GAP - slot_w - CELL, y, slot_w, slot_h)
    rects["slot_L"] = (middle + GAP + CELL, y, slot_w, slot_h)
    y += slot_h + GAP
    rects["grid"] = (MARGIN, y, grid_w, grid_h)
    y += grid_h + GAP // 2
    rects["status"] = (MARGIN, y, grid_w, STATUS_H)
    y += STATUS_H + MARGIN
    rects["window"] = (0, 0, width, y)
    return rects


def _inside(rect, x, y):
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def hit(rects, placements, cells, x, y):
    if _inside(rects["close"], x, y):
        return ("close",)
    for side in ("R", "L"):
        if _inside(rects["slot_" + side], x, y):
            return ("slot", side)
    if _inside(rects["grid"], x, y):
        gx, gy = rects["grid"][:2]
        col, row = int((x - gx) // CELL), int((y - gy) // CELL)
        for key, (c, r) in placements.items():
            w, h = cells.get(key, (1, 2))
            if c <= col < c + w and r <= row < r + h:
                return ("item", key)
        return ("grid",)
    if _inside(rects["title"], x, y):
        return ("title",)
    return None
```

- [ ] **Step 4: Run** `tests.test_invlook` — PASS (needs Task 8's assets).
- [ ] **Step 5: Commit** — `feat(inventory): the look as data - cells, packing, layout, hits`

---

### Task 10: the window (`maya_inventory.py`) and its wiring

**Files:**
- Create: `SkeldarAnim/maya_inventory.py`
- Modify: `SkeldarAnim/maya_scenesetup/window.py` (`Inventory` button), `SkeldarAnim/maya_hubicons.py` (`backpack`), `SkeldarAnim/maya_hotkeys.py` (`window.inventory`), `SkeldarAnim/install.py` (payload: `maya_inventory.py`, `maya_invlook.py`)
- Test: `tests/test_inventory.py`

**Interfaces:**
- Consumes: `maya_invlook.*`, `equip.*`, `droptarget.snapshot/target`, `maya_hubqt.qt()`, `catalog.WEAPONS`.
- Produces: `maya_inventory.show()`, `maya_inventory.close_all()`, `maya_inventory.OBJECT_NAME = "skeldarInventory"`, `maya_inventory.live()`,
  `InventoryWindow.drop_at(gx, gy, source)` (source = `("grid", key)` | `("slot", side)`), `.refresh()`, `.status_text`;
  `Scene` adapter class with `current()`, `holdings(root)`, `snapshot()`, `target(gx, gy, snap)`, `to_hand`, `to_floor`, `take_off`, `move` — the tests inject a fake.

- [ ] **Step 1: Failing tests** (`$env:QT_QPA_PLATFORM='offscreen'`):

```python
"""The inventory window offscreen: it builds, paints ink, and a drag on a fake
scene does what the table in the spec says."""

import unittest

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:            # noqa: BLE001
    QT = None

import maya_inventory as inv
import maya_invlook as look


class FakeScene(object):

    def __init__(self):
        self.log = []
        self.hold = {"R": ("hand", "LongSword_02", "Long Sword 02"), "L": (None, "", "")}
        self.aim = dict(kind="hand", root="|Manny_Rig:root", side="L", text="Manny_Rig · left hand")

    def current(self):
        return "|Manny_Rig:root"

    def holdings(self, root):
        from maya_scenesetup.equip import Holding
        return dict((s, Holding(w, "|w" if w else None, k, l)) for s, (w, k, l) in self.hold.items())

    def snapshot(self):
        return []

    def target(self, gx, gy, snap):
        return self.aim

    def to_hand(self, root, side, entry):
        self.log.append(("to_hand", root, side, entry.key)); return "into"

    def to_floor(self, root, entry, point, heading):
        self.log.append(("to_floor", root, entry.key)); return "floor"

    def take_off(self, root, side):
        self.log.append(("take_off", root, side)); return "off"

    def move(self, root, side, target):
        self.log.append(("move", root, side, target[0])); return "moved"


@unittest.skipIf(QT is None, "no Qt")
class Window(unittest.TestCase):

    def setUp(self):
        app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.scene = FakeScene()
        self.win = inv.make_window(self.scene, parent=None, remember=False)
        self.addCleanup(self.win.deleteLater)

    def test_it_paints_ink(self):
        image = QT.QtGui.QImage(self.win.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.win.render(image)
        inked = sum(1 for x in range(0, image.width(), 7) for y in range(0, image.height(), 7)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 100)

    def test_the_grid_holds_every_catalog_row(self):
        from maya_scenesetup import catalog
        self.assertEqual(set(self.win.placements), set(e.key for e in catalog.WEAPONS))

    def test_grid_onto_a_hand_in_the_viewport(self):
        self.win.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.scene.log, [("to_hand", "|Manny_Rig:root", "L", "Dagger_01")])

    def test_grid_onto_the_floor(self):
        self.scene.aim = dict(kind="floor", root="|root", point=(1, 0, 2), heading=(1, 0, 0), text="floor")
        self.win.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual(self.scene.log, [("to_floor", "|root", "Spear_01")])

    def test_slot_onto_the_grid_takes_it_off(self):
        gx, gy = self.win.mapToGlobal(QT.QtCore.QPoint(*[int(v) + 5 for v in self.win.rects["grid"][:2]])).toTuple()
        self.win.drop_at(gx, gy, ("slot", "R"))
        self.assertEqual(self.scene.log, [("take_off", "|Manny_Rig:root", "R")])

    def test_slot_onto_the_other_slot_moves_it(self):
        x, y = self.win.rects["slot_L"][:2]
        gx, gy = self.win.mapToGlobal(QT.QtCore.QPoint(int(x) + 5, int(y) + 5)).toTuple()
        self.win.drop_at(gx, gy, ("slot", "R"))
        self.assertEqual(self.scene.log, [("move", "|Manny_Rig:root", "R", "hand")])

    def test_no_target_does_nothing(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.win.drop_at(500, 500, ("grid", "Spear_01"))
        self.assertEqual(self.scene.log, [])
        self.assertIn("no floor", self.win.status_text)

    def test_the_status_line_takes_the_answer(self):
        self.win.drop_at(500, 500, ("grid", "Dagger_01"))
        self.assertEqual(self.win.status_text, "into")


class Wiring(unittest.TestCase):

    def test_the_payload_ships_both_modules(self):
        import install
        for name in ("maya_inventory.py", "maya_invlook.py"):
            self.assertIn(name, install.payload())

    def test_a_hotkey_row_opens_it(self):
        import maya_hotkeys
        self.assertIn("window.inventory", [row[0] for row in maya_hotkeys._OURS])

    def test_the_weapons_section_has_the_button(self):
        import inspect
        from maya_scenesetup import window
        self.assertIn("Inventory", inspect.getsource(window.build_weapons_panel))

    def test_the_backpack_icon(self):
        import maya_hubicons
        self.assertIn("backpack", maya_hubicons.ICONS)
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement** `maya_inventory.py`:
  - `Scene` — the real adapter: `current()` → `skeleton.current_root()`; `holdings` → `equip.holdings`; `snapshot` → `droptarget.snapshot()`; `target` → `droptarget.target(gx, gy, snap, _scale())`; the four actions → `equip`.
  - `_classes()` builds lazily (Qt imported inside): `Ghost(QWidget)` — `Qt.ToolTip | FramelessWindowHint | WindowStaysOnTopHint`, `WA_TranslucentBackground`, `WA_TransparentForMouseEvents`, `WA_ShowWithoutActivating`; paints the icon at 80 % opacity and a caption box (`ground` fill, `frame` border, `ghost_text`); `InventoryWindow(QWidget)` — `Qt.Tool | FramelessWindowHint`, fixed size = `layout()["window"]` × scale, object name `OBJECT_NAME`.
  - `InventoryWindow.__init__(scene, parent, remember)`: loads `QPixmap`s from `look.icon_path`, `self.cells = look.load_cells()` (fallback `look.item_cells(100)` per row), `self.placements = look.pack([(e.key, self.cells.get(e.key, (1, 3))) for e in catalog.WEAPONS])`, `self.rects` = layout × scale, restores `skeldarInventoryGeometry` when `remember`, `refresh()`.
  - `paintEvent`: ground; bevelled frame (three nested rects `frame_lo`, `frame`, `frame_hi`); the title in `TITLE_FONTS` gold, the name in parchment; the × in `frame_hi`; each slot a `cell`-filled rect with a `frame` border and its label at the bottom («Right hand», «Left hand») — a held weapon's icon fitted to the slot (a floor one at 45 % opacity plus «on the floor», «follows <label>» as text); while dragging over a slot, its border `valid` (or `invalid` when the source is that same slot); the grid: `cell` fill, `cell_line` lines, each item's icon in its cells (the item under the mouse on `hover`); the status text word-wrapped in parchment.
  - Mouse: press — `hit` → close (hide + kill job), title (start moving the window), item/slot with a weapon (start the drag: `self._drag = source`, ghost shown, `self._snap = scene.snapshot()`), else nothing. Move — moving the window, or the drag: ghost to the cursor, caption from `_describe(gx, gy)` throttled to 30 Hz (`QElapsedTimer`). Release — `drop_at(gx, gy, source)`; ghost hidden. Right button or Esc during a drag cancels.
  - `drop_at(gx, gy, source)`: local point → `hit`; a hit on the window: slot → from the grid `to_hand(current, side, entry)`, from the other slot `move(current, from, ("hand", current, side))`, from the same slot nothing; the grid from a slot → `take_off`; anywhere else in the window → nothing; outside the window → `target = scene.target(gx, gy, snap)`: hand → `to_hand` or `move(..., ("hand", root, side))`; floor → `to_floor(root, entry, point, heading)` or `move(..., ("floor", root, point, heading))`; none → the target's text. Everything through `_run`, which puts the answer or the exception's last line on `status_text` and refreshes.
  - The scriptJob: `cmds.scriptJob(event=[name, self._queue_refresh])` for `SelectionChanged`, `Undo`, `Redo`, `SceneOpened`, `NewSceneOpened`; ids kept; `_kill_jobs` on hide and on `destroyed`; `_queue_refresh` coalesces through `QTimer.singleShot(0, ...)`.
  - `show()`: `close_all()` first (every top-level widget with `OBJECT_NAME` from an older module object is deleted — trap 102's lesson), a fresh `InventoryWindow(Scene(), maya_main_window(), True)`, shown, raised. `live()` answers the open one.
  - `make_window(scene, parent=None, remember=False)` — the test seam.
  - `_scale()` = `mayaDpiSetting -q -realScaleValue` (1.0 without Maya).

  Wiring:
  - `window.build_weapons_panel`: after the Add / Remove row,
    ```python
    hubstyle.mark(cmds.button(
        label="Inventory", height=28,
        annotation="The weapon inventory: drag a weapon onto a hand in the "
                   "viewport, or onto the floor",
        command=lambda *_args: _run(open_inventory)), "secondary", "backpack")
    ```
    with `def open_inventory(): import maya_inventory; maya_inventory.show()`.
  - `maya_hubicons.ICONS["backpack"]` = Tabler's `backpack` paths:
    `"M5 18v-6a6 6 0 0 1 6 -6h2a6 6 0 0 1 6 6v6a3 3 0 0 1 -3 3h-8a3 3 0 0 1 -3 -3z"`, `"M10 6v-1a2 2 0 1 1 4 0v1"`, `"M9 21v-4a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v4"`, `"M11 10h2"`.
  - `maya_hotkeys._OURS`: `("window.inventory", "Windows", "Weapon inventory", "Open the weapon inventory: drag weapons onto the hands or the floor", partial(_show, "maya_inventory", "show"))`.
  - `install._PAYLOAD`: `"maya_invlook.py",  # the inventory's look (2026-09-29)` and `"maya_inventory.py",  # the inventory window`.

- [ ] **Step 4: Run** `tests.test_inventory tests.test_install tests.test_hotkeys tests.test_hubicons` and then the whole suite — PASS.
- [ ] **Step 5: Commit** — `feat(inventory): the Diablo window - the grid, the hands, the drag onto a hand or the floor`

---

### Task 11: proof, live runs, docs

**Files:**
- Create: `docs/superpowers/plans/verify_inventory.py` (mayapy standalone)
- Create: `docs/superpowers/plans/verify_inventory_live.py` (disposable Maya)
- Modify: `CLAUDE.md` (a section for the inventory)

- [ ] **Step 1: `verify_inventory.py`**, mayapy standalone, a fresh scene, gates printed `PASS/FAIL name value`, a final `N of M gates failed`:
  1. Manny rig added (`character.add_character(catalog.default_rig())`), rig at build pose.
  2. `equip.to_hand(root, "R", LongSword)` and `equip.to_hand(root, "L", Dagger)`: each weapon in its own space, `bonedrive.driving_weapon(weapon_r) == sword`, `(weapon_l) == dagger`.
  3. The left mirror: a second Long Sword into the left hand with no left grip stored — the node's world matrix against `Mz · W_right · Mx` (≤ 0.001 cm, ≤ 0.01°) — then the dagger back.
  4. `equip.to_floor(root, Spear01, (60, 0, 40), (1, 0, 0))` with both sides taken → the right hand's sword replaced (the `floor_side` rule), the sword gone; lowest vertex of the spear at y = 0.000 (vertices, not bbox — trap of the skin does not apply, the spear is not skinned, but measure the points anyway), its thickness axis up (dot ≥ 0.9999), `weapon_r` on its socket (0.000), the parked attributes present.
  5. Parked round trip: keys put on `weapon_r` BEFORE the drop (a known 3-key track) come back exactly (keys, values, tangents) after `equip.take_off(root, "R")`.
  6. A retarget with the dagger in the left hand and the spear on the floor (Longsword clip from `sources/`/the bridge cache, as `verify_creep_rig_asset.py` does): `weapon_l` carried from the clip and the dagger on it at its grip; the spear still on the floor (its world matrix unchanged 0.000); the parked track now the clip's `weapon_r`.
  7. Export (`animexport.export_hierarchy`) read back: bones only, 0 meshes.
  8. Creep rig: a sword into the left hand at the mirrored default against the mirror of the right (the geometric pair: default = zero grip).
- [ ] **Step 2: Run it** — all gates green; fix and re-run until so.
- [ ] **Step 3: `verify_inventory_live.py`** in a disposable Maya (port 7003, scratch `MAYA_APP_DIR`, killed after): Manny rig, sword right + dagger left; Connections: the chooser lists both; «Hand_L holds the Dagger 01» refusal on hanging the sword into Hand_L; moving the dagger to world then the sword into Hand_L (weapon_l driven by the dagger in world refusal); the sword's Hand_L follow refused while L holds; the inventory window open: `drop_at` onto the projected `hand_l` (global point via the panel widget's `mapToGlobal`) and onto a floor point; `widget.grab()` photos of the window in two states (two sends — trap 68); `verify_connections.py` still 40/40 there.
- [ ] **Step 4: Refresh the installed copy** in the animator's Maya if port 7001 listens (`install.install(quiet=True)` from the repo, `install` purged first); else say so.
- [ ] **Step 5: CLAUDE.md** — a section «The weapon inventory: two hands, the floor, a Diablo window (2026-09-29)» with the measured facts (the sockets table, the mirror formula, the parked track), the proofs and their numbers, and any trap met.
- [ ] **Step 6: Commit** — `docs: the weapon inventory - proofs and notes`

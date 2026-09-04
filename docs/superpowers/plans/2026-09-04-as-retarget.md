# Retarget onto the AdvancedSkeleton rig — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `maya_asretarget.py` — make the AdvancedSkeleton rig in the animator's scene follow a second, animated UE5 skeleton, in a shape AdvancedSkeleton's own **Bake** and **Disconnect MoCap Skeleton** buttons then handle unchanged.

**Architecture:** One root-level standalone module, `maya.cmds` only, no Qt, no package — the convention of every root-level tool and the sibling of `maya_retarget.py`. All policy lives in pure functions taking the scene as data (the drive table, the source resolution, the rest-offset algebra, the proportion check); the Maya-touching wrappers are thin. Constraints are built with NO maintainOffset wherever the control's rest frame already equals its bone's frame (measured identity after the 2026-09-04 axis work), and through a two-node offset helper where it does not (`Main`, `RootX_M`, the four poles). Every constraint's `nodeState` is connected to `MoCapConstraints.disableConstraints` and every helper is parented under `MoCapConstraints`, which is the entire contract AdvancedSkeleton's Bake and Disconnect rely on.

**Tech Stack:** Python 2/3-compatible plain `maya.cmds` + `maya.api.OpenMaya` for matrix algebra; `unittest` under `mayapy` for the pure parts; a live verify script sent through the command-port bridge for the rest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-04-as-retarget-design.md`. Read it before Task 1.
- Module path: `maya_asretarget.py` at the REPO ROOT (not in `SkeldarAnim/` — root tools never ship).
- `maya.cmds` and `maya.api.OpenMaya` only. No Qt, no package, no third-party imports.
- Tests: `tests/test_asretarget.py`, run with
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`.
  Pure functions take plain data (lists/dicts/strings) so no fake `cmds` is needed; follow `tests/test_retarget.py`.
- Holder node name: `MoCapConstraints`; switch attribute: `disableConstraints` (bool, keyable) — both spellings are AdvancedSkeleton's and must not change.
- Helper node prefixes: `asrtDriver_`, `asrtTarget_`.
- Maya is row-vector: `world = local · parent`, so a rest offset is `C_rest · B_rest⁻¹` and it goes on the helper's LOCAL matrix.
- Nothing writes keys; autoKey is forced off around every scene write and restored; every scene-touching entry point runs in one undo chunk.
- The live verify script runs in the animator's OPEN scene: register every created node's UUID as it is created, guard each teardown step on its own, and restore bind pose, autoKey, playback range, current frame and selection.

---

### Task 1: The drive table and `drive_plan`

**Files:**
- Create: `maya_asretarget.py`
- Test: `tests/test_asretarget.py`

**Interfaces:**
- Produces: `ROWS` (list of `(as_base, ue_base)`), `SIDES` (list of `(as_suffix, ue_suffix)`), `Drive` (namedtuple `control, bone, translate, rotate, offset`), `IK_ROWS`, `POLE_ROWS`, `ROOT_ROWS`, `drive_plan(controls, bones) -> (drives, missing)`.

- [ ] **Step 1: Write the failing test**

```python
import unittest

import maya_asretarget as ar

# The rig, measured 2026-09-04: 79 deform joints, and these are the controls
# that exist for them.  Sides as AdvancedSkeleton spells them.
FK_BASES = [
    "Spine1", "Spine2", "Spine3", "Spine4", "Spine5", "Neck", "NeckPart1", "Head",
    "Scapula", "Shoulder", "Elbow", "Wrist", "Hip", "Knee", "Ankle", "Toes",
    "ThumbFinger1", "ThumbFinger2", "ThumbFinger3",
]
for _f in ("Index", "Middle", "Ring", "Pinky"):
    for _i in (0, 1, 2, 3):
        FK_BASES.append("%sFinger%d" % (_f, _i))

CONTROLS = ["Main", "RootX_M"]
for _b in FK_BASES:
    for _s in ("_M", "_L", "_R"):
        CONTROLS.append("FK" + _b + _s)
for _s in ("_L", "_R"):
    CONTROLS += ["IKArm" + _s, "IKLeg" + _s, "IKToes" + _s,
                 "PoleArm" + _s, "PoleLeg" + _s]

# A full UE5 Manny's leaf names.
BONES = ["root", "pelvis", "neck_01", "neck_02", "head"]
BONES += ["spine_0%d" % i for i in range(1, 6)]
for _s in ("l", "r"):
    BONES += ["clavicle_" + _s, "upperarm_" + _s, "lowerarm_" + _s, "hand_" + _s,
              "thigh_" + _s, "calf_" + _s, "foot_" + _s, "ball_" + _s]
    for _f in ("index", "middle", "ring", "pinky"):
        BONES.append("%s_metacarpal_%s" % (_f, _s))
        BONES += ["%s_0%d_%s" % (_f, i, _s) for i in (1, 2, 3)]
    BONES += ["thumb_0%d_%s" % (i, _s) for i in (1, 2, 3)]


class TestDrivePlan(unittest.TestCase):

    def setUp(self):
        self.drives, self.missing = ar.drive_plan(CONTROLS, BONES)
        self.by_control = dict((d.control, d) for d in self.drives)

    def test_nothing_is_missing_on_a_full_rig_and_a_full_skeleton(self):
        self.assertEqual(self.missing, [])

    def test_every_control_is_driven_once(self):
        self.assertEqual(len(self.by_control), len(self.drives))

    def test_the_fk_controls_take_rotation_only_and_need_no_offset(self):
        d = self.by_control["FKShoulder_L"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("upperarm_l", False, True, False))

    def test_the_spine_is_one_to_one(self):
        for i in range(1, 6):
            self.assertEqual(self.by_control["FKSpine%d_M" % i].bone, "spine_0%d" % i)

    def test_the_neck_inbetween_takes_the_second_neck_bone(self):
        self.assertEqual(self.by_control["FKNeckPart1_M"].bone, "neck_02")

    def test_the_metacarpals_are_mapped(self):
        self.assertEqual(self.by_control["FKIndexFinger0_R"].bone, "index_metacarpal_r")

    def test_root_motion_goes_to_main_with_an_offset(self):
        d = self.by_control["Main"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("root", True, True, True))

    def test_the_pelvis_control_is_rootx_and_not_an_fk_control(self):
        d = self.by_control["RootX_M"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("pelvis", True, True, True))
        self.assertNotIn("FKRoot_M", self.by_control)

    def test_the_ik_ends_take_position_and_rotation_without_an_offset(self):
        self.assertEqual(self.by_control["IKLeg_R"].bone, "foot_r")
        for name in ("IKArm_L", "IKLeg_L"):
            d = self.by_control[name]
            self.assertEqual((d.translate, d.rotate, d.offset), (True, True, False))

    def test_the_toe_control_takes_rotation_only(self):
        d = self.by_control["IKToes_L"]
        self.assertEqual((d.bone, d.translate, d.rotate, d.offset),
                         ("ball_l", False, True, False))

    def test_the_poles_ride_the_upper_bone_by_position_through_an_offset(self):
        self.assertEqual(self.by_control["PoleLeg_L"].bone, "thigh_l")
        self.assertEqual(self.by_control["PoleArm_R"].bone, "upperarm_r")
        d = self.by_control["PoleLeg_R"]
        self.assertEqual((d.translate, d.rotate, d.offset), (True, False, True))

    def test_the_twist_joints_are_never_driven(self):
        for d in self.drives:
            self.assertNotIn("Part1", d.control.replace("NeckPart1", ""))
            self.assertNotIn("Part2", d.control)
            self.assertNotIn("twist", d.bone)

    def test_a_missing_source_bone_is_reported_and_skipped(self):
        bones = [b for b in BONES if b != "index_metacarpal_l"]
        drives, missing = ar.drive_plan(CONTROLS, bones)
        self.assertEqual(missing, [("FKIndexFinger0_L", "index_metacarpal_l")])
        self.assertNotIn("FKIndexFinger0_L", [d.control for d in drives])

    def test_a_missing_control_is_silently_skipped(self):
        controls = [c for c in CONTROLS if c != "FKNeckPart1_M"]
        drives, missing = ar.drive_plan(controls, BONES)
        self.assertEqual(missing, [])
        self.assertNotIn("FKNeckPart1_M", [d.control for d in drives])

    def test_a_ue4_schema_source_loses_only_what_it_lacks(self):
        # No metacarpals, spine stops at 03, no neck_02: the UE4 mannequin.
        bones = [b for b in BONES
                 if "metacarpal" not in b and b not in ("spine_04", "spine_05", "neck_02")]
        drives, missing = ar.drive_plan(CONTROLS, bones)
        names = [d.control for d in drives]
        self.assertIn("FKSpine3_M", names)
        self.assertNotIn("FKSpine4_M", names)
        self.assertEqual(len(missing), 8 + 2 + 1)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'maya_asretarget'`.

- [ ] **Step 3: Write the minimal implementation**

```python
"""Retarget: drive the AdvancedSkeleton rig from a second, animated UE5 skeleton.

Design: docs/superpowers/specs/2026-09-04-as-retarget-design.md

Run in Maya (Script Editor, Python tab):
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_asretarget
    maya_asretarget.report()      # read-only: what would be driven, from what
    maya_asretarget.connect()     # build it, from the selected source skeleton
    maya_asretarget.disconnect()  # the same as AdvancedSkeleton's own button
"""

import collections

# AdvancedSkeleton deform-joint base -> UE bone base.  The rig's own map
# (2026-09-04), minus the twist Part joints, which have no FK controls and are
# recomputed by the rig's twist network from the bones we drive.
ROWS = [
    ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"),
    ("Spine4", "spine_04"), ("Spine5", "spine_05"),
    ("Neck", "neck_01"), ("NeckPart1", "neck_02"), ("Head", "head"),
    ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"),
    ("Wrist", "hand"),
    ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"),
    ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
    ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"),
    ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
    ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"),
    ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
    ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"),
    ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
    ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"),
    ("ThumbFinger3", "thumb_03"),
    ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball"),
]
SIDES = [("_M", ""), ("_L", "_l"), ("_R", "_r")]

# The controls whose own rest frame is NOT the bone's frame: AdvancedSkeleton
# keeps them world-oriented on purpose (see the rig spec), so these go through
# an offset helper.  Root motion reaches `Main`, which is what the UE `root`
# bone follows -- the pelvis control takes the pelvis.
ROOT_ROWS = [("Main", "root"), ("RootX_M", "pelvis")]
# The IK end controls sit exactly on their bones with matching frames.
IK_ROWS = [("IKArm", "hand", True), ("IKLeg", "foot", True), ("IKToes", "ball", False)]
# The pole rides the UPPER bone's frame: the limb plane is fixed by its roll,
# and a pole point-constrained to the mid joint is degenerate on a straight limb.
POLE_ROWS = [("PoleArm", "upperarm"), ("PoleLeg", "thigh")]

Drive = collections.namedtuple("Drive", "control bone translate rotate offset")


def drive_plan(controls, bones):
    """Pure: what to constrain to what.

    controls -- names present in the rig's ControlSet
    bones    -- leaf names present in the source skeleton
    Returns (drives, missing), missing being [(control, bone)] rows skipped
    because the source has no such bone.
    """
    controls = set(controls)
    bones = set(bones)
    drives, missing = [], []

    def add(control, bone, translate, rotate, offset):
        if control not in controls:
            return
        if bone not in bones:
            missing.append((control, bone))
            return
        drives.append(Drive(control, bone, translate, rotate, offset))

    for control, bone in ROOT_ROWS:
        add(control, bone, True, True, True)
    for as_base, ue_base in ROWS:
        for as_side, ue_side in SIDES:
            add("FK" + as_base + as_side, ue_base + ue_side, False, True, False)
    for as_base, ue_base, translate in IK_ROWS:
        for as_side, ue_side in SIDES[1:]:
            add(as_base + as_side, ue_base + ue_side, translate, True, False)
    for as_base, ue_base in POLE_ROWS:
        for as_side, ue_side in SIDES[1:]:
            add(as_base + as_side, ue_base + ue_side, True, False, True)
    return drives, missing
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_asretarget.py tests/test_asretarget.py
git commit -m "feat(asretarget): the drive table, pure"
```

---

### Task 2: Source resolution and the refusals

**Files:**
- Modify: `maya_asretarget.py`
- Test: `tests/test_asretarget.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `top_joint(path, joint_paths) -> str or None`, `source_root_of(selection, joint_paths, rig_paths) -> (root, refusal)` where exactly one of the two is truthy.

- [ ] **Step 1: Write the failing test**

```python
class TestSourceRoot(unittest.TestCase):

    # The animator's scene: our rigged skeleton at |root, the AS rig under
    # |Group, and an imported clip whose top node Maya renamed.
    JOINTS = [
        "|root", "|root|pelvis", "|root|pelvis|spine_01",
        "|Group|MotionSystem|FKSystem|FKXSpine5_M",
        "|Manny_Skeleton_root", "|Manny_Skeleton_root|pelvis",
        "|Manny_Skeleton_root|pelvis|spine_01",
    ]
    RIG = ["|root", "|root|pelvis", "|root|pelvis|spine_01",
           "|Group|MotionSystem|FKSystem|FKXSpine5_M"]

    def test_the_top_joint_of_a_path_is_the_shallowest_joint_prefix(self):
        self.assertEqual(
            ar.top_joint("|Manny_Skeleton_root|pelvis|spine_01", self.JOINTS),
            "|Manny_Skeleton_root")

    def test_a_group_above_the_skeleton_is_not_the_top_joint(self):
        joints = ["|grp|root", "|grp|root|pelvis"]
        self.assertEqual(ar.top_joint("|grp|root|pelvis", joints), "|grp|root")

    def test_a_path_holding_no_joint_has_no_top_joint(self):
        self.assertIsNone(ar.top_joint("|persp", self.JOINTS))

    def test_any_joint_of_the_source_resolves_to_its_root(self):
        root, refusal = ar.source_root_of(
            ["|Manny_Skeleton_root|pelvis|spine_01"], self.JOINTS, self.RIG)
        self.assertEqual((root, refusal), ("|Manny_Skeleton_root", ""))

    def test_a_namespaced_source_works_the_same(self):
        joints = ["|clip:root", "|clip:root|clip:pelvis"]
        root, refusal = ar.source_root_of(["|clip:root|clip:pelvis"], joints, self.RIG)
        self.assertEqual((root, refusal), ("|clip:root", ""))

    def test_an_empty_selection_is_refused(self):
        root, refusal = ar.source_root_of([], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("select", refusal.lower())

    def test_a_selection_with_no_joint_is_refused(self):
        root, refusal = ar.source_root_of(["|persp"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("joint", refusal.lower())

    def test_our_own_rigged_skeleton_is_refused_by_name(self):
        root, refusal = ar.source_root_of(["|root|pelvis"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("|root", refusal)

    def test_the_rigs_own_internals_are_refused(self):
        root, refusal = ar.source_root_of(
            ["|Group|MotionSystem|FKSystem|FKXSpine5_M"], self.JOINTS, self.RIG)
        self.assertEqual(root, "")
        self.assertTrue(refusal)

    def test_two_different_sources_at_once_are_refused_and_both_named(self):
        joints = self.JOINTS + ["|second_root", "|second_root|pelvis"]
        root, refusal = ar.source_root_of(
            ["|Manny_Skeleton_root|pelvis", "|second_root|pelvis"], joints, self.RIG)
        self.assertEqual(root, "")
        self.assertIn("Manny_Skeleton_root", refusal)
        self.assertIn("second_root", refusal)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: FAIL — `AttributeError: module 'maya_asretarget' has no attribute 'top_joint'`.

- [ ] **Step 3: Write the minimal implementation**

```python
def top_joint(path, joint_paths):
    """Pure: the shallowest joint on `path`, or None. A group above the skeleton
    is not a joint, so `|grp|root|pelvis` answers `|grp|root`."""
    joint_paths = set(joint_paths)
    parts = [p for p in path.split("|") if p]
    for i in range(1, len(parts) + 1):
        candidate = "|" + "|".join(parts[:i])
        if candidate in joint_paths:
            return candidate
    return None


def source_root_of(selection, joint_paths, rig_paths):
    """Pure: which skeleton the animator means. Returns (root, refusal)."""
    if not selection:
        return "", "select any joint of the imported skeleton first"
    rig_paths = set(rig_paths)
    roots = []
    for path in selection:
        root = top_joint(path, joint_paths)
        if root and root not in roots:
            roots.append(root)
    if not roots:
        return "", "the selection holds no joint - select a bone of the imported skeleton"
    if len(roots) > 1:
        return "", "two skeletons selected (%s) - select bones of one only" % ", ".join(
            r.split("|")[-1] for r in roots)
    root = roots[0]
    if root in rig_paths or any(p == root or p.startswith(root + "|") for p in rig_paths):
        return "", ("%s is the rig's own skeleton - select the imported clip's "
                    "skeleton instead" % root)
    return root, ""
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: PASS, 23 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_asretarget.py tests/test_asretarget.py
git commit -m "feat(asretarget): resolve the source skeleton from the selection, pure"
```

---

### Task 3: The rest offset and the proportion check

**Files:**
- Modify: `maya_asretarget.py`
- Test: `tests/test_asretarget.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `offset_local(control_world, bone_world) -> list[16]`, `is_identity(matrix, tol=1e-6) -> bool`, `SEGMENTS` (list of `(a, b)` leaf-name pairs), `segment_lengths(positions) -> {name: float}`, `scale_warning(source_lengths, rig_lengths, tol=0.02) -> str`.

- [ ] **Step 1: Write the failing test**

```python
import math


class TestOffsetLocal(unittest.TestCase):

    IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def test_equal_frames_give_the_identity(self):
        m = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 5, 6, 7, 1]
        self.assertTrue(ar.is_identity(ar.offset_local(m, m)))

    def test_the_offset_reproduces_the_control_when_the_bone_stands_at_rest(self):
        # control 90 deg about Z at (1,2,3); bone unrotated at (1,2,3)
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = self.IDENT[:12] + [1, 2, 3, 1]
        local = ar.offset_local(ctrl, bone)
        self.assertFalse(ar.is_identity(local))
        # local * bone == ctrl  (row-vector: world = local * parent)
        import maya.api.OpenMaya as om
        got = list(om.MMatrix(local) * om.MMatrix(bone))
        for a, b in zip(got, ctrl):
            self.assertAlmostEqual(a, b, places=9)

    def test_it_is_not_the_other_order(self):
        ctrl = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 1]
        bone = [1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 4, 0, 0, 1]
        import maya.api.OpenMaya as om
        wrong = list(om.MMatrix(bone) * om.MMatrix(ar.offset_local(ctrl, bone)))
        self.assertFalse(all(abs(a - b) < 1e-9 for a, b in zip(wrong, ctrl)))


class TestScaleWarning(unittest.TestCase):

    def test_identical_proportions_warn_about_nothing(self):
        lengths = {"thigh_l": 40.0, "calf_l": 40.0, "upperarm_l": 30.0}
        self.assertEqual(ar.scale_warning(lengths, lengths), "")

    def test_a_two_percent_difference_is_tolerated(self):
        rig = {"thigh_l": 40.0}
        self.assertEqual(ar.scale_warning({"thigh_l": 40.6}, rig), "")

    def test_a_bigger_difference_names_the_segment_and_both_numbers(self):
        rig = {"thigh_l": 40.0, "calf_l": 40.0}
        msg = ar.scale_warning({"thigh_l": 50.0, "calf_l": 40.0}, rig)
        self.assertIn("thigh_l", msg)
        self.assertIn("50.0", msg)
        self.assertIn("40.0", msg)
        self.assertNotIn("calf_l", msg)

    def test_a_segment_the_source_lacks_is_not_a_warning(self):
        self.assertEqual(ar.scale_warning({}, {"thigh_l": 40.0}), "")

    def test_segment_lengths_come_from_positions(self):
        pos = {"thigh_l": (0.0, 0.0, 0.0), "calf_l": (0.0, -40.0, 0.0),
               "foot_l": (0.0, -40.0, 30.0)}
        lengths = ar.segment_lengths(pos)
        self.assertAlmostEqual(lengths["thigh_l"], 40.0, places=6)
        self.assertAlmostEqual(lengths["calf_l"], 30.0, places=6)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: FAIL — no attribute `is_identity`.

- [ ] **Step 3: Write the minimal implementation**

```python
import maya.api.OpenMaya as om

# Pose-independent proportions: a joint's local translation does not change with
# the pose, so these lengths compare two skeletons without posing either.
SEGMENTS = [("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("thigh_r", "calf_r"),
            ("calf_r", "foot_r"), ("upperarm_l", "lowerarm_l"),
            ("lowerarm_l", "hand_l"), ("upperarm_r", "lowerarm_r"),
            ("lowerarm_r", "hand_r"), ("pelvis", "spine_01"), ("neck_01", "head")]


def offset_local(control_world, bone_world):
    """Pure: the rest offset as a LOCAL matrix, C_rest * B_rest^-1.

    Maya is row-vector (world = local * parent), so a helper carrying this as
    its local matrix under a parent that holds the source bone's world matrix
    stands exactly where the control stands at rest.
    """
    return list(om.MMatrix(control_world) * om.MMatrix(bone_world).inverse())


def is_identity(matrix, tol=1e-6):
    """Pure: is this 16-float matrix the identity within tol?"""
    ident = om.MMatrix()
    return all(abs(a - b) <= tol for a, b in zip(list(om.MMatrix(matrix)), list(ident)))


def segment_lengths(positions):
    """Pure: {first bone of the pair: distance} for every SEGMENTS pair present."""
    out = {}
    for a, b in SEGMENTS:
        if a in positions and b in positions:
            pa, pb = positions[a], positions[b]
            out[a] = math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
    return out


def scale_warning(source_lengths, rig_lengths, tol=0.02):
    """Pure: name the segments whose length differs by more than tol, or ""."""
    bad = []
    for name in sorted(rig_lengths):
        if name not in source_lengths:
            continue
        rig, src = rig_lengths[name], source_lengths[name]
        if rig > 1e-6 and abs(src - rig) / rig > tol:
            bad.append("%s %.1f vs %.1f" % (name, src, rig))
    if not bad:
        return ""
    return ("the source's proportions differ (source vs rig): " + ", ".join(bad) +
            " - a rotation copy will not land the feet; scale the source first")
```

Add `import math` at the top of the module beside `import collections`.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: PASS, 31 tests.

- [ ] **Step 5: Commit**

```bash
git add maya_asretarget.py tests/test_asretarget.py
git commit -m "feat(asretarget): the rest offset and the proportion check, pure"
```

---

### Task 4: `connect`, `disconnect`, `report`

**Files:**
- Modify: `maya_asretarget.py`
- Test: `tests/test_asretarget.py` (a gone-test and a source-reading test with a fake `cmds`)

**Interfaces:**
- Consumes: `drive_plan`, `source_root_of`, `offset_local`, `is_identity`, `segment_lengths`, `scale_warning`.
- Produces: `HOLDER`, `SWITCH`, `DRIVER_PREFIX`, `TARGET_PREFIX`, `rig_paths() -> list[str]`, `source_bones(root) -> {leaf: long path}`, `connect(source_root=None) -> str`, `disconnect() -> str`, `report(source_root=None) -> str`.

- [ ] **Step 1: Write the failing test**

```python
class FakeCmds(object):
    """Only what source_bones and rig_paths ask for."""

    def __init__(self, joints, relatives):
        self._joints = joints
        self._relatives = relatives

    def ls(self, *args, **kwargs):
        if kwargs.get("type") == "joint":
            return list(self._joints)
        return []

    def listRelatives(self, node, **kwargs):
        return list(self._relatives.get(node, []))

    def objExists(self, node):
        return node in self._joints


class TestSourceBones(unittest.TestCase):

    def setUp(self):
        self._real = ar.cmds
        joints = ["|clip:root", "|clip:root|clip:pelvis", "|clip:root|clip:pelvis|clip:spine_01"]
        ar.cmds = FakeCmds(joints, {"|clip:root": joints[1:]})

    def tearDown(self):
        ar.cmds = self._real

    def test_the_leaf_name_drops_the_namespace(self):
        bones = ar.source_bones("|clip:root")
        self.assertEqual(sorted(bones), ["pelvis", "root", "spine_01"])
        self.assertEqual(bones["pelvis"], "|clip:root|clip:pelvis")


class TestNames(unittest.TestCase):

    def test_the_holder_and_switch_are_advancedskeletons_own_spelling(self):
        self.assertEqual(ar.HOLDER, "MoCapConstraints")
        self.assertEqual(ar.SWITCH, "disableConstraints")

    def test_no_bake_of_our_own(self):
        # The bake is AdvancedSkeleton's button; a second implementation would
        # drift from it. Deliberately absent.
        self.assertFalse(hasattr(ar, "bake"))
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_asretarget -v`
Expected: FAIL — no attribute `HOLDER`.

- [ ] **Step 3: Write the implementation**

```python
import maya.cmds as cmds

HOLDER = "MoCapConstraints"          # AdvancedSkeleton's own node name
SWITCH = "disableConstraints"        # ... and its own attribute
DRIVER_PREFIX = "asrtDriver_"
TARGET_PREFIX = "asrtTarget_"


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def source_bones(root):
    """{leaf name without namespace: long path} for the source subtree."""
    paths = [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or [])
    return dict((leaf(p), p) for p in paths)


def rig_paths():
    """Long paths that belong to the rig: everything under Group, plus the UE
    skeleton our DeformationSystem drives (its joints carry our constraints)."""
    out = []
    for j in cmds.ls(type="joint", long=True) or []:
        if j.startswith("|Group|") or j == "|Group":
            out.append(j)
            continue
        if cmds.listRelatives(j, children=True, type="constraint"):
            out.append(j)
    return out


def _holder():
    if not cmds.objExists(HOLDER):
        cmds.createNode("transform", name=HOLDER, skipSelect=True)
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(HOLDER + "." + attr, lock=True)
    if not cmds.attributeQuery(SWITCH, node=HOLDER, exists=True):
        cmds.addAttr(HOLDER, longName=SWITCH, attributeType="bool", keyable=True)
    return HOLDER


def _register(constraints):
    """AdvancedSkeleton's contract: its Bake walks these, its Disconnect deletes them."""
    for c in constraints:
        cmds.connectAttr(HOLDER + "." + SWITCH, c + ".nodeState", force=True)


def _helper(drive, bone_path):
    """Driver (follows the source bone 1:1) + target (holds the rest offset)."""
    driver = cmds.createNode("transform", name=DRIVER_PREFIX + drive.control,
                             parent=HOLDER, skipSelect=True)
    made = [cmds.pointConstraint(bone_path, driver)[0],
            cmds.orientConstraint(bone_path, driver)[0]]
    target = cmds.createNode("transform", name=TARGET_PREFIX + drive.control,
                             parent=driver, skipSelect=True)
    local = offset_local(cmds.getAttr(drive.control + ".worldMatrix[0]"),
                         cmds.getAttr(_rig_bone(drive) + ".worldMatrix[0]"))
    cmds.xform(target, objectSpace=True, matrix=local)
    return target, made


def _rig_bone(drive):
    """Our own UE bone for this drive's source bone -- the rest reference."""
    return RIG_BONES[drive.bone]
```

The rest of `connect()` (full body, in order):

```python
def connect(source_root=None):
    global RIG_BONES
    if not cmds.objExists("ControlSet") or not cmds.objExists("Main"):
        return "no AdvancedSkeleton rig in this scene (ControlSet/Main missing)"
    if cmds.objExists(HOLDER):
        return ("%s already exists - press Disconnect MoCap Skeleton in "
                "AdvancedSkeleton first, or run disconnect()" % HOLDER)
    joints = cmds.ls(type="joint", long=True) or []
    rig = rig_paths()
    if source_root is None:
        source_root, refusal = source_root_of(
            cmds.ls(selection=True, long=True) or [], joints, rig)
        if refusal:
            return refusal
    ue_root = _rig_skeleton_root(rig)
    RIG_BONES = dict((leaf(p), p) for p in
                     [ue_root] + (cmds.listRelatives(ue_root, ad=True, type="joint",
                                                     fullPath=True) or []))
    bones = source_bones(source_root)
    drives, missing = drive_plan(cmds.sets("ControlSet", q=True) or [], list(bones))
    if not drives:
        return "no bone of %s matches this rig - is it a UE5 skeleton?" % leaf(source_root)
    warn = scale_warning(
        segment_lengths(dict((n, cmds.xform(p, q=True, ws=True, t=True))
                             for n, p in bones.items())),
        segment_lengths(dict((n, cmds.xform(p, q=True, ws=True, t=True))
                             for n, p in RIG_BONES.items())))

    auto = cmds.autoKeyframe(q=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="AS retarget connect")
    made = []
    try:
        _holder()
        for drive in drives:
            target = bones[drive.bone]
            if drive.offset:
                target, helpers = _helper(drive, bones[drive.bone])
                made += helpers
            if drive.translate:
                made.append(cmds.pointConstraint(target, drive.control)[0])
            if drive.rotate:
                made.append(cmds.orientConstraint(target, drive.control)[0])
        _register(made)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto)

    lines = ["retarget connected: %d controls driven from %s"
             % (len(drives), leaf(source_root))]
    if missing:
        lines.append("no source bone for: " + ", ".join(c for c, _ in missing))
    if warn:
        lines.append(warn)
    lines.append("playback range %g..%g; the source's keys run %s"
                 % (cmds.playbackOptions(q=True, min=True),
                    cmds.playbackOptions(q=True, max=True),
                    _source_key_range(bones)))
    lines.append("now: AdvancedSkeleton > MoCap Matcher > Bake, then Disconnect")
    return "\n".join(lines)
```

Plus the three small helpers `_rig_skeleton_root(rig_paths)` (the shallowest
path in `rig_paths` that is not under `|Group`), `_source_key_range(bones)`
(`cmds.keyframe` min/max over the source joints, or `"no keys"`), `disconnect()`
(delete the constraints found through `HOLDER.SWITCH`, then the holder if it
still exists — trap 18), and `report()` (everything `connect` computes, printed,
with no scene write).

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
Expected: PASS — the new module's tests plus the existing suite unchanged.

- [ ] **Step 5: Commit**

```bash
git add maya_asretarget.py tests/test_asretarget.py
git commit -m "feat(asretarget): connect, disconnect and report"
```

---

### Task 5: The live proof

**Files:**
- Create: `docs/superpowers/plans/verify_asretarget.py`

**Interfaces:**
- Consumes: the whole module.
- Produces: a gate list printed as `PASS/FAIL gate NN`, ending in `RESULT: N of M gates failed`.

- [ ] **Step 1: Write the script**

Phases, in this order, each gate measured rather than asserted from theory:

1. **Fixture.** Duplicate the rig's UE skeleton into a namespace of its own
   (`asrtVerify:`), renaming every joint to its plain leaf name inside that
   namespace so the source is an exact twin; register every created node's UUID
   as it is created (trap 47). Key a synthetic take on it: `root` translated
   100 cm in Z over 20 frames, `spine_03` bent 25°, `thigh_l`/`calf_l` flexed
   40°/-50°, `upperarm_r` raised 35°, `index_01_l` curled 30°.
2. **Refusals** (gates 1-5): no selection; a non-joint selection; our own rigged
   skeleton; a second `connect()` while `MoCapConstraints` stands; and
   `disconnect()` with nothing connected.
3. **The build** (gates 6-12): every planned drive present with the expected
   constraint types and source; each helper's target world matrix equal to its
   control's rest world matrix while the source stands at frame 0 of the take
   (this is what makes the analytic offset a measurement rather than a claim);
   every constraint's `nodeState` connected to `MoCapConstraints.disableConstraints`;
   every helper a child of `MoCapConstraints`.
4. **The transfer** (gates 13-18): over sampled frames, our UE bones against the
   source's — `spine_03`, `head`, `index_01_l` and every FK-driven bone exact
   (world matrix, 1e-4); `hand_r`, `foot_l`, `ball_l` exact; `calf_l` within 1°
   in IK; `root` carrying the source's root motion (100 cm, not the pelvis).
5. **The bake** (gates 19-22): set the playback range to the take, run
   `asMoCapMatcherBake` through `maya.mel`, then `asMoCapMatcherDisconnect`;
   gate that keys landed on the driven controls, that no node of ours survives
   (holder, drivers, targets, constraints), and that **the rig still reproduces
   the take** on sampled frames with the source deleted.
6. **Teardown** (gate 23): the fixture deleted by UUID, the rig back at its bind
   pose (`asGoToBuildPose`), and autoKey, range, frame and selection restored.

- [ ] **Step 2: Send it through the bridge and read the output**

Run it in the animator's Maya over the command port. Expected:
`RESULT: 0 of 23 gates failed`.

- [ ] **Step 3: Fix what the gates find, re-run until green**

Every failure is either the code or the gate's own expectation — decide by
measuring, and never by loosening a tolerance.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_asretarget.py
git commit -m "test(asretarget): live gates, green in the animator's scene"
```

---

### Task 6: Write it down

**Files:**
- Modify: `CLAUDE.md` (a section under the AdvancedSkeleton rig section)
- Modify: `docs/superpowers/specs/2026-09-04-as-retarget-design.md` (measured numbers, and any decision the live run reversed)

- [ ] **Step 1: Add the CLAUDE.md section**

What it is, the animator's loop, the `MoCapConstraints` contract that makes
AdvancedSkeleton's Bake work, the four measurements the design rests on, the
entry points, and every trap the live run paid for.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-09-04-as-retarget-design.md
git commit -m "docs(asretarget): the retarget setup, and what the live run measured"
```

## Self-Review

**Spec coverage.** The vendor-Bake contract → Task 4 (`_register`, `HOLDER`,
`SWITCH`) and Task 5 phase 5. The no-offset rule and the offset helper → Tasks 1
and 3, gated in Task 5 phase 3. The drive table including poles and root motion →
Task 1. Source resolution and every refusal → Task 2, gated in phase 2. The
proportion warning → Task 3. The range report → Task 4. The verification →
Task 5. The "deliberately not done" list needs no task, but the *no bake of our
own* half is pinned by a gone-test in Task 4.

**Placeholders.** None: every step carries its test code or its exact command.
Task 4's step 3 quotes the full `connect()` body and names the three small
helpers with their exact behaviour; Task 5 lists its gates individually.

**Type consistency.** `Drive(control, bone, translate, rotate, offset)` is used
with those field names in Tasks 1, 4 and 5. `drive_plan(controls, bones)` returns
`(drives, missing)` everywhere. `offset_local(control_world, bone_world)` takes
16-float lists in Task 3 and is fed `cmds.getAttr(".worldMatrix[0]")` in Task 4,
which is exactly that. `source_root_of(selection, joint_paths, rig_paths)`
returns `(root, refusal)` in Task 2 and is unpacked that way in Task 4.

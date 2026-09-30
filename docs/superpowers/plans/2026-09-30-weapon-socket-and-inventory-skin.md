# One Weapon Socket and the Inventory Skin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every catalog weapon sits correctly in every rig's fist at zero grip, and the inventory window wears the hub's own look.

**Architecture:**
- A fixed socket turn `catalog.SOCKET_TURN = (90, 0, 0)` is composed with each row's own frame (`bonedrive.socket_frame`) and stored on the weapon node. Everything downstream already reads the node's frame.
- The Creep's two weapon bones are turned in place into UE's convention by a mayapy script.
- Remembered grips are re-expressed once (`grips.migrate`).
- The inventory's palette becomes `maya_hubstyle.TOKENS` and its paint is redone in the hub's cards.

**Tech Stack:** Maya 2027 mayapy, `maya.cmds`, OpenMaya 2.0, PySide6 via `maya_hubqt.qt()`, stdlib `unittest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-30-weapon-socket-and-inventory-skin-design.md`.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` from the repo root, with `$env:QT_QPA_PLATFORM='offscreen'`. No system Python, no pytest.
- Verification runs in mayapy STANDALONE, or in a disposable Maya (scratch `MAYA_APP_DIR`, port 7003, killed afterwards). Never in the animator's scene.
- Row vectors throughout: `world = grip · frame · bone`.
- `SOCKET_TURN = (90.0, 0.0, 0.0)`. The migration gate optionVar is `mayaSceneSetup_gripSocket`.
- Leave the other session's uncommitted `CLAUDE.md` hunk (the Orc D 1P FBX lines) and the untracked `docs/superpowers/plans/export_orc_d_1p_fbx.py` alone. Stage only our hunks (`git apply --cached`).
- Never push without asking.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Write them to a file and use `git commit -F`.

---

### Task 1: The socket turn, composed into every weapon's frame

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py` (add `SOCKET_TURN` beside `WEAPONS`)
- Modify: `SkeldarAnim/maya_scenesetup/bonedrive.py` (add `socket_frame` after `unframing`)
- Modify: `SkeldarAnim/maya_scenesetup/attach.py:354` (store the composed frame)
- Modify: `SkeldarAnim/maya_scenesetup/grips.py:130-132` (the mirror uses the composed frame)
- Test: `tests/test_scenesetup_bonedrive.py`, `tests/test_scenesetup_attach.py`, `tests/test_scenesetup_hands.py`

**Interfaces:**
- Produces:
  - `catalog.SOCKET_TURN: tuple[float, float, float] = (90.0, 0.0, 0.0)`;
  - `bonedrive.socket_frame(frame=(0,0,0)) -> tuple[float,float,float]`: the XYZ euler of R(frame) · R(SOCKET_TURN), rounded to 9 decimals, with -0.0 cleared.

- [ ] **Step 1: Failing tests.** In `tests/test_scenesetup_bonedrive.py` add:

```python
class SocketFrame(unittest.TestCase):
    """2026-09-30: every rig's weapon bone is UE's (grip line +Z, palm -Y),
    every model lies along +Y - one quarter turn between them."""

    def _m(self, rotate):
        return om.MMatrix(bonedrive.matrix_of(rotate, (0.0, 0.0, 0.0)))

    def test_the_turn(self):
        self.assertEqual(catalog.SOCKET_TURN, (90.0, 0.0, 0.0))

    def test_an_unframed_model_takes_the_turn_alone(self):
        self.assertEqual(bonedrive.socket_frame((0.0, 0.0, 0.0)), (90.0, 0.0, 0.0))
        self.assertEqual(bonedrive.socket_frame(), (90.0, 0.0, 0.0))

    def test_the_blade_goes_along_the_bones_z_and_the_thickness_along_minus_y(self):
        m = self._m(bonedrive.socket_frame())
        self.assertAlmostEqual((om.MVector(0, 1, 0) * m - om.MVector(0, 0, 1)).length(), 0.0, 9)
        self.assertAlmostEqual((om.MVector(0, 0, 1) * m - om.MVector(0, -1, 0)).length(), 0.0, 9)

    def test_a_models_own_frame_turns_first(self):
        """The Creep Sword's 45 about its own blade, then the socket turn."""
        want = self._m((0.0, 45.0, 0.0)) * self._m(catalog.SOCKET_TURN)
        got = self._m(bonedrive.socket_frame((0.0, 45.0, 0.0)))
        self.assertLess(max(abs(a - b) for a, b in zip(want, got)), 1e-9)
```

(`catalog` and `om` imports at the top of that test module if missing: `from maya_scenesetup import catalog`, `import maya.api.OpenMaya as om`.)

In `tests/test_scenesetup_attach.py`:
- give `FakeBonedrive` the real composition:
  `socket_frame = staticmethod(bonedrive.socket_frame)`;
- change `test_the_entrys_frame_goes_on_the_node` to expect `(90.0, 0.0, 0.0)`;
- change `test_a_framed_entry_writes_its_frame` to expect `bonedrive.socket_frame((0.0, 45.0, 0.0))`.

Both docstrings get the new rule («the catalog's frame composed with the socket turn»).

In `tests/test_scenesetup_hands.py`, `test_an_undialled_left_grip_is_the_right_ones_mirror`: the third argument seen by `mirror_grip` becomes `(90.0, 0.0, 0.0)` (Entry's frame is the identity).

- [ ] **Step 2: Run them, expect FAIL** (`AttributeError: socket_frame` / `SOCKET_TURN`).

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_bonedrive tests.test_scenesetup_attach tests.test_scenesetup_hands`

- [ ] **Step 3: Implement.**

`catalog.py`, right after the `WEAPONS` list:

```python
# 2026-09-30, «по умолчанию все виды оружия вставлялись в руку правильно без
# офсетов»: every rig's weapon bone is UE's weapon_r (measured: the grip line
# pinky -> index along its +Z, the palm normal along -Y, on Manny and the Orc D;
# the Creep's were turned to match), while every row above lies in its model's
# own axes (blade +Y, width X, thickness Z). This quarter turn takes the one
# into the other; a row's `frame` is the model's OWN extra turn before it (the
# Creep Sword's 45 about its blade). bonedrive.socket_frame composes the two.
SOCKET_TURN = (90.0, 0.0, 0.0)
```

`bonedrive.py`, after `unframing`:

```python
def socket_frame(frame=(0.0, 0.0, 0.0)):
    """A catalog row's frame as the node carries it: R(frame) . R(SOCKET_TURN),
    an XYZ euler in degrees. Pure.

    The row's frame turns the model in its own axes first; the socket turn
    then takes the model's axes (blade +Y) into a UE weapon bone's (grip
    line +Z) - catalog.SOCKET_TURN, 2026-09-30.
    """
    from maya_scenesetup import catalog
    product = (om.MMatrix(matrix_of(frame, (0.0, 0.0, 0.0)))
               * om.MMatrix(matrix_of(catalog.SOCKET_TURN, (0.0, 0.0, 0.0))))
    euler = (om.MTransformationMatrix(product).rotation(asQuaternion=False)
             .reorder(om.MEulerRotation.kXYZ))
    return tuple(round(math.degrees(v), 9) + 0.0 for v in (euler.x, euler.y, euler.z))
```

(If `bonedrive` already imports `catalog` at module level, use that and drop the local import. Check first with `grep -n "^from maya_scenesetup import" bonedrive.py`. bonedrive is a leaf, and catalog is stdlib-only, so the import cannot cycle.)

`attach.py:354` becomes:

```python
    bonedrive.store_frame(weapon, bonedrive.socket_frame(
        getattr(entry, "frame", (0.0, 0.0, 0.0))))
```

`grips.py` `for_hand`: replace `getattr(entry, "frame", (0.0, 0.0, 0.0))` with `bonedrive.socket_frame(getattr(entry, "frame", (0.0, 0.0, 0.0)))`.

`store_frame`'s "identity writes nothing" rule stays. A composed frame is never the identity now, so every new weapon node carries `mayaWeaponFrameRotate`.

- [ ] **Step 4: Run the three modules, expect PASS**, then the whole suite (other tests may assert the identity frame; fix them to the composed one, never loosen them).

- [ ] **Step 5: Commit.** Message: `feat(weapons): one socket turn - every model into a UE weapon bone at zero grip`.

---

### Task 2: The remembered grips carried across once

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/grips.py` (add `rebased`, `frame_for_key`, `migrate`, `MIGRATED`, call `migrate()` at the top of `stored`)
- Modify: `SkeldarAnim/maya_scenesetup/window.py:279-280` (`_remember` rebases a grip read off an older weapon node) and its two callers (607, 674) pass the weapon
- Test: `tests/test_scenesetup_hands.py`

**Interfaces:**
- Consumes: `bonedrive.socket_frame`, `bonedrive.matrix_of`, `bonedrive.grip_between`, `bonedrive.frame_of`.
- Produces:
  - `grips.MIGRATED = "mayaSceneSetup_gripSocket"`;
  - `grips.rebased(rotate, translate, from_frame, to_frame) -> (rotate, translate)`, where G_new = G · R(from) · R(to)⁻¹;
  - `grips.frame_for_key(key) -> tuple` (the catalog row's own frame, a trailing `_L` stripped; identity when unknown);
  - `grips.migrate() -> int` (the count re-expressed; 0 and nothing written once `MIGRATED` exists).

- [ ] **Step 1: Failing tests.** Extend `FakeVars`:
  - it answers `list=True` with its keys;
  - its constructor takes `migrated=True`, which adds `grips.MIGRATED: 1`, so every existing test runs past the gate unchanged.

Add:

```python
class Migration(unittest.TestCase):
    """2026-09-30: a grip dialled against the old zero keeps the weapon where
    the animator put it - their (90, 0, 0) becomes exactly 0 0 0."""

    def setUp(self):
        self.real = grips.cmds
        self.addCleanup(setattr, grips, "cmds", self.real)

    def test_rebased_undoes_the_old_quarter_turn(self):
        rotate, translate = grips.rebased((90, 0, 0), (0, 0, 0), (0, 0, 0),
                                          (90, 0, 0))
        self.assertTrue(close(rotate, (0, 0, 0), 1e-9) and close(translate, (0, 0, 0), 1e-9))

    def test_rebased_keeps_the_world(self):
        g, f_old, f_new = ((10, -20, 35), (1.5, -2, 4)), (0, 45, 0), None
        f_new = bonedrive.socket_frame(f_old)
        r, t = grips.rebased(g[0], g[1], f_old, f_new)
        before = om.MMatrix(bonedrive.matrix_of(*g)) * om.MMatrix(bonedrive.matrix_of(f_old, (0, 0, 0)))
        after = om.MMatrix(bonedrive.matrix_of(r, t)) * om.MMatrix(bonedrive.matrix_of(f_new, (0, 0, 0)))
        self.assertLess(max(abs(a - b) for a, b in zip(before, after)), 1e-9)

    def test_the_frame_of_a_key(self):
        self.assertEqual(grips.frame_for_key("Creep_Sword"), (0.0, 45.0, 0.0))
        self.assertEqual(grips.frame_for_key("Creep_Sword_L"), (0.0, 45.0, 0.0))
        self.assertEqual(grips.frame_for_key("LongSword_02"), (0.0, 0.0, 0.0))
        self.assertEqual(grips.frame_for_key("SomeFile"), (0.0, 0.0, 0.0))

    def test_migrate_once_every_hand_and_the_legacy_name(self):
        grips.cmds = FakeVars({
            "mayaSceneSetup_offset_LongSword_02": [90, 0, 0, 0, 0, 0],
            "mayaSceneSetup_offset_Dagger_01_L": [90, 0, 0, 1, 0, 0],
            "mayaWeapons_offset_Spear_03": [90, 0, 0, 0, 0, 0],
            "mayaSceneSetup_offset_Broken": [1, 2],
            "somethingElse": [90, 0, 0, 0, 0, 0]}, migrated=False)
        self.assertEqual(grips.migrate(), 3)
        v = grips.cmds.vars
        self.assertTrue(close(v["mayaSceneSetup_offset_LongSword_02"], (0,) * 6, 1e-9))
        self.assertTrue(close(v["mayaWeapons_offset_Spear_03"], (0,) * 6, 1e-9))
        self.assertTrue(close(v["mayaSceneSetup_offset_Dagger_01_L"][:3], (0, 0, 0), 1e-9))
        self.assertEqual(v["mayaSceneSetup_offset_Broken"], [1, 2])
        self.assertEqual(v["somethingElse"], [90, 0, 0, 0, 0, 0])
        self.assertIn(grips.MIGRATED, v)
        v["mayaSceneSetup_offset_LongSword_02"] = [90, 0, 0, 0, 0, 0]
        self.assertEqual(grips.migrate(), 0)
        self.assertEqual(v["mayaSceneSetup_offset_LongSword_02"], [90, 0, 0, 0, 0, 0])

    def test_the_first_read_migrates(self):
        grips.cmds = FakeVars({"mayaSceneSetup_offset_LongSword_02":
                               [90, 0, 0, 0, 0, 0]}, migrated=False)
        rotate, _t = grips.stored("LongSword_02")
        self.assertTrue(close(rotate, (0, 0, 0), 1e-9))
```

`close(a, b, tol)` already exists in that module: it compares element-wise. A value that holds a nested tuple is flattened first; for the translate row use the stored six numbers. For the left dagger, [1,0,0] is translated along X before the turn. With the rotation undone, the translate row becomes (1, 0, 0)·Rx(−90) = (1, 0, 0), so also assert `close(v[...][3:], (1, 0, 0), 1e-9)`.

- [ ] **Step 2: Run, expect FAIL** (`AttributeError: rebased`).

- [ ] **Step 3: Implement in `grips.py`:**

```python
MIGRATED = "mayaSceneSetup_gripSocket"      # 2026-09-30: grips re-expressed once
_PREFIXES = ("mayaSceneSetup_offset_", "mayaWeapons_offset_")


def rebased(rotate, translate, from_frame, to_frame):
    """A grip dialled under `from_frame`, re-expressed under `to_frame` so the
    weapon stands where it stood: G . R(from) . R(to)^-1. Pure."""
    child = (om.MMatrix(bonedrive.matrix_of(rotate, translate))
             * om.MMatrix(bonedrive.matrix_of(from_frame, (0.0, 0.0, 0.0))))
    return bonedrive.grip_between(tuple(child),
                                  bonedrive.matrix_of(to_frame, (0.0, 0.0, 0.0)))


def frame_for_key(key):
    """The catalog row's own frame for a remembered key (a left hand's `_L`
    stripped); the identity for a file the catalog does not know."""
    for candidate in (key, key[:-2] if key.endswith("_L") else None):
        entry = catalog.by_key(candidate) if candidate else None
        if entry is not None:
            return tuple(float(v) for v in getattr(entry, "frame", (0.0, 0.0, 0.0)))
    return (0.0, 0.0, 0.0)


def migrate():
    """Every remembered grip re-expressed ONCE for the socket turn (2026-09-30):
    dialled against R(frame) . bone, kept where it stood under
    socket_frame(frame) . bone. Gated by MIGRATED, written after the pass."""
    if cmds.optionVar(exists=MIGRATED):
        return 0
    count = 0
    for name in cmds.optionVar(list=True) or []:
        prefix = [p for p in _PREFIXES if name.startswith(p)]
        if not prefix:
            continue
        values = cmds.optionVar(query=name)
        try:
            numbers = [float(v) for v in values]
        except (TypeError, ValueError):
            continue
        if len(numbers) != 6:
            continue
        frame = frame_for_key(name[len(prefix[0]):])
        rotate, translate = rebased(numbers[:3], numbers[3:], frame,
                                    bonedrive.socket_frame(frame))
        cmds.optionVar(clearArray=name)
        for value in pack(rotate, translate):
            cmds.optionVar(floatValueAppend=(name, value))
        count += 1
    cmds.optionVar(intValue=(MIGRATED, 1))
    return count
```

Then `stored()` begins with `migrate()`. `FakeVars.optionVar` must also accept `intValue=(name, v)` by storing it, and `list=True` by returning `list(self.vars)`.

`window.py`: `_remember(entry, rotate, translate, weapon=None)`. When `weapon` exists and its node frame (`bonedrive.frame_of(weapon)`) differs from `bonedrive.socket_frame(entry.frame)` by more than 1e-6 on any component, remember `grips.rebased(rotate, translate, node_frame, socket_frame(entry.frame))` instead. This covers a weapon added before the change: its fields read against its own identity frame. Pass `weapon` from both callers (lines 607 and 674: `_remember(entry, rotate, translate, weapon)`). Add a test in the Weapons-section block of `test_scenesetup_hands.py`: with a fake `frame_of` answering (0,0,0) and fields (90,0,0), what gets remembered is 0 0 0 (use the existing `HandCmds` fakes; stub `window.bonedrive.frame_of` and restore it in `addCleanup`).

- [ ] **Step 4: Run `tests.test_scenesetup_hands`, then the whole suite. Expect PASS.**

- [ ] **Step 5: Commit.** Message: `feat(weapons): remembered grips carried onto the socket turn once`.

---

### Task 3: The Creep's weapon bones into UE's convention

**Files:**
- Create: `docs/superpowers/plans/make_creep_weapon_sockets.py`
- Modify (by running it): `SkeldarAnim/assets/Creep_Rig.ma`, `SkeldarAnim/assets/Creep_Skeleton.ma`

**Interfaces:**
- Consumes: the layout script's helpers, copied (not imported: that script runs on import): `wm`, `mdiff`, `meshes`, `snapshot`, `drift`, `bind_error`, `whole_bind_pose`, `cut_and_check`.
- Produces: both Creep assets with `weapon_r`'s knuckle line along its +Z and `weapon_l`'s along its −Z. Everything else is unchanged.

- [ ] **Step 1: Back up the two assets** to the scratchpad (`Copy-Item`), so the verify can compare against them.

- [ ] **Step 2: Write the script.** Docstring: the why, the spec, idempotence. Body per asset:
  1. open (`executeScriptNodes=False`), find the root (`|Armature|root`), `before = snapshot()`;
  2. for each side (`r`: Q = Rx(−90), knuckles want +Z; `l`: Q = Rx(+90), knuckles want −Z):
     - measure `k` = the knuckle line pinky_01 → index_01 in the bone's axes (the rows of its world matrix);
     - if `abs(k.z) > 0.9` and its sign is the wanted one, skip;
     - elif `abs(k.y) > 0.9`, the new local = Q · old local (`om.MMatrix(bonedrive.matrix_of(q_rot, (0,0,0))) * om.MMatrix(cmds.xform(bone, q=True, matrix=True, objectSpace=True))`), and write only the rotate channels (the XYZ euler of that product, `rotateOrder` 0 asserted, jointOrient asserted zero);
     - else raise, naming the bone and `k`;
     - afterwards re-measure and assert the knuckles lie along the wanted ±Z (> 0.99 on the bind pose's fist; the table says 0.995).
  3. For every skinCluster in which the bone is an influence, set that index's `bindPreMatrix` to `wm(bone).inverse()`.
  4. `whole_bind_pose(joints, null)`.
  5. Assert:
     - every OTHER joint's world matrix is unchanged (< 1e-9);
     - every vertex is unchanged (< 1e-4);
     - `bind_error() < 1e-4`;
     - the bone's position is unchanged (< 1e-9);
     - on the rig, the Main / RootX_M pose-and-back check from the layout script.
  6. Save as `.ma` in place, `cut_and_check`, print the MB.

- [ ] **Step 3: Run it** (`mayapy make_creep_weapon_sockets.py`). Expect for both assets: turned r/l, drift 0, bind 0, saved. **Run it a second time**, expecting "already in UE's convention" for both bones and nothing else changed except the file's timestamp. Skip the save when nothing changed.

- [ ] **Step 4: Re-run `measure_fist.py`** (scratchpad). Expect the Creep's knuckle line along +Z in `weapon_r` and −Z in `weapon_l`.

- [ ] **Step 5: Commit** the script and both assets. Message: `feat(creep): its weapon bones in UE's orientation - one socket for every rig`.

---

### Task 4: The proof — `verify_weapon_socket.py`, standalone

**Files:**
- Create: `docs/superpowers/plans/verify_weapon_socket.py`
- Modify (if their gates assumed the old Creep bones or identity frames): `verify_creep_rig_asset.py`, `verify_weapon_space.py`, `verify_inventory.py`

**Interfaces:**
- Consumes: Tasks 1–3.

- [ ] **Step 1: Write the verify** (the `verify_inventory.py` shape: gates, FAILS, the standalone init). Clear every stored grip first, then gate:
  1. **Every rig, every catalog weapon, zero grip, right hand** (`equip.to_hand`) on Manny_Rig, Orc_D_Rig and Creep_Rig:
     - blade (node +Y) within 15° of the knuckle line pinky_01_r → index_01_r;
     - thickness (node Z) within 15° of the palm normal (knuckles × metacarpals);
     - `bonedrive.measured_grip` rotate and translate all < 1e-6.
  2. **The left hand's default**, the undialled mirror on each rig: the blade within 20° of the left knuckle line pinky_01_l → index_01_l.
  3. **The Creep Sword on the Creep where the old asset stood it.** Import the BACKUP `Creep_Rig.ma` (Task 3 Step 1) into a namespace. Place the sword by the OLD rule (`bonedrive.framed((0,45,0), old weapon_r world)` onto a fresh transform), and compare it with the new asset's zero-grip node world (< 1e-6, both rigs at the origin, build pose).
  4. **A UE clip on the Creep.** Import the Longsword combo clip (the path `verify_inventory.py` uses), `run_retarget` onto the Creep rig holding a zero-grip Long Sword. At first, middle and last frame (real `currentTime` changes, trap 69), the blade within 25° of the knuckle line (measured before the fix: 101.9° at frame 0).
  5. **Migration end to end.** Remove `grips.MIGRATED`, store (90,0,0 / 0,0,0) for LongSword_02, call `grips.stored` (it migrates), then `equip.to_hand` on Manny. The node stands where `framed((0,0,0), matrix_of((90,0,0)) · weapon_r world)` put it before (< 1e-6), and the stored grip now reads 0.
- [ ] **Step 2: Run it**: `mayapy verify_weapon_socket.py`. All gates pass. A failure is diagnosed by measuring, and the numbers go into the report.
- [ ] **Step 3: Re-run** `verify_creep_rig_asset.py`, `verify_creep_skeleton_asset.py`, `verify_weapon_space.py`, `verify_creep_bind_pose.py`, `verify_inventory.py`. A gate that hardcoded the old Creep bone or an identity frame is rewritten to the new rule and says so in its message. A gate that fails on a real regression is a bug to fix, never a gate to loosen.
- [ ] **Step 4: Commit.** Message: `test(weapons): the socket proven on every rig - verify_weapon_socket`.

---

### Task 5: The inventory in the hub's look

**Files:**
- Modify: `SkeldarAnim/maya_invlook.py` (PALETTE = TOKENS, TITLE_FONTS gone, docstring)
- Modify: `SkeldarAnim/maya_inventory.py` (module docstring, `colour`, `font`, `Ghost.paintEvent`, `_bevel` / `_box` / `_diamond` → `_card` / `_well` / `_outline`, `paintEvent`, the translucent top-level)
- Test: `tests/test_invlook.py`, `tests/test_inventory.py`

**Interfaces:**
- Consumes: `maya_hubstyle.TOKENS` (stdlib), `maya_hubqt.pixmap(name, colour, size)`.
- Produces: `maya_invlook.PALETTE is maya_hubstyle.TOKENS`, and `maya_invlook.RADIUS = {"card": 8, "well": 6, "item": 4}` (logical px).

- [ ] **Step 1: Failing tests.** `test_invlook.py`:

```python
class Look(unittest.TestCase):
    """2026-09-30, «в стиле нашего интерфейса»: the hub's own tokens."""

    def test_the_palette_is_the_hubs(self):
        import maya_hubstyle
        self.assertIs(look.PALETTE, maya_hubstyle.TOKENS)

    def test_no_serif_title(self):
        self.assertFalse(hasattr(look, "TITLE_FONTS"))
```

`test_inventory.py`:

```python
class Skin(unittest.TestCase):

    def test_no_colour_of_its_own(self):
        import re
        src = open(inv.__file__, encoding="utf-8").read()
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b", src), [])

    def test_no_diablo_left(self):
        src = open(inv.__file__, encoding="utf-8").read().lower()
        for word in ("diablo", "bronze", "parchment", "gold", "_diamond", "_bevel"):
            self.assertNotIn(word, src)
```

In `Window`, add `test_the_ground_is_the_hubs_panel`. Render the window; the pixel at the window's middle-left inset (x = MARGIN/2, y = the middle of the name row) equals `QColor(maya_hubstyle.TOKENS["panel"])`.

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
  - `maya_invlook.py`: `import maya_hubstyle`, then `PALETTE = maya_hubstyle.TOKENS`, `RADIUS = {"card": 8, "well": 6, "item": 4}`, and delete `TITLE_FONTS`. The docstring says the look is the hub's (2026-09-30, the quote), no longer Diablo's.
  - `maya_inventory.py`:
    - `setAttribute(Qt.WA_TranslucentBackground)` on the window, so the rounded corners show;
    - `font(px, bold=False)` uses the default UI family;
    - drawing helpers:
      - `_card(p, r, lit)`: rounded `RADIUS["card"]`, `card` face (`card_active` when lit == "target"), outline 2 px `accent` for "target", `danger` for "refused", else none;
      - `_well(p, r)`: rounded `RADIUS["well"]`, `field`.
    - the window: `panel` rounded `RADIUS["card"]`, 1 px `line` outline;
    - the title: the `backpack` icon (`maya_hubqt.pixmap("backpack", PALETTE["muted"], int(16 * k))`), then «Inventory» bold `text`, left;
    - close: ✕ in `muted`, a `hover` rounded face while hovered (`self._hover == ("close",)`);
    - the character's name: `muted`, small, left;
    - slots:
      - `_card`, label at the top in `muted` small, a `_well` below holding the weapon;
      - the hover or valid target is lit "target"; the source slot while dragging is lit "refused";
      - «on the floor» as a `status` pill with `status_text`;
    - the grid: `_card` around, `_well` inside, cell lines `line` with alpha 90, the item under the mouse a `hover` rounded `RADIUS["item"]`;
    - the preview: `ok_tint` + 1 px `ok` outline when it fits, `danger_tint` + `danger` when there is no room;
    - status: a `status` rounded well, `status_text`;
    - the ghost caption: a `card` pill, `accent` edge when good, `danger` when not, `text`.
  - The palette keys used must all exist in TOKENS: panel, card, card_active, field, line, hover, text, muted, faint, accent, ok, ok_tint, danger, danger_tint, status, status_text.
- [ ] **Step 4: Run `tests.test_invlook tests.test_inventory`, then the whole suite. Expect PASS.**
- [ ] **Step 5: Photograph.** Run `scratchpad/look_window.py` and `look_drag.py` (offscreen, `QT_QPA_FONTDIR=C:/Windows/Fonts`), look at the PNGs, and fix anything that reads wrong.
- [ ] **Step 6: Commit.** Message: `feat(inventory): the hub's own look - cards, the accent, no Diablo`.

---

### Task 6: Docs, the live run, the installed copy

**Files:**
- Modify: `CLAUDE.md` (the inventory section's title and its Diablo lines; a new short section «One weapon socket (2026-09-30)»; the Creep pipeline order gains the script; the traps if any came up). Stage only our hunks.
- Modify: `catalog.py` row comments that say "the sword's axes" stay true; add nothing else.

- [ ] **Step 1: The live inventory** in a disposable Maya (scratch `MAYA_APP_DIR` seeded with the animator's three (90,0,0) grips, port 7003). Run the existing stages (`stage_setup.py`, `stage_photo_d.py`, `stage_drops.py`) with their gate numbers. Photograph the restyled window with `widget.grab()` in its own send (trap 68). Check that the seeded grips migrated to 0. Kill the process afterwards.
- [ ] **Step 2: The installed copy.** If port 7001 is listening, run `refresh_install.py` over it. If not, say so in the report: the next Check update or drag brings it.
- [ ] **Step 3: Docs** as listed, with the measured numbers from Tasks 3–5.
- [ ] **Step 4: Full test run, then commit.** Message: `docs: one weapon socket, the inventory in the hub look`.

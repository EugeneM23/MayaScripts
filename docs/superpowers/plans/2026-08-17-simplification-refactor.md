# Simplification Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove verified-dead code, deduplicate verified-identical code, split `fkcontrols.py` (1792 lines) into four single-responsibility modules, and archive superseded legacy tools — with zero behavior change.

**Architecture:** Spec: `docs/superpowers/specs/2026-08-17-simplification-refactor-design.md`. Part A is independent point cleanups, one commit each. Part B relocates functions verbatim into `fkchains.py` / `fkrings.py` / `fkalign.py`, with `fkcontrols` re-importing every moved name so every external caller, test, and verify script keeps working unchanged. Part C is `git mv` into `archive/`.

**Tech Stack:** Python 2/3-compatible Maya module code (`maya.cmds`), stdlib `unittest` run under mayapy.

## Global Constraints

- **Behavior preservation is absolute.** No logic edits, no signature changes, no renames of anything any caller uses. Functions in Part B move VERBATIM — docstrings and attached comments travel with them.
- **Test command** (PowerShell; do NOT append `2>&1` — unittest writes to stderr and PS 5.1 turns that into NativeCommandError noise):
  `$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  Run from `C:\!!!Work\MayaScripts`. Expected today: 265 tests, OK. Tasks 1–2 delete test classes, so the count drops; every remaining test must pass after every task.
- **Trap-protected code is untouchable** except as whole functions relocated verbatim. If an edit outside this plan's exact instructions looks tempting, don't.
- Line numbers below were read from the current working tree at commit `b4104dd`. Earlier tasks shift later line numbers — locate code by the quoted text, use numbers as a guide only.
- Commit messages follow the repo style (`refactor:`/`docs:` prefix, lowercase summary) and end with the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer. Use `git commit -F <file>` or a Bash heredoc, never a PowerShell here-string with double quotes.
- Branch: `feature/overrig-picker`. Do not push unless asked.

---

## Part A — cleanups

### Task 1: Dead code in fkcontrols

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (three deletions, one inline)
- Modify: `tests/test_fkcontrols.py` (delete `TestResolveChains`)
- Modify: `docs/superpowers/plans/verify_switch.py:115` (one line)

**Interfaces:**
- Consumes: nothing.
- Produces: `fkcontrols` no longer has `resolve_chains`, `remove_fk`, `_ik_hand_control`. Task 9's move list already excludes `resolve_chains`.

- [ ] **Step 1: Confirm the symbols are still dead** (they were at audit time; re-verify)

Grep the whole repo (`maya_overrig/`, `maya_uebridge/`, `maya_scenesetup/`, `tests/`, `docs/`, root `maya_*.py`) for `resolve_chains`, `remove_fk`, `_ik_hand_control`. Expected: `resolve_chains` — definition + `TestResolveChains` only; `remove_fk` — definition + `docs/superpowers/plans/verify_fk.py` (archived in Task 12) only; `_ik_hand_control` — definition, one internal call in `_rehang_riders`, one call in `docs/superpowers/plans/verify_switch.py:115`.

- [ ] **Step 2: Delete `fkcontrols.resolve_chains`** (lines 200–217, the whole function `def resolve_chains(nodes, members_by_chain, bone_owner):` through `return [name for name, _ in CHAINS if name in hit]`).

- [ ] **Step 3: Delete `fkcontrols.remove_fk`** (lines 581–594, `def remove_fk():` through `return len(doomed)`).

- [ ] **Step 4: Inline `_ik_hand_control`.** Delete the function (lines 1538–1543). In `_rehang_riders`, change:

```python
        target = _limb_anchor(scene_map, limb) or _ik_hand_control(limb)
```
to
```python
        target = _limb_anchor(scene_map, limb) or builder.ik_control(limb, "end")
```

- [ ] **Step 5: Update `docs/superpowers/plans/verify_switch.py:115`** (it already imports `builder` at line 15):

```python
ik_hand = builder.ik_control("arm_l", "end")
```

- [ ] **Step 6: Delete `TestResolveChains`** from `tests/test_fkcontrols.py` (class at lines 467–495).

- [ ] **Step 7: Run the suite.** Expected: all pass, count drops by `TestResolveChains`'s tests.

- [ ] **Step 8: Commit** — `refactor(overrig): drop dead resolve_chains, remove_fk, _ik_hand_control`

### Task 2: Dead code in builder

**Files:**
- Modify: `maya_overrig/builder.py` (delete `resolve_limbs` 80–107, `limbs_in_selection` 116–121)
- Modify: `tests/test_builder.py` (delete `TestResolveLimbs`, lines 130–198)
- Modify: `CLAUDE.md` (pure-function list)

**Interfaces:**
- Produces: `builder` no longer has `resolve_limbs` / `limbs_in_selection`. `built_limbs` (110–113) stays — it has live callers.

- [ ] **Step 1: Re-verify dead.** Grep the repo for `resolve_limbs` and `limbs_in_selection`. Expected callers: `tests/test_builder.py` and `docs/superpowers/plans/verify_bake.py` (archived in Task 12) only, plus the CLAUDE.md mention.

- [ ] **Step 2: Delete both functions** from `builder.py`: `def resolve_limbs(nodes, limb_members, scene_map):` (80–107) and `def limbs_in_selection(scene_map):` (116–121).

- [ ] **Step 3: Delete `TestResolveLimbs`** from `tests/test_builder.py` (130–198).

- [ ] **Step 4: Edit CLAUDE.md.** In the line naming the pure functions ("`resolve_limbs`, `order_by_nesting`, `foreign_knots_inside`, `detect_prefix`, `unrecorded_rig_roots`"), remove `resolve_limbs`.

- [ ] **Step 5: Run the suite.** Expected: all pass.

- [ ] **Step 6: Commit** — `refactor(overrig): drop dead resolve_limbs and limbs_in_selection`

### Task 3: One `_mel_gate` for the five MEL entry points

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`bake_fk` 1211–1217, `build_fk` 1236–1245, `bake_selection` 1394–1398, `rebuild` 1444–1450, `switch_limbs` 1727–1731)

**Interfaces:**
- Produces: module-level `_mel_gate() -> str | None` in fkcontrols. It MUST read the module-global `overrig` (never a local import) — `TestOverRigGuard` rebinds `fkcontrols.overrig` and asserts call counts.

- [ ] **Step 1: Add the helper** above `bake_fk`:

```python
def _mel_gate():
    """The refusal every MEL entry point shares, or None to proceed.

    Two guards in this order. The toolset must be in the session: without
    this the first Build of a fresh Maya threw "Cannot find procedure" out
    of the Qt slot, where nobody saw it, and the panel looked dead (trap
    20). And the time slider must not carry a multi-frame highlight:
    OverRig bakes across it before the playback range, so a capture or
    teardown under one silently clips to it (trap 36).
    """
    if not overrig.ensure_loaded():
        return overrig.NOT_LOADED_MESSAGE
    selection = overrig.slider_selection()
    if selection:
        return overrig.slider_message(selection)
    return None
```

- [ ] **Step 2: Replace the five gates.** The "Not connected" checks in `build_fk` (1234–1235) and `rebuild` (1442–1443) stay FIRST, exactly where they are — a test locks that order.

In `bake_fk`, replace lines 1211–1217 (the `ensure_loaded` check, the two-line Fast_Bake comment, and the `slider_selection` check) with:

```python
    message = _mel_gate()
    if message:
        return 0, message
```

In `build_fk`, replace lines 1236–1245 (the five-line trap-20 comment now living in the helper's docstring, plus both checks) with the same three lines as `bake_fk`.

In `bake_selection`, replace lines 1394–1398 with:

```python
    message = _mel_gate()
    if message:
        return message
```

In `rebuild`, replace lines 1444–1450 with (the teardown comment stays):

```python
    message = _mel_gate()
    # Checked before the teardown, not just inside build_fk: Fast_Bake reads
    # the highlight too, and a teardown under one loses everything outside it.
    if message:
        return message
```

In `switch_limbs`, replace lines 1727–1731 with:

```python
    message = _mel_gate()
    if message:
        return [], list(limbs), message
```

- [ ] **Step 3: Run the suite.** `TestOverRigGuard` (test_fkcontrols.py:208–267) is the safety net here — it must pass unchanged, including the `asked == 1` assertion.

- [ ] **Step 4: Commit** — `refactor(overrig): one _mel_gate for the five MEL entry points`

### Task 4: Route raw MEL parent calls through overrig helpers

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`_attach_chain` 1122–1123, `_parent_out` 1522–1523, `_parent_in` 1533–1534)

**Interfaces:**
- Consumes: `overrig.parent_out(node)` (overrig.py:278) and `overrig.parent_in(child, parent)` (overrig.py:284) — byte-identical bodies, live-proven by verify_connect_arms.py.

- [ ] **Step 1: Replace the three bodies.** In `_attach_chain`:

```python
    overrig.parent_in(child_ctrl, parent_ctrl)
```
replaces
```python
    cmds.select([child_ctrl, parent_ctrl], replace=True)
    mel.eval("apply_Parent_in()")
```

In `_parent_out`, `overrig.parent_out(ctrl)` replaces its select+eval pair. In `_parent_in`, `overrig.parent_in(child_ctrl, parent_ctrl)` replaces its select+eval pair. The manifest bookkeeping (`builder._scene_nodes()` before, `_record_into` after) stays exactly where it is. `mel` stays imported — `build_fk` and others still use it.

- [ ] **Step 2: Run the suite.** Expected: all pass (no unit test reaches these — the gate in Task 3's five entry points bails first under the fake).

- [ ] **Step 3: Commit** — `refactor(overrig): adopt overrig.parent_in/out in fkcontrols`

### Task 5: overrig.py — SOURCE_SET and the padded_range guard

**Files:**
- Modify: `maya_overrig/overrig.py` (line 22; `padded_range` 76–118)

- [ ] **Step 1: Re-verify** `SOURCE_SET` has no Python reference outside its definition (grep `SOURCE_SET` and `OverRig_rig_objects`).

- [ ] **Step 2: Demote it to a comment.** Replace line 22 with:

```python
# OverRig also keeps a set "OverRig_rig_objects" of the source objects it
# has rigged; nothing here reads it (builder._recordable skips it by prefix).
```

- [ ] **Step 3: Simplify `padded_range`.** Delete `_PAD_DEPTH = [0]` (line 76), the early-yield branch (96–102), both counter mutations (108, 115) and the docstring's final sentence ("Re-entrant: only the outermost use pads."). Resulting function:

```python
@contextmanager
def padded_range():
    """One frame of playback padding around an OverRig capture or bake.

    OverRig's CHAIN CAPTURE procs clip a frame at each end of the range: a
    pose keyed only at the first and last frames came out of
    `apply_ForwHierarhy` as a CONSTANT track holding the interior value --
    fingers posed at frame 0 fell to where they were on frame 1 after a
    rebuild. Widening the playback range by one frame on each side keeps
    the real range fully inside the capture.

    Scope this to the capture procs ONLY (ForwHierarhy, parentConstrAnim,
    the rebike IK): `apply_Fast_Bake` and `apply_Parent_in/out` measured
    zero drift for weeks without padding, and blanket padding introduced
    one-frame glitches around the current frame.
    """
    saved = (cmds.playbackOptions(query=True, animationStartTime=True),
             cmds.playbackOptions(query=True, animationEndTime=True),
             cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, maxTime=True))
    cmds.playbackOptions(animationStartTime=saved[0] - 1,
                         animationEndTime=saved[1] + 1,
                         minTime=saved[2] - 1, maxTime=saved[3] + 1)
    try:
        yield
    finally:
        cmds.playbackOptions(animationStartTime=saved[0],
                             animationEndTime=saved[1],
                             minTime=saved[2], maxTime=saved[3])
```

- [ ] **Step 4: Run the suite. Commit** — `refactor(overrig): drop the unused padded_range re-entrancy guard`

### Task 6: Picker cleanups

**Files:**
- Modify: `maya_overrig/pickerstate.py` (`selected_ids` 31–44)
- Modify: `maya_overrig/picker_window.py` (delete `refresh` 231–237; `_joint_to_id` at 79, 215, 220, 254)
- Modify: `docs/superpowers/specs/2026-08-14-overrig-picker-design.md:209`

- [ ] **Step 1: Merge `selected_ids`' two identical loops** (BUTTONS and IK_BUTTONS are both tuples; concatenation preserves the map order a test pins):

```python
def selected_ids(resolution, selected_paths):
    """Button ids whose controller is in the given selection, in map order.

    Matching is on full DAG paths, never bare names -- another character's
    same-named controller must not light our buttons up.
    """
    found = []
    for button in bodymap.BUTTONS + bodymap.IK_BUTTONS:
        if resolution.get(button.id) in selected_paths:
            found.append(button.id)
    return found
```

- [ ] **Step 2: Delete `PickerWindow.refresh`** (picker_window.py:231–237). Zero callers; binding already re-resolves from UUID on every `bound_root()` call.

- [ ] **Step 3: Amend the spec row** at `docs/superpowers/specs/2026-08-14-overrig-picker-design.md:209` so it stops naming the deleted entry point:

```markdown
| Bound root deleted | `bound_root()` returns `None`; every lookup goes dead until the user Connects again (auto-connect still runs on the next `show_picker()`). |
```

- [ ] **Step 4: `_joint_to_id` becomes `_fk_joints`.** All three consumers are key-membership only (`detect_prefix` does `set(known_names)`; line 220 counts; line 254 is an `in` test). Line 79:

```python
        self._fk_joints = frozenset(b.joint for b in bodymap.BUTTONS)
```

Line 215: `self._prefix = naming.detect_prefix(raw, self._fk_joints)`.
Line 220: `matched = sum(1 for j in self._fk_joints if j in self._scene_map)`.
Line 254: `if joint not in self._fk_joints:`.
Grep `_joint_to_id` afterwards — zero hits expected.

- [ ] **Step 5: Run the suite** (test_pickerstate's `test_ik_and_fk_ids_come_back_in_map_order` is the net for Step 1). **Commit** — `refactor(overrig): picker cleanups - dead refresh, set-shaped joint lookup`

### Task 7: uebridge cleanups

**Files:**
- Modify: `maya_uebridge/animimport.py` (delete 118–123; helper for 160–162 / 276–278; `import_clip` 324–328 and 363)

- [ ] **Step 1: Delete `_joints_with_curves`** (lines 118–123). Re-verify zero callers first (grep `joints_with_curves`).

- [ ] **Step 2: Add `_first_few`** above `rigged_target_message` and use it in both message builders (output byte-identical — tests lock the strings):

```python
def _first_few(names):
    """The first four names, sorted, an ellipsis when there are more."""
    shown = ", ".join(sorted(names)[:4])
    if len(names) > 4:
        shown += ", ..."
    return shown
```

In `rigged_target_message`, replace lines 160–162 with `shown = _first_few(names)`. In `stale_line`, replace lines 276–278 with `shown = _first_few(names)`.

- [ ] **Step 3: Bind `skeleton_roots()` once in `import_clip`.** Replace lines 324–328 with:

```python
        roots = skeleton_roots()
        target = choose_target_root(roots, selected_roots())
        if target is None:
            raise RuntimeError(
                AMBIGUOUS_TARGET_MESSAGE if roots else NO_TARGET_MESSAGE)
```

(Keep the surrounding `if merge:` block structure untouched.)

- [ ] **Step 4: Identity comprehension at 363:**

```python
    new_curves = list(set(cmds.ls(type="animCurve") or []) - before_curves)
```

- [ ] **Step 5: Run the suite** (test_uebridge_import locks both message formats). **Commit** — `refactor(uebridge): animimport cleanups - dead helper, shared truncation`

### Task 8: scenesetup cleanups

**Files:**
- Modify: `maya_scenesetup/window.py` (guard helper; `attached_message`; bound-label helper; tooltip 338–343)
- Modify: `maya_scenesetup/connect.py` (`linked_carrier` 77)

- [ ] **Step 1: Add two helpers** after `_carrier`:

```python
def _bound_root():
    """The character, with the header label refreshed to match."""
    root = skeleton.current_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root))
    return root


def _locate(entry):
    """Root, bone, carrier and link state, or None with the status set.

    The shared front half of every weapon callback: no character and a
    missing bone end the press the same way everywhere.
    """
    root, bone, carrier, linked = _carrier(entry)
    if not root:
        _status(NO_CHARACTER)
        return None
    if not bone:
        _status(missing_bone_message(root, entry.bone))
        return None
    return root, bone, carrier, linked
```

`_carrier` itself replaces its first two lines (150–151) with `root = _bound_root()`; `camera_setup` replaces its lines 267–268 with `root = _bound_root()`.

- [ ] **Step 2: Rewrite the three callbacks on `_locate`** — post-guard logic unchanged, message constants byte-identical:

```python
def add_weapon():
    """Put the chosen weapon into its bone, replacing what we put there before."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, bone, _carrier_now, linked = located
    if linked:
        # Replacing deletes the carrier, and the IK hand controls are its DAG
        # children: this press would take both arm rigs down unbaked.
        _status(LINKED_NO_ADD)
        return

    absent = catalog.missing(entry)
    if absent:
        _status(missing_file_message(absent))
        return

    rotate, translate = _fields()
    attach.attach(entry, bone, rotate, translate)
    _remember(entry, rotate, translate)
    _status(added_message(entry, bone))


def connect_arms():
    """Hand the arms over to the weapon: both to IK, hands onto the prop."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    root, _bone, carrier, linked = located
    if linked:
        _status(ALREADY_CONNECTED)
        return
    if not carrier:
        _status(NO_WEAPON)
        return
    _status(linking.connect(carrier, skeleton.scene_map(root)))


def disconnect_arms():
    """Hands back on the root control, weapon back in the hand."""
    entry = _entry()
    located = _locate(entry)
    if located is None:
        return
    _root, bone, carrier, linked = located
    if not linked:
        _status(NOT_CONNECTED)
        return
    _status(linking.disconnect(carrier, bone))
```

- [ ] **Step 3: Add `attached_message`** next to `added_message` and use it at the two inline sites (refresh:186, offsets_changed:239):

```python
def attached_message(entry, bone):
    return "{0} on {1}".format(entry.label, bone.split("|")[-1])
```

refresh: `_status(linked_message(entry) if linked else attached_message(entry, bone))`. offsets_changed: `_status(attached_message(entry, bone))`.

- [ ] **Step 4: Fix the Camera Setup tooltip** (lines 338–343):

```python
    cmds.button(label="Camera Setup", height=28,
                annotation="Make a camera on camera_bone, bake the bone's "
                           "animation onto it, and drive the bone from the "
                           "camera. The camera lands in the bone's transform; "
                           "only the axes differ (the measured turn).",
                command=lambda *_args: _run(camera_setup))
```

- [ ] **Step 5: Drop `linked_carrier`'s unused parameter** (connect.py:77–84): signature becomes `def linked_carrier():`, body iterates `for limb in ARMS:`. Re-verify no caller passes an argument (grep `linked_carrier(` — window.py:162 and verify_connect_arms.py all call it bare).

- [ ] **Step 6: Run the suite. Commit** — `refactor(scenesetup): shared callback guard, honest camera tooltip`

---

## Part B — the fkcontrols split

Mechanics, identical for Tasks 9–11: cut the listed functions/constants VERBATIM (docstrings and attached comment blocks travel along), paste into the new module under the given header, then add a re-import block in `fkcontrols` listing EVERY moved name — public and private. That keeps `fkcontrols.<name>` working for `picker_window`, `maya_scenesetup`, every test, and every verify script (`verify_control_axes.py` reads the private `_euler_matrix` and `_ROTATE_CHANNELS`). Monkey-patching still works where it matters: `verify_control_axes.py` patches `fkcontrols.orient_controllers`, and `build_fk` (staying in fkcontrols) resolves that name in fkcontrols' own globals at call time.

After each move, before running the suite, check every moved function body for names it references that stayed behind (or vice versa) — the from-import lists below were derived from the audit, but a `NameError` here only surfaces at call time in Maya, so verify by reading, not just by the suite.

**Do not move** (they stay in fkcontrols): `chain_members`, `built_fk_chains`, `_legacy_members`, `has_fk`, `_ensure_chain_set`, `_record_into`, `_record_fresh`, `_final_radii`'s callers (`build_fk`), `_attach_chain`, `_bake_fk_chains`, `bake_fk`, `_mel_gate`, `build_fk`, `bake_targets`, `bake_selection`, `rebuild`, `_parent_out`, `_parent_in`, `_anchor_in`, `_mute_anchor`, `_limb_anchor`, `hang_ik_on_root`, `lift_ik_off_root`, `hang_ik_end_on`, `lift_ik_end`, `_rehang_riders`, `switch_limbs`, `IK_TOP_ROLES`.

### Task 9: Extract `fkchains.py`

**Files:**
- Create: `maya_overrig/fkchains.py`
- Modify: `maya_overrig/fkcontrols.py`

**Interfaces:**
- Produces: `maya_overrig.fkchains` with the chain tables and pure resolution. Imports **stdlib + builder only** (for `_is_inside` and `LIMBS`) — these are the pure scene-as-data functions; none touches `cmds`. No import cycle: `builder` imports only `naming` and `overrig`.

- [ ] **Step 1: Create the module.** Header:

```python
"""The chain tables and their pure resolution.

Which bones form which chain, and everything that answers questions about
chains from plain data: the first bone the skeleton HAS (trap 21), the
innermost recorded owner of a node, which chains ride inside a doomed
container. Nothing here touches the scene -- callers pass the scene as data,
which is what makes all of it testable without Maya.
"""

from maya_overrig import builder
```

Move, verbatim and in this order: `FK_SET`, `FK_SET_PREFIX`, `SUFFIX` (26–28 with their comments), `LIMB_CHAINS` (30–31), `SWITCHABLE` (33–36 with its comment), `_finger_chains` (39–50), `CHAINS` (53–67 with its comment), `HYBRID_FK_CHAINS` (69–72 with its comment), `controller_name` (91–93), `chain_set` (96–98), `finger_chains_for` (101–112), `chain_root` (120–139), `chain_tip` (142–151), `chain_root_control` (154–161), `switchable_bones` (164–178), `innermost_owner` (181–197), `dependent_chains` (220–236), `limbs_riding_inside` (239–257), `attach_parent` (260–276).

- [ ] **Step 2: Re-import in fkcontrols.** Where the moved block was, add:

```python
from maya_overrig.fkchains import (  # noqa: F401 -- fkcontrols is the API
    FK_SET, FK_SET_PREFIX, SUFFIX, LIMB_CHAINS, SWITCHABLE, _finger_chains,
    CHAINS, HYBRID_FK_CHAINS, controller_name, chain_set, finger_chains_for,
    chain_root, chain_tip, chain_root_control, switchable_bones,
    innermost_owner, dependent_chains, limbs_riding_inside, attach_parent)
```

- [ ] **Step 3: Cross-check names.** Every moved function references only stdlib, other moved names, or `builder.*` — read them to confirm. Remainder references to moved names (`CHAINS`, `controller_name`, `chain_root`, …) now resolve through the import — grep the remainder for each moved name to confirm nothing was missed.

- [ ] **Step 4: Run the suite** — test_fkcontrols exercises the moved pure functions through `fkcontrols.<name>` and must pass unchanged. **Commit** — `refactor(overrig): extract fkchains - chain tables and pure resolution`

### Task 10: Extract `fkrings.py`

**Files:**
- Create: `maya_overrig/fkrings.py`
- Modify: `maya_overrig/fkcontrols.py`

**Interfaces:**
- Produces: `maya_overrig.fkrings` — ring sizing from the skinned mesh and knot dressing. Imports: `maya.cmds`, `maya.api.OpenMaya`, `maya.api.OpenMayaAnim`, `bodymap`, `naming`, `fkchains`.

- [ ] **Step 1: Create the module.** Header:

```python
"""Ring sizing from the skinned mesh, and dressing OverRig knots as controls.

Sizing comes from the mesh rather than bone length -- on this skeleton bone
length is meaningless (`head` measures 0 for having no children). A joint's
radius is the perpendicular spread of the vertices it dominates; _BORROW and
_SCALE hold the user-driven corrections, _SQUARE the bones drawn square so
they read among same-size neighbours. Dressing renames each knot to
<joint>_FK_ctrl and attaches our sized shape -- UUID-safe, because renaming a
chain parent invalidates every descendant path.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

from maya_overrig import bodymap, naming
from maya_overrig import fkchains
```

Move, verbatim: `_LEFT`, `_RIGHT`, `_CENTRE`, `_REGION_COLOURS`, `_DOMINANT_FLOOR`, `_SHARED_FLOOR`, `_SECTIONS`, `_LINE_WIDTH` (74–88 with comments), `colour_for` (115–117), `rollup` (279–298), `_BORROW`/`_SCALE` (301–~311 with the long comment block), `apply_size_rules`, `stagger`, `radius_from` (313–351), `_SQUARE` (~381 with its comment), `is_square`, `square_points` (384–~403), `_world_position`, `_bone_axis` (405–415), `_skin_data` (417–437), `_parent_map` (439–446), `_vertex_buckets` (448–485), `_radius_for` (487–508), `_style_curve`, `_make_ring`, `_make_square` (510–534), `_final_radii` (597–~637), `_bone_knot_map` (639–~674), `_hide_native_shapes`, `_hide_rig_machinery` (676–~703), `_dress_knots` (705–~745).

Inside the moved code, references to other moved names stay bare; references to fkchains names (`controller_name`, `CHAINS`, …) become `fkchains.<name>` — check each moved function body and adjust ONLY the qualification, never the logic.

- [ ] **Step 2: Re-import in fkcontrols:**

```python
from maya_overrig.fkrings import (  # noqa: F401 -- fkcontrols is the API
    colour_for, rollup, apply_size_rules, stagger, radius_from, is_square,
    square_points, _skin_data, _parent_map, _vertex_buckets, _radius_for,
    _style_curve, _make_ring, _make_square, _final_radii, _bone_knot_map,
    _hide_native_shapes, _hide_rig_machinery, _dress_knots, _BORROW, _SCALE,
    _SQUARE)
```

- [ ] **Step 3: Cross-check names** both directions, as in Task 9 (`_record_into` uses `_hide_rig_machinery`; `build_fk` uses `_parent_map`, `_final_radii`, `_dress_knots`, `colour_for`-adjacent code — grep the remainder for every moved name).

- [ ] **Step 4: Run the suite. Commit** — `refactor(overrig): extract fkrings - skin-driven sizing and knot dressing`

### Task 11: Extract `fkalign.py`

**Files:**
- Create: `maya_overrig/fkalign.py`
- Modify: `maya_overrig/fkcontrols.py`

**Interfaces:**
- Produces: `maya_overrig.fkalign` — the controller-axis algebra. Imports: `contextlib`, `math`, `maya.cmds`, `axes`, `fkchains`. This is traps-29/31 territory: the move must be character-for-character; the only permitted edits are import qualification.

- [ ] **Step 1: Create the module.** Header:

```python
"""Re-expressing FK controllers in their bones' axes.

Two steps, run at the tail of every build. align_controllers conjugates the
rotate CHANNELS into the bone's frame, so equal values on both sides give a
mirrored pose. orient_controllers then turns each knot's OWN frame onto its
bone -- the frame is everything an animator can see of a controller -- with
every DAG child counter-corrected in rotation AND turned translation (trap
29: angles are blind to position, and the bone is driven from a child
locator). Both steps are idempotent because they work from the measured
offset, not the channels alone. See CLAUDE.md and the 2026-08-15/16 axis
specs for the full argument.
"""

import contextlib
import math

import maya.cmds as cmds

from maya_overrig import axes
from maya_overrig import fkchains
```

Move, verbatim: `merge_key_times` (353–~364), `is_constant` (366–~378), `_ROTATE_CHANNELS`/`_TRANSLATE_CHANNELS` (748–749), `_world_rotation`, `_euler_matrix`, `_local_total` (752–776), `_unlocked` (779–~797), `_plugs`, `_settable`, `_curves_on` (799–~832), `_hold_still_by_orient` (834–~848), `_rewrite_triple` (850–~903), `_hold_still` (905–~943), `_ON_BONE` (~945), `_turn_onto_bone` (948–~984), `orient_controllers` (986–~1016), `_align_one` (1018–~1075), `align_controllers` (1077–~1098). Qualify fkchains references (`controller_name`, `CHAINS`) as `fkchains.<name>`.

- [ ] **Step 2: Re-import in fkcontrols** (the two private names `_euler_matrix` and `_ROTATE_CHANNELS` are read by `verify_control_axes.py` — a current all-green proof — so they MUST be here):

```python
from maya_overrig.fkalign import (  # noqa: F401 -- fkcontrols is the API
    merge_key_times, is_constant, orient_controllers, align_controllers,
    _euler_matrix, _ROTATE_CHANNELS)
```

- [ ] **Step 3: Cross-check names** both directions. `build_fk` calls `align_controllers` and `orient_controllers` — through the import these resolve in fkcontrols' globals, which keeps `verify_control_axes.py`'s monkey-patch of `fkcontrols.orient_controllers` effective.

- [ ] **Step 4: Check leftover imports in fkcontrols.** After the three moves, `om`/`oma` (OpenMaya) may have no remaining user in fkcontrols — grep and drop the now-unused imports (`math`, `contextlib` likewise if orphaned). `cmds`, `mel`, `axes`(?), `bodymap`, `builder`, `naming`, `overrig` — keep whichever are still used; grep each.

- [ ] **Step 5: Run the suite. Commit** — `refactor(overrig): extract fkalign - the controller axis algebra`

---

## Part C — archive and docs

### Task 12: Archive superseded tools and stale verify scripts

**Files:**
- Create: `archive/README.md`
- Move (git mv): 8 root tools + 3 verify scripts

- [ ] **Step 1: Move.** From the repo root:

```bash
mkdir -p archive
git mv maya_rig_controllers.py maya_ctrl_shape_orient.py maya_rig_align.py maya_rig_mirror.py maya_rig_groups.py maya_rig_constraints.py maya_cube_weapons.py maya_cube_shield.py archive/
git mv docs/superpowers/plans/verify_fk.py docs/superpowers/plans/verify_bake.py docs/superpowers/plans/verify_build.py archive/
```

- [ ] **Step 2: Write `archive/README.md`:**

```markdown
# Archive

Standalone tools superseded by the packages for the UE5 Manny workflow
(2026-08-17 audit; git history holds every version):

- `maya_rig_controllers`, `maya_ctrl_shape_orient`, `maya_rig_align`,
  `maya_rig_mirror`, `maya_rig_groups` — manual controller shaping/aligning;
  `maya_overrig` now sizes, colours, aligns and orients controllers
  automatically (fkrings, fkalign).
- `maya_cube_weapons`, `maya_cube_shield` — cube blockout spawners;
  `maya_scenesetup` attaches real catalog models. (The blockouts knew five
  weapons; the catalog holds one — kept here in case that gap matters.)
- `maya_rig_constraints` — generic prop constrainer, no package equivalent.
- `verify_fk.py`, `verify_bake.py`, `verify_build.py` — first-generation
  live proofs, stale against the per-chain manifest redesign
  (`verify_build.py` references the removed `builder.BUILD_SET`).
```

- [ ] **Step 3: Run the suite** (nothing imports the moved files — confirmed by audit — but prove it). **Commit** — `refactor: archive superseded standalone tools and stale verify scripts`

### Task 13: CLAUDE.md and doc updates

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Architecture table.** Add three rows and adjust fkcontrols':

```markdown
| `fkchains.py` | chain tables + pure chain resolution | stdlib + `builder` |
| `fkrings.py` | ring sizing from the skin, knot dressing | `maya.cmds`, OpenMaya, `bodymap`, `naming`, `fkchains` |
| `fkalign.py` | controller axis algebra (align/orient) | `maya.cmds`, `axes`, `fkchains` |
| `fkcontrols.py` | FK build/bake/switch orchestration; re-exports the three above | `maya.cmds`, `maya.mel`, `builder`, `overrig`, the three above |
```

(`fkcontrols.py` currently has no row — the table lists the other modules; add all four in the right place and keep the load-bearing-rules paragraph intact.)

- [ ] **Step 2: Root-tools paragraph.** In "What is here", note that superseded standalone tools live in `archive/` (one sentence).

- [ ] **Step 3: Test count.** Update "265 tests at time of writing" to the number the suite now reports.

- [ ] **Step 4: The "What the tool does today" FK-engine paragraph** — where it says the module names (`fkcontrols.build_fk`, `axes.py, fkcontrols.align_controllers`, `fkcontrols.orient_controllers`), the names still resolve; add one sentence that the alignment/orientation implementation now lives in `fkalign.py` and sizing in `fkrings.py`, re-exported by `fkcontrols`.

- [ ] **Step 5: Run the suite one last time. Commit** — `docs: record the fkcontrols split and the archive`

### Task 14: Live verification (needs the user's Maya)

This is the real gate — unit tests alone repeatedly passed here while the scene was broken.

- [ ] **Step 1: Ask the user** to open the Manny scene and run the command-port one-liner (CLAUDE.md "Driving the user's live Maya").
- [ ] **Step 2: Send through the bridge, one at a time, reading each result file:** `docs/superpowers/plans/verify_hybrid_build.py`, `verify_control_axes.py` (exercises the re-exported private names AND the `fkcontrols.orient_controllers` monkey-patch), `verify_arm_switch.py`, `verify_ik_under_root.py`. Follow every bridge rule: idempotent runner with a `.ran` marker, fresh output file per run, poll the file not the socket.
- [ ] **Step 3: If any check is red — STOP.** Do not fix forward; bisect the task that broke it (each task is one commit).
- [ ] **Step 4: Report results to the user** with the actual numbers from the scripts.

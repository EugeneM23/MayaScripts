# Simplification refactor — dead code out, fkcontrols split, legacy archived

2026-08-17. Approved scope: all three packages of work (cleanups, split, archive).

## Why

The owner asked for a whole-plugin review: "we do simple things but some files
hold suspiciously much code". A 14-agent audit read every module and
adversarially verified each finding against CLAUDE.md's documented traps.
Verdict: the packages are mostly healthy — much of what looks excessive is
trap-protection and must stay — but three real problems exist:

1. `maya_overrig/fkcontrols.py` is 1792 lines holding four separable
   responsibilities (SRP violation; everything else in the packages is
   44–574 lines).
2. ~200 lines of confirmed-dead or duplicated code across the packages,
   each verified unreferenced by repo-wide search.
3. ~1440 lines of root-level standalone tools fully superseded by the
   packages for the UE5 Manny workflow, plus three first-generation verify
   scripts that are stale (one already crashes on a removed attribute).

## Ground rules

- **Behavior preservation is absolute.** No logic changes, no API breaks.
  The mayapy unit suite and the current all-green live verify scripts
  (`verify_arm_switch`, `verify_capture_edges`, `verify_control_axes`,
  `verify_hybrid_build`, `verify_ik_under_root`, `verify_missing_bones`)
  must pass after every stage.
- **Trap-protected code is untouchable.** The audit catalogued the
  load-bearing machinery (UUID manifest diffs, manifest re-reads after
  re-parenting, the two-part child counter-correction, jointOrient
  lock/unlock and write order, the bone-side knot mapping, set-existence
  re-checks, the three-IK-top-groups rule, …). None of it moves except as
  whole functions relocated verbatim in part B.
- **Explicitly rejected:** deduplicating the key-walk between `_align_one`
  and `_rewrite_triple`. It is traps-29/31 machinery with zero unit
  coverage, provable only by live runs; ~20 saved lines do not buy that risk.

## Part A — cleanups (each verified by adversarial review)

Dead code (zero callers anywhere: packages, tests, verify scripts, root tools):

- `fkcontrols.resolve_chains` (200–217) + `TestResolveChains`
  (test_fkcontrols.py:467–495). Superseded by `bake_targets`.
- `fkcontrols.remove_fk` (581–594). Its only caller is the stale
  `verify_fk.py`, which retires in part C.
- `fkcontrols._ik_hand_control` (1538–1543) — a bare delegate to
  `builder.ik_control(limb, "end")`; inline the one internal call site
  (`_rehang_riders`, 1709) and update `verify_switch.py:115` to call
  `builder.ik_control` directly (it already imports builder).
- `builder.limbs_in_selection` (116–121) and `builder.resolve_limbs`
  (80–107) + `TestResolveLimbs` (test_builder.py:130–198). Superseded by
  `fkcontrols.bake_targets`'s innermost-owner rule. Their only caller is
  the stale `verify_bake.py`, retiring in part C. CLAUDE.md's pure-function
  list drops `resolve_limbs` in the same commit.
- `overrig.SOURCE_SET` (line 22) — demote to a comment next to `KNOT_SET`
  (the set name documents real OverRig bookkeeping).
- `picker_window.PickerWindow.refresh` (231–237) — survivor of a toolbar
  button dropped before shipping; binding already re-resolves lazily from
  UUID on every use. The spec row at
  `2026-08-14-overrig-picker-design.md:209` ("the next refresh falls back
  to auto-connect") gets a one-line amendment so it does not describe a
  removed entry point.
- `animimport._joints_with_curves` (118–123).

Duplication:

- The five identical MEL gates (ensure_loaded → slider_selection) in
  `bake_fk`/`build_fk`/`bake_selection`/`rebuild`/`switch_limbs` collapse
  into one module-level `_mel_gate()` returning the refusal message or
  None; callers wrap it in their own return shape. The helper lives in
  fkcontrols and reads the module-global `overrig`, so `TestOverRigGuard`'s
  fake injection and its `asked == 1` assertion keep working. The
  "Not connected" check stays ahead of the gate where it is today.
- `fkcontrols._parent_out`/`_parent_in`/`_attach_chain` re-implement
  `overrig.parent_out`/`parent_in` byte-for-byte (the helpers arrived later
  for scenesetup and fkcontrols never adopted them). Route them through the
  overrig helpers; manifest bookkeeping stays in the fkcontrols wrappers.
- `overrig.padded_range` re-entrancy guard (`_PAD_DEPTH`, the early-yield
  branch, two counter mutations): no call path nests since trap-12 scoped
  padding to the capture procs. Remove; each with-frame restores its own
  saved tuple, so even hypothetical nesting stays correct.
- `pickerstate.selected_ids`: two byte-identical loops become one over
  `bodymap.BUTTONS + bodymap.IK_BUTTONS` (order preserved; `resolve` stays
  as-is — its loop bodies genuinely differ).
- `picker_window._joint_to_id`: a dict whose values are never read becomes
  `frozenset` named `_fk_joints`.
- `animimport`: `_first_few(names)` helper for the twice-written
  "first four names, then ellipsis" formatting (output byte-identical;
  both message tests keep passing); bind `skeleton_roots()` once in
  `import_clip`; `list(...)` instead of the identity comprehension at 363.
- `maya_scenesetup/window.py`: extract `_locate(entry)` for the six-line
  root/bone guard written verbatim in three callbacks; add
  `attached_message(entry, bone)` next to the other message builders and
  use it at the two inline format sites; `camera_setup` reuses the
  bound-label refresh.
- `connect.linked_carrier`: drop the unused `limbs=ARMS` parameter.

Documentation fix:

- The Camera Setup tooltip (scenesetup window.py:338–343) still describes
  the removed reference-camera path. Reword to the real behavior: the
  camera lands on the bone; the axis offset is the measured constant.

## Part B — the fkcontrols split

`fkcontrols.py` (1792) becomes four modules. **Pure relocation**: functions
move verbatim, no signature or logic edits beyond imports.

| New module | Takes | ~Lines | May import |
|---|---|---|---|
| `fkchains.py` | chain tables + pure resolution: `FK_SET`, `FK_SET_PREFIX`, `SUFFIX`, `LIMB_CHAINS`, `SWITCHABLE`, `_finger_chains`, `CHAINS`, `HYBRID_FK_CHAINS`, `controller_name`, `chain_set`, `finger_chains_for`, `chain_root`, `chain_tip`, `chain_root_control`, `switchable_bones`, `innermost_owner`, `dependent_chains`, `limbs_riding_inside`, `attach_parent` | 250 | stdlib + `builder` (for `_is_inside`/`LIMBS`) — these are the pure scene-as-data functions |
| `fkrings.py` | ring sizing from skin + knot dressing: colour/floor consts, `colour_for`, `rollup`, `_BORROW`/`_SCALE`, `apply_size_rules`, `stagger`, `radius_from`, `_SQUARE`, `is_square`, `square_points`, `_world_position`, `_bone_axis`, `_skin_data`, `_parent_map`, `_vertex_buckets`, `_radius_for`, `_style_curve`, `_make_ring`, `_make_square`, `_final_radii`, `_bone_knot_map`, `_hide_native_shapes`, `_hide_rig_machinery`, `_dress_knots` | 330 | `maya.cmds`, OpenMaya, `bodymap`, `naming`, `fkchains` |
| `fkalign.py` | axis alignment: `merge_key_times`, `is_constant`, `_ROTATE_CHANNELS`/`_TRANSLATE_CHANNELS`, `_world_rotation`, `_euler_matrix`, `_local_total`, `_unlocked`, `_plugs`, `_settable`, `_curves_on`, `_hold_still_by_orient`, `_rewrite_triple`, `_hold_still`, `_ON_BONE`, `_turn_onto_bone`, `orient_controllers`, `_align_one`, `align_controllers` | 360 | `maya.cmds`, `math`, `contextlib`, `axes`, `fkchains` |
| `fkcontrols.py` (remainder) | orchestration: manifests (`chain_members`…`_record_fresh`), `_attach_chain`, `_bake_fk_chains`, `bake_fk`, `build_fk`, `bake_targets`, `bake_selection`, `rebuild`, and the whole Switch/IK-coupling section (`_parent_out`…`switch_limbs`) | 880 | Qt-free; `maya.cmds`, `maya.mel`, `builder`, `overrig`, the three new modules |

Compatibility contract — the conditions the adversarial verifier attached:

- `fkcontrols` re-exports **every moved public name** via
  `from .fkchains import …` etc., so `picker_window`, `builder`,
  `maya_scenesetup`, all tests and all verify scripts keep working
  unchanged.
- Two moved **private** names are also re-exported, because
  `verify_control_axes.py` — a current all-green proof — reads them:
  `_euler_matrix` (line 166) and `_ROTATE_CHANNELS` (line 208).
- The remainder imports the moved private helpers it calls:
  `_hide_rig_machinery` (used by `_record_into`), `_final_radii`,
  `_dress_knots`, `_parent_map` (used by `build_fk`).
- No moved function may touch the `overrig` module — `TestOverRigGuard`
  rebinds `fkcontrols.overrig` and counts calls. (Holds today: everything
  that talks to overrig stays in the remainder.)
- `build_fk` keeps calling `orient_controllers`/`align_controllers`
  through names patchable as `fkcontrols.<name>` —
  `verify_control_axes.py` monkey-patches `fkcontrols.orient_controllers`
  to measure the turn in isolation, and a from-import satisfies this
  (the call reads the module global at call time).
- CLAUDE.md's architecture table gains the three new rows.
- Tests stay where they are (`test_fkcontrols.py` keeps importing through
  `fkcontrols`) — passing unchanged is the proof of pure relocation.

## Part C — archive

`git mv` into `archive/` (history preserved, no deletions):

- Superseded by maya_overrig's automated build/align/orient:
  `maya_rig_controllers.py`, `maya_ctrl_shape_orient.py`,
  `maya_rig_align.py`, `maya_rig_mirror.py`, `maya_rig_groups.py`.
- Superseded by maya_scenesetup (caveat, owner accepted: the cube blockout
  spawners knew five weapons; the catalog currently holds one FBX):
  `maya_cube_weapons.py`, `maya_cube_shield.py`.
- Generic prop constrainer with no package equivalent, owner chose to
  archive anyway: `maya_rig_constraints.py`.
- Stale first-generation verify scripts:
  `docs/superpowers/plans/verify_fk.py` (asserts the legacy flat FK_SET and
  marker-era parenting — fails against current code),
  `docs/superpowers/plans/verify_bake.py` (only caller of the dead
  `limbs_in_selection`),
  `docs/superpowers/plans/verify_build.py` (already crashes: references
  the removed `builder.BUILD_SET`).

CLAUDE.md's root-tools paragraph gets one line saying superseded standalone
tools live in `archive/`.

## Order of work and verification

1. **Part A** in small commits, full mayapy suite after each.
2. **Part B** as one commit per extracted module (fkchains → fkrings →
   fkalign), full suite after each; the subprocess import-discipline tests
   guard the architecture rules throughout.
3. **Part C** last (pure moves).
4. **Live verification** in the owner's Maya over the command port:
   `verify_hybrid_build.py`, `verify_control_axes.py` (exercises the two
   re-exported private names and the monkey-patch), `verify_arm_switch.py`,
   `verify_ik_under_root.py`. `verify_missing_bones.py` in a fresh Maya if
   one is available. This step needs the owner's session and happens before
   the branch is called done.
5. CLAUDE.md updated in the same series: architecture table, pure-function
   list, test count, archive note.

Expected end state: `fkcontrols.py` ~880 lines, three focused new modules,
~200 dead/duplicated lines gone, ~1570 legacy lines out of the working set,
zero behavior change.

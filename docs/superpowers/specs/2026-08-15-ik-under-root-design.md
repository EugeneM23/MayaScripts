# IK rigs ride the root control; visible fingers on IK arms

Date: 2026-08-15. Status: approved by the user (conversation, this date).

Two items, one spec: a feature — every IK limb's rig hangs under
`root_FK_ctrl` so grabbing the root moves the whole character — and a bug
fix — FK finger controllers turn invisible the moment their arm is IK,
because they hang under a hidden locator.

## Why

In the hybrid rig the torso is FK and the limbs are IK. The FK chains are
coupled (pelvis rides root, spine rides pelvis, ...), so `root_FK_ctrl`
carries the torso — but the IK limbs are pinned in world. Measured on a
live build (arm_l, this date): moving the `root` BONE by 50 units moved
nothing — not `hand_l_IK_feet`, not `lowerarm_l_IK_knee`, **not even the
`upperarm_l` bone**. The IK rig reads the skeleton only at build time;
afterwards the limb is world-anchored end to end. So moving the character
by the root control leaves all four limbs floating behind.

The user wants the obvious thing: IK elements belong to the root control.

## Measured facts the design rests on

- All three of a limb's top groups — `<root>_IK_strech_gr`,
  `<mid>_IK_knee`, `<end>_IK_feet` — sit at world root, no parent.
- The only skeleton→rig wiring is capture locators inside `_IK_strech_gr`
  parent-constrained FROM the three source bones. It does not make the rig
  follow the skeleton (see the root+50 measurement above).
- Consequence: parenting only the two animator controls (`_IK_knee`,
  `_IK_feet`) under root would move the effector targets while the chain
  base stayed pinned — the shoulder tears off the body. **All three groups
  must ride the root control, machinery included.** All three are OverRig
  knots (members of `OverRig_knots`), so `apply_Parent_in` is designed for
  exactly them.

## Decisions

1. **Hang all three top groups of every IK limb under `root_FK_ctrl` via
   `apply_Parent_in`** (child first, parent last; animation re-baked into
   the new local space — the same verified zero-drift mechanism the FK
   chain coupling uses). The three are siblings, so order among them does
   not matter.
2. **Where:** in `fkcontrols`, immediately after each `builder.build`
   call — the hybrid `rebuild`, Switch FK→IK, and the Switch auto-build.
   `builder` must not learn about FK controller names (import cycle), and
   the hang is policy, which is `fkcontrols`' job.
3. **Bookkeeping:** the fresh nodes `apply_Parent_in` creates are recorded
   into the LIMB manifest (`RigPicker_build_<limb>`), never into an FK
   chain set — the coupling lives and dies with the IK rig. This needs a
   limb-set variant of `_record_fresh`.
4. **No `root_FK_ctrl` in the scene** (IK built via Switch after a full
   Bake+Delete): skip the hang, rig stays in world as today, say so in the
   status message. The next full Build tears down and rebuilds everything,
   which re-hangs it.
5. **Teardown — the user's call: lift, don't kill.** When a bake is about
   to delete an FK chain whose recorded members contain IK limb nodes
   (today that is only the root chain), the riding IK limbs are first
   lifted to world with `apply_Parent_out` (fresh nodes recorded into the
   limb manifest) and **keep working**; only the FK chain dies. Same
   precedent as the pelvis surviving the spine teardown. This runs inside
   `_bake_fk_chains`, so it covers Bake+Delete on root, the full-FK
   toggle, and `rebuild`'s FK-first teardown order uniformly — rebuild
   then bakes the lifted IK limbs in its existing IK pass.
6. **Switch IK→FK is unchanged:** `bake_limbs` deletes the limb's recorded
   members, which are now DAG children of the root control — deleting a
   child never touches the parent. Fingers are lifted first, as today.
7. **Selection resolution is already correct:** `innermost_owner` works on
   longest-member-path; an IK group nested inside `root_FK_ctrl` is an
   exact (longer) member match, so clicks on IK controls keep resolving to
   the limb, clicks on the root control to the root chain.

## Bug fix: invisible FK finger controllers on an IK arm

`_limb_anchor` creates `<limb>_IK_anchor` — the hidden locator riding the
hand BONE that finger chains hang on — and hides its **transform**
(`setAttr loc.visibility 0`). `_parent_in` then makes the finger
controllers DAG children of that transform, and visibility inherits down:
the rings exist, the picker selects them, but the viewport shows nothing.
This affects the hybrid Build as well as Switch — anywhere fingers land on
the anchor.

Fix: hide the locator's **shape** only, never the transform (this is
already `_hide_rig_machinery`'s convention — it hides locator shapes, which
is why the coupling machinery never hid anyone's children). When
`_limb_anchor` finds an EXISTING anchor, repair it in place: transform
visibility on, shape visibility off — so rigged scenes saved with the bug
heal on their next Switch/Build.

## Not building

- No re-hang of already-built world IK rigs when a root control appears
  later outside Build (YAGNI — Build rebuilds everything anyway).
- No per-limb choice of parent (nearest torso control etc.) — the user
  asked for the root control, and the root is the character's master.
- No constraint-based alternative: a constraint on the IK controls fights
  their keys and breaks direct manipulation; rejected. A single container
  group under root was also rejected — every group still needs its own
  `apply_Parent_in` re-bake, so the container buys nothing.

## Verification

Pure functions (unit tests, no Maya): the "which IK limbs ride inside
these FK chain members" resolver (inverse of `dependent_chains`, path
containment with the `|` separator guard).

Live verify script (`docs/superpowers/plans/verify_ik_under_root.py`, run
in the Manny scene through the bridge, binds explicitly, no `cmds.undo`,
reads values before writing them back):

1. Hybrid Build → all three groups of each limb are DAG children of
   `root_FK_ctrl`; every finger controller's effective visibility is on
   (walk every ancestor's `.visibility`).
2. Move `root_FK_ctrl` +50 → limb bones, IK controls and finger rings all
   move 50±ε together; restore.
3. Overpull regression: fingers still hold at rest distance past full arm
   extension (the anchor still works re-parented).
4. Switch arm_l → FK → back to IK → still hung under root, fingers visible.
5. Bake+Delete on root only → IK limbs lifted to world, still driving the
   bones, zero drift at the probe frames.
6. Full teardown → no strays, bones clean.

Unit tests keep passing under mayapy; the live script is the real proof.

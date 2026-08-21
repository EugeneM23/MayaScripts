# Clavicles as their own FK chains — design

**Date:** 2026-08-21
**Status:** designed.

## The ask

> «давай будем в базовом BUILD создавать ФК контролы для плечей (кость
> clavicle l\R)»

The default (hybrid) Build gives the animator IK arms and no clavicle control
at all — the clavicle is a bone of the FK **arm** chain, and that chain is not
built in hybrid mode. The animator wants to pose the shoulders.

**The user's explicit call on behaviour (2026-08-21, asked directly):** the
clavicle control drives **only the clavicle bone** — nothing is re-hung on
it. The alternative (hang the arm's `_IK_strech_gr` on the clavicle control)
was offered with its side effects named and declined. Do not add that
coupling without asking again.

**Measured live after the build (2026-08-21), correcting this spec's own
assumption:** the design here predicted the IK arm would ignore the clavicle
("the shoulder tears off"), because moving the root BONE had been measured
to move neither the IK controls nor the upperarm. Wrong inference: that
measurement never moved the clavicle bone's baked channels, so nothing could
propagate. In fact **OverRig's IK follows the chain's parent bone on its
own** — turning the new clavicle control moved the upperarm 1.223 (world
matrix delta at +25°) while the IK hand stayed planted at 9.6e-8 and the
poke restored to 0.0. So the shipped behaviour is the classic
clavicle-over-IK — the shoulder leads, the hand stays — with no re-hang and
no extra machinery. `verify_hybrid_build.py` pins all three numbers.

## The design: split the clavicle out of the arm chain

Exactly the precedent of the pelvis/spine split, and for the same reason: two
things that must be able to outlive each other cannot share a manifest.

In `fkchains.CHAINS`:

- `arm_l` becomes `("upperarm_l", "lowerarm_l", "hand_l")` (and mirrored);
- two new single-bone chains appear **before** the arms:
  `("clavicle_l", ("clavicle_l",))`, `("clavicle_r", ("clavicle_r",))`.
  Before, because parents precede children in CHAINS — that ordering is what
  lets a full build couple each chain to a controller that already exists.

Everything else falls out of existing machinery, which is the argument for
this shape over any special-casing:

- **Hybrid Build builds them.** `HYBRID_FK_CHAINS` is "everything buildable
  that is not a limb chain"; the new chains are buildable and are not limb
  chains. Twelve FK controllers instead of ten.
- **Full FK keeps its behaviour.** The arm chain (now three bones) couples to
  the nearest ancestor controller — the clavicle's — via `attach_parent`, so
  rotating the clavicle controller still carries the whole FK arm, as the
  four-bone chain did. Controller count is unchanged at 26.
- **A single-bone chain goes through `apply_parentConstrAnim`**, like root and
  pelvis: the knot is a plain transform whose frame already matches the bone,
  and `align_controllers` / `orient_controllers` skip it automatically (no
  `jointOrient` attribute to write). Same accepted property as the pelvis.
- **The clavicle ring** is sized from the skin by the existing dressing; the
  picker button (`clavicle_l/r` are already in `bodymap.BUTTONS`) lights up by
  the existing controller-existence rule.
- **Coupling**: the clavicle controller hangs on the spine-tip controller
  (`spine_05` on Manny, `spine_03` on a UE4-schema rig — `attach_parent` walks
  up and does not care).

## What the animator gains over today

Today, switching an arm to IK deletes the arm chain **including the clavicle
controller**; switching back rebuilds it. After the split the clavicle is its
own always-FK chain: it survives every arm switch, in both directions, because
the arm's manifest no longer contains it.

## Switch and Bake semantics

- **Selecting a clavicle BONE and pressing Switch still switches its arm.**
  The bone is no longer part of the switchable chain, but the animator's habit
  is older than the split, so `switchable_bones` gains an explicit
  `clavicle_l → arm_l` / `clavicle_r → arm_r` mapping.
- **Selecting the clavicle CONTROLLER and pressing Switch** resolves to the
  clavicle chain, which is not switchable — the press reports "nothing to
  switch" through the existing path. It is always FK; there is nothing to
  switch it to.
- **Bake+Delete on a clavicle** (bone or controller) bakes the clavicle chain.
  An FK arm coupled inside the clavicle controller is expanded in by the
  existing nesting rule (`dependent_chains` — a chain cannot outlive its
  container). An IK arm is untouched: its groups ride the root controller,
  not the clavicle.

## Old files

A file rigged before the split has the clavicle knot recorded in the ARM
chain's manifest. Teardown and bake read the manifest, not the table, so the
old rig comes apart exactly as it used to — the clavicle controller dies with
the old arm chain once, and the next Build creates the new shape. No
migration.

## Deliberately not done

- No re-hang of the IK base groups on the clavicle controls (the user's call,
  above). If the shoulders ever need to lead the IK arms, that is
  `hang_ik_on_root` growing a per-limb target, not a table change.
- No leg equivalent (thigh base on the pelvis control) — same conversation,
  not asked.

## Proof

Unit tests: the new CHAINS shape (clavicles before arms, arms without
clavicles), HYBRID_FK_CHAINS and BUILDABLE membership, `switchable_bones`
offering clavicle bones as their arms, `attach_parent` resolving
`upperarm_l → clavicle_l` and `clavicle_l → spine_05`.

Live (`verify_hybrid_build.py`): the hybrid build stands up 12 FK controllers;
the clavicle controller exists, drives its bone (rotate the controller,
measure the bone), hangs inside the spine controller; switching an arm to IK
and back leaves the clavicle controller standing and driving.

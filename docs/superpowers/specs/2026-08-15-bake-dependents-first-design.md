# Bake nested rigs before the rig containing them

Date: 2026-08-15
Status: approved
Branch: `feature/overrig-picker`
Follows: `2026-08-15-self-sufficient-bake-design.md`

## Context

Animators park one control under another — hanging the hand's IK control off the
foot's so the arm follows the leg. Baking the outer limb then destroys the inner
limb's rig along with it, and the inner limb was never baked, so its animation
goes with the rig.

Reproduced in the working scene. `hand_l_IK_feet` parented under
`foot_l_IK_feet`, then `Bake+Delete` on the left leg:

| After baking the leg | |
|---|---|
| Arm control alive | no — removed with the leg's 68 nodes |
| Arm joints constrained | yes, all three |
| Arm's driver | gone |
| Arm manifest | silently shrank from 68 nodes to 61 |

The arm ends up constrained to a rig that no longer exists, and its animation is
unrecoverable.

## Goal

Baking a limb bakes whatever is nested inside it first, so nothing loses its
animation to a parent being removed.

## Scope

**In**

- The requested limbs are expanded with any recorded limb whose rig sits inside
  them, transitively
- Baking order is innermost first
- An OverRig knot nested inside, belonging to no recorded limb, aborts the
  operation with its name

**Out**

- No re-parenting of anything
- No baking of rigs this tool did not build
- No change to how a single, unnested limb bakes

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Nested recorded limb | Bake it first, then the limb containing it | What the user asked for, and the only order that preserves the inner limb's animation. |
| Ordering | Topological — a limb is baked once nothing recorded remains inside it | Handles chains three deep as naturally as one, without a depth counter to get wrong. |
| Foreign knot nested inside | Abort, name it, touch nothing | It is a child of the rig being deleted, so "leave it alone" is not physically available — deleting the parent takes it. Of the three real options, only refusing never destroys the user's own work. Re-parenting it out looks safer than it is: `parent` preserves the world transform at the current frame only, which misaligns an animated node's curves. Unblocking is one drag in the outliner. |
| Where the logic lives | Two pure functions | Nesting and ordering are exactly the kind of thing that is painful to debug in a scene and trivial to test as data. |

## Architecture

No new modules. `builder.py` gains two pure functions and uses them at the top of
`bake_limbs`.

```python
order_by_nesting(limbs, limb_members) -> list[str]
    Expand the requested limbs with any recorded limb nested inside them, and
    return them innermost first.

foreign_knots_inside(rig_paths, our_paths, overrig_made) -> list[str]
    OverRig knots sitting inside those rigs that belong to no recorded limb.
```

Both take the scene as data — `limb_members` is `{limb: [paths]}`,
`overrig_made` is `OverRig_knots` membership — so neither needs Maya to be
tested.

Nesting is decided by DAG path prefix: limb B is inside limb A when one of B's
recorded paths starts with one of A's paths followed by a separator. The
separator matters: `|foot_l_IK_feet_extra` is a different node, not a child of
`|foot_l_IK_feet`.

## Flow in `bake_limbs`

1. Read every recorded limb's members into `limb_members`.
2. `ordered = order_by_nesting(requested, limb_members)`.
3. Collect the paths of every rig about to be removed, and every path recorded
   across all limbs.
4. `foreign_knots_inside(...)` — if anything comes back, return a refusal naming
   it and change nothing.
5. Bake the limbs in `ordered`.

Steps 1–4 happen before the undo chunk opens, so a refusal leaves no trace.

## Error handling

| Situation | Behaviour |
|---|---|
| Nothing nested | `order_by_nesting` returns the request unchanged; no cost |
| Nested recorded limb | Added to the operation and baked first; the status line names everything baked |
| Nested foreign knot | Abort, name it, scene untouched |
| Nested limb has no manifest | Nothing to nest, so it cannot be detected this way; the existing reclaim pass frees it when its own turn comes |
| Cycle in the containment relation | Impossible in a DAG hierarchy; the ordering falls back to emitting the remainder rather than looping |

## Testing

`order_by_nesting`, plain Python: nothing nested returns the request unchanged;
a nested limb is added and comes first; a three-deep chain comes out innermost
first; requesting the inner limb alone does not drag in its container; two
independent nestings both resolve; a limb with no manifest survives the call; a
path that merely shares a prefix without a separator is not treated as nested.

`foreign_knots_inside`, plain Python: a knot inside a doomed rig and outside our
manifests is reported; one that is in our manifests is not; one outside the
doomed rigs is not; a knot equal to a rig root is not reported as nested inside
itself; results are sorted and de-duplicated.

Live, and this is the proof: recreate the exact failure — arm control parented
under the leg's, bake the leg — and require that the arm comes out baked and
free rather than constrained to a corpse, that the leg is free, and that the
scene returns to its pre-build node count.

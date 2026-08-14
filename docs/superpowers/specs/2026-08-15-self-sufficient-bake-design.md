# Baking a limb without a manifest

Date: 2026-08-15
Status: approved
Branch: `feature/overrig-picker`
Follows: `2026-08-14-bake-single-limb-design.md`

## Context

Baking a limb removes what the per-limb manifest records. That works for rigs
this tool built with the current code, and fails for everything else.

It failed in practice. The working scene ended up holding **two generations of
IK at once**:

| Generation | Nodes | In our manifest | In `OverRig_knots` |
|---|---|---|---|
| First | `foot_l_IK_feet`, `calf_l_IK_knee`, `base_IK_strech1..4`, `locator6..32`, `leng_base1..4` | no | yes |
| Second | `foot_l_IK_feet1`, `..._IK_knee1`, `base_IK_strech5..8`, `locator33..64` | yes | yes |

1290 nodes against 863 in a clean scene, and 69 locators that no bake would ever
remove.

The first generation was built by earlier code that recorded only three nodes per
limb in a flat `RigPicker_build` set. That set was then deleted while migrating
to per-limb sets, which orphaned the entire rig. Baking behaved correctly — it
removed what was recorded — and the user was left with locators that could not be
removed through the panel at all. The `1` suffixes on the second generation are a
symptom: the first generation still held the names.

The bug is not the leftover nodes. It is that **the tool can only remove what it
recorded**, so any rig built by an older version, or whose manifest was lost,
becomes permanently unremovable.

## Goal

"Bake this limb" frees the limb, whoever built the rig driving it and whenever.

## Scope

**In**

- After clearing the manifest, baking checks whether the limb's source joints are
  still constrained, and removes the OverRig rig responsible
- `OverRig_knots` membership is the proof that OverRig created a node
- Nodes reclaimed this way are counted and reported separately from manifest ones

**Out**

- No standalone "clean the whole scene" command
- No touching rigs that drive joints outside the limb being baked
- No attempt to salvage animation from an unrecorded rig beyond the normal bake

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| How an unrecorded rig is found | Walk the constraints on the limb's own three joints out to their drivers | Bounded by construction: the walk can only reach rigs that actually drive this limb, so it can never wander into another limb or another character. |
| What proves a node is OverRig's | Membership in `OverRig_knots` | OverRig records its top-level creations there even when our manifest missed them — the first generation is in that set. Using it means we never delete a constraint the user set up by hand. |
| What gets deleted | The driver's top-level ancestor, then the constraint node | Deleting the rig root takes its locators, joints and expressions with it. The constraint node is a child of the source joint and survives its driver's removal, so it needs deleting explicitly — that is exactly what left joints "freed" but still constrained. |
| Unrecognised driver | Left alone, named in the report | A constraint whose rig is not OverRig's is the user's business. |

## Mechanism

Per limb, after the manifest nodes are gone:

1. Collect the constraint nodes parented under the limb's three source joints.
2. For each, collect the transforms driving it.
3. Reduce each driver to its top-level DAG ancestor.
4. Keep the ancestors that appear in `OverRig_knots`; those are rig roots to
   remove.
5. Delete those roots, then delete the constraint nodes that pointed at them.

One pass is enough: an OverRig IK setup is a single layer of drivers beneath one
root.

Two helpers carry the logic and are pure, so they are tested without Maya:

```python
top_level(path) -> str
    "|a|b|c" -> "|a"

unrecorded_rig_roots(driver_paths, overrig_made) -> list[str]
    top-level ancestors of the drivers that OverRig created, sorted
```

The graph reading stays in a thin Maya-side function that calls both.

## Error handling

| Situation | Behaviour |
|---|---|
| No constraints left after the manifest pass | Nothing to do, no cost |
| Constraint driven by something not in `OverRig_knots` | Left in place, named in the status line |
| Driver already deleted | Constraint removed anyway if its remaining drivers are all gone |
| Source joint missing | Skipped |
| Deletion raises | The enclosing undo chunk still closes, so `Ctrl+Z` unwinds |

## Testing

- `top_level` — root-level path, nested path, already-top path, path without a
  leading separator.
- `unrecorded_rig_roots` — a driver nested under a known rig root resolves to
  that root; a driver that is itself the root resolves to itself; a driver under
  something unknown yields nothing; duplicates collapse; results are sorted;
  empty inputs yield nothing.
- Live, and this is the real proof: the scene currently holds an orphaned first
  generation. Baking every limb must remove it, bring the locator count to zero,
  leave no constraints on the twelve limb joints, and return the node count to
  the clean 863.

That last check is why the fix is verified by cleaning the actual mess rather
than by a synthetic case.

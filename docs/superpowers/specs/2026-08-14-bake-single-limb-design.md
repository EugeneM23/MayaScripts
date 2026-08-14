# Bake a single limb back to FK

Date: 2026-08-14
Status: approved
Branch: `feature/overrig-picker`
Follows: `2026-08-14-build-ik-limbs-design.md`

## Context

Build creates IK on all four limbs. Removing it was all-or-nothing: the only way
back was a full rebuild or OverRig's scene-global
`barn_fast_bake_source_obj_and_delete_knots()`. An animator who is happy with
three limbs and wants the fourth back on FK had to redo everything.

OverRig has no button for this, but it has every primitive, which reading the
MEL confirmed:

| Proc | Scope |
|---|---|
| `apply_Fast_Bake()` | the current selection — it refuses when nothing is selected |
| `delete_constraint_attributes_on_objects($objects)` | an explicit array; strips `blendParent*`, `blendOrient*`, `blendPoint*`, `blendAim*`, `MaxHandle*` and their keys |
| `return_constrained_object()` | walks a control's constraints back to the objects it drives |

Only `barn_fast_bake_source_obj_and_delete_knots()` is global, and not by
nature — it simply selects the whole set before working.

This was also confirmed in the live scene: two limbs were baked back to FK by
hand while the other two stayed on IK, animation intact, constraints gone from
the baked joints only.

## Scope

**In**

- `Bake+Delete` bakes every limb the current selection touches
- Selection may be an IK control, any descendant of one, or the limb's source
  joints — so the picker's own limb buttons drive it
- Per-limb manifest so the tool knows which node belongs to which limb
- One undo step for the whole operation

**Out**

- No FK→IK switching back and forth; baking is one-way
- No partial-range bake (see Decisions)
- No baking of OverRig setups this tool did not create

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Bake range | Full timeline, `apply_Fast_Bake` | The IK is being removed for good, so the whole animation has to transfer. `apply_range_Fast_Bake` would leave everything outside the range still expressed through an IK we then delete, corrupting the result. A range bake makes sense only when the rig stays. |
| Several limbs selected | Bake all of them | Matches intent and avoids scolding a reasonable action. Baking only the first would repeat the silent-partial-work mistake already found in character binding. |
| Nothing relevant selected | Do nothing, explain | An empty selection meaning "bake everything" is too destructive for a stray click. |
| Manifest granularity | One object set per limb | The flat set could not say which node belonged to which limb. `build` already works limb by limb, so recording per limb is nearly free. |
| Selecting source joints counts | Yes | Makes the picker itself the selector: press `Leg L`, press bake. `Main` selects all four limbs' joints, so "bake the whole rig" needs no special case and no dangerous empty-selection rule. |

## Architecture

No new modules. `builder.py` gains the per-limb manifest and the bake
operation; `picker_window.py` gains the button wiring.

```python
BUILD_SET_PREFIX = "RigPicker_build_"

limb_set(limb) -> str                    # "RigPicker_build_leg_l"
built_limbs() -> list[str]               # limbs with a non-empty set
has_build() -> bool
resolve_limbs(nodes, limb_members, scene_map) -> list[str]   # pure
limbs_in_selection(scene_map) -> list[str]                   # reads the scene
bake_limbs(scene_map, limbs) -> BuildResult
```

`resolve_limbs` is deliberately pure: it takes the node paths, a
`{limb: [recorded paths]}` mapping and the binding map, and returns limb names
in `LIMBS` order. All the fiddly logic — ancestor prefixes, the source-joint
route, de-duplication — lives there and is testable without Maya.
`limbs_in_selection` is the thin wrapper that reads the sets and the selection.

A node counts for a limb when it is one of that limb's recorded nodes, a
descendant of one (so a curve shape or an internal handle resolves), or one of
that limb's three source joints.

## The manifest cannot come from OverRig's own set

`OverRig_knots` records only the three renamed groups per limb. Everything else
the IK setup creates — the locators that drive it, the expressions, the
`pairBlend` nodes, and **two** parentConstraints per source joint rather than one
— is in no set at all.

Building the manifest by diffing that set therefore inherited the gap: baking a
limb removed the control and one constraint, and left the other constraint alive,
driven by a locator nothing knew about. The joint stayed constrained after being
"freed", and leftovers accumulated across builds until they started stealing
node names — which is why `foot_l_IK_feet` came back as `foot_l_IK_feet1`.

The manifest is therefore a diff of **every node in the scene** across the
limb's build, excluding `animCurve` types. That comes to roughly 68 nodes per
limb instead of three. animCurves are excluded because baking writes the
transferred animation into animCurves on the source joints, and those must
outlive the rig.

Measured on the working scene: build creates 271 nodes, baking one limb removes
68 and frees only that limb, baking the remaining three removes 203, and the
scene returns to exactly the node count it started at.

## The bake operation

Per limb, inside a single undo chunk covering all of them:

1. Resolve the limb's three source joints through the binding map.
2. `apply_Fast_Bake()` on those joints.
3. `delete_constraint_attributes_on_objects()` on the same joints.
4. Delete the limb's recorded nodes that still exist.
5. Delete the limb's set.

`teardown` becomes `bake_limbs(scene_map, built_limbs())` — the whole-rig case
is the same code with every limb passed in, which is also what a rebuild uses.

## Error handling

| Situation | Behaviour |
|---|---|
| Picker not bound | Refuse, ask for Connect |
| Nothing selected | Do nothing, status line asks for a limb control or a picker limb button |
| Selection touches no built limb | Do nothing, say so |
| Limb has no manifest set (never built, or already baked) | Skip it, name it in the report |
| Limb's source joints missing from the binding | Skip it, name it in the report |
| A limb raises inside OverRig | Abort, close the undo chunk in `finally` so `Ctrl+Z` unwinds |

## Testing

- `resolve_limbs` — plain Python, and this is where the real coverage sits:
  a recorded node resolves; a descendant path resolves; a source joint resolves;
  a shape under a control resolves; an unrelated node resolves to nothing; two
  limbs' controls give both names; duplicates collapse; results come back in
  `LIMBS` order; an empty manifest with a source-joint hit still resolves.
- `limb_set` and `built_limbs` — naming and filtering, plain Python for the
  former.
- The bake itself, live through the bridge: build all four, bake one, and check
  that the baked limb has keys and no constraints while the other three keep
  their controls and constraints; then bake the remaining three and check the
  manifest sets are gone.

## Migration note

The scene currently holds a stale flat `RigPicker_build` set from the previous
design. Nothing reads it after this change, so it is deleted during
verification rather than being migrated — the build it described is disposable
test material.

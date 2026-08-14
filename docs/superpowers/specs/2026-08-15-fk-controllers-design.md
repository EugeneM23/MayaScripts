# Build FK — selection markers on every animator bone

Date: 2026-08-15
Status: approved
Branch: `feature/overrig-picker`

## Context

A temporary `Build FK` button that puts a classic FK-looking controller on every
bone, for selection convenience. How these coexist with the IK build and other
OverRig add-ons is deliberately left for later.

The requirement that shapes the whole design: controllers must be clearly
visible, must not sit inside the geometry, and must not blur into each other.

## Scope

**In**

- A controller on each of the 64 animator-facing joints, the same set the picker
  draws
- Ring shape, sized from the skinned mesh so it encircles the limb
- Colour by rigging convention
- Recorded in a manifest; pressing again rebuilds

**Out**

- The controllers drive nothing. They follow their bone and are selectable; that
  is all.
- No interaction with the IK build, no FK/IK switching, no space switching
- No controllers on twist joints, UE export helpers, weapons, camera or
  `center_of_mass`

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Drive the bones? | No — inert markers | What was asked for, and it sidesteps the IK conflict that was explicitly deferred: two drivers on one joint. |
| How they follow the bone | Parented under the joint, local transforms zeroed | Cheapest and exact. A constraint would add nodes and a second thing to clean up for no gain when nothing is driven. |
| Transforms locked | Yes | They drive nothing, so a draggable controller would invite the question of why moving it does nothing. Locking states the intent. |
| Which bones | The picker's 64 | Twist joints sit *inside* the forearm and thigh — their rings would overlap the main ones exactly, which is the visual merging the request warns against, and they are driven so animating them is meaningless. |
| Shape | Ring perpendicular to the bone | Local X runs along the bone on this skeleton (verified: `+X` for arms, spine, fingers, clavicle, neck; `-X` for legs — the sign differs, the axis does not). A ring in the joint's YZ plane therefore encircles the limb instead of lying inside it. |
| Size | 85th percentile of the perpendicular spread of the skinned vertices, plus a margin | Bone length is useless here. Measured on this rig: `pelvis` reads 3.68 because its first child sits on top of it, `lowerarm_l` reads 9.08 because its first child is a twist joint, `head` reads 0 for having no children at all. Skin weights give the real cross-section. |

## Sizing in detail

1. Fetch weights and world points per skinCluster through the API —
   `MFnSkinCluster.getWeights` and `MFnMesh.getPoints`, two calls per mesh.
   Measured at 0.07 s for 48705 vertices × 89 influences; per-vertex `skinPercent`
   is not viable at that size.
2. **Roll driven joints up.** Every influence is attributed to its nearest
   ancestor that has a controller, so `upperarm_twist_01_l` counts toward
   `upperarm_l`. Without this, `upperarm_l` and `thigh_l` collect zero vertices —
   their weight is split with their twists and never dominates.
3. Assign each vertex to the target with the highest rolled-up weight.
4. Radius is the 85th percentile of the vertices' perpendicular distance from the
   bone axis, times a small margin so the ring clears the surface.
5. Joints that still collect nothing — `root`, `spine_01`, `spine_05`, `neck_01`,
   `neck_02`, which lose the contest to fatter neighbours — get a second pass
   over non-dominant weights, then fall back to a neighbour-derived size.
6. `root` is special-cased: a large ring lying flat on the ground, sized from the
   character's bounding box, since it represents world position rather than a bone.

## Keeping them apart visually

Three independent mechanisms, because colour alone is not enough at finger scale:

- **True per-joint size** — a finger ring is about 1 cm, the pelvis about 15.
- **Colour by side**, matching the picker so the convention is shared: left blue,
  right red, centre yellow. Bright, since visibility was the requirement.
- **Each ring is perpendicular to its own bone**, so along a chain neighbouring
  rings present at different angles rather than stacking into a tube.

## Architecture

New module `maya_overrig/fkcontrols.py`.

```python
FK_SET = "RigPicker_fk"

controller_name(joint) -> str
colour_for(region) -> tuple[float, float, float]
rollup(influences, targets, parent_of) -> dict[str, str | None]
radius_from(distances, percentile=0.85, margin=1.15) -> float

has_fk() -> bool
build_fk(scene_map) -> FkResult
remove_fk() -> int
```

The first four are pure — `parent_of` is a plain `{joint: parent}` mapping, so
the rollup that caused the zero-vertex bug is testable without Maya. The vertex
work stays in a thin API wrapper.

`picker_window.py` gains a `Build FK` button and `build_fk_controls()`.

## Error handling

| Situation | Behaviour |
|---|---|
| Picker not bound | Refuse, ask for Connect |
| No skinCluster in the scene | Build anyway using neighbour-derived sizes, and say so in the status line |
| A joint missing from the binding | Skipped, counted in the report |
| A radius computes to zero or nonsense | Clamped to a floor derived from character height, so no invisible or degenerate ring |
| Pressing again | Existing controllers removed first, then rebuilt |

## Testing

Pure: `controller_name`; `colour_for` gives left and right different colours and
all centre regions the same; `rollup` attributes a twist joint to its targeted
ancestor, leaves an already-targeted joint as itself, returns `None` for a joint
with no targeted ancestor, and walks more than one level; `radius_from` takes the
percentile and applies the margin, handles a single distance, and floors an empty
input.

Live: 64 controllers created; every radius inside a sane range with fingers
smaller than the pelvis; none degenerate; all parented under their joints; a
rebuild leaves the count at 64 rather than doubling; removal takes the scene back
to its previous node count. Then a screenshot — the visibility requirement cannot
be verified any other way.

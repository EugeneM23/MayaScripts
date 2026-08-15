# Manny → protective-suit retarget — constraint-driven, hybrid offset

Date: 2026-08-15
Status: design approved by the user, implementation follows
Branch: `feature/overrig-picker`

## The job

Two skeletons share the open scene `Manny_Sckeleton.ma`:

- **Source** — `SKM_Manny_Simple|root`, 93 joints, stock UE5 Manny, skinned to
  `Skin_3p` and `Hands_1P`. Sits at the origin.
- **Target** — `Mesh_protective_suit:root`, **a reference** from
  `.../Protection_suite/Base_mesh/Mesh_protective suit.fbx`, 67 joints, skinned
  to `Mesh_protective_suit:head_low` (that one mesh is the whole suit body
  despite the name). Sits 145.017 cm away in +X.

Animation authored on Manny must drive the suit. Nothing is animated yet — this
builds the transfer rig, not a bake.

## What the two skeletons actually are

Manny is UE5-schema. The suit is UE4-schema. The difference is entirely
*subtractive* — every one of the suit's 67 joints has an exact name twin in
Manny, and nothing on the suit is unmatched. Manny carries 26 extra joints the
suit has no equivalent for:

| Manny has | Suit has | Consequence |
|---|---|---|
| `spine_01..05` | `spine_01..03` | needs a real mapping, see below |
| `neck_01`, `neck_02` | `neck_01` | harmless — `head` is a direct match |
| two twists per segment | one twist | second twist is simply unused |
| `*_metacarpal` ×8 | — | finger bases lose a little travel |
| `weapon_l/r`, `camera_root`, `camera_bone`, `center_of_mass`, `interaction` | — | not animation-bearing here |
| `root` (a joint) | `root` (a **group**, the FBX conversion node) | the suit has no root joint at all |

Height ratio 1.018, limb ratios 0.89–1.17. Close enough that no scale
compensation is wanted.

## The spine mapping is not the name mapping

Matching `spine_0N` to `spine_0N` is wrong. The suit hangs its clavicles and
neck on `spine_03`; Manny hangs them on `spine_05`. Those two are the same bone
semantically — the chest. Measuring the world-orientation difference between the
two rest poses settles it:

| suit bone | vs same name | vs semantic twin | twin |
|---|---|---|---|
| `spine_01` | 3.46° | **0.00°** | `spine_02` |
| `spine_02` | 14.06° | **2.75°** | `spine_04` |
| `spine_03` | 5.89° | **0.65°** | `spine_05` |

Normalised heights along the pelvis→chest span agree independently: suit
`spine_01` at 0.250 against Manny `spine_02` at 0.229, suit `spine_02` at 0.693
against Manny `spine_04` at 0.576, both chests at 1.0. The semantic map wins on
both counts and is the one we use.

The two Manny spine bones left over — `spine_01` and `spine_03` — do not drive
anything directly, but their contribution is not lost: every suit bone receives
its **world** orientation from its own source, so the suit's chest matches
Manny's chest exactly however Manny distributed the bend to get there. Only the
shape of the curve between pelvis and chest differs.

## Rest-pose divergence, measured

This is exactly what `maintainOffset` freezes into each constraint:

- body: mean 10.4°, max 23.9° (both clavicles)
- legs: 4.3–9.3°, uniformly small
- fingers: **mean 28.8°, max 54.7°**

The clavicle number is real geometry, not an axis artifact: the suit's clavicle
runs 7 cm further back than Manny's and is 2 cm shorter. Keeping that is keeping
the suit's shoulder shape.

The finger number is a **pose** difference. Manny is an FPS rig — it carries
`weapon_l/r` bones and a `Hands_1P` mesh, and its hand rests closed around a gun
grip. The suit's fingers rest relaxed.

## Decision: hybrid offset policy

Chosen by the user from three options.

- **Body — `maintainOffset=True`.** The suit keeps its own rest pose and
  silhouette and receives Manny's *relative* world rotation. This is the normal
  retarget contract between two different characters: 4–10° of A-pose variance
  is exactly what the offset is for.
- **Fingers — `maintainOffset=False`.** Absolute copy, so Manny's grip reaches
  the suit instead of the suit's fingers idling at 29° from it.
- **Spine — semantic map**, where the offset is near zero anyway.

The finger mode is the one call this design is not certain about in advance.
28.8° reads as pose rather than a bind-axis convention (a convention mismatch
would land near 90° or 180°), but it is settled by looking at the built result,
not by argument. `finger_mode` is therefore a parameter; flipping all 30 finger
bones back to offset mode is one keyword.

## Decision: never `parentConstraint` anything carrying the side offset

The user keeps the suit 145 cm to the side so both characters are visible at
once. That makes the choice of constraint type load-bearing.

`parentConstraint(mo=True)` stores its offset **in the source's space**. When
Manny turns on the spot, a suit held by a parent constraint does not turn beside
him — it swings through an arc around him, 145 cm out, while any world-space
constraint elsewhere on the body stays put. The character tears.

`pointConstraint(mo=True)` stores a **world** translation offset, which does not
rotate with the source. Manny turning on the spot then turns the suit on the
spot beside him, which is what the offset is meant to look like.

So: the pelvis and the two ik roots go through `point` + `orient`, never
`parent`. `parentConstraint` appears only where both ends live inside the suit
and no side offset is involved — the `ik_*` export helpers.

The group `Mesh_protective_suit:root` is **not constrained at all**. It is a
referenced node and constraining it would buy nothing: the pelvis is driven in
world space and would override it. The side offset therefore lives in the
constraints' own `offset` attributes, and `set_side_offset(dx)` rewrites them,
so putting the suit exactly inside Manny is one call rather than a rebuild.

## Wiring

| target (suit) | source | constraint |
|---|---|---|
| `pelvis` | `pelvis` | `point` + `orient`, `mo=True` |
| 29 remaining body joints | name twin, or spine map | `orient`, `mo=True` |
| 30 finger joints | name twin | `orient`, `mo=False` |
| `ik_foot_root`, `ik_hand_root` | Manny `root` | `point` + `orient`, `mo=True` |
| `ik_foot_l/r` | suit `foot_l/r` | `parent`, `mo=True` |
| `ik_hand_gun` | suit `hand_r` | `parent`, `mo=True` |
| `ik_hand_l` | suit `hand_l` | `parent`, `mo=True` |

`ik_hand_r` needs nothing — it is a zero-local child of `ik_hand_gun` and
inherits, exactly as on Manny. The four export-helper constraints mirror the
four Manny already carries on its own `ik_*` bones.

## Module shape

One file, `maya_retarget.py`, at the repository root: single-file, pure
`maya.cmds`, no Qt, no package — the root-level convention, alongside
`maya_rig_constraints.py`.

The fiddly part is pushed into a pure function so it can be tested without Maya:

```
build_bone_map(suit_names, manny_names, finger_mode) -> {suit: (manny, mode)}
```

It takes the two joint-name lists as data, applies `SPINE_MAP`, classifies
fingers by name, drops the `ik_*` helpers into their own table, and reports
anything it could not match. Everything that touches Maya — resolving joints
under each root, creating constraints, recording them — stays thin around it.

Bookkeeping follows the lesson the OverRig work paid for: every created node
goes into an `objectSet` named `retarget_manny_to_suit`, and teardown deletes by
**set membership**, never by name.

Public surface:

- `build_retarget(finger_mode="absolute", include_ik_helpers=True)`
- `remove_retarget()`
- `set_side_offset(dx)`
- `show_retarget_ui()` — three buttons, matching the house style

## Known limits, accepted

- **Feet will not land in Manny's footprints.** Calf ratio 0.952 and foot ratio
  1.168 mean a rotation-only transfer drifts at the contact. This is inherent to
  the method; IK foot pinning would be a separate job.
- **Metacarpal travel is dropped.** The suit's finger bases hang straight off
  the hand, so Manny's metacarpal spread does not reach them. Orientation of
  every finger bone is still exact, since each is driven in world space.
- **Manny's second twists, `neck_02`, `spine_01` and `spine_03` drive nothing
  directly.** Their contribution arrives through the world orientation of the
  bones that do map.
- **The suit has no root joint**, so a UE export of the suit would need one
  built. Out of scope here.

## Verification

Unit tests cover `build_bone_map` on `mayapy` with no Maya session, per the
repo's existing pattern.

The real proof is live, per the repo rule that unit tests here have repeatedly
passed over a broken scene: pose Manny at several bones, settle time, and
measure that each suit bone moved by the same world delta — near zero for
offset-mode bones and matching absolutely for finger bones. The verify script
lands in `docs/superpowers/plans/verify_retarget.py`. It must respect the
bridge hygiene already recorded in `CLAUDE.md`: disable autoKey around pokes,
wiggle time to settle before reading, restore what it read rather than writing
literal rest values, and never call `cmds.undo()`.

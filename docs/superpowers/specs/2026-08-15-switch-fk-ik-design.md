# Switch FK/IK — convert a limb to the opposite rig type

Date: 2026-08-15
Status: approved, semi-test version by declaration
Branch: `feature/overrig-picker`
Follows: `2026-08-15-fk-knots-design.md`

## Goal

Select any controller of an arm or leg, press `Switch FK/IK`, and the limb
converts to the opposite type — FK becomes IK, IK becomes FK — with the
animation re-baked correctly at every step. Arms and legs only; spine later;
the whole arrangement gets a proper reorganisation later ("полу тестовый
вариант" by the user's own words).

## Scope

**In**

- `Switch FK/IK` button; works on whatever limbs the selection touches
- Direction decided by the limb's current state
- Per-chain FK manifest (`RigPicker_fk_<chain>`), the structural prerequisite —
  a flat set cannot release one leg without releasing everything
- Finger chains survive an arm switch: re-hung onto the hand control of
  whichever rig the arm ends up with
- Animation re-baked at every step; zero drift is the acceptance test

**Out**

- Spine and neck switching
- Reworking the big buttons' mutual-exclusion guards (mixed states arise from
  Switch; the big buttons keep their current behaviour until the later
  reorganisation)
- Preserving the `ball` control on a leg that goes IK — the IK leg never had
  one; it returns when the leg switches back to FK

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Direction | From the limb's current state, per limb | Matches the request exactly; two selected limbs each switch their own way. |
| Fingers on an arm switch | Re-hung, not baked down | Chosen by the user. `apply_Parent_out` lifts the finger chains to world (re-baked), the arm converts, `apply_Parent_in` hangs them on the new hand control. Losing finger controls to an arm switch would be a destructive surprise. |
| New FK limb in a mixed scene | Couples to its parent's controller only if that controller exists; otherwise world-space, said in the status line | In a mixed state there may be nothing to couple to. Honest limitation of the semi-test version. |
| No rig on the limb | Skip and say so | Switch converts; it does not create from nothing. |
| Where the logic lives | `fkcontrols.switch_limbs` | It orchestrates existing pieces — `builder.bake_limbs`, `builder.build`, per-chain FK build/bake — and `fkcontrols` already imports `builder`. A third module would add a file to hold one function. |

## Mechanics

**FK → IK** (arm; legs skip the finger bracket):

1. `apply_Parent_out` each recorded finger chain of that hand — to world,
   re-baked.
2. Bake the limb's FK chain back to the bones (per-chain bake).
3. `builder.build(scene_map, only=[limb])` — the existing IK build, restricted.
4. `apply_Parent_in` each finger chain into the IK hand control, found through
   the limb's IK manifest (never by bare name — OverRig suffixes on collision).

**IK → FK**:

1. `apply_Parent_out` fingers if they hang on the IK hand control.
2. `builder.bake_limbs(scene_map, [limb])` — existing per-limb IK bake.
3. Build the limb's FK chain (`build_fk` restricted to it); couple to the
   parent controller when present.
4. `apply_Parent_in` fingers into the new FK hand control.

One undo chunk per Switch press. Every re-parent uses OverRig's procs because
they re-bake animation into the new space — a bare `parent` preserves only the
current frame.

**Per-chain manifest.** `build_fk` records each chain's scene diff into its own
`RigPicker_fk_<chain>` set, and couples each chain right after building it so
the coupling nodes land in that chain's set (parents precede children in the
chain table, so the target controller already exists). `bake_fk` takes an
optional chain subset, expands it with chains nested inside (reusing
`builder.order_by_nesting` — it is generic over `{name: [paths]}`), bakes those
chains' bones, deletes their recorded nodes and sets, and runs the reclaim
safety net. A legacy flat `RigPicker_fk` set, if present, is absorbed by a full
bake.

## Error handling

| Situation | Behaviour |
|---|---|
| Not bound | Refuse, ask for Connect |
| Selection touches no arm or leg | Nothing happens, status line says what to select |
| Limb has neither FK nor IK | Skipped, named in the report |
| Both recorded on one limb (should be impossible) | Treated as FK→IK: FK baked first, so the scene converges rather than stacking |
| Parent controller for coupling missing | New FK chain stays world-space, noted in the status line |
| `apply_Parent_out` misbehaves | It is probed by experiment before anything depends on it; the switch aborts inside its undo chunk if the re-hang fails |

## Testing

Pure: chain-set naming; the finger-chains-of-a-limb mapping; existing chain and
attach tests unchanged.

Live, the proof sequence: key real animation; full Build FK; switch a leg —
the leg is IK, the rest of the FK intact, zero drift; switch it back — FK
again, zero drift; switch an arm — finger controls survive, hang from the IK
hand, follow it when it moves, zero drift; bake everything back — scene at
baseline, animation on the bones.

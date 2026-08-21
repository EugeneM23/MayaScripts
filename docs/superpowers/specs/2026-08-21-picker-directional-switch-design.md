# Directional FK/IK buttons in the picker — design

**Date:** 2026-08-21
**Status:** designed.

## The ask

> «в самом пикере из кнопок для выделения контролов на верхней панели оставим
> только ALl все остальные не нужны. Кнопка FK limbs пусть переводит
> выделенную конечность или кость в ФК а кнопочка IK Limbs в ик от кнопочки
> switch давай избавимся»

Three UI changes in one sentence:

1. of the selection-group buttons, only **All** stays;
2. **FK Limbs** stops being a Build toggle and becomes an action: bring the
   selected limb (controller, bone or picker button) to FK; a new
   **IK Limbs** does the same toward IK;
3. the **Switch FK/IK** button goes.

## The design

**Group buttons.** `_GROUP_BUTTONS` shrinks to `(("All", "all"),)`. The
mechanism (table-driven grid, `bodymap.group_members`) stays — the other
groups remain selectable through the map itself, which is what the map is
for; the row of nine buttons duplicated it.

**Directional conversion** is a thin policy over machinery that already
exists and is already live-proven. New in `fkcontrols`:

- `limbs_to_convert(limbs, states, to_ik)` — pure. `states` is
  `{limb: (is_ik, is_fk)}`. A limb already in the asked state is left alone
  and NAMED (pressing FK on an FK arm must say "already FK", not rebuild
  it); one in the opposite state switches; a bare one is built directly in
  the asked type.
- `convert_limbs(scene_map, limbs, to_ik)` — the orchestrator, returning
  `(done, skipped, message)` like `switch_limbs`. The switching (and, for
  IK, the bare-chain build — `switch_limbs` already builds IK on a bare
  chain) goes through **`switch_limbs` itself**: riders, abort handling,
  re-hangs, the mel gate — all the paid-for machinery rides along. Bare
  chains asked to FK go through `build_fk(only=...)`, the same call the
  hybrid Build and Switch already use. Nothing new touches the scene.

`switch_limbs` itself STAYS: it is the engine under `convert_limbs`, the
auto-IK path of `connect.py`, and the proof harness of three verify scripts.
Only the button dies.

**The window.** `switch_selected_limbs`'s selection resolution (bake_targets
+ switchable_bones, innermost owner winning) is extracted into
`_selected_limbs()`; two thin slots call
`convert_limbs(..., to_ik=False/True)`. The FK Limbs toggle becomes a plain
button; IK Limbs appears beside it; the Switch button and its slot are
deleted. **Build always builds the hybrid rig now** — the full-FK build
stays reachable as `rebuild(fk_limbs=True)` (the API and
`verify_hybrid_build.py` use it) and, for the animator, as
Build → select all → FK Limbs.

A clavicle in the selection still resolves to its arm (`CLAVICLE_OF`, via
`switchable_bones`) — pressing IK Limbs with a clavicle bone selected
converts the arm, exactly as Switch used to.

## What this deliberately does not change

`SWITCHABLE`, the manifests, rider handling, the mel gate, the abort paths —
untouched. The spine still answers "select an arm or leg". No new scene
semantics: a press is either a `switch_limbs` call, a `build_fk` call, or a
named refusal.

## Proof

Unit: `limbs_to_convert` over the six state/direction combinations;
`convert_limbs` refusing with the OverRig message through the existing
fake-gate harness; the group table pinned to All alone.

Live (bridge runner): the toolbar holds FK Limbs, IK Limbs, no Switch, one
group button; on the hybrid rig — select an IK arm's bone, FK Limbs → the
chain is FK; FK Limbs again → "already FK" and nothing rebuilt; IK Limbs →
back to IK; a bare chain (after Bake+Delete of one limb) goes straight to
the asked type from either button. Panel screenshot via `widget.grab()`
(CLAUDE.md bridge note 3), looked at.

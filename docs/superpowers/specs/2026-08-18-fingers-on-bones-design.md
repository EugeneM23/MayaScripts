# Fingers on the bones — design

**Date:** 2026-08-18
**Status:** designed.

## The ask

> «Давай на время откажемся от создания ФК контроллов для пальцев рук. Буду
> анимировать на костях.»

Stop building FK controllers for the ten hand-finger chains. The animator poses
finger **bones** directly instead. Everything else about the rig is unchanged.

Answered by the user when asked:

- **The picker's finger buttons select the BONES.** Not left dimmed. 38 dead
  buttons would be worse than no buttons, and hunting individual finger joints
  in the viewport is exactly what the body map exists to avoid.

## Scope: hands only, and only the build

"Пальцев рук" is the hand fingers — the ten chains `index/middle/ring/pinky/
thumb` × `_l/_r` — 19 bones per hand, 38 in all. `ball_l`/`ball_r` are toes in
name only; they belong to the leg chains and are untouched.

Both build modes drop them: the default hybrid Build and the **FK Limbs** full-FK
Build. The user said "не создавать" without qualification, and a full-FK build
that quietly brought finger controls back would be a trap of its own.

## Why the finger chains stay in `CHAINS`

The obvious move — delete `_finger_chains()` from the table — is wrong twice
over.

**Scenes already rigged.** An animator's file built yesterday has ten
`RigPicker_fk_<finger>` sets and 38 controllers in it. Teardown is driven by
`CHAINS`: `_bake_fk_chains` reads `chain_members(name)` for `name, _ in CHAINS`,
and `bake_targets` builds its candidate list the same way. A finger chain absent
from the table is a rig nothing can bake and nothing can find — live
controllers, unrecorded, exactly the failure mode traps 3, 5 and 16 were all
about.

**"На время."** The hard-won knowledge in this area is not in the table, it is in
the code that hangs a chain on an IK hand: through `chain_root`, never `chain[0]`
(trap 21), onto `<limb>_IK_anchor` and never the control (the fingers tore off a
hand at full extension), lifted and re-hung around a switch. Deleting the table
entry leaves that code unreachable and unmaintained; leaving it reachable and
merely unfed keeps it honest.

So the change is one of **policy, not data**: a new `BUILDABLE` names the chains
a build may create, and `CHAINS` keeps describing what the rig can contain.

```python
FINGER_CHAINS = tuple(name for name, _ in _finger_chains())
BUILDABLE     = tuple(n for n, _ in CHAINS if n not in FINGER_CHAINS)
HYBRID_FK_CHAINS = tuple(n for n in BUILDABLE if n not in LIMB_CHAINS)
```

`build_fk` filters its loop through `BUILDABLE` — including an explicit `only=`,
so no caller can ask for a finger chain and get one. Its teardown still runs
over everything recorded, which is what lets a Build clean up yesterday's finger
rig on the way past.

Reverting is those three lines and the tests that pin them.

## The picker: one bone exception, and the controller still wins

`pickerstate.resolve` gains a third, optional argument:

```python
resolve(fk_nodes, ik_nodes, bone_nodes=None)
```

`bone_nodes` is `{joint: long path}` for buttons allowed to fall back to the bone
when no controller exists. The controller is tried first and always wins, so:

- today, finger buttons select `index_01_l`;
- a scene rigged before this change still selects `index_01_l_FK_ctrl`;
- if finger controls come back, nothing here needs touching.

**The policy stays out of the pure module.** `pickerstate` does not know what a
finger is; it falls back for whatever the caller offers. `picker_window` offers
`fkchains.FINGER_JOINTS` resolved through the bound subtree — so the exception is
one line in the window, next to the binding it depends on, and the pure module
stays "controller if there is one, else the fallback the caller allowed".

Everything downstream of `resolve` needs no change, and each for a reason worth
recording:

| operation | with a finger bone selected |
|---|---|
| selection sync | the button lights — it matches on the full DAG path, so another character's `index_01_l` cannot |
| Switch | fingers are not in `SWITCHABLE`; `switchable_bones` never offers them. "Select an arm or leg" |
| Bake+Delete | `bake_targets` maps the bone to `index_l`, which is neither a built limb nor a chain with members → nothing happens |

That last one is the important one, and it fails in the safe direction: nothing,
never the wrong rig. It is also why the bone fallback needs no guard of its
own — the resolution feeds selection, and selection alone.

## Two nodes that stopped being built

`rebuild` and `_rehang_riders` both asked for `_limb_anchor(scene_map, limb)`
*before* checking whether any finger chain wanted hanging, and `_limb_anchor`
creates the locator on demand. With no finger rigs that is a locator, a parent
constraint and a manifest entry per arm, built for nothing, on every Build.

Both now compute the rider list first and return early when it is empty. The
anchor machinery is untouched — it is still what fingers hang on when they come
back, and a scene that has finger rigs still gets its anchor.

## What the animator sees

- Build: 10 FK controllers instead of 48 in hybrid, 26 instead of 64 with FK
  Limbs on. No rings on the hands.
- The finger buttons are live and select bones — the hand groups (`Hand L`,
  `Hand R`) select all 19 bones of a hand at once.
- Finger bones carry no constraint and no baked curve from us, so they take keys
  directly, and their local rotate values are the bind orientation this skeleton
  keeps in its rotate channels (never key a literal 0 there — trap 30).
- Switch on an arm no longer has riders to lift, so an arm converts with one
  bake instead of one bake plus ten re-parents.
- The Build tooltip and the Switch tooltip both promised fingers; both now say
  what happens instead.

## Verification

`docs/superpowers/plans/verify_fingers_on_bones.py` — the live proof, in the
animator's own Manny scene. Ten gates: no finger controller and no finger
manifest after either build mode, finger bones unconstrained and keyable, no IK
anchor created, the picker resolution pointing at bones, an arm Switch and a
Bake+Delete both still clean.

Four existing verify scripts asserted the opposite and were rewritten rather
than deleted — `verify_arm_switch`, `verify_hybrid_build`, `verify_ik_under_root`
and `verify_missing_bones` each checked "the finger hangs on the hand". Their
gates now check that no finger controller exists and that the hand's bones are
free. `verify_missing_bones` keeps its point: it was the proof for trap 21, and
trap 21 is about `chain_root`, which the spine and the legs still exercise.

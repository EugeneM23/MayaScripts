# Weapon aim — design

**Date:** 2026-08-17
**Status:** designed.

## The ask

OverRig has an aim button: with an object selected it creates two locators —
one the object looks at, one that fixes its side rotation axis — and the object
is then aim-constrained to them. The animator wants that as **one button in
SceneSetup's weapon block**, with the locators placed automatically: the first
a little past the sword's tip, the second at the same distance along another
axis.

And it has to come apart the way the rest of the rig does: selecting the sword
or either locator in the viewport and pressing **Bake+Delete** in the Rig
Picker must bake *only* the sword and its aim, leaving the character's rig
alone.

Answered by the user during brainstorming:

- Aim works on the weapon **wherever it is** — in the hand under `weapon_r` or
  out in world after Connect Arms. The button does not check and does not care.
- The distance is computed **automatically from the model's size**. No field in
  the UI: a locator that landed wrong can be dragged, which is the OverRig
  workflow anyway.
- Selection happens **in the viewport**; the existing Bake+Delete button in the
  picker is the one that gets pressed. No new buttons in the body map.
- A second Aim press **refuses on the status line**. Removal is Bake+Delete
  only, so a stray press cannot cost anything.

## How OverRig's aim actually works, and why that shapes this

`make_aim_from_selected(1)` does **not** build the aim. It creates the two
locators on the object and registers a run-once
`scriptJob -ro 1 -cf "SomethingSelected"`; the real rig — parentConstraint the
locators to the source, bake, delete the constraints, then
`aimConstraint -mo -aimVector 1 0 0 -upVector 0 1 0 -worldUpType object
-worldUpObject <side>` back onto the source — is built **later, when the
animator deselects**. That gap is exactly where the locators get dragged into
place by hand.

We need placement *and* the build in one press, and we need a node diff around
the whole thing to record a manifest. So the deferred half cannot stay
deferred: a build that lands after our press is outside our undo chunk and
outside our diff, and the job would still be armed to fire a second time. This
project has paid for deferred-behaviour-plus-node-diffs more than once
(traps 5, 13, 16).

**The chosen approach: repeat the body of `make_aim_from_selected` in Python,
synchronously.** Same procs, same order, no scriptJob:

| step | proc | what it does |
|---|---|---|
| 1 | `BOVER_10_2_4b209c5c00abddc3e3509a14326e2488(src, "OverRig_rig_objects")` | records the source, as the native button does |
| 2 | `BOVER_10_2_c642429ed9a3aabf65a66eefcd97bfbb()` | creates `<name>_top` and `<name>_side`, snapped onto the source; returns tops then sides |
| 3 | `BOVER_10_2_2e50fb684e35f7dc58ab390d98530944({0.45,0.7,0.45})` | outliner colour, on the selection the previous proc left (the tops) |
| 4 | `BOVER_10_2_6de8028af587b467034457b4d6349f89(1)` | locator size, on both |
| 5 | *(ours)* | move the two locators to the computed places |
| 6 | `BOVER_10_2_4b209...(tops/sides, "OverRig_knots")` | registers them, as the native button does |
| 7 | `BOVER_10_2_10df34add5a583f84d24608e860c1b4b()` | **the deferred half, called directly**: constrain, bake, aim-constrain |

Step 7 is driven by MEL globals (`$select_joint`, `$select_loc_top`,
`$select_loc_side`) that step 2 sets, not by the selection, so calling it
straight after step 5 is well defined. Verified present in the live session:
all six procs exist.

The cost of this approach is that four of the six procs are internal,
hash-named. They are `global proc` and stable within v10.2, but an OverRig
update can rename them. So every one of them is checked with
`exists` up front and the press refuses with a message naming the missing proc
— never a traceback out of a UI callback (trap 20).

Deliberately not used: `assign_Sw_System` and `assign_Sword_pivot_System`, the
sword-specific variants. They want a hand control as a second selection and
build a pivot system; the plain aim is what the user described.

## Where the locators go

Measured on the real model in the user's scene (`LongSwordMesh`, 1382 points),
extents in the **model's own local frame**:

| local axis | min | max | extent | what it is |
|---|---|---|---|---|
| X | −15.576 | 15.576 | 31.152 | the crossguard — the plane of the blade |
| **Y** | −31.119 | **115.925** | **147.043** | **the blade**; the tip is at +115.925 |
| Z | −1.570 | 1.570 | 3.141 | the blade's thickness |

So the rule is read off the geometry, not off any axis convention:

- **blade axis** = the local axis with the largest extent, ties broken by axis
  order X before Y before Z so the answer never depends on sort stability.
  **The tip** = the end of the box further from the origin, signed — the origin
  sits in the grip because the carrier seats the model on the bone, and taking
  the *signed* further end is what makes a model authored along −Y work without
  a special case.
- **`_top`** sits on the blade axis at `tip * (1 + MARGIN)`, `MARGIN = 0.15`.
  On this sword: Y = 133.313, about 17 units past the tip.
- **`_side`** sits on the second-largest axis (here X, the plane of the blade)
  at the **same distance**, `|133.313|`, signed by the further end of that axis
  and positive on a tie — a blade is symmetric across its width, so the tie is
  the normal case.

Distance is the same for both because the user asked for that, and it reads
well: a long lever makes the roll control precise, and the locator sits clear
of the geometry where it can be clicked.

**Why placing by geometry is correct even though OverRig hardcodes
`aimVector 1 0 0`.** The constraint is built with `-mo`, so the offset is
measured at build time and the direction that tracks the target afterwards is
whatever direction pointed at it *when the offset was taken* — the blade, not
the local +X. Placing the locators along the real blade is therefore not a
workaround, it is the thing that makes the aim intuitive. Placing them along
local +X would aim a direction 90° off the blade on this model.

Two consequences worth stating:

- The aim is set up **against the pose on the current frame** — where the
  timeline stands when the button is pressed. Same class of caveat as "Build FK
  bakes the pose the skeleton stands in".
- **Nothing to measure, no aim.** `attach.model_root` falls back to the carrier
  when it finds no mesh, and a degenerate mesh can measure zero. So the press
  refuses whenever there are no mesh points at all *or* the blade extent is not
  greater than zero, rather than inventing a distance.

Size and colour are exactly the native button's (`size_lock` 1, outliner colour
`0.45/0.7/0.45`), so the locators look like every other OverRig locator.

## The aim goes on the geometry, not on the carrier

`attach.model_root(carrier)` — the same node Connect hangs the IK hands on.
Three reasons:

1. what the animator grabs in the viewport is the geometry (trap 34);
2. the IK hands ride it after Connect, so they follow the aim for free;
3. the grip offsets live on the carrier and stay writable — `setAttr` into a
   constrained channel raises, so aiming the carrier would break the Rotate and
   Translate fields.

Honest side effect: once the aim exists, the carrier's **Rotate has no visible
effect**. The constraint fixes the geometry's world orientation, so turning the
carrier is compensated away. Translate still works. The status line says so
instead of leaving the animator to discover a dead field.

## The manifest, and how Bake+Delete finds it

An aim gets a manifest of its own, built the way limb and chain manifests are
built — a **UUID diff of every node in the scene** across the build, minus
`animCurve` types (`builder._scene_nodes` / `_fresh_paths` / `_recordable`).
Nothing smaller works: OverRig's aim leaves a constraint node parented under
the source, and a manifest assembled from `OverRig_knots` would record only the
locators and leave that constraint live, driven by nothing (trap 3, trap 4).

The set is `RigPicker_aim_<weapon key>`, but **it is never found by that name** —
Maya uniquifies, and two characters holding the same sword would collide.
Discovery is by prefix `RigPicker_aim` over `objectSet`s, and identity comes
from two string attributes on the set:

- `rigPickerSource` — one UUID: the node whose animation gets baked;
- `rigPickerHandles` — space-separated UUIDs: the nodes whose selection means
  "this aim". The source and the carrier. **Neither is a member**, because
  members get deleted and the sword must not.

**Resolution is exact match, on purpose.** The selection is normalised (a
selected shape becomes its transform) and then compared against
`members ∪ handles`. No descendant walk: after Connect the IK hand controls are
DAG children of the sword geometry, and "descendant of the source" would
resolve a hand-control click into the aim. That is trap 9 and trap 34 from a
third side, and the safe direction of failure here is "nothing happens", not
"the wrong rig gets baked".

Baking one aim, in this order:

1. the shared MEL gate — toolset loaded (trap 20) **and** no multi-frame time
   slider highlight, because `apply_Fast_Bake` reads it (trap 36);
2. `overrig.fast_bake([source])` while the constraint still drives;
3. `overrig.delete_constraint_attributes([source])`;
4. delete the members that still exist;
5. delete the set — re-checking `objExists` first, because Maya deletes a set
   together with its last member (trap 18).

If the source is gone (someone deleted the sword by hand), steps 2–3 are
skipped and the orphaned locators are cleaned up anyway.

Note the split on gates, which looks inconsistent and is not: the aim **build**
is not gated on the slider highlight, because its bake
(`BOVER_10_2_de88efca...`) reads `playbackOptions -ast/-aet` and never
`timeControl -q -ra` — read, not assumed. The aim **bake** is gated, because
`apply_Fast_Bake` is one of the nineteen that do read it.

## Modules

| module | responsibility | may import |
|---|---|---|
| `maya_overrig/overrig.py` | +`aim_procs_present`, `make_aim_locators`, `build_aim`, `add_to_set`, and `mel_gate` moved here from `fkcontrols` | `maya.cmds`, `maya.mel` |
| `maya_overrig/aimrig.py` | the aim manifest: record, discover, resolve a selection, bake and delete. Knows nothing about weapons | `maya.cmds`, `overrig`, `builder` |
| `maya_scenesetup/aim.py` | placement policy and the press: measure, place, build, record, refuse | `maya.cmds`, OpenMaya, `attach`, `overrig`, `aimrig` |
| `maya_scenesetup/window.py` | the **Add Aim** button; Add refuses while an aim exists | as today |
| `maya_overrig/picker_window.py` | Bake+Delete asks `aimrig` as well as `fkcontrols` | as today |

`aimrig` deliberately sits in `maya_overrig` and knows nothing about weapons,
even though the only caller today is the weapon tool: the picker's Bake+Delete
has to resolve it, and `maya_overrig` importing `maya_scenesetup` would invert
the layering that already runs the other way.

The fiddly parts are pure functions over data, as the house rule requires:

```python
aim.placement(lo, hi, margin)   -> (top_offset, side_offset)   # two triples
aimrig.sets_hit(selected, table) -> [set names]                # table as data
```

`mel_gate` moves from `fkcontrols._mel_gate` into `overrig` so both bake paths
share one wording; `fkcontrols._mel_gate` stays as a delegating alias so no
call site changes.

## What the animator sees

**Add Aim**, in the weapon block under Disconnect Arms. One press:

- no character bound → the existing "no character" message;
- no weapon in the hand → the existing `NO_WEAPON`;
- an aim already on this weapon → `"aim is already on this weapon - Bake+Delete
  in the picker removes it"`;
- OverRig missing, or an internal proc renamed → a message naming what is
  missing;
- the model has no mesh → `"no geometry to measure - cannot place the aim"`;
- otherwise: `"Aim on Long Sword 02 - drag LongSwordMesh_top to point the
  blade"`, and the status mentions that Rotate is now inert.

**Add** gains one refusal: while an aim exists it says
`"the weapon has an aim - Bake+Delete in the picker first"`. Add deletes the
carrier whole, so without this it would take the aim down and leave two
locators driving a deleted node — the same reasoning that already makes Add
refuse while the hands are connected.

**Bake+Delete** in the picker: aims resolved from the selection are baked
first, then the FK/IK work as today, and the messages are joined. The button no
longer requires a bound skeleton *when only an aim is selected* — an aim's bake
does not need a `scene_map`.

## Testing

Unit tests, `mayapy -m unittest`, no Maya session — a fake `cmds` injected into
`sys.modules` with the module attribute rebound (never by deleting
`sys.modules[...]`, which hands back the stale object):

- `placement`: the measured LongSword numbers give Y=133.313 / X=133.313; a
  model authored along −Y gives a negative top; a symmetric axis ties to
  positive; a zero-extent model is refused;
- `sets_hit`: a member hits, a handle hits, a shape normalises to its
  transform, a **descendant of the source does not** (the IK-hand case), an
  unrelated node hits nothing, two aims stay apart;
- the bake order, with a recording fake: bake before delete, set deleted last,
  a missing source skips the bake but still cleans up;
- the window's refusals: aim-exists blocks Add, missing mesh, missing procs.

**Live verification** — `docs/superpowers/plans/verify_weapon_aim.py`, the real
proof. Gates:

1. the sword does not move when the aim is built — world matrices compared
   element-wise across **every** frame of the range, not just the current one,
   and including the first and last (that is what would catch an edge-clipping
   bake, the way trap 12 was caught);
2. the two locators land where `placement` said, in world;
3. dragging `_top` turns the blade toward it, and the blade — not local +X —
   is what ends up pointing at the locator;
4. dragging `_side` rolls the blade about it;
5. the manifest holds the locators and the constraint, and holds neither the
   sword nor the carrier;
6. Bake+Delete with the sword selected: the sword keeps its animation to
   floating-point equality across the range, the locators and the constraint are
   gone, the set is gone, and **the character's FK/IK rig is untouched** —
   counted before and after;
7. the same with a locator selected instead of the sword;
8. Bake+Delete with an arm control selected does **not** touch the aim;
9. a second Aim press changes nothing and returns the refusal;
10. round trip: Aim → Bake+Delete → Aim leaves the sword's animation intact.

Written with this repo's bridge hygiene: never `cmds.undo()` inside a bridge
script, never write literal rest values into keyed or constrained channels
(read first, write back), autoKey disabled around any poke, and time wiggled
before measuring.

## Out of scope

- Buttons for the sword or the locators in the picker's body map (the user
  chose viewport selection).
- A distance field, a per-weapon distance in the catalog, an Aim/Remove toggle,
  a Remove button in SceneSetup.
- The `assign_Sw_System` pivot variants.
- Aiming anything that is not a catalogued weapon. `aimrig` is generic enough
  to serve one later; `maya_scenesetup/aim.py` is not asked to.

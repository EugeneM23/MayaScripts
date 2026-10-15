# Tools: Bake to an additive layer (2026-10-13)

The animator: «Теперь давай реализуем функционал запекания на адитивный слой». OverRig's `>layer`
(its bake tab, `apply_Bake_to_layer` → `BOVER_c830bbb3…`) bakes the selection with `bakeResults
-destinationLayer` onto a new OVERRIDE layer `BakedAnim` over the animation range and deletes the
objects' constraints and pairBlends; its right click bakes the highlight only. Asked:

- **what**: «Любой объект» - any selected object, whatever drives it (our knot or anyone's
  constraint), not only our knots;
- **which layer**: a new one per press;
- **where**: a third button in the bottom row, **Bake | Layer | Remove**.

Ours differs from OverRig on purpose: an ADDITIVE layer holding the difference the drivers made, so
the object's own keys stay in the base under it - muting the layer gives the original back, its
weight blends, deleting it drops the change.

## The press (`maya_tools/layerbake.py`, `bake(selection, highlight)`)

1. **What the selection names**: a knot (its object), an object riding our knots, or an object
   carrying constraints. Per object its drivers, classified before anything changes:
   - our knot's constraint (`skeldarKnotOf`) - the knot, and every knot riding it, comes off as
     Remove does (constraint deleted, our static keys cut, the knot deleted);
   - a constraint the plugin's own features made - the constraint, or one of its targets, carries
     an attribute with our prefixes (`deletion.OUR_ATTR_PREFIXES`: a weapon link, a hand proxy, the
     scene camera) - REFUSED by name: "undo it in its own card";
   - a constraint the Retarget holds (its `nodeState` on a `disableConstraints`) - refused: press
     Retarget first;
   - the rig's own (AdvancedSkeleton's constraints on its game bones and inside it: the constraint
     in the rig's namespace; for a root-namespace rig, the object and every target under its group or
     skeleton) - refused: baking it would break the rig;
   - anything else (the animator's constraint, an OverRig setup) - baked and deleted.
   An object with no driver is refused ("nothing drives X - its animation is its own"), as is a
   selection with nothing to bake.
2. **The span**: the highlight `[a, b)` → frames `a..b-1`, the layer keys zero one frame outside
   (the knots' 0/1/1/0); else per object the take (playback ∪ animation range ∪ its keys and its
   knots' keys).
3. **What it shows**: one time walk (`timewalk.Walk`, unrecorded) reads every object's translate and
   rotate values on every frame - what the constraints and pairBlends write into the channels, so a
   knot's attach below 1 is already blended in.
4. **The drivers off**, inside the press's undo chunk: knots removed (riders first), foreign
   constraints deleted - Maya deletes their pairBlend and gives the curves back.
5. **Its own**: a second walk reads the same channels - the base.
6. **The difference**: per channel `shown - own`; a rotate's shown euler first taken nearest its own
   (`knotplan.closest_euler`, in the object's rotate order), so the layer holds a small turn and not
   a 360. A channel whose difference stays under 1e-4 on every frame is left off the layer; a locked
   channel is skipped.
7. **The layer**: a new additive layer `Baked_<leaf>` (marked `skeldarBakeLayer`, rotation
   accumulation by component), the changed channels added, their layer curves keyed with the
   difference on every frame (the writer Overlap uses, moved into `layerbake.write_deltas`). One undo
   chunk; the line names the objects, the drivers taken off, the span and the layer.

## Not built

Scale (a scale constraint's channels are skipped and named); channels driven by an expression, a
motion path or a driven key (left as they are, named); IK-driven joints (the solver writes no
connection - nothing comes off); several presses into one layer.

## Proof

Unit tests (the classification and the lines, pure, in `knotplan`; the card and the hotkey row);
`docs/superpowers/plans/verify_bake_layer.py` in mayapy standalone: a knot edited and baked onto a
layer - the object shows exactly what the knot showed, its own curves untouched, muting the layer
gives the original; a ranged knot - only inside; an animator's parentConstraint to a moving target
- baked and deleted; a double knot riding a knot; refusals (nothing selected, nothing driving, a
weapon link, a rig's own bone, the Retarget holder) changing nothing; one undo.

## Addendum (the build)

- **"Another card's" is narrower than "a target carries our prefix"**: a cup the animator
  constrained to the sword would have been refused. The rule built: the constraint itself carries
  one of our prefixes (Connections' link, the Retarget's stretch follow - its `<target>W0` weight
  attributes aside), the object is a weapon or armor space, or the object is a JOINT following a
  `mayaWeapon` / `mayaSceneSetupCamera` target (a bone driven by a weapon or the scene camera).
- **An unkeyed channel a constraint drove has no own value left**: Maya routes it through the
  pairBlend with input 1 reading 0 (measured), or drives it directly. After the drivers come off it
  is set to the pose the first walk read at the current frame, and the line names it («prop.ty ...
  had no keys of their own - held at frame 12 under the layer»). Our knots key every free channel at
  creation and give the value back on Remove, so a knot's object never meets this.
- Proof: `verify_bake_layer.py` 48/48 standalone; `verify_aim_overlap.py` 57/57 through the moved
  writer; 6243 unit tests.

## Addendum 2 (after using it): everything goes onto the layer

The animator, the same evening: «Я выделил объект на котором просто ключи нажал леер и он не
запекся а должен был». The first build put only what the DRIVERS changed on the layer, so a plainly
keyed object had nothing to put there and was refused. Asked, they chose **everything onto the
layer, the base a still pose** - for plain keys, knots and constraints alike.

- **Measured first, Maya's own** `bakeResults -destinationLayer` into an additive layer: it bakes
  the ABSOLUTE values, so the motion comes out doubled (tx 20 where the keys say 10), and with
  `-removeBakedAnimFromLayer` the base is left on a stale value (0.28 everywhere). Not a model.
- **The whole take**: after the drivers come off, each base curve that moves is deleted (and each
  channel a driver held) and set to a value; the second walk reads what is left (the base plus
  any other animation layers, untouched); the difference is taken, and each channel's first-frame
  difference is moved onto its base (`knotplan.anchored`): the base holds the pose of the span's
  first frame, the layer starts at 0. Mute it and the object stands in that pose.
- **A highlight**: the base keeps its keys outside it; inside, a key one frame outside each end is
  inserted (shape kept) and the keys between are cut (`knotplan.bridged`), so the base bridges the
  highlight on those two keys' tangents; the layer holds what the object showed minus that bridge,
  zero one frame outside. An unkeyed channel only a FOREIGN constraint drove is held at the current
  frame's pose (trap 238); a knot's channels have their own value back from Remove's rule.
- **A base under the animator's own layers**: the base is reached through each layer's blend node
  (input A); only the base's motion moves, their layers stay as they were.
- **Refused**: an object with no keys of its own, no knot and no constraint («nothing animates
  X»); one whose motion is all on layers already (a second press: «its animation is on layers
  already»); base keys that come from a reference.
- Proof: `verify_bake_layer.py` **58/58 standalone** - a plain keyed prop (the report) baked with
  the base on frame 0's pose and the prop as it was to 0.000000 cm, muted standing still, a second
  press refused, a highlight bridged; the knot, constraint, double-knot, rig and refusal cases on
  the new rule; under the animator's own layer only the base moved.

## Addendum 3: by keys, not baked

The animator: «Давай сделаем так что бы анимация не просто перепекалась на слой а чтобы она
переносилась по ключам и мы их не теряли».

- **Over the whole take, a channel only its own keys move**: the base curve NODE itself moves onto
  the layer - disconnected from the base, connected to the layer's blend input B, its values shifted
  by its first-frame value, which the base then holds (`_move`). Measured first in mayapy: the layer
  finds it as its curve (`findCurveForPlug`, `animCurves`), the motion is identical, a stepped
  tangent and cycle infinity survive, muted the object stands. Every key, tangent, weight,
  breakdown and infinity is kept, exact between frames too. A curve that also feeds another plug is
  read off the scene instead.
- **Under a highlight, a plain channel's keys inside it move as keys, exactly** (`_bridge`): the
  original's values and in / out slopes at its keys from one frame before the highlight to one
  after, less the bridged base's (a Hermite segment minus a Hermite segment is one), written as
  fixed tangents (`keyTangent -inAngle/-outAngle`: the tangent of the angle is the slope in UI units
  a frame - measured exact at film, ntsc and 60 fps). A curve whose keys are all stepped there: the
  bridge holds still (its first key stepped) and the keys move as they are. Weighted, or steps mixed
  with splines: every frame of the highlight. The edge keys and their outer neighbours are pinned
  first (trap 221), so nothing outside moves.
- **A channel a knot or a constraint drives stays keyed on every frame.** It has no keys of its own:
  a knot is keyed on every frame by construction, and keying a constraint only at its targets' keys
  was tried and refused - a two-turn spin between two target keys came back as no turn at all, and a
  ranged knot went inexact outside its range.
- `setKeyframe` takes no `fixed` and leaves the types of a key already there (the layer's identity
  key): the writer sets types through `keyTangent`.
- Proof: `verify_bake_layer.py` **66/66 standalone** - the plain prop's three curves on the layer as
  themselves (the same nodes, key times, tangent types, a step, a cycle), the prop as it was at every
  half frame; under a highlight a smooth curve with a broken tangent and fractional key and a stepped
  curve exact to 3.4e-9 at half frames, the stepped keys as they are, a weighted curve on every frame.

## Addendum 4 (2026-10-15): scale

The animator: «Наше запекание на слой сейчас не работает со скейлом». Layer read and moved translate
and rotate only: an object keyed only on scale was refused («nothing animates»), scale keys beside
others stayed on the base (muted, it still scaled), a scaleConstraint stayed.

- Layer's channels are `knotplan.LAYER_CHANNELS` (translate, rotate, scale); a knot and a re-parent
  still take translate and rotate.
- **The layer ADDS scale**: Maya's animLayer multiplies by default (`scaleAccumulationMode` 1, its
  identity key 1.0 - measured); `write_deltas` sets it to 0 before the first key, so a scale
  difference is shown minus own, a moved curve shifted by its first value, a ranged layer 0 outside,
  exactly as for translate.
- A scaleConstraint drives scale directly (no pairBlend) and is baked and deleted as any foreign
  constraint.
- Proof: `verify_bake_layer.py` **95/95** (L12: scale keys alone moved as themselves, the world
  matrix to 4.4e-16 at frames and half frames, the base frame 0's scale, muted it stands; a
  highlight exact to 3.7e-9; a scaleConstraint 0.0; scale beside a knot; one undo).

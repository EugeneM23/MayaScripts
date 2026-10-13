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

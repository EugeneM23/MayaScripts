# Layer: a knot bakes as itself, and always from the base (2026-10-15)

The animator, on the Tools card's Layer: «1 - При запекании анимации knot на слой сам knot не должен
удаляться анимация должна запечься на для него точно так же как и для любого другого объекта.
2 - Когда запекаем анимацию на слой то давай будем анимацию с базового слоя удалять». Asked: a
selected knot is an object like any other (its keys onto `Baked_<knot>`, the knot stays and goes on
driving), a selected object riding a knot keeps today's rule (the knot comes off, its motion onto
the object's layer); and the press always takes the base, whatever is selected in the Anim Layer
Editor.

## What was happening (measured in mayapy)

A keyed cube with a knot, Layer pressed with the knot or the cube selected:

- no layer selected in the Anim Layer Editor: the knot deleted, the cube's motion on `Baked_box`,
  the base with no curve - as designed;
- **any layer selected** (even an empty one): the press took the animation FROM that layer
  (2026-10-15 morning, `_chosen_source`), so the knot was deleted, the base kept both curves, and
  «nothing changed over 0-20, so no layer was made». Both complaints at once.

## The rules

1. **What the selection names** (`layerbake._object_of`): a node of a knot - its top, a double
   knot's inner, an aim's target or up, a snapshot - names ITSELF. A constraint names the object it
   constrains; a waiting pivot nothing (skipped and said); anything else itself. A selected knot is
   then planned as any object: its own base curves move onto its new layer, the knot keeps its
   constraint on its object and goes on driving it. A knot riding the selected knot (a knot on a
   knot) drives it, so it comes off as on any object.
2. **A knot's own machinery is not a driver**: a constraint on a LOCKED channel (Knot Orient's kept
   point constraint on its locked translate) is left alone - `_drivers` reads free channels only.
3. **Always from the base**: the selected layer no longer chooses the source, and the lone-layer
   fallback goes with it (`_chosen_source`, `_only_layer`, `_source_refusal`, `_whole_curves_ok`
   removed). An object whose animation lives only on layers is refused as before the morning:
   «its animation is on layers already». Every other layer, selected or not, stays as it is.
4. Unchanged: the base after the press - whole take, no curve, the pose of the span's first frame
   (mute the layer and the object stands); a highlight - the base bridged on its own keys outside.

## Proof

Unit tests where pure; `docs/superpowers/plans/verify_bake_layer.py` gains the knot-as-object case
(the knot stays, its curves on its layer as themselves, the object as it was at every frame and half
frame) and a layer selected in the editor taking nothing from it (the base cleared, the other layer's
curves untouched); `verify_tools_layers.py` rewritten where it relied on a selected source.

# Pose Library: any object beside the character, found again on load (2026-10-15)

The animator: «Сейчас она сохраняет позу и анимации нашего рига но объекты которые не относятся к
ригу мы не сохраняем или это не работает. нужно реализовать потдержку любых объектов и поиск их при
загрузке. Например мы сохранили наш риг и камеру в сцене при загрузке мы должны выполнить поиск
камеры с учетом того что в другой сцене на ней уже может быть немспейс (такой тип поиска думаю
будет логично реализовать только для тех объектов которые находятся в выделении)».

Asked, all three the recommendation:
- an object saved but NOT selected on load is still posed when found by its exact path; the
  namespace-blind search is only for the selection;
- an object keeps its transform's keyable attributes AND its shape's (a camera's focal length);
- poses and animation cards alike.

## What was wrong

- A card was either a character card or an objects card. A camera selected beside a rig was
  "left out" of the rig's card.
- A camera of the rig (Camera Setup's `Manny_Rig:SceneSetup_camera`, in the rig's namespace and
  its character group) counted as a PART of the rig: it named the whole body and was never saved.
- Only an objects card searched by name; a character card never looked for objects at all.

## The rule: body and objects

`objects.split(selection)` divides what is selected:
- **the body**: a joint, anything under a rig's AdvancedSkeleton `Group` (its controls, its
  meshes, its weapon spaces), a skinned mesh, a group holding the skeleton or the rig (the
  character group, the Creep's `Armature`), a weapon or an armour piece (they have cards of their
  own: Inventory);
- **an object**: everything else - a camera (the rig's own included), a knot, a locator, a prop,
  a curve, a light, in a character's group or not.

A character card holds the body's bones as before plus `objects`: one record per selected object
(`name` without namespace, `path`, `attrs`, `shape` {attr: value / curve} of its first
non-intermediate shape, `own` True when it stood in the card's character - its namespace or
group). Only objects selected: an objects card, as before (now with `shape`).

## Load

A character card onto its targets:
1. the selected objects take the card's objects as an objects card always did (`pair_objects`:
   exact path, then by name with the namespace ignored, then by order);
2. the card's objects left over (not with Selected only) are FOUND: an `own` object in each
   target character - its namespace + name (a rig), else by name under its character group (a
   skeleton) - so a pose saved on `Manny_Rig` poses `Manny_Rig1`'s own camera; any other by its
   exact path;
3. nothing found is said («not in the scene: cam1»), never searched for by name.

Only objects selected (no character) with a character card: the objects alone are posed, and the
line says the character was not selected. An objects card: unchanged, plus the shape's attributes.

Animation cards: the same pairing; the objects' curves pasted with the same paste plan inside the
character press's one undo chunk. Mirror leaves objects unmirrored (said). Blend mixes them as the
character. Select objects selects them too.

## Proof

`docs/superpowers/plans/verify_poselib_objects.py` (mayapy standalone): a Manny_Rig with its
SceneSetup camera, a free camera and a prop; a pose and an animation saved; applied onto a second
rig in a scene where the free camera stands in a namespace - by selection, by exact path, the
rig's own camera in the target's namespace, the focal length, one undo.

# Connections: IK into a world control (2026-10-28)

The animator: «Давай во вкладке connection там где мы перепекаем руки в IK сделаем
возможность поставить галочку WORLD. при простановке этой галочки мы должны не просто
переключиться в ик а переподвязаться еще на новый контрол который будет привязан как knot
world инструмент во вкладке tools».

Asked, all three the recommendation:
- the control is Tools' **Double knot World** (the card's «World ×2»): an outer `_dknotMove`
  that carries the place and has no rotation, an inner `_dknotRotate` that carries the turn;
- its keys are **only the frames the IK switch keys** (the keys-only rule of 2026-10-08), not
  every frame as the Tools tool bakes;
- **arms and legs**, one box for both.

## What it is for

An AdvancedSkeleton IK hand or foot lives in Main's space (`followMain 10`). Root motion on
Main carries it along. Under a world control it stays where it is in the scene while Main and
the body move: a hand planted on a wall, a foot on the ground. The world control is a Tools
knot. Tools' Bake and Remove, the attach blend and Delete character all work on it unchanged.

## The card

Each arm and leg row reads `Arm R [FK | IK | W]`: a third box **W** right after IK
(`fkik_box(side, "W", kind)`, `skeldarConnectionsFKIK_R_W`, `..FKIKLeg_L_W`). It is lit while
the limb is in world and a press toggles it (`connections.toggle_world`), whatever the box shows
- the scene decides, as for FK and IK. The spine has none.

(The first build, the same day, had one chip «World» under the rows for every IK press. The
animator, after using it: «сейчас кнопки переключателей очень длинные легко можно добавить тогл
переключатели w взле кнопки IK».)

## The presses

A limb is **in world** when a `double_world` knot drives its IK control (`ikworld.knot_of`).
A World ×2 knot the animator made in Tools on the IK control counts too.

| press | limb now | what happens |
|---|---|---|
| W | FK or mixed | switched to IK (keys only), then the IK control onto a new world control keyed on the same frames |
| W | IK | the IK control onto a world control keyed on its own keys - no switch |
| W | IK in world | **back from world**: the IK control keyed with what it shows on the world control's keys, the world control removed |
| W | FK, a world control left on its IK | the world control removed (the IK it drives is not shown) |
| IK | IK in world | refused: «Arm_R is already IK, in world - W takes it back into Main's space» |
| IK | FK, a world control left on its IK | refused: «... press FK to take it off first» |
| FK | IK in world | switched to FK on the keys of the IK controls and the world control, then the world control removed |
| FK | FK, a world control left | the world control removed |

Every press is one undo chunk. The refusals come before anything moves: the switch's own and
the knot's (`knots.knot_refusal`: a locked or driven channel, an uneven parent).

## The world control, keyed on frames

`knots.create_keyed(kind, obj, frames, tangents, highlight, order)` is `create` for one object
with the bake replaced by samples:
- the knot's nodes are made and constrained to the object as for every knot;
- what they hold is read on `frames` after a real time change;
- the temporary constraints are deleted, then each channel is keyed on those frames with the
  tangent types the switch used (`fkik.key_plan`'s `tangents`);
- a whole-take channel still on every frame becomes a plain value; rotations are
  euler-filtered;
- the time goes to the first frame before the object's follow constraint is made, because its
  offset is captured there, where the knot stands exactly on the object.

The span is a knot's own: a highlight `[a, b)` gives `[a-1, b]` with `attach` keyed
0 / 1 / 1 / 0, else the whole take.

Between keys the world control interpolates in the world, the IK control did in Main's space:
the hand's path between keys changes. That is the cost the animator chose; at the keys the
limb stands exactly where it did.

The rotate order is the IK control's own. The new Move control is selected, as Tools selects a
new knot.

## The controls

The same day: «давай вместо локатора мы будем создавать контроллер». The knot's two locators are
made controls after `create_keyed` (`ikworld.make_controls`, `curvectrl.reshape` - 1P Setup's
chest is made the same way), each one degree-1 curve, 2 px:
- the **Move** `<ik>_worldMove_ctrl`: a cube in world axes (it has no rotation), half side
  `BOX_GROW` 1.6 times the IK control's drawing's largest half extent, in the knot's gold;
- the **Rotate** `<ik>_worldRotate_ctrl`: three rings (XY, XZ, YZ) in its own axes, radius
  `RING_GROW` 1.3 times that, in the knot's light gold - one line, no chord between the rings
  (`rings`: the XZ ring broken at +Z for the whole YZ ring).
They are still a knot to Tools: knots are found by their marker in the Knots group, the inner
by its marker, never by shape or name.

## Back from world

`ikworld.leave(limb, top)`:
1. the frames are the keys of the world control's curves (both controls and `attach`) inside
   its span; for a ranged knot these are its keys in `a..b-1` and the two ends;
2. on each frame the IK control's local channels are read from its world matrix and its
   parent's, the eulers nearest the frame before;
3. the knot is removed through `knots.remove`, which gives the IK control its own curves back;
4. the frames are written with `fkik._write`, over the whole take or over `a..b-1`. Layered
   channels are keyed on the active layer, as the switch keys them.

## What stays the same

- An arm's pole follows Main (`followArm 0`), so with the hand in world the elbow's plane still
  rides the body. A leg's pole follows the IK leg (`followLeg 10`), so it rides the foot's
  world control.
- The toes control rides the IK leg.
- Weapon tab: a hand in world cannot follow a weapon: «Arm_R is IK in world - press its W
  first».

Not built: the Pose Library onto a limb in world (`rigsolve.knot_driver` takes a plain knot
only, so the IK control reads «not posed»); a world pole.

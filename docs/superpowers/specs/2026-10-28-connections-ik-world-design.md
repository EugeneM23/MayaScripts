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

Body tab, under the FK / IK rows: one chip **World** (`skeldarConnectionsFKIKWorld`),
remembered in the optionVar `skeldarConnectionsIKWorld` (off by default). It changes what an
IK press of an arm or a leg does. The spine and FK presses ignore it.

## The presses

A limb is **in world** when a `double_world` knot drives its IK control (`ikworld.knot_of`).
A World ×2 knot the animator made in Tools on the IK control counts too.

| press | limb now | what happens |
|---|---|---|
| IK, World on | FK or mixed | switched to IK (keys only), then the IK control onto a new world control keyed on the same frames |
| IK, World on | IK | the IK control onto a world control keyed on its own keys - no switch |
| IK, World on | IK in world | refused: «Arm_R is already IK in world (IKArm_R_dknotMove)» |
| IK, World off | IK in world | **back from world**: the IK control keyed with what it shows on the world control's keys, the world control removed |
| IK, World off / on | FK or mixed, a world control left on its IK | the world control removed first (the IK it drives is not shown), then as above |
| FK | IK in world | switched to FK on the keys of the IK controls and the world control, then the world control removed |

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

## Back from world

`ikworld.leave(limb, top)`:
1. the frames are the keys of the world control's curves (both locators and `attach`) inside
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
- Weapon tab: a hand in world cannot follow a weapon: «Arm_R is IK in world - press IK without
  World first».
- The card's subtitle names the limbs in world: «Arm_R, Leg_L IK in world».

Not built: the Pose Library onto a limb in world (`rigsolve.knot_driver` takes a plain knot
only, so the IK control reads «not posed»); a world pole.

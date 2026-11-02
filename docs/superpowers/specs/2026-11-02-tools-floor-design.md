# Tools > Floor: the feet on the floor, frame by frame (2026-11-02)

The animator: «нам нужен инструмент который вывровняет стопы по полу.....раньше он у нас вроде был но потом
мы его удалили». What they remember is Walk Builder's clean step `floor` / `floor_offset`, built 2026-10-14
and taken out with the rest of the levers the same day (`fb2a343c:SkeldarAnim/maya_walk/clean.py`): it moved
the body so the feet's LOWEST point over the whole cycle stood where it stands at rest over the root - one
vertical offset for the clip, a 5 cm dead zone, plus a hand offset. It read a cycle, not a scene.

Asked, they chose: it **puts the character on the floor** (lifts or lowers the body so the planted feet stand
on it, not levelling a foot's own pitch); it lives as a **row in Tools**, acting on the selected character in
the scene; the floor is **always world Y = 0**; and it works **frame by frame, contact by contact** - so a
take whose feet sink in the middle is mended there, not only shifted as a whole.

## What a foot touching the floor means

A foot's floor contact is its ankle (heel) or its ball, whichever is lower, and "on the floor" is where that
point stands AT THE BIND - the bind pose stands on y = 0, so the ball's own bind height (0.75 cm on Manny) is
the sole's thickness and the ankle's (8.24) is the heel's. So

    clearance(point, f) = y(point, f) - y(point, bind)
    low(side, f)        = min(clearance(ankle), clearance(ball))

is how far above the floor that foot is, 0 being exactly on it. The bind comes from
`maya_retargetmode.rest_world` - the skinCluster's `bindPreMatrix`, the one reader in the plugin that is not
fooled by a stale `dagPose` (trap 176).

## What is written: the lower foot, every frame

    want(f) = -min(low(side, f) for both sides)

so the lower foot stands exactly on the floor and nothing is left under it. Where the two feet disagree (a
double support on uneven ground), the lower one decides and the other is left above the floor: one vertical
offset cannot put two feet at two heights, and a foot ABOVE the floor is the safe direction.

**There is no contact detection, and that is the design.** Two rules were built and measured first, and both
are wrong:

- *the foot's own lowest over the span* (Walk Builder's `model.down`, `clean.LOW_TOL`): one stance sunk 6 cm
  into the floor is the deepest that foot ever goes, so against it every clean stance elsewhere reads as 6 cm
  of air and stops being a contact - the body was then carried 6 cm down for the length of the take;
- *the foot's own lowest NEARBY* (a window of some ten frames): better, and still wrong inside one stance -
  the body dips while the foot is planted, the foot goes down with it, and the clean half of that same stance
  reads as air beside the sunk half.

A planted foot a few centimetres off its own low is still the thing the body stands on. The only frames with
nothing to stand on are the ones where **both** feet are a swing's height up - a flight, a jump - and those
are skipped (`airborne`: every side more than `AIR_TOL` 8 cm above its own low within `DOWN_WINDOW` 8 frames;
a swing clears the floor by 10-20 cm at a walk, and a stance sunk less than that is still a stance). The
curve then runs between its neighbours, so a jump keeps its arc.

`down_frames` stays as the LINE's own reading («feet down: L 20 fr, R 20 fr») and decides nothing.

## How it is written

`want` is keyed as DELTAS on a new additive layer **`Floor`** (marked `skeldarFloor`,
`layerbake.write_deltas`), so the animation itself is never touched - the layer can be muted, weighted or
deleted - and a second press rewrites the same layer in place, keeping its name, its place in the stack, its
weight and its mute. The carrier is the rig's `Main` (root motion), else the skeleton's top joint as
`skeleton.current_root` answers it - never a Cascadeur wrapper above it, which would stop being Cascadeur's
layout the moment it moved.

**The centimetre of world rise is written in the channels that really carry it.** The Creep's root hangs
under a `-90 X Armature`, where world up is the root's own +Z: the local displacement is read per frame
(`v . parent3 = (0, 1, 0)`, row vectors) and spread over translateX/Y/Z, a channel that never moves further
than `AXIS_DEAD` left out - so a rig's Main takes one curve and the Creep's root takes its own Z.

**A standing layer's own curve is read back and added to.** The press reads the feet as they SHOW, so that
reading already carries whatever the standing Floor layer contributes; the curve it must end up holding is
`old + want / weight`. Writing `want` alone would take the old correction away again (measured: a second
press left the feet 5 cm off), and at a weight other than 1 only its share would land. A weight of 0 is
refused by name. A MUTED standing layer is the other way round - it shows nothing, so the reading does not
carry it and the curve takes the whole correction; the line says it is muted, and the check below holds its
tongue (a muted layer moves nothing, and blaming the carrier for that would be a lie).

The keys are the frames `want` holds, thinned so that **no frame is further than `KEY_TOL` (0.02 cm) from
the curve its keys draw** - each stretch split at its own worst frame until the bound holds, never a greedy
walk (which compares only with the key behind it and lets the error past the tolerance). A still contact
costs two keys and a sinking one follows the foot; between them Maya's own interpolation runs.

The span is the time slider's highlight, else the whole take (playback range union the animation range) -
every Tools row's rule; a highlight writes 0 one frame outside each end (`ranged`).

## What it says, and the check it says it from

After writing, the press walks the frames once more and reads the feet again: the line names the residual
when it is past `CHECK_TOL` (0.1 cm) - «the feet did not follow Main: still 7.4 cm off - a leg held in world
(Connections > W, 1P, a knot) does not move with the body». A foot whose world place is held by something
outside the carrier cannot be moved by the body, and this is what tells the animator so rather than leaving
them to wonder. The press is never undone for it: the whole thing is one undo chunk, and Ctrl+Z is theirs.

## Refused, by name, before anything changes

- no character in the selection (the plugin's one rule: the selection, else the only rig, else the only
  skeleton);
- the character has no `foot_l` / `foot_r` (a hand or a prop is not a walker);
- the carrier's translate locked, or driven by anything but time curves and animation layers (a constraint
  wins over the layer we would write), or an unevenly scaled / sheared parent (`knotplan.uneven_parent`);
- a standing Floor layer at weight 0;
- nothing to do: the feet are already on the floor within `FLOOR_DEAD` (0.2 cm) - «nothing changed».

Esc in the reading walk changes nothing.

## What it does not do

- It does not level a foot's own pitch (the toe or heel dipping through the floor): that is Walk Builder's
  `Foot flat` and the IK feet's own business, and the animator chose the body offset.
- It does not read the mesh: the sole is the ankle's and the ball's bind height, which is what every other
  tool here uses. A character whose shoes are not in its bind will stand on its bind's floor, not its shoes'.
- It moves the body vertically only. A foot sliding horizontally is not its job.
- The floor is world Y = 0; a podium or a step is not read (asked, and declined).
- A take whose body dips more than `AIR_TOL` inside one stance has that stance's clean half read as air.

## Proof

`tests/test_tools_floorplan.py` (pure: the clearance rule, the lower foot, the double support, a flight, the
sunk stance, the thinning's bound, the local channels, the refusals, and that it imports no Maya) and
`docs/superpowers/plans/verify_floor.py` in mayapy standalone on the shipped assets, a take keyed by hand (the
legs alternating, so each foot really has a stance and a swing) and read back by a measurement of its own -
**0 of 35 gates failed, 2026-11-02**:

- a Manny skeleton floated 15 cm and sunk 10: every frame's lower foot on the floor to **0.000000 cm**, no
  frame under it, the feet not sliding sideways (0.00e+00), the body moved 15.00 / 10.07 cm, one curve on the
  root, and one Ctrl+Z putting the take back exactly;
- one contact 6 cm into the floor while the others stand on it: the sunk contact on the floor (0.000000) and
  the other foot's stance not carried with it (0.070 cm, the fixture's own foot dip);
- the Creep skeleton: world up is the root's own Z under its `Armature` (axis 0.000, 0.000, 1.000), the key
  goes in `translateZ`, and the feet still land;
- Manny [rig]: the carrier is `Main` and the layer holds `Main.translateY` alone;
- a second press on a take already standing: «already on the floor ... nothing changed», no second layer; and
  with 5 cm more float and the layer at weight 0.5, the same layer rewritten in place, its weight kept, the
  feet landing all the same (0.000000) and the line naming the weight; muted and floated 3 cm more, the line
  says so and the feet stand on the floor (0.000000) the moment it is unmuted;
- the refusals: a locked channel, and a skeleton with no feet.

The card itself is drawn offscreen by `docs/superpowers/plans/render_tools_card.py` from the builder's own
calls (`tools_card.png`): a fifth subsection **Floor** «feet on the floor», closed by default, with one row
«Floor - the body onto world Y = 0».

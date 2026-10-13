# Tools: OverRig's aim tab, native - Aim and Overlap (2026-10-13)

The animator: «Теперь давай реализуем функционал AIM» (after Knots, Double knot and Parent the
day before). OverRig's `aim` tab holds two tools - `aim` (`make_aim_from_selected`) and
`overlapper` (`bar_tail_overlap_window` → `execute_overlap_command`) - and a `desel` button that
exists only to fire OverRig's deselect-triggered build. Asked, all three the recommendation:

- **both tools**, two subsections of the Tools card, **Aim** and **Overlap**;
- Aim in **two steps, Aim → Finish** (Knot Offset's shape), the locators placed for the animator;
- Overlap's result on an **additive animation layer**, one per press.

Native as the other tabs: no OverRig MEL runs; ours are known by our attributes.

## What OverRig builds (read from the MEL)

**aim** (`make_aim_from_selected(1)`, then on the next deselect `BOVER_10df34add…`):

1. per selected object two locators `<leaf>_top` and `<leaf>_side`, both snapped onto the object
   (its pivot and orientation), the side coloured; the animator drags them into place;
2. on deselect: each locator `parentConstraint -mo` to the object (they ride it where they were
   put), baked over the animation range (`-ast/-aet`), the constraints deleted; then
   `aimConstraint -mo -aimVector 1 0 0 -upVector 0 1 0 -worldUpType object -worldUpObject <side>`
   from `<top>` onto the object; the locators' rotate keys cut, zeroed and hidden.

So the object's ROTATION aims at the top locator with the side locator as its up point; its
translation keeps its own animation. The locators join `OverRig_knots`: OverRig's knot bake and
delete handle them.

**overlapper** (`execute_overlap_command(hierarchy, selection, softness, lag, 0, easing, cycled,
abs, save poses)`):

- the chains: with `hierarchy` every selected object is a root and its chain is its descendants of
  the same shape type (`select -hi` filtered); without it the selection, top to bottom, is the
  chain; a chain of one is skipped;
- a highlight narrows the work to it (`partial_mode`);
- per chain (`BOVER_ddf3e35…`): a joint chain built on the objects (oriented X down the chain,
  the last joint continuing its parent's line), baked to follow them, the objects constrained to
  it; then for each joint top to bottom: a locator on the joint moved along its X by
  `softness × the distance to the next joint` (the last: to the one before), constrained to the
  joint and baked - so it carries the joint's track AFTER the joints above have their overlap -
  then `aimConstraint -mo -aimVector 1 0 0 -upVector 0 0 1 -worldUpType objectrotation
  -worldUpVector 0 0 1 -worldUpObject <the locator>` from the locator onto the joint, and the
  locator's keys shifted LATER by `lag` frames (`keyframe -tc`), its rotation slerped; the first
  locator smoothed by `filterCurve -f resample -kernel gaussian2` over `softness × easing × 2`
  frames when easing is set; with `cycled` each locator's first frame copied to its end and its
  curves cycled; with `abs` the lag is divided by the chain's length (a total);
- the objects baked onto an override layer `BakedAnim` (a highlight keys the layer's weight
  0/1/1/0 one frame outside it), the rig deleted; `save poses` adds an additive child layer that
  holds the first and last poses and lets go over a fifth of the range at each end.

At the moment each aim is made its locator lies exactly on the joint's X with the joint's own Z,
so `-mo` captures the identity: the result does not depend on the frame the press was made on.

## Aim

**Card**: heading **Aim**, one row, one button **Aim** (reads **Finish** while an aim waits).

**First press** (`knots.begin_aim`), every selected object (several at once):
- the refusals of a knot (`_plan_object`, rotate channels only, as Knot Orient), plus an aim
  already waiting for that object;
- a space `<leaf>_aimSpace` riding the object (parentConstraint, no offset: at its rotate pivot,
  in its axes) in the object's Knots group, marked as a waiting space of kind `aim`
  (`skeldarKnotPendingKind`);
- in it `<leaf>_aimTarget` at `(r, 0, 0)` and `<leaf>_aimUp` at `(0, r, 0)`,
  `r = knotplan.aim_reach(size)` = four times the knot size; rotation locked (they are points);
  the target carries the waiting marker (the object's UUID), the span and the rotate-order choice;
- the targets selected, the Move tool on; the line says to move them and press Finish.

**Second press** (`knots.finish_aim`): the aims the selection names (a target, an up, a space, or
the object), else every aim waiting. For each:
- refused when the target stands on the object, or the up on the line to the target (under 3°);
- a group `<leaf>_aim` at identity (locked) in the Knots group - the knot's top: kind `aim`, the
  source, span, keyed channels, `attach`; under it `<leaf>_aimTarget` and `<leaf>_aimUp`
  (marked inner), each baked from the waiting one's world position over the span (translate
  only), rotation locked; the waiting space deleted;
- the object's free rotate channels keyed at their values (the pairBlend keeps its curves), then
  `aimConstraint -mo` from the target, `worldUpType object` on the up, the aim and up vectors the
  target's and the up's directions in the object's own axes at that frame (so the offset is the
  identity), its locked rotates skipped; `attach` drives its weight and Maya's pairBlend (Maya
  names that blend `blendAimCnstraint1`, measured);
- the target selected.

Bake, Remove, Attach 0/1 work as on every knot (the group is the top; its two locators are inner
nodes). Remove on a waiting aim drops its space. The subtitle counts waiting aims.

## Overlap

**Card**: heading **Overlap**; `Softness [2.0]`, `Lag, fr [1.0]`, `Easing [0.0]` (named rows,
float fields); chips **Hierarchy** (on), **Cycled**, **Total lag**, **Keep edges** in one row; one
button **Overlap**. All remembered (`skeldarOverlap*` optionVars).

**The model** (`maya_tools/overlapplan.py`, numpy only, pure) - OverRig's construction computed
directly rather than built out of a joint chain, locators, constraints and bakes:

- each chain member is a rigid frame `F_i(t)` - its world rotation at its world rotate pivot;
  `l_i(t) = F_i(t) · F_{i-1}(t)^-1`, its place under the member above (the joint chain OverRig
  builds);
- the rest geometry at the current frame: `d_i` the direction to the next member in member i's
  own axes (the last member: from the one before, continuing the line), `L_i = softness ×` that
  distance, `u_i` the member's own axis most perpendicular to `d_i`, made perpendicular;
- top to bottom, over every frame: the member's track before its own aim `P_i(t) = l_i(t) ·
  C_{i-1}(t)` (`C_{-1}` the identity, so `P_0 = F_0`); its target `L_i d_i · P_i(t - lag)` and up
  `u_i · rot(P_i(t - lag))` (Catmull-Rom between frames for a fractional lag; outside the sampled
  window the end value; cycled: wrapped into the take); the first member's target and up smoothed
  by a Gaussian of `softness × easing` frames when easing is set; then `C_i(t)` = the frame at
  `P_i(t)`'s position whose `d_i` points at the target and whose `u_i` leans to the up. At lag 0 it
  gives the members' own motion back exactly;
- total lag: the lag divided by the chain's length.

**The scene** (`maya_tools/overlap.py`):

- chains: hierarchy on - every selected object a root, the chain its descendants of the same kind
  (the shape type, else the node type), the nearest one each step through anything of another
  kind, ending at a branch (said); objects inside another selected root's chain are dropped.
  Off - the selection is one chain. A chain of one is refused by name;
- refused by name before anything changes: no free rotate channel, a rotate channel driven by
  anything but a time curve or an animation layer (a constraint, a knot's pairBlend, an
  expression); softness at 0 or less; lag 0;
- the range: the highlight `[a, b)` → frames `a..b-1`, the layer's keys zero one frame outside
  each end (the knots' 0/1/1/0); else the whole take (playback ∪ animation range);
- a previous overlap of ours on the same members is taken off first (their plugs out of our
  layers, an emptied layer deleted) - pressing again replaces it;
- one time walk (`timewalk.Walk`, unrecorded) reads, on every frame of the window (the range
  widened by the chain's whole lag both ways; cycled: the range), each member's world matrix,
  world rotate pivot, parent matrix and rotate and translate values;
- the new world frames are turned into channels: the parent's new world (`Parent · F_k^-1 · F'_k`
  for a parent at or under an earlier member k), the local rotation, `rotate = RA^-1 · local ·
  JO^-1` (a joint) or `RA^-1 · local` (a transform), the euler nearest the base value at that
  frame; a translate change only where the member's place moves (a member not parented under the
  one above), else no translate key at all;
- keep edges: every delta times a ramp that is 0 at the range's ends and 1 from a fifth in;
- written onto a new additive layer `Overlap` (marked `skeldarOverlap`, rotation accumulation by
  component - measured default 0 "By Component"): each changed channel added to the layer, its
  layer curve keyed with `final - base` on every frame (measured: a delta keyed on the layer curve
  adds exactly); cycled: the layer curves cycle;
- one undo chunk; the line names the chains, the settings, the range and the layer.

## Not built

OverRig's `desel` (our Finish replaces it); per-chain layers; a branching hierarchy as several
chains; scale; the overlap of a constrained or knotted member.

## Proof

Unit tests (`test_tools_overlapplan.py` on the pure model, `test_tools_knotplan.py`,
`test_tools_panel.py`, `test_hotkeys.py`); `docs/superpowers/plans/verify_aim_overlap.py` in mayapy
standalone: Aim - nothing moves at creation, the target moved turns the object onto it, the up
rolls it, a range, attach 0, Bake, Remove exact, one undo; Overlap - a keyed joint chain and an
AdvancedSkeleton finger chain: the base untouched, the layer's deltas, lag 0 refused, the tip
trailing its own motion, keep edges exact at both ends, cycled curves cycling, a second press
replacing the first, one undo. The live card is the animator's to try.

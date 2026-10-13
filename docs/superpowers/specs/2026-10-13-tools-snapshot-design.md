# Tools: Snapshot (2026-10-13)

The animator: «Давай реализуем создание снапшотов». They asked for OverRig's snapshot tab, rebuilt
natively in the Tools card. Asked:

- **Object only.** Components (vertices, edges, polys) and particles were offered and declined.
- **A key on every frame.** Keys only where something moves the object were offered and declined.

## What OverRig does (read from `base_OverRig_scripts.mel`)

`apply_LOH_Fast(1)` (the Object button), through `BOVER_10_2_7f0d6f1fb...`:

- **The range**: the time slider's highlight `[a, b)`, read as `a .. b-1`. With no highlight it is
  the animation range `ast .. aet` (`BOVER_10_2_8658db37...`).
- **The locators**: one per selected object, snapped onto it, renamed `LOH_<name>`. Each takes its
  object's rotate order, or the panel's.
- **The bake**: each locator is parent-constrained to its object (locked channels skipped), baked
  with `bakeResults -sm 1` over the range, and its constraints deleted.
- **The look**: sized by the panel's size, colour index 13, wire colour (0.8, 0.5, 0.5). The
  locators are put in `OverRig_knots`.

The result is a free locator that repeats the object's world motion. Nothing follows it. It is
used as a constraint target, a reference, a pin.

## Ours

**A snapshot is a knot that drives nothing.** It is a fourth `knotplan` kind, `snapshot` (label
«Snapshot», suffix `_snapshot`, OverRig's colour (0.8, 0.5, 0.5), constraint None). Its locator is
built as a Knot's:

- it lives in the object's `Knots` group (in its character group, else the world `SkeldarKnots`);
- its size follows the object's (`knot_size`);
- its rotate order is the card's «Rotate order» (Object: the object's own);
- a temporary `parentConstraint` with no offset carries the object's world track;
- it is baked on every frame of the span (`bakeResults -simulation`), its rotates euler-filtered,
  a still channel left as a plain value;
- the constraint is deleted.

The object is never touched: no keys, no constraint, no pairBlend, no `attach`. So nothing is
refused for what the object is: a rig control, a bone, a constrained or IK-driven object, an object
riding a knot, a knot, another snapshot.

- **The span.** A highlight of more than one frame `[a, b)` gives exactly the highlighted frames
  `a .. b-1`, as OverRig does (no ramp: nothing blends). Otherwise it is the whole take, the
  knots' rule: the playback and animation ranges with the keys of the object and of everything
  above it.
- **Marked** `skeldarKnot = "snapshot"`, `skeldarSnapshotOf` = the object's UUID, and
  `skeldarKnotSpan`. It does NOT carry `skeldarKnotSource`. A snapshot rides nothing, so:
  - every path that walks riders skips it (`_with_riders`, `bake_order`);
  - removing the object's knots leaves the snapshot alone;
  - removing a knot that a snapshot was taken FROM leaves the snapshot alone too.
- **Refused**:
  - nothing selected;
  - a component selected (`pCube1.vtx[3]`): «components are not snapshotted - select the object».
- **Selected after the press**: the new snapshots. The press is one undo chunk with autoKey off.
- **The line**: «Snapshot: cube -> cube_snapshot over 0-40», or «Snapshot: 3 objects over 10-20
  (the highlight)».

### With the card's other presses

- **Remove** deletes a selected snapshot, and any knot riding it. The line counts snapshots apart:
  «1 snapshot deleted».
- **Bake** has nothing to write for a snapshot. It skips it and says so: «cube_snapshot is a
  snapshot - it drives nothing (Remove deletes it)».
- **Attach 0 / 1** skip it: it has no `attach`.
- **Layer** treats a selected snapshot as a plain keyed object, the snapshot itself. Until now
  `layerbake._object_of` followed a knot to the object it drives, and a snapshot drives nothing.
- **Knot, Across and the other knots** may be made on a snapshot like on any locator.
- **Delete character** takes it with the character's `Knots` group.
- **The subtitle** counts snapshots apart: «2 knots, 1 snapshot in the scene».

### The card

A toolrow **Snapshot** in Knots, after Aim and before the rotate order:

- icon `camera`, hint «free copy of the motion»;
- the tip: «Snapshot - select objects: each gets a locator repeating its motion in world space,
  keyed on every frame (of the highlighted range, else the whole take). Nothing follows it - use it
  as a target or a reference; Remove deletes it».

The hotkey row is `tools.snapshot`.

## Proof

- **Unit tests**, `test_tools_knotplan` and `test_tools_panel`:
  - the kind;
  - `snapshot_span` (a highlight, a one-frame highlight, the whole take);
  - the line, the subtitle, the removed and baked lines;
  - the press on a fake cmds;
  - the hotkey row.
- **`docs/superpowers/plans/verify_snapshot.py`**, mayapy standalone:
  - a keyed prop under an animated carrier, zxy, a locked channel, rotate pivot off its origin;
  - the snapshot on the prop's world track on every integer frame (place and rotation), the prop's
    curves and connections untouched;
  - a highlight keys exactly its frames, the snapshot holding its first and last values outside;
  - the card's rotate order;
  - a constrained object, and a bone of Manny's rig, snapshotted in place;
  - one undo;
  - the refusals changing nothing;
  - Remove deleting it, and a knot riding it;
  - Remove of the object's own knot leaving its snapshot;
  - Bake skipping it;
  - Layer on it treating it as itself;
  - Delete character taking a snapshot of a rig control.

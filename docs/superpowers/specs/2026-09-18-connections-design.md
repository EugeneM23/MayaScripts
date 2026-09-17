# Connections: the hands on the weapon, and off it, on the AdvancedSkeleton rig

**Date:** 2026-09-18
**Ask:** «Нужно сделать вкладку connections, в которой мы сможем привязывать
и отвязывать руки к оружию. Привязку и отвязку реализуем при помощи OverRig,
будем перепекать анимацию (важно, чтобы мы не ломали иерархию нашего рига)».

## What it replaces

`maya_scenesetup/connect.py` (Connect Arms To Weapon, 2026-08-21) did this
for the OverRig picker rig: it hung the IK end groups under the weapon's
geometry with `apply_Parent_in`. That module stays (the picker is behind a
flag) and is not touched. The rig today is the AdvancedSkeleton one, whose
IK hand controls `IKArm_R` / `IKArm_L` live at
`CustomOrientIKArm_*|IKExtraArm_*|IKArm_*` inside `MotionSystem`, and that
place is load-bearing: the solver, the `followMain`/`followRoot` switches
and the FK/IK align all read it. Re-parenting them is exactly "breaking the
rig hierarchy".

## The split (the design in one paragraph)

**The weapon is re-baked by OverRig; the hands are constrained and never
re-parented.** Connect lifts the weapon from the hand bone to world through
`apply_Parent_out` (its world track baked onto its own channels — measured
2026-09-18 in the standalone probe's live counterpart: drift 0.000000 at a
mid frame) and parent-constrains each chosen IK control to the weapon's
geometry with `maintainOffset`, the control's own keys cut first. Disconnect
bakes the controls over the range with `cmds.bakeResults`, deletes only our
constraints, and hangs the weapon back under the hand through
`apply_Parent_in`, so whatever the animator did with it out in the world
survives in the hand's space. Nothing in the rig's DAG moves.

Why not OverRig for the hands too: OverRig's rebake procs re-parent; that is
what they are. Why not `cmds` for the weapon too: the animator asked for
OverRig's rebake by name, the weapon is geometry under a bone and not rig,
and `parent_out`/`parent_in` are the procs the earlier Connect already
proved live (zero drift, round trip exact).

## Rules, each with a reason

- **Which hands**: two checkboxes, Right hand and Left hand, both on by
  default, remembered in `skeldarConnections_right/left`. A longsword and a
  spear are two-handed, a dagger is not; the animator ticks.
- **The grip is the CURRENT frame's.** `maintainOffset` captures the hand's
  offset from the weapon on the frame the animator is looking at, and the
  status says which frame. The control's keys are cut BEFORE the constraint
  (trap 37: keying a constrained channel splices a pairBlend) and its
  current values are written back after the cut (trap 58: `cutKey` leaves a
  channel wherever the DG last evaluated), read off the curves with
  `keyframe -eval`.
- **The arm goes to IK**: `FKIKArm_*.FKIKBlend` is set to 10. A blend that
  is KEYED at anything else is refused by name — that is the animator's own
  switching and overriding it silently would change their take. The poles
  are untouched (the elbow keeps answering to the body).
- **Identity by attribute**: every constraint we make carries
  `skeldarHandLink` = the weapon's UUID. `connected_sides` asks for it, so
  a constraint of somebody else's on the same control is neither counted
  nor deleted, and nothing is found by name.
- **Refusals before anything moves**: no rig (the `maya_rigs` refusal, by
  name when several); no weapon in the hand («Weapons > Add first»);
  already connected; a `MoCapConstraints` holder standing (a retarget in
  progress); a keyed blend; and OverRig's `mel_gate` (not loaded, or a
  time-slider highlight — trap 36 — which `apply_Parent_out` would bake
  across).
- **The retarget refuses a connected rig** (`maya_rig_retarget.hands_connected`,
  both in `run_retarget` and in `bake`): its `connect` would skip the
  constrained IK controls as foreign and the take would arrive with the
  hands standing still; its bake would lift the weapon link under them.
  Lazy guarded import, so the retarget keeps working without Scene Setup.
- **Weapons > Add / Remove already refuse a linked weapon**; the Weapons
  panel finds the weapon out in world through `bonedrive.driving_weapon`
  (the constraint on `weapon_r` targets the node and survives the move),
  which is the one line changed there.
- **One undo chunk per press.**

## The section

`maya_scenesetup/connections.py`, a row in `maya_hub.SECTIONS` after
Weapons: a header («Manny_Rig: LongSwordMesh in the hand, hands free» /
«… right hand, left hand connected to LongSwordMesh»), the two checkboxes,
Connect, Disconnect, a status line. **No shelf button and no icon** (the
2026-09-17 rule). Hotkey rows `window.connections`, `connections.connect`,
`connections.disconnect`.

## Testing

Unit: the pure halves (`hands_to_connect`, `blend_refusal`, `union_range`,
the messages, `header_text`), the panel on `FakeUiCmds`, and the boundaries
read off the source — no `cmds.parent(` anywhere (the hands are never
re-parented), `parent_out`/`parent_in`/`parentConstraint`/`bakeResults`
present, no `mel.eval`, the marker asked for by attribute, the retarget
refusing a connected rig, no shelf button.

Live (`docs/superpowers/plans/verify_connections.py`, over the command port
in the animator's Maya, which today holds NO rig — OverRig's procs need the
time slider and die in mayapy with «Cannot convert data of type int to
type float[]», measured 2026-09-18): a throwaway `Manny_Rig` added, the
sword attached, the IK hand keyed; Connect → the weapon in world with its
track intact, the IK control constrained by our constraint, the hand's
world matrix unchanged over the range, the rig's DAG unchanged (the
control's path is the same); a weapon nudge moves the hand; Disconnect →
the controls keyed, our constraint gone, the weapon back under the hand
with zero drift, the nudge kept; Retarget refused while connected; every
node the run created deleted afterwards.

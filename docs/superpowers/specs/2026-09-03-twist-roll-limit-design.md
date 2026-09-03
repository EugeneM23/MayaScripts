# The twist network's roll limit — 2026-09-03

The animator reported arm bones over-twisting on an imported clip
(`longsword Idle.0031.mb`). The whip is ours: `upperarm_twist_01_r.rotateX`
steps **223.50°** between frames 9 and 10, and `upperarm_twist_02_r`'s world
orientation steps **163.66°** at frame 29. This spec records what was
measured, the two candidate fixes that measurement **refuted**, and why the
change that ships is a refusal rather than better arithmetic.

Everything below was measured in the animator's open scene through the
command port on 2026-09-03. Nothing here is inferred.

## What breaks

`twist._network` computes `Δ = M0⁻¹ · M` and reads the roll as
`2·atan2(v·a, w)` through `decomposeMatrix → quatNormalize → quatToEuler`.

Two facts, each isolated on sandbox nodes rather than argued:

- **`quatToEuler` wraps its output into (−180°, +180°].** Fed a 190° twist as
  `(x, w) = (sin 95°, cos 95°)` it answers **−170°**; fed 350° it answers
  **−10°**. Discontinuities sit at exactly ±180°. `quatNormalize` in front of
  it is innocent — it passes `x` and `w` through element for element.
- **`decomposeMatrix.outputQuat` canonicalises the sign**, so a delta past
  180° is re-expressed the short way *before* our arithmetic sees it. The
  information is gone upstream of the wrap; nothing downstream can recover it.

So when the roll crosses ±180° the network's output jumps ~360° in one frame.
Measured on `upperarm_twist_01_r`: **+164.86° → −170.39°**, a 335.25° step,
times the 0.6667 weight = the 223.50° whip. Four whips on this clip, frames
**10, 16, 20, 29** — three clean ±360° wraps, the fourth the degeneracy at the
singularity itself. Sub-frame sampling puts **121.44° of the 134.33°** jump
inside one 0.1-frame interval: an instantaneous whip, not interpolation.

## Two candidate fixes, both refuted by measurement

**Remove the swing geometrically.** Transport the reference perpendicular by
the minimal rotation taking the build-pose bone axis to the current one
(Rodrigues, no trig), then read the residual angle about the current axis.
Implemented in Python against the real rig and measured per frame:
`upperarm_r` came out **−309.6 .. +206.6** — *identical* to what ships today.
Refuted.

**Read the driver's innermost rotate channel.** Confirmed in a sandbox that
the innermost channel of a rotate order is exactly a turn about the joint's
own axis: with order `xyz`, +30° on `rotateX` turns **30.0000°**, **0.0000°**
off the joint's own X (with `zyx` the same +30 lands 50.23° off — the claim
holds only for the innermost channel, which is what `axis_choice` already
checks). But measured against the geometric roll it **diverges by 138.46°** on
`upperarm_l`, where the matrix roll is still sound; and it is not available at
all for the follow segments, whose drivers (`hand_*`, `foot_*`) sit
**14.35–33.83°** off the segment axis, past the module's own 10° limit.
Refuted.

## Why no formula fixes it

The right arm's bone axis swings **160.0°** over this clip; `hand_r`'s swings
**174.0°**, very nearly a reversal. The roll of a bone whose axis sweeps that
far has **no continuous bounded definition** — it is path-dependent, the same
holonomy that makes parallel transport around a loop come back rotated. Both
formulations agree on a 516° range because there is nothing to disagree about:
the quantity itself is unbounded. A third formula would not help.

## Where the extreme input comes from

Not from our rig. Every arm bone carries a **pairBlend at weight 1.000** —
`input1` the imported clip's animCurves, `input2` the OverRig
parentConstraints — so the clip's keys are **muted** and the bones are driven
entirely by the IK. That is trap 37's signature exactly: an FBX merge onto a
rigged skeleton keys constrained channels and Maya splices the blend in.

The asymmetry no two-handed grip explains: the hands travel through space
almost identically (**368.76** vs **375.61** cm on the forearms, 458 vs 466 on
the hands) while the right forearm rotates **3.23×** more violently than the
left (117.72° vs 36.44° per frame), and the right upper arm **2.45×**
(112.05° vs 45.70°). The constraint outputs feeding those bones wind through
350–540° of euler range.

So the whip is a symptom of a damaged rig, faithfully reported. The tool's own
defect is that it reports it as a silent 223° whip instead of saying so.

## What ships

**The build refuses a segment whose roll leaves the window it can express,
and names it.** This is the module's existing character, not a new one: it
already skips a joint whose axis is more than 10° off the bone, and refuses a
channel driven by anything that is not ours — both by name. It simply never
checked the one thing that actually breaks.

- `lift(values)` — a sign-ambiguous angle sequence made continuous. The
  quaternion a matrix decomposes to is sign-ambiguous (`q` and `−q` are one
  rotation, Maya picks by a rule of its own and the pick changes frame to
  frame), so every raw reading can differ from its neighbour by 360° for no
  physical reason. Carrying the sign forward is what makes the sequence mean
  anything. Pure.
- `excursion(values, window)` — how far the lifted sequence leaves
  `(−window, +window]`, `0.0` when it fits. Pure.
- `sampled_rolls(delta_matrices, axis)` — the roll per sampled delta, lifted.
  OpenMaya only, so it is testable without a scene, the way `axes.py` is.
- `build` samples the driver's delta across the playback range **before
  creating anything**, and a segment that does not fit is skipped with its
  number in the message.

Two anchoring decisions, both load-bearing:

- **The zero is the build pose**, where `Δ` is the identity and the roll is
  exactly 0 — so the window is `(−180°, +180°]` around the build frame, and
  the sampling is anchored there rather than at the range start. A sequence
  anchored at frame 0 would place the window wrong by however much the roll
  had already travelled.
- **A span wider than 360° wraps wherever the zero sits**, so that is checked
  as well and needs no anchor at all. On this clip the two agree:
  `upperarm_r` spans 516° (refused either way), `upperarm_l` 75° and well
  inside (rigged).

Measured effect on this clip: **1 segment of 8 refused**. The other seven keep
working with room to spare — `upperarm_l` −40.3..+34.6 (139.7° of headroom),
both forearms and all four leg segments far inside.

## Deliberately not done

**Unwrapping the bake.** `twist.bake` samples the channel, so unwrapping it
needs the per-joint period (360° × the weight) or a recompute of the roll from
the network's own `delta`/`dot`/`weight` nodes before they are deleted. Both
are feasible; it would make a *legacy* broken rig bake to something continuous
instead of stepping. It is out of scope here for two reasons: with the refusal
in place a freshly built rig can never wrap, so this only patches files already
damaged; and it changes a code path whose ordering — sample, delete, key — is
carefully argued and worth touching on its own, with its own tests.

**A better roll.** See above: there is no continuous bounded roll for a bone
whose axis sweeps 160°. If the twist rig is ever wanted on clips like this,
the change is upstream — repair the trap-37 damage (`Bake+Delete` before the
merge, which `animimport`'s guard already asks for) so the arm's rotation is
the clip's own rather than a constraint winding through 540°.

**Widening the window past ±180°.** Unreachable: `decomposeMatrix` destroys
the >180° delta before our nodes run.

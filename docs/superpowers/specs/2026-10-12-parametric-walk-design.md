# Parametric walk: a walk cycle read once, re-built from knobs (2026-10-12)

The animator, with a walk cycle loaded in Maya (bones only, `Desktop/Walk_01.fbx`): «Можешь ли ты взять
анимацию костей персонажа … это анимация поход. Проанализировать эту анимацию построить ее математическую
модель и затем менять параметрически эту походку? Например делать короче шаг или добавить веса
амплитудности в шаг?» — then «давай попробуем сделать». Asked, and answered:

- **the first version is the knobs**; a character pose (the hunched goblin) plugs in later, so the model
  keeps the mean pose apart from the motion around it;
- **the result is a copy beside the source**, re-keyed on every change; the source is never touched;
- **all four groups of knobs**: step, pelvis, upper body and overlap, weight and exaggeration;
- **approach A** (below), the source's stance-foot slide kept as it is.

Like the physical stop, it is a **script outside the plugin** first:
`docs/superpowers/plans/walkparam/` — `walkmodel.py` (numpy only, no Maya: the analysis and the model),
`skeldar_walk.py` (Maya: reading the source, the copy, the keys, the window, the drop handler),
`verify_walk.py` (mayapy standalone on the animator's clip). Into the plugin once tuned.

## What the clip is (measured, read only, 2026-10-12)

`Walk_01.fbx`: 93 joints under `|Armature|root` (Cascadeur's layout: the Null at -90 X), ntsc (30 fps),
keys on every frame 0..31, **frame 31 = frame 0** in the pelvis's space (2e-4): a closed loop of 31 frames,
two steps. Root motion: `root` travels +Z 176.95 cm a cycle (88.5 cm a step, 1.71 m/s), stands exactly
under the pelvis (1.5e-7 cm) with no rotation, and follows its sway. The pelvis bobs 91.2..98.9 cm (two
lows just after the contacts, two highs on the passing poses) and sways 4 cm, mostly toward the left foot.
Left stance about frames 10-23, right 26-9 (the ankle or the ball slower than 1/5 of the travel speed);
the stance foot slides ~0.3 cm a frame. Every rotate order xyz, no jointOrient; the only bones whose local
translation moves are root, pelvis, the `ik_*` helpers and the left leg by 0.05 cm (the clip's own).
Every helper follows a body bone rigidly (`ik_foot_*` the feet, `ik_hand_*` the right hand,
`camera_*` / `interaction` / `ik_*_root` the root, `weapon_*` the hands; errors <= 4e-5).

Fourier, for the choice of model: the upper body is smooth — 4-6 harmonics reproduce the spine, arms,
pelvis and head within 1 deg — and the legs are not: thigh, calf, foot and ball keep 2-4 deg of error at
8 harmonics, because a contact is a corner (planted, then an arc). **So the legs are built from where the
feet go, through IK, never from their joint angles.**

## The approach

Rejected: Fourier per channel (feet slide as soon as the stride changes, the legs lose their corners);
blending several walks (needs 2+ clips of one character — a later «style» knob).

**A — a contact-based hybrid that reproduces the source exactly at its defaults.** Everything the model
reads is the source's own data, sampled at a phase; a knob scales a deviation, shifts its sampling time, or
moves a footprint. At the defaults every factor is 1 and every shift 0, so the copy IS the source (by
construction, gated to 1e-4 cm / 1e-3 deg).

## The model (`walkmodel.py`)

Maya's row vectors throughout: a world matrix is `local · parent`, a position its row 3.

**The source** — `Clip(names, parents, worlds[J, P+1, 4, 4], fps, up)` — every joint's world matrix on
frames 0..P. Refusals by name: not a closed loop (the last frame's pose in the pelvis's space differs from
the first's by more than a typical frame-to-frame change), no root travel (an in-place clip: not in v1),
a curved path (the root's heading turns), no `thigh/calf/foot/ball_l/_r` (UE names; other conventions
later through `maya_skeletonmap`), a foot that never stops.

**The sampler.** Every joint's world matrix at a FRACTIONAL source time τ: positions minus the travel line
are periodic, rotations are log-vectors about the joint's chordal mean; both through a periodic Catmull-Rom
over the P samples, the travel added back. Exact at whole frames.

**The travel frame.** `fwd` = the root's horizontal travel per cycle `T` normalised, `up` = the scene's,
`side = up × fwd` (the character's left). The travel line `L(τ) = O + T·τ/P`, `O` chosen so the root's
deviation from it averages zero.

**The new cycle**: N frames (the tempo), new frame f ↔ phase φ = f/N ↔ source time τ = φ·P; new travel
`T' = k_stride·T`, `L'(φ) = O + T'·φ`. Keys on frames 0..N; frame N = frame 0 moved by `T'`.

**Root and pelvis.** Their positions as deviations from the travel line, in (fwd, side, up):
`fwd` (the surge: the body slowing at a contact) × `k_stride·g_ex`; `side` (sway) × `g_sway·g_ex`;
the pelvis's `up` (the bob) about its mean × `g_bob·g_ex`, shaped by the weight (below), minus the
lowering Δ (below). The root takes the same horizontal gains (it stands under the pelvis in the clip).
The pelvis's world rotation = `exp(g_prot·g_ex·ω(τ)) · mean`; the root's rotation as the source's.

**Upper body.** Each bone's LOCAL rotation `exp(g·g_ex·ω_j(τ_j)) · mean_j`, its local translation the
source's at τ; `g` by region — spine (`spine_*`, `neck_*`), arms (`clavicle`, `upperarm`, `lowerarm`,
`hand` and their twist bones), fingers 1 (they keep the source's motion, lagged with the hand). The head is
in WORLD: `exp(g_head·g_ex·ω_head(τ)) · mean` (0 holds the head steady, as a walker's eyes do).
**Overlap** samples a bone later: `τ_j = τ − frac_j·lag·P/N`, `lag` = the Overlap knob + the weight's
share, `frac` 0.2 (spine_01) rising 0.1 a bone to 0.6 (spine_05), neck 0.7/0.8, head 0.9, clavicle 0.6,
upper arm 0.8, forearm, hand and fingers 1.0.

**Feet.** Per foot, from the source: the stance interval [on, off] (the longest circular run where
min(ankle speed, ball speed) < travel per frame / 5), the footprint `S` = the foot's world matrix at
mid-stance, and its coordinates (c, σ, υ) against the travel line there.
- New footprint `S'`: S's rotation, at `L'(mid) + k_stride·c·fwd + (σ ± width/2)·side + υ·up` (+ for
  the left foot). Consecutive footprints are therefore `k_stride` times the source's apart.
- **Stance**: `foot'(τ) = E(τ) · S'`, `E = foot(τ) · S⁻¹` — the foot does exactly what it did on its
  footprint (the heel-to-toe roll, the slide), on the new one.
- **Swing**: the progress `s(τ)` = the foot's along-travel coordinate from lift-off (0) to strike (1);
  the reference `Ref(τ)` = the departure footprint moved by `s·T`; `E_sw = foot(τ) · Ref⁻¹`, its
  translation split into the straight blend `b = lerp(e_off, e_on, s)` and the lift `e − b` (no
  along-travel part, by the definition of s). New: `Ref'` = the new footprint moved by `s·T'`, translation
  `b + (0, g_lift·g_ex·lift_up, lift_side)`, rotation the source's. Continuous with the stance at both
  ends at any knob.

**Legs**: two-bone IK per frame from the new hip (thigh's position under the new pelvis) to the new ankle,
bone lengths the source's at τ, the knee bending toward the source's knee direction (its offset from the
hip-ankle line, in the travel frame). Thigh and calf turned by the rotation that takes the source's
(bone direction, leg-plane normal) onto the new ones — so a bone keeps its roll and at the defaults turns by
the identity. The foot's world rotation is the footprint model's; the ball and the leg twist bones keep the
source's local rotation.
**Reach**: no knee straighter than the straightest the source ever has (`reach = max d/(L1+L2)`); a frame
that would need more lowers the pelvis — `Δ` the largest drop any frame of either leg needs, one constant
for the cycle, said on the status line («pelvis lowered 2.1 cm for the stride»).

**Helpers**: a helper bone that follows a body bone rigidly in the source (`helper · bone⁻¹` constant to
1e-3; among ties the shallowest bone) keeps that relation; any other keeps its source local transform.

**Weight** `w` (-1..2, 0 = the source): the bob's low half × (1 + 0.5w), its high half × max(0, 1 − 0.15w);
the bob's clock slowed around the low poses (a warp `ψ(φ) = φ + β/(4π)·sin(4π(φ − φ0))`, β = 0.3w, centred
0.05 of a cycle after each low: it lingers down and rises slower); +w frames of overlap (the total kept
>= 0). Deeper bob → the IK bends the knees deeper by itself. The constants are first guesses, tuned with
the animator.

**Exaggeration** `g_ex` multiplies every deviation above (surge, sway, bob, pelvis rotation, spine, arms,
head, foot lift) — never the stride, the tempo or the fingers.

## Knobs

| Group | Knob | Range | Default |
|---|---|---|---|
| Step | Stride × | 0.4 - 1.8 | 1 |
| | Tempo: frames a cycle (whole: a seamless loop) | P/2 - 2P | P |
| | Foot lift × | 0 - 3 | 1 |
| | Width ± cm | -15 - 25 | 0 |
| Pelvis | Bob × / Sway × / Rotation × | 0 - 3 | 1 |
| Upper body | Spine × / Arms × / Head × | 0 - 3 | 1 |
| | Overlap (frames) | 0 - 6 | 0 |
| Weight | Weight | -1 - 2 | 0 |
| | Exaggeration × | 0 - 2 | 1 |

Speed = stride × tempo, shown on the status line with the cycle length and the stride in cm.

## The copy (`skeldar_walk.py`)

`cmds.duplicate` of the source's top node (no input connections: no curves), named `<top>_walk`, moved
`Offset` cm (default 100) along `side`, marked `skeldarWalk` = JSON {source UUID, knobs, version}. Every
change rewrites its curves in ONE undo chunk: translate where the source has translate curves, rotate
everywhere the source has rotate curves, frames 0..N, auto tangents, the euler nearest the previous frame
(trap 108). Locals from the model's world matrices against the SOURCE parents' (the offset lives on the
copy's top): `R = RA⁻¹ · L · JO⁻¹` in the joint's rotate order. The window reads a copy's knobs back from
its marker; analysis is cached per source UUID for the session.

**The window** (`cmds`, physstop's shape): Analyse (the selection's skeleton — a joint of the source, or
any node of a copy, which names its source), the four groups of sliders, Offset, Update / Reset / Delete
copy, and a status line: the clip («Walk_01: 31 frames, stride 88.5 cm, 1.71 m/s, stance 47 %») and the
last update (speed, stride, frames, the lowering, the largest stance-foot slide, the time it took). A
released slider updates the copy. Dropped into a viewport it reloads itself (trap 220).

## Proof

- `tests/test_walkmodel.py` — the pure model on a synthetic walker: the sampler exact at whole frames and
  periodic, IK exact and length-keeping, the alignment the identity at the defaults, the identity of the
  whole model, the stance foot moving as the source's on a moved footprint, each knob doing what it says.
- `verify_walk.py` — mayapy standalone on a copy of `Walk_01.fbx` (read from the Desktop, never committed):
  the analysis numbers; the defaults equal to the source on every bone and frame; stride 0.7 / 1.3, tempo
  25 / 40, lift, width, bob, sway, arms, head, overlap, weight, exaggeration each measured; bone lengths,
  the seamless loop and the stance foot's slide never worse than the source's; the source's curves
  unchanged; one Ctrl+Z.
- The live try — the window in the animator's Maya — is theirs.

Not built: an in-place clip, a curved walk, non-UE names, the character pose (the goblin) — the next step,
replacing the mean pose — several clips (style), stance duration as a knob, removing the source's slide.

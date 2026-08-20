# Overshoot, redesigned — 2026-08-20

`maya_overshoot.py` came in with the initial commit and was never touched. The
animator's report: *"качество какое-то плохое, пользовался только Spring"*, and
*"хорошо бы иметь возможность сделать овершут не только в конце"*. This spec says
what is wrong, why it is wrong at the level of the algorithm rather than the
constants, and what replaces it.

## What the old tool does

For each selected object it finds the **last key of the whole channel**, measures
`v = value(t_last) - value(t_last - 1)`, and writes a key on every frame of a
damped sinusoid into an **override** anim layer whose weight is stepped from 0 to
1 so the layer does not swallow the animation before the pose.

## Why it reads badly

Six defects, in the order they cost quality.

**1. The velocity is measured over one frame, at the one place where it is
smallest.** An animator eases into a pose, so the base curve's slope at the pose
key is nearly zero by construction. The amplitude is proportional to that slope
(`maya_overshoot.py:62`), so the harder the animator sells the arrival, the less
overshoot the tool gives. It is also frame-rate dependent: at 60 fps the
one-frame delta halves and so does the result.

**2. Amplitude and settle length are the same knob.**
`overshoot_amount = velocity * strength * duration * 0.3` (`:91`) — `duration`
multiplies the size. Physically a longer settle *does* mean a wider excursion for
the same entry speed (`A = v/ω`), but only through the entry speed, and here the
entry speed is the broken quantity from defect 1. The animator cannot ask for a
15 cm overshoot; only for a number that happens to produce one.

**3. The shapes are not normalized, so the type buttons change the size.**
Measured peaks of the three shapes as written: Spring `sin(3πt)e^{-4t}` → 0.5604,
Elastic `sin(4.5πt)e^{-2.5t}` → 0.7693, Bounce `|sin(3πt)|e^{-5t}` → 0.4973.
Switching Spring → Elastic multiplies the excursion by 1.37 before it changes any
character. `strength` therefore corresponds to nothing measurable.

**4. A key on every frame** — up to 120 per channel (`:103`). That is a bake, not
animation; the graph editor cannot be used on the result. Worse, the analytic
extremes fall *between* frames, so the real peak is clipped by a
duration-dependent amount. A hand-animated settle is 4-7 keys.

**5. Two outright bugs.**

- The layer weight steps to 1 at `global_last` = the **maximum** last-key time
  over all channels of the group (`:79-82`). A channel that ends earlier has its
  overshoot multiplied by weight 0 for part of its window and is silently
  suppressed. Only a rig where every channel ends on the same frame escapes.
- The final key is written twice (`:103` inside the loop, then `:108`), the second
  write flattening whatever the decay had left.

**6. Bounce bounces the wrong way and with the wrong rhythm.** `abs(sin)` × the
direction of travel sends the object *past* the pose again and again — through
the floor, three times, at a constant period. A real bounce goes **back the way
it came** and its intervals shorten geometrically.

## The thing behind all of it

An overshoot is not a tail glued onto a stopped object. It is the object **not
stopping**: it passes the pose still moving and is pulled back. So the offset the
tool adds has to carry a real velocity through the pose key, and that velocity
has to come from somewhere. The base curve does not have it — the animator spent
it on the ease-in. Adding a fast tail after a fully decelerated arrival gives a
velocity step at the pose: the object stops and is then kicked. That is the
"плохое качество", and no choice of constants fixes it.

What a hand-animator does instead is spend the ease-in *later*: the arrival is
straightened so the object reaches the pose at speed, flies past, and the easing
happens at the end of the settle. The redesign does exactly that, inside the
layer, from measurements of the animator's own curve.

## Design

### Where the overshoot goes

Selected keys, else the current frame (the animator's choice). Selected keys carry
**both a time and a channel**, so selecting only `translateY`'s key overshoots
only Y, and selecting a column of keys does a whole pose. With no key selection
the tool takes the key at — or the nearest one before — the current frame on every
enabled channel. The status line always names what it chose.

The last key of the channel is no longer special in any way.

### The window

For one pose key at time `T` on one channel:

- `T_prev` = the previous key on that channel, `P` = base value at `T`,
  `Δ = P - value(T_prev)`. No previous key, or `|Δ|` below epsilon: skip the
  channel — nothing arrived, so nothing overshoots.
- Sample the base curve across `[T_prev, T]` and find `v_peak`, the largest
  `|slope|` in the segment, at time `T_fast`.
- **Pre-window** `[T_fast, T]`: the offset is `line - base`, where `line` is the
  straight line of slope `v_peak` ending at `P` at `T`. At `T_fast` that line is
  tangent to the base curve, so the offset and its slope are both zero there —
  the window opens with no discontinuity, and it opens exactly where the object
  was fastest. Between there and the pose the object now travels at constant speed
  instead of decelerating.
- **Settle window** `[T, T + N]`: the shape, scaled so its peak is the requested
  amount. `N` comes from the Frames field, clamped to `T_next - T - 1` so the
  offset is back to zero before the animator's next key.

### The shapes

Two families. Both are normalized to **unit peak**, so the amount the animator
types is the excursion they get and switching type changes character only.

Damped sinusoid, `raw(u) = sin(π c u) · e^{-k u}` on `u ∈ [0,1]`, `u = (t-T)/N`.
Integer `c` makes `raw(1) = 0` exactly, so the shape lands on the pose with no
residual, and gives exactly `c` lobes. Measured constants:

| Button | c | k | peak of raw | at u | entry slope `f'(0)` | last lobe |
|---|---|---|---|---|---|---|
| **Snap** | 1 | 3.0 | 0.3342 | 0.257 | 9.40 | (single lobe) |
| **Spring** | 3 | 4.0 | 0.5604 | 0.124 | 16.82 | 6.9 % |
| **Elastic** | 7 | 2.5 | 0.8419 | 0.066 | 26.12 | 11.7 % |
| **Recoil** | 3 | 6.0 | 0.4452 | 0.107 | 21.17 | 1.8 % |

`f'(0) = πc / peak` is the entry slope of the normalized shape; the real entry
slope at the pose is `A · f'(0) / N` in units per frame. Snap has one lobe and
therefore no undershoot — the single overshoot most game work wants. Spring is the
old shape, kept: its geometry was never the problem.

Bouncing arcs for **Bounce**, one-sided and **against** the direction of travel,
which is what a landing does. Restitution `e` (default 0.5): apex heights
`h_i = e^{2i}`, arc durations `d_i = d_0 e^i` with `d_0` set so the arcs fill `N`,
arcs kept while `h_i > 0.02`. Four arcs at `e = 0.5`.

`c` (Swings) and `k` (Decay) stay editable, so the five buttons are presets over
one continuous family rather than five hardcoded formulas.

### Amplitude

`A = amount% · |Δ|` — the peak as a percentage of the move that arrived. Legible,
frame-rate independent, and directly checkable: the largest keyed offset equals
`A`.

The physically consistent amount is the one whose entry slope matches the speed
the object actually had: `A_phys = v_peak · N / f'(0)`. The tool computes it and
reports it; asking for more than the base curve can feed leaves a velocity step at
the pose, which the status line names rather than hides.

### Keys and tangents

Times are rounded to whole frames and the shape is evaluated **at the rounded
time**, so every key sits on the curve; the set is then rescaled so the largest
key is exactly `A`. Keys collapsing onto one frame (a short `N`) are deduped,
keeping the larger excursion.

- Sinusoid: `T_fast` (0), the pre-window's own extreme, `T` (0), each lobe
  extreme, `T + N` (0). Extremes get **auto** tangents, which Maya flattens at a
  local extreme — correct, since they are extremes. 6-9 keys per channel per pose.
- Bounce: contact and apex per arc. Contacts get **linear** tangents so the
  velocity reversal survives; auto tangents would round the impacts into mush.
  ~7 keys.

### Layers

One **additive** layer per object per channel group: `<obj>_overshoot_pos`,
`<obj>_overshoot_rot`. Additive rather than override removes the whole weight
mechanism and bug 5 with it: an additive layer with no keys is zero offset, so the
base passes through untouched everywhere outside the windows, with nothing to step
and nothing to gate.

Re-applying does not delete the layer. It clears the layer's keys inside the
window it is about to write and leaves every other pose's work alone — the old
tool deleted the whole layer, and any hand tweak with it. The layer's **weight is
the strength dial**: it scales the whole effect live, with no re-run.

The whole apply is one undo chunk.

### UI

Same `cmds` window, same shape: Translate and Rotate checkboxes, per-group Amount
% and Frames, five type buttons. Swings, Decay, Restitution and a *Straighten
arrival* checkbox live in a collapsed Advanced section. `show_overshoot_ui()`
moves behind `if __name__ == "__main__"` so pasting the file into the Script
Editor still opens the window while importing it (tests) does not.

Every callback goes through a `_run` wrapper that puts the failure on the status
line instead of the Script Editor (trap 20).

## To be measured before implementing

Three Maya semantics this design rests on, none of them verified yet:

1. Does `cmds.setKeyframe(obj, at=attr, t=, v=, animLayer=L)` write `v` as the
   **offset** on an additive layer's curve, or does it try to reach `v` as a final
   value? If the former is wrong, write through
   `animLayer(L, q=True, findCurveForPlug=plug)` instead.
2. Additive rotation accumulation. `animLayer -rotationAccumulationMode`: which
   setting makes our per-channel euler offsets add per channel, and is the combined
   rotate then `base + offset` to tolerance?
3. `keyTangent -outAngle`'s slope convention (units per frame or per second).
   Avoided by construction — every key sits on the analytic curve and tangents are
   left to `auto`/`linear` — but the pre-window's tangency claim should be
   confirmed numerically rather than trusted.

## Verification

`docs/superpowers/plans/verify_overshoot.py`, run in the live scene through the
command port. Gates:

1. The peak of the combined motion equals `amount% · |Δ|`.
2. The base animation outside `[T_fast, T+N]` is unchanged to 1e-9.
3. No velocity step at `T` beyond 2 % of `v_peak` for the sinusoid families when
   the amount is at or below `A_phys` (Bounce's contacts are corners on purpose).
4. Deleting the layer restores the original animation exactly.
5. Re-applying on the same pose is idempotent — same keys, no accumulation.
6. A pose in the middle of a clip leaves the next key untouched.
7. Amplitude is linear in amount %; layer weight scales the result.
8. Bounce never crosses to the far side of the pose.
9. Rotation: combined rotate equals base + offset to tolerance (validates the
   accumulation mode).
10. At most 10 keys per channel per pose.

Pure-function unit tests (`tests/test_overshoot.py`) cover the shapes'
normalization and lobe counts, the arc series, the key planner against a sampled
base curve given as data, the clamping against the next key, and the dedupe.

## Accepted limits

- **Rotation is overshot per euler channel**, in the direction of the euler delta
  that arrived. For the 10-30 % excursions this tool makes, that is the axis the
  animator moved; for a large multi-axis move near gimbal it is approximate. Doing
  it properly means a quaternion delta about the incoming rotation axis converted
  back to euler per frame — dense keys and a rotate-order dependency, for a gain
  nobody will see at 15 %.
- The straightening is measured from the current base curve, so applying twice
  after editing the arrival re-measures rather than compounding. That is the right
  behaviour, but it does mean the window can move between applications.
- Keys written past the end of the playback range are reported, not clamped, and
  the range is never changed — the clip length is the animator's decision.

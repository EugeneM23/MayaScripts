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

**1. The velocity is measured over one frame, at the one place where it is
smallest.** An animator eases into a pose, so the base curve's slope at the pose
key is nearly zero by construction. The amplitude is proportional to that slope
(`maya_overshoot.py:62`), so the harder the animator sells the arrival, the less
overshoot the tool gives. It is also frame-rate dependent: at 60 fps the one-frame
delta halves and so does the result.

**2. Amplitude and settle length are the same knob.**
`overshoot_amount = velocity * strength * duration * 0.3` (`:91`) — `duration`
multiplies the size. The animator cannot ask for a 15 cm overshoot; only for a
number that happens to produce one.

**3. The shapes are not normalized, so the type buttons change the size.**
Measured peaks of the three shapes as written: Spring `sin(3πt)e^{-4t}` → 0.5604,
Elastic `sin(4.5πt)e^{-2.5t}` → 0.7693, Bounce `|sin(3πt)|e^{-5t}` → 0.4973.
Switching Spring → Elastic multiplies the excursion by 1.37 before it changes any
character. `strength` therefore corresponds to nothing measurable.

**4. A key on every frame** — up to 120 per channel (`:103`). That is a bake, not
animation; the graph editor cannot be used on the result. Worse, the analytic
extremes fall *between* frames, so the real peak is clipped by a
duration-dependent amount.

**5. Two outright bugs.**

- The layer weight steps to 1 at `global_last` = the **maximum** last-key time
  over all channels of the group (`:79-82`). A channel that ends earlier has its
  overshoot multiplied by weight 0 for part of its window and is silently
  suppressed. Only a rig where every channel ends on the same frame escapes.
- The final key is written twice (`:103` inside the loop, then `:108`), the second
  write flattening whatever the decay had left.

**6. The bounce has the rhythm of a metronome.** `|sin(3πt)| e^{-5t}` puts its
contacts at equal intervals. A ball's intervals shrink geometrically — the fall
time goes as `√h` — so equal spacing is the one thing that stops a bounce reading
as a bounce.

## The thing behind all of it

All five of the amplitude defects share a cause, and it is not the constants.

The old tool leaves the pose key where it is and adds the excursion **after** it.
So the object decelerates into the pose, stops there, and is then kicked out and
pulled back. That kick is the "плохое качество": it is a second move, not a
follow-through.

The obvious repair — give the object speed at the pose by straightening its
arrival — cannot work, and it is worth writing down why, because it looks
plausible. Speed at the pose means distance covered just before the pose. For a
100-unit move over 10 frames with an ordinary ease-in, the peak speed is about
19 units/frame while the last frame covers about 2. Arriving at the pose at that
peak speed for even three frames means being 51 units — half the entire move —
behind where the animator put the object. Nothing that preserves the animator's
timing can produce speed at an eased pose. The momentum is not there to borrow.

So stop trying to add motion after the stop, and move the stop instead:

> **The pose key becomes the extreme of the overshoot. The pose becomes the
> settle target, reached `N` frames later.**

At `T` the object is at `P + A` with zero velocity — which is exactly what a
turning point is, so the arrival keeps its own ease and nothing is
discontinuous. Nothing before `T` is retimed. The excursion is reached by
scaling the arrival, not by inventing a second move, and the animator's timing
landmark still lands on their key: a punch that hit at frame 20 still hits at
frame 20, 15 % further out, settling back by 32.

## Design

### Where the overshoot goes

Selected keys, else the current frame (the animator's choice). Selected keys carry
**both a time and a channel**, so selecting only `translateY`'s key overshoots
only Y, and selecting a column of keys does a whole pose. With no key selection
the tool takes the key at — or the nearest one before — the current frame on every
enabled channel. The status line always names what it chose.

The last key of the channel is no longer special in any way.

### What one pose needs from the scene

Per channel, per pose key at `T`: the previous key `(T_prev, P_prev)`, the pose
value `P`, and the next key time `T_next`. That is all — no curve sampling, no
velocity measurement, nothing that depends on frame rate or on the animator's
tangents.

- `Δ = P - P_prev`, `A = amount% · |Δ| · sign(Δ)`.
- **No previous key, or `|Δ|` below epsilon: skip.** Nothing arrived, so nothing
  overshoots.
- **The pose must be an extreme.** If the next segment continues in the *same*
  direction (`sign(Δ_next) == sign(Δ)` and `|Δ_next|` above epsilon), the key is
  a pass-through, not a stop; an extreme there would be a hitch in the middle of
  a move. Skip it and say so. A reversal or a hold is a stop and is fine.
- `N` = the Frames field, clamped to `T_next - T - 1` so the settle is finished
  before the animator's next key. Too few frames for the requested swings: reduce
  the swings and report it.

### The settle shape

A spring released from rest — the exact motion of an object let go at the
extreme:

```
f(u) = e^{-k u} · ( cos(π c u) + (k / π c) · sin(π c u) )        u = (t - T) / N
```

`f(0) = 1` and `f'(0) = 0`, so it leaves the extreme the way an extreme is left.
Its derivative collapses to

```
f'(u) = -e^{-k u} · (k² + (π c)²) / (π c) · sin(π c u)
```

which is zero **only** at `u = i/c`, where `f(i/c) = (-1)^i · r^i` with
`r = e^{-k/c}`. So the shape has exactly `c` turning points, evenly spaced, with
each swing keeping a constant fraction `r` of the last one, and it is monotone
between them.

That is the whole implementation. The tool writes those `c+1` keys — times
`T + round(i·N/c)`, values `A·(-1)^i·r^i`, **flat tangents** because they are
turning points and a turning point has zero velocity — and Maya's cubic between
two flat keys reproduces the shape. The last key is forced to exactly `0`, so the
pose is reached exactly rather than off by `r^c`.

`r` is exposed rather than `k`: *"each swing keeps 30 % of the last"* is a
sentence an animator can act on, and `k = -c·ln(r)` recovers the closed form for
the verification script.

| Button | swings `c` | ratio `r` | what it reads as |
|---|---|---|---|
| **Snap** | 1 | — | out and back, no undershoot. Two keys. |
| **Spring** | 3 | 0.30 | out, back past, settle |
| **Elastic** | 6 | 0.60 | rubbery, many swings |
| **Recoil** | 2 | 0.15 | out, one small undershoot, dead |
| **Bounce** | arcs | `e` = 0.5 | a ball dropped onto the pose |

Bounce is the same idea with gravity instead of a spring: released at `A`, it
falls to the pose, bounces to `A·e²`, and so on, with fall times going as `√h`.
Apex `i` is at height `A·e^{2i}`, the first fall takes `d = N/(1 + 2e/(1-e))`
frames and each later arc `2d·e^i`; arcs are kept while `e^{2i} > 0.02`. Contacts
get **linear** tangents so the impact keeps its corner — auto tangents would
round it into mush — and apexes get flat ones. Seven keys at `e = 0.5`. The whole
excursion stays on the overshoot side of the pose, because the pose *is* the
floor.

`c` and `r` stay editable, so the five buttons are presets over two continuous
families rather than five hardcoded formulas.

### The arrival

The excursion has to be reached by the incoming move, and the layer does it with
**one key**: offset `0` at `T_prev`, offset `A` at `T`. Between them Maya's own
cubic lifts the arrival from `0` to `A`, so the combined curve is the animator's
move scaled to `Δ + A` over its original span. For the common case — a two-key
auto-tangent segment — the layer's cubic is the same cubic as the base's, so the
scaling is exactly proportional.

For a segment the animator has shaped by hand, the tangent **types and weights of
the base's two keys are copied onto the layer's two keys**, so a linear snap into
the pose stays a linear snap instead of being softened by a stock ease.

`Peak delay` (Advanced, default 0) moves the extreme to `T + p` for animators who
want the pose crossed before the extreme rather than at it. At `p = 0` the extreme
lands on the selected key, which preserves the timing the animator dialled.

### Where the keys go

An **additive** anim layer per object per channel group: `<obj>_overshoot_pos`,
`<obj>_overshoot_rot`. Additive rather than override removes the whole weight
mechanism and bug 5 with it: a layer with no keys is zero offset, so the base
passes through untouched everywhere outside the windows, with nothing to step and
nothing to gate. The layer's **weight is the strength dial** — it scales the
result live, with no re-run.

Re-applying does not delete the layer. It clears the layer's keys inside the
window it is about to write, so other poses' work survives; the old tool deleted
the whole layer and any hand tweak in it.

A *Bake into curves* checkbox writes the same plan straight into the base curves
instead — the key list is identical modulo `P`, since a layer holds `A·f(u)` where
a base curve holds `P + A·f(u)`. That is the destructive-but-legible option: four
keys the animator can see and drag, which is what they would have made by hand.

The whole apply is one undo chunk.

### UI

Same `cmds` window: Translate and Rotate checkboxes, per-group Amount % and
Frames, five type buttons. Swings, Ratio, Restitution, Peak delay and *Bake into
curves* live in a collapsed Advanced section. `show_overshoot_ui()` moves behind
`if __name__ == "__main__"` so pasting the file into the Script Editor still opens
the window while importing it (tests) does not.

Every callback goes through a `_run` wrapper that puts the failure on the status
line instead of the Script Editor (trap 20).

## The one unverified Maya semantic

Does `cmds.setKeyframe(obj, at=attr, t=, v=, animLayer=L)` write `v` as the
**offset** on an additive layer's curve, or does it try to reach `v` as a final
value? If the latter, write through
`animLayer(L, q=True, findCurveForPlug=plug)` instead. Gate 1c is built to say
which: an extreme reading 120 is an offset, one reading 20 is an absolute. The
*Bake into curves* path does not depend on the answer, which is one reason to
build both.

How an additive layer accumulates euler offsets is **not** configurable —
Maya 2027 has no `-rotationAccumulationMode` flag at all (trap 41) — so gate 12b
measures the combined channel instead of setting a mode.

The redesign needs nothing else from Maya's awkward corners: no tangent angles,
no curve sampling, no time-unit conversions.

## Verification

`docs/superpowers/plans/verify_overshoot.py`, run in the live scene through the
command port. Gates:

1. The combined value at `T` equals `P + amount% · |Δ|` — the extreme lands on
   the selected key, at the requested size.
2. The combined curve is unchanged before `T_prev` and after `T + N`, to 1e-9.
3. The turning points sit at `T + i·N/c` with the values `A·(-1)^i·r^i`, and the
   combined curve has no other turning point in the window.
4. Combined velocity at `T` is zero to tolerance — the extreme is an extreme, not
   a corner.
5. Deleting the layer restores the original animation exactly.
6. Re-applying on the same pose is idempotent — same keys, no accumulation.
7. A pose in the middle of a clip leaves the next key untouched.
8. Amplitude is linear in amount %; layer weight scales the result.
9. Bounce never crosses to the far side of the pose, and its contact intervals
   shrink by `e`.
10. A pass-through key is refused with a named reason; a first key is skipped.
11. At most `c + 3` keys per channel per pose.
12. Rotation: combined rotate equals base + offset to tolerance (validates the
    accumulation mode).

Pure-function unit tests (`tests/test_overshoot.py`) cover the shape's turning
points against the closed form, the geometric ratio, the arc series and its
shrinking intervals, the key planner, the clamping against the next key, the
swing reduction when there is no room, and every refusal.

## Accepted limits

- **Rotation is overshot per euler channel**, in the direction of the euler delta
  that arrived. For the 10-30 % excursions this tool makes, that is the axis the
  animator moved; for a large multi-axis move near gimbal it is approximate. Doing
  it properly means a quaternion delta about the incoming rotation axis converted
  back to euler per frame — dense keys and a rotate-order dependency, for a gain
  nobody will see at 15 %.
- The turnaround at the extreme is as soft as Maya's flat-to-flat cubic makes it.
  A sharper snap would need tangent weights, and no animator has asked yet.
- Keys written past the end of the playback range are reported, not clamped, and
  the range is never changed — the clip length is the animator's decision.

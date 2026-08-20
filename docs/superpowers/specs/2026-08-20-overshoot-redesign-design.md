# Overshoot, redesigned — 2026-08-20

`maya_overshoot.py` came in with the initial commit and was never touched. The
animator's report: *"качество какое-то плохое, пользовался только Spring"*, and
*"хорошо бы иметь возможность сделать овершут не только в конце"*.

The tool keeps its original concept, which the animator restated after seeing an
alternative and rejecting it: **the pose key stays where it is and the tool
builds the stop after it** — *"наш скрипт должен достроить овершут, то есть тип
остановки предмета... анимация должна начаться с того места, где был последний
ключ"*. What changes is everything about how the numbers are arrived at.

## What the old tool does

For each selected object it finds the **last key of the whole channel**, measures
`v = value(t_last) - value(t_last - 1)`, and writes a key on every frame of a
damped sinusoid into an **override** anim layer whose weight is stepped from 0 to
1 so the layer does not swallow the animation before the pose.

## Why it reads badly

**1. The speed is measured over one frame, at the one place where there is
none.** An animator eases into a pose, so the base curve's slope at the pose key
is nearly zero by construction. The amplitude is proportional to that slope
(`maya_overshoot.py:62`), so the harder the animator sells the arrival, the less
overshoot the tool gives. It is also frame-rate dependent: at 60 fps the
one-frame delta halves and so does the result. This is the defect that matters
most, and the animator's own prescription fixes it: take the speed **from the two
keys of the move**, `Δ / frames`, which is what the move actually did.

**2. Amplitude and settle length are tangled through a magic number.**
`velocity * strength * duration * 0.3` (`:91`). Nothing in that expression is a
quantity anyone can name.

**3. The shapes are not normalized, so the type buttons change the size.**
Measured peaks as written: Spring `sin(3πt)e^{-4t}` → 0.5604, Elastic
`sin(4.5πt)e^{-2.5t}` → 0.7693, Bounce `|sin(3πt)|e^{-5t}` → 0.4973. Switching
Spring → Elastic multiplies the excursion by 1.37 before it changes any
character.

**4. A key on every frame** — up to 120 per channel (`:103`). That is a bake, not
animation; the graph editor cannot be used on the result. The analytic extremes
fall *between* frames as well, so the real peak is clipped by a
duration-dependent amount.

**5. Two outright bugs.**

- The layer weight steps to 1 at `global_last` = the **maximum** last-key time
  over all channels of the group (`:79-82`). A channel that ends earlier has its
  overshoot multiplied by weight 0 for part of its window and is silently
  suppressed. Only a rig where every channel ends on the same frame escapes.
- The final key is written twice (`:103` inside the loop, then `:108`), the second
  write flattening whatever the decay had left.

**6. The bounce has the rhythm of a metronome.** `|sin(3πt)|e^{-5t}` puts its
contacts at equal intervals. A ball's intervals shrink geometrically — the fall
time goes as `√h` — and equal spacing is the one thing that stops a bounce
reading as a bounce.

## The iteration that was rejected, and why it is written down

There is a real tension in this feature. An overshoot is the object *not
stopping*; but if the animator eased into the pose there is no momentum at the
pose to continue, and none can be invented — arriving at an eased pose on the
move's peak speed for even three frames means being **51 units of a 100-unit
move behind** where the animator put the object.

So a version was built that resolved the tension the other way: the pose key
became the extreme (`P + A`) and the pose became a settle target `N` frames
later. It is defensible, it is what a hand-animator often does, and the animator
rejected it on sight — *"работает совершенно не так как раньше и совсем не
правильно"*. The pose is a decision, and a tool that moves it is not building an
overshoot, it is editing the pose.

The tension therefore stands, and the tool takes the animator's side of it: the
excursion is written **after** the pose, and the discontinuity at the pose is the
price. What can be done — and is done — is to make that discontinuity mean
something: the curve leaves the pose at exactly the speed the move arrived with,
so it reads as the motion carrying through rather than as a fresh kick out of
nothing.

## Design

### Where the overshoot goes

Selected keys, else the current frame. Selected keys carry **both a time and a
channel**, so selecting only `translateY`'s key overshoots only Y, and selecting
a column of keys does a whole pose. With no key selection the tool takes the key
at — or the nearest one before — the current frame on every enabled channel. The
status line always names what it chose. The last key of the channel is no longer
special in any way.

### What one pose needs from the scene

The previous key `(T_prev, P_prev)`, the pose value `P`, and the next key time.
No curve sampling, no tangent reading, nothing that depends on frame rate.

- `Δ = P - P_prev`, `speed = |Δ| / (T - T_prev)` in units per frame.
- **No previous key, or `|Δ|` below epsilon: skip.** Nothing arrived.
- **The pose must be a stop.** If the next segment continues in the *same*
  direction, the key is a pass-through and an excursion there is a wobble in the
  middle of a move. Skipped, with the reason named. A reversal or a hold is a
  stop.
- `N` = Frames, clamped to `T_next - 1 - T`; under two frames there is no room
  and the channel is skipped.

### The shapes

Both families start at the pose (`f(0) = 0`), return to it (`f(1) = 0`), and are
normalized to **unit peak**, so a type button changes character and not size.

Damped sinusoid, `raw(u) = sin(π c u)·e^{-k u}`, `u = (t - T)/N`, `k = -c·ln r`.
`raw' = 0` gives `tan(πcu) = πc/k`, so the crests are at
`u_i = atan(πc/k)/(πc) + i/c` — one half period apart from the first — and being
`1/c` apart makes each crest exactly `r` times the last. With `k = 0` the first
crest is the quarter period, the undamped answer, so `r = 1` needs no special
case. `raw(1) = 0` exactly for integer `c`.

That is the whole implementation: the tool writes the pose key, one key per
crest, and the landing — **flat tangents on the crests, because a crest has zero
velocity and flat is correct rather than a compromise** — and Maya's cubic
between two flat keys does the rest. **4-8 editable keys** instead of a key on
every frame.

| Button | swings `c` | keep `r` | frames | what it reads as |
|---|---|---|---|---|
| **Snap** | 1 | 0.30 | 5 | out and straight back |
| **Spring** | 3 | 0.30 | 12 | out, back past, settle |
| **Elastic** | 6 | 0.60 | 16 | rubbery, many swings |
| **Recoil** | 2 | 0.15 | 8 | out, one small undershoot, dead |
| **Bounce** | arcs | `e` = 0.5 | 7 | a ball thrown off the pose |

Bounce is the same idea with gravity: the object leaves the pose at the move's
speed, is pulled back to it, bounces keeping `e` of its speed and so `e²` of its
height, and the arcs shorten by `e`. Apexes are flat, contacts get **linear**
tangents so the impact keeps its corner — auto tangents would round it into mush.

**`frames` belongs to the preset.** Leaving the pose at a fixed speed means the
excursion is set by how long the settle lasts, so one slow swing travels
furthest: at Spring's 12 frames, Snap's overshoot is three times Spring's. The
four lengths above put every preset in the same size range for the same move. A
type button therefore loads its whole preset into the panel and applies it, and
*Apply, keep my numbers* in Advanced re-runs the same shape with whatever the
animator has changed since.

### Amplitude, and the one number that ties it together

```
entry  = f'(0) of the unit-peak shape        (πc / peak for the sinusoid, 4/d for an arc)
A      = strength · speed · N / entry
slope  = A · entry / N  ==  strength · speed
```

So the amplitude is derived, and the thing held fixed is the **slope leaving the
pose**: at strength 1.0 the overshoot leaves at exactly the speed the move had.
That is the design in one line, and it is what gate 2 measures. Strength is a
multiplier on it; the resulting peak is reported in the status line, and an
excursion wider than twice the move is clamped and said so.

### The pose key's tangent, without guessing Maya's units

The slope only exists if the pose key's out-tangent is set to it, and Maya's
`keyTangent -outAngle` is in degrees against an internal time unit that is not
the scene's frame. Rather than guess: a **linear** out-tangent aims at the next
key, whose secant we know exactly, so setting linear and querying the angle
calibrates the scale for that very curve, and the wanted angle follows
(`set_out_slope`). No temp nodes, no assumption, right at any frame rate. The
in-tangent is flat, since the offset before the pose is zero. If the calibration
ever fails, the fallback is a plain linear out-tangent — about half the intended
slope, which is a soft failure rather than a wrong one, and the verify script
recognises both failure modes by number.

### Where the keys go

An **additive** anim layer per object per channel group: `<obj>_overshoot_pos`,
`<obj>_overshoot_rot`. Additive rather than override removes the whole weight
mechanism and bug 5 with it: a layer with no keys is zero offset, so the base
passes through untouched everywhere outside the windows, with nothing to step and
nothing to gate. The layer's **weight is a live strength dial**.

Re-applying clears only the window it is about to write, so other poses' work
survives; the old tool deleted the whole layer and any hand tweak in it. Windows
never overlap — each is clamped to end before the next key — and where two poses
share a frame the pose key itself is never overwritten, since the whole point is
that the pose does not move.

A *Bake into curves* checkbox writes the same plan into the base curves instead
(the key list is identical modulo `P`). That path needs no anim-layer semantics
at all, which is why both exist.

The whole apply is one undo chunk, with autoKey off around the writes (trap 14).

### UI

Translate and Rotate checkboxes, per-group **Strength** and **Frames**, five type
buttons. Swings, Keep, Bounce `e`, *Bake into curves* and *Apply, keep my
numbers* in a collapsed Advanced section. `show_overshoot_ui()` sits behind
`if __name__ == "__main__"` so pasting the file into the Script Editor still
opens the window while importing it (tests) does not. Every callback goes through
`_run`, which puts the failure on the status line instead of the Script Editor
(trap 20).

## The one unverified Maya semantic

Does `cmds.setKeyframe(obj, at=attr, t=, v=, animLayer=L)` write `v` as the
**offset** on an additive layer's curve, or does it try to reach `v` as a final
value? Gate 1 answers it: the pose reading 100 is an offset, the pose reading 0 is
an absolute. If it is the latter, write through
`animLayer(L, q=True, findCurveForPlug=plug)` instead.

How an additive layer accumulates euler offsets is **not** configurable — Maya
2027 has no `-rotationAccumulationMode` flag at all (trap 41) — so gate 12c
measures the combined channel instead of setting a mode.

## Verification

`docs/superpowers/plans/verify_overshoot.py`, in a sandbox, through the command
port. The gates:

1. **The pose key keeps its value.** The claim the whole concept rests on.
2. **The curve leaves the pose at the speed of the move** (and at
   `strength × speed` for other strengths). Also the proof that the tangent
   calibration works: flat means it did not take, half means it fell back to
   linear.
3. The peak is `speed·N/entry`, lands where the shape says, and the settle
   returns to the pose exactly, with as many turning points as swings.
4. Nothing outside `[T, T+N]` changes, to 1e-9.
5. The next key is untouched; a nearby hold shortens the settle instead of
   running over it.
6. A pass-through key is refused, and the report says why.
7. At most six keys per channel per pose.
8. Applying twice changes nothing.
9. Strength scales the excursion and the exit speed; layer weight scales the
   result.
10. Deleting the layer restores the animation exactly.
11. Bounce stays on one side of the pose, its arcs shorten, and it launches at
    the move's speed too.
12. Rotation lands in its own layer, leaves the pose angle alone, adds per euler
    channel at the planned size, and comes off cleanly.
13. The bake-into-curves path does all of the above with no layer in the scene.

Pure-function unit tests (`tests/test_overshoot.py`, 68 of them) cover the
shapes against their closed forms, the crest spacing and geometric ratio, the arc
series, the entry-slope identity, every refusal, the clamping, and — as its own
test class — that the pose key comes out at offset zero for every shape, length
and strength.

## Accepted limits

- **The discontinuity at the pose is inherent to the concept**, not a bug: the
  base arrives eased and the overshoot leaves at speed. Making it continuous
  requires moving the pose, which is the rejected iteration above.
- **Rotation is overshot per euler channel**, in the direction of the euler delta
  that arrived. For the excursions this tool makes that is the axis the animator
  moved; for a large multi-axis move near gimbal it is approximate. Doing it
  properly means a quaternion delta about the incoming rotation axis converted
  back to euler per frame — dense keys and a rotate-order dependency, for a gain
  nobody will see.
- Keys written past the end of the playback range are reported, not clamped, and
  the range is never changed — the clip length is the animator's decision.

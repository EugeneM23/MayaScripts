# Interface look and motion: the Time Bar's style is the rule

The animator, 2026-10-18: «Давай составим правила и требования к анимациям интерфейса в
нашем проекте. Я хочу что бы мы всегда делали интерфейс в стиле в котором у нас сейчас
сделан тайм слайдер».

**Every new piece of interface, and every piece reworked, looks and moves like the Time
Bar.** This file is about the look and the animation only. It gives the numbers, how to
build it, and how to prove it. When a request and this file disagree, the request wins,
and this file is updated in the same change.

**The reference implementation** is `SkeldarAnim/maya_timebar/`:

| file | what it holds |
|---|---|
| `look.py` | stdlib: every number and curve, as pure functions of time |
| `bar.py` | Qt: the painted controls, the effects overlay, the one animation driver |

The side panel (`maya_sidepanel/`) is the second implementation and already imports
the Time Bar's numbers. Spec of the original:
`docs/superpowers/specs/2026-10-16-time-bar-design.md`.

## Scope

- **A surface of our own** (a strip, a panel, an overlay, a grid, a popup, a menu, an
  effect over the viewport) is **painted** the Time Bar's way: painted controls, the
  effects overlay, the burst, and everything below.
- **A hub card** keeps Maya's `cmds` controls inside the hub skin, so its builders and
  hotkey rows keep working (`maya_hubqt`). The skin already gives those controls the
  hub's glow and slide. What a card **adds** on top follows this file: its own painted
  widgets and its effects.
- **Older motion stays as tuned.** Each of these was tuned with the animator, and is
  changed only when the animator asks:
  - the hub cards' slide and light (`maya_hubmotion`);
  - the controls' ink glow (`maya_hubglow`);
  - the windows' spring (2026-10-22, the animator's pick of four mockups: the whole window
    grows out of the point on a damped spring and fades in, one picture drawn scaled -
    `maya_hubburst.MOTION`; the 2026-10-18 burst is kept as `"burst"`);
  - the radial menu (`maya_radial_rules`).

  All of them are already the same family: a back ease, nearest first, accent light.

## 1. The principles

1. **Motion has a centre.** A panel opens out of a point and closes back into it. The
   part nearest that point arrives first, the farthest leaves first.
2. **Every part moves on its own.** A panel's controls pop in one by one in a wave,
   never as one slab. A deleted key breaks into its own pieces.
3. **Motion is a response, never ambient.**
   - A control's states move: hover lifts and lights, a press flashes, a toggle pops.
   - An event moves: a key set flashes, a key the playhead reaches lights up, Play
     frames the timeline.
   - Nothing breathes, pulses or loops at rest.
4. **Light is added, never painted over.** Glows are drawn as added light
   (`CompositionMode_Plus`) or as rings fading outward. What is under a flash brightens;
   it is not covered.
5. **An effect happens where its thing is, and is made of that thing.** The flash is on
   the key that was set. A deleted key's pieces are that key: together they ARE the key
   at age 0.
6. **The data is instant; the picture catches up.** A deleted key is gone from the data
   at once. Its picture (a "ghost") waits for its turn in the wave, then breaks. An
   animation never delays a command, a key, an undo step or a refresh.
7. **Short.**
   - A control's state change: 110-200 ms.
   - A whole panel bursting out: about half a second.
   - An effect: at most 0.8 s.
   - A wave of many elements: its last element starts within 0.5 s, however many there
     are.
8. **It costs the animator nothing.** Our share of a frame stays under about 1 ms on a
   dense take. Maya's work comes first, and playback is never slowed.
9. **One switch turns it all off.** With ⋮ → Interface animations off
   (`maya_hubmotion.enabled()`), every motion lands at its end state at once. No effect
   is even created, and the result is the same as with the motion on.

## 2. The look

- **Colours only from `maya_hubstyle.TOKENS`:** `panel`, `card`, `field`, `track`,
  `track_edge`, `line`, `hover`, `text` / `muted` / `faint`, `accent` `#e07a36`,
  `accent_hover`, `accent_text`, `on_accent`, `accent_tint`.
  - Light's hot core is the Time Bar's `RIM` `#fff1e2`.
  - Other colours only where they mean something: breakdown cyan `#6fb7c9`, highlight
    blue `#7fa9e6`, record red `#e0524a`.
- **One orange per row:** the primary action (the Time Bar's Play) has an accent face,
  and every other control is plain.
- **Shapes:**
  - a control 24 logical px tall with a 5 px margin around it (room for its lift);
  - a rounded rectangle of radius 5, a chip fully round;
  - a track radius 6, with `track` and a 1 px `track_edge`.
- **Glyphs** are 16 x 16 SVG paths drawn in the control's ink colour (`GLYPHS`, QtSvg).
- **Text:** 12 logical px; numbers in Consolas.
- **Every length is logical × the display scale** (`ui`). Qt stylesheet pixels are
  physical (trap 98).

## 3. The motion vocabulary

Times in ms. The constants live in `maya_timebar/look.py` and `bar.py`; **new work
imports them** (as `maya_sidepanel/look.py` does: `UNROLL_MS = _bar.UNROLL_MS`) rather
than copying them.

**The curves:**

| curve | formula | used for |
|---|---|---|
| `back_out` | c = 1.70158; overshoots about 10 %, lands on 1 | a part popping in, a toggle's pop, a flash's halo growing |
| `back_in` | draws back a little, then goes | a part folding away |
| `ease_out_quint` | 1 - (1 - u)^5 | a panel unrolling, the Play frame closing in |
| `ease_in_quint` | u^5 | a panel closing |
| `approach` | value += (goal - value)(1 - e^(-3 dt / ms)), snapped within 0.005 | any state that can turn back half way (hover, a key's lift) |
| linear 1 → 0 | | a press flash |
| (1 - u)^2, (1 - u)^1.5 | | light fading (a reached key, a set key's flash) |

**A control's states:**

| state | numbers |
|---|---|
| hover | `HOVER_MS` 110 by `approach`. Scale +`LIFT` 10 %. The face goes to `hover`. Ink goes `muted` → `text`. The glow: four rings 1.6 px apart, alpha 46·level·(5-i)/4, then a 2 px edge, in `accent` (`RIM` on the orange button) |
| press | `FLASH_MS` 120, linear. The face goes to `accent`, scale -6 %, ink `on_accent` past half way |
| toggle | `POP_MS` 200; scale 0.7 + 0.3·back_out |
| a key lifted | grows `KEY_LIFT` 60 % by `approach`, with a cached halo |

**A panel coming and going** (every timing is the mockup's × `BURST_SLOW` 1.2):

| moment | numbers |
|---|---|
| the shape unrolls from its point | `UNROLL_MS` 288, ease_out_quint, by the host's mask |
| each part pops in | `POP_OPEN_MS` 240, scale `START_SCALE` 0.3 → 1 by back_out, opacity ×1.6. It starts at `burst_delay`: 48 ms + 21.6 ms per 60 logical px from the point (a vertical step counts 1.5). Nearest first |
| the reveal's light | `REVEAL_MS` 780. The two unrolling edges carry the light (`EDGE_GLOW` 24, core `EDGE_CORE` 3), fading as (1 - ease_out_quint)^0.55. The top edge stays lit (`TOP_GLOW` 16), fading as (1 - t)^1.6 |
| each part folds | `FOLD_MS` 168 by back_in to 0.3, the opacity going too. It starts at `fold_delay`: 216 ms less 14.4 ms per 60 px. Farthest first |
| the shape closes onto its point | `CLOSE_MS` 216, ease_in_quint, `CLOSE_AFTER_MS` 72 after the last fold |
| a first show with no point | `opening`: 200 ms a part, 18 ms apart in their order |
| Maya's widgets inside (too heavy to move per frame) | a PICTURE of the panel is moved instead, in rows of 44 logical px (the side panel) |

**Events:**

| moment | numbers |
|---|---|
| a key the playhead reaches | lit at once, fades over `KEY_FADE_MS` 600 as (1 - u)^2. Only the keys it swept over or landed on |
| the cell the playhead left | glows at `TRAIL_ALPHA` 0.28 of the accent and fades over 380 |
| Play | an accent frame closes in round the timeline over 420 (ease_out_quint inset, line from 3.5 px to 1) |
| a key set (also over a key that stood) | 520. A round halo `SET_GLOW` 44 logical px, laid twice, growing 0.6 + 0.4·back_out over the first 40 %, fading (1 - u)^1.5. A 13 px `RIM` core fading (1 - u)^2. Added light |
| a key deleted | 700. The key breaks into 3-5 uneven pieces stacked down it. They part left and right, are kicked up (`SHARD_SPEED` 170 px/s), spin (`SHARD_SPIN` 420 °/s), fall (`SHARD_FALL` 900 px/s²) and fade over the last half |
| many keys deleted | a wave left to right. Every key flies exactly as a single key does; only the starts are staggered, `DELETE_STEP_MS` 80 apart, squeezed so the last starts by `DELETE_START_MS` 500. Past `SHARD_BUDGET` 900 pieces, neighbours break as one block. Each key stays drawn until its turn |

## 4. How to build it

1. **Numbers and curves in a stdlib-only module.** Make them pure functions of age:
   `f(age_ms, delay, ...) -> (scale, opacity)`. A subprocess test pins that the module
   imports no Maya and no Qt. Record each value the animator chose next to it, with
   their words and the date.
2. **Everything is drawn from its age alone.**
   - The age is `clock() - t0 - delay`.
   - Randomness is seeded from the effect's own seed.
   - No state is stepped frame by frame, so a paint at any moment shows the right
     frame, a dropped frame changes nothing, and a test can render any instant.
   - The only stepped values are `approach` states (hover, lift), which are meant to
     turn back half way.
3. **One driver per surface.**
   - It is one QTimer at `FRAME_MS` 16, started by `kick()`.
   - Each moving part answers `busy(now)`.
   - A part repaints while it is busy, plus one paint after (`_was_busy`).
   - The timer stops itself when nothing is busy. **No timer runs at rest**; a slow
     poll for the scene (250 ms) is not an animation.
4. **We paint our own controls.**
   - A control is a painted `QAbstractButton` subclass (the Time Bar's `Pill`). It
     scales, glows and flashes in its own `paintEvent`.
   - A Qt or Maya widget we do not paint (a field, a divider) fades through a
     `QGraphicsOpacityEffect` that we HOLD (trap 201) and disable at rest (trap 204).
5. **Effects go on an overlay.**
   - The overlay is a child over the whole surface.
   - It paints only while an effect lives, and is clipped by the host's mask like
     everything else.
   - It is raised over the surface when an effect starts.
6. **What does not move is one cached picture.**
   - The still part is drawn into a `QPixmap` and drawn again only when its key changes
     (`_static_key`: size, view, ranges, data, scale).
   - Each frame draws the picture and the moving parts over it.
   - Many like shapes go into one `QPainterPath`; a repeated glow is a sprite drawn
     once per colour and size (`halo`).
   - Never draw element by element in Python per frame (trap 271): a test pins that a
     scrub rebuilds no picture.
7. **A panel moves under a mask; its layout never runs per frame.**
   - The host window stays put; the strip slides inside it, or the mask unrolls.
   - Where a panel holds Maya's own widgets, a picture of it moves instead.
   - That picture comes from DWM (`PrintWindow`), never `widget.grab()` (trap 134).
8. **Playback turns no event loop and no timer.**
   - Anything that must follow time paints with `repaint()` inside the time callback,
     not `update()` (trap 269).
   - It listens through OpenMaya callbacks, not scriptJobs (trap 277).
   - An animation that must run during playback is stepped from the time callback
     itself (`BottomEdge.step`).
9. **⋮ → Interface animations off is a branch everywhere.**
   - Read it through one seam (`animations_on()`).
   - With it off: every curve answers its end state, no effect is added, no timer
     starts.
   - The final picture must be the same as with motion on.
10. **Never keep a wrapper of Maya's widgets** (trap 135): find them again when needed.
    Never `grab()` them.
11. **A paint that raises prints its traceback once and stops** (`_failed`), never a
    loop of tracebacks. A driver that raises stops its timer. A failed effect draws the
    plain control for good (`broken`).

## 5. The budget

Measured on the Time Bar (`docs/superpowers/plans/bench_time_bar.py`, a key on every one
of 300 frames, 150 %):

| cost | budget |
|---|---|
| a scrub step | 0.97 ms |
| a tick of the key fade | 0.5 ms |
| a paint | 0.06 ms |
| our share of a playback frame while the bar shows | 0.3-0.5 ms |
| our share while it is hidden | nothing |
| a frame of the worst wave (1000 keys deleted) | ≤ 10 ms; `SHARD_BUDGET` exists for this |

A new surface keeps the same order. Measure it with a bench of its own before claiming
it is smooth. If the animator says it lags, measure in their scene: the Time Bar's key
menu has «Measure scrubbing (10 s)».

## 6. How it is proven

1. **The curves**, by unit tests:
   - monotone where they should be;
   - exact at both ends;
   - the wave's last start within its cap;
   - the off switch giving the end state;
   - seeded effects reading the same at the same age.
2. **The surface offscreen** (`QT_QPA_PLATFORM=offscreen`), on a fake link to Maya:
   - painted at chosen instants;
   - pixels sampled (ink grows from nothing, a lit part draws more, a far pixel stays
     empty);
   - no picture rebuilt during a scrub.
3. **A filmstrip** rendered by a script into a PNG beside it, e.g.
   `render_time_bar_burst.py` → `time_bar_burst.png`, `render_time_bar_reveal_glow.py`.
4. **The speed**, by a bench (section 5).
5. **In a GUI Maya**, only if the animator says so (they keep the live checks since
   2026-10-09). Otherwise the summary says plainly: «not seen in a GUI Maya».

## 7. How a new piece of motion is made

1. **A live mockup first.**
   - Make an HTML artifact with the real tokens at the real size: the Time Bar's 84 px
     strip, the 360 px dock.
   - Show the variants side by side, moving.
   - The animator picks: the reveal glow was B of five, the shard flight B of six.
2. **The pick's numbers go into the look module**, with the animator's words. A later
   "faster / slower / stronger" changes a named constant (e.g. `BURST_SLOW`), never a
   scatter of literals.
3. **Build it** with section 4, prove it with section 6, say how it was proven in the
   CLAUDE.md section and the spec.

## 8. Checklist

Copy it into the spec of anything that moves.

- [ ] A panel opens out of its point and closes into it: in nearest first, out farthest
      first.
- [ ] Every part moves on its own (a wave), within the durations of section 3.
- [ ] Hover 110 + 10 % + glow; press flash 120; toggle pop 200.
- [ ] Effects are added light, where their thing is, made of that thing.
- [ ] The data changes at once; only the picture is animated.
- [ ] Colours from `TOKENS` only; one orange per row; lengths × `ui`.
- [ ] Numbers in a stdlib module, imported from `maya_timebar.look` where they exist.
- [ ] Drawn from age; one 16 ms driver that stops at rest; the still part cached.
- [ ] Effects on an overlay; opacity effects held and disabled at rest.
- [ ] Playback: `repaint()` in the time callback, OpenMaya callbacks, stepped from the
      callback.
- [ ] Interface animations off: the same end state at once, nothing created.
- [ ] A paint error prints once; no Maya wrapper kept; no `grab()`.
- [ ] Measured against section 5.
- [ ] Unit tests + offscreen pixels + a filmstrip; «not seen in a GUI Maya» if it was
      not.

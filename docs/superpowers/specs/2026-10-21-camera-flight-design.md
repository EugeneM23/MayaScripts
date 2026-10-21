# Camera flight: the Space menu flies between cameras (2026-10-21)

The animator: «а возможно ли реализовать переключение между камерами при использование нашего
меню не мгновенное а с анимацией? Например мы находимся в камере персонажа и нажимаем на
переход в камеру перспективы скрипт создает подмену камеры и анимирует 0.3 сек полет от камеры
персонажа в перспективу».

Asked, both the recommendation:
- **ortho views flatten smoothly**: on the way into Top / Side / Front the substitute pulls back
  and narrows its angle until the picture is flat, then the cut; out of one, the reverse;
- **the flight orbits the subject**: it turns about the point each camera looks at, so what is
  looked at stays in frame.

## What it is

Space's camera menu (`maya_camradial`) no longer switches the viewport at once. Letting go on a
camera puts a **substitute camera** in the panel, standing exactly as the panel's view stood; it
flies 0.3 s (eased in and out) to stand exactly as the chosen camera, then the panel looks
through the chosen camera and the substitute is deleted. Since the substitute's last frame is the
target's frame, the cut is invisible.

Instant, as before:
- ⋮ → Interface animations off (`maya_hubmotion.enabled()`);
- the panel looks through something that is not a camera;
- the chosen camera is the one already shown;
- anything fails on the way: the panel is switched at once, the substitute removed.

## The view of a camera (pure, `maya_camflight_rules`)

A camera's view, read for the panel's aspect (`MFnCamera.getViewingFrustum(aspect, overscan,
squeeze, panZoom)`, which gives the frame the viewport actually shows, film fit, overscan and
film offset included):

| field | perspective | orthographic |
|---|---|---|
| `pivot` | position + forward × centre of interest | the same |
| `rot` | the world rotation, a quaternion (scale dropped) | the same |
| `half` | the frame's half height at the pivot: coi × tan | the ortho frame's half height |
| `tan` | tan of the vertical half angle (frustum top / near) | `TAN_FLAT` = tan 0.1° |
| `ox`, `oy` | the frame's centre off the axis, in half heights | the same |
| `near_rel`, `far_rel` | the clip planes from the pivot (clip − coi) | the same |
| `floor` | its near clip | none |

An ortho view is the perspective view that looks the same at the pivot with an angle of 0.1°: a
point 100 cm off the pivot's depth differs in size by under 0.2 % when the cut comes.

## The flight

At eased time `u` (`ease_in_out`, cubic), between views `a` and `b`:
- `pivot` lerp; `rot` slerp (the shorter way); `half` lerp in log space; `tan`, `ox`, `oy`,
  `near_rel`, `far_rel` lerp;
- the distance `d = half / tan`; the position `pivot − forward × d` - the pivot always stands
  on the substitute's axis (the frame's centre, but for a film offset), so the subject stays in
  frame;
- the near clip `max(floor, d + near_rel)` (`floor` the perspective ends' near clip, lerped when
  both are perspective), the far clip `max(2 × near, d + far_rel)`: an ortho end keeps its own
  depth range about the pivot;
- `tan` is lerped linearly: the perspective's strength is linear in it, so flattening reads even.

At `u` 0 and 1 the substitute IS the end's frame (a perspective end exactly).

**The substitute's lens**: film aperture with the viewport's aspect (vertical 1 in, horizontal ×
aspect), film fit Vertical, overscan 1, focal `12.7 / tan` mm (the aperture grown when that would
fall under Maya's 2.5 mm), film offset `ox, oy` × half the aperture. Measured in mayapy: a
substitute built from Camera Setup's lens (16:9, fitted horizontally, overscan 1.3, a film offset)
gives back its frustum to 2e-6.

## The scene half (`maya_camflight`)

- `fly(panel, target)` → True when a flight took the switch over, False when the caller switches
  at once. `maya_camradial.look_through` calls it.
- **Live ends**: both cameras are read again every tick, so an animated camera (the character's,
  during playback) is followed. A flight started while another runs in the same panel starts from
  where the substitute stands (frozen), on the same substitute.
- One flight per panel; the driver is a 16 ms Qt timer while a flight runs, plus a time-change
  callback (`MDGMessage.addTimeChangeCallback`) - playback turns no timer (trap 269). Time is the
  wall clock, so a slow viewport shortens the frames, never lengthens the flight.
- **The substitute** `:skeldarCameraFlight` (the root namespace, outside every scene tab), marked
  `skeldarCameraFlight`, hidden in the Outliner, not renderable. Made, moved and deleted with the
  undo queue off (no step on it) and through the API per tick (no autoKey); the scene's modified
  flag is put back when the last flight ends if it was clean when the first began. The first
  flight sweeps away a substitute a crash or a mid-flight save left in the scene.
- The panel is redrawn every tick (`M3dView.refresh(False, True)` on its own view).
- The Space menu leaves the substitute out of its list and marks the flight's target as the
  camera looked through.

## Proof

- `tests/test_camflight_rules.py`: the views, both ends exact, the pivot at the frame centre
  mid-flight, the ortho end's frame at the pivot, slerp the short way, the lens limits, the clips,
  stdlib only.
- `tests/test_camflight.py`: the flight on a fake backend and clock - instant when off, a flight
  that ends on the target with the substitute gone, live ends, chaining, a failure switching at
  once, the modified flag.
- `docs/superpowers/plans/verify_camera_flight.py` (mayapy standalone, the panel faked), **28/28**:
  27 points about the subject projected through the substitute against each end (persp, a Camera
  Setup-like lens, top) at u 0 / 1 (8.8e-7, 1.9e-6), the pivot on the axis mid-flight, the ortho
  cut at 0.1 % of the frame, chaining, no node left, no undo step, the modified flag kept, the time
  callback driving it, a stale substitute swept.
- Not seen in a GUI Maya: the flight on screen, during playback.

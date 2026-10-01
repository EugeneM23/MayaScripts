# Viewport Studio: a third look, Soft Studio, on a warm cyclorama

2026-10-01. The animator: «давай реализуем еще одну схему студийного освещения где свет будет
распределен в 3 раза более широким пятном. И в целом давай сделаем какие-то приятные теплые цвета для
подложки заднего фона (ее нужно сделать). Само освещение хочу тоже более приятное спереди теплый свет с
зади холодный». Asked, and answered:

- the backdrop is a **photo-studio cyclorama**: real geometry, the floor sweeping up into a wall
  behind the character with no corner and no horizon;
- **only the new look** gets it. Studio and Outdoor stay exactly as they are.

Built on `maya_vpstudio` (spec `2026-09-03-viewport-studio-design.md`); a look is a row in `LOOKS`.

## The look

`LOOKS["Soft Studio"]`, third in the dropdown (`LOOK_ORDER` = Studio, Outdoor, Soft Studio; Studio stays
the default).

**Lights** (`SOFT_LIGHTS`, in subject radii and degrees from the camera's heading, as every look):

| light | kind | az | el | dist | intensity | colour | shadow | specular | cover |
|---|---|---|---|---|---|---|---|---|---|
| key | spot | 35 | 30 | 2.6 | 1.25 | warm (1.00, 0.84, 0.64) | yes | yes | 5.1 |
| fill | directional | -55 | 12 | 2.9 | 0.28 | warm (1.00, 0.88, 0.74) | | | |
| rim | spot | 160 | 38 | 2.8 | 2.60 | cold (0.50, 0.68, 1.00) | | yes | 4.5 |
| kicker | spot | -150 | 22 | 2.8 | 1.70 | cold (0.55, 0.72, 1.00) | | yes | 4.5 |
| bounce | directional | -20 | -18 | 2.2 | 0.14 | warm (0.95, 0.80, 0.66) | | | |
| ambient | ambient | 0 | 70 | 3.0 | 0.10 | neutral (0.74, 0.71, 0.70) | | | |

- **"Three times wider"** is the spot's POOL on the subject: `cover` is the cone's half-width in radii
  at the light's distance, so Studio's key 1.7 and rim 1.5 become 5.1 and 4.5. At the same distance the
  cone's `tan(half)` is exactly three times Studio's (a test pins it): the key's cone is 126° against
  66°, the rim's 116° against 56°.
- **The falloff widens with it.** Maya's dropoff weighs a spot by `cos(θ)^dropoff`. At Studio's 6 the
  pool would still end at Studio's size, because a 126° cone at dropoff 6 is dark past 40°. A look now
  carries `spot` = {penumbra, dropoff}: Studio and Outdoor 14 / 6 as before; Soft Studio 20 / 1.3,
  which keeps the wide pool's edge as bright, relative to its centre, as Studio's: cos(63°)^1.3 = 0.36 against cos(33.2°)^6 = 0.34

- **Warm in front, cold behind.** The key, fill and bounce face the camera's side; the rim and a second
  cold back light, the kicker, stand behind the subject on either side. Six lights, within the eight
  `maxHardwareLights` allows. One shadow caster, as in every look.
- **The shadow** is wider and softer: a 126° cone spreads its depth map three times as thin, so the
  look asks for twice the quality's map (`dmap_scale` 2, at most 4096) and a softer filter
  (`shadow_filter` 6).

## The cyclorama

`cyclorama_plan(frame, azimuth, options)` (pure) and `_make_cyclorama(plan)`. When the Floor option is
on and the look's floor is a cyclorama, it is built **in place of** the flat floor. Its surface is the
shadow catcher.

- **Profile in subject radii**, in the cyclorama's own frame (+Z toward the camera, the wall at −Z),
  across `±12 r` in X:
  - the floor from `z = +12 r` to `z = −3.0 r`;
  - a quarter-circle cove of radius `1.5 r` (16 segments);
  - a vertical wall at `z = −4.5 r` up to `y = 8 r`.

  The cove starts behind every light: the furthest back light stands 2.6 r out horizontally, and the
  Rotate dial can turn it straight back. So no light ever ends up behind the paper.
- **Placed by the camera**, like the lights: the node stands under the subject's centre, a hair below
  the feet (the floor's own offset), turned `rotateY = azimuth`. So the wall is behind the character as
  seen from where the animator looked when they pressed Apply.
- **The Rotate dial turns the lights, not the backdrop.** The cyclorama hangs under the group, not
  under the light pivot: a dial that spun the paper away from behind the subject would defeat it.
- **Geometry**: a `polyPlane` (1 × N, no history), each vertex moved onto the profile by its own
  starting position, never by index; edges softened (`polySoftEdge 180` — a fresh polyPlane's edges are
  hard, measured), so the cove shades as one surface. Normals face the subject.
- **Dressing** as the floor's: a blinn, receives shadows, casts none, double-sided, reference display.
  Its colour is a warm sand-caramel, matte (specular 0.02). The flat floor and the cyclorama share one
  dresser (`_dress_catcher`).
- **The viewport behind it** (the look's `backdrop`) is a warm dark gradient, so the cyclorama's edges
  never meet Studio's cold grey. The look's `fog` colour is warm too (a look now carries `fog`; the
  others keep the old blue-grey).

## Unchanged

Studio and Outdoor (their lights, floor, sky, numbers), retune, restore, the capture, the index, the
panel's controls. The Backdrop check is relabelled from «Dark backdrop» to «Backdrop», since one look's
backdrop is now warm. The status line names the cyclorama in place of the floor.

## Proof

- Unit tests: the look's shape (six lights, one caster, warm front, cold back), the 3× pool, the
  falloff, the cyclorama profile (continuous, the floor under the feet, the wall behind every light,
  normals facing the subject), the dresser shared.
- `verify_vpstudio_soft.py` in a disposable GUI Maya on a textured Manny: the six lights, the cones,
  the cyclorama behind the subject from the camera, its shading flags, the Rotate dial moving the lights
  and not the paper, Studio ⇄ Soft Studio leaving nothing behind, Restore, the frame time, and
  playblasts to look at.

## Addendum — what the live run changed (2026-10-01)

- **Every light threw a shadow, in every look.** The first Soft Studio playblast showed extra
  silhouettes: up the wall from the low bounce, sideways from the fill, toward the camera from the back
  lights. Measured by switching the lights off one at a time: Maya's `spotLight` / `directionalLight`
  / `ambientLight` commands make a light with `useRayTraceShadows` ON, Viewport 2.0 draws those, and
  `_make_light` only ever turned depth-map shadows off. Studio's long streak to the right was the fill's.
  `_make_light` now turns ray-traced shadows off on every light, the caster included; its shadow is the
  depth map. **Studio and Outdoor change by exactly that**: one shadow each, as their table always
  said. The wide 126° cone itself was never the problem, and a spot opened past 90° shadows cleanly.
- **The back lights outshine the key.** At Studio-like strengths (rim 1.25, kicker 0.75, fill 0.40)
  the warm front flooded the edges and nothing read cold. Now rim 2.6 and kicker 1.7, cooler
  (0.50, 0.68, 1.00) / (0.55, 0.72, 1.00), fill 0.28. They cool the floor around the subject to a pale
  neutral, and the wall, facing away from them, stays warm. Light-linking them off the paper was tried:
  Viewport 2.0 then dropped the rim from the character as well, so it is not used.
- The fill stands at 2.9 radii, inside the cove's 3.0.

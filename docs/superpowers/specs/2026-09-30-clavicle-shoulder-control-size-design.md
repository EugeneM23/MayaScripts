# The clavicle and shoulder controls sized for the body — design

2026-09-30. The animator: «Давай теперь отредактируем размеры всех контроллеров у орка и у крипа. Сейчас
некоторые контроллеры не видно они в нутри шеометрии», then, narrowed: «У орка и крипа контролы ключиц
плечей не видны они внутри шеометрии тела». Asked how: **grow them to fit the body** (over drawing them on
top of the geometry, or both).

## Measured first

- AdvancedSkeleton draws every rig's controls at the same sizes. The Creep's and the Orc D's `FKShoulder_*`
  ring is Manny's to the CV (radius 12.5503 cm about its origin), and their `FKScapula_*` fin is AS's default
  (9.2476 cm) where Manny's is 12.3966. Their bodies are bulkier than Manny's at the neck and shoulders, so
  the drawings are buried.
- **Seen** = for each point of the curve (64 per shape), the share of 32 directions (a Fibonacci sphere)
  along which a ray reaches open space without meeting the character's own visible meshes. It needs no
  inside/outside test, so open or overlapping meshes do not fool it. An earlier ray-parity test did: the
  Creep's five overlapping meshes gave 0.69 or 0.95 "inside" depending on the ray directions.
- Seen, now:

  | | Manny (standard) | Creep | Orc D |
  |---|---|---|---|
  | FKScapula | 0.251 / 0.252 | 0.003 / 0.000 | 0.000 / 0.000 |
  | FKShoulder | 0.466 / 0.478 | 0.282 / 0.320 | 0.078 / 0.066 |

## The rule

The drawing grows uniformly about the control's origin (its pivot, checked), in its own object space. It
grows by the smallest factor on a 0.05 grid at which both sides are seen at least as well as Manny's pair,
and L and R take the same factor so the rig stays symmetric. `measure_control_sizes.py` finds the factors:

| | FKScapula | FKShoulder |
|---|---|---|
| Creep | ×1.75 → radius 16.183303 | ×1.65 → 20.707995 |
| Orc D | ×1.75 → 16.183303 | ×1.80 → 22.590540 |

Manny is the standard and stays as he is. Nothing but the drawing changes: no transform, pivot, axis or
connection, so no animation or retarget can see it.

## Where it lands

- **The shipped files, as text** (`make_control_sizes.py`, stdlib): the CV lines of the four shapes' `.cc`
  in `Creep_Rig.ma`, `Orc_D_Rig.ma` and `sources/orc/Orc_Rig.ma` (what the Orc D is built from), scaled to
  the table's radii. Everything else in each file is checked to be unchanged. It is idempotent: a shape at
  its radius is left alone.
- **The build**: `as_creep_rig_procedure.control_sizes()` does the same to a freshly built rig
  (`CONTROL_RADII`, the Creep's; `rebuild_orc_rig.py` sets the Orc's). It runs after `mark()` and
  `main_size()`.
- A catalog test pins the four radii on each file and the L/R equality.

A rig already in a scene keeps its small drawings; re-add it.

## Proof

`verify_control_sizes.py`, mayapy standalone: the old assets as the control (seen below Manny's), the three
rigs added side by side from the new ones, every one of the eight controls seen at least as well as Manny's
same control, L = R, only the curves changed, the controls still turning their bones. And viewport
playblasts of the shoulders before and after, from a disposable GUI Maya.

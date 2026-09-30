# Main at Manny's size on every rig — design

2026-09-30. The animator: «Давай сделаем размер главного контрола у всех ригов такой же как и у
menny сейчас он ну них меньше значительно».

## Measured first

- `Main` (the rig's whole-character control, root motion) is an identity transform in all three
  shipped rigs — `Manny_Rig.ma`, `Creep_Rig.ma`, `Orc_D_Rig.ma` — and in `sources/orc/Orc_Rig.ma`,
  which the Orc D is built from. Its shape `MainShape` is a periodic cubic circle (3 8 2, 11 CVs) on
  the floor, wired to nothing but `MotionSystem.v` and `AllSet`.
- **Manny's circle has a radius of 40.5236 cm; the Creep's and the Orc's 7.7574 cm** — the same curve,
  every CV exactly 5.223893× smaller: AdvancedSkeleton's default drawing, which the Creep procedure's
  build keeps, lost inside the feet of a 180–190 cm character. Manny's rig was built through
  AdvancedSkeleton's own UI, which drew it larger.
- The feet of all three stand where Manny's do (the Creep and the Orc have Manny's legs), so the same
  absolute circle is the right size on each — the literal ask.

## What changes

- **The shipped files, as text** (`docs/superpowers/plans/make_main_control_size.py`, stdlib): the 11
  CV lines of MainShape's `.cc` replaced with Manny's, and nothing else — the curve's header must
  already be Manny's, and the result is checked to differ from the original in those lines only.
  Idempotent. No open-and-resave (traps 121–122).
- **The build**: `as_creep_rig_procedure.main_size()` scales Main's CVs in its own space to
  `MAIN_RADIUS` (Manny's), after `mark()` — in `run()`, `rebuild_creep_rig.py` and
  `rebuild_orc_rig.py` — so a rebuilt Creep or Orc needs no second pass.
- A catalog test pins every rig row's Main (and the Orc source's) to Manny's CVs, and Manny's to
  40.5236.

Only the drawing changes: no transform, pivot, scale or connection. A rig already in a scene keeps
its small circle; re-add it.

## Proof

`docs/superpowers/plans/verify_main_control_size.py`, mayapy standalone, 9/9: the old Creep's
7.757 as the control; the procedure's `main_size` taking it to Manny's (×5.223893, a second run
×1.0); the three rigs added side by side through Add Character, each Main 40.523613 cm in world
(worst 0.0), flat, where the drop put it, its shape's one input its visibility, Main's scale 1; the
Creep's Main still carrying its root (25.000000 for 25) and the other two untouched.

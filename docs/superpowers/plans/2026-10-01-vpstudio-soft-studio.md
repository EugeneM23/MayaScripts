# Viewport Studio: Soft Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A third Viewport Studio look, Soft Studio: spots with a pool three times Studio's, warm light in
front and cold behind, on a warm cyclorama built as real geometry.

**Architecture:** One row in `maya_vpstudio.LOOKS` plus its light table; two look keys every look gains a
default for (`spot` softness, `fog` colour, `dmap_scale`); a pure `cyclorama_plan` / `cyclorama_rows` and a
`_make_cyclorama` builder sharing `_dress_catcher` with the flat floor. Spec:
`docs/superpowers/specs/2026-10-01-vpstudio-soft-studio-design.md`.

**Tech Stack:** Maya 2027 `maya.cmds`, stdlib `unittest` under mayapy.

## Global Constraints

- Studio and Outdoor are unchanged: their lights, floor, backdrop, filter, bloom, and spot penumbra 14 / dropoff 6.
- Studio stays the default look and `LOOK_ORDER[0]`.
- Every look: exactly one shadow caster, ≤ 8 lights, unique light names.
- Soft Studio key `cover` 5.1 = 3 × 1.7, rim/kicker 4.5 = 3 × 1.5.
- The cyclorama hangs under the group, NOT the light pivot (the Rotate dial turns lights only).
- No OpenMaya mesh creation (not undoable through the press's undo chunk): `polyPlane` + vertex moves.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`.

---

### Task 1: The look's table

**Files:** Modify `SkeldarAnim/maya_vpstudio.py` (light tables, `LOOKS`, `light_plan`, `render_settings`,
`CHECKS`); Test `tests/test_vpstudio.py` (`TestLooks`, new `TestSoftStudio`).

**Produces:** `SOFT_LIGHTS`; `LOOKS["Soft Studio"]` with keys `lights floor backdrop shadow_filter bloom
spot fog dmap_scale`; `spot_softness(look) -> (penumbra, dropoff)`; plan entries carry the look's
penumbra/dropoff and `dmap = min(4096, quality dmap × dmap_scale)`.

- [ ] Tests first: `LOOK_ORDER == ("Studio", "Outdoor", "Soft Studio")`; six lights named
  `key fill rim kicker bounce ambient`; `tan(cone/2)` of the soft key = 3 × Studio key's (same frame,
  `places=6`), rim likewise; key/fill/bounce warm (R > B) and in front (`cos(azimuth) > 0`), rim/kicker
  cold (B > R) and behind (`cos(azimuth) < 0`); soft dropoff < Studio's and penumbra > Studio's;
  `cos(half_soft)^dropoff >= cos(half_studio)^6` at the pool edge (the pool really is wider); Studio's
  plan still 14 / 6; soft dmap 4096 at Good, 4096 at Beauty (capped), 2048 at Fast; soft fog colour warm,
  Studio's unchanged; Backdrop check label `Backdrop`.
- [ ] Run, see them fail; add the table and the keys; run, see them pass.
- [ ] Commit `feat(vpstudio): Soft Studio's lights - three times the pool, warm front, cold back`.

### Task 2: The cyclorama

**Files:** Modify `SkeldarAnim/maya_vpstudio.py` (`cyclorama_plan`, `cyclorama_profile`,
`_dress_catcher`, `_make_cyclorama`, `_make_floor` on the dresser, `_setup`); Test `tests/test_vpstudio.py`
(`TestCyclorama`).

**Produces:** `cyclorama_profile(radius) -> [(z, y), ...]` from the front edge to the wall top;
`cyclorama_plan(frame, azimuth, options) -> {name, position, rotate_y, width, profile, colour, specular,
eccentricity, roll_off}` or None when the look's floor is flat; `_make_cyclorama(plan) -> (node, shader, sg)`.

- [ ] Tests first: the profile starts at `z = +12 r, y = 0`, is flat to `-3.0 r`, ends vertical at
  `z = -4.5 r, y = 8 r`; consecutive points never jump more than a cove segment (continuity); y never
  decreases going back; the cove points lie on the circle (radius 1.5 r about `(-3.0 r, 1.5 r)`); the
  wall's z is behind every soft light's horizontal reach at every rotation (`4.5 r - 1.5 r > max
  distance·cos(el)`); every quad's normal (cross of the profile tangent with +X) faces +z/+y (toward the
  subject); the plan stands at the centre's x/z, the floor's y offset, `rotate_y == azimuth`; width ≥ 24 r;
  None for Studio and Outdoor; the colour warm (R > G > B).
- [ ] Implement; `_setup` builds the cyclorama when `cyclorama_plan` answers, else the floor, both parented
  to the GROUP; the status line says `cyclorama`.
- [ ] Commit `feat(vpstudio): a warm cyclorama behind the subject for Soft Studio`.

### Task 3: Live proof

**Files:** Create `docs/superpowers/plans/verify_vpstudio_soft.py`.

- [ ] In a disposable GUI Maya (scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, a free port): a textured Manny
  skeleton added, a camera in front; Soft Studio applied — six lights, the cones in the scene 126/116°,
  dropoff/penumbra, one depth map at 4096; one cyclorama mesh under the group not the pivot, its wall
  behind the subject seen from the camera, every face normal facing the subject's centre, receives /
  casts / reference; Rotate 90 turns the key and leaves the cyclorama; Studio → no cyclorama, a floor;
  Soft again → one cyclorama; Restore → nothing of ours; the frame time at Good; playblasts front and
  three-quarter, and a wall pixel warm (R > G > B).
- [ ] Look at the pictures; tune colours/intensities by eye if needed (table values only).

### Task 4: Ship

- [ ] Full unit suite green; CLAUDE.md section; commit only our files/hunks (peers edit CLAUDE.md);
  installed copy refreshed from a `git archive` of our commit, `diff -rq` checked.

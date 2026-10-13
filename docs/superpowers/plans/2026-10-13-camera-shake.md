# Camera Shake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone Maya script that keys a procedural camera shake - handheld filming or an impact - on an additive animation layer of its own, over a stretch of the time slider, re-keyed live from its window.

**Architecture:** One file, `docs/superpowers/plans/camshake/skeldar_camshake.py`, in four sections like the physical stop's: the model (numpy: noise, handheld, impact), the rotation algebra (numpy: Maya's eulers both ways, a turn in the camera's own axes), the scene (cmds: targets, refusals, sampling the base through layers, the layer and its keys, apply / re-tune / delete / pick), the window (cmds). Dropped into a viewport it reloads itself and opens the window.

**Tech Stack:** Maya 2027 Python 3, `maya.cmds`, `maya.api.OpenMaya` (frame rate, units), numpy; tests with stdlib `unittest` under `mayapy`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-13-camera-shake-design.md`.
- Outside the plugin: nothing under `SkeldarAnim/` changes; the script imports nothing of the plugin (the verify may).
- One additive layer per press, `rotationAccumulationMode` 0, marked `skeldarCamShake` (JSON, version 1), named `CamShake_<Mode>_<a>_<b>` (a negative frame written `m5`), locked after writing.
- Keys on every frame `a..b` (spline), 0 at `a-1` / `b+1` (flat), `a`'s in-tangent and `b`'s out-tangent linear.
- Every frequency below `0.42 x fps`; amplitudes are two RMS.
- Refusals before any scene change; one undo chunk per Apply / re-tune / Delete.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_camshake -v` from the repo root.
- The live window is the animator's to try (no GUI Maya, no port).

---

### Task 1: The model - settings, noise, handheld, impact

**Files:**
- Create: `docs/superpowers/plans/camshake/skeldar_camshake.py` (section 1)
- Test: `tests/test_camshake.py`

**Interfaces:**
- Produces: `MODES`, `DIRECTIONS`, `CONTROLS[mode] = ((name, label, default, low, high), ...)`, `PRESETS[mode] = ((label, {name: value}), ...)`, `DEFAULT_PRESET`, `settings(mode, given=None) -> dict` (clamped, `seed` int, impact `direction`), `preset(mode, name, current=None) -> dict`, `capped(hz, fps)`, `noise(seconds, seed, stream, hz) -> ndarray`, `fractal(seconds, seed, stream, hz, octaves, gain=0.5, fps=None)`, `smootherstep(x)`, `eased(frames, a, b, ease)`, `kick(tau, swing, bounce, rate=1.0)`, `hit_vector(direction, seed, index=0)`, `picture_direction(h)`, `handheld(frames, a, b, fps, s, index=0) -> (rot (n,3) deg about the camera's X/Y/Z, off (n,3) cm along them)`, `impact(...)` the same, `shake(mode, ...)`, `layer_name(mode, a, b)`, `record_text(...)`, `parse_record(text)`.

- [ ] **Step 1: Write the failing tests** - `tests/test_camshake.py` loads the script by path (as `tests/test_physstop.py` did) and tests: settings clamp and fill; presets keep the seed/ease/length and an impact preset may set the direction; noise is deterministic, unit RMS over a long span (within 10 %), smooth (second difference small against the first), keeps its start when the span grows, has about `hz` zero crossings a second; fractal unit RMS; `capped`; `eased` 0 at both ends, 1 inside, ease 0 is 1; handheld: two RMS of pan = Sway at Jitter 0 over 4000 frames (within 15 %), tilt 0.75 of pan, roll x Roll, Drift on bob, scaling Sway scales the shape exactly, Speed raises the rate, seeds differ, a second camera index differs, 0 at `a` and `b` with Ease; impact: 0 at `a` and `b`, the crest of the kick at the strength, Below turns the view up (rot about +X > 0 at the crest), Left pans right (about -Y) and rolls the top right (about -Z), Front pushes back (+Z) and kicks up, Push along `h`, Bounce 1 overshoots more than Bounce 0, the rattle loud early and gone late, Random's direction seeded; names; record round trip.
- [ ] **Step 2: Run them, see them fail** (no file).
- [ ] **Step 3: Write section 1** (code in the file as committed).
- [ ] **Step 4: Run the tests until green.**
- [ ] **Step 5: Commit** `feat(camshake): the model - noise, handheld, impact`.

### Task 2: The rotation algebra

**Files:** the script (section 2), `tests/test_camshake.py`.

**Interfaces:**
- Produces: `ORDERS` (Maya's rotateOrder enum), `euler_matrix(radians, order)`, `matrix_eulers(m, order) -> [two solutions]`, `closest(solutions, near)`, `rotation_from_vector(v)`, `shaken(base_deg, order, rotvec_deg, rotate_axis_deg=(0,0,0)) -> deg`, `along_axes(offset, base_deg, order, rotate_axis_deg, joint_orient_deg) -> parent-space vector`, `deltas(rot, off, base, order, rotate_axis, joint_orient) -> (dr, dt)`.

- [ ] **Step 1: Tests** - against `maya.api.OpenMaya.MEulerRotation(...).asMatrix()` on all six orders and random angles; `matrix_eulers` round trips (both solutions give the matrix); `closest` lands within 180 of the base on each axis across the +-180 seam and after a full turn; `shaken` with a zero vector is the base; a tilt rotation turns the camera's view (-Z) up (view in the PARENT = `(0,0,-1) . M'`) with a rotate axis and on every order; `along_axes` with a 90 deg yaw sends +X to -Z; a joint orient enters the offset and not the turn.
- [ ] **Step 2: Fail. Step 3: write section 2. Step 4: green. Step 5: commit** `feat(camshake): the rotation algebra - eulers and a turn in the camera's axes`.

### Task 3: The scene - targets, the base, the layer, apply / re-tune / delete

**Files:** the script (section 3); Create `docs/superpowers/plans/camshake/verify_camshake.py`.

**Interfaces:**
- Consumes: sections 1-2.
- Produces: `Refused`, `frame_rate()`, `highlight()`, `frames_for(mode, s, given=None) -> (a, b, where)`, `targets(selection=None) -> [long paths]`, `our_cameras()`, `foreign_driver(plug)`, `base_rotations(node, layer, frames) -> (n,3) deg`, `shakes() -> [layers]`, `record(layer) -> dict|None`, `apply(mode, given=None, selection=None, frames=None) -> (layer, message)`, `retune(layer, given) -> message`, `delete(layer) -> message`, `picked()`, `pick(layer)`, `editor_pick()`.

- [ ] **Step 1: The verify** (mayapy standalone, scratch `MAYA_APP_DIR`): a keyed zxy camera with a rotate axis panning; handheld over 10-100: the layer (additive, mode 0, locked, marked), the base curves' keys unchanged, keys on 9..101, the shown rotation by a real time walk equal to `shaken(base, model)` on every frame (1e-6 deg) and the translation to `base + along_axes`, half frames outside the range 0, a later plain `setKeyframe` landing on the base layer not ours; a re-tune with Sway x2 on the same layer with its weight 0.6 kept: values x2; an impact over 40-60 from Below stacked on it: still at 40, the view up at 41-42, still at 60, the composition exact; two cameras: one layer, different shakes; a joint target; Delete and one undo each; refusals (nothing to shake, an aim-constrained camera, a 1-frame range) leave the scene's node list unchanged; the plugin's Manny skeleton with Camera Setup on `camera_root`, nothing selected: the SceneSetup camera shaken, `camera_root` = offset^-1 . camera on sampled frames and carrying the shake.
- [ ] **Step 2: Run it, see it fail. Step 3: write section 3. Step 4: run until every gate passes. Step 5: commit** `feat(camshake): the scene - one layer per shake, re-tuned in place`.

### Task 4: The window

**Files:** the script (section 4), `tests/test_camshake.py` (a recording fake `cmds`).

**Interfaces:**
- Consumes: section 3.
- Produces: `show()`, `onMayaDroppedPythonFile(*args)`, `_read(mode)`, `_show_settings(mode, s)`, the callbacks.

- [ ] **Step 1: Tests on a fake cmds**: `show()` builds without error and makes every control; a preset fills the sliders; a slider change with a picked shake calls `retune(layer, settings)` with the read values, with none picked calls nothing and remembers; Apply calls `apply(mode, settings)` and picks the layer; Mode switches pick `+ New`.
- [ ] **Step 2: Fail. Step 3: section 4. Step 4: green. Step 5: commit** `feat(camshake): the window - modes, presets, live re-tune`.

### Task 5: The picture and the record

- [ ] Render `docs/superpowers/plans/camshake/camshake_curves.png` (mayapy, offscreen QPainter): the three presets of each mode, pan/tilt/roll over frames.
- [ ] CLAUDE.md: a section for the script, its traps (the stale DG context read).
- [ ] Full unit suite green; commit `docs(camshake): ...`.

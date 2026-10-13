# Tools: Aim and Overlap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OverRig's aim tab in the Tools card, native: **Aim** (a two-press knot whose target and
up the object's rotation aims at) and **Overlap** (a chain trailing its own motion, keyed as deltas
on an additive layer).

**Architecture:** Aim is a new knot kind in `maya_tools/knots.py` (a group holding a target and an
up locator, `aimConstraint` through the knots' pairBlend/attach machinery), its pure half in
`knotplan.py`. Overlap is a pure numpy model (`maya_tools/overlapplan.py`) computing OverRig's
joint-chain-and-locators construction directly from sampled world frames, and a scene module
(`maya_tools/overlap.py`) that finds the chains, walks the time once, and keys the deltas on a new
additive layer. The card (`panel.py`) gets two subsections; hotkeys get two rows.

**Tech Stack:** Maya 2027 `cmds`, `maya.api` (time walk), numpy, stdlib `unittest` under mayapy.

## Global Constraints

- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
  with `$env:QT_QPA_PLATFORM = 'offscreen'`; no system Python.
- `knotplan.py` stays stdlib-only; `overlapplan.py` numpy + stdlib + `knotplan` only (a subprocess
  test pins that no `maya` module is imported).
- Maya's row vectors: a point p goes to `p · M`; frames are 4x4 with rotation in rows 0-2 and
  position in row 3; angles in degrees; rotate orders in Maya's enum `xyz yzx zxy xzy yxz zyx`.
- Ours known by attributes (`skeldarKnot*`, `skeldarOverlap`), never by name; one undo chunk per
  press with autoKey off (`knots._press`); a refusal changes nothing.
- Every button of the card `primary`, every row of buttons/chips `fill`.
- Live GUI checks are the animator's: proof is unit tests + `verify_aim_overlap.py` in mayapy
  standalone.
- Commit only this plan's paths (a peer session edits `docs/superpowers/plans/walkparam/*` and
  `tests/test_walkmodel.py`).

---

### Task 1: The Overlap model (`overlapplan.py`)

**Files:**
- Create: `SkeldarAnim/maya_tools/overlapplan.py`
- Test: `tests/test_tools_overlapplan.py`

**Interfaces:**
- Produces: `Settings(softness, lag, easing, hierarchy, cycled, total, edges)`, `DEFAULTS`,
  `ORDERS`, `CHANGED`, `matrix_from_euler(angles, order)`, `euler_from_matrix(m, order)`,
  `nearest_rotation(m3)`, `frame(world4x4, pivot3)`, `inverse_frames(frames)`, `rest(frames)`,
  `lookup(track, at, cycled)`, `smoothed(track, sigma, cycled)`, `aimed(d, u, dirs, ups)`,
  `simulate(frames, rest_frames, lag, softness, easing, cycled) -> (n, T, 4, 4)`,
  `carried(parent, before, after)`, `rotate_values(world_r, parent_m, ra, jo)`,
  `eulers(rotations, order, base)`, `translate_delta(pivot, parent, new_pivot, new_parent)`,
  `edge_weights(count)`, `link_lag(settings, members)`, `pad(lag, members)`, `NOTHING`,
  `alone_refusal(name, hierarchy)`, `settings_refusal(settings)`, `overlap_message(...)`.

- [ ] **Step 1:** write `tests/test_tools_overlapplan.py` (rotations both ways in all six orders
  and at the gimbal, against OpenMaya's `MEulerRotation` when it imports; lag 0 is the identity;
  a root turning in place comes out delayed by exactly the lag; the tip trails the root; cycled
  wraps; easing calms a jitter; coincident members refused; edge weights; total lag; the channel
  helpers; the lines; purity in a subprocess).
- [ ] **Step 2:** run it - fails on the missing module.
- [ ] **Step 3:** write `overlapplan.py` (the code as committed: rotations, frames, `rest`,
  `lookup` Catmull-Rom clamped or periodic, `smoothed` Gaussian, `aimed` an aimConstraint's frame
  `B_local^T · B_world`, `simulate` top to bottom with `P_i = l_i · C_{i-1}`, the channel helpers
  `RA^T · local · JO^T`, `q' - q` through the parents' inverses, the smoothstep edge ramp).
- [ ] **Step 4:** run - passes.
- [ ] **Step 5:** commit `feat(tools): the Overlap model - OverRig's overlapper computed`.

### Task 2: Aim's pure half (`knotplan.py`)

**Files:**
- Modify: `SkeldarAnim/maya_tools/knotplan.py` (the `aim` Kind, markers, `aim_reach`,
  `aim_vectors`, `axes_of`, `choose_aims`, `aim_label`, the lines, `subtitle(knots, pivots, aims)`)
- Test: `tests/test_tools_knotplan.py`

**Interfaces:**
- Produces: `Kind("aim", "Aim", "_aim", "_aimUp", ..., "aim")`, `AIM_TARGET_SUFFIX = "_aimTarget"`,
  `AIM_SPACE_SUFFIX = "_aimSpace"`, `PENDING_KIND_MARKER = "skeldarKnotPendingKind"`,
  `aim_reach(size) -> 4 * size`, `axes_of(matrix16) -> 3 unit rows`,
  `aim_vectors(name, target_local, up_local) -> (aim, up, refusal)`,
  `choose_aims(named, waiting) -> (list, refusal)`, `aim_label(waiting)`, `AIM_NOTHING`,
  `aim_begin_message(names)`, `aim_finish_message(pairs, span)`,
  `subtitle(knot_count, pivot_count, aim_count=0)`.

- [ ] **Step 1:** tests: the kind; `aim_vectors` normal / target on the object / up on the line;
  `axes_of` strips scale; `choose_aims` named, all waiting, none; `aim_label`; subtitle with aims.
- [ ] **Step 2:** run - fails.  **Step 3:** implement.  **Step 4:** run - passes.
- [ ] **Step 5:** commit with Task 3.

### Task 3: Aim in the scene (`knots.py`)

**Files:** Modify `SkeldarAnim/maya_tools/knots.py`.

**Interfaces:**
- Consumes: Task 2.
- Produces: `pivots(kind="offset")`, `aims_waiting()`, `begin_aim(selection, order, highlight)`,
  `finish_aim(selection)`; `_follow(..., aim=(aim_vector, up_vector, up_node))`;
  `_plan_object(obj, kind, finishing=False)` (kind "aim": rotate channels, an aim waiting refused).

- [ ] **Step 1:** waiting spaces carry a kind (none = offset); `pending_of` answers for a node in
  a waiting space; `_waiting_for(obj, kind)`; `_picked` collects both kinds.
- [ ] **Step 2:** `begin_aim`: a space riding each object, target at `(r,0,0)`, up at `(0,r,0)`,
  rotations locked, the targets selected.
- [ ] **Step 3:** `finish_aim`: the vectors from the placement in the object's axes, a group top
  with two baked locators (translate only, marked inner), the space deleted, `_key_free`, `_mark`,
  `_follow` with the aim branch.
- [ ] **Step 4:** the unit suite still passes; commit `feat(tools): Aim - a two-press knot the
  object's rotation aims at`.

### Task 4: Overlap in the scene (`overlap.py`)

**Files:** Create `SkeldarAnim/maya_tools/overlap.py`.

**Interfaces:**
- Consumes: Task 1, `knots._selection/_children/_parent/_long/_has/_set_string/_press/
  _highlight/constraints_of`, `maya_poselib.timewalk.Walk`.
- Produces: `chain_from(root) -> (chain, note)`, `chains(selection, hierarchy)`,
  `overlap_layers()`, `run(selection=None, settings=DEFAULTS, highlight=SLIDER) -> line`,
  `LAYER_NAME = "Overlap"`, `LAYER_MARKER = "skeldarOverlap"`.

- [ ] **Step 1:** chains (hierarchy walk through other kinds, ending at a branch; selection order).
- [ ] **Step 2:** refusals (settings, a chain of one, riding a knot, driven or all-locked rotates,
  two members in one place) before any change.
- [ ] **Step 3:** take off a previous overlap of ours on the members; one time walk per chain over
  the window; `simulate`; channels; keep edges; keys on a new marked additive layer (zero one
  frame outside a highlight, cycle infinity when cycled).
- [ ] **Step 4:** commit with Task 5.

### Task 5: The card and the hotkeys

**Files:** Modify `SkeldarAnim/maya_tools/panel.py`, `SkeldarAnim/maya_hotkeys.py`,
`tests/test_tools_panel.py`, `tests/test_hotkeys.py`.

**Interfaces:**
- Produces: `panel.aim()`, `panel.overlap()`, `panel.overlap_settings()`, controls
  `AIM_HEADING, AIM_BTN, OVERLAP_HEADING, SOFT_LABEL, SOFT_FIELD, LAG_LABEL, LAG_FIELD,
  EASE_LABEL, EASE_FIELD, HIER_CHIP, CYCLE_CHIP, TOTAL_CHIP, EDGES_CHIP, OVERLAP_BTN`; optionVars
  `skeldarOverlapSoftness/Lag/Easing/Hierarchy/Cycled/Total/Edges`; hotkey rows `tools.aim`,
  `tools.overlap`.

- [ ] **Step 1:** tests: the controls top down, roles (two new primaries, four new chips, 11 fill
  rows), the Aim press begins or finishes, its label, the overlap press reads the remembered
  settings, the fields and chips remember, the hotkey count 57 and the tools rows.
- [ ] **Step 2:** run - fails.  **Step 3:** implement.  **Step 4:** run the whole suite - passes.
- [ ] **Step 5:** commit `feat(tools): the Aim and Overlap subsections, hotkey rows`.

### Task 6: Proof in Maya and the notes

**Files:** Create `docs/superpowers/plans/verify_aim_overlap.py`; modify `CLAUDE.md`.

- [ ] **Step 1:** the verify (mayapy standalone): Aim - begin, place, finish with nothing moving,
  the target moved turning the prop onto it, the up rolling it, attach 0, Remove exact, Bake, undo,
  a range, refusals, a Manny control; Overlap - a keyed joint chain: base untouched, the root
  delayed by exactly the lag, the tip trailing, refusals, keep edges, cycled, replacing, undo, a
  highlight, the selection mode, an AdvancedSkeleton finger chain.
- [ ] **Step 2:** run until green; fix what it finds.
- [ ] **Step 3:** CLAUDE.md section; commit `docs(tools): the aim tab's proof and notes`.

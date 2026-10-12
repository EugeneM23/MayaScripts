# Tools: Knots and Double knot - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hub card Tools holding OverRig's Knot, Knot Offset (two-step), Knot Orient and Double knot
(Local, World), plus Bake and Remove, rebuilt natively in `cmds`.

**Architecture:** a new package `SkeldarAnim/maya_tools/`: `knotplan.py` (stdlib, pure: kinds,
spans, channel plans, sizes, messages), `knots.py` (`cmds`: build, bake, remove, find - identity by
our attributes), `panel.py` (the card and its presses). Wired into `maya_hub.SECTIONS`,
`maya_hubicons`, `maya_hotkeys`, `install.payload()`.

**Tech Stack:** Maya 2027 `maya.cmds`, `maya.api.OpenMayaAnim` (autoKey), stdlib `unittest` under
mayapy, mayapy standalone verify.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-12-tools-knots-design.md`.
- No `mel.eval` of OverRig; the only MEL read is the time slider's highlight through
  `maya_overrig.overrig.slider_selection` (None in batch).
- Lookups by attribute walking locators - never `ls("*.attr")` (CLAUDE.md trap 70).
- One undo chunk per press; a refusal opens none; autoKey off inside a press through
  `MAnimControl.setAutoKeyMode` (trap 212), the current frame left where it was.
- `knotplan.py` imports nothing outside the stdlib (a subprocess test pins it).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
  from the repo root (`C:/!!!Work/MayaScripts-tools`); never `2>&1` in PowerShell.

---

### Task 1: `knotplan` - the pure half

**Files:**
- Create: `SkeldarAnim/maya_tools/__init__.py`, `SkeldarAnim/maya_tools/knotplan.py`
- Test: `tests/test_tools_knotplan.py`

**Interfaces:**
- Produces: markers `KIND_MARKER, SOURCE_MARKER, SPAN_MARKER, KEYED_MARKER, OF_MARKER,
  PENDING_MARKER, PENDING_SPACE_MARKER, GROUP_MARKER, ORDER_MARKER, ATTACH`; `KINDS` (namedtuple
  `Kind(key, label, suffix, inner_suffix, colour, inner_colour, constraint)`), `kind(key)`;
  `TRANSLATE, ROTATE, CHANNELS, LONG`; `ORDERS, ORDER_DEFAULT, rotate_order_index(choice,
  object_order) -> int`; `leaf(path) -> str`; `span_for(playback, keys, highlight) -> (start, end,
  ranged)`; `widen(span, keys)`; `encode_span/decode_span`; `attach_keys(span) -> [(t, v)]`;
  `driver_word(node_type, is_constraint) -> str`; `channel_plan(name, locked, drivers, channels) ->
  (free, skipped, refusal)`; `encode_keyed/decode_keyed`; `is_constant(values)`;
  `still_static(values, value)`; `knot_size(diagonal, radius) -> float`; `OUTER_SCALE`;
  `bake_order(pairs) -> [knot]`; `choose_pivot(named, waiting) -> (pivot, refusal)`; messages
  `created_message, begin_message, finish_message, baked_message, removed_message, subtitle,
  offset_label, riding_refusal` and the refusal constants.

- [ ] **Step 1:** write `tests/test_tools_knotplan.py` covering every function above (spans with and
  without a highlight, `attach_keys` = OverRig's 0/1/1/0 at a-1, a, b-1, b, channel plans with
  locked / driven / free channels and the orient case, the round trips, the bake order of a knot on
  a knot, pivot choice, sizes, rotate orders, messages, stdlib-only by subprocess).
- [ ] **Step 2:** run it - fails on the missing module.
- [ ] **Step 3:** write `knotplan.py`.
- [ ] **Step 4:** run - passes.
- [ ] **Step 5:** commit `feat(tools): knotplan - the knots' pure half`.

### Task 2: `knots` - the scene

**Files:**
- Create: `SkeldarAnim/maya_tools/knots.py`
- Proof: `docs/superpowers/plans/verify_knots.py` (mayapy standalone)

**Interfaces:**
- Consumes: `knotplan` (Task 1); `maya_scenesetup.chargroup.group_of`; `maya_rigs.marked_near_top`;
  `maya_overrig.overrig.slider_selection`.
- Produces: `SLIDER` (the default `highlight`: read the time slider); `create(kind, selection=None,
  order=ORDER_DEFAULT, highlight=SLIDER) -> str`; `begin_offset(selection=None, order=...,
  highlight=SLIDER) -> str`; `finish_offset(selection=None) -> str`; `bake(selection=None) -> str`;
  `remove(selection=None) -> str`; `knots() -> [top]`; `pivots() -> [pivot]`; `top_of(node)`;
  `pending_of(node)`; `constraints_of(obj)`; `source_of(top)`; `waiting()` (bool).

Every press: refusals for every object before anything changes; then one undo chunk with autoKey
off; the build per object = group (`Knots` in the character group, else world `SkeldarKnots`) ->
locators (size, colour, rotate order) -> temporary constraints -> `bakeResults -simulation` over the
span per baked node (rotate curves euler-filtered, still channels plain) -> temporaries deleted ->
the object's free unconnected channels keyed -> markers and `attach` (keyed 0/1/1/0 when ranged)
-> the follow constraint `-mo` with skips, marked `skeldarKnotOf`, `attach` into its weight and
the pairBlend weight, quaternion interpolation. Bake: `bakeResults(preserveOutsideKeys=True)` on
the object's pairBlended channels over span ∪ the knot's keys, then the constraint deleted (Maya
reconnects the baked curve), the knot deleted, rotates euler-filtered. Remove: the constraint
deleted (Maya restores the object's curves), the channels we keyed cut (when still static) and
their values written back, the knot deleted.

- [ ] **Step 1:** write `verify_knots.py` (the gates of the spec's Proof section).
- [ ] **Step 2:** run it - fails (no module).
- [ ] **Step 3:** write `knots.py`.
- [ ] **Step 4:** run until every gate passes; fix what it finds.
- [ ] **Step 5:** commit `feat(tools): knots in the scene - build, bake, remove; the verify`.

### Task 3: the card, the hub, the icons, the hotkeys, the payload

**Files:**
- Create: `SkeldarAnim/maya_tools/panel.py`; test `tests/test_tools_panel.py`
- Modify: `SkeldarAnim/maya_hub.py` (SECTIONS), `SkeldarAnim/maya_hubicons.py` (+ tool, rotate,
  focus-2, stack-2), `SkeldarAnim/maya_hotkeys.py` (rows + `_tools`), `SkeldarAnim/install.py`
  (payload row), `tests/test_hub.py`, `tests/test_hotkeys.py`, the payload tests that count rows.

**Interfaces:**
- Consumes: `knots` (Task 2), `knotplan` (Task 1), `maya_hubstyle`, `maya_hubcopy`.
- Produces: `panel.HUB_SECTION = "tools"`; control names `SUBTITLE, STATUS, KNOT_BTN, OFFSET_BTN,
  ORIENT_BTN, LOCAL_BTN, WORLD_BTN, BAKE_BTN, REMOVE_BTN, ORDER, ORDER_SEG, KNOTS_HEADING,
  DOUBLE_HEADING`; `ORDER_VAR = "skeldarKnotRotateOrder"`; `order()`, `set_order(choice)`;
  presses `knot(), knot_offset(), knot_orient(), double_local(), double_world(), bake(),
  remove()` each returning the line; `refresh()`, `build_panel()`, `is_open()`, `show_window()`.

- [ ] **Step 1:** tests: the card's controls in order and their roles; a press writes the line and
  passes the remembered order; the offset button's label follows `knots.waiting()`; the order
  optionVar (default object, a bad value read as the default); the hub row (label, module,
  builder, frame, group animation, icon tool, after poses); the icons exist; the hotkey rows
  (`window.tools` + seven `tools.*`, counts updated); `maya_tools` in the payload.
- [ ] **Step 2:** run - fail.
- [ ] **Step 3:** write `panel.py`, wire hub / icons / hotkeys / install.
- [ ] **Step 4:** whole suite green.
- [ ] **Step 5:** commit `feat(tools): the Tools card - knots in the hub`.

### Task 4: CLAUDE.md, the GUI verify for the animator, merge

- [ ] **Step 1:** `docs/superpowers/plans/verify_tools_card.py` - the card in a live Maya (open,
  press Knot on a cube through Qt, undo), written and NOT run (the animator's live checks).
- [ ] **Step 2:** a CLAUDE.md section «Tools: OverRig's Knots and Double knot, native».
- [ ] **Step 3:** whole suite + `verify_knots.py` once more; commit; merge into `main` (no push -
  a push is a release, asked first).

# UE Bridge drag-to-viewport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A row of the UE Bridge list pressed and dragged into a viewport retargets onto the rig under
the cursor, or onto a new Manny rig when there is none.

**Architecture:** An event filter on the list's QListWidget (`maya_uebridge/listdrag.py`, Qt lazily)
carries the row with the hub's shared ghost; `droptarget.clip_target` names the rig under the cursor
from its projected game-skeleton bones; the release calls `window.import_dropped`, which exports from
the editor and hands `rigimport.import_and_retarget` the rig (new `rig=` argument) or `"new_rig"`.

**Tech Stack:** Maya 2027 cmds, OpenMaya/OpenMayaUI, PySide6 6.8.3; tests under mayapy unittest,
offscreen Qt.

## Global Constraints

- A new rig stands where the clip is (no offset); it is `catalog.default_rig()` (Manny).
- The import-mode segments and the selection do not change a drop; the timeline checkbox does.
- Bare skeletons are not drop targets.
- `maya_uebridge/window.py` stays `cmds` at import; Qt only inside `listdrag`, imported lazily.
- Every failure of a press reaches the status line (`window._run`).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
  with `$env:QT_QPA_PLATFORM='offscreen'`.

---

### Task 1: the rig under the cursor (`droptarget`)

**Files:** Modify `SkeldarAnim/maya_scenesetup/droptarget.py`; Test `tests/test_scenesetup_droptarget.py`

**Interfaces — Produces:**
- `figure_under(point, figures, radius_min) -> key | None` (pure; `choose` uses it on the figures with hands)
- `rig_text(label) -> "retarget onto <label>"`, `new_rig_text(label) -> "a new <label>"` (pure)
- `rig_snapshot() -> [dict(key=<namespace>, label, points, segments, root)]`
- `clip_target(gx, gy, snap, scale=1.0, new_label="Manny [rig]") -> dict` kinds `rig` (rig, label,
  text) / `new_rig` (text) / `none` (text)

- [ ] Tests: `figure_under` picks the nearest figure within max(radius_min, 8 % height), None off
  every figure, a figure with no hands still counts; `choose` unchanged (existing tests);
  `clip_target` with `Viewport.at` replaced by a fake view (identity projection, depth by key):
  on a figure → `rig`, off → `new_rig`, no viewport → `none` with `NO_VIEWPORT`.
- [ ] Implement, run, commit with Task 2.

### Task 2: an explicit rig for `import_and_retarget`

**Files:** Modify `SkeldarAnim/maya_uebridge/rigimport.py`; Test `tests/test_uebridge_rigimport.py`

- [ ] Tests (ThePress): `rig=second` with two rigs and no selection → reset/connect on `second`,
  `("which",)` never called; `target="new_rig", rig=first` adds a rig and never resets `first`.
- [ ] Implement: `def import_and_retarget(fbx_path, name, clip_fps=None, set_timeline=True,
  target="rig", rig=None)`; `if target == "new_rig": rig = None`; ask `current_rig()` only when
  `target == "rig" and rig is None and all_rigs`.
- [ ] Run, commit.

### Task 3: shared pieces — `run` icon, `maya_hubqt.on_hub`

**Files:** Modify `SkeldarAnim/maya_hubicons.py`, `SkeldarAnim/maya_hubqt.py`,
`SkeldarAnim/maya_chargrid.py`; Test `tests/test_hubicons.py` (existing checks cover the new path)

- [ ] `ICONS["run"]` = Tabler `run` outline paths.
- [ ] `maya_hubqt.on_hub(gx, gy, control="skeldarAnimHub")`: widget ancestry names include
  `hubstyle.ROOT` or the control, or the point falls in the visible control's rect; chargrid's
  `Scene.over_hub` returns it.

### Task 4: the list's drag (`listdrag`)

**Files:** Create `SkeldarAnim/maya_uebridge/listdrag.py`; Test `tests/test_uebridge_listdrag.py`

**Interfaces — Produces:** `attach(list_name, records_of, scene=None) -> Drag | None`,
`attach_widget(widget, records_of, scene) -> Drag`, `Drag.drop_at(gx, gy, record)`, `Scene`
(`scale, snapshot, target(gx, gy, snap), over_hub, drop(record, aim), say`), pure
`caption(name, aim) -> (text, good)`.

- [ ] Tests offscreen on a real QListWidget with three rows and a fake scene: press row 1 → move 30 px
  (drag starts, ghost exists) → move far → release: `drop` got record 1 and the fake aim; a click is
  no drag and the release reaches the list; moves while held are eaten (the list's selection stays
  on the pressed row); Esc cancels; the right button cancels; a release on the hub drops nothing;
  a drop whose `drop` raises says so; no row under the press starts nothing; `caption` texts.
- [ ] Implement, run, commit.

### Task 5: the window

**Files:** Modify `SkeldarAnim/maya_uebridge/window.py`; Test `tests/test_uebridge_window.py`

- [ ] `import_dropped(record, aim)`: `none` → status; `rig` → `maya_rigs.find(aim["rig"])`, gone →
  status; `_export_from_editor(record)`, `rigimport.import_and_retarget(..., target="rig", rig=rig)`
  or `target="new_rig"`; the timeline checkbox read guarded.
- [ ] `build_panel` ends with `_attach_drag()`: `listdrag.attach(_LIST, lambda: list(_STATE["filtered"]))`
  inside try/except (no Qt → nothing).
- [ ] Tests with fake cmds/rigimport: the three kinds route as above; the export is not called for a
  gone rig or `none`.
- [ ] Run the whole suite, commit.

### Task 6: live proof

**Files:** Create `docs/superpowers/plans/verify_uebridge_drag.py`

- [ ] In a disposable GUI Maya (port 7003+, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`): two rigs side by
  side; `clip_target` at each rig's projected pelvis → that rig; at an empty floor point → `new_rig`;
  off the viewport → `none`; a press-drag-release through Qt on the real list ends a drag; `drop_at`
  with `_export_from_editor` replaced by a shipped-asset UE clip (or a clip exported from a rig) →
  retarget onto the rig under the point, the other unmoved; empty floor → a third rig.

### Task 7: docs, install, commit

- [ ] CLAUDE.md section; installed copy refreshed from a `git archive` of the commit.

# Moveset: no planning in the card, Export into a slot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the Moveset card loses its statuses and assignees, and gains Export 3P / Export 1P, which write
the scene back into the AnimSequences the picked attack's montage slot plays.

**Architecture:** a new `maya_moveset/export.py` holds the pure plan (which scene frames each of the
slot's segments owns, and every refusal) and the press (the FBX per segment through
`animexport.export_hierarchy(start=, end=)`, the uasset's read-only flag through
`maya_uebridge.uasset_core`, the replace-import through `uescripts.reimport_script`). The card keeps no
knowledge of Unreal beyond calling it, exactly as Open does.

**Tech Stack:** `maya_moveset` (stdlib `model.py` / `export.py` pure halves, `cmds` `panel.py`, PySide6
`view.py`), the UE Bridge's `animexport`, `uasset_core`, `uescripts`, `uelink`; mayapy's unittest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-29-moveset-export-to-slot-design.md`.
- `model.py` and the pure half of `export.py` stay **stdlib only** — subprocess tests pin both.
- **The page is not touched**: its planning board, its statuses and its people stay, and so does what it
  wrote in `state.json`.
- **A refusal writes nothing** — no FBX, no flag cleared, no editor call.
- Perforce is never touched; the read-only flag is cleared and left off (the bridge's own rule).
- Tests at the end, as the animator asked: Tasks 1–4 keep the existing suite green, Task 5 writes the new
  tests.
- Tests run `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest ...` from the repo root,
  Qt tests with `$env:QT_QPA_PLATFORM = 'offscreen'`.

---

### Task 1: the planning leaves the card — DONE (6ed60b4f)

**Files:**
- Modify: `SkeldarAnim/maya_moveset/view.py` (the dots in `Card.paint` / `_paint_dot` / `dot_rect` /
  `dot_at`, `menu_rows`), `SkeldarAnim/maya_moveset/panel.py` (the Assignee menu, `_set`, `_summary`,
  `_fill_menus`, `attach`'s actions), `SkeldarAnim/maya_moveset/model.py` (`set_status`, `set_assignee`,
  `kept`'s `who`, `STATUSES`, `initials`)
- Test: `tests/test_moveset_model.py`, `tests/test_moveset_view.py` (the existing tests that name what
  goes)

- [ ] **Step 1: the model** — delete `set_status`, `set_assignee`, `STATUSES` and `initials`; `kept(tree,
      state, types=())` keeps the type filter only. `read_state` keeps every key it reads (the page still
      writes `status` / `assignee`, and `custom` / `hidden` / `weapon` are the card's).
- [ ] **Step 2: the view** — a card draws its name, its preview, its type stripe and its foot; the dots,
      their status colours and the assignee's emoji go with `dot_rect`, `dot_at`, `_paint_dot` and the
      1P double click. `menu_rows` is `Open 3P` / `Open 1P` (Export joins them in Task 3).
- [ ] **Step 3: the card** — the `WHO_MENU` dropdown and its `_filter(who=)` branch go, `_fill_menus`
      stops filling people, `_set` goes with the `status` / `assign` actions, and `_summary` reads
      «Dagger - 22 attacks».
- [ ] **Step 4: the existing tests** — the gone functions and the dots leave
      `tests/test_moveset_model.py` (`test_an_assignee_filter_and_unassigned`, the status half of
      `Files`) and `tests/test_moveset_view.py` (`test_a_status_shows_on_its_dot`,
      `test_a_dot_names_its_view_and_a_double_click_opens_it`, the menu rows' indices, the Presses'
      `_set` test, the `WeaponCard` summary's «1 of 10 done»). A gone-test pins that neither
      `set_status` nor `set_assignee` is in the model.
- [ ] **Step 5: Run** `mayapy -m unittest tests.test_moveset_model tests.test_moveset_view` — green.
- [ ] **Step 6: Commit** — `feat(moveset): the planning leaves the card`

---

### Task 2: the export's plan (pure) — DONE

**Files:**
- Create: `SkeldarAnim/maya_moveset/export.py`
- Test: (Task 5)

**Interfaces:**
- Produces:
  - `Piece = collections.namedtuple("Piece", ["package", "anim", "start", "end"])` — `start` / `end` are
    whole scene frames, `package` is what the replace-import writes.
  - `plan(graph, node_id, view, fps) -> (pieces, refusal)` — `refusal` "" when the slot can be written.
  - `TOL = 1e-4` (seconds), `line(node_label, view, pieces)` for the status line.

- [ ] **Step 1: the module** — stdlib only (`collections`, `os` not needed), the mapping the montage
      import uses: a segment covering montage seconds `[t0, t1)` owns scene frames
      `round(t0 * fps) .. round(t1 * fps)`, `t1 = t0 + (anim_end - anim_start)`. The boundary frame
      belongs to both neighbours: it is the end pose of one sequence and the start pose of the next.

```python
def plan(graph, node_id, view, fps):
    """(pieces, refusal) for a slot's track. Pure.

    The inverse of the montage import's own mapping: at frame f the take is
    the montage at f / fps, so a segment that plays its sequence whole at
    rate 1 owns the frames of its own span.
    """
    node = (graph.get("nodes") or {}).get(node_id)
    if node is None:
        return [], "{0}: graph.json holds no montage for it".format(node_id)
    key = "segments1p" if view == "1p" else "segments"
    slot = node.get("slot1p" if view == "1p" else "slot")
    segments = node.get(key) or []
    if not slot or not segments:
        return [], "{0} has no {1} track".format(node_id, view.upper())
    pieces = []
    for index, segment in enumerate(segments, 1):
        anim = str(segment.get("anim") or "")
        rate = float(segment.get("rate") or 1.0)
        loops = int(segment.get("loops") or 1)
        lo = float(segment.get("anim_start") or 0.0)
        hi = float(segment.get("anim_end") or 0.0)
        length = float(segment.get("anim_length") or 0.0)
        t0 = float(segment.get("start_pos") or 0.0)
        if abs(rate - 1.0) > TOL:
            return [], "{0} {1}: segment {2} plays at rate {3:.2f} - it cannot be written back".format(...)
        if loops != 1:
            return [], "{0} {1}: segment {2} loops {3} times - it cannot be written back".format(...)
        if lo > TOL or hi < length - TOL:
            return [], ("{0} {1}: segment {2} plays {3:.2f}-{4:.2f} s of {5} ({6:.2f} s) - a slice "
                        "cannot be written back, the import replaces the whole animation").format(...)
        pieces.append(Piece(package=anim.split(".", 1)[0], anim=anim.rsplit("/", 1)[-1].split(".")[0],
                            start=int(round(t0 * fps)), end=int(round((t0 + hi - lo) * fps))))
    return pieces, ""
```

- [ ] **Step 2: Run** `mayapy -c "from maya_moveset import export"` from `SkeldarAnim` — imports with no
      Maya.
- [ ] **Step 3: Commit** — `feat(moveset): the export's plan, pure`

---

### Task 3: the press and the two buttons

**Files:**
- Modify: `SkeldarAnim/maya_moveset/export.py` (the scene half), `SkeldarAnim/maya_moveset/panel.py`
  (the buttons, the menu rows), `SkeldarAnim/maya_moveset/view.py` (`menu_rows` gains Export),
  `SkeldarAnim/maya_uebridge/window.py` (one accessor: `def content_dir(): return _STATE.get("content_dir") or ""`)

**Interfaces:**
- Consumes: Task 2's `plan`; `animexport.resolve_root()`, `animexport.export_hierarchy(fbx, root=,
  start=, end=, layout=animexport.UNREAL_LAYOUT)`; `uasset_core.is_read_only / clear_read_only /
  fbx_staging_path / readonly_note`; `records.uasset_path_of(package, content_dir)`;
  `uescripts.reimport_script(out, package, fbx)`; `uelink.run_script(script, out, project=)`;
  `window.temp_folder()`, `window.project_choice()`, `window.content_dir()`.
- Produces: `export_slot(graph, node_id, view, label, asks=None) -> str` (the status line);
  `panel.export_picked(view)`; `panel.EXPORT = "skeldarMovesetExport{0}"`.

- [ ] **Step 1: the press** — refusals first (the plan's, then `resolve_root`'s), then ONE confirm
      listing every sequence and what a replace-import throws away, then per piece: the FBX, the flag,
      the reimport. A failure stops and names what was already written.
- [ ] **Step 2: the card** — `Export 3P` (secondary) and `Export 1P` in a row under Open 3P / Open 1P /
      Fit, and the same two rows in the right-button menu (`view.menu_rows`, `actions["export"]`).
- [ ] **Step 3: the bridge's accessor** — `window.content_dir()`, and its own uasset press uses it.
- [ ] **Step 4: Run** `mayapy -m unittest tests.test_moveset_model tests.test_moveset_view
      tests.test_uebridge_window` — green.
- [ ] **Step 5: Commit** — `feat(moveset): Export 3P / Export 1P into the slot`

---

### Task 4: the frame offset — NOT NEEDED (measured 2026-10-29)

`export.plan` over both graphs: every writable track is ONE sequence starting at frame 0 (25 + 25 rows),
so no export shifts anything. A piece that would start later is refused by name. The editor run waits for
a slot that plays two different sequences; the steps below stay for that day.

### Task 4 (deferred): the frame offset, measured against the editor

- [ ] **Step 1: ask** — the run needs the animator's editor open with Remote Execution, and it writes to
      a sandbox copy of an AnimSequence, never to one of theirs.
- [ ] **Step 2: the probe** — duplicate a dagger sequence into `/Game/__moveset_verify`, export the
      scene's frames 44–87 into it through `export_slot`'s own road, and read the result's frame count
      and the first frame's pose through `uelink`.
- [ ] **Step 3: the answer** — a 44-frame sequence means Unreal normalises and nothing more is needed;
      88 frames with an empty head means the export must shift the keys to 0 first, and the press gains
      that shift (one undo chunk, the scene restored).
- [ ] **Step 4: delete the sandbox asset** and say what was measured.
- [ ] **Step 5: Commit** — `fix(moveset): the exported segment starts at frame 0` (only if the shift is
      needed)

---

### Task 5: the tests and the docs

**Files:**
- Test: `tests/test_moveset_export.py` (new), `tests/test_moveset_view.py`
- Modify: `CLAUDE.md`, the spec's measured lines

- [ ] **Step 1: the plan's tests** — a one-segment slot's frames and package; a four-segment slot's four
      pieces, abutting on the boundary frame; the slice, the rate, the loop, the missing track and the
      missing node refusals, each naming its segment.
- [ ] **Step 2: the press's tests** — on fakes: the confirm's text names every sequence; a cancel writes
      nothing; each piece exports its own range and reimports its own package; a failing reimport stops
      and names what was written.
- [ ] **Step 3: the card's tests** — the two buttons and the two menu rows; the press with nothing picked
      says so.
- [ ] **Step 4: the gone-tests** — no status dot, no assignee row, no `set_status` / `set_assignee`.
- [ ] **Step 5: Run the whole suite** — only the six failures that predate the work.
- [ ] **Step 6: the docs** — CLAUDE.md's Moveset section gains the export and loses the planning; the
      spec gains what the build measured.
- [ ] **Step 7: Commit** — `test(moveset): the export's tests, and the docs`

## Self-review

- **Spec coverage:** the planning's removal (Task 1), the plan and its refusals (Task 2), the press, the
  confirm, the read-only flag and the status line (Task 3), the frame-offset measurement (Task 4), the
  proof and the docs (Task 5).
- **Placeholders:** the `.format(...)` ellipses in Task 2's code are the message arguments spelled out in
  the sentence beside them; every other step carries its code or its exact command.
- **Type consistency:** `Piece(package, anim, start, end)` and `plan(graph, node_id, view, fps) ->
  (pieces, refusal)` are used with those names in Tasks 2, 3 and 5; `export_slot(graph, node_id, view,
  label, asks=None)` in Tasks 3 and 5.

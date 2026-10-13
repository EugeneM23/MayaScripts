# The Tools card as a list with explanations - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The hub's Tools card rebuilt as mockup C: flat tool rows with explanations in three collapsible
subsections (Knots, Parent, Overlap), a "Selected knots" footer, orange only for a waiting Finish.

**Architecture:** The skin learns four roles (`toolrow`, `subhead`, `caption`, `columns`) and a
`hint` on a mark; `maya_hubqt.set_state(name, state)` lights a waiting row and turns a head's chevron.
`maya_tools/panel.py` builds the card from them with plain `cmds` and remembers which subsections are
open; its presses are unchanged.

**Tech Stack:** Maya 2027 `cmds`, PySide6 6.8.3 (the hub skin), stdlib unittest under mayapy.

Spec: `docs/superpowers/specs/2026-10-13-tools-card-list-design.md`

## Global Constraints

- `maya_hubstyle` stays stdlib-only; no Qt call in `maya_tools/panel.py` except through `_light`.
- Every control name of the old card that a press, a refresh, a hotkey row or a verify uses keeps its
  name (`KNOT_BTN`, `OFFSET_BTN`, ..., `STATUS`, `SUBTITLE`, `ORDER_SEG`).
- Stylesheet px are physical: every px through `hubstyle.px(n, scale)`.
- No blanket background rules (`test_no_blanket_background_rule`), no QLabel background.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
  with `$env:QT_QPA_PLATFORM = 'offscreen'`.

---

### Task 1: The skin's new roles and `set_state`

**Files:**
- Modify: `SkeldarAnim/maya_hubstyle.py` (Mark.hint, `mark(..., hint=)`, ROLES, TOKENS["tool_icon"],
  `ROW_NAME`, stylesheet rules)
- Modify: `SkeldarAnim/maya_hubqt.py` (`_ICON_COLOUR`, `_apply_mark` for the four roles, `_hint_class`,
  `set_state`, `_paint_state`, `_spread(..., "columns")`)
- Test: `tests/test_hubstyle.py`, `tests/test_hubqt.py`

**Interfaces:**
- Produces: `hubstyle.mark(name, role, icon=None, layout=False, hint=None)`;
  `hubstyle.Mark(name, role, icon, layout, colour, target=None, hint=None)`;
  roles `"toolrow"`, `"subhead"`, `"caption"`, `"columns"`;
  `hubstyle.ROW_NAME` (logical px of a tool row's name column);
  `maya_hubqt.set_state(name, state) -> bool` (`state` "" / "wait" for a tool row,
  "open" / "closed" for a head).

- [ ] Step 1: tests in `test_hubstyle.py`: a mark carries its hint; the four roles exist and are
  styled or handled; the toolrow rule has no border and aligns left, its wait rule is the accent;
  the head rule is bold over a hairline; the caption is muted.
- [ ] Step 2: tests in `test_hubqt.py` (`ApplyMarks`): a tool row's hint is a child label after the
  name column, elided at a narrow width, the icon in `tool_icon`; `set_state("wait")` sets
  `skState` and recolours the icon, `""` puts it back; a state set before the marks are applied is
  painted by `_apply_mark`; a head's chevron follows "closed" / "open"; `columns` spreads a label
  and a field over the row; `set_state` answers False for a control not there.
- [ ] Step 3: run them - FAIL.
- [ ] Step 4: implement (`maya_hubstyle`, `maya_hubqt`).
- [ ] Step 5: run - PASS; the whole hub suite green.
- [ ] Step 6: commit `feat(hub): tool rows, subsection heads, captions and columns in the skin`.

### Task 2: The Tools card rebuilt

**Files:**
- Modify: `SkeldarAnim/maya_tools/panel.py`
- Modify: `tests/test_tools_panel.py`
- Modify: `docs/superpowers/plans/verify_tools_card.py` (open Parent before Across)
- Modify: `CLAUDE.md` (the Tools section: a paragraph on the new card)

**Interfaces:**
- Consumes: Task 1's `mark(..., hint=)`, the roles, `maya_hubqt.set_state`.
- Produces: `panel.SECTIONS` = (("knots", "Knots", hint), ("parent", "Parent", hint),
  ("overlap", "Overlap", hint)); `panel.HEAD[key]`, `panel.BODY[key]`;
  `panel.is_section_open(key) -> bool`, `panel.set_section_open(key, on) -> bool`,
  `panel.toggle_section(key) -> bool`; `panel._light(name, state)` (the seam);
  `panel.HINTS[name]` (each tool row's explanation); `OPEN_VAR = "skeldarToolsOpen_%s"`.

- [ ] Step 1: rewrite the card tests: the controls top down (heads, bodies, rows, footer); the roles
  (toolrow for the eleven tools, subhead for the three heads, caption, columns, inset footer,
  danger Remove, no primary anywhere); the hints; the subsection memory (defaults, toggling manages
  the body and lights the head, remembered); the wait state lit through `_light` on refresh; the
  presses unchanged.
- [ ] Step 2: run - FAIL.
- [ ] Step 3: implement the builder.
- [ ] Step 4: run - PASS; the whole suite green.
- [ ] Step 5: verify plan and CLAUDE.md; commit `feat(tools): the Tools card as a list with
  explanations (variant C)`.

# Tools: the parent tab - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline here).

**Goal:** OverRig's parent tab in the Tools card: Inside, World, Swap (re-parent keeping the
motion), Across (a knot inside the parent), Multiple across, Attach 0 / 1.

**Architecture:** pure lines and plans in `maya_tools/knotplan.py`; `knots.py` gains the `across`
kind (`create_across`), the registry set and `set_attach`; a new `maya_tools/reparent.py` does
Inside / World / Swap; `panel.py` gets the Parent and Multiple across subsections and the Attach row.

**Tech Stack:** maya.cmds, mayapy unittest, mayapy standalone verify.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-12-tools-parent-design.md`.
- Re-parents bake the whole take, never a highlight; no scale keys cut, nothing hidden.
- Refusals before any change; one undo chunk per press; autoKey off through the API.
- Every button `primary`, every row of buttons `fill`.

---

### Task 1: knotplan - the pure half
- Tests then code: the `across` kind; `swap_plan(paths, parent_of)`; `inside_cycle(child, parent)`;
  `attach_times(highlight, selected_keys, now)`; `list_label(word, count)`; `rig_part_refusal`,
  `reparent` lines; `uneven_target`.
- Commit.

### Task 2: knots - across, the registry, attach
- `create_across(pairs, order, highlight, rotate, translate)`; registry objectSet; `knots()` adds
  its members; `set_attach(value, selection, highlight)`.
- `verify_parent.py` cases for Across / Multiple / Attach; run; commit.

### Task 3: reparent - Inside, World, Swap
- `reparent.py`; verify cases for the three and their refusals; run; commit.

### Task 4: the card, hotkeys, docs
- panel subsections, chips, lists, Attach row; tests; hotkey rows; CLAUDE.md; full suite; commit.

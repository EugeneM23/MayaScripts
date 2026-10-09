# The edge panel on either side of the screen

2026-10-09. The animator: «Можем добавить опцию выбора стороны монитора откуда выезжает наша полка?»
Asked, both the recommendation: **the left and the right edge** (the panel stays a full-height
column; top/bottom would turn it into a strip the cards do not lay out in), chosen in **⋮ → Edge
panel ▸ Off / Left edge / Right edge**.

Builds on `2026-10-08-hub-compact-and-edge-panel-design.md` (the edge panel) and the 2026-10-09
frame slide (`maya_edgerules.FRAME_MS / HUB_DELAY_MS / IN_MS`).

## Behaviour

- ⋮ → **Edge panel** is a submenu of three exclusive rows: **Off**, **Left edge**, **Right edge**,
  the standing state checked. It replaces the checkable «Edge panel» row.
- **A side picked while the mode is off** turns it on at that side: the dock goes, the panel is
  built and slides out once, held (it stays until visited and left, or a press lands outside), as
  turning the mode on does today.
- **The other side picked while the panel stands**: the panel goes at once (no slide back), stands
  at the new edge and slides out from it, held - the animator sees where it went.
- **The side already standing picked again**: nothing changes.
- **Off**: as today (the panel goes, the dock opens).
- **Remembered** in the optionVar `skeldarAnimHub_edgeSide` (`"left"` / `"right"`); missing or
  anything else reads `"left"`. `skeldarAnimHub_edge` (on/off) is unchanged, so an installed copy's
  state carries over. The width (`skeldarAnimHub_edgeWidth`) is one for both sides.
- **The screen** is the one holding Maya's main window, as before. A monitor beyond the chosen
  edge: a cursor crossing into it does not open the panel, the 100 ms dwell on the edge does (the
  left edge's rule, unchanged).

## The right side, mirrored

Every quantity the controller keeps is "from the screen edge inward": the slot's OFFSET (`-w` off
the edge, `0` out - `slide_x`, `reveal_at` unchanged) and the FRAME (px of the host showing from
the edge). Only their translation into the host's own coordinates depends on the side:

| | left | right |
|---|---|---|
| host | work area's left edge | work area's right edge (`x + w - pw`) |
| sensor | 2 px at the left edge | 2 px at the right edge |
| slot x (host-local), slot width `w - line` | `offset` | `line - offset` |
| frame shown (window mask) | `[0, frame)` | `[w - frame, w)` |
| the 1 px line | `frame - line` | `w - frame` |
| width grip | host's right `[w - g, w)` | host's left `[0, g)` |
| a grip drag by `dx` global px | `width0 + dx / scale` | `width0 - dx / scale` |

The host is right-anchored on the right side, so a width change moves its left edge (`place()`
already re-reads the rect on every `set_width`).

## Code

- **`maya_edgerules`** (stdlib): `SIDE_VAR`, `SIDES = ("left", "right")`, `side_of(value)`;
  `panel_rect(area, width, scale, side="left")`, `sensor_rect(area, side="left")`; the local
  geometry, pure: `slot_x(offset, line, side)`, `offset_of(x, line, side)`,
  `frame_span(frame, host_w, side)` -> `(x, w)`, `line_x(frame, host_w, line, side)`,
  `grip_x(host_w, grip, side)`, `dragged_width(width0, dx, scale, side)`.
- **`maya_hubedge`**: `Edge(side="left", ...)`, `edge.side`; the slot's offset is read back
  through `offset_of`, never as `slot.x()`; `set_side(side)`: a new side stops any slide, hides the
  panel at once and places the windows at the new edge, the sensor up (`maya_hub` then reveals it
  with a hold); the same side does nothing (False).
- **`maya_hub`**: `edge_side()`; `_ensure_edge` builds the Edge on it; `set_edge_side(choice)`
  (`"off"` / `"left"` / `"right"`): off is `set_edge(False)`; a side is remembered, then turns the
  mode on (`set_edge(True)`) or, with a panel standing, moves it (deferred - the press comes from
  the panel's own menu); refused like `set_edge(True)` without the new look. Callback key
  `"edge_side"`; `"edge"` stays for older callers.
- **`maya_hubqt`**: the submenu (`Skin.edge_menu`, `Skin.edge_actions[choice]` in a
  `QActionGroup`); `paint_edge(on, side="left")`, `set_edge_mode(on, side="left")`. A row's
  `triggered` calls back `("edge_side", choice)`; painting calls nothing.

## Proof

Unit tests (offscreen Qt, fake `cmds`): the rules on both sides; a right-side `Edge` - the windows'
places, the sensor, the frame growing from the right edge and its mask, the slot coming in from the
right and resting at the line, the grip on the left widening the panel when dragged left, a reveal
turned back; `set_side` moving a standing panel; the hub's choice table, the remembered side, the
deferred move; the submenu and its callbacks. The whole suite. **Live: the animator's** (no GUI
Maya, port or install of ours, 2026-10-09).

## Not built

Top and bottom edges; a side per monitor; a slide across from one side to the other.

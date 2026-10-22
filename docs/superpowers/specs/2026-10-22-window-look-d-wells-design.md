# Floating windows: the frame of look D, look B's wells (2026-10-22)

After the spring (`2026-10-22-window-look-b-spring-design.md`) the animator asked to redraw the
windows themselves: «перерисуем что бы было как вариант B в предыдущих макетах», then, on four
new frames (https://claude.ai/artifact/TEXoEcRVjj2ap5XJP1BVJf,
`docs/superpowers/plans/window_look_mockups.html`): «Мне нравится как ты сделал D с объемом».
So the frame is D's and the inside is the earlier mockup's B
(`window_motion_mockups.html`): every group of controls on a recessed well.

## The frame (look D)

Every `maya_hubwindow.WindowFrame`: the section windows, the edge rail's card, the chat window.

- The face fades from `BEVEL_TOP` #26282c at the top to `panel` by `BEVEL_FADE` 46 logical px;
  a white line at 7 % just inside the top edge (the bevel); a 1 px `EDGE` #101113 outline;
  radius `RADIUS` 10.
- A grip: a 34 x 3 bar in `line` at 60 %, 5 px down, in the middle of the top.
- The title: the group's dot (8 px in its group colour, a soft glow of it, `dot_pixmap`) and
  the name as written, bold, `text`, 10.5 logical px. No hairline under the title.
- The light of the window worked in (`maya_hubqt.paint_light(..., radius=10, face=False)`):
  the accent ring and its inner glow on the edge; the face no longer turns `card_active`.
- No drop shadow: a margin round the window would move its place, size and grips.

## The wells (look B)

- `wells(heads, items, left, right, pad, gap)`, pure: a group is the controls between two
  headings (`heading` or `subhead` marks), or all of them with none; its well is the group's
  height plus `WELL_PAD` 4, ending `WELL_GAP` 5 above the next heading; every well as wide as
  all the controls plus the pad, within `WELL_MARGIN` 5 of the frame's sides; radius 6,
  `track` with a `track_edge` edge.
- `_groups(content, frame)` reads the shown controls each paint: a widget holding no shown
  widget (scroll bars left out), headings and what is inside them apart. ~1.5 ms on a
  300-control card, so the frame's paint stays cheap.
- Inside a well the fields stand up: line edits, drop-downs, lists, tool buttons, chips, check
  boxes and segment tracks on `panel` with a `track_edge` edge (`recessed_sheet`).
- The chat window keeps its card (`content_face = "card"`).

## Proof

- `tests/test_hubwindow.py`: the bevel lighter than the panel below, the dark outline, the grip,
  a control on a well and the panel past it, no well on an empty content, `wells` (groups,
  gaps, sides, empties), the title's name and dot; the window and rail-card tests updated.
- `render_floating_window.py` -> `floating_window.png`, its stand-in now in two captioned
  groups.
- Not seen in a GUI Maya: the animator's to try after Check update.

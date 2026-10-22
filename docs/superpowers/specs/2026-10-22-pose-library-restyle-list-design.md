# Pose Library: our look, more compact, a list at the smallest size (2026-10-22)

The animator: «нужно перерисовать библеотеку поз в нашем стиле и сделать само меню более
компактным. Так же нужно сделать так что бы мы при минимальном размере значков наши карточки
начинали отображаться списком с маленькими привью». Four mockups
(https://claude.ai/artifact/2M3xdDHPGJZusLsV8PcjrU): A kept the folder tree as a column, B moved
the folder into a button in the top bar. They chose **B**.

## What changes

**No tree column.** The cards take the width the tree had. The folder is a button at the left of
the top bar, `skeldarPoseFolderButton`, reading the picked folder's path
(«Library › Hands › Left ▾», elided). A click opens the folder popup `skeldarPoseFolderPopup`
under it. The popup holds the SAME `QTreeWidget` (`skeldarPoseFolders`), so the tree's picks,
its right-button rows (New folder, Rename, Delete, Show in Explorer) and every test of them stay
as they are. A pick closes it; Esc or a press outside closes it. It is a frameless tool window
that never takes the mouse grab, so:

- **a card dragged onto the folder button opens the popup** (`folder_at`, which the chat's drag
  asks too), and a release over a folder in it moves the card there, as the tree did;
- the popup closes when the drag ends.

**The look** (docs/interface-motion.md, the 2026-10-22 window look D):

- the root a bevel: the face fades from `#26282c` to `panel` over its top, as the windows;
- three wells on `track` with a `track_edge` hairline and radius 6: the top bar, the cards,
  the side panel. Fields inside a well sit on `panel`;
- the type filter is a segment track `[All | Poses | Anims]` (`skeldarPoseType_<key>`); the
  combo `skeldarPoseType` stays as the hidden model, so the remembered value and the old seams
  keep working;
- the size slider has a list glyph at its low end and a grid glyph at its high end;
- Mirror, Selected only, 1P upper body, At current time, Connect and In place are chips
  (checkable buttons, the `chip` role), not check boxes: the same names, `click()`,
  `isChecked()`, `setChecked()` and `clicked`;
- one orange per row: + Save on the bar, Apply in the details.

**Compact.** The top bar is one well row, 26 logical px tall. Margins 4 (the bar's padding 4),
the side panel its least width.

**A list at the smallest size.** At `look.CELL_MIN` (the slider's low end) the cards are rows
(`look.LIST_AT`, `look.rows`): `ROW_H` 40 logical px, `ROW_GAP` 2, the MARGIN round them. A row
holds the card's picture in a `ROW_THUMB` 32 px rounded square (an animation card plays it under
the mouse, as the grid's), its name, its character, its folder and a tag - «POSE» in
`accent_text`, «▶ 48» in the highlight blue, the objects card «OBJ» muted. Rows alternate a faint
face; the row under the mouse is `hover`, the picked one `card_active` with the accent outline.
No row grows under the mouse (the grid's zoom is for pictures). A press, a drag, the right
button and the middle-drag blend work on a row as on a card; the drag's ghost is the card's
picture.

## Not changed

Saving, applying, the paste options, the blend, every drop but the tree's place, the card grid
above the smallest size, the hover zoom there.

## Proof

Unit tests: the folder button's text, the popup opening and picking, a drag over the button
opening it and a release over a folder moving the card, the type segments driving the hidden
combo and the remembered value, the chips, the list rows' layout, hit, paint and play, the
smallest size switching to rows and back. An offscreen render of the window at 150 % in both
modes. Not seen in a GUI Maya.

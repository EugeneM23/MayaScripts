# SkeldarAnim hub: a skin of our own, and every button in its place

**Date:** 2026-09-28
**Ask:** «Давай попробуем для нашего плагина нарисовать кастомный красивый
интерфейс. За одно можно подумать над тем как сделать расположение кнопок
более красивым».

**Decided in the brainstorm (mockups shown, the animator picked):**

- **Style B, "our own"**: a dark charcoal panel, sections as rounded cards
  with a coloured icon chip, rounded buttons, ONE orange primary button per
  section, the palette as dots. Picked over A (Maya's greys, tidied) and C
  (a dense icon grid).
- **Scheme 3**: the accordion stays (several sections open at once — the
  2026-09-17 decision), the sections are grouped — **Scene** (Characters,
  Weapons, Connections), **Animation** (UE Bridge, Retarget), **Look**
  (Studio, Colour) — and a strip of icons at the top jumps to a section
  (expand + scroll). Picked over 1 (groups, no strip) and 2 (tabs, one
  section at a time).
- **Hotkeys and Update move into the header**: the keyboard icon lights while
  the hotkey map is on; the version chip is the installed commit and checks
  for an update on a click; a ⋮ menu holds Hotkey Editor and Check update.
- The workspaceControl stays (2026-09-17: «не нужно переделывать тип
  интерфейса»); the animator docks it as before.

## What was wrong, measured on the live hub before the change

Every section expanded and photographed with `widget.grab()`:

- four button colours with no rule (green Apply, blue Retarget/Next free/
  Check update, brown Restore, grey everything else); Studio's and Colour's
  status lines in a fixed-width font, the rest in the UI font; Studio and
  Colour at a fixed 300 px column while the rest stretch;
- no primary action: Add Character = Camera Setup, IMPORT = the two Exports;
- Retarget 296 px for one button and a paragraph, Hotkeys 271 px, Update
  272 px; instructions as paragraphs inside the panel;
- nine identical grey header bars.

## Measured before designing the mechanism

In a throwaway `workspaceControl` (`skeldarSkinProbe`, deleted after):

1. **A cmds control can live inside a Qt widget of ours.** The control's
   `QWidget` has a `QVBoxLayout`; a `QWidget` of ours added to it holds a
   `QScrollArea` → cards → a body `QWidget` with a named `QVBoxLayout`;
   `cmds.setParent(MQtUtil.fullName(getCppPointer(layout)))` then puts
   `cmds.columnLayout` and everything a builder makes into that body. Names,
   `exists`, `edit` and `query` work as before; the full path runs through
   the Qt objects (`skeldarSkinProbe|||||skProbeBodyLayout|...` — unnamed Qt
   objects are empty path parts, so every object of ours gets a name).
2. **Maya's controls are Qt subclasses a stylesheet reaches**: `QPushButton`
   (button, and `QmayaIconTextButton` / `QmayaIconTextRadioButton` — a
   checkable QPushButton), `QmayaOptionMenu` → `QComboBox`, `QmayaCheckBox`
   → `QCheckBox`, `QmayaField` → `QLineEdit` (also every float field),
   `QmayaListWidget` → `QListWidget`, `QmayaLabel` → `QLabel`, sliders
   `QSlider`. Layouts are plain `QWidget`s that paint nothing. A stylesheet
   on our root restyles all of them; `cmds.button(backgroundColor=)` is a
   palette, which the stylesheet overrides.
3. **Specificity bites**: a blanket `QFrame[skCard] QWidget {background:
   transparent}` outranked `QPushButton[skRole=primary]` and emptied every
   field and the primary button. No blanket rules; `QLabel` gets no
   background rule either — the colour slider's swatch
   (`QmayaColorSliderLabel`) is a QLabel and went invisible.
4. **`QmayaRadioButton` keeps its dot** under `::indicator {width: 0}`;
   `iconTextRadioButton` (a checkable QPushButton) makes a clean segment.
5. **A cmds text moved into our card header by Qt keeps working**:
   `cmds.text(name, e=True, label=...)` lands on it after the move.
6. **Qt properties, not wrapper methods**: `wrapInstance(ptr, QLabel)` hands
   back the cached `QWidget` wrapper when one exists, so `setWordWrap` /
   `setIcon` raise AttributeError. `setProperty("wordWrap", False)`,
   `setProperty("icon", QIcon)`, `setProperty("iconSize", QSize)` work on
   any wrapper. An icon set that way survives `cmds.button(e=True, label=)`.
7. **Stylesheet pixels are physical here**: `devicePixelRatio` 1.0, logical
   DPI 144, the UI font 16 px (Maya scales fonts itself). Every px in our
   stylesheet and every icon size is multiplied by `mayaDpiSetting -q
   -realScaleValue` (1.5 on this machine).
8. `PySide6.QtSvg` ships with Maya 2027 (6.8.3): icons are SVG text rendered
   by `QSvgRenderer`.

## Architecture

Three new modules in `SkeldarAnim/` (payload rows), `maya_hub.py` reworked,
every builder given marks and a better arrangement.

### `maya_hubstyle.py` — stdlib only, pure

- `TOKENS`: the palette (panel `#1f2023`, card `#2a2c30`, field `#1b1c1f`,
  line `#45474d`, text `#e4e4e6` / `#c9cacf` / muted `#9a9ca3`, accent
  `#e07a36` with `#2a1405` on it, accent tint `#3a2a1f` / `#f0a26b`, danger
  `#e39a93`, status `#24262a` / `#a9abb1`, ok `#8fd19a`).
- `GROUPS`: `(key, label, icon colour, chip colour)` — scene orange,
  animation blue, look violet, settings (header-only).
- `stylesheet(scale)`: the whole QSS, px multiplied by `scale`, role
  selectors on `skRole`.
- **Marks**: `mark(name, role, icon=None, layout=False)` records a control's
  role and returns the name, so a builder writes
  `hubstyle.mark(cmds.button(...), "primary", "plus")`; `swatch(name, rgb)`
  records a colour chip; `take_marks()` hands them over and clears. Roles:
  `primary`, `danger`, `tool` (small square icon button), `chip` (a
  checkBox as a pill), `segments` (a row layout) / `segment` (an
  iconTextRadioButton), `status`, `note`, `context`, `subtitle` (moved into
  the card header), `swatch`, `swatchonly` (a colorSliderGrp with only its
  swatch shown). A mark costs nothing when the hub is not skinned.
- `hex_of(rgb)`.

### `maya_hubicons.py` — stdlib only, pure

The Tabler outline icons we use (MIT, notice in the module): user, sword,
hand-grab, transfer-in, arrows-exchange, bulb, palette, keyboard,
dots-vertical, chevron-down/right, plus, camera, trash, folder, brush,
download, upload, refresh, check, x, link, unlink, arrow-back-up.
`svg(name, colour)` → the SVG text. No PNG is drawn (the 2026-09-17 rule
was about shelf icons; nothing goes on the shelf).

### `maya_hubqt.py` — the Qt layer

PySide6, else PySide2; `available()` is False without Qt or
`maya.OpenMayaUI`, or in batch. Two seams, replaced by the tests:
`find(name, layout=False)` (MQtUtil → a QWidget wrapper) and `path_of(qt
layout)` (MQtUtil.fullName). Widgets of ours:

- **Header**: the "SA" mark, `SkeldarAnim`, the hotkeys button (checkable,
  keyboard icon), the version chip (text = installed short commit, state
  `ok`/`new`/none colours it), the ⋮ menu (Check update, Hotkey Editor…,
  Classic look); under it a **message line** (wraps, a × hides it), shown
  only while it holds text.
- **Jump strip**: one icon button per card section, the group's colour,
  tooltip = the label; click → `maya_hub.expand(key)`.
- **Group label**, and a **Card** per section: a clickable header (icon
  chip, title, the moved subtitle, chevron) and a body whose named layout is
  where the builder runs. Collapse hides the body; the header click calls
  back so the optionVar is remembered.
- `apply_marks(marks, card)`: roles as the `skRole` property, icons as
  `icon`/`iconSize` properties (coloured for the role), swatches as a
  per-widget stylesheet, subtitles moved into `card`'s header with word
  wrap off and an Ignored width policy (a long one clips, never widens).
- `icon(name, colour, size)`: SVG → QIcon.

### `maya_hub.py`

`SECTIONS` gains `group` and `icon`, in the new order: characters, weapons,
connections, uebridge, retarget, studio, colour, hotkeys, update (Weapons
still after Characters). `build()`:

- **skinned** when `maya_hubqt.available()` and the optionVar
  `skeldarAnimHub_classic` is not 1: root widget into the control's layout,
  header, message, strip, then per group a label and per card section a
  Card, its builder run into the body, its marks applied to it; the
  stylesheet set on the root last. The settings sections are the header,
  never cards. A skin that fails as a whole is deleted at once and the
  classic hub is built instead, the traceback printed.
- **classic** otherwise: today's accordion of frameLayouts in the new order,
  every section including Hotkeys and Update, plus a "New look" button at
  the top when Qt is there. Marks are taken and dropped.

`expand(key)`, `scroll_to(key)`, `rebuild()`, `is_open()` work in both;
in the skin a settings key expands nothing. New: `say(message, state=None)`
(the header's message line; `state` recolours the version chip),
`paint_hotkeys(active)`, `set_classic(on)` (deferred rebuild — a rebuild
from inside a button that it deletes must not run in that button's call).

### Tools, the few hooks

- `maya_hotkeys.paint(active)` also calls `maya_hub.paint_hotkeys` — only
  if `maya_hub` is already in `sys.modules` (no import for a paint).
- `maya_update._status(message, state=None)` also calls `maya_hub.say` the
  same way; "Up to date" passes `state="ok"`, the post-install message
  `"new"`.
- Every builder: marks, and the arrangement below.

## Each section

- **Characters**: the character line becomes the card's subtitle; the
  dropdown full width (its label dropped — the card says Characters); a row
  of eight palette dots (a click sets the swatch), the swatch itself
  (colour chooser on a click), a brush tool button = Recolour; **Add
  character** primary (plus), Camera setup (camera); status.
- **Weapons**: dropdown + folder tool button (a file dialog fills the FBX
  field); the FBX field; **Add** primary + Remove danger (trash) in one row;
  Rotate / Translate fields; the dots, swatch and brush as for characters;
  status.
- **Connections**: the header line as context; three rows — label,
  segments (`Free | Weapon`, `World | Hand R | Hand L`), a check tool button
  = Apply this row; **Apply all** primary; Bake across (link) + Release
  (unlink) in one row; status. `menus()` / `set_menus()` read and write the
  segments (`iconTextRadioCollection`), `_menu_changed` is their onCommand —
  the pure halves unchanged.
- **UE Bridge**: the connection line as subtitle; project dropdown + refresh
  tool button; the search field (placeholder "search name or folder"); the
  list; the import mode as segments `Rig | New rig | Skeleton` (the long
  explanation as the tooltip); the timeline check; **Import** primary
  (download); Export FBX… (upload) + Export to uasset in one row; status.
  `import_mode()` reads the collection; `mode_for` unchanged.
- **Retarget**: one short note, the full text as the button's tooltip;
  **Retarget** primary; status.
- **Studio**: Look and Quality side by side; the ten checks as chips, two a
  row; Brightness and Rotate; **Apply look** primary + Restore
  (arrow-back-up) in one row; status in the UI font. No fixed widths.
- **Colour**: the note; the eight colours as rounded swatches; custom
  swatch + Paint + Next free in one row; "taken" as the subtitle; status.
- **Hotkeys / Update** (classic only): their panels as today, marked.

## Not built

Axis-coloured X/Y/Z labels on the grip fields (a floatFieldGrp cannot
colour one field; three separate fields would change the control every
caller reads). A selection ring on the palette dots (the swatch beside them
shows the choice). Status colour by tone (the texts carry no tone).

## Testing

- `tests/test_hubstyle.py`, `tests/test_hubicons.py`: pure.
- `tests/test_hubqt.py`: offscreen Qt (mayapy's PySide6) with the two seams
  faked: header/strip/cards built, collapse, marks → properties and icons,
  subtitle moved, message line shown and hidden, hotkeys paint, chip.
- `tests/test_hub.py`: the new order; skinned when available, classic when
  not or when asked, a failing skin falling back; expand/scroll in both.
- The section tests: the new controls (segments, dots, rows), the marks.
- **Live**: `docs/superpowers/plans/verify_hub_skin.py` against the
  INSTALLED copy in the animator's Maya (UI only, the scene untouched):
  the structure, every card's named controls inside its body, the marks on
  the widgets, the stylesheet, the content no wider than the scroll area,
  subtitles live, the strip's expand + scroll, collapse memory, classic ↔
  skin round trip, hotkeys paint, the chip = the installed record; photos
  at three widths.

# Skill bar: F1 the Time Bar, F2-F12 pages of skills (2026-10-19)

## The ask

The animator: «Давай реализуем панель скилов для нашего интерфейса подобно панели из видео игр как в
lineage2. суть такая - F1 F2 F3 и так далее до 12 становятся хоткеями переключения полок со скилами.
Скилы это полка с клетками каждая клетка это какая-то функция или меню. В скил мы можем поместить
скрипты, методы как стандартные в мае так и из нашего плагина. F1 - включает таймслайдер F2 - первую
панель скилов F3 - вторую и тд. Посути это все одна меню таймсладер только с возможностью
переключаться на скилы. В виде скилов я бы хотел иметь возможно загружать наши риги и скелеты, позы из
библеотеки или любой инструмент или раздел. Панель скилов можно настроить и сделать в 2 - 3 - 4 ряда
по желанию.»

Mockups first (https://claude.ai/artifact/8Njhv7zm48qyKasTVdbfRP): A swap in place, B skills over the
timeline, C a compact hotbar. **Chosen: A.** Then, asked:

| question | answer |
|---|---|
| where F1-F12 apply | **our hotkey map only** (the SkeldarAnim set, like alt+q); Maya's own F-keys untouched in Maya's set |
| the bar hidden at the bottom edge, F3 pressed | **it comes out on page 3** |
| how skills get into cells | **all four**: the library drawer, a drag from our panels, Script Editor text, Maya shelf buttons |
| where the pages are kept | **a file per user**, `<userAppDir>/SkeldarSkills/skills.json` |

## What it is

The Time Bar's strip gains a thin **page row** along its top: twelve tabs, `F1 Time`, `F2 <name>` ...
`F12`. F1 shows the Time Bar as it is. F2-F12 replace the two time rows with that page's **cells**. The
page row, the strip's look, its burst out of the bottom edge and its menus are the Time Bar's.

- **Rows**: 2, 3 or 4 (one setting for every page, remembered in the file). At 2 rows a skill page is as
  tall as the time rows, so F1 and F2 do not jump; 3 and 4 make the bar taller.
- **Columns**: as many cells as fit the width. A cell's place is (row, column), so a narrower bar hides
  the cells past its edge and keeps them.
- **Click a cell**: its skill runs. **Right click**: Run, Rename, Change skill (the library), Clear,
  Rows ▸ 2 / 3 / 4, Skill library. **Click an empty cell**: the library opens. **Drag a cell**: onto
  another cell (swap), onto a page tab (to that page's first free cell).
- **A page tab**: click shows it; right click: Rename page, Clear page, Rows ▸, Skill library.

## The skills

An item is a small dict, stored as it is:

| kind | fields | running it |
|---|---|---|
| `section` | `key` | the radial menu's road: the section's window by the cursor |
| `cmd` | `key` (a hotkey row of ours) | `maya_hotkeys.run`; a two-step row (Aim, Knot Offset) lit «wait» and its Finish popup, as the radial menu |
| `character` | `model`, `char` (`rig` / `skeleton`) | Animation Setup's Add Character for that catalog row |
| `card` | `path` (relative to the Pose Library root) | the card onto the selection: a pose, or an animation with the library's remembered paste options |
| `weapon` | `key` | Inventory's Equip with that weapon into the picked hand |
| `maya` | `command` (a runTimeCommand) | `mel.eval(command)` |
| `script` | `lang` (`python` / `mel`), `code`, `label` | run in Maya's own interpreter (`__main__` for Python) |
| `shelf` | `lang`, `code`, `label`, `image` | a copy of a Maya shelf button, run as a script |

Every item may carry `label`, shown in place of its own name. An item whose thing is gone (a card
deleted, a section renamed) says so on a run and keeps its cell.

## Getting skills into cells

1. **The library drawer** - a window standing over the bar, as wide as it: a search field, categories
   `[All | Sections | Tools | Characters | Poses | Weapons | Maya | Shelves | Scripts]`, every item a
   chip with its picture; a chip dragged onto a cell (or a page tab) puts it there. Maya: the
   runTimeCommands (searched; a short list of the animation ones by default). Shelves: every button of
   every Maya shelf, its own icon. Scripts: «From the Script Editor» (the current tab's selected text,
   else its whole text, its language).
2. **Our panels' drags**: a portrait (Animation Setup's grid, in the kind it shows), a Pose Library card,
   an Inventory weapon tile, a hub rail icon - dropped on a cell or a page tab. While such a drag is
   over the bar, the cell under it is lit and the ghost says «skill F3 · row 1, cell 4».
3. **Text**: any text dropped on the bar (Script Editor text dragged out) is a script; a Maya shelf
   button's own drag, when it carries its command as text, likewise.
4. **Right click on an empty cell → Script from the Script Editor**.

## F1-F12

Hotkey rows `skills.page1` .. `skills.page12` (category Skill Bar), bound to F1-F12 with no modifier
in `DEFAULT_KEYS` (version 8) - our set only. A press:

- shows that page (the cells pop in from its tab);
- the bar hidden at the bottom edge: it comes out on that page from the cursor's x (as a key set brings
  it), and hides again as usual;
- the Time Bar off (Maya's slider): «The skill bar lives in the Time Bar - ⋮ -> Time bar».

## Motion (docs/interface-motion.md)

- A page shown: its cells pop in nearest the pressed tab first (`maya_timebar.look.popping`,
  `burst_delay`); F1's rows come in the same way; nothing folds out (the data is instant).
- A cell: hover 110 ms lift +10 % and the accent glow; press flash 120 ms; a skill run flashes a round
  added-light glow on the cell (the key set's, 520 ms). A two-step skill waiting is filled accent.
- The page row's tabs: hover and flash as the strip's pills; the current tab lit `card_active` with a
  1.5 px accent outline.
- The drawer opens out of the point it was asked from (unroll, then its chips pop in nearest first)
  and folds back into it.
- In the bottom edge's burst the page row and the cells pop like every other part.
- ⋮ -> Interface animations off: all at once.

## Modules

`SkeldarAnim/maya_skillbar/` (a payload row):

| module | what | imports |
|---|---|---|
| `look.py` | the model (pages, cells, rows, items), its JSON, the grid's geometry and hits, labels, the drop caption | stdlib only (a test pins it) |
| `store.py` | the file: read (defaults on first use, a broken file kept aside), atomic write | stdlib only |
| `run.py` | running an item; an item's label and picture source; the Script Editor's text | cmds, lazily the plugin |
| `sources.py` | the library's entries | cmds, lazily the plugin |
| `grid.py` | Qt: the page row, the cells, the drag of a cell, the drop target other panels ask | Qt |
| `library.py` | Qt: the drawer | Qt |
| `__init__.py` | `page(n)` for the hotkeys, `aim` / `drop` / `light` for other panels' drags | - |

The Strip (`maya_timebar.bar`) holds the page row and the grid; its two rows go into one box shown on
F1. The strip talks to the skills through its link (`scene.py` forwards to `maya_skillbar`); a fake
link without them gets an in-memory model.

## Proof

- Unit tests: the model, its JSON and defaults, the geometry and hits, the store, running each kind on
  fake Maya modules, the strip offscreen with the page row and the grid (switch, hover, click, the
  right-click rows, a drop, the text drop), the hotkey rows and keys.
- A filmstrip: `docs/superpowers/plans/render_skill_bar.py` -> `skill_bar.png` (F1, F2 at 2/3/4 rows, a
  page popping in, the drawer).
- Not seen in a GUI Maya until the animator tries it.

## Not built

A skill's own hotkey (1-0 on a page), a cooldown look, sharing pages through Shared, per-page rows,
icons drawn for Maya's runtime commands (they show their name's first letters).

# Radial menu: a section or a function under the cursor (2026-10-15)

The animator: «Давай реализуем радиальное меню для нашего плагина. я зажимаю какую-то клавишу появляется
радиальное меню и я могу выбирать то что в этом меню. В само меню можно поместить как и раздел так и
отдельную функцию раздела. Если мы выбираем раздел то открывается попап раздела (если он уже был открыт
где-то то он должен открыться в новом месте возле курсора мышки). Выбор какого-то инструмента вызовет
действие этого инструмента. Если это двухэтапная кнопка например AIM то у нас на экране появится попап
финиша действия.»

Asked, all four the recommendation: **hold and release** (a marking menu: hold the key, move toward a slot,
release; a click works too); **alt+q** bound in the SkeldarAnim hotkey set; **an editor card in the hub**
(Settings group) with a default set; **8 slots, one ring, no submenus**.

## What it is

- `SkeldarAnim/maya_radial_rules.py` (stdlib, pure): 8 slots clockwise from north (`SLOTS`, compass names),
  `slot_at(dx, dy, dead)` - the slot a cursor offset points at, None inside the dead zone or on an empty slot;
  an item is `"section:<key>"` or `"cmd:<hotkey row>"` (`parse`, `encode`/`decode` of the optionVar
  `skeldarRadialSlots`, a JSON list of 8, a broken one -> the defaults); `DEFAULTS`; `TWO_STEP` - the rows that
  wait for a second press (`tools.knot_offset`, `tools.aim`) and how to ask whether they wait; `release_action`
  (pure: a release over a slot runs it, a quick tap in the centre keeps the menu open for a click, anything else
  closes).
- `SkeldarAnim/maya_radial.py` (Qt + cmds):
  - `press()` / `release()` - the hotkey rows `radial.press` / `radial.release`. A press while the menu is up
    (key auto-repeat) does nothing. The press reads which keys are down (Win32 `GetAsyncKeyState`) and a 16 ms
    timer watches them: the release is the moment they are all up, whatever Maya's release command does (it may
    not reach Maya while another window holds focus, and auto-repeat may send one early - a release while the
    key is still down is ignored).
  - The overlay: a frameless, translucent `Qt.Tool` window over Maya's main window, centred on the cursor,
    never taking focus; 8 pills (icon + label) on a ring, the one the cursor points at lit in the accent, a
    line from the centre toward the cursor. A slot whose two-step tool waits reads «Finish <label>». Esc or the
    right button closes it (Esc polled too).
  - Running an item, after the overlay is gone: a function - `maya_hotkeys.run(row)`; a section - its popup
    opened in the viewport under the cursor, its top-left by the cursor (`maya_hubpop.open_at`; a popup already
    open anywhere is closed and opened here); a header-only section - the hub on it.
  - The finish popup: after a two-step row, while it waits, a small frameless window by the cursor - «<Tool>
    waiting», **Finish** (primary; runs the row again) and ✕ (closes the popup, the waiting tool stays for the
    card). It closes itself when nothing waits any more (300 ms poll), and shows the line a refused Finish said.
  - The editor: hub section `radial` «Radial Menu», Settings, Tabler icon `aperture`. Three rows of three: the 8
    slots around a centre telling the key; a slot's left button opens its menu (Empty, Sections ▸, one submenu
    per hotkey category), its right button clears it; Reset to defaults; Bind alt+q now (into the current hotkey
    set, only when it is the SkeldarAnim one - otherwise it says to switch the hotkey map on).
- `maya_hotkeys`: rows `radial.press` / `radial.release` (category «Radial Menu»); a `DEFAULT_KEYS` row may
  carry a release row; `("q", alt, "radial.press", "radial.release")`; `DEFAULT_KEYS_VERSION` 7.
- `maya_hubpop.open_at(key, point)`: the model panel whose GL rectangle holds the point, else the active one.

## Not built

Submenus, more than 8 slots, per-character menus, a press-and-hold gesture for the mouse.

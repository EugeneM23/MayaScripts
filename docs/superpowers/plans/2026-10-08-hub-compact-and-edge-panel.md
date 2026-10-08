# The Hub, Compact (B) and as an Edge Panel - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** make the SkeldarAnim hub's skin dense (variant B: one header row, one message line, compact cards, 10-row resizable file lists) and let the hub live in a panel that slides out of the left screen edge.

**Architecture:** the look stays data in `maya_hubstyle` (heights `H`, a status relay `tell`, list-row arithmetic), the Qt layer `maya_hubqt` reads new mark roles (`status` hidden and relayed, `note` -> tooltip, `context` hidden, `grip` -> a list height grip). Each section builder is re-arranged once for both hubs, reporting through `hubstyle.tell`. The edge panel is a pure rules module (`maya_edgerules`), a Qt module (`maya_hubedge`: a frameless Tool host, a 2 px sensor, a controller), `maya_hub`'s second home for the skin, and a startup plug-in the installer loads and autoloads.

**Tech Stack:** Maya 2027 `maya.cmds`, PySide6 6.8.3 (via `maya_hubqt.qt()`), Maya Python API 2.0 (the plug-in), stdlib `unittest` under `mayapy`.

**Spec:** `docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md` (read it first; it says why). Mockups: `docs/superpowers/mockups/hub-compact-all-cards-v2.html`.

## Global Constraints

- Run tests with Maya's interpreter, never `python` (the Store stub HANGS): from the repo root, in PowerShell, `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. A single module: `... -m unittest tests.test_hubstyle -v`. Never `2>&1` on mayapy in PowerShell.
- Every control NAME, callback, `refresh`, hotkey row and opener keeps working: this is arrangement, roles and a host, never a rename of an existing control.
- `maya_hubstyle`, `maya_edgerules`, `maya_charlook`, `maya_invlook` stay **stdlib only** (subprocess tests pin it for some; keep it for all).
- Qt pixels are PHYSICAL in Maya (devicePixelRatio 1.0); every logical px goes through `hubstyle.px(n, scale)` / `* scale`. `cmds` heights are LOGICAL.
- Never hold a wrapper of a Maya-owned widget across `processEvents()`; find it again by name (CLAUDE.md trap 135/148).
- Never call `.grab()` on Maya's widgets (trap 134).
- Code style: match the file you are in - the comment density and the long docstrings that say WHY (dates, the animator's words in Russian quotes where the spec has them).
- Python source edits through the Write/Edit tools; never PowerShell here-strings (trap 101), never Bash heredocs with backslashes (trap 198).
- Commit after each task. Stage ONLY the task's files (other sessions commit to this branch: `git add <paths>`, never `git add -A`). Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; write the message to a file and `git commit -F <file>`.
- Work happens in the worktree created for this plan (see "Before Task 1"); the main checkout is the animator's.
- Heights in the skin (spec): root margins 3, gaps 3, card padding 5/4/5/5, body gap 4, header chip 18, `rowSpacing` 3, buttons 24, small buttons/segments 22, fields 20. Classic hub keeps its own numbers through `hubstyle.pick(skin, classic)`.
- Lists: 10 rows by default, 5..40 by the grip, remembered in `skeldarAnimHub_listRows_<listName>`. Classic lists keep 300 / 150 px and get no grip.
- Edge: `skeldarAnimHub_edge` (int, default 0), `skeldarAnimHub_edgeWidth` (logical, default 360, 280..700), dwell 100 ms, hide 350 ms, retry 150 ms, slide in 180 / out 150 ms, sensor 2 physical px, width grip 5 logical px.

---

## Before Task 1: the worktree

- [ ] Create the worktree from the current branch head (`feature/overrig-picker`, which holds the spec commit):

```bash
cd "C:/!!!Work/MayaScripts"
git worktree add -b feature/hub-compact "C:/!!!Work/MayaScripts-hubcompact" HEAD
```

- [ ] Run the whole suite once in the worktree and note the count (expect ~4650, all passing) so later failures are yours:

```powershell
Set-Location 'C:\!!!Work\MayaScripts-hubcompact'; $env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . 
```

All paths below are relative to the worktree root.

---

### Task 1: The look as data - heights, the status relay, list rows, new roles, icons

**Files:**
- Modify: `SkeldarAnim/maya_hubstyle.py`
- Modify: `SkeldarAnim/maya_hubicons.py`
- Test: `tests/test_hubstyle.py`, `tests/test_hubicons.py`

**Interfaces:**
- Produces (used by every later task):
  - `hubstyle.H` = `{"button": 24, "small": 22, "segment": 22, "field": 20}`
  - `hubstyle.height(kind, classic) -> int` (skin: `H[kind]`, else `classic`)
  - `hubstyle.row_spacing(classic=6) -> int` (skin 3)
  - `hubstyle.Mark` namedtuple `name role icon layout colour target` (`target` defaults to None)
  - `hubstyle.grip(name, list_name) -> name` (records a `grip` mark whose `target` is the list)
  - `hubstyle.listen(fn) -> fn`, `hubstyle.unlisten(fn)`, `hubstyle.tell(control, text, viewport=False) -> text`; a listener is called `fn(control, text, viewport)`
  - `hubstyle.LIST_VAR = "skeldarAnimHub_listRows_{0}"`, `LIST_ROWS = 10`, `LIST_MIN = 5`, `LIST_MAX = 40`
  - `hubstyle.clamp_rows(rows) -> int`, `hubstyle.rows_after_drag(start_rows, dy, row_px) -> int`, `hubstyle.list_height(rows, row_px, frame_px) -> int`
  - roles `"grip"` and `"dot"` in `ROLES`
  - icons `"pin"`, `"pinned"`, `"clock"`

- [ ] **Step 1: Write the failing tests** - append to `tests/test_hubstyle.py`:

```python
class Compact(unittest.TestCase):
    """2026-10-08, variant B: the builders' heights, the relay, the lists."""

    def tearDown(self):
        style.set_skinning(False)
        style.take_marks()
        for fn in list(style._LISTENERS):
            style.unlisten(fn)

    def test_heights_are_the_compact_ones_in_the_skin_only(self):
        self.assertEqual(style.height("button", 32), 32)
        style.set_skinning(True)
        self.assertEqual(style.height("button", 32), 24)
        self.assertEqual(style.height("small", 28), 22)
        self.assertEqual(style.height("segment", 22), 22)
        self.assertEqual(style.height("field", 24), 20)

    def test_row_spacing(self):
        self.assertEqual(style.row_spacing(), 6)
        self.assertEqual(style.row_spacing(4), 4)
        style.set_skinning(True)
        self.assertEqual(style.row_spacing(4), 3)

    def test_a_grip_mark_names_its_list(self):
        self.assertEqual(style.grip("aGrip", "aList"), "aGrip")
        mark = style.take_marks()[0]
        self.assertEqual((mark.name, mark.role, mark.target),
                         ("aGrip", "grip", "aList"))

    def test_an_ordinary_mark_has_no_target(self):
        style.mark("b", "primary", "plus")
        self.assertIsNone(style.take_marks()[0].target)

    def test_new_roles(self):
        self.assertIn("grip", style.ROLES)
        self.assertIn("dot", style.ROLES)

    def test_tell_reaches_every_listener_and_answers_the_text(self):
        heard = []
        style.listen(lambda c, t, v: heard.append((c, t, v)))
        self.assertEqual(style.tell("status1", "done", viewport=True), "done")
        self.assertEqual(heard, [("status1", "done", True)])

    def test_tell_without_a_listener_is_quiet(self):
        self.assertEqual(style.tell("status1", "done"), "done")

    def test_a_listener_that_raises_costs_only_itself(self):
        heard = []

        def bad(*_a):
            raise RuntimeError("no")
        style.listen(bad)
        style.listen(lambda c, t, v: heard.append(t))
        style.tell("s", "x")
        self.assertEqual(heard, ["x"])

    def test_unlisten(self):
        heard = []
        fn = style.listen(lambda c, t, v: heard.append(t))
        style.unlisten(fn)
        style.unlisten(fn)                       # twice is harmless
        style.tell("s", "x")
        self.assertEqual(heard, [])

    def test_rows_clamp(self):
        self.assertEqual(style.clamp_rows(2), 5)
        self.assertEqual(style.clamp_rows(10.4), 10)
        self.assertEqual(style.clamp_rows(99), 40)

    def test_rows_after_a_drag_move_by_whole_rows(self):
        self.assertEqual(style.rows_after_drag(10, 0, 16), 10)
        self.assertEqual(style.rows_after_drag(10, 7, 16), 10)   # under half
        self.assertEqual(style.rows_after_drag(10, 9, 16), 11)
        self.assertEqual(style.rows_after_drag(10, -48, 16), 7)
        self.assertEqual(style.rows_after_drag(10, -999, 16), 5)
        self.assertEqual(style.rows_after_drag(10, 50, 0), 10)   # no row size

    def test_list_height(self):
        self.assertEqual(style.list_height(10, 16, 6), 166)

    def test_the_sheet_has_the_dot_and_grip_rules(self):
        sheet = style.stylesheet(1.0)
        self.assertIn('QLabel[skRole="dot"]', sheet)
        self.assertIn('QWidget[skRole="grip"]', sheet)
```

And to `tests/test_hubicons.py`:

```python
    def test_the_edge_panel_icons(self):
        for name in ("pin", "pinned", "clock"):
            self.assertIn("<path", icons.svg(name))
```

(Use the module alias the file already imports; check its first lines.)

- [ ] **Step 2: Run them, expect failures**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hubstyle tests.test_hubicons -v`
Expected: FAIL / ERROR (`height`, `grip`, `tell`, … not defined; KeyError for the icons).

- [ ] **Step 3: Implement in `SkeldarAnim/maya_hubstyle.py`**

1. Add `"grip"` and `"dot"` to `ROLES` with comments: `"grip",  # a placeholder under a list the skin turns into a height grip (2026-10-08)` and `"dot",  # a one-glyph state mark (● / ○) before a dropdown (2026-10-08)`.
2. Replace the `Mark` namedtuple and the three recorders:

```python
Mark = collections.namedtuple("Mark", "name role icon layout colour target",
                              defaults=(None,))


def mark(name, role, icon=None, layout=False):
    """Record that control `name` plays `role`; return `name`, so a creation
    call can be wrapped in place."""
    if role not in ROLES:
        raise ValueError("unknown hub role '{0}'".format(role))
    _MARKS.append(Mark(name, role, icon, bool(layout), None))
    return name


def swatch(name, rgb):
    """Record a colour chip: a button the skin paints `rgb`, rounded."""
    _MARKS.append(Mark(name, "swatch", None, False, hex_of(rgb)))
    return name


def grip(name, list_name):
    """Record that placeholder `name` (8 px under a list) is that list's
    height grip (2026-10-08, «нужно сделать возможность раздвигать или
    сдвигать окошко по высоте»); the skin draws and drives it."""
    _MARKS.append(Mark(name, "grip", None, False, None, list_name))
    return name
```

3. After `tool_width`, add:

```python
# ------------------------------------------------------------- compact (B)

#  The compact skin (2026-10-08, «сделаем его компактным»; variant B of the
#  brainstorm): the builders' control heights, logical px. The classic hub
#  keeps the numbers each builder passes as `classic`.
H = {"button": 24, "small": 22, "segment": 22, "field": 20}


def height(kind, classic):
    """A control's height: the compact one in the skin, `classic` otherwise."""
    return pick(H[kind], classic)


def row_spacing(classic=6):
    """A builder's column rowSpacing: 3 in the skin, `classic` otherwise."""
    return pick(3, classic)


# -------------------------------------------------------- the status relay

#  One message line for the whole hub (2026-10-08): a section's status writer
#  still writes its own control, and `tell`s the hub too. The skin listens
#  (maya_hubqt.Skin) and shows the text on its line with the card's icon; the
#  classic hub listens to nothing and keeps the status lines in the cards.
_LISTENERS = []


def listen(fn):
    """`fn(control, text, viewport)` is called by every `tell`; returns fn."""
    if fn not in _LISTENERS:
        _LISTENERS.append(fn)
    return fn


def unlisten(fn):
    if fn in _LISTENERS:
        _LISTENERS.remove(fn)


def tell(control, text, viewport=False):
    """Section status control `control` now says `text`. `viewport`: the
    writer shows it in the viewport itself (an inViewMessage), so the edge
    panel need not. Never raises; answers `text`."""
    for fn in list(_LISTENERS):
        try:
            fn(control, text, viewport)
        except Exception:                                    # noqa: BLE001
            pass
    return text


# --------------------------------------------------------------- the lists

#  The file lists (the animations, Shared): 10 rows by default, 5..40 by the
#  grip, remembered per list (2026-10-08, «хотя бы 10 ... раздвигать или
#  сдвигать окошко по высоте»).
LIST_VAR = "skeldarAnimHub_listRows_{0}"
LIST_ROWS = 10
LIST_MIN = 5
LIST_MAX = 40


def clamp_rows(rows):
    return int(max(LIST_MIN, min(LIST_MAX, int(round(rows)))))


def rows_after_drag(start_rows, dy, row_px):
    """The rows a list shows after the grip moved `dy` px from where the
    press found it showing `start_rows`, whole rows, clamped. Pure."""
    if not row_px or row_px <= 0:
        return clamp_rows(start_rows)
    return clamp_rows(start_rows + float(dy) / float(row_px))


def list_height(rows, row_px, frame_px):
    """A list's height showing `rows` rows of `row_px`, plus its frame."""
    return int(round(rows * row_px + frame_px))
```

4. Stylesheet `_SHEET` edits (B paddings and the two new roles):
   - `QPushButton { ... padding: {p3}px {p8}px; ...}` -> `padding: {p2}px {p6}px;`
   - `QComboBox { ... padding: {p3}px {p8}px; ...}` -> `padding: {p1}px {p6}px;`
   - `QLineEdit { ... padding: {p2}px {p6}px; ...}` -> `padding: {p1}px {p6}px;`
   - `QCheckBox[skRole="chip"] { ... padding: {p3}px {p10}px; ...}` -> `padding: {p2}px {p8}px;`
   - `QToolButton[skRole="headbtn"] { ... padding: {p3}px; }` -> `padding: {p2}px;`
   - `QToolButton[skRole="jump"] { ... padding: {p3}px; }` -> `padding: {p1}px;`
   - add before `QScrollBar:vertical`:

```
QLabel[skRole="dot"] {{ color: {faint}; }}
QWidget[skRole="grip"] {{ background: transparent; border-radius: {r3}px; }}
QWidget[skRole="grip"]:hover {{ background: {hover}; }}
QLabel[skRole="messageicon"] {{ background: transparent; }}
```

`{p1}` needs no change in `stylesheet()`: `p1` is already produced by the loop (n in 1, 2, 3, ...).

5. Update the module docstring's first paragraph with one line: `2026-10-08: compact (variant B) - H, the status relay, the list rows; spec docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md`.

- [ ] **Step 4: Icons** - in `SkeldarAnim/maya_hubicons.py` add to `ICONS` (Tabler 3.19 outline, verbatim):

```python
    "pin": (
        "M15 4.5l-4 4l-4 1.5l-1.5 1.5l7 7l1.5 -1.5l1.5 -4l4 -4",
        "M9 15l-4.5 4.5",
        "M14.5 4l5.5 5.5",
    ),
    "pinned": (
        "M9 4v6l-2 4v2h10v-2l-2 -4v-6",
        "M12 16l0 5",
        "M8 4l8 0",
    ),
    "clock": (
        "M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0",
        "M12 7v5l3 3",
    ),
```

If `tests/test_hubicons.py` pins the icon COUNT, raise it by 3.

- [ ] **Step 5: Run the two modules, expect PASS; then the whole suite** (the sheet text changed: a test that pins a padding string fails - update it to the new value, nothing else).

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_hubstyle.py SkeldarAnim/maya_hubicons.py tests/test_hubstyle.py tests/test_hubicons.py
git commit -F <msgfile>   # "feat(hub): compact heights, a status relay, list rows and the grip/dot roles"
```

---

### Task 2: The skin's frame - one header row, the message line with a source, compact cards, the group stripe

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`Card.__init__`, `_frame_class`, `Skin.__init__`, `_build_header`, `_build_message`, `add_jump`, `say`, `set_state`, `set_version`, `destroy`, new `paint_edge`, `set_edge_mode`, `_told`)
- Test: `tests/test_hubqt.py`

**Interfaces:**
- Consumes: Task 1 (`hubstyle.listen/unlisten`, icons `pin`/`pinned`).
- Produces:
  - `Skin.jumps[key]` are QToolButtons in the HEADER row (`self.jump_row`, a QHBoxLayout named `skeldarHubJumpRow`); there is no `self.strip`.
  - `Skin.version` is GONE. `Skin.set_version(text, tooltip, state=None)` and `Skin.set_state(state)` paint the `update` jump (tooltip; icon colour: `"new"` -> accent, `"ok"` -> `ok`, else its group colour).
  - `Skin.pin` (checkable QToolButton `skeldarHubPin`, hidden until `set_edge_mode(True)`), its click calls back `"pin"` with the checked state.
  - `Skin.edge_action` (checkable menu row "Edge panel", callback `"edge"` with the new state), `Skin.paint_edge(on)` (row checked, no callback), `Skin.set_edge_mode(on)` (pin shown/hidden + `paint_edge`).
  - `Skin.say(text, state=None, source=None)`: `source` a card key -> that card's icon at the line's left.
  - `Skin._told(control, text, viewport)`: the relay listener; registered in `__init__`, removed in `destroy`; calls back `"told"` with `(key, text, viewport)` after showing.
  - `Card(key, label, icon_name, colour, chip, scale, collapsed=False, on_toggle=None, motion=None)` unchanged signature; new attributes `card.icon_name`, `card.colour`, `card.status_controls` (a set of control names), method `card.add_hint(text)`.
  - `CardFrame.stripe` (a "#rrggbb" or None) painted as a 3 logical px bar down the left edge, inside the rounded face.

- [ ] **Step 1: Failing tests** - in `tests/test_hubqt.py`:
  - Replace `test_the_header_holds_logo_title_hotkeys_version_menu` with:

```python
    def test_the_header_holds_logo_jumps_hotkeys_pin_menu(self):
        names = [self.skin.header.layout().itemAt(i).widget().objectName()
                 for i in range(self.skin.header.layout().count())
                 if self.skin.header.layout().itemAt(i).widget()]
        self.assertEqual(names[0], "skeldarHubLogo")
        self.assertIn("skeldarHubHotkeys", names)
        self.assertIn("skeldarHubPin", names)
        self.assertIn("skeldarHubMenu", names)
        self.assertNotIn("skeldarHubTitle", names)
        self.assertNotIn("skeldarHubVersion", names)
        self.assertFalse(hasattr(self.skin, "strip"))

    def test_jumps_go_into_the_header_before_the_buttons(self):
        self.skin.add_jump("characters", "Animation Setup", "user", "#f0a26b")
        row = self.skin.jump_row
        self.assertEqual(row.itemAt(0).widget(), self.skin.jumps["characters"])
```

  - Replace `test_the_header_buttons_call_back` with one that clicks `hotkeys` only and expects `["hotkeys"]`.
  - Replace `test_a_state_recolours_the_version_chip` and `test_set_version` with:

```python
    def test_a_state_and_a_version_paint_the_update_jump(self):
        self.skin.add_jump("update", "Update", "refresh", "#9a9ca3")
        self.skin.set_version("d0a2631", "Installed: d0a2631")
        self.assertEqual(self.skin.jumps["update"].toolTip(),
                         "Update - Installed: d0a2631")
        self.skin.set_state("new")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "new")
        self.skin.set_state("")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "")

    def test_a_state_without_an_update_jump_is_harmless(self):
        self.skin.set_state("ok")
        self.skin.set_version("x", "y")
```

  - In `test_every_kind_of_button_sounds_once` replace `self.skin.version` with `self.skin.pin` (call `self.skin.set_edge_mode(True)` first so it is enabled/visible) - or with the menu button, whichever the test's list needs.
  - Delete `test_the_jump_strip_calls_back_with_the_key`; add:

```python
    def test_a_jump_calls_back_with_the_key(self):
        self.skin.add_jump("retarget", "Retarget", "arrows-exchange", "#7fa9e6")
        self.skin.jumps["retarget"].click()
        self.assertIn(("jump", "retarget"), self.calls)

    def test_the_pin_is_hidden_until_edge_mode_and_calls_back(self):
        self.calls_pin = []
        self.skin.cb["pin"] = lambda on: self.calls_pin.append(on)
        self.assertTrue(self.skin.pin.isHidden())
        self.skin.set_edge_mode(True)
        self.assertFalse(self.skin.pin.isHidden())
        self.assertTrue(self.skin.edge_action.isChecked())
        self.skin.pin.click()
        self.assertEqual(self.calls_pin, [True])
        self.skin.set_edge_mode(False)
        self.assertTrue(self.skin.pin.isHidden())

    def test_the_edge_row_calls_back_with_its_state(self):
        seen = []
        self.skin.cb["edge"] = lambda on: seen.append(on)
        self.skin.edge_action.trigger()
        self.assertEqual(seen, [True])
        self.skin.paint_edge(False)               # painted, no callback
        self.assertEqual(seen, [True])
```

  - Add relay and card tests:

```python
    def test_a_told_status_shows_on_the_line_with_its_card(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        card.status_controls.add("skeldarRetargetStatus")
        told = []
        self.skin.cb["told"] = lambda key, text, v: told.append((key, text, v))
        style.tell("skeldarRetargetStatus", "Retargeted 61 frames")
        self.assertEqual(self.skin.message_text.text(), "Retargeted 61 frames")
        self.assertFalse(self.skin.message.isHidden())
        self.assertFalse(self.skin.message_icon.isHidden())
        self.assertEqual(told, [("retarget", "Retargeted 61 frames", False)])

    def test_an_unknown_control_is_not_shown(self):
        style.tell("somebodyElse", "x")
        self.assertTrue(self.skin.message.isHidden())

    def test_an_empty_text_from_the_shown_source_hides_the_line(self):
        card = self.skin.add_card("com", "Center of Mass", "target",
                                  "#7fa9e6", "#23324a")
        card.status_controls.add("skeldarComStatus")
        style.tell("skeldarComStatus", "added")
        style.tell("skeldarComStatus", "")
        self.assertTrue(self.skin.message.isHidden())

    def test_destroy_stops_listening(self):
        self.skin.destroy()
        style.tell("anything", "x")                # no dead widget touched

    def test_a_said_message_has_no_icon(self):
        self.skin.say("Hotkey map: ON")
        self.assertTrue(self.skin.message_icon.isHidden())

    def test_a_hint_goes_to_the_card_header_tooltip(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        card.add_hint("Select the clip's skeleton")
        card.add_hint("and the rig")
        self.assertEqual(card.header.toolTip(),
                         "Select the clip's skeleton\nand the rig")

    def test_a_card_carries_its_group_stripe(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        self.assertEqual(card.frame.stripe, "#7fa9e6")
        self.assertEqual((card.icon_name, card.colour),
                         ("arrows-exchange", "#7fa9e6"))

    def test_compact_card_margins(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        m = card.frame.layout().contentsMargins()
        self.assertEqual((m.left(), m.top(), m.right(), m.bottom()),
                         (5, 4, 5, 5))
        self.assertEqual(card.body_layout.contentsMargins().top(), 4)

    def test_the_message_line_caps_at_three_lines(self):
        self.skin.say("word " * 400)
        lines = self.skin.message_text.fontMetrics().lineSpacing()
        self.assertLessEqual(self.skin.message_text.maximumHeight(),
                             3 * lines + 2)
        self.assertEqual(self.skin.message_text.toolTip().strip(),
                         ("word " * 400).strip())
```

  - In `SeamsMixin.setUp`'s callbacks dict add `"pin": lambda on: self.calls.append(("pin", on)), "edge": lambda on: self.calls.append(("edge", on)), "told": lambda *a: None,`.
  - `test_cards_stack_in_order_under_their_group_labels` stays (add_group remains an API; Task 4 stops calling it).

- [ ] **Step 2: Run `tests.test_hubqt`, expect failures.**

- [ ] **Step 3: Implement.**

`Card.__init__`: keep the signature; set `self.icon_name, self.colour = icon_name, colour`, `self.status_controls = set()`, `self._hints = []`; frame stripe: `self.frame.stripe = colour`; margins `column.setContentsMargins(s(5), s(4), s(5), s(5))`; header `row.setSpacing(s(5))`; icon chip `chip_label.setFixedSize(s(18), s(18))`, pixmap `s(12)`, chip radius `s(5)`; body `self.body_layout.setContentsMargins(0, s(4), 0, 0)`. Add:

```python
    def add_hint(self, text):
        """A builder's static hint, now the header's tooltip (2026-10-08:
        the compact skin keeps no hint line in the body)."""
        text = (text or "").strip()
        if text:
            self._hints.append(text)
            self.header.setToolTip("\n".join(self._hints))
```

`_frame_class` - CardFrame gains `self.stripe = None` and paints it before the light:

```python
            def paintEvent(self, event):                   # noqa: N802
                super(CardFrame, self).paintEvent(event)
                if self.stripe:
                    paint_stripe(self, self.stripe, self.scale)
                if self.level > 0.002 or self.flash > 0.002:
                    paint_light(self, self.level, self.flash, self.scale)
```

and a module function after `paint_light`:

```python
def paint_stripe(widget, colour, scale):
    """The card's group as a bar down its left edge (2026-10-08: the group
    labels are gone in the compact skin), clipped by the rounded face."""
    q = qt()
    QtCore, QtGui = q.QtCore, q.QtGui
    radius = float(hubstyle.px(8, scale))
    bar = float(hubstyle.px(3, scale))
    painter = QtGui.QPainter(widget)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        face = QtGui.QPainterPath()
        face.addRoundedRect(QtCore.QRectF(widget.rect()), radius, radius)
        painter.setClipPath(face)
        painter.fillRect(QtCore.QRectF(0, 0, bar, widget.height()),
                         QtGui.QColor(colour))
    finally:
        painter.end()
```

`Skin.__init__`: root margins `s(3)` all round, `top.setSpacing(s(3))`; build header and message; DELETE the strip block (no `self.strip`); `self.column.setSpacing(s(3))`; after the watcher is installed:

```python
        #  One message line for the whole hub (2026-10-08): every section's
        #  status writer tells it (maya_hubstyle.tell); the card marked that
        #  control (apply_marks -> Card.status_controls).
        self._message_source = None
        hubstyle.listen(self._told)
```

`_build_header` - the row: logo, `self.jump_row` (a `QHBoxLayout` named `skeldarHubJumpRow`, spacing `s(1)`, margins 0, added with `row.addLayout(self.jump_row, 1)`), hotkeys, pin, menu. Remove the title and the version chip; `row.setContentsMargins(s(1), s(1), s(1), s(1))`, `row.setSpacing(s(2))`; logo `s(18)`. The pin:

```python
        self.pin = self._head_button("skeldarHubPin", "pin",
                                     "Keep the panel out (edge panel)",
                                     checkable=True)
        self.pin.setIcon(icon("pin", hubstyle.TOKENS["muted"], self.px(16),
                              on_colour=hubstyle.TOKENS["accent_text"]))
        self.pin.clicked.connect(
            lambda checked=False: self._call("pin", bool(checked)))
        self.pin.setVisible(False)
```

The menu gains a checkable `("Edge panel", "edge")` row right after "Interface animations", wired like `sounds`/`animations` (`setattr(self, "edge_action", action)`).

`add_jump` puts the button into `self.jump_row` (not a strip), remembers `self._jump_colour[key] = colour`, size policy `Expanding/Fixed`, `setMinimumWidth(self.px(16))`.

```python
    def set_state(self, state):
        """The update jump's colour: "new" accent, "ok" ok, else its group's
        (2026-10-08: the version chip is gone from the compact header)."""
        button = self.jumps.get("update")
        if button is None:
            return
        button.setProperty("skState", state or "")
        tokens = hubstyle.TOKENS
        colour = {"new": tokens["accent"], "ok": tokens["ok"]}.get(
            state or "", self._jump_colour.get("update", tokens["muted"]))
        button.setIcon(icon("refresh", colour, self.px(16)))

    def set_version(self, text, tooltip, state=None):
        button = self.jumps.get("update")
        if button is not None:
            button.setToolTip("Update - " + (tooltip or text or ""))
        if state is not None:
            self.set_state(state)

    def paint_edge(self, on):
        self.edge_action.setChecked(bool(on))

    def set_edge_mode(self, on):
        """The hub stands in the edge panel (`on`): the pin is shown."""
        self.pin.setVisible(bool(on))
        if not on:
            self.pin.setChecked(False)
        self.paint_edge(on)
```

`_build_message`: margins `s(6), s(2), s(2), s(2)`; a `self.message_icon = _named(w.QLabel(), "skeldarHubMessageIcon", "messageicon")`, fixed `s(14)` square, hidden, added FIRST in the row (`AlignTop`); `self.message_text` keeps wordWrap; after creating it:

```python
        lines = self.message_text.fontMetrics().lineSpacing()
        self.message_text.setMaximumHeight(3 * lines + 2)
```

`say`:

```python
    def say(self, text, state=None, source=None):
        """The message line: shown while it holds text; `source` a card key
        puts that card's icon at its left. The whole text is the tooltip
        (the line shows three lines at most)."""
        self.message_text.setText(text or "")
        self.message_text.setToolTip(text or "")
        card = self.cards.get(source) if source else None
        if card is not None:
            self.message_icon.setPixmap(pixmap(card.icon_name, card.colour,
                                               self.px(14)))
        self.message_icon.setVisible(card is not None and bool(text))
        self._message_source = source if text else None
        self.message.setVisible(bool(text))
        if state is not None:
            self.set_state(state)

    def _told(self, control, text, viewport):
        """The relay: a section's status control said `text`."""
        if not self.alive():
            hubstyle.unlisten(self._told)
            return
        key = next((k for k, card in self.cards.items()
                    if control in card.status_controls), None)
        if key is None:
            return
        if text:
            self.say(text, source=key)
        elif self._message_source == key:
            self.say("")
        self._call("told", key, text, viewport)
```

`destroy`: first line `hubstyle.unlisten(self._told)`.

Update the module docstring's header list: `header  the SA mark, the jump icons, hotkeys, the pin (edge panel), a menu` and drop `strip`.

- [ ] **Step 4: Run `tests.test_hubqt` -> PASS, then the whole suite.** `tests/test_hub.py` will fail where it reads `skin.strip` / `skin.version` - leave those for Task 4 only if they are about the hub's build order; any test in `test_hubqt.py` must pass now.

- [ ] **Step 5: Commit** (`feat(hub): one header row, a message line with its source, compact cards with a group stripe`).

---

### Task 3: The skin reads the new roles - hidden statuses, hints, context, the list grip, the dot

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`_apply_mark`, new `_grip_class`, `list_widget`, `list_row_px`, `set_list_height`, `_optionvar`)
- Test: `tests/test_hubqt.py`

**Interfaces:**
- Consumes: Task 1 (`Mark.target`, `hubstyle.clamp_rows/rows_after_drag/list_height/LIST_VAR/LIST_ROWS`), Task 2 (`card.status_controls`, `card.add_hint`).
- Produces (seams the tests replace, all module-level in `maya_hubqt`):
  - `list_widget(name)` -> the QListWidget of textScrollList `name` or None
  - `list_row_px(name)` -> physical px of one row (`sizeHintForRow(0)`, else font line spacing + 4)
  - `set_list_height(name, logical)` -> `cmds.textScrollList(name, edit=True, height=logical)`
  - `optionvar_get(name)` / `optionvar_set(name, value)` (cmds, lazily imported)
  - `apply_list_rows(name, rows, scale)` -> sets the list to `rows`, answers the logical height
- Role behaviour in the skin:
  - `status`: the widget hidden (`setVisible(False)`, `setMaximumHeight(0)`), `card.status_controls.add(mark.name)`;
  - `note`: `card.add_hint(widget.property("text"))`, the widget hidden;
  - `context`: the widget hidden (its writer shows it elsewhere);
  - `heading`: unchanged (builders stop making headings in the skin, Task 5);
  - `grip`: a `ListGrip` laid over the placeholder (`_fill_class` keeps it there), the list set to its remembered rows (else `LIST_ROWS`);
  - `dot`: just the property (the stylesheet colours it).

- [ ] **Step 1: Failing tests** (`tests/test_hubqt.py`, in the marks test class that already registers controls by name through `self.control(cls, name)`):

```python
    def test_a_status_is_hidden_and_owned_by_its_card(self):
        card = self.skin.add_card("com", "Center of Mass", "target",
                                  "#7fa9e6", "#23324a")
        label = self.control(QtWidgets.QLabel, "skeldarComStatus", card.body)
        hubqt.apply_marks([style.Mark("skeldarComStatus", "status", None,
                                      False, None)], card, 1.0)
        self.assertTrue(label.isHidden())
        self.assertIn("skeldarComStatus", card.status_controls)

    def test_a_note_becomes_the_header_tooltip(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        label = self.control(QtWidgets.QLabel, "hint1", card.body)
        label.setText("Select the clip's skeleton")
        hubqt.apply_marks([style.Mark("hint1", "note", None, False, None)],
                          card, 1.0)
        self.assertTrue(label.isHidden())
        self.assertEqual(card.header.toolTip(), "Select the clip's skeleton")

    def test_a_context_line_is_hidden(self):
        card = self.skin.add_card("characters", "Animation Setup", "user",
                                  "#f0a26b", "#4a3322")
        label = self.control(QtWidgets.QLabel, "ueAnimBridgeHeader", card.body)
        hubqt.apply_marks([style.Mark("ueAnimBridgeHeader", "context", None,
                                      False, None)], card, 1.0)
        self.assertTrue(label.isHidden())


class ListGrip(SeamsMixin, unittest.TestCase):
    """2026-10-08: a list shows 10 rows and its grip changes that."""

    def setUp(self):
        super(ListGrip, self).setUp()
        self.vars, self.heights = {}, []
        self.saved_seams = (hubqt.list_row_px, hubqt.set_list_height,
                            hubqt.optionvar_get, hubqt.optionvar_set)
        hubqt.list_row_px = lambda name: 16
        hubqt.set_list_height = lambda name, h: self.heights.append((name, h))
        hubqt.optionvar_get = lambda name: self.vars.get(name)
        hubqt.optionvar_set = lambda name, v: self.vars.__setitem__(name, v)
        self.card = self.skin.add_card("shared", "Shared", "send", "#f0a26b",
                                       "#4a3322")
        self.placeholder = self.control(QtWidgets.QFrame, "theGrip",
                                        self.card.body)
        self.placeholder.resize(200, 8)

    def tearDown(self):
        (hubqt.list_row_px, hubqt.set_list_height, hubqt.optionvar_get,
         hubqt.optionvar_set) = self.saved_seams
        super(ListGrip, self).tearDown()

    def _apply(self):
        hubqt.apply_marks([style.Mark("theGrip", "grip", None, False, None,
                                      "theList")], self.card, 1.0)
        return self.placeholder.findChild(QtWidgets.QWidget, "theGrip_grip")

    def test_ten_rows_by_default(self):
        grip = self._apply()
        self.assertIsNotNone(grip)
        self.assertEqual(self.heights[-1][0], "theList")
        self.assertEqual(self.heights[-1][1], style.list_height(10, 16, hubqt.LIST_FRAME))

    def test_the_remembered_rows(self):
        self.vars[style.LIST_VAR.format("theList")] = 25
        self._apply()
        self.assertEqual(self.heights[-1][1], style.list_height(25, 16, hubqt.LIST_FRAME))

    def test_a_drag_changes_whole_rows_and_is_remembered_on_release(self):
        grip = self._apply()
        grip.press(100)
        grip.drag(100 + 16 * 3)
        self.assertEqual(self.heights[-1][1], style.list_height(13, 16, hubqt.LIST_FRAME))
        self.assertIsNone(self.vars.get(style.LIST_VAR.format("theList")))
        grip.release()
        self.assertEqual(self.vars[style.LIST_VAR.format("theList")], 13)

    def test_a_drag_clamps(self):
        grip = self._apply()
        grip.press(100)
        grip.drag(-5000)
        grip.release()
        self.assertEqual(self.vars[style.LIST_VAR.format("theList")], 5)
```

- [ ] **Step 2: Run, expect failures.**

- [ ] **Step 3: Implement** in `maya_hubqt.py`:

```python
# ---------------------------------------------------------------- the lists

#  A list's frame and padding, logical px, added to its rows' height
LIST_FRAME = 8


def list_widget(name):
    """The QListWidget under textScrollList `name` (Maya's textScrollList IS
    one - maya_uebridge.listdrag), or None."""
    import maya.OpenMayaUI as omui
    q = qt()
    ptr = omui.MQtUtil.findControl(name)
    if not ptr:
        return None
    return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QListWidget)


def list_row_px(name):
    """One row of list `name` in physical px."""
    widget = list_widget(name)
    if widget is None:
        return 0
    if widget.count():
        size = widget.sizeHintForRow(0)
        if size > 0:
            return size
    return widget.fontMetrics().lineSpacing() + 4


def set_list_height(name, logical):
    import maya.cmds as cmds
    if cmds.textScrollList(name, exists=True):
        cmds.textScrollList(name, edit=True, height=int(logical))


def optionvar_get(name):
    import maya.cmds as cmds
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name)
    return None


def optionvar_set(name, value):
    import maya.cmds as cmds
    cmds.optionVar(intValue=(name, int(value)))


def apply_list_rows(name, rows, scale):
    """List `name` shows `rows` rows; answers its logical height."""
    row = list_row_px(name) / float(scale or 1.0)
    height = hubstyle.list_height(hubstyle.clamp_rows(rows), row or 16,
                                  LIST_FRAME)
    set_list_height(name, height)
    return height


def remembered_rows(name):
    saved = optionvar_get(hubstyle.LIST_VAR.format(name))
    try:
        return hubstyle.clamp_rows(int(saved)) if saved else hubstyle.LIST_ROWS
    except (TypeError, ValueError):
        return hubstyle.LIST_ROWS


def _grip_class():
    """The height grip under a list (2026-10-08): ⋯ on an 8 px bar, the
    vertical resize cursor; a drag moves the list by whole rows (5..40), the
    release remembers. `press/drag/release` take GLOBAL y (physical px) so
    the tests can drive them without a mouse."""
    if "grip" not in _CLASSES:
        q = qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets

        class ListGrip(QtWidgets.QWidget):

            def __init__(self, list_name, scale, parent=None):
                super(ListGrip, self).__init__(parent)
                self.list_name, self.scale = list_name, float(scale or 1.0)
                self.rows = remembered_rows(list_name)
                self._start = None
                self.setProperty("skRole", "grip")
                self.setCursor(QtCore.Qt.SizeVerCursor)
                self.setToolTip("Drag to show more or fewer rows")

            def press(self, gy):
                self._start = (gy, self.rows)

            def drag(self, gy):
                if self._start is None:
                    return
                y0, rows0 = self._start
                row = list_row_px(self.list_name) or 16
                rows = hubstyle.rows_after_drag(rows0, gy - y0, row)
                if rows != self.rows:
                    self.rows = rows
                    apply_list_rows(self.list_name, rows, self.scale)

            def release(self):
                if self._start is not None:
                    optionvar_set(hubstyle.LIST_VAR.format(self.list_name),
                                  self.rows)
                self._start = None

            def mousePressEvent(self, event):              # noqa: N802
                if event.button() == QtCore.Qt.LeftButton:
                    self.press(event.globalPosition().y())
                    event.accept()

            def mouseMoveEvent(self, event):               # noqa: N802
                self.drag(event.globalPosition().y())

            def mouseReleaseEvent(self, event):            # noqa: N802
                self.release()

            def paintEvent(self, event):                   # noqa: N802
                super(ListGrip, self).paintEvent(event)
                painter = QtGui.QPainter(self)
                try:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing)
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.setBrush(QtGui.QColor(hubstyle.TOKENS["faint"]))
                    r = max(1.0, 1.2 * self.scale)
                    cx, cy = self.width() / 2.0, self.height() / 2.0
                    for dx in (-5, 0, 5):
                        painter.drawEllipse(QtCore.QPointF(
                            cx + dx * self.scale, cy), r, r)
                finally:
                    painter.end()

        _CLASSES["grip"] = ListGrip
    return _CLASSES["grip"]
```

(`paintEvent` of a plain QWidget does not draw the stylesheet background unless `WA_StyledBackground` is set: set it in `__init__`.)

In `_apply_mark`, before `widget.setProperty("skRole", mark.role)`:

```python
    if mark.role == "status":
        widget.setVisible(False)
        widget.setMaximumHeight(0)
        card.status_controls.add(mark.name)
        return True
    if mark.role == "note":
        card.add_hint(widget.property("text") or "")
        widget.setVisible(False)
        return True
    if mark.role == "context":
        widget.setVisible(False)
        return True
    if mark.role == "grip":
        cover = _grip_class()(mark.target, scale, widget)
        cover.setObjectName(mark.name + "_grip")
        widget.installEventFilter(_fill_class()(cover, cover))
        cover.setGeometry(widget.rect())
        cover.show()
        apply_list_rows(mark.target, cover.rows, scale)
        return True
```

- [ ] **Step 4: Run `tests.test_hubqt` -> PASS; the suite.**
- [ ] **Step 5: Commit** (`feat(hub): hidden statuses relayed, hints in the header, a height grip under the lists`).

---

### Task 4: The hub builds the compact skin

**Files:**
- Modify: `SkeldarAnim/maya_hub.py` (`_build_skin`, `_dress_header`, `chip_state`, `_callbacks`, `say`)
- Test: `tests/test_hub.py`

**Interfaces:**
- Consumes: Task 2 (`Skin.add_jump` into the header, `set_version`, `set_state`, `"told"`), Task 1.
- Produces: `_build_skin` no longer calls `skin.add_group`; `_callbacks()` gains `"told": _told`, `"pin": _press_pin`, `"edge": set_edge` (the last two are defined in Task 11 - add them here as `lambda *_a: None` placeholders ONLY IF Task 11 has not run; prefer running Task 11 later and wiring there). `_told(key, text, viewport)` is a no-op until Task 11.

- [ ] **Step 1: Failing tests** (`tests/test_hub.py`): find the tests that assert group labels are added (`add_group`) and change them to assert NO group label is added; find any test reading `skin.strip` / `skin.version` and point it at `skin.jumps["update"]`. Add:

```python
    def test_the_skin_has_no_group_labels(self):
        # build the skin with the module's fakes the file already uses
        ...
        self.assertFalse([c for c in skin_calls if c[0] == "add_group"])
```

(Use the file's existing fake-Skin recorder; if the file builds a real offscreen Skin, assert `not skin.content.findChildren(QtWidgets.QLabel, "skeldarHubGroup_scene")`.)

- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement**: in `_build_skin`, delete the `current`/`add_group` lines in the card loop. `_dress_header` keeps calling `skin.set_version(short, ...)`. Add to `_callbacks`: `"told": _told,`. Add:

```python
def _told(key, text, viewport):
    """A card's status reached the message line (maya_hubqt.Skin._told).
    The edge panel adds a viewport message while it is hidden (Task 11)."""
    return None
```

- [ ] **Step 4: Run `tests.test_hub` and the suite -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): the compact skin - no group labels, the header's jumps`).

---

### Task 5: Tiles with the name over the picture, compact hand cards

**Files:**
- Modify: `SkeldarAnim/maya_charlook.py`, `SkeldarAnim/maya_chargrid.py`, `SkeldarAnim/maya_armorgrid.py`, `SkeldarAnim/maya_inventory.py`, `SkeldarAnim/maya_invlook.py`
- Test: `tests/test_charlook.py`, `tests/test_chargrid.py`, `tests/test_armorgrid.py`, `tests/test_inventory.py`, `tests/test_invlook.py`

**Interfaces:**
- `maya_charlook`: `CELL_MIN = 58`, `GAP = 3`, `NAME_H = 16` (now the strip INSIDE the square's bottom). `grid(width, count, scale)` -> `(cols, cell, rects, height)` with `height = rows * cell + (rows - 1) * gap` (no name strip); `name_rect(rect, scale)` -> `(x, y + h - NAME_H*k, w, NAME_H*k)`; `tile_rect(rect, scale)` -> `rect`.
- `maya_invlook`: `ROW_H = 15`, `NAME_H = 16`; the channel labels always short (`tx … rz`).

- [ ] **Step 1: Failing tests**

`tests/test_charlook.py`:

```python
class OverlayNames(unittest.TestCase):
    """2026-10-08, variant B: five a row in the card, the name over the
    picture's bottom (no strip under it)."""

    def test_five_portraits_a_row_in_a_338_px_card(self):
        cols, cell, rects, height = look.grid(338, 5)
        self.assertEqual(cols, 5)
        self.assertGreaterEqual(cell, look.CELL_MIN)
        self.assertEqual(height, cell)                  # one row, no strip

    def test_the_name_lies_inside_the_square(self):
        rect = (10, 20, 64, 64)
        nx, ny, nw, nh = look.name_rect(rect)
        self.assertEqual((nx, nw, nh), (10, 64, look.NAME_H))
        self.assertEqual(ny + nh, 20 + 64)

    def test_a_tile_is_its_square(self):
        self.assertEqual(look.tile_rect((1, 2, 30, 30)), (1, 2, 30, 30))

    def test_two_rows_height(self):
        cols, cell, rects, height = look.grid(338, 7)
        self.assertEqual(height, 2 * cell + look.GAP)
```

`tests/test_invlook.py`:

```python
    def test_compact_hand_rows(self):
        self.assertEqual((look.ROW_H, look.NAME_H), (15, 16))

    def test_channel_names_are_always_short(self):
        # whatever split_row would say, the compact card shows tx .. rz
        self.assertEqual(look.labels(False), dict((c, c) for c in look.CHANNELS))
```

(Use the module's existing function name for the short/nice dict - the one at `maya_invlook.py:80-84`; read its name and signature first and test THAT. If it takes `short`, make it ignore the flag and always answer the short names, keeping the parameter for its callers.)

Fix every existing test that pins `CELL_MIN 72`, `GAP 6`, a height including `NAME_H`, `ROW_H 19`, `NAME_H 20` or a nice channel name: change the expected numbers to the new constants (derive them from the constants, never hard-code a new number twice).

- [ ] **Step 2: Run, expect failures.**
- [ ] **Step 3: Implement** in `maya_charlook.py`: the constants; in `grid` the row stride `cell + gap` and `height = rows * cell + (rows - 1) * gap`; `name_rect` / `tile_rect` as above.

In `maya_chargrid.py` `_paint_name` (and the same shape in `maya_armorgrid.py` ~L420 and `maya_inventory.py` ~L829), before drawing the text, paint the strip's backdrop:

```python
            shade = QtGui.QLinearGradient(nx, ny, nx, ny + nh)
            shade.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
            shade.setColorAt(1.0, QtGui.QColor(0, 0, 0, 190))
            p.setPen(Qt.NoPen)
            p.setBrush(shade)
            p.drawRect(QtCore.QRectF(nx, ny, nw, nh))
```

and use `font(10 * k, ...)` for the name. Any tag/pill drawn at the bottom of a square ("no rig", `look.tag_text`, "equipped", "floor") moves ABOVE the name strip: its `bottom()` term gains `- nh` (read `nh` from `look.name_rect(rect, k)`). Selected/dimmed colours unchanged.

In `maya_invlook.py`: `ROW_H = 15`, `NAME_H = 16`, and the short-names function always answers the short names.

- [ ] **Step 4: Run the five test modules, then the suite -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): tiles five a row with the name over the picture, compact hand cards`).

---

### Task 6: Animation Setup - one top row, no heading, the Connect block compact, a 10-row list with a grip

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/window.py` (`build_characters_panel`, `_kind_row`, `_status`)
- Modify: `SkeldarAnim/maya_uebridge/window.py` (`build_rows`, `_status`, `_header`, `_repopulate`, new `_DOT`, `_LIST_GRIP`)
- Test: `tests/test_hub_sections.py`, `tests/test_uebridge_window.py`

**Interfaces:**
- Consumes: Task 1 (`hubstyle.height`, `row_spacing`, `grip`, `tell`, `skinning`), Task 3 (roles).
- Produces: control names unchanged; new names `ueAnimBridgeDot` (`_DOT`), `ueAnimBridgeListGrip` (`_LIST_GRIP`).

- [ ] **Step 1: Failing tests** - in `tests/test_hub_sections.py` (the `SceneSetup` class builds with `FakeUiCmds`; read how it toggles skinning - if it doesn't, wrap a build in `style.set_skinning(True)` / `False` in try/finally):

```python
    def test_compact_top_row_is_kind_import_delete_camera(self):
        # the rowLayout right after the portraits' placeholder holds four:
        # the [Rig | Skeleton] segments, + Import, Delete, Camera Setup
        rows = [c for c in self.fake.calls if c[0] == "rowLayout"
                and c[2].get("numberOfColumns") == 4]
        self.assertTrue(rows)
        labels = [c[2].get("label") for c in self.fake.calls if c[0] == "button"]
        self.assertIn("Camera", labels)       # the classic build's label

    def test_no_heading_in_the_skin(self):
        # build again with skinning on: no "heading" mark at all
        ...
        self.assertFalse([m for m in marks if m.role == "heading"])

    def test_the_animation_list_has_a_grip(self):
        marks = self.marks_by_name()       # helper: {mark.name: mark}
        self.assertEqual(marks[uebridge._LIST_GRIP].role, "grip")
        self.assertEqual(marks[uebridge._LIST_GRIP].target, uebridge._LIST)

    def test_the_status_writers_tell_the_hub(self):
        heard = []
        style.listen(lambda c, t, v: heard.append((c, t)))
        try:
            scenesetup._status("hello", scenesetup._CHARACTER_STATUS)
            uebridge._status("bridge says")
        finally:
            style._LISTENERS[:] = []
        self.assertIn((scenesetup._CHARACTER_STATUS, "hello"), heard)
        self.assertIn((uebridge._STATUS, "bridge says"), heard)
```

Replace `test_the_editor_line_is_context_the_character_line_the_subtitle` expectations: `_HEADER` stays `context` (hidden in the skin); `_DOT` is a `dot` mark. Replace `test_the_sections_have_headings`: headings only in the classic build. Replace the `LIST_HEIGHT` test (line ~691): classic list keeps `LIST_HEIGHT` (300); a `grip` mark exists for `_LIST`.

In `tests/test_uebridge_window.py` add:

```python
    def test_the_header_line_goes_to_the_dropdown_tooltip_and_the_dot(self):
        fake = FakeUiCmds()
        bridge.cmds = fake
        bridge._header(bridge.editor_line(True))
        edits = [c for c in fake.calls if c[0] in ("optionMenu", "text")
                 and c[2].get("edit")]
        self.assertTrue([c for c in edits if c[0] == "optionMenu"
                         and c[2].get("annotation") == "connected"])
        self.assertTrue([c for c in edits if c[1] and c[1][0] == bridge._DOT
                         and c[2].get("label") == bridge.DOT_ON])

    def test_the_search_placeholder_counts_the_animations(self):
        self.assertEqual(bridge.search_hint(619), "search 619 animations")
        self.assertEqual(bridge.search_hint(0), "search name or folder")
```

(Adapt to the file's existing fake set-up; `FakeUiCmds` `exists` answers False, so make `_header` NOT guard its new edits on `exists` of the dropdown - guard each with `try/except RuntimeError` instead, or patch `fake.existing`.)

- [ ] **Step 2: Run, expect failures.**

- [ ] **Step 3: Implement.**

`maya_scenesetup/window.py`:

`_status` (L232-235) gains, after the label write: `hubstyle.tell(control, message)`. (Read the function; keep its guard; `tell` goes after the write, unconditionally.)

`_kind_row` height `hubstyle.height("segment", 22)`; it must NOT call `cmds.setParent("..")` itself when a caller wants it inside a row - give it a parameter: `def _kind_row(kind):` unchanged body, it already closes only its own segments rowLayout (it ends with one `cmds.setParent("..")` for the segments row) - good.

`build_characters_panel` body becomes:

```python
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))

    hubstyle.mark(cmds.text(_BOUND, label="", align="left"), "subtitle")
    #  the compact skin has no headings (2026-10-08): the card says it
    if not hubstyle.skinning():
        heading(_CHARACTERS_HEADING, "Characters")

    model, kind = remembered_choice()
    #  [Rig | Skeleton] [+ Import] [Delete] [Camera Setup] on one row
    #  (2026-10-08, variant B); Delete and Camera Setup icons in the skin
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 3),
                                 (3, "left", 3), (4, "left", 3)])
    _kind_row(kind)
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("Import", "+ Import"),
        height=hubstyle.height("button", 32),
        width=hubstyle.pick(84, 90),
        annotation=...,                 # unchanged text
        command=lambda *_args: _run(add_character, _CHARACTER_STATUS)),
        "primary", "plus")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Delete"),
        height=hubstyle.height("button", 32), width=hubstyle.pick(26, 64),
        annotation=...,                 # unchanged text
        command=lambda *_args: _run(delete_characters, _CHARACTER_STATUS)),
        "danger", "trash")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Camera"),
        height=hubstyle.height("button", 32), width=hubstyle.pick(26, 64),
        annotation="Camera Setup: " + ...,   # the old text, prefixed
        command=lambda *_args: _run(camera_setup, _CHARACTER_STATUS)),
        "secondary", "camera")
    cmds.setParent("..")

    cmds.columnLayout(_PORTRAITS, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_grid(model, kind):
        _character_dropdown()

    _bridge_rows()
    hubstyle.mark(cmds.text(_CHARACTER_STATUS, label="", align="left",
                            wordWrap=True, height=36), "status")
    cmds.setParent("..")
    _run(_bound_root, _CHARACTER_STATUS)
    _run(_say_choice, _CHARACTER_STATUS)
    return column
```

(Keep every annotation text exactly as it is now; `...` above means "the existing string, unchanged" - copy it.) Update the function's docstring with a 2026-10-08 paragraph: «сделаем его компактным» - the four buttons on one row, no heading, the status on the hub's line.

`maya_uebridge/window.py`:

Constants near `_HEADER`: `_DOT = "ueAnimBridgeDot"`, `_LIST_GRIP = "ueAnimBridgeListGrip"`, `DOT_ON, DOT_OFF = "●", "○"`.

```python
def search_hint(count):
    """The search field's placeholder: how many animations the source holds
    (2026-10-08: the editor line is a tooltip in the compact skin). Pure."""
    return ("search {0} animations".format(count) if count
            else "search name or folder")


def _status(text):
    if cmds.text(_STATUS, exists=True):
        cmds.text(_STATUS, edit=True, label=text)
    hubstyle.tell(_STATUS, text)


def _header(text):
    """The editor line: its own (hidden in the skin) text, the project
    dropdown's tooltip and the dot before it (● connected, ○ not)."""
    if cmds.text(_HEADER, exists=True):
        cmds.text(_HEADER, edit=True, label=text)
    for edit in (lambda: cmds.optionMenu(_PROJECT, edit=True, annotation=text),
                 lambda: cmds.text(_DOT, edit=True,
                                   label=DOT_ON if text == "connected"
                                   else DOT_OFF, annotation=text)):
        try:
            edit()
        except (RuntimeError, TypeError, ValueError):
            pass
```

In `_repopulate`, after `_STATE["filtered"] = shown`:

```python
    try:
        cmds.textField(_SEARCH, edit=True,
                       placeholderText=search_hint(len(_STATE["records"])))
    except (RuntimeError, TypeError, ValueError):
        pass
```

`build_rows` - the new body (names and callbacks unchanged; heights through `hubstyle.height`):

```python
    inset = cmds.columnLayout(_INSET, adjustableColumn=True,
                              rowSpacing=hubstyle.pick(3, 4),
                              columnAttach=("both", hubstyle.pick(0, 6)),
                              **hubstyle.pick({}, {"backgroundColor":
                                                   INSET_CLASSIC_BG}))
    hubstyle.mark(inset, "inset", layout=True)
    if not hubstyle.skinning():
        hubstyle.mark(cmds.text(_HEADING, label="Connect", align="left",
                                font="boldLabelFont"), "heading")
    # ... the source segments block, unchanged except height=hubstyle.height("segment", 22) ...
    #  the editor line: shown in the classic hub, hidden in the skin (its
    #  text is the dropdown's tooltip and the dot's state, `_header`)
    hubstyle.mark(cmds.text(_HEADER, label=editor_line(False), align="left",
                            wordWrap=True, height=36), "context")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3),
                                 (3, "left", 3)])
    hubstyle.mark(cmds.text(_DOT, label=DOT_OFF, width=12, align="center",
                            annotation=editor_line(False)), "dot")
    cmds.optionMenu(_PROJECT, ...)      # unchanged
    hubstyle.mark(cmds.button(..., height=hubstyle.height("field", 24), ...),
                  "tool", "refresh")    # unchanged otherwise
    cmds.setParent("..")

    cmds.textField(_SEARCH, placeholderText=search_hint(0),
                   height=hubstyle.height("field", 24),
                   textChangedCommand=lambda *_: _run(_repopulate))

    cmds.textScrollList(_LIST, ..., height=LIST_HEIGHT, ...)   # unchanged
    #  under the list its height grip (2026-10-08): 10 rows by default
    hubstyle.grip(cmds.separator(_LIST_GRIP, height=8, style="none"), _LIST)

    #  [Onto sel. | New] [⏱] [Import] [⤒ FBX] [uasset] - one row (variant B)
    cmds.rowLayout(numberOfColumns=5, adjustableColumn=3,
                   columnAttach=[(1, "left", 0), (2, "left", 3),
                                 (3, "both", 3), (4, "left", 3),
                                 (5, "left", 3)])
    segments = cmds.rowLayout(numberOfColumns=len(TARGETS),
                              columnAttach=[(i + 1, "both", 1)
                                            for i in range(len(TARGETS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_MODE)
    for target, label, note in TARGET_SEGMENTS:
        hubstyle.mark(cmds.iconTextRadioButton(
            target_button(target), style="textOnly",
            label=SHORT_TARGET.get(target, label),
            height=hubstyle.height("segment", 22),
            select=target == TARGETS[0], annotation=note), "segment")
    cmds.setParent("..")
    hubstyle.mark(cmds.checkBox(
        _TIMELINE, label=hubstyle.pick("", "timeline"), value=True,
        annotation="set the timeline to the clip's range"), "chip", "clock")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("Import", "Import Animation"),
        height=hubstyle.height("button", 32),
        annotation=...,                 # unchanged
        command=lambda *_: _run(import_selected, busy=_import_busy())),
        "primary", "download")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "FBX..."),
        height=hubstyle.height("button", 28), width=hubstyle.pick(26, 50),
        annotation="Export FBX... - " + ...,     # the old text, prefixed
        command=lambda *_: _run(export_fbx_selected,
                                busy="writing the fbx...")),
        "secondary", "upload")
    hubstyle.mark(cmds.button(
        _UASSET, label="uasset", height=hubstyle.height("button", 28),
        width=hubstyle.pick(52, 56),
        annotation=...,                 # unchanged
        command=lambda *_: _run(export_uasset_selected,
                                busy="writing the uasset...")),
        "secondary")
    cmds.setParent("..")
    cmds.setParent("..")             # out of the Connect block
```

with `SHORT_TARGET = {"onto": "Onto sel."}` keyed by the first value of `TARGETS` (read `TARGETS` / `TARGET_SEGMENTS`: use the actual key of "Onto selected"). Keep `_source_changed(remembered)` and `_attach_drag()` at the end.

- [ ] **Step 4: Run `tests.test_hub_sections tests.test_uebridge_window`, then the suite -> PASS.** Fix any other test that pins the old Animation Setup row order (the `test_the_bridge_rows_follow_camera_setup...` family) to the new order: kind/Import/Delete/Camera row, portraits, the bridge's block, the status.
- [ ] **Step 5: Commit** (`feat(hub): Animation Setup compact - one top row, the Connect block on fewer rows, a grip under the list`).

---

### Task 7: Inventory - Equip / Unequip on the tab row

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/window.py` (`_tab_row`, `build_weapons_panel`, new `equip_current`, `unequip_current`)
- Modify: `SkeldarAnim/maya_scenesetup/armorpanel.py` (`build_rows` loses its button row; `_status` tells)
- Test: `tests/test_hub_sections.py`

**Interfaces:**
- Produces: `window.equip_current()` / `window.unequip_current()` dispatching by `remembered_tab()` ("weapon" -> `add_weapon` / `remove_weapon` through `window._run`; "armor" -> `armorpanel._run(armorpanel.equip_armor)` / `armorpanel._run(armorpanel.unequip_armor)`).

- [ ] **Step 1: Failing tests** (replace `test_equip_and_unequip_share_a_row`, `test_equip_is_the_primary_and_unequip_the_danger` and the armor rows' button tests):

```python
    def test_equip_and_unequip_stand_on_the_tab_row(self):
        # the rowLayout holding the [Weapon | Armor] segments has 3 columns:
        # segments, Equip, Unequip; no other Equip button in the card
        equips = [c for c in self.fake.calls if c[0] == "button"
                  and c[2].get("label") in ("Equip", "Unequip", "")
                  and c[2].get("annotation", "").startswith(("Put", "Bake",
                                                             "Equip", "Take"))]
        self.assertEqual(len(equips), 2)

    def test_equip_current_follows_the_tab(self):
        calls = []
        saved = (scenesetup.add_weapon, armorpanel.equip_armor,
                 scenesetup.remembered_tab)
        try:
            scenesetup.add_weapon = lambda: calls.append("weapon")
            armorpanel.equip_armor = lambda: calls.append("armor")
            scenesetup.remembered_tab = lambda: "armor"
            scenesetup.equip_current()
            scenesetup.remembered_tab = lambda: "weapon"
            scenesetup.equip_current()
        finally:
            (scenesetup.add_weapon, armorpanel.equip_armor,
             scenesetup.remembered_tab) = saved
        self.assertEqual(calls, ["armor", "weapon"])

    def test_the_armor_rows_build_only_the_tiles(self):
        # armorpanel.build_rows makes no button
        ...
```

and a relay test for `armorpanel._status`.

- [ ] **Step 2: Run, expect failures.**
- [ ] **Step 3: Implement.**

```python
def equip_current():
    """Equip on the tab row (2026-10-08): the shown tab's Equip."""
    if remembered_tab() == "armor":
        from maya_scenesetup import armorpanel
        return armorpanel._run(armorpanel.equip_armor)
    return _run(add_weapon)


def unequip_current():
    if remembered_tab() == "armor":
        from maya_scenesetup import armorpanel
        return armorpanel._run(armorpanel.unequip_armor)
    return _run(remove_weapon)
```

`_tab_row(tab)` builds a 3-column rowLayout (adjustableColumn 1): the segments (height `hubstyle.height("segment", 24)`), Equip (primary, sword, `height("button", 32)`, `width=pick(84, 80)`, annotation: the weapon's text + " On the Armor tab: put the picked piece on." ), Unequip (danger, trash, label `pick("", "Unequip")`, `width=pick(26, 80)`, annotation joined likewise), then closes its row. The Equip/Unequip commands: `lambda *_a: equip_current()` / `unequip_current()`. `build_weapons_panel` loses its Equip/Unequip rowLayout in the weapon tab; columns use `rowSpacing=hubstyle.row_spacing(6)`. `armorpanel.build_rows` loses its rowLayout of two buttons; `armorpanel._status` gains `hubstyle.tell(<its control>, text)` after its write.

- [ ] **Step 4: Run tests -> PASS; the suite.**
- [ ] **Step 5: Commit** (`feat(hub): Inventory compact - Equip and Unequip on the tab row`).

---

### Task 8: Connections and Shared

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/connections.py` (`build_panel`, `_set_chooser`, `_status`, new `CHOOSER_ROW`)
- Modify: `SkeldarAnim/maya_share.py` (`build_panel`, `_status`, new `LIST_GRIP`)
- Test: `tests/test_scenesetup_connections.py`, `tests/test_share.py`

**Interfaces:** `connections.CHOOSER_ROW = "skeldarConnectionsChooserRow"`; `maya_share.LIST_GRIP = "skeldarShareListGrip"`.

- [ ] **Step 1: Failing tests**

`tests/test_scenesetup_connections.py`: change the `HEADER` role expectation (L327) to `"subtitle"`; add:

```python
    def test_both_arms_share_one_row(self):
        rows = [c for c in self.fake.calls if c[0] == "rowLayout"
                and c[2].get("numberOfColumns") == 4]
        self.assertTrue(rows)

    def test_the_chooser_row_shows_only_for_two_weapons(self):
        fake = FakeUiCmds()
        cx.cmds = fake
        cx._set_chooser(["|a"], "|a")
        cx._set_chooser(["|a", "|b"], "|a")
        manages = [c[2]["manage"] for c in fake.calls
                   if c[0] == "rowLayout" and c[1] and c[1][0] == cx.CHOOSER_ROW
                   and "manage" in c[2]]
        self.assertEqual(manages, [False, True])

    def test_apply_all_bake_and_release_share_a_row(self):
        ...  # a 3-column rowLayout holding the three buttons

    def test_the_status_tells_the_hub(self):
        heard = []
        style.listen(lambda c, t, v: heard.append((c, t)))
        try:
            cx._status("linked")
        finally:
            style._LISTENERS[:] = []
        self.assertIn((cx.STATUS, "linked"), heard)
```

(`labels_for`/`weapon_label` in `_set_chooser` may need the scene: patch them in the test with lambdas if `_set_chooser` calls into cmds for labels.)

`tests/test_share.py`: the list's grip mark (`LIST_GRIP` -> target `LIST`); Author/Name on ONE rowLayout of 2 columns with no `text` label in the skin; `_status` tells.

- [ ] **Step 2: Run, expect failures.**
- [ ] **Step 3: Implement.**

Connections `build_panel`:

```python
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    #  the scene's state line is the card's subtitle (2026-10-08)
    hubstyle.mark(cmds.text(HEADER, label="", align="left",
                            wordWrap=hubstyle.pick(False, True),
                            height=hubstyle.pick(18, 36)), "subtitle")
    #  Arm R [FK|IK]  Arm L [FK|IK] on one row (2026-10-08)
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3),
                                 (3, "left", 6), (4, "both", 3)])
    for side in SIDES[::-1]:
        cmds.text(label=ARM_ROW.format(side).replace("_", " "),
                  font="boldLabelFont")
        segments = cmds.rowLayout(numberOfColumns=2,
                                  columnAttach=[(1, "both", 1), (2, "both", 1)])
        hubstyle.mark(segments, "segments", layout=True)
        for mode in fkik.MODES:
            hubstyle.mark(cmds.iconTextCheckBox(...same as now, height=hubstyle.height("segment", 22)...), "segment")
        cmds.setParent("..")
    cmds.setParent("..")
    #  Which of two weapons: shown only while two stand (_set_chooser)
    cmds.rowLayout(CHOOSER_ROW, numberOfColumns=2, adjustableColumn=2,
                   columnWidth2=(hubstyle.pick(48, 64), 110),
                   columnAttach=[(1, "left", 0), (2, "both", 3)],
                   manage=False)
    ... the chooser exactly as now ...
    cmds.setParent("..")
    for row, choices in _ROWS:
        ... as now, columnWidth3=(hubstyle.pick(48, 64), 110, hubstyle.tool_width(66)),
            segment heights hubstyle.height("segment", 22),
            the tool button height hubstyle.height("small", 24) ...
    #  Apply all, BakeAcross, Release on one row (2026-10-08)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3),
                                 (3, "both", 3)])
    hubstyle.mark(cmds.button(label="Apply all",
                              height=hubstyle.height("button", 32), ...), "primary", "check")
    hubstyle.mark(cmds.button(label="BakeAcross",
                              height=hubstyle.height("button", 28), ...), "secondary", "link")
    hubstyle.mark(cmds.button(label="Release",
                              height=hubstyle.height("button", 28),
                              width=hubstyle.pick(78, 90), ...), "secondary", "unlink")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=54), "status")
```

(`...` = the existing arguments, unchanged.) `_set_chooser` ends with:

```python
    try:
        cmds.rowLayout(CHOOSER_ROW, edit=True, manage=len(labels) > 1)
    except (RuntimeError, TypeError, ValueError):
        pass
```

`_status` gains `hubstyle.tell(STATUS, <the text it wrote>)`.

Shared `build_panel`:

```python
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="connecting...", align="left"),
                  "subtitle")
    if hubstyle.skinning():
        #  author and name on one row, no labels: the placeholders say which
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                       columnWidth2=(110, 200),
                       columnAttach=[(1, "both", 0), (2, "both", 3)])
        cmds.textField(AUTHOR_FIELD, text=sender_name(),
                       placeholderText="author",
                       height=hubstyle.height("field", 24),
                       annotation="your name, as your colleagues see it",
                       changeCommand=_author_changed)
        cmds.textField(FILE_NAME_FIELD, text="",
                       placeholderText="name (empty: the scene's)",
                       height=hubstyle.height("field", 24))
        cmds.setParent("..")
    else:
        ... the two labelled rows exactly as now ...
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3)])
    ... Send scene (height=hubstyle.height("button", 32)) and Send file...
        (height=hubstyle.height("button", 32), width=hubstyle.pick(104, 110)) ...
    cmds.setParent("..")
    cmds.textScrollList(LIST, ..., height=LIST_HEIGHT, ...)    # unchanged
    hubstyle.grip(cmds.separator(LIST_GRIP, height=8, style="none"), LIST)
    cmds.rowLayout(numberOfColumns=4, ...)          # as now
    ... Open, Import (heights hubstyle.height("button", 28)),
        Save to... label=hubstyle.pick("", "Save to..."), width=hubstyle.pick(26, 90),
        Delete (width=hubstyle.pick(26, 64)) ...
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, ...), "status")      # unchanged
```

`_status` gains `hubstyle.tell(STATUS, <text>)` (read the function: it may already fall back to `hub.say` with no control - keep that path, add `tell` only where the control was written).

- [ ] **Step 4: Run the two modules and the suite -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): Connections and Shared compact, a grip under the Shared list`).

---

### Task 9: Retarget, Graph Overlay, CoM, Pose Library, Studio, Colour, Update

**Files:**
- Modify: `SkeldarAnim/maya_rig_retarget.py`, `SkeldarAnim/maya_graphoverlay/mode.py`, `SkeldarAnim/maya_com/panel.py`, `SkeldarAnim/maya_poselib/window.py` (build_panel ONLY - the Pose Library session owns the rest; keep `NOTE`'s text whatever it is), `SkeldarAnim/maya_vpstudio.py`, `SkeldarAnim/maya_colour.py`, `SkeldarAnim/maya_update.py`
- Test: `tests/test_hub_sections.py` (or each module's own test file where its `build_panel` is tested: `test_graphoverlay_mode.py`, `test_poselib_window.py`, `test_vpstudio.py`, `test_colour_tool.py`, `test_update.py`)

**Interfaces:** every writer below calls `hubstyle.tell(STATUS, first_line, viewport=...)`: `True` for `maya_rig_retarget._show`, `maya_graphoverlay.mode._show`, `maya_colour._status`, `maya_vpstudio._status` (they show it in the viewport themselves); `False` for `maya_com.panel.status`, `maya_update._status`.

- [ ] **Step 1: Failing tests** - one per module, the same shape:

```python
    def test_the_status_tells_the_hub(self):
        heard = []
        style.listen(lambda c, t, v: heard.append((c, t, v)))
        try:
            module._show("Retargeted")          # the module's writer
        finally:
            style._LISTENERS[:] = []
        self.assertIn((module.STATUS, "Retargeted", True), heard)
```

plus the arrangement tests:
- Retarget: the `_bones_row` rowLayout holds the segments AND the Retarget button (no "Bones" text in the skin build); the hint is a `note` mark (unchanged role).
- CoM: row 1 = Add CoM, Rebuild (label `pick("", "Rebuild")`), Remove, Select CoM (4 columns); row 2 = Trail, Floor, segments, the int field (no "frames" text in the skin; the field's annotation says frames).
- Studio: `cmds.flowLayout` holds the ten chips; chip labels in the skin are `SHORT_CHECK[key]`; the full label is in the annotation.
- Colour: one rowLayout of 8 swatches; `TAKEN` is a `subtitle` (already).
- Update: `INSTALLED` stays `subtitle` with `wordWrap` False and no height in the skin; the button height `hubstyle.height("button", 36)`.
- Pose Library: the button height `hubstyle.height("button", 34)`; the note stays a `note` mark.
- Graph Overlay: the button height `hubstyle.height("button", 34)`.

- [ ] **Step 2: Run, expect failures.**
- [ ] **Step 3: Implement**, module by module:

`maya_rig_retarget`: `_show` adds `hubstyle.tell(STATUS, first, viewport=True)` after its label write. `_bones_row` builds `cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnAttach=[(1, "left", 0), (2, "both", 3), (3, "left", 3)])`: the "Bones" text only when `not hubstyle.skinning()` (else a zero-width text: `cmds.text(label="", width=1)` keeps the column count), the segments (labels: `{"auto": "Auto", "rotation": "Rot.", "stretch": "Stretch"}` in the skin via `hubstyle.pick`, else `rm.LABELS`), then the Retarget button (moved here from `build_panel`, `height=hubstyle.height("button", 34)`, `width=hubstyle.pick(110, 100)`, its annotation `PANEL_NOTE`). `build_panel` keeps the note, calls `_bones_row()`, the status.

`maya_graphoverlay/mode.py`: `_show` tells (`viewport=True`); the button height through `hubstyle.height("button", 34)`; `rowSpacing=hubstyle.row_spacing(6)`.

`maya_com/panel.py`: `status()` tells; the build as listed (first row 4 columns: Add CoM adjustable, Rebuild `pick("", "Rebuild")` `width=pick(26, 80)`, Remove `width=pick(26, 72)`, Select CoM `label=pick("Select", "Select CoM")` `width=pick(56, 90)`; second row: the two chips, the segments, the int field `width=pick(36, 48)` with `annotation="Around: this many frames each way"`; the "frames" text only in the classic build). All heights through `hubstyle.height`.

`maya_poselib/window.py`: in `build_panel` only - `rowSpacing=hubstyle.row_spacing(6)`, the button `height=hubstyle.height("button", 34)`. Nothing else in the file.

`maya_vpstudio.py`:

```python
#  The compact skin's chip labels (2026-10-08): the full label is the tooltip
SHORT_CHECK = {"floor": "Floor", "shadows": "Shadows", "ao": "AO",
               "motion_blur": "Blur", "anti_alias": "AA", "bloom": "Bloom",
               "fog": "Haze", "dof": "DoF", "clean": "Clean",
               "backdrop": "Backdrop"}
```

the ten chips go into `cmds.flowLayout(wrap=True, columnSpacing=3)` in the skin (the classic build keeps its pairs of rowLayouts), each `label=hubstyle.pick(SHORT_CHECK[key], label)`, `annotation=label + " - " + note`; the two `floatSliderGrp`s get `label=hubstyle.pick("Bright", "Brightness ")` / `"Rotate"`, `columnWidth3=hubstyle.pick((44, 40, 150), (70, 45, 150))`, `height=hubstyle.height("small", 22)`; the buttons `height=hubstyle.height("button", 32)`, Restore `label=hubstyle.pick("Restore", "Restore Viewport")`, `width=hubstyle.pick(80, 130)`. `_status` tells (`viewport=True`, it calls headsUpMessage).

`maya_colour.py`: in the skin the eight swatches go into ONE rowLayout of 8 columns (`cell = (WIDTH - 16) // 8` there; the classic build keeps 4 a row: `columns = hubstyle.pick(8, COLUMNS)`), swatch `height=hubstyle.height("small", 28)`, label `hubstyle.pick("", entry.name)`; Paint / Next free colour heights through `hubstyle.height`, Next free `label=hubstyle.pick("Next free", "Next free colour")`, `width=hubstyle.pick(84, 130)`. `_status` tells (`viewport=True`).

`maya_update.py`: `build_panel` - `INSTALLED` `wordWrap=hubstyle.pick(False, True)`, `height=hubstyle.pick(18, 36)`; the button `height=hubstyle.height("button", 36)`. `_status` tells (`viewport=False`) where it writes the control.

Every one of these builders: `rowSpacing=hubstyle.row_spacing(6)`.

- [ ] **Step 4: Run every touched test module, then the suite -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): the remaining cards compact; every status on the hub's line`).

---

### Task 10: The edge panel's rules (pure)

**Files:**
- Create: `SkeldarAnim/maya_edgerules.py`
- Test: `tests/test_edgerules.py`

**Interfaces (produced):**

```python
EDGE_VAR = "skeldarAnimHub_edge"
WIDTH_VAR = "skeldarAnimHub_edgeWidth"
WIDTH, MIN_WIDTH, MAX_WIDTH = 360, 280, 700     # logical
DWELL_MS, HIDE_MS, RETRY_MS = 100, 350, 150
IN_MS, OUT_MS = 180, 150
SENSOR_PX = 2                                   # physical
GRIP_PX = 5                                     # logical
def clamp_width(width) -> int
def panel_rect(work_area, width, scale) -> (x, y, w, h)   # physical
def sensor_rect(work_area) -> (x, y, w, h)
def may_reveal(edge_on, shown, buttons, app_active) -> bool
def hide_blockers(pinned=False, held=False, inside=False, buttons=False,
                  popup=False, modal=False, typing=False) -> list of str
def slide_x(t, width, showing) -> int
def contains(rect, point, margin=0) -> bool
class Hold: held, entered; enter(); leave() -> bool released; press_outside() -> bool released
```

- [ ] **Step 1: Failing tests** - `tests/test_edgerules.py`:

```python
"""maya_edgerules: the hub's edge panel as rules (2026-10-08)."""

import subprocess
import sys
import unittest

import maya_edgerules as rules


class Width(unittest.TestCase):

    def test_clamp(self):
        self.assertEqual(rules.clamp_width(100), 280)
        self.assertEqual(rules.clamp_width(360.4), 360)
        self.assertEqual(rules.clamp_width(2000), 700)

    def test_the_panel_stands_on_the_work_area_s_left_edge_full_height(self):
        self.assertEqual(rules.panel_rect((0, 0, 2560, 1528), 360, 1.5),
                         (0, 0, 540, 1528))

    def test_on_a_screen_to_the_right(self):
        self.assertEqual(rules.panel_rect((2560, 0, 3840, 2088), 400, 1.0),
                         (2560, 0, 400, 2088))

    def test_never_wider_than_the_screen(self):
        self.assertEqual(rules.panel_rect((0, 0, 300, 800), 700, 1.0),
                         (0, 0, 300, 800))

    def test_the_sensor(self):
        self.assertEqual(rules.sensor_rect((0, 0, 2560, 1528)),
                         (0, 0, 2, 1528))


class Reveal(unittest.TestCase):

    def test_only_with_edge_on_hidden_no_button_and_maya_active(self):
        self.assertTrue(rules.may_reveal(True, False, False, True))
        self.assertFalse(rules.may_reveal(False, False, False, True))
        self.assertFalse(rules.may_reveal(True, True, False, True))
        self.assertFalse(rules.may_reveal(True, False, True, True))
        self.assertFalse(rules.may_reveal(True, False, False, False))


class Hide(unittest.TestCase):

    def test_nothing_blocks(self):
        self.assertEqual(rules.hide_blockers(), [])

    def test_each_reason(self):
        for key in ("pinned", "held", "inside", "buttons", "popup", "modal",
                    "typing"):
            self.assertEqual(rules.hide_blockers(**{key: True}), [key])

    def test_several(self):
        self.assertEqual(rules.hide_blockers(pinned=True, popup=True),
                         ["pinned", "popup"])


class Hold(unittest.TestCase):

    def test_a_command_reveal_holds_until_entered_and_left(self):
        hold = rules.Hold()
        hold.start()
        self.assertTrue(hold.held)
        self.assertFalse(hold.leave())          # never entered: still held
        hold.enter()
        self.assertTrue(hold.leave())           # entered and left: released
        self.assertFalse(hold.held)

    def test_a_press_outside_releases(self):
        hold = rules.Hold()
        hold.start()
        self.assertTrue(hold.press_outside())
        self.assertFalse(hold.held)

    def test_not_held_nothing_to_release(self):
        hold = rules.Hold()
        self.assertFalse(hold.leave())
        self.assertFalse(hold.press_outside())


class Slide(unittest.TestCase):

    def test_in_from_off_the_edge_to_zero(self):
        self.assertEqual(rules.slide_x(0.0, 540, True), -540)
        self.assertEqual(rules.slide_x(1.0, 540, True), 0)
        xs = [rules.slide_x(i / 20.0, 540, True) for i in range(21)]
        self.assertEqual(xs, sorted(xs))

    def test_out_from_zero_off_the_edge(self):
        self.assertEqual(rules.slide_x(0.0, 540, False), 0)
        self.assertEqual(rules.slide_x(1.0, 540, False), -540)
        xs = [rules.slide_x(i / 20.0, 540, False) for i in range(21)]
        self.assertEqual(xs, sorted(xs, reverse=True))

    def test_eased(self):
        # ease-out in: more than half way at half time
        self.assertGreater(rules.slide_x(0.5, 100, True), -50)


class Contains(unittest.TestCase):

    def test_contains(self):
        self.assertTrue(rules.contains((0, 0, 10, 10), (5, 5)))
        self.assertFalse(rules.contains((0, 0, 10, 10), (10, 5)))
        self.assertTrue(rules.contains((0, 0, 10, 10), (11, 5), margin=2))


class Purity(unittest.TestCase):

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); "
                "import maya_edgerules; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)
```

- [ ] **Step 2: Run, expect ImportError.**
- [ ] **Step 3: Implement** `SkeldarAnim/maya_edgerules.py`:

```python
"""maya_edgerules - the hub's edge panel as rules (stdlib only).

The animator (2026-10-08): «что бы наша полка получила возможность работать
как виджет ... когда я подношу мышку к левому краю экрана то появляется наша
полка когда убираю то полка скрывается». Asked: a switch in ⋮, waiting from
Maya's start, the full height of the screen, a 📌 pin.

Everything the panel decides is a function of plain values here; maya_hubedge
is the Qt that measures those values and moves the windows.

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

EDGE_VAR = "skeldarAnimHub_edge"
WIDTH_VAR = "skeldarAnimHub_edgeWidth"
WIDTH, MIN_WIDTH, MAX_WIDTH = 360, 280, 700     # logical px (the dock's 360)
#  The cursor must rest on the edge this long: thrown into the top-left
#  corner for File, or crossing into a monitor on the left, it does not.
DWELL_MS = 100
HIDE_MS = 350           # after the cursor left
RETRY_MS = 150          # a postponed hide asks again this often
IN_MS, OUT_MS = 180, 150
SENSOR_PX = 2           # physical px: the strip at the screen's left edge
GRIP_PX = 5             # logical px: the width grip on the panel's right


def clamp_width(width):
    return int(max(MIN_WIDTH, min(MAX_WIDTH, int(round(width)))))


def panel_rect(work_area, width, scale):
    """The panel in physical px: against the work area's left edge, its full
    height, `width` logical px wide (clamped, and never wider than the
    area)."""
    x, y, w, h = work_area
    pw = int(round(clamp_width(width) * float(scale or 1.0)))
    return (int(x), int(y), int(min(w, pw)), int(h))


def sensor_rect(work_area):
    x, y, _w, h = work_area
    return (int(x), int(y), SENSOR_PX, int(h))


def may_reveal(edge_on, shown, buttons, app_active):
    """The cursor at the edge may bring the panel out: edge mode on, the
    panel hidden, no mouse button held (a window or marquee dragged to the
    edge is not a request), Maya the active application."""
    return bool(edge_on and not shown and not buttons and app_active)


def hide_blockers(pinned=False, held=False, inside=False, buttons=False,
                  popup=False, modal=False, typing=False):
    """Why the panel must stay, in a fixed order (empty: it may go).

    pinned  the 📌 is on
    held    it was opened by a command and not yet visited (Hold)
    inside  the cursor is over it
    buttons a mouse button is down - a drag from the panel into the
            viewport would break if its source vanished
    popup   a dropdown's list, a menu is open
    modal   a dialog is up
    typing  a text field of the panel has the keyboard focus"""
    reasons = []
    for name, value in (("pinned", pinned), ("held", held),
                        ("inside", inside), ("buttons", buttons),
                        ("popup", popup), ("modal", modal),
                        ("typing", typing)):
        if value:
            reasons.append(name)
    return reasons


class Hold(object):
    """A reveal by command (the shelf button, a hotkey, a tool's
    show_window) holds the panel until the cursor has entered it and left,
    or a press lands outside it."""

    def __init__(self):
        self.held = False
        self.entered = False

    def start(self):
        self.held, self.entered = True, False

    def enter(self):
        if self.held:
            self.entered = True

    def leave(self):
        """True when this leave released the hold."""
        if self.held and self.entered:
            self.held = self.entered = False
            return True
        return False

    def press_outside(self):
        if self.held:
            self.held = self.entered = False
            return True
        return False


def slide_x(t, width, showing):
    """The panel's x inside its host at progress `t` (0..1): from -width to
    0 easing out while showing, from 0 to -width easing in while hiding."""
    t = max(0.0, min(1.0, float(t)))
    if showing:
        k = 1.0 - (1.0 - t) ** 3
        return int(round(-width * (1.0 - k)))
    k = t ** 3
    return int(round(-width * k))


def contains(rect, point, margin=0):
    x, y, w, h = rect
    px, py = point
    return (x - margin <= px < x + w + margin
            and y - margin <= py < y + h + margin)
```

- [ ] **Step 4: Run `tests.test_edgerules` -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): the edge panel's rules`).

---

### Task 11: The edge panel in Qt - host, sensor, controller

**Files:**
- Create: `SkeldarAnim/maya_hubedge.py`
- Test: `tests/test_hubedge.py`

**Interfaces (produced):**

```python
HOST = "skeldarAnimHubEdge"
SENSOR = "skeldarAnimHubEdgeSensor"
SLOT = "skeldarAnimHubEdgeSlot"
class Edge(object):
    def __init__(self, scale=1.0, parent=None, width=rules.WIDTH,
                 motion=lambda: True, on_width=None, work_area=None,
                 cursor=None, buttons=None, app_active=None)
    host, sensor, slot                 # QWidgets (slot holds the Skin root)
    shown -> bool (property)
    pinned -> bool
    def place(self)                    # geometry from the work area
    def reveal(self, hold=False)
    def conceal(self)
    def set_pinned(self, on)
    def set_width(self, logical)       # clamped, laid out, on_width called
    def sensor_entered(self) / sensor_left(self) / dwell_done(self)
    def host_entered(self) / host_left(self) / hide_due(self)
    def press_at(self, global_point)   # an application press (hold release)
    def blockers(self) -> list
    def destroy(self)
def destroy_all()                       # every HOST / SENSOR top-level, by name
def state() -> dict                      # sys._skeldar_hubedge {"edge": Edge or None}
```

Seams for tests (constructor arguments): `work_area()` -> (x, y, w, h); `cursor()` -> (x, y) global physical; `buttons()` -> bool; `app_active()` -> bool. Defaults read Qt: Maya's main window's screen `availableGeometry()`, `QCursor.pos()`, `QApplication.mouseButtons() != NoButton`, `QApplication.applicationState() == Qt.ApplicationActive`.

- [ ] **Step 1: Failing tests** - `tests/test_hubedge.py` (offscreen Qt; every timer driven by calling the controller's handlers directly, animations off unless the test is about the slide):

```python
"""maya_hubedge: the edge panel's windows and controller, offscreen."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

import maya_edgerules as rules
import maya_hubedge as hubedge


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class EdgeCase(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.point = (500, 400)
        self.down = False
        self.active = True
        self.widths = []
        self.edge = hubedge.Edge(
            scale=1.0, width=360, motion=lambda: False,
            on_width=self.widths.append,
            work_area=lambda: (0, 0, 1600, 900),
            cursor=lambda: self.point, buttons=lambda: self.down,
            app_active=lambda: self.active)

    def tearDown(self):
        self.edge.destroy()

    def test_built_hidden_the_sensor_up(self):
        self.assertFalse(self.edge.shown)
        self.assertFalse(self.edge.host.isVisible())
        self.assertTrue(self.edge.sensor.isVisible())
        self.assertEqual(self.edge.sensor.geometry().getRect(),
                         (0, 0, rules.SENSOR_PX, 900))

    def test_dwell_on_the_edge_reveals(self):
        self.point = (0, 300)
        self.edge.sensor_entered()
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.host.geometry().getRect(), (0, 0, 360, 900))
        self.assertEqual(self.edge.slot.x(), 0)
        self.assertFalse(self.edge.sensor.isVisible())

    def test_a_dwell_cut_short_reveals_nothing(self):
        self.point = (0, 300)
        self.edge.sensor_entered()
        self.point = (40, 300)                  # moved off before the timer
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def test_no_reveal_with_a_button_held_or_maya_inactive(self):
        self.point = (0, 300)
        self.down = True
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)
        self.down, self.active = False, False
        self.edge.dwell_done()
        self.assertFalse(self.edge.shown)

    def _shown(self):
        self.point = (0, 300)
        self.edge.dwell_done()
        self.assertTrue(self.edge.shown)

    def test_leaving_hides(self):
        self._shown()
        self.point = (900, 300)
        self.edge.host_left()
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)
        self.assertTrue(self.edge.sensor.isVisible())

    def test_the_cursor_back_inside_keeps_it(self):
        self._shown()
        self.point = (100, 300)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.assertEqual(self.edge.blockers(), ["inside"])

    def test_a_held_button_postpones(self):
        self._shown()
        self.point, self.down = (900, 300), True
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.down = False
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_pinned_stays(self):
        self._shown()
        self.edge.set_pinned(True)
        self.point = (900, 300)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)
        self.edge.set_pinned(False)
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_command_reveal_holds_until_visited(self):
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.edge.hide_due()
        self.assertTrue(self.edge.shown)          # never entered
        self.point = (100, 300)
        self.edge.host_entered()
        self.point = (900, 300)
        self.edge.host_left()
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_press_outside_releases_the_hold(self):
        self.point = (900, 300)
        self.edge.reveal(hold=True)
        self.edge.press_at((900, 300))
        self.edge.hide_due()
        self.assertFalse(self.edge.shown)

    def test_a_focused_field_postpones(self):
        self._shown()
        field = QtWidgets.QLineEdit(self.edge.slot)
        field.show()
        self.edge.host.activateWindow()
        field.setFocus()
        self.point = (900, 300)
        if self.app.focusWidget() is field:          # offscreen may refuse focus
            self.assertIn("typing", self.edge.blockers())

    def test_the_width_grip_clamps_and_reports(self):
        self.edge.set_width(1000)
        self.assertEqual(self.widths[-1], rules.MAX_WIDTH)
        self._shown()
        self.assertEqual(self.edge.host.width(), rules.MAX_WIDTH)

    def test_destroy_all_finds_them_by_name(self):
        other = hubedge.Edge(scale=1.0, motion=lambda: False,
                             work_area=lambda: (0, 0, 800, 600),
                             cursor=lambda: (0, 0), buttons=lambda: False,
                             app_active=lambda: True)
        self.assertGreaterEqual(hubedge.destroy_all(), 2)
        self.assertFalse(other.alive())


class Slide(unittest.TestCase):

    def test_a_slide_moves_the_slot_in_from_off_the_edge(self):
        _app()
        edge = hubedge.Edge(scale=1.0, motion=lambda: True,
                            work_area=lambda: (0, 0, 800, 600),
                            cursor=lambda: (0, 10), buttons=lambda: False,
                            app_active=lambda: True)
        try:
            edge.reveal()
            xs = []
            loop_until = QtCore.QDeadlineTimer(1500)
            while edge.sliding() and not loop_until.hasExpired():
                QtWidgets.QApplication.processEvents()
                xs.append(edge.slot.x())
            self.assertEqual(edge.slot.x(), 0)
            self.assertEqual(xs, sorted(xs))
        finally:
            edge.destroy()
```

- [ ] **Step 2: Run, expect ImportError.**

- [ ] **Step 3: Implement** `SkeldarAnim/maya_hubedge.py`. Structure (write it whole; keep the comments' WHY):

```python
"""maya_hubedge - the hub as a panel sliding out of the left screen edge.

2026-10-08 (the animator: «когда я подношу мышку к левому краю экрана то
появляется наша полка когда убираю то полка скрывается»). Three windows of
ours, each a frameless Qt.Tool owned by Maya's main window (so above Maya,
never above another application, gone with Maya minimized):

    host    the panel: the work area's left edge, its full height; holds
            the SLOT, which holds the Skin's root. A slide moves the SLOT
            inside the host - no window crosses into a monitor on the
            left, nothing is laid out again per frame.
    sensor  2 physical px over the edge at window opacity 1/255: Qt keeps
            it layered and it still takes the mouse (CLAUDE.md trap 110;
            the Graph Overlay's ghost measured alpha 1 hit-testable).
            Shown only while the panel is hidden.
    grip    5 logical px on the host's right: drag the width.

Every decision is maya_edgerules'. The cursor, the buttons, the work area
and whether Maya is the active application come through constructor seams,
so a verify drives the controller without moving the animator's mouse.
The Edge object lives on `sys._skeldar_hubedge` (an install purges our
modules; trap 111) and every window is found again by its objectName
(`destroy_all`, trap 102's family).

Spec: docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md
"""

import sys

import maya_edgerules as rules
import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

HOST = "skeldarAnimHubEdge"
SENSOR = "skeldarAnimHubEdgeSensor"
SLOT = "skeldarAnimHubEdgeSlot"
GRIP = "skeldarAnimHubEdgeGrip"


def state():
    st = getattr(sys, "_skeldar_hubedge", None)
    if st is None:
        st = {"edge": None}
        sys._skeldar_hubedge = st
    return st


def main_window():
    """Maya's main window, or None (tests, mayapy)."""
    try:
        import maya.OpenMayaUI as omui
        q = hubqt.qt()
        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return q.shiboken.wrapInstance(int(ptr), q.QtWidgets.QWidget)
    except Exception:                                        # noqa: BLE001
        pass
    return None


def destroy_all():
    """Delete every host, sensor of ours standing, found by name."""
    q = hubqt.qt()
    count = 0
    for widget in list(q.QtWidgets.QApplication.topLevelWidgets()):
        try:
            if widget.objectName() in (HOST, SENSOR):
                widget.hide()
                widget.setParent(None)
                q.shiboken.delete(widget)
                count += 1
        except RuntimeError:
            pass
    return count
```

Then `_classes()` building three QWidget subclasses once (cache in a dict like `maya_hubqt._CLASSES`):
- `Sensor(QWidget)`: `enterEvent` -> `self.edge.sensor_entered()`, `leaveEvent` -> `self.edge.sensor_left()`.
- `Host(QWidget)`: `enterEvent` -> `host_entered()`, `leaveEvent` -> `host_left()`, `resizeEvent` -> `self.edge._fit_slot()`; `paintEvent` paints `TOKENS["panel"]` and a 1 px `TOKENS["inset_line"]` line on the right edge (replaces the spec's "soft shadow": a translucent top-level holding Maya's widgets is untried, the line costs nothing; record that in the docstring).
- `WidthGrip(QWidget)`: cursor `SizeHorCursor`; press records global x and the logical width; move -> `edge.set_width(start + dx / scale, save=False)`; release -> `edge.set_width(current, save=True)`.

`Edge.__init__`: build `host` (`Qt.Tool | Qt.FramelessWindowHint`, parent `parent or main_window()`, `WA_ShowWithoutActivating`), `slot` (child of host, `QVBoxLayout` zero margins, named `SLOT` and its layout `SLOT + "Layout"`), `grip` (child of host, raised), `sensor` (Tool | Frameless, `setWindowOpacity(1.0 / 255)`, `WA_ShowWithoutActivating`); the timers `dwell` (single, `DWELL_MS`), `hide` (single, `HIDE_MS`), `retry` (single, `RETRY_MS`) as children of the host; `self.hold = rules.Hold()`; `self.pinned = False`; `self._anim = None`; `self._shown = False`; an application event filter (child of the host) that calls `press_at` on `MouseButtonPress` with `event.globalPosition()` when the press is not inside the host; `place()`; `sensor.show()`; `host.hide()`.

Methods (each a few lines; the rules decide):

```python
    @property
    def shown(self):
        return self._shown

    def alive(self):
        return hubqt._valid(self.host)

    def work_area(self):
        return self._work_area() if self._work_area else _maya_work_area()

    def place(self):
        area = self.work_area()
        x, y, w, h = rules.panel_rect(area, self.width, self.scale)
        self.host.setGeometry(x, y, w, h)
        sx, sy, sw, sh = rules.sensor_rect(area)
        self.sensor.setGeometry(sx, sy, sw, sh)
        grip = hubstyle.px(rules.GRIP_PX, self.scale)
        self.grip.setGeometry(w - grip, 0, grip, h)
        self._fit_slot()

    def _fit_slot(self):
        x = self.slot.x() if self._anim is not None else (
            0 if self._shown else -self.host.width())
        self.slot.setGeometry(x, 0, self.host.width(), self.host.height())

    def reveal(self, hold=False):
        if hold:
            self.hold.start()
        self.hide.stop()
        self.retry.stop()
        if self._shown and self._anim is None:
            self.host.raise_()
            return
        self._shown = True
        self.place()
        self.sensor.hide()
        self.host.show()
        self.host.raise_()
        self.grip.raise_()
        self._slide(True)

    def conceal(self):
        if not self._shown:
            return
        self._shown = False
        self._slide(False)

    def _slide(self, showing):
        self._stop_anim()
        width = self.host.width()
        if not self.motion():
            self._slide_done(showing)
            return
        q = hubqt.qt()
        anim = q.QtCore.QVariantAnimation(self.host)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(rules.IN_MS if showing else rules.OUT_MS)
        anim.valueChanged.connect(
            lambda t: self.slot.move(rules.slide_x(t, width, showing), 0))
        anim.finished.connect(lambda: self._slide_done(showing))
        self._anim = anim
        anim.start()

    def _slide_done(self, showing):
        self._stop_anim()
        self.slot.move(0 if showing else -self.host.width(), 0)
        if not showing:
            self.host.hide()
            self.sensor.show()

    def sliding(self):
        return self._anim is not None

    def sensor_entered(self):
        self.dwell.start()

    def sensor_left(self):
        self.dwell.stop()

    def dwell_done(self):
        area = self.work_area()
        if not rules.contains(rules.sensor_rect(area), self.cursor(), margin=1):
            return
        if rules.may_reveal(True, self._shown, self.buttons(),
                            self.app_active()):
            self.reveal()

    def host_entered(self):
        self.hide.stop()
        self.retry.stop()
        self.hold.enter()

    def host_left(self):
        self.hold.leave()
        if self._shown:
            self.hide.start()

    def press_at(self, point):
        if self._shown and not rules.contains(self._host_rect(), point):
            if self.hold.press_outside():
                self.hide.start()

    def blockers(self):
        q = hubqt.qt()
        app = q.QtWidgets.QApplication
        focus = app.focusWidget()
        typing = bool(
            focus is not None and self.host.isAncestorOf(focus)
            and isinstance(focus, (q.QtWidgets.QLineEdit,
                                   q.QtWidgets.QAbstractSpinBox,
                                   q.QtWidgets.QTextEdit))
            and self.host.isActiveWindow())
        return rules.hide_blockers(
            pinned=self.pinned, held=self.hold.held,
            inside=rules.contains(self._host_rect(), self.cursor()),
            buttons=self.buttons(),
            popup=app.activePopupWidget() is not None,
            modal=app.activeModalWidget() is not None, typing=typing)

    def hide_due(self):
        if not self._shown:
            return
        if self.blockers():
            self.retry.start()
            return
        self.conceal()

    def set_pinned(self, on):
        self.pinned = bool(on)
        if not on and self._shown:
            self.hide.start()

    def set_width(self, logical, save=True):
        self.width = rules.clamp_width(logical)
        self.place()
        if save and self.on_width:
            self.on_width(self.width)

    def destroy(self):
        self._stop_anim()
        q = hubqt.qt()
        app = q.QtWidgets.QApplication.instance()
        for widget in (self.sensor, self.host):
            if hubqt._valid(widget):
                widget.hide()
                widget.setParent(None)
                q.shiboken.delete(widget)
```

`retry.timeout` -> `hide_due`; `hide.timeout` -> `hide_due`; `dwell.timeout` -> `dwell_done`. `_host_rect()` answers `self.host.geometry().getRect()`. The default seams:

```python
def _maya_work_area():
    q = hubqt.qt()
    window = main_window()
    screen = (window.screen() if window is not None
              else q.QtGui.QGuiApplication.primaryScreen())
    return screen.availableGeometry().getRect()
```

cursor: `q.QtGui.QCursor.pos()` -> `(p.x(), p.y())`; buttons: `QApplication.mouseButtons() != Qt.NoButton`; app_active: `QGuiApplication.applicationState() == Qt.ApplicationActive`. `motion` default `hubmotion.enabled`.

- [ ] **Step 4: Run `tests.test_hubedge` -> PASS** (offscreen: if `QWidget.screen()` or window opacity are refused offscreen, the seams already avoid them - fix the code, not the test). Then the suite.
- [ ] **Step 5: Commit** (`feat(hub): the edge panel's windows and controller`).

---

### Task 12: The hub in the edge panel - mode switch, build, show, relay to the viewport

**Files:**
- Modify: `SkeldarAnim/maya_hub.py`
- Modify: `SkeldarAnim/install.py` (`rebuild_open_hub` and its caller: rebuild when the edge panel stands too; payload rows for `maya_edgerules.py`, `maya_hubedge.py`)
- Test: `tests/test_hub.py`, `tests/test_install.py`

**Interfaces:**
- Consumes: Tasks 2, 10, 11.
- Produces in `maya_hub`: `edge_on()`, `set_edge(on)`, `start()`, `stop()`, `edge()` (the standing Edge or None), `_press_pin(on)`, `_told(key, text, viewport)` (fills Task 4's stub), `show(key)` and `is_open()` aware of the edge.

- [ ] **Step 1: Failing tests** (`tests/test_hub.py`, with the module's fake cmds and a fake `hubedge` injected through a seam `maya_hub._hubedge()` that returns the module; give the fake an `Edge` recording `reveal(hold)`, `conceal`, `set_pinned`, `destroy`, `shown`):

```python
    def test_edge_mode_is_off_by_default(self):
        self.assertFalse(hub.edge_on())

    def test_set_edge_on_drops_the_dock_and_builds_the_edge(self):
        self.fake.workspace[hub.CONTROL] = {}
        hub.set_edge(True)
        self.assertEqual(self.fake.optionvars[hub.EDGE_VAR], 1)
        self.fake.run_deferred()
        self.assertIn(hub.CONTROL, self.fake.deleted)
        self.assertTrue(self.edges[-1].revealed_with_hold)

    def test_set_edge_off_destroys_the_edge_and_opens_the_dock(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.set_edge(False)
        self.fake.run_deferred()
        self.assertTrue(self.edges[-1].destroyed)
        self.assertIn(hub.CONTROL, self.fake.workspace)

    def test_show_in_edge_mode_reveals_and_holds(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        hub.show("retarget")
        self.assertTrue(self.edges[-1].revealed_with_hold)
        self.assertNotIn(hub.CONTROL, self.fake.workspace)

    def test_start_does_nothing_in_dock_mode(self):
        hub.start()
        self.assertEqual(self.edges, [])

    def test_the_uiscript_in_edge_mode_builds_nothing_in_the_dock(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        self.fake.workspace[hub.CONTROL] = {}
        hub.build()
        self.fake.run_deferred()
        self.assertIn(hub.CONTROL, self.fake.deleted)

    def test_a_status_while_hidden_goes_to_the_viewport(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        self.edges[-1].shown = False
        hub._told("characters", "Imported A_Jump", False)
        msgs = [c for c in self.fake.calls if c[0] == "inViewMessage"]
        self.assertTrue(msgs)

    def test_not_when_shown_or_when_the_writer_showed_it(self):
        self.fake.optionvars[hub.EDGE_VAR] = 1
        hub.start()
        self.edges[-1].shown = True
        hub._told("characters", "x", False)
        self.edges[-1].shown = False
        hub._told("retarget", "y", True)
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "inViewMessage"])

    def test_edge_mode_needs_the_skin(self):
        self.fake.optionvars[hub.CLASSIC_VAR] = 1
        self.assertFalse(hub.set_edge(True))
        self.assertNotEqual(self.fake.optionvars.get(hub.EDGE_VAR), 1)
```

(`_build_skin` needs Qt: in these tests stub `hub._build_skin` / `hub._qt_available` the way the file's existing tests do.)

`tests/test_install.py`: the payload holds `maya_edgerules.py` and `maya_hubedge.py`; `rebuild_open_hub` is scheduled when the edge host stands (inject a seam `install._edge_standing = lambda: True`).

- [ ] **Step 2: Run, expect failures.**

- [ ] **Step 3: Implement** in `maya_hub.py`:

```python
import maya_edgerules as edgerules

EDGE_VAR = edgerules.EDGE_VAR


def _hubedge():
    """The edge panel's Qt (a seam for tests)."""
    import maya_hubedge
    return maya_hubedge


def edge_on():
    """The hub lives in the edge panel (⋮ -> Edge panel; off by default):
    only with the skin."""
    if classic_asked() or not _qt_available():
        return False
    if cmds.optionVar(exists=EDGE_VAR):
        return bool(cmds.optionVar(query=EDGE_VAR))
    return False


def edge():
    """The Edge standing (maya_hubedge.state()), alive, or None."""
    try:
        current = _hubedge().state().get("edge")
    except Exception:                                        # noqa: BLE001
        return None
    return current if current is not None and current.alive() else None


def _edge_width():
    if cmds.optionVar(exists=edgerules.WIDTH_VAR):
        return cmds.optionVar(query=edgerules.WIDTH_VAR)
    return edgerules.WIDTH


def _save_edge_width(width):
    cmds.optionVar(intValue=(edgerules.WIDTH_VAR, int(width)))


def _ensure_edge():
    """The edge panel built (hidden) with the skin in it; the Edge."""
    global _SKIN, _BUILT_HERE
    current = edge()
    if current is not None and is_skinned():
        return current
    he = _hubedge()
    he.destroy_all()
    current = he.Edge(scale=_scale(), width=_edge_width(),
                      on_width=_save_edge_width)
    he.state()["edge"] = current
    if _SKIN is not None:
        _SKIN.destroy()
    _SKIN = _build_skin(host=current.slot)
    _SKIN.set_edge_mode(True)
    _BUILT_HERE = True
    return current
```

`_build_skin(host=None)`: `host` None keeps today's path (`qt.destroy_roots(CONTROL)`, `qt.host_widget(CONTROL)`); a given host skips `destroy_roots` and builds `qt.Skin(host, ...)`.

```python
def start():
    """The startup plug-in's call: in edge mode the panel waits, hidden."""
    if edge_on():
        _ensure_edge()


def stop():
    """The plug-in unloaded: the edge panel goes."""
    global _SKIN
    current = edge()
    if current is not None:
        if _SKIN is not None:
            _SKIN.destroy()
            _SKIN = None
        current.destroy()
        _hubedge().state()["edge"] = None


def set_edge(on):
    """⋮ -> Edge panel. Deferred: the press comes from inside the hub it
    rebuilds. Refused (False) without the skin."""
    if on and (classic_asked() or not _qt_available()):
        say("The edge panel needs the new look (⋮ -> Classic look is on)")
        return False
    cmds.optionVar(intValue=(EDGE_VAR, int(bool(on))))
    cmds.evalDeferred(lambda: _switch_edge(bool(on)), lowestPriority=True)
    return bool(on)


def _switch_edge(on):
    global _SKIN
    if on:
        if _SKIN is not None:
            _SKIN.destroy()
            _SKIN = None
        if cmds.workspaceControl(CONTROL, exists=True):
            cmds.deleteUI(CONTROL)
        _ensure_edge().reveal(hold=True)
        return
    stop()
    show()


def _press_pin(on):
    current = edge()
    if current is not None:
        current.set_pinned(on)


def _told(key, text, viewport):
    """A card's status reached the message line. While the edge panel is
    hidden it is also Maya's viewport message, unless its writer showed one
    itself (`viewport`)."""
    current = edge()
    if not text or viewport or current is None or current.shown:
        return None
    try:
        cmds.inViewMessage(assistMessage=text.splitlines()[0],
                           position="topCenter", fade=True,
                           fadeStayTime=3000)
    except Exception:                                        # noqa: BLE001
        pass
    return text
```

`_callbacks()` gains `"pin": _press_pin`, `"edge": set_edge`. `_dress_header(skin)` calls `skin.paint_edge(edge_on())`.

`build()` (the uiScript) first:

```python
    if edge_on():
        #  a docked control Maya restored from an older workspace: the hub
        #  lives at the edge now - the control goes, the edge waits
        cmds.evalDeferred(_drop_dock_for_edge, lowestPriority=True)
        _BUILT_HERE = True
        return CONTROL
```

with `_drop_dock_for_edge()` = delete `CONTROL` if it exists, then `_ensure_edge()`.

`rebuild()`: in edge mode `stop()` then `_ensure_edge()` (the Edge object is recreated; the width survives in its optionVar), else as now.

`is_open()`: `bool(cmds.workspaceControl(CONTROL, exists=True)) or edge() is not None`.

`show(key)`: first lines:

```python
    _close_legacy_windows()
    if edge_on():
        _ensure_edge().reveal(hold=True)
        if key:
            expand(key)
        return CONTROL
```

`install.py`:
- `_PAYLOAD` gains `"maya_edgerules.py",  # the edge panel's rules (2026-10-08)` and `"maya_hubedge.py",  # the edge panel's windows`.
- add

```python
def _edge_standing():
    """The hub's edge panel stands (2026-10-08): its host window, by name."""
    try:
        from PySide6 import QtWidgets
    except ImportError:
        return False
    app = QtWidgets.QApplication.instance()
    if app is None:
        return False
    return any(w.objectName() == "skeldarAnimHubEdge"
               for w in app.topLevelWidgets())
```

and where `install` computes `hub_open` (L760): `hub_open = bool(cmds.workspaceControl(HUB_CONTROL, exists=True)) or _edge_standing()`. `rebuild_open_hub` needs nothing more: the fresh `maya_hub.rebuild()` handles edge mode.

- [ ] **Step 4: Run `tests.test_hub tests.test_install`, then the suite -> PASS.**
- [ ] **Step 5: Commit** (`feat(hub): the edge panel mode - ⋮ switch, build, show and hold, the viewport message while hidden`).

---

### Task 13: The startup plug-in, loaded and autoloaded by the installer

**Files:**
- Create: `SkeldarAnim/plug-ins/skeldarAnimStartup.py`
- Modify: `SkeldarAnim/install.py` (payload row `"plug-ins"`, `register_startup(dest)`, called from `install`)
- Test: `tests/test_startup_plugin.py`, `tests/test_install.py`
- Create: `docs/superpowers/plans/probe_plugin_autoload.py` (the measurement)

- [ ] **Step 1: Measure first** - in a DISPOSABLE GUI Maya (scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, its own port; never the animator's 7001), with a throwaway plug-in file `C:/tmp_sk/probe/skProbe.py` (`initializePlugin` writes a marker file):
  1. `cmds.loadPlugin(r"C:/tmp_sk/probe/skProbe.py")`, `cmds.pluginInfo("skProbe", edit=True, autoload=True)`, `cmds.pluginInfo(savePluginPrefs=True)`; read `<MAYA_APP_DIR>/2027/prefs/pluginPrefs.mel` and record the exact line;
  2. restart that Maya; does the marker appear (loaded by path)?
  3. `mel.eval("getenv MAYA_PLUG_IN_PATH")`: is `<MAYA_APP_DIR>/2027/plug-ins` on it?
  4. inside `initializePlugin`, is `__file__` defined (write it into the marker)?
  Record the answers in the docstring of `register_startup`. If (2) fails, `register_startup` copies the file to `<userAppDir>/<version>/plug-ins/` (create the folder) and loads it by NAME; if (4) fails, the plug-in reads its own path with `cmds.pluginInfo("skeldarAnimStartup", query=True, path=True)`.

- [ ] **Step 2: Failing tests** - `tests/test_startup_plugin.py`:

```python
"""The startup plug-in: the edge panel waiting from Maya's start."""

import importlib.util
import os
import sys
import types
import unittest

PATH = os.path.join(os.path.dirname(__file__), "..", "SkeldarAnim",
                    "plug-ins", "skeldarAnimStartup.py")


def _load(batch=False):
    calls = []
    fake_cmds = types.SimpleNamespace(about=lambda **k: batch)
    fake_utils = types.SimpleNamespace(
        executeDeferred=lambda fn: calls.append(fn))
    fake_om = types.SimpleNamespace(MFnPlugin=lambda *a, **k: None)
    saved = {k: sys.modules.get(k) for k in
             ("maya", "maya.cmds", "maya.utils", "maya.api",
              "maya.api.OpenMaya")}
    maya = types.ModuleType("maya")
    maya.cmds, maya.utils = fake_cmds, fake_utils
    api = types.ModuleType("maya.api")
    api.OpenMaya = fake_om
    sys.modules.update({"maya": maya, "maya.cmds": fake_cmds,
                        "maya.utils": fake_utils, "maya.api": api,
                        "maya.api.OpenMaya": fake_om})
    try:
        spec = importlib.util.spec_from_file_location("skStartupTest", PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.initializePlugin(object())
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return module, calls


class StartupPlugin(unittest.TestCase):

    def test_it_defers_the_start_in_a_gui_maya(self):
        module, calls = _load(batch=False)
        self.assertEqual(len(calls), 1)
        self.assertTrue(hasattr(module, "maya_useNewAPI"))

    def test_nothing_in_batch(self):
        _module, calls = _load(batch=True)
        self.assertEqual(calls, [])

    def test_its_plugin_folder_is_the_installed_skeldaranim(self):
        module, _calls = _load()
        self.assertEqual(os.path.basename(module.PLUGIN_DIR), "SkeldarAnim")
```

(If the plug-in guards real Maya imports in a way the fakes do not satisfy, wrap the guarded `import maya.cmds` inside `initializePlugin` so the module imports with stdlib alone.)

`tests/test_install.py`: `register_startup(dest)` loads `<dest>/plug-ins/skeldarAnimStartup.py` and sets autoload (fake cmds records `loadPlugin` and `pluginInfo(edit=True, autoload=True)` and `pluginInfo(savePluginPrefs=True)`); a failure of either is caught and answered as a note, never raised; `"plug-ins"` is in the payload.

- [ ] **Step 3: Implement** the plug-in:

```python
"""skeldarAnimStartup - SkeldarAnim at Maya's start (2026-10-08).

The animator asked the hub's edge panel to wait at the screen edge from the
first second (the brainstorm's «Панель сразу ждёт у края»). Maya runs this
plug-in at startup because the installer loads it and sets it to autoload;
in a GUI Maya it defers `maya_hub.start()`, which builds the edge panel
hidden when ⋮ -> Edge panel is on and does nothing otherwise. It registers
no node and no command. Unloading it removes the edge panel.

Turn it off in Window > Settings/Preferences > Plug-in Manager (untick
Auto load), or ⋮ -> Edge panel off (the plug-in then does nothing).
"""

import os
import sys


def maya_useNewAPI():
    """Maya Python API 2.0."""


#  The installed SkeldarAnim folder: this file sits in its plug-ins/
PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _start():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)
    try:
        import maya_hub
        maya_hub.start()
    except Exception:                                        # noqa: BLE001
        import traceback
        print("SkeldarAnim startup: the hub did not start")
        print(traceback.format_exc())


def initializePlugin(plugin):                                # noqa: N802
    import maya.api.OpenMaya as om
    import maya.cmds as cmds
    om.MFnPlugin(plugin, "SkeldarAnim", "1.0")
    if cmds.about(batch=True):
        return
    import maya.utils
    maya.utils.executeDeferred(_start)


def uninitializePlugin(plugin):                              # noqa: N802
    import maya.api.OpenMaya as om
    om.MFnPlugin(plugin)
    hub = sys.modules.get("maya_hub")
    if hub is not None:
        try:
            hub.stop()
        except Exception:                                    # noqa: BLE001
            pass
```

(Apply what Step 1 measured: `__file__` fallback, copy-to-user-plug-ins.)

`install.py`: `_PAYLOAD` gains `"plug-ins",  # the startup plug-in: the edge panel from Maya's start (2026-10-08)`; add

```python
STARTUP_PLUGIN = "skeldarAnimStartup"


def register_startup(dest):
    """Load the startup plug-in from the installed folder and set it to
    autoload (2026-10-08). Answers "" or a note; never raises: a hub
    without its edge panel at startup is no reason to fail an install."""
    import maya.cmds as cmds
    path = os.path.join(dest, "plug-ins", STARTUP_PLUGIN + ".py").replace(
        "\\", "/")
    try:
        if cmds.pluginInfo(STARTUP_PLUGIN, query=True, loaded=True):
            cmds.unloadPlugin(STARTUP_PLUGIN, force=True)
        cmds.loadPlugin(path, quiet=True)
        cmds.pluginInfo(STARTUP_PLUGIN, edit=True, autoload=True)
        cmds.pluginInfo(savePluginPrefs=True)
        return ""
    except Exception as error:                               # noqa: BLE001
        return "startup plug-in not registered: {0}".format(error)
```

and call it in `install(...)` after the payload copy and the shelf (only outside batch: `if not cmds.about(batch=True)`), appending a non-empty note to the install's message. Unloading the plug-in runs `uninitializePlugin` -> `maya_hub.stop()`: the reload right after re-runs `start()`.

- [ ] **Step 4: Run `tests.test_startup_plugin tests.test_install`, then the suite -> PASS.** A test pinning "every maya_*.py beside install.py ships" stays green (Task 12 added the two modules).
- [ ] **Step 5: Commit** (`feat(hub): the startup plug-in - the edge panel waiting from Maya's start`).

---

### Task 14: Live proof of the compact hub

**Files:**
- Create: `docs/superpowers/plans/verify_hub_compact.py`

A disposable GUI Maya: launch `C:\Program Files\Autodesk\Maya2027\bin\maya.exe` with `MAYA_APP_DIR` a scratch folder, `MAYA_NO_HOME=1`, and a scratch `userSetup.py` in `<MAYA_APP_DIR>/2027/scripts/` opening a commandPort on a free port (7060+; check `Get-NetTCPConnection -State Listen` first; 7001 is the animator's, 7051 another session's). Install the worktree's plugin there (`install.install(quiet=True)` from the worktree's `SkeldarAnim/install.py`, the `install` module purged first). Use a runner with a `.ran` marker and an `if` guard (CLAUDE.md bridge notes 5, 7, 8). Float the hub and size it until its scroll viewport is 510 physical (trap 150). Phases, each its own send:

1. **cards**: open every card (through `maya_hub.expand(key)` with `Interface animations` off), then in the next send: `content.minimumSizeHint().width() <= viewport.width()`; for every card, no child widget's `geometry().right()` past the card's width; every row's height <= 30 physical * 1.5 except the lists and tiles.
2. **heights**: each card's height, compared with the same measurement made on a `git archive` snapshot of `ed00397` installed into a second scratch folder (run the phase once per build, write both to JSON, gate: every card shorter or equal, the whole content at least 35 % shorter).
3. **relay**: for each section, call its status writer with a marker text; gate: the hub's message line shows it, its icon is that card's, the card's height did not change.
4. **notes**: Retarget's, Graph Overlay's, Pose Library's, Studio's, Colour's header tooltips hold their hint texts; no visible note label.
5. **grips**: both lists show 10 rows (`QListWidget.height()` against `sizeHintForRow(0)`); a synthetic drag through `ListGrip.press/drag/release` by +3 rows -> 13, the optionVar 13; `maya_hub.rebuild()` -> 13 again; a drag to -9999 -> 5.
6. **picture**: DWM `PrintWindow` copy of the hub window to `docs/superpowers/plans/hub_compact.png` (never `.grab()`, trap 134).

- [ ] Write the script, run each phase, fix code (not gates) until all pass, record the numbers in the commit message.
- [ ] Commit (`test(hub): verify_hub_compact - every card fits the dock, statuses on one line, the grips`).

---

### Task 15: Live proof of the edge panel and the startup plug-in

**Files:**
- Create: `docs/superpowers/plans/verify_hub_edge.py`

Same disposable Maya harness; the Edge's `cursor`/`buttons` seams replaced by the script (never move the real cursor). Gates:

1. `maya_hub.set_edge(True)` (+ deferred) -> no `skeldarAnimHub` workspaceControl, the host and the sensor stand, the sensor's rect = the work area's left 2 px, full height.
2. `sensor_entered` + `dwell_done` with the fake cursor on the edge -> shown; the slot's x sampled through the slide monotonic onto 0 (animations ON); the host's rect = `panel_rect`.
3. A dwell cut short -> hidden.
4. Fake cursor away, `host_left` -> hidden after `HIDE_MS` (wait with `processEvents` loops), the sensor back.
5. Postponements: a fake button held; a dropdown's popup open (`QComboBox.showPopup()` on the Studio look menu's Qt widget, found by name); a field focused (the bridge's search); the pin -> each keeps it shown; each removed -> hides.
6. `maya_hub.show("retarget")` from the hidden state -> shown, the Retarget card open, held until a fake enter + leave.
7. The width grip: `set_width(500)` -> optionVar 500, host 500 * scale; a rebuild keeps 500.
8. Interface animations off -> reveal and conceal instant.
9. A status while hidden -> an `inViewMessage` call recorded (patch `cmds.inViewMessage` to a recorder for the gate).
10. `set_edge(False)` -> the edge gone, the dock open, `cmds.text("skeldarRetargetStatus", exists=True)`.
11. **Plug-in**: `install.install(quiet=True)` -> `cmds.pluginInfo("skeldarAnimStartup", q=True, loaded=True, autoload=True)`; with edge ON, kill and relaunch that Maya with the same `MAYA_APP_DIR` -> after startup the host stands hidden and the sensor shows, with nobody having pressed anything.
12. Picture: the panel shown over the viewport (PrintWindow of Maya's main window) -> `docs/superpowers/plans/hub_edge.png`.

- [ ] Write, run, fix, commit (`test(hub): verify_hub_edge - reveal, hide rules, hold, width, the startup plug-in`).

---

### Task 16: Records, merge, hand-off

**Files:**
- Modify: `CLAUDE.md` (a new section "The hub, compact (B) and as an edge panel (2026-10-08)" in the file's style: the ask in Russian, what changed, the measured numbers from Tasks 14-15, any new trap with its number continuing the list)
- Modify: `docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md` (an addendum for anything the build changed: the shadow -> a 1 px line, the plug-in measurement)

- [ ] Run the whole suite in the worktree; record the count.
- [ ] `git fetch` nothing (local branch); rebase the worktree branch onto the current `feature/overrig-picker` (`git rebase feature/overrig-picker`) - the Pose Library session merges its work there; resolve conflicts keeping BOTH sides (their `NOTE` text, our heights).
- [ ] Re-run the suite after the rebase.
- [ ] In the main checkout: `git merge --ff-only feature/hub-compact` (or a merge commit if fast-forward is impossible). Do NOT push, do NOT install into the animator's Maya (port 7001): ask the user first, and ask the other sessions (`ListAgents` / `SendMessage`) whether one is installing or running there (CLAUDE.md trap 148).
- [ ] Remove the worktree (`git worktree remove`).

---

## Self-review notes (for the executor)

- If a builder test file was not listed in a task but fails because a row moved, it belongs to that task: update the expectation to the new arrangement, never weaken a gate to "anything".
- `hubstyle.skinning()` is True only while `maya_hub._build_skin` runs the builders; a builder's `pick` is decided at build time. Tests that build "the skin" must `style.set_skinning(True)` around the build and reset it in `finally`.
- The relay must never import Qt or cmds into `maya_hubstyle`.
- A writer that `tell`s must still write its own control first: `is_open()` and the classic hub depend on it.

# Hub Rail Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The skinned hub shows a vertical rail of section icons on the left and ONE card on the right (layout C), with a ⋮ switch back to today's accordion.

**Architecture:** `maya_hubqt.Skin` takes `layout="rail"|"accordion"`. In the rail it builds a vertical rail (mark, jumps by group, hotkeys/pin/⋮ at the bottom) instead of the header row, keeps the same scroll column of cards, and shows one card frame at a time (`show_card`). Cards built for the rail cannot collapse. `maya_hub` picks the layout from an optionVar, remembers the shown card, routes `focus`/`expand` to `show_card`, and rebuilds on a layout switch. Every card is still built (control names, jobs, `is_open()` unchanged).

**Tech Stack:** Maya 2027, PySide6 6.8.3 (offscreen in tests), `maya.cmds`, stdlib unittest under mayapy.

## Global Constraints

- optionVar `skeldarAnimHub_layout`: "rail" (default) or "accordion".
- optionVar `skeldarAnimHub_current`: the shown section's key; the first card section when unset or stale.
- `RAIL_SWITCH_MS` 160, `RAIL_SLIDE` 12 logical px; instant with ⋮ → Interface animations off.
- Ctrl+click or a middle click on a rail icon opens the section as a popup at the cursor (`maya_hubpop.open_at(key, (x, y))`); the shown card does not change.
- Right button on a rail icon: menu «Show here» / «Open as popup».
- In the rail the collapse memory `skeldarAnimHub_collapsed_*` is neither read nor written.
- Classic look is untouched; the edge panel builds the same skin and follows the layout.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` with `QT_QPA_PLATFORM=offscreen`.

---

### Task 1: Rail-capable Skin and Card (maya_hubqt)

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (Card.__init__/toggle, Skin.__init__, Skin._build_header, Skin.add_jump, Skin.add_card, new Skin.show_card / paint_layout / _rail_menu)
- Modify: `SkeldarAnim/maya_hubmotion.py` (RAIL_SWITCH_MS, RAIL_SLIDE)
- Test: `tests/test_hubqt.py` (new class `Rail`)

**Interfaces:**
- Produces: `Skin(parent, scale=1.0, callbacks=None, layout="accordion")`, `Skin.layout`, `Skin.rail` (QWidget or None), `Skin.add_jump(key, label, icon_name, colour, group=None)`, `Skin.add_card(..., collapsible=True)`, `Skin.show_card(key, animate=False) -> card or None`, `Skin.shown` (key or None), `Skin.paint_layout(choice)`; callbacks it calls: `("jump", key)`, `("popup", key)`, `("layout", choice)`.
- `Card(..., collapsible=True)`: with `collapsible=False` the chevron is hidden, `toggle()` does nothing, `set_collapsed(True)` is ignored.

- [ ] **Step 1: Write the failing tests** — in `tests/test_hubqt.py` a `Rail(unittest.TestCase)` building `hubqt.Skin(layout, scale=1.0, callbacks=..., layout="rail")` with `"popup"` and `"layout"` callbacks recording calls; cards added with `collapsible=False`. Tests:
  - the root's layout is horizontal, `skin.rail` is its first widget, the header row is absent (`skin.header is None`), the hotkeys / pin / ⋮ buttons are children of the rail;
  - `add_jump(..., group=g)` puts a separator (`objectName` `skeldarHubRailGap_<group>`) before the first jump of each new group, none before the first group;
  - `show_card("b")` shows only card b's frame (`isVisibleTo(root)`), `skin.shown == "b"`, the jump for b has property `skCurrent` True and the others False;
  - a jump's click calls `("jump", key)`; with Ctrl held (`QApplication.keyboardModifiers` patched through `hubqt._modifiers`) it calls `("popup", key)` and the shown card stays;
  - a middle-button release on a jump calls `("popup", key)`;
  - `Card.toggle()` on a rail card changes nothing; its chevron is hidden;
  - ⋮ → Layout has rows "Rail" / "Accordion"; `paint_layout("rail")` checks Rail and calls nothing; triggering Accordion calls `("layout", "accordion")`;
  - `show_card(key, animate=True)` with `skin.animations` True runs an opacity animation that ends with no graphics effect left on the frame; with animations False the frame has no effect at once.
- [ ] **Step 2: Run** `tests.test_hubqt.Rail` → FAIL (unexpected keyword `layout`).
- [ ] **Step 3: Implement** in `maya_hubqt.py`:
  - `_modifiers()` seam returning `QApplication.keyboardModifiers()`.
  - `Skin.__init__(..., layout="accordion")`: `self.layout = "rail" if layout == "rail" else "accordion"`; for the rail the root's layout is a `QHBoxLayout` holding `self.rail = self._build_rail()` and a right `QWidget` whose `QVBoxLayout` holds the message line and the scroll; `self.header = None`. The accordion builds as today.
  - `_build_rail()`: a `QWidget` named `skeldarHubRail` (role `rail`), a `QVBoxLayout`: the SA mark, `self.jump_row` (a `QVBoxLayout`), a stretch, `self.hotkeys`, `self.pin`, `self.menu_button` (the same buttons `_build_header` makes - factor their creation into `_build_head_buttons()` used by both).
  - `add_jump(..., group=None)`: in the rail, fixed square `s(26)`, and when `group` differs from the last jump's group (and a jump exists) a gap widget `skeldarHubRailGap_<group>` (height `s(9)`, a 1 px `line`-coloured hairline across its middle, role `railgap`) first. Install `_RailJumpFilter` on rail jumps: a MouseButtonRelease with the middle button → `_call("popup", key)`; `customContextMenuRequested` → a menu «Show here» (`_call("jump", key)`) / «Open as popup» (`_call("popup", key)`). The jump's `clicked` goes through `self._jump(key)`: Ctrl held → popup, else `_call("jump", key)`.
  - `add_card(..., collapsible=True)` passes it to `Card`; in the rail the frame starts hidden.
  - `show_card(key, animate=False)`: unknown key → None; every other frame hidden, this one shown, `self.shown = key`, each rail jump's `skCurrent` property and its stylesheet (`background: card_active; border-left: 2px solid <its group colour>`), scroll bar to 0; when `animate and self.animations and self.root.isVisible()` a `QGraphicsOpacityEffect` on the frame (held on the card, trap 201) and a `QVariantAnimation` of `RAIL_SWITCH_MS` moving opacity 0→1 (ease) and the column's left margin `RAIL_SLIDE`→0, the effect removed (`setGraphicsEffect(None)`) when it ends.
  - The ⋮ menu gains `Layout ▸ Rail / Accordion` (exclusive, like Edge panel), `paint_layout(choice)`.
  - `Card(..., collapsible=True)`: rail cards hide the chevron, `toggle` returns at once, `set_collapsed` forces False.
  - `maya_hubmotion`: `RAIL_SWITCH_MS = 160`, `RAIL_SLIDE = 12`.
  - `maya_hubstyle.ROLES` gains `rail`, `railgap`; the stylesheet styles `QWidget[skRole=rail]` (background `strip`, radius) and the gap.
- [ ] **Step 4: Run** `tests.test_hubqt` (whole module: the accordion must not change) → PASS.
- [ ] **Step 5: Commit** `feat(hub): the skin can stand as a rail and one card`.

### Task 2: The hub chooses, remembers and switches (maya_hub)

**Files:**
- Modify: `SkeldarAnim/maya_hub.py` (`_build_skin`, `focus`, `expand`, `_callbacks`, new `layout`, `set_layout`, `current`, `remember_current`, `_press_popup`)
- Test: `tests/test_hub.py` (FakeSkin gains `layout`, `show_card`, `paint_layout`; new class `RailLayout`)

**Interfaces:**
- Consumes: Task 1's `Skin(..., layout=)`, `add_jump(..., group=)`, `add_card(..., collapsible=)`, `show_card`, `paint_layout`.
- Produces: `maya_hub.LAYOUT_VAR = "skeldarAnimHub_layout"`, `CURRENT_VAR = "skeldarAnimHub_current"`, `layout() -> "rail"|"accordion"`, `set_layout(choice)`, `current() -> key`, `remember_current(key)`.

- [ ] **Step 1: Write the failing tests** (FakeCmds already in test_hub): `layout()` is "rail" with no optionVar, "accordion" when set; `current()` falls back to the first card section for unset / stale; a built rail skin gets `layout="rail"`, every card `collapsible=False`, never asks `collapsed()`, and ends showing `current()`; `focus("tools")` / `expand("tools")` in the rail call `show_card("tools", animate=True)`, remember it, set it active, close nothing and remember no collapse; `set_layout("accordion")` writes the optionVar and defers a rebuild; the callbacks map has `"popup"` and `"layout"`; the accordion path is unchanged (existing tests).
- [ ] **Step 2: Run** `tests.test_hub` → the new tests FAIL.
- [ ] **Step 3: Implement**: `_build_skin` passes `layout=layout()`, `group=sec.group` to `add_jump`, `collapsible=(rail is False)` and `collapsed=False` in the rail; after the cards `skin.show_card(current())` and `skin.paint_layout(layout())`. `focus`/`expand`: when `is_skinned()` and `_SKIN.layout == "rail"`: `card = _SKIN.show_card(key, animate=True)`, `_SKIN.set_active(key)`, `remember_current(key)`, return the card. `_press_popup(key)`: `maya_hubpop.open_at(key, QCursor.pos())`, falling back to `_press_popout(key)`. `set_layout(choice)`: write, `cmds.evalDeferred(rebuild, lowestPriority=True)`.
- [ ] **Step 4: Run** `tests.test_hub tests.test_hubqt tests.test_hubedge tests.test_hubpop` → PASS.
- [ ] **Step 5: Commit** `feat(hub): the rail layout by default, ⋮ switches back to the accordion`.

### Task 3: Widths, the picture, the record

**Files:**
- Create: `docs/superpowers/plans/render_hub_rail.py`
- Modify: `CLAUDE.md`, the spec if the build changed anything

- [ ] **Step 1:** `render_hub_rail.py`: offscreen at scale 1.5, a Skin in each layout with a few stub cards (labels, buttons, a list), the rail's real jumps for every `maya_hub.card_sections()` entry, saved as `hub_rail.png`; prints each card's `content.minimumSizeHint().width()` against the column at the dock's 510 physical px viewport. Look at the picture.
- [ ] **Step 2:** Run the whole suite.
- [ ] **Step 3:** CLAUDE.md: a section for the rail layout (what moved, the switch, what is not proven live); commit `docs(hub): the rail layout`.

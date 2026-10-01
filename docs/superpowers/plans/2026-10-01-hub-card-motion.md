# The Hub's Card Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The skinned hub's cards slide open and shut (the chevron turning with them), a jump glides the scroll to its card, ⋮ → Interface animations switches it all.

**Architecture:** `maya_hubmotion` (stdlib) holds the numbers (ease, durations, the switch on an optionVar). `maya_hubqt.Card` slides by capping the body's `maximumHeight` per tick with the body's own layout DISABLED and laid out once at full height (children clipped, never squeezed); `Skin.scroll_to(animate=True)` glides toward the card's LIVE `frame.y()`. `maya_hub` passes `animate=True` from the animator's moves and wires the menu row.

**Tech Stack:** Python 3 stdlib, PySide6 6.8.3 (QVariantAnimation, QPainter), Maya `cmds.optionVar`; tests `mayapy -m unittest`, Qt offscreen.

Spec: `docs/superpowers/specs/2026-10-01-hub-card-motion-design.md`.

## Global Constraints

- `maya_hubmotion` imports nothing of maya or Qt at import time (a subprocess test pins it).
- optionVar `skeldarAnimHub_animations`, default ON.
- Durations: `clamp(140 + 0.12 · logical px, 160, 260)` ms; the glide `SCROLL_MS = 300` (longer than any slide, so its last stretch aims at a settled card).
- Ease: cubic ease-out `1 - (1 - t)^3` on a linear 0 → 1 animation value.
- `set_collapsed(c)` without `animate` is instant, as today; only the animator's moves pass `animate=True`.
- The classic hub is untouched.
- Every new `maya_*.py` beside install.py is a payload row.

---

### Task 1: `maya_hubmotion` — the numbers and the switch

**Files:**
- Create: `SkeldarAnim/maya_hubmotion.py`
- Modify: `SkeldarAnim/install.py` (payload row after `maya_hubsound.py`)
- Test: `tests/test_hubmotion.py`

**Interfaces:**
- Produces: `OPTIONVAR`, `BASE_MS`, `PER_PX_MS`, `MIN_MS`, `MAX_MS`, `SCROLL_MS`, `CHEVRON_OPEN` (90.0); `enabled() -> bool`; `set_enabled(on) -> bool`; `ease(t) -> float`; `duration(distance, scale=1.0) -> int`; `lerp(start, end, k) -> float`; seam `_cmds()`.

- [ ] **Step 1: tests** — `ease(0) == 0`, `ease(1) == 1`, `ease(0.5) == 0.875`, clamped outside 0..1, monotonic; `duration(0) == 160`, `duration(150 * 1.5, 1.5) == 160` (150 logical → 158 → clamped), `duration(420, 1.5) == 174`, `duration(810, 1.5) == 205`, `duration(-420, 1.5) == 174`, `duration(10000) == 260`; `lerp(10, 20, 0.25) == 12.5`; `enabled()` True with no optionVar, False after `set_enabled(False)`, True when `cmds` raises; `set_enabled` writes `intValue`; stdlib-only import.
- [ ] **Step 2:** `mayapy -m unittest tests.test_hubmotion -v` — FAIL (no module).
- [ ] **Step 3:** write the module:

```python
OPTIONVAR = "skeldarAnimHub_animations"
BASE_MS, PER_PX_MS, MIN_MS, MAX_MS = 140, 0.12, 160, 260
SCROLL_MS = 300
CHEVRON_OPEN = 90.0

def _cmds():
    import maya.cmds as cmds
    return cmds

def enabled():
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return True
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:
        return True

def set_enabled(on):
    on = bool(on)
    try:
        _cmds().optionVar(intValue=(OPTIONVAR, int(on)))
    except Exception:
        pass
    return on

def ease(t):
    t = min(1.0, max(0.0, float(t)))
    return 1.0 - (1.0 - t) ** 3

def duration(distance, scale=1.0):
    logical = abs(float(distance)) / float(scale or 1.0)
    return int(round(min(MAX_MS, max(MIN_MS, BASE_MS + PER_PX_MS * logical))))

def lerp(start, end, k):
    return start + (end - start) * k
```

- [ ] **Step 4:** run the tests — PASS; add the payload row `"maya_hubmotion.py",       # how its cards move (2026-10-01)`; `tests.test_install` PASS.
- [ ] **Step 5:** commit.

### Task 2: the card slides

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`import maya_hubmotion as hubmotion`; `rotated(pix, angle)`; `Card.__init__` gains `motion=None`, the column spacing moves into the body's top margin; `Card.set_collapsed(collapsed, animate=False)`, `toggle` animates, `natural_height`, `sliding`, `_slide`, `_tick`, `_finished`, `_settle`, `_stop`, `_lay_out_full`, `_paint_chevron`; `Skin.animations = True`, `add_card` passes `motion=lambda: self.animations`)
- Test: `tests/test_hubqt.py` (a `CardMotion` class)

**Interfaces:**
- Consumes: `hubmotion.ease`, `duration`, `lerp`, `CHEVRON_OPEN`.
- Produces: `Card.set_collapsed(collapsed, animate=False)`; `Card.sliding() -> bool`; `Card.natural_height(width=None) -> int`; `Card._anim` (the QVariantAnimation, object name `skeldarHubCardSlide_<key>`, value 0 → 1); `maya_hubqt.rotated(pixmap, angle) -> QPixmap`; `Skin.animations` (bool).

Core of the slide (the body's layout disabled for the length of it):

```python
def _slide(self, opening):
    start = self._shown if self.sliding() else (
        self.body.height() if self.body.isVisible() else 0)
    self._stop()
    if opening and not self.body.isVisible():
        self.body.setMaximumHeight(0)
        self.body.setVisible(True)
    self.body_layout.setEnabled(False)
    self._laid = None
    self._opening, self._from_height, self._from_angle = opening, start, self._angle
    self._shown = start
    target = self._lay_out_full() if opening else 0
    anim = QVariantAnimation(self.frame); start 0.0, end 1.0,
    duration hubmotion.duration(target - start, self.scale); valueChanged -> _tick;
    finished -> _finished; start

def _tick(self, value):
    k = hubmotion.ease(value)
    target = self._lay_out_full() if self._opening else 0
    self._shown = int(round(hubmotion.lerp(self._from_height, target, k)))
    self.body.setMaximumHeight(self._shown)
    self._angle = hubmotion.lerp(self._from_angle, CHEVRON_OPEN if self._opening else 0.0, k)
    self._paint_chevron(self._angle)

def _settle(self):
    self.body.setVisible(not self._collapsed)
    self.body.setMaximumHeight(QWIDGETSIZE_MAX)
    self.body_layout.setEnabled(True)
    self.body_layout.invalidate()
    self._angle = 0.0 if self._collapsed else CHEVRON_OPEN
    self._paint_chevron(None)
```

- [ ] **Step 1: tests** — on a shown skin (the host shown, `processEvents`): `toggle()` on an open card starts a slide (`sliding()`, the animation's object name), `collapsed()` True at once; driven to its end (`card._anim.setCurrentTime(card._anim.duration())`) the body is hidden, its maximum back to 16777215, the layout enabled; opening: visible at once with maximum 0, a fixed-height child keeps its height at mid-way (clipped), at the end the maximum is restored and the layout enabled; reversal mid-way ends open; animations off / `animate=False` / a card never shown → no animation, instant; `set_collapsed(c)` still does not call back; the chevron at mid-way is a rotated pixmap of the same size; the gap: header bottom to body top equals the old spacing (`px(6)`) on an open card; `rotated` keeps size.
- [ ] **Step 2:** run — FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `tests.test_hubqt` and `tests.test_hub` PASS.
- [ ] **Step 5:** commit.

### Task 3: the glide, the menu row, the hub's wiring

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`Skin.scroll_to(key, animate=False)`, `_glide_tick`, `_glide_done`, `_stop_glide`, the bar's `actionTriggered`/`sliderPressed` stopping it; menu row "Interface animations" key "animations" checkable; `Skin.animations_action`; `Skin.paint_animations(on)` sets the flag and the check)
- Modify: `SkeldarAnim/maya_hub.py` (`_callbacks()["animations"] = set_animations`; `set_animations(on)`; `_dress_animations(skin)` from `_dress_header`; `focus` / `expand` pass `animate=True`; `scroll_to(key, animate=False)` forwards it)
- Test: `tests/test_hubqt.py`, `tests/test_hub.py` (FakeCard/FakeSkin take `animate`, `paint_animations`)

**Interfaces:**
- Produces: `Skin.scroll_to(key, animate=False) -> int|None` (the card's offset now); `Skin._glide` (QVariantAnimation, object name `skeldarHubGlide`); `Skin.animations_action`; `Skin.paint_animations(on)`; `maya_hub.set_animations(on) -> bool`; `maya_hub._dress_animations(skin)`; `maya_hub.scroll_to(key, animate=False)`.

- [ ] **Step 1: tests** — the menu reads Check update, Hotkey Editor..., Interface sounds, Interface animations, Classic look, the new row checkable calling back `("animations", checked)`, `paint_animations` checks it without a call and sets `skin.animations`; `scroll_to(key, animate=True)` on a shown skin with a tall column starts the glide and, driven to its end, leaves the bar on the card's offset (clamped to the maximum); `actionTriggered` stops it; `animate=False` / animations off → no glide, the bar set at once; `maya_hub`: `_callbacks()` has `animations`; `set_animations(False)` writes the optionVar and paints the skin; `_dress_header` paints it from the optionVar; `focus("studio")` passed `animate=True` to every card it changed; `expand` likewise; the deferred scroll asks `animate=True`.
- [ ] **Step 2:** run — FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** the whole suite — PASS.
- [ ] **Step 5:** commit.

### Task 4: live

**Files:**
- Create: `docs/superpowers/plans/verify_hub_motion.py`
- Modify: `CLAUDE.md` (a section at the end)

- [ ] **Step 1:** in a disposable Maya (port 7016, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`) on the repo's hub, phases:
  0. every card closed instantly, the hub wide enough;
  1. each card opened and closed through real time (`processEvents` + 5 ms sleeps in the send), per tick: the body's height, one child's height; gates — monotonic, the child's height constant (clipped), the end on the settled height (0 px), hidden at the end of a close, the layout enabled, max ms per tick;
  2. reversal mid-way;
  3. a jump (`maya_hub.focus("studio")` after `uebridge`, `characters`, `weapons` were opened): the others shut, studio open, the bar monotonic and on `studio.frame.y()` (or the maximum) at the end;
  4. Interface animations off: `focus` instant (no slide, no glide), back on;
  5. photographs mid-slide (`root.grab()`, three frames).
- [ ] **Step 2:** the installed copy refreshed in the animator's Maya from a `git archive` of the commit (the open hub rebuilt by the installer).
- [ ] **Step 3:** CLAUDE.md section; commit.

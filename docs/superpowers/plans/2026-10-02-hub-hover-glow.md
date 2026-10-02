# Hub hover glow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every clickable control of the skinned hub glows softly in its own ink's colour while the mouse is over it (the orange primary button: a warm inner rim), fading in and out.

**Architecture:** the arithmetic in a numpy module (`maya_hubglow`), the numbers as data (`maya_hubstyle.HOVER_GLOW`, `maya_hubmotion.GLOW_*`), a `QGraphicsEffect` drawing a cached glow image at `level` opacity, and a `Glower` the Skin's application-wide watcher drives - holding only its own effects, never a widget.

**Tech Stack:** Maya 2027, PySide6 6.8.3, numpy (Maya's), stdlib unittest under mayapy.

## Global Constraints

- Glow only in the skin; the classic hub unchanged.
- What glows: `sounding(widget, root)` minus `skRole == "swatch"` minus a widget carrying a graphics effect that is not ours.
- Ink: luminance above the face's by `lo` 25, fully at `lo + span` 95; blur `radius` 5 logical px; `gain` 2.2; `strength` 0.42; the ink's own colour; added (Plus); the letters' cores left alone (× (1 - ink)).
- Primary (skRole "primary"): rim `#fff1e2`, `rim_strength` 0.38, `rim_depth` 6 logical px.
- Fade in 110 ms ease-out, out 220 ms smoothstep, from where it stands; Interface animations off = instant.
- Never hold a widget wrapper across events (trap 135); hold every effect (PySide deletes a collected one).
- `maya_hubglow` imports no Qt and no Maya (subprocess test). Payload row in `install.py`.

---

### Task 1: the arithmetic and the numbers

**Files:**
- Create: `SkeldarAnim/maya_hubglow.py`, `tests/test_hubglow.py`
- Modify: `SkeldarAnim/maya_hubstyle.py` (HOVER_GLOW), `SkeldarAnim/maya_hubmotion.py` (GLOW_IN_MS, GLOW_OUT_MS, glow_ms), `tests/test_hubmotion.py`, `tests/test_hubstyle.py`

**Interfaces:**
- Produces: `maya_hubglow.blur(a, radius) -> ndarray`, `ink(bgra, inner=None) -> (mask HxW 0..1, bgr HxWx3 float)`, `bloom(bgra, scale=1.0, inner=None) -> uint8 HxWx4 premultiplied BGRA or None`, `rim(bgra, scale=1.0) -> uint8 HxWx4 or None`, `pad(scale) -> int` (physical px the bloom spills); `maya_hubstyle.HOVER_GLOW` dict; `maya_hubmotion.glow_ms(on, start, target) -> int`.

- [ ] Write `tests/test_hubglow.py` (synthetic BGRA arrays: a face with a bright "letter" bar, a border line, a transparent background; an orange face with dark letters; a rounded opaque shape) + purity test; the HOVER_GLOW / glow_ms tests.
- [ ] Run, see them fail (no module).
- [ ] Implement `maya_hubglow.py`, `HOVER_GLOW`, `GLOW_IN_MS = 110`, `GLOW_OUT_MS = 220`, `glow_ms`.
- [ ] Run `mayapy -m unittest tests.test_hubglow tests.test_hubmotion tests.test_hubstyle`, green.
- [ ] Commit.

### Task 2: the effect and the Glower in the skin

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`glowing`, `_glow_class`, `Glower`, `Skin.__init__/_hover_from/_left_from/destroy/paint_animations`), `tests/test_hubqt.py` (class `HoverGlow`)

**Interfaces:**
- Consumes: Task 1.
- Produces: `maya_hubqt.glowing(widget, root) -> bool`, `HoverGlow` effect class with `.level`, `.mode`, `.broken`; `Glower(root, scale, motion)` with `.enter(widget)`, `.leave(widget)`, `.lit` (the lit effect or None), `.tick(now=None)`, `.stop()`; `Skin.glow` (the Glower).

- [ ] Tests: the glowing set; enter -> our effect on the button, level rises to 1 by ticks with a fake clock; leave -> back to 0; one at a time; the header's child label keeps the header lit; entering the body darkens; switched off -> instant; a foreign effect is left alone; a swatch never; a deleted button mid-fade -> no error, dropped; destroy stops; the painted glow brightens pixels beside a hovered button's text and leaves far pixels alone; the cache (one numpy run for two draws of the same pixmap).
- [ ] Run, fail.
- [ ] Implement.
- [ ] Run the whole `tests.test_hubqt`, green; run the full suite.
- [ ] Commit.

### Task 3: payload, live proof, records

**Files:**
- Modify: `SkeldarAnim/install.py` (payload row), `CLAUDE.md`
- Create: `docs/superpowers/plans/verify_hub_glow.py`

- [ ] Payload row `"maya_hubglow.py"`; the payload test green.
- [ ] Verify in a disposable GUI Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME, own port): every kind of control lit on Enter and dark on Leave through Maya's real widgets, the on-screen glow measured, draw cost, a rebuild mid-fade, a picture of a hovered control.
- [ ] CLAUDE.md section; commit; install into the animator's Maya only after asking the peers.

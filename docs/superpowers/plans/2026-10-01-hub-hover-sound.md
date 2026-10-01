# The Hub's Hover Sound Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A soft "glass tick" plays when the mouse enters any button, dropdown or card header of the skinned SkeldarAnim hub; ⋮ → Interface sounds switches it.

**Architecture:** `maya_hubsound` (stdlib at import) synthesises the sound, ships it as `assets/sounds/hover.wav` and plays it (QSoundEffect pool, else winsound), throttled, players on `sys`. `maya_hubqt.Skin` already filters every Enter in the application; it gains `sounding(widget, root)` and calls back `"hover"`; the menu gains a checkable row calling back `"sounds"`. `maya_hub` wires the two callbacks to `maya_hubsound`.

**Tech Stack:** Python 3 stdlib (`wave`, `struct`, `math`), PySide6 QtWidgets / QtMultimedia, Maya `cmds.optionVar`; tests: `mayapy -m unittest`, Qt offscreen.

Spec: `docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md`.

## Global Constraints

- `maya_hubsound` imports nothing of maya or Qt at import time (a subprocess test pins it).
- `play()` never raises; disabled / no file / no backend answers False.
- optionVar `skeldarAnimHub_sounds`, default ON.
- Throttle 35 ms (`MIN_GAP = 0.035`), pool of 3 (`POOL = 3`).
- The sound: E6 1318.51 Hz level 1.0 decay 16 ms + 2637.02 Hz level 0.2 decay 7 ms, attack 1.5 ms, length 80 ms, fade 15 ms, peak 0.178 (−15 dBFS), 48 kHz 16-bit mono.
- `maya_hubqt` imports no audio; `maya_hubsound` knows no widgets.
- Every new `maya_*.py` beside install.py is a payload row.

---

### Task 1: `maya_hubsound` — the sound and its player

**Files:**
- Create: `SkeldarAnim/maya_hubsound.py`
- Create: `docs/superpowers/plans/make_hub_sounds.py`
- Create (generated): `SkeldarAnim/assets/sounds/hover.wav`
- Test: `tests/test_hubsound.py`

**Interfaces:**
- Produces: `SOUNDS`, `Tone`, `RATE`, `OPTIONVAR`, `MIN_GAP`, `POOL`; `synth(tone, rate=RATE) -> list[float]`; `wav_bytes(samples, rate=RATE) -> bytes`; `sound_path(name) -> str`; `write(name, path=None) -> str`; `enabled() -> bool`; `set_enabled(on) -> bool`; `preload(name="hover") -> bool`; `play(name, now=None) -> bool`; seams `_cmds()` and `make_player(path)`; `reset()` (tests).

- [ ] **Step 1: tests** — synth shape (length 3840 samples, peak 0.178 ± 1e-9, first and last sample 0, mean ≈ 0, dominant frequency by zero crossings ≈ 1318 Hz), wav round trip (1 channel, 2 bytes, 48000), the shipped file equal to the synthesis within 1 LSB, enabled default True / set_enabled writes the optionVar and plays once when turned on, play: disabled → False, throttle (two plays 10 ms apart → second False, 40 ms → True), a missing file → False with no player made, a player that raises → False, the pool used in turn, the players kept on `sys` across a reload, stdlib-only import.
- [ ] **Step 2:** run `mayapy -m unittest tests.test_hubsound -v` — FAIL (no module).
- [ ] **Step 3:** write the module (see the spec's "The sound" and "How it plays"), the generator, run the generator.
- [ ] **Step 4:** run the tests — PASS.
- [ ] **Step 5:** commit.

### Task 2: the skin plays it and offers the switch

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (`sounding`, `Skin._hover_from`, `_build_header` menu row, `Skin.paint_sounds`)
- Modify: `SkeldarAnim/maya_hub.py` (`_callbacks`, `_hover_sound`, `set_sounds`, `_dress_header`)
- Modify: `SkeldarAnim/install.py` (payload row `maya_hubsound.py`)
- Test: `tests/test_hubqt.py`, `tests/test_hub.py`

**Interfaces:**
- Consumes: `maya_hubsound.play("hover")`, `set_enabled(on)`, `enabled()`, `preload("hover")`.
- Produces: `maya_hubqt.sounding(widget, root) -> bool`; callbacks `"hover"` () and `"sounds"` (checked: bool); `Skin.sounds_action`; `Skin.paint_sounds(on)`; `maya_hub.set_sounds(on) -> bool`.

- [ ] **Step 1: tests** — entering a button / a segment-like checkable QPushButton / a QComboBox / a card header / a header QToolButton calls back `"hover"` once; a label, a line edit, a disabled button, a widget outside the hub do not; the menu reads Check update, Hotkey Editor..., Interface sounds, Classic look, the sounds row checkable and calling back `("sounds", checked)`; `paint_sounds` checks it without calling back; `maya_hub._callbacks()` has `hover` and `sounds`, `set_sounds(False)` writes the optionVar and paints the skin.
- [ ] **Step 2:** run them — FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** the whole suite — PASS.
- [ ] **Step 5:** commit.

### Task 3: live — the animator's hub

- [ ] Install from a `git archive` of the commit (other sessions share the tree), the open hub rebuilds itself (trap 94).
- [ ] Over port 7001: the menu row present and checked; a QEnterEvent sent to a real Maya button, a segment, a dropdown and a card header plays (the pool's effect `isPlaying` / status Ready), a label does not; the throttle; the switch off silences it and writes the optionVar; back on.
- [ ] CLAUDE.md section, commit.

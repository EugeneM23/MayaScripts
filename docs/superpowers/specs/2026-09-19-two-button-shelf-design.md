# Two buttons on the shelf: SkeldarAnim and OverRig

**Date:** 2026-09-19
**Status:** approved

## The ask

«Давай из нашей полки уберем все лишнии скрипты. Пока пусть будет только
наш SkeldarAnim ну и овер риг тоже пускай устанавливается вместе с ним.»

Asked which half of OverRig to bring back, the animator chose the shelf
button only: the 84 OverRig hotkey rows stay off.

## What changes

The shelf a drop of `install.py` builds is **two buttons**: `SkeldarAnim`
(the hub, `maya_hub.show`) and `OverRig` (Pavel Barnev's own installer
command, verbatim, pointing at the shipped `overrig/`).

Nothing is deleted. The word was «пока», and the plugin already has the
shape for "off for now": a boolean in `skeldar_features.py`, read by
`install.button_specs`.

1. **`SECTION_BUTTONS = False`** — the seven per-section buttons (UE
   Bridge, Characters, Weapons, Retarget, Hotkeys, Studio, Colour) carry
   this flag in `_PYTHON_BUTTONS` where they carried `""`. The hub row
   stays unflagged. Their icons, `show_window()` functions and hotkey rows
   (`window.*`) stay and keep opening the hub on the section. `True`
   restores all seven in their old places.
2. **`OVERRIG` is split.** `OVERRIG = True` now means the shelf button
   only. A new **`OVERRIG_HOTKEYS = False`** gates the 84 rows in
   `maya_hotkeys.commands`. The picker (`PICKER`) and Overshoot
   (`OVERSHOOT`) are untouched.

Order with everything on is unchanged: the hub, the Python rows in table
order, OverRig last. With the shipped flags: `SkeldarAnim`, `OverRig`.

## What does not change

- The payload. Every module still ships; `make_build.py` reads the same
  whitelist.
- `maya_hotkeys.paint` finds the `Hotkeys` shelf button by label and
  skips the paint when it is absent (already the case); the hub's
  `Hotkey map: ON/OFF` toggle is painted instead.
- The hub's `SECTIONS` table: every section is still there.

## Tests

`tests/test_install.py::ButtonSpecs`: the shipped shelf is the two
labels; `SECTION_BUTTONS` brings the seven back in order; `OVERRIG` alone
adds only the button; the OverRig command is still the native installer.
`tests/test_hotkeys.py::FeatureFlags`: the 84 rows ride `OVERRIG_HOTKEYS`
and ignore `OVERRIG`; the shipped `OVERRIG_HOTKEYS` is False.

## Proof

Unit tests, then a real reinstall into the animator's open Maya over the
command port (`install.install(quiet=True)`, the `install` module purged
first) and a read of the shelf's button labels; then `make_build.py`.

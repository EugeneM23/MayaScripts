# Maya in the hub's colours (variant B)

2026-10-17. The animator: «Можем ли мы поменять цвета маи под наш интерфейс?» They were shown four mockups (Maya as
it stands, then A, B and C: https://claude.ai/artifact/3cscUGngcoXQjp4on8Lr1Z) and chose **B, the hub whole**: Maya's
panels, fields, menus and selection in the hub's charcoal and orange, a dark viewport, a dark Graph Editor. What follows
was decided alone (the animator's way: «work to the end, then show»).

## What changes

Three layers. Each is saved before it changes and given back exactly when the theme goes off.

1. **Qt's palette** on the QApplication: Window / Base / Button / Text / Highlight and the rest, from
   `maya_hubstyle.TOKENS` (`maya_mayatheme.PALETTE`). Maya's own style paints most of its widgets from it, including
   the Outliner, Channel Box and Node Editor, which ignore stylesheets.
2. **A short stylesheet appended to the application's own**, between two marker comments. It covers menus, the menu
   bar, tooltips, line edits, item views' selection, header sections and the tab bar's selected tab. It sets **colours,
   borders and radii only, never a size, padding or margin**: a size in an app-wide sheet would move every Maya layout
   and the hub's dock widths (traps 66, 117). The hub's root sheet sets the same properties for its own widgets and wins
   (a nearer sheet wins in Qt), so the hub does not change. No blanket `QWidget` rule (trap 98).
3. **Maya's display colours** (`displayRGBColor`), a list in `maya_mayatheme.RGB`, and the viewport gradient switched
   on (`displayPref -displayGradient`):
   - the viewport: `background`, `backgroundTop`, `backgroundBottom`;
   - the Graph Editor: `modernGraphEditor*` background, grid, axis and time ruler, and its outliner's background,
     selection and text;
   - the Outliner's child highlight; the Node Editor's background and grid; the Dope Sheet's backgrounds.
   Keys, curves, tangents and manipulators keep Maya's colours: they carry meaning.

## How it is switched

- ⋮ → **Maya theme**, a checkable row beside Interface sounds and animations. The optionVar `skeldarMayaTheme` is
  1 or 0, **off by default**: switching every colleague's Maya on by an update was not asked for.
- **On**: the first time, every display colour in `RGB` and the gradient flag are read and kept as JSON in the
  optionVar `skeldarMayaTheme_saved`. A second On while that is kept does not read again, or the theme's own colours
  would be saved as "theirs" (Viewport Studio's rule). Then the colours are written and the Qt part applied.
- **Off**: the saved colours and flag are written back, the optionVar removed, the palette and the application sheet
  put back.
- **At Maya's start** the hub's build calls `maya_mayatheme.ensure()` (deferred, guarded, GUI only). Maya keeps the
  display colours in its prefs by itself, so only the Qt part is applied again.
- The Qt state (the original palette and the original sheet) lives on `sys._skeldar_mayatheme` (trap 111). If it is
  lost, the original sheet is what precedes our start marker.

## Limits, said

- Icons, Maya's splash and windows that set their own colours (old MEL `-backgroundColor`, OverRig, AdvancedSkeleton)
  keep theirs.
- Viewport Studio sets the viewport background too. Its Restore gives back what stood when it was pressed, so the
  theme switched off while a studio stands can be overwritten by the studio's later Restore.
- Not seen in a GUI Maya when written: the palette's reach into Maya's own style is the animator's to judge.

## Proof

- Unit tests (`tests/test_mayatheme.py`): the sheet holds no size property, the palette covers every role it names,
  on / saved-once / off on a fake `cmds` (a second On does not save again, Off writes back exactly and removes the
  memory), the Qt part offscreen (the sheet appended between markers and taken out leaving the original byte for byte,
  the palette put back), the menu row and its callback.
- `docs/superpowers/plans/verify_maya_theme.py` for a GUI Maya: switch on, read the palette and sheet, every RGB
  written, a playblast of the viewport dark, switch off, everything equal to before. Unrun when written.

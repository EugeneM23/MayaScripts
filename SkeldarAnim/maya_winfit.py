"""maya_winfit - a `cmds` window that fits its content and can be stretched.

Three of the shelf's panels (Viewport Studio, Colour, Overshoot) were one
column of controls in a `sizeable=False` window at a height written in the
code. Maya scales every control for the display - on the animator's 150 %
monitor a 26 px button is 40 px tall - so the column outgrew the window
and the buttons at the bottom were clipped, with no way to drag the window
open («окошко не растягивается из-за чего кнопочки не видно», 2026-09-17).

This module is the one answer, so the fix exists in one copy:

    maya_winfit.forget_saved_size(WINDOW, cmds)      # before cmds.window
    cmds.window(WINDOW, ..., sizeable=True)
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=SPACING)
    ...
    cmds.showWindow(WINDOW)
    maya_winfit.fit_window(WINDOW, column, cmds, SPACING, MARGIN)

Every function takes the caller's `cmds`, because each tool's tests
rebind that module's own `cmds` attribute to a fake (CLAUDE.md, "Running
tests"); a module-level import here would look past the fake.

Two facts, both measured live 2026-09-17 on a 150 % display:

- `cmds.control -q -height` answers PHYSICAL pixels, while
  `cmds.window -e -height N` takes LOGICAL units and Maya multiplies
  them by the display scale (`window -e -height 600` queries back as
  900). Writing a measured 678 px sum straight back made a 1018 px
  window. The real scale is `mayaDpiSetting -q -realScaleValue` (1.5
  there; `-scaleValue` answers 1.0 and is not it).
- A saved `windowPref` (Maya writes one when a window closes) wins over
  the size a `cmds.window` creation asks for. The saved one was the
  clipped size, so it has to be forgotten before the window is made or
  the fix never reaches a Maya that opened the old panel once.
"""

import math


def fit_height(heights, spacing, margin):
    """The window height that shows every control: the children as Maya
    laid them out, the gaps between them, and a margin. Pure.

    Measured rather than tabulated: a number written in the code is right
    on one monitor and clips the buttons on the next.
    """
    heights = list(heights)
    gaps = spacing * (len(heights) - 1) if heights else 0
    return int(sum(heights) + gaps + margin)


def logical(pixels, scale):
    """Physical pixels as the logical units `window -e -height` takes,
    rounded up so a fraction can never clip the last row. Pure."""
    scale = scale if scale and scale > 0 else 1.0
    return int(math.ceil(pixels / float(scale)))


def dpi_scale(cmds):
    """Maya's real UI scale (1.5 on a 150 % display), 1.0 when unknown."""
    try:
        scale = float(cmds.mayaDpiSetting(query=True, realScaleValue=True))
    except Exception:
        return 1.0
    return scale if scale > 0 else 1.0


def forget_saved_size(window, cmds):
    """Drop the size Maya remembered for `window`. Returns True if there
    was one. Call it BEFORE `cmds.window(window, ...)`."""
    try:
        if not cmds.windowPref(window, exists=True):
            return False
        cmds.windowPref(window, remove=True)
        return True
    except Exception:
        return False


def child_heights(column, cmds):
    """The real height of every direct child of `column`, in pixels."""
    children = cmds.columnLayout(column, query=True, childArray=True) or []
    return [cmds.control("%s|%s" % (column, child), query=True, height=True)
            for child in children]


def fit_window(window, column, cmds, spacing, margin):
    """Give `window` the height its `column` really takes. Returns the
    logical height written.

    Call it AFTER `showWindow`, when the heights are real; `edit` wins
    over any size Maya remembered for the window.
    """
    pixels = fit_height(child_heights(column, cmds), spacing, margin)
    height = logical(pixels, dpi_scale(cmds))
    cmds.window(window, edit=True, height=height)
    return height

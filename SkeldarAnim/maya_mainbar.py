"""Maya's main bar in the hub's colours (2026-10-21).

The animator, with a picture of Maya's top - the Windows title bar (light), the
File / Edit / ... menu bar and the Workspace selector: «Давай перекрасим главную
панель в цвета нашего дизайна».

Two parts, both put back by Off:

- the title bar: Windows 11 paints a window's caption in a colour the window
  asks for (DwmSetWindowAttribute: DWMWA_CAPTION_COLOR 35, DWMWA_TEXT_COLOR 36,
  DWMWA_BORDER_COLOR 34; DWMWA_COLOR_DEFAULT gives Windows' own back). Older
  Windows answers an error and the caption stays as it is;
- the menu bar: a style sheet on Maya's main QMenuBar alone, its titles muted and
  lit under the mouse, the Workspace label and drop-down on the right in the
  hub's look. Colours, borders and radii only, never a size. Maya's drop-down
  menus stay Maya's (their rows are Maya's own drawing - trap 285).

A 2 s watch puts both back on when Maya re-creates its window or empties the
sheet. On with Use Skeldar interface, off with Use Maya interface, and its own
row ⋮ -> Main bar (on by default).

    enabled() / set_enabled(on)   the switch, at once
    ensure()                      at the hub's build
    sheet(scale)                  the menu bar's sheet (pure)
"""

import maya_hubstyle as hubstyle

OPTIONVAR = "skeldarMainBar"
DEFAULT = True
STATE = "_skeldar_mainbar"              # on sys (trap 111)
MARK = "skeldarMainBar"                 # a Qt property on the skinned menu bar
WATCH_MS = 2000
T = hubstyle.TOKENS

CAPTION = T["panel"]                    # the title bar: the hub's background
CAPTION_TEXT = T["text2"]
BORDER = T["line"]

DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF

_SHEET = """
QMenuBar[skeldarMainBar="1"] {{
    background: {panel}; color: {muted}; border: none;
    border-bottom: {b}px solid {track}; spacing: {p2}px; }}
QMenuBar[skeldarMainBar="1"]::item {{
    background: transparent; color: {muted}; padding: {p3}px {p8}px; border-radius: {r6}px; }}
QMenuBar[skeldarMainBar="1"]::item:selected,
QMenuBar[skeldarMainBar="1"]::item:pressed {{ background: {hover}; color: {text}; }}
QMenuBar[skeldarMainBar="1"] QLabel {{ background: transparent; color: {faint}; }}
QMenuBar[skeldarMainBar="1"] QComboBox {{
    background: {track}; color: {text2}; border: {b}px solid {line};
    border-radius: {r6}px; padding: 0 {p8}px; }}
QMenuBar[skeldarMainBar="1"] QComboBox:hover {{ border-color: {muted}; }}
QMenuBar[skeldarMainBar="1"] QComboBox QAbstractItemView {{
    background: {card}; color: {text}; border: {b}px solid {line};
    selection-background-color: {active}; selection-color: {accent_text}; }}
QMenuBar[skeldarMainBar="1"] QToolButton {{
    background: transparent; border: {b}px solid transparent; border-radius: {r6}px; }}
QMenuBar[skeldarMainBar="1"] QToolButton:hover {{ background: {hover}; border-color: {line}; }}
"""


def colorref(hex_colour):
    """'#rrggbb' as Windows' COLORREF 0x00bbggrr (pure)."""
    value = hex_colour.lstrip("#")
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return r | (g << 8) | (b << 16)


def sheet(scale=1.0):
    """The menu bar's sheet at `scale` (Maya's sheet pixels are PHYSICAL, trap
    98); every rule under the bar's mark (pure)."""
    def px(value):
        return max(1, int(round(value * scale)))
    values = dict(T)
    values["active"] = T["card_active"]
    for name, value in (("b", 1), ("p2", 2), ("p3", 3), ("p8", 8), ("r6", 6)):
        values[name] = px(value)
    return _SHEET.format(**values)


def caption_values(on):
    """{attribute: COLORREF} the title bar is given (pure)."""
    if not on:
        return {DWMWA_CAPTION_COLOR: DWMWA_COLOR_DEFAULT,
                DWMWA_TEXT_COLOR: DWMWA_COLOR_DEFAULT,
                DWMWA_BORDER_COLOR: DWMWA_COLOR_DEFAULT}
    return {DWMWA_CAPTION_COLOR: colorref(CAPTION),
            DWMWA_TEXT_COLOR: colorref(CAPTION_TEXT),
            DWMWA_BORDER_COLOR: colorref(BORDER)}


# ------------------------------------------------------------------- maya

def _cmds():
    import maya.cmds as cmds
    return cmds


def enabled():
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return DEFAULT
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:                                        # noqa: BLE001
        return False


def _state():
    import sys
    state = getattr(sys, STATE, None)
    if state is None:
        state = {"timer": None, "hwnd": None, "old_sheet": None}
        setattr(sys, STATE, state)
    return state


def _scale():
    try:
        return float(_cmds().mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def main_window():
    """Maya's main window as a QMainWindow, or None."""
    try:
        from maya import OpenMayaUI
        from PySide6 import QtWidgets
        import shiboken6
        pointer = OpenMayaUI.MQtUtil.mainWindow()
        if not pointer:
            return None
        return shiboken6.wrapInstance(int(pointer), QtWidgets.QMainWindow)
    except Exception:                                        # noqa: BLE001
        return None


def menu_bar(window=None):
    window = window if window is not None else main_window()
    if window is None:
        return None
    #  Maya's main window wraps as a QWidget (its cached wrapper, trap 96), so
    #  no menuBar(): the bar is the window's own QMenuBar child (measured
    #  2026-10-21; the Workspace selector lives in it)
    try:
        from PySide6 import QtWidgets
        for child in window.children():
            if isinstance(child, QtWidgets.QMenuBar):
                return child
    except Exception:                                        # noqa: BLE001
        pass
    return None


def paint_caption(hwnd, on):
    """The title bar's colours set through DWM; True when Windows took them."""
    try:
        import ctypes
        from ctypes import wintypes
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = (wintypes.HWND, wintypes.DWORD,
                                              ctypes.c_void_p, wintypes.DWORD)
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        took = True
        for attribute, value in caption_values(on).items():
            colour = wintypes.DWORD(value)
            result = dwm.DwmSetWindowAttribute(int(hwnd), attribute,
                                               ctypes.byref(colour),
                                               ctypes.sizeof(colour))
            took = took and result == 0
        return took
    except Exception:                                        # noqa: BLE001
        return False


def _hwnd(window):
    try:
        return int(window.effectiveWinId())
    except Exception:                                        # noqa: BLE001
        return None


def apply():
    """Both parts on. True when the menu bar was found."""
    window = main_window()
    if window is None:
        return False
    state = _state()
    hwnd = _hwnd(window)
    if hwnd and hwnd != state["hwnd"]:
        paint_caption(hwnd, True)
        state["hwnd"] = hwnd
    bar = menu_bar(window)
    if bar is None:
        return False
    wanted = sheet(_scale())
    if bar.property(MARK) != "1" or bar.styleSheet() != wanted:
        if bar.property(MARK) != "1":
            state["old_sheet"] = bar.styleSheet()
        bar.setProperty(MARK, "1")
        bar.setStyleSheet(wanted)
    return True


def remove():
    """Both parts back to Maya's and Windows'."""
    window = main_window()
    state = _state()
    if window is None:
        return False
    hwnd = _hwnd(window)
    if hwnd:
        paint_caption(hwnd, False)
    state["hwnd"] = None
    bar = menu_bar(window)
    if bar is not None and bar.property(MARK) == "1":
        bar.setProperty(MARK, None)
        bar.setStyleSheet(state.get("old_sheet") or "")
        state["old_sheet"] = None
    return True


def _tick():
    try:
        if enabled():
            apply()
    except Exception:                                        # noqa: BLE001
        pass


def watch():
    state = _state()
    if state["timer"] is not None:
        return
    from PySide6 import QtCore
    timer = QtCore.QTimer()
    timer.setInterval(WATCH_MS)
    timer.timeout.connect(_tick)
    timer.start()
    state["timer"] = timer


def unwatch():
    state = _state()
    timer = state.get("timer")
    state["timer"] = None
    if timer is not None:
        try:
            timer.stop()
            timer.deleteLater()
        except Exception:                                    # noqa: BLE001
            pass


def ensure():
    """At the hub's build: on and watched while the switch is on, else back."""
    cmds = _cmds()
    if cmds.about(batch=True):
        return False
    if not enabled():
        unwatch()
        return remove() if _state()["hwnd"] is not None else False
    done = apply()
    watch()
    return done


def set_enabled(on):
    """⋮ -> Main bar: Maya's title and menu bar in our colours at once, or back."""
    on = bool(on)
    cmds = _cmds()
    cmds.optionVar(intValue=(OPTIONVAR, int(on)))
    if cmds.about(batch=True):
        return "Main bar %s" % ("on" if on else "off")
    if on:
        apply()
        watch()
        return "Main bar in our colours"
    unwatch()
    remove()
    return "Main bar back to Maya's"


def reload_live():
    """After an install: the old module's watch stopped, the bar skinned again
    by this module (the caption painted again too)."""
    unwatch()
    _state()["hwnd"] = None
    return ensure()

"""Maya in the hub's colours (2026-10-17, variant B of the mockups).

The animator: «Можем ли мы поменять цвета маи под наш интерфейс?», then «Строим
вариант B - хаб целиком». Spec:
docs/superpowers/specs/2026-10-17-maya-theme-design.md

Three layers, each saved before it changes and given back when the theme goes
off:

    PALETTE / DISABLED   Qt's palette on the QApplication (Maya's own style
                         paints the Outliner, Channel Box and the rest from it)
    sheet(scale)         a short stylesheet appended to the application's own
                         between START and END: colours, borders, radii - never
                         a size (an app-wide size would move every layout and
                         the hub's dock widths)
    RGB                  Maya's display colours (displayRGBColor): the viewport
                         gradient, the Graph Editor, Outliner, Node Editor and
                         Dope Sheet backgrounds. Keys, curves and manipulators
                         keep Maya's colours: they carry meaning.

    enabled() / set_enabled(on)   ⋮ -> Maya theme in the hub (off by default)
    ensure()                      at Maya's start: the Qt part again (Maya keeps
                                  the display colours in its prefs itself)

Stdlib at import; `maya.cmds` and Qt are imported where used.
"""

import json
import sys

import maya_hubstyle as hubstyle

OPTIONVAR = "skeldarMayaTheme"
SAVED_VAR = "skeldarMayaTheme_saved"
STATE = "_skeldar_mayatheme"          # on sys (trap 111)
START = "/* skeldarMayaTheme start */"
END = "/* skeldarMayaTheme end */"

T = hubstyle.TOKENS
#  a selection in Maya's lists and fields: the accent tint, deep enough to
#  read on the darkest field
SELECT = "#5a3922"
SELECT_TEXT = T["accent_text"]
CHILD_SELECT = "#2d2620"

PALETTE = {
    "Window": T["panel"],
    "WindowText": T["text"],
    "Base": T["track"],
    "AlternateBase": T["field"],
    "Text": T["text"],
    "Button": T["card"],
    "ButtonText": T["text"],
    "BrightText": "#ffffff",
    "Highlight": SELECT,
    "HighlightedText": SELECT_TEXT,
    "ToolTipBase": T["card"],
    "ToolTipText": T["text"],
    "Light": T["hover"],
    "Midlight": "#2c2e33",
    "Mid": T["inset"],
    "Dark": "#141517",
    "Shadow": "#0d0d0e",
    "Link": T["accent_text"],
    "PlaceholderText": T["faint"],
}
DISABLED = {
    "WindowText": T["faint"],
    "Text": T["faint"],
    "ButtonText": T["faint"],
    "Highlight": T["hover"],
    "HighlightedText": T["muted"],
}


def _rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return tuple(round(int(h[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4))


RGB = dict((name, _rgb(colour)) for name, colour in (
    #  the viewport: a dark gradient (displayPref -displayGradient on)
    ("background", "#26282c"),
    ("backgroundTop", "#3a3c42"),
    ("backgroundBottom", "#141517"),
    #  the Graph Editor
    ("modernGraphEditorBackground", T["track"]),
    ("modernGraphEditorGrid", "#24262a"),
    ("modernGraphEditorGridAxis", T["line"]),
    ("modernGraphEditorTimeRulerBackgroundColor", T["panel"]),
    ("modernGraphEditorTimeRulerLabelColor", T["muted"]),
    ("modernGraphEditorTimeRulerTickColor", T["hover"]),
    ("graphEditorBackground", T["track"]),
    ("graphEditorGrid", "#24262a"),
    ("graphEditorGridAxis", T["line"]),
    ("graphEditorOutlinerBackground", T["track"]),
    ("graphEditorOutlinerSection", T["panel"]),
    ("graphEditorOutlinerSelected", SELECT),
    ("graphEditorOutlinerSelectedText", SELECT_TEXT),
    ("graphEditorOutlinerChildSelected", CHILD_SELECT),
    ("graphEditorOutlinerText", "#c9cacf"),
    #  the Outliner, the Node Editor, the Dope Sheet, the Hypergraph
    ("outlinerChildHilightColor", CHILD_SELECT),
    ("nodeEditorBackground", T["track"]),
    ("nodeEditorGrid", "#24262a"),
    ("dopeSheetBackgroundColor", T["track"]),
    ("dopeSheetOutlinerBackground", T["track"]),
    ("dopeSheetGrid", "#24262a"),
    ("hyperBackgroundColor", T["track"]),
))

#  colours, borders, radii only (a test pins: no width, height, padding,
#  margin, spacing or font size), no blanket QWidget rule (trap 98)
_SHEET = """
QToolTip {{ background: {card}; color: {text}; border: {b1}px solid {line};
  border-radius: {r4}px; }}
QMenuBar {{ background: {panel}; color: {text}; }}
QMenuBar::item:selected {{ background: {hover}; color: {text};
  border-radius: {r4}px; }}
QLineEdit {{ background: {field}; color: {text}; border: {b1}px solid {inset_line};
  border-radius: {r4}px; selection-background-color: {select};
  selection-color: {select_text}; }}
QLineEdit:hover {{ border-color: {line}; }}
QLineEdit:focus {{ border-color: {accent}; }}
QAbstractItemView {{ selection-background-color: {select};
  selection-color: {select_text}; }}
QTextEdit, QPlainTextEdit {{ selection-background-color: {select};
  selection-color: {select_text}; }}
QHeaderView::section {{ background: {card}; color: {muted};
  border: none; border-right: {b1}px solid {track};
  border-bottom: {b1}px solid {track}; }}
QSplitter::handle {{ background: {track}; }}
"""


def sheet(scale=1.0):
    """The stylesheet at display `scale` (its pixels are physical, trap 98)."""
    values = dict(T)
    values.update(select=SELECT, select_text=SELECT_TEXT,
                  b1=hubstyle.px(1, scale), r4=hubstyle.px(4, scale))
    return _SHEET.format(**values).strip() + "\n"


def with_ours(original, ours):
    """`original` (any copy of ours cut out first) with `ours` appended
    between START and END."""
    base = without_ours(original)
    return "{0}\n{1}\n{2}\n{3}\n".format(base, START, ours.rstrip("\n"), END)


def without_ours(sheet_text):
    """`sheet_text` with ours (START..END) cut out, as it was before: the one
    newline `with_ours` put before START and the one after END go too."""
    text = sheet_text or ""
    start = text.find(START)
    if start < 0:
        return text
    end = text.find(END, start)
    tail = text[end + len(END):] if end >= 0 else ""
    head = text[:start]
    if head.endswith("\n"):
        head = head[:-1]
    if tail.startswith("\n"):
        tail = tail[1:]
    return head + tail


# ------------------------------------------------------------------- scene

def _cmds():
    import maya.cmds as cmds
    return cmds


def enabled():
    """The theme is on (off by default)."""
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return False
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:                                        # noqa: BLE001
        return False


def _read_colours(cmds):
    colours, missing = {}, []
    for name in RGB:
        try:
            value = cmds.displayRGBColor(name, query=True, alpha=True)
            colours[name] = [float(v) for v in value]
        except Exception:                                    # noqa: BLE001
            missing.append(name)
    return colours, missing


def _write(cmds, name, values):
    values = list(values)
    if len(values) == 3:
        values.append(1.0)
    cmds.displayRGBColor(name, *values[:4], alpha=True)


def _gradient(cmds):
    try:
        return bool(cmds.displayPref(query=True, displayGradient=True))
    except Exception:                                        # noqa: BLE001
        return None


def _set_gradient(cmds, on):
    try:
        cmds.displayPref(displayGradient=bool(on))
    except Exception:                                        # noqa: BLE001
        pass


def _switch_on(cmds):
    """Theirs kept once, ours written. Answers the colours Maya lacks."""
    current, missing = _read_colours(cmds)
    if not cmds.optionVar(exists=SAVED_VAR):
        cmds.optionVar(stringValue=(SAVED_VAR, json.dumps(
            {"rgb": current, "gradient": _gradient(cmds)})))
    for name, rgb in RGB.items():
        if name in missing:
            continue
        alpha = current[name][3] if len(current[name]) > 3 else 1.0
        try:
            _write(cmds, name, list(rgb) + [alpha])
        except Exception:                                    # noqa: BLE001
            missing.append(name)
    _set_gradient(cmds, True)
    return missing


def _switch_off(cmds):
    """Theirs written back and forgotten."""
    if not cmds.optionVar(exists=SAVED_VAR):
        return
    try:
        kept = json.loads(cmds.optionVar(query=SAVED_VAR))
    except Exception:                                        # noqa: BLE001
        kept = {}
    for name, values in (kept.get("rgb") or {}).items():
        try:
            _write(cmds, name, values)
        except Exception:                                    # noqa: BLE001
            pass
    if kept.get("gradient") is not None:
        _set_gradient(cmds, kept["gradient"])
    cmds.optionVar(remove=SAVED_VAR)


def set_enabled(on):
    """⋮ -> Maya theme: switched, remembered, the line to say."""
    on = bool(on)
    cmds = _cmds()
    if on:
        missing = _switch_on(cmds)
        qt_ok = apply_qt()
    else:
        _switch_off(cmds)
        qt_ok = remove_qt()
        missing = []
    cmds.optionVar(intValue=(OPTIONVAR, int(on)))
    message = ("Maya theme ON - Maya in the hub's colours" if on
               else "Maya theme OFF - Maya's own colours back")
    if missing:
        message += (" | %d colour%s this Maya does not have: %s"
                    % (len(missing), "" if len(missing) == 1 else "s",
                       ", ".join(sorted(missing))))
    if not qt_ok:
        message += " | the panels could not be recoloured here (no Qt)"
    return message


def ensure():
    """At Maya's start (the hub's build): the Qt part again while the theme
    is on. Maya keeps the display colours in its prefs by itself."""
    if enabled():
        return apply_qt()
    return False


# ---------------------------------------------------------------------- qt

def _qt():
    try:
        from PySide6 import QtGui, QtWidgets
    except ImportError:
        try:
            from PySide2 import QtGui, QtWidgets
        except ImportError:
            return None, None
    return QtGui, QtWidgets


def _scale():
    try:
        return float(_cmds().mayaDpiSetting(query=True,
                                            realScaleValue=True)) or 1.0
    except Exception:                                        # noqa: BLE001
        return 1.0


def _state():
    state = getattr(sys, STATE, None)
    if state is None:
        state = {}
        setattr(sys, STATE, state)
    return state


def palette(QtGui):                                          # noqa: N803
    """Our QPalette, from PALETTE and DISABLED."""
    pal = QtGui.QPalette()
    roles = QtGui.QPalette.ColorRole
    for group in (QtGui.QPalette.Active, QtGui.QPalette.Inactive,
                  QtGui.QPalette.Disabled):
        for name, colour in PALETTE.items():
            role = getattr(roles, name, None)
            if role is not None:
                pal.setColor(group, role, QtGui.QColor(colour))
    for name, colour in DISABLED.items():
        role = getattr(roles, name, None)
        if role is not None:
            pal.setColor(QtGui.QPalette.Disabled, role, QtGui.QColor(colour))
    return pal


def apply_qt():
    """Our palette and sheet on the application; what stood is kept the first
    time. Answers False without Qt or an application."""
    QtGui, QtWidgets = _qt()                                 # noqa: N806
    app = QtWidgets.QApplication.instance() if QtWidgets else None
    if app is None:
        return False
    state = _state()
    if "palette" not in state:
        state["palette"] = QtGui.QPalette(app.palette())
    app.setPalette(palette(QtGui))
    current = app.styleSheet() or ""
    wanted = with_ours(current, sheet(_scale()))
    if wanted != current:
        app.setStyleSheet(wanted)
    return True


def remove_qt():
    """The palette and sheet that stood before, back."""
    QtGui, QtWidgets = _qt()                                 # noqa: N806
    app = QtWidgets.QApplication.instance() if QtWidgets else None
    if app is None:
        return False
    current = app.styleSheet() or ""
    original = without_ours(current)
    if original != current:
        app.setStyleSheet(original)
    state = _state()
    kept = state.pop("palette", None)
    if kept is not None:
        app.setPalette(kept)
    else:
        app.setPalette(app.style().standardPalette())
    return True

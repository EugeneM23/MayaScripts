"""The side panel's pages in the Time Bar's colours (2026-10-17, «приблизить дизайн и
цвета наших панелей к таймслайдеру»): Maya's own Channel Box, Layer Editor and
Attribute Editor, recoloured inside the panel only - the hidden Maya theme's palette
(maya_mayatheme), and a sheet of colours, borders and radii, never a size.
"""

import maya_hubstyle as hubstyle

T = hubstyle.TOKENS
STACK = "skeldarSidePanelStack"

_SHEET = """
QWidget#{stack} {{ background: {panel}; color: {text}; }}
QWidget#{stack} QPushButton {{ background: {card}; color: {text2};
  border: {b1}px solid {track_edge}; border-radius: {r5}px; }}
QWidget#{stack} QPushButton:hover {{ background: {hover}; color: {text}; }}
QWidget#{stack} QPushButton:pressed, QWidget#{stack} QPushButton:checked {{
  background: {accent_tint}; color: {accent_text}; border-color: {accent}; }}
QWidget#{stack} QPushButton:disabled {{ background: {track}; color: {faint}; }}
QWidget#{stack} QLineEdit {{ background: {track}; color: {text};
  border: {b1}px solid {track_edge}; border-radius: {r4}px;
  selection-background-color: {select}; selection-color: {accent_text}; }}
QWidget#{stack} QLineEdit:hover {{ border-color: {line}; }}
QWidget#{stack} QLineEdit:focus {{ border-color: {accent}; }}
QWidget#{stack} QComboBox {{ background: {card}; color: {text2};
  border: {b1}px solid {track_edge}; border-radius: {r5}px; }}
QWidget#{stack} QComboBox:hover {{ background: {hover}; color: {text}; }}
QWidget#{stack} QAbstractItemView {{ background: {track}; color: {text};
  alternate-background-color: {field};
  selection-background-color: {select}; selection-color: {accent_text}; }}
QWidget#{stack} QMenuBar {{ background: transparent; color: {text2}; }}
QWidget#{stack} QMenuBar::item:selected {{ background: {hover}; color: {text};
  border-radius: {r4}px; }}
QWidget#{stack} QTabBar::tab {{ background: {track}; color: {muted};
  border: {b1}px solid {track_edge}; border-top-left-radius: {r5}px; padding: {p3}px {p10}px;
  border-top-right-radius: {r5}px; }}
QWidget#{stack} QTabBar::tab:selected {{ background: {thumb}; color: {text}; }}
QWidget#{stack} QTabBar::tab:hover {{ color: {text}; }}
QWidget#{stack} QScrollBar:vertical {{ background: {panel}; border: none; }}
QWidget#{stack} QScrollBar::handle:vertical {{ background: {line};
  border-radius: {r4}px; }}
QWidget#{stack} QScrollBar::handle:vertical:hover {{ background: {muted}; }}
QWidget#{stack} QScrollBar:horizontal {{ background: {panel}; border: none; }}
QWidget#{stack} QScrollBar::handle:horizontal {{ background: {line};
  border-radius: {r4}px; }}
QWidget#{stack} QScrollBar::add-line, QWidget#{stack} QScrollBar::sub-line {{
  background: none; border: none; }}
QWidget#{stack} QScrollBar::add-page, QWidget#{stack} QScrollBar::sub-page {{
  background: none; }}
QWidget#{stack} QSplitter::handle {{ background: {track}; }}
QWidget#{stack} QadskFrameLayoutHeader {{ background: {card}; color: {text};
  border-radius: {r4}px; }}
QWidget#{stack} QadskFrameLayoutHeader:hover {{ background: {hover}; }}
QWidget#{stack} QHeaderView::section {{ background: {card}; color: {muted};
  border: none; border-right: {b1}px solid {track};
  border-bottom: {b1}px solid {track}; }}
"""


def sheet(scale=1.0, tokens=None):
    """The pages' stylesheet at display `scale` (physical pixels, trap 98)."""
    values = dict(tokens or T)
    values.update(stack=STACK, select="#5a3922",
                  b1=hubstyle.px(1, scale), r4=hubstyle.px(4, scale),
                  r5=hubstyle.px(5, scale), p3=hubstyle.px(3, scale),
                  p10=hubstyle.px(10, scale))
    return _SHEET.format(**values).strip() + "\n"


#  Maya fills some of its own widgets from a palette of their own, which ours does
#  not reach - read live 2026-10-17: the Attribute Editor's body #444444, the Layer
#  Editor's rows #2b2b2b. Only these exact colours are swapped (a blanket background
#  rule emptied the hub's fields once, trap 98).
FILLS = {"#444444": T["panel"], "#2b2b2b": T["track"], "#5d5d5d": T["card"]}
#  given back to Maya's own dock, the forms take Maya's colours back
BACK = dict((ours, maya) for maya, ours in FILLS.items())


def recolor(widget, QtGui, back=False):           # noqa: N803
    """Maya's own filled backgrounds under `widget` swapped for ours. Run again
    whenever Maya builds new widgets there (the Attribute Editor on a new node).
    Returns how many were swapped."""
    import maya_hubqt as hubqt
    QWidget = hubqt.qt().QtWidgets.QWidget
    swapped = 0
    roles = QtGui.QPalette.ColorRole
    looked = [getattr(roles, name) for name in ("Window", "Button", "Base", "AlternateBase")]
    for child in [widget] + widget.findChildren(QWidget):
        try:
            pal = child.palette()
            changed = False
            for role in looked:
                new = (BACK if back else FILLS).get(pal.color(role).name())
                if new is not None:
                    pal.setColor(role, QtGui.QColor(new))
                    changed = True
            if changed:
                child.setPalette(pal)
                swapped += 1
        except RuntimeError:
            pass
    return swapped


CHANNEL_BOX = "mainChannelBox"
#  the Channel Box's own colour flags (2026-10-17, live: its rows were Maya's grey
#  whatever the palette): its empty area and its attribute rows. Its node and
#  section rows (#444444) come from its C++ model and keep Maya's grey.
CHANNEL_COLOURS = {"backgroundColor": T["panel"], "attrBgColor": T["card"]}
#  what Maya's Channel Box draws without them, put back in Maya's mode
CHANNEL_DEFAULTS = {"backgroundColor": "#444444", "attrBgColor": "#444444"}


def _rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def channel_box(on):
    """The Channel Box's own colour flags: ours (`on`), or Maya's again."""
    try:
        import maya.cmds as cmds
        if not cmds.channelBox(CHANNEL_BOX, exists=True):
            return False
        colours = CHANNEL_COLOURS if on else CHANNEL_DEFAULTS
        for flag, colour in colours.items():
            cmds.channelBox(CHANNEL_BOX, edit=True, **{flag: _rgb(colour)})
        return True
    except Exception:                                        # noqa: BLE001
        return False


def apply(widget, QtGui, scale=1.0):              # noqa: N803
    """`widget` (the panel's page stack) and everything in it in our colours."""
    import maya_mayatheme
    widget.setObjectName(STACK)
    widget.setPalette(maya_mayatheme.palette(QtGui))
    widget.setAutoFillBackground(True)
    widget.setStyleSheet(sheet(scale))
    recolor(widget, QtGui)

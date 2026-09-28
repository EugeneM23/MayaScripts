"""maya_hubstyle - the SkeldarAnim hub's look: palette, groups, stylesheet, marks.

The animator's ask (2026-09-28): «нарисовать кастомный красивый интерфейс ...
подумать над тем как сделать расположение кнопок более красивым». Picked in
the brainstorm: style B (our own dark charcoal, rounded cards, one orange
primary action per section, the palette as dots) and scheme 3 (the accordion
grouped into Scene / Animation / Look, a strip of icons that jumps to a
section).

This module is the look as DATA, stdlib only: the tokens, the groups, the
whole Qt stylesheet as text, and the marks -- a builder says what a control
IS (`mark(cmds.button(...), "primary", "plus")`) and the Qt layer
(`maya_hubqt`) turns that into a property the stylesheet selects on. A mark
costs nothing when the hub is built classic; the hub takes and drops them.

Two measured facts shape the stylesheet (2026-09-28, a probe window):

- no blanket descendant rules: `QFrame[skCard] QWidget {background:
  transparent}` outranked `QPushButton[skRole=primary]` and emptied every
  field and the primary button;
- no `QLabel` background: the colour slider's swatch
  (`QmayaColorSliderLabel`) is a QLabel and went invisible.

Pixels are PHYSICAL in Maya's Qt here (devicePixelRatio 1.0, logical DPI 144
on a 150 % display, the UI font 16 px), so every px is scaled by the display
factor Maya reports (`stylesheet(scale)`).

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import collections

# ------------------------------------------------------------------ tokens

TOKENS = {
    "panel": "#1f2023",         # the hub's background
    "card": "#2a2c30",          # a section card
    #  the card being worked in (2026-09-28); brighter the same evening
    #  («выделение активной панели должно быть ярче»): a lighter face and
    #  the accent itself as its outline
    "card_active": "#383a41",
    "card_edge": "#e07a36",
    "field": "#1b1c1f",         # fields, lists, segment tracks
    "field_hover": "#232428",
    "line": "#45474d",          # outlines, the checked segment
    "hover": "#34363b",
    "strip": "#17181a",         # the jump strip's track
    "text": "#e4e4e6",
    "text2": "#c9cacf",
    "muted": "#9a9ca3",
    "faint": "#77797f",
    "accent": "#e07a36",        # the one primary action per section
    "accent_hover": "#ea8a48",
    "on_accent": "#2a1405",
    "accent_tint": "#3a2a1f",
    "accent_text": "#f0a26b",
    "danger": "#e39a93",
    "danger_tint": "#3a2626",
    "status": "#24262a",
    "status_text": "#a9abb1",
    "ok": "#8fd19a",
    "ok_tint": "#223326",
}

#  The objectNames the stylesheet scopes by (hubqt names its widgets so).
ROOT = "skeldarAnimHubRoot"
CONTENT = "skeldarHubContent"
VIEWPORT = "skeldarHubViewport"
SCROLL = "skeldarHubScrollArea"

# ------------------------------------------------------------------ groups

Group = collections.namedtuple("Group", "key label colour chip")

#  Scene orange, Animation blue, Look violet: the icon's colour and the chip
#  behind it. Settings (hotkeys, update) lives in the header of the skin.
GROUPS = (
    Group("scene", "Scene", "#f0a26b", "#4a3322"),
    Group("animation", "Animation", "#7fa9e6", "#23324a"),
    Group("look", "Look", "#c89be8", "#3a2a4a"),
    Group("settings", "Settings", "#9a9ca3", "#2d2f34"),
)

_GROUPS = dict((g.key, g) for g in GROUPS)


def group(key):
    return _GROUPS.get(key)


# ------------------------------------------------------------------- marks

#  What a builder may say a control IS.
ROLES = (
    "primary",      # the section's one main action: orange
    "secondary",    # an ordinary button that carries an icon
    "danger",       # a destructive action: red text
    "tool",         # a small square icon button beside a field
    "chip",         # a checkBox drawn as a pill, lit when on
    "segments",     # a row layout holding segments (layout=True)
    "segment",      # an iconTextRadioButton inside `segments`
    "status",       # the section's status line
    "note",         # a one-line hint
    "context",      # a line of scene context inside the body
    "subtitle",     # a line the skin moves into the card's header
    "swatch",       # a colour chip (see swatch())
    "swatchonly",   # a colorSliderGrp showing only its swatch
)

Mark = collections.namedtuple("Mark", "name role icon layout colour")

_MARKS = []


def mark(name, role, icon=None, layout=False):
    """Record that control `name` plays `role`; return `name`, so a creation
    call can be wrapped in place."""
    if role not in ROLES:
        raise ValueError("unknown hub role '{0}'".format(role))
    _MARKS.append(Mark(name, role, icon, bool(layout), None))
    return name


def swatch(name, rgb):
    """Record a colour chip: a button the skin paints `rgb`, rounded."""
    _MARKS.append(Mark(name, "swatch", None, False, hex_of(rgb)))
    return name


def take_marks():
    """The marks recorded since the last call, in order; the list is cleared."""
    out = list(_MARKS)
    del _MARKS[:]
    return out


#  Whether the build running now is the skin's. A builder lays out ONE
#  arrangement for both hubs; the few things that differ -- a tool button
#  is an icon in the skin and a word in the classic hub, the skin's card
#  already has margins -- ask `pick`. Set by maya_hub around a skinned build.
_SKINNING = [False]


def set_skinning(on):
    _SKINNING[0] = bool(on)


def skinning():
    return _SKINNING[0]


def pick(skin, classic):
    """`skin` while the skin is being built, `classic` otherwise."""
    return skin if _SKINNING[0] else classic


def tool_label(text):
    """A tool button's label: none in the skin (its icon says it)."""
    return pick("", text)


def tool_width(classic):
    """A tool button's width: an icon's in the skin, the word's otherwise."""
    return pick(30, classic)


# -------------------------------------------------------------------- pure

def hex_of(rgb):
    """(r, g, b) in 0..1 -> "#rrggbb", clamped."""
    parts = []
    for value in list(rgb)[:3]:
        value = min(1.0, max(0.0, float(value)))
        parts.append("%02x" % int(round(value * 255)))
    return "#" + "".join(parts)


def px(value, scale):
    """`value` logical pixels at display `scale`, never rounding a line away."""
    if value <= 0:
        return 0
    return max(1, int(value * scale + 0.5))


_SHEET = """
#{ROOT} {{ background: {panel}; }}
#{CONTENT}, #{VIEWPORT} {{ background: {panel}; }}
QScrollArea#{SCROLL} {{ background: {panel}; border: none; }}
QFrame[skCard="true"] {{ background: {card}; border-radius: {r8}px;
    border: {p2}px solid {card}; }}
QFrame[skCard="true"][skActive="true"] {{ background: {card_active};
    border: {p2}px solid {card_edge}; }}

QPushButton {{ background: transparent; border: {b1}px solid {line};
    border-radius: {r6}px; padding: {p3}px {p8}px; color: {text2}; }}
QPushButton:hover {{ background: {hover}; color: {text}; }}
QPushButton:pressed {{ background: {field}; }}
QPushButton:disabled {{ color: {faint}; border-color: {hover}; }}
QPushButton[skRole="primary"] {{ background: {accent}; border: none;
    color: {on_accent}; font-weight: bold; }}
QPushButton[skRole="primary"]:hover {{ background: {accent_hover}; }}
QPushButton[skRole="primary"]:pressed {{ background: {accent}; }}
QPushButton[skRole="danger"] {{ color: {danger}; }}
QPushButton[skRole="danger"]:hover {{ background: {danger_tint}; }}
QPushButton[skRole="tool"] {{ background: {field}; border: none;
    padding: {p3}px; }}
QPushButton[skRole="tool"]:hover {{ background: {hover}; }}
QWidget[skRole="segments"] {{ background: {field}; border-radius: {r6}px; }}
QPushButton[skRole="segment"] {{ background: transparent; border: none;
    border-radius: {r4}px; padding: {p2}px {p6}px; color: {muted}; }}
QPushButton[skRole="segment"]:hover {{ color: {text}; }}
QPushButton[skRole="segment"]:checked {{ background: {line}; color: {text}; }}

QComboBox {{ background: {field}; border: none; border-radius: {r6}px;
    padding: {p3}px {p8}px; color: {text}; }}
QComboBox:hover {{ background: {field_hover}; }}
QComboBox QAbstractItemView {{ background: {card}; color: {text};
    border: {b1}px solid {line}; selection-background-color: {accent_tint};
    selection-color: {accent_text}; }}
QLineEdit {{ background: {field}; border: {b1}px solid {field};
    border-radius: {r6}px; padding: {p2}px {p6}px; color: {text};
    selection-background-color: {accent_tint}; }}
QLineEdit:focus {{ border: {b1}px solid {accent}; }}
QListWidget {{ background: {field}; border: none; border-radius: {r6}px;
    color: {text2}; padding: {p2}px; }}
QListWidget::item:selected {{ background: {accent_tint}; color: {accent_text}; }}
QListWidget::item:hover {{ background: {field_hover}; }}

QCheckBox {{ color: {text2}; spacing: {p6}px; }}
QCheckBox::indicator {{ width: {p13}px; height: {p13}px; border-radius: {r3}px;
    background: {field}; border: {b1}px solid {line}; }}
QCheckBox::indicator:checked {{ background: {accent}; border: {b1}px solid {accent}; }}
QCheckBox[skRole="chip"] {{ background: {field}; border-radius: {r10}px;
    padding: {p3}px {p10}px; color: {muted}; }}
QCheckBox[skRole="chip"]:hover {{ color: {text}; }}
QCheckBox[skRole="chip"]:checked {{ background: {accent_tint}; color: {accent_text}; }}
QCheckBox[skRole="chip"]::indicator {{ width: 0px; height: 0px; border: none;
    background: transparent; margin: 0px; }}
QRadioButton {{ color: {text2}; }}
QSlider::groove:horizontal {{ height: {p4}px; background: {field};
    border-radius: {r2}px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: {r2}px; }}
QSlider::handle:horizontal {{ background: {text}; width: {p12}px;
    height: {p12}px; margin: -{p4}px 0px; border-radius: {r6}px; }}

QPushButton[skRole="secondary"] {{ color: {text2}; }}
QLabel[skRole="status"] {{ color: {status_text}; padding: {p2}px {p2}px; }}
QLabel[skRole="note"] {{ color: {muted}; }}
QLabel[skRole="context"] {{ color: {muted}; }}
QLabel[skRole="subtitle"] {{ color: {muted}; font-size: {small}px; }}

QScrollBar:vertical {{ background: transparent; width: {p8}px; margin: 0px; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: {r4}px;
    min-height: {p24}px; }}
QScrollBar:horizontal {{ background: transparent; height: {p8}px; margin: 0px; }}
QScrollBar::handle:horizontal {{ background: {line}; border-radius: {r4}px;
    min-width: {p24}px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ background: {card}; color: {text}; border: {b1}px solid {line};
    padding: {p4}px; }}
QMenu {{ background: {card}; color: {text}; border: {b1}px solid {line};
    padding: {p4}px; }}
QMenu::item {{ padding: {p4}px {p16}px; border-radius: {r4}px; }}
QMenu::item:selected {{ background: {accent_tint}; color: {accent_text}; }}
QMenu::separator {{ height: {b1}px; background: {line}; margin: {p4}px {p8}px; }}

QLabel[skRole="logo"] {{ background: {accent}; color: {on_accent};
    border-radius: {r5}px; font-weight: bold; }}
QLabel[skRole="hubtitle"] {{ color: {text}; font-weight: bold; }}
QToolButton[skRole="headbtn"] {{ background: transparent; border: none;
    border-radius: {r6}px; padding: {p3}px; }}
QToolButton[skRole="headbtn"]:hover {{ background: {card}; }}
QToolButton[skRole="headbtn"]:checked {{ background: {accent_tint}; }}
QToolButton[skRole="headbtn"]::menu-indicator {{ image: none; width: 0px; }}
QToolButton[skRole="version"] {{ background: {card}; border: none;
    border-radius: {r9}px; padding: {p2}px {p8}px; color: {muted};
    font-size: {small}px; }}
QToolButton[skRole="version"]:hover {{ background: {hover}; color: {text}; }}
QToolButton[skRole="version"][skState="ok"] {{ background: {ok_tint}; color: {ok}; }}
QToolButton[skRole="version"][skState="new"] {{ background: {accent_tint};
    color: {accent_text}; }}
QWidget[skRole="message"] {{ background: {status}; border-radius: {r6}px; }}
QLabel[skRole="messagetext"] {{ color: {status_text}; }}
QWidget[skRole="strip"] {{ background: {strip}; border-radius: {r7}px; }}
QToolButton[skRole="jump"] {{ background: transparent; border: none;
    border-radius: {r5}px; padding: {p3}px; }}
QToolButton[skRole="jump"]:hover {{ background: {card}; }}
QLabel[skRole="grouplabel"] {{ color: {muted}; font-size: {small}px; }}
QLabel[skRole="cardtitle"] {{ color: {text}; font-weight: bold; }}
"""


def stylesheet(scale=1.0, tokens=None, arrow=None):
    """The hub's whole Qt stylesheet at display `scale`. `arrow` is a file
    (an SVG the Qt layer writes) drawn as every dropdown's arrow."""
    values = dict(TOKENS)
    values.update(tokens or {})
    values.update(ROOT=ROOT, CONTENT=CONTENT, VIEWPORT=VIEWPORT,
                  SCROLL=SCROLL)
    for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 16, 24):
        values["p%d" % n] = px(n, scale)
        values["r%d" % n] = px(n, scale)
    values["b1"] = px(1, scale)
    values["small"] = px(9.5, scale)     # the UI font is ~10.7 logical
    sheet = _SHEET.format(**values).strip() + "\n"
    if arrow:
        sheet += ("QComboBox::drop-down {{ border: none; width: {0}px; }}\n"
                  "QComboBox::down-arrow {{ image: url({1}); width: {2}px; "
                  "height: {2}px; }}\n").format(px(18, scale),
                                                arrow.replace("\\", "/"),
                                                px(11, scale))
    return sheet

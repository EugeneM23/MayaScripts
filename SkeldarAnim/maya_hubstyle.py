"""maya_hubstyle - the SkeldarAnim hub's look: palette, groups, stylesheet, marks.

The animator's ask (2026-09-28): «нарисовать кастомный красивый интерфейс ...
подумать над тем как сделать расположение кнопок более красивым». Picked in
the brainstorm: style B (our own dark charcoal, rounded cards, one orange
primary action per section, the palette as dots) and scheme 3 (the accordion
grouped into Scene / Animation / Look, a strip of icons that jumps to a
section).

2026-10-08: compact (variant B) - H, the status relay, the list rows; spec
docs/superpowers/specs/2026-10-08-hub-compact-and-edge-panel-design.md

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

import maya_hubcopy

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
    #  a block set into a card (2026-10-02: Connect, the source of the
    #  animations): a step darker than the card, a hairline round it
    "inset": "#232529",
    "inset_line": "#3a3c42",
}

#  The objectNames the stylesheet scopes by (hubqt names its widgets so).
ROOT = "skeldarAnimHubRoot"
#  a section's popup window's root: "skeldarAnimPopupRoot_<tag>" (maya_hubpop,
#  2026-10-09) - matched by prefix
POPUP_ROOT = "skeldarAnimPopupRoot"
HUB_CONTROL = "skeldarAnimHub"          # maya_hub.CONTROL, the workspaceControl
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
    "heading",      # a section's title inside a card (2026-10-01: «UE Connect»)
    "inset",        # a column set into the card as its own block (layout=True;
                    # 2026-10-02: Connect «визуально как-то отделить»)
    "swatch",       # a colour chip (see swatch())
    "swatchonly",   # a colorSliderGrp showing only its swatch
    "grip",         # a placeholder under a list the skin turns into a height grip (2026-10-08)
    "dot",          # a one-glyph state mark (● / ○) before a dropdown (2026-10-08)
    "flow",         # a flowLayout whose wrapped lines the skin keeps in its
                    # height (layout=True; live 2026-10-08: Maya kept one line's)
)

Mark = collections.namedtuple("Mark", "name role icon layout colour target",
                              defaults=(None,))

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


def grip(name, list_name):
    """Record that placeholder `name` (8 px under a list) is that list's
    height grip (2026-10-08, «нужно сделать возможность раздвигать или
    сдвигать окошко по высоте»); the skin draws and drives it."""
    _MARKS.append(Mark(name, "grip", None, False, None, list_name))
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


# ------------------------------------------------------------- compact (B)

#  The compact skin (2026-10-08, «сделаем его компактным»; variant B of the
#  brainstorm): the builders' control heights, logical px. The classic hub
#  keeps the numbers each builder passes as `classic`.
H = {"button": 24, "small": 22, "segment": 22, "field": 20}


def height(kind, classic):
    """A control's height: the compact one in the skin, `classic` otherwise."""
    return pick(H[kind], classic)


def row_spacing(classic=6):
    """A builder's column rowSpacing: 3 in the skin, `classic` otherwise."""
    return pick(3, classic)


# -------------------------------------------------------- the status relay

#  One message line for the whole hub (2026-10-08): a section's status writer
#  still writes its own control, and `tell`s the hub too. The skin listens
#  (maya_hubqt.Skin) and shows the text on its line with the card's icon; the
#  classic hub listens to nothing and keeps the status lines in the cards.
_LISTENERS = []


def listen(fn):
    """`fn(control, text, viewport)` is called by every `tell`; returns fn."""
    if fn not in _LISTENERS:
        _LISTENERS.append(fn)
    return fn


def unlisten(fn):
    if fn in _LISTENERS:
        _LISTENERS.remove(fn)


def tell(control, text, viewport=False):
    """Section status control `control` now says `text`. `viewport`: the
    writer shows it in the viewport itself (an inViewMessage), so the edge
    panel need not. Never raises; answers `text`.

    Inside a section popup (2026-10-09) the control is the copy's own, and
    its name is what the listeners get - so a copy's line is not the hub's
    card's (the hub's relay matches by name)."""
    control = maya_hubcopy.resolve(control)
    for fn in list(_LISTENERS):
        try:
            fn(control, text, viewport)
        except Exception:                                    # noqa: BLE001
            pass
    return text


# --------------------------------------------------------------- the lists

#  The file lists (the animations, Shared): 10 rows by default, 5..40 by the
#  grip, remembered per list (2026-10-08, «хотя бы 10 ... раздвигать или
#  сдвигать окошко по высоте»).
LIST_VAR = "skeldarAnimHub_listRows_{0}"
LIST_ROWS = 10
LIST_MIN = 5
LIST_MAX = 40


def clamp_rows(rows):
    return int(max(LIST_MIN, min(LIST_MAX, int(round(rows)))))


def rows_after_drag(start_rows, dy, row_px):
    """The rows a list shows after the grip moved `dy` px from where the
    press found it showing `start_rows`, whole rows, clamped. Pure."""
    if not row_px or row_px <= 0:
        return clamp_rows(start_rows)
    return clamp_rows(start_rows + float(dy) / float(row_px))


def list_height(rows, row_px, frame_px):
    """A list's height showing `rows` rows of `row_px`, plus its frame."""
    return int(round(rows * row_px + frame_px))


# --------------------------------------------------------------- the light

#  The lit card (2026-10-01, «красивый глоу и анимацию подсветки»): its face
#  card_active and its 2 px ring card_edge as before (the stylesheet switched
#  them at once; the card paints them now, fading -- maya_hubqt.paint_light),
#  plus an INNER glow `width` logical px deep inward from the ring, the accent
#  at `alpha` at the edge falling off as (1 - depth)^2. A flash (the card just
#  chosen) adds `flash_alpha`, falling off linearly, and deepens the glow by
#  `flash_widen`. Drawn as rings ONE PHYSICAL PIXEL wide: wider ones showed
#  as bands (photographed live at 150 %).
GLOW = {
    "width": 10.0,
    "alpha": 0.28,
    "flash_alpha": 0.30,
    "flash_widen": 0.6,
}


#  A control under the mouse (2026-10-02, «все надпись немного подсвечивались
#  легким свечением когда мы наводим на них мышкой»; prototype A, the glow in
#  the text's own colour): its ink - luminance above its face by `lo`, fully
#  by `lo + span` - blurred `radius` logical px, x `gain`, taken off the ink
#  itself, added at `strength`. The orange primary button (dark letters on a
#  lit face) gets a `rim` inside its edge instead, `rim_depth` px deep.
#  maya_hubglow is the arithmetic, maya_hubqt.HoverGlow the drawing.
HOVER_GLOW = {
    "lo": 25.0,
    "span": 70.0,
    "radius": 5.0,
    "gain": 2.2,
    "strength": 0.42,
    "rim": "#fff1e2",
    "rim_strength": 0.38,
    "rim_depth": 6.0,
}


def glow_rings(level, flash, scale=1.0):
    """The inner glow at `level` (0..1) and `flash` (0..1) at the display's
    `scale`: [(inset, width, alpha)] in logical px from the inside of the
    ring, outermost first, each one physical px wide."""
    scale = float(scale or 1.0)
    depth = GLOW["width"] * (1.0 + GLOW["flash_widen"] * flash)
    steps = max(1, int(round(depth * scale)))
    width = 1.0 / scale
    rings = []
    for i in range(steps):
        fall = 1.0 - i / float(steps)
        alpha = (level * GLOW["alpha"] * fall * fall
                 + flash * GLOW["flash_alpha"] * fall)
        rings.append((i * width, width, min(1.0, alpha)))
    return rings


def mix(a, b, k):
    """Colour `k` (clamped 0..1) of the way from "#rrggbb" `a` to `b`."""
    k = min(1.0, max(0.0, float(k)))
    parts = []
    for i in (1, 3, 5):
        x, y = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        parts.append(int(round(x + (y - x) * k)))
    return "#{0:02x}{1:02x}{2:02x}".format(*parts)


# -------------------------------------------------------------------- pure

def hex_of(rgb):
    """(r, g, b) in 0..1 -> "#rrggbb", clamped."""
    parts = []
    for value in list(rgb)[:3]:
        value = min(1.0, max(0.0, float(value)))
        parts.append("%02x" % int(round(value * 255)))
    return "#" + "".join(parts)


def over_hub(names, control=HUB_CONTROL):
    """Whether a point whose widget ancestry carries `names` (objectNames,
    innermost first) lies on the hub itself - or on one of its section popups
    (2026-10-09, `POPUP_ROOT`): a drag released there does nothing
    (maya_hubqt.on_hub)."""
    return any(name in (ROOT, control) or name.startswith(POPUP_ROOT)
               for name in names or ())


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

QPushButton {{ background: transparent; border: {b1}px solid {line};
    border-radius: {r6}px; padding: {p2}px {p6}px; color: {text2}; }}
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
QWidget[skRole="inset"] {{ background: {inset}; border: {b1}px solid {inset_line};
    border-radius: {r8}px; }}
QPushButton[skRole="segment"] {{ background: transparent; border: none;
    border-radius: {r4}px; padding: {p2}px {p6}px; color: {muted}; }}
QPushButton[skRole="segment"]:hover {{ color: {text}; }}
QPushButton[skRole="segment"]:checked {{ background: {line}; color: {text}; }}

QComboBox {{ background: {field}; border: none; border-radius: {r6}px;
    padding: {p1}px {p6}px; color: {text}; }}
QComboBox:hover {{ background: {field_hover}; }}
QComboBox QAbstractItemView {{ background: {card}; color: {text};
    border: {b1}px solid {line}; selection-background-color: {accent_tint};
    selection-color: {accent_text}; }}
QLineEdit {{ background: {field}; border: {b1}px solid {field};
    border-radius: {r6}px; padding: {p1}px {p6}px; color: {text};
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
    padding: {p2}px {p8}px; color: {muted}; }}
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
QLabel[skRole="heading"] {{ color: {text}; font-weight: bold;
    padding: {p6}px 0px {p3}px 0px; border-bottom: {b1}px solid {line}; }}
QLabel[skRole="dot"] {{ color: {faint}; }}
QWidget[skRole="grip"] {{ background: transparent; border-radius: {r3}px; }}
QWidget[skRole="grip"]:hover {{ background: {hover}; }}
QLabel[skRole="messageicon"] {{ background: transparent; }}

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
    border-radius: {r6}px; padding: {p2}px; }}
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
    border-radius: {r5}px; padding: {p1}px; }}
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

"""The Time Bar's layer panel drawn offscreen frame by frame into timebar_layers.png
(2026-10-18): the real strip (with its layers pill lit) and the real column and lanes
on a fake link, at 150 %. Columns of frames: the column opening, at rest on Animation
(a hovered row, the lanes out), on Display, resized, closing; one more frame with a
foot button hovered (to look for a double image). Run:

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_timebar_layers.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt                                           # noqa: E402
import maya_hubstyle                                        # noqa: E402
from maya_timebar import bar, layerlook as L, layerpanel, look   # noqa: E402

QT = maya_hubqt.qt()
app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
    if os.path.exists(os.path.join(fonts, name)):
        QT.QtGui.QFontDatabase.addApplicationFont(os.path.join(fonts, name))
app.setFont(QT.QtGui.QFont("Segoe UI", 9))

UI = 1.5
STRIP_W, STRIP_H = 1500, int(84 * UI)
Y0 = 900                                  # the strip's virtual global top


# -- the fake links (copied from the tests: scripts do not import tests) ---------------

class PanelLink(object):

    def __init__(self):
        self.log = []
        self.opts = {}
        self.anim = [{"name": "Base", "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                      "weight_keyed": False, "mute": False, "solo": False, "lock": False,
                      "active": False, "base": True}]
        modes = ("add", "ovr")
        for i in range(8):
            self.anim.insert(0, {"name": "L%d" % i, "label": "Layer_%d" % (i + 1), "mode": modes[i % 2],
                                 "weight": [1.0, 0.65, 0.3, 1.0][i % 4], "weight_keyed": i == 2,
                                 "mute": i == 3, "solo": i == 5, "lock": i == 6,
                                 "active": i == 1, "base": False})
        #  the layers the selection belongs to: their names read green (2026-10-29)
        self.members = ["L1", "L3", "Base"]
        self.display_members = ["d1"]
        self.disp = [{"name": "d%d" % i, "label": "display_%d" % (i + 1),
                      "colour": ["#7fa9e6", "#e6a97f", "#8fd48f", "#d98fd9"][i], "visible": i != 2,
                      "playback": True, "type": i % 3} for i in range(4)]

    def _w(self, *entry):
        self.log.append(entry)
        return True, ""

    def anim_layers(self):
        return [dict(r) for r in self.anim]

    def display_layers(self):
        return [dict(r) for r in self.disp]

    def keys_by_layer(self, names):
        return {n: [float(f) for f in range(0, 95, 5 + (i % 4))] for i, n in enumerate(names)}

    def members_of(self, names):
        return [n for n in names if n in self.members]

    def display_members_of(self, names):
        return [n for n in names if n in self.display_members]

    def option(self, name, default):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def __getattr__(self, name):
        return lambda *a: self._w(name, *a)


class StripLink(object):
    """What the real strip asks of its link."""

    def __init__(self):
        self.s = {"now": 30.0, "a0": 0.0, "a1": 100.0, "p0": 0.0, "p1": 95.0, "unit": "ntsc",
                  "auto": True, "playing": False, "highlight": None}
        self.x = {"loop": "continuous", "speed": 1.0, "cache": True, "sound": "", "sound_shown": False,
                  "character": ""}
        self.k = ([0.0, 6.0, 12.0, 30.0, 40.0, 72.0], [9.0])

    def light(self):
        return dict(self.s)

    def extra(self):
        return dict(self.x)

    def keys(self):
        return self.k

    def bookmarks(self):
        return []

    def waveform(self, node, a, b):
        return []

    def now(self):
        return self.s["now"]

    def layer_state(self):
        return "Layer_2", 9

    def layer_link(self):
        return PanelLink()

    def layers(self):
        return [("Base", "BaseAnimation", False)]

    def layer_label(self):
        return "Layer_2"

    def sounds(self):
        return []

    def character_sets(self):
        return []

    def __getattr__(self, name):
        return lambda *a: None


class FakeStrip(object):
    """What the panel asks of the strip, over the real one standing at (0, Y0)."""

    def __init__(self, strip):
        self.strip = strip
        self.ui = UI

    def strip_rect(self):
        return (0, Y0, self.strip.width(), self.strip.height())

    def timeline_rect(self):
        t = self.strip.timeline
        p = t.mapTo(self.strip, t.rect().topLeft())
        return (p.x(), Y0 + p.y(), t.width(), t.height())

    def top_room(self):
        return Y0 - 20

    def track(self):
        return self.strip.timeline.track()

    def now(self):
        return 30.0


# -- drawing ---------------------------------------------------------------------------

strip = bar.make(StripLink(), UI, maya_hubstyle.TOKENS, motion=False)
strip.resize(STRIP_W, STRIP_H)
strip.move(4000, 4000)
strip.show()
app.processEvents()
fake = FakeStrip(strip)


def make(motion=False, opts=None):
    link = PanelLink()
    link.opts.update(opts or {})
    panel = layerpanel.Panel(fake, link, UI, maya_hubstyle.TOKENS, motion)
    panel.column.move(4000, 0)
    panel.lanes.move(4000, 0)
    return panel


def pill(on):
    strip.layers_btn.setChecked(on)
    strip.layers_btn.repaint()


def grab(widget):
    image = QT.QtGui.QImage(widget.size(), QT.QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    widget.render(image)
    return image


def frame(panel, label, lit=True, crop_left=None):
    """The column, the lanes if shown and the strip on one canvas, labelled."""
    pill(lit)
    col, lanes = panel.column, panel.lanes
    cg = col.geometry()
    top = min(cg.y(), Y0) - 6
    h = Y0 + STRIP_H - top + 6
    w = STRIP_W
    canvas = QT.QtGui.QImage(w, h + 22, QT.QtGui.QImage.Format_ARGB32)
    canvas.fill(QT.QtGui.QColor("#26272b"))
    p = QT.QtGui.QPainter(canvas)
    p.drawImage(0, Y0 - top + 22, grab(strip))
    if lanes.isVisible():
        p.drawImage(lanes.geometry().x(), lanes.geometry().y() - top + 22, grab(lanes))
    if col.isVisible() or panel.phase in ("opening", "closing"):
        p.drawImage(cg.x(), cg.y() - top + 22, grab(col))
    p.setPen(QT.QtGui.QColor("#e8e9ec"))
    p.setFont(QT.QtGui.QFont("Segoe UI", 10, QT.QtGui.QFont.Bold))
    p.drawText(8, 16, label)
    p.end()
    if crop_left is None:
        crop_left = max(0, cg.x() - 24)
    return canvas.copy(crop_left, 0, w - crop_left, canvas.height())


def hover(panel, part, i=0):
    """Hover a row's `part`, or ("foot", name) / ("tab", t)."""
    lay = panel.column.layout_()
    if part[0] == "row":
        rect = L.row_parts(lay.row_at(part[1], panel.scroll), lay.tab, lay.ui,
                           base=lay.bases[part[1]])[part[2]]
    elif part[0] == "foot":
        rect = dict(lay.foot)[part[1]]
    else:
        rect = lay.segments[part[1]]
    x, y = rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0
    panel.hover_at(L.hit(lay, x, y, panel.scroll))
    panel.column.repaint()


shots = []
origin = (1380, Y0 + STRIP_H // 2)

# 1. opening
for ms in (40, 120, 220, 400):
    panel = make(motion=True)
    panel.open(origin)
    panel.age_override = ms
    panel.column.repaint()
    panel.lanes.repaint()
    shots.append(("1", frame(panel, "opening %d ms" % ms)))
    panel.age_override = None
    panel.destroy()

# 2. at rest, Animation, a hovered row, the lanes out
panel = make(opts={layerpanel.LANES_VAR: 1})
panel.open(origin)
hover(panel, ("row", 2, "name"))
panel.lanes.repaint()
rest_lanes = frame(panel, "rest, Animation, row hovered, lanes out", crop_left=0)
shots.append(("2", frame(panel, "rest, Animation, row hovered, lanes out")))
panel.destroy()

panel = make()
panel.open(origin)
hover(panel, ("row", 3, "mute"))
shots.append(("2", frame(panel, "rest, Animation, mute hovered")))
panel.destroy()

# the double-image check: a foot button hovered, once with and once without
panel = make()
panel.open(origin)
hover(panel, ("foot", "add"))
shots.append(("2", frame(panel, "foot button hovered (+ Layer)")))
foot_hovered = panel.column
panel.destroy()

# 3. Display
panel = make(opts={layerpanel.TAB_VAR: "disp"})
panel.open(origin)
hover(panel, ("row", 1, "name"))
shots.append(("3", frame(panel, "Display, row hovered")))
panel.destroy()

# 4. resized
panel = make(opts={layerpanel.HEIGHT_VAR: 420})
panel.open(origin)
shots.append(("4", frame(panel, "resized to 420 px")))
panel.destroy()

# 5. closing
for ms in (60, 160, 300):
    panel = make(motion=True)
    panel.open(origin)
    panel.burst = None
    panel.phase = "open"
    panel.close(origin)
    panel.age_override = ms
    panel.column.repaint()
    shots.append(("5", frame(panel, "closing %d ms" % ms)))
    panel.age_override = None
    panel.destroy()

# -- the sheet: a column of frames per state -------------------------------------------
groups = {}
for g, img in shots:
    groups.setdefault(g, []).append(img)
GAP = 10
widths = [max(i.width() for i in v) for v in groups.values()]
heights = [sum(i.height() + GAP for i in v) for v in groups.values()]
sheet = QT.QtGui.QImage(sum(widths) + GAP * (len(widths) + 1), max(heights) + GAP + rest_lanes.height() + GAP,
                        QT.QtGui.QImage.Format_ARGB32)
sheet.fill(QT.QtGui.QColor("#101012"))
p = QT.QtGui.QPainter(sheet)
x = GAP
for (g, v), w in zip(groups.items(), widths):
    y = GAP
    for img in v:
        p.drawImage(x, y, img)
        y += img.height() + GAP
    x += w + GAP
p.drawImage(GAP, max(heights) + GAP, rest_lanes)
p.end()
out = os.path.join(HERE, "timebar_layers.png")
sheet.save(out)
print(out, sheet.width(), sheet.height())

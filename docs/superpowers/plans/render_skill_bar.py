"""The skill bar's filmstrip (2026-10-19): the Time Bar's strip offscreen at 150 % - F1, F2 at 2, 3
F2 (one row of 10 cells), F3 (characters), a page popping in from its tab, the library drawer over the bar.

    mayapy docs/superpowers/plans/render_skill_bar.py [out.png]

Writes docs/superpowers/plans/skill_bar.png by default. The model is the defaults, in memory; the
pictures and names are the real ones (maya_skillbar.run).
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt          # noqa: E402
import maya_hubstyle       # noqa: E402
from maya_skillbar import library, look, run, skills    # noqa: E402
from maya_timebar import bar                             # noqa: E402

UI = 1.5
WIDTH = 1500


class Link(object):
    """The strip's road with a still scene and the skill model in memory."""

    def __init__(self):
        self.model = skills.MemorySkills()
        for name in ("label", "tip", "tag", "short", "picture"):
            setattr(self.model, name, getattr(run, name))

    def skills(self):
        return self.model

    def light(self):
        return {"now": 24.0, "a0": 0.0, "a1": 120.0, "p0": 0.0, "p1": 96.0, "unit": "ntsc",
                "auto": True, "playing": False, "highlight": None}

    def extra(self):
        return {"loop": "continuous", "speed": 1.0, "cache": True, "sound": "", "sound_shown": False,
                "character": ""}

    def keys(self):
        return ([0.0, 12.0, 24.0, 40.0, 60.0, 72.0, 96.0], [30.0])

    def bookmarks(self):
        return []

    def now(self):
        return 24.0

    def layer_state(self):
        return ("BaseAnimation", 1)

    def __getattr__(self, name):
        return lambda *a, **k: None


def shot(widget, background="#202124"):
    q = maya_hubqt.qt()
    image = q.QtGui.QImage(widget.size(), q.QtGui.QImage.Format_ARGB32)
    image.fill(q.QtGui.QColor(background))
    widget.render(image)
    return image


def main(out):
    q = maya_hubqt.qt()
    app = q.QtWidgets.QApplication.instance() or q.QtWidgets.QApplication([])
    for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "consolab.ttf"):
        q.QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    app.setFont(q.QtGui.QFont("Segoe UI"))
    link = Link()
    strip = bar.make(link, UI, maya_hubstyle.TOKENS, motion=True)
    strip.resize(WIDTH, 10)
    strip.move(0, 900)
    strip.show()
    app.processEvents()
    shots = []

    def settle():
        strip.resize(WIDTH, strip.sizeHint().height())
        app.processEvents()

    def take(title):
        strip.skill_grid.pop = None
        strip.entrance = None
        strip.opened -= 10000
        settle()
        shots.append((title, shot(strip)))

    take("F1 - the Time Bar")
    strip.show_page(2)
    take("F2 Animate - 10 cells, as tall as the time rows")
    strip.show_page(3)
    take("F3 Characters")
    strip.show_page(2)
    settle()
    for age in (90, 200, 320):
        strip.skill_grid.pop["t0"] = strip.clock() - age
        shots.append(("F2 popping in from its tab, %d ms" % age, shot(strip)))
    strip.skill_grid.pop = None
    strip.show_page(6)
    settle()
    drawer = library.make(strip, ("cell", 6, 0, 0), None, motion=False,
                          entries=lambda cat, search="": [e for e in _entries() if cat == "All" or e[0] == cat])
    drawer.open()
    app.processEvents()
    shots.append(("The skill library over F6", shot(drawer, "#2a2c31")))
    strip.skill_grid.pop = None
    shots.append(("F6, empty: a click opens the library", shot(strip)))
    # the sheet
    gap, title_h = int(10 * UI), int(18 * UI)
    height = sum(i.height() + gap + title_h for _t, i in shots)
    sheet = q.QtGui.QImage(WIDTH, height, q.QtGui.QImage.Format_ARGB32)
    sheet.fill(q.QtGui.QColor("#121315"))
    p = q.QtGui.QPainter(sheet)
    font = q.QtGui.QFont("Segoe UI")
    font.setPixelSize(int(12 * UI))
    p.setFont(font)
    y = 0
    for title, image in shots:
        p.setPen(q.QtGui.QColor("#9a9ea8"))
        p.drawText(int(8 * UI), y + int(13 * UI), title)
        y += title_h
        p.drawImage(0, y, image)
        y += image.height() + gap
    p.end()
    sheet.save(out)
    print("wrote %s (%d shots)" % (out, len(shots)))


def _entries():
    found = []
    for item in look.DEFAULT_PAGES[2][1] + look.DEFAULT_PAGES[3][1]:
        found.append(("Tools" if item["kind"] == "cmd" else
                      "Sections" if item["kind"] == "section" else "Characters", item, run.label(item)))
    found.append(("Maya", {"kind": "maya", "command": "GraphEditor"}, "GraphEditor"))
    found.append(("Scripts", {"kind": "script", "lang": "python", "code": "# Mirror pose\npass"},
                  "Mirror pose"))
    return found


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "skill_bar.png"))

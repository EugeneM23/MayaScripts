"""verify_hub_motion.py - the hub's cards slide, a jump glides: live.

Run in a DISPOSABLE Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME) on the REPO's
hub, sent through its command port after the hub was rebuilt from the repo.
The animations need a real clock: the send turns the event loop itself
(QApplication.processEvents + maya.utils.processIdleEvents + 4 ms sleeps),
recording per turn what the animator would see.

    1  every card opened and shut through real time: the height per turn
       monotonic, the body's first child never resized (clipped, never
       squeezed), the end on the settled height (no jump), the layout
       enabled and the cap gone; the cost of a turn
    2  a slide turned back mid-way: no jump where it turns, ends shut
    3  a jump (maya_hub.focus) with three cards open above: they shut, the
       chosen one opens, the bar glides (several steps, monotonic) and ends
       on the card's place
    4  Interface animations off: a click and a jump are instant; back on
    5  photographs of a card sliding open (one strip, four moments)

UI only: no scene node is touched. The switch's optionVar is put back.

Spec: docs/superpowers/specs/2026-10-01-hub-card-motion-design.md
"""
import os
import time

import maya.cmds as cmds
import maya.utils

import maya_hub
import maya_hubmotion
import maya_hubqt

FAILED = []
PASSED = []
OUT = os.environ.get("SKELDAR_VERIFY_OUT", os.path.dirname(os.path.abspath(
    globals().get("__file__", "."))))


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2s %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


q = maya_hubqt.qt()
app = q.QtWidgets.QApplication.instance()
skin = maya_hub._SKIN
assert skin is not None and skin.alive(), "no skinned hub"
COST = []          # (ms, phase, moving) per turn of the loop
PHASE = ["cards"]


def moving():
    return skin._glide is not None or any(
        c.sliding() for c in skin.cards.values())


def turn():
    was = moving()
    t0 = time.perf_counter()
    app.processEvents()
    t1 = time.perf_counter()
    maya.utils.processIdleEvents()
    t2 = time.perf_counter()
    COST.append(((t1 - t0) * 1000.0, (t2 - t1) * 1000.0, PHASE[0],
                 was or moving()))


def run(until, timeout=1.5, record=None):
    """Turn the loop until `until()` (then a few more turns to settle);
    `record()` after every turn."""
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        turn()
        if record:
            record()
        if until():
            break
        time.sleep(0.004)
    for _ in range(6):
        turn()


def settle():
    for _ in range(8):
        turn()


def first_child(card):
    for child in card.body.children():
        if isinstance(child, q.QtWidgets.QWidget) and not child.isWindow():
            return child
    return None


def monotonic(values, rising):
    pairs = zip(values, values[1:])
    return all((b >= a) if rising else (b <= a) for a, b in pairs)


saved_switch = maya_hubmotion.enabled()
maya_hub.set_animations(True)
for card in skin.cards.values():
    card.set_collapsed(True)
settle()
print("viewport", skin.scroll.viewport().width(), "cards", len(skin.cards))

# --------------------------------------------------------------- 1 per card
rows = []
steady = {}         # key -> the header heights seen while it slid
for key, card in skin.cards.items():
    heights, kids = [], []
    PHASE[0] = key
    child = first_child(card)

    def rec(card=card, child=child, heights=heights, kids=kids):
        if card.sliding():
            heights.append(card._shown)
            steady.setdefault(card.key, set()).add(card.header.height())
            if child is not None and card._laid:
                kids.append((child.height(), card._laid[1], card._shown))

    card.toggle()                                          # open
    started = card.sliding()
    run(lambda card=card: not card.sliding(), record=rec)
    settled = card.body.height()
    natural = card.natural_height()
    last = heights[-1] if heights else None
    open_ok = (started and len(heights) >= 3 and monotonic(heights, True)
               and last == settled == natural
               and card.body_layout.isEnabled()
               and card.body.maximumHeight() == maya_hubqt._NO_CAP)
    #  every turn the content stands at its FULL height (the body's top
    #  margin above it) and the body shows less of it: clipped, not squeezed.
    #  The full height itself may move a few px when the scroll bar comes
    #  and the Characters / Weapons grids reflow to the new width.
    top = card.body_layout.contentsMargins().top()
    clipped = (bool(kids) and all(c + top == full for c, full, _s in kids)
               and any(s < c for c, _full, s in kids))
    reflow = (max(f for _c, f, _s in kids) - min(f for _c, f, _s in kids)
              if kids else 0)
    down = []

    def rec2(card=card, down=down):
        if card.sliding():
            down.append(card._shown)
            steady.setdefault(card.key, set()).add(card.header.height())

    PHASE[0] = key + " shut"
    card.toggle()                                          # shut
    run(lambda card=card: not card.sliding(), record=rec2)
    shut_ok = (len(down) >= 3 and monotonic(down, False)
               and card.body.isHidden() and card.body_layout.isEnabled()
               and card.body.maximumHeight() == maya_hubqt._NO_CAP)
    rows.append((key, open_ok, clipped, shut_ok, len(heights), len(down),
                 last, settled))
    print("  %-12s open %s (%d turns, last %s, settled %s) clipped %s "
          "(reflow %d px) shut %s (%d turns)" % (
              key, open_ok, len(heights), last, settled, clipped, reflow,
              shut_ok, len(down)))

gate(1, "every card slides open monotonically onto its settled height",
     all(r[1] for r in rows), [r[0] for r in rows if not r[1]])
gate(2, "the body's children are clipped, never squeezed, on the way",
     all(r[2] for r in rows), [r[0] for r in rows if not r[2]])
gate(3, "every card slides shut monotonically and ends hidden, uncapped",
     all(r[3] for r in rows), [r[0] for r in rows if not r[3]])
shaking = dict((k, sorted(v)) for k, v in steady.items()
               if v != {skin.cards[k].header.sizeHint().height()})
gate("3b", "the header keeps its height, the title does not shake "
     "(the animator saw it shake, 2026-10-01)", not shaking, shaking)
sliding = sorted(c[0] for c in COST if c[3])
p99 = sliding[int(len(sliding) * 0.99)] if sliding else 0.0
worst = sorted(COST, key=lambda c: c[0] + c[1])[-3:]
gate(4, "a frame while sliding: 99 of 100 under one 60 Hz frame",
     sliding and p99 < 16.7,
     "Qt events mean %.2f ms, p99 %.1f ms over %d sliding turns; worst "
     "turns (Qt ms, Maya idle ms, phase, moving) %s" % (
         sum(sliding) / len(sliding), p99, len(sliding),
         [("%.1f" % a, "%.1f" % b, p, m) for a, b, p, m in worst]))

# ------------------------------------------------------------- 2 turn back
PHASE[0] = "turn back"
card = skin.cards["uebridge"]
trace = []
card.toggle()                                              # opening
t0 = time.perf_counter()
while time.perf_counter() - t0 < 0.08:
    turn()
    trace.append(card._shown)
    time.sleep(0.004)
mid = card._shown
card.toggle()                                              # shut again
after = []
run(lambda: not card.sliding(),
    record=lambda: after.append(card._shown) if card.sliding() else None)
step = max([abs(b - a) for a, b in zip(trace, trace[1:])] or [0])
gate(5, "turned back mid-way: no jump where it turns, ends shut",
     0 < mid and after and abs(after[0] - mid) <= max(step, 1) * 2
     and monotonic(after, False) and card.body.isHidden(),
     "at %d, then %s..., step %d" % (mid, after[:3], step))

# --------------------------------------------------------------------- 3 jump
PHASE[0] = "jump"
for key in ("uebridge", "characters", "weapons"):
    skin.cards[key].set_collapsed(False)
settle()
bar = skin.scroll.verticalScrollBar()
bar.setValue(0)
settle()
values = []
maya_hub.focus("studio")
studio = skin.cards["studio"]
run(lambda: skin._glide is None and skin._glide_card is None and not any(
    c.sliding() for c in skin.cards.values()) and len(values) > 3,
    timeout=2.5, record=lambda: values.append(bar.value()))
shut = [k for k, c in skin.cards.items() if k != "studio"
        and not (c.collapsed() and c.body.isHidden())]
gate(6, "a jump shuts the others and opens the chosen one",
     not shut and not studio.collapsed() and not studio.body.isHidden(),
     shut)
distinct = sorted(set(values))
target = min(studio.frame.y(), bar.maximum())
gate(7, "the scroll glides (several steps, monotonic) onto the card",
     len(distinct) >= 4 and monotonic(values, True)
     and bar.value() == target,
     "%d distinct values %s ... ends %d, card at %d (max %d)" % (
         len(distinct), distinct[:4], bar.value(), studio.frame.y(),
         bar.maximum()))

# ----------------------------------------------------------------- 4 off
PHASE[0] = "off"
maya_hub.set_animations(False)
card = skin.cards["colour"]
card.toggle()
instant = not card.sliding() and not card.body.isHidden()
card.toggle()
instant = instant and not card.sliding() and card.body.isHidden()
bar.setValue(0)
settle()
maya_hub.focus("colour")
settle()
no_glide = skin._glide is None
gate(8, "switched off: a click and a jump are instant",
     instant and no_glide and not any(c.sliding()
                                      for c in skin.cards.values())
     and bar.value() == min(skin.cards["colour"].frame.y(), bar.maximum()),
     "menu row checked: %s" % skin.animations_action.isChecked())
maya_hub.set_animations(True)
gate(9, "back on: the switch, the menu row and the optionVar agree",
     skin.animations and skin.animations_action.isChecked()
     and maya_hubmotion.enabled())

# --------------------------------------------------------------- 5 photos
PHASE[0] = "photos"
for c in skin.cards.values():
    c.set_collapsed(True)
bar.setValue(0)
settle()
card = skin.cards["characters"]
card.set_collapsed(False, animate=True)
anim = card._anim
frames = []
for fraction in (0.15, 0.35, 0.6, 1.0):
    if card._anim is not None:
        card._anim.setCurrentTime(int(anim.duration() * fraction))
    settle()
    view = skin.scroll.viewport()
    frames.append(view.grab())
w = max(f.width() for f in frames)
h = max(f.height() for f in frames)
gap = 12
strip = q.QtGui.QPixmap(len(frames) * w + (len(frames) - 1) * gap, h)
strip.fill(q.QtGui.QColor("#1b1c20"))
painter = q.QtGui.QPainter(strip)
for i, f in enumerate(frames):
    painter.drawPixmap(i * (w + gap), 0, f)
painter.end()
path = os.path.join(OUT, "hub_motion_strip.png")
strip.save(path)
gate(10, "photographed: a card sliding open, four moments", os.path.isfile(
    path), path)

maya_hub.set_animations(saved_switch)
print("PASSED %d FAILED %d %s" % (len(PASSED), len(FAILED), FAILED))

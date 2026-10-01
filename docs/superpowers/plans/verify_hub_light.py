"""verify_hub_light.py - the hub's card light fades, a chosen card flashes:
live.

Run in a DISPOSABLE Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME) on the REPO's
hub, floated to the animator's dock width, sent through its command port.
The send turns the event loop itself (processEvents + processIdleEvents +
4 ms sleeps) so the animations run on a real clock. The mouse is stood in
for by Skin._hover_from(widget) - what the application-wide watcher calls on
every Enter - and a press by Skin.set_active (what it calls on a press).

    1  a hover lights a card: its level rises monotonically to 1 in about
       LIGHT_IN_MS; skActive at once
    2  a hover on another card cross-fades: the old falls monotonically to 0
       in about LIGHT_OUT_MS while the new rises
    3  a press on another card flashes it (up to ~1, then back to 0); a
       press inside the same card does not
    4  a quick sweep across the cards: a turn of the loop stays under a
       60 Hz frame (p99)
    5  the pixels on screen: the lit card's ring card_edge, its face
       card_active; a dark card's ring the plain card
    6  Interface animations off: the light switches at once, no flash

UI only: no scene node is touched; the switch's optionVar is put back.

Spec: docs/superpowers/specs/2026-10-01-hub-card-light-design.md
"""
import time

import maya.utils

import maya_hub
import maya_hubmotion
import maya_hubqt
import maya_hubstyle

FAILED = []
PASSED = []


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2s %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


q = maya_hubqt.qt()
app = q.QtWidgets.QApplication.instance()
skin = maya_hub._SKIN
assert skin is not None and skin.alive(), "no skinned hub"
COST = []


def turn():
    t0 = time.perf_counter()
    app.processEvents()
    maya.utils.processIdleEvents()
    COST.append((time.perf_counter() - t0) * 1000.0)


def run(until, timeout=1.5, record=None):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        turn()
        if record:
            record()
        if until():
            break
        time.sleep(0.004)
    for _ in range(4):
        turn()
    return time.perf_counter() - t0


def settle():
    for _ in range(8):
        turn()


def monotonic(values, rising):
    return all((y >= x) if rising else (y <= x)
               for x, y in zip(values, values[1:]))


def quiet():
    return not any(c._light_anim or c._flash_anim
                   for c in skin.cards.values())


saved_switch = maya_hubmotion.enabled()
maya_hub.set_animations(True)
for c in skin.cards.values():
    c.set_collapsed(True)
for k in ("retarget", "colour", "studio"):
    skin.cards[k].set_collapsed(False)
skin.scroll.verticalScrollBar().setValue(0)
skin.set_active(None)
skin._light(None)
settle()
run(quiet)
a, b, s = skin.cards["retarget"], skin.cards["colour"], skin.cards["studio"]

# ------------------------------------------------------------ 1 a hover
up = []
skin._hover_from(a.header)
lit_at_once = bool(a.frame.property("skActive"))
spent = run(lambda: a._light_anim is None,
            record=lambda: up.append(a.frame.level))
gate(1, "a hover lights the card: monotonic to 1, skActive at once",
     lit_at_once and monotonic(up, True) and a.frame.level == 1.0
     and len(set(up)) >= 3,
     "%d turns, %.0f ms (LIGHT_IN_MS %d)" % (len(up), spent * 1000,
                                            maya_hubmotion.LIGHT_IN_MS))

# ---------------------------------------------------------- 2 cross-fade
down, rise = [], []
skin._hover_from(b.header)
spent = run(lambda: a._light_anim is None and b._light_anim is None,
            record=lambda: (down.append(a.frame.level),
                            rise.append(b.frame.level)))
gate(2, "a hover on another card cross-fades the two",
     monotonic(down, False) and monotonic(rise, True)
     and (a.frame.level, b.frame.level) == (0.0, 1.0)
     and not a.frame.property("skActive")
     and bool(b.frame.property("skActive")),
     "old %.2f..%.2f, new %.2f..%.2f, %.0f ms (LIGHT_OUT_MS %d)" % (
         down[0], down[-1], rise[0], rise[-1], spent * 1000,
         maya_hubmotion.LIGHT_OUT_MS))

# --------------------------------------------------------------- 3 flash
flash = []
skin.set_active("studio")
started = s._flash_anim is not None
run(lambda: s._flash_anim is None and s._light_anim is None,
    record=lambda: flash.append(s.frame.flash))
peak = max(flash) if flash else 0.0
top = flash.index(peak) if flash else 0
skin.set_active("studio")                     # a press inside the same card
again = s._flash_anim is not None
gate(3, "a press on another card flashes it; inside the same one it does "
     "not",
     started and peak > 0.9 and monotonic(flash[:top + 1], True)
     and monotonic(flash[top:], False) and s.frame.flash == 0.0
     and not again,
     "peak %.2f at turn %d of %d" % (peak, top, len(flash)))

# --------------------------------------------------------------- 4 sweep
COST[:] = []
for key in ("retarget", "colour", "studio", "retarget", "colour"):
    skin._hover_from(skin.cards[key].header)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.06:
        turn()
        time.sleep(0.004)
run(quiet)
ordered = sorted(COST)
p99 = ordered[int(len(ordered) * 0.99)]
gate(4, "a quick sweep across the cards: 99 of 100 turns under a 60 Hz "
     "frame",
     p99 < 16.7, "mean %.2f ms, p99 %.1f, worst %.1f over %d turns" % (
         sum(COST) / len(COST), p99, ordered[-1], len(COST)))


# -------------------------------------------------------------- 5 pixels
def pixel(card, x, y):
    image = card.frame.grab().toImage()
    c = image.pixelColor(x, y)
    return c.red(), c.green(), c.blue()


def near(rgb, token, tol):
    h = maya_hubstyle.TOKENS[token]
    want = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    return all(abs(p - w) <= tol for p, w in zip(rgb, want))


skin._hover_from(a.header)
run(quiet)
mid = a.frame.width() // 2
ring_lit = pixel(a, mid, 1)
face_lit = pixel(a, mid, a.frame.height() - maya_hubstyle.px(24, a.scale))
ring_dark = pixel(b, mid, 1)
gate(5, "on screen: the lit ring card_edge, its face card_active, a dark "
     "card's ring plain",
     near(ring_lit, "card_edge", 14) and near(face_lit, "card_active", 6)
     and near(ring_dark, "card", 6),
     "lit ring %s face %s, dark ring %s" % (ring_lit, face_lit, ring_dark))

# ----------------------------------------------------------------- 6 off
maya_hub.set_animations(False)
skin._hover_from(s.header)
instant = (s.frame.level == 1.0 and a.frame.level == 0.0
           and s._light_anim is None and a._light_anim is None)
skin.set_active("colour")
no_flash = b._flash_anim is None and b.frame.flash == 0.0
gate(6, "Interface animations off: the light switches at once, no flash",
     instant and no_flash)
maya_hub.set_animations(saved_switch)
skin.set_active(None)
skin._light(None)
settle()
print("PASSED %d FAILED %d %s" % (len(PASSED), len(FAILED), FAILED))

"""verify_hub_glow.py - the hub's controls glow under the mouse: live.

Run in a DISPOSABLE Maya (scratch MAYA_APP_DIR, MAYA_NO_HOME) on the REPO's
hub, floated to the animator's dock width, sent through its command port.
The mouse is stood in for by a real QEnterEvent / Leave event sent to each
of Maya's own widgets: they go through the skin's application-wide watcher,
the same road a real hover takes. The send turns the event loop itself
(processEvents + processIdleEvents + 4 ms sleeps), so the fades run on a
real clock. Every widget is found AGAIN by name before each use (CLAUDE.md
trap 148).

    1  every kind of control glows when entered: a Maya button, a segment,
       a checkbox, a dropdown, a chip, a strip jump, a header button - our
       effect on it, level 1, its glow computed, not broken
    2  the fade: up monotonic in about GLOW_IN_MS, down monotonic in about
       GLOW_OUT_MS after a Leave; the effect stays, dark
    3  the picture: light round the control and nowhere else (its text
       grayscale while lit - Qt's source pixmap); going dark after the
       control repainted itself, it is drawn directly: only light added
    4  the primary button lights its rim (mode "rim"): brighter just inside
       its edge, its middle unchanged
    5  one at a time: entering another control cross-fades the two
    6  what does not glow: a heading, a field, a status line, a CARD HEADER
       (its card lights up instead), a disabled button
    7  the cost: a lit card's grab with the glow cached costs about what the
       dark one costs; the first compute stays small; a sweep across ten
       controls keeps 99 of 100 loop turns under a 60 Hz frame
    8  Interface animations off: the glow switches at once
    9  a hub rebuilt in the middle of a fade: nothing breaks, the new hub's
       controls glow
   10  a picture: a strip jump, a button, a segment, a dropdown, a
       checkbox and the primary button, each dark then lit
   11  every control of a card hovered once: their dark effects are
       disabled and the card paints as fast as with none

UI only: no scene node is touched; the switch's optionVar is put back.

Spec: docs/superpowers/specs/2026-10-02-hub-hover-glow-design.md
"""
import os
import time

import maya.cmds as cmds
import maya.utils

import maya_hub
import maya_hubglow
import maya_hubmotion
import maya_hubqt

FAILED = []
PASSED = []
OUT_PNG = "C:/!!!Work/MayaScripts/docs/superpowers/plans/hub_glow.png"


def gate(n, name, ok, detail=""):
    (PASSED if ok else FAILED).append(n)
    print("%s %2s %s%s" % ("ok  " if ok else "FAIL", n, name,
                           (" - " + str(detail)) if detail else ""))


q = maya_hubqt.qt()
QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
app = QtWidgets.QApplication.instance()
COST = []


def skin():
    s = maya_hub._SKIN
    assert s is not None and s.alive(), "no skinned hub"
    return s


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
    for _ in range(3):
        turn()
    return time.perf_counter() - t0


def settle():
    for _ in range(8):
        turn()


def monotonic(values, rising):
    return all((y >= x) if rising else (y <= x)
               for x, y in zip(values, values[1:]))


SENDING = [False]
FOREIGN = []


class Spy(QtCore.QObject):
    """Counts the Enter / Leave events on the hub that THIS script did not
    send: the real mouse over the disposable Maya's window (the animator may
    be using the machine) would move the glow under a gate."""

    def eventFilter(self, obj, event):                       # noqa: N802
        try:
            if (event.type() in (QtCore.QEvent.Enter, QtCore.QEvent.Leave)
                    and not SENDING[0]
                    and isinstance(obj, QtWidgets.QWidget)):
                s = maya_hub._SKIN
                if s is not None and s.alive() and (
                        obj is s.root or s.root.isAncestorOf(obj)):
                    FOREIGN.append((event.type() == QtCore.QEvent.Enter,
                                    obj.objectName()))
        except Exception:                                    # noqa: BLE001
            pass
        return False


SPY = Spy()
app.installEventFilter(SPY)


def deaf(on=True):
    """The real mouse kept off the hub's widgets for the length of the run
    (the animator may move it across the disposable Maya - 65 foreign events
    in one gate, measured): Qt's childAt skips a root that is transparent for
    mouse events, so no real Enter reaches a control; the events this script
    sends go to the widget directly."""
    skin().root.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, on)


def foreign():
    """How many hub Enter/Leave events came from elsewhere since last asked."""
    n = len(FOREIGN)
    del FOREIGN[:]
    return n


def enter(widget):
    pt = QtCore.QPointF(2, 2)
    SENDING[0] = True
    try:
        QtWidgets.QApplication.sendEvent(widget, QtGui.QEnterEvent(pt, pt, pt))
    finally:
        SENDING[0] = False


def leave(widget):
    SENDING[0] = True
    try:
        QtWidgets.QApplication.sendEvent(widget,
                                         QtCore.QEvent(QtCore.QEvent.Leave))
    finally:
        SENDING[0] = False


def into_view(widget):
    """Scroll the hub so `widget` is on screen: a control off screen is never
    painted, so its glow is never computed."""
    skin().scroll.ensureWidgetVisible(widget, 0, 60)
    settle()


def effect_of(widget):
    e = widget.graphicsEffect()
    return e if isinstance(e, maya_hubqt._glow_class()) else None


def quiet():
    return not skin().glow._fades


def array(image):
    import numpy as np
    image = image.convertToFormat(QtGui.QImage.Format_RGB32)
    w, h, bpl = image.width(), image.height(), image.bytesPerLine()
    data = np.frombuffer(image.constBits(), np.uint8, count=bpl * h)
    return data.reshape(h, bpl // 4, 4)[:, :w, :3].astype(int)


# --------------------------------------------------------- finding controls

def card_widgets(key):
    card = skin().cards[key]
    return [w for w in card.body.findChildren(QtWidgets.QWidget)
            if w.isVisible()]


def first(key, test):
    for w in card_widgets(key):
        if test(w):
            return w
    return None


def is_role(role):
    return lambda w: (isinstance(w, QtWidgets.QAbstractButton)
                      and w.property("skRole") == role and w.isEnabled())


FINDERS = {
    "primary": ("characters", is_role("primary")),
    "secondary": ("characters", lambda w: (
        isinstance(w, QtWidgets.QPushButton) and w.isEnabled()
        and w.property("skRole") in ("secondary", None, "")
        and w.text().strip() != "")),
    "segment": ("characters", lambda w: is_role("segment")(w)
                and not w.isChecked()),
    "checkbox": ("characters", lambda w: isinstance(w, QtWidgets.QCheckBox)
                 and w.isEnabled()),
    "dropdown": ("characters", lambda w: isinstance(w, QtWidgets.QComboBox)
                 and w.isEnabled()),
    "chip": ("studio", is_role("chip")),
}


def control(kind):
    s = skin()
    if kind == "header":
        return s.cards["retarget"].header
    if kind == "jump":
        return s.jumps["retarget"]
    if kind == "headbtn":
        return s.hotkeys
    key, test = FINDERS[kind]
    return first(key, test)


def card_key_of(widget):
    return skin().card_of(widget)


#  The switch as the animator had it, read BEFORE anything changes it;
#  every gate below runs inside one function under try/finally, so
#  whatever fails, the switch, the spy and the mouse come back (a gate
#  that died right after switching the animations off once left them
#  off for good: every later run 'restored' what it found).
saved_switch = maya_hubmotion.enabled()


def gates():
    # ------------------------------------------------------------------- setup

    maya_hub.set_animations(True)
    s = skin()
    for c in s.cards.values():
        c.set_collapsed(True)
    for k in ("characters", "retarget", "studio"):
        s.cards[k].set_collapsed(False)
    s.scroll.verticalScrollBar().setValue(0)
    deaf(True)
    settle()
    foreign()
    print("viewport", s.scroll.viewport().width(), "x",
          s.scroll.viewport().height())

    KINDS = ("secondary", "segment", "checkbox", "dropdown", "jump",
             "headbtn", "chip")

    # ----------------------------------------------------- 1 every kind glows
    found, lit_ok, detail = [], [], []
    for kind in KINDS:
        w = control(kind)
        if w is None:
            detail.append("%s: none found" % kind)
            continue
        found.append(kind)
        into_view(w)
        enter(control(kind))
        run(quiet)
        w = control(kind)
        e = effect_of(w)
        good = (e is not None and e.level == 1.0 and not e.broken
                and e.computed >= 1 and skin().glow.lit is e)
        lit_ok.append(good)
        detail.append("%s %s level %s computed %s%s" % (
            kind, type(w).__name__, None if e is None else round(e.level, 3),
            None if e is None else e.computed,
            "" if e is None or not e.broken else " BROKEN " + str(e.error)))
        leave(w)
        run(quiet)
    gate(1, "every kind of control glows when entered",
         len(found) == len(KINDS) and all(lit_ok),
         "; ".join(detail) + " | foreign events %d" % foreign())

    # ------------------------------------------------------------- 2 the fade
    w = control("secondary")
    into_view(w)
    foreign()
    up, down = [], []
    enter(control("secondary"))
    t_up = run(quiet, record=lambda: up.append(effect_of(control("secondary"))
                                               .level))
    lit_before_leave = skin().glow.lit is effect_of(control("secondary"))
    leave(control("secondary"))
    t_down = run(quiet, record=lambda: down.append(
        effect_of(control("secondary")).level))
    e = effect_of(control("secondary"))
    gate(2, "the fade: up then down, monotonic, about GLOW_IN_MS / GLOW_OUT_MS",
         monotonic(up, True) and monotonic(down, False) and len(set(up)) >= 3
         and len(set(down)) >= 3 and up[-1] == 1.0 and e is not None
         and e.level == 0.0,
         "up %d turns %.0f ms (%d), down %d turns %.0f ms (%d); lit before "
         "the leave %s, foreign events %d" % (
             len(up), t_up * 1000, maya_hubmotion.GLOW_IN_MS, len(down),
             t_down * 1000, maya_hubmotion.GLOW_OUT_MS, lit_before_leave,
             foreign()))


    # ---------------------------------------------------------- 3 the picture
    def lit_and_dark(kind):
        """(dark, lit, fading, rect of the control in its card frame): fading is
        the glow going dark after the control repainted itself (what the hover
        style coming off does as the real mouse leaves)."""
        w = control(kind)
        key = card_key_of(w)
        maya_hub.set_animations(False)
        enter(w)
        settle()
        frame = skin().cards[key].frame
        lit = array(frame.grab().toImage())
        e = effect_of(control(kind))
        e.rising, e.level = False, 0.6
        control(kind).update()
        settle()
        fading = array(skin().cards[key].frame.grab().toImage())
        leave(control(kind))
        settle()
        frame = skin().cards[key].frame
        dark = array(frame.grab().toImage())
        w = control(kind)
        top_left = w.mapTo(frame, QtCore.QPoint(0, 0))
        rect = QtCore.QRect(top_left, w.size())
        maya_hub.set_animations(True)
        return dark, lit, fading, rect


    import numpy as np                                            # noqa: E402

    dark, lit, fading, rect = lit_and_dark("secondary")
    diff = lit - dark
    reach = maya_hubglow.pad(skin().scale) + 1
    outside = np.ones(diff.shape[:2], bool)
    outside[max(0, rect.top() - reach):rect.bottom() + reach + 1,
            max(0, rect.left() - reach):rect.right() + reach + 1] = False
    fade = fading - dark
    gate(3, "the picture: light round the control and nowhere else; going dark "
         "the control is drawn directly again, its text as before",
         int(diff.max()) > 25 and int(np.abs(diff[outside]).max()) == 0
         and int(fade.min()) >= -1 and int(fade.max()) > 10
         and int(np.abs(fade[outside]).max()) == 0,
         "lit: up to +%d on %d pixels, outside %d, %d text-edge pixels darker "
         "(grayscale, not ClearType, while lit); fading: least %d, up to +%d" % (
             int(diff.max()), int((diff.max(axis=2) > 4).sum()),
             int(np.abs(diff[outside]).max()),
             int((diff.min(axis=2) < -1).sum()), int(fade.min()),
             int(fade.max())))

    # ------------------------------------------------------ 4 the primary rim
    dark_p, lit_p, _fading_p, rect_p = lit_and_dark("primary")
    e = effect_of(control("primary"))
    dp = (lit_p - dark_p).max(axis=2)
    cy = rect_p.center().y()
    edge_x = rect_p.left() + 2
    mid_x = rect_p.center().x()
    gate(4, "the primary button lights its rim, not its middle",
         e is not None and e.mode == "rim" and int(dp[cy, edge_x]) > 10
         and int(dp[cy, mid_x]) == 0,
         "mode %s, edge +%d, middle +%d" % (None if e is None else e.mode,
                                            int(dp[cy, edge_x]),
                                            int(dp[cy, mid_x])))

    # ----------------------------------------------------- 5 one at a time
    enter(control("secondary"))
    run(quiet)
    enter(control("segment"))
    a_vals, b_vals = [], []
    run(quiet, record=lambda: (a_vals.append(effect_of(control("secondary"))
                                             .level),
                               b_vals.append(effect_of(control("segment"))
                                             .level)))
    gate(5, "one at a time: another control cross-fades the two",
         monotonic(a_vals, False) and monotonic(b_vals, True)
         and a_vals[-1] == 0.0 and b_vals[-1] == 1.0
         and skin().glow.lit is effect_of(control("segment")),
         "old %.2f..%.2f, new %.2f..%.2f" % (a_vals[0], a_vals[-1], b_vals[0],
                                              b_vals[-1]))
    leave(control("segment"))
    run(quiet)

    # ------------------------------------------------- 6 what does not glow
    foreign()
    quiet_ok, why = True, []
    for name in ("mayaSceneSetupCharactersHeading", "ueAnimBridgeSearch",
                 "mayaSceneSetupCharacterStatus"):
        w = maya_hubqt.find(name)
        if w is None:
            why.append("%s: none found" % name)
            quiet_ok = False
            continue
        enter(w)
        run(quiet)
        w = maya_hubqt.find(name)
        lit = skin().glow.lit
        if effect_of(w) is not None or lit is not None:
            quiet_ok = False
        why.append("%s %s%s" % (name, w.metaObject().className(),
                                "" if lit is None else " LIT"))
    #  a card header: its card lights up, it does not glow (the animator, minutes
    #  after the first build)
    enter(skin().cards["retarget"].header)
    run(quiet)
    header_dark = (effect_of(skin().cards["retarget"].header) is None
                   and skin().glow.lit is None
                   and skin().active == "retarget")
    quiet_ok = quiet_ok and header_dark
    why.append("card header %s" % ("dark, its card lit" if header_dark
                                   else "GLOWS"))
    leave(skin().cards["retarget"].header)
    run(quiet)
    #  by NAME: `control("secondary")` asks for an ENABLED button and would hand
    #  back the next one
    btn_name = control("secondary").objectName()
    maya_hubqt.find(btn_name).setEnabled(False)
    enter(maya_hubqt.find(btn_name))
    run(quiet)
    e_dis = effect_of(maya_hubqt.find(btn_name))
    disabled_dark = (skin().glow.lit is None
                     and (e_dis is None or e_dis.level == 0.0))
    maya_hubqt.find(btn_name).setEnabled(True)
    why.append("disabled %s" % btn_name)
    gate(6, "a heading, a field, a status line, a disabled button do not glow",
         quiet_ok and disabled_dark,
         ", ".join(why) + "; disabled dark %s; foreign events %d" % (
             disabled_dark, foreign()))

    # ---------------------------------------------------------------- 7 cost
    def timed_grab(key):
        t0 = time.perf_counter()
        skin().cards[key].frame.grab()
        return (time.perf_counter() - t0) * 1000.0


    maya_hub.set_animations(False)
    w = control("dropdown")
    w_key = card_key_of(w)
    dark_ms = sorted(timed_grab(w_key) for _ in range(5))[2]
    enter(control("dropdown"))
    effect_of(control("dropdown"))._key = None     # a first compute, measured
    first_ms = timed_grab(w_key)
    cached_ms = sorted(timed_grab(w_key) for _ in range(5))[2]
    leave(control("dropdown"))
    settle()
    maya_hub.set_animations(True)


    def sweep():
        COST[:] = []
        for kind in KINDS * 2:
            enter(control(kind))
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 0.05:
                turn()
                time.sleep(0.004)
            leave(control(kind))
        run(quiet)
        ordered = sorted(COST)
        return ordered, ordered[int(len(ordered) * 0.99)]


    #  the same sweep with the glow switched off first: what the card light,
    #  the hover styles and the loop cost on their own
    skin().glow.enter = lambda widget: None
    base, base_p99 = sweep()
    del skin().glow.enter
    for e in skin().glow.effects:
        e._key = None                     # every glow computed afresh
    ordered, p99 = sweep()
    gate(7, "the cost: cached glow costs about nothing, a sweep keeps 60 Hz",
         cached_ms < dark_ms + 6.0 and first_ms < dark_ms + 12.0 and p99 < 16.7,
         "card grab dark %.1f ms, first lit %.1f, cached lit %.1f; sweep mean "
         "%.2f, p99 %.1f, worst %.1f over %d turns (without the glow: mean "
         "%.2f, p99 %.1f, worst %.1f); foreign events %d" % (
             dark_ms, first_ms, cached_ms, sum(ordered) / len(ordered), p99,
             ordered[-1], len(ordered), sum(base) / len(base), base_p99,
             base[-1], foreign()))

    # ------------------------------------------------------------------ 8 off
    maya_hub.set_animations(False)
    enter(control("checkbox"))
    e = effect_of(control("checkbox"))
    instant_on = e is not None and e.level == 1.0 and quiet()
    leave(control("checkbox"))
    instant_off = e.level == 0.0 and quiet()
    maya_hub.set_animations(True)
    gate(8, "Interface animations off: the glow switches at once",
         instant_on and instant_off)

    # ------------------------------------------------- 9 a rebuild mid-fade
    enter(control("secondary"))
    turn()
    turn()
    maya_hub.rebuild()
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.5:
        turn()
        time.sleep(0.004)
    s = skin()
    for k in ("characters", "retarget", "studio"):
        s.cards[k].set_collapsed(False)
    deaf(True)
    settle()
    enter(control("segment"))
    run(quiet)
    e = effect_of(control("segment"))
    gate(9, "a hub rebuilt mid-fade: nothing breaks, the new hub glows",
         e is not None and e.level == 1.0 and not e.broken
         and skin().glow.lit is e)
    leave(control("segment"))
    run(quiet)


    # ------------------------------------------------------------- 10 picture
    def holder(kind):
        """The card frame holding the control, or the strip / header (a jump
        and a header button stand outside every card)."""
        s = skin()
        key = card_key_of(control(kind))
        if key is not None:
            return s.cards[key].frame
        return s.strip if kind == "jump" else s.header


    def crop(kind):
        maya_hub.set_animations(False)
        enter(control(kind))
        settle()
        frame = holder(kind)
        w = control(kind)
        tl = w.mapTo(frame, QtCore.QPoint(0, 0))
        pad = maya_hubglow.pad(skin().scale) * 2
        box = QtCore.QRect(tl, w.size()).adjusted(-pad, -pad, pad, pad)
        box = box.intersected(frame.rect())
        lit = frame.grab(box)
        leave(control(kind))
        settle()
        dark = holder(kind).grab(box)
        maya_hub.set_animations(True)
        return dark, lit


    PICTURED = ("jump", "secondary", "segment", "dropdown", "checkbox",
                "primary")
    pairs = []
    for k in PICTURED:
        into_view(control(k))
        pairs.append(crop(k))
    column = max(d.width() for d, _l in pairs) + 26      # the lit column's x
    width = column + max(l.width() for _d, l in pairs) + 14
    height = sum(max(d.height(), l.height()) for d, l in pairs) + 12 * len(pairs)
    canvas = QtGui.QPixmap(width, height + 34)
    canvas.fill(QtGui.QColor("#1f2023"))
    painter = QtGui.QPainter(canvas)
    painter.setPen(QtGui.QColor("#9a9ca3"))
    painter.drawText(14, 22, "mouse away")
    painter.drawText(column + 2, 22, "mouse over it")
    y = 34
    for d, l in pairs:
        painter.drawPixmap(12, y, d)
        painter.drawPixmap(column, y, l)
        y += max(d.height(), l.height()) + 12
    painter.end()
    saved = canvas.save(OUT_PNG)
    gate(10, "a picture: each control dark, then lit", saved, OUT_PNG)

    # --------------------------------------- 11 dark effects cost nothing
    def glowable_names(key):
        s = skin()
        return [w.objectName() for w in card_widgets(key)
                if maya_hubqt.glowing(w, s.root) and w.objectName()]


    def grab_ms(key, n=7):
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            skin().cards[key].frame.grab()
            times.append((time.perf_counter() - t0) * 1000.0)
        return sorted(times)[n // 2]


    maya_hub.set_animations(False)
    names = glowable_names("characters")
    for name in names:                       # every control hovered once
        w = maya_hubqt.find(name)
        if w is not None:
            enter(w)
            leave(maya_hubqt.find(name))
    settle()
    with_fx = 0
    for name in names:
        w = maya_hubqt.find(name)
        e = None if w is None else effect_of(w)
        with_fx += int(e is not None and not e.isEnabled())
    dark_fx_ms = grab_ms("characters")
    for name in names:                       # every effect taken off again
        w = maya_hubqt.find(name)
        if w is not None and effect_of(w) is not None:
            w.setGraphicsEffect(None)
    skin().glow.effects = [e for e in skin().glow.effects
                           if maya_hubqt._valid(e)]
    none_ms = grab_ms("characters")
    maya_hub.set_animations(True)
    gate(11, "every control hovered once: their dark effects cost nothing",
         with_fx >= 10 and dark_fx_ms < none_ms * 1.10 + 1.0,
         "%d dark effects on the card; its grab %.1f ms against %.1f ms with "
         "none" % (with_fx, dark_fx_ms, none_ms))



try:
    gates()
except Exception:                                            # noqa: BLE001
    import traceback
    traceback.print_exc()
    FAILED.append("crashed")
finally:
    try:
        app.removeEventFilter(SPY)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        deaf(False)
    except Exception:                                        # noqa: BLE001
        pass
    maya_hub.set_animations(saved_switch)
    settle()
print("animations as found: %s" % (maya_hubmotion.enabled() == saved_switch))
print("PASSED %d FAILED %d %s" % (len(PASSED), len(FAILED), FAILED))

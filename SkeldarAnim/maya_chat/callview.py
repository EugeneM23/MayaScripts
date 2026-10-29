"""The call window (spec docs/superpowers/specs/2026-10-22-chat-calls-design.md): the hub's look,
the call page in it, buttons for the microphone, the camera, the screen, the devices, folding
and hanging up. One call at a time; the window follows the session's call events.

The page (callpage.py, call.js) drops a `signal` that comes before its `start`, so the window
holds the call's set-up messages until it has sent `start`, then hands them on in order. `start`
carries the first view holding me (I offer to those already in it); anyone who came after it
offers to me, so the membership since then follows as `add_peer` / `remove_peer`
(calls.peer_commands), right after `start` and on every later view.
"""
import sys
import time
import traceback

import maya_hubmotion as hubmotion
import maya_hubqt as hubqt
import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow

from . import calls as _calls
from . import window as W

MIC_VAR = "skeldarChatCallMic"
CAM_VAR = "skeldarChatCallCam"
#  Chromium salts a deviceId per origin and our profile is off the record, so the id a device
#  had belongs to the Maya session it was read in. The LABEL is what survives: the page resolves
#  a stale id by it (2026-10-29).
MIC_LABEL_VAR = "skeldarChatCallMicLabel"
CAM_LABEL_VAR = "skeldarChatCallCamLabel"
POS_VAR = "skeldarChatCallPos"
SIZE_VAR = "skeldarChatCallSize"
SIZE = (640, 440)          # logical px
LEAST = (420, 300)
TILE = (240, 170)          # folded
STAGE_POS_VAR = "skeldarChatStagePos"
STAGE_SIZE_VAR = "skeldarChatStageSize"
STAGE_SIZE = (900, 560)    # logical px
STAGE_NAME = "skeldarChatStageWindow"
ROOT_NAME = "skeldarChatCallWindow"
_ATTR = "_skeldar_chat_call"
_VARS = W._VARS            # optionVars where there is no Maya (tests)

BUTTONS = (("mic", "microphone", u"Микрофон"),
           ("camera", "video", u"Камера"),
           ("screen", "screen-share", u"Показать экран"),
           ("settings", "settings", u"Микрофон и камера"),
           ("fold", "minimize", u"Свернуть"),
           ("hang_up", "phone-off", u"Завершить"))


# a test seam: every connection through the TURN relay (proves the relay carries a call)
RELAY_ONLY = False

def get_var(name):
    return W.get_var(name)


def set_var(name, value):
    W.set_var(name, value)


def current():
    """The call window standing, or None."""
    held = getattr(sys, _ATTR, None)
    return held if held is not None and not held.closed else None


def _set_current(win):
    setattr(sys, _ATTR, win)


def _ask_switch(win):
    """Whether to end the call in progress for a new one (a question)."""
    q = W._q()
    box = q.QtWidgets.QMessageBox
    answer = box.question(win.root if win else None, u"Звонок",
                          u"Завершить текущий звонок и начать новый?")
    return answer == box.Yes


def _make_room(session):
    held = current()
    if held is None:
        return True
    if not _ask_switch(held):
        return False
    held.hang_up()
    return True


def start(session, chat, kind, view_factory=None):
    """I start a call in `chat`; None when the animator keeps the call they are in."""
    if not _make_room(session):
        return None
    win = CallWindow(session, kind, view_factory=view_factory)
    win.chat = chat
    try:
        win.cid = session.start_call(chat, kind)
    except Exception as exc:                                  # noqa: BLE001
        win.fail(refusal_text(getattr(exc, "code", None), getattr(exc, "text", None) or str(exc)),
                 leave=False)
        return None
    win.show()
    return win


def answer(session, call_id, kind, view_factory=None):
    """I join `call_id`; None when the animator keeps the call they are in."""
    if not _make_room(session):
        return None
    win = CallWindow(session, kind, call_id=call_id, view_factory=view_factory)
    view = (getattr(session.state, "calls", None) or {}).get(call_id)
    win.chat = view["chat"] if view else None
    if win.chat:
        win._paint_name()
    try:
        win.cid = session.join_call(call_id)
    except Exception as exc:                                  # noqa: BLE001
        win.fail(refusal_text(getattr(exc, "code", None), getattr(exc, "text", None) or str(exc)),
                 leave=False)
        return None
    win.show()
    return win


def hang_up():
    held = current()
    if held is not None:
        held.hang_up()


def destroy():
    """The window gone now (tests, a plugin update)."""
    held = getattr(sys, _ATTR, None)
    if held is not None:
        held.close_window(at_once=True)
    if hasattr(sys, _ATTR):
        delattr(sys, _ATTR)


def screen_choices(request, kinds=("screen", "window")):
    """[(kind, row, label)] of what a desktop media request offers: screens, then windows.

    A screen is named in our own words: Chromium calls it "Entire screen", one English row above
    eight window titles, and the whole point of the button is that it shares the whole screen."""
    out = []
    for kind, model in (("screen", _model(request, "screensModel")),
                        ("window", _model(request, "windowsModel"))):
        if model is None or kind not in kinds:
            continue
        rows = model.rowCount()
        for row in range(rows):
            label = model.data(model.index(row, 0))
            if kind == "screen":
                label = u"Весь экран" if rows == 1 else u"Весь экран %d" % (row + 1)
            out.append((kind, row, str(label) if label else u"Окно %d" % (row + 1)))
    return out


def capture_text(capture):
    """What the call window says about what is being shared, from the track's own settings."""
    if not capture:
        return u""
    try:
        w, h = int(capture.get("w") or 0), int(capture.get("h") or 0)
    except (TypeError, ValueError):
        w = h = 0
    size = u" %d×%d" % (w, h) if w and h else u""
    if capture.get("surface") == "monitor":
        return u"Экран" + size
    label = (capture.get("label") or u"").strip()
    return (u"Окно: " + label) if label else (u"Окно" + size)


def _model(request, name):
    try:
        return getattr(request, name)()
    except Exception:                                         # noqa: BLE001
        return None


def _pick_screen(win, choices):
    """A menu of the screens and windows under the screen button: (kind, row) or None."""
    q = W._q()
    menu = q.QtWidgets.QMenu(win.root)
    menu.setStyleSheet(hubstyle.stylesheet(win.scale))
    chosen, section = [], None
    for kind, row, label in choices:
        if kind != section:
            menu.addSection(u"Экран" if kind == "screen" else u"Окно")
            section = kind
        hubqt.tag_row(menu.addAction(label), len(chosen))
        chosen.append((kind, row))
    b = win.buttons["screen"]
    #  by the row's number, never its wrapper (maya_hubqt.tag_row, 2026-10-28)
    index = hubqt.row_value(menu.exec(b.mapToGlobal(b.rect().topLeft())))
    return chosen[index] if isinstance(index, int) and 0 <= index < len(chosen) else None


REFUSALS = {
    "call_full": u"В звонке уже 4 человека",
    "call_exists": u"В этом чате уже идёт звонок — присоединитесь к нему",
    "no_call": u"Звонок уже закончился",
    "not_in_call": u"Вы не в этом звонке",
    "too_many": u"Слишком часто — попробуйте через минуту",
    "bad_request": u"Звонок не начался",
}


class _StageWindow(object):
    """The shared screen's own window: our look-B frame around the page Qt hands us for the
    Document Picture-in-Picture window the call page asked for. The <video> itself is MOVED there
    by the page, so nothing is captured or encoded a second time."""

    def __init__(self, win, request):
        q = W._q()
        QtCore, w, Qt = q.QtCore, q.QtWidgets, q.QtCore.Qt
        from PySide6 import QtWebEngineCore, QtWebEngineWidgets
        self.win = win
        self.closed = False
        s, px = win.scale, win.px
        root = w.QWidget(W._main_window(), Qt.Tool | Qt.FramelessWindowHint)
        root.setObjectName(STAGE_NAME)
        root.setAttribute(Qt.WA_TranslucentBackground, True)
        root.setMinimumSize(px(320), px(220))
        outer = w.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = hubqt._named(hubwindow.frame_class()(s), "skeldarChatStageFrame")
        outer.addWidget(frame)
        column = w.QVBoxLayout(frame)
        column.setContentsMargins(px(5), 0, px(5), px(5))
        column.setSpacing(0)

        import maya_hubpop
        title = maya_hubpop._title_class()(self._grab, self._drag, self._drop, lambda: None, frame)
        title.setObjectName("skeldarChatStageTitle")
        title.setFixedHeight(px(hubwindow.TITLE_H))
        row = w.QHBoxLayout(title)
        row.setContentsMargins(px(5), 0, 0, 0)
        row.setSpacing(px(6))
        colour = hubstyle.group("scene").colour
        row.addWidget(hubwindow.title_icon("screen-share", colour, s, "skeldarChatStageIcon"))
        row.addWidget(hubwindow.title_label(u"Экран", s, "skeldarChatStageName"), 1)
        close = hubqt._named(hubwindow.pill_class()("x", s), "skeldarChatStageClose")
        close.setToolTip(u"Вернуть экран в окно звонка")
        close.clicked.connect(lambda *_a: self.close())
        row.addWidget(close)
        column.addWidget(title)

        body = w.QWidget()
        body.setObjectName("skeldarChatStageBody")
        frame.content = body
        column.addWidget(body, 1)
        lay = w.QVBoxLayout(body)
        lay.setContentsMargins(px(4), px(4), px(4), px(4))
        self.view = QtWebEngineWidgets.QWebEngineView(body)
        # the call page's own profile: the stage document stays the opener's, scriptable by it
        page = QtWebEngineCore.QWebEnginePage(win.page.profile(), self.view)
        self.view.setPage(page)
        self.page = page
        lay.addWidget(self.view, 1)
        grip = w.QSizeGrip(body)
        grip.setObjectName("skeldarChatStageGrip")
        grip.setFixedSize(px(14), px(14))
        self.grip = grip
        self._grip_watch = _resize_watch(self._place_grip, body)
        body.installEventFilter(self._grip_watch)
        root.setStyleSheet(hubstyle.stylesheet(s)
                           + "\n#skeldarChatStageFrame { border: none; background: transparent; }")
        hubwindow.dress(frame, s)
        self.root = root
        self.body = body
        request.openIn(page)
        self._place()
        root.show()
        root.raise_()
        self._place_grip()

    # ---------------------------------------------------------- place
    def _place(self):
        q = W._q()
        px = self.win.px
        size = W._pair(get_var(STAGE_SIZE_VAR)) or STAGE_SIZE
        self.root.resize(px(size[0]), px(size[1]))
        point = W._pair(get_var(STAGE_POS_VAR))
        if point:
            self.root.move(int(point[0]), int(point[1]))
        else:
            screen = q.QtWidgets.QApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                self.root.move(area.center().x() - self.root.width() // 2,
                               area.center().y() - self.root.height() // 2)

    def _remember(self):
        try:
            set_var(STAGE_POS_VAR, "%d,%d" % (self.root.x(), self.root.y()))
            set_var(STAGE_SIZE_VAR, "%d,%d" % (round(self.root.width() / self.win.scale),
                                               round(self.root.height() / self.win.scale)))
        except Exception:                                     # noqa: BLE001
            pass

    def _grab(self, point):
        # the title row hands a global (x, y), never a QPoint (maya_hubpop._global)
        pos = self.root.pos()
        self._grab_at = (point[0] - pos.x(), point[1] - pos.y())

    def _drag(self, point):
        grab = getattr(self, "_grab_at", (0, 0))
        self.root.move(point[0] - grab[0], point[1] - grab[1])

    def _drop(self):
        self._remember()

    def _place_grip(self):
        try:
            self.grip.move(self.body.width() - self.grip.width(),
                           self.body.height() - self.grip.height())
            self.grip.raise_()
        except RuntimeError:
            pass

    def close(self, tell=True):
        if self.closed:
            return
        self.closed = True
        self._remember()
        try:
            self.root.hide()
            self.root.deleteLater()
        except RuntimeError:
            pass
        if tell:
            self.win.stage_closed()


def refusal_text(code, text=None):
    """A refusal's line in Russian by its code; else the server's own text."""
    return REFUSALS.get(code) or text or code or u"Звонок не удался"


def _leave_when_known(session, cid, me):
    """A one-shot listener: leave the call `cid` started once its view arrives; gone on an
    error for that cid too."""
    def heard(kind, data):
        try:
            if kind == "error" and data.get("cid") == cid:
                session.unlisten(heard)
            elif kind == "call":
                view = data["call"]
                if view.get("cid") != cid or view.get("by") != me:
                    return
                session.unlisten(heard)
                if view["state"] != "ended" and me in view["members"]:
                    session.leave_call(view["id"])
        except Exception:                                     # noqa: BLE001
            traceback.print_exc()
    session.listen(heard)
    return heard


_CLASSES = {}


def _resize_watch(fn, parent):
    """An event filter calling fn() on its watched widget's resize."""
    if "resize" not in _CLASSES:
        q = W._q()

        class ResizeWatch(q.QtCore.QObject):
            def __init__(self, fn, parent=None):
                super(ResizeWatch, self).__init__(parent)
                self.fn = fn

            def eventFilter(self, obj, event):                # noqa: N802
                if event.type() == q.QtCore.QEvent.Resize:
                    self.fn()
                return False

        _CLASSES["resize"] = ResizeWatch
    return _CLASSES["resize"](fn, parent)


def _set_icon(button, name, scale, colour=None):
    colour = colour or hubstyle.TOKENS["text2"]
    button.setIcon(hubqt.icon(name, colour, hubstyle.px(14, scale)))


class CallWindow(object):
    """One call: the page, its buttons, folding, the session's events."""

    def __init__(self, session, kind, call_id=None, cid=None, view_factory=None):
        self.session, self.kind, self.call_id, self.cid = session, kind, call_id, cid
        self.chat = None
        self.view_factory = view_factory
        self.page_ready = False
        self.started = False          # the page has had its start command
        self.members = []
        self.held = []                # (call, from, data): signals that came before start
        self._pending_view = None
        self.state = {}
        self.icons = {}
        self.folded = False
        self.closed = False
        self.last_message = ""
        self.answered_at = None
        self._here = False
        self._unfolded = None
        self._last_note = ""
        self._want = "screen"         # what the next share takes: the whole screen unless asked
        self._again = False           # a re-take after a stall: the same source, no menu
        self._source = None           # (kind, row) last captured
        self._capture = None          # what the page says it holds
        self._nomic = ""              # why the page holds no microphone, if it holds none
        self._page_error = ""
        self._stalled = False
        self._retakes = 0
        self.stage = None             # the shared screen's own window
        self.scale = W._scale()
        self._build()
        session.listen(self._heard)
        _set_current(self)

    def px(self, n):
        return hubstyle.px(n, self.scale)

    # -------------------------------------------------- building
    def _build(self):
        q = W._q()
        QtCore, w, Qt = q.QtCore, q.QtWidgets, q.QtCore.Qt
        s, px = self.scale, self.px
        from . import callpage
        self.bridge = callpage.bridge_class()(self._page_ready, self._page_signal,
                                              self._page_state)
        root = w.QWidget(W._main_window(), Qt.Tool | Qt.FramelessWindowHint)
        root.setObjectName(ROOT_NAME)
        root.setAttribute(Qt.WA_TranslucentBackground, True)
        root.setMinimumSize(px(LEAST[0]), px(LEAST[1]))
        self.bridge.setParent(root)
        outer = w.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = hubqt._named(hubwindow.frame_class()(s), "skeldarChatCallFrame")
        outer.addWidget(frame)
        self.frame = frame
        column = w.QVBoxLayout(frame)
        column.setContentsMargins(px(5), 0, px(5), px(5))
        column.setSpacing(0)

        import maya_hubpop
        title = maya_hubpop._title_class()(self._grab, self._drag, self._drop, self._title_click,
                                           frame)
        title.setObjectName("skeldarChatCallTitle")
        title.setFixedHeight(px(hubwindow.TITLE_H))
        row = w.QHBoxLayout(title)
        row.setContentsMargins(px(5), 0, 0, 0)
        row.setSpacing(px(6))
        colour = hubstyle.group("scene").colour
        row.addWidget(hubwindow.title_icon("phone", colour, s, "skeldarChatCallIcon"))
        self.name_label = hubwindow.title_label(u"Звонок", s, "skeldarChatCallName")
        row.addWidget(self.name_label)
        self.timer_label = W._label("", "subtitle", "skeldarChatCallTimer")
        row.addWidget(self.timer_label, 1)
        close = hubqt._named(hubwindow.pill_class()("x", s), "skeldarChatCallClose")
        close.setToolTip(u"Завершить звонок")
        close.clicked.connect(lambda *_a: self.press("hang_up"))
        row.addWidget(close)
        column.addWidget(title)
        self.title = title

        body = w.QWidget()
        body.setObjectName("skeldarChatCallBody")
        frame.content = body
        column.addWidget(body, 1)
        self.body = body
        lay = w.QVBoxLayout(body)
        lay.setContentsMargins(px(4), px(4), px(4), px(4))
        lay.setSpacing(px(4))
        make = self.view_factory or callpage.make_view
        self.view, self.page = make(self.bridge, body)
        self.page.screen_requested.connect(self._screen_requested)
        try:
            self.page.stage_requested.connect(self._stage_requested)
        except AttributeError:                                # a page of a test's own
            pass
        lay.addWidget(self.view, 1)
        self.note_label = W._label("", "status", "skeldarChatCallNote", wrap=True)
        self.note_label.setVisible(False)
        lay.addWidget(self.note_label)

        buttons = w.QHBoxLayout()
        buttons.setSpacing(px(4))
        buttons.addStretch(1)
        self.buttons = {}
        for name, icon, tip in BUTTONS:
            b = W._button("", "danger" if name == "hang_up" else None, icon,
                          "skeldarChatCall_" + name, s, tip)
            b.clicked.connect(lambda *_a, n=name: self.press(n))
            if name == "screen":
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(self._screen_menu)
                b.setToolTip(u"Показать экран (правой кнопкой — окно)")
            self.buttons[name] = b
            self.icons[name] = icon
            buttons.addWidget(b)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        grip = w.QSizeGrip(body)
        grip.setObjectName("skeldarChatCallGrip")
        grip.setFixedSize(px(14), px(14))
        self.grip = grip
        self._grip_watch = _resize_watch(self._place_grip, body)
        body.installEventFilter(self._grip_watch)

        root.setStyleSheet(hubstyle.stylesheet(s)
                           + "\n#skeldarChatCallFrame {{ border: none; background: transparent; }}")
        hubwindow.dress(frame, s)
        self.root = root
        self.burster = hubwindow.Burster(frame, self._burst_parts, self._burst_face, s)
        self._place()
        self.clock = QtCore.QTimer(root)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._tick)
        self.clock.start()

    def _burst_parts(self):
        return hubqt.burst_parts(self.frame, self.title, self.body, None, self.scale)

    def _burst_face(self):
        return hubstyle.TOKENS["panel"]

    # -------------------------------------------------- place and size
    def _place(self):
        size = W._pair(get_var(SIZE_VAR)) or (self.px(SIZE[0]), self.px(SIZE[1]))
        size = (max(size[0], self.px(LEAST[0])), max(size[1], self.px(LEAST[1])))
        self.root.resize(size[0], size[1])
        pos = W._pair(get_var(POS_VAR))
        screens = W._screens()
        if pos is None or not any(W._on(sc, (pos[0] + size[0] // 2, pos[1] + self.px(10)))
                                  for sc in screens):
            main = W._main_window()
            if main is not None:
                g = main.frameGeometry()
                point = (g.x() + g.width() // 2, g.y() + g.height() // 2)
            else:
                point = W._cursor() or (screens[0][0] + screens[0][2] // 2,
                                        screens[0][1] + screens[0][3] // 2)
            pos = (point[0] - size[0] // 2, point[1] - size[1] // 2)
        self.root.move(pos[0], pos[1])

    def _remember_place(self):
        try:
            g = self._unfolded if self.folded and self._unfolded is not None \
                else self.root.geometry()
            set_var(POS_VAR, "%d,%d" % (g.x(), g.y()))
            set_var(SIZE_VAR, "%d,%d" % (g.width(), g.height()))
        except RuntimeError:
            pass

    def _grab(self, point):
        pos = self.root.pos()
        self._grab_at = (point[0] - pos.x(), point[1] - pos.y())

    def _drag(self, point):
        grab = getattr(self, "_grab_at", (0, 0))
        self.root.move(point[0] - grab[0], point[1] - grab[1])

    def _drop(self):
        if not self.folded:
            self._remember_place()

    def _title_click(self):
        if self.folded:
            self.fold(False)

    def show(self, origin=None):
        self.root.show()
        self.root.raise_()
        origin = origin or W._cursor()
        if origin is not None and hubmotion.enabled():
            try:
                if self.burster.run(True, origin, self._end_burst):
                    return
            except Exception:                                 # noqa: BLE001
                traceback.print_exc()
        self._end_burst()

    def _end_burst(self):
        try:
            self.burster.stop()
        except Exception:                                     # noqa: BLE001
            pass

    # -------------------------------------------------- the session
    def _heard(self, kind, data):
        if self.closed:
            return
        try:
            if kind == "call":
                self._call(data["call"])
            elif kind == "call_signal":
                self._signal_in(data)
            elif kind == "calls_end":                   # signing out, the session closing
                self.hang_up()
            elif kind == "error" and data.get("cid") and data.get("cid") == self.cid:
                self.fail(refusal_text(data.get("code"), data.get("text")), leave=False)
        except Exception:                                     # noqa: BLE001
            traceback.print_exc()

    def _signal_in(self, data):
        call = data.get("call")
        if self.call_id is not None and call != self.call_id:
            return
        if self.started:
            self.bridge.send("signal", {"from": data["from"], "data": data["data"]})
        else:
            self.held.append((call, data["from"], data["data"]))

    def _me(self):
        return (self.session.state.me or {}).get("id")

    def _call(self, view):
        me = self._me()
        if self.call_id is None:
            if view.get("cid") != self.cid or view.get("by") != me:
                return
            self.call_id = view["id"]
            self.chat = view["chat"]
            self._paint_name()
        if view["id"] != self.call_id:
            return
        if self.chat is None:
            self.chat = view["chat"]
            self._paint_name()
        if view["state"] == "ended":
            self.bridge.send("end", {})
            self.close_window()
            return
        if view.get("answered_at"):
            self.answered_at = view["answered_at"]
        if me not in view["members"]:
            if self.started:                  # left from elsewhere
                self.bridge.send("end", {})
                self.close_window()
            return
        self._mark_here(True)
        if not self.started:
            # The first view holding me is the one I came into: I offer to those already in
            # it. Anyone who joins later offers to me, so later views are membership only.
            if self._pending_view is None:
                self._pending_view = view
            self.members = list(view["members"])
            self._start_page()
            return
        for name, args in _calls.peer_commands(self.members, view["members"], me):
            self.bridge.send(name, args)
        self.members = list(view["members"])

    def _start_page(self):
        view = self._pending_view
        if not self.page_ready or view is None:
            return
        self._pending_view = None
        me = self._me()
        # those of the first view who have left since are not offered to
        view = dict(view, members=[u for u in view["members"] if u in self.members or u == me])
        servers, turn = self.session.turn_servers()
        args = _calls.start_args(view, me, self._names(), servers, self.kind == "video",
                                 get_var(MIC_VAR) or "", get_var(CAM_VAR) or "",
                                 get_var(MIC_LABEL_VAR) or "", get_var(CAM_LABEL_VAR) or "")
        args["relay_only"] = RELAY_ONLY
        args["colours"] = self._colours()         # a stroke is drawn in its author's own colour
        self.bridge.send("start", args)
        self.started = True
        for name, cargs in _calls.peer_commands(view["members"], self.members, me):
            self.bridge.send(name, cargs)
        held, self.held = self.held, []
        for call, frm, data in held:
            if call == self.call_id:
                self.bridge.send("signal", {"from": frm, "data": data})
        if not turn:
            self.say(u"прямое соединение - через строгую сеть может не пройти")

    def _mark_here(self, on):
        """This Maya is in the call (on disk, so after a crash it knows to leave it)."""
        if not self.call_id or self._here == bool(on):
            return
        self._here = bool(on)
        mark = getattr(self.session, "call_here", None)
        if mark is not None:
            try:
                mark(self.call_id, on)
            except Exception:                                 # noqa: BLE001
                traceback.print_exc()

    def holds(self, view):
        """Whether this window is the one for `view` (a starter's waiting on its cid too)."""
        if self.closed:
            return False
        if self.call_id is not None:
            return view.get("id") == self.call_id
        return bool(self.cid) and view.get("cid") == self.cid \
            and view.get("by") == self._me()

    def _names(self):
        chat = self.session.state.chats.get(self.chat) or {}
        from . import look
        return dict((u["id"], look.display_name(u))
                    for u in chat.get("members") or [] if u.get("id"))

    def _colours(self):
        """The avatars' palette, so a stroke over the screen is drawn in its author's colour."""
        from . import look
        chat = self.session.state.chats.get(self.chat) or {}
        ids = [u["id"] for u in chat.get("members") or [] if u.get("id")]
        me = self._me()
        if me and me not in ids:
            ids.append(me)
        return dict((uid, look.user_colour(uid)) for uid in ids)

    def _paint_name(self):
        chat = self.session.state.chats.get(self.chat) or {}
        name = chat.get("name") or ""
        if not name:
            me = self._me()
            try:
                from . import look
                others = [look.display_name(u) for u in chat.get("members") or []
                          if u.get("id") != me]
                name = ", ".join(others)
            except Exception:                                 # noqa: BLE001
                name = ""
        try:
            self.name_label.setText(name or u"Звонок")
        except RuntimeError:
            pass

    # -------------------------------------------------- the page
    def _page_ready(self):
        self.page_ready = True
        if self.started:              # a page that reloaded must not be started twice
            return
        self._start_page()

    def _page_signal(self, to, data):
        if self.call_id:
            self.session.call_signal(self.call_id, to, data)

    def _page_state(self, state):
        self.state = state
        note = state.get("note") or ""
        if note and note != self._last_note:
            self._last_note = note
            self.say(note)
        self._mic_state(state)
        self._capture_state(state)
        self._paint_buttons()

    def _mic_state(self, state):
        """A page with no microphone stays in the call: it hears everybody and its own line says
        so. Until 2026-10-29 a media failure read here called `fail()`, which LEAVES the call -
        the animator met it as «мая говорит что микрофон не найден и отклоняет звонки». Nothing but the call ending ends a call."""
        from . import callpage
        nomic = state.get("nomic") or ""
        if nomic != self._nomic:
            self._nomic = nomic
            callpage.log("[call] " + ("no microphone: " + nomic if nomic else "microphone: ok"))
        error = state.get("error") or ""
        if error != self._page_error:
            self._page_error = error
            if error:
                callpage.log("[call] " + error)

    def _capture_state(self, state):
        """What is being shared, whether it is still moving, and whether the screen wants its own
        window. All three are the page's own reading of the capture it holds."""
        capture = state.get("capture") or None
        if capture != self._capture:
            self._capture = capture
            # A capture of its own may stall in its turn: the flag is tied to the capture, not to
            # the page's stalled/not edge, which a quick recovery can carry away before it is read.
            self._stalled = False
            if capture:
                if not capture.get("again"):
                    self._retakes = 0
                text = capture_text(capture)
                self.say(text)
                from . import callpage
                callpage.log("[call] " + text)      # never a raise out of the state handler
        if not capture:
            self._retakes = 0
        if state.get("stalled") and not self._stalled:
            self._stalled = True
            self._retake()
        if state.get("wants_stage") and self.stage is None and not self.folded:
            self._open_stage()
        elif self.stage is not None and not state.get("stage") and not state.get("wants_stage"):
            self._close_stage(tell=False)

    # -------------------------------------------------- the screen's own window
    def _gesture(self):
        """A click into the page: documentPictureInPicture.requestWindow wants a user activation,
        and our buttons are Qt's, outside the page (measured 2026-10-29: with the click it opens,
        without it «Document PiP requires user activation»)."""
        q = W._q()
        QtCore = q.QtCore
        from PySide6 import QtGui
        target = self.view.focusProxy() or self.view
        point = QtCore.QPointF(max(2.0, target.width() / 2.0), max(2.0, target.height() / 2.0))
        glob = QtCore.QPointF(target.mapToGlobal(point.toPoint()))
        app = q.QtWidgets.QApplication.instance()
        for kind, held in ((QtCore.QEvent.MouseButtonPress, QtCore.Qt.LeftButton),
                           (QtCore.QEvent.MouseButtonRelease, QtCore.Qt.NoButton)):
            app.sendEvent(target, QtGui.QMouseEvent(kind, point, glob, QtCore.Qt.LeftButton,
                                                    held, QtCore.Qt.NoModifier))

    def _open_stage(self):
        if self.stage is not None or self.closed:
            return
        self._gesture()
        self.bridge.send("stage", {"on": True})

    def _stage_requested(self, request):
        """Qt hands the Picture-in-Picture window over: it is built in a frame of ours."""
        try:
            self.stage = _StageWindow(self, request)
        except Exception:                                     # noqa: BLE001
            traceback.print_exc()
            self.stage = None

    def _close_stage(self, tell=True):
        stage, self.stage = self.stage, None
        if stage is not None:
            stage.close(tell=False)
        if tell and not self.closed:
            self.bridge.send("stage", {"on": False})

    def stage_closed(self):
        """The stage window went (its ✕, or Maya): the page puts the tile back in the grid."""
        if self.stage is not None:
            self.stage = None
            if not self.closed:
                self.bridge.send("stage", {"on": False})

    def _paint_buttons(self):
        st = self.state
        for name, icon in (("mic", "microphone" if st.get("mic", True) else "microphone-off"),
                           ("camera", "video" if st.get("cam") else "video-off"),
                           ("screen", "screen-share-off" if st.get("screen") else "screen-share")):
            if self.icons.get(name) != icon:
                self.icons[name] = icon
                try:
                    _set_icon(self.buttons[name], icon, self.scale)
                except RuntimeError:
                    pass

    # -------------------------------------------------- presses
    def press(self, name):
        st = self.state
        if name == "mic":
            self.bridge.send("mute", {"on": bool(st.get("mic", True))})
        elif name == "camera":
            self.bridge.send("camera", {"on": not st.get("cam", False)})
        elif name == "screen":
            self.bridge.send("screen", {"on": not st.get("screen", False)})
        elif name == "settings":
            self._devices_menu()
        elif name == "fold":
            self.fold(not self.folded)
        elif name == "hang_up":
            self.hang_up()

    def hang_up(self):
        if self.closed:
            return
        self._leave()
        self.bridge.send("end", {})
        self.close_window()

    def _leave(self):
        """Leave the call on the server; before its id is known (the starter, the ack not
        back) leave it when its view arrives, so it does not ring on."""
        if self.call_id:
            try:
                self.session.leave_call(self.call_id)
            except Exception:                                 # noqa: BLE001
                traceback.print_exc()
        elif self.cid:
            _leave_when_known(self.session, self.cid, self._me())

    def choose_device(self, kind, device_id, label=""):
        set_var(MIC_VAR if kind == "mic" else CAM_VAR, device_id or "")
        set_var(MIC_LABEL_VAR if kind == "mic" else CAM_LABEL_VAR, label or "")
        self.bridge.send("devices", {"mic": get_var(MIC_VAR) or "", "cam": get_var(CAM_VAR) or "",
                                     "mic_label": get_var(MIC_LABEL_VAR) or "",
                                     "cam_label": get_var(CAM_LABEL_VAR) or ""})

    def _devices_menu(self):
        q = W._q()
        menu = q.QtWidgets.QMenu(self.root)
        menu.setStyleSheet(hubstyle.stylesheet(self.scale))
        devices = self.state.get("devices") or {}
        rows = (("mic", u"Микрофон", devices.get("mics") or [], MIC_VAR, MIC_LABEL_VAR),
                ("cam", u"Камера", devices.get("cams") or [], CAM_VAR, CAM_LABEL_VAR))
        for kind, title, items, var, label_var in rows:
            menu.addSection(title)
            chosen, named = get_var(var) or "", get_var(label_var) or ""
            if not items:
                menu.addAction(u"нет устройств").setEnabled(False)
            for d in items:
                #  the remembered id is this session's; a stale one is still ticked by its label
                text = d.get("label") or d.get("id")
                a = menu.addAction(text)
                a.setCheckable(True)
                a.setChecked(d.get("id") == chosen or (bool(named) and text == named))
                a.triggered.connect(
                    lambda *_a, k=kind, i=d.get("id"), n=text: self.choose_device(k, i, n))
        b = self.buttons["settings"]
        menu.exec(b.mapToGlobal(b.rect().topLeft()))

    def fold(self, on):
        """Folded: a small always-on-top tile of the call; a click on its title unfolds."""
        q = W._q()
        Qt = q.QtCore.Qt
        on = bool(on)
        if on == self.folded:
            return
        self.folded = on
        visible = self.root.isVisible()
        if on:
            self._unfolded = self.root.geometry()
            for name, b in self.buttons.items():
                b.setVisible(name in ("fold", "hang_up"))
            self.note_label.setVisible(False)
            self.grip.setVisible(False)
            self.root.setMinimumSize(0, 0)
            self.root.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.root.resize(self.px(TILE[0]), self.px(TILE[1]))
            _set_icon(self.buttons["fold"], "picture-in-picture", self.scale)
            self.buttons["fold"].setToolTip(u"Развернуть")
        else:
            for b in self.buttons.values():
                b.setVisible(True)
            self.note_label.setVisible(bool(self.last_message))
            self.grip.setVisible(True)
            self.root.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.root.setMinimumSize(self.px(LEAST[0]), self.px(LEAST[1]))
            if self._unfolded is not None:
                self.root.setGeometry(self._unfolded)
            _set_icon(self.buttons["fold"], "minimize", self.scale)
            self.buttons["fold"].setToolTip(u"Свернуть")
        if visible:                    # setWindowFlag hides a shown window
            self.root.show()

    # -------------------------------------------------- screens
    def choose_source(self, request):
        """What to capture. One press of the button shares the WHOLE screen: a lone screen is
        taken with no menu at all, several screens ask which. A window is shared only when it was
        asked for by name (the button's right-button menu), so one can no longer be picked by
        accident out of a list that mixed it with the screen. A re-take after a stall answers with
        the same source, silently."""
        want, self._want = self._want, "screen"
        again, self._again = self._again, False
        if again and self._source is not None:
            return self._source
        if want == "window":
            windows = screen_choices(request, ("window",))
            return _pick_screen(self, windows) if windows else None
        screens = screen_choices(request, ("screen",))
        if len(screens) == 1:
            return (screens[0][0], screens[0][1])
        if screens:
            return _pick_screen(self, screens)
        return _pick_screen(self, screen_choices(request)) or None

    def _screen_requested(self, request):
        try:
            picked = self.choose_source(request)
            if picked is None:
                request.cancel()
                return
            kind, row = picked
            self._source = picked
            model = _model(request, "screensModel" if kind == "screen" else "windowsModel")
            index = model.index(row, 0)
            (request.selectScreen if kind == "screen" else request.selectWindow)(index)
        except Exception:                                     # noqa: BLE001
            traceback.print_exc()
            try:
                request.cancel()
            except Exception:                                 # noqa: BLE001
                pass

    def _screen_menu(self, point):
        """The screen button's right button: share a window instead of the whole screen."""
        q = W._q()
        menu = q.QtWidgets.QMenu(self.root)
        menu.setStyleSheet(hubstyle.stylesheet(self.scale))
        hubqt.tag_row(menu.addAction(u"Весь экран"), "screen")
        hubqt.tag_row(menu.addAction(u"Показать окно…"), "window")
        b = self.buttons["screen"]
        chosen = hubqt.row_value(menu.exec(b.mapToGlobal(point)))
        if chosen not in ("screen", "window"):
            return
        self._want = chosen
        if self.state.get("screen"):
            self.bridge.send("screen", {"on": False})
        self.bridge.send("screen", {"on": True})

    def _retake(self):
        """The capture stopped handing out frames while its track was live: take it again with the
        same source (no menu). Twice at most - then it is said and left alone."""
        if self._retakes >= 2:
            self.say(u"Картинка замерла — поделитесь экраном заново")
            return
        self._retakes += 1
        self.say(u"Картинка замерла — беру экран заново")
        self._again = True
        self.bridge.send("screen", {"on": True, "again": True})

    # -------------------------------------------------- the rest
    def _tick(self):
        if self.closed:
            return
        try:
            self._place_grip()
            if self.answered_at:
                seconds = max(0, int(time.time() - self.answered_at / 1000.0))
                self.timer_label.setText("%d:%02d" % (seconds // 60, seconds % 60))
            else:
                self.timer_label.setText(u"вызов…")
        except RuntimeError:
            pass

    def _place_grip(self):
        try:
            self.grip.move(self.body.width() - self.grip.width(),
                           self.body.height() - self.grip.height())
            self.grip.raise_()
        except RuntimeError:
            pass

    def say(self, text):
        self.last_message = text
        try:
            self.note_label.setText(text)
            self.note_label.setVisible(bool(text) and not self.folded)
        except RuntimeError:
            pass

    def fail(self, text, leave=True):
        """Say why and close; `leave`: leave the call on the server too (a failure while in it)."""
        if leave and not self.closed:
            self._leave()
            self.bridge.send("end", {})
        self.say(text)
        try:
            from . import notify
            notify.say(u"Звонок", text)
        except Exception:                                     # noqa: BLE001
            pass
        self.close_window()

    def close_window(self, at_once=False):
        if self.closed:
            return
        self.closed = True
        try:
            self.session.unlisten(self._heard)
        except Exception:                                     # noqa: BLE001
            pass
        self._close_stage(tell=False)
        self._mark_here(False)
        self._remember_place()
        if getattr(sys, _ATTR, None) is self:
            delattr(sys, _ATTR)
        try:
            self.clock.stop()
        except RuntimeError:
            pass
        if not at_once and hubmotion.enabled() and self.root.isVisible():
            origin = W._cursor()
            try:
                if origin is not None and self.burster.run(False, origin, self._gone):
                    return
            except Exception:                                 # noqa: BLE001
                traceback.print_exc()
        self._gone()

    def _gone(self):
        self._end_burst()
        try:
            self.root.hide()
            self.root.deleteLater()
        except RuntimeError:
            pass

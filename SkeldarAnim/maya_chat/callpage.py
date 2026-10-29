"""The call page's host: the composed HTML, the QWebChannel bridge, the web page that grants the
camera, microphone and screen to our own page only.

The page itself is `assets/call/call.html` + `call.css` + `call.js`, inlined into one document with
Qt's own `qwebchannel.js` (read from Qt WebChannel's resources) and loaded at `ORIGIN + "/"`.

Spec: docs/superpowers/specs/2026-10-22-chat-calls-design.md
"""
import json
import os

import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

ORIGIN = "https://skeldar.call"
HOST = "skeldar.call"
COLOURS = ("panel", "card", "line", "text", "muted", "accent", "on_accent", "danger")
_CLASSES = {}


def _q():
    return hubqt.qt()


def folder():
    """Where the page's files are: the plugin's assets/call."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "call")


def _read(name):
    with open(os.path.join(folder(), name), encoding="utf-8") as f:
        return f.read()


def _qwebchannel_js():
    """Qt's qwebchannel.js, from Qt WebChannel's resources (registered when its module loads)."""
    q = _q()
    from PySide6 import QtWebChannel  # noqa: F401  (registers :/qtwebchannel/)
    f = q.QtCore.QFile(":/qtwebchannel/qwebchannel.js")
    if not f.open(q.QtCore.QIODevice.ReadOnly):
        raise RuntimeError("qwebchannel.js is not in this Qt")
    try:
        return bytes(f.readAll()).decode("utf-8")
    finally:
        f.close()


def compose(tokens=None):
    """The page with its CSS, JS and qwebchannel.js inlined and the hub's colours as CSS variables."""
    tokens = tokens or hubstyle.TOKENS
    variables = ":root{" + "".join("--%s:%s;" % (n, tokens.get(n, "#888")) for n in COLOURS) + "}"
    html = _read("call.html")
    html = html.replace("/*CSS*/", variables + _read("call.css"))
    html = html.replace("/*QWEBCHANNEL*/", _qwebchannel_js())
    return html.replace("/*JS*/", _read("call.js"))


def allowed(origin):
    """Whether a page at `origin` (a QUrl or a string) may have the camera, microphone or screen."""
    q = _q()
    url = origin if isinstance(origin, q.QtCore.QUrl) else q.QtCore.QUrl(origin)
    return url.scheme() == "https" and url.host() == HOST and url.port(443) == 443


def bridge_class():
    """`Bridge(on_ready, on_signal, on_state, parent=None)`: the object the page sees as `bridge`.

    Page -> Python: the slots `ready()`, `signal(to, data_json)`, `state(json)`, `log(text)`;
    a `signal` or `state` that is not a JSON object is ignored. Python -> page: `send(name, args)`,
    emitted as the Qt signal `command(name, args_json)`."""
    if "bridge" not in _CLASSES:
        q = _q()
        QtCore = q.QtCore

        class Bridge(QtCore.QObject):
            command = QtCore.Signal(str, str)

            def __init__(self, on_ready, on_signal, on_state, parent=None):
                super(Bridge, self).__init__(parent)
                self.on_ready, self.on_signal, self.on_state = on_ready, on_signal, on_state

            @QtCore.Slot()
            def ready(self):
                self.on_ready()

            @QtCore.Slot(str, str)
            def signal(self, to, data):
                value = _object(data)
                if value is not None:
                    self.on_signal(to, value)

            @QtCore.Slot(str)
            def state(self, text):
                value = _object(text)
                if value is not None:
                    self.on_state(value)

            @QtCore.Slot(str)
            def log(self, text):
                print("[call page] " + text)

            def send(self, name, args=None):
                self.command.emit(name, json.dumps(args or {}))

        _CLASSES["bridge"] = Bridge
    return _CLASSES["bridge"]


def _object(text):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _level(level):
    """A console level as a number, whether Qt hands an enum member or an int."""
    return int(getattr(level, "value", level))


def page_class():
    """`CallPage(profile, parent=None)`: grants media only to ORIGIN, hands a screen request on."""
    if "page" not in _CLASSES:
        q = _q()
        QtCore = q.QtCore
        from PySide6 import QtWebEngineCore

        class CallPage(QtWebEngineCore.QWebEnginePage):
            screen_requested = QtCore.Signal(object)
            stage_requested = QtCore.Signal(object)

            def __init__(self, profile, parent=None):
                super(CallPage, self).__init__(profile, parent)
                self.loaded = False
                self.permissionRequested.connect(self._permission)
                self.desktopMediaRequested.connect(self.screen_requested.emit)
                # The shared screen's own window: the page asks for a Document Picture-in-Picture
                # window and Qt offers it here, so it is built in a frame of ours (callview).
                self.newWindowRequested.connect(self.stage_requested.emit)
                self.loadFinished.connect(self._loaded)

            def _loaded(self, *_args):
                self.loaded = True

            def acceptNavigationRequest(self, url, kind, main_frame):            # noqa: N802
                # Our page is loaded once (setHtml); nothing may take the view anywhere after it,
                # or a page elsewhere would sit where the camera and microphone are granted.
                return not self.loaded

            def _permission(self, permission):
                if allowed(permission.origin()):
                    permission.grant()
                else:
                    permission.deny()

            def javaScriptConsoleMessage(self, level, message, line, source):   # noqa: N802
                # The level is a plain enum.Enum in Maya 2027's PySide6: no ordering, compare values.
                if _level(level) >= _level(_LEVELS().WarningMessageLevel):
                    print("[call page] %s (%s:%s)" % (message, source, line))

        def _LEVELS():                                  # noqa: N802
            return QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel

        _CLASSES["page"] = CallPage
    return _CLASSES["page"]


def make_view(bridge, parent=None):
    """A web view with our page and the bridge on its channel: `(view, page)`.

    The page has an off-the-record profile of its own, owned by the page so it outlives it."""
    q = _q()
    from PySide6 import QtWebChannel, QtWebEngineCore, QtWebEngineWidgets
    view = QtWebEngineWidgets.QWebEngineView(parent)
    view.setAcceptDrops(False)                               # a dropped link would navigate
    profile = QtWebEngineCore.QWebEngineProfile()            # off the record, its own
    page = page_class()(profile, view)
    profile.setParent(page)                                  # deleted after the page, never before
    attrs = QtWebEngineCore.QWebEngineSettings.WebAttribute
    settings = page.settings()
    settings.setAttribute(attrs.PlaybackRequiresUserGesture, False)
    settings.setAttribute(attrs.ScreenCaptureEnabled, True)
    channel = QtWebChannel.QWebChannel(page)
    channel.registerObject("bridge", bridge)
    page.setWebChannel(channel)
    view.setPage(page)
    page.setHtml(compose(), q.QtCore.QUrl(ORIGIN + "/"))
    return view, page

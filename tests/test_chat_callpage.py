"""maya_chat.callpage offscreen: the composed page, the bridge, the permissions."""
import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtWidgets

from maya_chat import callpage


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Compose(unittest.TestCase):
    def test_everything_is_inlined(self):
        _app()
        html = callpage.compose()
        for mark in ("/*CSS*/", "/*JS*/", "/*QWEBCHANNEL*/", "<script src", "<link"):
            self.assertNotIn(mark, html)
        self.assertIn("QWebChannel", html)
        self.assertIn("RTCPeerConnection", html)
        self.assertIn("--accent:", html)

    def test_the_tokens_given_are_the_colours(self):
        _app()
        html = callpage.compose({"accent": "#123456"})
        self.assertIn("--accent:#123456;", html)
        self.assertIn("--panel:#888;", html)

    def test_the_page_files_ship_in_assets(self):
        here = callpage.folder()
        for name in ("call.html", "call.css", "call.js"):
            self.assertTrue(os.path.isfile(os.path.join(here, name)), name)
        self.assertEqual(os.path.basename(os.path.dirname(here)), "assets")


class BridgeTests(unittest.TestCase):
    def test_slots_and_send(self):
        _app()
        got = []
        b = callpage.bridge_class()(lambda: got.append("ready"), lambda to, d: got.append((to, d)),
                                    lambda s: got.append(s))
        sent = []
        b.command.connect(lambda name, args: sent.append((name, json.loads(args))))
        b.ready()
        b.signal("bob", json.dumps({"sdp": "x"}))
        b.state(json.dumps({"mic": True}))
        b.send("mute", {"on": True})
        self.assertEqual(got, ["ready", ("bob", {"sdp": "x"}), {"mic": True}])
        self.assertEqual(sent, [("mute", {"on": True})])

    def test_a_bad_json_from_the_page_is_ignored(self):
        _app()
        got = []
        b = callpage.bridge_class()(lambda: None, lambda to, d: got.append(d), lambda s: got.append(s))
        b.signal("bob", "{not json")
        b.state("nope")
        b.state("[1, 2]")
        self.assertEqual(got, [])


class Permissions(unittest.TestCase):
    def test_only_our_origin(self):
        self.assertTrue(callpage.allowed(QtCore.QUrl("https://skeldar.call/")))
        self.assertTrue(callpage.allowed(QtCore.QUrl("https://skeldar.call")))
        self.assertFalse(callpage.allowed(QtCore.QUrl("https://evil.example/")))
        self.assertFalse(callpage.allowed(QtCore.QUrl("http://skeldar.call/")))
        self.assertFalse(callpage.allowed(QtCore.QUrl("https://skeldar.call.evil.example/")))
        self.assertFalse(callpage.allowed("https://evil.example/"))


class ConsoleMessages(unittest.TestCase):
    def test_warnings_and_errors_are_printed_info_is_not(self):
        import contextlib
        import io
        _app()
        from PySide6 import QtWebEngineCore
        levels = QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel
        override = callpage.page_class().javaScriptConsoleMessage     # its self is not used
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            override(None, levels.InfoMessageLevel, "info", 1, "call.js")
            override(None, levels.WarningMessageLevel, "warn", 2, "call.js")
            override(None, levels.ErrorMessageLevel, "boom", 3, "call.js")
        text = out.getvalue()
        self.assertNotIn("info", text)
        self.assertIn("[call page] warn (call.js:2)", text)
        self.assertIn("[call page] boom (call.js:3)", text)


class Navigation(unittest.TestCase):
    def test_only_the_first_load_may_navigate(self):
        _app()
        accept = callpage.page_class().acceptNavigationRequest

        class Fake(object):
            loaded = False
        page = Fake()
        url = QtCore.QUrl("https://skeldar.call/")
        self.assertTrue(accept(page, url, 0, True))
        page.loaded = True
        self.assertFalse(accept(page, QtCore.QUrl("https://evil.example/"), 0, True))
        self.assertFalse(accept(page, url, 0, True))

    def test_the_loaded_flag_follows_load_finished(self):
        _app()
        cls = callpage.page_class()

        class Fake(object):
            loaded = False
        page = Fake()
        cls._loaded(page, True)
        self.assertTrue(page.loaded)


class Page(unittest.TestCase):
    def test_a_late_signal_cannot_bring_back_one_who_left(self):
        js = open(os.path.join(callpage.folder(), "call.js"), encoding="utf-8").read()
        self.assertIn("S.left.has(from)", js)
        self.assertIn("S.left.add(uid)", js)
        self.assertIn("S.left.delete(a.uid)", js)
        self.assertIn("S.ended = true", js)


if __name__ == "__main__":
    unittest.main()

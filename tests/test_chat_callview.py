"""maya_chat.callview offscreen on a fake session and a fake page."""
import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtWidgets

import maya_hubmotion as hubmotion
from maya_chat import callview as V
from maya_chat import session as S

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def view(state="ringing", members=("me",), cid="c-1", **kw):
    v = {"id": "c1", "chat": "dm", "by": "me", "kind": "video", "cid": cid, "state": state,
         "members": list(members), "declined": [], "started_at": int(time.time() * 1000),
         "answered_at": None, "ended_at": None}
    v.update(kw)
    return v


class FakeSession(object):
    def __init__(self):
        self.state = S.State()
        self.state.me = ME
        self.state.chats = {"dm": {"id": "dm", "kind": "dm", "name": "", "members": [ME, BOB]}}
        self.listeners, self.calls = [], []

    def listen(self, fn):
        self.listeners.append(fn)

    def unlisten(self, fn):
        if fn in self.listeners:
            self.listeners.remove(fn)

    def tell(self, kind, data):
        for fn in list(self.listeners):
            fn(kind, data)

    def start_call(self, chat, kind):
        self.calls.append(("start", chat, kind))
        return "c-1"

    def join_call(self, call_id):
        self.calls.append(("join", call_id))
        return "j-1"

    def leave_call(self, call_id):
        self.calls.append(("leave", call_id))
        return True

    def call_signal(self, call_id, to, data):
        self.calls.append(("signal", call_id, to, data))
        return True

    def turn_servers(self, now=None):
        return [{"urls": ["stun:x"]}], False


class FakePage(object):
    def __init__(self):
        from PySide6 import QtCore

        class Sig(QtCore.QObject):
            screen_requested = QtCore.Signal(object)
        self.sig = Sig()
        self.screen_requested = self.sig.screen_requested


def fake_factory(store):
    def make(bridge, parent):
        store["bridge"] = bridge
        store["sent"] = sent = []
        bridge.command.connect(lambda name, args: sent.append((name, __import__("json").loads(args))))
        return QtWidgets.QWidget(parent), FakePage()
    return make


class Base(unittest.TestCase):
    def setUp(self):
        _app()
        V._VARS.clear()
        self.ses = FakeSession()
        self.store = {}

    def tearDown(self):
        V.destroy()

    def sent(self, name):
        return [a for n, a in self.store.get("sent", []) if n == name]


class Starting(Base):
    def test_start_rings_then_starts_the_page_alone(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.assertEqual(self.ses.calls, [("start", "dm", "video")])
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        self.assertEqual(w.call_id, "c1")
        starts = self.sent("start")
        self.assertEqual(len(starts), 1)
        self.assertEqual((starts[0]["me"], starts[0]["peers"], starts[0]["video"]), ("me", [], True))

    def test_the_answerer_joins_and_offers(self):
        w = V.answer(self.ses, "c1", "audio", view_factory=fake_factory(self.store))
        self.assertEqual(self.ses.calls, [("join", "c1")])
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("bob", "me"), by="bob")})
        st = self.sent("start")[0]
        self.assertEqual((st["peers"], st["offer_to"], st["video"]), (["bob"], ["bob"], False))

    def test_signals_go_both_ways_and_early_ones_wait_for_start(self):
        w = V.answer(self.ses, "c1", "video", view_factory=fake_factory(self.store))
        self.ses.tell("call_signal", {"kind": "call_signal", "call": "c1", "from": "bob", "data": {"sdp": "o"}})
        self.assertEqual(self.sent("signal"), [])                    # before start: held
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("bob", "me"), by="bob")})
        self.assertEqual(self.sent("signal"), [{"from": "bob", "data": {"sdp": "o"}}])
        self.store["bridge"].signal("bob", '{"ice": {"candidate": "x"}}')
        self.assertIn(("signal", "c1", "bob", {"ice": {"candidate": "x"}}), self.ses.calls)

    def test_newcomers_and_leavers(self):
        V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me", "bob"))})
        self.assertEqual(self.sent("add_peer"), [{"uid": "bob", "offer": False}])
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me",))})
        self.assertEqual(self.sent("remove_peer"), [{"uid": "bob"}])

    def test_the_end_closes_the_window(self):
        w = V.start(self.ses, "dm", "audio", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("call", {"kind": "call", "call": view("ended", ())})
        self.assertIsNone(V.current())
        self.assertIn("end", [n for n, _a in self.store["sent"]])

    def test_a_refused_start_closes_and_says_why(self):
        w = V.start(self.ses, "dm", "audio", view_factory=fake_factory(self.store))
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("error", {"kind": "error", "cid": "c-1", "code": "call_exists", "text": "join it"})
        self.assertIsNone(V.current())
        self.assertIn("join it", w.last_message)


class Buttons(Base):
    def live(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me", "bob"))})
        self.store["bridge"].state('{"mic": true, "cam": true, "screen": false, "devices": '
                                   '{"mics": [{"id": "m1", "label": "Mic"}], "cams": []}, "peers": {}}')
        return w

    def test_mic_camera_screen(self):
        w = self.live()
        w.press("mic")
        w.press("camera")
        w.press("screen")
        self.assertEqual(self.sent("mute"), [{"on": True}])
        self.assertEqual(self.sent("camera"), [{"on": False}])
        self.assertEqual(self.sent("screen"), [{"on": True}])

    def test_hang_up_leaves(self):
        w = self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w.press("hang_up")
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertIsNone(V.current())

    def test_fold_and_unfold(self):
        w = self.live()
        w.press("fold")
        self.assertTrue(w.folded)
        self.assertLessEqual(w.root.width(), w.px(260))
        w.fold(False)
        self.assertFalse(w.folded)

    def test_a_device_choice_is_remembered_and_sent(self):
        w = self.live()
        w.choose_device("mic", "m1")
        self.assertEqual(V.get_var(V.MIC_VAR), "m1")
        self.assertEqual(self.sent("devices")[-1], {"mic": "m1", "cam": ""})

    def test_one_call_at_a_time(self):
        self.live()
        with mock.patch.object(V, "_ask_switch", return_value=False):
            self.assertIsNone(V.start(self.ses, "dm", "audio", view_factory=fake_factory({})))
        with mock.patch.object(V, "_ask_switch", return_value=True), \
                mock.patch.object(hubmotion, "enabled", return_value=False):
            w2 = V.start(self.ses, "dm", "audio", view_factory=fake_factory({}))
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertIs(V.current(), w2)


class FakeRequest(object):
    """A QWebEngineDesktopMediaRequest stand-in: a screen and a window to choose from."""

    def __init__(self):
        from PySide6 import QtGui
        self.screens = QtGui.QStandardItemModel()
        self.screens.appendRow(QtGui.QStandardItem("Screen 1"))
        self.windows = QtGui.QStandardItemModel()
        self.windows.appendRow(QtGui.QStandardItem("Maya"))
        self.done = []

    def screensModel(self):                                    # noqa: N802
        return self.screens

    def windowsModel(self):                                    # noqa: N802
        return self.windows

    def selectScreen(self, index):                             # noqa: N802
        self.done.append(("screen", index.row()))

    def selectWindow(self, index):                             # noqa: N802
        self.done.append(("window", index.row()))

    def cancel(self):
        self.done.append(("cancel",))


class Screens(Base):
    def test_the_picker_offers_screens_and_windows(self):
        self.assertEqual([(t, r) for t, r, _l in V.screen_choices(FakeRequest())],
                         [("screen", 0), ("window", 0)])

    def test_a_choice_selects_it_and_none_cancels(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        req = FakeRequest()
        with mock.patch.object(V, "_pick_screen", return_value=("window", 0)):
            w.page.screen_requested.emit(req)
        self.assertEqual(req.done, [("window", 0)])
        req = FakeRequest()
        with mock.patch.object(V, "_pick_screen", return_value=None):
            w.page.screen_requested.emit(req)
        self.assertEqual(req.done, [("cancel",)])


class Edges(Base):
    def test_a_call_ended_elsewhere_while_ringing_closes(self):
        V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.ses.tell("call", {"kind": "call", "call": view()})
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("call", {"kind": "call", "call": view("ended", ())})
        self.assertIsNone(V.current())

    def test_another_call_s_events_are_ignored(self):
        w = V.answer(self.ses, "c1", "audio", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("x", "me"), id="c9", cid="z")})
        self.assertEqual(self.sent("start"), [])
        self.assertIs(V.current(), w)

    def test_the_mic_icon_follows_the_page(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].state('{"mic": false, "cam": false, "screen": true}')
        self.assertEqual(w.icons["mic"], "microphone-off")
        self.assertEqual(w.icons["camera"], "video-off")
        self.assertEqual(w.icons["screen"], "screen-share-off")

    def test_the_place_is_remembered(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        w.root.move(120, 80)
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w.close_window()
        self.assertEqual(V.get_var(V.POS_VAR), "120,80")
        self.assertTrue(V.get_var(V.SIZE_VAR))

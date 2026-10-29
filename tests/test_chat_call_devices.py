"""A call survives its microphone (2026-10-29): the remembered device goes as an id AND a label,
and nothing about a microphone ends a call.

The animator: «У меня случился баг при переключении беспроводных наушников. мая говорит что
микрофон не найден и отклоняет звонки и я ничего не слышал когда мне звонили». Their prefs held
`skeldarChatCallMic` from an earlier Maya session, and Chromium salts a deviceId per origin: the
page asked for that id `exact`, got OverconstrainedError, and the window LEFT the call.

The page's own half (the ideal ask, the label resolved, a call joined with no microphone, the
device change followed) is proven live by docs/superpowers/plans/verify_call_devices.py: this is
the Python around it. Spec: docs/superpowers/specs/2026-10-29-call-devices-design.md
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtWidgets  # noqa: E402

import maya_hubmotion as hubmotion  # noqa: E402
import maya_hubsound  # noqa: E402
from maya_chat import calls  # noqa: E402
from maya_chat import callview as V  # noqa: E402

from tests.test_chat_callview import FakeSession, fake_factory, view  # noqa: E402


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class StartArgs(unittest.TestCase):
    def test_the_remembered_device_goes_as_an_id_and_a_label(self):
        args = calls.start_args(view(state="live", members=("a", "b")), "b", {}, [], False,
                                mic="m1", cam="c1", mic_label="Desk mic", cam_label="Webcam")
        self.assertEqual((args["mic"], args["mic_label"]), ("m1", "Desk mic"))
        self.assertEqual((args["cam"], args["cam_label"]), ("c1", "Webcam"))

    def test_without_them_the_labels_are_empty(self):
        args = calls.start_args(view(), "a", {}, [], False)
        self.assertEqual((args["mic_label"], args["cam_label"]), ("", ""))


class Start(unittest.TestCase):
    def setUp(self):
        _app()
        V._VARS.clear()
        self.ses = FakeSession()
        self.store = {}

    def tearDown(self):
        V.destroy()
        V._VARS.clear()

    def live(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me", "bob"))})
        return w

    def sent(self, name):
        return [a for n, a in self.store.get("sent", []) if n == name]

    def test_the_page_is_started_with_both_remembered_devices(self):
        V.set_var(V.MIC_VAR, "m1")
        V.set_var(V.MIC_LABEL_VAR, "Desk mic")
        V.set_var(V.CAM_VAR, "c1")
        V.set_var(V.CAM_LABEL_VAR, "Webcam")
        self.live()
        args = self.sent("start")[-1]
        self.assertEqual((args["mic"], args["mic_label"]), ("m1", "Desk mic"))
        self.assertEqual((args["cam"], args["cam_label"]), ("c1", "Webcam"))

    def test_a_page_with_no_microphone_is_said_once_and_kept(self):
        w = self.live()
        said = []
        line = u"Микрофон не найден (NotFoundError)"
        with mock.patch.object(w, "say", lambda text: said.append(text)):
            #  the page says it in its note; the window keeps the call and says it once
            for _ in range(2):
                self.store["bridge"].state(
                    u'{"nomic": "NotFoundError", "note": "%s", "peers": {}}' % line)
        self.assertFalse(w.closed)
        self.assertNotIn(("leave", "c1"), self.ses.calls)
        self.assertEqual(said, [line])

    def test_the_microphone_state_is_logged_when_it_changes(self):
        w = self.live()
        from maya_chat import callpage
        lines = []
        with mock.patch.object(callpage, "log", lambda text: lines.append(text)):
            self.store["bridge"].state(u'{"nomic": "NotFoundError", "peers": {}}')
            self.store["bridge"].state(u'{"nomic": "NotFoundError", "peers": {}}')
            self.store["bridge"].state(u'{"nomic": "", "peers": {}}')
        self.assertEqual(len([t for t in lines if "no microphone" in t]), 1,
                         "the same state is not said twice")
        self.assertTrue(any("microphone: ok" in t for t in lines))
        self.assertFalse(w.closed)

    def test_a_page_error_that_is_not_about_a_device_is_logged_not_fatal(self):
        w = self.live()
        from maya_chat import callpage
        lines = []
        with mock.patch.object(callpage, "log", lambda text: lines.append(text)):
            self.store["bridge"].state(u'{"error": "offer: boom", "peers": {}}')
        self.assertTrue(any("offer: boom" in t for t in lines))
        self.assertFalse(w.closed)


class SoundDevices(unittest.TestCase):
    """The cached pools are dropped when the audio outputs change: a QSoundEffect builds its sink
    on the default device of the moment and Qt does not move a built one."""

    def setUp(self):
        _app()
        maya_hubsound.reset()

    def tearDown(self):
        maya_hubsound.reset()

    def test_forget_players_empties_the_cache(self):
        maya_hubsound._state()["players"]["drag"] = ("key", object())
        maya_hubsound.forget_players()
        self.assertEqual(maya_hubsound._state()["players"], {})

    def test_the_watcher_is_made_once_and_its_signal_forgets_them(self):
        maya_hubsound._watch_devices()
        watch = maya_hubsound._state()["devices"]
        self.assertTrue(watch, "QMediaDevices is in this Qt")
        maya_hubsound._watch_devices()
        self.assertIs(maya_hubsound._state()["devices"], watch)
        maya_hubsound._state()["players"]["drag"] = ("key", object())
        watch.audioOutputsChanged.emit()
        self.assertEqual(maya_hubsound._state()["players"], {})

    def test_a_player_asked_for_starts_the_watch(self):
        maya_hubsound._player("drag")
        self.assertIsNotNone(maya_hubsound._state()["devices"])

    def test_without_an_application_the_watch_waits(self):
        with mock.patch.object(QtWidgets.QApplication, "instance", staticmethod(lambda: None)), \
                mock.patch("PySide6.QtCore.QCoreApplication.instance", staticmethod(lambda: None)):
            maya_hubsound._watch_devices()
        self.assertIsNone(maya_hubsound._state()["devices"],
                          "asked again once there is an application")


if __name__ == "__main__":
    unittest.main()

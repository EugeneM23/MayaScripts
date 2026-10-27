"""maya_chat.callview: what test_chat_callview.py does not reach - the question before a second
call, the screen and device menus (their exec answered by the test), the title's drag and click,
the burst, the clock line, the buttons by their clicks. A fake session and a fake page; no
QWebEngine page is loaded and nothing reaches a server."""
import contextlib
import os
import sys
import time
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtWidgets  # noqa: E402

import maya_hubburst  # noqa: E402
import maya_hubmotion as hubmotion  # noqa: E402
from maya_chat import callview as V  # noqa: E402
from maya_chat import toast  # noqa: E402

from tests.test_chat_callview import FakeRequest, FakeSession, fake_factory, view  # noqa: E402

MISSING = object()


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Base(unittest.TestCase):
    def setUp(self):
        _app()
        V._VARS.clear()
        self.ses = FakeSession()
        self.store = {}
        self._toasts = getattr(sys, "_skeldar_chat_toasts", MISSING)
        toast.clear()

    def tearDown(self):
        V.destroy()
        toast.clear()
        QtWidgets.QApplication.processEvents()
        if self._toasts is MISSING:
            if hasattr(sys, "_skeldar_chat_toasts"):
                delattr(sys, "_skeldar_chat_toasts")
        else:
            sys._skeldar_chat_toasts = self._toasts

    def swap(self, obj, name, value):
        old = getattr(obj, name, MISSING)
        setattr(obj, name, value)
        self.addCleanup(lambda: setattr(obj, name, old) if old is not MISSING
                        else delattr(obj, name))

    def sent(self, name):
        return [a for n, a in self.store.get("sent", []) if n == name]

    def live(self, members=("me", "bob"), **kw):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", members, **kw)})
        return w


class _Widgets(object):
    """QtWidgets with QMenu a subclass whose exec the test answers: a Shiboken class attribute
    patched on QMenu is not what an instance's exec calls, and a real exec would block."""

    def __init__(self, menu_class):
        self.QMenu = menu_class

    def __getattr__(self, name):
        return getattr(QtWidgets, name)


@contextlib.contextmanager
def answered_menus(pick):
    """Every QMenu callview builds meanwhile: `pick(menu)` chooses the action exec returns
    (None: the menu closed)."""
    class Menu(QtWidgets.QMenu):
        def exec(self, *args, **kwargs):            # noqa: A003
            return pick(self)
    real = V.W._q
    q = real()
    fake = types.SimpleNamespace(QtCore=q.QtCore, QtGui=q.QtGui, QtWidgets=_Widgets(Menu))
    V.W._q = lambda: fake
    try:
        yield
    finally:
        V.W._q = real


def rows(menu):
    return [a for a in menu.actions() if not a.isSeparator() and a.text()]


def triggering(choose):
    """A pick that triggers what `choose(actions)` returns, as a click on it would."""
    def pick(menu):
        chosen = choose(rows(menu))
        if chosen is not None:
            chosen.trigger()
        return chosen
    return pick


class Switching(Base):
    def test_the_question_s_answer(self):
        box = QtWidgets.QMessageBox
        with mock.patch.object(box, "question", return_value=box.Yes) as asked:
            self.assertTrue(V._ask_switch(None))
        self.assertEqual(asked.call_args[0][1], u"Звонок")
        with mock.patch.object(box, "question", return_value=box.No):
            self.assertFalse(V._ask_switch(None))

    def test_a_second_answer_keeps_the_first_call_when_told_no(self):
        w = self.live()
        with mock.patch.object(V, "_ask_switch", return_value=False):
            self.assertIsNone(V.answer(self.ses, "c2", "audio",
                                       view_factory=fake_factory({})))
        self.assertIs(V.current(), w)

    def test_hang_up_ends_the_standing_call_and_nothing_without_one(self):
        self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            V.hang_up()
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertIsNone(V.current())
        V.hang_up()                                    # no call: nothing

    def test_a_refused_answer_closes_and_says_why(self):
        def refuse(call_id):
            from maya_chat import api
            raise api.ChatError("call_full", "full")
        self.ses.join_call = refuse
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.assertIsNone(V.answer(self.ses, "c1", "audio",
                                       view_factory=fake_factory(self.store)))
        self.assertIsNone(V.current())
        self.assertNotIn(("leave", "c1"), self.ses.calls, "never in it: nothing to leave")


class ScreenMenu(Base):
    def test_screens_then_windows_under_their_headings_and_a_pick(self):
        w = self.live()
        choices = V.screen_choices(FakeRequest())
        sections = []

        def pick(menu):
            sections.extend(a.text() for a in menu.actions() if a.isSeparator())
            return [a for a in menu.actions() if a.text() == "Maya"][0]
        with answered_menus(pick):
            self.assertEqual(V._pick_screen(w, choices), ("window", 0))
        self.assertEqual(sections, [u"Экран", u"Окно"])

    def test_closing_the_menu_picks_nothing(self):
        w = self.live()
        with answered_menus(lambda menu: None):
            self.assertIsNone(V._pick_screen(w, V.screen_choices(FakeRequest())))

    def test_a_request_for_a_screen_by_the_menu(self):
        w = self.live()
        req = FakeRequest()
        with answered_menus(triggering(lambda acts: acts[0])):
            w.page.screen_requested.emit(req)
        self.assertEqual(req.done, [("screen", 0)])

    def test_a_request_that_breaks_is_cancelled(self):
        w = self.live()
        req = FakeRequest()
        self.swap(V, "_pick_screen", lambda win, choices: 1 / 0)
        with mock.patch("traceback.print_exc"):
            w.page.screen_requested.emit(req)
        self.assertEqual(req.done, [("cancel",)])

    def test_unnamed_rows_get_numbers_and_a_request_without_models_offers_nothing(self):
        req = FakeRequest()
        from PySide6 import QtGui
        req.screens.appendRow(QtGui.QStandardItem(""))
        self.assertIn(("screen", 1, u"Экран 2"), V.screen_choices(req))

        class Bare(object):
            pass
        self.assertEqual(V.screen_choices(Bare()), [])


class Devices(Base):
    def test_the_devices_menu_marks_the_chosen_and_a_pick_is_sent(self):
        w = self.live()
        self.store["bridge"].state(
            '{"mic": true, "devices": {"mics": [{"id": "m1", "label": "Desk mic"},'
            ' {"id": "m2", "label": ""}], "cams": [{"id": "c1", "label": "Cam"}]}}')
        V.set_var(V.MIC_VAR, "m1")
        seen = {}

        def pick(acts):
            seen.update((a.text(), a.isChecked()) for a in acts)
            return [a for a in acts if a.text() == "Cam"][0]
        with answered_menus(triggering(pick)):
            w.buttons["settings"].click()
        self.assertTrue(seen["Desk mic"])
        self.assertFalse(seen["m2"], "a device without a label shows its id")
        self.assertEqual(V.get_var(V.CAM_VAR), "c1")
        self.assertEqual(self.sent("devices")[-1], {"mic": "m1", "cam": "c1"})

    def test_no_devices_is_a_disabled_row(self):
        w = self.live()
        seen = []

        def pick(menu):
            seen.extend((x.text(), x.isEnabled()) for x in menu.actions()
                        if not x.isSeparator())
            return None
        with answered_menus(pick):
            w.press("settings")
        self.assertEqual(seen.count((u"нет устройств", False)), 2)


class Buttons(Base):
    def test_every_button_by_its_click(self):
        w = self.live()
        self.store["bridge"].state('{"mic": true, "cam": false, "screen": false}')
        w.buttons["mic"].click()
        w.buttons["camera"].click()
        w.buttons["screen"].click()
        w.buttons["fold"].click()
        self.assertTrue(w.folded)
        self.assertEqual([name for name, b in w.buttons.items() if not b.isHidden()],
                         ["fold", "hang_up"])
        w.buttons["fold"].click()
        self.assertFalse(w.folded)
        self.assertEqual(self.sent("mute"), [{"on": True}])
        self.assertEqual(self.sent("camera"), [{"on": True}])
        self.assertEqual(self.sent("screen"), [{"on": True}])
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w.root.findChild(QtWidgets.QAbstractButton, "skeldarChatCallClose").click()
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertTrue(w.closed)

    def test_a_folded_tile_unfolds_by_its_title_and_does_not_remember_its_tile(self):
        w = self.live()
        w.root.setGeometry(200, 150, 700, 480)
        w.fold(True)
        w.fold(True)                                   # already: nothing
        w._grab((210, 155))
        w._drag((310, 255))
        self.assertEqual((w.root.x(), w.root.y()), (300, 250))
        w._drop()
        self.assertIsNone(V.get_var(V.POS_VAR), "a folded tile's place is not the window's")
        w._title_click()
        self.assertFalse(w.folded)
        self.assertEqual((w.root.width(), w.root.height()), (700, 480))
        w._grab((210, 155))
        w._drag((260, 205))
        w._drop()
        self.assertEqual(V.get_var(V.POS_VAR), "%d,%d" % (w.root.x(), w.root.y()))
        w._title_click()                               # unfolded: nothing
        self.assertFalse(w.folded)

    def test_a_note_while_folded_waits_and_shows_on_unfold(self):
        w = self.live()
        w.fold(True)
        w.say(u"плохая связь")
        self.assertTrue(w.note_label.isHidden())
        w.fold(False)
        self.assertFalse(w.note_label.isHidden())


class Clock(Base):
    def test_ringing_then_the_minutes_since_the_answer(self):
        w = self.live()
        w.answered_at = None
        w._tick()
        self.assertEqual(w.timer_label.text(), u"вызов…")
        w.answered_at = (time.time() - 125) * 1000.0
        w._tick()
        self.assertEqual(w.timer_label.text(), "2:05")

    def test_a_closed_window_s_clock_does_nothing(self):
        w = self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w.close_window()
        w.timer_label = None                           # would raise if touched
        w._tick()

    def test_the_answered_time_comes_with_the_view(self):
        w = self.live(answered_at=int(time.time() * 1000) - 61000)
        w._tick()
        self.assertEqual(w.timer_label.text(), "1:01")


class Events(Base):
    def test_an_error_for_my_start_closes_and_says_it(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
            self.ses.tell("error", {"cid": "c-1", "code": "call_exists", "text": "x"})
        self.assertTrue(w.closed)
        self.assertEqual(w.last_message, V.REFUSALS["call_exists"])
        self.assertNotIn(("leave", "c1"), self.ses.calls)

    def test_an_error_for_another_send_is_not_mine(self):
        w = self.live()
        self.ses.tell("error", {"cid": "other", "code": "too_many"})
        self.assertFalse(w.closed)

    def test_hanging_up_before_the_ack_leaves_once_it_is_known(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
            w.hang_up()
        self.ses.tell("call", {"kind": "call", "call": view("ringing", ("me",), cid="other")})
        self.assertNotIn(("leave", "c1"), self.ses.calls, "another start: not mine")
        self.ses.tell("call", {"kind": "call", "call": view("ringing", ("me",))})
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.ses.tell("call", {"kind": "call", "call": view("ringing", ("me",))})
        self.assertEqual(self.ses.calls.count(("leave", "c1")), 1, "once: it listens no more")

    def test_an_error_for_a_hung_up_start_stops_listening(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
            w.hang_up()
        before = len(self.ses.listeners)
        self.ses.tell("error", {"cid": "c-1", "code": "no_call"})
        self.assertEqual(len(self.ses.listeners), before - 1)

    def test_left_from_elsewhere_closes_the_window(self):
        w = self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("call", {"kind": "call", "call": view("live", ("bob",))})
        self.assertTrue(w.closed)
        self.assertEqual(self.sent("end"), [{}])

    def test_a_mic_error_with_nobody_in_ends_the_call(self):
        w = self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.store["bridge"].state(u'{"error": "Микрофон недоступен", "peers": {}}')
        self.assertTrue(w.closed)
        self.assertIn(("leave", "c1"), self.ses.calls)


class Burst(Base):
    def drive(self, w):
        self.assertIsNotNone(w.burster.anim)
        w.burster._tick(10 ** 6)
        self.assertIsNone(w.burster.anim)

    def test_the_window_bursts_out_of_a_point_and_folds_away(self):
        self.swap(maya_hubburst, "MOTION", "burst")
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
            self.assertTrue(w.root.isVisible())
            self.drive(w)
            self.assertTrue(w._burst_parts())
            self.assertEqual(w._burst_face(), V.hubstyle.TOKENS["panel"])
            with mock.patch.object(V.W, "_cursor", return_value=(300, 200)):
                w.close_window()
            self.assertTrue(w.closed)
            self.drive(w)
        self.assertFalse(w.root.isVisible())

    def test_a_burst_that_raises_shows_the_window_at_once(self):
        w = self.live()
        w.root.hide()

        def broken(*a, **k):
            raise RuntimeError("no effect")
        w.burster.run = broken
        with mock.patch.object(hubmotion, "enabled", return_value=True), \
                mock.patch("traceback.print_exc"):
            w.show((10, 10))
            self.assertTrue(w.root.isVisible())
            with mock.patch.object(V.W, "_cursor", return_value=(300, 200)):
                w.close_window()
        self.assertFalse(w.root.isVisible())


class Place(Base):
    def test_with_no_place_remembered_it_stands_on_maya_s_window(self):
        main = QtWidgets.QWidget()
        main.setGeometry(100, 100, 1000, 800)
        self.addCleanup(main.deleteLater)
        self.swap(V.W, "_main_window", lambda: main)
        w = self.live()
        g = main.frameGeometry()
        self.assertEqual(w.root.x() + w.root.width() // 2, g.x() + g.width() // 2)

    def test_a_place_on_screen_is_kept(self):
        V.set_var(V.POS_VAR, "150,120")
        V.set_var(V.SIZE_VAR, "700,500")
        self.swap(V.W, "_screens", lambda: [(0, 0, 1920, 1080)])
        w = self.live()
        self.assertEqual((w.root.x(), w.root.y(), w.root.width()), (150, 120, 700))


if __name__ == "__main__":
    unittest.main()

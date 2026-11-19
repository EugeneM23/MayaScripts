"""maya_chat.toast: the message card under the mouse, its stay, the call card's buttons, the
stack, and the presses that go to the window or the session. Offscreen; a stay's end is its
timer's timeout emitted by hand (no sleeps), the session and the call window are fakes. Nothing
moves: a card stands at its place at once and goes at once (2026-11-19)."""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_hubedge  # noqa: E402
from maya_chat import callview  # noqa: E402
from maya_chat import look  # noqa: E402
from maya_chat import notify  # noqa: E402
from maya_chat import toast  # noqa: E402
from maya_chat import window as W  # noqa: E402

MISSING = object()
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def mouse(kind, pos, button=QtCore.Qt.LeftButton, buttons=None):
    pos = QtCore.QPointF(pos)
    return QtGui.QMouseEvent(kind, pos, pos, button, button if buttons is None else buttons,
                             QtCore.Qt.NoModifier)


def call(**kw):
    v = {"id": "c1", "chat": "dm", "by": "bob", "kind": "video", "cid": "x", "state": "ringing",
         "members": ["bob"], "declined": [], "started_at": 0, "answered_at": None,
         "ended_at": None}
    v.update(kw)
    return v


def render(widget):
    image = QtGui.QImage(widget.size(), QtGui.QImage.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


class FakeSession(object):
    def __init__(self):
        self.declined = []

        class State(object):
            online = {"bob": {"online": True}}
        self.state = State()

    def decline_call(self, call_id):
        self.declined.append(call_id)
        return True


class Base(unittest.TestCase):
    def setUp(self):
        _app()
        self._held = {}
        for name in ("_skeldar_chat_toasts", "_skeldar_chat"):
            self._held[name] = getattr(sys, name, MISSING)
        sys._skeldar_chat = self.ses = FakeSession()
        toast.clear()

    def tearDown(self):
        toast.clear()
        QtWidgets.QApplication.processEvents()
        for name, old in self._held.items():
            if old is MISSING:
                if hasattr(sys, name):
                    delattr(sys, name)
            else:
                setattr(sys, name, old)

    def swap(self, obj, name, value):
        old = getattr(obj, name, MISSING)
        setattr(obj, name, value)
        self.addCleanup(lambda: setattr(obj, name, old) if old is not MISSING
                        else delattr(obj, name))


class MessageCard(Base):
    def test_it_stands_at_once_and_its_stay_counts_on_its_own_timer(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.assertTrue(card.isVisible())
        self.assertTrue(card.stay.isActive())
        self.assertTrue(card.stay.isSingleShot())
        self.assertNotIn("timer", toast._state(), "no motion timer for the stack")

    def test_under_the_mouse_it_is_held_and_leaving_gives_it_time_again(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        card.enterEvent(QtCore.QEvent(QtCore.QEvent.Enter))
        self.assertTrue(card.hover)
        self.assertFalse(card.stay.isActive(), "held: the stay does not count down")
        card.stay_left = 10.0
        self.assertIsNone(card.leaving)
        card.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertFalse(card.hover)
        self.assertGreaterEqual(card.stay_left, 1500.0)
        self.assertTrue(card.stay.isActive())
        self.assertGreater(card.stay.remainingTime(), 1000)

    def test_a_second_message_of_the_same_chat_gives_the_whole_stay_again(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        card.stay_left = 5.0
        again = toast.show("dm", BOB, "Bob", "more")
        self.assertIs(again, card)
        self.assertEqual(card.stay_left, float(look.TOAST_STAY_MS))
        self.assertTrue(card.stay.isActive())

    def test_the_stay_over_it_goes_at_once(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        card.stay.timeout.emit()
        self.assertTrue(card.leaving)
        self.assertEqual(toast.cards(), [])
        self.assertFalse(card.isVisible())

    def test_the_cross_lights_under_the_mouse_and_dismisses(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        cross = card.cross_rect().center()
        card.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, cross, QtCore.Qt.NoButton))
        self.assertTrue(card.cross_hover)
        lit = render(card)
        card.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, QtCore.QPointF(20, 20),
                                  QtCore.Qt.NoButton))
        self.assertFalse(card.cross_hover)
        plain = render(card)
        r = card.cross_rect().toRect()
        self.assertNotEqual([lit.pixelColor(x, y) for x in range(r.left(), r.right())
                             for y in range(r.top(), r.bottom())],
                            [plain.pixelColor(x, y) for x in range(r.left(), r.right())
                             for y in range(r.top(), r.bottom())])
        opened = []
        self.swap(toast, "open_chat", opened.append)
        card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, cross))
        self.assertIsNotNone(card.leaving)
        self.assertEqual(opened, [], "the cross only dismisses")

    def test_the_right_button_dismisses_too(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        opened = []
        self.swap(toast, "open_chat", opened.append)
        card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(60, 20),
                                   QtCore.Qt.RightButton))
        self.assertIsNotNone(card.leaving)
        self.assertEqual(opened, [])

    def test_a_hovered_card_paints_its_lit_face(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        plain = render(card).pixelColor(card.cw - 40, card.height() // 2)
        card.hover = True
        lit = render(card).pixelColor(card.cw - 40, card.height() // 2)
        self.assertNotEqual(plain, lit)

    def test_a_card_goes_to_its_place_at_once(self):
        card = toast.card_class()("dm", BOB, "Bob", "hi")
        card.go_to(30, 40)
        self.assertEqual(card.pos(), QtCore.QPoint(30, 40))
        card.go_to(30, 40)                                  # the same place again: unchanged
        self.assertEqual(card.pos(), QtCore.QPoint(30, 40))
        card.deleteLater()

    def test_a_card_that_leaves_is_taken_away_and_the_one_above_steps_down(self):
        older = toast.show("dm", BOB, "Bob", "hi")
        newer = toast.show("dm2", BOB, "Bob", "there")
        bottom = newer.y()
        self.assertLess(older.y(), bottom)
        newer.leave()
        self.assertEqual(toast.cards(), [older])
        self.assertEqual(older.y(), bottom, "at once, no easing")
        newer.leave()                                       # twice: nothing more
        self.assertEqual(toast.cards(), [older])

    def test_nothing_of_the_motion_is_left(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        for gone in ("tick", "fly_from", "flying", "moving", "gone", "born", "flash_at",
                     "place_to", "trail"):
            self.assertFalse(hasattr(card, gone), gone)
        for gone in ("_tick", "_wake", "_fly_in", "_animations", "HOVER_MS"):
            self.assertFalse(hasattr(toast, gone), gone)
        for gone in ("TOAST_IN_MS", "TOAST_OUT_MS", "TOAST_FLASH_MS", "TOAST_MOVE_MS",
                     "TOAST_FLY_MS", "toast_fly", "toast_trail", "toast_look", "ease_out"):
            self.assertFalse(hasattr(look, gone), gone)

    def test_an_older_build_s_state_is_dropped_with_its_timer_stopped(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        st = toast._state()
        timer = QtCore.QTimer()
        timer.start(16)
        st["timer"] = timer                            # as an older build left it
        st["module"] = object()
        fresh = toast._state()
        self.assertIsNot(fresh, st)
        self.assertFalse(timer.isActive())
        self.assertFalse(card.isVisible())

    def test_a_click_opens_the_chat_in_the_window(self):
        opened = []

        class Win(object):
            def open_chat(self, chat):
                opened.append(chat)
        self.swap(W, "show", lambda origin=None, session=None: Win())
        toast.open_chat("dm2")
        toast.open_chat(None)
        self.assertEqual(opened, ["dm2"])

    def test_a_window_that_cannot_open_is_said_in_the_script_editor_only(self):
        def broken(origin=None, session=None):
            raise RuntimeError("no window")
        self.swap(W, "show", broken)
        with mock.patch("traceback.print_exc") as said:
            toast.open_chat("dm")
        self.assertTrue(said.called)


class Area(Base):
    def test_without_a_viewport_it_is_the_screen_and_the_hub_s_rail_is_an_obstacle(self):
        def none(side="left"):
            raise RuntimeError("no Maya")
        self.swap(maya_hubedge, "_viewport_area", none)
        self.swap(W, "_main_window", lambda: None)
        rect, obstacles = toast.area()
        g = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        self.assertEqual(rect, (g.x(), g.y(), g.width(), g.height()))
        self.assertEqual(obstacles, [])

    def test_the_viewport_s_area_and_the_rail_beside_it(self):
        class Edge(object):
            def alive(self):
                return True

            def visible_rects(self):
                return [(0, 0, 40, 400)]
        old = getattr(sys, "_skeldar_hubedge", MISSING)
        sys._skeldar_hubedge = {"edge": Edge()}
        self.addCleanup(lambda: setattr(sys, "_skeldar_hubedge", old) if old is not MISSING
                        else delattr(sys, "_skeldar_hubedge"))
        self.swap(maya_hubedge, "_viewport_area", lambda side="left": (10, 20, 800, 600))
        self.swap(maya_hubedge, "_above_timebar", lambda rect: (10, 20, 800, 500))
        self.assertEqual(toast.area(), ((10, 20, 800, 500), [(0, 0, 40, 400)]))

    def test_with_maya_s_window_it_is_that_window(self):
        self.swap(maya_hubedge, "_viewport_area", lambda side="left": None)
        main = QtWidgets.QWidget()
        main.resize(640, 480)
        self.addCleanup(main.deleteLater)
        self.swap(W, "_main_window", lambda: main)
        rect, _o = toast.area()
        self.assertEqual(rect[2:], (640, 480))


class CallCard(Base):
    def setUp(self):
        Base.setUp(self)
        self.got = []
        self.swap(toast, "answer_call", lambda cid, kind: self.got.append((cid, kind)))
        self.swap(toast, "decline_call", lambda cid: self.got.append((cid, "no")))
        self.swap(notify, "_gone", lambda cid: self.got.append(("gone", cid)))
        self.card = toast.show_call(call(), BOB, "Bob")

    def at(self, name):
        return self.card.button_rects()[name].center()

    def test_the_mouse_over_a_button_lights_it_at_once(self):
        card = self.card
        plain = render(card)
        card.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, self.at("voice"), QtCore.Qt.NoButton))
        self.assertEqual(card.over, "voice")
        lit = render(card)
        r = card.button_rects()["voice"].toRect()
        x, y = r.left() + 3, r.center().y()
        self.assertNotEqual(lit.pixelColor(x, y), plain.pixelColor(x, y))
        card.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertIsNone(card.over)
        self.assertEqual(render(card).pixelColor(x, y), plain.pixelColor(x, y))

    def test_it_never_leaves_on_its_own(self):
        self.assertFalse(self.card.stay.isActive())
        self.card.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertFalse(self.card.stay.isActive(), "no stay starts when the mouse leaves")
        self.assertIsNone(self.card.leaving)

    def test_a_press_on_a_button_answers_or_declines_and_stops_the_ring(self):
        self.card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, self.at("decline")))
        self.assertEqual(self.got, [("gone", "c1"), ("c1", "no")])
        self.assertIsNotNone(self.card.leaving)
        other = toast.show_call(call(id="c2", kind="audio"), BOB, "Bob")
        other.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress,
                                    other.button_rects()["voice"].center()))
        self.assertEqual(self.got[-1], ("c2", "audio"))

    def test_a_press_beside_the_buttons_or_with_the_right_button_does_nothing(self):
        self.card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(4, 4)))
        self.card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, self.at("video"),
                                        QtCore.Qt.RightButton))
        self.assertEqual(self.got, [])
        self.assertIsNone(self.card.leaving)

    def test_it_paints_who_what_and_three_buttons(self):
        self.card.over = "video"
        image = render(self.card)
        for name in ("voice", "video", "decline"):
            r = self.card.button_rects()[name].toRect()
            inked = sum(1 for x in range(r.left(), r.right(), 2)
                        for y in range(r.top(), r.bottom(), 2) if image.pixelColor(x, y).alpha())
            self.assertGreater(inked, 20, name)
        self.card.set_call(call(kind="audio"), BOB, "Bob")
        self.card.hover = True
        self.assertGreater(render(self.card).width(), 0)

    def test_the_call_cards_stand_below_the_message_cards(self):
        msg = toast.show("dm2", BOB, "Bob", "hi")
        self.assertLess(msg.y(), self.card.y())

    def test_dismissed_it_is_gone_at_once(self):
        toast.dismiss_call("c1")
        self.assertEqual(toast.call_cards(), [])
        self.assertFalse(self.card.isVisible())

    def test_a_second_show_of_the_same_call_updates_its_card(self):
        again = toast.show_call(call(kind="audio"), BOB, "Bob")
        self.assertIs(again, self.card)
        self.assertEqual(self.card.kind, "audio")
        self.assertEqual(len(toast.call_cards()), 1)


class Answer(Base):
    def test_answer_goes_to_the_call_window_with_this_maya_s_session(self):
        got = []
        self.swap(callview, "answer", lambda ses, cid, kind: got.append((ses, cid, kind)))
        toast.answer_call("c1", "video")
        self.assertEqual(got, [(self.ses, "c1", "video")])

    def test_decline_goes_to_the_session_and_a_failure_is_quiet(self):
        toast.decline_call("c1")
        self.assertEqual(self.ses.declined, ["c1"])

        def broken(call_id):
            raise RuntimeError("offline")
        self.ses.decline_call = broken
        toast.decline_call("c2")                       # nothing raises


class Modules(Base):
    def test_a_new_module_object_drops_the_old_one_s_cards(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        st = toast._state()
        st["module"] = object()                        # as after an install's purge
        fresh = toast._state()
        self.assertIsNot(fresh, st)
        self.assertEqual(fresh["cards"], [])
        self.assertFalse(card.isVisible())


if __name__ == "__main__":
    unittest.main()

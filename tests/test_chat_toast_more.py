"""maya_chat.toast: the message card under the mouse, the call card's buttons over its life, the
stack's timer, and the presses that go to the window or the session. Offscreen; the clock is
moved by hand (no sleeps), the session and the call window are fakes."""
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import maya_hubedge  # noqa: E402
import maya_hubmotion as hubmotion  # noqa: E402
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
        timer = toast._state().get("timer")
        if timer is not None:
            timer.stop()
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

    def land(self, card):
        card.fly_at = None if card.fly_at is None else card.fly_at - look.TOAST_FLY_MS - 1
        card.born -= 10 ** 6
        card.flash_at -= 10 ** 6
        toast._tick()
        self.assertFalse(card.flying())


class MessageCard(Base):
    def test_under_the_mouse_it_is_held_and_leaving_gives_it_time_again(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.land(card)
        card.enterEvent(QtCore.QEvent(QtCore.QEvent.Enter))
        self.assertTrue(card.hover)
        card.stay_left = 10.0
        card.last -= 5000
        toast._tick()
        self.assertEqual(card.stay_left, 10.0, "held: the stay does not count down")
        self.assertIsNone(card.leaving)
        card.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
        self.assertFalse(card.hover)
        self.assertGreaterEqual(card.stay_left, 1500.0)
        self.assertTrue(toast._state()["timer"].isActive())

    def test_the_cross_lights_under_the_mouse_and_dismisses(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.land(card)
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
        self.land(card)
        opened = []
        self.swap(toast, "open_chat", opened.append)
        card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(60, 20),
                                   QtCore.Qt.RightButton))
        self.assertIsNotNone(card.leaving)
        self.assertEqual(opened, [])

    def test_a_hovered_card_paints_its_lit_face(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.land(card)
        plain = render(card).pixelColor(card.cw - 40, card.height() // 2)
        card.hover = True
        lit = render(card).pixelColor(card.cw - 40, card.height() // 2)
        self.assertNotEqual(plain, lit)

    def test_a_card_moved_up_eases_to_its_new_place(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.land(card)
        x, y = card.base
        card.go_to(x, y - 80, animate=True)
        self.assertEqual(card.place_to, (x, y - 80))
        card.go_to(x, y - 80, animate=True)               # the same place again: unchanged
        self.assertTrue(card.moving(toast._now()))
        card.place_at -= look.TOAST_MOVE_MS / 2.0
        card.tick(toast._now())
        self.assertTrue(y - 80 < card.base[1] < y)
        card.place_at -= look.TOAST_MOVE_MS
        card.tick(toast._now())
        self.assertIsNone(card.place_to)
        self.assertEqual(card.base, (x, y - 80))
        self.assertEqual((card.x(), card.y()), (x, y - 80))

    def test_a_hidden_card_goes_to_its_place_at_once_and_a_card_already_there_stays(self):
        card = toast.card_class()("dm", BOB, "Bob", "hi")
        card.go_to(30, 40, animate=True)
        self.assertEqual(card.base, (30, 40))
        self.assertEqual(card.pos(), QtCore.QPoint(30, 40))
        card.fly_from(10)                                   # nothing to fly: at its place
        self.assertFalse(card.flying())
        card.deleteLater()

    def test_with_animations_off_it_stands_at_once_and_leaves_at_once(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            card = toast.show("dm", BOB, "Bob", "hi")
            self.assertFalse(card.flying())
            self.assertFalse(card.moving(toast._now()) and card.hover)
            card.leave()
            self.assertTrue(card.gone(toast._now()))
            toast._tick()
        self.assertEqual(toast.cards(), [])

    def test_a_card_that_finished_leaving_is_taken_away_and_the_timer_stops(self):
        card = toast.show("dm", BOB, "Bob", "hi")
        self.land(card)
        card.leave()
        card.leaving -= look.TOAST_OUT_MS + 1
        toast._tick()
        self.assertEqual(toast._state()["cards"], [])
        self.assertFalse(toast._state()["timer"].isActive())
        timer = toast._state()["timer"]
        toast._wake()
        self.assertIs(toast._state()["timer"], timer, "one timer for every card")

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
        self.land(self.card)

    def at(self, name):
        return self.card.button_rects()[name].center()

    def test_the_mouse_over_a_button_lights_it_over_its_hover_time(self):
        card = self.card
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            card.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, self.at("voice"),
                                      QtCore.Qt.NoButton))
            self.assertEqual(card.over, "voice")
            self.assertTrue(card.moving(toast._now()), "a button lighting is motion")
            card.last = toast._now() - toast.HOVER_MS / 2.0
            card.tick(toast._now())
            self.assertTrue(0.0 < card.level["voice"] < 1.0)
            self.assertTrue(card.moving(toast._now()))
            card.last = toast._now() - toast.HOVER_MS * 2
            card.tick(toast._now())
            self.assertEqual(card.level["voice"], 1.0)
            self.assertFalse(card.moving(toast._now()), "lit and still: at rest")
            card.leaveEvent(QtCore.QEvent(QtCore.QEvent.Leave))
            self.assertIsNone(card.over)
            card.last = toast._now() - toast.HOVER_MS * 2
            card.tick(toast._now())
            self.assertEqual(card.level["voice"], 0.0)

    def test_with_animations_off_a_button_lights_at_once(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.card.mouseMoveEvent(mouse(QtCore.QEvent.MouseMove, self.at("decline"),
                                           QtCore.Qt.NoButton))
        self.assertEqual(self.card.level["decline"], 1.0)
        self.assertEqual(self.card.level["voice"], 0.0)

    def test_it_never_leaves_on_its_own(self):
        self.card.stay_left = 0.0
        self.card.last -= 10 ** 6
        toast._tick()
        self.assertIsNone(self.card.leaving)
        self.assertGreater(self.card.stay_left, 10 ** 9)

    def test_a_press_on_a_button_answers_or_declines_and_stops_the_ring(self):
        self.card.mousePressEvent(mouse(QtCore.QEvent.MouseButtonPress, self.at("decline")))
        self.assertEqual(self.got, [("gone", "c1"), ("c1", "no")])
        self.assertIsNotNone(self.card.leaving)
        other = toast.show_call(call(id="c2", kind="audio"), BOB, "Bob")
        self.land(other)
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
        self.card.level["video"] = 1.0
        image = render(self.card)
        for name in ("voice", "video", "decline"):
            r = self.card.button_rects()[name].toRect()
            inked = sum(1 for x in range(r.left(), r.right(), 2)
                        for y in range(r.top(), r.bottom(), 2) if image.pixelColor(x, y).alpha())
            self.assertGreater(inked, 20, name)
        self.card.set_call(call(kind="audio"), BOB, "Bob")
        self.card.hover = True
        self.card.flash_at = toast._now()
        self.assertGreater(render(self.card).width(), 0)

    def test_the_call_cards_stand_below_the_message_cards(self):
        msg = toast.show("dm2", BOB, "Bob", "hi")
        self.land(msg)
        toast._layout(animate=False)
        self.assertLess(msg.y(), self.card.y())

    def test_dismissed_with_animations_off_it_is_gone_at_once(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            toast.dismiss_call("c1")
        self.assertEqual(toast.call_cards(), [])

    def test_show_call_with_animations_off_does_not_fly(self):
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            card = toast.show_call(call(id="c3"), BOB, "Bob")
        self.assertFalse(card.flying())


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
        if st.get("timer") is not None:
            st["timer"].stop()
        st["module"] = object()                        # as after an install's purge
        fresh = toast._state()
        self.assertIsNot(fresh, st)
        self.assertEqual(fresh["cards"], [])
        self.assertFalse(card.isVisible())


if __name__ == "__main__":
    unittest.main()

"""The incoming call: its ring (a looped sound) and its card."""
import time
import unittest
from unittest import mock

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtWidgets

import maya_hubsound as sound
from maya_chat import notify
from maya_chat import session as S

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeSession(object):
    def __init__(self):
        self.state = S.State()
        self.state.me = dict(ME)
        self.state.chats = {"dm": {"id": "dm", "kind": "dm", "name": "", "members": [ME, BOB],
                                   "unread": 0}}
        self.declined = []

    def decline_call(self, call_id):
        self.declined.append(call_id)
        return True


def call(**kw):
    v = {"id": "c1", "chat": "dm", "by": "bob", "kind": "video", "cid": "x", "state": "ringing",
         "members": ["bob"], "declined": [], "started_at": int(time.time() * 1000),
         "answered_at": None, "ended_at": None}
    v.update(kw)
    return v


class Loop(unittest.TestCase):
    def test_a_loop_plays_until_stopped(self):
        class P(object):
            def __init__(self):
                self.playing = False

            def play(self):
                self.playing = True

            def stop(self):
                self.playing = False
        made = []
        with mock.patch.object(sound, "make_loop_player",
                               side_effect=lambda path: made.append(P()) or made[-1]):
            handle = sound.loop("ring", force=True)
            self.assertTrue(made[0].playing)
            handle.stop()
            self.assertFalse(made[0].playing)

    def test_a_loop_is_quiet_with_sounds_off_unless_forced(self):
        with mock.patch.object(sound, "enabled", return_value=False), \
                mock.patch.object(sound, "make_loop_player") as make:
            self.assertIsNone(sound.loop("ring"))
            make.assert_not_called()

    def test_the_shipped_ring_is_the_synthesis(self):
        from tests.test_hubsound import _decoded
        with open(sound.sound_path("ring"), "rb") as f:
            shipped = _decoded(f.read())
        made = _decoded(sound.wav_bytes(sound.synth(sound.SOUNDS["ring"])))
        self.assertEqual(shipped[0], made[0])
        self.assertEqual(len(shipped[1]), len(made[1]))
        self.assertLessEqual(max(abs(a - b) for a, b in zip(shipped[1], made[1])), 1)

    def test_the_real_loop_player_is_made_silent_under_test(self):
        self.assertTrue(sound.muted())
        handle = sound.loop("ring", force=True)
        self.assertIsNotNone(handle)
        handle.stop()


class CallCards(unittest.TestCase):
    def setUp(self):
        _app()
        from maya_chat import toast
        self.toast = toast
        toast.clear()
        notify._VARS.clear()
        self.ses = FakeSession()

    def tearDown(self):
        self.toast.clear()
        QtWidgets.QApplication.processEvents()

    def test_a_card_with_three_buttons(self):
        card = self.toast.show_call(call(), BOB, "Bob")
        self.assertEqual(set(card.button_rects()), {"voice", "video", "decline"})
        self.assertEqual([c.call_id for c in self.toast.call_cards()], ["c1"])
        self.toast.dismiss_call("c1")
        self.assertEqual(self.toast.call_cards(), [])

    def test_a_second_show_updates_the_card(self):
        a = self.toast.show_call(call(), BOB, "Bob")
        b = self.toast.show_call(call(kind="audio"), BOB, "Bob")
        self.assertIs(a, b)
        self.assertEqual(len(self.toast.call_cards()), 1)

    def test_the_buttons_answer_or_decline(self):
        got = []
        with mock.patch.object(self.toast, "answer_call",
                               side_effect=lambda cid, kind: got.append((cid, kind))), \
                mock.patch.object(self.toast, "decline_call",
                                  side_effect=lambda cid: got.append((cid, "no"))):
            self.toast.show_call(call(), BOB, "Bob").press("video")
            self.toast.show_call(call(id="c2"), BOB, "Bob").press("decline")
            self.toast.show_call(call(id="c3"), BOB, "Bob").press("voice")
        self.assertEqual(got, [("c1", "video"), ("c2", "no"), ("c3", "audio")])

    def test_decline_goes_to_the_session(self):
        from maya_chat import session as _session
        with mock.patch.object(_session, "get", return_value=self.ses):
            self.toast.decline_call("c1")
        self.assertEqual(self.ses.declined, ["c1"])

    def test_notify_rings_and_stops(self):
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: rings.append("ring") or H()):
            self.ses.state.calls = {"c1": call()}
            out = notify.heard(self.ses, "call", {"kind": "call", "call": call()}, out=[])
            self.assertIn(("call_card", "c1"), out)
            self.assertEqual(rings, ["ring"])
            notify.heard(self.ses, "call", {"kind": "call", "call": call()}, out=[])
            self.assertEqual(rings, ["ring"])                 # not twice
            ended = call(state="ended", members=[], ended_at=1)
            self.ses.state.calls = {"c1": ended}
            out = notify.heard(self.ses, "call", {"kind": "call", "call": ended}, out=[])
            self.assertIn(("call_gone", "c1"), out)
            self.assertEqual(rings, ["ring", "stop"])
        self.assertEqual(self.toast.call_cards(), [])

    def test_my_own_call_does_not_ring_me(self):
        mine = call(by="me", members=["me"])
        self.ses.state.calls = {"c1": mine}
        with mock.patch.object(notify, "_loop_ring") as ring:
            notify.heard(self.ses, "call", {"kind": "call", "call": mine}, out=[])
        ring.assert_not_called()
        self.assertEqual(self.toast.call_cards(), [])

    def test_pressing_a_button_stops_the_ring_at_once(self):
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: H()), \
                mock.patch.object(self.toast, "answer_call"):
            self.ses.state.calls = {"c1": call()}
            notify.heard(self.ses, "call", {"kind": "call", "call": call()}, out=[])
            self.toast.call_cards()[0].press("voice")
        self.assertEqual(rings, ["stop"])
        self.assertEqual(notify._rings(), {})
        self.assertEqual(self.toast.call_cards(), [])

    def test_uninstall_stops_every_ring_and_removes_the_cards(self):
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: H()):
            self.ses.state.calls = {"c1": call(), "c2": call(id="c2")}
            for c in self.ses.state.calls.values():
                notify.heard(self.ses, "call", {"kind": "call", "call": c}, out=[])
            self.assertEqual(len(self.toast.call_cards()), 2)
            notify.uninstall()
        self.assertEqual(rings, ["stop", "stop"])
        self.assertEqual(self.toast.call_cards(), [])

    def test_closing_the_session_calls_uninstall(self):
        with mock.patch.object(notify, "uninstall") as un:
            S.close()
        un.assert_called_once()

    def test_answered_elsewhere_stops_the_ring(self):
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: H()):
            self.ses.state.calls = {"c1": call()}
            notify.heard(self.ses, "call", {"kind": "call", "call": call()}, out=[])
            live = call(state="live", members=["bob", "me"])
            self.ses.state.calls = {"c1": live}
            out = notify.heard(self.ses, "call", {"kind": "call", "call": live}, out=[])
        self.assertIn(("call_gone", "c1"), out)
        self.assertEqual(rings, ["stop"])
        self.assertEqual(self.toast.call_cards(), [])


class HereSession(FakeSession):
    """A session whose disk remembers the calls this Maya was in."""

    def __init__(self, here=()):
        super(HereSession, self).__init__()
        self.here, self.left = set(here), []

    def calls_here(self):
        return list(self.here)

    def call_here(self, call_id, on):
        (self.here.add if on else self.here.discard)(call_id)

    def leave_call(self, call_id):
        self.left.append(call_id)
        return True


class Strays(unittest.TestCase):
    """Maya restarted mid-call: the server still has me in it, no window holds it."""

    def setUp(self):
        _app()
        if hasattr(__import__("sys"), "_skeldar_chat_strays"):
            del __import__("sys")._skeldar_chat_strays
        self.later = mock.patch.object(notify, "_later", side_effect=lambda ms, fn: fn())
        self.later.start()

    def tearDown(self):
        self.later.stop()
        from maya_chat import callview
        callview.destroy()

    def tell(self, ses, view):
        ses.state.calls = {view["id"]: view}
        return notify.heard(ses, "call", {"kind": "call", "call": view}, out=[])

    def test_a_call_I_was_in_here_with_no_window_is_left_once(self):
        ses = HereSession(here=["c1"])
        live = call(state="live", members=["bob", "me"])
        out = self.tell(ses, live)
        self.assertIn(("stray_left", "c1"), out)
        self.assertEqual(ses.left, ["c1"])
        self.assertNotIn("c1", ses.here)
        ses.here.add("c1")                                        # even marked again: once
        self.tell(ses, live)
        self.assertEqual(ses.left, ["c1"])

    def test_a_call_from_another_machine_is_not_left(self):
        ses = HereSession(here=[])
        self.tell(ses, call(state="live", members=["bob", "me"]))
        self.assertEqual(ses.left, [])

    def test_a_call_the_window_holds_is_not_left(self):
        from maya_chat import callview
        ses = HereSession(here=["c1"])

        class Win(object):
            closed = False
            call_id = "c1"

            def holds(self, view):
                return view["id"] == "c1"
        with mock.patch.object(callview, "current", return_value=Win()):
            self.tell(ses, call(state="live", members=["bob", "me"]))
        self.assertEqual(ses.left, [])

    def test_the_starter_s_window_waiting_on_its_cid_holds_it(self):
        from maya_chat import callview
        ses = HereSession(here=["c1"])
        win = callview.CallWindow.__new__(callview.CallWindow)
        win.closed, win.call_id, win.cid, win.session = False, None, "x", ses
        with mock.patch.object(callview, "current", return_value=win):
            self.tell(ses, call(by="me", members=["me"], cid="x"))
        self.assertEqual(ses.left, [])

    def test_an_ended_call_is_forgotten_on_disk(self):
        ses = HereSession(here=["c1"])
        self.tell(ses, call(state="ended", members=[], ended_at=1))
        self.assertNotIn("c1", ses.here)
        self.assertEqual(ses.left, [])

    def test_a_call_I_am_not_in_is_not_left(self):
        ses = HereSession(here=["c1"])
        self.tell(ses, call(state="live", members=["bob", "x"]))
        self.assertEqual(ses.left, [])


class Ending(unittest.TestCase):
    def setUp(self):
        _app()

    def test_calls_end_stops_the_rings(self):
        with mock.patch.object(notify, "stop_all") as stop:
            out = notify.heard(FakeSession(), "calls_end", None, out=[])
        stop.assert_called_once()
        self.assertIn(("calls_end",), out)

    def test_a_resync_stops_a_ring_for_a_call_no_longer_known(self):
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        ses = FakeSession()
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: H()):
            ses.state.calls = {"c1": call()}
            notify.heard(ses, "call", {"kind": "call", "call": call()}, out=[])
            ses.state.calls = {}
            out = notify.heard(ses, "resync", None, out=[])
        self.assertIn(("call_gone", "c1"), out)
        self.assertEqual(rings, ["stop"])


if __name__ == "__main__":
    unittest.main()

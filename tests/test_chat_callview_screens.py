"""Which screen is being shared, and the one-press way to Maya's own window.

The animator, 2026-10-29: «Когда я свой рабочий стол шарю то у меня не видно маи а у коллеги все
норм.» Measured the same day: Chromium offers ONE screen row on their machine - the external
monitor - while they work on the laptop panel, which Chromium does not offer at all. So «весь
экран» shared a screen with nothing of theirs on it, and the line said only «Экран 2560×1440».

What is pinned here: the captured monitor is named by its NATIVE size (the constrained one from
getSettings cannot tell two monitors apart), a screen that is not the window's own is said so, and
the screen button's menu has a row that takes Maya's own window by its title.
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtGui, QtWidgets  # noqa: E402

from maya_chat import callview as V  # noqa: E402

from tests.test_chat_callview import FakeRequest  # noqa: E402
from tests.test_chat_callview_more import Base, answered_menus  # noqa: E402


class FakeScreen(object):
    """A QScreen stand-in: a name, a logical geometry and a ratio."""

    def __init__(self, name, width, height, ratio=1.0):
        self._name, self._w, self._h, self._ratio = name, width, height, ratio

    def name(self):
        return self._name

    def geometry(self):
        from PySide6 import QtCore
        return QtCore.QRect(0, 0, self._w, self._h)

    def devicePixelRatio(self):
        return self._ratio


LAPTOP = FakeScreen("NE180QDM-NM2", 2560, 1600)
BIG = FakeScreen("LG ULTRAFINE", 3840, 2160)
#  what the page hands over for a capture of the big one: the SETTINGS are the constrained size
SHARED_BIG = {"surface": "monitor", "w": 2560, "h": 1440, "nw": 3840, "nh": 2160, "label": "screen:4:0"}


class Titles(unittest.TestCase):
    def test_a_long_window_title_keeps_its_front(self):
        long = ("session_20261029_141653.ma* - Autodesk MAYA 2027.2: "
                "C:\\Users\\MY PC\\Documents\\maya\\SkeldarTabs\\session_20261029_141653.ma")
        short = V.short_title(long)
        self.assertEqual(len(short), 46)
        self.assertTrue(short.startswith("session_20261029_141653.ma*"))
        self.assertTrue(short.endswith(u"…"))

    def test_a_short_title_is_left_alone_and_whitespace_collapses(self):
        self.assertEqual(V.short_title("Atone  -  Unreal\n Editor"), "Atone - Unreal Editor")
        self.assertEqual(V.short_title(None), u"")


class MayaRow(unittest.TestCase):
    def rows(self, *labels):
        return [("screen", 0, u"Весь экран")] + [("window", i, V.short_title(t))
                                                 for i, t in enumerate(labels)]

    def test_the_exact_title_windows_shows_names_the_row(self):
        choices = self.rows("untitled* - Autodesk MAYA 2027.2: untitled",
                            "session.ma* - Autodesk MAYA 2027.2: session.ma",
                            "Atone - Unreal Editor")
        self.assertEqual(V.maya_row(choices, "session.ma* - Autodesk MAYA 2027.2: session.ma"),
                         ("window", 1))

    def test_one_maya_window_needs_no_title(self):
        choices = self.rows("untitled* - Autodesk MAYA 2027.2: untitled", "Atone - Unreal Editor")
        self.assertEqual(V.maya_row(choices, None), ("window", 0))

    def test_a_crash_report_is_never_it(self):
        choices = self.rows("Autodesk MAYA 2027 Error Report",
                            "untitled* - Autodesk MAYA 2027.2: untitled")
        self.assertEqual(V.maya_row(choices, None), ("window", 1))

    def test_two_mayas_and_no_title_is_no_answer(self):
        # sharing the other Maya's window would be worse than sharing nothing
        choices = self.rows("one.ma - Autodesk MAYA 2027.2: one.ma",
                            "two.ma - Autodesk MAYA 2027.2: two.ma")
        self.assertIsNone(V.maya_row(choices, None))

    def test_no_window_at_all(self):
        self.assertIsNone(V.maya_row([("screen", 0, u"Весь экран")], "whatever"))


class WhichScreen(unittest.TestCase):
    def test_the_monitor_is_found_by_its_native_size(self):
        self.assertIs(V.capture_screen(SHARED_BIG, [LAPTOP, BIG]), BIG)

    def test_a_scaled_screen_is_measured_in_its_own_pixels(self):
        scaled = FakeScreen("HiDPI", 1920, 1080, 2.0)
        self.assertIs(V.capture_screen({"surface": "monitor", "nw": 3840, "nh": 2160},
                                       [LAPTOP, scaled]), scaled)

    def test_two_monitors_of_one_size_are_no_answer(self):
        twin = FakeScreen("LG ULTRAFINE 2", 3840, 2160)
        self.assertIsNone(V.capture_screen(SHARED_BIG, [BIG, twin]))

    def test_a_window_capture_is_no_screen(self):
        self.assertIsNone(V.capture_screen({"surface": "window", "nw": 3840, "nh": 2160},
                                           [LAPTOP, BIG]))

    def test_a_capture_from_an_older_page_says_nothing(self):
        self.assertIsNone(V.capture_screen({"surface": "monitor", "w": 2560, "h": 1440},
                                           [LAPTOP, BIG]))


class CaptureText(unittest.TestCase):
    def test_a_known_monitor_is_named_with_its_own_size(self):
        self.assertEqual(V.capture_text(SHARED_BIG, [LAPTOP, BIG]),
                         u"Экран LG ULTRAFINE 3840×2160")

    def test_an_unknown_monitor_keeps_the_plain_line(self):
        self.assertEqual(V.capture_text({"surface": "monitor", "w": 2560, "h": 1600}, []),
                         u"Экран 2560×1600")

    def test_a_window_is_named_by_its_title(self):
        self.assertEqual(V.capture_text({"surface": "window", "label": "Atone - Unreal Editor"}, []),
                         u"Окно: Atone - Unreal Editor")


class WrongScreen(Base):
    def test_the_screen_the_window_stands_on_says_nothing(self):
        w = self.live()
        with mock.patch.object(V, "capture_screen", return_value=BIG), \
                mock.patch.object(w, "here_screen", return_value=BIG):
            self.assertEqual(w._wrong_screen(SHARED_BIG), u"")

    def test_another_screen_is_said_with_the_way_out(self):
        w = self.live()
        with mock.patch.object(V, "capture_screen", return_value=BIG), \
                mock.patch.object(w, "here_screen", return_value=LAPTOP):
            note = w._wrong_screen(SHARED_BIG)
        self.assertIn(u"на другом экране", note)
        self.assertIn(u"Окно Maya", note)

    def test_nothing_is_said_when_the_monitor_is_unknown(self):
        w = self.live()
        with mock.patch.object(V, "capture_screen", return_value=None), \
                mock.patch.object(w, "here_screen", return_value=LAPTOP):
            self.assertEqual(w._wrong_screen(SHARED_BIG), u"")

    def test_the_line_about_a_share_carries_it(self):
        w = self.live()
        with mock.patch.object(V, "capture_screen", return_value=BIG), \
                mock.patch.object(w, "here_screen", return_value=LAPTOP):
            w._page_state({"capture": SHARED_BIG})
        self.assertIn(u"LG ULTRAFINE", w.last_message)
        self.assertIn(u"на другом экране", w.last_message)


class MayaWindowRow(Base):
    def test_the_menu_offers_maya_s_own_window_first(self):
        w = self.live()
        seen = []

        def pick(menu):
            seen.extend(a.text() for a in menu.actions())
            return None
        with answered_menus(pick):
            w._screen_menu(w.buttons["screen"].rect().topLeft())
        self.assertEqual(seen[0], u"Окно Maya")

    def test_picking_it_asks_the_page_for_a_share_of_maya_s_window(self):
        w = self.live()
        with answered_menus(lambda menu: [a for a in menu.actions()
                                          if a.text() == u"Окно Maya"][0]):
            w._screen_menu(w.buttons["screen"].rect().topLeft())
        self.assertEqual(w._want, "maya")
        self.assertEqual(self.sent("screen")[-1], {"on": True})

    def test_the_request_then_takes_maya_s_window_by_its_title(self):
        w = self.live()
        w._want = "maya"
        request = FakeRequest()
        request.windows.clear()
        for title in ("Atone - Unreal Editor", "untitled* - Autodesk MAYA 2027.2: untitled"):
            request.windows.appendRow(QtGui.QStandardItem(title))
        with mock.patch.object(V, "window_title",
                               return_value="untitled* - Autodesk MAYA 2027.2: untitled"):
            self.assertEqual(w.choose_source(request), ("window", 1))

    def test_no_maya_window_in_the_list_is_said_and_nothing_is_shared(self):
        w = self.live()
        w._want = "maya"
        request = FakeRequest()
        request.windows.clear()
        request.windows.appendRow(QtGui.QStandardItem("Atone - Unreal Editor"))
        with mock.patch.object(V, "window_title", return_value="nothing like it"):
            self.assertIsNone(w.choose_source(request))
        self.assertIn(u"Окно Maya", w.last_message)

    def test_the_window_rows_of_the_menu_are_short(self):
        request = FakeRequest()
        request.windows.clear()
        request.windows.appendRow(QtGui.QStandardItem(
            "session_20261029_141653.ma* - Autodesk MAYA 2027.2: "
            "C:\\Users\\MY PC\\Documents\\maya\\SkeldarTabs\\session_20261029_141653.ma"))
        labels = [label for kind, _row, label in V.screen_choices(request) if kind == "window"]
        self.assertTrue(all(len(label) <= 46 for label in labels), labels)


class TheTitleWindowsShows(unittest.TestCase):
    def test_qt_s_placeholder_is_not_what_chromium_lists(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("untitled[*] - Autodesk MAYA 2027.2: untitled")
        widget.setWindowModified(True)
        self.addCleanup(widget.deleteLater)
        #  offscreen there is no native title to read, so the fallback is what answers
        self.assertEqual(V.window_title(widget), "untitled* - Autodesk MAYA 2027.2: untitled")

    def test_nothing_to_ask(self):
        self.assertEqual(V.window_title(None), u"")


if __name__ == "__main__":
    unittest.main()

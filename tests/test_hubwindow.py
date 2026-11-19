"""maya_hubwindow - the floating window's and the rail card's look. Offscreen Qt.
Spec: docs/superpowers/specs/2026-10-18-floating-windows-design.md. Since 2026-11-19 nothing
of it moves or lights up (the animator: «удаляем все подсветки и анимации из плагина»)."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtGui, QtWidgets

import maya_hubstyle as hubstyle
import maya_hubwindow as hubwindow


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _rgb(image, x, y):
    c = image.pixelColor(x, y)
    return (c.red(), c.green(), c.blue())


def _hex(name):
    v = hubstyle.TOKENS[name]
    return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))


class Frame(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.frame = hubwindow.frame_class()(1.0)
        self.frame.resize(240, 160)
        layout = QtWidgets.QVBoxLayout(self.frame)
        layout.setContentsMargins(5, 34, 5, 5)
        self.frame.content = QtWidgets.QFrame()
        self.frame.content.setObjectName("testContent")
        layout.addWidget(self.frame.content)
        hubwindow.dress(self.frame, 1.0)
        self.frame.show()
        self.app.processEvents()

    def render(self):
        image = QtGui.QImage(240, 160, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.frame.render(image)
        return image

    def test_the_face_is_lighter_at_the_top_and_panel_below(self):
        """Look D (2026-10-22): the bevel fades from BEVEL_TOP to `panel`."""
        image = self.render()
        top = _rgb(image, 120, 4)
        low = _rgb(image, 120, 60)
        self.assertGreater(sum(top), sum(low))
        self.assertEqual(low, _hex("panel"))

    def test_the_outline_is_the_dark_edge_and_the_grip_stands_on_top(self):
        image = self.render()
        edge = QtGui.QColor(hubwindow.EDGE)
        self.assertEqual(_rgb(image, 0, 80), (edge.red(), edge.green(), edge.blue()))
        grip = _rgb(image, 120, hubwindow.GRIP_Y + 1)
        self.assertGreater(sum(grip), sum(_rgb(image, 120 + 30, hubwindow.GRIP_Y + 1)))

    def test_an_empty_content_has_no_well(self):
        image = self.render()
        self.assertEqual(_rgb(image, 120, 100), _hex("panel"))

    def test_a_control_stands_on_a_well(self):
        layout = QtWidgets.QVBoxLayout(self.frame.content)
        layout.setContentsMargins(4, 4, 4, 4)
        button = QtWidgets.QPushButton("Apply", self.frame.content)
        button.setFixedHeight(20)
        layout.addWidget(button)
        layout.addStretch(1)
        self.app.processEvents()
        image = self.render()
        top = button.mapTo(self.frame, QtCore.QPoint(0, 0))
        # beside the button, inside the content's side margin: the well
        self.assertEqual(_rgb(image, 7, top.y() + 10), _hex("track"))
        # well below the last control: the panel again
        self.assertEqual(_rgb(image, 120, 150), _hex("panel"))

    def test_a_card_face_paints_the_content_card(self):
        self.frame.content_face = "card"
        image = self.render()
        self.assertEqual(_rgb(image, 120, 100), _hex("card"))

    def test_the_fields_are_recessed_under_the_frame_only(self):
        self.frame.setObjectName("testFrame")
        field = QtWidgets.QLineEdit(self.frame.content)
        outside = QtWidgets.QLineEdit()
        hubwindow.recess(self.frame, 1.0)
        sheet = self.frame.styleSheet()
        self.assertIn("#testFrame QLineEdit", sheet)
        self.assertIn(hubstyle.TOKENS["panel"], sheet)
        for line in sheet.splitlines():
            if line.strip():
                self.assertTrue(line.startswith("#testFrame "), line)
        self.assertEqual(outside.styleSheet(), "")
        field.deleteLater()

    def test_no_stripe_and_no_accent_along_the_edges(self):
        image = self.render()
        accent = _hex("accent")
        for x, y in ((2, 80), (120, 1), (4, 40)):
            self.assertNotEqual(_rgb(image, x, y), accent)

    def test_a_frame_has_no_light_left(self):
        """2026-11-19: the window worked in is no longer ringed in the accent."""
        for name in ("level", "flash", "set_light"):
            self.assertFalse(hasattr(self.frame, name), name)
        self.assertFalse(hasattr(hubwindow, "Burster"))
        self.assertFalse(hasattr(hubwindow, "burst_class"))


class Pill(unittest.TestCase):

    def setUp(self):
        self.app = _app()
        self.pill = hubwindow.pill_class()("x", 1.0)
        self.pill.show()

    def render(self):
        """The pill's own paint, without the window background Qt fills under it."""
        image = QtGui.QImage(32, 30, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.pill.render(image, QtCore.QPoint(0, 0), QtGui.QRegion(),
                         QtWidgets.QWidget.RenderFlag.DrawChildren)
        return image

    def test_a_pill_is_its_24_by_22_face_and_4_px_round_it(self):
        self.assertEqual((self.pill.width(), self.pill.height()), (32, 30))

    def test_a_hovered_pill_shows_the_hover_face_flat(self):
        self.assertEqual(_rgb(self.render(), 16, 6), _hex("field"))
        self.pill.hover(True)
        self.assertTrue(self.pill.hovered)
        self.assertEqual(_rgb(self.render(), 16, 6), _hex("hover"))
        self.pill.hover(False)
        self.assertEqual(_rgb(self.render(), 16, 6), _hex("field"))

    def test_nothing_is_drawn_outside_its_face(self):
        self.pill.hover(True)
        image = self.render()
        face = QtCore.QRect(4, 4, 24, 22)
        for y in range(30):
            for x in range(32):
                if not face.contains(x, y):
                    self.assertEqual(image.pixelColor(x, y).alpha(), 0, (x, y))

    def test_no_timer_lift_or_flash(self):
        for name in ("timer", "level", "advance", "press", "flash_at"):
            self.assertFalse(hasattr(self.pill, name), name)


class Wells(unittest.TestCase):
    """maya_hubwindow.wells: look B's recessed plates under the headings, pure."""

    def test_no_heading_one_well_round_every_control(self):
        out = hubwindow.wells([], [(10, 30), (40, 60)], 5, 95, 4, 5)
        self.assertEqual(out, [(5, 6, 95, 64)])

    def test_each_heading_starts_a_well_and_the_one_above_ends_short_of_it(self):
        heads = [(0, 14), (60, 74)]
        items = [(20, 40), (44, 52), (80, 100)]
        out = hubwindow.wells(heads, items, 0, 100, 4, 5)
        self.assertEqual(out, [(0, 16, 100, 55), (0, 76, 100, 104)])

    def test_a_heading_with_nothing_under_it_has_no_well(self):
        out = hubwindow.wells([(0, 14), (20, 34)], [(40, 60)], 0, 100, 4, 5)
        self.assertEqual(out, [(0, 36, 100, 64)])

    def test_a_flat_control_counts_for_nothing(self):
        self.assertEqual(hubwindow.wells([], [(10, 10)], 0, 100, 4, 5), [])


class Title(unittest.TestCase):

    def setUp(self):
        self.app = _app()

    def test_the_title_is_the_name_as_written_bold(self):
        label = hubwindow.title_label("Connections", 1.0, "t")
        self.assertEqual(label.text(), "Connections")
        self.assertIn("bold", label.styleSheet())

    def test_the_mark_is_a_dot_in_the_group_colour(self):
        icon = hubwindow.title_icon("link", "#7fa9e6", 1.0, "i")
        image = icon.pixmap().toImage()
        c = image.width() // 2
        self.assertEqual(_rgb(image, c, c), (0x7f, 0xa9, 0xe6))
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(icon.property("skIconName"), "link")


class WellSides(unittest.TestCase):

    def test_every_well_is_as_wide_as_all_the_controls_plus_the_pad(self):
        heads = [(0, 14), (60, 74)]
        items = [(20, 40, 30, 70), (80, 100, 20, 50)]
        out = hubwindow.wells(heads, items, 5, 95, 4, 5)
        self.assertEqual([(x0, x1) for x0, _y, x1, _z in out], [(16, 74), (16, 74)])

    def test_the_sides_stay_within_the_bounds(self):
        out = hubwindow.wells([], [(10, 20, 2, 99)], 5, 95, 4, 5)
        self.assertEqual((out[0][0], out[0][2]), (5, 95))

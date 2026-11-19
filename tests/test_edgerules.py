"""maya_edgerules: the hub's edge panel as rules (2026-10-08)."""

import subprocess
import sys
import unittest

import maya_edgerules as rules


class Width(unittest.TestCase):

    def test_clamp(self):
        self.assertEqual(rules.clamp_width(100), 280)
        self.assertEqual(rules.clamp_width(360.4), 360)
        self.assertEqual(rules.clamp_width(2000), 700)

    def test_the_panel_stands_on_the_work_area_s_left_edge_full_height(self):
        self.assertEqual(rules.panel_rect((0, 0, 2560, 1528), 360, 1.5),
                         (0, 0, 540, 1528))

    def test_on_a_screen_to_the_right(self):
        self.assertEqual(rules.panel_rect((2560, 0, 3840, 2088), 400, 1.0),
                         (2560, 0, 400, 2088))

    def test_never_wider_than_the_screen(self):
        self.assertEqual(rules.panel_rect((0, 0, 300, 800), 700, 1.0),
                         (0, 0, 300, 800))

    def test_the_sensor(self):
        self.assertEqual(rules.sensor_rect((0, 0, 2560, 1528)),
                         (0, 0, 2, 1528))


class Sides(unittest.TestCase):
    """2026-10-09, the animator: «Можем добавить опцию выбора стороны
    монитора откуда выезжает наша полка?» - left or right."""

    def test_the_variable_and_the_sides(self):
        self.assertEqual(rules.SIDE_VAR, "skeldarAnimHub_edgeSide")
        self.assertEqual(rules.SIDES, ("left", "right"))

    def test_side_of_reads_right_or_left(self):
        self.assertEqual(rules.side_of("right"), "right")
        self.assertEqual(rules.side_of(" Right "), "right")
        for value in ("left", None, "", "top", 0, 1):
            self.assertEqual(rules.side_of(value), "left")

    def test_the_panel_on_the_right_edge(self):
        self.assertEqual(rules.panel_rect((0, 0, 2560, 1528), 360, 1.5,
                                          "right"), (2020, 0, 540, 1528))
        self.assertEqual(rules.panel_rect((2560, 40, 1280, 2000), 400, 1.0,
                                          "right"), (3440, 40, 400, 2000))
        self.assertEqual(rules.panel_rect((0, 0, 300, 800), 700, 1.0,
                                          "right"), (0, 0, 300, 800))

    def test_the_sensor_on_the_right_edge(self):
        self.assertEqual(rules.sensor_rect((0, 0, 2560, 1528), "right"),
                         (2558, 0, 2, 1528))

    def test_the_left_is_the_default(self):
        area = (100, 20, 1600, 900)
        self.assertEqual(rules.panel_rect(area, 360, 1.0),
                         rules.panel_rect(area, 360, 1.0, "left"))
        self.assertEqual(rules.sensor_rect(area),
                         rules.sensor_rect(area, "left"))


class LocalGeometry(unittest.TestCase):
    """Offsets and frames count from the screen edge inward; the host's own
    x depends on the side."""

    def test_the_slot(self):
        self.assertEqual(rules.slot_x(-540, 1), -540)
        self.assertEqual(rules.slot_x(0, 1), 0)
        self.assertEqual(rules.slot_x(-540, 1, "right"), 541)
        self.assertEqual(rules.slot_x(0, 1, "right"), 1)
        for side in rules.SIDES:
            for offset in (-540, -200, 0):
                x = rules.slot_x(offset, 1, side)
                self.assertEqual(rules.offset_of(x, 1, side), offset)

    def test_the_frame_shown(self):
        self.assertEqual(rules.frame_span(100, 540), (0, 100))
        self.assertEqual(rules.frame_span(100, 540, "right"), (440, 100))
        self.assertEqual(rules.frame_span(540, 540, "right"), (0, 540))

    def test_the_line_on_the_frame_s_inner_edge(self):
        self.assertEqual(rules.line_x(100, 540, 2), 98)
        self.assertEqual(rules.line_x(100, 540, 2, "right"), 440)

    def test_the_grip_on_the_panel_s_inner_side(self):
        self.assertEqual(rules.grip_x(540, 5), 535)
        self.assertEqual(rules.grip_x(540, 5, "right"), 0)

    def test_a_grip_drag_inward_widens(self):
        self.assertEqual(rules.dragged_width(360, 100, 1.0), 460)
        self.assertEqual(rules.dragged_width(360, -100, 1.0, "right"), 460)
        self.assertEqual(rules.dragged_width(360, 150, 1.5, "right"), 260)


class Reveal(unittest.TestCase):

    def test_only_with_edge_on_hidden_no_button_and_maya_active(self):
        self.assertTrue(rules.may_reveal(True, False, False, True))
        self.assertFalse(rules.may_reveal(False, False, False, True))
        self.assertFalse(rules.may_reveal(True, True, False, True))
        self.assertFalse(rules.may_reveal(True, False, True, True))
        self.assertFalse(rules.may_reveal(True, False, False, False))


class Hide(unittest.TestCase):

    def test_nothing_blocks(self):
        self.assertEqual(rules.hide_blockers(), [])

    def test_each_reason(self):
        for key in ("pinned", "held", "inside", "buttons", "popup", "modal",
                    "typing"):
            self.assertEqual(rules.hide_blockers(**{key: True}), [key])

    def test_several(self):
        self.assertEqual(rules.hide_blockers(pinned=True, popup=True),
                         ["pinned", "popup"])


class Hold(unittest.TestCase):

    def test_a_command_reveal_holds_until_entered_and_left(self):
        hold = rules.Hold()
        hold.start()
        self.assertTrue(hold.held)
        self.assertFalse(hold.leave())          # never entered: still held
        hold.enter()
        self.assertTrue(hold.leave())           # entered and left: released
        self.assertFalse(hold.held)

    def test_a_press_outside_releases(self):
        hold = rules.Hold()
        hold.start()
        self.assertTrue(hold.press_outside())
        self.assertFalse(hold.held)

    def test_not_held_nothing_to_release(self):
        hold = rules.Hold()
        self.assertFalse(hold.leave())
        self.assertFalse(hold.press_outside())


class NoMotion(unittest.TestCase):
    """Out and back are at once since 2026-11-19: no slide timing is left."""

    def test_no_slide_timing(self):
        for name in ("slide_x", "reveal_ms", "reveal_at", "FRAME_MS",
                     "HUB_DELAY_MS", "IN_MS", "OUT_MS"):
            self.assertFalse(hasattr(rules, name), name)


class Contains(unittest.TestCase):

    def test_contains(self):
        self.assertTrue(rules.contains((0, 0, 10, 10), (5, 5)))
        self.assertFalse(rules.contains((0, 0, 10, 10), (10, 5)))
        self.assertTrue(rules.contains((0, 0, 10, 10), (11, 5), margin=2))


class Purity(unittest.TestCase):

    def test_stdlib_only(self):
        code = ("import sys; sys.path.insert(0, 'SkeldarAnim'); "
                "import maya_edgerules; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)")
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)


if __name__ == "__main__":
    unittest.main()

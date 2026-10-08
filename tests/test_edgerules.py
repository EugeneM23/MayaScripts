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


class Slide(unittest.TestCase):

    def test_in_from_off_the_edge_to_zero(self):
        self.assertEqual(rules.slide_x(0.0, 540, True), -540)
        self.assertEqual(rules.slide_x(1.0, 540, True), 0)
        xs = [rules.slide_x(i / 20.0, 540, True) for i in range(21)]
        self.assertEqual(xs, sorted(xs))

    def test_out_from_zero_off_the_edge(self):
        self.assertEqual(rules.slide_x(0.0, 540, False), 0)
        self.assertEqual(rules.slide_x(1.0, 540, False), -540)
        xs = [rules.slide_x(i / 20.0, 540, False) for i in range(21)]
        self.assertEqual(xs, sorted(xs, reverse=True))

    def test_eased(self):
        # ease-out in: more than half way at half time
        self.assertGreater(rules.slide_x(0.5, 100, True), -50)


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

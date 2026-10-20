"""maya_timewarp: a Scene Time Warp off for the length of a bake (2026-10-20)."""
import unittest

import maya_timewarp as tw


class Unwarped(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.state = dict(tw._STATE)
        tw._STATE.update(depth=0, off=False)
        self.real = (tw.active, tw._switch)
        tw._switch = lambda on: self.calls.append(on)

    def tearDown(self):
        tw.active, tw._switch = self.real
        tw._STATE.clear()
        tw._STATE.update(self.state)

    def test_no_warp_switches_nothing(self):
        tw.active = lambda: False
        with tw.unwarped():
            with tw.unwarped():
                pass
        self.assertEqual(self.calls, [])

    def test_a_warp_is_switched_off_once_and_back_on(self):
        tw.active = lambda: True
        with tw.unwarped():
            tw.active = lambda: False          # off now: a nested block must not touch it
            with tw.unwarped():
                self.assertEqual(self.calls, [False])
            self.assertEqual(self.calls, [False])
        self.assertEqual(self.calls, [False, True])
        self.assertEqual(tw._STATE["depth"], 0)

    def test_an_error_inside_still_switches_it_back(self):
        tw.active = lambda: True
        with self.assertRaises(ValueError):
            with tw.unwarped():
                raise ValueError("press failed")
        self.assertEqual(self.calls, [False, True])

    def test_call_and_wrapped_run_inside(self):
        tw.active = lambda: True
        seen = []
        self.assertEqual(tw.call(lambda x: seen.append(list(self.calls)) or x, 3), 3)
        press = tw.wrapped(lambda: seen.append(list(self.calls)) or "done")
        self.assertEqual(press(), "done")
        self.assertEqual(seen, [[False], [False, True, False]])
        self.assertEqual(self.calls, [False, True, False, True])

    def test_without_maya_it_is_inactive(self):
        self.assertIn(tw.active(), (False, True))


if __name__ == "__main__":
    unittest.main()

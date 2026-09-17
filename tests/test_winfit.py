"""maya_winfit: a `cmds` window sized to its content, in the right units."""

import unittest

import maya_winfit as wf

from tests.uifakes import FakeUiCmds


class TestFitHeight(unittest.TestCase):

    def test_it_is_the_children_plus_the_gaps_plus_the_margin(self):
        self.assertEqual(wf.fit_height([10, 20, 30], spacing=3, margin=8),
                         60 + 6 + 8)

    def test_no_children_is_the_margin_alone(self):
        self.assertEqual(wf.fit_height([], spacing=3, margin=8), 8)


class TestLogicalUnits(unittest.TestCase):
    """`control -q -height` is physical, `window -e -height` is logical."""

    def test_pixels_are_divided_by_the_scale_and_rounded_up(self):
        self.assertEqual(wf.logical(678, 1.5), 452)
        self.assertEqual(wf.logical(679, 1.5), 453)

    def test_a_scale_of_one_changes_nothing(self):
        self.assertEqual(wf.logical(361, 1.0), 361)

    def test_a_nonsense_scale_is_treated_as_one(self):
        self.assertEqual(wf.logical(300, 0), 300)
        self.assertEqual(wf.logical(300, None), 300)


class TestDpiScale(unittest.TestCase):

    def test_the_real_scale_is_read(self):
        self.assertEqual(wf.dpi_scale(FakeUiCmds(dpi=1.5)), 1.5)

    def test_a_maya_without_the_command_means_no_scaling(self):
        class NoDpi(object):
            def __getattr__(self, name):
                raise AttributeError(name)
        self.assertEqual(wf.dpi_scale(NoDpi()), 1.0)

    def test_a_nonsense_answer_means_no_scaling(self):
        class Zero(object):
            def mayaDpiSetting(self, **_kw):
                return 0
        self.assertEqual(wf.dpi_scale(Zero()), 1.0)


class TestForgetSavedSize(unittest.TestCase):

    def test_a_saved_size_is_removed_and_reported(self):
        fake = FakeUiCmds(saved_pref=True)
        self.assertTrue(wf.forget_saved_size("win", fake))
        self.assertFalse(fake.saved_pref)
        self.assertEqual(len(fake.removed_prefs()), 1)

    def test_no_saved_size_touches_nothing(self):
        fake = FakeUiCmds(saved_pref=False)
        self.assertFalse(wf.forget_saved_size("win", fake))
        self.assertEqual(fake.removed_prefs(), [])

    def test_a_maya_that_raises_is_not_a_traceback(self):
        class Raises(object):
            def windowPref(self, *_a, **_kw):
                raise RuntimeError("no such window")
        self.assertFalse(wf.forget_saved_size("win", Raises()))


class TestFitWindow(unittest.TestCase):

    def test_the_window_takes_the_measured_height_in_logical_units(self):
        """The live bug: 678 px of controls written back as a height made
        a 1018 px window on a 150 % display."""
        fake = FakeUiCmds(control_height=30, dpi=1.5)
        fake.window("win", title="x")
        fake.children[:] = ["a", "b", "c", "d"]
        written = wf.fit_window("win", "col", fake, spacing=4, margin=12)
        pixels = 4 * 30 + 3 * 4 + 12
        self.assertEqual(written, wf.logical(pixels, 1.5))
        self.assertEqual(fake.windows["win"]["height"], written)

    def test_the_children_are_measured_one_by_one_after_layout(self):
        fake = FakeUiCmds(control_height=25)
        fake.window("win", title="x")
        fake.children[:] = ["a", "b"]
        wf.fit_window("win", "col", fake, spacing=3, margin=0)
        asked = [c for c in fake.calls if c[0] == "control"
                 and (c[2].get("query") or c[2].get("q"))]
        self.assertEqual([c[1][0] for c in asked], ["col|a", "col|b"])


if __name__ == "__main__":
    unittest.main()

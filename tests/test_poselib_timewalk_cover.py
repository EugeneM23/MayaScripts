"""timewalk's progress window, the cases `test_poselib_timewalk` leaves out: a Maya that cannot be asked
whether it is in batch mode, and a progress window that goes away in the middle of a walk. Whatever
the window does, the walk goes on.
"""
import unittest

from maya_poselib import timewalk


class WindowCmds(object):
    """`about`, `progressWindow`: `fail_on` names the calls that raise (`about`, `open`, `query`,
    `step`, `end`)."""

    def __init__(self, fail_on=()):
        self.fail_on = set(fail_on)
        self.log = []

    def about(self, batch=False):
        if "about" in self.fail_on:
            raise RuntimeError("no Maya to ask")
        return False

    def progressWindow(self, **kwargs):
        if kwargs.get("endProgress"):
            self.log.append("end")
            if "end" in self.fail_on:
                raise RuntimeError("the window is gone")
            return None
        if kwargs.get("query"):
            self.log.append("query")
            if "query" in self.fail_on:
                raise RuntimeError("the window is gone")
            return False
        if kwargs.get("edit"):
            self.log.append("step")
            if "step" in self.fail_on:
                raise RuntimeError("the window is gone")
            return None
        self.log.append("open")
        if "open" in self.fail_on:
            raise RuntimeError("no UI")
        return None


class ProgressGone(unittest.TestCase):

    def setUp(self):
        saved = timewalk.cmds
        self.addCleanup(setattr, timewalk, "cmds", saved)

    def use(self, **kwargs):
        timewalk.cmds = WindowCmds(**kwargs)
        return timewalk.cmds

    def test_a_maya_that_cannot_say_whether_it_is_in_batch_mode_opens_no_window(self):
        fake = self.use(fail_on=["about"])
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertFalse(progress.on)
            self.assertTrue(progress.step("1"))
            self.assertFalse(progress.asked())
        self.assertEqual(fake.log, [])

    def test_a_window_that_goes_away_before_it_is_asked_stops_asking(self):
        fake = self.use(fail_on=["query"])
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertTrue(progress.on)
            self.assertFalse(progress.asked())
            self.assertFalse(progress.on)
            self.assertFalse(progress.asked())
        self.assertEqual(fake.log, ["open", "query"])

    def test_a_window_that_goes_away_in_a_step_lets_the_walk_go_on_and_is_never_asked_again(self):
        fake = self.use(fail_on=["step"])
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertTrue(progress.step("1"))
            self.assertFalse(progress.on)
            self.assertTrue(progress.step("2"))
        self.assertEqual(fake.log, ["open", "step"])

    def test_a_window_that_cannot_be_ended_is_ended_all_the_same(self):
        fake = self.use(fail_on=["end"])
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertTrue(progress.on)
        self.assertFalse(progress.on)
        self.assertEqual(fake.log, ["open", "end"])

    def test_the_walk_s_own_error_passes_through_the_window(self):
        fake = self.use()
        with self.assertRaises(KeyError):
            with timewalk.Progress("Saving Walk", 3):
                raise KeyError("walk failed")
        self.assertEqual(fake.log, ["open", "end"])


if __name__ == "__main__":
    unittest.main()

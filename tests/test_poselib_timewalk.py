"""The pose library's time walk and its progress window (the animation cards, 2026-10-03).

An animation card is saved and applied by walking the time: per frame the scene is read (the
bones' worlds) or written (keys at that frame). `timewalk.Walk` is that walk as a context:
the animator's unkeyed tweaks read FIRST (any time change throws them away: measured in mayapy,
a locator's keyed ty set to 99 by hand read 1.112 after a two-frame walk), the viewport
suspended, the solve's evaluation (DG) around the whole walk when `fresh`, each frame an
`MAnimControl.setCurrentTime` (measured unrecorded: the undo queue's last name unchanged across
a walk; and fresh: a spline read 1.53 / 6.37 / 16.25 at frames 3 / 7 / 15 right after each
set). On exit the time goes back, the viewport resumes, the evaluation goes back and the tweaks
are set back - all but the plugs the press keyed (`walk.keyed`).

`Progress` is Maya's cancellable progress window, and nothing in batch mode (measured:
`progressWindow` answers None there and `isCancelled` None).

The scene runs on fakes rebound as module attributes (CLAUDE.md's rule) and restored after.
"""

import contextlib
import unittest

from maya_poselib import timewalk


class FakeTime(object):
    """om.MTime: a value and a unit."""

    def __init__(self, value, unit=None):
        self.value, self.unit = value, unit

    @staticmethod
    def uiUnit():
        return "ntsc"

    def __eq__(self, other):
        return isinstance(other, FakeTime) and (self.value, self.unit) == (other.value, other.unit)

    def __repr__(self):
        return "MTime(%r, %r)" % (self.value, self.unit)


class FakeOm(object):
    MTime = FakeTime


class FakeAnimControl(object):
    """oma.MAnimControl: the current time, every set logged into the shared log."""

    def __init__(self, log, start=12.0, fail_on=()):
        self.log, self.now, self.fail_on = log, FakeTime(start, "ntsc"), set(fail_on)

    def currentTime(self):
        return self.now

    def setCurrentTime(self, time):
        if time.value in self.fail_on:
            raise RuntimeError("setCurrentTime failed")
        self.log.append(("time", time.value))
        self.now = time


class FakeOma(object):
    def __init__(self, control):
        self.MAnimControl = control


class FakeTweaks(object):
    """keys.Tweaks: its reading and every restore logged with the skip it was given."""

    def __init__(self, log):
        self.log = log
        log.append(("tweaks",))

    def restore(self, skip=()):
        self.log.append(("restore", tuple(skip)))
        return ["back"]


class FakeKeys(object):
    def __init__(self, log):
        self.Tweaks = lambda: FakeTweaks(log)


class FakeCmds(object):
    """refresh / about / progressWindow, logged."""

    def __init__(self, log, batch=False, cancel_after=None, open_fails=False):
        self.log, self.batch = log, batch
        self.cancel_after, self.steps, self.open_fails = cancel_after, 0, open_fails

    def refresh(self, suspend=None, **kw):
        self.log.append(("suspend",) if suspend else ("resume",))

    def about(self, batch=False):
        assert batch
        return self.batch

    def progressWindow(self, **kw):
        # every call recorded, batch mode or not: an AssertionError raised here would be caught
        # by Progress's own "no UI" guard, and a test asserting none came could not fail
        if kw.get("query"):
            assert kw.get("isCancelled"), kw
            return self.cancel_after is not None and self.steps >= self.cancel_after
        if kw.get("endProgress"):
            self.log.append(("progress end",))
            return None
        if kw.get("edit"):
            self.steps += 1
            self.log.append(("progress step", kw.get("step"), kw.get("status")))
            return None
        if self.open_fails:
            raise RuntimeError("progressWindow: no UI")
        self.log.append(("progress open", kw.get("title"), kw.get("maxValue"),
                         kw.get("isInterruptable")))
        return None


class Rebound(unittest.TestCase):
    """timewalk's `cmds`, `om`, `oma`, `keys` and `_evaluation` replaced by fakes logging into
    `self.log`, put back after."""

    def setUp(self):
        self.log = []
        saved = {name: getattr(timewalk, name) for name in
                 ("cmds", "om", "oma", "keys", "_evaluation")}
        self.addCleanup(lambda: [setattr(timewalk, k, v) for k, v in saved.items()])
        self.control = FakeAnimControl(self.log)
        timewalk.cmds = FakeCmds(self.log)
        timewalk.om = FakeOm()
        timewalk.oma = FakeOma(self.control)
        timewalk.keys = FakeKeys(self.log)
        self.fresh_args = []

        @contextlib.contextmanager
        def evaluation(tweaks, skip):
            self.fresh_args.append((tweaks, skip))
            self.log.append(("fresh enter",))
            try:
                yield
            finally:
                self.log.append(("fresh exit", tuple(skip)))
        timewalk._evaluation = evaluation


class WalkOrder(Rebound):

    def test_tweaks_first_then_suspend_then_the_evaluation(self):
        with timewalk.Walk(fresh=True):
            self.assertEqual(self.log, [("tweaks",), ("suspend",), ("fresh enter",)])

    def test_go_sets_the_time_in_the_ui_unit(self):
        with timewalk.Walk(fresh=True) as walk:
            walk.go(5)
            walk.go(6.0)
            self.assertEqual(walk.frame, 6.0)
        times = [entry for entry in self.log if entry[0] == "time"]
        self.assertEqual(times[:2], [("time", 5), ("time", 6.0)])
        self.assertEqual(self.control.now, FakeTime(12.0, "ntsc"))      # back where it was

    def test_exit_time_back_resume_evaluation_then_tweaks_but_the_keyed(self):
        with timewalk.Walk(fresh=True) as walk:
            walk.go(5)
            walk.keyed.extend(["a.tx", "a.ty"])
        tail = self.log[self.log.index(("time", 5)) + 1:]
        self.assertEqual(tail, [("time", 12.0), ("resume",), ("fresh exit", ("a.tx", "a.ty")),
                                ("restore", ("a.tx", "a.ty"))])

    def test_the_evaluation_is_handed_the_walks_own_keyed_list(self):
        # its own set-back after its switch skips what the press keyed - extended later
        with timewalk.Walk(fresh=True) as walk:
            pass
        (tweaks, skip), = self.fresh_args
        self.assertIs(skip, walk.keyed)
        self.assertIsInstance(tweaks, FakeTweaks)

    def test_not_fresh_has_no_evaluation_switch(self):
        with timewalk.Walk(fresh=False) as walk:
            walk.go(3)
        self.assertEqual(self.log, [("tweaks",), ("suspend",), ("time", 3), ("time", 12.0),
                                    ("resume",), ("restore", ())])
        self.assertEqual(self.fresh_args, [])

    def test_an_exception_inside_still_puts_everything_back(self):
        with self.assertRaises(ValueError):
            with timewalk.Walk(fresh=True) as walk:
                walk.go(9)
                walk.keyed.append("a.rx")
                raise ValueError("solve failed")
        self.assertEqual(self.log[-4:], [("time", 12.0), ("resume",), ("fresh exit", ("a.rx",)),
                                         ("restore", ("a.rx",))])

    def test_a_failing_step_on_exit_does_not_stop_the_others(self):
        self.control.fail_on.add(12.0)              # the time cannot go back
        with self.assertRaises(RuntimeError):
            with timewalk.Walk(fresh=True) as walk:
                walk.go(4)
        self.assertEqual(self.log[-3:], [("resume",), ("fresh exit", ()), ("restore", ())])

    def test_an_evaluation_that_fails_to_open_resumes_the_viewport(self):
        @contextlib.contextmanager
        def broken(tweaks, skip):
            raise RuntimeError("evaluationManager refused")
            yield                                    # pragma: no cover
        timewalk._evaluation = broken
        with self.assertRaises(RuntimeError):
            with timewalk.Walk(fresh=True):
                pass
        self.assertEqual(self.log, [("tweaks",), ("suspend",), ("resume",)])

    def test_an_evaluation_that_cannot_be_made_resumes_the_viewport(self):
        # `_evaluation` imports the solver late: an ImportError there (a module mid-update) must
        # not leave the viewport suspended for the rest of the session
        def unimportable(tweaks, skip):
            raise ImportError("cannot import name 'rigsolve'")
        timewalk._evaluation = unimportable
        with self.assertRaises(ImportError):
            with timewalk.Walk(fresh=True):
                pass
        self.assertEqual(self.log, [("tweaks",), ("suspend",), ("resume",)])

    def test_arrive_on_the_frame_it_stands_on_does_not_set_the_time(self):
        """The final review (M2): a `setCurrentTime` to the frame the scene stands on throws
        away every unkeyed tweak, so a press pasting AT the current frame reads the scene as it
        stands there - until the walk has moved once; after that `arrive` is `go`."""
        with timewalk.Walk(fresh=True) as walk:
            self.assertFalse(walk.arrive(12.0))          # the frame it entered on: no time set
            self.assertEqual(walk.frame, 12.0)
            self.assertFalse(walk.arrive(12))
            self.assertTrue(walk.arrive(13))
            self.assertTrue(walk.arrive(12.0))           # it has moved: the frame is read again
        times = [entry for entry in self.log if entry[0] == "time"]
        self.assertEqual(times, [("time", 13), ("time", 12.0), ("time", 12.0)])

    def test_arrive_elsewhere_goes(self):
        with timewalk.Walk(fresh=True) as walk:
            self.assertTrue(walk.arrive(40))
        self.assertEqual([entry for entry in self.log if entry[0] == "time"],
                         [("time", 40), ("time", 12.0)])

    def test_restore_all_sets_back_every_tweak_now_and_on_exit(self):
        # a cancelled press: its chunk undone, nothing was keyed after all
        with timewalk.Walk(fresh=True) as walk:
            walk.go(2)
            walk.keyed.extend(["a.tx"])
            back = walk.restore_all()
            self.assertEqual(back, ["back"])
            self.assertEqual(self.log[-1], ("restore", ()))
            self.assertEqual(walk.keyed, [])
        self.assertEqual(self.log[-2:], [("fresh exit", ()), ("restore", ())])


class DefaultEvaluation(unittest.TestCase):

    def test_it_is_the_solves_evaluation(self):
        from maya_poselib import rigsolve
        saved = rigsolve._fresh
        self.addCleanup(setattr, rigsolve, "_fresh", saved)
        rigsolve._fresh = lambda tweaks, skip: ("fresh", tweaks, skip)
        self.assertEqual(timewalk._evaluation("T", ["s"]), ("fresh", "T", ["s"]))


class ProgressWindow(Rebound):

    def test_batch_never_opens_a_window_and_always_goes_on(self):
        # the fake opens a window in batch mode as anywhere else: only Progress's own question
        # (`about -batch`) keeps it shut
        timewalk.cmds = FakeCmds(self.log, batch=True)
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertTrue(progress.step("frame 1"))
            self.assertTrue(progress.step("frame 2"))
            self.assertFalse(progress.on)
        self.assertEqual(self.log, [])

    def test_opens_steps_and_ends(self):
        with timewalk.Progress("Saving Walk", 48) as progress:
            self.assertTrue(progress.step("frame 0"))
        self.assertEqual(self.log, [("progress open", "Saving Walk", 48, True),
                                    ("progress step", 1, "frame 0"), ("progress end",)])

    def test_esc_answers_false_and_stays_false(self):
        timewalk.cmds = FakeCmds(self.log, cancel_after=2)
        with timewalk.Progress("Pasting Walk", 10) as progress:
            self.assertTrue(progress.step("1"))
            self.assertFalse(progress.step("2"))
            self.assertFalse(progress.step("3"))
            self.assertTrue(progress.cancelled)

    def test_a_window_that_cannot_open_is_a_no_op(self):
        timewalk.cmds = FakeCmds(self.log, open_fails=True)
        with timewalk.Progress("Saving Walk", 3) as progress:
            self.assertTrue(progress.step("1"))
        self.assertEqual(self.log, [])

    def test_the_window_ends_when_the_press_raises(self):
        with self.assertRaises(KeyError):
            with timewalk.Progress("Saving Walk", 3):
                raise KeyError("x")
        self.assertEqual(self.log[-1], ("progress end",))

    def test_a_total_of_zero_still_opens_a_window_of_one(self):
        with timewalk.Progress("Saving Walk", 0):
            pass
        self.assertEqual(self.log[0], ("progress open", "Saving Walk", 1, True))


if __name__ == "__main__":
    unittest.main()

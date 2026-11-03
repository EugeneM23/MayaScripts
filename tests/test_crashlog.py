"""The crash log: faulthandler naming the Python line of a hard crash.

Maya writes a minidump and no readable log, so a crash in a Qt timer's slot
says nothing about which slot. `maya_crashlog` points Python's faulthandler at
a file of ours, so the next crash names the function and the line - and the
session after it reads that file back and says so.

Every seam is injectable: these tests need neither Maya nor a real crash.
"""
import os
import shutil
import tempfile
import unittest

import maya_crashlog as crashlog


class FakeFaulthandler(object):
    """Enough of the module to see what was asked of it."""

    def __init__(self, raises=False):
        self.file = None
        self.all_threads = None
        self.calls = 0
        self.raises = raises

    def enable(self, file=None, all_threads=True):
        self.calls += 1
        if self.raises:
            raise RuntimeError("no handler here")
        self.file = file
        self.all_threads = all_threads

    def is_enabled(self):
        return self.file is not None


class Folder(unittest.TestCase):

    def setUp(self):
        self.app = tempfile.mkdtemp(prefix="crashlog_")
        self.addCleanup(shutil.rmtree, self.app, ignore_errors=True)
        crashlog.forget()
        self.addCleanup(crashlog.forget)

    def test_the_log_lives_in_its_own_folder_under_the_user_s_app_dir(self):
        self.assertEqual(crashlog.folder(self.app),
                         os.path.join(self.app, crashlog.FOLDER))

    def test_the_folder_is_made_on_enable(self):
        crashlog.enable(self.app, faulthandler=FakeFaulthandler())
        self.assertTrue(os.path.isdir(crashlog.folder(self.app)))

    def test_enable_points_faulthandler_at_our_file_over_every_thread(self):
        fake = FakeFaulthandler()
        path = crashlog.enable(self.app, faulthandler=fake)
        self.assertEqual(path, crashlog.path(self.app))
        self.assertIsNotNone(fake.file)
        self.assertEqual(fake.file.name, path)
        self.assertTrue(fake.all_threads)

    def test_the_handle_is_kept_open_so_the_handler_can_write_at_crash_time(self):
        fake = FakeFaulthandler()
        crashlog.enable(self.app, faulthandler=fake)
        self.assertFalse(fake.file.closed)

    def test_the_file_opens_with_a_header_naming_the_session(self):
        crashlog.enable(self.app, faulthandler=FakeFaulthandler())
        with open(crashlog.path(self.app)) as fh:
            head = fh.read()
        self.assertIn("SkeldarAnim", head)
        self.assertIn(str(os.getpid()), head)

    def test_a_second_enable_in_one_session_does_nothing(self):
        fake = FakeFaulthandler()
        crashlog.enable(self.app, faulthandler=fake)
        crashlog.enable(self.app, faulthandler=fake)
        self.assertEqual(fake.calls, 1)

    def test_a_faulthandler_that_refuses_is_no_error(self):
        self.assertIsNone(crashlog.enable(
            self.app, faulthandler=FakeFaulthandler(raises=True)))

    def test_without_faulthandler_at_all_it_is_no_error(self):
        self.assertIsNone(crashlog.enable(self.app, faulthandler=None))


class LastCrash(unittest.TestCase):
    """A crash leaves its traceback in the file; the next session reads it."""

    def setUp(self):
        self.app = tempfile.mkdtemp(prefix="crashlog_")
        self.addCleanup(shutil.rmtree, self.app, ignore_errors=True)
        crashlog.forget()
        self.addCleanup(crashlog.forget)

    def _write(self, text):
        os.makedirs(crashlog.folder(self.app), exist_ok=True)
        with open(crashlog.path(self.app), "w") as fh:
            fh.write(text)

    CRASH = """SkeldarAnim 2026-11-03 08:09:00 pid 4242
Windows fatal exception: access violation

Current thread 0x00001234 (most recent call first):
  File "C:/x/maya_windowlight.py", line 612 in _follow
  File "C:/x/maya_windowlight.py", line 500 in poll
"""

    def test_a_file_holding_a_traceback_is_a_crash(self):
        self.assertTrue(crashlog.is_crash(self.CRASH))

    def test_a_header_alone_is_no_crash(self):
        self.assertFalse(crashlog.is_crash(
            "SkeldarAnim 2026-11-03 08:00:00 pid 1\n"))

    def test_enable_keeps_a_previous_crash_under_its_own_name(self):
        self._write(self.CRASH)
        crashlog.enable(self.app, faulthandler=FakeFaulthandler())
        kept = crashlog.reports(self.app)
        self.assertEqual(len(kept), 1)
        with open(kept[0]) as fh:
            self.assertIn("_follow", fh.read())

    def test_enable_answers_what_the_previous_crash_said(self):
        self._write(self.CRASH)
        fake = FakeFaulthandler()
        crashlog.enable(self.app, faulthandler=fake)
        last = crashlog.previous()
        self.assertIn("maya_windowlight.py", last)
        self.assertIn("_follow", last)

    def test_a_clean_previous_session_is_not_kept_and_says_nothing(self):
        self._write("SkeldarAnim 2026-11-03 08:00:00 pid 1\n")
        crashlog.enable(self.app, faulthandler=FakeFaulthandler())
        self.assertEqual(crashlog.reports(self.app), [])
        self.assertIsNone(crashlog.previous())

    def test_the_kept_reports_are_newest_first_and_capped(self):
        os.makedirs(crashlog.folder(self.app), exist_ok=True)
        for i in range(crashlog.KEEP + 4):
            name = "crash_2026110%d_0000%02d.txt" % (1 + i // 10, i)
            with open(os.path.join(crashlog.folder(self.app), name), "w") as fh:
                fh.write(self.CRASH)
        self._write(self.CRASH)
        crashlog.enable(self.app, faulthandler=FakeFaulthandler())
        kept = crashlog.reports(self.app)
        self.assertEqual(len(kept), crashlog.KEEP)
        names = [os.path.basename(p) for p in kept]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_the_line_names_the_file_and_the_function(self):
        self.assertEqual(
            crashlog.blamed(self.CRASH),
            "maya_windowlight.py line 612 in _follow")

    def test_a_crash_with_no_python_frame_is_named_as_such(self):
        self.assertEqual(
            crashlog.blamed("Windows fatal exception: access violation\n"),
            "no Python frame")


if __name__ == "__main__":
    unittest.main()

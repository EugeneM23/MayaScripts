"""Scene tabs: no «save changes?» before an open that goes into a tab, and Maya's
Open into a tab with tabs off (2026-10-16)."""
import os
import unittest

from maya_scenetabs import hooks, records, savechanges, scope

MAYA_FILE = os.path.join(os.environ.get("MAYA_LOCATION", "C:/Program Files/Autodesk/Maya2027"),
                         "scripts", "others", savechanges.FILE)


class OpenedPath(unittest.TestCase):

    def test_maya_s_file_open_action(self):
        action = ('file -f -options "v=0;"  -esn false  -ignoreVersion  -typ "mayaAscii" '
                  '-o "C:/w/a b/shot.ma";addRecentFile("C:/w/a b/shot.ma", "mayaAscii")')
        self.assertEqual(savechanges.opened_path(action), "C:/w/a b/shot.ma")

    def test_the_recent_files_and_long_flag_forms(self):
        self.assertEqual(savechanges.opened_path('file -f -typ "mayaBinary" -o "C:/w/x.mb";'
                                                 '{addRecentFile("C:/w/x.mb", "mayaBinary");}'),
                         "C:/w/x.mb")
        self.assertEqual(savechanges.opened_path('file -f -open "C:/w/x.ma"'), "C:/w/x.ma")

    def test_an_escaped_quote_and_backslash(self):
        self.assertEqual(savechanges.opened_path('file -f -o "C:\\\\w\\\\q\\"x.ma"'), 'C:\\w\\q"x.ma')

    def test_no_open_no_path(self):
        for action in ("", "file -f -new", 'file -f -options "-o x" -new',
                       'file -op "v=0" -typ "mayaAscii" -nr "C:/w/x.ma"'):
            self.assertEqual(savechanges.opened_path(action), "", action)


class Renamed(unittest.TestCase):

    def test_maya_s_own_file_gets_its_proc_renamed_once(self):
        if not os.path.isfile(MAYA_FILE):
            self.skipTest("no Maya install")
        with open(MAYA_FILE, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        got = savechanges.renamed(text)
        self.assertIsNotNone(got)
        self.assertIn("global proc int %s(" % savechanges.MAYA, got)
        self.assertIsNone(savechanges.HEADER.search(got))
        self.assertEqual(len(got), len(text) - len("saveChanges ") + len(savechanges.MAYA))

    def test_a_file_this_does_not_know_is_refused(self):
        self.assertIsNone(savechanges.renamed("global proc other() {}"))
        self.assertIsNone(savechanges.renamed("global proc int saveChanges(string $a) {}\n"
                                              "global proc int saveChanges(string $b) {}"))

    def test_the_wrapper_falls_back_to_maya_s_copy(self):
        self.assertIn("return %s($saveChangeAction);" % savechanges.MAYA, savechanges.WRAPPER)
        self.assertIn("catch($tab = python(", savechanges.WRAPPER)
        self.assertIn("global proc int saveChanges(string $saveChangeAction)", savechanges.WRAPPER)


class SkipQuestion(unittest.TestCase):

    def setUp(self):
        self.saved = hooks.goes_to_tab
        self.asked = []

    def tearDown(self):
        hooks.goes_to_tab = self.saved

    def test_an_open_the_check_takes_into_a_tab_skips_the_question(self):
        hooks.goes_to_tab = lambda path: self.asked.append(path) or True
        self.assertTrue(savechanges.skip_question('file -f -o "C:/w/b.ma";addRecentFile("C:/w/b.ma", "")'))
        self.assertEqual(self.asked, ["C:/w/b.ma"])

    def test_new_and_every_other_open_ask_as_maya_does(self):
        hooks.goes_to_tab = lambda path: False
        self.assertFalse(savechanges.skip_question('file -f -o "C:/w/b.ma"'))
        hooks.goes_to_tab = lambda path: self.fail("asked for a New")
        self.assertFalse(savechanges.skip_question("file -f -new"))

    def test_an_error_asks_as_maya_does(self):
        def broken(path):
            raise RuntimeError("boom")
        hooks.goes_to_tab = broken
        self.assertFalse(savechanges.skip_question('file -f -o "C:/w/b.ma"'))


class Redirects(unittest.TestCase):
    """hooks.redirects: which of Maya's opens go into a tab."""

    def setUp(self):
        self.saved = (hooks.session.is_on, scope.opens_in_tab, records.holds_session)
        self.on, self.in_tab, self.session_file = False, True, False
        hooks.session.is_on = lambda: self.on
        scope.opens_in_tab = lambda path, cmds_=None: self.in_tab
        records.holds_session = lambda path: self.session_file

    def tearDown(self):
        hooks.session.is_on, scope.opens_in_tab, records.holds_session = self.saved

    def test_tabs_off_a_scene_beside_an_open_one_goes_into_a_tab(self):
        self.assertTrue(hooks.redirects("C:/w/b.ma"))
        self.assertTrue(hooks.redirects("C:/w/b.MB"))

    def test_tabs_off_an_empty_scene_or_the_same_file_opens_as_maya_does(self):
        self.in_tab = False
        self.assertFalse(hooks.redirects("C:/w/b.ma"))

    def test_a_saved_session_and_a_file_that_is_no_maya_scene_open_as_maya_does(self):
        self.session_file = True
        self.assertFalse(hooks.redirects("C:/w/session.ma"))
        self.session_file = False
        self.assertFalse(hooks.redirects("C:/w/clip.fbx"))

    def test_tabs_on_every_maya_scene_but_a_session(self):
        self.on, self.in_tab = True, False
        self.assertTrue(hooks.redirects("C:/w/b.ma"))

    def test_with_the_checks_off_nothing_goes_to_a_tab(self):
        state = hooks._st()
        saved = list(state["callbacks"])
        state["callbacks"][:] = []
        try:
            self.assertFalse(hooks.goes_to_tab("C:/w/b.ma"))
            state["callbacks"].append("a callback")
            self.assertTrue(hooks.goes_to_tab("C:/w/b.ma"))
            with hooks.bypass():
                self.assertFalse(hooks.goes_to_tab("C:/w/b.ma"))
        finally:
            state["callbacks"][:] = saved


if __name__ == "__main__":
    unittest.main()

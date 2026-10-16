import os
import shutil
import sys
import tempfile
import unittest

from maya_scenetabs import records, workspaces

HERE = os.path.dirname(os.path.abspath(__file__))
TABS = os.path.join(os.path.dirname(HERE), "SkeldarAnim", "maya_scenetabs")


class FakeCmds(object):
    """Maya's workspace list as the 2026-10-16 measurement found it: names listed with
    spaces, a delete of the current workspace doing nothing, a saveAs making its name
    current."""

    def __init__(self, listed, current, startup="", prefs="", batch=False):
        self.listed = list(listed)
        self.current = current
        self.vars = {workspaces.STARTUP_VAR: startup} if startup else {}
        self.prefs = prefs
        self.batch = batch
        self.calls = []

    def about(self, batch=False):
        return self.batch

    def internalVar(self, userPrefDir=False):
        return self.prefs

    def optionVar(self, exists=None, q=None, stringValue=None):
        if exists is not None:
            return exists in self.vars
        if q is not None:
            return self.vars.get(q, 0)
        self.vars[stringValue[0]] = stringValue[1]

    def workspaceLayoutManager(self, listLayouts=False, q=False, current=False, saveAs=None, delete=None):
        if listLayouts:
            return list(self.listed)
        if q and current:
            return self.current
        if saveAs is not None:
            self.calls.append(("saveAs", saveAs))
            shown = saveAs.replace("_", " ")
            if shown not in self.listed:
                self.listed.append(shown)
            self.current = shown
        if delete is not None:
            self.calls.append(("delete", delete))
            if delete in self.listed and delete != self.current:
                self.listed.remove(delete)


class Names(unittest.TestCase):

    def test_ours_in_both_spellings_only(self):
        self.assertTrue(workspaces.is_ours("SkeldarTab tab untitled1"))
        self.assertTrue(workspaces.is_ours("SkeldarTab_tab_untitled1"))
        for name in ("General", "Animation", "SkeldarTabby", "My SkeldarTab", ""):
            self.assertFalse(workspaces.is_ours(name), name)

    def test_a_file_is_listed_with_spaces(self):
        self.assertEqual(workspaces.listed_name("Modeling_-_Standard.json"), "Modeling - Standard")
        self.assertEqual(workspaces.listed_name("SkeldarTab_tab_A.json"), "SkeldarTab tab A")

    def test_home_is_the_animators_last_written_workspace(self):
        listed = ["Animation", "General", "Rigging", "SkeldarTab tab A"]
        written = {"Animation": 1.0, "General": 2.0, "Rigging": 3.0, "SkeldarTab tab A": 9.0}
        self.assertEqual(workspaces.home(listed, written), "Rigging")
        self.assertEqual(workspaces.home(listed, {}), "General")
        self.assertEqual(workspaces.home(["Animation", "SkeldarTab tab A"], {}), "Animation")


class Sweep(unittest.TestCase):

    def setUp(self):
        self.prefs = tempfile.mkdtemp()
        folder = os.path.join(self.prefs, "workspaces")
        os.makedirs(folder)
        for name, when in (("General.json", 100), ("Rigging.json", 300), ("SkeldarTab_tab_A.json", 900)):
            path = os.path.join(folder, name)
            open(path, "w").close()
            os.utime(path, (when, when))

    def tearDown(self):
        shutil.rmtree(self.prefs, ignore_errors=True)

    def test_every_tab_workspace_goes_and_the_screen_is_kept_under_the_animators_own(self):
        cmds = FakeCmds(["General", "Rigging", "SkeldarTab tab A", "SkeldarTab tab B"],
                        current="SkeldarTab tab A", startup="SkeldarTab tab A", prefs=self.prefs)
        self.assertEqual(workspaces.sweep(cmds), 2)
        self.assertEqual(cmds.calls[0], ("saveAs", "Rigging"))
        self.assertEqual(cmds.listed, ["General", "Rigging"])
        self.assertEqual(cmds.current, "Rigging")
        self.assertEqual(cmds.vars[workspaces.STARTUP_VAR], "Rigging")

    def test_a_current_workspace_of_the_animators_is_left_alone(self):
        cmds = FakeCmds(["General", "SkeldarTab tab A"], current="General", startup="General",
                        prefs=self.prefs)
        self.assertEqual(workspaces.sweep(cmds), 1)
        self.assertNotIn("saveAs", [call[0] for call in cmds.calls])
        self.assertEqual(cmds.vars[workspaces.STARTUP_VAR], "General")

    def test_nothing_of_ours_nothing_done(self):
        cmds = FakeCmds(["General"], current="General", prefs=self.prefs)
        self.assertEqual(workspaces.sweep(cmds), 0)
        self.assertEqual(cmds.calls, [])

    def test_batch_does_nothing(self):
        cmds = FakeCmds(["SkeldarTab tab A"], current="SkeldarTab tab A", batch=True, prefs=self.prefs)
        self.assertEqual(workspaces.sweep(cmds), 0)
        self.assertEqual(cmds.calls, [])

    def test_once_a_session(self):
        calls = []
        saved, flag = workspaces.sweep, getattr(sys, "_skeldar_tab_workspaces_swept", None)
        workspaces.sweep = lambda cmds=None: calls.append(1) or 0
        try:
            sys._skeldar_tab_workspaces_swept = False
            workspaces.sweep_once()
            workspaces.sweep_once()
        finally:
            workspaces.sweep = saved
            if flag is None:
                del sys._skeldar_tab_workspaces_swept
            else:
                sys._skeldar_tab_workspaces_swept = flag
        self.assertEqual(calls, [1])


class NoWorkspacePerTab(unittest.TestCase):

    def test_a_tab_names_no_workspace(self):
        self.assertNotIn("layout", records.new_tab("tab_a", "a.ma", "film", {}))
        self.assertNotIn("layout", records.loads(records.dumps(
            {"version": records.VERSION, "active": "tab_a", "session": "",
             "tabs": [dict(records.new_tab("tab_a", "a.ma", "film", {}), layout="SkeldarTab_tab_a")]}))["tabs"][0])

    def test_only_the_sweep_touches_workspaces(self):
        for name in sorted(os.listdir(TABS)):
            if name.endswith(".py") and name != "workspaces.py":
                with open(os.path.join(TABS, name), encoding="utf-8") as handle:
                    self.assertNotIn("workspaceLayoutManager", handle.read(), name)


if __name__ == "__main__":
    unittest.main()

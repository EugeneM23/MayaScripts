"""Tests for the window's pure helpers.

The widgets need a Maya session; what is testable here is the cache, which is
where a mistake would quietly hand the user a wrong list.
"""

import collections
import sys
import types
import unittest


def _install_fake_maya():
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import records, window  # noqa: E402


class CacheRoundTrip(unittest.TestCase):

    def payload(self):
        return {"assets": [
            {"name": "A_Jump", "package": "/Game/Manny/A_Jump", "skeleton": "SK",
             "frames": 45, "length": 1.5, "fps": 30.0},
            {"name": "A_Walk", "package": "/Game/Manny/A_Walk"}]}

    def test_records_survive_a_save_and_load(self):
        original = records.parse_payload(self.payload())
        again = window.records_from_cache(window.cache_payload(original))
        self.assertEqual(again, original)

    def test_the_cache_keeps_the_project(self):
        cached = window.cache_payload([], project="C:/x/Atone.uproject")
        self.assertEqual(cached["project"], "C:/x/Atone.uproject")

    def test_the_cache_remembers_which_editor_was_chosen(self):
        """With two projects open, reopening the window should not change which
        one it reads."""
        cached = window.cache_payload([], project="", choice="Atone")
        self.assertEqual(cached["choice"], "Atone")

    def test_the_cache_is_shaped_like_the_editor_reply(self):
        """One parser reads both, so the shapes must not drift apart."""
        cached = window.cache_payload(records.parse_payload(self.payload()))
        self.assertIn("assets", cached)
        self.assertEqual(len(records.parse_payload(cached)), 2)

    def test_an_empty_cache_loads_as_an_empty_list(self):
        self.assertEqual(window.records_from_cache({"assets": []}), [])

    def test_a_cache_written_before_the_picker_still_loads(self):
        """An old cache has no 'choice' key; that must not break the window."""
        self.assertEqual(window.records_from_cache({"assets": []}), [])

    def test_the_cache_keeps_the_content_dir(self):
        cached = window.cache_payload([], content_dir="C:/proj/Content")
        self.assertEqual(cached["content_dir"], "C:/proj/Content")

    def test_a_phase_one_cache_reads_as_no_content_dir(self):
        """A cache written before this key existed must load as ''. The
        payload shape is what load_cache reads, so the .get default is the
        contract being pinned here."""
        payload = window.cache_payload([])
        payload.pop("content_dir")
        self.assertEqual(payload.get("content_dir", ""), "")


class EditorsLine(unittest.TestCase):

    def test_silent_with_one_editor(self):
        self.assertEqual(window.editors_line(["Atone"], "Atone"), "")

    def test_silent_with_none(self):
        self.assertEqual(window.editors_line([], ""), "")

    def test_names_the_chosen_one_when_several_are_open(self):
        line = window.editors_line(["Atone", "MarkerLess_02"], "Atone")
        self.assertIn("2 editors", line)
        self.assertIn("Atone", line)


class CountLine(unittest.TestCase):

    def test_no_query_reports_the_total(self):
        self.assertEqual(window.count_line(470, 470, ""), "470 animations")

    def test_a_query_reports_both_numbers(self):
        """Saying '470 shown' over a list of 34 rows is simply a lie."""
        line = window.count_line(470, 34, "jump")
        self.assertIn("34", line)
        self.assertIn("470", line)
        self.assertIn("jump", line)

    def test_no_match_says_so(self):
        line = window.count_line(470, 0, "zzz")
        self.assertIn("nothing matches", line)
        self.assertIn("zzz", line)

    def test_whitespace_counts_as_no_query(self):
        self.assertEqual(window.count_line(470, 470, "   "), "470 animations")


class ImportLine(unittest.TestCase):

    def merged(self, **over):
        info = {"merged": True, "joints": 92, "start": 0.0, "end": 62.0,
                "namespace": "", "warning": ""}
        info.update(over)
        return info

    def test_a_merge_says_it_went_onto_the_scene_skeleton(self):
        line = window.import_line("AS_Attack", self.merged())
        self.assertIn("scene skeleton", line)
        self.assertIn("92", line)
        self.assertIn("AS_Attack", line)

    def test_a_merge_reports_the_frame_range(self):
        self.assertIn("0-62", window.import_line("A", self.merged()))

    def test_a_new_skeleton_names_its_namespace(self):
        line = window.import_line("A", {"merged": False, "joints": 116,
                                        "namespace": "A", "start": 0.0,
                                        "end": 62.0, "warning": ""})
        self.assertIn("into A", line)

    def test_a_warning_is_appended_not_swallowed(self):
        line = window.import_line("A", self.merged(warning="no bone names matched"))
        self.assertIn("no bone names matched", line)

    def test_no_keys_does_not_print_a_broken_range(self):
        line = window.import_line("A", self.merged(start=None, end=None))
        self.assertNotIn("None", line)


class NoPerforce(unittest.TestCase):
    """One window since 2026-09-07, and no Perforce in it: the Export tab,
    the Checkout button and the VCS row left with the animator's «уберем весь
    функционал по работе с перфорсом». `vcs.py` and `checkouts.py` stay as
    modules; this file must not reach either."""

    def _source(self):
        with open(window.__file__.replace(".pyc", ".py"),
                  encoding="utf-8") as handle:
            return handle.read()

    def test_the_window_imports_neither_vcs_nor_checkouts(self):
        src = self._source()
        imports = [line for line in src.splitlines()
                   if line.strip().startswith(("import ", "from "))]
        for line in imports:
            self.assertNotIn("vcs", line, line)
            self.assertNotIn("checkouts", line, line)
        for name in ("vcs.prepare_target", "vcs.place", "checkouts.marks",
                     "checkouts.build_tab", "tabLayout", "with_vcs_suffix",
                     "_vcs_target", "checkout_selected", "ueBridgeVcs"):
            self.assertNotIn(name, src, name)

    def test_the_three_buttons_and_two_modes(self):
        src = self._source()
        for label in ('label="Export FBX..."', 'label="Export to uasset"',
                      'label="Import"', '"Rig"', '"New rig"',
                      '"Skeleton"', 'Retarget onto the rig', 'Onto a NEW rig',
                      'As a new skeleton'):
            self.assertIn(label, src, label)
        self.assertTrue(callable(window.export_fbx_selected))
        self.assertTrue(callable(window.export_uasset_selected))
        self.assertTrue(callable(window.import_selected))

    def test_the_default_mode_is_the_retarget(self):
        """Without the widget (a headless session) IMPORT means the whole
        pipeline -- the row the radio opens on."""
        real = window.cmds
        window.cmds = types.SimpleNamespace(
            iconTextRadioCollection=lambda *a, **k: False)
        try:
            self.assertTrue(window.retarget_selected())
            self.assertEqual(window.import_mode(), "rig")
        finally:
            window.cmds = real

    def test_the_three_rows_are_the_three_targets(self):
        """2026-09-08: «onto a NEW rig» is how many rigs arrive through
        import; the skeleton row is the only one that is not a retarget."""
        self.assertEqual(window.MODES, ("rig", "new_rig", "skeleton"))
        self.assertEqual([window.mode_for(i) for i in (1, 2, 3)],
                         ["rig", "new_rig", "skeleton"])
        self.assertEqual(window.mode_for(0), "rig")
        self.assertEqual(window.mode_for(None), "rig")

    def test_the_legacy_checkouts_popup_is_still_closed_on_open(self):
        self.assertIn("ueBridgeCheckouts", window.LEGACY_WINDOWS)


class ImportDropped(unittest.TestCase):
    """2026-10-01: an animation dragged out of the list and released over a
    viewport - onto the rig under the cursor, else onto a new rig. The editor,
    the scene and rigimport are faked."""

    Rig = collections.namedtuple("Rig", "namespace")

    def setUp(self):
        from maya_uebridge import rigimport
        self.rigimport = rigimport
        self.calls = []
        self.statuses = []
        self.rigs = {"Manny_Rig1": self.Rig("Manny_Rig1")}
        saved = dict(cmds=window.cmds, export=window._export_from_editor,
                     status=window._status, press=rigimport.import_and_retarget,
                     maya_rigs=sys.modules.get("maya_rigs"))

        def restore():
            window.cmds = saved["cmds"]
            window._export_from_editor = saved["export"]
            window._status = saved["status"]
            rigimport.import_and_retarget = saved["press"]
            if saved["maya_rigs"] is not None:
                sys.modules["maya_rigs"] = saved["maya_rigs"]
            else:
                sys.modules.pop("maya_rigs", None)
        self.addCleanup(restore)
        window.cmds = types.SimpleNamespace(
            checkBox=lambda name, exists=False, query=False, value=False: (
                True if exists else False))
        window._export_from_editor = lambda record: (
            self.calls.append(("export", record.name)) or ("C:/t/%s.fbx" % record.name, 30.0))
        window._status = self.statuses.append

        def press(fbx, name, clip_fps=None, set_timeline=True, target="rig", rig=None,
                  at=None):
            self.calls.append(("press", fbx, name, clip_fps, set_timeline, target,
                               rig.namespace if rig else None, at))
            return "%s retargeted" % name
        rigimport.import_and_retarget = press
        sys.modules["maya_rigs"] = types.SimpleNamespace(
            find=lambda namespace: self.rigs.get(namespace))
        self.record = records.parse_payload({"assets": [
            {"name": "A_Jump", "package": "/Game/A_Jump", "fps": 30.0}]})[0]

    def test_onto_the_rig_under_the_cursor(self):
        text = window.import_dropped(self.record, dict(
            kind="rig", rig="Manny_Rig1", label="Manny_Rig1", text="retarget onto Manny_Rig1"))
        self.assertEqual(self.calls, [
            ("export", "A_Jump"),
            ("press", "C:/t/A_Jump.fbx", "A_Jump", 30.0, False, "rig", "Manny_Rig1", None)])
        self.assertEqual(text, "A_Jump retargeted")
        self.assertEqual(self.statuses, ["A_Jump retargeted"])

    def test_beside_every_rig_onto_a_new_rig_at_the_floor_point(self):
        window.import_dropped(self.record, dict(kind="new_rig", point=(100.0, 0.0, -50.0),
                                                text="a new Manny [rig]"))
        self.assertEqual(self.calls[-1][5:], ("new_rig", None, (100.0, 0.0, -50.0)))

    def test_no_floor_point_a_new_rig_where_the_clip_is(self):
        window.import_dropped(self.record, dict(kind="new_rig", text="a new Manny [rig]"))
        self.assertEqual(self.calls[-1][5:], ("new_rig", None, None))

    def test_a_rig_gone_during_the_drag_imports_nothing(self):
        window.import_dropped(self.record, dict(kind="rig", rig="Gone", label="Gone"))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.statuses, ["the rig Gone is gone - nothing imported"])

    def test_no_target_imports_nothing_and_says_why(self):
        window.import_dropped(self.record, dict(kind="none", text="no floor"))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.statuses, ["no floor"])

    def test_the_list_is_given_its_drag(self):
        import inspect
        source = inspect.getsource(window.build_panel)
        self.assertIn("_attach_drag()", source)
        self.assertIn("listdrag.attach(_LIST", inspect.getsource(window._attach_drag))


class SeveralAnimations(unittest.TestCase):
    """2026-10-01: several picked - the Rig mode (or a drop on a rig) takes the
    first, New rig / Skeleton (or a floor drop) lay them all out in a line."""

    Rig = collections.namedtuple("Rig", "namespace")

    def setUp(self):
        from maya_uebridge import lineimport, rigimport
        self.calls = []
        self.statuses = []
        self.picked = [1, 3]
        self.mode = "new_rig"
        #  the list's own order (parse_payload would sort them by name)
        self.recs = [records.AnimRecord(n, "/Game/" + n, "", 0, 0.0, 30.0)
                     for n in ("A_Jump", "A_Walk", "A_Run")]
        saved = dict(cmds=window.cmds, export=window._export_from_editor,
                     status=window._status, mode=window.import_mode,
                     filtered=window._STATE.get("filtered"),
                     press=rigimport.import_and_retarget, run=lineimport.run,
                     maya_rigs=sys.modules.get("maya_rigs"))

        def restore():
            window.cmds = saved["cmds"]
            window._export_from_editor = saved["export"]
            window._status = saved["status"]
            window.import_mode = saved["mode"]
            window._STATE["filtered"] = saved["filtered"]
            rigimport.import_and_retarget = saved["press"]
            lineimport.run = saved["run"]
            if saved["maya_rigs"] is not None:
                sys.modules["maya_rigs"] = saved["maya_rigs"]
            else:
                sys.modules.pop("maya_rigs", None)
        self.addCleanup(restore)
        window._STATE["filtered"] = list(self.recs)
        window.cmds = types.SimpleNamespace(
            checkBox=lambda name, exists=False, query=False, value=False: False,
            textScrollList=lambda name, query=False, selectIndexedItem=False: list(self.picked))
        window.import_mode = lambda: self.mode
        window._export_from_editor = lambda record: (
            self.calls.append(("export", record.name)) or ("C:/t/%s.fbx" % record.name, 30.0))
        window._status = self.statuses.append

        def press(fbx, name, clip_fps=None, set_timeline=True, target="rig", rig=None,
                  at=None):
            self.calls.append(("press", name, target, rig.namespace if rig else None, at))
            return "%s retargeted" % name
        rigimport.import_and_retarget = press

        def run(chosen, export, target, centre=(0.0, 0.0, 0.0), set_timeline=True,
                step=250.0):
            self.calls.append(("line", [r.name for r in chosen], target, tuple(centre),
                               set_timeline, export is window._export_from_editor))
            return "laid out"
        lineimport.run = run
        rigs = {"Manny_Rig1": self.Rig("Manny_Rig1")}
        sys.modules["maya_rigs"] = types.SimpleNamespace(
            find=lambda namespace: rigs.get(namespace), rigs=lambda: list(rigs.values()),
            current_rig=lambda: (rigs["Manny_Rig1"], ""))

    def test_the_picked_rows_in_list_order(self):
        self.picked = [3, 1]
        self.assertEqual([r.name for r in window._selected_records()], ["A_Jump", "A_Run"])
        self.assertEqual(window._selected_record().name, "A_Jump")

    def test_new_rig_lays_them_all_out_about_the_origin(self):
        window.import_selected()
        self.assertEqual(self.calls, [("line", ["A_Jump", "A_Run"], "new_rig",
                                       (0.0, 0.0, 0.0), True, True)])
        self.assertEqual(self.statuses, ["laid out"])

    def test_skeleton_lays_them_all_out_too(self):
        self.mode = "skeleton"
        window.import_selected()
        self.assertEqual(self.calls[0][:3], ("line", ["A_Jump", "A_Run"], "skeleton"))

    def test_rig_takes_the_first_and_says_so(self):
        self.mode = "rig"
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Jump"),
                                      ("press", "A_Jump", "rig", None, None)])
        self.assertEqual(self.statuses, [
            "only A_Jump: a rig takes one animation (1 more picked)  |  A_Jump retargeted"])

    def test_one_picked_is_the_press_it_always_was(self):
        self.picked = [2]
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Walk"),
                                      ("press", "A_Walk", "new_rig", None, None)])
        self.assertEqual(self.statuses, ["A_Walk retargeted"])

    def test_a_drop_of_several_on_a_rig_takes_the_first(self):
        text = window.import_dropped(self.recs, dict(
            kind="rig", rig="Manny_Rig1", label="Manny_Rig1", text="retarget onto Manny_Rig1"))
        self.assertEqual(self.calls, [("export", "A_Jump"),
                                      ("press", "A_Jump", "rig", "Manny_Rig1", None)])
        self.assertEqual(text, "only A_Jump: a rig takes one animation (2 more picked)"
                               "  |  A_Jump retargeted")

    def test_a_floor_drop_of_several_lays_them_out_about_the_point(self):
        window.import_dropped(self.recs, dict(kind="new_rig", point=(120.0, 0.0, -36.0),
                                              label="Manny [rig]"))
        self.assertEqual(self.calls, [("line", ["A_Jump", "A_Walk", "A_Run"], "new_rig",
                                       (120.0, 0.0, -36.0), True, True)])

    def test_a_floor_drop_that_saw_no_floor_centres_on_the_origin(self):
        window.import_dropped(self.recs, dict(kind="new_rig", point=None))
        self.assertEqual(self.calls[0][3], (0.0, 0.0, 0.0))

    def test_a_drop_of_one_in_a_list_is_the_old_drop(self):
        window.import_dropped(self.recs[:1], dict(kind="new_rig", point=(5.0, 0.0, 6.0)))
        self.assertEqual(self.calls[-1], ("press", "A_Jump", "new_rig", None, (5.0, 0.0, 6.0)))

    def test_export_to_uasset_refuses_several(self):
        window.export_uasset_selected()
        self.assertEqual(self.statuses, ["pick one animation to overwrite - 2 are picked"])


class ProjectLabel(unittest.TestCase):

    def test_shows_the_project_name_not_the_path(self):
        self.assertEqual(window._project_label("C:/x/y/Atone.uproject"), "Atone")

    def test_says_so_when_there_is_no_project(self):
        self.assertEqual(window._project_label(""), "no project")


if __name__ == "__main__":
    unittest.main()

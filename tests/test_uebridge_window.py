"""Tests for the window's pure helpers.

The widgets need a Maya session; what is testable here is the cache, which is
where a mistake would quietly hand the user a wrong list.
"""

import collections
import sys
import types
import unittest


def _install_fake_maya():
    # the real package wins where it imports (trap 60: a fake `maya` installed beside an
    # importable one shadows it, and Scene Setup needs maya.api)
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
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

    def test_the_three_buttons_and_two_targets(self):
        src = self._source()
        for label in ('label="Export FBX..."', 'label="Export to uasset"',
                      'label="Import Animation"', '"Onto selected"', '"New"'):
            self.assertIn(label, src, label)
        self.assertTrue(callable(window.export_fbx_selected))
        self.assertTrue(callable(window.export_uasset_selected))
        self.assertTrue(callable(window.import_selected))

    def test_the_default_mode_is_the_retarget(self):
        """Without the widget (a headless session) IMPORT means the whole
        pipeline -- the target the segments open on, and the kind Rig."""
        real, kind = window.cmds, window.import_kind
        window.cmds = types.SimpleNamespace(
            iconTextRadioCollection=lambda *a, **k: False)
        window.import_kind = lambda: "rig"
        try:
            self.assertEqual(window.import_target(), "onto")
            self.assertTrue(window.retarget_selected())
            self.assertEqual(window.import_mode(), "rig")
        finally:
            window.cmds, window.import_kind = real, kind

    def test_the_kind_times_the_target(self):
        """2026-10-01, «Слить»: the Characters card's [Rig | Skeleton] says
        what, the Import row's [Onto selected | New] says where."""
        self.assertEqual(window.MODES, ("rig", "new_rig", "skeleton", "onto_skeleton"))
        self.assertEqual(window.TARGETS, ("onto", "new"))
        self.assertEqual(window.mode_for("rig", "onto"), "rig")
        self.assertEqual(window.mode_for("rig", "new"), "new_rig")
        self.assertEqual(window.mode_for("skeleton", "new"), "skeleton")
        self.assertEqual(window.mode_for("skeleton", "onto"), "onto_skeleton")
        self.assertEqual(window.mode_for(None, None), "rig")
        self.assertEqual(window.mode_for("rig", "nonsense"), "rig")

    def test_the_target_is_read_off_the_lit_segment(self):
        real = window.cmds
        lit = {"value": "hubBody|row|" + window.target_button("new")}
        window.cmds = types.SimpleNamespace(
            iconTextRadioCollection=lambda name, exists=False, query=False,
            select=False: True if exists else lit["value"])
        try:
            self.assertEqual(window.import_target(), "new")
            lit["value"] = ""
            self.assertEqual(window.import_target(), "onto")
        finally:
            window.cmds = real

    def test_the_kind_is_the_characters_card_s(self):
        from maya_scenesetup import window as scene_window
        saved = scene_window.current_choice
        try:
            scene_window.current_choice = lambda: ("Manny", "skeleton")
            self.assertEqual(window.import_kind(), "skeleton")
            scene_window.current_choice = lambda: ("Manny", "rig")
            self.assertEqual(window.import_kind(), "rig")
            #  a model without the kind (Orc D has no skeleton): the kind kept
            scene_window.current_choice = lambda: ("Orc_D", "skeleton")
            self.assertEqual(window.import_kind(), "skeleton")
            #  the Auto card brings either kind (2026-10-02)
            scene_window.current_choice = lambda: ("Auto", "skeleton")
            self.assertEqual(window.import_kind(), "skeleton")
            self.assertEqual(window.auto_kind(), "skeleton")
            scene_window.current_choice = lambda: ("Creep", "rig")
            self.assertIsNone(window.auto_kind())
        finally:
            scene_window.current_choice = saved

    def test_retarget_selected_means_a_rig(self):
        saved = window.import_mode
        try:
            for mode, wanted in (("rig", True), ("new_rig", True),
                                 ("skeleton", False), ("onto_skeleton", False)):
                window.import_mode = lambda m=mode: m
                self.assertEqual(window.retarget_selected(), wanted, mode)
        finally:
            window.import_mode = saved

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
        source = inspect.getsource(window.build_rows)
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

    def test_a_skeleton_drop_of_several_is_a_square_of_skeletons_about_the_point(self):
        window.import_dropped(self.recs, dict(kind="skeleton", point=(50.0, 0.0, 60.0)))
        self.assertEqual(self.calls, [("line", ["A_Jump", "A_Walk", "A_Run"], "skeleton",
                                       (50.0, 0.0, 60.0), True, True)])

    def _skeleton_press(self):
        """skeletonimport faked: the Characters card's skeleton, the press."""
        from maya_uebridge import skeletonimport
        saved = skeletonimport.precheck, skeletonimport.import_onto_skeleton

        def restore():
            skeletonimport.precheck, skeletonimport.import_onto_skeleton = saved
        self.addCleanup(restore)
        skeletonimport.precheck = lambda entry=None: self.refusal
        skeletonimport.import_onto_skeleton = (
            lambda fbx, name, clip_fps=None, set_timeline=True, at=None, entry=None: (
                self.calls.append(("onto", fbx, name, set_timeline, at)) or
                "%s onto the skeleton" % name))
        self.refusal = ""

    def test_a_skeleton_drop_of_one_goes_onto_the_characters_skeleton_on_the_point(self):
        """2026-10-01, «использовать скелет который активен в вкладке
        character»: the Skeleton mode's skeleton, with its geometry."""
        self._skeleton_press()
        text = window.import_dropped(self.recs[:1], dict(kind="skeleton",
                                                         point=(50.0, 0.0, 60.0)))
        self.assertEqual(self.calls, [("export", "A_Jump"),
                                      ("onto", "C:/t/A_Jump.fbx", "A_Jump", True,
                                       (50.0, 0.0, 60.0))])
        self.assertEqual(text, "A_Jump onto the skeleton")

    def test_a_skeleton_drop_with_no_floor_stands_where_the_clip_is(self):
        self._skeleton_press()
        window.import_dropped(self.recs[0], dict(kind="skeleton", point=None))
        self.assertEqual(self.calls[-1][-1], None)

    def test_a_missing_skeleton_file_refuses_before_the_editor(self):
        self._skeleton_press()
        self.refusal = "no skeleton file - Creep_Skeleton.ma is missing from assets/"
        text = window.import_dropped(self.recs[0], dict(kind="skeleton", point=None))
        self.assertEqual(self.calls, [])
        self.assertEqual(text, self.refusal)

    def test_the_skeleton_button_with_one_picked_goes_onto_the_characters_skeleton(self):
        self._skeleton_press()
        self.mode = "skeleton"
        self.picked = [2]
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Walk"),
                                      ("onto", "C:/t/A_Walk.fbx", "A_Walk", True, None)])
        self.assertEqual(self.statuses, ["A_Walk onto the skeleton"])

    def test_export_to_uasset_refuses_several(self):
        window.export_uasset_selected()
        self.assertEqual(self.statuses, ["pick one animation to overwrite - 2 are picked"])


class OntoASkeleton(unittest.TestCase):
    """2026-10-01, the merge: Skeleton picked in Characters x Onto selected
    puts the clip on a skeleton already in the scene - the selected one,
    else the only one, else a new one; a drop on a skeleton does it too.
    The editor and skeletonimport are faked."""

    def setUp(self):
        from maya_uebridge import skeletonimport
        self.sk = skeletonimport
        self.calls, self.statuses = [], []
        self.picked = [1]
        self.recs = [records.AnimRecord(n, "/Game/" + n, "", 0, 0.0, 30.0)
                     for n in ("A_Jump", "A_Walk")]
        self.uuids = {"UUID-ROOT1": "|root1"}
        self.target = ("|root1", "")
        self.refusal = ""
        saved = dict(cmds=window.cmds, export=window._export_from_editor,
                     status=window._status, mode=window.import_mode,
                     filtered=window._STATE.get("filtered"),
                     sk=(skeletonimport.target_skeleton, skeletonimport.onto_refusal,
                         skeletonimport.import_onto_existing, skeletonimport.precheck,
                         skeletonimport.import_onto_skeleton))

        def restore():
            window.cmds = saved["cmds"]
            window._export_from_editor = saved["export"]
            window._status = saved["status"]
            window.import_mode = saved["mode"]
            window._STATE["filtered"] = saved["filtered"]
            (skeletonimport.target_skeleton, skeletonimport.onto_refusal,
             skeletonimport.import_onto_existing, skeletonimport.precheck,
             skeletonimport.import_onto_skeleton) = saved["sk"]
        self.addCleanup(restore)
        window._STATE["filtered"] = list(self.recs)
        window.cmds = types.SimpleNamespace(
            checkBox=lambda name, exists=False, query=False, value=False: False,
            textScrollList=lambda name, query=False, selectIndexedItem=False: list(self.picked),
            ls=lambda uuid, long=False: [self.uuids[uuid]] if uuid in self.uuids else [])
        window.import_mode = lambda: "onto_skeleton"
        window._export_from_editor = lambda record: (
            self.calls.append(("export", record.name)) or ("C:/t/%s.fbx" % record.name, 30.0))
        window._status = self.statuses.append
        skeletonimport.target_skeleton = lambda: self.target
        skeletonimport.onto_refusal = lambda root: (
            self.calls.append(("check", root)) or self.refusal)
        skeletonimport.import_onto_existing = (
            lambda fbx, name, root, clip_fps=None, set_timeline=True: (
                self.calls.append(("onto", fbx, name, root, clip_fps, set_timeline))
                or "%s onto %s" % (name, root)))
        skeletonimport.precheck = lambda entry=None: ""
        skeletonimport.import_onto_skeleton = (
            lambda fbx, name, clip_fps=None, set_timeline=True, at=None, entry=None: (
                self.calls.append(("new", fbx, name, at)) or "%s onto a new skeleton" % name))

    def test_onto_the_selected_skeleton(self):
        window.import_selected()
        self.assertEqual(self.calls, [
            ("check", "|root1"), ("export", "A_Jump"),
            ("onto", "C:/t/A_Jump.fbx", "A_Jump", "|root1", 30.0, True)])
        self.assertEqual(self.statuses, ["A_Jump onto |root1"])

    def test_several_picked_the_first_goes_and_the_note_leads(self):
        self.picked = [1, 2]
        window.import_selected()
        self.assertEqual([c[0] for c in self.calls], ["check", "export", "onto"])
        self.assertEqual(self.statuses, [
            "only A_Jump: a skeleton takes one animation (1 more picked)  |  "
            "A_Jump onto |root1"])

    def test_a_refusal_comes_before_the_editor(self):
        self.target = (None, "2 skeletons in the scene (root, root1) - select any "
                             "bone or mesh of the one you mean")
        window.import_selected()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.statuses, [self.target[1]])

    def test_a_constrained_skeleton_refuses_before_the_editor(self):
        self.refusal = "root1: 1 bone(s) under a constraint that is not ours"
        window.import_selected()
        self.assertEqual(self.calls, [("check", "|root1")])
        self.assertEqual(self.statuses, [self.refusal])

    def test_no_skeleton_in_the_scene_adds_one_where_the_clip_is(self):
        self.target = (None, "")
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Jump"),
                                      ("new", "C:/t/A_Jump.fbx", "A_Jump", None)])
        self.assertEqual(self.statuses, ["A_Jump onto a new skeleton"])

    def test_a_drop_on_a_skeleton_goes_onto_it(self):
        text = window.import_dropped(self.recs, dict(
            kind="onto_skeleton", root="|root1", uuid="UUID-ROOT1", label="root1",
            text="onto root1"))
        self.assertEqual(self.calls, [
            ("check", "|root1"), ("export", "A_Jump"),
            ("onto", "C:/t/A_Jump.fbx", "A_Jump", "|root1", 30.0, True)])
        self.assertEqual(text, "only A_Jump: a skeleton takes one animation "
                               "(1 more picked)  |  A_Jump onto |root1")

    def test_a_skeleton_gone_during_the_drag_imports_nothing(self):
        text = window.import_dropped(self.recs[0], dict(
            kind="onto_skeleton", uuid="GONE", label="root1"))
        self.assertEqual(self.calls, [])
        self.assertEqual(text, "the skeleton root1 is gone - nothing imported")


class AutoCard(unittest.TestCase):
    """2026-10-02: Import with the Auto card picked. The explicit target wins (Onto selected with a
    character of the kind selected); otherwise each clip is matched (`autoimport`), Unreal asked
    for the clip's mesh. Every scene step is faked."""

    Rig = collections.namedtuple("Rig", "namespace")

    def setUp(self):
        from maya_uebridge import autoimport, lineimport, rigimport
        self.calls, self.statuses = [], []
        self.kind, self.target = "rig", "new"
        self.explicit = (None, "")
        self.picked = [2]
        self.recs = [records.AnimRecord(n, "/Game/" + n, "", 0, 0.0, 30.0)
                     for n in ("A_Jump", "A_Walk", "A_Run")]
        saved = [(window, n, getattr(window, n)) for n in (
            "cmds", "_export_unreal", "_status", "auto_kind", "import_target", "_onto_existing")]
        saved += [(autoimport, n, getattr(autoimport, n)) for n in (
            "explicit_rig", "explicit_skeleton", "import_auto")]
        saved += [(rigimport, "import_and_retarget", rigimport.import_and_retarget),
                  (lineimport, "run", lineimport.run)]
        filtered = window._STATE.get("filtered")
        self.addCleanup(lambda: [setattr(o, n, v) for o, n, v in saved])
        self.addCleanup(window._STATE.__setitem__, "filtered", filtered)
        window._STATE["filtered"] = list(self.recs)
        window.cmds = types.SimpleNamespace(
            checkBox=lambda name, exists=False, query=False, value=False: False,
            textScrollList=lambda name, query=False, selectIndexedItem=False: list(self.picked))
        window._status = self.statuses.append
        window.auto_kind = lambda: self.kind
        window.import_target = lambda: self.target
        window._export_unreal = lambda record, mesh=False: (
            self.calls.append(("export", record.name, mesh)) or ("C:/t/%s.fbx" % record.name, 30.0))
        autoimport.explicit_rig = lambda: self.explicit
        autoimport.explicit_skeleton = lambda: self.explicit
        autoimport.import_auto = lambda fbx, name, kind, clip_fps=None, set_timeline=True, \
            at=None: self.calls.append(("auto", fbx, name, kind, at)) or "auto " + name
        rigimport.import_and_retarget = lambda fbx, name, clip_fps=None, set_timeline=True, \
            target="rig", rig=None, at=None: (
                self.calls.append(("press", name, target, rig.namespace if rig else None))
                or "pressed " + name)
        lineimport.run = lambda chosen, export, target, centre=(0.0, 0.0, 0.0), \
            set_timeline=True, step=250.0, auto=False: (
                self.calls.append(("line", [r.name for r in chosen], target, tuple(centre),
                                   auto, export is window._export_with_mesh)) or "laid out")
        window._onto_existing = lambda record, root=None, note="": (
            self.calls.append(("onto", record.name, root, note)) or "onto " + record.name)

    def test_new_matches_the_clip_and_asks_for_its_mesh(self):
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Walk", True),
                                      ("auto", "C:/t/A_Walk.fbx", "A_Walk", "rig", None)])
        self.assertEqual(self.statuses, ["auto A_Walk"])

    def test_onto_selected_with_nothing_named_matches_too(self):
        self.target = "onto"
        window.import_selected()
        self.assertEqual([c[0] for c in self.calls], ["export", "auto"])

    def test_a_selected_rig_takes_the_clip_as_the_rig_press_does(self):
        self.target = "onto"
        self.explicit = (self.Rig("Manny_Rig1"), "")
        self.picked = [2, 3]
        window.import_selected()
        self.assertEqual(self.calls, [("export", "A_Walk", False),
                                      ("press", "A_Walk", "rig", "Manny_Rig1")])
        self.assertIn("only A_Walk", self.statuses[-1])

    def test_two_selected_rigs_refuse_before_the_editor(self):
        self.target = "onto"
        self.explicit = (None, "two rigs selected (a, b) - select controls of one only")
        window.import_selected()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.statuses, ["two rigs selected (a, b) - select controls of one only"])

    def test_a_selected_skeleton_takes_the_clip_with_skeleton_picked(self):
        self.kind, self.target = "skeleton", "onto"
        self.explicit = ("|Manny_Skeleton_Character|root", "")
        window.import_selected()
        self.assertEqual(self.calls, [("onto", "A_Walk", "|Manny_Skeleton_Character|root", "")])

    def test_several_go_to_the_square_each_matched(self):
        self.picked = [1, 3]
        self.kind = "skeleton"
        window.import_selected()
        self.assertEqual(self.calls, [("line", ["A_Jump", "A_Run"], "skeleton",
                                       (0.0, 0.0, 0.0), True, True)])

    def test_a_floor_drop_stands_the_clip_on_the_point(self):
        aim = dict(kind="new_rig", point=(1.0, 0.0, 2.0), auto=True, auto_kind="rig")
        window.import_dropped(self.recs[0], aim)
        self.assertEqual(self.calls[-1], ("auto", "C:/t/A_Jump.fbx", "A_Jump", "rig",
                                          (1.0, 0.0, 2.0)))
        self.assertEqual(self.calls[0], ("export", "A_Jump", True))

    def test_a_floor_drop_of_several_is_a_square_about_the_point(self):
        aim = dict(kind="skeleton", point=(1.0, 0.0, 2.0), auto=True, auto_kind="skeleton")
        window.import_dropped(self.recs[:2], aim)
        self.assertEqual(self.calls, [("line", ["A_Jump", "A_Walk"], "skeleton",
                                       (1.0, 0.0, 2.0), True, True)])

    def test_a_drop_on_a_rig_stays_the_explicit_target(self):
        import sys as _sys
        saved = _sys.modules.get("maya_rigs")
        self.addCleanup(lambda: _sys.modules.__setitem__("maya_rigs", saved)
                        if saved is not None else _sys.modules.pop("maya_rigs", None))
        _sys.modules["maya_rigs"] = types.SimpleNamespace(
            find=lambda namespace: self.Rig(namespace))
        window.import_dropped(self.recs[0], dict(kind="rig", rig="Manny_Rig1",
                                                 label="Manny_Rig1"))
        self.assertEqual(self.calls, [("export", "A_Jump", False),
                                      ("press", "A_Jump", "rig", "Manny_Rig1")])


class ProjectLabel(unittest.TestCase):

    def test_shows_the_project_name_not_the_path(self):
        self.assertEqual(window._project_label("C:/x/y/Atone.uproject"), "Atone")

    def test_says_so_when_there_is_no_project(self):
        self.assertEqual(window._project_label(""), "no project")


class FileSources(unittest.TestCase):
    """2026-10-02: Unity and Folder fill the same list; one step differs."""

    def setUp(self):
        from maya_uebridge import sources
        self.sources = sources
        self.file = sources.file_record("C:/f/run.bvh", "run", "", 10, fps=30.0)

    def _checked(self, answer):
        """The file check stubbed: it reads the disk through Maya's readers."""
        saved = window.os.path.isfile, window._clip_check
        window.os.path.isfile = lambda p: True
        checked = []
        window._clip_check = lambda ref: checked.append(ref) or answer

        def put_back():
            window.os.path.isfile, window._clip_check = saved
        self.addCleanup(put_back)
        return checked

    def test_a_file_record_hands_the_funnel_its_reference(self):
        checked = self._checked("")
        self.assertEqual(window._export_from_editor(self.file), ("C:/f/run.bvh", 30.0))
        self.assertEqual(checked, ["C:/f/run.bvh"])
        take = self.sources.file_record("C:/f/p.fbx", "p · jump",
                                        self.sources.clip_text(take=2), 5)
        self.assertEqual(window._export_from_editor(take)[0], "C:/f/p.fbx|take=2")

    def test_what_the_file_check_refuses_is_refused_before_the_press(self):
        """The fix review: a take no longer in the file, a Unity clip that
        cannot stand - refused at the export step, before a rig is added."""
        self._checked("p.fbx: take 'Run' is not in the file - it holds Take 001")
        take = self.sources.file_record("C:/f/p.fbx", "p · Run",
                                        self.sources.clip_text(take_name="Run"), 5)
        with self.assertRaises(window.uelink.UeBridgeError) as caught:
            window._export_from_editor(take)
        self.assertIn("'Run' is not in the file", str(caught.exception))

    def test_the_source_before_the_switch_is_built_is_the_remembered_one(self):
        """The fix review: a refresh from a hotkey before the card is built
        read 'unreal' over a remembered Folder."""
        saved = window._STATE.get("source"), window._var
        window._STATE["source"] = None
        window._var = lambda name, default="": "folder" if name == window.SOURCE_VAR else default

        def put_back():
            window._STATE["source"], window._var = saved
        self.addCleanup(put_back)
        self.assertEqual(window.current_source(), "folder")
        window._STATE["source"] = "unity"
        self.assertEqual(window.current_source(), "unity")

    def test_an_unreal_record_still_asks_the_editor(self):
        saved = window._export_unreal
        asked = []
        window._export_unreal = lambda record, mesh=False: (
            asked.append(mesh) or ("C:/t/x.fbx", 30.0))
        self.addCleanup(setattr, window, "_export_unreal", saved)
        rec = records.AnimRecord("A", "/Game/A", "", 3, 0.1, 30.0)
        self.assertEqual(window._export_from_editor(rec), ("C:/t/x.fbx", 30.0))
        # the Auto card asks for the clip's mesh too (2026-10-02)
        self.assertEqual(window._export_with_mesh(rec), ("C:/t/x.fbx", 30.0))
        self.assertEqual(asked, [False, True])

    def test_a_humanoid_row_refuses_before_anything_happens(self):
        rec = self.sources.file_record("C:/u/w.anim", "Walk", note="humanoid")
        self.assertIn("Humanoid", window.file_refusal(rec))
        with self.assertRaises(window.uelink.UeBridgeError):
            window._export_from_editor(rec)

    def test_a_vanished_file_refuses(self):
        rec = self.sources.file_record("C:/nowhere/gone.bvh", "gone")
        self.assertIn("gone", window.file_refusal(rec))

    def test_the_dropdown_lists_hub_projects_then_browsed_then_browse(self):
        hub = [("Lugal", "C:/w/work", "2022.3", 9), ("Rokets", "C:/w/Rokets", "6000", 1)]
        items = window.menu_items("unity", ["C:/w/work", "D:/other"], hub,
                                  {window.os.path.normcase(window.os.path.normpath(
                                      "C:/w/work"))})
        self.assertEqual([v for _l, v in items],
                         ["C:/w/work", "C:/w/Rokets", "D:/other", None])
        self.assertIn("open", items[0][0])
        self.assertEqual(items[-1][0], window.BROWSE)

    def test_a_folder_dropdown_names_the_folder_and_its_path(self):
        items = window.menu_items("folder", ["C:/clips/mocap"])
        self.assertEqual(items[0], ("mocap  -  C:/clips", "C:/clips/mocap"))

    def test_the_file_cache_keeps_every_field(self):
        payload = window.file_cache_payload([self.file], "folder", "C:/f")
        self.assertEqual(records.parse_payload(payload), [self.file])


if __name__ == "__main__":
    unittest.main()

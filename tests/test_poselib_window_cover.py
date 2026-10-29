"""The Pose Library window's module-level seams, the parts `test_poselib_window` leaves out - never
the Qt classes: the scene's settings and watchers (`Scene`), the drop seams that ask other tools
(`walk_well`, `chat_aim`, `skill_aim`, `skill_light`, `light_well`), the steps of a press that pastes
curves (`press_steps`), the window kept and let go (`_window_gone`), a blend cancelled while the window
closes (`_closing`), Windows' user32 (`_user32`) and the one idle later (`defer`).

`window._cmds` and the tools the window asks are rebound for the test and restored by cleanup.
"""
import os
import shutil
import tempfile
import types
import unittest

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya.utils
import maya_filedrag
import maya_hubqt
import maya_skillbar
from maya_scenesetup import droptarget
from maya_walk import posewell

from maya_poselib import animdata, scene, store, window


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)

    def patch_missing(self, target, name, value):
        had = hasattr(target, name)
        saved = getattr(target, name, None)
        setattr(target, name, value)

        def undo():
            if had:
                setattr(target, name, saved)
            else:
                delattr(target, name)

        self.addCleanup(undo)


class OptionCmds(object):
    """`optionVar`, `internalVar`, `mayaDpiSetting`, `ls`, `workspaceControl`, `scriptJob`,
    `currentTime` of a dict scene."""

    def __init__(self, options=None, dpi=1.0, control=False, jobs=None, killed=None):
        self.options = dict(options or {})
        self.dpi = dpi
        self.control = control
        self.jobs = jobs
        self.alive = set(killed or ())
        self.log = []
        self.job_ids = iter(range(101, 200))

    def mayaDpiSetting(self, query=False, realScaleValue=False):
        if isinstance(self.dpi, Exception):
            raise self.dpi
        return self.dpi

    def optionVar(self, exists=None, query=None, **flags):
        if exists is not None:
            return exists in self.options
        if query is not None:
            return self.options[query]
        (flag, (name, value)), = flags.items()
        self.log.append((flag, name, value))
        self.options[name] = value

    def internalVar(self, userAppDir=False):
        return "C:/Users/a/Documents/maya/"

    def workspaceControl(self, name, exists=False):
        if isinstance(self.control, Exception):
            raise self.control
        return self.control

    def scriptJob(self, event=None, parent=None, exists=None, kill=None, force=None):
        if exists is not None:
            if isinstance(self.jobs, Exception):
                raise self.jobs
            return exists in self.alive
        if kill is not None:
            self.log.append(("kill", kill, force))
            return None
        self.log.append(("job", event[0], parent))
        if isinstance(self.jobs, Exception):
            raise self.jobs
        if self.jobs == "none":
            return None
        return next(self.job_ids)

    def ls(self, selection=False, long=False):
        return ["|sel"]


class Settings(Patched):

    def use(self, **kwargs):
        fake = OptionCmds(**kwargs)
        self.patch(window, "_cmds", lambda: fake)
        return fake

    def test_the_ui_scale_is_the_dpi_setting_else_one(self):
        self.use(dpi=1.5)
        self.assertEqual(window.Scene().scale(), 1.5)
        self.use(dpi=0)
        self.assertEqual(window.Scene().scale(), 1.0)
        self.use(dpi=RuntimeError("no ui"))
        self.assertEqual(window.Scene().scale(), 1.0)

    def test_an_option_is_its_value_when_set_else_the_default(self):
        self.use(options={"x": 5})
        self.assertEqual(window.Scene().option("x"), 5)
        self.assertEqual(window.Scene().option("y", 7), 7)
        self.assertIsNone(window.Scene().option("y"))

    def test_an_option_is_stored_as_the_kind_of_value_it_is(self):
        fake = self.use()
        window.Scene().set_option("a", 3)
        window.Scene().set_option("b", 2.5)
        window.Scene().set_option("c", "text")
        window.Scene().set_option("d", True)
        self.assertEqual(fake.log, [("intValue", "a", 3), ("floatValue", "b", 2.5),
                                    ("stringValue", "c", "text"), ("intValue", "d", True)])

    def test_the_library_folder_is_remembered_as_a_string(self):
        fake = self.use()
        window.Scene().set_library("D:/poses")
        self.assertEqual(fake.log, [("stringValue", store.ROOT_VAR, "D:/poses")])

    def test_the_trash_is_the_stores_folder_under_the_maya_user_folder(self):
        self.use()
        self.assertEqual(window.Scene().trash(), store.trash_dir("C:/Users/a/Documents/maya/"))


class Library(Patched):

    def setUp(self):
        self.plugin = tempfile.mkdtemp()
        self.other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.plugin, True)
        self.addCleanup(shutil.rmtree, self.other, True)
        self.patch(window, "plugin_root", lambda: self.plugin.replace("\\", "/"))

    def use(self, options=None):
        fake = OptionCmds(options=options)
        self.patch(window, "_cmds", lambda: fake)

    def test_with_no_setting_it_is_the_plugin_s_own_folder_made_on_first_use(self):
        self.use()
        root = window.Scene().library()
        self.assertEqual(root, self.plugin.replace("\\", "/") + "/poses")
        self.assertTrue(os.path.isdir(root))

    def test_a_setting_that_names_a_folder_is_the_library(self):
        self.use({store.ROOT_VAR: self.other})
        self.assertEqual(window.Scene().library(), self.other.replace("\\", "/"))

    def test_a_setting_that_names_no_folder_falls_back_to_the_plugin_s(self):
        self.use({store.ROOT_VAR: os.path.join(self.other, "nope")})
        self.assertEqual(window.Scene().library(), self.plugin.replace("\\", "/") + "/poses")

    def test_an_empty_setting_falls_back_to_the_plugin_s(self):
        self.use({store.ROOT_VAR: ""})
        self.assertTrue(window.Scene().library().endswith("/poses"))


class SelectionReads(Patched):

    def ref(self, root, label="Manny [rig]", kind="rig", namespace="Manny_Rig1"):
        return scene.CharacterRef(kind, root, "rig" if kind == "rig" else None, label, "k", "m", namespace)

    def test_the_label_is_the_scenes_description_of_the_selection(self):
        self.patch(scene, "selection_label", lambda selection=None: "Manny [rig] (Manny_Rig1)")
        self.assertEqual(window.Scene().selection_label(), "Manny [rig] (Manny_Rig1)")

    def test_the_regions_are_those_of_the_one_character_the_selection_names(self):
        a = self.ref("|A|root")
        self.patch(scene, "resolve", lambda selection=None: [("|A|hand_l", a), ("|A|foot_l", a),
                                                              ("|prop", None)])
        self.patch(scene, "skeleton", lambda ref: ({"hand_l": {}}, "ue"))
        seen = []
        self.patch(scene, "members_of", lambda ref, nodes, bones: seen.append(nodes) or ["hand_l"])
        self.patch(scene, "regions_of", lambda bones, members: ["Hand L"] if members == ["hand_l"] else [])
        self.assertEqual(window.Scene().selection_regions(), ["Hand L"])
        self.assertEqual(seen, [["|A|hand_l", "|A|foot_l"]])

    def test_two_characters_or_none_have_no_regions(self):
        a, b = self.ref("|A|root"), self.ref("|B|root")
        self.patch(scene, "resolve", lambda selection=None: [("|A|x", a), ("|B|x", b)])
        self.assertIsNone(window.Scene().selection_regions())
        self.patch(scene, "resolve", lambda selection=None: [("|prop", None)])
        self.assertIsNone(window.Scene().selection_regions())
        self.patch(scene, "resolve", lambda selection=None: [])
        self.assertIsNone(window.Scene().selection_regions())

    def test_the_apply_targets_name_a_rig_by_its_namespace_and_a_skeleton_as_the_panel_does(self):
        rig, skeleton = self.ref("|A|root"), self.ref("|S|root", "Manny UE5 [skeleton]", "skeleton", "")
        self.patch(window, "_cmds", lambda: OptionCmds())
        self.patch(scene, "characters", lambda selection=None: ([rig, skeleton], []))
        self.assertEqual(window.Scene().apply_targets(),
                         ("onto Manny_Rig1, Manny UE5 [skeleton] (root)", True))

    def test_nothing_selected_among_the_scene_s_characters_is_the_only_one(self):
        rig = self.ref("|A|root")
        fake = OptionCmds()
        fake.ls = lambda selection=False, long=False: []
        self.patch(window, "_cmds", lambda: fake)
        self.patch(scene, "characters", lambda selection=None: ([], []))
        self.patch(scene, "all_characters", lambda: [rig])
        self.assertEqual(window.Scene().apply_targets(), ("onto Manny_Rig1 - the only character", True))

    def test_a_selection_of_no_character_is_refused(self):
        self.patch(window, "_cmds", lambda: OptionCmds())
        self.patch(scene, "characters", lambda selection=None: ([], ["|sel"]))
        self.patch(scene, "all_characters", lambda: self.fail("a selection is never redirected"))
        text, ok = window.Scene().apply_targets()
        self.assertEqual((text, ok), (window.NOT_A_CHARACTER, False))


class Watchers(Patched):

    def setUp(self):
        self.fake_callback = None
        original = OptionCmds.scriptJob
        test = self

        def scriptJob(fake, event=None, parent=None, exists=None, kill=None, force=None):
            if event is not None and event[0] == "timeChanged":
                test.fake_callback = event[1]
            return original(fake, event=event, parent=parent, exists=exists, kill=kill, force=force)

        OptionCmds.scriptJob = scriptJob
        self.addCleanup(setattr, OptionCmds, "scriptJob", original)

    def use(self, **kwargs):
        fake = OptionCmds(**kwargs)
        self.patch(window, "_cmds", lambda: fake)
        return fake

    def test_one_job_per_event_and_only_real_job_ids_are_kept(self):
        fake = self.use()
        jobs = window.Scene().watch(lambda: None)
        self.assertEqual(len(jobs), len(window.EVENTS))
        self.assertTrue(all(isinstance(job, int) for job in jobs))
        self.assertEqual([entry[1] for entry in fake.log if entry[0] == "job"], list(window.EVENTS))

    def test_a_standalone_maya_makes_no_job_and_keeps_none(self):
        self.use(jobs="none")
        self.assertEqual(window.Scene().watch(lambda: None), [])

    def test_a_job_maya_refuses_is_left_out(self):
        self.use(jobs=RuntimeError("no scriptJob"))
        self.assertEqual(window.Scene().watch(lambda: None), [])

    def test_the_jobs_are_parented_to_the_control_when_it_stands(self):
        fake = self.use(control=True)
        window.Scene().watch(lambda: None)
        self.assertTrue(all(entry[2] == window.CONTROL for entry in fake.log if entry[0] == "job"))
        fake = self.use(control=False)
        window.Scene().watch(lambda: None)
        self.assertTrue(all(entry[2] is None for entry in fake.log if entry[0] == "job"))

    def test_a_control_that_cannot_be_asked_leaves_the_jobs_plain(self):
        fake = self.use(control=RuntimeError("no ui"))
        window.Scene().watch(lambda: None)
        self.assertTrue(all(entry[2] is None for entry in fake.log if entry[0] == "job"))

    def test_the_time_job_calls_back_only_once_the_frame_has_moved(self):
        self.use()
        frames = iter([10.0, 10.0, 12.0, 13.0])
        self.patch(window, "_current_time", lambda: next(frames))
        called = []
        jobs = window.Scene().watch_time(lambda *args: called.append(args))
        self.assertEqual(len(jobs), 1)
        callback = self.fake_callback
        callback(1)
        callback(2)
        callback(3)
        self.assertEqual(called, [(2,), (3,)])

    def test_a_time_job_whose_frame_cannot_be_read_calls_back_all_the_same(self):
        self.use()
        frames = iter([10.0])

        def current():
            try:
                return next(frames)
            except StopIteration:
                raise RuntimeError("no time")

        self.patch(window, "_current_time", current)
        called = []
        window.Scene().watch_time(lambda *args: called.append(args))
        self.fake_callback(7)
        self.assertEqual(called, [(7,)])

    def test_a_time_job_maya_refuses_is_no_job(self):
        self.use(jobs=RuntimeError("no scriptJob"))
        self.patch(window, "_current_time", lambda: 1.0)
        self.assertEqual(window.Scene().watch_time(lambda: None), [])

    def test_a_standalone_maya_makes_no_time_job(self):
        self.use(jobs="none")
        self.patch(window, "_current_time", lambda: 1.0)
        self.assertEqual(window.Scene().watch_time(lambda: None), [])

    def test_only_live_integer_jobs_are_killed(self):
        fake = self.use(killed=[5, 6])
        window.Scene().unwatch([5, "text", 7, None, 6])
        self.assertEqual([entry for entry in fake.log if entry[0] == "kill"],
                         [("kill", 5, True), ("kill", 6, True)])

    def test_no_jobs_and_a_maya_that_refuses_kill_nothing_and_break_nothing(self):
        fake = self.use(jobs=RuntimeError("gone"))
        window.Scene().unwatch([5])
        window.Scene().unwatch(None)
        window.Scene().unwatch([])
        self.assertEqual(fake.log, [])


class Time(Patched):

    def test_the_current_time_is_the_scenes_frame_as_a_float(self):
        class Cmds(object):
            def currentTime(self, query=False):
                return 12

        self.patch(window, "_cmds", lambda: Cmds())
        value = window._current_time()
        self.assertEqual(value, 12.0)
        self.assertIsInstance(value, float)


class DropSeams(Patched):

    def test_the_snapshot_and_the_target_are_the_drop_tool_s(self):
        self.patch(droptarget, "snapshot", lambda: "snap")
        self.assertEqual(window.Scene().snapshot_scene(), "snap")

    def test_a_character_under_the_point_is_the_target(self):
        self.patch(window.Scene, "scale", lambda self: 2.0)
        self.patch(droptarget, "character_target", lambda gx, gy, snap, scale: {
            "kind": "character", "root": "|r", "scale": scale})
        self.patch(droptarget, "floor_at", lambda gx, gy: self.fail("a character is the answer"))
        self.assertEqual(window.Scene().target(1, 2, "snap"),
                         {"kind": "character", "root": "|r", "scale": 2.0})

    def test_no_viewport_is_the_answer_not_a_floor(self):
        self.patch(window.Scene, "scale", lambda self: 1.0)
        no_viewport = {"kind": "none", "text": droptarget.NO_VIEWPORT}
        self.patch(droptarget, "character_target", lambda gx, gy, snap, scale: no_viewport)
        self.patch(droptarget, "floor_at", lambda gx, gy: self.fail("no viewport has no floor"))
        self.assertEqual(window.Scene().target(1, 2, "snap"), no_viewport)

    def test_else_the_floor_the_camera_ray_meets(self):
        self.patch(window.Scene, "scale", lambda self: 1.0)
        self.patch(droptarget, "character_target", lambda gx, gy, snap, scale: {"kind": "none"})
        self.patch(droptarget, "floor_at", lambda gx, gy: {"kind": "floor", "at": (gx, gy)})
        self.assertEqual(window.Scene().target(3, 4, "snap"), {"kind": "floor", "at": (3, 4)})

    def test_the_point_is_over_the_window_on_the_hub_or_on_its_control(self):
        calls = []

        def on_hub(gx, gy, control=None):
            calls.append(control)
            return control == window.CONTROL

        self.patch(maya_hubqt, "on_hub", on_hub)
        self.assertIs(window.Scene().over_window(1, 2), True)
        self.assertEqual(calls, [None, window.CONTROL])

    def test_a_point_over_neither_is_outside(self):
        self.patch(maya_hubqt, "on_hub", lambda gx, gy, control=None: False)
        self.assertIs(window.Scene().over_window(1, 2), False)

    def test_nothing_to_say_says_nothing(self):
        self.assertIsNone(window.Scene().say(""))
        self.assertIsNone(window.Scene().say(None))

    def test_explorer_opens_with_the_path_selected_and_the_path_opens_with_its_program(self):
        import subprocess
        launched, started = [], []
        self.patch(subprocess, "Popen", lambda args: launched.append(args))
        self.patch_missing(os, "startfile", lambda path: started.append(path))
        window.Scene().reveal("C:/poses/Fist.pose")
        window.Scene().open_path("C:/poses/Fist.pose")
        self.assertEqual(launched, [["explorer", "/select,", os.path.normpath("C:/poses/Fist.pose")]])
        self.assertEqual(started, [os.path.normpath("C:/poses/Fist.pose")])


class OtherTools(Patched):
    """A tool that is not there, or fails, is no target - never an error in a drag."""

    def test_the_walk_builder_well_under_the_point(self):
        self.patch(posewell, "well_at", lambda gx, gy: "pose" if (gx, gy) == (1, 2) else None)
        self.assertEqual(window.walk_well(1, 2), "pose")
        self.assertIsNone(window.walk_well(3, 4))

    def test_a_walk_builder_that_fails_has_no_well(self):
        def broken(gx, gy):
            raise RuntimeError("no hub")

        self.patch(posewell, "well_at", broken)
        self.assertIsNone(window.walk_well(1, 2))

    def test_the_chat_is_under_the_point_when_the_file_drag_says_so(self):
        self.patch(maya_filedrag, "_names_at", lambda gx, gy: ["names"])
        self.patch(maya_filedrag, "section_under", lambda names: "chat" if names == ["names"] else None)
        self.assertTrue(window.chat_aim(1, 2))
        self.patch(maya_filedrag, "section_under", lambda names: "library")
        self.assertFalse(window.chat_aim(1, 2))

    def test_a_chat_that_cannot_be_asked_is_not_under_the_point(self):
        def broken(gx, gy):
            raise RuntimeError("no hub")

        self.patch(maya_filedrag, "_names_at", broken)
        self.assertFalse(window.chat_aim(1, 2))

    def test_the_skill_bar_cell_under_the_point(self):
        self.patch(maya_skillbar, "aim", lambda gx, gy: {"cell": 3})
        self.assertEqual(window.skill_aim(1, 2), {"cell": 3})

    def test_a_skill_bar_that_fails_has_no_cell(self):
        def broken(gx, gy):
            raise RuntimeError("no bar")

        self.patch(maya_skillbar, "aim", broken)
        self.assertIsNone(window.skill_aim(1, 2))

    def test_the_skill_bar_is_lit_for_a_target_and_a_failure_is_swallowed(self):
        lit = []
        self.patch(maya_skillbar, "light", lambda target: lit.append(target))
        window.skill_light({"cell": 3})
        self.assertEqual(lit, [{"cell": 3}])

        def broken(target):
            raise RuntimeError("no bar")

        self.patch(maya_skillbar, "light", broken)
        window.skill_light({"cell": 3})

    def test_the_well_is_lit_and_a_failure_is_swallowed(self):
        lit = []
        self.patch(posewell, "light", lambda well: lit.append(well))
        window.light_well("pose")
        window.light_well(None)
        self.assertEqual(lit, ["pose", None])

        def broken(well):
            raise RuntimeError("no hub")

        self.patch(posewell, "light", broken)
        window.light_well("pose")


class PressSteps(unittest.TestCase):

    def header(self, **kwargs):
        header = {"kind": "character", "start": 0.0, "end": 47.0,
                  "curves": {"layers": [{"name": "BaseAnimation", "base": True}], "nodes": 2}}
        header.update(kwargs)
        return header

    def test_pasting_curves_steps_once_per_channel_of_the_curves_read(self):
        curves = {"nodes": [{"attrs": {"tx": [], "ty": []}}, {"attrs": {"rx": []}}, {"attrs": None}]}
        options = animdata.Options(paste_as="curves")
        self.assertEqual(window.press_steps(self.header(), options, 0.0, curves), 3)

    def test_pasting_curves_not_read_yet_steps_once_per_channel_the_header_names(self):
        header = self.header(objects=[{"attrs": {"tx": 1, "ty": 2}}, {"attrs": {"rx": 3}}, None])
        options = animdata.Options(paste_as="curves")
        self.assertEqual(window.press_steps(header, options, 0.0), 3)

    def test_pasting_curves_with_no_channels_still_steps_once(self):
        options = animdata.Options(paste_as="curves")
        self.assertEqual(window.press_steps(self.header(), options, 0.0, {"nodes": []}), 1)

    def test_a_card_that_holds_no_curves_is_stepped_by_its_frames_whatever_was_asked(self):
        header = self.header(curves=None)
        options = animdata.Options(paste_as="curves")
        self.assertEqual(window.press_steps(header, options, 0.0), 48)

    def test_an_objects_card_steps_once_per_channel_and_at_least_once(self):
        header = {"kind": "objects", "objects": [{"attrs": {"tx": 1, "ty": 2}}, {"attrs": {}}, None]}
        self.assertEqual(window.press_steps(header, None, 0.0), 2)
        self.assertEqual(window.press_steps({"kind": "objects", "objects": []}, None, 0.0), 1)

    def test_a_plan_the_press_refuses_steps_once(self):
        header = {"kind": "character", "start": 0.0, "end": 9.0}
        self.assertEqual(window.press_steps(header, {"start": 50, "end": 60}, 0.0), 1)


class Closing(Patched):

    def test_a_blend_that_cannot_be_cancelled_still_lets_go_of_the_jobs(self):
        killed = []

        class Fake(object):
            def blend_cancel(self):
                raise RuntimeError("no session")

            def unwatch(self, jobs):
                killed.append(list(jobs))

        self.patch(window.traceback, "print_exc", lambda: None)
        window._closing(Fake(), [1, 2], timed=[3])
        self.assertEqual(killed, [[1, 2], [3]])

    def test_no_time_job_is_not_asked_to_be_killed(self):
        killed = []

        class Fake(object):
            def blend_cancel(self):
                pass

            def unwatch(self, jobs):
                killed.append(list(jobs))

        window._closing(Fake(), [1])
        self.assertEqual(killed, [[1]])


class KeptWindows(Patched):

    def test_a_destroyed_window_is_let_go_and_only_that_one(self):
        first, second = object(), object()
        self.patch(window, "_WINDOW", [first])
        window._window_gone(id(second), "ignored")
        self.assertEqual(window._WINDOW, [first])
        window._window_gone(id(first))
        self.assertEqual(window._WINDOW, [])

    def test_no_window_standing_is_none(self):
        self.patch(window, "_WINDOW", [])
        self.assertIsNone(window.live())

    def test_a_window_that_cannot_be_checked_is_let_go(self):
        self.patch(window, "_WINDOW", [object()])
        self.patch(window, "_classes", lambda: {})
        self.assertIsNone(window.live())
        self.assertEqual(window._WINDOW, [])

    def test_a_window_the_toolkit_says_is_alive_is_the_live_one(self):
        marker = object()
        self.patch(window, "_WINDOW", [marker])
        shiboken = types.SimpleNamespace(isValid=lambda widget: widget is marker)
        self.patch(window, "_classes", lambda: {"qt": types.SimpleNamespace(shiboken=shiboken)})
        self.assertIs(window.live(), marker)

    def test_a_window_the_toolkit_says_is_dead_is_let_go(self):
        self.patch(window, "_WINDOW", [object()])
        shiboken = types.SimpleNamespace(isValid=lambda widget: False)
        self.patch(window, "_classes", lambda: {"qt": types.SimpleNamespace(shiboken=shiboken)})
        self.assertIsNone(window.live())
        self.assertEqual(window._WINDOW, [])


class IdleLater(Patched):

    def test_a_function_is_run_one_idle_later(self):
        deferred = []
        self.patch_missing(maya.utils, "executeDeferred", lambda fn: deferred.append(fn))

        def work():
            return None

        window.defer(work)
        self.assertEqual(deferred, [work])


class User32(Patched):

    def setUp(self):
        self.patch(window, "_USER32", [])

    def test_the_answer_is_made_once_and_kept(self):
        first = window._user32()
        self.assertIs(window._user32(), first)
        self.assertEqual(len(window._USER32), 1)

    def test_a_library_that_cannot_be_loaded_is_none_and_that_is_kept_too(self):
        import ctypes
        calls = []

        def broken(name):
            calls.append(name)
            raise OSError("no user32")

        self.patch_missing(ctypes, "WinDLL", broken)
        self.assertIsNone(window._user32())
        self.assertIsNone(window._user32())
        self.assertEqual(calls, ["user32"])

    def test_off_windows_there_is_no_library_to_load(self):
        import ctypes
        saved = getattr(ctypes, "WinDLL", None)
        if saved is not None:
            delattr(ctypes, "WinDLL")
            self.addCleanup(setattr, ctypes, "WinDLL", saved)
        self.assertIsNone(window._user32())


if __name__ == "__main__":
    unittest.main()

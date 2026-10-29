"""The Pose Library's Save, the parts `test_poselib_scene` and `test_poselib_backdrop` leave out: the
scene held at a frame (`_at`), a character pose built from a skeleton (`character_pose`), an objects
pose (`object_records`, `objects_pose`), what a selection makes (`build_pose`), a model panel's port
(`_port`), a viewport backdrop Maya refuses, and every early answer of `thumbnail` (batch, no
viewport, a port too small, no Qt) plus its note.

The scene, the skeleton read, the panel and the blast are rebound for the test and restored by cleanup.
"""
import contextlib
import os
import sys
import types
import unittest
from unittest import mock

try:
    import maya.cmds  # noqa: F401  (the real package when mayapy has it - trap 60)
except ImportError:
    pass

import maya.api
import maya_hubqt
import maya_vpstudio

from maya_poselib import capture, objects, scene


class Patched(unittest.TestCase):

    def patch(self, target, name, value):
        saved = getattr(target, name)
        setattr(target, name, value)
        self.addCleanup(setattr, target, name, saved)


class TimeCmds(object):

    def __init__(self, now=5.0):
        self.now = now
        self.log = []

    def currentTime(self, *frame, **kwargs):
        if kwargs.get("query"):
            return self.now
        self.log.append(("time", frame[0]))
        self.now = frame[0]


class Tweaks(object):
    made = []

    def __init__(self):
        self.restored = 0
        Tweaks.made.append(self)

    def restore(self):
        self.restored += 1


class AuthorCmds(object):

    def __init__(self, name=None, broken=False):
        self.name = name
        self.broken = broken

    def optionVar(self, exists=None, query=None):
        if self.broken:
            raise RuntimeError("no optionVars")
        if exists is not None:
            return self.name is not None
        return self.name


class Author(Patched):

    def test_the_name_the_shared_card_goes_by_is_the_author(self):
        self.patch(capture, "cmds", AuthorCmds("  Yevhen  "))
        self.assertEqual(capture.author(), "Yevhen")

    def test_a_blank_or_missing_name_is_the_windows_user(self):
        self.patch(capture.getpass, "getuser", lambda: "winuser")
        self.patch(capture, "cmds", AuthorCmds("   "))
        self.assertEqual(capture.author(), "winuser")
        self.patch(capture, "cmds", AuthorCmds(None))
        self.assertEqual(capture.author(), "winuser")

    def test_a_scene_that_cannot_be_asked_is_the_windows_user(self):
        self.patch(capture.getpass, "getuser", lambda: "winuser")
        self.patch(capture, "cmds", AuthorCmds("Yevhen", broken=True))
        self.assertEqual(capture.author(), "winuser")

    def test_no_windows_user_is_the_username_variable_else_nothing(self):
        def broken():
            raise OSError("no user")

        self.patch(capture.getpass, "getuser", broken)
        self.patch(capture, "cmds", AuthorCmds(None))
        with mock.patch.dict(os.environ, {"USERNAME": "fromenv"}, clear=True):
            self.assertEqual(capture.author(), "fromenv")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(capture.author(), "")


class AtFrame(Patched):

    def setUp(self):
        Tweaks.made = []
        self.fake = TimeCmds(5.0)
        self.patch(capture, "cmds", self.fake)
        self.patch(capture, "keys", types.SimpleNamespace(Tweaks=Tweaks))

    def test_no_frame_or_the_current_one_changes_nothing(self):
        for frame in (None, 5.0, 5):
            with capture._at(frame) as at:
                self.assertEqual(at, 5.0)
        self.assertEqual(self.fake.log, [])
        self.assertEqual(Tweaks.made, [])

    def test_another_frame_is_the_time_for_the_block_and_the_time_is_put_back_after(self):
        with capture._at(12) as at:
            self.assertEqual(at, 12)
            self.assertEqual(self.fake.now, 12)
            self.assertEqual(Tweaks.made[0].restored, 0)
        self.assertEqual(self.fake.log, [("time", 12), ("time", 5.0)])
        self.assertEqual(self.fake.now, 5.0)
        self.assertEqual(Tweaks.made[0].restored, 1)

    def test_the_time_is_put_back_when_the_block_raises(self):
        with self.assertRaises(KeyError):
            with capture._at(12):
                raise KeyError("read failed")
        self.assertEqual(self.fake.now, 5.0)
        self.assertEqual(Tweaks.made[0].restored, 1)


def bones_of(names=("root", "pelvis", "hand_l")):
    out = {}
    for name in names:
        out[name] = {"parent": None if name == "root" else "root", "canonical": name,
                     "rest": [1.0] * 16, "world": [2.0] * 16, "rotateOrder": 0}
    return out


class CharacterPose(Patched):

    REF = scene.CharacterRef("rig", "|r|root", None, "Manny [rig]", "Manny_Rig", "Manny", "Manny_Rig1")

    def setUp(self):
        self.bones = bones_of()
        self.members = ["pelvis", "hand_l"]
        self.notes = []
        self.read = []

        def skeleton(ref, notes):
            self.read.append(ref)
            notes.extend(self.notes)
            return self.bones, "ue"

        self.patch(scene, "skeleton", skeleton)
        self.patch(scene, "members_of", lambda ref, nodes, bones: self.members)
        self.patch(scene, "identity",
                   lambda ref, convention: {"label": ref.label, "convention": convention})
        self.patch(scene, "regions_of", lambda bones, members: ["Hand L"] if "hand_l" in members else [])
        self.patch(capture, "_common", lambda kind: {"kind": kind})

    def test_the_card_holds_every_bone_the_members_and_who_it_was_made_on(self):
        data, note = capture.character_pose(self.REF, ["|r|root|hand_l"])
        self.assertEqual(data["kind"], "character")
        self.assertEqual(sorted(data["bones"]), ["hand_l", "pelvis", "root"])
        self.assertEqual(data["members"], ["pelvis", "hand_l"])
        self.assertEqual(data["regions"], ["Hand L"])
        self.assertEqual(data["objects"], [])
        self.assertEqual(data["character"], {"label": "Manny [rig]", "convention": "ue"})
        self.assertEqual(note, "Manny [rig] (Manny_Rig1): 2 of 3 bones - Hand L")

    def test_a_bone_record_is_its_parent_name_rest_world_and_order_and_only_a_drive_it_has(self):
        self.bones["hand_l"]["drive"] = [3.0] * 16
        self.bones["pelvis"]["drive"] = []
        self.bones["pelvis"]["jointOrient"] = [9.0, 9.0, 9.0]
        data, _note = capture.character_pose(self.REF, [])
        self.assertEqual(data["bones"]["hand_l"], {
            "parent": "root", "canonical": "hand_l", "rest": [1.0] * 16, "world": [2.0] * 16,
            "rotateOrder": 0, "drive": [3.0] * 16})
        self.assertEqual(data["bones"]["pelvis"], {
            "parent": "root", "canonical": "pelvis", "rest": [1.0] * 16, "world": [2.0] * 16,
            "rotateOrder": 0})
        self.assertIsNone(data["bones"]["root"]["parent"])

    def test_the_skeleton_s_own_notes_follow_the_line(self):
        self.notes = ["Manny carries 2 bones named ball_l - the first is kept"]
        _data, note = capture.character_pose(self.REF, [])
        self.assertEqual(note.split(" | ")[1], self.notes[0])

    def test_a_line_with_no_region_names_none(self):
        self.members = ["root"]
        _data, note = capture.character_pose(self.REF, [])
        self.assertEqual(note, "Manny [rig] (Manny_Rig1): 1 of 3 bones")

    def test_nothing_left_after_the_chips_is_a_refusal_naming_them(self):
        self.members = []
        self.assertEqual(capture.character_pose(self.REF, [], regions=["Head", "Spine"]),
                         (None, "no bone of Head, Spine in the pose of Manny [rig]"))
        self.assertEqual(capture.character_pose(self.REF, []),
                         (None, "no bone of the selection in the pose of Manny [rig]"))

    def test_a_chip_turned_off_drops_its_members(self):
        data, _note = capture.character_pose(self.REF, [], regions=["Hand L"])
        self.assertEqual(data["members"], ["hand_l"])

    def test_a_chip_turned_on_that_the_selection_did_not_touch_brings_its_region_in_whole(self):
        self.members = ["pelvis"]
        data, _note = capture.character_pose(self.REF, [], regions=["Pelvis", "Hand L"])
        self.assertEqual(data["members"], ["pelvis", "hand_l"])


class ObjectsPose(Patched):

    def setUp(self):
        self.patch(scene, "dag_object", lambda node: None if node == "bad" else "|" + node.split(".")[0])
        self.records = []

        def pose_record(path, own, cmds_):
            self.records.append((path, own, cmds_))
            return {"path": path, "own": own}

        self.patch(objects, "pose_record", pose_record)
        self.patch(capture, "_common", lambda kind: {"kind": kind})
        self.patch(capture, "cmds", "the scene")

    def test_each_transform_is_a_record_once_in_order_and_a_non_dag_node_is_left_out(self):
        out = capture.object_records(["cam", "prop.vtx[0]", "bad", "cam", "prop"])
        self.assertEqual([r["path"] for r in out], ["|cam", "|prop"])
        self.assertEqual([entry[2] for entry in self.records], ["the scene", "the scene"])

    def test_the_character_s_own_objects_are_marked(self):
        out = capture.object_records(["cam", "prop"], own=["|cam"])
        self.assertEqual([(r["path"], r["own"]) for r in out], [("|cam", True), ("|prop", False)])

    def test_nothing_makes_no_records(self):
        self.assertEqual(capture.object_records(None), [])
        self.assertEqual(capture.object_records([]), [])

    def test_an_objects_pose_is_the_common_fields_and_the_records(self):
        data = capture.objects_pose(["cam"], own=["|cam"])
        self.assertEqual(data["kind"], "objects")
        self.assertEqual(data["objects"], [{"path": "|cam", "own": True}])


class BuildPose(Patched):

    REF = CharacterPose.REF

    def setUp(self):
        self.split = ([], [], [])
        self.entered = []
        self.character = ({"kind": "character", "objects": []}, "the line")
        self.patch(scene, "split", lambda selection=None: self.split)
        self.patch(scene, "owned", lambda ref, owner: owner is not None)
        self.patch(capture, "character_pose", lambda ref, body, regions: self.character)
        self.patch(capture, "object_records", lambda paths, own=(): ["record %s own=%s" % (p, p in own)
                                                                   for p in paths])
        self.patch(capture, "objects_pose", lambda paths: {"kind": "objects", "paths": list(paths)})

        @contextlib.contextmanager
        def at(frame):
            self.entered.append(frame)
            yield frame

        self.patch(capture, "_at", at)

    def test_nothing_selected_is_the_word_for_it(self):
        self.assertEqual(capture.build_pose(), (None, scene.NOTHING))

    def test_the_frame_asked_is_the_one_the_scene_is_read_at(self):
        capture.build_pose(frame=12)
        self.assertEqual(self.entered, [12])

    def test_two_characters_are_refused(self):
        self.split = ([self.REF, self.REF._replace(root="|other")], [], [])
        self.assertEqual(capture.build_pose(), (None, scene.MANY))

    def test_a_character_is_its_pose_and_its_line(self):
        self.split = ([self.REF], ["|r|root|hand_l"], [])
        data, note = capture.build_pose(regions=["Hand L"])
        self.assertEqual((data["kind"], note), ("character", "the line"))
        self.assertEqual(data["objects"], [])

    def test_the_objects_beside_a_character_are_in_its_card_and_the_line_says_so(self):
        self.split = ([self.REF], ["|r|root|hand_l"], [("|cam", self.REF), ("|prop", None)])
        data, note = capture.build_pose()
        self.assertEqual(data["objects"], ["record |cam own=True", "record |prop own=False"])
        self.assertEqual(note, "the line | + 2 objects")

    def test_a_refused_character_pose_takes_no_objects(self):
        self.split = ([self.REF], [], [("|cam", None)])
        self.character = (None, "no bone of the selection in the pose of Manny [rig]")
        self.assertEqual(capture.build_pose(), self.character)

    def test_objects_alone_make_an_objects_pose(self):
        self.split = ([], [], [("|cam", None), ("|prop", None)])
        data, note = capture.build_pose()
        self.assertEqual(data, {"kind": "objects", "paths": ["|cam", "|prop"]})
        self.assertEqual(note, "2 objects")


class FakeUi(types.ModuleType):

    class M3dView(object):
        size = (800, 450)

        @classmethod
        def getM3dViewFromModelPanel(cls, panel):
            if panel == "gone":
                raise RuntimeError("no such panel")
            view = cls()
            return view

        def portWidth(self):
            return self.size[0]

        def portHeight(self):
            return self.size[1]


class Port(Patched):

    def setUp(self):
        fake = FakeUi("maya.api.OpenMayaUI")
        saved_module = sys.modules.get("maya.api.OpenMayaUI")
        sys.modules["maya.api.OpenMayaUI"] = fake
        had = hasattr(maya.api, "OpenMayaUI")
        saved_attr = getattr(maya.api, "OpenMayaUI", None)
        maya.api.OpenMayaUI = fake

        def undo():
            if saved_module is None:
                sys.modules.pop("maya.api.OpenMayaUI", None)
            else:
                sys.modules["maya.api.OpenMayaUI"] = saved_module
            if had:
                maya.api.OpenMayaUI = saved_attr
            else:
                del maya.api.OpenMayaUI

        self.addCleanup(undo)

    def test_a_panel_s_port_is_its_width_and_height(self):
        self.assertEqual(capture._port("modelPanel4"), (800, 450))

    def test_a_panel_that_is_gone_has_no_port(self):
        self.assertIsNone(capture._port("gone"))


class RefusingCmds(object):
    """A viewport whose colours and gradient can be made to refuse."""

    def __init__(self, refuse_set=(), refuse_query=(), gradient=True, refuse_gradient_set=False,
                 refuse_gradient_query=False):
        self.colours = {"background": [0.3] * 3, "backgroundTop": [0.5] * 3, "backgroundBottom": [0.1] * 3}
        self.refuse_set = set(refuse_set)
        self.refuse_query = set(refuse_query)
        self.gradient = gradient
        self.refuse_gradient_set = refuse_gradient_set
        self.refuse_gradient_query = refuse_gradient_query
        self.set_calls = []

    def displayRGBColor(self, name, *rgb, **flags):
        if flags.get("query"):
            if name in self.refuse_query:
                raise RuntimeError("unknown colour")
            return list(self.colours[name])
        self.set_calls.append(name)
        if name in self.refuse_set:
            raise RuntimeError("refused")
        self.colours[name] = list(rgb)

    def displayPref(self, query=False, displayGradient=None):
        if query:
            if self.refuse_gradient_query:
                raise RuntimeError("no such pref")
            return self.gradient
        if self.refuse_gradient_set:
            raise RuntimeError("refused")
        self.gradient = displayGradient


class BackdropRefused(Patched):

    def use(self, **kwargs):
        fake = RefusingCmds(**kwargs)
        self.patch(capture, "cmds", fake)
        return fake

    def test_a_colour_maya_refuses_is_left_and_the_others_are_still_set_and_put_back(self):
        fake = self.use(refuse_set=["backgroundTop"])
        with capture.backdrop("anim"):
            self.assertEqual(fake.colours["background"], list(capture.BACKDROPS["anim"]))
            self.assertEqual(fake.colours["backgroundBottom"], list(capture.BACKDROPS["anim"]))
            self.assertEqual(fake.colours["backgroundTop"], [0.5] * 3)
        self.assertEqual(fake.colours["background"], [0.3] * 3)
        self.assertEqual(fake.colours["backgroundBottom"], [0.1] * 3)

    def test_a_colour_that_cannot_be_read_is_never_touched(self):
        fake = self.use(refuse_query=["backgroundTop"])
        with capture.backdrop("pose"):
            pass
        self.assertNotIn("backgroundTop", fake.set_calls)

    def test_a_gradient_that_cannot_be_turned_off_is_left_and_nothing_breaks(self):
        fake = self.use(refuse_gradient_set=True)
        with capture.backdrop("pose"):
            self.assertTrue(fake.gradient)
        self.assertTrue(fake.gradient)

    def test_a_gradient_that_cannot_be_read_is_left_alone(self):
        fake = self.use(refuse_gradient_query=True)
        with capture.backdrop("pose"):
            self.assertTrue(fake.gradient)
        self.assertTrue(fake.gradient)

    def test_a_colour_that_cannot_be_put_back_stops_none_of_the_others(self):
        fake = self.use()
        originals = dict((k, list(v)) for k, v in fake.colours.items())
        with capture.backdrop("pose"):
            fake.refuse_set.add("background")
        self.assertEqual(fake.colours["backgroundTop"], originals["backgroundTop"])
        self.assertEqual(fake.colours["backgroundBottom"], originals["backgroundBottom"])
        self.assertTrue(fake.gradient)

    def test_a_gradient_that_cannot_be_turned_back_on_breaks_nothing(self):
        fake = self.use()
        with capture.backdrop("pose"):
            fake.refuse_gradient_set = True
        self.assertFalse(fake.gradient)

    def test_an_unknown_kind_is_shot_on_the_pose_s_colour(self):
        fake = self.use()
        with capture.backdrop("nonsense"):
            self.assertEqual(fake.colours["background"], list(capture.BACKDROPS["pose"]))


class ThumbCmds(object):

    def __init__(self, batch=False):
        self.batch = batch
        self.log = []

    def about(self, batch=False):
        return self.batch

    def currentTime(self, query=False):
        return 7.0

    def refresh(self, force=False):
        self.log.append("refresh")

    def playblast(self, **kwargs):
        self.log.append("playblast")

    def modelEditor(self, panel, **kwargs):
        if kwargs.get("query"):
            flag = [k for k in kwargs if k not in ("query",)][0]
            if flag == "nParticles":
                raise RuntimeError("this editor has no such flag")
            return True
        self.log.append(("flags", panel, tuple(sorted(kwargs.items()))))

    def displayRGBColor(self, name, *rgb, **flags):
        if flags.get("query"):
            return [0.3, 0.3, 0.3]

    def displayPref(self, query=False, displayGradient=None):
        if query:
            return False


class ThumbnailAnswers(Patched):

    def setUp(self):
        self.cmds = ThumbCmds()
        self.patch(capture, "cmds", self.cmds)
        self.panel = "modelPanel4"
        self.port = (800, 450)
        self.patch(maya_vpstudio, "active_panel", lambda: self.panel)
        self.patch(capture, "_port", lambda panel: self.port)
        self.qt = object()
        self.patch(maya_hubqt, "qt", lambda: self.qt)

    def test_batch_mode_has_no_viewport(self):
        self.cmds.batch = True
        self.assertEqual(capture.thumbnail("x.jpg"), (False, capture.NO_VIEWPORT))

    def test_no_model_panel_has_no_viewport(self):
        self.panel = None
        self.assertEqual(capture.thumbnail("x.jpg"), (False, capture.NO_VIEWPORT))

    def test_a_panel_with_no_port_has_no_viewport(self):
        self.port = None
        self.assertEqual(capture.thumbnail("x.jpg"), (False, capture.NO_VIEWPORT))

    def test_a_hidden_port_says_its_size(self):
        self.port = (800, capture.SMALLEST_PORT - 1)
        self.assertEqual(capture.thumbnail("x.jpg"),
                         (False, "the viewport is 800x15 - too small for a thumbnail"))
        self.port = (capture.SMALLEST_PORT - 1, 450)
        self.assertEqual(capture.thumbnail("x.jpg")[1],
                         "the viewport is 15x450 - too small for a thumbnail")

    def test_no_qt_says_so(self):
        self.qt = None
        self.assertEqual(capture.thumbnail("x.jpg"), (False, "no Qt for a thumbnail"))


class ThumbnailBlast(ThumbnailAnswers):
    """The whole blast on fakes: the editor's flags hidden and put back, the tweaks put back, the
    picture cut by `square_jpg`, and the note counting the blasts."""

    def setUp(self):
        ThumbnailAnswers.setUp(self)
        self.asked = []
        self.flags = []
        self.pictures = iter([b"a"] * 10)
        self.jpg = (True, "")
        Tweaks.made = []
        self.patch(capture, "keys", types.SimpleNamespace(Tweaks=Tweaks))
        self.patch(capture, "blast_file", lambda options, frame, path: next(self.pictures))
        self.patch(capture, "pump", lambda qt: self.asked.append("pump"))
        self.patch(capture, "set_flags", lambda panel, values: self.flags.append(dict(values)))
        self.patch(capture, "shown_flags", lambda panel: {"joints": True, "grid": False})

        def square_jpg(qt, source, path, size, kind):
            self.asked.append(("jpg", path, size, kind))
            return self.jpg

        self.patch(capture, "square_jpg", square_jpg)

    def test_a_settled_blast_says_how_many_blasts_it_took(self):
        ok, note = capture.thumbnail("card.jpg", 320, "anim")
        self.assertTrue(ok)
        self.assertEqual(note, "thumbnail from modelPanel4 (800x450, 3 blasts)")
        self.assertIn(("jpg", "card.jpg", 320, "anim"), self.asked)
        self.assertEqual(self.asked.count("pump"), 2)

    def test_the_editor_flags_are_hidden_for_the_blast_and_put_back_as_they_were(self):
        capture.thumbnail("card.jpg")
        self.assertEqual(self.flags, [{"joints": False, "grid": False}, {"joints": True, "grid": False}])
        self.assertEqual(Tweaks.made[0].restored, 1)

    def test_a_viewport_still_loading_textures_says_so(self):
        counter = iter(range(100))
        self.patch(capture, "blast_file", lambda options, frame, path: str(next(counter)).encode())
        ok, note = capture.thumbnail("card.jpg")
        self.assertTrue(ok)
        self.assertEqual(note, "thumbnail from modelPanel4 (800x450, 5 blasts, textures still loading)")

    def test_a_picture_that_cannot_be_written_is_the_note_and_the_flags_are_back_all_the_same(self):
        self.jpg = (False, "the playblast wrote nothing readable")
        self.assertEqual(capture.thumbnail("card.jpg"), (False, "the playblast wrote nothing readable"))
        self.assertEqual(self.flags[-1], {"joints": True, "grid": False})

    def test_a_blast_that_raises_puts_the_flags_and_the_tweaks_back(self):
        def blast(options, frame, path):
            raise RuntimeError("playblast failed")

        self.patch(capture, "blast_file", blast)
        with self.assertRaises(RuntimeError):
            capture.thumbnail("card.jpg")
        self.assertEqual(self.flags[-1], {"joints": True, "grid": False})
        self.assertEqual(Tweaks.made[0].restored, 1)

    def test_the_raw_blast_is_not_left_in_the_temp_folder(self):
        capture.thumbnail("card.jpg")
        import tempfile
        raw = os.path.join(tempfile.gettempdir(), "skeldar_pose_thumbnail_%d.png" % os.getpid())
        self.assertFalse(os.path.exists(raw))


class Flags(Patched):

    def test_the_editor_s_flags_are_asked_one_by_one_and_an_unknown_one_is_left_out(self):
        cmds = ThumbCmds()
        self.patch(capture, "cmds", cmds)
        shown = capture.shown_flags("modelPanel4")
        self.assertNotIn("nParticles", shown)
        self.assertEqual(sorted(shown), sorted(f for f in capture.HIDDEN if f != "nParticles"))

    def test_a_flag_the_editor_refuses_stops_none_of_the_others(self):
        calls = []

        class Cmds(object):
            def modelEditor(self, panel, edit=False, **flags):
                calls.append(sorted(flags))
                if "joints" in flags:
                    raise RuntimeError("refused")

        self.patch(capture, "cmds", Cmds())
        capture.set_flags("modelPanel4", {"joints": False, "grid": False})
        self.assertEqual(calls, [["joints"], ["grid"]])

    def test_the_blast_s_options_are_the_ports_own_size_offscreen_from_the_panel(self):
        options = capture.blast_options("modelPanel4", 800, 450)
        self.assertEqual(options["widthHeight"], (800, 450))
        self.assertEqual(options["editorPanelName"], "modelPanel4")
        self.assertEqual(options["percent"], 100)
        self.assertTrue(options["offScreen"])
        self.assertFalse(options["viewer"])
        self.assertEqual(options["quality"], capture.BLAST_QUALITY)


class BlastFile(Patched):

    def test_a_blast_is_the_bytes_of_the_file_it_wrote(self):
        import shutil
        import tempfile
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        path = os.path.join(folder, "raw.png")
        log = []

        class Cmds(object):
            def refresh(self, force=False):
                log.append(("refresh", force))

            def playblast(self, frame=None, completeFilename=None, **options):
                log.append(("playblast", frame, options["panel"] if "panel" in options else None))
                with open(completeFilename, "wb") as handle:
                    handle.write(b"PNGDATA")

        self.patch(capture, "cmds", Cmds())
        self.assertEqual(capture.blast_file({"viewer": False}, 7.0, path), b"PNGDATA")
        self.assertEqual(log, [("refresh", True), ("playblast", [7.0], None)])


class Pump(Patched):

    def test_one_turn_of_mayas_idle_queue_and_qts_events(self):
        import maya.utils
        log = []
        had = hasattr(maya.utils, "processIdleEvents")
        saved = getattr(maya.utils, "processIdleEvents", None)
        maya.utils.processIdleEvents = lambda: log.append("idle")

        def undo():
            if had:
                maya.utils.processIdleEvents = saved
            else:
                del maya.utils.processIdleEvents

        self.addCleanup(undo)
        app = types.SimpleNamespace(processEvents=lambda: log.append("events"))
        qt = types.SimpleNamespace(QtWidgets=types.SimpleNamespace(QApplication=app))
        capture.pump(qt)
        self.assertEqual(log, ["idle", "events"])


if __name__ == "__main__":
    unittest.main()

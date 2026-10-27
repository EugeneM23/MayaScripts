"""The export reads its own FBX back and puts a stuck bake rate right (2026-10-27).

A fake FBX plugin plays the measured one: the first export of a session at a rate other than 30
latches the bake step, every later export bakes at it under a header naming the scene's rate, and
an FBXImport with the sampling rate taken from the File sets it to that file's rate."""

import os
import sys
import tempfile
import types
import unittest


def _install_fake_maya():
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

from maya_uebridge import animexport, fbxkeys  # noqa: E402
from tests.test_uebridge_fbxkeys import frames, write_fbx  # noqa: E402

SELECTOR = "Import|IncludeGrp|Animation|SamplingPanel|SamplingRateSelector"
TIMELINE = "Import|IncludeGrp|Animation|ExtraGrp|TimeLine"
ANIMATION = "Import|IncludeGrp|Animation"


class FakePlugin(object):
    """mel.eval for the FBX commands the export sends, and the plugin's latch."""

    def __init__(self, scene_fps, latched=None, import_resets=True):
        self.fps = scene_fps
        self.latched = latched
        self.import_resets = import_resets
        self.calls = []
        self.props = {SELECTOR: "Custom", TIMELINE: 1, ANIMATION: 0}
        self.mode = "merge"
        self.set_rate = 1
        self.exports = []
        self.imports = []

    def eval(self, text):
        self.calls.append(text)
        for piece in [p.strip() for p in text.split(";") if p.strip()]:
            out = self._one(piece)
            if out is not None:
                return out
        return None

    def _one(self, text):
        if text.startswith("FBXExport -f"):
            path = text.split('"')[1]
            rate = self.latched or self.fps
            write_fbx(path, [("root", "Lcl Rotation", frames(rate, 0, 59 * rate / self.fps))],
                      extra_layer_curve=False)
            if self.latched is None and self.fps != 30:
                self.latched = self.fps
            self.exports.append(path)
            return None
        if text.startswith("FBXImport -f"):
            self.imports.append((self.mode, self.props[SELECTOR], self.props[TIMELINE],
                                 self.props[ANIMATION], self.set_rate))
            if self.import_resets and self.props[SELECTOR] == "File":
                self.latched = self.fps
            return None
        if text == "FBXImportMode -q":
            return self.mode
        if text.startswith("FBXImportMode -v"):
            self.mode = text.split()[-1]
            return None
        if text == "FBXImportSetMayaFrameRate -q":
            return self.set_rate
        if text.startswith("FBXImportSetMayaFrameRate -v"):
            self.set_rate = 1 if text.split()[-1] == "true" else 0
            return None
        if text.startswith("FBXProperty"):
            path = text.split('"')[1]
            rest = text.split('"', 2)[2].strip()
            if rest == "-q":
                return self.props[path]
            value = rest.split(None, 1)[1].strip()
            if value.startswith('"'):
                self.props[path] = value.strip('"')
            else:
                self.props[path] = 1 if value == "true" else 0
            return None
        return None


class FakeCmds(object):

    def __init__(self, unit="ntsc"):
        self.nodes = set()
        self.selection = []
        self.time = 17.0
        self.unit = unit
        self.created = []

    def createNode(self, kind, name=None, skipSelect=False):
        self.nodes.add(name)
        self.created.append(name)
        return name

    def objExists(self, name):
        return name in self.nodes

    def delete(self, name):
        self.nodes.discard(name)

    def select(self, nodes=None, replace=False, clear=False):
        self.selection = [] if clear else list(nodes if isinstance(nodes, list) else [nodes])

    def currentTime(self, frame=None, query=False, edit=False):
        if query:
            return self.time
        self.time = frame

    def currentUnit(self, query=False, time=None, updateAnimation=None):
        if query:
            return self.unit
        self.unit = time


class Rig(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "clip.fbx")
        self.saved = (animexport.cmds, animexport.mel, animexport.animimport.scene_fps,
                      animexport._apply_export_options, animexport._put_time,
                      animexport.PROBE_FOLDER)
        animexport.PROBE_FOLDER = self.folder
        animexport._apply_export_options = lambda start, end: self.applied.append((start, end))
        animexport._put_time = lambda frame: setattr(self.cmds, "time", frame)
        self.applied = []

    def tearDown(self):
        (animexport.cmds, animexport.mel, animexport.animimport.scene_fps,
         animexport._apply_export_options, animexport._put_time,
         animexport.PROBE_FOLDER) = self.saved

    def plugin(self, fps, latched=None, import_resets=True):
        self.cmds = FakeCmds()
        self.fake = FakePlugin(fps, latched, import_resets)
        animexport.cmds = self.cmds
        animexport.mel = types.SimpleNamespace(eval=self.fake.eval)
        animexport.animimport.scene_fps = lambda: float(fps)
        self.selects = []
        return lambda: self.selects.append("bones")

    def keys(self):
        return fbxkeys.read_key_times(self.path)


class ExportChecked(Rig):

    def test_a_clean_bake_is_exported_once_and_nothing_else_happens(self):
        select = self.plugin(30)
        note = animexport._export_checked(self.path, 0, 59, select)
        self.assertEqual(note, "")
        self.assertEqual(len(self.fake.exports), 1)
        self.assertEqual(self.fake.imports, [])
        self.assertEqual(fbxkeys.bake_problem(self.keys(), 30.0), "")

    def test_the_measured_case_a_24_latch_in_a_30_scene_is_put_right(self):
        """What happened to AS_Dg_Atk_JA_Passive_1P: keys every 1/24 s under a 30 fps header."""
        select = self.plugin(30, latched=24)
        note = animexport._export_checked(self.path, 0, 59, select)
        self.assertEqual(fbxkeys.bake_problem(self.keys(), 30.0), "")
        self.assertAlmostEqual(fbxkeys.key_rate(self.keys()), 30.0)
        self.assertEqual(len(self.fake.imports), 1)
        self.assertIn("1/24", note)
        self.assertIn("exported again", note)
        # the real export ran again with our options and our bones selected
        self.assertEqual(self.applied, [(0, 59)])
        self.assertEqual(self.selects, ["bones"])
        self.assertEqual(os.path.normpath(self.fake.exports[-1]), os.path.normpath(self.path))

    def test_the_reset_import_creates_nothing_and_samples_at_the_files_rate(self):
        select = self.plugin(30, latched=24)
        animexport._export_checked(self.path, 0, 59, select)
        mode, selector, timeline, animation, set_rate = self.fake.imports[0]
        self.assertEqual(mode, "exmerge")
        self.assertEqual(selector, "File")
        self.assertEqual(timeline, 0)
        self.assertEqual(animation, 1)
        self.assertEqual(set_rate, 0)

    def test_the_animators_import_settings_come_back(self):
        select = self.plugin(30, latched=24)
        animexport._export_checked(self.path, 0, 59, select)
        self.assertEqual(self.fake.mode, "merge")
        self.assertEqual(self.fake.props, {SELECTOR: "Custom", TIMELINE: 1, ANIMATION: 0})
        self.assertEqual(self.fake.set_rate, 1)

    def test_the_probe_node_is_gone_and_the_frame_is_put_back(self):
        select = self.plugin(30, latched=24)
        self.cmds.time = 17.0
        animexport._export_checked(self.path, 0, 59, select)
        self.assertEqual(self.cmds.nodes, set())
        self.assertEqual(len(self.cmds.created), 1)
        self.assertEqual(self.cmds.time, 17.0)
        self.assertFalse(os.path.exists(os.path.join(self.folder, animexport.PROBE_FILE)))

    def test_a_15_latch_on_the_grid_but_missing_frames_is_caught_too(self):
        select = self.plugin(30, latched=15)
        animexport._export_checked(self.path, 0, 59, select)
        self.assertEqual(len(self.fake.imports), 1)
        self.assertAlmostEqual(fbxkeys.key_rate(self.keys()), 30.0)

    def test_a_latch_that_will_not_let_go_refuses_and_leaves_no_file(self):
        select = self.plugin(30, latched=24, import_resets=False)
        with self.assertRaises(RuntimeError) as caught:
            animexport._export_checked(self.path, 0, 59, select)
        self.assertIn("1/24", str(caught.exception))
        self.assertIn("restart Maya", str(caught.exception))
        self.assertFalse(os.path.exists(self.path))

    def test_a_24_scene_after_a_30_export_is_left_alone(self):
        """30 first, then 24: measured right, nothing to put back."""
        select = self.plugin(24)
        self.assertEqual(animexport._export_checked(self.path, 0, 59, select), "")
        self.assertEqual(self.fake.imports, [])


class EveryRoadIsChecked(unittest.TestCase):

    def test_the_hierarchy_export_goes_through_the_check(self):
        """Export to uasset, Export FBX... and the checkouts' EXPORT all run _export_hierarchy."""
        import inspect
        source = inspect.getsource(animexport._export_hierarchy)
        self.assertIn("_export_checked(", source)
        self.assertNotIn("mel.eval(export_command(fbx_path))", source)


if __name__ == "__main__":
    unittest.main()

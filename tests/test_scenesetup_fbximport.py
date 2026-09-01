"""Tests for the one home of the FBX import-mode guard.

This is trap 33 and nothing else: the FBX plugin's import MODE is a single
global setting for the whole Maya session, `maya_uebridge` leaves it on
`exmerge` where the importer CREATES NOTHING, and `cmds.file` inherits it
even though it ignores the curve-related settings. Both callers -- the
weapon in `attach` and the character in `character` -- would silently stop
importing after any animation import from Unreal.

It lived inside `attach.import_model` until 2026-09-01. One home now,
because a fix for a silent failure that exists in two copies is a fix that
will exist in one copy soon enough.
"""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_scenesetup import fbximport  # noqa: E402


class FakeMel(object):
    """The FBX plugin's option state, as maya.mel answers for it."""

    def __init__(self, mode="exmerge", unknown=()):
        self.mode = mode
        self.commands = []
        self.unknown = set(unknown)

    def eval(self, command):
        self.commands.append(command)
        head = command.split(" ", 1)[0]
        if head in self.unknown:
            raise RuntimeError("invalid command: " + head)
        if command.strip() == "FBXImportMode -q":
            return self.mode
        if command.startswith("FBXImportMode -v"):
            self.mode = command.rsplit(None, 1)[-1]
        return None


class FakeCmds(object):
    def __init__(self, mel, nodes=("|thing",), boom=False, loaded=True):
        self._mel = mel
        self._nodes = list(nodes)
        self._boom = boom
        self._loaded = loaded
        self.mode_during_import = None
        self.loaded_plugins = []
        self.file_kwargs = None

    def pluginInfo(self, name, query=False, loaded=False, **kwargs):
        return self._loaded

    def loadPlugin(self, name, quiet=False, **kwargs):
        self.loaded_plugins.append(name)
        self._loaded = True
        return [name]

    def file(self, path, **kwargs):
        self.mode_during_import = self._mel.mode
        self.file_kwargs = kwargs
        if self._boom:
            raise RuntimeError("import failed")
        return list(self._nodes)


class ImportNodes(unittest.TestCase):

    def setUp(self):
        self.real = (fbximport.cmds, fbximport.mel)
        self.mel = FakeMel("exmerge")
        self.cmds = FakeCmds(self.mel)
        fbximport.mel = self.mel
        fbximport.cmds = self.cmds

    def tearDown(self):
        fbximport.cmds, fbximport.mel = self.real

    def test_the_import_runs_in_add_mode(self):
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.cmds.mode_during_import, "add")

    def test_the_previous_mode_is_put_back(self):
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.mel.mode, "exmerge")

    def test_the_mode_is_put_back_when_the_import_blows_up(self):
        self.cmds = FakeCmds(self.mel, boom=True)
        fbximport.cmds = self.cmds
        with self.assertRaises(RuntimeError):
            fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.mel.mode, "exmerge")

    def test_it_returns_the_nodes_that_arrived(self):
        self.cmds = FakeCmds(self.mel, nodes=("|a", "|a|b"))
        fbximport.cmds = self.cmds
        self.assertEqual(fbximport.import_nodes("C:/x/thing.fbx"),
                         ["|a", "|a|b"])

    def test_an_empty_import_is_an_empty_list_not_none(self):
        self.cmds = FakeCmds(self.mel, nodes=())
        fbximport.cmds = self.cmds
        self.assertEqual(fbximport.import_nodes("C:/x/thing.fbx"), [])

    def test_it_asks_for_the_new_nodes_by_name(self):
        """`returnNewNodes` is the whole reason this is cmds.file rather
        than the plugin's own FBXImport, which cannot report what it made."""
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertTrue(self.cmds.file_kwargs.get("returnNewNodes"))
        self.assertEqual(self.cmds.file_kwargs.get("type"), "FBX")
        self.assertTrue(self.cmds.file_kwargs.get("i"))

    def test_the_scene_frame_rate_is_never_written(self):
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertIn("FBXImportSetMayaFrameRate -v false",
                      self.mel.commands)

    def test_the_plugin_is_loaded_when_it_is_not_there(self):
        self.cmds = FakeCmds(self.mel, loaded=False)
        fbximport.cmds = self.cmds
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.cmds.loaded_plugins, ["fbxmaya"])

    def test_an_already_loaded_plugin_is_not_loaded_again(self):
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.cmds.loaded_plugins, [])

    def test_a_flag_missing_on_some_maya_build_does_not_stop_the_import(self):
        """Best-effort, like every other option block in this project: an
        unknown flag must not cost the animator the import."""
        self.mel = FakeMel("exmerge",
                           unknown={"FBXImportSetMayaFrameRate"})
        self.cmds = FakeCmds(self.mel)
        fbximport.mel = self.mel
        fbximport.cmds = self.cmds
        self.assertEqual(fbximport.import_nodes("C:/x/thing.fbx"), ["|thing"])
        self.assertEqual(self.cmds.mode_during_import, "add")

    def test_a_mode_query_that_answers_nothing_leaves_the_mode_alone(self):
        """Nothing to put back is not an excuse to write a guess."""
        self.mel = FakeMel("")
        self.cmds = FakeCmds(self.mel)
        fbximport.mel = self.mel
        fbximport.cmds = self.cmds
        fbximport.import_nodes("C:/x/thing.fbx")
        self.assertEqual(self.cmds.mode_during_import, "add")
        self.assertEqual(self.mel.mode, "add")


if __name__ == "__main__":
    unittest.main()

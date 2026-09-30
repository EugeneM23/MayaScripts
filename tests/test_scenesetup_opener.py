"""Open scene (2026-09-30): a character's or a weapon's own file opened as the
scene, from the right button on its icon. On a recording `cmds`; the FBX
import guard and the relink are replaced, since each has its own tests.

Spec: docs/superpowers/specs/2026-09-30-open-scene-menu-design.md
"""

import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock


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

from maya_scenesetup import catalog, opener  # noqa: E402


class FakeMel(object):
    def __init__(self, answer=1):
        self.answer = answer
        self.commands = []

    def eval(self, command):
        self.commands.append(command)
        return self.answer


class FakeCmds(object):
    def __init__(self, batch=True, scripts=(), config=None):
        self.batch = batch
        self.scripts = list(scripts)
        self.config = config
        self.opened = []
        self.flags = []
        self.deleted = []
        self.playback = None

    def about(self, batch=False, **kwargs):
        return self.batch

    def file(self, *args, **kwargs):
        if kwargs.get("query"):
            return False
        if kwargs.get("open"):
            self.opened.append((args, kwargs))
        elif "modified" in kwargs:
            self.flags.append(kwargs["modified"])
        return None

    def objExists(self, name):
        if name == opener.SCENE_CONFIG:
            return self.config is not None
        return name in self.scripts

    def scriptNode(self, name, **kwargs):
        return self.config

    def playbackOptions(self, **kwargs):
        self.playback = kwargs

    def ls(self, *args, **kwargs):
        if kwargs.get("type") == "script":
            return list(self.scripts)
        return []

    def lockNode(self, node, **kwargs):
        pass

    def delete(self, node):
        self.deleted.append(node)
        self.scripts.remove(node)


class OpenAsset(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        os.makedirs(os.path.join(self.tmp, "assets"))
        self.ma = self._file("Manny_Rig.ma")
        self.fbx = self._file("Spear_01.fbx")
        self.real = (opener.cmds, opener.mel, catalog._CONTAINER)
        catalog._CONTAINER = self.tmp.replace("\\", "/")
        self.cmds = FakeCmds()
        self.mel = FakeMel()
        opener.cmds, opener.mel = self.cmds, self.mel
        self.relinked = (0, [])
        self.fbx_opened = []
        patches = [
            mock.patch.object(opener.colour, "relink_images",
                              lambda nodes, resolve: self.relinked),
            mock.patch.object(opener.fbximport, "open_file",
                              lambda path: self.fbx_opened.append(path)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        opener.cmds, opener.mel, catalog._CONTAINER = self.real

    def _file(self, name):
        path = os.path.join(self.tmp, "assets", name).replace("\\", "/")
        with open(path, "w") as handle:
            handle.write("//Maya ASCII")
        return path

    def test_a_scene_opens_with_its_script_nodes_off(self):
        opener.open_asset(self.ma, "Manny [rig]")
        (args, kwargs), = self.cmds.opened
        self.assertEqual(args, (self.ma,))
        self.assertTrue(kwargs["force"])
        self.assertFalse(kwargs["executeScriptNodes"])
        self.assertFalse(kwargs["prompt"])

    def test_the_line_names_the_file_under_the_plugin_and_warns(self):
        text = opener.open_asset(self.ma, "Manny [rig]")
        self.assertTrue(text.startswith("Opened Manny [rig] - assets/Manny_Rig.ma"))
        self.assertIn("Save As", text)
        self.assertNotIn(self.tmp.replace("\\", "/"), text)

    def test_the_scene_reads_unmodified_after_the_relink(self):
        opener.open_asset(self.ma, "Manny [rig]")
        self.assertEqual(self.cmds.flags, [False])

    def test_the_ranges_come_from_the_config_node_never_evaluated(self):
        self.cmds.config = "playbackOptions -min 5 -max 45 -ast 0 -aet 50 ;"
        opener.open_asset(self.ma, "Manny [rig]")
        self.assertEqual(self.cmds.playback, dict(minTime=5.0, maxTime=45.0,
                                                  animationStartTime=0.0,
                                                  animationEndTime=50.0))
        self.assertEqual(self.mel.commands, [])

    def test_a_vaccine_node_is_deleted_and_named(self):
        self.cmds.scripts = ["vaccine_gene", "uiConfigurationScriptNode"]
        text = opener.open_asset(self.ma, "Manny [rig]")
        self.assertEqual(self.cmds.deleted, ["vaccine_gene"])
        self.assertIn("removed malware script node(s): vaccine_gene", text)

    def test_a_missing_image_is_named(self):
        self.relinked = (2, [self.tmp + "/assets/Orc_D/Orc_D_Body_Color.jpg"])
        text = opener.open_asset(self.ma, "Orc D [rig]")
        self.assertIn("missing in the plugin: Orc_D_Body_Color.jpg", text)

    def test_an_fbx_opens_through_the_import_guard(self):
        text = opener.open_asset(self.fbx, "Spear 01")
        self.assertEqual(self.fbx_opened, [self.fbx])
        self.assertEqual(self.cmds.opened, [])
        self.assertTrue(text.startswith("Opened Spear 01 - assets/Spear_01.fbx"))

    def test_an_fbx_reads_unmodified_too(self):
        """An FBX open is an import into a new scene, which Maya reads as a
        change (measured on every catalog weapon)."""
        opener.open_asset(self.fbx, "Spear 01")
        self.assertEqual(self.cmds.flags, [False])

    def test_a_missing_file_opens_nothing(self):
        path = self.tmp + "/assets/Gone.ma"
        text = opener.open_asset(path, "Gone")
        self.assertEqual(text, "Gone: the plugin has no assets/Gone.ma - nothing opened.")
        self.assertEqual(self.cmds.opened, [])

    def test_cancel_on_save_changes_opens_nothing(self):
        self.cmds.batch = False
        self.mel.answer = 0
        text = opener.open_asset(self.ma, "Manny [rig]")
        self.assertEqual(text, opener.CANCELLED)
        self.assertEqual(self.mel.commands, ['saveChanges("")'])
        self.assertEqual(self.cmds.opened, [])
        self.assertEqual(self.fbx_opened, [])

    def test_save_changes_saying_go_on_opens(self):
        self.cmds.batch = False
        self.mel.answer = 1
        opener.open_asset(self.ma, "Manny [rig]")
        self.assertEqual(len(self.cmds.opened), 1)


class PluginRelative(unittest.TestCase):

    def setUp(self):
        self.real = catalog._CONTAINER
        catalog._CONTAINER = "C:/Users/me/Documents/maya/scripts/SkeldarAnim"

    def tearDown(self):
        catalog._CONTAINER = self.real

    def test_under_the_plugin(self):
        self.assertEqual(opener.plugin_relative(
            "C:\\Users\\me\\Documents\\maya\\scripts\\SkeldarAnim\\assets\\X.ma"),
            "assets/X.ma")

    def test_outside_the_plugin_is_the_path_itself(self):
        self.assertEqual(opener.plugin_relative("D:/elsewhere/X.ma"),
                         "D:/elsewhere/X.ma")

    def test_a_folder_that_only_starts_the_same_is_outside(self):
        self.assertEqual(opener.plugin_relative(
            "C:/Users/me/Documents/maya/scripts/SkeldarAnimOld/assets/X.ma"),
            "C:/Users/me/Documents/maya/scripts/SkeldarAnimOld/assets/X.ma")


if __name__ == "__main__":
    unittest.main()

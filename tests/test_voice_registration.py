"""Voice is registered where the hub, the icons and the installer look for it,
and its panel's pure parts behave without a scene (run under mayapy)."""

import os
import re
import unittest

import install
import maya_hub
import maya_hubicons

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "SkeldarAnim")


class Registration(unittest.TestCase):

    def test_voice_is_a_section_in_the_scene_group_after_stash(self):
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertIn("voice", keys)
        self.assertEqual(keys.index("voice"), keys.index("stash") + 1)
        section = [s for s in maya_hub.SECTIONS if s.key == "voice"][0]
        self.assertEqual(section.module, "maya_voice.window")
        self.assertEqual(section.builder, "build_panel")
        self.assertEqual(section.group, "scene")
        self.assertEqual(section.icon, "mic")

    def test_its_icons_exist(self):
        self.assertIn("mic", maya_hubicons.ICONS)
        self.assertIn("screen", maya_hubicons.ICONS)

    def test_the_package_ships_and_its_modules_are_on_disk(self):
        self.assertIn("maya_voice", install.payload())
        for name in ("__init__.py", "protocol.py", "jitter.py", "gate.py",
                     "roster.py", "pcm.py", "ws.py", "session.py",
                     "media.py", "window.py"):
            path = os.path.join(PLUGIN, "maya_voice", name)
            self.assertTrue(os.path.isfile(path), path)

    def test_the_pure_modules_name_neither_maya_nor_qt(self):
        #  the rule the spec states: only media.py and window.py touch Qt or cmds
        banned = re.compile(r"^\s*(import|from)\s+(maya|PySide\w*)(\.|\s|$)",
                            re.MULTILINE)
        for name in ("protocol", "jitter", "gate", "roster", "pcm", "ws",
                     "session"):
            with open(os.path.join(PLUGIN, "maya_voice", name + ".py"),
                      encoding="utf-8") as handle:
                source = handle.read()
            self.assertIsNone(banned.search(source), name)

    def test_the_server_folder_is_not_in_the_payload(self):
        self.assertNotIn("voice_server", install.payload())
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "voice_server")))


class FakeCmds(object):
    """Records every cmds call; queries of text fields answer what was set.

    mayapy in batch has no UI commands (textField, text, button), so the
    panel's builder and its status line are run against this instead.
    """

    def __init__(self):
        self.calls = []
        self.fields = {}

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "textField" and kwargs.get("query"):
                return self.fields.get(args[0] if args else "", "")
            if name == "optionVar" and kwargs.get("query"):
                raise RuntimeError("no such optionVar")
            return None
        return call


class PanelPureParts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            import maya.cmds  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("needs mayapy (maya.cmds)")
        import maya_voice.window as window
        cls.window = window

    def setUp(self):
        self._real_cmds = self.window.cmds
        self.window.cmds = FakeCmds()
        self.window.state().update(session=None, server="", name="",
                                   sharing=False, wanted=False)

    def tearDown(self):
        self.window.cmds = self._real_cmds

    def test_a_bad_room_is_refused_by_name(self):
        message = self.window.join("Bad Room!!")
        self.assertIn("letters, digits", message)

    def test_no_server_is_said_before_anything_opens(self):
        message = self.window.join("layout")
        self.assertIn("server address", message)

    def test_share_needs_a_room(self):
        self.assertEqual(self.window.toggle_share(), "Join a room first.")

    def test_viewing_with_nobody_sharing_says_so(self):
        self.assertEqual(self.window.view_screen(), "Nobody is sharing.")

    def test_room_labels_show_the_members(self):
        label = self.window._rooms_label({"room": "lay",
                                          "members": ["Eugene", "Oleg"]})
        self.assertEqual(label, "lay (2): Eugene, Oleg")
        self.assertEqual(self.window._rooms_label({"room": "empty"}),
                         "empty (0)")


if __name__ == "__main__":
    unittest.main()

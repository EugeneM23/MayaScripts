"""Tests for the window's pure helpers.

The widgets need a Maya session; what is testable here is the cache, which is
where a mistake would quietly hand the user a wrong list.
"""

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

    def test_the_cache_is_shaped_like_the_editor_reply(self):
        """One parser reads both, so the shapes must not drift apart."""
        cached = window.cache_payload(records.parse_payload(self.payload()))
        self.assertIn("assets", cached)
        self.assertEqual(len(records.parse_payload(cached)), 2)

    def test_an_empty_cache_loads_as_an_empty_list(self):
        self.assertEqual(window.records_from_cache({"assets": []}), [])


class ProjectLabel(unittest.TestCase):

    def test_shows_the_project_name_not_the_path(self):
        self.assertEqual(window._project_label("C:/x/y/Atone.uproject"), "Atone")

    def test_says_so_when_there_is_no_project(self):
        self.assertEqual(window._project_label(""), "no project")


if __name__ == "__main__":
    unittest.main()

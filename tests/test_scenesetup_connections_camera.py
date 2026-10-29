"""Connections' Camera tab (2026-10-28): the card's rows and the presses. The scene half is
docs/superpowers/plans/verify_camera_tab.py."""

import unittest

from maya_scenesetup import camera
from maya_scenesetup import connections as cx

from tests.test_scenesetup_connections import FakeMenuCmds


class Text(unittest.TestCase):

    def test_the_state_line(self):
        self.assertEqual(cx.camera_text("Head", True, True), "Camera: Head (position) - Aim Mode")
        self.assertEqual(cx.camera_text("Main", False, False), "Camera: Main")
        self.assertEqual(cx.camera_text(None, False, False), cx.NO_CAMERA_TEXT)


class Card(unittest.TestCase):

    def setUp(self):
        self.real = (cx.cmds, cx.refresh)
        self.fake = FakeMenuCmds()
        cx.cmds = self.fake
        cx.refresh = lambda *a: ""
        cx.hubstyle.take_marks()
        cx.build_panel()
        self.marks = dict((m.name, m) for m in cx.hubstyle.take_marks())

    def tearDown(self):
        cx.cmds, cx.refresh = self.real

    def test_the_parents_are_the_camera_s_five(self):
        self.assertEqual([label for _n, label in self.fake.segments[cx.CAMERA_MENU]],
                         list(camera.PARENTS))

    def test_the_camera_tab_holds_parent_position_and_aim(self):
        order = [c[1][0] if c[1] else c[2].get("label") for c in self.fake.calls
                 if c[0] in ("columnLayout", "checkBox", "button", "iconTextRadioCollection")
                 and not c[2].get("edit")]
        column = order.index(cx.TAB_COLUMN["camera"])
        for item in (cx.CAMERA_MENU, cx.CAMERA_POSITION, cx.CAMERA_APPLY,
                     cx.CAMERA_AIM_MENU, cx.CAMERA_AIM_APPLY,
                     cx.APPLY_ALL["camera"]):
            self.assertLess(column, order.index(item), item)

    def test_the_aim_is_a_row_and_apply_all_is_the_tab_s_primary(self):
        """2026-10-29: the camera's parent and its aim are picked, and the tab's
        one orange Apply all bakes them - its two buttons are gone."""
        self.assertEqual(self.marks[cx.CAMERA_AIM_SEGMENT.format(cx.AIM_ON)].role,
                         "segment")
        self.assertEqual(self.marks[cx.CAMERA_AIM_APPLY].role, "tool")
        self.assertEqual(self.marks[cx.CAMERA_APPLY].role, "tool")
        self.assertEqual(self.marks[cx.APPLY_ALL["camera"]].role, "primary")
        self.assertFalse(hasattr(cx, "CAMERA_AIM_BUTTON"))


class Presses(unittest.TestCase):

    def test_the_aim_presses_go_through_camera_aim(self):
        asked = []
        saved = cx.camera_aim, cx._run
        cx.camera_aim = lambda on=True: asked.append(on) or "done"
        cx._run = lambda action: action()
        try:
            cx._press_camera_aim_mode()
            cx._press_camera_default()
        finally:
            cx.camera_aim, cx._run = saved
        self.assertEqual(asked, [True, False])

    def test_no_camera_refuses_the_parent(self):
        saved = cx._camera_bone
        cx._camera_bone = lambda: (None, "select any part of a character")
        try:
            self.assertEqual(cx.camera_parent("Head"), "select any part of a character")
            self.assertEqual(cx.camera_aim(True), "select any part of a character")
        finally:
            cx._camera_bone = saved


if __name__ == "__main__":
    unittest.main()

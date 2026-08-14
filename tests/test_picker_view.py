import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from maya_overrig import bodymap, picker_view


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class TestPickerView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.view = picker_view.PickerView()

    def test_one_item_per_button(self):
        self.assertEqual(len(self.view.items_by_id), len(bodymap.BUTTONS))

    def test_item_geometry_matches_bodymap(self):
        b = bodymap.button_by_id("head")
        item = self.view.items_by_id["head"]
        rect = item.rect()
        self.assertEqual(rect.width(), b.w)
        self.assertEqual(rect.height(), b.h)
        self.assertEqual(item.pos().x(), b.x)
        self.assertEqual(item.pos().y(), b.y)

    def test_items_start_neutral(self):
        for item in self.view.items_by_id.values():
            self.assertEqual(item.state, picker_view.STATE_NEUTRAL)

    def test_set_selected_marks_only_those_ids(self):
        self.view.set_selected(["head", "hand_l"])
        self.assertEqual(self.view.items_by_id["head"].state,
                         picker_view.STATE_SELECTED)
        self.assertEqual(self.view.items_by_id["hand_l"].state,
                         picker_view.STATE_SELECTED)
        self.assertEqual(self.view.items_by_id["pelvis"].state,
                         picker_view.STATE_NEUTRAL)

    def test_set_selected_clears_previous(self):
        self.view.set_selected(["head"])
        self.view.set_selected(["pelvis"])
        self.assertEqual(self.view.items_by_id["head"].state,
                         picker_view.STATE_NEUTRAL)

    def test_items_start_available(self):
        for item in self.view.items_by_id.values():
            self.assertTrue(item.available)

    def test_set_available_dims_the_rest(self):
        self.view.set_available(["head"])
        self.assertTrue(self.view.items_by_id["head"].available)
        self.assertFalse(self.view.items_by_id["pelvis"].available)

    def test_unavailable_items_do_not_accept_hover(self):
        self.view.set_available(["head"])
        self.assertFalse(
            self.view.items_by_id["pelvis"].acceptHoverEvents())

    def test_left_and_right_get_different_colours(self):
        left = picker_view.region_colour("arm_l")
        right = picker_view.region_colour("arm_r")
        self.assertNotEqual(left.name(), right.name())

    def test_centre_regions_share_one_colour(self):
        self.assertEqual(picker_view.region_colour("spine").name(),
                         picker_view.region_colour("head").name())
        self.assertEqual(picker_view.region_colour("root").name(),
                         picker_view.region_colour("spine").name())

    def test_scene_rect_matches_canvas(self):
        rect = self.view.scene().sceneRect()
        self.assertEqual(rect.width(), bodymap.CANVAS_W)
        self.assertEqual(rect.height(), bodymap.CANVAS_H)


if __name__ == "__main__":
    unittest.main()

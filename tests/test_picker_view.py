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


class TestInteraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.view = picker_view.PickerView()
        self.view.resize(400, 620)
        self.emitted = []
        self.view.selection_requested.connect(
            lambda ids, mode: self.emitted.append((list(ids), mode)))

    @staticmethod
    def _index_finger_rect():
        """A marquee covering the whole index finger row, joints included."""
        first = bodymap.button_by_id("index_metacarpal_l")
        last = bodymap.button_by_id("index_03_l")
        return QtCore.QRectF(first.x - 1, first.y - 1,
                             (last.x + last.w) - first.x + 2, first.h + 2)

    def test_ids_in_rect_finds_a_whole_finger(self):
        found = self.view.ids_in_rect(self._index_finger_rect())
        for expected in ("index_metacarpal_l", "index_01_l",
                         "index_02_l", "index_03_l"):
            self.assertIn(expected, found)

    def test_ids_in_rect_stays_within_one_finger(self):
        found = self.view.ids_in_rect(self._index_finger_rect())
        self.assertNotIn("middle_metacarpal_l", found)
        self.assertNotIn("thumb_01_l", found)

    def test_ids_in_rect_skips_unavailable(self):
        self.view.set_available(["index_01_l"])
        found = self.view.ids_in_rect(self._index_finger_rect())
        self.assertEqual(found, ["index_01_l"])

    def test_ids_in_rect_empty_outside_the_body(self):
        corner = QtCore.QRectF(0, bodymap.CANVAS_H - 4, 4, 4)
        self.assertEqual(self.view.ids_in_rect(corner), [])

    def test_modifier_mapping(self):
        self.assertEqual(picker_view.mode_for(QtCore.Qt.NoModifier),
                         picker_view.MODE_REPLACE)
        self.assertEqual(picker_view.mode_for(QtCore.Qt.ShiftModifier),
                         picker_view.MODE_ADD)
        self.assertEqual(picker_view.mode_for(QtCore.Qt.ControlModifier),
                         picker_view.MODE_TOGGLE)

    def test_click_emits_replace_for_that_button(self):
        self.view.emit_click("head", picker_view.MODE_REPLACE)
        self.assertEqual(self.emitted, [(["head"], "replace")])

    def test_marquee_emits_every_covered_id(self):
        self.view.emit_marquee(self._index_finger_rect(), picker_view.MODE_ADD)
        ids, mode = self.emitted[0]
        self.assertEqual(mode, "add")
        self.assertIn("index_03_l", ids)

    def test_marquee_covering_nothing_emits_nothing(self):
        empty = QtCore.QRectF(bodymap.CANVAS_W / 2 - 2,
                              bodymap.CANVAS_H - 6, 4, 4)
        self.assertEqual(self.view.ids_in_rect(empty), [],
                         "picked a spot that is not actually empty")
        self.view.emit_marquee(empty, picker_view.MODE_REPLACE)
        self.assertEqual(self.emitted, [])


if __name__ == "__main__":
    unittest.main()

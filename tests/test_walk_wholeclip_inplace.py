"""In place on a whole clip (2026-11-19): the root's travel along the floor taken off every joint."""
import unittest

import numpy as np

from maya_walk import wholeclip as wcl
from maya_walk import scene as ws


def walker(frames=10, step=7.0):
    """root, pelvis under it, a hand: the root walks +Z and climbs a little, the pelvis bobs and turns."""
    names, parents = ["root", "pelvis", "hand"], [-1, 0, 1]
    w = np.tile(np.eye(4), (3, frames, 1, 1))
    for f in range(frames):
        a = 0.2 * f
        turn = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
        w[0, f, 3, :3] = (0.3 * f, 0.5 * f, step * f)
        w[1, f, :3, :3] = turn
        w[1, f, 3, :3] = w[0, f, 3, :3] + (0, 95 + np.sin(f), 0)
        w[2, f, 3, :3] = w[1, f, 3, :3] + (30, 10, 5) @ turn
    return names, parents, w


class InPlace(unittest.TestCase):
    def test_the_root_stands_still_on_the_floor_and_keeps_its_height(self):
        names, parents, w = walker()
        out, travel = wcl.in_place(w, names, parents)
        self.assertLess(np.abs(out[0, :, 3, [0, 2]] - w[0, 0, 3, [0, 2]][:, None]).max(), 1e-9)
        np.testing.assert_allclose(out[0, :, 3, 1], w[0, :, 3, 1])
        self.assertAlmostEqual(travel, np.hypot(0.3 * 9, 7.0 * 9))

    def test_the_body_plays_about_the_root_as_before(self):
        names, parents, w = walker()
        out, _t = wcl.in_place(w, names, parents)
        np.testing.assert_allclose(out[:, :, 3, :3] - out[0, :, 3, :3][None], w[:, :, 3, :3] - w[0, :, 3, :3][None],
                                   atol=1e-9)
        np.testing.assert_array_equal(out[:, :, :3, :3], w[:, :, :3, :3])

    def test_the_input_is_not_changed(self):
        names, parents, w = walker()
        keep = w.copy()
        wcl.in_place(w, names, parents)
        np.testing.assert_array_equal(w, keep)

    def test_a_skeleton_with_no_joint_named_root_uses_its_top_joint(self):
        names, parents, w = walker()
        out, travel = wcl.in_place(w, ["hips", "spine", "hand"], parents)
        self.assertGreater(travel, 60.0)
        self.assertLess(np.abs(out[0, :, 3, 2] - w[0, 0, 3, 2]).max(), 1e-9)

    def test_another_up_axis(self):
        names, parents, w = walker()
        out, _t = wcl.in_place(w, names, parents, up=(0.0, 0.0, 1.0))      # Z up: the climb along Z stays
        np.testing.assert_allclose(out[0, :, 3, 2], w[0, :, 3, 2])
        self.assertLess(np.abs(out[0, :, 3, 1] - w[0, 0, 3, 1]).max(), 1e-9)


class Asked(unittest.TestCase):
    def test_the_card_s_chip_asks_it(self):
        self.assertTrue(ws.whole_in_place({"in_place": 1.0}, None))
        self.assertFalse(ws.whole_in_place({"in_place": 0.0}, {"in_place": 1.0}))

    def test_with_no_parameters_the_model_s_knob_asks_it(self):
        self.assertTrue(ws.whole_in_place(None, {"in_place": 1.0}))
        self.assertFalse(ws.whole_in_place(None, None))


if __name__ == "__main__":
    unittest.main()


class CardKeepsInPlace(unittest.TestCase):
    def test_a_whole_clip_greys_the_timing_but_not_in_place(self):
        from unittest import mock
        from maya_walk import panel
        edits = {}

        def control(name, **kw):
            if kw.get("exists"):
                return True
            if kw.get("query"):
                return "tip"
            edits[name] = kw.get("enable")
        fake = mock.Mock(floatSliderGrp=control, checkBox=control)
        with mock.patch.object(panel, "_cmds", return_value=fake):
            panel._grey_timing(True)
        self.assertNotIn(panel.IN_PLACE_BOX, edits)
        self.assertIn(panel.SPEED, edits)
        self.assertFalse(edits[panel.SPEED])

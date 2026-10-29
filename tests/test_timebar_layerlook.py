"""The layer panel's layout and rules (2026-10-18), pure: no Maya, no Qt.
Spec: docs/superpowers/specs/2026-10-18-time-bar-layer-panel-design.md"""
import os
import subprocess
import sys
import unittest

from maya_timebar import layerlook as L
from maya_timebar import look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def anim_rows(n):
    rows = [{"name": "L%d" % i, "label": "L%d" % i, "mode": "add", "weight": 1.0, "mute": False,
             "solo": False, "lock": False, "active": i == 0, "base": False} for i in range(n - 1)]
    return rows + [{"name": "BaseAnimation", "label": "BaseAnimation", "mode": "base", "weight": 1.0,
                    "mute": False, "solo": False, "lock": False, "active": False, "base": True}]


class Pure(unittest.TestCase):

    def test_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_timebar.layerlook; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; "
                "print(bad); sys.exit(1 if bad else 0)") % PLUGIN
        self.assertEqual(subprocess.call([sys.executable, "-c", code]), 0)


class Height(unittest.TestCase):

    def test_clamped_between_the_least_and_the_room(self):
        self.assertEqual(L.clamp_height(100, 600), L.MIN_H)
        self.assertEqual(L.clamp_height(300, 600), 300)
        self.assertEqual(L.clamp_height(900, 600), 600 - L.TOP_ROOM)

    def test_no_room_still_gives_the_least(self):
        self.assertEqual(L.clamp_height(300, 80), L.MIN_H)


class Place(unittest.TestCase):

    def test_the_column_stands_right_of_the_timeline_over_the_strip(self):
        strip = (100, 900, 1500, 84)
        timeline = (106, 940, 1100, 40)
        x, y, w, h = L.column_rect(strip, timeline, 268, 1.0)
        self.assertEqual(x, 106 + 1100 + L.SIDE)
        self.assertEqual(x + w, 100 + 1500 - L.SIDE)
        self.assertEqual(y + h, 900 - L.ABOVE)
        self.assertEqual(h, 268)

    def test_the_lanes_span_from_the_timeline_to_the_column(self):
        column = (1212, 626, 382, 268)
        timeline = (106, 940, 1100, 40)
        self.assertEqual(L.lanes_rect(column, timeline), (106, 626, 1212 - 106, 268))


class Layouts(unittest.TestCase):

    def test_rows_fill_the_well_and_scroll_past_it(self):
        lay = L.Layout(380, 268, anim_rows(12), "anim", 1.0)
        self.assertEqual(len(lay.rows), 12)
        self.assertEqual(lay.rows[1][1] - lay.rows[0][1], L.ROW_H + L.ROW_GAP)
        self.assertGreater(lay.max_scroll, 0)
        few = L.Layout(380, 268, anim_rows(2), "anim", 1.0)
        self.assertEqual(few.max_scroll, 0)

    def test_scale_multiplies_every_length(self):
        a, b = L.Layout(380, 268, anim_rows(3), "anim", 1.0), L.Layout(570, 402, anim_rows(3), "anim", 1.5)
        self.assertAlmostEqual(b.rows[0][3], a.rows[0][3] * 1.5)
        self.assertAlmostEqual(b.grip[3], a.grip[3] * 1.5)

    def test_the_foot_differs_by_tab(self):
        self.assertEqual([n for n, _r in L.Layout(380, 268, [], "anim", 1.0).foot],
                         ["add", "addsel", "remsel", "merge", "delete"])
        self.assertEqual([n for n, _r in L.Layout(380, 268, [], "disp", 1.0).foot],
                         ["add", "addsel", "remsel", "select", "delete"])

    def test_a_row_has_its_controls_left_to_right(self):
        parts = L.row_parts((0, 0, 360, 30), "anim", 1.0)
        order = ["mode", "name", "wkey", "weight", "wnum", "mute", "solo", "lock"]
        xs = [parts[n][0] for n in order]
        self.assertEqual(xs, sorted(xs))
        disp = L.row_parts((0, 0, 360, 30), "disp", 1.0)
        self.assertEqual(sorted(disp), ["name", "playback", "swatch", "type", "visible"])

    def test_the_base_row_has_no_weight_and_no_solo(self):
        parts = L.row_parts((0, 0, 360, 30), "anim", 1.0, base=True)
        self.assertNotIn("weight", parts)
        self.assertNotIn("wkey", parts)
        self.assertNotIn("solo", parts)

    def test_the_weight_key_cell_s_state(self):
        """2026-10-20: the weight's key cell, the Channel Box's."""
        self.assertIsNone(L.weight_state({"base": True}, 10))
        self.assertEqual(L.weight_state({"weight_keys": ()}, 10), "plain")
        self.assertEqual(L.weight_state({"weight_keys": (0.0, 10.0)}, 10), "onkey")
        self.assertEqual(L.weight_state({"weight_keys": (0.0, 10.0)}, 5), "keyed")
        cx, cy, cw, ch = L.wkey_cell((100, 0, 14, 30), 1.0)
        self.assertEqual((cx + cw / 2.0, cy + ch / 2.0), (107.0, 15.0))


class Hits(unittest.TestCase):

    def setUp(self):
        self.lay = L.Layout(380, 268, anim_rows(4), "anim", 1.0)

    def centre(self, rect):
        return rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0

    def test_grip_tab_lanes_and_foot(self):
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.grip), scroll=0), ("grip",))
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.segments["disp"]), scroll=0), ("tab", "disp"))
        self.assertEqual(L.hit(self.lay, *self.centre(self.lay.lanes), scroll=0), ("lanes",))
        name, rect = self.lay.foot[0]
        self.assertEqual(L.hit(self.lay, *self.centre(rect), scroll=0), ("foot", "add"))

    def test_a_row_and_its_parts_with_the_scroll(self):
        rect = self.lay.row_at(1, 0)
        parts = L.row_parts(rect, "anim", 1.0)
        self.assertEqual(L.hit(self.lay, *self.centre(parts["mute"]), scroll=0), ("row", 1, "mute"))
        self.assertEqual(L.hit(self.lay, *self.centre(parts["name"]), scroll=0), ("row", 1, "name"))
        scrolled = self.lay.row_at(2, L.ROW_H + L.ROW_GAP)
        self.assertEqual(scrolled, rect)

    def test_the_base_row_has_no_solo_weight_or_number_to_hit(self):
        lay = L.Layout(380, 268, anim_rows(4), "anim", 1.0)
        base_i = len(lay.rows) - 1
        rect = lay.row_at(base_i, 0)
        # the same slots a non-base row would have, measured from a non-base row_parts
        plain = L.row_parts(rect, "anim", 1.0)
        for part in ("solo", "weight", "wnum"):
            self.assertEqual(L.hit(lay, *self.centre(plain[part]), scroll=0), ("row", base_i, "name"))

    def test_outside_the_rows_in_the_well_is_nothing(self):
        x, y, w, h = self.lay.well
        self.assertIsNone(L.hit(self.lay, x + w / 2.0, y + h - 2, scroll=0))


class Rules(unittest.TestCase):

    def test_weight_from_x(self):
        self.assertEqual(L.weight_at(0, (10, 0, 100, 14)), 0.0)
        self.assertEqual(L.weight_at(60, (10, 0, 100, 14)), 0.5)
        self.assertEqual(L.weight_at(500, (10, 0, 100, 14)), 1.0)

    def test_mute_and_solo_dim(self):
        rows = anim_rows(3)
        self.assertFalse(L.dimmed(rows[0], rows))
        rows[1]["mute"] = True
        self.assertTrue(L.dimmed(rows[1], rows))
        rows[0]["solo"] = True
        self.assertFalse(L.dimmed(rows[0], rows))
        self.assertFalse(L.dimmed(rows[2], rows))      # BaseAnimation is never left out by a solo

    def test_a_layer_the_selection_belongs_to_reads_green(self):
        """2026-10-29: «подсвечивать зелененьким имена анимационных слоев которым он
        принадлежит» - green wins over the active row's accent (its bold and its frame
        still mark it)."""
        self.assertEqual(L.name_tone(True, False), "ok")
        self.assertEqual(L.name_tone(True, True), "ok")

    def test_any_other_name_is_the_accent_lit_and_plain_text_cold(self):
        self.assertEqual(L.name_tone(False, True), "accent_text")
        self.assertEqual(L.name_tone(False, False), "text")

    def test_display_type_steps(self):
        self.assertEqual([L.step_type(t) for t in (0, 1, 2)], [1, 2, 0])

    def test_signature_sees_every_value(self):
        rows = anim_rows(2)
        before = L.signature(rows)
        rows[0]["weight"] = 0.5
        self.assertNotEqual(L.signature(rows), before)

    def test_schedule_nearest_first_in_and_farthest_first_out(self):
        parts = [(0, 0, 10, 10), (0, 200, 10, 10)]
        (o_far, f_far), (o_near, f_near) = L.schedule(parts, (5, 205), 1.0)
        self.assertLess(o_near, o_far)
        self.assertLess(f_far, f_near)
        self.assertEqual(o_near, look.burst_delay(0, 0))


class LaneRules(unittest.TestCase):
    """The column's selection and the lanes (2026-10-19)."""

    names = ["A3", "A2", "A1", "Base"]

    def test_a_plain_click_selects_alone(self):
        self.assertEqual(L.selection_after(["A3", "A1"], "A2", "A3", False, False, self.names), (["A2"], "A2"))

    def test_ctrl_toggles(self):
        self.assertEqual(L.selection_after(["A3"], "A1", "A3", True, False, self.names), (["A3", "A1"], "A1"))
        self.assertEqual(L.selection_after(["A3", "A1"], "A1", "A3", True, False, self.names), (["A3"], "A3"))

    def test_shift_takes_the_range(self):
        self.assertEqual(L.selection_after(["A3"], "A1", "A3", False, True, self.names),
                         (["A3", "A2", "A1"], "A1"))
        self.assertEqual(L.selection_after(["Base"], "A3", "A2", True, True, self.names),
                         (["A3", "A2", "Base"], "A3"))

    def test_lane_at_and_between(self):
        lay = L.Layout(300, 268, anim_rows(3), "anim", 1.0)
        r = lay.row_at(1, 0)
        self.assertEqual(L.lane_at(lay, r[1] + 2, 0), 1)
        self.assertIsNone(L.lane_at(lay, 0, 0))
        self.assertEqual(L.lanes_between(2, 0), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()

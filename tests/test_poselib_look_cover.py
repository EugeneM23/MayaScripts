"""The Pose Library window's look as data, the corners `test_poselib_look` leaves out: a zoom that
goes nowhere, the skill drop's own caption, an applied status with no count.
"""
import unittest

from maya_poselib import look


class ZoomTime(unittest.TestCase):

    def test_no_way_to_go_takes_no_time(self):
        self.assertEqual(look.zoom_ms(0.0, 0.0), 0)
        self.assertEqual(look.zoom_ms(1.0, 1.0), 0)
        self.assertEqual(look.zoom_ms(0.4, 0.4), 0)

    def test_the_whole_way_takes_the_whole_time_in_or_out(self):
        self.assertEqual(look.zoom_ms(0.0, 1.0), look.ZOOM_IN_MS)
        self.assertEqual(look.zoom_ms(1.0, 0.0), look.ZOOM_OUT_MS)

    def test_part_of_the_way_takes_its_share_and_never_under_the_least(self):
        self.assertEqual(look.zoom_ms(0.0, 0.5), max(look.ZOOM_MIN_MS, int(round(look.ZOOM_IN_MS * 0.5))))
        self.assertEqual(look.zoom_ms(0.5, 0.5001), look.ZOOM_MIN_MS)


class DropCaption(unittest.TestCase):

    def test_a_skill_says_its_own_text_else_the_card_s_name(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "skill", "text": "Fist - Skill 3"}),
                         ("Fist - Skill 3", True))
        self.assertEqual(look.drop_caption("Fist", {"kind": "skill"}), ("Fist", True))

    def test_a_card_with_no_name_is_called_pose(self):
        self.assertEqual(look.drop_caption("", {"kind": "skill"}), ("Pose", True))

    def test_nothing_to_apply_to_says_why_when_it_knows(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "none", "text": "no rig selected"}),
                         ("no rig selected", False))
        self.assertEqual(look.drop_caption("Fist", {"kind": "none"}), (look.NO_TARGET, False))

    def test_anything_else_reads_no_target(self):
        self.assertEqual(look.drop_caption("Fist", {"kind": "bogus"}), (look.NO_TARGET, False))
        self.assertEqual(look.drop_caption("Fist", None), (look.NO_TARGET, False))


class CurvesLine(unittest.TestCase):
    """The details' line for a card that keeps its source's curves."""

    def line(self, curves):
        return look._curves_line({"curves": curves})

    def test_the_layers_are_named_in_order(self):
        layers = [{"name": "BaseAnimation"}, {"name": "AnimLayer1"}]
        self.assertEqual(self.line({"layers": layers}),
                         "original curves %s BaseAnimation, AnimLayer1" % look.DOT)

    def test_a_card_saved_in_1p_says_it_is_pasted_by_the_bones(self):
        text = self.line({"layers": [{"name": "BaseAnimation"}], "first_person": True})
        self.assertTrue(text.endswith("%s %s" % (look.DOT, look.SAVED_IN_1P)))

    def test_no_curves_block_or_a_broken_one_says_nothing(self):
        for data in (None, {}, "text", {"curves": None}, {"curves": {}}, {"curves": {"layers": []}},
                     {"curves": {"layers": "BaseAnimation"}}, {"curves": []}):
            self.assertEqual(look._curves_line(data), "", repr(data))

    def test_layers_with_no_text_name_say_nothing(self):
        self.assertEqual(self.line({"layers": [{"name": 3}, {}, "x", None]}), "")

    def test_a_layer_with_no_name_is_left_out_of_the_line(self):
        text = self.line({"layers": [{"name": "A"}, {}, {"name": "B"}]})
        self.assertEqual(text, "original curves %s A, B" % look.DOT)


class StatusLine(unittest.TestCase):

    def test_an_apply_with_no_count_says_it_was_applied(self):
        self.assertEqual(look.status_line({"name": "Fist", "target": "Rig"}), "Fist onto Rig: applied")

    def test_an_apply_with_no_target_names_only_the_card(self):
        self.assertEqual(look.status_line({"name": "Fist", "count": 2, "noun": "bones"}),
                         "Fist: 2 bones keyed")

    def test_an_apply_with_no_name_is_called_pose(self):
        self.assertEqual(look.status_line({"target": "Rig"}), "Pose onto Rig: applied")


if __name__ == "__main__":
    unittest.main()

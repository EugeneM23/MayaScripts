"""maya_hubpop_rules - where a popup stands in its viewport (pure, no Maya).

The clamp keeps a popup inside its viewport's rectangle (a drag cannot carry
it onto another monitor), the offset moves it with the viewport, and the
optionVars' text round-trips. Spec:
docs/superpowers/specs/2026-10-09-hub-section-popups-design.md.
"""

import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya_hubpop_rules as rules

VIEW = (100, 50, 800, 600)     # a viewport at (100, 50), 800 x 600


class ClampOrigin(unittest.TestCase):

    def test_inside_is_unchanged(self):
        self.assertEqual(rules.clamp_origin(200, 150, 300, 200, VIEW),
                         (200, 150))

    def test_past_the_left_or_top_edge_stops_at_it(self):
        self.assertEqual(rules.clamp_origin(-500, -500, 300, 200, VIEW),
                         (100, 50))

    def test_past_the_right_or_bottom_edge_stops_inside(self):
        self.assertEqual(rules.clamp_origin(9000, 9000, 300, 200, VIEW),
                         (100 + 800 - 300, 50 + 600 - 200))

    def test_a_window_bigger_than_the_viewport_sits_at_its_corner(self):
        self.assertEqual(rules.clamp_origin(500, 500, 900, 700, VIEW),
                         (100, 50))

    def test_a_drag_onto_another_monitor_is_held_on_the_viewport(self):
        # the cursor far off to the left, on a monitor beside the viewport
        x, y = rules.clamp_origin(-3000, 200, 300, 200, VIEW)
        self.assertGreaterEqual(x, VIEW[0])
        self.assertLessEqual(x + 300, VIEW[0] + VIEW[2])


class OffsetAndOrigin(unittest.TestCase):

    def test_offset_is_logical_from_the_viewport_corner(self):
        self.assertEqual(rules.offset_of(250, 110, VIEW, 1.5),
                         ((250 - 100) / 1.5, (110 - 50) / 1.5))

    def test_origin_of_an_offset_round_trips(self):
        offset = rules.offset_of(340, 210, VIEW, 1.5)
        self.assertEqual(rules.origin_of(offset, VIEW, 300, 200, 1.5),
                         (340, 210))

    def test_origin_of_clamps_an_offset_past_a_shrunk_viewport(self):
        small = (100, 50, 400, 300)
        self.assertEqual(rules.origin_of((900.0, 900.0), small, 300, 200,
                                         1.0),
                         (100 + 400 - 300, 50 + 300 - 200))

    def test_the_offset_follows_the_viewport_when_it_moves(self):
        offset = rules.offset_of(340, 210, VIEW, 1.0)
        moved = (1920 + 100, 60, 800, 600)     # the viewport on monitor 2
        self.assertEqual(rules.origin_of(offset, moved, 300, 200, 1.0),
                         (1920 + 100 + 240, 60 + 160))

    def test_zero_scale_is_taken_as_one(self):
        self.assertEqual(rules.offset_of(110, 60, VIEW, 0), (10.0, 10.0))


class DefaultOffsets(unittest.TestCase):

    def test_the_first_sits_in_the_top_right_corner_inside_the_margin(self):
        x, y = rules.origin_of(rules.default_offset(0, VIEW, 300, 200, 1.0),
                               VIEW, 300, 200, 1.0)
        self.assertEqual(x, VIEW[0] + VIEW[2] - 300 - rules.MARGIN)
        self.assertEqual(y, VIEW[1] + rules.MARGIN)

    def test_each_next_cascades_down_and_left(self):
        first = rules.origin_of(rules.default_offset(0, VIEW, 300, 200, 1.0),
                                VIEW, 300, 200, 1.0)
        second = rules.origin_of(rules.default_offset(1, VIEW, 300, 200, 1.0),
                                 VIEW, 300, 200, 1.0)
        self.assertEqual(second, (first[0] - rules.CASCADE,
                                  first[1] + rules.CASCADE))

    def test_a_deep_cascade_stays_inside(self):
        for index in range(0, 40):
            x, y = rules.origin_of(rules.default_offset(index, VIEW, 300, 200,
                                                        1.0),
                                   VIEW, 300, 200, 1.0)
            self.assertGreaterEqual(x, VIEW[0])
            self.assertLessEqual(x + 300, VIEW[0] + VIEW[2])
            self.assertGreaterEqual(y, VIEW[1])
            self.assertLessEqual(y + 200, VIEW[1] + VIEW[3])


class PopupSize(unittest.TestCase):
    """The size rule (2026-10-09): the hub's dock width unless the section needs
    more, the height exactly its content plus the title row, rolled up = the title."""

    def test_the_width_is_the_dock_width(self):
        w, _h = rules.popup_size(0, 100, VIEW, 1.0, 40)
        self.assertEqual(w, rules.WIDTH)

    def test_wider_only_when_the_section_minimum_needs_it(self):
        w, _h = rules.popup_size(500, 100, VIEW, 1.0, 40)
        self.assertEqual(w, 500)

    def test_the_width_scales_with_the_display(self):
        w, _h = rules.popup_size(0, 100, VIEW, 1.5, 40)
        self.assertEqual(w, int(round(rules.WIDTH * 1.5)))

    def test_never_wider_than_the_viewport_less_its_margins(self):
        small = (0, 0, 300, 600)
        w, _h = rules.popup_size(700, 100, small, 1.0, 40)
        self.assertEqual(w, 300 - 2 * rules.MARGIN)

    def test_the_height_is_the_title_plus_the_content_and_nothing_more(self):
        _w, h = rules.popup_size(0, 300, VIEW, 1.5, 40)
        self.assertEqual(h, 340)

    def test_a_tall_section_is_capped_and_its_scroll_bar_takes_width(self):
        w, h = rules.popup_size(0, 9000, VIEW, 1.0, 40, scrollbar_w=12)
        self.assertEqual(h, rules.MAX_HEIGHT)
        self.assertEqual(w, rules.WIDTH + 12)

    def test_an_expanded_popup_is_never_taller_than_the_cap_at_any_scale(self):
        _w, h = rules.popup_size(0, 500, VIEW, 1.5, 40)
        self.assertEqual(h, int(round(rules.MAX_HEIGHT * 1.5)))

    def test_a_section_under_the_cap_is_not_scrolled(self):
        w, h = rules.popup_size(0, 100, VIEW, 1.0, 40, scrollbar_w=12)
        self.assertEqual((w, h), (rules.WIDTH, 140))

    def test_the_cap_is_smaller_than_a_tall_viewport(self):
        _w, h = rules.popup_size(0, 9000, (0, 0, 800, 2000), 1.0, 40)
        self.assertEqual(h, rules.MAX_HEIGHT)

    def test_a_short_section_keeps_the_minimum_height(self):
        _w, h = rules.popup_size(0, 10, VIEW, 1.0, 0)
        self.assertEqual(h, rules.MIN_HEIGHT)

    def test_rolled_up_the_popup_is_its_title_row_alone(self):
        w, h = rules.popup_size(0, 900, VIEW, 1.0, 40, collapsed=True)
        self.assertEqual((w, h), (rules.WIDTH, 40))

    def test_the_yes_no_memory_round_trips(self):
        self.assertEqual(rules.decode_flag(rules.encode_flag(True)), True)
        self.assertEqual(rules.decode_flag(rules.encode_flag(False)), False)
        self.assertIsNone(rules.decode_flag(None))
        self.assertIsNone(rules.decode_flag("yes"))


class Resize(unittest.TestCase):
    """The size a rolled-up popup takes (as wide as its name), the sizes the
    animator drags, the bounds a drag may take, and the optionVars (2026-10-09)."""

    def test_a_rolled_up_popup_is_as_wide_as_its_name(self):
        self.assertEqual(rules.popup_size(0, 900, VIEW, 1.0, 40, collapsed=True,
                                          title_w=190), (190, 40))

    def test_a_rolled_up_popup_is_never_narrower_than_its_name(self):
        self.assertEqual(rules.popup_size(0, 900, VIEW, 1.0, 40, collapsed=True,
                                          title_w=190, user_w=100), (190, 40))

    def test_a_rolled_up_popup_takes_a_wider_dragged_width(self):
        self.assertEqual(rules.popup_size(0, 900, VIEW, 1.0, 40, collapsed=True,
                                          title_w=190, user_w=260), (260, 40))

    def test_an_unrolled_popup_takes_the_dragged_size(self):
        self.assertEqual(rules.popup_size(0, 100, VIEW, 1.0, 40, user_w=500,
                                          user_h=300), (500, 300))

    def test_a_dragged_height_may_be_taller_than_the_automatic_cap(self):
        _w, h = rules.popup_size(0, 100, VIEW, 1.0, 40, user_h=500)
        self.assertEqual(h, 500)
        self.assertGreater(h, rules.MAX_HEIGHT)

    def test_a_dragged_size_is_held_to_the_minimums(self):
        self.assertEqual(rules.popup_size(0, 100, VIEW, 1.0, 40, user_w=50,
                                          user_h=10),
                         (rules.MIN_RESIZE_W, rules.MIN_HEIGHT))

    def test_a_dragged_width_is_held_to_the_section_minimum(self):
        w, _h = rules.popup_size(400, 100, VIEW, 1.0, 40, user_w=200)
        self.assertEqual(w, 400)

    def test_a_dragged_size_is_held_to_the_viewport_less_its_margins(self):
        self.assertEqual(rules.popup_size(0, 100, VIEW, 1.0, 40, user_w=5000,
                                          user_h=5000),
                         (VIEW[2] - 2 * rules.MARGIN, VIEW[3] - 2 * rules.MARGIN))

    def test_a_drag_cannot_carry_the_far_edges_out_of_the_viewport(self):
        origin = (VIEW[0] + 700, VIEW[1] + 100)
        _lw, high_w, _lh, high_h = rules.bounds(0, VIEW, 1.0, 40, origin=origin)
        self.assertEqual(high_w, VIEW[0] + VIEW[2] - rules.MARGIN - origin[0])
        self.assertEqual(high_h, VIEW[1] + VIEW[3] - rules.MARGIN - origin[1])

    def test_a_drag_from_inside_is_bounded_by_the_viewport_alone(self):
        _lw, high_w, _lh, _hh = rules.bounds(0, VIEW, 1.0, 40,
                                             origin=(VIEW[0] + 10, VIEW[1] + 10))
        self.assertEqual(high_w, VIEW[2] - 2 * rules.MARGIN)

    def test_the_bounds_of_a_rolled_up_popup(self):
        self.assertEqual(rules.bounds(0, VIEW, 1.0, 40, collapsed=True,
                                      title_w=190),
                         (190, 776, 40, 40))

    def test_a_dragged_height_that_scrolls_takes_the_bar_from_the_automatic_width(self):
        w, h = rules.popup_size(0, 500, VIEW, 1.0, 40, scrollbar_w=12, user_h=200)
        self.assertEqual((w, h), (rules.WIDTH + 12, 200))

    def test_the_sizes_round_trip_and_automatic_reads_as_none(self):
        text = rules.encode_pair(420.0, None)
        self.assertEqual(text, "420.0,-")
        self.assertEqual(rules.decode_pair(text), (420.0, None))
        self.assertEqual(rules.decode_pair("garbage"), (None, None))
        self.assertEqual(rules.encode_single(None), "-")
        self.assertIsNone(rules.decode_single("-"))
        self.assertIsNone(rules.decode_single("0"))
        self.assertIsNone(rules.decode_single("abc"))
        self.assertEqual(rules.decode_single(rules.encode_single(190.0)), 190.0)


class Memory(unittest.TestCase):

    def test_keys_are_written_in_order_each_once(self):
        self.assertEqual(rules.encode_keys(["weapons", "characters",
                                            "weapons", ""]),
                         "weapons,characters")

    def test_unknown_keys_are_dropped_on_read(self):
        known = ["characters", "weapons"]
        self.assertEqual(rules.decode_keys("weapons,gone,characters",
                                           known),
                         ["weapons", "characters"])

    def test_a_missing_or_empty_list_reads_as_none(self):
        self.assertEqual(rules.decode_keys(None, ["a"]), [])
        self.assertEqual(rules.decode_keys("", ["a"]), [])

    def test_read_ignores_spaces_around_keys(self):
        self.assertEqual(rules.decode_keys(" a , b ", ["a", "b"]), ["a", "b"])

    def test_an_offset_round_trips_to_two_decimals(self):
        text = rules.encode_offset((12.345, -3.0))
        self.assertEqual(text, "12.35,-3.00")
        self.assertEqual(rules.decode_offset(text), (12.35, -3.0))

    def test_a_bad_offset_reads_as_none(self):
        for text in (None, "", "1", "a,b", "1,2,3"):
            self.assertIsNone(rules.decode_offset(text))


if __name__ == "__main__":
    unittest.main()

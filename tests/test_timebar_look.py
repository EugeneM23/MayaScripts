"""maya_timebar.look - the Time Bar's arithmetic (2026-10-16)."""

import os
import subprocess
import sys
import unittest

from maya_timebar import look


class TrackTests(unittest.TestCase):

    def test_frame_and_x_round_trip(self):
        t = look.Track(-10, 90, 12, 1012)
        self.assertAlmostEqual(t.scale, 10.0)
        self.assertAlmostEqual(t.x(0), 112.0)
        self.assertAlmostEqual(t.frame(t.x(37.5)), 37.5)

    def test_whole_rounds_and_clamps(self):
        t = look.Track(0, 100, 0, 1000)
        self.assertEqual(t.whole(54.9), 5)
        self.assertEqual(t.whole(-500, lo=0, hi=60), 0)
        self.assertEqual(t.whole(5000, lo=0, hi=60), 60)

    def test_an_empty_range_still_has_width(self):
        t = look.Track(5, 5, 0, 100)
        self.assertGreater(t.scale, 0)


class CellTests(unittest.TestCase):
    """2026-10-17: the timeline's frames are cells [f, f + 1), as Maya's slider."""

    def setUp(self):
        self.t = look.Track(0, 9, 0, 100, cells=True)            # 10 cells of 10 px

    def test_the_last_frame_has_a_whole_cell(self):
        self.assertAlmostEqual(self.t.scale, 10.0)
        self.assertEqual(self.t.cell(9), (90.0, 100.0))
        self.assertEqual(self.t.end(9), 100.0)

    def test_a_press_takes_the_cell_it_falls_in(self):
        self.assertEqual(self.t.whole(44.0), 4)
        self.assertEqual(self.t.whole(49.9), 4)
        self.assertEqual(self.t.whole(50.0), 5)

    def test_a_key_between_frames_stands_in_its_cell(self):
        self.assertEqual(self.t.cell(6.47), (60.0, 70.0))
        self.assertTrue(look.on_frame(6.0))
        self.assertFalse(look.on_frame(6.47))

    def test_the_highlight_holds_its_cells_and_a_move_keeps_the_fraction(self):
        self.assertTrue(look.inside(40.6, (30, 40)))
        self.assertFalse(look.inside(41.0, (30, 40)))
        self.assertAlmostEqual(look.mapped(40.6, (30, 40), (33, 43)), 43.6)
        self.assertEqual(look.mapped(35.0, (30, 40), (30, 50)), 40)

    def test_without_cells_nothing_changes(self):
        t = look.Track(0, 10, 0, 100)
        self.assertAlmostEqual(t.scale, 10.0)
        self.assertEqual(t.whole(46.0), 5)
        self.assertEqual(t.end(10), 100.0)


class HideDelayTests(unittest.TestCase):

    def test_the_bar_waits_1_2_seconds_before_it_hides(self):
        self.assertEqual(look.HIDE_MS, 1200)


class TickTests(unittest.TestCase):

    def test_labels_leave_room_for_their_numbers(self):
        for width in (300, 800, 2000):
            t = look.Track(0, 120, 0, width)
            labels = [f for f, kind in look.ticks(t) if kind == "label"]
            gaps = {b - a for a, b in zip(labels, labels[1:])}
            self.assertEqual(len(gaps), 1)
            self.assertGreaterEqual(gaps.pop() * t.scale, look.LABEL_GAP)

    def test_every_label_is_a_multiple_of_its_step_and_inside_the_view(self):
        t = look.Track(-13, 77, 0, 900)
        found = look.ticks(t)
        self.assertTrue(all(-13 <= f <= 77 for f, _ in found))
        self.assertIn((0, "label"), found)

    def test_ticks_never_crowd(self):
        t = look.Track(0, 5000, 0, 1000)
        frames = [f for f, _ in look.ticks(t)]
        self.assertTrue(all((b - a) * t.scale >= look.TICK_GAP
                            for a, b in zip(frames, frames[1:])))

    def test_the_display_scale_widens_the_steps(self):
        t = look.Track(0, 120, 0, 600)
        step = lambda ui: [f for f, k in look.ticks(t, ui) if k == "label"][1]  # noqa: E731
        self.assertGreater(step(2.0), step(1.0))


class HitTests(unittest.TestCase):

    def setUp(self):
        self.t = look.Track(0, 100, 12, 1012)        # 10 px a frame

    def test_the_band_s_edges_are_handles(self):
        self.assertEqual(look.hit(self.t, self.t.x(20) + 3, 50, 20, 80), "p0")
        self.assertEqual(look.hit(self.t, self.t.x(80) - 4, 50, 20, 80), "p1")
        self.assertEqual(look.hit(self.t, self.t.x(50), 50, 20, 80), "now")

    def test_without_the_band_everything_scrubs(self):
        self.assertEqual(look.hit(self.t, self.t.x(20), 50, 20, 80, band=False), "now")

    def test_the_grips_live_past_the_track_s_ends(self):
        self.assertEqual(look.hit(self.t, 3, 50, 0, 100), "a0")
        self.assertEqual(look.hit(self.t, 1020, 50, 0, 100), "a1")
        self.assertEqual(look.hit(self.t, self.t.x(0) + 2, 50, 0, 100), "p0")


class DragTests(unittest.TestCase):

    def test_the_band_keeps_a_frame(self):
        self.assertEqual(look.dragged("p0", 90, 0, 100, 10, 60), (0, 100, 59, 60))
        self.assertEqual(look.dragged("p1", -5, 0, 100, 10, 60), (0, 100, 10, 11))

    def test_the_animation_range_grows_to_hold_the_band(self):
        self.assertEqual(look.dragged("p0", -20, 0, 100, 10, 60), (-20, 100, -20, 60))
        self.assertEqual(look.dragged("p1", 130, 0, 100, 10, 60), (0, 130, 10, 130))

    def test_the_animation_range_never_cuts_the_band(self):
        self.assertEqual(look.dragged("a0", 40, 0, 100, 10, 60), (10, 100, 10, 60))
        self.assertEqual(look.dragged("a1", 30, 0, 100, 10, 60), (0, 60, 10, 60))


class HighlightTests(unittest.TestCase):

    def test_a_drag_either_way(self):
        self.assertEqual(look.highlight(30, 12), (12, 30))
        self.assertEqual(look.highlight(12.4, 29.6), (12, 30))

    def test_range_array_is_end_exclusive_and_more_than_a_frame(self):
        self.assertEqual(look.range_array((12, 30)), (12.0, 31.0))
        self.assertIsNone(look.range_array((12, 12)))
        self.assertIsNone(look.range_array(None))


class KeyTests(unittest.TestCase):

    def test_neighbours(self):
        keys = [0, 6, 12.5, 18]
        self.assertEqual(look.neighbour_key(keys, 6, True), 12.5)
        self.assertEqual(look.neighbour_key(keys, 6, False), 0)
        self.assertIsNone(look.neighbour_key(keys, 18, True))
        self.assertIsNone(look.neighbour_key([], 5, False))


class TextTests(unittest.TestCase):

    def test_frames(self):
        self.assertEqual(look.frame_text(12.0), "12")
        self.assertEqual(look.frame_text(-3), "-3")
        self.assertEqual(look.frame_text(12.5), "12.5")

    def test_fps(self):
        self.assertEqual(look.fps_label("ntsc"), "30 fps")
        self.assertEqual(look.fps_label("film"), "24 fps")
        self.assertEqual(look.fps_label("23.976fps"), "23.976 fps")
        self.assertEqual([u for _, u in look.FPS], ["film", "pal", "ntsc", "show", "palf", "ntscf"])


class FullBarTests(unittest.TestCase):

    def test_zoom_keeps_the_frame_under_the_mouse(self):
        v0, v1 = look.zoomed(0, 100, 30, 0.5)
        self.assertEqual((v0, v1), (15.0, 65.0))
        self.assertEqual(look.zoomed(0, 10, 5, 0.5), (0, 10))         # never under MIN_VIEW
        self.assertEqual(look.zoomed(0, 100, 50, 4, 0, 100), (-20.0, 120.0))

    def test_highlight_parts(self):
        t = look.Track(0, 100, 0, 1000)
        self.assertEqual(look.highlight_hit(t, 200, (20, 40)), "h0")
        self.assertEqual(look.highlight_hit(t, 402, (20, 40)), "h1")
        self.assertEqual(look.highlight_hit(t, 300, (20, 40)), "hmove")
        self.assertIsNone(look.highlight_hit(t, 600, (20, 40)))
        self.assertEqual(look.highlight_hit(t, 303, (30, 30)), "hmove")
        self.assertIsNone(look.highlight_hit(t, 300, None))

    def test_key_drag_moves_and_scales(self):
        self.assertEqual(look.key_drag("hmove", (20, 40), 30, 35), (25, 45))
        self.assertEqual(look.key_drag("h1", (20, 40), 40, 50), (20, 50))
        self.assertEqual(look.key_drag("h0", (20, 40), 20, 45), (39, 40))
        self.assertEqual(look.key_drag("h1", (30, 30), 30, 33), (33, 33))

    def test_mapped_keys_follow_the_highlight(self):
        self.assertEqual(look.mapped(30, (20, 40), (20, 60)), 40)
        self.assertEqual(look.mapped(10, (20, 40), (20, 60)), 10)
        self.assertEqual(look.mapped(30, (30, 30), (33, 33)), 33)

    def test_no_motion_is_left_for_the_time_bar(self):
        """2026-11-19, «удаляем все подсветки и анимации из плагина»: the playhead's
        reached keys, the slide, the unroll, the reveal glow, the key effects and the
        steel cooling are gone."""
        for name in ("passed", "flash", "opening", "slide", "unroll", "reveal_glow", "EFFECT_MS",
                     "key_changes", "progress", "play_glow", "delete_plan", "shards", "shard_groups",
                     "sparks", "cooling", "plate", "spread", "steel_glow", "HEAT", "COOL_MS", "RIM",
                     "HOVER_MS", "FLASH_MS", "approach", "back_out", "popping", "folding",
                     "burst_delay", "fold_delay", "UNROLL_MS", "REVEAL_MS", "EDGE_GLOW"):
            self.assertFalse(hasattr(look, name), name)

    def test_envelope(self):
        samples = [0.0] * 100 + [0.5] * 100 + [1.0] * 100        # 300 samples at 30 Hz: 10 s
        env = look.envelope(samples, 30.0, 30.0, 0, 0, 299, per_frame=1)
        self.assertEqual(len(env), 300)
        self.assertEqual(env[50][1], 0.0)
        self.assertAlmostEqual(env[150][1], 0.5)
        self.assertEqual(env[250][1], 1.0)
        self.assertEqual(look.envelope([], 30, 30, 0, 0, 10), [])


class EdgeTests(unittest.TestCase):

    def test_the_mode_and_an_older_build_s_switch(self):
        self.assertEqual(look.mode_from("edge"), "edge")
        self.assertEqual(look.mode_from(None, 0), "maya")
        self.assertEqual(look.mode_from(None, 1), "docked")
        self.assertEqual(look.mode_from("nonsense"), "edge")
        self.assertEqual(look.mode_from(None), "edge")

    def test_an_update_moves_the_bar_to_the_bottom_edge_once(self):
        self.assertEqual(look.upgraded("docked", 0), "edge")
        self.assertEqual(look.upgraded("edge", 0), "edge")
        self.assertEqual(look.upgraded("maya", 0), "maya")              # Maya's own, chosen: kept
        self.assertEqual(look.upgraded("docked", look.DEFAULT_VERSION), "docked")   # a later choice stands
        self.assertEqual([m for _l, m in look.MODE_LABELS], list(look.MODES))

    def test_the_bands_sit_along_the_window_s_bottom(self):
        self.assertEqual(look.bottom_band((100, 50, 1900, 1000), 126), (100, 924, 1900, 126))
        self.assertEqual(look.sensor_band((100, 50, 1900, 1000), 2), (100, 1048, 1900, 2))
        self.assertEqual(look.bottom_band((0, 0, 800, 60), 126)[3], 60)


class MeterTests(unittest.TestCase):

    def test_a_steady_scrub(self):
        stamps = [i * 20.0 for i in range(100)]                  # a frame every 20 ms
        out, text = look.meter_report(stamps, [1.0] * 99, [12.0] * 99)
        self.assertEqual(out["changes"], 100)
        self.assertAlmostEqual(out["rate"], 50.0)
        self.assertEqual((out["ours"], out["maya"]), (1.0, 12.0))
        self.assertIn("50 a second", text)
        self.assertIn("the Time Bar's own work 1.00 ms", text)

    def test_pauses_are_not_frames_and_maya_s_slider_is_named(self):
        stamps = [0, 20, 40, 3000, 3020, 3040]
        out, text = look.meter_report(stamps)
        self.assertEqual(out["gap_max"], 20.0)
        self.assertIn("Maya's own slider", text)

    def test_nothing_scrubbed(self):
        out, text = look.meter_report([], seconds=10)
        self.assertEqual(out["changes"], 0)
        self.assertIn("no scrubbing", text)


class Purity(unittest.TestCase):

    def test_look_and_the_package_import_with_the_stdlib_alone(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        code = ("import sys; import maya_timebar, maya_timebar.look; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; print(bad); "
                "sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class SetKeyCommandTests(unittest.TestCase):

    def test_maya_s_setkeyframe_commands_are_read(self):
        f = look.set_key_command
        self.assertEqual(f('setKeyframe "-breakdown" 0 "-preserveCurveShape" 0 "-hierarchy" "none";\n'),
                         (None, False))
        self.assertEqual(f('setKeyframe "-at" "ty" "-t" 5 "pCube1";\n'), (5.0, False))
        self.assertEqual(f('setKeyframe -breakdown 1 -time 12.5 pCube1'), (12.5, True))
        self.assertIsNone(f('setKeyframeBlendshapeTargetWts;'))
        self.assertIsNone(f('optionVar "-query" "setKeyframeWhich";'))
        self.assertIsNone(f('currentTime 5;'))


class KeyCellTests(unittest.TestCase):

    def test_a_key_fills_its_cell_with_a_gap_and_an_inset(self):
        l, tp, w, h = look.key_cell(100.0, 20.0, 12.0, 58.0)
        self.assertAlmostEqual(w, (20.0 - 3.0) * look.KEY_WIDTH)
        self.assertAlmostEqual(l + w / 2.0, 110.0)      # centred in its cell
        self.assertAlmostEqual((tp, h), (14.0, 42.0))

    def test_a_key_is_a_fifth_narrower_than_its_cell_leaves_it(self):
        self.assertAlmostEqual(look.KEY_WIDTH, 0.8)
        self.assertAlmostEqual(look.key_cell(0.0, 20.0, 0, 40)[2], 13.6)

    def test_neighbouring_keys_never_touch_on_a_roomy_track(self):
        a = look.key_cell(0.0, 10.0, 0, 40)
        b = look.key_cell(10.0, 10.0, 0, 40)
        self.assertGreater(b[0] - (a[0] + a[2]), 0.9)

    def test_a_thin_cell_is_filled_whole_and_never_thinner_than_1_5(self):
        self.assertAlmostEqual(look.key_cell(0.0, 2.5, 0, 40)[2], 2.5 * look.KEY_WIDTH)
        self.assertAlmostEqual(look.key_cell(0.0, 0.5, 0, 40)[2], 1.5)

    def test_a_key_is_seen_in_its_cell_middle_or_on_its_time(self):
        t = look.Track(0, 9, 0, 100, cells=True)
        self.assertAlmostEqual(look.key_centre(t, 3.0), t.x(3.0) + 5.0)
        self.assertAlmostEqual(look.key_centre(t, 3.5), t.x(3.5))


class FreeSpanTests(unittest.TestCase):
    """2026-10-17: the bar at the bottom edge steps aside for our panels and Maya's
    docked editors. Read live: the window (0, 34, 2560, 1494), the pane (2, 176,
    2556, 1350)."""

    WINDOW = (0, 34, 2560, 1494)

    def test_maya_s_viewport_area_across(self):
        self.assertEqual(look.free_span(self.WINDOW, 117), (0, 2560))
        self.assertEqual(look.free_span(self.WINDOW, 117, (2, 176, 2556, 1350)), (2, 2558))
        self.assertEqual(look.free_span(self.WINDOW, 117, (300, 176, 1800, 1350)), (300, 2100))

    def test_a_panel_on_the_right_cuts_the_end_on_the_left_the_start(self):
        side = (1910, 176, 648, 1350)            # the side panel, down to the bottom
        hub = (0, 34, 540, 1494)                 # the hub's edge panel on the left
        self.assertEqual(look.free_span(self.WINDOW, 117, None, [side]), (0, 1910))
        self.assertEqual(look.free_span(self.WINDOW, 117, None, [side, hub]), (540, 1910))

    def test_a_panel_above_the_band_does_not_count(self):
        self.assertEqual(look.free_span(self.WINDOW, 117, None, [(1910, 176, 648, 1200)]),
                         (0, 2560))

    def test_nothing_left_gives_the_whole_width(self):
        self.assertEqual(look.free_span(self.WINDOW, 117, None, [(0, 34, 2560, 1494)]),
                         (0, 2560))

    def test_the_band_cut_to_the_span(self):
        self.assertEqual(look.band_in(self.WINDOW, 117, (0, 1910)), (0, 1411, 1910, 117))


if __name__ == "__main__":
    unittest.main()


class DragKeys(unittest.TestCase):

    def test_maya_s_set_key_commands_for_a_drag(self):
        self.assertEqual(look.drag_key("s"), "SetKey")
        self.assertEqual(look.drag_key("S"), "SetKey")
        self.assertEqual(look.drag_key("w", shift=True), "SetKeyTranslate")
        self.assertEqual(look.drag_key("e", shift=True), "SetKeyRotate")
        self.assertEqual(look.drag_key("r", shift=True), "SetKeyScale")
        for args in (("w",), ("s", True), ("s", False, True), ("s", False, False, True), ("",), ("x",)):
            self.assertIsNone(look.drag_key(*args), args)

    def test_what_s_does_on_the_strip(self):
        self.assertIsNone(look.key_action(None, None, (1, 5), 3.0))
        drag = ("hmove", 30, None, (22, 40))
        self.assertEqual(look.key_action("SetKey", drag, None, (27, 45)),
                         ("stamp", (22, 40), (27, 45)))          # where the block is dragged to
        self.assertEqual(look.key_action("SetKey", ("h1", 40, None, (22, 40)), None, (22, 50)),
                         ("stamp", (22, 40), (22, 50)))          # an edge drag: scaled
        self.assertIsNone(look.key_action("SetKeyRotate", drag, None, (27, 45)))
        self.assertIsNone(look.key_action("SetKey", ("hl", 3, None), None))
        self.assertEqual(look.key_action("SetKey", ("now", None, None), (1, 5), 3.0), ("run",))
        self.assertEqual(look.key_action("SetKey", None, (4.0, 9.0), 3.0), ("range", 4, 9))
        self.assertIsNone(look.key_action("SetKey", None, (4, 4), 3.0))
        self.assertIsNone(look.key_action("SetKey", None, None, 3.0))

    def test_copies_s_put_down_stay_where_they_went_down_while_the_block_moves(self):
        self.assertIsNone(look.held(None))
        stamped = {"c": {"keys": [(22.0, {}), (30.0, {}), (40.0, {})], "stamped": {27.0, 35.0, 45.0}}}
        carried = look.held(stamped)
        self.assertEqual(carried, (frozenset({22.0, 30.0, 40.0}), frozenset({27.0, 35.0, 45.0})))
        self.assertEqual(look.shown_at(30, (22, 40), (32, 50), carried), [40])     # dragged
        self.assertEqual(look.shown_at(35, (22, 40), (32, 50), carried), [35])     # a copy stays
        self.assertEqual(look.shown_at(35, (22, 40), (32, 50)), [45])              # before any S
        both = look.held({"c": {"keys": [(30.0, {})], "stamped": {30.0}}})
        self.assertEqual(sorted(look.shown_at(30, (30, 30), (34, 34), both)), [30, 34])


class AllKeysTests(unittest.TestCase):
    """A right double click highlights every key (2026-10-19)."""

    def test_first_to_last_breakdowns_included(self):
        self.assertEqual(look.all_keys([6.0, 30.0, 12.0], [2.0, 41.0]), (2, 41))

    def test_a_key_between_frames_counts_in_its_cell(self):
        self.assertEqual(look.all_keys([4.5, 19.5, 7.9999999], []), (4, 19))
        self.assertEqual(look.all_keys([-3.5], []), (-4, -4))

    def test_none_without_keys(self):
        self.assertIsNone(look.all_keys([], []))

    def test_the_double_window(self):
        self.assertFalse(look.right_double(None, 1000.0, 300))
        self.assertTrue(look.right_double(1000.0, 1250.0, 300))
        self.assertFalse(look.right_double(1000.0, 1301.0, 300))


class SpanLabelTests(unittest.TestCase):
    """A highlight's frame labels (2026-10-20)."""

    def test_inside_the_block_when_both_fit(self):
        a, b = look.span_labels(100, 300, 20, 24, 1000)
        self.assertEqual((a, b), (103, 273))

    def test_outside_the_edges_when_the_block_is_narrow(self):
        a, b = look.span_labels(100, 130, 20, 24, 1000)
        self.assertEqual((a, b), (77, 133))

    def test_kept_on_the_track_and_apart(self):
        a, b = look.span_labels(0, 10, 20, 24, 1000)
        self.assertEqual(a, 0.0)
        self.assertGreaterEqual(b, a + 20 + look.SPAN_GAP)
        a, b = look.span_labels(990, 1000, 20, 24, 1000)
        self.assertEqual(b + 24, 1000)
        self.assertLessEqual(a + 20 + look.SPAN_GAP, b)

    def test_one_frame_shows_one_label_centred(self):
        a, b = look.span_labels(100, 110, 20, 20, 1000, single=True)
        self.assertEqual((a, b), (95, None))


class IngotTests(unittest.TestCase):
    """Steel keys as ingots (2026-10-20, the mockup's «фаска»)."""

    def test_the_face_is_lit_at_the_top_and_shaded_at_the_bottom(self):
        top, mid, bottom = look.ingot_shades(look.STEEL)
        self.assertEqual(mid, look.STEEL)
        self.assertGreater(sum(look._rgb(top)), sum(look._rgb(mid)))
        self.assertLess(sum(look._rgb(bottom)), sum(look._rgb(mid)))

    def test_steel_is_darker_than_the_flat_key_was(self):
        self.assertLess(sum(look._rgb(look.STEEL)), sum(look._rgb("#b8c0ca")))

    def test_the_side_faces_stay_between_three_quarters_and_two_px(self):
        self.assertEqual(look.ingot_side(1.0), 0.75)
        self.assertEqual(look.ingot_side(100.0), 2.0)
        self.assertAlmostEqual(look.ingot_side(10.0), 1.4)


class SteelDefaultTests(unittest.TestCase):
    def test_steel_keys_are_the_default(self):
        # 2026-10-20: «стальные ключи сделаем ключами по умолчанию»
        self.assertTrue(look.STEEL_DEFAULT)

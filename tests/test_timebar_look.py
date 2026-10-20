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

    def test_the_playhead_lights_the_keys_in_its_cell(self):
        self.assertEqual(look.passed([6.0, 6.47, 7.0], 30.0, 6.0), [6.0, 6.47])

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

    def test_passed_keys(self):
        keys = [0, 6, 12, 30]
        self.assertEqual(look.passed(keys, 10, 13), [12])
        self.assertEqual(look.passed(keys, 12, 13), [])                # leaving a key lights nothing
        self.assertEqual(look.passed(keys, 13, 10), [12])              # backwards too
        self.assertEqual(look.passed(keys, 60, 0), [0])                # the loop's jump: the landing only
        self.assertEqual(look.passed(keys, None, 6), [])

    def test_the_motion_curves(self):
        self.assertEqual(look.flash(0, 600), 1.0)
        self.assertEqual(look.flash(600, 600), 0.0)
        self.assertGreater(look.flash(100, 600), look.flash(300, 600))
        self.assertEqual(look.approach(0.0, 1.0, 1000, 110), 1.0)
        self.assertLess(look.approach(0.0, 1.0, 16, 110), 1.0)
        self.assertGreater(max(look.back_out(u / 20.0) for u in range(21)), 1.0)   # it overshoots
        self.assertEqual(look.back_out(1.0), 1.0)
        self.assertEqual(look.opening(0, 3), (0.3, 0.0))
        self.assertEqual(look.opening(10000, 3), (1.0, 1.0))

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

    def test_the_slide(self):
        self.assertEqual(look.slide(0, 120, True, 180), 120)
        self.assertEqual(look.slide(180, 120, True, 180), 0)
        self.assertLess(look.slide(60, 120, True, 180), 60)          # eases out: most of the way early
        self.assertEqual(look.slide(0, 120, False, 140), 0)
        self.assertEqual(look.slide(140, 120, False, 140), 120)
        self.assertEqual(look.slide(5, 120, True, 0), 0)


class BurstTests(unittest.TestCase):

    def test_the_mockup_s_timings_1_2_times_longer(self):
        self.assertEqual((look.UNROLL_MS, look.POP_OPEN_MS, look.FOLD_MS, look.CLOSE_MS), (288, 240, 168, 216))

    def test_nearer_pops_sooner_and_farther_folds_sooner(self):
        self.assertLess(look.burst_delay(10, 0), look.burst_delay(600, 0))
        self.assertLess(look.burst_delay(0, 0), look.burst_delay(0, 40))       # a row down counts more
        self.assertEqual(look.burst_delay(0, 0), 48.0)
        self.assertEqual(look.burst_delay(120, 0, ui=2.0), look.burst_delay(60, 0))
        self.assertGreater(look.fold_delay(10), look.fold_delay(600))
        self.assertEqual(look.fold_delay(5000), 0.0)

    def test_pop_and_fold(self):
        self.assertEqual(look.popping(0, 50), (look.START_SCALE, 0.0))
        self.assertEqual(look.popping(50 + look.POP_OPEN_MS, 50), (1.0, 1.0))
        self.assertGreater(max(look.popping(50 + look.POP_OPEN_MS * u / 20.0, 50)[0] for u in range(21)), 1.0)
        self.assertEqual(look.folding(0, 50), (1.0, 1.0))
        self.assertEqual(look.folding(50 + look.FOLD_MS, 50), (look.START_SCALE, 0.0))
        self.assertGreater(look.folding(50 + look.FOLD_MS * 0.1, 50)[0], 1.0)  # draws back first

    def test_unroll_from_and_onto_the_cursor(self):
        self.assertEqual(look.unroll(0, 300, 1000, True), (300.0, 300.0))
        self.assertEqual(look.unroll(1, 300, 1000, True), (0.0, 1000.0))
        x0, x1 = look.unroll(0.5, 300, 1000, True)
        self.assertTrue(0 < x0 < 300 < x1 < 1000)
        self.assertEqual(look.unroll(1, 300, 1000, False), (300.0, 300.0))
        self.assertEqual(look.unroll(0, 300, 1000, False), (0.0, 1000.0))


class RevealGlowTests(unittest.TestCase):
    """The racing edges of the reveal (2026-10-17, mockup B of five)."""

    def test_the_mockup_s_numbers(self):
        self.assertEqual((look.REVEAL_MS, look.EDGE_GLOW, look.EDGE_CORE, look.TOP_GLOW), (780, 24, 3, 16))
        self.assertEqual(look.EFFECT_MS["reveal"], look.REVEAL_MS)

    def test_both_edges_start_on_the_cursor_at_full_light(self):
        x0, x1, edges, edge, top = look.reveal_glow(0, 300, 1000)
        self.assertEqual((x0, x1), (300.0, 300.0))
        self.assertEqual(edges, [300.0, 300.0])
        self.assertEqual((edge, top), (1.0, 1.0))

    def test_the_edges_ride_the_unroll_and_fade_as_they_slow(self):
        mid = look.UNROLL_MS * 0.3
        x0, x1, edges, edge, top = look.reveal_glow(mid, 300, 1000)
        u0, u1 = look.unroll(0.3, 300, 1000, True)
        self.assertAlmostEqual(x0, u0, places=6)
        self.assertAlmostEqual(x1, u1, places=6)
        self.assertEqual(edges, [x0, x1])
        self.assertTrue(0.0 < edge < 1.0)
        self.assertTrue(0.0 < top < 1.0)
        later = look.reveal_glow(look.UNROLL_MS * 0.6, 300, 1000)
        self.assertLess(later[3], edge)
        self.assertLess(later[4], top)

    def test_an_edge_at_the_window_s_end_carries_nothing(self):
        x0, x1, edges, edge, _top = look.reveal_glow(look.UNROLL_MS, 300, 1000)
        self.assertEqual((x0, x1), (0.0, 1000.0))
        self.assertEqual(edges, [])
        self.assertEqual(edge, 0.0)
        _x0, _x1, edges, _e, _t = look.reveal_glow(look.UNROLL_MS * 0.4, 0, 1000)
        self.assertEqual(len(edges), 1)                 # from the left end: one edge races

    def test_the_top_edge_stays_lit_after_the_unroll_and_is_gone_at_the_end(self):
        top = look.reveal_glow(look.UNROLL_MS + 100, 300, 1000)[4]
        self.assertGreater(top, 0.0)
        self.assertEqual(look.reveal_glow(look.REVEAL_MS, 300, 1000)[4], 0.0)
        self.assertEqual(look.reveal_glow(look.REVEAL_MS + 50, 300, 1000)[4], 0.0)


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


class KeyEffectTests(unittest.TestCase):

    def test_key_changes_reads_sets_deletes_and_snaps(self):
        self.assertEqual(look.key_changes([1.0, 2.0], [1.0, 2.0, 5.0]), ([5.0], [], []))
        self.assertEqual(look.key_changes([1.0, 2.0], [1.0]), ([], [2.0], []))
        self.assertEqual(look.key_changes([1.0, 2.5], [1.0, 3.0]), ([], [], [(2.5, 3.0)]))
        self.assertEqual(look.key_changes(None, [1.0]), ([], [], []))
        self.assertEqual(look.key_changes([], list(map(float, range(20)))), ([], [], []))

    def test_sparks_are_a_formula_of_their_age_and_fall(self):  # the old delete effect, kept
        a = look.sparks(3, 24, 500, 600, 170, 620)
        self.assertEqual(a, look.sparks(3, 24, 500, 600, 170, 620))
        self.assertEqual(len(a), 24)
        self.assertGreater(sum(dy for _dx, dy, _l in a) / len(a), 0)
        self.assertEqual(look.sparks(3, 24, 600, 600, 170, 620), [])

    def test_progress(self):
        self.assertIsNone(look.progress(-1, "set"))
        self.assertAlmostEqual(look.progress(260, "set"), 0.5)
        self.assertIsNone(look.progress(look.EFFECT_MS["delete"], "delete"))


class DeleteWaveTests(unittest.TestCase):
    """Keys deleted together break one after another left to right, the wave within
    600 ms (2026-10-17: 300, then «замедлить в двое»)."""

    def test_an_edited_pure_deletion_of_many_keys_is_read(self):
        old = list(map(float, range(1000)))
        self.assertEqual(look.key_changes(old, [], edited=True), ([], old, []))
        self.assertEqual(look.key_changes(old, []), ([], [], []))      # a selection change: a reload
        self.assertEqual(look.key_changes(old, [5000.0], edited=True), ([], [], []))

    def test_one_key_plays_its_whole_effect(self):
        self.assertEqual(look.delete_plan(1), ([0.0], look.EFFECT_MS["delete"]))

    def test_a_few_keys_follow_each_other(self):
        delays, life = look.delete_plan(3)
        self.assertEqual(delays, [0, look.DELETE_STEP_MS, 2 * look.DELETE_STEP_MS])
        self.assertEqual(life, look.EFFECT_MS["delete"])

    def test_every_key_flies_whole_and_the_last_starts_within_half_a_second(self):
        self.assertEqual(look.DELETE_START_MS, 500)
        for n in (2, 7, 13, 50, 1000, 10000):
            delays, life = look.delete_plan(n)
            self.assertEqual(len(delays), n)
            self.assertEqual(delays, sorted(delays))
            self.assertEqual(life, look.EFFECT_MS["delete"])        # the flight of a single key
            self.assertLessEqual(delays[-1], look.DELETE_START_MS + 1e-6)
        self.assertEqual(look.delete_plan(7)[0][1], look.DELETE_STEP_MS)   # a few: one step apart

    def test_a_key_always_breaks_into_three_cubes_stacked_down_it(self):
        # 2026-10-18: «из 3 кубиков (всегда кубики разлетаются)»
        cuts = look.shard_cuts(42.0)
        self.assertEqual(cuts, [(0.0, 14.0), (14.0, 28.0), (28.0, 42.0)])
        for rect in ((100.0, 20.0, 12.0, 42.0), (100.0, 20.0, 2.0, 42.0), (100.0, 20.0, 60.0, 42.0)):
            for seed in range(1, 60):
                start = look.shards(seed, rect, 0, 700, 260, 900)
                self.assertEqual(len(start), 3)
                for (cx, cy, w, h, angle, alpha), (a, b) in zip(start, cuts):
                    self.assertAlmostEqual(cx, rect[0] + rect[2] / 2.0)   # down the key's middle
                    self.assertAlmostEqual(cy, 20.0 + (a + b) / 2.0)
                    self.assertEqual((w, h, angle, alpha), (14.0, 14.0, 0.0, 1.0))   # a square
                for age in (100, 400, 650):
                    for _cx, _cy, w, h, _a, _al in look.shards(seed, rect, age, 700, 260, 900):
                        self.assertEqual(w, h)

    def test_the_pieces_fly_apart_fall_and_fade(self):
        rect = (100.0, 20.0, 12.0, 40.0)
        late = look.shards(7, rect, 600, 700, 260, 900)
        xs = [p[0] for p in late]
        self.assertTrue(min(xs) < 106.0 < max(xs))      # some go left, some right
        self.assertTrue(all(p[5] < 0.5 for p in late))
        self.assertEqual(look.shards(7, rect, 700, 700, 260, 900), [])
        self.assertEqual(look.shards(7, rect, 300, 700, 260, 900),
                         look.shards(7, rect, 300, 700, 260, 900))


class ShardFlightTests(unittest.TestCase):

    def test_the_flight_is_shorter(self):
        # variant B of the six played side by side (2026-10-17)
        self.assertEqual((look.SHARD_SPEED, look.SHARD_FALL, look.SHARD_SPIN), (170.0, 900.0, 420.0))
        self.assertEqual(look.EFFECT_MS["delete"], 700)
        rect = (100.0, 30.0, 12.0, 44.0)
        far = 0.0
        for seed in range(1, 40):
            for age in range(0, 700, 20):
                for cx, cy, _w, _h, _a, _al in look.shards(seed, rect, age, 700, look.SHARD_SPEED,
                                                            look.SHARD_FALL):
                    far = max(far, abs(cx - 106.0))
        self.assertLess(far, 130.0)                     # shorter than the first flight's


class ShardGroupTests(unittest.TestCase):

    def test_each_key_alone_until_the_budget_then_runs_of_neighbours(self):
        self.assertEqual(look.shard_groups(0), [])
        self.assertEqual(look.shard_groups(5), [(i, i + 1) for i in range(5)])
        many = look.shard_groups(1000)
        self.assertEqual(many[0][0], 0)
        self.assertEqual(many[-1][1], 1000)
        for (a, b), (c, _d) in zip(many, many[1:]):
            self.assertEqual(b, c)                      # every key in exactly one run
        self.assertLessEqual(len(many) * look.SHARDS[0], look.SHARD_BUDGET + look.SHARDS[0])


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

    def test_the_glow_grows_with_heat_and_a_little_with_a_lift(self):
        self.assertEqual(look.steel_glow(0.0, 0.0), 0.0)
        self.assertAlmostEqual(look.steel_glow(1.0, 0.0), look.STEEL_GLOW)
        self.assertAlmostEqual(look.steel_glow(0.0, 1.0), look.STEEL_GLOW * look.STEEL_GLOW_LIFT)
        self.assertAlmostEqual(look.steel_glow(1.0, 1.0), look.STEEL_GLOW)


class CoolingTests(unittest.TestCase):
    """Steel keys (2026-10-20): a key set glows hot and cools into steel."""

    def test_white_hot_then_cherry_red_then_steel(self):
        hot, heat = look.cooling(0)
        self.assertEqual((hot, heat), (look.HEAT[0][1], 1.0))
        red, _ = look.cooling(look.COOL_MS * 0.45)
        r, g, b = look._rgb(red)
        self.assertGreater(r, g + 100)
        self.assertEqual(look.cooling(look.COOL_MS), (look.STEEL, 0.0))
        self.assertEqual(look.cooling(look.COOL_MS * 3)[0], look.STEEL)

    def test_the_heat_only_falls_and_is_gone_before_the_end(self):
        heats = [look.cooling(t)[1] for t in range(0, look.COOL_MS + 1, 30)]
        self.assertEqual(heats, sorted(heats, reverse=True))
        self.assertEqual(look.cooling(look.COOL_MS * 0.75)[1], 0.0)

    def test_a_handful_of_colours_so_each_glow_is_cached_once(self):
        colours = {look.cooling(t)[0] for t in range(0, look.COOL_MS + 1)}
        self.assertLessEqual(len(colours), look.COOL_STEPS + 1)

    def test_the_last_stop_is_the_steel_asked_for(self):
        self.assertEqual(look.cooling(look.COOL_MS, steel="#808080")[0], "#808080")


class SpreadTests(unittest.TestCase):
    """Many keys set at once: the round flash on a few of them, spread along."""

    def test_all_when_few_else_spread_with_both_ends(self):
        self.assertEqual(look.spread(5, 8), [0, 1, 2, 3, 4])
        got = look.spread(200, 8)
        self.assertEqual(len(got), 8)
        self.assertEqual((got[0], got[-1]), (0, 199))
        self.assertEqual(got, sorted(got))
        self.assertEqual(look.spread(3, 1), [0])


class SteelDefaultTests(unittest.TestCase):
    def test_steel_keys_are_the_default(self):
        # 2026-10-20: «стальные ключи сделаем ключами по умолчанию»
        self.assertTrue(look.STEEL_DEFAULT)

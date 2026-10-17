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

    def test_a_key_breaks_into_three_to_five_pieces_that_are_the_key(self):
        rect = (100.0, 20.0, 12.0, 40.0)
        counts = set()
        for seed in range(1, 60):
            cuts = look.shard_cuts(seed, 40.0)
            counts.add(len(cuts))
            self.assertAlmostEqual(cuts[0][0], 0.0)
            self.assertAlmostEqual(cuts[-1][1], 40.0)
            for (a, b), (c, _d) in zip(cuts, cuts[1:]):
                self.assertAlmostEqual(b, c)            # no gap, no overlap
            start = look.shards(seed, rect, 0, 700, 260, 900)
            self.assertEqual(len(start), len(cuts))
            for (cx, cy, w, h, angle, alpha), (a, b) in zip(start, cuts):
                self.assertAlmostEqual(cx, 106.0)       # at age 0 each piece sits in the key
                self.assertAlmostEqual(cy, 20.0 + (a + b) / 2.0)
                self.assertEqual((w, angle, alpha), (12.0, 0.0, 1.0))
                self.assertAlmostEqual(h, b - a)
        self.assertEqual(counts, {3, 4, 5})

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

    def test_the_flight_is_snap_and_drop(self):
        # variant D of the six played side by side (2026-10-17)
        self.assertEqual((look.SHARD_SPEED, look.SHARD_FALL, look.SHARD_SPIN), (143.0, 1600.0, 300.0))
        self.assertEqual(look.EFFECT_MS["delete"], 600)
        rect = (100.0, 30.0, 12.0, 44.0)
        far = 0.0
        for seed in range(1, 40):
            for age in range(0, 600, 20):
                for cx, cy, _w, _h, _a, _al in look.shards(seed, rect, age, 600, look.SHARD_SPEED,
                                                            look.SHARD_FALL):
                    far = max(far, abs(cx - 106.0))
        self.assertLess(far, 90.0)                      # a short kick: pieces stay near the key


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
        self.assertAlmostEqual(w, 20.0 - 3.0)
        self.assertAlmostEqual(l, 101.5)
        self.assertAlmostEqual((tp, h), (14.0, 42.0))

    def test_neighbouring_keys_never_touch_on_a_roomy_track(self):
        a = look.key_cell(0.0, 10.0, 0, 40)
        b = look.key_cell(10.0, 10.0, 0, 40)
        self.assertGreater(b[0] - (a[0] + a[2]), 0.9)

    def test_a_thin_cell_is_filled_whole_and_never_thinner_than_1_5(self):
        self.assertAlmostEqual(look.key_cell(0.0, 2.5, 0, 40)[2], 2.5)
        self.assertAlmostEqual(look.key_cell(0.0, 0.5, 0, 40)[2], 1.5)

    def test_a_key_is_seen_in_its_cell_middle_or_on_its_time(self):
        t = look.Track(0, 9, 0, 100, cells=True)
        self.assertAlmostEqual(look.key_centre(t, 3.0), t.x(3.0) + 5.0)
        self.assertAlmostEqual(look.key_centre(t, 3.5), t.x(3.5))

if __name__ == "__main__":
    unittest.main()

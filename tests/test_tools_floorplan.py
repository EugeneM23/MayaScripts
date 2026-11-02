"""Tools > Floor: the pure half - which frames are contacts, how far the body must move, and which of
those frames are worth a key (docs/superpowers/specs/2026-11-02-tools-floor-design.md). No Maya."""

import math
import os
import subprocess
import sys
import unittest

from maya_tools import floorplan as fp

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def heights(rows):
    """{side: {frame: how far above the floor}} from a list of (frame, left, right)."""
    out = {"l": {}, "r": {}}
    for f, left, right in rows:
        out["l"][f] = left
        out["r"][f] = right
    return out


class ContactTests(unittest.TestCase):
    """down_frames: a foot is down within DOWN_TOL of its own lowest, never of the floor."""

    def test_a_still_foot_on_the_floor_is_down(self):
        low = heights([(0, 0.0, 20.0), (1, 0.0, 18.0), (2, 0.1, 9.0)])
        self.assertEqual(fp.down_frames(low["l"]), [0, 1, 2])
        self.assertEqual(fp.down_frames(low["r"]), [2])

    def test_a_character_fifteen_centimetres_up_still_has_contacts(self):
        """The take this tool is for: nothing is near y = 0, and the stance is still the stance."""
        low = dict((f, 15.0 + h) for f, h in ((0, 0.0), (1, 0.2), (2, 8.0), (3, 20.0), (4, 0.4)))
        self.assertEqual(fp.down_frames(low), [0, 1, 4])

    def test_a_foot_never_within_the_tolerance_of_its_own_lowest_is_down_at_its_lowest(self):
        low = {0: 40.0, 1: 10.0, 2: 41.0}
        self.assertEqual(fp.down_frames(low), [1])

    def test_nothing_measured_is_no_contact(self):
        self.assertEqual(fp.down_frames({}), [])


class WantedTests(unittest.TestCase):
    """wanted: minus the LOWER foot, frame by frame, and nothing where both feet are in the air."""

    def test_the_body_rises_by_what_the_lowest_foot_floats(self):
        low = heights([(0, 2.0, 30.0), (1, 2.5, 28.0)])
        want = fp.wanted(low)
        self.assertAlmostEqual(want[0], -2.0, places=9)
        self.assertAlmostEqual(want[1], -2.5, places=9)

    def test_the_body_sinks_by_what_the_deepest_foot_is_under(self):
        low = heights([(0, -6.0, 20.0)])
        self.assertAlmostEqual(fp.wanted(low)[0], 6.0, places=9)

    def test_a_double_support_is_decided_by_the_lower_foot(self):
        """One offset cannot put two feet at two heights: the lower decides, the other stays above."""
        low = heights([(0, 2.0, -1.0)])
        self.assertAlmostEqual(fp.wanted(low)[0], 1.0, places=9)

    def test_a_flight_is_skipped(self):
        low = {}
        for f in range(0, 6):
            low[f] = (0.0, 0.0)
        for f in range(6, 10):
            low[f] = (22.0, 25.0)              # both feet a swing's height up
        for f in range(10, 16):
            low[f] = (0.0, 0.0)
        rows = heights([(f, a, b) for f, (a, b) in low.items()])
        skip = fp.airborne(rows)
        want = fp.wanted(rows, skip)
        self.assertEqual(skip, [6, 7, 8, 9])    # the whole flight, and nothing beside it
        for f in (7, 8):
            self.assertNotIn(f, want)
        self.assertIn(0, want)
        self.assertIn(15, want)

    def test_a_planted_foot_a_few_centimetres_off_its_own_low_still_carries_the_body(self):
        """The sunk-stance case, measured 2026-11-02: inside one stance the body dips 6 cm, the foot
        goes with it, and the clean half must stay a contact - or the whole take is carried down."""
        rows = {"l": {}, "r": {}}
        for f in range(0, 13):
            rows["l"][f] = 0.0
            rows["r"][f] = 0.0
        for f in range(13, 16):
            rows["l"][f] = 0.0
            rows["r"][f] = 12.0
        for f in range(16, 21):
            rows["l"][f] = -6.0
            rows["r"][f] = -2.7
        for f in range(21, 25):
            rows["l"][f] = 0.0
            rows["r"][f] = 1.0
        want = fp.wanted(rows, fp.airborne(rows))
        self.assertAlmostEqual(want[18], 6.0, places=9)      # the sunk half raised
        self.assertAlmostEqual(want[23], 0.0, places=9)      # the clean half left alone
        self.assertAlmostEqual(want[5], 0.0, places=9)


class KeyTests(unittest.TestCase):
    """keys_for: every frame a foot is down, thinned to what the curve needs."""

    def test_a_still_contact_costs_two_keys(self):
        want = dict((f, 3.0) for f in range(10))
        self.assertEqual(fp.keys_for(want), [0, 9])

    def test_a_sinking_contact_keeps_the_frames_that_bend_it(self):
        want = {0: 0.0, 1: 1.0, 2: 2.0, 3: 6.0, 4: 6.0}
        self.assertEqual(fp.keys_for(want), [0, 2, 3, 4])

    def test_a_straight_ramp_costs_its_ends(self):
        want = dict((f, 0.5 * f) for f in range(8))
        self.assertEqual(fp.keys_for(want), [0, 7])

    def test_two_contacts_apart_each_keep_their_ends(self):
        want = {0: 1.0, 1: 1.0, 8: 4.0, 9: 4.0}
        self.assertEqual(fp.keys_for(want), [0, 1, 8, 9])

    def test_one_frame_and_nothing(self):
        self.assertEqual(fp.keys_for({5: 2.0}), [5])
        self.assertEqual(fp.keys_for({}), [])


class RefusalTests(unittest.TestCase):
    """What the press refuses, and the words it refuses with."""

    def test_no_contact_at_all(self):
        self.assertIn("nothing to stand the body on", fp.refusal({}, 0, 40))

    def test_the_feet_are_already_on_the_floor(self):
        want = {0: 0.05, 1: -0.1, 2: 0.0}
        text = fp.refusal(want, 0, 40)
        self.assertIn("already on the floor", text)
        self.assertIn("nothing changed", text)

    def test_a_real_offset_is_no_refusal(self):
        self.assertIsNone(fp.refusal({0: 2.0, 1: 2.1}, 0, 40))

    def test_the_line_says_which_way_the_body_went_and_how_many_keys(self):
        text = fp.line("Manny_Skeleton", "root", {0: -2.1, 1: 0.4}, [0, 1], {"l": [0], "r": [1]})
        self.assertIn("Manny_Skeleton", text)
        self.assertIn("root", text)
        self.assertIn("2 keys", text)
        self.assertIn("2.1", text)      # the body raised
        self.assertIn("0.4", text)      # ...and lowered


class TrackTests(unittest.TestCase):
    """tracks_for: the local channels one centimetre of world rise really costs."""

    def test_a_rig_main_takes_one_curve(self):
        want = {0: 2.0, 4: 3.0}
        tracks = fp.tracks_for(want, [0, 4], {0: (0.0, 1.0, 0.0), 4: (0.0, 1.0, 0.0)})
        self.assertEqual(sorted(tracks), ["ty"])
        self.assertEqual(tracks["ty"][0], [0, 4])
        self.assertAlmostEqual(tracks["ty"][1][1], 3.0, places=9)

    def test_a_root_under_a_turned_wrapper_takes_the_channel_that_carries_it(self):
        """The Creep's root hangs under a -90 X Armature: world up is the root's own +Z."""
        tracks = fp.tracks_for({0: 2.0}, [0], {0: (0.0, 0.0, 1.0)})
        self.assertEqual(sorted(tracks), ["tz"])
        self.assertAlmostEqual(tracks["tz"][1][0], 2.0, places=9)

    def test_a_scaled_parent_costs_more_or_less_local(self):
        tracks = fp.tracks_for({0: 2.0}, [0], {0: (0.0, 0.5, 0.0)})
        self.assertAlmostEqual(tracks["ty"][1][0], 1.0, places=9)

    def test_a_frame_with_no_axis_read_costs_nothing(self):
        self.assertEqual(fp.tracks_for({0: 2.0}, [0], {}), {})

    def test_nothing_to_write_is_no_track(self):
        self.assertEqual(fp.tracks_for({0: 0.0}, [0], {0: (0.0, 1.0, 0.0)}), {})


class LocalContactTests(unittest.TestCase):
    """down_frames is the LINE's reading - which frames a foot stands near its own nearby low. It is
    local, and it is deliberately NOT what `wanted` asks: a frame beside a sunk stance reads as air by
    this measure while the foot is just as planted (`WantedTests`)."""

    def test_the_stances_read_down_and_the_swing_does_not(self):
        low = {}
        for f in range(0, 13):
            low[f] = 0.0                     # a stance
        for f in range(13, 19):
            low[f] = 14.0                    # a swing
        for f in range(19, 25):
            low[f] = 0.0                     # a stance again
        down = fp.down_frames(low)
        self.assertIn(0, down)
        self.assertIn(12, down)
        self.assertIn(24, down)
        self.assertNotIn(15, down)

    def test_the_window_decides_what_nearby_means(self):
        low = dict((f, 0.0) for f in range(0, 40))
        low[20] = -9.0
        down = fp.down_frames(low, window=3)
        self.assertIn(0, down)
        self.assertIn(20, down)
        self.assertNotIn(19, down)           # 9 cm above its own lowest, three frames away


class BoundTests(unittest.TestCase):
    """keys_for keeps its promise: no frame is further than KEY_TOL from the curve its keys draw."""

    def _worst(self, want, keys):
        worst = 0.0
        for f in sorted(want):
            before = [k for k in keys if k <= f]
            after = [k for k in keys if k >= f]
            if not before or not after:
                continue
            a, b = before[-1], after[0]
            span = float(b - a)
            line = want[a] + (want[b] - want[a]) * (f - a) / span if span else want[a]
            worst = max(worst, abs(want[f] - line))
        return worst

    def test_a_spike_inside_a_flat_run_is_kept(self):
        want = dict((f, 0.0) for f in range(0, 20))
        want[7] = 0.07
        keys = fp.keys_for(want)
        self.assertIn(7, keys)
        self.assertLessEqual(self._worst(want, keys), fp.KEY_TOL + 1e-12)

    def test_a_wavy_contact_stays_within_the_tolerance(self):
        want = dict((f, 0.4 * math.sin(f * 0.7) + 0.03 * math.cos(f * 2.1)) for f in range(0, 40))
        keys = fp.keys_for(want)
        self.assertLessEqual(self._worst(want, keys), fp.KEY_TOL + 1e-12)
        self.assertLess(len(keys), 40)


class Purity(unittest.TestCase):
    """The pure half carries no Maya: a verify, a probe or a test may read it anywhere."""

    def test_no_maya_is_imported(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_tools.floorplan; "
                "print(sorted(m for m in sys.modules if m == 'maya' or m.startswith('maya.')))"
                % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN)
        self.assertEqual(out.decode().strip().splitlines()[-1], "[]")

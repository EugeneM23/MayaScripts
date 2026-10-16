"""The radial menu's pure half (2026-10-15)."""

import subprocess
import sys
import os
import unittest

import maya_radial_rules as rules


class SlotTests(unittest.TestCase):
    def test_eight_slots_clockwise_from_north(self):
        cases = [((0, -50), 0), ((50, -50), 1), ((50, 0), 2), ((50, 50), 3),
                 ((0, 50), 4), ((-50, 50), 5), ((-50, 0), 6), ((-50, -50), 7)]
        for (dx, dy), slot in cases:
            self.assertEqual(rules.slot_at(dx, dy), slot, (dx, dy))

    def test_dead_zone(self):
        self.assertIsNone(rules.slot_at(5, -5))
        self.assertIsNone(rules.slot_at(0, 0))

    def test_boundaries_round_to_nearest(self):
        self.assertEqual(rules.slot_at(10, -100), 0)     # 6 deg east of north
        self.assertEqual(rules.slot_at(-10, -100), 0)    # 6 deg west
        self.assertEqual(rules.slot_at(100, -30), 2)     # 73 deg -> east

    def test_position_matches_slot(self):
        for i in range(rules.SLOTS):
            dx, dy = rules.slot_position(i)
            self.assertEqual(rules.slot_at(dx, dy), i)


class CountTests(unittest.TestCase):
    def test_default_count_is_eight(self):
        self.assertEqual(rules.SLOTS, 8)
        self.assertEqual(rules.clamp_count(None), 8)
        self.assertEqual(rules.clamp_count("x"), 8)
        self.assertEqual(rules.clamp_count(0), 8)

    def test_count_clamped(self):
        self.assertEqual(rules.clamp_count(1), rules.MIN_SLOTS)
        self.assertEqual(rules.clamp_count(40), rules.MAX_SLOTS)
        self.assertEqual(rules.clamp_count("6"), 6)

    def test_every_count_finds_its_own_slots(self):
        for n in range(rules.MIN_SLOTS, rules.MAX_SLOTS + 1):
            for i in range(n):
                dx, dy = rules.slot_position(i, 100.0, n)
                self.assertEqual(rules.slot_at(dx, dy, count=n), i, (n, i))

    def test_four_slots_are_the_cross(self):
        self.assertEqual(rules.slot_at(0, -50, count=4), 0)
        self.assertEqual(rules.slot_at(50, 0, count=4), 1)
        self.assertEqual(rules.slot_at(0, 50, count=4), 2)
        self.assertEqual(rules.slot_at(-50, 0, count=4), 3)
        self.assertEqual(rules.slot_at(50, -40, count=4), 1)     # 51 deg -> east

    def test_ring_widens_past_eight(self):
        self.assertEqual(rules.ring_radius(4), rules.RADIUS)
        self.assertEqual(rules.ring_radius(8), rules.RADIUS)
        self.assertAlmostEqual(rules.ring_radius(12), rules.RADIUS * 1.5)

    def test_directions(self):
        self.assertEqual([rules.direction(i, 8) for i in range(8)], list(rules.COMPASS))
        self.assertEqual([rules.direction(i, 4) for i in range(4)], ["N", "E", "S", "W"])
        self.assertEqual(rules.direction(1, 12), "30 deg")
        self.assertEqual(rules.direction(3, 12), "E")

    def test_a_smaller_count_keeps_the_items_past_it(self):
        items = tuple("cmd:r{0}".format(i) for i in range(rules.MAX_SLOTS))
        self.assertEqual(rules.decode(rules.encode(items)), items)


class AnchorTests(unittest.TestCase):
    def test_labels_grow_outward(self):
        self.assertEqual([rules.pill_anchor(i) for i in range(8)],
                         [0.5, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0])


class ItemTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(rules.parse("section:tools"), ("section", "tools"))
        self.assertEqual(rules.parse("cmd:tools.aim"), ("cmd", "tools.aim"))
        self.assertEqual(rules.parse(""), (None, None))
        self.assertEqual(rules.parse("cmd:"), (None, None))
        self.assertEqual(rules.parse("junk"), (None, None))
        self.assertEqual(rules.parse(None), (None, None))

    def test_round_trip(self):
        slots = ("section:tools", "", "cmd:tools.aim") + ("",) * (rules.MAX_SLOTS - 3)
        self.assertEqual(rules.decode(rules.encode(slots)), slots)

    def test_short_and_junk_normalised(self):
        self.assertEqual(rules.decode('["cmd:a", 3, "bad"]'),
                         ("cmd:a",) + ("",) * (rules.MAX_SLOTS - 1))
        self.assertEqual(len(rules.decode('["cmd:a"]')), rules.MAX_SLOTS)

    def test_broken_text_gives_defaults(self):
        for text in ("", None, "{", "{}", "7"):
            self.assertEqual(rules.decode(text)[:rules.SLOTS], rules.DEFAULTS)

    def test_defaults_are_eight_valid_items(self):
        self.assertEqual(len(rules.DEFAULTS), rules.SLOTS)
        for item in rules.DEFAULTS:
            self.assertIsNotNone(rules.parse(item)[0], item)


class ReleaseTests(unittest.TestCase):
    def test_slot_runs(self):
        self.assertEqual(rules.release_action(3, True, 2.0), rules.RUN)

    def test_empty_slot_closes(self):
        self.assertEqual(rules.release_action(3, False, 0.1), rules.CLOSE)

    def test_tap_keeps(self):
        self.assertEqual(rules.release_action(None, False, 0.1), rules.KEEP)

    def test_held_in_centre_closes(self):
        self.assertEqual(rules.release_action(None, False, 1.0), rules.CLOSE)


class DefaultsKnownTests(unittest.TestCase):
    def test_defaults_name_real_sections_and_rows(self):
        try:
            import maya.cmds  # noqa: F401
        except ImportError:
            self.skipTest("needs maya.cmds")
        import maya_hub
        import maya_hotkeys
        for item in rules.DEFAULTS + tuple(rules.TWO_STEP and
                                           ["cmd:" + k for k in rules.TWO_STEP]):
            kind, key = rules.parse(item)
            if kind == "section":
                self.assertIsNotNone(maya_hub.section(key), item)
            else:
                self.assertIsNotNone(maya_hotkeys.row(key), item)


class PurityTests(unittest.TestCase):
    def test_stdlib_only(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugin = os.path.join(here, "SkeldarAnim")
        code = ("import sys, maya_radial_rules; "
                "bad=[m for m in sys.modules if m.startswith(('maya','PySide'))"
                " and m != 'maya_radial_rules']; print(bad)")
        out = subprocess.check_output([sys.executable, "-c", code], cwd=plugin)
        self.assertEqual(out.decode().strip(), "[]")


if __name__ == "__main__":
    unittest.main()

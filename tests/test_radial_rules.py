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
        slots = ("section:tools", "", "cmd:tools.aim", "", "", "", "", "")
        self.assertEqual(rules.decode(rules.encode(slots)), slots)

    def test_short_and_junk_normalised(self):
        self.assertEqual(rules.decode('["cmd:a", 3, "bad"]'),
                         ("cmd:a",) + ("",) * 7)
        self.assertEqual(len(rules.decode('["cmd:a"]' )), 8)

    def test_broken_text_gives_defaults(self):
        for text in ("", None, "{", "{}", "7"):
            self.assertEqual(rules.decode(text), rules.DEFAULTS)

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

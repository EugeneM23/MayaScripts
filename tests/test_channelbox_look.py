"""maya_channelbox.look - our Channel Box's plain values (2026-10-18)."""

import os
import subprocess
import sys
import unittest

from maya_channelbox import look


class FormatTests(unittest.TestCase):

    def test_numbers_drop_trailing_zeros_and_never_read_minus_zero(self):
        self.assertEqual(look.fmt(4.8), "4.8")
        self.assertEqual(look.fmt(12.40300), "12.403")
        self.assertEqual(look.fmt(-0.0001), "0")
        self.assertEqual(look.fmt(1.0), "1")
        self.assertEqual(look.fmt(-18.5), "-18.5")
        self.assertEqual(look.fmt(2.123456, precision=5), "2.12346")

    def test_bools_enums_and_ints(self):
        self.assertEqual(look.fmt(1, "bool"), "on")
        self.assertEqual(look.fmt(0, "bool"), "off")
        self.assertEqual(look.fmt(1, "enum", names=["xyz", "yzx"]), "yzx")
        self.assertEqual(look.fmt(7, "enum", names=["a"]), "7")
        self.assertEqual(look.fmt(3.6, "long"), "4")


class TypedTests(unittest.TestCase):

    def test_plain_and_relative(self):
        self.assertEqual(look.typed("5", 2.0), 5.0)
        self.assertEqual(look.typed("+=5", 2.0), 7.0)
        self.assertEqual(look.typed("-=0.5", 2.0), 1.5)
        self.assertEqual(look.typed("*=3", 2.0), 6.0)
        self.assertEqual(look.typed("/=4", 2.0), 0.5)

    def test_nonsense_and_division_by_zero_mean_nothing(self):
        self.assertIsNone(look.typed("abc", 1.0))
        self.assertIsNone(look.typed("", 1.0))
        self.assertIsNone(look.typed("/=0", 1.0))

    def test_bools_read_words_and_ints_round(self):
        self.assertEqual(look.typed("off", 1, "bool"), 0)
        self.assertEqual(look.typed("yes", 0, "bool"), 1)
        self.assertEqual(look.typed("2.6", 0, "long"), 3)


class StateTests(unittest.TestCase):

    def test_every_state(self):
        self.assertEqual(look.state_of({"locked": True, "source": "curve", "on_key": True})[0], "locked")
        self.assertEqual(look.state_of({"source": "driven"})[0], "driven")
        self.assertEqual(look.state_of({"source": "curve", "keys": [0], "on_key": True})[0], "onkey")
        self.assertEqual(look.state_of({"source": "curve", "keys": [0], "on_key": True,
                                        "breakdown": True})[0], "onbd")
        self.assertEqual(look.state_of({"source": "curve", "keys": [0]})[0], "keyed")
        self.assertEqual(look.state_of({})[0], "plain")

    def test_muted_and_changed_ride_along(self):
        state, muted, changed = look.state_of({"source": "curve", "keys": [0], "muted": True,
                                               "changed": True})
        self.assertEqual((state, muted, changed), ("keyed", True, True))
        self.assertEqual(look.state_of({"locked": True, "changed": True})[2], False)


def ch(attr, **kw):
    d = {"key": attr, "attr": attr}
    d.update(kw)
    return d


class RowTests(unittest.TestCase):

    def test_rules_between_groups_in_the_main_section_only(self):
        sections = [{"key": "main", "kind": "main",
                     "channels": [ch("translateX"), ch("translateY"), ch("rotateX"), ch("scaleX"),
                                  ch("visibility"), ch("swivel"), ch("roll")]},
                    {"key": "inputs:a", "kind": "inputs", "label": "a", "title": "INPUTS",
                     "channels": [ch("width"), ch("height")]}]
        kinds = [r["kind"] for r in look.rows(sections)]
        self.assertEqual(kinds, ["channel", "channel", "rule", "channel", "rule", "channel", "rule",
                                 "channel", "rule", "channel", "channel", "section"])
        opened = look.rows(sections, opened=("inputs:a",))
        self.assertEqual([r["kind"] for r in opened][-3:], ["section", "channel", "channel"])
        self.assertTrue(opened[-3]["open"])

    def test_layout_puts_the_cell_left_the_value_right_and_hit_finds_them(self):
        rows = look.rows([{"key": "main", "kind": "main", "channels": [ch("tx"), ch("ty")]}])
        placed, height = look.layout(rows, 340, 1.0)
        self.assertEqual(len(placed), 2)
        y, h, parts = placed[1]
        self.assertAlmostEqual(h, look.ROW_H)
        self.assertLess(parts["mark"][0], parts["name"][0])
        self.assertAlmostEqual(parts["value"][0] + parts["value"][2], 340 - look.PAD)
        self.assertGreater(height, y + h)
        vx, vy, vw, vh = parts["value"]
        self.assertEqual(look.hit(placed, rows, vx + 2, y + 5), (1, "value"))
        mx = parts["mark"][0] + 2
        self.assertEqual(look.hit(placed, rows, mx, y + 5), (1, "mark"))
        self.assertEqual(look.hit(placed, rows, parts["name"][0] + 3, y + 5), (1, "name"))
        self.assertEqual(look.hit(placed, rows, 5, height + 50), (None, None))

    def test_layout_scales_with_the_display(self):
        rows = look.rows([{"key": "main", "kind": "main", "channels": [ch("tx")]}])
        placed, _ = look.layout(rows, 510, 1.5)
        self.assertAlmostEqual(placed[0][1], look.ROW_H * 1.5)
        self.assertAlmostEqual(placed[0][2]["value"][2], look.VALUE_W * 1.5)


class SelectTests(unittest.TestCase):
    order = ["tx", "ty", "tz", "rx"]

    def test_a_click_selects_alone(self):
        self.assertEqual(look.select(self.order, {"tx", "ty"}, "tx", "rx"), ({"rx"}, "rx"))

    def test_ctrl_toggles(self):
        sel, anchor = look.select(self.order, {"tx"}, "tx", "ty", ctrl=True)
        self.assertEqual(sel, {"tx", "ty"})
        sel, _ = look.select(self.order, sel, anchor, "tx", ctrl=True)
        self.assertEqual(sel, {"ty"})

    def test_shift_adds_the_run_from_the_anchor(self):
        sel, anchor = look.select(self.order, {"ty"}, "ty", "rx", shift=True)
        self.assertEqual(sel, {"ty", "tz", "rx"})
        self.assertEqual(anchor, "ty")


class SliderTests(unittest.TestCase):

    def test_the_step_follows_the_kind_and_maya_speed(self):
        self.assertAlmostEqual(look.per_px("translateX", "doubleLinear"), 0.1)
        self.assertAlmostEqual(look.per_px("rotateY", "doubleAngle"), 1.0)
        self.assertAlmostEqual(look.per_px("scaleZ", "double"), 0.01)
        self.assertAlmostEqual(look.per_px("rotateY", "doubleAngle", speed=0.1), 0.1)
        self.assertAlmostEqual(look.per_px("stretchy", "double", lo=0, hi=10), 0.05)

    def test_scrubbed_clamps_and_rounds_ints(self):
        self.assertAlmostEqual(look.scrubbed(1.0, 20, 0.1), 3.0)
        self.assertEqual(look.scrubbed(9.0, 50, 0.1, 0, 10), 10.0)
        self.assertEqual(look.scrubbed(1, 7, 0.2, kind="long"), 2)
        self.assertEqual(look.modifier(shift=True), 5.0)
        self.assertEqual(look.modifier(ctrl=True), 0.2)


class KeyMoveTests(unittest.TestCase):

    def test_a_key_that_came_or_left_this_frame(self):
        before = {"tx": (False, 3), "ty": (True, 3), "tz": (True, 3), "rx": (True, 2)}
        after = {"tx": (True, 4), "ty": (False, 2), "tz": (True, 3), "ry": (True, 1)}
        self.assertEqual(look.key_moves(before, after, 12), (["tx"], ["ty"]))

    def test_a_key_dragged_away_is_no_deletion(self):
        self.assertEqual(look.key_moves({"tx": (True, 3)}, {"tx": (False, 3)}, 12), ([], []))


class HeadTests(unittest.TestCase):

    def test_head_text(self):
        self.assertEqual(look.head_text("|grp|IKLeg_L", 2), ("IKLeg_L", "+2"))
        self.assertEqual(look.head_text("IKLeg_L", 0), ("IKLeg_L", ""))


class Purity(unittest.TestCase):

    def test_look_and_the_package_import_with_the_stdlib_alone(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "SkeldarAnim")
        code = ("import sys; import maya_channelbox, maya_channelbox.look; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6')]; print(bad); "
                "sys.exit(1 if bad else 0)")
        done = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()

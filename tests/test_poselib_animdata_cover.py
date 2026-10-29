"""The arithmetic of an animation card, the corner `test_poselib_animdata` leaves out: a remembered
range end that is not a number.
"""
import unittest

from maya_poselib import animdata as ad


class RangeEnds(unittest.TestCase):

    def test_a_number_and_a_numeric_string_are_floats(self):
        self.assertEqual(ad._number(12), 12.0)
        self.assertEqual(ad._number(" 3.5 "), 3.5)
        self.assertIsInstance(ad._number(12), float)

    def test_nothing_remembered_is_none(self):
        for value in (None, "", "   "):
            self.assertIsNone(ad._number(value), repr(value))

    def test_a_value_that_is_not_a_number_is_none(self):
        for value in ("abc", "1,5", [3], {}, object()):
            self.assertIsNone(ad._number(value), repr(value))

    def test_a_number_that_is_not_finite_is_none(self):
        for value in (float("inf"), float("-inf"), float("nan"), "inf", "nan"):
            self.assertIsNone(ad._number(value), repr(value))

    def test_options_from_a_mapping_drops_a_range_end_that_is_not_a_number(self):
        options = ad.options_from({"start": "abc", "end": "40"})
        self.assertIsNone(options.start)
        self.assertEqual(options.end, 40.0)


if __name__ == "__main__":
    unittest.main()

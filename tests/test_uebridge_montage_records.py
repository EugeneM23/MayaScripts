"""The record's montage half: the kind, the slot and the row's words."""

import unittest

from maya_uebridge import records


class MontageRecords(unittest.TestCase):
    def test_a_record_defaults_to_no_kind(self):
        rec = records.AnimRecord("A", "/Game/A", "SK", 10, 1.0, 30.0)
        self.assertEqual(rec.kind, "")
        self.assertFalse(records.is_montage(rec))

    def test_a_positional_record_still_means_what_it_meant(self):
        rec = records.AnimRecord("A", "/Game/A", "SK", 10, 1.0, 30.0,
                                 "folder", "C:/a.fbx", "take=2", "fbx")
        self.assertEqual(rec.source, "folder")
        self.assertEqual(rec.fmt, "fbx")
        self.assertEqual(rec.kind, "")

    def test_parse_payload_reads_the_kind(self):
        out = records.parse_payload({"assets": [
            {"name": "AM_X", "package": "/Game/AM_X", "kind": "montage"}]})
        self.assertTrue(records.is_montage(out[0]))

    def test_parse_payload_leaves_an_animation_without_a_kind(self):
        out = records.parse_payload({"assets": [
            {"name": "A", "package": "/Game/A", "frames": "10"}]})
        self.assertEqual(out[0].kind, "")

    def test_with_slot_names_the_montage_and_the_slot(self):
        rec = records.AnimRecord("AM_X", "/Game/Combat/AM_X", "SK", None, None,
                                 None, kind="montage")
        slotted = records.with_slot(rec, "1P")
        self.assertEqual(slotted.name, "AM_X_1P")
        self.assertEqual(records.montage_slot(slotted), "1P")
        self.assertEqual(slotted.package, rec.package)
        self.assertTrue(records.is_montage(slotted))

    def test_with_slot_twice_does_not_stack_the_slot(self):
        rec = records.AnimRecord("AM_X", "/Game/AM_X", "SK", None, None, None,
                                 kind="montage")
        once = records.with_slot(rec, "1P")
        twice = records.with_slot(once, "DefaultSlot")
        self.assertEqual(twice.name, "AM_X_DefaultSlot")
        self.assertEqual(records.montage_slot(twice), "DefaultSlot")

    def test_with_slot_leaves_a_record_without_a_slot_alone(self):
        rec = records.AnimRecord("AM_X", "/Game/AM_X", "SK", None, None, None,
                                 kind="montage")
        self.assertEqual(records.with_slot(rec, ""), rec)

    def test_an_animation_is_never_slotted(self):
        rec = records.AnimRecord("A", "/Game/A", "SK", 10, 1.0, 30.0)
        self.assertEqual(records.with_slot(rec, "1P"), rec)

    def test_a_montage_row_says_montage_in_place_of_frames(self):
        rec = records.AnimRecord("AM_X", "/Game/Combat/AM_X", "SK", None, None,
                                 None, kind="montage")
        row = records.format_row(rec)
        self.assertIn("AM_X", row)
        self.assertIn("/Game/Combat", row)
        self.assertIn("montage", row)

    def test_a_slotted_row_names_the_slot(self):
        rec = records.with_slot(
            records.AnimRecord("AM_X", "/Game/AM_X", "SK", None, None, None,
                               kind="montage"), "1P")
        self.assertIn("1P", records.format_row(rec))

    def test_an_animation_row_is_unchanged(self):
        rec = records.AnimRecord("A_Jump", "/Game/Anims/A_Jump", "SK", 24,
                                 0.8, 30.0)
        row = records.format_row(rec)
        self.assertIn("24 fr", row)
        self.assertNotIn("montage", row)


if __name__ == "__main__":
    unittest.main()

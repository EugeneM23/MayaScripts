"""Tests for the pure record model of the UE bridge.

Runs with neither Maya nor Unreal present.
"""

import os
import subprocess
import sys
import unittest

from maya_uebridge import records


class ParsePayload(unittest.TestCase):

    def test_reads_the_fields_it_needs(self):
        payload = {"assets": [{"name": "A_Jump", "package": "/Game/Anim/A_Jump",
                               "skeleton": "SK_Manny", "frames": 45,
                               "length": 1.5, "fps": 30.0}]}
        (rec,) = records.parse_payload(payload)
        self.assertEqual(rec.name, "A_Jump")
        self.assertEqual(rec.package, "/Game/Anim/A_Jump")
        self.assertEqual(rec.skeleton, "SK_Manny")
        self.assertEqual(rec.frames, 45)
        self.assertEqual(rec.fps, 30.0)

    def test_survives_missing_tags(self):
        """UE returns no frame count for some assets; that must not lose the row."""
        payload = {"assets": [{"name": "A_Jump", "package": "/Game/Anim/A_Jump"}]}
        (rec,) = records.parse_payload(payload)
        self.assertIsNone(rec.frames)
        self.assertEqual(rec.skeleton, "")

    def test_drops_rows_with_no_package(self):
        """Without a package path there is nothing to export later."""
        payload = {"assets": [{"name": "A_Jump"},
                              {"name": "A_Walk", "package": "/Game/A_Walk"}]}
        got = records.parse_payload(payload)
        self.assertEqual([r.name for r in got], ["A_Walk"])

    def test_an_empty_payload_is_an_empty_list(self):
        self.assertEqual(records.parse_payload({}), [])

    def test_numbers_arriving_as_strings_are_converted(self):
        """Asset registry tags come back as text, not typed values."""
        payload = {"assets": [{"name": "A", "package": "/Game/A",
                               "frames": "45", "length": "1.5", "fps": "30"}]}
        (rec,) = records.parse_payload(payload)
        self.assertEqual(rec.frames, 45)
        self.assertEqual(rec.length, 1.5)
        self.assertEqual(rec.fps, 30.0)

    def test_unparsable_numbers_become_none_instead_of_raising(self):
        payload = {"assets": [{"name": "A", "package": "/Game/A", "frames": "n/a"}]}
        (rec,) = records.parse_payload(payload)
        self.assertIsNone(rec.frames)

    def test_rows_come_back_sorted_by_name(self):
        payload = {"assets": [{"name": "B", "package": "/Game/B"},
                              {"name": "a", "package": "/Game/a"}]}
        self.assertEqual([r.name for r in records.parse_payload(payload)], ["a", "B"])


class Filtering(unittest.TestCase):

    def setUp(self):
        self.recs = records.parse_payload({"assets": [
            {"name": "A_Jump_Start", "package": "/Game/Manny/A_Jump_Start"},
            {"name": "A_Walk_Fwd", "package": "/Game/Manny/A_Walk_Fwd"},
            {"name": "A_Idle", "package": "/Game/Enemy/A_Idle"}]})

    def test_empty_query_keeps_everything(self):
        self.assertEqual(len(records.filter_records(self.recs, "")), 3)

    def test_whitespace_only_query_keeps_everything(self):
        self.assertEqual(len(records.filter_records(self.recs, "   ")), 3)

    def test_matches_case_insensitively(self):
        got = records.filter_records(self.recs, "jump")
        self.assertEqual([r.name for r in got], ["A_Jump_Start"])

    def test_matches_on_the_path_too(self):
        got = records.filter_records(self.recs, "enemy")
        self.assertEqual([r.name for r in got], ["A_Idle"])

    def test_every_term_must_match(self):
        """Typing two words narrows instead of widening."""
        got = records.filter_records(self.recs, "manny walk")
        self.assertEqual([r.name for r in got], ["A_Walk_Fwd"])

    def test_terms_may_match_in_either_field(self):
        got = records.filter_records(self.recs, "enemy idle")
        self.assertEqual([r.name for r in got], ["A_Idle"])

    def test_no_match_is_an_empty_list(self):
        self.assertEqual(records.filter_records(self.recs, "zzz"), [])


class Namespaces(unittest.TestCase):

    def test_uses_the_asset_name(self):
        self.assertEqual(records.namespace_for("A_Jump", set()), "A_Jump")

    def test_strips_characters_maya_rejects(self):
        self.assertEqual(records.namespace_for("A Jump-01.v2", set()), "A_Jump_01_v2")

    def test_prefixes_a_leading_digit(self):
        self.assertEqual(records.namespace_for("01_Jump", set()), "_01_Jump")

    def test_uniquifies_against_what_exists(self):
        self.assertEqual(records.namespace_for("A_Jump", {"A_Jump", "A_Jump1"}),
                         "A_Jump2")

    def test_an_empty_name_still_yields_something_usable(self):
        self.assertTrue(records.namespace_for("", set()))

    def test_uniquifying_respects_the_sanitised_form(self):
        """The taken set holds real Maya namespaces, so compare after cleaning."""
        self.assertEqual(records.namespace_for("A Jump", {"A_Jump"}), "A_Jump1")


class Rows(unittest.TestCase):

    def test_shows_name_path_and_length(self):
        (rec,) = records.parse_payload({"assets": [
            {"name": "A_Jump", "package": "/Game/Manny/A_Jump", "frames": 45}]})
        row = records.format_row(rec)
        self.assertIn("A_Jump", row)
        self.assertIn("/Game/Manny", row)
        self.assertIn("45", row)

    def test_a_missing_frame_count_does_not_print_none(self):
        (rec,) = records.parse_payload({"assets": [
            {"name": "A_Jump", "package": "/Game/Manny/A_Jump"}]})
        self.assertNotIn("None", records.format_row(rec))

    def test_a_long_folder_keeps_its_tail_not_its_head(self):
        """Every UE path starts /Game/...; what tells rows apart is the end."""
        (rec,) = records.parse_payload({"assets": [{
            "name": "Jump_Apex",
            "package": "/Game/ParagonSevarog/Characters/Heroes/Sevarog/"
                       "Animations/Locomotion/Jump/Jump_Apex"}]})
        row = records.format_row(rec)
        self.assertIn("Locomotion/Jump", row)
        self.assertIn("...", row)
        self.assertNotIn("ParagonSevarog", row)

    def test_a_short_folder_is_not_mangled(self):
        (rec,) = records.parse_payload({"assets": [
            {"name": "A_Jump", "package": "/Game/Manny/A_Jump"}]})
        row = records.format_row(rec)
        self.assertIn("/Game/Manny", row)
        self.assertNotIn("...", row)

    def test_long_names_keep_both_ends(self):
        """These names say what they are at the head and which one at the tail;
        six Longsword rows read identically if either end is cut."""
        names = ["AS_Longsword_Attack_Back_Light_Combo_v2_1_3P",
                 "AS_Longsword_Attack_Back_Light_Combo_v2_2_1P",
                 "AS_Longsword_Attack_Forward_Combo_2_Hold_2_Stand_Right_3P",
                 "AS_Longsword_Attack_Forward_Combo_2_Hold_1_Stand_Left_1P"]
        parsed = records.parse_payload({"assets": [
            {"name": n, "package": "/Game/A/" + n} for n in names]})
        rows = [records.format_row(rec).split("  ")[0] for rec in parsed]
        self.assertEqual(len(set(rows)), len(names), rows)

    def test_a_truncated_name_shows_its_ending(self):
        (rec,) = records.parse_payload({"assets": [{
            "name": "AS_Longsword_Attack_Forward_Combo_2_Hold_2_Stand_Right_3P",
            "package": "/Game/A/x"}]})
        row = records.format_row(rec)
        self.assertIn("AS_Longsword", row)
        self.assertIn("Right_3P", row)
        self.assertIn("...", row)

    def test_a_name_that_fits_is_untouched(self):
        (rec,) = records.parse_payload({"assets": [
            {"name": "AS_Jump", "package": "/Game/A/AS_Jump"}]})
        self.assertIn("AS_Jump", records.format_row(rec))
        self.assertNotIn("...", records.format_row(rec).split("  ")[0])

    def test_two_animations_in_different_deep_folders_read_differently(self):
        deep = records.parse_payload({"assets": [
            {"name": "Jump", "package":
             "/Game/ParagonSevarog/Characters/Heroes/Sevarog/Anims/Jump"},
            {"name": "Jump", "package":
             "/Game/ParagonKwang/Characters/Heroes/Kwang/Anims/Jump"}]})
        rows = [records.format_row(rec) for rec in deep]
        self.assertNotEqual(rows[0], rows[1])


class Purity(unittest.TestCase):

    def test_the_pure_modules_import_without_maya(self):
        """records/uescripts/uelink must not drag maya.cmds or the window in."""
        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import maya_uebridge, maya_uebridge.records,"
            " maya_uebridge.uescripts, maya_uebridge.uelink,"
            " maya_uebridge.vcs;"
            "assert 'maya.cmds' not in sys.modules, 'maya.cmds leaked in';"
            "assert 'maya_uebridge.window' not in sys.modules, 'window leaked in';"
            "assert 'maya_uebridge.animimport' not in sys.modules, 'animimport leaked in';"
            "print('clean')" % root)
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True)
        self.assertIn("clean", out.stdout, out.stderr)


if __name__ == "__main__":
    unittest.main()

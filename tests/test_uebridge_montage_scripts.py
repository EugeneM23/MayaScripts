"""The three montage scripts we send into the editor.

They are source TEXT, so what can be tested here is that each one compiles,
carries its parameters as JSON literals (a Windows path's backslash is not an
escape sequence) and ends in the marker the sender waits for.
"""

import json
import unittest

from maya_uebridge import uescripts


class MontageList(unittest.TestCase):
    def test_it_compiles(self):
        compile(uescripts.montage_list_script("/tmp/o.json"), "<gen>", "exec")

    def test_it_carries_the_reply_path_as_a_literal(self):
        src = uescripts.montage_list_script("C:\\temp\\o.json")
        self.assertIn(json.dumps("C:\\temp\\o.json"), src)

    def test_it_asks_the_registry_for_montages(self):
        src = uescripts.montage_list_script("/tmp/o.json")
        self.assertIn("AnimMontage", src)
        self.assertIn("get_assets", src)

    def test_it_loads_nothing(self):
        """Loading all 195 would pull their clips; the listing is registry only."""
        self.assertNotIn("load_asset", uescripts.montage_list_script("/tmp/o.json"))

    def test_it_marks_every_row_a_montage(self):
        self.assertIn(json.dumps("montage"),
                      uescripts.montage_list_script("/tmp/o.json"))

    def test_it_takes_a_package_path(self):
        src = uescripts.montage_list_script("/tmp/o.json", "/Game/Combat")
        self.assertIn(json.dumps("/Game/Combat"), src)

    def test_it_says_when_the_registry_is_still_scanning(self):
        self.assertIn("is_loading_assets",
                      uescripts.montage_list_script("/tmp/o.json"))

    def test_it_ends_in_the_marker(self):
        self.assertIn(json.dumps(uescripts.MARKER),
                      uescripts.montage_list_script("/tmp/o.json"))


class MontagePlan(unittest.TestCase):
    def test_it_compiles(self):
        compile(uescripts.montage_plan_script("/tmp/o.json", ["/Game/AM_X"]),
                "<gen>", "exec")

    def test_it_carries_every_package(self):
        src = uescripts.montage_plan_script("/tmp/o.json",
                                            ["/Game/A", "/Game/B"])
        self.assertIn(json.dumps(["/Game/A", "/Game/B"]), src)

    def test_it_reads_the_segments_fields(self):
        src = uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"])
        for field in ("slot_anim_tracks", "anim_segments", "start_pos",
                      "anim_start_time", "anim_end_time", "anim_play_rate"):
            self.assertIn(field, src)

    def test_it_reads_looping_count_by_its_real_name(self):
        """`loop_count` answers None on this build; the property is
        `looping_count` (measured 2026-10-29)."""
        src = uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"])
        self.assertIn("looping_count", src)

    def test_it_reads_whether_a_clip_is_additive(self):
        self.assertIn("additive_anim_type",
                      uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"]))

    def test_it_reads_the_sections(self):
        """No montage in Atone has any; read them so the day one does is not a
        silent wrong answer."""
        self.assertIn("composite_sections",
                      uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"]))

    def test_a_clip_travels_as_a_package_not_an_object_path(self):
        """`get_path_name` answers /Game/A/Name.Name, and the exporter names
        its file after the tail - the plan normalises it (measured live
        2026-10-29: the FBX came out LongSword_Block_Stun_In_1P.LongSword_
        Block_Stun_In_1P.fbx without this)."""
        self.assertIn("package_of",
                      uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"]))

    def test_it_ends_in_the_marker(self):
        self.assertIn(json.dumps(uescripts.MARKER),
                      uescripts.montage_plan_script("/tmp/o.json", ["/Game/A"]))


class MontageExport(unittest.TestCase):
    def test_it_compiles(self):
        compile(uescripts.montage_export_script("/tmp/o.json", ["/Game/A"],
                                                "C:\\temp\\clips"),
                "<gen>", "exec")

    def test_it_carries_the_packages_and_the_folder(self):
        src = uescripts.montage_export_script("/tmp/o.json",
                                              ["/Game/A", "/Game/B"],
                                              "C:\\temp\\clips")
        self.assertIn(json.dumps(["/Game/A", "/Game/B"]), src)
        self.assertIn(json.dumps("C:\\temp\\clips"), src)

    def test_it_runs_the_anim_sequence_exporter(self):
        src = uescripts.montage_export_script("/tmp/o.json", ["/Game/A"], "/tmp")
        self.assertIn("AnimSequenceExporterFBX", src)
        self.assertIn("run_asset_export_task", src)

    def test_it_keeps_every_dialog_away(self):
        src = uescripts.montage_export_script("/tmp/o.json", ["/Game/A"], "/tmp")
        self.assertIn("automated", src)
        self.assertIn("prompt", src)

    def test_it_names_a_clip_it_could_not_export_rather_than_failing_the_lot(self):
        src = uescripts.montage_export_script("/tmp/o.json", ["/Game/A"], "/tmp")
        self.assertIn("failed", src)

    def test_the_preview_mesh_is_a_literal(self):
        with_mesh = uescripts.montage_export_script("/tmp/o.json", ["/Game/A"],
                                                    "/tmp", preview_mesh=True)
        without = uescripts.montage_export_script("/tmp/o.json", ["/Game/A"],
                                                  "/tmp")
        self.assertIn("export_preview_mesh", with_mesh)
        self.assertNotEqual(with_mesh, without)

    def test_it_ends_in_the_marker(self):
        self.assertIn(json.dumps(uescripts.MARKER),
                      uescripts.montage_export_script("/tmp/o.json",
                                                      ["/Game/A"], "/tmp"))


if __name__ == "__main__":
    unittest.main()

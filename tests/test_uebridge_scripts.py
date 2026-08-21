"""Tests for the UE-side script text.

The scripts run inside the editor, where we cannot test them. What we can test
here is that they are valid Python, that nothing we interpolate can break out of
its literal, and that they keep the promises the rest of the tool relies on.
"""

import json
import unittest

from maya_uebridge import uescripts


class Embedding(unittest.TestCase):

    def test_windows_paths_survive_embedding(self):
        r"""A raw C:\temp\new\x.json would turn \t and \n into control characters."""
        path = "C:\\temp\\new\\anim.json"
        src = uescripts.list_script(path)
        self.assertIn(json.dumps(path), src)
        self.assertNotIn("'" + path + "'", src)

    def test_a_quote_in_an_asset_path_cannot_break_out(self):
        src = uescripts.export_script(
            "/tmp/o.json", "/Game/A'; import os; os.remove('x'); y='", "/tmp/a.fbx")
        compile(src, "<generated>", "exec")

    def test_a_backslash_in_an_asset_path_cannot_break_out(self):
        src = uescripts.export_script("/tmp/o.json", "/Game/A\\", "/tmp/a.fbx")
        compile(src, "<generated>", "exec")

    def test_both_scripts_are_valid_python(self):
        compile(uescripts.list_script("/tmp/o.json"), "<generated>", "exec")
        compile(uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx"),
                "<generated>", "exec")

    def test_the_package_path_is_a_parameter_not_a_constant(self):
        src = uescripts.list_script("/tmp/o.json", package_path="/Game/Characters")
        self.assertIn(json.dumps("/Game/Characters"), src)

    def test_the_default_package_path_is_the_whole_game_folder(self):
        self.assertIn(json.dumps("/Game"), uescripts.list_script("/tmp/o.json"))


class ListContract(unittest.TestCase):

    def test_checks_the_registry_is_done_scanning(self):
        """A partial list right after editor start reads as a small project."""
        self.assertIn("is_loading_assets", uescripts.list_script("/tmp/o.json"))

    def test_reports_the_project_so_the_window_can_name_it(self):
        self.assertIn("get_project_file_path", uescripts.list_script("/tmp/o.json"))

    def test_asks_for_anim_sequences(self):
        self.assertIn("AnimSequence", uescripts.list_script("/tmp/o.json"))

    def test_survives_the_registry_api_change(self):
        """class_names became class_paths in 5.1; both branches must be present."""
        src = uescripts.list_script("/tmp/o.json")
        self.assertIn("class_paths", src)
        self.assertIn("class_names", src)

    def test_reads_tags_rather_than_loading_assets(self):
        """Loading every AnimSequence to read its length would take minutes."""
        src = uescripts.list_script("/tmp/o.json")
        self.assertIn("get_tag_value", src)
        self.assertNotIn("load_asset", src)

    def test_tries_several_tag_spellings(self):
        """Tag names differ across engine versions, so we do not guess just one."""
        src = uescripts.list_script("/tmp/o.json")
        self.assertIn("Number of Frames", src)
        self.assertIn("SequenceLength", src)

    def test_can_be_asked_to_dump_raw_tags_for_the_spike(self):
        plain = uescripts.list_script("/tmp/o.json")
        sampled = uescripts.list_script("/tmp/o.json", sample_tags=True)
        self.assertIn("sample_tags", sampled)
        self.assertNotEqual(plain, sampled)
        compile(sampled, "<generated>", "exec")


class ExportContract(unittest.TestCase):

    def test_runs_unattended(self):
        """A modal dialog with nobody to click it hangs the whole editor."""
        src = uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")
        self.assertIn("automated", src)
        self.assertIn("prompt", src)

    def test_uses_the_anim_sequence_exporter(self):
        src = uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")
        self.assertIn("AnimSequenceExporterFBX", src)
        self.assertIn("run_asset_export_task", src)

    def test_sets_export_options_defensively(self):
        """FbxExportOption field names move between versions; a miss must not abort."""
        src = uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")
        self.assertIn("FbxExportOption", src)
        self.assertIn("export_preview_mesh", src)

    def test_confirms_the_file_actually_appeared(self):
        """run_asset_export_task returning True is not proof of a file on disk."""
        src = uescripts.export_script("/tmp/o.json", "/Game/A", "/tmp/a.fbx")
        self.assertIn("isfile", src)


class ReplyContract(unittest.TestCase):

    def scripts(self):
        return (uescripts.list_script("/tmp/out.json"),
                uescripts.export_script("/tmp/out.json", "/Game/A", "/tmp/a.fbx"))

    def test_both_write_their_reply_to_the_file_we_named(self):
        for src in self.scripts():
            self.assertIn(json.dumps("/tmp/out.json"), src)
            self.assertIn("json.dump", src)

    def test_both_report_their_own_failures_into_the_reply(self):
        """A traceback must reach us, not vanish into the editor's log."""
        for src in self.scripts():
            self.assertIn("except Exception", src)
            self.assertIn("format_exc", src)

    def test_the_reply_is_written_even_when_the_body_raises(self):
        for src in self.scripts():
            self.assertIn("finally", src)

    def test_both_print_the_marker(self):
        for src in self.scripts():
            self.assertIn(uescripts.MARKER, src)


class ReimportScript(unittest.TestCase):

    def script(self):
        return uescripts.reimport_script(
            "C:\\temp\\out.json", "/Game/Anims/AS_X",
            "C:\\src\\Exports\\AS_X.fbx")

    def test_paths_are_json_encoded_not_pasted(self):
        self.assertIn(json.dumps("C:\\src\\Exports\\AS_X.fbx"), self.script())

    def test_the_script_compiles(self):
        compile(self.script(), "<reimport>", "exec")

    def test_the_reimport_is_an_automated_replace_import(self):
        """This engine build has no ReimportSubsystem (measured 2026-08-21),
        so the reimport is an AssetImportTask over the existing package -
        automated, or the editor raises a dialog nobody can click."""
        text = self.script()
        self.assertIn("replace_existing", text)
        self.assertIn('"automated", True', text)
        self.assertIn("FBXIT_ANIMATION", text)

    def test_the_import_is_forced_onto_the_legacy_fbx_path(self):
        """Interchange swallows a bones-only fbx with 'nothing to import'
        (measured 2026-08-21 in the editor log), so the task runs with the
        Interchange fbx flag off, and the flag is put back in a finally."""
        text = self.script()
        self.assertIn("Interchange.FeatureFlags.Import.FBX", text)
        self.assertIn("finally:", text.split("import_asset_tasks")[0]
                      + text.split("import_asset_tasks")[1])

    def test_success_is_measured_by_get_objects(self):
        """task.result is deprecated on this build; imported_object_paths
        stays empty (measured) - get_objects is what answers."""
        self.assertIn("get_objects", self.script())

    def test_the_skeleton_comes_from_the_asset_itself(self):
        self.assertIn('get_editor_property("skeleton")', self.script())

    def test_the_asset_is_saved_after_the_reimport(self):
        self.assertIn("save_asset", self.script())

    def test_a_missing_asset_is_guarded_before_use(self):
        """Trap 24: a null object crashes the editor, it does not raise."""
        self.assertIn("could not load asset", self.script())

    def test_the_reply_tail_is_present(self):
        text = self.script()
        self.assertIn("finally:", text)
        self.assertIn(json.dumps(uescripts.MARKER), text)


class ListScriptContentDir(unittest.TestCase):

    def test_the_listing_reports_the_content_dir(self):
        text = uescripts.list_script("C:/out.json")
        self.assertIn("project_content_dir", text)
        self.assertIn("content_dir", text)


if __name__ == "__main__":
    unittest.main()

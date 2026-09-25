"""Tests for Export to uasset -- the direct road, with no Perforce on it.

The two things worth pinning hard: the dialog says what is actually at
stake (an animator who clicks through it must not be surprised in Unreal),
and the module genuinely does not reach Perforce -- which a docstring
cannot promise, so a subprocess measures it.

Live proof: docs/superpowers/plans/verify_uebridge_uasset.py.
"""

import os
import subprocess
import sys
import tempfile
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import records, uassetexport  # noqa: E402

REC = records.AnimRecord(
    name="AS_Sword_Attack_3P", package="/Game/Anim/Sword/AS_Sword_Attack_3P",
    skeleton="/Game/Char/SK_Manny", frames=60, length=2.0, fps=30.0)


# ---------------------------------------------------------------------------
# the package <-> path pair, after the move into records.py
# ---------------------------------------------------------------------------

class PackagePath(unittest.TestCase):

    CONTENT = os.path.join("D:", os.sep, "Atone", "Content")

    def test_round_trips(self):
        path = records.uasset_path_of(REC.package, self.CONTENT)
        self.assertTrue(path.endswith("AS_Sword_Attack_3P.uasset"), path)
        self.assertEqual(records.package_of(path, self.CONTENT), REC.package)

    def test_a_file_outside_content_has_no_package(self):
        self.assertEqual(
            records.package_of(os.path.join("E:", os.sep, "x.uasset"),
                               self.CONTENT), "")

    def test_vcs_still_answers_to_the_old_names(self):
        """Every existing caller says vcs.uasset_path_of; the move must be
        invisible to them."""
        from maya_uebridge import vcs
        self.assertIs(vcs.uasset_path_of, records.uasset_path_of)
        self.assertIs(vcs.package_of, records.package_of)

    def test_checkouts_shares_the_one_reimport_wording(self):
        from maya_uebridge import checkouts
        self.assertIs(checkouts.reimport_line, records.reimport_line)


class ReimportLine(unittest.TestCase):

    def test_saved_says_so_with_the_frame_count(self):
        line = records.reimport_line({"saved": True, "frames": 60})
        self.assertIn("saved", line)
        self.assertIn("60", line)

    def test_not_saved_tells_the_animator_what_to_do(self):
        line = records.reimport_line({"saved": False, "frames": 60})
        self.assertIn("NOT saved", line)
        self.assertIn("editor", line)

    def test_no_frame_count_is_not_a_blank_number(self):
        self.assertNotIn("None", records.reimport_line({"saved": True}))

    def test_nothing_at_all_does_not_raise(self):
        self.assertTrue(records.reimport_line(None))


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------

class UnchangedWarning(unittest.TestCase):
    """The silent no-op, measured live 2026-09-01: an FBX whose bones do
    not match the asset's skeleton imports with ok=True, saved=True, no
    notes and no error, and leaves the animation exactly as it was. The
    status said "reimported and saved (196 frames)" over an asset nothing
    had been written to."""

    CHANGED = {"saved": True, "frames": 72, "length": 2.4,
               "before_frames": 196, "before_length": 3.25,
               "skeleton": "UE4_Mannequin_Skeleton"}
    SAME = {"saved": True, "frames": 196, "length": 3.25,
            "before_frames": 196, "before_length": 3.25,
            "skeleton": "UE4_Mannequin_Skeleton"}

    def test_a_real_replacement_is_not_warned_about(self):
        self.assertEqual(records.unchanged_warning(self.CHANGED), "")

    def test_an_untouched_asset_is_named_along_with_its_skeleton(self):
        warning = records.unchanged_warning(self.SAME)
        self.assertIn("did NOT change", warning)
        self.assertIn("196", warning)
        self.assertIn("UE4_Mannequin_Skeleton", warning)

    def test_a_changed_length_alone_is_enough_to_stay_quiet(self):
        """Two clips can share a frame count and differ in length; only
        both being identical is the signal."""
        payload = dict(self.SAME, length=2.4)
        self.assertEqual(records.unchanged_warning(payload), "")

    def test_an_old_payload_without_the_before_fields_says_nothing(self):
        """A reply from a build before the before-read existed must not
        start warning about every export."""
        self.assertEqual(
            records.unchanged_warning({"saved": True, "frames": 60}), "")

    def test_no_skeleton_name_still_reads_as_a_sentence(self):
        payload = dict(self.SAME, skeleton="")
        self.assertIn("skeleton", records.unchanged_warning(payload))
        self.assertNotIn("None", records.unchanged_warning(payload))

    def test_nothing_at_all_does_not_raise(self):
        self.assertEqual(records.unchanged_warning(None), "")

    def test_it_reaches_the_status_line(self):
        line = uassetexport.result_line(
            "AS_X", {"joints": 93, "start": 0, "end": 71, "warning": ""},
            self.SAME)
        self.assertIn("did NOT change", line)

    def test_both_export_directions_use_the_one_warning(self):
        from maya_uebridge import checkouts
        with open(checkouts.__file__, encoding="utf-8") as handle:
            self.assertIn("unchanged_warning", handle.read())


class Refusal(unittest.TestCase):

    def test_nothing_selected(self):
        self.assertEqual(uassetexport.refusal(None, "D:/C", "x", True),
                         uassetexport.NO_SELECTION)

    def test_no_content_dir_names_refresh(self):
        message = uassetexport.refusal(REC, "", "", False)
        self.assertEqual(message, uassetexport.NO_CONTENT_DIR)
        self.assertIn("Refresh", message)

    def test_a_missing_uasset_names_the_path(self):
        message = uassetexport.refusal(REC, "D:/C", "D:/C/x.uasset", False)
        self.assertIn("D:/C/x.uasset", message)

    def test_everything_present_is_no_refusal(self):
        self.assertEqual(
            uassetexport.refusal(REC, "D:/C", "D:/C/x.uasset", True), "")

    def test_the_selection_is_checked_before_the_content_dir(self):
        """Nothing selected is the animator's likeliest mistake, and the
        message has to be about that rather than about Refresh."""
        self.assertEqual(uassetexport.refusal(None, "", "", False),
                         uassetexport.NO_SELECTION)


# ---------------------------------------------------------------------------
# the dialog
# ---------------------------------------------------------------------------

class OverwriteMessage(unittest.TestCase):

    def _message(self, read_only=False):
        return uassetexport.overwrite_message(
            REC.name, REC.package, "|root", read_only)

    def test_names_the_asset_and_the_skeleton(self):
        message = self._message()
        self.assertIn(REC.name, message)
        self.assertIn(REC.package, message)
        self.assertIn("root", message)

    def test_says_what_the_replace_import_throws_away(self):
        """The animator finds out in Unreal otherwise, and by then the
        asset is already saved."""
        message = self._message()
        self.assertIn("Pose_0..9", message)
        self.assertIn("MoveData", message)
        self.assertIn("REBUILT", message)

    def test_says_perforce_is_not_involved(self):
        message = self._message()
        self.assertIn("Perforce", message)
        self.assertIn("changelist", message)

    def test_mentions_the_flag_only_when_the_file_is_read_only(self):
        self.assertIn("read-only", self._message(read_only=True))
        self.assertNotIn("read-only", self._message(read_only=False))

    def test_an_unresolved_skeleton_does_not_print_none(self):
        message = uassetexport.overwrite_message("A", "/Game/A", None, False)
        self.assertNotIn("None", message)

    def test_the_long_dag_path_is_reduced_to_the_leaf(self):
        message = uassetexport.overwrite_message(
            "A", "/Game/A", "|grp|root1", False)
        self.assertIn("root1", message)
        self.assertNotIn("|grp|", message)


class ReadonlyNote(unittest.TestCase):

    def test_says_so_when_the_flag_came_off(self):
        self.assertIn("read-only", uassetexport.readonly_note(True))

    def test_a_writable_file_gets_no_note(self):
        self.assertEqual(uassetexport.readonly_note(False), "")


class ResultLine(unittest.TestCase):

    INFO = {"root": "root", "joints": 93, "start": 0, "end": 60,
            "warning": ""}

    def test_carries_the_export_and_the_reimport(self):
        line = uassetexport.result_line(
            REC.name, self.INFO, {"saved": True, "frames": 60})
        self.assertIn("93 bones", line)
        self.assertIn("saved", line)

    def test_empty_parts_are_dropped_rather_than_left_blank(self):
        line = uassetexport.result_line(
            REC.name, self.INFO, {"saved": True, "frames": 60}, ["", ""])
        self.assertNotIn("|  |", line)
        self.assertFalse(line.endswith("|"))

    def test_the_read_only_note_rides_along(self):
        line = uassetexport.result_line(
            REC.name, self.INFO, {"saved": True},
            [uassetexport.readonly_note(True)])
        self.assertIn("read-only cleared", line)

    def test_an_editor_error_is_reported_verbatim(self):
        line = uassetexport.result_line(
            REC.name, self.INFO,
            {"saved": False, "error": "could not load asset: /Game/x"})
        self.assertIn("could not load asset: /Game/x", line)


class Staging(unittest.TestCase):

    def test_the_fbx_is_named_for_the_button_that_wrote_it(self):
        path = uassetexport.fbx_staging_path("AS_X", os.path.join("T", "tmp"))
        self.assertTrue(path.endswith("AS_X.uasset.fbx"), path)

    def test_it_lands_in_the_folder_it_was_given(self):
        folder = os.path.join("T", "tmp")
        self.assertEqual(os.path.dirname(
            uassetexport.fbx_staging_path("AS_X", folder)), folder)


# ---------------------------------------------------------------------------
# the read-only flag, on a real temp file
# ---------------------------------------------------------------------------

class ReadOnlyFlag(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".uasset")
        os.close(handle)

    def tearDown(self):
        try:
            os.chmod(self.path, 0o666)
            os.remove(self.path)
        except OSError:
            pass

    def test_a_fresh_file_is_writable(self):
        self.assertFalse(uassetexport.is_read_only(self.path))

    def test_a_read_only_file_reads_as_one(self):
        os.chmod(self.path, 0o444)
        self.assertTrue(uassetexport.is_read_only(self.path))

    def test_clearing_makes_it_writable_and_reports_no_failure(self):
        os.chmod(self.path, 0o444)
        self.assertEqual(uassetexport.clear_read_only(self.path), "")
        self.assertFalse(uassetexport.is_read_only(self.path))

    def test_clearing_a_writable_file_is_a_no_op_that_succeeds(self):
        self.assertEqual(uassetexport.clear_read_only(self.path), "")

    def test_a_missing_file_fails_with_a_reason(self):
        os.remove(self.path)
        self.assertTrue(uassetexport.clear_read_only(self.path))

    def test_a_missing_file_is_not_reported_as_read_only(self):
        """`is_read_only` answers a question about a file that exists; the
        refusal table is what handles a missing one."""
        os.remove(self.path)
        self.assertFalse(uassetexport.is_read_only(self.path))


# ---------------------------------------------------------------------------
# the boundary
# ---------------------------------------------------------------------------

class NoPerforce(unittest.TestCase):
    """The claim that makes this button safe to press is "it never touches
    Perforce". A docstring cannot promise that; an import graph can."""

    def test_importing_it_does_not_drag_vcs_in(self):
        plugin = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "SkeldarAnim")
        script = (
            "import sys, types\n"
            "for name in ('maya', 'maya.cmds', 'maya.mel'):\n"
            "    sys.modules.setdefault(name, types.ModuleType(name))\n"
            "sys.modules['maya'].cmds = sys.modules['maya.cmds']\n"
            "sys.modules['maya'].mel = sys.modules['maya.mel']\n"
            "import maya_uebridge.uassetexport\n"
            "leaked = [m for m in sys.modules if m.endswith('uebridge.vcs')\n"
            "          or m.endswith('uebridge.checkouts')]\n"
            "print('leaked:' + ';'.join(sorted(leaked)))\n")
        result = subprocess.run([sys.executable, "-c", script], cwd=plugin,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("leaked:\n", result.stdout + "\n", result.stdout)

    def test_the_module_imports_nothing_perforce_shaped(self):
        """Read as CODE, not as text: the docstring says "p4 edit" while
        explaining what this road skips, and that mention is the point."""
        import ast
        with open(uassetexport.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add("{0}.{1}".format(node.module or "",
                                                  alias.name))
        for name in imported:
            self.assertNotIn("vcs", name, name)
            self.assertNotIn("checkouts", name, name)

        names = {node.id for node in ast.walk(tree)
                 if isinstance(node, ast.Name)}
        names |= {node.attr for node in ast.walk(tree)
                  if isinstance(node, ast.Attribute)}
        for forbidden in ("vcs", "prepare_target", "run_p4", "fstat",
                          "checkout", "place", "add"):
            self.assertNotIn(forbidden, names, forbidden)


# ---------------------------------------------------------------------------
# the orchestration, with everything faked
# ---------------------------------------------------------------------------

class ExportToUasset(unittest.TestCase):
    """The order is the point: refusals first, then the dialog, then the
    export, then the flag, then the editor. A failed export must leave the
    uasset -- flag and all -- exactly as it was."""

    CONTENT = None   # set in setUp, a real temp dir

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.content = os.path.join(self.folder, "Content")
        self.uasset = records.uasset_path_of(REC.package, self.content)
        os.makedirs(os.path.dirname(self.uasset))
        with open(self.uasset, "w") as handle:
            handle.write("uasset")
        self.calls = []
        self.real = (uassetexport.animexport, uassetexport.animimport)
        uassetexport.animexport = self._FakeExport(self.calls)
        uassetexport.animimport = self._FakeImport()

    def tearDown(self):
        uassetexport.animexport, uassetexport.animimport = self.real
        import shutil
        try:
            os.chmod(self.uasset, 0o666)
        except OSError:
            pass
        shutil.rmtree(self.folder, ignore_errors=True)

    class _FakeExport(object):
        # the roads into Unreal pass animexport.UNREAL_LAYOUT (2026-09-25)
        UNREAL_LAYOUT = "plain"

        def __init__(self, calls, fail=False):
            self.calls = calls
            self.fail = fail
            self.layouts = []

        def resolve_root(self):
            return "|root"

        def export_hierarchy(self, path, root=None, layout=None):
            self.layouts.append(layout)
            self.calls.append(("export", path, root))
            if self.fail:
                raise RuntimeError("the exporter wrote nothing")
            return {"root": "root", "joints": 93, "start": 0, "end": 60,
                    "warning": ""}

        def export_line(self, name, info):
            return "{0}: {1} bones".format(name, info["joints"])

    class _FakeImport(object):
        def fps_warning(self, clip, scene):
            return ""

        def scene_fps(self):
            return 30.0

    def _run(self, answer=True, run_script=None):
        def confirm(message):
            self.calls.append(("confirm", message))
            return answer

        def script(source, out, project=None):
            self.calls.append(("editor", project))
            return {"ok": True, "saved": True, "frames": 60}

        return uassetexport.export_to_uasset(
            REC, self.content, "Atone", self.folder,
            asks={"confirm": confirm,
                  "run_script": run_script or script})

    def test_the_happy_path_asks_then_exports_then_asks_the_editor(self):
        line = self._run()
        kinds = [call[0] for call in self.calls]
        self.assertEqual(kinds, ["confirm", "export", "editor"])
        self.assertIn("93 bones", line)
        self.assertIn("saved", line)

    def test_the_editor_is_pinned_to_the_chosen_project(self):
        self._run()
        self.assertIn(("editor", "Atone"), self.calls)

    def test_cancel_does_nothing_at_all(self):
        line = self._run(answer=False)
        self.assertEqual([call[0] for call in self.calls], ["confirm"])
        self.assertIn(REC.name, line)
        self.assertIn("untouched", line)

    def test_the_fbx_goes_to_the_folder_it_was_handed(self):
        self._run()
        export = [c for c in self.calls if c[0] == "export"][0]
        self.assertEqual(os.path.dirname(export[1]), self.folder)
        self.assertTrue(export[1].endswith(".uasset.fbx"))

    def test_the_resolved_root_is_passed_to_the_exporter(self):
        """Resolved once, before the dialog, and reused -- or the dialog
        could name one skeleton and the export take another."""
        self._run()
        export = [c for c in self.calls if c[0] == "export"][0]
        self.assertEqual(export[2], "|root")

    def test_a_read_only_uasset_is_cleared_and_reported(self):
        os.chmod(self.uasset, 0o444)
        line = self._run()
        self.assertFalse(uassetexport.is_read_only(self.uasset))
        self.assertIn("read-only cleared", line)

    def test_the_dialog_warns_about_the_flag_before_clearing_it(self):
        os.chmod(self.uasset, 0o444)
        self._run()
        message = [c for c in self.calls if c[0] == "confirm"][0][1]
        self.assertIn("read-only", message)

    def test_a_failed_export_leaves_the_flag_on(self):
        os.chmod(self.uasset, 0o444)
        uassetexport.animexport = self._FakeExport(self.calls, fail=True)
        with self.assertRaises(RuntimeError):
            self._run()
        self.assertTrue(uassetexport.is_read_only(self.uasset))
        self.assertNotIn("editor", [call[0] for call in self.calls])

    def test_an_undecidable_skeleton_refuses_before_the_dialog(self):
        class NoRoot(self._FakeExport):
            def resolve_root(self):
                raise RuntimeError("two skeletons - select one")
        uassetexport.animexport = NoRoot(self.calls)
        line = self._run()
        self.assertIn("select one", line)
        self.assertEqual(self.calls, [])

    def test_a_missing_uasset_refuses_before_the_dialog(self):
        os.remove(self.uasset)
        line = self._run()
        self.assertIn(".uasset", line)
        self.assertEqual(self.calls, [])

    def test_no_content_dir_refuses_before_the_dialog(self):
        line = uassetexport.export_to_uasset(
            REC, "", "Atone", self.folder,
            asks={"confirm": lambda message: True})
        self.assertEqual(line, uassetexport.NO_CONTENT_DIR)

    def test_no_record_refuses_before_the_dialog(self):
        line = uassetexport.export_to_uasset(
            None, self.content, "Atone", self.folder,
            asks={"confirm": lambda message: True})
        self.assertEqual(line, uassetexport.NO_SELECTION)


if __name__ == "__main__":
    unittest.main()

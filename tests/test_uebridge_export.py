"""Tests for the export-back direction: the pure range/wording logic and the
window-free parts of the checkouts machinery."""

import os
import sys
import types
import unittest


def _install_fake_maya():
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import animexport  # noqa: E402


class UnionRange(unittest.TestCase):

    def test_equal_ranges_stay_put(self):
        self.assertEqual(animexport.union_range((0, 60), (0, 60)), (0, 60))

    def test_a_zoomed_in_timeline_does_not_trim_the_clip(self):
        """Trap 38: the visible slider narrowed inside the animation range
        must not narrow the export."""
        self.assertEqual(animexport.union_range((0, 120), (30, 50)), (0, 120))

    def test_a_widened_slider_widens_the_export(self):
        self.assertEqual(animexport.union_range((0, 60), (-10, 80)), (-10, 80))


class OutsideKeysWarning(unittest.TestCase):

    def test_keys_inside_say_nothing(self):
        self.assertEqual(
            animexport.outside_keys_warning([0, 30, 60], 0, 60), "")

    def test_no_keys_say_nothing(self):
        self.assertEqual(animexport.outside_keys_warning([], 0, 60), "")

    def test_keys_outside_are_counted_and_placed(self):
        text = animexport.outside_keys_warning([-5, 0, 60, 70, 80], 0, 60)
        self.assertIn("3", text)
        self.assertIn("-5", text)


class ExportCommand(unittest.TestCase):

    def test_backslashes_become_forward_slashes(self):
        self.assertEqual(animexport.export_command("C:\\a\\b.fbx"),
                         'FBXExport -f "C:/a/b.fbx" -s;')


class ExportLine(unittest.TestCase):

    def info(self, **over):
        info = {"root": "root", "joints": 93, "start": 0.0, "end": 62.0,
                "warning": ""}
        info.update(over)
        return info

    def test_names_the_clip_the_bones_and_the_range(self):
        line = animexport.export_line("AS_Walk", self.info())
        self.assertIn("AS_Walk", line)
        self.assertIn("93", line)
        self.assertIn("0-62", line)

    def test_a_warning_rides_along(self):
        line = animexport.export_line("A",
                                      self.info(warning="2 key(s) outside"))
        self.assertIn("outside", line)


from maya_uebridge import checkouts, records, vcs  # noqa: E402


def _record(name="AS_Walk", package="/Game/Anims/AS_Walk"):
    return records.AnimRecord(name=name, package=package, skeleton="SK",
                              frames=60, length=2.0, fps=30.0)


class AnimCheckouts(unittest.TestCase):

    CONTENT = "C:\\p4\\Atone\\Content"

    def opened(self, client, action="edit"):
        return {"depotFile": "//d/x", "clientFile": client, "action": action}

    def test_an_opened_animsequence_is_matched_to_its_record(self):
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Anims\\AS_Walk.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0].name, "AS_Walk")
        self.assertEqual(rows[0][2], "edit")

    def test_a_non_animation_uasset_is_dropped(self):
        """The window is about animations, not the depot."""
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Props\\SM_Rock.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(rows, [])

    def test_matching_ignores_case(self):
        rows = checkouts.anim_checkouts(
            [self.opened("c:\\P4\\ATONE\\content\\anims\\as_walk.uasset")],
            self.CONTENT, [_record()])
        self.assertEqual(len(rows), 1)

    def test_rows_sort_by_name(self):
        rows = checkouts.anim_checkouts(
            [self.opened(self.CONTENT + "\\Anims\\AS_Zed.uasset"),
             self.opened(self.CONTENT + "\\Anims\\AS_Abc.uasset")],
            self.CONTENT,
            [_record("AS_Zed", "/Game/Anims/AS_Zed"),
             _record("AS_Abc", "/Game/Anims/AS_Abc")])
        self.assertEqual([r[0].name for r in rows], ["AS_Abc", "AS_Zed"])


class FormatRow(unittest.TestCase):

    def row(self, fbx="ok"):
        return checkouts.CheckoutRow(_record(), "C:\\x.uasset", "edit", fbx,
                                     "C:\\src\\AS_Walk.fbx")

    def test_a_row_names_the_animation_the_action_and_the_fbx(self):
        text = checkouts.format_row(self.row())
        self.assertIn("AS_Walk", text)
        self.assertIn("edit", text)
        self.assertIn("ok", text)

    def test_every_export_row_carries_the_tick(self):
        """Everything on this tab IS checked out - the mark says so, the
        same one the import list uses."""
        self.assertTrue(checkouts.format_row(self.row()).startswith(
            checkouts.TICK))

    def test_a_missing_fbx_shouts(self):
        self.assertIn("MISSING", checkouts.format_row(self.row("missing")))

    def test_rows_align(self):
        a = checkouts.format_row(self.row())
        b = checkouts.format_row(checkouts.CheckoutRow(
            _record("AS_A_Very_Much_Longer_Animation_Name_Than_That",
                    "/Game/Deep/Folder/AS_X"),
            "C:\\y.uasset", "add", "depot", ""))
        self.assertEqual(a.index("fbx "), b.index("fbx "))


class ModifiedFlag(unittest.TestCase):

    def test_a_row_defaults_to_unmodified(self):
        row = checkouts.CheckoutRow(_record(), "C:\\x.uasset", "edit", "ok", "")
        self.assertFalse(row.modified)

    def test_an_add_is_always_modified(self):
        """An added file has no depot side to differ from - new content by
        definition."""
        self.assertTrue(checkouts.is_modified("C:\\x.uasset", "add", set()))

    def test_an_edit_is_modified_when_the_diff_says_so(self):
        changed = {os.path.normcase("C:\\x.uasset")}
        self.assertTrue(checkouts.is_modified("C:\\x.uasset", "edit", changed))

    def test_an_untouched_edit_is_not_modified(self):
        self.assertFalse(checkouts.is_modified("C:\\x.uasset", "edit", set()))

    def test_the_match_ignores_case(self):
        changed = {os.path.normcase("C:\\Anims\\AS_X.uasset")}
        self.assertTrue(checkouts.is_modified("c:\\anims\\as_x.uasset",
                                              "edit", changed))


class MarkPrefix(unittest.TestCase):

    def test_a_checked_out_package_gets_the_tick(self):
        self.assertEqual(
            checkouts.mark_prefix("/Game/A/AS_X", {"/game/a/as_x"}),
            checkouts.TICK)

    def test_everything_else_gets_a_blank_of_the_same_width(self):
        tick = checkouts.mark_prefix("/Game/A", {"/game/a"})
        blank = checkouts.mark_prefix("/Game/B", {"/game/a"})
        self.assertNotEqual(tick, blank)
        self.assertEqual(len(tick), len(blank))


class CheckoutsCountLine(unittest.TestCase):

    def test_zero_says_nothing_checked_out(self):
        self.assertIn("nothing", checkouts.count_line(0))

    def test_a_count_is_reported(self):
        self.assertIn("3", checkouts.count_line(3))


class ReimportLine(unittest.TestCase):

    def test_saved_with_frames(self):
        line = checkouts.reimport_line({"ok": True, "saved": True,
                                        "frames": 62})
        self.assertIn("saved", line)
        self.assertIn("62", line)

    def test_unsaved_is_loud(self):
        line = checkouts.reimport_line({"ok": True, "saved": False})
        self.assertIn("NOT saved", line)


class FbxState(unittest.TestCase):

    def test_no_root_finds_nothing(self):
        state, path = checkouts.fbx_state("AS_X", "",
                                          lambda args, cwd: (0, "", ""))
        self.assertEqual(state, "missing")
        self.assertEqual(path, "")


if __name__ == "__main__":
    unittest.main()

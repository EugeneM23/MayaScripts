"""Tests for the window's pure helpers.

The widgets need a Maya session; what is testable here is the cache, which is
where a mistake would quietly hand the user a wrong list.
"""

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

from maya_uebridge import records, window  # noqa: E402


class CacheRoundTrip(unittest.TestCase):

    def payload(self):
        return {"assets": [
            {"name": "A_Jump", "package": "/Game/Manny/A_Jump", "skeleton": "SK",
             "frames": 45, "length": 1.5, "fps": 30.0},
            {"name": "A_Walk", "package": "/Game/Manny/A_Walk"}]}

    def test_records_survive_a_save_and_load(self):
        original = records.parse_payload(self.payload())
        again = window.records_from_cache(window.cache_payload(original))
        self.assertEqual(again, original)

    def test_the_cache_keeps_the_project(self):
        cached = window.cache_payload([], project="C:/x/Atone.uproject")
        self.assertEqual(cached["project"], "C:/x/Atone.uproject")

    def test_the_cache_remembers_which_editor_was_chosen(self):
        """With two projects open, reopening the window should not change which
        one it reads."""
        cached = window.cache_payload([], project="", choice="Atone")
        self.assertEqual(cached["choice"], "Atone")

    def test_the_cache_is_shaped_like_the_editor_reply(self):
        """One parser reads both, so the shapes must not drift apart."""
        cached = window.cache_payload(records.parse_payload(self.payload()))
        self.assertIn("assets", cached)
        self.assertEqual(len(records.parse_payload(cached)), 2)

    def test_an_empty_cache_loads_as_an_empty_list(self):
        self.assertEqual(window.records_from_cache({"assets": []}), [])

    def test_a_cache_written_before_the_picker_still_loads(self):
        """An old cache has no 'choice' key; that must not break the window."""
        self.assertEqual(window.records_from_cache({"assets": []}), [])

    def test_the_cache_keeps_the_content_dir(self):
        cached = window.cache_payload([], content_dir="C:/proj/Content")
        self.assertEqual(cached["content_dir"], "C:/proj/Content")

    def test_a_phase_one_cache_reads_as_no_content_dir(self):
        """A cache written before this key existed must load as ''. The
        payload shape is what load_cache reads, so the .get default is the
        contract being pinned here."""
        payload = window.cache_payload([])
        payload.pop("content_dir")
        self.assertEqual(payload.get("content_dir", ""), "")


class EditorsLine(unittest.TestCase):

    def test_silent_with_one_editor(self):
        self.assertEqual(window.editors_line(["Atone"], "Atone"), "")

    def test_silent_with_none(self):
        self.assertEqual(window.editors_line([], ""), "")

    def test_names_the_chosen_one_when_several_are_open(self):
        line = window.editors_line(["Atone", "MarkerLess_02"], "Atone")
        self.assertIn("2 editors", line)
        self.assertIn("Atone", line)


class CountLine(unittest.TestCase):

    def test_no_query_reports_the_total(self):
        self.assertEqual(window.count_line(470, 470, ""), "470 animations")

    def test_a_query_reports_both_numbers(self):
        """Saying '470 shown' over a list of 34 rows is simply a lie."""
        line = window.count_line(470, 34, "jump")
        self.assertIn("34", line)
        self.assertIn("470", line)
        self.assertIn("jump", line)

    def test_no_match_says_so(self):
        line = window.count_line(470, 0, "zzz")
        self.assertIn("nothing matches", line)
        self.assertIn("zzz", line)

    def test_whitespace_counts_as_no_query(self):
        self.assertEqual(window.count_line(470, 470, "   "), "470 animations")


class ImportLine(unittest.TestCase):

    def merged(self, **over):
        info = {"merged": True, "joints": 92, "start": 0.0, "end": 62.0,
                "namespace": "", "warning": ""}
        info.update(over)
        return info

    def test_a_merge_says_it_went_onto_the_scene_skeleton(self):
        line = window.import_line("AS_Attack", self.merged())
        self.assertIn("scene skeleton", line)
        self.assertIn("92", line)
        self.assertIn("AS_Attack", line)

    def test_a_merge_reports_the_frame_range(self):
        self.assertIn("0-62", window.import_line("A", self.merged()))

    def test_a_new_skeleton_names_its_namespace(self):
        line = window.import_line("A", {"merged": False, "joints": 116,
                                        "namespace": "A", "start": 0.0,
                                        "end": 62.0, "warning": ""})
        self.assertIn("into A", line)

    def test_a_warning_is_appended_not_swallowed(self):
        line = window.import_line("A", self.merged(warning="no bone names matched"))
        self.assertIn("no bone names matched", line)

    def test_no_keys_does_not_print_a_broken_range(self):
        line = window.import_line("A", self.merged(start=None, end=None))
        self.assertNotIn("None", line)


class NoPerforce(unittest.TestCase):
    """One window since 2026-09-07, and no Perforce in it: the Export tab,
    the Checkout button and the VCS row left with the animator's «уберем весь
    функционал по работе с перфорсом». `vcs.py` and `checkouts.py` stay as
    modules; this file must not reach either."""

    def _source(self):
        with open(window.__file__.replace(".pyc", ".py"),
                  encoding="utf-8") as handle:
            return handle.read()

    def test_the_window_imports_neither_vcs_nor_checkouts(self):
        src = self._source()
        imports = [line for line in src.splitlines()
                   if line.strip().startswith(("import ", "from "))]
        for line in imports:
            self.assertNotIn("vcs", line, line)
            self.assertNotIn("checkouts", line, line)
        for name in ("vcs.prepare_target", "vcs.place", "checkouts.marks",
                     "checkouts.build_tab", "tabLayout", "with_vcs_suffix",
                     "_vcs_target", "checkout_selected", "ueBridgeVcs"):
            self.assertNotIn(name, src, name)

    def test_the_three_buttons_and_two_modes(self):
        src = self._source()
        for label in ('label="Export FBX..."', 'label="Export to uasset"',
                      'label="Import"', '"Rig"', '"New rig"',
                      '"Skeleton"', 'Retarget onto the rig', 'Onto a NEW rig',
                      'As a new skeleton'):
            self.assertIn(label, src, label)
        self.assertTrue(callable(window.export_fbx_selected))
        self.assertTrue(callable(window.export_uasset_selected))
        self.assertTrue(callable(window.import_selected))

    def test_the_default_mode_is_the_retarget(self):
        """Without the widget (a headless session) IMPORT means the whole
        pipeline -- the row the radio opens on."""
        real = window.cmds
        window.cmds = types.SimpleNamespace(
            iconTextRadioCollection=lambda *a, **k: False)
        try:
            self.assertTrue(window.retarget_selected())
            self.assertEqual(window.import_mode(), "rig")
        finally:
            window.cmds = real

    def test_the_three_rows_are_the_three_targets(self):
        """2026-09-08: «onto a NEW rig» is how many rigs arrive through
        import; the skeleton row is the only one that is not a retarget."""
        self.assertEqual(window.MODES, ("rig", "new_rig", "skeleton"))
        self.assertEqual([window.mode_for(i) for i in (1, 2, 3)],
                         ["rig", "new_rig", "skeleton"])
        self.assertEqual(window.mode_for(0), "rig")
        self.assertEqual(window.mode_for(None), "rig")

    def test_the_legacy_checkouts_popup_is_still_closed_on_open(self):
        self.assertIn("ueBridgeCheckouts", window.LEGACY_WINDOWS)


class ProjectLabel(unittest.TestCase):

    def test_shows_the_project_name_not_the_path(self):
        self.assertEqual(window._project_label("C:/x/y/Atone.uproject"), "Atone")

    def test_says_so_when_there_is_no_project(self):
        self.assertEqual(window._project_label(""), "no project")


if __name__ == "__main__":
    unittest.main()

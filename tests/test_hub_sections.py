"""The four tools that became hub sections without a window test of their
own, plus the two new sections (Retarget, Hotkeys): each `build_panel`
lands its named controls in the current layout, opens no window, and
`show_window` asks the hub for its own section.

Spec: docs/superpowers/specs/2026-09-17-skeldar-hub-design.md
"""

import unittest

import maya_hub
import maya_hotkeys
import maya_hubstyle
import maya_rig_retarget as rr
from maya_scenesetup import window as scenesetup
from maya_uebridge import window as uebridge

from tests.uifakes import FakeUiCmds


def _hub_asked(show_window):
    """Run `show_window` against a recording hub; the keys it asked for."""
    asked = []
    saved = maya_hub.show
    maya_hub.show = lambda key=None: asked.append(key) or "hub"
    try:
        result = show_window()
    finally:
        maya_hub.show = saved
    return result, asked


class SceneSetup(unittest.TestCase):
    """Two sections of one module: Characters, then Weapons."""

    def setUp(self):
        self.saved = (scenesetup.cmds, scenesetup.refresh,
                      scenesetup._advance_swatch, scenesetup._bound_root)
        self.fake = FakeUiCmds()
        scenesetup.cmds = self.fake
        #  The scene reads after the build are the module's own and not
        #  under test here.
        scenesetup.refresh = lambda: None
        scenesetup._advance_swatch = lambda name: None
        scenesetup._bound_root = lambda: None
        maya_hubstyle.take_marks()
        scenesetup.build_characters_panel()
        self.after_characters = list(self.fake.children)
        scenesetup.build_weapons_panel()
        self.marks = maya_hubstyle.take_marks()
        self._unnamed = [n for n in self.fake.children
                         if n.startswith("button")]

    def tearDown(self):
        (scenesetup.cmds, scenesetup.refresh, scenesetup._advance_swatch,
         scenesetup._bound_root) = self.saved

    def test_no_window_and_stretching_columns(self):
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(self.fake.column.get("adjustableColumn"))

    def test_characters_holds_the_character_controls_and_its_own_line(self):
        for name in (scenesetup._BOUND, scenesetup._CHARACTER,
                     scenesetup._CHARACTER_COLOUR, scenesetup._CHARACTER_STATUS):
            self.assertIn(name, self.after_characters, name)

    def test_characters_has_a_camera_setup_button(self):
        """2026-09-18: the retarget's camera step, by hand, on camera_root."""
        labels = [c[2].get("label") for c in self.fake.calls if c[0] == "button"]
        self.assertIn("Camera Setup", labels)
        self.assertLess(labels.index("Add Character"), labels.index("Camera Setup"))
        for name in (scenesetup._MENU, scenesetup._STATUS, scenesetup._ROTATE):
            self.assertNotIn(name, self.after_characters, name)

    def test_weapons_holds_the_weapon_controls_and_its_own_line(self):
        weapons = self.fake.children[len(self.after_characters):]
        for name in (scenesetup._MENU, scenesetup._CUSTOM, scenesetup._ROTATE,
                     scenesetup._TRANSLATE, scenesetup._WEAPON_COLOUR,
                     scenesetup._STATUS):
            self.assertIn(name, weapons, name)
        self.assertNotIn(scenesetup._CHARACTER, weapons)

    def test_the_two_status_lines_are_different_controls(self):
        self.assertNotEqual(scenesetup._STATUS, scenesetup._CHARACTER_STATUS)

    def test_character_presses_report_on_the_characters_line(self):
        scenesetup._status("hello", scenesetup._CHARACTER_STATUS)
        scenesetup._status("world")
        edits = [(c[1][0], c[2]["label"]) for c in self.fake.calls
                 if c[0] == "text" and c[2].get("edit")]
        self.assertEqual(edits[-2:], [(scenesetup._CHARACTER_STATUS, "hello"),
                                      (scenesetup._STATUS, "world")])

    def test_is_open_follows_the_weapons_status_control(self):
        self.assertTrue(scenesetup.is_open())
        self.fake.children.remove(scenesetup._STATUS)
        self.assertFalse(scenesetup.is_open())

    def test_show_window_and_show_weapons_open_their_sections(self):
        result, asked = _hub_asked(scenesetup.show_window)
        self.assertEqual((result, asked), ("hub", ["characters"]))
        result, asked = _hub_asked(scenesetup.show_weapons)
        self.assertEqual((result, asked), ("hub", ["weapons"]))
        self.assertEqual(maya_hub.section("characters").module,
                         "maya_scenesetup.window")
        self.assertEqual(maya_hub.section("weapons").builder,
                         "build_weapons_panel")

    def _marks(self):
        return dict((m.name, m) for m in self.marks)

    def test_the_character_line_is_the_card_s_subtitle(self):
        self.assertEqual(self._marks()[scenesetup._BOUND].role, "subtitle")

    def test_the_character_dropdown_needs_no_label(self):
        menus = [c for c in self.fake.calls if c[0] == "optionMenu"
                 and c[1] == (scenesetup._CHARACTER,) and not c[2].get("edit")]
        self.assertNotIn("label", menus[0][2])

    def test_eight_palette_dots_per_colour_row(self):
        from maya_scenesetup import colour as colouring
        marks = self._marks()
        for pattern in (scenesetup._CHARACTER_DOT, scenesetup._WEAPON_DOT):
            for index, entry in enumerate(colouring.PALETTE):
                mark = marks[pattern.format(index)]
                self.assertEqual(mark.role, "swatch")
                self.assertEqual(mark.colour, maya_hubstyle.hex_of(entry.rgb))

    def test_a_dot_sets_its_swatch(self):
        from maya_scenesetup import colour as colouring
        dot = [c for c in self.fake.calls if c[0] == "button"
               and c[1] == (scenesetup._WEAPON_DOT.format(2),)][0]
        dot[2]["command"]()
        edits = [c for c in self.fake.calls if c[0] == "colorSliderGrp"
                 and c[1] == (scenesetup._WEAPON_COLOUR,) and c[2].get("edit")]
        self.assertEqual(tuple(edits[-1][2]["rgbValue"]),
                         tuple(colouring.PALETTE[2].rgb))

    def test_the_swatches_show_only_the_swatch_in_the_skin(self):
        marks = self._marks()
        for name in (scenesetup._CHARACTER_COLOUR, scenesetup._WEAPON_COLOUR):
            self.assertEqual(marks[name].role, "swatchonly")

    def test_one_primary_action_per_section(self):
        roles = self._button_roles()
        self.assertEqual(roles["Add Character"], ("primary", "plus"))
        self.assertEqual(roles["Camera Setup"], ("secondary", "camera"))
        self.assertEqual(roles["Add"], ("primary", "plus"))
        self.assertEqual(roles["Remove Weapon"], ("danger", "trash"))
        primaries = [label for label, (role, _i) in roles.items()
                     if role == "primary"]
        self.assertEqual(sorted(primaries), ["Add", "Add Character"])

    def test_recolour_is_a_brush_tool_on_both(self):
        tools = [m for m in self.marks if m.role == "tool"
                 and m.icon == "brush"]
        self.assertEqual(len(tools), 2)

    def test_add_and_remove_share_a_row(self):
        index = self._created_index()
        add, remove = index["Add"], index["Remove Weapon"]
        rows = [i for i, c in enumerate(self.fake.calls) if c[0] == "rowLayout"]
        row = max(i for i in rows if i < add)
        self.assertLess(row, remove)
        between = [c for c in self.fake.calls[add:remove]
                   if c[0] == "setParent"]
        self.assertEqual(between, [])

    def test_the_status_lines_are_marked(self):
        marks = self._marks()
        for name in (scenesetup._STATUS, scenesetup._CHARACTER_STATUS):
            self.assertEqual(marks[name].role, "status")

    def test_the_folder_button_fills_the_fbx_field(self):
        self.assertEqual(self._marks()[scenesetup._BROWSE].icon, "folder")
        saved = scenesetup.custom_changed
        changed = []
        scenesetup.custom_changed = lambda: changed.append(True)
        try:
            self.fake.fileDialog2 = lambda **kw: ["C:/weapons/Axe.fbx"]
            self.assertEqual(scenesetup.browse_fbx(), "C:/weapons/Axe.fbx")
            edits = [c for c in self.fake.calls if c[0] == "textFieldGrp"
                     and c[2].get("edit")]
            self.assertEqual(edits[-1][2]["text"], "C:/weapons/Axe.fbx")
            self.assertEqual(changed, [True])
            self.fake.fileDialog2 = lambda **kw: None
            self.assertIsNone(scenesetup.browse_fbx())
            self.assertEqual(changed, [True])
        finally:
            scenesetup.custom_changed = saved

    def _created_index(self):
        return dict((c[2].get("label"), i) for i, c in
                    enumerate(self.fake.calls) if c[0] == "button"
                    and not c[2].get("edit") and c[2].get("label"))

    def _button_roles(self):
        """label -> (role, icon) for the marked buttons, by the name the
        fake handed back for each creation."""
        marks = self._marks()
        names = [c for c in self.fake.calls if c[0] == "button"
                 and not c[2].get("edit")]
        out = {}
        for call in names:
            label = call[2].get("label")
            name = call[1][0] if call[1] else None
            if name is None:
                #  unnamed: the fake's own counter name, in creation order
                name = self._unnamed.pop(0)
            if name in marks and label:
                out[label] = (marks[name].role, marks[name].icon)
        return out

    def test_the_standalone_window_is_gone(self):
        self.assertFalse(hasattr(scenesetup, "WINDOW"))
        self.assertFalse(hasattr(scenesetup, "build_panel"))
        self.assertIn("mayaSceneSetupWindow", maya_hub.LEGACY_WINDOWS)
        self.assertIn("mayaWeaponsWindow", maya_hub.LEGACY_WINDOWS)


class UeBridge(unittest.TestCase):

    def setUp(self):
        self.saved = (uebridge.cmds, uebridge.load_cache,
                      uebridge._repopulate, uebridge.fill_project_menu)
        self.fake = FakeUiCmds()
        uebridge.cmds = self.fake
        uebridge.load_cache = lambda: ([], "", "", "")
        uebridge._repopulate = lambda: []
        uebridge.fill_project_menu = lambda labels: None
        maya_hubstyle.take_marks()
        self.form = uebridge.build_panel()
        self.marks = maya_hubstyle.take_marks()

    def tearDown(self):
        (uebridge.cmds, uebridge.load_cache, uebridge._repopulate,
         uebridge.fill_project_menu) = self.saved

    def test_no_window(self):
        self.assertEqual(self.fake.windows, {})

    def test_rows_not_a_form_and_the_list_has_a_height(self):
        """Measured 2026-09-17: a formLayout inside the hub's column
        reported a 1128 px minimum width whatever its children were told,
        so the panel is rows in a column and only the list is sized."""
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "formLayout"])
        lists = [c for c in self.fake.calls if c[0] == "textScrollList"
                 and not c[2].get("edit") and not c[2].get("query")]
        self.assertEqual(lists[0][2].get("height"), uebridge.LIST_HEIGHT)
        self.assertGreaterEqual(uebridge.LIST_HEIGHT, 200)

    def test_the_import_mode_is_three_short_segments(self):
        """2026-09-28: the vertical radios (three long labels in a row
        wanted 670 px) became Rig / New rig / Skeleton, the long text the
        tooltip."""
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "radioButtonGrp"])
        segments = [c for c in self.fake.calls if c[0] == "iconTextRadioButton"
                    and not c[2].get("edit")]
        self.assertEqual([c[2]["label"] for c in segments],
                         ["Rig", "New rig", "Skeleton"])
        self.assertEqual([c[1][0] for c in segments],
                         [uebridge.mode_button(m) for m in uebridge.MODES])
        self.assertTrue(segments[0][2]["select"])
        for call in segments:
            self.assertGreater(len(call[2]["annotation"]), 40)
        marks = dict((m.name, m) for m in self.marks)
        for call in segments:
            self.assertEqual(marks[call[1][0]].role, "segment")

    def test_import_is_the_primary_action(self):
        marks = [m for m in self.marks if m.role == "primary"]
        self.assertEqual([m.icon for m in marks], ["download"])
        labels = [c[2]["label"] for c in self.fake.calls if c[0] == "button"
                  and not c[2].get("edit")]
        self.assertIn("Import", labels)
        self.assertIn("Export FBX...", labels)
        self.assertIn("Export to uasset", labels)

    def test_the_connection_line_is_the_card_s_subtitle(self):
        marks = dict((m.name, m) for m in self.marks)
        self.assertEqual(marks[uebridge._HEADER].role, "subtitle")
        self.assertEqual(marks[uebridge._STATUS].role, "status")

    def test_the_status_line_wraps(self):
        texts = [c for c in self.fake.calls
                 if c[0] == "text" and c[1] == (uebridge._STATUS,)]
        self.assertTrue(texts[0][2].get("wordWrap"))

    def test_the_named_controls_exist(self):
        for name in (uebridge._LIST, uebridge._SEARCH, uebridge._STATUS,
                     uebridge._HEADER, uebridge._TIMELINE, uebridge._PROJECT):
            self.assertIn(name, self.fake.children, name)
        #  the mode is a collection of segments now (2026-09-28)
        self.assertIn(("iconTextRadioCollection", (uebridge._MODE,), {}),
                      self.fake.calls)
        self.assertTrue(uebridge.is_open())

    def test_show_window_opens_the_hub_on_its_section(self):
        result, asked = _hub_asked(uebridge.show_window)
        self.assertEqual((result, asked), ("hub", ["uebridge"]))

    def test_the_standalone_window_is_legacy_now(self):
        self.assertFalse(hasattr(uebridge, "WINDOW"))
        self.assertIn("ueAnimBridgeWindow", uebridge.LEGACY_WINDOWS)
        for name in uebridge.LEGACY_WINDOWS:
            self.assertIn(name, maya_hub.LEGACY_WINDOWS)


class Retarget(unittest.TestCase):

    def setUp(self):
        self.saved = (rr.cmds, rr.retarget)
        self.fake = FakeUiCmds()
        rr.cmds = self.fake
        rr.retarget = lambda *a, **k: "Manny_Rig: connected 74  |  baked\nmore"
        rr.build_panel()

    def tearDown(self):
        rr.cmds, rr.retarget = self.saved

    def test_a_button_and_a_status_line_no_window(self):
        self.assertEqual(self.fake.windows, {})
        self.assertIn(rr.STATUS, self.fake.children)
        buttons = [c for c in self.fake.calls if c[0] == "button"]
        self.assertEqual(buttons[0][2]["label"], "Retarget")
        self.assertTrue(rr.is_open())

    def test_the_button_runs_the_shelf_action_and_reports_on_the_line(self):
        buttons = [c for c in self.fake.calls if c[0] == "button"]
        buttons[0][2]["command"]()
        edits = [c for c in self.fake.calls
                 if c[0] == "text" and c[1] == (rr.STATUS,) and c[2].get("edit")]
        self.assertEqual(edits[-1][2]["label"],
                         "Manny_Rig: connected 74  |  baked")

    def test_a_failure_lands_on_the_line_and_still_raises(self):
        def explode(*a, **k):
            raise RuntimeError("boom")
        rr.retarget = explode
        with self.assertRaises(RuntimeError):
            rr._press()
        edits = [c for c in self.fake.calls
                 if c[0] == "text" and c[1] == (rr.STATUS,) and c[2].get("edit")]
        self.assertEqual(edits[-1][2]["label"], "RuntimeError: boom")

    def test_show_window_opens_the_hub_on_its_section(self):
        result, asked = _hub_asked(rr.show_window)
        self.assertEqual((result, asked), ("hub", ["retarget"]))


class Hotkeys(unittest.TestCase):

    def setUp(self):
        self.saved = (maya_hotkeys.cmds, maya_hotkeys.is_active,
                      maya_hotkeys.shelf_button)
        self.fake = FakeUiCmds()
        maya_hotkeys.cmds = self.fake
        maya_hotkeys.is_active = lambda: False
        maya_hotkeys.shelf_button = lambda *a, **k: None
        maya_hotkeys.build_panel()

    def tearDown(self):
        (maya_hotkeys.cmds, maya_hotkeys.is_active,
         maya_hotkeys.shelf_button) = self.saved

    def _button_edits(self):
        return [c for c in self.fake.calls
                if c[0] == "button" and c[1] == (maya_hotkeys.PANEL_BUTTON,)
                and c[2].get("edit")]

    def test_the_toggle_reads_off_when_the_map_is_off(self):
        created = [c for c in self.fake.calls
                   if c[0] == "button" and c[1] == (maya_hotkeys.PANEL_BUTTON,)
                   and not c[2].get("edit")]
        self.assertEqual(created[0][2]["label"], "Hotkey map: OFF")
        self.assertFalse(created[0][2]["enableBackground"])
        self.assertTrue(maya_hotkeys.is_open())

    def test_paint_lights_the_panel_button_without_a_shelf(self):
        self.assertTrue(maya_hotkeys.paint(True))
        edit = self._button_edits()[-1][2]
        self.assertEqual(edit["label"], "Hotkey map: ON")
        self.assertTrue(edit["enableBackground"])
        self.assertEqual(edit["backgroundColor"], maya_hotkeys.ON_COLOUR)
        maya_hotkeys.paint(False)
        self.assertEqual(self._button_edits()[-1][2]["label"],
                         "Hotkey map: OFF")

    def test_paint_lights_the_skinned_hub_s_header(self):
        """2026-09-28: the header switch, when a skinned hub stands."""
        import sys
        import types
        painted = []
        hub = types.ModuleType("maya_hub")
        hub.is_skinned = lambda: True
        hub.paint_hotkeys = painted.append
        saved = sys.modules.get("maya_hub")
        sys.modules["maya_hub"] = hub
        try:
            self.fake.children.remove(maya_hotkeys.PANEL_BUTTON)
            self.assertTrue(maya_hotkeys.paint(True))
            hub.is_skinned = lambda: False
            self.assertFalse(maya_hotkeys.paint(False))
        finally:
            sys.modules["maya_hub"] = saved
        self.assertEqual(painted, [True])

    def test_paint_imports_no_hub(self):
        import sys
        saved = sys.modules.pop("maya_hub", None)
        try:
            maya_hotkeys.paint(True)
            self.assertNotIn("maya_hub", sys.modules)
        finally:
            if saved is not None:
                sys.modules["maya_hub"] = saved

    def test_paint_with_neither_button_is_quiet(self):
        self.fake.children.remove(maya_hotkeys.PANEL_BUTTON)
        self.assertFalse(maya_hotkeys.paint(True))
        self.assertEqual(self._button_edits(), [])

    def test_panel_label_is_pure(self):
        self.assertEqual(maya_hotkeys.panel_label(True), "Hotkey map: ON")
        self.assertEqual(maya_hotkeys.panel_label(False), "Hotkey map: OFF")

    def test_show_window_opens_the_hub_on_its_section(self):
        result, asked = _hub_asked(maya_hotkeys.show_window)
        self.assertEqual((result, asked), ("hub", ["hotkeys"]))


if __name__ == "__main__":
    unittest.main()

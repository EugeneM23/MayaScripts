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
from maya_scenesetup import armorpanel
from maya_scenesetup import catalog
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
                      scenesetup._attach_inventory, scenesetup._bound_root,
                      scenesetup._attach_grid)
        self.saved_bridge = (uebridge.cmds, uebridge.load_cache,
                             uebridge._repopulate, uebridge.fill_project_menu,
                             uebridge._attach_drag)
        self.fake = FakeUiCmds()
        scenesetup.cmds = self.fake
        #  the UE Bridge's rows are part of the Characters card (2026-10-01):
        #  one fake records both modules, in the order the card builds them
        uebridge.cmds = self.fake
        uebridge.load_cache = lambda: ([], "", "", "")
        uebridge._repopulate = lambda quiet=False: []
        uebridge.fill_project_menu = lambda labels: None
        uebridge._attach_drag = lambda: None
        #  ... and the Armor section's rows are part of the Inventory card
        self.saved_armor = (armorpanel.cmds, armorpanel._attach_tiles, armorpanel.refresh)
        armorpanel.cmds = self.fake
        armorpanel._attach_tiles = lambda: True
        armorpanel.refresh = lambda *a, **k: None
        #  The scene reads after the build are the module's own and not
        #  under test here; the portrait grid and the inventory are Qt's
        #  (test_chargrid, test_inventory).
        scenesetup.refresh = lambda: None
        scenesetup._bound_root = lambda: None
        self.attached, self.inventories = [], []
        scenesetup._attach_grid = lambda model, kind: (
            self.attached.append((model, kind)) or True)
        scenesetup._attach_inventory = lambda: (
            self.inventories.append(True) or True)
        maya_hubstyle.take_marks()
        scenesetup.build_characters_panel()
        self.after_characters = list(self.fake.children)
        scenesetup.build_weapons_panel()
        self.marks = maya_hubstyle.take_marks()
        self._unnamed = [n for n in self.fake.children
                         if n.startswith("button")]

    def tearDown(self):
        (scenesetup.cmds, scenesetup.refresh, scenesetup._attach_inventory,
         scenesetup._bound_root, scenesetup._attach_grid) = self.saved
        (uebridge.cmds, uebridge.load_cache, uebridge._repopulate,
         uebridge.fill_project_menu, uebridge._attach_drag) = self.saved_bridge
        armorpanel.cmds, armorpanel._attach_tiles, armorpanel.refresh = self.saved_armor

    def test_no_window_and_stretching_columns(self):
        self.assertEqual(self.fake.windows, {})
        self.assertTrue(self.fake.column.get("adjustableColumn"))

    def test_characters_holds_the_character_controls_and_its_own_line(self):
        for name in (scenesetup._BOUND, scenesetup._CHARACTER_STATUS):
            self.assertIn(name, self.after_characters, name)
        #  the portraits' placeholder, a columnLayout, and the grid laid over it
        self.assertIn(("columnLayout", (scenesetup._PORTRAITS,),
                       {"adjustableColumn": True}), self.fake.calls)
        self.assertEqual(len(self.attached), 1)
        self.assertNotIn(scenesetup._CHARACTER, self.after_characters)

    def test_no_colour_control_in_either_card(self):
        """2026-09-30: «все что касается покраски вынесем из меню» - the
        Colour section paints, characters the same morning, weapons the
        same evening («все что касается покраски оружия вынесем в
        покраску»)."""
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "colorSliderGrp"])
        dots = [c for c in self.fake.calls if c[0] == "button" and c[1]
                and "Dot" in str(c[1][0])]
        self.assertEqual(dots, [])
        self.assertFalse([m for m in self.marks if m.role in (
            "swatch", "swatchonly") or m.icon == "brush"])
        self.assertFalse(hasattr(scenesetup, "_CHARACTER_COLOUR"))
        self.assertFalse(hasattr(scenesetup, "recolour_character"))
        self.assertFalse(hasattr(scenesetup, "recolour_weapon"))

    def test_the_kind_switch_is_two_segments(self):
        self.assertIn(("iconTextRadioCollection", (scenesetup._KIND,), {}),
                      self.fake.calls)
        segments = [c for c in self.fake.calls if c[0] == "iconTextRadioButton"
                    and c[1] and c[1][0].startswith(scenesetup._KIND)]
        self.assertEqual([c[1][0] for c in segments],
                         [scenesetup.kind_segment("rig"),
                          scenesetup.kind_segment("skeleton")])
        self.assertEqual([c[2]["label"] for c in segments], ["Rig", "Skeleton"])
        marks = self._marks()
        for call in segments:
            self.assertEqual(marks[call[1][0]].role, "segment")
        self.assertIn("segments", [m.role for m in self.marks if m.layout])

    def test_the_dropdown_stands_only_without_the_grid(self):
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        scenesetup._attach_grid = lambda model, kind: False
        scenesetup.build_characters_panel()
        menus = [c for c in fake.calls if c[0] == "optionMenu"
                 and c[1] == (scenesetup._CHARACTER,)
                 and not (c[2].get("edit") or c[2].get("exists")
                          or c[2].get("query"))]
        self.assertEqual(len(menus), 1)
        self.assertNotIn("label", menus[0][2])

    def test_characters_has_a_camera_setup_button(self):
        """2026-09-18: the retarget's camera step, by hand, on camera_root.
        2026-10-08: the classic hub's button reads «Camera» (the skin's is an
        icon), its tooltip still says Camera Setup."""
        labels = [c[2].get("label") for c in self.fake.calls if c[0] == "button"]
        self.assertIn("Camera", labels)
        self.assertLess(labels.index("+ Import"), labels.index("Camera"))
        camera = [c for c in self.fake.calls if c[0] == "button"
                  and c[2].get("label") == "Camera"][0]
        self.assertTrue(camera[2]["annotation"].startswith("Camera Setup: "))
        for name in (scenesetup._WEAPONS_BOUND, scenesetup._STATUS):
            self.assertNotIn(name, self.after_characters, name)

    def _skin_build(self):
        """The Characters card built once more with the skin's arrangement
        (`set_skinning(True)`): (the fake, its marks)."""
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        uebridge.cmds = fake
        maya_hubstyle.take_marks()
        maya_hubstyle.set_skinning(True)
        try:
            scenesetup.build_characters_panel()
        finally:
            maya_hubstyle.set_skinning(False)
        return fake, maya_hubstyle.take_marks()

    def test_compact_top_row_is_kind_import_delete_camera(self):
        """2026-10-08, variant B: [Rig | Skeleton] [+ Import] [Delete]
        [Camera] are ONE row of four, ahead of the portraits."""
        rows = [i for i, c in enumerate(self.fake.calls) if c[0] == "rowLayout"
                and c[2].get("numberOfColumns") == 4]
        self.assertEqual(len(rows), 1)
        portraits = [i for i, c in enumerate(self.fake.calls)
                     if c[0] == "columnLayout" and c[1] == (scenesetup._PORTRAITS,)][0]
        inside = self.fake.calls[rows[0]:portraits]
        self.assertEqual([c[2]["label"] for c in inside if c[0] == "button"],
                         ["+ Import", "Delete", "Camera"])
        kind = [c[1][0] for c in inside if c[0] == "iconTextRadioButton"]
        self.assertEqual(kind, [scenesetup.kind_segment("rig"),
                                scenesetup.kind_segment("skeleton")])
        #  the segments' own row and the top row: two closes, nothing else
        self.assertEqual(len([c for c in inside if c[0] == "setParent"]), 2)
        self.assertEqual(self.fake.calls[rows[0]][2]["adjustableColumn"], 1)

    def test_the_skin_arrangement_is_icons_and_the_compact_heights(self):
        fake, marks = self._skin_build()
        buttons = [c[2] for c in fake.calls if c[0] == "button"
                   and not c[2].get("edit") and "label" in c[2]]
        self.assertEqual([b["label"] for b in buttons[:3]], ["Import", "", ""])
        #  + Import, Delete, Camera, then the bridge's Refresh (a field-high
        #  tool button), Import, FBX, uasset
        self.assertEqual([b["height"] for b in buttons],
                         [24, 24, 24, 20, 24, 24, 24])
        roles = [(m.role, m.icon) for m in marks if m.role in (
            "primary", "danger", "secondary") and m.icon]
        self.assertEqual(roles[:3], [("primary", "plus"), ("danger", "trash"),
                                     ("secondary", "camera")])

    def test_no_heading_in_the_skin(self):
        """2026-10-08: the compact card says nothing twice - Characters and
        Connect keep their headings in the classic hub only."""
        fake, marks = self._skin_build()
        self.assertFalse([m for m in marks if m.role == "heading"])
        texts = [c[1][0] for c in fake.calls if c[0] == "text" and c[1]
                 and not c[2].get("edit")]
        self.assertNotIn(scenesetup._CHARACTERS_HEADING, texts)
        self.assertNotIn(uebridge._HEADING, texts)

    def test_the_animation_list_has_a_grip(self):
        """2026-10-08: ten rows, a height grip under the list (the skin's);
        the classic list keeps LIST_HEIGHT and gets none applied."""
        marks = self._marks()
        self.assertEqual(marks[uebridge._LIST_GRIP].role, "grip")
        self.assertEqual(marks[uebridge._LIST_GRIP].target, uebridge._LIST)
        calls = [c[0] for c in self.fake.calls]
        lists = [i for i, c in enumerate(self.fake.calls)
                 if c[0] == "textScrollList" and c[1] == (uebridge._LIST,)
                 and not c[2].get("edit") and not c[2].get("query")]
        grip = [i for i, c in enumerate(self.fake.calls)
                if c[0] == "separator" and c[1] == (uebridge._LIST_GRIP,)]
        self.assertEqual(len(grip), 1)
        self.assertEqual(grip[0], lists[0] + 1)
        self.assertEqual(self.fake.calls[grip[0]][2]["height"], 8)
        self.assertIn("separator", calls)

    def test_the_status_writers_tell_the_hub(self):
        """2026-10-08: a status writer still writes its own control and
        tells the hub's one message line too."""
        heard = []

        def listener(control, text, viewport=False):
            heard.append((control, text))
        maya_hubstyle.listen(listener)
        try:
            scenesetup._status("hello", scenesetup._CHARACTER_STATUS)
            scenesetup._status("world")
            uebridge._status("bridge says")
        finally:
            maya_hubstyle.unlisten(listener)
        self.assertIn((scenesetup._CHARACTER_STATUS, "hello"), heard)
        self.assertIn((scenesetup._STATUS, "world"), heard)
        self.assertIn((uebridge._STATUS, "bridge says"), heard)

    def _weapons_calls(self):
        start = [i for i, c in enumerate(self.fake.calls) if c[0] == "text"
                 and c[1] == (scenesetup._WEAPONS_BOUND,)][0]
        return self.fake.calls[start:]

    def test_weapons_is_the_inventory_add_remove_and_its_line(self):
        """2026-09-30: «сам выбор оружия превратим в наш инвентарь ... как
        часть нашего меню»; the inventory is laid over the placeholder."""
        weapons = self.fake.children[len(self.after_characters):]
        for name in (scenesetup._WEAPONS_BOUND, scenesetup._STATUS):
            self.assertIn(name, weapons, name)
        self.assertIn(("columnLayout", (scenesetup._INVENTORY,),
                       {"adjustableColumn": True}), self._weapons_calls())
        self.assertEqual(self.inventories, [True])
        self.assertNotIn(scenesetup._CHARACTER, weapons)

    def test_no_dropdown_fbx_hand_row_grip_rows_or_inventory_button(self):
        calls = [c for c in self._weapons_calls()
                 if not (c[1] and str(c[1][0]).startswith(scenesetup._INVENTORY_TABS))]
        for kind in ("optionMenu", "textFieldGrp", "floatFieldGrp",
                     "colorSliderGrp", "iconTextRadioButton",
                     "iconTextRadioCollection"):
            self.assertFalse([c for c in calls if c[0] == kind], kind)
        labels = [c[2].get("label") for c in calls if c[0] == "button"]
        #  2026-10-01: Equip / Unequip in both sections of the Inventory card;
        #  2026-10-08: ONE pair on the tab row, acting on the shown tab
        self.assertEqual(labels, ["Equip", "Unequip"])

    def test_the_weapons_subtitle_names_the_character(self):
        self.assertEqual(self._marks()[scenesetup._WEAPONS_BOUND].role,
                         "subtitle")

    def test_without_qt_a_dropdown_and_the_hand_row_stand_in(self):
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        scenesetup._attach_inventory = lambda: False
        scenesetup.build_weapons_panel()
        menus = [c for c in fake.calls if c[0] == "optionMenu"
                 and c[1] == (scenesetup._WEAPON_MENU,)
                 and not (c[2].get("edit") or c[2].get("query"))]
        self.assertEqual(len(menus), 1)
        segments = [c[1][0] for c in fake.calls
                    if c[0] == "iconTextRadioButton" and c[1]
                    and not c[1][0].startswith(scenesetup._INVENTORY_TABS)]
        self.assertEqual(segments, [scenesetup.hand_segment("R"),
                                    scenesetup.hand_segment("L")])
        self.assertFalse([c for c in fake.calls if c[0] == "floatFieldGrp"])

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

    def test_one_primary_action_per_section(self):
        roles = self._button_roles()
        #  2026-10-01: the UE Bridge in the card; the same evening «Add
        #  Character на + Import (Вернем кнопке оранжевый цвет)» and the
        #  bridge's Import is «Import Animation» - a primary for each half
        self.assertEqual(roles["+ Import"], ("primary", "plus"))
        self.assertEqual(roles["Import Animation"], ("primary", "download"))
        self.assertNotIn("Add Character", roles)
        self.assertEqual(roles["Camera"], ("secondary", "camera"))
        #  the Inventory card: Equip (orange) + Unequip, ONE pair on the tab
        #  row since 2026-10-08 (they act on the shown tab)
        inventory = [(label, role, icon) for label, role, icon, _i in self._buttons()
                     if label in ("Equip", "Unequip")]
        self.assertEqual(inventory, [("Equip", "primary", "sword"),
                                     ("Unequip", "danger", "trash")])
        primaries = [label for label, role, _icon, _i in self._buttons()
                     if role == "primary"]
        self.assertEqual(primaries, ["+ Import", "Import Animation", "Equip"])

    def test_the_bridge_rows_follow_the_portraits_and_the_card_has_one_line(self):
        """2026-10-01 («UE bridge и character ... объеденить в одно окно»):
        who on top, the animations under them, one status line last. Since
        2026-10-08: the top row (kind, Import, Delete, Camera), the
        portraits, the Connect block, the line."""
        index = self._created_index()
        lists = [i for i, c in enumerate(self.fake.calls)
                 if c[0] == "textScrollList" and c[1] == (uebridge._LIST,)
                 and not c[2].get("edit") and not c[2].get("query")]
        line = [i for i, c in enumerate(self.fake.calls) if c[0] == "text"
                and c[1] == (scenesetup._CHARACTER_STATUS,) and not c[2].get("edit")]
        portraits = [i for i, c in enumerate(self.fake.calls)
                     if c[0] == "columnLayout" and c[1] == (scenesetup._PORTRAITS,)]
        self.assertEqual(len(lists), 1)
        self.assertEqual(len(line), 1)
        self.assertEqual(len(portraits), 1)
        self.assertLess(index["Camera"], portraits[0])
        self.assertLess(portraits[0], lists[0])
        self.assertLess(index["+ Import"], lists[0])
        self.assertLess(lists[0], index["Import Animation"])
        self.assertLess(index["Import Animation"], line[0])
        for name in (uebridge._LIST, uebridge._SEARCH, uebridge._HEADER,
                     uebridge._TIMELINE, uebridge._PROJECT):
            self.assertIn(name, self.after_characters, name)
        statuses = [m.name for m in self.marks if m.role == "status"]
        self.assertEqual(statuses, [scenesetup._CHARACTER_STATUS, scenesetup._STATUS])

    def test_the_import_button_reads_plus_import(self):
        """«Add Character на + Import»: the skin draws the plus icon beside
        «Import», the classic hub (no icons) spells «+ Import»."""
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        maya_hubstyle.set_skinning(True)
        try:
            scenesetup.build_characters_panel()
        finally:
            maya_hubstyle.set_skinning(False)
        labels = [c[2].get("label") for c in fake.calls
                  if c[0] == "button" and not c[2].get("edit")]
        self.assertIn("Import", labels)
        self.assertNotIn("+ Import", labels)
        self.assertNotIn("Add Character", labels)

    def test_the_bridge_writes_the_card_s_line(self):
        self.assertEqual(uebridge._STATUS, scenesetup._CHARACTER_STATUS)
        self.assertEqual(uebridge.HUB_SECTION, scenesetup.HUB_SECTION)

    def test_the_editor_line_is_context_the_character_line_the_subtitle(self):
        """2026-10-08: the editor line stays a `context` line (the skin hides
        it: its text is the dropdown's tooltip and the dot's state); the dot
        before the dropdown is a `dot`."""
        marks = self._marks()
        self.assertEqual(marks[uebridge._HEADER].role, "context")
        self.assertEqual(marks[uebridge._DOT].role, "dot")
        subtitles = [m.name for m in self.marks if m.role == "subtitle"]
        self.assertEqual(subtitles, [scenesetup._BOUND, scenesetup._WEAPONS_BOUND])

    def test_a_broken_bridge_leaves_the_rest_of_the_card(self):
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        saved = uebridge.build_rows

        def boom():
            raise RuntimeError("no editor module")
        uebridge.build_rows = boom
        try:
            scenesetup.build_characters_panel()
        finally:
            uebridge.build_rows = saved
        texts = [c[2].get("label", "") for c in fake.calls if c[0] == "text"]
        self.assertTrue(any("UE Bridge failed" in t and "no editor module" in t
                            for t in texts))
        self.assertIn(scenesetup._CHARACTER_STATUS, fake.children)

    def test_equip_and_unequip_stand_on_the_tab_row(self):
        """2026-10-08 (variant B): the row holding the [Weapon | Armor]
        segments has THREE columns - the segments (the adjustable one), Equip,
        Unequip - and those are the card's only buttons: the weapon tab and the
        armor rows lost the pair they each had."""
        calls = self._weapons_calls()
        rows = [(i, c) for i, c in enumerate(calls)
                if c[0] == "rowLayout" and not c[2].get("edit")]
        tab_at, tab = rows[0]
        segments_at, segments = rows[1]
        self.assertEqual(tab[2]["numberOfColumns"], 3)
        self.assertEqual(tab[2]["adjustableColumn"], 1)
        self.assertEqual(segments[2]["numberOfColumns"], len(scenesetup.TABS))
        buttons = [i for i, c in enumerate(calls)
                   if c[0] == "button" and not c[2].get("edit")]
        self.assertEqual([calls[i][2]["label"] for i in buttons], ["Equip", "Unequip"])
        radios = [i for i, c in enumerate(calls)
                  if c[0] == "iconTextRadioButton" and c[1]
                  and c[1][0].startswith(scenesetup._INVENTORY_TABS)]
        self.assertLess(tab_at, segments_at)
        self.assertLess(segments_at, radios[0])
        self.assertLess(radios[-1], buttons[0])
        #  the tab row is still open at both buttons: only the segments' own
        #  row closed between its creation and Unequip ...
        self.assertEqual(len([c for c in calls[tab_at:buttons[1]]
                              if c[0] == "setParent"]), 1)
        #  ... and the very next call closes the tab row, ahead of the tab columns
        self.assertEqual(calls[buttons[1] + 1][0], "setParent")
        column = [i for i, c in enumerate(calls) if c[0] == "columnLayout"
                  and c[1] == (scenesetup._TAB_COLUMN["weapon"],)][0]
        self.assertLess(buttons[1] + 1, column)
        roles = self._button_roles()
        self.assertEqual(roles["Equip"], ("primary", "sword"))
        self.assertEqual(roles["Unequip"], ("danger", "trash"))

    def _inventory_build(self, skin):
        """The Inventory card built once more, with the skin's arrangement or
        the classic hub's: (the fake, its marks)."""
        fake = FakeUiCmds()
        scenesetup.cmds = fake
        armorpanel.cmds = fake
        maya_hubstyle.take_marks()
        maya_hubstyle.set_skinning(skin)
        try:
            scenesetup.build_weapons_panel()
        finally:
            maya_hubstyle.set_skinning(False)
        return fake, maya_hubstyle.take_marks()

    def test_the_tab_row_is_compact_in_the_skin_and_words_in_the_classic_hub(self):
        fake, _marks = self._inventory_build(True)
        buttons = [c[2] for c in fake.calls if c[0] == "button" and not c[2].get("edit")]
        self.assertEqual([(b["label"], b["width"], b["height"]) for b in buttons],
                         [("Equip", 84, 24), ("", 26, 24)])
        tabs = [c[2]["height"] for c in fake.calls if c[0] == "iconTextRadioButton"
                and c[1][0].startswith(scenesetup._INVENTORY_TABS)]
        self.assertEqual(tabs, [22, 22])
        spacing = [c[2]["rowSpacing"] for c in fake.calls
                   if c[0] == "columnLayout" and "rowSpacing" in c[2]]
        self.assertEqual(spacing, [3, 3, 3])
        fake, _marks = self._inventory_build(False)
        buttons = [c[2] for c in fake.calls if c[0] == "button" and not c[2].get("edit")]
        self.assertEqual([(b["label"], b["width"], b["height"]) for b in buttons],
                         [("Equip", 80, 32), ("Unequip", 80, 32)])
        tabs = [c[2]["height"] for c in fake.calls if c[0] == "iconTextRadioButton"
                and c[1][0].startswith(scenesetup._INVENTORY_TABS)]
        self.assertEqual(tabs, [24, 24])
        spacing = [c[2]["rowSpacing"] for c in fake.calls
                   if c[0] == "columnLayout" and "rowSpacing" in c[2]]
        self.assertEqual(spacing, [6, 6, 6])

    def test_the_buttons_keep_the_weapon_tooltips_and_say_what_the_armor_tab_does(self):
        buttons = dict((c[2]["label"], c[2]["annotation"]) for c in self.fake.calls
                       if c[0] == "button" and c[2].get("label") in ("Equip", "Unequip"))
        self.assertIn("Put the weapon picked in the tiles into the picked hand",
                      buttons["Equip"])
        self.assertTrue(buttons["Equip"].endswith(
            " On the Armor tab: put the picked piece on."))
        self.assertIn("Bake the picked hand's weapon-bone animation back",
                      buttons["Unequip"])
        self.assertTrue(buttons["Unequip"].endswith(
            " On the Armor tab: Take the picked piece off the character."))

    def test_the_buttons_press_equip_current_and_unequip_current(self):
        pressed = []
        saved = (scenesetup.equip_current, scenesetup.unequip_current)
        try:
            scenesetup.equip_current = lambda: pressed.append("equip")
            scenesetup.unequip_current = lambda: pressed.append("unequip")
            for label in ("Equip", "Unequip"):
                call = [c for c in self.fake.calls if c[0] == "button"
                        and c[2].get("label") == label and not c[2].get("edit")][0]
                call[2]["command"]()
        finally:
            scenesetup.equip_current, scenesetup.unequip_current = saved
        self.assertEqual(pressed, ["equip", "unequip"])

    def test_equip_current_follows_the_tab(self):
        calls = []
        saved = (scenesetup.add_weapon, scenesetup.remove_weapon,
                 armorpanel.equip_armor, armorpanel.unequip_armor,
                 scenesetup.remembered_tab)
        try:
            scenesetup.add_weapon = lambda: calls.append("add_weapon")
            scenesetup.remove_weapon = lambda: calls.append("remove_weapon")
            armorpanel.equip_armor = lambda: calls.append("equip_armor")
            armorpanel.unequip_armor = lambda: calls.append("unequip_armor")
            scenesetup.remembered_tab = lambda: "armor"
            scenesetup.equip_current()
            scenesetup.unequip_current()
            scenesetup.remembered_tab = lambda: "weapon"
            scenesetup.equip_current()
            scenesetup.unequip_current()
        finally:
            (scenesetup.add_weapon, scenesetup.remove_weapon,
             armorpanel.equip_armor, armorpanel.unequip_armor,
             scenesetup.remembered_tab) = saved
        self.assertEqual(calls, ["equip_armor", "unequip_armor",
                                 "add_weapon", "remove_weapon"])

    def test_the_remembered_tab_decides_which_equip_runs(self):
        calls = []
        saved = (scenesetup.add_weapon, armorpanel.equip_armor)
        try:
            scenesetup.add_weapon = lambda: calls.append("add_weapon")
            armorpanel.equip_armor = lambda: calls.append("equip_armor")
            scenesetup.equip_current()                  # nothing remembered: Weapon
            self.fake.optionvars[scenesetup._TAB_OPTIONVAR] = "armor"
            scenesetup.equip_current()
            self.fake.optionvars[scenesetup._TAB_OPTIONVAR] = "nonsense"
            scenesetup.equip_current()
        finally:
            scenesetup.add_weapon, armorpanel.equip_armor = saved
        self.assertEqual(calls, ["add_weapon", "equip_armor", "add_weapon"])

    def test_a_failing_equip_lands_on_the_card_s_line_on_either_tab(self):
        def boom():
            raise RuntimeError("boom")
        saved = (scenesetup.add_weapon, armorpanel.equip_armor)
        try:
            scenesetup.add_weapon = boom
            armorpanel.equip_armor = boom
            for tab in ("weapon", "armor"):
                self.fake.optionvars[scenesetup._TAB_OPTIONVAR] = tab
                with self.assertRaises(RuntimeError):
                    scenesetup.equip_current()
                lines = [c[2].get("label") for c in self.fake.calls
                         if c[0] == "text" and c[1] == (scenesetup._STATUS,)
                         and c[2].get("edit")]
                self.assertEqual(lines[-1], "RuntimeError: boom", tab)
        finally:
            scenesetup.add_weapon, armorpanel.equip_armor = saved

    def test_characters_has_delete_beside_add_character(self):
        """2026-10-01: «кнопку удаления» - a danger button in the + Import
        row (Add Character until that evening), pressing `delete_characters`
        onto the card's own line."""
        index = self._created_index()
        add, delete = index["+ Import"], index["Delete"]
        rows = [i for i, c in enumerate(self.fake.calls) if c[0] == "rowLayout"]
        row = max(i for i in rows if i < add)
        self.assertLess(row, delete)
        between = [c for c in self.fake.calls[add:delete] if c[0] == "setParent"]
        self.assertEqual(between, [])
        self.assertLess(delete, index["Camera"])
        #  ... and Camera too: one row of three buttons (2026-10-08)
        between = [c for c in self.fake.calls[delete:index["Camera"]]
                   if c[0] == "setParent"]
        self.assertEqual(between, [])
        self.assertEqual(self._button_roles()["Delete"], ("danger", "trash"))
        pressed = []
        saved = (scenesetup.delete_characters, scenesetup._run)
        try:
            scenesetup.delete_characters = lambda: pressed.append(True)
            scenesetup._run = lambda action, status=None: (action(), pressed.append(status))
            self.fake.calls[delete][2]["command"]()
        finally:
            scenesetup.delete_characters, scenesetup._run = saved
        self.assertEqual(pressed, [True, scenesetup._CHARACTER_STATUS])

    def test_the_status_lines_are_marked(self):
        marks = self._marks()
        for name in (scenesetup._STATUS, scenesetup._CHARACTER_STATUS):
            self.assertEqual(marks[name].role, "status")

    def _buttons(self):
        """[(label, role, icon, call index)] of the marked buttons, in
        creation order - two sections may share a label (Equip)."""
        marks = self._marks()
        unnamed = [n for n in self.fake.children if n.startswith("button")]
        out = []
        for index, call in enumerate(self.fake.calls):
            if call[0] != "button" or call[2].get("edit"):
                continue
            name = call[1][0] if call[1] else unnamed.pop(0)
            label = call[2].get("label")
            if name in marks and label:
                out.append((label, marks[name].role, marks[name].icon, index))
        return out

    def test_the_sections_have_headings(self):
        """2026-10-01: «Пусть все будет консистентно» - Characters and UE
        Connect in Animation Setup; Inventory's sections are its TABS. The
        CLASSIC hub only since 2026-10-08 (the skin: no headings at all, see
        `test_no_heading_in_the_skin`)."""
        heads = [(c[1][0], c[2]["label"]) for c in self.fake.calls
                 if c[0] == "text" and c[1] and not c[2].get("edit")
                 and self._marks().get(c[1][0]) is not None
                 and self._marks()[c[1][0]].role == "heading"]
        self.assertEqual(heads, [(scenesetup._CHARACTERS_HEADING, "Characters"),
                                 (uebridge._HEADING, "Connect")])

    def test_the_inventory_is_two_tabs_one_shown(self):
        """2026-10-01, the evening: «переключаемся нажимая на название
        раздела Weapon или Armor ... две под вкладки» - a [Weapon | Armor]
        row of segments, a column per tab, the Weapon tab shown first."""
        calls = self._weapons_calls()
        self.assertIn(("iconTextRadioCollection", (scenesetup._INVENTORY_TABS,), {}), calls)
        segments = [c for c in calls if c[0] == "iconTextRadioButton" and c[1]
                    and c[1][0].startswith(scenesetup._INVENTORY_TABS)]
        self.assertEqual([(c[1][0], c[2]["label"], c[2]["select"]) for c in segments],
                         [(scenesetup.tab_segment("weapon"), "Weapon", True),
                          (scenesetup.tab_segment("armor"), "Armor", False)])
        marks = self._marks()
        for call in segments:
            self.assertEqual(marks[call[1][0]].role, "segment")
        columns = dict((c[1][0], c[2]) for c in calls if c[0] == "columnLayout"
                       and c[1] and c[1][0] in scenesetup._TAB_COLUMN.values())
        self.assertEqual(columns[scenesetup._TAB_COLUMN["weapon"]]["manage"], True)
        self.assertEqual(columns[scenesetup._TAB_COLUMN["armor"]]["manage"], False)
        # the weapon panel and its buttons in the Weapon column, the tiles in the
        # Armor column, the line after both
        order = [c[1][0] for c in calls if c[0] in ("columnLayout", "text") and c[1]
                 and not c[2].get("edit")]
        want = [scenesetup._TAB_COLUMN["weapon"], scenesetup._INVENTORY,
                scenesetup._TAB_COLUMN["armor"], armorpanel._TILES, scenesetup._STATUS]
        self.assertEqual([n for n in order if n in want], want)

    def test_show_tab_switches_the_columns_and_remembers(self):
        real = self.fake.columnLayout

        def column(*args, **kwargs):
            if kwargs.get("exists"):
                return args[0] in scenesetup._TAB_COLUMN.values()
            return real(*args, **kwargs)
        self.fake.columnLayout = column
        shown = []
        saved = armorpanel.show
        armorpanel.show = lambda: shown.append("armor")
        try:
            scenesetup.show_tab("armor")
        finally:
            armorpanel.show = saved
        self.assertEqual(self.fake.optionvars[scenesetup._TAB_OPTIONVAR], "armor")
        manages = [(c[1][0], c[2]["manage"]) for c in self.fake.calls
                   if c[0] == "columnLayout" and c[2].get("edit")]
        self.assertEqual(sorted(manages[-2:]), sorted([
            (scenesetup._TAB_COLUMN["weapon"], False), (scenesetup._TAB_COLUMN["armor"], True)]))
        self.assertEqual(shown, ["armor"])
        self.assertEqual(scenesetup.remembered_tab(), "armor")
        scenesetup.show_tab("nonsense")
        self.assertEqual(scenesetup.remembered_tab(), "armor")

    def test_the_weapon_line_is_left_alone_on_the_armor_tab(self):
        written = []
        saved = (scenesetup._status, scenesetup._attached, scenesetup._inventory)
        scenesetup._status = lambda message, control=None: written.append(message)
        scenesetup._attached = lambda entry, key=None: (None, None, None, None, False)
        scenesetup._inventory = lambda: None
        try:
            self.fake.optionvars[scenesetup._TAB_OPTIONVAR] = "armor"
            saved_refresh = scenesetup.refresh
            scenesetup.refresh = self.saved[1]          # the real one
            scenesetup.refresh()
            self.assertEqual(written, [])
            self.fake.optionvars[scenesetup._TAB_OPTIONVAR] = "weapon"
            scenesetup.refresh()
            self.assertEqual(written, [scenesetup.NO_CHARACTER])
        finally:
            scenesetup.refresh = saved_refresh
            (scenesetup._status, scenesetup._attached, scenesetup._inventory) = saved

    def test_the_inventory_card_has_one_line_and_the_armor_rows_under_the_weapons(self):
        calls = self._weapons_calls()
        lines = [c for c in calls if c[0] == "text" and c[1]
                 and c[1][0] in (scenesetup._STATUS, "mayaSceneSetupArmorStatus")
                 and not c[2].get("edit")]
        self.assertEqual([c[1][0] for c in lines], [scenesetup._STATUS])
        self.assertEqual(armorpanel._STATUS, scenesetup._STATUS)
        self.assertEqual(armorpanel._BOUND, scenesetup._WEAPONS_BOUND)
        order = [c[1][0] for c in calls if c[0] in ("text", "columnLayout") and c[1]
                 and c[1][0] in (scenesetup._INVENTORY, armorpanel._TILES, scenesetup._STATUS)
                 and not c[2].get("edit")]
        self.assertEqual(order, [scenesetup._INVENTORY, armorpanel._TILES, scenesetup._STATUS])
        jobs = [c for c in calls if c[0] == "scriptJob"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0][2]["parent"], scenesetup._STATUS)

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


class Armor(unittest.TestCase):
    """The Armor section (2026-10-01): its rows in the Inventory card - the
    tiles (Equip / Unequip stand on the card's tab row since 2026-10-08) -
    writing the card's one line."""

    def setUp(self):
        self.saved = (armorpanel.cmds, armorpanel._attach_tiles, armorpanel.refresh,
                      armorpanel._bound_root, armorpanel.armor.equip, armorpanel.armor.unequip)
        self.fake = FakeUiCmds()
        armorpanel.cmds = self.fake
        self.refreshes = []
        armorpanel.refresh = lambda *a, **k: self.refreshes.append(k.get("say", True))
        self.tiles = []
        armorpanel._attach_tiles = lambda: self.tiles.append(True) or True
        maya_hubstyle.take_marks()
        armorpanel.build_rows()
        self.marks = dict((m.name, m) for m in maya_hubstyle.take_marks())

    def tearDown(self):
        (armorpanel.cmds, armorpanel._attach_tiles, armorpanel.refresh,
         armorpanel._bound_root, armorpanel.armor.equip, armorpanel.armor.unequip) = self.saved

    def _buttons(self):
        return [c[2] for c in self.fake.calls if c[0] == "button" and not c[2].get("edit")]

    def test_no_window_no_column_no_heading_the_tiles(self):
        """The Armor tab's segment names the section (2026-10-01)."""
        self.assertEqual(self.fake.windows, {})
        self.assertFalse([c for c in self.fake.calls if c[0] == "columnLayout"
                          and c[1] != (armorpanel._TILES,)])
        self.assertFalse([m for m in self.marks.values() if m.role == "heading"])
        self.assertFalse(hasattr(armorpanel, "_HEADING"))
        self.assertTrue(any(c[0] == "columnLayout" and c[1] == (armorpanel._TILES,)
                            for c in self.fake.calls))

    def test_the_rows_build_no_subtitle_no_line_no_job(self):
        """The card's: its subtitle, its one line, the job hung on it."""
        self.assertFalse([m for m in self.marks.values() if m.role in ("subtitle", "status")])
        self.assertNotIn(armorpanel._STATUS, self.fake.children)
        self.assertFalse([c for c in self.fake.calls if c[0] == "scriptJob"])
        self.assertFalse(hasattr(armorpanel, "build_panel"))

    def test_the_tiles_are_laid_over_the_placeholder_and_no_dropdown(self):
        self.assertEqual(self.tiles, [True])
        self.assertFalse(any(c[0] == "optionMenu" for c in self.fake.calls))

    def test_without_qt_a_dropdown_of_the_rows(self):
        fake = FakeUiCmds()
        armorpanel.cmds = fake
        armorpanel._attach_tiles = lambda: False
        armorpanel.build_rows()
        self.assertTrue(any(c[0] == "optionMenu" and c[1] == (armorpanel._MENU,)
                            for c in fake.calls))
        items = [c[2].get("label") for c in fake.calls if c[0] == "menuItem"]
        self.assertEqual(items, catalog.armor_labels())

    def test_the_rows_build_only_the_tiles_no_button(self):
        """2026-10-08: Equip / Unequip stand on the Inventory card's tab row
        (`window.equip_current` / `unequip_current` dispatch to this tab's
        `equip_armor` / `unequip_armor`); the Armor tab is the tiles alone."""
        self.assertEqual(self._buttons(), [])
        self.assertFalse([c for c in self.fake.calls if c[0] == "rowLayout"])
        self.assertFalse([m for m in self.marks.values()
                          if m.role in ("primary", "danger", "secondary")])
        self.assertEqual(self.tiles, [True])

    def test_the_line_is_told_to_the_hub(self):
        """2026-10-08: the status writer tells the hub's one message line too,
        the presses' and the tiles' Open scene alike."""
        heard = []

        def listener(control, text, viewport=False):
            heard.append((control, text))
        maya_hubstyle.listen(listener)
        try:
            armorpanel._status("worn")
            armorpanel.say("opened")
        finally:
            maya_hubstyle.unlisten(listener)
        self.assertEqual(heard, [(armorpanel._STATUS, "worn"),
                                 (armorpanel._STATUS, "opened")])
        lines = [c[2].get("label") for c in self.fake.calls
                 if c[0] == "text" and c[1] == (armorpanel._STATUS,) and c[2].get("edit")]
        self.assertEqual(lines, ["worn", "opened"])

    def test_watch_hangs_one_job_on_the_card_s_line_that_writes_no_line(self):
        armorpanel.watch()
        jobs = [c for c in self.fake.calls if c[0] == "scriptJob"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0][2]["event"][0], "SelectionChanged")
        self.assertEqual(jobs[0][2]["parent"], armorpanel._STATUS)
        jobs[0][2]["event"][1]()
        self.assertEqual(self.refreshes, [False, False])     # watch's own, then the job's

    def test_the_card_s_line_and_subtitle(self):
        from maya_scenesetup import window as scene
        self.assertEqual(armorpanel._STATUS, scene._STATUS)
        self.assertEqual(armorpanel._BOUND, scene._WEAPONS_BOUND)
        self.assertEqual(armorpanel.HUB_SECTION, "weapons")

    def test_equip_and_unequip_report_on_the_line(self):
        armorpanel.refresh = lambda *a, **k: None
        armorpanel._bound_root = lambda: "|Manny_Rig:root"
        seen = []
        armorpanel.armor.equip = lambda root, entry: seen.append(("on", root, entry.key)) or "put on"
        armorpanel.armor.unequip = lambda root, key: seen.append(("off", root, key)) or "taken off"
        armorpanel.equip_armor()
        armorpanel.unequip_armor()
        self.assertEqual(seen, [("on", "|Manny_Rig:root", "Tech_Limb"),
                                ("off", "|Manny_Rig:root", "Tech_Limb")])
        lines = [c[2].get("label") for c in self.fake.calls
                 if c[0] == "text" and c[1] == (armorpanel._STATUS,) and c[2].get("edit")]
        self.assertEqual(lines[-2:], ["put on", "taken off"])

    def test_a_drop_on_a_character_equips_it_there(self):
        armorpanel.refresh = lambda *a, **k: None
        seen = []
        armorpanel.armor.equip = lambda root, entry: seen.append((root, entry.key)) or "put on"
        self.assertEqual(armorpanel.equip_on("|Creep_Rig:root", "Tech_Limb"), "put on")
        self.assertEqual(seen, [("|Creep_Rig:root", "Tech_Limb")])
        self.assertEqual(self.fake.optionvars[armorpanel._OPTIONVAR], "Tech_Limb")
        self.assertEqual(armorpanel.equip_on("|Creep_Rig:root", "not_a_row"), "")
        self.assertEqual(armorpanel.equip_on(None, "Tech_Limb"), armorpanel.NO_CHARACTER)
        self.assertEqual(len(seen), 1)

    def test_no_character_says_so_and_touches_nothing(self):
        armorpanel._bound_root = lambda: None
        armorpanel.armor.equip = lambda *a: self.fail("equipped with no character")
        armorpanel.equip_armor()
        lines = [c[2].get("label") for c in self.fake.calls
                 if c[0] == "text" and c[1] == (armorpanel._STATUS,) and c[2].get("edit")]
        self.assertEqual(lines[-1], armorpanel.NO_CHARACTER)

    def test_the_pick_is_remembered(self):
        armorpanel.select_armor("Tech_Limb")
        self.assertEqual(self.fake.optionvars[armorpanel._OPTIONVAR], "Tech_Limb")
        self.assertEqual(armorpanel.chosen_armor().key, "Tech_Limb")
        armorpanel.select_armor("not_a_row")
        self.assertEqual(self.fake.optionvars[armorpanel._OPTIONVAR], "Tech_Limb")

    def test_is_open_follows_the_line(self):
        self.assertFalse(armorpanel.is_open())
        self.fake.children.append(armorpanel._STATUS)
        self.assertTrue(armorpanel.is_open())

    def test_show_window_opens_the_inventory_on_its_armor_tab(self):
        fake = FakeUiCmds()
        saved = scenesetup.cmds
        scenesetup.cmds = fake
        try:
            result, asked = _hub_asked(armorpanel.show_window)
        finally:
            scenesetup.cmds = saved
        self.assertEqual((result, asked), ("hub", ["weapons"]))
        self.assertEqual(fake.optionvars[scenesetup._TAB_OPTIONVAR], "armor")


class UeBridge(unittest.TestCase):
    """The bridge's rows (2026-10-01: built into the Characters card)."""

    def setUp(self):
        self.saved = (uebridge.cmds, uebridge.load_cache,
                      uebridge._repopulate, uebridge.fill_project_menu,
                      uebridge._attach_drag)
        self.fake = FakeUiCmds()
        uebridge.cmds = self.fake
        uebridge.load_cache = lambda: ([], "", "", "")
        self.quiet = []
        uebridge._repopulate = lambda quiet=False: self.quiet.append(quiet) or []
        uebridge.fill_project_menu = lambda labels: None
        uebridge._attach_drag = lambda: None
        self.headers = []
        self.saved_header = uebridge._header
        uebridge._header = self.headers.append
        maya_hubstyle.take_marks()
        uebridge.build_rows()
        self.marks = maya_hubstyle.take_marks()

    def tearDown(self):
        (uebridge.cmds, uebridge.load_cache, uebridge._repopulate,
         uebridge.fill_project_menu, uebridge._attach_drag) = self.saved
        uebridge._header = self.saved_header

    def test_no_window_and_one_block_set_into_the_card(self):
        """2026-10-02: «раздел с подключением ... визуально как-то отделить» -
        the rows' one column is the Connect block, an inset in the skin, a
        background of its own in the classic hub."""
        self.assertEqual(self.fake.windows, {})
        columns = [c for c in self.fake.calls if c[0] == "columnLayout"
                   and not c[2].get("edit") and not c[2].get("query")]
        self.assertEqual([c[1][0] for c in columns], [uebridge._INSET])
        self.assertEqual(columns[0][2]["backgroundColor"], uebridge.INSET_CLASSIC_BG)
        insets = [m for m in self.marks if m.role == "inset"]
        self.assertEqual(len(insets), 1)
        self.assertTrue(insets[0].layout)

    def test_the_source_switch_is_three_segments(self):
        """Unreal, Unity, Folder - the remembered one lit (Unreal by default)."""
        segments = [c for c in self.fake.calls if c[0] == "iconTextRadioButton"
                    and c[1][0].startswith(uebridge._SOURCE)]
        self.assertEqual([c[2]["label"] for c in segments],
                         ["Unreal", "Unity", "Folder"])
        self.assertEqual([c[2]["select"] for c in segments], [True, False, False])
        marks = dict((m.name, m) for m in self.marks)
        for call in segments:
            self.assertEqual(marks[call[1][0]].role, "segment")
            self.assertTrue(callable(call[2]["onCommand"]))

    def test_the_heading_comes_first_in_the_block(self):
        texts = [c[1][0] for c in self.fake.calls if c[0] == "text" and c[1]
                 and not c[2].get("edit")]
        self.assertEqual(texts[0], uebridge._HEADING)

    def test_not_a_section_any_more(self):
        self.assertFalse(hasattr(uebridge, "build_panel"))
        self.assertFalse(hasattr(uebridge, "MODE_SEGMENTS"))
        self.assertFalse(hasattr(uebridge, "mode_button"))

    def test_rows_not_a_form_and_the_list_has_a_height(self):
        """Measured 2026-09-17: a formLayout inside the hub's column
        reported a 1128 px minimum width whatever its children were told,
        so the panel is rows in a column and only the list is sized."""
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "formLayout"])
        lists = [c for c in self.fake.calls if c[0] == "textScrollList"
                 and not c[2].get("edit") and not c[2].get("query")]
        #  the classic list keeps its pixel height; the skin shows 10 rows by
        #  its grip (2026-10-08), which `_LIST_GRIP` marks
        self.assertEqual(lists[0][2].get("height"), uebridge.LIST_HEIGHT)
        self.assertGreaterEqual(uebridge.LIST_HEIGHT, 200)
        self.assertTrue(lists[0][2].get("allowMultiSelection"))
        grips = [m for m in self.marks if m.role == "grip"]
        self.assertEqual([(m.name, m.target) for m in grips],
                         [(uebridge._LIST_GRIP, uebridge._LIST)])

    def test_the_import_target_is_two_short_segments(self):
        """2026-10-01, «Слить»: the card's [Rig | Skeleton] says what, these
        two say where - Onto selected (lit on every build) and New."""
        self.assertFalse([c for c in self.fake.calls
                          if c[0] == "radioButtonGrp"])
        segments = [c for c in self.fake.calls if c[0] == "iconTextRadioButton"
                    and c[1][0].startswith(uebridge._MODE)
                    and not c[2].get("edit")]
        #  2026-10-08: «Onto sel.» in both hubs (the tooltip says the rest)
        self.assertEqual([c[2]["label"] for c in segments],
                         ["Onto sel.", "New"])
        self.assertEqual([c[1][0] for c in segments],
                         [uebridge.target_button(t) for t in uebridge.TARGETS])
        self.assertEqual([c[2]["select"] for c in segments], [True, False])
        for call in segments:
            self.assertGreater(len(call[2]["annotation"]), 40)
        marks = dict((m.name, m) for m in self.marks)
        for call in segments:
            self.assertEqual(marks[call[1][0]].role, "segment")

    def test_import_is_the_primary_action(self):
        marks = [m for m in self.marks if m.role == "primary"]
        self.assertEqual([m.icon for m in marks], ["download"])
        labels = [c[2]["label"] for c in self.fake.calls if c[0] == "button"
                  and "label" in c[2]
                  and not c[2].get("edit")]
        self.assertIn("Import Animation", labels)
        self.assertNotIn("Import", labels)
        #  2026-10-08: the two exports share the Import row; the classic hub
        #  spells «FBX...» and «uasset», the tooltips say Export
        self.assertIn("FBX...", labels)
        self.assertIn("uasset", labels)
        fbx = [c for c in self.fake.calls if c[0] == "button"
               and c[2].get("label") == "FBX..."][0]
        self.assertTrue(fbx[2]["annotation"].startswith("Export FBX... - "))

    def test_the_import_row_is_one_row_of_five(self):
        """2026-10-08, variant B: [Onto sel. | New] [timeline] [Import]
        [FBX] [uasset] on one row - the exports no longer take a row of their
        own."""
        rows = [i for i, c in enumerate(self.fake.calls) if c[0] == "rowLayout"
                and c[2].get("numberOfColumns") == 5]
        self.assertEqual(len(rows), 1)
        inside = self.fake.calls[rows[0]:]
        order = [c[1][0] if c[1] else c[2].get("label") for c in inside
                 if (c[0] in ("iconTextRadioButton", "checkBox", "button")
                     and not (c[2].get("edit") or c[2].get("exists")
                              or c[2].get("query")))]
        self.assertEqual(order, [uebridge.target_button("onto"),
                                 uebridge.target_button("new"),
                                 uebridge._TIMELINE, "Import Animation",
                                 "FBX...", uebridge._UASSET])
        #  the five columns close once for the segments' own row and once for
        #  the row, then the Connect block
        self.assertEqual(len([c for c in inside if c[0] == "setParent"]), 3)
        self.assertEqual(self.fake.calls[rows[0]][2]["adjustableColumn"], 3)

    def test_the_timeline_box_is_a_clock_chip(self):
        """The skin draws the checkbox as a pill with a clock; the classic
        hub keeps a word."""
        marks = dict((m.name, m) for m in self.marks)
        self.assertEqual((marks[uebridge._TIMELINE].role,
                          marks[uebridge._TIMELINE].icon), ("chip", "clock"))
        box = [c for c in self.fake.calls if c[0] == "checkBox"][0]
        self.assertEqual(box[1], (uebridge._TIMELINE,))
        self.assertEqual(box[2]["label"], "timeline")
        self.assertTrue(box[2]["value"])
        self.assertIn("timeline", box[2]["annotation"])

    def test_the_editor_line_is_context_and_the_rows_build_no_status(self):
        marks = dict((m.name, m) for m in self.marks)
        self.assertEqual(marks[uebridge._HEADER].role, "context")
        self.assertFalse([m for m in self.marks if m.role in ("subtitle", "status")])
        self.assertNotIn(uebridge._STATUS, self.fake.children)
        header = [c for c in self.fake.calls if c[0] == "text"
                  and c[1] == (uebridge._HEADER,) and not c[2].get("edit")]
        self.assertTrue(header[0][2].get("wordWrap"))
        self.assertEqual(header[0][2].get("height"), 36)

    def test_the_cache_is_the_editor_line_s_to_say_on_open(self):
        self.assertEqual(self.quiet, [True])
        self.assertEqual(self.headers, [uebridge.editor_line(False, 0)])

    def test_the_editor_line(self):
        self.assertEqual(uebridge.editor_line(True), "connected")
        self.assertIn("619 animations from the last refresh",
                      uebridge.editor_line(False, 619))
        self.assertNotIn("Unreal:", uebridge.editor_line(False, 619))   # the heading says it
        self.assertIn("press Refresh to read", uebridge.editor_line(False, 0))

    def test_the_named_controls_exist(self):
        for name in (uebridge._LIST, uebridge._SEARCH, uebridge._DOT,
                     uebridge._HEADER, uebridge._TIMELINE, uebridge._PROJECT,
                     uebridge._LIST_GRIP):
            self.assertIn(name, self.fake.children, name)
        self.assertIn(("iconTextRadioCollection", (uebridge._MODE,), {}),
                      self.fake.calls)
        #  open while the card's line stands
        self.assertFalse(uebridge.is_open())
        self.fake.children.append(uebridge._STATUS)
        self.assertTrue(uebridge.is_open())

    def test_show_window_opens_the_characters_card(self):
        result, asked = _hub_asked(uebridge.show_window)
        self.assertEqual((result, asked), ("hub", ["characters"]))

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

    def test_one_line_of_hint_the_paragraph_is_the_tooltip(self):
        """2026-09-28: 296 px for one button and a paragraph was the
        section's cost; the paragraph is the button's tooltip now."""
        texts = [c[2].get("label") for c in self.fake.calls
                 if c[0] == "text" and not c[2].get("edit")]
        self.assertIn(rr.PANEL_HINT, texts)
        self.assertNotIn(rr.PANEL_NOTE, texts)
        buttons = [c for c in self.fake.calls if c[0] == "button"]
        self.assertEqual(buttons[0][2]["annotation"], rr.PANEL_NOTE)
        self.assertLess(len(rr.PANEL_HINT), 60)

    def test_retarget_is_the_primary_action(self):
        maya_hubstyle.take_marks()
        rr.build_panel()
        roles = [(m.role, m.icon) for m in maya_hubstyle.take_marks()]
        self.assertIn(("primary", "arrows-exchange"), roles)
        self.assertIn(("status", None), roles)

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

"""The AT bar (2026-10-21): animBot's tools as a bar of their own on top of the Time Bar.

Its glyphs, where it docks, the ⋮ -> Time bar ▸ AT bar switch, and the smoothing its SM slider uses.
"""

import datetime
import os
import re
import sys
import types
import unittest
import xml.etree.ElementTree as ElementTree
from unittest import mock

import maya

import maya_atbar
from maya_atbar import core, glyphs

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


class Glyphs(unittest.TestCase):
    def test_every_glyph_is_an_svg_drawn_in_the_colour_asked(self):
        for name in glyphs.GLYPHS:
            doc = glyphs.svg(name, "#123456")
            self.assertTrue(ElementTree.fromstring(doc).tag.endswith("svg"), name)
            self.assertNotIn("currentColor", doc, name)
            self.assertIn("#123456", doc, name)

    def test_every_button_names_a_glyph_and_all_26_are_used(self):
        with open(os.path.join(PLUGIN, "maya_atbar", "bar.py"), encoding="utf-8") as handle:
            source = handle.read()
        used = set(re.findall(r'(?:self\._button|\bb)\("(\w+)"', source))
        self.assertEqual(sorted(used - set(glyphs.GLYPHS)), [])
        self.assertEqual(sorted(set(glyphs.GLYPHS) - used), [])
        self.assertEqual(len(used), 26)


class Place(unittest.TestCase):
    """Docked as the Time Bar is, on top of it."""

    def test_on_top_of_the_time_bar_while_it_shows(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: True, lambda n: n == "skeldarTimeBar"),
                         ("dockToControl", ("skeldarTimeBar", "top")))

    def test_on_top_of_maya_s_slider_while_only_it_shows(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: True, lambda n: n == "TimeSlider"),
                         ("dockToControl", ("TimeSlider", "top")))

    def test_a_hidden_time_bar_still_comes_before_the_window(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: n == "skeldarTimeBar", lambda n: False),
                         ("dockToControl", ("skeldarTimeBar", "top")))

    def test_the_bottom_of_maya_s_window_without_either(self):
        self.assertEqual(maya_atbar.dock_target(lambda n: False, lambda n: False),
                         ("dockToMainWindow", ("bottom", False)))

    def test_the_uiscript_builds_the_bar_from_the_plugin_folder(self):
        code = maya_atbar.uiscript("C:\\x\\SkeldarAnim\\")
        self.assertIn('_p = "C:/x/SkeldarAnim"', code)
        self.assertIn("maya_atbar.bar.build()", code)
        compile(code, "uiscript", "exec")


class _Cmds(object):
    def __init__(self):
        self.optionvars = {}

    def optionVar(self, q=None, exists=None, intValue=None, stringValue=None):
        if exists is not None:
            return exists in self.optionvars
        if q is not None:
            return self.optionvars[q]
        for pair in (intValue, stringValue):
            if pair is not None:
                self.optionvars[pair[0]] = pair[1]
        return None

    def about(self, batch=False):
        return False


class Switch(unittest.TestCase):
    """⋮ -> Time bar ▸ AT bar ▸ Full / Compact / Off (2026-10-26, «2 варіанта розкладки»): off by default,
    the layout remembered apart from on / off."""

    def setUp(self):
        self.cmds = _Cmds()
        for patch in (mock.patch.dict(sys.modules, {"maya.cmds": self.cmds}),
                      mock.patch.object(maya, "cmds", self.cmds, create=True)):
            patch.start()
            self.addCleanup(patch.stop)

    def choose(self, choice):
        with mock.patch.object(maya_atbar, "ensure") as ensure, mock.patch.object(maya_atbar, "hide") as hide:
            text = maya_atbar.set_layout(choice)
        return text, ensure, hide

    def test_off_until_the_animator_turns_it_on(self):
        self.assertFalse(maya_atbar.wanted())
        self.assertEqual(maya_atbar.layout(), "off")

    def test_full_is_remembered_and_shows_the_bar(self):
        text, ensure, hide = self.choose("full")
        self.assertEqual(self.cmds.optionvars[maya_atbar.OPTIONVAR], 1)
        self.assertEqual(self.cmds.optionvars[maya_atbar.LAYOUT_OPT], "full")
        ensure.assert_called_once_with()
        hide.assert_not_called()
        self.assertTrue(maya_atbar.wanted())
        self.assertEqual(maya_atbar.layout(), "full")
        self.assertEqual(text, maya_atbar.MESSAGES["full"])

    def test_compact_is_remembered_and_shows_the_bar(self):
        text, ensure, hide = self.choose("compact")
        self.assertEqual(self.cmds.optionvars[maya_atbar.OPTIONVAR], 1)
        self.assertEqual(self.cmds.optionvars[maya_atbar.LAYOUT_OPT], "compact")
        ensure.assert_called_once_with()
        hide.assert_not_called()
        self.assertEqual(maya_atbar.layout(), "compact")
        self.assertEqual(text, maya_atbar.MESSAGES["compact"])

    def test_off_hides_the_bar_and_keeps_the_layout_for_the_next_on(self):
        self.choose("compact")
        text, ensure, hide = self.choose("off")
        self.assertEqual(self.cmds.optionvars[maya_atbar.OPTIONVAR], 0)
        hide.assert_called_once_with()
        ensure.assert_not_called()
        self.assertEqual(maya_atbar.layout(), "off")
        self.assertEqual(text, maya_atbar.MESSAGES["off"])
        with mock.patch.object(maya_atbar, "ensure"):
            maya_atbar.set_on(True)
        self.assertEqual(maya_atbar.layout(), "compact")

    def test_an_older_true_or_false_reads_as_full_or_off(self):
        self.assertEqual(maya_atbar.choice_of(True), "full")
        self.assertEqual(maya_atbar.choice_of(False), "off")
        self.assertEqual(maya_atbar.choice_of("compact"), "compact")
        self.assertEqual(maya_atbar.choice_of("nonsense"), "full")
        self.cmds.optionvars[maya_atbar.OPTIONVAR] = 1           # on before the layouts existed
        self.assertEqual(maya_atbar.layout(), "full")

    def test_the_hub_brings_it_back_only_when_it_was_left_on(self):
        with mock.patch.object(maya_atbar, "ensure", return_value="skeldarATBar") as ensure:
            self.assertIsNone(maya_atbar.ensure_wanted())
            ensure.assert_not_called()
            self.cmds.optionvars[maya_atbar.OPTIONVAR] = 1
            self.assertEqual(maya_atbar.ensure_wanted(), "skeldarATBar")
            ensure.assert_called_once_with()


class InsideTheTimeBar(unittest.TestCase):
    """2026-10-21, «прибери ще сірі роздєлітєльні лінії»: a control of its own stood behind Maya's splitter
    line, so on a docked Time Bar the strip is its top row - and the Time Bar's height counts it."""

    def test_no_row_no_height_and_nothing_imported_for_it(self):
        with mock.patch.dict(sys.modules):
            sys.modules.pop("maya_atbar.bar", None)
            self.assertEqual(maya_atbar.docked_height(), 0)
            self.assertNotIn("maya_atbar.bar", sys.modules)

    def test_the_time_bar_asks_the_at_bar(self):
        import maya_timebar
        with mock.patch.object(maya_atbar, "docked_height", return_value=57):
            self.assertEqual(maya_timebar.extra_height(), 57)
        with mock.patch.object(maya_atbar, "docked_height", side_effect=RuntimeError("no Qt")):
            self.assertEqual(maya_timebar.extra_height(), 0)

    def test_a_page_shown_sizes_the_control_for_the_page_and_the_row(self):
        import maya_timebar
        from maya_timebar import scene

        class Cmds(object):
            def __init__(self):
                self.edits = []

            def workspaceControl(self, name, exists=False, edit=False, **kwargs):
                if exists:
                    return True
                self.edits.append((name, kwargs))

        class Strip(object):
            ui = 1.0

            def sizeHint(self):
                return types.SimpleNamespace(height=lambda: 130)

            def parentWidget(self):
                return None

        fake = Cmds()
        state = {"bar": None, "jobs": [], "callbacks": [], "host": "docked"}
        with mock.patch.object(scene, "cmds", fake), mock.patch.object(sys, "_skeldar_timebar", state, create=True), \
                mock.patch.object(maya_timebar, "extra_height", return_value=57):
            scene.page_height(Strip())
        self.assertEqual(fake.edits, [(maya_timebar.CONTROL, {"resizeHeight": 130 + 57})])

    def test_a_row_gone_frees_the_fixed_height_so_the_dock_can_shrink(self):
        # 2026-10-26, Full -> Compact: a fixed workspaceControl keeps its height as its minimum (172 for 115),
        # so the splitter could not take the AT row's 57 px back until the height was free
        import maya_timebar
        from maya_timebar import scene

        class Cmds(object):
            def __init__(self):
                self.edits = []

            def workspaceControl(self, name, exists=False, edit=False, **kwargs):
                if exists:
                    return True
                self.edits.append(kwargs)

        host = types.SimpleNamespace(height=lambda: 172)
        strip = types.SimpleNamespace(ui=1.0, sizeHint=lambda: types.SimpleNamespace(height=lambda: 115),
                                      parentWidget=lambda: host)
        fake = Cmds()
        fitted = []
        state = {"bar": None, "jobs": [], "callbacks": [], "host": "docked"}
        with mock.patch.object(scene, "cmds", fake), mock.patch.object(sys, "_skeldar_timebar", state, create=True), \
                mock.patch.object(maya_timebar, "extra_height", return_value=0), \
                mock.patch.object(scene, "_later", lambda fn: fn()), \
                mock.patch.object(scene, "_fit_splitter",
                                  lambda h, want: fitted.append((h, want, fake.edits[-1]))):
            scene.page_height(strip)
        self.assertEqual(fitted, [(host, 115, {"heightProperty": "free"})])
        self.assertEqual(fake.edits[-1], {"heightProperty": "fixed"})

    def _splitter(self, dock):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtCore, QtWidgets
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.resize(400, 900)
        view, host = QtWidgets.QWidget(), QtWidgets.QWidget()
        splitter.addWidget(view)
        splitter.addWidget(host)
        splitter.show()
        splitter.setSizes([900 - dock, dock])
        self.app.processEvents()
        return splitter, host

    def test_the_dock_shrinks_back_when_maya_left_it_taller(self):
        # 2026-10-23: moved to another screen and back, resizeHeight never gave the 232 px back
        from maya_timebar import scene
        splitter, host = self._splitter(232)
        scene._fit_splitter(host, 172)
        self.app.processEvents()
        self.assertEqual(host.height(), 172)

    def test_the_dock_grows_taking_the_room_from_the_viewport(self):
        from maya_timebar import scene
        splitter, host = self._splitter(115)
        scene._fit_splitter(host, 172)
        self.app.processEvents()
        self.assertEqual(host.height(), 172)


class SelectSets(unittest.TestCase):
    """2026-10-21: a set made in a scene tab went into the tab's namespace, and the menu, listing
    `AT_sel_*` at the root, showed none - «не зберігається нічого»."""

    TAB = "tab_AS_Dagger_Attack_Cbm_L_R_1p_Full_with3p_1"

    def test_a_set_in_the_tab_s_namespace_is_listed_by_its_own_name(self):
        nodes = [self.TAB + ":AT_sel_L_fingers", self.TAB + ":defaultObjectSet", "AT_sel_root_only",
                 "tab_other:AT_sel_elsewhere", self.TAB + ":Manny_Rig1:AT_sel_inside_the_rig"]
        self.assertEqual(core.sets_in(nodes, self.TAB), [("L_fingers", self.TAB + ":AT_sel_L_fingers")])

    def test_the_root_namespace_lists_the_root_s_sets(self):
        nodes = ["AT_sel_hands", self.TAB + ":AT_sel_L_fingers", "AT_sel_feet", "lightLinker1"]
        self.assertEqual(core.sets_in(nodes, ":"), [("feet", "AT_sel_feet"), ("hands", "AT_sel_hands")])
        self.assertEqual(core.sets_in(nodes, ""), core.sets_in(nodes, ":"))

    def test_a_label_is_the_name_without_namespace_and_prefix(self):
        self.assertEqual(core.set_label(self.TAB + ":AT_sel_L_fingers1"), "L_fingers1")

    def test_the_cells_fill_four_columns_then_wrap(self):
        """2026-10-21, «окремі ячейки щоб вони спливали»: the pop-up's grid."""
        self.assertEqual(core.sets_grid(1), [(0, 0)])
        self.assertEqual(core.sets_grid(3), [(0, 0), (0, 1), (0, 2)])
        self.assertEqual(core.sets_grid(6), [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1)])
        self.assertEqual(core.sets_grid(0), [])


class MotionTrails(unittest.TestCase):
    """2026-10-23, «моушн тейл перестав справно працювати»: Maya named the groups AT_MOTION_TRAILS3..12,
    the toggle looked for AT_MOTION_TRAILS alone and added a trail on every click."""

    def test_a_numbered_group_is_ours(self):
        self.assertTrue(core.is_trail_group_name("|AT_MOTION_TRAILS12"))
        self.assertTrue(core.is_trail_group_name("AT_MOTION_TRAILS"))
        self.assertTrue(core.is_trail_group_name("tab_x:AT_MOTION_TRAILS3"))
        self.assertFalse(core.is_trail_group_name("AT_MOTION_TRAILS_old"))
        self.assertFalse(core.is_trail_group_name("AT_trail_DaggerMesh1Handle"))

    def test_the_numbered_groups_are_found_and_the_toggle_takes_them_away(self):
        fake = mock.MagicMock()

        def ls(*args, **kwargs):
            if args and args[0].startswith("*."):
                return ["|AT_MOTION_TRAILS13"]
            return ["|AT_MOTION_TRAILS3", "|AT_MOTION_TRAILS12", "|grp|AT_MOTION_TRAILS4"]
        fake.ls.side_effect = ls
        fake.listRelatives.side_effect = lambda n, **k: ["|grp"] if n == "|grp|AT_MOTION_TRAILS4" else None
        fake.objExists.return_value = True
        with mock.patch.object(core, "cmds", fake), mock.patch.object(core, "selection", return_value=[]):
            self.assertEqual(core.trail_groups(), ["|AT_MOTION_TRAILS12", "|AT_MOTION_TRAILS13", "|AT_MOTION_TRAILS3"])
            self.assertTrue(core.motion_trails_exist())
            core.motion_trail_click()
        deleted = set(c.args[0] for c in fake.delete.call_args_list)
        self.assertEqual(deleted, {"|AT_MOTION_TRAILS12", "|AT_MOTION_TRAILS13", "|AT_MOTION_TRAILS3"})
        fake.createNode.assert_not_called()

    def test_a_handle_from_before_the_tag_is_known_by_its_name(self):
        self.assertTrue(core.legacy_trail_of("|AT_MOTION_TRAILS3|AT_trail_DaggerMesh3Handle", "DaggerMesh"))
        self.assertTrue(core.legacy_trail_of("|g|AT_trail_DaggerMesh_aimUpHandle", "DaggerMesh_aimUp"))
        self.assertFalse(core.legacy_trail_of("|g|AT_trail_DaggerMesh_aimUpHandle", "DaggerMesh"))

    def test_clear_takes_only_the_selection_s_trails(self):
        handles = [("|g|AT_trail_HandLHandle", "uuid-hand"), ("|g|AT_trail_HeadHandle", "uuid-head"),
                   ("|g|AT_trail_DaggerMesh3Handle", None), ("|g|AT_trail_Foot2Handle", None)]
        self.assertEqual(core.handles_of(handles, [("uuid-hand", "HandL"), ("uuid-dagger", "DaggerMesh")]),
                         ["|g|AT_trail_HandLHandle", "|g|AT_trail_DaggerMesh3Handle"])
        self.assertEqual(core.handles_of(handles, [("uuid-none", "Pelvis")]), [])


class TempControlsInATab(unittest.TestCase):
    """2026-10-26, «чому не працює Temp Control?»: in a scene tab the current namespace is the tab's, so
    the group Maya made was `tab_x:AT_TEMP` while the code parented to `AT_TEMP` (No object matches
    name), and `ls("AT_tempCtrl_*")` never saw the tab's locators - every click made one more."""

    def test_a_name_in_the_current_namespace(self):
        self.assertEqual(core.here("AT_TEMP", ":tab_x"), ":tab_x:AT_TEMP")
        self.assertEqual(core.here("AT_tempCtrl_*", ":tab_x"), ":tab_x:AT_tempCtrl_*")
        self.assertEqual(core.here("AT_TEMP", ":"), ":AT_TEMP")
        self.assertEqual(core.here("AT_TEMP", ""), ":AT_TEMP")

    def _fake(self, existing):
        fake = mock.MagicMock()
        fake.namespaceInfo.return_value = ":tab_x"
        fake.ls.side_effect = lambda pattern, **k: list(existing.get(pattern, []))
        fake.objExists.side_effect = lambda name: name in existing
        return fake

    def test_the_tab_s_temp_controls_are_found_and_baked_back(self):
        fake = self._fake({":tab_x:AT_tempCtrl_*": ["|tab_x:AT_tempCtrl_IKArm_L"]})
        with mock.patch.object(core, "cmds", fake), \
                mock.patch.object(core, "_release_temp_controls") as release:
            self.assertTrue(core.temp_controls_active())
            core.toggle_temp_controls()
        release.assert_called_once_with(["|tab_x:AT_tempCtrl_IKArm_L"])

    def test_the_group_is_the_node_maya_made(self):
        fake = self._fake({})
        fake.createNode.return_value = "tab_x:AT_TEMP"
        with mock.patch.object(core, "cmds", fake):
            self.assertEqual(core._temp_group(), "tab_x:AT_TEMP")
        fake = self._fake({":tab_x:AT_TEMP": []})
        with mock.patch.object(core, "cmds", fake):
            self.assertEqual(core._temp_group(), ":tab_x:AT_TEMP")
        fake.createNode.assert_not_called()

    def test_the_tab_s_temp_pivot_is_found(self):
        fake = self._fake({":tab_x:AT_tempPivot": []})
        with mock.patch.object(core, "cmds", fake):
            self.assertTrue(core.temp_pivot_active())


class RelationshipInRange(unittest.TestCase):
    """2026-10-23, «прив'язку на всі ключі заміни на прив'язку тільки виділеної кількості ключів,
    умовно з 10 по 20»: the paste on the keys inside the Time Bar's highlight, none on all keys."""

    def test_keys_in_range_count_both_ends(self):
        self.assertEqual(core.keys_in_range([0, 5, 10, 14, 20, 21, 10], 10, 20), [10, 14, 20])
        self.assertEqual(core.keys_in_range([0, 30], 10, 20), [])

    def _paste(self, span, keys):
        ran = []
        fake = mock.MagicMock()
        fake.objExists.return_value = True
        with mock.patch.object(core, "cmds", fake), \
                mock.patch.object(core, "_clip", {"rel": ("anchor", [("follower", [1.0] * 16, [0, 0, 0])])}), \
                mock.patch.object(core, "highlighted_range", return_value=span), \
                mock.patch.object(core, "key_times", return_value=keys), \
                mock.patch.object(core, "run_at_times", side_effect=lambda times, fn: ran.extend(times)), \
                mock.patch.object(core, "warn", side_effect=lambda text: ran.append(text)), \
                mock.patch.object(core, "message"):
            core.paste_relationship(in_range=True)
        return ran

    def test_the_paste_walks_only_the_highlighted_keys(self):
        self.assertEqual(self._paste((10, 20), [0, 4, 10, 12, 18, 20, 26]), [10, 12, 18, 20])

    def test_without_a_highlight_it_asks_for_one(self):
        ran = self._paste(None, [0, 10, 20])
        self.assertEqual(len(ran), 1)
        self.assertIn("highlight", ran[0])

    def test_the_all_keys_paste_is_gone(self):
        import inspect
        self.assertNotIn("all_keys", inspect.signature(core.paste_relationship).parameters)

    def _keyed(self, layer):
        fake = mock.MagicMock()
        fake.getAttr.return_value = 5.0
        with mock.patch.object(core, "cmds", fake), \
                mock.patch.object(core, "free_transform_attrs", return_value=["tx", "ry"]), \
                mock.patch.object(core, "_key_layer", return_value=layer):
            core.key_transform("arm", 12.0, force=True)
        return fake

    def test_a_layered_scene_keys_the_active_layer_with_the_final_value(self):
        # 2026-10-27, «по одному працює, але виділені ні»: no animLayer flag - Maya keyed the muted layer
        base = types.SimpleNamespace(name="skeldarTabsLayerRoot", base=True)
        fake = self._keyed(base)
        for call in fake.setKeyframe.call_args_list:
            self.assertEqual(call.kwargs["animLayer"], "skeldarTabsLayerRoot")
            self.assertEqual((call.kwargs["time"], call.kwargs["value"]), (12.0, 5.0))
        self.assertEqual([c.args[0] for c in fake.setKeyframe.call_args_list], ["arm.tx", "arm.ry"])
        fake.animLayer.assert_not_called()

    def test_a_selected_layer_takes_the_plug_first(self):
        fake = self._keyed(types.SimpleNamespace(name="Upper", base=False))
        fake.animLayer.assert_any_call("Upper", edit=True, attribute="arm.tx")
        self.assertEqual(fake.setKeyframe.call_args_list[0].kwargs["animLayer"], "Upper")

    def test_only_a_live_override_above_hides_the_selected_layer(self):
        stack = ["root", "Lower", "Upper", "Over", "Off"]
        affected = {"root", "Lower", "Upper", "Over", "Off"}
        override = {"Over": True, "Off": True}
        self.assertEqual(core.overriding_above(stack, "Lower", affected, override, {"Off": True}, {}), ["Over"])
        self.assertEqual(core.overriding_above(stack, "Lower", affected, override, {}, {"Over": 0.0}), ["Off"])
        self.assertEqual(core.overriding_above(stack, "Lower", affected - {"Over", "Off"}, override, {}, {}), [])
        self.assertEqual(core.overriding_above(stack, "Over", affected, {"Over": True}, {}, {}), [])

    def test_no_layers_keys_as_before(self):
        fake = self._keyed(None)
        fake.setKeyframe.assert_called_once_with("arm", attribute=["tx", "ry"], t=12.0)


class SetLibrary(unittest.TestCase):
    """2026-10-23, «щоб селекшн сет зберігався в ядрі АТ ... в будь-якій сцені»: the sets in a library
    of the animator's own, members found again by name in whatever scene is open."""

    def test_a_member_is_kept_without_its_namespaces(self):
        self.assertEqual(core.member_keys(["tab_x:Manny_Rig1:FKWrist_L", "|grp|Manny_Rig1:FKElbow_L",
                                           "Manny_Rig1:FKWrist_L", "DaggerMesh"]),
                         ["FKWrist_L", "FKElbow_L", "DaggerMesh"])

    def test_a_set_made_on_one_rig_finds_the_rig_of_another_scene(self):
        self.assertEqual(core.resolve(["FKWrist_L", "FKElbow_L"], ["Manny_Rig:FKWrist_L", "Manny_Rig:FKElbow_L"]),
                         ["Manny_Rig:FKWrist_L", "Manny_Rig:FKElbow_L"])

    def test_two_rigs_one_character_the_selected_one(self):
        found = ["Manny_Rig:FKWrist_L", "Manny_Rig1:FKWrist_L", "Manny_Rig:FKElbow_L", "Manny_Rig1:FKElbow_L"]
        self.assertEqual(core.resolve(["FKWrist_L", "FKElbow_L"], found, prefer=["Manny_Rig1"]),
                         ["Manny_Rig1:FKWrist_L", "Manny_Rig1:FKElbow_L"])
        self.assertEqual(core.resolve(["FKWrist_L", "FKElbow_L"], found),
                         ["Manny_Rig:FKWrist_L", "Manny_Rig:FKElbow_L"])

    def test_the_rig_holding_most_of_the_set_wins_and_a_prop_at_the_root_comes_along(self):
        found = ["Other:FKWrist_L", "Manny_Rig1:FKWrist_L", "Manny_Rig1:FKElbow_L", "DaggerMesh"]
        self.assertEqual(core.resolve(["FKWrist_L", "FKElbow_L", "DaggerMesh"], found),
                         ["Manny_Rig1:FKWrist_L", "Manny_Rig1:FKElbow_L", "DaggerMesh"])

    def test_a_scene_tab_keeps_to_its_own_namespace(self):
        found = ["Manny_Rig:FKWrist_L", "tab_b:Manny_Rig:FKWrist_L"]
        self.assertEqual(core.resolve(["FKWrist_L"], found, within="tab_b"), ["tab_b:Manny_Rig:FKWrist_L"])

    def test_a_missing_member_is_skipped(self):
        self.assertEqual(core.resolve(["FKWrist_L", "Gone"], ["R:FKWrist_L"]), ["R:FKWrist_L"])

    def test_the_scene_s_old_sets_are_taken_once(self):
        lib = {"sets": {"hands": {"members": ["A"], "colour": "#fff"}}, "seen": []}
        scene = [("hands", ["R:B"]), ("L_fingers", ["Manny_Rig1:FKThumbFinger1_L"])]
        self.assertTrue(core.take_scene_sets(lib, scene))
        self.assertEqual(lib["sets"]["hands"]["members"], ["A"])
        self.assertEqual(lib["sets"]["L_fingers"]["members"], ["FKThumbFinger1_L"])
        del lib["sets"]["L_fingers"]
        self.assertFalse(core.take_scene_sets(lib, scene))
        self.assertNotIn("L_fingers", lib["sets"])

    def test_the_library_round_trips_and_a_broken_file_reads_empty(self):
        import tempfile
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "sets.json")
        self.assertEqual(core.load_library(path), {"sets": {}, "seen": []})
        lib = {"sets": {"hands": {"members": ["FKWrist_L"], "colour": None}}, "seen": ["hands"]}
        core.save_library(lib, path)
        self.assertEqual(core.load_library(path), lib)
        self.assertFalse(os.path.exists(path + ".partial"))
        with open(path, "w") as f:
            f.write("{broken")
        self.assertEqual(core.load_library(path), {"sets": {}, "seen": []})


class Smoothing(unittest.TestCase):
    """The SM slider (2026-10-21): left smooths - gradually, pass by pass - right roughens."""

    def test_jitter_is_removed_not_flipped(self):
        noise = [10.0, -10.0] * 6
        out = core.smoothed(noise, 3)
        self.assertLess(max(abs(v) for v in out[2:-2]), 1.0)

    def test_zero_changes_nothing_and_each_step_left_smooths_more(self):
        values = [0.0, 10.0, -10.0, 10.0, -10.0, 50.0, 10.0, -10.0, 0.0]
        levels = core.smoothing_levels(values)
        spike = [level[5] for level in levels]
        self.assertEqual(core.smooth_at(spike, -0.0), 50.0)
        shown = [core.smooth_at(spike, p) for p in (-0.05, -0.25, -0.5, -1.0, -1.5)]
        self.assertEqual(shown, sorted(shown, reverse=True))
        self.assertAlmostEqual(core.smooth_at(spike, -0.125), (spike[0] + spike[1]) / 2.0)
        self.assertAlmostEqual(core.smooth_at(spike, -1.0), spike[core.SM_PASSES_AT_100])
        self.assertAlmostEqual(core.smooth_at(spike, -9.0), spike[-1])


class Recovery(unittest.TestCase):
    """2026-10-22, «після відкриття останньої версії я маю побачити останні збережені зміни»: the backup
    offered when a scene opens is its newest one made after the file was saved."""

    STEM = "AS_Dagger_14"
    SAVED = datetime.datetime(2026, 10, 22, 15, 47, 23)

    def test_the_newest_backup_after_the_save_is_offered(self):
        names = ["AS_Dagger_14_20261022_154000.mb", "AS_Dagger_14_20261022_163505.mb",
                 "AS_Dagger_14_20261022_155005.ma", "AS_Dagger_14_20261022_170000.partial.mb"]
        self.assertEqual(core.newest_backup(self.STEM, self.SAVED, names), "AS_Dagger_14_20261022_163505.mb")

    def test_nothing_when_every_backup_is_older_than_the_save(self):
        names = ["AS_Dagger_14_20261022_154000.mb", "AS_Dagger_14_20261022_154723.mb"]
        self.assertIsNone(core.newest_backup(self.STEM, self.SAVED, names))

    def test_another_scene_s_backups_are_not_its_own(self):
        names = ["AS_Dagger_14_2_20261022_163505.mb", "AS_Dagger_1_20261022_163505.mb", "AS_Dagger_20261022_163505.mb"]
        self.assertEqual(core.backups_of(self.STEM, names), [])
        self.assertEqual(core.backups_of("AS_Dagger_14_2", names),
                         [(datetime.datetime(2026, 10, 22, 16, 35, 5), "AS_Dagger_14_2_20261022_163505.mb")])
        self.assertEqual(core.backups_of("AS_Dagger", names),
                         [(datetime.datetime(2026, 10, 22, 16, 35, 5), "AS_Dagger_20261022_163505.mb")])


if __name__ == "__main__":
    unittest.main()

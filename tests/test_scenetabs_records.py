"""maya_scenetabs.records: the session as data, pure (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import os
import subprocess
import sys
import tempfile
import unittest

from maya_scenetabs import records

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def _tab(ns, path="", modified=False, unit="ntsc", ranges=None):
    tab = records.new_tab(ns, path, unit, ranges or {"minTime": 0.0, "maxTime": 50.0})
    tab["modified"] = modified
    return tab


class Names(unittest.TestCase):

    def test_a_tab_namespace_is_its_files_stem_with_the_prefix(self):
        self.assertEqual(records.namespace_for("C:/a/attack_01.ma", []), "tab_attack_01")

    def test_illegal_characters_become_underscores(self):
        self.assertEqual(records.namespace_for("C:/a/my attack-v2.final.mb", []), "tab_my_attack_v2_final")

    def test_a_taken_namespace_gets_a_number(self):
        self.assertEqual(records.namespace_for("x/attack.ma", ["tab_attack", ":tab_attack1"]), "tab_attack2")

    def test_no_file_is_untitled(self):
        self.assertEqual(records.namespace_for("", ["UI", "shared"]), "tab_untitled")

    def test_the_prefix_keeps_a_rigs_namespace_free(self):
        # a tab opened from assets/Manny_Rig.ma must not BE the namespace its rig moves into on a save
        self.assertNotEqual(records.namespace_for("assets/Manny_Rig.ma", []), "Manny_Rig")


class Units(unittest.TestCase):

    def test_the_ma_header_line(self):
        text = '//Maya ASCII 2027 scene\nrequires maya "2027";\ncurrentUnit -l centimeter -a degree -t ntsc;\n'
        self.assertEqual(records.unit_from_ma(text), "ntsc")

    def test_the_ma_header_with_a_frame_rate(self):
        self.assertEqual(records.unit_from_ma("currentUnit -l centimeter -a degree -t 23.976fps;"), "23.976fps")

    def test_no_unit_line_is_empty(self):
        self.assertEqual(records.unit_from_ma("createNode transform;"), "")

    def test_the_mb_tuni_chunk_as_measured(self):
        # 2026-10-15, Maya 2027: b'TUNI' + 4 bytes + an 8-byte big-endian size + the name
        data = b"FOR8\x00\x00" + b"TUNI\xfc\x00\x00\x00" + (4).to_bytes(8, "big") + b"film\x00\x00\x00\x00"
        self.assertEqual(records.unit_from_mb(data), "film")
        data = b"TUNI\xfc\x00\x00\x00" + (5).to_bytes(8, "big") + b"ntscf\x00\x00\x00"
        self.assertEqual(records.unit_from_mb(data), "ntscf")

    def test_a_broken_mb_chunk_is_empty(self):
        self.assertEqual(records.unit_from_mb(b"TUNI\x00\x00\x00\x00" + (900).to_bytes(8, "big")), "")
        self.assertEqual(records.unit_from_mb(b"no chunk here"), "")

    def test_read_unit_reads_either_kind_from_disk(self):
        folder = tempfile.mkdtemp()
        ma = os.path.join(folder, "a.ma")
        with open(ma, "w") as fh:
            fh.write("currentUnit -l centimeter -a degree -t film;\n")
        mb = os.path.join(folder, "b.mb")
        with open(mb, "wb") as fh:
            fh.write(b"TUNI\xfc\x00\x00\x00" + (4).to_bytes(8, "big") + b"ntsc\x00\x00\x00\x00")
        self.assertEqual(records.read_unit(ma), "film")
        self.assertEqual(records.read_unit(mb), "ntsc")
        self.assertEqual(records.read_unit(os.path.join(folder, "missing.ma")), "")


class Ranges(unittest.TestCase):

    def test_ranges_from_the_config_node(self):
        got = records.ranges_from_script("playbackOptions -min 5 -max 40 -ast 0 -aet 45 ;")
        self.assertEqual(got, {"minTime": 5.0, "maxTime": 40.0, "animationStartTime": 0.0, "animationEndTime": 45.0})

    def test_the_config_script_round_trips(self):
        ranges = {"minTime": 1.25, "maxTime": 150.0, "animationStartTime": 0.0, "animationEndTime": 200.5}
        self.assertEqual(records.ranges_from_script(records.config_script(ranges)), ranges)

    def test_no_ranges_no_script(self):
        self.assertEqual(records.config_script({}), "")

    def test_range_text(self):
        self.assertEqual(records.range_text({"minTime": 0.0, "maxTime": 50.0}), "0-50")
        self.assertEqual(records.range_text({}), "?")


class Furniture(unittest.TestCase):

    def test_maya_managers_and_the_files_copies_are_furniture(self):
        for leaf, kind in (("renderLayerManager", "renderLayerManager"), ("defaultRenderLayer", "renderLayer"),
                           ("lightLinker1", "lightLinker"), ("shapeEditorManager", "shapeEditorManager"),
                           ("UsdDefaultRenderSettings", "UsdDefaultSettings"), ("defaultLayer", "displayLayer"),
                           ("uiConfigurationScriptNode", "script")):
            self.assertTrue(records.is_furniture(leaf, kind), leaf)

    def test_the_config_node_and_a_users_nodes_are_not(self):
        self.assertFalse(records.is_furniture("sceneConfigurationScriptNode", "script"))
        self.assertFalse(records.is_furniture("hero", "transform"))
        self.assertFalse(records.is_furniture("cubesLayer", "displayLayer"))
        self.assertFalse(records.is_furniture("Layer1", "animLayer"))


class State(unittest.TestCase):

    def test_round_trip(self):
        state = records.empty_state()
        state = records.with_tab(state, _tab("tab_a", "C:/a.ma"))
        state = records.with_tab(state, _tab("tab_b", "C:/b.ma"))
        state["active"], state["session"] = "tab_b", "C:/s/session_1.ma"
        self.assertEqual(records.loads(records.dumps(state)), state)

    def test_bad_json_is_an_empty_state(self):
        self.assertEqual(records.loads("{nope"), records.empty_state())
        self.assertEqual(records.loads('{"version": 99, "tabs": []}'), records.empty_state())

    def test_an_unknown_active_falls_back_to_the_first_tab(self):
        state = records.with_tab(records.empty_state(), _tab("tab_a"))
        state["active"] = "tab_gone"
        self.assertEqual(records.loads(records.dumps(state))["active"], "tab_a")

    def test_with_tab_replaces_in_place_and_inserts_at_an_index(self):
        state = records.empty_state()
        for ns in ("tab_a", "tab_b", "tab_c"):
            state = records.with_tab(state, _tab(ns))
        state = records.with_tab(state, _tab("tab_b", "C:/new.ma"))
        self.assertEqual([t["ns"] for t in state["tabs"]], ["tab_a", "tab_b", "tab_c"])
        self.assertEqual(records.tab(state, "tab_b")["path"], "C:/new.ma")
        state = records.with_tab(state, _tab("tab_x"), index=1)
        self.assertEqual([t["ns"] for t in state["tabs"]], ["tab_a", "tab_x", "tab_b", "tab_c"])

    def test_removed_hands_active_to_the_right_neighbour_else_the_left(self):
        state = records.empty_state()
        for ns in ("tab_a", "tab_b", "tab_c"):
            state = records.with_tab(state, _tab(ns))
        state["active"] = "tab_b"
        self.assertEqual(records.removed(state, "tab_b")["active"], "tab_c")
        state["active"] = "tab_c"
        self.assertEqual(records.removed(state, "tab_c")["active"], "tab_b")
        state["active"] = "tab_a"
        self.assertEqual(records.removed(state, "tab_c")["active"], "tab_a")


class Bar(unittest.TestCase):

    def test_one_scene_is_one_item_without_a_close_button(self):
        items = records.bar_items(records.empty_state(), "C:/a/attack.ma", True)
        self.assertEqual(items, [{"ns": "", "text": "attack*", "tip": "C:/a/attack.ma", "active": True, "closable": False}])

    def test_an_unsaved_single_scene_is_untitled(self):
        self.assertEqual(records.bar_items(records.empty_state(), "", False)[0]["text"], "untitled")

    def test_tabs_carry_star_tooltip_and_active(self):
        state = records.empty_state()
        state = records.with_tab(state, _tab("tab_a", "C:/a/attack.ma", modified=True))
        state = records.with_tab(state, _tab("tab_b", "C:/a/walk.mb", unit="film"))
        state["active"] = "tab_b"
        items = records.bar_items(state, "C:/s/session.ma", scene_modified=True)
        self.assertEqual([i["text"] for i in items], ["attack*", "walk*"])
        self.assertEqual([i["active"] for i in items], [False, True])
        self.assertEqual(items[1]["tip"], "C:/a/walk.mb\nfilm, 0-50")
        self.assertTrue(all(i["closable"] for i in items))


class Saves(unittest.TestCase):

    def test_saving_to_the_sessions_name_is_save(self):
        self.assertEqual(records.save_plan("C:/s/session_1.ma", "C:/s/session_1.ma"), ("save", ""))
        self.assertEqual(records.save_plan("", "C:/s/session_1.ma"), ("save", ""))

    def test_any_other_name_is_save_as(self):
        self.assertEqual(records.save_plan("C:/w/new.ma", "C:/s/session_1.ma"), ("save_as", "C:/w/new.ma"))

    def test_same_file_ignores_case_and_slashes(self):
        self.assertTrue(records.same_file("C:/A/b.ma", "c:\\a\\B.ma"))

    def test_autosave_is_inside_the_autosave_folder(self):
        self.assertTrue(records.is_autosave("C:/p/autosave/session_1.0001.ma", "C:/p/autosave/"))
        self.assertFalse(records.is_autosave("C:/p/scenes/a.ma", "C:/p/autosave/"))
        self.assertFalse(records.is_autosave("C:/p/a.ma", ""))

    def test_an_emergency_save_is_maya_crash_save(self):
        temp = "C:/Users/me/AppData/Local/Temp"
        self.assertTrue(records.is_emergency(temp + "/untitled.ma", temp))
        self.assertTrue(records.is_emergency("D:/x/Manny_Rig[Recovered-MY PC.2026-10-01-11.55].ma", temp))
        self.assertTrue(records.is_emergency("D:/x/scene_Recovered-2.ma", temp))
        self.assertFalse(records.is_emergency(temp + "/tool/work.ma", temp))     # a folder inside temp
        self.assertFalse(records.is_emergency("C:/p/scenes/a.ma", temp))
        self.assertFalse(records.is_emergency("", temp))

    def test_changed_on_disk(self):
        path = os.path.join(tempfile.mkdtemp(), "a.ma")
        with open(path, "w") as fh:
            fh.write("x")
        stamp = os.path.getmtime(path)
        self.assertFalse(records.changed_on_disk(path, stamp))
        os.utime(path, (stamp + 30, stamp + 30))
        self.assertTrue(records.changed_on_disk(path, stamp))
        self.assertFalse(records.changed_on_disk(path, 0.0))

    def test_holds_session_finds_the_node_name_in_the_file(self):
        folder = tempfile.mkdtemp()
        yes, no = os.path.join(folder, "s.ma"), os.path.join(folder, "n.ma")
        with open(yes, "w") as fh:
            fh.write('createNode network -n "skeldarSceneTabs";\n')
        with open(no, "w") as fh:
            fh.write('createNode transform -n "hero";\n')
        self.assertTrue(records.holds_session(yes))
        self.assertFalse(records.holds_session(no))

    def test_session_name(self):
        self.assertEqual(records.session_name("C:/u/SkeldarTabs/", "20261015_120000"),
                         "C:/u/SkeldarTabs/session_20261015_120000.ma")


class Purity(unittest.TestCase):

    def test_records_imports_no_maya_and_no_qt(self):
        code = ("import sys; sys.path.insert(0, %r); from maya_scenetabs import records;"
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; print(bad)"
                % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()

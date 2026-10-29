"""Animation Setup's montage half: the kind switch, the slot row, the export.

On the same fake card the other window tests use (controls by name, an
optionMenu with items, the editor faked).
"""

import os
import unittest

from maya_uebridge import montage, records, uelink, uescripts, window

from tests.test_uebridge_window_more import Base, NODES

MONT = "/Game/Block/Montages/AM_LongSword_Block_Stun"
C3 = "/Game/Block/3P/LongSword_Block_Stun_3P"
IN_1P = "/Game/Block/1P/LongSword_Block_Stun_In_1P"
IDLE_1P = "/Game/Block/1P/LongSword_Block_Stun_Idle_1P"
NONE = "<AdditiveAnimationType.AAT_NONE: 0>"

LIST_PAYLOAD = {
    "project": "C:/p/Atone/Atone.uproject", "content_dir": "C:/p/Atone/Content",
    "assets": [{"name": "AM_LongSword_Block_Stun", "package": MONT,
                "skeleton": "SK_Mannequin_proto", "kind": "montage"},
               {"name": "AM_Grab_Reach", "package": "/Game/Sword/AM_Grab_Reach",
                "skeleton": "SK_Mannequin_proto", "kind": "montage"}]}


def segment(clip, start_pos, lo, hi, rate, additive=NONE):
    return {"clip": clip, "clip_name": clip.rsplit("/", 1)[-1],
            "start_pos": start_pos, "anim_start_time": lo, "anim_end_time": hi,
            "anim_play_rate": rate, "looping_count": 1, "additive": additive,
            "clip_length": 1.3666667, "clip_frames": 42}


PLAN_PAYLOAD = {"montages": {MONT: {
    "name": "AM_LongSword_Block_Stun", "length": 1.9358833,
    "skeleton": "SK_Mannequin_proto", "sections": [],
    "slots": [{"slot": "DefaultSlot", "segments": [
        segment(C3, 0.0, 0.0, 0.33, 0.52),
        segment(C3, 0.6346154, 0.33, 0.63, 0.475),
        segment(C3, 1.2661943, 0.63, 1.3666667, 1.1)]},
              {"slot": "1P", "segments": [
                  segment(IN_1P, 0.0, 0.0, 0.6333333, 1.0),
                  segment(IDLE_1P, 0.6333333, 0.0, 0.6333333, 1.0)]}]}}}

EXPORT_PAYLOAD = {"clips": {
    IN_1P: {"path": "C:/t/clips/LongSword_Block_Stun_In_1P.fbx", "fps": 30.0,
            "frames": 21, "length": 0.6666667},
    IDLE_1P: {"path": "C:/t/clips/LongSword_Block_Stun_Idle_1P.fbx",
              "fps": 30.0, "frames": 21, "length": 0.6666667}},
    "failed": {}}


class MontageBase(Base):
    def setUp(self):
        Base.setUp(self)
        window._STATE["asset_kind"] = None
        window._STATE["montage_plans"] = {}
        self.card.prefdir = self.tmp
        self.ran = []

    def editor(self, answers):
        """The editor answering a script with whatever `answers` says."""
        def run(script, out, project=None):
            self.ran.append((script, out, project))
            for mark, payload in answers:
                if mark in script:
                    return payload
            return {}
        self.patch(uelink, "run_script", run)

    def montage_record(self):
        """The Block_Stun row - `parse_payload` sorts by name, so not [0]."""
        for record in records.parse_payload(LIST_PAYLOAD):
            if record.package == MONT:
                return record
        raise AssertionError("the fixture lost its montage")


class Kind(MontageBase):
    def test_the_kind_is_animations_until_it_is_switched(self):
        self.assertEqual(window.asset_kind(), "anims")
        self.assertEqual(window.asset_word(), "animations")

    def test_the_kind_is_remembered(self):
        self.card.vars[window._ASSET_KIND] = "montages"
        window._STATE["asset_kind"] = None
        self.assertEqual(window.asset_kind(), "montages")
        self.assertEqual(window.asset_word(), "montages")

    def test_a_file_source_has_no_montages(self):
        self.card.vars[window._ASSET_KIND] = "montages"
        window._STATE.update({"asset_kind": None, "source": "folder"})
        self.assertEqual(window.asset_kind(), "anims")

    def test_a_broken_memory_reads_as_animations(self):
        self.card.vars[window._ASSET_KIND] = "nonsense"
        window._STATE["asset_kind"] = None
        self.assertEqual(window.asset_kind(), "anims")

    def test_switching_remembers_and_asks_for_a_refresh_when_empty(self):
        self.card_with_rows()
        window.set_asset_kind("montages")
        self.assertEqual(self.card.vars[window._ASSET_KIND], "montages")
        self.assertEqual(window._STATE["records"], [])
        self.assertIn("press Refresh", self.card.controls[window._STATUS]["label"])

    def test_switching_shows_the_kind_s_own_cached_list(self):
        self.card_with_rows()
        window._STATE["asset_kind"] = "montages"
        window.save_cache(records.parse_payload(LIST_PAYLOAD),
                          "C:/p/Atone/Atone.uproject", "Atone")
        window._STATE["asset_kind"] = "anims"
        window.set_asset_kind("montages")
        self.assertEqual([r.name for r in window._STATE["records"]],
                         ["AM_Grab_Reach", "AM_LongSword_Block_Stun"])
        self.assertTrue(all(records.is_montage(r)
                            for r in window._STATE["records"]))

    def test_each_kind_keeps_its_own_cache_file(self):
        window._STATE["asset_kind"] = "anims"
        anims = window.cache_path()
        window._STATE["asset_kind"] = "montages"
        self.assertNotEqual(window.cache_path(), anims)
        self.assertTrue(window.cache_path().endswith("_montages.json"))

    def test_the_list_s_words_follow_the_kind(self):
        self.assertEqual(window.count_line(195, 195, "", "montages"),
                         "195 montages")
        self.assertEqual(window.search_hint(195, "montages"),
                         "search 195 montages")


class Rows(MontageBase):
    def rows(self):
        self.card.layout(window._KIND_ROW)
        self.card.layout(window._SLOT_ROW)

    def test_the_kind_row_is_the_unreal_source_s(self):
        self.rows()
        window._STATE["source"] = "folder"
        window._show_slot_row()
        self.assertFalse(self.card.controls[window._KIND_ROW]["manage"])
        window._STATE["source"] = "unreal"
        window._show_slot_row()
        self.assertTrue(self.card.controls[window._KIND_ROW]["manage"])

    def test_the_slot_row_is_the_montages_kind_s(self):
        self.rows()
        window._STATE.update({"source": "unreal", "asset_kind": "anims"})
        window._show_slot_row()
        self.assertFalse(self.card.controls[window._SLOT_ROW]["manage"])
        window._STATE["asset_kind"] = "montages"
        window._show_slot_row()
        self.assertTrue(self.card.controls[window._SLOT_ROW]["manage"])


class Slots(MontageBase):
    def setUp(self):
        MontageBase.setUp(self)
        self.card.menu(window._SLOT)
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD)])
        self.patch(uescripts, "montage_plan_script",
                   lambda out, packages: "MONTAGE PLAN {0}".format(packages))

    def test_the_dropdown_is_filled_in_the_montage_s_own_order(self):
        chosen = window._fill_slots(self.montage_record())
        self.assertEqual(self.card.labels(window._SLOT),
                         ["DefaultSlot", "1P"])
        self.assertEqual(chosen, "DefaultSlot")

    def test_the_remembered_slot_is_kept_when_the_montage_has_it(self):
        self.card.vars[window.SLOT_VAR] = "1P"
        self.assertEqual(window._fill_slots(self.montage_record()), "1P")
        self.assertEqual(self.card.chosen(window._SLOT), "1P")

    def test_a_remembered_slot_the_montage_lacks_falls_back_to_the_first(self):
        self.card.vars[window.SLOT_VAR] = "UpperBody"
        self.assertEqual(window._fill_slots(self.montage_record()),
                         "DefaultSlot")

    def test_the_plan_is_read_once_per_montage(self):
        window._fill_slots(self.montage_record())
        window._fill_slots(self.montage_record())
        self.assertEqual(len(self.ran), 1)

    def test_an_animation_row_fills_nothing(self):
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "SK", 45, 1.5, 30.0)
        self.assertEqual(window._fill_slots(rec), "")
        self.assertEqual(self.card.labels(window._SLOT), [window.NO_SLOT])
        self.assertEqual(self.ran, [])

    def test_picking_a_slot_remembers_it(self):
        window._fill_slots(self.montage_record())
        self.card.menus[window._SLOT]["select"] = 2
        window.set_montage_slot(window._slot_choice())
        self.assertEqual(self.card.vars[window.SLOT_VAR], "1P")


class Picked(MontageBase):
    def setUp(self):
        MontageBase.setUp(self)
        self.card_with_rows()
        self.card.menu(window._SLOT, ["DefaultSlot", "1P"])
        self.card.menus[window._SLOT]["select"] = 2
        window._STATE["records"] = records.parse_payload(LIST_PAYLOAD)
        window._STATE["asset_kind"] = "montages"
        window._repopulate(quiet=True)
        self.card.textScrollList(window._LIST, edit=True, selectIndexedItem=2)

    def test_a_picked_montage_comes_back_slotted(self):
        picked = window._selected_records()
        self.assertEqual([r.name for r in picked],
                         ["AM_LongSword_Block_Stun_1P"])
        self.assertEqual(records.montage_slot(picked[0]), "1P")
        self.assertEqual(picked[0].package, MONT)

    def test_an_animation_row_is_untouched_by_the_slot(self):
        window._STATE["asset_kind"] = "anims"
        picked = window._selected_records()
        self.assertEqual([r.name for r in picked],
                         ["AM_LongSword_Block_Stun"])

    def test_a_drag_carries_the_slotted_row(self):
        """The ghost's caption and the clip's name must name the slot too."""
        carried = window.drag_records()
        self.assertEqual([r.name for r in carried if r is not None],
                         ["AM_Grab_Reach_1P", "AM_LongSword_Block_Stun_1P"])

    def test_a_drag_in_the_animations_kind_carries_the_rows_as_they_are(self):
        window._STATE["asset_kind"] = "anims"
        carried = window.drag_records()
        self.assertEqual([r.name for r in carried if r is not None],
                         ["AM_Grab_Reach", "AM_LongSword_Block_Stun"])

    def test_the_import_button_names_the_slot(self):
        """A long name is cut in the MIDDLE, so the slot - its tail - shows."""
        self.card.button(window._IMPORT, label="")
        window.paint_import()
        label = self.card.controls[window._IMPORT]["label"]
        self.assertIn("1P", label)
        self.assertIn("AM_Long", label)
        self.assertLessEqual(len(label), records.IMPORT_LABEL_MAX)


class Export(MontageBase):
    def setUp(self):
        MontageBase.setUp(self)
        self.patch(uescripts, "montage_plan_script",
                   lambda out, packages: "MONTAGE PLAN {0}".format(packages))
        self.patch(uescripts, "montage_export_script",
                   lambda out, packages, folder, preview_mesh=False:
                   "MONTAGE EXPORT {0} {1} {2}".format(packages, folder,
                                                       preview_mesh))

    def record(self, slot="1P"):
        return records.with_slot(self.montage_record(), slot)

    def test_the_slot_s_clips_are_exported_in_one_round_trip(self):
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", EXPORT_PAYLOAD)])
        ref, fps = window._export_from_editor(self.record("1P"))
        self.assertTrue(montage.is_ref(ref))
        self.assertEqual(fps, 30.0)
        exports = [script for script, _out, _p in self.ran
                   if script.startswith("MONTAGE EXPORT")]
        self.assertEqual(len(exports), 1)
        self.assertIn(IN_1P, exports[0])
        self.assertIn(IDLE_1P, exports[0])

    def test_the_plan_file_holds_the_spans_and_the_clips(self):
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", EXPORT_PAYLOAD)])
        ref, _fps = window._export_from_editor(self.record("1P"))
        payload = montage.read_plan(montage.plan_file_of(ref))
        self.assertEqual(payload["name"], "AM_LongSword_Block_Stun_1P")
        self.assertEqual(payload["slot"], "1P")
        self.assertEqual(len(payload["spans"]), 2)
        self.assertEqual(set(payload["clips"]), {IN_1P, IDLE_1P})

    def test_an_additive_slot_refuses_before_anything_is_exported(self):
        additive = {"montages": {MONT: {"name": "AM_LongSword_Block_Stun",
                                        "slots": [{"slot": "1P", "segments": [
                                            segment(IN_1P, 0.0, 0.0, 0.6, 1.0,
                                                    additive="AAT_ROTATION")]}]}}}
        self.editor([("MONTAGE PLAN", additive),
                     ("MONTAGE EXPORT", EXPORT_PAYLOAD)])
        with self.assertRaises(uelink.UeBridgeError) as caught:
            window._export_from_editor(self.record("1P"))
        self.assertIn("additive", str(caught.exception))
        self.assertEqual([s for s, _o, _p in self.ran
                          if s.startswith("MONTAGE EXPORT")], [])

    def test_a_slot_the_montage_lacks_takes_its_first_instead(self):
        """The remembered slot can be another montage's; the dropdown falls
        back to the montage's first on a pick, and so does the press - the
        status line then names the slot that came in."""
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", {"clips": {
                         C3: {"path": "C:/t/c.fbx", "fps": 30.0}},
                         "failed": {}})])
        ref, _fps = window._export_from_editor(self.record("UpperBody"))
        payload = montage.read_plan(montage.plan_file_of(ref))
        self.assertEqual(payload["slot"], "DefaultSlot")

    def test_a_clip_the_editor_could_not_export_is_named(self):
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", {"clips": {}, "failed": {
                         IDLE_1P: "could not load the asset"}})])
        with self.assertRaises(uelink.UeBridgeError) as caught:
            window._export_from_editor(self.record("1P"))
        self.assertIn("LongSword_Block_Stun_Idle_1P", str(caught.exception))

    def test_no_slot_picked_takes_the_montage_s_first(self):
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", {"clips": {
                         C3: {"path": "C:/t/c.fbx", "fps": 30.0}},
                         "failed": {}})])
        ref, _fps = window._export_from_editor(self.montage_record())
        payload = montage.read_plan(montage.plan_file_of(ref))
        self.assertEqual(payload["slot"], "DefaultSlot")

    def test_the_mesh_flag_travels_to_the_clip_exports(self):
        self.editor([("MONTAGE PLAN", PLAN_PAYLOAD),
                     ("MONTAGE EXPORT", EXPORT_PAYLOAD)])
        window._export_with_mesh(self.record("1P"))
        exports = [s for s, _o, _p in self.ran if s.startswith("MONTAGE EXPORT")]
        self.assertIn("True", exports[0])

    def test_an_animation_record_never_takes_the_montage_road(self):
        self.editor([("LIST", {})])
        self.patch(window, "_export_unreal",
                   lambda record, mesh=False: ("C:/t/A.fbx", 30.0))
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "SK", 45, 1.5, 30.0)
        self.assertEqual(window._export_from_editor(rec), ("C:/t/A.fbx", 30.0))


class Refresh(MontageBase):
    def setUp(self):
        MontageBase.setUp(self)
        self.card_with_rows()
        self.patch(uelink, "discover_nodes", lambda: NODES[1:])
        self.patch(uescripts, "montage_list_script",
                   lambda out, package_path="/Game": "MONTAGE LIST " + out)
        self.patch(uescripts, "list_script", lambda out: "LIST " + out)
        self.editor([("MONTAGE LIST", LIST_PAYLOAD), ("LIST", {"assets": []})])

    def test_the_montages_kind_asks_for_montages(self):
        window._STATE["asset_kind"] = "montages"
        window._refresh_unreal()
        self.assertTrue(self.ran[0][0].startswith("MONTAGE LIST"))
        self.assertEqual(len(window._STATE["records"]), 2)
        self.assertTrue(all(records.is_montage(r)
                            for r in window._STATE["records"]))
        self.assertIn("2 montages", self.card.controls[window._STATUS]["label"])

    def test_the_animations_kind_asks_for_animations(self):
        window._STATE["asset_kind"] = "anims"
        window._refresh_unreal()
        self.assertTrue(self.ran[0][0].startswith("LIST"))

    def test_a_refresh_forgets_the_plans_it_cached(self):
        window._STATE["asset_kind"] = "montages"
        window._STATE["montage_plans"] = {MONT: {"slots": []}}
        window._refresh_unreal()
        self.assertEqual(window._STATE["montage_plans"], {})

    def test_the_montage_rows_are_cached_under_their_own_name(self):
        window._STATE["asset_kind"] = "montages"
        window._refresh_unreal()
        self.assertTrue(os.path.isfile(window.cache_path("montages")))
        self.assertFalse(os.path.isfile(window.cache_path("anims")))


if __name__ == "__main__":
    unittest.main()

"""maya_moveset.export: the plan over a montage slot, and the press on fakes.

The fixtures are the animator's own graphs' shapes, float32 noise and all
(`2.0333333015441895` is 61 frames at 30 fps): that noise is why `TOL` is a
ten-thousandth of a second rather than an epsilon.
"""
import os
import subprocess
import sys
import unittest

from maya_moveset import export

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")

SWORD = ("/Game/Prototype/Animation/PlayerCharacter/Weapons/Longsword/3P/"
         "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P")
ONE_P = ("/Game/Prototype/Animation/PlayerCharacter/Weapons/Longsword/1P/"
         "AS_Longsword_Attack_Back_Combo_2_Hold_1_1P")
COMBO = ("/Game/Prototype/Animation/PlayerCharacter/Weapons/Longsword/3P/"
         "AS_Longsword_Attack_Light_Forward_Combo_1_3P")


def segment(package, start_pos, lo, hi, length, rate=1.0, loops=1):
    """One of the montage's segments, as the extraction writes it."""
    return {"anim": "{0}.{1}".format(package, package.rsplit("/", 1)[-1]),
            "start_pos": start_pos, "anim_start": lo, "anim_end": hi,
            "anim_length": length, "rate": rate, "loops": loops}


def graph(segments=None, segments1p=None, slot="DefaultSlot", slot1p="1P"):
    node = {"path": "/Game/M/AM_X.AM_X", "slot": slot, "slot1p": slot1p}
    if segments is not None:
        node["segments"] = segments
    if segments1p is not None:
        node["segments1p"] = segments1p
    return {"nodes": {"AM_X": node}, "edges": [], "entries": []}


#  the real one-sequence track: one segment playing all of 2.0333 s
WHOLE = [segment(SWORD, 0.0, 0.0, 2.0333333015441895, 2.0333333015441895)]

#  the real CUT track (6 of the sword's 25 writable rows): one sequence in
#  three pieces, cut at its hit windows, each at rate 1
CUT = [segment(COMBO, 0.0, 0.0, 0.4699999988079071, 1.3666666746139526),
       segment(COMBO, 0.4699999988079071, 0.4699999988079071, 0.6000000238418579,
               1.3666666746139526),
       segment(COMBO, 0.6000000238418579, 0.6000000238418579, 1.3666666746139526,
               1.3666666746139526)]


class Pure(unittest.TestCase):
    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; from maya_moveset import export; "
                "print(sorted(n for n in sys.modules "
                "if n.startswith('maya.') or n.startswith('PySide')))")
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN).decode().strip()
        self.assertEqual(out, "[]")


class Plan(unittest.TestCase):
    def plan(self, data, view="3p", fps=30.0):
        return export.plan(data, "AM_X", view, fps)

    def test_one_segment_is_one_sequence_over_its_own_frames(self):
        pieces, refusal = self.plan(graph(WHOLE))
        self.assertEqual(refusal, "")
        self.assertEqual([tuple(p) for p in pieces],
                         [(SWORD, "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P", 0, 61)])

    def test_a_sequence_cut_at_its_hit_windows_is_one_piece(self):
        """Several segments of ONE sequence at rate 1 play it straight through:
        the whole animation, written back as one."""
        pieces, refusal = self.plan(graph(CUT))
        self.assertEqual(refusal, "")
        self.assertEqual(len(pieces), 1)
        self.assertEqual((pieces[0].anim, pieces[0].start, pieces[0].end),
                         ("AS_Longsword_Attack_Light_Forward_Combo_1_3P", 0, 41))

    def test_the_frames_follow_the_scenes_own_rate(self):
        pieces, _r = self.plan(graph(WHOLE), fps=24.0)
        self.assertEqual(pieces[0].end, 49)

    def test_the_1p_track_is_its_own(self):
        pieces, refusal = self.plan(graph(WHOLE, segments1p=[
            segment(ONE_P, 0.0, 0.0, 3.3333332538604736, 3.3333332538604736)]), view="1p")
        self.assertEqual(refusal, "")
        self.assertEqual((pieces[0].package, pieces[0].end), (ONE_P, 100))

    def test_a_slice_is_refused_by_name_with_its_seconds(self):
        """The real 1P row of that attack: 2.30 s of a 3.33 s sequence. The
        import replaces the whole asset, so the rest would be thrown away."""
        _p, refusal = self.plan(graph([segment(ONE_P, 0.0, 0.0, 2.299999952316284,
                                               3.3333332538604736)]))
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_1P", refusal)
        self.assertIn("0.00-2.30 s of 3.33 s", refusal)
        self.assertIn("slice", refusal)

    def test_a_rate_other_than_one_is_a_time_warp_and_is_refused(self):
        _p, refusal = self.plan(graph([segment(SWORD, 0.0, 0.0, 2.0333333015441895,
                                               2.0333333015441895, rate=2.0)]))
        self.assertIn("rate 2.00", refusal)
        self.assertIn("time warp", refusal)

    def test_a_looping_segment_is_refused(self):
        _p, refusal = self.plan(graph([segment(SWORD, 0.0, 0.0, 2.0333333015441895,
                                               2.0333333015441895, loops=3)]))
        self.assertIn("loops 3 times", refusal)

    def test_pieces_played_out_of_order_are_a_time_warp(self):
        out_of_order = [CUT[0], CUT[2], CUT[1]]
        _p, refusal = self.plan(graph(out_of_order))
        self.assertIn("out of order", refusal)

    def test_a_gap_before_a_sequence_is_refused(self):
        late = [segment(SWORD, 0.5, 0.0, 2.0333333015441895, 2.0333333015441895)]
        _p, refusal = self.plan(graph(late))
        self.assertIn("gap before AS_Longsword_Attack_Back_Combo_2_Hold_1_3P", refusal)

    def test_a_second_sequence_in_the_slot_is_refused_not_guessed(self):
        """Unmeasured: whether Unreal normalises a take that starts at frame 44.
        No track in either graph needs it, so it is refused by name."""
        two = WHOLE + [segment(ONE_P, 2.0333333015441895, 0.0, 1.0, 1.0)]
        _p, refusal = self.plan(graph(two))
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_1P starts 2.03 s into the slot",
                      refusal)
        self.assertIn("not built", refusal)

    def test_no_track_for_the_view(self):
        _p, refusal = self.plan(graph(WHOLE, slot1p=""), view="1p")
        self.assertEqual(refusal, "no 1P track in the montage")
        _p, refusal = self.plan(graph(WHOLE), view="1p")
        self.assertEqual(refusal, "no 1P track in the montage")

    def test_a_card_of_the_animators_own_has_no_montage(self):
        _p, refusal = export.plan(graph(WHOLE), "custom-1", "3p", 30.0)
        self.assertIn("a card of your own", refusal)

    def test_a_segment_naming_no_animation(self):
        nameless = [dict(WHOLE[0], anim="")]
        _p, refusal = self.plan(graph(nameless))
        self.assertIn("names no animation", refusal)

    def test_the_line_names_every_sequence_and_its_frames(self):
        pieces, _r = self.plan(graph(WHOLE))
        self.assertEqual(
            export.line("Back Combo 2 Hold 1", "3p", pieces),
            "Back Combo 2 Hold 1 3P - 1 sequence written: "
            "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P (frames 0-61)")

    def test_the_line_counts_several(self):
        two = [export.Piece("/Game/A/AS_X", "AS_X", 0, 10),
               export.Piece("/Game/A/AS_Y", "AS_Y", 11, 20)]
        self.assertIn("2 sequences written: AS_X (frames 0-10), AS_Y (frames 11-20)",
                      export.line("X", "1p", two))


class Message(unittest.TestCase):
    def test_the_confirm_names_the_asset_the_frames_and_the_skeleton(self):
        pieces, _r = export.plan(graph(WHOLE), "AM_X", "3p", 30.0)
        text = export.message("Back Combo 2 Hold 1", "3p", pieces, "|Manny_Rig_Character|root", 0)
        self.assertIn("Overwrite the animation of Back Combo 2 Hold 1 3P?", text)
        self.assertIn("{0}   frames 0-61".format(SWORD), text)
        self.assertIn("skeleton: root", text)
        self.assertIn("Pose_0..9", text)
        self.assertIn("Perforce is not touched", text)
        self.assertNotIn("read-only", text)

    def test_a_locked_file_is_said_out_loud(self):
        pieces, _r = export.plan(graph(WHOLE), "AM_X", "3p", 30.0)
        text = export.message("X", "3p", pieces, "root", 1)
        self.assertIn("One file is read-only. That flag will be CLEARED and left off.", text)

    def test_several_assets_are_counted(self):
        two = [export.Piece("/Game/A/AS_X", "AS_X", 0, 10),
               export.Piece("/Game/A/AS_Y", "AS_Y", 11, 20)]
        text = export.message("X", "1p", two, "root", 2)
        self.assertIn("Overwrite the 2 animations of X 1P?", text)
        self.assertIn("/Game/A/AS_X   frames 0-10", text)
        self.assertIn("/Game/A/AS_Y   frames 11-20", text)
        self.assertIn("2 files are read-only", text)

    def test_what_was_already_written_is_named_when_a_press_stops(self):
        """The day a slot plays two sequences: the first is written and the
        second fails. The earlier one is not rolled back, and the line says so."""
        written = [export.Piece("/Game/A/AS_X", "AS_X", 0, 10)]
        said = export._stopped("X", "3p", written, "AS_Y: editor: boom")
        self.assertIn("AS_Y: editor: boom", said)
        self.assertIn("already written: AS_X (frames 0-10)", said)
        self.assertEqual(export._stopped("X", "3p", [], "AS_X: boom"), "AS_X: boom")


class Press(unittest.TestCase):
    """The press with neither Maya nor Unreal: every seam is in `asks`.

    Today's graphs never make a press write more than one sequence - every
    writable track is ONE sequence from frame 0, and a second one is refused
    by name - so these run on one piece, and the wording of a stop in the
    middle is pinned above as the pure thing it is.
    """

    def setUp(self):
        self.seen = []
        self.payload = {"ok": True, "saved": True, "frames": 62, "before_frames": 20,
                        "length": 2.03, "before_length": 0.7, "notes": [], "error": ""}

    def asks(self, **over):
        seen = self.seen
        asks = {
            "fps": lambda: 30.0,
            "bridge": lambda: ("C:/P/Content", "P.uproject", "C:/tmp"),
            "root": lambda: "|Manny_Rig_Character|Manny_Rig:root",
            "exists": lambda path: True,
            "read_only": lambda path: False,
            "clear": lambda path: seen.append(("clear", path)) or "",
            "confirm": lambda text: seen.append(("confirm", text)) or True,
            "export": lambda fbx, root, start, end: seen.append(
                ("export", fbx, root, start, end)) or {"joints": 93, "start": start, "end": end},
            "run_script": lambda source, out, project=None: seen.append(
                ("script", source, out, project)) or self.payload,
        }
        asks.update(over)
        return asks

    def press(self, data=None, view="3p", **over):
        return export.export_slot(data or graph(WHOLE), "AM_X", view, "Back Combo",
                                  asks=self.asks(**over))

    def kinds(self):
        return [one[0] for one in self.seen]

    def test_the_piece_exports_its_own_range_and_reimports_its_own_package(self):
        line = self.press()
        export_call = [one for one in self.seen if one[0] == "export"][0]
        self.assertEqual(export_call[3:], (0, 61))
        self.assertTrue(export_call[1].endswith(
            "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P.slot.fbx"))
        self.assertEqual(export_call[2], "|Manny_Rig_Character|Manny_Rig:root")
        script = [one for one in self.seen if one[0] == "script"][0]
        self.assertIn(SWORD, script[1])
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_3P.slot.fbx", script[1])
        self.assertEqual(script[3], "P.uproject")
        self.assertIn("1 sequence written: AS_Longsword_Attack_Back_Combo_2_Hold_1_3P "
                      "(frames 0-61)", line)

    def test_the_confirm_comes_before_the_export(self):
        self.press()
        self.assertEqual(self.kinds()[:2], ["confirm", "export"])

    def test_a_cancel_writes_nothing(self):
        line = self.press(confirm=lambda text: False)
        self.assertEqual(line, export.CANCELLED)
        self.assertEqual(self.kinds(), [])

    def test_a_refused_track_never_asks_and_never_writes(self):
        line = self.press(graph(WHOLE), view="1p")
        self.assertEqual(line, "no 1P track in the montage")
        self.assertEqual(self.seen, [])

    def test_no_content_folder_yet(self):
        line = self.press(bridge=lambda: ("", "P.uproject", "C:/tmp"))
        self.assertEqual(line, export.NO_CONTENT_DIR)
        self.assertEqual(self.seen, [])

    def test_a_missing_uasset_is_named_and_nothing_is_written(self):
        line = self.press(exists=lambda path: False)
        self.assertIn("no uasset at", line)
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_3P.uasset", line)
        self.assertEqual(self.seen, [])

    def test_an_undecidable_skeleton_costs_no_click(self):
        def refuse():
            raise RuntimeError("several skeletons in the scene - select one")
        line = self.press(root=refuse)
        self.assertEqual(line, "several skeletons in the scene - select one")
        self.assertEqual(self.seen, [])

    def test_a_read_only_asset_is_cleared_after_the_export_and_said(self):
        line = self.press(read_only=lambda path: True)
        self.assertEqual(self.kinds(), ["confirm", "export", "clear", "script"])
        self.assertIn("read-only cleared on 1 file", line)

    def test_a_flag_that_cannot_be_cleared_stops_the_press(self):
        line = self.press(read_only=lambda path: True,
                          clear=lambda path: "still not writable")
        self.assertIn("cannot clear read-only", line)
        self.assertIn("still not writable", line)
        self.assertNotIn("script", self.kinds())

    def test_a_failed_export_stops_before_the_flag_and_the_editor(self):
        def boom(fbx, root, start, end):
            raise RuntimeError("the FBX plugin was baking keys every 1/24 s")
        line = self.press(read_only=lambda path: True, export=boom)
        self.assertIn("the FBX plugin was baking keys", line)
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_3P", line)
        self.assertEqual(self.kinds(), ["confirm"])

    def test_an_editor_error_is_the_presss_answer(self):
        self.payload = {"ok": False, "error": "could not load asset"}
        line = self.press()
        self.assertIn("editor: could not load asset", line)
        self.assertNotIn("sequence written", line)

    def test_a_dead_link_stops_the_press(self):
        def boom(source, out, project=None):
            raise RuntimeError("no editor answered on 6766")
        line = self.press(run_script=boom)
        self.assertIn("no editor answered", line)

    def test_a_silent_no_op_is_said_out_loud(self):
        """The worst failure this project keeps finding: ok, saved, no error,
        and the asset untouched (trap: the FBX's bones do not match)."""
        self.payload = dict(self.payload, frames=20, length=0.7)
        line = self.press()
        self.assertIn("sequence written", line)
        self.assertIn("AS_Longsword_Attack_Back_Combo_2_Hold_1_3P:", line)
        self.assertIn("check the exported bones", line.lower())

    def test_an_unsaved_reimport_is_said(self):
        self.payload = dict(self.payload, saved=False)
        line = self.press()
        self.assertIn("NOT saved", line)


if __name__ == "__main__":
    unittest.main()

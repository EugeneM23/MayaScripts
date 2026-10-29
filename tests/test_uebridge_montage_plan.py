"""The montage plan: spans, samples, cuts and refusals. Pure, no Maya.

The numbers are Atone's own, read out of the editor on 2026-10-29:
`AM_SwordShield_1p_blockreact_mid` cuts one clip into three pieces at rates
1.5 / 0.8 / 1.2, and `AM_LongSword_Block_Stun`'s `1P` slot runs three
different clips at rate 1.
"""

import os
import subprocess
import sys
import unittest

from maya_uebridge import montage

MID = "/Game/Block/Montages/AM_SwordShield_1p_blockreact_mid"
C3 = "/Game/Block/3P/AS_Techlimb_Character_Parry_3P_Anim"
C1 = "/Game/Block/1P/AS_Techlimb_Character_Shield_Parry_1P"

NONE = "<AdditiveAnimationType.AAT_NONE: 0>"
ROTATION = "<AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE: 2>"


def segment(clip, start_pos, lo, hi, rate, loops=1, additive=NONE):
    return {"clip": clip, "clip_name": clip.rsplit("/", 1)[-1],
            "start_pos": start_pos, "anim_start_time": lo,
            "anim_end_time": hi, "anim_play_rate": rate,
            "looping_count": loops, "additive": additive,
            "clip_length": 0.8666667, "clip_frames": 27}


PAYLOAD = {"montages": {MID: {
    "name": "AM_SwordShield_1p_blockreact_mid",
    "length": 1.423050045967102,
    "skeleton": "SK_Mannequin_proto",
    "sections": [],
    "slots": [
        {"slot": "DefaultSlot", "segments": [
            segment(C3, 0.0, 0.0, 0.27000001072883606, 1.5),
            segment(C3, 0.18000000715255737, 0.27000001072883606,
                    0.8666666746139526, 0.800000011920929),
            segment(C3, 0.9258333444595337, 0.27000001072883606,
                    0.8666666746139526, 1.2000000476837158)]},
        {"slot": "1P", "segments": [
            segment(C1, 0.0, 0.0, 0.27000001072883606, 1.5),
            segment(C1, 0.18000000715255737, 0.27000001072883606,
                    0.8666666746139526, 0.800000011920929),
            segment(C1, 0.9258333444595337, 0.27000001072883606,
                    0.8666666746139526, 1.2000000476837158)]}]}}}


class Slots(unittest.TestCase):
    def test_the_slots_come_in_the_montage_s_own_order(self):
        self.assertEqual(montage.slots_of(PAYLOAD, MID), ["DefaultSlot", "1P"])

    def test_a_montage_the_payload_does_not_hold_has_no_slots(self):
        self.assertEqual(montage.slots_of(PAYLOAD, "/Game/Nope"), [])

    def test_pick_slot_keeps_the_remembered_one(self):
        self.assertEqual(montage.pick_slot(["DefaultSlot", "1P"], "1P"), "1P")

    def test_pick_slot_falls_back_to_the_first(self):
        self.assertEqual(montage.pick_slot(["FullBody", "1P"], "UpperBody"),
                         "FullBody")

    def test_pick_slot_with_no_slots_is_empty(self):
        self.assertEqual(montage.pick_slot([], "1P"), "")


class Spans(unittest.TestCase):
    def setUp(self):
        self.plan = montage.plan_for(PAYLOAD, MID, "DefaultSlot")

    def test_the_rate_divides_the_slice(self):
        """0.27 s of clip at 1.5 is 0.18 s of montage."""
        self.assertAlmostEqual(self.plan.spans[0].t1, 0.18, places=5)
        self.assertAlmostEqual(self.plan.spans[1].t1, 0.9258333, places=5)
        self.assertAlmostEqual(self.plan.spans[2].t1, 1.4230555, places=5)

    def test_the_end_agrees_with_the_montage_s_own_length(self):
        """The montage reports 1.4230500 and the spans add to 1.4230555 - five
        microseconds apart, which is the float noise in its own rates."""
        self.assertAlmostEqual(self.plan.end, 1.4230555, places=5)
        self.assertAlmostEqual(self.plan.end, PAYLOAD["montages"][MID]["length"],
                               places=4)

    def test_the_spans_abut(self):
        for first, second in zip(self.plan.spans, self.plan.spans[1:]):
            self.assertAlmostEqual(first.t1, second.t0, places=4)

    def test_one_clip_three_times_is_one_clip(self):
        self.assertEqual(self.plan.clips, [C3])

    def test_the_plan_names_the_montage_and_the_slot(self):
        self.assertEqual(self.plan.montage,
                         "AM_SwordShield_1p_blockreact_mid")
        self.assertEqual(self.plan.slot, "DefaultSlot")

    def test_three_different_clips_are_three_clips(self):
        payload = {"montages": {"/Game/AM_Y": {
            "name": "AM_Y", "length": 1.9, "slots": [{"slot": "1P", "segments": [
                segment("/Game/In", 0.0, 0.0, 0.6333333, 1.0),
                segment("/Game/Idle", 0.6333333, 0.0, 0.6333333, 1.0),
                segment("/Game/Out", 1.2666667, 0.0, 0.6666667, 1.0)]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_Y", "1P")
        self.assertEqual(plan.clips, ["/Game/In", "/Game/Idle", "/Game/Out"])
        self.assertAlmostEqual(plan.end, 1.9333334, places=5)

    def test_a_looping_segment_repeats_its_slice(self):
        payload = {"montages": {"/Game/AM_L": {
            "name": "AM_L", "length": 3.0, "slots": [{"slot": "1P", "segments": [
                segment("/Game/C", 0.0, 0.0, 0.5, 1.0, loops=3)]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_L", "1P")
        self.assertEqual(len(plan.spans), 3)
        self.assertAlmostEqual(plan.end, 1.5, places=6)
        self.assertAlmostEqual(plan.spans[1].t0, 0.5, places=6)
        self.assertAlmostEqual(plan.spans[1].src, 0.0, places=6)

    def test_a_zero_length_slice_is_left_out(self):
        payload = {"montages": {"/Game/AM_Z": {
            "name": "AM_Z", "length": 1.0, "slots": [{"slot": "1P", "segments": [
                segment("/Game/C", 0.0, 0.4, 0.4, 1.0),
                segment("/Game/C", 0.0, 0.0, 0.5, 1.0)]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_Z", "1P")
        self.assertEqual(len(plan.spans), 1)


class SourceTime(unittest.TestCase):
    def setUp(self):
        self.plan = montage.plan_for(PAYLOAD, MID, "DefaultSlot")

    def test_the_first_frame_reads_the_slice_s_start(self):
        frame, clip, time = montage.samples(self.plan, 30.0)[0]
        self.assertEqual((frame, clip), (0, C3))
        self.assertAlmostEqual(time, 0.0, places=6)

    def test_a_frame_inside_the_second_span_maps_through_its_rate(self):
        """Frame 6 is 0.2 s: 0.02 s into a span that plays at 0.8."""
        rows = dict((f, (c, t)) for f, c, t in montage.samples(self.plan, 30.0))
        clip, time = rows[6]
        self.assertEqual(clip, C3)
        self.assertAlmostEqual(time, 0.27 + 0.02 * 0.8, places=5)

    def test_the_boundary_frame_belongs_to_the_later_span(self):
        """A span starting exactly at t owns t - the engine starts it there."""
        plan = montage.plan_for(
            {"montages": {"/Game/AM_B": {"name": "AM_B", "length": 1.0,
             "slots": [{"slot": "1P", "segments": [
                 segment("/Game/A", 0.0, 0.0, 0.5, 1.0),
                 segment("/Game/B", 0.5, 0.2, 0.7, 1.0)]}]}}},
            "/Game/AM_B", "1P")
        rows = dict((f, (c, t)) for f, c, t in montage.samples(plan, 10.0))
        self.assertEqual(rows[5][0], "/Game/B")
        self.assertAlmostEqual(rows[5][1], 0.2, places=6)

    def test_the_last_frame_stays_inside_the_slice(self):
        rows = montage.samples(self.plan, 30.0)
        frame, clip, time = rows[-1]
        self.assertEqual(frame, 42)          # floor(1.4230833 * 30)
        self.assertLessEqual(time, 0.8666667 + 1e-6)

    def test_the_frame_count_never_runs_past_the_end(self):
        for fps in (24.0, 30.0, 60.0):
            last = montage.samples(self.plan, fps)[-1][0]
            self.assertLessEqual(last / fps, self.plan.end + 1e-9)

    def test_a_negative_rate_runs_the_source_backwards(self):
        payload = {"montages": {"/Game/AM_N": {
            "name": "AM_N", "length": 1.0, "slots": [{"slot": "1P", "segments": [
                segment("/Game/C", 0.0, 0.0, 0.5, -1.0)]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_N", "1P")
        rows = dict((f, t) for f, _c, t in montage.samples(plan, 10.0))
        self.assertAlmostEqual(rows[0], 0.5, places=6)
        self.assertAlmostEqual(rows[2], 0.3, places=6)
        self.assertAlmostEqual(rows[5], 0.0, places=6)

    def test_every_frame_of_the_take_is_sampled_once(self):
        rows = montage.samples(self.plan, 30.0)
        frames = [row[0] for row in rows]
        self.assertEqual(frames, list(range(len(frames))))


class Cuts(unittest.TestCase):
    def test_the_cuts_are_the_boundaries_in_frames(self):
        plan = montage.plan_for(PAYLOAD, MID, "DefaultSlot")
        self.assertEqual(montage.cuts(plan, 30.0), [5.4, 27.8])

    def test_one_span_has_no_cuts(self):
        payload = {"montages": {"/Game/AM_S": {
            "name": "AM_S", "length": 1.0, "slots": [{"slot": "1P", "segments": [
                segment("/Game/C", 0.0, 0.0, 0.5, 1.0)]}]}}}
        plan = montage.plan_for(payload, "/Game/AM_S", "1P")
        self.assertEqual(montage.cuts(plan, 30.0), [])


class Refusals(unittest.TestCase):
    def test_the_good_payload_is_not_refused(self):
        self.assertEqual(montage.refusal(PAYLOAD, MID, "DefaultSlot"), "")

    def test_a_slot_the_montage_lacks_is_refused_by_name(self):
        text = montage.refusal(PAYLOAD, MID, "UpperBody")
        self.assertIn("UpperBody", text)
        self.assertIn("DefaultSlot", text)

    def test_a_montage_with_no_plan_is_refused(self):
        self.assertIn("Refresh", montage.refusal({"montages": {}}, MID, "1P"))

    def test_an_empty_track_is_refused(self):
        payload = {"montages": {"/Game/AM_E": {
            "name": "AM_E", "length": 0.0,
            "slots": [{"slot": "1P", "segments": []}]}}}
        self.assertIn("no animation",
                      montage.refusal(payload, "/Game/AM_E", "1P"))

    def test_an_additive_clip_is_refused_by_name(self):
        payload = {"montages": {"/Game/AM_A": {
            "name": "AM_A", "length": 1.0, "slots": [
                {"slot": "UpperBodyAdditive", "segments": [
                    segment("/Game/Add", 0.0, 0.0, 0.5, 1.0,
                            additive=ROTATION)]}]}}}
        text = montage.refusal(payload, "/Game/AM_A", "UpperBodyAdditive")
        self.assertIn("additive", text)
        self.assertIn("Add", text)

    def test_a_segment_with_no_clip_is_refused(self):
        payload = {"montages": {"/Game/AM_C": {
            "name": "AM_C", "length": 1.0, "slots": [{"slot": "1P", "segments": [
                segment("", 0.0, 0.0, 0.5, 1.0)]}]}}}
        self.assertIn("no animation",
                      montage.refusal(payload, "/Game/AM_C", "1P"))

    def test_a_segment_at_rate_zero_is_refused(self):
        payload = {"montages": {"/Game/AM_R": {
            "name": "AM_R", "length": 1.0, "slots": [{"slot": "1P", "segments": [
                segment("/Game/C", 0.0, 0.0, 0.5, 0.0)]}]}}}
        self.assertIn("rate", montage.refusal(payload, "/Game/AM_R", "1P"))


class Names(unittest.TestCase):
    def test_the_clip_name_is_the_montage_and_the_slot(self):
        self.assertEqual(montage.clip_name("AM_X", "1P"), "AM_X_1P")

    def test_a_reference_round_trips(self):
        ref = montage.ref_of("C:\\temp\\plan.json")
        self.assertTrue(montage.is_ref(ref))
        self.assertEqual(montage.plan_file_of(ref), "C:/temp/plan.json")

    def test_a_plain_path_is_no_montage_reference(self):
        self.assertFalse(montage.is_ref("C:/temp/clip.fbx"))
        self.assertFalse(montage.is_ref(""))


class Purity(unittest.TestCase):
    def test_the_module_pulls_in_no_maya(self):
        """The plan model is stdlib: it must be testable with no Maya at all."""
        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; import maya_uebridge.montage as m;"
                " bad = [n for n in sys.modules if n == 'maya'"
                " or n.startswith('maya.')];"
                " print('LEAK' if bad else 'CLEAN')")
        out = subprocess.check_output([sys.executable, "-c", code], cwd=root,
                                      stderr=subprocess.STDOUT)
        self.assertIn(b"CLEAN", out)


if __name__ == "__main__":
    unittest.main()

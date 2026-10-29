"""The montage's scan windows: the class pick, the clipping, the frames. Pure.

The numbers are Atone's own, read out of the editor on 2026-10-29:
`AM_Longsword_Attack_Left_Forward_Hold` carries four MeleeScanWindow states at
0.600+0.397, 1.000+0.115, 1.114+0.187 and 1.301+0.107, and two of the project's
90 windows are NAMED `GameplayEvent Window` while every one of them is of class
`AnimNotifyState_MeleeScanWindow`.
"""

import unittest

from maya_uebridge import montage

HOLD = "/Game/Longsword/Montages/AM_Longsword_Attack_Left_Forward_Hold"
CLIP = "/Game/Longsword/3P/LongSword_Attack_Left_Forward_3P"

SCAN = "AnimNotifyState_MeleeScanWindow"


def notify(name, trigger, duration, klass=SCAN, state=True):
    return {"name": name, "class": klass, "state": state,
            "trigger": trigger, "duration": duration}


def segment(clip, start_pos, lo, hi, rate):
    return {"clip": clip, "clip_name": clip.rsplit("/", 1)[-1],
            "start_pos": start_pos, "anim_start_time": lo,
            "anim_end_time": hi, "anim_play_rate": rate,
            "looping_count": 1,
            "additive": "<AdditiveAnimationType.AAT_NONE: 0>"}


PAYLOAD = {"montages": {HOLD: {
    "name": "AM_Longsword_Attack_Left_Forward_Hold",
    "length": 2.4333334,
    "skeleton": "SK_Mannequin_proto",
    "sections": [],
    "notifies": [
        notify("Melee Transition Window", 0.0, 0.25,
               "AnimNotifyState_MeleeTransitionWindow"),
        notify("PlaySound", 0.0, 0.0, "AnimNotify_PlaySound", state=False),
        notify("MeleeScanWindow", 0.6, 0.3966667),
        notify("MeleeScanWindow", 1.0, 0.1150000),
        notify("GameplayEvent Window", 1.1136667, 0.1866667),
        notify("MeleeScanWindow", 1.3013333, 0.1066667)],
    "slots": [
        {"slot": "DefaultSlot", "segments": [
            segment(CLIP, 0.0, 0.0, 2.4333334, 1.0)]},
        {"slot": "Short", "segments": [
            segment(CLIP, 0.0, 0.0, 1.2, 1.0)]}]}}}


class IsScan(unittest.TestCase):
    def test_a_scan_window_is_known_by_its_class(self):
        self.assertTrue(montage.is_scan(notify("whatever", 1.0, 0.1)))

    def test_the_two_oddly_named_ones_count(self):
        """Two of Atone's 90 are named `GameplayEvent Window`."""
        self.assertTrue(montage.is_scan(
            notify("GameplayEvent Window", 1.0, 0.1)))

    def test_another_window_class_is_not_a_scan(self):
        self.assertFalse(montage.is_scan(
            notify("Combo Window", 1.0, 0.7, "AnimNotifyState_ComboWindow")))

    def test_a_point_notify_is_not_a_scan(self):
        self.assertFalse(montage.is_scan(
            notify("Footstep", 1.0, 0.0, "AnimNotify_Footstep", state=False)))

    def test_a_row_with_no_class_is_not_a_scan(self):
        self.assertFalse(montage.is_scan({"name": "MeleeScanWindow"}))

    def test_nothing_is_not_a_scan(self):
        self.assertFalse(montage.is_scan(None))


class WindowsOf(unittest.TestCase):
    def test_the_four_scan_windows_of_the_hold(self):
        windows = montage.windows_of(PAYLOAD, HOLD)
        self.assertEqual(len(windows), 4)
        self.assertEqual([round(w.t0, 4) for w in windows],
                         [0.6, 1.0, 1.1137, 1.3013])

    def test_a_window_keeps_its_own_name(self):
        self.assertEqual([w.name for w in montage.windows_of(PAYLOAD, HOLD)],
                         ["MeleeScanWindow", "MeleeScanWindow",
                          "GameplayEvent Window", "MeleeScanWindow"])

    def test_the_end_is_the_trigger_plus_the_duration(self):
        first = montage.windows_of(PAYLOAD, HOLD)[0]
        self.assertAlmostEqual(first.t1, 0.9966667, places=6)

    def test_a_montage_the_payload_does_not_hold(self):
        self.assertEqual(montage.windows_of(PAYLOAD, "/Game/none"), [])

    def test_a_payload_from_an_older_build_has_no_notifies(self):
        self.assertEqual(montage.windows_of(
            {"montages": {HOLD: {"name": "x", "slots": []}}}, HOLD), [])


class Clipped(unittest.TestCase):
    def test_a_window_inside_the_slot_is_kept(self):
        windows = [montage.Window("MeleeScanWindow", 0.6, 0.9966667)]
        self.assertEqual(montage.clipped(windows, 2.4333334), windows)

    def test_a_window_crossing_the_slot_end_is_cut_back(self):
        windows = [montage.Window("MeleeScanWindow", 1.0, 1.4)]
        self.assertEqual(montage.clipped(windows, 1.2),
                         [montage.Window("MeleeScanWindow", 1.0, 1.2)])

    def test_a_window_past_the_slot_end_is_dropped(self):
        """3 of Atone's 1928 slot/notify pairs sit past the slot's end."""
        windows = [montage.Window("MeleeScanWindow", 1.3013333, 1.408)]
        self.assertEqual(montage.clipped(windows, 1.2), [])

    def test_a_slot_of_no_length_keeps_nothing(self):
        windows = [montage.Window("MeleeScanWindow", 0.0, 0.1)]
        self.assertEqual(montage.clipped(windows, 0.0), [])

    def test_nothing_in_nothing_out(self):
        self.assertEqual(montage.clipped(None, 1.0), [])


class PlanWindows(unittest.TestCase):
    def test_the_plan_of_the_long_slot_carries_all_four(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        self.assertEqual(len(plan.windows), 4)

    def test_the_short_slot_keeps_only_what_fits(self):
        """A slot can be shorter than its montage - 44 of Atone's are."""
        plan = montage.plan_for(PAYLOAD, HOLD, "Short")
        self.assertEqual([w.name for w in plan.windows],
                         ["MeleeScanWindow", "MeleeScanWindow",
                          "GameplayEvent Window"])
        self.assertAlmostEqual(plan.windows[-1].t1, 1.2, places=6)

    def test_a_plan_built_by_hand_has_no_windows(self):
        """The field's default: an older caller keeps working."""
        plan = montage.Plan(montage="AM_X", slot="1P", spans=[], end=0.0,
                            clips=[])
        self.assertEqual(plan.windows, ())


class BookmarksFor(unittest.TestCase):
    def setUp(self):
        self.plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")

    def test_the_frames_snap_outward(self):
        """0.600..0.9967 s at 30 fps is 18.0..29.9 -> 18..30: a window is
        never shown shorter than it is, and the range stays whole."""
        rows = montage.bookmarks_for(self.plan, 30.0)
        self.assertEqual(rows[0], ("MeleeScanWindow", 18.0, 30.0))

    def test_every_window_lands(self):
        self.assertEqual(len(montage.bookmarks_for(self.plan, 30.0)), 4)

    def test_a_one_frame_window_stays_one_frame(self):
        """The shortest of Atone's 90 is 0.033 s - exactly one frame."""
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 0.5, 0.5333333)])
        self.assertEqual(montage.bookmarks_for(plan, 30.0),
                         [("MeleeScanWindow", 15.0, 16.0)])

    def test_a_window_of_no_length_is_still_a_frame_wide(self):
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 1.0, 1.0)])
        self.assertEqual(montage.bookmarks_for(plan, 30.0),
                         [("MeleeScanWindow", 30.0, 31.0)])

    def test_sixty_fps(self):
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 0.6, 0.9966667)])
        self.assertEqual(montage.bookmarks_for(plan, 60.0),
                         [("MeleeScanWindow", 36.0, 60.0)])

    def test_no_windows_no_bookmarks(self):
        plan = self.plan._replace(windows=())
        self.assertEqual(montage.bookmarks_for(plan, 30.0), [])

    def test_no_fps_reads_as_thirty(self):
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 0.6, 0.9966667)])
        self.assertEqual(montage.bookmarks_for(plan, 0),
                         [("MeleeScanWindow", 18.0, 30.0)])


class PayloadRoundTrip(unittest.TestCase):
    def test_the_windows_survive_the_plan_file(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        back = montage.plan_of_payload(
            montage.plan_payload(plan, {CLIP: "C:/t/c.fbx"}, 30.0))
        self.assertEqual(list(back.windows), list(plan.windows))

    def test_a_plan_file_from_an_older_build_reads_as_no_windows(self):
        back = montage.plan_of_payload(
            {"montage": "AM_X", "slot": "1P", "end": 1.0, "spans": []})
        self.assertEqual(list(back.windows), [])


class Lines(unittest.TestCase):
    def test_the_press_line_names_the_windows(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        self.assertIn("4 scan windows", montage.plan_line(plan, 30.0))

    def test_a_slot_with_no_window_says_nothing_about_them(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")._replace(
            windows=())
        self.assertNotIn("scan window", montage.plan_line(plan, 30.0))

    def test_the_note_names_them_too(self):
        self.assertIn("2 scan windows", montage.note_of(
            {"montage": {"name": "AM_X", "slot": "1P", "windows": 2}}))

    def test_one_window_reads_as_one(self):
        self.assertIn("1 scan window", montage.note_of(
            {"montage": {"name": "AM_X", "slot": "1P", "windows": 1}}))

    def test_a_clip_that_is_no_montage_says_nothing(self):
        self.assertEqual(montage.note_of({"frames": 30}), "")


if __name__ == "__main__":
    unittest.main()

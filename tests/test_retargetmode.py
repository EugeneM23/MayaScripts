"""The two retargets and which one runs (maya_retargetmode, 2026-10-02):
ROTATIONS keeps every bone's length, STRETCH puts every bone on the clip's
joint; Auto takes the stretch for a twin, asks when it would break the
proportions."""
import os
import subprocess
import sys
import unittest

import maya_retargetmode as rm

PLUGIN = os.path.dirname(os.path.abspath(rm.__file__))


def rows_twin():
    return [("upperarm_l", 28.0, 28.0), ("lowerarm_l", 27.0, 27.0),
            ("thigh_l", 45.0, 45.0), ("calf_l", 43.0, 43.0),
            ("spine_02", 10.0, 10.0), ("neck_01", 12.0, 12.0)]


def rows_creep():
    # the Creep's arms are longer than a UE clip's, its legs the same
    return [("upperarm_l", 28.0, 34.8), ("lowerarm_l", 27.0, 36.0),
            ("thigh_l", 45.0, 45.0), ("calf_l", 43.0, 43.0),
            ("spine_02", 10.0, 10.5), ("neck_01", 12.0, 16.0)]


class Purity(unittest.TestCase):

    def test_importing_it_drags_no_maya_in(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_retargetmode; "
                "print('maya' in sys.modules or 'maya.cmds' in sys.modules)" % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN)
        self.assertEqual(out.strip(), b"False")


class Regions(unittest.TestCase):

    def test_ue_names(self):
        self.assertEqual(rm.region_of("upperarm_l"), "arms")
        self.assertEqual(rm.region_of("clavicle_r"), "arms")
        self.assertEqual(rm.region_of("hand_r"), "arms")
        self.assertEqual(rm.region_of("index_02_l"), "fingers")
        self.assertEqual(rm.region_of("thigh_l"), "legs")
        self.assertEqual(rm.region_of("ball_r"), "legs")
        self.assertEqual(rm.region_of("spine_05"), "spine")
        self.assertEqual(rm.region_of("neck_02"), "neck")
        self.assertEqual(rm.region_of("head"), "neck")

    def test_playermale_and_mixamo_names(self):
        self.assertEqual(rm.region_of("Right_ForeArm"), "arms")
        self.assertEqual(rm.region_of("LeftUpLeg"), "legs")
        self.assertEqual(rm.region_of("LeftHandIndex1"), "fingers")
        self.assertEqual(rm.region_of("Spine2"), "spine")

    def test_helpers_root_and_pelvis_are_no_length(self):
        for name in ("root", "pelvis", "ik_hand_gun", "weapon_r", "camera_root"):
            self.assertTrue(rm.excluded(name), name)
        self.assertFalse(rm.excluded("hand_r"))
        self.assertTrue(rm.excluded("Hip", extra=("Hip",)))


class Segments(unittest.TestCase):

    def test_each_bone_with_its_nearest_paired_ancestor(self):
        ours = {"root": "|root", "pelvis": "|root|pelvis",
                "spine_01": "|root|pelvis|spine_01", "spine_02": "|root|pelvis|spine_01|spine_02",
                "spine_03": "|root|pelvis|spine_01|spine_02|spine_03"}
        # a three-joint spine: spine_02 has no counterpart
        theirs = {"Hips": "|Hips", "Spine": "|Hips|Spine", "Spine1": "|Hips|Spine|Spine1"}
        pairs = {"pelvis": "Hips", "spine_01": "Spine", "spine_03": "Spine1"}
        segs = rm.segments(pairs, ours, theirs)
        self.assertEqual(segs, [("spine_01", "pelvis", "Spine", "Hips"),
                                ("spine_03", "spine_01", "Spine1", "Spine")])

    def test_a_counterpart_off_the_chain_is_not_compared(self):
        ours = {"a": "|a", "b": "|a|b"}
        theirs = {"A": "|A", "B": "|B"}       # B is not under A
        self.assertEqual(rm.segments({"a": "A", "b": "B"}, ours, theirs), [])

    def test_the_separator_matters(self):
        ours = {"a": "|a", "b": "|a|b"}
        theirs = {"A": "|foot", "B": "|foot_extra|B"}
        self.assertEqual(rm.segments({"a": "A", "b": "B"}, ours, theirs), [])

    def test_lengths_and_the_clips_own_stretch(self):
        segs = [("b", "a", "B", "A")]
        rows = rm.segment_lengths(segs, {"a": (0, 0, 0), "b": (0, 3, 4)},
                                  {"A": (0, 0, 0), "B": (6, 8, 0)})
        self.assertEqual(rows, [("b", 10.0, 5.0)])
        frames = [{"A": (0, 0, 0), "B": (0, 10, 0)}, {"A": (0, 0, 0), "B": (0, 13.7, 0)}]
        bone, spread = rm.worst_stretch(segs, frames)
        self.assertEqual(bone, "B")
        self.assertAlmostEqual(spread, 3.7)


class Measuring(unittest.TestCase):

    def test_a_twin(self):
        m = rm.measure(rows_twin(), None, "Clip", "Manny_Rig")
        self.assertTrue(m.twin)
        self.assertAlmostEqual(m.scale, 1.0)
        self.assertTrue(all(abs(p) < 1e-9 for _, p in m.regions))

    def test_the_creep_is_not_a_twin_and_says_where(self):
        m = rm.measure(rows_creep(), ("neck_01", 3.7), "Clip", "Creep_Rig")
        self.assertFalse(m.twin)
        self.assertAlmostEqual(m.scale, 1.0)          # the same legs
        regions = dict(m.regions)
        self.assertAlmostEqual(regions["arms"], 100.0 * (55.0 - 70.8) / 70.8)
        self.assertAlmostEqual(regions["legs"], 0.0)
        self.assertAlmostEqual(regions["neck"], -25.0)
        self.assertEqual(rm.regions_text(m), "arms -22 %, spine -5 %, neck -25 %")
        self.assertEqual(rm.stretch_text(m), "the clip itself stretches neck_01 3.7 cm")

    def test_the_size_is_the_legs(self):
        # a clip at ten times our size, the same proportions
        rows = [(n, 10.0 * s, t) for n, s, t in rows_twin()]
        m = rm.measure(rows)
        self.assertFalse(m.twin)
        self.assertAlmostEqual(m.scale, 0.1)
        self.assertTrue(rm.same_proportions(m))
        self.assertTrue(all(abs(p) < 1e-9 for _, p in m.regions))

    def test_a_3p_clip_stretching_a_few_bones_is_still_a_twin(self):
        rows = rows_twin() + [("spine_03", 10.5, 10.0), ("spine_04", 10.4, 10.0)]
        self.assertTrue(rm.measure(rows).twin)

    def test_short_bones_do_not_vote(self):
        rows = rows_twin() + [("index_03_l", 0.9, 0.5)] * 20
        self.assertTrue(rm.measure(rows).twin)

    def test_nothing_measured(self):
        m = rm.measure([])
        self.assertEqual(m.count, 0)
        self.assertEqual(rm.decide(rm.AUTO, m, True).mode, None)


class Deciding(unittest.TestCase):
    """The table the animator asked for: Auto decides and asks only when the
    stretch would break the proportions; the forced settings never ask."""

    def setUp(self):
        self.twin = rm.measure(rows_twin(), None, "Clip", "Manny_Rig")
        self.creep = rm.measure(rows_creep(), ("neck_01", 3.7), "Clip", "Creep_Rig")

    def test_auto_twin_is_stretch_exact_and_asks_nothing(self):
        d = rm.decide(rm.AUTO, self.twin, True)
        self.assertEqual((d.mode, d.ask), (rm.STRETCH, False))
        self.assertEqual(d.reason, "stretch - Manny_Rig is the clip's twin, exact")

    def test_auto_another_body_asks_defaulting_to_rotations(self):
        d = rm.decide(rm.AUTO, self.creep, True)
        self.assertEqual((d.mode, d.ask), (rm.ROTATION, True))
        self.assertTrue(d.reason.startswith("rotations - Creep_Rig keeps its proportions (arms -22 %"))

    def test_auto_with_no_one_to_ask_keeps_proportions_and_says_why(self):
        d = rm.decide(rm.AUTO, self.creep, False)
        self.assertEqual((d.mode, d.ask), (rm.ROTATION, False))
        self.assertIn("no one to ask here", d.reason)

    def test_auto_same_proportions_at_another_size_stretches(self):
        m = rm.measure([(n, 10.0 * s, t) for n, s, t in rows_twin()], None, "Big", "Manny_Rig")
        d = rm.decide(rm.AUTO, m, True)
        self.assertEqual((d.mode, d.ask), (rm.STRETCH, False))
        self.assertIn("x0.1", d.reason)

    def test_forced_settings_never_ask(self):
        for m in (self.twin, self.creep, None):
            self.assertEqual(rm.decide(rm.ROTATION, m, True), rm.Decision(
                rm.ROTATION, False, "rotations - the Retarget card says Rotations"))
            d = rm.decide(rm.STRETCH, m, True)
            self.assertEqual((d.mode, d.ask), (rm.STRETCH, False))
        self.assertTrue(rm.decide(rm.STRETCH, self.twin, True).reason.endswith("exact (a twin)"))

    def test_an_unknown_setting_reads_auto(self):
        self.assertEqual(rm.decide("bogus", self.twin, True).mode, rm.STRETCH)

    def test_the_answers(self):
        d = rm.decide(rm.AUTO, self.creep, True)
        self.assertEqual(rm.answered(d, rm.KEEP, self.creep).mode, rm.ROTATION)
        s = rm.answered(d, rm.SQUASH, self.creep)
        self.assertEqual(s.mode, rm.STRETCH)
        self.assertTrue(s.reason.startswith("stretch - Creep_Rig squashed & stretched"))
        self.assertIsNone(rm.answered(d, rm.CANCEL, self.creep))
        self.assertEqual(rm.answered(d, "", self.creep).mode, rm.ROTATION)

    def test_the_question_names_both_and_the_differences(self):
        text = rm.question(self.creep)
        self.assertIn("Clip onto Creep_Rig", text)
        self.assertIn("arms -22 %", text)
        self.assertIn("neck_01 3.7 cm", text)
        self.assertIn("Keep proportions", text)
        self.assertIn("Squash & stretch", text)


class Batch(unittest.TestCase):
    """«a batch import asks ONCE»: one question, the worst named, the answer
    for every clip that would ask; a twin stays exact."""

    def setUp(self):
        self.twin = rm.measure(rows_twin(), None, "A", "Creep_Rig")
        self.mild = rm.measure([(n, s, t * (1.0 if n.startswith(("thigh", "calf")) else 1.05))
                                for n, s, t in rows_twin()], None, "B", "Creep_Rig")
        self.bad = rm.measure(rows_creep(), None, "C", "Creep_Rig")

    def test_one_question_about_the_worst(self):
        decisions, ask_about, asking = rm.decide_batch(rm.AUTO, [self.twin, self.mild, self.bad], True)
        self.assertEqual([d.mode for d in decisions], [rm.STRETCH, rm.ROTATION, rm.ROTATION])
        self.assertIs(ask_about, self.bad)
        self.assertEqual(asking, 2)
        self.assertIn("all 2 animations", rm.question(ask_about, asking - 1))

    def test_the_answer_goes_for_every_asking_clip(self):
        measures = [self.twin, self.mild, self.bad]
        decisions, _, _ = rm.decide_batch(rm.AUTO, measures, True)
        out = rm.apply_answer(decisions, measures, rm.SQUASH)
        self.assertEqual([d.mode for d in out], [rm.STRETCH, rm.STRETCH, rm.STRETCH])
        self.assertTrue(out[0].reason.endswith("twin, exact"))
        self.assertIsNone(rm.apply_answer(decisions, measures, rm.CANCEL))

    def test_nothing_to_ask(self):
        _, ask_about, asking = rm.decide_batch(rm.AUTO, [self.twin], True)
        self.assertEqual((ask_about, asking), (None, 0))

    def test_choose_batch_asks_once(self):
        asked = []
        rm.set_asker(lambda text: asked.append(text) or rm.KEEP)
        try:
            out = rm.choose_batch([self.twin, self.mild, self.bad], rm.AUTO)
        finally:
            rm.set_asker(None)
        self.assertEqual(len(asked), 1)
        self.assertEqual([d.mode for d in out], [rm.STRETCH, rm.ROTATION, rm.ROTATION])

    def test_choose_raises_on_cancel(self):
        rm.set_asker(lambda text: rm.CANCEL)
        try:
            with self.assertRaises(rm.Cancelled):
                rm.choose(self.bad, rm.AUTO)
            with self.assertRaises(rm.Cancelled):
                rm.choose_batch([self.bad], rm.AUTO)
            self.assertEqual(rm.choose(self.twin, rm.AUTO).mode, rm.STRETCH)
        finally:
            rm.set_asker(None)


class Frames(unittest.TestCase):

    def test_sampled_ends_and_between(self):
        self.assertEqual(rm.sample_frames(0, 30, 4), [0.0, 10.0, 20.0, 30.0])
        self.assertEqual(rm.sample_frames(5, 5), [5])
        self.assertEqual(rm.sample_frames(None, None), [])


if __name__ == "__main__":
    unittest.main()

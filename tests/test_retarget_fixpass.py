"""The review's fixes to the two retarget versions (2026-10-02, the fix pass): Rotations on a
rig without the rotation mark keep the legacy IK on the clip's hands and feet; a stretch
take says which limbs are in IK; the PlayerMale's stretch rides one frame; the clip is
scaled about its root's first-frame floor point; a Cancel puts the scene's time back; the
decided twin verdict is the one that runs."""
import types
import unittest

import maya_asretarget as ar
import maya_pmretarget as pm
import maya_retargetmode as rm
from maya_uebridge import rigimport

CONTROLS = ar.candidates(ar.UE5)
BONES = [b for _, b in ar.ROWS] + ["root", "pelvis", "hand", "foot", "ball", "thigh", "upperarm"]
BONES = [b + s for b in BONES for s in ("", "_l", "_r")]


class KeepLengths(unittest.TestCase):
    """Rotations on Manny (no rotation mark): FK by angle, no position - a twin's neither -
    and, since 2026-10-02, the IK ends and poles on our own FK like every other version
    (the fix pass had them on the clip's hands and feet, somewhere the FK was not)."""

    def test_fk_takes_no_position_even_for_a_twin(self):
        drives, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, keep_lengths=True)
        fk = [d for d in drives if d.control.startswith("FK")]
        self.assertTrue(fk and all(d.rotate and not d.translate for d in fk))

    def test_ik_ends_follow_our_fk_as_in_every_version(self):
        keep, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, keep_lengths=True)
        rotation, _ = ar.drive_plan(CONTROLS, BONES, ar.UE5, rotation=True)
        self.assertEqual(keep, rotation)
        ik = [d for d in keep if d.control.startswith(("IK", "Pole"))]
        self.assertTrue(ik and all(d.own and d.bone.startswith("FKX") for d in ik))

    def test_a_foreign_schema_is_exactly_the_legacy_plan(self):
        mixamo = ["Hips", "Spine", "Spine1", "Spine2", "LeftArm", "LeftForeArm", "LeftHand",
                  "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"]
        self.assertEqual(ar.drive_plan(CONTROLS, mixamo, ar.MIXAMO, keep_lengths=True),
                         ar.drive_plan(CONTROLS, mixamo, ar.MIXAMO))

    def test_the_note_says_fk_and_ik_agree(self):
        text = ar.keep_note({"arm": 1.165, "leg": 0.974})
        self.assertIn("keeps its own length", text)
        self.assertIn("FK and IK agree", text)
        self.assertIn("arm is +16.5%", text)


class StretchIk(unittest.TestCase):

    def test_limbs_past_half_read_ik(self):
        self.assertEqual(ar.ik_limbs({"arm_l": 0.0, "arm_r": 0.0, "leg_l": 10.0, "leg_r": 6.0}),
                         ["leg_l", "leg_r"])
        self.assertEqual(pm.ik_limbs({"arm_l": 4.9, "leg_l": None}), [])

    def test_no_note_says_an_ik_limb_keeps_its_lengths_any_more(self):
        # 2026-10-02: the bake gives the IK limbs the FK's lengths (maya_ikmatch)
        self.assertFalse(hasattr(ar, "stretch_ik_note"))
        for module in (ar, pm, rm):
            with open(module.__file__.replace(".pyc", ".py"), encoding="utf-8") as handle:
                self.assertNotIn("keep their own lengths", handle.read())

    def test_the_question_says_the_ik_takes_the_stretch_too(self):
        m = rm.measure([("upperarm_l", 28.0, 34.8), ("thigh_l", 45.0, 45.0)], None, "Clip", "Creep_Rig")
        self.assertNotIn("keeps its own lengths", rm.question(m))
        self.assertIn("in FK and in IK alike", rm.question(m))


class PmOneFrame(unittest.TestCase):
    """The PlayerMale's stretch: the FK followers carry the pelvis's offset in pm's own scaled
    frame, the one Main and RootX_M ride."""

    def test_the_pelvis_offset_first(self):
        self.assertEqual(pm.stretch_offset({"Main": (1, 2, 3), "RootX_M": (0.1, 0.2, 0.3)}), (0.1, 0.2, 0.3))
        self.assertEqual(pm.stretch_offset({"Main": (1, 2, 3)}), (1, 2, 3))
        self.assertEqual(pm.stretch_offset({}), (0.0, 0.0, 0.0))

    def test_no_rigid_copy_of_the_clips_top_node(self):
        import inspect
        source = inspect.getsource(pm.connect)
        self.assertNotIn("scale_space", source)
        self.assertNotIn("retargetmode.scaled_follower", source)


class Pivot(unittest.TestCase):

    def test_the_floor_under_the_roots_start(self):
        self.assertEqual(rm.floor_pivot((150.0, 96.5, -80.0)), (150.0, 0.0, -80.0))

    def test_a_point_in_a_moved_space(self):
        matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 10.0, 0, -5.0, 1]
        local = rm.to_local((15.0, 0.0, -5.0), matrix)
        self.assertAlmostEqual(local[0], 5.0)
        self.assertAlmostEqual(local[2], 0.0)


class TheVerdict(unittest.TestCase):
    """A Decision carries the measure's twin verdict, so the transfer runs on it."""

    def setUp(self):
        self.twin = rm.measure([("upperarm_l", 28.0, 28.0), ("thigh_l", 45.0, 45.0)], None, "C", "Manny")
        self.creep = rm.measure([("upperarm_l", 28.0, 34.8), ("lowerarm_l", 27.0, 36.0), ("neck_01", 12.0, 16.0),
                                 ("calf_l", 43.0, 43.0)], None, "C", "Creep")

    def test_auto(self):
        self.assertIs(rm.decide(rm.AUTO, self.twin, True).twin, True)
        self.assertIs(rm.decide(rm.AUTO, self.creep, True).twin, False)
        self.assertIsNone(rm.decide(rm.AUTO, None, True).twin)

    def test_forced_stretch_and_the_answers(self):
        self.assertIs(rm.decide(rm.STRETCH, self.twin, True).twin, True)
        d = rm.decide(rm.AUTO, self.creep, True)
        self.assertIs(rm.answered(d, rm.SQUASH, self.creep).twin, False)
        self.assertIs(rm.answered(d, rm.KEEP, self.creep).twin, False)

    def test_three_fields_still_build_one(self):
        self.assertIsNone(rm.Decision(rm.ROTATION, False, "why").twin)


class FakeTime(object):
    """A cmds that holds a scene's time and records what was written, in order."""

    def __init__(self):
        self.unit, self.now = "film", 12.0
        self.ranges = {"min": 0.0, "max": 48.0, "animationStartTime": -5.0, "animationEndTime": 60.0}
        self.writes = []

    def currentUnit(self, query=False, time=None, updateAnimation=None):
        if query:
            return self.unit
        self.writes.append(("unit", time, updateAnimation))
        self.unit = time

    def currentTime(self, value=None, query=False, update=True):
        if query:
            return self.now
        self.writes.append(("time", value))
        self.now = value

    def playbackOptions(self, query=False, **kw):
        if query:
            return self.ranges[list(kw)[0]]
        self.writes.append(("ranges", dict(kw)))
        self.ranges.update(kw)


class CancelPutsTheTimeBack(unittest.TestCase):
    """An FBX import switched the scene to ntsc, rescaled its keys and put the ranges and
    the time on the clip's (measured); a Cancel takes the unit back WITH the keys, then the
    ranges and the frame."""

    def setUp(self):
        self.saved = rigimport.cmds
        self.addCleanup(lambda: setattr(rigimport, "cmds", self.saved))
        rigimport.cmds = self.fake = FakeTime()

    def test_round_trip(self):
        state = rigimport.time_state()
        self.fake.unit, self.fake.now = "ntsc", 0.0
        self.fake.ranges.update(min=0.0, max=59.0, animationStartTime=0.0, animationEndTime=59.0)
        rigimport.restore_time(state)
        self.assertEqual(self.fake.writes[0], ("unit", "film", True))
        self.assertEqual([w[0] for w in self.fake.writes], ["unit", "ranges", "time"])
        self.assertEqual((self.fake.unit, self.fake.now), ("film", 12.0))
        self.assertEqual(self.fake.ranges, {"min": 0.0, "max": 48.0, "animationStartTime": -5.0,
                                            "animationEndTime": 60.0})

    def test_the_unit_is_left_alone_when_it_did_not_change(self):
        rigimport.restore_time(rigimport.time_state())
        self.assertNotIn("unit", [w[0] for w in self.fake.writes])

    def test_a_cmds_that_cannot_say_restores_nothing(self):
        rigimport.cmds = types.SimpleNamespace()
        self.assertIsNone(rigimport.time_state())
        rigimport.restore_time(None)


if __name__ == "__main__":
    unittest.main()

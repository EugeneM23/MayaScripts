"""maya_skeletonmap: a source's SIZE read without its pose, and a static root (2026-10-02 fix pass).

The review of the conventions build found the size ratio read off the pelvis height
in whichever rest `choose_rest` picked - the first frame of a clip whose bind lives
in its rotate channels, which may be a crouch - and a floor-standing root accepted
even when it never moves (MotionBuilder's Reference, Character Creator's BoneRoot)
while the hips carry the travel."""

import math
import os
import sys
import unittest

import maya_skeletonmap as sm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skeleton_conventions as fixtures  # noqa: E402


def ours_of(convention, scale=1.0):
    """{our bone: world position} of a fixture, its rest."""
    rows, expected = fixtures.build(convention)
    at = dict((n, pos) for n, _p, pos in rows)
    return dict((o, tuple(c * scale for c in at[s])) for o, s in expected.items())


def crouched(positions, drop=30.0):
    """The same body crouched: the pelvis and everything above it `drop` lower,
    the knees pushed forward so thigh and calf keep their lengths."""
    out = dict(positions)
    for side in ("l", "r"):
        hip, ankle = out["thigh_" + side], out["foot_" + side]
        thigh = math.dist(hip, out["calf_" + side])
        calf = math.dist(out["calf_" + side], ankle)
        new_hip = (hip[0], hip[1] - drop, hip[2])
        span = math.dist(new_hip, ankle)
        # the knee on the circle both lengths allow, pushed forward (+Z)
        a = (thigh ** 2 - calf ** 2 + span ** 2) / (2 * span)
        h = math.sqrt(max(0.0, thigh ** 2 - a ** 2))
        d = tuple((q - p) / span for p, q in zip(new_hip, ankle))
        base = tuple(p + a * u for p, u in zip(new_hip, d))
        dz = d[2]
        perp = (-dz * d[0], -dz * d[1], 1.0 - dz * d[2])          # +Z off the hip-ankle line
        length = math.sqrt(sum(c * c for c in perp))
        out["calf_" + side] = tuple(b + h * c / length for b, c in zip(base, perp))
        out["thigh_" + side] = new_hip
    for bone, pos in positions.items():
        if bone.startswith(("pelvis", "spine", "neck", "head", "clavicle", "upperarm",
                            "lowerarm", "hand")) or "_0" in bone or "metacarpal" in bone:
            out[bone] = (pos[0], pos[1] - drop, pos[2])
    return out


class TestLegLength(unittest.TestCase):

    def test_the_fixture_body(self):
        body = ours_of("ue5")
        hip, knee, ankle = fixtures.HIP, fixtures.KNEE, fixtures.ANKLE
        expected = math.dist(hip, knee) + math.dist(knee, ankle)
        self.assertAlmostEqual(sm.leg_length(body), expected, places=6)

    def test_pose_free(self):
        body = ours_of("mixamo")
        self.assertAlmostEqual(sm.leg_length(crouched(body)), sm.leg_length(body), places=6)

    def test_none_without_legs(self):
        self.assertIsNone(sm.leg_length({"pelvis": (0, 1, 0)}))


class TestStandingHeight(unittest.TestCase):

    def test_upright_rest(self):
        body = ours_of("mixamo")
        self.assertAlmostEqual(sm.standing_height(body), fixtures.HIPS[1] - fixtures.ANKLE[1],
                               places=1)

    def test_a_crouch_is_no_standing_pose(self):
        self.assertIsNone(sm.standing_height(crouched(ours_of("mixamo"))))

    def test_a_straight_line_is_no_standing_pose(self):
        # a UE-style source zeroed: every bone along one axis, the legs along +X
        body = ours_of("mixamo")
        line = dict((k, (v[1], 0.0, 0.0)) for k, v in body.items())
        for side in ("l", "r"):
            for bone in ("thigh_", "calf_", "foot_"):
                p = body[bone + side]
                line[bone + side] = (body["pelvis"][1], 0.0, p[1] - body["pelvis"][1])
        self.assertIsNone(sm.standing_height(line))

    def test_lying_down_still_stands_in_its_own_frame(self):
        body = ours_of("mixamo")
        prone = dict((k, (v[0], v[2], -v[1])) for k, v in body.items())   # turned 90 about X
        self.assertAlmostEqual(sm.standing_height(prone), sm.standing_height(body), places=6)


class TestSizeRatio(unittest.TestCase):

    def test_metres_against_centimetres(self):
        ratio, how = sm.size_ratio(ours_of("ue5"), {"jointOrient": ours_of("ue5", 0.01)})
        self.assertAlmostEqual(ratio, 100.0, places=6)
        self.assertEqual(how, "standing (jointOrient)")

    def test_a_crouched_first_frame_does_not_change_the_size(self):
        """The bug the review found: a crouched frame 0 read the pelvis 30 cm low."""
        ours, theirs = ours_of("ue5"), ours_of("mixamo", 0.01)
        straight, _how = sm.size_ratio(ours, {"firstFrame": theirs})
        ratio, how = sm.size_ratio(ours, {"firstFrame": crouched(theirs, drop=0.3)})
        self.assertTrue(how.startswith("legs"), how)
        legs = sm.leg_length(ours) / sm.leg_length(theirs)
        self.assertAlmostEqual(ratio, legs, places=6)
        self.assertLess(abs(ratio / straight - 1.0), 0.05)

    def test_a_true_rest_wins_over_a_crouched_frame(self):
        ours, theirs = ours_of("ue5"), ours_of("mixamo")
        ratio, how = sm.size_ratio(ours, {"firstFrame": crouched(theirs),
                                          "jointOrient": theirs})
        self.assertEqual(how, "standing (jointOrient)")
        self.assertAlmostEqual(ratio, sm.standing_height(ours) / sm.standing_height(theirs))

    def test_unusable(self):
        self.assertEqual(sm.size_ratio({}, {"jointOrient": {}}), (1.0, ""))


class TestStaticRoot(unittest.TestCase):

    IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def test_a_still_reference_with_travelling_hips(self):
        roots = [list(self.IDENTITY)] * 5
        hips = [(0.0, 95.0, 20.0 * i) for i in range(5)]
        self.assertTrue(sm.static_root(roots, hips, 85.0))

    def test_a_travelling_root(self):
        roots = []
        for i in range(5):
            m = list(self.IDENTITY)
            m[14] = 20.0 * i
            roots.append(m)
        hips = [(0.0, 95.0, 20.0 * i) for i in range(5)]
        self.assertFalse(sm.static_root(roots, hips, 85.0))

    def test_an_in_place_clip_keeps_its_root(self):
        roots = [list(self.IDENTITY)] * 5
        hips = [(0.5 * i, 95.0, 0.0) for i in range(5)]     # a sway, no travel
        self.assertFalse(sm.static_root(roots, hips, 85.0))

    def test_a_turning_root_is_not_static(self):
        roots = []
        for i in range(5):
            a = math.radians(10 * i)
            roots.append([math.cos(a), 0, -math.sin(a), 0, 0, 1, 0, 0,
                          math.sin(a), 0, math.cos(a), 0, 0, 0, 0, 1])
        hips = [(0.0, 95.0, 20.0 * i) for i in range(5)]
        self.assertFalse(sm.static_root(roots, hips, 85.0))

    def test_drop_static_root(self):
        mapping = {"root": "|Reference", "pelvis": "|Reference|Hips"}
        tracks = {"|Reference": [list(self.IDENTITY)] * 3,
                  "|Reference|Hips": [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 95, 30.0 * i, 1]
                                      for i in range(3)]}
        notes = []
        out = sm.drop_static_root(mapping, lambda path, frame: tracks[path][frame], [0, 1, 2],
                                  85.0, notes)
        self.assertNotIn("root", out)
        self.assertEqual(out["pelvis"], "|Reference|Hips")
        self.assertIn("never moves", notes[0])
        self.assertIn("root", mapping)                      # the input is left alone

    def test_sample_frames(self):
        self.assertEqual(sm.sample_frames(0, 4), [0, 1, 2, 3, 4])
        frames = sm.sample_frames(0, 1000, most=11)
        self.assertEqual(len(frames), 11)
        self.assertEqual((frames[0], frames[-1]), (0, 1000))
        self.assertEqual(sm.sample_frames(None, None), [])


class TestPivot(unittest.TestCase):

    def test_scale_pivot_on_the_floor_under_the_first_frame(self):
        self.assertEqual(sm.scale_pivot((20.0, 95.0, -4.0), (0.0, 3.0, 0.0)), (20.0, 3.0, -4.0))

    def test_a_scaled_track_keeps_its_first_point(self):
        track = [(20.0, 95.0, 0.0), (25.0, 95.0, 10.0)]
        out = sm.scaled_track(track, 2.0)
        self.assertEqual(out[0], track[0])
        self.assertEqual(out[1], (30.0, 95.0, 20.0))


if __name__ == "__main__":
    unittest.main()

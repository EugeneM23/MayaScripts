"""Gait Builder's operators (gaitmodel's aspect knobs) on the synthetic walker: each one adds its unit to what
aspects.measure reads off the result, and at 0 changes nothing. numpy only."""

import unittest

import numpy as np

from tests import test_walkmodel as tw
from tests.test_gait_model import load, apart

gm = load("gaitmodel")
asp = load("aspects")


def walk():
    c = tw.clip()
    return gm.analyse(gm.Clip(c.names, c.parents, c.worlds.copy(), c.fps, c.up, c.name))


# the physics off, so the read-back is the operator's alone (Balance, the springs and Foot placement on top are
# the gates' business, on real walks)
QUIET = {"balance": 0.0, "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0, "foot_placement": 0.0}

# a joint's own axes turned, its world places and motion kept: v . R becomes v . (Q . R) - the frame a UE
# skeleton's spine joints stand in (asd's spine_05: its X along the world's Y, its Y along -Z)
SPINE_AXES = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, -1.0], [-1.0, 0.0, 0.0]])


def turned_spine_walk():
    c = tw.clip()
    worlds = c.worlds.copy()
    for j, name in enumerate(c.names):
        if name.startswith("spine_"):
            worlds[j, :, :3, :3] = SPINE_AXES[None] @ worlds[j, :, :3, :3]
    return gm.analyse(gm.Clip(c.names, c.parents, worlds, c.fps, c.up, c.name))


class OperatorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = walk()
        cls.base_result = cls.w.evaluate(QUIET)
        cls.base = asp.measure(cls.w, cls.base_result.worlds)

    def read(self, **given):
        g = dict(QUIET)
        g.update(given)
        return asp.measure(self.w, self.w.evaluate(g).worlds)

    def moved(self, key, side=None, **given):
        m = self.read(**given)
        if side:
            return m[key][side] - self.base[key][side]
        return m[key] - self.base[key]

    def test_zero_changes_nothing(self):
        zero = dict((name, 0.0) for name in gm.ASPECT_KNOBS)
        zero.update({"toe_add": 0.0, "knee_bend": 0.0})
        zero.update(QUIET)
        cm, deg = apart(self.base_result.worlds, self.w.evaluate(zero).worlds)
        self.assertLess(cm, 1e-9)

    def test_pelvis_swings_add_in_phase(self):
        # the bob raised where the legs have room (the walker's legs are near straight at mid-stance: a higher
        # top is cut by their reach - the pelvis's drop, as it should be)
        low = self.read(pelvis_height=-8.0)["bob"]
        self.assertAlmostEqual(self.read(pelvis_height=-8.0, bob_add=2.0)["bob"] - low, 2.0, delta=0.15)
        self.assertAlmostEqual(self.moved("sway", sway_add=3.0), 3.0, delta=0.2)
        self.assertAlmostEqual(self.moved("surge", surge_add=1.5), 1.5, delta=0.15)
        self.assertAlmostEqual(self.moved("bob", bob_add=-1.0), -1.0, delta=0.15)

    def test_lean(self):
        self.assertAlmostEqual(self.moved("lean", lean_add=10.0), 10.0, delta=1.0)
        self.assertAlmostEqual(self.moved("lean", lean_add=-6.0), -6.0, delta=0.8)

    def test_arm_swing_forward_and_out(self):
        for s in "lr":
            self.assertAlmostEqual(self.moved("arm_swing", s, arm_swing_add=10.0), 10.0, delta=1.5)
            self.assertAlmostEqual(self.moved("arms_forward", s, arm_fwd_add=15.0), 15.0, delta=1.5)
            self.assertAlmostEqual(self.moved("arm_out", s, arm_out_add=12.0), 12.0, delta=1.5)

    def test_elbow(self):
        for s in "lr":
            self.assertAlmostEqual(self.moved("elbow", s, elbow_add=20.0), 20.0, delta=1.5)
            # about a bent elbow: the bend is unsigned, a swing through straight would fold back
            self.assertAlmostEqual(self.moved("elbow_swing", s, elbow_add=20.0, elbow_swing_add=8.0), 8.0, delta=1.5)

    def test_one_side_alone(self):
        m = self.read(elbow_add_l=25.0)
        self.assertAlmostEqual(m["elbow"]["l"] - self.base["elbow"]["l"], 25.0, delta=1.5)
        self.assertAlmostEqual(m["elbow"]["r"] - self.base["elbow"]["r"], 0.0, delta=1e-6)

    def test_toe_out(self):
        for s in "lr":
            self.assertAlmostEqual(self.moved("toe_out", s, toe_add=12.0), 12.0, delta=1.0)

    def test_knee_bend_holds_the_planted_knee_bent(self):
        m = self.read(knee_bend=30.0)
        for s in "lr":
            self.assertGreaterEqual(m["knee_bend"][s], 30.0 - 0.5)

    def test_chest_bounce(self):
        self.assertAlmostEqual(self.moved("chest_bounce", chest_bounce_add=4.0), 4.0, delta=0.8)

    def test_arm_out_on_an_arm_held_forward(self):
        # a run holds the upper arm forward: turned about the body's front it only spun about itself (HavyRun read
        # 4.2 of 10 deg); about the axis across the arm and its side it goes out as asked
        ahead = self.read(arm_fwd_add=70.0)
        out = self.read(arm_fwd_add=70.0, arm_out_add=10.0)
        for s in "lr":
            self.assertAlmostEqual(out["arm_out"][s] - ahead["arm_out"][s], 10.0, delta=1.5, msg=s)

    def test_lift_is_solved_on_the_walk_s_own_swing(self):
        # Foot lift's engine knob scales the swing's height over the line from where the foot leaves the ground to
        # where it lands; aspects.lift_scale solves it on that profile for the asked height over the ground
        m = self.base
        for s in "lr":
            for change in (4.0, -3.0):
                L = asp.lift_scale(self.w.lift_profile(s), change)
                got = self.read(**{"lift_" + s: L})
                self.assertAlmostEqual(got["lift"][s] - m["lift"][s], change, delta=0.3, msg=(s, change))

    def test_knee_bend_holds_only_the_planted_leg(self):
        # the swinging leg keeps its own reach: capped too, a run's leg reaching for the ground was drawn in and
        # held the pelvis down - Knee bend overshot 3x (HavyRun)
        own = min(self.base["knee_bend"].values())          # the walker's knees: 46 deg at their straightest
        m = asp.measure(self.w, self.w.evaluate(dict(QUIET, knee_bend=own + 10.0)).worlds)
        for s in "lr":
            self.assertGreater(m["knee_bend"][s], own + 10.0 - 1.0, msg=s)
            self.assertLess(m["knee_bend"][s], own + 10.0 + 4.0, msg=s)

    def test_chest_bounce_on_spine_axes_far_from_the_world(self):
        # a UE spine joint's axes stand ~90 deg off the world's: the bounce is a WORLD pitch, read and added the
        # same whatever the joints' own axes (it read 0.13 of 5 deg on asd while both were taken in them)
        w = turned_spine_walk()
        base = w.evaluate(QUIET)
        m0 = asp.measure(w, base.worlds)
        self.assertAlmostEqual(m0["chest_bounce"], self.base["chest_bounce"], delta=0.05)
        m = asp.measure(w, w.evaluate(dict(QUIET, chest_bounce_add=4.0)).worlds)
        self.assertAlmostEqual(m["chest_bounce"] - m0["chest_bounce"], 4.0, delta=0.8)

    def test_arm_timing_shifts_the_swing(self):
        # the swing's amplitude stays, its phase moves: the arm's forward angle at frame f is the old at f - 3
        base = self.base_result.worlds
        later = self.w.evaluate(dict(QUIET, arm_lag_add=3.0)).worlds
        i = self.w.index["hand_l"]
        n = base.shape[1] - 1
        y0 = base[i, :n, 3, :3] - base[self.w.index["upperarm_l"], :n, 3, :3]
        y1 = later[i, :n, 3, :3] - later[self.w.index["upperarm_l"], :n, 3, :3]
        self.assertLess(float(np.abs(np.roll(y0, 3, axis=0) - y1).max()), 0.5)


if __name__ == "__main__":
    unittest.main()

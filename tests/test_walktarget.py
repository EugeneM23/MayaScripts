"""The saved walk (walkfile.py) and a walk carried onto another skeleton (walktarget.py), on the synthetic
walker of test_walkmodel: onto itself, onto a copy at 0.7 of its size. mayapy (posemath needs OpenMaya)."""

import json
import math
import os
import shutil
import tempfile
import unittest

import numpy as np

from tests.test_walkmodel import BONES, FOLDER, clip, load, walk, wm

wf = load("walkfile")
wt = load("walktarget")


def statics_of(c, frame=0, scale=1.0):
    """The synthetic skeleton as a card's bones: parent, canonical (its UE leaf), rest (a frame, scaled)."""
    out = {}
    for j, name in enumerate(c.names):
        p = c.parents[j]
        rest = np.array(c.worlds[j, frame])
        rest[3, :3] *= scale
        out[name] = {"parent": c.names[p] if p >= 0 else None, "canonical": name,
                     "rest": [float(v) for v in rest.reshape(16)]}
    return out


def target_of(c, frame=0, scale=1.0, shift=(0.0, 0.0, 0.0)):
    """A target skeleton: the synthetic one scaled, standing `shift` away, as scene.skeleton reads it."""
    bones = statics_of(c, frame, scale)
    for name, bone in bones.items():
        world = np.array(bone["rest"]).reshape(4, 4)
        world[3, :3] += shift
        bone["world"] = [float(v) for v in world.reshape(16)]
        bone["path"] = "|" + name
    return bones


def worlds(frames, leaf):
    return np.array([np.array(list(f[leaf])).reshape(4, 4) for f in frames])


class WalkFileTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="walkfile_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_round_trip(self):
        c = clip()
        statics = statics_of(c)
        path = wf.path_for(self.folder, "My walk: 01")
        self.assertTrue(path.endswith("My_walk_01" + wf.SUFFIX))
        wf.save(path, c, statics, start=5)
        data = wf.load(path)
        self.assertEqual(data["names"], c.names)
        self.assertEqual(data["parents"], c.parents)
        self.assertTrue(np.allclose(data["worlds"], c.worlds))
        self.assertEqual((data["fps"], data["name"], data["start"]), (30.0, "synthetic", 5))
        self.assertEqual(data["statics"]["thigh_l"]["parent"], "pelvis")
        self.assertEqual(wf.names_in(self.folder), ["My_walk_01"])
        back = wf.clip_of(data, wm)
        self.assertTrue(np.allclose(back.worlds, c.worlds))

    def test_refuses_another_format(self):
        path = os.path.join(self.folder, "x" + wf.SUFFIX)
        import gzip
        with gzip.open(path, "wt") as handle:
            json.dump({"format": "something else"}, handle)
        with self.assertRaises(wf.Refusal):
            wf.load(path)

    def test_mannys_rest_only_for_mannys_bones(self):
        c = clip()
        template = {}
        for name, bone in statics_of(c, frame=3).items():
            template[name] = {"parent": bone["parent"], "world_matrix": bone["rest"]}
        positions = dict((n, tuple(c.worlds[j, 0, 3, :3])) for j, n in enumerate(c.names))
        rests = wf.template_rests(positions, dict((n, b["parent"]) for n, b in statics_of(c).items()), template)
        self.assertIsNotNone(rests)
        self.assertEqual(rests["thigh_l"], template["thigh_l"]["world_matrix"])
        small = dict((n, tuple(0.7 * np.array(p))) for n, p in positions.items())
        self.assertIsNone(wf.template_rests(small, dict((n, b["parent"]) for n, b in statics_of(c).items()),
                                            template))


class RetargetTests(unittest.TestCase):

    def test_onto_itself_is_the_walk(self):
        w, c = walk(), clip()
        statics = statics_of(c)
        target = target_of(c)
        rt = wt.Retarget(w, statics, target)
        result = w.evaluate(w.own_knobs())      # the walk itself (the defaults turn the pelvis as people do)
        frames, info = rt.frames(result)
        self.assertEqual(len(frames), 25)
        self.assertEqual(info["scale"], 1.0)
        for leaf in rt.written():
            j = w.index[leaf]
            self.assertLess(float(np.abs(worlds(frames, leaf) - c.worlds[j]).max()), 1e-6, leaf)
        self.assertEqual(max(info["drop"]), 0.0)

    def test_onto_a_smaller_body_the_steps_shrink_and_the_feet_stay(self):
        w, c = walk(), clip()
        rt = wt.Retarget(w, statics_of(c), target_of(c, scale=0.7, shift=(50.0, 0.0, -20.0)))
        frames, info = rt.frames(w.evaluate({"foot_placement": 0.0}))     # the walk's own feet: no reach drop
        self.assertAlmostEqual(info["scale"], 0.7, places=9)
        root = worlds(frames, "root")
        self.assertTrue(np.allclose(root[-1, 3, :3] - root[0, 3, :3], [0.0, 0.0, 0.7 * 120.0], atol=1e-6))
        self.assertTrue(np.allclose(root[0, 3, :3], [50.0 + 0.7 * c.worlds[0, 0, 3, 0], 0.0,
                                                      -20.0 + 0.7 * c.worlds[0, 0, 3, 2]], atol=1e-6))
        foot = worlds(frames, "foot_l")[:, 3, :3]
        stance = [w.feet["l"].on + i for i in range(w.feet["l"].length + 1)]
        self.assertLess(float(np.ptp(foot[stance], axis=0).max()), 1e-6)
        for side in "lr":
            hip, knee, ankle = (worlds(frames, b + "_" + side)[:, 3, :3] for b in ("thigh", "calf", "foot"))
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - 0.7 * 48.0).max()), 1e-6)
            self.assertLess(float(np.abs(np.linalg.norm(ankle - knee, axis=1) - 0.7 * 47.0).max()), 1e-6)
        pelvis = worlds(frames, "pelvis")[:24, 3, 1]
        self.assertTrue(np.allclose(pelvis, 0.7 * c.worlds[1, :24, 3, 1], atol=1e-6))

    def test_knobs_reach_the_target(self):
        w, c = walk(), clip()
        rt = wt.Retarget(w, statics_of(c), target_of(c, scale=0.7))
        frames, info = rt.frames(w.evaluate({"stride": 1.3}))
        root = worlds(frames, "root")
        self.assertAlmostEqual(float(root[-1, 3, 2] - root[0, 3, 2]), 0.7 * 1.3 * 120.0, places=6)

    def test_helpers_follow_their_bones_and_the_written_bones(self):
        w, c = walk(), clip()
        rt = wt.Retarget(w, statics_of(c), target_of(c, scale=0.7))
        frames, info = rt.frames(w.evaluate({"stride": 1.2}))
        self.assertLess(float(np.abs(worlds(frames, "ik_foot_l") - worlds(frames, "foot_l")).max()), 1e-6)
        cam = worlds(frames, "camera_root")[:, 3, :3] - worlds(frames, "root")[:, 3, :3]
        self.assertTrue(np.allclose(cam, [0.0, 0.7 * 160.0, 0.0], atol=1e-6))
        written = set(rt.written())
        self.assertTrue({"root", "pelvis", "thigh_l", "calf_r", "foot_l", "spine_02", "hand_r", "ik_foot_l",
                         "camera_root"} <= written)
        self.assertEqual(set(rt.translated()), {"root", "pelvis", "ik_foot_root", "ik_foot_l", "ik_foot_r",
                                                "camera_root"})

    def test_shorter_legs_than_the_walk_drop_the_pelvis(self):
        """A body as tall as the walk's (its pelvis as high) on legs 20 % shorter cannot reach the walk's
        footprints standing as high: the pelvis drops, and only where it must."""
        w, c = walk(), clip()
        target = target_of(c)
        for side in "lr":
            at = lambda leaf: np.array(target[leaf]["rest"][12:15])
            hip, knee, ankle, ball = (at(b + "_" + side) for b in ("thigh", "calf", "foot", "ball"))
            knee2 = hip + 0.8 * (knee - hip)
            ankle2 = knee2 + 0.8 * (ankle - knee)
            for leaf, point in (("calf", knee2), ("foot", ankle2), ("ball", ankle2 + (ball - ankle))):
                for key in ("rest", "world"):
                    target[leaf + "_" + side][key][12:15] = [float(v) for v in point]
        self.assertAlmostEqual(wt.Retarget(w, statics_of(c), target).scale, 0.8, places=9)  # the legs' size
        rt = wt.Retarget(w, statics_of(c), target, scale=1.0)       # carried at the walk's own size
        frames, info = rt.frames(w.evaluate())
        self.assertEqual(info["scale"], 1.0)
        self.assertGreater(max(info["drop"]), 5.0)
        self.assertLess(min(info["drop"]), max(info["drop"]))
        self.assertLess(info["short"], 1e-6)
        for side in "lr":
            hip, knee, ankle = (worlds(frames, b + "_" + side)[:, 3, :3] for b in ("thigh", "calf", "foot"))
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - 0.8 * 48.0).max()), 1e-6)
            d = np.linalg.norm(ankle - hip, axis=1)
            self.assertLessEqual(float(d.max()), w.reach[side] * 0.8 * 95.0 + 1e-6)
            foot = ankle
            stance = [w.feet[side].on + i for i in range(w.feet[side].length + 1)]
            stance = [f for f in stance if f <= 24]
            self.assertLess(float(np.ptp(foot[stance], axis=0).max()), 1e-6)

    def test_the_knee_pop_fix_takes_the_clicks_away_and_keeps_the_feet(self):
        """2026-10-27 («инструмент который будет чинить щелчки в колене», the gait guide's «никогда не
        выпрямляют ногу до конца, а на кадрах, где она почти прямая, опускают корень»): legs 20 % shorter go
        straight at the reach and click; with the fix the clicks are gone, the planted feet stay planted, the
        bones keep their lengths and the pelvis only goes down."""
        w, c = walk(), clip()
        target = target_of(c)
        for side in "lr":
            at = lambda leaf: np.array(target[leaf]["rest"][12:15])
            hip, knee, ankle, ball = (at(b + "_" + side) for b in ("thigh", "calf", "foot", "ball"))
            knee2 = hip + 0.8 * (knee - hip)
            ankle2 = knee2 + 0.8 * (ankle - knee)
            for leaf, point in (("calf", knee2), ("foot", ankle2), ("ball", ankle2 + (ball - ankle))):
                for key in ("rest", "world"):
                    target[leaf + "_" + side][key][12:15] = [float(v) for v in point]
        w.reach = dict((s, 1.0) for s in w.reach)          # legs that may go fully straight: they click
        result = w.evaluate({"pelvis_height": 6.0})
        rough, info0 = wt.Retarget(w, statics_of(c), target, scale=1.0).frames(result, knee_pops=False)
        rt = wt.Retarget(w, statics_of(c), target, scale=1.0)
        fixed, info = rt.frames(result, knee_pops=True)
        before = wt.pops(rt.bends(rough))
        after = wt.pops(rt.bends(fixed))
        self.assertTrue(any(before.values()), "the fixture clicks")
        self.assertFalse(any(after.values()), after)
        self.assertEqual(info["pops"]["fixed"], sum(len(v) for v in before.values()))
        self.assertGreaterEqual(min(np.array(info["drop"]) - np.array(info0["drop"])), -1e-9)
        self.assertIn("knee pops smoothed", wt.pops_line(info["pops"]))
        for side in "lr":
            hip, knee, ankle = (worlds(fixed, b + "_" + side)[:, 3, :3] for b in ("thigh", "calf", "foot"))
            self.assertLess(float(np.abs(np.linalg.norm(knee - hip, axis=1) - 0.8 * 48.0).max()), 1e-6)
            stance = [w.feet[side].on + i for i in range(w.feet[side].length + 1)]
            stance = [f for f in stance if f <= 24]
            self.assertLess(float(np.ptp(ankle[stance], axis=0).max()), 1e-6)

    def test_a_click_is_a_sharp_minimum_near_straight(self):
        smooth = np.radians(20.0 + 15.0 * np.cos(np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)))
        self.assertEqual(wt.pops({"l": smooth})["l"], [])
        sharp = np.array(smooth)
        sharp[12] = np.radians(1.0)                # a V into straight
        self.assertEqual(wt.pops({"l": sharp})["l"], [12])

    def test_a_target_without_legs_is_refused(self):
        w, c = walk(), clip()
        target = target_of(c)
        target = dict((n, b) for n, b in target.items() if not n.startswith(("calf_", "foot_", "ball_")))
        with self.assertRaises(wt.Refusal):
            wt.Retarget(w, statics_of(c), target)


wp = load("walkpose")


class PoseTests(unittest.TestCase):

    def pose_of(self, c, frame):
        """The synthetic walker standing as it does at `frame`, as a saved pose's bones."""
        bones = statics_of(c)
        for j, name in enumerate(c.names):
            bones[name]["world"] = [float(v) for v in c.worlds[j, frame].reshape(16)]
        return bones

    def test_pose_file_round_trip(self):
        folder = tempfile.mkdtemp(prefix="walkpose_")
        try:
            c = clip()
            path = wf.pose_path_for(folder, "goblin hunch")
            wf.save_pose(path, "goblin hunch", self.pose_of(c, 5))
            name, bones = wf.load_pose(path)
            self.assertEqual(name, "goblin hunch")
            self.assertEqual(bones["spine_01"]["world"], self.pose_of(c, 5)["spine_01"]["world"])
            self.assertEqual(wf.pose_names_in(folder), ["goblin_hunch"])
            self.assertEqual(wf.names_in(folder), [])
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_frame_of_the_walk_comes_back_as_the_pose(self):
        """The walker's own frame 5 as a pose onto its own skeleton (a twin): the spine's locals, the head
        and the pelvis exactly frame 5's, the height its pelvis's, the knees turned to frame 5's heading."""
        w, c = walk(), clip()
        pose = wp.prepare(w, statics_of(c), self.pose_of(c, 5), wm, wt)
        self.assertEqual(pose["scale"], 1.0)
        for j, local in pose["spine"].items():
            p = w.parents[j]
            want = c.worlds[j, 5, :3, :3] @ c.worlds[p, 5, :3, :3].T
            self.assertLess(float(np.abs(local - want).max()), 1e-9, w.names[j])
        self.assertEqual(sorted(w.names[j] for j in pose["spine"]), ["neck_01", "spine_01", "spine_02"])
        self.assertLess(float(np.abs(pose["head"] - c.worlds[w.index["head"], 5, :3, :3]).max()), 1e-9)
        self.assertLess(float(np.abs(pose["pelvis"] - c.worlds[w.index["pelvis"], 5, :3, :3]).max()), 1e-9)
        self.assertAlmostEqual(pose["height"], float(c.worlds[w.index["pelvis"], 5, 3, 1]), places=6)
        means = wp.mean_knee_headings(w)
        for side in "lr":
            hip, knee, ankle = (c.worlds[w.index["%s_%s" % (b, side)], 5, 3, :3] for b in ("thigh", "calf", "foot"))
            want = math.atan2(*reversed([float(np.dot(wp._bend(hip, knee, ankle), v)) for v in (w.fwd, w.side)]))
            self.assertAlmostEqual(pose["knee_turn"][side], want - means[side], places=9)

    def test_the_arms_and_the_feet_of_a_frame(self):
        w, c = walk(), clip()
        pose = wp.prepare(w, statics_of(c), self.pose_of(c, 5), wm, wt)
        for name in ("clavicle_l", "upperarm_l", "lowerarm_r", "hand_r", "index_01_l"):
            j = w.index[name]
            want = c.worlds[j, 5, :3, :3] @ c.worlds[w.parents[j], 5, :3, :3].T
            self.assertLess(float(np.abs(pose["arms"][j] - want).max()), 1e-9, name)
        gap = float(np.dot(c.worlds[w.index["foot_l"], 5, 3, :3] - c.worlds[w.index["foot_r"], 5, 3, :3], w.across))
        self.assertAlmostEqual(pose["width"], gap - (w.body_print("l") - w.body_print("r")), places=6)
        self.assertAlmostEqual(pose["toe"]["l"], 0.0, places=9)     # the walker's feet never turn
        self.assertEqual(pose["weapons"], {})
        only = wp.filtered(pose, ("torso", "feet"))
        self.assertEqual(sorted(only), ["gait_lean", "head", "hips_yaw", "lean_room", "scale", "spine", "toe", "width"])
        self.assertEqual(sorted(wp.filtered(pose, ())), ["gait_lean", "hips_yaw", "lean_room", "scale"])

    def test_the_gait_s_lean_against_its_rest(self):
        """Each torso bone's forward pitch (about the walk's side axis) of the walk's mean over the skeleton's rest
        - what a pose's torso would take away and Gait lean gives back - and the room the pose leaves to
        horizontal: the rest itself as the pose leaves all of it (1)."""
        w, c = walk(), clip()
        pose = wp.prepare(w, statics_of(c), self.pose_of(c, 0), wm, wt)        # the rest (frame 0) as the pose
        self.assertAlmostEqual(pose["lean_room"], 1.0, places=9)
        for name in ("pelvis", "spine_01", "spine_02", "neck_01", "head"):
            j = w.index[name]
            want = float(np.dot(wm.log_rot(c.worlds[j, 0, :3, :3].T @ w.wmean[j]), w.side))
            self.assertAlmostEqual(pose["gait_lean"][j], want, places=9, msg=name)
        self.assertNotIn(w.index["thigh_l"], pose["gait_lean"])
        bent = self.pose_of(c, 0)
        turn = np.eye(4)
        turn[:3, :3] = wm.exp_rot(w.side * math.radians(45.0))      # the pose 45 deg further forward from the hips
        hips = np.array(bent["pelvis"]["world"]).reshape(4, 4)
        for name in ("pelvis", "spine_01", "spine_02", "neck_01", "head"):
            m = np.array(bent[name]["world"]).reshape(4, 4)
            m[3, :3] -= hips[3, :3]
            m = m @ turn
            m[3, :3] += hips[3, :3]
            bent[name]["world"] = [float(v) for v in m.reshape(16)]
        leaned = wp.prepare(w, statics_of(c), bent, wm, wt)
        line = lambda worlds: worlds[w.index["neck_01"], 0, 3, :3] - worlds[w.index["pelvis"], 0, 3, :3]
        rest_lean = math.degrees(math.atan2(float(np.dot(line(c.worlds), w.fwd)), float(np.dot(line(c.worlds), w.up))))
        self.assertAlmostEqual(leaned["lean_room"], (90.0 - rest_lean - 45.0) / (90.0 - rest_lean), places=4)
        self.assertEqual(sorted(k for k in wp.filtered(pose, ()) if k != "scale"), ["gait_lean", "hips_yaw", "lean_room"])

    def test_the_hips_turn_of_a_pose_standing_side_on(self):
        """The pose's hip line against the walk's mean one, about up (+ toward the walk's side axis): Leg match
        gives it back from the pelvis. A frame of the walk turns by its own hip line's sway; the same frame
        with the body turned 30 deg about up on its root reads 30 deg more."""
        w, c = walk(), clip()
        heading = lambda d: math.atan2(float(np.dot(d, w.side)), float(np.dot(d, w.fwd)))
        line = lambda worlds, f: worlds[w.index["thigh_l"], f, 3, :3] - worlds[w.index["thigh_r"], f, 3, :3]
        mean = (w.pos[w.index["thigh_l"]] - w.pos[w.index["thigh_r"]]).mean(axis=0)
        pose = wp.prepare(w, statics_of(c), self.pose_of(c, 5), wm, wt)
        self.assertAlmostEqual(pose["hips_yaw"], heading(line(c.worlds, 5)) - heading(mean), places=9)
        turned = self.pose_of(c, 5)
        turn = np.eye(4)
        turn[:3, :3] = wm.exp_rot(w.up * math.radians(30.0))
        for name, bone in turned.items():
            if name == "root":
                continue
            bone["world"] =[float(v) for v in (np.array(bone["world"]).reshape(4, 4) @ turn).reshape(16)]
        self.assertAlmostEqual(wp.prepare(w, statics_of(c), turned, wm, wt)["hips_yaw"],
                               pose["hips_yaw"] + math.radians(30.0), places=6)

    def test_a_pose_stands_on_the_walk_s_body_not_on_its_root(self):
        """A walk whose body is turned 35 deg about up against its own root (a diagonal backward walk, 2026-10-16:
        the mirror pair in the animator's scene stood +-35 deg off their roots, the pose placed by the root read
        76 deg off one body and 7 off the other, and Leg match crossed the first one's feet) takes a pose facing
        its root just as the unturned walk does: the same hips turn, the same knee and toe turns."""
        c = clip()
        root = c.names.index("root")
        turn = wm.exp_rot(np.array([0.0, 1.0, 0.0]) * math.radians(35.0))
        turned = np.array(c.worlds, copy=True)          # the whole walk turned rigidly about the origin...
        turned[..., :3, :3] = c.worlds[..., :3, :3] @ turn
        turned[..., 3, :3] = c.worlds[..., 3, :3] @ turn
        turned[root, :, :3, :3] = c.worlds[root, :, :3, :3]     # ...but its root facing the way it did
        w0 = walk()
        w1 = wm.analyse(wm.Clip(c.names, c.parents, turned, c.fps, c.up, "turned"))
        statics = statics_of(c)
        plain = wp.prepare(w0, statics, self.pose_of(c, 5), wm, wt)
        moved = wp.prepare(w1, statics, self.pose_of(c, 5), wm, wt)
        self.assertAlmostEqual(moved["hips_yaw"], plain["hips_yaw"], places=4)
        for key in ("knee_turn", "toe"):
            for side in "lr":
                self.assertAlmostEqual(moved[key][side], plain[key][side], places=4, msg=key + side)
        self.assertAlmostEqual(moved["width"], plain["width"], delta=0.05)

    def test_the_pelvis_height_is_read_over_the_feet_not_the_root(self):
        """A pose whose root stands 17 cm under its feet (dw's, 2026-10-13: the pose's pelvis read over the root
        landed 17 cm low - the walk in a crouch) gives the walk the same height: the pelvis over its feet."""
        w, c = walk(), clip()
        plain = wp.prepare(w, statics_of(c), self.pose_of(c, 5), wm, wt)
        low = self.pose_of(c, 5)
        low["root"]["world"][13] -= 17.0
        pose = wp.prepare(w, statics_of(c), low, wm, wt)
        self.assertAlmostEqual(pose["height"], plain["height"], places=6)
        gap = float(c.worlds[w.index["pelvis"], 5, 3, 1]) - min(float(c.worlds[w.index["ball_" + s], 5, 3, 1]) for s in "lr")
        self.assertAlmostEqual(wp.pose_floor_gap(dict((n, b["world"]) for n, b in low.items()), w), gap, places=6)

    def test_a_pose_on_a_bigger_body_keeps_its_angles_and_scales_its_height(self):
        w, c = walk(), clip()
        big = self.pose_of(c, 5)
        for bone in big.values():
            for key in ("rest", "world"):
                bone[key][12:15] = [v * 1.25 for v in bone[key][12:15]]
        pose = wp.prepare(w, statics_of(c), big, wm, wt)
        self.assertAlmostEqual(pose["scale"], 0.8, places=9)
        self.assertAlmostEqual(pose["height"], float(c.worlds[w.index["pelvis"], 5, 3, 1]), places=6)
        j = w.index["spine_01"]
        want = c.worlds[j, 5, :3, :3] @ c.worlds[w.parents[j], 5, :3, :3].T
        self.assertLess(float(np.abs(pose["spine"][j] - want).max()), 1e-9)


if __name__ == "__main__":
    unittest.main()

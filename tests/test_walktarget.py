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
        result = w.evaluate()
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
        frames, info = rt.frames(w.evaluate())
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

    def test_a_target_without_legs_is_refused(self):
        w, c = walk(), clip()
        target = target_of(c)
        target = dict((n, b) for n, b in target.items() if not n.startswith(("calf_", "foot_", "ball_")))
        with self.assertRaises(wt.Refusal):
            wt.Retarget(w, statics_of(c), target)


if __name__ == "__main__":
    unittest.main()

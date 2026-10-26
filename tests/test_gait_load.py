"""Gait Builder's loader (docs/superpowers/plans/gaitbuilder/gaitload.py): a walk's knobs probed once, kept on the
source and on disk, whatever the pose's share. numpy only; the probe is counted, not run."""

import os
import shutil
import tempfile
import unittest

from tests.test_gait_model import load
from tests.test_gait_aspects import fork_walk

gl = load("gaitload")
asp = gl.asp


class DiskCurves(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.walk = fork_walk()

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.kept = (gl.DISK, gl.asp.calibrate, gl._stamp)
        gl.DISK = os.path.join(self.folder, "cache")
        self.calls = []

        def probe(walk, base, run):
            self.calls.append(walk)
            curves = {"duty": {"": [(-2.0, -1.0), (0.0, 0.0), (2.0, 1.5)]}}
            base["_curve"] = curves
            return curves
        gl.asp.calibrate = probe
        gl._state().clear()

    def tearDown(self):
        gl.DISK, gl.asp.calibrate, gl._stamp = self.kept
        gl._state().clear()
        shutil.rmtree(self.folder, ignore_errors=True)

    def source(self, ident="synthetic"):
        return gl.Source("synthetic", "synthetic", self.walk, {}, 0, None, ident)

    def test_probed_once_whatever_the_share(self):
        src = self.source()
        a = gl.baseline(src, None, 0.0)
        b = gl.baseline(src, None, 0.5)
        self.assertEqual(len(self.calls), 1)
        self.assertIs(a["_curve"], b["_curve"])
        self.assertIn("_knee_planted", a)
        self.assertGreater(a["speed"], 0.0)

    def test_another_maya_reads_the_disk(self):
        first = gl.baseline(self.source(), None, 0.0)["_curve"]
        gl._state().clear()
        src = self.source()
        self.assertFalse(gl.needs_probe(src))
        again = gl.baseline(src, None, 0.0)["_curve"]
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(again, first)
        self.assertEqual(again["duty"][""][2], (2.0, 1.5))

    def test_another_walk_is_probed(self):
        gl.baseline(self.source("one"), None, 0.0)
        gl._state().clear()
        gl.baseline(self.source("two"), None, 0.0)
        self.assertEqual(len(self.calls), 2)

    def test_changed_code_is_probed_again(self):
        gl.baseline(self.source(), None, 0.0)
        gl._state().clear()
        gl._stamp = lambda module: 12345.0
        self.assertTrue(gl.needs_probe(self.source()))

    def test_a_broken_file_is_probed_again(self):
        src = self.source()
        gl.baseline(src, None, 0.0)
        path = gl._disk_path(src)[0]
        with open(path, "w") as f:
            f.write("{not json")
        gl._state().clear()
        gl.baseline(self.source(), None, 0.0)
        self.assertEqual(len(self.calls), 2)

    def test_no_disk(self):
        gl.DISK = None
        src = self.source()
        self.assertTrue(gl.needs_probe(src))
        gl.baseline(src, None, 0.0)
        self.assertFalse(gl.needs_probe(src))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "cache")))

    def test_a_source_without_ident_stays_off_disk(self):
        gl.baseline(self.source(None), None, 0.0)
        self.assertFalse(os.path.exists(os.path.join(self.folder, "cache")))


class PosedCurves(unittest.TestCase):
    """Under a pose the knobs are probed once more at full share, kept per pose, and mixed by the share."""

    @classmethod
    def setUpClass(cls):
        cls.walk = fork_walk()

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.kept = (gl.DISK, gl.asp.calibrate)
        gl.DISK = os.path.join(self.folder, "cache")
        self.calls = []

        def probe(walk, base, run):
            self.calls.append(base.get("_lowered"))
            gain = 2.0 if len(self.calls) > 1 else 1.0
            return {"bob": {"": [(-2.0, -2.0 * gain), (0.0, 0.0), (2.0, 2.0 * gain)]}}
        gl.asp.calibrate = probe
        gl._state().clear()
        self.pose = {"height": 60.0}

    def tearDown(self):
        gl.DISK, gl.asp.calibrate = self.kept
        gl._state().clear()
        shutil.rmtree(self.folder, ignore_errors=True)

    def source(self):
        return gl.Source("synthetic", "synthetic", self.walk, {}, 0, None, "synthetic")

    def test_probed_once_a_pose_whatever_its_share(self):
        src = self.source()
        self.assertTrue(gl.needs_probe(src, self.pose, 0.5))
        gl.baseline(src, self.pose, 0.5)
        gl.baseline(src, self.pose, 0.8)
        self.assertEqual(len(self.calls), 2)                   # the bare walk, then the pose
        self.assertFalse(gl.needs_probe(src, self.pose, 0.3))
        self.assertTrue(gl.needs_probe(src, {"height": 50.0}, 0.3))     # another pose is probed

    def test_the_share_mixes_the_two_responses(self):
        src = self.source()
        half = gl.baseline(src, self.pose, 0.5)["_curve"]["bob"][""]
        self.assertAlmostEqual(gl._at(half, 2.0), 3.0)         # half way between 2 and 4
        self.assertAlmostEqual(gl._at(half, -2.0), -3.0)
        full = gl.baseline(src, self.pose, 1.0)["_curve"]["bob"][""]
        self.assertAlmostEqual(gl._at(full, 2.0), 4.0)

    def test_another_maya_reads_the_posed_responses_off_disk(self):
        gl.baseline(self.source(), self.pose, 1.0)
        gl._state().clear()
        src = self.source()
        self.assertFalse(gl.needs_probe(src, self.pose, 1.0))
        gl.baseline(src, self.pose, 1.0)
        self.assertEqual(len(self.calls), 2)


class Blend(unittest.TestCase):

    def test_read_at_both_asked_changes_and_held_at_the_ends(self):
        bare = {"knee_bend": {"l": [(0.0, 0.0), (10.0, 10.0)]}}
        posed = {"knee_bend": {"l": [(0.0, 0.0), (5.0, 10.0), (20.0, 20.0)]}}
        out = gl.blend_curves(bare, posed, 0.5)["knee_bend"]["l"]
        self.assertEqual([x for x, _ in out], [0.0, 5.0, 10.0, 20.0])
        self.assertAlmostEqual(gl._at(out, 5.0), 0.5 * 5.0 + 0.5 * 10.0)
        self.assertAlmostEqual(gl._at(out, 20.0), 0.5 * 10.0 + 0.5 * 20.0)     # the bare curve held at its end

    def test_the_ends_of_the_share_are_the_curves_themselves(self):
        bare, posed = {"bob": {"": [(0.0, 0.0), (1.0, 1.0)]}}, {"bob": {"": [(0.0, 0.0), (1.0, 3.0)]}}
        self.assertIs(gl.blend_curves(bare, posed, 0.0), bare)
        self.assertIs(gl.blend_curves(bare, posed, 1.0), posed)

    def test_a_pose_is_known_by_its_content(self):
        import numpy as np
        a = {"height": 60.0, "spine": {"spine_01": np.eye(3)}}
        b = {"spine": {"spine_01": np.eye(3)}, "height": 60.0}
        c = {"height": 60.5, "spine": {"spine_01": np.eye(3)}}
        self.assertEqual(gl.pose_ident(a), gl.pose_ident(b))
        self.assertNotEqual(gl.pose_ident(a), gl.pose_ident(c))


if __name__ == "__main__":
    unittest.main()

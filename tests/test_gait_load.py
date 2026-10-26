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


if __name__ == "__main__":
    unittest.main()

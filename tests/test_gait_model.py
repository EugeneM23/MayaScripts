"""Gait Builder's model (docs/superpowers/plans/gaitbuilder/gaitmodel.py), a fork of maya_walk.model: at Walk
Builder's knobs it is Walk Builder, and its new operators change only what they are for. numpy only."""

import importlib.util
import math
import os
import sys
import unittest

import numpy as np

from tests import test_walkmodel as tw

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "docs", "superpowers", "plans", "gaitbuilder")


def load(name):
    """A module of the gaitbuilder folder (its own imports resolved there)."""
    if FOLDER not in sys.path:
        sys.path.insert(0, FOLDER)
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(FOLDER, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gm = load("gaitmodel")
wm = tw.wm


def both(**kw):
    """(Walk Builder's walk, the fork's walk) of one synthetic clip."""
    c = tw.clip(**kw)
    return wm.analyse(c), gm.analyse(gm.Clip(c.names, c.parents, c.worlds.copy(), c.fps, c.up, c.name))


class ParityTests(unittest.TestCase):

    def check(self, given, **kw):
        a, b = both(**kw)
        ra, rb = a.evaluate(given), b.evaluate(given)
        self.assertEqual(ra.worlds.shape, rb.worlds.shape)
        err = float(np.abs(np.asarray(ra.worlds) - np.asarray(rb.worlds)).max())
        self.assertLess(err, 1e-6, "%s: %g" % (given, err))

    def test_defaults(self):
        self.check({})

    def test_own_knobs(self):
        a, _ = both()
        self.check(a.own_knobs())

    def test_long_stride_and_ground_time(self):
        self.check({"stride": 1.3})
        self.check({"ground_time": 1.2})

    def test_two_strides_a_cycle(self):
        self.check({"stride": 1.2, "bob": 2.0}, strides=2)


if __name__ == "__main__":
    unittest.main()

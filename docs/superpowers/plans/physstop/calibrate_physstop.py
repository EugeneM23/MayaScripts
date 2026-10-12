"""Fit the physical stop's constants to the animator's cube (mayapy, numpy).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/calibrate_physstop.py

Prints the damping and the default overshoot / swing, and the fit per component. The cube is
cube_reference.json (its world matrix on every frame 0..30); tests/test_tailbuilder.py decomposes it the way
the model describes motion (cube_components) and runs the three-key model on its frames 0 / 5 / the frame it
passes B (cube_model). The bottom's height and side come from the arc through those three places, so no
constant moves them: they are reported, not fitted.
"""
import importlib.util
import itertools
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tests = load("tailbuilder_tests_fit", os.path.join(REPO, "tests", "test_tailbuilder.py"))
ps = tests.ps
with open(os.path.join(HERE, "cube_reference.json")) as f:
    cube = tests.cube_components(json.load(f))
KEYS = ("travel", "tilt", "sink", "sway")
TARGET = {k: np.array(cube[k]) for k in KEYS}
SCALE = {"travel": 32.36, "tilt": 1.0, "sink": 1.0, "sway": 1.0}   # travel in cm
WEIGHT = {"travel": 1 / 0.3, "tilt": 1 / 2.0}


def run(overshoot, swing):
    model, tr = tests.cube_model(cube, {"overshoot": overshoot, "swing": swing})
    return {k: np.array(v) for k, v in model.items()}, tr.end


def error(model, key):
    return float(np.sqrt(np.mean((model[key] - TARGET[key]) ** 2))) * SCALE[key]


def report(title, zeta, amplitude, swing):
    ps.ZETA = zeta
    model, end = run(amplitude, swing)
    score = sum(error(model, k) * WEIGHT[k] for k in WEIGHT)
    print("%s: ZETA = %.3f, overshoot %.2f, swing %.2f  (score %.3f, settles at frame %d, B passed at %.2f)"
          % (title, zeta, amplitude, swing, score, end, cube["t_b"]))
    for k in KEYS:
        print("   %-6s rms %.3f   (range %.2f)%s" % (k, error(model, k), float(np.ptp(TARGET[k])) * SCALE[k],
                                                    "" if k in WEIGHT else "  - the arc's, not fitted"))


# K_TILT only shapes the lag (the breakdown scales it), so it keeps its two-pose value.
current = (ps.ZETA, dict(ps.DEFAULTS)["overshoot"], dict(ps.DEFAULTS)["swing"])
best = None
for zeta, swing, amplitude in itertools.product(np.linspace(0.22, 0.42, 11), np.linspace(4.25, 5.5, 6),
                                                np.linspace(2.0, 6.5, 10)):
    ps.ZETA = float(zeta)
    model, _ = run(amplitude, swing)
    score = sum(error(model, k) * WEIGHT[k] for k in WEIGHT)
    if best is None or score < best[0]:
        best = (score, float(zeta), float(amplitude), float(swing))
report("the script's constants", *current)
report("the best on this grid", *best[1:])

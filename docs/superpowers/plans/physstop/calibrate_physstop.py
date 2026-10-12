"""Fit the physical stop's constants to the animator's cube (mayapy, numpy).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/calibrate_physstop.py

Prints the constants block for skeldar_physstop.py and the fit per component. The cube is
cube_reference.json (its world matrix on every frame 0..30); tests/test_physstop.py decomposes it the way
the model describes motion (cube_components).
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


tests = load("physstop_tests_fit", os.path.join(REPO, "tests", "test_physstop.py"))
ps = tests.ps
with open(os.path.join(HERE, "cube_reference.json")) as f:
    cube = tests.cube_components(json.load(f))
KEYS = ("travel", "tilt", "sink", "sway", "yaw")
TARGET = {k: np.array(cube[k]) for k in KEYS}
SCALE = {"travel": 32.36, "tilt": 1.0, "sink": 1.0, "sway": 1.0, "yaw": 1.0}   # travel in cm
WEIGHT = {"travel": 1 / 0.3, "tilt": 1 / 2.0, "sink": 1 / 0.15}


def run(overshoot, swing):
    """The three-key model on the cube's frames 0 / 5 / the frame it passes B, the tilt shape scaled to
    the cube's lag at 5 (as a breakdown sets it): tests.cube_model."""
    model, tr = tests.cube_model(cube, {"overshoot": overshoot, "swing": swing})
    return {k: np.array(v) for k, v in model.items()}, tr.end


def error(model, key):
    return float(np.sqrt(np.mean((model[key] - TARGET[key]) ** 2))) * SCALE[key]


def rescale(model, key, current):
    """Least-squares rescale of a component (nearly) linear in its constant."""
    m = model[key]
    if not np.any(m):
        return current
    return current * float(np.dot(m, TARGET[key]) / np.dot(m, m))


best = None
for zeta, swing, amplitude in itertools.product(np.linspace(0.22, 0.42, 11), np.linspace(4.25, 5.5, 6),
                                                np.linspace(2.5, 6.5, 9)):
    ps.ZETA = float(zeta)
    ps.K_SINK = 0.51
    for _ in range(3):                      # the drive saturates softly: iterate the linear rescale
        model, _ = run(amplitude, swing)
        ps.K_SINK = rescale(model, "sink", ps.K_SINK)
    model, _ = run(amplitude, swing)
    score = sum(error(model, k) * WEIGHT[k] for k in WEIGHT)
    if best is None or score < best[0]:
        best = (score, float(zeta), float(swing), float(amplitude), ps.K_SINK)

# K_TILT only shapes the lag now (the breakdown scales it), so it keeps its two-pose value.
_, ps.ZETA, swing, amplitude, ps.K_SINK = best
sway_best = None
for rate in np.linspace(0.4, 1.2, 33):
    ps.SWAY_RATE = float(rate)
    ps.K_SWAY = 0.21
    for _ in range(3):
        model, _ = run(amplitude, swing)
        ps.K_SWAY = rescale(model, "sway", ps.K_SWAY)
    model, _ = run(amplitude, swing)
    e = error(model, "sway")
    if sway_best is None or e < sway_best[0]:
        sway_best = (e, float(rate), ps.K_SWAY)
_, ps.SWAY_RATE, ps.K_SWAY = sway_best
ps.K_YAW = 52.0
for _ in range(3):
    model, end = run(amplitude, swing)
    ps.K_YAW = rescale(model, "yaw", ps.K_YAW)
model, end = run(amplitude, swing)

print("ZETA = %.3f" % ps.ZETA)
print("K_TILT = %.2f" % ps.K_TILT)
print("K_SINK = %.3f" % ps.K_SINK)
print("K_SWAY = %.3f" % ps.K_SWAY)
print("SWAY_RATE = %.3f" % ps.SWAY_RATE)
print("K_YAW = %.1f" % ps.K_YAW)
print("DEFAULTS overshoot %.2f, swing %.2f" % (amplitude, swing))
for k in KEYS:
    print("%-6s rms %.3f   (range %.2f)" % (k, error(model, k), float(np.ptp(TARGET[k])) * SCALE[k]))
print("settles at frame %d (B passed at %.2f)" % (end, cube["t_b"]))

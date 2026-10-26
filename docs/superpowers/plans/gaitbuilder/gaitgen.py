"""gaitgen - a CAT preset as a clip: our CAT (docs/superpowers/plans/catwalk/catmodel.py) synthesises the cycle on
Manny's template, and from then on it is a clip like any other - analysed, measured and tuned by the same knobs.
numpy only."""
import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CATWALK = os.path.normpath(os.path.join(HERE, "..", "catwalk"))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "SkeldarAnim", "assets",
                                         "manny_skeleton_template.json"))
PRESETS = ("Walk", "Jog", "Run", "Sneak")       # Strafe and Backward wait for Direction (step 2)


def _catmodel():
    if "catmodel" in sys.modules:
        return sys.modules["catmodel"]
    if CATWALK not in sys.path:
        sys.path.insert(0, CATWALK)
    spec = importlib.util.spec_from_file_location("catmodel", os.path.join(CATWALK, "catmodel.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["catmodel"] = module
    spec.loader.exec_module(module)
    return module


def template():
    """Manny's template: {name: {"parent", "world_matrix"}}."""
    with open(TEMPLATE) as handle:
        joints = json.load(handle)["joints"]
    return dict((j["name"], {"parent": j.get("parent"), "world_matrix": [float(v) for v in j["world_matrix"]]})
                for j in joints)


def preset_clip(name, fps=30.0, model=None):
    """(clip, statics) of the CAT preset `name` on Manny's template at `fps`: `model` is the walk model module
    whose Clip it builds (gaitmodel by default); statics {leaf: {"parent", "canonical", "rest"}} - Manny's bind."""
    if name not in PRESETS:
        raise ValueError("no CAT preset %r here (%s)" % (name, ", ".join(PRESETS)))
    if model is None:
        import gaitmodel as model
    cm = _catmodel()
    joints = template()
    skel = cm.Skeleton.from_template(joints)
    cycle = cm.generate(skel, cm.preset(name, fps), fps)
    names = list(skel.order)
    index = dict((n, i) for i, n in enumerate(names))
    parents = [index.get(skel.parent[n], -1) if skel.parent[n] is not None else -1 for n in names]
    worlds = np.array([[cycle.frames[f][n] for f in range(len(cycle.frames))] for n in names], float)
    clip = model.Clip(names, parents, worlds, float(fps), (0.0, 1.0, 0.0), "CAT " + name)
    statics = dict((n, {"parent": joints[n].get("parent"), "canonical": n, "rest": list(joints[n]["world_matrix"])})
                   for n in names)
    return clip, statics

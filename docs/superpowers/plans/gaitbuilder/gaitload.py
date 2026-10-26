"""gaitload - Gait Builder's sources and baselines: a walk read into the fork's model (a saved walk, a Walk cycles
card of the Pose Library, a CAT preset), what it measures as it stands (the knobs' own values), and a cycle
evaluated from the animator's units. The saved walks and cards are found through the plugin's maya_walk.scene
(Maya); a CAT preset and a walk file need no Maya.

A source key: "cat:<preset>", "card:<path in the library>.anim", or a saved walk's name."""
import os
import sys

import numpy as np

import gaitmodel as gm
import aspects as asp
import gaitgen

CACHE_KEPT = 12


class Source(object):
    """A walk ready to evaluate: `walk` (gaitmodel.Walk), `statics` {leaf: {"parent", "canonical", "rest"}}, the
    cycle's first frame `start`, a `label`, and the clean `report` (or None)."""

    def __init__(self, key, label, walk, statics, start, report=None):
        self.key, self.label, self.walk, self.statics, self.start, self.report = key, label, walk, statics, start, report


def _state():
    if not hasattr(sys, "_skeldar_gait_cache"):
        sys._skeldar_gait_cache = {}
    return sys._skeldar_gait_cache


def _kept(key, make):
    cache = _state()
    if key not in cache:
        if len(cache) >= CACHE_KEPT:
            cache.pop(next(iter(cache)))
        cache[key] = make()
    return cache[key]


def label_of(key):
    if key.startswith("cat:"):
        return "CAT " + key[4:]
    if key.startswith("card:"):
        return os.path.splitext(os.path.basename(key[5:]))[0]
    return key


def from_file(key, path, clean=None):
    """The walk file at `path` read as Walk Builder reads it: cleaned under the Clean knobs `clean`, the mean pose
    correction beside it applied, analysed by the fork."""
    from maya_walk import model as wm, files as wf, clean as wc, meanpose as mp
    knobs = wc.knobs(clean)
    stamp = os.path.getmtime(path)
    fix_path = mp.path_for(path)
    fix_stamp = os.path.getmtime(fix_path) if os.path.exists(fix_path) else None

    def make():
        data = wf.load(path)
        clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], None, knobs)
        fix = mp.load(fix_path)
        clip = mp.correct(clip, fix)
        walk = gm.analyse(gm.Clip(clip.names, clip.parents, np.array(clip.worlds), clip.fps, clip.up, clip.name))
        walk.fix = mp.model_fix(fix)
        return Source(key, label_of(key), walk, data["statics"], int(data["start"]), report)
    return _kept(("file", path, stamp, fix_stamp, tuple(sorted(knobs.items()))), make)


def from_preset(name, fps):
    def make():
        clip, statics = gaitgen.preset_clip(name, fps, gm)
        return Source("cat:" + name, label_of("cat:" + name), gm.analyse(clip), statics, 0, None)
    return _kept(("preset", name, float(fps)), make)


def load(key, clean=None, fps=30.0):
    """The source `key` (see the module); a saved walk or a card found through maya_walk.scene."""
    if key.startswith("cat:"):
        return from_preset(key[4:], fps)
    from maya_walk import scene
    return from_file(key, scene.walk_path(key), clean)


def baseline(source, pose=None, share=0.0):
    """The walk as it stands under the pose's `share` (`pose` walkpose.prepare's, filtered to its parts): its
    measure in units - the knobs' own values - kept per source, pose and share."""
    def make():
        e = asp.base_engine(source.walk)
        if pose is not None and share > 0.0:
            e["pose"] = share
        result = source.walk.evaluate(e, pose if share > 0.0 else None)
        return asp.measure(source.walk, result.worlds)
    return _kept(("base", id(source), id(pose), float(share)), make)


def evaluate(source, gait, pose=None, share=0.0):
    """(Result, base, the model's knobs) of the source under the animator's units `gait`."""
    base = baseline(source, pose, share)
    e = asp.engine_knobs(source.walk, base, gait)
    if pose is not None and share > 0.0:
        e["pose"] = share
    return source.walk.evaluate(e, pose if share > 0.0 else None), base, e

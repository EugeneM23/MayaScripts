"""gaitload - Gait Builder's sources and baselines: a walk read into the fork's model (a saved walk, a Walk cycles
card of the Pose Library, a CAT preset), what it measures as it stands (the knobs' own values), and a cycle
evaluated from the animator's units. The saved walks and cards are found through the plugin's maya_walk.scene
(Maya); a CAT preset and a walk file need no Maya.

A source key: "cat:<preset>", "card:<path in the library>.anim", or a saved walk's name."""
import hashlib
import json
import os
import sys

import numpy as np

import gaitmodel as gm
import aspects as asp
import gaitgen

CACHE_KEPT = 12
# The calibrated knobs' responses (aspects.calibrate: sixteen evaluations, 3-20 s CPU a walk) are kept on disk per walk
# and code: a walk read again - in this Maya or the next - costs one evaluation. None: no disk.
DISK = os.path.join(os.environ.get("MAYA_APP_DIR") or os.path.join(os.path.expanduser("~"), "Documents", "maya"),
                    "SkeldarGaitCache")


class Source(object):
    """A walk ready to evaluate: `walk` (gaitmodel.Walk), `statics` {leaf: {"parent", "canonical", "rest"}}, the
    cycle's first frame `start`, a `label`, and the clean `report` (or None)."""

    def __init__(self, key, label, walk, statics, start, report=None, ident=None):
        self.key, self.label, self.walk, self.statics, self.start, self.report = key, label, walk, statics, start, report
        self.ident = ident        # what the walk is made of, for the disk cache (None: not kept on disk)
        self.curves = None        # the calibrated knobs' responses, once read (curves())


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
        ident = repr(("file", os.path.normcase(os.path.abspath(path)), stamp, os.path.getsize(path), fix_stamp,
                      tuple(sorted(knobs.items()))))
        return Source(key, label_of(key), walk, data["statics"], int(data["start"]), report, ident)
    return _kept(("file", path, stamp, fix_stamp, tuple(sorted(knobs.items()))), make)


def from_preset(name, fps):
    def make():
        clip, statics = gaitgen.preset_clip(name, fps, gm)
        ident = repr(("preset", name, float(fps), _stamp(gaitgen)))
        return Source("cat:" + name, label_of("cat:" + name), gm.analyse(clip), statics, 0, None, ident)
    return _kept(("preset", name, float(fps)), make)


def load(key, clean=None, fps=30.0):
    """The source `key` (see the module); a saved walk or a card found through maya_walk.scene."""
    if key.startswith("cat:"):
        return from_preset(key[4:], fps)
    from maya_walk import scene
    return from_file(key, scene.walk_path(key), clean)


def _stamp(module):
    path = getattr(module, "__file__", None)
    return os.path.getmtime(path) if path and os.path.exists(path) else None


def _disk_path(source):
    """The file the source's responses live in (None: not on disk): named for the walk and the code that probed it,
    so a changed walk, clean, mean pose correction, model or knob table is probed again."""
    if not DISK or not source.ident:
        return None
    ident = repr((source.ident, _stamp(gm), _stamp(asp)))
    return os.path.join(DISK, hashlib.sha1(ident.encode("utf-8")).hexdigest() + ".json"), ident


def _read_curves(source):
    got = _disk_path(source)
    if got is None or not os.path.exists(got[0]):
        return None
    try:
        with open(got[0], "r") as f:
            data = json.load(f)
        if data.get("ident") != got[1]:
            return None
        return dict((name, dict((side, [tuple(float(x) for x in p) for p in points])
                                for side, points in sides.items()))
                    for name, sides in data["curves"].items())
    except Exception:
        return None


def _write_curves(source, curves):
    got = _disk_path(source)
    if got is None:
        return
    try:
        if not os.path.isdir(DISK):
            os.makedirs(DISK)
        part = got[0] + ".part"
        with open(part, "w") as f:
            json.dump({"ident": got[1], "curves": curves}, f)
        os.replace(part, got[0])
    except Exception:
        pass


def _plain(source, posed=None, share=0.0):
    """The walk as it stands (under the pose's share): its measure in units and what the knobs need of the model's
    own evaluation (aspects.annotate)."""
    e = asp.base_engine(source.walk)
    if posed is not None:
        e["pose"] = share
    result = source.walk.evaluate(e, posed)
    base = asp.measure(source.walk, result.worlds)
    asp.annotate(source.walk, base, result)
    return base


def needs_probe(source):
    """True when the source's knobs have not been probed yet and are not on disk (the next baseline takes sixteen
    evaluations more)."""
    if source.curves is not None:
        return False
    got = _read_curves(source)
    if got is not None:
        source.curves = got
        return False
    return True


def curves(source, plain=None):
    """The calibrated knobs' responses on the source's walk (aspects.calibrate: their curves, the pelvis's drop
    along Step and Ground time), probed once a walk with no pose -
    a pose's share changes the walk's own values, which a baseline measures again, not how far a knob moves them -
    and kept on the source and on disk. `plain` is the walk's own unposed measure when already made."""
    if source.curves is None:
        got = _read_curves(source)
        if got is None:
            base = dict(plain) if plain is not None else _plain(source)
            got = asp.calibrate(source.walk, base,
                                lambda g: source.walk.evaluate(asp.engine_knobs(source.walk, base, g)))
            _write_curves(source, got)
        source.curves = got
    return source.curves


def baseline(source, pose=None, share=0.0):
    """The walk as it stands under the pose's `share` (`pose` walkpose.prepare's, filtered to its parts): its
    measure in units - the knobs' own values - with the calibrated knobs' responses (curves()), kept per source,
    pose and share. One evaluation, sixteen more the first time a walk is read with no responses on disk."""
    posed = pose if share > 0.0 else None

    def make():
        base = _plain(source, posed, share)
        base["_curve"] = curves(source, base if posed is None else None)
        return base
    return _kept(("base", id(source), id(pose), float(share)), make)


def evaluate(source, gait, pose=None, share=0.0):
    """(Result, base, the model's knobs) of the source under the animator's units `gait`."""
    base = baseline(source, pose, share)
    e = asp.engine_knobs(source.walk, base, gait)
    if pose is not None and share > 0.0:
        e["pose"] = share
    return source.walk.evaluate(e, pose if share > 0.0 else None), base, e

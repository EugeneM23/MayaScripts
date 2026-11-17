"""verify_walk_wholeclip - mayapy STANDALONE proof of Walk Builder on a whole clip
(docs/superpowers/specs/2026-11-17-walk-builder-whole-clip-design.md).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_wholeclip.py [clip.pkl]

Clips: Unreal's AS_am_LongS_OxGuardL_Walk_Fwd_Start (a start into strides, %TEMP%/maya_uebridge) and, when given,
a pickled clip ({names, parents, worlds}) - the animator's start-and-walk read off their scene, not committed. Each is
keyed onto the plugin's Manny UE5 skeleton, then pressed through maya_walk.scene.apply(whole=True) in a temporary
walks folder, and read back off the joints.
"""
import os
import pickle
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, PLANS)
import verify_startstop as vs  # noqa: E402  (initialises Maya standalone, loads the plugins)

cmds = vs.cmds
from maya_walk import scene as ws, wholeclip  # noqa: E402
from maya_startstop import model as ss, scene as sss  # noqa: E402

PKL = sys.argv[1] if len(sys.argv) > 1 else ""
GATES = []


def gate(name, ok, detail):
    GATES.append((name, bool(ok)))
    print("%s  %-66s %s" % ("PASS" if ok else "FAIL", name, detail))


def keyed(root):
    return sss.read_worlds(root)[0]


def key_pickled(root, path):
    data = pickle.load(open(path, "rb"))
    bones, _n = ws.read_bones(root)
    names = list(data["names"])
    written = [n for n in names if n in bones]
    om = ws._om()
    worlds = np.asarray(data["worlds"], float)
    frames = [dict((n, om.MMatrix([float(v) for v in worlds[names.index(n), f].reshape(16)])) for n in written)
              for f in range(worlds.shape[1])]
    values, static = ws.channel_values(bones, frames, written, set(written))
    ws.write_curves(values, static, 0)
    cmds.playbackOptions(minTime=0, maxTime=worlds.shape[1] - 1, animationStartTime=0,
                         animationEndTime=worlds.shape[1] - 1)


def jerk(clip, worlds, name):
    p = worlds[clip.index[name], :, 3, :3]
    return np.linalg.norm(p[2:] - 2 * p[1:-1] + p[:-2], axis=1)


def slide(clip, a, w):
    worst = 0.0
    for s in ss.SIDES:
        for joint in ("foot_" + s, "ball_" + s):
            j = clip.index[joint]
            for c0, c1 in a.feet[s]["contacts"]:
                for f in range(c0 + 1, c1 + 1):
                    moved = float(np.linalg.norm(w[j, f, 3, :3] - w[j, f - 1, 3, :3]))
                    own = float(np.linalg.norm(clip.worlds[j, f, 3, :3] - clip.worlds[j, f - 1, 3, :3]))
                    worst = max(worst, moved - own)
    return worst


def lengths(clip, w):
    worst = 0.0
    for j in range(clip.J):
        p = clip.parents[j]
        if p < 0 or clip.names[j].startswith(("ik_", "pelvis")):
            continue
        new = np.linalg.norm(w[j, :, 3, :3] - w[p, :, 3, :3], axis=1)
        old = np.linalg.norm(clip.worlds[j, :, 3, :3] - clip.worlds[p, :, 3, :3], axis=1)
        worst = max(worst, float(np.abs(new - old).max()))
    return worst


POINTS = ("head", "hand_r", "hand_l", "lowerarm_r", "lowerarm_l", "spine_05")


def _hips_frame(get):
    p = get("pelvis")
    s = get("thigh_l") - get("thigh_r")
    s[1] = 0.0
    s /= np.linalg.norm(s)
    up = np.array([0.0, 1.0, 0.0])
    r = np.stack([s, up, np.cross(s, up)])
    return dict((n, r @ (get(n) - p)) for n in POINTS)


def in_pose(clip, card_path, f):
    """The worst distance (cm) of the head, hands, elbows and chest at frame `f` from where the pose card has them,
    both read in the hips' own frame."""
    from maya_walk import cards as wcards
    _n, bones = wcards.read_card(card_path)
    want = _hips_frame(lambda n: np.array(bones[n]["world"], float).reshape(4, 4)[3, :3])
    got = _hips_frame(lambda n: clip.worlds[clip.index[n], f, 3, :3])
    return max(float(np.linalg.norm(got[n] - want[n])) for n in POINTS)


def params(**changes):
    return ws.normal_params({"changes": dict((k, v) for k, v in changes.items()), "physics": False})


def check(label, root, card):
    source = keyed(root)
    a = ss.Analysis(source)
    walk = ws.capture_source(root)
    _r, _i, text = ws.apply(root, walk, None, None, ws.ALL_PARTS, params=params(), whole=True)
    gate("%s: Pick keys the whole clip" % label, "whole clip" in text and ws.memo_of(root).get("whole"),
         text.split("|")[0].strip()[:110])
    own = keyed(root)
    off = float(np.abs(own.worlds[:, :, 3, :3] - source.worlds[:, :, 3, :3]).max())
    gate("%s: the walk's own values give the clip back" % label, off < 0.5, "%.3f cm" % off)
    gate("%s: every frame keyed" % label, own.F == source.F, "%d of %d" % (own.F, source.F))
    asked = params(height=("offset", 5.0))
    _r, info, text = ws.apply(root, walk, None, None, ws.ALL_PARTS, params=asked, whole=True)
    up = keyed(root)
    pelvis = source.index["pelvis"]
    rise = up.worlds[pelvis, :, 3, 1] - source.worlds[pelvis, :, 3, 1]
    anim = ws.animate(root, walk, None, None, ws.ALL_PARTS, params=asked, whole=True)
    lc = anim.walk.clip
    li = lc.names.index("pelvis")
    loop = ss.Cycle(ss.Clip(lc.names, lc.parents, np.asarray(lc.worlds), lc.fps, "loop"))
    res = ss.Cycle(ss.Clip(lc.names, lc.parents, np.asarray(anim.moving), lc.fps, "res"))
    whole_info = info["whole"]
    gaps, rises = [], []
    for t0, t1 in whole_info["walking"]:
        for f in range(t0, min(t1, source.F)):
            ph = whole_info["phases"][f]
            want = res.sample(ph)[li, 3, 1] - loop.sample(ph)[li, 3, 1]
            gaps.append(abs(rise[f] - want))
            rises.append(want)
    gate("%s: Height +5 on the walking frames as on the walk's loop" % label,
         float(np.median(gaps)) < 0.5 and float(np.max(np.abs(rises))) > 0.5,
         "median %.2f cm off the loop's own rise (it reaches %.2f)" % (float(np.median(gaps)),
                                                                     float(np.max(np.abs(rises)))))
    gate("%s: no planted foot slides more than the clip's" % label, slide(source, a, up.worlds) < 0.05,
         "%.4f cm a frame" % slide(source, a, up.worlds))
    gate("%s: every bone the clip's length" % label, lengths(source, up.worlds) < 0.05,
         "%.4f cm" % lengths(source, up.worlds))
    worst = max(float((jerk(source, up.worlds, n) - jerk(source, source.worlds, n)).max())
                for n in ("pelvis", "spine_05", "head", "hand_r", "hand_l"))
    gate("%s: no jolt above the clip's own" % label, worst < 1.5, "%.2f cm a frame^2 over the clip's" % worst)
    if card:
        from maya_walk import cards as wcards
        _r, pinfo, _t = ws.apply(root, walk, None, None, ws.ALL_PARTS, pose_card=card,
                                 params=dict(params(), pose=1.0), whole=True)
        posed = keyed(root)
        order = pinfo["whole"]["names"]           # the stance in the clip's own joint order: put in the source's
        stance = np.asarray(pinfo["whole"]["stance_worlds"])[[order.index(n) for n in source.names]]
        still = a.stillness_at(float(np.mean(ss.Analysis(source).com_speed)))
        f0 = int(np.argmax(still))
        moved = float(np.abs(posed.worlds[:, f0, 3, :3] - source.worlds[:, f0, 3, :3]).max())
        gate("%s: the pose's stance where the body stands" % label, moved > 1.0, "%.1f cm at frame %d" % (moved, f0))
        # a start begins IN the pose (2026-11-17, «мы должны стартовать из указаной позы»): its first frame's hands,
        # elbows and head where the card has them, in the hips' own frame
        if whole_info.get("start") is not None and whole_info["start"][0] == 0:
            off = in_pose(posed, card, 0)
            gate("%s: the start's first frame is the card's pose" % label, off < 3.0, "%.1f cm at worst" % off)
        gate("%s: posed, no planted foot slides" % label, slide(source, a, posed.worlds) < 0.05,
             "%.4f cm a frame" % slide(source, a, posed.worlds))
        # the pose's own stance (Start/Stop Builder's model on this clip) changes posture as the body picks up
        # speed; the blend must add no jolt above whichever of the clip and that stance jolts more
        worst = max(float((jerk(source, posed.worlds, n)
                           - np.maximum(jerk(source, source.worlds, n), jerk(source, stance, n))).max())
                    for n in ("pelvis", "spine_05", "head"))
        gate("%s: posed, no jolt above the clip's or the stance's own" % label, worst < 1.5,
             "%.2f cm a frame^2" % worst)
    cmds.undoInfo(state=True)
    before = keyed(root).worlds
    ws.apply(root, walk, None, None, ws.ALL_PARTS, params=params(height=("offset", 9.0)), whole=True)
    cmds.undo()
    back = float(np.abs(keyed(root).worlds - before).max())
    gate("%s: one undo takes a press back" % label, back < 1e-4, "%.2e" % back)
    ws.restore_source(root)
    gone = float(np.abs(keyed(root).worlds[:, :, 3, :3] - source.worlds[:, :, 3, :3]).max())
    gate("%s: Restore gives the clip back" % label, gone < 1e-3, "%.2e cm" % gone)


def main():
    folder = tempfile.mkdtemp()
    cmds.optionVar(stringValue=("skeldarWalkFolder", folder))
    poses = vs.cards()
    card = poses["goblin"]
    root = vs.add_skeleton()
    vs.key_clip(root, vs.START, "wcstart")
    check("OxGuard start", root, card)
    if PKL and os.path.exists(PKL):
        other = vs.add_skeleton()
        key_pickled(other, PKL)
        check("the animator's start-walk", other, card)
    failed = [n for n, ok in GATES if not ok]
    print("\n%d of %d gates failed" % (len(failed), len(GATES)))
    for n in failed:
        print("  FAILED: " + n)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        os._exit(0)

"""Standalone gates for the two retarget versions and the choice between them (2026-10-02).

    mayapy verify_retarget_modes.py [PLUGIN_DIR] [PHASES]

mayapy STANDALONE, empty scenes (it adds rigs and skeletons, imports and deletes clips):
never the animator's scene. PLUGIN_DIR defaults to the SkeldarAnim folder beside this
repository's docs; PHASES is a comma list of a,b,c,f,g (all by default).

The question is answered by an injected answerer (`maya_retargetmode.set_asker`), which
also counts how often it was asked: a batch session has no dialog, and the gates are
about WHEN the press asks as much as about what it builds.

  a  a UE5 3P clip onto Manny_Rig through the Retarget button: Auto takes the stretch
     without asking (a twin), and it is the old twin path to the number - a second Manny
     retargeted by the legacy call stands where the first does on every sampled frame.
  b  the same clip onto Creep_Rig and Orc_D_Rig: Auto asks once each; Keep proportions
     keeps every bone length of the game skeleton (its bind lengths) and turns the bones
     as the clip's; Squash & stretch puts every paired bone on the clip's joint at our
     size and changes the lengths by the measured proportion difference.
  c  onto a Manny UE5 skeleton and a Creep skeleton (the bridge's Skeleton mode): the
     same two ways, a twin exact without asking.
  f  a batch of three clips onto Creep skeletons asks ONCE, the worst named.
  g  Cancel - the Retarget button, a bridge import onto a new rig, a batch onto new rigs:
     no node left behind, the rig's take as it was, the scene's time unit, its keys, its
     ranges and its frame as they were (an FBX import switches all four).
  h  the scale pivot (the fix pass): a clip standing off the origin, moved and turned,
     squashed & stretched onto a Creep through the Retarget button - the game root starts
     where the clip's root does, not (1 - s) of the way to the origin; and a bridge import
     onto a Creep standing turned at a place keeps it there.

The fix pass (2026-10-02) also made b4 measure the stretch AS THE RIG STANDS (legs in
IK keep their lengths and say so), b6 find the follows by their attribute and put the
bones' translates back, e check that Rotations keep Manny's IK feet on the clip's, and
d move the clip after the connect (one frame for the PlayerMale's body).
"""
import math
import os
import sys
import time

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = (sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
          else os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
if not os.path.isdir(PLUGIN):
    PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "SkeldarAnim"))
PHASES = set((sys.argv[2] if len(sys.argv) > 2 else "a,b,c,f,g,h").split(","))
sys.path.insert(0, PLUGIN)
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass

EXPORT = "C:/!!!Work/Animations/Export/"
HEAVY = EXPORT + "LongSword_Attack_Right_Heavy_3P.FBX"
THRUST = EXPORT + "ShortSword_Attack_Thrust_3P.FBX"
WALK = EXPORT + "ShortSword_Walk_1P.fbx"

import maya_retargetmode as rm
import maya_rigs
import maya_rig_retarget as rr
import maya_asretarget as ar
from maya_scenesetup import catalog, character
from maya_uebridge import rigimport, skeletonimport, lineimport

print("plugin:", os.path.dirname(rm.__file__))
FAILS = []
ASKED = []
ANSWER = [rm.KEEP]


def gate(n, ok, msg):
    print("%s gate %s: %s" % ("PASS" if ok else "FAIL", n, msg))
    sys.stdout.flush()
    if not ok:
        FAILS.append(n)


def answerer(text):
    ASKED.append(text)
    return ANSWER[0]


rm.set_asker(answerer)
rm.set_setting(rm.AUTO)


def leaf(p):
    return p.split("|")[-1].split(":")[-1]


def joints(root):
    return [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or [])


def by_leaf(root):
    return dict((leaf(p), p) for p in joints(root))


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


def quat(n):
    m = om.MMatrix(cmds.xform(n, q=True, ws=True, m=True))
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def import_clip(path, ns):
    before = set(cmds.ls(type="joint", long=True))
    cmds.namespace(add=ns)
    cmds.namespace(set=":" + ns)
    mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
    mel.eval('FBXImport -f "%s";' % path)
    cmds.namespace(set=":")
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    root = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")),
               key=lambda j: j.count("|"))
    return root


def clip_range(root):
    paths = list(by_leaf(root).values())
    return cmds.findKeyframe(paths, which="first"), cmds.findKeyframe(paths, which="last")


def frames(first, last, n=7):
    return [round(first + (last - first) * i / float(n - 1)) for i in range(n)]


def add(key):
    before = set(r.namespace for r in maya_rigs.rigs())
    text = character.add_character(catalog.character_by_key(key))
    print("   ", text.splitlines()[0])
    fresh = [r for r in maya_rigs.rigs() if r.namespace not in before]
    return fresh[0] if fresh else None


def add_skeleton(key):
    before = set(cmds.ls(type="joint", long=True))
    text = character.add_character(catalog.character_by_key(key))
    print("   ", text.splitlines()[0])
    fresh = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    return min(fresh, key=lambda p: (p.count("|"), p))


SKIP_POS = ("ik_", "weapon_", "camera_", "center_of_mass", "interaction")


def skeleton_pairs(target_root, source_root):
    t, s = by_leaf(target_root), by_leaf(source_root)
    return [(n, t[n], s[n]) for n in sorted(t) if n in s]


def lengths_now(paths):
    out = {}
    for name, path in paths.items():
        par = cmds.listRelatives(path, parent=True, fullPath=True, type="joint")
        if par:
            out[name] = (pos(path) - pos(par[0])).length()
    return out


def bind_lengths(paths):
    out = {}
    for name, path in paths.items():
        par = cmds.listRelatives(path, parent=True, fullPath=True, type="joint")
        if par:
            a = om.MMatrix(rm.rest_world(path))
            b = om.MMatrix(rm.rest_world(par[0]))
            out[name] = (om.MVector(a[12], a[13], a[14]) - om.MVector(b[12], b[13], b[14])).length()
    return out


LIMB = ("upperarm_", "lowerarm_", "thigh_", "calf_")


def compare(target_root, source_root, samples, scale=1.0):
    """Over the sampled frames: (worst position off the scaled clip joint, its bone; worst
    orientation off the clip bone among non-limb, non-twist bones; worst limb direction;
    worst length change against the bind, its bone)."""
    pairs = [(n, t, s) for n, t, s in skeleton_pairs(target_root, source_root)
             if not n.startswith(SKIP_POS)]
    tpaths = dict((n, t) for n, t, _ in pairs)
    rest = bind_lengths(tpaths)
    worst_pos, worst_rot, worst_dir, worst_len = (0.0, ""), (0.0, ""), (0.0, ""), (0.0, "")
    for f in samples:
        cmds.currentTime(f, update=True)
        now = lengths_now(tpaths)
        for n, t, s in pairs:
            if "twist" in n:
                continue
            d = (pos(t) - pos(s) * scale).length()
            if d > worst_pos[0]:
                worst_pos = (d, "%s@%g" % (n, f))
            if n.startswith(LIMB):
                kids = [k for k in (cmds.listRelatives(t, children=True, type="joint", fullPath=True) or [])
                        if leaf(k).replace("_twist", "") and "twist" not in leaf(k)]
                skids = dict((leaf(k), k) for k in cmds.listRelatives(s, children=True, type="joint", fullPath=True) or [])
                for k in kids:
                    if leaf(k) in skids:
                        a = (pos(k) - pos(t)).normal()
                        b = (pos(skids[leaf(k)]) - pos(s)).normal()
                        dd = math.degrees(math.acos(max(-1.0, min(1.0, a * b))))
                        if dd > worst_dir[0]:
                            worst_dir = (dd, "%s@%g" % (n, f))
            else:
                r = ang(quat(t), quat(s))
                if r > worst_rot[0]:
                    worst_rot = (r, "%s@%g" % (n, f))
        for n, l in now.items():
            # the pelvis's "length" is the hips' motion off the root, not a bone
            if n in rest and "twist" not in n and n != "pelvis":
                d = abs(l - rest[n])
                if d > worst_len[0]:
                    worst_len = (d, "%s@%g" % (n, f))
    return worst_pos, worst_rot, worst_dir, worst_len


LIMB_BONES = {"leg_l": ("thigh_l", "calf_l", "foot_l", "ball_l"),
              "leg_r": ("thigh_r", "calf_r", "foot_r", "ball_r"),
              "arm_l": ("upperarm_l", "lowerarm_l", "hand_l"),
              "arm_r": ("upperarm_r", "lowerarm_r", "hand_r")}


def ik_bones(rig):
    """{limb in IK: its game bones} (fingers ride an IK hand too)."""
    out = {}
    for limb in ar.ik_limbs(dict((label, cmds.getAttr(maya_rigs.node(rig, "FKIK%s%s.FKIKBlend" % (b, s))))
                                 for b, s, label in ar.IK_LIMBS
                                 if cmds.objExists(maya_rigs.node(rig, "FKIK%s%s.FKIKBlend" % (b, s))))):
        names = set(LIMB_BONES[limb])
        if limb.startswith("arm"):
            side = limb[-1]
            names |= set(n for n in by_leaf(rig.skeleton_root)
                         if n.endswith("_" + side) and rm.region_of(n) == "fingers")
        out[limb] = names
    return out


def compare_as_it_stands(target_root, source_root, samples, scale, limbs):
    """The stretch take as the rig stands: (worst position of a bone OUTSIDE the IK limbs off
    the scaled clip joint, its bone; worst length change of an IK limb's bone against the
    bind; worst IK END bone off the scaled clip joint)."""
    inside = set()
    for names in limbs.values():
        inside |= names
    ends = set(n for names in limbs.values() for n in names if n.startswith(("foot_", "hand_")))
    pairs = [(n, t, s) for n, t, s in skeleton_pairs(target_root, source_root)
             if not n.startswith(SKIP_POS) and "twist" not in n]
    tpaths = dict((n, t) for n, t, _ in pairs)
    rest = bind_lengths(tpaths)
    out_pos, ik_len, ik_end = (0.0, ""), (0.0, ""), (0.0, "")
    for f in samples:
        cmds.currentTime(f, update=True)
        now = lengths_now(tpaths)
        for n, t, s in pairs:
            d = (pos(t) - pos(s) * scale).length()
            if n in ends and d > ik_end[0]:
                ik_end = (d, "%s@%g" % (n, f))
            if n in inside:
                if n in rest and n in now and n not in ("foot_l", "foot_r", "hand_l", "hand_r"):
                    dl = abs(now[n] - rest[n])
                    if dl > ik_len[0]:
                        ik_len = (dl, "%s@%g" % (n, f))
                continue
            if d > out_pos[0]:
                out_pos = (d, "%s@%g" % (n, f))
    return out_pos, ik_len, ik_end


def time_setup():
    """A film scene with keys of its own, ranges and a frame - what a Cancel must give back."""
    cmds.currentUnit(time="film", updateAnimation=True)
    loc = cmds.spaceLocator(name="verifyTimeKeys")[0]
    cmds.setKeyframe(loc, attribute="tx", time=24, value=1)
    cmds.setKeyframe(loc, attribute="tx", time=48, value=2)
    cmds.playbackOptions(min=5, max=40, animationStartTime=0, animationEndTime=50)
    cmds.currentTime(7)
    return loc


def time_now(loc):
    return (cmds.currentUnit(q=True, time=True),
            tuple(cmds.keyframe(loc + ".tx", q=True, timeChange=True) or []),
            tuple(cmds.playbackOptions(q=True, **{f: True})
                  for f in ("min", "max", "animationStartTime", "animationEndTime")),
            cmds.currentTime(q=True))


TIME_EXPECTED = ("film", (24.0, 48.0), (5.0, 40.0, 0.0, 50.0), 7.0)


def region_lengths(paths):
    out = {}
    for n, l in lengths_now(paths).items():
        if n.startswith(SKIP_POS) or n in ("pelvis", "root") or "twist" in n:
            continue
        r = rm.region_of(n)
        if r:
            out[r] = out.get(r, 0.0) + l
    return out


def module_name(mod):
    return getattr(mod, "__name__", "")


def snapshot():
    return set(cmds.ls(cmds.ls(), uuid=True) or [])


EXCUSED_TYPES = ("UsdDefaultRenderSettings", "shapeEditorManager", "poseInterpolatorManager",
                 "nodeGraphEditorInfo", "hyperGraphInfo", "hyperLayout", "dagPose", "objectSet")


def leftovers(before):
    new = [n for n in (cmds.ls(list(snapshot() - before)) or [])]
    return [n for n in new if cmds.nodeType(n) not in EXCUSED_TYPES]


# ------------------------------------------------------------------- a
if "a" in PHASES:
    print("--- phase a: a UE5 3P clip onto Manny_Rig")
    cmds.file(new=True, force=True)
    manny = add("Manny_Rig")
    legacy = add("Manny_Rig")
    src = import_clip(HEAVY, "clip")
    first, last = clip_range(src)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    m, refusal = ar.measure(source_root=src, rig=manny)
    gate("a1", m is not None and m.twin and abs(m.scale - 1.0) < 1e-3,
         "measured a twin: median %.5f, s %.5f, %d lengths, the clip's own stretch %s %.3f cm"
         % (m.median, m.scale, m.count, m.stretch_bone, m.stretch_cm) if m else refusal)
    del ASKED[:]
    t0 = time.time()
    ok, text = rr.run_retarget(source_root=src, rig=manny)
    print("   ", text[:300], "(%.1fs)" % (time.time() - t0))
    gate("a2", ok and not ASKED and "twin, exact" in text and ar.connected_mode(manny) is None,
         "Auto: stretch, nothing asked (%d questions), the line says why" % len(ASKED))
    # the legacy call on the second Manny: the old twin path
    cmds.currentTime(first)
    mod = ar
    mod.reset_build_pose(legacy)
    print("   ", mod.connect(source_root=src, rig=legacy).splitlines()[0])
    print("   ", rr.bake(rig=legacy)[:160])
    samples = frames(first, last)
    worst_pos, worst_rot, _d, _l = compare(manny.skeleton_root, src, samples)
    gate("a3", worst_pos[0] < 0.1 and worst_rot[0] < 0.1,
         "every bone on the clip's: worst %.5f cm (%s), %.5f deg (%s)" % (worst_pos + worst_rot))
    a, b = by_leaf(manny.skeleton_root), by_leaf(legacy.skeleton_root)
    worst = (0.0, "")
    for f in samples:
        cmds.currentTime(f, update=True)
        for n in a:
            if n in b:
                d = (pos(a[n]) - pos(b[n])).length()
                if d > worst[0]:
                    worst = (d, "%s@%g" % (n, f))
    gate("a4", worst[0] < 1e-6, "the twin's stretch IS the old twin path: Manny_Rig against the "
         "legacy Manny_Rig1 worst %.2e cm (%s)" % worst)

# ------------------------------------------------------------------- b
if "b" in PHASES:
    print("--- phase b: the same clip onto Creep_Rig and Orc_D_Rig, both versions")
    for key in ("Creep_Rig", "Orc_D_Rig"):
        cmds.file(new=True, force=True)
        keep = add(key)
        squash = add(key)
        src = import_clip(HEAVY, "clip")
        first, last = clip_range(src)
        cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
        samples = frames(first, last)
        m, _ = ar.measure(source_root=src, rig=keep)
        print("    measured:", m.median, m.scale, m.regions, m.stretch_bone, m.stretch_cm)
        before_regions = region_lengths(dict((n, p) for n, p in by_leaf(squash.skeleton_root).items()))
        bind_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in by_leaf(squash.skeleton_root).items())
        del ASKED[:]
        ANSWER[0] = rm.KEEP
        ok, text = rr.run_retarget(source_root=src, rig=keep)
        print("   ", text[:240])
        gate("b1-" + key, ok and len(ASKED) == 1 and ("onto " + keep.namespace) in ASKED[0]
             and "arms" in ASKED[0] and "rotations - %s keeps its proportions" % keep.namespace in text,
             "Auto asked once (%d) naming the rig and the regions; Keep -> rotations: %s"
             % (len(ASKED), (ASKED[0].splitlines()[1] if ASKED else "")))
        worst_pos, worst_rot, worst_dir, worst_len = compare(keep.skeleton_root, src, samples)
        gate("b2-" + key, worst_len[0] < 1e-4 and worst_rot[0] < 0.01 and worst_dir[0] < 2.0,
             "rotations: lengths kept to %.2e cm (%s), orientations on the clip's to %.5f deg (%s), "
             "limb directions %.3f deg (%s); positions off by up to %.2f cm (the proportions)"
             % (worst_len + worst_rot + worst_dir + (worst_pos[0],)))
        del ASKED[:]
        ANSWER[0] = rm.SQUASH
        ok, text = rr.run_retarget(source_root=src, rig=squash)
        print("   ", text[:240])
        gate("b3-" + key, ok and len(ASKED) == 1 and "stretch - %s squashed" % squash.namespace in text,
             "Auto asked once; Squash & stretch -> stretch")
        cmds.currentTime(first, update=True)
        limbs = ik_bones(squash)
        out_pos, ik_len, ik_end = compare_as_it_stands(squash.skeleton_root, src, samples, m.scale, limbs)
        named = all(limb in text for limb in limbs) and ("in IK keep" in text if limbs else True)
        gate("b4-" + key, out_pos[0] < 0.05 and ik_len[0] < 1e-3 and ik_end[0] < 1.0 and named,
             "stretch AS THE RIG STANDS: every bone outside the IK limbs (%s) on the clip's joint at "
             "x%.4f to %.4f cm (%s); the IK limbs' bones keep their lengths to %.2e cm (%s), their ends "
             "%.4f cm off the clip's (%s); the line names them: %s"
             % (", ".join(sorted(limbs)) or "none", m.scale, out_pos[0], out_pos[1], ik_len[0], ik_len[1],
                ik_end[0], ik_end[1], named))
        # the FK product: every limb shown in FK for the measurement (the rig's legs default to
        # IK, and an IK limb reaches with the rig's own lengths) and put back after
        blends = [maya_rigs.node(squash, "FKIK%s_%s.FKIKBlend" % (limb, side))
                  for limb in ("Arm", "Leg") for side in ("L", "R")]
        blends = [b for b in blends if cmds.objExists(b)]
        held = [(b, cmds.getAttr(b)) for b in blends]
        for b in blends:
            cmds.setAttr(b, 0)
        try:
            worst_pos, worst_rot, worst_dir, worst_len = compare(squash.skeleton_root, src, samples, m.scale)
        finally:
            for b, v in held:
                cmds.setAttr(b, v)
        gate("b4fk-" + key, worst_pos[0] < 0.05 and worst_rot[0] < 0.05,
             "stretch, the limbs switched to FK for the measurement: every paired bone on the clip's "
             "joint at x%.4f to %.4f cm (%s), turned as the clip's to %.4f deg (%s); lengths moved up "
             "to %.2f cm" % (m.scale, worst_pos[0], worst_pos[1], worst_rot[0], worst_rot[1], worst_len[0]))
        cmds.currentTime(first, update=True)
        after_regions = region_lengths(dict((n, p) for n, p in by_leaf(squash.skeleton_root).items()))
        measured = dict(m.regions)
        rows = []
        worst_pp = 0.0
        for r in ("arms", "legs", "spine", "neck"):
            if r in before_regions and r in measured:
                got = 100.0 * (after_regions[r] - before_regions[r]) / before_regions[r]
                rows.append("%s %+.1f%% (asked %+.1f%%)" % (r, got, measured[r]))
                worst_pp = max(worst_pp, abs(got - measured[r]))
        gate("b5-" + key, worst_pp < 1.0,
             "the lengths changed by the measured difference at the first frame: %s - worst %.2f points"
             % (", ".join(rows), worst_pp))
        def our_follows():
            return [c for c in cmds.listRelatives(squash.skeleton_root, allDescendents=True,
                                                  type="pointConstraint", fullPath=True) or []
                    if cmds.attributeQuery(ar.FOLLOW_ATTR, node=c, exists=True)]
        follows = our_follows()
        followed = set(leaf(cmds.listRelatives(c, parent=True, fullPath=True)[0]) for c in follows)
        # the same rig retargeted again with Rotations: the position follow taken away, every
        # length back to the bind
        del ASKED[:]
        ok, text = rr.run_retarget(source_root=src, rig=squash, bones=rm.ROTATION)
        left = our_follows()
        now_t = by_leaf(squash.skeleton_root)
        worst_t = max([max(abs(a - b) for a, b in zip(cmds.getAttr(now_t[n] + ".translate")[0], bind_t[n]))
                       for n in followed if n in now_t] or [0.0])
        worst_pos, worst_rot, worst_dir, worst_len = compare(squash.skeleton_root, src, samples)
        gate("b6-" + key, ok and not ASKED and follows and not left and worst_len[0] < 1e-4 and worst_t < 1e-6,
             "stretch gave %d game bones a position follow (found by their attribute under the "
             "skeleton); Rotations on the same rig takes them away (%d left), their translates "
             "written back to the bind's to %.2e, every length the bind's again to %.2e cm (%s)"
             % (len(follows), len(left), worst_t, worst_len[0], worst_len[1]))

# ------------------------------------------------------------------- c
if "c" in PHASES:
    print("--- phase c: onto skeletons (the bridge's Skeleton mode)")
    for key, label in (("Manny", "Manny UE5 [skeleton]"), ("Creep", "Creep [skeleton]")):
        entry = catalog.character_by_key(key)
        for answer in ((rm.KEEP, rm.SQUASH) if key == "Creep" else (None,)):
            cmds.file(new=True, force=True)
            ref = import_clip(HEAVY, "ref")                # the reference, kept
            first, last = clip_range(ref)
            cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
            samples = frames(first, last)
            namespace, info, source = rigimport.import_source(HEAVY, "Heavy", set_timeline=False)
            del ASKED[:]
            ANSWER[0] = answer or rm.KEEP
            line, failure, top = skeletonimport.onto_skeleton(entry, namespace, info, source, "Heavy",
                                                              None, decide=skeletonimport.choose_for)
            print("   ", (failure or line)[:260])
            roots = [j for j in cmds.ls(type="joint", long=True)
                     if not cmds.listRelatives(j, parent=True, type="joint") and not j.startswith("|ref:")
                     and leaf(j) == "root"]
            root = roots[0]
            m = skeletonimport.measure(ref, root, first, label)
            worst_pos, worst_rot, worst_dir, worst_len = compare(root, ref, samples, m.scale)
            tag = "c-%s-%s" % (key, answer or "auto")
            if answer is None:
                gate(tag + "1", not ASKED and "exact" in line and "twin, exact" in line,
                     "a twin: nothing asked, exact (%s)" % line.split("|")[-1].strip())
                gate(tag + "2", worst_pos[0] < 1e-3 and worst_rot[0] < 1e-3,
                     "every bone on the clip's: %.2e cm (%s), %.2e deg (%s)"
                     % (worst_pos + worst_rot))
            elif answer == rm.KEEP:
                gate(tag + "1", len(ASKED) == 1 and "keeps its proportions" in line,
                     "asked once, rotations: %s" % line.split("|")[-1].strip())
                gate(tag + "2", worst_len[0] < 1e-4 and worst_rot[0] < 0.01,
                     "lengths kept to %.2e cm (%s), orientations to %.5f deg (%s)"
                     % (worst_len + worst_rot))
            else:
                gate(tag + "1", len(ASKED) == 1 and "squashed & stretched" in line,
                     "asked once, stretch: %s" % line.split("|")[-1].strip())
                gate(tag + "2", worst_pos[0] < 1e-3 and worst_rot[0] < 1e-3,
                     "every bone on the clip's joint at x%.4f: %.2e cm (%s), %.2e deg (%s); lengths "
                     "moved up to %.2f cm" % ((m.scale,) + worst_pos + worst_rot + (worst_len[0],)))

# ------------------------------------------------------------------- e
MIXAMO = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"
if "e" in PHASES:
    print("--- phase e: a Mixamo clip onto Manny_Rig, both versions (another size, aligned rests)")
    if not os.path.isfile(MIXAMO):
        print("SKIP phase e: %s is not on this disk" % MIXAMO)
    else:
        for answer in (rm.KEEP, rm.SQUASH):
            cmds.file(new=True, force=True)
            rig = add("Manny_Rig")
            legacy = add("Manny_Rig") if answer == rm.KEEP else None
            src = import_clip(MIXAMO, "mx")
            first, last = clip_range(src)
            cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
            samples = frames(first, last, 5)
            m, _ = ar.measure(source_root=src, rig=rig)
            plan = ar._plan(src, rig)
            pairs = ar.pairs_of(plan.drives, plan.rig_bones)
            print("    measured: median %.3f, scaled %.3f, s %.4f, %s" % (m.median, m.scaled_median,
                                                                            m.scale, m.regions))
            del ASKED[:]
            ANSWER[0] = answer
            ok, text = rr.run_retarget(source_root=src, rig=rig)
            print("   ", text[:260])
            game = plan.rig_bones
            rest = bind_lengths(game)
            parent = (cmds.listRelatives(src, parent=True, fullPath=True) or [None])[0]
            # the stretch scales about the clip root's first-frame floor point (the fix pass)
            pivot_w = rm.floor_pivot(rm.root_start(src, first))
            blends = [maya_rigs.node(rig, "FKIK%s_%s.FKIKBlend" % (limb, side))
                      for limb in ("Arm", "Leg") for side in ("L", "R")]
            for b in [b for b in blends if cmds.objExists(b)]:
                cmds.setAttr(b, 0)
            worst_pos, worst_len = (0.0, ""), (0.0, "")
            for f in samples:
                cmds.currentTime(f, update=True)
                pm_ = om.MMatrix(cmds.xform(parent, q=True, ws=True, m=True)) if parent else om.MMatrix()
                for n, l in lengths_now(game).items():
                    if n in rest and n not in ("pelvis",) and "twist" not in n and not n.startswith(SKIP_POS):
                        d = abs(l - rest[n])
                        if d > worst_len[0]:
                            worst_len = (d, "%s@%g" % (n, f))
                for ours, theirs in pairs.items():
                    if ours in ("root",) or ours.startswith(SKIP_POS) or theirs not in plan.bones:
                        continue
                    p = om.MPoint(pos(plan.bones[theirs])) * pm_.inverse()
                    c = om.MPoint(*pivot_w) * pm_.inverse()
                    expected = om.MPoint(c.x + (p.x - c.x) * m.scale, c.y + (p.y - c.y) * m.scale,
                                         c.z + (p.z - c.z) * m.scale) * pm_
                    dd = (om.MVector(pos(game[ours])) - om.MVector(expected)).length()
                    if dd > worst_pos[0]:
                        worst_pos = (dd, "%s@%g" % (ours, f))
            tag = "e-%s" % ("keep" if answer == rm.KEEP else "squash")
            if answer == rm.KEEP:
                # the legacy road kept (the fix pass): Rotations on a rig without the rotation
                # mark IS the legacy plan for a foreign clip - FK by angle, the IK ends on the
                # clip's hands and feet. A second Manny retargeted by the legacy call must stand
                # where the first does, bone for bone, with the limbs in FK and in IK
                cmds.currentTime(first, update=True)
                ar.reset_build_pose(legacy)
                print("   ", ar.connect(source_root=src, rig=legacy).splitlines()[0][:160])
                print("   ", rr.bake(rig=legacy)[:120])
                a, b = by_leaf(rig.skeleton_root), by_leaf(legacy.skeleton_root)
                lblends = [maya_rigs.node(legacy, "FKIK%s_%s.FKIKBlend" % (limb, side))
                           for limb in ("Arm", "Leg") for side in ("L", "R")]
                same = (0.0, "")
                for value in (0, 10):
                    for blend in [x for x in blends + lblends if cmds.objExists(x)]:
                        cmds.setAttr(blend, value)
                    for f in samples:
                        cmds.currentTime(f, update=True)
                        for n in a:
                            if n in b:
                                dd = (pos(a[n]) - pos(b[n])).length()
                                if dd > same[0]:
                                    same = (dd, "%s@%g blend %d" % (n, f, value))
                for blend in [x for x in blends + lblends if cmds.objExists(x)]:
                    cmds.setAttr(blend, 0)
                gate(tag + "-legacy", same[0] < 1e-5 and "ROTATIONS (every bone its own length" in text,
                     "Rotations on Manny IS the legacy plan for a Mixamo clip: against a Manny retargeted "
                     "by the legacy call, worst %.2e cm (%s), limbs in FK and in IK; the line says so"
                     % same)
                # Manny's game bones follow AS by the vendor's -mo point constraints, and its
                # left leg's fit stands 0.0637 cm off calf_l (CLAUDE.md, the twin work): that
                # offset wanders with the knee's roll, so 0.1 cm is this rig's own floor
                gate(tag, ok and len(ASKED) == 1 and worst_len[0] < 0.1,
                     "a Mixamo clip (median %.2f off, x%.3f) asked once; rotations: lengths kept to "
                     "%.2e cm (%s)" % (m.median, m.scale, worst_len[0], worst_len[1]))
            else:
                gate(tag, ok and len(ASKED) == 1 and worst_pos[0] < 0.1,
                     "squash & stretch, limbs in FK: every paired bone on the clip's joint at x%.4f to "
                     "%.4f cm (%s); lengths moved up to %.2f cm"
                     % (m.scale, worst_pos[0], worst_pos[1], worst_len[0]))

# ------------------------------------------------------------------- d
LUGAL = "C:/Users/MY PC/Documents/maya/projects/default/scenes/Lugal_Rig_01_left_arm_fixed_20260906_0058.mb"
if "d" in PHASES:
    print("--- phase d: the PlayerMale (Lugal) rig, opened read-only from the animator's backup")
    import maya_pmretarget as pm
    if not os.path.isfile(LUGAL):
        print("SKIP phase d: %s is not on this disk" % LUGAL)
    else:
        for answer in (rm.KEEP, rm.SQUASH):
            cmds.file(LUGAL, open=True, force=True, executeScriptNodes=False, prompt=False)
            rigs = maya_rigs.rigs()
            rig = rigs[0] if len(rigs) == 1 else None
            if rig is None:
                gate("d0", False, "one rig in the Lugal scene: %s" % [r.namespace for r in rigs])
                break
            mod, refusal = rr.rig_module(rig)
            src = import_clip(HEAVY, "clip")
            first, last = clip_range(src)
            cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
            samples = frames(first, last, 5)
            plan = pm._plan(src, rig)
            m, _ = pm.measure(source_root=src, rig=rig)
            print("    measured: median %.3f, scaled %.3f, s %.4f (travel %.4f), %s"
                  % (m.median, m.scaled_median, m.scale, plan.scale, m.regions))
            del ASKED[:]
            ANSWER[0] = answer
            ok, text = rr.run_retarget(source_root=src, rig=rig)
            print("   ", text[:260])
            game = by_leaf(rig.skeleton_root)
            fk = [d for d in plan.drives if d.kind == "fk"]
            rest = bind_lengths(game)
            pelvis_src = plan.bones.get(dict((pm.our_bone(d.control), d.source) for d in plan.drives
                                             if d.kind == "pelvis").get(pm.OUR_PELVIS, ""))
            worst_pos, worst_len = (0.0, ""), (0.0, "")
            # the FK product: the limbs shown in FK (the Lugal's legs default to IK)
            blends = [maya_rigs.node(rig, "FKIK%s_%s.FKIKBlend" % (limb, side))
                      for limb in ("Arm", "Leg") for side in ("L", "R")]
            for b in [b for b in blends if cmds.objExists(b)]:
                cmds.setAttr(b, 0)
            for f in samples:
                cmds.currentTime(f, update=True)
                now = lengths_now(game)
                for n, l in now.items():
                    if n in rest and n not in (pm.OUR_ROOT, pm.OUR_PELVIS):
                        d = abs(l - rest[n])
                        if d > worst_len[0]:
                            worst_len = (d, "%s@%g" % (n, f))
                for d in fk:
                    ours, theirs = pm.our_bone(d.control), plan.bones.get(d.source)
                    if ours in game and theirs and pelvis_src:
                        # the body: the clip's shape about its pelvis at our size (the PlayerMale's
                        # FK hangs off its scaled pelvis, rest offset and all - the fix pass)
                        dd = ((pos(game[ours]) - pos(game[pm.OUR_PELVIS]))
                              - (pos(theirs) - pos(pelvis_src)) * plan.scale).length()
                        if dd > worst_pos[0]:
                            worst_pos = (dd, "%s@%g" % (ours, f))
            tag = "d-%s" % ("keep" if answer == rm.KEEP else "squash")
            if answer == rm.KEEP:
                gate(tag, ok and len(ASKED) == 1 and module_name(mod) == "maya_pmretarget"
                     and worst_len[0] < 1e-3,
                     "asked once (%d), rotations: the game bones' lengths kept to %.2e units (%s)"
                     % (len(ASKED), worst_len[0], worst_len[1]))
            else:
                gate(tag, ok and len(ASKED) == 1 and "SQUASH" in text.upper() and worst_pos[0] < 0.01,
                     "asked once, stretch: every FK-driven game bone about the game pelvis is the clip's "
                     "shape about its pelvis at x%.4f to %.4f units (%s); lengths moved up to %.3f units"
                     % (plan.scale, worst_pos[0], worst_pos[1], worst_len[0]))

        # the PlayerMale's stretch in ONE frame (the fix pass): the clip wrapped, connected,
        # then moved and turned as the bridge moves it - the body must stay the clip's scaled
        # shape about its pelvis (FK riding a rigid copy of the clip's top node while Main and
        # the pelvis rode the scaled group tore it by (1 - s) of the move)
        cmds.file(LUGAL, open=True, force=True, executeScriptNodes=False, prompt=False)
        rig = maya_rigs.rigs()[0]
        src = import_clip(HEAVY, "clip")
        first, last = clip_range(src)
        cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
        wrap = cmds.group(empty=True, name="verifyWrap")
        src = cmds.parent(src, wrap)[0]
        src = cmds.ls(src, long=True)[0]
        cmds.currentTime(first, update=True)
        pm.reset_build_pose(rig)
        plan = pm._plan(src, rig)          # before the connect: its rests are the build pose's
        print("   ", pm.connect(source_root=src, rig=rig, bones=rm.STRETCH).splitlines()[0][:200])
        cmds.setAttr(wrap + ".translate", 30.0, 0.0, 20.0)
        cmds.setAttr(wrap + ".rotate", 0.0, 25.0, 0.0)
        # the limbs shown in FK, as d-squash measures them (the Lugal's legs default to IK, and an
        # IK leg reaches with the rig's own lengths - the stretch's stated limit, not the frame's)
        for blend in [maya_rigs.node(rig, "FKIK%s_%s.FKIKBlend" % (limb, side))
                      for limb in ("Arm", "Leg") for side in ("L", "R")]:
            if cmds.objExists(blend):
                cmds.setAttr(blend, 0)
        game = by_leaf(rig.skeleton_root)
        tear = (0.0, "")
        pelvis_src = plan.bones.get(dict((pm.our_bone(d.control), d.source) for d in plan.drives
                                         if d.kind == "pelvis").get(pm.OUR_PELVIS, ""), None)
        for f in frames(first, last, 5):
            cmds.currentTime(f, update=True)
            for d in plan.drives:
                if d.kind != "fk":
                    continue
                ours, theirs = pm.our_bone(d.control), plan.bones.get(d.source)
                if ours in game and theirs and pelvis_src and pm.OUR_PELVIS in game:
                    got = pos(game[ours]) - pos(game[pm.OUR_PELVIS])
                    want = (pos(theirs) - pos(pelvis_src)) * plan.scale
                    dd = (got - want).length()
                    if dd > tear[0]:
                        tear = (dd, "%s@%g" % (ours, f))
        pm.disconnect(rig=rig)
        gate("d-frame", tear[0] < 0.01,
             "the clip moved 36 units and turned 25 deg after the connect: every FK-driven game bone "
             "about the game pelvis is the clip's shape about its pelvis at x%.4f to %.4f units (%s)"
             % (plan.scale, tear[0], tear[1]))

# ------------------------------------------------------------------- f
if "f" in PHASES:
    print("--- phase f: a batch of three onto Creep skeletons asks once")
    cmds.file(new=True, force=True)
    Rec = __import__("collections").namedtuple("Rec", "name package fps")
    records = [Rec("Heavy", HEAVY, 30), Rec("Thrust", THRUST, 30), Rec("Walk", WALK, 30)]
    creep = catalog.character_by_key("Creep")
    saved = skeletonimport.skeleton_entry
    skeletonimport.skeleton_entry = lambda: creep
    del ASKED[:]
    ANSWER[0] = rm.KEEP
    try:
        text = lineimport.run(records, lambda r: (r.package, None), "skeleton", set_timeline=True)
    finally:
        skeletonimport.skeleton_entry = saved
    print("   ", text[:300])
    roots = [j for j in cmds.ls(type="joint", long=True)
             if not cmds.listRelatives(j, parent=True, type="joint") and leaf(j) == "root"]
    worst = (0.0, "")
    for root in roots:
        paths = by_leaf(root)
        rest = bind_lengths(paths)
        for f in frames(cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)):
            cmds.currentTime(f, update=True)
            for n, l in lengths_now(paths).items():
                if n in rest and "twist" not in n and n != "pelvis" and not n.startswith(SKIP_POS):
                    d = abs(l - rest[n])
                    if d > worst[0]:
                        worst = (d, "%s %s@%g" % (root, n, f))
    gate("f1", len(ASKED) == 1 and "all 3 animations" in ASKED[0] and len(roots) == 3,
         "%d question(s) for 3 clips (%s), %d skeletons" % (len(ASKED), ASKED[0].splitlines()[0] if ASKED else "", len(roots)))
    gate("f2", worst[0] < 1e-4 and "keeps its proportions" in text,
         "Keep for the batch: every skeleton's lengths kept to %.2e cm (%s); the line says it" % worst)

# ------------------------------------------------------------------- g
if "g" in PHASES:
    print("--- phase g: Cancel leaves the scene as it was")
    cmds.file(new=True, force=True)
    creep = add("Creep_Rig")
    src = import_clip(HEAVY, "clip")
    first, last = clip_range(src)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    ANSWER[0] = rm.KEEP
    rr.run_retarget(source_root=src, rig=creep)              # a take on the rig
    curves = sorted(cmds.ls(cmds.listConnections(cmds.sets(creep.control_set, q=True), type="animCurve") or [], uuid=True))
    keys = cmds.keyframe(cmds.sets(creep.control_set, q=True), q=True, valueChange=True) or []
    before = snapshot()
    del ASKED[:]
    ANSWER[0] = rm.CANCEL
    ok, text = rr.run_retarget(source_root=src, rig=creep)
    curves2 = sorted(cmds.ls(cmds.listConnections(cmds.sets(creep.control_set, q=True), type="animCurve") or [], uuid=True))
    keys2 = cmds.keyframe(cmds.sets(creep.control_set, q=True), q=True, valueChange=True) or []
    gate("g1", not ok and rr.CANCELLED in text and len(ASKED) == 1 and curves == curves2 and keys == keys2
         and not leftovers(before) and not (snapshot() ^ before),
         "the Retarget button: Cancel -> %r, the rig's %d curves and %d keys as they were, nodes %+d"
         % (text, len(curves), len(keys), len(snapshot()) - len(before)))
    # a bridge import onto a NEW Creep rig, cancelled - in a film scene with keys of its own
    keys_loc = time_setup()
    saved_entry = rigimport.new_rig_entry
    rigimport.new_rig_entry = lambda: catalog.character_by_key("Creep_Rig")
    namespaces = set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
    before = snapshot()
    del ASKED[:]
    try:
        text = rigimport.import_and_retarget(HEAVY, "Heavy", set_timeline=False, target="new_rig")
    finally:
        rigimport.new_rig_entry = saved_entry
    left = leftovers(before)
    timing = time_now(keys_loc)
    gate("g2", text == rigimport.CANCELLED and len(ASKED) == 1 and not left
         and set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or []) == namespaces
         and len(maya_rigs.rigs()) == 1 and timing == TIME_EXPECTED,
         "a bridge import onto a new Creep: %r, %d node(s) left %s, rigs %d, namespaces as they were; "
         "the time as it was: %s (unit, the scene's own keys, ranges, frame)"
         % (text, len(left), left[:5], len(maya_rigs.rigs()), timing))
    # a batch onto new rigs, cancelled
    Rec = __import__("collections").namedtuple("Rec", "name package fps")
    rigimport.new_rig_entry = lambda: catalog.character_by_key("Creep_Rig")
    cmds.delete(keys_loc)
    keys_loc = time_setup()
    before = snapshot()
    del ASKED[:]
    try:
        text = lineimport.run([Rec("Heavy", HEAVY, 30), Rec("Thrust", THRUST, 30)],
                              lambda r: (r.package, None), "new_rig", set_timeline=False)
    finally:
        rigimport.new_rig_entry = saved_entry
    left = leftovers(before)
    timing = time_now(keys_loc)
    gate("g3", lineimport.CANCELLED in text and len(ASKED) == 1 and not left and len(maya_rigs.rigs()) == 1
         and set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or []) == namespaces
         and timing == TIME_EXPECTED,
         "a batch of two onto new Creeps: %r, one question, %d node(s) left %s; the time as it was: %s"
         % (text, len(left), left[:5], timing))

# ------------------------------------------------------------------- h
if "h" in PHASES:
    print("--- phase h: the scale pivot - a clip off the origin, a rig at a place")
    cmds.file(new=True, force=True)
    creep = add("Creep_Rig")
    src = import_clip(HEAVY, "clip")
    first, last = clip_range(src)
    cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
    moved = cmds.group(empty=True, name="verifyMoved")
    src = cmds.ls(cmds.parent(src, moved)[0], long=True)[0]      # parented at rest, THEN changed
    # the group stays at the origin, turned 30 and scaled 0.8 (the Creep's legs equal a UE clip's,
    # so at x1 no pivot could show); the ROOT starts away from it: its own keys moved (150, -80)
    cmds.setAttr(moved + ".rotate", 0.0, 30.0, 0.0)
    cmds.setAttr(moved + ".scale", 0.8, 0.8, 0.8)
    for attr, value in (("tx", 150.0), ("tz", -80.0)):
        if cmds.keyframe(src + "." + attr, q=True, keyframeCount=True):
            cmds.keyframe(src + "." + attr, edit=True, relative=True, valueChange=value)
        else:
            cmds.setAttr(src + "." + attr, cmds.getAttr(src + "." + attr) + value)
    start = cmds.getAttr(src + ".worldMatrix[0]", time=first)
    m, _ = ar.measure(source_root=src, rig=creep)
    del ASKED[:]
    ok, text = rr.run_retarget(source_root=src, rig=creep, bones=rm.STRETCH)
    print("   ", text[:220])
    cmds.currentTime(first, update=True)
    root = by_leaf(creep.skeleton_root)["root"]
    got = pos(root)
    off = math.hypot(got.x - start[12], got.z - start[14])
    origin = math.hypot(got.x - m.scale * start[12], got.z - m.scale * start[14])
    gate("h1", ok and not ASKED and off < 0.01,
         "a clip whose root starts at (%.1f, %.1f) away from its space's origin, stretched at x%.4f: "
         "the game root starts on it to %.4f cm (scaled about the space's origin it would stand %.2f cm "
         "away)"
         % (start[12], start[14], m.scale, off, origin))
    samples = frames(first, last)
    shape = (0.0, "")
    t, sp = by_leaf(creep.skeleton_root), by_leaf(src)
    for f in samples:
        cmds.currentTime(f, update=True)
        for a, b in [(a, b) for a, b in (("upperarm_l", "lowerarm_l"), ("lowerarm_r", "hand_r"),
                                         ("spine_01", "neck_01"), ("pelvis", "head"))
                     if a in t and b in t and a in sp and b in sp]:
            dd = abs((pos(t[b]) - pos(t[a])).length() - m.scale * (pos(sp[b]) - pos(sp[a])).length())
            if dd > shape[0]:
                shape = (dd, "%s-%s@%g" % (a, b, f))
    gate("h2", shape[0] < 0.05, "the body is the clip's at x%.4f, moved and turned: worst span off "
         "%.4f cm (%s)" % (m.scale, shape[0], shape[1]))
    # the bridge onto a Creep STANDING at a place, turned: the stretch keeps it there
    cmds.file(new=True, force=True)
    creep = add("Creep_Rig")
    cmds.xform(creep.main, worldSpace=True, translation=(120.0, 0.0, -60.0), rotation=(0, 30, 0))
    del ASKED[:]
    ANSWER[0] = rm.SQUASH
    text = rigimport.import_and_retarget(HEAVY, "Heavy", set_timeline=True, target="rig", rig=creep)
    print("   ", text[:220])
    first = cmds.playbackOptions(q=True, min=True)
    cmds.currentTime(first, update=True)
    main = cmds.xform(creep.main, q=True, ws=True, m=True)
    yaw = rigimport.facing(main)
    off = math.hypot(main[12] - 120.0, main[14] + 60.0)
    gate("h3", len(ASKED) == 1 and "squashed & stretched" in text and off < 0.05 and abs(yaw - 30.0) < 0.05,
         "Squash & stretch onto a Creep standing at (120, -60) turned 30: Main at the clip's first frame "
         "%.4f cm off the place, facing %.4f deg" % (off, yaw))
    # the Skeleton mode's drop point: the clip moved onto it BEFORE the transfer, so the
    # stretch must scale about where the root now starts
    cmds.file(new=True, force=True)
    namespace, info, source = rigimport.import_source(HEAVY, "Heavy", set_timeline=True)
    del ASKED[:]
    ANSWER[0] = rm.SQUASH
    line, failure, top = skeletonimport.onto_skeleton(catalog.character_by_key("Creep"), namespace, info,
                                                      source, "Heavy", (100.0, 0.0, -50.0),
                                                      decide=skeletonimport.choose_for)
    print("   ", (failure or line)[:220])
    root = [j for j in cmds.ls(type="joint", long=True)
            if not cmds.listRelatives(j, parent=True, type="joint") and leaf(j) == "root"][0]
    cmds.currentTime(info.get("start"), update=True)
    got = pos(root)
    off = math.hypot(got.x - 100.0, got.z + 50.0)
    gate("h4", not failure and len(ASKED) == 1 and "squashed & stretched" in line and off < 0.05,
         "Skeleton mode, a Creep skeleton dropped at (100, -50), stretched: its root starts %.4f cm off "
         "the point" % off)

rm.set_asker(None)
print("RESULT: %s" % ("ALL GATES PASSED" if not FAILS else "FAILED %s" % FAILS))

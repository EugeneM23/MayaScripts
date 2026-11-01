"""His torso across the whole spine, in both shipped assets, IN PLACE.

His file skins the torso to `pelvis` and `spine_05` alone -- 1.2 joints a vertex, a hard
switch in the middle of a 60 cm span, with spine_01..04 and the neck carrying no weight at
all. Under a clip that is a rigid slab hinged at one place: measured on
`am_Orc_Loco_Walk_Fwd_NoRM`, his torso's own centroid line folds 148 deg where Manny's bends
15. The animator saw it as a broken back.

Manny's own torso, measured: every vertex rides 2.5 joints, the weight's spread about its
centre 3.3 cm at the hips and 15-19 cm through the chest -- which is what a blend of constant
width in JOINT INDEX gives, since the chain's joints stand close at the hips and far apart in
the chest. So the fix takes the weight `pelvis` and `spine_05` hold, places each vertex along
the spine polyline, and lays that weight on the chain under a hat `SOFT` joints wide. Nothing
else of his skin is touched: every limb influence is left as his file has it, and the bind
cannot move (a skin at its own bind returns its rest points whatever its weights -- gated).

    mayapy make_swordman_spine_skin.py                 # both assets, in place
    mayapy make_swordman_spine_skin.py --out DIR       # beside them, for a proof run
    mayapy make_swordman_spine_skin.py --soft 2.0      # another blend width

Re-runnable: an asset already done carries `skeldarSpineSkin` on its skinCluster and is left
alone. The joints must stand at their bind when the influences are added -- `addInfluence`
takes a bindPreMatrix from the joint's world inverse AT THAT MOMENT -- so every skin is gated
at its bind before anything is written.
"""
import collections
import os
import re
import sys

import maya.standalone

maya.standalone.initialize()
import maya.cmds as cmds                                                    # noqa: E402
import maya.api.OpenMaya as om                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asset_dress as dress                                                 # noqa: E402

ASSETS = ["Swordman_Rig.ma", "Swordman_Skeleton.ma"]
CHAIN = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
         "neck_01", "neck_02", "head"]
SPREAD = ("pelvis", "spine_05")     # whose weight is laid along the chain
MARKER = "skeldarSpineSkin"         # the width it was done with, so a re-run is a no-op
SOFT = 1.5                          # the hat's half width, in chain joints
BIND_TOL = 1e-4                     # how far an influence may stand off its bind matrix
POINT_TOL = 1e-6                    # how far a vertex may move at the bind (cm): it must not


def chain_joints(root):
    js = [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or [])
    have = dict((p.split("|")[-1].split(":")[-1], p) for p in js)
    missing = [n for n in CHAIN if n not in have]
    if missing:
        raise RuntimeError("his skeleton has no %s" % ", ".join(missing))
    return dict((n, have[n]) for n in CHAIN)


def game_root():
    roots = [j for j in cmds.ls(type="joint", long=True)
             if j.split("|")[-1].split(":")[-1] == "root"
             and not cmds.listRelatives(j, parent=True, type="joint")]
    if len(roots) != 1:
        raise RuntimeError("expected one game skeleton, found %s" % roots)
    return roots[0]


def skins():
    out = []
    for shape in cmds.ls(type="mesh", noIntermediate=True, long=True):
        mesh = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        for sc in cmds.ls(cmds.listHistory(shape), type="skinCluster") or []:
            out.append((mesh, sc))
    return out


def at_bind(sc):
    """How far the skin stands off its own bind: every influence's BPM times its world."""
    worst = 0.0
    for i in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, i), s=True, d=False) or []
        if not src:
            continue
        m = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, i))) * \
            om.MMatrix(cmds.getAttr(cmds.ls(src[0], long=True)[0] + ".worldMatrix[0]"))
        worst = max(worst, max(abs(m.getElement(r, c) - (1.0 if r == c else 0.0))
                               for r in range(4) for c in range(4)))
    return worst


def points(mesh):
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True, noIntermediate=True)[0]
    sl = om.MSelectionList()
    sl.add(shape)
    return om.MFnMesh(sl.getDagPath(0)).getPoints(om.MSpace.kWorld)


def arc(places):
    out = [0.0]
    for i in range(1, len(places)):
        out.append(out[-1] + (places[i] - places[i - 1]).length())
    return out


def along(places, p):
    """Where `p` falls on the spine polyline: a float joint index."""
    best, best_t, best_d = 0, 0.0, 1e18
    for i in range(len(places) - 1):
        a, ab = places[i], places[i + 1] - places[i]
        length = ab * ab
        if length < 1e-9:
            continue
        s = max(0.0, min(1.0, ((p - a) * ab) / length))
        d = (p - (a + ab * s)).length()
        if d < best_d:
            best, best_t, best_d = i, s, d
    return best + best_t


def add_influences(sc, joints):
    """The chain joints the skin lacks, at weight 0. The asset must be at its bind."""
    have = set(i.split("|")[-1].split(":")[-1]
               for i in cmds.skinCluster(sc, q=True, influence=True))
    added = [n for n in CHAIN if n not in have]
    for n in added:
        cmds.skinCluster(sc, edit=True, addInfluence=joints[n], weight=0.0)
    return added


def lay_along_chain(sc, mesh, joints, soft):
    """Take what SPREAD holds and lay it on the chain, by each vertex's place along it."""
    infl = cmds.skinCluster(sc, q=True, influence=True)
    leaf = [i.split("|")[-1].split(":")[-1] for i in infl]
    index = dict((n, k) for k, n in enumerate(leaf))
    places = [om.MVector(cmds.xform(joints[n], q=True, ws=True, t=True)) for n in CHAIN]
    moved = set()
    for v in range(cmds.polyEvaluate(mesh, vertex=True)):
        plug = "%s.vtx[%d]" % (mesh, v)
        w = cmds.skinPercent(sc, plug, q=True, value=True)
        share = sum(w[index[n]] for n in SPREAD)
        if share < 1e-6:
            continue
        t = along(places, om.MVector(cmds.xform(plug, q=True, ws=True, t=True)))
        hat = [max(0.0, 1.0 - abs(i - t) / soft) for i in range(len(CHAIN))]
        total = sum(hat)
        if total < 1e-9:
            continue
        new = list(w)
        for n in SPREAD:
            new[index[n]] = 0.0
        for i, n in enumerate(CHAIN):
            if hat[i] > 0:
                new[index[n]] += share * hat[i] / total
        cmds.skinPercent(sc, plug, transformValue=[(infl[k], new[k])
                                                   for k in range(len(infl))])
        moved.add(v)
    return moved


def relink_images():
    """Opening a shipped textured asset resolves its relative image path against the .ma's
    own folder and stores it ABSOLUTE (trap 284). Every file node carrying `ASSET_IMAGE` is
    given its relative image back -- from the empty working folder it stays relative (trap
    119) -- its colour space kept."""
    from maya_scenesetup import colour
    for node in cmds.ls(type="file") or []:
        if not cmds.attributeQuery(colour.ASSET_IMAGE, node=node, exists=True):
            continue
        relative = cmds.getAttr(node + "." + colour.ASSET_IMAGE)
        space = cmds.getAttr(node + ".colorSpace")
        cmds.setAttr(node + ".fileTextureName", relative, type="string")
        cmds.setAttr(node + ".colorSpace", space, type="string")
        if cmds.getAttr(node + ".fileTextureName") != relative:
            raise RuntimeError("%s would not keep its relative image %r"
                               % (node, relative))


def report(sc, mesh, joints, only=None):
    """Manny's own measure: joints a vertex, and the weight's spread about its centre.
    `only`: the vertices to read (the laid ones -- the head's rigid verts ride the chain
    too, and their spread of 0 would be half the sample)."""
    infl = cmds.skinCluster(sc, q=True, influence=True)
    leaf = [i.split("|")[-1].split(":")[-1] for i in infl]
    names = [n for n in CHAIN if n in leaf]
    places = [om.MVector(cmds.xform(joints[n], q=True, ws=True, t=True)) for n in CHAIN]
    spots = arc(places)
    pos = dict((n, spots[CHAIN.index(n)]) for n in names)
    index = dict((n, leaf.index(n)) for n in names)
    sds, counts = [], []
    for v in (range(cmds.polyEvaluate(mesh, vertex=True)) if only is None
              else sorted(only)):
        w = cmds.skinPercent(sc, "%s.vtx[%d]" % (mesh, v), q=True, value=True)
        got = dict((n, w[index[n]]) for n in names)
        s = sum(got.values())
        if s < 0.6:
            continue
        mean = sum(got[n] * pos[n] for n in names) / s
        var = sum(got[n] * (pos[n] - mean) ** 2 for n in names) / s
        sds.append(var ** 0.5)
        counts.append(sum(1 for n in names if got[n] > 0.01))
    if not sds:
        return "no vertex rides the chain"
    sds.sort()
    return ("%d vertices ride the chain, %.1f joints each, spread median %.1f cm "
            "(Manny: 2.5 joints, 3.3 cm)"
            % (len(sds), sum(counts) / float(len(counts)), sds[len(sds) // 2]))


def explained(line, owner, skin_names, chain_leaves):
    """A body line a skin edit may change."""
    kind, name = owner or (None, None)
    if kind == "skinCluster":
        return True
    if kind == "joint" and name in chain_leaves:
        # Maya puts lockInfluenceWeights on a joint when it becomes an influence
        return bool(re.match(r'^\taddAttr .*"(liw|lockInfluenceWeights)"', line)
                    or re.match(r'^\tsetAttr "\.liw"', line))
    if line.startswith("connectAttr") and any(('"%s.' % n) in line for n in skin_names):
        return True
    if line.startswith("connectAttr") and "lockInfluenceWeights" in line:
        return True
    if kind == "select" and name in dress.SHADING_LISTS:
        return True
    if any(p.match(line) for p in dress.NOISE + dress.METADATA):
        return True
    if kind and any(kind.startswith(s) or name.startswith(s) for s in dress.SINGLETONS):
        return True
    return False


def unexplained(before_lines, after_lines, skin_names, chain_leaves):
    """The diff lines that are a real change. One line of text taken out and the same text
    put back is a MOVE, not a change -- which is all that happens to the connectAttr block
    when the new influences' connections are written into the middle of it. So the first
    min(removed, added) hits on one text are paired off as moves, and only the excess is a
    removal or an addition of its own."""
    owners_b, owners_a = dress.blocks(before_lines), dress.blocks(after_lines)
    rows = [(sign, i, hunk, (before_lines if sign == "-" else after_lines)[i])
            for sign, i, hunk in dress.diff_lines(before_lines, after_lines)]
    minus = collections.Counter(r[3] for r in rows if r[0] == "-")
    plus = collections.Counter(r[3] for r in rows if r[0] == "+")
    moves = dict((line, min(minus[line], plus[line])) for line in set(minus) | set(plus))
    seen = collections.Counter()
    out, hunks = [], {}
    for sign, i, hunk, line in rows:
        seen[(sign, line)] += 1
        if seen[(sign, line)] <= moves.get(line, 0):
            continue                                       # the same line, moved
        owner = (owners_b if sign == "-" else owners_a).get(i)
        hunks.setdefault(hunk, []).append((sign, line, owner))
    for _hunk, rows in sorted(hunks.items()):
        gone = " ".join(r[1].strip() for r in rows if r[0] == "-")
        came = " ".join(r[1].strip() for r in rows if r[0] == "+")
        if gone and came and dress.same_but_digits(gone, came):
            # the same text, numbers within the tolerance -- Maya's resave noise, whose
            # line WRAPPING may differ too (a double3 written on one line, not two)
            continue
        for sign, line, owner in rows:
            if not explained(line, owner, skin_names, chain_leaves):
                out.append("%s %-28s %s" % (sign, "/".join(owner or ("?", "?")),
                                            line.strip()[:110]))
    return out


def save(path, before_text, skin_names, chain_leaves, out_dir):
    name = os.path.basename(path)
    new = path[:-3] + ".new.ma"
    cmds.file(rename=new)
    cmds.file(save=True, type="mayaAscii", force=True)
    after_text = dress.text_without_scripts(new)
    with open(new, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(after_text))
    bad = [(n, w) for n, line in enumerate(after_text, 1) for w in dress.BANNED
           if w in line]
    if bad:
        raise RuntimeError("banned content in %s (left as %s): %s" % (name, new, bad[:10]))
    head_b, body_b = dress.split_header(before_text)
    head_a, body_a = dress.split_header(after_text)
    if head_b != head_a:
        raise RuntimeError("the header changed (left as %s)" % new)
    strange = unexplained(body_b, body_a, skin_names, chain_leaves)
    print("  the header is the same (%d lines); %d body lines differ that are not the skin"
          % (len(head_a), len(strange)))
    for s in strange[:40]:
        print("    " + s)
    if strange:
        raise RuntimeError("%s changed beyond its skin: %d lines (left as %s)"
                           % (name, len(strange), new))
    target = os.path.join(out_dir, name).replace("\\", "/") if out_dir else path
    os.replace(new, target)
    print("  saved %s (%.1f MB)" % (target, os.path.getsize(target) / 1e6))


def one(asset, out_dir, soft):
    path = os.path.join(dress.ASSETS, asset).replace("\\", "/")
    print("=== %s ===" % asset)
    before_text = dress.open_asset(path)
    relink_images()
    joints = chain_joints(game_root())
    todo = skins()
    print("  %d skinned mesh(es): %s" % (len(todo),
                                         ", ".join(m.split("|")[-1] for m, _ in todo)))
    done = [sc for _m, sc in todo if cmds.objExists(sc + "." + MARKER)]
    if done:
        print("  already laid along the chain (%s) -- left alone" % ", ".join(done))
        return
    for _mesh, sc in todo:
        off = at_bind(sc)
        if off > BIND_TOL:
            raise RuntimeError("%s is not at its bind (%.2e): an influence added now would "
                               "take the wrong bindPreMatrix" % (sc, off))
    print("  every skin at its bind, so the influences take their true bind matrices")
    for mesh, sc in todo:
        rest = points(mesh)
        leaf = mesh.split("|")[-1]
        print("  %s as his file has it: %s" % (leaf, report(sc, mesh, joints)))
        print("    added as influences: %s" % (add_influences(sc, joints) or "none"))
        moved = lay_along_chain(sc, mesh, joints, soft)
        print("    laid %d vertices along the chain, hat %.1f joints wide"
              % (len(moved), soft))
        print("  %s now: %s" % (leaf, report(sc, mesh, joints)))
        print("    the laid ones alone: %s" % report(sc, mesh, joints, only=moved))
        now = points(mesh)
        drift = max((om.MVector(rest[i] - now[i])).length() for i in range(len(rest)))
        print("    the bind pose moved %.2e cm (a skin at its bind returns its rest points)"
              % drift)
        if drift > POINT_TOL:
            raise RuntimeError("%s moved at its bind by %.3e cm" % (mesh, drift))
        off = at_bind(sc)
        if off > BIND_TOL:
            raise RuntimeError("%s left its bind (%.2e)" % (sc, off))
        cmds.addAttr(sc, longName=MARKER, dataType="string")
        cmds.setAttr(sc + "." + MARKER, "%.2f" % soft, type="string")
    save(path, before_text, [sc for _m, sc in todo], set(CHAIN), out_dir)


def main():
    args, out_dir = dress.out_dir_arg(sys.argv[1:])
    soft = SOFT
    if "--soft" in args:
        i = args.index("--soft")
        soft = float(args[i + 1])
        del args[i:i + 2]
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    if args:
        dress.begin()
        one(args[0], out_dir, soft)
    else:
        for asset in ASSETS:
            line = [sys.executable, os.path.abspath(__file__), asset,
                    "--soft", "%.2f" % soft]
            if out_dir:
                line += ["--out", out_dir]
            code = os.spawnv(os.P_WAIT, sys.executable, ['"%s"' % a for a in line])
            if code:
                raise SystemExit("%s failed (%d)" % (asset, code))


main()
maya.standalone.uninitialize()

"""Read an FBX with Maya and write what the slime sandbox needs from it.

    mayapy fbxread.py <in.fbx> <out.json> [--max-frames N] [--fps N]

The browser has no FBX reader, and writing one is weeks of work for a format
whose every exporter writes it differently. Maya reads FBX for a living and it
is on the machine this prototype is for, so the page hands the file to serve.py,
serve.py runs this, and the page loads a small JSON instead.

What comes out is only what the sandbox can use:

  bones    name, parent, and the capsule that stands for the bone
  frames   every bone's world position and rotation, one entry a frame
  meta     the frame range, the rate, and how it was scaled

The capsule radius is measured from the skin where there is one - the vertices
whose heaviest influence is that bone, taken at the 70th percentile of their
distance from the bone's axis, which is the shape of the limb rather than the
longest stray vertex - and guessed from the bone's own length where there is
not. That is the same reading the plugin's ragdoll makes, for the same reason:
a collider that is not the size of the limb is worse than none.

Units are centimetres, which is one cell of the sandbox's grid.
"""
import json
import os
import sys


def _mayapy():
    import maya.standalone
    maya.standalone.initialize(name='python')


def _import_fbx(path):
    import maya.cmds as cmds
    import maya.mel as mel
    if not cmds.pluginInfo('fbxmaya', q=True, loaded=True):
        cmds.loadPlugin('fbxmaya')
    # The import MODE is one global setting for the whole session and another
    # tool may have left it on exmerge, where the importer creates nothing at
    # all and reports success - the plugin's oldest trap. Set it, every time.
    mel.eval('FBXResetImport')
    mel.eval('FBXImportMode -v add')
    mel.eval('FBXImportFillTimeline -v true')
    mel.eval('FBXImportSetMayaFrameRate -v true')
    mel.eval('FBXImport -f "%s"' % path.replace('\\', '/'))


def _joints():
    import maya.cmds as cmds
    found = cmds.ls(type='joint', long=True) or []
    # Deepest paths last, so a parent is always written before its children and
    # the page can build the tree in one pass.
    found.sort(key=lambda p: (p.count('|'), p))
    return found


def _parent_of(path, index):
    import maya.cmds as cmds
    up = cmds.listRelatives(path, parent=True, fullPath=True)
    while up:
        if up[0] in index:
            return index[up[0]]
        up = cmds.listRelatives(up[0], parent=True, fullPath=True)
    return -1


def _skin_radii(joints, index):
    """The thickness of each bone, from the vertices it owns."""
    import maya.cmds as cmds
    from maya.api import OpenMaya as om
    radii = {}
    skins = cmds.ls(type='skinCluster') or []
    for skin in skins:
        shapes = cmds.skinCluster(skin, q=True, geometry=True) or []
        infl = cmds.skinCluster(skin, q=True, influence=True) or []
        infl_long = [cmds.ls(i, long=True)[0] for i in infl]
        for shape in shapes:
            try:
                sel = om.MSelectionList()
                sel.add(cmds.ls(shape, long=True)[0])
                mesh = om.MFnMesh(sel.getDagPath(0))
                pts = mesh.getPoints(om.MSpace.kWorld)
            except Exception:
                continue
            # One query for the whole mesh rather than one a vertex: the weights
            # come back flat, influence-major per vertex.
            try:
                weights = cmds.skinPercent(skin, shape + '.vtx[*]', q=True, value=True)
            except Exception:
                continue
            n = len(infl)
            if not n or len(weights) < n:
                continue
            for v in range(len(pts)):
                row = weights[v * n:(v + 1) * n]
                if not row:
                    break
                best = max(range(len(row)), key=lambda k: row[k])
                if row[best] < 0.2:
                    continue
                radii.setdefault(infl_long[best], []).append((v, pts[v]))
    return radii


def _capsule(path, child_pos, own_pos, owned, fallback):
    """A segment and a radius, in world centimetres."""
    import math
    a = own_pos
    b = child_pos if child_pos is not None else None
    if b is None:
        # A tip bone: a short stub along nothing in particular, so it is a ball.
        b = a
    ax = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(c * c for c in ax)) or 1.0
    unit = [c / length for c in ax]
    dists = []
    for _, p in owned:
        d = [p[i] - a[i] for i in range(3)]
        t = sum(d[i] * unit[i] for i in range(3))
        t = max(0.0, min(length, t))
        off = [d[i] - unit[i] * t for i in range(3)]
        dists.append(math.sqrt(sum(c * c for c in off)))
    if len(dists) >= 8:
        dists.sort()
        r = dists[int(len(dists) * 0.70)]
    else:
        r = fallback
    return max(0.5, min(r, 40.0))


# The spellings of a side this reader knows, left first.
SIDES = (('_l', '_r'), ('_left', '_right'), ('.l', '.r'), ('left', 'right'))


def _sided(name):
    low = name.lower()
    return any(low.endswith(a) or low.endswith(b) for a, b in SIDES)


def _body_widths(names, rest, parents, child_of):
    """How wide the body is at each midline bone, measured off the skeleton.

    An animation clip carries no skin, so there is nothing to measure a limb
    against and `_capsule` falls back to the bone's own length. For an arm that
    is about right; for a torso it is nonsense - a spine joint is 8 cm long and
    a chest is 30 cm across, and the slime pours straight through a stick.

    The skeleton does say how wide the body is, in the one place it is written
    down: how far out its own left and right limbs hang. A midline bone is as
    wide as the gap to the limbs that grow out of it - the pelvis to the hips,
    the chest to the clavicles - and a midline bone with no limbs of its own
    (the spine between them) is as wide as the one below it.

    Measured against the limb's MIDDLE rather than its root, so a chest comes
    out as wide as the shoulder is out, not as the clavicle's inner end.

    Two readings were tried before and are wrong, both for the same reason -
    they let a bone far from the body decide. Taking the nearest left/right
    PAIR by height made the pelvis 60 cm across, because at frame 0 of a walk
    the hands hang at hip height; taking the nearest sided bone in 3D made the
    chest 35 cm across, for the same hands. Only a limb the bone itself
    carries can say how wide the body is there.
    """
    import math

    def mid(k):
        kids = child_of.get(k, [])
        if not kids:
            return rest[k]
        tip = rest[kids[0]]
        return [(rest[k][c] + tip[c]) * 0.5 for c in range(3)]

    tall = max(r[1] for r in rest) - min(r[1] for r in rest)
    cap = max(8.0, 0.24 * tall) if tall > 1.0 else 80.0
    widths = {}
    for i, nm in enumerate(names):          # parents come first, so the
        if _sided(nm):                      # inherit below always has a value
            continue
        limbs = [k for k in child_of.get(i, []) if _sided(names[k])]
        if limbs:
            # Sideways only: a thigh's middle is 20 cm DOWN the leg, and its
            # distance in three dimensions says the hips are 40 cm across.
            out = max(math.hypot(rest[i][0] - q[0], rest[i][2] - q[2])
                      for q in (rest[limbs[0]], mid(limbs[0])))
            widths[i] = min(2.0 * out, cap)
        elif parents[i] >= 0 and parents[i] in widths:
            widths[i] = widths[parents[i]]
    return widths


def read(path, out, max_frames=600):
    import maya.cmds as cmds
    _import_fbx(path)
    joints = _joints()
    if not joints:
        raise SystemExit('no joints in %s' % path)
    index = {p: i for i, p in enumerate(joints)}
    parents = [_parent_of(p, index) for p in joints]
    names = [p.rsplit('|', 1)[-1].rsplit(':', 1)[-1] for p in joints]

    start = cmds.playbackOptions(q=True, min=True)
    end = cmds.playbackOptions(q=True, max=True)
    curves = cmds.ls(type='animCurve') or []
    if curves:
        times = cmds.keyframe(curves, q=True, timeChange=True) or []
        if times:
            start, end = min(times), max(times)
    start, end = int(round(start)), int(round(end))
    if end - start + 1 > max_frames:
        end = start + max_frames - 1
    fps = {'game': 15, 'film': 24, 'pal': 25, 'ntsc': 30, 'show': 48,
           'palf': 50, 'ntscf': 60}.get(cmds.currentUnit(q=True, time=True), 30)

    # The bind pose is where the skin is measured; the clip is sampled after.
    owned = _skin_radii(joints, index)
    cmds.currentTime(start)
    rest = [cmds.xform(p, q=True, ws=True, t=True) for p in joints]
    child_of = {}
    for i, par in enumerate(parents):
        if par >= 0:
            child_of.setdefault(par, []).append(i)

    import math
    cmds.currentTime(start)
    rest_m = [cmds.xform(p, q=True, ws=True, matrix=True) for p in joints]

    bones = []
    widths = _body_widths(names, rest, parents, child_of)
    for i, p in enumerate(joints):
        kids = child_of.get(i, [])
        tip = rest[kids[0]] if kids else None
        span = (math.sqrt(sum((tip[k] - rest[i][k]) ** 2 for k in range(3)))
                if tip else 0.0)
        mine = owned.get(p, [])
        par = parents[i]
        if tip is None:
            # A tip bone - a head, a toe, a fingertip - is a ball, and it is as
            # thick as the bone it hangs off. Half its parent's LENGTH, which
            # this used to be, made a toe an 8 cm ball on a 4 cm foot.
            fallback = max(2.0, bones[par]['radius']) if 0 <= par < len(bones) else 4.0
        elif _sided(names[i]):
            fallback = max(1.0, span * 0.22)
        else:
            # A midline bone - the pelvis, the spine, the neck. Its own length
            # says nothing about how thick the body is there (a spine joint is
            # 8 cm long and a chest is 30 cm across), so ask the one thing the
            # skeleton does record: how far apart the left and right bones are.
            wide = widths.get(i)
            fallback = max(1.0, wide * 0.55) if wide else max(1.0, span * 0.22)
        r = _capsule(p, tip, rest[i], mine, fallback)

        # The tip in the bone's OWN frame, so the page can rebuild the segment
        # from any frame's rotation without looking a child up.
        m = rest_m[i]
        d = [(tip or rest[i])[k] - rest[i][k] for k in range(3)]
        local = [d[0] * m[0] + d[1] * m[1] + d[2] * m[2],
                 d[0] * m[4] + d[1] * m[5] + d[2] * m[6],
                 d[0] * m[8] + d[1] * m[9] + d[2] * m[10]]
        bones.append({
            'name': names[i],
            'parent': parents[i],
            'radius': round(r, 3),
            'tip': [round(v, 3) for v in local],
            'len': round(span, 3),
        })

    # Which of them are worth colliding with. Every bone can hold an emitter -
    # a weapon bone or a fingertip is exactly where somebody wants slime to
    # come from - but a collider that is a 24 cm ball at the origin because an
    # export helper happens to have a distant child is worse than no collider,
    # and thirty of them would not fit in the uniform the solver reads.
    IGNORE = ('ik_', 'weapon', 'camera', 'interaction', 'center_of_mass',
              'attach', 'socket', 'root_motion', 'twist')
    want = []
    for i, b in enumerate(bones):
        low = b['name'].lower()
        if any(k in low for k in IGNORE):
            continue
        # A tip bone has no length and is a ball: a head counts, a fingertip
        # does not, and the radius is what tells them apart.
        if b['radius'] < 1.5 or (b['len'] < 3.0 and b['radius'] < 3.0):
            continue
        want.append((b['radius'] ** 2 * b['len'], i))
    want.sort(reverse=True)
    colliders = sorted(i for _, i in want[:24])

    frames = []
    for f in range(start, end + 1):
        cmds.currentTime(f)
        row = []
        for p in joints:
            t = cmds.xform(p, q=True, ws=True, t=True)
            m = cmds.xform(p, q=True, ws=True, matrix=True)
            row.append([round(t[0], 3), round(t[1], 3), round(t[2], 3),
                        round(m[0], 4), round(m[1], 4), round(m[2], 4),
                        round(m[4], 4), round(m[5], 4), round(m[6], 4),
                        round(m[8], 4), round(m[9], 4), round(m[10], 4)])
        frames.append(row)

    data = {
        'format': 'skeldar.slimerig/1',
        'source': os.path.basename(path),
        'fps': fps,
        'start': start,
        'end': end,
        'bones': bones,
        'colliders': colliders,
        # position (3) then the rotation's three columns (9), a bone a row
        'frames': frames,
    }
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)
    return data


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) < 2:
        raise SystemExit(__doc__)
    cap = 600
    for a in sys.argv[1:]:
        if a.startswith('--max-frames'):
            cap = int(a.split('=', 1)[1]) if '=' in a else cap
    _mayapy()
    data = read(args[0], args[1], cap)
    print('bones %d  frames %d  fps %d  -> %s'
          % (len(data['bones']), len(data['frames']), data['fps'], args[1]))


if __name__ == '__main__':
    main()

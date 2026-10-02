"""Two retargets, and which one runs: ROTATIONS (the bones never stretch) or
STRETCH (the bones take the clip's joint positions - squash & stretch).

2026-10-02, the animator: «у нас должно быть две версии ретаргета в первой
где мы делаем ретаргет но гарантируем что кости не растягиваются, то есть
переносим в основном вращения костей. Вторая версия где у нас учитывается
растяжение костей. Наш скрипт должен определить какую ретаргет систему стоит
использовать и если перенос анимации на риг или скелет будет ломать пропорции
то необходимо спросить у пользователя согласен ли он на сквош и стрейч
костей.»

What this module holds, and only this: the measurement of a clip's skeleton
against one of ours (bone lengths paired by the retarget's own map), the
decision, the question and its wording - pure, stdlib, testable without Maya -
plus a few thin scene wrappers that import `maya.cmds` lazily (the setting,
the dialog, reading lengths, the scaled followers a stretch drive rides). The
retarget modules (`maya_asretarget`, `maya_pmretarget`, the bridge's
`skeletonimport`) build their own drives; they ask this module what to build.

The rule (`decide`):
    the setting says Rotations or Stretch  -> that, never asked;
    Auto, the clip is our TWIN             -> stretch: exact, nothing to ask
                                              (a twin's bones ARE the clip's;
                                              the old twin path, unchanged);
    Auto, the same proportions at another
          size                             -> stretch, the clip taken at our size;
    Auto, anything else                    -> the stretch would break our
                                              proportions: ASK, defaulting to
                                              rotations; with no one to ask (a
                                              batch session) rotations, and the
                                              status line says why.

Twin = the MEDIAN relative difference of the paired bone lengths within 1 %
(the bridge's rule since 2026-10-01, trap 152: a 3P clip animates some of its
bones' lengths, so a share-within-1 % test read 0.90 against its own skeleton).
Lengths are measured between each paired bone and its nearest PAIRED ancestor,
on both skeletons - so a 3-joint Mixamo spine against our 5 compares like with
like - ours at the bind (the skinCluster's bindPreMatrix: a rig carrying a
stretched take still answers its own lengths), the clip's at its first frame.
The size: `s` = our legs over the clip's (the hip-to-ankle chains): a clip's
rest pose is never visible in an animated clip, its legs' lengths are.

Spec: docs/superpowers/specs/2026-10-02-retarget-stretch-design.md
"""

import collections
import math

AUTO, ROTATION, STRETCH = "auto", "rotation", "stretch"
SETTINGS = (AUTO, ROTATION, STRETCH)
LABELS = {AUTO: "Auto", ROTATION: "Rotations", STRETCH: "Stretch"}
OPTIONVAR = "skeldarRetargetBones"

TWIN_TOLERANCE = 0.01      # the median paired bone within 1 % makes a twin
SHORTEST = 1.0             # cm: shorter bones do not vote (the bridge's rule)
SHOWN_REGIONS = 3          # regions a status line names
SAMPLES = 24               # frames the clip's own stretch is sampled at

KEEP, SQUASH, CANCEL = "Keep proportions", "Squash & stretch", "Cancel"
BUTTONS = (KEEP, SQUASH, CANCEL)

# Bones that say nothing about a body's proportions: the root (its "length" is
# the root motion), the pelvis (its offset from the root is the hips' motion),
# and the export helpers, whose layout is each skeleton's own.
HELPER_PREFIXES = ("ik_", "weapon_", "camera_")
NOT_A_LENGTH = ("root", "pelvis", "center_of_mass", "interaction")

# Regions, by OUR bone's name, first match wins (fingers before arms: a
# "Hand" is an arm, a "HandIndex1" a finger). Lowercase substrings, so UE,
# PlayerMale (Right_ForeArm, Left_Thigh) and Mixamo (LeftUpLeg) names all land.
REGIONS = (
    ("fingers", ("thumb", "index", "middle", "ring", "pinky", "finger")),
    ("arms", ("clavicle", "scapula", "shoulder", "upperarm", "lowerarm", "forearm",
              "arm", "elbow", "wrist", "hand")),
    ("legs", ("thigh", "calf", "knee", "shin", "upleg", "leg", "foot", "ankle",
              "ball", "toe")),
    ("neck", ("neck", "head")),
    ("spine", ("spine", "chest", "hips", "pelvis")),
)
REGION_ORDER = ("arms", "legs", "spine", "neck", "fingers")

Measure = collections.namedtuple(
    "Measure", "source target twin median scaled_median scale regions "
               "stretch_bone stretch_cm count")
Measure.__new__.__defaults__ = ("", "", False, 1.0, 1.0, 1.0, (), "", 0.0, 0)
Decision = collections.namedtuple("Decision", "mode ask reason twin")
# twin -- what the MEASURE said (True / False), so the press that runs the version runs it
#         on the same verdict the status line reports; None when nothing was measured or the
#         verdict cannot matter (Rotations never take a twin's positions)
Decision.__new__.__defaults__ = (None,)


class Cancelled(Exception):
    """The animator answered Cancel: nothing is to change."""


# --------------------------------------------------------------------- pure

def leaf(path):
    """A DAG path's last name without its namespace."""
    return path.split("|")[-1].split(":")[-1]


def clip_name(path):
    """What a message calls a clip's skeleton: the namespace its root was
    imported into (the bridge names it after the animation), else the root's
    name. Pure."""
    node = path.split("|")[-1]
    return node.rsplit(":", 1)[0].split(":")[-1] if ":" in node else node


def excluded(name, extra=()):
    """Whether a bone's length says nothing about proportions. Pure."""
    low = name.lower()
    return (name in NOT_A_LENGTH or name in extra
            or any(low.startswith(p) for p in HELPER_PREFIXES))


def region_of(name):
    """"arms" / "legs" / "spine" / "neck" / "fingers" for one of OUR bones,
    or None. Pure."""
    low = name.lower()
    for region, words in REGIONS:
        if any(word in low for word in words):
            return region
    return None


def _components(path):
    return [part for part in path.split("|") if part]


def _is_ancestor(ancestor, path):
    """Path prefix with the separator (trap 7)."""
    return path.startswith(ancestor + "|")


def segments(pairs, target_paths, source_paths, extra=()):
    """[(target bone, its anchor, source bone, its anchor)]: each paired bone
    with its nearest PAIRED ancestor on our side, kept only when the source's
    counterpart of that anchor is an ancestor of the source's bone too - so the
    two lengths span the same stretch of body. Pure.

    pairs        {our bone: the clip's bone}
    target_paths {our bone: long path}
    source_paths {the clip's bone: long path}
    """
    by_path = dict((path, name) for name, path in target_paths.items())
    out = []
    for name in sorted(pairs):
        if excluded(name, extra) or name not in target_paths:
            continue
        source = pairs[name]
        if source not in source_paths:
            continue
        parts = _components(target_paths[name])
        anchor = None
        for i in range(len(parts) - 1, 0, -1):
            candidate = "|" + "|".join(parts[:i])
            up = by_path.get(candidate)
            if up is not None and up in pairs and pairs[up] in source_paths:
                anchor = up
                break
        if anchor is None:
            continue
        if not _is_ancestor(source_paths[pairs[anchor]], source_paths[source]):
            continue
        out.append((name, anchor, source, pairs[anchor]))
    return out


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def scale_of(rows):
    """Our size over the clip's: the summed leg lengths (hip to ankle, every
    row in the "legs" region), else every length. 1.0 with nothing to measure.
    Pure. `rows` are (our bone, the clip's length, our length)."""
    legs = [(s, t) for name, s, t in rows if region_of(name) == "legs"]
    use = legs if sum(s for s, _ in legs) > 1e-6 else [(s, t) for _, s, t in rows]
    src = sum(s for s, _ in use)
    tgt = sum(t for _, t in use)
    if src <= 1e-6 or tgt <= 1e-6:
        return 1.0
    return tgt / src


def median_difference(rows, scale=1.0, shortest=SHORTEST):
    """The median relative difference |s*clip - ours| / max over the rows whose
    longer side passes `shortest`, or None with nothing to vote. Pure."""
    diffs = sorted(abs(scale * s - t) / max(scale * s, t) for _, s, t in rows
                   if max(scale * s, t) > shortest)
    if not diffs:
        return None
    return diffs[len(diffs) // 2]


def region_changes(rows, scale):
    """[(region, percent)] in REGION_ORDER: how much the stretch would change
    OUR bones of that region - (sum of s*clip - sum of ours) / sum of ours.
    Pure."""
    sums = collections.OrderedDict()
    for name, s, t in rows:
        region = region_of(name)
        if region is None:
            continue
        acc = sums.setdefault(region, [0.0, 0.0])
        acc[0] += scale * s
        acc[1] += t
    out = []
    for region in REGION_ORDER:
        if region in sums and sums[region][1] > 1e-6:
            src, tgt = sums[region]
            out.append((region, 100.0 * (src - tgt) / tgt))
    return out


def measure(rows, stretch=None, source="", target="", tolerance=TWIN_TOLERANCE):
    """The Measure of a clip against one of ours. Pure.

    rows    [(our bone, the clip's length, our length)]
    stretch (the clip's bone, how far its own length varies over the take, cm)
            - the worst one, or None
    """
    rows = list(rows or [])
    scale = scale_of(rows)
    median = median_difference(rows, 1.0)
    scaled = median_difference(rows, scale)
    twin = median is not None and median <= tolerance
    bone, cm = (stretch or ("", 0.0))
    return Measure(source=source, target=target, twin=twin,
                   median=1.0 if median is None else median,
                   scaled_median=1.0 if scaled is None else scaled,
                   scale=scale, regions=tuple(region_changes(rows, scale)),
                   stretch_bone=bone, stretch_cm=cm * scale, count=len(rows))


def same_proportions(m, tolerance=TWIN_TOLERANCE):
    """Not a twin, but every bone in the same proportion at another size: the
    stretch takes the clip at our size and breaks nothing. Pure."""
    return (not m.twin and m.count > 0 and m.scaled_median <= tolerance)


def _percent(value):
    return "{0:+.0f} %".format(value).replace("+0 %", "0 %").replace("-0 %", "0 %")


def regions_text(m, limit=None, least=0.5):
    """«arms -21 %, legs 0 %, neck -28 %» - the regions in REGION_ORDER, or the
    `limit` largest. Pure."""
    regions = [(r, p) for r, p in m.regions if abs(p) >= least] or list(m.regions[:1])
    if limit is not None and len(regions) > limit:
        regions = sorted(regions, key=lambda rp: -abs(rp[1]))[:limit]
        regions.sort(key=lambda rp: REGION_ORDER.index(rp[0]))
    return ", ".join("{0} {1}".format(r, _percent(p)) for r, p in regions)


def stretch_text(m, least=0.05):
    """«the clip itself stretches neck_01 3.7 cm» or "". Pure."""
    if not m.stretch_bone or m.stretch_cm < least:
        return ""
    return "the clip itself stretches {0} {1:.1f} cm".format(m.stretch_bone, m.stretch_cm)


def question(m, others=0):
    """The dialog's message. Pure."""
    who = "{0} onto {1}".format(m.source or "the clip", m.target or "the character")
    lines = ["{0}: its bones are not {1}'s.".format(who, m.target or "ours"),
             "Squash & stretch would change {0}'s proportions: {1}.".format(
                 m.target or "the character", regions_text(m))]
    if abs(m.scale - 1.0) > 0.01:
        lines.append("The clip is taken at {0}'s size (x{1:.3g}).".format(
            m.target or "our", m.scale))
    extra = stretch_text(m)
    if extra:
        lines.append(extra[0].upper() + extra[1:] + ".")
    if others:
        lines.append("The answer goes for all {0} animations that differ (the "
                     "worst is named).".format(others + 1))
    lines.append("")
    lines.append("Keep proportions: the bones turn as the clip's and keep "
                 "their own lengths.")
    lines.append("Squash & stretch: every bone lands on the clip's joint, its "
                 "length the clip's - in FK and in IK alike.")
    return "\n".join(lines)


def keep_reason(m, why=""):
    """«rotations - Creep_Rig keeps its proportions (arms -21 %, neck -28 %)».
    Pure."""
    text = "rotations - {0} keeps its proportions ({1})".format(
        m.target or "the character", regions_text(m, SHOWN_REGIONS))
    return text + ("; " + why if why else "")


def stretch_reason(m):
    """«stretch - Creep_Rig squashed & stretched to the clip (arms -21 %)».
    Pure."""
    return "stretch - {0} squashed & stretched to the clip ({1})".format(
        m.target or "the character", regions_text(m, SHOWN_REGIONS))


def decide(setting, m, can_ask):
    """The Decision for one clip onto one of ours. Pure.

    setting  AUTO / ROTATION / STRETCH (anything else reads AUTO)
    m        the Measure, or None (nothing could be measured: the legacy
             retarget, mode None)
    can_ask  whether a dialog can stand
    """
    if setting == ROTATION:
        return Decision(ROTATION, False, "rotations - the Retarget card says Rotations")
    twin = None if m is None or not m.count else bool(m.twin)
    if setting == STRETCH:
        tail = ", exact (a twin)" if twin else ""
        return Decision(STRETCH, False, "stretch - the Retarget card says Stretch" + tail, twin)
    if twin is None:
        return Decision(None, False, "")
    if twin:
        return Decision(STRETCH, False, "stretch - {0} is the clip's twin, exact".format(
            m.target or "the character"), True)
    if same_proportions(m):
        return Decision(STRETCH, False,
                        "stretch - the clip has {0}'s proportions at x{1:.3g}".format(
                            m.target or "our", m.scale), False)
    if not can_ask:
        return Decision(ROTATION, False, keep_reason(m, "no one to ask here"), False)
    return Decision(ROTATION, True, keep_reason(m), False)


def answered(decision, button, m):
    """The Decision once the dialog answered `button`; None for Cancel. Pure."""
    twin = None if m is None else bool(m.twin)
    if button == SQUASH:
        return Decision(STRETCH, False, stretch_reason(m), twin)
    if button in (KEEP, None, ""):
        return Decision(ROTATION, False, keep_reason(m), twin)
    return None


def worst(measures):
    """The measure whose proportions would change most (the largest |region|).
    Pure."""
    measures = [m for m in measures if m is not None]
    if not measures:
        return None
    return max(measures, key=lambda m: max([abs(p) for _, p in m.regions] or [0.0]))


def decide_batch(setting, measures, can_ask):
    """(the Decisions, one per measure, and the measure to ASK about or None).
    Pure. One question for the whole batch: every clip that would ask shares
    the answer; a twin stays exact."""
    decisions = [decide(setting, m, can_ask) for m in measures]
    asking = [m for m, d in zip(measures, decisions) if d.ask]
    return decisions, (worst(asking) if asking else None), len(asking)


def apply_answer(decisions, measures, button):
    """The batch's Decisions after the one answer; None for Cancel. Pure."""
    out = []
    for d, m in zip(decisions, measures):
        if not d.ask:
            out.append(d)
            continue
        a = answered(d, button, m)
        if a is None:
            return None
        out.append(a)
    return out


def sample_frames(start, end, samples=SAMPLES):
    """Frames to sample a take at: the ends and evenly between. Pure."""
    if start is None or end is None:
        return []
    if end <= start:
        return [start]
    n = max(2, int(samples))
    return [start + (end - start) * i / float(n - 1) for i in range(n)]


def segment_lengths(segs, target_pos, source_pos):
    """[(our bone, the clip's length, our length)] from positions. Pure."""
    return [(t, distance(source_pos[s], source_pos[sa]), distance(target_pos[t], target_pos[ta]))
            for t, ta, s, sa in segs
            if t in target_pos and ta in target_pos and s in source_pos and sa in source_pos]


def worst_stretch(segs, frames_pos):
    """(the clip's bone, its length's range in cm) over `frames_pos` - a list of
    {bone: position} per sampled frame - the widest one, or None. Pure."""
    best = None
    for _t, _ta, s, sa in segs:
        lengths = [distance(f[s], f[sa]) for f in frames_pos if s in f and sa in f]
        if len(lengths) < 2:
            continue
        spread = max(lengths) - min(lengths)
        if best is None or spread > best[1]:
            best = (s, spread)
    return best


# ------------------------------------------------------------------- scene
#
# Thin, and `maya.cmds` only inside: importing this module stays stdlib.

_ASKER = None      # a verify run installs an answerer: fn(question) -> button


def set_asker(fn):
    """Install (or clear, with None) the answerer the dialog defers to."""
    global _ASKER
    _ASKER = fn


def setting():
    """The Retarget card's setting, AUTO when unset or unknown."""
    import maya.cmds as cmds
    try:
        if cmds.optionVar(exists=OPTIONVAR):
            value = cmds.optionVar(query=OPTIONVAR)
            if value in SETTINGS:
                return value
    except Exception:                                        # noqa: BLE001
        pass
    return AUTO


def set_setting(value):
    import maya.cmds as cmds
    if value not in SETTINGS:
        raise ValueError("unknown retarget setting %r" % (value,))
    cmds.optionVar(stringValue=(OPTIONVAR, value))
    return value


def can_ask():
    """A dialog can stand: an answerer is installed, or Maya has a UI."""
    if _ASKER is not None:
        return True
    try:
        import maya.cmds as cmds
        return not cmds.about(batch=True)
    except Exception:                                        # noqa: BLE001
        return False


def ask(text):
    """The animator's button: KEEP, SQUASH or CANCEL."""
    if _ASKER is not None:
        return _ASKER(text)
    import maya.cmds as cmds
    return cmds.confirmDialog(title="Retarget: squash & stretch?", message=text,
                              button=list(BUTTONS), defaultButton=KEEP,
                              cancelButton=CANCEL, dismissString=CANCEL)


def choose(m, setting_=None):
    """The Decision for one clip, asking when the rule says so; raises
    Cancelled for Cancel."""
    d = decide(setting() if setting_ is None else setting_, m, can_ask())
    if not d.ask:
        return d
    a = answered(d, ask(question(m)), m)
    if a is None:
        raise Cancelled(m.source)
    return a


def choose_batch(measures, setting_=None):
    """The Decisions for several clips, asking ONCE (the worst named); raises
    Cancelled for Cancel."""
    decisions, worst_m, asking = decide_batch(
        setting() if setting_ is None else setting_, measures, can_ask())
    if worst_m is None:
        return decisions
    out = apply_answer(decisions, measures, ask(question(worst_m, asking - 1)))
    if out is None:
        raise Cancelled(worst_m.source)
    return out


def rest_world(joint):
    """The joint's world matrix at its BIND: the inverse of a skinCluster's
    bindPreMatrix for it (a rig carrying a stretched take still answers its own
    lengths; the joints' own `.bindPose` attribute was measured 3.5 cm stale on
    Manny_Rig), else its world matrix now."""
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    for plug in cmds.listConnections(joint + ".worldMatrix[0]", source=False,
                                     destination=True, plugs=True,
                                     type="skinCluster") or []:
        node, attr = plug.split(".", 1)
        if not attr.startswith("matrix["):
            continue
        index = attr[len("matrix["):].split("]")[0]
        bpm = cmds.getAttr("{0}.bindPreMatrix[{1}]".format(node, index))
        if bpm:
            return list(om.MMatrix(bpm).inverse())
    return cmds.getAttr(joint + ".worldMatrix[0]")


def _position(matrix):
    return (matrix[12], matrix[13], matrix[14])


def measure_scene(pairs, target_paths, source_paths, start=None, end=None,
                  source="", target="", extra=()):
    """The Measure of a clip's skeleton (`source_paths`, keyed at start..end)
    against one of ours (`target_paths`), paired by `pairs` {ours: theirs}."""
    import maya.cmds as cmds
    segs = segments(pairs, target_paths, source_paths, extra)
    if not segs:
        return measure([], None, source, target)
    ours = set(t for t, _a, _s, _sa in segs) | set(a for _t, a, _s, _sa in segs)
    theirs = set(s for _t, _a, s, _sa in segs) | set(sa for _t, _a, _s, sa in segs)
    target_pos = dict((n, _position(rest_world(target_paths[n]))) for n in ours)
    frames = sample_frames(start, end)

    def at(frame):
        if frame is None:
            return dict((n, _position(cmds.getAttr(source_paths[n] + ".worldMatrix[0]")))
                        for n in theirs)
        return dict((n, _position(cmds.getAttr(source_paths[n] + ".worldMatrix[0]",
                                               time=frame))) for n in theirs)
    first = at(frames[0] if frames else None)
    rows = segment_lengths(segs, target_pos, first)
    spread = worst_stretch(segs, [first] + [at(f) for f in frames[1:]])
    return measure(rows, spread, source, target)


def key_span(paths):
    """(first, last) key over the paths, or (None, None)."""
    import maya.cmds as cmds
    paths = list(paths or [])
    if not paths or not (cmds.keyframe(paths, query=True, keyframeCount=True) or 0):
        return None, None
    return (cmds.findKeyframe(paths, which="first"),
            cmds.findKeyframe(paths, which="last"))


# The scaled followers a stretch drive rides. A follower stands where the
# clip's joint stands, at OUR size: its position the joint's position in the
# clip's top space times `s`, its rotation the joint's world rotation, its
# scale 1. "The clip's top space" is the root's parent (the bridge's wrapper,
# moved and turned onto the rig's place AFTER the connect - so the move is
# carried 1:1 and only the body is scaled), or the world when there is none.
#
#   space   (under `parent`) rides the root's parent, rigidly (-mo: its pivot
#           does not matter)
#   follow  (under space) point + orient constrained to the joint: its channels
#           ARE the joint in the space
#   scaled  (under space, scale s) -> body (translate/rotate connected from
#           follow) -> unit (scale 1/s): the follower
#
# Transforms and plain connections only, so everything dies with `parent`.
#
# The scale is taken about the clip root's FIRST-FRAME FLOOR POINT (its x and z
# at the clip's first key, y 0), not the space's origin: every place the
# bridge computes (`rigimport.place_moves`, the drop point, a skeleton's own
# place) is measured from the UNSCALED root at its first frame, so a body
# scaled about the origin stood (1 - s) times the root's start away from it -
# the fix pass of 2026-10-02 (a clip whose root starts at x = 150 put a Creep's
# Main 25 cm short). About that point the scaled root starts exactly where the
# clip's does, and a wrapper turned about the root's start turns it in place.

def floor_pivot(point):
    """(x, 0, z): the floor point under `point`. Pure."""
    return (float(point[0]), 0.0, float(point[2]))


def to_local(point, matrix):
    """`point` (world) in the space whose world matrix is `matrix` (16 floats, row
    vectors). Arithmetic only (OpenMaya, no scene)."""
    import maya.api.OpenMaya as om
    p = om.MPoint(point[0], point[1], point[2]) * om.MMatrix(matrix).inverse()
    return (p.x, p.y, p.z)


def root_start(source_root, start=None):
    """The clip root's world position at the clip's first frame: `start`, else its
    joints' first key, else where it stands now."""
    import maya.cmds as cmds
    if start is None:
        joints = [source_root] + (cmds.listRelatives(source_root, allDescendents=True,
                                                     type="joint", fullPath=True) or [])
        start = key_span(joints)[0]
    if start is None:
        m = cmds.getAttr(source_root + ".worldMatrix[0]")
    else:
        m = cmds.getAttr(source_root + ".worldMatrix[0]", time=start)
    return (m[12], m[13], m[14])


def scale_space(source_root, factor, parent, name, start=None):
    """The space node and its scaled group, under `parent` (None: world), the
    scale taken about the clip root's first-frame floor point (above).
    Returns (space, scaled_group, made constraints)."""
    import maya.cmds as cmds
    kwargs = dict(skipSelect=True)
    if parent:
        kwargs["parent"] = parent
    space = cmds.createNode("transform", name=name + "Space", **kwargs)
    made = []
    up = cmds.listRelatives(source_root, parent=True, fullPath=True)
    if up:
        cmds.xform(space, worldSpace=True,
                   matrix=cmds.xform(up[0], query=True, worldSpace=True, matrix=True))
        made.append(cmds.parentConstraint(up[0], space, maintainOffset=True)[0])
    scaled = cmds.createNode("transform", name=name + "Scaled", parent=space, skipSelect=True)
    pivot = to_local(floor_pivot(root_start(source_root, start)),
                     cmds.xform(space, query=True, worldSpace=True, matrix=True))
    cmds.setAttr(scaled + ".scalePivot", *pivot)
    cmds.setAttr(scaled + ".scale", factor, factor, factor)
    return space, scaled, made


def scaled_follower(joint, space, scaled, factor, name):
    """A transform at the joint scaled by `factor` in the space (see above).
    Returns (follower, made constraints)."""
    import maya.cmds as cmds
    follow = cmds.createNode("transform", name=name + "Follow", parent=space, skipSelect=True)
    made = [cmds.pointConstraint(joint, follow)[0], cmds.orientConstraint(joint, follow)[0]]
    body = cmds.createNode("transform", name=name + "Body", parent=scaled, skipSelect=True)
    cmds.connectAttr(follow + ".translate", body + ".translate")
    cmds.connectAttr(follow + ".rotate", body + ".rotate")
    unit = cmds.createNode("transform", name=name, parent=body, skipSelect=True)
    # scale 1 in WORLD: the body carries `factor` AND whatever scale the clip's top node
    # has (a scaled wrapper is copied into the space at creation, and a parentConstraint
    # never drives scale, so it stays what it was) - a follower left at that scale would
    # scale the rest offsets the constraints on it carry
    world = cmds.xform(body, query=True, worldSpace=True, matrix=True)
    size = math.sqrt(world[0] ** 2 + world[1] ** 2 + world[2] ** 2)
    inverse = 1.0 / size if size > 1e-9 else 1.0
    cmds.setAttr(unit + ".scale", inverse, inverse, inverse)
    return unit, made

"""Auto rig for a bone array: group controls OVER the bones' own
animation, nothing baked onto the controls.

Test-mode tool, deliberately minimal (the project's spec/TDD pipeline is
skipped on purpose). The workflow it serves: the bones are animated by
scripts or simulation first; then Create Rig is pressed ONCE, reading
everything - group pivots, control orientation - from the CURRENT frame
on the timeline; then the animator layers secondary animation onto the
group controls, on top of the animation that stays on the bones.

The construction is pure DAG, no constraints and no baking:

- every control (knot) is a static circle; under it sits a hidden
  "space" transform whose world matrix equals the ROOT's world matrix,
  and the group's bones are parented into that space with their local
  values kept (relative) - the parent's world is the same as before, so
  the bones' own curves keep playing UNCHANGED while the knot turns the
  whole group around its pivot on top;
- the main knot stands on the root's current pose the same way: its
  space matches the root's old parent, the root moves in with its
  curves intact - so the root's own animation still carries everything,
  and the main knot is the whole-object secondary control;
- group knots are children of the ROOT, so they ride the root's
  animation, and their bones ride them;
- groups come from the learned groups file (position match in the
  root's local space), else from k-means clustering (Groups field);
  bones in the ArrowBones display layer get their own assembly instead:
  Parent -> root -> ArrowMiddle_knot -> ArrowHead/ArrowEnd knots on the
  two ends of the arrow's bone cloud, the layer bones split between
  them at the midpoint.

Bake to Bones is the way OUT to a clean skeleton: the combined result
(bone animation plus whatever was animated on the knots) is captured in
world space, the bones return under the root, the keys are written back
onto them and the rig is deleted whole.

Run:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_geobonesrig; maya_geobonesrig.show()
"""

import json
import math
import os

import maya.cmds as cmds

WINDOW = "geoBonesRigWindow"
RIG_SET = "GeoAutoRig_set"
ARROW_LAYER = "ArrowBones"
GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "geobones_groups.json")
CHANNELS = ["translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ"]
BAKE_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz"]
IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

_kfield = None
_status = None


# ---------------------------------------------------------------- pure logic

def cluster_bones(positions, k):
    """Deterministic k-means over (x, y, z) positions: seeds by
    farthest-point sampling, then Lloyd iterations to convergence.
    Returns (assignment index per position, centers)."""
    n = len(positions)
    k = max(1, min(int(k), n))

    def d2(a, b):
        return sum((a[i] - b[i]) ** 2 for i in range(3))

    centroid = [sum(p[i] for p in positions) / n for i in range(3)]
    seeds = [max(range(n), key=lambda i: d2(positions[i], centroid))]
    while len(seeds) < k:
        seeds.append(max(range(n),
                         key=lambda i: min(d2(positions[i], positions[s])
                                           for s in seeds)))
    centers = [list(positions[s]) for s in seeds]
    assign = [0] * n
    for _round in range(50):
        changed = False
        for i, p in enumerate(positions):
            best = min(range(k), key=lambda c: d2(p, centers[c]))
            if best != assign[i]:
                assign[i] = best
                changed = True
        for c in range(k):
            members = [positions[i] for i in range(n) if assign[i] == c]
            if members:
                centers[c] = [sum(m[i] for m in members) / len(members)
                              for i in range(3)]
        if not changed:
            break
    return assign, centers


def box_fit(points, src_lo, src_hi, dst_lo, dst_hi):
    """Map points from one bounding box into another, axis by axis. A
    degenerate axis reads as the middle."""
    out = []
    for p in points:
        q = []
        for i in range(3):
            size = src_hi[i] - src_lo[i]
            f = (p[i] - src_lo[i]) / size if size > 1e-9 else 0.5
            q.append(dst_lo[i] + f * (dst_hi[i] - dst_lo[i]))
        out.append(q)
    return out


def _apply_matrix(points, m):
    """Row-vector points through a 16-float Maya matrix."""
    out = []
    for p in points:
        out.append([p[0] * m[0] + p[1] * m[4] + p[2] * m[8] + m[12],
                    p[0] * m[1] + p[1] * m[5] + p[2] * m[9] + m[13],
                    p[0] * m[2] + p[1] * m[6] + p[2] * m[10] + m[14]])
    return out


def knot_radius(pivot, member_positions):
    """A knot big enough to grab: a share of the group's spread around
    its pivot, never smaller than a hand-sized ring."""
    reach = 0.0
    for p in member_positions:
        d = math.sqrt(sum((p[a] - pivot[a]) ** 2 for a in range(3)))
        reach = max(reach, d)
    return max(6.0, 0.35 * reach)


# ---------------------------------------------------------------- scene side

def hierarchy_markers(top):
    """Locator-shaped transforms anywhere under the selected node."""
    out = []
    for node in cmds.listRelatives(top, allDescendents=True,
                                   type="transform", fullPath=True) or []:
        shapes = cmds.listRelatives(node, shapes=True,
                                    fullPath=True) or []
        if shapes and cmds.objectType(shapes[0]) == "locator":
            out.append(node)
    return out


def collect_groups(top, markers):
    """[(marker, joints)]: every joint under `top` assigned to its
    NEAREST locator ancestor; a joint with none is the root's own."""
    marker_set = set(markers)
    groups = {m: [] for m in markers}
    for j in cmds.listRelatives(top, allDescendents=True, type="joint",
                                fullPath=True) or []:
        node = j
        while node != top:
            parents = cmds.listRelatives(node, parent=True,
                                         fullPath=True)
            if not parents:
                break
            node = parents[0]
            if node in marker_set:
                groups[node].append(j)
                break
    return [(m, groups[m]) for m in markers]


def resolve_root(top):
    """The root joint of the selected hierarchy."""
    if cmds.objectType(top, isAType="joint"):
        return top
    joints = cmds.listRelatives(top, allDescendents=True, type="joint",
                                fullPath=True) or []
    tops = []
    for j in joints:
        parents = cmds.listRelatives(j, parent=True, fullPath=True) or []
        if not parents or not cmds.objectType(parents[0],
                                              isAType="joint"):
            tops.append(j)
    return tops[0] if len(tops) == 1 else None


def learn_groups(top):
    """Memorise the locator grouping of the selected hierarchy in the
    root's local space (name, pivot, bone names and positions), so the
    grouping survives the object being regenerated, moved or turned."""
    markers = hierarchy_markers(top)
    root = resolve_root(top)
    grouped = set()
    data = []
    for m, joints in collect_groups(top, markers):
        if not joints:
            continue
        grouped.update(joints)
        pivot = cmds.xform(m, query=True, worldSpace=True,
                           translation=True)
        data.append({"name": m.split("|")[-1],
                     "pivot": list(pivot),
                     "bones": [j.split("|")[-1] for j in joints],
                     "points": [list(cmds.xform(j, query=True,
                                                worldSpace=True,
                                                translation=True))
                                for j in joints]})
    if data:
        rest = [j for j in cmds.listRelatives(
            top, allDescendents=True, type="joint",
            fullPath=True) or [] if j not in grouped and j != root]
        if rest:
            data.append({"name": "__root__", "pivot": [0.0, 0.0, 0.0],
                         "bones": [j.split("|")[-1] for j in rest],
                         "points": [list(cmds.xform(j, query=True,
                                                    worldSpace=True,
                                                    translation=True))
                                    for j in rest]})
        space = "world"
        if root:
            inv = cmds.getAttr(root + ".worldInverseMatrix[0]")
            for entry in data:
                entry["points"] = _apply_matrix(entry["points"], inv)
                entry["pivot"] = _apply_matrix([entry["pivot"]],
                                               inv)[0]
            space = "root-local"
        with open(GROUPS_FILE, "w") as handle:
            json.dump({"space": space, "groups": data}, handle,
                      indent=2)
    return data


def saved_payload():
    """(groups, space): 'root-local' for files the current learn
    writes, 'world' for the legacy list format."""
    if not os.path.isfile(GROUPS_FILE):
        return [], "world"
    try:
        with open(GROUPS_FILE) as handle:
            raw = json.load(handle)
    except (ValueError, OSError):
        return [], "world"
    if isinstance(raw, dict):
        return raw.get("groups") or [], raw.get("space", "world")
    return raw or [], "world"


def saved_groups():
    """The memorised grouping, [] when nothing was learned yet."""
    return saved_payload()[0]


def _arrow_layer_bones():
    """The joints the animator keeps in the ArrowBones display layer."""
    if ARROW_LAYER not in (cmds.ls(type="displayLayer") or []):
        return []
    return cmds.ls(
        [m for m in (cmds.editDisplayLayerMembers(
            ARROW_LAYER, query=True, fullNames=True) or [])
         if cmds.objectType(m, isAType="joint")], long=True)


def _scene_uuids():
    """Every node as UUIDs; ls(uuid=True) with no objects returns names
    (trap 8), hence the double ls."""
    return set(cmds.ls(cmds.ls(), uuid=True) or [])


def _uuid_nodes(uuids):
    out = []
    for u in uuids:
        out.extend(cmds.ls(u, long=True) or [])
    return out


def _uuid_of(node):
    return cmds.ls(node, uuid=True)[0]


def _node_of(uuid):
    hits = cmds.ls(uuid, long=True) or []
    return hits[0] if hits else None


def _make_knot(name, pivot, rotation, radius):
    knot = cmds.circle(name=name, normal=(0, 1, 0), radius=radius,
                       constructionHistory=False)[0]
    cmds.xform(knot, worldSpace=True, translation=pivot)
    cmds.xform(knot, worldSpace=True, rotation=rotation)
    return cmds.ls(knot, long=True)[0]


def _space_under(knot, world_matrix):
    """The compensating transform: a child of the knot whose WORLD
    matrix is pinned, so whatever is parented into it keeps the local
    values it had under a parent with that same world matrix."""
    space = cmds.group(empty=True,
                       name=knot.split("|")[-1] + "_space")
    space = cmds.ls(cmds.parent(space, knot, relative=True)[0],
                    long=True)[0]
    cmds.xform(space, worldSpace=True, matrix=world_matrix)
    return space


def _adopt(joints, space):
    """Bones into the control's space, local values untouched - the
    space's world equals their old parent's world, so their own curves
    keep playing exactly as before."""
    for j in joints:
        cmds.parent(j, space, relative=True)


def build_rig(root, groups):
    """The whole build, at the current frame, no baking anywhere;
    `groups` is [(name, world pivot, joints)]. Returns (main knot,
    [(name, count)])."""
    root_uuid = _uuid_of(root)
    group_data = [(name, pivot, [_uuid_of(j) for j in joints])
                  for name, pivot, joints in groups]
    root_mat = cmds.getAttr(root + ".worldMatrix[0]")
    root_ro = cmds.xform(root, query=True, worldSpace=True,
                         rotation=True)
    root_pos = cmds.xform(root, query=True, worldSpace=True,
                          translation=True)
    root_parent = cmds.listRelatives(root, parent=True, fullPath=True)
    parent_mat = (cmds.getAttr(root_parent[0] + ".worldMatrix[0]")
                  if root_parent else list(IDENTITY))

    all_pivots = [p for _n, p, _j in groups] or [root_pos]
    main = _make_knot("Parent_" + root.split("|")[-1], root_pos,
                      root_ro, knot_radius(root_pos, all_pivots) * 1.2)
    if root_parent:
        main = cmds.ls(cmds.parent(main, root_parent[0])[0],
                       long=True)[0]
    main_uuid = _uuid_of(main)
    main_space = _space_under(main, parent_mat)
    cmds.parent(_node_of(root_uuid), main_space, relative=True)

    counts = []
    for name, pivot, joint_uuids in group_data:
        joints = [_node_of(u) for u in joint_uuids]
        member_pos = [cmds.xform(j, query=True, worldSpace=True,
                                 translation=True) for j in joints]
        knot = _make_knot(name + "_knot", pivot, root_ro,
                          knot_radius(pivot, member_pos))
        knot = cmds.ls(cmds.parent(knot, _node_of(root_uuid))[0],
                       long=True)[0]
        space = _space_under(knot, root_mat)
        _adopt([_node_of(u) for u in joint_uuids], space)
        counts.append((name, len(joint_uuids)))
    return _node_of(main_uuid), counts


def _arrow_setup(root, layer_bones):
    """The arrow assembly: ArrowMiddle under the root, head and tail
    knots on the two ends of the arrow's bone cloud (root-local axis),
    the layer bones split between them at the midpoint. Same DAG-space
    construction - nothing baked, curves stay on the bones."""
    if len(layer_bones) < 2:
        return ""
    bone_uuids = [_uuid_of(j) for j in layer_bones]
    root_inv = cmds.getAttr(root + ".worldInverseMatrix[0]")
    root_mat = cmds.getAttr(root + ".worldMatrix[0]")
    root_ro = cmds.xform(root, query=True, worldSpace=True,
                         rotation=True)
    local = {}
    for u in bone_uuids:
        j = _node_of(u)
        local[u] = _apply_matrix(
            [cmds.xform(j, query=True, worldSpace=True,
                        translation=True)], root_inv)[0]
    pts = list(local.values())
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    axis_i = max(range(3), key=lambda i: hi[i] - lo[i])
    center = [(lo[i] + hi[i]) * 0.5 for i in range(3)]
    end_a = list(center)
    end_b = list(center)
    end_a[axis_i] = lo[axis_i]
    end_b[axis_i] = hi[axis_i]

    head_hint = None
    payload, space_kind = saved_payload()
    if space_kind == "root-local":
        for entry in payload:
            if entry.get("name") == "ArrowHead":
                head_hint = entry.get("pivot")
    if head_hint:
        da = sum((end_a[i] - head_hint[i]) ** 2 for i in range(3))
        db = sum((end_b[i] - head_hint[i]) ** 2 for i in range(3))
        head_loc, tail_loc = ((end_a, end_b) if da <= db
                              else (end_b, end_a))
    else:
        head_loc, tail_loc = end_a, end_b
    mid_loc = [(head_loc[i] + tail_loc[i]) * 0.5 for i in range(3)]

    axis_v = [tail_loc[i] - head_loc[i] for i in range(3)]
    axis_len2 = sum(v * v for v in axis_v) or 1.0
    head_grp = []
    tail_grp = []
    for u in bone_uuids:
        t = sum((local[u][i] - head_loc[i]) * axis_v[i]
                for i in range(3)) / axis_len2
        (head_grp if t < 0.5 else tail_grp).append(u)

    mid = _make_knot("ArrowMiddle_knot",
                     _apply_matrix([mid_loc], root_mat)[0], root_ro,
                     8.0)
    mid = cmds.ls(cmds.parent(mid, root)[0], long=True)[0]
    for name, pos_loc, members in (
            ("ArrowHead_knot", head_loc, head_grp),
            ("ArrowEnd_knot", tail_loc, tail_grp)):
        knot = _make_knot(name, _apply_matrix([pos_loc], root_mat)[0],
                          root_ro, 6.0)
        knot = cmds.ls(cmds.parent(knot, mid)[0], long=True)[0]
        if members:
            space = _space_under(knot, root_mat)
            _adopt([_node_of(u) for u in members], space)
    return (" Arrow: head %d + tail %d under ArrowMiddle_knot."
            % (len(head_grp), len(tail_grp)))


def _safe_to_delete(node):
    """Never let the manifest take a joint - or anything still holding
    one - down with the rig."""
    if cmds.objectType(node, isAType="joint"):
        return False
    if cmds.objectType(node, isAType="dagNode"):
        if cmds.listRelatives(node, allDescendents=True, type="joint"):
            return False
    return True


def bake_to_bones(start, end):
    """The way out: capture the combined world result of every joint
    living inside the rig, return the joints under the root, key the
    result back onto them, delete the rig. Also handles the older
    constraint-driven rigs, so any build can be taken down."""
    members = [m for m in
               (cmds.sets(RIG_SET, query=True) or [])
               if cmds.objExists(m)]
    members = list(dict.fromkeys(
        n for m in members for n in (cmds.ls(m, long=True) or [])))

    # captive joints: living inside rig transforms (the DAG build)
    captive = []
    for m in members:
        if not cmds.objectType(m, isAType="dagNode"):
            continue
        for j in cmds.listRelatives(m, allDescendents=True,
                                    type="joint", fullPath=True) or []:
            captive.append(j)
    captive = sorted(set(captive))
    roots = [j for j in captive
             if not any(cmds.objectType(p, isAType="joint")
                        for p in (cmds.listRelatives(
                            j, parent=True, fullPath=True) or []))]
    root = roots[0] if len(roots) == 1 else None
    bones = [j for j in captive if j != root]

    # constraint-driven joints (the older builds)
    constrained = []
    for m in members:
        if cmds.objExists(m) and cmds.objectType(m,
                                                 isAType="constraint"):
            parent = cmds.listRelatives(m, parent=True, fullPath=True)
            if parent and cmds.objectType(parent[0], isAType="joint"):
                constrained.append(parent[0])
    constrained = sorted(set(constrained))

    total = 0
    if captive and root:
        uuids = {j: _uuid_of(j) for j in captive}
        root_uuid = uuids[root]
        temp = []
        catchers = {}
        for j in captive:
            loc = cmds.spaceLocator(name="bakeCatch#")[0]
            loc = cmds.ls(loc, long=True)[0]
            temp.append(cmds.parentConstraint(j, loc)[0])
            catchers[uuids[j]] = loc
        cmds.bakeResults(list(catchers.values()), time=(start, end),
                         simulation=True, sampleBy=1,
                         attribute=BAKE_ATTRS,
                         disableImplicitControl=True,
                         preserveOutsideKeys=False)
        cmds.delete([t for t in temp if cmds.objExists(t)])

        # structure back: root to its original container, bones under
        # the root; then the captured worlds keyed on through temp
        # constraints
        main = None
        root_now = _node_of(root_uuid)
        walk = root_now
        while True:
            parents = cmds.listRelatives(walk, parent=True,
                                         fullPath=True)
            if not parents:
                break
            walk = parents[0]
            if walk.split("|")[-1].startswith("Parent_"):
                main = walk
                break
        outer = (cmds.listRelatives(main, parent=True, fullPath=True)
                 if main else None)
        if outer:
            cmds.parent(root_now, outer[0])
        else:
            try:
                cmds.parent(root_now, world=True)
            except RuntimeError:
                pass
        root_now = _node_of(root_uuid)
        for j_uuid in [uuids[j] for j in bones]:
            j_now = _node_of(j_uuid)
            if j_now:
                cmds.parent(j_now, root_now)
        back = []
        for j_uuid, loc in catchers.items():
            j_now = _node_of(j_uuid)
            if not j_now:
                continue
            cmds.cutKey(j_now, attribute=CHANNELS, clear=True)
            back.append(cmds.parentConstraint(loc, j_now)[0])
        targets = [_node_of(u) for u in catchers if _node_of(u)]
        cmds.bakeResults(targets, time=(start, end), simulation=True,
                         sampleBy=1, attribute=BAKE_ATTRS,
                         disableImplicitControl=True,
                         preserveOutsideKeys=False)
        for con in back:
            if cmds.objExists(con):
                cmds.delete(con)
        for loc in catchers.values():
            if cmds.objExists(loc):
                cmds.delete(loc)
        total += len(captive)

    if constrained:
        cmds.bakeResults(constrained, time=(start, end),
                         simulation=True, sampleBy=1,
                         attribute=BAKE_ATTRS,
                         disableImplicitControl=True,
                         preserveOutsideKeys=False)
        for m in members:
            if cmds.objExists(m) and cmds.objectType(
                    m, isAType="constraint"):
                cmds.delete(m)
        total += len(constrained)

    for m in members:
        if not cmds.objExists(m):
            continue
        if not _safe_to_delete(m):
            print("geobonesrig: refusing to delete %s - joints under it"
                  % m)
            continue
        try:
            cmds.delete(m)
        except RuntimeError:
            pass
    if cmds.objExists(RIG_SET):
        cmds.delete(RIG_SET)
    return total


# ------------------------------------------------------------------- window

def _say(message):
    if _status and cmds.text(_status, exists=True):
        cmds.text(_status, edit=True, label=message)
    print("geobonesrig: " + message)


def _frame_range():
    start = int(math.floor(cmds.playbackOptions(query=True, min=True)))
    end = int(math.ceil(cmds.playbackOptions(query=True, max=True)))
    return start, end


def _build_pressed(*_):
    try:
        sel = cmds.ls(selection=True, long=True) or []
        if len(sel) != 1:
            _say("Select the root of the bone hierarchy (exactly one "
                 "node).")
            return
        top = sel[0]
        root = resolve_root(top)
        if not root:
            _say("Could not find one root joint under the selection.")
            return
        if cmds.objExists(RIG_SET):
            _say("An auto rig already exists - Bake to Bones first.")
            return

        arrow_bones_list = [j for j in _arrow_layer_bones()
                            if j != root]
        arrow_set = set(arrow_bones_list)
        bones = [j for j in cmds.listRelatives(
            top, allDescendents=True, type="joint",
            fullPath=True) or [] if j != root and j not in arrow_set]
        markers = hierarchy_markers(top)
        groups = []
        empty = []
        source = ""
        if markers:
            source = "locator hints"
            for m, joints in collect_groups(top, markers):
                joints = [j for j in joints if j not in arrow_set]
                if joints:
                    pivot = cmds.xform(m, query=True, worldSpace=True,
                                       translation=True)
                    groups.append((m.split("|")[-1], pivot, joints))
                else:
                    empty.append(m.split("|")[-1])
        else:
            payload, space = saved_payload()
            saved = [e for e in payload if e.get("points")
                     and not (arrow_set and e.get("name")
                              in ("ArrowHead", "ArrowEnd"))]
            if saved and bones:
                source = "the learned groups file"
                root_inv = cmds.getAttr(root + ".worldInverseMatrix[0]")
                root_mat = cmds.getAttr(root + ".worldMatrix[0]")
                work_pos = {}
                for j in bones:
                    p = cmds.xform(j, query=True, worldSpace=True,
                                   translation=True)
                    if space == "root-local":
                        p = _apply_matrix([p], root_inv)[0]
                    work_pos[j] = p
                all_pts = [p for e in saved for p in e["points"]]
                src_lo = [min(p[i] for p in all_pts) for i in range(3)]
                src_hi = [max(p[i] for p in all_pts) for i in range(3)]
                dst_lo = [min(p[i] for p in work_pos.values())
                          for i in range(3)]
                dst_hi = [max(p[i] for p in work_pos.values())
                          for i in range(3)]
                labeled = []
                pivots = {}
                for gi, entry in enumerate(saved):
                    for q in box_fit(entry["points"], src_lo, src_hi,
                                     dst_lo, dst_hi):
                        labeled.append((q, gi))
                    pivots[gi] = box_fit(
                        [entry.get("pivot", [0, 0, 0])],
                        src_lo, src_hi, dst_lo, dst_hi)[0]
                members_by = {}
                for j in bones:
                    p = work_pos[j]
                    best = None
                    best_d = None
                    for lp, gi in labeled:
                        d = ((lp[0] - p[0]) ** 2 + (lp[1] - p[1]) ** 2
                             + (lp[2] - p[2]) ** 2)
                        if best_d is None or d < best_d:
                            best_d = d
                            best = gi
                    members_by.setdefault(best, []).append(j)
                for gi, entry in enumerate(saved):
                    if entry.get("name") == "__root__":
                        continue
                    members = members_by.get(gi, [])
                    if members:
                        pivot = pivots[gi]
                        if space == "root-local":
                            pivot = _apply_matrix([pivot],
                                                  root_mat)[0]
                        groups.append((entry.get("name", "group"),
                                       pivot, members))
            if not groups:
                source = "clustering"
                k = cmds.intFieldGrp(_kfield, query=True, value1=True)
                if k >= 1 and bones:
                    positions = [cmds.xform(j, query=True,
                                            worldSpace=True,
                                            translation=True)
                                 for j in bones]
                    assign, centers = cluster_bones(positions, k)
                    for c in range(len(centers)):
                        members = [bones[i] for i in range(len(bones))
                                   if assign[i] == c]
                        if members:
                            groups.append(("geoGroup%d" % (c + 1),
                                           centers[c], members))

        root_uuid = _uuid_of(root)
        arrow_uuids = [_uuid_of(j) for j in arrow_bones_list]
        before = _scene_uuids()
        cmds.undoInfo(openChunk=True)
        try:
            main, counts = build_rig(root, groups)
            root_now = _node_of(root_uuid)
            arrow_note = _arrow_setup(
                root_now, [_node_of(u) for u in arrow_uuids
                           if _node_of(u)])
            fresh_nodes = _uuid_nodes(_scene_uuids() - before)
            curves = set(cmds.ls(fresh_nodes, type="animCurve") or [])
            manifest = [n for n in fresh_nodes if n not in curves]
            cmds.sets(manifest, name=RIG_SET)
        finally:
            cmds.undoInfo(closeChunk=True)

        if counts:
            named = ", ".join("%s:%d" % (n, c) for n, c in counts)
            message = ("Rig built at the current frame: main knot %s, "
                       "%d group knot(s) over %d bone(s). %s."
                       % (main.split("|")[-1], len(counts),
                          sum(c for _n, c in counts), named))
        else:
            message = ("Rig built at the current frame: main knot %s "
                       "over the whole array (no groups requested)."
                       % main.split("|")[-1])
        message += arrow_note
        if counts and source:
            message += " Groups from %s." % source
        if empty:
            message += " Empty marker(s) skipped: %s." % ", ".join(empty)
        message += " Bones keep their own animation."
        _say(message)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def _learn_pressed(*_):
    try:
        sel = cmds.ls(selection=True, long=True) or []
        if len(sel) != 1:
            _say("Select the root of the hint hierarchy (exactly one "
                 "node).")
            return
        data = learn_groups(sel[0])
        if not data:
            _say("No locator groups with bones under the selection - "
                 "nothing to learn.")
            return
        shown = [e for e in data if e["name"] != "__root__"]
        rest = sum(len(e["bones"]) for e in data) \
            - sum(len(e["bones"]) for e in shown)
        named = ", ".join("%s:%d" % (e["name"], len(e["bones"]))
                          for e in shown)
        message = ("Learned %d group(s) over %d bone(s): %s."
                   % (len(shown),
                      sum(len(e["bones"]) for e in shown), named))
        if rest:
            message += " %d bone(s) learned as the root's own." % rest
        message += " Saved to %s." % os.path.basename(GROUPS_FILE)
        _say(message)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def _bake_pressed(*_):
    try:
        if not cmds.objExists(RIG_SET):
            _say("No auto rig in the scene.")
            return
        start, end = _frame_range()
        frame_was = cmds.currentTime(query=True)
        cmds.undoInfo(openChunk=True)
        try:
            count = bake_to_bones(start, end)
        finally:
            cmds.undoInfo(closeChunk=True)
            cmds.currentTime(frame_was)
        _say("Baked back onto %d object(s), rig deleted." % count)
    except Exception as exc:
        _say("Failed: %s" % exc)
        raise


def show():
    global _kfield, _status
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="Geo Bones Rig", sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 10))
    cmds.text(label="Select the root, press Create Rig: group controls "
                    "are built at the",
              align="left")
    cmds.text(label="current frame, the bones move INSIDE them and "
                    "keep their own",
              align="left")
    cmds.text(label="animation - the knots add secondary motion on "
                    "top.",
              align="left")
    _kfield = cmds.intFieldGrp(
        label="Groups", value1=6,
        annotation="How many clusters when there is no learned file "
                   "and no locators. The ArrowBones layer always gets "
                   "its own head/middle/tail assembly.")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 0),
                                 (3, "both", 0)])
    cmds.button(label="Create Rig", height=34, command=_build_pressed)
    cmds.button(label="Learn Groups", height=34, width=100,
                command=_learn_pressed,
                annotation="In the hint scene: memorise which bones sit "
                           "in which locator and where the pivots are.")
    cmds.button(label="Bake to Bones", height=34, width=110,
                command=_bake_pressed)
    cmds.setParent("..")
    cmds.text(label="Bake to Bones writes the combined result onto the "
                    "bones and deletes the rig.",
              align="left", enable=False)
    _status = cmds.text(label="", align="left")
    cmds.separator(height=4, style="none")
    cmds.showWindow(WINDOW)

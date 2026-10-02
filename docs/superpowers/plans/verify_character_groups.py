"""verify_character_groups.py - one outliner group and one layer per character (2026-10-02).

mayapy STANDALONE (it adds characters and deletes them - never the animator's scene):

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_character_groups.py

The plugin is this worktree's SkeldarAnim (SKELDAR_PLUGIN overrides).

A  every catalog row alone: ONE new world-level node (its group, marked, linked from its root,
   locked at identity) and ONE new layer holding it; nothing of it moved by the grouping (joints
   and mesh points against the same Add with the grouping switched off); the layer's V off hides
   every shape of it, the asset's own layers included (positive control: they were visible).
B  four characters in one scene (Manny rig, Creep rig, Manny skeleton, Creep skeleton), each with
   a weapon in the hand, one on the floor, the Tech Limb, Camera Setup and a CoM: every part inside
   its own group, nothing else at world level; who-is-it questions (current_root, selection_names,
   deletion.characters, rig_of) answering from the group; a UE clip retargeted onto the rig, a new
   rig and a new skeleton through the bridge, and a square of two through lineimport - all grouped.
C  the exports: animexport.export_hierarchy in both layouts for a grouped rig, a grouped skeleton
   and a grouped Creep (Armature), each read back - the same file as the same character ungrouped
   (top node, joints, world matrices at a frame), no group in it, the scene put back exactly; the
   positive control: the body without the lift DOES write the group.
D  Delete: the group, the layer and everything in it gone, Ctrl+Z bringing them back (the layer
   holding the group again), redo.
E  a legacy character (the grouping switched off): no group, its parts at world level as before,
   Delete and the export working on it.
"""

import os
import sys
import tempfile
import traceback

import maya.standalone

maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except RuntimeError:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.environ.get("SKELDAR_PLUGIN")
                         or os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
cmds.undoInfo(state=True, infinity=True)
CLIP = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX"
TMP = os.path.join(tempfile.gettempdir(), "verify_character_groups")
if not os.path.isdir(TMP):
    os.makedirs(TMP)

import maya_rigs  # noqa: E402
from maya_overrig import builder  # noqa: E402
from maya_scenesetup import armor, camera, catalog, character, chargroup  # noqa: E402
from maya_scenesetup import deletion, droptarget, equip, skeleton  # noqa: E402

print("PLUGIN", PLUGIN, "chargroup from", chargroup.__file__)
FAILED, PASSED = [], []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + str(detail)) if detail else ""))


def tops():
    return set(cmds.ls(assemblies=True, long=True) or [])


def new_root(before):
    fresh = [r for r in builder.character_roots() if r not in before]
    fresh = [r for r in fresh if not any(maya_rigs.under(r, g.group) for g in maya_rigs.rigs())]
    return sorted(fresh, key=lambda p: p.count("|"))[0] if fresh else None


def add(key):
    """(entry, root, rig or None, group) of a row just added."""
    entry = catalog.character_by_key(key)
    rigs_before = set(r.namespace for r in maya_rigs.rigs())
    roots_before = set(builder.character_roots())
    line = character.add_character(entry)
    rig = None
    if catalog.is_rig(entry):
        rig = [r for r in maya_rigs.rigs() if r.namespace not in rigs_before][0]
        root = rig.skeleton_root
    else:
        root = new_root(roots_before)
    return entry, root, rig, character.character_group(rig or root), line


def shapes_under(group):
    return [s for s in cmds.listRelatives(group, allDescendents=True, fullPath=True) or []
            if cmds.objectType(s, isAType="shape")
            and not cmds.getAttr(s + ".intermediateObject")]


def visible(paths):
    count = 0
    for p in paths:
        sel = om.MSelectionList()
        sel.add(p)
        if sel.getDagPath(0).isVisible():
            count += 1
    return count


def world(node):
    return cmds.xform(node, query=True, matrix=True, worldSpace=True)


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b)) if a and b else 1e9


def joint_worlds(root):
    out = {}
    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        out[j.split("|")[-1].split(":")[-1]] = world(j)
    return out


def mesh_points(group_or_paths, limit=40):
    """{mesh leaf: [world points]} of the skinned shapes (a sample)."""
    out = {}
    paths = group_or_paths
    for shape in paths:
        if cmds.nodeType(shape) != "mesh":
            continue
        n = cmds.polyEvaluate(shape, vertex=True)
        step = max(1, n // limit)
        pts = []
        for i in range(0, n, step):
            pts.extend(cmds.pointPosition("%s.vtx[%d]" % (shape, i), world=True))
        out[shape.split("|")[-1].split(":")[-1]] = pts
    return out


def char_shapes(root, rig):
    """The visible shapes of a character, grouped or not: its skinned meshes and its rig's
    controls."""
    from maya_scenesetup import colour
    shapes = [s for s in colour.skinned_shapes(root)]
    if rig is not None:
        shapes += [s for s in cmds.listRelatives(rig.group, allDescendents=True, fullPath=True,
                                                 type="mesh") or []]
    return [cmds.ls(s, long=True)[0] for s in shapes if cmds.objExists(s)
            and not cmds.getAttr(s + ".intermediateObject")]


# ------------------------------------------------------------------ phase A

def ungrouped_add(key):
    """The same Add with the grouping switched off: the legacy character, for comparison."""
    real = character.group_character
    character.group_character = lambda *a, **k: (None, None)
    try:
        return add(key)
    finally:
        character.group_character = real


def phase_a():
    for entry in catalog.CHARACTERS:
        key = entry.key
        cmds.file(new=True, force=True)
        _e, root0, rig0, group0, _line = ungrouped_add(key)
        ref_joints = joint_worlds(root0)
        ref_points = mesh_points(char_shapes(root0, rig0))
        cmds.file(new=True, force=True)
        before_tops, before_layers = tops(), set(cmds.ls(type="displayLayer") or [])
        _e, root, rig, group, line = add(key)
        new_tops = tops() - before_tops
        new_layers = set(cmds.ls(type="displayLayer") or []) - before_layers
        ours = chargroup.layer_of(group)
        gate("A %s: one new world-level node, its group (%s)" % (entry.label, group),
             bool(group) and new_tops == {group}, sorted(new_tops))
        gate("A %s: marked with the row, linked from its root" % entry.label,
             cmds.getAttr(group + "." + chargroup.MARKER) == entry.label
             and chargroup.root_of(group) == root, (chargroup.root_of(group), root))
        gate("A %s: locked at identity" % entry.label,
             worst(world(group), list(om.MMatrix())) < 1e-12
             and all(cmds.getAttr(group + "." + a, lock=True) for a in chargroup.LOCKED))
        members = cmds.editDisplayLayerMembers(ours, query=True, fullNames=True) or []
        gate("A %s: one new layer of ours (%s) holding the group alone" % (entry.label, ours),
             bool(ours) and ours in new_layers and members == [group],
             (sorted(new_layers), members))
        gate("A %s: the line still counts what arrived" % entry.label,
             " 0 joints" not in line, line)
        if rig is not None:
            gate("A %s: the rig's group is AdvancedSkeleton's, below the character group"
                 % entry.label, rig.character == group and cmds.listRelatives(
                     rig.group, parent=True, fullPath=True) == [group]
                 and not maya_rigs.under(rig.skeleton_root, rig.group)
                 and maya_rigs.under(rig.skeleton_root, group), (rig.group, rig.skeleton_root))
        jw = joint_worlds(root)
        jworst = max(worst(jw[k], v) for k, v in ref_joints.items() if k in jw)
        pts = mesh_points(char_shapes(root, rig))
        pworst = max([worst(pts[k], v) for k, v in ref_points.items() if k in pts] or [1e9])
        gate("A %s: the grouping moved nothing (%d joints %.1e cm, %d meshes %.1e cm)"
             % (entry.label, len(ref_joints), jworst, len(ref_points), pworst),
             len(jw) == len(ref_joints) and jworst < 1e-6 and pworst < 1e-4
             and set(pts) == set(ref_points))
        shapes = shapes_under(group)
        on = visible(shapes)
        asset_layers = sorted(l for l in new_layers if l != ours)
        cmds.setAttr(ours + ".visibility", 0)
        off = visible(shapes)
        # the asset's own layers forced visible must not bring anything back
        for layer in asset_layers:
            cmds.setAttr(layer + ".visibility", 1)
        off_forced = visible(shapes)
        cmds.setAttr(ours + ".visibility", 1)
        back = visible(shapes)
        gate("A %s: V off hides every shape (%d visible -> %d, %d with its own layers %s on)"
             % (entry.label, on, off, off_forced, asset_layers),
             on > 0 and off == 0 and off_forced == 0 and back == on)


# ------------------------------------------------------------------ phase B

def phase_b():
    cmds.file(new=True, force=True)
    sword, spear = catalog.by_key("LongSword_02"), catalog.by_key("Spear_01")
    cast = []
    for key in ("Manny_Rig", "Creep_Rig", "Manny", "Creep"):
        cast.append(add(key))
    groups = [c[3] for c in cast]
    for entry, root, rig, group, _line in cast:
        print("   ", equip.to_hand(root, "R", sword))
        print("   ", equip.to_floor(root, spear, (100.0 * len(groups), 0.0, 30.0), (1.0, 0.0, 0.0)))
        print("   ", armor.equip(root, catalog.armor_by_key("Tech_Limb")))
        bone = skeleton.resolve_bone(root, camera.BONE)
        if bone:
            print("   ", camera.setup(bone, 0, 10))
        from maya_com import network
        char = network._character_for(root)
        model, info = network.build_model(char)
        network.create(char, model, info)
    world_now = tops() - set(["|persp", "|top", "|front", "|side"])
    gate("B: nothing at world level but the four groups", world_now == set(groups),
         sorted(world_now - set(groups)))
    for entry, root, rig, group, _line in cast:
        held = equip.occupant(root, "R")[0]
        floor = equip.occupant(root, "L")[0]
        piece = list(armor.worn(root).values())[0][0]
        bone = skeleton.resolve_bone(root, camera.BONE)
        cam = camera.camera_for(bone) if bone else None
        from maya_com import network
        com = [g for g in network.find_all() if network.root_of(g) == root]
        parts = [held, floor, piece] + ([cam] if cam else []) + com
        inside = [maya_rigs.under(cmds.ls(p, long=True)[0], group) for p in parts]
        gate("B %s: hand weapon, floor weapon, armor, camera, CoM all in its group"
             % entry.label, all(inside) and len(com) == 1,
             [p.split("|")[-1] for p, ok in zip(parts, inside) if not ok])
        if rig is None:
            space = cmds.listRelatives(held, parent=True, fullPath=True)[0]
            spaces = cmds.listRelatives(space, parent=True, fullPath=True)[0]
            gate("B %s: its WeaponSpaces group is its own, in its group" % entry.label,
                 cmds.listRelatives(spaces, parent=True, fullPath=True) == [group], spaces)
        else:
            space = cmds.listRelatives(held, parent=True, fullPath=True)[0]
            gate("B %s: the rig's weapon space under the rig's own group" % entry.label,
                 maya_rigs.under(space, rig.group), space)
        # who-is-it, from the group and from a mesh
        cmds.select(group, replace=True)
        gate("B %s: the group selected names its character" % entry.label,
             skeleton.current_root() == root, skeleton.current_root())
        if rig is None:
            mesh = cmds.listRelatives(char_shapes(root, None)[0], parent=True, fullPath=True)[0]
            cmds.select(mesh, replace=True)
            gate("B %s: a mesh selected names its skeleton" % entry.label,
                 skeleton.current_root() == root, skeleton.current_root())
            from maya_uebridge import skeletonimport
            named, _labels = skeletonimport.selection_names(
                [group], skeletonimport.bare_roots(), maya_rigs.rigs())
            gate("B %s: Onto selected reads the group as the skeleton" % entry.label,
                 named == [root], named)
        else:
            gate("B %s: rig_of(the group) is the rig" % entry.label,
                 maya_rigs.rig_of(group, maya_rigs.rigs()) == rig)
        import maya_colour
        from maya_scenesetup import colour as colouring
        found = maya_colour.targets([group], connected="")
        want = set(maya_colour.without_weapons(colouring.character_meshes(root)))
        gate("B %s: the Colour card reads the group as the character (%d shapes)"
             % (entry.label, len(want)), len(found) == 1 and set(found[0].shapes) == want
             and bool(want), [t.label for t in found])
        chars = deletion.characters()
        picked, _unowned = deletion.choose([group], chars)
        gate("B %s: Delete reads the group as the character" % entry.label,
             len(picked) == 1 and picked[0].root == root, [c.label for c in picked])
        cmds.select(clear=True)
    names = sorted(r for r, _l in droptarget.characters())
    gate("B: the drop targets are the four characters",
         names == sorted(c[1] for c in cast), names)
    gate("B: no shield joint reads as a character",
         len(deletion.characters()) == 4, [c.label for c in deletion.characters()])

    # The bridge: onto the rig, a new rig, a new skeleton, a square of two.
    if not os.path.isfile(CLIP):
        gate("B bridge: the clip is on disk", False, CLIP)
        return
    from maya_uebridge import rigimport, skeletonimport, lineimport, records
    rig = cast[0][2]
    hand = skeleton.resolve_bone(rig.skeleton_root, "hand_r")
    at0 = world(hand)
    print("   ", rigimport.import_and_retarget(CLIP, "Heavy", target="rig", rig=rig))
    cmds.currentTime(30)
    gate("B bridge: the clip went onto the grouped rig (hand_r moved %.1f cm)"
         % worst(world(hand), at0), worst(world(hand), at0) > 1.0)
    before = tops()
    print("   ", rigimport.import_and_retarget(CLIP, "Heavy", target="new_rig"))
    fresh = tops() - before
    gate("B bridge: a new rig arrives as one group", len(fresh) == 1
         and chargroup.MARKER in (cmds.listAttr(list(fresh)[0], userDefined=True) or []),
         sorted(fresh))
    before = tops()
    print("   ", skeletonimport.import_onto_skeleton(CLIP, "Heavy"))
    fresh = tops() - before
    gate("B bridge: a new skeleton arrives as one group", len(fresh) == 1
         and chargroup.MARKER in (cmds.listAttr(list(fresh)[0], userDefined=True) or []),
         sorted(fresh))
    before = tops()
    recs = [records.AnimRecord("Heavy_%d" % i, "/Game/x", "", 60, 2.0, 30.0) for i in range(2)]
    print("   ", lineimport.run(recs, lambda record: (CLIP, 30.0), "new_rig"))
    fresh = tops() - before
    gate("B bridge: a square of two new rigs arrives as two groups", len(fresh) == 2
         and all(chargroup.MARKER in (cmds.listAttr(f, userDefined=True) or []) for f in fresh),
         sorted(fresh))
    stray = tops() - set(["|persp", "|top", "|front", "|side"]) - set(
        g for g in tops() if maya_rigs.is_character_group(g))
    gate("B bridge: nothing loose at world level after the bridge", not stray, sorted(stray))


# ------------------------------------------------------------------ phase C

def read_back(path):
    """(top-level names, joint leaves, {leaf: world matrix at frame 20}) of an FBX."""
    if cmds.namespace(exists=":chk"):
        cmds.namespace(removeNamespace=":chk", deleteNamespaceContent=True)
    cmds.namespace(add="chk")
    cmds.namespace(set=":chk")
    try:
        mel.eval("FBXImportMode -v add")
        mel.eval('FBXImport -f "%s";' % path.replace("\\", "/"))
    finally:
        cmds.namespace(set=":")
    nodes = cmds.namespaceInfo(":chk", listOnlyDependencyNodes=True, dagPath=True) or []
    dag = [n for n in cmds.ls(nodes, long=True) or [] if cmds.objectType(n, isAType="dagNode")]
    top = sorted(set(n.split("|")[1].split(":")[-1] for n in dag))
    joints = [n for n in dag if cmds.objectType(n) == "joint"]
    cmds.currentTime(20)
    mats = dict((j.split("|")[-1].split(":")[-1], world(j)) for j in joints)
    leaves = sorted(mats)
    cmds.namespace(removeNamespace=":chk", deleteNamespaceContent=True)
    return top, leaves, mats


def state(root):
    """What an export must leave exactly as it found it: the root's path, every top, names."""
    return (cmds.ls(root, long=True), sorted(tops()),
            sorted(cmds.ls(type="joint", long=True) or []))


def phase_c():
    from maya_uebridge import animexport
    cmds.file(new=True, force=True)
    cmds.playbackOptions(minTime=0, maxTime=30, animationStartTime=0, animationEndTime=30)
    cast = [add(k) for k in ("Manny_Rig", "Manny", "Creep")]
    # a little animation on each so a frame's matrices say something
    for entry, root, rig, group, _l in cast:
        if rig is not None:
            main = rig.main
            cmds.setKeyframe(main, attribute="translateX", time=0, value=0)
            cmds.setKeyframe(main, attribute="translateX", time=30, value=60)
        else:
            cmds.setKeyframe(root, attribute="translateX", time=0,
                             value=cmds.getAttr(root + ".translateX"))
            cmds.setKeyframe(root, attribute="translateX", time=30,
                             value=cmds.getAttr(root + ".translateX") + 60)
    for entry, root, rig, group, _l in cast:
        root_uuid = cmds.ls(root, uuid=True)[0]
        for layout in ("cascadeur", "plain"):
            root = cmds.ls(root_uuid, long=True)[0]
            label = "%s %s" % (entry.label, layout)
            before = state(root)
            grouped = os.path.join(TMP, "g_%s_%s.fbx" % (entry.key, layout))
            info = animexport.export_hierarchy(grouped, root=root, start=0, end=30, layout=layout)
            gate("C %s: the scene is put back exactly" % label, state(root) == before)
            # One Ctrl+Z after an export is a net nothing (the review: it used to undo the lift's
            # LAST step and put the top out at world level), and redo too.
            cmds.undo()
            after_undo = state(cmds.ls(root_uuid, long=True)[0])
            cmds.redo()
            after_redo = state(cmds.ls(root_uuid, long=True)[0])
            gate("C %s: one Ctrl+Z after the export leaves the top in its group, redo too" % label,
                 after_undo == before and after_redo == before
                 and maya_rigs.under(cmds.ls(root_uuid, long=True)[0], group),
                 (after_undo[0], after_redo[0]))
            # the same character out of its group by hand: the file a legacy character writes
            top = chargroup.child_on_path(root, group)
            top_uuid = cmds.ls(top, uuid=True)[0]
            cmds.parent(top, world=True, relative=True)
            loose = os.path.join(TMP, "u_%s_%s.fbx" % (entry.key, layout))
            animexport.export_hierarchy(loose, root=cmds.ls(root_uuid, long=True)[0], start=0,
                                        end=30, layout=layout)
            cmds.parent(cmds.ls(top_uuid, long=True)[0], group, relative=True)
            g_top, g_joints, g_mats = read_back(grouped)
            u_top, u_joints, u_mats = read_back(loose)
            mworst = max([worst(g_mats[k], u_mats[k]) for k in g_mats if k in u_mats] or [1e9])
            gate("C %s: the file is the ungrouped character's (top %s, %d joints, %.1e)"
                 % (label, g_top, len(g_joints), mworst),
                 g_top == u_top and g_joints == u_joints and mworst < 1e-4
                 and not any(GROUP_SUFFIX_IN(t) for t in g_top), (g_top, u_top, info.get("layout")))
    # positive control: the body WITHOUT the lift writes the group (the exporter takes ancestors)
    entry, root, rig, group, _l = cast[1]
    root = cmds.ls(cmds.ls(root, uuid=True)[0], long=True)[0]
    control = os.path.join(TMP, "control.fbx")
    animexport._export_hierarchy(control, root, 0, 30, "plain")
    c_top, _j, _m = read_back(control)
    gate("C control: without the lift the group IS in the file (%s)" % c_top,
         any(GROUP_SUFFIX_IN(t) for t in c_top), c_top)

    # Control for the undo gate: the lift and the body WITHOUT the chunk, then one Ctrl+Z -- the
    # top comes out of its group (what the chunk exists to prevent), so the gate above can fail.
    root_uuid = cmds.ls(root, uuid=True)[0]
    with animexport._out_of_group(root) as lifted_root:
        animexport._export_hierarchy(os.path.join(TMP, "nochunk.fbx"), lifted_root, 0, 30,
                                     "plain")
    cmds.undo()
    out = not maya_rigs.under(cmds.ls(root_uuid, long=True)[0], group)
    cmds.redo()
    gate("C control: without the chunk one Ctrl+Z takes the top out of its group",
         out and maya_rigs.under(cmds.ls(root_uuid, long=True)[0], group))

    # The lift beside a world-level `root` (a legacy skeleton): the lifted root is `root1` for the
    # export's length, and the status line must not name it (the review's finding).
    stray = cmds.createNode("joint", skipSelect=True)
    stray = cmds.rename(stray, "root")
    stray_uuid = cmds.ls(stray, uuid=True)[0]
    root = cmds.ls(root_uuid, long=True)[0]
    before = state(root)
    info = animexport.export_hierarchy(os.path.join(TMP, "beside_root.fbx"), root=root, start=0,
                                       end=30, layout="plain")
    gate("C beside a world `root`: the line names `root`, never the lift's `root1` (%r)"
         % info.get("warning"), info.get("root") == "root"
         and "root1" not in (info.get("warning") or ""), info)
    gate("C beside a world `root`: the scene put back, both roots named `root`",
         state(cmds.ls(root_uuid, long=True)[0]) == before
         and cmds.ls(root_uuid, long=True)[0].split("|")[-1] == "root"
         and cmds.ls(stray_uuid, long=True)[0] == "|root")
    with animexport._out_of_group(cmds.ls(root_uuid, long=True)[0]) as lifted_root:
        leaf_then = lifted_root.split("|")[-1]
        control = animexport._export_hierarchy(os.path.join(TMP, "beside_ctl.fbx"),
                                               lifted_root, 0, 30, "plain")
    gate("C control: without the shown name the line names `%s`" % leaf_then,
         leaf_then != "root" and leaf_then in (control.get("warning") or ""), control)
    cmds.delete(cmds.ls(stray_uuid, long=True)[0])


def GROUP_SUFFIX_IN(name):
    return name.endswith(chargroup.GROUP_SUFFIX) or chargroup.GROUP_SUFFIX + "1" in name


# ------------------------------------------------------------------ phase D

def uuids():
    return set(cmds.ls(cmds.ls() or [], uuid=True) or [])


def phase_d():
    cmds.file(new=True, force=True)
    other = add("Creep")
    for key in ("Manny", "Manny_Rig"):
        before = uuids()
        entry, root, rig, group, _l = add(key)
        print("   ", equip.to_hand(root, "R", catalog.by_key("LongSword_02")))
        print("   ", equip.to_floor(root, catalog.by_key("Spear_01"), (90.0, 0.0, 0.0),
                                    (1.0, 0.0, 0.0)))
        layer = chargroup.layer_of(group)
        added = uuids() - before
        mesh = cmds.listRelatives(char_shapes(root, rig)[0], parent=True, fullPath=True)[0]
        line = deletion.delete_selected([mesh], confirm=lambda text: True)
        print("    ", line)
        left = set(u for u in uuids() - before
                   if cmds.nodeType(cmds.ls(u)[0]) not in deletion.SINGLETONS)
        gate("D %s: the group, the layer and everything in it gone" % entry.label,
             not cmds.objExists(group) and not cmds.objExists(layer) and not left,
             sorted(cmds.ls(list(left))[:8]))
        gate("D %s: the other character untouched" % entry.label,
             cmds.objExists(other[3]) and cmds.objExists(other[1]))
        cmds.undo()
        back = cmds.ls(cmds.ls(group.split("|")[-1], long=True) or [], long=True)
        members = (cmds.editDisplayLayerMembers(layer, query=True, fullNames=True) or []) \
            if cmds.objExists(layer) else []
        gate("D %s: Ctrl+Z brings it all back, the layer holding the group" % entry.label,
             added <= uuids() and members == [group], (len(added - uuids()), members))
        cmds.redo()
        gate("D %s: redo takes it again" % entry.label,
             not cmds.objExists(group) and not cmds.objExists(layer))


# ------------------------------------------------------------------ phase E

def phase_e():
    from maya_uebridge import animexport
    cmds.file(new=True, force=True)
    entry, root, rig, group, _l = ungrouped_add("Manny")
    gate("E legacy: no group, the root at world level", group is None
         and cmds.listRelatives(root, parent=True) is None, root)
    print("   ", equip.to_hand(root, "R", catalog.by_key("LongSword_02")))
    held = equip.occupant(root, "R")[0]
    gate("E legacy: its WeaponSpaces at world level, as before",
         cmds.ls(held, long=True)[0].count("|") == 3, cmds.ls(held, long=True)[0])
    path = os.path.join(TMP, "legacy.fbx")
    info = animexport.export_hierarchy(path, root=root, start=0, end=10, layout="cascadeur")
    gate("E legacy: the export writes Armature over root", read_back(path)[0] == ["Armature"],
         info.get("layout"))
    line = deletion.delete_selected([root], confirm=lambda text: True)
    gate("E legacy: Delete takes it whole", not cmds.objExists(root)
         and not (tops() - set(["|persp", "|top", "|front", "|side"])), line)


def phase_f():
    """A portrait dropped on the floor (`add_character(at=)`): the character stands on the point,
    its group stays at the origin, the Creep's Armature too (Cascadeur's layout kept)."""
    from maya_uebridge import fbxlayout
    for key, point in (("Manny_Rig", (150.0, 0.0, -40.0)), ("Creep", (-90.0, 0.0, 60.0))):
        entry = catalog.character_by_key(key)
        found = []
        for drop in (None, point):
            cmds.file(new=True, force=True)
            rigs_before = set(r.namespace for r in maya_rigs.rigs())
            roots_before = set(builder.character_roots())
            character.add_character(entry, at=drop)
            if catalog.is_rig(entry):
                rig = [r for r in maya_rigs.rigs() if r.namespace not in rigs_before][0]
                node, root = rig.main, rig.skeleton_root
            else:
                node = root = new_root(roots_before)
            found.append((node, root, cmds.xform(node, query=True, worldSpace=True,
                                                 translation=True)))
        node, root, at = found[1]
        rest = found[0][2]
        group = character.character_group(root)
        layout = fbxlayout.root_in_layout(root)[0] if key == "Creep" else True
        off = max(abs(at[0] - rest[0] - point[0]), abs(at[1] - rest[1]),
                  abs(at[2] - rest[2] - point[2]))
        gate("F %s dropped at %s: moved by exactly that (%.1e), its group at the origin%s"
             % (entry.label, point[::2], off,
                ", the Armature in Cascadeur's layout" if key == "Creep" else ""),
             off < 1e-6 and bool(group) and worst(world(group), list(om.MMatrix())) < 1e-12
             and layout)


class _Failing(object):
    """`maya.cmds` with ONE call of one command made to raise -- `chargroup.make` failing half
    way. Only that call: the rollback goes through the same `cmds` and must be able to run."""

    def __init__(self, real, name, after=0):
        self._real, self._name, self._after, self._calls = real, name, after, 0

    def __getattr__(self, attr):
        if attr != self._name:
            return getattr(self._real, attr)

        def failing(*args, **kwargs):
            self._calls += 1
            if self._calls == self._after + 1:      # that one call only: the rollback's own run
                raise RuntimeError("probe: %s refused" % self._name)
            return getattr(self._real, attr)(*args, **kwargs)
        return failing


def phase_g():
    """`chargroup.make` failing half way leaves the character exactly as an Add before the groups
    left it -- no half group, no layer -- and the Add line says so (the review's finding)."""
    for key, fail, after in (("Manny", "createDisplayLayer", 0), ("Creep", "parent", 1),
                             ("Manny_Rig", "editDisplayLayerMembers", 0)):
        cmds.file(new=True, force=True)
        layers_before = set(cmds.ls(type="displayLayer") or [])
        real = chargroup.cmds
        chargroup.cmds = _Failing(real, fail, after)
        try:
            entry, root, rig, group, line = add(key)
        finally:
            chargroup.cmds = real
        world_now = tops() - set(["|persp", "|top", "|front", "|side"])
        layers_left = set(cmds.ls(type="displayLayer") or []) - layers_before
        ours = [l for l in layers_left if l.endswith(chargroup.LAYER_SUFFIX)]
        loose = sorted(t for t in world_now if maya_rigs.is_character_group(t))
        # the same Add with the grouping switched off, for the shape it must equal
        cmds.file(new=True, force=True)
        _e, legacy_root, _r, _g, _l = ungrouped_add(key)
        legacy_world = tops() - set(["|persp", "|top", "|front", "|side"])
        gate("G %s, %s refused: no group, no layer, the tops as a legacy Add leaves them "
             "(%d at world)" % (entry.label, fail, len(world_now)),
             group is None and not loose and not ours
             and sorted(t.split("|")[-1] for t in world_now)
             == sorted(t.split("|")[-1] for t in legacy_world), (loose, ours, sorted(world_now)))
        gate("G %s, %s refused: the Add line says the character was not grouped" % (
            entry.label, fail), "no character group" in (line or ""), line)


def phase_h():
    """A UE clip onto a GROUPED rig equals the same clip onto the same rig ungrouped: the rig
    turned and moved first (rig_place keeps its place and facing), hand_r and root over the take,
    the source namespace gone, the holder gone (the review: `hand_r moved > 1 cm` proved nothing)."""
    if not os.path.isfile(CLIP):
        gate("H: the clip is on disk", False, CLIP)
        return
    from maya_uebridge import rigimport
    found = []
    for grouped in (False, True):
        cmds.file(new=True, force=True)
        entry, root, rig, group, _l = (add if grouped else ungrouped_add)("Manny_Rig")
        cmds.setAttr(rig.main + ".translateX", 90.0)
        cmds.setAttr(rig.main + ".translateZ", -40.0)
        cmds.setAttr(rig.main + ".rotateY", 60.0)
        namespaces = set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or [])
        print("   ", rigimport.import_and_retarget(CLIP, "Heavy", target="rig", rig=rig))
        hand = skeleton.resolve_bone(rig.skeleton_root, "hand_r")
        track = []
        for frame in (0, 10, 20, 30, 40):
            cmds.currentTime(frame - 1)
            cmds.currentTime(frame)
            track.append((world(hand), world(rig.skeleton_root), world(rig.main)))
        left = set(cmds.namespaceInfo(":", listOnlyNamespaces=True) or []) - namespaces
        holder = maya_rigs.node(rig, "MoCapConstraints")
        found.append((track, left, cmds.objExists(holder), group))
    (ref, ref_left, ref_holder, _g), (got, left, holder, group) = found
    worst_hand = max(worst(a[0], b[0]) for a, b in zip(ref, got))
    worst_root = max(worst(a[1], b[1]) for a, b in zip(ref, got))
    worst_main = max(worst(a[2], b[2]) for a, b in zip(ref, got))
    moved = max(worst(got[0][0], g[0]) for g in got)
    gate("H: the clip onto the grouped rig = onto the ungrouped one (hand_r %.1e, root %.1e, "
         "Main %.1e over 5 frames; hand_r travels %.1f)" % (worst_hand, worst_root, worst_main,
                                                            moved),
         worst_hand < 1e-4 and worst_root < 1e-4 and worst_main < 1e-4 and moved > 1.0
         and bool(group))
    gate("H: the source namespace and the holder gone, both roads",
         not left and not holder and not ref_left and not ref_holder,
         (sorted(left), holder, sorted(ref_left), ref_holder))
    turned = cmds.xform(cmds.ls(found[1][3], long=True)[0] if found[1][3] else "|persp",
                        query=True, worldSpace=True, matrix=True)
    gate("H: the character group still at the origin after the retarget",
         worst(turned, list(om.MMatrix())) < 1e-12)


def phase_i():
    """Two grouped characters of ONE skeleton asset (two Manny skeletons, two Creep skeletons):
    a grouped second Manny keeps a plain `root` and plain mesh names now (no world-level clash),
    so every rule written for 'only the top node collides' is asked again here; and a prop of the
    animator's dropped into a group, the floor weapon and the camera selected."""
    from maya_scenesetup import colour as colouring
    from maya_uebridge import animexport, skeletonimport
    import maya_colour
    cmds.file(new=True, force=True)
    cmds.playbackOptions(minTime=0, maxTime=10, animationStartTime=0, animationEndTime=10)
    cast = [add(k) for k in ("Manny", "Manny", "Creep", "Creep")]
    names = [c[1].split("|")[-1] for c in cast]
    gate("I: the second Manny and Creep keep a plain `root` (%s)" % names,
         names == ["root"] * 4, [c[1] for c in cast])
    # the Colour card on each one's mesh: that character's shapes, nobody else's
    for i, (entry, root, rig, group, _l) in enumerate(cast):
        want = set(maya_colour.without_weapons(colouring.character_meshes(root)))
        others = set()
        for j, c in enumerate(cast):
            if j != i:
                others |= set(colouring.character_meshes(c[1]))
        mesh = cmds.listRelatives(sorted(want)[0], parent=True, fullPath=True)[0]
        found = maya_colour.targets([mesh], connected="")
        shapes = set(found[0].shapes) if found else set()
        gate("I %s #%d: the Colour card's target is its own %d shapes" % (entry.label, i,
                                                                          len(want)),
             bool(want) and shapes and shapes <= want and not (shapes & others),
             (len(shapes), len(shapes & others)))
    # a real recolour of each Manny through its group: its own shapes take the colour, the
    # other's keep theirs (the shapes share leaf names now -- colour.unambiguous's case)
    red, teal = (0.8, 0.1, 0.1), (0.1, 0.7, 0.7)
    for (entry, root, rig, group, _l), rgb in zip(cast[:2], (red, teal)):
        print("   ", maya_colour.paint(rgb, selection=[group], connected="", undoable=False))
    for (entry, root, rig, group, _l), rgb in zip(cast[:2], (red, teal)):
        shapes = list(maya_colour.without_weapons(colouring.character_meshes(root)))
        worn = colouring.colour_of(shapes)
        gate("I recolour %s in %s: its %d shapes wear it, the other Manny not" % (
            group.split("|")[-1], colouring.colour_name(rgb), len(shapes)),
            bool(shapes) and worn is not None and colouring.same_colour(worn, rgb), worn)
    # export: nothing selected refuses (two plausible skeletons), each selected exports itself
    cmds.select(clear=True)
    try:
        animexport.resolve_root()
        refused = False
    except RuntimeError as exc:
        refused = True
        print("    nothing selected:", exc)
    gate("I export: with nothing selected and four skeletons the export refuses (no guess)",
         refused)
    for i, (entry, root, rig, group, _l) in enumerate(cast[:2]):
        mesh = cmds.listRelatives(char_shapes(root, None)[0], parent=True, fullPath=True)[0]
        cmds.select(mesh, replace=True)
        resolved = animexport.resolve_root()
        gate("I export Manny #%d: its mesh selected resolves its own root" % i,
             resolved == root, (resolved, root))
        cmds.select(clear=True)
    # Onto selected: each mesh, the floor weapon, the camera name their own skeleton
    from maya_scenesetup import equip
    spear = catalog.by_key("Spear_01")
    for i, (entry, root, rig, group, _l) in enumerate(cast[:2]):
        print("   ", equip.to_floor(root, spear, (150.0 * (i + 1), 0.0, 40.0), (1.0, 0.0, 0.0)))
        bone = skeleton.resolve_bone(root, camera.BONE)
        print("   ", camera.setup(bone, 0, 10))
    bare, rigs_ = skeletonimport.bare_roots(), maya_rigs.rigs()
    for i, (entry, root, rig, group, _l) in enumerate(cast[:2]):
        floor_weapon = equip.occupant(root, "R")[0] or equip.occupant(root, "L")[0]
        cam = camera.camera_for(skeleton.resolve_bone(root, camera.BONE))
        mesh = cmds.listRelatives(char_shapes(root, None)[0], parent=True, fullPath=True)[0]
        for what, node in (("mesh", mesh), ("floor weapon", floor_weapon), ("camera", cam)):
            named, _labels = skeletonimport.selection_names([cmds.ls(node, long=True)[0]], bare,
                                                            rigs_)
            cmds.select(node, replace=True)
            current = skeleton.current_root()
            gate("I Onto selected, Manny #%d's %s: names its own skeleton, as current_root does"
                 % (i, what), named == [root] and current == root, (named, current))
    cmds.select(clear=True)
    # the animator's prop parked in the first Manny's group: kept on Delete, named in the confirm
    entry, root, rig, group, _l = cast[0]
    prop = cmds.polyCube(name="prop_cube")[0]
    prop = cmds.parent(prop, group)[0]
    prop_uuid = cmds.ls(prop, uuid=True)[0]
    cmds.setAttr(cmds.ls(prop_uuid, long=True)[0] + ".translateX", 33.0)
    at_before = world(cmds.ls(prop_uuid, long=True)[0])
    picked, _u = deletion.choose([cmds.ls(prop_uuid, long=True)[0]], deletion.characters())
    gate("I prop: the animator's own prop in the group names no character", picked == [],
         [c.label for c in picked])
    asked = []
    other = cast[1]
    mesh = cmds.listRelatives(char_shapes(root, None)[0], parent=True, fullPath=True)[0]
    line = deletion.delete_selected([mesh], confirm=lambda text: asked.append(text) or True)
    print("    ", line)
    kept = cmds.ls(prop_uuid, long=True)
    gate("I prop: Delete of the character keeps the prop at world level, where it stood",
         bool(kept) and kept[0].count("|") == 1 and worst(world(kept[0]), at_before) < 1e-9
         and not cmds.objExists(group), (kept, line))
    gate("I prop: the confirm and the line name the prop",
         asked and "prop_cube" in asked[0] and "prop_cube" in (line or ""), (asked, line))
    gate("I Delete: the other Manny skeleton whole (its group, root, meshes)",
         cmds.objExists(other[3]) and cmds.objExists(other[1])
         and bool(char_shapes(other[1], None)))
    cmds.undo()
    back = cmds.ls(prop_uuid, long=True)
    gate("I prop: Ctrl+Z puts the character and the prop in its group back",
         cmds.objExists(group) and back and maya_rigs.under(back[0], group), back)


if __name__ == "__main__":
    for name, phase in (("A", phase_a), ("B", phase_b), ("C", phase_c), ("D", phase_d),
                        ("E", phase_e), ("F", phase_f), ("G", phase_g), ("H", phase_h),
                        ("I", phase_i)):
        if os.environ.get("PHASES") and name not in os.environ["PHASES"]:
            continue
        print("=== phase", name)
        try:
            phase()
        except Exception:                                          # noqa: BLE001
            traceback.print_exc()
            gate("phase %s ran to the end" % name, False)
    print("\n%d gates, %d failed" % (len(PASSED) + len(FAILED), len(FAILED)))
    for name in FAILED:
        print("FAILED:", name)
    sys.stdout.flush()
    os._exit(0)

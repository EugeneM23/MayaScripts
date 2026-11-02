"""The Swordman's sword and shield as catalog weapons.

    mayapy make_swordman_weapons.py

Reads  sources/swordman/Swordman_Source.mb
Writes SkeldarAnim/assets/Swordman_Sword.fbx  (weapon_r)
       SkeldarAnim/assets/Swordman_Shield.fbx (weapon_l)

`bonedrive` places a weapon at `world = grip . frame . bone`, and a catalog
row's default frame makes that `R(SOCKET_TURN) . W_bone` at zero grip. So each
prop is exported with its points expressed in THAT seat: Add Weapon at zero
grip then puts each back in his fist exactly where he holds it, and the rows
need no stored grip and no frame of their own.

The points carry his 2.54 (trap 86): the sword is a 117 cm blade, not the
46 cm its own geometry reads.

And since 2026-11-02 they carry his own SEAT: he placed both props on his rig by
hand («я выставлю тебе так как это должно сидеть на персонаже»), `swordman_seats`
holds where each must sit in its hand, and the difference between that and what
Add Weapon gives today is folded into the points. Two things that difference is
made of: the sword he simply turned (52 deg), and a LEFT-hand weapon gets the
mirror grip `grips.for_hand` computes when nothing is dialled -- the shield was
exported for zero grip, so Add stood it ~171 deg away and he saw it backwards.
"""
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
from maya_scenesetup import bonedrive                              # noqa: E402
from maya_scenesetup import catalog, grips                         # noqa: E402

RIG_ROW = "Swordman_Rig"
DEFAULTS = {}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swordman_seats                                              # noqa: E402

SRC = os.path.join(REPO, "sources", "swordman", "Swordman_Source.mb")
ASSETS = os.path.join(REPO, "SkeldarAnim", "assets")

# (the source's mesh, its bone, the exported file, the exported mesh name)
PROPS = [("Swordman_Sword", "weapon_r", "Swordman_Sword.fbx", "Swordman_SwordMesh"),
         ("Swordman_Shield", "weapon_l", "Swordman_Shield.fbx", "Swordman_ShieldMesh")]
TOL = 1e-4


def leaf(path):
    return path.split("|")[-1].split(":")[-1]


def one(pattern, **kw):
    hits = cmds.ls("*" + pattern, long=True, **kw) or []
    if len(hits) != 1:
        raise RuntimeError("%s: expected one, found %d" % (pattern, len(hits)))
    return hits[0]


def shape_of(transform):
    return cmds.listRelatives(transform, shapes=True, fullPath=True,
                              noIntermediate=True)[0]


def points_of(path, space=om.MSpace.kWorld):
    """Fresh MPoints: the MPointArray's own memory dangles once it is collected."""
    got = om.MFnMesh(om.MSelectionList().add(path).getDagPath(0)).getPoints(space)
    return [om.MPoint(p.x, p.y, p.z) for p in got]


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def hand_of(bone):
    """The hand a drive bone hangs under: the reference for a seat."""
    return cmds.listRelatives(bone, parent=True, fullPath=True)[0]


def defaults_from_the_rig():
    """{key: where Add Weapon stands that prop in its hand}, read off the RIG.

    `grip . frame . bone` is the placement, so in the hand's own frame it is
    `grip . frame . bone_local`. Two things decide it and both belong to the
    shipped rig, not to his source scene: the drive bone's own local, and -
    for the left hand - the mirror grip `grips.for_hand` computes from the two
    sockets. Read in a scratch scene holding nothing but the rig, with both
    hands empty, which is the state a colleague's first Add meets.

    Measured 2026-11-02, and it is why this is not read from the source scene
    any more: there the sword's own frame built `weapon_r`, so its local is
    not the rig's, and the fold came out one whole turn off - the live press
    stood the sword 52 deg from his seat with the asset that was meant to
    reproduce it.

    The grip must be the COMPUTED one: a grip remembered in whoever runs this
    script's prefs would silently seat the asset for them alone.
    """
    entry = [c for c in catalog.CHARACTERS if c.key == RIG_ROW][0]
    cmds.file(new=True, force=True)
    cmds.file(catalog.character_file(entry), i=True, type="mayaAscii",
              ignoreVersion=True, namespace="rig", mergeNamespacesOnClash=False,
              preserveReferences=True, executeScriptNodes=False)
    root = one("rig:root", type="joint")
    out = {}
    for key, (side, _hand, bone_leaf) in sorted(swordman_seats.HANDS.items()):
        if grips.stored(key, side) is not None:
            raise RuntimeError("%s: a grip for the %s hand is remembered in these prefs "
                               "(%s) -- clear it before exporting"
                               % (key, side, grips.optionvar_name(key, side)))
        row = catalog.by_key(key)
        bone = one("rig:" + bone_leaf, type="joint")
        if cmds.listConnections(bone + ".translateX", s=True, d=False):
            raise RuntimeError("%s is driven in the rig asset: its own local is not "
                               "the socket" % bone_leaf)
        grip = om.MMatrix(bonedrive.matrix_of(*grips.for_hand(row, side, root)))
        out[key] = rigid(grip * seat_of(bone) * wm(hand_of(bone)).inverse())
        print("  %-22s the press stands it at %s in %s"
              % (key, [round(v, 4) for v in
                       om.MTransformationMatrix(out[key]).translation(om.MSpace.kTransform)],
                 _hand))
    return out


def rigid(matrix):
    """`matrix` without its scale: the rig's own chain leaves 4e-6 of it."""
    got = om.MTransformationMatrix(matrix)
    out = om.MTransformationMatrix()
    out.setRotation(got.rotation(asQuaternion=False))
    out.setTranslation(got.translation(om.MSpace.kTransform), om.MSpace.kTransform)
    return out.asMatrix()


def seat_of(bone):
    """Where zero grip stands a weapon of the default frame on `bone`.

    Through bonedrive's own `socket_frame` and `framed`, so this can never
    drift from what Add Weapon actually does.
    """
    frame = bonedrive.socket_frame()
    return om.MMatrix(bonedrive.framed(frame, cmds.getAttr(bone + ".worldMatrix[0]")))


def span(points):
    return max((om.MVector(a - b).length() for a in points for b in points), default=0.0)


def longest_axis(points):
    extents = []
    for axis in range(3):
        values = [p[axis] for p in points]
        extents.append((max(values) - min(values), "xyz"[axis]))
    extents.sort(reverse=True)
    return extents[0]


def export(mesh_name, bone_name, file_name, out_name):
    cmds.file(SRC, open=True, force=True, executeScriptNodes=False, prompt=False)
    mesh = one(mesh_name, type="transform")
    bone = one(bone_name, type="joint")

    his = points_of(shape_of(mesh))
    seat = seat_of(bone)
    #  his seat, folded in: the points are turned by the difference between where
    #  he put the prop in its hand and where Add Weapon stands it today, so the
    #  default placement reproduces his (`p . delta . D = p . X`).
    want = om.MMatrix(swordman_seats.IN_HAND[mesh_name])
    today = DEFAULTS[mesh_name]
    delta = want * today.inverse()
    local = [om.MPoint(p) * seat.inverse() * delta for p in his]
    hand = wm(hand_of(bone))
    placed = today * hand
    wanted = [om.MPoint(p) * placed for p in local]
    moved = om.MTransformationMatrix(delta)
    angle = moved.rotation(asQuaternion=True).asAxisAngle()[1]
    print("  %-22s his seat folded in: turned %.2f deg, moved %.2f cm"
          % (file_name, om.MAngle(angle, om.MAngle.kRadians).asDegrees(),
             om.MVector(moved.translation(om.MSpace.kTransform)).length()))

    # keep this one prop, nothing else
    # `parent -world` answers None for a node already at world level
    moved = cmds.parent(mesh, world=True) if mesh.count("|") > 1 else None
    keep = cmds.ls(moved[0] if moved else mesh, long=True)[0]
    for top in cmds.ls(assemblies=True, long=True) or []:
        if top != keep and leaf(top) not in ("persp", "top", "front", "side"):
            cmds.delete(top)
    keep = cmds.ls("*" + mesh_name, long=True, type="transform")[0]
    #  his source scene keys these props (measured 2026-11-02: 9 curves on each),
    #  and a weapon that arrives ANIMATED ignores where Add Weapon stands it -- the
    #  curves take the node over on the first evaluation. Cut them before the
    #  channels are zeroed, or the zeros are written into a curve instead.
    cmds.cutKey(keep, clear=True)
    for attr, value in (("translate", (0, 0, 0)), ("rotate", (0, 0, 0)),
                        ("scale", (1, 1, 1)), ("shear", (0, 0, 0)),
                        ("rotateAxis", (0, 0, 0))):
        cmds.setAttr(keep + "." + attr, *value)
    left = cmds.listConnections(keep, type="animCurve", source=True,
                                destination=False) or []
    if left:
        raise RuntimeError("%s still carries %d animCurve(s): %s"
                           % (file_name, len(left), left[:4]))
    shape = shape_of(keep)
    om.MFnMesh(om.MSelectionList().add(shape).getDagPath(0)).setPoints(
        om.MPointArray(local), om.MSpace.kObject)

    # a plain lambert: the atlas arrives through the catalog row's `texture`,
    # and openPBR_shader1 is a node type not every Maya has.
    for engine in cmds.listConnections(shape, type="shadingEngine") or []:
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
    material = cmds.shadingNode("lambert", asShader=True, name=out_name + "_Mat")
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                      name=material + "SG")
    cmds.connectAttr(material + ".outColor", group + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=group)
    keep = cmds.ls(cmds.rename(keep, out_name), long=True)[0]

    out = os.path.join(ASSETS, file_name)
    work = os.path.join(tempfile.gettempdir(), "swordman_weapons_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    tmp = os.path.join(work, file_name).replace("\\", "/")
    cmds.loadPlugin("fbxmaya", quiet=True)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportSmoothingGroups -v true")
    #  and no animation in the file at all: belt and braces beside the cut above
    mel.eval('FBXProperty "Export|IncludeGrp|Animation" -v false')
    mel.eval("FBXExportSkins -v false")
    mel.eval("FBXExportShapes -v false")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval('FBXExport -f "%s"' % tmp)
    if not os.path.exists(tmp):
        raise RuntimeError("the exporter wrote nothing to %s" % tmp)

    check(tmp, out_name, wanted, placed, file_name, his)
    shutil.move(tmp, out)
    return out


def check(path, out_name, his_world, seat, file_name, source_world=()):
    """Read it back the way Add Weapon does and place it as the press would.

    `seat` is the placement Add Weapon gives in this scene's pose and
    `his_world` the points it must then show -- his own seat. `source_world`
    is where the source file held the prop, so the print says how far his
    seat moved it.
    """
    cmds.file(new=True, force=True)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))
    mesh = one(out_name, type="transform")
    shape = shape_of(mesh)
    back = points_of(shape, om.MSpace.kObject)
    if len(back) != len(his_world):
        raise RuntimeError("%s: %d points went out, %d came back"
                           % (file_name, len(his_world), len(back)))
    placed = [om.MPoint(p) * seat for p in back]
    worst = max((om.MVector(a - b).length() for a, b in zip(placed, his_world)),
                default=0.0)
    if worst > TOL:
        raise RuntimeError("%s lands %.6f cm off the seat asked" % (file_name, worst))
    length, axis = longest_axis(back)
    uvs = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
    print("  %-22s %3d verts, %6.1f cm along its own %s, span %.1f, uv %s"
          % (file_name, len(back), length, axis, span(back), uvs))
    print("  %-22s lands %.2e cm off the seat asked under Add Weapon" % ("", worst))
    if source_world:
        off = max((om.MVector(a - b).length() for a, b in zip(placed, source_world)),
                  default=0.0)
        print("  %-22s %.1f cm from where the source file held it" % ("", off))


def main():
    global DEFAULTS
    os.chdir(tempfile.gettempdir())
    print("reading where Add Weapon stands each prop, off the shipped rig:")
    DEFAULTS = defaults_from_the_rig()
    print("exporting so that that placement reproduces the seat he set on his")
    print("rig (swordman_seats.IN_HAND):")
    for mesh_name, bone, file_name, out_name in PROPS:
        got = export(mesh_name, bone, file_name, out_name)
        print("  wrote %s (%.1f KB)" % (got, os.path.getsize(got) / 1024.0))


if __name__ == "__main__":
    main()
    maya.standalone.uninitialize()

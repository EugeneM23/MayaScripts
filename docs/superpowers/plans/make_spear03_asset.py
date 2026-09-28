"""make_spear03_asset.py - the animator's Spear_03.fbx onto the sword's axes,
exported as SkeldarAnim/assets/Spear_03.fbx, its texture beside it as
Spear_03.png. mayapy STANDALONE:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_spear03_asset.py

Spec: docs/superpowers/specs/2026-09-28-spear03-textured-weapon-design.md.
The sources (sources/weapons/, copied from the animator's Downloads) are never
written.

Measured on the source (2026-09-28, a Blender 2.83 export from a Unity
project): TWO meshes, `Spear_03_LOD0` (230 vertices, 185 faces) and
`Spear_03_LOD1` (116) - the LOD0 ships, as the Orc's did. Identity
transforms, pivots at the origin. Long axis already **+Y** (199.6 cm,
-0.215..199.407), the head at +Y (166..199, 7.7 cm wide in **Z** and 2.9 cm
thin in X), the butt at the origin. One phong `Halberd` whose colour is a
file node pointing at `D:\\Unity_Project\\...\\Halberd_A.tga` - a path that
exists on no machine of ours. The UV set is named `UVКарта`, which Maya
shows as `UV?????`. The texture: a 2048 x 2048 TGA, 24-bit, uncompressed,
no alpha, 12.6 MB.

The sword's frame: blade along +Y with the tip at +Y, the width on X, the
thickness on Z - so a quarter turn about Y takes the head's width from Z to
X. The grip: the animator chose Spear 01's («как у Spear 01»), the SAME
FRACTION of the length from the butt, measured on the shipped Spear_01.fbx
in this very run rather than typed.
"""
import ctypes
import os
import sys

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
cmds.loadPlugin("fbxmaya", quiet=True)

from maya_scenesetup import attach  # noqa: E402

SOURCE = "C:/!!!Work/MayaScripts/sources/weapons/Spear_03.fbx"
SOURCE_TEXTURE = "C:/!!!Work/MayaScripts/sources/weapons/Halberd_A.tga"
REFERENCE = PLUGIN + "/assets/Spear_01.fbx"
TARGET = PLUGIN + "/assets/Spear_03.fbx"
TARGET_TEXTURE = PLUGIN + "/assets/Spear_03.png"
MESH_NAME = "Spear03Mesh"
MATERIAL = "Spear_03_material"
KEEP = "LOD0"

# A quarter turn about +Y, as the images of the source's basis vectors (Maya
# row vectors: world = local . M): X -> -Z, Y -> Y, Z -> +X. The head's width
# (source Z) lands on X, its thickness (source X) on -Z. Determinant +1.
ROWS = ((0.0, 0.0, -1.0),
        (0.0, 1.0, 0.0),
        (1.0, 0.0, 0.0))
BUTT = 16.0        # the butt cap and the shaft's bottom ring: source Y 0..16


def points(shape):
    sel = om.MSelectionList()
    sel.add(shape)
    fn = om.MFnMesh(sel.getDagPath(0))
    return [(p.x, p.y, p.z) for p in fn.getPoints(om.MSpace.kObject)]


def det3(rows):
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def extents(shape):
    pts = points(shape)
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)], pts)


def shape_of(mesh):
    return cmds.listRelatives(mesh, shapes=True, fullPath=True,
                              noIntermediate=True)[0]


def freeze(mesh):
    cmds.makeIdentity(mesh, apply=True, translate=True, rotate=True,
                      scale=True, normal=0)


def grip_fraction():
    """Spear 01's origin as a fraction of its length from the butt."""
    cmds.file(new=True, force=True)
    meshes = attach.mesh_transforms(attach.import_model(REFERENCE))
    lo, hi, _ = extents(shape_of(meshes[0]))
    fraction = -lo[1] / (hi[1] - lo[1])
    print("Spear 01: Y %.3f..%.3f, origin %.3f cm above the butt = %.4f of "
          "%.3f" % (lo[1], hi[1], -lo[1], fraction, hi[1] - lo[1]))
    return fraction


def pixel_bytes(image):
    """The image's pixels. `MImage.pixels()` answers an ADDRESS (an int), and
    `getSize()` a list - `bytes(address)` is a MemoryError, and a list is
    never equal to a tuple (both cost the first run)."""
    width, height = image.getSize()
    return ctypes.string_at(image.pixels(), width * height * image.depth())


def convert_texture():
    """The TGA as a PNG, lossless: both read back through MImage and compared
    pixel for pixel."""
    image = om.MImage()
    image.readFromFile(SOURCE_TEXTURE)
    width, height = image.getSize()
    if os.path.exists(TARGET_TEXTURE):
        os.remove(TARGET_TEXTURE)
    image.writeToFile(TARGET_TEXTURE, "png")
    back = om.MImage()
    back.readFromFile(TARGET_TEXTURE)
    same = list(back.getSize()) == [width, height] and \
        pixel_bytes(back) == pixel_bytes(image)
    print("texture %dx%d -> %s, %d bytes (TGA %d), pixels equal: %s" % (
        width, height, TARGET_TEXTURE, os.path.getsize(TARGET_TEXTURE),
        os.path.getsize(SOURCE_TEXTURE), same))
    assert same, "the PNG is not the TGA"


def main():
    assert abs(det3(ROWS) - 1.0) < 1e-9, "the turn must be a rotation"
    fraction = grip_fraction()

    cmds.file(new=True, force=True)
    roots = attach.import_model(SOURCE)
    meshes = attach.mesh_transforms(roots)
    print("source meshes:", meshes)
    keep = [m for m in meshes if m.split("|")[-1].endswith(KEEP)]
    assert len(keep) == 1, keep
    mesh = keep[0]
    for other in meshes:
        if other != mesh:
            cmds.delete(other)
    shape = shape_of(mesh)
    lo, hi, _ = extents(shape)
    print("source extents  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # 1. the quarter turn, frozen into the points
    matrix = [ROWS[0][0], ROWS[0][1], ROWS[0][2], 0.0,
              ROWS[1][0], ROWS[1][1], ROWS[1][2], 0.0,
              ROWS[2][0], ROWS[2][1], ROWS[2][2], 0.0,
              0.0, 0.0, 0.0, 1.0]
    cmds.xform(mesh, matrix=matrix, objectSpace=True)
    freeze(mesh)
    lo, hi, pts = extents(shape)
    print("turned extents  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # 2. the shaft onto the axis (the butt cap and the shaft's bottom ring),
    #    and the origin up the shaft to Spear 01's fraction of the length
    butt = [p for p in pts if p[1] < lo[1] + BUTT]
    cx = sum(p[0] for p in butt) / len(butt)
    cz = sum(p[2] for p in butt) / len(butt)
    grip_y = lo[1] + fraction * (hi[1] - lo[1])
    print("shaft centroid x %.4f z %.4f (%d verts); grip at Y %.3f" % (
        cx, cz, len(butt), grip_y))
    cmds.xform(mesh, translation=(-cx, -grip_y, -cz), objectSpace=True)
    freeze(mesh)
    cmds.xform(mesh, pivots=(0.0, 0.0, 0.0), objectSpace=True)
    cmds.delete(mesh, constructionHistory=True)
    lo, hi, pts = extents(shape)
    butt = [p for p in pts if p[1] < lo[1] + BUTT]
    print("after: shaft centroid x %.5f z %.5f; butt %.3f below the origin, "
          "fraction %.4f" % (sum(p[0] for p in butt) / len(butt),
                             sum(p[2] for p in butt) / len(butt), -lo[1],
                             -lo[1] / (hi[1] - lo[1])))

    # 3. the UV set by a plain name: `UVКарта` reaches Maya as `UV?????`
    sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
    print("uv sets:", sets)
    assert len(sets) == 1, sets
    if sets[0] != "map1":
        cmds.polyUVSet(shape, rename=True, uvSet=sets[0], newUVSet="map1")
    print("uv sets now:", cmds.polyUVSet(shape, query=True, allUVSets=True),
          "uvs:", cmds.polyEvaluate(shape, uvcoord=True))

    # 4. a plain material: Add dresses the weapon in the shipped texture
    #    itself - the file's own points at a D:\ path on nobody's machine
    old = set()
    for sg in set(cmds.listConnections(shape, type="shadingEngine") or []):
        old.update(cmds.listConnections(sg + ".surfaceShader") or [])
        old.add(sg)
    material = cmds.shadingNode("lambert", asShader=True, name=MATERIAL)
    cmds.setAttr(material + ".color", 0.55, 0.55, 0.58, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                   name=MATERIAL + "SG")
    cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    cmds.sets(shape, edit=True, forceElement=sg)
    for node in list(old) + (cmds.ls(type="file") or []) + \
            (cmds.ls(type="place2dTexture") or []):
        if cmds.objExists(node) and node not in cmds.ls(defaultNodes=True):
            cmds.delete(node)
    mesh = cmds.rename(mesh, MESH_NAME)

    # 5. export the mesh alone
    if os.path.exists(TARGET):
        os.remove(TARGET)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportInputConnections -v false")
    mel.eval("FBXExportSmoothingGroups -v true")
    mel.eval("FBXExportInAscii -v false")
    cmds.select(mesh, replace=True)
    mel.eval('FBXExport -f "%s" -s' % TARGET)
    print("wrote", TARGET, os.path.getsize(TARGET), "bytes")

    # 6. the texture
    convert_texture()

    # 7. read it back
    cmds.file(new=True, force=True)
    roots = attach.import_model(TARGET)
    meshes = attach.mesh_transforms(roots)
    shape = shape_of(meshes[0])
    lo, hi, _ = extents(shape)
    print("re-import:", meshes, "extents  X %.3f..%.3f  Y %.3f..%.3f  "
          "Z %.3f..%.3f" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    print("re-import uv sets:", cmds.polyUVSet(shape, query=True,
                                               allUVSets=True))
    print("re-import file nodes:", cmds.ls(type="file"))
    size = [hi[i] - lo[i] for i in range(3)]
    assert len(meshes) == 1, meshes
    assert size[1] > size[0] > size[2], "shaft on Y, width on X, thickness on Z"
    assert hi[1] > -lo[1], "head at +Y"
    print("spear 03 asset OK")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            maya.standalone.uninitialize()
        except Exception:
            pass

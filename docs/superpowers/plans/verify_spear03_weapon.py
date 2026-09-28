"""Spear 03 as a catalog weapon that arrives in its texture, in mayapy
STANDALONE (it adds a rig).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_spear03_weapon.py

Spec: docs/superpowers/specs/2026-09-28-spear03-textured-weapon-design.md.
The frame and the grip are measured on Spear 01 and Spear 03 in the same
run and compared, never typed. Then a real Add onto the rig: the spear on
weapon_r at zero grip, in the one shader with the shipped image on its
colour (the file node sampled against the image's own pixels), outside the
palette; Recolour puts a colour over it; a second Add brings the texture
back on the same material; the sword replaces it.
"""

import ctypes
import os
import sys
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)

from maya_scenesetup import (aim, attach, bonedrive, catalog, character,  # noqa: E402
                             colour, skeleton, weaponspace)

SOURCE_TEXTURE = "C:/!!!Work/MayaScripts/sources/weapons/Halberd_A.tga"
RESULTS = []


def gate(number, ok, text, detail=""):
    RESULTS.append(bool(ok))
    line = "%s %2d %s" % ("PASS" if ok else "FAIL", number, text)
    if detail:
        line += "   [%s]" % detail
    print(line)
    return bool(ok)


def frame(lo, hi):
    """(longest axis, sign of its further end, the other two by size)."""
    size = [hi[i] - lo[i] for i in range(3)]
    order = sorted(range(3), key=lambda i: (-size[i], i))
    blade = order[0]
    tip = 1 if abs(hi[blade]) >= abs(lo[blade]) else -1
    return blade, tip, order[1], order[2], size


def shape_of(node):
    return cmds.listRelatives(node, shapes=True, fullPath=True,
                              noIntermediate=True)[0]


def local_points(node):
    pts = cmds.xform(shape_of(node) + ".vtx[*]", query=True, translation=True,
                     objectSpace=True)
    return list(zip(pts[0::3], pts[1::3], pts[2::3]))


def image(path):
    img = om.MImage()
    img.readFromFile(path)
    width, height = img.getSize()
    return width, height, ctypes.string_at(img.pixels(),
                                           width * height * img.depth())


def look_ok(shader):
    """Every LOOK value on `shader`."""
    for attr, value in colour.LOOK.items():
        got = cmds.getAttr(shader + "." + attr)
        if isinstance(value, tuple):
            if max(abs(x - y) for x, y in zip(got[0], value)) > 1e-6:
                return False
        elif abs(got - value) > 1e-6:
            return False
    return True


def shader_of(node):
    engines = cmds.listSets(object=shape_of(node), type=1) or []
    shaders = cmds.listConnections(engines[0] + ".surfaceShader") if engines else []
    return shaders[0] if shaders else None


def main():
    t_all = time.time()
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")

    spear1 = catalog.by_key("Spear_01")
    spear3 = catalog.by_key("Spear_03")
    sword = catalog.by_key("LongSword_02")
    gate(1, spear3 and spear3.texture and not catalog.missing(spear3)
         and os.path.isfile(spear3.texture),
         "the catalog holds Spear 03, its model and its texture on disk",
         "%s | %s" % (spear3.path, spear3.texture))

    models = {}
    for number, entry in ((2, spear1), (3, spear3)):
        meshes = attach.mesh_transforms(attach.import_model(entry.path))
        gate(number, len(meshes) == 1, "%s imports to exactly one mesh" % entry.label,
             str(meshes))
        models[entry.key] = meshes[0] if meshes else None
    if not all(models.values()):
        return 99
    ext = {key: aim.local_extents(node) for key, node in models.items()}
    f1 = frame(*ext["Spear_01"])
    f3 = frame(*ext["Spear_03"])
    gate(4, f3[:4] == f1[:4] == (1, 1, 0, 2),
         "Spear 03's frame is Spear 01's: shaft Y, head at +Y, width X, thickness Z",
         "spear 01 %s spear 03 %s" % (f1[:4], f3[:4]))
    lo1, hi1 = ext["Spear_01"]
    lo3, hi3 = ext["Spear_03"]
    frac1 = -lo1[1] / (hi1[1] - lo1[1])
    frac3 = -lo3[1] / (hi3[1] - lo3[1])
    gate(5, abs(frac1 - frac3) < 1e-3 and abs(hi3[1] - lo3[1] - 199.62) < 0.1,
         "the grip sits at Spear 01's fraction of the length from the butt",
         "spear 01 %.4f spear 03 %.4f, length %.2f cm, butt %.2f below" % (
             frac1, frac3, hi3[1] - lo3[1], -lo3[1]))
    butt = [p for p in local_points(models["Spear_03"]) if p[1] < lo3[1] + 16.0]
    off = (sum(p[0] for p in butt) / len(butt), sum(p[2] for p in butt) / len(butt))
    gate(6, (off[0] ** 2 + off[1] ** 2) ** 0.5 < 0.01,
         "the shaft is centred on the axis", "x %.5f z %.5f (%d verts)" % (
             off[0], off[1], len(butt)))
    top1, _ = aim.placement(lo1, hi1)
    top3, _ = aim.placement(lo3, hi3)
    gate(7, top1[1] > 0 and top3[1] > 0 and top3[0] == top3[2] == 0,
         "aim.placement puts the top locator past the head on +Y for both",
         "%s / %s" % (["%.1f" % v for v in top1], ["%.1f" % v for v in top3]))
    sets = cmds.polyUVSet(shape_of(models["Spear_03"]), query=True, allUVSets=True)
    gate(8, sets == ["map1"] and cmds.polyEvaluate(
        shape_of(models["Spear_03"]), uvcoord=True) > 0,
         "the shipped model's UVs are in map1 (the source's was UVКарта)", str(sets))
    if os.path.isfile(SOURCE_TEXTURE):
        a = image(SOURCE_TEXTURE)
        b = image(spear3.texture)
        gate(9, a == b, "the shipped PNG is the TGA pixel for pixel",
             "%dx%d, %d bytes of pixels" % (b[0], b[1], len(b[2])))
    else:
        print("SKIP  9 the source TGA is not in Downloads any more")
    cmds.delete(list(models.values()))

    # ------------------------------------------------------------ a real Add
    cmds.file(new=True, force=True)
    text = character.add_character(catalog.default_rig())
    root = skeleton.current_root()
    bone = skeleton.resolve_bone(root, "weapon_r")
    hand = attach.parent_bone(bone)
    gate(10, "added as Manny_Rig" in text and root and bone and hand,
         "the rig added, weapon_r and its hand resolved", "%s / %s" % (bone, hand))
    rig_colours = list(colour.used_colours())
    weapon, note = attach.attach(spear3, hand, bone)
    gate(11, weapon and note == "" and weaponspace.holding_hand(weapon) == hand
         and bonedrive.driving_weapon(bone) == weapon,
         "Add Weapon: the spear is the geometry, in the hand's space, driving weapon_r",
         "%s %r" % (weapon, note))
    w = cmds.xform(weapon, query=True, matrix=True, worldSpace=True)
    b = cmds.xform(bone, query=True, matrix=True, worldSpace=True)
    err = max(abs(w[i] - b[i]) for i in range(16))
    gate(12, err < 1e-4, "at zero grip the spear stands ON weapon_r", "%.2e" % err)

    shader = shader_of(weapon)
    files = cmds.listConnections(shader + ".color", type="file") or []
    look = look_ok(shader)
    gate(13, cmds.nodeType(shader) == colour.SHADER and look and len(files) == 1,
         "the one shader wearing LOOK, a file node on its colour",
         "%s (%s), files %s" % (shader, cmds.nodeType(shader), files))
    path = cmds.getAttr(files[0] + ".fileTextureName") if files else ""
    size = (cmds.getAttr(files[0] + ".outSizeX"), cmds.getAttr(files[0] + ".outSizeY")) \
        if files else (0, 0)
    gate(14, os.path.normcase(path) == os.path.normcase(spear3.texture)
         and size == (2048.0, 2048.0),
         "the file node reads the shipped image, 2048 x 2048", "%s %s" % (path, size))
    # the image the file node samples is the PNG's own pixels
    width, height, pixels = image(spear3.texture)

    def texel(col, row):
        index = (row * width + col) * 4
        return [pixels[index + k] / 255.0 for k in range(3)]

    # sampled at texel CENTRES (colorAtPoint filters between neighbours),
    # against the image's row as MImage stores it and the row flipped, so a
    # texture read upside down cannot pass
    worst, flipped, varied = 0.0, 0.0, set()
    for col, row in ((266, 430), (1065, 983), (1577, 1843), (635, 1351),
                     (1843, 246), (400, 1700)):
        u, v = (col + 0.5) / width, (row + 0.5) / height
        got = cmds.colorAtPoint(files[0], output="RGB", u=u, v=v)
        worst = max(worst, max(abs(g - x) for g, x in zip(got, texel(col, row))))
        flipped = max(flipped, max(abs(g - x) for g, x in zip(
            got, texel(col, height - 1 - row))))
        varied.add(tuple(round(g, 2) for g in got))
    gate(15, worst < 0.01 and len(varied) > 3,
         "the texture samples ARE the image's pixels (not a flat default)",
         "worst %.4f over 6 texels (the rows flipped: %.4f), %d distinct" % (
             worst, flipped, len(varied)))
    gate(16, cmds.attributeQuery(colour.TEXTURE_MARKER, node=shader, exists=True)
         and not colour.is_ours(shader) and colour.used_colours() == rig_colours,
         "marked textured, outside the palette: the colour scan still sees only the rig",
         "%s vs %s" % (colour.used_colours(), rig_colours))

    rgb = colour.free_colour().rgb
    colour.paint_nodes([weapon], rgb, spear3.key)
    painted = shader_of(weapon)
    gate(17, colour.is_ours(painted) and not cmds.listConnections(
        painted + ".color", type="file")
         and colour.same_colour(colour.colour_plug(painted), rgb),
         "Recolour puts a colour material over the texture (the animator's ruling)",
         "%s %s" % (painted, colour.colour_name(rgb)))

    again, _ = attach.attach(spear3, hand, bone)
    textured = [m for m in cmds.ls(materials=True)
                if cmds.attributeQuery(colour.TEXTURE_MARKER, node=m, exists=True)]
    # ours only: the rig file carries its own file nodes (Manny's maps)
    ours = [f for f in cmds.ls(type="file") or []
            if (cmds.getAttr(f + ".fileTextureName") or "").replace("\\", "/")
            .lower() == spear3.texture.lower()]
    gate(18, shader_of(again) == shader and textured == [shader] and len(ours) == 1,
         "a second Add brings the texture back on the SAME material, one file node",
         "%s, textured %s, ours %s" % (shader_of(again), textured, ours))

    sword_node, _ = attach.attach(sword, hand, bone)
    gate(19, sword_node and not cmds.objExists(again)
         and bonedrive.driving_weapon(bone) == sword_node
         and colour.is_ours(shader_of(sword_node)),
         "the sword replaces the spear, in a palette colour as ever", str(sword_node))

    failed = RESULTS.count(False)
    print("\n%d of %d gates failed (%.0f s)" % (failed, len(RESULTS), time.time() - t_all))
    return failed


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 99
    sys.stdout.flush()
    try:
        maya.standalone.uninitialize()
    except Exception:
        pass
    os._exit(1 if code else 0)

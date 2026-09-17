"""The dagger as a catalog weapon, in mayapy STANDALONE (it adds a rig).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_dagger_weapon.py

What it proves (spec: docs/superpowers/specs/2026-09-17-dagger-weapon-design.md):
the shipped Dagger_01.fbx imports to ONE mesh transform; its axes are the
sword's -- measured on both files in the same run and compared, never
typed: the longest local axis, the sign of its further end (the tip), the
order of the other two; the grip's centroid lies on the blade's axis;
`aim.placement` puts the top locator on the same axis for both; a real Add
onto the rig lands the dagger under the hand driving weapon_r, exactly as
the sword does, and the sword replaces it.
"""

import os
import sys
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)

from maya_scenesetup import aim, attach, bonedrive, catalog, character, skeleton  # noqa: E402

RESULTS = []


def gate(number, ok, text, detail=""):
    RESULTS.append(bool(ok))
    line = "%s %2d %s" % ("PASS" if ok else "FAIL", number, text)
    if detail:
        line += "   [%s]" % detail
    print(line)
    return bool(ok)


def extents(model):
    lo, hi = aim.local_extents(model)
    return list(lo), list(hi)


def frame(lo, hi):
    """(longest axis, sign of its further end, the other two by size)."""
    size = [hi[i] - lo[i] for i in range(3)]
    order = sorted(range(3), key=lambda i: (-size[i], i))
    blade = order[0]
    tip = 1 if abs(hi[blade]) >= abs(lo[blade]) else -1
    return blade, tip, order[1], order[2], size


def main():
    t_all = time.time()
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")

    sword = catalog.by_key("LongSword_02")
    dagger = catalog.by_key("Dagger_01")
    gate(1, sword and dagger
         and catalog.labels() == ["Long Sword 02", "Spear 01", "Dagger 01"]
         and not catalog.missing(dagger),
         "the catalog holds the sword, the spear and the dagger, the dagger on disk",
         str(catalog.labels()))

    models = {}
    for entry in (sword, dagger):
        roots = attach.import_model(entry.path)
        meshes = attach.mesh_transforms(roots)
        gate(2 if entry is sword else 3, len(meshes) == 1,
             "%s imports to exactly one mesh transform" % entry.label,
             "%s -> %s" % (roots, meshes))
        models[entry.key] = meshes[0] if meshes else None
    if not all(models.values()):
        return 99
    sw_lo, sw_hi = extents(models["LongSword_02"])
    dg_lo, dg_hi = extents(models["Dagger_01"])
    sw = frame(sw_lo, sw_hi)
    dg = frame(dg_lo, dg_hi)
    print("    sword   lo %s hi %s" % (["%.2f" % v for v in sw_lo], ["%.2f" % v for v in sw_hi]))
    print("    dagger  lo %s hi %s" % (["%.2f" % v for v in dg_lo], ["%.2f" % v for v in dg_hi]))
    gate(4, sw[0] == 1 and sw[1] == 1,
         "the sword: longest axis Y, tip at +Y (the 2026-08-17 measurement)",
         "axis %d tip %+d" % (sw[0], sw[1]))
    gate(5, dg[0] == sw[0] and dg[1] == sw[1],
         "the dagger's longest axis and tip sign are the sword's",
         "dagger axis %d tip %+d" % (dg[0], dg[1]))
    gate(6, (dg[2], dg[3]) == (sw[2], sw[3]) == (0, 2),
         "width on X and thickness on Z for both", "sword %s dagger %s" % (sw[2:4], dg[2:4]))
    gate(7, dg_hi[1] > 80 and dg_lo[1] < -25 and abs(dg_hi[1] - dg_lo[1] - 114.26) < 0.5,
         "the dagger is the 114 cm model, tip at +Y, grip below the origin",
         "Y %.2f..%.2f" % (dg_lo[1], dg_hi[1]))
    # the grip is centred on the blade's axis, like the sword's: the
    # centroid of the vertices between the guard and the pommel (y in
    # -19..-2 after the turn) lies within 0.05 cm of x = z = 0. The sword's
    # own grip measures the same way in the same run.
    offsets = {}
    for key, band in (("Dagger_01", (-19.0, -2.0)), ("LongSword_02", (-19.0, -7.0))):
        shape = cmds.listRelatives(models[key], shapes=True, fullPath=True,
                                   noIntermediate=True)[0]
        pts = cmds.xform(shape + ".vtx[*]", query=True, translation=True, objectSpace=True)
        xyz = [p for p in zip(pts[0::3], pts[1::3], pts[2::3]) if band[0] < p[1] < band[1]]
        cx = sum(p[0] for p in xyz) / len(xyz)
        cz = sum(p[2] for p in xyz) / len(xyz)
        offsets[key] = ((cx * cx + cz * cz) ** 0.5, len(xyz))
    gate(8, offsets["Dagger_01"][0] < 0.05 and offsets["LongSword_02"][0] < 0.05,
         "the grip's centroid lies on the axis for both (within 0.05 cm)",
         "dagger %.4f (%d verts), sword %.4f (%d verts)" % (
             offsets["Dagger_01"] + offsets["LongSword_02"]))
    top_sw, side_sw = aim.placement(sw_lo, sw_hi)
    top_dg, side_dg = aim.placement(dg_lo, dg_hi)
    gate(9, top_sw[1] > 0 and top_dg[1] > 0
         and top_sw[0] == top_sw[2] == 0 == top_dg[0] == top_dg[2],
         "aim.placement puts the top locator past the tip on +Y for both",
         "sword %s dagger %s" % (["%.1f" % v for v in top_sw], ["%.1f" % v for v in top_dg]))
    cmds.delete([m for m in models.values()])

    # ------------------------------------------------------------ a real Add
    cmds.file(new=True, force=True)
    text = character.add_character(catalog.default_rig())
    root = skeleton.current_root()
    bone = skeleton.resolve_bone(root, "weapon_r")
    hand = attach.parent_bone(bone)
    gate(10, "added as Manny_Rig" in text and root and bone and hand,
         "the rig added, weapon_r and its hand resolved", "%s / %s" % (bone, hand))
    weapon, note = attach.attach(dagger, hand, bone)
    gate(11, weapon and cmds.objExists(weapon) and note == "" and weapon.startswith(hand + "|")
         and cmds.listRelatives(weapon, children=True, type="mesh"),
         "Add Weapon: the dagger IS the geometry, parented under the hand, no group",
         "%s %r" % (weapon, note))
    gate(12, bonedrive.driving_weapon(bone) == weapon, "the dagger drives weapon_r",
         str(bonedrive.driving_weapon(bone)))
    w = cmds.xform(weapon, query=True, matrix=True, worldSpace=True)
    b = cmds.xform(bone, query=True, matrix=True, worldSpace=True)
    err = max(abs(x - y) for x, y in zip(w, b))
    gate(13, err < 1e-4, "at the zero grip the dagger's origin and axes sit ON weapon_r",
         "worst %.6f" % err)
    marker = cmds.attributeQuery(bonedrive.MARKER, node=weapon, exists=True)
    gate(14, marker and cmds.getAttr(weapon + "." + bonedrive.MARKER) == "Dagger_01",
         "the marker names the dagger's key, so the grip is remembered per weapon",
         str(cmds.getAttr(weapon + "." + bonedrive.MARKER) if marker else None))
    sword_node, _ = attach.attach(sword, hand, bone)
    gate(15, sword_node and cmds.objExists(sword_node) and not cmds.objExists(weapon)
         and bonedrive.driving_weapon(bone) == sword_node,
         "Add with the sword REPLACES the dagger (one weapon per bone)", str(sword_node))

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

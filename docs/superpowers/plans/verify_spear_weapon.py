"""The spear as a catalog weapon, in mayapy STANDALONE (it adds a rig).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_spear_weapon.py

What it proves (spec: docs/superpowers/specs/2026-09-08-spear-weapon-design.md):
the shipped Spear_01.fbx imports to ONE mesh transform; its axes are the
sword's -- measured on both files in the same run and compared, never typed:
the longest local axis, the sign of its further end (the tip), the order of
the other two; the origin lies on the shaft; `aim.placement` puts the top
locator on the same axis for both; a real Add onto the rig lands the spear
under the hand driving weapon_r, exactly as the sword does.
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
    spear = catalog.by_key("Spear_01")
    gate(1, sword and spear and catalog.labels() == ["Long Sword 02", "Spear 01"]
         and not catalog.missing(spear), "the catalog holds the sword and the spear, both on disk",
         str(catalog.labels()))

    models = {}
    for entry in (sword, spear):
        roots = attach.import_model(entry.path)
        meshes = attach.mesh_transforms(roots)
        gate(2 if entry is sword else 3, len(meshes) == 1,
             "%s imports to exactly one mesh transform" % entry.label, "%s -> %s" % (roots, meshes))
        models[entry.key] = meshes[0] if meshes else None
    if not all(models.values()):
        return 99
    sw_lo, sw_hi = extents(models["LongSword_02"])
    sp_lo, sp_hi = extents(models["Spear_01"])
    sw = frame(sw_lo, sw_hi)
    sp = frame(sp_lo, sp_hi)
    print("    sword  lo %s hi %s" % (["%.2f" % v for v in sw_lo], ["%.2f" % v for v in sw_hi]))
    print("    spear  lo %s hi %s" % (["%.2f" % v for v in sp_lo], ["%.2f" % v for v in sp_hi]))
    gate(4, sw[0] == 1 and sw[1] == 1, "the sword: longest axis Y, tip at +Y (the 2026-08-17 measurement)",
         "axis %d tip %+d" % (sw[0], sw[1]))
    gate(5, sp[0] == sw[0] and sp[1] == sw[1], "the spear's longest axis and tip sign are the sword's",
         "spear axis %d tip %+d" % (sp[0], sp[1]))
    gate(6, (sp[2], sp[3]) == (sw[2], sw[3]) == (0, 2),
         "width on X and thickness on Z for both", "sword %s spear %s" % (sw[2:4], sp[2:4]))
    gate(7, sp_hi[1] > 200 and sp_lo[1] < -50 and abs(sp_hi[1] - sp_lo[1] - 266.18) < 0.5,
         "the spear is the 266 cm model, head at +Y, butt below the origin",
         "Y %.2f..%.2f" % (sp_lo[1], sp_hi[1]))
    # the origin lies on the shaft's AXIS: the shaft is straight along Y, so the
    # butt cap's centroid (the only vertices below the origin) and the head
    # base's centroid both sit on that axis -- both within 3 cm of x = z = 0.
    # (Individual vertices are 7-14 cm off-axis: the cap is 13 cm wide and the
    # blade 22; a gate on vertex radius measured the head, not the origin.)
    shape = cmds.listRelatives(models["Spear_01"], shapes=True, fullPath=True, noIntermediate=True)[0]
    pts = cmds.xform(shape + ".vtx[*]", query=True, translation=True, objectSpace=True)
    xyz = list(zip(pts[0::3], pts[1::3], pts[2::3]))
    butt = [p for p in xyz if p[1] < -30]
    base = [p for p in xyz if 90 < p[1] < 120]
    offs = []
    for group in (butt, base):
        if group:
            cx = sum(p[0] for p in group) / len(group)
            cz = sum(p[2] for p in group) / len(group)
            offs.append((cx * cx + cz * cz) ** 0.5)
    gate(8, len(offs) == 2 and max(offs) < 3.0,
         "the origin sits on the shaft's axis (butt-cap and head-base centroids within 3 cm of it)",
         "%d/%d verts, centroid offsets %s" % (len(butt), len(base), ["%.2f" % o for o in offs]))
    top_sw, side_sw = aim.placement(sw_lo, sw_hi)
    top_sp, side_sp = aim.placement(sp_lo, sp_hi)
    gate(9, top_sw[1] > 0 and top_sp[1] > 0 and top_sw[0] == top_sw[2] == 0 == top_sp[0] == top_sp[2],
         "aim.placement puts the top locator past the tip on +Y for both",
         "sword %s spear %s" % (["%.1f" % v for v in top_sw], ["%.1f" % v for v in top_sp]))
    cmds.delete([m for m in models.values()])
    for ns in ("LongSword_02", "Spear_01"):
        pass

    # ------------------------------------------------------------ a real Add
    cmds.file(new=True, force=True)
    text = character.add_character(catalog.default_rig())
    root = skeleton.current_root()
    bone = skeleton.resolve_bone(root, "weapon_r")
    hand = attach.parent_bone(bone)
    gate(10, "added as Manny_Rig" in text and root and bone and hand, "the rig added, weapon_r and its hand resolved",
         "%s / %s" % (bone, hand))
    weapon, note = attach.attach(spear, hand, bone)
    gate(11, weapon and cmds.objExists(weapon) and note == "" and weapon.startswith(hand + "|")
         and cmds.listRelatives(weapon, children=True, type="mesh"),
         "Add Weapon: the spear IS the geometry, parented under the hand, no group", "%s %r" % (weapon, note))
    gate(12, bonedrive.driving_weapon(bone) == weapon, "the spear drives weapon_r", str(bonedrive.driving_weapon(bone)))
    w = cmds.xform(weapon, query=True, matrix=True, worldSpace=True)
    b = cmds.xform(bone, query=True, matrix=True, worldSpace=True)
    err = max(abs(x - y) for x, y in zip(w, b))
    gate(13, err < 1e-4, "at the zero grip the spear's origin and axes sit ON weapon_r", "worst %.6f" % err)
    marker = cmds.attributeQuery(bonedrive.MARKER, node=weapon, exists=True)
    gate(14, marker and cmds.getAttr(weapon + "." + bonedrive.MARKER) == "Spear_01",
         "the marker names the spear's key, so the grip is remembered per weapon",
         str(cmds.getAttr(weapon + "." + bonedrive.MARKER) if marker else None))
    # replace with the sword and back: one weapon per bone, both from the table
    sword_node, _ = attach.attach(sword, hand, bone)
    gate(15, sword_node and cmds.objExists(sword_node) and not cmds.objExists(weapon)
         and bonedrive.driving_weapon(bone) == sword_node,
         "Add with the sword REPLACES the spear (one weapon per bone)", str(sword_node))

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

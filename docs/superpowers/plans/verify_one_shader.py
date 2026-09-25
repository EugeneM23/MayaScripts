"""The one shader on every model and rig we put into the scene (2026-09-25 evening).

    mayapy verify_one_shader.py

The animator: «нужно на все наши модели и риги настроить единый шейдер, такой чтобы он смотрелся
хорошо в мае и в каскадере. Сейчас при экспорте в каскадер модель выглядит темной и на модели много
материалов». mayapy STANDALONE, an empty scene: every catalog character through Add Character, every
catalog weapon through Add onto the Creep rig's hand. Gates:

1. every character's renderable meshes wear ONE material, SHADER, wearing LOOK, in the colour Add
   gave it -- the asset's own many materials (the Orc's five per-face sets, the Creep body's none,
   Manny's MaterialX) no longer on any face;
2. every weapon the same;
3. an FBX of one character's meshes (FBXExport -s, what an artist does by hand) carries that one
   material with Cascadeur's own numbers: phong, specular 0.2, shininess 20, no reflection, the
   colour at full (no DiffuseFactor below 1);
4. the animation export's top node is `Armature`.
"""
import os
import sys
import tempfile

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("fbxmaya", "matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
from maya_scenesetup import attach, catalog, character, colour
from maya_uebridge import animexport, fbxlayout
import maya_rigs

OUT = tempfile.mkdtemp(prefix="one_shader_").replace("\\", "/")
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def worn(shapes):
    """{material: [shape leaf]} over every shading assignment of `shapes`, whole or per face."""
    out = {}
    for s in shapes:
        for sg in set(cmds.listConnections(s, type="shadingEngine") or []):
            for m in cmds.listConnections(sg + ".surfaceShader") or ["<none>"]:
                out.setdefault(m, []).append(s.split("|")[-1])
        if not cmds.listConnections(s, type="shadingEngine"):
            out.setdefault("<none>", []).append(s.split("|")[-1])
    return out


def looks_right(material):
    if not cmds.objExists(material) or cmds.nodeType(material) != colour.SHADER:
        return False
    for attr, value in colour.LOOK.items():
        got = cmds.getAttr(material + "." + attr)
        got = got[0] if isinstance(got, list) else got
        want = value if isinstance(value, tuple) else (value,)
        got = got if isinstance(got, tuple) else (got,)
        if max(abs(a - b) for a, b in zip(got, want)) > 1e-5:
            return False
    return True


cmds.file(new=True, force=True)
cmds.currentUnit(time="ntsc")
bad, report = [], []
for entry in catalog.CHARACTERS:
    before = set(cmds.ls(type="mesh", long=True))
    print(character.add_character(entry))
    shapes = [s for s in cmds.ls(type="mesh", long=True, noIntermediate=True) if s not in before]
    w = worn(shapes)
    ok = len(w) == 1 and looks_right(list(w)[0]) and len(list(w.values())[0]) == len(shapes)
    report.append("%s: %d meshes wear %s" % (entry.key, len(shapes), dict((k, len(v)) for k, v in w.items())))
    if not ok:
        bad.append(entry.key)
gate(1, not bad, "every character: " + "; ".join(report) + ("  -- BAD: %s" % bad if bad else ""))

creep = maya_rigs.find("Creep_Rig")
bones = dict((p.split("|")[-1].split(":")[-1], p)
             for p in cmds.listRelatives(creep.skeleton_root, allDescendents=True, type="joint", fullPath=True))
hand, bone = bones["hand_r"], bones["weapon_r"]
bad, report = [], []
for entry in catalog.WEAPONS:
    weapon, note = attach.attach(entry, hand, bone, (0, 0, 0), (0, 0, 0))
    shapes = cmds.listRelatives(weapon, shapes=True, fullPath=True, noIntermediate=True) or []
    w = worn(shapes)
    ok = len(w) == 1 and looks_right(list(w)[0])
    report.append("%s wears %s" % (entry.key, list(w)))
    if not ok:
        bad.append(entry.key)
gate(2, not bad, "every weapon: " + "; ".join(report) + ("  -- BAD: %s" % bad if bad else ""))

# an artist's own export of one character's meshes: what reaches Cascadeur is what they wear
orc = maya_rigs.find("Orc_Rig")
orc_meshes = [cmds.listRelatives(s, parent=True, fullPath=True)[0] for s in cmds.ls(type="mesh", long=True, noIntermediate=True)
              if s.startswith(orc.group + "|")]
path = OUT + "/orc_meshes.fbx"
mel.eval("FBXResetExport; FBXExportSkins -v false; FBXExportShapes -v false; FBXExportInAscii -v true;")
cmds.select(orc_meshes, replace=True)
mel.eval('FBXExport -f "%s" -s' % path)
text = open(path, encoding="utf-8", errors="replace").read()
import re
# an Objects block, `\tMaterial: <id>, "Material::<name>", "" {` -- not LayerElementMaterial
blocks = re.split(r'\n\tMaterial: \d+, "Material::', text)[1:]
props = blocks[0][:3000] if blocks else ""


def prop(name):
    import re
    m = re.search(r'P: "%s",[^\n]*?,([-0-9.e, ]+)\n' % name, props)
    return [float(x) for x in m.group(1).split(",") if x.strip()] if m else None


shading = 'ShadingModel: "phong"' in props
got = dict((k, prop(k)) for k in ("DiffuseColor", "DiffuseFactor", "SpecularColor", "ShininessExponent", "Shininess",
                                  "ReflectionFactor"))
# FBX leaves a property at its default out of the file: DiffuseFactor 1, ShininessExponent 20
spec = [round(v, 6) for v in got["SpecularColor"] or []]
ok = (len(blocks) == 1 and shading and (got["DiffuseFactor"] in (None, [1.0])) and spec == [0.2, 0.2, 0.2]
      and (got["ShininessExponent"] or [20.0]) == [20.0] and got["Shininess"] == [20.0]
      and got["ReflectionFactor"] in (None, [0.0]))
gate(3, ok, "the Orc's meshes exported by hand: %d material(s), phong %s, %s" % (len(blocks), shading, got))

anim = OUT + "/creep_anim.fbx"
cmds.select(clear=True)
info = animexport.export_hierarchy(anim, root=creep.skeleton_root, start=0, end=1)
cmds.file(new=True, force=True)
mel.eval("FBXResetImport; FBXImportMode -v add;")
mel.eval('FBXImport -f "%s"' % anim)
tops = cmds.ls(assemblies=True)
gate(4, info["wrapper"] == fbxlayout.WRAPPER_NAME == "Armature" and "Armature" in tops
     and cmds.listRelatives(cmds.ls("root", type="joint", long=True)[0], parent=True) == ["Armature"],
     "the animation export: wrapper %r, top nodes %s" % (info["wrapper"], [t for t in tops if t not in ("persp", "top", "front", "side")]))
print("RESULT: %d of 4 gates failed %s" % (len(FAILS), FAILS))

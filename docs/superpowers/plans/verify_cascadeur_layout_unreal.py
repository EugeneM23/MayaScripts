"""Unreal reads Cascadeur's layout as it reads the plain one -- measured through its own import (2026-09-25).

    mayapy verify_cascadeur_layout_unreal.py

mayapy STANDALONE (it adds a rig and retargets), with the animator's Unreal editor open and
reached through `uelink`, as the bridge does. Everything destructive happens to a SANDBOX asset
duplicated into `/Game/__bridge_verify` and deleted again (trap 46: the editor's own Perforce
integration makes transient p4 noise around it).

1. a clip on the project's skeleton exported out of Unreal, retargeted onto a fresh Manny_Rig;
   the rig's skeleton is the ground truth;
2. exported in Cascadeur's layout (wrapper `Manny`) and in the plain layout (the control);
3. each reimported into the sandbox asset, the sandbox exported back out of Unreal, and read
   beside the ground truth: every bone's world per frame;
4. no bone named for the wrapper appears in what Unreal wrote, and the editor log carries no
   warning naming it;
5. the sandbox deleted.
"""
import json
import math
import os
import sys
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

PLUGIN = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, PLUGIN)
for p in ("fbxmaya", "matrixNodes", "quatNodes"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
from maya_scenesetup import catalog, character
from maya_uebridge import animexport, animimport, uelink, uescripts, window
import maya_rigs
import maya_rig_retarget as rr

VERIFY_DIR = "/Game/__bridge_verify"
VERIFY_PKG = VERIFY_DIR + "/AS_VerifyCascadeurLayout"
SKELETON = "SK_Mannequin_proto"
TMP = window.temp_folder()
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def ang(a, b):
    qa = om.MTransformationMatrix(a).rotation(asQuaternion=True)
    qb = om.MTransformationMatrix(b).rotation(asQuaternion=True)
    q = qa.inverse() * qb
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(m):
    return om.MVector(m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))


def fresh():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")


def run(source, name, project):
    out = os.path.join(TMP, name).replace("\\", "/")
    return uelink.run_script(source, out, project=project)


def asset_script(out, body):
    return ("import json, traceback\nimport unreal\n_OUT = %s\n"
            "result = {\"ok\": False, \"error\": \"\"}\n"
            "try:\n    lib = unreal.EditorAssetLibrary\n%s    result[\"ok\"] = True\n"
            "except Exception:\n    result[\"error\"] = traceback.format_exc()\n"
            "finally:\n    with open(_OUT, \"w\") as handle:\n        json.dump(result, handle)\n"
            "    print(\"__UEBRIDGE_DONE__\")\n" % (json.dumps(out), body))


def duplicate(source_package, project):
    out = os.path.join(TMP, "vcl_dup.json").replace("\\", "/")
    body = ("    if lib.does_asset_exist(%(d)s):\n        lib.delete_asset(%(d)s)\n"
            "    if lib.duplicate_asset(%(s)s, %(d)s) is None:\n        raise RuntimeError('duplicate failed')\n"
            "    lib.save_asset(%(d)s, only_if_is_dirty=False)\n"
            % {"s": json.dumps(source_package), "d": json.dumps(VERIFY_PKG)})
    return uelink.run_script(asset_script(out, body), out, project=project)


def delete_sandbox(project):
    out = os.path.join(TMP, "vcl_del.json").replace("\\", "/")
    body = ("    if lib.does_asset_exist(%(d)s):\n        lib.delete_asset(%(d)s)\n"
            "    if lib.does_directory_exist(%(f)s):\n        lib.delete_directory(%(f)s)\n"
            % {"d": json.dumps(VERIFY_PKG), "f": json.dumps(VERIFY_DIR)})
    return uelink.run_script(asset_script(out, body), out, project=project)


def read_back(path, namespace):
    cmds.namespace(add=namespace)
    cmds.namespace(set=":" + namespace)
    try:
        mel.eval("FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;")
        mel.eval('FBXImport -f "%s";' % path.replace("\\", "/"))
    finally:
        cmds.namespace(set=":")
    root = cmds.ls(namespace + ":root", type="joint", long=True)[0]
    return dict((p.split("|")[-1].split(":")[-1], p)
                for p in [root] + (cmds.listRelatives(root, ad=True, type="joint", fullPath=True) or []))


def track(bones, frames):
    out = {}
    for t in frames:
        cmds.currentTime(t)
        out[t] = dict((n, wm(p)) for n, p in bones.items())
    return out


cached, project_path, choice, content_dir = window.load_cache()
pool = [r for r in cached if r.skeleton == SKELETON and r.frames and 40 <= r.frames <= 120
        and "/Additive/" not in r.package and "Offset" not in r.name]
source = sorted(pool, key=lambda r: (r.frames, r.name))[len(pool) // 2] if pool else None
print("source:", source.package if source else None, source.frames if source else None, "| project:", choice)
log = os.path.join(os.path.dirname(os.path.normpath(content_dir)), "Saved", "Logs", "Atone.log")
log_start = os.path.getsize(log) if os.path.isfile(log) else 0

try:
    uelink.discover_nodes(timeout=6)
    # 1. the clip out of Unreal, onto a fresh Manny rig
    src_fbx = os.path.join(TMP, "vcl_source.fbx").replace("\\", "/")
    reply = run(uescripts.export_script(os.path.join(TMP, "vcl_export.json").replace("\\", "/"),
                                        source.package, src_fbx), "vcl_export.json", choice)
    gate(1, bool(reply.get("ok")) and os.path.isfile(src_fbx),
         "the clip %s exported out of Unreal: %s" % (source.name, str(reply.get("error", ""))[:120]))
    fresh()
    print(character.add_character(catalog.character_by_key("Manny_Rig")))
    rig = maya_rigs.find("Manny_Rig")
    animimport.import_clip(src_fbx, namespace="src", merge=False)
    first, last = cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)
    cmds.select(cmds.ls("Manny_Rig:Main")[0], cmds.ls("src:root", type="joint", long=True)[0])
    ok, text = rr.run_retarget()
    print("retarget:", ok, text.splitlines()[0][:140])
    frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 10))))
    truth_bones = dict((p.split("|")[-1].split(":")[-1], p) for p in
                       [rig.skeleton_root] + cmds.listRelatives(rig.skeleton_root, ad=True, type="joint", fullPath=True))
    truth = track(truth_bones, frames)
    ours = {}
    for layout in ("cascadeur", "plain"):
        path = os.path.join(TMP, "vcl_ours_%s.fbx" % layout).replace("\\", "/")
        cmds.select(clear=True)
        info = animexport.export_hierarchy(path, root=rig.skeleton_root, layout=layout)
        ours[layout] = (path, info)
    gate(2, ours["cascadeur"][1]["layout"] == "cascadeur" and ours["cascadeur"][1]["wrapper"] == "Manny"
         and ours["plain"][1]["layout"] == "plain",
         "our two files: %s / %s" % ((ours["cascadeur"][1]["layout"], ours["cascadeur"][1]["wrapper"]),
                                     ours["plain"][1]["layout"]))

    # 2-3. each into the sandbox, back out of Unreal, beside the truth
    result = {}
    for layout in ("cascadeur", "plain"):
        dup = duplicate(source.package, choice)
        if not dup.get("ok"):
            gate(3, False, "sandbox duplicate: %s" % str(dup.get("error"))[:160])
            break
        rep = run(uescripts.reimport_script(os.path.join(TMP, "vcl_re.json").replace("\\", "/"),
                                            VERIFY_PKG, ours[layout][0]), "vcl_re.json", choice)
        back_fbx = os.path.join(TMP, "vcl_back_%s.fbx" % layout).replace("\\", "/")
        exp = run(uescripts.export_script(os.path.join(TMP, "vcl_back.json").replace("\\", "/"),
                                          VERIFY_PKG, back_fbx), "vcl_back.json", choice)
        result[layout] = {"reimport": rep, "export": exp, "fbx": back_fbx}
        print("%s: reimport ok=%s saved=%s frames=%s notes=%s error=%s" % (
            layout, rep.get("ok"), rep.get("saved"), rep.get("frames"), rep.get("notes"), str(rep.get("error"))[:120]))

    for n, layout in ((4, "cascadeur"), (5, "plain")):
        if layout not in result:
            continue
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        back = read_back(result[layout]["fbx"], "U")
        got = track(back, frames)
        worst_p = worst_r = 0.0
        where = ""
        for t in frames:
            for name, m in truth[t].items():
                if name in got[t]:
                    p = (pos(m) - pos(got[t][name])).length()
                    r = ang(m, got[t][name])
                    if p > worst_p:
                        worst_p, where = p, "%s@%g" % (name, t)
                    worst_r = max(worst_r, r)
        extra = sorted(set(back) - set(truth_bones))
        result[layout]["worst"] = (worst_p, worst_r)
        gate(n, bool(result[layout]["reimport"].get("ok")) and worst_p < 0.5 and worst_r < 1.0 and not extra
             and "Manny" not in back,
             "%s layout through Unreal: every bone's world on ours to %.4f cm (%s) and %.4f deg; bones Unreal "
             "added: %s" % (layout, worst_p, where, worst_r, extra))
    if "cascadeur" in result and "plain" in result:
        (cp, cr), (pp, pr) = result["cascadeur"]["worst"], result["plain"]["worst"]
        gate(6, abs(cp - pp) < 0.05 and abs(cr - pr) < 0.1,
             "Cascadeur's layout reads in Unreal as the plain one does: %.4f / %.4f cm, %.4f / %.4f deg"
             % (cp, pp, cr, pr))
    text = ""
    if os.path.isfile(log):
        with open(log, "rb") as handle:
            handle.seek(log_start)
            text = handle.read().decode("utf-8", "replace")
    suspicious = [l for l in text.splitlines() if ("Manny" in l and ("bone" in l.lower() or "skeleton" in l.lower()))
                  or ("Warning" in l and "FBX" in l)]
    gate(7, not [l for l in suspicious if "Manny" in l],
         "the editor log since the start: %d FBX warning line(s), none naming the wrapper%s"
         % (len(suspicious), (" -- " + " | ".join(l.strip()[:140] for l in suspicious[:4])) if suspicious else ""))
except Exception:
    FAILS.append("raised")
    traceback.print_exc()
finally:
    try:
        cleanup = delete_sandbox(choice)
        gate(8, bool(cleanup.get("ok")), "the sandbox deleted: %s" % str(cleanup.get("error", ""))[:120])
    except Exception:
        FAILS.append("cleanup raised")
        traceback.print_exc()
print("RESULT: %d failed %s" % (len(FAILS), FAILS))

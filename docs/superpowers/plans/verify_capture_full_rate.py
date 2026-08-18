"""Live proof: Build reproduces a fast imported clip on EVERY frame.

OverRig's chain capture snaps its aim helpers on every second frame and
interpolates between (double `$i++`, base_OverRig_scripts.mel ~5404), which
put up to 20.3 cm of error on the odd frames of a sword-attack clip. The fix
runs the capture in doubled time. This script is the regression gate:

  1  teardown whatever rig exists
  2  merge the clip onto the skeleton through the bridge's own path
  3  import the same FBX as a namespaced reference skeleton
  4  press the real Build (fkcontrols.rebuild, hybrid)
  5  compare every shared bone against the reference on every frame,
     odd and even reported separately
  6  the attach weight and the key grid are checked explicitly
  7  the merge-over-rig guard is proved by attempting exactly that

Run in the Manny scene with the command port open. The clip FBX must exist in
%TEMP%/maya_uebridge (any UE clip re-exported by the bridge works; edit FBX
below to point at another one).
"""

import os
import sys

sys.path.append(r"C:/!!!Work/MayaScripts")

import maya.cmds as cmds

from maya_overrig import builder, fkcontrols, naming, picker_window
from maya_uebridge import animimport

FBX = os.path.join(os.environ["TEMP"], "maya_uebridge",
                   "AS_Longsword_Attack_Back_Light_Thrust_1P.fbx")
NS = "RPREF"

PASSED = []
FAILED = []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  [{0}] {1}   {2}".format("PASS" if ok else "FAIL", name, detail))


print("=== 0. the scene ===")
root = picker_window.bound_root()
if not root:
    roots = builder.character_roots()
    root = roots[0] if len(roots) == 1 else None
scene_map = naming.hierarchy_map(root)
print("root:", root, " bones:", len(scene_map), " fbx:", os.path.isfile(FBX))

print("\n=== 1. teardown ===")
if fkcontrols.has_fk():
    print("bake_fk ->", fkcontrols.bake_fk(scene_map)[1][:70])
if builder.has_build():
    print("bake_limbs ->", builder.bake_limbs(
        scene_map, builder.built_limbs()).message[:70])
gate("teardown leaves no rig",
     not fkcontrols.built_fk_chains() and not builder.built_limbs())

print("\n=== 2. the clip, merged fresh ===")
report = animimport.import_clip(FBX, set_timeline=True, merge=True)
print("merge:", {k: report[k] for k in ("target", "joints", "curves",
                                        "start", "end")})
gate("merge landed", report["curves"] > 500 and report["joints"] > 80)
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
FRAMES = list(range(start, end + 1))

print("\n=== 3. the reference ===")
if cmds.namespace(exists=NS):
    cmds.namespace(removeNamespace=NS, deleteNamespaceContent=True)
ref = animimport.import_clip(FBX, namespace=NS, set_timeline=False,
                             merge=False)
ref_map = {}
for joint in cmds.ls(NS + ":*", type="joint", long=True) or []:
    ref_map[joint.split("|")[-1].split(":")[-1]] = joint
shared = sorted(set(scene_map) & set(ref_map))
gate("reference skeleton in place", len(shared) > 80,
     "{0} shared bones".format(len(shared)))

print("\n=== 4. Build ===")
resume = cmds.currentTime(query=True)
message = fkcontrols.rebuild(scene_map, fk_limbs=False)
print("Build said:", message)
gate("hybrid rig built",
     sorted(fkcontrols.built_fk_chains())
     == sorted(fkcontrols.HYBRID_FK_CHAINS)
     and len(builder.built_limbs()) == 4)

print("\n=== 5. every bone, every frame, against the reference ===")
per_bone = {}
odd_max = 0.0
even_max = 0.0
worst = ("", 0.0, 0)
for frame in FRAMES:
    cmds.currentTime(frame, update=True)
    for bone in shared:
        ours = cmds.xform(scene_map[bone], query=True, worldSpace=True,
                          matrix=True)
        there = cmds.xform(ref_map[bone], query=True, worldSpace=True,
                           matrix=True)
        delta = max(abs(a - b) for a, b in zip(ours, there))
        per_bone[bone] = max(per_bone.get(bone, 0.0), delta)
        if delta > worst[1]:
            worst = (bone, delta, frame)
        if frame % 2:
            odd_max = max(odd_max, delta)
        else:
            even_max = max(even_max, delta)
cmds.currentTime(resume)

ranked = sorted(per_bone.items(), key=lambda kv: -kv[1])
print("worst: {0} = {1:.6f} at f{2}".format(*worst))
print("top 6: " + ", ".join("{0}={1:.5f}".format(b, d) for b, d in ranked[:6]))
gate("even frames exact", even_max < 0.01,
     "even-max {0:.6f}".format(even_max))
gate("odd frames exact (the regression)", odd_max < 0.01,
     "odd-max {0:.6f}".format(odd_max))

print("\n=== 6. the machinery the fix must not damage ===")
knot = fkcontrols.controller_name("spine_01")
mid = (start + end) // 2
cmds.currentTime(mid)
attach_ok = True
if cmds.attributeQuery("attach", node=knot, exists=True):
    attach_ok = abs(cmds.getAttr(knot + ".attach") - 1.0) < 1e-6
gate("attach weight holds 1.0 mid-clip", attach_ok)
cmds.currentTime(resume)

times = cmds.keyframe(knot, attribute="rotateX", query=True,
                      timeChange=True) or []
stray = [t for t in times if abs(t - round(t)) > 1e-6]
gate("controller keys sit on whole frames", not stray,
     "{0} keys, {1} stray".format(len(times), len(stray)))

bone_times = cmds.keyframe(scene_map["clavicle_l"], attribute="rotateX",
                           query=True, timeChange=True) or []
gate("unrigged bone keys untouched",
     bone_times and not [t for t in bone_times if abs(t - round(t)) > 1e-6]
     and min(bone_times) == start and max(bone_times) == end,
     "{0} keys {1}..{2}".format(len(bone_times),
                                min(bone_times) if bone_times else "-",
                                max(bone_times) if bone_times else "-"))

print("\n=== 7. merge over a live rig is refused ===")
try:
    animimport.import_clip(FBX, set_timeline=False, merge=True)
    gate("rigged merge refused", False, "import went through")
except RuntimeError as exc:
    gate("rigged merge refused", "Bake+Delete" in str(exc), str(exc)[:80])

print("\n=== cleanup ===")
if cmds.namespace(exists=NS):
    cmds.namespace(removeNamespace=NS, deleteNamespaceContent=True)
print("reference removed; the hybrid rig is left built on the clip")

print("\n================ {0}/{1} PASSED ================".format(
    len(PASSED), len(PASSED) + len(FAILED)))
for name in FAILED:
    print("  FAILED: " + name)
print("DONE")

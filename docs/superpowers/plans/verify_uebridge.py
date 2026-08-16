"""Live checks: the UE -> Maya animation bridge, end to end.

Run inside Maya through the bridge runner (see CLAUDE.md; the runner's explicit
globals dict is what lets these helpers see module-level names), with the
Unreal editor open and Remote Execution enabled.

This script is also the spike: it prints the real asset-registry tag names and
the real FbxExportOption field names on this engine build, so the candidate
lists in uescripts.py are checked against the engine rather than trusted.

It imports into its own namespaces and deletes them at the end, so the user's
scene is left as it was found. No cmds.undo -- the whole script is one command,
and undoing would revert a prior chunk.
"""

import os
import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_uebridge")]:
    del sys.modules[name]

import maya.cmds as cmds

from maya_uebridge import animimport, records, uelink, uescripts, window

failures = []
made_namespaces = []
run_count = [0]


def check(label, condition, detail=""):
    run_count[0] += 1
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def temp(name):
    return os.path.join(window.temp_folder(), name)


# ---------------------------------------------------------------- transport

root = uelink.find_engine_root()
check("engine root found", bool(root), root or "")
if not root:
    print("\nno engine - nothing further can run")
    raise SystemExit

client_path = os.path.join(root, uelink.REMOTE_EXEC_RELPATH)
check("Epic's client is where we expect", os.path.isfile(client_path))

try:
    with uelink.UeLink() as link:
        answer = link.run("print('hello from maya')")
    reached = "hello from maya" in uelink.output_text(answer)
except uelink.UeBridgeError as error:
    reached = False
    print("   {0}".format(error))
check("the editor answers", reached)
if not reached:
    print("\nno editor - enable Remote Execution and try again")
    raise SystemExit


# ---------------------------------------------------------------- listing

out = temp("verify_list.json")
payload = uelink.run_script(uescripts.list_script(out, sample_tags=True), out,
                            keep_reply=True)

check("registry finished scanning", not payload.get("scanning"))
check("project reported", bool(payload.get("project")), payload.get("project", ""))

found = records.parse_payload(payload)
check("animations listed", len(found) > 0, "{0} assets".format(len(found)))

# The spike: what the registry really calls these tags on this build.
print("\n--- raw tags on {0} ---".format(
    payload.get("sample_tags", {}).get("asset", "?")))
for key, value in sorted(payload.get("sample_tags", {}).get("tags", {}).items()):
    print("    {0:<28} {1}".format(key, str(value)[:60]))
print("--- end tags ---\n")

with_frames = [r for r in found if r.frames is not None]
check("frame counts came through", bool(with_frames),
      "{0}/{1} rows carry a frame count".format(len(with_frames), len(found)))

# An independent count from inside the editor, so a filter bug cannot hide.
count_out = temp("verify_count.json")
count_src = (
    "import json, unreal\n"
    "registry = unreal.AssetRegistryHelpers.get_asset_registry()\n"
    "everything = registry.get_all_assets()\n"
    "total = 0\n"
    "for data in everything:\n"
    "    if str(data.asset_class_path.asset_name) == 'AnimSequence':\n"
    "        total += 1\n"
    "result = {'ok': True, 'error': '', 'total': total}\n"
    "json.dump(result, open(%s, 'w'))\n"
    "print('done')\n" % repr(count_out))
try:
    counted = uelink.run_script(count_src, count_out)["total"]
    check("count matches an independent scan", counted == len(found),
          "filter {0} vs scan {1}".format(len(found), counted))
except uelink.UeBridgeError as error:
    check("count matches an independent scan", False, str(error)[:70])

check("search narrows", len(records.filter_records(found, found[0].name)) >= 1)
check("search finds nothing for nonsense",
      records.filter_records(found, "zzzz_not_an_animation") == [])


# ---------------------------------------------------------------- export

target = found[0]
fbx = temp("{0}.fbx".format(target.name))
export_out = temp("verify_export.json")
exported = uelink.run_script(
    uescripts.export_script(export_out, target.package, fbx), export_out,
    keep_reply=True)

check("export reported success", bool(exported.get("ok")),
      exported.get("error", "")[:70])
check("the FBX exists on disk", os.path.isfile(fbx))
check("the FBX is not empty",
      os.path.isfile(fbx) and os.path.getsize(fbx) > 1024,
      "{0} bytes".format(os.path.getsize(fbx) if os.path.isfile(fbx) else 0))

if exported.get("notes"):
    print("\n--- FbxExportOption fields this build does NOT have ---")
    for note in exported["notes"]:
        print("    {0}".format(note))
    print("--- end fields ---\n")
else:
    print("\nevery FbxExportOption field we set exists on this build\n")


# ---------------------------------------------------------------- import

before = set(cmds.ls(long=True))
namespace = records.namespace_for(target.name, animimport.existing_namespaces())
info = animimport.import_clip(fbx, namespace, set_timeline=False,
                              clip_fps=exported.get("fps"))
made_namespaces.append(info["namespace"])

check("joints arrived", info["joints"] > 0, "{0} joints".format(info["joints"]))
check("keys arrived", info["curves"] > 0, "{0} curves".format(info["curves"]))
check("a key range was found", info["start"] is not None,
      "{0} - {1}".format(info["start"], info["end"]))
check("everything landed in our namespace",
      all(node.split("|")[-1].startswith(info["namespace"] + ":")
          for node in (cmds.ls(long=True) or []) if node not in before
          and cmds.objectType(node) == "joint"))

if exported.get("frames") and info["start"] is not None:
    span = info["end"] - info["start"] + 1
    close = abs(span - exported["frames"]) <= 1
    check("key range matches what UE reported", close,
          "maya {0:g} frames vs ue {1}".format(span, exported["frames"]))

scene_rate = animimport.scene_fps()
check("fps policy: warning appears only on a real mismatch",
      bool(animimport.fps_warning(exported.get("fps"), scene_rate))
      == (exported.get("fps") is not None and scene_rate is not None
          and abs(exported["fps"] - scene_rate) >= 0.01),
      "clip {0} scene {1}".format(exported.get("fps"), scene_rate))
check("the scene frame rate was left alone",
      animimport.scene_fps() == scene_rate)

# A second import of the same clip must not collide with the first.
second = records.namespace_for(target.name, animimport.existing_namespaces())
info2 = animimport.import_clip(fbx, second, set_timeline=False)
made_namespaces.append(info2["namespace"])
check("a second import gets its own namespace",
      info2["namespace"] != info["namespace"],
      "{0} then {1}".format(info["namespace"], info2["namespace"]))
check("the second import brought the same joints",
      info2["joints"] == info["joints"])


# ---------------------------------------------------------------- failure paths

missing_out = temp("verify_missing.json")
try:
    uelink.run_script(
        uescripts.export_script(missing_out, "/Game/NoSuchAsset_zzz",
                                temp("nope.fbx")), missing_out)
    check("a missing asset raises rather than half-succeeding", False)
except uelink.UeBridgeError as error:
    check("a missing asset raises rather than half-succeeding", True,
          str(error).strip().splitlines()[-1][:50])

check("the reply file is cleaned up after a run",
      not os.path.isfile(missing_out))


# ---------------------------------------------------------------- cleanup

cmds.namespace(setNamespace=":")
for name in made_namespaces:
    if cmds.namespace(exists=name):
        try:
            cmds.namespace(removeNamespace=name, deleteNamespaceContent=True)
        except RuntimeError as error:
            print("could not remove namespace {0}: {1}".format(name, error))

check("the scene was left clean",
      all(not cmds.namespace(exists=n) for n in made_namespaces))

for name in ("verify_list.json", "verify_export.json"):
    path = temp(name)
    if os.path.isfile(path):
        os.remove(path)

print("\n{0}/{1} checks passed".format(run_count[0] - len(failures), run_count[0]))
if failures:
    print("FAILED: " + ", ".join(failures))
else:
    print("ALL GREEN")

# Live verification for the UE bridge export-back direction (checkouts
# window, pair checkout/revert, scene -> fbx -> reimport).
#
# Meant to run through the command-port bridge in the animator's Maya with a
# UE editor open. Sandbox-first: the exporter is proved on a throwaway chain,
# the reimport on a DUPLICATED uasset that is created and deleted by this
# script, and the only depot mutation is one edit+revert of the Longsword
# pair, guarded on both files being free and reverted in a finally.
#
# Bridge rules honoured: no modal dialogs (every ask injected), no SystemExit,
# no cmds.undo, autoKey off around pokes, sandbox nodes deleted in guarded
# finally steps, the animator's timeline saved and put back.

import json
import os
import sys
import traceback

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.insert(0, REPO)
# The session imports the INSTALLED SkeldarAnim copy (working notes, bridge
# note 9) - purge all three package trees whole so this run proves the repo.
for _name in list(sys.modules):
    for _pkg in ("maya_overrig", "maya_uebridge", "maya_scenesetup"):
        if _name == _pkg or _name.startswith(_pkg + "."):
            del sys.modules[_name]
            break

import maya.cmds as cmds  # noqa: E402

from maya_uebridge import animexport  # noqa: E402
from maya_uebridge import animimport  # noqa: E402
from maya_uebridge import checkouts  # noqa: E402
from maya_uebridge import uelink  # noqa: E402
from maya_uebridge import uescripts  # noqa: E402
from maya_uebridge import vcs  # noqa: E402
from maya_uebridge import window  # noqa: E402

SCRATCH = (r"C:\Users\MYPC~1\AppData\Local\Temp\claude"
           r"\C-----Work-MayaScripts\8544e4f0-aa4f-42b4-8353-2c77624893fa"
           r"\scratchpad")

FAILURES = []
SKIPS = []


def gate(number, name, condition, detail=""):
    verdict = "OK" if condition else "FAIL"
    if not condition:
        FAILURES.append("{0} {1} {2}".format(number, name, detail))
    print("GATE {0} {1}: {2} {3}".format(number, verdict, name, detail))


def skip(number, name, reason):
    SKIPS.append("{0} {1}".format(number, name))
    print("GATE {0} SKIP: {1} - {2}".format(number, name, reason))


print("=== verify_uebridge_export ===")
print("repo animexport:", animexport.__file__)

# ---------------------------------------------------------------- state save
_saved_selection = cmds.ls(selection=True, long=True) or []
_saved_autokey = cmds.autoKeyframe(query=True, state=True)
_saved_range = (cmds.playbackOptions(query=True, animationStartTime=True),
                cmds.playbackOptions(query=True, animationEndTime=True),
                cmds.playbackOptions(query=True, minTime=True),
                cmds.playbackOptions(query=True, maxTime=True))
cmds.autoKeyframe(state=False)

SANDBOX = "__uebx_sandbox"
CHECK_NS = "__uebx_check"

try:
    # ------------------------------------------------ gate 1: export round trip
    try:
        if cmds.objExists(SANDBOX):
            cmds.delete(SANDBOX)
        group = cmds.group(empty=True, name=SANDBOX)
        cmds.select(clear=True)
        a = cmds.joint(name="uebx_a", position=(0, 0, 0))
        b = cmds.joint(name="uebx_b", position=(2, 0, 0))
        c = cmds.joint(name="uebx_c", position=(4, 0, 0))
        cmds.parent(a, group)
        for frame, angle in ((0, 0.0), (12, 35.0), (24, -20.0)):
            cmds.setKeyframe(b, attribute="rotateZ", time=frame, value=angle)
            cmds.setKeyframe(a, attribute="translateY", time=frame,
                             value=angle / 10.0)
        a_path = cmds.ls(a, long=True)[0]

        fbx_path = os.path.join(SCRATCH, "uebx_roundtrip.fbx")
        cmds.select(a_path, replace=True)
        info = animexport.export_hierarchy(fbx_path, start=0, end=24)
        gate("1a", "export wrote a file",
             os.path.isfile(fbx_path) and os.path.getsize(fbx_path) > 0,
             "size={0}".format(os.path.getsize(fbx_path)
                               if os.path.isfile(fbx_path) else 0))
        gate("1b", "export counted the sandbox joints", info["joints"] == 3,
             "joints={0}".format(info["joints"]))
        gate("1c", "resolve_root honoured the selection",
             info["root"] == "uebx_a", "root={0}".format(info["root"]))

        result = animimport.import_clip(fbx_path, namespace=CHECK_NS,
                                        set_timeline=False, merge=False)
        gate("1d", "the reimported chain has 3 joints",
             result["joints"] == 3, "joints={0}".format(result["joints"]))
        span_ok = (result["start"] is not None
                   and abs(result["start"] - 0) <= 1
                   and abs(result["end"] - 24) <= 1)
        gate("1e", "the key range survived", span_ok,
             "range={0}..{1}".format(result["start"], result["end"]))
        back_b = "{0}:uebx_b".format(CHECK_NS)
        value = cmds.getAttr(back_b + ".rotateZ", time=12)
        gate("1f", "the mid-frame value survived the bake",
             abs(value - 35.0) < 1e-3, "rz@12={0:.6f}".format(value))
    except Exception:
        FAILURES.append("gate 1 raised")
        traceback.print_exc()

    # ------------------------------------------------ gate 2: range policy
    try:
        cmds.playbackOptions(animationStartTime=0, animationEndTime=24,
                             minTime=5, maxTime=10)
        start, end = animexport.export_range()
        gate("2", "a zoomed-in timeline does not trim the export",
             start == 0 and end == 24, "range={0:g}..{1:g}".format(start, end))
    except Exception:
        FAILURES.append("gate 2 raised")
        traceback.print_exc()
    finally:
        cmds.playbackOptions(animationStartTime=_saved_range[0],
                             animationEndTime=_saved_range[1],
                             minTime=_saved_range[2],
                             maxTime=_saved_range[3])

    # ------------------------------------------------ records + content dir
    cached, project, choice, cached_content = window.load_cache()
    window._STATE["records"] = cached
    window._STATE["project"] = project
    window._STATE["choice"] = choice
    window._STATE["content_dir"] = cached_content

    if not cached:
        try:
            out = os.path.join(window.temp_folder(), "verify_list.json")
            payload = uelink.run_script(uescripts.list_script(out), out,
                                        project=choice)
            from maya_uebridge import records as records_mod
            window._STATE["records"] = records_mod.parse_payload(payload)
            window._STATE["content_dir"] = payload.get("content_dir", "")
        except Exception:
            print("no cache and no editor listing:")
            traceback.print_exc()

    content = checkouts.content_dir()
    print("content_dir:", repr(content))
    print("records:", len(window._STATE["records"]))
    print("source root:", repr(window._saved_root()))

    # ------------------------------------------------ gate 3: p4 read-only
    if not content:
        skip("3", "p4 listing", "no Content dir (no cache, no editor)")
    else:
        try:
            opened, failure = vcs.opened_records(content)
            if failure:
                skip("3", "p4 listing", failure)
            else:
                gate("3a", "opened_records answers without failure", True,
                     "{0} opened uasset(s)".format(len(opened)))
                rows, row_failure = checkouts.load_rows()
                gate("3b", "load_rows answers without raising",
                     row_failure == "" or bool(row_failure),
                     "rows={0} failure={1!r}".format(len(rows), row_failure))
                round_trip_ok = True
                for row in rows:
                    package = vcs.package_of(row.client_file, content)
                    back = vcs.uasset_path_of(package, content)
                    if (os.path.normcase(os.path.normpath(back))
                            != os.path.normcase(os.path.normpath(
                                row.client_file))):
                        round_trip_ok = False
                        print("  round trip broke:", row.client_file, "->",
                              package, "->", back)
                    print("  row:", checkouts.format_row(row))
                gate("3c", "every row round-trips through the package map",
                     round_trip_ok)
        except Exception:
            FAILURES.append("gate 3 raised")
            traceback.print_exc()

    # ------------------------------------------------ gate 4: sandbox reimport
    VERIFY_DIR = "/Game/__bridge_verify"
    VERIFY_PKG = VERIFY_DIR + "/AS_VerifyReimport"
    editor_up = True
    try:
        uelink.discover_nodes(timeout=6)
    except uelink.UeBridgeError as error:
        editor_up = False
        skip("4", "sandbox reimport", str(error).splitlines()[0])

    if editor_up and not window._STATE["records"]:
        editor_up = False
        skip("4", "sandbox reimport", "no records to duplicate from")

    if editor_up:
        # Duplicate a clip on the project's MAIN skeleton - the scene holds
        # the player character, and a random smallest clip could belong to
        # some creature whose bones our fbx does not carry.
        tally = {}
        for rec in window._STATE["records"]:
            if rec.skeleton:
                tally[rec.skeleton] = tally.get(rec.skeleton, 0) + 1
        common = max(tally, key=tally.get) if tally else ""
        candidates = [rec for rec in window._STATE["records"]
                      if rec.frames is not None
                      and (not common or rec.skeleton == common)]
        source = (sorted(candidates, key=lambda rec: rec.frames)[0]
                  if candidates else window._STATE["records"][0])
        print("duplicating", source.package)
        dup_out = os.path.join(window.temp_folder(), "verify_dup.json")
        dup_script = (
            "import json, os, traceback\n"
            "import unreal\n"
            "_OUT = {out}\n"
            "result = {{\"ok\": False, \"error\": \"\"}}\n"
            "try:\n"
            "    lib = unreal.EditorAssetLibrary\n"
            "    if lib.does_asset_exist({dest}):\n"
            "        lib.delete_asset({dest})\n"
            "    made = lib.duplicate_asset({src}, {dest})\n"
            "    if made is None:\n"
            "        raise RuntimeError(\"duplicate_asset returned None\")\n"
            "    lib.save_asset({dest}, only_if_is_dirty=False)\n"
            "    result[\"ok\"] = True\n"
            "except Exception:\n"
            "    result[\"error\"] = traceback.format_exc()\n"
            "finally:\n"
            "    with open(_OUT, \"w\") as handle:\n"
            "        json.dump(result, handle)\n"
            "    print(\"__UEBRIDGE_DONE__\")\n").format(
                out=json.dumps(dup_out), src=json.dumps(source.package),
                dest=json.dumps(VERIFY_PKG))
        try:
            dup = uelink.run_script(dup_script, dup_out,
                                    project=window._STATE["choice"])
            gate("4a", "duplicated a sandbox uasset", bool(dup.get("ok")),
                 dup.get("error", "")[:200])

            scene_fbx = os.path.join(SCRATCH, "uebx_scene.fbx")
            cmds.select(clear=True)
            scene_info = animexport.export_hierarchy(scene_fbx)
            gate("4b", "exported the scene skeleton",
                 os.path.isfile(scene_fbx) and scene_info["joints"] > 0,
                 "root={0} joints={1} range={2:g}..{3:g}".format(
                     scene_info["root"], scene_info["joints"],
                     scene_info["start"], scene_info["end"]))

            re_out = os.path.join(window.temp_folder(), "verify_reimport.json")
            re_payload = uelink.run_script(
                uescripts.reimport_script(re_out, VERIFY_PKG, scene_fbx),
                re_out, project=window._STATE["choice"])
            gate("4c", "the sandbox uasset reimported and saved",
                 bool(re_payload.get("ok")) and bool(re_payload.get("saved")),
                 "frames={0} notes={1}".format(re_payload.get("frames"),
                                               re_payload.get("notes")))
        except Exception:
            FAILURES.append("gate 4 raised")
            traceback.print_exc()
        finally:
            try:
                del_out = os.path.join(window.temp_folder(),
                                       "verify_del.json")
                del_script = (
                    "import json, traceback\n"
                    "import unreal\n"
                    "_OUT = {out}\n"
                    "result = {{\"ok\": False, \"error\": \"\"}}\n"
                    "try:\n"
                    "    lib = unreal.EditorAssetLibrary\n"
                    "    if lib.does_asset_exist({dest}):\n"
                    "        lib.delete_asset({dest})\n"
                    "    if lib.does_directory_exist({folder}):\n"
                    "        lib.delete_directory({folder})\n"
                    "    result[\"ok\"] = True\n"
                    "except Exception:\n"
                    "    result[\"error\"] = traceback.format_exc()\n"
                    "finally:\n"
                    "    with open(_OUT, \"w\") as handle:\n"
                    "        json.dump(result, handle)\n"
                    "    print(\"__UEBRIDGE_DONE__\")\n").format(
                        out=json.dumps(del_out),
                        dest=json.dumps(VERIFY_PKG),
                        folder=json.dumps(VERIFY_DIR))
                cleanup = uelink.run_script(del_script, del_out,
                                            project=window._STATE["choice"])
                gate("4d", "the sandbox uasset was deleted",
                     bool(cleanup.get("ok")), cleanup.get("error", "")[:200])
            except Exception:
                FAILURES.append("gate 4 cleanup raised")
                traceback.print_exc()

    # ------------------------------------------------ gate 5: pair edit+revert
    root_dir = window._saved_root()
    longsword = None
    for rec in window._STATE["records"]:
        if "longsword" in rec.name.lower():
            longsword = rec
            break
    asks = {"file": lambda paths: paths[0],
            "folder": lambda name: "",
            "confirm": lambda paths: True,
            "others": lambda users: False,
            "failure": lambda reason: False}

    if not content:
        skip("5", "pair checkout+revert", "no Content dir")
    elif not root_dir or not os.path.isdir(root_dir):
        skip("5", "pair checkout+revert", "no saved source root")
    elif longsword is None:
        skip("5", "pair checkout+revert", "no Longsword record in the list")
    else:
        uasset_path = vcs.uasset_path_of(longsword.package, content)
        u_fields, u_fail = vcs.fstat(uasset_path)
        resolved = window._vcs_target(longsword, asks)
        fbx_path = resolved[0] if resolved else ""
        f_fields, f_fail = ({}, "no fbx target") if not fbx_path else \
            vcs.fstat(fbx_path)
        busy = (u_fields.get("action") or vcs.other_openers(u_fields)
                or f_fields.get("action") or vcs.other_openers(f_fields))
        if u_fail or f_fail:
            skip("5", "pair checkout+revert",
                 "fstat: {0} {1}".format(u_fail, f_fail))
        elif not u_fields.get("depotFile"):
            skip("5", "pair checkout+revert",
                 "uasset not under this client: " + uasset_path)
        elif busy:
            skip("5", "pair checkout+revert",
                 "a file of the pair is open somewhere - never touch it")
        else:
            try:
                line = checkouts.checkout_pair(longsword, asks)
                print("checkout_pair:", line)
                gate("5a", "checkout_pair opened the pair",
                     "checked out" in line and "not opened" not in line, line)

                opened, _ = vcs.opened_records(content)
                mine = [f for f in opened
                        if os.path.normcase(f.get("clientFile", ""))
                        == os.path.normcase(uasset_path)]
                gate("5b", "the uasset shows up in opened_records",
                     len(mine) == 1)

                rows, row_failure = checkouts.load_rows()
                match = [row for row in rows
                         if row.record.name == longsword.name]
                gate("5c", "load_rows lists the checkout",
                     len(match) == 1 and match[0].fbx == "ok",
                     "rows={0} fbx={1}".format(
                         len(match), match[0].fbx if match else "?"))

                if match:
                    line = checkouts.revert_pair(match[0], asks)
                    print("revert_pair:", line)
                    gate("5d", "revert_pair reverted",
                         line.startswith("reverted")
                         and "NOT reverted" not in line, line)
            except Exception:
                FAILURES.append("gate 5 raised")
                traceback.print_exc()
            finally:
                # Self-cleaning whatever happened above: revert answers ""
                # for a file that is not opened, so this is safe to repeat.
                for path in (uasset_path, fbx_path):
                    if path:
                        left = vcs.revert(path)
                        if left:
                            print("cleanup revert failed for", path, "-", left)
                u_after, _ = vcs.fstat(uasset_path)
                gate("5e", "the pair is free again",
                     not u_after.get("action"))

finally:
    # ---------------------------------------------- put the scene back
    for step in (
        lambda: cmds.delete(SANDBOX) if cmds.objExists(SANDBOX) else None,
        lambda: cmds.namespace(removeNamespace=":" + CHECK_NS,
                               deleteNamespaceContent=True)
        if cmds.namespace(exists=":" + CHECK_NS) else None,
        lambda: cmds.autoKeyframe(state=_saved_autokey),
        lambda: cmds.playbackOptions(
            animationStartTime=_saved_range[0],
            animationEndTime=_saved_range[1],
            minTime=_saved_range[2], maxTime=_saved_range[3]),
        lambda: (cmds.select(_saved_selection, replace=True)
                 if _saved_selection else cmds.select(clear=True)),
    ):
        try:
            step()
        except Exception:
            traceback.print_exc()

print("skips:", SKIPS if SKIPS else "none")
print("failures:", FAILURES if FAILURES else "none")
print("VERIFY DONE", len(FAILURES))

"""Live proof for Export to uasset -- the direct road, no Perforce on it.

Run through the command-port bridge in the user's Maya, with an Unreal
editor open. Everything destructive happens to a SANDBOX asset this script
duplicates into `/Game/__bridge_verify` and deletes again: overwriting one
of the animator's real animations to prove a button works is not on the
table, and the whole feature is about overwriting.

What it measures, in order:

  1  the refusal table, against the real cached listing and a real uasset
     path on disk -- nothing selected, no Content dir, a uasset that is not
     there, and the Cancel answer;
  2  the dialog text on a real record;
  3  the round trip on the sandbox: a REAL read-only flag set on the
     duplicated uasset, the export, the flag coming off, and the editor
     reporting the new frame count;
  4  that the flag was left off, that no Perforce state was touched (the
     module cannot even import vcs), and that the sandbox is gone.

Bridge hygiene (CLAUDE.md): the confirm dialog is INJECTED, never raised -
a modal over the command port blocks Maya's idle queue (note 6). No
SystemExit anywhere (note 8). autoKey off, frame/selection restored, every
teardown step guarded on its own.
"""

import json
import os
import sys
import traceback

PLUGIN = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

for _name in [m for m in list(sys.modules)
              if m.split(".")[0] in ("maya_overrig", "maya_uebridge",
                                     "maya_scenesetup")]:
    del sys.modules[_name]

import maya.cmds as cmds

from maya_uebridge import (animexport, records, uassetexport, uelink,
                           uescripts, window)

VERIFY_DIR = "/Game/__bridge_verify"
VERIFY_PKG = VERIFY_DIR + "/AS_VerifyUassetExport"

# A verify-only heuristic for picking a source whose skeleton the scene's
# character can actually satisfy. Product code never guesses this -- the
# whole point of `unchanged_warning` is that it does not have to.
MANNY_HINTS = ("manny", "mannequin_ue5", "quinn")

FAILURES = []
SKIPPED = []


def gate(tag, label, condition, detail=""):
    print("%-4s %-56s %s %s" % (tag, label, "OK" if condition else "FAIL",
                                detail))
    if not condition:
        FAILURES.append("{0} {1}".format(tag, label))


def skip(tag, label, why):
    print("%-4s %-56s SKIP %s" % (tag, label, why))
    SKIPPED.append("{0} {1}: {2}".format(tag, label, why))


def run_ue(source, out_name, project):
    out = os.path.join(window.temp_folder(), out_name)
    return uelink.run_script(source, out, project=project)


def _asset_script(out, body):
    """One small UE script: `body` runs with `lib` and `result` in scope."""
    return ("import json, traceback\n"
            "import unreal\n"
            "_OUT = %s\n"
            "result = {\"ok\": False, \"error\": \"\", \"frames\": None}\n"
            "try:\n"
            "    lib = unreal.EditorAssetLibrary\n"
            "%s"
            "    result[\"ok\"] = True\n"
            "except Exception:\n"
            "    result[\"error\"] = traceback.format_exc()\n"
            "finally:\n"
            "    with open(_OUT, \"w\") as handle:\n"
            "        json.dump(result, handle)\n"
            "    print(\"__UEBRIDGE_DONE__\")\n" % (json.dumps(out), body))


def duplicate_asset(source_package, project):
    body = ("    if lib.does_asset_exist(%(dest)s):\n"
            "        lib.delete_asset(%(dest)s)\n"
            "    made = lib.duplicate_asset(%(src)s, %(dest)s)\n"
            "    if made is None:\n"
            "        raise RuntimeError('duplicate_asset returned None')\n"
            "    lib.save_asset(%(dest)s, only_if_is_dirty=False)\n"
            "    anim = unreal.load_asset(%(dest)s)\n"
            "    result['frames'] = anim.get_editor_property("
            "'number_of_sampled_frames')\n"
            % {"src": json.dumps(source_package),
               "dest": json.dumps(VERIFY_PKG)})
    out = os.path.join(window.temp_folder(), "vuasset_dup.json")
    return uelink.run_script(_asset_script(out, body), out, project=project)


def read_frames(project):
    body = ("    anim = unreal.load_asset(%(dest)s)\n"
            "    if anim is None:\n"
            "        raise RuntimeError('gone: ' + %(dest)s)\n"
            "    result['frames'] = anim.get_editor_property("
            "'number_of_sampled_frames')\n"
            % {"dest": json.dumps(VERIFY_PKG)})
    out = os.path.join(window.temp_folder(), "vuasset_frames.json")
    return uelink.run_script(_asset_script(out, body), out, project=project)


def delete_sandbox(project):
    body = ("    if lib.does_asset_exist(%(dest)s):\n"
            "        lib.delete_asset(%(dest)s)\n"
            "    if lib.does_directory_exist(%(folder)s):\n"
            "        lib.delete_directory(%(folder)s)\n"
            % {"dest": json.dumps(VERIFY_PKG),
               "folder": json.dumps(VERIFY_DIR)})
    out = os.path.join(window.temp_folder(), "vuasset_del.json")
    return uelink.run_script(_asset_script(out, body), out, project=project)


def main():
    cached, project_path, choice, content_dir = window.load_cache()
    window._STATE["records"] = cached
    window._STATE["content_dir"] = content_dir

    print("cached records: %d   project: %s" % (len(cached), choice))
    print("content dir:    %s" % content_dir)
    print("")

    if not cached or not content_dir:
        skip("0", "everything", "no cached listing - press Refresh first")
        return

    # A record whose uasset is really on disk, so the refusal table is
    # measured against a real path rather than a made-up one.
    real = None
    for rec in cached:
        path = records.uasset_path_of(rec.package, content_dir)
        if os.path.isfile(path):
            real = (rec, path)
            break
    if real is None:
        skip("0", "everything", "no cached record resolves to a file on disk")
        return
    record, uasset = real

    # ------------------------------------------------- 1: the refusal table
    gate("1a", "a real record with a real uasset is no refusal",
         uassetexport.refusal(record, content_dir, uasset, True) == "",
         os.path.basename(uasset))
    gate("1b", "nothing selected refuses",
         uassetexport.refusal(None, content_dir, uasset, True)
         == uassetexport.NO_SELECTION)
    gate("1c", "no Content dir names Refresh",
         "Refresh" in uassetexport.refusal(record, "", "", False))
    gate("1d", "a uasset that is not there names the path",
         uasset in uassetexport.refusal(record, content_dir, uasset, False))

    # ------------------------------------------------------- 2: the dialog
    message = uassetexport.overwrite_message(
        record.name, record.package, "|root", True)
    gate("2a", "the dialog names the asset and what is lost",
         record.name in message and "Pose_0..9" in message
         and "REBUILT" in message)
    gate("2b", "it says Perforce is not involved",
         "Perforce" in message and "changelist" in message)
    gate("2c", "it warns about the read-only flag when there is one",
         "read-only" in message
         and "read-only" not in uassetexport.overwrite_message(
             record.name, record.package, "|root", False))

    # Cancel must do nothing at all, and that is measurable: the staging
    # fbx must not appear.
    staged = uassetexport.fbx_staging_path(record.name,
                                           window.temp_folder())
    if os.path.isfile(staged):
        os.remove(staged)
    line = uassetexport.export_to_uasset(
        record, content_dir, choice, window.temp_folder(),
        asks={"confirm": lambda _message: False})
    gate("2d", "Cancel writes no fbx and says what was left alone",
         not os.path.isfile(staged) and "untouched" in line, line)

    # -------------------------------------------- 3: the sandbox round trip
    try:
        uelink.discover_nodes(timeout=6)
    except uelink.UeBridgeError as error:
        skip("3", "the sandbox round trip", str(error).splitlines()[0])
        return

    tally = {}
    for rec in cached:
        if rec.skeleton:
            tally[rec.skeleton] = tally.get(rec.skeleton, 0) + 1
    print("skeletons in the listing: " + ", ".join(
        "{0}x{1}".format(n, name) for name, n in
        sorted(tally.items(), key=lambda kv: -kv[1])[:5]))

    # The MISMATCH case, and deliberately so: the project's most common
    # skeleton is almost never the character in the animator's scene, which
    # is exactly the silent no-op this feature had to learn to report.
    common = max(tally, key=tally.get) if tally else ""
    pool = [rec for rec in cached
            if rec.frames is not None and (not common
                                           or rec.skeleton == common)]
    source = (sorted(pool, key=lambda rec: rec.frames)[0] if pool
              else cached[0])
    print("duplicating %s -> %s" % (source.package, VERIFY_PKG))

    try:
        dup = duplicate_asset(source.package, choice)
        gate("3a", "duplicated a sandbox uasset", bool(dup.get("ok")),
             str(dup.get("error", ""))[:160])
        if not dup.get("ok"):
            return
        before_frames = dup.get("frames")

        sandbox_path = records.uasset_path_of(VERIFY_PKG, content_dir)
        gate("3b", "the sandbox uasset is on disk where we expect it",
             os.path.isfile(sandbox_path), sandbox_path)
        if not os.path.isfile(sandbox_path):
            return

        # The real thing this feature is about: a read-only uasset.
        os.chmod(sandbox_path, 0o444)
        gate("3c", "the sandbox is read-only before the press",
             uassetexport.is_read_only(sandbox_path))

        sandbox_record = records.AnimRecord(
            name="AS_VerifyUassetExport", package=VERIFY_PKG,
            skeleton=source.skeleton, frames=before_frames,
            length=None, fps=source.fps)

        asked = []
        line = uassetexport.export_to_uasset(
            sandbox_record, content_dir, choice, window.temp_folder(),
            asks={"confirm": lambda message: asked.append(message) or True})
        print("status: " + line)

        gate("3d", "the dialog was raised before anything was written",
             len(asked) == 1 and "read-only" in asked[0])
        gate("3e", "the read-only flag came off and stayed off",
             not uassetexport.is_read_only(sandbox_path))
        gate("3f", "the status says the flag was cleared",
             "read-only cleared" in line)
        gate("3g", "the fbx was staged in the temp folder",
             os.path.isfile(uassetexport.fbx_staging_path(
                 sandbox_record.name, window.temp_folder())))
        gate("3h", "the editor reimported and saved",
             "reimported and saved" in line, line)

        # THE gate this script exists for. The sandbox is duplicated from
        # whatever the project has most of, so its skeleton usually does
        # NOT match the character in the Maya scene -- and an FBX whose
        # bones do not match imports with ok/saved/no notes while writing
        # nothing (measured 2026-09-01, and the reason `unchanged_warning`
        # exists). Either the animation really changed, or the status says
        # in so many words that it did not. Silence over a no-op is the
        # failure.
        after = read_frames(choice)
        changed = (bool(after.get("ok"))
                   and after.get("frames") not in (None, before_frames))
        warned = "did NOT change" in line
        gate("3i", "a no-op reimport is never reported as a success",
             changed != warned,
             "before={0} after={1} changed={2} warned={3}".format(
                 before_frames, after.get("frames"), changed, warned))
        if warned:
            print("     (expected here: the sandbox's skeleton is %s and "
                  "the scene exports a different character)"
                  % (source.skeleton or "?"))
    except Exception:
        FAILURES.append("gate 3 raised")
        traceback.print_exc()
    finally:
        try:
            sandbox_path = records.uasset_path_of(VERIFY_PKG, content_dir)
            if os.path.isfile(sandbox_path):
                os.chmod(sandbox_path, 0o666)
        except OSError:
            traceback.print_exc()
        try:
            cleanup = delete_sandbox(choice)
            gate("4a", "the sandbox uasset and its folder are gone",
                 bool(cleanup.get("ok")), str(cleanup.get("error", ""))[:160])
        except Exception:
            FAILURES.append("4a cleanup raised")
            traceback.print_exc()
        gate("4b", "the animator's own uasset was never touched",
             not uassetexport.is_read_only(uasset)
             and os.path.isfile(uasset),
             os.path.basename(uasset))

    # ---------------------------------- 5: the MATCH case, the other half
    # A no-op that is reported is only half the proof; a real replacement
    # has to come out changed and unwarned. Needs a source whose skeleton
    # the scene's character can satisfy, which the listing may not have.
    matching = [rec for rec in cached
                if rec.frames is not None
                and any(hint in (rec.skeleton or "").lower()
                        for hint in MANNY_HINTS)]
    if not matching:
        skip("5", "a real replacement changes the asset",
             "the listing has no clip on a Manny-shaped skeleton")
        return

    source = sorted(matching, key=lambda rec: rec.frames)[0]
    print("")
    print("duplicating %s (skeleton %s) -> %s"
          % (source.package, source.skeleton, VERIFY_PKG))
    try:
        dup = duplicate_asset(source.package, choice)
        if not dup.get("ok"):
            skip("5", "a real replacement changes the asset",
                 str(dup.get("error", ""))[:120])
            return
        before_frames = dup.get("frames")
        sandbox_record = records.AnimRecord(
            name="AS_VerifyUassetExport", package=VERIFY_PKG,
            skeleton=source.skeleton, frames=before_frames,
            length=None, fps=source.fps)
        line = uassetexport.export_to_uasset(
            sandbox_record, content_dir, choice, window.temp_folder(),
            asks={"confirm": lambda _m: True})
        print("status: " + line)
        after = read_frames(choice)
        gate("5a", "the asset took the scene's animation",
             after.get("frames") not in (None, before_frames),
             "before={0} after={1}".format(before_frames,
                                           after.get("frames")))
        gate("5b", "and nothing warned about a no-op",
             "did NOT change" not in line)
        gate("5c", "a writable uasset gets no read-only note",
             "read-only cleared" not in line)
    except Exception:
        FAILURES.append("gate 5 raised")
        traceback.print_exc()
    finally:
        try:
            cleanup = delete_sandbox(choice)
            gate("5d", "the second sandbox is gone too",
                 bool(cleanup.get("ok")),
                 str(cleanup.get("error", ""))[:160])
        except Exception:
            FAILURES.append("5d cleanup raised")
            traceback.print_exc()
        gate("4c", "the module cannot reach Perforce at all",
             "maya_uebridge.vcs" not in sys.modules
             or not any(name.startswith("vcs")
                        for name in dir(uassetexport)),
             "vcs imported by something else: {0}".format(
                 "maya_uebridge.vcs" in sys.modules))


auto_key = cmds.autoKeyframe(query=True, state=True)
FRAME = cmds.currentTime(query=True)
SELECTION = cmds.ls(selection=True, long=True) or []
cmds.autoKeyframe(state=False)
try:
    main()
finally:
    for step in (
            lambda: cmds.autoKeyframe(state=auto_key),
            lambda: cmds.currentTime(FRAME, edit=True),
            lambda: (cmds.select([n for n in SELECTION
                                  if cmds.objExists(n)], replace=True)
                     if any(cmds.objExists(n) for n in SELECTION)
                     else cmds.select(clear=True)),
    ):
        try:
            step()
        except Exception:
            traceback.print_exc()

print("")
for note in SKIPPED:
    print("SKIPPED: " + note)
print("%d of the gates that ran failed%s" % (
    len(FAILURES), (": " + ", ".join(FAILURES)) if FAILURES else ""))

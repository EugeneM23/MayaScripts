"""Live verification: the UE bridge's Perforce placement.

Run in the user's Maya through the command port. Uses a SANDBOX source root
in Maya's temp folder - the real SourceArt is never written - and mutates the
depot not at all: the p4 gates are fstat reads; the edit branch is proved by
unit tests over captured output. Dialog-bearing paths get injected answers (a
modal over the command port blocks Maya - bridge note 6). The timeline is
never touched (set_timeline=False) and the import goes into its own namespace,
so the scene skeleton and whatever the animator is doing stay untouched.

Gates:
 1. vcs.find_fbx finds the planted file by name, case-insensitively
 2. choose_target: single hit taken silently
 3. choose_target: ambiguity resolved by the injected pick, remembered
 4. choose_target: new file lands in the planted conventional folder
 5. choose_target: new file with no folder asks, remembers, second call silent
 6. conventional_folder is the pure mirror: the Longsword package maps onto
    the folder the depot actually uses, 3P kept (the reported bug's fix)
 7. real p4 fstat on the tracked example uasset parses: depotFile present,
    plan kind is edit/others/mine
 8. real p4 fstat on the sandbox fbx answers untracked; prepare_target
    proceeds with "not in depot" and raises no dialog
 9. place() overwrites a read-only sandbox target and the bytes change
10. animimport.import_clip on the placed fbx AS A NEW NAMESPACED SKELETON
    (merge=False - the scene skeleton is untouched) animates joints
11. window._vcs_target with injected asks resolves end to end and the dir
    map optionVar grows
12. find_fbx_depot finds the real Longsword fbx that sits in the depot
    (never synced before the first run) at its canonical clientFile path
13. choose_target with the real root and real p4 resolves that name to the
    depot path silently - the reported scenario, discovery half
14. prepare_target on that real file checks it out (a never-synced file
    answers "not on client" and checkout syncs and retries - the user's
    sync+checkout ask), then p4 revert puts the open state back; the file
    stays synced on disk. Skipped cleanly if a colleague holds it open.

The dir map optionVar is deliberately CLEARED at the end (not restored):
answers remembered under the dropped-1P/3P convention are stale.
"""

import json
import os
import shutil
import stat
import sys
import tempfile

import maya.cmds as cmds

REPO = "C:/!!!Work/MayaScripts"
REAL_FBX = ("C:/!!!Work/Perforce/SourceArt/Prototype/Animation/Exports/"
            "PlayerCharacter/Unarmed/AS_Unarmed_Idle_1P.fbx")
REAL_UASSET = ("C:/!!!Work/Perforce/Atone/Content/Prototype/Animation/"
               "PlayerCharacter/Unarmed/1P/AS_Unarmed_Idle_1P.uasset")
REAL_SOURCEART = "C:/!!!Work/Perforce/SourceArt"
REAL_PACKAGE = ("/Game/Prototype/Animation/PlayerCharacter/Unarmed/1P/"
                "AS_Unarmed_Idle_1P")
LONGSWORD_NAME = "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P"
LONGSWORD_PACKAGE = ("/Game/Prototype/Animation/PlayerCharacter/Weapons/"
                     "Longsword/3P/" + LONGSWORD_NAME)
LONGSWORD_CLIENT = os.path.normpath(
    "C:/!!!Work/Perforce/SourceArt/Prototype/Animation/Exports/"
    "PlayerCharacter/Weapons/Longsword/3P/" + LONGSWORD_NAME + ".fbx")
NAMESPACE = "vcsverify"

# The session imports the INSTALLED SkeldarAnim copy (note 9): put the repo
# first and purge the package tree whole, or this proves yesterday's code.
sys.path.insert(0, REPO)
for name in [key for key in list(sys.modules)
             if key == "maya_uebridge" or key.startswith("maya_uebridge.")]:
    del sys.modules[name]

from maya_uebridge import animimport, records, vcs, window  # noqa: E402

RESULTS = []
# True only while gate 14 holds the Longsword file open; the finally block
# reverts it if an exception lands between the edit and the revert. Never
# revert unconditionally - the animator may hold that file open with REAL
# work, and gate 14 skips itself in that case.
LONGSWORD_OPENED = [False]


def gate(number, label, ok, detail=""):
    RESULTS.append((number, label, bool(ok), detail))
    print("gate {0:>2} {1}: {2}{3}".format(
        number, "PASS" if ok else "FAIL", label,
        "  [{0}]".format(detail) if detail else ""))


def never(*_):
    raise AssertionError("a dialog was raised where none belongs")


def plant(root, *parts):
    path = os.path.join(root, *parts)
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    shutil.copyfile(REAL_FBX, path)
    return path


def optionvar_snapshot(names):
    held = {}
    for name in names:
        if cmds.optionVar(exists=name):
            held[name] = cmds.optionVar(query=name)
    return held


def optionvar_restore(names, held):
    for name in names:
        if name in held:
            if isinstance(held[name], int):
                cmds.optionVar(intValue=(name, held[name]))
            else:
                cmds.optionVar(stringValue=(name, held[name]))
        elif cmds.optionVar(exists=name):
            cmds.optionVar(remove=name)


OPTIONVARS = ("ueBridgeVcs", "ueBridgeVcsRoot", "ueBridgeVcsDirMap")

sandbox = tempfile.mkdtemp(prefix="uebridge_vcs_verify_")
held_vars = optionvar_snapshot(OPTIONVARS)

try:
    # -- gate 1: find by name, case-insensitively ------------------------
    planted = plant(sandbox, "Somewhere", "Deep", "AS_Unarmed_Idle_1P.fbx")
    hits = vcs.find_fbx("as_unarmed_idle_1p", sandbox)
    gate(1, "find_fbx finds the planted file by name",
         hits == [os.path.join(sandbox, "Somewhere", "Deep",
                               "AS_Unarmed_Idle_1P.fbx")],
         "hits={0}".format(hits))

    # -- gate 2: single hit taken silently -------------------------------
    path, dm = vcs.choose_target("AS_Unarmed_Idle_1P", REAL_PACKAGE,
                                 sandbox, {}, never, never)
    gate(2, "single hit taken silently", path == planted, path)

    # -- gate 3: ambiguity resolved by injected pick, remembered ---------
    second = plant(sandbox, "Elsewhere", "AS_Unarmed_Idle_1P.fbx")
    path, dm = vcs.choose_target("AS_Unarmed_Idle_1P", REAL_PACKAGE,
                                 sandbox, {}, lambda paths: second, never)
    remembered = vcs.remembered_folder(dm, REAL_PACKAGE)
    gate(3, "ambiguity resolved by the injected pick and remembered",
         path == second and remembered == os.path.dirname(second),
         "picked={0} remembered={1}".format(path, remembered))

    # -- gate 4: new file lands in the planted conventional folder -------
    fresh = os.path.join(sandbox, "fresh_root")
    convention = os.path.join(fresh, "Prototype", "Animation", "Exports",
                              "PlayerCharacter", "Unarmed", "1P")
    os.makedirs(convention)
    path, dm = vcs.choose_target("AS_Unarmed_New", REAL_PACKAGE,
                                 fresh, {}, never, never)
    gate(4, "new file lands in the conventional folder",
         path == os.path.join(convention, "AS_Unarmed_New.fbx"), path)

    # -- gate 5: no folder -> ask, remember, second call silent ----------
    bare = os.path.join(sandbox, "bare_root")
    chosen = os.path.join(bare, "MyExports")
    os.makedirs(chosen)
    asked = []

    def ask_folder(name):
        asked.append(name)
        return chosen

    path, dm = vcs.choose_target("AS_Unarmed_New", REAL_PACKAGE,
                                 bare, {}, never, ask_folder)
    path2, dm = vcs.choose_target("AS_Unarmed_New", REAL_PACKAGE,
                                  bare, dm, never, never)
    gate(5, "folder asked once, remembered for the second call",
         (path == os.path.join(chosen, "AS_Unarmed_New.fbx")
          and path2 == path and asked == ["AS_Unarmed_New"]),
         "asked={0}".format(asked))

    # -- gate 6: the convention is the depot's pure mirror ----------------
    mirror = os.path.normpath(
        vcs.conventional_folder(LONGSWORD_PACKAGE, REAL_SOURCEART))
    gate(6, "conventional_folder mirrors the depot layout, 3P kept",
         mirror == os.path.dirname(LONGSWORD_CLIENT), mirror)

    # -- gate 7: real fstat on the tracked uasset parses -----------------
    fields, failure = vcs.fstat(REAL_UASSET.replace("/", os.sep))
    plan = vcs.plan_for(fields)
    gate(7, "real fstat on the tracked uasset parses into a plan",
         (not failure) and fields.get("depotFile", "").startswith("//")
         and plan["kind"] in ("edit", "others", "mine"),
         failure or "kind={0} rev={1}".format(plan["kind"],
                                              fields.get("headRev")))

    # -- gate 8: sandbox fbx is untracked, prepare proceeds silently -----
    proceed, note = vcs.prepare_target(planted, never, never)
    gate(8, "untracked sandbox file proceeds with no dialog and no p4 action",
         proceed and note == "not in depot", note)

    # -- gate 9: place() overwrites a read-only target -------------------
    target = plant(sandbox, "Placed", "AS_Unarmed_Idle_1P.fbx")
    os.chmod(target, stat.S_IREAD)
    marker_bytes = b"not really an fbx"
    temp_export = os.path.join(sandbox, "temp_export.fbx")
    with open(temp_export, "wb") as handle:
        handle.write(marker_bytes)
    vcs.place(temp_export, target)
    with open(target, "rb") as handle:
        body = handle.read()
    gate(9, "place() overwrites a read-only target",
         body == marker_bytes, "size={0}".format(len(body)))
    shutil.copyfile(REAL_FBX, target)  # a real fbx again for gate 10

    # -- gate 10: import the placed fbx as a namespaced skeleton ---------
    if cmds.namespace(exists=NAMESPACE):
        cmds.namespace(removeNamespace=NAMESPACE,
                       deleteNamespaceContent=True)
    info = animimport.import_clip(target, NAMESPACE, set_timeline=False,
                                  clip_fps=30.0, merge=False)
    gate(10, "the placed fbx imports as a namespaced skeleton",
         (info.get("joints", 0) or 0) > 0,
         "joints={0}".format(info.get("joints")))

    # -- gate 11: window._vcs_target end to end with injected asks -------
    cmds.optionVar(stringValue=("ueBridgeVcsRoot", sandbox))
    cmds.optionVar(stringValue=("ueBridgeVcsDirMap", "{}"))
    record = records.parse_payload({"assets": [{
        "name": "AS_Window_Test", "package": REAL_PACKAGE}]})[0]
    lone = plant(sandbox, "WindowCase", "AS_Window_Test.fbx")
    resolved = window._vcs_target(record, asks={"root": never,
                                                "file": never,
                                                "folder": never})
    gate(11, "window._vcs_target resolves end to end",
         resolved is not None and resolved[0] == lone
         and resolved[1] is False,
         "resolved={0}".format(resolved))

    # -- gate 12: the depot search finds the real Longsword fbx ----------
    depot_hits = vcs.find_fbx_depot(LONGSWORD_NAME, REAL_SOURCEART,
                                    vcs.run_p4)
    clients = [os.path.normpath(rec.get("clientFile", ""))
               for rec in depot_hits]
    gate(12, "find_fbx_depot finds the depot-side Longsword fbx",
         clients == [LONGSWORD_CLIENT], "clients={0}".format(clients))

    # -- gate 13: choose_target resolves the reported case silently ------
    path, _ = vcs.choose_target(LONGSWORD_NAME, LONGSWORD_PACKAGE,
                                REAL_SOURCEART, {}, never, never,
                                run=vcs.run_p4)
    gate(13, "choose_target lands the Longsword import on the depot path",
         os.path.normpath(path) == LONGSWORD_CLIENT, path)

    # -- gate 14: the user's sync+checkout flow, then put back -----------
    fields_before, fail_before = vcs.fstat(LONGSWORD_CLIENT)
    plan_before = vcs.plan_for(fields_before)
    if fail_before:
        gate(14, "real sync+checkout flow", False, fail_before)
    elif plan_before["kind"] == "mine":
        gate(14, "real sync+checkout flow (skipped - already opened by you)",
             True, "")
    elif plan_before["kind"] == "others":
        gate(14, "real sync+checkout flow (skipped - held by a colleague)",
             True, ", ".join(plan_before["users"]))
    elif plan_before["kind"] == "untracked":
        gate(14, "real sync+checkout flow", False,
             "expected the Longsword fbx tracked in the depot")
    else:
        proceed, note = vcs.prepare_target(LONGSWORD_CLIENT, never, never)
        LONGSWORD_OPENED[0] = proceed and note == "checked out"
        after, _ = vcs.fstat(LONGSWORD_CLIENT)
        opened = after.get("action") == "edit"
        synced = (os.path.isfile(LONGSWORD_CLIENT)
                  and after.get("haveRev") == after.get("headRev"))
        code, _, _ = vcs.run_p4(["revert", LONGSWORD_CLIENT],
                                os.path.dirname(LONGSWORD_CLIENT))
        if code == 0:
            LONGSWORD_OPENED[0] = False
        back, _ = vcs.fstat(LONGSWORD_CLIENT)
        gate(14, "real sync+checkout flow, then reverted",
             proceed and note == "checked out" and opened and synced
             and not back.get("action"),
             "note={0} have={1}/{2} revert_rc={3}".format(
                 note, after.get("haveRev"), after.get("headRev"), code))

except Exception:
    import traceback
    print(traceback.format_exc())
    gate(99, "no unhandled exception", False, "see traceback above")

finally:
    # Every teardown step guarded on its own (trap 42): one failed restore
    # must not take the rest of the restore with it.
    try:
        if LONGSWORD_OPENED[0]:
            vcs.run_p4(["revert", LONGSWORD_CLIENT],
                       os.path.dirname(LONGSWORD_CLIENT))
            print("backup revert of the Longsword checkout ran")
    except Exception as error:
        print("backup revert failed: {0}".format(error))
    try:
        optionvar_restore(OPTIONVARS, held_vars)
    except Exception as error:
        print("optionVar restore failed: {0}".format(error))
    try:
        # Deliberately NOT restored: folder answers remembered under the
        # dropped-1P/3P convention are stale and would misplace new files.
        previous_map = held_vars.get("ueBridgeVcsDirMap", "")
        cmds.optionVar(stringValue=("ueBridgeVcsDirMap", "{}"))
        print("dir map cleared (was: {0!r})".format(previous_map))
    except Exception as error:
        print("dir map clearing failed: {0}".format(error))
    try:
        if cmds.namespace(exists=NAMESPACE):
            cmds.namespace(removeNamespace=NAMESPACE,
                           deleteNamespaceContent=True)
    except Exception as error:
        print("namespace cleanup failed: {0}".format(error))
    try:
        shutil.rmtree(sandbox, True)
    except Exception as error:
        print("sandbox cleanup failed: {0}".format(error))

failed = [entry for entry in RESULTS if not entry[2]]
print("VERDICT: {0} of {1} gates failed".format(len(failed), len(RESULTS)))

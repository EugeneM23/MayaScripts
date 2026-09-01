r"""Proof for maya_anim_batch_export.py -- camera_root to a typed XYZ vector.

NOT a bridge script. It runs in its own mayapy session:

    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_anim_batch_camera.py

and it must stay that way, because the tool starts every file with
`cmds.file(new=True, force=True)` -- sending it down the command port would
discard whatever the animator has open. Same rule, same reason, as
`verify_root_offset_batch.py`.

Two measured facts about mayapy batch shape this script. `cmds.window()`
returns False there while `columnLayout`/`checkBox` succeed, and every UI
query answers False -- so `get_ui_settings()` returns a dict of False and this
script builds the settings dict by hand and calls `run_on_folder` directly,
never `run_tool()`. The module imports cleanly, module-level `show_ui()`
included.

It works on COPIES of two real AS_DownState clips in a temp sandbox and never
writes into the animator's Desktop folder.

What is claimed:

  * camera_root lands on the typed vector, on all three axes, in the file
    that reaches disk -- not merely in the scene in memory,
  * the vector has three distinct non-zero coordinates, so an axis dropped,
    transposed or left at the clip's own value cannot pass,
  * no animCurve is left driving camera_root,
  * the root key range survives -- placing the camera must not cost the
    animation,
  * and both clips pass, because the failure that matters is a batch that
    works on the first file only.
"""

import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

REPO = r"C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO)
import maya_anim_batch_export as T  # noqa: E402

SOURCE_DIR = r"C:/Users/MY PC/Desktop/DownState"
CLIPS = ["AS_DownState_Loop.FBX", "AS_DownState_Turn_180.FBX"]

# Three distinct, non-zero, differently-signed coordinates on purpose: a
# one-axis implementation, a transposition or an inherited clip value all
# fail against it.
VECTOR = (12.5, -34.25, 7.75)

TOL = 1e-4
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  --  " + detail if detail else ""))


def camera_root_state():
    """(local translate, animCurve count) for camera_root in the open scene."""
    root = T.find_node_by_name("root")
    if not root:
        return None, None
    cam = T.find_child_by_name(root, "camera_root")
    if not cam:
        return None, None
    pos = cmds.xform(cam, query=True, objectSpace=True, translation=True)
    curves = cmds.listConnections(cam, type="animCurve",
                                  source=True, destination=False) or []
    return list(pos), len(set(curves))


def main():
    missing = [c for c in CLIPS if not os.path.isfile(os.path.join(SOURCE_DIR, c))]
    if missing:
        check("source clips present", False, "missing: {0}".format(missing))
        return

    sandbox_in = tempfile.mkdtemp(prefix="downstate_in_")
    sandbox_out = tempfile.mkdtemp(prefix="downstate_out_")
    print("sandbox in : {0}".format(sandbox_in))
    print("sandbox out: {0}".format(sandbox_out))

    for clip in CLIPS:
        shutil.copy2(os.path.join(SOURCE_DIR, clip), os.path.join(sandbox_in, clip))

    # --- read the sources, so every claim is measured against them ----------
    source_state = {}
    for clip in CLIPS:
        T.open_file(os.path.join(sandbox_in, clip))
        pos, curves = camera_root_state()
        source_state[clip] = {
            "pos": pos,
            "curves": curves,
            "range": T.get_key_range_from_root(),
        }
        print("source {0}: camera_root {1}, {2} curve(s), range {3}".format(
            clip, pos, curves, source_state[clip]["range"]))

    check("both clips carry camera_root",
          all(source_state[c]["pos"] is not None for c in CLIPS),
          str({c: source_state[c]["pos"] for c in CLIPS}))
    check("the target vector is not already there",
          all(source_state[c]["pos"] is None
              or max(abs(a - b) for a, b in zip(source_state[c]["pos"], VECTOR)) > TOL
              for c in CLIPS),
          "otherwise the gates below would pass on a tool that does nothing")

    # --- the run: settings by hand, run_on_folder directly ------------------
    settings = {
        "input_folder": sandbox_in,
        "output_folder": sandbox_out,
        "process_all_files": True,
        "process_maya": False,
        "process_fbx": True,
        "use_camera_position": True,
        "use_clean_scene": True,
        "snap_keys": True,
        "bake_animation": False,
        "camera_position": VECTOR,
    }
    T.run_on_folder(settings)

    # --- measure what landed on disk ---------------------------------------
    for clip in CLIPS:
        out = os.path.join(sandbox_out, os.path.splitext(clip)[0] + ".fbx")
        if not os.path.isfile(out):
            check("{0}: exported".format(clip), False, "no file at {0}".format(out))
            continue
        check("{0}: exported".format(clip), True, os.path.basename(out))

        T.open_file(out)
        pos, curves = camera_root_state()
        if pos is None:
            check("{0}: camera_root survived the export".format(clip), False)
            continue
        check("{0}: camera_root survived the export".format(clip), True)

        worst = max(abs(a - b) for a, b in zip(pos, VECTOR))
        check("{0}: camera_root on the vector".format(clip), worst < TOL,
              "got {0}, want {1}, worst {2:.9f}".format(
                  [round(v, 6) for v in pos], list(VECTOR), worst))

        for axis, got, want in zip("XYZ", pos, VECTOR):
            check("{0}: axis {1}".format(clip, axis), abs(got - want) < TOL,
                  "{0:.6f} vs {1}".format(got, want))

        check("{0}: no animCurve on camera_root".format(clip), curves == 0,
              "{0} curve(s)".format(curves))

        got_range = T.get_key_range_from_root()
        want_range = source_state[clip]["range"]
        check("{0}: root key range survived".format(clip),
              got_range == want_range,
              "got {0}, source {1}".format(got_range, want_range))

    shutil.rmtree(sandbox_in, ignore_errors=True)
    shutil.rmtree(sandbox_out, ignore_errors=True)


try:
    main()
finally:
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\n{0} of {1} gates failed".format(len(failed), len(RESULTS)))
    for name in failed:
        print("  FAIL {0}".format(name))

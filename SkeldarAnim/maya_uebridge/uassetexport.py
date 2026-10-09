"""Overwrite one AnimSequence straight from the scene. No Perforce on this road.

The Export tab already puts the scene back into a uasset, but only the long
way: resolve the working fbx, `p4 edit`, place it, reimport. This is the short
way the animator asked for on 2026-09-01 -- a button on the IMPORT tab,
a confirm, and the selected asset takes the scene's animation.

Two things it deliberately does NOT do, both by request:

  * it touches Perforce nowhere. Not an fstat, not an edit, not an add. The
    consequence -- a uasset modified on disk with no changelist behind it --
    is said out loud in the dialog instead of worked around. This module
    imports `records` for the pure package<->path pair rather than `vcs`,
    which is what makes that claim testable (a subprocess test asserts
    `maya_uebridge.vcs` never reaches sys.modules through here).
  * it does not put the read-only flag back. The file genuinely is modified
    afterwards, and restoring the flag would hide that.

Order is the import direction's, for the same reasons: everything that can
refuse refuses first (a refusal must cost nothing), the FBX goes to a temp
file BEFORE the read-only flag is touched (a failed export must leave the
uasset exactly as it was), and the editor is asked last.

Design: docs/superpowers/specs/2026-09-01-uasset-export-design.md
"""

import os

import maya.cmds as cmds

from maya_uebridge import animexport
from maya_uebridge import animimport
from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts
from maya_uebridge.uasset_core import (LOST_CURVES, clear_read_only,
                                       fbx_staging_path, is_read_only,
                                       readonly_note)

NO_SELECTION = "select an animation first"
NO_CONTENT_DIR = ("press Refresh first - the project's Content folder is "
                  "not known yet")
NO_UASSET = "no uasset at {0}"
CANCELLED = "cancelled - {0} untouched"
READONLY_FAILED = "cannot clear read-only on {0}: {1}"

CONFIRM = "Overwrite"
CANCEL = "Cancel"


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def refusal(record, content_dir, uasset, uasset_exists):
    """Why the press must not run, or "". Pure: the scene arrives as data."""
    if record is None:
        return NO_SELECTION
    if not content_dir:
        return NO_CONTENT_DIR
    if not uasset_exists:
        return NO_UASSET.format(uasset)
    return ""


def overwrite_message(name, package, root, read_only):
    """The confirm dialog's text. Pure, so the wording is tested.

    It names the three things actually at stake rather than asking "are you
    sure": what is lost, that Perforce is not involved, and the flag.
    """
    lines = [
        "Overwrite the animation in {0}?".format(name),
        "",
        "    asset:    {0}".format(package),
        "    skeleton: {0}".format(root.split("|")[-1] if root else "?"),
        "",
        "The asset is REBUILT from an FBX of the scene, so curves the FBX",
        "does not carry do not survive it ({0}).".format(LOST_CURVES),
        "",
        "Perforce is not touched: the uasset is written on disk with no",
        "changelist behind it.",
    ]
    if read_only:
        lines += ["",
                  "The file is read-only. That flag will be CLEARED and left"
                  " off."]
    return "\n".join(lines)


def result_line(name, info, payload, extra=()):
    """The whole status line for one press. Pure.

    Parts are dropped when empty, so a clean export on a writable file reads
    as one short sentence instead of a row of blanks.
    """
    parts = [animexport.export_line(name, info),
             records.reimport_line(payload),
             # The silent no-op: a "successful" import that wrote nothing.
             records.unchanged_warning(payload)]
    parts.extend(extra)
    error = (payload or {}).get("error")
    if error:
        parts.append("editor: " + str(error))
    return "  |  ".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# the file
# ---------------------------------------------------------------------------

def _ask_overwrite(message):
    """The confirm dialog. Cancel is both the default and the dismiss.

    Injectable through `asks` because a modal raised over the command port
    blocks Maya's idle queue, and every live proof here runs over that port.
    """
    answer = cmds.confirmDialog(
        title="Export to uasset",
        message=message,
        button=[CONFIRM, CANCEL],
        defaultButton=CANCEL,
        cancelButton=CANCEL,
        dismissString=CANCEL)
    return answer == CONFIRM


# ---------------------------------------------------------------------------
# the press
# ---------------------------------------------------------------------------

def export_to_uasset(record, content_dir, project, temp_folder, asks=None):
    """Scene -> temp fbx -> the uasset, and nothing else. Returns the status.

    `temp_folder` is passed in rather than imported: `window.temp_folder()`
    is the caller's, and taking it as an argument keeps this module free of
    the window.
    """
    asks = asks or {}
    confirm = asks.get("confirm", _ask_overwrite)
    run_script = asks.get("run_script", uelink.run_script)

    uasset = (records.uasset_path_of(record.package, content_dir)
              if record is not None and content_dir else "")
    problem = refusal(record, content_dir, uasset,
                      bool(uasset) and os.path.isfile(uasset))
    if problem:
        return problem

    # Before the dialog: an undecidable skeleton must not cost a click.
    try:
        root = animexport.resolve_root()
    except RuntimeError as exc:
        return str(exc)

    read_only = is_read_only(uasset)
    if not confirm(overwrite_message(record.name, record.package, root,
                                    read_only)):
        return CANCELLED.format(record.name)

    # The export first, and into a temp file: a failed export must leave the
    # uasset exactly as it was, flag included.
    fbx = fbx_staging_path(record.name, temp_folder)
    info = animexport.export_hierarchy(fbx, root=root, layout=animexport.UNREAL_LAYOUT)

    if read_only:
        failure = clear_read_only(uasset)
        if failure:
            return READONLY_FAILED.format(uasset, failure)

    out = os.path.join(temp_folder, "uasset_reimport.json")
    payload = run_script(
        uescripts.reimport_script(out, record.package, fbx),
        out, project=project)

    extra = [readonly_note(read_only),
             # The scene's frame rate is never written; a mismatch is said
             # out loud and UE resamples the clip.
             animimport.fps_warning(record.fps, animimport.scene_fps())]
    return result_line(record.name, info, payload, extra)

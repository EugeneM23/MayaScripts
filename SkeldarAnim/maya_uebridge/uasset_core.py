"""The Maya-free part of the uasset road, shared with the Cascadeur bridge.

uassetexport keeps its Maya flow and imports these names from here, so the
Maya module's public names do not change. Stdlib only.
"""

import os
import stat

# What a replace-import throws away, named in the dialog. Measured on one
# real UE clip (trap 40): 135 such curves against 9 transform channels.
LOST_CURVES = "Pose_0..9, MoveData_*, DisableLegIK, RootMotionAdditiveInput"


def is_read_only(path):
    """True when the file exists and cannot be written to.

    `os.access(W_OK)` rather than the mode bits: it is what actually decides
    whether the editor's save will succeed.
    """
    return os.path.isfile(path) and not os.access(path, os.W_OK)


def clear_read_only(path):
    """Take the read-only flag off. Returns "" or the reason it failed."""
    try:
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IWRITE | stat.S_IWUSR)
    except OSError as exc:
        return str(exc)
    if not os.access(path, os.W_OK):
        return "still not writable"
    return ""


def fbx_staging_path(name, folder):
    """Where the intermediate FBX goes. Named for what it is, so a leftover
    in the temp folder says which button wrote it."""
    return os.path.join(folder, "{0}.uasset.fbx".format(name))


def readonly_note(cleared):
    """What the status says about the flag. Pure."""
    return "read-only cleared" if cleared else ""

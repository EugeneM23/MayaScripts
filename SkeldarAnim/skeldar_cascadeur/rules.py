"""The Cascadeur bridge's pure rules: what may run, and what the status says.

Stdlib only. Every refusal is a sentence that names what did not change.
"""

import math

EXPECTED_FPS = 30.0

NO_SKELETON = "the scene holds no skeleton - nothing to export"
SEVERAL_SKELETONS = ("the scene holds {0} skeletons ({1}) - keep one, "
                     "export refused")
NO_TARGET = ("no Unreal animation to write back to - select one in the "
             "list, or import a clip first")
NO_UASSET = "no uasset at {0} - nothing changed"


def skeleton_problem(roots):
    """Why an export must not run, or "". `roots` is the scene's root joints."""
    roots = list(roots or [])
    if not roots:
        return NO_SKELETON
    if len(roots) > 1:
        return SEVERAL_SKELETONS.format(len(roots), ", ".join(sorted(roots)))
    return ""


def export_refusal(package, uasset, uasset_exists):
    """Why the write-back must not run, or "". Pure: the disk is passed in."""
    if not package:
        return NO_TARGET
    if not uasset_exists:
        return NO_UASSET.format(uasset)
    return ""


def fps_problem(fps, expected=EXPECTED_FPS):
    """A warning when the scene's rate is not Unreal's, or "" (also when unknown)."""
    if fps is None:
        return ""
    if abs(float(fps) - float(expected)) < 1e-6:
        return ""
    return ("scene is {0:g} fps, Unreal's clip is {1:g} - UE resamples "
            "it".format(float(fps), float(expected)))


def frame_range_outward(start, end):
    """A range rounded outward to whole frames. A fractional end makes UE refuse
    the animation silently (trap 50); outward can only widen it."""
    return int(math.floor(start)), int(math.ceil(end))


def clip_tab_name(name):
    """The scene tab's name for an imported clip."""
    text = (name or "").strip()
    return text or "clip"


def join_status(parts):
    """One status line from its parts; empty parts are dropped."""
    return "  |  ".join(part for part in parts if part)

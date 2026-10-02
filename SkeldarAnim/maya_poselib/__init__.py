"""The Pose Library (2026-10-02): cards of a character's bones, applied to any rig or skeleton.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""


def __getattr__(name):
    # lazy: importing the package drags neither Qt nor Maya in (the maya_overrig rule)
    if name in ("show_window", "build_panel", "is_open"):
        from maya_poselib import window
        return getattr(window, name)
    raise AttributeError(name)

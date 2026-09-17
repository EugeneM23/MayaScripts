"""Set a shot up: weapons in the hands, a camera on the camera bone.

`show_window` is resolved lazily on first access, the way the other packages
here do it: importing it eagerly would drag maya.cmds in through the package
and break the rule that catalog.py is testable in plain Python.
"""

__all__ = ["show_window", "show_weapons"]


def __getattr__(name):
    if name == "show_window":
        from maya_scenesetup.window import show_window
        return show_window
    if name == "show_weapons":
        from maya_scenesetup.window import show_weapons
        return show_weapons
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))

"""Python wrapper around the OverRig MEL toolset.

`show_picker` is resolved lazily on first access. Importing it eagerly here
would drag maya.cmds, OpenMayaUI and Qt in through the package, which would
break the design rule that bodymap.py is testable in plain Python with no Maya
and no Qt present.
"""

__all__ = ["show_picker"]


def __getattr__(name):
    if name == "show_picker":
        from maya_overrig.picker_window import show_picker
        return show_picker
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))

"""Bridge from a running Unreal editor to Maya, for animation.

`show_window` is resolved lazily on first access. Importing it eagerly would
drag maya.cmds in through the package, which would break the design rule that
records.py, uescripts.py and uelink.py are testable in plain Python with
neither Maya nor Unreal present.
"""

__all__ = ["show_window"]


def __getattr__(name):
    if name == "show_window":
        from maya_uebridge.window import show_window
        return show_window
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))

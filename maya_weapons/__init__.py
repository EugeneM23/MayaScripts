"""Put weapon models into a character's hands.

`show_window` is resolved lazily on first access, the way the other packages
here do it: importing it eagerly would drag maya.cmds in through the package
and break the rule that catalog.py is testable in plain Python.
"""

__all__ = ["show_window"]


def __getattr__(name):
    if name == "show_window":
        from maya_weapons.window import show_window
        return show_window
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))

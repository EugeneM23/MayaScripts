"""Curve Overlay: the graph editor drawn over the viewport.

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_curveview; maya_curveview.toggle()

Design: docs/superpowers/specs/2026-09-05-viewport-curve-overlay-design.md

`toggle` is resolved through `__getattr__` so importing the package drags in
neither Qt nor Maya -- `mapping.py` is proved pure by a subprocess test that
imports it in a bare interpreter, and that test imports this file first.
Making the import eager would break it, and with it every plain-Python test.
"""

__all__ = ["toggle", "enable", "disable", "is_on", "refresh"]


def __getattr__(name):
    if name in __all__:
        from maya_curveview import tool
        return getattr(tool, name)
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))


def __dir__():
    return sorted(list(globals()) + __all__)

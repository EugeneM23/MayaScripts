"""maya_graphoverlay - Maya's own Graph Editor over the viewport, see-through.

    import maya_graphoverlay; maya_graphoverlay.toggle()      # alt+c in our set

The names are resolved lazily so that importing the package drags in neither
Qt nor numpy nor Maya - the pure halves are tested without any of them.
Spec: docs/superpowers/specs/2026-09-30-graph-overlay-design.md
"""

_EXPORTS = ("toggle", "enable", "disable", "is_on", "show_window",
            "build_panel", "is_open")


def __getattr__(name):
    if name in _EXPORTS:
        from maya_graphoverlay import mode
        return getattr(mode, name)
    raise AttributeError(name)

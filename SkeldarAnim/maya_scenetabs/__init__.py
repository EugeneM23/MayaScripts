"""Scene tabs (2026-10-15): several scenes in one Maya, switched like browser tabs.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md. `show()` is
resolved lazily so `import maya_scenetabs` pulls in neither Maya nor Qt.
"""


def __getattr__(name):
    if name == "show":
        from . import bar
        return bar.show
    raise AttributeError(name)

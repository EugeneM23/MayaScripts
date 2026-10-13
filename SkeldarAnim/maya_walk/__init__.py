"""The parametric walk (2026-10-12/13): a walk cycle read once, rebuilt from knobs, put on any skeleton.

model (numpy: the walk's mathematics), files (a saved walk / pose), target (onto any skeleton), pose (a
character pose under the walk), scene (Maya: save, apply, the marker), panel (the hub's Walk Builder card).
Importing the package imports none of them.
"""


def show_window():
    """The hub, on the Walk Builder card."""
    from . import panel
    return panel.show_window()

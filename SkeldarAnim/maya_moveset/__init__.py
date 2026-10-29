"""The Longsword moveset's combo trees in Maya: the hub card Moveset.

The card draws the trees the animator's moveset page draws, from the same files
(a folder of their own, never shipped), and opens an attack's montage slot
through the UE Bridge's montage import. Importing the package imports no Maya.
"""
HUB_SECTION = "moveset"


def show_window():
    import maya_hub
    return maya_hub.show(HUB_SECTION)

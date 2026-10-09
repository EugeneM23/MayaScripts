"""Scripts > SkeldarAnim > Bridge in Cascadeur.

Cascadeur's action discovery (python_actions_rule.get_action_info) reads
`name`, `description` and `run` from this module. `run(scene)` opens the
window once; a second press raises it. The window and the Cascadeur side are
imported only when the window opens, so discovery at Cascadeur's start stays
light and cannot fail on PySide6.
"""

import os
import sys
import tempfile

HOLDER = "_skeldar_cascadeur_bridge"


def name():
    return "SkeldarAnim.Bridge"


def description():
    return ("Unreal <-> Cascadeur: import a skeletal animation, write the "
            "scene back to its uasset, send it to Shared")


def wire(temp_dir=None):
    """The bridge object with the real ports (Unreal, Cascadeur, Shared)."""
    from PySide6 import QtWidgets
    from skeldar_cascadeur import actions
    from skeldar_cascadeur import cascade_io
    from skeldar_cascadeur import prefs
    from skeldar_cascadeur import shared
    from skeldar_cascadeur import unreal

    def ask(text):
        answer = QtWidgets.QMessageBox.question(
            None, "SkeldarAnim - Bridge", text,
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        return answer == QtWidgets.QMessageBox.Ok

    folder = temp_dir or os.path.join(tempfile.gettempdir(), "skeldar_cascadeur")
    return actions.Bridge(unreal, cascade_io, shared, prefs.default_path(),
                          folder, ask)


def run(scene):
    """Open the bridge window, or raise the one already open."""
    from skeldar_cascadeur import window

    existing = getattr(sys, HOLDER, None)
    if existing is not None and existing.isVisible():
        existing.raise_()
        existing.activateWindow()
        return existing
    win = window.BridgeWindow(wire())
    setattr(sys, HOLDER, win)
    win.show()
    return win

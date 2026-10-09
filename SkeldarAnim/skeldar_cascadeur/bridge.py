"""Scripts > SkeldarAnim > Bridge in Cascadeur.

Cascadeur's action discovery (python_actions_rule.get_action_info) reads
`name`, `description` and `run` from this module. `run(scene)` opens the QML
window once; a second press raises it. The view, the model and the Cascadeur
side are imported only when the window opens, so discovery at Cascadeur's start
stays light.

The window is QML on a QQmlApplicationEngine, not QtWidgets: Cascadeur is a
QGuiApplication, and a QWidget there aborted the process (2026-10-09).
"""

import os
import sys
import tempfile

ENGINE = "_skeldar_cascadeur_engine"
MODEL = "_skeldar_cascadeur_model"


def name():
    return "SkeldarAnim.Bridge"


def description():
    return ("Unreal <-> Cascadeur: import a skeletal animation, write the "
            "scene back to its uasset, send it to Shared")


def wire(temp_dir=None):
    """The bridge object with the real ports (Unreal, Cascadeur, Shared)."""
    from skeldar_cascadeur import actions
    from skeldar_cascadeur import cascade_io
    from skeldar_cascadeur import prefs
    from skeldar_cascadeur import shared
    from skeldar_cascadeur import unreal

    folder = temp_dir or os.path.join(tempfile.gettempdir(), "skeldar_cascadeur")
    # `ask` is only used by Bridge.export_to_uasset (synchronous callers); the
    # window goes through plan_export and cascade_io.confirm instead.
    return actions.Bridge(unreal, cascade_io, shared, prefs.default_path(),
                          folder, lambda text: False)


def run(scene):
    """Open the bridge window, or raise the one already open."""
    from PySide6 import QtCore, QtQml
    from skeldar_cascadeur import cascade_io
    from skeldar_cascadeur import window

    engine = getattr(sys, ENGINE, None)
    if engine is not None and engine.rootObjects():
        root = engine.rootObjects()[0]
        root.setProperty("visible", True)
        root.requestActivate()
        return root

    model = window.BridgeModel(wire(), cascade_io.confirm)
    engine = QtQml.QQmlApplicationEngine()
    engine.rootContext().setContextProperty("bridge", model)
    engine.load(QtCore.QUrl.fromLocalFile(window.VIEW_FILE))
    if not engine.rootObjects():
        raise RuntimeError("the bridge view did not load: " + window.VIEW_FILE)
    setattr(sys, ENGINE, engine)
    setattr(sys, MODEL, model)
    return engine.rootObjects()[0]

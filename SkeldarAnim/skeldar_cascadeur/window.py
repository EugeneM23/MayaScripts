"""The Cascadeur bridge window: a QML view over a Python model.

Why QML and not QtWidgets: Cascadeur runs as a QGuiApplication. Creating a
QWidget inside it aborted the whole process (live, 2026-10-09: Qt6Core fast-fail
0xc0000409). Cascadeur's own Python dialogs are QML for the same reason.

BridgeModel holds the state the view shows and answers its calls. It imports no
csc and no QtWidgets, so the tests exercise it without Cascadeur.
Module-level functions here are NOT named `run` or `name`: Cascadeur's action
discovery treats a module with `run` as a menu action (only bridge.py is one).
"""

import os

from PySide6 import QtCore

VIEW_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "view.qml")


class BridgeModel(QtCore.QObject):
    """What the QML view shows, and the calls it makes.

    `confirm(text, on_yes)` shows Cascadeur's own dialog and calls `on_yes`
    only when the animator says yes. It is injected (bridge.py wires it to
    csc.view.DialogManager; tests pass a fake).
    """

    changed = QtCore.Signal()

    def __init__(self, bridge, confirm, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self._confirm = confirm
        self._filter = ""
        self._status = ""
        self._target = ""
        self._author = ""
        self._picked = []
        self._refresh_target()

    # ---- properties the view reads -----------------------------------------

    def _names(self):
        return [rec.name for rec in self._bridge.records]

    @QtCore.Property("QStringList", notify=changed)
    def clipNames(self):
        needle = self._filter.lower()
        return [name for name in self._names() if needle in name.lower()]

    @QtCore.Property(str, notify=changed)
    def statusText(self):
        return self._status

    @QtCore.Property(str, notify=changed)
    def targetText(self):
        return self._target

    # ---- slots the view calls ----------------------------------------------

    @QtCore.Slot(str)
    def setFilter(self, text):
        self._filter = text or ""
        self.changed.emit()

    @QtCore.Slot(str)
    def setAuthor(self, text):
        self._author = text or ""

    @QtCore.Slot()
    def refresh(self):
        self._say(self._bridge.refresh())
        self.changed.emit()

    @QtCore.Slot("QStringList")
    def pick(self, names):
        """The names the animator has selected in the list."""
        self._picked = list(names or [])

    @QtCore.Slot()
    def importPicked(self):
        picked = [rec for rec in self._bridge.records if rec.name in self._picked]
        if not picked:
            self._say("select one or more animations first")
            return
        self._say(self._bridge.import_clips(picked))
        self._refresh_target()

    @QtCore.Slot()
    def exportPicked(self):
        picked = [rec for rec in self._bridge.records if rec.name in self._picked]
        record = picked[0] if len(picked) == 1 else None
        refusal, plan = self._bridge.plan_export(record)
        if refusal:
            self._say(refusal)
            return

        def on_yes():
            self._say(self._bridge.run_export(plan))
            self._refresh_target()
            self.changed.emit()

        self._confirm(plan.confirm_text, on_yes)

    @QtCore.Slot(str, str)
    def sendPicked(self, typed_name, author):
        self._say(self._bridge.send_to_shared(typed_name, author or self._author))

    # ---- helpers -----------------------------------------------------------

    def _say(self, text):
        self._status = text
        self.changed.emit()

    def _refresh_target(self):
        rec = getattr(self._bridge, "target", None)
        self._target = ("Write-back target: " + rec.package) if rec is not None \
            else "Write-back target: none - import a clip first"
        self.changed.emit()

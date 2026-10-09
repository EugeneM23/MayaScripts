"""The Cascadeur bridge window. Plain PySide6 widgets; every button calls the
bridge object (actions.Bridge), which holds the logic and is tested without Qt.

Module-level functions here are NOT named `run` or `name`: Cascadeur's action
discovery treats a module with `run` as a menu action (only bridge.py is one).
"""

from PySide6 import QtCore, QtWidgets


class BridgeWindow(QtWidgets.QWidget):

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setObjectName("skeldarCascadeurBridge")
        self.setWindowTitle("SkeldarAnim - Bridge")
        self.resize(460, 620)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Unreal animations"))

        row = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("search")
        self.search.textChanged.connect(self._filter)
        row.addWidget(self.search, 1)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)

        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list, 1)

        self.import_button = QtWidgets.QPushButton("Import into Cascadeur")
        self.import_button.clicked.connect(self.import_selected)
        layout.addWidget(self.import_button)

        layout.addWidget(QtWidgets.QLabel("Cascadeur scene"))
        self.export_button = QtWidgets.QPushButton("Export to uasset")
        self.export_button.clicked.connect(self.export_selected)
        layout.addWidget(self.export_button)

        self.author = QtWidgets.QLineEdit()
        self.author.setPlaceholderText("author")
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("name of the upload")
        layout.addWidget(self.author)
        layout.addWidget(self.name)
        self.send_button = QtWidgets.QPushButton("Send to Shared")
        self.send_button.clicked.connect(self.send_selected)
        layout.addWidget(self.send_button)

        self.target = QtWidgets.QLabel("")
        layout.addWidget(self.target)
        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.populate()
        self._show_target()

    # ---- the list ---------------------------------------------------------

    def populate(self):
        self.list.clear()
        for rec in self.bridge.records:
            item = QtWidgets.QListWidgetItem(rec.name)
            item.setData(QtCore.Qt.UserRole, rec.package)
            self.list.addItem(item)
        self._filter(self.search.text())

    def visible_names(self):
        return [self.list.item(i).text() for i in range(self.list.count())
                if not self.list.item(i).isHidden()]

    def _filter(self, text):
        needle = (text or "").lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(needle not in item.text().lower())

    def _picked(self):
        by_name = {rec.name: rec for rec in self.bridge.records}
        return [by_name[item.text()] for item in self.list.selectedItems()
                if item.text() in by_name]

    # ---- the buttons ------------------------------------------------------

    def refresh(self):
        self._say(self.bridge.refresh())
        self.populate()

    def import_selected(self):
        picked = self._picked()
        if not picked:
            return self._say("select one or more animations first")
        self._say(self.bridge.import_clips(picked))
        self._show_target()

    def export_selected(self):
        picked = self._picked()
        record = picked[0] if len(picked) == 1 else None
        self._say(self.bridge.export_to_uasset(record))
        self._show_target()

    def send_selected(self):
        self._say(self.bridge.send_to_shared(self.name.text(), self.author.text()))

    # ---- helpers ----------------------------------------------------------

    def _say(self, text):
        self.status.setText(text)

    def _show_target(self):
        rec = getattr(self.bridge, "target", None)
        self.target.setText("Write-back target: {0}".format(
            rec.package if rec is not None else "none - import a clip first"))

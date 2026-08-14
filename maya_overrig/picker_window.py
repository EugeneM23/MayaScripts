"""Maya-facing shell for the OverRig picker.

Owns every interaction with the scene. The view below it stays Maya-free.
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance

from maya_overrig import bodymap, naming
from maya_overrig.picker_view import MODE_ADD, MODE_TOGGLE, PickerView, mode_for

WINDOW_OBJECT_NAME = "overRigPickerWindow"
WINDOW_TITLE = "OverRig Picker"

_GROUP_BUTTONS = (
    ("All", "all"), ("Main", "main"), ("Spine", "spine"), ("Head", "head"),
    ("Arm L", "arm_l"), ("Arm R", "arm_r"),
    ("Hand L", "hand_l"), ("Hand R", "hand_r"),
    ("Leg L", "leg_l"), ("Leg R", "leg_r"),
)

_GROUP_STYLE = (
    "QPushButton { background: #3c3c3c; color: #d8d8d8; border: none; "
    "padding: 4px; border-radius: 3px; }"
    "QPushButton:hover { background: #4a4a4a; }"
)


def maya_main_window():
    """Return Maya's main window as a QWidget so the panel parents correctly."""
    pointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget)


class PickerWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(PickerWindow, self).__init__(parent or maya_main_window())
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(660, 540)

        # Guards against the selection feedback loop: we set the scene
        # selection, Maya fires SelectionChanged, we would repaint and could
        # loop. The callback returns early while this is set.
        self._applying = False
        self._script_job = None

        self._joint_to_id = {b.joint: b.id for b in bodymap.BUTTONS}

        self.view = PickerView(self)
        self.view.selection_requested.connect(self.apply_selection)
        self.view.hovered.connect(self._on_hover)

        central = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_groups())
        layout.addWidget(self.view, 1)
        self.setCentralWidget(central)

        self.status = self.statusBar()
        self.status.showMessage("")

        self.refresh_availability()
        self.sync_from_scene()
        self._install_script_job()

    def _build_toolbar(self):
        bar = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)

        refresh = QtWidgets.QPushButton("Refresh", bar)
        refresh.setStyleSheet(_GROUP_STYLE)
        refresh.clicked.connect(lambda _checked=False: self.refresh_availability())
        row.addWidget(refresh)
        row.addStretch(1)

        for label in ("Build", "Bake+Delete"):
            button = QtWidgets.QPushButton(label, bar)
            button.setEnabled(False)
            button.setToolTip("Not implemented yet")
            row.addWidget(button)

        return bar

    def _build_groups(self):
        box = QtWidgets.QWidget(self)
        grid = QtWidgets.QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for index, (label, group) in enumerate(_GROUP_BUTTONS):
            button = QtWidgets.QPushButton(label, box)
            button.setStyleSheet(_GROUP_STYLE)
            button.clicked.connect(
                lambda _checked=False, g=group: self._select_group(g))
            grid.addWidget(button, index // 5, index % 5)
        return box

    def _select_group(self, group):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.apply_selection(list(bodymap.group_members(group)),
                             mode_for(modifiers))

    def _on_hover(self, button_id):
        self.status.showMessage(button_id)

    def refresh_availability(self):
        """Dim buttons whose joint is not in the scene."""
        found = naming.resolve_many([b.joint for b in bodymap.BUTTONS])
        available = [self._joint_to_id[j] for j in found]
        self.view.set_available(available)

        missing = len(bodymap.BUTTONS) - len(available)
        if not available:
            self.status.showMessage(
                "No matching skeleton in the scene - every button disabled")
        elif missing:
            self.status.showMessage("{0} joint(s) missing".format(missing))
        else:
            self.status.showMessage("")

    def apply_selection(self, ids, mode):
        """Translate a picker request into a Maya selection change."""
        wanted_joints = [bodymap.button_by_id(i).joint for i in ids]
        resolved = naming.resolve_many(wanted_joints)
        paths = [resolved[j] for j in wanted_joints if j in resolved]
        if not paths:
            return

        self._applying = True
        try:
            if mode == MODE_ADD:
                cmds.select(paths, add=True)
            elif mode == MODE_TOGGLE:
                cmds.select(paths, toggle=True)
            else:
                cmds.select(paths, replace=True)
        finally:
            self._applying = False

        self.sync_from_scene()

    def sync_from_scene(self):
        """Repaint button states from the current Maya selection."""
        selected = cmds.ls(selection=True, long=True) or []
        leaves = {naming.leaf(node) for node in selected}
        ids = [self._joint_to_id[j] for j in leaves if j in self._joint_to_id]
        self.view.set_selected(ids)

    def _on_scene_selection_changed(self):
        if self._applying:
            return
        self.sync_from_scene()

    def _install_script_job(self):
        self._script_job = cmds.scriptJob(
            event=["SelectionChanged", self._on_scene_selection_changed],
            protected=False)

    def _kill_script_job(self):
        if self._script_job is not None and cmds.scriptJob(exists=self._script_job):
            cmds.scriptJob(kill=self._script_job, force=True)
        self._script_job = None

    def closeEvent(self, event):
        # Left alive, the job keeps firing into a dead widget and spams errors.
        self._kill_script_job()
        super(PickerWindow, self).closeEvent(event)


def show_picker():
    """Open the picker, replacing any window left from a previous call."""
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            widget.close()
            widget.deleteLater()

    window = PickerWindow()
    window.show()
    return window

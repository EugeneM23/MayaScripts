"""Maya-facing shell for the Rig Picker.

Owns every interaction with the scene. The view below it stays Maya-free.

The panel is bound to one skeleton at a time. Binding is explicit: select any
joint of the character -- or the group holding it -- and press Connect. The
root is remembered by UUID, so renaming it or dropping the character into a
group does not break the link.
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance

from maya_overrig import bodymap, builder, naming
from maya_overrig.picker_view import MODE_ADD, MODE_TOGGLE, PickerView, mode_for

WINDOW_OBJECT_NAME = "rigPickerWindow"
WINDOW_TITLE = "Rig Picker"

_GROUP_BUTTONS = (
    ("All", "all"), ("Main", "main"), ("Spine", "spine"), ("Head", "head"),
    ("Arm L", "arm_l"), ("Arm R", "arm_r"),
    ("Hand L", "hand_l"), ("Hand R", "hand_r"),
    ("Leg L", "leg_l"), ("Leg R", "leg_r"),
)

_BUTTON_STYLE = (
    "QPushButton { background: #3c3c3c; color: #d8d8d8; border: none; "
    "padding: 4px; border-radius: 3px; }"
    "QPushButton:hover { background: #4a4a4a; }"
    "QPushButton:disabled { color: #6a6a6a; }"
)

_CONNECT_STYLE = (
    "QPushButton { background: #45607a; color: #e8e8e8; border: none; "
    "padding: 4px 12px; border-radius: 3px; }"
    "QPushButton:hover { background: #52738f; }"
)

_UNBOUND_MESSAGE = "Not connected - select the character and press Connect"


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
        self.resize(660, 560)

        # Guards against the selection feedback loop: we set the scene
        # selection, Maya fires SelectionChanged, we would repaint and could
        # loop. The callback returns early while this is set.
        self._applying = False
        self._script_job = None

        # The bound skeleton. `_scene_map` is leaf name -> long DAG path and is
        # the ONLY route from a button to a scene object, which is what keeps a
        # second character out of the picture.
        self._root_uuid = None
        self._scene_map = {}
        self._prefix = ""

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

        self.auto_connect()
        self._install_script_job()

    # -- construction --------------------------------------------------------

    def _build_toolbar(self):
        bar = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        connect = QtWidgets.QPushButton("Connect", bar)
        connect.setStyleSheet(_CONNECT_STYLE)
        connect.setToolTip(
            "Bind the picker to the selected character.\n"
            "Any joint of the character will do, or the group holding it.")
        connect.clicked.connect(lambda _checked=False: self.connect_to_selection())
        row.addWidget(connect)

        self.bound_label = QtWidgets.QLabel("", bar)
        self.bound_label.setStyleSheet("QLabel { color: #9a9a9a; }")
        row.addWidget(self.bound_label)

        row.addStretch(1)

        self.build_button = QtWidgets.QPushButton("Build", bar)
        self.build_button.setStyleSheet(_BUTTON_STYLE)
        self.build_button.setToolTip(
            "Create IK on both arms and both legs.\n"
            "Pressing again rebuilds from scratch.")
        self.build_button.clicked.connect(lambda _checked=False: self.build_rig())
        row.addWidget(self.build_button)

        teardown_button = QtWidgets.QPushButton("Bake+Delete", bar)
        teardown_button.setStyleSheet(_BUTTON_STYLE)
        teardown_button.setEnabled(False)
        teardown_button.setToolTip("Not implemented yet")
        row.addWidget(teardown_button)

        return bar

    def _build_groups(self):
        box = QtWidgets.QWidget(self)
        grid = QtWidgets.QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for index, (label, group) in enumerate(_GROUP_BUTTONS):
            button = QtWidgets.QPushButton(label, box)
            button.setStyleSheet(_BUTTON_STYLE)
            button.clicked.connect(
                lambda _checked=False, g=group: self._select_group(g))
            grid.addWidget(button, index // 5, index % 5)
        return box

    # -- binding -------------------------------------------------------------

    def connect_to_selection(self):
        """Bind to the character reachable from the current selection."""
        selected = cmds.ls(selection=True, long=True) or []
        if not selected:
            self.status.showMessage(
                "Nothing selected - pick a joint of the character first")
            return

        root = naming.find_root(selected[0])
        if not root:
            self.status.showMessage(
                "No skeleton found under {0}".format(selected[0].split("|")[-1]))
            return

        self._bind(root)

    def auto_connect(self):
        """Bind without asking when the scene holds exactly one skeleton."""
        roots = builder.character_roots()
        if len(roots) == 1:
            self._bind(roots[0])
            return
        self._root_uuid = None
        self._scene_map = {}
        self._prefix = ""
        self._refresh_view()
        if len(roots) > 1:
            self.status.showMessage(
                "{0} skeletons in the scene - select one and press "
                "Connect".format(len(roots)))
        else:
            self.status.showMessage(_UNBOUND_MESSAGE)

    def _bind(self, root):
        self._root_uuid = naming.uuid_of(root)

        # Rigs often arrive with every joint prefixed. The prefix is worked out
        # once for the whole skeleton, so the body map's plain UE5 names line up
        # without each button having to guess.
        raw = naming.hierarchy_map(root)
        self._prefix = naming.detect_prefix(raw, self._joint_to_id)
        self._scene_map = naming.strip_prefix(raw, self._prefix)

        self._refresh_view()
        self.sync_from_scene()

        matched = sum(1 for j in self._joint_to_id if j in self._scene_map)
        message = "Connected to {0} - {1}/{2} buttons matched".format(
            root.split("|")[-1], matched, len(bodymap.BUTTONS))
        if self._prefix:
            message += "  (prefix '{0}')".format(self._prefix)
        self.status.showMessage(message)

    def bound_root(self):
        """Current root's DAG path, re-resolved from its UUID, or None."""
        return naming.path_from_uuid(self._root_uuid)

    def refresh(self):
        """Re-read the bound skeleton, following it through renames or moves."""
        root = self.bound_root()
        if root is None:
            self.auto_connect()
            return
        self._bind(root)

    # -- view state ----------------------------------------------------------

    def _refresh_view(self):
        """Dim every button whose joint is missing from the bound skeleton."""
        available = [self._joint_to_id[j] for j in self._scene_map
                     if j in self._joint_to_id]
        self.view.set_available(available)

        root = self.bound_root()
        if root is None:
            self.bound_label.setText("not connected")
        else:
            self.bound_label.setText(root.split("|")[-1])

    def _select_group(self, group):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.apply_selection(list(bodymap.group_members(group)),
                             mode_for(modifiers))

    def _on_hover(self, button_id):
        self.status.showMessage(button_id)

    # -- selection -----------------------------------------------------------

    def apply_selection(self, ids, mode):
        """Translate a picker request into a Maya selection change."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        paths = []
        for button_id in ids:
            joint = bodymap.button_by_id(button_id).joint
            if joint in self._scene_map:
                paths.append(self._scene_map[joint])
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

    def build_rig(self):
        """Create IK on both arms and both legs of the bound skeleton."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        self.build_button.setEnabled(False)
        try:
            result = builder.build(self._scene_map)
        finally:
            self.build_button.setEnabled(True)

        self.status.showMessage(result.message)
        self.sync_from_scene()

    def sync_from_scene(self):
        """Repaint button states from the current Maya selection.

        Membership is tested on the full DAG path, never on the bare name --
        otherwise selecting another character's `spine_03` would light up a
        button that selects ours.
        """
        selected = set(cmds.ls(selection=True, long=True) or [])
        ids = [self._joint_to_id[joint]
               for joint, dag in self._scene_map.items()
               if dag in selected and joint in self._joint_to_id]
        self.view.set_selected(ids)

    def _on_scene_selection_changed(self):
        if self._applying:
            return
        self.sync_from_scene()

    # -- lifecycle -----------------------------------------------------------

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

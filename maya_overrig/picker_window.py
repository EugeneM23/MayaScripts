"""Maya-facing shell for the Rig Picker.

Owns every interaction with the scene. The view below it stays Maya-free.

The panel is bound to one skeleton at a time. Binding is explicit: select any
joint of the character -- or the group holding it -- and press Connect. The
root is remembered by UUID, so renaming it or dropping the character into a
group does not break the link.
"""

import traceback

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance

from maya_overrig import bodymap, builder, fkcontrols, naming, pickerstate
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

_TOGGLE_STYLE = _BUTTON_STYLE + (
    "QPushButton:checked { background: #5a4a7a; color: #f0e8ff; }"
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
            "Build the rig over the current animation, replacing whatever\n"
            "is there. Default: IK arms and legs, FK spine, head and\n"
            "fingers. With FK Limbs on: FK controllers on every chain.")
        self.build_button.clicked.connect(lambda _checked=False: self.build_rig())
        row.addWidget(self.build_button)

        self.fk_limbs_button = QtWidgets.QPushButton("FK Limbs", bar)
        self.fk_limbs_button.setStyleSheet(_TOGGLE_STYLE)
        self.fk_limbs_button.setCheckable(True)
        self.fk_limbs_button.setToolTip(
            "When on, Build makes the arms and legs FK as well.")
        row.addWidget(self.fk_limbs_button)

        self.switch_button = QtWidgets.QPushButton("Switch FK/IK", bar)
        self.switch_button.setStyleSheet(_BUTTON_STYLE)
        self.switch_button.setToolTip(
            "Convert the selected arms or legs to the opposite rig type.\n"
            "With no rig on the limb, the first press builds its IK.\n"
            "FK becomes IK, IK becomes FK; animation is re-baked, and\n"
            "fingers survive on the new hand control.")
        self.switch_button.clicked.connect(
            lambda _checked=False: self.switch_selected_limbs())
        row.addWidget(self.switch_button)

        self.bake_button = QtWidgets.QPushButton("Bake+Delete", bar)
        self.bake_button.setStyleSheet(_BUTTON_STYLE)
        self.bake_button.setToolTip(
            "Bake ONLY the selected limbs/chains onto clean bones and\n"
            "remove their rig; everything else stays. Select controllers,\n"
            "bones, or picker buttons; All bakes the whole rig.")
        self.bake_button.clicked.connect(
            lambda _checked=False: self.bake_selected_limbs())
        row.addWidget(self.bake_button)

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

    def _resolution(self):
        """Button id -> controller path, for every control that exists now.

        FK controllers are our own renames, so the name lookup is trusted --
        the same trust align and Switch already place in it. IK controls go
        through the limb manifests, never by bare name. Unbound resolves
        nothing: an unconnected picker is inert by design.
        """
        if not self._scene_map:
            return {}

        fk_nodes = {}
        for joint in self._scene_map:
            if joint not in self._joint_to_id:
                continue
            paths = cmds.ls(fkcontrols.controller_name(joint),
                            long=True) or []
            fk_nodes[joint] = paths[0] if paths else None

        ik_nodes = {}
        for button in bodymap.IK_BUTTONS:
            ik_nodes[(button.limb, button.role)] = builder.ik_control(
                button.limb, button.role)

        return pickerstate.resolve(fk_nodes, ik_nodes)

    def _refresh_view(self):
        root = self.bound_root()
        if root is None:
            self.bound_label.setText("not connected")
        else:
            self.bound_label.setText(root.split("|")[-1])
        self.sync_from_scene()

    def _select_group(self, group):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        self.apply_selection(list(bodymap.group_members(group)),
                             mode_for(modifiers))

    def _on_hover(self, button_id):
        self.status.showMessage(button_id)

    # -- selection -----------------------------------------------------------

    def apply_selection(self, ids, mode):
        """Translate a picker request into a Maya selection of controllers.

        Bones are never selected -- a button acts only when its controller
        exists, which is also what the availability dimming shows.
        """
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        resolution = self._resolution()
        paths = [resolution[b] for b in ids if b in resolution]
        if not paths:
            self.status.showMessage(
                "No controller built there yet - press Build first")
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

    def _run(self, label, button, action):
        """Run a toolbar action, reporting whatever it does -- or fails at.

        An exception thrown out of a Qt slot lands in the Script Editor and
        nowhere else, so the panel looked like it had simply done nothing.
        That is exactly how a missing OverRig read as "Build does nothing":
        `apply_ForwHierarhy` was not there, the RuntimeError went where the
        user was not looking, and the status bar kept its old message.
        """
        button.setEnabled(False)
        try:
            message = action()
        except Exception as error:  # noqa: BLE001 - the panel is the report
            traceback.print_exc()   # full trace still goes to the Script Editor
            message = "{0} failed: {1}".format(label, error)
        finally:
            button.setEnabled(True)

        self.status.showMessage(message)
        self.sync_from_scene()
        return message

    def build_rig(self):
        """Build the rig, replacing any previous build of either kind.

        Hybrid by default -- IK arms and legs, FK everything else; full FK
        when the FK Limbs toggle is on. The teardown of whatever exists
        happens inside `rebuild`, so mixed post-Switch states are fine.
        """
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        self._run("Build", self.build_button, lambda: fkcontrols.rebuild(
            self._scene_map, fk_limbs=self.fk_limbs_button.isChecked()))

    def switch_selected_limbs(self):
        """Convert the selected arms/legs to the opposite rig type."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        selected = cmds.ls(selection=True, long=True) or []
        # One innermost-owner resolution for both kinds -- an arm controller
        # nested inside the torso's controllers must NOT drag those in.
        ik_limbs, fk_chains = fkcontrols.bake_targets(self._scene_map)
        # Bones resolve too: with no rig on the chain at all, the first
        # Switch press builds its IK.
        bone_owner = fkcontrols.switchable_bones(self._scene_map)
        bone_hits = {bone_owner[p] for p in selected if p in bone_owner}

        hit = set(ik_limbs) | set(fk_chains) | bone_hits
        limbs = [l for l in fkcontrols.SWITCHABLE if l in hit]
        if not limbs:
            self.status.showMessage(
                "Select an arm or leg - a controller, a bone, or its "
                "picker button")
            return

        self._run("Switch", self.switch_button,
                  lambda: fkcontrols.switch_limbs(self._scene_map, limbs)[2])

    def bake_selected_limbs(self):
        """Bake ONLY what the selection touches back to clean bones.

        Everything else in the scene keeps its rig. IK limbs take their
        riding finger chains down with them; FK chains bake per chain,
        expanding to whatever rides inside them.
        """
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        ik_limbs, fk_chains = fkcontrols.bake_targets(self._scene_map)
        if not ik_limbs and not fk_chains:
            self.status.showMessage(
                "Select a rigged element - a controller, a bone, or a "
                "picker button")
            return

        self._run("Bake+Delete", self.bake_button,
                  lambda: fkcontrols.bake_selection(self._scene_map, ik_limbs,
                                                    fk_chains))

    def sync_from_scene(self):
        """Repaint availability and selection from the scene as it is now.

        Availability is recomputed on every sync -- builds, bakes, switches
        and manual deletes all change which controllers exist, and the sync
        after each is what keeps the dimming honest. Selection membership is
        tested on full DAG paths, never bare names -- otherwise another
        character's same-named controller would light our buttons up.
        """
        resolution = self._resolution()
        self.view.set_available(list(resolution))

        selected = set(cmds.ls(selection=True, long=True) or [])
        self.view.set_selected(
            pickerstate.selected_ids(resolution, selected))

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

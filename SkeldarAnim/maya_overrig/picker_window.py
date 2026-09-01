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

from maya_overrig import (active, aimrig, bodymap, builder, fkcontrols,
                          manifest, naming, pickerstate)
from maya_overrig.picker_view import MODE_ADD, MODE_TOGGLE, PickerView, mode_for

WINDOW_OBJECT_NAME = "rigPickerWindow"
WINDOW_TITLE = "Rig Picker"

# Only All survives of the group-selection row (2026-08-21, the user's
# call: «оставим только All, все остальные не нужны») - the other groups
# were the body map duplicated as buttons. The mechanism stays table-driven;
# bodymap.group_members still knows every group.
_GROUP_BUTTONS = (
    ("All", "all"),
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

        self._fk_joints = frozenset(b.joint for b in bodymap.BUTTONS)

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
            "Build the hybrid rig over the current animation, replacing\n"
            "whatever is there: IK arms and legs, FK root, spine, head and\n"
            "clavicles. Bring any limb to FK afterwards with FK Limbs.\n"
            "Fingers get no controllers - their buttons select the bones.")
        self.build_button.clicked.connect(lambda _checked=False: self.build_rig())
        row.addWidget(self.build_button)

        self.fk_limbs_button = QtWidgets.QPushButton("FK Limbs", bar)
        self.fk_limbs_button.setStyleSheet(_BUTTON_STYLE)
        self.fk_limbs_button.setToolTip(
            "Bring the selected arms/legs to FK - a controller, a bone, or\n"
            "a picker button names the limb. IK converts (animation\n"
            "re-baked), a bare chain builds FK, FK stays and says so.")
        self.fk_limbs_button.clicked.connect(
            lambda _checked=False: self.convert_selected_limbs(to_ik=False))
        row.addWidget(self.fk_limbs_button)

        self.ik_limbs_button = QtWidgets.QPushButton("IK Limbs", bar)
        self.ik_limbs_button.setStyleSheet(_BUTTON_STYLE)
        self.ik_limbs_button.setToolTip(
            "Bring the selected arms/legs to IK - a controller, a bone, or\n"
            "a picker button names the limb. FK converts (animation\n"
            "re-baked), a bare chain builds its IK, IK stays and says so.")
        self.ik_limbs_button.clicked.connect(
            lambda _checked=False: self.convert_selected_limbs(to_ik=True))
        row.addWidget(self.ik_limbs_button)

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
        active.clear()
        self._refresh_view()
        if len(roots) > 1:
            self.status.showMessage(
                "{0} skeletons in the scene - select one and press "
                "Connect".format(len(roots)))
        else:
            self.status.showMessage(_UNBOUND_MESSAGE)

    def _bind(self, root):
        self._root_uuid = naming.uuid_of(root)

        # Connect IS the choice of active character (the user's own
        # description: press Connect on a hierarchy and that hierarchy is
        # what we work with). Claiming happens here too, so a scene rigged
        # before manifests carried a character tag is migrated the moment
        # it is connected -- which is before a second character can exist.
        active.set_root(root)
        manifest.claim_untagged()

        # Rigs often arrive with every joint prefixed. The prefix is worked out
        # once for the whole skeleton, so the body map's plain UE5 names line up
        # without each button having to guess.
        raw = naming.hierarchy_map(root)
        self._prefix = naming.detect_prefix(raw, self._fk_joints)
        self._scene_map = naming.strip_prefix(raw, self._prefix)

        self._refresh_view()

        matched = sum(1 for j in self._fk_joints if j in self._scene_map)
        message = "Connected to {0} - {1}/{2} buttons matched".format(
            root.split("|")[-1], matched, len(bodymap.BUTTONS))
        if self._prefix:
            message += "  (prefix '{0}')".format(self._prefix)
        self.status.showMessage(message)

    def bound_root(self):
        """Current root's DAG path, re-resolved from its UUID, or None."""
        return naming.path_from_uuid(self._root_uuid)

    # -- view state ----------------------------------------------------------

    def _resolution(self):
        """Button id -> the node it selects, for everything that exists now.

        BOTH halves go through the bound character's own manifests, never
        by bare name (2026-09-01). FK controllers used to be trusted as
        our own renames -- true until a second character in the scene
        makes Maya's second `upperarm_l_FK_ctrl` into `..._FK_ctrl1`, at
        which point every button on character two lit up character one's
        rig. Unbound resolves nothing: an unconnected picker is inert by
        design.

        One manifest snapshot for the whole sync: the scan is a scene-wide
        `ls` and this runs on every selection change.

        The one exception to "controllers, never bones": the finger buttons
        fall back to the finger BONE, because finger FK controllers are no
        longer built and the animator poses those bones. A controller still
        wins where one exists, so a file rigged before that change is
        unaffected.
        """
        if not self._scene_map:
            return {}

        # The window is the UI's definition of the active character, so it
        # re-asserts it here rather than trusting whatever ran last: a
        # verify script or a second panel can have adopted a different
        # character since, and the buttons must keep showing THIS binding.
        active.set_root(self.bound_root())

        table = manifest.records()
        controls = fkcontrols.fk_control_paths(self._scene_map, table=table)
        fk_nodes = {joint: controls.get(joint)
                    for joint in self._scene_map if joint in self._fk_joints}

        ik_nodes = {}
        for button in bodymap.IK_BUTTONS:
            ik_nodes[(button.limb, button.role)] = builder.ik_control(
                button.limb, button.role, table=table)

        # Existence is re-checked rather than trusted: the binding is a
        # snapshot, and the animator keeps working in the scene while the
        # panel is open.
        bone_nodes = {}
        for joint in fkcontrols.FINGER_JOINTS:
            path = self._scene_map.get(joint)
            if path and cmds.objExists(path):
                bone_nodes[joint] = path

        return pickerstate.resolve(fk_nodes, ik_nodes, bone_nodes)

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
        """Translate a picker request into a Maya selection.

        A button acts only when it resolves to something, which is also what
        the availability dimming shows: its controller, or -- for the fingers
        alone -- its bone.
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
        """Build the hybrid rig, replacing any previous build of either kind.

        Always hybrid from the window since 2026-08-21 -- IK arms and legs,
        FK everything else; any limb goes FK afterwards through FK Limbs.
        The full-FK build stays reachable as `rebuild(fk_limbs=True)`. The
        teardown of whatever exists happens inside `rebuild`, so mixed
        states are fine.
        """
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        self._run("Build", self.build_button, lambda: fkcontrols.rebuild(
            self._scene_map, fk_limbs=False))

    def _selected_limbs(self):
        """The switchable limbs the selection touches.

        One innermost-owner resolution for both manifest kinds -- an arm
        controller nested inside the torso's controllers must NOT drag
        those in -- plus bones (a clavicle still names its arm), so a
        viewport bone click works with no rig standing at all.
        """
        selected = cmds.ls(selection=True, long=True) or []
        ik_limbs, fk_chains = fkcontrols.bake_targets(self._scene_map)
        bone_owner = fkcontrols.switchable_bones(self._scene_map)
        bone_hits = {bone_owner[p] for p in selected if p in bone_owner}
        hit = set(ik_limbs) | set(fk_chains) | bone_hits
        return [l for l in fkcontrols.SWITCHABLE if l in hit]

    def convert_selected_limbs(self, to_ik):
        """Bring the selected arms/legs to FK or IK; ones already there stay."""
        if not self._scene_map:
            self.status.showMessage(_UNBOUND_MESSAGE)
            return

        limbs = self._selected_limbs()
        if not limbs:
            self.status.showMessage(
                "Select an arm or leg - a controller, a bone, or its "
                "picker button")
            return

        label = "IK Limbs" if to_ik else "FK Limbs"
        button = self.ik_limbs_button if to_ik else self.fk_limbs_button
        self._run(label, button, lambda: fkcontrols.convert_limbs(
            self._scene_map, limbs, to_ik)[2])

    def bake_selected_limbs(self):
        """Bake ONLY what the selection touches back to clean bones.

        Everything else in the scene keeps its rig. IK limbs take their
        riding finger chains down with them; FK chains bake per chain,
        expanding to whatever rides inside them; a weapon aim bakes onto its
        sword and goes.
        """
        aims = aimrig.aim_targets()

        # An aim needs no scene_map -- the sword is not part of the body map --
        # so a selected aim is bakeable with no skeleton bound.
        if not self._scene_map:
            if not aims:
                self.status.showMessage(_UNBOUND_MESSAGE)
                return
            self._run("Bake+Delete", self.bake_button,
                      lambda: aimrig.bake_aims(aims))
            return

        ik_limbs, fk_chains = fkcontrols.bake_targets(self._scene_map)
        if not ik_limbs and not fk_chains and not aims:
            self.status.showMessage(
                "Select a rigged element - a controller, a bone, a picker "
                "button, or a weapon with an aim")
            return

        def run():
            messages = []
            # The aim first: it is the smaller teardown, and neither order
            # matters to the other -- the aim drives the sword, not the arm.
            if aims:
                messages.append(aimrig.bake_aims(aims))
            if ik_limbs or fk_chains:
                messages.append(fkcontrols.bake_selection(
                    self._scene_map, ik_limbs, fk_chains))
            return " | ".join(messages)

        self._run("Bake+Delete", self.bake_button, run)

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


def _open_window():
    """The live picker window, or None."""
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            return widget
    return None


def bound_root():
    """The open picker's bound skeleton root, or None.

    Companion tools ask this so they act on the character the animator is
    already driving. The binding lives in the live window and is not persisted
    anywhere, so there is nothing else to read it out of.
    """
    window = _open_window()
    return window.bound_root() if window else None


def connect_root(root):
    """Bind the open picker to `root`. True when a picker took it.

    What lets Add Character hand over the character it just imported, so
    "add it" and "work on it" are one press. With no picker open the active
    character is still set -- a Scene Setup press acts on it either way --
    and the next Connect decides.
    """
    if not root:
        return False
    window = _open_window()
    if window is None:
        active.set_root(root)
        manifest.claim_untagged()
        return False
    window._bind(root)
    return True


def show_picker():
    """Open the picker, replacing any window left from a previous call."""
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            widget.close()
            widget.deleteLater()

    window = PickerWindow()
    window.show()
    return window

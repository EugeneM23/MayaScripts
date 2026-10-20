"""The scene half of the skill bar's status-line tools (2026-10-20): reads Maya's own status-line
controls and runs the commands they run. Every call answers something whatever Maya says: a
broken read is the state Maya starts with, a broken press is printed to the Script Editor.
Spec: docs/superpowers/specs/2026-10-20-skill-bar-status-tools-design.md
"""

import traceback

from . import status


def _mel():
    import maya.mel as mel
    return mel


def _cmds():
    import maya.cmds as cmds
    return cmds


def mode():
    cmds = _cmds()
    try:
        if cmds.selectMode(q=True, component=True):
            return status.COMPONENT
        if cmds.selectMode(q=True, hierarchical=True):
            return status.HIERARCHY
    except Exception:                                        # noqa: BLE001
        pass
    return status.OBJECT


def _control_state(control):
    """A status-line iconTextCheckBox read, or None when there is no status line."""
    cmds = _cmds()
    if not cmds.iconTextCheckBox(control, exists=True):
        return None
    return status.mask_state(cmds.iconTextCheckBox(control, q=True, value=True),
                             cmds.iconTextCheckBox(control, q=True, image1=True))


def _flags(flags):
    cmds = _cmds()
    values = []
    for flag in flags:
        try:
            values.append(cmds.selectType(q=True, **{flag: True}))
        except Exception:                                    # noqa: BLE001
            pass                                             # a flag this Maya does not have
    return status.flags_state(values)


def _hier(key):
    try:
        return "on" if _cmds().selectMode(q=True, **{key: True}) else ""
    except Exception:                                        # noqa: BLE001
        return ""


class MayaStatus(object):
    """The model the tools read in Maya."""

    def read(self):
        st = status.blank_state(mode())
        cmds = _cmds()
        try:
            for key, _label, _icon, control, _command, _popup, flags in status.masks(st["mode"]):
                if st["mode"] == status.HIERARCHY:
                    st["masks"][key] = _hier(key)
                    continue
                got = _control_state(control)
                st["masks"][key] = got if got is not None else _flags(flags)
            st["lock"] = bool(cmds.selectPref(q=True, xformNoSelect=True))
            st["hilite"] = bool(cmds.selectPref(q=True, allowHiliteSelection=True))
            for key, _label, _icon, flag in status.SNAPS:
                st["snaps"][key] = bool(cmds.snapMode(q=True, **{flag: True}))
            st["live"] = bool(cmds.makeLive(q=True))
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        return st

    def press(self, group, key):
        """What the status-line button runs, with its new value."""
        cmds, mel = _cmds(), _mel()
        st = self.read()
        try:
            if group == "mask":
                for k, _label, _icon, _control, command, _popup, _flags in status.masks(st["mode"]):
                    if k == key:
                        if st["mode"] == status.HIERARCHY:
                            mel.eval(command)
                        else:
                            mel.eval(status.pressed(command, st["masks"].get(key)))
            elif group == "select" and key == "lock":
                cmds.selectPref(xformNoSelect=not st["lock"])
                _sync_maya("lockSelectionIcon", not st["lock"])
            elif group == "select":
                cmds.selectPref(allowHiliteSelection=not st["hilite"])
                if mel.eval('exists "updateHighlightSelectIcon"'):
                    _try(mel.eval, "updateHighlightSelectIcon")
            elif group == "snap":
                flag = dict((k, f) for k, _l, _i, f in status.SNAPS)[key]
                cmds.snapMode(**{flag: not st["snaps"][key]})
            else:
                mel.eval("statusLineSetMakeLive")
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        return self.read()

    def menu(self, group, key):
        """The right button's rows [(label, checked, command)]: a mask's own types (Maya's
        createMaskPopup, read back off its popup), Make Live's add / remove."""
        if group == "live":
            return [("Add selection to live", False, "statusLineAddSelToLive"),
                    ("Remove selection from live", False, "statusLineRemoveSelFromLive"),
                    ("Toggle live", False, "statusLineToggleLive")]
        if group != "mask":
            return []
        st_mode = mode()
        popup = None
        for k, _label, _icon, _control, _command, group_name, _flags in status.masks(st_mode):
            if k == key:
                popup = group_name
        if not popup:
            return []
        cmds, mel = _cmds(), _mel()
        menu = popup + "Popup"
        try:
            if not cmds.popupMenu(menu, exists=True):
                return []
            mel.eval('createMaskPopup "%s"' % popup)
            items = cmds.popupMenu(menu, q=True, itemArray=True) or []
            labels, checks, commands = [], [], []
            for item in items:
                path = menu + "|" + item
                if cmds.menuItem(path, q=True, divider=True):
                    continue
                labels.append(cmds.menuItem(path, q=True, label=True))
                checks.append(cmds.menuItem(path, q=True, checkBox=True)
                              if cmds.menuItem(path, q=True, isCheckBox=True) else False)
                commands.append(cmds.menuItem(path, q=True, command=True))
            return status.menu_rows(labels, checks, commands)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            return []

    def run(self, command, checked=None):
        """A menu row's command, `#1` the row's new value."""
        if not command:
            return
        try:
            if callable(command):
                command(not checked if checked is not None else True)
                return
            text = command.replace("#1", "0" if checked else "1")
            _mel().eval(text)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()


def _sync_maya(control, value):
    """Keep Maya's own (hidden or shown) status-line button in step with a press of ours."""
    cmds = _cmds()
    try:
        if cmds.iconTextCheckBox(control, exists=True):
            cmds.iconTextCheckBox(control, e=True, value=bool(value))
    except Exception:                                        # noqa: BLE001
        pass


def _try(fn, *args):
    try:
        return fn(*args)
    except Exception:                                        # noqa: BLE001
        return None

"""Time Bar: Maya's time slider redrawn as one bar in the hub's look (2026-10-16).

A workspaceControl `skeldarTimeBar` docked where Maya's Time Slider is, Maya's
Time Slider and Range Slider hidden while it shows (optionVar skeldarTimeBar, on
by default; the hub's ⋮ -> Time bar, the hotkey row window.timebar). Nothing
heavy at import: `active()` and `highlight()` are asked by every bake.
Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""

import os
import sys

CONTROL = "skeldarTimeBar"
LABEL = "Time Bar"
OPTIONVAR = "skeldarTimeBar"
MAYA_CONTROLS = ("TimeSlider", "RangeSlider")
HEIGHT = 106                # logical px: the page row (the skill bar, 2026-10-19), the range row, the time row


def _state():
    state = getattr(sys, "_skeldar_timebar", None)
    if state is None:
        state = {"bar": None, "jobs": [], "callbacks": []}
        sys._skeldar_timebar = state
    return state


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


def uiscript(root):
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n_p = \"{0}\"\nif _p not in sys.path:\n    sys.path.insert(0, _p)\n"
            "import maya_timebar.bar\nmaya_timebar.bar.build()\n").format(root)


MODE_VAR = "skeldarTimeBarMode"          # maya | docked | edge (2026-10-16)
LAST_VAR = "skeldarTimeBarLastMode"      # the last of docked / edge, for the switch back
DEFAULTS_VAR = "skeldarTimeBarDefaults"  # the DEFAULT_VERSION this Maya has had


def mode():
    """Maya's, Docked or Bottom edge - an older build's on/off optionVar read
    when there is no mode yet."""
    import maya.cmds as cmds
    from . import look
    value = cmds.optionVar(q=MODE_VAR) if cmds.optionVar(exists=MODE_VAR) else None
    old = cmds.optionVar(q=OPTIONVAR) if cmds.optionVar(exists=OPTIONVAR) else None
    return look.mode_from(value, old)


def wanted():
    """Ours (docked or at the bottom edge) rather than Maya's slider."""
    return mode() != "maya"


def active():
    """The time bar stands and Maya's slider is hidden by it: the highlight is ours.
    Cheap, and False wherever there is no UI."""
    if _state().get("bar") is None:
        return False
    try:
        import maya.cmds as cmds
        if cmds.about(batch=True):
            return False
        edge = _state().get("edge")
        if edge is not None and edge.alive():
            return True
        return bool(cmds.workspaceControl(CONTROL, exists=True)
                    and cmds.workspaceControl(CONTROL, q=True, visible=True))
    except Exception:                                        # noqa: BLE001
        return False


def highlight():
    """The highlight as `timeControl -q -rangeArray` answers it - (first, last + 1) -
    or None (nothing, or one frame)."""
    from . import look, scene
    return look.range_array(scene.read_highlight())


def ensure_docked():
    """The bar made (or restored) beside Maya's Time Slider, and Maya's two hidden."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return ""
    drop_edge()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
        for flags in ({"actLikeMayaUIElement": True}, {"resizeHeight": HEIGHT}):
            try:                    # a control the first build made: no tab, two rows tall
                cmds.workspaceControl(CONTROL, edit=True, **flags)
            except Exception:                                # noqa: BLE001
                pass
        from . import bar
        if bar.current() is None or _state().get("host") != "docked":
            bar.build()
    else:
        #  actLikeMayaUIElement: no tab, no title - it sits as Maya's own slider does
        options = dict(label=LABEL, retain=False, floating=False, heightProperty="fixed",
                       initialHeight=HEIGHT, actLikeMayaUIElement=True,
                       uiScript=uiscript(plugin_root()))
        if cmds.workspaceControl("TimeSlider", exists=True):
            options["dockToControl"] = ("TimeSlider", "top")
        else:
            options["dockToMainWindow"] = ("bottom", False)
        cmds.workspaceControl(CONTROL, **options)
    maya_slider(False)
    return CONTROL


def _hide_control():
    import maya.cmds as cmds
    try:
        if cmds.workspaceControl(CONTROL, exists=True):
            cmds.workspaceControl(CONTROL, edit=True, visible=False)
    except Exception:                                        # noqa: BLE001
        pass


def ensure_edge():
    """The bar at the bottom edge of Maya's window: the docked one hidden, Maya's
    two hidden, the bar out of sight until the cursor reaches the edge."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return None
    edge = _state().get("edge")
    if edge is not None and edge.alive():
        maya_slider(False)
        return edge
    _hide_control()
    from . import bar, edge as edge_module
    edge_module.destroy_all()
    try:
        from . import layerpanel
        layerpanel.destroy_all()
    except Exception:                                        # noqa: BLE001
        pass
    ui = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0
    controller = edge_module.BottomEdge(lambda parent: bar.make(bar.Link(), ui, parent=parent))
    _state()["edge"] = controller
    _state()["bar"] = controller.strip
    _state()["host"] = "edge"
    bar.start_jobs()
    maya_slider(False)
    return controller


def drop_edge():
    edge = _state().pop("edge", None)
    try:
        from . import layerpanel
        layerpanel.destroy_all()
    except Exception:                                        # noqa: BLE001
        pass
    if edge is not None:
        try:
            edge.destroy()
        except Exception:                                    # noqa: BLE001
            pass
        if _state().get("host") == "edge":
            _state()["bar"] = None
            _state()["host"] = None


def maya_slider(show):
    """Maya's Time Slider and Range Slider shown or hidden."""
    import maya.cmds as cmds
    for name in MAYA_CONTROLS:
        try:
            if cmds.workspaceControl(name, exists=True):
                cmds.workspaceControl(name, edit=True, visible=bool(show))
        except Exception:                                    # noqa: BLE001 - a layout without it
            pass


MESSAGES = {
    "maya": "Maya's time slider is back - ⋮ -> Time bar brings ours again",
    "docked": "Time bar docked in place of Maya's time slider",
    "edge": "Time bar at the bottom edge - move the mouse to the bottom of Maya's window",
}


def set_mode(choice):
    """Maya's, Docked or Bottom edge, remembered; returns what to say."""
    import maya.cmds as cmds
    from . import look
    choice = choice if choice in look.MODES else "docked"
    cmds.optionVar(stringValue=(MODE_VAR, choice))
    cmds.optionVar(intValue=(OPTIONVAR, 0 if choice == "maya" else 1))
    if choice != "maya":
        cmds.optionVar(stringValue=(LAST_VAR, choice))
    if choice == "maya":
        drop_edge()
        _hide_control()
        maya_slider(True)
    elif choice == "docked":
        ensure_docked()
    else:
        ensure_edge()
    return MESSAGES[choice]


def upgrade():
    """Once per look.DEFAULT_VERSION: the bottom edge, unless Maya's was chosen."""
    import maya.cmds as cmds
    from . import look
    seen = cmds.optionVar(q=DEFAULTS_VAR) if cmds.optionVar(exists=DEFAULTS_VAR) else 0
    if seen >= look.DEFAULT_VERSION:
        return mode()
    choice = look.upgraded(mode(), seen)
    cmds.optionVar(stringValue=(MODE_VAR, choice))
    cmds.optionVar(intValue=(DEFAULTS_VAR, look.DEFAULT_VERSION))
    return choice


def ensure():
    """The mode the animator chose, standing (the hub's build calls it); an
    update's new default taken once first."""
    choice = upgrade()
    if choice == "edge":
        return ensure_edge()
    if choice == "docked":
        return ensure_docked()
    return None


def _stop_jobs():
    """The strip's scriptJobs and callbacks killed (they may be an older
    module's)."""
    import maya.cmds as cmds
    for job in _state().get("jobs", []):
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    _state()["jobs"] = []
    try:
        import maya.api.OpenMaya as om
        for cid in _state().get("callbacks", []):
            try:
                om.MMessage.removeCallback(cid)
            except Exception:                                # noqa: BLE001
                pass
    except Exception:                                        # noqa: BLE001
        pass
    _state()["callbacks"] = []


def reload_live():
    """After an install (2026-10-19): the bar an OLDER module built - at the bottom
    edge or docked - dropped and built again from this one, in the mode chosen.
    The state lives on `sys`, so this module can take down what the old one made.
    True when ours stands again."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return False
    drop_edge()
    _state()["bar"] = None              # a docked strip of the old classes: build again
    _state()["host"] = None
    _stop_jobs()
    return ensure() is not None


def show():
    import maya.cmds as cmds
    last = cmds.optionVar(q=LAST_VAR) if cmds.optionVar(exists=LAST_VAR) else "docked"
    return set_mode(last if last in ("docked", "edge") else "docked")


def hide():
    """Maya's own slider back, ours hidden."""
    return set_mode("maya")


def set_on(on):
    """A choice ('maya' / 'docked' / 'edge') or, from an older caller, on / off."""
    if isinstance(on, str):
        return set_mode(on)
    return show() if on else hide()


def toggle():
    return hide() if wanted() and active() else show()


def steel():
    """⋮ -> Time bar ▸ Steel keys: the keys in steel, a key set glowing hot and cooling."""
    from . import bar
    return bar.steel_on()


def set_steel(on):
    """Steel keys on or off (2026-10-20, «эффект остывания стали»): remembered, and every
    standing strip repainted at once."""
    import maya.cmds as cmds
    from . import bar, look
    cmds.optionVar(intValue=(look.STEEL_VAR, 1 if on else 0))
    try:
        from PySide6 import QtWidgets
        for w in QtWidgets.QApplication.allWidgets():
            if w.objectName() == bar.ROOT_NAME and hasattr(w, "set_steel"):
                w.set_steel(on)
    except Exception:                                        # noqa: BLE001
        import traceback
        print(traceback.format_exc())
    return "Steel keys: a key set glows hot and cools into steel" if on else "Keys in the accent orange"

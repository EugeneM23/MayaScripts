"""A character's own camera puts the character in 1P (2026-10-22).

The animator: «Давай добавим настройку в наши сеттингсы и эта настройка будет не
активна по умолчанию. Суть: когда я переключаюсь на камеру нашего персонажа то он
автоматически переключает свой режим в 1p, когда я выхожу из камеры персонажа он
включает 3P (если конечно эта опция доступна)».

⋮ -> 1P in its camera (optionVar `skeldarCamView1P`, OFF by default). While it is
on, a 250 ms watch reads the cameras the viewports look through (a camera flight's
TARGET in place of its substitute, so the switch comes as the flight starts):

- a viewport on a Camera Setup camera (`maya_scenesetup.camera.MARKER`) of a rig
  whose Main carries `view` (Manny, Orc D, Playerchar - not the Creep) and stands
  in 3P puts that rig in 1P, and remembers it did;
- once no viewport shows that camera, the rig goes back to 3P - only a rig the
  watch itself put in 1P: one the animator put there by hand stays as it is.

`Main.view` is a view, not animation (not keyable): it is written with the undo
queue off, and a clean scene is left clean.

    enabled() / set_enabled(on)   the switch
    ensure()                      at the hub's build
    plan(shown, values, ours)     what to switch (pure)
"""

import contextlib
import sys
import traceback

OPTIONVAR = "skeldarCamView1P"
DEFAULT = False
STATE = "_skeldar_camview"              # on sys (trap 111)
WATCH_MS = 250
VIEW = "view"                           # Main's enum 3P:1P
FIRST, THIRD = 1, 0


def plan(shown, values, ours):
    """What the watch switches. Pure.

    `shown`: the Main plugs whose camera a viewport shows; `values`: each known
    plug's view now (None when it cannot be written); `ours`: the plugs the watch
    put in 1P. Answers (to_first, to_third, ours after)."""
    shown = set(shown)
    to_first, to_third, kept = [], [], set()
    for plug in sorted(shown):
        value = values.get(plug)
        if value is None:
            continue
        if plug in ours:
            kept.add(plug)
        elif value == THIRD:
            to_first.append(plug)
            kept.add(plug)
    for plug in sorted(set(ours) - shown):
        if values.get(plug) == FIRST:
            to_third.append(plug)
    return to_first, to_third, kept


# ------------------------------------------------------------------ the scene

def _cmds():
    import maya.cmds as cmds
    return cmds


def enabled():
    cmds = _cmds()
    if not cmds.optionVar(exists=OPTIONVAR):
        return DEFAULT
    return bool(cmds.optionVar(query=OPTIONVAR))


def _state():
    st = getattr(sys, STATE, None)
    if st is None:
        st = {"timer": None, "ours": set(), "owners": {}}
        setattr(sys, STATE, st)
    return st


def _panels():
    cmds = _cmds()
    panels = []
    try:
        visible = cmds.getPanel(visiblePanels=True) or []
    except Exception:                                        # noqa: BLE001
        visible = []
    for panel in visible:
        try:
            if cmds.getPanel(typeOf=panel) == "modelPanel":
                panels.append(panel)
        except Exception:                                    # noqa: BLE001
            pass
    if not panels:                                           # trap 88
        panels = cmds.getPanel(type="modelPanel") or []
    return panels


def _shown_camera(panel):
    """The camera transform `panel` looks through, its flight's target first."""
    cmds = _cmds()
    try:
        import maya_camflight
        target = maya_camflight.target_of(panel)
    except Exception:                                        # noqa: BLE001
        target = None
    if target:
        return target
    try:
        cam = cmds.modelPanel(panel, query=True, camera=True) or ""
    except Exception:                                        # noqa: BLE001
        return ""
    if cam and cmds.objExists(cam) and cmds.objectType(cam, isAType="camera"):
        cam = (cmds.listRelatives(cam, parent=True, fullPath=True) or [cam])[0]
    found = cmds.ls(cam, long=True) or [] if cam else []
    return found[0] if found else ""


def owner_plug(camera):
    """The `Main.view` plug of the rig whose Camera Setup camera this is, else ""."""
    cmds = _cmds()
    if not camera or not cmds.objExists(camera):
        return ""
    from maya_scenesetup import camera as setup
    if not cmds.attributeQuery(setup.MARKER, node=camera, exists=True):
        return ""
    import maya_rigs
    rig = maya_rigs.rig_of(camera, maya_rigs.rigs())
    if rig is None or not rig.main:
        return ""
    if not cmds.attributeQuery(VIEW, node=rig.main, exists=True):
        return ""
    return rig.main + "." + VIEW


def _value(plug):
    """The plug's view, or None when it is gone, locked or driven."""
    cmds = _cmds()
    try:
        if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
            return None
        return int(cmds.getAttr(plug))
    except Exception:                                        # noqa: BLE001
        return None


@contextlib.contextmanager
def _quiet():
    """No undo step, and a clean scene left clean."""
    cmds = _cmds()
    was = bool(cmds.undoInfo(query=True, state=True))
    clean = not cmds.file(query=True, modified=True)
    if was:
        cmds.undoInfo(stateWithoutFlush=False)
    try:
        yield
    finally:
        if was:
            cmds.undoInfo(stateWithoutFlush=True)
        if clean:
            cmds.file(modified=False)


def tick():
    """One look at the viewports; what was switched, as (to_first, to_third)."""
    st = _state()
    owners = st["owners"]
    shown = set()
    for panel in _panels():
        camera = _shown_camera(panel)
        if not camera:
            continue
        if camera not in owners:
            owners[camera] = owner_plug(camera)
        if owners[camera]:
            shown.add(owners[camera])
    values = {plug: _value(plug) for plug in shown | set(st["ours"])}
    to_first, to_third, kept = plan(shown, values, st["ours"])
    if to_first or to_third:
        cmds = _cmds()
        with _quiet():
            for plug in to_first:
                cmds.setAttr(plug, FIRST)
            for plug in to_third:
                cmds.setAttr(plug, THIRD)
    st["ours"] = kept
    if len(owners) > 64:
        owners.clear()
    return to_first, to_third


def _slot(*_args):
    try:
        import maya_camview
        maya_camview.tick()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


def watch():
    st = _state()
    if st["timer"] is None:
        import maya_hubqt
        q = maya_hubqt.qt()
        timer = q.QtCore.QTimer()
        timer.setInterval(WATCH_MS)
        timer.timeout.connect(_slot)
        st["timer"] = timer
    st["owners"].clear()
    if not st["timer"].isActive():
        st["timer"].start()


def unwatch(restore=True):
    """The watch stopped; the rigs it put in 1P back in 3P."""
    st = _state()
    if st["timer"] is not None:
        try:
            st["timer"].stop()
        except Exception:                                    # noqa: BLE001
            pass
        st["timer"] = None
    if restore and st["ours"]:
        cmds = _cmds()
        with _quiet():
            for plug in sorted(st["ours"]):
                if _value(plug) == FIRST:
                    cmds.setAttr(plug, THIRD)
    st["ours"] = set()
    st["owners"].clear()


def ensure():
    """At the hub's build: watched while the switch is on."""
    cmds = _cmds()
    if cmds.about(batch=True):
        return False
    if not enabled():
        unwatch()
        return False
    watch()
    _slot()
    return True


def set_enabled(on):
    """⋮ -> 1P in its camera."""
    on = bool(on)
    cmds = _cmds()
    cmds.optionVar(intValue=(OPTIONVAR, int(on)))
    if cmds.about(batch=True):
        return "1P in its camera %s" % ("on" if on else "off")
    if on:
        watch()
        _slot()
        return "1P in its camera: a character's own camera puts it in 1P"
    unwatch()
    return "1P in its camera off"


def reload_live():
    """After an install: the old module's timer stopped, watched by this one."""
    st = _state()
    if st["timer"] is not None:
        try:
            st["timer"].stop()
        except Exception:                                    # noqa: BLE001
            pass
        st["timer"] = None
    return ensure()

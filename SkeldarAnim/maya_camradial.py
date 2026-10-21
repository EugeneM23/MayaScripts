"""maya_camradial - Space: our radial menu in place of Maya's hotbox, cameras only (2026-10-20).

The animator: «В мае при нажатии на пробел вылазит круговое меню. Давай его заменим на такое же
как у нас с красивыми анимациями. Пока в этом меню давай сделаем только переключения между
камерами». Of three mockups they chose B: one ring of eight - Top north, Side east, Front south,
Persp west, the scene's own cameras on the diagonals (Camera Setup's first), an empty diagonal a
dot; every pill shows the world axes as that camera sees them, the camera the panel looks through
is marked.

- Hold Space: the menu under the cursor (`maya_radial.press("cameras")`); let go on a pill: the
  viewport the cursor was over looks through that camera. A quick tap in the centre is Maya's own
  tap: single / four views (`panePopAt`'s rule). Esc or the right button close it.
- The menu is `maya_radial.Menu` with these items - its motion, look and keys are the radial
  menu's. Only the scene half lives here.
- Bound on Space in the SkeldarAnim hotkey set only (`maya_hotkeys.DEFAULT_KEYS`); Maya's own sets
  keep the hotbox.
- Since 2026-10-21 the switch FLIES (`maya_camflight`): a substitute camera goes 0.3 s from the
  panel's view to the chosen one, orbiting what is looked at and flattening into an ortho view;
  instant with Interface animations off. The substitute is left out of the menu, and the camera a
  flight goes to is the one marked.
"""

import sys
import traceback

import maya.cmds as cmds

import maya_camflight_rules as flight_rules
import maya_radial_rules as rules

STARTUP = ("persp", "top", "front", "side")
SETUP_MARKER = "mayaSceneSetupCamera"      # maya_scenesetup.camera.MARKER


def _state():
    st = getattr(sys, "_skeldar_camradial", None)
    if st is None:
        st = {"panel": ""}
        sys._skeldar_camradial = st
    return st


def _scoped(paths):
    try:
        import maya_scenetabs.scope as scope
        return scope.active_only(paths)
    except Exception:                                        # noqa: BLE001
        return paths


def _local(path):
    try:
        import maya_scenetabs.scope as scope
        return scope.local(path)
    except Exception:                                        # noqa: BLE001
        return path


def _leaf(path):
    return path.rsplit("|", 1)[-1].rsplit(":", 1)[-1]


def cameras():
    """({startup name: transform path}, [scene camera transform paths in the menu's order])."""
    views, scene, marked = {}, [], []
    shapes = cmds.ls(type="camera", long=True) or []
    for shape in shapes:
        parent = (cmds.listRelatives(shape, parent=True, fullPath=True) or [None])[0]
        if not parent:
            continue
        if cmds.objExists(parent + "." + flight_rules.MARKER):
            continue                                          # a flight's substitute
        try:
            startup = bool(cmds.camera(parent, query=True, startupCamera=True))
        except Exception:                                    # noqa: BLE001
            startup = False
        if startup:
            name = _leaf(parent)
            if name in STARTUP and name not in views:
                views[name] = parent
            continue
        if parent in scene:
            continue
        scene.append(parent)
        try:
            if cmds.attributeQuery(SETUP_MARKER, node=parent, exists=True):
                marked.append(parent)
        except Exception:                                    # noqa: BLE001
            pass
    scene = rules.scene_order(_scoped(scene), marked)
    return views, scene


def panel_under_cursor():
    """The model panel under the mouse, else the one with focus, else ""."""
    for flags in ({"underPointer": True}, {"withFocus": True}):
        try:
            panel = cmds.getPanel(**flags) or ""
        except Exception:                                    # noqa: BLE001
            panel = ""
        if panel and cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    return ""


def current_camera(panel):
    if not panel:
        return ""
    try:
        cam = cmds.modelPanel(panel, query=True, camera=True) or ""
    except Exception:                                        # noqa: BLE001
        return ""
    if cam and cmds.objectType(cam, isAType="camera"):
        cam = (cmds.listRelatives(cam, parent=True, fullPath=True) or [cam])[0]
    found = cmds.ls(cam, long=True) or []
    return found[0] if found else cam


def label(path):
    name = _leaf(path)
    try:
        startup = bool(cmds.camera(path, query=True, startupCamera=True))
    except Exception:                                        # noqa: BLE001
        startup = False
    if startup and name in rules.VIEW_LABELS:
        return rules.VIEW_LABELS[name]
    return _local(path).rsplit("|", 1)[-1]


def axes(path):
    try:
        return rules.axes_seen(cmds.xform(path, query=True, worldSpace=True, matrix=True))
    except Exception:                                        # noqa: BLE001
        return {}


def spec():
    """What the menu shows, read when Space goes down: items, texts, the marked slot, the axes."""
    panel = panel_under_cursor()
    _state()["panel"] = panel
    views, scene = cameras()
    items = rules.camera_slots(views, scene)
    current = _flying_to(panel) or current_camera(panel)
    texts, seen, marked = [], [], set()
    for i, item in enumerate(items):
        kind, path = rules.parse(item)
        if kind != "camera":
            texts.append("")
            seen.append({})
            continue
        texts.append(label(path))
        seen.append(axes(path))
        if current and path == current:
            marked.add(i)
    return {"items": items, "texts": texts, "axes": seen, "marked": marked,
            "on_tap": tap, "release": rules.camera_release, "centre": "camera"}


def look_through(path):
    """The panel the menu was opened over looks through `path`."""
    panel = _state()["panel"] or panel_under_cursor()
    if not panel:
        return _say("Space: no viewport under the cursor")
    if not cmds.objExists(path):
        return _say("Space: {0} is gone".format(_leaf(path)))
    try:
        if not _fly(panel, path):
            cmds.lookThru(panel, path)
    except Exception as error:                               # noqa: BLE001
        traceback.print_exc()
        return _say("Space: {0}".format(error))
    return label(path)


def _fly(panel, path):
    """True when a flight took the switch over (maya_camflight); False: switch at once."""
    try:
        import maya_camflight
        return bool(maya_camflight.fly(panel, path))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def _flying_to(panel):
    try:
        import maya_camflight
        return maya_camflight.target_of(panel) or ""
    except Exception:                                        # noqa: BLE001
        return ""


def tap():
    """A quick tap of Space: single / four views, as Maya's hotbox does (panePopAt)."""
    panel = _state()["panel"]
    if not panel:
        return ""
    try:
        import maya.mel as mel
        mel.eval('global string $gMainPane;'
                 'if (`paneLayout -q -configuration $gMainPane` == "single")'
                 ' doSwitchPanes(1, { "@goBack", "" });'
                 ' else doSwitchPanes(1, { "single", "%s" });'
                 ' updateToolbox();' % panel)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    return ""


def _say(message):
    try:
        cmds.inViewMessage(assistMessage=message, position="midCenterTop", fade=True)
    except Exception:                                        # noqa: BLE001
        pass
    return message

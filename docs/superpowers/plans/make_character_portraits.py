"""Render the Characters grid's portraits from the characters themselves (2026-09-30).

Run INSIDE a GUI Maya - Viewport 2.0 needs a viewport, so not mayapy - and never
the animator's (it opens new scenes): a disposable Maya with its own MAYA_APP_DIR
and MAYA_NO_HOME=1, the file exec'd over its commandPort.

For each model of maya_scenesetup.catalog.MODELS: a fresh scene, the model's rig
row (else its skeleton row) added through character.add_character, only polygons
shown, a light clay phong on everything but a textured row (the Orc D keeps
Unreal's textures - a portrait never shows a palette colour the character will not
arrive in), three directional lights, AO and multisample AA, and a perspective
camera at 85 mm framed head and shoulders from the skeleton - the two upper arms
give the span, the meshes' top the crown - turned a little toward the
character's left and a little above the eyes. One frame playblast at RENDER px
with the background transparent, scaled to catalog's 256 px with smooth
filtering, written to SkeldarAnim/assets/character_portraits/<model>.png (RGBA).
The Auto card (2026-10-02) has no character to render: its «?» is drawn by
make_auto_portrait.py, and both calls below leave it out.

    render_all()             every model into the plugin's assets
    render("Manny", out)     one model into `out`
"""

import math
import os
import sys
import time

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
for _name in list(sys.modules):
    if _name.split(".")[0] in ("maya_scenesetup", "maya_overrig", "maya_uebridge",
                               "maya_rigs", "maya_hubstyle", "maya_hubqt",
                               "maya_charlook", "maya_chargrid"):
        sys.modules.pop(_name, None)

import maya.cmds as cmds  # noqa: E402

from maya_scenesetup import catalog  # noqa: E402
from maya_scenesetup import character  # noqa: E402

RENDER = 512
FINAL = 256
FOCAL = 85.0
APERTURE = 1.417                 # inches, square film back
TURN = 22.0                      # degrees toward the character's left (+X)
RISE = 6.0                       # degrees above the frame's centre
CLAY = (0.33, 0.32, 0.31)
PANEL = "modelPanel4"
LIGHTS = (("portraitKey", (-32.0, 42.0, 0.0), (1.0, 0.92, 0.80), 1.6),
          ("portraitFill", (-10.0, -60.0, 0.0), (0.70, 0.80, 1.0), 0.45),
          ("portraitRim", (-20.0, 165.0, 0.0), (1.0, 0.95, 0.90), 1.4))


def _leaf(path):
    return path.split("|")[-1].split(":")[-1]


def _root_of(entry):
    """The new character's skeleton root."""
    if catalog.is_rig(entry):
        import maya_rigs
        rigs = maya_rigs.rigs()
        return rigs[0].skeleton_root if rigs else None
    from maya_overrig import builder
    roots = builder.character_roots()
    return roots[0] if roots else None


def _joint(root, leaf):
    for joint in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                              fullPath=True) or []):
        if _leaf(joint) == leaf:
            return joint
    raise RuntimeError("%s has no joint %s" % (root, leaf))


def _world(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def _meshes():
    shapes = cmds.ls(type="mesh", noIntermediate=True, long=True) or []
    out = []
    for shape in shapes:
        parent = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        path = parent
        visible = True
        while path:
            if not cmds.getAttr(path + ".visibility"):
                visible = False
                break
            up = cmds.listRelatives(path, parent=True, fullPath=True)
            path = up[0] if up else None
        if visible:
            out.append(parent)
    return out


def _clay(meshes):
    shader = cmds.shadingNode("phong", asShader=True, name="portraitClay")
    cmds.setAttr(shader + ".color", *CLAY, type="double3")
    cmds.setAttr(shader + ".specularColor", 0.18, 0.18, 0.18, type="double3")
    cmds.setAttr(shader + ".cosinePower", 18)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                      name="portraitClaySG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader")
    cmds.sets(meshes, edit=True, forceElement=group)


def _lights():
    for name, rotate, rgb, intensity in LIGHTS:
        shape = cmds.directionalLight(name=name, rgb=rgb, intensity=intensity)
        transform = cmds.listRelatives(shape, parent=True)[0]
        cmds.setAttr(transform + ".rotate", *rotate, type="double3")


def framing(head, left, right, crown):
    """(centre, side) of the square window: head and shoulders. Pure."""
    span = math.dist((left[0], left[2]), (right[0], right[2])) or 1.0
    shoulder = (left[1] + right[1]) / 2.0
    height = (crown - shoulder) * 1.18 + 0.60 * span
    side = max(height, 1.70 * span)
    top = crown + 0.08 * side
    centre = (head[0], top - side / 2.0, (left[2] + right[2] + head[2]) / 3.0)
    return centre, side


def _camera(centre, side):
    fov = 2.0 * math.atan((APERTURE * 25.4 / 2.0) / FOCAL)
    distance = (side / 2.0) / math.tan(fov / 2.0)
    turn, rise = math.radians(TURN), math.radians(RISE)
    offset = (math.sin(turn) * math.cos(rise), math.sin(rise),
              math.cos(turn) * math.cos(rise))
    position = [centre[i] + offset[i] * distance for i in range(3)]
    camera, _shape = cmds.camera(name="portraitCam", focalLength=FOCAL,
                                 horizontalFilmAperture=APERTURE,
                                 verticalFilmAperture=APERTURE, filmFit="fill",
                                 nearClipPlane=1.0, farClipPlane=10000.0)
    cmds.xform(camera, worldSpace=True, translation=position)
    forward = [centre[i] - position[i] for i in range(3)]
    flat = math.hypot(forward[0], forward[2])
    cmds.xform(camera, worldSpace=True, rotation=(
        math.degrees(math.atan2(forward[1], flat)),
        math.degrees(math.atan2(-forward[0], -forward[2])), 0.0))
    return camera


def _panel(camera):
    cmds.modelPanel(PANEL, edit=True, camera=camera)
    cmds.modelEditor(PANEL, edit=True, allObjects=False, polymeshes=True,
                     displayAppearance="smoothShaded", displayTextures=True,
                     displayLights="all", shadows=False, grid=False,
                     headsUpDisplay=False, selectionHiliteDisplay=False,
                     wireframeOnShaded=False, xray=False, useDefaultMaterial=False)
    for attr, value in (("ssaoEnable", 1), ("ssaoAmount", 1.0), ("multiSampleEnable", 1),
                        ("multiSampleCount", 16)):
        try:
            cmds.setAttr("hardwareRenderingGlobals." + attr, value)
        except Exception:                                    # noqa: BLE001
            pass


def _save(raw, out):
    from PySide6 import QtCore, QtGui
    image = QtGui.QImage(raw)
    if image.isNull():
        raise RuntimeError("the playblast wrote nothing readable: " + raw)
    image = image.convertToFormat(QtGui.QImage.Format_ARGB32)
    small = image.scaled(FINAL, FINAL, QtCore.Qt.KeepAspectRatio,
                         QtCore.Qt.SmoothTransformation)
    if not small.save(out, "PNG"):
        raise RuntimeError("could not write " + out)
    corner = image.pixelColor(2, 2)
    return corner.alpha()


def _idle(seconds):
    """Let Maya be idle for `seconds`: its idle queue and Qt's events, not a sleep."""
    import maya.utils
    from PySide6 import QtWidgets
    end = time.time() + seconds
    while time.time() < end:
        maya.utils.processIdleEvents()
        QtWidgets.QApplication.processEvents()
        time.sleep(0.05)


def render(model, out_dir):
    """One model's portrait into `out_dir`; its path and a line of numbers."""
    if catalog.is_auto(model):
        print("%s has no character - draw it with make_auto_portrait.py" % model)
        return None
    entry = catalog.character_for(model, "rig") or catalog.character_for(model, "skeleton")
    cmds.file(new=True, force=True)
    print(character.add_character(entry))
    cmds.select(clear=True)
    root = _root_of(entry)
    head = _world(_joint(root, "head"))
    left = _world(_joint(root, "upperarm_l"))
    right = _world(_joint(root, "upperarm_r"))
    meshes = _meshes()
    crown = max(cmds.exactWorldBoundingBox(mesh)[4] for mesh in meshes)
    if not getattr(entry, "textured", False):
        _clay(meshes)
    _lights()
    centre, side = framing(head, left, right, crown)
    camera = _camera(centre, side)
    _panel(camera)
    # Viewport 2.0 loads textures in the background: the first try at the
    # Orc D blasted its shoulder pads black, and six draws half a second apart
    # still blasted the textured Manny (2026-09-30) near black. The loading
    # moves on only while Maya is IDLE (a sleep holding the main thread let two
    # blasts agree on a half-loaded torso), so between blasts the idle queue and
    # Qt's events are run; a textured row is blasted until two agree.
    raw = os.path.join(out_dir, model + "_raw.png").replace("\\", "/")
    previous = None
    for attempt in range(40 if getattr(entry, "textured", False) else 1):
        cmds.refresh(force=True)
        cmds.playblast(frame=[cmds.currentTime(query=True)], format="image", compression="png",
                       completeFilename=raw, widthHeight=(RENDER, RENDER), percent=100,
                       viewer=False, showOrnaments=False, offScreen=True, forceOverwrite=True,
                       clearCache=True, editorPanelName=PANEL)
        with open(raw, "rb") as handle:
            picture = handle.read()
        if picture == previous and attempt >= 2:
            print("%s: the picture settled after %d blasts" % (model, attempt + 1))
            break
        previous = picture
        if getattr(entry, "textured", False):
            _idle(1.0)
    out = os.path.join(out_dir, model + ".png").replace("\\", "/")
    alpha = _save(raw, out)
    os.remove(raw)
    print("%s: %s  side %.1f cm  crown %.1f  corner alpha %d" % (
        model, out, side, crown, alpha))
    return out


def render_all(out_dir=None):
    out_dir = out_dir or os.path.join(REPO, "assets", "character_portraits")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    # the Auto card has no character to render: its «?» is drawn by make_auto_portrait.py
    return [render(model.key, out_dir) for model in catalog.MODELS
            if not catalog.is_auto(model.key)]


if __name__ == "__main__":
    OUT = os.environ.get("PORTRAITS_OUT") or None
    ONLY = os.environ.get("PORTRAITS_ONLY") or ""
    if ONLY:
        target = OUT or os.path.join(REPO, "assets", "character_portraits")
        if not os.path.isdir(target):
            os.makedirs(target)
        for key in ONLY.split(","):
            render(key, target)
    else:
        render_all(OUT)

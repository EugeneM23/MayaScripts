"""poseclip_tool - Pose on clip as a window: our poses onto a locomotion clip, tuned live.

Drop this file into a Maya viewport (or run `import poseclip_tool; poseclip_tool.show()` with this folder on
sys.path). Select the character carrying the clip - any bone, mesh, its label - and press Use selected (with
only one keyed character in the scene it is picked by itself). Pick a pose; every slider re-keys a copy of the
character beside it when it is let go. The original is never written; the copy is one undo step a change.

The animator, 2026-10-14: «Собери все скрипты в один инструмент что бы я его открыл потом выделил нужный мне
цикл бега и дальше мог работать применять позы и парамметры коррекции.»
Spec: docs/superpowers/specs/2026-10-14-pose-on-clip-design.md
"""
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import poseclip as model  # noqa: E402
import poseclip_maya as scene  # noqa: E402

WINDOW = "skeldarPoseClipTool"
PREFIX = "skeldarPoseClipTool_"
MODULES = ("poseclip_tool", "poseclip_maya", "poseclip", "posemath", "skeletonmap")
GROUPS = (
    ("Pose share", (("share_torso", "Torso"), ("share_pelvis", "Pelvis"), ("share_knees", "Knees"),
                    ("share_arms", "Arms"), ("share_feet", "Feet (stance)"))),
    ("Clip motion", (("motion_torso", "Torso"), ("motion_arms", "Arms"))),
    ("Pelvis, cm", (("pelvis_height", "Height"), ("pelvis_forward", "Forward"))),
    ("Stance and lean", (("width", "Width x"), ("stance_speed", "Stance at, cm/s"), ("lean_limit", "Lean limit, deg"))),
)
OFFSET, OFFSET_DEFAULT, OFFSET_RANGE = "offset", 150.0, (-400.0, 400.0)
CLIP_TEXT, POSE_MENU, STATUS = PREFIX + "clip", PREFIX + "pose", PREFIX + "status"
Refusal = model.Refusal


def onMayaDroppedPythonFile(*_):
    """Maya's viewport drop: the latest code (a drop imports a file by its stem once - trap 220), then the
    window."""
    for name in MODULES:
        sys.modules.pop(name, None)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import poseclip_tool
    poseclip_tool.show()


def _cmds():
    import maya.cmds as cmds
    return cmds


def _state():
    """The window's session on sys (a reloaded module must find it), started afresh when the model module is not
    the one that read it (an old Session's methods are the old code's - CLAUDE.md trap 226)."""
    state = getattr(sys, "_skeldar_poseclip", None)
    if state is None or state.get("model") is not model or state.get("scene") is not scene:
        state = {"model": model, "scene": scene, "session": None}
        sys._skeldar_poseclip = state
    return state


# ---- the core, without the window ----

def session(node=None, reload=False):
    """The character the window works on: the one already read (while it stands), else `node`'s / the
    selection's / the only keyed one, read now."""
    state = _state()
    current = state.get("session")
    if current is not None and not reload and node is None and current.alive():
        return current
    current = scene.Session(scene.character_root(node))
    state["session"] = current
    return current


def run(pose, k, offset=OFFSET_DEFAULT, node=None):
    """The pose `pose` with the knobs `k` onto the window's copy. Returns the status line."""
    started = time.time()
    current = session(node)
    pose_name = current.pose(pose)[0]
    result = current.evaluate(pose, k)
    copy, curves, removed = current.key(result, pose_name, k, offset, tool=True)
    return scene.status(current, result, pose_name, copy, removed, time.time() - started)


def delete_copy():
    current = _state().get("session")
    if current is None or not current.alive():
        raise Refusal("no character read yet - select it and press Use selected")
    with scene._Chunk("skeldarPoseClipDelete"):
        removed = scene.remove_copies(current.uuid, tool=True)
    return "the copy deleted" if removed else "no copy to delete"


# ---- the window ----

def _ctrl(name):
    return PREFIX + name


def _remembered(name, default):
    cmds = _cmds()
    var = PREFIX + name
    if cmds.optionVar(exists=var):
        try:
            return float(cmds.optionVar(query=var))
        except (TypeError, ValueError):
            pass
    return default


def _remember(name, value):
    _cmds().optionVar(floatValue=(PREFIX + name, float(value)))


def knobs_from_window():
    """The knobs as the sliders stand."""
    cmds = _cmds()
    given = {}
    for _title, rows in GROUPS:
        for name, _label in rows:
            given[name] = cmds.floatSliderGrp(_ctrl(name), query=True, value=True)
    return model.knobs(**given)


def _offset():
    return _cmds().floatSliderGrp(_ctrl(OFFSET), query=True, value=True)


def _pose():
    cmds = _cmds()
    value = cmds.optionMenu(POSE_MENU, query=True, value=True) if cmds.optionMenu(POSE_MENU, exists=True) else None
    if not value or value.startswith("("):
        raise Refusal("no pose - save one with Walk Builder's Save pose")
    return value


def _say(text):
    cmds = _cmds()
    if cmds.scrollField(STATUS, exists=True):
        cmds.scrollField(STATUS, edit=True, text=text)
    print("Pose on clip: " + text)


def _header():
    cmds = _cmds()
    current = _state().get("session")
    text = current.describe() if current is not None and current.alive() else \
        "No clip yet: select the character carrying it (a bone, a mesh, its label) and press Use selected."
    if cmds.text(CLIP_TEXT, exists=True):
        cmds.text(CLIP_TEXT, edit=True, label=text)


def _guard(action):
    """Every press through here: a refusal or an error on the status line, never only in the Script Editor."""
    def call(*_):
        try:
            text = action()
            if text:
                _say(text)
        except Refusal as error:
            _say(str(error))
        except Exception as error:                                   # noqa: BLE001
            traceback.print_exc()
            _say("error: %s (the Script Editor has the trace)" % error)
    return call


def apply_now():
    return run(_pose(), knobs_from_window(), _offset())


def use_selected():
    session(reload=True)
    _header()
    return apply_now()


def knob_changed(name):
    _remember(name, _cmds().floatSliderGrp(_ctrl(name), query=True, value=True))
    return apply_now()


def pose_changed(*_):
    cmds = _cmds()
    cmds.optionVar(stringValue=(PREFIX + "pose", _pose()))
    return apply_now()


def reset():
    cmds = _cmds()
    for _title, rows in GROUPS:
        for name, _label in rows:
            cmds.floatSliderGrp(_ctrl(name), edit=True, value=model.DEFAULTS[name])
            _remember(name, model.DEFAULTS[name])
    return apply_now()


def refresh_poses():
    cmds = _cmds()
    for item in cmds.optionMenu(POSE_MENU, query=True, itemListLong=True) or []:
        cmds.deleteUI(item)
    names = scene.pose_names()
    for name in names or ["(no poses)"]:
        cmds.menuItem(label=name, parent=POSE_MENU)
    wanted = cmds.optionVar(query=PREFIX + "pose") if cmds.optionVar(exists=PREFIX + "pose") else None
    if wanted in names:
        cmds.optionMenu(POSE_MENU, edit=True, value=wanted)
    return "%d poses in %s" % (len(names), scene.pose_folder())


def show():
    """The window (rebuilt), on the character already read, else the only keyed one in the scene."""
    cmds = _cmds()
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    cmds.window(WINDOW, title="Pose on clip", widthHeight=(420, 700), sizeable=True)
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=("both", 6))
    cmds.text(CLIP_TEXT, label="", align="left", wordWrap=True, height=52)
    cmds.button(label="Use selected", height=28, annotation="Read the clip of the selected character "
                "(a bone, a mesh, its label; nothing selected: the only keyed one)", command=_guard(use_selected))
    cmds.separator(height=6, style="none")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2, columnWidth3=(40, 260, 70))
    cmds.text(label="Pose")
    cmds.optionMenu(POSE_MENU, changeCommand=_guard(pose_changed))
    cmds.button(label="Refresh", command=_guard(refresh_poses), annotation="Read the poses folder again")
    cmds.setParent("..")
    for title, rows in GROUPS:
        cmds.frameLayout(label=title, collapsable=True, marginWidth=4, marginHeight=4)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        for name, label in rows:
            lo, hi = model.RANGES[name]
            cmds.floatSliderGrp(_ctrl(name), label=label, field=True, minValue=lo, maxValue=hi,
                                fieldMinValue=lo, fieldMaxValue=hi, value=_remembered(name, model.DEFAULTS[name]),
                                precision=2, step=(hi - lo) / 100.0, columnWidth3=(110, 60, 200), adjustableColumn=3,
                                columnAlign=(1, "left"), changeCommand=_guard(lambda n=name: knob_changed(n)))
        cmds.setParent("..")
        cmds.setParent("..")
    cmds.frameLayout(label="Copy", collapsable=True, marginWidth=4, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
    lo, hi = OFFSET_RANGE
    cmds.floatSliderGrp(_ctrl(OFFSET), label="Offset, cm", field=True, minValue=lo, maxValue=hi, fieldMinValue=lo,
                        fieldMaxValue=hi, value=_remembered(OFFSET, OFFSET_DEFAULT), precision=0, step=10.0,
                        columnWidth3=(110, 60, 200), adjustableColumn=3, columnAlign=(1, "left"),
                        annotation="Where the copy stands: + to the character's right, - to its left",
                        changeCommand=_guard(lambda: knob_changed(OFFSET)))
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, columnWidth3=(160, 120, 120))
    cmds.button(label="Apply", height=30, command=_guard(apply_now))
    cmds.button(label="Reset knobs", height=30, command=_guard(reset))
    cmds.button(label="Delete copy", height=30, command=_guard(delete_copy))
    cmds.setParent("..")
    cmds.scrollField(STATUS, editable=False, wordWrap=True, height=96, text="")
    cmds.showWindow(WINDOW)
    refresh_poses()
    # the character: the one already read, else - quietly - the only keyed one in the scene
    try:
        session()
    except Refusal:
        pass
    _header()
    _say("Pick a pose and move a slider - the copy is re-keyed when you let go. Apply re-keys it now.")

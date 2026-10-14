"""poseclip_tool - Pose on clip as a window: our poses onto a locomotion clip, tuned live.

Drop this file into a Maya viewport (or run `import poseclip_tool; poseclip_tool.show()` with this folder on
sys.path). Select the character carrying the clip - any bone, mesh, its label - and press Use selected (with
only one keyed character in the scene it is picked by itself). Pick a final pose and a start pose, each with
its share and the parts it takes; every slider re-keys a copy of the character beside it when it is let go. The
original is never written; the copy is one undo step a change.

Laid out as Walk Builder's card (spec addendum 4): the poses at the top, the knobs in tabs - Stop, Legs,
Pelvis, Chest, Arms, Weight - one shown at a time, and [Both | Left | Right] for the knobs a body part has two
of. The start pose can be the cycle's own posture: the stop then runs in the posture of the cycle it starts on.

The animator, 2026-10-14: «Собери все скрипты в один инструмент что бы я его открыл потом выделил нужный мне
цикл бега и дальше мог работать применять позы и парамметры коррекции.» - and later: «Мне бы хотелось тут иметь
такие же инструменты которые бы контролировали веса позы и все остальное. Так же нужно добавить опцию которая
будет за основу для старта брать позу исходного цикла.»
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
#  (tab, ((knob, label, tooltip), ...)) - Walk Builder's names where the knob is Walk Builder's
TABS = (
    ("Stop", (
        ("final_speed", "Final pose at, cm/s", "The start pose is all there is while the body moves faster; the "
                                               "final pose comes in as it slows to this"),
        ("stance_speed", "Stance at, cm/s", "The pose's stance (its width, its balance over its feet) is gone "
                                            "at this speed and comes in as the body stops"),
        ("from_cycle", "From the cycle, fr", "Frames the stop takes to go from the cycle's frames to its own "
                                             "(with a cycle set)"),
        ("offset", "Copy offset, cm", "Where the copy stands: + to the character's right, - to its left"))),
    ("Legs", (
        ("stance", "Stance x", "x each foot's place across the stance (the pose's width): 0 the feet together"),
        ("lift", "Foot lift x", "x the swinging foot's height over its line from takeoff to landing"),
        ("swing_out", "Swing out, cm", "The swing bowed out (+) or in (-), sideways"),
        ("leg_match", "Leg match", "Running, a side-on pose's hips face the run and its knees and toes keep only "
                                   "the splay the gait allows; standing, the pose stands as it is"),
        ("leg_turn", "Leg turn x", "x the poses' knee and toe turns"),
        ("knee_foot", "Knee <-> foot", "A knee and its foot turned apart past 15 deg meet: 0 the knee goes to "
                                       "the foot, 1 the foot to the knee"),
        ("foot_lag", "Foot lag, fr", "Frames the swinging foot trails its shin"),
        ("foot_flex", "Foot flex x", "x the swinging foot's turn in its ankle (and the toes')"))),
    ("Pelvis", (
        ("pelvis_height", "Height, cm", "The pelvis up (+) or down (-) - the legs follow by IK"),
        ("pelvis_forward", "Forward, cm", "The hips ahead (+) or behind (-) of where the balance puts them"),
        ("bob", "Bob x", "x the pelvis's up and down"),
        ("pelvis_rot", "Pelvis turns x", "x the pelvis's turns over the reference"))),
    ("Chest", (
        ("spine", "Spine x", "x the spine's and the neck's motion"),
        ("gait_lean", "Gait lean", "x the forward lean the clip's motion keeps (in the room the pose leaves)"),
        ("lean_limit", "Lean limit, deg", "The trunk's forward lean never past this"),
        ("head", "Head x", "x the head's motion in the world; 0 keeps the pose's gaze"),
        ("torso_drag", "Torso drag, fr", "Overlap: frames the trunk trails its motion by"),
        ("torso_bounce", "Torso bounce", "How far the trunk and the head overshoot"),
        ("head_drag", "Head drag, fr", "Frames the head trails its gaze by"))),
    ("Arms", (
        ("arms", "Arms x", "x the clip's motion in the arms and fingers"),
        ("elbow", "Elbow x", "x the forearm's own motion in the elbow, on top of Arms"),
        ("arm_drag", "Arm drag, fr", "Overlap: frames the arms trail by"),
        ("arm_bounce", "Arm bounce", "How far the arms overshoot"))),
    ("Weight", (
        ("balance", "Balance", "How far the pelvis is carried to keep the centre of mass over the feet"),
        ("exaggeration", "Exaggeration x", "x every motion of the clip: spine, pelvis, bob, head, arms"))),
)
PART_LABELS = (("torso", "Torso"), ("pelvis", "Pelvis"), ("knees", "Knees"), ("arms", "Arms"), ("feet", "Feet"))
SIDE_LABELS = ("Both", "Left", "Right")
OFFSET, OFFSET_DEFAULT, OFFSET_RANGE = "offset", 150.0, (-400.0, 400.0)
CLIP_TEXT, STATUS, CYCLE_TEXT = PREFIX + "clip", PREFIX + "status", PREFIX + "cycle"
POSE_MENU, START_MENU = PREFIX + "pose", PREFIX + "startPose"
SIDE_ROW, TAB_LAYOUT = PREFIX + "side", PREFIX + "tabs"
SAME = "(same as final)"
CYCLE = scene.CYCLE_START
Refusal = model.Refusal
_QUIET = [False]            # set while the window fills itself from memory: a control's command does nothing


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
        old = state.get("session") if state else None
        hint = getattr(old, "uuid", None) or (state.get("hint") if state else None)
        state = {"model": model, "scene": scene, "session": None, "hint": hint}   # the character, read again
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
    if current is None and not reload and node is None and state.get("hint"):
        found = _cmds().ls(state["hint"], long=True)     # the character the window had before a reload
        node = found[0] if found else None
    current = scene.Session(scene.character_root(node))
    state["hint"] = current.uuid
    state["session"] = current
    return current


def run(pose, k, offset=OFFSET_DEFAULT, node=None, start=None):
    """The final pose `pose` (the start pose `start` on the run: a pose's name, CYCLE - the cycle's posture -,
    None: the final all along) with the knobs `k` onto the window's copy, from the session's cycle when one is
    set. Returns the status line."""
    started = time.time()
    current = session(node)
    pose_name = current.pose(pose)[0]
    note = ""
    if start == CYCLE and current.posture is None:      # no cycle read yet: the final pose all along, said so
        start = None
        note = " | NO CYCLE: the start pose is the final one until you select a looping clip and press Use " \
               "selected as cycle"
    if start and start == pose:
        note += " | the start pose IS the final pose - pick another start to see one"
    start_name = current.start_label(start)
    result = current.evaluate(pose, k, start)
    copy, curves, removed = current.key(result, pose_name, k, offset, tool=True, start_name=start_name)
    _state()["last"] = result.info
    return scene.status(current, result, pose_name, copy, removed, time.time() - started, start_name) + note


def use_cycle(node=None):
    """The selected (or `node`'s) looping clip as the cycle the stop starts on."""
    cmds = _cmds()
    if node is None:
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            raise Refusal("select the character carrying the cycle (a bone, a mesh)")
        node = selection[0]
    return session().use_cycle(node)


def clear_cycle():
    current = _state().get("session")
    if current is not None:
        current.clear_cycle()


def delete_copy():
    current = _state().get("session")
    if current is None or not current.alive():
        raise Refusal("no character read yet - select it and press Use selected")
    with scene._Chunk("skeldarPoseClipDelete"):
        removed = scene.remove_copies(current.uuid, tool=True)
    return "the copy deleted" if removed else "no copy to delete"


# ---- the memory: optionVars, the window's truth (a side's slider shows one side of a knob) ----

def _var(name):
    return PREFIX + name


def _remembered(name, default):
    cmds = _cmds()
    var = _var(name)
    if cmds.optionVar(exists=var):
        try:
            return float(cmds.optionVar(query=var))
        except (TypeError, ValueError):
            pass
    return default


def _remember(name, value):
    _cmds().optionVar(floatValue=(_var(name), float(value)))


def _forget(name):
    cmds = _cmds()
    if cmds.optionVar(exists=_var(name)):
        cmds.optionVar(remove=_var(name))


def _side_value(name, side):
    """A knob as one side reads it: its own value where it has one, else the knob's."""
    base = _remembered(name, model.DEFAULTS[name])
    return _remembered("%s_%s" % (name, side), base)


def _part_on(which, part):
    return _remembered("%s_%s" % (which, part), 1.0) > 0.5


def knobs_from_memory():
    """Every knob as the window holds it: the tabs' knobs (and a side's own values), each pose's share x its lit
    parts."""
    given = {}
    for _tab, rows in TABS:
        for name, _label, _tip in rows:
            if name in model.DEFAULTS:
                given[name] = _remembered(name, model.DEFAULTS[name])
    for name in model.SIDED:
        for side in model.SIDES:
            if _cmds().optionVar(exists=_var("%s_%s" % (name, side))):
                given["%s_%s" % (name, side)] = _remembered("%s_%s" % (name, side), given[name])
    for which, knob in (("final", "share"), ("start", "start")):
        share = _remembered(which + "Share", 1.0)
        for part, _label in PART_LABELS:
            given["%s_%s" % (knob, part)] = share if _part_on(which, part) else 0.0
    return model.knobs(**given)


knobs_from_window = knobs_from_memory


# ---- the window ----

def _ctrl(name):
    return PREFIX + name


def _side():
    cmds = _cmds()
    if not cmds.radioButtonGrp(SIDE_ROW, exists=True):
        return "both"
    return ("both", "l", "r")[max(cmds.radioButtonGrp(SIDE_ROW, query=True, select=True), 1) - 1]


def _label_of(name):
    for _tab, rows in TABS:
        for knob, label, _tip in rows:
            if knob == name:
                return label
    return name


def _show_sides():
    """The sided sliders as the side row reads them: Both - the knob, marked * where its sides differ; Left or
    Right - that side's value, its label marked L or R."""
    cmds = _cmds()
    side = _side()
    _QUIET[0] = True
    try:
        for name in model.SIDED:
            ctrl = _ctrl(name)
            if not cmds.floatSliderGrp(ctrl, exists=True):
                continue
            label = _label_of(name)
            if side == "both":
                base = _remembered(name, model.DEFAULTS[name])
                differ = any(abs(_side_value(name, s) - base) > 1e-6 for s in model.SIDES)
                cmds.floatSliderGrp(ctrl, edit=True, value=base, label=label + (" *" if differ else ""))
            else:
                cmds.floatSliderGrp(ctrl, edit=True, value=_side_value(name, side),
                                    label="%s  %s" % (label, side.upper()))
    finally:
        _QUIET[0] = False


def _pose():
    cmds = _cmds()
    value = cmds.optionMenu(POSE_MENU, query=True, value=True) if cmds.optionMenu(POSE_MENU, exists=True) else None
    if not value or value.startswith("(no "):
        raise Refusal("no pose - save one with Walk Builder's Save pose")
    return value


def _start():
    """The start as the menu reads it: None (the final all along), CYCLE, or a pose's name."""
    cmds = _cmds()
    value = cmds.optionMenu(START_MENU, query=True, value=True) if cmds.optionMenu(START_MENU, exists=True) else None
    if not value or value == SAME:
        return None
    return value


def _offset():
    return _remembered(OFFSET, OFFSET_DEFAULT)


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


def _cycle_line():
    cmds = _cmds()
    current = _state().get("session")
    text = ("Starts on " + current.cycle_name) if current is not None and current.cycle is not None else \
        "No cycle: the stop starts as the clip does. Select a looping clip and press Use selected as cycle."
    if cmds.text(CYCLE_TEXT, exists=True):
        cmds.text(CYCLE_TEXT, edit=True, label=text)


def _start_enabled():
    """The start pose's share and chips mean nothing while the start is the final pose."""
    cmds = _cmds()
    on = _start() is not None
    if cmds.floatSliderGrp(_ctrl("startShare"), exists=True):
        cmds.floatSliderGrp(_ctrl("startShare"), edit=True, enable=on)
    for part, _label in PART_LABELS:
        if cmds.checkBox(_ctrl("start_" + part), exists=True):
            cmds.checkBox(_ctrl("start_" + part), edit=True, enable=on)


def _guard(action):
    """Every press through here: a refusal or an error on the status line, never only in the Script Editor;
    nothing while the window fills itself."""
    def call(*_):
        if _QUIET[0]:
            return
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
    return run(_pose(), knobs_from_memory(), _offset(), start=_start())


def _set_start(value):
    """The start menu to `value` quietly (setting an optionMenu by code fires its command - trap 116), and
    remembered."""
    cmds = _cmds()
    _QUIET[0] = True
    try:
        if cmds.optionMenu(START_MENU, exists=True):
            cmds.optionMenu(START_MENU, edit=True, value=value)
    finally:
        _QUIET[0] = False
    cmds.optionVar(stringValue=(_var("start"), value))
    _start_enabled()


def cycle_picked():
    """A cycle read; a start that was the final pose becomes the cycle's posture (the point of starting on a
    cycle is to start in it)."""
    name = use_cycle()
    _cycle_line()
    note = ""
    if _start() is None:
        _set_start(CYCLE)
        note = " | the start pose is now the cycle's posture"
    return apply_now() + note


def cycle_cleared():
    clear_cycle()
    _cycle_line()
    if _start() == CYCLE:
        _set_start(SAME)
    return apply_now()


def start_changed(*_):
    _cmds().optionVar(stringValue=(_var("start"), _cmds().optionMenu(START_MENU, query=True, value=True)))
    _start_enabled()
    return apply_now()


def pose_changed(*_):
    _cmds().optionVar(stringValue=(_var("pose"), _pose()))
    return apply_now()


def use_selected():
    current = session(reload=True)
    _header()
    _cycle_line()
    if _start() == CYCLE and current.cycle is None:
        _set_start(SAME)
    return apply_now()


def knob_changed(name):
    """A slider let go: remembered (a sided knob for the side the row shows, or both sides linked again in
    Both), the copy re-keyed."""
    value = _cmds().floatSliderGrp(_ctrl(name), query=True, value=True)
    side = _side()
    if name in model.SIDED and side != "both":
        _remember("%s_%s" % (name, side), value)
    else:
        _remember(name, value)
        if name in model.SIDED:
            for s in model.SIDES:
                _forget("%s_%s" % (name, s))
    _show_sides()
    return apply_now()


def share_changed(which):
    _remember(which + "Share", _cmds().floatSliderGrp(_ctrl(which + "Share"), query=True, value=True))
    return apply_now()


def part_changed(which, part):
    _remember("%s_%s" % (which, part), 1.0 if _cmds().checkBox(_ctrl("%s_%s" % (which, part)), query=True,
                                                               value=True) else 0.0)
    return apply_now()


def side_changed(*_):
    _show_sides()
    _cmds().optionVar(intValue=(_var("side"), _cmds().radioButtonGrp(SIDE_ROW, query=True, select=True)))


def tab_changed(*_):
    cmds = _cmds()
    _cmds().optionVar(intValue=(_var("tab"), cmds.tabLayout(TAB_LAYOUT, query=True, selectTabIndex=True)))


def reset():
    """Every knob to its default, both sides linked; the poses' shares and parts kept."""
    cmds = _cmds()
    _QUIET[0] = True
    try:
        for _tab, rows in TABS:
            for name, _label, _tip in rows:
                default = model.DEFAULTS.get(name, OFFSET_DEFAULT)
                _remember(name, default)
                if name in model.SIDED:
                    for s in model.SIDES:
                        _forget("%s_%s" % (name, s))
                cmds.floatSliderGrp(_ctrl(name), edit=True, value=default)
    finally:
        _QUIET[0] = False
    _show_sides()
    return apply_now()


def refresh_poses():
    """The poses folder read again into both menus (nothing re-keyed)."""
    cmds = _cmds()
    names = scene.pose_names()
    _QUIET[0] = True
    try:
        for menu, first, var in ((POSE_MENU, (), "pose"), (START_MENU, (SAME, CYCLE), "start")):
            for item in cmds.optionMenu(menu, query=True, itemListLong=True) or []:
                cmds.deleteUI(item)
            items = list(first) + (names or ([] if first else ["(no poses)"]))
            for name in items:
                cmds.menuItem(label=name, parent=menu)
            wanted = cmds.optionVar(query=_var(var)) if cmds.optionVar(exists=_var(var)) else None
            if wanted in items:
                cmds.optionMenu(menu, edit=True, value=wanted)
    finally:
        _QUIET[0] = False
    _start_enabled()
    return "%d poses in %s" % (len(names), scene.pose_folder())


def _pose_row(which, title, menu, command, tip):
    """A pose's row: its menu, then its share and the parts it takes (Walk Builder's)."""
    cmds = _cmds()
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(70, 300))
    cmds.text(label=title, align="left", annotation=tip)
    cmds.optionMenu(menu, changeCommand=_guard(command), annotation=tip)
    cmds.setParent("..")
    cmds.floatSliderGrp(_ctrl(which + "Share"), label="  Share", field=True, minValue=0.0, maxValue=1.0,
                        fieldMinValue=0.0, fieldMaxValue=1.0, value=_remembered(which + "Share", 1.0), precision=2,
                        step=0.01, columnWidth3=(70, 50, 200), adjustableColumn=3, columnAlign=(1, "left"),
                        annotation="How much of the %s pose the lit parts take" % which,
                        changeCommand=_guard(lambda w=which: share_changed(w)))
    cmds.rowLayout(numberOfColumns=len(PART_LABELS) + 1, columnWidth=[(1, 70)] + [(i + 2, 64) for i in
                                                                                 range(len(PART_LABELS))])
    cmds.text(label="")
    for part, label in PART_LABELS:
        cmds.checkBox(_ctrl("%s_%s" % (which, part)), label=label, value=_part_on(which, part),
                      annotation="The %s pose's %s" % (which, label.lower()),
                      changeCommand=_guard(lambda _v=None, w=which, p=part: part_changed(w, p)))
    cmds.setParent("..")


def show():
    """The window (rebuilt), on the character already read, else the only keyed one in the scene."""
    cmds = _cmds()
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    if cmds.windowPref(WINDOW, exists=True):
        cmds.windowPref(WINDOW, remove=True)
    cmds.window(WINDOW, title="Pose on clip", widthHeight=(440, 780), sizeable=True)
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=("both", 6))
    cmds.text(CLIP_TEXT, label="", align="left", wordWrap=True, height=52)
    cmds.button(label="Use selected", height=28, annotation="Read the clip of the selected character "
                "(a bone, a mesh, its label; nothing selected: the only keyed one)", command=_guard(use_selected))
    cmds.separator(height=8, style="in")
    _pose_row("final", "Final pose", POSE_MENU, pose_changed, "The pose the body stops in")
    cmds.separator(height=6, style="none")
    _pose_row("start", "Start pose", START_MENU, start_changed,
              "The pose on the run: (same as final) - the final all along; (the cycle's posture) - the posture "
              "of the cycle the stop starts on; or a pose")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnWidth2=(70, 300))
    cmds.text(label="")
    cmds.button(label="Refresh poses", height=22, command=_guard(refresh_poses),
                annotation="Read the poses folder again (Walk Builder's Save pose writes there)")
    cmds.setParent("..")
    cmds.separator(height=8, style="in")
    cmds.text(CYCLE_TEXT, label="", align="left", wordWrap=True, height=36)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnWidth2=(220, 120))
    cmds.button(label="Use selected as cycle", command=_guard(cycle_picked),
                annotation="The stop starts on a frame of the selected looping clip (Walk Builder's, any loop) - "
                           "and the start pose can be its posture")
    cmds.button(label="Clear cycle", command=_guard(cycle_cleared))
    cmds.setParent("..")
    cmds.separator(height=8, style="in")
    cmds.radioButtonGrp(SIDE_ROW, label="Sides", numberOfRadioButtons=3, labelArray3=SIDE_LABELS,
                        select=int(_remembered("side", 1)), columnWidth4=(70, 70, 70, 70), columnAlign=(1, "left"),
                        annotation="Both: a leg or arm knob sets both sides (marked * where they differ); Left or "
                                   "Right: that side alone", changeCommand=_guard(side_changed))
    cmds.tabLayout(TAB_LAYOUT, innerMarginWidth=4, innerMarginHeight=4, changeCommand=_guard(tab_changed))
    for tab, rows in TABS:
        column = cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
        for name, label, tip in rows:
            if name == OFFSET:
                lo, hi = OFFSET_RANGE
                default, precision = OFFSET_DEFAULT, 0
            else:
                lo, hi = model.RANGES[name]
                default, precision = model.DEFAULTS[name], 2
            cmds.floatSliderGrp(_ctrl(name), label=label, field=True, minValue=lo, maxValue=hi, fieldMinValue=lo,
                                fieldMaxValue=hi, value=_remembered(name, default), precision=precision,
                                step=(hi - lo) / 100.0, columnWidth3=(120, 60, 200), adjustableColumn=3,
                                columnAlign=(1, "left"), annotation=tip,
                                changeCommand=_guard(lambda _v=None, n=name: knob_changed(n)))
        cmds.setParent("..")
        cmds.tabLayout(TAB_LAYOUT, edit=True, tabLabel=(column, tab))
    tab = int(_remembered("tab", 1))
    if 1 <= tab <= len(TABS):
        cmds.tabLayout(TAB_LAYOUT, edit=True, selectTabIndex=tab)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1, columnWidth3=(160, 120, 120))
    cmds.button(label="Apply", height=30, command=_guard(apply_now), annotation="Re-key the copy now")
    cmds.button(label="Reset knobs", height=30, command=_guard(reset),
                annotation="Every knob of the tabs to its default, both sides linked; the poses kept")
    cmds.button(label="Delete copy", height=30, command=_guard(delete_copy))
    cmds.setParent("..")
    cmds.scrollField(STATUS, editable=False, wordWrap=True, height=110, text="")
    cmds.showWindow(WINDOW)
    refresh_poses()
    _show_sides()
    # the character: the one already read, else - quietly - the only keyed one in the scene
    try:
        current = session()
        if _start() == CYCLE and current.cycle is None:
            _set_start(SAME)
    except Refusal:
        pass
    _header()
    _cycle_line()
    _say("Pick the poses and move a slider - the copy is re-keyed when you let go. Apply re-keys it now.")

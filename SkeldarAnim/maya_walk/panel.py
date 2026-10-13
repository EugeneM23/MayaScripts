"""Walk Builder - the hub card of the parametric walk (2026-10-13).

The animator: «Давай встроим этот скрипт в наш плагин. Интерфейс рисуй компактным» - the standalone window
of docs/superpowers/plans/walkparam/ becomes a card. Compact: the walk and the pose each one dropdown with a
save icon beside it, the pose's share and its parts on two lines, Apply / Reset, and the knobs in six groups
of which ONE is shown at a time ([Step | Legs | Pelvis | Chest | Arms | Weight]).

Select a skeleton and press Apply: the walk is keyed onto it and it becomes the card's target - a released
knob re-keys it. Selecting a skeleton that already walks reads its walk, pose and knobs into the card (what
the window's Pick did), and it becomes the target. Every value is remembered (optionVars), so the card comes
back as it was and a hotkey row presses with the card closed.
The design: docs/superpowers/specs/2026-10-13-walk-builder-card-design.md.
"""
import json
import os
import traceback

from . import scene

HUB_SECTION = "walk"
SUBTITLE = "skeldarWalkSubtitle"
STATUS = "skeldarWalkStatus"
WALK_MENU = "skeldarWalkMenu"
POSE_MENU = "skeldarWalkPoseMenu"
APPLY_BTN = "skeldarWalkApply"
RESET_BTN = "skeldarWalkReset"
SAVE_WALK_BTN = "skeldarWalkSaveWalk"
SAVE_POSE_BTN = "skeldarWalkSavePose"
GROUP_TABS = "skeldarWalkGroups"
OPTION = "skeldarWalk_"
NO_POSE = scene.NO_POSE
NOTHING = "Select a skeleton - Apply puts the walk on it"

#  The knobs but Pose (its share stands under the pose's dropdown), one group shown at a time.
GROUPS = (
    ("step", "Step", ("stride", "tempo", "lift")),
    ("legs", "Legs", ("foot_placement", "stance", "swing_out", "leg_turn", "knee_foot", "foot_lag", "foot_flex")),
    ("pelvis", "Pelvis", ("pelvis_height", "bob", "sway", "pelvis_rot", "pelvis_twist", "pelvis_list",
                          "root_sway")),
    ("chest", "Chest", ("spine", "chest_twist", "chest_sway", "head")),
    ("arms", "Arms", ("arms", "elbow", "arm_drag", "arm_bounce", "overlap")),
    ("weight", "Weight", ("weight", "balance", "exaggeration")),
)
PART_LABELS = (("torso", "Torso"), ("pelvis", "Pelvis"), ("knees", "Knees"), ("arms", "Arms"), ("feet", "Feet"))
LABELS = {
    "pose": ("Pose", "How far the pose picked above replaces the walk's own (its parts below): 0 is the walk, "
                     "1 the pose"),
    "stride": ("Stride", "x the step length; the travel follows (a long stride sinks the contacts)"),
    "tempo": ("Tempo, fr", "Frames a cycle of two steps; fewer is faster"),
    "lift": ("Foot lift", "x how high the swinging foot rises above its path"),
    "foot_placement": ("Foot placement", "1: a planted foot never slides (it rolls heel to ball about a still "
                                         "point) and one foot is always on the ground - both are down a while "
                                         "at every step; 0 is the walk's own feet, slides and all"),
    "stance": ("Stance", "x how far apart the feet stand on the ground (the pose's spread included); 0 puts "
                         "them on one line, 1 is the walk with the pose"),
    "swing_out": ("Swing out, cm", "The swinging foot's path bowed this far out to its side between the "
                                   "steps (negative: in, toward the other leg), in the walk's size"),
    "leg_turn": ("Leg turn", "x how far the pose turns the knees and the toes out (or in); 0 walks on the "
                             "walk's own knees and feet"),
    "knee_foot": ("Knee <-> foot", "A knee turned against its foot past 15 deg (a shin twists that far) "
                                   "meets it: 0 turns the knee to the foot, 1 the foot to the knee"),
    "foot_lag": ("Foot lag, fr", "Frames the swinging foot trails its shin: it flicks through after it "
                                 "leaves the ground and catches up before it lands (the toes 1.5x)"),
    "foot_flex": ("Foot flex", "x how far the swinging foot turns in its ankle (and the toes in theirs)"),
    "pelvis_height": ("Pelvis height", "cm: raises (+) or lowers (-) the pelvis over the feet, the legs "
                                       "following - a walk or a pose that crouches stands up; the legs never "
                                       "straighten past the walk's straightest, so the feet stay down"),
    "bob": ("Bob", "x the pelvis's up and down"),
    "sway": ("Sway", "x the pelvis's side to side"),
    "pelvis_rot": ("Pelvis motion", "x all the pelvis's turns and tilts (Twist and Hip drop included)"),
    "pelvis_twist": ("Twist, deg", "The pelvis turns this far each way with the legs, the forward leg's hip "
                                   "forward - at a normal step (0.8 of the leg); it grows with the step. "
                                   "People: about 5; the lower back takes it back"),
    "pelvis_list": ("Hip drop, deg", "The standing leg's hip this far up, the swinging leg's down, highest "
                                     "just after the foot lands. People: about 4"),
    "root_sway": ("Root sway", "0: the root runs straight down the walk's line (what a game's capsule "
                               "wants); 1 weaves with the hips as the walk does"),
    "spine": ("Spine", "x the spine's and the neck's motion (Chest twist and sway included)"),
    "chest_twist": ("Chest twist", "deg: the shoulders turn this far each way against the hips' turn, at a "
                                   "normal step; it grows with the step. People: about 7"),
    "chest_sway": ("Chest sway", "deg: the shoulder line tilts this far each way over the steps. People: "
                                 "about 5"),
    "head": ("Head", "x the head's motion in the world (0 holds it steady)"),
    "arms": ("Arms", "x the arms' own swing - about a pose's arms too (they are the mean it swings about); "
                     "hands holding one thing together hold it"),
    "elbow": ("Elbow", "x the forearm's own swing in the elbow, on top of Arms"),
    "arm_drag": ("Arm drag, fr", "The arms trail the body with weight: each limb follows through a spring "
                                 "that feels the shoulder's motion - about this many frames late. A held "
                                 "weapon trails the same way. 0: the arms exactly as the walk puts them"),
    "arm_bounce": ("Arm bounce", "How far the arms overshoot as they catch up: 0 settles, 1 whips through"),
    "overlap": ("Overlap, fr", "Frames the hands' own motion runs late against the pelvis (the spine and "
                               "the head less)"),
    "weight": ("Weight", "Heavier: deeper, longer low poses, a slower rise, more overlap; negative: lighter"),
    "balance": ("Balance", "How far the centre of mass follows the feet like a pendulum: wider feet, a "
                           "slower step, a crouch sway it more; a leaning pose takes the hips back over the "
                           "feet. 0 leaves the pelvis to the other knobs"),
    "exaggeration": ("Exaggeration", "x every motion around the mean pose at once (not the stride)"),
}
TIPS = {
    "apply": "Put the walk on the selected skeleton (UE5/UE4, Mixamo, HumanIK, Unity, Biped ...), in its own "
             "proportions, from where it stands. It becomes the target: every released knob re-keys it. "
             "Selecting a walked skeleton reads its walk, pose and knobs back.",
    "reset": "Every knob back to its default (the tempo to the walk's own); the target is keyed again",
    "save_walk": "Save walk: select a bone of a walk cycle (a closed loop with root motion) and press",
    "save_pose": "Save pose: select a skeleton standing in a character pose and press; the walk takes its "
                 "parts at the Pose share",
    "parts": "What of the pose replaces the walk's own (Arms: the mean the walk's swing runs about - hands "
             "holding one thing together hold it; Feet: the width and the toes' turn)",
}
#  The selection job of each card standing: '' the hub's, a popup copy's tag its own.
JOB = {}
#  True while the card is being filled from the scene: an optionMenu's value set by code fires its
#  changeCommand (maya_vpstudio's note), and that must not re-key anything.
_QUIET = [False]


def _cmds():
    import maya.cmds as cmds
    return cmds


def _control(name):
    return OPTION + name


def _part_control(part):
    return "skeldarWalkPart_" + part


def _group_column(key):
    return "skeldarWalkGroup_" + key


def _group_tab(key):
    return "skeldarWalkGroupTab_" + key


# ---- the memory ----

def _stored(name, default=None):
    cmds = _cmds()
    key = OPTION + name
    return cmds.optionVar(query=key) if cmds.optionVar(exists=key) else default


def _remember(name, value):
    cmds = _cmds()
    if isinstance(value, str):
        cmds.optionVar(stringValue=(OPTION + name, value))
    else:
        cmds.optionVar(floatValue=(OPTION + name, float(value)))


def values():
    """The knobs: the card's where it stands (and remembered), else what was remembered."""
    cmds = _cmds()
    out = {}
    for name, default in scene.wm.DEFAULTS.items():
        control = _control(name)
        if name == "tempo" and cmds.intSliderGrp(control, exists=True):
            out[name] = float(cmds.intSliderGrp(control, query=True, value=True))
        elif name != "tempo" and cmds.floatSliderGrp(control, exists=True):
            out[name] = float(cmds.floatSliderGrp(control, query=True, value=True))
        else:
            out[name] = float(_stored("knob_" + name, default))
            continue
        _remember("knob_" + name, out[name])
    return out


def chosen_walk():
    cmds = _cmds()
    names = scene.walk_names()
    if not names:
        raise scene.Refusal("no walk saved yet - select a bone of a walk cycle and press Save walk")
    value = cmds.optionMenu(WALK_MENU, query=True, value=True) if cmds.optionMenu(WALK_MENU, exists=True) \
        else _stored("walk")
    return value if value in names else names[0]


def chosen_pose():
    cmds = _cmds()
    value = cmds.optionMenu(POSE_MENU, query=True, value=True) if cmds.optionMenu(POSE_MENU, exists=True) \
        else _stored("pose")
    return None if not value or value == NO_POSE or value not in scene.pose_names() else value


def chosen_parts():
    cmds = _cmds()
    if cmds.checkBox(_part_control(PART_LABELS[0][0]), exists=True):
        return tuple(part for part, _ in PART_LABELS if cmds.checkBox(_part_control(part), query=True, value=True))
    stored = _stored("parts")
    if stored is None:
        return scene.ALL_PARTS
    try:
        return tuple(p for p in json.loads(stored) if p in scene.ALL_PARTS)
    except (TypeError, ValueError):
        return scene.ALL_PARTS


# ---- filling the card ----

def _fill(menu, names, selected, first=None):
    cmds = _cmds()
    for item in cmds.optionMenu(menu, query=True, itemListLong=True) or []:
        cmds.deleteUI(item)
    items = ([first] if first else []) + list(names)
    for name in items:
        cmds.menuItem(label=name, parent=menu)
    if selected in items:
        cmds.optionMenu(menu, edit=True, value=selected)


def _fill_menus(walk=None, pose=None):
    cmds = _cmds()
    if not cmds.optionMenu(WALK_MENU, exists=True):
        return
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        _fill(WALK_MENU, scene.walk_names(), walk or _stored("walk"))
        _fill(POSE_MENU, scene.pose_names(), pose or _stored("pose") or NO_POSE, first=NO_POSE)
    finally:
        _QUIET[0] = quiet


def _set_knobs(knobs, frames):
    """The knobs into the card (and the memory); the tempo's range follows the walk's own `frames`."""
    cmds = _cmds()
    for name, value in knobs.items():
        if name not in scene.wm.DEFAULTS:
            continue
        control = _control(name)
        if name == "tempo":
            shown = int(round(value)) if value >= 1 else int(frames)
            if cmds.intSliderGrp(control, exists=True):
                cmds.intSliderGrp(control, edit=True, minValue=max(4, frames // 2), maxValue=2 * frames,
                                  fieldMaxValue=4 * frames, value=shown)
            _remember("knob_" + name, shown)
        else:
            if cmds.floatSliderGrp(control, exists=True):
                cmds.floatSliderGrp(control, edit=True, value=value)
            _remember("knob_" + name, value)


def _set_parts(parts):
    cmds = _cmds()
    for part, _ in PART_LABELS:
        if cmds.checkBox(_part_control(part), exists=True):
            cmds.checkBox(_part_control(part), edit=True, value=part in parts)
    _remember("parts", json.dumps(list(parts)))


def show_group(key):
    """Show the knob group `key` alone: its column managed, its tab lit, remembered."""
    cmds = _cmds()
    if key not in dict((k, l) for k, l, _ in GROUPS):
        key = GROUPS[0][0]
    _remember("group", key)
    for each, _, _ in GROUPS:
        if cmds.columnLayout(_group_column(each), exists=True):
            cmds.columnLayout(_group_column(each), edit=True, manage=each == key)
    if cmds.iconTextRadioButton(_group_tab(key), exists=True):
        cmds.iconTextRadioButton(_group_tab(key), edit=True, select=True)


def _load(root):
    """A walked skeleton's walk, pose, parts and knobs into the card; it becomes the target."""
    name, knobs, pose, parts = scene.pick(root)
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        _remember("walk", name)
        _remember("pose", pose or NO_POSE)
        _fill_menus(name, pose or NO_POSE)
        _set_parts(parts)
        frames = scene.load_walk(name)[0].P if name in scene.walk_names() else int(knobs.get("tempo") or 30)
        _set_knobs(knobs, frames)
    finally:
        _QUIET[0] = quiet
    return name


# ---- the lines ----

def _short(path):
    return path.rsplit("|", 1)[-1] if path else "-"


def selection_line(root):
    """The card's subtitle: the selected skeleton (walked or not), else the target."""
    try:
        walk = chosen_walk()
    except scene.Refusal:
        walk = None
    if root:
        memo = scene.memo_of(root)
        if memo.get("walk"):
            pose = memo.get("pose")
            share = memo.get("knobs", {}).get("pose", 0.0)
            return "%s walks %s%s" % (_short(root), memo["walk"],
                                      " under %s x%.2f" % (pose, share) if pose and share > 0 else "")
        return "%s: Apply puts %s on it" % (_short(root), walk) if walk else "%s: save a walk first" % _short(root)
    try:
        target = scene.target_root()
    except scene.Refusal:
        return NOTHING
    return "Target: %s (%s)" % (_short(target), scene.memo_of(target).get("walk", "-"))


def status(text):
    """The card's line - and the hub's one message line. Answers the text (a hotkey row shows it when the
    card is closed)."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


def refresh(*_):
    """The subtitle from the selection; a walked skeleton selected that is not the target is read into the
    card and becomes the target."""
    cmds = _cmds()
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        root = scene.selected_top()
        if root and scene.memo_of(root).get("walk"):
            uuid = (cmds.ls(root, uuid=True) or [None])[0]
            if uuid != scene._state().get("target"):
                _load(root)
        cmds.text(SUBTITLE, edit=True, label=selection_line(root))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _press(action):
    try:
        text = action()
    except scene.REFUSALS as refusal:
        text = str(refusal)
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        text = "Walk Builder failed: %s" % exc
    refresh()
    return status(text)


# ---- the presses ----

def _apply_to(root):
    _remember("walk", chosen_walk())
    _remember("pose", chosen_pose() or NO_POSE)
    _remember("parts", json.dumps(list(chosen_parts())))
    return scene.apply(root, chosen_walk(), values(), chosen_pose(), chosen_parts())[2]


def press_apply(*_):
    """Apply: the walk onto the selected skeleton, which becomes the target."""
    return _press(lambda: _apply_to(scene.selected_root()))


def slider_changed(*_):
    """A released knob (a pose, a part): the target keyed again; none - say how to get one."""
    if _QUIET[0]:
        return None
    return _press(lambda: _apply_to(scene.target_root()))


def walk_changed(*_):
    """Another walk picked: its own tempo in the card; the target waits for Apply."""
    if _QUIET[0]:
        return None

    def run():
        name = chosen_walk()
        _remember("walk", name)
        walk = scene.load_walk(name)[0]
        _set_knobs({"tempo": walk.P}, walk.P)
        return walk.summary() + " - Apply puts it on the selected skeleton"
    return _press(run)


def press_reset(*_):
    def run():
        walk = scene.load_walk(chosen_walk())[0]
        knobs = dict(scene.wm.DEFAULTS)
        knobs["tempo"] = walk.P
        _set_knobs(knobs, walk.P)
        try:
            root = scene.target_root()
        except scene.Refusal:
            return "the knobs are back at their defaults - select a skeleton and press Apply"
        return _apply_to(root)
    return _press(run)


def _ask(title, default):
    cmds = _cmds()
    answer = cmds.promptDialog(title=title, message="Name:", text=default, button=["Save", "Cancel"],
                               defaultButton="Save", cancelButton="Cancel", dismissString="Cancel")
    return (cmds.promptDialog(query=True, text=True) or default) if answer == "Save" else None


def press_save_walk(*_):
    def run():
        root = scene.selected_root()
        name = _ask("Save walk", scene.read_clip(root)[0].name)
        if name is None:
            return "nothing saved"
        name, line = scene.save_walk(root, name)
        _remember("walk", name)
        _fill_menus(walk=name)
        walk = scene.load_walk(name)[0]
        _set_knobs({"tempo": walk.P}, walk.P)
        return line
    return _press(run)


def press_save_pose(*_):
    def run():
        root = scene.selected_root()
        name = _ask("Save pose", _short(root).split(":")[-1] + "_pose")
        if name is None:
            return "nothing saved"
        name, line = scene.save_pose(root, name)
        _remember("pose", name)
        _fill_menus(pose=name)
        return line + " - raise Pose to walk in it"
    return _press(run)


def show_folder(*_):
    folder = scene.folder()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    os.startfile(folder)
    return status("the walks folder: %s" % folder)


def refresh_lists(*_):
    _fill_menus()
    return status("%d walks, %d poses in %s" % (len(scene.walk_names()), len(scene.pose_names()),
                                                 scene.folder()))


def group_changed(key):
    def go(*_):
        show_group(key)
    return go


# ---- the card ----

def _menu_row(menu, label, command, button, icon_tip, press):
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    #  the word in a column of its own: no other card gives an optionMenu a label, and the skin styles the
    #  bare dropdown (a QComboBox)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3), (3, "left", 3)])
    cmds.text(label=label, width=hubstyle.pick(32, 36), align="left")
    cmds.optionMenu(menu, changeCommand=command,
                    annotation=("The walk Apply puts on a skeleton" if menu == WALK_MENU else
                                "The character pose the walk takes at the Pose share (none: the walk's own)")
                    + " - right click: the walks folder")
    cmds.popupMenu(parent=menu, button=3)
    cmds.menuItem(label="Show the walks folder", command=show_folder)
    cmds.menuItem(label="Read the lists again", command=refresh_lists)
    cmds.setParent("..", menu=True)
    hubstyle.mark(cmds.button(button, label=hubstyle.tool_label("Save..."), width=hubstyle.tool_width(56),
                              height=hubstyle.height("field", 24), annotation=icon_tip,
                              command=lambda *_: press()), "tool", "device-floppy")
    cmds.setParent("..")


def _slider(name):
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    label, tip = LABELS[name]
    default = scene.wm.DEFAULTS[name]
    common = dict(label=label, field=True, columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                  adjustableColumn=3, height=hubstyle.height("small", 22), annotation=tip,
                  changeCommand=slider_changed)
    if name == "tempo":
        stored = int(round(float(_stored("knob_tempo", 0.0) or 0.0)))
        cmds.intSliderGrp(_control(name), minValue=4, maxValue=120, fieldMinValue=4, fieldMaxValue=400,
                          value=stored if stored >= 4 else 30, **common)
        return
    low, high = scene.wm.RANGES[name]
    cmds.floatSliderGrp(_control(name), minValue=low, maxValue=high, fieldMinValue=low, fieldMaxValue=high,
                        step=0.05, precision=2, value=float(_stored("knob_" + name, default)), **common)


def build_panel():
    """The card into the current layout: the target line; the walk and the pose with their save icons; the
    pose's share and parts; Apply / Reset; the knob groups' tabs and the shown group; the status line."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=NOTHING, align="left"), "subtitle")
    _menu_row(WALK_MENU, "Walk", walk_changed, SAVE_WALK_BTN, TIPS["save_walk"], press_save_walk)
    _menu_row(POSE_MENU, "Pose", slider_changed, SAVE_POSE_BTN, TIPS["save_pose"], press_save_pose)
    _slider("pose")
    stored_parts = chosen_parts()

    def chip(part, label):
        hubstyle.mark(cmds.checkBox(_part_control(part), label=label, value=part in stored_parts,
                                    annotation=TIPS["parts"], changeCommand=slider_changed), "chip")
    if hubstyle.skinning():
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
    else:
        cmds.rowLayout(numberOfColumns=len(PART_LABELS))
    for part, label in PART_LABELS:
        chip(part, label)
    cmds.setParent("..")
    hubstyle.mark(cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                                 columnAttach=[(1, "both", 0), (2, "both", 4)]), "fill", layout=True)
    hubstyle.mark(cmds.button(APPLY_BTN, label="Apply", height=hubstyle.height("button", 28),
                              annotation=TIPS["apply"], command=lambda *_: press_apply()), "primary", "walk")
    hubstyle.mark(cmds.button(RESET_BTN, label="Reset", height=hubstyle.height("button", 28),
                              annotation=TIPS["reset"], command=lambda *_: press_reset()), "secondary", "refresh")
    cmds.setParent("..")
    shown = _stored("group", GROUPS[0][0])
    segments = cmds.rowLayout(numberOfColumns=len(GROUPS),
                              columnAttach=[(i + 1, "both", 1) for i in range(len(GROUPS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(GROUP_TABS)
    for key, label, names in GROUPS:
        hubstyle.mark(cmds.iconTextRadioButton(
            _group_tab(key), style="textOnly", label=label, height=hubstyle.height("segment", 24),
            select=key == shown, collection=GROUP_TABS,
            annotation="The knobs of %s: %s" % (label.lower(), ", ".join(LABELS[n][0] for n in names)),
            onCommand=group_changed(key)), "segment")
    cmds.setParent("..")
    for key, label, names in GROUPS:
        cmds.columnLayout(_group_column(key), adjustableColumn=True, rowSpacing=hubstyle.row_spacing(2),
                          manage=key == shown)
        for name in names:
            _slider(name)
        cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    _fill_menus()
    try:
        walk = scene.load_walk(chosen_walk())[0]
        tempo = float(_stored("knob_tempo", 0.0) or 0.0)
        _set_knobs({"tempo": tempo if tempo >= 1 else walk.P}, walk.P)
    except Exception:                                        # noqa: BLE001 - no walk saved yet
        pass
    show_group(shown)
    start()
    refresh()
    return column


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own refresh on every selection change (per card: a popup copy's job dies with the
    copy and leaves the hub's)."""
    import maya_hubcopy as hubcopy
    cmds = _cmds()
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    old = JOB.pop(_card_key(), None)
    if old is not None:
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", refresh], parent=STATUS)


def is_open():
    return bool(_cmds().text(STATUS, exists=True))


def show_window():
    """The hub, on the Walk Builder section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
